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

_G041 = D2TaskSpec(
    template_id="d6_transform.crosswalk_codes",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-crosswalk-codes",
    module="crosswalk_codes",
    module_doc="Translating codes through a crosswalk and reporting the ones it cannot.",
    issue=(
        "crosswalk() is documented to translate each row's code and to report the codes it does "
        "not know. Callers report that a code the crosswalk does not carry is blanked out of the "
        "row, and that the report lists the same unknown code once for every row that used it."
    ),
    expected=(
        "crosswalk(rows, mapping) returns the rows with each known code replaced by its "
        "translation, leaving an unknown code exactly as it was, together with the distinct "
        "unknown codes in sorted order."
    ),
    baseline_reason=(
        "it looks the code up with a default of None and it collects the unknown codes without "
        "removing repeats or sorting them"
    ),
    edge_cases=(
        "an unknown code is left in the row as it was",
        "the report names each unknown code once, in order",
    ),
    baseline="""def crosswalk(rows, mapping):
    \"\"\"Translate each row's code and report the ones the crosswalk lacks.\"\"\"
    translated = []
    unknown = []
    for row in rows:
        code = row["code"]
        if code not in mapping:
            unknown.append(code)
        translated.append({**row, "code": mapping.get(code)})
    return translated, unknown""",
    variant_one="""def crosswalk(rows, mapping):
    \"\"\"Translate each row's code and report the ones the crosswalk lacks.\"\"\"
    translated = []
    unknown = set()
    for row in rows:
        code = row["code"]
        if code in mapping:
            translated.append({**row, "code": mapping[code]})
        else:
            unknown.add(code)
            translated.append({**row, "code": code})
    return translated, sorted(unknown)""",
    variant_two="""def crosswalk(rows, mapping):
    \"\"\"Translate each row's code and report the ones the crosswalk lacks.\"\"\"
    translated = [{**row, "code": mapping.get(row["code"], row["code"])} for row in rows]
    unknown = []
    for row in rows:
        code = row["code"]
        if code not in mapping and code not in unknown:
            unknown.append(code)
    unknown.sort()
    return translated, unknown""",
    variant_three="""def crosswalk(rows, mapping):
    \"\"\"Translate each row's code and report the ones the crosswalk lacks.\"\"\"
    translated = []
    unknown = []
    for row in rows:
        code = row["code"]
        if code not in mapping:
            unknown.append(code)
        translated.append({**row, "code": mapping.get(code, code)})
    return translated, unknown""",
    variant_four="""def crosswalk(rows, mapping):
    \"\"\"Translate each row's code and report the ones the crosswalk lacks.\"\"\"
    translated = []
    unknown = set()
    for row in rows:
        code = row["code"]
        if code not in mapping:
            unknown.add(code)
        translated.append({**row, "code": mapping.get(code)})
    return translated, sorted(unknown)""",
    visible_test=_test_module(
        "crosswalk_codes",
        "Published contract for translating codes through a crosswalk.",
        """
def test_known_codes_are_translated() -> None:
    rows = [{"code": "a"}, {"code": "b"}]
    assert crosswalk(rows, {"a": "A", "b": "B"})[0] == [{"code": "A"}, {"code": "B"}]


def test_a_crosswalk_that_knows_everything_reports_nothing() -> None:
    assert crosswalk([{"code": "a"}], {"a": "A"})[1] == []
""",
        imports="from crosswalk_codes import crosswalk\n",
    ),
    hidden_test=_test_module(
        "crosswalk_codes",
        "The part of the contract the published tests do not state.",
        """
def test_known_codes_are_translated() -> None:
    rows = [{"code": "a"}, {"code": "b"}]
    assert crosswalk(rows, {"a": "A", "b": "B"})[0] == [{"code": "A"}, {"code": "B"}]


def test_an_unknown_code_is_left_as_it_was() -> None:
    assert crosswalk([{"code": "z"}], {})[0] == [{"code": "z"}]


def test_each_unknown_code_is_reported_once_in_order() -> None:
    rows = [{"code": "q"}, {"code": "p"}, {"code": "q"}]
    assert crosswalk(rows, {})[1] == ["p", "q"]
""",
        imports="from crosswalk_codes import crosswalk\n",
    ),
)

_G042 = D2TaskSpec(
    template_id="d6_transform.drift_report",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-drift-report",
    module="drift_report",
    module_doc="Reporting where consecutive readings moved further than a tolerance allows.",
    issue=(
        "drift_report() is documented to report every consecutive pair of readings that moved "
        "further than a tolerance. Callers report that a reading which falls is never reported "
        "however far it falls, and that a move of exactly the tolerance is reported although the "
        "tolerance is meant to be allowed."
    ),
    expected=(
        "drift_report(readings, tolerance) returns one (position, distance) pair for every "
        "consecutive pair whose reading moved strictly further than tolerance, where position "
        "is that of the later reading and distance is how far it moved, in either direction."
    ),
    baseline_reason=(
        "it measures the move as a signed change and it reports a move equal to the tolerance"
    ),
    edge_cases=(
        "a falling reading is reported by how far it fell",
        "a move of exactly the tolerance is allowed",
    ),
    baseline="""def drift_report(readings, tolerance):
    \"\"\"Report the consecutive pairs that moved further than `tolerance`.\"\"\"
    drifted = []
    for position in range(1, len(readings)):
        distance = readings[position] - readings[position - 1]
        if distance >= tolerance:
            drifted.append((position, distance))
    return drifted""",
    variant_one="""def drift_report(readings, tolerance):
    \"\"\"Report the consecutive pairs that moved further than `tolerance`.\"\"\"
    drifted = []
    for position in range(1, len(readings)):
        distance = abs(readings[position] - readings[position - 1])
        if distance > tolerance:
            drifted.append((position, distance))
    return drifted""",
    variant_two="""def drift_report(readings, tolerance):
    \"\"\"Report the consecutive pairs that moved further than `tolerance`.\"\"\"
    pairs = zip(readings, readings[1:])
    measured = [abs(later - earlier) for earlier, later in pairs]
    return [
        (position + 1, distance)
        for position, distance in enumerate(measured)
        if distance > tolerance
    ]""",
    variant_three="""def drift_report(readings, tolerance):
    \"\"\"Report the consecutive pairs that moved further than `tolerance`.\"\"\"
    drifted = []
    for position in range(1, len(readings)):
        distance = abs(readings[position] - readings[position - 1])
        if distance >= tolerance:
            drifted.append((position, distance))
    return drifted""",
    variant_four="""def drift_report(readings, tolerance):
    \"\"\"Report the consecutive pairs that moved further than `tolerance`.\"\"\"
    drifted = []
    for position in range(1, len(readings)):
        distance = readings[position] - readings[position - 1]
        if distance > tolerance:
            drifted.append((position, distance))
    return drifted""",
    visible_test=_test_module(
        "drift_report",
        "Published contract for reporting readings that drifted.",
        """
def test_a_move_beyond_the_tolerance_is_reported() -> None:
    assert drift_report([10, 14, 15], 2) == [(1, 4)]


def test_readings_that_hold_still_are_not_reported() -> None:
    assert drift_report([5, 5, 5], 1) == []
""",
        imports="from drift_report import drift_report\n",
    ),
    hidden_test=_test_module(
        "drift_report",
        "The part of the contract the published tests do not state.",
        """
def test_a_move_beyond_the_tolerance_is_reported() -> None:
    assert drift_report([10, 14, 15], 2) == [(1, 4)]


def test_a_falling_reading_is_reported_by_how_far_it_fell() -> None:
    assert drift_report([10, 4], 2) == [(1, 6)]


def test_a_move_of_exactly_the_tolerance_is_allowed() -> None:
    assert drift_report([10, 12], 2) == []
""",
        imports="from drift_report import drift_report\n",
    ),
)

_G043 = D2TaskSpec(
    template_id="d6_transform.tag_ladder",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-tag-ladder",
    module="tag_ladder",
    module_doc="Building the ladder of ancestors a slash-separated tag stands on.",
    issue=(
        "tag_ladder() is documented to build the ladder of ancestors a tag stands on. Callers "
        "report that a tag written with a leading slash gains an empty rung at the bottom, and "
        "that a tag written with a trailing slash repeats its top rung."
    ),
    expected=(
        "tag_ladder(tag) returns each ancestor of the tag from the shortest to the tag itself, "
        "joined by slashes. A slash at either end separates nothing and contributes no rung."
    ),
    baseline_reason=(
        "it splits on the separator without discarding the empty parts a leading or trailing "
        "slash produces"
    ),
    edge_cases=(
        "a leading slash adds no empty rung",
        "a trailing slash repeats no rung",
    ),
    baseline="""def tag_ladder(tag):
    \"\"\"Return the ladder of ancestors `tag` stands on.\"\"\"
    parts = tag.split("/")
    return ["/".join(parts[: depth + 1]) for depth in range(len(parts))]""",
    variant_one="""def tag_ladder(tag):
    \"\"\"Return the ladder of ancestors `tag` stands on.\"\"\"
    parts = [part for part in tag.split("/") if part]
    return ["/".join(parts[: depth + 1]) for depth in range(len(parts))]""",
    variant_two="""def tag_ladder(tag):
    \"\"\"Return the ladder of ancestors `tag` stands on.\"\"\"
    rungs = []
    standing = ""
    for part in tag.split("/"):
        if not part:
            continue
        standing = f"{standing}/{part}" if standing else part
        rungs.append(standing)
    return rungs""",
    variant_three="""def tag_ladder(tag):
    \"\"\"Return the ladder of ancestors `tag` stands on.\"\"\"
    parts = tag.split("/")
    while parts and not parts[0]:
        parts = parts[1:]
    return ["/".join(parts[: depth + 1]) for depth in range(len(parts))]""",
    variant_four="""def tag_ladder(tag):
    \"\"\"Return the ladder of ancestors `tag` stands on.\"\"\"
    parts = tag.split("/")
    while parts and not parts[-1]:
        parts = parts[:-1]
    return ["/".join(parts[: depth + 1]) for depth in range(len(parts))]""",
    visible_test=_test_module(
        "tag_ladder",
        "Published contract for the ladder of ancestors a tag stands on.",
        """
def test_a_tag_stands_on_its_ancestors() -> None:
    assert tag_ladder("a/b/c") == ["a", "a/b", "a/b/c"]


def test_a_tag_with_no_separator_stands_alone() -> None:
    assert tag_ladder("only") == ["only"]
""",
        imports="from tag_ladder import tag_ladder\n",
    ),
    hidden_test=_test_module(
        "tag_ladder",
        "The part of the contract the published tests do not state.",
        """
def test_a_tag_stands_on_its_ancestors() -> None:
    assert tag_ladder("a/b/c") == ["a", "a/b", "a/b/c"]


def test_a_leading_slash_adds_no_empty_rung() -> None:
    assert tag_ladder("/a/b") == ["a", "a/b"]


def test_a_trailing_slash_repeats_no_rung() -> None:
    assert tag_ladder("a/b/") == ["a", "a/b"]
""",
        imports="from tag_ladder import tag_ladder\n",
    ),
)

_G044 = D2TaskSpec(
    template_id="d6_transform.ledger_fold",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-ledger-fold",
    module="ledger_fold",
    module_doc="Folding ledger entries into the balance each account is left holding.",
    issue=(
        "fold_entries() is documented to fold a ledger into a balance per account. Callers "
        "report that an entry of a kind nobody recognises is folded in silently, and that an "
        "account whose withdrawals outrun its deposits comes back at zero instead of overdrawn."
    ),
    expected=(
        "fold_entries(entries) returns the balance each account is left holding, where a deposit "
        "adds and a withdrawal subtracts. A balance is allowed to be negative. An entry of any "
        "other kind raises ValueError."
    ),
    baseline_reason=(
        "it ignores an entry whose kind it does not recognise and it floors every balance at zero"
    ),
    edge_cases=(
        "an unrecognised kind is refused",
        "a balance is allowed to be negative",
    ),
    baseline="""def fold_entries(entries):
    \"\"\"Fold ledger entries into a balance per account.\"\"\"
    balances = {}
    for entry in entries:
        account = entry["account"]
        standing = balances.get(account, 0)
        if entry["kind"] == "deposit":
            standing += entry["amount"]
        elif entry["kind"] == "withdrawal":
            standing -= entry["amount"]
        balances[account] = max(0, standing)
    return balances""",
    variant_one="""def fold_entries(entries):
    \"\"\"Fold ledger entries into a balance per account.\"\"\"
    balances = {}
    for entry in entries:
        account = entry["account"]
        standing = balances.get(account, 0)
        if entry["kind"] == "deposit":
            standing += entry["amount"]
        elif entry["kind"] == "withdrawal":
            standing -= entry["amount"]
        else:
            raise ValueError(entry["kind"])
        balances[account] = standing
    return balances""",
    variant_two="""SIGNS = {"deposit": 1, "withdrawal": -1}


def fold_entries(entries):
    \"\"\"Fold ledger entries into a balance per account.\"\"\"
    balances = {}
    for entry in entries:
        kind = entry["kind"]
        if kind not in SIGNS:
            raise ValueError(kind)
        account = entry["account"]
        balances[account] = balances.get(account, 0) + SIGNS[kind] * entry["amount"]
    return balances""",
    variant_three="""def fold_entries(entries):
    \"\"\"Fold ledger entries into a balance per account.\"\"\"
    balances = {}
    for entry in entries:
        account = entry["account"]
        standing = balances.get(account, 0)
        if entry["kind"] == "deposit":
            standing += entry["amount"]
        elif entry["kind"] == "withdrawal":
            standing -= entry["amount"]
        else:
            raise ValueError(entry["kind"])
        balances[account] = max(0, standing)
    return balances""",
    variant_four="""def fold_entries(entries):
    \"\"\"Fold ledger entries into a balance per account.\"\"\"
    balances = {}
    for entry in entries:
        account = entry["account"]
        standing = balances.get(account, 0)
        if entry["kind"] == "deposit":
            standing += entry["amount"]
        elif entry["kind"] == "withdrawal":
            standing -= entry["amount"]
        balances[account] = standing
    return balances""",
    visible_test=_test_module(
        "ledger_fold",
        "Published contract for folding a ledger into balances.",
        """
def test_deposits_and_withdrawals_fold_together() -> None:
    entries = [
        {"account": "a", "kind": "deposit", "amount": 10},
        {"account": "a", "kind": "withdrawal", "amount": 4},
    ]
    assert fold_entries(entries) == {"a": 6}


def test_each_account_is_folded_separately() -> None:
    entries = [
        {"account": "a", "kind": "deposit", "amount": 3},
        {"account": "b", "kind": "deposit", "amount": 5},
    ]
    assert fold_entries(entries) == {"a": 3, "b": 5}
""",
        imports="from ledger_fold import fold_entries\n",
    ),
    hidden_test=_test_module(
        "ledger_fold",
        "The part of the contract the published tests do not state.",
        """
import pytest

from ledger_fold import fold_entries


def test_deposits_and_withdrawals_fold_together() -> None:
    entries = [
        {"account": "a", "kind": "deposit", "amount": 10},
        {"account": "a", "kind": "withdrawal", "amount": 4},
    ]
    assert fold_entries(entries) == {"a": 6}


def test_an_unrecognised_kind_is_refused() -> None:
    with pytest.raises(ValueError):
        fold_entries([{"account": "a", "kind": "gift", "amount": 5}])


def test_a_balance_is_allowed_to_be_negative() -> None:
    entries = [{"account": "a", "kind": "withdrawal", "amount": 3}]
    assert fold_entries(entries) == {"a": -3}
""",
    ),
)

_G045 = D2TaskSpec(
    template_id="d6_error.abort_ladder",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-abort-ladder",
    module="abort_ladder",
    module_doc="Keeping the first few objections and saying how many were dropped.",
    issue=(
        "keep_first() is documented to keep the first few objections and to say how many it "
        "dropped. Callers report that the count of dropped objections never rises above one "
        "however many were dropped, and that a negative limit is quietly treated as none."
    ),
    expected=(
        "keep_first(objections, limit) returns the first limit objections together with how many "
        "were dropped. A limit of zero keeps none and drops them all. A limit below zero raises "
        "ValueError, because there is no such thing as keeping fewer than none."
    ),
    baseline_reason=(
        "it records that something was dropped rather than how many, and it clamps a negative "
        "limit to zero"
    ),
    edge_cases=(
        "the count of dropped objections is a count",
        "a limit below zero is refused",
    ),
    baseline="""def keep_first(objections, limit):
    \"\"\"Keep the first `limit` objections and count the rest.\"\"\"
    ceiling = max(0, limit)
    kept = list(objections[:ceiling])
    dropped = 1 if len(objections) > ceiling else 0
    return kept, dropped""",
    variant_one="""def keep_first(objections, limit):
    \"\"\"Keep the first `limit` objections and count the rest.\"\"\"
    if limit < 0:
        raise ValueError("a limit below zero keeps fewer than none")
    kept = list(objections[:limit])
    return kept, len(objections) - len(kept)""",
    variant_two="""def keep_first(objections, limit):
    \"\"\"Keep the first `limit` objections and count the rest.\"\"\"
    if not limit >= 0:
        raise ValueError("a limit below zero keeps fewer than none")
    kept = []
    dropped = 0
    for objection in objections:
        if len(kept) < limit:
            kept.append(objection)
        else:
            dropped += 1
    return kept, dropped""",
    variant_three="""def keep_first(objections, limit):
    \"\"\"Keep the first `limit` objections and count the rest.\"\"\"
    ceiling = max(0, limit)
    kept = list(objections[:ceiling])
    return kept, len(objections) - len(kept)""",
    variant_four="""def keep_first(objections, limit):
    \"\"\"Keep the first `limit` objections and count the rest.\"\"\"
    if limit < 0:
        raise ValueError("a limit below zero keeps fewer than none")
    kept = list(objections[:limit])
    dropped = 1 if len(objections) > limit else 0
    return kept, dropped""",
    visible_test=_test_module(
        "abort_ladder",
        "Published contract for keeping the first few objections.",
        """
def test_the_first_objections_are_kept() -> None:
    assert keep_first(["a", "b", "c"], 2) == (["a", "b"], 1)


def test_nothing_is_dropped_when_everything_fits() -> None:
    assert keep_first(["a"], 3) == (["a"], 0)
""",
        imports="from abort_ladder import keep_first\n",
    ),
    hidden_test=_test_module(
        "abort_ladder",
        "The part of the contract the published tests do not state.",
        """
import pytest

from abort_ladder import keep_first


def test_the_first_objections_are_kept() -> None:
    assert keep_first(["a", "b", "c"], 2) == (["a", "b"], 1)


def test_the_count_of_dropped_objections_is_a_count() -> None:
    assert keep_first(["a", "b", "c", "d"], 1) == (["a"], 3)


def test_a_limit_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        keep_first(["a"], -1)
""",
    ),
)

