from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.domain import new_id
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.storage import AppendResult, StoredEvent, StoredEventDecoder


def test_stored_event_and_append_result_validate() -> None:
    envelope = EventEnvelope.model_validate_json(
        Path("tests/fixtures/contracts/v1/task-created-envelope.json").read_bytes()
    )
    stored = StoredEvent(
        global_position=1,
        stored_at=datetime(2026, 7, 14, tzinfo=UTC),
        envelope=envelope,
    )
    result = AppendResult(
        stream_id=envelope.stream_id,
        previous_stream_version=0,
        current_stream_version=1,
        event_ids=(envelope.event_id,),
        global_positions=(1,),
        stored_at=stored.stored_at,
    )
    assert result.current_stream_version == 1
    assert StoredEventDecoder(build_default_event_catalog()).decode_stored_event(stored).payload


@pytest.mark.parametrize(
    ("trace_id", "span_id"),
    [("a" * 31, "b" * 16), ("a" * 32, None), ("A" * 32, "b" * 16)],
)
def test_stored_event_rejects_invalid_trace_context(trace_id, span_id) -> None:
    envelope = EventEnvelope.model_validate_json(
        Path("tests/fixtures/contracts/v1/task-created-envelope.json").read_bytes()
    )
    with pytest.raises(ValidationError):
        StoredEvent(
            global_position=1,
            stored_at=datetime.now(UTC),
            envelope=envelope,
            trace_id=trace_id,
            span_id=span_id,
        )


def test_append_result_rejects_inconsistent_positions() -> None:
    with pytest.raises(ValidationError):
        AppendResult(
            stream_id=new_id(),
            previous_stream_version=0,
            current_stream_version=2,
            event_ids=(new_id(), new_id()),
            global_positions=(2, 1),
            stored_at=datetime.now(UTC),
        )
