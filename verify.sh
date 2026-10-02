#!/usr/bin/env bash
set -euo pipefail

COMFY_DIR="$(printenv COMFY_DIR || printf /workspace/runpod-slim/ComfyUI)"
if [ ! -d "$COMFY_DIR" ]; then
  echo "ERRO: ComfyUI nao encontrado em $COMFY_DIR"
  exit 1
fi
cd "$COMFY_DIR"

if [ -x "$COMFY_DIR/.venv-cu128/bin/python" ]; then
  PYTHON="$COMFY_DIR/.venv-cu128/bin/python"
elif [ -x "$COMFY_DIR/.venv/bin/python" ]; then
  PYTHON="$COMFY_DIR/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

echo "== Ambiente =="
git describe --tags --always || true
"$PYTHON" -m pip check
echo
echo "== GPU / Torch =="
"$PYTHON" - <<'PY'
import torch
print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CUDA indisponivel")
print("Capability:", torch.cuda.get_device_capability(0) if torch.cuda.is_available() else "-")
PY

check_file () {
  local expected="$1"
  local file="$2"
  if [ ! -f "$file" ]; then echo "FALTANDO: $file"; return 1; fi
  local actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  if [ "$actual" = "$expected" ]; then
    echo "OK  $file"
  else
    echo "ERRO $file"
    echo " esperado: $expected"
    echo " obtido:   $actual"
    return 1
  fi
}
check_present () {
  if [ -f "$1" ]; then echo "OK  $1"; else echo "FALTANDO: $1"; return 1; fi
}

echo
echo "== Pesos H3 com SHA256 registrado =="
check_file "9255f52b6677845ad238f20dfaafa94727053694127ab7f255c048f0f9365779" "models/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"
check_file "35a88d51044231fe332301d7a62aa81e3f2cba62febeb446e2c1e3e0ef76f2c6" "models/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
check_file "8e505d95dd1561d47abd43d4238fd40d9bb1ae9e147ed0a4cba778d76ae4db48" "models/vae/minimax_h3_audio_vae_fp32.safetensors"

echo
echo "== Pesos do workflow atual =="
check_present "models/vae/minimax_h3_video_vae_int8_convrot.safetensors"
check_present "models/checkpoints/sam3.1_multiplex_fp16.safetensors"
check_present "custom_nodes/ComfyUI-H3-Reusable/__init__.py"
check_present "custom_nodes/ComfyUI-H3-Reusable/logic.py"
grep -q "h3-mask-protection-v2" "custom_nodes/ComfyUI-H3-Reusable/__init__.py" || { echo "ERRO: mascara v2 nao encontrada"; exit 1; }
check_present "user/default/workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json"
python -m json.tool "user/default/workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json" >/dev/null

echo
echo "Workflow e arquivos presentes."
