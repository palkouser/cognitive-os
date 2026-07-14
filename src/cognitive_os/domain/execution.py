"""Execution-plan and execution-step contracts."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import ActorRef, ArtifactRef, ErrorInfo, NonEmptyStr, UtcDatetime
from .enums import StepStatus
from .identifiers import PlanId, StepId, TaskRunId


def dependency_graph_is_acyclic(steps: tuple[PlanStepDefinition, ...]) -> bool:
    """Return whether every plan dependency can be topologically visited."""
    graph = {step.step_id: step.depends_on for step in steps}
    visiting: set[StepId] = set()
    visited: set[StepId] = set()

    def visit(step_id: StepId) -> bool:
        if step_id in visiting:
            return False
        if step_id in visited:
            return True
        visiting.add(step_id)
        if any(not visit(dependency) for dependency in graph[step_id]):
            return False
        visiting.remove(step_id)
        visited.add(step_id)
        return True

    return all(visit(step_id) for step_id in graph)


class PlanStepDefinition(ImmutableContractModel):
    step_id: StepId
    sequence: int = Field(ge=1)
    step_type: NonEmptyStr
    title: NonEmptyStr
    description: str | None = None
    depends_on: tuple[StepId, ...] = ()
    expected_output: str | None = None
    required_tool_ids: tuple[NonEmptyStr, ...] = ()
    required_verifier_ids: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def validate_references(self) -> PlanStepDefinition:
        if self.step_id in self.depends_on:
            raise ValueError("a plan step cannot depend on itself")
        for values, label in (
            (self.depends_on, "dependency IDs"),
            (self.required_tool_ids, "tool IDs"),
            (self.required_verifier_ids, "verifier IDs"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must be unique")
        return self


class ExecutionPlan(ImmutableContractModel):
    plan_id: PlanId
    task_run_id: TaskRunId
    version: int = Field(ge=1)
    created_at: UtcDatetime
    created_by: ActorRef
    steps: tuple[PlanStepDefinition, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_plan(self) -> ExecutionPlan:
        step_ids = tuple(step.step_id for step in self.steps)
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("plan step IDs must be unique")
        sequences = tuple(step.sequence for step in self.steps)
        if len(set(sequences)) != len(sequences):
            raise ValueError("plan step sequence values must be unique")
        known = set(step_ids)
        if any(set(step.depends_on) - known for step in self.steps):
            raise ValueError("all dependencies must exist in the same plan")
        if not dependency_graph_is_acyclic(self.steps):
            raise ValueError("plan dependency graph must be acyclic")
        return self


class ExecutionStep(ImmutableContractModel):
    step_id: StepId
    task_run_id: TaskRunId
    plan_id: PlanId
    status: StepStatus = StepStatus.PENDING
    attempt: int = Field(default=1, ge=1)
    started_at: UtcDatetime | None = None
    finished_at: UtcDatetime | None = None
    input_artifacts: tuple[ArtifactRef, ...] = ()
    output_artifacts: tuple[ArtifactRef, ...] = ()
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> ExecutionStep:
        terminal = {
            StepStatus.COMPLETED,
            StepStatus.FAILED,
            StepStatus.SKIPPED,
            StepStatus.CANCELLED,
        }
        if self.status in terminal and self.finished_at is None:
            raise ValueError("terminal execution steps require finished_at")
        if self.status not in terminal and self.finished_at is not None:
            raise ValueError("non-terminal execution steps cannot have finished_at")
        if (
            self.finished_at is not None
            and self.started_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status is StepStatus.FAILED and self.error is None:
            raise ValueError("failed execution steps require an error")
        if self.status is StepStatus.COMPLETED and self.error is not None:
            raise ValueError("completed execution steps cannot contain an error")
        artifacts = self.input_artifacts + self.output_artifacts
        artifact_ids = tuple(item.artifact_id for item in artifacts)
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("execution-step artifact references must be unique")
        return self