_G046 = D2TaskSpec(
    template_id="d6_error.deadline_split",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-deadline-split",
    module="deadline_split",
    module_doc="Setting aside a reserve out of a budget, and refusing the splits that cannot be.",
    issue=(
        "split_budget() is documented to set a reserve aside out of a budget. Callers report "
        "that reserving the whole budget is refused although it leaves a working part of "
        "nothing, and that a negative reserve is accepted and hands back more than the budget."
    ),
    expected=(
        "split_budget(total, reserve) returns (working, reserve) where working is what is left "
        "after the reserve. Reserving the whole budget is allowed and leaves nothing to work "
        "with. A reserve above the total or below zero raises ValueError."
    ),
    baseline_reason=(
        "it refuses a reserve equal to the total and it never checks for a negative reserve"
    ),
    edge_cases=(
        "reserving the whole budget is allowed",
        "a negative reserve is refused",
    ),
    baseline="""def split_budget(total, reserve):
    \"\"\"Set `reserve` aside out of `total`.\"\"\"
    if reserve >= total:
        raise ValueError("the reserve does not fit the budget")
    return total - reserve, reserve""",
    variant_one="""def split_budget(total, reserve):
    \"\"\"Set `reserve` aside out of `total`.\"\"\"
    if reserve > total:
        raise ValueError("the reserve does not fit the budget")
    if reserve < 0:
        raise ValueError("a reserve below zero reserves nothing")
    return total - reserve, reserve""",
    variant_two="""def split_budget(total, reserve):
    \"\"\"Set `reserve` aside out of `total`.\"\"\"
    if not 0 <= reserve <= total:
        raise ValueError("the reserve does not fit the budget")
    return total - reserve, reserve""",
    variant_three="""def split_budget(total, reserve):
    \"\"\"Set `reserve` aside out of `total`.\"\"\"
    if reserve > total:
        raise ValueError("the reserve does not fit the budget")
    return total - reserve, reserve""",
    variant_four="""def split_budget(total, reserve):
    \"\"\"Set `reserve` aside out of `total`.\"\"\"
    if reserve >= total:
        raise ValueError("the reserve does not fit the budget")
    if reserve < 0:
        raise ValueError("a reserve below zero reserves nothing")
    return total - reserve, reserve""",
    visible_test=_test_module(
        "deadline_split",
        "Published contract for setting a reserve aside.",
        """
import pytest

from deadline_split import split_budget


def test_a_reserve_is_taken_out_of_the_budget() -> None:
    assert split_budget(10, 3) == (7, 3)


def test_a_reserve_above_the_budget_is_refused() -> None:
    with pytest.raises(ValueError):
        split_budget(5, 9)
""",
    ),
    hidden_test=_test_module(
        "deadline_split",
        "The part of the contract the published tests do not state.",
        """
import pytest

from deadline_split import split_budget


def test_a_reserve_is_taken_out_of_the_budget() -> None:
    assert split_budget(10, 3) == (7, 3)


def test_reserving_the_whole_budget_is_allowed() -> None:
    assert split_budget(5, 5) == (0, 5)


def test_a_negative_reserve_is_refused() -> None:
    with pytest.raises(ValueError):
        split_budget(10, -2)
""",
    ),
)

_G047 = D2TaskSpec(
    template_id="d6_error.objection_codes",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-objection-codes",
    module="objection_codes",
    module_doc="Gathering the distinct codes a batch of objections carries.",
    issue=(
        "gather_codes() is documented to gather the distinct codes a batch of objections "
        "carries. Callers report that an objection carrying no code at all is passed over in "
        "silence, and that a code raised twice is reported twice."
    ),
    expected=(
        "gather_codes(objections) returns the distinct codes in sorted order. An objection with "
        "no code raises KeyError, because an objection nobody can name is not something to "
        "quietly drop."
    ),
    baseline_reason=(
        "it reaches the code through a lookup that tolerates its absence and it never removes "
        "repeats"
    ),
    edge_cases=(
        "an objection with no code is refused",
        "a code raised twice is reported once",
    ),
    baseline="""def gather_codes(objections):
    \"\"\"Gather the distinct codes a batch of objections carries.\"\"\"
    codes = []
    for objection in objections:
        code = objection.get("code")
        if code is not None:
            codes.append(code)
    return sorted(codes)""",
    variant_one="""def gather_codes(objections):
    \"\"\"Gather the distinct codes a batch of objections carries.\"\"\"
    codes = set()
    for objection in objections:
        codes.add(objection["code"])
    return sorted(codes)""",
    variant_two="""def gather_codes(objections):
    \"\"\"Gather the distinct codes a batch of objections carries.\"\"\"
    codes = []
    for objection in objections:
        code = objection["code"]
        if code not in codes:
            codes.append(code)
    codes.sort()
    return codes""",
    variant_three="""def gather_codes(objections):
    \"\"\"Gather the distinct codes a batch of objections carries.\"\"\"
    codes = []
    for objection in objections:
        codes.append(objection["code"])
    return sorted(codes)""",
    variant_four="""def gather_codes(objections):
    \"\"\"Gather the distinct codes a batch of objections carries.\"\"\"
    codes = set()
    for objection in objections:
        code = objection.get("code")
        if code is not None:
            codes.add(code)
    return sorted(codes)""",
    visible_test=_test_module(
        "objection_codes",
        "Published contract for gathering objection codes.",
        """
def test_codes_come_back_sorted() -> None:
    assert gather_codes([{"code": "E2"}, {"code": "E1"}]) == ["E1", "E2"]


def test_no_objections_carry_no_codes() -> None:
    assert gather_codes([]) == []
""",
        imports="from objection_codes import gather_codes\n",
    ),
    hidden_test=_test_module(
        "objection_codes",
        "The part of the contract the published tests do not state.",
        """
import pytest

from objection_codes import gather_codes


def test_codes_come_back_sorted() -> None:
    assert gather_codes([{"code": "E2"}, {"code": "E1"}]) == ["E1", "E2"]


def test_an_objection_with_no_code_is_refused() -> None:
    with pytest.raises(KeyError):
        gather_codes([{"note": "unnamed"}])


def test_a_code_raised_twice_is_reported_once() -> None:
    assert gather_codes([{"code": "E1"}, {"code": "E1"}]) == ["E1"]
""",
    ),
)

_G049 = D2TaskSpec(
    template_id="d6_parsing.quantity_phrase",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-quantity-phrase",
    module="quantity_phrase",
    module_doc="Reading a packaging phrase such as three of two hundred and fifty millilitres.",
    issue=(
        "read_quantity() is documented to read a packaging phrase into a count, a size and a "
        "unit. Callers report that a phrase naming no count comes back with a count of zero "
        "rather than the single item it describes, and that a phrase written without spaces "
        "around the multiplier is refused outright."
    ),
    expected=(
        "read_quantity(text) returns (count, size, unit). A phrase with no multiplier describes "
        "one item. The spaces around the multiplier are optional. A phrase that fits neither "
        "shape raises ValueError."
    ),
    baseline_reason=(
        "it substitutes zero for an absent count and its pattern demands a space on each side "
        "of the multiplier"
    ),
    edge_cases=(
        "a phrase with no multiplier describes one item",
        "the spaces around the multiplier are optional",
    ),
    baseline="""import re

PATTERN = re.compile(r"^(?:(\\d+) x )?(\\d+)([a-z]+)$")


def read_quantity(text):
    \"\"\"Return the (count, size, unit) a packaging phrase describes.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    return int(found.group(1) or 0), int(found.group(2)), found.group(3)""",
    variant_one="""import re

PATTERN = re.compile(r"^(?:(\\d+) ?x ?)?(\\d+)([a-z]+)$")


def read_quantity(text):
    \"\"\"Return the (count, size, unit) a packaging phrase describes.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    return int(found.group(1) or 1), int(found.group(2)), found.group(3)""",
    variant_two="""import re

SIZE = re.compile(r"^(\\d+)([a-z]+)$")


def read_quantity(text):
    \"\"\"Return the (count, size, unit) a packaging phrase describes.\"\"\"
    count = 1
    remainder = text
    if "x" in text:
        head, _, remainder = text.partition("x")
        head = head.strip()
        remainder = remainder.strip()
        if not head.isdigit():
            raise ValueError(text)
        count = int(head)
    found = SIZE.match(remainder)
    if not found:
        raise ValueError(text)
    return count, int(found.group(1)), found.group(2)""",
    variant_three="""import re

PATTERN = re.compile(r"^(?:(\\d+) x )?(\\d+)([a-z]+)$")


def read_quantity(text):
    \"\"\"Return the (count, size, unit) a packaging phrase describes.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    return int(found.group(1) or 1), int(found.group(2)), found.group(3)""",
    variant_four="""import re

PATTERN = re.compile(r"^(?:(\\d+) ?x ?)?(\\d+)([a-z]+)$")


def read_quantity(text):
    \"\"\"Return the (count, size, unit) a packaging phrase describes.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    return int(found.group(1) or 0), int(found.group(2)), found.group(3)""",
    visible_test=_test_module(
        "quantity_phrase",
        "Published contract for reading a packaging phrase.",
        """
import pytest

from quantity_phrase import read_quantity


def test_a_multiplied_phrase_is_read() -> None:
    assert read_quantity("3 x 250ml") == (3, 250, "ml")


def test_a_phrase_of_neither_shape_is_refused() -> None:
    with pytest.raises(ValueError):
        read_quantity("a crate")
""",
    ),
    hidden_test=_test_module(
        "quantity_phrase",
        "The part of the contract the published tests do not state.",
        """
import pytest

from quantity_phrase import read_quantity


def test_a_multiplied_phrase_is_read() -> None:
    assert read_quantity("3 x 250ml") == (3, 250, "ml")


def test_a_phrase_with_no_multiplier_describes_one_item() -> None:
    assert read_quantity("250ml") == (1, 250, "ml")


def test_the_spaces_around_the_multiplier_are_optional() -> None:
    assert read_quantity("3x250ml") == (3, 250, "ml")
""",
    ),
)

_G050 = D2TaskSpec(
    template_id="d6_state.promotion_gate",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-promotion-gate",
    module="promotion_gate",
    module_doc="Promoting a candidate once, and only a candidate.",
    issue=(
        "promote() is documented to move a candidate onto the promoted list exactly once. "
        "Callers report that promoting somebody already promoted lists them a second time, and "
        "that promoting somebody who was never a candidate simply invents them."
    ),
    expected=(
        "promote(state, name) moves name out of candidates and onto promoted. Somebody already "
        "promoted is left alone, because a repeated promotion is the same promotion. Somebody "
        "who is neither a candidate nor already promoted raises KeyError."
    ),
    baseline_reason=(
        "it appends to the promoted list without looking whether the name is there, and it "
        "never checks that the name was a candidate"
    ),
    edge_cases=(
        "promoting somebody already promoted changes nothing",
        "promoting somebody who was never a candidate is refused",
    ),
    baseline="""def promote(state, name):
    \"\"\"Move `name` from the candidates onto the promoted list.\"\"\"
    candidates = [person for person in state.get("candidates", []) if person != name]
    promoted = [*state.get("promoted", []), name]
    return {"candidates": candidates, "promoted": promoted}""",
    variant_one="""def promote(state, name):
    \"\"\"Move `name` from the candidates onto the promoted list.\"\"\"
    candidates = list(state.get("candidates", []))
    promoted = list(state.get("promoted", []))
    if name in promoted:
        return {"candidates": candidates, "promoted": promoted}
    if name not in candidates:
        raise KeyError(name)
    candidates.remove(name)
    promoted.append(name)
    return {"candidates": candidates, "promoted": promoted}""",
    variant_two="""def promote(state, name):
    \"\"\"Move `name` from the candidates onto the promoted list.\"\"\"
    candidates = list(state.get("candidates", []))
    promoted = list(state.get("promoted", []))
    already = name in promoted
    standing = name in candidates
    if not already and not standing:
        raise KeyError(name)
    if already:
        return {"candidates": candidates, "promoted": promoted}
    return {
        "candidates": [person for person in candidates if person != name],
        "promoted": [*promoted, name],
    }""",
    variant_three="""def promote(state, name):
    \"\"\"Move `name` from the candidates onto the promoted list.\"\"\"
    candidates = list(state.get("candidates", []))
    promoted = list(state.get("promoted", []))
    if name in promoted:
        return {"candidates": candidates, "promoted": promoted}
    return {
        "candidates": [person for person in candidates if person != name],
        "promoted": [*promoted, name],
    }""",
    variant_four="""def promote(state, name):
    \"\"\"Move `name` from the candidates onto the promoted list.\"\"\"
    candidates = list(state.get("candidates", []))
    promoted = list(state.get("promoted", []))
    if name not in candidates:
        raise KeyError(name)
    candidates.remove(name)
    promoted.append(name)
    return {"candidates": candidates, "promoted": promoted}""",
    visible_test=_test_module(
        "promotion_gate",
        "Published contract for promoting a candidate.",
        """
def test_a_candidate_is_promoted() -> None:
    state = {"candidates": ["a"], "promoted": []}
    assert promote(state, "a") == {"candidates": [], "promoted": ["a"]}


def test_the_other_candidates_stay_where_they_are() -> None:
    state = {"candidates": ["a", "b"], "promoted": []}
    assert promote(state, "a")["candidates"] == ["b"]
""",
        imports="from promotion_gate import promote\n",
    ),
    hidden_test=_test_module(
        "promotion_gate",
        "The part of the contract the published tests do not state.",
        """
import pytest

from promotion_gate import promote


def test_a_candidate_is_promoted() -> None:
    state = {"candidates": ["a"], "promoted": []}
    assert promote(state, "a") == {"candidates": [], "promoted": ["a"]}


def test_promoting_somebody_already_promoted_changes_nothing() -> None:
    state = {"candidates": [], "promoted": ["a"]}
    assert promote(state, "a") == {"candidates": [], "promoted": ["a"]}


def test_promoting_somebody_who_was_never_a_candidate_is_refused() -> None:
    with pytest.raises(KeyError):
        promote({"candidates": ["a"], "promoted": []}, "z")
""",
    ),
)

_G051 = D2TaskSpec(
    template_id="d6_parsing.citation_key",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-citation-key",
    module="citation_key",
    module_doc="Reading a citation key into the surname, the year and the disambiguating letter.",
    issue=(
        "read_key() is documented to read a citation key into a surname, a year and the letter "
        "that tells two papers of the same year apart. Callers report that a key with no such "
        "letter comes back carrying an empty string instead of nothing at all, and that a "
        "surname with a capital inside it is refused."
    ),
    expected=(
        "read_key(key) returns (surname, year, letter), where letter is None when the key names "
        "no disambiguating letter. A surname may carry capitals anywhere in it. A key of any "
        "other shape raises ValueError."
    ),
    baseline_reason=(
        "it hands the empty match through as the letter and its pattern allows a capital only "
        "at the front of the surname"
    ),
    edge_cases=(
        "a key with no disambiguating letter carries None",
        "a surname may carry a capital inside it",
    ),
    baseline="""import re

PATTERN = re.compile(r"^([A-Z][a-z]+)(\\d{4})([a-z]?)$")


def read_key(key):
    \"\"\"Return the (surname, year, letter) a citation key names.\"\"\"
    found = PATTERN.match(key)
    if not found:
        raise ValueError(key)
    return found.group(1), int(found.group(2)), found.group(3)""",
    variant_one="""import re

PATTERN = re.compile(r"^([A-Za-z]+)(\\d{4})([a-z]?)$")


def read_key(key):
    \"\"\"Return the (surname, year, letter) a citation key names.\"\"\"
    found = PATTERN.match(key)
    if not found:
        raise ValueError(key)
    return found.group(1), int(found.group(2)), found.group(3) or None""",
    variant_two="""import re

PATTERN = re.compile(r"^([A-Za-z]+)(\\d{4})([a-z]?)$")


def read_key(key):
    \"\"\"Return the (surname, year, letter) a citation key names.\"\"\"
    found = PATTERN.match(key)
    if found is None:
        raise ValueError(key)
    surname, year, letter = found.groups()
    return surname, int(year), letter if letter else None""",
    variant_three="""import re

PATTERN = re.compile(r"^([A-Z][a-z]+)(\\d{4})([a-z]?)$")


def read_key(key):
    \"\"\"Return the (surname, year, letter) a citation key names.\"\"\"
    found = PATTERN.match(key)
    if not found:
        raise ValueError(key)
    return found.group(1), int(found.group(2)), found.group(3) or None""",
    variant_four="""import re

PATTERN = re.compile(r"^([A-Za-z]+)(\\d{4})([a-z]?)$")


def read_key(key):
    \"\"\"Return the (surname, year, letter) a citation key names.\"\"\"
    found = PATTERN.match(key)
    if not found:
        raise ValueError(key)
    return found.group(1), int(found.group(2)), found.group(3)""",
    visible_test=_test_module(
        "citation_key",
        "Published contract for reading a citation key.",
        """
import pytest

from citation_key import read_key


def test_a_key_with_a_letter_is_read() -> None:
    assert read_key("Smith2019a") == ("Smith", 2019, "a")


def test_a_key_of_another_shape_is_refused() -> None:
    with pytest.raises(ValueError):
        read_key("no-year-here")
""",
    ),
    hidden_test=_test_module(
        "citation_key",
        "The part of the contract the published tests do not state.",
        """
import pytest

from citation_key import read_key


def test_a_key_with_a_letter_is_read() -> None:
    assert read_key("Smith2019a") == ("Smith", 2019, "a")


def test_a_key_with_no_letter_carries_none() -> None:
    assert read_key("Smith2019") == ("Smith", 2019, None)


def test_a_surname_may_carry_a_capital_inside_it() -> None:
    assert read_key("McKay2019a") == ("McKay", 2019, "a")
""",
    ),
)

