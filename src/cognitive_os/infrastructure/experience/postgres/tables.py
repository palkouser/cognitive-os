"""SQLAlchemy Core metadata for Experience Compiler tables."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

_COMPILATION_STATUSES = (
    "'requested','snapshot_created','reconstructing','assessing',"
    "'generating_candidates','completed','failed','cancelled'"
)
_CANDIDATE_STATUSES = "'proposed','validated','rejected','routed','superseded'"
_CANDIDATE_TYPES = (
    "'memory','semantic_observation','skill','strategy','failure_pattern',"
    "'routing_observation','benchmark_case','negative_example','corpus_item'"
)
_DECISION_TYPES = (
    "'completed','completed_with_warnings','insufficient_sources','invalid_sources',"
    "'unverifiable','rejected','failed','cancelled'"
)

experience_compilations = Table(
    "experience_compilations",
    metadata,
    Column("compilation_id", UUID(as_uuid=True), primary_key=True),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("idempotency_key", String(256), nullable=False, unique=True),
    Column("profile_id", Text, nullable=False),
    Column("profile_version", Integer, nullable=False),
    Column("profile_hash", String(64), nullable=False),
    Column("current_status", Text, nullable=False),
    Column("request_hash", String(64), nullable=False, unique=True),
    Column("request_json", JSONB, nullable=False),
    Column("manifest_hash", String(64), nullable=True, unique=True),
    Column("manifest_json", JSONB, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        f"current_status IN ({_COMPILATION_STATUSES})",
        name="ck_experience_compilation_status",
    ),
    CheckConstraint("profile_version > 0", name="ck_experience_profile_version"),
    CheckConstraint("profile_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_profile_hash"),
    CheckConstraint("request_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_request_hash"),
    CheckConstraint(
        "(manifest_hash IS NULL AND manifest_json IS NULL) OR "
        "(manifest_hash ~ '^[0-9a-f]{64}$' AND manifest_json IS NOT NULL)",
        name="ck_experience_manifest_pair",
    ),
)

experience_sources = Table(
    "experience_sources",
    metadata,
    Column("compilation_id", UUID(as_uuid=True), primary_key=True),
    Column("source_order", Integer, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("source_hash", String(64), nullable=False),
    Column("scope", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("required", Boolean, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "compilation_id",
        "source_type",
        "source_id",
        "source_revision",
        name="uq_experience_source_identity",
    ),
    CheckConstraint("source_order >= 0 AND source_order < 512", name="ck_experience_source_order"),
    CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_source_hash"),
)

experience_snapshots = Table(
    "experience_snapshots",
    metadata,
    Column("compilation_id", UUID(as_uuid=True), primary_key=True),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("snapshot_hash", String(64), nullable=False, unique=True),
    Column("terminal_state", Text, nullable=False),
    Column("completeness", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("snapshot_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_snapshot_hash"),
)

experience_step_assessments = Table(
    "experience_step_assessments",
    metadata,
    Column("compilation_id", UUID(as_uuid=True), primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("step_id", Text, nullable=False),
    Column("assessment_hash", String(64), nullable=False, unique=True),
    Column("confidence", Numeric(5, 4), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("sequence > 0", name="ck_experience_assessment_sequence"),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_experience_confidence"),
)

experience_candidates = Table(
    "experience_candidates",
    metadata,
    Column("candidate_id", UUID(as_uuid=True), primary_key=True),
    Column("compilation_id", UUID(as_uuid=True), nullable=False),
    Column("candidate_type", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("target_subsystem", Text, nullable=False),
    Column("target_schema_version", Text, nullable=False),
    Column("candidate_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("current_revision > 0", name="ck_experience_candidate_revision"),
    CheckConstraint(
        f"current_status IN ({_CANDIDATE_STATUSES})", name="ck_experience_candidate_status"
    ),
    CheckConstraint(f"candidate_type IN ({_CANDIDATE_TYPES})", name="ck_experience_candidate_type"),
)

experience_candidate_revisions = Table(
    "experience_candidate_revisions",
    metadata,
    Column("candidate_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_status", Text, nullable=True),
    Column("status", Text, nullable=False),
    Column("actor_id", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("revision_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["candidate_id"],
        [f"{SCHEMA_NAME}.experience_candidates.candidate_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("revision > 0", name="ck_experience_candidate_history_revision"),
    CheckConstraint(
        f"status IN ({_CANDIDATE_STATUSES})", name="ck_experience_candidate_history_status"
    ),
)

experience_candidate_sources = Table(
    "experience_candidate_sources",
    metadata,
    Column("candidate_id", UUID(as_uuid=True), primary_key=True),
    Column("candidate_revision", Integer, primary_key=True),
    Column("source_order", Integer, primary_key=True),
    Column("compilation_id", UUID(as_uuid=True), nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("source_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["candidate_id", "candidate_revision"],
        [
            f"{SCHEMA_NAME}.experience_candidate_revisions.candidate_id",
            f"{SCHEMA_NAME}.experience_candidate_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "source_order >= 0 AND source_order < 128", name="ck_experience_candidate_source_order"
    ),
)

experience_decisions = Table(
    "experience_decisions",
    metadata,
    Column("compilation_id", UUID(as_uuid=True), primary_key=True),
    Column("decision", Text, nullable=False),
    Column("decision_hash", String(64), nullable=False, unique=True),
    Column("verifier_bundle_id", UUID(as_uuid=True), nullable=False),
    Column("verifier_bundle_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("decision_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_decision_hash"),
    CheckConstraint("verifier_bundle_hash ~ '^[0-9a-f]{64}$'", name="ck_experience_verifier_hash"),
    CheckConstraint(f"decision IN ({_DECISION_TYPES})", name="ck_experience_decision_type"),
)

experience_accesses = Table(
    "experience_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("compilation_id", UUID(as_uuid=True), nullable=False),
    Column("access_type", Text, nullable=False),
    Column("source_type", Text, nullable=True),
    Column("source_id", Text, nullable=True),
    Column("candidate_id", UUID(as_uuid=True), nullable=True),
    Column("actor_id", Text, nullable=False),
    Column("access_hash", String(64), nullable=False, unique=True),
    Column("accessed_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["compilation_id"],
        [f"{SCHEMA_NAME}.experience_compilations.compilation_id"],
        ondelete="RESTRICT",
    ),
)

Index(
    "ix_experience_compilations_task",
    experience_compilations.c.task_run_id,
    experience_compilations.c.created_at,
)
Index(
    "ix_experience_compilations_profile",
    experience_compilations.c.profile_id,
    experience_compilations.c.profile_version,
)
Index(
    "ix_experience_sources_identity",
    experience_sources.c.source_type,
    experience_sources.c.source_id,
    experience_sources.c.source_revision,
)
Index(
    "ix_experience_candidates_type_status",
    experience_candidates.c.candidate_type,
    experience_candidates.c.current_status,
)
Index(
    "ix_experience_candidates_target",
    experience_candidates.c.target_subsystem,
    experience_candidates.c.target_schema_version,
)
Index(
    "ix_experience_candidate_sources_identity",
    experience_candidate_sources.c.source_type,
    experience_candidate_sources.c.source_id,
)
Index(
    "ix_experience_decisions_type",
    experience_decisions.c.decision,
    experience_decisions.c.created_at,
)
Index(
    "ix_experience_accesses_time",
    experience_accesses.c.compilation_id,
    experience_accesses.c.accessed_at,
)

EXPERIENCE_TABLES = (
    experience_compilations,
    experience_sources,
    experience_snapshots,
    experience_step_assessments,
    experience_candidates,
    experience_candidate_revisions,
    experience_candidate_sources,
    experience_decisions,
    experience_accesses,
)

EXPERIENCE_HISTORY_TABLES = (
    experience_sources,
    experience_snapshots,
    experience_step_assessments,
    experience_candidate_revisions,
    experience_candidate_sources,
    experience_decisions,
    experience_accesses,
)
