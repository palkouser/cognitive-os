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
corpus_source_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_sources') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_sources) END")"
corpus_item_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_items') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_items) END")"
corpus_route_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_route_decisions') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_route_decisions) END")"
corpus_manifest_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_manifests') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_manifests) END")"
corpus_export_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_exports') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_exports) END")"
corpus_access_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT CASE WHEN to_regclass('cognitive_os.corpus_accesses') IS NULL THEN 0 ELSE (SELECT count(*) FROM cognitive_os.corpus_accesses) END")"
corpus_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT NOT EXISTS (SELECT 1 FROM cognitive_os.corpus_item_sources s LEFT JOIN cognitive_os.corpus_items i USING (corpus_item_id) LEFT JOIN cognitive_os.corpus_sources c USING (source_manifest_id) WHERE i.corpus_item_id IS NULL OR c.source_manifest_id IS NULL) AND NOT EXISTS (SELECT 1 FROM cognitive_os.corpus_exports e LEFT JOIN cognitive_os.corpus_manifests m ON m.corpus_id=e.corpus_id AND m.revision=e.corpus_revision WHERE m.corpus_id IS NULL)")"
corpus_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT row_to_json(history)::text FROM (SELECT corpus_item_id, current_revision, current_status, canonical_content_hash, item_hash FROM cognitive_os.corpus_items ORDER BY corpus_item_id) history" | sha256sum | awk '{print $1}')"
routing_profile_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.model_capability_profiles")"
routing_profile_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.model_capability_revisions")"
routing_policy_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_policies")"
routing_policy_revision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_policy_revisions")"
routing_observation_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_observations")"
routing_decision_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_decisions")"
routing_outcome_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_outcomes")"
routing_statistics_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_statistics")"
routing_experiment_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_experiments")"
routing_access_count="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT count(*) FROM cognitive_os.routing_accesses")"
routing_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT NOT EXISTS (SELECT 1 FROM cognitive_os.model_capability_profiles p LEFT JOIN cognitive_os.model_capability_revisions r ON r.model_identity_hash=p.model_identity_hash AND r.revision=p.current_revision WHERE r.model_identity_hash IS NULL OR r.profile_hash<>p.current_profile_hash) AND NOT EXISTS (SELECT 1 FROM cognitive_os.routing_policies p LEFT JOIN cognitive_os.routing_policy_revisions r ON r.policy_id=p.policy_id AND r.revision=p.current_revision WHERE r.policy_id IS NULL OR r.policy_hash<>p.current_policy_hash) AND NOT EXISTS (SELECT 1 FROM cognitive_os.routing_outcomes o LEFT JOIN cognitive_os.routing_decisions d USING (decision_id) WHERE d.decision_id IS NULL)")"
routing_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT kind, identity, revision, content_hash FROM (SELECT 'profile' kind, model_identity_hash identity, revision, profile_hash content_hash FROM cognitive_os.model_capability_revisions UNION ALL SELECT 'policy', policy_id, revision, policy_hash FROM cognitive_os.routing_policy_revisions UNION ALL SELECT 'observation', observation_id::text, 1, content_hash FROM cognitive_os.routing_observations UNION ALL SELECT 'decision', decision_id::text, 1, content_hash FROM cognitive_os.routing_decisions UNION ALL SELECT 'outcome', outcome_id::text, 1, content_hash FROM cognitive_os.routing_outcomes UNION ALL SELECT 'statistics', statistics_id::text, 1, content_hash FROM cognitive_os.routing_statistics UNION ALL SELECT 'experiment', experiment_id::text, 1, content_hash FROM cognitive_os.routing_experiments UNION ALL SELECT 'access', access_id::text, 1, content_hash FROM cognitive_os.routing_accesses) history ORDER BY kind, identity, revision" | sha256sum | awk '{print $1}')"
weakness_counts_json="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('mining_runs',(SELECT count(*) FROM cognitive_os.weakness_mining_runs),'signals',(SELECT count(*) FROM cognitive_os.weakness_signals),'groups_and_clusters',(SELECT count(*) FROM cognitive_os.weakness_clusters),'cluster_members',(SELECT count(*) FROM cognitive_os.weakness_cluster_members),'weaknesses',(SELECT count(*) FROM cognitive_os.weakness_items),'revisions',(SELECT count(*) FROM cognitive_os.weakness_revisions),'sources_and_packages',(SELECT count(*) FROM cognitive_os.weakness_sources),'impact_scores',(SELECT count(*) FROM cognitive_os.weakness_impact_scores),'queue_records',(SELECT count(*) FROM cognitive_os.weakness_queue),'accesses',(SELECT count(*) FROM cognitive_os.weakness_accesses))")"
weakness_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT NOT EXISTS (SELECT 1 FROM cognitive_os.weakness_revisions r LEFT JOIN cognitive_os.weakness_items i USING (weakness_id) WHERE i.weakness_id IS NULL) AND NOT EXISTS (SELECT 1 FROM cognitive_os.weakness_queue q LEFT JOIN cognitive_os.weakness_items i USING (weakness_id) WHERE q.record_kind='entry' AND i.weakness_id IS NULL)")"
weakness_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT kind, identity, revision, content_hash FROM (SELECT 'run' kind, mining_run_id::text identity, 1 revision, request_hash content_hash FROM cognitive_os.weakness_mining_runs UNION ALL SELECT 'signal', signal_id::text, 1, content_hash FROM cognitive_os.weakness_signals UNION ALL SELECT 'cluster', cluster_id::text, revision, content_hash FROM cognitive_os.weakness_clusters UNION ALL SELECT 'member', member_id::text, 1, content_hash FROM cognitive_os.weakness_cluster_members UNION ALL SELECT 'weakness', weakness_id::text, current_revision, current_revision_hash FROM cognitive_os.weakness_items UNION ALL SELECT 'revision', weakness_id::text, revision, revision_hash FROM cognitive_os.weakness_revisions UNION ALL SELECT 'source', source_record_id::text, 1, content_hash FROM cognitive_os.weakness_sources UNION ALL SELECT 'impact', impact_score_id::text, 1, content_hash FROM cognitive_os.weakness_impact_scores UNION ALL SELECT 'queue', queue_record_id::text, 1, content_hash FROM cognitive_os.weakness_queue UNION ALL SELECT 'access', access_id::text, 1, content_hash FROM cognitive_os.weakness_accesses) history ORDER BY kind, identity, revision" | sha256sum | awk '{print $1}')"
proposal_counts_json="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('proposals',(SELECT count(*) FROM cognitive_os.harness_proposals),'revisions',(SELECT count(*) FROM cognitive_os.harness_proposal_revisions),'sources',(SELECT count(*) FROM cognitive_os.harness_proposal_sources),'alternatives',(SELECT count(*) FROM cognitive_os.harness_proposal_alternatives),'risks',(SELECT count(*) FROM cognitive_os.harness_proposal_risks),'validation_plans',(SELECT count(*) FROM cognitive_os.harness_proposal_validation_plans),'rollback_plans',(SELECT count(*) FROM cognitive_os.harness_proposal_rollback_plans),'reviews',(SELECT count(*) FROM cognitive_os.harness_proposal_reviews),'queue_records',(SELECT count(*) FROM cognitive_os.harness_proposal_queue),'accesses',(SELECT count(*) FROM cognitive_os.harness_proposal_accesses))")"
proposal_integrity="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT NOT EXISTS (SELECT 1 FROM cognitive_os.harness_proposal_revisions r LEFT JOIN cognitive_os.harness_proposals p USING (proposal_id) WHERE p.proposal_id IS NULL) AND NOT EXISTS (SELECT 1 FROM cognitive_os.harness_proposals p LEFT JOIN cognitive_os.harness_proposal_revisions r ON r.proposal_id=p.proposal_id AND r.revision=p.current_revision WHERE r.proposal_id IS NULL OR r.content_hash<>p.current_content_hash)")"
proposal_history_sha256="$(psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT kind, identity, revision, content_hash FROM (SELECT 'proposal' kind, proposal_id::text identity, current_revision revision, current_content_hash content_hash FROM cognitive_os.harness_proposals UNION ALL SELECT 'revision', proposal_id::text, revision, content_hash FROM cognitive_os.harness_proposal_revisions UNION ALL SELECT 'source', source_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_sources UNION ALL SELECT 'alternative', alternative_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_alternatives UNION ALL SELECT 'risk', risk_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_risks UNION ALL SELECT 'validation', validation_plan_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_validation_plans UNION ALL SELECT 'rollback', rollback_plan_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_rollback_plans UNION ALL SELECT 'review', review_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_reviews UNION ALL SELECT 'queue', queue_record_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_queue UNION ALL SELECT 'access', access_id::text, proposal_revision, content_hash FROM cognitive_os.harness_proposal_accesses) history ORDER BY kind, identity, revision" | sha256sum | awk '{print $1}')"
uv run python - "$manifest" "$semantic_observation_count" "$semantic_claim_count" "$semantic_revision_count" "$semantic_evidence_count" "$semantic_relation_count" "$semantic_contradiction_count" "$wiki_page_count" "$wiki_revision_count" "$semantic_history_sha256" "$semantic_as_of_sha256" "$skill_count" "$skill_revision_count" "$skill_history_sha256" "$strategy_count" "$strategy_revision_count" "$strategy_edge_count" "$strategy_selection_count" "$strategy_outcome_count" "$strategy_access_count" "$strategy_history_sha256" "$experience_compilation_count" "$experience_source_count" "$experience_candidate_count" "$experience_decision_count" "$experience_access_count" "$experience_history_sha256" "$corpus_source_count" "$corpus_item_count" "$corpus_route_count" "$corpus_manifest_count" "$corpus_export_count" "$corpus_access_count" "$corpus_history_sha256" "$routing_profile_count" "$routing_profile_revision_count" "$routing_policy_count" "$routing_policy_revision_count" "$routing_observation_count" "$routing_decision_count" "$routing_outcome_count" "$routing_statistics_count" "$routing_experiment_count" "$routing_access_count" "$routing_history_sha256" "$weakness_counts_json" "$weakness_history_sha256" "$proposal_counts_json" "$proposal_history_sha256" <<'PY'
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
corpus_values = tuple(map(int, sys.argv[28:34]))
corpus_history_hash = sys.argv[34]
routing_values = tuple(map(int, sys.argv[35:45]))
routing_history_hash = sys.argv[45]
weakness_counts = json.loads(sys.argv[46])
weakness_history_hash = sys.argv[47]
proposal_counts = json.loads(sys.argv[48])
proposal_history_hash = sys.argv[49]
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
corpus_keys = (
    "corpus_source_count",
    "corpus_item_count",
    "corpus_route_count",
    "corpus_manifest_count",
    "corpus_export_count",
    "corpus_access_count",
)
if any(manifest.get(key, 0) != value for key, value in zip(corpus_keys, corpus_values, strict=True)):
    raise SystemExit("restored corpus counts do not match the backup manifest")
