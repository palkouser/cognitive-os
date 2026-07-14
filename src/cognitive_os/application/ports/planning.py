"""Controller planning boundary."""

from typing import Protocol

from cognitive_os.domain.controller import ControllerBudget
from cognitive_os.domain.planning import ControllerExecutionPlan
from cognitive_os.domain.problems import ProblemRepresentation


class PlanningPort(Protocol):
    async def create_plan(
        self, problem: ProblemRepresentation, budget: ControllerBudget
    ) -> ControllerExecutionPlan: ...
    async def revise_plan(
        self, current: ControllerExecutionPlan, reason: str, budget: ControllerBudget
    ) -> ControllerExecutionPlan: ...
