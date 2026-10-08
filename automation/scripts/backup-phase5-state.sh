#!/usr/bin/env bash
set -euo pipefail
STATE_ROOT="${TT_PHASE5_STATE_ROOT:-/home/aniket/nas-stack/travellingtrails-phase5}"
BACKUP_ROOT="${TT_BACKUP_ROOT:-/mnt/storage/travellingtrails-backups}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/${TS}-phase5-state"
mkdir -p "$DEST"
chmod 700 "$DEST"
if [[ -f "$STATE_ROOT/phase5.sqlite3" ]]; then
  python3 - "$STATE_ROOT/phase5.sqlite3" "$DEST/phase5.sqlite3" <<'PY'
import sqlite3,sys
src,dst=sys.argv[1:]
a=sqlite3.connect(src); b=sqlite3.connect(dst); a.backup(b); b.close(); a.close()
PY
fi
if [[ -d "$STATE_ROOT/runs" ]]; then
  tar -C "$STATE_ROOT" -czf "$DEST/runs.tar.gz" runs
fi
( cd "$DEST" && sha256sum phase5.sqlite3 runs.tar.gz 2>/dev/null || true ) > "$DEST/SHA256SUMS"
chmod 600 "$DEST"/* 2>/dev/null || true
printf '%s\n' "$DEST"
