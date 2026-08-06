"""The Sprint 21D4 calibration corpus: one hundred fresh four-candidate groups.

D4 needs a hundred *independent* calibration decisions, and after the W1 erratum "independent"
has a precise meaning: distinct fitted feature vectors. A transformation of a group does not
produce one, so the only way to a hundred is to author a hundred, which is what this module is.

The spec shape is D2's `D2TaskSpec`, unchanged and deliberately so — the catalogue, the template
registry and the campaign all already agree about it, and a fourth dataclass with the same fields
under a D4 name would give them a fourth thing to agree about.

Every group here obeys the same authoring contract:

- the **baseline** passes the visible suite and fails the hidden one;
- **variant one** and **variant two** repair the contract by materially different routes and pass
  both suites;
- **variant three** fixes the first declared edge case only, **variant four** the second only, and
  both therefore pass the visible suite and fail the hidden one.

That shape is what makes a ranking decision meaningful: four candidates that a visible suite
cannot separate, and a hidden verifier that can. It is also why the visible suite must never
exercise a declared edge case — a visible test that caught the partial fixes would turn the
decision into a lookup.

Two constraints come from elsewhere in the sprint. S21D4-015 renames identifiers in the
invariance sample, so every body binds its names locally — a module-level function and its own
locals — and none reaches a name through `getattr`, `globals()` or any other reflective route,
which `correction_source.py` refuses outright. S21D4-031 proves near-clone separation over every
C3, D2, D3 and D4 body, so no two groups here are the same algorithm wearing different names.

The fixture group at the bottom is not part of the corpus. S21D4-033 spends a whole group proving
the pipeline end to end, and spending a calibration member on it would take a scored group out of
the hundred before a single number was read.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# ------------------------------------------------------------------ boundary and collections

_G001 = D2TaskSpec(
    template_id="d4_boundary.rotate_left",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-rotate-left",
    module="ring_rotation",
    module_doc="Rotating a sequence by a number of places.",
    issue=(
        "rotate_left() is documented to rotate a sequence by a number of places. Callers report "
        "that a shift larger than the sequence returns an empty list, and that rotating an empty "
        "sequence raises."
    ),
    expected=(
        "rotate_left(items, shift) moves the first shift items to the end, treats a shift larger "
        "than the sequence as its remainder, and returns an empty list for an empty sequence."
    ),
    baseline_reason="it slices with the raw shift and divides by the length without checking it",
    edge_cases=(
        "a shift larger than the sequence wraps around",
        "an empty sequence rotates to an empty sequence",
    ),
    baseline="""def rotate_left(items, shift):
    \"\"\"Return `items` rotated `shift` places to the left.\"\"\"
    collected = list(items)
    return collected[shift:] + collected[:shift]""",
    variant_one="""def rotate_left(items, shift):
    \"\"\"Return `items` rotated `shift` places to the left.\"\"\"
    collected = list(items)
    if not collected:
        return []
    offset = shift % len(collected)
    return collected[offset:] + collected[:offset]""",
    variant_two="""def rotate_left(items, shift):
    \"\"\"Return `items` rotated `shift` places to the left.\"\"\"
    collected = list(items)
    total = len(collected)
    if total == 0:
        return []
    return [collected[(position + shift) % total] for position in range(total)]""",
    variant_three="""def rotate_left(items, shift):
    \"\"\"Return `items` rotated `shift` places to the left.\"\"\"
    collected = list(items)
    offset = shift % len(collected)
    return collected[offset:] + collected[:offset]""",
    variant_four="""def rotate_left(items, shift):
    \"\"\"Return `items` rotated `shift` places to the left.\"\"\"
    collected = list(items)
    if not collected:
        return []
    return collected[shift:] + collected[:shift]""",
    visible_test=_test_module(
        "ring_rotation",
        "Published contract for rotating a sequence.",
        """
def test_a_small_shift_moves_the_head_to_the_tail() -> None:
    assert rotate_left([1, 2, 3, 4], 1) == [2, 3, 4, 1]


def test_a_zero_shift_leaves_the_sequence_alone() -> None:
    assert rotate_left([1, 2, 3], 0) == [1, 2, 3]
""",
        imports="from ring_rotation import rotate_left\n",
    ),
    hidden_test=_test_module(
        "ring_rotation",
        "The part of the contract the published tests do not state.",
        """
def test_a_small_shift_moves_the_head_to_the_tail() -> None:
    assert rotate_left([1, 2, 3, 4], 1) == [2, 3, 4, 1]


def test_a_shift_larger_than_the_sequence_wraps() -> None:
    assert rotate_left([1, 2, 3], 5) == [3, 1, 2]


