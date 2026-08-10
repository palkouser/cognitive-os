"""The Sprint 21D6 certification corpus: fresh four-candidate groups.

D6 needs a hundred *independent* certification decisions, and independence means distinct fitted
feature vectors, so the only route to a hundred is to author a hundred. This module is that
authoring. It is the certification half; D5's hundred calibration groups are the conformal half
that places the bar, and S21D6-022 proves the two share no group, no clone and no body.

The spec shape is `D2TaskSpec`, unchanged, for the reason D4 and D5 both gave: the catalogue,
the template registry and the campaign already agree about it.

Every group obeys the authoring contract D2 froze and D4 and D5 re-proved:

- the **baseline** passes the visible suite and fails the hidden one;
- **variant one** and **variant two** repair the contract by materially different routes and
  pass both suites;
- **variant three** fixes the first declared edge case only and **variant four** the second
  only, so both pass the visible suite and fail the hidden one.

Three failure modes account for every authoring defect the predecessors found, and all three are
invisible without executing:

1. *The two hidden tests probe one defect wearing two descriptions.* Then no partial fix repairs
   exactly one, and variants three and four both pass hidden. Every edge-case pair here is chosen
   so that a fix for one leaves the other untouched, and `scripts/corpus_d6.py` is what decides
   whether the choice held.
2. *The baseline is broken so badly it fails its own visible suite.* The defect has to be
   peripheral enough that the ordinary case still works.
3. *A near-clone collision at the level of the task, not the code.* Rewriting a variant cannot
   repair that — the group is withdrawn and a different one authored. With 526 released groups
   the obvious small-function repair space is heavily occupied, so every module name here was
   checked against the released corpus **before** its bodies were written.

Two constraints come from elsewhere in the sprint. The invariance sample renames identifiers, so
every body binds its names locally and none reaches a name through `getattr`, `globals()` or any
other reflective route, which `correction_source.py` refuses outright. And no group here may be
read before the conformal bar exists: revision 6 forbids it, and the campaign is what enforces
the order.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# ------------------------------------------------------------------ boundary and collections

_G001 = D2TaskSpec(
    template_id="d6_boundary.window_starts",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-window-starts",
    module="window_starts",
    module_doc="Choosing where each fixed-size window over a sequence begins.",
    issue=(
        "window_starts() is documented to return the starting offset of every window of a given "
        "size over a sequence, stepping by a given stride. Callers report that a sequence which "
        "does not divide evenly loses its final partial window, and that a stride larger than "
        "the window silently returns overlapping offsets."
    ),
    expected=(
        "window_starts(total, size, stride) returns the offsets 0, stride, 2*stride and so on "
        "while the offset is below total, so a trailing partial window keeps its offset. The "
        "stride is used as given, whatever its relation to the size."
    ),
    baseline_reason=(
        "it stops at the last offset that fits a whole window and steps by the size rather than "
        "the stride"
    ),
    edge_cases=(
        "a trailing partial window keeps its offset",
        "the stride is used even when it differs from the size",
    ),
    baseline='''def window_starts(total, size, stride):
    """Return the starting offset of every window over `total` items."""
    offsets = []
    offset = 0
    while offset + size <= total:
        offsets.append(offset)
        offset += size
    return offsets''',
    variant_one='''def window_starts(total, size, stride):
    """Return the starting offset of every window over `total` items."""
    offsets = []
    offset = 0
    while offset < total:
        offsets.append(offset)
        offset += stride
    return offsets''',
    variant_two='''def window_starts(total, size, stride):
    """Return the starting offset of every window over `total` items."""
    if total <= 0:
        return []
    count = (total + stride - 1) // stride
    return [position * stride for position in range(count)]''',
    variant_three='''def window_starts(total, size, stride):
    """Return the starting offset of every window over `total` items."""
    offsets = []
    offset = 0
    while offset < total:
        offsets.append(offset)
        offset += size
    return offsets''',
    variant_four='''def window_starts(total, size, stride):
    """Return the starting offset of every window over `total` items."""
    offsets = []
    offset = 0
    while offset + size <= total:
        offsets.append(offset)
        offset += stride
    return offsets''',
    visible_test=_test_module(
        "window_starts",
        "Published contract for placing fixed-size windows.",
        """
def test_an_even_division_places_one_window_per_step() -> None:
    assert window_starts(6, 2, 2) == [0, 2, 4]


def test_a_single_window_starts_at_the_beginning() -> None:
    assert window_starts(3, 3, 3) == [0]
""",
        imports="from window_starts import window_starts\n",
    ),
    hidden_test=_test_module(
        "window_starts",
        "The part of the contract the published tests do not state.",
        """
def test_an_even_division_places_one_window_per_step() -> None:
    assert window_starts(6, 2, 2) == [0, 2, 4]


def test_a_trailing_partial_window_keeps_its_offset() -> None:
    assert window_starts(7, 3, 3) == [0, 3, 6]


def test_a_stride_wider_than_the_window_is_used_as_given() -> None:
    assert window_starts(10, 2, 5) == [0, 5]
""",
        imports="from window_starts import window_starts\n",
    ),
)

_G002 = D2TaskSpec(
    template_id="d6_boundary.stable_top",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-stable-top",
    module="stable_top",
    module_doc="Taking the highest-scoring entries without disturbing equal ones.",
    issue=(
        "top_by() is documented to return the highest-scoring entries, leaving entries that "
        "score equally in the order they arrived. Callers report that equal scores come back "
        "reordered by their own value, and that asking for a negative count returns almost the "
        "whole list instead of nothing."
    ),
    expected=(
        "top_by(items, count, score) returns the `count` highest-scoring items in descending "
        "score, with items of equal score kept in their original order. A count of zero or "
        "less returns an empty list."
    ),
    baseline_reason=(
        "it sorts on the score paired with the item, so the item breaks ties, and it slices "
        "with the count directly, so a negative one slices from the end"
    ),
    edge_cases=(
        "items of equal score keep the order they arrived in",
        "a count of zero or less returns an empty list",
    ),
    baseline='''def top_by(items, count, score):
    """Return the `count` highest-scoring of `items`."""
    ordered = sorted(items, key=lambda item: (score(item), item), reverse=True)
    return ordered[:count]''',
    variant_one='''def top_by(items, count, score):
    """Return the `count` highest-scoring of `items`."""
    if count <= 0:
        return []
    ordered = sorted(items, key=score, reverse=True)
    return ordered[:count]''',
    variant_two='''def top_by(items, count, score):
    """Return the `count` highest-scoring of `items`."""
    collected = list(items)
    if count <= 0:
        return []
    positions = sorted(
        range(len(collected)),
        key=lambda index: (-score(collected[index]), index),
    )
    return [collected[index] for index in positions[:count]]''',
    variant_three='''def top_by(items, count, score):
    """Return the `count` highest-scoring of `items`."""
    ordered = sorted(items, key=score, reverse=True)
    return ordered[:count]''',
    variant_four='''def top_by(items, count, score):
    """Return the `count` highest-scoring of `items`."""
    if count <= 0:
        return []
    ordered = sorted(items, key=lambda item: (score(item), item), reverse=True)
    return ordered[:count]''',
    visible_test=_test_module(
        "stable_top",
        "Published contract for taking the highest-scoring entries.",
        """
def test_the_highest_scores_come_first() -> None:
    assert top_by(["a", "bb", "ccc"], 2, len) == ["ccc", "bb"]


def test_asking_for_more_than_there_is_returns_everything() -> None:
    assert top_by(["a", "bb"], 5, len) == ["bb", "a"]
""",
        imports="from stable_top import top_by\n",
    ),
    hidden_test=_test_module(
        "stable_top",
        "The part of the contract the published tests do not state.",
        """
def test_the_highest_scores_come_first() -> None:
    assert top_by(["a", "bb", "ccc"], 2, len) == ["ccc", "bb"]


def test_equal_scores_keep_the_order_they_arrived_in() -> None:
    assert top_by(["bo", "ada", "cy"], 2, len) == ["ada", "bo"]


def test_a_count_of_zero_or_less_returns_nothing() -> None:
    assert top_by(["a", "bb"], -1, len) == []
""",
        imports="from stable_top import top_by\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G003 = D2TaskSpec(
    template_id="d6_numeric.digit_carries",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-digit-carries",
    module="digit_carries",
    module_doc="Settling a run of digits that have grown past their base.",
    issue=(
        "normalise_digits() is documented to settle a list of digits so every one of them is "
        "below the base, carrying leftwards. Callers report that a carry out of the leading "
        "digit is dropped, so the number silently shrinks, and that an empty list of digits "
        "comes back empty instead of as a single zero."
    ),
    expected=(
        "normalise_digits(digits, base) returns the digits, most significant first, with every "
        "digit below the base; a carry past the leading digit extends the list on the left. An "
        "empty list of digits describes zero and returns [0]."
    ),
    baseline_reason=(
        "it carries in place from the right and discards whatever is left over at the front, "
        "and it returns its input untouched when there is nothing to carry into"
    ),
    edge_cases=(
        "a carry out of the leading digit extends the list",
        "an empty list of digits returns a single zero",
    ),
    baseline='''def normalise_digits(digits, base):
    """Return `digits` settled so each one is below `base`."""
    settled = list(digits)
    carry = 0
    for index in range(len(settled) - 1, -1, -1):
        total = settled[index] + carry
        settled[index] = total % base
        carry = total // base
    return settled''',
    variant_one='''def normalise_digits(digits, base):
    """Return `digits` settled so each one is below `base`."""
    settled = list(digits)
    carry = 0
    for index in range(len(settled) - 1, -1, -1):
        total = settled[index] + carry
        settled[index] = total % base
        carry = total // base
    while carry:
        settled.insert(0, carry % base)
        carry //= base
    return settled or [0]''',
    variant_two='''def normalise_digits(digits, base):
    """Return `digits` settled so each one is below `base`."""
    value = 0
    for digit in digits:
        value = value * base + digit
    rendered = []
    while value:
        rendered.append(value % base)
        value //= base
    rendered.reverse()
    return rendered or [0]''',
    variant_three='''def normalise_digits(digits, base):
    """Return `digits` settled so each one is below `base`."""
    settled = list(digits)
    carry = 0
    for index in range(len(settled) - 1, -1, -1):
        total = settled[index] + carry
        settled[index] = total % base
        carry = total // base
    while carry:
        settled.insert(0, carry % base)
        carry //= base
    return settled''',
    variant_four='''def normalise_digits(digits, base):
    """Return `digits` settled so each one is below `base`."""
    settled = list(digits)
    if not settled:
        return [0]
    carry = 0
    for index in range(len(settled) - 1, -1, -1):
        total = settled[index] + carry
        settled[index] = total % base
        carry = total // base
    return settled''',
    visible_test=_test_module(
        "digit_carries",
        "Published contract for settling digits past their base.",
        """
def test_a_digit_past_the_base_carries_left() -> None:
    assert normalise_digits([1, 12], 10) == [2, 2]


def test_digits_already_below_the_base_are_left_alone() -> None:
    assert normalise_digits([4, 0, 7], 10) == [4, 0, 7]
""",
        imports="from digit_carries import normalise_digits\n",
    ),
    hidden_test=_test_module(
        "digit_carries",
        "The part of the contract the published tests do not state.",
        """
def test_a_digit_past_the_base_carries_left() -> None:
    assert normalise_digits([1, 12], 10) == [2, 2]


def test_a_carry_out_of_the_leading_digit_extends_the_list() -> None:
    assert normalise_digits([9, 13], 10) == [1, 0, 3]


def test_no_digits_at_all_describe_zero() -> None:
    assert normalise_digits([], 10) == [0]
""",
        imports="from digit_carries import normalise_digits\n",
    ),
)

_G004 = D2TaskSpec(
    template_id="d6_numeric.share_rounding",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-share-rounding",
    module="share_rounding",
    module_doc="Splitting a total into whole shares that still add up.",
    issue=(
        "whole_shares() is documented to split a total into whole shares in proportion to a set "
        "of weights, without losing or inventing units. Callers report that the shares do not "
        "add back up to the total, and that a set of weights summing to zero raises "
        "ZeroDivisionError instead of returning zero shares."
    ),
    expected=(
        "whole_shares(total, weights) returns one whole share per weight, proportional to the "
        "weights, whose sum is exactly the total; the remainder goes to the largest fractional "
        "parts first. Weights summing to zero return a zero for each weight."
    ),
    baseline_reason=(
        "it truncates each share independently, so the remainder is dropped, and it divides by "
        "the weight total without checking it"
    ),
    edge_cases=(
        "the shares add back up to the total",
        "weights summing to zero return a zero for each weight",
    ),
    baseline='''def whole_shares(total, weights):
    """Split `total` into whole shares proportional to `weights`."""
    overall = sum(weights)
    return [int(total * weight / overall) for weight in weights]''',
    variant_one='''def whole_shares(total, weights):
    """Split `total` into whole shares proportional to `weights`."""
    overall = sum(weights)
    if overall == 0:
        return [0 for _ in weights]
    shares = [int(total * weight / overall) for weight in weights]
    remainders = sorted(
        range(len(weights)),
        key=lambda index: (total * weights[index] / overall) - shares[index],
        reverse=True,
    )
    for index in remainders[: total - sum(shares)]:
        shares[index] += 1
    return shares''',
    variant_two='''def whole_shares(total, weights):
    """Split `total` into whole shares proportional to `weights`."""
    overall = sum(weights)
    if not overall:
        return [0] * len(weights)
    shares = []
    running_weight = 0
    awarded = 0
    for weight in weights:
        running_weight += weight
        target = round(total * running_weight / overall)
        shares.append(target - awarded)
        awarded = target
    return shares''',
    variant_three='''def whole_shares(total, weights):
    """Split `total` into whole shares proportional to `weights`."""
    overall = sum(weights)
    shares = [int(total * weight / overall) for weight in weights]
    position = 0
    while sum(shares) < total and shares:
        shares[position % len(shares)] += 1
        position += 1
    return shares''',
    variant_four='''def whole_shares(total, weights):
    """Split `total` into whole shares proportional to `weights`."""
    overall = sum(weights)
    if overall == 0:
        return [0 for _ in weights]
    return [int(total * weight / overall) for weight in weights]''',
    visible_test=_test_module(
        "share_rounding",
        "Published contract for splitting a total into whole shares.",
        """
