"""Expected-version lifecycle audit for dedicated memory streams."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType
from cognitive_os.domain.memory import MemoryRecord, MemoryRevision
from cognitive_os.infrastructure.errors import WrongExpectedVersionError

from .base import EventPayload, create_event_envelope
from .memory_events import MemoryItemCreated
from .memory_store import EventStoreConflictError
from .storage import AppendResult


class MemoryEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="governed-memory-service")

    async def append(
        self,
        *,
        memory_id: UUID,
        payload: EventPayload,
        expected_version: int,
        correlation_id: UUID,
        causation_event_id: UUID | None = None,
    ) -> AppendResult:
        envelope = create_event_envelope(
            payload=payload,
            stream_id=memory_id,
            stream_type=StreamType.MEMORY,
            stream_version=expected_version + 1,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component="governed-memory-service",
            privacy_class=PrivacyClass.SENSITIVE,
        )
        return await self._store.append((envelope,), expected_version=expected_version)

    async def ensure_item_created(
        self,
        *,
        record: MemoryRecord,
        revision: MemoryRevision,
        correlation_id: UUID,
    ) -> AppendResult | None:
        """Append `memory.item_created` if the record does not have one yet.

        **22B W3-F1.** The governed create writes the record in one transaction and appends
        this event in another, so a crash in the window between them leaves an item outside
        its own event stream. `MemoryService.create` used to decide whether to append by
        asking whether the memory existed *before* the write — which is the wrong question
        twice over. It is answered by a lookup, so on the resume that re-runs a crashed range
        the idempotency key makes the answer "it existed" and the event is never appended:
        the orphan is permanent, and the more often you resume the more certain it becomes.
        And it is a question about the record, when the fact in doubt is about the stream.

        This asks the stream instead. A record whose stream is empty gets its creation event,
        whether this call created the record or found it; a record that already has one is
        left alone. The resume therefore repairs, which is the second fix 22C's plan names.

        It does not close the window — a range that is never re-run keeps its orphan, and a
        repaired event is stamped when the repair ran, not when the record was written.
        Closing the window needs the record and the event in one transaction, which needs a
        transactional boundary the repository and event-store ports do not share.
        """
        if await self._store.get_stream_version(record.memory_id):
            return None
        try:
            return await self.append(
                memory_id=record.memory_id,
                payload=MemoryItemCreated(record=record, revision=revision),
                expected_version=0,
                correlation_id=correlation_id,
            )
        except (WrongExpectedVersionError, EventStoreConflictError):
            # Another writer appended between the probe and this append. The stream has its
            # creation event, which is the whole point; losing the race is a success.
            return None
