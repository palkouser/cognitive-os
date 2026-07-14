from datetime import timedelta

import pytest
from pydantic import ValidationError

from cognitive_os.domain import ExecutionPlan, ExecutionStep, PlanStepDefinition, StepStatus, new_id


def test_linear_and_branching_plans_validate(plan: ExecutionPlan) -> None:
    branch = PlanStepDefinition(
        step_id=new_id(),
        sequence=3,
        step_type="verify",
        title="Verify",
        depends_on=(plan.steps[0].step_id,),
    )
    revised = ExecutionPlan.model_validate({**plan.model_dump(), "steps": (*plan.steps, branch)})
    assert len(revised.steps) == 3


@pytest.mark.parametrize(
    "problem", ["duplicate_id", "missing_dependency", "duplicate_sequence", "cycle"]
)
def test_invalid_plan_graphs_are_rejected(plan: ExecutionPlan, problem: str) -> None:
    first, second = plan.steps
    if problem == "duplicate_id":
        steps = (first, second.model_copy(update={"step_id": first.step_id}))
    elif problem == "missing_dependency":
        steps = (first, second.model_copy(update={"depends_on": (new_id(),)}))
    elif problem == "duplicate_sequence":
        steps = (first, second.model_copy(update={"sequence": first.sequence}))
    else:
        steps = (
            first.model_copy(update={"depends_on": (second.step_id,)}),
            second,
        )
    with pytest.raises(ValidationError):
        ExecutionPlan.model_validate({**plan.model_dump(), "steps": steps})


def test_execution_step_lifecycle_is_validated(plan: ExecutionPlan, task_run, now, error) -> None:
    with pytest.raises(ValidationError):
        ExecutionStep(
            step_id=plan.steps[0].step_id,
            task_run_id=task_run.task_run_id,
            plan_id=plan.plan_id,
            status=StepStatus.FAILED,
            started_at=now,
            finished_at=now + timedelta(seconds=1),
        )
    valid = ExecutionStep(
        step_id=plan.steps[0].step_id,
        task_run_id=task_run.task_run_id,
        plan_id=plan.plan_id,
        status=StepStatus.FAILED,
        started_at=now,
        finished_at=now + timedelta(seconds=1),
        error=error,
    )
    assert valid.error == error
