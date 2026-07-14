"""Task and task-run snapshot contracts."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ActorRef, ErrorInfo, NonEmptyStr, UtcDatetime
from .enums import PrivacyClass, RiskLevel, TaskPriority, TaskRunStatus, TaskStatus
from .identifiers import SessionId, StepId, TaskId, TaskRunId

Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class Task(ImmutableContractModel):
    task_id: TaskId
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
    raw_request: NonEmptyStr
    normalized_request: str | None = None
    created_at: UtcDatetime
    updated_at: UtcDatetime
    priority: TaskPriority = TaskPriority.NORMAL
    risk_level: RiskLevel = RiskLevel.LOW
    status: TaskStatus = TaskStatus.CREATED
    tags: tuple[Tag, ...] = ()
    requested_by: ActorRef
    privacy_class: PrivacyClass = PrivacyClass.INTERNAL

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip().casefold() for item in value)
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> Task:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        if len(self.tags) > 64:
            raise ValueError("a task cannot contain more than 64 tags")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("task tags must be unique")
        return self


class TaskRun(ImmutableContractModel):
    task_run_id: TaskRunId
    task_id: TaskId
    session_id: SessionId
    correlation_id: UUID
    status: TaskRunStatus = TaskRunStatus.PENDING
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    active_step_id: StepId | None = None
    selected_provider: NonEmptyStr | None = None
    selected_model: NonEmptyStr | None = None
    result_summary: str | None = None
    error: ErrorInfo | None = None
    attempt: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_lifecycle(self) -> TaskRun:
        terminal = {
            TaskRunStatus.COMPLETED,
            TaskRunStatus.FAILED,
            TaskRunStatus.CANCELLED,
        }
        if self.status in terminal and self.finished_at is None:
            raise ValueError("terminal task runs require finished_at")
        if self.status not in terminal and self.finished_at is not None:
            raise ValueError("non-terminal task runs cannot have finished_at")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot be earlier than started_at")
        if self.status is TaskRunStatus.FAILED and self.error is None:
            raise ValueError("failed task runs require an error")
        if self.status is TaskRunStatus.COMPLETED and self.error is not None:
            raise ValueError("completed task runs cannot contain an error")
        return self
