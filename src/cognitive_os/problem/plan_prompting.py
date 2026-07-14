"""Bounded sequential-plan prompt construction."""

import json

from cognitive_os.domain.controller import ControllerBudget
from cognitive_os.domain.problems import ProblemRepresentation


def plan_instructions(problem: ProblemRepresentation, budget: ControllerBudget) -> str:
    return (
        "Create a sequential ControllerExecutionPlan matching the supplied schema. "
        "Do not invent providers, tools, verifiers, permissions, parallel actions, or subtasks. "
        f"Maximum steps: {budget.maximum_plan_steps}. "
        f"Problem: {json.dumps(problem.model_dump(mode='json'), sort_keys=True)}"
    )
