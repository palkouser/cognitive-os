"""Expected-version protected verifier lifecycle persistence."""

from __future__ import annotations

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType
from cognitive_os.events.base import EventPayload, create_event_envelope
from cognitive_os.events.storage import AppendResult


class VerifierEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.VERIFIER, actor_id="verifier-service")

    async def append(
        self,
        *,
        verification_id: UUID,
        payload: EventPayload,
        correlation_id: UUID,
        causation_event_id: UUID | None = None,
    ) -> AppendResult:
        expected_version = await self._store.get_stream_version(verification_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=verification_id,
            stream_type=StreamType.VERIFIER,
            stream_version=expected_version + 1,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component="verifier-service",
            privacy_class=PrivacyClass.SENSITIVE,
        )
        return await self._store.append((envelope,), expected_version=expected_version)
