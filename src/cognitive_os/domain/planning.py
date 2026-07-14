"""Controller action data layered over the structural ExecutionPlan."""

from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import ActorRef, NonEmptyStr, UtcDatetime
from .controller import ControllerActionType
from .execution import ExecutionPlan
from .identifiers import StepId


class ControllerStepAction(ImmutableContractModel):
    step_id: StepId
    action_type: ControllerActionType
    provider_id: NonEmptyStr | None = None
    requested_model: NonEmptyStr | None = None
    provider_instructions: NonEmptyStr | None = None
    tool_id: NonEmptyStr | None = None
    tool_version: NonEmptyStr | None = None
    tool_arguments: dict[str, Any] | None = None
    verifier_ids: tuple[NonEmptyStr, ...] = ()
    response_format: NonEmptyStr | None = None
    response_schema: dict[str, Any] | None = None
    expected_artifacts: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def action_fields_match_type(self) -> ControllerStepAction:
        if self.action_type is ControllerActionType.PROVIDER:
            if not self.provider_instructions:
                raise ValueError("provider actions require instructions")
            if self.tool_id is not None or self.tool_arguments is not None:
                raise ValueError("provider actions cannot contain tool fields")
        elif self.action_type is ControllerActionType.TOOL:
            if not self.tool_id or not self.tool_version or self.tool_arguments is None:
                raise ValueError("tool actions require ID, version, and arguments")
            if self.provider_id or self.provider_instructions:
                raise ValueError("tool actions cannot contain provider fields")
        elif self.action_type is ControllerActionType.VERIFICATION:
            if not self.verifier_ids:
                raise ValueError("verification actions require verifier IDs")
        elif self.action_type is ControllerActionType.MANUAL and not self.provider_instructions:
            raise ValueError("manual actions require a clear instruction")
        return self


class ControllerExecutionPlan(ImmutableContractModel):
    plan: ExecutionPlan
    actions: tuple[ControllerStepAction, ...] = Field(min_length=1)
    created_at: UtcDatetime
    created_by: ActorRef
    sequential_only: bool = True

    @model_validator(mode="after")
    def complete_mapping(self) -> ControllerExecutionPlan:
        step_ids = {step.step_id for step in self.plan.steps}
        action_ids = [action.step_id for action in self.actions]
        if len(action_ids) != len(set(action_ids)) or set(action_ids) != step_ids:
            raise ValueError("plan steps and controller actions require a one-to-one mapping")
        if not self.sequential_only:
            raise ValueError("Sprint 6 requires sequential execution")
        for action in self.actions:
            step = next(item for item in self.plan.steps if item.step_id == action.step_id)
            if step.step_type != action.action_type.value:
                raise ValueError("plan step type and action type must match")
        return self
