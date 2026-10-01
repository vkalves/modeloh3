#!/usr/bin/env bash
set -euo pipefail

COMFY_VERSION="${COMFY_VERSION:-v0.38.0}"
COMFY_DIR="${COMFY_DIR:-/workspace/runpod-slim/ComfyUI}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== MiniMax H3 / ComfyUI installer =="
echo "ComfyUI: ${COMFY_VERSION}"
echo "Destino:  ${COMFY_DIR}"

mkdir -p "$(dirname "${COMFY_DIR}")"

if [ ! -d "${COMFY_DIR}/.git" ]; then
  if [ -d "${COMFY_DIR}" ] && [ "$(ls -A "${COMFY_DIR}" 2>/dev/null || true)" ]; then
    echo "ERRO: ${COMFY_DIR} existe, mas nao e um repositorio Git."
    echo "Use o template ComfyUI - CUDA 13.0 do RunPod ou defina COMFY_DIR."
    exit 1
  fi
  echo "Clonando ComfyUI..."
  git clone https://github.com/Comfy-Org/ComfyUI.git "${COMFY_DIR}"
fi

cd "${COMFY_DIR}"
git fetch --tags
git checkout "${COMFY_VERSION}"

if [ -x "${COMFY_DIR}/.venv-cu128/bin/python" ]; then
  PYTHON="${COMFY_DIR}/.venv-cu128/bin/python"
elif [ -x "${COMFY_DIR}/.venv/bin/python" ]; then
  PYTHON="${COMFY_DIR}/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

echo "Python: ${PYTHON}"

echo "Instalando/ajustando dependencias do ComfyUI..."
"${PYTHON}" -m pip install -r requirements.txt
"${PYTHON}" -m pip install "huggingface_hub>=0.34,<2.0"

mkdir -p   models/diffusion_models   models/text_encoders   models/vae   user/default/workflows

echo "Baixando modelos oficiais Comfy-Org/MiniMax-H3..."
"${PYTHON}" - <<'PY'
import os
from huggingface_hub import hf_hub_download

repo_id = "Comfy-Org/MiniMax-H3"
local_dir = os.path.join(os.getcwd(), "models")
token = os.environ.get("HF_TOKEN") or None

files = [
    "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
    "text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
    "vae/minimax_h3_video_vae_fp16.safetensors",
    "vae/minimax_h3_audio_vae_fp32.safetensors",
]

for filename in files:
    print(f"\n>>> {filename}")
    hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        local_dir=local_dir,
        token=token,
    )
PY

echo
echo "Copiando workflow final..."
cp -f   "${SCRIPT_DIR}/workflows/H3_FINAL_RTX_PRO_6000_REVISADO.json"   "${COMFY_DIR}/user/default/workflows/H3_FINAL_RTX_PRO_6000_REVISADO.json"

echo
echo "Verificando integridade..."
bash "${SCRIPT_DIR}/verify.sh"

echo
echo "============================================"
echo "INSTALACAO CONCLUIDA."
echo "ComfyUI: ${COMFY_DIR}"
echo "Modelos MiniMax H3 baixados e verificados."
echo "Workflow instalado em user/default/workflows."
echo "============================================"
