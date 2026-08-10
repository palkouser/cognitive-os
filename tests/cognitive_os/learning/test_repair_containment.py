"""The containment signal, tested on the two properties the D7 class leans on.

Whether the share ranks anything is a measurement on a fresh corpus, not a unit test. What is
testable now is what the module claims for itself and what W2 would have to stop on:

*The share is the arithmetic it says it is.* One group of hand-computable sources, every share
read off by hand and compared, including the asymmetry that makes the signal informative — a
complete repair contains both partial ones, a partial repair contains neither its sibling nor
half of a complete one.

*A consistent rename cannot move the ordering.* The frozen six-case generator renames every
source in a group with one map, and the module's whole invariance argument is that a bijection
on tokens is a bijection on stripped lines. The test applies a rename to every source and
demands identical shares, not merely an identical order.

*The degenerate group falls back rather than fails.* A group where nothing is added — the
pure-deletion case §5.1 sends the vertical slice at — scores every candidate zero and leaves
the frozen baseline order standing.
"""

from __future__ import annotations

import pytest

from cognitive_os.learning.repair_containment import (
    REPAIR_CONTAINMENT_CHANNEL,
    added_lines,
    containment_ordering,
    containment_shares,
    repair_lines,
)

BASELINE = """
def normalise(values):
    return values
"""

#: The frozen anatomy: two complete repairs by different routes, two partial ones.
COMPLETE_A = """
def normalise(values):
    if values is None:
        return []
    if not values:
        return []
    return values
"""
COMPLETE_B = """
def normalise(values):
    if not values:
        return []
    if values is None:
        return []
    return values
"""
PARTIAL_NONE = """
def normalise(values):
    if values is None:
        return []
    return values
"""
PARTIAL_EMPTY = """
def normalise(values):
    if not values:
        return []
    return values
"""

GROUP = {
    "complete-a": COMPLETE_A,
    "complete-b": COMPLETE_B,
    "partial-none": PARTIAL_NONE,
    "partial-empty": PARTIAL_EMPTY,
}
ORDER = ("partial-empty", "complete-a", "partial-none", "complete-b")


def _renamed(source: str) -> str:
    """One map over every token, the way `transformations_d3` renames a whole group."""
    return source.replace("normalise", "__cogos_s0001_b0001").replace("values", "__cogos_s0002")


def test_the_shares_are_the_arithmetic_the_module_claims() -> None:
    """Hand-computed: the two complete repairs add both guards, the partials one each."""
    assert added_lines(BASELINE, PARTIAL_NONE) == frozenset({"if values is None:", "return []"})
    shares = containment_shares(BASELINE, GROUP)

    # A complete repair contains every other candidate's added lines: both partials entirely,
    # and its sibling, which differs from it only in the order of the two guards.
    assert shares["complete-a"] == pytest.approx(1.0)
    assert shares["complete-b"] == pytest.approx(1.0)
    # A partial repair contains its own two lines out of a complete repair's three, and shares
    # only `return []` — one of its sibling's two lines — with the other partial.
    assert shares["partial-none"] == pytest.approx((2 / 3 + 2 / 3 + 1 / 2) / 3)
    assert shares["partial-empty"] == pytest.approx(shares["partial-none"])
    assert shares["complete-a"] > shares["partial-none"]


def test_the_ordering_ranks_containment_and_breaks_ties_on_the_baseline() -> None:
    ordered = containment_ordering(BASELINE, GROUP, baseline_order=ORDER)

    # Both complete repairs score 1.0, so the tie falls to the frozen order, not to the ID.
    assert ordered == ("complete-a", "complete-b", "partial-empty", "partial-none")
    reordered = ("complete-b", "complete-a", "partial-none", "partial-empty")
    assert containment_ordering(BASELINE, GROUP, baseline_order=reordered) == reordered


def test_a_consistent_rename_moves_neither_a_share_nor_the_ordering() -> None:
    """The invariance argument, exercised rather than asserted in prose."""
    renamed = {candidate: _renamed(source) for candidate, source in GROUP.items()}
    assert renamed != GROUP

    assert containment_shares(_renamed(BASELINE), renamed) == containment_shares(BASELINE, GROUP)
    assert containment_ordering(
        _renamed(BASELINE), renamed, baseline_order=ORDER
    ) == containment_ordering(BASELINE, GROUP, baseline_order=ORDER)


def test_a_pure_deletion_group_scores_zero_and_keeps_the_baseline_order() -> None:
    """§5.1's degenerate case: nothing is added, so nothing is contained."""
    deletions = {name: "def normalise(values):\n    return values\n" for name in ORDER}
    shares = containment_shares(BASELINE, deletions)

    assert set(shares.values()) == {0.0}
    assert containment_ordering(BASELINE, deletions, baseline_order=ORDER) == ORDER


def test_whitespace_and_blank_lines_do_not_reach_the_signal() -> None:
    """Lines are stripped, so a reindentation of the whole group is not a repair."""
    assert repair_lines("  a  \n\n\tb\n") == frozenset({"a", "b"})
    indented = {name: source.replace("    ", "\t") for name, source in GROUP.items()}
    assert containment_shares(BASELINE, indented) == containment_shares(BASELINE, GROUP)


def test_the_module_refuses_what_it_cannot_relate() -> None:
    with pytest.raises(ValueError, match="at least two candidates"):
        containment_shares(BASELINE, {"only": COMPLETE_A})
    with pytest.raises(ValueError, match="disagree"):
        containment_ordering(BASELINE, GROUP, baseline_order=ORDER[:3])


def test_the_channel_name_is_the_one_the_class_fits() -> None:
    assert REPAIR_CONTAINMENT_CHANNEL == "repair_containment_share"
