"""Typed Problem Representation and Cognitive Controller event payloads."""

from uuid import UUID

from cognitive_os.domain.clarifications import (
    ClarificationRequest,
    ClarificationResponse,
    ContinuationTokenRecord,
)
from cognitive_os.domain.common import ArtifactRef, NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.controller import ControllerDecision, ControllerState, ControllerUsage
from cognitive_os.domain.identifiers import TaskRunId
from cognitive_os.domain.problems import ProblemRepresentation

from .base import EventPayload


class ProblemRepresentationCreated(EventPayload):
    event_type = "problem.representation_created"
    representation: ProblemRepresentation | None = None
    representation_artifact: ArtifactRef | None = None


class ProblemRepresentationRevised(EventPayload):
    event_type = "problem.representation_revised"
    problem_id: UUID
    previous_revision: int
    representation: ProblemRepresentation | None = None
    representation_artifact: ArtifactRef | None = None


class ControllerStateChanged(EventPayload):
    event_type = "controller.state_changed"
    previous_state: ControllerState
    current_state: ControllerState
    reason: NonEmptyStr
    decision_id: UUID
    changed_at: UtcDatetime


class ControllerDecisionRecorded(EventPayload):
    event_type = "controller.decision_recorded"
    decision: ControllerDecision


class ControllerClarificationRequested(EventPayload):
    event_type = "controller.clarification_requested"
    request: ClarificationRequest


class ControllerClarificationProvided(EventPayload):
    event_type = "controller.clarification_provided"
    response: ClarificationResponse


class ControllerCheckpointCreated(EventPayload):
    event_type = "controller.checkpoint_created"
    checkpoint_id: UUID
    checkpoint_artifact: ArtifactRef
    event_stream_version: int
    content_hash: Sha256Hex


class ControllerContinuationIssued(EventPayload):
    event_type = "controller.continuation_issued"
    record: ContinuationTokenRecord


class ControllerContinuationConsumed(EventPayload):
    event_type = "controller.continuation_consumed"
    continuation_id: UUID
    consumed_at: UtcDatetime


class ControllerBudgetExhaustedEvent(EventPayload):
    event_type = "controller.budget_exhausted"
    task_run_id: TaskRunId
    reason: NonEmptyStr
    usage: ControllerUsage
    exhausted_at: UtcDatetime


class ControllerPaused(EventPayload):
    event_type = "controller.paused"
    task_run_id: TaskRunId
    reason: NonEmptyStr
    paused_at: UtcDatetime


class ControllerCancelled(EventPayload):
    event_type = "controller.cancelled"
    task_run_id: TaskRunId
    reason: NonEmptyStr
    cancelled_at: UtcDatetime
