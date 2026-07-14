"""Explicit lifecycle transition tables."""

from .enums import StepStatus, TaskRunStatus, TaskStatus

TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.CREATED: frozenset({TaskStatus.READY, TaskStatus.CANCELLED}),
    TaskStatus.READY: frozenset({TaskStatus.RUNNING, TaskStatus.CANCELLED}),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.WAITING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
    ),
    TaskStatus.WAITING: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED}),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}

TASK_RUN_TRANSITIONS: dict[TaskRunStatus, frozenset[TaskRunStatus]] = {
    TaskRunStatus.PENDING: frozenset({TaskRunStatus.RUNNING, TaskRunStatus.CANCELLED}),
    TaskRunStatus.RUNNING: frozenset(
        {
            TaskRunStatus.WAITING_FOR_APPROVAL,
            TaskRunStatus.COMPLETED,
            TaskRunStatus.FAILED,
            TaskRunStatus.CANCELLED,
        }
    ),
    TaskRunStatus.WAITING_FOR_APPROVAL: frozenset(
        {TaskRunStatus.RUNNING, TaskRunStatus.FAILED, TaskRunStatus.CANCELLED}
    ),
    TaskRunStatus.COMPLETED: frozenset(),
    TaskRunStatus.FAILED: frozenset(),
    TaskRunStatus.CANCELLED: frozenset(),
}

STEP_TRANSITIONS: dict[StepStatus, frozenset[StepStatus]] = {
    StepStatus.PENDING: frozenset({StepStatus.READY, StepStatus.SKIPPED, StepStatus.CANCELLED}),
    StepStatus.READY: frozenset({StepStatus.RUNNING, StepStatus.SKIPPED, StepStatus.CANCELLED}),
    StepStatus.RUNNING: frozenset({StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.CANCELLED}),
    StepStatus.COMPLETED: frozenset(),
    StepStatus.FAILED: frozenset(),
    StepStatus.SKIPPED: frozenset(),
    StepStatus.CANCELLED: frozenset(),
}


def can_transition_task(current: TaskStatus, target: TaskStatus) -> bool:
    return target in TASK_TRANSITIONS[current]


def can_transition_task_run(current: TaskRunStatus, target: TaskRunStatus) -> bool:
    return target in TASK_RUN_TRANSITIONS[current]


def can_transition_step(current: StepStatus, target: StepStatus) -> bool:
    return target in STEP_TRANSITIONS[current]
