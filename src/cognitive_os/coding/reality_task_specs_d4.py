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

#: Authored so far. The tuple grows as batches are authored and executed; `corpus_d4.py`
#: reads it rather than a count, so a partially authored corpus reports what it has instead
#: of claiming what it does not.
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
)
