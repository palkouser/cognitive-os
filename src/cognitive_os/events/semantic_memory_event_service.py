"""Expected-version lifecycle audit for semantic aggregate streams."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .storage import AppendResult


class SemanticMemoryEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="semantic-memory-service")

    async def current_version(self, aggregate_id: UUID) -> int:
        return await self._store.get_stream_version(aggregate_id) or 0

    async def append(
        self,
        *,
        aggregate_id: UUID,
        payload: EventPayload,
        expected_version: int,
        correlation_id: UUID,
        causation_event_id: UUID | None = None,
    ) -> AppendResult:
        envelope = create_event_envelope(
            payload=payload,
            stream_id=aggregate_id,
            stream_type=StreamType.SEMANTIC,
            stream_version=expected_version + 1,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component="semantic-memory-service",
            privacy_class=PrivacyClass.SENSITIVE,
        )
        return await self._store.append((envelope,), expected_version=expected_version)