def test_equal_weights_split_evenly() -> None:
    assert whole_shares(10, [1, 1]) == [5, 5]


def test_a_single_weight_takes_everything() -> None:
    assert whole_shares(7, [3]) == [7]
""",
        imports="from share_rounding import whole_shares\n",
    ),
    hidden_test=_test_module(
        "share_rounding",
        "The part of the contract the published tests do not state.",
        """
def test_equal_weights_split_evenly() -> None:
    assert whole_shares(10, [1, 1]) == [5, 5]


def test_the_shares_add_back_up_to_the_total() -> None:
    assert sum(whole_shares(10, [1, 1, 1])) == 10


def test_weights_summing_to_zero_return_zero_shares() -> None:
    assert whole_shares(10, [0, 0]) == [0, 0]
""",
        imports="from share_rounding import whole_shares\n",
    ),
)

# ------------------------------------------------------------------------ parsing validation

_G005 = D2TaskSpec(
    template_id="d6_parsing.duration_words",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-duration-words",
    module="duration_words",
    module_doc="Reading a spoken duration into a number of seconds.",
    issue=(
        "read_duration() is documented to read a duration written as a run of value-and-unit "
        "pairs into seconds. Callers report that a duration naming the same unit twice keeps "
        "only the last occurrence, and that an unknown unit is silently ignored instead of "
        "raising."
    ),
    expected=(
        "read_duration(text) sums every value-and-unit pair in the text, so a repeated unit "
        "contributes twice, and raises ValueError on a unit it does not know."
    ),
    baseline_reason=(
        "it collects the pairs into a dictionary keyed by unit, which drops a repeat, and it "
        "skips a pair whose unit is not in its table"
    ),
    edge_cases=(
        "a repeated unit contributes each time it appears",
        "an unknown unit raises ValueError",
    ),
    baseline='''def read_duration(text):
    """Return the number of seconds `text` describes."""
    scale = {"s": 1, "m": 60, "h": 3600}
    found = {}
    parts = text.split()
    for position in range(0, len(parts) - 1, 2):
        unit = parts[position + 1]
        if unit in scale:
            found[unit] = int(parts[position])
    return sum(value * scale[unit] for unit, value in found.items())''',
    variant_one='''def read_duration(text):
    """Return the number of seconds `text` describes."""
    scale = {"s": 1, "m": 60, "h": 3600}
    total = 0
    parts = text.split()
    for position in range(0, len(parts) - 1, 2):
        unit = parts[position + 1]
        if unit not in scale:
            raise ValueError(f"unknown unit {unit}")
        total += int(parts[position]) * scale[unit]
    return total''',
    variant_two='''def read_duration(text):
    """Return the number of seconds `text` describes."""
    scale = {"s": 1, "m": 60, "h": 3600}
    parts = text.split()
    pairs = list(zip(parts[0::2], parts[1::2]))
    unknown = [unit for _, unit in pairs if unit not in scale]
    if unknown:
        raise ValueError(f"unknown unit {unknown[0]}")
    return sum(int(value) * scale[unit] for value, unit in pairs)''',
    variant_three='''def read_duration(text):
    """Return the number of seconds `text` describes."""
    scale = {"s": 1, "m": 60, "h": 3600}
    total = 0
    parts = text.split()
    for position in range(0, len(parts) - 1, 2):
        unit = parts[position + 1]
        if unit in scale:
            total += int(parts[position]) * scale[unit]
    return total''',
    variant_four='''def read_duration(text):
    """Return the number of seconds `text` describes."""
    scale = {"s": 1, "m": 60, "h": 3600}
    found = {}
    parts = text.split()
    for position in range(0, len(parts) - 1, 2):
        unit = parts[position + 1]
        if unit not in scale:
            raise ValueError(f"unknown unit {unit}")
        found[unit] = int(parts[position])
    return sum(value * scale[unit] for unit, value in found.items())''',
    visible_test=_test_module(
        "duration_words",
        "Published contract for reading a spoken duration.",
        """
def test_two_units_are_added_together() -> None:
    assert read_duration("2 m 30 s") == 150


def test_a_single_unit_reads_on_its_own() -> None:
    assert read_duration("3 h") == 10800
""",
        imports="from duration_words import read_duration\n",
    ),
    hidden_test=_test_module(
        "duration_words",
        "The part of the contract the published tests do not state.",
        """
import pytest

from duration_words import read_duration


def test_two_units_are_added_together() -> None:
    assert read_duration("2 m 30 s") == 150


def test_a_repeated_unit_contributes_each_time() -> None:
    assert read_duration("1 m 1 m") == 120


def test_an_unknown_unit_is_refused() -> None:
    with pytest.raises(ValueError):
        read_duration("5 w")
""",
    ),
)

_G006 = D2TaskSpec(
    template_id="d6_parsing.tag_pairs",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-tag-pairs",
    module="tag_pairs",
    module_doc="Reading a run of key-value tags off a label.",
    issue=(
        "read_tags() is documented to read a label of comma-separated key=value tags into "
        "pairs. Callers report that a value containing an equals sign loses everything after "
        "the second one, and that a tag with no equals sign is returned with an empty key "
        "instead of raising."
    ),
    expected=(
        "read_tags(label) splits each tag on its first equals sign only, so the value keeps any "
        "further ones, and raises ValueError on a tag carrying no equals sign at all."
    ),
    baseline_reason=(
        "it splits each tag on every equals sign and takes the first two fields, and it pads a "
        "tag with no separator instead of refusing it"
    ),
    edge_cases=(
        "a value containing an equals sign keeps it",
        "a tag with no equals sign raises ValueError",
    ),
    baseline='''def read_tags(label):
    """Return the key-value pairs in `label`."""
    pairs = []
    for tag in label.split(","):
        fields = tag.split("=")
        key = fields[0] if fields else ""
        value = fields[1] if len(fields) > 1 else ""
        pairs.append((key.strip(), value.strip()))
    return pairs''',
    variant_one='''def read_tags(label):
    """Return the key-value pairs in `label`."""
    pairs = []
    for tag in label.split(","):
        if "=" not in tag:
            raise ValueError(f"tag {tag.strip()} carries no value")
        key, _, value = tag.partition("=")
        pairs.append((key.strip(), value.strip()))
    return pairs''',
    variant_two='''def read_tags(label):
    """Return the key-value pairs in `label`."""
    pairs = []
    for tag in label.split(","):
        fields = tag.split("=", 1)
        if len(fields) != 2:
            raise ValueError(f"tag {tag.strip()} carries no value")
        pairs.append((fields[0].strip(), fields[1].strip()))
    return pairs''',
    variant_three='''def read_tags(label):
    """Return the key-value pairs in `label`."""
    pairs = []
    for tag in label.split(","):
        key, _, value = tag.partition("=")
        pairs.append((key.strip(), value.strip()))
    return pairs''',
    variant_four='''def read_tags(label):
    """Return the key-value pairs in `label`."""
    pairs = []
    for tag in label.split(","):
        fields = tag.split("=")
        if len(fields) < 2:
            raise ValueError(f"tag {tag.strip()} carries no value")
        pairs.append((fields[0].strip(), fields[1].strip()))
    return pairs''',
    visible_test=_test_module(
        "tag_pairs",
        "Published contract for reading key-value tags.",
        """
def test_two_tags_read_as_two_pairs() -> None:
    assert read_tags("a=1,b=2") == [("a", "1"), ("b", "2")]


def test_surrounding_space_is_dropped() -> None:
    assert read_tags(" name = ada ") == [("name", "ada")]
""",
        imports="from tag_pairs import read_tags\n",
    ),
    hidden_test=_test_module(
        "tag_pairs",
        "The part of the contract the published tests do not state.",
        """
import pytest

from tag_pairs import read_tags


def test_two_tags_read_as_two_pairs() -> None:
    assert read_tags("a=1,b=2") == [("a", "1"), ("b", "2")]


def test_a_value_keeps_a_further_equals_sign() -> None:
    assert read_tags("query=a=b") == [("query", "a=b")]


def test_a_tag_without_a_value_is_refused() -> None:
    with pytest.raises(ValueError):
        read_tags("a=1,bare")
""",
    ),
)

# ------------------------------------------------------------------------- state idempotency

_G007 = D2TaskSpec(
    template_id="d6_state.lease_renewal",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-lease-renewal",
    module="lease_renewal",
    module_doc="Keeping track of which holder owns a lease, and until when.",
    issue=(
        "renew() is documented to extend a lease for the holder that already owns it, and to "
        "refuse a renewal from anybody else. Callers report that a second holder can take over "
        "an unexpired lease, and that renewing an expired lease keeps the old expiry instead of "
        "measuring the new one from now."
    ),
    expected=(
        "renew(state, holder, now, span) extends the lease only when the state is unheld, "
        "expired, or already held by that holder; a renewal from another holder while the lease "
        "is live raises PermissionError. The new expiry is always now plus span."
    ),
    baseline_reason=(
        "it overwrites the holder unconditionally and adds the span to the stored expiry rather "
        "than to now"
    ),
    edge_cases=(
        "a second holder cannot take a live lease",
        "a renewal measures the new expiry from now",
    ),
    baseline='''def renew(state, holder, now, span):
    """Extend the lease in `state` for `holder`."""
    state["holder"] = holder
    state["expires_at"] = state.get("expires_at", now) + span
    return state''',
    variant_one='''def renew(state, holder, now, span):
    """Extend the lease in `state` for `holder`."""
    owner = state.get("holder")
    expires_at = state.get("expires_at", 0)
    if owner is not None and owner != holder and expires_at > now:
        raise PermissionError(f"the lease is held by {owner}")
    state["holder"] = holder
    state["expires_at"] = now + span
    return state''',
    variant_two='''def renew(state, holder, now, span):
    """Extend the lease in `state` for `holder`."""
    live = state.get("expires_at", 0) > now
    same_holder = state.get("holder") in (None, holder)
    if live and not same_holder:
        raise PermissionError(f"the lease is held by {state['holder']}")
    return {**state, "holder": holder, "expires_at": now + span}''',
    variant_three='''def renew(state, holder, now, span):
    """Extend the lease in `state` for `holder`."""
    owner = state.get("holder")
    if owner is not None and owner != holder and state.get("expires_at", 0) > now:
        raise PermissionError(f"the lease is held by {owner}")
    state["holder"] = holder
    state["expires_at"] = state.get("expires_at", now) + span
    return state''',
    variant_four='''def renew(state, holder, now, span):
    """Extend the lease in `state` for `holder`."""
    state["holder"] = holder
    state["expires_at"] = now + span
    return state''',
    visible_test=_test_module(
        "lease_renewal",
        "Published contract for renewing a lease.",
        """
def test_an_unheld_lease_is_taken() -> None:
    assert renew({}, "ada", 10, 5) == {"holder": "ada", "expires_at": 15}


def test_the_holder_renews_its_own_lease() -> None:
    state = {"holder": "ada", "expires_at": 15}
    assert renew(state, "ada", 10, 5)["holder"] == "ada"
""",
        imports="from lease_renewal import renew\n",
    ),
    hidden_test=_test_module(
        "lease_renewal",
        "The part of the contract the published tests do not state.",
        """
import pytest

from lease_renewal import renew


def test_an_unheld_lease_is_taken() -> None:
    assert renew({}, "ada", 10, 5) == {"holder": "ada", "expires_at": 15}


def test_a_second_holder_cannot_take_a_live_lease() -> None:
    with pytest.raises(PermissionError):
        renew({"holder": "ada", "expires_at": 20}, "bo", 10, 5)


def test_a_renewal_measures_the_new_expiry_from_now() -> None:
    state = {"holder": "ada", "expires_at": 12}
    assert renew(state, "ada", 40, 5)["expires_at"] == 45
""",
    ),
)

_G008 = D2TaskSpec(
    template_id="d6_state.draft_publishing",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-draft-publishing",
    module="draft_publishing",
    module_doc="Moving a draft through to published, once.",
    issue=(
        "publish() is documented to publish a draft and to be safe to call twice. Callers "
        "report that a second call bumps the revision again, and that publishing a withdrawn "
        "document silently revives it instead of raising."
    ),
    expected=(
        "publish(document) sets the status to published and increments the revision the first "
        "time only; a second call returns the document unchanged. A withdrawn document raises "
        "ValueError."
    ),
    baseline_reason=(
        "it increments the revision on every call and does not look at the status it is leaving"
    ),
    edge_cases=(
        "a second publish leaves the revision alone",
        "a withdrawn document cannot be published",
    ),
    baseline='''def publish(document):
    """Publish `document`, once."""
    document["status"] = "published"
    document["revision"] = document.get("revision", 0) + 1
    return document''',
    variant_one='''def publish(document):
    """Publish `document`, once."""
    status = document.get("status")
    if status == "withdrawn":
        raise ValueError("a withdrawn document cannot be published")
    if status == "published":
        return document
    document["status"] = "published"
    document["revision"] = document.get("revision", 0) + 1
    return document''',
    variant_two='''def publish(document):
    """Publish `document`, once."""
    status = document.get("status")
    refused = {"withdrawn"}
    if status in refused:
        raise ValueError("a withdrawn document cannot be published")
    already = status == "published"
    return {
        **document,
        "status": "published",
        "revision": document.get("revision", 0) + (0 if already else 1),
    }''',
    variant_three='''def publish(document):
    """Publish `document`, once."""
    if document.get("status") == "published":
        return document
    document["status"] = "published"
    document["revision"] = document.get("revision", 0) + 1
    return document''',
    variant_four='''def publish(document):
    """Publish `document`, once."""
    if document.get("status") == "withdrawn":
        raise ValueError("a withdrawn document cannot be published")
    document["status"] = "published"
    document["revision"] = document.get("revision", 0) + 1
    return document''',
    visible_test=_test_module(
        "draft_publishing",
        "Published contract for publishing a draft.",
        """
def test_a_draft_becomes_published() -> None:
    assert publish({"status": "draft", "revision": 1})["status"] == "published"


def test_publishing_bumps_the_revision() -> None:
    assert publish({"status": "draft", "revision": 1})["revision"] == 2
