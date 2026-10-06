#!/usr/bin/env bash
# Shared by install, verify and start. Never execute configuration as shell code.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -z "${COMFY_DIR:-}" && -f "$ROOT_DIR/.h3-comfy-dir" ]]; then
  IFS= read -r COMFY_DIR < "$ROOT_DIR/.h3-comfy-dir"
fi
export COMFY_DIR="${COMFY_DIR:-/workspace/ComfyUI-H3}"
[[ "$COMFY_DIR" = /* && "$COMFY_DIR" != / ]] || { echo 'ERRO: COMFY_DIR deve ser um caminho absoluto diferente de /.'; exit 1; }
export COMFY_VERSION="${COMFY_VERSION:-v0.38.0}"
PYTHON="$COMFY_DIR/.venv-h3/bin/python"
WORKFLOW=H3_REUTILIZAVEL_SAM3_MASCARA_NATIVA.json
require_python() {
  [[ -x "$PYTHON" ]] || { echo "Ambiente H3 ausente. Execute: bash $ROOT_DIR/install.sh"; exit 1; }
}