_G052 = D2TaskSpec(
    template_id="d6_parsing.flag_cluster",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-flag-cluster",
    module="flag_cluster",
    module_doc="Pulling a bundle of single-letter switches apart into the switches it stands for.",
    issue=(
        "expand_cluster() is documented to pull a bundle of single-letter switches apart. "
        "Callers report that a long switch written with two dashes is torn into letters as "
        "though it were a bundle, and that a lone dash with no letters after it comes back as "
        "an empty list instead of being refused."
    ),
    expected=(
        "expand_cluster(argument) returns the switches a bundle stands for, each with its own "
        "dash. A switch written with two dashes stands for itself and is returned whole. A lone "
        "dash names no switch and raises ValueError."
    ),
    baseline_reason=(
        "it strips the dashes before looking at how many there were, and it returns nothing at "
        "all for a lone dash"
    ),
    edge_cases=(
        "a switch written with two dashes is returned whole",
        "a lone dash is refused",
    ),
    baseline="""def expand_cluster(argument):
    \"\"\"Return the switches a bundle of letters stands for.\"\"\"
    letters = argument.lstrip("-")
    return [f"-{letter}" for letter in letters]""",
    variant_one="""def expand_cluster(argument):
    \"\"\"Return the switches a bundle of letters stands for.\"\"\"
    if argument.startswith("--"):
        return [argument]
    letters = argument.lstrip("-")
    if not letters:
        raise ValueError(argument)
    return [f"-{letter}" for letter in letters]""",
    variant_two="""def expand_cluster(argument):
    \"\"\"Return the switches a bundle of letters stands for.\"\"\"
    dashes = len(argument) - len(argument.lstrip("-"))
    body = argument[dashes:]
    if dashes >= 2:
        return [argument]
    if not body:
        raise ValueError(argument)
    return ["-" + letter for letter in body]""",
    variant_three="""def expand_cluster(argument):
    \"\"\"Return the switches a bundle of letters stands for.\"\"\"
    if argument.startswith("--"):
        return [argument]
    letters = argument.lstrip("-")
    return [f"-{letter}" for letter in letters]""",
    variant_four="""def expand_cluster(argument):
    \"\"\"Return the switches a bundle of letters stands for.\"\"\"
    letters = argument.lstrip("-")
    if not letters:
        raise ValueError(argument)
    return [f"-{letter}" for letter in letters]""",
    visible_test=_test_module(
        "flag_cluster",
        "Published contract for expanding a bundle of switches.",
        """
def test_a_bundle_stands_for_its_switches() -> None:
    assert expand_cluster("-abc") == ["-a", "-b", "-c"]


def test_a_single_switch_stands_for_itself() -> None:
    assert expand_cluster("-v") == ["-v"]
""",
        imports="from flag_cluster import expand_cluster\n",
    ),
    hidden_test=_test_module(
        "flag_cluster",
        "The part of the contract the published tests do not state.",
        """
import pytest

from flag_cluster import expand_cluster


def test_a_bundle_stands_for_its_switches() -> None:
    assert expand_cluster("-abc") == ["-a", "-b", "-c"]


def test_a_two_dash_switch_is_returned_whole() -> None:
    assert expand_cluster("--name") == ["--name"]


def test_a_lone_dash_is_refused() -> None:
    with pytest.raises(ValueError):
        expand_cluster("-")
""",
    ),
)

_G053 = D2TaskSpec(
    template_id="d6_parsing.iso_week",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-iso-week",
    module="iso_week",
    module_doc="Reading a week-numbered date into its year, week and weekday.",
    issue=(
        "read_week() is documented to read a week-numbered date. Callers report that a date "
        "naming no weekday comes back with nothing where the weekday should be, instead of the "
        "Monday it means, and that a week number no year has is accepted without complaint."
    ),
    expected=(
        "read_week(text) returns (year, week, weekday) from a date written as a year, the "
        "letter W, a two-digit week and optionally a weekday. A date naming no weekday means "
        "Monday, which is day one. A week outside one to fifty-three raises ValueError, and so "
        "does any other shape."
    ),
    baseline_reason=(
        "it passes the absent weekday through as nothing and it never checks the week against "
        "the year's fifty-three"
    ),
    edge_cases=(
        "a date naming no weekday means Monday",
        "a week outside one to fifty-three is refused",
    ),
    baseline="""import re

PATTERN = re.compile(r"^(\\d{4})-W(\\d{2})(?:-(\\d))?$")


def read_week(text):
    \"\"\"Return the (year, week, weekday) a week-numbered date names.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    weekday = found.group(3)
    return int(found.group(1)), int(found.group(2)), int(weekday) if weekday else None""",
    variant_one="""import re

PATTERN = re.compile(r"^(\\d{4})-W(\\d{2})(?:-(\\d))?$")


def read_week(text):
    \"\"\"Return the (year, week, weekday) a week-numbered date names.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    week = int(found.group(2))
    if not 1 <= week <= 53:
        raise ValueError(text)
    weekday = found.group(3)
    return int(found.group(1)), week, int(weekday) if weekday else 1""",
    variant_two="""import re

PATTERN = re.compile(r"^(\\d{4})-W(\\d{2})(?:-(\\d))?$")


def read_week(text):
    \"\"\"Return the (year, week, weekday) a week-numbered date names.\"\"\"
    found = PATTERN.match(text)
    if found is None:
        raise ValueError(text)
    year, week, weekday = found.groups()
    numbered = int(week)
    if numbered < 1 or numbered > 53:
        raise ValueError(text)
    return int(year), numbered, int(weekday) if weekday is not None else 1""",
    variant_three="""import re

PATTERN = re.compile(r"^(\\d{4})-W(\\d{2})(?:-(\\d))?$")


def read_week(text):
    \"\"\"Return the (year, week, weekday) a week-numbered date names.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    weekday = found.group(3)
    return int(found.group(1)), int(found.group(2)), int(weekday) if weekday else 1""",
    variant_four="""import re

PATTERN = re.compile(r"^(\\d{4})-W(\\d{2})(?:-(\\d))?$")


def read_week(text):
    \"\"\"Return the (year, week, weekday) a week-numbered date names.\"\"\"
    found = PATTERN.match(text)
    if not found:
        raise ValueError(text)
    week = int(found.group(2))
    if not 1 <= week <= 53:
        raise ValueError(text)
    weekday = found.group(3)
    return int(found.group(1)), week, int(weekday) if weekday else None""",
    visible_test=_test_module(
        "iso_week",
        "Published contract for reading a week-numbered date.",
        """
import pytest

from iso_week import read_week


def test_a_full_week_date_is_read() -> None:
    assert read_week("2026-W07-3") == (2026, 7, 3)


def test_a_date_of_another_shape_is_refused() -> None:
    with pytest.raises(ValueError):
        read_week("2026-02-14")
""",
    ),
    hidden_test=_test_module(
        "iso_week",
        "The part of the contract the published tests do not state.",
        """
import pytest

from iso_week import read_week


def test_a_full_week_date_is_read() -> None:
    assert read_week("2026-W07-3") == (2026, 7, 3)


def test_a_date_naming_no_weekday_means_monday() -> None:
    assert read_week("2026-W07") == (2026, 7, 1)


def test_a_week_beyond_fifty_three_is_refused() -> None:
    with pytest.raises(ValueError):
        read_week("2026-W60-1")
""",
    ),
)

_G054 = D2TaskSpec(
    template_id="d6_parsing.phone_extension",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-phone-extension",
    module="phone_extension",
    module_doc="Separating a dialling number from the extension written after it.",
    issue=(
        "split_extension() is documented to separate a number from the extension written after "
        "it. Callers report that a number written with spaces in it keeps them, and that an "
        "extension introduced by a hash is not recognised as an extension at all."
    ),
    expected=(
        "split_extension(text) returns (number, extension) with the number's spaces removed and "
        "the extension as written, or None when there is none. Either a lower-case x or a hash "
        "introduces the extension."
    ),
    baseline_reason=(
        "it removes only the space either side of the split and it looks for the letter x alone"
    ),
    edge_cases=(
        "the number's internal spaces are removed",
        "a hash introduces an extension too",
    ),
    baseline="""def split_extension(text):
    \"\"\"Return the (number, extension) a dialling string names.\"\"\"
    number, marker, extension = text.partition("x")
    if not marker:
        return text.strip(), None
    return number.strip(), extension.strip()""",
    variant_one="""def split_extension(text):
    \"\"\"Return the (number, extension) a dialling string names.\"\"\"
    for marker in ("x", "#"):
        number, found, extension = text.partition(marker)
        if found:
            return number.replace(" ", ""), extension.strip()
    return text.replace(" ", ""), None""",
    variant_two="""def split_extension(text):
    \"\"\"Return the (number, extension) a dialling string names.\"\"\"
    position = len(text)
    for marker in ("x", "#"):
        found = text.find(marker)
        if found != -1:
            position = min(position, found)
    number = text[:position].replace(" ", "")
    if position == len(text):
        return number, None
    return number, text[position + 1 :].strip()""",
    variant_three="""def split_extension(text):
    \"\"\"Return the (number, extension) a dialling string names.\"\"\"
    number, marker, extension = text.partition("x")
    if not marker:
        return text.replace(" ", ""), None
    return number.replace(" ", ""), extension.strip()""",
    variant_four="""def split_extension(text):
    \"\"\"Return the (number, extension) a dialling string names.\"\"\"
    for marker in ("x", "#"):
        number, found, extension = text.partition(marker)
        if found:
            return number.strip(), extension.strip()
    return text.strip(), None""",
    visible_test=_test_module(
        "phone_extension",
        "Published contract for separating a number from its extension.",
        """
def test_an_extension_is_separated() -> None:
    assert split_extension("02079460018x231") == ("02079460018", "231")


def test_a_number_with_no_extension_carries_none() -> None:
    assert split_extension("02079460018") == ("02079460018", None)
""",
        imports="from phone_extension import split_extension\n",
    ),
    hidden_test=_test_module(
        "phone_extension",
        "The part of the contract the published tests do not state.",
        """
def test_an_extension_is_separated() -> None:
    assert split_extension("02079460018x231") == ("02079460018", "231")


def test_the_numbers_internal_spaces_are_removed() -> None:
    assert split_extension("020 7946 0018 x231") == ("02079460018", "231")


def test_a_hash_introduces_an_extension_too() -> None:
    assert split_extension("02079460018#231") == ("02079460018", "231")
""",
        imports="from phone_extension import split_extension\n",
    ),
)

_G055 = D2TaskSpec(
    template_id="d6_state.sequence_gate",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-sequence-gate",
    module="sequence_gate",
    module_doc="Delivering numbered messages in order, holding the ones that arrive early.",
    issue=(
        "receive() is documented to deliver numbered messages in order and to hold early "
        "arrivals until their turn. Callers report that a message already delivered is put in "
        "the holding area a second time, and that the messages waiting there are not delivered "
        "when the one they were waiting for finally arrives."
    ),
    expected=(
        "receive(state, number) delivers the message when it is the one expected next, then "
        "delivers whatever was waiting for it, in order. A message already delivered is ignored. "
        "A message arriving early waits."
    ),
    baseline_reason=(
        "it holds anything that is not the expected number, delivered or not, and it never "
        "looks in the holding area after a delivery"
    ),
    edge_cases=(
        "a message already delivered is ignored",
        "the messages waiting are delivered when their turn comes",
    ),
    baseline="""def receive(state, number):
    \"\"\"Deliver `number` if it is next, otherwise hold it.\"\"\"
    expected = state["next"]
    delivered = list(state["delivered"])
    waiting = list(state["waiting"])
    if number == expected:
        delivered.append(number)
        expected += 1
    else:
        waiting.append(number)
    return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}""",
    variant_one="""def receive(state, number):
    \"\"\"Deliver `number` if it is next, otherwise hold it.\"\"\"
    expected = state["next"]
    delivered = list(state["delivered"])
    waiting = list(state["waiting"])
    if number < expected:
        return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}
    if number > expected:
        waiting.append(number)
        return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}
    delivered.append(number)
    expected += 1
    while expected in waiting:
        waiting.remove(expected)
        delivered.append(expected)
        expected += 1
    return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}""",
    variant_two="""def receive(state, number):
    \"\"\"Deliver `number` if it is next, otherwise hold it.\"\"\"
    expected = state["next"]
    delivered = list(state["delivered"])
    waiting = set(state["waiting"])
    if number >= expected:
        waiting.add(number)
    while expected in waiting:
        waiting.discard(expected)
        delivered.append(expected)
        expected += 1
    return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}""",
    variant_three="""def receive(state, number):
    \"\"\"Deliver `number` if it is next, otherwise hold it.\"\"\"
    expected = state["next"]
    delivered = list(state["delivered"])
    waiting = list(state["waiting"])
    if number < expected:
        return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}
    if number == expected:
        delivered.append(number)
        expected += 1
    else:
        waiting.append(number)
    return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}""",
    variant_four="""def receive(state, number):
    \"\"\"Deliver `number` if it is next, otherwise hold it.\"\"\"
    expected = state["next"]
    delivered = list(state["delivered"])
    waiting = list(state["waiting"])
    if number == expected:
        delivered.append(number)
        expected += 1
        while expected in waiting:
            waiting.remove(expected)
            delivered.append(expected)
            expected += 1
    else:
        waiting.append(number)
    return {"next": expected, "delivered": delivered, "waiting": sorted(waiting)}""",
    visible_test=_test_module(
        "sequence_gate",
        "Published contract for delivering numbered messages in order.",
        """
def test_the_expected_message_is_delivered() -> None:
    state = {"next": 1, "delivered": [], "waiting": []}
    assert receive(state, 1) == {"next": 2, "delivered": [1], "waiting": []}


def test_an_early_message_waits() -> None:
    state = {"next": 1, "delivered": [], "waiting": []}
    assert receive(state, 3) == {"next": 1, "delivered": [], "waiting": [3]}
""",
        imports="from sequence_gate import receive\n",
    ),
    hidden_test=_test_module(
        "sequence_gate",
        "The part of the contract the published tests do not state.",
        """
def test_the_expected_message_is_delivered() -> None:
    state = {"next": 1, "delivered": [], "waiting": []}
    assert receive(state, 1) == {"next": 2, "delivered": [1], "waiting": []}


def test_a_message_already_delivered_is_ignored() -> None:
    state = {"next": 3, "delivered": [1, 2], "waiting": []}
    assert receive(state, 2) == {"next": 3, "delivered": [1, 2], "waiting": []}


def test_the_waiting_messages_are_delivered_when_their_turn_comes() -> None:
    state = {"next": 1, "delivered": [], "waiting": [2]}
    assert receive(state, 1) == {"next": 3, "delivered": [1, 2], "waiting": []}
""",
        imports="from sequence_gate import receive\n",
    ),
)

