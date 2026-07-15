"""Minimal governed-memory lifecycle event payloads."""

from uuid import UUID

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.memory import MemoryRecord, MemoryRevision

from .base import EventPayload


class MemoryItemCreated(EventPayload):
    event_type = "memory.item_created"
    record: MemoryRecord
    revision: MemoryRevision


class MemoryRevisionAppended(EventPayload):
    event_type = "memory.revision_appended"
    memory_id: UUID
    expected_revision: int
    revision: MemoryRevision


class _MemoryTransitionEvent(EventPayload):
    memory_id: UUID
    expected_revision: int
    revision: MemoryRevision
    reason: NonEmptyStr
    transitioned_at: UtcDatetime


class MemoryPromoted(_MemoryTransitionEvent):
    event_type = "memory.promoted"


class MemorySuperseded(_MemoryTransitionEvent):
    event_type = "memory.superseded"
    successor_memory_id: UUID


class MemoryRetracted(_MemoryTransitionEvent):
    event_type = "memory.retracted"


class MemoryExpired(_MemoryTransitionEvent):
    event_type = "memory.expired"


class MemoryEmbeddingRecorded(EventPayload):
    event_type = "memory.embedding_recorded"
    memory_id: UUID
    revision: int
    provider_id: NonEmptyStr
    model_id: NonEmptyStr
    dimension: int
    content_hash: Sha256Hex
    recorded_at: UtcDatetime


class MemoryIngestionCompleted(EventPayload):
    event_type = "memory.ingestion_completed"
    ingestion_id: UUID
    source_hash: Sha256Hex
    memory_ids: tuple[UUID, ...]
    completed_at: UtcDatetime


class MemoryIngestionRejected(EventPayload):
    event_type = "memory.ingestion_rejected"
    ingestion_id: UUID
    source_hash: Sha256Hex
    reason_code: NonEmptyStr
    rejected_at: UtcDatetime


MEMORY_EVENT_MODELS: tuple[type[EventPayload], ...] = (
    MemoryItemCreated,
    MemoryRevisionAppended,
    MemoryPromoted,
    MemorySuperseded,
    MemoryRetracted,
    MemoryExpired,
    MemoryEmbeddingRecorded,
    MemoryIngestionCompleted,
    MemoryIngestionRejected,
)
