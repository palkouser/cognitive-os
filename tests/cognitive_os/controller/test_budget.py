from datetime import UTC, datetime

from cognitive_os.controller.budget import BudgetLedger
from cognitive_os.domain.controller import ControllerBudget, ControllerUsage


def test_budget_is_host_enforced_at_exact_limit() -> None:
    now = datetime.now(UTC)
    budget = ControllerBudget(
        maximum_provider_calls=1,
        maximum_tool_calls=1,
        maximum_plan_steps=1,
        maximum_repair_cycles=1,
        maximum_clarification_cycles=1,
        maximum_elapsed_seconds=10,
        maximum_input_tokens=10,
        maximum_output_tokens=10,
    )
    ledger = BudgetLedger(budget, ControllerUsage(started_at=now, last_updated_at=now))
    assert ledger.evaluate().allowed
    ledger.record(provider_calls=1)
    decision = ledger.evaluate()
    assert not decision.allowed
    assert decision.remaining_provider_calls == 0


def test_budget_object_cannot_be_mutated_by_provider_output() -> None:
    now = datetime.now(UTC)
    budget = ControllerBudget(
        maximum_provider_calls=1,
        maximum_tool_calls=1,
        maximum_plan_steps=1,
        maximum_repair_cycles=1,
        maximum_clarification_cycles=1,
        maximum_elapsed_seconds=10,
    )
    usage = ControllerUsage(started_at=now, last_updated_at=now)
    BudgetLedger(budget, usage).record(provider_calls=1)
    assert budget.maximum_provider_calls == 1
