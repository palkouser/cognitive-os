"""SQLAlchemy Core metadata for governed strategy tables."""

from sqlalchemy import (
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

_STATUS = "'draft','staged','verified','deprecated','superseded','retracted'"
_TARGETS = ",".join(
    f"'{value}'"
    for value in (
        "strategy_revision",
        "problem_class",
        "failure_mode",
        "phase",
        "skill_revision",
        "tool",
        "model_role",
        "verifier",
        "context_profile",
        "task_run",
        "controller_plan",
        "context_bundle",
        "correction_event",
        "acceptance_decision",
        "outcome",
        "artifact",
        "semantic_claim_revision",
    )
)

strategy_items = Table(
    "strategy_items",
    metadata,
    Column("strategy_id", UUID(as_uuid=True), primary_key=True),
    Column("canonical_name", String(256), nullable=False),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("problem_class_id", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("identity_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "canonical_name", "scope_type", "scope_id", name="uq_strategy_items_name_scope"
    ),
    CheckConstraint("length(btrim(canonical_name)) > 0", name="ck_strategy_name_nonempty"),
    CheckConstraint("current_revision > 0", name="ck_strategy_items_revision"),
    CheckConstraint(f"current_status IN ({_STATUS})", name="ck_strategy_items_status"),
    CheckConstraint("idempotency_key ~ '^[0-9a-f]{64}$'", name="ck_strategy_items_key"),
)

strategy_revisions = Table(
    "strategy_revisions",
    metadata,
    Column("strategy_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("status", Text, nullable=False),
    Column("problem_class_id", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["strategy_id"], [f"{SCHEMA_NAME}.strategy_items.strategy_id"], ondelete="RESTRICT"
    ),
    ForeignKeyConstraint(
        ["strategy_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_strategy_revisions_previous",
    ),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_strategy_revisions_sequence",
    ),
    CheckConstraint(f"status IN ({_STATUS})", name="ck_strategy_revisions_status"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_strategy_revision_hash"),
)

strategy_sources = Table(
    "strategy_sources",
    metadata,
    Column("strategy_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("source_order", Integer, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("content_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["strategy_id", "revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    CheckConstraint("source_order >= 0 AND source_order < 64", name="ck_strategy_source_order"),
)

strategy_edges = Table(
    "strategy_edges",
    metadata,
    Column("edge_id", UUID(as_uuid=True), primary_key=True),
    Column("strategy_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("edge_type", Text, nullable=False),
    Column("target_type", Text, nullable=False),
    Column("target_id", Text, nullable=False),
    Column("target_revision", Text, nullable=False),
    Column("target_hash", String(64), nullable=False),
    Column("weight", Numeric(12, 9), nullable=False),
    Column("edge_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["strategy_id", "revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    UniqueConstraint("strategy_id", "revision", "edge_hash", name="uq_strategy_edge_hash"),
    CheckConstraint(f"target_type IN ({_TARGETS})", name="ck_strategy_edge_target_type"),
    CheckConstraint("weight >= -1 AND weight <= 1", name="ck_strategy_edge_weight"),
    CheckConstraint(
        "NOT (edge_type = 'supersedes' AND target_type = 'strategy_revision' "
        "AND target_id = strategy_id::text AND target_revision = revision::text)",
        name="ck_strategy_no_self_supersession",
    ),
)

strategy_selections = Table(
    "strategy_selections",
    metadata,
    Column("selection_id", UUID(as_uuid=True), primary_key=True),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("status", Text, nullable=False),
    Column("selected_strategy_id", UUID(as_uuid=True), nullable=True),
    Column("selected_revision", Integer, nullable=True),
    Column("decision_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["selected_strategy_id", "selected_revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    CheckConstraint(
        "(status = 'selected' AND selected_strategy_id IS NOT NULL "
        "AND selected_revision IS NOT NULL) OR "
        "(status <> 'selected' AND selected_strategy_id IS NULL "
        "AND selected_revision IS NULL)",
        name="ck_strategy_selection_result",
    ),
)

strategy_outcomes = Table(
    "strategy_outcomes",
    metadata,
    Column("outcome_id", UUID(as_uuid=True), primary_key=True),
    Column("execution_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("selection_id", UUID(as_uuid=True), nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("strategy_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("cohort_id", Text, nullable=False, server_default="all"),
    Column("status", Text, nullable=False),
    Column("outcome_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("finished_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["strategy_id", "revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["selection_id"],
        [f"{SCHEMA_NAME}.strategy_selections.selection_id"],
        ondelete="RESTRICT",
    ),
)

strategy_statistics = Table(
    "strategy_statistics",
    metadata,
    Column("strategy_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("cohort_id", Text, primary_key=True),
    Column("projection_revision", Integer, primary_key=True),
    Column("projection_hash", String(64), nullable=False, unique=True),
    Column("executions", Integer, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    ForeignKeyConstraint(
        ["strategy_id", "revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
    CheckConstraint("projection_revision > 0", name="ck_strategy_statistics_revision"),
    CheckConstraint("executions >= 0", name="ck_strategy_statistics_finite"),
)

strategy_accesses = Table(
    "strategy_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("strategy_id", UUID(as_uuid=True), nullable=False),
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
        ["strategy_id", "revision"],
        [
            f"{SCHEMA_NAME}.strategy_revisions.strategy_id",
            f"{SCHEMA_NAME}.strategy_revisions.revision",
        ],
        ondelete="RESTRICT",
    ),
)

Index(
    "ix_strategy_items_name_scope",
    strategy_items.c.canonical_name,
    strategy_items.c.scope_type,
    strategy_items.c.scope_id,
)
Index(
    "ix_strategy_items_problem_status",
    strategy_items.c.problem_class_id,
    strategy_items.c.current_status,
)
Index(
    "ix_strategy_revisions_problem",
    strategy_revisions.c.problem_class_id,
    strategy_revisions.c.status,
)
Index(
    "ix_strategy_sources_revision",
    strategy_sources.c.source_type,
    strategy_sources.c.source_id,
    strategy_sources.c.source_revision,
)
Index(
    "ix_strategy_edges_source",
    strategy_edges.c.strategy_id,
    strategy_edges.c.revision,
    strategy_edges.c.edge_type,
)
Index(
    "ix_strategy_edges_target",
    strategy_edges.c.target_type,
    strategy_edges.c.target_id,
    strategy_edges.c.target_revision,
)
Index(
    "ix_strategy_selections_task",
    strategy_selections.c.task_run_id,
    strategy_selections.c.created_at,
)
Index(
    "ix_strategy_outcomes_cohort",
    strategy_outcomes.c.strategy_id,
    strategy_outcomes.c.revision,
    strategy_outcomes.c.cohort_id,
)
Index(
    "ix_strategy_statistics_cohort",
    strategy_statistics.c.cohort_id,
    strategy_statistics.c.strategy_id,
    strategy_statistics.c.revision,
)
Index(
    "ix_strategy_accesses_time",
    strategy_accesses.c.strategy_id,
    strategy_accesses.c.revision,
    strategy_accesses.c.accessed_at,
)

STRATEGY_TABLES = (
    strategy_items,
    strategy_revisions,
    strategy_sources,
    strategy_edges,
    strategy_selections,
    strategy_outcomes,
    strategy_statistics,
    strategy_accesses,
)
STRATEGY_HISTORY_TABLES = STRATEGY_TABLES[1:]