""",
        imports="from draft_publishing import publish\n",
    ),
    hidden_test=_test_module(
        "draft_publishing",
        "The part of the contract the published tests do not state.",
        """
import pytest

from draft_publishing import publish


def test_a_draft_becomes_published() -> None:
    assert publish({"status": "draft", "revision": 1})["status"] == "published"


def test_a_second_publish_leaves_the_revision_alone() -> None:
    document = publish({"status": "draft", "revision": 1})
    assert publish(document)["revision"] == 2


def test_a_withdrawn_document_is_refused() -> None:
    with pytest.raises(ValueError):
        publish({"status": "withdrawn", "revision": 3})
""",
    ),
)

# --------------------------------------------------------------------------- error handling

_G009 = D2TaskSpec(
    template_id="d6_error.deadline_guard",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-deadline-guard",
    module="deadline_guard",
    module_doc="Starting as many steps as a deadline allows, and no more.",
    issue=(
        "run_until() is documented to start steps in order while the clock has not passed the "
        "deadline, and to report which ones ran. Callers report that a step is abandoned "
        "half-way when the deadline falls during it, and that a step whose start lands exactly "
        "on the deadline is refused although the deadline has not passed."
    ),
    expected=(
        "run_until(steps, deadline, clock) reads the clock before each step and starts it while "
        "the reading is at or before the deadline; a step that has started always runs to "
        "completion. It returns the results of the steps that ran."
    ),
    baseline_reason=(
        "it re-reads the clock after starting a step and discards the result when the deadline "
        "has passed, and its comparison excludes the deadline itself"
    ),
    edge_cases=(
        "a step that has started keeps its result",
        "a start landing exactly on the deadline is allowed",
    ),
    baseline='''def run_until(steps, deadline, clock):
    """Run `steps` in order while the deadline has not passed."""
    done = []
    for step in steps:
        if clock() >= deadline:
            break
        result = step()
        if clock() > deadline:
            break
        done.append(result)
    return done''',
    variant_one='''def run_until(steps, deadline, clock):
    """Run `steps` in order while the deadline has not passed."""
    done = []
    for step in steps:
        if clock() > deadline:
            break
        done.append(step())
    return done''',
    variant_two='''def run_until(steps, deadline, clock):
    """Run `steps` in order while the deadline has not passed."""
    done = []
    remaining = list(steps)
    while remaining:
        if clock() > deadline:
            return done
        step = remaining.pop(0)
        done.append(step())
    return done''',
    variant_three='''def run_until(steps, deadline, clock):
    """Run `steps` in order while the deadline has not passed."""
    done = []
    for step in steps:
        if clock() >= deadline:
            break
        done.append(step())
    return done''',
    variant_four='''def run_until(steps, deadline, clock):
    """Run `steps` in order while the deadline has not passed."""
    done = []
    for step in steps:
        if clock() > deadline:
            break
        result = step()
        if clock() > deadline:
            break
        done.append(result)
    return done''',
    visible_test=_test_module(
        "deadline_guard",
        "Published contract for running steps against a deadline.",
        """
def test_every_step_runs_while_there_is_time() -> None:
    ticks = iter([0, 1, 2, 3, 4, 5])
    assert run_until([lambda: "a", lambda: "b"], 10, lambda: next(ticks)) == ["a", "b"]


def test_no_step_runs_once_the_deadline_has_passed() -> None:
    assert run_until([lambda: "a"], 1, lambda: 9) == []
""",
        imports="from deadline_guard import run_until\n",
    ),
    hidden_test=_test_module(
        "deadline_guard",
        "The part of the contract the published tests do not state.",
        """
def test_every_step_runs_while_there_is_time() -> None:
    ticks = iter([0, 1, 2, 3, 4, 5])
    assert run_until([lambda: "a", lambda: "b"], 10, lambda: next(ticks)) == ["a", "b"]


def test_a_step_that_has_started_keeps_its_result() -> None:
    ticks = iter([0, 99, 99])
    assert run_until([lambda: "a", lambda: "b"], 5, lambda: next(ticks)) == ["a"]


def test_a_start_landing_on_the_deadline_is_allowed() -> None:
    assert run_until([lambda: "a"], 5, lambda: 5) == ["a"]
""",
        imports="from deadline_guard import run_until\n",
    ),
)

# ----------------------------------------------------------------------- data transformation

_G010 = D2TaskSpec(
    template_id="d6_transform.column_pivot",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-column-pivot",
    module="column_pivot",
    module_doc="Turning a list of records into one list per field.",
    issue=(
        "pivot() is documented to turn a list of records into a mapping from field name to the "
        "list of its values. Callers report that a record missing a field shifts every later "
        "value up a position, and that a field appearing only in a later record is dropped."
    ),
    expected=(
        "pivot(records) returns one list per field seen in any record, each holding one entry "
        "per record in order, with None where a record does not carry the field."
    ),
    baseline_reason=(
        "it takes its field list from the first record alone and appends only the values it finds"
    ),
    edge_cases=(
        "a record missing a field holds its place with None",
        "a field appearing only later still gets a column",
    ),
    baseline='''def pivot(records):
    """Return one list of values per field across `records`."""
    if not records:
        return {}
    columns = {field: [] for field in records[0]}
    for record in records:
        for field in columns:
            if field in record:
                columns[field].append(record[field])
    return columns''',
    variant_one='''def pivot(records):
    """Return one list of values per field across `records`."""
    fields = []
    for record in records:
        for field in record:
            if field not in fields:
                fields.append(field)
    return {field: [record.get(field) for record in records] for field in fields}''',
    variant_two='''def pivot(records):
    """Return one list of values per field across `records`."""
    columns = {}
    for position, record in enumerate(records):
        for field, value in record.items():
            column = columns.setdefault(field, [None] * len(records))
            column[position] = value
    return columns''',
    variant_three='''def pivot(records):
    """Return one list of values per field across `records`."""
    if not records:
        return {}
    columns = {field: [] for field in records[0]}
    for record in records:
        for field in columns:
            columns[field].append(record.get(field))
    return columns''',
    variant_four='''def pivot(records):
    """Return one list of values per field across `records`."""
    fields = []
    for record in records:
        for field in record:
            if field not in fields:
                fields.append(field)
    columns = {field: [] for field in fields}
    for record in records:
        for field in fields:
            if field in record:
                columns[field].append(record[field])
    return columns''',
    visible_test=_test_module(
        "column_pivot",
        "Published contract for pivoting records into columns.",
        """
def test_two_records_share_their_fields() -> None:
    assert pivot([{"a": 1}, {"a": 2}]) == {"a": [1, 2]}


def test_no_records_pivot_to_nothing() -> None:
    assert pivot([]) == {}
""",
        imports="from column_pivot import pivot\n",
    ),
    hidden_test=_test_module(
        "column_pivot",
        "The part of the contract the published tests do not state.",
        """
def test_two_records_share_their_fields() -> None:
    assert pivot([{"a": 1}, {"a": 2}]) == {"a": [1, 2]}


def test_a_record_missing_a_field_holds_its_place() -> None:
    assert pivot([{"a": 1}, {}]) == {"a": [1, None]}


def test_a_field_appearing_only_later_still_gets_a_column() -> None:
    assert pivot([{"a": 1}, {"b": 2}]) == {"a": [1, None], "b": [None, 2]}
""",
        imports="from column_pivot import pivot\n",
    ),
)

_G011 = D2TaskSpec(
    template_id="d6_error.required_fields",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-required-fields",
    module="required_fields",
    module_doc="Checking that a record carries everything a step needs.",
    issue=(
        "require_all() is documented to refuse a record that is missing any required field, "
        "naming all of them. Callers report that only the first missing field is named, so a "
        "form has to be submitted once per mistake, and that a field present but empty is "
        "reported as missing."
    ),
    expected=(
        "require_all(record, names) raises KeyError whose message names every missing field, "
        "in the order the names were given. A field is missing only when the record does not "
        "carry it; a field carrying an empty or zero value is present."
    ),
    baseline_reason=(
        "it raises on the first name it fails and tests the value for truth rather than the key "
        "for presence"
    ),
    edge_cases=(
        "every missing field is named, not only the first",
        "a field carrying an empty value is present",
    ),
    baseline='''def require_all(record, names):
    """Refuse `record` unless it carries every name in `names`."""
    for name in names:
        if not record.get(name):
            raise KeyError(name)
    return record''',
    variant_one='''def require_all(record, names):
    """Refuse `record` unless it carries every name in `names`."""
    missing = [name for name in names if name not in record]
    if missing:
        raise KeyError(", ".join(missing))
    return record''',
    variant_two='''def require_all(record, names):
    """Refuse `record` unless it carries every name in `names`."""
    carried = set(record)
    missing = []
    for name in names:
        if name not in carried:
            missing.append(name)
    if missing:
        raise KeyError(", ".join(missing))
    return record''',
    variant_three='''def require_all(record, names):
    """Refuse `record` unless it carries every name in `names`."""
    missing = [name for name in names if not record.get(name)]
    if missing:
        raise KeyError(", ".join(missing))
    return record''',
    variant_four='''def require_all(record, names):
    """Refuse `record` unless it carries every name in `names`."""
    for name in names:
        if name not in record:
            raise KeyError(name)
    return record''',
    visible_test=_test_module(
        "required_fields",
        "Published contract for checking required fields.",
        """
import pytest

from required_fields import require_all


def test_a_complete_record_passes() -> None:
    assert require_all({"a": 1, "b": 2}, ("a", "b")) == {"a": 1, "b": 2}


def test_a_missing_field_is_refused() -> None:
    with pytest.raises(KeyError):
        require_all({"a": 1}, ("a", "b"))
""",
    ),
    hidden_test=_test_module(
        "required_fields",
        "The part of the contract the published tests do not state.",
        """
import pytest

from required_fields import require_all


def test_a_complete_record_passes() -> None:
    assert require_all({"a": 1, "b": 2}, ("a", "b")) == {"a": 1, "b": 2}


def test_every_missing_field_is_named() -> None:
    with pytest.raises(KeyError) as caught:
        require_all({}, ("a", "b"))
    assert "a" in str(caught.value) and "b" in str(caught.value)


def test_a_field_carrying_an_empty_value_is_present() -> None:
    assert require_all({"a": ""}, ("a",)) == {"a": ""}
""",
    ),
)

_G012 = D2TaskSpec(
    template_id="d6_error.checked_cast",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-checked-cast",
    module="checked_cast",
    module_doc="Converting a value to a declared kind, or saying why not.",
    issue=(
        "checked_cast() is documented to convert a value to a declared kind and to raise a "
        "TypeError naming the kind it was given when it cannot. Callers report that True is "
        "accepted where a whole number is required, and that the refusal message does not say "
        "what was passed."
    ),
    expected=(
        "checked_cast(value, kind) returns the value converted to the kind. A boolean is never "
        "accepted where int is required, because a flag is not a number. A refusal raises "
        "TypeError whose message names the kind of the value it was given."
    ),
    baseline_reason=(
        "it converts with the kind directly, and bool is a subclass of int, and its message "
        "names only the kind it wanted"
    ),
    edge_cases=(
        "a boolean is refused where a whole number is required",
        "the refusal names the kind of the value it was given",
    ),
    baseline='''def checked_cast(value, kind):
    """Return `value` as `kind`, or refuse it."""
    try:
        return kind(value)
    except (TypeError, ValueError):
        raise TypeError(f"expected {kind.__name__}") from None''',
    variant_one='''def checked_cast(value, kind):
    """Return `value` as `kind`, or refuse it."""
    if kind is int and isinstance(value, bool):
        raise TypeError(f"expected int, got {type(value).__name__}")
    try:
        return kind(value)
    except (TypeError, ValueError):
        raise TypeError(f"expected {kind.__name__}, got {type(value).__name__}") from None''',
    variant_two='''def checked_cast(value, kind):
    """Return `value` as `kind`, or refuse it."""
    refused = kind is int and value.__class__ is bool
    if not refused:
        try:
            return kind(value)
        except (TypeError, ValueError):
            refused = True
    raise TypeError(f"expected {kind.__name__}, got {type(value).__name__}")''',
    variant_three='''def checked_cast(value, kind):
    """Return `value` as `kind`, or refuse it."""
    if kind is int and isinstance(value, bool):
        raise TypeError(f"expected {kind.__name__}")
    try:
        return kind(value)
    except (TypeError, ValueError):
        raise TypeError(f"expected {kind.__name__}") from None''',
    variant_four='''def checked_cast(value, kind):
    """Return `value` as `kind`, or refuse it."""
    try:
        return kind(value)
    except (TypeError, ValueError):
        raise TypeError(f"expected {kind.__name__}, got {type(value).__name__}") from None''',
    visible_test=_test_module(
        "checked_cast",
        "Published contract for converting a value to a declared kind.",
        """
import pytest

from checked_cast import checked_cast


def test_a_numeric_string_becomes_a_number() -> None:
    assert checked_cast("12", int) == 12


def test_a_word_is_refused_as_a_number() -> None:
    with pytest.raises(TypeError):
        checked_cast("ada", int)
""",
    ),
    hidden_test=_test_module(
        "checked_cast",
        "The part of the contract the published tests do not state.",
        """
import pytest

from checked_cast import checked_cast


def test_a_numeric_string_becomes_a_number() -> None:
    assert checked_cast("12", int) == 12


def test_a_flag_is_not_a_number() -> None:
    with pytest.raises(TypeError):
        checked_cast(True, int)


def test_the_refusal_names_what_it_was_given() -> None:
    with pytest.raises(TypeError) as caught:
        checked_cast("ada", int)
    assert "str" in str(caught.value)
