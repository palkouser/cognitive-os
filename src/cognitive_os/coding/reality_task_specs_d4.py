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
    template_id="d4_boundary.partition_by_threshold",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-partition-threshold",
    module="threshold_split",
    module_doc="Separating readings that reach a threshold from those that do not.",
    issue=(
        "partition_by_threshold() is documented to return the readings at or above a threshold "
        "and those below it, each in their original order. Callers report that a reading exactly "
        "on the threshold lands in the wrong half, and that the two halves come back swapped when "
        "nothing reaches the threshold."
    ),
    expected=(
        "partition_by_threshold(readings, threshold) returns (at_or_above, below), each in "
        "original order, counts a reading equal to the threshold as at or above, and returns an "
        "empty first half rather than swapping when nothing reaches it."
    ),
    baseline_reason=(
        "the comparison is strict, and an empty upper half is quietly reported the other way round"
    ),
    edge_cases=(
        "a reading exactly on the threshold counts as at or above",
        "nothing reaching the threshold leaves the halves in order",
    ),
    baseline="""def partition_by_threshold(readings, threshold):
    \"\"\"Return the readings at or above `threshold`, then those below it.\"\"\"
    upper = []
    lower = []
    for reading in readings:
        if reading > threshold:
            upper.append(reading)
        else:
            lower.append(reading)
    if not upper:
        return lower, upper
    return upper, lower""",
    variant_one="""def partition_by_threshold(readings, threshold):
    \"\"\"Return the readings at or above `threshold`, then those below it.\"\"\"
    upper = []
    lower = []
    for reading in readings:
        if reading >= threshold:
            upper.append(reading)
        else:
            lower.append(reading)
    return upper, lower""",
    variant_two="""def partition_by_threshold(readings, threshold):
    \"\"\"Return the readings at or above `threshold`, then those below it.\"\"\"
    collected = list(readings)
    reached = [reading for reading in collected if not reading < threshold]
    missed = [reading for reading in collected if reading < threshold]
    return reached, missed""",
    variant_three="""def partition_by_threshold(readings, threshold):
    \"\"\"Return the readings at or above `threshold`, then those below it.\"\"\"
    upper = []
    lower = []
    for reading in readings:
        if reading >= threshold:
            upper.append(reading)
        else:
            lower.append(reading)
    if not upper:
        return lower, upper
    return upper, lower""",
    variant_four="""def partition_by_threshold(readings, threshold):
    \"\"\"Return the readings at or above `threshold`, then those below it.\"\"\"
    upper = []
    lower = []
    for reading in readings:
        if reading > threshold:
            upper.append(reading)
        else:
            lower.append(reading)
    return upper, lower""",
    visible_test=_test_module(
        "threshold_split",
        "Published contract for splitting readings at a threshold.",
        """
def test_readings_split_around_the_threshold() -> None:
    assert partition_by_threshold([9, 1, 7, 2], 5) == ([9, 7], [1, 2])


def test_every_reading_above_the_threshold() -> None:
    assert partition_by_threshold([8, 9], 5) == ([8, 9], [])
""",
        imports="from threshold_split import partition_by_threshold\n",
    ),
    hidden_test=_test_module(
        "threshold_split",
        "The part of the contract the published tests do not state.",
        """
def test_readings_split_around_the_threshold() -> None:
    assert partition_by_threshold([9, 1, 7, 2], 5) == ([9, 7], [1, 2])


def test_a_reading_on_the_threshold_counts_as_reaching_it() -> None:
    assert partition_by_threshold([5, 1], 5) == ([5], [1])


def test_nothing_reaching_the_threshold_leaves_the_halves_in_order() -> None:
    assert partition_by_threshold([1, 2], 5) == ([], [1, 2])
""",
        imports="from threshold_split import partition_by_threshold\n",
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

_G006 = D2TaskSpec(
    template_id="d4_boundary.rank_positions",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-rank-positions",
    module="standings",
    module_doc="Assigning competition ranks to a table of scores.",
    issue=(
        "rank_positions() is documented to assign competition ranks, highest score first. Callers "
        "report that the rank after a tie continues counting instead of skipping the places the "
        "tie consumed, and that an empty table comes back holding a rank."
    ),
    expected=(
        "rank_positions(scores) returns one rank per score in the original order, gives tied "
        "scores the same rank, resumes after a tie at the place the tie consumed, and returns no "
        "ranks at all for an empty table."
    ),
    baseline_reason=(
        "ranking against the distinct scores makes the ranks dense, and an empty table is papered "
        "over with a first place nobody holds"
    ),
    edge_cases=(
        "the rank after a tie skips the places the tie consumed",
        "an empty table returns no ranks",
    ),
    baseline="""def rank_positions(scores):
    \"\"\"Return the competition rank of each score, highest first.\"\"\"
    collected = list(scores)
    distinct = sorted(set(collected), reverse=True)
    ranks = [distinct.index(score) + 1 for score in collected]
    if not ranks:
        return [1]
    return ranks""",
    variant_one="""def rank_positions(scores):
    \"\"\"Return the competition rank of each score, highest first.\"\"\"
    collected = list(scores)
    ranks = []
    for score in collected:
        ahead = 0
        for other in collected:
            if other > score:
                ahead += 1
        ranks.append(ahead + 1)
    return ranks""",
    variant_two="""def rank_positions(scores):
    \"\"\"Return the competition rank of each score, highest first.\"\"\"
    collected = list(scores)
    ordered = sorted(collected, reverse=True)
    return [ordered.index(score) + 1 for score in collected]""",
    variant_three="""def rank_positions(scores):
    \"\"\"Return the competition rank of each score, highest first.\"\"\"
    collected = list(scores)
    ranks = []
    for score in collected:
        ahead = 0
        for other in collected:
            if other > score:
                ahead += 1
        ranks.append(ahead + 1)
    if not ranks:
        return [1]
    return ranks""",
    variant_four="""def rank_positions(scores):
    \"\"\"Return the competition rank of each score, highest first.\"\"\"
    collected = list(scores)
    distinct = sorted(set(collected), reverse=True)
    return [distinct.index(score) + 1 for score in collected]""",
    visible_test=_test_module(
        "standings",
        "Published contract for competition ranking.",
        """
def test_distinct_scores_rank_in_order() -> None:
    assert rank_positions([10, 30, 20]) == [3, 1, 2]


def test_a_single_score_ranks_first() -> None:
    assert rank_positions([7]) == [1]
""",
        imports="from standings import rank_positions\n",
    ),
    hidden_test=_test_module(
        "standings",
        "The part of the contract the published tests do not state.",
        """
def test_distinct_scores_rank_in_order() -> None:
    assert rank_positions([10, 30, 20]) == [3, 1, 2]


def test_the_rank_after_a_tie_skips_the_consumed_places() -> None:
    assert rank_positions([50, 40, 40, 20]) == [1, 2, 2, 4]


def test_an_empty_table_returns_no_ranks() -> None:
    assert rank_positions([]) == []
""",
        imports="from standings import rank_positions\n",
    ),
)

_G007 = D2TaskSpec(
    template_id="d4_boundary.common_prefix",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-common-prefix",
    module="shared_head",
    module_doc="Finding the shared leading run of several sequences.",
    issue=(
        "common_prefix() is documented to return the leading run shared by every sequence. "
        "Callers report that passing no sequences raises instead of returning nothing, and that "
        "one empty sequence among several is ignored rather than ending the prefix immediately."
    ),
    expected=(
        "common_prefix(sequences) returns the longest leading run present in every sequence, "
        "returns an empty list when there are no sequences, and returns an empty list when any "
        "sequence is empty."
    ),
    baseline_reason=(
        "it indexes the first sequence without checking there is one, and indexes the others "
        "without checking they are that long"
    ),
    edge_cases=(
        "no sequences at all yield an empty prefix",
        "a shorter sequence ends the prefix rather than being indexed past its end",
    ),
    baseline="""def common_prefix(sequences):
    \"\"\"Return the longest leading run shared by every sequence.\"\"\"
    collected = [list(entry) for entry in sequences]
    prefix = []
    for position in range(len(collected[0])):
        value = collected[0][position]
        if all(other[position] == value for other in collected[1:]):
            prefix.append(value)
        else:
            break
    return prefix""",
    variant_one="""def common_prefix(sequences):
    \"\"\"Return the longest leading run shared by every sequence.\"\"\"
    collected = [list(entry) for entry in sequences]
    if not collected:
        return []
    shortest = min(len(entry) for entry in collected)
    prefix = []
    for position in range(shortest):
        value = collected[0][position]
        if any(entry[position] != value for entry in collected):
            break
        prefix.append(value)
    return prefix""",
    variant_two="""def common_prefix(sequences):
    \"\"\"Return the longest leading run shared by every sequence.\"\"\"
    collected = [list(entry) for entry in sequences]
    if len(collected) == 0:
        return []
    prefix = []
    for values in zip(*collected):
        first = values[0]
        for value in values:
            if value != first:
                return prefix
        prefix.append(first)
    return prefix""",
    variant_three="""def common_prefix(sequences):
    \"\"\"Return the longest leading run shared by every sequence.\"\"\"
    collected = [list(entry) for entry in sequences]
    if not collected:
        return []
    prefix = []
    for position in range(len(collected[0])):
        value = collected[0][position]
        if all(other[position] == value for other in collected[1:]):
            prefix.append(value)
        else:
            break
    return prefix""",
    variant_four="""def common_prefix(sequences):
    \"\"\"Return the longest leading run shared by every sequence.\"\"\"
    collected = [list(entry) for entry in sequences]
    shortest = min(len(entry) for entry in collected)
    prefix = []
    for position in range(shortest):
        value = collected[0][position]
        if any(entry[position] != value for entry in collected):
            break
        prefix.append(value)
    return prefix""",
    visible_test=_test_module(
        "shared_head",
        "Published contract for the shared leading run.",
        """
def test_two_sequences_sharing_a_head() -> None:
    assert common_prefix([[1, 2, 9], [1, 2, 8]]) == [1, 2]


def test_sequences_sharing_nothing() -> None:
    assert common_prefix([[1], [2]]) == []
""",
        imports="from shared_head import common_prefix\n",
    ),
    hidden_test=_test_module(
        "shared_head",
        "The part of the contract the published tests do not state.",
        """
def test_two_sequences_sharing_a_head() -> None:
    assert common_prefix([[1, 2, 9], [1, 2, 8]]) == [1, 2]


def test_no_sequences_yield_an_empty_prefix() -> None:
    assert common_prefix([]) == []


def test_a_shorter_sequence_ends_the_prefix() -> None:
    assert common_prefix([[1, 2, 3], [1, 2]]) == [1, 2]
""",
        imports="from shared_head import common_prefix\n",
    ),
)

_G008 = D2TaskSpec(
    template_id="d4_boundary.pairwise_gaps",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-pairwise-gaps",
    module="reading_deltas",
    module_doc="Reporting the gaps between consecutive readings.",
    issue=(
        "pairwise_gaps() is documented to report the gap between each pair of consecutive "
        "readings. Callers report that a single reading raises instead of reporting no gaps, and "
        "that the gaps come back with the sign of the traversal rather than as magnitudes."
    ),
    expected=(
        "pairwise_gaps(readings) returns the absolute gap between each consecutive pair, and "
        "returns an empty list when there are fewer than two readings."
    ),
    baseline_reason=(
        "an empty result is papered over with a zero, and the subtraction keeps the sign of the "
        "traversal"
    ),
    edge_cases=(
        "fewer than two readings yield no gaps",
        "a falling series reports magnitudes",
    ),
    baseline="""def pairwise_gaps(readings):
    \"\"\"Return the gap between each pair of consecutive readings.\"\"\"
    collected = list(readings)
    total = len(collected) - 1
    gaps = [collected[index + 1] - collected[index] for index in range(total)]
    if not gaps:
        return [0]
    return gaps""",
    variant_one="""def pairwise_gaps(readings):
    \"\"\"Return the gap between each pair of consecutive readings.\"\"\"
    collected = list(readings)
    if len(collected) < 2:
        return []
    gaps = []
    for index in range(len(collected) - 1):
        gaps.append(abs(collected[index + 1] - collected[index]))
    return gaps""",
    variant_two="""def pairwise_gaps(readings):
    \"\"\"Return the gap between each pair of consecutive readings.\"\"\"
    collected = list(readings)
    pairs = zip(collected, collected[1:])
    return [abs(later - earlier) for earlier, later in pairs]""",
    variant_three="""def pairwise_gaps(readings):
    \"\"\"Return the gap between each pair of consecutive readings.\"\"\"
    collected = list(readings)
    total = len(collected) - 1
    return [collected[index + 1] - collected[index] for index in range(total)]""",
    variant_four="""def pairwise_gaps(readings):
    \"\"\"Return the gap between each pair of consecutive readings.\"\"\"
    collected = list(readings)
    total = len(collected) - 1
    gaps = [abs(collected[index + 1] - collected[index]) for index in range(total)]
    if not gaps:
        return [0]
    return gaps""",
    visible_test=_test_module(
        "reading_deltas",
        "Published contract for consecutive gaps.",
        """
def test_a_rising_series_reports_its_steps() -> None:
    assert pairwise_gaps([1, 3, 6]) == [2, 3]


def test_a_flat_series_reports_zeros() -> None:
    assert pairwise_gaps([4, 4, 4]) == [0, 0]
""",
        imports="from reading_deltas import pairwise_gaps\n",
    ),
    hidden_test=_test_module(
        "reading_deltas",
        "The part of the contract the published tests do not state.",
        """
def test_a_rising_series_reports_its_steps() -> None:
    assert pairwise_gaps([1, 3, 6]) == [2, 3]


def test_a_single_reading_yields_no_gaps() -> None:
    assert pairwise_gaps([5]) == []


def test_a_falling_series_reports_magnitudes() -> None:
    assert pairwise_gaps([9, 4, 2]) == [5, 2]
""",
        imports="from reading_deltas import pairwise_gaps\n",
    ),
)

_G009 = D2TaskSpec(
    template_id="d4_boundary.trim_both_ends",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-trim-both-ends",
    module="pad_strip",
    module_doc="Trimming a padding value from both ends of a sequence.",
    issue=(
        "trim_both_ends() is documented to drop a padding value from both ends. Callers report "
        "that padding in the middle is dropped as well, and that a sequence made entirely of "
        "padding raises instead of trimming to nothing."
    ),
    expected=(
        "trim_both_ends(items, padding) removes leading and trailing runs of padding, keeps "
        "padding that sits between other items, and returns an empty list when everything is "
        "padding."
    ),
    baseline_reason="it filters the whole sequence, and the all-padding case leaves no bounds",
    edge_cases=(
        "padding in the middle is kept",
        "an all-padding sequence trims to nothing",
    ),
    baseline="""def trim_both_ends(items, padding):
    \"\"\"Return `items` without leading and trailing runs of `padding`.\"\"\"
    collected = [entry for entry in items if entry != padding]
    return collected""",
    variant_one="""def trim_both_ends(items, padding):
    \"\"\"Return `items` without leading and trailing runs of `padding`.\"\"\"
    collected = list(items)
    start = 0
    while start < len(collected) and collected[start] == padding:
        start += 1
    end = len(collected)
    while end > start and collected[end - 1] == padding:
        end -= 1
    return collected[start:end]""",
    variant_two="""def trim_both_ends(items, padding):
    \"\"\"Return `items` without leading and trailing runs of `padding`.\"\"\"
    collected = list(items)
    while collected and collected[0] == padding:
        collected.pop(0)
    while collected and collected[-1] == padding:
        collected.pop()
    return collected""",
    variant_three="""def trim_both_ends(items, padding):
    \"\"\"Return `items` without leading and trailing runs of `padding`.\"\"\"
    collected = list(items)
    first = min(index for index, entry in enumerate(collected) if entry != padding)
    last = max(index for index, entry in enumerate(collected) if entry != padding)
    return collected[first : last + 1]""",
    variant_four="""def trim_both_ends(items, padding):
    \"\"\"Return `items` without leading and trailing runs of `padding`.\"\"\"
    collected = [entry for entry in items if entry != padding]
    if not collected:
        return []
    return collected""",
    visible_test=_test_module(
        "pad_strip",
        "Published contract for trimming both ends.",
        """
def test_padding_at_both_ends_is_removed() -> None:
    assert trim_both_ends([0, 1, 2, 0], 0) == [1, 2]


def test_a_sequence_without_padding_is_unchanged() -> None:
    assert trim_both_ends([1, 2], 0) == [1, 2]
""",
        imports="from pad_strip import trim_both_ends\n",
    ),
    hidden_test=_test_module(
        "pad_strip",
        "The part of the contract the published tests do not state.",
        """
def test_padding_at_both_ends_is_removed() -> None:
    assert trim_both_ends([0, 1, 2, 0], 0) == [1, 2]


def test_padding_in_the_middle_is_kept() -> None:
    assert trim_both_ends([0, 1, 0, 2, 0], 0) == [1, 0, 2]


def test_an_all_padding_sequence_trims_to_nothing() -> None:
    assert trim_both_ends([0, 0], 0) == []
""",
        imports="from pad_strip import trim_both_ends\n",
    ),
)

_G010 = D2TaskSpec(
    template_id="d4_boundary.take_until",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-take-until",
    module="prefix_until",
    module_doc="Taking the leading run of a sequence before a sentinel.",
    issue=(
        "take_until() is documented to return the items before the first sentinel. Callers "
        "report that a sentinel in first position still yields that item, and that a sequence "
        "with no sentinel at all loses its final item."
    ),
    expected=(
        "take_until(items, sentinel) returns the items before the first sentinel, returns an "
        "empty list when the sentinel is first, and returns every item when no sentinel appears."
    ),
    baseline_reason=(
        "the scan starts at the second item, and when no sentinel is found the cut defaults to "
        "one item short of the end"
    ),
    edge_cases=(
        "a leading sentinel yields nothing",
        "a sequence without a sentinel is returned whole",
    ),
    baseline="""def take_until(items, sentinel):
    \"\"\"Return the items of `items` before the first `sentinel`.\"\"\"
    collected = list(items)
    stop = len(collected) - 1
    for position in range(1, len(collected)):
        if collected[position] == sentinel:
            stop = position
            break
    return collected[:stop]""",
    variant_one="""def take_until(items, sentinel):
    \"\"\"Return the items of `items` before the first `sentinel`.\"\"\"
    taken = []
    for entry in items:
        if entry == sentinel:
            break
        taken.append(entry)
    return taken""",
    variant_two="""def take_until(items, sentinel):
    \"\"\"Return the items of `items` before the first `sentinel`.\"\"\"
    collected = list(items)
    if sentinel in collected:
        return collected[: collected.index(sentinel)]
    return collected""",
    variant_three="""def take_until(items, sentinel):
    \"\"\"Return the items of `items` before the first `sentinel`.\"\"\"
    collected = list(items)
    stop = len(collected) - 1
    for position in range(len(collected)):
        if collected[position] == sentinel:
            stop = position
            break
    return collected[:stop]""",
    variant_four="""def take_until(items, sentinel):
    \"\"\"Return the items of `items` before the first `sentinel`.\"\"\"
    collected = list(items)
    stop = len(collected)
    for position in range(1, len(collected)):
        if collected[position] == sentinel:
            stop = position
            break
    return collected[:stop]""",
    visible_test=_test_module(
        "prefix_until",
        "Published contract for taking a prefix before a sentinel.",
        """
def test_items_before_a_middle_sentinel() -> None:
    assert take_until([1, 2, 0, 3], 0) == [1, 2]


def test_a_sentinel_just_before_the_end() -> None:
    assert take_until([1, 0, 9], 0) == [1]
""",
        imports="from prefix_until import take_until\n",
    ),
    hidden_test=_test_module(
        "prefix_until",
        "The part of the contract the published tests do not state.",
        """
def test_items_before_a_middle_sentinel() -> None:
    assert take_until([1, 2, 0, 3], 0) == [1, 2]


def test_a_leading_sentinel_yields_nothing() -> None:
    assert take_until([0, 1, 2], 0) == []


def test_a_sequence_without_a_sentinel_is_whole() -> None:
    assert take_until([1, 2, 3], 0) == [1, 2, 3]
""",
        imports="from prefix_until import take_until\n",
    ),
)

# ------------------------------------------------------------------------ parsing and validation

_G011 = D2TaskSpec(
    template_id="d4_parsing.key_values",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-key-values",
    module="settings_line",
    module_doc="Reading a semicolon-separated settings line.",
    issue=(
        "parse_key_values() is documented to read a settings line into a mapping. Callers report "
        "that a fragment carrying no equals sign crashes the parse instead of being skipped, and "
        "that spaces around a name or a value end up inside them."
    ),
    expected=(
        "parse_key_values(line) returns a mapping of names to values, skips any fragment without "
        "an equals sign, and strips surrounding whitespace from both sides."
    ),
    baseline_reason="every fragment is unpacked as a pair, and neither side is stripped",
    edge_cases=(
        "a fragment without an equals sign is skipped",
        "whitespace around a name or value is removed",
    ),
    baseline="""def parse_key_values(line):
    \"\"\"Return the settings in `line` as a mapping of names to values.\"\"\"
    settings = {}
    for fragment in line.split(";"):
        if not fragment:
            continue
        name, value = fragment.split("=")
        settings[name] = value
    return settings""",
    variant_one="""def parse_key_values(line):
    \"\"\"Return the settings in `line` as a mapping of names to values.\"\"\"
    settings = {}
    for fragment in line.split(";"):
        if "=" not in fragment:
            continue
        name, _, value = fragment.partition("=")
        settings[name.strip()] = value.strip()
    return settings""",
    variant_two="""def parse_key_values(line):
    \"\"\"Return the settings in `line` as a mapping of names to values.\"\"\"
    settings = {}
    for fragment in line.split(";"):
        pieces = fragment.split("=", 1)
        if len(pieces) != 2:
            continue
        settings[pieces[0].strip()] = pieces[1].strip()
    return settings""",
    variant_three="""def parse_key_values(line):
    \"\"\"Return the settings in `line` as a mapping of names to values.\"\"\"
    settings = {}
    for fragment in line.split(";"):
        if "=" not in fragment:
            continue
        name, _, value = fragment.partition("=")
        settings[name] = value
    return settings""",
    variant_four="""def parse_key_values(line):
    \"\"\"Return the settings in `line` as a mapping of names to values.\"\"\"
    settings = {}
    for fragment in line.split(";"):
        if not fragment:
            continue
        name, value = fragment.split("=")
        settings[name.strip()] = value.strip()
    return settings""",
    visible_test=_test_module(
        "settings_line",
        "Published contract for reading a settings line.",
        """
def test_two_settings_are_read() -> None:
    assert parse_key_values("a=1;b=2") == {"a": "1", "b": "2"}


def test_a_single_setting_is_read() -> None:
    assert parse_key_values("mode=fast") == {"mode": "fast"}
""",
        imports="from settings_line import parse_key_values\n",
    ),
    hidden_test=_test_module(
        "settings_line",
        "The part of the contract the published tests do not state.",
        """
def test_two_settings_are_read() -> None:
    assert parse_key_values("a=1;b=2") == {"a": "1", "b": "2"}


def test_a_fragment_without_an_equals_sign_is_skipped() -> None:
    assert parse_key_values("a=1;broken;b=2") == {"a": "1", "b": "2"}


def test_whitespace_around_a_name_or_value_is_removed() -> None:
    assert parse_key_values(" a = 1 ") == {"a": "1"}
""",
        imports="from settings_line import parse_key_values\n",
    ),
)

_G012 = D2TaskSpec(
    template_id="d4_parsing.span_bounds",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-span-bounds",
    module="span_text",
    module_doc="Reading an inclusive numeric span written as text.",
    issue=(
        "parse_span() is documented to read a span such as '3-7'. Callers report that a bare "
        "number crashes instead of describing a span of one, and that a span starting below zero "
        "is split at its own minus sign."
    ),
    expected=(
        "parse_span(text) returns (low, high); a bare number describes the span containing only "
        "itself; a leading minus belongs to the lower bound rather than separating the two."
    ),
    baseline_reason="the text is split on every minus sign and two pieces are assumed",
    edge_cases=(
        "a bare number is a span of one",
        "a negative lower bound is not treated as a separator",
    ),
    baseline="""def parse_span(text):
    \"\"\"Return the inclusive (low, high) bounds written in `text`.\"\"\"
    trimmed = text.strip()
    low, high = trimmed.split("-")
    return int(low), int(high)""",
    variant_one="""def parse_span(text):
    \"\"\"Return the inclusive (low, high) bounds written in `text`.\"\"\"
    trimmed = text.strip()
    position = trimmed.find("-", 1)
    if position == -1:
        only = int(trimmed)
        return only, only
    return int(trimmed[:position]), int(trimmed[position + 1 :])""",
    variant_two="""def parse_span(text):
    \"\"\"Return the inclusive (low, high) bounds written in `text`.\"\"\"
    trimmed = text.strip()
    head = trimmed[:1]
    rest = trimmed[1:]
    if "-" not in rest:
        only = int(trimmed)
        return only, only
    first, _, second = rest.partition("-")
    return int(head + first), int(second)""",
    variant_three="""def parse_span(text):
    \"\"\"Return the inclusive (low, high) bounds written in `text`.\"\"\"
    trimmed = text.strip()
    if "-" not in trimmed:
        only = int(trimmed)
        return only, only
    low, high = trimmed.split("-")
    return int(low), int(high)""",
    variant_four="""def parse_span(text):
    \"\"\"Return the inclusive (low, high) bounds written in `text`.\"\"\"
    trimmed = text.strip()
    position = trimmed.find("-", 1)
    return int(trimmed[:position]), int(trimmed[position + 1 :])""",
    visible_test=_test_module(
        "span_text",
        "Published contract for reading a span.",
        """
def test_a_simple_span() -> None:
    assert parse_span("3-7") == (3, 7)


def test_a_wider_span() -> None:
    assert parse_span("10-20") == (10, 20)
""",
        imports="from span_text import parse_span\n",
    ),
    hidden_test=_test_module(
        "span_text",
        "The part of the contract the published tests do not state.",
        """
def test_a_simple_span() -> None:
    assert parse_span("3-7") == (3, 7)


def test_a_bare_number_is_a_span_of_one() -> None:
    assert parse_span("5") == (5, 5)


def test_a_negative_lower_bound_is_kept() -> None:
    assert parse_span("-2-4") == (-2, 4)
""",
        imports="from span_text import parse_span\n",
    ),
)

_G013 = D2TaskSpec(
    template_id="d4_parsing.release_number",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-release-number",
    module="release_number",
    module_doc="Reading a three-part release number.",
    issue=(
        "parse_release() is documented to read a three-part release number. Callers report that "
        "a two-part number comes back with two parts instead of a zero-filled third, and that a "
        "four-part number is accepted rather than rejected."
    ),
    expected=(
        "parse_release(text) returns exactly three integers, filling missing trailing parts with "
        "zero, and raises ValueError for more than three parts."
    ),
    baseline_reason="the parts are converted as they come, with no padding and no length check",
    edge_cases=(
        "a missing trailing part is filled with zero",
        "more than three parts is rejected",
    ),
    baseline="""def parse_release(text):
    \"\"\"Return the three integer parts of the release number in `text`.\"\"\"
    return tuple(int(part) for part in text.split("."))""",
    variant_one="""def parse_release(text):
    \"\"\"Return the three integer parts of the release number in `text`.\"\"\"
    parts = text.split(".")
    if len(parts) > 3:
        raise ValueError("a release number has at most three parts")
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)""",
    variant_two="""def parse_release(text):
    \"\"\"Return the three integer parts of the release number in `text`.\"\"\"
    parts = text.split(".")
    if len(parts) not in (1, 2, 3):
        raise ValueError("a release number has at most three parts")
    padded = parts + ["0"] * (3 - len(parts))
    return tuple(int(part) for part in padded)""",
    variant_three="""def parse_release(text):
    \"\"\"Return the three integer parts of the release number in `text`.\"\"\"
    numbers = [int(part) for part in text.split(".")]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)""",
    variant_four="""def parse_release(text):
    \"\"\"Return the three integer parts of the release number in `text`.\"\"\"
    parts = text.split(".")
    if len(parts) > 3:
        raise ValueError("a release number has at most three parts")
    return tuple(int(part) for part in parts)""",
    visible_test=_test_module(
        "release_number",
        "Published contract for reading a release number.",
        """
def test_a_three_part_number() -> None:
    assert parse_release("1.2.3") == (1, 2, 3)


def test_a_zero_release() -> None:
    assert parse_release("0.0.1") == (0, 0, 1)
""",
        imports="from release_number import parse_release\n",
    ),
    hidden_test=_test_module(
        "release_number",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_three_part_number() -> None:
    assert parse_release("1.2.3") == (1, 2, 3)


def test_a_missing_trailing_part_is_filled_with_zero() -> None:
    assert parse_release("1.2") == (1, 2, 0)


def test_more_than_three_parts_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_release("1.2.3.4")
""",
        imports="from release_number import parse_release\n",
    ),
)

_G014 = D2TaskSpec(
    template_id="d4_parsing.hex_colour",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-hex-colour",
    module="hex_colour",
    module_doc="Reading a colour written as hexadecimal channels.",
    issue=(
        "parse_colour() is documented to read a hexadecimal colour. Callers report that the "
        "three-digit shorthand crashes instead of expanding to full channels, and that a colour "
        "written without its leading hash is accepted rather than rejected."
    ),
    expected=(
        "parse_colour(text) returns the (red, green, blue) channels, expands the three-digit "
        "shorthand by doubling each digit, and raises ValueError when the leading hash is absent."
    ),
    baseline_reason=(
        "the body is sliced in fixed pairs, and the hash is stripped rather than required"
    ),
    edge_cases=(
        "the three-digit shorthand expands to full channels",
        "a colour without a leading hash is rejected",
    ),
    baseline="""def parse_colour(text):
    \"\"\"Return the (red, green, blue) channels written in `text`.\"\"\"
    body = text.lstrip("#")
    return int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)""",
    variant_one="""def parse_colour(text):
    \"\"\"Return the (red, green, blue) channels written in `text`.\"\"\"
    if not text.startswith("#"):
        raise ValueError(f"{text!r} is missing its leading hash")
    body = text[1:]
    if len(body) == 3:
        body = "".join(digit * 2 for digit in body)
    return int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)""",
    variant_two="""def parse_colour(text):
    \"\"\"Return the (red, green, blue) channels written in `text`.\"\"\"
    if text[:1] != "#":
        raise ValueError(f"{text!r} is missing its leading hash")
    body = text[1:]
    width = 1 if len(body) == 3 else 2
    channels = [body[start : start + width] for start in range(0, len(body), width)]
    return tuple(int(channel * (3 - width), 16) for channel in channels[:3])""",
    variant_three="""def parse_colour(text):
    \"\"\"Return the (red, green, blue) channels written in `text`.\"\"\"
    body = text.lstrip("#")
    if len(body) == 3:
        body = "".join(digit * 2 for digit in body)
    return int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)""",
    variant_four="""def parse_colour(text):
    \"\"\"Return the (red, green, blue) channels written in `text`.\"\"\"
    if not text.startswith("#"):
        raise ValueError(f"{text!r} is missing its leading hash")
    body = text[1:]
    return int(body[0:2], 16), int(body[2:4], 16), int(body[4:6], 16)""",
    visible_test=_test_module(
        "hex_colour",
        "Published contract for reading a hexadecimal colour.",
        """
def test_a_full_colour_is_read() -> None:
    assert parse_colour("#1a2b3c") == (26, 43, 60)


def test_black_is_all_zeros() -> None:
    assert parse_colour("#000000") == (0, 0, 0)
""",
        imports="from hex_colour import parse_colour\n",
    ),
    hidden_test=_test_module(
        "hex_colour",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_full_colour_is_read() -> None:
    assert parse_colour("#1a2b3c") == (26, 43, 60)


def test_the_shorthand_expands_to_full_channels() -> None:
    assert parse_colour("#abc") == (170, 187, 204)


def test_a_colour_without_a_leading_hash_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_colour("1a2b3c")
""",
        imports="from hex_colour import parse_colour\n",
    ),
)

_G015 = D2TaskSpec(
    template_id="d4_parsing.truth_word",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-truth-word",
    module="truth_word",
    module_doc="Reading a written yes-or-no answer.",
    issue=(
        "parse_truth() is documented to read a written answer. Callers report that an answer in "
        "capitals is read as false, and that an answer nobody recognises is quietly read as "
        "false instead of being rejected."
    ),
    expected=(
        "parse_truth(word) recognises yes and no answers regardless of case, and raises "
        "ValueError for a word it does not recognise."
    ),
    baseline_reason=(
        "membership is tested against lowercase spellings and anything else falls through"
    ),
    edge_cases=(
        "an answer in capitals is recognised",
        "an unrecognised answer is rejected",
    ),
    baseline="""def parse_truth(word):
    \"\"\"Return the boolean written in `word`.\"\"\"
    return word in ("true", "yes", "on", "1")""",
    variant_one="""def parse_truth(word):
    \"\"\"Return the boolean written in `word`.\"\"\"
    spelled = word.strip().lower()
    if spelled in ("true", "yes", "on", "1"):
        return True
    if spelled in ("false", "no", "off", "0"):
        return False
    raise ValueError(f"unrecognised answer {word!r}")""",
    variant_two="""def parse_truth(word):
    \"\"\"Return the boolean written in `word`.\"\"\"
    answers = {
        "true": True,
        "yes": True,
        "on": True,
        "1": True,
        "false": False,
        "no": False,
        "off": False,
        "0": False,
    }
    spelled = word.strip().lower()
    if spelled not in answers:
        raise ValueError(f"unrecognised answer {word!r}")
    return answers[spelled]""",
    variant_three="""def parse_truth(word):
    \"\"\"Return the boolean written in `word`.\"\"\"
    return word.strip().lower() in ("true", "yes", "on", "1")""",
    variant_four="""def parse_truth(word):
    \"\"\"Return the boolean written in `word`.\"\"\"
    if word in ("true", "yes", "on", "1"):
        return True
    if word in ("false", "no", "off", "0"):
        return False
    raise ValueError(f"unrecognised answer {word!r}")""",
    visible_test=_test_module(
        "truth_word",
        "Published contract for reading a written answer.",
        """
def test_a_positive_answer() -> None:
    assert parse_truth("yes") is True


def test_a_negative_answer() -> None:
    assert parse_truth("no") is False
""",
        imports="from truth_word import parse_truth\n",
    ),
    hidden_test=_test_module(
        "truth_word",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_positive_answer() -> None:
    assert parse_truth("yes") is True


def test_an_answer_in_capitals_is_recognised() -> None:
    assert parse_truth("YES") is True


def test_an_unrecognised_answer_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_truth("maybe")
""",
        imports="from truth_word import parse_truth\n",
    ),
)

_G016 = D2TaskSpec(
    template_id="d4_parsing.option_tokens",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-option-tokens",
    module="option_tokens",
    module_doc="Reading the options named by a command-line token.",
    issue=(
        "parse_option() is documented to read the options a token names. Callers report that a "
        "long option comes back as its individual letters, and that a token carrying no leading "
        "dash is accepted as if it were one."
    ),
    expected=(
        "parse_option(token) returns the letters of a short token, the single whole name of a "
        "long token, and raises ValueError for a token that does not begin with a dash."
    ),
    baseline_reason="the dashes are stripped and whatever is left is spread into letters",
    edge_cases=(
        "a long option is one whole name",
        "a token without a leading dash is rejected",
    ),
    baseline="""def parse_option(token):
    \"\"\"Return the options named by `token`.\"\"\"
    return list(token.lstrip("-"))""",
    variant_one="""def parse_option(token):
    \"\"\"Return the options named by `token`.\"\"\"
    if not token.startswith("-"):
        raise ValueError(f"{token!r} is not an option")
    if token.startswith("--"):
        return [token[2:]]
    return list(token[1:])""",
    variant_two="""def parse_option(token):
    \"\"\"Return the options named by `token`.\"\"\"
    dashes = len(token) - len(token.lstrip("-"))
    if dashes == 0:
        raise ValueError(f"{token!r} is not an option")
    body = token[dashes:]
    return [body] if dashes >= 2 else list(body)""",
    variant_three="""def parse_option(token):
    \"\"\"Return the options named by `token`.\"\"\"
    if token.startswith("--"):
        return [token[2:]]
    return list(token.lstrip("-"))""",
    variant_four="""def parse_option(token):
    \"\"\"Return the options named by `token`.\"\"\"
    if not token.startswith("-"):
        raise ValueError(f"{token!r} is not an option")
    return list(token.lstrip("-"))""",
    visible_test=_test_module(
        "option_tokens",
        "Published contract for reading an option token.",
        """
def test_a_short_token_names_each_letter() -> None:
    assert parse_option("-abc") == ["a", "b", "c"]


def test_a_single_letter_token() -> None:
    assert parse_option("-x") == ["x"]
""",
        imports="from option_tokens import parse_option\n",
    ),
    hidden_test=_test_module(
        "option_tokens",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_short_token_names_each_letter() -> None:
    assert parse_option("-abc") == ["a", "b", "c"]


def test_a_long_token_is_one_whole_name() -> None:
    assert parse_option("--verbose") == ["verbose"]


def test_a_token_without_a_dash_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_option("abc")
""",
        imports="from option_tokens import parse_option\n",
    ),
)

