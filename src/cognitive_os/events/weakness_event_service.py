"""Append and replay weakness lifecycle evidence."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .weakness_events import WEAKNESS_EVENT_MODELS


class WeaknessEventService:
    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="weakness-miner")

    async def append(self, stream_id: UUID, payload: EventPayload, *, correlation_id: UUID) -> int:
        version = await self._store.get_stream_version(stream_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=stream_id,
            stream_type=StreamType.SYSTEM,
            stream_version=version + 1,
            correlation_id=correlation_id,
            causation_event_id=None,
            actor=self._actor,
            source_component="weakness-miner",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.current_stream_version

    async def replay(self, stream_id: UUID) -> tuple[EventPayload, ...]:
        events = await self._store.read_stream(stream_id)
        models = {model.event_type: model for model in WEAKNESS_EVENT_MODELS}
        return tuple(
            models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
        )
