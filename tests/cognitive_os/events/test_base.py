from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.domain import PrivacyClass, StreamType, new_id
from cognitive_os.events import create_event_envelope
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.task_events import TaskCreated


def test_typed_payload_creates_valid_envelope(task, actor, now) -> None:
    envelope = create_event_envelope(
        payload=TaskCreated(task=task),
        stream_id=task.task_id,
        stream_type=StreamType.TASK,
        stream_version=1,
        correlation_id=new_id(),
        causation_event_id=None,
        actor=actor,
        source_component="cognitive-os.contract-test",
        privacy_class=PrivacyClass.INTERNAL,
        occurred_at=now,
        recorded_at=now,
    )
    assert envelope.event_type == "task.created"
    assert envelope.schema_version == 1
    assert len(envelope.payload_hash) == 64
    assert EventEnvelope.model_validate_json(envelope.model_dump_json()) == envelope


def test_envelope_rejects_hash_tampering_and_invalid_time(task, actor, now) -> None:
    envelope = create_event_envelope(
        payload=TaskCreated(task=task),
        stream_id=task.task_id,
        stream_type=StreamType.TASK,
        stream_version=1,
        correlation_id=new_id(),
        causation_event_id=None,
        actor=actor,
        source_component="contract-test",
        privacy_class=PrivacyClass.INTERNAL,
        occurred_at=now,
        recorded_at=now,
    )
    with pytest.raises(ValidationError, match="hash mismatch"):
        EventEnvelope.model_validate({**envelope.model_dump(), "payload": {"tampered": True}})
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate(
            {**envelope.model_dump(), "recorded_at": now - timedelta(seconds=1)}
        )
