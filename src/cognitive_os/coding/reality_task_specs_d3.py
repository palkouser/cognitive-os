"""The Sprint 21D3 calibration corpus: twenty fresh groups plus one vertical-slice fixture.

D3 reuses D2's fifty training groups, so the only correction tasks that have to be authored are
the twenty calibration groups S21D3-030 requires — genuinely new, and group, clone and source
disjoint from every D2 calibration, final, canary and D3 retrieval group.

The spec shape is D2's, deliberately. `D2TaskSpec` already carries four variants under a
per-task recipe binding, and re-declaring an identical dataclass under a D3 name would give the
catalogue two shapes to agree about. What is new is the eligibility contract these twenty have
to satisfy that D2's did not: S21D3-015 freezes six metamorphic cases per group, four of which
rename an identifier, so every task here binds a source-local name the independent generator can
rename coherently — a module-level function plus locals of its own — and none of them reaches a
name through `getattr`, `globals()` or any other reflective route, which `correction_source.py`
refuses outright.

The vertical-slice fixture at the bottom is not part of the corpus. S21D3-033 spends a whole
group proving the pipeline end to end, and spending a calibration member on it would take a
scored group out of the twenty before a single number was read.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# ------------------------------------------------------------------ boundary and collections

_C1 = D2TaskSpec(
    template_id="d3_boundary.tail_after",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d3-boundary-tail-after",
    module="tail_segments",
    module_doc="Reading the part of a sequence that follows a marker.",
    issue=(
        "tail_after() is documented to return everything after the last occurrence of a marker. "
        "Callers report a crash when the marker is absent, and that a sequence carrying the "
        "marker twice is cut at the first one."
    ),
    expected=(
        "tail_after(items, marker) returns the items following the last occurrence of marker, "
        "returns an empty list when marker is absent, and cuts at the last occurrence when the "
        "marker appears more than once."
    ),
    baseline_reason="it cuts at the first occurrence and index() raises when the marker is absent",
    edge_cases=(
        "an absent marker returns an empty list",
        "a repeated marker cuts at the last occurrence",
    ),
    baseline="""def tail_after(items, marker):
    \"\"\"Return the items after the last occurrence of `marker`.\"\"\"
    collected = list(items)
    position = collected.index(marker)
    return collected[position + 1 :]""",
    variant_one="""def tail_after(items, marker):
    \"\"\"Return the items after the last occurrence of `marker`.\"\"\"
    collected = list(items)
    if marker not in collected:
        return []
    position = len(collected) - 1 - collected[::-1].index(marker)
    return collected[position + 1 :]""",
    variant_two="""def tail_after(items, marker):
    \"\"\"Return the items after the last occurrence of `marker`.\"\"\"
    tail = []
    seen = False
    for entry in items:
        if entry == marker:
            tail = []
            seen = True
        else:
            tail.append(entry)
    return tail if seen else []""",
    variant_three="""def tail_after(items, marker):
    \"\"\"Return the items after the last occurrence of `marker`.\"\"\"
    collected = list(items)
    if marker not in collected:
        return []
    return collected[collected.index(marker) + 1 :]""",
    variant_four="""def tail_after(items, marker):
    \"\"\"Return the items after the last occurrence of `marker`.\"\"\"
    collected = list(items)
    position = len(collected) - 1 - collected[::-1].index(marker)
    return collected[position + 1 :]""",
    visible_test=_test_module(
        "tail_segments",
        "Published contract for reading a trailing segment.",
        """
def test_items_after_a_single_marker() -> None:
    assert tail_after([1, 2, 3, 4], 2) == [3, 4]


def test_a_marker_at_the_end_yields_nothing() -> None:
    assert tail_after([1, 2], 2) == []
""",
        imports="from tail_segments import tail_after\n",
    ),
    hidden_test=_test_module(
        "tail_segments",
        "The part of the contract the published tests do not state.",
        """
def test_items_after_a_single_marker() -> None:
    assert tail_after([1, 2, 3, 4], 2) == [3, 4]


def test_an_absent_marker_returns_an_empty_list() -> None:
    assert tail_after([1, 2, 3], 9) == []


def test_a_repeated_marker_cuts_at_the_last_occurrence() -> None:
    assert tail_after([1, 2, 3, 2, 5], 2) == [5]
""",
        imports="from tail_segments import tail_after\n",
    ),
)

_C2 = D2TaskSpec(
    template_id="d3_boundary.head_within",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d3-boundary-head-within",
    module="budget_prefix",
    module_doc="Taking the leading run of a sequence that fits a budget.",
    issue=(
        "head_within() is documented to return the longest leading run whose running total stays "
        "within a budget. Callers report that it keeps scanning past the first item that does "
        "not fit, and that an item landing exactly on the budget is dropped."
    ),
    expected=(
        "head_within(values, budget) returns the longest prefix whose running total is at most "
        "budget, stops at the first item that would exceed it, and keeps an item whose total "
        "lands exactly on the budget."
    ),
    baseline_reason=(
        "it filters instead of stopping, and compares below the budget instead of at it"
    ),
    edge_cases=(
        "scanning stops at the first item that does not fit",
        "a total landing exactly on the budget is kept",
    ),
    baseline="""def head_within(values, budget):
    \"\"\"Return the longest prefix of `values` whose running total stays within `budget`.\"\"\"
    total = 0
    kept = []
    for value in values:
        if total + value < budget:
            total += value
            kept.append(value)
    return kept""",
    variant_one="""def head_within(values, budget):
    \"\"\"Return the longest prefix of `values` whose running total stays within `budget`.\"\"\"
    total = 0
    kept = []
    for value in values:
        if total + value > budget:
            break
        total += value
        kept.append(value)
    return kept""",
    variant_two="""def head_within(values, budget):
    \"\"\"Return the longest prefix of `values` whose running total stays within `budget`.\"\"\"
    from itertools import accumulate, takewhile

    collected = list(values)
    fitting = list(takewhile(lambda total: total <= budget, accumulate(collected)))
    return collected[: len(fitting)]""",
    variant_three="""def head_within(values, budget):
    \"\"\"Return the longest prefix of `values` whose running total stays within `budget`.\"\"\"
    total = 0
    kept = []
    for value in values:
        if total + value >= budget:
            break
        total += value
        kept.append(value)
    return kept""",
    variant_four="""def head_within(values, budget):
    \"\"\"Return the longest prefix of `values` whose running total stays within `budget`.\"\"\"
    total = 0
    kept = []
    for value in values:
        if total + value <= budget:
            total += value
            kept.append(value)
    return kept""",
    visible_test=_test_module(
        "budget_prefix",
        "Published contract for the budgeted prefix.",
        """
def test_a_prefix_well_inside_the_budget_is_returned_whole() -> None:
    assert head_within([1, 2, 3], 10) == [1, 2, 3]


def test_a_budget_of_zero_yields_nothing() -> None:
    assert head_within([1, 2], 0) == []
""",
        imports="from budget_prefix import head_within\n",
    ),
    hidden_test=_test_module(
        "budget_prefix",
        "The part of the contract the published tests do not state.",
        """
def test_a_prefix_well_inside_the_budget_is_returned_whole() -> None:
    assert head_within([1, 2, 3], 10) == [1, 2, 3]


def test_scanning_stops_at_the_first_item_that_does_not_fit() -> None:
    assert head_within([1, 5, 1], 3) == [1]


def test_a_total_landing_exactly_on_the_budget_is_kept() -> None:
    assert head_within([2, 2], 4) == [2, 2]
