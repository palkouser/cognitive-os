from uuid import uuid4

import pytest

from cognitive_os.controller.errors import IllegalControllerTransition
from cognitive_os.controller.machine import ControllerStateMachine, StateTransition
from cognitive_os.controller.transitions import TRANSITIONS
from cognitive_os.domain.controller import ControllerState


@pytest.mark.parametrize("source", tuple(ControllerState))
@pytest.mark.parametrize("target", tuple(ControllerState))
def test_all_controller_transition_pairs(source: ControllerState, target: ControllerState) -> None:
    transition = StateTransition(source, target, "tested", uuid4(), 0)
    if target in TRANSITIONS[source]:
        assert ControllerStateMachine.transition(transition) is target
    else:
        with pytest.raises(IllegalControllerTransition):
            ControllerStateMachine.transition(transition)
