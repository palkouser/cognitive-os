"""Infrastructure-free controller transition machine."""

from dataclasses import dataclass
from uuid import UUID

from cognitive_os.domain.controller import TERMINAL_CONTROLLER_STATES, ControllerState

from .errors import IllegalControllerTransition
from .transitions import TRANSITIONS


@dataclass(frozen=True)
class StateTransition:
    current: ControllerState
    target: ControllerState
    reason: str
    decision_id: UUID
    expected_stream_version: int


class ControllerStateMachine:
    @staticmethod
    def can_transition(current: ControllerState, target: ControllerState) -> bool:
        return target in TRANSITIONS[current]

    @classmethod
    def require_transition(cls, transition: StateTransition) -> None:
        if not transition.reason.strip():
            raise IllegalControllerTransition("transition reason must be non-empty")
        if transition.expected_stream_version < 0:
            raise IllegalControllerTransition("expected stream version must be non-negative")
        if not cls.can_transition(transition.current, transition.target):
            raise IllegalControllerTransition(
                f"illegal controller transition: {transition.current} -> {transition.target}"
            )

    @classmethod
    def transition(cls, transition: StateTransition) -> ControllerState:
        cls.require_transition(transition)
        return transition.target

    @staticmethod
    def is_terminal(state: ControllerState) -> bool:
        return state in TERMINAL_CONTROLLER_STATES

    @staticmethod
    def is_waiting(state: ControllerState) -> bool:
        return state in {ControllerState.WAITING_FOR_CLARIFICATION, ControllerState.PAUSED}