if manifest.get("corpus_history_sha256") != corpus_history_hash:
    raise SystemExit("restored corpus item history differs from the backup manifest")
routing_keys = (
    "routing_profile_count",
    "routing_profile_revision_count",
    "routing_policy_count",
    "routing_policy_revision_count",
    "routing_observation_count",
    "routing_decision_count",
    "routing_outcome_count",
    "routing_statistics_count",
    "routing_experiment_count",
    "routing_access_count",
)
if any(manifest.get(key, 0) != value for key, value in zip(routing_keys, routing_values, strict=True)):
    raise SystemExit("restored routing counts do not match the backup manifest")
if manifest.get("routing_history_sha256") != routing_history_hash:
    raise SystemExit("restored routing history differs from the backup manifest")
if manifest.get("weakness_counts", {}) != weakness_counts:
    raise SystemExit("restored weakness counts do not match the backup manifest")
if manifest.get("weakness_history_sha256") != weakness_history_hash:
    raise SystemExit("restored weakness history differs from the backup manifest")
if manifest.get("proposal_counts", {}) != proposal_counts:
    raise SystemExit("restored proposal counts do not match the backup manifest")
if manifest.get("proposal_history_sha256") != proposal_history_hash:
    raise SystemExit("restored proposal history differs from the backup manifest")
