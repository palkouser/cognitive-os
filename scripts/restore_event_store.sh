#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
[[ "${1:-}" == "--test-restore" ]] || { echo "Only --test-restore is supported." >&2; exit 1; }
for command in pg_restore psql sha256sum zstd tar; do require_command "$command"; done
for name in COGOS_RESTORE_DATABASE_URL COGOS_RESTORE_DATABASE_NAME COGOS_DATABASE_BOOTSTRAP_URL; do require_value "$name"; done
require_test_database "$COGOS_RESTORE_DATABASE_NAME"
backup_root="${COGOS_BACKUP_ROOT:-/home/palkouser/backup/cognitive-os-archive}"
manifest="$(find "$backup_root/database-backups" -name '*-backup-manifest.json' -type f | sort | tail -n1)"
[[ -n "$manifest" ]] || { echo "No backup manifest found." >&2; exit 1; }
prefix="${manifest%-backup-manifest.json}"
dump="$prefix-event-store.dump"
archive="$backup_root/artifacts/$(basename "$prefix")-artifacts.tar.zst"
sha256sum -c "$dump.sha256"
sha256sum -c "$archive.sha256"
psql "$COGOS_DATABASE_BOOTSTRAP_URL" -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$COGOS_RESTORE_DATABASE_NAME\"" \
  -c "CREATE DATABASE \"$COGOS_RESTORE_DATABASE_NAME\""
pg_restore --no-owner --exit-on-error --dbname="$COGOS_RESTORE_DATABASE_URL" "$dump"
restore_root="$(mktemp -d)"
trap 'rm -rf "$restore_root"' EXIT
zstd -q -dc "$archive" | tar -xf - -C "$restore_root"
revision="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT version_num FROM alembic_version LIMIT 1')"
event_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT count(*) FROM cognitive_os.events')"
artifact_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT count(*) FROM cognitive_os.artifacts')"
[[ -n "$revision" && "$event_count" =~ ^[0-9]+$ && "$artifact_count" =~ ^[0-9]+$ ]]
echo "Isolated restore verification passed."