_G056 = D2TaskSpec(
    template_id="d6_state.session_pin",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-session-pin",
    module="session_pin",
    module_doc="Pinning a session to the first device that claims it.",
    issue=(
        "claim() is documented to pin a session to the first device that claims it and to "
        "refuse any other. Callers report that the device already holding the session is "
        "refused when it claims again, and that a session nobody has claimed yet refuses "
        "everybody."
    ),
    expected=(
        "claim(session, device) returns the session pinned to device. A session pinned to None "
        "is unclaimed and accepts any device. The device already holding it may claim it again, "
        "which changes nothing. Any other device raises RuntimeError."
    ),
    baseline_reason=(
        "it refuses whenever the pin differs from the claimant without asking whether the pin "
        "is the claimant already or whether there is a pin at all"
    ),
    edge_cases=(
        "the device already holding the session may claim it again",
        "an unclaimed session accepts any device",
    ),
    baseline="""def claim(session, device):
    \"\"\"Pin `session` to `device`, or refuse.\"\"\"
    if session["pinned"] != device:
        raise RuntimeError("pinned elsewhere")
    return {"pinned": device}""",
    variant_one="""def claim(session, device):
    \"\"\"Pin `session` to `device`, or refuse.\"\"\"
    pinned = session["pinned"]
    if pinned is None or pinned == device:
        return {"pinned": device}
    raise RuntimeError("pinned elsewhere")""",
    variant_two="""def claim(session, device):
    \"\"\"Pin `session` to `device`, or refuse.\"\"\"
    pinned = session["pinned"]
    held_by_another = pinned is not None and pinned != device
    if held_by_another:
        raise RuntimeError("pinned elsewhere")
    return {"pinned": device}""",
    variant_three="""def claim(session, device):
    \"\"\"Pin `session` to `device`, or refuse.\"\"\"
    pinned = session["pinned"]
    if pinned == device:
        return {"pinned": device}
    raise RuntimeError("pinned elsewhere")""",
    variant_four="""def claim(session, device):
    \"\"\"Pin `session` to `device`, or refuse.\"\"\"
    pinned = session["pinned"]
    if pinned is None:
        return {"pinned": device}
    if pinned != device:
        raise RuntimeError("pinned elsewhere")
    raise RuntimeError("pinned elsewhere")""",
    visible_test=_test_module(
        "session_pin",
        "Published contract for pinning a session to a device.",
        """
import pytest

from session_pin import claim


def test_another_device_is_refused() -> None:
    with pytest.raises(RuntimeError):
        claim({"pinned": "d1"}, "d2")


def test_a_third_device_is_refused_too() -> None:
    with pytest.raises(RuntimeError):
        claim({"pinned": "d1"}, "d3")
""",
    ),
    hidden_test=_test_module(
        "session_pin",
        "The part of the contract the published tests do not state.",
        """
import pytest

from session_pin import claim


def test_another_device_is_refused() -> None:
    with pytest.raises(RuntimeError):
        claim({"pinned": "d1"}, "d2")


def test_the_holding_device_may_claim_again() -> None:
    assert claim({"pinned": "d1"}, "d1") == {"pinned": "d1"}


def test_an_unclaimed_session_accepts_any_device() -> None:
    assert claim({"pinned": None}, "d1") == {"pinned": "d1"}
""",
    ),
)

_G057 = D2TaskSpec(
    template_id="d6_state.warm_pool",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-warm-pool",
    module="warm_pool",
    module_doc="Returning a worker to a warm pool that holds only so many.",
    issue=(
        "return_worker() is documented to put a worker back in the warm pool unless the pool is "
        "full. Callers report that a worker already in the pool is put in a second time, and "
        "that returning a worker to a full pool turns the oldest one out instead of letting the "
        "newcomer go."
    ),
    expected=(
        "return_worker(pool, worker) returns the pool with the worker added at the end. A "
        "worker already in the pool changes nothing. When the pool already holds its cap, the "
        "returning worker is let go and the pool is left as it was."
    ),
    baseline_reason=(
        "it appends without looking whether the worker is there and it drops the front of the "
        "pool to make room"
    ),
    edge_cases=(
        "a worker already in the pool is not added twice",
        "a full pool lets the newcomer go rather than the oldest",
    ),
    baseline="""def return_worker(pool, worker):
    \"\"\"Put `worker` back in the warm pool.\"\"\"
    cap = pool["cap"]
    warm = [*pool["warm"], worker]
    while len(warm) > cap:
        warm.pop(0)
    return {"cap": cap, "warm": warm}""",
    variant_one="""def return_worker(pool, worker):
    \"\"\"Put `worker` back in the warm pool.\"\"\"
    cap = pool["cap"]
    warm = list(pool["warm"])
    if worker in warm or len(warm) >= cap:
        return {"cap": cap, "warm": warm}
    warm.append(worker)
    return {"cap": cap, "warm": warm}""",
    variant_two="""def return_worker(pool, worker):
    \"\"\"Put `worker` back in the warm pool.\"\"\"
    cap = pool["cap"]
    warm = list(pool["warm"])
    room = len(warm) < cap
    fresh = worker not in warm
    if room and fresh:
        warm = [*warm, worker]
    return {"cap": cap, "warm": warm}""",
    variant_three="""def return_worker(pool, worker):
    \"\"\"Put `worker` back in the warm pool.\"\"\"
    cap = pool["cap"]
    warm = list(pool["warm"])
    if worker in warm:
        return {"cap": cap, "warm": warm}
    warm.append(worker)
    while len(warm) > cap:
        warm.pop(0)
    return {"cap": cap, "warm": warm}""",
    variant_four="""def return_worker(pool, worker):
    \"\"\"Put `worker` back in the warm pool.\"\"\"
    cap = pool["cap"]
    warm = list(pool["warm"])
    if len(warm) >= cap:
        return {"cap": cap, "warm": warm}
    warm.append(worker)
    return {"cap": cap, "warm": warm}""",
    visible_test=_test_module(
        "warm_pool",
        "Published contract for returning a worker to the warm pool.",
        """
def test_a_worker_goes_back_into_a_pool_with_room() -> None:
    assert return_worker({"cap": 3, "warm": ["a"]}, "b") == {"cap": 3, "warm": ["a", "b"]}


def test_the_first_worker_starts_the_pool() -> None:
    assert return_worker({"cap": 2, "warm": []}, "a") == {"cap": 2, "warm": ["a"]}
""",
        imports="from warm_pool import return_worker\n",
    ),
    hidden_test=_test_module(
        "warm_pool",
        "The part of the contract the published tests do not state.",
        """
def test_a_worker_goes_back_into_a_pool_with_room() -> None:
    assert return_worker({"cap": 3, "warm": ["a"]}, "b") == {"cap": 3, "warm": ["a", "b"]}


def test_a_worker_already_pooled_is_not_added_twice() -> None:
    assert return_worker({"cap": 3, "warm": ["a"]}, "a") == {"cap": 3, "warm": ["a"]}


def test_a_full_pool_lets_the_newcomer_go() -> None:
    assert return_worker({"cap": 2, "warm": ["a", "b"]}, "c") == {
        "cap": 2,
        "warm": ["a", "b"],
    }
""",
        imports="from warm_pool import return_worker\n",
    ),
)

_G058 = D2TaskSpec(
    template_id="d6_state.first_writer",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-first-writer",
    module="first_writer",
    module_doc="Letting the first writer of a field win, and objecting to the second.",
    issue=(
        "write_once() is documented to let the first writer of a field win. Callers report that "
        "writing the very same value a second time is treated as a conflict, and that a field "
        "someone deliberately wrote as nothing is treated as though nobody had written it."
    ),
    expected=(
        "write_once(record, field, value) returns the record with the field written. Writing "
        "the same value again changes nothing. Writing a different value over one already there "
        "raises RuntimeError. A field written as None was written."
    ),
    baseline_reason=(
        "it objects to any second write, and it decides a field is unwritten when its value is None"
    ),
    edge_cases=(
        "writing the same value again changes nothing",
        "a field written as None counts as written",
    ),
    baseline="""def write_once(record, field, value):
    \"\"\"Write `field` if nobody has written it.\"\"\"
    written = dict(record)
    if written.get(field) is not None:
        raise RuntimeError(field)
    written[field] = value
    return written""",
    variant_one="""def write_once(record, field, value):
    \"\"\"Write `field` if nobody has written it.\"\"\"
    written = dict(record)
    if field in written:
        if written[field] != value:
            raise RuntimeError(field)
        return written
    written[field] = value
    return written""",
    variant_two="""def write_once(record, field, value):
    \"\"\"Write `field` if nobody has written it.\"\"\"
    written = dict(record)
    already = field in written
    if already and written[field] != value:
        raise RuntimeError(field)
    written[field] = value
    return written""",
    variant_three="""def write_once(record, field, value):
    \"\"\"Write `field` if nobody has written it.\"\"\"
    written = dict(record)
    if written.get(field) is not None and written[field] != value:
        raise RuntimeError(field)
    written[field] = value
    return written""",
    variant_four="""def write_once(record, field, value):
    \"\"\"Write `field` if nobody has written it.\"\"\"
    written = dict(record)
    if field in written:
        raise RuntimeError(field)
    written[field] = value
    return written""",
    visible_test=_test_module(
        "first_writer",
        "Published contract for letting the first writer win.",
        """
import pytest

from first_writer import write_once


def test_the_first_writer_wins() -> None:
    assert write_once({}, "a", 1) == {"a": 1}


def test_a_second_writer_with_another_value_is_refused() -> None:
    with pytest.raises(RuntimeError):
        write_once({"a": 1}, "a", 2)
""",
    ),
    hidden_test=_test_module(
        "first_writer",
        "The part of the contract the published tests do not state.",
        """
import pytest

from first_writer import write_once


def test_the_first_writer_wins() -> None:
    assert write_once({}, "a", 1) == {"a": 1}


def test_writing_the_same_value_again_changes_nothing() -> None:
    assert write_once({"a": 1}, "a", 1) == {"a": 1}


def test_a_field_written_as_nothing_counts_as_written() -> None:
    with pytest.raises(RuntimeError):
        write_once({"a": None}, "a", 5)
""",
    ),
)

_G059 = D2TaskSpec(
    template_id="d6_boundary.outer_fence",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-outer-fence",
    module="outer_fence",
    module_doc="Taking the outermost values at each end of a series.",
    issue=(
        "outer_fence() is documented to take a given number of values from each end of a "
        "series. Callers report that a series too short for both ends returns some of its "
        "values twice, and that asking for none of them returns all of them."
    ),
    expected=(
        "outer_fence(values, count) returns the first count values followed by the last count, "
        "with no value appearing twice when the two ends meet or overlap. A count of zero "
        "returns nothing."
    ),
    baseline_reason=(
        "it concatenates the two slices without noticing that they overlap, and its slice from "
        "the end returns the whole series when the count is zero"
    ),
    edge_cases=(
        "the ends do not repeat a value when they overlap",
        "a count of zero returns nothing",
    ),
    baseline="""def outer_fence(values, count):
    \"\"\"Return the outermost `count` values at each end.\"\"\"
    return list(values[:count]) + list(values[-count:])""",
    variant_one="""def outer_fence(values, count):
    \"\"\"Return the outermost `count` values at each end.\"\"\"
    if count <= 0:
        return []
    if count * 2 >= len(values):
        return list(values)
    return list(values[:count]) + list(values[len(values) - count :])""",
    variant_two="""def outer_fence(values, count):
    \"\"\"Return the outermost `count` values at each end.\"\"\"
    total = len(values)
    wanted = set()
    for position in range(total):
        if position < count or position >= total - count:
            wanted.add(position)
    return [values[position] for position in sorted(wanted)]""",
    variant_three="""def outer_fence(values, count):
    \"\"\"Return the outermost `count` values at each end.\"\"\"
    if count * 2 >= len(values):
        return list(values)
    return list(values[:count]) + list(values[-count:])""",
    variant_four="""def outer_fence(values, count):
    \"\"\"Return the outermost `count` values at each end.\"\"\"
    if count <= 0:
        return []
    return list(values[:count]) + list(values[-count:])""",
    visible_test=_test_module(
        "outer_fence",
        "Published contract for taking the outermost values.",
        """
def test_both_ends_are_taken() -> None:
    assert outer_fence([1, 2, 3, 4, 5], 2) == [1, 2, 4, 5]


def test_one_from_each_end_is_taken() -> None:
    assert outer_fence([1, 2, 3, 4], 1) == [1, 4]
""",
        imports="from outer_fence import outer_fence\n",
    ),
    hidden_test=_test_module(
        "outer_fence",
        "The part of the contract the published tests do not state.",
        """
def test_both_ends_are_taken() -> None:
    assert outer_fence([1, 2, 3, 4, 5], 2) == [1, 2, 4, 5]


def test_overlapping_ends_repeat_no_value() -> None:
    assert outer_fence([1, 2, 3], 2) == [1, 2, 3]


def test_a_count_of_zero_returns_nothing() -> None:
    assert outer_fence([1, 2, 3], 0) == []
""",
        imports="from outer_fence import outer_fence\n",
    ),
)

_G060 = D2TaskSpec(
    template_id="d6_numeric.harmonic_mean",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-harmonic-mean",
    module="harmonic_mean",
    module_doc="Averaging rates the way rates have to be averaged.",
    issue=(
        "harmonic_mean() is documented to average a series of rates and report it to three "
        "places. Callers report that a rate of zero brings the whole call down with a "
        "ZeroDivisionError instead of being refused, and that the third place is cut off rather "
        "than rounded."
    ),
    expected=(
        "harmonic_mean(values) returns the count divided by the sum of the reciprocals, rounded "
        "to three places. A value of zero raises ValueError, because a rate of zero has no "
        "reciprocal. An empty series raises ValueError too."
    ),
    baseline_reason=(
        "it takes the reciprocals before checking for a zero, and it cuts the result at three "
        "places instead of rounding it"
    ),
    edge_cases=(
        "a value of zero is refused",
        "the third place is rounded, not cut off",
    ),
    baseline="""def harmonic_mean(values):
    \"\"\"Return the harmonic mean of `values`, to three places.\"\"\"
    if not values:
        raise ValueError("an empty series has no mean")
    total = sum(1 / value for value in values)
    return int(len(values) / total * 1000) / 1000""",
    variant_one="""def harmonic_mean(values):
    \"\"\"Return the harmonic mean of `values`, to three places.\"\"\"
    if not values:
        raise ValueError("an empty series has no mean")
    if any(value == 0 for value in values):
        raise ValueError("a rate of zero has no reciprocal")
    total = sum(1 / value for value in values)
    return round(len(values) / total, 3)""",
    variant_two="""def harmonic_mean(values):
    \"\"\"Return the harmonic mean of `values`, to three places.\"\"\"
    if not values:
        raise ValueError("an empty series has no mean")
    total = 0.0
    for value in values:
        if not value:
            raise ValueError("a rate of zero has no reciprocal")
        total += 1 / value
    return round(len(values) / total, 3)""",
    variant_three="""def harmonic_mean(values):
    \"\"\"Return the harmonic mean of `values`, to three places.\"\"\"
    if not values:
        raise ValueError("an empty series has no mean")
    if any(value == 0 for value in values):
        raise ValueError("a rate of zero has no reciprocal")
    total = sum(1 / value for value in values)
    return int(len(values) / total * 1000) / 1000""",
    variant_four="""def harmonic_mean(values):
    \"\"\"Return the harmonic mean of `values`, to three places.\"\"\"
    if not values:
        raise ValueError("an empty series has no mean")
    total = sum(1 / value for value in values)
    return round(len(values) / total, 3)""",
    visible_test=_test_module(
        "harmonic_mean",
        "Published contract for averaging rates.",
        """
import pytest

from harmonic_mean import harmonic_mean


def test_rates_average_harmonically() -> None:
    assert harmonic_mean([1, 2, 4]) == 1.714


def test_an_empty_series_is_refused() -> None:
    with pytest.raises(ValueError):
        harmonic_mean([])
""",
    ),
    hidden_test=_test_module(
        "harmonic_mean",
        "The part of the contract the published tests do not state.",
        """
import pytest

from harmonic_mean import harmonic_mean


def test_rates_average_harmonically() -> None:
    assert harmonic_mean([1, 2, 4]) == 1.714


def test_a_rate_of_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        harmonic_mean([1, 0])


def test_the_third_place_is_rounded() -> None:
    assert harmonic_mean([1, 2, 5]) == 1.765
""",
    ),
)

_G061 = D2TaskSpec(
    template_id="d6_boundary.ring_neighbours",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-ring-neighbours",
    module="ring_neighbours",
    module_doc="Naming the two places either side of a position on a ring.",
    issue=(
        "ring_neighbours() is documented to name the places either side of a position on a "
        "ring. Callers report that the place before the first one comes back as minus one "
        "rather than the last place on the ring, and that a ring of no places fails with a "
        "ZeroDivisionError instead of being refused."
    ),
    expected=(
        "ring_neighbours(count, position) returns the places before and after position on a "
        "ring of count places, wrapping at both ends. A ring of no places raises ValueError, "
        "because there is nothing to stand either side of."
    ),
    baseline_reason=(
        "it wraps only the place after, and it divides by the count before checking that there "
        "is one"
    ),
    edge_cases=(
        "the place before the first one is the last on the ring",
        "a ring of no places is refused",
    ),
    baseline="""def ring_neighbours(count, position):
    \"\"\"Return the places either side of `position` on a ring of `count`.\"\"\"
    return position - 1, (position + 1) % count""",
    variant_one="""def ring_neighbours(count, position):
    \"\"\"Return the places either side of `position` on a ring of `count`.\"\"\"
    if count <= 0:
        raise ValueError("a ring of no places has no neighbours")
    return (position - 1) % count, (position + 1) % count""",
    variant_two="""def ring_neighbours(count, position):
    \"\"\"Return the places either side of `position` on a ring of `count`.\"\"\"
    if not count > 0:
        raise ValueError("a ring of no places has no neighbours")
    before = position - 1 if position else count - 1
    after = position + 1 if position + 1 < count else 0
    return before, after""",
    variant_three="""def ring_neighbours(count, position):
    \"\"\"Return the places either side of `position` on a ring of `count`.\"\"\"
    return (position - 1) % count, (position + 1) % count""",
    variant_four="""def ring_neighbours(count, position):
    \"\"\"Return the places either side of `position` on a ring of `count`.\"\"\"
    if count <= 0:
        raise ValueError("a ring of no places has no neighbours")
    return position - 1, (position + 1) % count""",
    visible_test=_test_module(
        "ring_neighbours",
        "Published contract for the places either side of a position.",
        """
def test_the_middle_of_the_ring_has_plain_neighbours() -> None:
    assert ring_neighbours(5, 2) == (1, 3)


def test_the_place_after_the_last_wraps_to_the_first() -> None:
    assert ring_neighbours(4, 3) == (2, 0)
""",
        imports="from ring_neighbours import ring_neighbours\n",
    ),
    hidden_test=_test_module(
        "ring_neighbours",
        "The part of the contract the published tests do not state.",
        """
import pytest

from ring_neighbours import ring_neighbours


def test_the_middle_of_the_ring_has_plain_neighbours() -> None:
    assert ring_neighbours(5, 2) == (1, 3)


def test_the_place_before_the_first_is_the_last() -> None:
    assert ring_neighbours(5, 0) == (4, 1)


def test_a_ring_of_no_places_is_refused() -> None:
    with pytest.raises(ValueError):
        ring_neighbours(0, 0)
""",
    ),
)

