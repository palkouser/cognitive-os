import pytest

from cognitive_os.domain import PrivacyClass, StreamType, new_id
from cognitive_os.events import create_event_envelope
from cognitive_os.events.batches import validate_event_batch
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.task_events import TaskCreated
from cognitive_os.infrastructure.errors import InvalidEventBatchError


def make_event(task, actor, now, *, version=1, stream_id=None):
    return create_event_envelope(
        payload=TaskCreated(task=task),
        stream_id=stream_id or task.task_id,
        stream_type=StreamType.TASK,
        stream_version=version,
        correlation_id=new_id(),
        causation_event_id=None,
        actor=actor,
        source_component="batch-test",
        privacy_class=PrivacyClass.INTERNAL,
        occurred_at=now,
        recorded_at=now,
    )


def test_valid_batch_is_frozen_tuple(task, actor, now) -> None:
    event = make_event(task, actor, now)
    assert validate_event_batch(
        [event], expected_version=0, catalog=build_default_event_catalog()
    ) == (event,)


@pytest.mark.parametrize("expected_version", [-1, 1])
def test_invalid_expected_or_first_version_fails(task, actor, now, expected_version) -> None:
    with pytest.raises(InvalidEventBatchError):
        validate_event_batch(
            [make_event(task, actor, now)],
            expected_version=expected_version,
            catalog=build_default_event_catalog(),
        )


def test_empty_mixed_and_oversized_batches_fail(task, actor, now) -> None:
    catalog = build_default_event_catalog()
    with pytest.raises(InvalidEventBatchError):
        validate_event_batch([], expected_version=0, catalog=catalog)
    with pytest.raises(InvalidEventBatchError):
        validate_event_batch(
            [
                make_event(task, actor, now),
                make_event(task, actor, now, version=2, stream_id=new_id()),
            ],
            expected_version=0,
            catalog=catalog,
        )
    with pytest.raises(InvalidEventBatchError):
        validate_event_batch(
            [make_event(task, actor, now)],
            expected_version=0,
            catalog=catalog,
            maximum_batch_size=0,
        )
