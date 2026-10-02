#!/usr/bin/env bash
set -euo pipefail

COMFY_VERSION="$(printenv COMFY_VERSION || printf v0.38.0)"
COMFY_DIR="$(printenv COMFY_DIR || printf /workspace/runpod-slim/ComfyUI)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NODE_SOURCE="$SCRIPT_DIR/custom_nodes/ComfyUI-H3-Reusable"
NODE_TARGET="$COMFY_DIR/custom_nodes/ComfyUI-H3-Reusable"

echo "== MiniMax H3 + SAM3.1 / ComfyUI installer =="
echo "ComfyUI: $COMFY_VERSION"
echo "Destino:  $COMFY_DIR"

mkdir -p "$(dirname "$COMFY_DIR")"
if [ ! -d "$COMFY_DIR/.git" ]; then
  if [ -d "$COMFY_DIR" ] && [ "$(ls -A "$COMFY_DIR" 2>/dev/null || true)" ]; then
    echo "ERRO: $COMFY_DIR existe, mas nao e um repositorio Git."
    echo "Use o template ComfyUI - CUDA 13.0 do RunPod ou defina COMFY_DIR."
    exit 1
  fi
  echo "Clonando ComfyUI..."
  git clone https://github.com/Comfy-Org/ComfyUI.git "$COMFY_DIR"
fi

cd "$COMFY_DIR"
git fetch --tags
git checkout "$COMFY_VERSION"
if [ -x "$COMFY_DIR/.venv-cu128/bin/python" ]; then
  PYTHON="$COMFY_DIR/.venv-cu128/bin/python"
elif [ -x "$COMFY_DIR/.venv/bin/python" ]; then
  PYTHON="$COMFY_DIR/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

echo "Python: $PYTHON"
echo "Instalando dependencias do ComfyUI..."
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m pip install "huggingface_hub>=0.34,<2.0"

mkdir -p models/diffusion_models models/text_encoders models/vae models/checkpoints user/default/workflows custom_nodes
echo "Baixando os pesos usados pelo workflow..."
"$PYTHON" - <<'PY'
import os
from huggingface_hub import hf_hub_download

token = os.environ.get("HF_TOKEN") or None
files = [
    ("Comfy-Org/MiniMax-H3", "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
    ("Comfy-Org/MiniMax-H3", "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    ("Comfy-Org/MiniMax-H3", "vae/minimax_h3_video_vae_int8_convrot.safetensors"),
    ("Comfy-Org/MiniMax-H3", "vae/minimax_h3_audio_vae_fp32.safetensors"),
    ("Comfy-Org/sam3.1", "checkpoints/sam3.1_multiplex_fp16.safetensors"),
]
for repo_id, filename in files:
    print(f"\n>>> {repo_id}/{filename}")
    hf_hub_download(repo_id=repo_id, filename=filename, local_dir="models", token=token)
PY

echo
echo "Instalando o nó H3 com mascara v2..."
if ! grep -q "h3-mask-protection-v2" "$NODE_SOURCE/__init__.py"; then
  echo "ERRO: o pacote do nó nao contem a correcao de mascara v2."
  exit 1
fi
"$PYTHON" -m py_compile "$NODE_SOURCE/__init__.py" "$NODE_SOURCE/logic.py"
if [ -d "$NODE_TARGET" ]; then
  BACKUP="$COMFY_DIR/h3_backups/ComfyUI-H3-Reusable_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$(dirname "$BACKUP")"
  cp -a "$NODE_TARGET" "$BACKUP"
  echo "Backup do nó anterior: $BACKUP"
fi
rm -rf "$NODE_TARGET"
cp -a "$NODE_SOURCE" "$NODE_TARGET"

echo
echo "Instalando o workflow atual..."
cp -f "$SCRIPT_DIR/workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json" \
  "$COMFY_DIR/user/default/workflows/H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json"

echo
echo "Verificando..."
bash "$SCRIPT_DIR/verify.sh"
echo
echo "INSTALACAO CONCLUIDA."
echo "Reinicie o ComfyUI antes de usar o workflow."
