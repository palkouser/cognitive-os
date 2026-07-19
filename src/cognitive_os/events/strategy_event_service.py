"""Append and replay bounded strategy lifecycle evidence."""

from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef
from cognitive_os.domain.enums import ActorType, PrivacyClass, StreamType
from cognitive_os.domain.strategies import StrategyStatus
from cognitive_os.strategies.engine import validate_lifecycle_transition

from .base import EventPayload, create_event_envelope
from .strategy_events import (
    STRATEGY_EVENT_MODELS,
    StrategyCreated,
    StrategyExecutionCompleted,
    StrategyExecutionFailed,
    StrategyExecutionStarted,
    StrategyRevisionAppended,
    StrategyStatusChanged,
)


class StrategyEventService:
    def __init__(self, store: EventStorePort) -> None:
        self._store = store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="strategy-engine")

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
            source_component="strategy-engine",
            privacy_class=PrivacyClass.INTERNAL,
        )
        result = await self._store.append((envelope,), expected_version=version)
        return result.current_stream_version

    async def replay(self, stream_id: UUID) -> tuple[EventPayload, ...]:
        events = await self._store.read_stream(stream_id)
        models = {model.event_type: model for model in STRATEGY_EVENT_MODELS}
        payloads = tuple(
            models[item.envelope.event_type].model_validate(item.envelope.payload)
            for item in events
        )
        revisions: set[int] = set()
        status: StrategyStatus | None = None
        executions: set[UUID] = set()
        terminals: set[UUID] = set()
        for payload in payloads:
            if type(payload) is StrategyCreated:
                if payload.revision != 1 or revisions:
                    raise ValueError("invalid strategy creation event sequence")
                revisions.add(1)
                status = payload.status
            elif type(payload) is StrategyRevisionAppended:
                if (
                    payload.revision != payload.previous_revision + 1
                    or payload.previous_revision not in revisions
                    or payload.revision in revisions
                ):
                    raise ValueError("invalid strategy revision event sequence")
                revisions.add(payload.revision)
            elif isinstance(payload, StrategyStatusChanged):
                if status is None or payload.previous_status is not status:
                    raise ValueError("strategy status event does not match replay state")
                validate_lifecycle_transition(status, payload.status)
                status = payload.status
            if isinstance(payload, StrategyExecutionStarted):
                if payload.execution_id in executions:
                    raise ValueError("duplicate strategy execution start event")
                executions.add(payload.execution_id)
            if isinstance(payload, (StrategyExecutionCompleted, StrategyExecutionFailed)):
                if payload.execution_id not in executions or payload.execution_id in terminals:
                    raise ValueError("invalid strategy execution terminal event")
                terminals.add(payload.execution_id)
        return payloads
