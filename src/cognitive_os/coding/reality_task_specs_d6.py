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
)
