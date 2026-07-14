"""Public bounded Cognitive Controller boundary and result contracts."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import ArtifactRef, NonEmptyStr
from cognitive_os.domain.controller import ControllerState, ControllerStateSnapshot, ControllerUsage
from cognitive_os.domain.planning import ControllerExecutionPlan
from cognitive_os.domain.problems import ProblemRepresentation
from cognitive_os.verification.minimal import MinimalAcceptanceDecision


class StartControllerRequest(ImmutableContractModel):
    task_id: UUID
    task_run_id: UUID
    correlation_id: UUID
    title: NonEmptyStr
    raw_request: NonEmptyStr


class ContinueControllerRequest(ImmutableContractModel):
    task_run_id: UUID
    continuation_token: NonEmptyStr
    answers: dict[str, object] = Field(default_factory=dict)


class ControllerRunResult(ImmutableContractModel):
    task_run_id: UUID
    state: ControllerState
    problem_representation: ProblemRepresentation | None = None
    plan: ControllerExecutionPlan | None = None
    current_step_id: UUID | None = None
    acceptance_decision: MinimalAcceptanceDecision | None = None
    continuation_token: str | None = None
    usage: ControllerUsage
    result_artifacts: tuple[ArtifactRef, ...] = ()
    warnings: tuple[str, ...] = ()
    error: str | None = None
    last_stream_version: int = Field(ge=0)


class CognitiveControllerPort(Protocol):
    async def start(self, request: StartControllerRequest) -> ControllerRunResult: ...
    async def continue_run(self, request: ContinueControllerRequest) -> ControllerRunResult: ...
    async def pause(self, task_run_id: UUID, reason: str) -> ControllerRunResult: ...
    async def cancel(self, task_run_id: UUID, reason: str) -> ControllerRunResult: ...
    async def inspect(self, task_run_id: UUID) -> ControllerStateSnapshot: ...
    async def replay(self, task_run_id: UUID) -> ControllerStateSnapshot: ...