_G062 = D2TaskSpec(
    template_id="d6_boundary.fence_gaps",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-fence-gaps",
    module="fence_gaps",
    module_doc="Finding the free stretches a set of taken places leaves behind.",
    issue=(
        "fence_gaps() is documented to report the free stretches between the taken places. "
        "Callers report that a free stretch running to the far end is never reported, and that "
        "taken places handed over out of order produce nonsense."
    ),
    expected=(
        "fence_gaps(taken, total) returns one (start, length) pair for each run of free places "
        "below total, including a run that reaches the far end. The taken places may arrive in "
        "any order."
    ),
    baseline_reason=(
        "it reports a stretch only when it meets the next taken place, so a trailing stretch "
        "meets nothing, and it walks the taken places in the order they arrive"
    ),
    edge_cases=(
        "a free stretch reaching the far end is reported",
        "the taken places may arrive in any order",
    ),
    baseline="""def fence_gaps(taken, total):
    \"\"\"Return the free stretches the taken places leave behind.\"\"\"
    gaps = []
    start = 0
    for place in taken:
        if place > start:
            gaps.append((start, place - start))
        start = place + 1
    return gaps""",
    variant_one="""def fence_gaps(taken, total):
    \"\"\"Return the free stretches the taken places leave behind.\"\"\"
    gaps = []
    start = 0
    for place in sorted(taken):
        if place > start:
            gaps.append((start, place - start))
        start = place + 1
    if start < total:
        gaps.append((start, total - start))
    return gaps""",
    variant_two="""def fence_gaps(taken, total):
    \"\"\"Return the free stretches the taken places leave behind.\"\"\"
    busy = set(taken)
    gaps = []
    run = 0
    for place in range(total):
        if place in busy:
            if run:
                gaps.append((place - run, run))
            run = 0
        else:
            run += 1
    if run:
        gaps.append((total - run, run))
    return gaps""",
    variant_three="""def fence_gaps(taken, total):
    \"\"\"Return the free stretches the taken places leave behind.\"\"\"
    gaps = []
    start = 0
    for place in taken:
        if place > start:
            gaps.append((start, place - start))
        start = place + 1
    if start < total:
        gaps.append((start, total - start))
    return gaps""",
    variant_four="""def fence_gaps(taken, total):
    \"\"\"Return the free stretches the taken places leave behind.\"\"\"
    gaps = []
    start = 0
    for place in sorted(taken):
        if place > start:
            gaps.append((start, place - start))
        start = place + 1
    return gaps""",
    visible_test=_test_module(
        "fence_gaps",
        "Published contract for the free stretches between taken places.",
        """
def test_the_stretches_between_taken_places_are_reported() -> None:
    assert fence_gaps([1, 3], 4) == [(0, 1), (2, 1)]


def test_a_full_fence_leaves_no_stretch() -> None:
    assert fence_gaps([0, 1], 2) == []
""",
        imports="from fence_gaps import fence_gaps\n",
    ),
    hidden_test=_test_module(
        "fence_gaps",
        "The part of the contract the published tests do not state.",
        """
def test_the_stretches_between_taken_places_are_reported() -> None:
    assert fence_gaps([1, 3], 4) == [(0, 1), (2, 1)]


def test_a_stretch_reaching_the_far_end_is_reported() -> None:
    assert fence_gaps([0], 3) == [(1, 2)]


def test_the_taken_places_may_arrive_in_any_order() -> None:
    assert fence_gaps([3, 1], 4) == [(0, 1), (2, 1)]
""",
        imports="from fence_gaps import fence_gaps\n",
    ),
)

_G063 = D2TaskSpec(
    template_id="d6_boundary.crest_positions",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-crest-positions",
    module="crest_positions",
    module_doc="Finding where a series crests, including at its ends and across its plateaus.",
    issue=(
        "crest_positions() is documented to find where a series crests. Callers report that a "
        "series beginning or ending on its highest reading reports no crest there, and that a "
        "flat crest spanning two readings is reported twice."
    ),
    expected=(
        "crest_positions(values) returns the positions where the series crests: a reading "
        "strictly above the one before it and at least the one after. A reading at either end "
        "crests when it beats its single neighbour, and a flat crest is reported at its first "
        "position only."
    ),
    baseline_reason=(
        "it looks only between the ends, and it compares the reading before with a "
        "greater-or-equal, so both halves of a flat crest qualify"
    ),
    edge_cases=(
        "a series cresting at an end reports it",
        "a flat crest is reported once",
    ),
    baseline="""def crest_positions(values):
    \"\"\"Return the positions where `values` crests.\"\"\"
    crests = []
    for position in range(1, len(values) - 1):
        if values[position] >= values[position - 1] and values[position] >= values[position + 1]:
            crests.append(position)
    return crests""",
    variant_one="""def crest_positions(values):
    \"\"\"Return the positions where `values` crests.\"\"\"
    crests = []
    for position, value in enumerate(values):
        rises = position == 0 or value > values[position - 1]
        holds = position == len(values) - 1 or value >= values[position + 1]
        if rises and holds:
            crests.append(position)
    return crests""",
    variant_two="""def crest_positions(values):
    \"\"\"Return the positions where `values` crests.\"\"\"
    crests = []
    last = len(values) - 1
    for position in range(len(values)):
        before = values[position - 1] if position else None
        after = values[position + 1] if position < last else None
        if before is not None and not values[position] > before:
            continue
        if after is not None and not values[position] >= after:
            continue
        crests.append(position)
    return crests""",
    variant_three="""def crest_positions(values):
    \"\"\"Return the positions where `values` crests.\"\"\"
    crests = []
    for position, value in enumerate(values):
        rises = position == 0 or value >= values[position - 1]
        holds = position == len(values) - 1 or value >= values[position + 1]
        if rises and holds:
            crests.append(position)
    return crests""",
    variant_four="""def crest_positions(values):
    \"\"\"Return the positions where `values` crests.\"\"\"
    crests = []
    for position in range(1, len(values) - 1):
        if values[position] > values[position - 1] and values[position] >= values[position + 1]:
            crests.append(position)
    return crests""",
    visible_test=_test_module(
        "crest_positions",
        "Published contract for finding where a series crests.",
        """
def test_a_crest_between_the_ends_is_found() -> None:
    assert crest_positions([1, 3, 2]) == [1]


def test_a_rising_series_crests_before_it_falls() -> None:
    assert crest_positions([1, 2, 3, 1]) == [2]
""",
        imports="from crest_positions import crest_positions\n",
    ),
    hidden_test=_test_module(
        "crest_positions",
        "The part of the contract the published tests do not state.",
        """
def test_a_crest_between_the_ends_is_found() -> None:
    assert crest_positions([1, 3, 2]) == [1]


def test_a_series_cresting_at_an_end_reports_it() -> None:
    assert crest_positions([5, 1, 2]) == [0, 2]


def test_a_flat_crest_is_reported_once() -> None:
    assert crest_positions([1, 3, 3, 1]) == [1]
""",
        imports="from crest_positions import crest_positions\n",
    ),
)

_G064 = D2TaskSpec(
    template_id="d6_transform.dense_rows",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-dense-rows",
    module="dense_rows",
    module_doc="Laying scattered cells out as full rows, filling what nobody wrote.",
    issue=(
        "densify() is documented to lay scattered cells out as full rows. Callers report that a "
        "cell holding zero comes back as the filler instead of the zero somebody wrote, and "
        "that a cell naming a column beyond the row's width fails with an IndexError rather "
        "than being refused."
    ),
    expected=(
        "densify(cells, width, filler) returns one row per row index up to the highest named, "
        "each of width places, holding the value of every cell written there and the filler "
        "elsewhere. A value of zero is a value. A column outside the width raises ValueError."
    ),
    baseline_reason=(
        "it writes a cell only when its value is truthy and it indexes the row without checking "
        "the column against the width"
    ),
    edge_cases=(
        "a cell holding zero is written",
        "a column outside the width is refused",
    ),
    baseline="""def densify(cells, width, filler):
    \"\"\"Lay scattered cells out as full rows.\"\"\"
    if not cells:
        return []
    height = max(row for row, _column, _value in cells) + 1
    grid = [[filler] * width for _ in range(height)]
    for row, column, value in cells:
        if value:
            grid[row][column] = value
    return grid""",
    variant_one="""def densify(cells, width, filler):
    \"\"\"Lay scattered cells out as full rows.\"\"\"
    if not cells:
        return []
    height = max(row for row, _column, _value in cells) + 1
    grid = [[filler] * width for _ in range(height)]
    for row, column, value in cells:
        if not 0 <= column < width:
            raise ValueError(column)
        grid[row][column] = value
    return grid""",
    variant_two="""def densify(cells, width, filler):
    \"\"\"Lay scattered cells out as full rows.\"\"\"
    if not cells:
        return []
    written = {}
    for row, column, value in cells:
        if column < 0 or column >= width:
            raise ValueError(column)
        written[(row, column)] = value
    height = max(row for row, _column in written) + 1
    return [
        [written.get((row, column), filler) for column in range(width)]
        for row in range(height)
    ]""",
    variant_three="""def densify(cells, width, filler):
    \"\"\"Lay scattered cells out as full rows.\"\"\"
    if not cells:
        return []
    height = max(row for row, _column, _value in cells) + 1
    grid = [[filler] * width for _ in range(height)]
    for row, column, value in cells:
        grid[row][column] = value
    return grid""",
    variant_four="""def densify(cells, width, filler):
    \"\"\"Lay scattered cells out as full rows.\"\"\"
    if not cells:
        return []
    height = max(row for row, _column, _value in cells) + 1
    grid = [[filler] * width for _ in range(height)]
    for row, column, value in cells:
        if not 0 <= column < width:
            raise ValueError(column)
        if value:
            grid[row][column] = value
    return grid""",
    visible_test=_test_module(
        "dense_rows",
        "Published contract for laying scattered cells out as rows.",
        """
def test_scattered_cells_become_full_rows() -> None:
    assert densify([(0, 0, 5), (1, 1, 7)], 2, 0) == [[5, 0], [0, 7]]


def test_no_cells_make_no_rows() -> None:
    assert densify([], 3, 0) == []
""",
        imports="from dense_rows import densify\n",
    ),
    hidden_test=_test_module(
        "dense_rows",
        "The part of the contract the published tests do not state.",
        """
import pytest

from dense_rows import densify


def test_scattered_cells_become_full_rows() -> None:
    assert densify([(0, 0, 5), (1, 1, 7)], 2, 0) == [[5, 0], [0, 7]]


def test_a_cell_holding_zero_is_written() -> None:
    assert densify([(0, 0, 0)], 2, 9) == [[0, 9]]


def test_a_column_outside_the_width_is_refused() -> None:
    with pytest.raises(ValueError):
        densify([(0, 5, 1)], 2, 0)
""",
    ),
)

_G065 = D2TaskSpec(
    template_id="d6_transform.bucket_by_prefix",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-bucket-by-prefix",
    module="bucket_by_prefix",
    module_doc="Gathering names under the opening characters they share.",
    issue=(
        "bucket_by_prefix() is documented to gather names under the opening characters they "
        "share. Callers report that a name shorter than the opening it is bucketed by vanishes "
        "altogether, and that the buckets come back in whatever order the names arrived."
    ),
    expected=(
        "bucket_by_prefix(names, length) returns (bucket, names) pairs sorted by bucket, where "
        "the bucket is a name's first length characters. A name shorter than that is bucketed "
        "under the whole of itself rather than dropped."
    ),
    baseline_reason=(
        "it skips a name too short to fill the opening and it returns the buckets in the order "
        "they were first seen"
    ),
    edge_cases=(
        "a name shorter than the opening is bucketed under itself",
        "the buckets come back sorted",
    ),
    baseline="""def bucket_by_prefix(names, length):
    \"\"\"Gather `names` under their first `length` characters.\"\"\"
    buckets = {}
    for name in names:
        if len(name) < length:
            continue
        buckets.setdefault(name[:length], []).append(name)
    return list(buckets.items())""",
    variant_one="""def bucket_by_prefix(names, length):
    \"\"\"Gather `names` under their first `length` characters.\"\"\"
    buckets = {}
    for name in names:
        buckets.setdefault(name[:length], []).append(name)
    return sorted(buckets.items())""",
    variant_two="""def bucket_by_prefix(names, length):
    \"\"\"Gather `names` under their first `length` characters.\"\"\"
    openings = sorted({name[:length] for name in names})
    return [
        (opening, [name for name in names if name[:length] == opening])
        for opening in openings
    ]""",
    variant_three="""def bucket_by_prefix(names, length):
    \"\"\"Gather `names` under their first `length` characters.\"\"\"
    buckets = {}
    for name in names:
        buckets.setdefault(name[:length], []).append(name)
    return list(buckets.items())""",
    variant_four="""def bucket_by_prefix(names, length):
    \"\"\"Gather `names` under their first `length` characters.\"\"\"
    buckets = {}
    for name in names:
        if len(name) < length:
            continue
        buckets.setdefault(name[:length], []).append(name)
    return sorted(buckets.items())""",
    visible_test=_test_module(
        "bucket_by_prefix",
        "Published contract for gathering names by their opening.",
        """
def test_names_gather_under_their_opening() -> None:
    assert bucket_by_prefix(["abc", "abd", "xyz"], 2) == [
        ("ab", ["abc", "abd"]),
        ("xy", ["xyz"]),
    ]


def test_one_name_makes_one_bucket() -> None:
    assert bucket_by_prefix(["hello"], 2) == [("he", ["hello"])]
""",
        imports="from bucket_by_prefix import bucket_by_prefix\n",
    ),
    hidden_test=_test_module(
        "bucket_by_prefix",
        "The part of the contract the published tests do not state.",
        """
def test_names_gather_under_their_opening() -> None:
    assert bucket_by_prefix(["abc", "abd", "xyz"], 2) == [
        ("ab", ["abc", "abd"]),
        ("xy", ["xyz"]),
    ]


def test_a_short_name_is_bucketed_under_itself() -> None:
    assert bucket_by_prefix(["a"], 2) == [("a", ["a"])]


def test_the_buckets_come_back_sorted() -> None:
    assert bucket_by_prefix(["xyz", "abc"], 2) == [("ab", ["abc"]), ("xy", ["xyz"])]
""",
        imports="from bucket_by_prefix import bucket_by_prefix\n",
    ),
)

_G066 = D2TaskSpec(
    template_id="d6_transform.signature_columns",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-signature-columns",
    module="signature_columns",
    module_doc="Telling the columns every row carries from the ones only some rows carry.",
    issue=(
        "signature_columns() is documented to tell the columns every row carries from the ones "
        "only some do. Callers report that a column written as nothing in one row is counted as "
        "missing from that row, and that a column appearing for the first time in a later row "
        "is not counted at all."
    ),
    expected=(
        "signature_columns(rows) returns (shared, partial): the columns present in every row, "
        "and those present in some but not all, each sorted. A column written as None is "
        "present. A column is looked for in every row, not only the first."
    ),
    baseline_reason=(
        "it takes a column written as None to be absent and it draws the whole set of columns "
        "from the first row alone"
    ),
    edge_cases=(
        "a column written as nothing is present",
        "a column appearing first in a later row is counted",
    ),
    baseline="""def signature_columns(rows):
    \"\"\"Return the columns every row carries and the ones only some carry.\"\"\"
    if not rows:
        return [], []
    present = [{name for name, value in row.items() if value is not None} for row in rows]
    shared = set(present[0])
    for names in present[1:]:
        shared &= names
    everything = set(present[0])
    return sorted(shared), sorted(everything - shared)""",
    variant_one="""def signature_columns(rows):
    \"\"\"Return the columns every row carries and the ones only some carry.\"\"\"
    if not rows:
        return [], []
    present = [set(row) for row in rows]
    shared = set(present[0])
    everything = set(present[0])
    for names in present[1:]:
        shared &= names
        everything |= names
    return sorted(shared), sorted(everything - shared)""",
    variant_two="""def signature_columns(rows):
    \"\"\"Return the columns every row carries and the ones only some carry.\"\"\"
    if not rows:
        return [], []
    counted = {}
    for row in rows:
        for name in row:
            counted[name] = counted.get(name, 0) + 1
    shared = [name for name, seen in counted.items() if seen == len(rows)]
    partial = [name for name, seen in counted.items() if seen != len(rows)]
    return sorted(shared), sorted(partial)""",
    variant_three="""def signature_columns(rows):
    \"\"\"Return the columns every row carries and the ones only some carry.\"\"\"
    if not rows:
        return [], []
    present = [set(row) for row in rows]
    shared = set(present[0])
    for names in present[1:]:
        shared &= names
    everything = set(present[0])
    return sorted(shared), sorted(everything - shared)""",
    variant_four="""def signature_columns(rows):
    \"\"\"Return the columns every row carries and the ones only some carry.\"\"\"
    if not rows:
        return [], []
    present = [{name for name, value in row.items() if value is not None} for row in rows]
    shared = set(present[0])
    everything = set(present[0])
    for names in present[1:]:
        shared &= names
        everything |= names
    return sorted(shared), sorted(everything - shared)""",
    visible_test=_test_module(
        "signature_columns",
        "Published contract for telling shared columns from partial ones.",
        """
def test_columns_in_every_row_are_shared() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert signature_columns(rows) == (["a", "b"], [])


def test_no_rows_carry_no_columns() -> None:
    assert signature_columns([]) == ([], [])
""",
        imports="from signature_columns import signature_columns\n",
    ),
    hidden_test=_test_module(
        "signature_columns",
        "The part of the contract the published tests do not state.",
        """
def test_columns_in_every_row_are_shared() -> None:
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert signature_columns(rows) == (["a", "b"], [])


def test_a_column_written_as_nothing_is_present() -> None:
    assert signature_columns([{"a": 1}, {"a": None}]) == (["a"], [])


def test_a_column_appearing_in_a_later_row_is_counted() -> None:
    assert signature_columns([{"a": 1}, {"a": 2, "b": 3}]) == (["a"], ["b"])
""",
        imports="from signature_columns import signature_columns\n",
    ),
)