_G017 = D2TaskSpec(
    template_id="d4_parsing.tidy_route",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-tidy-route",
    module="route_tidy",
    module_doc="Tidying a slash-separated route.",
    issue=(
        "tidy_route() is documented to resolve the current-directory and parent steps in a "
        "route. Callers report that a parent step at the very start escapes above the root "
        "instead of being dropped, and that a trailing slash leaves an empty final step."
    ),
    expected=(
        "tidy_route(route) resolves '.' and '..' steps, drops a parent step that would escape "
        "above the root, and ignores empty steps left by repeated or trailing slashes."
    ),
    baseline_reason="the parent step pops unconditionally and empty steps are kept",
    edge_cases=(
        "a parent step at the root is dropped",
        "a trailing slash leaves no empty step",
    ),
    baseline="""def tidy_route(route):
    \"\"\"Return `route` with current-directory and parent steps resolved.\"\"\"
    steps = []
    for step in route.split("/"):
        if step == ".":
            continue
        if step == "..":
            steps.pop()
        else:
            steps.append(step)
    return "/".join(steps)""",
    variant_one="""def tidy_route(route):
    \"\"\"Return `route` with current-directory and parent steps resolved.\"\"\"
    steps = []
    for step in route.split("/"):
        if step in (".", ""):
            continue
        if step == "..":
            if steps:
                steps.pop()
            continue
        steps.append(step)
    return "/".join(steps)""",
    variant_two="""def tidy_route(route):
    \"\"\"Return `route` with current-directory and parent steps resolved.\"\"\"
    steps = []
    for step in [item for item in route.split("/") if item and item != "."]:
        if step == "..":
            steps = steps[:-1]
        else:
            steps = steps + [step]
    return "/".join(steps)""",
    variant_three="""def tidy_route(route):
    \"\"\"Return `route` with current-directory and parent steps resolved.\"\"\"
    steps = []
    for step in route.split("/"):
        if step == ".":
            continue
        if step == "..":
            if steps:
                steps.pop()
            continue
        steps.append(step)
    return "/".join(steps)""",
    variant_four="""def tidy_route(route):
    \"\"\"Return `route` with current-directory and parent steps resolved.\"\"\"
    steps = []
    for step in route.split("/"):
        if step in (".", ""):
            continue
        if step == "..":
            steps.pop()
        else:
            steps.append(step)
    return "/".join(steps)""",
    visible_test=_test_module(
        "route_tidy",
        "Published contract for tidying a route.",
        """
def test_a_plain_route_is_unchanged() -> None:
    assert tidy_route("a/b") == "a/b"


def test_a_current_directory_step_is_dropped() -> None:
    assert tidy_route("a/./b") == "a/b"
""",
        imports="from route_tidy import tidy_route\n",
    ),
    hidden_test=_test_module(
        "route_tidy",
        "The part of the contract the published tests do not state.",
        """
def test_a_plain_route_is_unchanged() -> None:
    assert tidy_route("a/b") == "a/b"


def test_a_parent_step_at_the_root_is_dropped() -> None:
    assert tidy_route("../a") == "a"


def test_a_trailing_slash_leaves_no_empty_step() -> None:
    assert tidy_route("a/b/") == "a/b"
""",
        imports="from route_tidy import tidy_route\n",
    ),
)

_G018 = D2TaskSpec(
    template_id="d4_parsing.column_label",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-column-label",
    module="column_label",
    module_doc="Turning a spreadsheet column label into its number.",
    issue=(
        "column_number() is documented to turn a column label into its one-based number. Callers "
        "report that a label written in lowercase produces a wildly wrong number, and that an "
        "empty label comes back as zero instead of being rejected."
    ),
    expected=(
        "column_number(label) returns the one-based column number, accepts a label in either "
        "case, and raises ValueError for an empty label."
    ),
    baseline_reason=(
        "each letter is offset from capital A, and an empty label never enters the loop"
    ),
    edge_cases=(
        "a label in lowercase is accepted",
        "an empty label is rejected",
    ),
    baseline="""def column_number(label):
    \"\"\"Return the one-based column number named by `label`.\"\"\"
    total = 0
    for character in label:
        total = total * 26 + (ord(character) - ord("A") + 1)
    return total""",
    variant_one="""def column_number(label):
    \"\"\"Return the one-based column number named by `label`.\"\"\"
    if not label:
        raise ValueError("a column label cannot be empty")
    total = 0
    for character in label.upper():
        total = total * 26 + (ord(character) - ord("A") + 1)
    return total""",
    variant_two="""def column_number(label):
    \"\"\"Return the one-based column number named by `label`.\"\"\"
    letters = label.upper()
    if len(letters) == 0:
        raise ValueError("a column label cannot be empty")
    total = 0
    for place, character in enumerate(reversed(letters)):
        total += (ord(character) - 64) * (26**place)
    return total""",
    variant_three="""def column_number(label):
    \"\"\"Return the one-based column number named by `label`.\"\"\"
    total = 0
    for character in label.upper():
        total = total * 26 + (ord(character) - ord("A") + 1)
    return total""",
    variant_four="""def column_number(label):
    \"\"\"Return the one-based column number named by `label`.\"\"\"
    if not label:
        raise ValueError("a column label cannot be empty")
    total = 0
    for character in label:
        total = total * 26 + (ord(character) - ord("A") + 1)
    return total""",
    visible_test=_test_module(
        "column_label",
        "Published contract for reading a column label.",
        """
def test_the_first_column() -> None:
    assert column_number("A") == 1


def test_the_first_two_letter_column() -> None:
    assert column_number("AA") == 27
""",
        imports="from column_label import column_number\n",
    ),
    hidden_test=_test_module(
        "column_label",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_column() -> None:
    assert column_number("A") == 1


def test_a_lowercase_label_is_accepted() -> None:
    assert column_number("aa") == 27


def test_an_empty_label_is_rejected() -> None:
    with pytest.raises(ValueError):
        column_number("")
""",
        imports="from column_label import column_number\n",
    ),
)

_G019 = D2TaskSpec(
    template_id="d4_parsing.bracketed_body",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-bracketed-body",
    module="bracket_body",
    module_doc="Reading the text inside a bracketed call.",
    issue=(
        "bracketed_body() is documented to return the text between the outermost brackets. "
        "Callers report that a nested bracket ends the text early, and that a call with no "
        "brackets at all crashes instead of returning nothing."
    ),
    expected=(
        "bracketed_body(text) returns the text between the outermost matching brackets, keeps "
        "nested brackets inside it, and returns an empty string when there are no brackets."
    ),
    baseline_reason="it cuts at the first closing bracket and assumes an opening one exists",
    edge_cases=(
        "a nested bracket does not end the text",
        "text without brackets returns nothing",
    ),
    baseline="""def bracketed_body(text):
    \"\"\"Return the text between the outermost brackets of `text`.\"\"\"
    start = text.index("(")
    end = text.index(")")
    return text[start + 1 : end]""",
    variant_one="""def bracketed_body(text):
    \"\"\"Return the text between the outermost brackets of `text`.\"\"\"
    body = ""
    if "(" not in text:
        return body
    start = text.index("(")
    depth = 0
    for position in range(start, len(text)):
        if text[position] == "(":
            depth += 1
        elif text[position] == ")":
            depth -= 1
            if depth == 0:
                body = text[start + 1 : position]
                break
    return body""",
    variant_two="""def bracketed_body(text):
    \"\"\"Return the text between the outermost brackets of `text`.\"\"\"
    if "(" not in text or ")" not in text:
        return ""
    start = text.index("(")
    end = text.rindex(")")
    return text[start + 1 : end]""",
    variant_three="""def bracketed_body(text):
    \"\"\"Return the text between the outermost brackets of `text`.\"\"\"
    start = text.index("(")
    end = text.rindex(")")
    return text[start + 1 : end]""",
    variant_four="""def bracketed_body(text):
    \"\"\"Return the text between the outermost brackets of `text`.\"\"\"
    if "(" not in text:
        return ""
    start = text.index("(")
    end = text.index(")")
    return text[start + 1 : end]""",
    visible_test=_test_module(
        "bracket_body",
        "Published contract for reading a bracketed body.",
        """
def test_a_simple_call() -> None:
    assert bracketed_body("f(a)") == "a"


def test_a_call_with_two_arguments() -> None:
    assert bracketed_body("g(x, y)") == "x, y"
""",
        imports="from bracket_body import bracketed_body\n",
    ),
    hidden_test=_test_module(
        "bracket_body",
        "The part of the contract the published tests do not state.",
        """
def test_a_simple_call() -> None:
    assert bracketed_body("f(a)") == "a"


def test_a_nested_bracket_does_not_end_the_text() -> None:
    assert bracketed_body("f(a, g(b))") == "a, g(b)"


def test_text_without_brackets_returns_nothing() -> None:
    assert bracketed_body("plain") == ""
""",
        imports="from bracket_body import bracketed_body\n",
    ),
)

_G020 = D2TaskSpec(
    template_id="d4_parsing.word_tokens",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-word-tokens",
    module="word_tokens",
    module_doc="Breaking a sentence into lowercase words.",
    issue=(
        "tokenize_words() is documented to break a sentence into lowercase words. Callers report "
        "that an apostrophe inside a word splits it in two, and that a number is dropped instead "
        "of being kept as a word of its own."
    ),
    expected=(
        "tokenize_words(sentence) returns the lowercase words of a sentence, keeps an apostrophe "
        "inside a word, and keeps a run of digits as a word."
    ),
    baseline_reason="every character that is not a letter is treated as a separator",
    edge_cases=(
        "an apostrophe stays inside a word",
        "a run of digits is kept as a word",
    ),
    baseline="""def tokenize_words(sentence):
    \"\"\"Return the lowercase words of `sentence`.\"\"\"
    words = []
    current = []
    for character in sentence.lower():
        if character.isalpha():
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words""",
    variant_one="""def tokenize_words(sentence):
    \"\"\"Return the lowercase words of `sentence`.\"\"\"
    words = []
    current = []
    for character in sentence.lower():
        if character.isalnum() or (character == "'" and current):
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words""",
    variant_two="""def tokenize_words(sentence):
    \"\"\"Return the lowercase words of `sentence`.\"\"\"
    softened = []
    for position, character in enumerate(sentence.lower()):
        keeps = character.isalnum() or (character == "'" and 0 < position)
        softened.append(character if keeps else " ")
    return [word for word in "".join(softened).split(" ") if word]""",
    variant_three="""def tokenize_words(sentence):
    \"\"\"Return the lowercase words of `sentence`.\"\"\"
    words = []
    current = []
    for character in sentence.lower():
        if character.isalpha() or (character == "'" and current):
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words""",
    variant_four="""def tokenize_words(sentence):
    \"\"\"Return the lowercase words of `sentence`.\"\"\"
    words = []
    current = []
    for character in sentence.lower():
        if character.isalnum():
            current.append(character)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    return words""",
    visible_test=_test_module(
        "word_tokens",
        "Published contract for breaking a sentence into words.",
        """
def test_punctuation_separates_words() -> None:
    assert tokenize_words("Hello, world!") == ["hello", "world"]


def test_a_pair_of_plain_words() -> None:
    assert tokenize_words("Alpha Beta") == ["alpha", "beta"]
""",
        imports="from word_tokens import tokenize_words\n",
    ),
    hidden_test=_test_module(
        "word_tokens",
        "The part of the contract the published tests do not state.",
        """
def test_punctuation_separates_words() -> None:
    assert tokenize_words("Hello, world!") == ["hello", "world"]


def test_an_apostrophe_stays_inside_a_word() -> None:
    assert tokenize_words("don't stop") == ["don't", "stop"]


def test_a_run_of_digits_is_kept_as_a_word() -> None:
    assert tokenize_words("top 5 hits") == ["top", "5", "hits"]
""",
        imports="from word_tokens import tokenize_words\n",
    ),
)

# ------------------------------------------------------------------------- state and idempotency

_G021 = D2TaskSpec(
    template_id="d4_state.advance_offset",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-advance-offset",
    module="stream_offset",
    module_doc="Advancing a stored stream offset.",
    issue=(
        "advance_offset() is documented to move a stored offset forward. Callers report that a "
        "replayed message rewinds the offset instead of leaving it alone, and that recording the "
        "very first offset crashes because there is nothing stored yet."
    ),
    expected=(
        "advance_offset(state, offset) returns state with the offset moved forward, leaves it "
        "alone when the new offset is not ahead of the stored one, and accepts the first offset "
        "against a state that has none."
    ),
    baseline_reason="the stored offset is read before it exists and overwritten without comparison",
    edge_cases=(
        "an offset behind the stored one leaves it alone",
        "the first offset is accepted against an empty state",
    ),
    baseline="""def advance_offset(state, offset):
    \"\"\"Return `state` with its stream offset advanced to `offset`.\"\"\"
    current = state["offset"]
    updated = dict(state)
    updated["offset"] = offset
    return updated""",
    variant_one="""def advance_offset(state, offset):
    \"\"\"Return `state` with its stream offset advanced to `offset`.\"\"\"
    current = state.get("offset")
    if current is not None and offset <= current:
        return dict(state)
    updated = dict(state)
    updated["offset"] = offset
    return updated""",
    variant_two="""def advance_offset(state, offset):
    \"\"\"Return `state` with its stream offset advanced to `offset`.\"\"\"
    updated = dict(state)
    if "offset" in updated:
        updated["offset"] = max(updated["offset"], offset)
    else:
        updated["offset"] = offset
    return updated""",
    variant_three="""def advance_offset(state, offset):
    \"\"\"Return `state` with its stream offset advanced to `offset`.\"\"\"
    current = state["offset"]
    updated = dict(state)
    if offset > current:
        updated["offset"] = offset
    return updated""",
    variant_four="""def advance_offset(state, offset):
    \"\"\"Return `state` with its stream offset advanced to `offset`.\"\"\"
    updated = dict(state)
    updated["offset"] = offset
    return updated""",
    visible_test=_test_module(
        "stream_offset",
        "Published contract for advancing a stream offset.",
        """
def test_a_later_offset_moves_the_stored_one() -> None:
    assert advance_offset({"offset": 5}, 7) == {"offset": 7}


def test_advancing_from_zero() -> None:
    assert advance_offset({"offset": 0}, 1) == {"offset": 1}
""",
        imports="from stream_offset import advance_offset\n",
    ),
    hidden_test=_test_module(
        "stream_offset",
        "The part of the contract the published tests do not state.",
        """
def test_a_later_offset_moves_the_stored_one() -> None:
    assert advance_offset({"offset": 5}, 7) == {"offset": 7}


def test_an_offset_behind_the_stored_one_leaves_it_alone() -> None:
    assert advance_offset({"offset": 5}, 3) == {"offset": 5}


def test_the_first_offset_is_accepted() -> None:
    assert advance_offset({}, 4) == {"offset": 4}
""",
        imports="from stream_offset import advance_offset\n",
    ),
)

_G022 = D2TaskSpec(
    template_id="d4_state.bind_alias",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-bind-alias",
    module="alias_registry",
    module_doc="Binding a short alias to a target name.",
    issue=(
        "bind_alias() is documented to bind an alias to a target. Callers report that rebinding "
        "an existing alias to a different target silently replaces it instead of being refused, "
        "and that an alias pointing at itself is accepted."
    ),
    expected=(
        "bind_alias(registry, alias, target) returns the registry with the binding added, raises "
        "ValueError when the alias already points somewhere else, and raises ValueError when the "
        "alias and the target are the same name."
    ),
    baseline_reason=(
        "the binding is written without checking what is already there or what it names"
    ),
    edge_cases=(
        "rebinding an alias to a different target is refused",
        "an alias pointing at itself is refused",
    ),
    baseline="""def bind_alias(registry, alias, target):
    \"\"\"Return `registry` with `alias` bound to `target`.\"\"\"
    bound = dict(registry)
    bound[alias] = target
    return bound""",
    variant_one="""def bind_alias(registry, alias, target):
    \"\"\"Return `registry` with `alias` bound to `target`.\"\"\"
    if alias == target:
        raise ValueError(f"{alias!r} cannot alias itself")
    existing = registry.get(alias)
    if existing is not None and existing != target:
        raise ValueError(f"{alias!r} already names {existing!r}")
    bound = dict(registry)
    bound[alias] = target
    return bound""",
    variant_two="""def bind_alias(registry, alias, target):
    \"\"\"Return `registry` with `alias` bound to `target`.\"\"\"
    conflicts = alias in registry and registry[alias] != target
    if conflicts or alias == target:
        raise ValueError(f"{alias!r} cannot be bound to {target!r}")
    return {**registry, alias: target}""",
    variant_three="""def bind_alias(registry, alias, target):
    \"\"\"Return `registry` with `alias` bound to `target`.\"\"\"
    existing = registry.get(alias)
    if existing is not None and existing != target:
        raise ValueError(f"{alias!r} already names {existing!r}")
    bound = dict(registry)
    bound[alias] = target
    return bound""",
    variant_four="""def bind_alias(registry, alias, target):
    \"\"\"Return `registry` with `alias` bound to `target`.\"\"\"
    if alias == target:
        raise ValueError(f"{alias!r} cannot alias itself")
    bound = dict(registry)
    bound[alias] = target
    return bound""",
    visible_test=_test_module(
        "alias_registry",
        "Published contract for binding an alias.",
        """
def test_a_new_alias_is_bound() -> None:
    assert bind_alias({}, "ls", "list") == {"ls": "list"}


def test_rebinding_to_the_same_target_is_accepted() -> None:
    assert bind_alias({"ls": "list"}, "ls", "list") == {"ls": "list"}
""",
        imports="from alias_registry import bind_alias\n",
    ),
    hidden_test=_test_module(
        "alias_registry",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_new_alias_is_bound() -> None:
    assert bind_alias({}, "ls", "list") == {"ls": "list"}


def test_rebinding_to_a_different_target_is_refused() -> None:
    with pytest.raises(ValueError):
        bind_alias({"ls": "list"}, "ls", "show")


def test_an_alias_pointing_at_itself_is_refused() -> None:
    with pytest.raises(ValueError):
        bind_alias({}, "ls", "ls")
""",
        imports="from alias_registry import bind_alias\n",
    ),
)

_G023 = D2TaskSpec(
    template_id="d4_state.mark_delivered",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-mark-delivered",
    module="delivery_state",
    module_doc="Marking a parcel as delivered.",
    issue=(
        "mark_delivered() is documented to record a delivery. Callers report that a duplicate "
        "delivery notice overwrites the original delivery time, and that a cancelled parcel can "
        "be marked delivered."
    ),
    expected=(
        "mark_delivered(parcel, at) returns the parcel marked delivered, keeps the first "
        "delivery time when it is already delivered, and raises ValueError for a cancelled "
        "parcel."
    ),
    baseline_reason="the time is written unconditionally and the current status is never read",
    edge_cases=(
        "a repeated delivery keeps the first time",
        "a cancelled parcel cannot be delivered",
    ),
    baseline="""def mark_delivered(parcel, at):
    \"\"\"Return `parcel` marked delivered at `at`.\"\"\"
    updated = dict(parcel)
    updated["status"] = "delivered"
    updated["delivered_at"] = at
    return updated""",
    variant_one="""def mark_delivered(parcel, at):
    \"\"\"Return `parcel` marked delivered at `at`.\"\"\"
    if parcel.get("status") == "cancelled":
        raise ValueError("a cancelled parcel cannot be delivered")
    if parcel.get("status") == "delivered":
        return dict(parcel)
    updated = dict(parcel)
    updated["status"] = "delivered"
    updated["delivered_at"] = at
    return updated""",
    variant_two="""def mark_delivered(parcel, at):
    \"\"\"Return `parcel` marked delivered at `at`.\"\"\"
    status = parcel.get("status")
    if status == "cancelled":
        raise ValueError("a cancelled parcel cannot be delivered")
    updated = dict(parcel)
    updated["status"] = "delivered"
    updated.setdefault("delivered_at", at)
    return updated""",
    variant_three="""def mark_delivered(parcel, at):
    \"\"\"Return `parcel` marked delivered at `at`.\"\"\"
    if parcel.get("status") == "delivered":
        return dict(parcel)
    updated = dict(parcel)
    updated["status"] = "delivered"
    updated["delivered_at"] = at
    return updated""",
    variant_four="""def mark_delivered(parcel, at):
    \"\"\"Return `parcel` marked delivered at `at`.\"\"\"
    if parcel.get("status") == "cancelled":
        raise ValueError("a cancelled parcel cannot be delivered")
    updated = dict(parcel)
    updated["status"] = "delivered"
    updated["delivered_at"] = at
    return updated""",
    visible_test=_test_module(
        "delivery_state",
        "Published contract for marking a delivery.",
        """
def test_a_pending_parcel_is_delivered() -> None:
    assert mark_delivered({"status": "pending"}, 10) == {
        "status": "delivered",
        "delivered_at": 10,
    }


def test_a_parcel_in_transit_is_delivered() -> None:
    assert mark_delivered({"status": "in_transit"}, 4) == {
        "status": "delivered",
        "delivered_at": 4,
    }
""",
        imports="from delivery_state import mark_delivered\n",
    ),
    hidden_test=_test_module(
        "delivery_state",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_pending_parcel_is_delivered() -> None:
    assert mark_delivered({"status": "pending"}, 10) == {
        "status": "delivered",
        "delivered_at": 10,
    }


def test_a_repeated_delivery_keeps_the_first_time() -> None:
    already = {"status": "delivered", "delivered_at": 3}
    assert mark_delivered(already, 9) == {"status": "delivered", "delivered_at": 3}


def test_a_cancelled_parcel_cannot_be_delivered() -> None:
    with pytest.raises(ValueError):
        mark_delivered({"status": "cancelled"}, 5)
""",
        imports="from delivery_state import mark_delivered\n",
    ),
)

_G024 = D2TaskSpec(
    template_id="d4_state.join_barrier",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-join-barrier",
    module="barrier_state",
    module_doc="Registering participants at a release barrier.",
    issue=(
        "join_barrier() is documented to register a participant. Callers report that a "
        "participant who retries is counted twice, and that a participant arriving after the "
        "barrier has already released is accepted instead of being refused."
    ),
    expected=(
        "join_barrier(barrier, name) returns the barrier with the participant registered once, "
        "ignores a repeat registration, and raises ValueError once the barrier has released."
    ),
    baseline_reason=(
        "the name is appended to a list without checking membership or the release flag"
    ),
    edge_cases=(
        "a repeated registration is ignored",
        "registering after release is refused",
    ),
    baseline="""def join_barrier(barrier, name):
    \"\"\"Return `barrier` with `name` registered.\"\"\"
    joined = dict(barrier)
    joined["waiting"] = list(barrier.get("waiting", [])) + [name]
    return joined""",
    variant_one="""def join_barrier(barrier, name):
    \"\"\"Return `barrier` with `name` registered.\"\"\"
    if barrier.get("released"):
        raise ValueError("the barrier has already released")
    waiting = list(barrier.get("waiting", []))
    if name in waiting:
        return dict(barrier)
    joined = dict(barrier)
    joined["waiting"] = waiting + [name]
    return joined""",
    variant_two="""def join_barrier(barrier, name):
    \"\"\"Return `barrier` with `name` registered.\"\"\"
    if barrier.get("released") is True:
        raise ValueError("the barrier has already released")
    waiting = list(barrier.get("waiting", []))
    joined = dict(barrier)
    joined["waiting"] = waiting if name in waiting else waiting + [name]
    return joined""",
    variant_three="""def join_barrier(barrier, name):
    \"\"\"Return `barrier` with `name` registered.\"\"\"
    waiting = list(barrier.get("waiting", []))
    if name in waiting:
        return dict(barrier)
    joined = dict(barrier)
    joined["waiting"] = waiting + [name]
    return joined""",
    variant_four="""def join_barrier(barrier, name):
    \"\"\"Return `barrier` with `name` registered.\"\"\"
    if barrier.get("released"):
        raise ValueError("the barrier has already released")
    joined = dict(barrier)
    joined["waiting"] = list(barrier.get("waiting", [])) + [name]
    return joined""",
    visible_test=_test_module(
        "barrier_state",
        "Published contract for joining a barrier.",
        """
def test_the_first_participant_is_registered() -> None:
    assert join_barrier({}, "a") == {"waiting": ["a"]}


def test_a_second_participant_is_registered() -> None:
    assert join_barrier({"waiting": ["a"]}, "b") == {"waiting": ["a", "b"]}
""",
        imports="from barrier_state import join_barrier\n",
    ),
    hidden_test=_test_module(
        "barrier_state",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_participant_is_registered() -> None:
    assert join_barrier({}, "a") == {"waiting": ["a"]}


def test_a_repeated_registration_is_ignored() -> None:
    assert join_barrier({"waiting": ["a"]}, "a") == {"waiting": ["a"]}


def test_registering_after_release_is_refused() -> None:
    with pytest.raises(ValueError):
        join_barrier({"waiting": [], "released": True}, "a")
""",
        imports="from barrier_state import join_barrier\n",
    ),
)

_G025 = D2TaskSpec(
    template_id="d4_state.apply_schema_step",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-apply-schema-step",
    module="schema_step",
    module_doc="Recording that a schema step has been applied.",
    issue=(
        "apply_step() is documented to record a schema step. Callers report that re-running a "
        "step that is already applied appends it a second time, and that a step numbered below "
        "the current one is accepted instead of being refused."
    ),
    expected=(
        "apply_step(state, step) records the step and moves the version forward, ignores a step "
        "already applied, and raises ValueError for a step numbered below the current version."
    ),
    baseline_reason="the step is appended and the version overwritten with no comparison at all",
    edge_cases=(
        "a step already applied is ignored",
        "a step below the current version is refused",
    ),
    baseline="""def apply_step(state, step):
    \"\"\"Return `state` with schema `step` recorded as applied.\"\"\"
    updated = dict(state)
    updated["applied"] = list(state.get("applied", [])) + [step]
    updated["version"] = step
    return updated""",
    variant_one="""def apply_step(state, step):
    \"\"\"Return `state` with schema `step` recorded as applied.\"\"\"
    applied = list(state.get("applied", []))
    if step in applied:
        return dict(state)
    if step < state.get("version", 0):
        raise ValueError(f"step {step} is below the current version")
    updated = dict(state)
    updated["applied"] = applied + [step]
    updated["version"] = step
    return updated""",
    variant_two="""def apply_step(state, step):
    \"\"\"Return `state` with schema `step` recorded as applied.\"\"\"
    applied = list(state.get("applied", []))
    version = state.get("version", 0)
    if step in applied:
        return dict(state)
    if not step >= version:
        raise ValueError(f"step {step} is below the current version")
    return {**state, "applied": applied + [step], "version": step}""",
    variant_three="""def apply_step(state, step):
    \"\"\"Return `state` with schema `step` recorded as applied.\"\"\"
    applied = list(state.get("applied", []))
    if step in applied:
        return dict(state)
    updated = dict(state)
    updated["applied"] = applied + [step]
    updated["version"] = step
    return updated""",
    variant_four="""def apply_step(state, step):
    \"\"\"Return `state` with schema `step` recorded as applied.\"\"\"
    if step < state.get("version", 0):
        raise ValueError(f"step {step} is below the current version")
    updated = dict(state)
    updated["applied"] = list(state.get("applied", [])) + [step]
    updated["version"] = step
    return updated""",
    visible_test=_test_module(
        "schema_step",
        "Published contract for applying a schema step.",
        """
def test_the_first_step_is_applied() -> None:
    assert apply_step({}, 1) == {"applied": [1], "version": 1}


def test_a_later_step_is_applied() -> None:
    assert apply_step({"applied": [1], "version": 1}, 2) == {
        "applied": [1, 2],
        "version": 2,
    }
""",
        imports="from schema_step import apply_step\n",
    ),
    hidden_test=_test_module(
        "schema_step",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_step_is_applied() -> None:
    assert apply_step({}, 1) == {"applied": [1], "version": 1}


def test_a_step_already_applied_is_ignored() -> None:
    state = {"applied": [1, 2], "version": 2}
    assert apply_step(state, 2) == state


def test_a_step_below_the_current_version_is_refused() -> None:
    with pytest.raises(ValueError):
        apply_step({"applied": [1, 5], "version": 5}, 3)
""",
        imports="from schema_step import apply_step\n",
    ),
)

_G026 = D2TaskSpec(
    template_id="d4_state.revoke_grant",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-revoke-grant",
    module="grant_revocation",
    module_doc="Revoking a permission grant.",
    issue=(
        "revoke_grant() is documented to revoke a grant. Callers report that revoking a grant "
        "nobody holds crashes instead of doing nothing, and that a grant already revoked has its "
        "revocation time rewritten by a retry."
    ),
    expected=(
        "revoke_grant(grants, holder, at) returns the grants with the holder's grant revoked, "
        "does nothing when the holder has no grant, and keeps the first revocation time."
    ),
    baseline_reason="the holder is indexed directly and the revocation time is always rewritten",
    edge_cases=(
        "revoking a grant nobody holds does nothing",
        "a repeated revocation keeps the first time",
    ),
    baseline="""def revoke_grant(grants, holder, at):
    \"\"\"Return `grants` with `holder`'s grant revoked at `at`.\"\"\"
    revoked = dict(grants)
    entry = dict(grants[holder])
    entry["revoked_at"] = at
    revoked[holder] = entry
    return revoked""",
    variant_one="""def revoke_grant(grants, holder, at):
    \"\"\"Return `grants` with `holder`'s grant revoked at `at`.\"\"\"
    if holder not in grants:
        return dict(grants)
    entry = dict(grants[holder])
    if "revoked_at" in entry:
        return dict(grants)
    entry["revoked_at"] = at
    revoked = dict(grants)
    revoked[holder] = entry
    return revoked""",
    variant_two="""def revoke_grant(grants, holder, at):
    \"\"\"Return `grants` with `holder`'s grant revoked at `at`.\"\"\"
    existing = grants.get(holder)
    if existing is None:
        return dict(grants)
    entry = dict(existing)
    entry.setdefault("revoked_at", at)
    return {**grants, holder: entry}""",
    variant_three="""def revoke_grant(grants, holder, at):
    \"\"\"Return `grants` with `holder`'s grant revoked at `at`.\"\"\"
    if holder not in grants:
        return dict(grants)
    entry = dict(grants[holder])
    entry["revoked_at"] = at
    revoked = dict(grants)
    revoked[holder] = entry
    return revoked""",
    variant_four="""def revoke_grant(grants, holder, at):
    \"\"\"Return `grants` with `holder`'s grant revoked at `at`.\"\"\"
    entry = dict(grants[holder])
    if "revoked_at" in entry:
        return dict(grants)
    entry["revoked_at"] = at
    revoked = dict(grants)
    revoked[holder] = entry
    return revoked""",
    visible_test=_test_module(
        "grant_revocation",
        "Published contract for revoking a grant.",
        """
def test_a_held_grant_is_revoked() -> None:
    grants = {"ann": {"scope": "read"}}
    assert revoke_grant(grants, "ann", 7) == {"ann": {"scope": "read", "revoked_at": 7}}


def test_other_holders_are_untouched() -> None:
    grants = {"ann": {"scope": "read"}, "bo": {"scope": "write"}}
    revoked = revoke_grant(grants, "ann", 7)
    assert revoked["bo"] == {"scope": "write"}
""",
        imports="from grant_revocation import revoke_grant\n",
    ),
    hidden_test=_test_module(
        "grant_revocation",
        "The part of the contract the published tests do not state.",
        """
def test_a_held_grant_is_revoked() -> None:
    grants = {"ann": {"scope": "read"}}
    assert revoke_grant(grants, "ann", 7) == {"ann": {"scope": "read", "revoked_at": 7}}


def test_revoking_a_grant_nobody_holds_does_nothing() -> None:
    assert revoke_grant({"ann": {"scope": "read"}}, "zed", 7) == {"ann": {"scope": "read"}}


def test_a_repeated_revocation_keeps_the_first_time() -> None:
    grants = {"ann": {"scope": "read", "revoked_at": 2}}
    assert revoke_grant(grants, "ann", 9) == {"ann": {"scope": "read", "revoked_at": 2}}
""",
        imports="from grant_revocation import revoke_grant\n",
    ),
)

_G027 = D2TaskSpec(
    template_id="d4_state.reserve_capacity",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-reserve-capacity",
    module="capacity_pool",
    module_doc="Reserving capacity from a shared pool.",
    issue=(
        "reserve_capacity() is documented to take capacity from a pool. Callers report that "
        "reserving more than remains leaves the pool negative instead of being refused, and that "
        "a reservation of zero still records a holder."
    ),
    expected=(
        "reserve_capacity(pool, holder, amount) returns the pool with the amount reserved, "
        "raises ValueError when the amount exceeds what remains, and records no holder for a "
        "reservation of zero."
    ),
    baseline_reason="the remaining capacity is decremented with no check on the amount",
    edge_cases=(
        "reserving more than remains is refused",
        "a reservation of zero records no holder",
    ),
    baseline="""def reserve_capacity(pool, holder, amount):
    \"\"\"Return `pool` with `amount` reserved for `holder`.\"\"\"
    updated = dict(pool)
    updated["remaining"] = pool["remaining"] - amount
    updated["holders"] = list(pool.get("holders", [])) + [holder]
    return updated""",
    variant_one="""def reserve_capacity(pool, holder, amount):
    \"\"\"Return `pool` with `amount` reserved for `holder`.\"\"\"
    if amount > pool["remaining"]:
        raise ValueError("not enough capacity remains")
    if amount == 0:
        return dict(pool)
    updated = dict(pool)
    updated["remaining"] = pool["remaining"] - amount
    updated["holders"] = list(pool.get("holders", [])) + [holder]
    return updated""",
    variant_two="""def reserve_capacity(pool, holder, amount):
    \"\"\"Return `pool` with `amount` reserved for `holder`.\"\"\"
    remaining = pool["remaining"]
    if not amount <= remaining:
        raise ValueError("not enough capacity remains")
    if not amount:
        return {**pool}
    holders = list(pool.get("holders", []))
    return {**pool, "remaining": remaining - amount, "holders": holders + [holder]}""",
    variant_three="""def reserve_capacity(pool, holder, amount):
    \"\"\"Return `pool` with `amount` reserved for `holder`.\"\"\"
    if amount > pool["remaining"]:
        raise ValueError("not enough capacity remains")
    updated = dict(pool)
    updated["remaining"] = pool["remaining"] - amount
    updated["holders"] = list(pool.get("holders", [])) + [holder]
    return updated""",
    variant_four="""def reserve_capacity(pool, holder, amount):
    \"\"\"Return `pool` with `amount` reserved for `holder`.\"\"\"
    if amount == 0:
        return dict(pool)
    updated = dict(pool)
    updated["remaining"] = pool["remaining"] - amount
    updated["holders"] = list(pool.get("holders", [])) + [holder]
    return updated""",
    visible_test=_test_module(
        "capacity_pool",
        "Published contract for reserving capacity.",
        """
def test_capacity_is_reserved() -> None:
    assert reserve_capacity({"remaining": 10}, "ann", 4) == {
        "remaining": 6,
        "holders": ["ann"],
    }


def test_reserving_everything_that_remains() -> None:
    assert reserve_capacity({"remaining": 3}, "bo", 3) == {
        "remaining": 0,
        "holders": ["bo"],
    }
""",
        imports="from capacity_pool import reserve_capacity\n",
    ),
    hidden_test=_test_module(
        "capacity_pool",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_capacity_is_reserved() -> None:
    assert reserve_capacity({"remaining": 10}, "ann", 4) == {
        "remaining": 6,
        "holders": ["ann"],
    }


def test_reserving_more_than_remains_is_refused() -> None:
    with pytest.raises(ValueError):
        reserve_capacity({"remaining": 2}, "ann", 5)


def test_a_reservation_of_zero_records_no_holder() -> None:
    assert reserve_capacity({"remaining": 5}, "ann", 0) == {"remaining": 5}
""",
        imports="from capacity_pool import reserve_capacity\n",
    ),
)

_G028 = D2TaskSpec(
    template_id="d4_state.transition_history",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-transition-history",
    module="transition_history",
    module_doc="Appending to a written transition history.",
    issue=(
        "record_transition() is documented to append a state to a history written as an "
        "arrow-separated trail. Callers report that recording the state the trail already ends "
        "in appends it again, and that a transition the machine does not allow is accepted."
    ),
    expected=(
        "record_transition(trail, state) returns the trail with the state appended, leaves the "
        "trail alone when it already ends in that state, and raises ValueError when the machine "
        "does not allow the move."
    ),
    baseline_reason="the state is appended without reading the tail of the trail or the table",
    edge_cases=(
        "recording the current state leaves the trail alone",
        "a transition the machine forbids is refused",
    ),
    baseline="""def record_transition(trail, state):
    \"\"\"Return `trail` with `state` appended to the arrow-separated history.\"\"\"
    if not trail:
        return state
    return trail + ">" + state""",
    variant_one="""def record_transition(trail, state):
    \"\"\"Return `trail` with `state` appended to the arrow-separated history.\"\"\"
    allowed = {"new": ("ready",), "ready": ("running",), "running": ("done", "failed")}
    if not trail:
        return state
    current = trail.split(">")[-1]
    if current == state:
        return trail
    if state not in allowed.get(current, ()):
        raise ValueError(f"{current!r} cannot move to {state!r}")
    return trail + ">" + state""",
    variant_two="""def record_transition(trail, state):
    \"\"\"Return `trail` with `state` appended to the arrow-separated history.\"\"\"
    allowed = {"new": ("ready",), "ready": ("running",), "running": ("done", "failed")}
    steps = trail.split(">") if trail else []
    if not steps:
        return state
    if steps[-1] == state:
        return trail
    if state not in allowed.get(steps[-1], ()):
        raise ValueError(f"{steps[-1]!r} cannot move to {state!r}")
    return ">".join(steps + [state])""",
    variant_three="""def record_transition(trail, state):
    \"\"\"Return `trail` with `state` appended to the arrow-separated history.\"\"\"
    if not trail:
        return state
    if trail.split(">")[-1] == state:
        return trail
    return trail + ">" + state""",
    variant_four="""def record_transition(trail, state):
    \"\"\"Return `trail` with `state` appended to the arrow-separated history.\"\"\"
    allowed = {"new": ("ready",), "ready": ("running",), "running": ("done", "failed")}
    if not trail:
        return state
    current = trail.split(">")[-1]
    if state not in allowed.get(current, ()):
        raise ValueError(f"{current!r} cannot move to {state!r}")
    return trail + ">" + state""",
    visible_test=_test_module(
        "transition_history",
        "Published contract for recording a transition.",
        """
def test_the_first_state_starts_the_trail() -> None:
    assert record_transition("", "new") == "new"


def test_an_allowed_move_is_appended() -> None:
    assert record_transition("new", "ready") == "new>ready"
""",
        imports="from transition_history import record_transition\n",
    ),
    hidden_test=_test_module(
        "transition_history",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_state_starts_the_trail() -> None:
    assert record_transition("", "new") == "new"


def test_recording_the_current_state_leaves_the_trail_alone() -> None:
    assert record_transition("new>ready", "ready") == "new>ready"


def test_a_forbidden_transition_is_refused() -> None:
    with pytest.raises(ValueError):
        record_transition("new>ready", "done")
""",
        imports="from transition_history import record_transition\n",
    ),
)

_G029 = D2TaskSpec(
    template_id="d4_state.record_vote",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-record-vote",
    module="ballot_box",
    module_doc="Recording a vote in a ballot.",
    issue=(
        "record_vote() is documented to record one vote per voter. Callers report that a voter "
        "changing their mind adds a second vote instead of replacing the first, and that a vote "
        "cast after the ballot closed is accepted."
    ),
    expected=(
        "record_vote(ballot, voter, choice) returns the ballot with the voter's single current "
        "choice recorded, replacing any earlier one, and raises ValueError once the ballot is "
        "closed."
    ),
    baseline_reason="votes are appended to a list and the closed flag is never read",
    edge_cases=(
        "a changed vote replaces the earlier one",
        "a vote after closing is refused",
    ),
    baseline="""def record_vote(ballot, voter, choice):
    \"\"\"Return `ballot` with `voter`'s `choice` recorded.\"\"\"
    updated = dict(ballot)
    updated["votes"] = list(ballot.get("votes", [])) + [(voter, choice)]
    return updated""",
    variant_one="""def record_vote(ballot, voter, choice):
    \"\"\"Return `ballot` with `voter`'s `choice` recorded.\"\"\"
    if ballot.get("closed"):
        raise ValueError("the ballot is closed")
    votes = [pair for pair in ballot.get("votes", []) if pair[0] != voter]
    updated = dict(ballot)
    updated["votes"] = votes + [(voter, choice)]
    return updated""",
    variant_two="""def record_vote(ballot, voter, choice):
    \"\"\"Return `ballot` with `voter`'s `choice` recorded.\"\"\"
    if ballot.get("closed") is True:
        raise ValueError("the ballot is closed")
    kept = []
    for name, cast in ballot.get("votes", []):
        if name != voter:
            kept.append((name, cast))
    return {**ballot, "votes": kept + [(voter, choice)]}""",
    variant_three="""def record_vote(ballot, voter, choice):
    \"\"\"Return `ballot` with `voter`'s `choice` recorded.\"\"\"
    votes = [pair for pair in ballot.get("votes", []) if pair[0] != voter]
    updated = dict(ballot)
    updated["votes"] = votes + [(voter, choice)]
    return updated""",
    variant_four="""def record_vote(ballot, voter, choice):
    \"\"\"Return `ballot` with `voter`'s `choice` recorded.\"\"\"
    if ballot.get("closed"):
        raise ValueError("the ballot is closed")
    updated = dict(ballot)
    updated["votes"] = list(ballot.get("votes", [])) + [(voter, choice)]
    return updated""",
    visible_test=_test_module(
        "ballot_box",
        "Published contract for recording a vote.",
        """
def test_a_first_vote_is_recorded() -> None:
    assert record_vote({}, "ann", "yes") == {"votes": [("ann", "yes")]}


def test_a_second_voter_is_recorded() -> None:
    ballot = {"votes": [("ann", "yes")]}
    assert record_vote(ballot, "bo", "no") == {
        "votes": [("ann", "yes"), ("bo", "no")]
    }
""",
        imports="from ballot_box import record_vote\n",
    ),
    hidden_test=_test_module(
        "ballot_box",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_first_vote_is_recorded() -> None:
    assert record_vote({}, "ann", "yes") == {"votes": [("ann", "yes")]}


def test_a_changed_vote_replaces_the_earlier_one() -> None:
    ballot = {"votes": [("ann", "yes"), ("bo", "no")]}
    assert record_vote(ballot, "ann", "no") == {
        "votes": [("bo", "no"), ("ann", "no")]
    }


def test_a_vote_after_closing_is_refused() -> None:
    with pytest.raises(ValueError):
        record_vote({"votes": [], "closed": True}, "ann", "yes")
""",
        imports="from ballot_box import record_vote\n",
    ),
)

