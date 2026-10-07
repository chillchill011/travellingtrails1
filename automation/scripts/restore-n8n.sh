#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 ]] || { echo "usage: $0 <backup-dir>" >&2; exit 2; }; SRC="$1/database.sqlite"; DB="${TT_N8N_DB:-/home/aniket/nas-stack/n8n/data/database.sqlite}"; [[ -f "$SRC" ]] || { echo "missing backup DB" >&2; exit 2; }; echo "Restore is safety-gated: stop n8n via Portainer first and set TT_ALLOW_RESTORE=YES." >&2; [[ "${TT_ALLOW_RESTORE:-}" == YES ]] || exit 3; cp -a "$DB" "$DB.pre-restore.$(date -u +%Y%m%dT%H%M%SZ)"; cp -a "$SRC" "$DB"