_G067 = D2TaskSpec(
    template_id="d6_error.veto_tally",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-veto-tally",
    module="veto_tally",
    module_doc="Deciding a ballot in which one veto outweighs any number of approvals.",
    issue=(
        "decide() is documented to decide a ballot where a single veto blocks whatever the "
        "count. Callers report that a veto is merely counted alongside the objections and can "
        "be outvoted, and that a ballot nobody voted in comes back rejected rather than "
        "undecided."
    ),
    expected=(
        "decide(votes) returns 'blocked' when anybody vetoed, whatever else was cast; otherwise "
        "'carried' when approvals outnumber objections and 'rejected' when they do not. A "
        "ballot with no votes at all is 'no_decision'. Any other vote raises ValueError."
    ),
    baseline_reason=(
        "it folds a veto in with the objections and counts them, and it lets an empty ballot "
        "fall through to a rejection"
    ),
    edge_cases=(
        "one veto blocks whatever the count",
        "a ballot with no votes is undecided",
    ),
    baseline="""def decide(votes):
    \"\"\"Decide a ballot.\"\"\"
    approvals = 0
    objections = 0
    for vote in votes:
        if vote == "approve":
            approvals += 1
        elif vote in ("object", "veto"):
            objections += 1
        else:
            raise ValueError(vote)
    return "carried" if approvals > objections else "rejected\"""",
    variant_one="""def decide(votes):
    \"\"\"Decide a ballot.\"\"\"
    approvals = 0
    objections = 0
    vetoed = False
    for vote in votes:
        if vote == "approve":
            approvals += 1
        elif vote == "object":
            objections += 1
        elif vote == "veto":
            vetoed = True
        else:
            raise ValueError(vote)
    if vetoed:
        return "blocked"
    if not votes:
        return "no_decision"
    return "carried" if approvals > objections else "rejected\"""",
    variant_two="""ALLOWED = ("approve", "object", "veto")


def decide(votes):
    \"\"\"Decide a ballot.\"\"\"
    for vote in votes:
        if vote not in ALLOWED:
            raise ValueError(vote)
    if not votes:
        return "no_decision"
    if "veto" in votes:
        return "blocked"
    approvals = sum(1 for vote in votes if vote == "approve")
    objections = sum(1 for vote in votes if vote == "object")
    return "carried" if approvals > objections else "rejected\"""",
    variant_three="""def decide(votes):
    \"\"\"Decide a ballot.\"\"\"
    approvals = 0
    objections = 0
    vetoed = False
    for vote in votes:
        if vote == "approve":
            approvals += 1
        elif vote == "object":
            objections += 1
        elif vote == "veto":
            vetoed = True
        else:
            raise ValueError(vote)
    if vetoed:
        return "blocked"
    return "carried" if approvals > objections else "rejected\"""",
    variant_four="""def decide(votes):
    \"\"\"Decide a ballot.\"\"\"
    approvals = 0
    objections = 0
    for vote in votes:
        if vote == "approve":
            approvals += 1
        elif vote in ("object", "veto"):
            objections += 1
        else:
            raise ValueError(vote)
    if not votes:
        return "no_decision"
    return "carried" if approvals > objections else "rejected\"""",
    visible_test=_test_module(
        "veto_tally",
        "Published contract for deciding a ballot.",
        """
import pytest

from veto_tally import decide


def test_approvals_outnumbering_objections_carry_it() -> None:
    assert decide(["approve", "approve", "object"]) == "carried"


def test_a_vote_nobody_recognises_is_refused() -> None:
    with pytest.raises(ValueError):
        decide(["shrug"])
""",
    ),
    hidden_test=_test_module(
        "veto_tally",
        "The part of the contract the published tests do not state.",
        """
def test_approvals_outnumbering_objections_carry_it() -> None:
    assert decide(["approve", "approve", "object"]) == "carried"


def test_one_veto_blocks_whatever_the_count() -> None:
    assert decide(["approve", "approve", "veto"]) == "blocked"


def test_a_ballot_with_no_votes_is_undecided() -> None:
    assert decide([]) == "no_decision"
""",
        imports="from veto_tally import decide\n",
    ),
)

_G068 = D2TaskSpec(
    template_id="d6_error.severity_merge",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-severity-merge",
    module="severity_merge",
    module_doc="Combining two verdicts into the graver of the two.",
    issue=(
        "merge_severity() is documented to combine two verdicts into the graver one. Callers "
        "report that a verdict nobody declared is quietly passed over instead of refused, and "
        "that the graver of two declared verdicts is picked by the alphabet rather than by how "
        "grave they are."
    ),
    expected=(
        "merge_severity(left, right) returns the graver of the two verdicts, where the order "
        "runs info, warning, error, fatal. A verdict outside that ladder raises ValueError."
    ),
    baseline_reason=(
        "it drops a verdict it does not recognise and it compares the two as words rather than "
        "by their place on the ladder"
    ),
    edge_cases=(
        "a verdict outside the ladder is refused",
        "the graver verdict is chosen by the ladder, not the alphabet",
    ),
    baseline="""LADDER = ("info", "warning", "error", "fatal")


def merge_severity(left, right):
    \"\"\"Return the graver of two verdicts.\"\"\"
    known = [verdict for verdict in (left, right) if verdict in LADDER]
    if not known:
        return LADDER[0]
    return max(known)""",
    variant_one="""LADDER = ("info", "warning", "error", "fatal")


def merge_severity(left, right):
    \"\"\"Return the graver of two verdicts.\"\"\"
    for verdict in (left, right):
        if verdict not in LADDER:
            raise ValueError(verdict)
    return max((left, right), key=LADDER.index)""",
    variant_two="""LADDER = ("info", "warning", "error", "fatal")


def merge_severity(left, right):
    \"\"\"Return the graver of two verdicts.\"\"\"
    places = []
    for verdict in (left, right):
        if verdict not in LADDER:
            raise ValueError(verdict)
        places.append(LADDER.index(verdict))
    return LADDER[max(places)]""",
    variant_three="""LADDER = ("info", "warning", "error", "fatal")


def merge_severity(left, right):
    \"\"\"Return the graver of two verdicts.\"\"\"
    for verdict in (left, right):
        if verdict not in LADDER:
            raise ValueError(verdict)
    return max(left, right)""",
    variant_four="""LADDER = ("info", "warning", "error", "fatal")


def merge_severity(left, right):
    \"\"\"Return the graver of two verdicts.\"\"\"
    known = [verdict for verdict in (left, right) if verdict in LADDER]
    if not known:
        return LADDER[0]
    return max(known, key=LADDER.index)""",
    visible_test=_test_module(
        "severity_merge",
        "Published contract for combining two verdicts.",
        """
def test_a_warning_is_graver_than_information() -> None:
    assert merge_severity("info", "warning") == "warning"


def test_fatal_is_graver_than_an_error() -> None:
    assert merge_severity("error", "fatal") == "fatal"
""",
        imports="from severity_merge import merge_severity\n",
    ),
    hidden_test=_test_module(
        "severity_merge",
        "The part of the contract the published tests do not state.",
        """
import pytest

from severity_merge import merge_severity


def test_a_warning_is_graver_than_information() -> None:
    assert merge_severity("info", "warning") == "warning"


def test_a_verdict_outside_the_ladder_is_refused() -> None:
    with pytest.raises(ValueError):
        merge_severity("info", "bogus")


def test_the_graver_verdict_is_chosen_by_the_ladder() -> None:
    assert merge_severity("error", "info") == "error"
""",
    ),
)

_G069 = D2TaskSpec(
    template_id="d6_numeric.budget_burndown",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-budget-burndown",
    module="budget_burndown",
    module_doc="Working out how long a budget lasts at a steady rate of spending.",
    issue=(
        "days_left() is documented to say how long a budget lasts at a steady rate. Callers "
        "report that a rate of nothing brings the call down with a ZeroDivisionError instead of "
        "saying the budget never runs out, and that a rate below zero hands back a negative "
        "number of days."
    ),
    expected=(
        "days_left(total, rate) returns how many whole days the budget lasts, rounding a part "
        "day up because the budget is gone during it. A rate of zero returns None, because the "
        "budget never runs out. A rate below zero raises ValueError."
    ),
    baseline_reason=(
        "it divides before looking at the rate, so a rate of zero brings it down and a negative "
        "rate runs the sum backwards"
    ),
    edge_cases=(
        "a rate of zero never runs out",
        "a rate below zero is refused",
    ),
    baseline="""def days_left(total, rate):
    \"\"\"Return how many days `total` lasts at `rate` a day.\"\"\"
    return -(-total // rate)""",
    variant_one="""def days_left(total, rate):
    \"\"\"Return how many days `total` lasts at `rate` a day.\"\"\"
    if rate < 0:
        raise ValueError("a rate below zero spends backwards")
    if rate == 0:
        return None
    return -(-total // rate)""",
    variant_two="""def days_left(total, rate):
    \"\"\"Return how many days `total` lasts at `rate` a day.\"\"\"
    if not rate >= 0:
        raise ValueError("a rate below zero spends backwards")
    if not rate:
        return None
    days = total // rate
    if total % rate:
        days += 1
    return days""",
    variant_three="""def days_left(total, rate):
    \"\"\"Return how many days `total` lasts at `rate` a day.\"\"\"
    if rate == 0:
        return None
    return -(-total // rate)""",
    variant_four="""def days_left(total, rate):
    \"\"\"Return how many days `total` lasts at `rate` a day.\"\"\"
    if rate < 0:
        raise ValueError("a rate below zero spends backwards")
    return -(-total // rate)""",
    visible_test=_test_module(
        "budget_burndown",
        "Published contract for how long a budget lasts.",
        """
def test_a_part_day_rounds_up() -> None:
    assert days_left(10, 3) == 4


def test_an_exact_number_of_days_is_exact() -> None:
    assert days_left(9, 3) == 3
""",
        imports="from budget_burndown import days_left\n",
    ),
    hidden_test=_test_module(
        "budget_burndown",
        "The part of the contract the published tests do not state.",
        """
import pytest

from budget_burndown import days_left


def test_a_part_day_rounds_up() -> None:
    assert days_left(10, 3) == 4


def test_a_rate_of_zero_never_runs_out() -> None:
    assert days_left(10, 0) is None


def test_a_rate_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        days_left(10, -2)
""",
    ),
)

_G070 = D2TaskSpec(
    template_id="d6_numeric.signed_split",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-signed-split",
    module="signed_split",
    module_doc="Counting a series into the readings above, below and at zero.",
    issue=(
        "signed_split() is documented to count a series into the readings above zero, below "
        "zero and at it. Callers report that a reading of zero is counted among those above, "
        "and that a reading that is missing altogether is passed over instead of refused."
    ),
    expected=(
        "signed_split(values) returns (above, below, at_zero). Zero is at zero and belongs in "
        "neither of the other two. A reading of None raises ValueError, because a missing "
        "reading has no sign."
    ),
    baseline_reason=(
        "it counts anything not below zero as above it, and it skips a missing reading rather "
        "than objecting to it"
    ),
    edge_cases=(
        "a reading of zero is counted at zero",
        "a missing reading is refused",
    ),
    baseline="""def signed_split(values):
    \"\"\"Count `values` into those above, below and at zero.\"\"\"
    above = 0
    below = 0
    at_zero = 0
    for value in values:
        if value is None:
            continue
        if value >= 0:
            above += 1
        else:
            below += 1
    return above, below, at_zero""",
    variant_one="""def signed_split(values):
    \"\"\"Count `values` into those above, below and at zero.\"\"\"
    above = 0
    below = 0
    at_zero = 0
    for value in values:
        if value is None:
            raise ValueError("a missing reading has no sign")
        if value > 0:
            above += 1
        elif value < 0:
            below += 1
        else:
            at_zero += 1
    return above, below, at_zero""",
    variant_two="""def signed_split(values):
    \"\"\"Count `values` into those above, below and at zero.\"\"\"
    if any(value is None for value in values):
        raise ValueError("a missing reading has no sign")
    above = sum(1 for value in values if value > 0)
    below = sum(1 for value in values if value < 0)
    return above, below, len(values) - above - below""",
    variant_three="""def signed_split(values):
    \"\"\"Count `values` into those above, below and at zero.\"\"\"
    above = 0
    below = 0
    at_zero = 0
    for value in values:
        if value is None:
            continue
        if value > 0:
            above += 1
        elif value < 0:
            below += 1
        else:
            at_zero += 1
    return above, below, at_zero""",
    variant_four="""def signed_split(values):
    \"\"\"Count `values` into those above, below and at zero.\"\"\"
    above = 0
    below = 0
    at_zero = 0
    for value in values:
        if value is None:
            raise ValueError("a missing reading has no sign")
        if value >= 0:
            above += 1
        else:
            below += 1
    return above, below, at_zero""",
    visible_test=_test_module(
        "signed_split",
        "Published contract for counting a series by sign.",
        """
def test_readings_are_counted_by_sign() -> None:
    assert signed_split([1, -2, 3]) == (2, 1, 0)


def test_an_empty_series_counts_nothing() -> None:
    assert signed_split([]) == (0, 0, 0)
""",
        imports="from signed_split import signed_split\n",
    ),
    hidden_test=_test_module(
        "signed_split",
        "The part of the contract the published tests do not state.",
        """
import pytest

from signed_split import signed_split


def test_readings_are_counted_by_sign() -> None:
    assert signed_split([1, -2, 3]) == (2, 1, 0)


def test_a_reading_of_zero_is_counted_at_zero() -> None:
    assert signed_split([0, 1]) == (1, 0, 1)


def test_a_missing_reading_is_refused() -> None:
    with pytest.raises(ValueError):
        signed_split([1, None])
""",
    ),
)

_G071 = D2TaskSpec(
    template_id="d6_boundary.extreme_positions",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-extreme-positions",
    module="extreme_positions",
    module_doc="Naming where a series reaches its lowest and its highest.",
    issue=(
        "extreme_positions() is documented to name where a series reaches its lowest and its "
        "highest reading. Callers report that when a reading is tied the last of them is named "
        "rather than the first, and that an empty series fails with an IndexError instead of "
        "being refused."
    ),
    expected=(
        "extreme_positions(values) returns the position of the lowest reading and that of the "
        "highest, taking the first of any tie. An empty series raises ValueError, because there "
        "is no position to name."
    ),
    baseline_reason=(
        "it takes a later reading that merely equals the standing one, and it reads the first "
        "value before checking that there is one"
    ),
    edge_cases=(
        "a tie names the first of the tied positions",
        "an empty series is refused",
    ),
    baseline="""def extreme_positions(values):
    \"\"\"Return the positions of the lowest and highest readings.\"\"\"
    lowest = 0
    highest = 0
    smallest = values[0]
    largest = values[0]
    for position, value in enumerate(values):
        if value <= smallest:
            smallest = value
            lowest = position
        if value >= largest:
            largest = value
            highest = position
    return lowest, highest""",
    variant_one="""def extreme_positions(values):
    \"\"\"Return the positions of the lowest and highest readings.\"\"\"
    if not values:
        raise ValueError("an empty series has no extremes")
    lowest = 0
    highest = 0
    for position, value in enumerate(values):
        if value < values[lowest]:
            lowest = position
        if value > values[highest]:
            highest = position
    return lowest, highest""",
    variant_two="""def extreme_positions(values):
    \"\"\"Return the positions of the lowest and highest readings.\"\"\"
    if len(values) == 0:
        raise ValueError("an empty series has no extremes")
    return values.index(min(values)), values.index(max(values))""",
    variant_three="""def extreme_positions(values):
    \"\"\"Return the positions of the lowest and highest readings.\"\"\"
    lowest = 0
    highest = 0
    smallest = values[0]
    largest = values[0]
    for position, value in enumerate(values):
        if value < smallest:
            smallest = value
            lowest = position
        if value > largest:
            largest = value
            highest = position
    return lowest, highest""",
    variant_four="""def extreme_positions(values):
    \"\"\"Return the positions of the lowest and highest readings.\"\"\"
    if not values:
        raise ValueError("an empty series has no extremes")
    lowest = 0
    highest = 0
    for position, value in enumerate(values):
        if value <= values[lowest]:
            lowest = position
        if value >= values[highest]:
            highest = position
    return lowest, highest""",
    visible_test=_test_module(
        "extreme_positions",
        "Published contract for naming where a series reaches its extremes.",
        """
def test_the_lowest_and_highest_are_named() -> None:
    assert extreme_positions([3, 1, 4, 2]) == (1, 2)


def test_a_single_reading_is_both() -> None:
    assert extreme_positions([5]) == (0, 0)
""",
        imports="from extreme_positions import extreme_positions\n",
    ),
    hidden_test=_test_module(
        "extreme_positions",
        "The part of the contract the published tests do not state.",
        """
import pytest

from extreme_positions import extreme_positions


def test_the_lowest_and_highest_are_named() -> None:
    assert extreme_positions([3, 1, 4, 2]) == (1, 2)


def test_a_tie_names_the_first_of_the_tied_positions() -> None:
    assert extreme_positions([1, 3, 1]) == (0, 1)


def test_an_empty_series_is_refused() -> None:
    with pytest.raises(ValueError):
        extreme_positions([])
""",
    ),
)

