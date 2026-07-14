"""Complete Sprint 6 state-transition table."""

from cognitive_os.domain.controller import ControllerState

TRANSITIONS: dict[ControllerState, frozenset[ControllerState]] = {
    ControllerState.RECEIVED: frozenset(
        {ControllerState.REPRESENTING_PROBLEM, ControllerState.CANCELLED}
    ),
    ControllerState.REPRESENTING_PROBLEM: frozenset(
        {
            ControllerState.WAITING_FOR_CLARIFICATION,
            ControllerState.READY,
            ControllerState.FAILED,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.WAITING_FOR_CLARIFICATION: frozenset(
        {
            ControllerState.REPRESENTING_PROBLEM,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.READY: frozenset({ControllerState.PLANNING, ControllerState.CANCELLED}),
    ControllerState.PLANNING: frozenset(
        {
            ControllerState.EXECUTING,
            ControllerState.WAITING_FOR_CLARIFICATION,
            ControllerState.FAILED,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.EXECUTING: frozenset(
        {
            ControllerState.VERIFYING,
            ControllerState.PAUSED,
            ControllerState.FAILED,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.VERIFYING: frozenset(
        {
            ControllerState.COMPLETED,
            ControllerState.REPAIRING,
            ControllerState.WAITING_FOR_CLARIFICATION,
            ControllerState.FAILED,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.REPAIRING: frozenset(
        {
            ControllerState.EXECUTING,
            ControllerState.FAILED,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.PAUSED: frozenset(
        {
            ControllerState.EXECUTING,
            ControllerState.VERIFYING,
            ControllerState.CANCELLED,
            ControllerState.BUDGET_EXHAUSTED,
        }
    ),
    ControllerState.COMPLETED: frozenset(),
    ControllerState.FAILED: frozenset(),
    ControllerState.CANCELLED: frozenset(),
    ControllerState.BUDGET_EXHAUSTED: frozenset(),
}
