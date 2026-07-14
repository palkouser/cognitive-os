"""SQLAlchemy Core metadata for durable Cognitive OS storage."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

SCHEMA_NAME = "cognitive_os"
metadata = MetaData(schema=SCHEMA_NAME)

event_streams = Table(
    "event_streams",
    metadata,
    Column("stream_id", UUID(as_uuid=True), primary_key=True),
    Column("stream_type", Text, nullable=False),
    Column("current_version", BigInteger, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("current_version >= 0", name="ck_event_streams_current_version"),
    CheckConstraint("stream_type ~ '^[a-z][a-z0-9_]*$'", name="ck_event_streams_stream_type"),
)

events = Table(
    "events",
    metadata,
    Column("global_position", BigInteger, Identity(), primary_key=True),
    Column("event_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column(
        "stream_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.event_streams.stream_id", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("stream_type", Text, nullable=False),
    Column("stream_version", BigInteger, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("recorded_at", DateTime(timezone=True), nullable=False),
    Column(
        "stored_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.transaction_timestamp(),
    ),
    Column("correlation_id", UUID(as_uuid=True), nullable=False),
    Column(
        "causation_event_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.events.event_id", ondelete="RESTRICT"),
        nullable=True,
    ),
    Column("actor_json", JSONB, nullable=False),
    Column("source_component", Text, nullable=False),
    Column("payload_json", JSONB, nullable=False),
    Column("payload_hash", String(64), nullable=False),
    Column("privacy_class", Text, nullable=False),
    Column("trace_id", String(32), nullable=True),
    Column("span_id", String(16), nullable=True),
    UniqueConstraint("stream_id", "stream_version", name="uq_events_stream_version"),
    CheckConstraint("stream_version > 0", name="ck_events_stream_version"),
    CheckConstraint("schema_version > 0", name="ck_events_schema_version"),
    CheckConstraint("recorded_at >= occurred_at", name="ck_events_timestamp_order"),
    CheckConstraint("payload_hash ~ '^[0-9a-f]{64}$'", name="ck_events_payload_hash"),
    CheckConstraint("trace_id IS NULL OR trace_id ~ '^[0-9a-f]{32}$'", name="ck_events_trace_id"),
    CheckConstraint("span_id IS NULL OR span_id ~ '^[0-9a-f]{16}$'", name="ck_events_span_id"),
)
Index("ix_events_stream_version", events.c.stream_id, events.c.stream_version)
Index("ix_events_global_position", events.c.global_position)
Index("ix_events_correlation_id", events.c.correlation_id)
Index("ix_events_event_type_recorded_at", events.c.event_type, events.c.recorded_at)
Index("ix_events_recorded_at", events.c.recorded_at)
Index("ix_events_causation_event_id", events.c.causation_event_id)

artifact_blobs = Table(
    "artifact_blobs",
    metadata,
    Column("content_hash", String(64), primary_key=True),
    Column("size_bytes", BigInteger, nullable=False),
    Column("storage_key", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="ck_artifact_blobs_hash"),
    CheckConstraint("size_bytes >= 0", name="ck_artifact_blobs_size"),
)

artifacts = Table(
    "artifacts",
    metadata,
    Column("artifact_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "content_hash",
        String(64),
        ForeignKey(f"{SCHEMA_NAME}.artifact_blobs.content_hash", ondelete="RESTRICT"),
        nullable=False,
    ),
    Column("media_type", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column(
        "source_event_id",
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA_NAME}.events.event_id", ondelete="RESTRICT"),
        nullable=True,
    ),
)
Index("ix_artifacts_content_hash", artifacts.c.content_hash)
Index("ix_artifacts_source_event_id", artifacts.c.source_event_id)