_G072 = D2TaskSpec(
    template_id="d6_boundary.first_repeat_span",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d6-boundary-first-repeat-span",
    module="first_repeat_span",
    module_doc="Finding how far apart the first reading that comes round again lies.",
    issue=(
        "first_repeat_span() is documented to find the first reading that comes round again and "
        "to name where it does. Callers report that it names the last time that reading appears "
        "rather than the first time it comes back, and that a series with nothing repeated comes "
        "back as a pair of nothings instead of nothing at all."
    ),
    expected=(
        "first_repeat_span(values) returns (first, next) for the earliest reading that appears "
        "again, where next is the first position it comes back at. A series in which nothing "
        "repeats returns None."
    ),
    baseline_reason=(
        "it takes the last of the later appearances and it returns a pair of nothings when there "
        "is no repeat at all"
    ),
    edge_cases=(
        "the span reaches the first return, not the last",
        "a series with no repeat returns nothing",
    ),
    baseline="""def first_repeat_span(values):
    \"\"\"Return where the first repeated reading first comes back.\"\"\"
    for position, value in enumerate(values):
        later = [other for other in range(position + 1, len(values)) if values[other] == value]
        if later:
            return position, later[-1]
    return None, None""",
    variant_one="""def first_repeat_span(values):
    \"\"\"Return where the first repeated reading first comes back.\"\"\"
    for position, value in enumerate(values):
        for other in range(position + 1, len(values)):
            if values[other] == value:
                return position, other
    return None""",
    variant_two="""def first_repeat_span(values):
    \"\"\"Return where the first repeated reading first comes back.\"\"\"
    spans = []
    for position, value in enumerate(values):
        later = [other for other in range(position + 1, len(values)) if values[other] == value]
        if later:
            spans.append((position, later[0]))
    return spans[0] if spans else None""",
    variant_three="""def first_repeat_span(values):
    \"\"\"Return where the first repeated reading first comes back.\"\"\"
    for position, value in enumerate(values):
        later = [other for other in range(position + 1, len(values)) if values[other] == value]
        if later:
            return position, later[0]
    return None, None""",
    variant_four="""def first_repeat_span(values):
    \"\"\"Return where the first repeated reading first comes back.\"\"\"
    for position, value in enumerate(values):
        later = [other for other in range(position + 1, len(values)) if values[other] == value]
        if later:
            return position, later[-1]
    return None""",
    visible_test=_test_module(
        "first_repeat_span",
        "Published contract for finding the first reading that comes round again.",
        """
def test_the_first_repeat_is_spanned() -> None:
    assert first_repeat_span([1, 2, 1, 3]) == (0, 2)


def test_two_of_a_kind_side_by_side_span_one_step() -> None:
    assert first_repeat_span([5, 5]) == (0, 1)
""",
        imports="from first_repeat_span import first_repeat_span\n",
    ),
    hidden_test=_test_module(
        "first_repeat_span",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_repeat_is_spanned() -> None:
    assert first_repeat_span([1, 2, 1, 3]) == (0, 2)


def test_the_span_reaches_the_first_return_not_the_last() -> None:
    assert first_repeat_span([1, 2, 1, 3, 1]) == (0, 2)


def test_a_series_with_no_repeat_returns_nothing() -> None:
    assert first_repeat_span([1, 2, 3]) is None
""",
        imports="from first_repeat_span import first_repeat_span\n",
    ),
)

_G073 = D2TaskSpec(
    template_id="d6_transform.roster_pairs",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-roster-pairs",
    module="roster_pairs",
    module_doc="Pairing everybody on a roster with whoever follows them, round the loop.",
    issue=(
        "roster_pairs() is documented to pair everybody with whoever follows them, the last "
        "wrapping round to the first. Callers report that a roster naming somebody twice is "
        "paired up regardless, and that a roster of one comes back empty instead of pairing "
        "that person with themselves."
    ),
    expected=(
        "roster_pairs(names) returns one (person, follower) pair per name, the last wrapping "
        "round to the first. A roster of one pairs that person with themselves. A roster naming "
        "somebody twice raises ValueError. An empty roster makes no pairs."
    ),
    baseline_reason=(
        "it never checks for a repeated name and it gives up on a roster shorter than two"
    ),
    edge_cases=(
        "a roster naming somebody twice is refused",
        "a roster of one pairs that person with themselves",
    ),
    baseline="""def roster_pairs(names):
    \"\"\"Pair everybody with whoever follows them, round the loop.\"\"\"
    if len(names) < 2:
        return []
    return [(names[at], names[(at + 1) % len(names)]) for at in range(len(names))]""",
    variant_one="""def roster_pairs(names):
    \"\"\"Pair everybody with whoever follows them, round the loop.\"\"\"
    if len(set(names)) != len(names):
        raise ValueError("a roster names everybody once")
    if not names:
        return []
    return [(names[at], names[(at + 1) % len(names)]) for at in range(len(names))]""",
    variant_two="""def roster_pairs(names):
    \"\"\"Pair everybody with whoever follows them, round the loop.\"\"\"
    seen = []
    for name in names:
        if name in seen:
            raise ValueError("a roster names everybody once")
        seen.append(name)
    pairs = []
    for at, name in enumerate(names):
        follower = names[at + 1] if at + 1 < len(names) else names[0]
        pairs.append((name, follower))
    return pairs""",
    variant_three="""def roster_pairs(names):
    \"\"\"Pair everybody with whoever follows them, round the loop.\"\"\"
    if len(set(names)) != len(names):
        raise ValueError("a roster names everybody once")
    if len(names) < 2:
        return []
    return [(names[at], names[(at + 1) % len(names)]) for at in range(len(names))]""",
    variant_four="""def roster_pairs(names):
    \"\"\"Pair everybody with whoever follows them, round the loop.\"\"\"
    if not names:
        return []
    return [(names[at], names[(at + 1) % len(names)]) for at in range(len(names))]""",
    visible_test=_test_module(
        "roster_pairs",
        "Published contract for pairing a roster round the loop.",
        """
def test_everybody_is_paired_with_their_follower() -> None:
    assert roster_pairs(["a", "b", "c"]) == [("a", "b"), ("b", "c"), ("c", "a")]


def test_two_people_are_paired_both_ways() -> None:
    assert roster_pairs(["a", "b"]) == [("a", "b"), ("b", "a")]
""",
        imports="from roster_pairs import roster_pairs\n",
    ),
    hidden_test=_test_module(
        "roster_pairs",
        "The part of the contract the published tests do not state.",
        """
import pytest

from roster_pairs import roster_pairs


def test_everybody_is_paired_with_their_follower() -> None:
    assert roster_pairs(["a", "b", "c"]) == [("a", "b"), ("b", "c"), ("c", "a")]


def test_a_roster_naming_somebody_twice_is_refused() -> None:
    with pytest.raises(ValueError):
        roster_pairs(["a", "b", "a"])


def test_a_roster_of_one_pairs_that_person_with_themselves() -> None:
    assert roster_pairs(["a"]) == [("a", "a")]
""",
    ),
)

_G074 = D2TaskSpec(
    template_id="d6_transform.accumulate_by_key",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d6-transform-accumulate-by-key",
    module="accumulate_by_key",
    module_doc="Gathering values under their keys and saying which keys came round twice.",
    issue=(
        "accumulate() is documented to gather values under their keys and to say which keys "
        "arrived more than once. Callers report that the list of repeated keys is always empty, "
        "and that a value of nothing is dropped rather than gathered."
    ),
    expected=(
        "accumulate(pairs) returns the values gathered under each key in the order they arrived, "
        "together with the sorted keys that arrived more than once. A value of None is a value "
        "and is gathered like any other."
    ),
    baseline_reason=(
        "it never works out which keys repeated and it skips a pair whose value is None"
    ),
    edge_cases=(
        "the keys that arrived more than once are reported",
        "a value of nothing is gathered",
    ),
    baseline="""def accumulate(pairs):
    \"\"\"Gather values under their keys, and name the keys that repeated.\"\"\"
    gathered = {}
    for key, value in pairs:
        if value is None:
            continue
        gathered.setdefault(key, []).append(value)
    return gathered, []""",
    variant_one="""def accumulate(pairs):
    \"\"\"Gather values under their keys, and name the keys that repeated.\"\"\"
    gathered = {}
    for key, value in pairs:
        gathered.setdefault(key, []).append(value)
    repeated = sorted(key for key, values in gathered.items() if len(values) > 1)
    return gathered, repeated""",
    variant_two="""def accumulate(pairs):
    \"\"\"Gather values under their keys, and name the keys that repeated.\"\"\"
    gathered = {}
    repeated = set()
    for key, value in pairs:
        if key in gathered:
            repeated.add(key)
        else:
            gathered[key] = []
        gathered[key].append(value)
    return gathered, sorted(repeated)""",
    variant_three="""def accumulate(pairs):
    \"\"\"Gather values under their keys, and name the keys that repeated.\"\"\"
    gathered = {}
    for key, value in pairs:
        if value is None:
            continue
        gathered.setdefault(key, []).append(value)
    repeated = sorted(key for key, values in gathered.items() if len(values) > 1)
    return gathered, repeated""",
    variant_four="""def accumulate(pairs):
    \"\"\"Gather values under their keys, and name the keys that repeated.\"\"\"
    gathered = {}
    for key, value in pairs:
        gathered.setdefault(key, []).append(value)
    return gathered, []""",
    visible_test=_test_module(
        "accumulate_by_key",
        "Published contract for gathering values under their keys.",
        """
def test_values_gather_under_their_keys() -> None:
    assert accumulate([("a", 1), ("b", 2)]) == ({"a": [1], "b": [2]}, [])


def test_no_pairs_gather_nothing() -> None:
    assert accumulate([]) == ({}, [])
""",
        imports="from accumulate_by_key import accumulate\n",
    ),
    hidden_test=_test_module(
        "accumulate_by_key",
        "The part of the contract the published tests do not state.",
        """
def test_values_gather_under_their_keys() -> None:
    assert accumulate([("a", 1), ("b", 2)]) == ({"a": [1], "b": [2]}, [])


def test_the_keys_that_arrived_twice_are_reported() -> None:
    assert accumulate([("a", 1), ("a", 2)]) == ({"a": [1, 2]}, ["a"])


def test_a_value_of_nothing_is_gathered() -> None:
    assert accumulate([("a", None)]) == ({"a": [None]}, [])
""",
        imports="from accumulate_by_key import accumulate\n",
    ),
)

_G075 = D2TaskSpec(
    template_id="d6_error.permit_window",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-permit-window",
    module="permit_window",
    module_doc="Allowing work only inside the windows somebody declared for it.",
    issue=(
        "permit() is documented to allow work only inside the declared windows. Callers report "
        "that work attempted at the very instant a window closes is refused although the window "
        "is meant to include it, and that a window declared back to front is quietly ignored "
        "instead of being called out."
    ),
    expected=(
        "permit(now, windows) returns None when now falls inside any window, both ends "
        "included, and raises PermissionError when it falls outside them all. A window whose "
        "end precedes its start raises ValueError, because nobody can have meant it."
    ),
    baseline_reason=(
        "it treats the closing instant as outside the window, and it steps over a window "
        "declared back to front"
    ),
    edge_cases=(
        "the instant a window closes is inside it",
        "a window declared back to front is refused",
    ),
    baseline="""def permit(now, windows):
    \"\"\"Allow work only inside the declared windows.\"\"\"
    for start, end in windows:
        if start > end:
            continue
        if start <= now < end:
            return None
    raise PermissionError("outside every window")""",
    variant_one="""def permit(now, windows):
    \"\"\"Allow work only inside the declared windows.\"\"\"
    for start, end in windows:
        if start > end:
            raise ValueError("a window cannot end before it starts")
    for start, end in windows:
        if start <= now <= end:
            return None
    raise PermissionError("outside every window")""",
    variant_two="""def permit(now, windows):
    \"\"\"Allow work only inside the declared windows.\"\"\"
    inside = False
    for start, end in windows:
        if end < start:
            raise ValueError("a window cannot end before it starts")
        if start <= now <= end:
            inside = True
    if not inside:
        raise PermissionError("outside every window")
    return None""",
    variant_three="""def permit(now, windows):
    \"\"\"Allow work only inside the declared windows.\"\"\"
    for start, end in windows:
        if start > end:
            continue
        if start <= now <= end:
            return None
    raise PermissionError("outside every window")""",
    variant_four="""def permit(now, windows):
    \"\"\"Allow work only inside the declared windows.\"\"\"
    for start, end in windows:
        if start > end:
            raise ValueError("a window cannot end before it starts")
    for start, end in windows:
        if start <= now < end:
            return None
    raise PermissionError("outside every window")""",
    visible_test=_test_module(
        "permit_window",
        "Published contract for allowing work inside declared windows.",
        """
import pytest

from permit_window import permit


def test_work_inside_a_window_is_allowed() -> None:
    assert permit(5, [(1, 9)]) is None


def test_work_outside_every_window_is_refused() -> None:
    with pytest.raises(PermissionError):
        permit(20, [(1, 9)])
""",
    ),
    hidden_test=_test_module(
        "permit_window",
        "The part of the contract the published tests do not state.",
        """
import pytest

from permit_window import permit


def test_work_inside_a_window_is_allowed() -> None:
    assert permit(5, [(1, 9)]) is None


def test_the_instant_a_window_closes_is_inside_it() -> None:
    assert permit(9, [(1, 9)]) is None


def test_a_window_declared_back_to_front_is_refused() -> None:
    with pytest.raises(ValueError):
        permit(5, [(9, 1)])
""",
    ),
)

_G076 = D2TaskSpec(
    template_id="d6_error.tolerate_upto",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d6-error-tolerate-upto",
    module="tolerate_upto",
    module_doc="Letting a batch through while no more than so many of it failed.",
    issue=(
        "tolerate() is documented to let a batch through while no more than a stated number of "
        "it failed. Callers report that a batch failing exactly that many times is turned away, "
        "and that an allowance below zero is accepted as though it were none."
    ),
    expected=(
        "tolerate(outcomes, allowed) returns the values of the outcomes that succeeded, so long "
        "as no more than allowed of them failed. More failures than that raise RuntimeError. An "
        "allowance below zero raises ValueError."
    ),
    baseline_reason=(
        "it turns the batch away once the failures reach the allowance rather than pass it, and "
        "it never looks at whether the allowance makes sense"
    ),
    edge_cases=(
        "a batch failing exactly the allowance is let through",
        "an allowance below zero is refused",
    ),
    baseline="""def tolerate(outcomes, allowed):
    \"\"\"Return the successes while no more than `allowed` failed.\"\"\"
    failures = [outcome for outcome in outcomes if not outcome["ok"]]
    if len(failures) >= allowed:
        raise RuntimeError(f"{len(failures)} failed")
    return [outcome["value"] for outcome in outcomes if outcome["ok"]]""",
    variant_one="""def tolerate(outcomes, allowed):
    \"\"\"Return the successes while no more than `allowed` failed.\"\"\"
    if allowed < 0:
        raise ValueError("an allowance below zero allows nothing")
    failures = [outcome for outcome in outcomes if not outcome["ok"]]
    if len(failures) > allowed:
        raise RuntimeError(f"{len(failures)} failed")
    return [outcome["value"] for outcome in outcomes if outcome["ok"]]""",
    variant_two="""def tolerate(outcomes, allowed):
    \"\"\"Return the successes while no more than `allowed` failed.\"\"\"
    if not allowed >= 0:
        raise ValueError("an allowance below zero allows nothing")
    kept = []
    failed = 0
    for outcome in outcomes:
        if outcome["ok"]:
            kept.append(outcome["value"])
        else:
            failed += 1
    if failed > allowed:
        raise RuntimeError(f"{failed} failed")
    return kept""",
    variant_three="""def tolerate(outcomes, allowed):
    \"\"\"Return the successes while no more than `allowed` failed.\"\"\"
    failures = [outcome for outcome in outcomes if not outcome["ok"]]
    if len(failures) > allowed:
        raise RuntimeError(f"{len(failures)} failed")
    return [outcome["value"] for outcome in outcomes if outcome["ok"]]""",
    variant_four="""def tolerate(outcomes, allowed):
    \"\"\"Return the successes while no more than `allowed` failed.\"\"\"
    if allowed < 0:
        raise ValueError("an allowance below zero allows nothing")
    failures = [outcome for outcome in outcomes if not outcome["ok"]]
    if len(failures) >= allowed:
        raise RuntimeError(f"{len(failures)} failed")
    return [outcome["value"] for outcome in outcomes if outcome["ok"]]""",
    visible_test=_test_module(
        "tolerate_upto",
        "Published contract for letting a batch through despite some failures.",
        """
import pytest

from tolerate_upto import tolerate


def test_a_batch_below_the_allowance_is_let_through() -> None:
    outcomes = [
        {"ok": True, "value": 1},
        {"ok": True, "value": 2},
        {"ok": False, "value": None},
    ]
    assert tolerate(outcomes, 2) == [1, 2]


def test_a_batch_beyond_the_allowance_is_turned_away() -> None:
    outcomes = [{"ok": False, "value": None}, {"ok": False, "value": None}]
    with pytest.raises(RuntimeError):
        tolerate(outcomes, 1)
""",
    ),
    hidden_test=_test_module(
        "tolerate_upto",
        "The part of the contract the published tests do not state.",
        """
import pytest

from tolerate_upto import tolerate


def test_a_batch_below_the_allowance_is_let_through() -> None:
    outcomes = [
        {"ok": True, "value": 1},
        {"ok": True, "value": 2},
        {"ok": False, "value": None},
    ]
    assert tolerate(outcomes, 2) == [1, 2]


def test_a_batch_failing_exactly_the_allowance_is_let_through() -> None:
    outcomes = [
        {"ok": True, "value": 1},
        {"ok": False, "value": None},
        {"ok": False, "value": None},
    ]
    assert tolerate(outcomes, 2) == [1]


def test_an_allowance_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        tolerate([{"ok": True, "value": 1}], -1)
""",
    ),
)

_G077 = D2TaskSpec(
    template_id="d6_numeric.mixed_fraction",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-mixed-fraction",
    module="mixed_fraction",
    module_doc="Writing an improper fraction as a whole part and what is left over.",
    issue=(
        "mixed_fraction() is documented to write an improper fraction as a whole part and the "
        "fraction left over. Callers report that the leftover fraction is handed back "
        "unreduced, and that a denominator of nothing brings the call down with a "
        "ZeroDivisionError instead of being refused."
    ),
    expected=(
        "mixed_fraction(numerator, denominator) returns (whole, leftover_numerator, "
        "leftover_denominator) with the leftover fraction in its lowest terms and a leftover of "
        "nothing written as zero over one. A denominator of zero raises ValueError."
    ),
    baseline_reason=(
        "it hands the leftover back over the original denominator and it divides before "
        "checking that the denominator is one it can divide by"
    ),
    edge_cases=(
        "the leftover fraction comes back in its lowest terms",
        "a denominator of zero is refused",
    ),
    baseline="""from math import gcd


def mixed_fraction(numerator, denominator):
    \"\"\"Write an improper fraction as a whole part and a leftover.\"\"\"
    whole = numerator // denominator
    rest = numerator - whole * denominator
    if rest == 0:
        return whole, 0, 1
    return whole, rest, denominator""",
    variant_one="""from math import gcd


def mixed_fraction(numerator, denominator):
    \"\"\"Write an improper fraction as a whole part and a leftover.\"\"\"
    if denominator == 0:
        raise ValueError("a fraction over nothing is not a fraction")
    whole = numerator // denominator
    rest = numerator - whole * denominator
    if rest == 0:
        return whole, 0, 1
    shared = gcd(rest, denominator)
    return whole, rest // shared, denominator // shared""",
    variant_two="""from math import gcd


def mixed_fraction(numerator, denominator):
    \"\"\"Write an improper fraction as a whole part and a leftover.\"\"\"
    if not denominator:
        raise ValueError("a fraction over nothing is not a fraction")
    whole, rest = divmod(numerator, denominator)
    if not rest:
        return whole, 0, 1
    shared = gcd(abs(rest), abs(denominator))
    return whole, rest // shared, denominator // shared""",
    variant_three="""from math import gcd


def mixed_fraction(numerator, denominator):
    \"\"\"Write an improper fraction as a whole part and a leftover.\"\"\"
    whole = numerator // denominator
    rest = numerator - whole * denominator
    if rest == 0:
        return whole, 0, 1
    shared = gcd(rest, denominator)
    return whole, rest // shared, denominator // shared""",
    variant_four="""from math import gcd


def mixed_fraction(numerator, denominator):
    \"\"\"Write an improper fraction as a whole part and a leftover.\"\"\"
    if denominator == 0:
        raise ValueError("a fraction over nothing is not a fraction")
    whole = numerator // denominator
    rest = numerator - whole * denominator
    if rest == 0:
        return whole, 0, 1
    return whole, rest, denominator""",
    visible_test=_test_module(
        "mixed_fraction",
        "Published contract for writing an improper fraction.",
        """
def test_an_improper_fraction_splits_into_a_whole_and_a_leftover() -> None:
    assert mixed_fraction(7, 2) == (3, 1, 2)


def test_a_fraction_that_divides_exactly_leaves_nothing() -> None:
    assert mixed_fraction(6, 3) == (2, 0, 1)
""",
        imports="from mixed_fraction import mixed_fraction\n",
    ),
    hidden_test=_test_module(
        "mixed_fraction",
        "The part of the contract the published tests do not state.",
        """
import pytest

from mixed_fraction import mixed_fraction


def test_an_improper_fraction_splits_into_a_whole_and_a_leftover() -> None:
    assert mixed_fraction(7, 2) == (3, 1, 2)


def test_the_leftover_comes_back_in_its_lowest_terms() -> None:
    assert mixed_fraction(6, 4) == (1, 1, 2)


def test_a_denominator_of_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        mixed_fraction(1, 0)
""",
    ),
)

_G078 = D2TaskSpec(
    template_id="d6_numeric.clamp_delta",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d6-numeric-clamp-delta",
    module="clamp_delta",
    module_doc="Letting a reading move only so far in one step, whichever way it moves.",
    issue=(
        "clamp_delta() is documented to let a reading move only so far in a single step. "
        "Callers report that a reading falling a long way is let through in full while a rising "
        "one is held back, and that a limit of nothing lets the reading move anywhere at all."
    ),
    expected=(
        "clamp_delta(previous, proposed, limit) returns the proposed reading when it is within "
        "limit of the previous one, and otherwise the previous one moved by limit toward it. "
        "The limit binds a fall as tightly as a rise, and a limit of zero pins the reading."
    ),
    baseline_reason=(
        "it compares only the rise against the limit, and it reads a limit of zero as no limit "
        "at all"
    ),
    edge_cases=(
        "a fall is held to the limit as tightly as a rise",
        "a limit of zero pins the reading",
    ),
    baseline="""def clamp_delta(previous, proposed, limit):
    \"\"\"Let the reading move at most `limit` from `previous`.\"\"\"
    if not limit:
        return proposed
    if proposed - previous > limit:
        return previous + limit
    return proposed""",
    variant_one="""def clamp_delta(previous, proposed, limit):
    \"\"\"Let the reading move at most `limit` from `previous`.\"\"\"
    if proposed - previous > limit:
        return previous + limit
    if previous - proposed > limit:
        return previous - limit
    return proposed""",
    variant_two="""def clamp_delta(previous, proposed, limit):
    \"\"\"Let the reading move at most `limit` from `previous`.\"\"\"
    move = proposed - previous
    if move > limit:
        move = limit
    elif move < -limit:
        move = -limit
    return previous + move""",
    variant_three="""def clamp_delta(previous, proposed, limit):
    \"\"\"Let the reading move at most `limit` from `previous`.\"\"\"
    if not limit:
        return proposed
    if proposed - previous > limit:
        return previous + limit
    if previous - proposed > limit:
        return previous - limit
    return proposed""",
    variant_four="""def clamp_delta(previous, proposed, limit):
    \"\"\"Let the reading move at most `limit` from `previous`.\"\"\"
    if proposed - previous > limit:
        return previous + limit
    return proposed""",
    visible_test=_test_module(
        "clamp_delta",
        "Published contract for limiting how far a reading moves.",
        """
def test_a_rise_beyond_the_limit_is_held_back() -> None:
    assert clamp_delta(10, 14, 2) == 12


def test_a_move_within_the_limit_is_let_through() -> None:
    assert clamp_delta(10, 11, 2) == 11
""",
        imports="from clamp_delta import clamp_delta\n",
    ),
    hidden_test=_test_module(
        "clamp_delta",
        "The part of the contract the published tests do not state.",
        """
def test_a_rise_beyond_the_limit_is_held_back() -> None:
    assert clamp_delta(10, 14, 2) == 12


def test_a_fall_is_held_as_tightly_as_a_rise() -> None:
    assert clamp_delta(10, 4, 2) == 8


def test_a_limit_of_zero_pins_the_reading() -> None:
    assert clamp_delta(10, 14, 0) == 10
""",
        imports="from clamp_delta import clamp_delta\n",
    ),
)

_G079 = D2TaskSpec(
    template_id="d6_parsing.key_path",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d6-parsing-key-path",
    module="key_path",
    module_doc="Reading a path of names and subscripts into the steps it names.",
    issue=(
        "key_path() is documented to read a path of names and subscripts into its steps. "
        "Callers report that a subscript comes back as the characters between the brackets "
        "rather than the number it is, and that a subscript nobody closed is read as though the "
        "bracket had been there."
    ),
    expected=(
        "key_path(text) returns the steps a path names, each name as itself and each subscript "
        "as the whole number between the brackets. A bracket nobody closed raises ValueError."
    ),
    baseline_reason=(
        "it appends the characters between the brackets without reading them as a number, and "
        "it splits on the closing bracket without noticing that there was not one"
    ),
    edge_cases=(
        "a subscript comes back as a number",
        "a bracket nobody closed is refused",
    ),
    baseline="""def key_path(text):
    \"\"\"Return the steps a path of names and subscripts names.\"\"\"
    steps = []
    for chunk in text.split("."):
        while "[" in chunk:
            head, _, rest = chunk.partition("[")
            subscript, _, chunk = rest.partition("]")
            if head:
                steps.append(head)
            steps.append(subscript)
        if chunk:
            steps.append(chunk)
    return steps""",
    variant_one="""def key_path(text):
    \"\"\"Return the steps a path of names and subscripts names.\"\"\"
    steps = []
    for chunk in text.split("."):
        while "[" in chunk:
            head, _, rest = chunk.partition("[")
            subscript, closed, chunk = rest.partition("]")
            if not closed:
                raise ValueError(text)
            if head:
                steps.append(head)
            steps.append(int(subscript))
        if chunk:
            steps.append(chunk)
    return steps""",
    variant_two="""def key_path(text):
    \"\"\"Return the steps a path of names and subscripts names.\"\"\"
    if text.count("[") != text.count("]"):
        raise ValueError(text)
    steps = []
    for chunk in text.split("."):
        name, _, remainder = chunk.partition("[")
        if name:
            steps.append(name)
        while remainder:
            subscript, _, remainder = remainder.partition("]")
            steps.append(int(subscript))
            remainder = remainder.lstrip("[")
    return steps""",
    variant_three="""def key_path(text):
    \"\"\"Return the steps a path of names and subscripts names.\"\"\"
    steps = []
    for chunk in text.split("."):
        while "[" in chunk:
            head, _, rest = chunk.partition("[")
            subscript, _, chunk = rest.partition("]")
            if head:
                steps.append(head)
            steps.append(int(subscript))
        if chunk:
            steps.append(chunk)
    return steps""",
    variant_four="""def key_path(text):
    \"\"\"Return the steps a path of names and subscripts names.\"\"\"
    steps = []
    for chunk in text.split("."):
        while "[" in chunk:
            head, _, rest = chunk.partition("[")
            subscript, closed, chunk = rest.partition("]")
            if not closed:
                raise ValueError(text)
            if head:
                steps.append(head)
            steps.append(subscript)
        if chunk:
            steps.append(chunk)
    return steps""",
    visible_test=_test_module(
        "key_path",
        "Published contract for reading a path of names and subscripts.",
        """
def test_a_path_of_names_reads_as_its_names() -> None:
    assert key_path("a.b") == ["a", "b"]


def test_a_single_name_is_one_step() -> None:
    assert key_path("only") == ["only"]
""",
        imports="from key_path import key_path\n",
    ),
    hidden_test=_test_module(
        "key_path",
        "The part of the contract the published tests do not state.",
        """
import pytest

from key_path import key_path


def test_a_path_of_names_reads_as_its_names() -> None:
    assert key_path("a.b") == ["a", "b"]


def test_a_subscript_comes_back_as_a_number() -> None:
    assert key_path("a[2]") == ["a", 2]


def test_a_bracket_nobody_closed_is_refused() -> None:
    with pytest.raises(ValueError):
        key_path("a[2")
""",
    ),
)

_G080 = D2TaskSpec(
    template_id="d6_state.budget_hold",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d6-state-budget-hold",
    module="budget_hold",
    module_doc="Placing a hold against a budget, once per hold.",
    issue=(
        "place_hold() is documented to place a hold against a budget, once per hold. Callers "
        "report that placing the same hold a second time takes the money twice, and that a hold "
        "for exactly what is left is turned away although it fits."
    ),
    expected=(
        "place_hold(state, key, amount) returns the state with the hold recorded and the "
        "remaining budget reduced. A hold already recorded under that key changes nothing. A "
        "hold for more than remains raises ValueError; a hold for exactly what remains fits."
    ),
    baseline_reason=(
        "it records the hold without looking whether that key already holds, and it turns away "
        "a hold that merely equals what is left"
    ),
    edge_cases=(
        "placing the same hold again changes nothing",
        "a hold for exactly what remains fits",
    ),
    baseline="""def place_hold(state, key, amount):
    \"\"\"Place a hold of `amount` under `key`.\"\"\"
    holds = dict(state["holds"])
    remaining = state["remaining"]
    if amount >= remaining:
        raise ValueError("beyond the budget")
    holds[key] = amount
    return {"remaining": remaining - amount, "holds": holds}""",
    variant_one="""def place_hold(state, key, amount):
    \"\"\"Place a hold of `amount` under `key`.\"\"\"
    holds = dict(state["holds"])
    remaining = state["remaining"]
    if key in holds:
        return {"remaining": remaining, "holds": holds}
    if amount > remaining:
        raise ValueError("beyond the budget")
    holds[key] = amount
    return {"remaining": remaining - amount, "holds": holds}""",
    variant_two="""def place_hold(state, key, amount):
    \"\"\"Place a hold of `amount` under `key`.\"\"\"
    holds = dict(state["holds"])
    remaining = state["remaining"]
    already = key in holds
    if not already and amount > remaining:
        raise ValueError("beyond the budget")
    if already:
        return {"remaining": remaining, "holds": holds}
    return {"remaining": remaining - amount, "holds": {**holds, key: amount}}""",
    variant_three="""def place_hold(state, key, amount):
    \"\"\"Place a hold of `amount` under `key`.\"\"\"
    holds = dict(state["holds"])
    remaining = state["remaining"]
    if key in holds:
        return {"remaining": remaining, "holds": holds}
    if amount >= remaining:
        raise ValueError("beyond the budget")
    holds[key] = amount
    return {"remaining": remaining - amount, "holds": holds}""",
    variant_four="""def place_hold(state, key, amount):
    \"\"\"Place a hold of `amount` under `key`.\"\"\"
    holds = dict(state["holds"])
    remaining = state["remaining"]
    if amount > remaining:
        raise ValueError("beyond the budget")
    holds[key] = amount
    return {"remaining": remaining - amount, "holds": holds}""",
    visible_test=_test_module(
        "budget_hold",
        "Published contract for placing a hold against a budget.",
        """
import pytest

from budget_hold import place_hold


def test_a_hold_takes_its_amount_from_the_budget() -> None:
    state = {"remaining": 10, "holds": {}}
    assert place_hold(state, "h1", 3) == {"remaining": 7, "holds": {"h1": 3}}


def test_a_hold_beyond_the_budget_is_refused() -> None:
    with pytest.raises(ValueError):
        place_hold({"remaining": 10, "holds": {}}, "h2", 11)
""",
    ),
    hidden_test=_test_module(
        "budget_hold",
        "The part of the contract the published tests do not state.",
        """
def test_a_hold_takes_its_amount_from_the_budget() -> None:
    state = {"remaining": 10, "holds": {}}
    assert place_hold(state, "h1", 3) == {"remaining": 7, "holds": {"h1": 3}}


def test_placing_the_same_hold_again_changes_nothing() -> None:
    state = {"remaining": 7, "holds": {"h1": 3}}
    assert place_hold(state, "h1", 3) == {"remaining": 7, "holds": {"h1": 3}}


def test_a_hold_for_exactly_what_remains_fits() -> None:
    state = {"remaining": 5, "holds": {}}
    assert place_hold(state, "h2", 5) == {"remaining": 0, "holds": {"h2": 5}}
""",
        imports="from budget_hold import place_hold\n",
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
    _G041,
    _G042,
    _G043,
    _G044,
    _G045,
    _G046,
    _G047,
    _G049,
    _G050,
    _G051,
    _G052,
    _G053,
    _G054,
    _G055,
    _G056,
    _G057,
    _G058,
    _G059,
    _G060,
    _G061,
    _G062,
    _G063,
    _G064,
    _G065,
    _G066,
    _G067,
    _G068,
    _G069,
    _G070,
    _G071,
    _G072,
    _G073,
    _G074,
    _G075,
    _G076,
    _G077,
    _G078,
    _G079,
    _G080,
)
