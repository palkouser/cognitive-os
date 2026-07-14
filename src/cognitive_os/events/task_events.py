"""Task and task-run lifecycle payloads."""

from cognitive_os.domain.common import ArtifactRef, ErrorInfo, UtcDatetime
from cognitive_os.domain.enums import TaskStatus
from cognitive_os.domain.identifiers import TaskId, TaskRunId
from cognitive_os.domain.tasks import Task, TaskRun

from .base import EventPayload


class TaskCreated(EventPayload):
    event_type = "task.created"
    task: Task


class TaskUpdated(EventPayload):
    event_type = "task.updated"
    task_id: TaskId
    previous_status: TaskStatus
    current_snapshot: Task
    changed_fields: tuple[str, ...]


class TaskCancelled(EventPayload):
    event_type = "task.cancelled"
    task_id: TaskId
    cancelled_at: UtcDatetime
    reason: str | None = None


class TaskRunStarted(EventPayload):
    event_type = "task_run.started"
    task_run: TaskRun


class TaskRunWaiting(EventPayload):
    event_type = "task_run.waiting"
    task_run_id: TaskRunId
    waiting_since: UtcDatetime
    reason: str


class TaskRunCompleted(EventPayload):
    event_type = "task_run.completed"
    task_run_id: TaskRunId
    finished_at: UtcDatetime
    result_summary: str | None = None
    result_artifacts: tuple[ArtifactRef, ...] = ()


class TaskRunFailed(EventPayload):
    event_type = "task_run.failed"
    task_run_id: TaskRunId
    finished_at: UtcDatetime
    error: ErrorInfo


class TaskRunCancelled(EventPayload):
    event_type = "task_run.cancelled"
    task_run_id: TaskRunId
    finished_at: UtcDatetime
    reason: str | None = None
