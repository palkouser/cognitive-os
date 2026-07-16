"""Append-only Context Builder lifecycle persistence and replay."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .context_events import (
    CONTEXT_EVENT_MODELS,
    ContextBundleAttached,
    ContextBundleCreated,
)


class ContextEventService:
    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="context-builder")

    async def append(
        self,
        context_request_id: UUID,
        task_run_id: UUID,
        payload: EventPayload,
        *,
        correlation_id: UUID,
    ) -> int:
        version = await self._store.get_stream_version(context_request_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=context_request_id,
            stream_type=StreamType.SYSTEM,
            stream_version=version + 1,
            correlation_id=correlation_id,
            causation_event_id=None,
            actor=self._actor,
            source_component="context-builder",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.current_stream_version

    async def replay(self, context_request_id: UUID) -> tuple[EventPayload, ...]:
        events = await self._store.read_stream(context_request_id)
        models = {model.event_type: model for model in CONTEXT_EVENT_MODELS}
        payloads = tuple(
            models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
        )
        created: set[tuple[UUID, int]] = set()
        for payload in payloads:
            if isinstance(payload, ContextBundleCreated):
                key = payload.context_bundle_id, payload.revision
                if key in created:
                    raise ValueError("duplicate Context Bundle revision event")
                if (
                    payload.revision > 1
                    and (payload.context_bundle_id, payload.revision - 1) not in created
                ):
                    raise ValueError("Context Bundle revision event gap")
                created.add(key)
            elif isinstance(payload, ContextBundleAttached):
                if (payload.context_bundle_id, payload.revision) not in created:
                    raise ValueError("an unknown Context Bundle revision was attached")
        return payloads
