"""Host-enforced controller budget decisions."""

from __future__ import annotations

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.controller import ControllerBudget, ControllerUsage


class BudgetDecision(ImmutableContractModel):
    allowed: bool
    reason: str
    remaining_provider_calls: int = Field(ge=0)
    remaining_tool_calls: int = Field(ge=0)
    remaining_plan_steps: int = Field(ge=0)
    remaining_repair_cycles: int = Field(ge=0)
    remaining_clarification_cycles: int = Field(ge=0)
    remaining_seconds: float = Field(ge=0)
    remaining_input_tokens: int | None = Field(default=None, ge=0)
    remaining_output_tokens: int | None = Field(default=None, ge=0)
    remaining_cost_units: float | None = Field(default=None, ge=0)


class BudgetLedger:
    def __init__(self, budget: ControllerBudget, usage: ControllerUsage) -> None:
        self.budget = budget
        self.usage = usage

    def evaluate(self, *, elapsed_seconds: float = 0) -> BudgetDecision:
        provider = max(0, self.budget.maximum_provider_calls - self.usage.provider_calls)
        tool = max(0, self.budget.maximum_tool_calls - self.usage.tool_calls)
        steps = max(0, self.budget.maximum_plan_steps - self.usage.plan_steps_started)
        repair = max(0, self.budget.maximum_repair_cycles - self.usage.repair_cycles)
        clarification = max(
            0, self.budget.maximum_clarification_cycles - self.usage.clarification_cycles
        )
        seconds = max(0.0, self.budget.maximum_elapsed_seconds - elapsed_seconds)
        input_tokens = (
            None
            if self.budget.maximum_input_tokens is None
            else max(0, self.budget.maximum_input_tokens - self.usage.input_tokens)
        )
        output_tokens = (
            None
            if self.budget.maximum_output_tokens is None
            else max(0, self.budget.maximum_output_tokens - self.usage.output_tokens)
        )
        cost = (
            None
            if self.budget.maximum_cost_units is None
            else max(0.0, self.budget.maximum_cost_units - self.usage.cost_units)
        )
        candidates: tuple[tuple[str, int | float | None], ...] = (
            ("provider", provider),
            ("tool", tool),
            ("steps", steps),
            ("repair", repair),
            ("clarification", clarification),
            ("seconds", seconds),
            ("input", input_tokens),
            ("output", output_tokens),
            ("cost", cost),
        )
        exhausted = next(
            (name for name, value in candidates if value is not None and value <= 0), None
        )
        return BudgetDecision(
            allowed=exhausted is None,
            reason="within budget" if exhausted is None else f"{exhausted} budget exhausted",
            remaining_provider_calls=provider,
            remaining_tool_calls=tool,
            remaining_plan_steps=steps,
            remaining_repair_cycles=repair,
            remaining_clarification_cycles=clarification,
            remaining_seconds=seconds,
            remaining_input_tokens=input_tokens,
            remaining_output_tokens=output_tokens,
            remaining_cost_units=cost,
        )

    def record(self, **increments: int | float) -> ControllerUsage:
        allowed = set(type(self.usage).model_fields) - {"started_at"}
        unknown = set(increments) - allowed
        if unknown or any(value < 0 for value in increments.values()):
            raise ValueError("usage increments must be known and non-negative")
        values = self.usage.model_dump()
        for key, value in increments.items():
            values[key] += value
        self.usage = ControllerUsage.model_validate(values)
        return self.usage