def test_an_empty_sequence_rotates_to_an_empty_sequence() -> None:
    assert rotate_left([], 3) == []
""",
        imports="from ring_rotation import rotate_left\n",
    ),
)

_G002 = D2TaskSpec(
    template_id="d4_boundary.window_sums",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-window-sums",
    module="sliding_totals",
    module_doc="Totalling a sliding window over a series.",
    issue=(
        "window_sums() is documented to total every window of a given width. Callers report that "
        "a width of zero returns one zero per position instead of nothing, and that a negative "
        "width returns totals of backwards slices instead of nothing."
    ),
    expected=(
        "window_sums(values, width) returns one total per window of exactly width consecutive "
        "values, and returns an empty list for any width that is not at least one."
    ),
    baseline_reason="nothing rejects a width below one, so range() is handed a nonsense count",
    edge_cases=(
        "a width of zero yields nothing",
        "a negative width yields nothing",
    ),
    baseline="""def window_sums(values, width):
    \"\"\"Return the total of every window of `width` consecutive values.\"\"\"
    collected = list(values)
    last = len(collected) - width + 1
    return [sum(collected[start : start + width]) for start in range(last)]""",
    variant_one="""def window_sums(values, width):
    \"\"\"Return the total of every window of `width` consecutive values.\"\"\"
    collected = list(values)
    if width < 1:
        return []
    last = len(collected) - width + 1
    return [sum(collected[start : start + width]) for start in range(last)]""",
    variant_two="""def window_sums(values, width):
    \"\"\"Return the total of every window of `width` consecutive values.\"\"\"
    collected = list(values)
    totals = []
    start = 0
    while width >= 1 and start + width <= len(collected):
        totals.append(sum(collected[start : start + width]))
        start += 1
    return totals""",
    variant_three="""def window_sums(values, width):
    \"\"\"Return the total of every window of `width` consecutive values.\"\"\"
    collected = list(values)
    if width == 0:
        return []
    last = len(collected) - width + 1
    return [sum(collected[start : start + width]) for start in range(last)]""",
    variant_four="""def window_sums(values, width):
    \"\"\"Return the total of every window of `width` consecutive values.\"\"\"
    collected = list(values)
    if width < 0:
        return []
    last = len(collected) - width + 1
    return [sum(collected[start : start + width]) for start in range(last)]""",
    visible_test=_test_module(
        "sliding_totals",
        "Published contract for sliding-window totals.",
        """
def test_windows_of_two_over_four_values() -> None:
    assert window_sums([1, 2, 3, 4], 2) == [3, 5, 7]


def test_windows_of_one_are_the_values_themselves() -> None:
    assert window_sums([4, 5], 1) == [4, 5]
""",
        imports="from sliding_totals import window_sums\n",
    ),
    hidden_test=_test_module(
        "sliding_totals",
        "The part of the contract the published tests do not state.",
        """
def test_windows_of_two_over_four_values() -> None:
    assert window_sums([1, 2, 3, 4], 2) == [3, 5, 7]


def test_a_width_of_zero_yields_nothing() -> None:
    assert window_sums([1, 2], 0) == []


def test_a_negative_width_yields_nothing() -> None:
    assert window_sums([1, 2], -1) == []
""",
        imports="from sliding_totals import window_sums\n",
    ),
)

_G003 = D2TaskSpec(
    template_id="d4_boundary.split_on",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-split-on",
    module="segment_split",
    module_doc="Cutting a sequence into segments around a separator.",
    issue=(
        "split_on() is documented to cut a sequence at every separator. Callers report that two "
        "adjacent separators produce one segment instead of an empty one between them, and that "
        "a trailing separator loses the empty segment after it."
    ),
    expected=(
        "split_on(items, separator) returns the segments between separators, including empty "
        "segments produced by adjacent separators and by a trailing separator."
    ),
    baseline_reason="it only appends a segment when the segment is non-empty",
    edge_cases=(
        "adjacent separators produce an empty segment between them",
        "a trailing separator produces a final empty segment",
    ),
    baseline="""def split_on(items, separator):
    \"\"\"Return the segments of `items` around each `separator`.\"\"\"
    segments = []
    current = []
    for entry in items:
        if entry == separator:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(entry)
    if current:
        segments.append(current)
    return segments""",
    variant_one="""def split_on(items, separator):
    \"\"\"Return the segments of `items` around each `separator`.\"\"\"
    segments = []
    current = []
    for entry in items:
        if entry == separator:
            segments.append(current)
            current = []
        else:
            current.append(entry)
    segments.append(current)
    return segments""",
    variant_two="""def split_on(items, separator):
    \"\"\"Return the segments of `items` around each `separator`.\"\"\"
    collected = list(items)
    segments = [[]]
    for entry in collected:
        if entry == separator:
            segments.append([])
        else:
            segments[-1].append(entry)
    return segments""",
    variant_three="""def split_on(items, separator):
    \"\"\"Return the segments of `items` around each `separator`.\"\"\"
    segments = []
    current = []
    for entry in items:
        if entry == separator:
            segments.append(current)
            current = []
        else:
            current.append(entry)
    if current:
        segments.append(current)
    return segments""",
    variant_four="""def split_on(items, separator):
    \"\"\"Return the segments of `items` around each `separator`.\"\"\"
    collected = list(items)
    segments = []
    current = []
    for entry in collected:
        if entry == separator:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(entry)
    segments.append(current)
    return segments""",
    visible_test=_test_module(
        "segment_split",
        "Published contract for splitting around a separator.",
        """