""",
        imports="from budget_prefix import head_within\n",
    ),
)

_C3 = D2TaskSpec(
    template_id="d3_boundary.centre_window",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d3-boundary-centre-window",
    module="centre_windows",
    module_doc="Taking a window of fixed width from the middle of a sequence.",
    issue=(
        "centre_window() is documented to return a window of the requested width taken from the "
        "middle of a sequence. Callers report that a width above the length loses items, and "
        "that an odd leftover leans the wrong way."
    ),
    expected=(
        "centre_window(items, width) returns width items centred in the sequence, returns the "
        "whole sequence when width reaches its length, and gives the extra leftover item to the "
        "left side when the leftover is odd."
    ),
    baseline_reason="the margin goes negative for a wide window and leans right on an odd leftover",
    edge_cases=(
        "a width above the length returns the whole sequence",
        "an odd leftover leans left",
    ),
    baseline="""def centre_window(items, width):
    \"\"\"Return `width` items taken from the middle of `items`.\"\"\"
    collected = list(items)
    margin = (len(collected) - width) // 2
    return collected[margin : margin + width]""",
    variant_one="""def centre_window(items, width):
    \"\"\"Return `width` items taken from the middle of `items`.\"\"\"
    collected = list(items)
    if width >= len(collected):
        return collected
    margin = (len(collected) - width + 1) // 2
    return collected[margin : margin + width]""",
    variant_two="""def centre_window(items, width):
    \"\"\"Return `width` items taken from the middle of `items`.\"\"\"
    collected = list(items)
    span = min(max(width, 0), len(collected))
    leftover = len(collected) - span
    margin = (leftover + 1) // 2
    return collected[margin : margin + span]""",
    variant_three="""def centre_window(items, width):
    \"\"\"Return `width` items taken from the middle of `items`.\"\"\"
    collected = list(items)
    margin = (len(collected) - width + 1) // 2
    return collected[margin : margin + width]""",
    variant_four="""def centre_window(items, width):
    \"\"\"Return `width` items taken from the middle of `items`.\"\"\"
    collected = list(items)
    if width >= len(collected):
        return collected
    margin = (len(collected) - width) // 2
    return collected[margin : margin + width]""",
    visible_test=_test_module(
        "centre_windows",
        "Published contract for the centred window.",
        """
def test_a_narrow_window_is_centred() -> None:
    assert centre_window([1, 2, 3, 4, 5], 3) == [2, 3, 4]


def test_a_window_of_zero_is_empty() -> None:
    assert centre_window([1, 2, 3], 0) == []
""",
        imports="from centre_windows import centre_window\n",
    ),
    hidden_test=_test_module(
        "centre_windows",
        "The part of the contract the published tests do not state.",
        """
def test_a_narrow_window_is_centred() -> None:
    assert centre_window([1, 2, 3, 4, 5], 3) == [2, 3, 4]


def test_a_wide_window_returns_the_whole_sequence() -> None:
    assert centre_window([1, 2, 3], 7) == [1, 2, 3]


def test_an_odd_leftover_leans_left() -> None:
    assert centre_window([1, 2, 3, 4], 3) == [2, 3, 4]
""",
        imports="from centre_windows import centre_window\n",
    ),
)

_C4 = D2TaskSpec(
    template_id="d3_boundary.step_gaps",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d3-boundary-step-gaps",
    module="step_gaps",
    module_doc="Differences between neighbouring readings.",
    issue=(
        "step_gaps() is documented to return the difference between each pair of neighbouring "
        "readings. Callers report a crash for a single reading, and an empty answer when the "
        "readings arrive as a one-shot iterator."
    ),
    expected=(
        "step_gaps(readings) returns one difference per neighbouring pair, returns an empty list "
        "for fewer than two readings, and accepts any iterable including a one-shot iterator."
    ),
    baseline_reason="it walks the argument three times and indexes past the end for one reading",
    edge_cases=(
        "one reading gives an empty list",
        "a one-shot iterator is materialised before it is walked",
    ),
    baseline="""def step_gaps(readings):
    \"\"\"Return the difference between each pair of neighbouring readings.\"\"\"
    steps = [
        second - first
        for first, second in zip(list(readings)[:-1], list(readings)[1:])
    ]
    if not steps and list(readings):
        return [list(readings)[0]]
    return steps""",
    variant_one="""def step_gaps(readings):
    \"\"\"Return the difference between each pair of neighbouring readings.\"\"\"
    collected = list(readings)
    if len(collected) < 2:
        return []
    return [second - first for first, second in zip(collected[:-1], collected[1:])]""",
    variant_two="""def step_gaps(readings):
    \"\"\"Return the difference between each pair of neighbouring readings.\"\"\"
    from itertools import pairwise

    return [second - first for first, second in pairwise(list(readings))]""",
    variant_three="""def step_gaps(readings):
    \"\"\"Return the difference between each pair of neighbouring readings.\"\"\"
    steps = [
        second - first
        for first, second in zip(list(readings)[:-1], list(readings)[1:])
    ]
    return steps""",
    variant_four="""def step_gaps(readings):
    \"\"\"Return the difference between each pair of neighbouring readings.\"\"\"
    collected = list(readings)
    steps = [second - first for first, second in zip(collected[:-1], collected[1:])]
    if not steps and collected:
        return [collected[0]]
    return steps""",
    visible_test=_test_module(
        "step_gaps",
        "Published contract for neighbouring differences.",
        """
def test_differences_between_three_readings() -> None:
    assert step_gaps([1, 4, 9]) == [3, 5]


def test_two_readings_give_one_difference() -> None:
    assert step_gaps([2, 7]) == [5]
""",
        imports="from step_gaps import step_gaps\n",
    ),
    hidden_test=_test_module(
        "step_gaps",
        "The part of the contract the published tests do not state.",
        """
def test_differences_between_three_readings() -> None:
    assert step_gaps([1, 4, 9]) == [3, 5]


def test_one_reading_gives_no_differences() -> None:
    assert step_gaps([5]) == []


def test_a_one_shot_iterator_is_walked_once() -> None:
    assert step_gaps(iter([2, 5, 6])) == [3, 1]
""",
        imports="from step_gaps import step_gaps\n",
    ),
)

# ----------------------------------------------------------------- parsing and validation

_C5 = D2TaskSpec(
    template_id="d3_parsing.parse_pair",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d3-parsing-pair",
    module="pair_syntax",
    module_doc="Reading a name and value out of an assignment.",
    issue=(
        "parse_pair() is documented to split an assignment into its name and value. Callers "
        "report that a value carrying its own equals sign is truncated, and that text without "
        "an equals sign returns something instead of being rejected."
    ),
    expected=(
        "parse_pair(text) returns (name, value) split at the first equals sign only, keeps any "
        "further equals signs inside the value, and raises ValueError when there is none."
    ),
    baseline_reason="it splits on every equals sign and returns a pair for text without one",
    edge_cases=(
        "a value containing an equals sign is kept whole",
        "text without an equals sign raises ValueError",
    ),
    baseline="""def parse_pair(text):
    \"\"\"Return the (name, value) pair described by `text`.\"\"\"
    parts = text.split("=")
    return parts[0], parts[-1]""",
    variant_one="""def parse_pair(text):
    \"\"\"Return the (name, value) pair described by `text`.\"\"\"
    if "=" not in text:
        raise ValueError(f"not an assignment: {text!r}")
    name, value = text.split("=", 1)
    return name, value""",
    variant_two="""def parse_pair(text):
    \"\"\"Return the (name, value) pair described by `text`.\"\"\"
    name, separator, value = text.partition("=")
    if not separator:
        raise ValueError(f"not an assignment: {text!r}")
    return name, value""",
    variant_three="""def parse_pair(text):
    \"\"\"Return the (name, value) pair described by `text`.\"\"\"
    parts = text.split("=", 1)
    return parts[0], parts[-1]""",
    variant_four="""def parse_pair(text):
    \"\"\"Return the (name, value) pair described by `text`.\"\"\"
    if "=" not in text:
        raise ValueError(f"not an assignment: {text!r}")
    parts = text.split("=")
    return parts[0], parts[-1]""",
    visible_test=_test_module(
        "pair_syntax",
        "Published contract for reading an assignment.",
        """
def test_a_simple_assignment() -> None:
    assert parse_pair("host=local") == ("host", "local")


def test_an_empty_value_is_allowed() -> None:
    assert parse_pair("host=") == ("host", "")
""",
        imports="from pair_syntax import parse_pair\n",
    ),
    hidden_test=_test_module(
        "pair_syntax",
        "The part of the contract the published tests do not state.",
        """
import pytest

