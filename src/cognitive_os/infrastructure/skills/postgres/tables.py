"""SQLAlchemy Core metadata for governed procedural skill tables."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata

skill_items = Table(
    "skill_items",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("canonical_name", String(256), nullable=False),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("identity_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("canonical_name", "scope_type", "scope_id", name="uq_skill_items_name_scope"),
    CheckConstraint("current_revision > 0", name="ck_skill_items_revision"),
    CheckConstraint("idempotency_key ~ '^[0-9a-f]{64}$'", name="ck_skill_items_key"),
    CheckConstraint(
        "current_status IN ('draft','staged','verified','deprecated','superseded','retracted')",
        name="ck_skill_items_status",
    ),
)

skill_revisions = Table(
    "skill_revisions",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("status", Text, nullable=False),
    Column("package_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("domains_json", JSONB, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["skill_id"], [f"{SCHEMA_NAME}.skill_items.skill_id"], ondelete="RESTRICT"
    ),
    ForeignKeyConstraint(
        ["skill_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_skill_revisions_previous",
    ),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_skill_revisions_sequence",
    ),
    CheckConstraint("package_hash ~ '^[0-9a-f]{64}$'", name="ck_skill_revision_package"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_skill_revision_content"),
)

skill_sources = Table(
    "skill_sources",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("source_order", Integer, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    CheckConstraint("source_order >= 0 AND source_order < 64", name="ck_skill_source_order"),
)

skill_requirements = Table(
    "skill_requirements",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("requirement_id", Text, primary_key=True),
    Column("requirement_type", Text, nullable=False),
    Column("capability_id", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

skill_package_artifacts = Table(
    "skill_package_artifacts",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column(
        "artifact_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("package_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

skill_executions = Table(
    "skill_executions",
    metadata,
    Column("execution_id", UUID(as_uuid=True), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("status", Text, nullable=False),
    Column("result_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

skill_execution_steps = Table(
    "skill_execution_steps",
    metadata,
    Column("execution_id", UUID(as_uuid=True), primary_key=True),
    Column("step_order", Integer, primary_key=True),
    Column("step_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["execution_id"],
        [f"{SCHEMA_NAME}.skill_executions.execution_id"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("step_order >= 0 AND step_order < 64", name="ck_skill_step_order"),
)

skill_statistics = Table(
    "skill_statistics",
    metadata,
    Column("skill_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("projection_revision", Integer, primary_key=True),
    Column("projection_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

skill_accesses = Table(
    "skill_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("skill_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("access_type", Text, nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=True),
    Column("context_request_id", UUID(as_uuid=True), nullable=True),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("accessed_at", DateTime(timezone=True), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["skill_id", "revision"],
        [
            f"{SCHEMA_NAME}.skill_revisions.skill_id",
            f"{SCHEMA_NAME}.skill_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

Index(
    "ix_skill_items_scope_status",
    skill_items.c.scope_type,
    skill_items.c.scope_id,
    skill_items.c.current_status,
)
Index("ix_skill_revisions_status", skill_revisions.c.status)
Index("ix_skill_revisions_domains", skill_revisions.c.domains_json, postgresql_using="gin")
Index("ix_skill_sources_identity", skill_sources.c.source_type, skill_sources.c.source_id)
Index(
    "ix_skill_requirements_capability",
    skill_requirements.c.requirement_type,
    skill_requirements.c.capability_id,
)
Index(
    "ix_skill_executions_skill",
    skill_executions.c.skill_id,
    skill_executions.c.revision,
    skill_executions.c.finished_at,
)
Index("ix_skill_executions_task", skill_executions.c.task_run_id, skill_executions.c.started_at)
Index(
    "ix_skill_accesses_skill_time",
    skill_accesses.c.skill_id,
    skill_accesses.c.revision,
    skill_accesses.c.accessed_at,
)

SKILL_TABLES = (
    skill_items,
    skill_revisions,
    skill_sources,
    skill_requirements,
    skill_package_artifacts,
    skill_executions,
    skill_execution_steps,
    skill_statistics,
    skill_accesses,
)
SKILL_HISTORY_TABLES = SKILL_TABLES[1:]
