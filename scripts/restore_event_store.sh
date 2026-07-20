#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/postgres_common.sh
source "$(dirname "${BASH_SOURCE[0]}")/postgres_common.sh"
load_postgres_environment
[[ "${1:-}" == "--test-restore" ]] || { echo "Only --test-restore is supported." >&2; exit 1; }
for command in psql sha256sum zstd tar; do require_command "$command"; done
if [[ -n "${COGOS_POSTGRES_TOOL_CONTAINER:-}" ]]; then
  require_command docker
  require_value COGOS_CONTAINER_RESTORE_DATABASE_URL
else
  require_command pg_restore
fi
for name in COGOS_RESTORE_DATABASE_URL COGOS_RESTORE_DATABASE_NAME COGOS_DATABASE_BOOTSTRAP_URL; do require_value "$name"; done
require_value COGOS_POSTGRES_OWNER_USER
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
  -c "CREATE DATABASE \"$COGOS_RESTORE_DATABASE_NAME\" OWNER \"$COGOS_POSTGRES_OWNER_USER\""
if [[ -n "${COGOS_POSTGRES_TOOL_CONTAINER:-}" ]]; then
  docker exec -i "$COGOS_POSTGRES_TOOL_CONTAINER" \
    pg_restore --no-owner --exit-on-error --dbname="$COGOS_CONTAINER_RESTORE_DATABASE_URL" \
    < "$dump"
else
  pg_restore --no-owner --exit-on-error --dbname="$COGOS_RESTORE_DATABASE_URL" "$dump"
