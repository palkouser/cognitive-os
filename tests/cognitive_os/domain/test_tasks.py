from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.domain import ErrorInfo, Task, TaskRun, TaskRunStatus, new_id


def test_task_normalizes_tags_and_round_trips(task: Task) -> None:
    changed = task.model_copy(update={"tags": (" Report ", "URGENT")})
    validated = Task.model_validate(changed.model_dump())
    restored = Task.model_validate_json(validated.model_dump_json())
    assert restored.tags == ("report", "urgent")


def test_duplicate_tags_and_invalid_timestamp_order_are_rejected(task: Task) -> None:
    with pytest.raises(ValidationError):
        Task.model_validate({**task.model_dump(), "tags": ["same", "SAME"]})
    with pytest.raises(ValidationError):
        Task.model_validate(
            {**task.model_dump(), "updated_at": task.created_at - timedelta(seconds=1)}
        )


def test_task_run_lifecycle_invariants(task_run: TaskRun, error: ErrorInfo) -> None:
    with pytest.raises(ValidationError):
        TaskRun.model_validate({**task_run.model_dump(), "status": "failed"})
    with pytest.raises(ValidationError):
        TaskRun.model_validate(
            {
                **task_run.model_dump(),
                "status": "completed",
                "finished_at": task_run.started_at,
                "error": error.model_dump(),
            }
        )
    with pytest.raises(ValidationError):
        TaskRun.model_validate({**task_run.model_dump(), "finished_at": task_run.started_at})


def test_completed_and_failed_task_runs_validate(task_run: TaskRun, error: ErrorInfo) -> None:
    completed = TaskRun.model_validate(
        {**task_run.model_dump(), "status": "completed", "finished_at": task_run.started_at}
    )
    failed = TaskRun.model_validate(
        {
            **task_run.model_dump(),
            "task_run_id": new_id(),
            "status": TaskRunStatus.FAILED,
            "finished_at": task_run.started_at,
            "error": error.model_dump(),
        }
    )
    assert TaskRun.model_validate_json(completed.model_dump_json()) == completed
    assert failed.error == error
