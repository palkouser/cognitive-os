"""Credential-free deterministic Sprint 6 controller primitive smoke test."""

from datetime import UTC, datetime
from uuid import uuid4

from cognitive_os.controller.budget import BudgetLedger
from cognitive_os.controller.checkpoint import ContinuationTokenService
from cognitive_os.controller.machine import ControllerStateMachine, StateTransition
from cognitive_os.domain.controller import ControllerBudget, ControllerState, ControllerUsage


def main() -> None:
    now = datetime.now(UTC)
    budget = ControllerBudget(
        maximum_provider_calls=2,
        maximum_tool_calls=2,
        maximum_plan_steps=2,
        maximum_repair_cycles=1,
        maximum_clarification_cycles=1,
        maximum_elapsed_seconds=30,
    )
    assert (
        BudgetLedger(budget, ControllerUsage(started_at=now, last_updated_at=now))
        .evaluate()
        .allowed
    )
    assert (
        ControllerStateMachine.transition(
            StateTransition(
                ControllerState.RECEIVED,
                ControllerState.REPRESENTING_PROBLEM,
                "offline smoke",
                uuid4(),
                0,
            )
        )
        is ControllerState.REPRESENTING_PROBLEM
    )
    token, record = ContinuationTokenService(lambda: "smoke-only-value").issue(
        task_run_id=uuid4(),
        checkpoint_id=uuid4(),
        event_stream_version=1,
        ttl_seconds=60,
        now=now,
    )
    assert token != record.token_hash
    print("Controller primitive smoke test passed.")


if __name__ == "__main__":
    main()
