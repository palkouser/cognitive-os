"""SQLAlchemy Core metadata for governed weakness mining."""

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

weakness_mining_runs = Table(
    "weakness_mining_runs",
    metadata,
    Column("mining_run_id", UUID(as_uuid=True), primary_key=True),
    Column("idempotency_key", Text, nullable=False, unique=True),
    Column("scope", Text, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("request_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

weakness_signals = Table(
    "weakness_signals",
    metadata,
    Column("signal_id", UUID(as_uuid=True), primary_key=True),
    Column("mining_run_id", UUID(as_uuid=True), nullable=False),
    Column("weakness_type", Text, nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=False),
    Column("signature_hash", String(64), nullable=False),
    Column("component_identity", Text, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["mining_run_id"], [f"{SCHEMA_NAME}.weakness_mining_runs.mining_run_id"]),
)

weakness_clusters = Table(
    "weakness_clusters",
    metadata,
    Column("cluster_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("snapshot_hash", String(64), nullable=False),
    Column("signature_hash", String(64), nullable=True),
    Column("cluster_method", Text, nullable=False),
    Column("authoritative", Boolean, nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("revision > 0", name="ck_weakness_clusters_revision"),
)

weakness_cluster_members = Table(
    "weakness_cluster_members",
    metadata,
    Column("member_id", UUID(as_uuid=True), primary_key=True),
    Column("cluster_id", UUID(as_uuid=True), nullable=False),
    Column("cluster_revision", Integer, nullable=False),
    Column("signal_id", UUID(as_uuid=True), nullable=True),
    Column("group_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["cluster_id", "cluster_revision"],
        [
            f"{SCHEMA_NAME}.weakness_clusters.cluster_id",
            f"{SCHEMA_NAME}.weakness_clusters.revision",
        ],
    ),
    ForeignKeyConstraint(["signal_id"], [f"{SCHEMA_NAME}.weakness_signals.signal_id"]),
)

weakness_items = Table(
    "weakness_items",
    metadata,
    Column("weakness_id", UUID(as_uuid=True), primary_key=True),
    Column("canonical_name", Text, nullable=False),
    Column("weakness_type", Text, nullable=False),
    Column("signature_hash", String(64), nullable=False),
    Column("scope", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("current_revision_hash", String(64), nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("current_revision > 0", name="ck_weakness_items_revision"),
)

weakness_revisions = Table(
    "weakness_revisions",
    metadata,
    Column("weakness_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("status", Text, nullable=False),
    Column("revision_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["weakness_id"], [f"{SCHEMA_NAME}.weakness_items.weakness_id"]),
    CheckConstraint("revision > 0", name="ck_weakness_revisions_revision"),
)

weakness_sources = Table(
    "weakness_sources",
    metadata,
    Column("source_record_id", UUID(as_uuid=True), primary_key=True),
    Column("mining_run_id", UUID(as_uuid=True), nullable=True),
    Column("record_kind", Text, nullable=False),
    Column("source_type", Text, nullable=False),
    Column("source_identity", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("source_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["mining_run_id"], [f"{SCHEMA_NAME}.weakness_mining_runs.mining_run_id"]),
    UniqueConstraint(
        "record_kind",
        "source_type",
        "source_identity",
        "source_revision",
        name="uq_weakness_source_exact_identity",
    ),
)

weakness_impact_scores = Table(
    "weakness_impact_scores",
    metadata,
    Column("impact_score_id", UUID(as_uuid=True), primary_key=True),
    Column("weakness_id", UUID(as_uuid=True), nullable=True),
    Column("weakness_revision", Integer, nullable=True),
    Column("group_snapshot_hash", String(64), nullable=False),
    Column("priority", Text, nullable=False),
    Column("final_score", Numeric(7, 4), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("final_score >= 0 AND final_score <= 100", name="ck_weakness_impact_score"),
)

weakness_queue = Table(
    "weakness_queue",
    metadata,
    Column("queue_record_id", UUID(as_uuid=True), primary_key=True),
    Column("record_kind", Text, nullable=False),
    Column("weakness_id", UUID(as_uuid=True), nullable=True),
    Column("weakness_revision", Integer, nullable=True),
    Column("priority", Text, nullable=True),
    Column("status", Text, nullable=True),
    Column("policy_hash", String(64), nullable=False),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint(
        "record_kind",
        "weakness_id",
        "weakness_revision",
        "policy_hash",
        name="uq_weakness_queue_revision_policy",
    ),
)

weakness_accesses = Table(
    "weakness_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("access_type", Text, nullable=False),
    Column("subject_id", Text, nullable=False),
    Column("subject_revision", Integer, nullable=True),
    Column("content_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

Index(
    "ix_weakness_mining_scope_created",
    weakness_mining_runs.c.scope,
    weakness_mining_runs.c.created_at,
)
Index(
    "ix_weakness_signal_type_task",
    weakness_signals.c.weakness_type,
    weakness_signals.c.task_run_id,
)
Index("ix_weakness_signal_signature", weakness_signals.c.signature_hash)
Index("ix_weakness_signal_component", weakness_signals.c.component_identity)
Index("ix_weakness_cluster_snapshot", weakness_clusters.c.snapshot_hash)
Index("ix_weakness_cluster_member_group", weakness_cluster_members.c.group_hash)
Index("ix_weakness_item_status", weakness_items.c.current_status, weakness_items.c.weakness_type)
Index(
    "ix_weakness_impact_priority",
    weakness_impact_scores.c.priority,
    weakness_impact_scores.c.final_score,
)
Index("ix_weakness_queue_priority", weakness_queue.c.priority, weakness_queue.c.status)
Index(
    "ix_weakness_source_identity",
    weakness_sources.c.source_type,
    weakness_sources.c.source_identity,
)
Index("ix_weakness_access_created", weakness_accesses.c.created_at)

WEAKNESS_TABLES = (
    weakness_mining_runs,
    weakness_signals,
    weakness_clusters,
    weakness_cluster_members,
    weakness_items,
    weakness_revisions,
    weakness_sources,
    weakness_impact_scores,
    weakness_queue,
    weakness_accesses,
)

WEAKNESS_HISTORY_TABLES = (
    weakness_signals,
    weakness_clusters,
    weakness_cluster_members,
    weakness_revisions,
    weakness_sources,
    weakness_impact_scores,
    weakness_queue,
    weakness_accesses,
)
