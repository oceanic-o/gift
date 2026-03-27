#!/usr/bin/env bash
# =============================================================================
# backup_db.sh — Manual PostgreSQL backup
#
# Usage:
#   ./scripts/backup_db.sh               # saves to ./backups/giftdb_<timestamp>.dump
#   ./scripts/backup_db.sh my_backup     # saves to ./backups/my_backup.dump
#
# The .dump file is in PostgreSQL custom format (-F c).
# Keeps only the latest 2 non-empty backups in ./backups.
# Restore with: ./scripts/restore_db.sh <filename.dump>
# =============================================================================

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$(cd "$(dirname "$0")/.." && pwd)/backups"
LABEL="${1:-giftdb_${TIMESTAMP}}"
OUTPUT="${BACKUP_DIR}/${LABEL}.dump"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting backup → ${OUTPUT}"

docker exec gift_postgres \
  pg_dump \
    -U giftuser \
    -d giftdb \
    -F c \
    -f "/tmp/${LABEL}.dump"

docker cp "gift_postgres:/tmp/${LABEL}.dump" "$OUTPUT"
docker exec gift_postgres rm "/tmp/${LABEL}.dump"

if [ ! -s "$OUTPUT" ]; then
  echo "[backup] ERROR: backup file is empty, removing ${OUTPUT}"
  rm -f "$OUTPUT"
  exit 1
fi

# Remove zero-byte dumps and keep only latest 2 backups
find "$BACKUP_DIR" -type f -name "*.dump" -size 0 -delete
ls -1t "$BACKUP_DIR"/*.dump 2>/dev/null | tail -n +3 | xargs -r rm -f --

SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo "[backup] Done. File: ${OUTPUT} (${SIZE})"

# List all existing backups
echo ""
echo "[backup] All backups in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}"/*.dump 2>/dev/null || echo "  (none yet)"
