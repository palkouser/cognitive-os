"""Append-only benchmark lifecycle persistence."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType
from cognitive_os.events.base import EventPayload, create_event_envelope


class BenchmarkEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="benchmark-runner")

    async def append(
        self, run_id: UUID, payload: EventPayload, *, causation_event_id: UUID | None = None
    ) -> UUID:
        version = await self._store.get_stream_version(run_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=run_id,
            stream_type=StreamType.SYSTEM,
            stream_version=version + 1,
            correlation_id=run_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component="benchmark-runner",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.event_ids[-1]
