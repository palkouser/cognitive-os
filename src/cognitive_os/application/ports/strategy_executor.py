"""Host-controlled execution boundary for declarative strategy phases."""

from typing import Protocol

from cognitive_os.domain.strategies import (
    StrategyExecutionRequest,
    StrategyPhase,
    StrategyPhaseExecution,
    StrategyPlanInstantiation,
)


class StrategyExecutorPort(Protocol):
    async def execute_phase(
        self,
        request: StrategyExecutionRequest,
        plan: StrategyPlanInstantiation,
        phase: StrategyPhase,
    ) -> StrategyPhaseExecution: ...
