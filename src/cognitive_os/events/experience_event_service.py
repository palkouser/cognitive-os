"""Append and replay Experience Compiler lifecycle evidence."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope
from .experience_events import (
    EXPERIENCE_EVENT_MODELS,
    ExperienceCandidateCreated,
    ExperienceCompilationCancelled,
    ExperienceCompilationCompleted,
    ExperienceCompilationFailed,
    ExperienceCompilationRequested,
    ExperienceSnapshotCreated,
)


class ExperienceEventService:
    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="experience-compiler")

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
            source_component="experience-compiler",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.current_stream_version

    async def replay(self, stream_id: UUID) -> tuple[EventPayload, ...]:
        events = await self._store.read_stream(stream_id)
        models = {model.event_type: model for model in EXPERIENCE_EVENT_MODELS}
        payloads = tuple(
            models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
        )
        requested = False
        snapshot = False
        terminal = False
        candidates: set[UUID] = set()
        for payload in payloads:
            if isinstance(payload, ExperienceCompilationRequested):
                if requested:
                    raise ValueError("duplicate compilation request event")
                requested = True
            elif isinstance(payload, ExperienceSnapshotCreated):
                if not requested or snapshot or terminal:
                    raise ValueError("invalid snapshot lifecycle event")
                snapshot = True
            elif isinstance(
                payload,
                (
                    ExperienceCompilationCompleted,
                    ExperienceCompilationFailed,
                    ExperienceCompilationCancelled,
                ),
            ):
                if not requested or not snapshot or terminal:
                    raise ValueError("invalid compilation terminal event")
                terminal = True
            elif isinstance(payload, ExperienceCandidateCreated):
                if not snapshot or terminal or payload.candidate_id in candidates:
                    raise ValueError("invalid candidate creation event")
                candidates.add(payload.candidate_id)
        return payloads
