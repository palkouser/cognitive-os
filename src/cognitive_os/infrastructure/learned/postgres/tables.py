"""SQLAlchemy Core metadata for the durable learned evidence store.

Eight tables: one mutable projection and seven append-only ledgers. The split is the
authority model from ADR 0086 made structural — the projection can be rebuilt from
`learned_component_revisions`, so it is derived data, while every ledger is evidence and
is protected by an append-only trigger.

No table stores artifact bytes. `learned_artifacts` holds lineage that references the
existing `artifacts` table, so content addressing, deduplication and backup coverage
keep working unchanged.
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

#: Allowlisted values, mirrored as database CHECK constraints. The domain enum and the
#: constraint must agree; `test_learned_evidence_tables` asserts that they do.
LEARNED_COMPONENT_STATES = (
    "registered",
    "shadow",
    "verified",
    "active",
    "disabled",
    "retracted",
)
LEARNED_EVIDENCE_KINDS = (
    "prediction",
    "shadow_result",
    "mandatory_path_invariance",
    "forgetting_assessment",
    "distribution_comparison",
    "retrieval_capacity",
    "baseline_ladder",
    "out_of_distribution_assessment",
    "promotion_assessment",
)
LEARNED_OBSERVATION_STATUSES = ("accepted", "quarantined", "rejected")
LEARNED_OBSERVATION_ATTRIBUTIONS = ("direct", "contributing", "unknown")
LEARNED_PROVENANCE_CLASSES = ("self_play", "real_governed_run", "operator_supplied")
LEARNED_ACTIVATION_ACTIONS = ("approval", "activation", "disable", "rollback")
LEARNED_ARTIFACT_ROLES = (
    "dataset",
    "split_manifest",
    "example_manifest",
    "model",
    "report",
    "metric_bundle",
)
LEARNED_CORPUS_ROLES = ("training", "evaluation")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    rendered = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({rendered})"


#: The mutable current-state projection. Derived from `learned_component_revisions`;
#: `cogos_app` never writes it directly.
learned_components = Table(
    "learned_components",
    metadata,
    Column("component_id", Text, primary_key=True),
    Column("surface", Text, nullable=False),
    Column("descriptor_version", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_state", String(32), nullable=False),
    Column("descriptor_hash", String(64), nullable=False),
    Column("artifact_lineage_id", UUID(as_uuid=True), nullable=True),
    Column("content_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("current_state", LEARNED_COMPONENT_STATES), name="ck_learned_state"),
    CheckConstraint("current_revision >= 1", name="ck_learned_revision_positive"),
    Index("ix_learned_components_surface", "surface"),
    # One active component per surface, enforced by the database rather than by hope.
    Index(
        "uq_learned_components_active_surface",
        "surface",
        unique=True,
        postgresql_where=Column("current_state") == "active",
    ),
    schema=SCHEMA_NAME,
)

#: Append-only lifecycle history. This is the authority for learned state.
learned_component_revisions = Table(
    "learned_component_revisions",
    metadata,
    Column("component_id", Text, nullable=False, primary_key=True),
    Column("revision", Integer, nullable=False, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("surface", Text, nullable=False),
    Column("state_before", String(32), nullable=True),
    Column("state_after", String(32), nullable=False),
    Column("descriptor_hash", String(64), nullable=False),
    Column("artifact_lineage_id", UUID(as_uuid=True), nullable=True),
    Column("promotion_assessment_hash", String(64), nullable=True),
    Column("activation_approval_hash", String(64), nullable=True),
    Column("rollback_target_revision", Integer, nullable=True),
    Column("actor", Text, nullable=False),
    Column("authority", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("state_after", LEARNED_COMPONENT_STATES), name="ck_learned_rev_after"),
    CheckConstraint(
        f"state_before IS NULL OR {_in_list('state_before', LEARNED_COMPONENT_STATES)}",
        name="ck_learned_rev_before",
    ),
    CheckConstraint("revision >= 1", name="ck_learned_rev_positive"),
    CheckConstraint(
        "previous_revision IS NULL OR previous_revision < revision",
        name="ck_learned_rev_predecessor",
    ),
    # Reaching ACTIVE without naming both pieces of evidence is refused in the contract
    # and again here, because the database is the last line that a buggy caller meets.
    CheckConstraint(
        "state_after <> 'active' OR "
        "(promotion_assessment_hash IS NOT NULL AND activation_approval_hash IS NOT NULL)",
        name="ck_learned_rev_active_needs_evidence",
    ),
    UniqueConstraint("idempotency_key", name="uq_learned_revision_idempotency"),
    Index("ix_learned_revisions_surface", "surface"),
    schema=SCHEMA_NAME,
)

#: Append-only dataset snapshot metadata. Example bodies stay in the Artifact Store.
learned_datasets = Table(
    "learned_datasets",
    metadata,
    Column("dataset_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, nullable=False),
    Column("surface", Text, nullable=False),
    Column("corpus_role", String(32), nullable=False),
    Column("feature_schema_hash", String(64), nullable=False),
    Column("split_manifest_artifact_id", UUID(as_uuid=True), nullable=True),
    Column("split_manifest_hash", String(64), nullable=False),
    Column("example_manifest_artifact_id", UUID(as_uuid=True), nullable=True),
    Column("example_manifest_hash", String(64), nullable=False),
    Column("provenance_counts", JSONB, nullable=False),
    Column("observation_count", Integer, nullable=False),
    # Boolean rather than a 0/1 integer: the contract field is a bool, and a column that
    # needs a conversion on every read and write is a lossy mapping waiting to drift.
    Column("usage_rights_verified", Boolean, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("corpus_role", LEARNED_CORPUS_ROLES), name="ck_learned_corpus_role"),
    CheckConstraint("observation_count >= 0", name="ck_learned_dataset_count"),
    # The training exclusion, in the database as well as the contract. A real governed
    # run reaching a training snapshot would silently contaminate every later
    # distribution measurement, so it must be impossible rather than merely refused.
    CheckConstraint(
        "corpus_role <> 'training' OR NOT (provenance_counts ? 'real_governed_run')",
        name="ck_learned_training_excludes_real_runs",
    ),
    CheckConstraint(
        "corpus_role <> 'training' OR usage_rights_verified",
        name="ck_learned_training_rights",
    ),
    Index("ix_learned_datasets_surface", "surface"),
    schema=SCHEMA_NAME,
)

#: Append-only lineage into the existing content-addressed Artifact Store.
learned_artifacts = Table(
    "learned_artifacts",
    metadata,
    Column("lineage_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "artifact_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("role", String(32), nullable=False),
    Column("component_id", Text, nullable=True),
    Column("dataset_id", UUID(as_uuid=True), nullable=True),
    Column("media_type", Text, nullable=False),
    Column("declared_format", Text, nullable=False),
    Column("declared_content_hash", String(64), nullable=False),
    Column("observed_content_hash", String(64), nullable=False),
    Column("size_bytes", Integer, nullable=False),
    Column("producing_evidence_hash", String(64), nullable=True),
    Column("verified_by", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("verified_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("role", LEARNED_ARTIFACT_ROLES), name="ck_learned_artifact_role"),
    CheckConstraint("size_bytes >= 0", name="ck_learned_artifact_size"),
    CheckConstraint(
        "declared_content_hash = observed_content_hash",
        name="ck_learned_artifact_hash_agrees",
    ),
    CheckConstraint(
        "component_id IS NOT NULL OR dataset_id IS NOT NULL",
        name="ck_learned_artifact_owner",
    ),
    Index("ix_learned_artifacts_component", "component_id"),
    Index("ix_learned_artifacts_artifact", "artifact_id"),
    schema=SCHEMA_NAME,
)

#: One append-only typed evidence table rather than one per contract. See ADR 0086.
learned_evidence_records = Table(
    "learned_evidence_records",
    metadata,
    Column("evidence_id", UUID(as_uuid=True), primary_key=True),
    Column("evidence_kind", String(48), nullable=False),
    Column("component_id", Text, nullable=True),
    Column("dataset_id", UUID(as_uuid=True), nullable=True),
    Column("surface", Text, nullable=False),
    Column("source_run_id", UUID(as_uuid=True), nullable=True),
    Column("schema_version", Text, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("payload_artifact_id", UUID(as_uuid=True), nullable=True),
    Column("payload_json", JSONB, nullable=False),
    Column("recorded_by", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("evidence_kind", LEARNED_EVIDENCE_KINDS), name="ck_learned_ev_kind"),
    CheckConstraint(
        "component_id IS NOT NULL OR dataset_id IS NOT NULL", name="ck_learned_ev_owner"
    ),
    Index("ix_learned_evidence_component_kind", "component_id", "evidence_kind"),
    schema=SCHEMA_NAME,
)

#: Append-only governed-outcome intake and quarantine ledger.
learned_observations = Table(
    "learned_observations",
    metadata,
    Column("observation_id", UUID(as_uuid=True), primary_key=True),
    Column("surface", Text, nullable=False),
    Column("source_kind", Text, nullable=False),
    Column("source_task_id", UUID(as_uuid=True), nullable=True),
    Column("source_run_id", UUID(as_uuid=True), nullable=True),
    Column("source_event_id", UUID(as_uuid=True), nullable=True),
    Column("source_payload_hash", String(64), nullable=False),
    Column("provenance_class", String(32), nullable=False),
    Column("attribution", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("verifier_status", Text, nullable=True),
    Column("verifier_evidence_hash", String(64), nullable=True),
    Column("usage_rights_verified", Boolean, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("decision_reason", Text, nullable=False),
    Column("evaluation_eligible", Boolean, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("status", LEARNED_OBSERVATION_STATUSES), name="ck_learned_obs_status"),
    CheckConstraint(
        _in_list("attribution", LEARNED_OBSERVATION_ATTRIBUTIONS), name="ck_learned_obs_attr"
    ),
    CheckConstraint(
        _in_list("provenance_class", LEARNED_PROVENANCE_CLASSES), name="ck_learned_obs_prov"
    ),
    CheckConstraint(
        "status <> 'accepted' OR (usage_rights_verified AND attribution <> 'unknown')",
        name="ck_learned_obs_accept_needs_rights",
    ),
    CheckConstraint(
        "NOT evaluation_eligible OR status = 'accepted'", name="ck_learned_obs_eligible"
    ),
    UniqueConstraint("idempotency_key", name="uq_learned_observation_idempotency"),
    Index("ix_learned_observations_status", "surface", "status"),
    schema=SCHEMA_NAME,
)

#: Append-only activation authority and receipt ledger.
learned_activation_history = Table(
    "learned_activation_history",
    metadata,
    Column("receipt_id", UUID(as_uuid=True), primary_key=True),
    Column("action", String(32), nullable=False),
    Column("component_id", Text, nullable=False),
    Column("component_revision", Integer, nullable=False),
    Column("surface", Text, nullable=False),
    Column("artifact_lineage_id", UUID(as_uuid=True), nullable=True),
    Column("promotion_assessment_hash", String(64), nullable=True),
    Column("approval_id", UUID(as_uuid=True), nullable=True),
    Column("approval_hash", String(64), nullable=True),
    Column("previous_receipt_id", UUID(as_uuid=True), nullable=True),
    Column("rollback_target_receipt_id", UUID(as_uuid=True), nullable=True),
    Column("actor", Text, nullable=False),
    Column("authority", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("idempotency_key", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(_in_list("action", LEARNED_ACTIVATION_ACTIONS), name="ck_learned_act_action"),
    CheckConstraint("component_revision >= 1", name="ck_learned_act_revision"),
    # An activation must name all four pieces of evidence; nothing else may name a
    # rollback target.
    CheckConstraint(
        "action <> 'activation' OR (artifact_lineage_id IS NOT NULL "
        "AND promotion_assessment_hash IS NOT NULL AND approval_id IS NOT NULL "
        "AND approval_hash IS NOT NULL)",
        name="ck_learned_act_activation_evidence",
    ),
    CheckConstraint(
        "(action = 'rollback') = (rollback_target_receipt_id IS NOT NULL)",
        name="ck_learned_act_rollback_target",
    ),
    UniqueConstraint("idempotency_key", name="uq_learned_activation_idempotency"),
    Index("ix_learned_activation_surface", "surface", "recorded_at"),
    schema=SCHEMA_NAME,
)

#: Append-only approvals, kept separate so an approval can be audited without reading
#: the activation it authorised.
learned_activation_approvals = Table(
    "learned_activation_approvals",
    metadata,
    Column("approval_id", UUID(as_uuid=True), primary_key=True),
    Column("component_id", Text, nullable=False),
    Column("component_revision", Integer, nullable=False),
    Column("surface", Text, nullable=False),
    Column("promotion_assessment_hash", String(64), nullable=False),
    Column("artifact_lineage_id", UUID(as_uuid=True), nullable=False),
    Column("approved", Boolean, nullable=False),
    Column("approver", Text, nullable=False),
    Column("approver_kind", String(32), nullable=False),
    Column("reason", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("approved_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    # A model or provider identity cannot approve. Refused in the contract and here.
    CheckConstraint(
        "NOT approved OR approver_kind = 'human_operator'",
        name="ck_learned_approval_human_only",
    ),
    Index("ix_learned_approvals_component", "component_id", "component_revision"),
    schema=SCHEMA_NAME,
)

#: Append-only read and export audit. Carries no sensitive example body.
learned_accesses = Table(
    "learned_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("actor", Text, nullable=False),
    Column("authority", Text, nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=False),
    Column("purpose", Text, nullable=False),
    Column("decision", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Index("ix_learned_accesses_target", "target_type", "target_id"),
    schema=SCHEMA_NAME,
)

#: Every table migration 0014 creates, in dependency order.
LEARNED_EVIDENCE_TABLES = (
    learned_components,
    learned_component_revisions,
    learned_datasets,
    learned_artifacts,
    learned_evidence_records,
    learned_observations,
    learned_activation_approvals,
    learned_activation_history,
    learned_accesses,
)

#: The append-only ledgers. `learned_components` is absent on purpose: it is a derived
#: projection, so it is the one table a controlled function may update.
LEARNED_APPEND_ONLY_TABLES = tuple(
    table for table in LEARNED_EVIDENCE_TABLES if table.name != "learned_components"
)