from pair_syntax import parse_pair


def test_a_simple_assignment() -> None:
    assert parse_pair("host=local") == ("host", "local")


def test_a_value_containing_an_equals_sign_is_kept_whole() -> None:
    assert parse_pair("token=a=b") == ("token", "a=b")


def test_text_without_an_equals_sign_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_pair("host")
""",
    ),
)

_C6 = D2TaskSpec(
    template_id="d3_parsing.parse_signed",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d3-parsing-signed",
    module="signed_numbers",
    module_doc="Reading a signed integer written by a human.",
    issue=(
        "parse_signed() is documented to read an integer that may carry an explicit sign. "
        "Callers report that a leading plus reads as zero, and that blank text is read as zero "
        "instead of being refused."
    ),
    expected=(
        "parse_signed(text) returns the integer described by text, accepts an explicit leading "
        "plus or minus, and raises ValueError for text that holds no digits."
    ),
    baseline_reason="it strips only the minus and falls back to zero for anything else",
    edge_cases=(
        "an explicit leading plus is accepted",
        "blank text raises ValueError",
    ),
    baseline="""def parse_signed(text):
    \"\"\"Return the integer described by `text`.\"\"\"
    body = text.strip()
    negative = body.startswith("-")
    digits = body.lstrip("-")
    if not digits.isdigit():
        return 0
    return -int(digits) if negative else int(digits)""",
    variant_one="""def parse_signed(text):
    \"\"\"Return the integer described by `text`.\"\"\"
    body = text.strip()
    sign = -1 if body.startswith("-") else 1
    digits = body.lstrip("+-")
    if not digits.isdigit():
        raise ValueError(f"not a signed integer: {text!r}")
    return sign * int(digits)""",
    variant_two="""def parse_signed(text):
    \"\"\"Return the integer described by `text`.\"\"\"
    body = text.strip()
    try:
        return int(body)
    except ValueError as error:
        raise ValueError(f"not a signed integer: {text!r}") from error""",
    variant_three="""def parse_signed(text):
    \"\"\"Return the integer described by `text`.\"\"\"
    body = text.strip()
    sign = -1 if body.startswith("-") else 1
    digits = body.lstrip("+-")
    if not digits.isdigit():
        return 0
    return sign * int(digits)""",
    variant_four="""def parse_signed(text):
    \"\"\"Return the integer described by `text`.\"\"\"
    body = text.strip()
    negative = body.startswith("-")
    digits = body.lstrip("-")
    if not digits.isdigit():
        raise ValueError(f"not a signed integer: {text!r}")
    return -int(digits) if negative else int(digits)""",
    visible_test=_test_module(
        "signed_numbers",
        "Published contract for reading a signed integer.",
        """
def test_a_plain_number() -> None:
    assert parse_signed("12") == 12


def test_a_negative_number() -> None:
    assert parse_signed("-3") == -3
""",
        imports="from signed_numbers import parse_signed\n",
    ),
    hidden_test=_test_module(
        "signed_numbers",
        "The part of the contract the published tests do not state.",
        """
import pytest

from signed_numbers import parse_signed


def test_a_plain_number() -> None:
    assert parse_signed("12") == 12


def test_an_explicit_leading_plus_is_accepted() -> None:
    assert parse_signed("+7") == 7


def test_blank_text_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_signed("   ")
""",
    ),
)

_C7 = D2TaskSpec(
    template_id="d3_parsing.tidy_route",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d3-parsing-route",
    module="route_text",
    module_doc="Tidying a slash-separated route.",
    issue=(
        "tidy_route() is documented to collapse repeated separators and drop a trailing one. "
        "Callers report that a relative route gains a leading separator it never had, and that "
        "an empty route becomes a separator."
    ),
    expected=(
        "tidy_route(route) collapses repeated separators, drops a trailing one, leaves a "
        "relative route relative, and returns an empty route unchanged."
    ),
    baseline_reason="it rebuilds the route from its segments and always prepends a separator",
    edge_cases=(
        "a relative route does not gain a leading separator",
        "an empty route stays empty",
    ),
    baseline="""def tidy_route(route):
    \"\"\"Return `route` with repeated separators collapsed and no trailing one.\"\"\"
    segments = [segment for segment in route.split("/") if segment]
    return "/" + "/".join(segments)""",
    variant_one="""def tidy_route(route):
    \"\"\"Return `route` with repeated separators collapsed and no trailing one.\"\"\"
    segments = [segment for segment in route.split("/") if segment]
    leading = "/" if route.startswith("/") else ""
    if not segments:
        return leading if route else ""
    return leading + "/".join(segments)""",
    variant_two="""def tidy_route(route):
    \"\"\"Return `route` with repeated separators collapsed and no trailing one.\"\"\"
    import re

    collapsed = re.sub("/+", "/", route)
    if collapsed == "/":
        return collapsed
    return collapsed.rstrip("/")""",
    variant_three="""def tidy_route(route):
    \"\"\"Return `route` with repeated separators collapsed and no trailing one.\"\"\"
    segments = [segment for segment in route.split("/") if segment]
    if not segments:
        return "/"
    leading = "/" if route.startswith("/") else ""
    return leading + "/".join(segments)""",
    variant_four="""def tidy_route(route):
    \"\"\"Return `route` with repeated separators collapsed and no trailing one.\"\"\"
    segments = [segment for segment in route.split("/") if segment]
    if not segments:
        return route
    return "/" + "/".join(segments)""",
    visible_test=_test_module(
        "route_text",
        "Published contract for tidying a route.",
        """
def test_repeated_separators_collapse() -> None:
    assert tidy_route("/a//b") == "/a/b"


def test_a_trailing_separator_is_dropped() -> None:
    assert tidy_route("/a/b/") == "/a/b"
""",
        imports="from route_text import tidy_route\n",
    ),
    hidden_test=_test_module(
        "route_text",
        "The part of the contract the published tests do not state.",
        """
def test_repeated_separators_collapse() -> None:
    assert tidy_route("/a//b") == "/a/b"


def test_a_relative_route_does_not_gain_a_leading_separator() -> None:
    assert tidy_route("a/b") == "a/b"


def test_an_empty_route_stays_empty() -> None:
    assert tidy_route("") == ""
""",
        imports="from route_text import tidy_route\n",
    ),
)

_C8 = D2TaskSpec(
    template_id="d3_parsing.parse_ratio",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d3-parsing-ratio",
    module="ratio_syntax",
    module_doc="Reading a colon-separated ratio.",
    issue=(
        "parse_ratio() is documented to read a ratio written as two numbers around a colon and "
        "to report it in lowest terms. Callers report that the terms come back unreduced, and "
        "that a zero second term is accepted even though nothing can divide by it."
    ),
    expected=(
        "parse_ratio(text) returns (left, right) in lowest terms and raises ValueError when the "
        "second term is zero."
    ),
    baseline_reason="it converts the raw pieces, never reduces them and never checks the divisor",
    edge_cases=(
        "the returned ratio is in lowest terms",
        "a zero second term raises ValueError",
    ),
    baseline="""def parse_ratio(text):
    \"\"\"Return the (left, right) integers described by `text`, in lowest terms.\"\"\"
    pieces = text.split(":")
    return int(pieces[0]), int(pieces[1])""",
    variant_one="""def parse_ratio(text):
    \"\"\"Return the (left, right) integers described by `text`, in lowest terms.\"\"\"
    from math import gcd

    left, right = (int(piece) for piece in text.split(":"))
    if right == 0:
        raise ValueError(f"a ratio cannot divide by zero: {text!r}")
    divisor = gcd(left, right)
    return left // divisor, right // divisor""",
    variant_two="""def parse_ratio(text):
    \"\"\"Return the (left, right) integers described by `text`, in lowest terms.\"\"\"
    from fractions import Fraction

    numbers = [int(piece) for piece in text.split(":")]
    if numbers[1] == 0:
        raise ValueError(f"a ratio cannot divide by zero: {text!r}")
    ratio = Fraction(numbers[0], numbers[1])
    return ratio.numerator, ratio.denominator""",
    variant_three="""def parse_ratio(text):
    \"\"\"Return the (left, right) integers described by `text`, in lowest terms.\"\"\"
    from math import gcd

    left, right = (int(piece) for piece in text.split(":"))
    divisor = gcd(left, right)
    return left // divisor, right // divisor""",
    variant_four="""def parse_ratio(text):
    \"\"\"Return the (left, right) integers described by `text`, in lowest terms.\"\"\"
    left, right = (int(piece) for piece in text.split(":"))
    if right == 0:
        raise ValueError(f"a ratio cannot divide by zero: {text!r}")
    return left, right""",
    visible_test=_test_module(
        "ratio_syntax",
        "Published contract for reading a ratio.",
        """
def test_a_ratio_already_in_lowest_terms() -> None:
    assert parse_ratio("3:4") == (3, 4)


def test_a_negative_first_term() -> None:
    assert parse_ratio("-3:4") == (-3, 4)
""",
        imports="from ratio_syntax import parse_ratio\n",
    ),
    hidden_test=_test_module(
        "ratio_syntax",
        "The part of the contract the published tests do not state.",
        """
import pytest

from ratio_syntax import parse_ratio


def test_a_ratio_already_in_lowest_terms() -> None:
    assert parse_ratio("3:4") == (3, 4)


def test_the_returned_ratio_is_reduced() -> None:
    assert parse_ratio("6:8") == (3, 4)


def test_a_zero_second_term_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_ratio("3:0")
""",
    ),
)

