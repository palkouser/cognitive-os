"""Pre-transaction event batch validation."""

from collections.abc import Sequence

from cognitive_os.infrastructure.errors import InvalidEventBatchError

from .base import EventEnvelope
from .catalog import EventCatalog, EventCatalogError
from .hashing import sha256_digest

DEFAULT_MAXIMUM_BATCH_SIZE = 256


def validate_event_batch(
    events: Sequence[EventEnvelope],
    *,
    expected_version: int,
    catalog: EventCatalog,
    maximum_batch_size: int = DEFAULT_MAXIMUM_BATCH_SIZE,
) -> tuple[EventEnvelope, ...]:
    batch = tuple(events)
    if not batch:
        raise InvalidEventBatchError("event batch must not be empty")
    if expected_version < 0:
        raise InvalidEventBatchError("expected_version must be non-negative")
    if maximum_batch_size < 1 or len(batch) > maximum_batch_size:
        raise InvalidEventBatchError(f"event batch exceeds maximum size {maximum_batch_size}")
    if any(not isinstance(event, EventEnvelope) for event in batch):
        raise InvalidEventBatchError("every batch item must be an EventEnvelope")
    stream_id = batch[0].stream_id
    stream_type = batch[0].stream_type
    if any(event.stream_id != stream_id for event in batch):
        raise InvalidEventBatchError("all events must have the same stream_id")
    if any(event.stream_type != stream_type for event in batch):
        raise InvalidEventBatchError("all events must have the same stream_type")
    if len({event.event_id for event in batch}) != len(batch):
        raise InvalidEventBatchError("event IDs must be unique within a batch")
    expected_versions = tuple(range(expected_version + 1, expected_version + len(batch) + 1))
    if tuple(event.stream_version for event in batch) != expected_versions:
        raise InvalidEventBatchError("stream versions must be contiguous after expected_version")
    for event in batch:
        if sha256_digest(event.payload) != event.payload_hash:
            raise InvalidEventBatchError(f"invalid payload hash for event {event.event_id}")
        try:
            catalog.get_payload_model(event.event_type, event.schema_version)
        except EventCatalogError as error:
            raise InvalidEventBatchError(
                f"unsupported event contract: {event.event_type} v{event.schema_version}"
            ) from error
    return batch