def test_a_single_separator_makes_two_segments() -> None:
    assert split_on([1, 0, 2], 0) == [[1], [2]]


def test_a_sequence_without_the_separator_is_one_segment() -> None:
    assert split_on([1, 2], 0) == [[1, 2]]
""",
        imports="from segment_split import split_on\n",
    ),
    hidden_test=_test_module(
        "segment_split",
        "The part of the contract the published tests do not state.",
        """
def test_a_single_separator_makes_two_segments() -> None:
    assert split_on([1, 0, 2], 0) == [[1], [2]]


def test_adjacent_separators_leave_an_empty_segment() -> None:
    assert split_on([1, 0, 0, 2], 0) == [[1], [], [2]]


def test_a_trailing_separator_leaves_a_final_empty_segment() -> None:
    assert split_on([1, 0], 0) == [[1], []]
""",
        imports="from segment_split import split_on\n",
    ),
)

_G004 = D2TaskSpec(
    template_id="d4_boundary.interleave",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-interleave",
    module="alternating_merge",
    module_doc="Alternating two sequences into one.",
    issue=(
        "interleave() is documented to alternate two sequences and then append whatever is left "
        "over. Callers report that the longer sequence is truncated to the shorter one, and that "
        "interleaving with an empty sequence discards everything."
    ),
    expected=(
        "interleave(left, right) alternates items starting with left, and appends the remainder "
        "of whichever sequence is longer, including when the other one is empty."
    ),
    baseline_reason="zip stops at the shorter sequence and nothing appends the remainder",
    edge_cases=(
        "the longer sequence keeps its remainder",
        "interleaving with an empty sequence returns the other one whole",
    ),
    baseline="""def interleave(left, right):
    \"\"\"Return `left` and `right` alternated, starting with `left`.\"\"\"
    merged = []
    for first, second in zip(left, right):
        merged.append(first)
        merged.append(second)
    return merged""",
    variant_one="""def interleave(left, right):
    \"\"\"Return `left` and `right` alternated, starting with `left`.\"\"\"
    first_items = list(left)
    second_items = list(right)
    merged = []
    for position in range(max(len(first_items), len(second_items))):
        if position < len(first_items):
            merged.append(first_items[position])
        if position < len(second_items):
            merged.append(second_items[position])
    return merged""",
    variant_two="""def interleave(left, right):
    \"\"\"Return `left` and `right` alternated, starting with `left`.\"\"\"
    first_items = list(left)
    second_items = list(right)
    shared = min(len(first_items), len(second_items))
    merged = []
    for position in range(shared):
        merged.append(first_items[position])
        merged.append(second_items[position])
    merged.extend(first_items[shared:])
    merged.extend(second_items[shared:])
    return merged""",
    variant_three="""def interleave(left, right):
    \"\"\"Return `left` and `right` alternated, starting with `left`.\"\"\"
    first_items = list(left)
    second_items = list(right)
    merged = []
    for first, second in zip(first_items, second_items):
        merged.append(first)
        merged.append(second)
    shared = min(len(first_items), len(second_items))
    if shared:
        merged.extend(first_items[shared:])
        merged.extend(second_items[shared:])
    return merged""",
    variant_four="""def interleave(left, right):
    \"\"\"Return `left` and `right` alternated, starting with `left`.\"\"\"
    first_items = list(left)
    second_items = list(right)
    if not first_items:
        return second_items
    if not second_items:
        return first_items
    merged = []
    for first, second in zip(first_items, second_items):
        merged.append(first)
        merged.append(second)
    return merged""",
    visible_test=_test_module(
        "alternating_merge",
        "Published contract for alternating two sequences.",
        """
