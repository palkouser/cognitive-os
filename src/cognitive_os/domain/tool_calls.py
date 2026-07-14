"""Execution-independent tool-call audit contracts."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, JsonValue, NonEmptyStr, UtcDatetime
from .enums import CallStatus, PermissionDecision, RiskLevel
from .identifiers import StepId, TaskRunId, ToolCallId


class ToolCallRequestRecord(ImmutableContractModel):
    tool_call_id: ToolCallId
    task_run_id: TaskRunId
    step_id: StepId | None = None
    tool_id: NonEmptyStr
    tool_version: NonEmptyStr
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    requested_at: UtcDatetime
    risk_level: RiskLevel = RiskLevel.LOW
    permission_decision: PermissionDecision = PermissionDecision.NOT_REQUIRED
    status: CallStatus = CallStatus.PENDING

    @field_validator("arguments", mode="before")
    @classmethod
    def copy_arguments(cls, value: Any) -> Any:
        return dict(value) if isinstance(value, dict) else value


class ToolCallResultRecord(ImmutableContractModel):
    tool_call_id: ToolCallId
    status: CallStatus
    started_at: UtcDatetime | None = None
    finished_at: UtcDatetime | None = None
    exit_code: int | None = None
    stdout_artifact: ArtifactRef | None = None
    stderr_artifact: ArtifactRef | None = None
    result_artifacts: tuple[ArtifactRef, ...] = ()
    sandbox_id: NonEmptyStr | None = None
    duration_ms: float | None = Field(default=None, ge=0)
    error: ErrorInfo | None = None
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_result(self) -> ToolCallResultRecord:
        terminal = {
            CallStatus.COMPLETED,
            CallStatus.FAILED,
            CallStatus.CANCELLED,
            CallStatus.TIMED_OUT,
        }
        if self.status in terminal and self.finished_at is None:
            raise ValueError("terminal tool calls require finished_at")
        if (
            self.finished_at is not None
            and self.started_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status is CallStatus.FAILED and self.error is None and self.exit_code in (None, 0):
            raise ValueError("failed tool calls require an error or non-zero exit code")
        artifacts = tuple(
            item
            for item in (self.stdout_artifact, self.stderr_artifact, *self.result_artifacts)
            if item is not None
        )
        ids = tuple(item.artifact_id for item in artifacts)
        if len(set(ids)) != len(ids):
            raise ValueError("tool-call artifact references must be unique")
        return self
