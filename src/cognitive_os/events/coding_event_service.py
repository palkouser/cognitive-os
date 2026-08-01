"""Expected-version persistence for the authoritative task-run coding trajectory."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType

from .base import EventPayload, create_event_envelope


class CodingEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="python-coding-agent")

    async def append(
        self,
        task_run_id: UUID,
        payload: EventPayload,
        *,
        correlation_id: UUID,
        causation_event_id: UUID | None = None,
        stream_type: StreamType = StreamType.TASK_RUN,
    ) -> UUID:
        """Append with expected-version compare-and-set.

        `stream_type` is a parameter rather than a constant because Sprint 21D2's campaign
        sequence receipt is keyed by campaign, not by task run: one stream per campaign, so
        the receipts of one campaign are ordered against each other and a concurrent resume
        loses the race instead of writing a second receipt. It is still one service and one
        store — a second writer would be a second authority over the same evidence.
        """
        version = await self._store.get_stream_version(task_run_id) or 0
        envelope = create_event_envelope(
            payload=payload,
            stream_id=task_run_id,
            stream_type=stream_type,
            stream_version=version + 1,
            correlation_id=correlation_id,
            causation_event_id=causation_event_id,
            actor=self._actor,
            source_component="python-coding-agent",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.event_ids[-1]
