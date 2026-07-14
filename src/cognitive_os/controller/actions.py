"""Deterministic one-step-at-a-time scheduler."""

from uuid import UUID

from cognitive_os.domain.execution import PlanStepDefinition
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction


def ready_steps(
    plan: ControllerExecutionPlan,
    *,
    completed: frozenset[UUID],
    failed: frozenset[UUID],
) -> tuple[PlanStepDefinition, ...]:
    known = {step.step_id for step in plan.plan.steps}
    if (completed | failed) - known or completed & failed:
        raise ValueError("inconsistent scheduler dependency state")
    return tuple(
        step
        for step in plan.plan.steps
        if step.step_id not in completed | failed
        and set(step.depends_on) <= completed
        and not set(step.depends_on) & failed
    )


def select_next_action(
    plan: ControllerExecutionPlan,
    *,
    completed: frozenset[UUID] = frozenset(),
    failed: frozenset[UUID] = frozenset(),
) -> ControllerStepAction | None:
    candidates = sorted(
        ready_steps(plan, completed=completed, failed=failed),
        key=lambda step: (step.sequence, str(step.step_id)),
    )
    if not candidates:
        return None
    selected = candidates[0].step_id
    return next(action for action in plan.actions if action.step_id == selected)
