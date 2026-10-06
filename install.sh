#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/scripts/common.sh"
for cmd in git python3 flock; do
  command -v "$cmd" >/dev/null || { echo "ERRO: instale $cmd no template antes de continuar."; exit 1; }
done
mkdir -p "$ROOT_DIR/logs"
exec 9>"$ROOT_DIR/.h3-install.lock"
flock -n 9 || { echo 'Ja existe uma instalacao em andamento neste repositorio.'; exit 1; }
LOG="$ROOT_DIR/logs/install-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
trap 'echo "ERRO na etapa ${STEP:-inicial}, linha $LINENO. Log: $LOG. Corrija o erro e repita bash install.sh; nao apague os modelos."' ERR
export PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 HF_HUB_DOWNLOAD_TIMEOUT=60 HF_HUB_ETAG_TIMEOUT=30
export GIT_TERMINAL_PROMPT=0
# Ignore another ComfyUI virtualenv inherited from the terminal.
BASE_PYTHON="${H3_BASE_PYTHON:-$(python3 -c 'import sys; print(sys._base_executable)')}"
step() { STEP="$1"; echo; echo "[$STEP/7] $2"; }
run() { "$BASE_PYTHON" "$ROOT_DIR/scripts/run_step.py" "$@"; }
step 1 'Conferindo armazenamento e ambiente'
echo "Destino: $COMFY_DIR | Versao: $COMFY_VERSION | Log: $LOG"
"$BASE_PYTHON" "$ROOT_DIR/scripts/preflight.py"
# Refuse to modify code/dependencies of a live instance.
"$BASE_PYTHON" - <<'PY'
from pathlib import Path
import os
for proc in Path('/proc').glob('[0-9]*'):
    try:
        args = (proc/'cmdline').read_bytes().split(b'\0')
        if b'main.py' in args and (proc/'cwd').resolve() == Path(os.environ['COMFY_DIR']).resolve():
            raise SystemExit(f'ComfyUI deste destino esta ativo (PID {proc.name}). Pare-o antes de instalar.')
    except (PermissionError, FileNotFoundError, ProcessLookupError):
        pass
PY
step 2 'Preparando ComfyUI'
if [[ ! -d "$COMFY_DIR/.git" ]]; then
  [[ -z "$(ls -A "$COMFY_DIR")" ]] || { echo 'Destino nao vazio e sem Git. Escolha outra pasta com COMFY_DIR.'; exit 1; }
  run git clone --branch "$COMFY_VERSION" --depth 1 https://github.com/Comfy-Org/ComfyUI.git "$COMFY_DIR"
fi
cd "$COMFY_DIR"
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'ComfyUI tem alteracoes locais. Preserve-as antes de atualizar.'; exit 1; }
run git fetch --depth 1 origin "tag" "$COMFY_VERSION"
git checkout --detach "$COMFY_VERSION"
step 3 'Criando ambiente Python exclusivo do H3'
if [[ ! -x "$PYTHON" ]]; then
  run "$BASE_PYTHON" -m venv "$COMFY_DIR/.venv-h3"
fi
"$PYTHON" -c 'import sys; print("Python H3:", sys.executable)'
run "$PYTHON" -m pip install --timeout 60 --retries 3 -r requirements.txt
run "$PYTHON" -m pip install --timeout 60 --retries 3 'huggingface_hub>=0.34,<2.0'
"$PYTHON" -m pip check
step 4 'Baixando modelos (repetir aproveita o cache do Hugging Face)'
mkdir -p models user/default/workflows custom_nodes
run "$PYTHON" "$ROOT_DIR/scripts/download_models.py"
step 5 'Instalando no e workflow; preservando copia anterior'
NODE_SOURCE="$ROOT_DIR/custom_nodes/ComfyUI-H3-Reusable"
grep -q h3-mask-protection-v2 "$NODE_SOURCE/__init__.py"
"$PYTHON" -m py_compile "$NODE_SOURCE/__init__.py" "$NODE_SOURCE/logic.py"
BACKUP="$COMFY_DIR/h3_backups/$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$BACKUP"
if [[ -e custom_nodes/ComfyUI-H3-Reusable ]]; then
  mv custom_nodes/ComfyUI-H3-Reusable "$BACKUP/"
fi
cp -a "$NODE_SOURCE" custom_nodes/
if [[ -f "user/default/workflows/$WORKFLOW" ]]; then
  cp -a "user/default/workflows/$WORKFLOW" "$BACKUP/"
fi
cp "$ROOT_DIR/workflows/$WORKFLOW" user/default/workflows/
step 6 'Verificando dependencias e arquivos'
run bash "$ROOT_DIR/verify.sh"
step 7 'Salvando destino para os proximos comandos'
printf '%s\n' "$COMFY_DIR" > "$ROOT_DIR/.h3-comfy-dir"
echo 'ARQUIVOS INSTALADOS E VERIFICADOS. O servidor ainda precisa ser iniciado.'
echo "Para abrir a instalacao correta: bash $ROOT_DIR/start.sh"
echo 'A geracao de video ainda precisa de um teste real na GPU.'