""",
    ),
)

_G015 = D2TaskSpec(
    template_id="d6_boundary.first_gap",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-first-gap",
    module="first_gap",
    module_doc="Finding the lowest slot nobody has taken.",
    issue=(
        "first_gap() is documented to return the lowest whole number from zero upwards that is "
        "not in a set of taken slots. Callers report that a slot listed twice makes the answer "
        "too low, and that a negative slot in the list does the same."
    ),
    expected=(
        "first_gap(taken) returns the lowest whole number from zero upwards that does not "
        "appear in `taken`. Repeated entries count once, and entries below zero are not slots "
        "and are ignored."
    ),
    baseline_reason=(
        "it walks the sorted list comparing each entry to its position, which a repeat or a "
        "negative entry shifts"
    ),
    edge_cases=(
        "a slot listed twice does not shift the answer",
        "a slot below zero is ignored",
    ),
    baseline='''def first_gap(taken):
    """Return the lowest whole number not in `taken`."""
    ordered = sorted(taken)
    for position, slot in enumerate(ordered):
        if slot != position:
            return position
    return len(ordered)''',
    variant_one='''def first_gap(taken):
    """Return the lowest whole number not in `taken`."""
    occupied = {slot for slot in taken if slot >= 0}
    candidate = 0
    while candidate in occupied:
        candidate += 1
    return candidate''',
    variant_two='''def first_gap(taken):
    """Return the lowest whole number not in `taken`."""
    ordered = sorted({slot for slot in taken if slot >= 0})
    for position, slot in enumerate(ordered):
        if slot != position:
            return position
    return len(ordered)''',
    variant_three='''def first_gap(taken):
    """Return the lowest whole number not in `taken`."""
    ordered = sorted(set(taken))
    for position, slot in enumerate(ordered):
        if slot != position:
            return position
    return len(ordered)''',
    variant_four='''def first_gap(taken):
    """Return the lowest whole number not in `taken`."""
    ordered = sorted(slot for slot in taken if slot >= 0)
    for position, slot in enumerate(ordered):
        if slot != position:
            return position
    return len(ordered)''',
    visible_test=_test_module(
        "first_gap",
        "Published contract for finding the lowest free slot.",
        """
def test_a_hole_in_the_middle_is_the_answer() -> None:
    assert first_gap([0, 1, 3]) == 2


def test_a_full_run_continues_past_the_end() -> None:
    assert first_gap([0, 1, 2]) == 3
""",
        imports="from first_gap import first_gap\n",
    ),
    hidden_test=_test_module(
        "first_gap",
        "The part of the contract the published tests do not state.",
        """
def test_a_hole_in_the_middle_is_the_answer() -> None:
    assert first_gap([0, 1, 3]) == 2


def test_a_slot_listed_twice_counts_once() -> None:
    assert first_gap([0, 0, 1]) == 2


def test_a_slot_below_zero_is_not_a_slot() -> None:
    assert first_gap([-1, 0, 1]) == 2
""",
        imports="from first_gap import first_gap\n",
    ),
)

_G018 = D2TaskSpec(
    template_id="d6_numeric.bounded_average",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-bounded-average",
    module="bounded_average",
    module_doc="Averaging readings that a sensor may report out of range.",
    issue=(
        "bounded_average() is documented to average readings after pulling each one back into "
        "the sensor's range. Callers report that a single wild reading still drags the average "
        "far outside the range, and that a run with no readings at all raises "
        "ZeroDivisionError."
    ),
    expected=(
        "bounded_average(readings, low, high) pulls every reading into the range first and then "
        "averages, so no single reading can drag the result past a bound. With no readings it "
        "raises ValueError."
    ),
    baseline_reason=(
        "it averages first and clamps the result afterwards, and it divides by the count "
        "without checking it"
    ),
    edge_cases=(
        "each reading is pulled into range before the average is taken",
        "no readings at all raises ValueError",
    ),
    baseline='''def bounded_average(readings, low, high):
    """Average `readings`, keeping each one inside the range."""
    average = sum(readings) / len(readings)
    return min(max(average, low), high)''',
    variant_one='''def bounded_average(readings, low, high):
    """Average `readings`, keeping each one inside the range."""
    collected = list(readings)
    if not collected:
        raise ValueError("no readings to average")
    pulled = [min(max(reading, low), high) for reading in collected]
    return sum(pulled) / len(pulled)''',
    variant_two='''def bounded_average(readings, low, high):
    """Average `readings`, keeping each one inside the range."""
    total = 0
    count = 0
    for reading in readings:
        if reading < low:
            reading = low
        elif reading > high:
            reading = high
        total += reading
        count += 1
    if count == 0:
        raise ValueError("no readings to average")
    return total / count''',
    variant_three='''def bounded_average(readings, low, high):
    """Average `readings`, keeping each one inside the range."""
    pulled = [min(max(reading, low), high) for reading in readings]
    return sum(pulled) / len(pulled)''',
    variant_four='''def bounded_average(readings, low, high):
    """Average `readings`, keeping each one inside the range."""
    collected = list(readings)
    if not collected:
        raise ValueError("no readings to average")
    average = sum(collected) / len(collected)
    return min(max(average, low), high)''',
    visible_test=_test_module(
        "bounded_average",
        "Published contract for averaging readings inside a range.",
        """
def test_readings_inside_the_range_average_as_they_are() -> None:
    assert bounded_average([2, 4], 0, 10) == 3


def test_an_average_past_the_top_is_pulled_back() -> None:
    assert bounded_average([20, 20], 0, 10) == 10
""",
        imports="from bounded_average import bounded_average\n",
    ),
    hidden_test=_test_module(
        "bounded_average",
        "The part of the contract the published tests do not state.",
        """
import pytest

from bounded_average import bounded_average


def test_readings_inside_the_range_average_as_they_are() -> None:
    assert bounded_average([2, 4], 0, 10) == 3


def test_one_wild_reading_cannot_drag_the_average() -> None:
    assert bounded_average([0, 100], 0, 10) == 5


def test_no_readings_at_all_is_refused() -> None:
    with pytest.raises(ValueError):
        bounded_average([], 0, 10)
""",
    ),
)

_G020 = D2TaskSpec(
    template_id="d6_state.ack_once",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-ack-once",
    module="ack_once",
    module_doc="Acknowledging a delivered message exactly once.",
    issue=(
        "acknowledge() is documented to acknowledge a delivered message once. Callers report "
        "that a redelivery acknowledged twice counts twice, and that acknowledging a message "
        "nobody delivered creates it instead of raising."
    ),
    expected=(
        "acknowledge(inbox, message_id) marks the message acknowledged and increments the "
        "acknowledged count the first time only; a second call leaves both alone. A message "
        "the inbox does not carry raises KeyError."
    ),
    baseline_reason=(
        "it counts every call and writes the entry with setdefault, which invents a message "
        "that was never delivered"
    ),
    edge_cases=(
        "a second acknowledgement does not count twice",
        "acknowledging an undelivered message raises KeyError",
    ),
    baseline='''def acknowledge(inbox, message_id):
    """Acknowledge `message_id` in `inbox`."""
    messages = inbox.setdefault("messages", {})
    messages.setdefault(message_id, {"acknowledged": False})
    messages[message_id]["acknowledged"] = True
    inbox["acknowledged_count"] = inbox.get("acknowledged_count", 0) + 1
    return inbox''',
    variant_one='''def acknowledge(inbox, message_id):
    """Acknowledge `message_id` in `inbox`."""
    messages = inbox.get("messages", {})
    if message_id not in messages:
        raise KeyError(message_id)
    if messages[message_id]["acknowledged"]:
        return inbox
    messages[message_id]["acknowledged"] = True
    inbox["acknowledged_count"] = inbox.get("acknowledged_count", 0) + 1
    return inbox''',
    variant_two='''def acknowledge(inbox, message_id):
    """Acknowledge `message_id` in `inbox`."""
    messages = inbox.get("messages", {})
    message = messages[message_id]
    already = message.get("acknowledged", False)
    message["acknowledged"] = True
    counted = inbox.get("acknowledged_count", 0)
    inbox["acknowledged_count"] = counted if already else counted + 1
    return inbox''',
    variant_three='''def acknowledge(inbox, message_id):
    """Acknowledge `message_id` in `inbox`."""
    messages = inbox.setdefault("messages", {})
    message = messages.setdefault(message_id, {"acknowledged": False})
    if message["acknowledged"]:
        return inbox
    message["acknowledged"] = True
    inbox["acknowledged_count"] = inbox.get("acknowledged_count", 0) + 1
    return inbox''',
    variant_four='''def acknowledge(inbox, message_id):
    """Acknowledge `message_id` in `inbox`."""
    messages = inbox.get("messages", {})
    if message_id not in messages:
        raise KeyError(message_id)
    messages[message_id]["acknowledged"] = True
    inbox["acknowledged_count"] = inbox.get("acknowledged_count", 0) + 1
    return inbox''',
    visible_test=_test_module(
        "ack_once",
        "Published contract for acknowledging a delivered message.",
        """
def test_a_delivered_message_is_acknowledged() -> None:
    inbox = {"messages": {"m1": {"acknowledged": False}}}
    assert acknowledge(inbox, "m1")["messages"]["m1"]["acknowledged"] is True


def test_the_first_acknowledgement_counts() -> None:
    inbox = {"messages": {"m1": {"acknowledged": False}}}
    assert acknowledge(inbox, "m1")["acknowledged_count"] == 1
""",
        imports="from ack_once import acknowledge\n",
    ),
    hidden_test=_test_module(
        "ack_once",
        "The part of the contract the published tests do not state.",
        """
import pytest

from ack_once import acknowledge


def test_a_delivered_message_is_acknowledged() -> None:
    inbox = {"messages": {"m1": {"acknowledged": False}}}
    assert acknowledge(inbox, "m1")["messages"]["m1"]["acknowledged"] is True


def test_a_second_acknowledgement_does_not_count_twice() -> None:
    inbox = {"messages": {"m1": {"acknowledged": False}}}
    acknowledge(inbox, "m1")
    assert acknowledge(inbox, "m1")["acknowledged_count"] == 1


def test_an_undelivered_message_is_refused() -> None:
    with pytest.raises(KeyError):
        acknowledge({"messages": {}}, "ghost")
""",
    ),
)

_G021 = D2TaskSpec(
    template_id="d6_boundary.plateau_spans",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-plateau-spans",
    module="plateau_spans",
    module_doc="Reporting the runs of equal consecutive values in a series.",
    issue=(
        "plateau_spans() is documented to report every run of equal consecutive values that is "
        "long enough. Callers report that a run reaching the end of the series is missing, and "
        "that a run exactly as long as the stated minimum is left out."
    ),
    expected=(
        "plateau_spans(values, minimum) returns one (start, length) pair for every maximal run "
        "of equal consecutive values whose length is at least minimum, including the run that "
        "ends the series."
    ),
    baseline_reason=(
        "it emits a run only when the value changes, so the final run is never emitted, and it "
        "compares the length with a strict greater-than"
    ),
    edge_cases=(
        "the run that reaches the end of the series is reported",
        "a run exactly as long as the minimum is reported",
    ),
    baseline="""def plateau_spans(values, minimum):
    \"\"\"Return (start, length) for each long enough run of equal values.\"\"\"
    spans = []
    start = 0
    for position in range(1, len(values)):
        if values[position] != values[start]:
            if position - start > minimum:
                spans.append((start, position - start))
            start = position
    return spans""",
    variant_one="""def plateau_spans(values, minimum):
    \"\"\"Return (start, length) for each long enough run of equal values.\"\"\"
    spans = []
    start = 0
    for position in range(1, len(values) + 1):
        if position == len(values) or values[position] != values[start]:
            if position - start >= minimum:
                spans.append((start, position - start))
            start = position
    return spans""",
    variant_two="""def plateau_spans(values, minimum):
    \"\"\"Return (start, length) for each long enough run of equal values.\"\"\"
    runs = []
    for index, value in enumerate(values):
        if runs and runs[-1][2] == value:
            runs[-1][1] += 1
        else:
            runs.append([index, 1, value])
    return [(start, length) for start, length, _value in runs if length >= minimum]""",
    variant_three="""def plateau_spans(values, minimum):
    \"\"\"Return (start, length) for each long enough run of equal values.\"\"\"
    spans = []
    start = 0
    for position in range(1, len(values) + 1):
        if position == len(values) or values[position] != values[start]:
            if position - start > minimum:
                spans.append((start, position - start))
            start = position
    return spans""",
    variant_four="""def plateau_spans(values, minimum):
    \"\"\"Return (start, length) for each long enough run of equal values.\"\"\"
    spans = []
    start = 0
    for position in range(1, len(values)):
        if values[position] != values[start]:
            if position - start >= minimum:
                spans.append((start, position - start))
            start = position
    return spans""",
    visible_test=_test_module(
        "plateau_spans",
        "Published contract for reporting runs of equal values.",
        """
def test_runs_longer_than_the_minimum_are_reported() -> None:
    assert plateau_spans([1, 1, 1, 2, 2, 2, 7], 2) == [(0, 3), (3, 3)]


def test_a_series_of_one_run_below_the_minimum_reports_nothing() -> None:
    assert plateau_spans([4, 9], 2) == []
""",
        imports="from plateau_spans import plateau_spans\n",
    ),
    hidden_test=_test_module(
        "plateau_spans",
        "The part of the contract the published tests do not state.",
        """
def test_runs_longer_than_the_minimum_are_reported() -> None:
    assert plateau_spans([1, 1, 1, 2, 2, 2, 7], 2) == [(0, 3), (3, 3)]


def test_the_run_reaching_the_end_is_reported() -> None:
    assert plateau_spans([4, 4, 4, 5, 5, 5], 2) == [(0, 3), (3, 3)]


def test_a_run_exactly_as_long_as_the_minimum_is_reported() -> None:
    assert plateau_spans([8, 8, 9, 9, 9, 1], 2) == [(0, 2), (2, 3)]
