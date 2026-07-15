import pytest

pytest.importorskip("sqlalchemy")

from cognitive_os.infrastructure.postgres.tables import (
    SCHEMA_NAME,
    artifact_blobs,
    artifacts,
    event_streams,
    events,
    metadata,
)


def test_core_metadata_uses_explicit_schema_and_tables() -> None:
    assert SCHEMA_NAME == "cognitive_os"
    assert {
        "cognitive_os.event_streams",
        "cognitive_os.events",
        "cognitive_os.artifact_blobs",
        "cognitive_os.artifacts",
    } <= set(metadata.tables)
    assert event_streams.primary_key.columns.keys() == ["stream_id"]
    assert events.primary_key.columns.keys() == ["global_position"]
    assert artifact_blobs.primary_key.columns.keys() == ["content_hash"]
    assert artifacts.primary_key.columns.keys() == ["artifact_id"]


def test_event_mapping_columns_and_constraints_are_complete() -> None:
    required = {
        "global_position",
        "event_id",
        "stream_id",
        "stream_type",
        "stream_version",
        "event_type",
        "schema_version",
        "occurred_at",
        "recorded_at",
        "stored_at",
        "correlation_id",
        "causation_event_id",
        "actor_json",
        "source_component",
        "payload_json",
        "payload_hash",
        "privacy_class",
        "trace_id",
        "span_id",
    }
    assert set(events.c.keys()) == required
    assert len(events.indexes) >= 6
    assert any(constraint.name == "uq_events_stream_version" for constraint in events.constraints)
