#!/usr/bin/env bash
set -Eeuo pipefail
source "$(dirname "$0")/scripts/common.sh"
python3 "$ROOT_DIR/scripts/sync_nodes.py" "$COMFY_DIR"
