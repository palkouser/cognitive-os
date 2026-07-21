"""SQLAlchemy Core metadata for Corpus Factory tables."""

from sqlalchemy import (
    Column,
    DateTime,
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

corpus_sources = Table(
    "corpus_sources",
    metadata,
    Column("source_manifest_id", UUID(as_uuid=True), primary_key=True),
    Column("source_type", Text, nullable=False),
    Column("source_identity", Text, nullable=False),
    Column("source_revision", Text, nullable=False),
    Column("source_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("source_identity", "source_revision", name="uq_corpus_source_identity"),
)

corpus_items = Table(
    "corpus_items",
    metadata,
    Column("corpus_item_id", UUID(as_uuid=True), primary_key=True),
    Column("current_revision", Integer, nullable=False),
    Column("current_status", Text, nullable=False),
    Column("canonical_content_hash", String(64), nullable=False),
    Column("item_hash", String(64), nullable=False, unique=True),
    Column("scope", Text, nullable=False),
    Column("sensitivity", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("status_actor", Text, nullable=False),
    Column("status_reason", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

corpus_item_sources = Table(
    "corpus_item_sources",
    metadata,
    Column("corpus_item_id", UUID(as_uuid=True), primary_key=True),
    Column("source_manifest_id", UUID(as_uuid=True), primary_key=True),
    ForeignKeyConstraint(["corpus_item_id"], [f"{SCHEMA_NAME}.corpus_items.corpus_item_id"]),
    ForeignKeyConstraint(
        ["source_manifest_id"], [f"{SCHEMA_NAME}.corpus_sources.source_manifest_id"]
    ),
)

corpus_classifications = Table(
    "corpus_classifications",
    metadata,
    Column("classification_id", UUID(as_uuid=True), primary_key=True),
    Column("corpus_item_id", UUID(as_uuid=True), nullable=False),
    Column("item_revision", Integer, nullable=False),
    Column("content_type", Text, nullable=False),
    Column("classification_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["corpus_item_id"], [f"{SCHEMA_NAME}.corpus_items.corpus_item_id"]),
)

corpus_route_decisions = Table(
    "corpus_route_decisions",
    metadata,
    Column("route_decision_id", UUID(as_uuid=True), primary_key=True),
    Column("corpus_item_id", UUID(as_uuid=True), nullable=False),
    Column("item_revision", Integer, nullable=False),
    Column("destination", Text, nullable=False),
    Column("status", Text, nullable=False),
    Column("decision_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(["corpus_item_id"], [f"{SCHEMA_NAME}.corpus_items.corpus_item_id"]),
)

corpus_manifests = Table(
    "corpus_manifests",
    metadata,
    Column("corpus_id", UUID(as_uuid=True), primary_key=True),
    Column("revision", Integer, primary_key=True),
    Column("previous_revision", Integer, nullable=True),
    Column("purpose", Text, nullable=False),
    Column("manifest_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

corpus_manifest_items = Table(
    "corpus_manifest_items",
    metadata,
    Column("corpus_id", UUID(as_uuid=True), primary_key=True),
    Column("corpus_revision", Integer, primary_key=True),
    Column("corpus_item_id", UUID(as_uuid=True), primary_key=True),
    Column("item_revision", Integer, nullable=False),
    Column("item_hash", String(64), nullable=False),
    Column("split", Text, nullable=True),
    ForeignKeyConstraint(
        ["corpus_id", "corpus_revision"],
        [f"{SCHEMA_NAME}.corpus_manifests.corpus_id", f"{SCHEMA_NAME}.corpus_manifests.revision"],
    ),
    ForeignKeyConstraint(["corpus_item_id"], [f"{SCHEMA_NAME}.corpus_items.corpus_item_id"]),
)

corpus_exports = Table(
    "corpus_exports",
    metadata,
    Column("export_id", UUID(as_uuid=True), primary_key=True),
    Column("corpus_id", UUID(as_uuid=True), nullable=False),
    Column("corpus_revision", Integer, nullable=False),
    Column("export_type", Text, nullable=False),
    Column("export_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["corpus_id", "corpus_revision"],
        [f"{SCHEMA_NAME}.corpus_manifests.corpus_id", f"{SCHEMA_NAME}.corpus_manifests.revision"],
    ),
)

corpus_accesses = Table(
    "corpus_accesses",
    metadata,
    Column("access_id", UUID(as_uuid=True), primary_key=True),
    Column("source_manifest_id", UUID(as_uuid=True), nullable=True),
    Column("corpus_item_id", UUID(as_uuid=True), nullable=True),
    Column("corpus_id", UUID(as_uuid=True), nullable=True),
    Column("export_id", UUID(as_uuid=True), nullable=True),
    Column("access_type", Text, nullable=False),
    Column("access_hash", String(64), nullable=False, unique=True),
    Column("payload_json", JSONB, nullable=False),
    Column("accessed_at", DateTime(timezone=True), nullable=False),
)

Index(
    "ix_corpus_sources_identity", corpus_sources.c.source_identity, corpus_sources.c.source_revision
)
Index("ix_corpus_items_hash", corpus_items.c.canonical_content_hash)
Index("ix_corpus_items_status", corpus_items.c.current_status, corpus_items.c.created_at)
Index(
    "ix_corpus_routes_destination",
    corpus_route_decisions.c.destination,
    corpus_route_decisions.c.status,
)

CORPUS_TABLES = (
    corpus_sources,
    corpus_items,
    corpus_item_sources,
    corpus_classifications,
    corpus_route_decisions,
    corpus_manifests,
    corpus_manifest_items,
    corpus_exports,
    corpus_accesses,
)
CORPUS_HISTORY_TABLES = tuple(table for table in CORPUS_TABLES if table is not corpus_items)
