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
memory_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.memory_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.memory_items) END")"
memory_revision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.memory_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.memory_revisions) END")"
embedding_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.memory_embeddings') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.memory_embeddings) END")"
semantic_claim_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claims') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claims) END")"
semantic_revision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_revisions) END")"
semantic_observation_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_observations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_observations) END")"
semantic_evidence_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_evidence') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_evidence) END")"
semantic_relation_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_relations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_relations) END")"
semantic_contradiction_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_contradictions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_contradictions) END")"
wiki_page_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.wiki_pages') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.wiki_pages) END")"
wiki_revision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.wiki_page_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.wiki_page_revisions) END")"
semantic_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT claim_id, revision, previous_revision, object_json, belief_status, valid_from, valid_to, recorded_at, content_hash FROM cognitive_os.semantic_claim_revisions ORDER BY claim_id, revision) history" | sha256sum | awk '{print $1}')"
psql "$database_cli_url" -Atqc "SELECT json_build_object('content_hash', b.content_hash, 'size_bytes', b.size_bytes, 'storage_key', b.storage_key)::text FROM cognitive_os.artifact_blobs b JOIN cognitive_os.artifacts a ON a.content_hash=b.content_hash GROUP BY b.content_hash, b.size_bytes, b.storage_key ORDER BY b.storage_key" | uv run python scripts/artifact_restore_verify.py "$COGOS_ARTIFACT_ROOT"
uv run python - "$manifest" "$timestamp" "$dump" "$archive" "$event_count" "$artifact_count" "$revision" "$COGOS_POSTGRES_DATABASE" "$memory_count" "$memory_revision_count" "$embedding_count" "$semantic_claim_count" "$semantic_revision_count" "$semantic_observation_count" "$semantic_evidence_count" "$semantic_relation_count" "$semantic_contradiction_count" "$wiki_page_count" "$wiki_revision_count" "$semantic_history_sha256" <<'PY'
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

(
    manifest,
    timestamp,
    dump,
    archive,
    event_count,
    artifact_count,
    revision,
    database_name,
    memory_count,
    memory_revision_count,
    embedding_count,
    semantic_claim_count,
    semantic_revision_count,
    semantic_observation_count,
    semantic_evidence_count,
    semantic_relation_count,
    semantic_contradiction_count,
    wiki_page_count,
    wiki_revision_count,
    semantic_history_sha256,
) = sys.argv[1:]
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
data = {
    "created_at": datetime.now(UTC).isoformat(),
    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sprint_parent_baseline": "sprint-9-baseline",
    "database_name": database_name,
    "alembic_revision": revision,
    "database_dump": Path(dump).name,
    "database_sha256": digest(dump),
    "artifact_archive": Path(archive).name,
    "artifact_sha256": digest(archive),
    "event_count": int(event_count),
    "artifact_count": int(artifact_count),
    "memory_count": int(memory_count),
    "memory_revision_count": int(memory_revision_count),
    "embedding_count": int(embedding_count),
    "semantic_claim_count": int(semantic_claim_count),
    "semantic_revision_count": int(semantic_revision_count),
    "semantic_observation_count": int(semantic_observation_count),
    "semantic_evidence_count": int(semantic_evidence_count),
    "semantic_relation_count": int(semantic_relation_count),
    "semantic_contradiction_count": int(semantic_contradiction_count),
    "wiki_page_count": int(wiki_page_count),
    "wiki_revision_count": int(wiki_revision_count),
    "semantic_history_sha256": semantic_history_sha256,
}
Path(manifest).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
chmod 0640 "$dump" "$dump.sha256" "$archive" "$archive.sha256" "$manifest"
echo "Backup manifest: $manifest"
