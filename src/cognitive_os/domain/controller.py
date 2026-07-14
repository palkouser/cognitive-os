"""Durable Cognitive Controller state, budget, usage, and decision contracts."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import NonEmptyStr, UtcDatetime
from .identifiers import EventId, PlanId, StepId, TaskRunId


class ControllerState(StrEnum):
    RECEIVED = "received"
    REPRESENTING_PROBLEM = "representing_problem"
    WAITING_FOR_CLARIFICATION = "waiting_for_clarification"
    READY = "ready"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPAIRING = "repairing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


TERMINAL_CONTROLLER_STATES = frozenset(
    {
        ControllerState.COMPLETED,
        ControllerState.FAILED,
        ControllerState.CANCELLED,
        ControllerState.BUDGET_EXHAUSTED,
    }
)


class ControllerDecisionType(StrEnum):
    REPRESENT_PROBLEM = "represent_problem"
    REQUEST_CLARIFICATION = "request_clarification"
    GENERATE_PLAN = "generate_plan"
    EXECUTE_PROVIDER = "execute_provider"
    EXECUTE_TOOL = "execute_tool"
    VERIFY = "verify"
    REPAIR = "repair"
    PAUSE = "pause"
    COMPLETE = "complete"
    FAIL = "fail"
    CANCEL = "cancel"
    EXHAUST_BUDGET = "exhaust_budget"


class ControllerActionType(StrEnum):
    PROVIDER = "provider"
    TOOL = "tool"
    VERIFICATION = "verification"
    MANUAL = "manual"


class ControllerBudget(ImmutableContractModel):
    maximum_provider_calls: int = Field(gt=0)
    maximum_tool_calls: int = Field(gt=0)
    maximum_plan_steps: int = Field(gt=0)
    maximum_repair_cycles: int = Field(gt=0)
    maximum_clarification_cycles: int = Field(gt=0)
    maximum_elapsed_seconds: float = Field(gt=0)
    maximum_input_tokens: int | None = Field(default=None, gt=0)
    maximum_output_tokens: int | None = Field(default=None, gt=0)
    maximum_cost_units: float | None = Field(default=None, gt=0)
    maximum_verifier_calls: int = Field(default=64, gt=0)
    maximum_verification_seconds: float = Field(default=600, gt=0)


class ControllerUsage(ImmutableContractModel):
    provider_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    plan_steps_started: int = Field(default=0, ge=0)
    plan_steps_completed: int = Field(default=0, ge=0)
    repair_cycles: int = Field(default=0, ge=0)
    clarification_cycles: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_units: float = Field(default=0, ge=0)
    verifier_calls: int = Field(default=0, ge=0)
    verification_seconds: float = Field(default=0, ge=0)
    started_at: UtcDatetime
    last_updated_at: UtcDatetime


class ControllerDecision(ImmutableContractModel):
    decision_id: UUID
    task_run_id: TaskRunId
    current_state: ControllerState
    decision_type: ControllerDecisionType
    reason: NonEmptyStr
    selected_step_id: StepId | None = None
    selected_provider_id: NonEmptyStr | None = None
    selected_tool_id: NonEmptyStr | None = None
    created_at: UtcDatetime
    causation_event_id: EventId | None = None


class ControllerStateSnapshot(ImmutableContractModel):
    task_run_id: TaskRunId
    state: ControllerState
    problem_id: UUID | None = None
    problem_revision: int | None = Field(default=None, ge=1)
    plan_id: PlanId | None = None
    plan_version: int | None = Field(default=None, ge=1)
    current_step_id: StepId | None = None
    completed_step_ids: tuple[StepId, ...] = ()
    failed_step_ids: tuple[StepId, ...] = ()
    usage: ControllerUsage
    repair_cycle: int = Field(default=0, ge=0)
    clarification_cycle: int = Field(default=0, ge=0)
    last_event_id: EventId | None = None
    last_stream_version: int = Field(ge=0)
    updated_at: UtcDatetime
    terminal_reason: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_state(self) -> ControllerStateSnapshot:
        terminal = self.state in TERMINAL_CONTROLLER_STATES
        if terminal != (self.terminal_reason is not None):
            raise ValueError("terminal reason must exist only for terminal states")
        if self.current_step_id and self.state not in {
            ControllerState.EXECUTING,
            ControllerState.VERIFYING,
            ControllerState.REPAIRING,
        }:
            raise ValueError("current step is invalid for this controller state")
        if set(self.completed_step_ids) & set(self.failed_step_ids):
            raise ValueError("completed and failed step IDs must be disjoint")
        if terminal and self.current_step_id is not None:
            raise ValueError("terminal state cannot have a current step")
        return self
