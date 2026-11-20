#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
RECIPIENT_FILE="${BACKUP_RECIPIENT_FILE:-$ROOT_DIR/deploy/backup.age-recipient}"

command -v age >/dev/null 2>&1 || {
  echo "age is required. Install age before taking encrypted backups." >&2
  exit 1
}
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 1; }
[[ -f "$RECIPIENT_FILE" ]] || {
  echo "Create $RECIPIENT_FILE containing the age public recipient key." >&2
  exit 1
}
RECIPIENT="$(tr -d '\r\n ' < "$RECIPIENT_FILE")"
[[ -n "$RECIPIENT" ]] || { echo "Backup recipient key is empty." >&2; exit 1; }

COMPOSE=(docker compose --env-file "$ENV_FILE" -f compose.production.yml)
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_DIR="$(mktemp -d)"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Dumping PostgreSQL database..."
"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$TMP_DIR/database.dump"

echo "Archiving private uploaded files..."
"${COMPOSE[@]}" exec -T web sh -c 'tar -C /app/media -czf - .' > "$TMP_DIR/media.tar.gz"

echo "Encrypting backup files..."
age -r "$RECIPIENT" -o "$BACKUP_DIR/spm-database-$STAMP.dump.age" "$TMP_DIR/database.dump"
age -r "$RECIPIENT" -o "$BACKUP_DIR/spm-media-$STAMP.tar.gz.age" "$TMP_DIR/media.tar.gz"

find "$BACKUP_DIR" -type f -name 'spm-*.age' -mtime +30 -delete

echo "Encrypted backup completed:"
echo "  $BACKUP_DIR/spm-database-$STAMP.dump.age"
echo "  $BACKUP_DIR/spm-media-$STAMP.tar.gz.age"
echo "Copy these encrypted files to a separate off-site backup location."