# ------------------------------------------------------------------- state and idempotency

_C9 = D2TaskSpec(
    template_id="d3_state.claim_slot",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d3-state-claim-slot",
    module="slot_claims",
    module_doc="Claiming a named slot on behalf of an owner.",
    issue=(
        "claim_slot() is documented to hand a slot to an owner without ever taking it from "
        "someone else. Callers report that a claim on a slot another owner already holds "
        "succeeds anyway, and that an empty owner name is accepted."
    ),
    expected=(
        "claim_slot(owners, slot, owner) records owner and returns True for a free slot or a "
        "re-claim by the same owner, returns False and leaves the holder untouched for a slot "
        "someone else holds, and raises ValueError for an empty owner name."
    ),
    baseline_reason="it assigns unconditionally and never looks at the owner name",
    edge_cases=(
        "a slot another owner holds is not taken over",
        "an empty owner name raises ValueError",
    ),
    baseline="""def claim_slot(owners, slot, owner):
    \"\"\"Record `owner` against `slot` and report whether they now hold it.\"\"\"
    owners.update({slot: owner})
    return True""",
    variant_one="""def claim_slot(owners, slot, owner):
    \"\"\"Record `owner` against `slot` and report whether they now hold it.\"\"\"
    if not owner:
        raise ValueError("an owner name is required")
    holder = owners.get(slot)
    if holder is not None and holder != owner:
        return False
    owners[slot] = owner
    return True""",
    variant_two="""def claim_slot(owners, slot, owner):
    \"\"\"Record `owner` against `slot` and report whether they now hold it.\"\"\"
    if not owner:
        raise ValueError("an owner name is required")
    return owners.setdefault(slot, owner) == owner""",
    variant_three="""def claim_slot(owners, slot, owner):
    \"\"\"Record `owner` against `slot` and report whether they now hold it.\"\"\"
    holder = owners.get(slot)
    if holder is not None and holder != owner:
        return False
    owners[slot] = owner
    return True""",
    variant_four="""def claim_slot(owners, slot, owner):
    \"\"\"Record `owner` against `slot` and report whether they now hold it.\"\"\"
    if not owner:
        raise ValueError("an owner name is required")
    owners[slot] = owner
    return True""",
    visible_test=_test_module(
        "slot_claims",
        "Published contract for claiming a slot.",
        """
def test_a_free_slot_is_claimed() -> None:
    owners = {}
    assert claim_slot(owners, "a", "ada") is True
    assert owners["a"] == "ada"


def test_the_same_owner_may_reclaim() -> None:
    owners = {"a": "ada"}
    assert claim_slot(owners, "a", "ada") is True
""",
        imports="from slot_claims import claim_slot\n",
    ),
    hidden_test=_test_module(
        "slot_claims",
        "The part of the contract the published tests do not state.",
        """
import pytest

from slot_claims import claim_slot


def test_a_free_slot_is_claimed() -> None:
    owners = {}
    assert claim_slot(owners, "a", "ada") is True


def test_a_slot_another_owner_holds_is_not_taken_over() -> None:
    owners = {"a": "ada"}
    assert claim_slot(owners, "a", "bob") is False
    assert owners["a"] == "ada"


def test_an_empty_owner_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        claim_slot({}, "a", "")
""",
    ),
)

_C10 = D2TaskSpec(
    template_id="d3_state.expire_before",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d3-state-expire-before",
    module="entry_expiry",
    module_doc="Dropping entries that are older than a cutoff.",
    issue=(
        "expire_before() is documented to report the entries at or after a cutoff. Callers "
        "report that an entry landing exactly on the cutoff disappears, and that the mapping "
        "they passed in comes back with rows missing."
    ),
    expected=(
        "expire_before(entries, cutoff) returns a new mapping holding every entry whose stamp "
        "is at or after cutoff, and leaves the caller's mapping exactly as it was."
    ),
    baseline_reason="it deletes in place and drops the entry that lands on the cutoff",
    edge_cases=(
        "an entry exactly on the cutoff is kept",
        "the caller's mapping is not modified",
    ),
    baseline="""def expire_before(entries, cutoff):
    \"\"\"Return the entries whose stamp is at or after `cutoff`.\"\"\"
    for key in list(entries):
        if entries[key] <= cutoff:
            del entries[key]
    return entries""",
    variant_one="""def expire_before(entries, cutoff):
    \"\"\"Return the entries whose stamp is at or after `cutoff`.\"\"\"
    return {key: stamp for key, stamp in entries.items() if stamp >= cutoff}""",
    variant_two="""def expire_before(entries, cutoff):
    \"\"\"Return the entries whose stamp is at or after `cutoff`.\"\"\"
    kept = dict(entries)
    for key in list(kept):
        if kept[key] < cutoff:
            del kept[key]
    return kept""",
    variant_three="""def expire_before(entries, cutoff):
    \"\"\"Return the entries whose stamp is at or after `cutoff`.\"\"\"
    for key in list(entries):
        if entries[key] < cutoff:
            del entries[key]
    return entries""",
    variant_four="""def expire_before(entries, cutoff):
    \"\"\"Return the entries whose stamp is at or after `cutoff`.\"\"\"
    return {key: stamp for key, stamp in entries.items() if stamp > cutoff}""",
    visible_test=_test_module(
        "entry_expiry",
        "Published contract for expiring entries.",
        """
def test_older_entries_are_dropped() -> None:
    assert expire_before({"a": 1, "b": 5}, 3) == {"b": 5}


def test_every_entry_may_survive() -> None:
    assert expire_before({"a": 8, "b": 9}, 3) == {"a": 8, "b": 9}
""",
        imports="from entry_expiry import expire_before\n",
    ),
    hidden_test=_test_module(
        "entry_expiry",
        "The part of the contract the published tests do not state.",
        """
def test_older_entries_are_dropped() -> None:
    assert expire_before({"a": 1, "b": 5}, 3) == {"b": 5}


def test_an_entry_exactly_on_the_cutoff_is_kept() -> None:
    assert expire_before({"a": 3, "b": 5}, 3) == {"a": 3, "b": 5}


def test_the_callers_mapping_is_not_modified() -> None:
    original = {"a": 1, "b": 5}
    expire_before(original, 3)
    assert original == {"a": 1, "b": 5}
""",
        imports="from entry_expiry import expire_before\n",
    ),
)

