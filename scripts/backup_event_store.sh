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
skill_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.skill_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.skill_items) END")"
skill_revision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.skill_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.skill_revisions) END")"
skill_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT skill_id, revision, previous_revision, status, package_hash, content_hash FROM cognitive_os.skill_revisions ORDER BY skill_id, revision) history" | sha256sum | awk '{print $1}')"
strategy_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_items) END")"
strategy_revision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_revisions) END")"
strategy_edge_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_edges') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_edges) END")"
strategy_selection_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_selections') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_selections) END")"
strategy_outcome_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_outcomes') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_outcomes) END")"
strategy_access_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_accesses) END")"
strategy_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT strategy_id, revision, previous_revision, status, content_hash FROM cognitive_os.strategy_revisions ORDER BY strategy_id, revision) history" | sha256sum | awk '{print $1}')"
experience_compilation_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_compilations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_compilations) END")"
experience_source_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_sources') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_sources) END")"
experience_candidate_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_candidates') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_candidates) END")"
experience_decision_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_decisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_decisions) END")"
experience_access_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_accesses) END")"
experience_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT compilation_id, snapshot_hash, terminal_state, completeness FROM cognitive_os.experience_snapshots ORDER BY compilation_id) history" | sha256sum | awk '{print $1}')"
corpus_source_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_sources') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_sources) END")"
corpus_item_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_items) END")"
corpus_route_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_route_decisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_route_decisions) END")"
corpus_manifest_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_manifests') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_manifests) END")"
corpus_export_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_exports') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_exports) END")"
corpus_access_count="$(psql "$database_cli_url" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_accesses) END")"
corpus_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT corpus_item_id, current_revision, current_status, canonical_content_hash, item_hash FROM cognitive_os.corpus_items ORDER BY corpus_item_id) history" | sha256sum | awk '{print $1}')"
routing_profile_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.model_capability_profiles")"
routing_profile_revision_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.model_capability_revisions")"
routing_policy_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_policies")"
routing_policy_revision_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_policy_revisions")"
routing_observation_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_observations")"
routing_decision_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_decisions")"
routing_outcome_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_outcomes")"
routing_statistics_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_statistics")"
routing_experiment_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_experiments")"
routing_access_count="$(psql "$database_cli_url" -Atqc "SELECT count(*) FROM cognitive_os.routing_accesses")"
routing_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT kind, identity, revision, content_hash FROM (SELECT 'profile' kind, model_identity_hash identity, revision, profile_hash content_hash FROM cognitive_os.model_capability_revisions UNION ALL SELECT 'policy', policy_id, revision, policy_hash FROM cognitive_os.routing_policy_revisions UNION ALL SELECT 'observation', observation_id::text, 1, content_hash FROM cognitive_os.routing_observations UNION ALL SELECT 'decision', decision_id::text, 1, content_hash FROM cognitive_os.routing_decisions UNION ALL SELECT 'outcome', outcome_id::text, 1, content_hash FROM cognitive_os.routing_outcomes UNION ALL SELECT 'statistics', statistics_id::text, 1, content_hash FROM cognitive_os.routing_statistics UNION ALL SELECT 'experiment', experiment_id::text, 1, content_hash FROM cognitive_os.routing_experiments UNION ALL SELECT 'access', access_id::text, 1, content_hash FROM cognitive_os.routing_accesses) history ORDER BY kind, identity, revision" | sha256sum | awk '{print $1}')"
semantic_history_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(history)::text FROM (SELECT claim_id, revision, previous_revision, object_json, belief_status, valid_from, valid_to, recorded_at, content_hash FROM cognitive_os.semantic_claim_revisions ORDER BY claim_id, revision) history" | sha256sum | awk '{print $1}')"
semantic_as_of_sha256="$(psql "$database_cli_url" -Atqc "SELECT row_to_json(result)::text FROM (SELECT q.claim_id, q.valid_at, q.known_at, visible.revision, visible.content_hash FROM (SELECT DISTINCT claim_id, valid_from AS valid_at, recorded_at AS known_at FROM cognitive_os.semantic_claim_revisions) q LEFT JOIN LATERAL (SELECT revision, content_hash FROM cognitive_os.semantic_claim_revisions r WHERE r.claim_id=q.claim_id AND r.recorded_at<=q.known_at AND r.valid_from<=q.valid_at AND (r.valid_to IS NULL OR r.valid_to>q.valid_at) ORDER BY r.revision DESC LIMIT 1) visible ON true ORDER BY q.claim_id, q.valid_at, q.known_at) result" | sha256sum | awk '{print $1}')"
psql "$database_cli_url" -Atqc "SELECT json_build_object('content_hash', b.content_hash, 'size_bytes', b.size_bytes, 'storage_key', b.storage_key)::text FROM cognitive_os.artifact_blobs b JOIN cognitive_os.artifacts a ON a.content_hash=b.content_hash GROUP BY b.content_hash, b.size_bytes, b.storage_key ORDER BY b.storage_key" | uv run python scripts/artifact_restore_verify.py "$COGOS_ARTIFACT_ROOT"
uv run python - "$manifest" "$timestamp" "$dump" "$archive" "$event_count" "$artifact_count" "$revision" "$COGOS_POSTGRES_DATABASE" "$memory_count" "$memory_revision_count" "$embedding_count" "$semantic_claim_count" "$semantic_revision_count" "$semantic_observation_count" "$semantic_evidence_count" "$semantic_relation_count" "$semantic_contradiction_count" "$wiki_page_count" "$wiki_revision_count" "$semantic_history_sha256" "$semantic_as_of_sha256" "$skill_count" "$skill_revision_count" "$skill_history_sha256" "$strategy_count" "$strategy_revision_count" "$strategy_edge_count" "$strategy_selection_count" "$strategy_outcome_count" "$strategy_access_count" "$strategy_history_sha256" "$experience_compilation_count" "$experience_source_count" "$experience_candidate_count" "$experience_decision_count" "$experience_access_count" "$experience_history_sha256" "$corpus_source_count" "$corpus_item_count" "$corpus_route_count" "$corpus_manifest_count" "$corpus_export_count" "$corpus_access_count" "$corpus_history_sha256" "$routing_profile_count" "$routing_profile_revision_count" "$routing_policy_count" "$routing_policy_revision_count" "$routing_observation_count" "$routing_decision_count" "$routing_outcome_count" "$routing_statistics_count" "$routing_experiment_count" "$routing_access_count" "$routing_history_sha256" <<'PY'
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
    semantic_as_of_sha256,
    skill_count,
    skill_revision_count,
    skill_history_sha256,
    strategy_count,
    strategy_revision_count,
    strategy_edge_count,
    strategy_selection_count,
    strategy_outcome_count,
    strategy_access_count,
    strategy_history_sha256,
    experience_compilation_count,
    experience_source_count,
    experience_candidate_count,
    experience_decision_count,
    experience_access_count,
    experience_history_sha256,
    corpus_source_count,
    corpus_item_count,
    corpus_route_count,
    corpus_manifest_count,
    corpus_export_count,
    corpus_access_count,
    corpus_history_sha256,
    routing_profile_count,
    routing_profile_revision_count,
    routing_policy_count,
    routing_policy_revision_count,
    routing_observation_count,
    routing_decision_count,
    routing_outcome_count,
    routing_statistics_count,
    routing_experiment_count,
    routing_access_count,
    routing_history_sha256,
) = sys.argv[1:]
digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
data = {
    "created_at": datetime.now(UTC).isoformat(),
    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "sprint_parent_baseline": "sprint-15-baseline",
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
    "semantic_as_of_sha256": semantic_as_of_sha256,
    "skill_count": int(skill_count),
    "skill_revision_count": int(skill_revision_count),
    "skill_history_sha256": skill_history_sha256,
    "strategy_count": int(strategy_count),
    "strategy_revision_count": int(strategy_revision_count),
    "strategy_edge_count": int(strategy_edge_count),
    "strategy_selection_count": int(strategy_selection_count),
    "strategy_outcome_count": int(strategy_outcome_count),
    "strategy_access_count": int(strategy_access_count),
    "strategy_history_sha256": strategy_history_sha256,
    "experience_compilation_count": int(experience_compilation_count),
    "experience_source_count": int(experience_source_count),
    "experience_candidate_count": int(experience_candidate_count),
    "experience_decision_count": int(experience_decision_count),
    "experience_access_count": int(experience_access_count),
    "experience_history_sha256": experience_history_sha256,
    "corpus_source_count": int(corpus_source_count),
    "corpus_item_count": int(corpus_item_count),
    "corpus_route_count": int(corpus_route_count),
    "corpus_manifest_count": int(corpus_manifest_count),
    "corpus_export_count": int(corpus_export_count),
    "corpus_access_count": int(corpus_access_count),
    "corpus_history_sha256": corpus_history_sha256,
    "routing_profile_count": int(routing_profile_count),
    "routing_profile_revision_count": int(routing_profile_revision_count),
    "routing_policy_count": int(routing_policy_count),
    "routing_policy_revision_count": int(routing_policy_revision_count),
    "routing_observation_count": int(routing_observation_count),
    "routing_decision_count": int(routing_decision_count),
    "routing_outcome_count": int(routing_outcome_count),
    "routing_statistics_count": int(routing_statistics_count),
    "routing_experiment_count": int(routing_experiment_count),
    "routing_access_count": int(routing_access_count),
    "routing_history_sha256": routing_history_sha256,
}
Path(manifest).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
chmod 0640 "$dump" "$dump.sha256" "$archive" "$archive.sha256" "$manifest"
echo "Backup manifest: $manifest"
