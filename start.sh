#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/scripts/common.sh"
require_python
actual_version="$(git -C "$COMFY_DIR" describe --tags --exact-match 2>/dev/null || true)"
[[ "$actual_version" = "$COMFY_VERSION" ]] || { echo "ERRO: esperado $COMFY_VERSION no destino, encontrado $actual_version"; exit 1; }
"$PYTHON" "$ROOT_DIR/scripts/sync_nodes.py" --check "$COMFY_DIR"
mkdir -p "$ROOT_DIR/logs"
LOG="$ROOT_DIR/logs/start-$(date +%Y%m%d-%H%M%S).log"
echo "Destino: $COMFY_DIR | Python: $PYTHON | Log: $LOG"
"$PYTHON" -u "$ROOT_DIR/scripts/server.py" 2>&1 | tee -a "$LOG"
