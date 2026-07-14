import pytest

from cognitive_os.domain import StepStatus, TaskRunStatus, TaskStatus
from cognitive_os.domain.transitions import (
    STEP_TRANSITIONS,
    TASK_RUN_TRANSITIONS,
    TASK_TRANSITIONS,
    can_transition_step,
    can_transition_task,
    can_transition_task_run,
)


@pytest.mark.parametrize("current", TaskStatus)
@pytest.mark.parametrize("target", TaskStatus)
def test_every_task_transition_pair(current: TaskStatus, target: TaskStatus) -> None:
    assert can_transition_task(current, target) is (target in TASK_TRANSITIONS[current])


@pytest.mark.parametrize("current", TaskRunStatus)
@pytest.mark.parametrize("target", TaskRunStatus)
def test_every_task_run_transition_pair(current: TaskRunStatus, target: TaskRunStatus) -> None:
    assert can_transition_task_run(current, target) is (target in TASK_RUN_TRANSITIONS[current])


@pytest.mark.parametrize("current", StepStatus)
@pytest.mark.parametrize("target", StepStatus)
def test_every_step_transition_pair(current: StepStatus, target: StepStatus) -> None:
    assert can_transition_step(current, target) is (target in STEP_TRANSITIONS[current])