_C11 = D2TaskSpec(
    template_id="d3_state.keep_recent",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d3-state-keep-recent",
    module="recent_log",
    module_doc="Trimming a log down to its most recent entries.",
    issue=(
        "keep_recent() is documented to return the most recent entries of a log. Callers report "
        "that asking for none of them returns the whole log, and that a negative limit is "
        "accepted instead of being refused."
    ),
    expected=(
        "keep_recent(entries, limit) returns the last limit entries as a new list, returns an "
        "empty list for a limit of zero, and raises ValueError for a negative limit."
    ),
    baseline_reason="a negative slice offset of zero selects everything and no limit is validated",
    edge_cases=(
        "a limit of zero returns an empty list",
        "a negative limit raises ValueError",
    ),
    baseline="""def keep_recent(entries, limit):
    \"\"\"Return the last `limit` entries of `entries`.\"\"\"
    return list(entries)[-limit:]""",
    variant_one="""def keep_recent(entries, limit):
    \"\"\"Return the last `limit` entries of `entries`.\"\"\"
    if limit < 0:
        raise ValueError("a limit cannot be negative")
    if limit == 0:
        return []
    return list(entries)[-limit:]""",
    variant_two="""def keep_recent(entries, limit):
    \"\"\"Return the last `limit` entries of `entries`.\"\"\"
    from collections import deque

    if limit < 0:
        raise ValueError("a limit cannot be negative")
    return list(deque(entries, maxlen=limit))""",
    variant_three="""def keep_recent(entries, limit):
    \"\"\"Return the last `limit` entries of `entries`.\"\"\"
    if limit == 0:
        return []
    return list(entries)[-limit:]""",
    variant_four="""def keep_recent(entries, limit):
    \"\"\"Return the last `limit` entries of `entries`.\"\"\"
    if limit < 0:
        raise ValueError("a limit cannot be negative")
    return list(entries)[-limit:]""",
    visible_test=_test_module(
        "recent_log",
        "Published contract for trimming a log.",
        """
def test_the_most_recent_two_entries() -> None:
    assert keep_recent([1, 2, 3, 4], 2) == [3, 4]


def test_a_limit_above_the_length_returns_everything() -> None:
    assert keep_recent([1, 2], 5) == [1, 2]
""",
        imports="from recent_log import keep_recent\n",
    ),
    hidden_test=_test_module(
        "recent_log",
        "The part of the contract the published tests do not state.",
        """
import pytest

from recent_log import keep_recent


def test_the_most_recent_two_entries() -> None:
    assert keep_recent([1, 2, 3, 4], 2) == [3, 4]


def test_a_limit_of_zero_returns_an_empty_list() -> None:
    assert keep_recent([1, 2, 3], 0) == []


def test_a_negative_limit_is_rejected() -> None:
    with pytest.raises(ValueError):
        keep_recent([1, 2, 3], -1)
""",
    ),
)

# ------------------------------------------------------------------------- numeric logic

_C12 = D2TaskSpec(
    template_id="d3_numeric.share_amount",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d3-numeric-share-amount",
    module="amount_shares",
    module_doc="Splitting a whole amount into equal shares.",
    issue=(
        "share_amount() is documented to split an amount into shares that add back up to it. "
        "Callers report that the remainder disappears, and that asking for no shares at all "
        "crashes instead of being refused."
    ),
    expected=(
        "share_amount(total, parts) returns parts integers summing to total, giving the "
        "remainder to the earliest shares, and raises ValueError when parts is not positive."
    ),
    baseline_reason="integer division drops the remainder and a zero part count divides by zero",
    edge_cases=(
        "the remainder goes to the earliest shares",
        "a part count of zero raises ValueError",
    ),
    baseline="""def share_amount(total, parts):
    \"\"\"Split `total` into `parts` shares that add back up to it.\"\"\"
    even = total // parts
    return [even for _ in range(parts)]""",
    variant_one="""def share_amount(total, parts):
    \"\"\"Split `total` into `parts` shares that add back up to it.\"\"\"
    if parts <= 0:
        raise ValueError("a share count must be positive")
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]""",
    variant_two="""def share_amount(total, parts):
    \"\"\"Split `total` into `parts` shares that add back up to it.\"\"\"
    if parts <= 0:
        raise ValueError("a share count must be positive")
    shares = []
    left = total
    for index in range(parts, 0, -1):
        share = -(-left // index)
        left -= share
        shares.append(share)
    return shares""",
    variant_three="""def share_amount(total, parts):
    \"\"\"Split `total` into `parts` shares that add back up to it.\"\"\"
    base, remainder = divmod(total, parts)
    shares = []
    for index in range(parts):
        extra = 1 if index < remainder else 0
        shares.append(base + extra)
    return shares""",
    variant_four="""def share_amount(total, parts):
    \"\"\"Split `total` into `parts` shares that add back up to it.\"\"\"
    if parts <= 0:
        raise ValueError("a share count must be positive")
    return [total // parts] * parts""",
    visible_test=_test_module(
        "amount_shares",
        "Published contract for splitting an amount.",
        """
def test_an_amount_that_divides_evenly() -> None:
    assert share_amount(6, 3) == [2, 2, 2]


def test_a_zero_amount() -> None:
    assert share_amount(0, 2) == [0, 0]
""",
        imports="from amount_shares import share_amount\n",
    ),
    hidden_test=_test_module(
        "amount_shares",
        "The part of the contract the published tests do not state.",
        """
import pytest

from amount_shares import share_amount


def test_an_amount_that_divides_evenly() -> None:
    assert share_amount(6, 3) == [2, 2, 2]


def test_the_remainder_goes_to_the_earliest_shares() -> None:
    assert share_amount(7, 3) == [3, 2, 2]


def test_a_part_count_of_zero_is_rejected() -> None:
    with pytest.raises(ValueError):
        share_amount(6, 0)
""",
    ),
)

_C13 = D2TaskSpec(
    template_id="d3_numeric.safe_share",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d3-numeric-safe-share",
    module="share_ratio",
    module_doc="Reporting a part of a whole as a bounded fraction.",
    issue=(
        "safe_share() is documented to report a part of a whole as a fraction between zero and "
        "one. Callers report a crash when the whole is zero, and fractions above one when the "
        "part overshoots."
    ),
    expected=(
        "safe_share(part, whole) returns part divided by whole clamped into the range zero to "
        "one, and returns 0.0 when whole is zero."
    ),
    baseline_reason="it divides without guarding the zero whole and never clamps the result",
    edge_cases=(
        "a zero whole gives 0.0",
        "a part above the whole clamps to 1.0",
    ),
    baseline="""def safe_share(part, whole):
    \"\"\"Return `part` of `whole` as a fraction between zero and one.\"\"\"
    return part / whole""",
    variant_one="""def safe_share(part, whole):
    \"\"\"Return `part` of `whole` as a fraction between zero and one.\"\"\"
    if whole == 0:
        return 0.0
    return min(1.0, max(0.0, part / whole))""",
    variant_two="""def safe_share(part, whole):
    \"\"\"Return `part` of `whole` as a fraction between zero and one.\"\"\"
    try:
        share = part / whole
    except ZeroDivisionError:
        return 0.0
    return sorted((0.0, share, 1.0))[1]""",
    variant_three="""def safe_share(part, whole):
    \"\"\"Return `part` of `whole` as a fraction between zero and one.\"\"\"
    if whole == 0:
        return 0.0
    return part / whole""",
    variant_four="""def safe_share(part, whole):
    \"\"\"Return `part` of `whole` as a fraction between zero and one.\"\"\"
    return min(1.0, max(0.0, part / whole))""",
    visible_test=_test_module(
        "share_ratio",
        "Published contract for a bounded share.",
        """
def test_a_quarter() -> None:
    assert safe_share(1, 4) == 0.25


def test_nothing_of_something() -> None:
    assert safe_share(0, 4) == 0.0
""",
        imports="from share_ratio import safe_share\n",
    ),
    hidden_test=_test_module(
        "share_ratio",
        "The part of the contract the published tests do not state.",
        """
def test_a_quarter() -> None:
    assert safe_share(1, 4) == 0.25


def test_a_zero_whole_gives_zero() -> None:
    assert safe_share(3, 0) == 0.0


def test_a_part_above_the_whole_clamps_to_one() -> None:
    assert safe_share(9, 4) == 1.0
""",
        imports="from share_ratio import safe_share\n",
    ),
)

