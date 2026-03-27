#!/usr/bin/env bash
# =============================================================================
# restore_db.sh — Restore PostgreSQL from a .dump file
#
# Usage:
#   ./scripts/restore_db.sh backups/giftdb_20260302_210000.dump
#
# WARNING: This drops and recreates the giftdb database.
#          All current data will be replaced.
# =============================================================================

set -e

DUMP_FILE="$1"

if [ -z "$DUMP_FILE" ]; then
  echo "Usage: $0 <path_to_dump_file>"
  echo ""
  echo "Available backups:"
  ls -lh "$(cd "$(dirname "$0")/.." && pwd)/backups/"*.dump 2>/dev/null || echo "  (none found)"
  exit 1
fi

if [ ! -f "$DUMP_FILE" ]; then
  echo "[ERROR] File not found: ${DUMP_FILE}"
  exit 1
fi

DUMP_FILENAME=$(basename "$DUMP_FILE")

echo "[restore] Source: ${DUMP_FILE}"
echo "[restore] WARNING: This will REPLACE all data in giftdb!"
read -p "[restore] Are you sure? Type 'yes' to continue: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "[restore] Aborted."
  exit 0
fi

echo "[restore] Copying dump into container..."
docker cp "$DUMP_FILE" "gift_postgres:/tmp/${DUMP_FILENAME}"

echo "[restore] Dropping and recreating database..."
docker exec gift_postgres \
  psql -U giftuser -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='giftdb' AND pid <> pg_backend_pid();"

docker exec gift_postgres \
  psql -U giftuser -d postgres -c "DROP DATABASE IF EXISTS giftdb;"

docker exec gift_postgres \
  psql -U giftuser -d postgres -c "CREATE DATABASE giftdb OWNER giftuser;"

echo "[restore] Restoring from dump..."
docker exec gift_postgres \
  pg_restore \
    -U giftuser \
    -d giftdb \
    --no-owner \
    --role=giftuser \
    "/tmp/${DUMP_FILENAME}"

docker exec gift_postgres rm "/tmp/${DUMP_FILENAME}"

echo ""
echo "[restore] Done! Database restored from: ${DUMP_FILE}"
