"""SQLAlchemy Core metadata for governed memory tables."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.types import UserDefinedType

from cognitive_os.infrastructure.postgres.tables import SCHEMA_NAME, metadata


class VectorType(UserDefinedType[object]):
    """Dependency-free SQL type declaration for pgvector's variable vector type."""

    cache_ok = True

    def get_col_spec(self, **_kw: object) -> str:
        return "vector"


memory_items = Table(
    "memory_items",
    metadata,
    Column("memory_id", UUID(as_uuid=True), primary_key=True),
    Column("idempotency_key", String(64), nullable=False, unique=True),
    Column("memory_type", Text, nullable=False),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("current_revision", Integer, nullable=False),
    Column("title", String(1024), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    CheckConstraint("length(scope_id) > 0", name="ck_memory_items_scope_id"),
    CheckConstraint("idempotency_key ~ '^[0-9a-f]{64}$'", name="ck_memory_items_idempotency_key"),
    CheckConstraint("current_revision > 0", name="ck_memory_items_revision"),
    CheckConstraint(
        "memory_type IN ('episode','observation','decision','correction','task_summary',"
        "'code_context','verification_summary','failure_pattern','user_instruction')",
        name="ck_memory_items_type",
    ),
    CheckConstraint(
        "scope_type IN ('global','project','repository','task','session','domain')",
        name="ck_memory_items_scope_type",
    ),
    CheckConstraint(
        "status IN ('candidate','verified','superseded','retracted','expired')",
        name="ck_memory_items_status",
    ),
)

memory_revisions = Table(
    "memory_revisions",
    metadata,
    Column("memory_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("content_json", JSONB, nullable=False),
    Column(
        "content_artifact_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.artifacts.artifact_id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("content_hash", String(64), nullable=False),
    Column("search_text", Text, nullable=False),
    Column(
        "search_document",
        TSVECTOR,
        Computed("to_tsvector('english'::regconfig, search_text)", persisted=True),
        nullable=False,
    ),
    Column("status", Text, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("salience", Float, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("created_by_type", Text, nullable=False),
    Column("created_by_id", Text, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=True),
    Column("successor_memory_id", UUID(as_uuid=True), nullable=True),
    ForeignKeyConstraint(
        ["memory_id"],
        [f"{SCHEMA_NAME}.memory_items.memory_id"],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["memory_id", "previous_revision"],
        [
            f"{SCHEMA_NAME}.memory_revisions.memory_id",
            f"{SCHEMA_NAME}.memory_revisions.revision",
        ],
        ondelete="RESTRICT",
        name="fk_memory_revisions_previous",
    ),
    CheckConstraint("revision > 0", name="ck_memory_revisions_positive"),
    CheckConstraint(
        "(revision = 1 AND previous_revision IS NULL) OR previous_revision = revision - 1",
        name="ck_memory_revisions_sequence",
    ),
    CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_memory_confidence"),
    CheckConstraint("salience >= 0 AND salience <= 1", name="ck_memory_salience"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_memory_content_hash"),
    CheckConstraint("octet_length(search_text) <= 32768", name="ck_memory_search_text_size"),
    CheckConstraint(
        "sensitivity IN ('public','internal','confidential','restricted')",
        name="ck_memory_sensitivity",
    ),
)

memory_sources = Table(
    "memory_sources",
    metadata,
    Column("memory_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("source_order", Integer, primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_id", UUID(as_uuid=True), nullable=True),
    Column("source_memory_id", UUID(as_uuid=True), nullable=True),
    Column("source_memory_revision", Integer, nullable=True),
    Column("source_hash", String(64), nullable=False),
    Column("relationship", String(128), nullable=False),
    ForeignKeyConstraint(
        ["memory_id", "revision"],
        [f"{SCHEMA_NAME}.memory_revisions.memory_id", f"{SCHEMA_NAME}.memory_revisions.revision"],
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["source_memory_id", "source_memory_revision"],
        [f"{SCHEMA_NAME}.memory_revisions.memory_id", f"{SCHEMA_NAME}.memory_revisions.revision"],
        ondelete="RESTRICT",
        name="fk_memory_sources_memory_revision",
    ),
    UniqueConstraint(
        "memory_id",
        "revision",
        "source_type",
        "source_id",
        "source_memory_id",
        "source_memory_revision",
        name="uq_memory_source_identity",
        postgresql_nulls_not_distinct=True,
    ),
    CheckConstraint("source_order >= 0 AND source_order < 64", name="ck_memory_source_order"),
    CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="ck_memory_source_hash"),
    CheckConstraint(
        "(source_type = 'memory_revision' AND source_id IS NULL AND "
        "source_memory_id IS NOT NULL AND source_memory_revision IS NOT NULL) OR "
        "(source_type <> 'memory_revision' AND source_id IS NOT NULL AND "
        "source_memory_id IS NULL AND source_memory_revision IS NULL)",
        name="ck_memory_source_identity_shape",
    ),
)

memory_embeddings = Table(
    "memory_embeddings",
    metadata,
    Column("embedding_id", UUID(as_uuid=True), primary_key=True),
    Column("memory_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("provider_id", String(256), nullable=False),
    Column("model_id", String(256), nullable=False),
    Column("dimension", Integer, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("embedding", VectorType(), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["memory_id", "revision"],
        [f"{SCHEMA_NAME}.memory_revisions.memory_id", f"{SCHEMA_NAME}.memory_revisions.revision"],
        ondelete="RESTRICT",
    ),
    UniqueConstraint(
        "memory_id",
        "revision",
        "provider_id",
        "model_id",
        "content_hash",
        name="uq_memory_embedding_revision_model",
    ),
    CheckConstraint("dimension > 0 AND dimension <= 4096", name="ck_memory_embedding_dimension"),
    CheckConstraint("vector_dims(embedding) = dimension", name="ck_memory_embedding_vector_dims"),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_memory_embedding_hash"),
)

memory_accesses = Table(
    "memory_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("query_id", UUID(as_uuid=True), nullable=False),
    Column("task_run_id", UUID(as_uuid=True), nullable=True),
    Column("memory_id", UUID(as_uuid=True), nullable=False),
    Column("revision", Integer, nullable=False),
    Column("retrieval_mode", Text, nullable=False),
    Column("retrieval_rank", Integer, nullable=False),
    Column("retrieval_score", Float, nullable=False),
    Column("accessed_at", DateTime(timezone=True), nullable=False),
    Column("used_in_context", Integer, nullable=False, server_default="0"),
    Column("scope_type", Text, nullable=False),
    Column("scope_id", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("query_hash", String(64), nullable=False),
    Column("filter_hash", String(64), nullable=False),
    ForeignKeyConstraint(
        ["memory_id", "revision"],
        [f"{SCHEMA_NAME}.memory_revisions.memory_id", f"{SCHEMA_NAME}.memory_revisions.revision"],
        ondelete="RESTRICT",
    ),
    CheckConstraint("retrieval_mode IN ('metadata','text','vector')", name="ck_memory_access_mode"),
    CheckConstraint("retrieval_rank > 0", name="ck_memory_access_rank"),
    CheckConstraint("used_in_context IN (0, 1)", name="ck_memory_access_used"),
)

Index(
    "ix_memory_items_scope_status",
    memory_items.c.scope_type,
    memory_items.c.scope_id,
    memory_items.c.status,
)
Index("ix_memory_items_type", memory_items.c.memory_type)
Index("ix_memory_items_created", memory_items.c.created_at)
Index("ix_memory_items_current_revision", memory_items.c.memory_id, memory_items.c.current_revision)
Index("ix_memory_revisions_created", memory_revisions.c.created_at)
Index("ix_memory_revisions_search", memory_revisions.c.search_document, postgresql_using="gin")
Index("ix_memory_sources_identity", memory_sources.c.source_type, memory_sources.c.source_id)
Index(
    "ix_memory_sources_memory_identity",
    memory_sources.c.source_memory_id,
    memory_sources.c.source_memory_revision,
)
Index(
    "ix_memory_embeddings_model",
    memory_embeddings.c.provider_id,
    memory_embeddings.c.model_id,
    memory_embeddings.c.dimension,
    memory_embeddings.c.content_hash,
)
Index("ix_memory_accesses_query_time", memory_accesses.c.query_id, memory_accesses.c.accessed_at)
