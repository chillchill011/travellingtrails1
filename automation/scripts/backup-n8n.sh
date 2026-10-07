#!/usr/bin/env bash
set -euo pipefail
ROOT="${TT_BACKUP_ROOT:-/mnt/storage/travellingtrails-backups}"; DB="${TT_N8N_DB:-/home/aniket/nas-stack/n8n/data/database.sqlite}"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; DIR="$ROOT/$TS-phase1"; mkdir -p "$DIR"; chmod 700 "$DIR"
python3 -c 'import sqlite3,sys; a=sqlite3.connect(sys.argv[1]); b=sqlite3.connect(sys.argv[2]); a.backup(b); b.close(); a.close()' "$DB" "$DIR/database.sqlite"
sha256sum "$DIR/database.sqlite" > "$DIR/SHA256SUMS"; chmod 600 "$DIR"/*; echo "$DIR"