_G030 = D2TaskSpec(
    template_id="d4_state.permission_mask",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-permission-mask",
    module="permission_mask",
    module_doc="Granting a permission held as a bit in a mask.",
    issue=(
        "grant_bit() is documented to grant a permission held as one bit of a mask. Callers "
        "report that granting a permission somebody already holds corrupts the mask instead of "
        "leaving it alone, and that a bit position outside the mask is accepted."
    ),
    expected=(
        "grant_bit(mask, position) returns the mask with the bit set, leaves the mask unchanged "
        "when the bit is already set, and raises ValueError for a position outside 0 to 31."
    ),
    baseline_reason="the bit is added rather than merged, and the position is never range-checked",
    edge_cases=(
        "granting a bit already set leaves the mask unchanged",
        "a bit position outside the mask is refused",
    ),
    baseline="""def grant_bit(mask, position):
    \"\"\"Return `mask` with the bit at `position` granted.\"\"\"
    return mask + (1 << position)""",
    variant_one="""def grant_bit(mask, position):
    \"\"\"Return `mask` with the bit at `position` granted.\"\"\"
    if position < 0 or position > 31:
        raise ValueError(f"bit {position} is outside the mask")
    return mask | (1 << position)""",
    variant_two="""def grant_bit(mask, position):
    \"\"\"Return `mask` with the bit at `position` granted.\"\"\"
    if not 0 <= position <= 31:
        raise ValueError(f"bit {position} is outside the mask")
    bit = 1 << position
    return mask if mask & bit else mask + bit""",
    variant_three="""def grant_bit(mask, position):
    \"\"\"Return `mask` with the bit at `position` granted.\"\"\"
    return mask | (1 << position)""",
    variant_four="""def grant_bit(mask, position):
    \"\"\"Return `mask` with the bit at `position` granted.\"\"\"
    if position < 0 or position > 31:
        raise ValueError(f"bit {position} is outside the mask")
    return mask + (1 << position)""",
    visible_test=_test_module(
        "permission_mask",
        "Published contract for granting a permission bit.",
        """
def test_the_first_permission_is_granted() -> None:
    assert grant_bit(0, 0) == 1


def test_a_second_permission_is_granted() -> None:
    assert grant_bit(1, 2) == 5
""",
        imports="from permission_mask import grant_bit\n",
    ),
    hidden_test=_test_module(
        "permission_mask",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_permission_is_granted() -> None:
    assert grant_bit(0, 0) == 1


def test_granting_a_bit_already_set_leaves_the_mask_unchanged() -> None:
    assert grant_bit(1, 0) == 1


def test_a_bit_outside_the_mask_is_refused() -> None:
    with pytest.raises(ValueError):
        grant_bit(0, 64)
""",
        imports="from permission_mask import grant_bit\n",
    ),
)

# ------------------------------------------------------------------------------- numeric logic

_G031 = D2TaskSpec(
    template_id="d4_numeric.positive_remainder",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-positive-remainder",
    module="positive_remainder",
    module_doc="Taking a remainder that is never negative.",
    issue=(
        "positive_remainder() is documented to return a remainder in the range zero to just "
        "below the modulus. Callers report that a negative input gives the remainder of its "
        "magnitude instead, and that a modulus of zero raises an arithmetic error rather than "
        "being reported as a bad argument."
    ),
    expected=(
        "positive_remainder(value, modulus) returns a remainder between zero and the modulus for "
        "any sign of value, and raises ValueError when the modulus is zero."
    ),
    baseline_reason="the sign is thrown away before the division and the modulus is never checked",
    edge_cases=(
        "a negative value still gives a non-negative remainder",
        "a modulus of zero is reported as a bad argument",
    ),
    baseline="""def positive_remainder(value, modulus):
    \"\"\"Return the non-negative remainder of `value` divided by `modulus`.\"\"\"
    return abs(value) % modulus""",
    variant_one="""def positive_remainder(value, modulus):
    \"\"\"Return the non-negative remainder of `value` divided by `modulus`.\"\"\"
    if modulus == 0:
        raise ValueError("the modulus cannot be zero")
    return value % modulus""",
    variant_two="""def positive_remainder(value, modulus):
    \"\"\"Return the non-negative remainder of `value` divided by `modulus`.\"\"\"
    if not modulus:
        raise ValueError("the modulus cannot be zero")
    remainder = value - (value // modulus) * modulus
    while remainder < 0:
        remainder += modulus
    return remainder""",
    variant_three="""def positive_remainder(value, modulus):
    \"\"\"Return the non-negative remainder of `value` divided by `modulus`.\"\"\"
    return value % modulus""",
    variant_four="""def positive_remainder(value, modulus):
    \"\"\"Return the non-negative remainder of `value` divided by `modulus`.\"\"\"
    if modulus == 0:
        raise ValueError("the modulus cannot be zero")
    return abs(value) % modulus""",
    visible_test=_test_module(
        "positive_remainder",
        "Published contract for a non-negative remainder.",
        """
def test_a_plain_remainder() -> None:
    assert positive_remainder(7, 3) == 1


def test_an_exact_multiple_has_no_remainder() -> None:
    assert positive_remainder(9, 3) == 0
""",
        imports="from positive_remainder import positive_remainder\n",
    ),
    hidden_test=_test_module(
        "positive_remainder",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_plain_remainder() -> None:
    assert positive_remainder(7, 3) == 1


def test_a_negative_value_gives_a_non_negative_remainder() -> None:
    assert positive_remainder(-7, 3) == 2


def test_a_modulus_of_zero_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        positive_remainder(7, 0)
""",
        imports="from positive_remainder import positive_remainder\n",
    ),
)

_G032 = D2TaskSpec(
    template_id="d4_numeric.rounded_up_division",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-rounded-up-division",
    module="page_count",
    module_doc="Counting how many pages a number of rows needs.",
    issue=(
        "pages_needed() is documented to count the pages a number of rows needs. Callers report "
        "that a row count filling its pages exactly gets one page too many, and that a page size "
        "of zero raises an arithmetic error instead of a bad-argument error."
    ),
    expected=(
        "pages_needed(rows, size) returns the number of pages needed, adds no extra page when "
        "the rows divide exactly, and raises ValueError for a page size of zero."
    ),
    baseline_reason="a page is always added after the floor division, and the size is not checked",
    edge_cases=(
        "an exact fit needs no extra page",
        "a page size of zero is reported as a bad argument",
    ),
    baseline="""def pages_needed(rows, size):
    \"\"\"Return how many pages of `size` rows are needed for `rows` rows.\"\"\"
    return rows // size + 1""",
    variant_one="""def pages_needed(rows, size):
    \"\"\"Return how many pages of `size` rows are needed for `rows` rows.\"\"\"
    if size == 0:
        raise ValueError("a page cannot hold zero rows")
    return -(-rows // size)""",
    variant_two="""def pages_needed(rows, size):
    \"\"\"Return how many pages of `size` rows are needed for `rows` rows.\"\"\"
    if size == 0:
        raise ValueError("a page cannot hold zero rows")
    whole, left_over = divmod(rows, size)
    return whole + 1 if left_over else whole""",
    variant_three="""def pages_needed(rows, size):
    \"\"\"Return how many pages of `size` rows are needed for `rows` rows.\"\"\"
    whole, left_over = divmod(rows, size)
    return whole + 1 if left_over else whole""",
    variant_four="""def pages_needed(rows, size):
    \"\"\"Return how many pages of `size` rows are needed for `rows` rows.\"\"\"
    if size == 0:
        raise ValueError("a page cannot hold zero rows")
    return rows // size + 1""",
    visible_test=_test_module(
        "page_count",
        "Published contract for counting pages.",
        """
def test_rows_that_overflow_a_page() -> None:
    assert pages_needed(7, 3) == 3


def test_fewer_rows_than_one_page() -> None:
    assert pages_needed(1, 3) == 1
""",
        imports="from page_count import pages_needed\n",
    ),
    hidden_test=_test_module(
        "page_count",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_rows_that_overflow_a_page() -> None:
    assert pages_needed(7, 3) == 3


def test_an_exact_fit_needs_no_extra_page() -> None:
    assert pages_needed(6, 3) == 2


def test_a_page_size_of_zero_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        pages_needed(5, 0)
""",
        imports="from page_count import pages_needed\n",
    ),
)

_G033 = D2TaskSpec(
    template_id="d4_numeric.lowest_common_multiple",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-lowest-common-multiple",
    module="common_multiple",
    module_doc="Finding the lowest multiple two numbers share.",
    issue=(
        "lowest_common_multiple() is documented to return the smallest positive multiple two "
        "numbers share. Callers report that a negative argument yields a negative multiple, and "
        "that two zeros raise an arithmetic error instead of being reported as bad arguments."
    ),
    expected=(
        "lowest_common_multiple(first, second) returns the smallest positive shared multiple "
        "regardless of sign, and raises ValueError when both arguments are zero."
    ),
    baseline_reason=(
        "the signs are carried through the product and the all-zero case is not checked"
    ),
    edge_cases=(
        "a negative argument still yields a positive multiple",
        "two zeros are reported as bad arguments",
    ),
    baseline="""def lowest_common_multiple(first, second):
    \"\"\"Return the smallest positive multiple shared by `first` and `second`.\"\"\"
    left, right = first, second
    while right:
        left, right = right, left % right
    return first * second // left""",
    variant_one="""def lowest_common_multiple(first, second):
    \"\"\"Return the smallest positive multiple shared by `first` and `second`.\"\"\"
    if first == 0 and second == 0:
        raise ValueError("two zeros share no positive multiple")
    left, right = abs(first), abs(second)
    while right:
        left, right = right, left % right
    return abs(first * second) // left""",
    variant_two="""def lowest_common_multiple(first, second):
    \"\"\"Return the smallest positive multiple shared by `first` and `second`.\"\"\"
    if not first and not second:
        raise ValueError("two zeros share no positive multiple")
    larger = max(abs(first), abs(second))
    smaller = min(abs(first), abs(second))
    while smaller:
        larger, smaller = smaller, larger % smaller
    return abs(first) // larger * abs(second)""",
    variant_three="""def lowest_common_multiple(first, second):
    \"\"\"Return the smallest positive multiple shared by `first` and `second`.\"\"\"
    left, right = abs(first), abs(second)
    while right:
        left, right = right, left % right
    return abs(first * second) // left""",
    variant_four="""def lowest_common_multiple(first, second):
    \"\"\"Return the smallest positive multiple shared by `first` and `second`.\"\"\"
    if first == 0 and second == 0:
        raise ValueError("two zeros share no positive multiple")
    left, right = first, second
    while right:
        left, right = right, left % right
    return first * second // left""",
    visible_test=_test_module(
        "common_multiple",
        "Published contract for the lowest common multiple.",
        """
def test_two_numbers_sharing_a_factor() -> None:
    assert lowest_common_multiple(4, 6) == 12


def test_two_numbers_sharing_nothing() -> None:
    assert lowest_common_multiple(3, 5) == 15
""",
        imports="from common_multiple import lowest_common_multiple\n",
    ),
    hidden_test=_test_module(
        "common_multiple",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_numbers_sharing_a_factor() -> None:
    assert lowest_common_multiple(4, 6) == 12


def test_a_negative_argument_still_yields_a_positive_multiple() -> None:
    assert lowest_common_multiple(-4, 6) == 12


def test_two_zeros_are_bad_arguments() -> None:
    with pytest.raises(ValueError):
        lowest_common_multiple(0, 0)
""",
        imports="from common_multiple import lowest_common_multiple\n",
    ),
)

_G034 = D2TaskSpec(
    template_id="d4_numeric.share_out",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-share-out",
    module="share_out",
    module_doc="Sharing a whole number out into equal parts.",
    issue=(
        "share_out() is documented to share a total into parts as evenly as possible. Callers "
        "report that the remainder is silently dropped so the parts no longer add up to the "
        "total, and that asking for zero parts raises an arithmetic error."
    ),
    expected=(
        "share_out(total, parts) returns that many shares adding up to the total, giving the "
        "earlier shares the extra unit, and raises ValueError when parts is zero."
    ),
    baseline_reason="every share gets the floor and the leftover is never handed out",
    edge_cases=(
        "the shares add up to the total",
        "zero parts is reported as a bad argument",
    ),
    baseline="""def share_out(total, parts):
    \"\"\"Return `parts` shares of `total`, as evenly as possible.\"\"\"
    return [total // parts] * parts""",
    variant_one="""def share_out(total, parts):
    \"\"\"Return `parts` shares of `total`, as evenly as possible.\"\"\"
    if parts == 0:
        raise ValueError("a total cannot be shared into zero parts")
    each, left_over = divmod(total, parts)
    return [each + 1 if index < left_over else each for index in range(parts)]""",
    variant_two="""def share_out(total, parts):
    \"\"\"Return `parts` shares of `total`, as evenly as possible.\"\"\"
    if parts == 0:
        raise ValueError("a total cannot be shared into zero parts")
    shares = []
    remaining = total
    for place in range(parts, 0, -1):
        piece = -(-remaining // place)
        shares.append(piece)
        remaining -= piece
    return shares""",
    variant_three="""def share_out(total, parts):
    \"\"\"Return `parts` shares of `total`, as evenly as possible.\"\"\"
    each, left_over = divmod(total, parts)
    return [each + 1 if index < left_over else each for index in range(parts)]""",
    variant_four="""def share_out(total, parts):
    \"\"\"Return `parts` shares of `total`, as evenly as possible.\"\"\"
    if parts == 0:
        raise ValueError("a total cannot be shared into zero parts")
    return [total // parts] * parts""",
    visible_test=_test_module(
        "share_out",
        "Published contract for sharing a total.",
        """
def test_a_total_that_divides_evenly() -> None:
    assert share_out(6, 3) == [2, 2, 2]


def test_a_larger_even_share() -> None:
    assert share_out(10, 5) == [2, 2, 2, 2, 2]
""",
        imports="from share_out import share_out\n",
    ),
    hidden_test=_test_module(
        "share_out",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_total_that_divides_evenly() -> None:
    assert share_out(6, 3) == [2, 2, 2]


def test_the_shares_add_up_to_the_total() -> None:
    assert share_out(7, 3) == [3, 2, 2]


def test_zero_parts_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        share_out(5, 0)
""",
        imports="from share_out import share_out\n",
    ),
)

_G035 = D2TaskSpec(
    template_id="d4_numeric.approach_target",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-approach-target",
    module="approach_target",
    module_doc="Moving a value toward a target by a bounded step.",
    issue=(
        "approach() is documented to move a value toward a target by at most one step. Callers "
        "report that a step larger than the remaining distance overshoots the target, and that a "
        "negative step is accepted and moves the value backwards."
    ),
    expected=(
        "approach(current, target, step) moves current toward target by at most step, never past "
        "the target, and raises ValueError for a negative step."
    ),
    baseline_reason="the step is added or subtracted whole, and its sign is never checked",
    edge_cases=(
        "a step larger than the distance stops at the target",
        "a negative step is reported as a bad argument",
    ),
    baseline="""def approach(current, target, step):
    \"\"\"Return `current` moved toward `target` by at most `step`.\"\"\"
    if target > current:
        return current + step
    return current - step""",
    variant_one="""def approach(current, target, step):
    \"\"\"Return `current` moved toward `target` by at most `step`.\"\"\"
    if step < 0:
        raise ValueError("a step cannot be negative")
    if target > current:
        return min(current + step, target)
    return max(current - step, target)""",
    variant_two="""def approach(current, target, step):
    \"\"\"Return `current` moved toward `target` by at most `step`.\"\"\"
    if step < 0:
        raise ValueError("a step cannot be negative")
    distance = target - current
    if abs(distance) <= step:
        return target
    return current + step if distance > 0 else current - step""",
    variant_three="""def approach(current, target, step):
    \"\"\"Return `current` moved toward `target` by at most `step`.\"\"\"
    if target > current:
        return min(current + step, target)
    return max(current - step, target)""",
    variant_four="""def approach(current, target, step):
    \"\"\"Return `current` moved toward `target` by at most `step`.\"\"\"
    if step < 0:
        raise ValueError("a step cannot be negative")
    if target > current:
        return current + step
    return current - step""",
    visible_test=_test_module(
        "approach_target",
        "Published contract for a bounded approach.",
        """
def test_moving_up_toward_a_distant_target() -> None:
    assert approach(0, 10, 3) == 3


def test_moving_down_toward_a_distant_target() -> None:
    assert approach(10, 0, 4) == 6
""",
        imports="from approach_target import approach\n",
    ),
    hidden_test=_test_module(
        "approach_target",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_moving_up_toward_a_distant_target() -> None:
    assert approach(0, 10, 3) == 3


def test_a_step_larger_than_the_distance_stops_at_the_target() -> None:
    assert approach(0, 2, 5) == 2


def test_a_negative_step_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        approach(0, 10, -1)
""",
        imports="from approach_target import approach\n",
    ),
)

_G036 = D2TaskSpec(
    template_id="d4_numeric.weighted_score",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-weighted-score",
    module="weighted_score",
    module_doc="Combining scores under their weights.",
    issue=(
        "weighted_score() is documented to combine scores under matching weights. Callers report "
        "that a short weight list silently ignores the trailing scores, and that weights adding "
        "up to zero raise an arithmetic error rather than being reported as bad arguments."
    ),
    expected=(
        "weighted_score(scores, weights) returns the weighted average, raises ValueError when "
        "the two lists differ in length, and raises ValueError when the weights add up to zero."
    ),
    baseline_reason="zip stops at the shorter list and the divisor is never inspected",
    edge_cases=(
        "lists of different lengths are reported as bad arguments",
        "weights adding up to zero are reported as bad arguments",
    ),
    baseline="""def weighted_score(scores, weights):
    \"\"\"Return the average of `scores` under `weights`.\"\"\"
    paired = zip(scores, weights)
    return sum(score * weight for score, weight in paired) / sum(weights)""",
    variant_one="""def weighted_score(scores, weights):
    \"\"\"Return the average of `scores` under `weights`.\"\"\"
    if len(scores) != len(weights):
        raise ValueError("every score needs exactly one weight")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("the weights cannot add up to zero")
    paired = zip(scores, weights)
    return sum(score * weight for score, weight in paired) / total_weight""",
    variant_two="""def weighted_score(scores, weights):
    \"\"\"Return the average of `scores` under `weights`.\"\"\"
    values = list(scores)
    shares = list(weights)
    if len(values) != len(shares):
        raise ValueError("every score needs exactly one weight")
    running = 0
    divisor = 0
    for place, value in enumerate(values):
        running += value * shares[place]
        divisor += shares[place]
    if not divisor:
        raise ValueError("the weights cannot add up to zero")
    return running / divisor""",
    variant_three="""def weighted_score(scores, weights):
    \"\"\"Return the average of `scores` under `weights`.\"\"\"
    if len(scores) != len(weights):
        raise ValueError("every score needs exactly one weight")
    paired = zip(scores, weights)
    return sum(score * weight for score, weight in paired) / sum(weights)""",
    variant_four="""def weighted_score(scores, weights):
    \"\"\"Return the average of `scores` under `weights`.\"\"\"
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("the weights cannot add up to zero")
    paired = zip(scores, weights)
    return sum(score * weight for score, weight in paired) / total_weight""",
    visible_test=_test_module(
        "weighted_score",
        "Published contract for a weighted score.",
        """
def test_two_equally_weighted_scores() -> None:
    assert weighted_score([1, 2], [1, 1]) == 1.5


def test_a_single_score() -> None:
    assert weighted_score([10], [2]) == 10.0
""",
        imports="from weighted_score import weighted_score\n",
    ),
    hidden_test=_test_module(
        "weighted_score",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_equally_weighted_scores() -> None:
    assert weighted_score([1, 2], [1, 1]) == 1.5


def test_lists_of_different_lengths_are_bad_arguments() -> None:
    with pytest.raises(ValueError):
        weighted_score([1, 2], [1])


def test_weights_adding_up_to_zero_are_bad_arguments() -> None:
    with pytest.raises(ValueError):
        weighted_score([1, 2], [0, 0])
""",
        imports="from weighted_score import weighted_score\n",
    ),
)

_G037 = D2TaskSpec(
    template_id="d4_numeric.render_in_base",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-render-in-base",
    module="base_render",
    module_doc="Writing a number out in another base.",
    issue=(
        "render_in_base() is documented to write a number in a base between two and thirty-six. "
        "Callers report that zero comes back as an empty string, and that a base beyond "
        "thirty-six is accepted and produces nonsense."
    ),
    expected=(
        "render_in_base(number, base) returns the number written in that base, writes zero as "
        "'0', and raises ValueError for a base outside two to thirty-six."
    ),
    baseline_reason="the loop never runs for zero, and the base is trusted to be in range",
    edge_cases=(
        "zero is written as a single nought",
        "a base outside two to thirty-six is refused",
    ),
    baseline="""def render_in_base(number, base):
    \"\"\"Return `number` written in `base`.\"\"\"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    written = ""
    remaining = number
    while remaining:
        written = digits[remaining % base] + written
        remaining //= base
    return written""",
    variant_one="""def render_in_base(number, base):
    \"\"\"Return `number` written in `base`.\"\"\"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if base < 2 or base > 36:
        raise ValueError("the base must be between two and thirty-six")
    if number == 0:
        return "0"
    written = ""
    remaining = number
    while remaining:
        written = digits[remaining % base] + written
        remaining //= base
    return written""",
    variant_two="""def render_in_base(number, base):
    \"\"\"Return `number` written in `base`.\"\"\"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if not 2 <= base <= 36:
        raise ValueError("the base must be between two and thirty-six")
    places = []
    remaining = number
    while remaining:
        remaining, place = divmod(remaining, base)
        places.append(digits[place])
    return "".join(reversed(places)) or "0" """,
    variant_three="""def render_in_base(number, base):
    \"\"\"Return `number` written in `base`.\"\"\"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if number == 0:
        return "0"
    written = ""
    remaining = number
    while remaining:
        written = digits[remaining % base] + written
        remaining //= base
    return written""",
    variant_four="""def render_in_base(number, base):
    \"\"\"Return `number` written in `base`.\"\"\"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if base < 2 or base > 36:
        raise ValueError("the base must be between two and thirty-six")
    written = ""
    remaining = number
    while remaining:
        written = digits[remaining % base] + written
        remaining //= base
    return written""",
    visible_test=_test_module(
        "base_render",
        "Published contract for writing a number in another base.",
        """
def test_ten_in_binary() -> None:
    assert render_in_base(10, 2) == "1010"


def test_two_hundred_and_fifty_five_in_hexadecimal() -> None:
    assert render_in_base(255, 16) == "ff"
""",
        imports="from base_render import render_in_base\n",
    ),
    hidden_test=_test_module(
        "base_render",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_ten_in_binary() -> None:
    assert render_in_base(10, 2) == "1010"


def test_zero_is_written_as_a_single_nought() -> None:
    assert render_in_base(0, 2) == "0"


def test_a_base_beyond_thirty_six_is_refused() -> None:
    with pytest.raises(ValueError):
        render_in_base(10, 40)
""",
        imports="from base_render import render_in_base\n",
    ),
)

_G038 = D2TaskSpec(
    template_id="d4_numeric.overlap_length",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-overlap-length",
    module="interval_overlap",
    module_doc="Measuring how far two inclusive intervals overlap.",
    issue=(
        "overlap_length() is documented to measure how far two inclusive intervals overlap. "
        "Callers report that two intervals that do not meet report a negative overlap, and that "
        "an interval written with its bounds the wrong way round is accepted."
    ),
    expected=(
        "overlap_length(first, second) returns how many whole positions the two inclusive "
        "intervals share, reports zero when they do not meet, and raises ValueError when either "
        "interval has its bounds reversed."
    ),
    baseline_reason="the difference is returned as computed, and neither interval is checked",
    edge_cases=(
        "intervals that do not meet overlap by nothing",
        "an interval with reversed bounds is refused",
    ),
    baseline="""def overlap_length(first, second):
    \"\"\"Return how many positions the inclusive intervals `first` and `second` share.\"\"\"
    low = max(first[0], second[0])
    high = min(first[1], second[1])
    return high - low + 1""",
    variant_one="""def overlap_length(first, second):
    \"\"\"Return how many positions the inclusive intervals `first` and `second` share.\"\"\"
    for interval in (first, second):
        if interval[0] > interval[1]:
            raise ValueError(f"{interval!r} has its bounds reversed")
    low = max(first[0], second[0])
    high = min(first[1], second[1])
    return max(0, high - low + 1)""",
    variant_two="""def overlap_length(first, second):
    \"\"\"Return how many positions the inclusive intervals `first` and `second` share.\"\"\"
    if first[0] > first[1] or second[0] > second[1]:
        raise ValueError("an interval cannot have its bounds reversed")
    low = max(first[0], second[0])
    high = min(first[1], second[1])
    return high - low + 1 if high >= low else 0""",
    variant_three="""def overlap_length(first, second):
    \"\"\"Return how many positions the inclusive intervals `first` and `second` share.\"\"\"
    low = max(first[0], second[0])
    high = min(first[1], second[1])
    return max(0, high - low + 1)""",
    variant_four="""def overlap_length(first, second):
    \"\"\"Return how many positions the inclusive intervals `first` and `second` share.\"\"\"
    for interval in (first, second):
        if interval[0] > interval[1]:
            raise ValueError(f"{interval!r} has its bounds reversed")
    low = max(first[0], second[0])
    high = min(first[1], second[1])
    return high - low + 1""",
    visible_test=_test_module(
        "interval_overlap",
        "Published contract for measuring an overlap.",
        """
def test_two_partly_overlapping_intervals() -> None:
    assert overlap_length((1, 5), (3, 8)) == 3


def test_one_interval_inside_another() -> None:
    assert overlap_length((1, 10), (2, 4)) == 3
""",
        imports="from interval_overlap import overlap_length\n",
    ),
    hidden_test=_test_module(
        "interval_overlap",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_partly_overlapping_intervals() -> None:
    assert overlap_length((1, 5), (3, 8)) == 3


def test_intervals_that_do_not_meet_overlap_by_nothing() -> None:
    assert overlap_length((1, 2), (5, 6)) == 0


def test_an_interval_with_reversed_bounds_is_refused() -> None:
    with pytest.raises(ValueError):
        overlap_length((5, 1), (2, 3))
""",
        imports="from interval_overlap import overlap_length\n",
    ),
)

_G039 = D2TaskSpec(
    template_id="d4_numeric.roman_value",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-roman-value",
    module="roman_value",
    module_doc="Reading the value of a Roman numeral.",
    issue=(
        "roman_value() is documented to read a Roman numeral. Callers report that a subtractive "
        "pair such as IV is read as six rather than four, and that an unrecognised letter raises "
        "a lookup error instead of a bad-argument error."
    ),
    expected=(
        "roman_value(numeral) returns the value of the numeral, reads a smaller letter before a "
        "larger one as a subtraction, and raises ValueError for an unrecognised letter."
    ),
    baseline_reason="every letter is added, and the lookup table is indexed without checking",
    edge_cases=(
        "a smaller letter before a larger one subtracts",
        "an unrecognised letter is reported as a bad argument",
    ),
    baseline="""def roman_value(numeral):
    \"\"\"Return the value of the Roman numeral `numeral`.\"\"\"
    letters = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for letter in numeral:
        total += letters[letter]
    return total""",
    variant_one="""def roman_value(numeral):
    \"\"\"Return the value of the Roman numeral `numeral`.\"\"\"
    letters = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for place, letter in enumerate(numeral):
        if letter not in letters:
            raise ValueError(f"{letter!r} is not a Roman letter")
        value = letters[letter]
        following = numeral[place + 1 :]
        if following and letters.get(following[0], 0) > value:
            total -= value
        else:
            total += value
    return total""",
    variant_two="""def roman_value(numeral):
    \"\"\"Return the value of the Roman numeral `numeral`.\"\"\"
    letters = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    values = []
    for letter in numeral:
        if letter not in letters:
            raise ValueError(f"{letter!r} is not a Roman letter")
        values.append(letters[letter])
    total = 0
    for place, value in enumerate(values):
        after = values[place + 1 :]
        total += -value if after and after[0] > value else value
    return total""",
    variant_three="""def roman_value(numeral):
    \"\"\"Return the value of the Roman numeral `numeral`.\"\"\"
    letters = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for place, letter in enumerate(numeral):
        value = letters[letter]
        following = numeral[place + 1 :]
        if following and letters.get(following[0], 0) > value:
            total -= value
        else:
            total += value
    return total""",
    variant_four="""def roman_value(numeral):
    \"\"\"Return the value of the Roman numeral `numeral`.\"\"\"
    letters = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    for letter in numeral:
        if letter not in letters:
            raise ValueError(f"{letter!r} is not a Roman letter")
        total += letters[letter]
    return total""",
    visible_test=_test_module(
        "roman_value",
        "Published contract for reading a Roman numeral.",
        """
def test_three_ones() -> None:
    assert roman_value("III") == 3


def test_a_five_followed_by_a_one() -> None:
    assert roman_value("VI") == 6
""",
        imports="from roman_value import roman_value\n",
    ),
    hidden_test=_test_module(
        "roman_value",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_three_ones() -> None:
    assert roman_value("III") == 3


def test_a_smaller_letter_before_a_larger_one_subtracts() -> None:
    assert roman_value("IV") == 4


def test_an_unrecognised_letter_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        roman_value("Q")
""",
        imports="from roman_value import roman_value\n",
    ),
)

_G040 = D2TaskSpec(
    template_id="d4_numeric.normalised_position",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-normalised-position",
    module="normalised_position",
    module_doc="Placing a reading on a nought-to-one scale.",
    issue=(
        "normalised_position() is documented to place a reading between two bounds on a scale "
        "from nought to one. Callers report that a reading outside the bounds lands outside the "
        "scale, and that equal bounds raise an arithmetic error."
    ),
    expected=(
        "normalised_position(reading, low, high) returns where the reading sits between the "
        "bounds, clamped to the nought-to-one scale, and raises ValueError when the bounds are "
        "equal."
    ),
    baseline_reason="the span is divided into without clamping the result or checking the span",
    edge_cases=(
        "a reading outside the bounds is clamped to the scale",
        "equal bounds are reported as a bad argument",
    ),
    baseline="""def normalised_position(reading, low, high):
    \"\"\"Return where `reading` sits between `low` and `high`, from nought to one.\"\"\"
    return (reading - low) / (high - low)""",
    variant_one="""def normalised_position(reading, low, high):
    \"\"\"Return where `reading` sits between `low` and `high`, from nought to one.\"\"\"
    if high == low:
        raise ValueError("the bounds cannot be equal")
    placed = (reading - low) / (high - low)
    return max(0.0, min(1.0, placed))""",
    variant_two="""def normalised_position(reading, low, high):
    \"\"\"Return where `reading` sits between `low` and `high`, from nought to one.\"\"\"
    span = high - low
    if span == 0:
        raise ValueError("the bounds cannot be equal")
    if reading <= low:
        return 0.0
    if reading >= high:
        return 1.0
    return (reading - low) / span""",
    variant_three="""def normalised_position(reading, low, high):
    \"\"\"Return where `reading` sits between `low` and `high`, from nought to one.\"\"\"
    placed = (reading - low) / (high - low)
    return max(0.0, min(1.0, placed))""",
    variant_four="""def normalised_position(reading, low, high):
    \"\"\"Return where `reading` sits between `low` and `high`, from nought to one.\"\"\"
    if high == low:
        raise ValueError("the bounds cannot be equal")
    return (reading - low) / (high - low)""",
    visible_test=_test_module(
        "normalised_position",
        "Published contract for placing a reading on a scale.",
        """
def test_a_reading_in_the_middle() -> None:
    assert normalised_position(5, 0, 10) == 0.5


def test_a_reading_at_the_lower_bound() -> None:
    assert normalised_position(0, 0, 10) == 0.0
""",
        imports="from normalised_position import normalised_position\n",
    ),
    hidden_test=_test_module(
        "normalised_position",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_reading_in_the_middle() -> None:
    assert normalised_position(5, 0, 10) == 0.5


def test_a_reading_outside_the_bounds_is_clamped() -> None:
    assert normalised_position(15, 0, 10) == 1.0


def test_equal_bounds_are_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        normalised_position(5, 4, 4)
""",
        imports="from normalised_position import normalised_position\n",
    ),
)

# ------------------------------------------------------------------------------ error handling

_G041 = D2TaskSpec(
    template_id="d4_errors.first_error_message",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-first-error-message",
    module="first_error",
    module_doc="Finding the first error reported by a run.",
    issue=(
        "first_error_message() is documented to return the first error a run reported, or "
        "nothing when it reported none. Callers report that a run with no results at all comes "
        "back with an empty string instead of nothing, and that a result carrying no error field "
        "raises a lookup error."
    ),
    expected=(
        "first_error_message(results) returns the first non-empty error message, returns None "
        "when there is none, and treats a result without an error field as carrying no error."
    ),
    baseline_reason=(
        "the error field is indexed directly and the empty case falls through to a string"
    ),
    edge_cases=(
        "no results at all reports nothing",
        "a result without an error field carries no error",
    ),
    baseline="""def first_error_message(results):
    \"\"\"Return the first error message among `results`, or nothing.\"\"\"
    for result in results:
        if result["error"]:
            return result["error"]
    return \"\"""",
    variant_one="""def first_error_message(results):
    \"\"\"Return the first error message among `results`, or nothing.\"\"\"
    for result in results:
        message = result.get("error")
        if message:
            return message
    return None""",
    variant_two="""def first_error_message(results):
    \"\"\"Return the first error message among `results`, or nothing.\"\"\"
    reported = [result.get("error") for result in results]
    for message in reported:
        if message:
            return message
    return None""",
    variant_three="""def first_error_message(results):
    \"\"\"Return the first error message among `results`, or nothing.\"\"\"
    for result in results:
        if result["error"]:
            return result["error"]
    return None""",
    variant_four="""def first_error_message(results):
    \"\"\"Return the first error message among `results`, or nothing.\"\"\"
    for result in results:
        message = result.get("error")
        if message:
            return message
    return \"\"""",
    visible_test=_test_module(
        "first_error",
        "Published contract for finding the first error.",
        """
def test_the_first_reported_error_is_returned() -> None:
    assert first_error_message([{"error": ""}, {"error": "boom"}]) == "boom"


def test_the_earliest_of_two_errors_wins() -> None:
    assert first_error_message([{"error": "first"}, {"error": "second"}]) == "first"
""",
        imports="from first_error import first_error_message\n",
    ),
    hidden_test=_test_module(
        "first_error",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_reported_error_is_returned() -> None:
    assert first_error_message([{"error": ""}, {"error": "boom"}]) == "boom"


def test_no_results_at_all_reports_nothing() -> None:
    assert first_error_message([]) is None


def test_a_result_without_an_error_field_carries_no_error() -> None:
    assert first_error_message([{"ok": True}]) is None
""",
        imports="from first_error import first_error_message\n",
    ),
)

_G042 = D2TaskSpec(
    template_id="d4_errors.retry_delays",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-retry-delays",
    module="retry_delays",
    module_doc="Working out how long to wait between retries.",
    issue=(
        "retry_delays() is documented to return one doubling delay per attempt, never longer "
        "than a ceiling. Callers report that asking for no attempts still returns one delay, and "
        "that the delays keep doubling past the ceiling."
    ),
    expected=(
        "retry_delays(attempts, first, ceiling) returns one delay per attempt, each double the "
        "one before but never above the ceiling, and returns nothing for zero attempts."
    ),
    baseline_reason="an empty schedule is replaced with a single delay and the ceiling is ignored",
    edge_cases=(
        "zero attempts wait for nothing",
        "the delays stop doubling at the ceiling",
    ),
    baseline="""def retry_delays(attempts, first, ceiling):
    \"\"\"Return the delay before each of `attempts` retries.\"\"\"
    delays = []
    delay = first
    for _ in range(attempts):
        delays.append(delay)
        delay *= 2
    return delays or [first]""",
    variant_one="""def retry_delays(attempts, first, ceiling):
    \"\"\"Return the delay before each of `attempts` retries.\"\"\"
    delays = []
    delay = first
    for _ in range(attempts):
        delays.append(min(delay, ceiling))
        delay *= 2
    return delays""",
    variant_two="""def retry_delays(attempts, first, ceiling):
    \"\"\"Return the delay before each of `attempts` retries.\"\"\"
    schedule = []
    for step in range(attempts):
        wanted = first * (2**step)
        schedule.append(ceiling if wanted > ceiling else wanted)
    return schedule""",
    variant_three="""def retry_delays(attempts, first, ceiling):
    \"\"\"Return the delay before each of `attempts` retries.\"\"\"
    delays = []
    delay = first
    for _ in range(attempts):
        delays.append(delay)
        delay *= 2
    return delays""",
    variant_four="""def retry_delays(attempts, first, ceiling):
    \"\"\"Return the delay before each of `attempts` retries.\"\"\"
    delays = []
    delay = first
    for _ in range(attempts):
        delays.append(min(delay, ceiling))
        delay *= 2
    return delays or [first]""",
    visible_test=_test_module(
        "retry_delays",
        "Published contract for a retry schedule.",
        """
def test_three_doubling_delays() -> None:
    assert retry_delays(3, 1, 100) == [1, 2, 4]


def test_two_delays_from_a_larger_start() -> None:
    assert retry_delays(2, 5, 100) == [5, 10]
""",
        imports="from retry_delays import retry_delays\n",
    ),
    hidden_test=_test_module(
        "retry_delays",
        "The part of the contract the published tests do not state.",
        """
def test_three_doubling_delays() -> None:
    assert retry_delays(3, 1, 100) == [1, 2, 4]


def test_zero_attempts_wait_for_nothing() -> None:
    assert retry_delays(0, 1, 100) == []


def test_the_delays_stop_doubling_at_the_ceiling() -> None:
    assert retry_delays(4, 10, 25) == [10, 20, 25, 25]
""",
        imports="from retry_delays import retry_delays\n",
    ),
)

_G043 = D2TaskSpec(
    template_id="d4_errors.root_cause",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-root-cause",
    module="cause_chain",
    module_doc="Following a chain of causes to its root.",
    issue=(
        "root_cause() is documented to follow an error's causes to the root and report its "
        "message. Callers report that an error recorded without a cause field raises a lookup "
        "error, and that a chain that never ends walks for ever instead of being reported."
    ),
    expected=(
        "root_cause(error) returns the message of the deepest cause, treats a missing cause "
        "field as no cause, and raises ValueError once the chain passes ten links."
    ),
    baseline_reason="the cause field is indexed directly and the walk has no depth limit",
    edge_cases=(
        "an error without a cause field reports its own message",
        "a chain longer than ten links is refused",
    ),
    baseline="""def root_cause(error):
    \"\"\"Return the message of the deepest cause of `error`.\"\"\"
    current = error
    while current["cause"]:
        current = current["cause"]
    return current["message"]""",
    variant_one="""def root_cause(error):
    \"\"\"Return the message of the deepest cause of `error`.\"\"\"
    current = error
    depth = 0
    while current.get("cause"):
        depth += 1
        if depth > 10:
            raise ValueError("the cause chain is too long to follow")
        current = current["cause"]
    return current["message"]""",
    variant_two="""def root_cause(error):
    \"\"\"Return the message of the deepest cause of `error`.\"\"\"
    current = error
    for _ in range(11):
        deeper = current.get("cause")
        if not deeper:
            return current["message"]
        current = deeper
    raise ValueError("the cause chain is too long to follow")""",
    variant_three="""def root_cause(error):
    \"\"\"Return the message of the deepest cause of `error`.\"\"\"
    current = error
    while current.get("cause"):
        current = current["cause"]
    return current["message"]""",
    variant_four="""def root_cause(error):
    \"\"\"Return the message of the deepest cause of `error`.\"\"\"
    current = error
    depth = 0
    while current["cause"]:
        depth += 1
        if depth > 10:
            raise ValueError("the cause chain is too long to follow")
        current = current["cause"]
    return current["message"]""",
    visible_test=_test_module(
        "cause_chain",
        "Published contract for following a cause chain.",
        """
def test_a_chain_of_two() -> None:
    error = {"message": "outer", "cause": {"message": "inner", "cause": None}}
    assert root_cause(error) == "inner"


def test_a_chain_of_three() -> None:
    deepest = {"message": "root", "cause": None}
    error = {"message": "outer", "cause": {"message": "middle", "cause": deepest}}
    assert root_cause(error) == "root"
""",
        imports="from cause_chain import root_cause\n",
    ),
    hidden_test=_test_module(
        "cause_chain",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_chain_of_two() -> None:
    error = {"message": "outer", "cause": {"message": "inner", "cause": None}}
    assert root_cause(error) == "inner"


def test_an_error_without_a_cause_field_reports_its_own_message() -> None:
    assert root_cause({"message": "solo"}) == "solo"


def test_a_chain_longer_than_ten_links_is_refused() -> None:
    error = {"message": "deepest", "cause": None}
    for step in range(12):
        error = {"message": f"link{step}", "cause": error}
    with pytest.raises(ValueError):
        root_cause(error)
""",
        imports="from cause_chain import root_cause\n",
    ),
)

_G044 = D2TaskSpec(
    template_id="d4_errors.group_by_prefix",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-group-by-prefix",
    module="error_tally",
    module_doc="Tallying error messages by the subsystem that raised them.",
    issue=(
        "tally_by_subsystem() is documented to count messages by the subsystem named before the "
        "colon. Callers report that a message with no colon is counted under its whole text "
        "instead of under 'unknown', and that spacing around the subsystem name splits one "
        "subsystem into two."
    ),
    expected=(
        "tally_by_subsystem(messages) counts messages by the name before the first colon, "
        "trimmed of spacing, and counts a message with no colon under 'unknown'."
    ),
    baseline_reason="the text before the colon is taken as it stands, colon or no colon",
    edge_cases=(
        "a message with no colon counts as unknown",
        "spacing around the subsystem name is trimmed",
    ),
    baseline="""def tally_by_subsystem(messages):
    \"\"\"Return how many messages each subsystem raised.\"\"\"
    tally = {}
    for message in messages:
        name = message.split(":")[0]
        tally[name] = tally.get(name, 0) + 1
    return tally""",
    variant_one="""def tally_by_subsystem(messages):
    \"\"\"Return how many messages each subsystem raised.\"\"\"
    tally = {}
    for message in messages:
        name = message.split(":")[0].strip() if ":" in message else "unknown"
        tally[name] = tally.get(name, 0) + 1
    return tally""",
    variant_two="""def tally_by_subsystem(messages):
    \"\"\"Return how many messages each subsystem raised.\"\"\"
    tally = {}
    for message in messages:
        head, marker, _ = message.partition(":")
        name = head.strip() if marker else "unknown"
        if name not in tally:
            tally[name] = 0
        tally[name] += 1
    return tally""",
    variant_three="""def tally_by_subsystem(messages):
    \"\"\"Return how many messages each subsystem raised.\"\"\"
    tally = {}
    for message in messages:
        name = message.split(":")[0] if ":" in message else "unknown"
        tally[name] = tally.get(name, 0) + 1
    return tally""",
    variant_four="""def tally_by_subsystem(messages):
    \"\"\"Return how many messages each subsystem raised.\"\"\"
    tally = {}
    for message in messages:
        name = message.split(":")[0].strip()
        tally[name] = tally.get(name, 0) + 1
    return tally""",
    visible_test=_test_module(
        "error_tally",
        "Published contract for tallying by subsystem.",
        """
def test_two_messages_from_one_subsystem() -> None:
    assert tally_by_subsystem(["db: down", "db: slow"]) == {"db": 2}


def test_one_message_from_another_subsystem() -> None:
    assert tally_by_subsystem(["net: lost"]) == {"net": 1}
""",
        imports="from error_tally import tally_by_subsystem\n",
    ),
    hidden_test=_test_module(
        "error_tally",
        "The part of the contract the published tests do not state.",
        """
def test_two_messages_from_one_subsystem() -> None:
    assert tally_by_subsystem(["db: down", "db: slow"]) == {"db": 2}


def test_a_message_with_no_colon_counts_as_unknown() -> None:
    assert tally_by_subsystem(["boom"]) == {"unknown": 1}


def test_spacing_around_the_subsystem_name_is_trimmed() -> None:
    assert tally_by_subsystem([" db : down"]) == {"db": 1}
""",
        imports="from error_tally import tally_by_subsystem\n",
    ),
)

_G045 = D2TaskSpec(
    template_id="d4_errors.lookup_path",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-lookup-path",
    module="nested_lookup",
    module_doc="Looking a value up by a dotted path.",
    issue=(
        "lookup_path() is documented to follow a dotted path and fall back to a default. Callers "
        "report that a path continuing through a value that is not a mapping raises a type error "
        "instead of falling back, and that an empty path raises instead of returning the whole "
        "mapping."
    ),
    expected=(
        "lookup_path(mapping, path, default) returns the value at the dotted path, returns the "
        "whole mapping for an empty path, and returns the default when the path cannot be "
        "followed."
    ),
    baseline_reason=(
        "each step indexes whatever it reached, and the empty path becomes one blank step"
    ),
    edge_cases=(
        "a path through a value that is not a mapping falls back",
        "an empty path returns the whole mapping",
    ),
    baseline="""def lookup_path(mapping, path, default=None):
    \"\"\"Return the value `path` names inside `mapping`, or `default`.\"\"\"
    current = mapping
    for step in path.split("."):
        if step not in current:
            return default
        current = current[step]
    return current""",
    variant_one="""def lookup_path(mapping, path, default=None):
    \"\"\"Return the value `path` names inside `mapping`, or `default`.\"\"\"
    if not path:
        return mapping
    current = mapping
    for step in path.split("."):
        if not isinstance(current, dict) or step not in current:
            return default
        current = current[step]
    return current""",
    variant_two="""def lookup_path(mapping, path, default=None):
    \"\"\"Return the value `path` names inside `mapping`, or `default`.\"\"\"
    steps = [step for step in path.split(".") if step]
    current = mapping
    for step in steps:
        try:
            current = current[step]
        except (KeyError, TypeError):
            return default
    return current""",
    variant_three="""def lookup_path(mapping, path, default=None):
    \"\"\"Return the value `path` names inside `mapping`, or `default`.\"\"\"
    current = mapping
    for step in path.split("."):
        if not isinstance(current, dict) or step not in current:
            return default
        current = current[step]
    return current""",
    variant_four="""def lookup_path(mapping, path, default=None):
    \"\"\"Return the value `path` names inside `mapping`, or `default`.\"\"\"
    if not path:
        return mapping
    current = mapping
    for step in path.split("."):
        if step not in current:
            return default
        current = current[step]
    return current""",
    visible_test=_test_module(
        "nested_lookup",
        "Published contract for a dotted-path lookup.",
        """
def test_a_two_step_path() -> None:
    assert lookup_path({"a": {"b": 1}}, "a.b") == 1


def test_a_missing_step_falls_back() -> None:
    assert lookup_path({"a": {"b": 1}}, "a.z", "none") == "none"
""",
        imports="from nested_lookup import lookup_path\n",
    ),
    hidden_test=_test_module(
        "nested_lookup",
        "The part of the contract the published tests do not state.",
        """
def test_a_two_step_path() -> None:
    assert lookup_path({"a": {"b": 1}}, "a.b") == 1


def test_a_path_through_a_plain_value_falls_back() -> None:
    assert lookup_path({"a": 1}, "a.b", "none") == "none"


def test_an_empty_path_returns_the_whole_mapping() -> None:
    assert lookup_path({"a": 1}, "") == {"a": 1}
""",
        imports="from nested_lookup import lookup_path\n",
    ),
)

_G046 = D2TaskSpec(
    template_id="d4_errors.escalate_severity",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-escalate-severity",
    module="severity_ladder",
    module_doc="Raising an alert up the severity ladder.",
    issue=(
        "escalate() is documented to raise a severity by a number of steps. Callers report that "
        "escalating past the top of the ladder raises an index error instead of staying at the "
        "top, and that an unrecognised severity raises a lookup error rather than a "
        "bad-argument error."
    ),
    expected=(
        "escalate(level, steps) returns the severity that many steps higher, stops at the top of "
        "the ladder, and raises ValueError for an unrecognised severity."
    ),
    baseline_reason="the ladder is indexed past its end and the severity is looked up unchecked",
    edge_cases=(
        "escalating past the top stays at the top",
        "an unrecognised severity is reported as a bad argument",
    ),
    baseline="""def escalate(level, steps):
    \"\"\"Return the severity `steps` above `level`.\"\"\"
    ladder = ["low", "medium", "high", "critical"]
    places = {name: place for place, name in enumerate(ladder)}
    return ladder[places[level] + steps]""",
    variant_one="""def escalate(level, steps):
    \"\"\"Return the severity `steps` above `level`.\"\"\"
    ladder = ["low", "medium", "high", "critical"]
    if level not in ladder:
        raise ValueError(f"{level!r} is not a severity")
    place = ladder.index(level) + steps
    return ladder[min(place, len(ladder) - 1)]""",
    variant_two="""def escalate(level, steps):
    \"\"\"Return the severity `steps` above `level`.\"\"\"
    ladder = ["low", "medium", "high", "critical"]
    places = {name: place for place, name in enumerate(ladder)}
    if level not in places:
        raise ValueError(f"{level!r} is not a severity")
    wanted = places[level] + steps
    top = len(ladder) - 1
    return ladder[top if wanted > top else wanted]""",
    variant_three="""def escalate(level, steps):
    \"\"\"Return the severity `steps` above `level`.\"\"\"
    ladder = ["low", "medium", "high", "critical"]
    places = {name: place for place, name in enumerate(ladder)}
    wanted = places[level] + steps
    return ladder[min(wanted, len(ladder) - 1)]""",
    variant_four="""def escalate(level, steps):
    \"\"\"Return the severity `steps` above `level`.\"\"\"
    ladder = ["low", "medium", "high", "critical"]
    if level not in ladder:
        raise ValueError(f"{level!r} is not a severity")
    return ladder[ladder.index(level) + steps]""",
    visible_test=_test_module(
        "severity_ladder",
        "Published contract for escalating a severity.",
        """
def test_one_step_up_from_the_bottom() -> None:
    assert escalate("low", 1) == "medium"


def test_one_step_up_from_the_middle() -> None:
    assert escalate("medium", 1) == "high"
""",
        imports="from severity_ladder import escalate\n",
    ),
    hidden_test=_test_module(
        "severity_ladder",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_step_up_from_the_bottom() -> None:
    assert escalate("low", 1) == "medium"


def test_escalating_past_the_top_stays_at_the_top() -> None:
    assert escalate("high", 2) == "critical"


def test_an_unrecognised_severity_is_a_bad_argument() -> None:
    with pytest.raises(ValueError):
        escalate("bogus", 1)
""",
        imports="from severity_ladder import escalate\n",
    ),
)

_G047 = D2TaskSpec(
    template_id="d4_errors.shorten_message",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-shorten-message",
    module="message_shorten",
    module_doc="Shortening a long message for a one-line log.",
    issue=(
        "shorten() is documented to shorten a message to a length, marking the cut with an "
        "ellipsis. Callers report that a message already short enough gains an ellipsis it does "
        "not need, and that a length too small to hold the ellipsis produces nonsense instead of "
        "being refused."
    ),
    expected=(
        "shorten(message, length) returns the message unchanged when it already fits, otherwise "
        "cuts it so the result including the ellipsis is exactly that long, and raises "
        "ValueError for a length below four."
    ),
    baseline_reason="the cut and the ellipsis are applied whatever the message and the length are",
    edge_cases=(
        "a message that already fits is unchanged",
        "a length too small for the ellipsis is refused",
    ),
    baseline="""def shorten(message, length):
    \"\"\"Return `message` shortened to `length` characters.\"\"\"
    return message[: length - 3] + "..." """,
    variant_one="""def shorten(message, length):
    \"\"\"Return `message` shortened to `length` characters.\"\"\"
    if length < 4:
        raise ValueError("a shortened message needs room for the ellipsis")
    if len(message) <= length:
        return message
    return message[: length - 3] + "..." """,
    variant_two="""def shorten(message, length):
    \"\"\"Return `message` shortened to `length` characters.\"\"\"
    if not length >= 4:
        raise ValueError("a shortened message needs room for the ellipsis")
    return message if len(message) <= length else message[: length - 3] + "..." """,
    variant_three="""def shorten(message, length):
    \"\"\"Return `message` shortened to `length` characters.\"\"\"
    if len(message) <= length:
        return message
    return message[: length - 3] + "..." """,
    variant_four="""def shorten(message, length):
    \"\"\"Return `message` shortened to `length` characters.\"\"\"
    if length < 4:
        raise ValueError("a shortened message needs room for the ellipsis")
    return message[: length - 3] + "..." """,
    visible_test=_test_module(
        "message_shorten",
        "Published contract for shortening a message.",
        """
def test_a_long_message_is_cut() -> None:
    assert shorten("abcdefgh", 5) == "ab..."


def test_a_longer_allowance_keeps_more() -> None:
    assert shorten("hello world", 8) == "hello..."
""",
        imports="from message_shorten import shorten\n",
    ),
    hidden_test=_test_module(
        "message_shorten",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_long_message_is_cut() -> None:
    assert shorten("abcdefgh", 5) == "ab..."


def test_a_message_that_already_fits_is_unchanged() -> None:
    assert shorten("abc", 10) == "abc"


def test_a_length_too_small_for_the_ellipsis_is_refused() -> None:
    with pytest.raises(ValueError):
        shorten("abcdefgh", 2)
""",
        imports="from message_shorten import shorten\n",
    ),
)

_G048 = D2TaskSpec(
    template_id="d4_errors.status_band",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-status-band",
    module="status_band",
    module_doc="Naming the band a status code falls in.",
    issue=(
        "status_band() is documented to name the band a status code falls in. Callers report "
        "that a code above the highest band is named as a server fault instead of being "
        "refused, and that a negative code is named as informational."
    ),
    expected=(
        "status_band(code) names the band for a code between 100 and 599, and raises ValueError "
        "for any code outside that range."
    ),
    baseline_reason="the ladder of comparisons has no floor and no ceiling",
    edge_cases=(
        "a code above the highest band is refused",
        "a code below the lowest band is refused",
    ),
    baseline="""def status_band(code):
    \"\"\"Return the name of the band `code` falls in.\"\"\"
    if code < 200:
        return "informational"
    if code < 300:
        return "successful"
    if code < 400:
        return "redirect"
    if code < 500:
        return "client fault"
    return "server fault\"""",
    variant_one="""def status_band(code):
    \"\"\"Return the name of the band `code` falls in.\"\"\"
    if code < 100 or code > 599:
        raise ValueError(f"{code} is not a status code")
    if code < 200:
        return "informational"
    if code < 300:
        return "successful"
    if code < 400:
        return "redirect"
    if code < 500:
        return "client fault"
    return "server fault\"""",
    variant_two="""def status_band(code):
    \"\"\"Return the name of the band `code` falls in.\"\"\"
    bands = (
        (200, "informational"),
        (300, "successful"),
        (400, "redirect"),
        (500, "client fault"),
        (600, "server fault"),
    )
    if not 100 <= code <= 599:
        raise ValueError(f"{code} is not a status code")
    for boundary, name in bands:
        if code < boundary:
            return name
    raise ValueError(f"{code} is not a status code")""",
    variant_three="""def status_band(code):
    \"\"\"Return the name of the band `code` falls in.\"\"\"
    if code > 599:
        raise ValueError(f"{code} is not a status code")
    if code < 200:
        return "informational"
    if code < 300:
        return "successful"
    if code < 400:
        return "redirect"
    if code < 500:
        return "client fault"
    return "server fault\"""",
    variant_four="""def status_band(code):
    \"\"\"Return the name of the band `code` falls in.\"\"\"
    if code < 100:
        raise ValueError(f"{code} is not a status code")
    if code < 200:
        return "informational"
    if code < 300:
        return "successful"
    if code < 400:
        return "redirect"
    if code < 500:
        return "client fault"
    return "server fault\"""",
    visible_test=_test_module(
        "status_band",
        "Published contract for naming a status band.",
        """
def test_a_successful_code() -> None:
    assert status_band(200) == "successful"


def test_a_client_fault_code() -> None:
    assert status_band(404) == "client fault"
""",
        imports="from status_band import status_band\n",
    ),
    hidden_test=_test_module(
        "status_band",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_successful_code() -> None:
    assert status_band(200) == "successful"


def test_a_code_above_the_highest_band_is_refused() -> None:
    with pytest.raises(ValueError):
        status_band(900)


def test_a_code_below_the_lowest_band_is_refused() -> None:
    with pytest.raises(ValueError):
        status_band(-1)
""",
        imports="from status_band import status_band\n",
    ),
)

_G049 = D2TaskSpec(
    template_id="d4_errors.retry_after",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-retry-after",
    module="retry_after",
    module_doc="Reading how long a service asked us to wait.",
    issue=(
        "retry_after_seconds() is documented to read the wait a service asked for. Callers "
        "report that the header is missed when the service spells its name with capitals, and "
        "that a response carrying no such header raises a lookup error instead of reporting no "
        "wait."
    ),
    expected=(
        "retry_after_seconds(headers) returns the requested wait in seconds, matches the header "
        "name regardless of case, and returns None when the header is absent."
    ),
    baseline_reason="the header is indexed by one exact spelling",
    edge_cases=(
        "the header name is matched regardless of case",
        "an absent header reports no wait",
    ),
    baseline="""def retry_after_seconds(headers):
    \"\"\"Return the wait in seconds the service asked for, or nothing.\"\"\"
    return int(headers["retry-after"])""",
    variant_one="""def retry_after_seconds(headers):
    \"\"\"Return the wait in seconds the service asked for, or nothing.\"\"\"
    for name, value in headers.items():
        if name.lower() == "retry-after":
            return int(value)
    return None""",
    variant_two="""def retry_after_seconds(headers):
    \"\"\"Return the wait in seconds the service asked for, or nothing.\"\"\"
    folded = {name.lower(): value for name, value in headers.items()}
    if "retry-after" not in folded:
        return None
    return int(folded["retry-after"])""",
    variant_three="""def retry_after_seconds(headers):
    \"\"\"Return the wait in seconds the service asked for, or nothing.\"\"\"
    for name, value in headers.items():
        if name.lower() == "retry-after":
            return int(value)
    raise KeyError("retry-after")""",
    variant_four="""def retry_after_seconds(headers):
    \"\"\"Return the wait in seconds the service asked for, or nothing.\"\"\"
    if "retry-after" not in headers:
        return None
    return int(headers["retry-after"])""",
    visible_test=_test_module(
        "retry_after",
        "Published contract for reading a requested wait.",
        """
def test_a_wait_of_thirty_seconds() -> None:
    assert retry_after_seconds({"retry-after": "30"}) == 30


def test_a_wait_of_no_seconds() -> None:
    assert retry_after_seconds({"retry-after": "0"}) == 0
""",
        imports="from retry_after import retry_after_seconds\n",
    ),
    hidden_test=_test_module(
        "retry_after",
        "The part of the contract the published tests do not state.",
        """
def test_a_wait_of_thirty_seconds() -> None:
    assert retry_after_seconds({"retry-after": "30"}) == 30


def test_the_header_name_is_matched_regardless_of_case() -> None:
    assert retry_after_seconds({"Retry-After": "30"}) == 30


def test_an_absent_header_reports_no_wait() -> None:
    assert retry_after_seconds({}) is None
""",
        imports="from retry_after import retry_after_seconds\n",
    ),
)

_G050 = D2TaskSpec(
    template_id="d4_errors.abort_reason",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-abort-reason",
    module="abort_reason",
    module_doc="Naming why a run stopped early.",
    issue=(
        "abort_reason() is documented to name why a run stopped, taking the most deliberate "
        "reason when several hold at once. Callers report that a run both cancelled and failed "
        "is reported as failed, and that a run that stopped for none of these reasons is "
        "reported as an empty string instead of nothing."
    ),
    expected=(
        "abort_reason(state) names the reason with the highest precedence -- cancelled, then "
        "failed, then timed out -- and returns None when none of them holds."
    ),
    baseline_reason=(
        "the reasons are checked in the order they were added, and no reason means a blank"
    ),
    edge_cases=(
        "a cancelled run outranks a failed one",
        "no reason at all reports nothing",
    ),
    baseline="""def abort_reason(state):
    \"\"\"Return the most deliberate reason `state` stopped, or nothing.\"\"\"
    for name in ("timed_out", "failed", "cancelled"):
        if state.get(name):
            return name
    return \"\"""",
    variant_one="""def abort_reason(state):
    \"\"\"Return the most deliberate reason `state` stopped, or nothing.\"\"\"
    for name in ("cancelled", "failed", "timed_out"):
        if state.get(name):
            return name
    return None""",
    variant_two="""def abort_reason(state):
    \"\"\"Return the most deliberate reason `state` stopped, or nothing.\"\"\"
    precedence = ("cancelled", "failed", "timed_out")
    holding = [name for name in precedence if state.get(name)]
    return holding[0] if holding else None""",
    variant_three="""def abort_reason(state):
    \"\"\"Return the most deliberate reason `state` stopped, or nothing.\"\"\"
    for name in ("cancelled", "failed", "timed_out"):
        if state.get(name):
            return name
    return \"\"""",
    variant_four="""def abort_reason(state):
    \"\"\"Return the most deliberate reason `state` stopped, or nothing.\"\"\"
    for name in ("timed_out", "failed", "cancelled"):
        if state.get(name):
            return name
    return None""",
    visible_test=_test_module(
        "abort_reason",
        "Published contract for naming an abort reason.",
        """
def test_a_failed_run() -> None:
    assert abort_reason({"failed": True}) == "failed"


def test_a_run_that_timed_out() -> None:
    assert abort_reason({"timed_out": True}) == "timed_out"
""",
        imports="from abort_reason import abort_reason\n",
    ),
    hidden_test=_test_module(
        "abort_reason",
        "The part of the contract the published tests do not state.",
        """
def test_a_failed_run() -> None:
    assert abort_reason({"failed": True}) == "failed"


def test_a_cancelled_run_outranks_a_failed_one() -> None:
    assert abort_reason({"failed": True, "cancelled": True}) == "cancelled"


def test_no_reason_at_all_reports_nothing() -> None:
    assert abort_reason({}) is None
""",
        imports="from abort_reason import abort_reason\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G051 = D2TaskSpec(
    template_id="d4_transform.rename_fields",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-rename-fields",
    module="field_rename",
    module_doc="Renaming the fields of a record.",
    issue=(
        "rename_fields() is documented to rename the fields a record carries. Callers report "
        "that asking to rename a field the record does not have raises a lookup error, and that "
        "renaming a field onto a name already in use silently discards one of them."
    ),
    expected=(
        "rename_fields(record, renames) returns the record with the named fields renamed, "
        "ignores a rename for a field that is absent, and raises ValueError when a rename would "
        "collide with a field already present."
    ),
    baseline_reason="each rename is read straight out of the record and written without checking",
    edge_cases=(
        "renaming an absent field is ignored",
        "a rename colliding with an existing field is refused",
    ),
    baseline="""def rename_fields(record, renames):
    \"\"\"Return `record` with its fields renamed according to `renames`.\"\"\"
    renamed = {}
    for old, new in renames.items():
        renamed[new] = record[old]
    for name, value in record.items():
        if name not in renames:
            renamed[name] = value
    return renamed""",
    variant_one="""def rename_fields(record, renames):
    \"\"\"Return `record` with its fields renamed according to `renames`.\"\"\"
    renamed = {}
    for old, new in renames.items():
        if old not in record:
            continue
        if new in record and new not in renames:
            raise ValueError(f"{new!r} is already a field")
        renamed[new] = record[old]
    for name, value in record.items():
        if name not in renames:
            renamed[name] = value
    return renamed""",
    variant_two="""def rename_fields(record, renames):
    \"\"\"Return `record` with its fields renamed according to `renames`.\"\"\"
    renamed = {}
    for name, value in record.items():
        target = renames.get(name, name)
        if target != name and target in record and target not in renames:
            raise ValueError(f"{target!r} is already a field")
        renamed[target] = value
    return renamed""",
    variant_three="""def rename_fields(record, renames):
    \"\"\"Return `record` with its fields renamed according to `renames`.\"\"\"
    renamed = {}
    for old, new in renames.items():
        if old not in record:
            continue
        renamed[new] = record[old]
    for name, value in record.items():
        if name not in renames:
            renamed[name] = value
    return renamed""",
    variant_four="""def rename_fields(record, renames):
    \"\"\"Return `record` with its fields renamed according to `renames`.\"\"\"
    renamed = {}
    for old, new in renames.items():
        if new in record and new not in renames:
            raise ValueError(f"{new!r} is already a field")
        renamed[new] = record[old]
    for name, value in record.items():
        if name not in renames:
            renamed[name] = value
    return renamed""",
    visible_test=_test_module(
        "field_rename",
        "Published contract for renaming fields.",
        """
def test_one_field_is_renamed() -> None:
    assert rename_fields({"a": 1, "b": 2}, {"a": "x"}) == {"x": 1, "b": 2}


def test_the_only_field_is_renamed() -> None:
    assert rename_fields({"a": 1}, {"a": "z"}) == {"z": 1}
""",
        imports="from field_rename import rename_fields\n",
    ),
    hidden_test=_test_module(
        "field_rename",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_field_is_renamed() -> None:
    assert rename_fields({"a": 1, "b": 2}, {"a": "x"}) == {"x": 1, "b": 2}


def test_renaming_an_absent_field_is_ignored() -> None:
    assert rename_fields({"b": 2}, {"a": "x"}) == {"b": 2}


def test_a_rename_colliding_with_an_existing_field_is_refused() -> None:
    with pytest.raises(ValueError):
        rename_fields({"a": 1, "b": 2}, {"a": "b"})
""",
        imports="from field_rename import rename_fields\n",
    ),
)

_G052 = D2TaskSpec(
    template_id="d4_transform.run_lengths",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-run-lengths",
    module="run_lengths",
    module_doc="Describing a sequence as runs of repeated values.",
    issue=(
        "run_lengths() is documented to describe a sequence as consecutive runs. Callers report "
        "that an empty sequence raises instead of describing nothing, and that a sequence made "
        "of a single run comes back empty."
    ),
    expected=(
        "run_lengths(values) returns one (value, length) pair per consecutive run, returns "
        "nothing for an empty sequence, and describes a sequence of one run as that one run."
    ),
    baseline_reason=(
        "the first value is read before the sequence is checked, and the final run is only "
        "emitted when an earlier run already was"
    ),
    edge_cases=(
        "an empty sequence describes nothing",
        "a sequence of one run describes that run",
    ),
    baseline="""def run_lengths(values):
    \"\"\"Return the consecutive runs of `values` as (value, length) pairs.\"\"\"
    runs = []
    current = values[0]
    count = 0
    for value in values:
        if value == current:
            count += 1
        else:
            runs.append((current, count))
            current, count = value, 1
    if runs:
        runs.append((current, count))
    return runs""",
    variant_one="""def run_lengths(values):
    \"\"\"Return the consecutive runs of `values` as (value, length) pairs.\"\"\"
    collected = list(values)
    if not collected:
        return []
    runs = []
    current = collected[0]
    count = 0
    for value in collected:
        if value == current:
            count += 1
        else:
            runs.append((current, count))
            current, count = value, 1
    runs.append((current, count))
    return runs""",
    variant_two="""def run_lengths(values):
    \"\"\"Return the consecutive runs of `values` as (value, length) pairs.\"\"\"
    runs = []
    for value in values:
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))
    return runs""",
    variant_three="""def run_lengths(values):
    \"\"\"Return the consecutive runs of `values` as (value, length) pairs.\"\"\"
    collected = list(values)
    if not collected:
        return []
    runs = []
    current = collected[0]
    count = 0
    for value in collected:
        if value == current:
            count += 1
        else:
            runs.append((current, count))
            current, count = value, 1
    if runs:
        runs.append((current, count))
    return runs""",
    variant_four="""def run_lengths(values):
    \"\"\"Return the consecutive runs of `values` as (value, length) pairs.\"\"\"
    runs = []
    current = values[0]
    count = 0
    for value in values:
        if value == current:
            count += 1
        else:
            runs.append((current, count))
            current, count = value, 1
    runs.append((current, count))
    return runs""",
    visible_test=_test_module(
        "run_lengths",
        "Published contract for describing runs.",
        """
def test_two_runs_of_different_lengths() -> None:
    assert run_lengths([1, 1, 2]) == [(1, 2), (2, 1)]


def test_two_runs_of_equal_length() -> None:
    assert run_lengths([5, 5, 6, 6]) == [(5, 2), (6, 2)]
""",
        imports="from run_lengths import run_lengths\n",
    ),
    hidden_test=_test_module(
        "run_lengths",
        "The part of the contract the published tests do not state.",
        """
def test_two_runs_of_different_lengths() -> None:
    assert run_lengths([1, 1, 2]) == [(1, 2), (2, 1)]


def test_an_empty_sequence_describes_nothing() -> None:
    assert run_lengths([]) == []


def test_a_sequence_of_one_run_describes_that_run() -> None:
    assert run_lengths([7, 7]) == [(7, 2)]
""",
        imports="from run_lengths import run_lengths\n",
    ),
)

_G053 = D2TaskSpec(
    template_id="d4_transform.invert_mapping",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-invert-mapping",
    module="mapping_invert",
    module_doc="Turning a mapping inside out.",
    issue=(
        "invert() is documented to turn a mapping inside out. Callers report that two names "
        "sharing a value silently lose one of them, and that a value that cannot be a key raises "
        "a type error instead of a bad-argument error."
    ),
    expected=(
        "invert(mapping) returns the mapping with names and values swapped, raises ValueError "
        "when two names share a value, and raises ValueError when a value cannot be a key."
    ),
    baseline_reason="the comprehension overwrites duplicates and lets the type error escape",
    edge_cases=(
        "two names sharing a value is refused",
        "a value that cannot be a key is refused",
    ),
    baseline="""def invert(mapping):
    \"\"\"Return `mapping` with its names and values swapped.\"\"\"
    return {value: name for name, value in mapping.items()}""",
    variant_one="""def invert(mapping):
    \"\"\"Return `mapping` with its names and values swapped.\"\"\"
    inverted = {}
    for name, value in mapping.items():
        try:
            already = value in inverted
        except TypeError as error:
            raise ValueError(f"{value!r} cannot be a name") from error
        if already:
            raise ValueError(f"{value!r} is shared by two names")
        inverted[value] = name
    return inverted""",
    variant_two="""def invert(mapping):
    \"\"\"Return `mapping` with its names and values swapped.\"\"\"
    inverted = {}
    for name, value in mapping.items():
        if not isinstance(value, (str, int, float, bool, bytes, tuple, type(None))):
            raise ValueError(f"{value!r} cannot be a name")
        if value in inverted:
            raise ValueError(f"{value!r} is shared by two names")
        inverted[value] = name
    return inverted""",
    variant_three="""def invert(mapping):
    \"\"\"Return `mapping` with its names and values swapped.\"\"\"
    inverted = {}
    for name, value in mapping.items():
        if value in inverted:
            raise ValueError(f"{value!r} is shared by two names")
        inverted[value] = name
    return inverted""",
    variant_four="""def invert(mapping):
    \"\"\"Return `mapping` with its names and values swapped.\"\"\"
    inverted = {}
    for name, value in mapping.items():
        if not isinstance(value, (str, int, float, bool, bytes, tuple, type(None))):
            raise ValueError(f"{value!r} cannot be a name")
        inverted[value] = name
    return inverted""",
    visible_test=_test_module(
        "mapping_invert",
        "Published contract for inverting a mapping.",
        """
def test_two_distinct_pairs_are_swapped() -> None:
    assert invert({"a": 1, "b": 2}) == {1: "a", 2: "b"}


def test_an_empty_mapping_inverts_to_nothing() -> None:
    assert invert({}) == {}
""",
        imports="from mapping_invert import invert\n",
    ),
    hidden_test=_test_module(
        "mapping_invert",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_distinct_pairs_are_swapped() -> None:
    assert invert({"a": 1, "b": 2}) == {1: "a", 2: "b"}


def test_two_names_sharing_a_value_is_refused() -> None:
    with pytest.raises(ValueError):
        invert({"a": 1, "b": 1})


def test_a_value_that_cannot_be_a_name_is_refused() -> None:
    with pytest.raises(ValueError):
        invert({"a": [1]})
""",
        imports="from mapping_invert import invert\n",
    ),
)

_G054 = D2TaskSpec(
    template_id="d4_transform.expand_ranges",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-expand-ranges",
    module="range_expand",
    module_doc="Expanding a written list of numbers and spans.",
    issue=(
        "expand_ranges() is documented to expand a written selection such as '1-3,5'. Callers "
        "report that a span written backwards silently expands to nothing, and that a stray "
        "comma crashes the expansion instead of being ignored."
    ),
    expected=(
        "expand_ranges(spec) returns the numbers the selection names, raises ValueError for a "
        "span whose end is below its start, and ignores an empty fragment."
    ),
    baseline_reason="the span is handed to range() unchecked and an empty fragment reaches int()",
    edge_cases=(
        "a backwards span is refused",
        "an empty fragment is ignored",
    ),
    baseline="""def expand_ranges(spec):
    \"\"\"Return the numbers named by the selection `spec`.\"\"\"
    numbers = []
    for fragment in spec.split(","):
        if "-" in fragment:
            low, high = fragment.split("-")
            numbers.extend(range(int(low), int(high) + 1))
        else:
            numbers.append(int(fragment))
    return numbers""",
    variant_one="""def expand_ranges(spec):
    \"\"\"Return the numbers named by the selection `spec`.\"\"\"
    numbers = []
    for fragment in spec.split(","):
        if not fragment.strip():
            continue
        if "-" in fragment:
            low, high = fragment.split("-")
            if int(high) < int(low):
                raise ValueError(f"{fragment!r} runs backwards")
            numbers.extend(range(int(low), int(high) + 1))
        else:
            numbers.append(int(fragment))
    return numbers""",
    variant_two="""def expand_ranges(spec):
    \"\"\"Return the numbers named by the selection `spec`.\"\"\"
    numbers = []
    fragments = [item for item in spec.split(",") if item.strip()]
    for fragment in fragments:
        start, marker, stop = fragment.partition("-")
        if not marker:
            numbers.append(int(start))
            continue
        first, last = int(start), int(stop)
        if last < first:
            raise ValueError(f"{fragment!r} runs backwards")
        numbers += list(range(first, last + 1))
    return numbers""",
    variant_three="""def expand_ranges(spec):
    \"\"\"Return the numbers named by the selection `spec`.\"\"\"
    numbers = []
    for fragment in spec.split(","):
        if "-" in fragment:
            low, high = fragment.split("-")
            if int(high) < int(low):
                raise ValueError(f"{fragment!r} runs backwards")
            numbers.extend(range(int(low), int(high) + 1))
        else:
            numbers.append(int(fragment))
    return numbers""",
    variant_four="""def expand_ranges(spec):
    \"\"\"Return the numbers named by the selection `spec`.\"\"\"
    numbers = []
    for fragment in spec.split(","):
        if not fragment.strip():
            continue
        if "-" in fragment:
            low, high = fragment.split("-")
            numbers.extend(range(int(low), int(high) + 1))
        else:
            numbers.append(int(fragment))
    return numbers""",
    visible_test=_test_module(
        "range_expand",
        "Published contract for expanding a selection.",
        """
def test_a_span_and_a_single_number() -> None:
    assert expand_ranges("1-3,5") == [1, 2, 3, 5]


def test_a_single_number_alone() -> None:
    assert expand_ranges("2") == [2]
""",
        imports="from range_expand import expand_ranges\n",
    ),
    hidden_test=_test_module(
        "range_expand",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_span_and_a_single_number() -> None:
    assert expand_ranges("1-3,5") == [1, 2, 3, 5]


def test_a_backwards_span_is_refused() -> None:
    with pytest.raises(ValueError):
        expand_ranges("5-3")


def test_an_empty_fragment_is_ignored() -> None:
    assert expand_ranges("1,,2") == [1, 2]
""",
        imports="from range_expand import expand_ranges\n",
    ),
)

_G055 = D2TaskSpec(
    template_id="d4_transform.nest_by_dot",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-nest-by-dot",
    module="dotted_nest",
    module_doc="Turning dotted names into nested records.",
    issue=(
        "nest_by_dot() is documented to turn dotted names into nested records. Callers report "
        "that a name which is both a value and a prefix of another name raises a type error "
        "instead of being reported, and that a name with an empty segment quietly creates a "
        "record under a blank name."
    ),
    expected=(
        "nest_by_dot(flat) returns the nested record, raises ValueError when a name is used both "
        "as a value and as a prefix, and raises ValueError for a name with an empty segment."
    ),
    baseline_reason="each segment is opened with setdefault, whatever is already sitting there",
    edge_cases=(
        "a name used as both value and prefix is refused",
        "a name with an empty segment is refused",
    ),
    baseline="""def nest_by_dot(flat):
    \"\"\"Return the nested record described by the dotted names of `flat`.\"\"\"
    nested = {}
    for path, value in flat.items():
        parts = path.split(".")
        current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return nested""",
    variant_one="""def nest_by_dot(flat):
    \"\"\"Return the nested record described by the dotted names of `flat`.\"\"\"
    nested = {}
    for path, value in flat.items():
        parts = path.split(".")
        if any(not part for part in parts):
            raise ValueError(f"{path!r} has an empty segment")
        current = nested
        for part in parts[:-1]:
            existing = current.setdefault(part, {})
            if not isinstance(existing, dict):
                raise ValueError(f"{part!r} is both a value and a prefix")
            current = existing
        current[parts[-1]] = value
    return nested""",
    variant_two="""def nest_by_dot(flat):
    \"\"\"Return the nested record described by the dotted names of `flat`.\"\"\"
    nested = {}
    for path in sorted(flat):
        parts = path.split(".")
        for part in parts:
            if part == "":
                raise ValueError(f"{path!r} has an empty segment")
        current = nested
        for part in parts[:-1]:
            if part in current and not isinstance(current[part], dict):
                raise ValueError(f"{part!r} is both a value and a prefix")
            current = current.setdefault(part, {})
        current[parts[-1]] = flat[path]
    return nested""",
    variant_three="""def nest_by_dot(flat):
    \"\"\"Return the nested record described by the dotted names of `flat`.\"\"\"
    nested = {}
    for path, value in flat.items():
        parts = path.split(".")
        current = nested
        for part in parts[:-1]:
            existing = current.setdefault(part, {})
            if not isinstance(existing, dict):
                raise ValueError(f"{part!r} is both a value and a prefix")
            current = existing
        current[parts[-1]] = value
    return nested""",
    variant_four="""def nest_by_dot(flat):
    \"\"\"Return the nested record described by the dotted names of `flat`.\"\"\"
    nested = {}
    for path, value in flat.items():
        parts = path.split(".")
        if any(not part for part in parts):
            raise ValueError(f"{path!r} has an empty segment")
        current = nested
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    return nested""",
    visible_test=_test_module(
        "dotted_nest",
        "Published contract for nesting dotted names.",
        """
def test_a_two_part_name_nests() -> None:
    assert nest_by_dot({"a.b": 1}) == {"a": {"b": 1}}


def test_a_plain_name_stays_at_the_top() -> None:
    assert nest_by_dot({"x": 2}) == {"x": 2}
""",
        imports="from dotted_nest import nest_by_dot\n",
    ),
    hidden_test=_test_module(
        "dotted_nest",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_two_part_name_nests() -> None:
    assert nest_by_dot({"a.b": 1}) == {"a": {"b": 1}}


def test_a_name_used_as_both_value_and_prefix_is_refused() -> None:
    with pytest.raises(ValueError):
        nest_by_dot({"a": 1, "a.b": 2})


def test_a_name_with_an_empty_segment_is_refused() -> None:
    with pytest.raises(ValueError):
        nest_by_dot({"a..b": 1})
""",
        imports="from dotted_nest import nest_by_dot\n",
    ),
)

_G056 = D2TaskSpec(
    template_id="d4_transform.merge_defaults",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-merge-defaults",
    module="default_overlay",
    module_doc="Overlaying a caller's settings on a set of defaults.",
    issue=(
        "merge_defaults() is documented to overlay a caller's settings on a set of defaults. "
        "Callers report that overriding one entry of a nested section silently discards the "
        "rest of that section, and that an override written as None is ignored rather than "
        "applied."
    ),
    expected=(
        "merge_defaults(defaults, overrides) returns a new mapping in which a nested section is "
        "merged key by key, and every key the caller wrote wins, including one written as None."
    ),
    baseline_reason=(
        "it copies the defaults, then assigns each override that looks like it has a value"
    ),
    edge_cases=(
        "a nested section keeps the default keys the override does not mention",
        "an override written as None still replaces the default",
    ),
    baseline="""def merge_defaults(defaults, overrides):
    \"\"\"Overlay `overrides` on `defaults`, merging nested sections.\"\"\"
    merged = dict(defaults)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value
    return merged""",
    variant_one="""def merge_defaults(defaults, overrides):
    \"\"\"Overlay `overrides` on `defaults`, merging nested sections.\"\"\"
    merged = dict(defaults)
    for key, value in overrides.items():
        beneath = merged.get(key)
        if isinstance(beneath, dict) and isinstance(value, dict):
            merged[key] = merge_defaults(beneath, value)
        else:
            merged[key] = value
    return merged""",
    variant_two="""def merge_defaults(defaults, overrides):
    \"\"\"Overlay `overrides` on `defaults`, merging nested sections.\"\"\"
    merged = dict(defaults)
    pending = [(merged, overrides)]
    while pending:
        target, source = pending.pop()
        for key, value in source.items():
            beneath = target.get(key)
            if isinstance(beneath, dict) and isinstance(value, dict):
                copied = dict(beneath)
                target[key] = copied
                pending.append((copied, value))
            else:
                target[key] = value
    return merged""",
    variant_three="""def merge_defaults(defaults, overrides):
    \"\"\"Overlay `overrides` on `defaults`, merging nested sections.\"\"\"
    merged = dict(defaults)
    for key, value in overrides.items():
        if value is None:
            continue
        beneath = merged.get(key)
        if isinstance(beneath, dict) and isinstance(value, dict):
            merged[key] = merge_defaults(beneath, value)
        else:
            merged[key] = value
    return merged""",
    variant_four="""def merge_defaults(defaults, overrides):
    \"\"\"Overlay `overrides` on `defaults`, merging nested sections.\"\"\"
    return {**defaults, **overrides}""",
    visible_test=_test_module(
        "default_overlay",
        "Published contract for overlaying settings on defaults.",
        """
def test_an_override_wins() -> None:
    assert merge_defaults({"host": "local", "port": 80}, {"port": 8080}) == {
        "host": "local",
        "port": 8080,
    }


def test_a_key_the_defaults_do_not_have_is_added() -> None:
    assert merge_defaults({"host": "local"}, {"debug": True}) == {
        "host": "local",
        "debug": True,
    }


def test_no_overrides_leaves_the_defaults_alone() -> None:
    assert merge_defaults({"host": "local"}, {}) == {"host": "local"}
""",
        imports="from default_overlay import merge_defaults\n",
    ),
    hidden_test=_test_module(
        "default_overlay",
        "The part of the contract the published tests do not state.",
        """
def test_an_override_wins() -> None:
    assert merge_defaults({"host": "local", "port": 80}, {"port": 8080}) == {
        "host": "local",
        "port": 8080,
    }


def test_a_nested_section_keeps_the_keys_the_override_does_not_mention() -> None:
    defaults = {"log": {"level": "info", "path": "/var/log"}}
    assert merge_defaults(defaults, {"log": {"level": "debug"}}) == {
        "log": {"level": "debug", "path": "/var/log"}
    }


def test_an_override_written_as_none_still_replaces_the_default() -> None:
    assert merge_defaults({"proxy": "corp"}, {"proxy": None}) == {"proxy": None}
""",
        imports="from default_overlay import merge_defaults\n",
    ),
)

_G057 = D2TaskSpec(
    template_id="d4_transform.tabulate_rows",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-tabulate-rows",
    module="record_table",
    module_doc="Laying records out as a header and rows.",
    issue=(
        "tabulate_rows() is documented to lay a list of records out as a header and one row per "
        "record. Callers report that a field which first appears in a later record gets no "
        "column at all, and that a record missing a field renders the word None in that cell."
    ),
    expected=(
        "tabulate_rows(records) returns (header, rows); the header holds every field any record "
        "has, in the order it was first seen, and a record missing a field renders an empty cell."
    ),
    baseline_reason=(
        "it reads the column names off the first record and stringifies whatever it finds"
    ),
    edge_cases=(
        "a field that first appears in a later record still gets a column",
        "a record missing a field renders an empty cell",
    ),
    baseline="""def tabulate_rows(records):
    \"\"\"Return (header, rows) for `records`, one row per record.\"\"\"
    if not records:
        return [], []
    header = list(records[0])
    rows = [[str(record.get(name)) for name in header] for record in records]
    return header, rows""",
    variant_one="""def tabulate_rows(records):
    \"\"\"Return (header, rows) for `records`, one row per record.\"\"\"
    header = []
    for record in records:
        for name in record:
            if name not in header:
                header.append(name)
    rows = [
        [str(record[name]) if name in record else "" for name in header] for record in records
    ]
    return header, rows""",
    variant_two="""def tabulate_rows(records):
    \"\"\"Return (header, rows) for `records`, one row per record.\"\"\"
    columns = {}
    for record in records:
        columns.update(dict.fromkeys(record))
    header = list(columns)
    rows = []
    for record in records:
        row = []
        for name in header:
            row.append("" if name not in record else str(record[name]))
        rows.append(row)
    return header, rows""",
    variant_three="""def tabulate_rows(records):
    \"\"\"Return (header, rows) for `records`, one row per record.\"\"\"
    header = []
    for record in records:
        for name in record:
            if name not in header:
                header.append(name)
    rows = [[str(record.get(name)) for name in header] for record in records]
    return header, rows""",
    variant_four="""def tabulate_rows(records):
    \"\"\"Return (header, rows) for `records`, one row per record.\"\"\"
    if not records:
        return [], []
    header = list(records[0])
    rows = [
        [str(record[name]) if name in record else "" for name in header] for record in records
    ]
    return header, rows""",
    visible_test=_test_module(
        "record_table",
        "Published contract for laying records out as a table.",
        """
def test_records_that_share_their_fields() -> None:
    header, rows = tabulate_rows([{"id": 1, "name": "ada"}, {"id": 2, "name": "bo"}])
    assert header == ["id", "name"]
    assert rows == [["1", "ada"], ["2", "bo"]]


def test_a_single_record() -> None:
    assert tabulate_rows([{"id": 7}]) == (["id"], [["7"]])


def test_no_records_at_all() -> None:
    assert tabulate_rows([]) == ([], [])
""",
        imports="from record_table import tabulate_rows\n",
    ),
    hidden_test=_test_module(
        "record_table",
        "The part of the contract the published tests do not state.",
        """
def test_records_that_share_their_fields() -> None:
    header, rows = tabulate_rows([{"id": 1, "name": "ada"}, {"id": 2, "name": "bo"}])
    assert header == ["id", "name"]
    assert rows == [["1", "ada"], ["2", "bo"]]


def test_a_field_first_seen_in_a_later_record_still_gets_a_column() -> None:
    header, rows = tabulate_rows([{"id": 1}, {"id": 2, "note": "late"}])
    assert header == ["id", "note"]
    assert rows == [["1", ""], ["2", "late"]]


def test_a_record_missing_a_field_renders_an_empty_cell() -> None:
    header, rows = tabulate_rows([{"id": 1, "name": "ada"}, {"id": 2}])
    assert header == ["id", "name"]
    assert rows == [["1", "ada"], ["2", ""]]
""",
        imports="from record_table import tabulate_rows\n",
    ),
)

_G058 = D2TaskSpec(
    template_id="d4_transform.camel_to_snake",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-camel-to-snake",
    module="name_convention",
    module_doc="Rewriting identifiers from one naming convention to another.",
    issue=(
        "camel_to_snake() is documented to rewrite an identifier in snake_case. Callers report "
        "that a run of capitals comes back with an underscore between every letter, and that a "
        "name beginning with a capital comes back with a leading underscore."
    ),
    expected=(
        "camel_to_snake(name) lower-cases the name and separates its words with underscores, "
        "treating a run of capitals as one word and never opening the result with an underscore."
    ),
    baseline_reason="it opens an underscore in front of every capital letter it meets",
    edge_cases=(
        "a run of capitals is one word",
        "a name beginning with a capital gains no leading underscore",
    ),
    baseline="""def camel_to_snake(name):
    \"\"\"Return `name` written in snake_case.\"\"\"
    letters = []
    for letter in name:
        if letter.isupper():
            letters.append("_")
            letters.append(letter.lower())
        else:
            letters.append(letter)
    return "".join(letters)""",
    variant_one="""def camel_to_snake(name):
    \"\"\"Return `name` written in snake_case.\"\"\"
    letters = []
    for index, letter in enumerate(name):
        if not letter.isupper():
            letters.append(letter)
            continue
        after_lower = index > 0 and name[index - 1].islower()
        before_lower = index + 1 < len(name) and name[index + 1].islower()
        if index > 0 and (after_lower or before_lower):
            letters.append("_")
        letters.append(letter.lower())
    return "".join(letters)""",
    variant_two="""def camel_to_snake(name):
    \"\"\"Return `name` written in snake_case.\"\"\"
    words = []
    current = ""
    for index, letter in enumerate(name):
        following = name[index + 1] if index + 1 < len(name) else ""
        opens_word = (
            letter.isupper() and current and (current[-1].islower() or following.islower())
        )
        if opens_word:
            words.append(current)
            current = letter
        else:
            current += letter
    if current:
        words.append(current)
    return "_".join(word.lower() for word in words)""",
    variant_three="""def camel_to_snake(name):
    \"\"\"Return `name` written in snake_case.\"\"\"
    letters = []
    for index, letter in enumerate(name):
        if not letter.isupper():
            letters.append(letter)
            continue
        after_lower = index > 0 and name[index - 1].islower()
        before_lower = index + 1 < len(name) and name[index + 1].islower()
        if after_lower or before_lower:
            letters.append("_")
        letters.append(letter.lower())
    return "".join(letters)""",
    variant_four="""def camel_to_snake(name):
    \"\"\"Return `name` written in snake_case.\"\"\"
    letters = []
    for index, letter in enumerate(name):
        if letter.isupper():
            if index > 0:
                letters.append("_")
            letters.append(letter.lower())
        else:
            letters.append(letter)
    return "".join(letters)""",
    visible_test=_test_module(
        "name_convention",
        "Published contract for rewriting an identifier in snake_case.",
        """
def test_a_two_word_name() -> None:
    assert camel_to_snake("userName") == "user_name"


def test_a_three_word_name() -> None:
    assert camel_to_snake("totalItemCount") == "total_item_count"


def test_a_name_that_is_already_one_word() -> None:
    assert camel_to_snake("value") == "value"
""",
        imports="from name_convention import camel_to_snake\n",
    ),
    hidden_test=_test_module(
        "name_convention",
        "The part of the contract the published tests do not state.",
        """
def test_a_two_word_name() -> None:
    assert camel_to_snake("userName") == "user_name"


def test_a_run_of_capitals_is_one_word() -> None:
    assert camel_to_snake("parseHTTPResponse") == "parse_http_response"


def test_a_name_beginning_with_a_capital_gains_no_leading_underscore() -> None:
    assert camel_to_snake("UserName") == "user_name"
""",
        imports="from name_convention import camel_to_snake\n",
    ),
)

_G059 = D2TaskSpec(
    template_id="d4_transform.fill_forward",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-fill-forward",
    module="forward_fill",
    module_doc="Carrying the last known reading over the gaps in a column.",
    issue=(
        "fill_forward() is documented to carry the last known reading over the gaps in a column "
        "of readings. Callers report that a column beginning with a gap comes back opening at "
        "zero rather than still unknown, and that the list they handed in comes back changed."
    ),
    expected=(
        "fill_forward(values) returns a new list in which every gap holds the nearest reading "
        "before it, a gap with no reading before it stays a gap, and the caller's own list is "
        "left as it was."
    ),
    baseline_reason=(
        "it patches the gaps in place, starting from zero because nothing has been read yet"
    ),
    edge_cases=(
        "a column opening with a gap stays open",
        "the caller's list is left as it was",
    ),
    baseline="""def fill_forward(values):
    \"\"\"Carry the last known reading forward over the gaps.\"\"\"
    last = 0
    for index, value in enumerate(values):
        if value is None:
            values[index] = last
        else:
            last = value
    return values""",
    variant_one="""def fill_forward(values):
    \"\"\"Carry the last known reading forward over the gaps.\"\"\"
    filled = []
    last = None
    for value in values:
        if value is None:
            filled.append(last)
        else:
            last = value
            filled.append(value)
    return filled""",
    variant_two="""def fill_forward(values):
    \"\"\"Carry the last known reading forward over the gaps.\"\"\"
    filled = list(values)
    for index in range(1, len(filled)):
        if filled[index] is None:
            filled[index] = filled[index - 1]
    return filled""",
    variant_three="""def fill_forward(values):
    \"\"\"Carry the last known reading forward over the gaps.\"\"\"
    last = None
    for index, value in enumerate(values):
        if value is None:
            values[index] = last
        else:
            last = value
    return values""",
    variant_four="""def fill_forward(values):
    \"\"\"Carry the last known reading forward over the gaps.\"\"\"
    filled = list(values)
    last = 0
    for index, value in enumerate(filled):
        if value is None:
            filled[index] = last
        else:
            last = value
    return filled""",
    visible_test=_test_module(
        "forward_fill",
        "Published contract for carrying a reading over the gaps.",
        """
def test_one_reading_covers_the_gaps_after_it() -> None:
    assert fill_forward([1, None, None, 4]) == [1, 1, 1, 4]


def test_a_column_with_no_gaps_at_all() -> None:
    assert fill_forward([2, 3, 5]) == [2, 3, 5]


def test_a_gap_at_the_very_end() -> None:
    assert fill_forward([5, None]) == [5, 5]
""",
        imports="from forward_fill import fill_forward\n",
    ),
    hidden_test=_test_module(
        "forward_fill",
        "The part of the contract the published tests do not state.",
        """
def test_one_reading_covers_the_gaps_after_it() -> None:
    assert fill_forward([1, None, None, 4]) == [1, 1, 1, 4]


def test_a_column_opening_with_a_gap_stays_open() -> None:
    assert fill_forward([None, None, 3]) == [None, None, 3]


def test_the_callers_list_is_left_as_it_was() -> None:
    readings = [1, None, 3]
    fill_forward(readings)
    assert readings == [1, None, 3]
""",
        imports="from forward_fill import fill_forward\n",
    ),
)

_G060 = D2TaskSpec(
    template_id="d4_transform.join_on_key",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-join-on-key",
    module="record_join",
    module_doc="Joining one list of records onto another on a shared field.",
    issue=(
        "join_on_key() is documented to bring a second list of records alongside a first on a "
        "shared field. Callers report that a record with nothing to join to disappears from the "
        "result, and that where both sides carry the same field the second side's value is the "
        "one that survives."
    ),
    expected=(
        "join_on_key(left, right, key) returns one record per left record, in the left order, "
        "carrying the matching right record's fields where there is one, and the left record's "
        "own value wherever both sides carry the same field."
    ),
    baseline_reason=(
        "it indexes the right side, skips a left record that misses, and merges the match on top"
    ),
    edge_cases=(
        "a left record with nothing to join to is still returned",
        "the left record's value wins a field both sides carry",
    ),
    baseline="""def join_on_key(left, right, key):
    \"\"\"Join `right` onto `left` on `key`, keeping every left record.\"\"\"
    index = {record[key]: record for record in right}
    joined = []
    for record in left:
        match = index.get(record[key])
        if match is None:
            continue
        joined.append({**record, **match})
    return joined""",
    variant_one="""def join_on_key(left, right, key):
    \"\"\"Join `right` onto `left` on `key`, keeping every left record.\"\"\"
    index = {record[key]: record for record in right}
    joined = []
    for record in left:
        merged = dict(index.get(record[key], {}))
        merged.update(record)
        joined.append(merged)
    return joined""",
    variant_two="""def join_on_key(left, right, key):
    \"\"\"Join `right` onto `left` on `key`, keeping every left record.\"\"\"
    joined = []
    for record in left:
        merged = dict(record)
        for other in right:
            if other[key] == record[key]:
                for name, value in other.items():
                    merged.setdefault(name, value)
                break
        joined.append(merged)
    return joined""",
    variant_three="""def join_on_key(left, right, key):
    \"\"\"Join `right` onto `left` on `key`, keeping every left record.\"\"\"
    index = {record[key]: record for record in right}
    joined = []
    for record in left:
        match = index.get(record[key], {})
        joined.append({**record, **match})
    return joined""",
    variant_four="""def join_on_key(left, right, key):
    \"\"\"Join `right` onto `left` on `key`, keeping every left record.\"\"\"
    index = {record[key]: record for record in right}
    joined = []
    for record in left:
        match = index.get(record[key])
        if match is None:
            continue
        joined.append({**match, **record})
    return joined""",
    visible_test=_test_module(
        "record_join",
        "Published contract for joining records on a shared field.",
        """
def test_every_record_finds_its_match() -> None:
    left = [{"id": 1, "name": "ada"}, {"id": 2, "name": "bo"}]
    right = [{"id": 2, "city": "oslo"}, {"id": 1, "city": "kyiv"}]
    assert join_on_key(left, right, "id") == [
        {"id": 1, "name": "ada", "city": "kyiv"},
        {"id": 2, "name": "bo", "city": "oslo"},
    ]


def test_the_left_order_is_kept() -> None:
    left = [{"id": 2}, {"id": 1}]
    right = [{"id": 1, "city": "kyiv"}, {"id": 2, "city": "oslo"}]
    assert [record["id"] for record in join_on_key(left, right, "id")] == [2, 1]


def test_a_single_record_on_each_side() -> None:
    assert join_on_key([{"id": 1}], [{"id": 1, "city": "oslo"}], "id") == [
        {"id": 1, "city": "oslo"}
    ]
""",
        imports="from record_join import join_on_key\n",
    ),
    hidden_test=_test_module(
        "record_join",
        "The part of the contract the published tests do not state.",
        """
def test_every_record_finds_its_match() -> None:
    left = [{"id": 1, "name": "ada"}]
    right = [{"id": 1, "city": "kyiv"}]
    assert join_on_key(left, right, "id") == [{"id": 1, "name": "ada", "city": "kyiv"}]


def test_a_left_record_with_nothing_to_join_to_is_still_returned() -> None:
    left = [{"id": 1, "name": "ada"}, {"id": 9, "name": "zoe"}]
    right = [{"id": 1, "city": "kyiv"}]
    assert join_on_key(left, right, "id") == [
        {"id": 1, "name": "ada", "city": "kyiv"},
        {"id": 9, "name": "zoe"},
    ]


def test_the_left_value_wins_a_field_both_sides_carry() -> None:
    left = [{"id": 1, "city": "kyiv"}]
    right = [{"id": 1, "city": "oslo"}]
    assert join_on_key(left, right, "id") == [{"id": 1, "city": "kyiv"}]
""",
        imports="from record_join import join_on_key\n",
    ),
)

_G061 = D2TaskSpec(
    template_id="d4_transform.unfold_multi_values",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-unfold-multi-values",
    module="multi_value_unfold",
    module_doc="Expanding a record whose field holds several values.",
    issue=(
        "unfold_multi_values() is documented to expand a record whose field holds several values "
        "into one record per value. Callers report that a record whose list is empty vanishes "
        "from the result, and that a record whose field holds a plain string comes back as one "
        "record per letter."
    ),
    expected=(
        "unfold_multi_values(records, field) yields one record per value of `field`, yields a "
        "single record carrying None for an empty list, and leaves a record whose field is not a "
        "list untouched."
    ),
    baseline_reason="it loops over whatever the field holds, which a string obligingly allows",
    edge_cases=(
        "an empty list still yields one record",
        "a field holding a plain value is not taken apart",
    ),
    baseline="""def unfold_multi_values(records, field):
    \"\"\"Expand `field` so that every record holds one value.\"\"\"
    expanded = []
    for record in records:
        for value in record[field]:
            copied = dict(record)
            copied[field] = value
            expanded.append(copied)
    return expanded""",
    variant_one="""def unfold_multi_values(records, field):
    \"\"\"Expand `field` so that every record holds one value.\"\"\"
    expanded = []
    for record in records:
        held = record[field]
        if not isinstance(held, list):
            expanded.append(dict(record))
            continue
        if not held:
            blank = dict(record)
            blank[field] = None
            expanded.append(blank)
            continue
        for value in held:
            copied = dict(record)
            copied[field] = value
            expanded.append(copied)
    return expanded""",
    variant_two="""def unfold_multi_values(records, field):
    \"\"\"Expand `field` so that every record holds one value.\"\"\"
    expanded = []
    for record in records:
        held = record[field]
        if not isinstance(held, list):
            spread = [held]
        elif held:
            spread = held
        else:
            spread = [None]
        expanded.extend({**record, field: value} for value in spread)
    return expanded""",
    variant_three="""def unfold_multi_values(records, field):
    \"\"\"Expand `field` so that every record holds one value.\"\"\"
    expanded = []
    for record in records:
        held = record[field] or [None]
        for value in held:
            copied = dict(record)
            copied[field] = value
            expanded.append(copied)
    return expanded""",
    variant_four="""def unfold_multi_values(records, field):
    \"\"\"Expand `field` so that every record holds one value.\"\"\"
    expanded = []
    for record in records:
        held = record[field]
        if not isinstance(held, list):
            expanded.append(dict(record))
            continue
        for value in held:
            copied = dict(record)
            copied[field] = value
            expanded.append(copied)
    return expanded""",
    visible_test=_test_module(
        "multi_value_unfold",
        "Published contract for expanding a record's repeated field.",
        """
def test_a_record_with_two_values() -> None:
    assert unfold_multi_values([{"id": 1, "tag": ["a", "b"]}], "tag") == [
        {"id": 1, "tag": "a"},
        {"id": 1, "tag": "b"},
    ]


def test_a_record_with_one_value() -> None:
    assert unfold_multi_values([{"id": 1, "tag": ["a"]}], "tag") == [{"id": 1, "tag": "a"}]


def test_two_records_expand_in_order() -> None:
    records = [{"id": 1, "tag": ["a"]}, {"id": 2, "tag": ["b", "c"]}]
    assert [record["id"] for record in unfold_multi_values(records, "tag")] == [1, 2, 2]
""",
        imports="from multi_value_unfold import unfold_multi_values\n",
    ),
    hidden_test=_test_module(
        "multi_value_unfold",
        "The part of the contract the published tests do not state.",
        """
def test_a_record_with_two_values() -> None:
    assert unfold_multi_values([{"id": 1, "tag": ["a", "b"]}], "tag") == [
        {"id": 1, "tag": "a"},
        {"id": 1, "tag": "b"},
    ]


def test_an_empty_list_still_yields_one_record() -> None:
    assert unfold_multi_values([{"id": 1, "tag": []}], "tag") == [{"id": 1, "tag": None}]


def test_a_field_holding_a_plain_value_is_not_taken_apart() -> None:
    assert unfold_multi_values([{"id": 1, "tag": "ab"}], "tag") == [{"id": 1, "tag": "ab"}]
""",
        imports="from multi_value_unfold import unfold_multi_values\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G062 = D2TaskSpec(
    template_id="d4_boundary.merge_intervals",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-merge-intervals",
    module="interval_merge",
    module_doc="Reducing closed intervals to the fewest that cover the same points.",
    issue=(
        "merge_intervals() is documented to reduce a set of closed intervals to the fewest that "
        "cover the same points. Callers report that two intervals meeting exactly at a point "
        "come back separate, and that intervals handed over out of order come back merged into "
        "nonsense."
    ),
    expected=(
        "merge_intervals(intervals) returns the merged intervals in ascending order, joining two "
        "that meet at a single point, and does not require the caller to sort them first."
    ),
    baseline_reason=(
        "it folds the intervals in the order given and only joins one that starts strictly inside"
    ),
    edge_cases=(
        "intervals that meet at a single point are joined",
        "intervals handed over out of order are merged all the same",
    ),
    baseline="""def merge_intervals(intervals):
    \"\"\"Reduce closed `intervals` to the fewest that cover the same points.\"\"\"
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            opened, closed = merged[-1]
            merged[-1] = (opened, max(closed, end))
        else:
            merged.append((start, end))
    return merged""",
    variant_one="""def merge_intervals(intervals):
    \"\"\"Reduce closed `intervals` to the fewest that cover the same points.\"\"\"
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            opened, closed = merged[-1]
            merged[-1] = (opened, max(closed, end))
        else:
            merged.append((start, end))
    return merged""",
    variant_two="""def merge_intervals(intervals):
    \"\"\"Reduce closed `intervals` to the fewest that cover the same points.\"\"\"
    merged = []
    current = None
    for start, end in sorted(intervals):
        if current is None:
            current = [start, end]
        elif start <= current[1]:
            current[1] = max(current[1], end)
        else:
            merged.append((current[0], current[1]))
            current = [start, end]
    if current is not None:
        merged.append((current[0], current[1]))
    return merged""",
    variant_three="""def merge_intervals(intervals):
    \"\"\"Reduce closed `intervals` to the fewest that cover the same points.\"\"\"
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            opened, closed = merged[-1]
            merged[-1] = (opened, max(closed, end))
        else:
            merged.append((start, end))
    return merged""",
    variant_four="""def merge_intervals(intervals):
    \"\"\"Reduce closed `intervals` to the fewest that cover the same points.\"\"\"
    merged = []
    for start, end in sorted(intervals):
        if merged and start < merged[-1][1]:
            opened, closed = merged[-1]
            merged[-1] = (opened, max(closed, end))
        else:
            merged.append((start, end))
    return merged""",
    visible_test=_test_module(
        "interval_merge",
        "Published contract for merging closed intervals.",
        """
def test_two_intervals_that_overlap() -> None:
    assert merge_intervals([(1, 5), (3, 8)]) == [(1, 8)]


def test_intervals_that_stay_apart() -> None:
    assert merge_intervals([(1, 2), (5, 6)]) == [(1, 2), (5, 6)]


def test_one_interval_swallowing_another() -> None:
    assert merge_intervals([(1, 9), (3, 4)]) == [(1, 9)]
""",
        imports="from interval_merge import merge_intervals\n",
    ),
    hidden_test=_test_module(
        "interval_merge",
        "The part of the contract the published tests do not state.",
        """
def test_two_intervals_that_overlap() -> None:
    assert merge_intervals([(1, 5), (3, 8)]) == [(1, 8)]


def test_intervals_that_meet_at_a_single_point_are_joined() -> None:
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]


def test_intervals_handed_over_out_of_order_are_merged_all_the_same() -> None:
    assert merge_intervals([(5, 8), (1, 2)]) == [(1, 2), (5, 8)]
""",
        imports="from interval_merge import merge_intervals\n",
    ),
)

_G063 = D2TaskSpec(
    template_id="d4_boundary.split_at_indices",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-split-at-indices",
    module="cut_points",
    module_doc="Cutting a sequence at a set of positions.",
    issue=(
        "split_at_indices() is documented to cut a sequence at a set of positions. Callers "
        "report that positions handed over out of order produce empty pieces in the middle, and "
        "that a position past the end leaves an empty piece hanging off the back."
    ),
    expected=(
        "split_at_indices(items, cuts) returns the pieces between the cuts in order, accepts the "
        "cuts in any order, and ignores a cut at or before the start or at or past the end."
    ),
    baseline_reason=(
        "it walks the cuts exactly as handed over and slices from the last one to the end"
    ),
    edge_cases=(
        "cuts handed over out of order still cut in order",
        "a cut past the end leaves no empty piece",
    ),
    baseline="""def split_at_indices(items, cuts):
    \"\"\"Cut `items` into the pieces between `cuts`.\"\"\"
    pieces = []
    start = 0
    for cut in cuts:
        pieces.append(items[start:cut])
        start = cut
    pieces.append(items[start:])
    return pieces""",
    variant_one="""def split_at_indices(items, cuts):
    \"\"\"Cut `items` into the pieces between `cuts`.\"\"\"
    pieces = []
    start = 0
    for cut in sorted(cut for cut in cuts if 0 < cut < len(items)):
        pieces.append(items[start:cut])
        start = cut
    pieces.append(items[start:])
    return pieces""",
    variant_two="""def split_at_indices(items, cuts):
    \"\"\"Cut `items` into the pieces between `cuts`.\"\"\"
    inside = sorted(cut for cut in cuts if 0 < cut < len(items))
    bounds = [0, *inside, len(items)]
    return [items[bounds[index] : bounds[index + 1]] for index in range(len(bounds) - 1)]""",
    variant_three="""def split_at_indices(items, cuts):
    \"\"\"Cut `items` into the pieces between `cuts`.\"\"\"
    pieces = []
    start = 0
    for cut in sorted(cuts):
        pieces.append(items[start:cut])
        start = cut
    pieces.append(items[start:])
    return pieces""",
    variant_four="""def split_at_indices(items, cuts):
    \"\"\"Cut `items` into the pieces between `cuts`.\"\"\"
    pieces = []
    start = 0
    for cut in cuts:
        if not 0 < cut < len(items):
            continue
        pieces.append(items[start:cut])
        start = cut
    pieces.append(items[start:])
    return pieces""",
    visible_test=_test_module(
        "cut_points",
        "Published contract for cutting a sequence at positions.",
        """
def test_one_cut() -> None:
    assert split_at_indices([1, 2, 3, 4, 5], [2]) == [[1, 2], [3, 4, 5]]


def test_two_cuts_in_order() -> None:
    assert split_at_indices([1, 2, 3, 4, 5, 6], [2, 4]) == [[1, 2], [3, 4], [5, 6]]


def test_no_cuts_at_all() -> None:
    assert split_at_indices([1, 2, 3], []) == [[1, 2, 3]]
""",
        imports="from cut_points import split_at_indices\n",
    ),
    hidden_test=_test_module(
        "cut_points",
        "The part of the contract the published tests do not state.",
        """
def test_one_cut() -> None:
    assert split_at_indices([1, 2, 3, 4, 5], [2]) == [[1, 2], [3, 4, 5]]


def test_cuts_handed_over_out_of_order_still_cut_in_order() -> None:
    assert split_at_indices([1, 2, 3, 4, 5, 6], [4, 2]) == [[1, 2], [3, 4], [5, 6]]


def test_a_cut_past_the_end_leaves_no_empty_piece() -> None:
    assert split_at_indices([1, 2, 3, 4], [2, 9]) == [[1, 2], [3, 4]]
""",
        imports="from cut_points import split_at_indices\n",
    ),
)

_G064 = D2TaskSpec(
    template_id="d4_boundary.sample_evenly",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-sample-evenly",
    module="even_sampling",
    module_doc="Taking a fixed number of items spread across a sequence.",
    issue=(
        "sample_evenly() is documented to take a fixed number of items spread across a sequence, "
        "keeping both ends. Callers report that asking for one item raises, and that asking for "
        "more items than the sequence holds returns the same item several times over."
    ),
    expected=(
        "sample_evenly(items, count) returns `count` items spread evenly across the sequence "
        "including both ends, returns the first item alone when one is asked for, and returns "
        "the whole sequence when more are asked for than it holds."
    ),
    baseline_reason="it divides the span by one fewer than the count and trusts the count to fit",
    edge_cases=(
        "asking for one item returns the first",
        "asking for more than the sequence holds returns all of it",
    ),
    baseline="""def sample_evenly(items, count):
    \"\"\"Take `count` items spread evenly across `items`, keeping both ends.\"\"\"
    step = (len(items) - 1) / (count - 1)
    return [items[int(index * step + 0.5)] for index in range(count)]""",
    variant_one="""def sample_evenly(items, count):
    \"\"\"Take `count` items spread evenly across `items`, keeping both ends.\"\"\"
    if count <= 0 or not items:
        return []
    if count == 1:
        return [items[0]]
    if count >= len(items):
        return list(items)
    step = (len(items) - 1) / (count - 1)
    return [items[int(index * step + 0.5)] for index in range(count)]""",
    variant_two="""def sample_evenly(items, count):
    \"\"\"Take `count` items spread evenly across `items`, keeping both ends.\"\"\"
    if count <= 0 or not items:
        return []
    if count >= len(items):
        return list(items)
    if count == 1:
        return [items[0]]
    span = len(items) - 1
    picked = []
    for index in range(count):
        picked.append(items[(index * span + (count - 1) // 2) // (count - 1)])
    return picked""",
    variant_three="""def sample_evenly(items, count):
    \"\"\"Take `count` items spread evenly across `items`, keeping both ends.\"\"\"
    if count == 1:
        return [items[0]]
    step = (len(items) - 1) / (count - 1)
    return [items[int(index * step + 0.5)] for index in range(count)]""",
    variant_four="""def sample_evenly(items, count):
    \"\"\"Take `count` items spread evenly across `items`, keeping both ends.\"\"\"
    if count >= len(items):
        return list(items)
    step = (len(items) - 1) / (count - 1)
    return [items[int(index * step + 0.5)] for index in range(count)]""",
    visible_test=_test_module(
        "even_sampling",
        "Published contract for sampling a sequence evenly.",
        """
def test_three_of_five() -> None:
    assert sample_evenly([1, 2, 3, 4, 5], 3) == [1, 3, 5]


def test_both_ends_and_nothing_else() -> None:
    assert sample_evenly([1, 2, 3, 4, 5], 2) == [1, 5]


def test_four_of_five() -> None:
    assert sample_evenly([1, 2, 3, 4, 5], 4) == [1, 2, 4, 5]
""",
        imports="from even_sampling import sample_evenly\n",
    ),
    hidden_test=_test_module(
        "even_sampling",
        "The part of the contract the published tests do not state.",
        """
def test_three_of_five() -> None:
    assert sample_evenly([1, 2, 3, 4, 5], 3) == [1, 3, 5]


def test_asking_for_one_item_returns_the_first() -> None:
    assert sample_evenly([1, 2, 3, 4, 5], 1) == [1]


def test_asking_for_more_than_the_sequence_holds_returns_all_of_it() -> None:
    assert sample_evenly([1, 2, 3], 5) == [1, 2, 3]
""",
        imports="from even_sampling import sample_evenly\n",
    ),
)

_G065 = D2TaskSpec(
    template_id="d4_boundary.first_at_least",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d4-boundary-first-at-least",
    module="lower_bound_search",
    module_doc="Finding where a value belongs in a sorted sequence.",
    issue=(
        "first_at_least() is documented to report the first position in a sorted sequence whose "
        "value reaches a target. Callers report that a target beyond everything in the sequence "
        "answers minus one rather than the length, and that an empty sequence raises instead of "
        "answering zero."
    ),
    expected=(
        "first_at_least(items, target) returns the index of the first item that is at least "
        "`target`, returns the length of the sequence when no item reaches it, and returns zero "
        "for an empty sequence."
    ),
    baseline_reason=(
        "it settles the hopeless case by peeking at the last item and answering minus one"
    ),
    edge_cases=(
        "a target beyond everything answers the length",
        "an empty sequence answers zero",
    ),
    baseline="""def first_at_least(items, target):
    \"\"\"Return the first index in sorted `items` whose value is at least `target`.\"\"\"
    if items[-1] < target:
        return -1
    low = 0
    high = len(items) - 1
    while low < high:
        middle = (low + high) // 2
        if items[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low""",
    variant_one="""def first_at_least(items, target):
    \"\"\"Return the first index in sorted `items` whose value is at least `target`.\"\"\"
    low = 0
    high = len(items)
    while low < high:
        middle = (low + high) // 2
        if items[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low""",
    variant_two="""def first_at_least(items, target):
    \"\"\"Return the first index in sorted `items` whose value is at least `target`.\"\"\"
    for index, value in enumerate(items):
        if value >= target:
            return index
    return len(items)""",
    variant_three="""def first_at_least(items, target):
    \"\"\"Return the first index in sorted `items` whose value is at least `target`.\"\"\"
    if items[-1] < target:
        return len(items)
    low = 0
    high = len(items) - 1
    while low < high:
        middle = (low + high) // 2
        if items[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low""",
    variant_four="""def first_at_least(items, target):
    \"\"\"Return the first index in sorted `items` whose value is at least `target`.\"\"\"
    if not items:
        return 0
    if items[-1] < target:
        return -1
    low = 0
    high = len(items) - 1
    while low < high:
        middle = (low + high) // 2
        if items[middle] < target:
            low = middle + 1
        else:
            high = middle
    return low""",
    visible_test=_test_module(
        "lower_bound_search",
        "Published contract for finding where a value belongs.",
        """
def test_a_value_that_is_present() -> None:
    assert first_at_least([1, 3, 5, 7], 3) == 1


def test_a_value_that_falls_between_two() -> None:
    assert first_at_least([1, 3, 5, 7], 4) == 2


def test_a_value_at_or_below_the_first() -> None:
    assert first_at_least([1, 3, 5, 7], 1) == 0
    assert first_at_least([1, 3, 5, 7], 0) == 0
""",
        imports="from lower_bound_search import first_at_least\n",
    ),
    hidden_test=_test_module(
        "lower_bound_search",
        "The part of the contract the published tests do not state.",
        """
def test_a_value_that_is_present() -> None:
    assert first_at_least([1, 3, 5, 7], 3) == 1


def test_a_target_beyond_everything_answers_the_length() -> None:
    assert first_at_least([1, 3, 5, 7], 9) == 4


def test_an_empty_sequence_answers_zero() -> None:
    assert first_at_least([], 3) == 0
""",
        imports="from lower_bound_search import first_at_least\n",
    ),
)

# ------------------------------------------------------------------------ parsing and validation

_G066 = D2TaskSpec(
    template_id="d4_parsing.percent_escapes",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-percent-escapes",
    module="percent_escapes",
    module_doc="Decoding the percent escapes in an encoded string.",
    issue=(
        "decode_percent() is documented to decode the percent escapes in a string. Callers "
        "report that a percent sign the encoder never meant as an escape brings the whole call "
        "down, and that an escape written with lowercase hex digits is refused rather than "
        "decoded."
    ),
    expected=(
        "decode_percent(text) replaces every percent sign followed by two hex digits with the "
        "character they name, reads those digits in either case, and leaves a percent sign that "
        "is not followed by two hex digits exactly as it was written."
    ),
    baseline_reason=(
        "it accepts only the uppercase digits it knows and refuses everything else outright"
    ),
    edge_cases=(
        "a percent sign that is not an escape is left as written",
        "hex digits written in lowercase are decoded too",
    ),
    baseline="""def decode_percent(text):
    \"\"\"Decode the percent escapes in `text`.\"\"\"
    digits = "0123456789ABCDEF"
    decoded = []
    index = 0
    while index < len(text):
        letter = text[index]
        if letter != "%":
            decoded.append(letter)
            index += 1
            continue
        code = text[index + 1 : index + 3]
        if len(code) == 2 and all(digit in digits for digit in code):
            decoded.append(chr(int(code, 16)))
            index += 3
        else:
            raise ValueError("a percent sign must be followed by two hex digits")
    return "".join(decoded)""",
    variant_one="""def decode_percent(text):
    \"\"\"Decode the percent escapes in `text`.\"\"\"
    digits = "0123456789abcdefABCDEF"
    decoded = []
    index = 0
    while index < len(text):
        letter = text[index]
        if letter != "%":
            decoded.append(letter)
            index += 1
            continue
        code = text[index + 1 : index + 3]
        if len(code) == 2 and all(digit in digits for digit in code):
            decoded.append(chr(int(code, 16)))
            index += 3
        else:
            decoded.append(letter)
            index += 1
    return "".join(decoded)""",
    variant_two="""def decode_percent(text):
    \"\"\"Decode the percent escapes in `text`.\"\"\"
    pieces = text.split("%")
    decoded = [pieces[0]]
    for piece in pieces[1:]:
        head = piece[:2]
        if len(head) == 2 and all(digit in "0123456789abcdefABCDEF" for digit in head):
            decoded.append(chr(int(head, 16)) + piece[2:])
        else:
            decoded.append("%" + piece)
    return "".join(decoded)""",
    variant_three="""def decode_percent(text):
    \"\"\"Decode the percent escapes in `text`.\"\"\"
    digits = "0123456789ABCDEF"
    decoded = []
    index = 0
    while index < len(text):
        letter = text[index]
        if letter != "%":
            decoded.append(letter)
            index += 1
            continue
        code = text[index + 1 : index + 3]
        if len(code) == 2 and all(digit in digits for digit in code):
            decoded.append(chr(int(code, 16)))
            index += 3
        else:
            decoded.append(letter)
            index += 1
    return "".join(decoded)""",
    variant_four="""def decode_percent(text):
    \"\"\"Decode the percent escapes in `text`.\"\"\"
    digits = "0123456789abcdefABCDEF"
    decoded = []
    index = 0
    while index < len(text):
        letter = text[index]
        if letter != "%":
            decoded.append(letter)
            index += 1
            continue
        code = text[index + 1 : index + 3]
        if len(code) == 2 and all(digit in digits for digit in code):
            decoded.append(chr(int(code, 16)))
            index += 3
        else:
            raise ValueError("a percent sign must be followed by two hex digits")
    return "".join(decoded)""",
    visible_test=_test_module(
        "percent_escapes",
        "Published contract for decoding percent escapes.",
        """
def test_a_space() -> None:
    assert decode_percent("a%20b") == "a b"


def test_a_percent_sign_of_its_own() -> None:
    assert decode_percent("100%25") == "100%"


def test_a_string_with_nothing_to_decode() -> None:
    assert decode_percent("plain") == "plain"
""",
        imports="from percent_escapes import decode_percent\n",
    ),
    hidden_test=_test_module(
        "percent_escapes",
        "The part of the contract the published tests do not state.",
        """
def test_a_space() -> None:
    assert decode_percent("a%20b") == "a b"


def test_a_percent_sign_that_is_not_an_escape_is_left_as_written() -> None:
    assert decode_percent("50% off") == "50% off"
    assert decode_percent("a%zzb") == "a%zzb"


def test_hex_digits_written_in_lowercase_are_decoded_too() -> None:
    assert decode_percent("a%2fb") == "a/b"
""",
        imports="from percent_escapes import decode_percent\n",
    ),
)

_G067 = D2TaskSpec(
    template_id="d4_parsing.version_constraint",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-version-constraint",
    module="constraint_syntax",
    module_doc="Reading a version constraint as an operator and a version.",
    issue=(
        "parse_constraint() is documented to read a version constraint as an operator and a "
        "version. Callers report that a bare version comes back with no operator at all, and "
        "that a constraint written with a two-character operator comes back with the first "
        "character as the operator and the second stuck to the front of the version."
    ),
    expected=(
        "parse_constraint(text) returns (operator, version); a bare version means equality, and "
        "a two-character operator is read whole rather than one character at a time."
    ),
    baseline_reason="it tries the one-character operators first and settles for no operator at all",
    edge_cases=(
        "a bare version means equality",
        "a two-character operator is read whole",
    ),
    baseline="""def parse_constraint(text):
    \"\"\"Split a version constraint into its operator and its version.\"\"\"
    trimmed = text.strip()
    for operator in ("<", ">", "=="):
        if trimmed.startswith(operator):
            return operator, trimmed[len(operator) :].strip()
    return "", trimmed""",
    variant_one="""def parse_constraint(text):
    \"\"\"Split a version constraint into its operator and its version.\"\"\"
    trimmed = text.strip()
    for operator in (">=", "<=", "==", ">", "<"):
        if trimmed.startswith(operator):
            return operator, trimmed[len(operator) :].strip()
    return "==", trimmed""",
    variant_two="""def parse_constraint(text):
    \"\"\"Split a version constraint into its operator and its version.\"\"\"
    trimmed = text.strip()
    cut = 0
    while cut < len(trimmed) and trimmed[cut] in "<>=":
        cut += 1
    return trimmed[:cut] or "==", trimmed[cut:].strip()""",
    variant_three="""def parse_constraint(text):
    \"\"\"Split a version constraint into its operator and its version.\"\"\"
    trimmed = text.strip()
    for operator in ("<", ">", "=="):
        if trimmed.startswith(operator):
            return operator, trimmed[len(operator) :].strip()
    return "==", trimmed""",
    variant_four="""def parse_constraint(text):
    \"\"\"Split a version constraint into its operator and its version.\"\"\"
    trimmed = text.strip()
    for operator in (">=", "<=", "==", ">", "<"):
        if trimmed.startswith(operator):
            return operator, trimmed[len(operator) :].strip()
    return "", trimmed""",
    visible_test=_test_module(
        "constraint_syntax",
        "Published contract for reading a version constraint.",
        """
def test_greater_than() -> None:
    assert parse_constraint(">1.2") == (">", "1.2")


def test_equal_to() -> None:
    assert parse_constraint("==2.0") == ("==", "2.0")


def test_less_than_with_room_around_it() -> None:
    assert parse_constraint(" < 3 ") == ("<", "3")
""",
        imports="from constraint_syntax import parse_constraint\n",
    ),
    hidden_test=_test_module(
        "constraint_syntax",
        "The part of the contract the published tests do not state.",
        """
def test_greater_than() -> None:
    assert parse_constraint(">1.2") == (">", "1.2")


def test_a_bare_version_means_equality() -> None:
    assert parse_constraint("1.2.3") == ("==", "1.2.3")


def test_a_two_character_operator_is_read_whole() -> None:
    assert parse_constraint(">=1.2") == (">=", "1.2")
    assert parse_constraint("<=4") == ("<=", "4")
""",
        imports="from constraint_syntax import parse_constraint\n",
    ),
)

_G068 = D2TaskSpec(
    template_id="d4_parsing.strip_quotes",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-strip-quotes",
    module="quote_stripping",
    module_doc="Taking the surrounding quotes off a quoted value.",
    issue=(
        "strip_quotes() is documented to take one matching pair of surrounding quotes off a "
        "value. Callers report that a value opening with one kind of quote and closing with the "
        "other is stripped anyway, and that a value that is nothing but a single quote "
        "character comes back empty."
    ),
    expected=(
        "strip_quotes(text) removes the outer pair only when the value opens and closes with the "
        "same quote character and is long enough to hold a pair; anything else comes back "
        "exactly as it was."
    ),
    baseline_reason=(
        "it checks that each end is a quote without checking that they are the same one"
    ),
    edge_cases=(
        "ends that do not match are left alone",
        "a lone quote character is not a pair",
    ),
    baseline="""def strip_quotes(text):
    \"\"\"Remove one matching pair of surrounding quotes from `text`.\"\"\"
    if text[:1] in ("'", '"') and text[-1:] in ("'", '"'):
        return text[1:-1]
    return text""",
    variant_one="""def strip_quotes(text):
    \"\"\"Remove one matching pair of surrounding quotes from `text`.\"\"\"
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text""",
    variant_two="""def strip_quotes(text):
    \"\"\"Remove one matching pair of surrounding quotes from `text`.\"\"\"
    for quote in ("'", '"'):
        if len(text) > 1 and text.startswith(quote) and text.endswith(quote):
            return text[1:-1]
    return text""",
    variant_three="""def strip_quotes(text):
    \"\"\"Remove one matching pair of surrounding quotes from `text`.\"\"\"
    if text[:1] in ("'", '"') and text[:1] == text[-1:]:
        return text[1:-1]
    return text""",
    variant_four="""def strip_quotes(text):
    \"\"\"Remove one matching pair of surrounding quotes from `text`.\"\"\"
    if len(text) >= 2 and text[0] in ("'", '"') and text[-1] in ("'", '"'):
        return text[1:-1]
    return text""",
    visible_test=_test_module(
        "quote_stripping",
        "Published contract for taking the quotes off a value.",
        """
def test_double_quotes() -> None:
    assert strip_quotes('"abc"') == "abc"


def test_single_quotes() -> None:
    assert strip_quotes("'abc'") == "abc"


def test_a_value_with_no_quotes_at_all() -> None:
    assert strip_quotes("abc") == "abc"
""",
        imports="from quote_stripping import strip_quotes\n",
    ),
    hidden_test=_test_module(
        "quote_stripping",
        "The part of the contract the published tests do not state.",
        """
def test_double_quotes() -> None:
    assert strip_quotes('"abc"') == "abc"


def test_ends_that_do_not_match_are_left_alone() -> None:
    mixed = '"abc' + "'"
    assert strip_quotes(mixed) == mixed


def test_a_lone_quote_character_is_not_a_pair() -> None:
    assert strip_quotes('"') == '"'
    assert strip_quotes("'") == "'"
""",
        imports="from quote_stripping import strip_quotes\n",
    ),
)

_G069 = D2TaskSpec(
    template_id="d4_parsing.split_top_level",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-split-top-level",
    module="depth_split",
    module_doc="Splitting an argument list at its top-level separators.",
    issue=(
        "split_top_level() is documented to split a list at the commas that are not inside "
        "brackets. Callers report that a call nested inside another call is split in the middle, "
        "and that a list with a bracket left open comes back split rather than refused."
    ),
    expected=(
        "split_top_level(text) returns the trimmed pieces between the commas that stand outside "
        "every bracket, counts nested brackets properly, and raises ValueError when the brackets "
        "do not balance."
    ),
    baseline_reason=(
        "it remembers only whether it is inside brackets, not how deep, and never checks the "
        "brackets balance"
    ),
    edge_cases=(
        "a comma inside a nested bracket does not split",
        "a bracket left open is refused",
    ),
    baseline="""def split_top_level(text):
    \"\"\"Split `text` at the commas that stand outside every bracket.\"\"\"
    pieces = []
    current = ""
    inside = False
    for letter in text:
        if letter == "(":
            inside = True
        elif letter == ")":
            inside = False
        if letter == "," and not inside:
            pieces.append(current.strip())
            current = ""
        else:
            current += letter
    pieces.append(current.strip())
    return pieces""",
    variant_one="""def split_top_level(text):
    \"\"\"Split `text` at the commas that stand outside every bracket.\"\"\"
    pieces = []
    current = ""
    depth = 0
    for letter in text:
        if letter == "(":
            depth += 1
        elif letter == ")":
            depth -= 1
            if depth < 0:
                raise ValueError("a bracket closes that never opened")
        if letter == "," and depth == 0:
            pieces.append(current.strip())
            current = ""
        else:
            current += letter
    if depth != 0:
        raise ValueError("a bracket opens that never closes")
    pieces.append(current.strip())
    return pieces""",
    variant_two="""def split_top_level(text):
    \"\"\"Split `text` at the commas that stand outside every bracket.\"\"\"
    pieces = []
    current = ""
    index = 0
    while index < len(text):
        letter = text[index]
        if letter == "(":
            depth = 0
            opened = index
            while index < len(text):
                if text[index] == "(":
                    depth += 1
                elif text[index] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                index += 1
            if depth != 0:
                raise ValueError("a bracket opens that never closes")
            current += text[opened : index + 1]
        elif letter == ")":
            raise ValueError("a bracket closes that never opened")
        elif letter == ",":
            pieces.append(current.strip())
            current = ""
        else:
            current += letter
        index += 1
    pieces.append(current.strip())
    return pieces""",
    variant_three="""def split_top_level(text):
    \"\"\"Split `text` at the commas that stand outside every bracket.\"\"\"
    pieces = []
    current = ""
    depth = 0
    for letter in text:
        if letter == "(":
            depth += 1
        elif letter == ")":
            depth -= 1
        if letter == "," and depth == 0:
            pieces.append(current.strip())
            current = ""
        else:
            current += letter
    pieces.append(current.strip())
    return pieces""",
    variant_four="""def split_top_level(text):
    \"\"\"Split `text` at the commas that stand outside every bracket.\"\"\"
    if text.count("(") != text.count(")"):
        raise ValueError("the brackets do not balance")
    pieces = []
    current = ""
    inside = False
    for letter in text:
        if letter == "(":
            inside = True
        elif letter == ")":
            inside = False
        if letter == "," and not inside:
            pieces.append(current.strip())
            current = ""
        else:
            current += letter
    pieces.append(current.strip())
    return pieces""",
    visible_test=_test_module(
        "depth_split",
        "Published contract for splitting at top-level separators.",
        """
def test_a_plain_list() -> None:
    assert split_top_level("a, b, c") == ["a", "b", "c"]


def test_a_comma_inside_one_bracket_does_not_split() -> None:
    assert split_top_level("a, f(x, y), b") == ["a", "f(x, y)", "b"]


def test_a_single_item() -> None:
    assert split_top_level("only") == ["only"]
""",
        imports="from depth_split import split_top_level\n",
    ),
    hidden_test=_test_module(
        "depth_split",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_plain_list() -> None:
    assert split_top_level("a, b, c") == ["a", "b", "c"]


def test_a_comma_inside_a_nested_bracket_does_not_split() -> None:
    assert split_top_level("f(g(a,b),c)") == ["f(g(a,b),c)"]


def test_a_bracket_left_open_is_refused() -> None:
    with pytest.raises(ValueError):
        split_top_level("a, f(x")
""",
        imports="from depth_split import split_top_level\n",
    ),
)

_G070 = D2TaskSpec(
    template_id="d4_parsing.parse_ordinal",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-ordinal",
    module="ordinal_number",
    module_doc="Reading the number written as an ordinal.",
    issue=(
        "parse_ordinal() is documented to read the number written as an ordinal. Callers report "
        "that the eleventh, twelfth and thirteenth are refused outright, and that an ordinal "
        "with a space around it is refused as well."
    ),
    expected=(
        "parse_ordinal(text) returns the number, ignores the room around it, refuses a suffix "
        "that does not fit the number, and knows that eleven, twelve and thirteen take th "
        "whatever their last digit is."
    ),
    baseline_reason=(
        "it picks the suffix from the last digit alone and reads the text exactly as given"
    ),
    edge_cases=(
        "eleven, twelve and thirteen take th",
        "room around the ordinal is ignored",
    ),
    baseline="""def parse_ordinal(text):
    \"\"\"Return the number written as an ordinal in `text`.\"\"\"
    number = int(text[:-2])
    wanted = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if text[-2:] != wanted:
        raise ValueError("the suffix does not fit the number")
    return number""",
    variant_one="""def parse_ordinal(text):
    \"\"\"Return the number written as an ordinal in `text`.\"\"\"
    trimmed = text.strip()
    number = int(trimmed[:-2])
    if number % 100 in (11, 12, 13):
        wanted = "th"
    else:
        wanted = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if trimmed[-2:] != wanted:
        raise ValueError("the suffix does not fit the number")
    return number""",
    variant_two="""def parse_ordinal(text):
    \"\"\"Return the number written as an ordinal in `text`.\"\"\"
    trimmed = text.strip()
    number = int(trimmed[:-2])
    wanted = "th"
    if number % 100 not in (11, 12, 13):
        for suffix, last in (("st", 1), ("nd", 2), ("rd", 3)):
            if number % 10 == last:
                wanted = suffix
                break
    if trimmed[-2:] != wanted:
        raise ValueError("the suffix does not fit the number")
    return number""",
    variant_three="""def parse_ordinal(text):
    \"\"\"Return the number written as an ordinal in `text`.\"\"\"
    number = int(text[:-2])
    if number % 100 in (11, 12, 13):
        wanted = "th"
    else:
        wanted = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if text[-2:] != wanted:
        raise ValueError("the suffix does not fit the number")
    return number""",
    variant_four="""def parse_ordinal(text):
    \"\"\"Return the number written as an ordinal in `text`.\"\"\"
    trimmed = text.strip()
    number = int(trimmed[:-2])
    wanted = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    if trimmed[-2:] != wanted:
        raise ValueError("the suffix does not fit the number")
    return number""",
    visible_test=_test_module(
        "ordinal_number",
        "Published contract for reading an ordinal.",
        """
import pytest


def test_the_first() -> None:
    assert parse_ordinal("1st") == 1


def test_the_twenty_second() -> None:
    assert parse_ordinal("22nd") == 22


def test_a_suffix_that_does_not_fit_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_ordinal("4st")
""",
        imports="from ordinal_number import parse_ordinal\n",
    ),
    hidden_test=_test_module(
        "ordinal_number",
        "The part of the contract the published tests do not state.",
        """
def test_the_first() -> None:
    assert parse_ordinal("1st") == 1


def test_eleven_twelve_and_thirteen_take_th() -> None:
    assert parse_ordinal("11th") == 11
    assert parse_ordinal("113th") == 113


def test_room_around_the_ordinal_is_ignored() -> None:
    assert parse_ordinal(" 2nd ") == 2
""",
        imports="from ordinal_number import parse_ordinal\n",
    ),
)

# ------------------------------------------------------------------------- state and idempotency

_G071 = D2TaskSpec(
    template_id="d4_state.rotate_key",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-rotate-key",
    module="credential_rotation",
    module_doc="Rotating the active signing key of a store.",
    issue=(
        "rotate_key() is documented to make a key active and keep the one it replaced. Callers "
        "report that rotating to the key that is already active records a rotation that never "
        "happened, and that the retired list grows without end instead of holding the one key "
        "just replaced."
    ),
    expected=(
        "rotate_key(store, key, at) returns the store with `key` active, the key it replaced as "
        "the only retired one and the rotation stamped at `at`; rotating to the key already "
        "active returns the store exactly as it was."
    ),
    baseline_reason=(
        "it appends to whatever was retired before and never asks whether the key changed"
    ),
    edge_cases=(
        "rotating to the key already active changes nothing",
        "only the key just replaced stays retired",
    ),
    baseline="""def rotate_key(store, key, at):
    \"\"\"Return `store` with `key` made active.\"\"\"
    rotated = dict(store)
    rotated["retired"] = [*store.get("retired", []), store["active"]]
    rotated["active"] = key
    rotated["rotated_at"] = at
    return rotated""",
    variant_one="""def rotate_key(store, key, at):
    \"\"\"Return `store` with `key` made active.\"\"\"
    if store["active"] == key:
        return dict(store)
    rotated = dict(store)
    rotated["retired"] = [store["active"]]
    rotated["active"] = key
    rotated["rotated_at"] = at
    return rotated""",
    variant_two="""def rotate_key(store, key, at):
    \"\"\"Return `store` with `key` made active.\"\"\"
    if store["active"] == key:
        return {name: value for name, value in store.items()}
    replaced = store["active"]
    fresh = {name: value for name, value in store.items() if name != "retired"}
    fresh["retired"] = [replaced]
    fresh["active"] = key
    fresh["rotated_at"] = at
    return fresh""",
    variant_three="""def rotate_key(store, key, at):
    \"\"\"Return `store` with `key` made active.\"\"\"
    if store["active"] == key:
        return dict(store)
    rotated = dict(store)
    rotated["retired"] = [*store.get("retired", []), store["active"]]
    rotated["active"] = key
    rotated["rotated_at"] = at
    return rotated""",
    variant_four="""def rotate_key(store, key, at):
    \"\"\"Return `store` with `key` made active.\"\"\"
    rotated = dict(store)
    rotated["retired"] = [store["active"]]
    rotated["active"] = key
    rotated["rotated_at"] = at
    return rotated""",
    visible_test=_test_module(
        "credential_rotation",
        "Published contract for rotating a signing key.",
        """
def test_a_first_rotation() -> None:
    store = {"active": "k1", "rotated_at": 0}
    assert rotate_key(store, "k2", 5) == {
        "active": "k2",
        "retired": ["k1"],
        "rotated_at": 5,
    }


def test_the_caller_store_is_not_changed() -> None:
    store = {"active": "k1", "rotated_at": 0}
    rotate_key(store, "k2", 5)
    assert store == {"active": "k1", "rotated_at": 0}


def test_other_settings_are_carried_over() -> None:
    store = {"active": "k1", "rotated_at": 0, "owner": "billing"}
    assert rotate_key(store, "k2", 5)["owner"] == "billing"
""",
        imports="from credential_rotation import rotate_key\n",
    ),
    hidden_test=_test_module(
        "credential_rotation",
        "The part of the contract the published tests do not state.",
        """
def test_a_first_rotation() -> None:
    store = {"active": "k1", "rotated_at": 0}
    assert rotate_key(store, "k2", 5)["active"] == "k2"


def test_rotating_to_the_key_already_active_changes_nothing() -> None:
    store = {"active": "k1", "rotated_at": 0}
    assert rotate_key(store, "k1", 9) == store


def test_only_the_key_just_replaced_stays_retired() -> None:
    once = rotate_key({"active": "k1", "rotated_at": 0}, "k2", 5)
    twice = rotate_key(once, "k3", 6)
    assert twice["retired"] == ["k2"]
""",
        imports="from credential_rotation import rotate_key\n",
    ),
)

_G072 = D2TaskSpec(
    template_id="d4_state.rename_stage",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-rename-stage",
    module="stage_rename",
    module_doc="Renaming a stage of a pipeline without disturbing the order.",
    issue=(
        "rename_stage() is documented to rename a stage of a pipeline. Callers report that a "
        "renamed stage is moved to the end of the pipeline instead of staying where it was, and "
        "that renaming a stage to the name it already has is refused as a clash with itself."
    ),
    expected=(
        "rename_stage(pipeline, old, new) returns the pipeline with the stage renamed in place, "
        "returns it unchanged when the two names are the same, and raises ValueError for a stage "
        "that is not there or a name another stage already holds."
    ),
    baseline_reason="it drops the stage and puts it back, which puts it back at the end",
    edge_cases=(
        "the renamed stage keeps its place in the order",
        "renaming a stage to the name it already has changes nothing",
    ),
    baseline="""def rename_stage(pipeline, old, new):
    \"\"\"Return `pipeline` with the stage `old` renamed to `new`.\"\"\"
    if old not in pipeline:
        raise ValueError("no such stage")
    if new in pipeline:
        raise ValueError("that name is taken")
    renamed = {name: settings for name, settings in pipeline.items() if name != old}
    renamed[new] = pipeline[old]
    return renamed""",
    variant_one="""def rename_stage(pipeline, old, new):
    \"\"\"Return `pipeline` with the stage `old` renamed to `new`.\"\"\"
    if old not in pipeline:
        raise ValueError("no such stage")
    if old == new:
        return dict(pipeline)
    if new in pipeline:
        raise ValueError("that name is taken")
    return {(new if name == old else name): settings for name, settings in pipeline.items()}""",
    variant_two="""def rename_stage(pipeline, old, new):
    \"\"\"Return `pipeline` with the stage `old` renamed to `new`.\"\"\"
    if old not in pipeline:
        raise ValueError("no such stage")
    if old == new:
        return dict(pipeline)
    if new in pipeline:
        raise ValueError("that name is taken")
    names = list(pipeline)
    names[names.index(old)] = new
    settings = dict(pipeline)
    settings[new] = settings.pop(old)
    return {name: settings[name] for name in names}""",
    variant_three="""def rename_stage(pipeline, old, new):
    \"\"\"Return `pipeline` with the stage `old` renamed to `new`.\"\"\"
    if old not in pipeline:
        raise ValueError("no such stage")
    if new in pipeline:
        raise ValueError("that name is taken")
    return {(new if name == old else name): settings for name, settings in pipeline.items()}""",
    variant_four="""def rename_stage(pipeline, old, new):
    \"\"\"Return `pipeline` with the stage `old` renamed to `new`.\"\"\"
    if old not in pipeline:
        raise ValueError("no such stage")
    if old == new:
        return dict(pipeline)
    if new in pipeline:
        raise ValueError("that name is taken")
    renamed = {name: settings for name, settings in pipeline.items() if name != old}
    renamed[new] = pipeline[old]
    return renamed""",
    visible_test=_test_module(
        "stage_rename",
        "Published contract for renaming a pipeline stage.",
        """
import pytest


def test_renaming_the_last_stage() -> None:
    assert rename_stage({"fetch": 1, "load": 2}, "load", "store") == {"fetch": 1, "store": 2}


def test_a_stage_that_is_not_there() -> None:
    with pytest.raises(ValueError):
        rename_stage({"fetch": 1}, "load", "store")


def test_a_name_another_stage_already_holds() -> None:
    with pytest.raises(ValueError):
        rename_stage({"fetch": 1, "load": 2}, "fetch", "load")
""",
        imports="from stage_rename import rename_stage\n",
    ),
    hidden_test=_test_module(
        "stage_rename",
        "The part of the contract the published tests do not state.",
        """
def test_renaming_the_last_stage() -> None:
    assert rename_stage({"fetch": 1, "load": 2}, "load", "store") == {"fetch": 1, "store": 2}


def test_the_renamed_stage_keeps_its_place_in_the_order() -> None:
    renamed = rename_stage({"fetch": 1, "clean": 2, "load": 3}, "fetch", "collect")
    assert list(renamed) == ["collect", "clean", "load"]


def test_renaming_a_stage_to_the_name_it_already_has_changes_nothing() -> None:
    assert rename_stage({"fetch": 1, "load": 2}, "load", "load") == {"fetch": 1, "load": 2}
""",
        imports="from stage_rename import rename_stage\n",
    ),
)

_G073 = D2TaskSpec(
    template_id="d4_state.enrol_member",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-enrol-member",
    module="enrolment",
    module_doc="Enrolling a member in a group that has a waiting list.",
    issue=(
        "enrol() is documented to enrol a member in a group, or to put them on the waiting list "
        "when the group is full. Callers report that a member already waiting is enrolled a "
        "second time, and that a full group takes the member anyway instead of putting them on "
        "the list."
    ),
    expected=(
        "enrol(group, member) returns the group with the member enrolled while there is room, "
        "on the waiting list once there is not, and unchanged when the member is already "
        "enrolled or already waiting."
    ),
    baseline_reason="it looks only at the members and never at the waiting list or the capacity",
    edge_cases=(
        "a member already waiting is not enrolled as well",
        "a full group puts the member on the waiting list",
    ),
    baseline="""def enrol(group, member):
    \"\"\"Return `group` with `member` enrolled, or waiting if there is no room.\"\"\"
    if member in group["members"]:
        return dict(group)
    joined = dict(group)
    joined["members"] = [*group["members"], member]
    return joined""",
    variant_one="""def enrol(group, member):
    \"\"\"Return `group` with `member` enrolled, or waiting if there is no room.\"\"\"
    if member in group["members"] or member in group["waiting"]:
        return dict(group)
    joined = dict(group)
    if len(group["members"]) < group["capacity"]:
        joined["members"] = [*group["members"], member]
    else:
        joined["waiting"] = [*group["waiting"], member]
    return joined""",
    variant_two="""def enrol(group, member):
    \"\"\"Return `group` with `member` enrolled, or waiting if there is no room.\"\"\"
    members = list(group["members"])
    waiting = list(group["waiting"])
    if member not in members and member not in waiting:
        if len(members) < group["capacity"]:
            members.append(member)
        else:
            waiting.append(member)
    return {**group, "members": members, "waiting": waiting}""",
    variant_three="""def enrol(group, member):
    \"\"\"Return `group` with `member` enrolled, or waiting if there is no room.\"\"\"
    if member in group["members"] or member in group["waiting"]:
        return dict(group)
    joined = dict(group)
    joined["members"] = [*group["members"], member]
    return joined""",
    variant_four="""def enrol(group, member):
    \"\"\"Return `group` with `member` enrolled, or waiting if there is no room.\"\"\"
    if member in group["members"]:
        return dict(group)
    joined = dict(group)
    if len(group["members"]) < group["capacity"]:
        joined["members"] = [*group["members"], member]
    else:
        joined["waiting"] = [*group["waiting"], member]
    return joined""",
    visible_test=_test_module(
        "enrolment",
        "Published contract for enrolling a member.",
        """
def test_a_group_with_room() -> None:
    group = {"members": ["ada"], "waiting": [], "capacity": 3}
    assert enrol(group, "bo")["members"] == ["ada", "bo"]


def test_a_member_already_enrolled_is_not_enrolled_twice() -> None:
    group = {"members": ["ada"], "waiting": [], "capacity": 3}
    assert enrol(group, "ada") == group


def test_the_caller_group_is_not_changed() -> None:
    group = {"members": ["ada"], "waiting": [], "capacity": 3}
    enrol(group, "bo")
    assert group["members"] == ["ada"]
""",
        imports="from enrolment import enrol\n",
    ),
    hidden_test=_test_module(
        "enrolment",
        "The part of the contract the published tests do not state.",
        """
def test_a_group_with_room() -> None:
    group = {"members": ["ada"], "waiting": [], "capacity": 3}
    assert enrol(group, "bo")["members"] == ["ada", "bo"]


def test_a_member_already_waiting_is_not_enrolled_as_well() -> None:
    group = {"members": ["ada"], "waiting": ["bo"], "capacity": 3}
    assert enrol(group, "bo") == group


def test_a_full_group_puts_the_member_on_the_waiting_list() -> None:
    group = {"members": ["ada", "bo"], "waiting": [], "capacity": 2}
    joined = enrol(group, "cy")
    assert joined["members"] == ["ada", "bo"]
    assert joined["waiting"] == ["cy"]
""",
        imports="from enrolment import enrol\n",
    ),
)

_G074 = D2TaskSpec(
    template_id="d4_state.record_heartbeat",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-record-heartbeat",
    module="heartbeat_log",
    module_doc="Keeping the latest heartbeat seen from each node.",
    issue=(
        "record_heartbeat() is documented to keep the latest heartbeat seen from each node. "
        "Callers report that a heartbeat that arrives late, stamped earlier than the one already "
        "recorded, overwrites it, and that the first heartbeat from a new node brings the call "
        "down."
    ),
    expected=(
        "record_heartbeat(nodes, name, at) returns the log with the node's stamp moved forward "
        "to `at`, leaves it alone when `at` is no later than the stamp already there, and "
        "records a node it has not seen before."
    ),
    baseline_reason=(
        "it compares the two stamps for difference rather than for order, and assumes "
        "the node is known"
    ),
    edge_cases=(
        "a heartbeat stamped earlier than the one recorded is ignored",
        "a node not seen before is recorded",
    ),
    baseline="""def record_heartbeat(nodes, name, at):
    \"\"\"Return `nodes` with `name` beating at `at`.\"\"\"
    seen = dict(nodes)
    if at != seen[name]:
        seen[name] = at
    return seen""",
    variant_one="""def record_heartbeat(nodes, name, at):
    \"\"\"Return `nodes` with `name` beating at `at`.\"\"\"
    seen = dict(nodes)
    if name not in seen or at > seen[name]:
        seen[name] = at
    return seen""",
    variant_two="""def record_heartbeat(nodes, name, at):
    \"\"\"Return `nodes` with `name` beating at `at`.\"\"\"
    latest = max(at, nodes[name]) if name in nodes else at
    return {**nodes, name: latest}""",
    variant_three="""def record_heartbeat(nodes, name, at):
    \"\"\"Return `nodes` with `name` beating at `at`.\"\"\"
    seen = dict(nodes)
    if at > seen[name]:
        seen[name] = at
    return seen""",
    variant_four="""def record_heartbeat(nodes, name, at):
    \"\"\"Return `nodes` with `name` beating at `at`.\"\"\"
    seen = dict(nodes)
    if name not in seen or at != seen[name]:
        seen[name] = at
    return seen""",
    visible_test=_test_module(
        "heartbeat_log",
        "Published contract for recording a heartbeat.",
        """
def test_a_later_heartbeat_moves_the_stamp_forward() -> None:
    assert record_heartbeat({"alpha": 10}, "alpha", 20) == {"alpha": 20}


def test_the_same_stamp_again_changes_nothing() -> None:
    assert record_heartbeat({"alpha": 10}, "alpha", 10) == {"alpha": 10}


def test_the_other_nodes_are_left_alone() -> None:
    assert record_heartbeat({"alpha": 10, "beta": 3}, "alpha", 20) == {"alpha": 20, "beta": 3}
""",
        imports="from heartbeat_log import record_heartbeat\n",
    ),
    hidden_test=_test_module(
        "heartbeat_log",
        "The part of the contract the published tests do not state.",
        """
def test_a_later_heartbeat_moves_the_stamp_forward() -> None:
    assert record_heartbeat({"alpha": 10}, "alpha", 20) == {"alpha": 20}


def test_a_heartbeat_stamped_earlier_than_the_one_recorded_is_ignored() -> None:
    assert record_heartbeat({"alpha": 20}, "alpha", 10) == {"alpha": 20}


def test_a_node_not_seen_before_is_recorded() -> None:
    assert record_heartbeat({"alpha": 20}, "beta", 5) == {"alpha": 20, "beta": 5}
""",
        imports="from heartbeat_log import record_heartbeat\n",
    ),
)

_G075 = D2TaskSpec(
    template_id="d4_state.undo_last",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-undo-last",
    module="undo_stack",
    module_doc="Undoing the last action of an editing history.",
    issue=(
        "undo_last() is documented to undo the last action of a history. Callers report that "
        "undoing a history with nothing done brings the call down instead of reporting that "
        "there was nothing to undo, and that redoing after two undos replays them the wrong way "
        "round."
    ),
    expected=(
        "undo_last(history) returns (history, action) with the last done action moved to the "
        "front of the undone list, and returns the history unchanged with no action at all when "
        "nothing has been done."
    ),
    baseline_reason=(
        "it pops the last action without looking first and files it at the back of the undone list"
    ),
    edge_cases=(
        "undoing nothing reports no action rather than raising",
        "the undone action goes to the front of the list",
    ),
    baseline="""def undo_last(history):
    \"\"\"Return `history` with its last action undone, and the action itself.\"\"\"
    done = list(history["done"])
    action = done.pop()
    return {"done": done, "undone": [*history["undone"], action]}, action""",
    variant_one="""def undo_last(history):
    \"\"\"Return `history` with its last action undone, and the action itself.\"\"\"
    done = list(history["done"])
    if not done:
        return {"done": done, "undone": list(history["undone"])}, None
    action = done.pop()
    return {"done": done, "undone": [action, *history["undone"]]}, action""",
    variant_two="""def undo_last(history):
    \"\"\"Return `history` with its last action undone, and the action itself.\"\"\"
    done = history["done"]
    undone = list(history["undone"])
    if not done:
        return {"done": list(done), "undone": undone}, None
    action = done[-1]
    return {"done": list(done[:-1]), "undone": [action] + undone}, action""",
    variant_three="""def undo_last(history):
    \"\"\"Return `history` with its last action undone, and the action itself.\"\"\"
    done = list(history["done"])
    if not done:
        return {"done": done, "undone": list(history["undone"])}, None
    action = done.pop()
    return {"done": done, "undone": [*history["undone"], action]}, action""",
    variant_four="""def undo_last(history):
    \"\"\"Return `history` with its last action undone, and the action itself.\"\"\"
    done = list(history["done"])
    action = done.pop()
    return {"done": done, "undone": [action, *history["undone"]]}, action""",
    visible_test=_test_module(
        "undo_stack",
        "Published contract for undoing the last action.",
        """
def test_the_last_action_comes_off() -> None:
    history, action = undo_last({"done": ["type", "bold"], "undone": []})
    assert action == "bold"
    assert history == {"done": ["type"], "undone": ["bold"]}


def test_the_caller_history_is_not_changed() -> None:
    history = {"done": ["type"], "undone": []}
    undo_last(history)
    assert history == {"done": ["type"], "undone": []}


def test_a_single_action() -> None:
    assert undo_last({"done": ["type"], "undone": []}) == ({"done": [], "undone": ["type"]}, "type")
""",
        imports="from undo_stack import undo_last\n",
    ),
    hidden_test=_test_module(
        "undo_stack",
        "The part of the contract the published tests do not state.",
        """
def test_the_last_action_comes_off() -> None:
    history, action = undo_last({"done": ["type", "bold"], "undone": []})
    assert action == "bold"


def test_undoing_nothing_reports_no_action() -> None:
    history, action = undo_last({"done": [], "undone": []})
    assert action is None
    assert history == {"done": [], "undone": []}


def test_the_undone_action_goes_to_the_front_of_the_list() -> None:
    history, _ = undo_last({"done": ["type"], "undone": ["bold"]})
    assert history["undone"] == ["type", "bold"]
""",
        imports="from undo_stack import undo_last\n",
    ),
)

# ------------------------------------------------------------------------------- numeric logic

_G076 = D2TaskSpec(
    template_id="d4_numeric.make_change",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-make-change",
    module="coin_change",
    module_doc="Making an amount up out of the coins available.",
    issue=(
        "make_change() is documented to make an amount up out of the coins available, spending "
        "the largest coins first. Callers report that handing the coins over in any order but "
        "largest-first returns a fistful of small change, and that an amount the coins cannot "
        "make exactly comes back short without a word."
    ),
    expected=(
        "make_change(amount, coins) returns how many of each coin makes the amount, spending the "
        "largest coins first whatever order they arrive in, and raises ValueError when the coins "
        "cannot make the amount exactly."
    ),
    baseline_reason="it spends the coins in the order handed over and never checks what is left",
    edge_cases=(
        "the coins are spent largest first whatever order they arrive in",
        "an amount the coins cannot make exactly is refused",
    ),
    baseline="""def make_change(amount, coins):
    \"\"\"Return how many of each coin makes `amount`, largest coins first.\"\"\"
    counts = {}
    left = amount
    for coin in coins:
        if left >= coin:
            counts[coin] = left // coin
            left -= counts[coin] * coin
    return counts""",
    variant_one="""def make_change(amount, coins):
    \"\"\"Return how many of each coin makes `amount`, largest coins first.\"\"\"
    counts = {}
    left = amount
    for coin in sorted(coins, reverse=True):
        if left >= coin:
            counts[coin] = left // coin
            left -= counts[coin] * coin
    if left:
        raise ValueError("those coins cannot make that amount exactly")
    return counts""",
    variant_two="""def make_change(amount, coins):
    \"\"\"Return how many of each coin makes `amount`, largest coins first.\"\"\"
    counts = {}
    left = amount
    for coin in sorted(coins, reverse=True):
        spent = 0
        while left >= coin:
            left -= coin
            spent += 1
        if spent:
            counts[coin] = spent
    if left != 0:
        raise ValueError("those coins cannot make that amount exactly")
    return counts""",
    variant_three="""def make_change(amount, coins):
    \"\"\"Return how many of each coin makes `amount`, largest coins first.\"\"\"
    counts = {}
    left = amount
    for coin in sorted(coins, reverse=True):
        if left >= coin:
            counts[coin] = left // coin
            left -= counts[coin] * coin
    return counts""",
    variant_four="""def make_change(amount, coins):
    \"\"\"Return how many of each coin makes `amount`, largest coins first.\"\"\"
    counts = {}
    left = amount
    for coin in coins:
        if left >= coin:
            counts[coin] = left // coin
            left -= counts[coin] * coin
    if left:
        raise ValueError("those coins cannot make that amount exactly")
    return counts""",
    visible_test=_test_module(
        "coin_change",
        "Published contract for making an amount out of coins.",
        """
def test_a_mixed_handful() -> None:
    assert make_change(87, (25, 10, 5, 1)) == {25: 3, 10: 1, 1: 2}


def test_an_amount_two_coins_make() -> None:
    assert make_change(30, (25, 10, 5, 1)) == {25: 1, 5: 1}


def test_no_amount_at_all_needs_no_coins() -> None:
    assert make_change(0, (25, 10, 5, 1)) == {}
""",
        imports="from coin_change import make_change\n",
    ),
    hidden_test=_test_module(
        "coin_change",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_mixed_handful() -> None:
    assert make_change(87, (25, 10, 5, 1)) == {25: 3, 10: 1, 1: 2}


def test_the_coins_are_spent_largest_first_whatever_order_they_arrive_in() -> None:
    assert make_change(30, (5, 25, 10, 1)) == {25: 1, 5: 1}


def test_an_amount_the_coins_cannot_make_exactly_is_refused() -> None:
    with pytest.raises(ValueError):
        make_change(3, (5, 2))
""",
        imports="from coin_change import make_change\n",
    ),
)

_G077 = D2TaskSpec(
    template_id="d4_numeric.turn_between",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-turn-between",
    module="compass_turn",
    module_doc="The shorter way round from one compass bearing to another.",
    issue=(
        "turn_between() is documented to report the shorter signed turn from one bearing to "
        "another. Callers report that a turn of exactly half a circle comes back as minus one "
        "hundred and eighty rather than plus, and that a bearing more than a whole circle away "
        "from the other comes back as a turn no one could make."
    ),
    expected=(
        "turn_between(start, finish) returns the shorter turn in degrees, positive clockwise, "
        "reports an exact half circle as plus one hundred and eighty, and brings bearings more "
        "than a whole circle apart into range before measuring."
    ),
    baseline_reason=(
        "it corrects a turn only once, in whichever direction it is too long, and calls half a "
        "circle too long"
    ),
    edge_cases=(
        "an exact half circle is reported as plus one hundred and eighty",
        "bearings more than a whole circle apart are brought into range first",
    ),
    baseline="""def turn_between(start, finish):
    \"\"\"Return the shorter signed turn in degrees from `start` to `finish`.\"\"\"
    difference = finish - start
    if difference >= 180:
        difference -= 360
    elif difference < -180:
        difference += 360
    return difference""",
    variant_one="""def turn_between(start, finish):
    \"\"\"Return the shorter signed turn in degrees from `start` to `finish`.\"\"\"
    difference = (finish - start) % 360
    if difference > 180:
        difference -= 360
    return difference""",
    variant_two="""def turn_between(start, finish):
    \"\"\"Return the shorter signed turn in degrees from `start` to `finish`.\"\"\"
    clockwise = (finish - start) % 360
    return clockwise if clockwise <= 180 else clockwise - 360""",
    variant_three="""def turn_between(start, finish):
    \"\"\"Return the shorter signed turn in degrees from `start` to `finish`.\"\"\"
    difference = finish - start
    if difference > 180:
        difference -= 360
    elif difference < -180:
        difference += 360
    return difference""",
    variant_four="""def turn_between(start, finish):
    \"\"\"Return the shorter signed turn in degrees from `start` to `finish`.\"\"\"
    difference = (finish - start) % 360
    if difference >= 180:
        difference -= 360
    return difference""",
    visible_test=_test_module(
        "compass_turn",
        "Published contract for the turn between two bearings.",
        """
def test_a_quarter_turn_clockwise() -> None:
    assert turn_between(0, 90) == 90


def test_a_quarter_turn_the_other_way() -> None:
    assert turn_between(90, 0) == -90


def test_a_turn_across_north() -> None:
    assert turn_between(350, 10) == 20
""",
        imports="from compass_turn import turn_between\n",
    ),
    hidden_test=_test_module(
        "compass_turn",
        "The part of the contract the published tests do not state.",
        """
def test_a_quarter_turn_clockwise() -> None:
    assert turn_between(0, 90) == 90


def test_an_exact_half_circle_is_reported_as_plus_one_hundred_and_eighty() -> None:
    assert turn_between(0, 180) == 180


def test_bearings_more_than_a_whole_circle_apart_are_brought_into_range() -> None:
    assert turn_between(0, 730) == 10
""",
        imports="from compass_turn import turn_between\n",
    ),
)

_G078 = D2TaskSpec(
    template_id="d4_numeric.compare_versions",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-compare-versions",
    module="version_order",
    module_doc="Ordering two dotted version numbers.",
    issue=(
        "compare_versions() is documented to order two dotted version numbers. Callers report "
        "that version one point ten sorts before version one point nine, and that a version "
        "written with fewer parts than the other is called equal to it whatever the extra parts "
        "hold."
    ),
    expected=(
        "compare_versions(left, right) returns -1, 0 or 1; each part is compared as a number "
        "rather than as text, and a part the shorter version does not write counts as zero."
    ),
    baseline_reason=(
        "it compares the parts as text and stops as soon as the shorter version runs out"
    ),
    edge_cases=(
        "a part is compared as a number, not as text",
        "a part the shorter version does not write counts as zero",
    ),
    baseline="""def compare_versions(left, right):
    \"\"\"Return -1, 0 or 1 as `left` sorts before, with, or after `right`.\"\"\"
    first = left.split(".")
    second = right.split(".")
    for one, other in zip(first, second):
        if one != other:
            return -1 if one < other else 1
    return 0""",
    variant_one="""def compare_versions(left, right):
    \"\"\"Return -1, 0 or 1 as `left` sorts before, with, or after `right`.\"\"\"
    first = [int(part) for part in left.split(".")]
    second = [int(part) for part in right.split(".")]
    while len(first) < len(second):
        first.append(0)
    while len(second) < len(first):
        second.append(0)
    for one, other in zip(first, second):
        if one != other:
            return -1 if one < other else 1
    return 0""",
    variant_two="""def compare_versions(left, right):
    \"\"\"Return -1, 0 or 1 as `left` sorts before, with, or after `right`.\"\"\"
    first = left.split(".")
    second = right.split(".")
    for index in range(max(len(first), len(second))):
        one = int(first[index]) if index < len(first) else 0
        other = int(second[index]) if index < len(second) else 0
        if one != other:
            return -1 if one < other else 1
    return 0""",
    variant_three="""def compare_versions(left, right):
    \"\"\"Return -1, 0 or 1 as `left` sorts before, with, or after `right`.\"\"\"
    first = [int(part) for part in left.split(".")]
    second = [int(part) for part in right.split(".")]
    for one, other in zip(first, second):
        if one != other:
            return -1 if one < other else 1
    return 0""",
    variant_four="""def compare_versions(left, right):
    \"\"\"Return -1, 0 or 1 as `left` sorts before, with, or after `right`.\"\"\"
    first = left.split(".")
    second = right.split(".")
    while len(first) < len(second):
        first.append("0")
    while len(second) < len(first):
        second.append("0")
    for one, other in zip(first, second):
        if one != other:
            return -1 if one < other else 1
    return 0""",
    visible_test=_test_module(
        "version_order",
        "Published contract for ordering two versions.",
        """
def test_an_earlier_version() -> None:
    assert compare_versions("1.2.0", "1.3.0") == -1


def test_a_later_version() -> None:
    assert compare_versions("2.0.0", "1.9.9") == 1


def test_the_same_version() -> None:
    assert compare_versions("1.2.3", "1.2.3") == 0
""",
        imports="from version_order import compare_versions\n",
    ),
    hidden_test=_test_module(
        "version_order",
        "The part of the contract the published tests do not state.",
        """
def test_an_earlier_version() -> None:
    assert compare_versions("1.2.0", "1.3.0") == -1


def test_a_part_is_compared_as_a_number_not_as_text() -> None:
    assert compare_versions("1.10", "1.9") == 1


def test_a_part_the_shorter_version_does_not_write_counts_as_zero() -> None:
    assert compare_versions("1.2", "1.2.0") == 0
    assert compare_versions("1.2", "1.2.1") == -1
""",
        imports="from version_order import compare_versions\n",
    ),
)

_G079 = D2TaskSpec(
    template_id="d4_numeric.average_speed",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-average-speed",
    module="journey_rate",
    module_doc="The average speed over a journey made of legs.",
    issue=(
        "average_speed() is documented to report the average speed over a whole journey. "
        "Callers report that a journey whose legs take different times comes back too fast, and "
        "that a leg recorded as taking no time at all brings the call down."
    ),
    expected=(
        "average_speed(legs) returns the total distance divided by the total time, which is not "
        "the mean of the leg speeds unless the legs take equally long, and raises ValueError for "
        "a leg that takes no time."
    ),
    baseline_reason="it works out each leg's speed and takes the mean of those",
    edge_cases=(
        "the average is over the totals, not the mean of the leg speeds",
        "a leg that takes no time is refused",
    ),
    baseline="""def average_speed(legs):
    \"\"\"Return the average speed over the whole journey.\"\"\"
    speeds = [distance / time for distance, time in legs]
    return sum(speeds) / len(speeds)""",
    variant_one="""def average_speed(legs):
    \"\"\"Return the average speed over the whole journey.\"\"\"
    total_distance = 0
    total_time = 0
    for distance, time in legs:
        if time <= 0:
            raise ValueError("a leg must take some time")
        total_distance += distance
        total_time += time
    return total_distance / total_time""",
    variant_two="""def average_speed(legs):
    \"\"\"Return the average speed over the whole journey.\"\"\"
    if any(time <= 0 for _, time in legs):
        raise ValueError("a leg must take some time")
    return sum(distance for distance, _ in legs) / sum(time for _, time in legs)""",
    variant_three="""def average_speed(legs):
    \"\"\"Return the average speed over the whole journey.\"\"\"
    total_distance = sum(distance for distance, _ in legs)
    total_time = sum(time for _, time in legs)
    return total_distance / total_time""",
    variant_four="""def average_speed(legs):
    \"\"\"Return the average speed over the whole journey.\"\"\"
    if any(time <= 0 for _, time in legs):
        raise ValueError("a leg must take some time")
    speeds = [distance / time for distance, time in legs]
    return sum(speeds) / len(speeds)""",
    visible_test=_test_module(
        "journey_rate",
        "Published contract for the average speed of a journey.",
        """
def test_two_legs_of_the_same_length_in_time() -> None:
    assert average_speed([(60, 1), (120, 1)]) == 90.0


def test_two_longer_legs_of_the_same_length_in_time() -> None:
    assert average_speed([(50, 2), (150, 2)]) == 50.0


def test_a_single_leg() -> None:
    assert average_speed([(100, 4)]) == 25.0
""",
        imports="from journey_rate import average_speed\n",
    ),
    hidden_test=_test_module(
        "journey_rate",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_legs_of_the_same_length_in_time() -> None:
    assert average_speed([(60, 1), (120, 1)]) == 90.0


def test_the_average_is_over_the_totals_not_the_mean_of_the_leg_speeds() -> None:
    assert average_speed([(60, 1), (60, 3)]) == 30.0


def test_a_leg_that_takes_no_time_is_refused() -> None:
    with pytest.raises(ValueError):
        average_speed([(10, 0)])
""",
        imports="from journey_rate import average_speed\n",
    ),
)

_G080 = D2TaskSpec(
    template_id="d4_numeric.trimmed_mean",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d4-numeric-trimmed-mean",
    module="trimmed_average",
    module_doc="Averaging readings once the extremes at each end are dropped.",
    issue=(
        "trimmed_mean() is documented to average readings once a few at each end are dropped. "
        "Callers report that asking to drop none of them brings the call down instead of "
        "averaging them all, and that asking to drop more than there are brings it down as well "
        "rather than saying so."
    ),
    expected=(
        "trimmed_mean(values, trim) sorts the readings, drops `trim` from each end, and averages "
        "what is left; a trim of zero averages every reading, and a trim that would leave "
        "nothing raises ValueError."
    ),
    baseline_reason=(
        "it takes the slice from `trim` to minus `trim`, which for a trim of zero is the empty "
        "slice"
    ),
    edge_cases=(
        "a trim of zero averages every reading",
        "a trim that would leave nothing is refused",
    ),
    baseline="""def trimmed_mean(values, trim):
    \"\"\"Average `values` once `trim` readings at each end are dropped.\"\"\"
    ordered = sorted(values)
    kept = ordered[trim:-trim]
    return sum(kept) / len(kept)""",
    variant_one="""def trimmed_mean(values, trim):
    \"\"\"Average `values` once `trim` readings at each end are dropped.\"\"\"
    ordered = sorted(values)
    kept = ordered[trim : len(ordered) - trim]
    if not kept:
        raise ValueError("trimming that much leaves nothing to average")
    return sum(kept) / len(kept)""",
    variant_two="""def trimmed_mean(values, trim):
    \"\"\"Average `values` once `trim` readings at each end are dropped.\"\"\"
    ordered = sorted(values)
    kept = [
        value for index, value in enumerate(ordered) if trim <= index < len(ordered) - trim
    ]
    if not kept:
        raise ValueError("trimming that much leaves nothing to average")
    return sum(kept) / len(kept)""",
    variant_three="""def trimmed_mean(values, trim):
    \"\"\"Average `values` once `trim` readings at each end are dropped.\"\"\"
    ordered = sorted(values)
    kept = ordered[trim : len(ordered) - trim]
    return sum(kept) / len(kept)""",
    variant_four="""def trimmed_mean(values, trim):
    \"\"\"Average `values` once `trim` readings at each end are dropped.\"\"\"
    ordered = sorted(values)
    kept = ordered[trim:-trim]
    if not kept:
        raise ValueError("trimming that much leaves nothing to average")
    return sum(kept) / len(kept)""",
    visible_test=_test_module(
        "trimmed_average",
        "Published contract for a trimmed average.",
        """
def test_dropping_one_from_each_end() -> None:
    assert trimmed_mean([1, 2, 3, 4, 5], 1) == 3.0


def test_the_readings_are_sorted_first() -> None:
    assert trimmed_mean([10, 1, 5], 1) == 5.0


def test_dropping_two_from_each_end() -> None:
    assert trimmed_mean([1, 2, 3, 4, 5, 6], 2) == 3.5
""",
        imports="from trimmed_average import trimmed_mean\n",
    ),
    hidden_test=_test_module(
        "trimmed_average",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_dropping_one_from_each_end() -> None:
    assert trimmed_mean([1, 2, 3, 4, 5], 1) == 3.0


def test_a_trim_of_zero_averages_every_reading() -> None:
    assert trimmed_mean([1, 2, 3], 0) == 2.0


def test_a_trim_that_would_leave_nothing_is_refused() -> None:
    with pytest.raises(ValueError):
        trimmed_mean([1, 2, 3], 2)
""",
        imports="from trimmed_average import trimmed_mean\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G081 = D2TaskSpec(
    template_id="d4_transform.melt_columns",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-melt-columns",
    module="wide_to_long",
    module_doc="Turning one wide record into a row per measure.",
    issue=(
        "melt() is documented to turn one wide record into a row per measure. Callers report "
        "that a measure recorded as nothing at all is left out entirely rather than reported as "
        "nothing, and that the rows come back in alphabetical order rather than in the order the "
        "record wrote them."
    ),
    expected=(
        "melt(record, keep) returns one row per field outside `keep`, in the record's own field "
        "order, each row carrying the kept fields alongside the field name and its value, "
        "including a field holding nothing."
    ),
    baseline_reason="it walks the field names in sorted order and passes over the empty ones",
    edge_cases=(
        "a field holding nothing still makes a row",
        "the rows follow the record's own field order",
    ),
    baseline="""def melt(record, keep):
    \"\"\"Turn the wide `record` into one row per field outside `keep`.\"\"\"
    kept = {name: record[name] for name in keep}
    rows = []
    for name in sorted(record):
        if name in keep or record[name] is None:
            continue
        rows.append({**kept, "field": name, "value": record[name]})
    return rows""",
    variant_one="""def melt(record, keep):
    \"\"\"Turn the wide `record` into one row per field outside `keep`.\"\"\"
    kept = {name: record[name] for name in keep}
    rows = []
    for name, value in record.items():
        if name in keep:
            continue
        rows.append({**kept, "field": name, "value": value})
    return rows""",
    variant_two="""def melt(record, keep):
    \"\"\"Turn the wide `record` into one row per field outside `keep`.\"\"\"
    kept = {name: record[name] for name in keep}
    return [
        dict(kept, field=name, value=value)
        for name, value in record.items()
        if name not in keep
    ]""",
    variant_three="""def melt(record, keep):
    \"\"\"Turn the wide `record` into one row per field outside `keep`.\"\"\"
    kept = {name: record[name] for name in keep}
    rows = []
    for name in sorted(record):
        if name in keep:
            continue
        rows.append({**kept, "field": name, "value": record[name]})
    return rows""",
    variant_four="""def melt(record, keep):
    \"\"\"Turn the wide `record` into one row per field outside `keep`.\"\"\"
    kept = {name: record[name] for name in keep}
    rows = []
    for name, value in record.items():
        if name in keep or value is None:
            continue
        rows.append({**kept, "field": name, "value": value})
    return rows""",
    visible_test=_test_module(
        "wide_to_long",
        "Published contract for melting a wide record.",
        """
def test_two_measures() -> None:
    assert melt({"id": 1, "alpha": 10, "beta": 20}, ("id",)) == [
        {"id": 1, "field": "alpha", "value": 10},
        {"id": 1, "field": "beta", "value": 20},
    ]


def test_a_single_measure() -> None:
    assert melt({"id": 7, "alpha": 3}, ("id",)) == [{"id": 7, "field": "alpha", "value": 3}]


def test_two_kept_fields() -> None:
    rows = melt({"id": 1, "day": "mon", "alpha": 10}, ("id", "day"))
    assert rows == [{"id": 1, "day": "mon", "field": "alpha", "value": 10}]
""",
        imports="from wide_to_long import melt\n",
    ),
    hidden_test=_test_module(
        "wide_to_long",
        "The part of the contract the published tests do not state.",
        """
def test_two_measures() -> None:
    assert melt({"id": 1, "alpha": 10, "beta": 20}, ("id",)) == [
        {"id": 1, "field": "alpha", "value": 10},
        {"id": 1, "field": "beta", "value": 20},
    ]


def test_a_field_holding_nothing_still_makes_a_row() -> None:
    assert melt({"id": 1, "alpha": None}, ("id",)) == [
        {"id": 1, "field": "alpha", "value": None}
    ]


def test_the_rows_follow_the_records_own_field_order() -> None:
    rows = melt({"id": 1, "beta": 20, "alpha": 10}, ("id",))
    assert [row["field"] for row in rows] == ["beta", "alpha"]
""",
        imports="from wide_to_long import melt\n",
    ),
)

_G082 = D2TaskSpec(
    template_id="d4_transform.first_value",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-first-value",
    module="first_present",
    module_doc="Choosing the first field a record actually holds.",
    issue=(
        "first_value() is documented to return the first of several fields a record actually "
        "holds. Callers report that a field holding the number zero is passed over as though it "
        "were missing, and that a record holding none of the fields brings the call down instead "
        "of falling back."
    ),
    expected=(
        "first_value(record, names, fallback) returns the value of the first name the record "
        "holds with anything other than None -- a zero counts -- and returns the fallback when "
        "the record holds none of them."
    ),
    baseline_reason="it keeps the values that look like something and takes the first of them",
    edge_cases=(
        "a field holding zero counts as held",
        "a record holding none of the names falls back",
    ),
    baseline="""def first_value(record, names, fallback):
    \"\"\"Return the first of `names` that `record` actually holds.\"\"\"
    found = [record[name] for name in names if record.get(name)]
    return found[0]""",
    variant_one="""def first_value(record, names, fallback):
    \"\"\"Return the first of `names` that `record` actually holds.\"\"\"
    for name in names:
        if name in record and record[name] is not None:
            return record[name]
    return fallback""",
    variant_two="""def first_value(record, names, fallback):
    \"\"\"Return the first of `names` that `record` actually holds.\"\"\"
    held = [record[name] for name in names if record.get(name, None) is not None]
    return held[0] if held else fallback""",
    variant_three="""def first_value(record, names, fallback):
    \"\"\"Return the first of `names` that `record` actually holds.\"\"\"
    found = [record[name] for name in names if record.get(name) is not None]
    return found[0]""",
    variant_four="""def first_value(record, names, fallback):
    \"\"\"Return the first of `names` that `record` actually holds.\"\"\"
    found = [record[name] for name in names if record.get(name)]
    return found[0] if found else fallback""",
    visible_test=_test_module(
        "first_present",
        "Published contract for choosing the first field held.",
        """
def test_the_first_name_wins() -> None:
    assert first_value({"nickname": "ada", "name": "Ada"}, ("nickname", "name"), "?") == "ada"


def test_a_name_the_record_does_not_have_is_passed_over() -> None:
    assert first_value({"name": "Ada"}, ("nickname", "name"), "?") == "Ada"


def test_a_name_the_record_holds_as_nothing_is_passed_over() -> None:
    assert first_value({"nickname": None, "name": "Ada"}, ("nickname", "name"), "?") == "Ada"
""",
        imports="from first_present import first_value\n",
    ),
    hidden_test=_test_module(
        "first_present",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_name_wins() -> None:
    assert first_value({"nickname": "ada", "name": "Ada"}, ("nickname", "name"), "?") == "ada"


def test_a_field_holding_zero_counts_as_held() -> None:
    assert first_value({"count": 0, "total": 5}, ("count", "total"), -1) == 0


def test_a_record_holding_none_of_the_names_falls_back() -> None:
    assert first_value({}, ("nickname", "name"), "?") == "?"
""",
        imports="from first_present import first_value\n",
    ),
)

_G083 = D2TaskSpec(
    template_id="d4_transform.build_tree",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-build-tree",
    module="parent_tree",
    module_doc="Building a tree out of records that name their parent.",
    issue=(
        "build_tree() is documented to build a tree out of records that name their parent. "
        "Callers report that a record naming a parent that is not in the batch brings the call "
        "down with a key error rather than being refused, and that the children of a node come "
        "back sorted by id rather than in the order the records arrived."
    ),
    expected=(
        "build_tree(records) returns the records with no parent as roots, each carrying its "
        "children in the order the records arrived, and raises ValueError for a record naming a "
        "parent that is not there."
    ),
    baseline_reason=(
        "it walks the records in id order and reaches for the parent without looking first"
    ),
    edge_cases=(
        "a record naming a parent that is not there is refused",
        "the children keep the order the records arrived in",
    ),
    baseline="""def build_tree(records):
    \"\"\"Return the roots of the tree the parent links describe.\"\"\"
    nodes = {record["id"]: {**record, "children": []} for record in records}
    roots = []
    for record in sorted(records, key=lambda item: item["id"]):
        node = nodes[record["id"]]
        if record["parent"] is None:
            roots.append(node)
        else:
            nodes[record["parent"]]["children"].append(node)
    return roots""",
    variant_one="""def build_tree(records):
    \"\"\"Return the roots of the tree the parent links describe.\"\"\"
    nodes = {record["id"]: {**record, "children": []} for record in records}
    roots = []
    for record in records:
        node = nodes[record["id"]]
        parent = record["parent"]
        if parent is None:
            roots.append(node)
        elif parent in nodes:
            nodes[parent]["children"].append(node)
        else:
            raise ValueError("a record names a parent that is not there")
    return roots""",
    variant_two="""def build_tree(records):
    \"\"\"Return the roots of the tree the parent links describe.\"\"\"
    known = {record["id"] for record in records}
    for record in records:
        if record["parent"] is not None and record["parent"] not in known:
            raise ValueError("a record names a parent that is not there")
    nodes = {record["id"]: dict(record, children=[]) for record in records}
    for record in records:
        if record["parent"] is not None:
            nodes[record["parent"]]["children"].append(nodes[record["id"]])
    return [nodes[record["id"]] for record in records if record["parent"] is None]""",
    variant_three="""def build_tree(records):
    \"\"\"Return the roots of the tree the parent links describe.\"\"\"
    nodes = {record["id"]: {**record, "children": []} for record in records}
    roots = []
    for record in sorted(records, key=lambda item: item["id"]):
        node = nodes[record["id"]]
        parent = record["parent"]
        if parent is None:
            roots.append(node)
        elif parent in nodes:
            nodes[parent]["children"].append(node)
        else:
            raise ValueError("a record names a parent that is not there")
    return roots""",
    variant_four="""def build_tree(records):
    \"\"\"Return the roots of the tree the parent links describe.\"\"\"
    nodes = {record["id"]: {**record, "children": []} for record in records}
    roots = []
    for record in records:
        node = nodes[record["id"]]
        if record["parent"] is None:
            roots.append(node)
        else:
            nodes[record["parent"]]["children"].append(node)
    return roots""",
    visible_test=_test_module(
        "parent_tree",
        "Published contract for building a tree from parent links.",
        """
def test_a_root_with_two_children() -> None:
    roots = build_tree(
        [
            {"id": 1, "parent": None},
            {"id": 2, "parent": 1},
            {"id": 3, "parent": 1},
        ]
    )
    assert len(roots) == 1
    assert [child["id"] for child in roots[0]["children"]] == [2, 3]


def test_a_single_record() -> None:
    roots = build_tree([{"id": 1, "parent": None}])
    assert roots[0]["children"] == []


def test_a_grandchild() -> None:
    roots = build_tree(
        [
            {"id": 1, "parent": None},
            {"id": 2, "parent": 1},
            {"id": 3, "parent": 2},
        ]
    )
    assert roots[0]["children"][0]["children"][0]["id"] == 3
""",
        imports="from parent_tree import build_tree\n",
    ),
    hidden_test=_test_module(
        "parent_tree",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_root_with_two_children() -> None:
    roots = build_tree(
        [
            {"id": 1, "parent": None},
            {"id": 2, "parent": 1},
            {"id": 3, "parent": 1},
        ]
    )
    assert [child["id"] for child in roots[0]["children"]] == [2, 3]


def test_a_record_naming_a_parent_that_is_not_there_is_refused() -> None:
    with pytest.raises(ValueError):
        build_tree([{"id": 1, "parent": None}, {"id": 2, "parent": 9}])


def test_the_children_keep_the_order_the_records_arrived_in() -> None:
    roots = build_tree(
        [
            {"id": 1, "parent": None},
            {"id": 3, "parent": 1},
            {"id": 2, "parent": 1},
        ]
    )
    assert [child["id"] for child in roots[0]["children"]] == [3, 2]
""",
        imports="from parent_tree import build_tree\n",
    ),
)

_G084 = D2TaskSpec(
    template_id="d4_transform.compact_record",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-compact-record",
    module="record_compaction",
    module_doc="Dropping the fields of a record that hold nothing.",
    issue=(
        "compact() is documented to drop the fields of a record that hold nothing. Callers "
        "report that a field holding the number zero or an empty string is dropped as well, and "
        "that a section nested inside the record keeps its empty fields."
    ),
    expected=(
        "compact(record) returns the record without the fields holding None, keeps a field "
        "holding zero, False or an empty string, and compacts a nested section the same way."
    ),
    baseline_reason="it keeps the fields that look like something and never looks inside one",
    edge_cases=(
        "a field holding zero or an empty string is kept",
        "a nested section is compacted too",
    ),
    baseline="""def compact(record):
    \"\"\"Return `record` without the fields that hold nothing.\"\"\"
    return {name: value for name, value in record.items() if value}""",
    variant_one="""def compact(record):
    \"\"\"Return `record` without the fields that hold nothing.\"\"\"
    compacted = {}
    for name, value in record.items():
        if value is None:
            continue
        compacted[name] = compact(value) if isinstance(value, dict) else value
    return compacted""",
    variant_two="""def compact(record):
    \"\"\"Return `record` without the fields that hold nothing.\"\"\"
    kept = [(name, value) for name, value in record.items() if value is not None]
    return dict(
        (name, compact(value)) if isinstance(value, dict) else (name, value)
        for name, value in kept
    )""",
    variant_three="""def compact(record):
    \"\"\"Return `record` without the fields that hold nothing.\"\"\"
    return {name: value for name, value in record.items() if value is not None}""",
    variant_four="""def compact(record):
    \"\"\"Return `record` without the fields that hold nothing.\"\"\"
    compacted = {}
    for name, value in record.items():
        if not value:
            continue
        compacted[name] = compact(value) if isinstance(value, dict) else value
    return compacted""",
    visible_test=_test_module(
        "record_compaction",
        "Published contract for dropping the empty fields of a record.",
        """
def test_one_empty_field() -> None:
    assert compact({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}


def test_a_record_with_nothing_to_drop() -> None:
    assert compact({"a": 1, "b": "x"}) == {"a": 1, "b": "x"}


def test_a_record_that_is_all_empty() -> None:
    assert compact({"a": None, "b": None}) == {}
""",
        imports="from record_compaction import compact\n",
    ),
    hidden_test=_test_module(
        "record_compaction",
        "The part of the contract the published tests do not state.",
        """
def test_one_empty_field() -> None:
    assert compact({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}


def test_a_field_holding_zero_or_an_empty_string_is_kept() -> None:
    assert compact({"a": 0, "b": "", "c": None}) == {"a": 0, "b": ""}


def test_a_nested_section_is_compacted_too() -> None:
    assert compact({"outer": {"a": 1, "b": None}}) == {"outer": {"a": 1}}
""",
        imports="from record_compaction import compact\n",
    ),
)

_G085 = D2TaskSpec(
    template_id="d4_transform.merge_sorted",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d4-transform-merge-sorted",
    module="sorted_merge",
    module_doc="Merging two already-sorted streams of records into one.",
    issue=(
        "merge_sorted() is documented to merge two already-sorted streams into one. Callers "
        "report that where a record from each side ties on the key the right-hand one is taken "
        "first, and that a record without the key at all brings the call down rather than "
        "sorting after the records that have one."
    ),
    expected=(
        "merge_sorted(left, right, key) returns the two streams merged in key order, takes the "
        "left record first where two tie, and sorts a record without the key after every record "
        "that has one."
    ),
    baseline_reason=(
        "it takes the left record only when it is strictly smaller, and reads the key straight "
        "off every record"
    ),
    edge_cases=(
        "a tie takes the left record first",
        "a record without the key sorts after the ones that have it",
    ),
    baseline="""def merge_sorted(left, right, key):
    \"\"\"Merge two streams already sorted by `key` into one.\"\"\"
    merged = []
    first = 0
    second = 0
    while first < len(left) and second < len(right):
        if left[first][key] < right[second][key]:
            merged.append(left[first])
            first += 1
        else:
            merged.append(right[second])
            second += 1
    merged.extend(left[first:])
    merged.extend(right[second:])
    return merged""",
    variant_one="""def merge_sorted(left, right, key):
    \"\"\"Merge two streams already sorted by `key` into one.\"\"\"
    merged = []
    first = 0
    second = 0
    while first < len(left) and second < len(right):
        ahead = left[first]
        behind = right[second]
        ahead_rank = (0, ahead[key]) if key in ahead else (1,)
        behind_rank = (0, behind[key]) if key in behind else (1,)
        if behind_rank < ahead_rank:
            merged.append(behind)
            second += 1
        else:
            merged.append(ahead)
            first += 1
    merged.extend(left[first:])
    merged.extend(right[second:])
    return merged""",
    variant_two="""def merge_sorted(left, right, key):
    \"\"\"Merge two streams already sorted by `key` into one.\"\"\"
    combined = [*left, *right]
    return sorted(
        combined, key=lambda record: (0, record[key]) if key in record else (1,)
    )""",
    variant_three="""def merge_sorted(left, right, key):
    \"\"\"Merge two streams already sorted by `key` into one.\"\"\"
    merged = []
    first = 0
    second = 0
    while first < len(left) and second < len(right):
        if right[second][key] < left[first][key]:
            merged.append(right[second])
            second += 1
        else:
            merged.append(left[first])
            first += 1
    merged.extend(left[first:])
    merged.extend(right[second:])
    return merged""",
    variant_four="""def merge_sorted(left, right, key):
    \"\"\"Merge two streams already sorted by `key` into one.\"\"\"
    merged = []
    first = 0
    second = 0
    while first < len(left) and second < len(right):
        ahead = left[first]
        behind = right[second]
        ahead_rank = (0, ahead[key]) if key in ahead else (1,)
        behind_rank = (0, behind[key]) if key in behind else (1,)
        if ahead_rank < behind_rank:
            merged.append(ahead)
            first += 1
        else:
            merged.append(behind)
            second += 1
    merged.extend(left[first:])
    merged.extend(right[second:])
    return merged""",
    visible_test=_test_module(
        "sorted_merge",
        "Published contract for merging two sorted streams.",
        """
def test_two_streams_that_interleave() -> None:
    left = [{"n": 1}, {"n": 3}]
    right = [{"n": 2}, {"n": 4}]
    assert [record["n"] for record in merge_sorted(left, right, "n")] == [1, 2, 3, 4]


def test_one_stream_empty() -> None:
    assert merge_sorted([], [{"n": 1}], "n") == [{"n": 1}]


def test_one_record_on_each_side() -> None:
    assert [record["n"] for record in merge_sorted([{"n": 1}], [{"n": 5}], "n")] == [1, 5]
""",
        imports="from sorted_merge import merge_sorted\n",
    ),
    hidden_test=_test_module(
        "sorted_merge",
        "The part of the contract the published tests do not state.",
        """
def test_two_streams_that_interleave() -> None:
    left = [{"n": 1}, {"n": 3}]
    right = [{"n": 2}, {"n": 4}]
    assert [record["n"] for record in merge_sorted(left, right, "n")] == [1, 2, 3, 4]


def test_a_tie_takes_the_left_record_first() -> None:
    merged = merge_sorted([{"id": "L", "n": 2}], [{"id": "R", "n": 2}], "n")
    assert [record["id"] for record in merged] == ["L", "R"]


def test_a_record_without_the_key_sorts_after_the_ones_that_have_it() -> None:
    merged = merge_sorted([{"id": "a", "n": 1}, {"id": "z"}], [{"id": "b", "n": 2}], "n")
    assert [record["id"] for record in merged] == ["a", "b", "z"]
""",
        imports="from sorted_merge import merge_sorted\n",
    ),
)

# ------------------------------------------------------------------------------ error handling

_G086 = D2TaskSpec(
    template_id="d4_errors.unwrap_result",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-unwrap-result",
    module="result_unwrap",
    module_doc="Reading a result that carries either a value or an error.",
    issue=(
        "unwrap() is documented to report whether a result succeeded and what it carries. "
        "Callers report that a result carrying the number zero is refused as carrying nothing, "
        "and that a failure whose message is empty is refused the same way instead of being "
        "reported as the failure it is."
    ),
    expected=(
        "unwrap(result) returns (True, value) for a result carrying a value, (False, message) "
        "for one carrying an error, and raises ValueError only for a result carrying neither; "
        "a value of zero and a message of no words are still a value and still a message."
    ),
    baseline_reason=(
        "it asks whether each field looks like something rather than whether it is there"
    ),
    edge_cases=(
        "a value of zero is still a value",
        "an error whose message is empty is still an error",
    ),
    baseline="""def unwrap(result):
    \"\"\"Return (True, value) or (False, message) for `result`.\"\"\"
    if result.get("error"):
        return False, result["error"]
    if result.get("value"):
        return True, result["value"]
    raise ValueError("the result carries neither a value nor an error")""",
    variant_one="""def unwrap(result):
    \"\"\"Return (True, value) or (False, message) for `result`.\"\"\"
    if "error" in result:
        return False, result["error"]
    if "value" in result:
        return True, result["value"]
    raise ValueError("the result carries neither a value nor an error")""",
    variant_two="""def unwrap(result):
    \"\"\"Return (True, value) or (False, message) for `result`.\"\"\"
    carried = [name for name in ("error", "value") if name in result]
    if not carried:
        raise ValueError("the result carries neither a value nor an error")
    return carried[0] == "value", result[carried[0]]""",
    variant_three="""def unwrap(result):
    \"\"\"Return (True, value) or (False, message) for `result`.\"\"\"
    if result.get("error"):
        return False, result["error"]
    if "value" in result:
        return True, result["value"]
    raise ValueError("the result carries neither a value nor an error")""",
    variant_four="""def unwrap(result):
    \"\"\"Return (True, value) or (False, message) for `result`.\"\"\"
    if "error" in result:
        return False, result["error"]
    if result.get("value"):
        return True, result["value"]
    raise ValueError("the result carries neither a value nor an error")""",
    visible_test=_test_module(
        "result_unwrap",
        "Published contract for reading a result.",
        """
import pytest


def test_a_result_carrying_a_value() -> None:
    assert unwrap({"value": 5}) == (True, 5)


def test_a_result_carrying_an_error() -> None:
    assert unwrap({"error": "boom"}) == (False, "boom")


def test_a_result_carrying_neither() -> None:
    with pytest.raises(ValueError):
        unwrap({})
""",
        imports="from result_unwrap import unwrap\n",
    ),
    hidden_test=_test_module(
        "result_unwrap",
        "The part of the contract the published tests do not state.",
        """
def test_a_result_carrying_a_value() -> None:
    assert unwrap({"value": 5}) == (True, 5)


def test_a_value_of_zero_is_still_a_value() -> None:
    assert unwrap({"value": 0}) == (True, 0)


def test_an_error_whose_message_is_empty_is_still_an_error() -> None:
    assert unwrap({"error": ""}) == (False, "")
""",
        imports="from result_unwrap import unwrap\n",
    ),
)

_G087 = D2TaskSpec(
    template_id="d4_errors.should_retry",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-should-retry",
    module="retry_decision",
    module_doc="Deciding whether a failed call is worth trying again.",
    issue=(
        "should_retry() is documented to decide whether a failed call is worth trying again. "
        "Callers report that the last attempt allowed is retried once more, giving one attempt "
        "too many, and that an error of a kind nobody has classified is retried as though it "
        "were a passing glitch."
    ),
    expected=(
        "should_retry(kind, attempt, limit) retries only the kinds known to pass -- timed out, "
        "throttled, unavailable -- and only while an attempt is left, counting attempts from "
        "one, so the attempt numbered `limit` is the last."
    ),
    baseline_reason=(
        "it names the kinds that must not be retried rather than the kinds that may, and counts "
        "the last attempt as one still to come"
    ),
    edge_cases=(
        "the last attempt allowed is not retried",
        "a kind nobody has classified is not retried",
    ),
    baseline="""def should_retry(kind, attempt, limit):
    \"\"\"Return whether an error of `kind` on `attempt` is worth trying again.\"\"\"
    permanent = ("invalid", "forbidden")
    if kind in permanent:
        return False
    return attempt <= limit""",
    variant_one="""def should_retry(kind, attempt, limit):
    \"\"\"Return whether an error of `kind` on `attempt` is worth trying again.\"\"\"
    transient = ("timed_out", "throttled", "unavailable")
    return kind in transient and attempt < limit""",
    variant_two="""def should_retry(kind, attempt, limit):
    \"\"\"Return whether an error of `kind` on `attempt` is worth trying again.\"\"\"
    if attempt >= limit:
        return False
    for passing in ("timed_out", "throttled", "unavailable"):
        if kind == passing:
            return True
    return False""",
    variant_three="""def should_retry(kind, attempt, limit):
    \"\"\"Return whether an error of `kind` on `attempt` is worth trying again.\"\"\"
    permanent = ("invalid", "forbidden")
    if kind in permanent:
        return False
    return attempt < limit""",
    variant_four="""def should_retry(kind, attempt, limit):
    \"\"\"Return whether an error of `kind` on `attempt` is worth trying again.\"\"\"
    transient = ("timed_out", "throttled", "unavailable")
    if kind not in transient:
        return False
    return attempt <= limit""",
    visible_test=_test_module(
        "retry_decision",
        "Published contract for deciding on a retry.",
        """
def test_a_glitch_early_in_the_run() -> None:
    assert should_retry("timed_out", 1, 3) is True


def test_a_throttle_part_way_through() -> None:
    assert should_retry("throttled", 2, 3) is True


def test_a_request_that_was_never_valid() -> None:
    assert should_retry("invalid", 1, 3) is False
""",
        imports="from retry_decision import should_retry\n",
    ),
    hidden_test=_test_module(
        "retry_decision",
        "The part of the contract the published tests do not state.",
        """
def test_a_glitch_early_in_the_run() -> None:
    assert should_retry("timed_out", 1, 3) is True


def test_the_last_attempt_allowed_is_not_retried() -> None:
    assert should_retry("timed_out", 3, 3) is False


def test_a_kind_nobody_has_classified_is_not_retried() -> None:
    assert should_retry("corrupted", 1, 3) is False
""",
        imports="from retry_decision import should_retry\n",
    ),
)

_G088 = D2TaskSpec(
    template_id="d4_errors.summarise_attempts",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-summarise-attempts",
    module="attempt_summary",
    module_doc="Summarising how a run of attempts ended.",
    issue=(
        "summarise_attempts() is documented to report how many attempts a run took and what "
        "went wrong last. Callers report that a run which recovered still reports the error it "
        "recovered from, and that a run with no attempts at all brings the call down."
    ),
    expected=(
        "summarise_attempts(attempts) returns (how many attempts, the error the run ended on), "
        "reporting no error at all for a run whose last attempt succeeded and for a run with no "
        "attempts."
    ),
    baseline_reason="it gathers every error the run met and reports the last of those",
    edge_cases=(
        "a run whose last attempt succeeded reports no error",
        "a run with no attempts reports none rather than raising",
    ),
    baseline="""def summarise_attempts(attempts):
    \"\"\"Return how many attempts a run took and the error it ended on.\"\"\"
    errors = [attempt["error"] for attempt in attempts if attempt.get("error")]
    return len(attempts), errors[-1]""",
    variant_one="""def summarise_attempts(attempts):
    \"\"\"Return how many attempts a run took and the error it ended on.\"\"\"
    if not attempts:
        return 0, None
    return len(attempts), attempts[-1].get("error")""",
    variant_two="""def summarise_attempts(attempts):
    \"\"\"Return how many attempts a run took and the error it ended on.\"\"\"
    last = attempts[-1] if attempts else {}
    return len(attempts), last.get("error")""",
    variant_three="""def summarise_attempts(attempts):
    \"\"\"Return how many attempts a run took and the error it ended on.\"\"\"
    return len(attempts), attempts[-1].get("error")""",
    variant_four="""def summarise_attempts(attempts):
    \"\"\"Return how many attempts a run took and the error it ended on.\"\"\"
    errors = [attempt["error"] for attempt in attempts if attempt.get("error")]
    return len(attempts), errors[-1] if errors else None""",
    visible_test=_test_module(
        "attempt_summary",
        "Published contract for summarising a run of attempts.",
        """
def test_a_single_failed_attempt() -> None:
    assert summarise_attempts([{"error": "boom"}]) == (1, "boom")


def test_a_run_that_failed_after_a_success() -> None:
    assert summarise_attempts([{"ok": True}, {"error": "boom"}]) == (2, "boom")


def test_a_run_that_failed_twice() -> None:
    assert summarise_attempts([{"error": "a"}, {"error": "b"}]) == (2, "b")
""",
        imports="from attempt_summary import summarise_attempts\n",
    ),
    hidden_test=_test_module(
        "attempt_summary",
        "The part of the contract the published tests do not state.",
        """
def test_a_single_failed_attempt() -> None:
    assert summarise_attempts([{"error": "boom"}]) == (1, "boom")


def test_a_run_whose_last_attempt_succeeded_reports_no_error() -> None:
    assert summarise_attempts([{"error": "boom"}, {"ok": True}]) == (2, None)


def test_a_run_with_no_attempts_reports_none() -> None:
    assert summarise_attempts([]) == (0, None)
""",
        imports="from attempt_summary import summarise_attempts\n",
    ),
)

_G089 = D2TaskSpec(
    template_id="d4_errors.explain_missing",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-explain-missing",
    module="missing_report",
    module_doc="Naming the required fields a record does not hold.",
    issue=(
        "explain_missing() is documented to name the required fields a record does not hold. "
        "Callers report that a field written into the record as nothing counts as held, and "
        "that a record holding everything still comes back with a message naming nothing at all."
    ),
    expected=(
        "explain_missing(record, required) returns a message naming every required field the "
        "record does not hold, in the order they were required, counting a field written as "
        "None as not held, and returns None when the record holds them all."
    ),
    baseline_reason=(
        "it asks only whether the name is written in the record and always writes a message"
    ),
    edge_cases=(
        "a field written as None counts as not held",
        "a record holding every field gets no message at all",
    ),
    baseline="""def explain_missing(record, required):
    \"\"\"Return a message naming the required fields `record` does not hold.\"\"\"
    missing = [name for name in required if name not in record]
    return "missing: " + ", ".join(missing)""",
    variant_one="""def explain_missing(record, required):
    \"\"\"Return a message naming the required fields `record` does not hold.\"\"\"
    missing = [name for name in required if record.get(name) is None]
    if not missing:
        return None
    return "missing: " + ", ".join(missing)""",
    variant_two="""def explain_missing(record, required):
    \"\"\"Return a message naming the required fields `record` does not hold.\"\"\"
    missing = []
    for name in required:
        if name not in record or record[name] is None:
            missing.append(name)
    return "missing: {}".format(", ".join(missing)) if missing else None""",
    variant_three="""def explain_missing(record, required):
    \"\"\"Return a message naming the required fields `record` does not hold.\"\"\"
    missing = [name for name in required if record.get(name) is None]
    return "missing: " + ", ".join(missing)""",
    variant_four="""def explain_missing(record, required):
    \"\"\"Return a message naming the required fields `record` does not hold.\"\"\"
    missing = [name for name in required if name not in record]
    if not missing:
        return None
    return "missing: " + ", ".join(missing)""",
    visible_test=_test_module(
        "missing_report",
        "Published contract for naming the fields a record lacks.",
        """
def test_one_field_missing() -> None:
    assert explain_missing({"a": 1}, ("a", "b")) == "missing: b"


def test_every_field_missing() -> None:
    assert explain_missing({}, ("a", "b")) == "missing: a, b"


def test_the_order_the_fields_were_required_in() -> None:
    assert explain_missing({"b": 2}, ("a", "b", "c")) == "missing: a, c"
""",
        imports="from missing_report import explain_missing\n",
    ),
    hidden_test=_test_module(
        "missing_report",
        "The part of the contract the published tests do not state.",
        """
def test_one_field_missing() -> None:
    assert explain_missing({"a": 1}, ("a", "b")) == "missing: b"


def test_a_field_written_as_none_counts_as_not_held() -> None:
    assert explain_missing({"a": 1, "b": None}, ("a", "b")) == "missing: b"


def test_a_record_holding_every_field_gets_no_message_at_all() -> None:
    assert explain_missing({"a": 1, "b": 2}, ("a", "b")) is None
""",
        imports="from missing_report import explain_missing\n",
    ),
)

_G090 = D2TaskSpec(
    template_id="d4_errors.matches_known",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-matches-known",
    module="known_errors",
    module_doc="Recognising an error message as one already known about.",
    issue=(
        "matches_known() is documented to say whether an error message is one already known "
        "about. Callers report that the same message written with capitals goes unrecognised, "
        "and that when nothing at all is known about yet every message is recognised."
    ),
    expected=(
        "matches_known(message, patterns) returns whether the message holds any of the patterns, "
        "ignoring the case of both, and returns False when there are no patterns to match."
    ),
    baseline_reason="it matches the case exactly and treats knowing nothing as knowing everything",
    edge_cases=(
        "the match ignores the case of both sides",
        "no patterns at all match nothing",
    ),
    baseline="""def matches_known(message, patterns):
    \"\"\"Return whether `message` is one of the known `patterns`.\"\"\"
    if not patterns:
        return True
    return any(pattern in message for pattern in patterns)""",
    variant_one="""def matches_known(message, patterns):
    \"\"\"Return whether `message` is one of the known `patterns`.\"\"\"
    lowered = message.lower()
    return any(pattern.lower() in lowered for pattern in patterns)""",
    variant_two="""def matches_known(message, patterns):
    \"\"\"Return whether `message` is one of the known `patterns`.\"\"\"
    for pattern in patterns:
        if pattern.casefold() in message.casefold():
            return True
    return False""",
    variant_three="""def matches_known(message, patterns):
    \"\"\"Return whether `message` is one of the known `patterns`.\"\"\"
    if not patterns:
        return True
    lowered = message.lower()
    return any(pattern.lower() in lowered for pattern in patterns)""",
    variant_four="""def matches_known(message, patterns):
    \"\"\"Return whether `message` is one of the known `patterns`.\"\"\"
    if not patterns:
        return False
    return any(pattern in message for pattern in patterns)""",
    visible_test=_test_module(
        "known_errors",
        "Published contract for recognising a known error.",
        """
def test_a_message_that_is_known() -> None:
    assert matches_known("connection timed out", ("timed out",)) is True


def test_the_second_pattern_matches() -> None:
    assert matches_known("connection refused", ("timed out", "refused")) is True


def test_a_message_that_is_not_known() -> None:
    assert matches_known("all is well", ("timed out",)) is False
""",
        imports="from known_errors import matches_known\n",
    ),
    hidden_test=_test_module(
        "known_errors",
        "The part of the contract the published tests do not state.",
        """
def test_a_message_that_is_known() -> None:
    assert matches_known("connection timed out", ("timed out",)) is True


def test_the_match_ignores_the_case_of_both_sides() -> None:
    assert matches_known("Connection Timed Out", ("timed out",)) is True


def test_no_patterns_at_all_match_nothing() -> None:
    assert matches_known("anything at all", ()) is False
""",
        imports="from known_errors import matches_known\n",
    ),
)

_G091 = D2TaskSpec(
    template_id="d4_errors.rate_limited",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d4-errors-rate-limited",
    module="request_window",
    module_doc="Deciding whether another request would break a rate limit.",
    issue=(
        "rate_limited() is documented to say whether another request now would break the limit. "
        "Callers report that a request stamped exactly at the far edge of the window is counted "
        "as outside it, and that a history that does not arrive newest first is barely counted "
        "at all."
    ),
    expected=(
        "rate_limited(history, now, window, limit) counts every stamp at or after `now` minus "
        "the window, whatever order the history arrives in, and reports whether that count has "
        "reached the limit."
    ),
    baseline_reason=(
        "it counts down the history until the first stamp too old and takes that as the end of "
        "the window"
    ),
    edge_cases=(
        "a stamp exactly on the edge of the window is inside it",
        "a history that does not arrive newest first is counted all the same",
    ),
    baseline="""def rate_limited(history, now, window, limit):
    \"\"\"Return whether another request now would break the limit.\"\"\"
    recent = 0
    for stamp in history:
        if stamp > now - window:
            recent += 1
        else:
            break
    return recent >= limit""",
    variant_one="""def rate_limited(history, now, window, limit):
    \"\"\"Return whether another request now would break the limit.\"\"\"
    recent = [stamp for stamp in history if stamp >= now - window]
    return len(recent) >= limit""",
    variant_two="""def rate_limited(history, now, window, limit):
    \"\"\"Return whether another request now would break the limit.\"\"\"
    edge = now - window
    return sum(1 for stamp in history if stamp >= edge) >= limit""",
    variant_three="""def rate_limited(history, now, window, limit):
    \"\"\"Return whether another request now would break the limit.\"\"\"
    recent = 0
    for stamp in history:
        if stamp >= now - window:
            recent += 1
        else:
            break
    return recent >= limit""",
    variant_four="""def rate_limited(history, now, window, limit):
    \"\"\"Return whether another request now would break the limit.\"\"\"
    edge = now - window
    return sum(1 for stamp in history if stamp > edge) >= limit""",
    visible_test=_test_module(
        "request_window",
        "Published contract for a rate limit over a window.",
        """
def test_a_window_that_is_full() -> None:
    assert rate_limited([100, 95, 80], 100, 30, 3) is True


def test_a_window_with_room_left() -> None:
    assert rate_limited([100, 95], 100, 30, 3) is False


def test_no_history_at_all() -> None:
    assert rate_limited([], 100, 30, 1) is False
""",
        imports="from request_window import rate_limited\n",
    ),
    hidden_test=_test_module(
        "request_window",
        "The part of the contract the published tests do not state.",
        """
def test_a_window_that_is_full() -> None:
    assert rate_limited([100, 95, 80], 100, 30, 3) is True


def test_a_stamp_exactly_on_the_edge_of_the_window_is_inside_it() -> None:
    assert rate_limited([70], 100, 30, 1) is True


def test_a_history_that_does_not_arrive_newest_first_is_counted_all_the_same() -> None:
    assert rate_limited([50, 95, 100], 100, 30, 2) is True
""",
        imports="from request_window import rate_limited\n",
    ),
)

# ------------------------------------------------------------------------ parsing and validation

_G092 = D2TaskSpec(
    template_id="d4_parsing.parse_duration_parts",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-duration-parts",
    module="duration_parts",
    module_doc="Reading a duration written as a run of numbered parts.",
    issue=(
        "parse_duration() is documented to read a duration written as a run of numbered parts. "
        "Callers report that a number written at the end with no unit after it is quietly "
        "dropped, and that an unknown unit brings the call down with a key error instead of "
        "being refused as bad input."
    ),
    expected=(
        "parse_duration(text) returns the seconds the parts add up to, takes the parts in any "
        "order, and raises ValueError both for a number with no unit after it and for a unit it "
        "does not know."
    ),
    baseline_reason=(
        "it looks each unit up as it meets it and forgets whatever number is still in hand at "
        "the end"
    ),
    edge_cases=(
        "a number with no unit after it is refused",
        "a unit the reader does not know is refused",
    ),
    baseline="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` describes.\"\"\"
    units = {"h": 3600, "m": 60, "s": 1}
    total = 0
    number = ""
    for letter in text:
        if letter.isdigit():
            number += letter
        else:
            total += int(number) * units[letter]
            number = ""
    return total""",
    variant_one="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` describes.\"\"\"
    units = {"h": 3600, "m": 60, "s": 1}
    total = 0
    number = ""
    for letter in text:
        if letter.isdigit():
            number += letter
            continue
        if letter not in units:
            raise ValueError("that is not a unit of time")
        total += int(number) * units[letter]
        number = ""
    if number:
        raise ValueError("a number with no unit is not a duration")
    return total""",
    variant_two="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` describes.\"\"\"
    units = {"h": 3600, "m": 60, "s": 1}
    parts = []
    number = ""
    for letter in text:
        if letter.isdigit():
            number += letter
        elif letter in units:
            parts.append((int(number), units[letter]))
            number = ""
        else:
            raise ValueError("that is not a unit of time")
    if number:
        raise ValueError("a number with no unit is not a duration")
    return sum(count * seconds for count, seconds in parts)""",
    variant_three="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` describes.\"\"\"
    units = {"h": 3600, "m": 60, "s": 1}
    total = 0
    number = ""
    for letter in text:
        if letter.isdigit():
            number += letter
        else:
            total += int(number) * units[letter]
            number = ""
    if number:
        raise ValueError("a number with no unit is not a duration")
    return total""",
    variant_four="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` describes.\"\"\"
    units = {"h": 3600, "m": 60, "s": 1}
    total = 0
    number = ""
    for letter in text:
        if letter.isdigit():
            number += letter
            continue
        if letter not in units:
            raise ValueError("that is not a unit of time")
        total += int(number) * units[letter]
        number = ""
    return total""",
    visible_test=_test_module(
        "duration_parts",
        "Published contract for reading a duration.",
        """
def test_a_single_part() -> None:
    assert parse_duration("1h") == 3600


def test_two_parts() -> None:
    assert parse_duration("1h30m") == 5400


def test_the_parts_in_any_order() -> None:
    assert parse_duration("30m1h") == 5400
""",
        imports="from duration_parts import parse_duration\n",
    ),
    hidden_test=_test_module(
        "duration_parts",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_single_part() -> None:
    assert parse_duration("1h") == 3600


def test_a_number_with_no_unit_after_it_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_duration("1h30")


def test_a_unit_the_reader_does_not_know_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_duration("5x")
""",
        imports="from duration_parts import parse_duration\n",
    ),
)

_G093 = D2TaskSpec(
    template_id="d4_parsing.parse_semver",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d4-parsing-semver",
    module="semver_parts",
    module_doc="Splitting a version into its core, prerelease and build parts.",
    issue=(
        "parse_semver() is documented to split a version into its core, its prerelease and its "
        "build metadata. Callers report that a prerelease with a hyphen inside it is split a "
        "second time, leaving the hyphen's left half glued to the core, and that a version "
        "without a prerelease or without build metadata reports an empty string where it should "
        "report nothing at all."
    ),
    expected=(
        "parse_semver(text) returns (core, prerelease, build); the build is whatever follows the "
        "first plus sign, the prerelease is everything after the first hyphen before it, and a "
        "part the version does not carry is reported as None."
    ),
    baseline_reason=(
        "it cuts the prerelease off at the last hyphen rather than the first and reports what is "
        "left over"
    ),
    edge_cases=(
        "a prerelease with a hyphen inside it is not split again",
        "a part the version does not carry is reported as nothing at all",
    ),
    baseline="""def parse_semver(text):
    \"\"\"Split a version into its core, its prerelease and its build metadata.\"\"\"
    head, _, build = text.partition("+")
    core, _, prerelease = head.rpartition("-")
    if not core:
        core, prerelease = head, ""
    return core, prerelease, build""",
    variant_one="""def parse_semver(text):
    \"\"\"Split a version into its core, its prerelease and its build metadata.\"\"\"
    head, plus, build = text.partition("+")
    core, hyphen, prerelease = head.partition("-")
    return core, prerelease if hyphen else None, build if plus else None""",
    variant_two="""def parse_semver(text):
    \"\"\"Split a version into its core, its prerelease and its build metadata.\"\"\"
    build = None
    head = text
    if "+" in text:
        head, build = text.split("+", 1)
    prerelease = None
    core = head
    if "-" in head:
        core, prerelease = head.split("-", 1)
    return core, prerelease, build""",
    variant_three="""def parse_semver(text):
    \"\"\"Split a version into its core, its prerelease and its build metadata.\"\"\"
    head, _, build = text.partition("+")
    core, _, prerelease = head.partition("-")
    return core, prerelease, build""",
    variant_four="""def parse_semver(text):
    \"\"\"Split a version into its core, its prerelease and its build metadata.\"\"\"
    head, plus, build = text.partition("+")
    core, hyphen, prerelease = head.rpartition("-")
    if not hyphen:
        core, prerelease = head, None
    return core, prerelease, build if plus else None""",
    visible_test=_test_module(
        "semver_parts",
        "Published contract for splitting a version.",
        """
def test_a_release_candidate_with_build_metadata() -> None:
    assert parse_semver("1.2.3-rc.1+build5") == ("1.2.3", "rc.1", "build5")


def test_an_alpha_with_a_build_number() -> None:
    assert parse_semver("2.0.0-alpha+001") == ("2.0.0", "alpha", "001")


def test_a_beta_with_a_longer_build() -> None:
    assert parse_semver("0.1.0-beta.2+exp.sha") == ("0.1.0", "beta.2", "exp.sha")
""",
        imports="from semver_parts import parse_semver\n",
    ),
    hidden_test=_test_module(
        "semver_parts",
        "The part of the contract the published tests do not state.",
        """
def test_a_release_candidate_with_build_metadata() -> None:
    assert parse_semver("1.2.3-rc.1+build5") == ("1.2.3", "rc.1", "build5")


def test_a_prerelease_with_a_hyphen_inside_it_is_not_split_again() -> None:
    assert parse_semver("1.2.3-alpha-2+b") == ("1.2.3", "alpha-2", "b")


def test_a_part_the_version_does_not_carry_is_reported_as_nothing() -> None:
    assert parse_semver("1.2.3") == ("1.2.3", None, None)
""",
        imports="from semver_parts import parse_semver\n",
    ),
)

# ------------------------------------------------------------------------- state and idempotency

_G094 = D2TaskSpec(
    template_id="d4_state.set_primary",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-set-primary",
    module="primary_flag",
    module_doc="Marking exactly one of a set of items as the primary one.",
    issue=(
        "set_primary() is documented to mark one item primary and leave exactly one. Callers "
        "report that the item that was primary before stays primary as well, so two of them "
        "are, and that naming an item that is not there quietly creates it."
    ),
    expected=(
        "set_primary(items, name) returns the items with `name` the only primary one, every "
        "other one no longer primary, and raises ValueError for a name that is not there."
    ),
    baseline_reason="it marks the one it was given and never touches the one that held the mark",
    edge_cases=(
        "the item that was primary before is no longer primary",
        "a name that is not there is refused",
    ),
    baseline="""def set_primary(items, name):
    \"\"\"Return `items` with `name` the only primary one.\"\"\"
    updated = dict(items)
    updated[name] = {**items.get(name, {}), "primary": True}
    return updated""",
    variant_one="""def set_primary(items, name):
    \"\"\"Return `items` with `name` the only primary one.\"\"\"
    if name not in items:
        raise ValueError("no such item")
    return {key: {**record, "primary": key == name} for key, record in items.items()}""",
    variant_two="""def set_primary(items, name):
    \"\"\"Return `items` with `name` the only primary one.\"\"\"
    if name not in items:
        raise ValueError("no such item")
    cleared = {key: dict(record, primary=False) for key, record in items.items()}
    cleared[name] = dict(items[name], primary=True)
    return cleared""",
    variant_three="""def set_primary(items, name):
    \"\"\"Return `items` with `name` the only primary one.\"\"\"
    if name not in items:
        raise ValueError("no such item")
    updated = dict(items)
    updated[name] = {**items[name], "primary": True}
    return updated""",
    variant_four="""def set_primary(items, name):
    \"\"\"Return `items` with `name` the only primary one.\"\"\"
    updated = {key: {**record, "primary": False} for key, record in items.items()}
    updated[name] = {**items.get(name, {}), "primary": True}
    return updated""",
    visible_test=_test_module(
        "primary_flag",
        "Published contract for marking the primary item.",
        """
def test_marking_one_of_two() -> None:
    items = {"a": {"primary": False}, "b": {"primary": False}}
    assert set_primary(items, "a") == {"a": {"primary": True}, "b": {"primary": False}}


def test_the_other_fields_are_carried_over() -> None:
    items = {"a": {"primary": False, "label": "first"}}
    assert set_primary(items, "a")["a"]["label"] == "first"


def test_the_caller_items_are_not_changed() -> None:
    items = {"a": {"primary": False}, "b": {"primary": False}}
    set_primary(items, "a")
    assert items["a"] == {"primary": False}
""",
        imports="from primary_flag import set_primary\n",
    ),
    hidden_test=_test_module(
        "primary_flag",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_marking_one_of_two() -> None:
    items = {"a": {"primary": False}, "b": {"primary": False}}
    assert set_primary(items, "a") == {"a": {"primary": True}, "b": {"primary": False}}


def test_the_item_that_was_primary_before_is_no_longer_primary() -> None:
    items = {"a": {"primary": True}, "b": {"primary": False}}
    assert set_primary(items, "b") == {"a": {"primary": False}, "b": {"primary": True}}


def test_a_name_that_is_not_there_is_refused() -> None:
    with pytest.raises(ValueError):
        set_primary({"a": {"primary": False}}, "nobody")
""",
        imports="from primary_flag import set_primary\n",
    ),
)

_G095 = D2TaskSpec(
    template_id="d4_state.assign_reviewer",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d4-state-assign-reviewer",
    module="review_rota",
    module_doc="Handing a request to the next reviewer on a rota.",
    issue=(
        "assign() is documented to hand a request to the next reviewer on the rota. Callers "
        "report that someone can be given their own request to review, and that once the rota "
        "reaches the last reviewer its next position runs off the end of the roster instead of "
        "coming back round."
    ),
    expected=(
        "assign(rota, requester) returns the rota moved on and the reviewer it names, passes "
        "over the requester so nobody reviews their own request, and brings the next position "
        "back round to the start once it passes the last reviewer."
    ),
    baseline_reason=(
        "it takes whoever stands at the next position and moves that position on by one"
    ),
    edge_cases=(
        "the requester is passed over rather than given their own request",
        "the next position comes back round instead of running off the end",
    ),
    baseline="""def assign(rota, requester):
    \"\"\"Return the rota moved on and the reviewer it names.\"\"\"
    reviewers = rota["reviewers"]
    chosen = reviewers[rota["next"]]
    return {**rota, "next": rota["next"] + 1}, chosen""",
    variant_one="""def assign(rota, requester):
    \"\"\"Return the rota moved on and the reviewer it names.\"\"\"
    reviewers = rota["reviewers"]
    position = rota["next"] % len(reviewers)
    for _ in range(len(reviewers)):
        chosen = reviewers[position]
        position = (position + 1) % len(reviewers)
        if chosen != requester:
            return {**rota, "next": position}, chosen
    raise ValueError("nobody but the requester is on the rota")""",
    variant_two="""def assign(rota, requester):
    \"\"\"Return the rota moved on and the reviewer it names.\"\"\"
    reviewers = rota["reviewers"]
    start = rota["next"] % len(reviewers)
    order = [(start + step) % len(reviewers) for step in range(len(reviewers))]
    for position in order:
        if reviewers[position] != requester:
            moved = (position + 1) % len(reviewers)
            return {**rota, "next": moved}, reviewers[position]
    raise ValueError("nobody but the requester is on the rota")""",
    variant_three="""def assign(rota, requester):
    \"\"\"Return the rota moved on and the reviewer it names.\"\"\"
    reviewers = rota["reviewers"]
    position = rota["next"]
    while position < len(reviewers) and reviewers[position] == requester:
        position += 1
    return {**rota, "next": position + 1}, reviewers[position]""",
    variant_four="""def assign(rota, requester):
    \"\"\"Return the rota moved on and the reviewer it names.\"\"\"
    reviewers = rota["reviewers"]
    position = rota["next"] % len(reviewers)
    moved = (position + 1) % len(reviewers)
    return {**rota, "next": moved}, reviewers[position]""",
    visible_test=_test_module(
        "review_rota",
        "Published contract for handing out a review.",
        """
def test_the_first_reviewer_on_the_rota() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 0}
    moved, reviewer = assign(rota, "zoe")
    assert reviewer == "ada"
    assert moved["next"] == 1


def test_part_way_along_the_rota() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 1}
    moved, reviewer = assign(rota, "ada")
    assert reviewer == "bo"
    assert moved["next"] == 2


def test_the_caller_rota_is_not_changed() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 0}
    assign(rota, "zoe")
    assert rota["next"] == 0
""",
        imports="from review_rota import assign\n",
    ),
    hidden_test=_test_module(
        "review_rota",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_reviewer_on_the_rota() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 0}
    moved, reviewer = assign(rota, "zoe")
    assert reviewer == "ada"
    assert moved["next"] == 1


def test_the_requester_is_passed_over() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 0}
    moved, reviewer = assign(rota, "ada")
    assert reviewer == "bo"
    assert moved["next"] == 2


def test_the_next_position_comes_back_round() -> None:
    rota = {"reviewers": ["ada", "bo", "cy"], "next": 2}
    moved, reviewer = assign(rota, "zoe")
    assert reviewer == "cy"
    assert moved["next"] == 0
""",
        imports="from review_rota import assign\n",
    ),
)

#: Authored so far. The tuple grows as batches are authored and executed;
#: `corpus_d4.py` reads it rather than a count, so a partially authored corpus reports what it
#: has instead of claiming what it does not.
D4_CALIBRATION_SPECS: tuple[D2TaskSpec, ...] = (
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
    _G013,
    _G014,
    _G015,
    _G016,
    _G017,
    _G018,
    _G019,
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
    _G031,
    _G032,
    _G033,
    _G034,
    _G035,
    _G036,
    _G037,
    _G038,
    _G039,
    _G040,
    _G041,
    _G042,
    _G043,
    _G044,
    _G045,
    _G046,
    _G047,
    _G048,
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
    _G081,
    _G082,
    _G083,
    _G084,
    _G085,
    _G086,
    _G087,
    _G088,
    _G089,
    _G090,
    _G091,
    _G092,
    _G093,
    _G094,
    _G095,
)
