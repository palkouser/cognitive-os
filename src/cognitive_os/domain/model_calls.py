"""Provider-neutral model-call audit contracts."""

from __future__ import annotations

from pydantic import Field, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, NonEmptyStr, Sha256Hex, TokenUsage, UtcDatetime
from .enums import CallStatus
from .identifiers import ModelCallId, StepId, TaskRunId, ToolCallId


class ModelParameters(ImmutableContractModel):
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int | None = Field(default=None, ge=1)
    context_budget: int | None = Field(default=None, ge=1)
    timeout_seconds: float | None = Field(default=None, gt=0)
    tool_choice: NonEmptyStr | None = None
    structured_output_schema_name: NonEmptyStr | None = None


class ModelCallRequestRecord(ImmutableContractModel):
    model_call_id: ModelCallId
    task_run_id: TaskRunId
    step_id: StepId | None = None
    provider: NonEmptyStr
    requested_model: NonEmptyStr
    system_context_hash: Sha256Hex | None = None
    input_artifacts: tuple[ArtifactRef, ...] = ()
    parameters: ModelParameters = ModelParameters()
    requested_at: UtcDatetime
    status: CallStatus = CallStatus.PENDING


class ModelCallResultRecord(ImmutableContractModel):
    model_call_id: ModelCallId
    resolved_model: NonEmptyStr | None = None
    status: CallStatus
    started_at: UtcDatetime | None = None
    finished_at: UtcDatetime | None = None
    content_artifact: ArtifactRef | None = None
    raw_response_artifact: ArtifactRef | None = None
    tool_call_ids: tuple[ToolCallId, ...] = ()
    usage: TokenUsage | None = None
    finish_reason: str | None = None
    latency_ms: float | None = Field(default=None, ge=0)
    error: ErrorInfo | None = None
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_lifecycle(self) -> ModelCallResultRecord:
        terminal = {
            CallStatus.COMPLETED,
            CallStatus.FAILED,
            CallStatus.CANCELLED,
            CallStatus.TIMED_OUT,
        }
        if self.status in terminal and self.finished_at is None:
            raise ValueError("terminal model calls require finished_at")
        if (
            self.finished_at is not None
            and self.started_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status is CallStatus.FAILED and self.error is None:
            raise ValueError("failed model calls require an error")
        if self.status is CallStatus.COMPLETED and self.error is not None:
            raise ValueError("completed model calls cannot contain an error")
        if len(set(self.tool_call_ids)) != len(self.tool_call_ids):
            raise ValueError("tool_call_ids must be unique")
        return self