fi
restore_root="$(mktemp -d)"
trap 'rm -rf "$restore_root"' EXIT
zstd -q -dc "$archive" | tar -xf - -C "$restore_root"
revision="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT version_num FROM alembic_version LIMIT 1')"
event_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT count(*) FROM cognitive_os.events')"
artifact_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc 'SELECT count(*) FROM cognitive_os.artifacts')"
memory_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.memory_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.memory_items) END")"
memory_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.memory_revisions') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.memory_items i LEFT JOIN cognitive_os.memory_revisions r ON r.memory_id=i.memory_id AND r.revision=i.current_revision WHERE r.memory_id IS NULL OR r.status<>i.status) AND NOT EXISTS (SELECT 1 FROM cognitive_os.memory_revisions r WHERE r.content_hash !~ '^[0-9a-f]{64}$' OR (r.revision=1 AND r.previous_revision IS NOT NULL) OR (r.revision>1 AND r.previous_revision<>r.revision-1)) END")"
semantic_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_revisions') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.semantic_claims c LEFT JOIN cognitive_os.semantic_claim_revisions r ON r.claim_id=c.claim_id AND r.revision=c.current_revision WHERE r.claim_id IS NULL OR r.belief_status<>c.current_belief_status) AND NOT EXISTS (SELECT 1 FROM cognitive_os.semantic_claim_revisions WHERE valid_to IS NOT NULL AND valid_to<=valid_from) END")"
semantic_observation_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_observations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_observations) END")"
semantic_claim_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claims') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claims) END")"
semantic_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_revisions) END")"
semantic_evidence_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_evidence') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_evidence) END")"
semantic_relation_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_claim_relations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_claim_relations) END")"
semantic_contradiction_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.semantic_contradictions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.semantic_contradictions) END")"
wiki_page_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.wiki_pages') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.wiki_pages) END")"
wiki_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.wiki_page_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.wiki_page_revisions) END")"
semantic_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(history)::text FROM (SELECT claim_id, revision, previous_revision, object_json, belief_status, valid_from, valid_to, recorded_at, content_hash FROM cognitive_os.semantic_claim_revisions ORDER BY claim_id, revision) history" | sha256sum | awk '{print $1}')"
semantic_as_of_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(result)::text FROM (SELECT q.claim_id, q.valid_at, q.known_at, visible.revision, visible.content_hash FROM (SELECT DISTINCT claim_id, valid_from AS valid_at, recorded_at AS known_at FROM cognitive_os.semantic_claim_revisions) q LEFT JOIN LATERAL (SELECT revision, content_hash FROM cognitive_os.semantic_claim_revisions r WHERE r.claim_id=q.claim_id AND r.recorded_at<=q.known_at AND r.valid_from<=q.valid_at AND (r.valid_to IS NULL OR r.valid_to>q.valid_at) ORDER BY r.revision DESC LIMIT 1) visible ON true ORDER BY q.claim_id, q.valid_at, q.known_at) result" | sha256sum | awk '{print $1}')"
semantic_lineage_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.wiki_page_claims') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.semantic_contradictions c LEFT JOIN cognitive_os.semantic_contradiction_revisions r ON r.contradiction_id=c.contradiction_id AND r.revision=c.current_revision WHERE r.contradiction_id IS NULL OR r.status<>c.current_status) AND NOT EXISTS (SELECT 1 FROM cognitive_os.wiki_pages p LEFT JOIN cognitive_os.wiki_page_revisions r ON r.page_id=p.page_id AND r.revision=p.current_revision WHERE p.current_revision>0 AND r.page_id IS NULL) AND NOT EXISTS (SELECT 1 FROM cognitive_os.wiki_page_claims w LEFT JOIN cognitive_os.semantic_claim_revisions r ON r.claim_id=w.claim_id AND r.revision=w.claim_revision WHERE r.claim_id IS NULL) END")"
skill_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.skill_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.skill_items) END")"
skill_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.skill_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.skill_revisions) END")"
skill_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.skill_revisions') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.skill_items i LEFT JOIN cognitive_os.skill_revisions r ON r.skill_id=i.skill_id AND r.revision=i.current_revision WHERE r.skill_id IS NULL OR r.status<>i.current_status) AND NOT EXISTS (SELECT 1 FROM cognitive_os.skill_revisions r LEFT JOIN cognitive_os.skill_package_artifacts p ON p.skill_id=r.skill_id AND p.revision=r.revision WHERE p.skill_id IS NULL OR p.package_hash<>r.package_hash) END")"
skill_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(history)::text FROM (SELECT skill_id, revision, previous_revision, status, package_hash, content_hash FROM cognitive_os.skill_revisions ORDER BY skill_id, revision) history" | sha256sum | awk '{print $1}')"
strategy_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_items) END")"
strategy_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_revisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_revisions) END")"
strategy_edge_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_edges') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_edges) END")"
strategy_selection_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_selections') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_selections) END")"
strategy_outcome_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_outcomes') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_outcomes) END")"
strategy_access_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.strategy_accesses) END")"
strategy_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.strategy_revisions') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.strategy_items i LEFT JOIN cognitive_os.strategy_revisions r ON r.strategy_id=i.strategy_id AND r.revision=i.current_revision WHERE r.strategy_id IS NULL OR r.status<>i.current_status) AND NOT EXISTS (SELECT 1 FROM cognitive_os.strategy_outcomes o LEFT JOIN cognitive_os.strategy_selections s ON s.selection_id=o.selection_id WHERE s.selection_id IS NULL) END")"
strategy_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(history)::text FROM (SELECT strategy_id, revision, previous_revision, status, content_hash FROM cognitive_os.strategy_revisions ORDER BY strategy_id, revision) history" | sha256sum | awk '{print $1}')"
experience_compilation_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_compilations') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_compilations) END")"
experience_source_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_sources') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_sources) END")"
experience_candidate_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_candidates') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_candidates) END")"
experience_decision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_decisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_decisions) END")"
experience_access_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.experience_accesses) END")"
experience_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.experience_snapshots') IS NULL THEN true ELSE NOT EXISTS (SELECT 1 FROM cognitive_os.experience_compilations c LEFT JOIN cognitive_os.experience_snapshots s USING (compilation_id) WHERE c.current_status='completed' AND s.compilation_id IS NULL) AND NOT EXISTS (SELECT 1 FROM cognitive_os.experience_candidates c LEFT JOIN cognitive_os.experience_candidate_revisions r ON r.candidate_id=c.candidate_id AND r.revision=c.current_revision WHERE r.candidate_id IS NULL OR r.status<>c.current_status) END")"
experience_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(history)::text FROM (SELECT compilation_id, snapshot_hash, terminal_state, completeness FROM cognitive_os.experience_snapshots ORDER BY compilation_id) history" | sha256sum | awk '{print $1}')"
uv run python - "$manifest" "$semantic_observation_count" "$semantic_claim_count" "$semantic_revision_count" "$semantic_evidence_count" "$semantic_relation_count" "$semantic_contradiction_count" "$wiki_page_count" "$wiki_revision_count" "$semantic_history_sha256" "$semantic_as_of_sha256" "$skill_count" "$skill_revision_count" "$skill_history_sha256" "$strategy_count" "$strategy_revision_count" "$strategy_edge_count" "$strategy_selection_count" "$strategy_outcome_count" "$strategy_access_count" "$strategy_history_sha256" "$experience_compilation_count" "$experience_source_count" "$experience_candidate_count" "$experience_decision_count" "$experience_access_count" "$experience_history_sha256" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
keys = (
    "semantic_observation_count",
    "semantic_claim_count",
    "semantic_revision_count",
    "semantic_evidence_count",
    "semantic_relation_count",
    "semantic_contradiction_count",
    "wiki_page_count",
    "wiki_revision_count",
)
history_hash, as_of_hash = sys.argv[10:12]
skill_count, skill_revision_count, skill_history_hash = sys.argv[12:15]
strategy_values = tuple(map(int, sys.argv[15:21]))
strategy_history_hash = sys.argv[21]
experience_values = tuple(map(int, sys.argv[22:27]))
experience_history_hash = sys.argv[27]
actual = dict(zip(keys, map(int, sys.argv[2:10]), strict=True))
if any(manifest.get(key, 0) != value for key, value in actual.items()):
    raise SystemExit("restored semantic counts do not match the backup manifest")
