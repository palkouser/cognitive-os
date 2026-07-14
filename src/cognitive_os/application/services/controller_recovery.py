"""Controller replay and fail-safe active-child classification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.clarifications import (
    ClarificationAnswer,
    ClarificationRequest,
    ClarificationResponse,
    ContinuationTokenRecord,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.controller import ControllerState, ControllerStateSnapshot, ControllerUsage
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.events.controller_events import (
    ControllerClarificationRequested,
    ControllerContinuationConsumed,
    ControllerContinuationIssued,
    ControllerStateChanged,
    ProblemRepresentationCreated,
    ProblemRepresentationRevised,
)
from cognitive_os.events.storage import StoredEventDecoder


class ActiveChildClassification(StrEnum):
    NOT_STARTED = "not_started"
    SAFE_TO_REEVALUATE = "safe_to_reevaluate"
    UNCERTAIN = "uncertain"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class ContinuationContext:
    request: ClarificationRequest
    token_record: ContinuationTokenRecord
    problem: ProblemRepresentation
    usage: ControllerUsage
    stream_version: int

    def response_from_answers(self, answers: dict[str, object]) -> ClarificationResponse:
        return ClarificationResponse(
            clarification_id=self.request.clarification_id,
            task_run_id=self.request.task_run_id,
            answers=tuple(
                ClarificationAnswer(question_id=UUID(key), answer=value)
                for key, value in sorted(answers.items())
            ),
            provided_at=utc_now(),
            provided_by="controller-owner",
        )


def classify_child_call(event_types: tuple[str, ...]) -> ActiveChildClassification:
    terminal_suffixes = (".completed", ".failed", ".denied", ".timed_out", ".cancelled")
    if any(item.endswith(terminal_suffixes) for item in event_types):
        return ActiveChildClassification.TERMINAL
    if any(item.endswith(".started") for item in event_types):
        return ActiveChildClassification.UNCERTAIN
    if any(item.endswith(".requested") for item in event_types):
        return ActiveChildClassification.SAFE_TO_REEVALUATE
    return ActiveChildClassification.NOT_STARTED


class ControllerRecoveryService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._decoder = StoredEventDecoder(build_default_event_catalog())

    async def replay(self, task_run_id: UUID) -> ControllerStateSnapshot:
        stored = await self._store.read_stream(task_run_id)
        if not stored:
            raise LookupError("controller task-run stream does not exist")
        now = utc_now()
        state = ControllerState.RECEIVED
        last_event_id = None
        for event in stored:
            decoded = self._decoder.decode_stored_event(event)
            if isinstance(decoded.payload, ControllerStateChanged):
                if decoded.payload.previous_state is not state:
                    raise ValueError("controller replay found an invalid state sequence")
                state = decoded.payload.current_state
            last_event_id = event.envelope.event_id
        return ControllerStateSnapshot(
            task_run_id=task_run_id,
            state=state,
            usage=ControllerUsage(started_at=now, last_updated_at=now),
            last_event_id=last_event_id,
            last_stream_version=stored[-1].envelope.stream_version,
            updated_at=stored[-1].envelope.occurred_at,
            terminal_reason="replayed terminal state"
            if state
            in {
                ControllerState.COMPLETED,
                ControllerState.FAILED,
                ControllerState.CANCELLED,
                ControllerState.BUDGET_EXHAUSTED,
            }
            else None,
        )

    async def continuation_context(self, task_run_id: UUID) -> ContinuationContext:
        stored = await self._store.read_stream(task_run_id)
        if not stored:
            raise LookupError("controller task-run stream does not exist")
        problem = None
        request = None
        record = None
        consumed: set[UUID] = set()
        usage = ControllerUsage(
            started_at=stored[0].envelope.occurred_at,
            last_updated_at=stored[-1].envelope.occurred_at,
        )
        for event in stored:
            payload = self._decoder.decode_stored_event(event).payload
            if isinstance(payload, (ProblemRepresentationCreated, ProblemRepresentationRevised)):
                problem = payload.representation
            elif isinstance(payload, ControllerClarificationRequested):
                request = payload.request
            elif isinstance(payload, ControllerContinuationIssued):
                record = payload.record
            elif isinstance(payload, ControllerContinuationConsumed):
                consumed.add(payload.continuation_id)
        if problem is None or request is None or record is None:
            raise LookupError("controller has no resumable clarification context")
        if record.continuation_id in consumed:
            raise ValueError("continuation token has already been consumed")
        return ContinuationContext(
            request=request,
            token_record=record,
            problem=problem,
            usage=usage,
            stream_version=stored[-1].envelope.stream_version,
        )