PY
[[ -n "$revision" && "$event_count" =~ ^[0-9]+$ && "$artifact_count" =~ ^[0-9]+$ && "$memory_count" =~ ^[0-9]+$ && "$memory_integrity" == "t" && "$semantic_integrity" == "t" && "$semantic_lineage_integrity" == "t" && "$skill_integrity" == "t" && "$strategy_integrity" == "t" && "$experience_integrity" == "t" && "$corpus_integrity" == "t" && "$routing_integrity" == "t" && "$weakness_integrity" == "t" && "$proposal_integrity" == "t" ]]
psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('content_hash', b.content_hash, 'size_bytes', b.size_bytes, 'storage_key', b.storage_key)::text FROM cognitive_os.artifact_blobs b JOIN cognitive_os.artifacts a ON a.content_hash=b.content_hash GROUP BY b.content_hash, b.size_bytes, b.storage_key ORDER BY b.storage_key" | uv run python scripts/artifact_restore_verify.py "$restore_root"
psql "$COGOS_RESTORE_DATABASE_URL" -Atqc "SELECT json_build_object('content_hash', w.content_hash, 'markdown_base64', replace(encode(convert_to(w.markdown, 'UTF8'), 'base64'), E'\\n', ''), 'snapshot_hash', w.snapshot_hash, 'claim_refs', COALESCE((SELECT json_agg(json_build_object('claim', json_build_object('claim_id', c.claim_id, 'revision', c.claim_revision), 'section', c.section, 'display_order', c.display_order) ORDER BY c.section, c.display_order) FROM cognitive_os.wiki_page_claims c WHERE c.page_id=w.page_id AND c.page_revision=w.revision), '[]'::json))::text FROM cognitive_os.wiki_page_revisions w ORDER BY w.page_id, w.revision" | uv run python scripts/wiki_restore_verify.py
echo "Isolated restore verification passed."
