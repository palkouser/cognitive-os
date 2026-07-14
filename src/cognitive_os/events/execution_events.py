"""Plan, execution-step, checkpoint, and resume payloads."""

from uuid import UUID

from cognitive_os.domain.common import ArtifactRef, ErrorInfo, UtcDatetime
from cognitive_os.domain.execution import ExecutionPlan, ExecutionStep
from cognitive_os.domain.identifiers import StepId, TaskRunId

from .base import EventPayload


class PlanCreated(EventPayload):
    event_type = "plan.created"
    plan: ExecutionPlan


class PlanRevised(EventPayload):
    event_type = "plan.revised"
    plan: ExecutionPlan
    previous_version: int


class ExecutionStepCreated(EventPayload):
    event_type = "execution_step.created"
    step: ExecutionStep


class ExecutionStepStarted(EventPayload):
    event_type = "execution_step.started"
    step_id: StepId
    started_at: UtcDatetime
    attempt: int


class ExecutionStepCompleted(EventPayload):
    event_type = "execution_step.completed"
    step_id: StepId
    finished_at: UtcDatetime
    output_artifacts: tuple[ArtifactRef, ...] = ()


class ExecutionStepFailed(EventPayload):
    event_type = "execution_step.failed"
    step_id: StepId
    finished_at: UtcDatetime
    error: ErrorInfo


class ExecutionStepRetried(EventPayload):
    event_type = "execution_step.retried"
    step_id: StepId
    previous_attempt: int
    next_attempt: int


class ExecutionStepSkipped(EventPayload):
    event_type = "execution_step.skipped"
    step_id: StepId
    skipped_at: UtcDatetime
    reason: str


class CheckpointCreated(EventPayload):
    event_type = "checkpoint.created"
    task_run_id: TaskRunId
    checkpoint_id: UUID
    created_at: UtcDatetime
    active_step_id: StepId | None = None


class RunResumed(EventPayload):
    event_type = "run.resumed"
    task_run_id: TaskRunId
    checkpoint_id: UUID
    resumed_at: UtcDatetime


class ExecutionStepCancelled(EventPayload):
    event_type = "execution_step.cancelled"
    step_id: StepId
    cancelled_at: UtcDatetime
    reason: str | None = None