""",
        imports="from plateau_spans import plateau_spans\n",
    ),
)

_G022 = D2TaskSpec(
    template_id="d6_boundary.anchor_spans",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-anchor-spans",
    module="anchor_spans",
    module_doc="Working out how far each anchor reaches before the next one.",
    issue=(
        "anchor_spans() is documented to pair each anchor with the distance to the next one. "
        "Callers report that an anchor sitting at offset zero disappears from the result, and "
        "that two anchors at the same offset produce a span of length zero instead of one span."
    ),
    expected=(
        "anchor_spans(anchors, total) returns one (offset, span) pair per distinct anchor, in "
        "order, where the span reaches the next distinct anchor and the last reaches total. An "
        "anchor at offset zero is an anchor like any other."
    ),
    baseline_reason=(
        "it skips an anchor whose offset is falsy and it does not collapse repeated offsets"
    ),
    edge_cases=(
        "an anchor at offset zero is kept",
        "repeated offsets collapse into one span",
    ),
    baseline="""def anchor_spans(anchors, total):
    \"\"\"Pair each anchor with the distance to the next one.\"\"\"
    spans = []
    for index, offset in enumerate(anchors):
        if not offset:
            continue
        if index + 1 < len(anchors):
            spans.append((offset, anchors[index + 1] - offset))
        else:
            spans.append((offset, total - offset))
    return spans""",
    variant_one="""def anchor_spans(anchors, total):
    \"\"\"Pair each anchor with the distance to the next one.\"\"\"
    distinct = []
    for offset in anchors:
        if not distinct or distinct[-1] != offset:
            distinct.append(offset)
    spans = []
    for index, offset in enumerate(distinct):
        following = distinct[index + 1] if index + 1 < len(distinct) else total
        spans.append((offset, following - offset))
    return spans""",
    variant_two="""def anchor_spans(anchors, total):
    \"\"\"Pair each anchor with the distance to the next one.\"\"\"
    seen = []
    for offset in anchors:
        if offset not in seen:
            seen.append(offset)
    edges = [*seen, total]
    return [(edges[index], edges[index + 1] - edges[index]) for index in range(len(seen))]""",
    variant_three="""def anchor_spans(anchors, total):
    \"\"\"Pair each anchor with the distance to the next one.\"\"\"
    spans = []
    for index, offset in enumerate(anchors):
        if index + 1 < len(anchors):
            spans.append((offset, anchors[index + 1] - offset))
        else:
            spans.append((offset, total - offset))
    return spans""",
    variant_four="""def anchor_spans(anchors, total):
    \"\"\"Pair each anchor with the distance to the next one.\"\"\"
    distinct = []
    for offset in anchors:
        if not offset:
            continue
        if not distinct or distinct[-1] != offset:
            distinct.append(offset)
    spans = []
    for index, offset in enumerate(distinct):
        following = distinct[index + 1] if index + 1 < len(distinct) else total
        spans.append((offset, following - offset))
    return spans""",
    visible_test=_test_module(
        "anchor_spans",
        "Published contract for measuring the reach of each anchor.",
        """
def test_each_anchor_reaches_the_next_one() -> None:
    assert anchor_spans([2, 5], 9) == [(2, 3), (5, 4)]


def test_a_single_anchor_reaches_the_total() -> None:
    assert anchor_spans([3], 8) == [(3, 5)]
""",
        imports="from anchor_spans import anchor_spans\n",
    ),
    hidden_test=_test_module(
        "anchor_spans",
        "The part of the contract the published tests do not state.",
        """
def test_each_anchor_reaches_the_next_one() -> None:
    assert anchor_spans([2, 5], 9) == [(2, 3), (5, 4)]


def test_an_anchor_at_offset_zero_is_kept() -> None:
    assert anchor_spans([0, 4], 8) == [(0, 4), (4, 4)]


def test_repeated_offsets_collapse_into_one_span() -> None:
    assert anchor_spans([1, 1, 6], 9) == [(1, 5), (6, 3)]
