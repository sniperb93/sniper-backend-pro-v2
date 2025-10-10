#!/usr/bin/env bash
# Backup helper for remote hosts
# Usage:
#   ./scripts/backup_paths.sh /root/blaxing backend/routes/agent_executor_routes.py backend/utils
# Creates: /root/blaxing/backups_before_emergent_YYYYMMDD_HHMMSS/
set -euo pipefail

if [ $# -lt 2 ]; then
  echo "Usage: $0 <base_dir> <path1> [path2] ..." >&2
  exit 1
fi

BASE_DIR="$1"; shift
if [ ! -d "$BASE_DIR" ]; then
  echo "Base dir not found: $BASE_DIR" >&2
  exit 2
fi

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BASE_DIR/backups_before_emergent_${TS}"
mkdir -p "$BACKUP_DIR"

for P in "$@"; do
  # Resolve absolute source
  if [[ "$P" = /* ]]; then
    SRC="$P"
  else
    SRC="$BASE_DIR/$P"
  fi
  if [ ! -e "$SRC" ]; then
    echo "[WARN] Not found, skipping: $SRC" >&2
    continue
  fi

  # Compute relative path under base if possible
  REL="$P"
  if [[ "$SRC" == $BASE_DIR/* ]]; then
    REL="${SRC#${BASE_DIR}/}"
  fi

  DEST_DIR="$BACKUP_DIR/$(dirname "$REL")"
  mkdir -p "$DEST_DIR"
  echo "Backing up $SRC -> $BACKUP_DIR/$REL"
  cp -a "$SRC" "$BACKUP_DIR/$REL"

done

echo "Backup completed at: $BACKUP_DIR"