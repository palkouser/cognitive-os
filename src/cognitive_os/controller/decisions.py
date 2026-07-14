"""Deterministic post-verification decisions."""

from enum import StrEnum


class TerminalChoice(StrEnum):
    CANCEL = "cancel"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PAUSE = "pause"
    CLARIFY = "clarify"
    COMPLETE = "complete"
    REPAIR = "repair"
    FAIL = "fail"


def choose_after_verification(
    *,
    cancellation_requested: bool = False,
    budget_exhausted: bool = False,
    approval_pending: bool = False,
    clarification_required: bool = False,
    accepted: bool = False,
    repairable: bool = False,
    repair_budget_remaining: bool = False,
) -> TerminalChoice:
    if cancellation_requested:
        return TerminalChoice.CANCEL
    if budget_exhausted:
        return TerminalChoice.BUDGET_EXHAUSTED
    if approval_pending:
        return TerminalChoice.PAUSE
    if clarification_required:
        return TerminalChoice.CLARIFY
    if accepted:
        return TerminalChoice.COMPLETE
    if repairable and repair_budget_remaining:
        return TerminalChoice.REPAIR
    return TerminalChoice.FAIL