_C14 = D2TaskSpec(
    template_id="d3_numeric.round_to_step",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d3-numeric-round-to-step",
    module="step_rounding",
    module_doc="Rounding a value onto a fixed step.",
    issue=(
        "round_to_step() is documented to round a value onto the nearest multiple of a step, "
        "with a halfway value going up. Callers report that a halfway value goes down, and that "
        "a step of zero crashes instead of being refused."
    ),
    expected=(
        "round_to_step(value, step) returns the nearest multiple of step, rounds a halfway "
        "value up, and raises ValueError when step is not positive."
    ),
    baseline_reason="round() breaks halfway ties to even and a zero step divides by zero",
    edge_cases=(
        "a halfway value rounds up",
        "a step of zero raises ValueError",
    ),
    baseline="""def round_to_step(value, step):
    \"\"\"Return `value` rounded onto the nearest multiple of `step`.\"\"\"
    steps = value / step
    return step * round(steps)""",
    variant_one="""def round_to_step(value, step):
    \"\"\"Return `value` rounded onto the nearest multiple of `step`.\"\"\"
    import math

    if step <= 0:
        raise ValueError("a step must be positive")
    return int(math.floor(value / step + 0.5)) * step""",
    variant_two="""def round_to_step(value, step):
    \"\"\"Return `value` rounded onto the nearest multiple of `step`.\"\"\"
    from decimal import ROUND_HALF_UP, Decimal

    if step <= 0:
        raise ValueError("a step must be positive")
    steps = Decimal(value) / Decimal(step)
    return int(steps.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) * step""",
    variant_three="""def round_to_step(value, step):
    \"\"\"Return `value` rounded onto the nearest multiple of `step`.\"\"\"
    import math

    return int(math.floor(value / step + 0.5)) * step""",
    variant_four="""def round_to_step(value, step):
    \"\"\"Return `value` rounded onto the nearest multiple of `step`.\"\"\"
    if step <= 0:
        raise ValueError("a step must be positive")
    return round(value / step) * step""",
    visible_test=_test_module(
        "step_rounding",
        "Published contract for rounding onto a step.",
        """
def test_a_value_below_the_midpoint_rounds_down() -> None:
    assert round_to_step(7, 5) == 5


def test_a_value_above_the_midpoint_rounds_up() -> None:
    assert round_to_step(8, 5) == 10
""",
        imports="from step_rounding import round_to_step\n",
    ),
    hidden_test=_test_module(
        "step_rounding",
        "The part of the contract the published tests do not state.",
        """
import pytest

from step_rounding import round_to_step


def test_a_value_below_the_midpoint_rounds_down() -> None:
    assert round_to_step(7, 5) == 5


def test_a_halfway_value_rounds_up() -> None:
    assert round_to_step(5, 10) == 10


def test_a_step_of_zero_is_rejected() -> None:
    with pytest.raises(ValueError):
        round_to_step(7, 0)
""",
    ),
)

# ------------------------------------------------------------------------ error handling

