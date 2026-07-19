"""Append and replay bounded procedural skill lifecycle evidence."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .skill_events import (
    SKILL_EVENT_MODELS,
    SkillCreated,
    SkillExecutionCompleted,
    SkillExecutionFailed,
    SkillExecutionStarted,
    SkillRevisionAppended,
)


class SkillEventService:
    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="skill-engine")

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
            source_component="skill-engine",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.current_stream_version

    async def replay(self, stream_id: UUID) -> tuple[EventPayload, ...]:
        events = await self._store.read_stream(stream_id)
        models = {model.event_type: model for model in SKILL_EVENT_MODELS}
        payloads = tuple(
            models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
        )
        revisions: set[int] = set()
        executions: set[UUID] = set()
        for payload in payloads:
            if type(payload) is SkillCreated:
                if payload.revision != 1 or revisions:
                    raise ValueError("invalid skill creation event sequence")
                revisions.add(1)
            if type(payload) is SkillRevisionAppended:
                if (
                    payload.revision != payload.previous_revision + 1
                    or payload.previous_revision not in revisions
                    or payload.revision in revisions
                ):
                    raise ValueError("invalid skill revision event sequence")
                revisions.add(payload.revision)
            if isinstance(payload, SkillExecutionStarted):
                if payload.execution_id in executions:
                    raise ValueError("duplicate skill execution start event")
                executions.add(payload.execution_id)
            if isinstance(payload, (SkillExecutionCompleted, SkillExecutionFailed)):
                if payload.execution_id not in executions:
                    raise ValueError("skill execution terminal event without start")
                executions.remove(payload.execution_id)
        return payloads