def test_two_equal_sequences_alternate() -> None:
    assert interleave([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_two_empty_sequences_merge_to_nothing() -> None:
    assert interleave([], []) == []
""",
        imports="from alternating_merge import interleave\n",
    ),
    hidden_test=_test_module(
        "alternating_merge",
        "The part of the contract the published tests do not state.",
        """
def test_two_equal_sequences_alternate() -> None:
    assert interleave([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_the_longer_sequence_keeps_its_remainder() -> None:
    assert interleave([1, 3, 5, 7], [2, 4]) == [1, 2, 3, 4, 5, 7]


def test_an_empty_sequence_leaves_the_other_whole() -> None:
    assert interleave([1, 2, 3], []) == [1, 2, 3]
""",
        imports="from alternating_merge import interleave\n",
    ),
)

_G005 = D2TaskSpec(
    template_id="d4_boundary.batch_by_size",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-batch-by-size",
    module="batching",
    module_doc="Grouping a sequence into fixed-size batches.",
    issue=(
        "batch_by_size() is documented to group a sequence into batches of a fixed size. Callers "
        "report that the final short batch is dropped, and that an empty sequence produces a "
        "batch containing nothing rather than no batches at all."
    ),
    expected=(
        "batch_by_size(items, size) returns consecutive batches of size items, keeps the final "
        "shorter batch when the sequence does not divide evenly, and returns no batches for an "
        "empty sequence."
    ),
    baseline_reason=(
        "a partly filled buffer is dropped, and the empty-input case is papered over by emitting "
        "the empty buffer whenever nothing else was emitted"
    ),
    edge_cases=(
        "a final short batch is kept",
        "an empty sequence produces no batches",
    ),
    baseline="""def batch_by_size(items, size):
    \"\"\"Return `items` grouped into consecutive batches of `size`.\"\"\"
    batches = []
    buffer = []
    for entry in items:
        buffer.append(entry)
        if len(buffer) == size:
            batches.append(buffer)
            buffer = []
    if not batches:
        batches.append(buffer)
    return batches""",
    variant_one="""def batch_by_size(items, size):
    \"\"\"Return `items` grouped into consecutive batches of `size`.\"\"\"
    batches = []
    buffer = []
    for entry in items:
        buffer.append(entry)
        if len(buffer) == size:
            batches.append(buffer)
            buffer = []
    if buffer:
        batches.append(buffer)
    return batches""",
    variant_two="""def batch_by_size(items, size):
    \"\"\"Return `items` grouped into consecutive batches of `size`.\"\"\"
    collected = list(items)
    return [collected[start : start + size] for start in range(0, len(collected), size)]""",
    variant_three="""def batch_by_size(items, size):
    \"\"\"Return `items` grouped into consecutive batches of `size`.\"\"\"
    batches = []
    buffer = []
    for entry in items:
        buffer.append(entry)
        if len(buffer) == size:
            batches.append(buffer)
            buffer = []
    if buffer or not batches:
        batches.append(buffer)
    return batches""",
    variant_four="""def batch_by_size(items, size):
    \"\"\"Return `items` grouped into consecutive batches of `size`.\"\"\"
    batches = []
    buffer = []
    for entry in items:
        buffer.append(entry)
        if len(buffer) == size:
            batches.append(buffer)
            buffer = []
    return batches""",
    visible_test=_test_module(
        "batching",
        "Published contract for fixed-size batching.",
        """
def test_a_sequence_that_divides_evenly() -> None:
    assert batch_by_size([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_a_batch_size_of_one() -> None:
    assert batch_by_size([1, 2], 1) == [[1], [2]]
""",
        imports="from batching import batch_by_size\n",
    ),
    hidden_test=_test_module(
        "batching",
        "The part of the contract the published tests do not state.",
        """
def test_a_sequence_that_divides_evenly() -> None:
    assert batch_by_size([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_a_final_short_batch_is_kept() -> None:
    assert batch_by_size([1, 2, 3], 2) == [[1, 2], [3]]


def test_an_empty_sequence_produces_no_batches() -> None:
    assert batch_by_size([], 3) == []
""",
        imports="from batching import batch_by_size\n",
    ),
)

#: Authored so far. The tuple grows as batches are authored and executed; `corpus_d4.py` reads
#: it rather than a count, so a partially authored corpus reports what it has instead of
#: claiming what it does not.
D4_CALIBRATION_SPECS: tuple[D2TaskSpec, ...] = (
    _G001,
    _G002,
    _G003,
    _G004,
    _G005,
)