if manifest.get("semantic_history_sha256") != history_hash:
    raise SystemExit("restored historical semantic query differs from the backup manifest")
if manifest.get("semantic_as_of_sha256") != as_of_hash:
    raise SystemExit("restored as-of query revisions differ from the backup manifest")
if manifest.get("skill_count", 0) != int(skill_count):
    raise SystemExit("restored skill count does not match the backup manifest")
if manifest.get("skill_revision_count", 0) != int(skill_revision_count):
    raise SystemExit("restored skill revision count does not match the backup manifest")
if manifest.get("skill_history_sha256") != skill_history_hash:
    raise SystemExit("restored skill history differs from the backup manifest")
strategy_keys = (
    "strategy_count",
    "strategy_revision_count",
    "strategy_edge_count",
    "strategy_selection_count",
    "strategy_outcome_count",
    "strategy_access_count",
)
if any(manifest.get(key, 0) != value for key, value in zip(strategy_keys, strategy_values, strict=True)):
    raise SystemExit("restored strategy counts do not match the backup manifest")
if manifest.get("strategy_history_sha256") != strategy_history_hash:
    raise SystemExit("restored strategy history differs from the backup manifest")
experience_keys = (
    "experience_compilation_count",
    "experience_source_count",
    "experience_candidate_count",
    "experience_decision_count",
    "experience_access_count",
)
if any(manifest.get(key, 0) != value for key, value in zip(experience_keys, experience_values, strict=True)):
    raise SystemExit("restored experience counts do not match the backup manifest")
if manifest.get("experience_history_sha256") != experience_history_hash:
    raise SystemExit("restored experience snapshot history differs from the backup manifest")
PY
[[ -n "$revision" && "$event_count" =~ ^[0-9]+$ && "$artifact_count" =~ ^[0-9]+$ && "$memory_count" =~ ^[0-9]+$ && "$memory_integrity" == "t" && "$semantic_integrity" == "t" && "$semantic_lineage_integrity" == "t" && "$skill_integrity" == "t" && "$strategy_integrity" == "t" && "$experience_integrity" == "t" ]]
psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('content_hash', b.content_hash, 'size_bytes', b.size_bytes, 'storage_key', b.storage_key)::text FROM cognitive_os.artifact_blobs b JOIN cognitive_os.artifacts a ON a.content_hash=b.content_hash GROUP BY b.content_hash, b.size_bytes, b.storage_key ORDER BY b.storage_key" | uv run python scripts/artifact_restore_verify.py "$restore_root"
psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('content_hash', w.content_hash, 'markdown_base64', replace(encode(convert_to(w.markdown, 'UTF8'), 'base64'), E'\\n', ''), 'snapshot_hash', w.snapshot_hash, 'claim_refs', COALESCE((SELECT json_agg(json_build_object('claim', json_build_object('claim_id', c.claim_id, 'revision', c.claim_revision), 'section', c.section, 'display_order', c.display_order) ORDER BY c.section, c.display_order) FROM cognitive_os.wiki_page_claims c WHERE c.page_id=w.page_id AND c.page_revision=w.revision), '[]'::json))::text FROM cognitive_os.wiki_page_revisions w ORDER BY w.page_id, w.revision" | uv run python scripts/wiki_restore_verify.py
echo "Isolated restore verification passed."
