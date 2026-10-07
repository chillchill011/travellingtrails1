#!/usr/bin/env bash
set -euo pipefail
LOCK_ROOT="${TT_LOCK_ROOT:-/mnt/storage/chatgpt-locks}"; LOCK_FILE="$LOCK_ROOT/travellingtrails-n8n.lock"; mkdir -p "$LOCK_ROOT"; exec 9>"$LOCK_FILE"; flock -n 9 || { echo "Travelling Trails n8n lock is busy" >&2; exit 75; }; exec "$@"
