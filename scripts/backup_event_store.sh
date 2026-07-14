#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
for command in sha256sum tar zstd psql; do require_command "$command"; done
if [[ -n "${COGOS_POSTGRES_TOOL_CONTAINER:-}" ]]; then
  require_command docker
  require_value COGOS_CONTAINER_DATABASE_ADMIN_URL
else
  require_command pg_dump
fi
for name in COGOS_DATABASE_ADMIN_URL COGOS_POSTGRES_DATABASE COGOS_ARTIFACT_ROOT; do require_value "$name"; done
database_cli_url="${COGOS_DATABASE_ADMIN_URL/postgresql+asyncpg/postgresql}"
backup_root="${COGOS_BACKUP_ROOT:-/home/palkouser/backup/cognitive-os-archive}"
database_dir="$backup_root/database-backups"
artifact_dir="$backup_root/artifacts"
mkdir -p "$database_dir" "$artifact_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$database_dir/$timestamp-event-store.dump"
archive="$artifact_dir/$timestamp-artifacts.tar.zst"
manifest="$database_dir/$timestamp-backup-manifest.json"
echo "Backing up database: $COGOS_POSTGRES_DATABASE"
if [[ -n "${COGOS_POSTGRES_TOOL_CONTAINER:-}" ]]; then
  docker exec "$COGOS_POSTGRES_TOOL_CONTAINER" \
    pg_dump --format=custom "$COGOS_CONTAINER_DATABASE_ADMIN_URL" > "$dump"
else
  pg_dump --format=custom --file="$dump" "$database_cli_url"
fi
sha256sum "$dump" > "$dump.sha256"
if [[ -d "$COGOS_ARTIFACT_ROOT" ]]; then
  tar --exclude='.tmp' -C "$COGOS_ARTIFACT_ROOT" -cf - . | zstd -q -T0 -o "$archive"
else
  tar -cf - --files-from /dev/null | zstd -q -T0 -o "$archive"
fi
sha256sum "$archive" > "$archive.sha256"
event_count="$(psql "$database_cli_url" -Atqc 'SELECT count(*) FROM cognitive_os.events')"
artifact_count="$(psql "$database_cli_url" -Atqc 'SELECT count(*) FROM cognitive_os.artifacts')"
revision="$(psql "$database_cli_url" -Atqc 'SELECT version_num FROM alembic_version LIMIT 1')"
uv run python - "$manifest" "$timestamp" "$dump" "$archive" "$event_count" "$artifact_count" "$revision" "$COGOS_POSTGRES_DATABASE" <<'PY'
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

manifest, timestamp, dump, archive, event_count, artifact_count, revision, database_name = sys.argv[1:]
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
data = {
    "created_at": datetime.now(UTC).isoformat(),
    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sprint_baseline": "sprint-3-baseline",
    "database_name": database_name,
    "alembic_revision": revision,
    "database_dump": Path(dump).name,
    "database_sha256": digest(dump),
    "artifact_archive": Path(archive).name,
    "artifact_sha256": digest(archive),
    "event_count": int(event_count),
    "artifact_count": int(artifact_count),
}
Path(manifest).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
chmod 0640 "$dump" "$dump.sha256" "$archive" "$archive.sha256" "$manifest"
echo "Backup manifest: $manifest"