_C15 = D2TaskSpec(
    template_id="d3_errors.first_passing",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d3-errors-first-passing",
    module="first_passing",
    module_doc="Finding the first item a check accepts.",
    issue=(
        "first_passing() is documented to return the first item a check accepts. Callers report "
        "that an accepted item which happens to be falsy is skipped, and that a check raising "
        "on one item aborts the whole search."
    ),
    expected=(
        "first_passing(items, check, default) returns the first item check accepts including a "
        "falsy one, treats an item whose check raises as not accepted, and returns default when "
        "nothing is accepted."
    ),
    baseline_reason="it tests the item for truth first and lets a raising check escape",
    edge_cases=(
        "an accepted falsy item is returned",
        "an item whose check raises is skipped",
    ),
    baseline="""def first_passing(items, check, default=None):
    \"\"\"Return the first item `check` accepts, or `default`.\"\"\"
    for item in items:
        if item and check(item):
            return item
    return default""",
    variant_one="""def first_passing(items, check, default=None):
    \"\"\"Return the first item `check` accepts, or `default`.\"\"\"
    for item in items:
        try:
            accepted = check(item)
        except Exception:
            continue
        if accepted:
            return item
    return default""",
    variant_two="""def first_passing(items, check, default=None):
    \"\"\"Return the first item `check` accepts, or `default`.\"\"\"

    def accepts(candidate):
        try:
            return bool(check(candidate))
        except Exception:
            return False

    return next((item for item in items if accepts(item)), default)""",
    variant_three="""def first_passing(items, check, default=None):
    \"\"\"Return the first item `check` accepts, or `default`.\"\"\"
    for item in items:
        if check(item):
            return item
    return default""",
    variant_four="""def first_passing(items, check, default=None):
    \"\"\"Return the first item `check` accepts, or `default`.\"\"\"
    for item in items:
        try:
            accepted = item and check(item)
        except Exception:
            continue
        if accepted:
            return item
    return default""",
    visible_test=_test_module(
        "first_passing",
        "Published contract for the first accepted item.",
        """
def test_the_first_accepted_item() -> None:
    assert first_passing([1, 3, 4], lambda value: value > 2) == 3


def test_nothing_accepted_gives_the_default() -> None:
    assert first_passing([1, 2], lambda value: value > 9, "none") == "none"
""",
        imports="from first_passing import first_passing\n",
    ),
    hidden_test=_test_module(
        "first_passing",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_accepted_item() -> None:
    assert first_passing([1, 3, 4], lambda value: value > 2) == 3


def test_an_accepted_falsy_item_is_returned() -> None:
    assert first_passing([0, 5], lambda value: value < 1) == 0


def test_an_item_whose_check_raises_is_skipped() -> None:
    assert first_passing(["a", 5], lambda value: value > 1) == 5
""",
        imports="from first_passing import first_passing\n",
    ),
)

_C16 = D2TaskSpec(
    template_id="d3_errors.merge_optional",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d3-errors-merge-optional",
    module="optional_merge",
    module_doc="Merging two mappings either of which may be absent.",
    issue=(
        "merge_optional() is documented to merge two mappings, either of which may be absent. "
        "Callers report a crash when one side is None, and that the mapping they passed on the "
        "left comes back changed."
    ),
    expected=(
        "merge_optional(left, right) returns a new mapping with right winning on conflicts, "
        "treats None on either side as empty, and leaves both arguments unchanged."
    ),
    baseline_reason="it updates the left mapping in place and calls a method None does not have",
    edge_cases=(
        "None on either side is treated as empty",
        "neither argument is modified",
    ),
    baseline="""def merge_optional(left, right):
    \"\"\"Return `left` merged with `right`, right winning on conflicts.\"\"\"
    for key in right:
        left[key] = right[key]
    return left""",
    variant_one="""def merge_optional(left, right):
    \"\"\"Return `left` merged with `right`, right winning on conflicts.\"\"\"
    return {**(left or {}), **(right or {})}""",
    variant_two="""def merge_optional(left, right):
    \"\"\"Return `left` merged with `right`, right winning on conflicts.\"\"\"
    merged = dict(left) if left else {}
    if right:
        merged.update(right)
    return merged""",
    variant_three="""def merge_optional(left, right):
    \"\"\"Return `left` merged with `right`, right winning on conflicts.\"\"\"
    merged = {} if left is None else left
    for key, value in (right or {}).items():
        merged[key] = value
    return merged""",
    variant_four="""def merge_optional(left, right):
    \"\"\"Return `left` merged with `right`, right winning on conflicts.\"\"\"
    merged = dict(left)
    for key in right:
        merged[key] = right[key]
    return merged""",
    visible_test=_test_module(
        "optional_merge",
        "Published contract for merging two mappings.",
        """
def test_two_mappings_merge() -> None:
    assert merge_optional({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_the_right_side_wins() -> None:
    assert merge_optional({"a": 1}, {"a": 2}) == {"a": 2}
""",
        imports="from optional_merge import merge_optional\n",
    ),
    hidden_test=_test_module(
        "optional_merge",
        "The part of the contract the published tests do not state.",
        """
def test_two_mappings_merge() -> None:
    assert merge_optional({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_none_on_either_side_is_empty() -> None:
    assert merge_optional(None, {"b": 2}) == {"b": 2}
    assert merge_optional({"a": 1}, None) == {"a": 1}


def test_neither_argument_is_modified() -> None:
    original = {"a": 1}
    merge_optional(original, {"b": 2})
    assert original == {"a": 1}
""",
        imports="from optional_merge import merge_optional\n",
    ),
)

_C17 = D2TaskSpec(
    template_id="d3_errors.attempt_times",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d3-errors-attempt-times",
    module="bounded_attempts",
    module_doc="Calling an action a bounded number of times.",
    issue=(
        "attempt_times() is documented to call an action until it succeeds, within a bound. "
        "Callers report that an action failing every time returns None instead of surfacing the "
        "failure, and that a bound of zero is accepted."
    ),
    expected=(
        "attempt_times(action, attempts) returns the first successful result, re-raises the "
        "last failure once every attempt is spent, and raises ValueError when attempts is not "
        "positive."
    ),
    baseline_reason="it swallows the last failure and never checks the bound",
    edge_cases=(
        "the last failure is re-raised once every attempt is spent",
        "a bound of zero raises ValueError",
    ),
    baseline="""def attempt_times(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    failure = None
    for _ in range(attempts):
        try:
            return action()
        except Exception as error:
            failure = error
    return failure and None""",
    variant_one="""def attempt_times(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("an attempt count must be positive")
    failure = None
    spent = 0
    while spent < attempts:
        spent += 1
        try:
            return action()
        except Exception as error:
            failure = error
    raise failure""",
    variant_two="""def attempt_times(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("an attempt count must be positive")
    for _ in range(attempts - 1):
        try:
            return action()
        except Exception:
            continue
    return action()""",
    variant_three="""def attempt_times(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    failure = None
    for attempt in range(attempts):
        try:
            return action()
        except Exception as error:
            failure = error
            continue
    raise failure""",
    variant_four="""def attempt_times(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("an attempt count must be positive")
    failure = None
    for _ in range(attempts):
        try:
            return action()
        except Exception as error:
            failure = error
    return failure and None""",
    visible_test=_test_module(
        "bounded_attempts",
        "Published contract for bounded attempts.",
        """
def test_a_first_time_success() -> None:
    assert attempt_times(lambda: "ok", 3) == "ok"


def test_a_success_after_one_failure() -> None:
    calls = []

    def action():
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("not yet")
        return "ok"

    assert attempt_times(action, 3) == "ok"
""",
        imports="from bounded_attempts import attempt_times\n",
    ),
    hidden_test=_test_module(
        "bounded_attempts",
        "The part of the contract the published tests do not state.",
        """
import pytest

from bounded_attempts import attempt_times


def test_a_first_time_success() -> None:
    assert attempt_times(lambda: "ok", 3) == "ok"


def test_the_last_failure_is_re_raised() -> None:
    def action():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError):
        attempt_times(action, 2)


def test_a_bound_of_zero_is_rejected() -> None:
    with pytest.raises(ValueError):
        attempt_times(lambda: "ok", 0)
""",
    ),
)

# --------------------------------------------------------------------- data transformation

_C18 = D2TaskSpec(
    template_id="d3_transform.tally_by",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d3-transform-tally-by",
    module="tally_groups",
    module_doc="Counting items by a derived key.",
    issue=(
        "tally_by() is documented to count items under the key a caller derives, keeping the "
        "keys in the order they were first seen. Callers report that the keys come back sorted, "
        "and that items whose key is None are counted."
    ),
    expected=(
        "tally_by(items, derive) returns a mapping from derived key to count in first-seen order, "
        "leaves out items whose key is None."
    ),
    baseline_reason="it sorts the result and counts the None key like any other",
    edge_cases=(
        "keys keep their first-seen order",
        "an item whose key is None is left out",
    ),
    baseline="""def tally_by(items, derive):
    \"\"\"Count `items` under `derive`, keys in first-seen order.\"\"\"
    counts = {}
    for item in items:
        derived = derive(item)
        counts[derived] = counts.get(derived, 0) + 1
    return dict(sorted(counts.items(), key=repr))""",
    variant_one="""def tally_by(items, derive):
    \"\"\"Count `items` under `derive`, keys in first-seen order.\"\"\"
    counts = {}
    for item in items:
        derived = derive(item)
        if derived is None:
            continue
        counts[derived] = counts.get(derived, 0) + 1
    return counts""",
    variant_two="""def tally_by(items, derive):
    \"\"\"Count `items` under `derive`, keys in first-seen order.\"\"\"
    counts = {}
    for derived in (derive(item) for item in items):
        if derived is not None:
            counts.setdefault(derived, 0)
            counts[derived] += 1
    return counts""",
    variant_three="""def tally_by(items, derive):
    \"\"\"Count `items` under `derive`, keys in first-seen order.\"\"\"
    counts = {}
    for item in items:
        derived = derive(item)
        counts[derived] = counts.get(derived, 0) + 1
    return counts""",
    variant_four="""def tally_by(items, derive):
    \"\"\"Count `items` under `derive`, keys in first-seen order.\"\"\"
    counts = {}
    for item in items:
        derived = derive(item)
        if derived is None:
            continue
        counts[derived] = counts.get(derived, 0) + 1
    return dict(sorted(counts.items(), key=repr))""",
    visible_test=_test_module(
        "tally_groups",
        "Published contract for counting by a key.",
        """
def test_counts_by_length() -> None:
    assert tally_by(["aa", "ab", "b"], len) == {2: 2, 1: 1}


def test_no_items_give_no_counts() -> None:
    assert tally_by([], len) == {}
""",
        imports="from tally_groups import tally_by\n",
    ),
    hidden_test=_test_module(
        "tally_groups",
        "The part of the contract the published tests do not state.",
        """
def test_counts_by_length() -> None:
    assert tally_by(["aa", "ab", "b"], len) == {2: 2, 1: 1}


def test_keys_keep_their_first_seen_order() -> None:
    assert list(tally_by(["aa", "ab", "b"], len)) == [2, 1]


def test_an_item_whose_key_is_none_is_left_out() -> None:
    assert tally_by([1, 2], lambda value: None if value == 1 else "kept") == {"kept": 1}
""",
        imports="from tally_groups import tally_by\n",
    ),
)

_C19 = D2TaskSpec(
    template_id="d3_transform.pick_fields",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d3-transform-pick-fields",
    module="field_projection",
    module_doc="Projecting a record down to the fields a caller names.",
    issue=(
        "pick_fields() is documented to project a record onto the fields a caller names. "
        "Callers report a crash when they name a field the record does not carry, and that a "
        "field holding None comes back instead of being left out."
    ),
    expected=(
        "pick_fields(record, fields) returns a mapping of the named fields, leaving out any "
        "field the record does not carry and any field whose value is None."
    ),
    baseline_reason="it indexes every named field and keeps a None value like any other",
    edge_cases=(
        "a field the record does not carry is left out",
        "a field whose value is None is left out",
    ),
    baseline="""def pick_fields(record, fields):
    \"\"\"Return `record` projected onto `fields`.\"\"\"
    picked = {}
    for field in fields:
        picked[field] = record[field]
    return picked""",
    variant_one="""def pick_fields(record, fields):
    \"\"\"Return `record` projected onto `fields`.\"\"\"
    return {
        field: record[field]
        for field in fields
        if field in record and record[field] is not None
    }""",
    variant_two="""def pick_fields(record, fields):
    \"\"\"Return `record` projected onto `fields`.\"\"\"
    picked = {}
    for field in fields:
        value = record.get(field)
        if value is not None:
            picked[field] = value
    return picked""",
    variant_three="""def pick_fields(record, fields):
    \"\"\"Return `record` projected onto `fields`.\"\"\"
    return dict((field, record[field]) for field in fields if field in record)""",
    variant_four="""def pick_fields(record, fields):
    \"\"\"Return `record` projected onto `fields`.\"\"\"
    return {field: record[field] for field in fields if record[field] is not None}""",
    visible_test=_test_module(
        "field_projection",
        "Published contract for projecting a record.",
        """
def test_named_fields_are_kept() -> None:
    assert pick_fields({"a": 1, "b": 2, "c": 3}, ["a", "c"]) == {"a": 1, "c": 3}


def test_no_fields_give_an_empty_mapping() -> None:
    assert pick_fields({"a": 1}, []) == {}
""",
        imports="from field_projection import pick_fields\n",
    ),
    hidden_test=_test_module(
        "field_projection",
        "The part of the contract the published tests do not state.",
        """
def test_named_fields_are_kept() -> None:
    assert pick_fields({"a": 1, "b": 2, "c": 3}, ["a", "c"]) == {"a": 1, "c": 3}


def test_a_field_the_record_does_not_carry_is_left_out() -> None:
    assert pick_fields({"a": 1}, ["a", "z"]) == {"a": 1}


def test_a_field_whose_value_is_none_is_left_out() -> None:
    assert pick_fields({"a": 1, "b": None}, ["a", "b"]) == {"a": 1}
""",
        imports="from field_projection import pick_fields\n",
    ),
)

_C20 = D2TaskSpec(
    template_id="d3_transform.split_text",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d3-transform-split-text",
    module="text_chunks",
    module_doc="Cutting text into fixed-width chunks.",
    issue=(
        "split_text() is documented to cut text into chunks of a fixed width. Callers report "
        "that the last partial chunk is dropped, and that a negative width returns nothing "
        "instead of being refused."
    ),
    expected=(
        "split_text(text, size) returns the chunks of text in order including a shorter final "
        "one, and raises ValueError when size is not positive."
    ),
    baseline_reason="the range stops a whole chunk early and no size is validated",
    edge_cases=(
        "a shorter final chunk is kept",
        "a size that is not positive raises ValueError",
    ),
    baseline="""def split_text(text, size):
    \"\"\"Return `text` cut into chunks of `size` characters.\"\"\"
    return [text[start : start + size] for start in range(0, len(text) - size + 1, size)]""",
    variant_one="""def split_text(text, size):
    \"\"\"Return `text` cut into chunks of `size` characters.\"\"\"
    if size <= 0:
        raise ValueError("a chunk size must be positive")
    return [text[start : start + size] for start in range(0, len(text), size)]""",
    variant_two="""def split_text(text, size):
    \"\"\"Return `text` cut into chunks of `size` characters.\"\"\"
    if size <= 0:
        raise ValueError("a chunk size must be positive")
    chunks = []
    remaining = text
    while remaining:
        chunks.append(remaining[:size])
        remaining = remaining[size:]
    return chunks""",
    variant_three="""def split_text(text, size):
    \"\"\"Return `text` cut into chunks of `size` characters.\"\"\"
    return [text[start : start + size] for start in range(0, len(text), size)]""",
    variant_four="""def split_text(text, size):
    \"\"\"Return `text` cut into chunks of `size` characters.\"\"\"
    if size <= 0:
        raise ValueError("a chunk size must be positive")
    return [text[start : start + size] for start in range(0, len(text) - size + 1, size)]""",
    visible_test=_test_module(
        "text_chunks",
        "Published contract for cutting text into chunks.",
        """
def test_text_that_divides_evenly() -> None:
    assert split_text("abcdef", 2) == ["ab", "cd", "ef"]


def test_empty_text_gives_no_chunks() -> None:
    assert split_text("", 2) == []
""",
        imports="from text_chunks import split_text\n",
    ),
    hidden_test=_test_module(
        "text_chunks",
        "The part of the contract the published tests do not state.",
        """
import pytest

from text_chunks import split_text


def test_text_that_divides_evenly() -> None:
    assert split_text("abcdef", 2) == ["ab", "cd", "ef"]


def test_a_shorter_final_chunk_is_kept() -> None:
    assert split_text("abcde", 2) == ["ab", "cd", "e"]


def test_a_size_that_is_not_positive_is_rejected() -> None:
    with pytest.raises(ValueError):
        split_text("abc", -1)
""",
    ),
)

#: The twenty fresh calibration groups, in authoring order. `assign_d3_calibration` deals them
#: family-interleaved, so this order is provenance rather than partition membership.
D3_CALIBRATION_SPECS: tuple[D2TaskSpec, ...] = (
    _C1,
    _C2,
    _C3,
    _C4,
    _C5,
    _C6,
    _C7,
    _C8,
    _C9,
    _C10,
    _C11,
    _C12,
    _C13,
    _C14,
    _C15,
    _C16,
    _C17,
    _C18,
    _C19,
    _C20,
)

# ----------------------------------------------------------- S21D3-033 vertical-slice fixture

#: Outside every D3 campaign role. §6.1 requires the vertical slice to spend no calibration
#: case, final member, canary member or retrieval judgement, and the only way to guarantee that
#: is for the group it runs on to belong to no partition at all.
D3_FIXTURE_SPEC = D2TaskSpec(
    template_id="d3_fixture.trim_suffix",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d3-fixture-trim-suffix",
    module="suffix_trim",
    module_doc="Removing a declared suffix from a label.",
    issue=(
        "trim_suffix() is documented to remove a suffix when present and to return the label "
        "untouched otherwise. Callers report that it cuts characters off labels that do not "
        "carry the suffix, and that an empty suffix empties the label."
    ),
    expected=(
        "trim_suffix(label, suffix) removes suffix only when label ends with it, returns label "
        "unchanged otherwise, and treats an empty suffix as removing nothing."
    ),
    baseline_reason="it slices by suffix length without checking that the suffix is present",
    edge_cases=(
        "a label without the suffix is unchanged",
        "an empty suffix removes nothing",
    ),
    baseline="""def trim_suffix(label, suffix):
    \"\"\"Return `label` without `suffix`, or unchanged when it is not present.\"\"\"
    return label[: -len(suffix)]""",
    variant_one="""def trim_suffix(label, suffix):
    \"\"\"Return `label` without `suffix`, or unchanged when it is not present.\"\"\"
    if not suffix or not label.endswith(suffix):
        return label
    return label[: -len(suffix)]""",
    variant_two="""def trim_suffix(label, suffix):
    \"\"\"Return `label` without `suffix`, or unchanged when it is not present.\"\"\"
    if not suffix:
        return label
    return label.removesuffix(suffix)""",
    variant_three="""def trim_suffix(label, suffix):
    \"\"\"Return `label` without `suffix`, or unchanged when it is not present.\"\"\"
    if not label.endswith(suffix):
        return label
    return label[: -len(suffix)]""",
    variant_four="""def trim_suffix(label, suffix):
    \"\"\"Return `label` without `suffix`, or unchanged when it is not present.\"\"\"
    if not suffix:
        return label
    return label[: -len(suffix)]""",
    visible_test=_test_module(
        "suffix_trim",
        "Published contract for removing a suffix.",
        """
def test_a_present_suffix_is_removed() -> None:
    assert trim_suffix("report.txt", ".txt") == "report"


def test_a_short_label_with_the_suffix() -> None:
    assert trim_suffix("a.txt", ".txt") == "a"
""",
        imports="from suffix_trim import trim_suffix\n",
    ),
    hidden_test=_test_module(
        "suffix_trim",
        "The part of the contract the published tests do not state.",
        """
def test_a_present_suffix_is_removed() -> None:
    assert trim_suffix("report.txt", ".txt") == "report"


def test_a_label_without_the_suffix_is_unchanged() -> None:
    assert trim_suffix("report.md", ".txt") == "report.md"


def test_an_empty_suffix_removes_nothing() -> None:
    assert trim_suffix("report", "") == "report"
""",
        imports="from suffix_trim import trim_suffix\n",
    ),
)

#: Every D3-authored correction group: the twenty scored ones plus the fixture. The registry in
#: `reality_tasks` needs all of them; the catalogue needs only the twenty.
D3_TASK_SPECS: tuple[D2TaskSpec, ...] = (*D3_CALIBRATION_SPECS, D3_FIXTURE_SPEC)
