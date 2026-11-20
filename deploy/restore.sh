#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-.env.production}"
: "${CONFIRM_RESTORE:?Set CONFIRM_RESTORE=YES to explicitly authorise a destructive restore}"
: "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the private age identity file}"
: "${DB_BACKUP:?Set DB_BACKUP to the encrypted database backup path}"
: "${MEDIA_BACKUP:?Set MEDIA_BACKUP to the encrypted media backup path}"
[[ "$CONFIRM_RESTORE" == "YES" ]] || { echo "Restore not confirmed." >&2; exit 1; }
[[ -f "$ENV_FILE" && -f "$AGE_IDENTITY_FILE" && -f "$DB_BACKUP" && -f "$MEDIA_BACKUP" ]] || {
  echo "One or more restore files are missing." >&2
  exit 1
}
command -v age >/dev/null 2>&1 || { echo "Install age first." >&2; exit 1; }

COMPOSE=(docker compose --env-file "$ENV_FILE" -f compose.production.yml)

echo "Stopping application workers before the destructive restore..."
"${COMPOSE[@]}" stop web worker beat

echo "Restoring PostgreSQL database..."
age -d -i "$AGE_IDENTITY_FILE" "$DB_BACKUP" | \
  "${COMPOSE[@]}" exec -T db sh -c 'pg_restore --exit-on-error --clean --if-exists --single-transaction --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

echo "Restoring private uploads..."
age -d -i "$AGE_IDENTITY_FILE" "$MEDIA_BACKUP" | \
  "${COMPOSE[@]}" run --rm --no-deps -T web sh -c 'find /app/media -mindepth 1 -delete && tar -C /app/media -xzf -'

"${COMPOSE[@]}" up -d web worker beat caddy
"${COMPOSE[@]}" ps
echo "Restore completed. Verify application data, uploads, balances and logs before reopening service."