""",
        imports="from anchor_spans import anchor_spans\n",
    ),
)

_G023 = D2TaskSpec(
    template_id="d6_transform.slab_index",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-slab-index",
    module="slab_index",
    module_doc="Numbering the fixed-size slabs a run of positions falls into.",
    issue=(
        "slab_index() is documented to give each position the number of the slab it belongs to. "
        "Callers report that a slab size of one puts every position in slab zero, and that the "
        "positions of a trailing partial slab are numbered as though they were in the one before."
    ),
    expected=(
        "slab_index(count, size) returns one slab number per position: position // size, so a "
        "size of one numbers every position separately and a trailing partial slab gets a number "
        "of its own."
    ),
    baseline_reason=(
        "it short-circuits a size of one or less to a single slab and it clamps the number to "
        "the count of whole slabs"
    ),
    edge_cases=(
        "a slab size of one numbers every position separately",
        "a trailing partial slab gets a number of its own",
    ),
    baseline="""def slab_index(count, size):
    \"\"\"Return the slab number of each of `count` positions.\"\"\"
    if size <= 1:
        return [0] * count
    highest = count // size - 1
    return [min(position // size, highest) for position in range(count)]""",
    variant_one="""def slab_index(count, size):
    \"\"\"Return the slab number of each of `count` positions.\"\"\"
    return [position // size for position in range(count)]""",
    variant_two="""def slab_index(count, size):
    \"\"\"Return the slab number of each of `count` positions.\"\"\"
    numbers = []
    slab = 0
    filled = 0
    for _position in range(count):
        if filled == size:
            slab += 1
            filled = 0
        numbers.append(slab)
        filled += 1
    return numbers""",
    variant_three="""def slab_index(count, size):
    \"\"\"Return the slab number of each of `count` positions.\"\"\"
    highest = count // size - 1
    return [min(position // size, highest) for position in range(count)]""",
    variant_four="""def slab_index(count, size):
    \"\"\"Return the slab number of each of `count` positions.\"\"\"
    if size <= 1:
        return [0] * count
    return [position // size for position in range(count)]""",
    visible_test=_test_module(
        "slab_index",
        "Published contract for numbering fixed-size slabs.",
        """
def test_whole_slabs_are_numbered_in_order() -> None:
    assert slab_index(6, 3) == [0, 0, 0, 1, 1, 1]


def test_a_single_whole_slab_is_slab_zero() -> None:
    assert slab_index(2, 2) == [0, 0]
""",
        imports="from slab_index import slab_index\n",
    ),
    hidden_test=_test_module(
        "slab_index",
        "The part of the contract the published tests do not state.",
        """
def test_whole_slabs_are_numbered_in_order() -> None:
    assert slab_index(6, 3) == [0, 0, 0, 1, 1, 1]


def test_a_slab_size_of_one_numbers_every_position() -> None:
    assert slab_index(4, 1) == [0, 1, 2, 3]


def test_a_trailing_partial_slab_gets_its_own_number() -> None:
    assert slab_index(7, 3) == [0, 0, 0, 1, 1, 1, 2]
""",
        imports="from slab_index import slab_index\n",
    ),
)

_G024 = D2TaskSpec(
    template_id="d6_transform.stencil_apply",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-stencil-apply",
    module="stencil_apply",
    module_doc="Selecting items through a stencil of keep-or-drop entries.",
    issue=(
        "stencil_apply() is documented to keep the items their stencil marks. Callers report "
        "that a stencil shorter than the items keeps the uncovered tail anyway, and that a "
        "stencil written with ones and zeroes keeps nothing at all."
    ),
    expected=(
        "stencil_apply(items, stencil) returns the items whose stencil entry is truthy. Items "
        "the stencil does not reach are not kept, and any truthy entry keeps its item, not only "
        "the value True."
    ),
    baseline_reason=(
        "it pads a short stencil with True and it compares each entry with True by identity"
    ),
    edge_cases=(
        "items the stencil does not reach are dropped",
        "any truthy entry keeps its item",
    ),
    baseline="""def stencil_apply(items, stencil):
    \"\"\"Return the items their stencil marks to keep.\"\"\"
    padded = list(stencil) + [True] * (len(items) - len(stencil))
    return [item for item, mark in zip(items, padded) if mark is True]""",
    variant_one="""def stencil_apply(items, stencil):
    \"\"\"Return the items their stencil marks to keep.\"\"\"
    return [item for item, mark in zip(items, stencil) if mark]""",
    variant_two="""def stencil_apply(items, stencil):
    \"\"\"Return the items their stencil marks to keep.\"\"\"
    kept = []
    for position, item in enumerate(items):
        if position < len(stencil) and bool(stencil[position]):
            kept.append(item)
    return kept""",
    variant_three="""def stencil_apply(items, stencil):
    \"\"\"Return the items their stencil marks to keep.\"\"\"
    return [item for item, mark in zip(items, stencil) if mark is True]""",
    variant_four="""def stencil_apply(items, stencil):
    \"\"\"Return the items their stencil marks to keep.\"\"\"
    padded = list(stencil) + [True] * (len(items) - len(stencil))
    return [item for item, mark in zip(items, padded) if mark]""",
    visible_test=_test_module(
        "stencil_apply",
        "Published contract for selecting items through a stencil.",
        """
def test_marked_items_are_kept() -> None:
    assert stencil_apply([10, 20, 30], [True, False, True]) == [10, 30]


def test_an_all_false_stencil_keeps_nothing() -> None:
    assert stencil_apply([1, 2], [False, False]) == []
""",
        imports="from stencil_apply import stencil_apply\n",
    ),
    hidden_test=_test_module(
        "stencil_apply",
        "The part of the contract the published tests do not state.",
        """
def test_marked_items_are_kept() -> None:
    assert stencil_apply([10, 20, 30], [True, False, True]) == [10, 30]


def test_items_the_stencil_does_not_reach_are_dropped() -> None:
    assert stencil_apply([10, 20, 30], [True]) == [10]


def test_any_truthy_entry_keeps_its_item() -> None:
    assert stencil_apply([10, 20, 30], [1, 0, "yes"]) == [10, 30]
""",
        imports="from stencil_apply import stencil_apply\n",
    ),
)

_G025 = D2TaskSpec(
    template_id="d6_error.embargo_guard",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-embargo-guard",
    module="embargo_guard",
    module_doc="Refusing work that is attempted before its embargo lifts.",
    issue=(
        "check_embargo() is documented to refuse work attempted before an embargo lifts. "
        "Callers report that an attempt exactly at the moment the embargo lifts is refused, and "
        "that an item with no embargo at all fails with a TypeError instead of being allowed."
    ),
    expected=(
        "check_embargo(now, embargo) raises PermissionError while now is strictly before "
        "embargo, and returns None otherwise. An embargo of None places no restriction."
    ),
    baseline_reason=(
        "it refuses on a non-strict comparison and it compares against None instead of treating "
        "a missing embargo as unrestricted"
    ),
    edge_cases=(
        "an attempt exactly when the embargo lifts is allowed",
        "a missing embargo places no restriction",
    ),
    baseline="""def check_embargo(now, embargo):
    \"\"\"Refuse work attempted before `embargo`.\"\"\"
    if now <= embargo:
        raise PermissionError("embargoed")
    return None""",
    variant_one="""def check_embargo(now, embargo):
    \"\"\"Refuse work attempted before `embargo`.\"\"\"
    if embargo is None:
        return None
    if now < embargo:
        raise PermissionError("embargoed")
    return None""",
    variant_two="""def check_embargo(now, embargo):
    \"\"\"Refuse work attempted before `embargo`.\"\"\"
    embargoed = embargo is not None and now < embargo
    if embargoed:
        raise PermissionError("embargoed")
    return None""",
    variant_three="""def check_embargo(now, embargo):
    \"\"\"Refuse work attempted before `embargo`.\"\"\"
    if now < embargo:
        raise PermissionError("embargoed")
    return None""",
    variant_four="""def check_embargo(now, embargo):
    \"\"\"Refuse work attempted before `embargo`.\"\"\"
    if embargo is None:
        return None
    if now <= embargo:
        raise PermissionError("embargoed")
    return None""",
    visible_test=_test_module(
        "embargo_guard",
        "Published contract for refusing embargoed work.",
        """
import pytest

from embargo_guard import check_embargo


def test_an_attempt_after_the_embargo_is_allowed() -> None:
    assert check_embargo(10, 5) is None


def test_an_attempt_before_the_embargo_is_refused() -> None:
    with pytest.raises(PermissionError):
        check_embargo(2, 5)
""",
    ),
    hidden_test=_test_module(
        "embargo_guard",
        "The part of the contract the published tests do not state.",
        """
import pytest

from embargo_guard import check_embargo


def test_an_attempt_after_the_embargo_is_allowed() -> None:
    assert check_embargo(10, 5) is None


def test_an_attempt_exactly_when_the_embargo_lifts_is_allowed() -> None:
    assert check_embargo(5, 5) is None


def test_a_missing_embargo_places_no_restriction() -> None:
    assert check_embargo(3, None) is None
""",
    ),
)

_G026 = D2TaskSpec(
    template_id="d6_error.escrow_release",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-escrow-release",
    module="escrow_release",
    module_doc="Releasing a held amount, once, and objecting when there is nothing to release.",
    issue=(
        "release() is documented to hand back a held amount and to object when it cannot. "
        "Callers report that releasing a key nobody holds quietly returns zero, and that "
        "releasing a hold that was already handed back returns zero as well."
    ),
    expected=(
        "release(holds, key) returns the amount held under key. An unknown key raises KeyError. "
        "A hold already released, recorded as None, raises RuntimeError."
    ),
    baseline_reason=(
        "it defaults an unknown key to zero and it turns an already-released hold into zero "
        "instead of objecting"
    ),
    edge_cases=(
        "an unknown key is refused with KeyError",
        "an already-released hold is refused with RuntimeError",
    ),
    baseline="""def release(holds, key):
    \"\"\"Return the amount held under `key`.\"\"\"
    amount = holds.get(key, 0)
    if amount is None:
        return 0
    return amount""",
    variant_one="""def release(holds, key):
    \"\"\"Return the amount held under `key`.\"\"\"
    if key not in holds:
        raise KeyError(key)
    amount = holds[key]
    if amount is None:
        raise RuntimeError("already released")
    return amount""",
    variant_two="""def release(holds, key):
    \"\"\"Return the amount held under `key`.\"\"\"
    missing = object()
    amount = holds.get(key, missing)
    if amount is missing:
        raise KeyError(key)
    if amount is None:
        raise RuntimeError("already released")
    return amount""",
    variant_three="""def release(holds, key):
    \"\"\"Return the amount held under `key`.\"\"\"
    if key not in holds:
        raise KeyError(key)
    amount = holds[key]
    if amount is None:
        return 0
    return amount""",
    variant_four="""def release(holds, key):
    \"\"\"Return the amount held under `key`.\"\"\"
    amount = holds.get(key, 0)
    if amount is None:
        raise RuntimeError("already released")
    return amount""",
    visible_test=_test_module(
        "escrow_release",
        "Published contract for releasing a held amount.",
        """
def test_a_held_amount_is_returned() -> None:
    assert release({"a": 30}, "a") == 30


def test_a_zero_hold_is_returned_as_zero() -> None:
    assert release({"b": 0}, "b") == 0
""",
        imports="from escrow_release import release\n",
    ),
    hidden_test=_test_module(
        "escrow_release",
        "The part of the contract the published tests do not state.",
        """
import pytest

from escrow_release import release


def test_a_held_amount_is_returned() -> None:
    assert release({"a": 30}, "a") == 30


def test_an_unknown_key_is_refused() -> None:
    with pytest.raises(KeyError):
        release({}, "ghost")


def test_an_already_released_hold_is_refused() -> None:
    with pytest.raises(RuntimeError):
        release({"a": None}, "a")
""",
    ),
)

_G027 = D2TaskSpec(
    template_id="d6_numeric.ratchet_value",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-ratchet-value",
    module="ratchet_value",
    module_doc="Moving a value that is only ever allowed to climb.",
    issue=(
        "ratchet() is documented to keep the higher of the value it holds and the one proposed. "
        "Callers report that the first proposal is floored at zero when it is negative, and "
        "that proposing the value it already holds raises instead of leaving it alone."
    ),
    expected=(
        "ratchet(previous, proposed) returns the greater of the two. When previous is None the "
        "proposal is taken as given, negative or not. A proposal equal to previous returns that "
        "value unchanged."
    ),
    baseline_reason=(
        "it substitutes zero for a missing previous value and it objects to an equal proposal"
    ),
    edge_cases=(
        "a first proposal is taken as given, even a negative one",
        "an equal proposal returns the value unchanged",
    ),
    baseline="""def ratchet(previous, proposed):
    \"\"\"Return the higher of the held and the proposed value.\"\"\"
    if proposed == previous:
        raise ValueError("no movement")
    return max(previous or 0, proposed)""",
    variant_one="""def ratchet(previous, proposed):
    \"\"\"Return the higher of the held and the proposed value.\"\"\"
    if previous is None:
        return proposed
    return max(previous, proposed)""",
    variant_two="""def ratchet(previous, proposed):
    \"\"\"Return the higher of the held and the proposed value.\"\"\"
    if previous is None or proposed > previous:
        return proposed
    return previous""",
    variant_three="""def ratchet(previous, proposed):
    \"\"\"Return the higher of the held and the proposed value.\"\"\"
    if proposed == previous:
        raise ValueError("no movement")
    if previous is None:
        return proposed
    return max(previous, proposed)""",
    variant_four="""def ratchet(previous, proposed):
    \"\"\"Return the higher of the held and the proposed value.\"\"\"
    return max(previous or 0, proposed)""",
    visible_test=_test_module(
        "ratchet_value",
        "Published contract for a value that only climbs.",
        """
def test_a_higher_proposal_is_taken() -> None:
    assert ratchet(5, 8) == 8


def test_a_lower_proposal_is_ignored() -> None:
    assert ratchet(9, 4) == 9
""",
        imports="from ratchet_value import ratchet\n",
    ),
    hidden_test=_test_module(
        "ratchet_value",
        "The part of the contract the published tests do not state.",
        """
def test_a_higher_proposal_is_taken() -> None:
    assert ratchet(5, 8) == 8


def test_a_first_proposal_is_taken_as_given() -> None:
    assert ratchet(None, -3) == -3


def test_an_equal_proposal_leaves_the_value_alone() -> None:
    assert ratchet(4, 4) == 4
""",
        imports="from ratchet_value import ratchet\n",
    ),
)

_G028 = D2TaskSpec(
    template_id="d6_numeric.cadence_beats",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-cadence-beats",
    module="cadence_beats",
    module_doc="Counting how many evenly spaced beats fall inside a span.",
    issue=(
        "beats_within() is documented to count the beats of a cadence that fall inside a span. "
        "Callers report that a beat landing exactly on the end of the span is not counted, and "
        "that a cadence of zero fails with a ZeroDivisionError instead of being refused."
    ),
    expected=(
        "beats_within(total, cadence) returns how many multiples of cadence, counting from one, "
        "are less than or equal to total. A cadence of zero or less raises ValueError."
    ),
    baseline_reason=(
        "it counts against one less than the total and it divides before checking the cadence"
    ),
    edge_cases=(
        "a beat landing exactly on the end of the span is counted",
        "a cadence of zero is refused with ValueError",
    ),
    baseline="""def beats_within(total, cadence):
    \"\"\"Count the beats of `cadence` that fall inside `total`.\"\"\"
    return (total - 1) // cadence""",
    variant_one="""def beats_within(total, cadence):
    \"\"\"Count the beats of `cadence` that fall inside `total`.\"\"\"
    if cadence <= 0:
        raise ValueError("cadence must be positive")
    return total // cadence""",
    variant_two="""def beats_within(total, cadence):
    \"\"\"Count the beats of `cadence` that fall inside `total`.\"\"\"
    if not cadence > 0:
        raise ValueError("cadence must be positive")
    counted = 0
    beat = cadence
    while beat <= total:
        counted += 1
        beat += cadence
    return counted""",
    variant_three="""def beats_within(total, cadence):
    \"\"\"Count the beats of `cadence` that fall inside `total`.\"\"\"
    return total // cadence""",
    variant_four="""def beats_within(total, cadence):
    \"\"\"Count the beats of `cadence` that fall inside `total`.\"\"\"
    if cadence <= 0:
        raise ValueError("cadence must be positive")
    return (total - 1) // cadence""",
    visible_test=_test_module(
        "cadence_beats",
        "Published contract for counting evenly spaced beats.",
        """
def test_beats_inside_the_span_are_counted() -> None:
    assert beats_within(10, 3) == 3


def test_a_span_shorter_than_one_beat_counts_none() -> None:
    assert beats_within(2, 5) == 0
""",
        imports="from cadence_beats import beats_within\n",
    ),
    hidden_test=_test_module(
        "cadence_beats",
        "The part of the contract the published tests do not state.",
        """
import pytest

from cadence_beats import beats_within


def test_beats_inside_the_span_are_counted() -> None:
    assert beats_within(10, 3) == 3


def test_a_beat_landing_on_the_end_is_counted() -> None:
    assert beats_within(9, 3) == 3


def test_a_cadence_of_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        beats_within(5, 0)
""",
    ),
)

_G029 = D2TaskSpec(
    template_id="d6_parsing.nesting_depth",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-nesting-depth",
    module="nesting_depth",
    module_doc="Measuring how deeply round brackets nest in a line of text.",
    issue=(
        "nesting_depth() is documented to measure how deeply round brackets nest. Callers "
        "report that a closing bracket with nothing to close is accepted rather than refused, "
        "and that brackets written inside a quoted run of text are counted as structure."
    ),
    expected=(
        "nesting_depth(text) returns the greatest depth reached by round brackets. A closing "
        "bracket with no matching opener raises ValueError. Brackets between single quotes are "
        "text, not structure."
    ),
    baseline_reason=(
        "it lets the depth fall below zero without objecting and it counts brackets inside quotes"
    ),
    edge_cases=(
        "a closing bracket with no opener is refused",
        "brackets inside quotes are not structure",
    ),
    baseline="""def nesting_depth(text):
    \"\"\"Return the greatest bracket depth reached in `text`.\"\"\"
    depth = 0
    deepest = 0
    for character in text:
        if character == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif character == ")":
            depth -= 1
    return deepest""",
    variant_one="""def nesting_depth(text):
    \"\"\"Return the greatest bracket depth reached in `text`.\"\"\"
    depth = 0
    deepest = 0
    quoted = False
    for character in text:
        if character == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif character == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif character == ")":
            if depth == 0:
                raise ValueError("unmatched closing bracket")
            depth -= 1
    return deepest""",
    variant_two="""def nesting_depth(text):
    \"\"\"Return the greatest bracket depth reached in `text`.\"\"\"
    structural = []
    quoted = False
    for character in text:
        if character == "'":
            quoted = not quoted
            continue
        if not quoted and character in "()":
            structural.append(character)
    depth = 0
    deepest = 0
    for character in structural:
        if character == "(":
            depth += 1
            deepest = max(deepest, depth)
        else:
            if not depth:
                raise ValueError("unmatched closing bracket")
            depth -= 1
    return deepest""",
    variant_three="""def nesting_depth(text):
    \"\"\"Return the greatest bracket depth reached in `text`.\"\"\"
    depth = 0
    deepest = 0
    for character in text:
        if character == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif character == ")":
            if depth == 0:
                raise ValueError("unmatched closing bracket")
            depth -= 1
    return deepest""",
    variant_four="""def nesting_depth(text):
    \"\"\"Return the greatest bracket depth reached in `text`.\"\"\"
    depth = 0
    deepest = 0
    quoted = False
    for character in text:
        if character == "'":
            quoted = not quoted
        elif quoted:
            continue
        elif character == "(":
            depth += 1
            deepest = max(deepest, depth)
        elif character == ")":
            depth -= 1
    return deepest""",
    visible_test=_test_module(
        "nesting_depth",
        "Published contract for measuring bracket nesting.",
        """
def test_nested_brackets_reach_their_depth() -> None:
    assert nesting_depth("a(b(c)d)e") == 2


def test_text_without_brackets_has_no_depth() -> None:
    assert nesting_depth("plain") == 0
""",
        imports="from nesting_depth import nesting_depth\n",
    ),
    hidden_test=_test_module(
        "nesting_depth",
        "The part of the contract the published tests do not state.",
        """
import pytest

from nesting_depth import nesting_depth


def test_nested_brackets_reach_their_depth() -> None:
    assert nesting_depth("a(b(c)d)e") == 2


def test_a_closing_bracket_with_no_opener_is_refused() -> None:
    with pytest.raises(ValueError):
        nesting_depth("a)b")


def test_brackets_inside_quotes_are_not_structure() -> None:
    assert nesting_depth("a('(((')b") == 1
""",
    ),
)

_G030 = D2TaskSpec(
    template_id="d6_state.watermark_state",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-watermark-state",
    module="watermark_state",
    module_doc="Keeping the high-water mark of the offsets a reader has processed.",
    issue=(
        "advance() is documented to keep the highest offset a reader has processed. Callers "
        "report that a first offset of zero is not counted as processed, and that replaying an "
        "older offset drags the mark backwards."
    ),
    expected=(
        "advance(state, offset) returns the state with mark set to the highest offset seen and "
        "applied counting the offsets that advanced it. A reader that has seen nothing has no "
        "mark, so a first offset of zero advances it. An offset at or below the mark changes "
        "nothing."
    ),
    baseline_reason=(
        "it treats a missing mark as zero and it assigns the offset to the mark whether or not "
        "the offset advanced it"
    ),
    edge_cases=(
        "a first offset of zero advances the mark",
        "replaying an older offset does not drag the mark back",
    ),
    baseline="""def advance(state, offset):
    \"\"\"Record `offset` against the high-water mark in `state`.\"\"\"
    mark = state.get("mark", 0)
    applied = state.get("applied", 0)
    if offset > mark:
        applied += 1
    return {"mark": offset, "applied": applied}""",
    variant_one="""def advance(state, offset):
    \"\"\"Record `offset` against the high-water mark in `state`.\"\"\"
    mark = state.get("mark")
    applied = state.get("applied", 0)
    if mark is None or offset > mark:
        return {"mark": offset, "applied": applied + 1}
    return {"mark": mark, "applied": applied}""",
    variant_two="""def advance(state, offset):
    \"\"\"Record `offset` against the high-water mark in `state`.\"\"\"
    applied = state.get("applied", 0)
    if "mark" not in state:
        return {"mark": offset, "applied": applied + 1}
    mark = state["mark"]
    advanced = offset > mark
    return {"mark": max(mark, offset), "applied": applied + (1 if advanced else 0)}""",
    variant_three="""def advance(state, offset):
    \"\"\"Record `offset` against the high-water mark in `state`.\"\"\"
    mark = state.get("mark")
    applied = state.get("applied", 0)
    if mark is None or offset > mark:
        applied += 1
    return {"mark": offset, "applied": applied}""",
    variant_four="""def advance(state, offset):
    \"\"\"Record `offset` against the high-water mark in `state`.\"\"\"
    mark = state.get("mark", 0)
    applied = state.get("applied", 0)
    if offset > mark:
        return {"mark": offset, "applied": applied + 1}
    return {"mark": mark, "applied": applied}""",
    visible_test=_test_module(
        "watermark_state",
        "Published contract for a reader's high-water mark.",
        """
def test_a_first_offset_advances_the_mark() -> None:
    assert advance({}, 5) == {"mark": 5, "applied": 1}


def test_a_higher_offset_advances_the_mark() -> None:
    assert advance({"mark": 5, "applied": 1}, 9) == {"mark": 9, "applied": 2}
""",
        imports="from watermark_state import advance\n",
    ),
    hidden_test=_test_module(
        "watermark_state",
        "The part of the contract the published tests do not state.",
        """
def test_a_first_offset_advances_the_mark() -> None:
    assert advance({}, 5) == {"mark": 5, "applied": 1}


def test_a_first_offset_of_zero_advances_the_mark() -> None:
    assert advance({}, 0) == {"mark": 0, "applied": 1}


def test_replaying_an_older_offset_does_not_drag_the_mark_back() -> None:
    assert advance({"mark": 7, "applied": 1}, 3) == {"mark": 7, "applied": 1}
""",
        imports="from watermark_state import advance\n",
    ),
)

_G032 = D2TaskSpec(
    template_id="d6_parsing.gutter_split",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-gutter-split",
    module="gutter_split",
    module_doc="Splitting a column-aligned line where the gutters between fields fall.",
    issue=(
        "gutter_split() is documented to break a line at the gutters between its columns. "
        "Callers report that a field containing a single space is torn in two, and that a line "
        "of nothing but spaces comes back as one empty field instead of no fields at all."
    ),
    expected=(
        "gutter_split(line) returns the fields of a column-aligned line, splitting only where "
        "two or more spaces fall together. A single space belongs to its field. A line holding "
        "nothing but whitespace has no fields."
    ),
    baseline_reason=(
        "it splits on any run of whitespace and it returns the empty string as a field"
    ),
    edge_cases=(
        "a single space belongs to its field",
        "a line of only whitespace has no fields",
    ),
    baseline="""import re


def gutter_split(line):
    \"\"\"Return the fields of a column-aligned line.\"\"\"
    return re.split(r"\\s+", line.strip())""",
    variant_one="""import re


def gutter_split(line):
    \"\"\"Return the fields of a column-aligned line.\"\"\"
    trimmed = line.strip()
    if not trimmed:
        return []
    return re.split(r"\\s{2,}", trimmed)""",
    variant_two="""def gutter_split(line):
    \"\"\"Return the fields of a column-aligned line.\"\"\"
    trimmed = line.strip()
    if not trimmed:
        return []
    fields = []
    current = ""
    gap = 0
    for character in trimmed:
        if character == " ":
            gap += 1
            continue
        if gap >= 2:
            fields.append(current)
            current = ""
        elif gap == 1:
            current += " "
        gap = 0
        current += character
    fields.append(current)
    return fields""",
    variant_three="""import re


def gutter_split(line):
    \"\"\"Return the fields of a column-aligned line.\"\"\"
    return re.split(r"\\s{2,}", line.strip())""",
    variant_four="""import re


def gutter_split(line):
    \"\"\"Return the fields of a column-aligned line.\"\"\"
    trimmed = line.strip()
    if not trimmed:
        return []
    return re.split(r"\\s+", trimmed)""",
    visible_test=_test_module(
        "gutter_split",
        "Published contract for splitting a column-aligned line.",
        """
def test_a_gutter_separates_two_fields() -> None:
    assert gutter_split("name  age") == ["name", "age"]


def test_surrounding_space_is_dropped() -> None:
    assert gutter_split("  left   right  ") == ["left", "right"]
""",
        imports="from gutter_split import gutter_split\n",
    ),
    hidden_test=_test_module(
        "gutter_split",
        "The part of the contract the published tests do not state.",
        """
def test_a_gutter_separates_two_fields() -> None:
    assert gutter_split("name  age") == ["name", "age"]


def test_a_single_space_belongs_to_its_field() -> None:
    assert gutter_split("full name  age") == ["full name", "age"]


def test_a_line_of_only_whitespace_has_no_fields() -> None:
    assert gutter_split("   ") == []
""",
        imports="from gutter_split import gutter_split\n",
    ),
)

_G033 = D2TaskSpec(
    template_id="d6_parsing.chord_notes",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-chord-notes",
    module="chord_notes",
    module_doc="Reading the root and the quality out of a chord symbol.",
    issue=(
        "read_chord() is documented to split a chord symbol into its root and its quality. "
        "Callers report that a sharpened or flattened root loses its accidental to the quality, "
        "and that a bare root comes back with an empty quality instead of the major it means."
    ),
    expected=(
        "read_chord(symbol) returns (root, quality). The root is the letter A to G together "
        "with a following sharp or flat when one is written. A symbol with no quality after the "
        "root is major. A symbol whose first character is not a letter A to G raises ValueError."
    ),
    baseline_reason=(
        "it takes only the first character as the root and it passes an empty quality through"
    ),
    edge_cases=(
        "an accidental belongs to the root",
        "a bare root is major",
    ),
    baseline="""def read_chord(symbol):
    \"\"\"Return the (root, quality) of a chord symbol.\"\"\"
    if not symbol or symbol[0] not in "ABCDEFG":
        raise ValueError("unknown root")
    return symbol[0], symbol[1:]""",
    variant_one="""def read_chord(symbol):
    \"\"\"Return the (root, quality) of a chord symbol.\"\"\"
    if not symbol or symbol[0] not in "ABCDEFG":
        raise ValueError("unknown root")
    length = 2 if symbol[1:2] in ("#", "b") else 1
    quality = symbol[length:]
    return symbol[:length], quality or "maj\"""",
    variant_two="""def read_chord(symbol):
    \"\"\"Return the (root, quality) of a chord symbol.\"\"\"
    if not symbol or symbol[0] not in "ABCDEFG":
        raise ValueError("unknown root")
    root = symbol[0]
    rest = symbol[1:]
    if rest[:1] in ("#", "b"):
        root += rest[0]
        rest = rest[1:]
    if not rest:
        rest = "maj"
    return root, rest""",
    variant_three="""def read_chord(symbol):
    \"\"\"Return the (root, quality) of a chord symbol.\"\"\"
    if not symbol or symbol[0] not in "ABCDEFG":
        raise ValueError("unknown root")
    length = 2 if symbol[1:2] in ("#", "b") else 1
    return symbol[:length], symbol[length:]""",
    variant_four="""def read_chord(symbol):
    \"\"\"Return the (root, quality) of a chord symbol.\"\"\"
    if not symbol or symbol[0] not in "ABCDEFG":
        raise ValueError("unknown root")
    return symbol[0], symbol[1:] or "maj\"""",
    visible_test=_test_module(
        "chord_notes",
        "Published contract for reading a chord symbol.",
        """
import pytest

from chord_notes import read_chord


def test_a_root_and_quality_are_split() -> None:
    assert read_chord("Cm7") == ("C", "m7")


def test_a_symbol_with_no_root_letter_is_refused() -> None:
    with pytest.raises(ValueError):
        read_chord("H")
""",
    ),
    hidden_test=_test_module(
        "chord_notes",
        "The part of the contract the published tests do not state.",
        """
import pytest

from chord_notes import read_chord


def test_a_root_and_quality_are_split() -> None:
    assert read_chord("Cm7") == ("C", "m7")


def test_an_accidental_belongs_to_the_root() -> None:
    assert read_chord("F#m") == ("F#", "m")


def test_a_bare_root_is_major() -> None:
    assert read_chord("G") == ("G", "maj")
""",
    ),
)

_G034 = D2TaskSpec(
    template_id="d6_numeric.tier_labels",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-tier-labels",
    module="tier_labels",
    module_doc="Placing readings into tiers named by their upper bounds.",
    issue=(
        "tier_labels() is documented to place each reading in the first tier whose bound it "
        "does not exceed. Callers report that a reading sitting exactly on a bound is pushed "
        "into the next tier, and that bounds handed over out of order tier everything wrongly."
    ),
    expected=(
        "tier_labels(values, bounds) returns the tier of each value: the position of the first "
        "bound the value does not exceed, counting the bounds in ascending order, or the count "
        "of bounds when the value exceeds them all. The bounds are inclusive upper limits."
    ),
    baseline_reason=(
        "it compares each bound with a strict less-than and it reads the bounds in the order "
        "they arrive"
    ),
    edge_cases=(
        "a reading exactly on a bound stays in that tier",
        "bounds handed over out of order are sorted first",
    ),
    baseline="""def tier_labels(values, bounds):
    \"\"\"Return the tier of each value against `bounds`.\"\"\"
    tiers = []
    for value in values:
        placed = len(bounds)
        for position, bound in enumerate(bounds):
            if value < bound:
                placed = position
                break
        tiers.append(placed)
    return tiers""",
    variant_one="""def tier_labels(values, bounds):
    \"\"\"Return the tier of each value against `bounds`.\"\"\"
    ordered = sorted(bounds)
    tiers = []
    for value in values:
        placed = len(ordered)
        for position, bound in enumerate(ordered):
            if value <= bound:
                placed = position
                break
        tiers.append(placed)
    return tiers""",
    variant_two="""def tier_labels(values, bounds):
    \"\"\"Return the tier of each value against `bounds`.\"\"\"
    ordered = sorted(bounds)
    return [sum(1 for bound in ordered if value > bound) for value in values]""",
    variant_three="""def tier_labels(values, bounds):
    \"\"\"Return the tier of each value against `bounds`.\"\"\"
    tiers = []
    for value in values:
        placed = len(bounds)
        for position, bound in enumerate(bounds):
            if value <= bound:
                placed = position
                break
        tiers.append(placed)
    return tiers""",
    variant_four="""def tier_labels(values, bounds):
    \"\"\"Return the tier of each value against `bounds`.\"\"\"
    ordered = sorted(bounds)
    tiers = []
    for value in values:
        placed = len(ordered)
        for position, bound in enumerate(ordered):
            if value < bound:
                placed = position
                break
        tiers.append(placed)
    return tiers""",
    visible_test=_test_module(
        "tier_labels",
        "Published contract for tiering readings against bounds.",
        """
def test_readings_land_in_ascending_tiers() -> None:
    assert tier_labels([1, 5, 9], [3, 7]) == [0, 1, 2]


def test_a_reading_below_every_bound_is_the_first_tier() -> None:
    assert tier_labels([0], [3, 7]) == [0]
""",
        imports="from tier_labels import tier_labels\n",
    ),
    hidden_test=_test_module(
        "tier_labels",
        "The part of the contract the published tests do not state.",
        """
def test_readings_land_in_ascending_tiers() -> None:
    assert tier_labels([1, 5, 9], [3, 7]) == [0, 1, 2]


def test_a_reading_exactly_on_a_bound_stays_in_that_tier() -> None:
    assert tier_labels([3, 7], [3, 7]) == [0, 1]


def test_bounds_out_of_order_are_sorted_first() -> None:
    assert tier_labels([5], [7, 3]) == [1]
""",
        imports="from tier_labels import tier_labels\n",
    ),
)

_G035 = D2TaskSpec(
    template_id="d6_state.vestibule_queue",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-vestibule-queue",
    module="vestibule_queue",
    module_doc="Admitting arrivals to a room and holding the rest in the vestibule.",
    issue=(
        "admit() is documented to let an arrival in while there is room and to hold it in the "
        "vestibule otherwise, never listing anyone twice. Callers report that someone already "
        "waiting is queued a second time, and that a name differing only in case is treated as "
        "a stranger."
    ),
    expected=(
        "admit(state, name) returns the state with the arrival inside when the room is below "
        "capacity and in waiting otherwise. Someone already inside or already waiting is left "
        "where they are, and names are matched without regard to case."
    ),
    baseline_reason=(
        "it looks for the arrival only among those inside, and it compares names exactly"
    ),
    edge_cases=(
        "someone already waiting is not queued again",
        "names are matched without regard to case",
    ),
    baseline="""def admit(state, name):
    \"\"\"Admit `name` to the room, or hold it in the vestibule.\"\"\"
    inside = list(state.get("inside", []))
    waiting = list(state.get("waiting", []))
    capacity = state.get("capacity", 0)
    if name in inside:
        return {"capacity": capacity, "inside": inside, "waiting": waiting}
    if len(inside) < capacity:
        inside.append(name)
    else:
        waiting.append(name)
    return {"capacity": capacity, "inside": inside, "waiting": waiting}""",
    variant_one="""def admit(state, name):
    \"\"\"Admit `name` to the room, or hold it in the vestibule.\"\"\"
    inside = list(state.get("inside", []))
    waiting = list(state.get("waiting", []))
    capacity = state.get("capacity", 0)
    known = {person.lower() for person in inside + waiting}
    if name.lower() in known:
        return {"capacity": capacity, "inside": inside, "waiting": waiting}
    if len(inside) < capacity:
        inside.append(name)
    else:
        waiting.append(name)
    return {"capacity": capacity, "inside": inside, "waiting": waiting}""",
    variant_two="""def admit(state, name):
    \"\"\"Admit `name` to the room, or hold it in the vestibule.\"\"\"
    inside = list(state.get("inside", []))
    waiting = list(state.get("waiting", []))
    capacity = state.get("capacity", 0)
    result = {"capacity": capacity, "inside": inside, "waiting": waiting}
    for person in inside + waiting:
        if person.lower() == name.lower():
            return result
    target = "inside" if len(inside) < capacity else "waiting"
    result[target] = [*result[target], name]
    return result""",
    variant_three="""def admit(state, name):
    \"\"\"Admit `name` to the room, or hold it in the vestibule.\"\"\"
    inside = list(state.get("inside", []))
    waiting = list(state.get("waiting", []))
    capacity = state.get("capacity", 0)
    if name in inside or name in waiting:
        return {"capacity": capacity, "inside": inside, "waiting": waiting}
    if len(inside) < capacity:
        inside.append(name)
    else:
        waiting.append(name)
    return {"capacity": capacity, "inside": inside, "waiting": waiting}""",
    variant_four="""def admit(state, name):
    \"\"\"Admit `name` to the room, or hold it in the vestibule.\"\"\"
    inside = list(state.get("inside", []))
    waiting = list(state.get("waiting", []))
    capacity = state.get("capacity", 0)
    if name.lower() in {person.lower() for person in inside}:
        return {"capacity": capacity, "inside": inside, "waiting": waiting}
    if len(inside) < capacity:
        inside.append(name)
    else:
        waiting.append(name)
    return {"capacity": capacity, "inside": inside, "waiting": waiting}""",
    visible_test=_test_module(
        "vestibule_queue",
        "Published contract for admitting arrivals to a room.",
        """
def test_an_arrival_enters_a_room_with_space() -> None:
    state = {"capacity": 2, "inside": [], "waiting": []}
    assert admit(state, "ann")["inside"] == ["ann"]


def test_an_arrival_waits_when_the_room_is_full() -> None:
    state = {"capacity": 1, "inside": ["ann"], "waiting": []}
    assert admit(state, "bob")["waiting"] == ["bob"]
""",
        imports="from vestibule_queue import admit\n",
    ),
    hidden_test=_test_module(
        "vestibule_queue",
        "The part of the contract the published tests do not state.",
        """
def test_an_arrival_enters_a_room_with_space() -> None:
    state = {"capacity": 2, "inside": [], "waiting": []}
    assert admit(state, "ann")["inside"] == ["ann"]


def test_someone_already_waiting_is_not_queued_again() -> None:
    state = {"capacity": 0, "inside": [], "waiting": ["bob"]}
    assert admit(state, "bob")["waiting"] == ["bob"]


def test_names_are_matched_without_regard_to_case() -> None:
    state = {"capacity": 1, "inside": ["ann"], "waiting": []}
    assert admit(state, "ANN")["waiting"] == []
""",
        imports="from vestibule_queue import admit\n",
    ),
)

_G036 = D2TaskSpec(
    template_id="d6_boundary.rungs_between",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-rungs-between",
    module="rungs_between",
    module_doc="Placing evenly spaced rungs from one bound to another.",
    issue=(
        "rungs_between() is documented to place a given number of evenly spaced rungs from a "
        "low bound to a high one. Callers report that asking for a single rung fails with a "
        "ZeroDivisionError, and that a high bound below the low one produces a descending "
        "ladder instead of being refused."
    ),
    expected=(
        "rungs_between(low, high, count) returns count values from low to high inclusive, "
        "evenly spaced. A count of one returns just the low bound, and a count of zero returns "
        "nothing. A high bound below the low one raises ValueError."
    ),
    baseline_reason=(
        "it divides by one less than the count without guarding a count of one, and it never "
        "checks that the bounds ascend"
    ),
    edge_cases=(
        "a count of one returns just the low bound",
        "a high bound below the low one is refused",
    ),
    baseline="""def rungs_between(low, high, count):
    \"\"\"Return `count` evenly spaced rungs from `low` to `high`.\"\"\"
    if count <= 0:
        return []
    step = (high - low) // (count - 1)
    return [low + step * position for position in range(count)]""",
    variant_one="""def rungs_between(low, high, count):
    \"\"\"Return `count` evenly spaced rungs from `low` to `high`.\"\"\"
    if high < low:
        raise ValueError("the high bound is below the low one")
    if count <= 0:
        return []
    if count == 1:
        return [low]
    step = (high - low) // (count - 1)
    return [low + step * position for position in range(count)]""",
    variant_two="""def rungs_between(low, high, count):
    \"\"\"Return `count` evenly spaced rungs from `low` to `high`.\"\"\"
    if not high >= low:
        raise ValueError("the high bound is below the low one")
    rungs = []
    for position in range(count):
        gaps = count - 1
        offset = 0 if gaps == 0 else (high - low) * position // gaps
        rungs.append(low + offset)
    return rungs""",
    variant_three="""def rungs_between(low, high, count):
    \"\"\"Return `count` evenly spaced rungs from `low` to `high`.\"\"\"
    if count <= 0:
        return []
    if count == 1:
        return [low]
    step = (high - low) // (count - 1)
    return [low + step * position for position in range(count)]""",
    variant_four="""def rungs_between(low, high, count):
    \"\"\"Return `count` evenly spaced rungs from `low` to `high`.\"\"\"
    if high < low:
        raise ValueError("the high bound is below the low one")
    if count <= 0:
        return []
    step = (high - low) // (count - 1)
    return [low + step * position for position in range(count)]""",
    visible_test=_test_module(
        "rungs_between",
        "Published contract for placing evenly spaced rungs.",
        """
def test_rungs_span_the_bounds() -> None:
    assert rungs_between(0, 10, 6) == [0, 2, 4, 6, 8, 10]


def test_no_rungs_are_placed_for_a_count_of_zero() -> None:
    assert rungs_between(0, 10, 0) == []
""",
        imports="from rungs_between import rungs_between\n",
    ),
    hidden_test=_test_module(
        "rungs_between",
        "The part of the contract the published tests do not state.",
        """
import pytest

from rungs_between import rungs_between


def test_rungs_span_the_bounds() -> None:
    assert rungs_between(0, 10, 6) == [0, 2, 4, 6, 8, 10]


def test_a_count_of_one_returns_the_low_bound() -> None:
    assert rungs_between(4, 4, 1) == [4]


def test_a_high_bound_below_the_low_one_is_refused() -> None:
    with pytest.raises(ValueError):
        rungs_between(9, 3, 3)
""",
    ),
)

_G037 = D2TaskSpec(
    template_id="d6_boundary.ballast_trim",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-ballast-trim",
    module="ballast_trim",
    module_doc="Keeping the leading run of a load that a budget can carry.",
    issue=(
        "ballast_trim() is documented to keep the longest leading run of a load whose total "
        "fits a budget. Callers report that a run totalling exactly the budget is cut short, "
        "and that a negative entry is left out of the running total altogether."
    ),
    expected=(
        "ballast_trim(values, budget) returns the longest leading run of values whose running "
        "total stays at or below budget. Every value counts toward that total, negative ones "
        "included."
    ),
    baseline_reason=(
        "it compares the running total with a strict less-than and it adds only positive values "
        "to it"
    ),
    edge_cases=(
        "a run totalling exactly the budget is kept whole",
        "a negative value counts toward the running total",
    ),
    baseline="""def ballast_trim(values, budget):
    \"\"\"Return the longest leading run that fits `budget`.\"\"\"
    kept = []
    total = 0
    for value in values:
        candidate = total + value if value > 0 else total
        if not candidate < budget:
            break
        total = candidate
        kept.append(value)
    return kept""",
    variant_one="""def ballast_trim(values, budget):
    \"\"\"Return the longest leading run that fits `budget`.\"\"\"
    kept = []
    total = 0
    for value in values:
        if total + value > budget:
            break
        total += value
        kept.append(value)
    return kept""",
    variant_two="""def ballast_trim(values, budget):
    \"\"\"Return the longest leading run that fits `budget`.\"\"\"
    total = 0
    length = 0
    for value in values:
        total += value
        if total > budget:
            break
        length += 1
    return list(values[:length])""",
    variant_three="""def ballast_trim(values, budget):
    \"\"\"Return the longest leading run that fits `budget`.\"\"\"
    kept = []
    total = 0
    for value in values:
        candidate = total + value if value > 0 else total
        if candidate > budget:
            break
        total = candidate
        kept.append(value)
    return kept""",
    variant_four="""def ballast_trim(values, budget):
    \"\"\"Return the longest leading run that fits `budget`.\"\"\"
    kept = []
    total = 0
    for value in values:
        candidate = total + value
        if not candidate < budget:
            break
        total = candidate
        kept.append(value)
    return kept""",
    visible_test=_test_module(
        "ballast_trim",
        "Published contract for trimming a load to a budget.",
        """
def test_the_leading_run_that_fits_is_kept() -> None:
    assert ballast_trim([2, 3, 9], 6) == [2, 3]


def test_a_first_value_over_the_budget_keeps_nothing() -> None:
    assert ballast_trim([9, 1], 6) == []
""",
        imports="from ballast_trim import ballast_trim\n",
    ),
    hidden_test=_test_module(
        "ballast_trim",
        "The part of the contract the published tests do not state.",
        """
def test_the_leading_run_that_fits_is_kept() -> None:
    assert ballast_trim([2, 3, 9], 6) == [2, 3]


def test_a_run_totalling_exactly_the_budget_is_kept_whole() -> None:
    assert ballast_trim([2, 4, 1], 6) == [2, 4]


def test_a_negative_value_counts_toward_the_total() -> None:
    assert ballast_trim([4, -3, 4], 6) == [4, -3, 4]
""",
        imports="from ballast_trim import ballast_trim\n",
    ),
)

_G038 = D2TaskSpec(
    template_id="d6_transform.harmonise_units",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-harmonise-units",
    module="harmonise_units",
    module_doc="Bringing a set of length readings onto one common unit.",
    issue=(
        "harmonise() is documented to bring every reading onto millimetres. Callers report that "
        "a reading carrying a unit nobody recognises passes through untouched, and that a "
        "reading with no unit at all fails with a KeyError instead of being read as millimetres."
    ),
    expected=(
        "harmonise(readings) returns each reading's value in millimetres, where a metre is a "
        "thousand and a centimetre is ten. A reading with no unit is already in millimetres. A "
        "unit outside metres, centimetres and millimetres raises ValueError."
    ),
    baseline_reason=(
        "it falls back to a factor of one for an unknown unit and it reads the unit key directly"
    ),
    edge_cases=(
        "an unrecognised unit is refused",
        "a reading with no unit is already in millimetres",
    ),
    baseline="""FACTORS = {"m": 1000, "cm": 10, "mm": 1}


def harmonise(readings):
    \"\"\"Return every reading in millimetres.\"\"\"
    return [reading["value"] * FACTORS.get(reading["unit"], 1) for reading in readings]""",
    variant_one="""FACTORS = {"m": 1000, "cm": 10, "mm": 1}


def harmonise(readings):
    \"\"\"Return every reading in millimetres.\"\"\"
    harmonised = []
    for reading in readings:
        unit = reading.get("unit", "mm")
        if unit not in FACTORS:
            raise ValueError(unit)
        harmonised.append(reading["value"] * FACTORS[unit])
    return harmonised""",
    variant_two="""FACTORS = {"m": 1000, "cm": 10, "mm": 1}


def _factor(unit):
    try:
        return FACTORS[unit]
    except KeyError:
        raise ValueError(unit) from None


def harmonise(readings):
    \"\"\"Return every reading in millimetres.\"\"\"
    return [
        reading["value"] * _factor(reading.get("unit", "mm")) for reading in readings
    ]""",
    variant_three="""FACTORS = {"m": 1000, "cm": 10, "mm": 1}


def harmonise(readings):
    \"\"\"Return every reading in millimetres.\"\"\"
    harmonised = []
    for reading in readings:
        unit = reading["unit"]
        if unit not in FACTORS:
            raise ValueError(unit)
        harmonised.append(reading["value"] * FACTORS[unit])
    return harmonised""",
    variant_four="""FACTORS = {"m": 1000, "cm": 10, "mm": 1}


def harmonise(readings):
    \"\"\"Return every reading in millimetres.\"\"\"
    return [
        reading["value"] * FACTORS.get(reading.get("unit", "mm"), 1)
        for reading in readings
    ]""",
    visible_test=_test_module(
        "harmonise_units",
        "Published contract for bringing readings onto one unit.",
        """
def test_readings_are_brought_onto_millimetres() -> None:
    readings = [{"value": 2, "unit": "m"}, {"value": 5, "unit": "cm"}]
    assert harmonise(readings) == [2000, 50]


def test_millimetres_pass_through_unchanged() -> None:
    assert harmonise([{"value": 7, "unit": "mm"}]) == [7]
""",
        imports="from harmonise_units import harmonise\n",
    ),
    hidden_test=_test_module(
        "harmonise_units",
        "The part of the contract the published tests do not state.",
        """
import pytest

from harmonise_units import harmonise


def test_readings_are_brought_onto_millimetres() -> None:
    readings = [{"value": 2, "unit": "m"}, {"value": 5, "unit": "cm"}]
    assert harmonise(readings) == [2000, 50]


def test_an_unrecognised_unit_is_refused() -> None:
    with pytest.raises(ValueError):
        harmonise([{"value": 1, "unit": "furlong"}])


def test_a_reading_with_no_unit_is_millimetres() -> None:
    assert harmonise([{"value": 7}]) == [7]
""",
    ),
)

_G040 = D2TaskSpec(
    template_id="d6_numeric.waypoint_legs",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-waypoint-legs",
    module="waypoint_legs",
    module_doc="Measuring the legs between consecutive waypoints along a line.",
    issue=(
        "waypoint_legs() is documented to measure each leg between consecutive waypoints. "
        "Callers report that two waypoints at the same place produce no leg at all instead of "
        "one of length zero, and that walking backwards produces a negative leg."
    ),
    expected=(
        "waypoint_legs(points) returns one leg per consecutive pair, each the distance between "
        "them and never negative. A pair at the same place is a leg of zero. Fewer than two "
        "waypoints make no legs."
    ),
    baseline_reason=("it drops a pair that does not move and it returns the signed difference"),
    edge_cases=(
        "a pair at the same place is a leg of zero",
        "walking backwards gives a positive leg",
    ),
    baseline="""def waypoint_legs(points):
    \"\"\"Return the leg between each consecutive pair of waypoints.\"\"\"
    legs = []
    for position in range(1, len(points)):
        step = points[position] - points[position - 1]
        if step:
            legs.append(step)
    return legs""",
    variant_one="""def waypoint_legs(points):
    \"\"\"Return the leg between each consecutive pair of waypoints.\"\"\"
    return [
        abs(points[position] - points[position - 1])
        for position in range(1, len(points))
    ]""",
    variant_two="""def waypoint_legs(points):
    \"\"\"Return the leg between each consecutive pair of waypoints.\"\"\"
    legs = []
    previous = None
    for point in points:
        if previous is not None:
            step = point - previous
            legs.append(step if step >= 0 else -step)
        previous = point
    return legs""",
    variant_three="""def waypoint_legs(points):
    \"\"\"Return the leg between each consecutive pair of waypoints.\"\"\"
    legs = []
    for position in range(1, len(points)):
        legs.append(points[position] - points[position - 1])
    return legs""",
    variant_four="""def waypoint_legs(points):
    \"\"\"Return the leg between each consecutive pair of waypoints.\"\"\"
    legs = []
    for position in range(1, len(points)):
        step = abs(points[position] - points[position - 1])
        if step:
            legs.append(step)
    return legs""",
    visible_test=_test_module(
        "waypoint_legs",
        "Published contract for measuring legs between waypoints.",
        """
def test_each_consecutive_pair_makes_a_leg() -> None:
    assert waypoint_legs([0, 3, 7]) == [3, 4]


def test_a_single_waypoint_makes_no_legs() -> None:
    assert waypoint_legs([4]) == []
""",
        imports="from waypoint_legs import waypoint_legs\n",
    ),
    hidden_test=_test_module(
        "waypoint_legs",
        "The part of the contract the published tests do not state.",
        """
def test_each_consecutive_pair_makes_a_leg() -> None:
    assert waypoint_legs([0, 3, 7]) == [3, 4]


def test_a_pair_at_the_same_place_is_a_leg_of_zero() -> None:
    assert waypoint_legs([2, 2, 5]) == [0, 3]


def test_walking_backwards_gives_a_positive_leg() -> None:
    assert waypoint_legs([9, 4]) == [5]
""",
        imports="from waypoint_legs import waypoint_legs\n",
    ),
)

D6_CERTIFICATION_SPECS: tuple[D2TaskSpec, ...] = (
    _G001,
    _G002,
    _G003,
    _G004,
    _G005,
    _G006,
    _G007,
    _G008,
    _G009,
    _G010,
    _G011,
    _G012,
    _G015,
    _G018,
    _G020,
    _G021,
    _G022,
    _G023,
    _G024,
    _G025,
    _G026,
    _G027,
    _G028,
    _G029,
    _G030,
    _G032,
    _G033,
    _G034,
    _G035,
    _G036,
    _G037,
    _G038,
    _G040,
)
