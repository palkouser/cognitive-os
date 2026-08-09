"""The Sprint 21D5 calibration corpus: fresh four-candidate groups.

D5 needs a hundred *independent* calibration decisions, and after D4's erratum "independent"
means distinct fitted feature vectors. A transformation of a group does not produce one, so the
only route to a hundred is to author a hundred. This module is that authoring.

The spec shape is `D2TaskSpec`, unchanged, for the reason D4 gave: the catalogue, the template
registry and the campaign already agree about it, and a fifth dataclass with the same fields
under a D5 name would give them a fifth thing to agree about.

Every group obeys the authoring contract D2 froze and D4 re-proved:

- the **baseline** passes the visible suite and fails the hidden one;
- **variant one** and **variant two** repair the contract by materially different routes and
  pass both suites;
- **variant three** fixes the first declared edge case only and **variant four** the second
  only, so both pass the visible suite and fail the hidden one.

Three failure modes account for every authoring defect the predecessors found, and all three
are invisible without executing:

1. *The two hidden tests probe one defect wearing two descriptions.* Then no partial fix repairs
   exactly one, and variants three and four both pass hidden. Every edge-case pair here is
   chosen so that a fix for one leaves the other untouched, and `scripts/corpus_d5.py` is what
   decides whether the choice held.
2. *The baseline is broken so badly it fails its own visible suite.* The defect has to be
   peripheral enough that the ordinary case still works.
3. *A near-clone collision at the level of the task, not the code.* Rewriting a variant cannot
   repair that — the group is withdrawn and a different one authored. With 336 released groups
   the obvious small-function repair space is largely occupied, so every module name and task
   here was checked against the released corpus **before** its bodies were written.

Two constraints come from elsewhere in the sprint. The invariance sample renames identifiers, so
every body binds its names locally and none reaches a name through `getattr`, `globals()` or any
other reflective route, which `correction_source.py` refuses outright. S21D5-022 proves
near-clone separation over every C3, D2, D3, D4 and D5 body.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# ------------------------------------------------------------------ boundary and collections

_G001 = D2TaskSpec(
    template_id="d5_boundary.column_widths",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-column-widths",
    module="column_widths",
    module_doc="Measuring how wide each column of a table has to be.",
    issue=(
        "column_widths() is documented to return the display width of every column across a "
        "table. Callers report that a row carrying more columns than the first one raises, and "
        "that a cell holding anything other than text raises as well."
    ),
    expected=(
        "column_widths(rows) returns one width per column, where a column's width is the widest "
        "rendered cell in it. A row longer than any seen so far extends the result, and a cell "
        "is measured by the text it renders as."
    ),
    baseline_reason=(
        "it sizes the result from the first row alone and measures each cell with len() on the "
        "value itself"
    ),
    edge_cases=(
        "a row with more columns than the first extends the result",
        "a cell that is not text is measured by its rendered width",
    ),
    baseline='''def column_widths(rows):
    """Return the display width of every column across `rows`."""
    widths = [0] * len(rows[0])
    for row in rows:
        for position, cell in enumerate(row):
            widths[position] = max(widths[position], len(cell))
    return widths''',
    variant_one='''def column_widths(rows):
    """Return the display width of every column across `rows`."""
    widths = []
    for row in rows:
        for position, cell in enumerate(row):
            size = len(str(cell))
            if position < len(widths):
                widths[position] = max(widths[position], size)
            else:
                widths.append(size)
    return widths''',
    variant_two='''def column_widths(rows):
    """Return the display width of every column across `rows`."""
    collected = [list(row) for row in rows]
    columns = max((len(row) for row in collected), default=0)
    widths = []
    for position in range(columns):
        sizes = [len(str(row[position])) for row in collected if position < len(row)]
        widths.append(max(sizes, default=0))
    return widths''',
    variant_three='''def column_widths(rows):
    """Return the display width of every column across `rows`."""
    widths = []
    for row in rows:
        for position, cell in enumerate(row):
            while len(widths) <= position:
                widths.append(0)
            widths[position] = max(widths[position], len(cell))
    return widths''',
    variant_four='''def column_widths(rows):
    """Return the display width of every column across `rows`."""
    widths = [0] * len(rows[0])
    for row in rows:
        for position, cell in enumerate(row):
            widths[position] = max(widths[position], len(str(cell)))
    return widths''',
    visible_test=_test_module(
        "column_widths",
        "Published contract for measuring column widths.",
        """
def test_each_column_takes_its_widest_cell() -> None:
    assert column_widths([("id", "name"), ("7", "ada")]) == [2, 4]


def test_a_single_row_is_its_own_width() -> None:
    assert column_widths([("alpha", "b")]) == [5, 1]
""",
        imports="from column_widths import column_widths\n",
    ),
    hidden_test=_test_module(
        "column_widths",
        "The part of the contract the published tests do not state.",
        """
def test_each_column_takes_its_widest_cell() -> None:
    assert column_widths([("id", "name"), ("7", "ada")]) == [2, 4]


def test_a_longer_row_extends_the_result() -> None:
    assert column_widths([("id",), ("7", "ada")]) == [2, 3]


def test_a_cell_that_is_not_text_is_measured_as_rendered() -> None:
    assert column_widths([("id", "n"), (1234, "a")]) == [4, 1]
""",
        imports="from column_widths import column_widths\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G002 = D2TaskSpec(
    template_id="d5_numeric.nearest_rank",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-nearest-rank",
    module="nearest_rank",
    module_doc="Reading a percentile off a series by nearest rank.",
    issue=(
        "percentile() is documented to return the nearest-rank percentile of a series. Callers "
        "report that a fraction landing between two ranks returns the lower neighbour instead "
        "of the upper one, and that an empty series raises IndexError instead of a clear error."
    ),
    expected=(
        "percentile(values, fraction) sorts the series and returns the value at the ceiling of "
        "fraction times the count, counting from one. An empty series raises ValueError."
    ),
    baseline_reason=(
        "it truncates the rank instead of taking its ceiling and indexes an empty list"
    ),
    edge_cases=(
        "a fraction landing between two ranks takes the upper one",
        "an empty series raises ValueError",
    ),
    imports="import math\n",
    baseline='''def percentile(values, fraction):
    """Return the nearest-rank percentile of `values`."""
    ordered = sorted(values)
    rank = int(fraction * len(ordered))
    if rank < 1:
        rank = 1
    return ordered[rank - 1]''',
    variant_one='''def percentile(values, fraction):
    """Return the nearest-rank percentile of `values`."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("an empty series has no percentile")
    rank = math.ceil(fraction * len(ordered))
    if rank < 1:
        rank = 1
    return ordered[rank - 1]''',
    variant_two='''def percentile(values, fraction):
    """Return the nearest-rank percentile of `values`."""
    ordered = sorted(values)
    total = len(ordered)
    if total == 0:
        raise ValueError("an empty series has no percentile")
    exact = fraction * total
    rank = int(exact) + (1 if exact > int(exact) else 0)
    return ordered[max(rank, 1) - 1]''',
    variant_three='''def percentile(values, fraction):
    """Return the nearest-rank percentile of `values`."""
    ordered = sorted(values)
    rank = math.ceil(fraction * len(ordered))
    if rank < 1:
        rank = 1
    return ordered[rank - 1]''',
    variant_four='''def percentile(values, fraction):
    """Return the nearest-rank percentile of `values`."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("an empty series has no percentile")
    rank = int(fraction * len(ordered))
    if rank < 1:
        rank = 1
    return ordered[rank - 1]''',
    visible_test=_test_module(
        "nearest_rank",
        "Published contract for reading a percentile.",
        """
def test_a_fraction_landing_on_a_rank_takes_that_rank() -> None:
    assert percentile([4, 1, 3, 2], 0.75) == 3


def test_the_lowest_fraction_takes_the_smallest_value() -> None:
    assert percentile([4, 1, 3, 2], 0.25) == 1
""",
        imports="from nearest_rank import percentile\n",
    ),
    hidden_test=_test_module(
        "nearest_rank",
        "The part of the contract the published tests do not state.",
        """
import pytest

from nearest_rank import percentile


def test_a_fraction_landing_on_a_rank_takes_that_rank() -> None:
    assert percentile([4, 1, 3, 2], 0.75) == 3


def test_a_fraction_between_two_ranks_takes_the_upper_one() -> None:
    assert percentile([4, 1, 3, 2], 0.3) == 2


def test_an_empty_series_is_refused() -> None:
    with pytest.raises(ValueError):
        percentile([], 0.5)
""",
    ),
)

# ------------------------------------------------------------------------ parsing validation

_G003 = D2TaskSpec(
    template_id="d5_parsing.csv_quoting",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-csv-quoting",
    module="csv_quoting",
    module_doc="Quoting a single field on the way out to CSV.",
    issue=(
        "quote_field() is documented to quote a CSV field whenever quoting is needed. Callers "
        "report that a field already containing a quote character comes back with its quotes "
        "unescaped, and that a field padded with spaces comes back unquoted so the padding is "
        "lost on the next read."
    ),
    expected=(
        "quote_field(value) returns the field unchanged when it needs no quoting, and otherwise "
        "wraps it in double quotes. A field is quoted when it contains a comma, a double quote, "
        "a newline, or leading or trailing whitespace, and every contained double quote is "
        "doubled."
    ),
    baseline_reason=(
        "it decides on commas and newlines alone and copies the value into the quotes verbatim"
    ),
    edge_cases=(
        "a contained double quote is doubled inside the quotes",
        "leading or trailing whitespace forces quoting",
    ),
    baseline='''def quote_field(value):
    """Return `value` quoted for CSV if it needs to be."""
    if "," in value or "\\n" in value:
        return "".join(('"', value, '"'))
    return value''',
    variant_one='''def quote_field(value):
    """Return `value` quoted for CSV if it needs to be."""
    needs_quotes = any(marker in value for marker in (",", '"', "\\n"))
    if not needs_quotes and value.strip() != value:
        needs_quotes = True
    if not needs_quotes:
        return value
    return "".join(('"', value.replace('"', '""'), '"'))''',
    variant_two='''def quote_field(value):
    """Return `value` quoted for CSV if it needs to be."""
    special = {",", '"', "\\n"}
    trimmed = value.strip()
    if not (special & set(value)) and trimmed == value:
        return value
    escaped = "".join('""' if character == '"' else character for character in value)
    return "".join(('"', escaped, '"'))''',
    variant_three='''def quote_field(value):
    """Return `value` quoted for CSV if it needs to be."""
    if "," in value or "\\n" in value or '"' in value:
        return "".join(('"', value.replace('"', '""'), '"'))
    return value''',
    variant_four='''def quote_field(value):
    """Return `value` quoted for CSV if it needs to be."""
    if "," in value or "\\n" in value or value.strip() != value:
        return "".join(('"', value, '"'))
    return value''',
    visible_test=_test_module(
        "csv_quoting",
        "Published contract for quoting a CSV field.",
        """
def test_a_plain_field_is_returned_unchanged() -> None:
    assert quote_field("ada") == "ada"


def test_a_field_with_a_comma_is_quoted() -> None:
    assert quote_field("ada,lovelace") == '"ada,lovelace"'
""",
        imports="from csv_quoting import quote_field\n",
    ),
    hidden_test=_test_module(
        "csv_quoting",
        "The part of the contract the published tests do not state.",
        """
def test_a_plain_field_is_returned_unchanged() -> None:
    assert quote_field("ada") == "ada"


def test_a_contained_quote_is_doubled() -> None:
    assert quote_field('a"b') == '"a""b"'


def test_padding_forces_quoting() -> None:
    assert quote_field(" ada ") == '" ada "'
""",
        imports="from csv_quoting import quote_field\n",
    ),
)

# ------------------------------------------------------------------------ data transformation

_G004 = D2TaskSpec(
    template_id="d5_transform.key_difference",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-key-difference",
    module="key_difference",
    module_doc="Comparing two mappings key by key.",
    issue=(
        "difference() is documented to report which keys were added, removed and changed "
        "between two mappings. Callers report that the three lists come back in whatever order "
        "the mappings happened to be built in, and that a key whose value became None is "
        "reported as removed rather than changed."
    ),
    expected=(
        "difference(before, after) returns a mapping with sorted 'added', 'removed' and "
        "'changed' key lists. A key counts as changed when it is present in both and its values "
        "differ, whatever those values are; presence is decided by the keys alone."
    ),
    baseline_reason=(
        "it reports keys in iteration order and decides presence by truthiness of the value"
    ),
    edge_cases=(
        "the three lists are sorted regardless of insertion order",
        "a key whose value became None is changed, not removed",
    ),
    baseline='''def difference(before, after):
    """Report the added, removed and changed keys between two mappings."""
    added = [key for key in after if key not in before]
    removed = [key for key in before if not after.get(key)]
    changed = [
        key for key in before if after.get(key) is not None and after[key] != before[key]
    ]
    return {"added": added, "removed": removed, "changed": changed}''',
    variant_one='''def difference(before, after):
    """Report the added, removed and changed keys between two mappings."""
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if key not in after)
    changed = sorted(
        key for key in before if key in after and after[key] != before[key]
    )
    return {"added": added, "removed": removed, "changed": changed}''',
    variant_two='''def difference(before, after):
    """Report the added, removed and changed keys between two mappings."""
    left = set(before)
    right = set(after)
    shared = left & right
    return {
        "added": sorted(right - left),
        "removed": sorted(left - right),
        "changed": sorted(key for key in shared if before[key] != after[key]),
    }''',
    variant_three='''def difference(before, after):
    """Report the added, removed and changed keys between two mappings."""
    added = sorted(key for key in after if key not in before)
    removed = sorted(key for key in before if not after.get(key))
    changed = sorted(
        key for key in before if after.get(key) is not None and after[key] != before[key]
    )
    return {"added": added, "removed": removed, "changed": changed}''',
    variant_four='''def difference(before, after):
    """Report the added, removed and changed keys between two mappings."""
    added = [key for key in after if key not in before]
    removed = [key for key in before if key not in after]
    changed = [key for key in before if key in after and after[key] != before[key]]
    return {"added": added, "removed": removed, "changed": changed}''',
    visible_test=_test_module(
        "key_difference",
        "Published contract for comparing two mappings.",
        """
def test_an_added_key_is_reported() -> None:
    assert difference({"a": 1}, {"a": 1, "b": 2})["added"] == ["b"]


def test_a_changed_value_is_reported() -> None:
    assert difference({"a": 1}, {"a": 2})["changed"] == ["a"]
""",
        imports="from key_difference import difference\n",
    ),
    hidden_test=_test_module(
        "key_difference",
        "The part of the contract the published tests do not state.",
        """
def test_an_added_key_is_reported() -> None:
    assert difference({"a": 1}, {"a": 1, "b": 2})["added"] == ["b"]


def test_the_lists_are_sorted() -> None:
    report = difference({"a": 1}, {"a": 1, "z": 1, "b": 1})
    assert report["added"] == ["b", "z"]


def test_a_value_that_became_none_is_changed() -> None:
    report = difference({"a": 1}, {"a": None})
    assert report["changed"] == ["a"]
    assert report["removed"] == []
""",
        imports="from key_difference import difference\n",
    ),
)

# ------------------------------------------------------------------------ state idempotency

_G005 = D2TaskSpec(
    template_id="d5_state.partition_offsets",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-partition-offsets",
    module="partition_offsets",
    module_doc="Advancing a per-partition read offset.",
    issue=(
        "advance() is documented to move each partition's offset forward as workers report "
        "progress. Callers report that a late report from a slow worker drags an offset "
        "backwards, and that a partition nobody has reported before is dropped instead of "
        "being recorded."
    ),
    expected=(
        "advance(current, reported) returns a new mapping in which every partition's offset is "
        "the larger of the two. A partition seen only in the reports is added at its reported "
        "offset, and the mapping passed in is not modified."
    ),
    baseline_reason="it overwrites each known offset with the reported one and skips unknown ones",
    edge_cases=(
        "a report lower than the recorded offset does not move it backwards",
        "a partition absent from the current mapping is added",
    ),
    baseline='''def advance(current, reported):
    """Return the offsets after applying `reported` to `current`."""
    updated = dict(current)
    for partition, offset in reported.items():
        if partition in updated:
            updated[partition] = offset
    return updated''',
    variant_one='''def advance(current, reported):
    """Return the offsets after applying `reported` to `current`."""
    updated = dict(current)
    for partition, offset in reported.items():
        if partition in updated:
            updated[partition] = max(updated[partition], offset)
        else:
            updated[partition] = offset
    return updated''',
    variant_two='''def advance(current, reported):
    """Return the offsets after applying `reported` to `current`."""
    partitions = set(current) | set(reported)
    return {
        partition: max(
            current.get(partition, reported.get(partition, 0)),
            reported.get(partition, current.get(partition, 0)),
        )
        for partition in partitions
    }''',
    variant_three='''def advance(current, reported):
    """Return the offsets after applying `reported` to `current`."""
    updated = dict(current)
    for partition, offset in reported.items():
        if partition in updated:
            updated[partition] = max(updated[partition], offset)
    return updated''',
    variant_four='''def advance(current, reported):
    """Return the offsets after applying `reported` to `current`."""
    updated = dict(current)
    for partition, offset in reported.items():
        updated[partition] = offset
    return updated''',
    visible_test=_test_module(
        "partition_offsets",
        "Published contract for advancing read offsets.",
        """
def test_a_higher_report_moves_the_offset_forward() -> None:
    assert advance({"a": 4}, {"a": 9}) == {"a": 9}


def test_an_unreported_partition_keeps_its_offset() -> None:
    assert advance({"a": 4, "b": 2}, {"a": 5}) == {"a": 5, "b": 2}
""",
        imports="from partition_offsets import advance\n",
    ),
    hidden_test=_test_module(
        "partition_offsets",
        "The part of the contract the published tests do not state.",
        """
def test_a_higher_report_moves_the_offset_forward() -> None:
    assert advance({"a": 4}, {"a": 9}) == {"a": 9}


def test_a_late_report_does_not_move_the_offset_backwards() -> None:
    assert advance({"a": 9}, {"a": 4}) == {"a": 9}


def test_an_unknown_partition_is_added() -> None:
    assert advance({"a": 4}, {"b": 7}) == {"a": 4, "b": 7}
""",
        imports="from partition_offsets import advance\n",
    ),
)

# ---------------------------------------------------------------------------- error handling

_G006 = D2TaskSpec(
    template_id="d5_error.batch_outcome",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-batch-outcome",
    module="batch_outcome",
    module_doc="Classifying how a batch of results turned out.",
    issue=(
        "classify() is documented to describe a batch as succeeded, partial or failed. Callers "
        "report that a batch in which everything failed comes back as partial, and that an "
        "empty batch comes back as failed when there was nothing to fail."
    ),
    expected=(
        "classify(results) returns 'succeeded' when every result is ok, 'failed' when none is, "
        "and 'partial' when some are and some are not. An empty batch succeeded, because "
        "nothing in it failed."
    ),
    baseline_reason=(
        "it calls anything that is not wholly successful partial, and treats the empty batch as "
        "the absence of success"
    ),
    edge_cases=(
        "a batch in which nothing succeeded is failed, not partial",
        "an empty batch succeeded",
    ),
    baseline='''def classify(results):
    """Return how the batch turned out."""
    successes = [item for item in results if item]
    if len(successes) == len(results) and successes:
        return "succeeded"
    return "partial"''',
    variant_one='''def classify(results):
    """Return how the batch turned out."""
    collected = list(results)
    successes = [item for item in collected if item]
    if len(successes) == len(collected):
        return "succeeded"
    if not successes:
        return "failed"
    return "partial"''',
    variant_two='''def classify(results):
    """Return how the batch turned out."""
    collected = list(results)
    failures = [item for item in collected if not item]
    if not failures:
        return "succeeded"
    if len(failures) == len(collected):
        return "failed"
    return "partial"''',
    variant_three='''def classify(results):
    """Return how the batch turned out."""
    collected = list(results)
    successes = [item for item in collected if item]
    if len(successes) == len(collected) and successes:
        return "succeeded"
    if not successes:
        return "failed"
    return "partial"''',
    variant_four='''def classify(results):
    """Return how the batch turned out."""
    collected = list(results)
    successes = [item for item in collected if item]
    if len(successes) == len(collected):
        return "succeeded"
    return "partial"''',
    visible_test=_test_module(
        "batch_outcome",
        "Published contract for classifying a batch.",
        """
def test_a_batch_where_everything_worked_succeeded() -> None:
    assert classify([True, True]) == "succeeded"


def test_a_batch_with_one_failure_is_partial() -> None:
    assert classify([True, False]) == "partial"
""",
        imports="from batch_outcome import classify\n",
    ),
    hidden_test=_test_module(
        "batch_outcome",
        "The part of the contract the published tests do not state.",
        """
def test_a_batch_with_one_failure_is_partial() -> None:
    assert classify([True, False]) == "partial"


def test_a_batch_where_nothing_succeeded_failed() -> None:
    assert classify([False, False]) == "failed"


def test_an_empty_batch_succeeded() -> None:
    assert classify([]) == "succeeded"
""",
        imports="from batch_outcome import classify\n",
    ),
)


# ------------------------------------------------------------------ batch two

_G007 = D2TaskSpec(
    template_id="d5_boundary.round_robin",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-round-robin",
    module="round_robin",
    module_doc="Taking turns across several queues.",
    issue=(
        "interleave() is documented to take one item from each queue in turn until every queue "
        "is empty. Callers report that it raises as soon as one queue is shorter than the "
        "first, and that calling it with no queues at all raises instead of returning nothing."
    ),
    expected=(
        "interleave(queues) returns the items taken one per queue per round, in queue order, "
        "continuing until every queue is exhausted. Queues of different lengths are allowed, "
        "and no queues at all yields an empty list."
    ),
    baseline_reason=(
        "it takes the number of rounds from the first queue and indexes the rest blindly"
    ),
    edge_cases=(
        "queues of different lengths keep rotating after the shortest is exhausted",
        "no queues at all yields an empty list",
    ),
    baseline='''def interleave(queues):
    """Return the items of `queues` taken one per queue per round."""
    taken = []
    rounds = len(queues[0])
    for index in range(rounds):
        for queue in queues:
            taken.append(queue[index])
    return taken''',
    variant_one='''def interleave(queues):
    """Return the items of `queues` taken one per queue per round."""
    taken = []
    rounds = max((len(queue) for queue in queues), default=0)
    for index in range(rounds):
        for queue in queues:
            if index < len(queue):
                taken.append(queue[index])
    return taken''',
    variant_two='''def interleave(queues):
    """Return the items of `queues` taken one per queue per round."""
    pending = [list(queue) for queue in queues]
    taken = []
    while any(pending):
        for queue in pending:
            if queue:
                taken.append(queue.pop(0))
    return taken''',
    variant_three='''def interleave(queues):
    """Return the items of `queues` taken one per queue per round."""
    taken = []
    rounds = max(len(queue) for queue in queues)
    for index in range(rounds):
        for queue in queues:
            if index < len(queue):
                taken.append(queue[index])
    return taken''',
    variant_four='''def interleave(queues):
    """Return the items of `queues` taken one per queue per round."""
    if not queues:
        return []
    taken = []
    rounds = len(queues[0])
    for index in range(rounds):
        for queue in queues:
            taken.append(queue[index])
    return taken''',
    visible_test=_test_module(
        "round_robin",
        "Published contract for taking turns across queues.",
        """
def test_two_queues_of_equal_length_alternate() -> None:
    assert interleave([[1, 3], [2, 4]]) == [1, 2, 3, 4]


def test_a_single_queue_comes_back_in_order() -> None:
    assert interleave([[1, 2, 3]]) == [1, 2, 3]
""",
        imports="from round_robin import interleave\n",
    ),
    hidden_test=_test_module(
        "round_robin",
        "The part of the contract the published tests do not state.",
        """
def test_two_queues_of_equal_length_alternate() -> None:
    assert interleave([[1, 3], [2, 4]]) == [1, 2, 3, 4]


def test_a_shorter_queue_drops_out_of_the_rotation() -> None:
    assert interleave([[1, 3, 5], [2]]) == [1, 2, 3, 5]


def test_no_queues_yields_nothing() -> None:
    assert interleave([]) == []
""",
        imports="from round_robin import interleave\n",
    ),
)

_G008 = D2TaskSpec(
    template_id="d5_boundary.bin_packing",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-bin-packing",
    module="bin_packing",
    module_doc="Packing weights into bins of a fixed capacity.",
    issue=(
        "pack() is documented to fill each bin up to its capacity before opening the next one. "
        "Callers report that a set of weights adding up to exactly the capacity is split across "
        "two bins, and that a weight nobody could ever pack is accepted into a bin of its own."
    ),
    expected=(
        "pack(weights, capacity) returns bins in order, filling each bin while the next weight "
        "still fits. A bin may be filled exactly to capacity, and a weight larger than the "
        "capacity raises ValueError because no bin could hold it."
    ),
    baseline_reason=(
        "it compares the running total with a strict less-than and never checks the weight"
    ),
    edge_cases=(
        "a bin may be filled exactly to capacity",
        "a weight larger than the capacity raises ValueError",
    ),
    baseline='''def pack(weights, capacity):
    """Return `weights` packed into bins of at most `capacity`."""
    bins = []
    current = []
    total = 0
    for weight in weights:
        if total + weight < capacity:
            current.append(weight)
            total += weight
        else:
            bins.append(current)
            current = [weight]
            total = weight
    bins.append(current)
    return bins''',
    variant_one='''def pack(weights, capacity):
    """Return `weights` packed into bins of at most `capacity`."""
    bins = []
    current = []
    total = 0
    for weight in weights:
        if weight > capacity:
            raise ValueError("a weight larger than the capacity can never be packed")
        if total + weight <= capacity:
            current.append(weight)
            total += weight
        else:
            bins.append(current)
            current = [weight]
            total = weight
    bins.append(current)
    return bins''',
    variant_two='''def pack(weights, capacity):
    """Return `weights` packed into bins of at most `capacity`."""
    collected = list(weights)
    for weight in collected:
        if weight > capacity:
            raise ValueError("a weight larger than the capacity can never be packed")
    bins = [[]]
    for weight in collected:
        if sum(bins[-1]) + weight > capacity:
            bins.append([])
        bins[-1].append(weight)
    return bins''',
    variant_three='''def pack(weights, capacity):
    """Return `weights` packed into bins of at most `capacity`."""
    bins = []
    current = []
    total = 0
    for weight in weights:
        if total + weight <= capacity:
            current.append(weight)
            total += weight
        else:
            bins.append(current)
            current = [weight]
            total = weight
    bins.append(current)
    return bins''',
    variant_four='''def pack(weights, capacity):
    """Return `weights` packed into bins of at most `capacity`."""
    bins = []
    current = []
    total = 0
    for weight in weights:
        if weight > capacity:
            raise ValueError("a weight larger than the capacity can never be packed")
        if total + weight < capacity:
            current.append(weight)
            total += weight
        else:
            bins.append(current)
            current = [weight]
            total = weight
    bins.append(current)
    return bins''',
    visible_test=_test_module(
        "bin_packing",
        "Published contract for packing weights into bins.",
        """
def test_weights_that_fit_share_one_bin() -> None:
    assert pack([1, 2], 6) == [[1, 2]]


def test_a_weight_that_does_not_fit_opens_the_next_bin() -> None:
    assert pack([4, 5], 6) == [[4], [5]]
""",
        imports="from bin_packing import pack\n",
    ),
    hidden_test=_test_module(
        "bin_packing",
        "The part of the contract the published tests do not state.",
        """
import pytest

from bin_packing import pack


def test_weights_that_fit_share_one_bin() -> None:
    assert pack([1, 2], 6) == [[1, 2]]


def test_a_bin_may_be_filled_exactly() -> None:
    assert pack([3, 3], 6) == [[3, 3]]


def test_a_weight_larger_than_the_capacity_is_refused() -> None:
    with pytest.raises(ValueError):
        pack([7], 6)
""",
    ),
)

_G009 = D2TaskSpec(
    template_id="d5_parsing.ipv4_octets",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-ipv4-octets",
    module="ipv4_octets",
    module_doc="Reading a dotted-quad address into its four octets.",
    issue=(
        "parse_address() is documented to read a dotted-quad address and refuse anything that "
        "is not one. Callers report that an octet written with a leading zero is accepted, and "
        "that an octet larger than any octet can be is accepted too."
    ),
    expected=(
        "parse_address(text) returns the four octets as integers. An address has exactly four "
        "parts, each a decimal number from 0 to 255 written without a leading zero; anything "
        "else raises ValueError."
    ),
    baseline_reason="it converts each part with int() and checks nothing beyond the part count",
    edge_cases=(
        "an octet written with a leading zero is refused",
        "an octet larger than 255 is refused",
    ),
    baseline='''def parse_address(text):
    """Return the four octets of the dotted-quad `text`."""
    parts = text.split(".")
    if len(parts) != 4:
        raise ValueError("an address has four octets")
    return tuple(int(part) for part in parts)''',
    variant_one='''def parse_address(text):
    """Return the four octets of the dotted-quad `text`."""
    parts = text.split(".")
    if len(parts) != 4:
        raise ValueError("an address has four octets")
    octets = []
    for part in parts:
        if len(part) > 1 and part.startswith("0"):
            raise ValueError("an octet is written without a leading zero")
        value = int(part)
        if value > 255:
            raise ValueError("an octet is at most 255")
        octets.append(value)
    return tuple(octets)''',
    variant_two='''def parse_address(text):
    """Return the four octets of the dotted-quad `text`."""
    parts = text.split(".")
    if len(parts) != 4:
        raise ValueError("an address has four octets")
    for part in parts:
        if part != str(int(part)):
            raise ValueError("an octet is written without a leading zero")
    octets = tuple(int(part) for part in parts)
    if any(octet > 255 for octet in octets):
        raise ValueError("an octet is at most 255")
    return octets''',
    variant_three='''def parse_address(text):
    """Return the four octets of the dotted-quad `text`."""
    parts = text.split(".")
    if len(parts) != 4:
        raise ValueError("an address has four octets")
    for part in parts:
        if len(part) > 1 and part.startswith("0"):
            raise ValueError("an octet is written without a leading zero")
    return tuple(int(part) for part in parts)''',
    variant_four='''def parse_address(text):
    """Return the four octets of the dotted-quad `text`."""
    parts = text.split(".")
    if len(parts) != 4:
        raise ValueError("an address has four octets")
    octets = tuple(int(part) for part in parts)
    if any(octet > 255 for octet in octets):
        raise ValueError("an octet is at most 255")
    return octets''',
    visible_test=_test_module(
        "ipv4_octets",
        "Published contract for reading a dotted-quad address.",
        """
import pytest

from ipv4_octets import parse_address


def test_a_plain_address_reads_as_four_octets() -> None:
    assert parse_address("10.0.0.1") == (10, 0, 0, 1)


def test_an_address_with_three_parts_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_address("10.0.1")
""",
    ),
    hidden_test=_test_module(
        "ipv4_octets",
        "The part of the contract the published tests do not state.",
        """
import pytest

from ipv4_octets import parse_address


def test_a_plain_address_reads_as_four_octets() -> None:
    assert parse_address("10.0.0.1") == (10, 0, 0, 1)


def test_a_leading_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_address("10.01.0.1")


def test_an_octet_above_the_limit_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_address("10.0.0.999")
""",
    ),
)

_G010 = D2TaskSpec(
    template_id="d5_parsing.glob_match",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-glob-match",
    module="glob_match",
    module_doc="Matching a name against a shell-style pattern.",
    issue=(
        "matches() is documented to decide whether a name matches a pattern in which '*' stands "
        "for any run of characters and '?' for exactly one. Callers report that a pattern "
        "matches a name that merely starts with it, and that a full stop in the pattern matches "
        "any character instead of a full stop."
    ),
    expected=(
        "matches(pattern, name) is true when the whole name matches the whole pattern. '*' "
        "stands for any run of characters including none, '?' for exactly one, and every other "
        "character stands for itself."
    ),
    baseline_reason=(
        "it rewrites the wildcards into a regular expression without escaping the rest and "
        "matches from the start rather than over the whole name"
    ),
    imports="import re\n",
    baseline='''def matches(pattern, name):
    """Return whether `name` matches the shell-style `pattern`."""
    expression = pattern.replace("*", ".*").replace("?", ".")
    return re.match(expression, name) is not None''',
    variant_one='''def matches(pattern, name):
    """Return whether `name` matches the shell-style `pattern`."""
    expression = re.escape(pattern).replace(r"\\*", ".*").replace(r"\\?", ".")
    return re.fullmatch(expression, name) is not None''',
    variant_two='''def matches(pattern, name):
    """Return whether `name` matches the shell-style `pattern`."""
    pieces = []
    for character in pattern:
        if character == "*":
            pieces.append(".*")
        elif character == "?":
            pieces.append(".")
        else:
            pieces.append(re.escape(character))
    return re.match("".join(pieces) + r"\\Z", name) is not None''',
    variant_three='''def matches(pattern, name):
    """Return whether `name` matches the shell-style `pattern`."""
    expression = pattern.replace("*", ".*").replace("?", ".")
    return re.fullmatch(expression, name) is not None''',
    variant_four='''def matches(pattern, name):
    """Return whether `name` matches the shell-style `pattern`."""
    expression = re.escape(pattern).replace(r"\\*", ".*").replace(r"\\?", ".")
    return re.match(expression, name) is not None''',
    edge_cases=(
        "the pattern has to match the whole name, not just its start",
        "a full stop in the pattern stands for a full stop",
    ),
    visible_test=_test_module(
        "glob_match",
        "Published contract for shell-style matching.",
        """
def test_a_star_stands_for_any_run() -> None:
    assert matches("a*c", "abbbc") is True


def test_a_question_mark_stands_for_one_character() -> None:
    assert matches("a?c", "abc") is True
""",
        imports="from glob_match import matches\n",
    ),
    hidden_test=_test_module(
        "glob_match",
        "The part of the contract the published tests do not state.",
        """
def test_a_star_stands_for_any_run() -> None:
    assert matches("a*c", "abbbc") is True


def test_a_prefix_is_not_a_match() -> None:
    assert matches("ab", "abc") is False


def test_a_full_stop_is_literal() -> None:
    assert matches("a.c", "abc") is False
""",
        imports="from glob_match import matches\n",
    ),
)

_G011 = D2TaskSpec(
    template_id="d5_numeric.luhn_check",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-luhn-check",
    module="luhn_check",
    module_doc="Checking a number against its Luhn check digit.",
    issue=(
        "is_valid() is documented to check a number against its trailing Luhn check digit. "
        "Callers report that a number written with grouping separators raises instead of being "
        "checked, and that an empty string is reported as a valid number."
    ),
    expected=(
        "is_valid(number) doubles every second digit from the right, subtracting nine from any "
        "result above nine, and is true when the total is a multiple of ten. Spaces and hyphens "
        "are grouping and are ignored. A number with no digits at all is not valid."
    ),
    baseline_reason=(
        "it converts every character to a digit and calls a total of zero a multiple of ten"
    ),
    edge_cases=(
        "spaces and hyphens are ignored",
        "a number with no digits is not valid",
    ),
    baseline='''def is_valid(number):
    """Return whether `number` carries a valid Luhn check digit."""
    total = 0
    for position, character in enumerate(reversed(number)):
        digit = int(character)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0''',
    variant_one='''def is_valid(number):
    """Return whether `number` carries a valid Luhn check digit."""
    digits = [character for character in number if character not in " -"]
    if not digits:
        return False
    total = 0
    for position, character in enumerate(reversed(digits)):
        digit = int(character)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0''',
    variant_two='''def is_valid(number):
    """Return whether `number` carries a valid Luhn check digit."""
    digits = [int(character) for character in number if character.isdigit()]
    if len(digits) == 0:
        return False
    running = 0
    for position, digit in enumerate(digits[::-1]):
        value = digit * 2 if position % 2 else digit
        running += value - 9 if value > 9 else value
    return running % 10 == 0''',
    variant_three='''def is_valid(number):
    """Return whether `number` carries a valid Luhn check digit."""
    digits = [character for character in number if character not in " -"]
    total = 0
    for position, character in enumerate(reversed(digits)):
        digit = int(character)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0''',
    variant_four='''def is_valid(number):
    """Return whether `number` carries a valid Luhn check digit."""
    if not number:
        return False
    total = 0
    for position, character in enumerate(reversed(number)):
        digit = int(character)
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0''',
    visible_test=_test_module(
        "luhn_check",
        "Published contract for checking a Luhn number.",
        """
def test_a_valid_number_checks_out() -> None:
    assert is_valid("79927398713") is True


def test_a_number_with_a_wrong_check_digit_does_not() -> None:
    assert is_valid("79927398710") is False
""",
        imports="from luhn_check import is_valid\n",
    ),
    hidden_test=_test_module(
        "luhn_check",
        "The part of the contract the published tests do not state.",
        """
def test_a_valid_number_checks_out() -> None:
    assert is_valid("79927398713") is True


def test_grouping_separators_are_ignored() -> None:
    assert is_valid("7992-7398-713") is True


def test_a_number_with_no_digits_is_not_valid() -> None:
    assert is_valid("") is False
""",
        imports="from luhn_check import is_valid\n",
    ),
)

_G012 = D2TaskSpec(
    template_id="d5_numeric.significant_figures",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-significant-figures",
    module="significant_figures",
    module_doc="Rounding a measurement to a number of significant figures.",
    issue=(
        "round_to() is documented to round a measurement to a given number of significant "
        "figures. Callers report that rounding zero raises a maths domain error, and that "
        "rounding a negative measurement raises the same way."
    ),
    expected=(
        "round_to(value, figures) rounds `value` so that `figures` significant digits remain. "
        "Zero rounds to zero whatever the figure count, and a negative value keeps its sign."
    ),
    baseline_reason=(
        "it takes the base-ten logarithm of the value itself, which zero and negatives have no"
    ),
    imports="import math\n",
    edge_cases=(
        "zero rounds to zero rather than raising",
        "a negative value keeps its sign rather than raising",
    ),
    baseline='''def round_to(value, figures):
    """Return `value` rounded to `figures` significant figures."""
    exponent = math.floor(math.log10(value))
    return round(value, figures - 1 - exponent)''',
    variant_one='''def round_to(value, figures):
    """Return `value` rounded to `figures` significant figures."""
    if value == 0:
        return 0.0
    exponent = math.floor(math.log10(abs(value)))
    return round(value, figures - 1 - exponent)''',
    variant_two='''def round_to(value, figures):
    """Return `value` rounded to `figures` significant figures."""
    if not value:
        return 0.0
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    exponent = math.floor(math.log10(magnitude))
    return sign * round(magnitude, figures - 1 - exponent)''',
    variant_three='''def round_to(value, figures):
    """Return `value` rounded to `figures` significant figures."""
    if value == 0:
        return 0.0
    exponent = math.floor(math.log10(value))
    return round(value, figures - 1 - exponent)''',
    variant_four='''def round_to(value, figures):
    """Return `value` rounded to `figures` significant figures."""
    sign = -1 if value < 0 else 1
    exponent = math.floor(math.log10(abs(value)))
    return sign * round(abs(value), figures - 1 - exponent)''',
    visible_test=_test_module(
        "significant_figures",
        "Published contract for rounding to significant figures.",
        """
def test_a_large_measurement_keeps_two_figures() -> None:
    assert round_to(1234, 2) == 1200


def test_a_small_measurement_keeps_two_figures() -> None:
    assert round_to(0.04567, 2) == 0.046
""",
        imports="from significant_figures import round_to\n",
    ),
    hidden_test=_test_module(
        "significant_figures",
        "The part of the contract the published tests do not state.",
        """
def test_a_large_measurement_keeps_two_figures() -> None:
    assert round_to(1234, 2) == 1200


def test_zero_rounds_to_zero() -> None:
    assert round_to(0, 3) == 0


def test_a_negative_measurement_keeps_its_sign() -> None:
    assert round_to(-1234, 2) == -1200
""",
        imports="from significant_figures import round_to\n",
    ),
)

_G013 = D2TaskSpec(
    template_id="d5_transform.value_histogram",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-value-histogram",
    module="value_histogram",
    module_doc="Counting readings into equal-width buckets.",
    issue=(
        "histogram() is documented to count readings into a fixed number of equal-width "
        "buckets. Callers report that a series in which every reading is the same divides by "
        "zero, and that an empty series raises instead of reporting no readings anywhere."
    ),
    expected=(
        "histogram(readings, buckets) returns one count per bucket, spanning the smallest to "
        "the largest reading. The largest reading belongs to the last bucket. When every "
        "reading is the same they all fall in the first bucket, and an empty series counts "
        "nothing anywhere."
    ),
    baseline_reason=(
        "it takes the bucket width from a range it never checks and reads min() of an empty series"
    ),
    edge_cases=(
        "a series in which every reading is the same counts them all in the first bucket",
        "an empty series counts nothing anywhere",
    ),
    baseline='''def histogram(readings, buckets):
    """Return the count of `readings` in each of `buckets` equal-width buckets."""
    low = min(readings)
    high = max(readings)
    counts = [0] * buckets
    width = (high - low) / buckets
    for reading in readings:
        index = int((reading - low) / width)
        if index >= buckets:
            index = buckets - 1
        counts[index] += 1
    return counts''',
    variant_one='''def histogram(readings, buckets):
    """Return the count of `readings` in each of `buckets` equal-width buckets."""
    counts = [0] * buckets
    if not readings:
        return counts
    low = min(readings)
    high = max(readings)
    if high == low:
        counts[0] = len(readings)
        return counts
    width = (high - low) / buckets
    for reading in readings:
        index = int((reading - low) / width)
        counts[min(index, buckets - 1)] += 1
    return counts''',
    variant_two='''def histogram(readings, buckets):
    """Return the count of `readings` in each of `buckets` equal-width buckets."""
    collected = list(readings)
    counts = [0] * buckets
    if len(collected) == 0:
        return counts
    low, high = min(collected), max(collected)
    span = high - low
    for reading in collected:
        if span == 0:
            counts[0] += 1
            continue
        position = (reading - low) / span * buckets
        counts[min(int(position), buckets - 1)] += 1
    return counts''',
    variant_three='''def histogram(readings, buckets):
    """Return the count of `readings` in each of `buckets` equal-width buckets."""
    low = min(readings)
    high = max(readings)
    counts = [0] * buckets
    if high == low:
        counts[0] = len(readings)
        return counts
    width = (high - low) / buckets
    for reading in readings:
        index = int((reading - low) / width)
        counts[min(index, buckets - 1)] += 1
    return counts''',
    variant_four='''def histogram(readings, buckets):
    """Return the count of `readings` in each of `buckets` equal-width buckets."""
    counts = [0] * buckets
    if not readings:
        return counts
    low = min(readings)
    high = max(readings)
    width = (high - low) / buckets
    for reading in readings:
        index = int((reading - low) / width)
        counts[min(index, buckets - 1)] += 1
    return counts''',
    visible_test=_test_module(
        "value_histogram",
        "Published contract for counting readings into buckets.",
        """
def test_readings_spread_across_two_buckets() -> None:
    assert histogram([1, 2, 3, 4], 2) == [2, 2]


def test_the_largest_reading_lands_in_the_last_bucket() -> None:
    assert histogram([0, 10], 2) == [1, 1]
""",
        imports="from value_histogram import histogram\n",
    ),
    hidden_test=_test_module(
        "value_histogram",
        "The part of the contract the published tests do not state.",
        """
def test_readings_spread_across_two_buckets() -> None:
    assert histogram([1, 2, 3, 4], 2) == [2, 2]


def test_readings_that_are_all_the_same_fall_in_the_first_bucket() -> None:
    assert histogram([5, 5, 5], 3) == [3, 0, 0]


def test_an_empty_series_counts_nothing() -> None:
    assert histogram([], 3) == [0, 0, 0]
""",
        imports="from value_histogram import histogram\n",
    ),
)

_G014 = D2TaskSpec(
    template_id="d5_transform.topological_order",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-topological-order",
    module="topological_order",
    module_doc="Ordering steps so that what they need comes first.",
    issue=(
        "ordered() is documented to return every step with its prerequisites ahead of it. "
        "Callers report that a step named only as somebody's prerequisite is missing from the "
        "result, and that a circular requirement returns a short list instead of complaining."
    ),
    expected=(
        "ordered(requirements) returns every step exactly once, with each step's prerequisites "
        "before it, breaking ties by name. A step named only as a prerequisite is a step too. "
        "Requirements that cannot all be met raise ValueError."
    ),
    baseline_reason=(
        "it starts from the named steps alone and returns whatever it managed when it gets stuck"
    ),
    edge_cases=(
        "a step named only as a prerequisite is included",
        "a circular requirement raises ValueError",
    ),
    baseline='''def ordered(requirements):
    """Return the steps of `requirements` with prerequisites first."""
    remaining = {step: set(needs) for step, needs in requirements.items()}
    result = []
    while remaining:
        ready = sorted(step for step, needs in remaining.items() if not needs)
        if not ready:
            break
        for step in ready:
            result.append(step)
            del remaining[step]
        for needs in remaining.values():
            needs.difference_update(ready)
    return result''',
    variant_one='''def ordered(requirements):
    """Return the steps of `requirements` with prerequisites first."""
    remaining = {step: set(needs) for step, needs in requirements.items()}
    for needs in list(remaining.values()):
        for step in needs:
            remaining.setdefault(step, set())
    result = []
    while remaining:
        ready = sorted(step for step, needs in remaining.items() if not needs)
        if not ready:
            raise ValueError("the requirements are circular")
        for step in ready:
            result.append(step)
            del remaining[step]
        for needs in remaining.values():
            needs.difference_update(ready)
    return result''',
    variant_two='''def ordered(requirements):
    """Return the steps of `requirements` with prerequisites first."""
    every = set(requirements)
    for needs in requirements.values():
        every.update(needs)
    result = []
    placed = set()
    while len(placed) < len(every):
        ready = sorted(
            step
            for step in every
            if step not in placed and set(requirements.get(step, ())) <= placed
        )
        if not ready:
            raise ValueError("the requirements are circular")
        result.extend(ready)
        placed.update(ready)
    return result''',
    variant_three='''def ordered(requirements):
    """Return the steps of `requirements` with prerequisites first."""
    remaining = {step: set(needs) for step, needs in requirements.items()}
    for needs in list(remaining.values()):
        for step in needs:
            remaining.setdefault(step, set())
    result = []
    while remaining:
        ready = sorted(step for step, needs in remaining.items() if not needs)
        if not ready:
            break
        for step in ready:
            result.append(step)
            del remaining[step]
        for needs in remaining.values():
            needs.difference_update(ready)
    return result''',
    variant_four='''def ordered(requirements):
    """Return the steps of `requirements` with prerequisites first."""
    remaining = {step: set(needs) for step, needs in requirements.items()}
    result = []
    while remaining:
        ready = sorted(step for step, needs in remaining.items() if not needs)
        if not ready:
            raise ValueError("the requirements are circular")
        for step in ready:
            result.append(step)
            del remaining[step]
        for needs in remaining.values():
            needs.difference_update(ready)
    return result''',
    visible_test=_test_module(
        "topological_order",
        "Published contract for ordering steps.",
        """
def test_a_prerequisite_comes_first() -> None:
    assert ordered({"b": ["a"], "a": []}) == ["a", "b"]


def test_independent_steps_come_back_in_name_order() -> None:
    assert ordered({"b": [], "a": []}) == ["a", "b"]
""",
        imports="from topological_order import ordered\n",
    ),
    hidden_test=_test_module(
        "topological_order",
        "The part of the contract the published tests do not state.",
        """
import pytest

from topological_order import ordered


def test_a_prerequisite_comes_first() -> None:
    assert ordered({"b": ["a"], "a": []}) == ["a", "b"]


def test_a_step_named_only_as_a_prerequisite_is_included() -> None:
    assert ordered({"b": ["a"]}) == ["a", "b"]


def test_a_circular_requirement_is_refused() -> None:
    with pytest.raises(ValueError):
        ordered({"a": ["b"], "b": ["a"]})
""",
    ),
)

_G015 = D2TaskSpec(
    template_id="d5_state.debounce_window",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-debounce-window",
    module="debounce_window",
    module_doc="Letting an action run at most once per window.",
    issue=(
        "allow() is documented to let an action run at most once per window per key. Callers "
        "report that the very first action for a key raises instead of being allowed, and that "
        "an action arriving exactly one window later is suppressed."
    ),
    expected=(
        "allow(seen, key, now, window) returns whether the action may run and the updated "
        "mapping of last-allowed times. The first action for a key is always allowed, and an "
        "action arriving at or after `window` since the last allowed one is allowed too. A "
        "suppressed action leaves the mapping alone."
    ),
    baseline_reason="it reads the key straight out of the mapping and compares the gap strictly",
    edge_cases=(
        "the first action for a key is allowed",
        "an action arriving exactly one window later is allowed",
    ),
    baseline='''def allow(seen, key, now, window):
    """Return whether the action may run, and the updated mapping."""
    last = seen[key]
    if now - last > window:
        updated = dict(seen)
        updated[key] = now
        return True, updated
    return False, seen''',
    variant_one='''def allow(seen, key, now, window):
    """Return whether the action may run, and the updated mapping."""
    last = seen.get(key)
    if last is None or now - last >= window:
        updated = dict(seen)
        updated[key] = now
        return True, updated
    return False, seen''',
    variant_two='''def allow(seen, key, now, window):
    """Return whether the action may run, and the updated mapping."""
    if key in seen and now - seen[key] < window:
        return False, seen
    updated = dict(seen)
    updated[key] = now
    return True, updated''',
    variant_three='''def allow(seen, key, now, window):
    """Return whether the action may run, and the updated mapping."""
    last = seen.get(key)
    if last is None or now - last > window:
        updated = dict(seen)
        updated[key] = now
        return True, updated
    return False, seen''',
    variant_four='''def allow(seen, key, now, window):
    """Return whether the action may run, and the updated mapping."""
    last = seen[key]
    if now - last >= window:
        updated = dict(seen)
        updated[key] = now
        return True, updated
    return False, seen''',
    visible_test=_test_module(
        "debounce_window",
        "Published contract for letting an action run once per window.",
        """
def test_an_action_well_after_the_window_is_allowed() -> None:
    allowed, updated = allow({"a": 0}, "a", 10, 5)
    assert allowed is True
    assert updated == {"a": 10}


def test_an_action_inside_the_window_is_suppressed() -> None:
    allowed, updated = allow({"a": 0}, "a", 2, 5)
    assert allowed is False
    assert updated == {"a": 0}
""",
        imports="from debounce_window import allow\n",
    ),
    hidden_test=_test_module(
        "debounce_window",
        "The part of the contract the published tests do not state.",
        """
def test_an_action_well_after_the_window_is_allowed() -> None:
    allowed, _ = allow({"a": 0}, "a", 10, 5)
    assert allowed is True


def test_the_first_action_for_a_key_is_allowed() -> None:
    allowed, updated = allow({}, "a", 3, 5)
    assert allowed is True
    assert updated == {"a": 3}


def test_an_action_exactly_one_window_later_is_allowed() -> None:
    allowed, _ = allow({"a": 0}, "a", 5, 5)
    assert allowed is True
""",
        imports="from debounce_window import allow\n",
    ),
)

_G016 = D2TaskSpec(
    template_id="d5_state.replica_reconcile",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-replica-reconcile",
    module="replica_reconcile",
    module_doc="Reconciling two replicas of a versioned store.",
    issue=(
        "reconcile() is documented to merge a remote replica into the local one, keeping "
        "whichever entry carries the higher version. Callers report that a key only the remote "
        "has is dropped, and that two entries at the same version flip to the remote value, so "
        "reconciling twice does not settle."
    ),
    expected=(
        "reconcile(local, remote) returns the merged mapping of key to (version, value). The "
        "higher version wins; at the same version the local entry is kept, so reconciling an "
        "already reconciled pair changes nothing. A key only one side has is adopted."
    ),
    baseline_reason=(
        "it only looks at keys the local replica already has and lets an equal version win"
    ),
    edge_cases=(
        "a key only the remote has is adopted",
        "at the same version the local entry is kept",
    ),
    baseline='''def reconcile(local, remote):
    """Return the merge of `remote` into `local` by version."""
    merged = dict(local)
    for key, entry in remote.items():
        if key in merged and entry[0] >= merged[key][0]:
            merged[key] = entry
    return merged''',
    variant_one='''def reconcile(local, remote):
    """Return the merge of `remote` into `local` by version."""
    merged = dict(local)
    for key, entry in remote.items():
        if key not in merged or entry[0] > merged[key][0]:
            merged[key] = entry
    return merged''',
    variant_two='''def reconcile(local, remote):
    """Return the merge of `remote` into `local` by version."""
    merged = {}
    for key in set(local) | set(remote):
        here = local.get(key)
        there = remote.get(key)
        if here is None:
            merged[key] = there
        elif there is None or there[0] <= here[0]:
            merged[key] = here
        else:
            merged[key] = there
    return merged''',
    variant_three='''def reconcile(local, remote):
    """Return the merge of `remote` into `local` by version."""
    merged = dict(local)
    for key, entry in remote.items():
        if key not in merged or entry[0] >= merged[key][0]:
            merged[key] = entry
    return merged''',
    variant_four='''def reconcile(local, remote):
    """Return the merge of `remote` into `local` by version."""
    merged = dict(local)
    for key, entry in remote.items():
        if key in merged and entry[0] > merged[key][0]:
            merged[key] = entry
    return merged''',
    visible_test=_test_module(
        "replica_reconcile",
        "Published contract for reconciling two replicas.",
        """
def test_a_higher_remote_version_wins() -> None:
    assert reconcile({"a": (1, "x")}, {"a": (2, "y")}) == {"a": (2, "y")}


def test_a_lower_remote_version_loses() -> None:
    assert reconcile({"a": (2, "x")}, {"a": (1, "y")}) == {"a": (2, "x")}
""",
        imports="from replica_reconcile import reconcile\n",
    ),
    hidden_test=_test_module(
        "replica_reconcile",
        "The part of the contract the published tests do not state.",
        """
def test_a_higher_remote_version_wins() -> None:
    assert reconcile({"a": (1, "x")}, {"a": (2, "y")}) == {"a": (2, "y")}


def test_a_key_only_the_remote_has_is_adopted() -> None:
    assert reconcile({"a": (1, "x")}, {"b": (1, "z")}) == {"a": (1, "x"), "b": (1, "z")}


def test_the_same_version_keeps_the_local_entry() -> None:
    assert reconcile({"a": (1, "x")}, {"a": (1, "y")}) == {"a": (1, "x")}
""",
        imports="from replica_reconcile import reconcile\n",
    ),
)

_G017 = D2TaskSpec(
    template_id="d5_error.circuit_breaker",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-circuit-breaker",
    module="circuit_breaker",
    module_doc="Deciding when a run of failures should open the circuit.",
    issue=(
        "should_trip() is documented to open the circuit once the failure ratio reaches the "
        "threshold, but only once there is enough evidence. Callers report that a single "
        "failure opens it immediately, and that a ratio landing exactly on the threshold leaves "
        "it closed."
    ),
    expected=(
        "should_trip(results, threshold, minimum) is true when at least `minimum` results have "
        "been seen and the share of failures is at least `threshold`. Below the minimum it is "
        "never true, whatever the share."
    ),
    baseline_reason=(
        "it never counts the evidence and compares the share with a strict greater-than"
    ),
    edge_cases=(
        "below the minimum number of results it never trips",
        "a share landing exactly on the threshold trips",
    ),
    baseline='''def should_trip(results, threshold, minimum):
    """Return whether the failures in `results` should open the circuit."""
    failures = [item for item in results if not item]
    share = len(failures) / len(results)
    return share > threshold''',
    variant_one='''def should_trip(results, threshold, minimum):
    """Return whether the failures in `results` should open the circuit."""
    collected = list(results)
    if len(collected) < minimum:
        return False
    failures = [item for item in collected if not item]
    return len(failures) / len(collected) >= threshold''',
    variant_two='''def should_trip(results, threshold, minimum):
    """Return whether the failures in `results` should open the circuit."""
    collected = list(results)
    seen = len(collected)
    if seen < minimum or seen == 0:
        return False
    failed = sum(1 for item in collected if not item)
    return not failed < threshold * seen''',
    variant_three='''def should_trip(results, threshold, minimum):
    """Return whether the failures in `results` should open the circuit."""
    collected = list(results)
    if len(collected) < minimum:
        return False
    failures = [item for item in collected if not item]
    return len(failures) / len(collected) > threshold''',
    variant_four='''def should_trip(results, threshold, minimum):
    """Return whether the failures in `results` should open the circuit."""
    failures = [item for item in results if not item]
    share = len(failures) / len(results)
    return share >= threshold''',
    visible_test=_test_module(
        "circuit_breaker",
        "Published contract for opening the circuit.",
        """
def test_mostly_failures_open_the_circuit() -> None:
    assert should_trip([False, False, False, True], 0.5, 3) is True


def test_mostly_successes_leave_it_closed() -> None:
    assert should_trip([True, True, True, False], 0.5, 3) is False
""",
        imports="from circuit_breaker import should_trip\n",
    ),
    hidden_test=_test_module(
        "circuit_breaker",
        "The part of the contract the published tests do not state.",
        """
def test_mostly_failures_open_the_circuit() -> None:
    assert should_trip([False, False, False, True], 0.5, 3) is True


def test_too_little_evidence_leaves_it_closed() -> None:
    assert should_trip([False], 0.5, 3) is False


def test_a_share_exactly_on_the_threshold_trips() -> None:
    assert should_trip([False, True], 0.5, 2) is True
""",
        imports="from circuit_breaker import should_trip\n",
    ),
)

_G018 = D2TaskSpec(
    template_id="d5_error.duplicate_suppression",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-duplicate-suppression",
    module="duplicate_suppression",
    module_doc="Collapsing repeated error messages into one line each.",
    issue=(
        "collapse() is documented to report each distinct message once with the number of times "
        "it occurred. Callers report that the report comes back in alphabetical order rather "
        "than in the order the messages first appeared, and that two messages differing only in "
        "trailing whitespace are reported separately."
    ),
    expected=(
        "collapse(messages) returns (message, count) pairs in the order each message first "
        "appeared. Trailing whitespace does not distinguish two messages, and the form reported "
        "is the one that appeared first."
    ),
    baseline_reason="it sorts the tally and compares the messages exactly as they arrived",
    edge_cases=(
        "the pairs come back in first-seen order",
        "trailing whitespace does not distinguish two messages",
    ),
    baseline='''def collapse(messages):
    """Return each distinct message once with how often it occurred."""
    counts = {}
    for message in messages:
        counts[message] = counts.get(message, 0) + 1
    return sorted(counts.items())''',
    variant_one='''def collapse(messages):
    """Return each distinct message once with how often it occurred."""
    first = {}
    counts = {}
    for message in messages:
        key = message.rstrip()
        if key not in first:
            first[key] = message
            counts[key] = 0
        counts[key] += 1
    return [(first[key], counts[key]) for key in first]''',
    variant_two='''def collapse(messages):
    """Return each distinct message once with how often it occurred."""
    order = []
    tally = {}
    for message in messages:
        key = message.rstrip()
        if key in tally:
            tally[key][1] += 1
        else:
            tally[key] = [message, 1]
            order.append(key)
    return [tuple(tally[key]) for key in order]''',
    variant_three='''def collapse(messages):
    """Return each distinct message once with how often it occurred."""
    counts = {}
    for message in messages:
        counts[message] = counts.get(message, 0) + 1
    return list(counts.items())''',
    variant_four='''def collapse(messages):
    """Return each distinct message once with how often it occurred."""
    first = {}
    counts = {}
    for message in messages:
        key = message.rstrip()
        if key not in first:
            first[key] = message
            counts[key] = 0
        counts[key] += 1
    return sorted((first[key], counts[key]) for key in first)''',
    visible_test=_test_module(
        "duplicate_suppression",
        "Published contract for collapsing repeated messages.",
        """
def test_a_repeated_message_is_reported_once_with_its_count() -> None:
    assert collapse(["a", "b", "a"]) == [("a", 2), ("b", 1)]


def test_a_single_message_is_reported_once() -> None:
    assert collapse(["only"]) == [("only", 1)]
""",
        imports="from duplicate_suppression import collapse\n",
    ),
    hidden_test=_test_module(
        "duplicate_suppression",
        "The part of the contract the published tests do not state.",
        """
def test_a_single_message_is_reported_once() -> None:
    assert collapse(["only"]) == [("only", 1)]


def test_the_pairs_come_back_in_first_seen_order() -> None:
    assert collapse(["b", "a", "b"]) == [("b", 2), ("a", 1)]


def test_trailing_whitespace_does_not_distinguish_messages() -> None:
    assert collapse(["disk full", "disk full  "]) == [("disk full", 2)]
""",
        imports="from duplicate_suppression import collapse\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G019 = D2TaskSpec(
    template_id="d5_boundary.word_wrap",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-word-wrap",
    module="word_wrap",
    module_doc="Folding a run of prose into lines that fit a column.",
    issue=(
        "wrap_words() is documented to fold text into lines no wider than a column. Callers "
        "report that a word longer than the column disappears from the output entirely, and "
        "that text typed with two spaces between sentences comes back with the gap intact."
    ),
    expected=(
        "wrap_words(text, width) returns the lines of the text in order, each no longer than "
        "`width` except where a single word is already longer, in which case that word takes a "
        "line of its own. Words are separated by a single space however many the input had."
    ),
    baseline_reason=(
        "it only starts a new line for a word that would fit on one, and it separates words by "
        "splitting on a single space rather than on runs of whitespace"
    ),
    edge_cases=(
        "a run of several spaces separates two words exactly as one space would",
        "a word longer than the width takes a line of its own instead of being dropped",
    ),
    baseline='''def wrap_words(text, width):
    """Return `text` folded into lines no wider than `width`."""
    lines = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= width:
            current = candidate
        elif len(word) <= width:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines''',
    variant_one='''def wrap_words(text, width):
    """Return `text` folded into lines no wider than `width`."""
    lines = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines''',
    variant_two='''def wrap_words(text, width):
    """Return `text` folded into lines no wider than `width`."""
    words = [word for word in text.split(" ") if word]
    lines = []
    start = 0
    while start < len(words):
        stop = start + 1
        length = len(words[start])
        while stop < len(words) and length + 1 + len(words[stop]) <= width:
            length += 1 + len(words[stop])
            stop += 1
        lines.append(" ".join(words[start:stop]))
        start = stop
    return lines''',
    variant_three='''def wrap_words(text, width):
    """Return `text` folded into lines no wider than `width`."""
    lines = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= width:
            current = candidate
        elif len(word) <= width:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines''',
    variant_four='''def wrap_words(text, width):
    """Return `text` folded into lines no wider than `width`."""
    lines = []
    current = ""
    for word in text.split(" "):
        candidate = f"{current} {word}" if current else word
        if not current or len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines''',
    visible_test=_test_module(
        "word_wrap",
        "Published contract for folding prose into a column.",
        """
def test_words_fill_a_line_before_the_next_one_starts() -> None:
    assert wrap_words("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_text_shorter_than_the_column_stays_on_one_line() -> None:
    assert wrap_words("one two", 20) == ["one two"]
""",
        imports="from word_wrap import wrap_words\n",
    ),
    hidden_test=_test_module(
        "word_wrap",
        "The part of the contract the published tests do not state.",
        """
def test_words_fill_a_line_before_the_next_one_starts() -> None:
    assert wrap_words("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_a_run_of_spaces_separates_words_as_one_space_would() -> None:
    assert wrap_words("alpha   beta", 20) == ["alpha beta"]


def test_a_word_longer_than_the_column_takes_a_line_of_its_own() -> None:
    assert wrap_words("hi disproportionately ok", 6) == ["hi", "disproportionately", "ok"]
""",
        imports="from word_wrap import wrap_words\n",
    ),
)


_G020 = D2TaskSpec(
    template_id="d5_boundary.ring_read",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-ring-read",
    module="ring_read",
    module_doc="Reading a span of entries out of a circular buffer.",
    issue=(
        "read_ring() is documented to hand back a span of entries from a circular buffer. "
        "Callers report that a span starting near the end comes back short instead of "
        "continuing from the front, and that asking for more entries than the buffer holds "
        "quietly returns whatever was there."
    ),
    expected=(
        "read_ring(buffer, start, count) returns `count` entries beginning at `start`, "
        "continuing from the front of the buffer once it runs past the end, and raises "
        "ValueError when `count` is larger than the buffer."
    ),
    baseline_reason="it reads the span as a plain slice, which neither wraps nor complains",
    edge_cases=(
        "a span running past the end continues from the front",
        "a count larger than the buffer is refused",
    ),
    baseline='''def read_ring(buffer, start, count):
    """Return `count` entries of `buffer` beginning at `start`, wrapping round."""
    items = list(buffer)
    return items[start : start + count]''',
    variant_one='''def read_ring(buffer, start, count):
    """Return `count` entries of `buffer` beginning at `start`, wrapping round."""
    items = list(buffer)
    if count > len(items):
        raise ValueError(f"cannot read {count} entries from a ring of {len(items)}")
    return [items[(start + step) % len(items)] for step in range(count)]''',
    variant_two='''def read_ring(buffer, start, count):
    """Return `count` entries of `buffer` beginning at `start`, wrapping round."""
    items = list(buffer)
    size = len(items)
    if count > size:
        raise ValueError(f"cannot read {count} entries from a ring of {size}")
    doubled = items + items
    return doubled[start : start + count]''',
    variant_three='''def read_ring(buffer, start, count):
    """Return `count` entries of `buffer` beginning at `start`, wrapping round."""
    items = list(buffer)
    return [items[(start + step) % len(items)] for step in range(count)]''',
    variant_four='''def read_ring(buffer, start, count):
    """Return `count` entries of `buffer` beginning at `start`, wrapping round."""
    items = list(buffer)
    if count > len(items):
        raise ValueError(f"cannot read {count} entries from a ring of {len(items)}")
    return items[start : start + count]''',
    visible_test=_test_module(
        "ring_read",
        "Published contract for reading a span out of a ring.",
        """
def test_a_span_inside_the_buffer_reads_straight_through() -> None:
    assert read_ring(("a", "b", "c", "d"), 1, 2) == ["b", "c"]


def test_a_span_covering_the_whole_buffer_reads_it_all() -> None:
    assert read_ring(("a", "b", "c"), 0, 3) == ["a", "b", "c"]
""",
        imports="from ring_read import read_ring\n",
    ),
    hidden_test=_test_module(
        "ring_read",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_span_inside_the_buffer_reads_straight_through() -> None:
    assert read_ring(("a", "b", "c", "d"), 1, 2) == ["b", "c"]


def test_a_span_running_past_the_end_continues_from_the_front() -> None:
    assert read_ring(("a", "b", "c", "d"), 3, 3) == ["d", "a", "b"]


def test_a_count_larger_than_the_buffer_is_refused() -> None:
    with pytest.raises(ValueError):
        read_ring(("a", "b", "c", "d"), 0, 5)
""",
        imports="from ring_read import read_ring\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G021 = D2TaskSpec(
    template_id="d5_numeric.half_even",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-half-even",
    module="half_even",
    module_doc="Rounding a measurement the way a settlement report has to.",
    issue=(
        "round_half_even() is documented to round to a number of places with a tie going to "
        "the even digit. Auditors report that a value landing exactly halfway rounds upwards "
        "instead, and that a value such as 2.675 rounds down when the report says 2.68."
    ),
    expected=(
        "round_half_even(value, places) returns the value as a Decimal rounded to `places` "
        "decimal places, a value landing exactly halfway going to the even digit, and a float "
        "read at the value its decimal literal names rather than at its binary expansion."
    ),
    baseline_reason=(
        "it rounds half away from zero and builds the Decimal straight from the float, which "
        "carries the binary expansion rather than the literal"
    ),
    edge_cases=(
        "a value landing exactly halfway goes to the even digit",
        "a float is read at the value its decimal literal names",
    ),
    imports="from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal\n",
    baseline='''def round_half_even(value, places):
    """Return `value` rounded to `places` places with a tie going to the even digit."""
    step = Decimal(1).scaleb(-places)
    return Decimal(value).quantize(step, rounding=ROUND_HALF_UP)''',
    variant_one='''def round_half_even(value, places):
    """Return `value` rounded to `places` places with a tie going to the even digit."""
    step = Decimal(1).scaleb(-places)
    return Decimal(str(value)).quantize(step, rounding=ROUND_HALF_EVEN)''',
    variant_two='''def round_half_even(value, places):
    """Return `value` rounded to `places` places with a tie going to the even digit."""
    exact = Decimal(str(value)).scaleb(places)
    return exact.to_integral_value(rounding=ROUND_HALF_EVEN).scaleb(-places)''',
    variant_three='''def round_half_even(value, places):
    """Return `value` rounded to `places` places with a tie going to the even digit."""
    step = Decimal(1).scaleb(-places)
    return Decimal(value).quantize(step, rounding=ROUND_HALF_EVEN)''',
    variant_four='''def round_half_even(value, places):
    """Return `value` rounded to `places` places with a tie going to the even digit."""
    step = Decimal(1).scaleb(-places)
    return Decimal(str(value)).quantize(step, rounding=ROUND_HALF_UP)''',
    visible_test=_test_module(
        "half_even",
        "Published contract for rounding a settlement figure.",
        """
from decimal import Decimal


def test_a_value_below_the_midpoint_rounds_down() -> None:
    assert round_half_even(1.234, 2) == Decimal("1.23")


def test_a_value_above_the_midpoint_rounds_up() -> None:
    assert round_half_even(1.236, 2) == Decimal("1.24")


def test_a_whole_number_keeps_its_value() -> None:
    assert round_half_even(3.0, 0) == Decimal("3")
""",
        imports="from half_even import round_half_even\n",
    ),
    hidden_test=_test_module(
        "half_even",
        "The part of the contract the published tests do not state.",
        """
from decimal import Decimal


def test_a_value_below_the_midpoint_rounds_down() -> None:
    assert round_half_even(1.234, 2) == Decimal("1.23")


def test_a_tie_goes_to_the_even_digit() -> None:
    assert round_half_even(2.5, 0) == Decimal("2")
    assert round_half_even(3.5, 0) == Decimal("4")


def test_a_float_is_read_at_the_value_its_literal_names() -> None:
    assert round_half_even(2.675, 2) == Decimal("2.68")
""",
        imports="from half_even import round_half_even\n",
    ),
)


_G022 = D2TaskSpec(
    template_id="d5_numeric.prime_factors",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-prime-factors",
    module="prime_factors",
    module_doc="Breaking a whole number into the primes that multiply to it.",
    issue=(
        "prime_factors() is documented to return the primes whose product is the number. "
        "Callers report that the factors of 14 come back as just [2], and that a number below "
        "two comes back as an empty list rather than being refused."
    ),
    expected=(
        "prime_factors(number) returns the prime factors of the number in ascending order with "
        "each repeated as often as it divides, so their product is the number, and raises "
        "ValueError for a number below two."
    ),
    baseline_reason=(
        "it trials divisors only up to the square root of the original number and never "
        "collects what is left over, and it treats a number below two as having no factors"
    ),
    edge_cases=(
        "a prime factor above the square root is still collected",
        "a number below two is refused",
    ),
    baseline='''def prime_factors(number):
    """Return the ascending prime factors of `number` with their multiplicities."""
    factors = []
    remaining = number
    limit = int(remaining**0.5)
    for candidate in range(2, limit + 1):
        while remaining % candidate == 0:
            factors.append(candidate)
            remaining //= candidate
    return factors''',
    variant_one='''def prime_factors(number):
    """Return the ascending prime factors of `number` with their multiplicities."""
    if number < 2:
        raise ValueError(f"prime factors are undefined for {number}")
    factors = []
    remaining = number
    candidate = 2
    while candidate * candidate <= remaining:
        while remaining % candidate == 0:
            factors.append(candidate)
            remaining //= candidate
        candidate += 1
    if remaining > 1:
        factors.append(remaining)
    return factors''',
    variant_two='''def prime_factors(number):
    """Return the ascending prime factors of `number` with their multiplicities."""
    if number < 2:
        raise ValueError(f"prime factors are undefined for {number}")
    factors = []
    remaining = number
    while remaining > 1:
        divisor = next(
            (
                candidate
                for candidate in range(2, int(remaining**0.5) + 1)
                if remaining % candidate == 0
            ),
            remaining,
        )
        factors.append(divisor)
        remaining //= divisor
    return factors''',
    variant_three='''def prime_factors(number):
    """Return the ascending prime factors of `number` with their multiplicities."""
    factors = []
    remaining = number
    candidate = 2
    while candidate * candidate <= remaining:
        while remaining % candidate == 0:
            factors.append(candidate)
            remaining //= candidate
        candidate += 1
    if remaining > 1:
        factors.append(remaining)
    return factors''',
    variant_four='''def prime_factors(number):
    """Return the ascending prime factors of `number` with their multiplicities."""
    if number < 2:
        raise ValueError(f"prime factors are undefined for {number}")
    factors = []
    remaining = number
    limit = int(remaining**0.5)
    for candidate in range(2, limit + 1):
        while remaining % candidate == 0:
            factors.append(candidate)
            remaining //= candidate
    return factors''',
    visible_test=_test_module(
        "prime_factors",
        "Published contract for factorising a whole number.",
        """
def test_a_number_with_repeated_factors_repeats_them() -> None:
    assert prime_factors(12) == [2, 2, 3]


def test_a_power_of_two_is_all_twos() -> None:
    assert prime_factors(8) == [2, 2, 2]


def test_a_square_factorises_in_pairs() -> None:
    assert prime_factors(36) == [2, 2, 3, 3]
""",
        imports="from prime_factors import prime_factors\n",
    ),
    hidden_test=_test_module(
        "prime_factors",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_number_with_repeated_factors_repeats_them() -> None:
    assert prime_factors(12) == [2, 2, 3]


def test_a_prime_factor_above_the_square_root_is_collected() -> None:
    assert prime_factors(14) == [2, 7]
    assert prime_factors(97) == [97]


def test_a_number_below_two_is_refused() -> None:
    with pytest.raises(ValueError):
        prime_factors(1)
""",
        imports="from prime_factors import prime_factors\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G023 = D2TaskSpec(
    template_id="d5_parsing.line_continuation",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-line-continuation",
    module="line_continuation",
    module_doc="Rejoining physical lines that an author split across a continuation marker.",
    issue=(
        "join_continuations() is documented to rejoin lines split across a continuation marker. "
        "Callers report that a file whose last line is still continued loses that line "
        "altogether, and that an indented continuation carries its indentation into the middle "
        "of the joined text."
    ),
    expected=(
        "join_continuations(lines) returns the logical lines in order. A line ending in '&' "
        "continues onto the next with the marker removed, the continuation's leading "
        "whitespace is dropped before joining, and a continuation still open at the end of the "
        "input yields its logical line all the same."
    ),
    baseline_reason=(
        "it throws away whatever is still buffered when the input ends, and it appends the "
        "continuation exactly as written rather than trimming its indentation"
    ),
    edge_cases=(
        "a continuation still open at the end of the input yields its line",
        "an indented continuation is joined without its indentation",
    ),
    baseline='''def join_continuations(lines):
    """Return the logical lines of `lines`, rejoining continuations."""
    joined = []
    buffer = ""
    for line in lines:
        if line.endswith("&"):
            buffer += line[:-1]
            continue
        joined.append(buffer + line)
        buffer = ""
    return joined''',
    variant_one='''def join_continuations(lines):
    """Return the logical lines of `lines`, rejoining continuations."""
    joined = []
    buffer = ""
    for line in lines:
        piece = line.lstrip() if buffer else line
        if piece.endswith("&"):
            buffer += piece[:-1]
            continue
        joined.append(buffer + piece)
        buffer = ""
    if buffer:
        joined.append(buffer)
    return joined''',
    variant_two='''def join_continuations(lines):
    """Return the logical lines of `lines`, rejoining continuations."""
    joined = []
    parts = []
    for line in lines:
        continued = line.endswith("&")
        text = line[:-1] if continued else line
        parts.append(text.lstrip() if parts else text)
        if not continued:
            joined.append("".join(parts))
            parts = []
    if parts:
        joined.append("".join(parts))
    return joined''',
    variant_three='''def join_continuations(lines):
    """Return the logical lines of `lines`, rejoining continuations."""
    joined = []
    buffer = ""
    for line in lines:
        if line.endswith("&"):
            buffer += line[:-1]
            continue
        joined.append(buffer + line)
        buffer = ""
    if buffer:
        joined.append(buffer)
    return joined''',
    variant_four='''def join_continuations(lines):
    """Return the logical lines of `lines`, rejoining continuations."""
    joined = []
    buffer = ""
    for line in lines:
        piece = line.lstrip() if buffer else line
        if piece.endswith("&"):
            buffer += piece[:-1]
            continue
        joined.append(buffer + piece)
        buffer = ""
    return joined''',
    visible_test=_test_module(
        "line_continuation",
        "Published contract for rejoining continued lines.",
        """
def test_a_marked_line_joins_the_one_after_it() -> None:
    assert join_continuations(["alpha&", "beta", "gamma"]) == ["alphabeta", "gamma"]


def test_plain_lines_pass_through_unchanged() -> None:
    assert join_continuations(["one", "two"]) == ["one", "two"]
""",
        imports="from line_continuation import join_continuations\n",
    ),
    hidden_test=_test_module(
        "line_continuation",
        "The part of the contract the published tests do not state.",
        """
def test_a_marked_line_joins_the_one_after_it() -> None:
    assert join_continuations(["alpha&", "beta", "gamma"]) == ["alphabeta", "gamma"]


def test_a_continuation_open_at_the_end_still_yields_its_line() -> None:
    assert join_continuations(["alpha&", "beta&"]) == ["alphabeta"]


def test_an_indented_continuation_loses_its_indentation() -> None:
    assert join_continuations(["first&", "    second"]) == ["firstsecond"]
""",
        imports="from line_continuation import join_continuations\n",
    ),
)


_G024 = D2TaskSpec(
    template_id="d5_parsing.accept_quality",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-accept-quality",
    module="accept_quality",
    module_doc="Reading which representations a client would rather be sent.",
    issue=(
        "preferred_types() is documented to order the media types of an Accept header by "
        "preference. Callers report that a type offered without an explicit weight sinks to "
        "the bottom of the order, and that a type the client explicitly refused is still "
        "offered back."
    ),
    expected=(
        "preferred_types(header) returns the media types in descending order of quality, a "
        "type carrying no explicit q taking quality one, a type carrying q=0 being left out "
        "altogether, and types of equal quality keeping the order the header gave them."
    ),
    baseline_reason=(
        "it takes a missing q as zero rather than one, and it ranks a refused type instead of "
        "dropping it"
    ),
    edge_cases=(
        "a type with no explicit q takes quality one",
        "a type with q=0 is left out",
    ),
    baseline='''def preferred_types(header):
    """Return the media types of `header` in descending order of preference."""
    ranked = []
    for position, part in enumerate(header.split(",")):
        pieces = [piece.strip() for piece in part.split(";")]
        media = pieces[0]
        quality = 0.0
        for piece in pieces[1:]:
            if piece.startswith("q="):
                quality = float(piece[2:])
        ranked.append((-quality, position, media))
    ranked.sort()
    return [media for _, _, media in ranked]''',
    variant_one='''def preferred_types(header):
    """Return the media types of `header` in descending order of preference."""
    ranked = []
    for position, part in enumerate(header.split(",")):
        pieces = [piece.strip() for piece in part.split(";")]
        media = pieces[0]
        quality = 1.0
        for piece in pieces[1:]:
            if piece.startswith("q="):
                quality = float(piece[2:])
        if quality == 0.0:
            continue
        ranked.append((-quality, position, media))
    ranked.sort()
    return [media for _, _, media in ranked]''',
    variant_two='''def preferred_types(header):
    """Return the media types of `header` in descending order of preference."""
    entries = []
    for part in header.split(","):
        media, _, parameters = part.strip().partition(";")
        quality = 1.0
        for parameter in parameters.split(";"):
            name, sign, value = parameter.strip().partition("=")
            if sign and name == "q":
                quality = float(value)
        if quality > 0.0:
            entries.append((media.strip(), quality))
    order = sorted(range(len(entries)), key=lambda index: (-entries[index][1], index))
    return [entries[index][0] for index in order]''',
    variant_three='''def preferred_types(header):
    """Return the media types of `header` in descending order of preference."""
    ranked = []
    for position, part in enumerate(header.split(",")):
        pieces = [piece.strip() for piece in part.split(";")]
        media = pieces[0]
        quality = 1.0
        for piece in pieces[1:]:
            if piece.startswith("q="):
                quality = float(piece[2:])
        ranked.append((-quality, position, media))
    ranked.sort()
    return [media for _, _, media in ranked]''',
    variant_four='''def preferred_types(header):
    """Return the media types of `header` in descending order of preference."""
    ranked = []
    for position, part in enumerate(header.split(",")):
        pieces = [piece.strip() for piece in part.split(";")]
        media = pieces[0]
        quality = 0.0
        for piece in pieces[1:]:
            if piece.startswith("q="):
                quality = float(piece[2:])
        if quality == 0.0:
            continue
        ranked.append((-quality, position, media))
    ranked.sort()
    return [media for _, _, media in ranked]''',
    visible_test=_test_module(
        "accept_quality",
        "Published contract for ordering a client's accepted types.",
        """
def test_the_heavier_weight_is_offered_first() -> None:
    header = "text/html;q=0.8, application/json;q=0.9"
    assert preferred_types(header) == ["application/json", "text/html"]


def test_equal_weights_keep_the_order_of_the_header() -> None:
    assert preferred_types("a/b;q=0.5, c/d;q=0.5") == ["a/b", "c/d"]


def test_a_single_weighted_type_is_returned_alone() -> None:
    assert preferred_types("a/b;q=0.5") == ["a/b"]
""",
        imports="from accept_quality import preferred_types\n",
    ),
    hidden_test=_test_module(
        "accept_quality",
        "The part of the contract the published tests do not state.",
        """
def test_the_heavier_weight_is_offered_first() -> None:
    header = "text/html;q=0.8, application/json;q=0.9"
    assert preferred_types(header) == ["application/json", "text/html"]


def test_a_type_with_no_weight_is_wanted_most() -> None:
    assert preferred_types("text/plain, text/html;q=0.5") == ["text/plain", "text/html"]


def test_a_refused_type_is_left_out() -> None:
    assert preferred_types("a/b;q=0.9, c/d;q=0") == ["a/b"]
""",
        imports="from accept_quality import preferred_types\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G025 = D2TaskSpec(
    template_id="d5_transform.collate_values",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-collate-values",
    module="collate_values",
    module_doc="Gathering a stream of labelled readings under the labels that carried them.",
    issue=(
        "collate() is documented to gather a stream of (label, reading) pairs under their "
        "labels. Callers report that a label reappearing later in the stream loses the "
        "readings it carried earlier on, and that the readings under a label come back "
        "ascending rather than in the order they arrived."
    ),
    expected=(
        "collate(pairs) returns a mapping from label to the list of readings that label "
        "carried, labels in the order they were first seen, readings in the order they "
        "arrived, and a label reappearing later in the stream extending the list it already "
        "has rather than starting a new one."
    ),
    baseline_reason=(
        "it gathers only runs of adjacent pairs, so a label that comes back later overwrites "
        "what it gathered before, and it sorts each run instead of keeping arrival order"
    ),
    edge_cases=(
        "a label reappearing later extends the readings it already has",
        "the readings keep the order they arrived in",
    ),
    imports="from itertools import groupby\n",
    baseline='''def collate(pairs):
    """Return the readings of `pairs` gathered under their labels."""
    collated = {}
    for label, group in groupby(pairs, key=lambda pair: pair[0]):
        collated[label] = sorted(reading for _, reading in group)
    return collated''',
    variant_one='''def collate(pairs):
    """Return the readings of `pairs` gathered under their labels."""
    collated = {}
    for label, reading in pairs:
        collated.setdefault(label, []).append(reading)
    return collated''',
    variant_two='''def collate(pairs):
    """Return the readings of `pairs` gathered under their labels."""
    ordered = list(pairs)
    labels = []
    for label, _ in ordered:
        if label not in labels:
            labels.append(label)
    return {
        label: [reading for other, reading in ordered if other == label] for label in labels
    }''',
    variant_three='''def collate(pairs):
    """Return the readings of `pairs` gathered under their labels."""
    collated = {}
    for label, reading in pairs:
        collated.setdefault(label, []).append(reading)
    return {label: sorted(readings) for label, readings in collated.items()}''',
    variant_four='''def collate(pairs):
    """Return the readings of `pairs` gathered under their labels."""
    collated = {}
    for label, group in groupby(pairs, key=lambda pair: pair[0]):
        collated[label] = [reading for _, reading in group]
    return collated''',
    visible_test=_test_module(
        "collate_values",
        "Published contract for gathering readings under their labels.",
        """
def test_readings_gather_under_the_label_that_carried_them() -> None:
    assert collate([("a", 1), ("a", 2), ("b", 3)]) == {"a": [1, 2], "b": [3]}


def test_an_empty_stream_gathers_nothing() -> None:
    assert collate([]) == {}
""",
        imports="from collate_values import collate\n",
    ),
    hidden_test=_test_module(
        "collate_values",
        "The part of the contract the published tests do not state.",
        """
def test_readings_gather_under_the_label_that_carried_them() -> None:
    assert collate([("a", 1), ("a", 2), ("b", 3)]) == {"a": [1, 2], "b": [3]}


def test_a_label_coming_back_later_keeps_what_it_gathered_before() -> None:
    assert collate([("a", 1), ("b", 2), ("a", 3)]) == {"a": [1, 3], "b": [2]}


def test_the_readings_keep_the_order_they_arrived_in() -> None:
    assert collate([("a", 3), ("a", 1)]) == {"a": [3, 1]}
""",
        imports="from collate_values import collate\n",
    ),
)


_G026 = D2TaskSpec(
    template_id="d5_transform.sequence_diff",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-sequence-diff",
    module="sequence_diff",
    module_doc="Saying what a listing gained and lost between two readings.",
    issue=(
        "diff_sequences() is documented to say what a listing gained and lost. Callers report "
        "that a second copy of an entry that was only there once before is not reported as "
        "gained, and that the report comes back alphabetically rather than in the order the "
        "listing reads."
    ),
    expected=(
        "diff_sequences(old, new) returns (added, removed). Added holds the entries of `new` "
        "that `old` does not account for, in the order `new` gives them, removed holds the "
        "entries of `old` that `new` does not account for, in the order `old` gives them, and "
        "an entry appearing more often on one side is reported for the surplus only."
    ),
    baseline_reason=(
        "it compares the two listings as sets, which forgets how often an entry appears, and "
        "it sorts what is left instead of keeping the reading order"
    ),
    edge_cases=(
        "an entry appearing more often on one side is reported for the surplus",
        "the report keeps the order the listing reads rather than sorting",
    ),
    baseline='''def diff_sequences(old, new):
    """Return (added, removed) between the `old` and `new` listings."""
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    return added, removed''',
    variant_one='''def diff_sequences(old, new):
    """Return (added, removed) between the `old` and `new` listings."""
    remaining = list(old)
    added = []
    for entry in new:
        if entry in remaining:
            remaining.remove(entry)
        else:
            added.append(entry)
    kept = list(new)
    removed = []
    for entry in old:
        if entry in kept:
            kept.remove(entry)
        else:
            removed.append(entry)
    return added, removed''',
    variant_two='''def diff_sequences(old, new):
    """Return (added, removed) between the `old` and `new` listings."""
    surplus = {}
    for entry in old:
        surplus[entry] = surplus.get(entry, 0) - 1
    for entry in new:
        surplus[entry] = surplus.get(entry, 0) + 1
    budget = dict(surplus)
    added = []
    for entry in new:
        if budget.get(entry, 0) > 0:
            budget[entry] -= 1
            added.append(entry)
    shortfall = dict(surplus)
    removed = []
    for entry in old:
        if shortfall.get(entry, 0) < 0:
            shortfall[entry] += 1
            removed.append(entry)
    return added, removed''',
    variant_three='''def diff_sequences(old, new):
    """Return (added, removed) between the `old` and `new` listings."""
    remaining = list(old)
    added = []
    for entry in new:
        if entry in remaining:
            remaining.remove(entry)
        else:
            added.append(entry)
    kept = list(new)
    removed = []
    for entry in old:
        if entry in kept:
            kept.remove(entry)
        else:
            removed.append(entry)
    return sorted(added), sorted(removed)''',
    variant_four='''def diff_sequences(old, new):
    """Return (added, removed) between the `old` and `new` listings."""
    known = set(old)
    seen = set(new)
    added = [entry for entry in new if entry not in known]
    removed = [entry for entry in old if entry not in seen]
    return added, removed''',
    visible_test=_test_module(
        "sequence_diff",
        "Published contract for reporting what a listing gained and lost.",
        """
def test_one_entry_gained_and_one_lost() -> None:
    assert diff_sequences(["a", "b", "c"], ["a", "c", "d"]) == (["d"], ["b"])


def test_an_unchanged_listing_reports_nothing() -> None:
    assert diff_sequences(["x"], ["x"]) == ([], [])
""",
        imports="from sequence_diff import diff_sequences\n",
    ),
    hidden_test=_test_module(
        "sequence_diff",
        "The part of the contract the published tests do not state.",
        """
def test_one_entry_gained_and_one_lost() -> None:
    assert diff_sequences(["a", "b", "c"], ["a", "c", "d"]) == (["d"], ["b"])


def test_a_second_copy_of_an_entry_counts_as_gained() -> None:
    assert diff_sequences(["a"], ["a", "a"]) == (["a"], [])


def test_the_report_keeps_the_order_the_listing_reads() -> None:
    assert diff_sequences(["m"], ["z", "b"]) == (["z", "b"], ["m"])
""",
        imports="from sequence_diff import diff_sequences\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G027 = D2TaskSpec(
    template_id="d5_state.token_bucket",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-token-bucket",
    module="token_bucket",
    module_doc="Deciding whether a caller may spend against a bucket that refills over time.",
    issue=(
        "spend() is documented to refill a bucket by the time that has passed and then grant "
        "the spend if the bucket can cover it. Operators report that a caller idle overnight "
        "comes back with far more than the bucket holds, and that a node whose clock steps "
        "backwards is refused for readings it should have covered."
    ),
    expected=(
        "spend(state, now, cost) returns (granted, state). The bucket first gains rate tokens "
        "for every unit of time since its stamp but never passes its capacity, a reading "
        "earlier than the stamp gains nothing and leaves the stamp where it was, the spend is "
        "granted only when the bucket covers the cost, and the caller's state is left alone."
    ),
    baseline_reason=(
        "it adds the whole refill without looking at the capacity, and it computes the elapsed "
        "time as a plain subtraction that goes negative when the clock steps backwards"
    ),
    edge_cases=(
        "a long idle fills the bucket no further than its capacity",
        "a reading earlier than the stamp gains nothing and keeps the stamp",
    ),
    baseline='''def spend(state, now, cost):
    """Return (granted, state) after refilling the bucket up to `now` and spending `cost`."""
    tokens = state["tokens"] + (now - state["stamp"]) * state["rate"]
    granted = tokens >= cost
    if granted:
        tokens -= cost
    return granted, {**state, "tokens": tokens, "stamp": now}''',
    variant_one='''def spend(state, now, cost):
    """Return (granted, state) after refilling the bucket up to `now` and spending `cost`."""
    elapsed = max(now - state["stamp"], 0)
    tokens = min(state["tokens"] + elapsed * state["rate"], state["capacity"])
    granted = tokens >= cost
    if granted:
        tokens -= cost
    return granted, {**state, "tokens": tokens, "stamp": max(state["stamp"], now)}''',
    variant_two='''def spend(state, now, cost):
    """Return (granted, state) after refilling the bucket up to `now` and spending `cost`."""
    updated = dict(state)
    if now > updated["stamp"]:
        gained = (now - updated["stamp"]) * updated["rate"]
        headroom = updated["capacity"] - updated["tokens"]
        updated["tokens"] += min(gained, max(headroom, 0))
        updated["stamp"] = now
    if updated["tokens"] < cost:
        return False, updated
    updated["tokens"] -= cost
    return True, updated''',
    variant_three='''def spend(state, now, cost):
    """Return (granted, state) after refilling the bucket up to `now` and spending `cost`."""
    gained = (now - state["stamp"]) * state["rate"]
    tokens = min(state["tokens"] + gained, state["capacity"])
    granted = tokens >= cost
    if granted:
        tokens -= cost
    return granted, {**state, "tokens": tokens, "stamp": now}''',
    variant_four='''def spend(state, now, cost):
    """Return (granted, state) after refilling the bucket up to `now` and spending `cost`."""
    elapsed = max(now - state["stamp"], 0)
    tokens = state["tokens"] + elapsed * state["rate"]
    granted = tokens >= cost
    if granted:
        tokens -= cost
    return granted, {**state, "tokens": tokens, "stamp": max(state["stamp"], now)}''',
    visible_test=_test_module(
        "token_bucket",
        "Published contract for spending against a refilling bucket.",
        """
def test_a_spend_the_refilled_bucket_covers_is_granted() -> None:
    state = {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
    assert spend(state, 3, 4) == (True, {"tokens": 1, "stamp": 3, "capacity": 10, "rate": 1})


def test_a_spend_the_bucket_cannot_cover_is_refused() -> None:
    state = {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
    assert spend(state, 1, 5) == (False, {"tokens": 3, "stamp": 1, "capacity": 10, "rate": 1})


def test_the_callers_state_is_left_alone() -> None:
    state = {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
    spend(state, 3, 1)
    assert state == {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
""",
        imports="from token_bucket import spend\n",
    ),
    hidden_test=_test_module(
        "token_bucket",
        "The part of the contract the published tests do not state.",
        """
def test_a_spend_the_refilled_bucket_covers_is_granted() -> None:
    state = {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
    assert spend(state, 3, 4) == (True, {"tokens": 1, "stamp": 3, "capacity": 10, "rate": 1})


def test_a_long_idle_fills_no_further_than_the_capacity() -> None:
    state = {"tokens": 2, "stamp": 0, "capacity": 10, "rate": 1}
    assert spend(state, 100, 1) == (
        True,
        {"tokens": 9, "stamp": 100, "capacity": 10, "rate": 1},
    )


def test_a_reading_from_before_the_stamp_gains_nothing() -> None:
    state = {"tokens": 5, "stamp": 10, "capacity": 10, "rate": 1}
    assert spend(state, 4, 1) == (True, {"tokens": 4, "stamp": 10, "capacity": 10, "rate": 1})
""",
        imports="from token_bucket import spend\n",
    ),
)


_G028 = D2TaskSpec(
    template_id="d5_state.config_patch",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-config-patch",
    module="config_patch",
    module_doc="Laying an overlay over stored settings without losing what it does not mention.",
    issue=(
        "apply_patch() is documented to lay an overlay over stored settings. Operators report "
        "that a setting they meant to clear comes back holding a null instead of being gone, "
        "and that overriding one entry of a nested section wipes out the rest of the section."
    ),
    expected=(
        "apply_patch(config, patch) returns a new mapping with the patch laid over the "
        "settings. A value of None removes the setting and removing one that was never there "
        "is not an error, a mapping value is laid over the mapping already stored rather than "
        "replacing it, and the caller's mapping is left as it was."
    ),
    baseline_reason=(
        "it merges the two mappings wholesale, so a null is stored rather than removing the "
        "setting and a nested section is replaced rather than overlaid"
    ),
    edge_cases=(
        "a value of None removes the setting, absent or not",
        "a mapping value is laid over the section already stored",
    ),
    baseline='''def apply_patch(config, patch):
    """Return `config` with `patch` laid over it."""
    return {**config, **patch}''',
    variant_one='''def apply_patch(config, patch):
    """Return `config` with `patch` laid over it."""
    updated = dict(config)
    for key, value in patch.items():
        if value is None:
            updated.pop(key, None)
        elif isinstance(value, dict) and isinstance(updated.get(key), dict):
            updated[key] = apply_patch(updated[key], value)
        else:
            updated[key] = value
    return updated''',
    variant_two='''def apply_patch(config, patch):
    """Return `config` with `patch` laid over it."""
    updated = {}
    fresh = [key for key in patch if key not in config]
    for key in list(config) + fresh:
        if key not in patch:
            updated[key] = config[key]
            continue
        value = patch[key]
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            value = apply_patch(config[key], value)
        updated[key] = value
    return updated''',
    variant_three='''def apply_patch(config, patch):
    """Return `config` with `patch` laid over it."""
    updated = dict(config)
    for key, value in patch.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    return updated''',
    variant_four='''def apply_patch(config, patch):
    """Return `config` with `patch` laid over it."""
    updated = dict(config)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(updated.get(key), dict):
            updated[key] = apply_patch(updated[key], value)
        else:
            updated[key] = value
    return updated''',
    visible_test=_test_module(
        "config_patch",
        "Published contract for laying an overlay over stored settings.",
        """
def test_the_overlay_replaces_and_adds() -> None:
    assert apply_patch({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {"a": 1, "b": 3, "c": 4}


def test_an_empty_overlay_changes_nothing() -> None:
    assert apply_patch({"a": 1}, {}) == {"a": 1}


def test_the_callers_mapping_is_left_alone() -> None:
    config = {"a": 1}
    apply_patch(config, {"b": 2})
    assert config == {"a": 1}
""",
        imports="from config_patch import apply_patch\n",
    ),
    hidden_test=_test_module(
        "config_patch",
        "The part of the contract the published tests do not state.",
        """
def test_the_overlay_replaces_and_adds() -> None:
    assert apply_patch({"a": 1, "b": 2}, {"b": 3, "c": 4}) == {"a": 1, "b": 3, "c": 4}


def test_a_null_removes_the_setting_whether_or_not_it_was_there() -> None:
    assert apply_patch({"a": 1, "b": 2}, {"b": None, "z": None}) == {"a": 1}


def test_a_section_is_laid_over_rather_than_replaced() -> None:
    stored = {"limits": {"cpu": 1, "mem": 2}}
    assert apply_patch(stored, {"limits": {"mem": 5}}) == {"limits": {"cpu": 1, "mem": 5}}
""",
        imports="from config_patch import apply_patch\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G029 = D2TaskSpec(
    template_id="d5_error.rollback_steps",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-rollback-steps",
    module="rollback_steps",
    module_doc="Running a sequence of steps and unwinding it when one of them fails.",
    issue=(
        "run_steps() is documented to unwind the steps it has already applied when one fails. "
        "Callers report that the unwinding runs in the order the steps were applied rather "
        "than backwards, and that the step which raised is unwound even though it never took "
        "effect."
    ),
    expected=(
        "run_steps(steps) applies each (apply, undo) pair in order and returns what the applies "
        "returned. When an apply raises, the steps that did take effect are undone in the "
        "reverse of the order they were applied, the step that raised is not undone because it "
        "never took effect, and the original exception is raised on."
    ),
    baseline_reason=(
        "it records a step's undo before running its apply and replays the recorded undos "
        "forwards, so the failing step is unwound and the order is back to front"
    ),
    edge_cases=(
        "the steps that took effect are undone in reverse order",
        "the step that raised is not undone",
    ),
    baseline='''def run_steps(steps):
    """Apply every step, unwinding the ones that took effect if one raises."""
    results = []
    done = []
    for apply_step, undo_step in steps:
        done.append(undo_step)
        try:
            results.append(apply_step())
        except Exception:
            for undo in done:
                undo()
            raise
    return results''',
    variant_one='''def run_steps(steps):
    """Apply every step, unwinding the ones that took effect if one raises."""
    results = []
    done = []
    for apply_step, undo_step in steps:
        try:
            results.append(apply_step())
        except Exception:
            for undo in reversed(done):
                undo()
            raise
        done.append(undo_step)
    return results''',
    variant_two='''def run_steps(steps):
    """Apply every step, unwinding the ones that took effect if one raises."""
    ordered = list(steps)
    results = []
    for position, pair in enumerate(ordered):
        try:
            results.append(pair[0]())
        except Exception:
            for earlier in range(position - 1, -1, -1):
                ordered[earlier][1]()
            raise
    return results''',
    variant_three='''def run_steps(steps):
    """Apply every step, unwinding the ones that took effect if one raises."""
    results = []
    done = []
    for apply_step, undo_step in steps:
        done.append(undo_step)
        try:
            results.append(apply_step())
        except Exception:
            for undo in reversed(done):
                undo()
            raise
    return results''',
    variant_four='''def run_steps(steps):
    """Apply every step, unwinding the ones that took effect if one raises."""
    results = []
    done = []
    for apply_step, undo_step in steps:
        try:
            results.append(apply_step())
        except Exception:
            for undo in done:
                undo()
            raise
        done.append(undo_step)
    return results''',
    visible_test=_test_module(
        "rollback_steps",
        "Published contract for running a sequence of steps.",
        """
def test_every_step_that_succeeds_returns_its_result() -> None:
    steps = [(lambda: 1, lambda: None), (lambda: 2, lambda: None)]
    assert run_steps(steps) == [1, 2]


def test_no_steps_at_all_returns_nothing() -> None:
    assert run_steps([]) == []
""",
        imports="from rollback_steps import run_steps\n",
    ),
    hidden_test=_test_module(
        "rollback_steps",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _boom():
    raise RuntimeError("the third step refuses")


def test_every_step_that_succeeds_returns_its_result() -> None:
    steps = [(lambda: 1, lambda: None), (lambda: 2, lambda: None)]
    assert run_steps(steps) == [1, 2]


def test_the_steps_that_took_effect_are_undone_backwards() -> None:
    log = []
    steps = [
        (lambda: log.append("a"), lambda: log.append("undo-a")),
        (lambda: log.append("b"), lambda: log.append("undo-b")),
        (_boom, lambda: None),
    ]
    with pytest.raises(RuntimeError):
        run_steps(steps)
    assert log == ["a", "b", "undo-b", "undo-a"]


def test_the_step_that_raised_is_not_undone() -> None:
    log = []
    with pytest.raises(RuntimeError):
        run_steps([(_boom, lambda: log.append("undo-the-failure"))])
    assert log == []
""",
        imports="from rollback_steps import run_steps\n",
    ),
)


_G030 = D2TaskSpec(
    template_id="d5_error.redact_secrets",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-redact-secrets",
    module="redact_secrets",
    module_doc="Scrubbing the credentials out of a failure before anything writes it down.",
    issue=(
        "redact_error() is documented to scrub every known credential out of a failure before "
        "it is logged. Reviewers report that a credential quoted twice in one message is only "
        "scrubbed the first time, and that when one credential is the opening of another the "
        "tail of the longer one is left in the log."
    ),
    expected=(
        "redact_error(error, secrets) returns the text of the error with every occurrence of "
        "every secret replaced by '***', the longer secrets being scrubbed first so that a "
        "secret contained in another cannot leave the rest of it behind."
    ),
    baseline_reason=(
        "it replaces one occurrence per secret and works through the secrets in the order it "
        "was handed them rather than longest first"
    ),
    edge_cases=(
        "every occurrence of a secret is scrubbed, not only the first",
        "a secret contained in a longer one does not leave the rest behind",
    ),
    imports="import re\n",
    baseline='''def redact_error(error, secrets):
    """Return the text of `error` with every known secret scrubbed out."""
    text = str(error)
    for secret in secrets:
        text = text.replace(secret, "***", 1)
    return text''',
    variant_one='''def redact_error(error, secrets):
    """Return the text of `error` with every known secret scrubbed out."""
    text = str(error)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "***")
    return text''',
    variant_two='''def redact_error(error, secrets):
    """Return the text of `error` with every known secret scrubbed out."""
    ordered = sorted(secrets, key=len, reverse=True)
    if not ordered:
        return str(error)
    pattern = "|".join(re.escape(secret) for secret in ordered)
    return re.sub(pattern, "***", str(error))''',
    variant_three='''def redact_error(error, secrets):
    """Return the text of `error` with every known secret scrubbed out."""
    text = str(error)
    for secret in secrets:
        text = text.replace(secret, "***")
    return text''',
    variant_four='''def redact_error(error, secrets):
    """Return the text of `error` with every known secret scrubbed out."""
    text = str(error)
    for secret in sorted(secrets, key=len, reverse=True):
        text = text.replace(secret, "***", 1)
    return text''',
    visible_test=_test_module(
        "redact_secrets",
        "Published contract for scrubbing a failure before it is logged.",
        """
def test_the_credential_is_scrubbed_out() -> None:
    assert redact_error(ValueError("login failed for hunter2"), ["hunter2"]) == (
        "login failed for ***"
    )


def test_two_separate_credentials_are_both_scrubbed() -> None:
    assert redact_error(ValueError("a=alpha b=beta"), ["alpha", "beta"]) == "a=*** b=***"


def test_a_message_holding_no_credential_is_untouched() -> None:
    assert redact_error(ValueError("no secrets here"), ["abc"]) == "no secrets here"
""",
        imports="from redact_secrets import redact_error\n",
    ),
    hidden_test=_test_module(
        "redact_secrets",
        "The part of the contract the published tests do not state.",
        """
def test_the_credential_is_scrubbed_out() -> None:
    assert redact_error(ValueError("login failed for hunter2"), ["hunter2"]) == (
        "login failed for ***"
    )


def test_every_occurrence_is_scrubbed_not_only_the_first() -> None:
    assert redact_error(ValueError("hunter2 then hunter2"), ["hunter2"]) == "*** then ***"


def test_a_secret_contained_in_a_longer_one_leaves_nothing_behind() -> None:
    assert redact_error(ValueError("token=pw123"), ["pw", "pw123"]) == "token=***"
""",
        imports="from redact_secrets import redact_error\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G031 = D2TaskSpec(
    template_id="d5_boundary.spiral_order",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-spiral-order",
    module="spiral_order",
    module_doc="Reading a rectangular grid inwards, one ring at a time.",
    issue=(
        "spiral() is documented to read a grid inwards ring by ring, each cell once. Callers "
        "report that a grid whose innermost ring is a single row reads part of that row twice, "
        "and that a grid with no rows at all raises instead of coming back empty."
    ),
    expected=(
        "spiral(grid) returns the cells of the grid read clockwise from the top left inwards, "
        "each cell exactly once, and returns nothing for a grid with no rows."
    ),
    baseline_reason=(
        "it always walks all four sides of a ring, so a ring only one row deep is walked back "
        "along, and it reads the width off the first row without checking there is one"
    ),
    edge_cases=(
        "a ring only one row deep is read once, not back along as well",
        "a grid with no rows returns nothing",
    ),
    baseline='''def spiral(grid):
    """Return the cells of `grid` read clockwise inwards."""
    rows = [list(row) for row in grid]
    out = []
    top, bottom = 0, len(rows) - 1
    left, right = 0, len(rows[0]) - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            out.append(rows[top][column])
        for row in range(top + 1, bottom + 1):
            out.append(rows[row][right])
        for column in range(right - 1, left - 1, -1):
            out.append(rows[bottom][column])
        for row in range(bottom - 1, top, -1):
            out.append(rows[row][left])
        top, bottom = top + 1, bottom - 1
        left, right = left + 1, right - 1
    return out''',
    variant_one='''def spiral(grid):
    """Return the cells of `grid` read clockwise inwards."""
    rows = [list(row) for row in grid]
    if not rows:
        return []
    out = []
    top, bottom = 0, len(rows) - 1
    left, right = 0, len(rows[0]) - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            out.append(rows[top][column])
        for row in range(top + 1, bottom + 1):
            out.append(rows[row][right])
        if top < bottom:
            for column in range(right - 1, left - 1, -1):
                out.append(rows[bottom][column])
        if left < right:
            for row in range(bottom - 1, top, -1):
                out.append(rows[row][left])
        top, bottom = top + 1, bottom - 1
        left, right = left + 1, right - 1
    return out''',
    variant_two='''def spiral(grid):
    """Return the cells of `grid` read clockwise inwards."""
    rows = [list(row) for row in grid]
    if not rows or not rows[0]:
        return []
    height, width = len(rows), len(rows[0])
    headings = ((0, 1), (1, 0), (0, -1), (-1, 0))
    seen = set()
    out = []
    row = column = facing = 0
    for _ in range(height * width):
        out.append(rows[row][column])
        seen.add((row, column))
        for turn in range(4):
            step = headings[(facing + turn) % 4]
            ahead = (row + step[0], column + step[1])
            inside = 0 <= ahead[0] < height and 0 <= ahead[1] < width
            if inside and ahead not in seen:
                facing = (facing + turn) % 4
                row, column = ahead
                break
    return out''',
    variant_three='''def spiral(grid):
    """Return the cells of `grid` read clockwise inwards."""
    rows = [list(row) for row in grid]
    out = []
    top, bottom = 0, len(rows) - 1
    left, right = 0, len(rows[0]) - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            out.append(rows[top][column])
        for row in range(top + 1, bottom + 1):
            out.append(rows[row][right])
        if top < bottom:
            for column in range(right - 1, left - 1, -1):
                out.append(rows[bottom][column])
        if left < right:
            for row in range(bottom - 1, top, -1):
                out.append(rows[row][left])
        top, bottom = top + 1, bottom - 1
        left, right = left + 1, right - 1
    return out''',
    variant_four='''def spiral(grid):
    """Return the cells of `grid` read clockwise inwards."""
    rows = [list(row) for row in grid]
    if not rows:
        return []
    out = []
    top, bottom = 0, len(rows) - 1
    left, right = 0, len(rows[0]) - 1
    while top <= bottom and left <= right:
        for column in range(left, right + 1):
            out.append(rows[top][column])
        for row in range(top + 1, bottom + 1):
            out.append(rows[row][right])
        for column in range(right - 1, left - 1, -1):
            out.append(rows[bottom][column])
        for row in range(bottom - 1, top, -1):
            out.append(rows[row][left])
        top, bottom = top + 1, bottom - 1
        left, right = left + 1, right - 1
    return out''',
    visible_test=_test_module(
        "spiral_order",
        "Published contract for reading a grid inwards.",
        """
def test_a_two_by_two_grid_reads_round_once() -> None:
    assert spiral([[1, 2], [3, 4]]) == [1, 2, 4, 3]


def test_a_two_row_grid_reads_along_and_back() -> None:
    assert spiral([[1, 2, 3, 4], [5, 6, 7, 8]]) == [1, 2, 3, 4, 8, 7, 6, 5]
""",
        imports="from spiral_order import spiral\n",
    ),
    hidden_test=_test_module(
        "spiral_order",
        "The part of the contract the published tests do not state.",
        """
def test_a_two_by_two_grid_reads_round_once() -> None:
    assert spiral([[1, 2], [3, 4]]) == [1, 2, 4, 3]


def test_a_ring_one_row_deep_is_read_once() -> None:
    grid = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
    assert spiral(grid) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]


def test_a_grid_with_no_rows_reads_nothing() -> None:
    assert spiral([]) == []
""",
        imports="from spiral_order import spiral\n",
    ),
)


_G032 = D2TaskSpec(
    template_id="d5_boundary.split_on_marker",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-split-on-marker",
    module="split_on_marker",
    module_doc="Cutting a stream into sections, each opened by the entry that marks it.",
    issue=(
        "split_sections() is documented to cut a stream into sections, each opened by a marker "
        "and carrying it. Callers report that a stream opening on a marker comes back with an "
        "empty section in front of it, and that an empty stream comes back holding one empty "
        "section rather than none at all."
    ),
    expected=(
        "split_sections(items, is_marker) returns the sections of the stream in order, each "
        "one opened by the marker that introduced it and carrying it, whatever comes before "
        "the first marker forming a section of its own, and no empty section ever produced."
    ),
    baseline_reason=(
        "it closes the section in hand whenever a marker arrives and again when the stream "
        "ends, without checking either time that the section holds anything"
    ),
    edge_cases=(
        "a stream opening on a marker has no empty section in front of it",
        "an empty stream produces no sections at all",
    ),
    baseline='''def split_sections(items, is_marker):
    """Return the sections of `items`, each opened by a marker."""
    sections = []
    current = []
    for item in items:
        if is_marker(item):
            sections.append(current)
            current = [item]
        else:
            current.append(item)
    sections.append(current)
    return sections''',
    variant_one='''def split_sections(items, is_marker):
    """Return the sections of `items`, each opened by a marker."""
    sections = []
    current = []
    for item in items:
        if is_marker(item):
            if current:
                sections.append(current)
            current = [item]
        else:
            current.append(item)
    if current:
        sections.append(current)
    return sections''',
    variant_two='''def split_sections(items, is_marker):
    """Return the sections of `items`, each opened by a marker."""
    entries = list(items)
    if not entries:
        return []
    opens = [position for position, item in enumerate(entries) if is_marker(item)]
    bounds = opens if opens and opens[0] == 0 else [0, *opens]
    sections = []
    for place, start in enumerate(bounds):
        stop = bounds[place + 1] if place + 1 < len(bounds) else len(entries)
        sections.append(entries[start:stop])
    return sections''',
    variant_three='''def split_sections(items, is_marker):
    """Return the sections of `items`, each opened by a marker."""
    sections = []
    current = []
    for item in items:
        if is_marker(item):
            if current:
                sections.append(current)
            current = [item]
        else:
            current.append(item)
    sections.append(current)
    return sections''',
    variant_four='''def split_sections(items, is_marker):
    """Return the sections of `items`, each opened by a marker."""
    sections = []
    current = []
    for item in items:
        if is_marker(item):
            sections.append(current)
            current = [item]
        else:
            current.append(item)
    if current:
        sections.append(current)
    return sections''',
    visible_test=_test_module(
        "split_on_marker",
        "Published contract for cutting a stream into marked sections.",
        """
def test_a_marker_opens_the_section_it_belongs_to() -> None:
    assert split_sections(["a", "M", "b"], lambda item: item == "M") == [["a"], ["M", "b"]]


def test_a_stream_with_no_marker_is_one_section() -> None:
    assert split_sections(["a", "b"], lambda item: item == "M") == [["a", "b"]]
""",
        imports="from split_on_marker import split_sections\n",
    ),
    hidden_test=_test_module(
        "split_on_marker",
        "The part of the contract the published tests do not state.",
        """
def test_a_marker_opens_the_section_it_belongs_to() -> None:
    assert split_sections(["a", "M", "b"], lambda item: item == "M") == [["a"], ["M", "b"]]


def test_a_stream_opening_on_a_marker_has_nothing_in_front_of_it() -> None:
    assert split_sections(["M", "a"], lambda item: item == "M") == [["M", "a"]]


def test_an_empty_stream_produces_no_sections() -> None:
    assert split_sections([], lambda item: item == "M") == []
""",
        imports="from split_on_marker import split_sections\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G033 = D2TaskSpec(
    template_id="d5_numeric.reading_spread",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-reading-spread",
    module="reading_spread",
    module_doc="Measuring how far a set of readings sits from its own middle.",
    issue=(
        "variance() is documented to return the mean of the squared deviations. Analysts "
        "report that a set whose mean is not a whole number comes back with the wrong spread, "
        "and that an empty set raises a division error rather than saying what is wrong."
    ),
    expected=(
        "variance(readings) returns the mean of the squared deviations of the readings from "
        "their mean, and raises ValueError when there are no readings."
    ),
    baseline_reason=(
        "it takes the mean with a floor division, so a mean that is not whole is truncated "
        "before the deviations are measured, and it never checks there are readings at all"
    ),
    edge_cases=(
        "a mean that is not a whole number is not truncated",
        "no readings at all is refused",
    ),
    baseline='''def variance(readings):
    """Return the mean squared deviation of `readings` from their mean."""
    values = list(readings)
    mean = sum(values) // len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)''',
    variant_one='''def variance(readings):
    """Return the mean squared deviation of `readings` from their mean."""
    values = list(readings)
    if not values:
        raise ValueError("variance needs at least one reading")
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)''',
    variant_two='''def variance(readings):
    """Return the mean squared deviation of `readings` from their mean."""
    values = list(readings)
    count = len(values)
    if count == 0:
        raise ValueError("variance needs at least one reading")
    total = sum(values)
    squares = sum(value * value for value in values)
    return squares / count - (total / count) ** 2''',
    variant_three='''def variance(readings):
    """Return the mean squared deviation of `readings` from their mean."""
    values = list(readings)
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)''',
    variant_four='''def variance(readings):
    """Return the mean squared deviation of `readings` from their mean."""
    values = list(readings)
    if not values:
        raise ValueError("variance needs at least one reading")
    mean = sum(values) // len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)''',
    visible_test=_test_module(
        "reading_spread",
        "Published contract for measuring the spread of a set of readings.",
        """
def test_readings_that_are_all_equal_have_no_spread() -> None:
    assert variance([5, 5, 5]) == 0.0


def test_readings_around_a_whole_mean() -> None:
    assert variance([2, 4, 6]) == pytest.approx(8 / 3)


def test_a_single_reading_has_no_spread() -> None:
    assert variance([7]) == 0.0
""",
        imports="import pytest\n\nfrom reading_spread import variance\n",
    ),
    hidden_test=_test_module(
        "reading_spread",
        "The part of the contract the published tests do not state.",
        """
def test_readings_that_are_all_equal_have_no_spread() -> None:
    assert variance([5, 5, 5]) == 0.0


def test_a_mean_that_is_not_whole_is_not_truncated() -> None:
    assert variance([1, 2]) == pytest.approx(0.25)


def test_no_readings_at_all_is_refused() -> None:
    with pytest.raises(ValueError):
        variance([])
""",
        imports="import pytest\n\nfrom reading_spread import variance\n",
    ),
)


_G034 = D2TaskSpec(
    template_id="d5_numeric.proportional_allocate",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-proportional-allocate",
    module="proportional_allocate",
    module_doc="Dividing a whole total across claimants in proportion to their weights.",
    issue=(
        "allocate() is documented to divide a whole total across weighted claimants. "
        "Accounting reports that the parts sometimes come to less than the total, and that "
        "weights that are all zero raise a division error rather than being refused."
    ),
    expected=(
        "allocate(total, weights) returns one whole part per weight, proportional to the "
        "weights and summing to exactly the total, whatever is left over after the "
        "proportional shares going to the largest fractions first and to the earliest "
        "claimant on a tie, and raises ValueError when the weights sum to zero."
    ),
    baseline_reason=(
        "it floors each proportional share and hands back what is left of the total to nobody, "
        "and it divides by the total weight without checking there is any"
    ),
    edge_cases=(
        "the parts sum to exactly the total",
        "weights summing to zero are refused",
    ),
    baseline='''def allocate(total, weights):
    """Return whole parts of `total` proportional to `weights`."""
    share = sum(weights)
    return [total * weight // share for weight in weights]''',
    variant_one='''def allocate(total, weights):
    """Return whole parts of `total` proportional to `weights`."""
    share = sum(weights)
    if share == 0:
        raise ValueError("the weights must not sum to zero")
    parts = [total * weight // share for weight in weights]
    fractions = [(total * weight) % share for weight in weights]
    order = sorted(range(len(weights)), key=lambda index: (-fractions[index], index))
    for index in order[: total - sum(parts)]:
        parts[index] += 1
    return parts''',
    variant_two='''def allocate(total, weights):
    """Return whole parts of `total` proportional to `weights`."""
    share = sum(weights)
    if share == 0:
        raise ValueError("the weights must not sum to zero")
    parts = []
    fractions = []
    for weight in weights:
        exact = total * weight
        whole = exact // share
        parts.append(whole)
        fractions.append(exact - whole * share)
    for _ in range(total - sum(parts)):
        best = 0
        for index in range(1, len(fractions)):
            if fractions[index] > fractions[best]:
                best = index
        parts[best] += 1
        fractions[best] = -1
    return parts''',
    variant_three='''def allocate(total, weights):
    """Return whole parts of `total` proportional to `weights`."""
    share = sum(weights)
    parts = [total * weight // share for weight in weights]
    fractions = [(total * weight) % share for weight in weights]
    order = sorted(range(len(weights)), key=lambda index: (-fractions[index], index))
    for index in order[: total - sum(parts)]:
        parts[index] += 1
    return parts''',
    variant_four='''def allocate(total, weights):
    """Return whole parts of `total` proportional to `weights`."""
    share = sum(weights)
    if share == 0:
        raise ValueError("the weights must not sum to zero")
    return [total * weight // share for weight in weights]''',
    visible_test=_test_module(
        "proportional_allocate",
        "Published contract for dividing a total across weighted claimants.",
        """
def test_equal_weights_divide_evenly() -> None:
    assert allocate(100, [1, 1]) == [50, 50]


def test_weights_that_divide_exactly_need_nothing_carried() -> None:
    assert allocate(90, [1, 2]) == [30, 60]
""",
        imports="from proportional_allocate import allocate\n",
    ),
    hidden_test=_test_module(
        "proportional_allocate",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_equal_weights_divide_evenly() -> None:
    assert allocate(100, [1, 1]) == [50, 50]


def test_the_parts_sum_to_exactly_the_total() -> None:
    assert allocate(10, [1, 1, 1]) == [4, 3, 3]


def test_weights_summing_to_zero_are_refused() -> None:
    with pytest.raises(ValueError):
        allocate(10, [0, 0])
""",
        imports="from proportional_allocate import allocate\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G035 = D2TaskSpec(
    template_id="d5_parsing.markdown_links",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-markdown-links",
    module="markdown_links",
    module_doc="Picking the inline links out of a piece of marked-up prose.",
    issue=(
        "links() is documented to pick the inline links out of marked-up prose. Reviewers "
        "report that an inline image is reported as though it were a link, and that a link "
        "left with nothing to point at is reported with an empty target."
    ),
    expected=(
        "links(text) returns the inline links of the text in order as (label, target) pairs. "
        "An image, which is the same shape introduced by an exclamation mark, is not a link, "
        "and a link whose target is empty is left out."
    ),
    baseline_reason=(
        "it takes every label-and-target shape it finds without looking at the character in "
        "front of it or at whether the target holds anything"
    ),
    edge_cases=(
        "an image is not reported as a link",
        "a link with an empty target is left out",
    ),
    baseline='''def links(text):
    """Return the (label, target) pairs of the inline links in `text`."""
    found = []
    position = 0
    while True:
        opened = text.find("[", position)
        if opened < 0:
            break
        closed = text.find("]", opened)
        if closed < 0 or text[closed + 1 : closed + 2] != "(":
            position = opened + 1
            continue
        ends = text.find(")", closed)
        found.append((text[opened + 1 : closed], text[closed + 2 : ends]))
        position = ends + 1
    return found''',
    variant_one='''def links(text):
    """Return the (label, target) pairs of the inline links in `text`."""
    found = []
    position = 0
    while True:
        opened = text.find("[", position)
        if opened < 0:
            break
        closed = text.find("]", opened)
        if closed < 0 or text[closed + 1 : closed + 2] != "(":
            position = opened + 1
            continue
        ends = text.find(")", closed)
        target = text[closed + 2 : ends]
        image = opened > 0 and text[opened - 1] == "!"
        if target and not image:
            found.append((text[opened + 1 : closed], target))
        position = ends + 1
    return found''',
    variant_two='''def links(text):
    """Return the (label, target) pairs of the inline links in `text`."""
    found = []
    rest = text
    while "](" in rest:
        head, _, rest = rest.partition("](")
        opened = head.rfind("[")
        if opened < 0:
            continue
        target, closed, remainder = rest.partition(")")
        if not closed:
            break
        rest = remainder
        image = opened > 0 and head[opened - 1] == "!"
        if target and not image:
            found.append((head[opened + 1 :], target))
    return found''',
    variant_three='''def links(text):
    """Return the (label, target) pairs of the inline links in `text`."""
    found = []
    position = 0
    while True:
        opened = text.find("[", position)
        if opened < 0:
            break
        closed = text.find("]", opened)
        if closed < 0 or text[closed + 1 : closed + 2] != "(":
            position = opened + 1
            continue
        ends = text.find(")", closed)
        image = opened > 0 and text[opened - 1] == "!"
        if not image:
            found.append((text[opened + 1 : closed], text[closed + 2 : ends]))
        position = ends + 1
    return found''',
    variant_four='''def links(text):
    """Return the (label, target) pairs of the inline links in `text`."""
    found = []
    position = 0
    while True:
        opened = text.find("[", position)
        if opened < 0:
            break
        closed = text.find("]", opened)
        if closed < 0 or text[closed + 1 : closed + 2] != "(":
            position = opened + 1
            continue
        ends = text.find(")", closed)
        target = text[closed + 2 : ends]
        if target:
            found.append((text[opened + 1 : closed], target))
        position = ends + 1
    return found''',
    visible_test=_test_module(
        "markdown_links",
        "Published contract for picking links out of prose.",
        """
def test_the_links_come_back_in_order() -> None:
    text = "see [docs](http://a) and [more](http://b)"
    assert links(text) == [("docs", "http://a"), ("more", "http://b")]


def test_prose_with_no_links_yields_nothing() -> None:
    assert links("nothing to follow here") == []
""",
        imports="from markdown_links import links\n",
    ),
    hidden_test=_test_module(
        "markdown_links",
        "The part of the contract the published tests do not state.",
        """
def test_the_links_come_back_in_order() -> None:
    text = "see [docs](http://a) and [more](http://b)"
    assert links(text) == [("docs", "http://a"), ("more", "http://b")]


def test_an_image_is_not_a_link() -> None:
    assert links("![shot](pic.png) and [docs](http://a)") == [("docs", "http://a")]


def test_a_link_with_an_empty_target_is_left_out() -> None:
    assert links("[empty]() and [docs](http://a)") == [("docs", "http://a")]
""",
        imports="from markdown_links import links\n",
    ),
)


_G036 = D2TaskSpec(
    template_id="d5_parsing.postcode_format",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-postcode-format",
    module="postcode_format",
    module_doc="Putting a postcode into the shape the address file expects.",
    issue=(
        "normalise() is documented to put a postcode into its printed shape. Callers report "
        "that a code typed with its own space comes back with two spaces in it, and that "
        "something far too short to be a postcode comes back reshaped instead of refused."
    ),
    expected=(
        "normalise(text) returns the postcode uppercased with every space in the input "
        "removed and a single space put back before the last three characters, and raises "
        "ValueError for anything shorter than five characters once the spaces are gone."
    ),
    baseline_reason=(
        "it only trims the spaces at the two ends rather than removing all of them, and it "
        "reshapes whatever it is given without checking the length"
    ),
    edge_cases=(
        "a space inside the code is removed, not just the ones at the ends",
        "anything shorter than five characters is refused",
    ),
    baseline='''def normalise(text):
    """Return `text` as a printed postcode."""
    packed = text.strip().upper()
    return f"{packed[:-3]} {packed[-3:]}"''',
    variant_one='''def normalise(text):
    """Return `text` as a printed postcode."""
    packed = "".join(text.split()).upper()
    if len(packed) < 5:
        raise ValueError(f"a postcode needs at least five characters, got {text!r}")
    return f"{packed[:-3]} {packed[-3:]}"''',
    variant_two='''def normalise(text):
    """Return `text` as a printed postcode."""
    packed = "".join(letter for letter in text.upper() if not letter.isspace())
    if len(packed) < 5:
        raise ValueError(f"a postcode needs at least five characters, got {text!r}")
    cut = len(packed) - 3
    return packed[:cut] + " " + packed[cut:]''',
    variant_three='''def normalise(text):
    """Return `text` as a printed postcode."""
    packed = "".join(text.split()).upper()
    return f"{packed[:-3]} {packed[-3:]}"''',
    variant_four='''def normalise(text):
    """Return `text` as a printed postcode."""
    packed = text.strip().upper()
    if len(packed) < 5:
        raise ValueError(f"a postcode needs at least five characters, got {text!r}")
    return f"{packed[:-3]} {packed[-3:]}"''',
    visible_test=_test_module(
        "postcode_format",
        "Published contract for printing a postcode.",
        """
def test_a_packed_code_gains_its_space() -> None:
    assert normalise("ec1a1bb") == "EC1A 1BB"


def test_padding_at_the_ends_is_trimmed() -> None:
    assert normalise("  m11ae  ") == "M1 1AE"
""",
        imports="from postcode_format import normalise\n",
    ),
    hidden_test=_test_module(
        "postcode_format",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_packed_code_gains_its_space() -> None:
    assert normalise("ec1a1bb") == "EC1A 1BB"


def test_a_space_inside_the_code_is_removed_too() -> None:
    assert normalise("sw1a 1aa") == "SW1A 1AA"


def test_something_too_short_to_be_a_postcode_is_refused() -> None:
    with pytest.raises(ValueError):
        normalise("ab1")
""",
        imports="from postcode_format import normalise\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G037 = D2TaskSpec(
    template_id="d5_transform.secondary_order",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-secondary-order",
    module="secondary_order",
    module_doc="Ordering a table on one field, and settling the ties on another.",
    issue=(
        "order_records() is documented to order on a primary field and settle ties on a "
        "secondary one, highest first. Callers report that the ties come out lowest first, "
        "and that a record which simply does not carry the secondary field brings the whole "
        "sort down with a KeyError."
    ),
    expected=(
        "order_records(records, primary, secondary) returns the records ordered by the "
        "primary field ascending and, among records sharing a primary value, by the secondary "
        "field descending. A record that does not carry the secondary field comes after those "
        "that do, in the order it arrived."
    ),
    baseline_reason=(
        "it sorts on the pair of fields at once, which orders the secondary ascending like the "
        "primary, and it reads the secondary without checking the record carries it"
    ),
    edge_cases=(
        "records sharing a primary value are ordered by the secondary descending",
        "a record not carrying the secondary comes last, in arrival order",
    ),
    baseline='''def order_records(records, primary, secondary):
    """Return `records` ordered on `primary`, ties settled on `secondary`."""
    return sorted(records, key=lambda record: (record[primary], record[secondary]))''',
    variant_one='''def order_records(records, primary, secondary):
    """Return `records` ordered on `primary`, ties settled on `secondary`."""
    entries = list(records)
    carrying = [record for record in entries if secondary in record]
    lacking = [record for record in entries if secondary not in record]
    carrying.sort(key=lambda record: record[secondary], reverse=True)
    ordered = carrying + lacking
    ordered.sort(key=lambda record: record[primary])
    return ordered''',
    variant_two='''def order_records(records, primary, secondary):
    """Return `records` ordered on `primary`, ties settled on `secondary`."""
    entries = list(records)
    scale = sorted(
        {record[secondary] for record in entries if secondary in record}, reverse=True
    )

    def place(record):
        if secondary not in record:
            return (1, 0)
        return (0, scale.index(record[secondary]))

    return sorted(entries, key=lambda record: (record[primary], place(record)))''',
    variant_three='''def order_records(records, primary, secondary):
    """Return `records` ordered on `primary`, ties settled on `secondary`."""
    entries = list(records)
    entries.sort(key=lambda record: record[secondary], reverse=True)
    entries.sort(key=lambda record: record[primary])
    return entries''',
    variant_four='''def order_records(records, primary, secondary):
    """Return `records` ordered on `primary`, ties settled on `secondary`."""
    entries = list(records)
    carrying = [record for record in entries if secondary in record]
    lacking = [record for record in entries if secondary not in record]
    carrying.sort(key=lambda record: record[secondary])
    ordered = carrying + lacking
    ordered.sort(key=lambda record: record[primary])
    return ordered''',
    visible_test=_test_module(
        "secondary_order",
        "Published contract for ordering a table on two fields.",
        """
def test_records_come_back_ordered_on_the_primary() -> None:
    records = [
        {"team": "b", "score": 1},
        {"team": "a", "score": 2},
        {"team": "c", "score": 3},
    ]
    assert order_records(records, "team", "score") == [
        {"team": "a", "score": 2},
        {"team": "b", "score": 1},
        {"team": "c", "score": 3},
    ]


def test_a_single_record_comes_back_alone() -> None:
    assert order_records([{"team": "a", "score": 1}], "team", "score") == [
        {"team": "a", "score": 1}
    ]
""",
        imports="from secondary_order import order_records\n",
    ),
    hidden_test=_test_module(
        "secondary_order",
        "The part of the contract the published tests do not state.",
        """
def test_records_come_back_ordered_on_the_primary() -> None:
    records = [
        {"team": "b", "score": 1},
        {"team": "a", "score": 2},
        {"team": "c", "score": 3},
    ]
    assert order_records(records, "team", "score") == [
        {"team": "a", "score": 2},
        {"team": "b", "score": 1},
        {"team": "c", "score": 3},
    ]


def test_a_shared_primary_is_settled_on_the_secondary_descending() -> None:
    records = [
        {"team": "a", "score": 1},
        {"team": "a", "score": 3},
        {"team": "a", "score": 2},
    ]
    assert order_records(records, "team", "score") == [
        {"team": "a", "score": 3},
        {"team": "a", "score": 2},
        {"team": "a", "score": 1},
    ]


def test_a_record_without_the_secondary_comes_last() -> None:
    records = [{"team": "a", "score": 2}, {"team": "a"}]
    assert order_records(records, "team", "score") == [{"team": "a", "score": 2}, {"team": "a"}]
""",
        imports="from secondary_order import order_records\n",
    ),
)


_G038 = D2TaskSpec(
    template_id="d5_transform.swap_levels",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-swap-levels",
    module="swap_levels",
    module_doc="Turning a two-level mapping inside out so the inner keys sit on the outside.",
    issue=(
        "swap_levels() is documented to turn a two-level mapping inside out. Callers report "
        "that an inner key appearing under more than one outer key keeps only the last one, "
        "and that an outer key holding something other than a mapping fails with an "
        "AttributeError rather than saying what was wrong."
    ),
    expected=(
        "swap_levels(nested) returns the mapping with its two levels exchanged, so every "
        "inner key becomes an outer one holding every outer key that carried it, and raises "
        "ValueError when an outer key does not hold a mapping."
    ),
    baseline_reason=(
        "it assigns a fresh single-entry mapping for each inner key rather than adding to what "
        "is already there, and it walks the inner mapping without checking there is one"
    ),
    edge_cases=(
        "an inner key under several outer keys keeps all of them",
        "an outer key not holding a mapping is refused",
    ),
    baseline='''def swap_levels(nested):
    """Return `nested` with its two levels exchanged."""
    swapped = {}
    for outer, inner in nested.items():
        for key, value in inner.items():
            swapped[key] = {outer: value}
    return swapped''',
    variant_one='''def swap_levels(nested):
    """Return `nested` with its two levels exchanged."""
    swapped = {}
    for outer, inner in nested.items():
        if not isinstance(inner, dict):
            raise ValueError(f"{outer!r} does not hold a mapping")
        for key, value in inner.items():
            swapped.setdefault(key, {})[outer] = value
    return swapped''',
    variant_two='''def swap_levels(nested):
    """Return `nested` with its two levels exchanged."""
    for outer, inner in nested.items():
        if not isinstance(inner, dict):
            raise ValueError(f"{outer!r} does not hold a mapping")
    keys = []
    for inner in nested.values():
        for key in inner:
            if key not in keys:
                keys.append(key)
    return {
        key: {outer: inner[key] for outer, inner in nested.items() if key in inner}
        for key in keys
    }''',
    variant_three='''def swap_levels(nested):
    """Return `nested` with its two levels exchanged."""
    swapped = {}
    for outer, inner in nested.items():
        for key, value in inner.items():
            swapped.setdefault(key, {})[outer] = value
    return swapped''',
    variant_four='''def swap_levels(nested):
    """Return `nested` with its two levels exchanged."""
    swapped = {}
    for outer, inner in nested.items():
        if not isinstance(inner, dict):
            raise ValueError(f"{outer!r} does not hold a mapping")
        for key, value in inner.items():
            swapped[key] = {outer: value}
    return swapped''',
    visible_test=_test_module(
        "swap_levels",
        "Published contract for turning a two-level mapping inside out.",
        """
def test_the_two_levels_change_places() -> None:
    assert swap_levels({"a": {"x": 1}, "b": {"y": 2}}) == {"x": {"a": 1}, "y": {"b": 2}}


def test_an_empty_mapping_swaps_to_nothing() -> None:
    assert swap_levels({}) == {}
""",
        imports="from swap_levels import swap_levels\n",
    ),
    hidden_test=_test_module(
        "swap_levels",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_two_levels_change_places() -> None:
    assert swap_levels({"a": {"x": 1}, "b": {"y": 2}}) == {"x": {"a": 1}, "y": {"b": 2}}


def test_an_inner_key_under_several_outer_keys_keeps_them_all() -> None:
    assert swap_levels({"a": {"x": 1}, "b": {"x": 2}}) == {"x": {"a": 1, "b": 2}}


def test_an_outer_key_not_holding_a_mapping_is_refused() -> None:
    with pytest.raises(ValueError):
        swap_levels({"a": 5})
""",
        imports="from swap_levels import swap_levels\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G039 = D2TaskSpec(
    template_id="d5_state.recent_cache",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-recent-cache",
    module="recent_cache",
    module_doc="Keeping the keys most recently reached for, oldest first, up to a limit.",
    issue=(
        "record() is documented to keep the keys most recently reached for. Callers report "
        "that a key reached for twice appears twice in the list, and that the list grows "
        "past the limit it was given instead of dropping the oldest key."
    ),
    expected=(
        "record(order, key, limit) returns the keys in use oldest first after `key` has been "
        "reached for. A key already in use moves to the end rather than appearing twice, and "
        "once the limit would be passed the oldest keys are dropped until it is not."
    ),
    baseline_reason=(
        "it appends the key to a copy of the list without looking for it first and without "
        "looking at the limit at all"
    ),
    edge_cases=(
        "a key already in use moves to the end rather than appearing twice",
        "the list is trimmed to the limit by dropping the oldest",
    ),
    baseline='''def record(order, key, limit):
    """Return the keys in use, oldest first, after `key` is reached for."""
    return list(order) + [key]''',
    variant_one='''def record(order, key, limit):
    """Return the keys in use, oldest first, after `key` is reached for."""
    keys = [entry for entry in order if entry != key]
    keys.append(key)
    del keys[: max(len(keys) - limit, 0)]
    return keys''',
    variant_two='''def record(order, key, limit):
    """Return the keys in use, oldest first, after `key` is reached for."""
    keys = list(order)
    if key in keys:
        keys.remove(key)
    keys.append(key)
    while len(keys) > limit:
        keys.pop(0)
    return keys''',
    variant_three='''def record(order, key, limit):
    """Return the keys in use, oldest first, after `key` is reached for."""
    keys = [entry for entry in order if entry != key]
    keys.append(key)
    return keys''',
    variant_four='''def record(order, key, limit):
    """Return the keys in use, oldest first, after `key` is reached for."""
    keys = list(order) + [key]
    del keys[: max(len(keys) - limit, 0)]
    return keys''',
    visible_test=_test_module(
        "recent_cache",
        "Published contract for keeping the keys most recently reached for.",
        """
def test_a_fresh_key_joins_the_end() -> None:
    assert record(["a", "b"], "c", 5) == ["a", "b", "c"]


def test_the_first_key_starts_the_list() -> None:
    assert record([], "a", 5) == ["a"]
""",
        imports="from recent_cache import record\n",
    ),
    hidden_test=_test_module(
        "recent_cache",
        "The part of the contract the published tests do not state.",
        """
def test_a_fresh_key_joins_the_end() -> None:
    assert record(["a", "b"], "c", 5) == ["a", "b", "c"]


def test_a_key_already_in_use_moves_rather_than_repeats() -> None:
    assert record(["a", "b"], "a", 5) == ["b", "a"]


def test_the_oldest_key_is_dropped_at_the_limit() -> None:
    assert record(["a", "b"], "c", 2) == ["b", "c"]
""",
        imports="from recent_cache import record\n",
    ),
)


_G040 = D2TaskSpec(
    template_id="d5_state.inflight_claim",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-inflight-claim",
    module="inflight_claim",
    module_doc="Handing out the next piece of work and holding it for the worker who took it.",
    issue=(
        "next_claim() is documented to hand out the next piece of work nobody is holding. "
        "Operators report that a piece whose holder never came back stays out of circulation "
        "for ever, and that a piece already finished is handed out again."
    ),
    expected=(
        "next_claim(items, now, timeout) returns (id, items) for the first piece of work that "
        "is not finished and is not currently held, marking it held until now plus timeout. A "
        "hold that has run out counts as not held, a finished piece is never handed out, "
        "(None, items) comes back when there is nothing to hand out, and the caller's list is "
        "left alone."
    ),
    baseline_reason=(
        "it treats any hold at all as current however long ago it ran out, and it never looks "
        "at whether the piece is already finished"
    ),
    edge_cases=(
        "a hold that has run out counts as not held",
        "a finished piece is never handed out",
    ),
    baseline='''def next_claim(items, now, timeout):
    """Return (id, items) for the next piece of work to hand out."""
    entries = [dict(item) for item in items]
    for entry in entries:
        if entry["held_until"] is None:
            entry["held_until"] = now + timeout
            return entry["id"], entries
    return None, entries''',
    variant_one='''def next_claim(items, now, timeout):
    """Return (id, items) for the next piece of work to hand out."""
    entries = [dict(item) for item in items]
    for entry in entries:
        if entry["done"]:
            continue
        held = entry["held_until"]
        if held is None or held <= now:
            entry["held_until"] = now + timeout
            return entry["id"], entries
    return None, entries''',
    variant_two='''def next_claim(items, now, timeout):
    """Return (id, items) for the next piece of work to hand out."""
    entries = [dict(item) for item in items]
    free = [
        place
        for place, entry in enumerate(entries)
        if not entry["done"] and (entry["held_until"] is None or entry["held_until"] <= now)
    ]
    if not free:
        return None, entries
    taken = entries[free[0]]
    taken["held_until"] = now + timeout
    return taken["id"], entries''',
    variant_three='''def next_claim(items, now, timeout):
    """Return (id, items) for the next piece of work to hand out."""
    entries = [dict(item) for item in items]
    for entry in entries:
        held = entry["held_until"]
        if held is None or held <= now:
            entry["held_until"] = now + timeout
            return entry["id"], entries
    return None, entries''',
    variant_four='''def next_claim(items, now, timeout):
    """Return (id, items) for the next piece of work to hand out."""
    entries = [dict(item) for item in items]
    for entry in entries:
        if entry["done"]:
            continue
        if entry["held_until"] is None:
            entry["held_until"] = now + timeout
            return entry["id"], entries
    return None, entries''',
    visible_test=_test_module(
        "inflight_claim",
        "Published contract for handing out the next piece of work.",
        """
def test_a_free_piece_is_handed_out_and_held() -> None:
    items = [{"id": "a", "held_until": None, "done": False}]
    assert next_claim(items, 5, 10) == ("a", [{"id": "a", "held_until": 15, "done": False}])


def test_a_piece_held_by_somebody_else_is_not_handed_out() -> None:
    items = [{"id": "a", "held_until": 100, "done": False}]
    assert next_claim(items, 5, 10) == (None, [{"id": "a", "held_until": 100, "done": False}])


def test_the_callers_list_is_left_alone() -> None:
    items = [{"id": "a", "held_until": None, "done": False}]
    next_claim(items, 5, 10)
    assert items == [{"id": "a", "held_until": None, "done": False}]
""",
        imports="from inflight_claim import next_claim\n",
    ),
    hidden_test=_test_module(
        "inflight_claim",
        "The part of the contract the published tests do not state.",
        """
def test_a_free_piece_is_handed_out_and_held() -> None:
    items = [{"id": "a", "held_until": None, "done": False}]
    assert next_claim(items, 5, 10) == ("a", [{"id": "a", "held_until": 15, "done": False}])


def test_a_hold_that_has_run_out_counts_as_free() -> None:
    items = [{"id": "a", "held_until": 3, "done": False}]
    assert next_claim(items, 5, 10) == ("a", [{"id": "a", "held_until": 15, "done": False}])


def test_a_finished_piece_is_never_handed_out() -> None:
    items = [{"id": "a", "held_until": None, "done": True}]
    assert next_claim(items, 5, 10) == (None, [{"id": "a", "held_until": None, "done": True}])
""",
        imports="from inflight_claim import next_claim\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G041 = D2TaskSpec(
    template_id="d5_error.quarantine_batch",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-quarantine-batch",
    module="quarantine_batch",
    module_doc="Working through a batch and setting aside the records that will not go through.",
    issue=(
        "process() is documented to work through a batch, setting aside the records that "
        "raise. Operators report that the quarantine file holds exception objects rather than "
        "anything readable, and that cancelling the run leaves the cancellation sitting in the "
        "quarantine file instead of stopping the batch."
    ),
    expected=(
        "process(records, handle) returns (results, quarantined). Results holds what the "
        "handler returned for the records it accepted, quarantined holds (record, reason) for "
        "the ones that raised with the reason being the text of the error, both in the order "
        "the records arrived, and anything that is not an ordinary error is raised on rather "
        "than quarantined."
    ),
    baseline_reason=(
        "it stores the exception object itself as the reason, and it catches every "
        "interruption there is rather than only ordinary errors"
    ),
    edge_cases=(
        "the reason recorded is the text of the error, not the error itself",
        "an interruption that is not an ordinary error is raised on",
    ),
    baseline='''def process(records, handle):
    """Return (results, quarantined) after working through `records`."""
    results = []
    quarantined = []
    for record in records:
        try:
            results.append(handle(record))
        except BaseException as error:
            quarantined.append((record, error))
    return results, quarantined''',
    variant_one='''def process(records, handle):
    """Return (results, quarantined) after working through `records`."""
    results = []
    quarantined = []
    for record in records:
        try:
            results.append(handle(record))
        except Exception as error:
            quarantined.append((record, str(error)))
    return results, quarantined''',
    variant_two='''def process(records, handle):
    """Return (results, quarantined) after working through `records`."""
    outcomes = []
    for record in records:
        try:
            outcomes.append((True, record, handle(record)))
        except Exception as error:
            outcomes.append((False, record, str(error)))
    results = [value for accepted, _, value in outcomes if accepted]
    quarantined = [(record, why) for accepted, record, why in outcomes if not accepted]
    return results, quarantined''',
    variant_three='''def process(records, handle):
    """Return (results, quarantined) after working through `records`."""
    results = []
    quarantined = []
    for record in records:
        try:
            results.append(handle(record))
        except BaseException as error:
            quarantined.append((record, str(error)))
    return results, quarantined''',
    variant_four='''def process(records, handle):
    """Return (results, quarantined) after working through `records`."""
    results = []
    quarantined = []
    for record in records:
        try:
            results.append(handle(record))
        except Exception as error:
            quarantined.append((record, error))
    return results, quarantined''',
    visible_test=_test_module(
        "quarantine_batch",
        "Published contract for working through a batch.",
        """
def test_a_batch_that_all_goes_through_quarantines_nothing() -> None:
    assert process([1, 2], lambda number: number * 2) == ([2, 4], [])


def test_an_empty_batch_yields_nothing_either_way() -> None:
    assert process([], lambda number: number) == ([], [])
""",
        imports="from quarantine_batch import process\n",
    ),
    hidden_test=_test_module(
        "quarantine_batch",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _refuse_three(number):
    if number == 3:
        raise ValueError("three is not allowed")
    return number * 2


def _cancel(number):
    raise KeyboardInterrupt


def test_a_batch_that_all_goes_through_quarantines_nothing() -> None:
    assert process([1, 2], lambda number: number * 2) == ([2, 4], [])


def test_the_reason_recorded_is_the_text_of_the_error() -> None:
    assert process([1, 3], _refuse_three) == ([2], [(3, "three is not allowed")])


def test_an_interruption_stops_the_batch_rather_than_being_quarantined() -> None:
    with pytest.raises(KeyboardInterrupt):
        process([1], _cancel)
""",
        imports="from quarantine_batch import process\n",
    ),
)


_G042 = D2TaskSpec(
    template_id="d5_error.cleanup_suppressed",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-cleanup-suppressed",
    module="cleanup_suppressed",
    module_doc="Running the tidying up without letting it hide what actually went wrong.",
    issue=(
        "run_with_cleanup() is documented to tidy up whatever happens without hiding the "
        "original failure. Callers report that when the tidying up itself fails the original "
        "error disappears and the tidying-up error is reported instead, and that the tidying "
        "up stops at the first handler that fails so the rest never run."
    ),
    expected=(
        "run_with_cleanup(body, cleanups) runs the body, then runs every cleanup in order "
        "whatever happened. If the body failed, that failure is the one raised and no cleanup "
        "failure replaces it. If the body succeeded and a cleanup failed, the first cleanup "
        "failure is raised once the remaining cleanups have run."
    ),
    baseline_reason=(
        "it runs the cleanups in a finally block, where a cleanup that raises both replaces "
        "the failure already in flight and abandons the cleanups after it"
    ),
    edge_cases=(
        "a failing cleanup does not replace the failure the body raised",
        "a failing cleanup does not stop the cleanups after it",
    ),
    baseline='''def run_with_cleanup(body, cleanups):
    """Run `body`, then every cleanup, without losing what actually went wrong."""
    try:
        return body()
    finally:
        for cleanup in cleanups:
            cleanup()''',
    variant_one='''def run_with_cleanup(body, cleanups):
    """Run `body`, then every cleanup, without losing what actually went wrong."""
    failure = None
    result = None
    try:
        result = body()
    except Exception as error:
        failure = error
    later = None
    for cleanup in cleanups:
        try:
            cleanup()
        except Exception as error:
            if later is None:
                later = error
    if failure is not None:
        raise failure
    if later is not None:
        raise later
    return result''',
    variant_two='''def run_with_cleanup(body, cleanups):
    """Run `body`, then every cleanup, without losing what actually went wrong."""
    produced = []
    failures = []
    try:
        produced.append(body())
    except Exception as error:
        failures.append(error)
    for cleanup in cleanups:
        try:
            cleanup()
        except Exception as error:
            failures.append(error)
    if failures:
        raise failures[0]
    return produced[0]''',
    variant_three='''def run_with_cleanup(body, cleanups):
    """Run `body`, then every cleanup, without losing what actually went wrong."""
    failure = None
    result = None
    try:
        result = body()
    except Exception as error:
        failure = error
    try:
        for cleanup in cleanups:
            cleanup()
    except Exception as error:
        if failure is None:
            failure = error
    if failure is not None:
        raise failure
    return result''',
    variant_four='''def run_with_cleanup(body, cleanups):
    """Run `body`, then every cleanup, without losing what actually went wrong."""
    try:
        return body()
    finally:
        last = None
        for cleanup in cleanups:
            try:
                cleanup()
            except Exception as error:
                last = error
        if last is not None:
            raise last''',
    visible_test=_test_module(
        "cleanup_suppressed",
        "Published contract for tidying up after a piece of work.",
        """
def test_the_body_result_comes_back_and_the_cleanups_run() -> None:
    log = []
    result = run_with_cleanup(lambda: 7, [lambda: log.append("one"), lambda: log.append("two")])
    assert result == 7
    assert log == ["one", "two"]


def test_no_cleanups_at_all_is_fine() -> None:
    assert run_with_cleanup(lambda: 7, []) == 7
""",
        imports="from cleanup_suppressed import run_with_cleanup\n",
    ),
    hidden_test=_test_module(
        "cleanup_suppressed",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _body_fails():
    raise RuntimeError("the body refused")


def _cleanup_fails():
    raise ValueError("the cleanup refused")


def test_the_body_result_comes_back_and_the_cleanups_run() -> None:
    log = []
    result = run_with_cleanup(lambda: 7, [lambda: log.append("one"), lambda: log.append("two")])
    assert result == 7
    assert log == ["one", "two"]


def test_a_failing_cleanup_does_not_replace_the_bodys_failure() -> None:
    with pytest.raises(RuntimeError):
        run_with_cleanup(_body_fails, [_cleanup_fails])


def test_a_failing_cleanup_does_not_stop_the_ones_after_it() -> None:
    log = []
    with pytest.raises(ValueError):
        run_with_cleanup(lambda: 7, [_cleanup_fails, lambda: log.append("after")])
    assert log == ["after"]
""",
        imports="from cleanup_suppressed import run_with_cleanup\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G043 = D2TaskSpec(
    template_id="d5_boundary.unzip_pairs",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-unzip-pairs",
    module="unzip_pairs",
    module_doc="Taking a list of pairs apart into the two columns it was built from.",
    issue=(
        "unzip() is documented to take a list of pairs apart into two columns. Callers report "
        "that an empty list raises about unpacking instead of coming back with two empty "
        "columns, and that a row carrying a third entry is quietly taken apart as though the "
        "third were not there."
    ),
    expected=(
        "unzip(pairs) returns (firsts, seconds), the two columns of the pairs in order. An "
        "empty list gives two empty columns, and a row that is not exactly two long is refused "
        "with ValueError."
    ),
    baseline_reason=(
        "it unpacks the transposed rows straight into two names, which has nothing to unpack "
        "for an empty list and quietly drops the surplus of a longer row"
    ),
    edge_cases=(
        "an empty list gives two empty columns",
        "a row that is not exactly two long is refused",
    ),
    baseline='''def unzip(pairs):
    """Return the two columns of `pairs`."""
    firsts, seconds = zip(*pairs)
    return list(firsts), list(seconds)''',
    variant_one='''def unzip(pairs):
    """Return the two columns of `pairs`."""
    firsts = []
    seconds = []
    for row in pairs:
        entries = tuple(row)
        if len(entries) != 2:
            raise ValueError(f"expected a pair, found a row of {len(entries)}")
        firsts.append(entries[0])
        seconds.append(entries[1])
    return firsts, seconds''',
    variant_two='''def unzip(pairs):
    """Return the two columns of `pairs`."""
    rows = [tuple(row) for row in pairs]
    wrong = [len(row) for row in rows if len(row) != 2]
    if wrong:
        raise ValueError(f"expected pairs, found rows of {wrong}")
    if not rows:
        return [], []
    columns = list(zip(*rows))
    return list(columns[0]), list(columns[1])''',
    variant_three='''def unzip(pairs):
    """Return the two columns of `pairs`."""
    rows = list(pairs)
    if not rows:
        return [], []
    firsts, seconds = zip(*rows)
    return list(firsts), list(seconds)''',
    variant_four='''def unzip(pairs):
    """Return the two columns of `pairs`."""
    rows = [tuple(row) for row in pairs]
    for row in rows:
        if len(row) != 2:
            raise ValueError(f"expected a pair, found a row of {len(row)}")
    firsts, seconds = zip(*rows)
    return list(firsts), list(seconds)''',
    visible_test=_test_module(
        "unzip_pairs",
        "Published contract for taking a list of pairs apart.",
        """
def test_the_two_columns_come_back_in_order() -> None:
    assert unzip([("a", 1), ("b", 2)]) == (["a", "b"], [1, 2])


def test_a_single_pair_gives_two_columns_of_one() -> None:
    assert unzip([("a", 1)]) == (["a"], [1])
""",
        imports="from unzip_pairs import unzip\n",
    ),
    hidden_test=_test_module(
        "unzip_pairs",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_two_columns_come_back_in_order() -> None:
    assert unzip([("a", 1), ("b", 2)]) == (["a", "b"], [1, 2])


def test_an_empty_list_gives_two_empty_columns() -> None:
    assert unzip([]) == ([], [])


def test_a_row_that_is_not_a_pair_is_refused() -> None:
    with pytest.raises(ValueError):
        unzip([("a", 1), ("b", 2, 3)])
""",
        imports="from unzip_pairs import unzip\n",
    ),
)


_G044 = D2TaskSpec(
    template_id="d5_boundary.sparse_expand",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-sparse-expand",
    module="sparse_expand",
    module_doc="Filling a run of slots from the few positions that were actually given.",
    issue=(
        "expand() is documented to fill a run of slots from the positions given, everything "
        "else taking a default. Callers report that a position outside the run either writes "
        "at the wrong end or fails with an IndexError rather than being refused, and that "
        "filling with a list as the default hands every slot the same list."
    ),
    expected=(
        "expand(entries, length, default) returns a run of `length` slots, each named position "
        "holding its value and every other slot holding its own copy of the default, and "
        "raises ValueError for a position outside the run."
    ),
    baseline_reason=(
        "it builds the run by repeating the one default object, so every untouched slot is the "
        "same object, and it writes by plain indexing, which wraps for a negative position and "
        "raises an IndexError past the end"
    ),
    edge_cases=(
        "a position outside the run is refused",
        "each untouched slot holds its own copy of the default",
    ),
    imports="import copy\n",
    baseline='''def expand(entries, length, default):
    """Return a run of `length` slots filled from `entries`."""
    slots = [default] * length
    for index, value in entries:
        slots[index] = value
    return slots''',
    variant_one='''def expand(entries, length, default):
    """Return a run of `length` slots filled from `entries`."""
    slots = [copy.deepcopy(default) for _ in range(length)]
    for index, value in entries:
        if not 0 <= index < length:
            raise ValueError(f"position {index} is outside a run of {length}")
        slots[index] = value
    return slots''',
    variant_two='''def expand(entries, length, default):
    """Return a run of `length` slots filled from `entries`."""
    placed = {}
    for index, value in entries:
        if not 0 <= index < length:
            raise ValueError(f"position {index} is outside a run of {length}")
        placed[index] = value
    return [
        placed[index] if index in placed else copy.deepcopy(default)
        for index in range(length)
    ]''',
    variant_three='''def expand(entries, length, default):
    """Return a run of `length` slots filled from `entries`."""
    slots = [default] * length
    for index, value in entries:
        if not 0 <= index < length:
            raise ValueError(f"position {index} is outside a run of {length}")
        slots[index] = value
    return slots''',
    variant_four='''def expand(entries, length, default):
    """Return a run of `length` slots filled from `entries`."""
    slots = [copy.deepcopy(default) for _ in range(length)]
    for index, value in entries:
        slots[index] = value
    return slots''',
    visible_test=_test_module(
        "sparse_expand",
        "Published contract for filling a run of slots.",
        """
def test_named_positions_hold_their_values() -> None:
    assert expand([(0, "a"), (2, "c")], 3, "-") == ["a", "-", "c"]


def test_no_positions_at_all_is_all_default() -> None:
    assert expand([], 2, 0) == [0, 0]
""",
        imports="from sparse_expand import expand\n",
    ),
    hidden_test=_test_module(
        "sparse_expand",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_named_positions_hold_their_values() -> None:
    assert expand([(0, "a"), (2, "c")], 3, "-") == ["a", "-", "c"]


def test_a_position_outside_the_run_is_refused() -> None:
    with pytest.raises(ValueError):
        expand([(3, "x")], 3, "-")
    with pytest.raises(ValueError):
        expand([(-1, "x")], 3, "-")


def test_each_slot_holds_its_own_copy_of_the_default() -> None:
    slots = expand([], 3, [])
    slots[0].append("x")
    assert slots == [["x"], [], []]
""",
        imports="from sparse_expand import expand\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G045 = D2TaskSpec(
    template_id="d5_numeric.simplify_ratio",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-simplify-ratio",
    module="simplify_ratio",
    module_doc="Reducing a ratio to the smallest whole numbers that say the same thing.",
    issue=(
        "simplify() is documented to reduce a ratio to lowest terms. Callers report that a "
        "ratio written with a negative below the line comes back with the minus sign still "
        "below the line, and that a denominator of zero comes back as a ratio rather than "
        "being refused."
    ),
    expected=(
        "simplify(numerator, denominator) returns the ratio in lowest terms as a pair, with "
        "the sign carried by the numerator and the denominator always positive, and raises "
        "ValueError for a denominator of zero."
    ),
    baseline_reason=(
        "it divides both sides by their common divisor and hands them back as they came, so a "
        "negative denominator keeps its sign, and it never checks the denominator is not zero"
    ),
    edge_cases=(
        "the sign is carried by the numerator, never by the denominator",
        "a denominator of zero is refused",
    ),
    imports="import math\n",
    baseline='''def simplify(numerator, denominator):
    """Return the ratio in lowest terms with the sign on the numerator."""
    divisor = math.gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor''',
    variant_one='''def simplify(numerator, denominator):
    """Return the ratio in lowest terms with the sign on the numerator."""
    if denominator == 0:
        raise ValueError("a ratio cannot have a denominator of zero")
    divisor = math.gcd(numerator, denominator)
    sign = -1 if denominator < 0 else 1
    return (sign * numerator) // divisor, (sign * denominator) // divisor''',
    variant_two='''def simplify(numerator, denominator):
    """Return the ratio in lowest terms with the sign on the numerator."""
    if denominator == 0:
        raise ValueError("a ratio cannot have a denominator of zero")
    top, bottom = numerator, denominator
    if bottom < 0:
        top, bottom = -top, -bottom
    divisor = math.gcd(abs(top), bottom)
    return top // divisor, bottom // divisor''',
    variant_three='''def simplify(numerator, denominator):
    """Return the ratio in lowest terms with the sign on the numerator."""
    top, bottom = numerator, denominator
    if bottom < 0:
        top, bottom = -top, -bottom
    divisor = math.gcd(abs(top), bottom)
    return top // divisor, bottom // divisor''',
    variant_four='''def simplify(numerator, denominator):
    """Return the ratio in lowest terms with the sign on the numerator."""
    if denominator == 0:
        raise ValueError("a ratio cannot have a denominator of zero")
    divisor = math.gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor''',
    visible_test=_test_module(
        "simplify_ratio",
        "Published contract for reducing a ratio.",
        """
def test_a_ratio_reduces_by_its_common_divisor() -> None:
    assert simplify(6, 8) == (3, 4)


def test_a_negative_above_the_line_stays_there() -> None:
    assert simplify(-6, 8) == (-3, 4)


def test_a_ratio_of_equals_is_one_to_one() -> None:
    assert simplify(5, 5) == (1, 1)
""",
        imports="from simplify_ratio import simplify\n",
    ),
    hidden_test=_test_module(
        "simplify_ratio",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_ratio_reduces_by_its_common_divisor() -> None:
    assert simplify(6, 8) == (3, 4)


def test_the_sign_moves_above_the_line() -> None:
    assert simplify(1, -2) == (-1, 2)
    assert simplify(-4, -6) == (2, 3)


def test_a_denominator_of_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        simplify(4, 0)
""",
        imports="from simplify_ratio import simplify\n",
    ),
)


_G046 = D2TaskSpec(
    template_id="d5_numeric.month_length",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-month-length",
    module="month_length",
    module_doc="Saying how many days a given month of a given year runs to.",
    issue=(
        "days_in() is documented to say how long a month runs. Schedulers report that February "
        "1900 comes back as twenty-nine days, and that a month number nobody has heard of "
        "comes back with an answer instead of being refused."
    ),
    expected=(
        "days_in(year, month) returns the number of days in that month. February has "
        "twenty-nine days in a leap year, where a year divisible by one hundred is a leap year "
        "only when it is also divisible by four hundred, and a month outside one to twelve is "
        "refused with ValueError."
    ),
    baseline_reason=(
        "it takes every fourth year as a leap year without the hundred-and-four-hundred rule, "
        "and it indexes the table of lengths without checking the month is on it"
    ),
    edge_cases=(
        "a century year is a leap year only when it divides by four hundred",
        "a month outside one to twelve is refused",
    ),
    baseline='''def days_in(year, month):
    """Return the number of days in `month` of `year`."""
    lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if month == 2 and year % 4 == 0:
        return 29
    return lengths[month - 1]''',
    variant_one='''def days_in(year, month):
    """Return the number of days in `month` of `year`."""
    lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= month <= 12:
        raise ValueError(f"there is no month {month}")
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    if month == 2 and leap:
        return 29
    return lengths[month - 1]''',
    variant_two='''def days_in(year, month):
    """Return the number of days in `month` of `year`."""
    if not 1 <= month <= 12:
        raise ValueError(f"there is no month {month}")
    short = {4, 6, 9, 11}
    if month != 2:
        return 30 if month in short else 31
    if year % 400 == 0:
        return 29
    if year % 100 == 0:
        return 28
    return 29 if year % 4 == 0 else 28''',
    variant_three='''def days_in(year, month):
    """Return the number of days in `month` of `year`."""
    lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    if month == 2 and leap:
        return 29
    return lengths[month - 1]''',
    variant_four='''def days_in(year, month):
    """Return the number of days in `month` of `year`."""
    lengths = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= month <= 12:
        raise ValueError(f"there is no month {month}")
    if month == 2 and year % 4 == 0:
        return 29
    return lengths[month - 1]''',
    visible_test=_test_module(
        "month_length",
        "Published contract for the length of a month.",
        """
def test_february_in_an_ordinary_leap_year() -> None:
    assert days_in(2024, 2) == 29


def test_february_in_a_year_that_is_not_a_leap_year() -> None:
    assert days_in(2023, 2) == 28


def test_a_month_of_thirty_days() -> None:
    assert days_in(2023, 4) == 30
""",
        imports="from month_length import days_in\n",
    ),
    hidden_test=_test_module(
        "month_length",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_february_in_an_ordinary_leap_year() -> None:
    assert days_in(2024, 2) == 29


def test_a_century_year_needs_four_hundred_to_be_a_leap_year() -> None:
    assert days_in(1900, 2) == 28
    assert days_in(2000, 2) == 29


def test_a_month_nobody_has_heard_of_is_refused() -> None:
    with pytest.raises(ValueError):
        days_in(2023, 13)
    with pytest.raises(ValueError):
        days_in(2023, 0)
""",
        imports="from month_length import days_in\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G047 = D2TaskSpec(
    template_id="d5_parsing.morse_decode",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-morse-decode",
    module="morse_decode",
    module_doc="Reading a keyed signal back into the letters it was sent as.",
    issue=(
        "decode() is documented to read a keyed signal back into letters, with a wider gap "
        "between words. Operators report that a signal carrying two words comes back as one "
        "run of nonsense, and that a symbol the table does not know fails with a KeyError "
        "rather than saying what was wrong."
    ),
    expected=(
        "decode(signal) returns the letters of the signal. Symbols are separated by one space "
        "and words by three, so a word gap becomes a single space in the answer, and a symbol "
        "the table does not know is refused with ValueError."
    ),
    baseline_reason=(
        "it splits on every single space, which turns a word gap into empty symbols, and it "
        "looks each symbol up straight in the table"
    ),
    edge_cases=(
        "three spaces are a word gap and become one space in the answer",
        "a symbol the table does not know is refused",
    ),
    baseline='''def decode(signal):
    """Return the letters `signal` was keyed as."""
    table = {
        ".-": "a", "-...": "b", "-.-.": "c", "-..": "d",
        ".": "e", "..-.": "f", "--.": "g", "....": "h",
    }
    return "".join(table[symbol] for symbol in signal.split(" "))''',
    variant_one='''def decode(signal):
    """Return the letters `signal` was keyed as."""
    table = {
        ".-": "a", "-...": "b", "-.-.": "c", "-..": "d",
        ".": "e", "..-.": "f", "--.": "g", "....": "h",
    }
    words = []
    for word in signal.split("   "):
        letters = []
        for symbol in word.split(" "):
            if symbol not in table:
                raise ValueError(f"{symbol!r} is not a symbol this table knows")
            letters.append(table[symbol])
        words.append("".join(letters))
    return " ".join(words)''',
    variant_two='''def decode(signal):
    """Return the letters `signal` was keyed as."""
    table = {
        ".-": "a", "-...": "b", "-.-.": "c", "-..": "d",
        ".": "e", "..-.": "f", "--.": "g", "....": "h",
    }
    out = []
    for word in signal.split("   "):
        for symbol in word.split(" "):
            try:
                out.append(table[symbol])
            except KeyError:
                raise ValueError(f"{symbol!r} is not a symbol this table knows") from None
        out.append(" ")
    return "".join(out[:-1])''',
    variant_three='''def decode(signal):
    """Return the letters `signal` was keyed as."""
    table = {
        ".-": "a", "-...": "b", "-.-.": "c", "-..": "d",
        ".": "e", "..-.": "f", "--.": "g", "....": "h",
    }
    return " ".join(
        "".join(table[symbol] for symbol in word.split(" "))
        for word in signal.split("   ")
    )''',
    variant_four='''def decode(signal):
    """Return the letters `signal` was keyed as."""
    table = {
        ".-": "a", "-...": "b", "-.-.": "c", "-..": "d",
        ".": "e", "..-.": "f", "--.": "g", "....": "h",
    }
    letters = []
    for symbol in signal.split(" "):
        if symbol not in table:
            raise ValueError(f"{symbol!r} is not a symbol this table knows")
        letters.append(table[symbol])
    return "".join(letters)''',
    visible_test=_test_module(
        "morse_decode",
        "Published contract for reading a keyed signal.",
        """
def test_a_run_of_symbols_reads_as_a_word() -> None:
    assert decode(".... .") == "he"


def test_a_single_symbol_reads_as_its_letter() -> None:
    assert decode(".-") == "a"
""",
        imports="from morse_decode import decode\n",
    ),
    hidden_test=_test_module(
        "morse_decode",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_run_of_symbols_reads_as_a_word() -> None:
    assert decode(".... .") == "he"


def test_three_spaces_are_a_word_gap() -> None:
    assert decode(".-   -...") == "a b"


def test_a_symbol_the_table_does_not_know_is_refused() -> None:
    with pytest.raises(ValueError):
        decode(".-.-.-.-.-")
""",
        imports="from morse_decode import decode\n",
    ),
)


_G048 = D2TaskSpec(
    template_id="d5_parsing.locale_tag",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-locale-tag",
    module="locale_tag",
    module_doc="Putting a language tag into the casing the registry writes it in.",
    issue=(
        "normalise() is documented to put a language tag into its registry casing. Callers "
        "report that a tag naming a script comes back shouting the script in capitals, and "
        "that a tag with a subtag missing between two hyphens comes back reshaped rather than "
        "being refused."
    ),
    expected=(
        "normalise(tag) returns the tag with its subtags in registry casing: the language "
        "lowercase, a four-letter script in title case, and any other following subtag "
        "uppercase, joined by hyphens. A tag with an empty subtag is refused with ValueError."
    ),
    baseline_reason=(
        "it uppercases every subtag after the language, which shouts a script that should be "
        "in title case, and it never notices a subtag with nothing in it"
    ),
    edge_cases=(
        "a four-letter script subtag takes title case, not capitals",
        "a tag with an empty subtag is refused",
    ),
    baseline='''def normalise(tag):
    """Return `tag` in registry casing."""
    parts = tag.split("-")
    shaped = [parts[0].lower()]
    for part in parts[1:]:
        shaped.append(part.upper())
    return "-".join(shaped)''',
    variant_one='''def normalise(tag):
    """Return `tag` in registry casing."""
    parts = tag.split("-")
    if any(not part for part in parts):
        raise ValueError(f"{tag!r} has an empty subtag")
    shaped = [parts[0].lower()]
    for part in parts[1:]:
        shaped.append(part.title() if len(part) == 4 else part.upper())
    return "-".join(shaped)''',
    variant_two='''def normalise(tag):
    """Return `tag` in registry casing."""
    parts = tag.split("-")
    if "" in parts:
        raise ValueError(f"{tag!r} has an empty subtag")

    def shape(place, part):
        if place == 0:
            return part.lower()
        if len(part) == 4:
            return part[:1].upper() + part[1:].lower()
        return part.upper()

    return "-".join(shape(place, part) for place, part in enumerate(parts))''',
    variant_three='''def normalise(tag):
    """Return `tag` in registry casing."""
    parts = tag.split("-")
    shaped = [parts[0].lower()]
    for part in parts[1:]:
        shaped.append(part.title() if len(part) == 4 else part.upper())
    return "-".join(shaped)''',
    variant_four='''def normalise(tag):
    """Return `tag` in registry casing."""
    parts = tag.split("-")
    if any(not part for part in parts):
        raise ValueError(f"{tag!r} has an empty subtag")
    shaped = [parts[0].lower()]
    for part in parts[1:]:
        shaped.append(part.upper())
    return "-".join(shaped)''',
    visible_test=_test_module(
        "locale_tag",
        "Published contract for the casing of a language tag.",
        """
def test_a_language_and_region_take_their_casing() -> None:
    assert normalise("en-gb") == "en-GB"


def test_a_language_on_its_own_goes_lowercase() -> None:
    assert normalise("FR") == "fr"
""",
        imports="from locale_tag import normalise\n",
    ),
    hidden_test=_test_module(
        "locale_tag",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_language_and_region_take_their_casing() -> None:
    assert normalise("en-gb") == "en-GB"


def test_a_script_subtag_takes_title_case() -> None:
    assert normalise("zh-hans-cn") == "zh-Hans-CN"


def test_an_empty_subtag_is_refused() -> None:
    with pytest.raises(ValueError):
        normalise("en--gb")
""",
        imports="from locale_tag import normalise\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G049 = D2TaskSpec(
    template_id="d5_transform.prune_empty",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-prune-empty",
    module="prune_empty",
    module_doc="Clearing the entries that hold nothing out of a settings tree.",
    issue=(
        "prune() is documented to clear out the entries that hold nothing. Callers report that "
        "a reading of zero is cleared out along with them even though zero is a reading, and "
        "that a branch whose own entries were all cleared is left behind as an empty branch."
    ),
    expected=(
        "prune(nested) returns the mapping with every entry dropped whose value is None, an "
        "empty mapping or an empty list, applied to nested branches as well so a branch left "
        "with nothing is dropped in its turn. A value that merely reads as false -- zero, "
        "False, an empty string -- is kept."
    ),
    baseline_reason=(
        "it keeps an entry only when its value reads as true, which throws away zero and False "
        "along with the empties and never looks inside a branch at all"
    ),
    edge_cases=(
        "a branch left with nothing after its own pruning is dropped",
        "a value that merely reads as false is kept",
    ),
    baseline='''def prune(nested):
    """Return `nested` with the entries that hold nothing cleared out."""
    out = {}
    for key, value in nested.items():
        if value:
            out[key] = value
    return out''',
    variant_one='''def prune(nested):
    """Return `nested` with the entries that hold nothing cleared out."""
    out = {}
    for key, value in nested.items():
        if isinstance(value, dict):
            value = prune(value)
        if value is None or value == {} or value == []:
            continue
        out[key] = value
    return out''',
    variant_two='''def prune(nested):
    """Return `nested` with the entries that hold nothing cleared out."""

    def holds_nothing(value):
        return value is None or (isinstance(value, (dict, list)) and len(value) == 0)

    cleaned = {}
    for key, value in nested.items():
        shrunk = prune(value) if isinstance(value, dict) else value
        if not holds_nothing(shrunk):
            cleaned[key] = shrunk
    return cleaned''',
    variant_three='''def prune(nested):
    """Return `nested` with the entries that hold nothing cleared out."""
    out = {}
    for key, value in nested.items():
        if isinstance(value, dict):
            value = prune(value)
        if value:
            out[key] = value
    return out''',
    variant_four='''def prune(nested):
    """Return `nested` with the entries that hold nothing cleared out."""
    out = {}
    for key, value in nested.items():
        if value is None or value == {} or value == []:
            continue
        out[key] = value
    return out''',
    visible_test=_test_module(
        "prune_empty",
        "Published contract for clearing empty entries out of a settings tree.",
        """
def test_an_entry_holding_nothing_is_cleared() -> None:
    assert prune({"a": 1, "b": None}) == {"a": 1}


def test_an_empty_list_is_cleared_too() -> None:
    assert prune({"a": 1, "b": []}) == {"a": 1}


def test_a_mapping_with_nothing_in_it_prunes_to_nothing() -> None:
    assert prune({}) == {}
""",
        imports="from prune_empty import prune\n",
    ),
    hidden_test=_test_module(
        "prune_empty",
        "The part of the contract the published tests do not state.",
        """
def test_an_entry_holding_nothing_is_cleared() -> None:
    assert prune({"a": 1, "b": None}) == {"a": 1}


def test_a_branch_left_with_nothing_is_dropped_in_its_turn() -> None:
    assert prune({"a": {"b": None}, "c": 1}) == {"c": 1}


def test_a_value_that_merely_reads_as_false_is_kept() -> None:
    assert prune({"a": 0, "b": False, "c": ""}) == {"a": 0, "b": False, "c": ""}
""",
        imports="from prune_empty import prune\n",
    ),
)


_G050 = D2TaskSpec(
    template_id="d5_transform.top_per_group",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-top-per-group",
    module="top_per_group",
    module_doc="Keeping the best few of every group and throwing the rest away.",
    issue=(
        "top_per_group() is documented to keep the best few records of every group. Callers "
        "report that the groups come back in alphabetical order rather than the order the "
        "records introduced them, and that a record with no score at all brings the whole run "
        "down with a KeyError."
    ),
    expected=(
        "top_per_group(records, group_key, score_key, count) returns a mapping from group to "
        "its highest-scoring records, at most `count` of them and highest first, the groups "
        "in the order the records first introduced them, and a record carrying no score left "
        "out rather than raising."
    ),
    baseline_reason=(
        "it walks the groups in sorted order rather than the order it met them, and it reads "
        "each score without checking the record carries one"
    ),
    edge_cases=(
        "the groups come back in the order the records first introduced them",
        "a record carrying no score is left out",
    ),
    baseline='''def top_per_group(records, group_key, score_key, count):
    """Return the best `count` records of each group, best first."""
    grouped = {}
    for record in records:
        grouped.setdefault(record[group_key], []).append(record)
    out = {}
    for group in sorted(grouped):
        ranked = sorted(grouped[group], key=lambda record: record[score_key], reverse=True)
        out[group] = ranked[:count]
    return out''',
    variant_one='''def top_per_group(records, group_key, score_key, count):
    """Return the best `count` records of each group, best first."""
    grouped = {}
    for record in records:
        if score_key not in record:
            continue
        grouped.setdefault(record[group_key], []).append(record)
    return {
        group: sorted(entries, key=lambda record: record[score_key], reverse=True)[:count]
        for group, entries in grouped.items()
    }''',
    variant_two='''def top_per_group(records, group_key, score_key, count):
    """Return the best `count` records of each group, best first."""
    scored = [record for record in records if score_key in record]
    order = []
    for record in scored:
        if record[group_key] not in order:
            order.append(record[group_key])
    out = {}
    for group in order:
        entries = [record for record in scored if record[group_key] == group]
        entries.sort(key=lambda record: record[score_key], reverse=True)
        out[group] = entries[:count]
    return out''',
    variant_three='''def top_per_group(records, group_key, score_key, count):
    """Return the best `count` records of each group, best first."""
    grouped = {}
    for record in records:
        grouped.setdefault(record[group_key], []).append(record)
    return {
        group: sorted(entries, key=lambda record: record[score_key], reverse=True)[:count]
        for group, entries in grouped.items()
    }''',
    variant_four='''def top_per_group(records, group_key, score_key, count):
    """Return the best `count` records of each group, best first."""
    grouped = {}
    for record in records:
        if score_key not in record:
            continue
        grouped.setdefault(record[group_key], []).append(record)
    out = {}
    for group in sorted(grouped):
        ranked = sorted(grouped[group], key=lambda record: record[score_key], reverse=True)
        out[group] = ranked[:count]
    return out''',
    visible_test=_test_module(
        "top_per_group",
        "Published contract for keeping the best few of every group.",
        """
def test_each_group_keeps_its_best() -> None:
    records = [
        {"team": "a", "score": 1},
        {"team": "a", "score": 5},
        {"team": "b", "score": 3},
    ]
    assert top_per_group(records, "team", "score", 1) == {
        "a": [{"team": "a", "score": 5}],
        "b": [{"team": "b", "score": 3}],
    }


def test_a_group_with_fewer_than_the_count_keeps_them_all() -> None:
    records = [{"team": "a", "score": 1}]
    assert top_per_group(records, "team", "score", 3) == {"a": [{"team": "a", "score": 1}]}
""",
        imports="from top_per_group import top_per_group\n",
    ),
    hidden_test=_test_module(
        "top_per_group",
        "The part of the contract the published tests do not state.",
        """
def test_each_group_keeps_its_best() -> None:
    records = [
        {"team": "a", "score": 1},
        {"team": "a", "score": 5},
        {"team": "b", "score": 3},
    ]
    assert top_per_group(records, "team", "score", 1) == {
        "a": [{"team": "a", "score": 5}],
        "b": [{"team": "b", "score": 3}],
    }


def test_the_groups_keep_the_order_the_records_introduced_them() -> None:
    records = [{"team": "b", "score": 1}, {"team": "a", "score": 2}]
    assert list(top_per_group(records, "team", "score", 1)) == ["b", "a"]


def test_a_record_carrying_no_score_is_left_out() -> None:
    records = [{"team": "a", "score": 1}, {"team": "a"}]
    assert top_per_group(records, "team", "score", 3) == {"a": [{"team": "a", "score": 1}]}
""",
        imports="from top_per_group import top_per_group\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G051 = D2TaskSpec(
    template_id="d5_state.idempotent_transfer",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-idempotent-transfer",
    module="idempotent_transfer",
    module_doc="Moving money between accounts so that a repeated instruction moves it once.",
    issue=(
        "apply_transfer() is documented to move money once per instruction. Reconciliation "
        "reports that an instruction resent after a timeout moves the money a second time, and "
        "that an instruction larger than the source account holds leaves that account below "
        "zero instead of being refused."
    ),
    expected=(
        "apply_transfer(ledger, transfer) returns a new ledger with the amount moved from one "
        "account to the other and the instruction's id recorded as applied. An instruction "
        "whose id is already recorded changes nothing, an instruction the source cannot cover "
        "is refused with ValueError, and the caller's ledger is left as it was."
    ),
    baseline_reason=(
        "it moves the money for every instruction it is handed without looking at what has "
        "already been applied, and it debits the source without checking the balance covers it"
    ),
    edge_cases=(
        "an instruction whose id is already recorded changes nothing",
        "an instruction the source cannot cover is refused",
    ),
    baseline='''def apply_transfer(ledger, transfer):
    """Return `ledger` with `transfer` applied once."""
    balances = dict(ledger["balances"])
    balances[transfer["from"]] -= transfer["amount"]
    balances[transfer["to"]] = balances.get(transfer["to"], 0) + transfer["amount"]
    return {"balances": balances, "applied": [*ledger["applied"], transfer["id"]]}''',
    variant_one='''def apply_transfer(ledger, transfer):
    """Return `ledger` with `transfer` applied once."""
    if transfer["id"] in ledger["applied"]:
        return {"balances": dict(ledger["balances"]), "applied": list(ledger["applied"])}
    balances = dict(ledger["balances"])
    if balances.get(transfer["from"], 0) < transfer["amount"]:
        raise ValueError(f"{transfer['from']!r} cannot cover {transfer['amount']}")
    balances[transfer["from"]] -= transfer["amount"]
    balances[transfer["to"]] = balances.get(transfer["to"], 0) + transfer["amount"]
    return {"balances": balances, "applied": [*ledger["applied"], transfer["id"]]}''',
    variant_two='''def apply_transfer(ledger, transfer):
    """Return `ledger` with `transfer` applied once."""
    settled = {
        "balances": dict(ledger["balances"]),
        "applied": list(ledger["applied"]),
    }
    if transfer["id"] in settled["applied"]:
        return settled
    source = settled["balances"].get(transfer["from"], 0)
    if source < transfer["amount"]:
        raise ValueError(f"{transfer['from']!r} cannot cover {transfer['amount']}")
    settled["balances"][transfer["from"]] = source - transfer["amount"]
    target = settled["balances"].get(transfer["to"], 0)
    settled["balances"][transfer["to"]] = target + transfer["amount"]
    settled["applied"].append(transfer["id"])
    return settled''',
    variant_three='''def apply_transfer(ledger, transfer):
    """Return `ledger` with `transfer` applied once."""
    if transfer["id"] in ledger["applied"]:
        return {"balances": dict(ledger["balances"]), "applied": list(ledger["applied"])}
    balances = dict(ledger["balances"])
    balances[transfer["from"]] -= transfer["amount"]
    balances[transfer["to"]] = balances.get(transfer["to"], 0) + transfer["amount"]
    return {"balances": balances, "applied": [*ledger["applied"], transfer["id"]]}''',
    variant_four='''def apply_transfer(ledger, transfer):
    """Return `ledger` with `transfer` applied once."""
    balances = dict(ledger["balances"])
    if balances.get(transfer["from"], 0) < transfer["amount"]:
        raise ValueError(f"{transfer['from']!r} cannot cover {transfer['amount']}")
    balances[transfer["from"]] -= transfer["amount"]
    balances[transfer["to"]] = balances.get(transfer["to"], 0) + transfer["amount"]
    return {"balances": balances, "applied": [*ledger["applied"], transfer["id"]]}''',
    visible_test=_test_module(
        "idempotent_transfer",
        "Published contract for moving money between accounts.",
        """
def test_the_money_moves_and_the_instruction_is_recorded() -> None:
    ledger = {"balances": {"a": 10, "b": 0}, "applied": []}
    transfer = {"id": "t1", "from": "a", "to": "b", "amount": 4}
    assert apply_transfer(ledger, transfer) == {
        "balances": {"a": 6, "b": 4},
        "applied": ["t1"],
    }


def test_the_callers_ledger_is_left_alone() -> None:
    ledger = {"balances": {"a": 10, "b": 0}, "applied": []}
    apply_transfer(ledger, {"id": "t1", "from": "a", "to": "b", "amount": 4})
    assert ledger == {"balances": {"a": 10, "b": 0}, "applied": []}
""",
        imports="from idempotent_transfer import apply_transfer\n",
    ),
    hidden_test=_test_module(
        "idempotent_transfer",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_money_moves_and_the_instruction_is_recorded() -> None:
    ledger = {"balances": {"a": 10, "b": 0}, "applied": []}
    transfer = {"id": "t1", "from": "a", "to": "b", "amount": 4}
    assert apply_transfer(ledger, transfer) == {
        "balances": {"a": 6, "b": 4},
        "applied": ["t1"],
    }


def test_an_instruction_already_applied_changes_nothing() -> None:
    ledger = {"balances": {"a": 6, "b": 4}, "applied": ["t1"]}
    transfer = {"id": "t1", "from": "a", "to": "b", "amount": 4}
    assert apply_transfer(ledger, transfer) == {
        "balances": {"a": 6, "b": 4},
        "applied": ["t1"],
    }


def test_an_instruction_the_source_cannot_cover_is_refused() -> None:
    ledger = {"balances": {"a": 3, "b": 0}, "applied": []}
    with pytest.raises(ValueError):
        apply_transfer(ledger, {"id": "t2", "from": "a", "to": "b", "amount": 4})
""",
        imports="from idempotent_transfer import apply_transfer\n",
    ),
)


_G052 = D2TaskSpec(
    template_id="d5_state.reentrancy_guard",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-reentrancy-guard",
    module="reentrancy_guard",
    module_doc="Letting a named piece of work run, but never twice at the same time.",
    issue=(
        "run_guarded() is documented to run a named piece of work and refuse a second run of "
        "the same name while the first is still going. Operators report that a name is never "
        "refused at all, and that a run which fails leaves its name marked as running for "
        "ever after."
    ),
    expected=(
        "run_guarded(active, key, body) marks the key as running, runs the body and returns "
        "what it returned, and takes the mark off again whatever happened, including when the "
        "body raised. A key already marked as running is refused with RuntimeError and its "
        "body is not run."
    ),
    baseline_reason=(
        "it marks the key and clears it on the line after the body, which never runs when the "
        "body raises, and it never looks at whether the key is already marked"
    ),
    edge_cases=(
        "a key already marked as running is refused and its body is not run",
        "the mark comes off even when the body raises",
    ),
    baseline='''def run_guarded(active, key, body):
    """Run `body` with `key` marked as running."""
    active.add(key)
    result = body()
    active.discard(key)
    return result''',
    variant_one='''def run_guarded(active, key, body):
    """Run `body` with `key` marked as running."""
    if key in active:
        raise RuntimeError(f"{key!r} is already running")
    active.add(key)
    try:
        return body()
    finally:
        active.discard(key)''',
    variant_two='''def run_guarded(active, key, body):
    """Run `body` with `key` marked as running."""
    if key in active:
        raise RuntimeError(f"{key!r} is already running")
    active.add(key)
    outcome = None
    failure = None
    try:
        outcome = body()
    except Exception as error:
        failure = error
    active.discard(key)
    if failure is not None:
        raise failure
    return outcome''',
    variant_three='''def run_guarded(active, key, body):
    """Run `body` with `key` marked as running."""
    if key in active:
        raise RuntimeError(f"{key!r} is already running")
    active.add(key)
    result = body()
    active.discard(key)
    return result''',
    variant_four='''def run_guarded(active, key, body):
    """Run `body` with `key` marked as running."""
    active.add(key)
    try:
        return body()
    finally:
        active.discard(key)''',
    visible_test=_test_module(
        "reentrancy_guard",
        "Published contract for running a named piece of work.",
        """
def test_the_body_runs_and_the_mark_comes_off() -> None:
    active = set()
    assert run_guarded(active, "a", lambda: 7) == 7
    assert active == set()


def test_two_different_names_may_run_one_after_the_other() -> None:
    active = set()
    run_guarded(active, "a", lambda: 1)
    assert run_guarded(active, "b", lambda: 2) == 2
    assert active == set()
""",
        imports="from reentrancy_guard import run_guarded\n",
    ),
    hidden_test=_test_module(
        "reentrancy_guard",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _explode():
    raise ValueError("the body refused")


def test_the_body_runs_and_the_mark_comes_off() -> None:
    active = set()
    assert run_guarded(active, "a", lambda: 7) == 7
    assert active == set()


def test_a_name_already_running_is_refused_and_its_body_is_not_run() -> None:
    active = {"a"}
    ran = []
    with pytest.raises(RuntimeError):
        run_guarded(active, "a", lambda: ran.append("went"))
    assert ran == []


def test_the_mark_comes_off_even_when_the_body_raises() -> None:
    active = set()
    with pytest.raises(ValueError):
        run_guarded(active, "a", _explode)
    assert active == set()
""",
        imports="from reentrancy_guard import run_guarded\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G053 = D2TaskSpec(
    template_id="d5_error.partial_flush",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-partial-flush",
    module="partial_flush",
    module_doc="Writing a backlog out in batches and saying honestly how far it got.",
    issue=(
        "flush() is documented to write a backlog out in batches and report how much of it "
        "landed. Operators report that the count includes the batch that failed, so the "
        "figure is larger than what was written, and that the batches after a failure are "
        "attempted anyway."
    ),
    expected=(
        "flush(items, write, size) writes the items out in batches of `size` and returns "
        "(written, failure). Written counts only the items a write actually accepted, failure "
        "is the text of the first write that raised or None, and no batch is attempted after "
        "one has failed."
    ),
    baseline_reason=(
        "it adds the batch to the count before handing it to the write, and it records the "
        "failure without leaving the loop"
    ),
    edge_cases=(
        "the count leaves out the batch that failed",
        "no batch is attempted after one has failed",
    ),
    baseline='''def flush(items, write, size):
    """Write `items` out in batches, returning (written, failure)."""
    entries = list(items)
    written = 0
    failure = None
    for start in range(0, len(entries), size):
        batch = entries[start : start + size]
        written += len(batch)
        try:
            write(batch)
        except Exception as error:
            failure = str(error)
    return written, failure''',
    variant_one='''def flush(items, write, size):
    """Write `items` out in batches, returning (written, failure)."""
    entries = list(items)
    written = 0
    for start in range(0, len(entries), size):
        batch = entries[start : start + size]
        try:
            write(batch)
        except Exception as error:
            return written, str(error)
        written += len(batch)
    return written, None''',
    variant_two='''def flush(items, write, size):
    """Write `items` out in batches, returning (written, failure)."""
    entries = list(items)
    batches = [entries[start : start + size] for start in range(0, len(entries), size)]
    written = 0
    failure = None
    for batch in batches:
        if failure is not None:
            break
        try:
            write(batch)
            written += len(batch)
        except Exception as error:
            failure = str(error)
    return written, failure''',
    variant_three='''def flush(items, write, size):
    """Write `items` out in batches, returning (written, failure)."""
    entries = list(items)
    written = 0
    failure = None
    for start in range(0, len(entries), size):
        batch = entries[start : start + size]
        try:
            write(batch)
            written += len(batch)
        except Exception as error:
            failure = str(error)
    return written, failure''',
    variant_four='''def flush(items, write, size):
    """Write `items` out in batches, returning (written, failure)."""
    entries = list(items)
    written = 0
    for start in range(0, len(entries), size):
        batch = entries[start : start + size]
        written += len(batch)
        try:
            write(batch)
        except Exception as error:
            return written, str(error)
    return written, None''',
    visible_test=_test_module(
        "partial_flush",
        "Published contract for writing a backlog out in batches.",
        """
def test_a_backlog_that_all_lands_is_counted_in_full() -> None:
    seen = []
    assert flush([1, 2, 3], seen.append, 2) == (3, None)
    assert seen == [[1, 2], [3]]


def test_an_empty_backlog_writes_nothing() -> None:
    seen = []
    assert flush([], seen.append, 2) == (0, None)
    assert seen == []
""",
        imports="from partial_flush import flush\n",
    ),
    hidden_test=_test_module(
        "partial_flush",
        "The part of the contract the published tests do not state.",
        """
def test_a_backlog_that_all_lands_is_counted_in_full() -> None:
    seen = []
    assert flush([1, 2, 3], seen.append, 2) == (3, None)
    assert seen == [[1, 2], [3]]


def test_the_count_leaves_out_the_batch_that_failed() -> None:
    def write(batch):
        if 3 in batch:
            raise RuntimeError("the store refused")

    assert flush([1, 2, 3, 4], write, 2) == (2, "the store refused")


def test_no_batch_is_attempted_after_one_has_failed() -> None:
    seen = []

    def write(batch):
        seen.append(batch)
        raise RuntimeError("the store refused")

    flush([1, 2, 3], write, 1)
    assert seen == [[1]]
""",
        imports="from partial_flush import flush\n",
    ),
)


_G054 = D2TaskSpec(
    template_id="d5_error.admit_limit",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-admit-limit",
    module="admit_limit",
    module_doc="Letting a request through only while there is room left for it.",
    issue=(
        "admit() is documented to let a request through while there is room. Callers report "
        "that a request filling the allowance exactly is turned away as though it had "
        "overflowed, and that a request for a negative amount is let through and quietly "
        "gives room back."
    ),
    expected=(
        "admit(used, request, limit) returns the new usage when the request fits, where a "
        "request that fills the allowance exactly does fit, raises ValueError naming the "
        "overrun when it does not, and raises ValueError for a request below zero."
    ),
    baseline_reason=(
        "it turns away anything that reaches the limit rather than anything that passes it, "
        "and it never checks the request is not negative"
    ),
    edge_cases=(
        "a request that fills the allowance exactly is let through",
        "a request below zero is refused",
    ),
    baseline='''def admit(used, request, limit):
    """Return the new usage, or refuse the request."""
    if used + request >= limit:
        raise ValueError(f"over the allowance by {used + request - limit}")
    return used + request''',
    variant_one='''def admit(used, request, limit):
    """Return the new usage, or refuse the request."""
    if request < 0:
        raise ValueError(f"a request cannot be negative, got {request}")
    if used + request > limit:
        raise ValueError(f"over the allowance by {used + request - limit}")
    return used + request''',
    variant_two='''def admit(used, request, limit):
    """Return the new usage, or refuse the request."""
    if request < 0:
        raise ValueError(f"a request cannot be negative, got {request}")
    room = limit - used
    if request > room:
        raise ValueError(f"over the allowance by {request - room}")
    return used + request''',
    variant_three='''def admit(used, request, limit):
    """Return the new usage, or refuse the request."""
    if used + request > limit:
        raise ValueError(f"over the allowance by {used + request - limit}")
    return used + request''',
    variant_four='''def admit(used, request, limit):
    """Return the new usage, or refuse the request."""
    if request < 0:
        raise ValueError(f"a request cannot be negative, got {request}")
    if used + request >= limit:
        raise ValueError(f"over the allowance by {used + request - limit}")
    return used + request''',
    visible_test=_test_module(
        "admit_limit",
        "Published contract for letting a request through.",
        """
import pytest


def test_a_request_with_room_to_spare_is_let_through() -> None:
    assert admit(2, 3, 10) == 5


def test_the_first_request_is_let_through() -> None:
    assert admit(0, 1, 10) == 1


def test_a_request_past_the_allowance_is_refused() -> None:
    with pytest.raises(ValueError):
        admit(9, 5, 10)
""",
        imports="from admit_limit import admit\n",
    ),
    hidden_test=_test_module(
        "admit_limit",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_request_with_room_to_spare_is_let_through() -> None:
    assert admit(2, 3, 10) == 5


def test_a_request_filling_the_allowance_exactly_is_let_through() -> None:
    assert admit(7, 3, 10) == 10


def test_a_request_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        admit(5, -2, 10)
""",
        imports="from admit_limit import admit\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G055 = D2TaskSpec(
    template_id="d5_boundary.cartesian_rows",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-cartesian-rows",
    module="cartesian_rows",
    module_doc="Laying out every combination of a set of option lists, like an odometer.",
    issue=(
        "combine() is documented to lay out every combination of the option lists, the last "
        "list turning fastest. Callers report that the combinations come out with the first "
        "list turning fastest instead, and that no option lists at all raises rather than "
        "giving the one empty combination."
    ),
    expected=(
        "combine(groups) returns every combination of one option from each group as a tuple, "
        "ordered like an odometer so the last group turns fastest, and returns the single "
        "empty combination when there are no groups at all."
    ),
    baseline_reason=(
        "it loops over the new group outside the combinations built so far, which turns the "
        "earlier groups fastest, and it seeds itself from the first group without checking "
        "there is one"
    ),
    edge_cases=(
        "no groups at all gives the single empty combination",
        "the last group turns fastest",
    ),
    baseline='''def combine(groups):
    """Return every combination of one option from each of `groups`."""
    rows = [(option,) for option in groups[0]]
    for group in groups[1:]:
        rows = [(*row, option) for option in group for row in rows]
    return rows''',
    variant_one='''def combine(groups):
    """Return every combination of one option from each of `groups`."""
    rows = [()]
    for group in groups:
        rows = [(*row, option) for row in rows for option in group]
    return rows''',
    variant_two='''def combine(groups):
    """Return every combination of one option from each of `groups`."""
    lists = [list(group) for group in groups]
    total = 1
    for group in lists:
        total *= len(group)
    rows = []
    for number in range(total):
        row = []
        remaining = number
        for group in reversed(lists):
            row.append(group[remaining % len(group)])
            remaining //= len(group)
        rows.append(tuple(reversed(row)))
    return rows''',
    variant_three='''def combine(groups):
    """Return every combination of one option from each of `groups`."""
    rows = [()]
    for group in groups:
        rows = [(*row, option) for option in group for row in rows]
    return rows''',
    variant_four='''def combine(groups):
    """Return every combination of one option from each of `groups`."""
    rows = [(option,) for option in groups[0]]
    for group in groups[1:]:
        rows = [(*row, option) for row in rows for option in group]
    return rows''',
    visible_test=_test_module(
        "cartesian_rows",
        "Published contract for laying out combinations.",
        """
def test_one_group_gives_one_combination_per_option() -> None:
    assert combine([["a", "b"]]) == [("a",), ("b",)]


def test_two_single_option_groups_give_one_combination() -> None:
    assert combine([["a"], ["x"]]) == [("a", "x")]
""",
        imports="from cartesian_rows import combine\n",
    ),
    hidden_test=_test_module(
        "cartesian_rows",
        "The part of the contract the published tests do not state.",
        """
def test_one_group_gives_one_combination_per_option() -> None:
    assert combine([["a", "b"]]) == [("a",), ("b",)]


def test_no_groups_gives_the_single_empty_combination() -> None:
    assert combine([]) == [()]


def test_the_last_group_turns_fastest() -> None:
    assert combine([["a", "b"], ["x", "y"]]) == [
        ("a", "x"),
        ("a", "y"),
        ("b", "x"),
        ("b", "y"),
    ]
""",
        imports="from cartesian_rows import combine\n",
    ),
)


_G056 = D2TaskSpec(
    template_id="d5_boundary.cluster_by_gap",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-cluster-by-gap",
    module="cluster_by_gap",
    module_doc="Gathering readings that sit close together into groups.",
    issue=(
        "cluster() is documented to gather readings into groups, breaking wherever the step "
        "from one reading to the next is wider than the gap allowed. Callers report that two "
        "readings exactly the allowed gap apart are pushed into separate groups, and that a "
        "run with no readings at all raises."
    ),
    expected=(
        "cluster(readings, gap) returns the readings gathered into groups in order, a step "
        "exactly the size of `gap` keeping two readings together and anything wider starting "
        "a new group, and returns no groups at all for no readings."
    ),
    baseline_reason=(
        "it breaks on a step that merely reaches the gap rather than one that passes it, and "
        "it opens the first group from the first reading without checking there is one"
    ),
    edge_cases=(
        "a step exactly the size of the gap keeps two readings together",
        "no readings at all gives no groups",
    ),
    baseline='''def cluster(readings, gap):
    """Return `readings` gathered into groups no wider apart than `gap`."""
    groups = []
    current = [readings[0]]
    for previous, reading in zip(readings, readings[1:]):
        if reading - previous < gap:
            current.append(reading)
        else:
            groups.append(current)
            current = [reading]
    groups.append(current)
    return groups''',
    variant_one='''def cluster(readings, gap):
    """Return `readings` gathered into groups no wider apart than `gap`."""
    entries = list(readings)
    if not entries:
        return []
    groups = [[entries[0]]]
    for previous, reading in zip(entries, entries[1:]):
        if reading - previous <= gap:
            groups[-1].append(reading)
        else:
            groups.append([reading])
    return groups''',
    variant_two='''def cluster(readings, gap):
    """Return `readings` gathered into groups no wider apart than `gap`."""
    entries = list(readings)
    breaks = [
        place + 1
        for place, reading in enumerate(entries[1:])
        if reading - entries[place] > gap
    ]
    bounds = [0, *breaks, len(entries)]
    return [
        entries[start:stop]
        for start, stop in zip(bounds, bounds[1:])
        if stop > start
    ]''',
    variant_three='''def cluster(readings, gap):
    """Return `readings` gathered into groups no wider apart than `gap`."""
    groups = []
    current = [readings[0]]
    for previous, reading in zip(readings, readings[1:]):
        if reading - previous <= gap:
            current.append(reading)
        else:
            groups.append(current)
            current = [reading]
    groups.append(current)
    return groups''',
    variant_four='''def cluster(readings, gap):
    """Return `readings` gathered into groups no wider apart than `gap`."""
    entries = list(readings)
    if not entries:
        return []
    groups = []
    current = [entries[0]]
    for previous, reading in zip(entries, entries[1:]):
        if reading - previous < gap:
            current.append(reading)
        else:
            groups.append(current)
            current = [reading]
    groups.append(current)
    return groups''',
    visible_test=_test_module(
        "cluster_by_gap",
        "Published contract for gathering readings that sit close together.",
        """
def test_a_wide_step_starts_a_new_group() -> None:
    assert cluster([1, 2, 10, 11], 3) == [[1, 2], [10, 11]]


def test_a_single_reading_is_a_group_of_its_own() -> None:
    assert cluster([5], 3) == [[5]]
""",
        imports="from cluster_by_gap import cluster\n",
    ),
    hidden_test=_test_module(
        "cluster_by_gap",
        "The part of the contract the published tests do not state.",
        """
def test_a_wide_step_starts_a_new_group() -> None:
    assert cluster([1, 2, 10, 11], 3) == [[1, 2], [10, 11]]


def test_a_step_exactly_the_allowed_gap_keeps_them_together() -> None:
    assert cluster([1, 4, 9], 3) == [[1, 4], [9]]


def test_no_readings_at_all_gives_no_groups() -> None:
    assert cluster([], 3) == []
""",
        imports="from cluster_by_gap import cluster\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G057 = D2TaskSpec(
    template_id="d5_numeric.integer_root",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-integer-root",
    module="integer_root",
    module_doc="Finding the largest whole number whose given power does not pass a value.",
    issue=(
        "integer_root() is documented to return the largest whole number whose `degree` power "
        "does not pass the value. Callers report that an exact power such as the cube root of "
        "a thousand comes back one short, and that a negative value or a degree of zero fails "
        "with whatever the arithmetic happens to raise rather than being refused."
    ),
    expected=(
        "integer_root(value, degree) returns the largest whole number whose `degree` power is "
        "not greater than `value`, exactly even where the floating-point root falls just "
        "short, and raises ValueError for a negative value or a degree below one."
    ),
    baseline_reason=(
        "it truncates the floating-point root, which sits a hair below the answer for an exact "
        "power, and it neither checks the degree nor the sign of the value"
    ),
    edge_cases=(
        "an exact power returns its whole root rather than one less",
        "a negative value or a degree below one is refused",
    ),
    baseline='''def integer_root(value, degree):
    """Return the largest whole number whose `degree` power does not pass `value`."""
    return int(value ** (1 / degree))''',
    variant_one='''def integer_root(value, degree):
    """Return the largest whole number whose `degree` power does not pass `value`."""
    if degree < 1:
        raise ValueError(f"the degree must be at least one, got {degree}")
    if value < 0:
        raise ValueError(f"the value must not be negative, got {value}")
    guess = int(value ** (1 / degree)) + 2
    while guess**degree > value:
        guess -= 1
    return guess''',
    variant_two='''def integer_root(value, degree):
    """Return the largest whole number whose `degree` power does not pass `value`."""
    if degree < 1:
        raise ValueError(f"the degree must be at least one, got {degree}")
    if value < 0:
        raise ValueError(f"the value must not be negative, got {value}")
    low, high = 0, max(value, 1)
    while low < high:
        middle = (low + high + 1) // 2
        if middle**degree <= value:
            low = middle
        else:
            high = middle - 1
    return low''',
    variant_three='''def integer_root(value, degree):
    """Return the largest whole number whose `degree` power does not pass `value`."""
    guess = int(value ** (1 / degree)) + 2
    while guess**degree > value:
        guess -= 1
    return guess''',
    variant_four='''def integer_root(value, degree):
    """Return the largest whole number whose `degree` power does not pass `value`."""
    if degree < 1:
        raise ValueError(f"the degree must be at least one, got {degree}")
    if value < 0:
        raise ValueError(f"the value must not be negative, got {value}")
    return int(value ** (1 / degree))''',
    visible_test=_test_module(
        "integer_root",
        "Published contract for the whole root of a value.",
        """
def test_a_perfect_square_returns_its_root() -> None:
    assert integer_root(9, 2) == 3


def test_a_value_between_two_squares_rounds_down() -> None:
    assert integer_root(10, 2) == 3


def test_a_larger_perfect_square() -> None:
    assert integer_root(16, 2) == 4
""",
        imports="from integer_root import integer_root\n",
    ),
    hidden_test=_test_module(
        "integer_root",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_perfect_square_returns_its_root() -> None:
    assert integer_root(9, 2) == 3


def test_an_exact_cube_returns_its_whole_root() -> None:
    assert integer_root(1000, 3) == 10


def test_a_negative_value_or_a_degree_below_one_is_refused() -> None:
    with pytest.raises(ValueError):
        integer_root(-8, 3)
    with pytest.raises(ValueError):
        integer_root(8, 0)
""",
        imports="from integer_root import integer_root\n",
    ),
)


_G058 = D2TaskSpec(
    template_id="d5_numeric.geometric_mean",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-geometric-mean",
    module="geometric_mean",
    module_doc="Averaging growth factors the way that survives being multiplied together.",
    issue=(
        "geometric_mean() is documented to average a run of factors multiplicatively. "
        "Analysts report that a run containing a zero fails with a maths domain error instead "
        "of averaging to zero, and that an empty run fails with a division error rather than "
        "being refused."
    ),
    expected=(
        "geometric_mean(readings) returns the multiplicative average of the readings, which "
        "is zero when any reading is zero, and raises ValueError when there are no readings."
    ),
    baseline_reason=(
        "it averages the logarithms, which has nothing to take the logarithm of at zero, and "
        "it divides by the count without checking there is one"
    ),
    edge_cases=(
        "a run containing a zero averages to zero",
        "no readings at all is refused",
    ),
    imports="import math\n",
    baseline='''def geometric_mean(readings):
    """Return the multiplicative average of `readings`."""
    values = list(readings)
    return math.exp(sum(math.log(value) for value in values) / len(values))''',
    variant_one='''def geometric_mean(readings):
    """Return the multiplicative average of `readings`."""
    values = list(readings)
    if not values:
        raise ValueError("a geometric mean needs at least one reading")
    if any(value == 0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))''',
    variant_two='''def geometric_mean(readings):
    """Return the multiplicative average of `readings`."""
    values = list(readings)
    if not values:
        raise ValueError("a geometric mean needs at least one reading")
    product = 1.0
    for value in values:
        product *= value
    if product == 0:
        return 0.0
    return product ** (1 / len(values))''',
    variant_three='''def geometric_mean(readings):
    """Return the multiplicative average of `readings`."""
    values = list(readings)
    if any(value == 0 for value in values):
        return 0.0
    return math.exp(sum(math.log(value) for value in values) / len(values))''',
    variant_four='''def geometric_mean(readings):
    """Return the multiplicative average of `readings`."""
    values = list(readings)
    if not values:
        raise ValueError("a geometric mean needs at least one reading")
    return math.exp(sum(math.log(value) for value in values) / len(values))''',
    visible_test=_test_module(
        "geometric_mean",
        "Published contract for averaging a run of factors.",
        """
import pytest


def test_two_factors_average_to_their_root() -> None:
    assert geometric_mean([1, 4]) == pytest.approx(2.0)


def test_equal_factors_average_to_themselves() -> None:
    assert geometric_mean([2, 2, 2]) == pytest.approx(2.0)
""",
        imports="from geometric_mean import geometric_mean\n",
    ),
    hidden_test=_test_module(
        "geometric_mean",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_factors_average_to_their_root() -> None:
    assert geometric_mean([1, 4]) == pytest.approx(2.0)


def test_a_run_containing_a_zero_averages_to_zero() -> None:
    assert geometric_mean([0, 5]) == 0.0


def test_no_readings_at_all_is_refused() -> None:
    with pytest.raises(ValueError):
        geometric_mean([])
""",
        imports="from geometric_mean import geometric_mean\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G059 = D2TaskSpec(
    template_id="d5_parsing.name_initials",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-name-initials",
    module="name_initials",
    module_doc="Reducing a written name to the initials a form field wants.",
    issue=(
        "initials() is documented to reduce a written name to its initials. Registrars report "
        "that a hyphenated forename gives only one initial where the form wants both, and "
        "that a lowercase particle such as van or de is given an initial of its own."
    ),
    expected=(
        "initials(name) returns the initials of the name in capitals, each followed by a full "
        "stop. Each side of a hyphenated part gives its own initial, and a part beginning with "
        "a lowercase letter is a particle and is left out."
    ),
    baseline_reason=(
        "it takes the first letter of every whitespace-separated part, which reads a "
        "hyphenated part as one and gives a lowercase particle an initial"
    ),
    edge_cases=(
        "each side of a hyphenated part gives its own initial",
        "a part beginning with a lowercase letter is left out",
    ),
    baseline='''def initials(name):
    """Return the initials of `name`."""
    return "".join(f"{part[0].upper()}." for part in name.split())''',
    variant_one='''def initials(name):
    """Return the initials of `name`."""
    letters = []
    for part in name.split():
        if part[0].islower():
            continue
        for piece in part.split("-"):
            if piece:
                letters.append(f"{piece[0].upper()}.")
    return "".join(letters)''',
    variant_two='''def initials(name):
    """Return the initials of `name`."""
    parts = name.replace("-", " ").split()
    kept = [part for part in parts if part[:1].isupper()]
    return "".join(f"{part[0]}." for part in kept)''',
    variant_three='''def initials(name):
    """Return the initials of `name`."""
    parts = name.replace("-", " ").split()
    return "".join(f"{part[0].upper()}." for part in parts)''',
    variant_four='''def initials(name):
    """Return the initials of `name`."""
    letters = []
    for part in name.split():
        if part[0].islower():
            continue
        letters.append(f"{part[0].upper()}.")
    return "".join(letters)''',
    visible_test=_test_module(
        "name_initials",
        "Published contract for reducing a name to initials.",
        """
def test_a_two_part_name_gives_two_initials() -> None:
    assert initials("Ada Lovelace") == "A.L."


def test_a_middle_name_gives_its_own_initial() -> None:
    assert initials("Grace Brewster Hopper") == "G.B.H."
""",
        imports="from name_initials import initials\n",
    ),
    hidden_test=_test_module(
        "name_initials",
        "The part of the contract the published tests do not state.",
        """
def test_a_two_part_name_gives_two_initials() -> None:
    assert initials("Ada Lovelace") == "A.L."


def test_both_sides_of_a_hyphen_give_an_initial() -> None:
    assert initials("Jean-Luc Picard") == "J.L.P."


def test_a_lowercase_particle_is_left_out() -> None:
    assert initials("Ludwig van Beethoven") == "L.B."
""",
        imports="from name_initials import initials\n",
    ),
)


_G060 = D2TaskSpec(
    template_id="d5_parsing.entity_unescape",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-entity-unescape",
    module="entity_unescape",
    module_doc="Turning the escaped entities in a marked-up fragment back into characters.",
    issue=(
        "unescape() is documented to turn escaped entities back into characters. Callers "
        "report that a numeric entity is left sitting in the text as written, and that text "
        "which escaped its own ampersand comes back decoded a second time, so an escaped "
        "entity turns into the character it was protecting."
    ),
    expected=(
        "unescape(text) returns the text with every entity it recognises replaced by the "
        "character it names, including a numeric entity written as a hash and digits. Each "
        "entity is decoded once, so an escaped ampersand does not cause what follows it to be "
        "decoded again, and an entity it does not recognise is left exactly as written."
    ),
    baseline_reason=(
        "it runs one replacement per known entity over the whole text, which decodes an "
        "escaped ampersand and then decodes what that reveals, and it knows no numeric "
        "entities at all"
    ),
    edge_cases=(
        "a numeric entity is decoded to its character",
        "each entity is decoded once, so an escaped ampersand is not decoded twice",
    ),
    baseline='''def unescape(text):
    """Return `text` with its escaped entities turned back into characters."""
    table = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": chr(34)}
    for entity, character in table.items():
        text = text.replace(entity, character)
    return text''',
    variant_one='''def unescape(text):
    """Return `text` with its escaped entities turned back into characters."""
    table = {"amp": "&", "lt": "<", "gt": ">", "quot": chr(34)}
    out = []
    position = 0
    while position < len(text):
        if text[position] != "&":
            out.append(text[position])
            position += 1
            continue
        end = text.find(";", position)
        if end < 0:
            out.append(text[position])
            position += 1
            continue
        body = text[position + 1 : end]
        if body in table:
            out.append(table[body])
        elif body[:1] == "#" and body[1:].isdigit():
            out.append(chr(int(body[1:])))
        else:
            out.append(text[position : end + 1])
        position = end + 1
    return "".join(out)''',
    variant_two='''def unescape(text):
    """Return `text` with its escaped entities turned back into characters."""
    table = {"amp": "&", "lt": "<", "gt": ">", "quot": chr(34)}
    pieces = []
    rest = text
    while "&" in rest:
        before, _, after = rest.partition("&")
        pieces.append(before)
        body, closed, tail = after.partition(";")
        if not closed:
            pieces.append("&")
            rest = after
            continue
        if body in table:
            pieces.append(table[body])
        elif body[:1] == "#" and body[1:].isdigit():
            pieces.append(chr(int(body[1:])))
        else:
            pieces.append(f"&{body};")
        rest = tail
    pieces.append(rest)
    return "".join(pieces)''',
    variant_three='''def unescape(text):
    """Return `text` with its escaped entities turned back into characters."""
    table = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": chr(34)}
    for entity, character in table.items():
        text = text.replace(entity, character)
    out = []
    rest = text
    while "&#" in rest:
        before, _, after = rest.partition("&#")
        digits, closed, tail = after.partition(";")
        if closed and digits.isdigit():
            out.append(before)
            out.append(chr(int(digits)))
            rest = tail
        else:
            out.append(before + "&#")
            rest = after
    out.append(rest)
    return "".join(out)''',
    variant_four='''def unescape(text):
    """Return `text` with its escaped entities turned back into characters."""
    table = {"amp": "&", "lt": "<", "gt": ">", "quot": chr(34)}
    pieces = []
    position = 0
    while position < len(text):
        if text[position] != "&":
            pieces.append(text[position])
            position += 1
            continue
        end = text.find(";", position)
        if end < 0:
            pieces.append(text[position])
            position += 1
            continue
        body = text[position + 1 : end]
        if body in table:
            pieces.append(table[body])
        else:
            pieces.append(text[position : end + 1])
        position = end + 1
    return "".join(pieces)''',
    visible_test=_test_module(
        "entity_unescape",
        "Published contract for decoding escaped entities.",
        """
def test_an_escaped_ampersand_comes_back() -> None:
    assert unescape("a &amp; b") == "a & b"


def test_escaped_angle_brackets_come_back() -> None:
    assert unescape("&lt;tag&gt;") == "<tag>"
""",
        imports="from entity_unescape import unescape\n",
    ),
    hidden_test=_test_module(
        "entity_unescape",
        "The part of the contract the published tests do not state.",
        """
def test_an_escaped_ampersand_comes_back() -> None:
    assert unescape("a &amp; b") == "a & b"


def test_a_numeric_entity_decodes_to_its_character() -> None:
    assert unescape("&#65;&#66;") == "AB"


def test_an_escaped_ampersand_is_not_decoded_twice() -> None:
    assert unescape("&amp;lt;") == "&lt;"
""",
        imports="from entity_unescape import unescape\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G061 = D2TaskSpec(
    template_id="d5_transform.compose_pipeline",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-compose-pipeline",
    module="compose_pipeline",
    module_doc="Building one step out of a list of steps that run in the order they are read.",
    issue=(
        "compose() is documented to build one step from a list of steps that run in reading "
        "order. Callers report that the steps run in the opposite order, and that adding a "
        "step to the list after the pipeline has been built quietly changes what the pipeline "
        "already handed out does."
    ),
    expected=(
        "compose(steps) returns a callable that applies the steps to its argument in the order "
        "they are read, left to right, returning the argument unchanged when there are no "
        "steps. The list is read once when the pipeline is built, so changing it afterwards "
        "does not change the pipeline."
    ),
    baseline_reason=(
        "it walks the steps backwards, and it walks the caller's list itself rather than a "
        "copy taken when the pipeline was built"
    ),
    edge_cases=(
        "the steps run in reading order, left to right",
        "changing the list after the pipeline is built does not change the pipeline",
    ),
    imports="import functools\n",
    baseline='''def compose(steps):
    """Return a callable applying `steps` in reading order."""

    def run(value):
        for step in reversed(steps):
            value = step(value)
        return value

    return run''',
    variant_one='''def compose(steps):
    """Return a callable applying `steps` in reading order."""
    fixed = tuple(steps)

    def run(value):
        for step in fixed:
            value = step(value)
        return value

    return run''',
    variant_two='''def compose(steps):
    """Return a callable applying `steps` in reading order."""
    fixed = list(steps)

    def run(value):
        return functools.reduce(lambda carried, step: step(carried), fixed, value)

    return run''',
    variant_three='''def compose(steps):
    """Return a callable applying `steps` in reading order."""

    def run(value):
        for step in steps:
            value = step(value)
        return value

    return run''',
    variant_four='''def compose(steps):
    """Return a callable applying `steps` in reading order."""
    fixed = tuple(steps)

    def run(value):
        for step in reversed(fixed):
            value = step(value)
        return value

    return run''',
    visible_test=_test_module(
        "compose_pipeline",
        "Published contract for building one step out of many.",
        """
def test_two_steps_both_run() -> None:
    assert compose([lambda number: number + 1, lambda number: number + 2])(0) == 3


def test_no_steps_hands_the_value_straight_back() -> None:
    assert compose([])(7) == 7
""",
        imports="from compose_pipeline import compose\n",
    ),
    hidden_test=_test_module(
        "compose_pipeline",
        "The part of the contract the published tests do not state.",
        """
def test_two_steps_both_run() -> None:
    assert compose([lambda number: number + 1, lambda number: number + 2])(0) == 3


def test_the_steps_run_in_reading_order() -> None:
    assert compose([lambda number: number + 1, lambda number: number * 2])(3) == 8


def test_the_list_is_read_once_when_the_pipeline_is_built() -> None:
    steps = [lambda number: number + 1]
    pipeline = compose(steps)
    steps.append(lambda number: number * 10)
    assert pipeline(1) == 2
""",
        imports="from compose_pipeline import compose\n",
    ),
)


_G062 = D2TaskSpec(
    template_id="d5_transform.longest_match",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-longest-match",
    module="longest_match",
    module_doc="Choosing the setting whose prefix says the most about the name being looked up.",
    issue=(
        "resolve() is documented to answer with the setting whose prefix matches the name most "
        "closely. Callers report that a general prefix declared first wins over the specific "
        "one that follows it, and that a name matching no prefix at all raises rather than "
        "coming back with the default."
    ),
    expected=(
        "resolve(prefixes, name, default) returns the value of the longest prefix the name "
        "begins with, and returns the default when the name begins with none of them."
    ),
    baseline_reason=(
        "it answers with the first prefix it happens to walk past rather than the longest one, "
        "and it raises rather than falling back when nothing matches"
    ),
    edge_cases=(
        "the longest matching prefix wins, not the first declared",
        "a name matching no prefix comes back with the default",
    ),
    baseline='''def resolve(prefixes, name, default):
    """Return the value of the longest prefix `name` begins with."""
    for prefix, value in prefixes.items():
        if name.startswith(prefix):
            return value
    raise KeyError(name)''',
    variant_one='''def resolve(prefixes, name, default):
    """Return the value of the longest prefix `name` begins with."""
    best = None
    for prefix, value in prefixes.items():
        if name.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    return default if best is None else prefixes[best]''',
    variant_two='''def resolve(prefixes, name, default):
    """Return the value of the longest prefix `name` begins with."""
    matching = sorted(
        (prefix for prefix in prefixes if name.startswith(prefix)), key=len, reverse=True
    )
    if not matching:
        return default
    return prefixes[matching[0]]''',
    variant_three='''def resolve(prefixes, name, default):
    """Return the value of the longest prefix `name` begins with."""
    best = None
    for prefix in prefixes:
        if name.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    if best is None:
        raise KeyError(name)
    return prefixes[best]''',
    variant_four='''def resolve(prefixes, name, default):
    """Return the value of the longest prefix `name` begins with."""
    for prefix, value in prefixes.items():
        if name.startswith(prefix):
            return value
    return default''',
    visible_test=_test_module(
        "longest_match",
        "Published contract for choosing a setting by prefix.",
        """
def test_the_matching_prefix_answers() -> None:
    assert resolve({"a/": 1, "b/": 2}, "a/x", 0) == 1


def test_a_single_prefix_answers_for_what_it_covers() -> None:
    assert resolve({"a/": 1}, "a/y", 0) == 1
""",
        imports="from longest_match import resolve\n",
    ),
    hidden_test=_test_module(
        "longest_match",
        "The part of the contract the published tests do not state.",
        """
def test_the_matching_prefix_answers() -> None:
    assert resolve({"a/": 1, "b/": 2}, "a/x", 0) == 1


def test_the_longest_matching_prefix_wins() -> None:
    assert resolve({"a/": 1, "a/deep/": 2}, "a/deep/x", 0) == 2


def test_a_name_matching_nothing_comes_back_with_the_default() -> None:
    assert resolve({"a/": 1}, "z/x", 0) == 0
""",
        imports="from longest_match import resolve\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G063 = D2TaskSpec(
    template_id="d5_state.journal_replay",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-journal-replay",
    module="journal_replay",
    module_doc="Rebuilding a running total from a journal that may be handed over twice.",
    issue=(
        "replay() is documented to fold a journal into a running total, picking up where the "
        "cursor left off. Operators report that a hand-over which repeats the last entry "
        "counts it a second time, and that a journal missing an entry in the middle is folded "
        "in as though nothing were missing."
    ),
    expected=(
        "replay(state, entries) returns the state with the entries folded into the total and "
        "the cursor moved to the last one applied. An entry whose sequence number is at or "
        "below the cursor has already been applied and is skipped, and a gap in the sequence "
        "is refused with ValueError."
    ),
    baseline_reason=(
        "it folds in every entry it is handed without comparing its sequence number to the "
        "cursor, and it never checks the numbers run on without a gap"
    ),
    edge_cases=(
        "an entry at or below the cursor is skipped",
        "a gap in the sequence is refused",
    ),
    baseline='''def replay(state, entries):
    """Return `state` with `entries` folded in."""
    total = state["total"]
    cursor = state["cursor"]
    for entry in entries:
        total += entry["amount"]
        cursor = entry["seq"]
    return {"total": total, "cursor": cursor}''',
    variant_one='''def replay(state, entries):
    """Return `state` with `entries` folded in."""
    total = state["total"]
    cursor = state["cursor"]
    for entry in entries:
        if entry["seq"] <= cursor:
            continue
        if entry["seq"] != cursor + 1:
            raise ValueError(f"the journal skips from {cursor} to {entry['seq']}")
        total += entry["amount"]
        cursor = entry["seq"]
    return {"total": total, "cursor": cursor}''',
    variant_two='''def replay(state, entries):
    """Return `state` with `entries` folded in."""
    settled = {"total": state["total"], "cursor": state["cursor"]}
    fresh = [entry for entry in entries if entry["seq"] > settled["cursor"]]
    expected = settled["cursor"]
    for entry in fresh:
        expected += 1
        if entry["seq"] != expected:
            raise ValueError(f"the journal skips from {expected - 1} to {entry['seq']}")
    for entry in fresh:
        settled["total"] += entry["amount"]
        settled["cursor"] = entry["seq"]
    return settled''',
    variant_three='''def replay(state, entries):
    """Return `state` with `entries` folded in."""
    total = state["total"]
    cursor = state["cursor"]
    for entry in entries:
        if entry["seq"] <= cursor:
            continue
        total += entry["amount"]
        cursor = entry["seq"]
    return {"total": total, "cursor": cursor}''',
    variant_four='''def replay(state, entries):
    """Return `state` with `entries` folded in."""
    total = state["total"]
    cursor = state["cursor"]
    for entry in entries:
        if entry["seq"] != cursor + 1:
            raise ValueError(f"the journal skips from {cursor} to {entry['seq']}")
        total += entry["amount"]
        cursor = entry["seq"]
    return {"total": total, "cursor": cursor}''',
    visible_test=_test_module(
        "journal_replay",
        "Published contract for folding a journal into a running total.",
        """
def test_entries_following_the_cursor_are_folded_in() -> None:
    state = {"total": 0, "cursor": 0}
    entries = [{"seq": 1, "amount": 5}, {"seq": 2, "amount": 3}]
    assert replay(state, entries) == {"total": 8, "cursor": 2}


def test_an_empty_hand_over_changes_nothing() -> None:
    assert replay({"total": 8, "cursor": 2}, []) == {"total": 8, "cursor": 2}
""",
        imports="from journal_replay import replay\n",
    ),
    hidden_test=_test_module(
        "journal_replay",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_entries_following_the_cursor_are_folded_in() -> None:
    state = {"total": 0, "cursor": 0}
    entries = [{"seq": 1, "amount": 5}, {"seq": 2, "amount": 3}]
    assert replay(state, entries) == {"total": 8, "cursor": 2}


def test_an_entry_at_or_below_the_cursor_is_skipped() -> None:
    state = {"total": 8, "cursor": 2}
    entries = [{"seq": 2, "amount": 3}, {"seq": 3, "amount": 1}]
    assert replay(state, entries) == {"total": 9, "cursor": 3}


def test_a_gap_in_the_sequence_is_refused() -> None:
    with pytest.raises(ValueError):
        replay({"total": 0, "cursor": 0}, [{"seq": 2, "amount": 5}])
""",
        imports="from journal_replay import replay\n",
    ),
)


_G064 = D2TaskSpec(
    template_id="d5_state.snapshot_restore",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-snapshot-restore",
    module="snapshot_restore",
    module_doc="Putting a saved copy of the working settings back into use.",
    issue=(
        "restore() is documented to put a saved copy back into use. Operators report that "
        "asking for a name nobody saved fails with a KeyError rather than saying what is "
        "wrong, and that editing the settings after a restore quietly edits the saved copy "
        "along with them, so the copy can never be restored twice."
    ),
    expected=(
        "restore(store, name) returns the store with the named saved copy put back into use as "
        "the working settings. The saved copies are left as they were and the working "
        "settings are a copy of their own, so later edits do not reach back into the saved "
        "one, and a name nobody saved is refused with ValueError."
    ),
    baseline_reason=(
        "it hands the saved mapping itself back as the working settings rather than a copy, "
        "and it reaches for the name straight out of the saved copies"
    ),
    edge_cases=(
        "a name nobody saved is refused",
        "the working settings are a copy, so later edits do not reach the saved one",
    ),
    imports="import copy\n",
    baseline='''def restore(store, name):
    """Return `store` with the saved copy `name` put back into use."""
    return {"live": store["snapshots"][name], "snapshots": store["snapshots"]}''',
    variant_one='''def restore(store, name):
    """Return `store` with the saved copy `name` put back into use."""
    if name not in store["snapshots"]:
        raise ValueError(f"nobody saved a copy called {name!r}")
    return {
        "live": copy.deepcopy(store["snapshots"][name]),
        "snapshots": store["snapshots"],
    }''',
    variant_two='''def restore(store, name):
    """Return `store` with the saved copy `name` put back into use."""
    saved = store["snapshots"]
    try:
        wanted = saved[name]
    except KeyError:
        raise ValueError(f"nobody saved a copy called {name!r}") from None
    return {"live": {key: copy.deepcopy(value) for key, value in wanted.items()},
            "snapshots": saved}''',
    variant_three='''def restore(store, name):
    """Return `store` with the saved copy `name` put back into use."""
    if name not in store["snapshots"]:
        raise ValueError(f"nobody saved a copy called {name!r}")
    return {"live": store["snapshots"][name], "snapshots": store["snapshots"]}''',
    variant_four='''def restore(store, name):
    """Return `store` with the saved copy `name` put back into use."""
    return {
        "live": copy.deepcopy(store["snapshots"][name]),
        "snapshots": store["snapshots"],
    }''',
    visible_test=_test_module(
        "snapshot_restore",
        "Published contract for putting a saved copy back into use.",
        """
def test_the_saved_copy_becomes_the_working_settings() -> None:
    store = {"live": {"x": 1}, "snapshots": {"s": {"x": 9}}}
    assert restore(store, "s") == {"live": {"x": 9}, "snapshots": {"s": {"x": 9}}}


def test_the_saved_copies_are_all_still_there() -> None:
    store = {"live": {"x": 1}, "snapshots": {"s": {"x": 9}, "t": {"x": 8}}}
    assert set(restore(store, "s")["snapshots"]) == {"s", "t"}
""",
        imports="from snapshot_restore import restore\n",
    ),
    hidden_test=_test_module(
        "snapshot_restore",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_saved_copy_becomes_the_working_settings() -> None:
    store = {"live": {"x": 1}, "snapshots": {"s": {"x": 9}}}
    assert restore(store, "s") == {"live": {"x": 9}, "snapshots": {"s": {"x": 9}}}


def test_a_name_nobody_saved_is_refused() -> None:
    store = {"live": {"x": 1}, "snapshots": {"s": {"x": 9}}}
    with pytest.raises(ValueError):
        restore(store, "nobody-saved-this")


def test_editing_the_working_settings_does_not_reach_the_saved_copy() -> None:
    store = {"live": {"x": 1}, "snapshots": {"s": {"x": 9}}}
    restored = restore(store, "s")
    restored["live"]["x"] = 5
    assert restored["snapshots"]["s"] == {"x": 9}
""",
        imports="from snapshot_restore import restore\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G065 = D2TaskSpec(
    template_id="d5_error.degrade_mode",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-degrade-mode",
    module="degrade_mode",
    module_doc="Serving from a standby when the real source is down, and saying so.",
    issue=(
        "fetch() is documented to serve from the standby only when the real source is down. "
        "Operators report that the standby is asked every single time, even when the real "
        "source answered, and that when both are down the failure reported is the standby's "
        "rather than the real source's."
    ),
    expected=(
        "fetch(primary, secondary) returns (value, degraded). The primary is tried first and "
        "the secondary is not called at all when it answers. When the primary fails the "
        "secondary answers and the result is marked degraded, and when both fail the "
        "primary's failure is the one raised."
    ),
    baseline_reason=(
        "it fetches the standby up front so it is always called, and asking it first means "
        "its own failure escapes before the real source is ever tried"
    ),
    edge_cases=(
        "the secondary is not called when the primary answers",
        "when both fail the primary's failure is the one raised",
    ),
    baseline='''def fetch(primary, secondary):
    """Return (value, degraded) from the primary, or from the standby."""
    fallback = secondary()
    try:
        return primary(), False
    except Exception:
        return fallback, True''',
    variant_one='''def fetch(primary, secondary):
    """Return (value, degraded) from the primary, or from the standby."""
    try:
        return primary(), False
    except Exception as first:
        try:
            return secondary(), True
        except Exception:
            raise first from None''',
    variant_two='''def fetch(primary, secondary):
    """Return (value, degraded) from the primary, or from the standby."""
    failure = None
    try:
        value = primary()
    except Exception as error:
        failure = error
    else:
        return value, False
    try:
        return secondary(), True
    except Exception:
        pass
    raise failure''',
    variant_three='''def fetch(primary, secondary):
    """Return (value, degraded) from the primary, or from the standby."""
    try:
        return primary(), False
    except Exception:
        return secondary(), True''',
    variant_four='''def fetch(primary, secondary):
    """Return (value, degraded) from the primary, or from the standby."""
    fallback = None
    standby_failed = False
    try:
        fallback = secondary()
    except Exception:
        standby_failed = True
    try:
        return primary(), False
    except Exception:
        if standby_failed:
            raise
        return fallback, True''',
    visible_test=_test_module(
        "degrade_mode",
        "Published contract for serving from a standby.",
        """
def _refuse():
    raise RuntimeError("the real source is down")


def test_the_real_source_answers_when_it_can() -> None:
    assert fetch(lambda: "live", lambda: "cached") == ("live", False)


def test_the_standby_answers_when_the_real_source_is_down() -> None:
    assert fetch(_refuse, lambda: "cached") == ("cached", True)
""",
        imports="from degrade_mode import fetch\n",
    ),
    hidden_test=_test_module(
        "degrade_mode",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _refuse():
    raise RuntimeError("the real source is down")


def _refuse_standby():
    raise ValueError("the standby is down too")


def test_the_real_source_answers_when_it_can() -> None:
    assert fetch(lambda: "live", lambda: "cached") == ("live", False)


def test_the_standby_is_not_asked_when_the_real_source_answers() -> None:
    asked = []

    def standby():
        asked.append("asked")
        return "cached"

    fetch(lambda: "live", standby)
    assert asked == []


def test_when_both_are_down_the_real_sources_failure_is_raised() -> None:
    with pytest.raises(RuntimeError):
        fetch(_refuse, _refuse_standby)
""",
        imports="from degrade_mode import fetch\n",
    ),
)


_G066 = D2TaskSpec(
    template_id="d5_error.required_fields",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-required-fields",
    module="required_fields",
    module_doc="Checking a payload carries what the handler downstream is going to read.",
    issue=(
        "check_required() is documented to refuse a payload that does not carry every required "
        "field. Callers report that a field present but holding nothing is accepted as though "
        "it were filled in, and that a payload carrying an extra field the schema never named "
        "is refused even though nothing downstream reads it."
    ),
    expected=(
        "check_required(payload, required) returns the payload unchanged when it carries every "
        "required field with something in it. A field that is absent, or present but holding "
        "None, is missing and the payload is refused with ValueError naming what is missing. "
        "A field the schema never named is ignored."
    ),
    baseline_reason=(
        "it checks only that the key is there rather than that it holds anything, and it "
        "refuses a payload for carrying a field nobody asked about"
    ),
    edge_cases=(
        "a field present but holding None counts as missing",
        "a field the schema never named is ignored",
    ),
    baseline='''def check_required(payload, required):
    """Return `payload` when it carries every required field."""
    missing = [name for name in required if name not in payload]
    unexpected = [name for name in payload if name not in required]
    if missing or unexpected:
        raise ValueError(f"missing {sorted(missing)}, unexpected {sorted(unexpected)}")
    return payload''',
    variant_one='''def check_required(payload, required):
    """Return `payload` when it carries every required field."""
    missing = [name for name in required if payload.get(name) is None]
    if missing:
        raise ValueError(f"missing {sorted(missing)}")
    return payload''',
    variant_two='''def check_required(payload, required):
    """Return `payload` when it carries every required field."""
    filled = {name for name, value in payload.items() if value is not None}
    missing = sorted(set(required) - filled)
    if missing:
        raise ValueError(f"missing {missing}")
    return payload''',
    variant_three='''def check_required(payload, required):
    """Return `payload` when it carries every required field."""
    missing = [name for name in required if payload.get(name) is None]
    unexpected = [name for name in payload if name not in required]
    if missing or unexpected:
        raise ValueError(f"missing {sorted(missing)}, unexpected {sorted(unexpected)}")
    return payload''',
    variant_four='''def check_required(payload, required):
    """Return `payload` when it carries every required field."""
    missing = [name for name in required if name not in payload]
    if missing:
        raise ValueError(f"missing {sorted(missing)}")
    return payload''',
    visible_test=_test_module(
        "required_fields",
        "Published contract for checking a payload carries what it must.",
        """
import pytest


def test_a_payload_carrying_everything_comes_back_unchanged() -> None:
    assert check_required({"a": 1, "b": 2}, ["a", "b"]) == {"a": 1, "b": 2}


def test_a_payload_missing_a_field_is_refused() -> None:
    with pytest.raises(ValueError):
        check_required({"a": 1}, ["a", "b"])
""",
        imports="from required_fields import check_required\n",
    ),
    hidden_test=_test_module(
        "required_fields",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_payload_carrying_everything_comes_back_unchanged() -> None:
    assert check_required({"a": 1, "b": 2}, ["a", "b"]) == {"a": 1, "b": 2}


def test_a_field_holding_nothing_counts_as_missing() -> None:
    with pytest.raises(ValueError):
        check_required({"a": 1, "b": None}, ["a", "b"])


def test_a_field_the_schema_never_named_is_ignored() -> None:
    payload = {"a": 1, "b": 2, "extra": 3}
    assert check_required(payload, ["a", "b"]) == {"a": 1, "b": 2, "extra": 3}
""",
        imports="from required_fields import check_required\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G067 = D2TaskSpec(
    template_id="d5_boundary.missing_numbers",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-missing-numbers",
    module="missing_numbers",
    module_doc="Saying which numbers of an expected run never turned up.",
    issue=(
        "missing() is documented to report which numbers of an expected run are absent. "
        "Callers report that the last number of the run is never reported missing even when "
        "it is, and that a run written back to front comes back saying nothing is missing "
        "rather than being refused."
    ),
    expected=(
        "missing(present, first, last) returns the numbers from `first` to `last` inclusive "
        "that do not appear in `present`, in ascending order, and raises ValueError when "
        "`first` is above `last`."
    ),
    baseline_reason=(
        "it walks a range that stops before `last`, so the last number is never examined, and "
        "a backwards run makes that range empty rather than an error"
    ),
    edge_cases=(
        "the run includes its last number",
        "a run whose first is above its last is refused",
    ),
    baseline='''def missing(present, first, last):
    """Return the numbers from `first` to `last` that `present` does not carry."""
    known = set(present)
    return [number for number in range(first, last) if number not in known]''',
    variant_one='''def missing(present, first, last):
    """Return the numbers from `first` to `last` that `present` does not carry."""
    if first > last:
        raise ValueError(f"the run from {first} to {last} runs backwards")
    known = set(present)
    return [number for number in range(first, last + 1) if number not in known]''',
    variant_two='''def missing(present, first, last):
    """Return the numbers from `first` to `last` that `present` does not carry."""
    if first > last:
        raise ValueError(f"the run from {first} to {last} runs backwards")
    wanted = set(range(first, last + 1))
    return sorted(wanted - set(present))''',
    variant_three='''def missing(present, first, last):
    """Return the numbers from `first` to `last` that `present` does not carry."""
    known = set(present)
    return [number for number in range(first, last + 1) if number not in known]''',
    variant_four='''def missing(present, first, last):
    """Return the numbers from `first` to `last` that `present` does not carry."""
    if first > last:
        raise ValueError(f"the run from {first} to {last} runs backwards")
    known = set(present)
    return [number for number in range(first, last) if number not in known]''',
    visible_test=_test_module(
        "missing_numbers",
        "Published contract for finding the gaps in an expected run.",
        """
def test_a_gap_in_the_middle_is_reported() -> None:
    assert missing([1, 2, 4], 1, 4) == [3]


def test_a_run_of_one_that_turned_up_reports_nothing() -> None:
    assert missing([5], 5, 5) == []
""",
        imports="from missing_numbers import missing\n",
    ),
    hidden_test=_test_module(
        "missing_numbers",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_gap_in_the_middle_is_reported() -> None:
    assert missing([1, 2, 4], 1, 4) == [3]


def test_the_last_number_of_the_run_can_be_missing_too() -> None:
    assert missing([1], 1, 3) == [2, 3]


def test_a_run_that_goes_backwards_is_refused() -> None:
    with pytest.raises(ValueError):
        missing([], 5, 2)
""",
        imports="from missing_numbers import missing\n",
    ),
)


_G068 = D2TaskSpec(
    template_id="d5_boundary.knight_moves",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-knight-moves",
    module="knight_moves",
    module_doc="Listing the squares a knight can reach from where it stands.",
    issue=(
        "moves() is documented to list the squares a knight can reach, in order. Callers "
        "report that a knight standing in a corner is offered squares off the edge of the "
        "board, and that the squares come back in whatever order the move table happens to "
        "be written in."
    ),
    expected=(
        "moves(square, size) returns the squares a knight at `square` can reach on a board "
        "`size` by `size`, as (row, column) pairs, leaving out anything off the board and "
        "returning them in ascending order."
    ),
    baseline_reason=(
        "it adds every move of its table to the square without checking the result lands on "
        "the board, and it hands them back in table order"
    ),
    edge_cases=(
        "a move landing off the board is left out",
        "the squares come back in ascending order",
    ),
    baseline='''def moves(square, size):
    """Return the squares a knight at `square` can reach on a `size` board."""
    row, column = square
    steps = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
    return [(row + down, column + across) for down, across in steps]''',
    variant_one='''def moves(square, size):
    """Return the squares a knight at `square` can reach on a `size` board."""
    row, column = square
    steps = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
    landed = [(row + down, column + across) for down, across in steps]
    return sorted(
        (place for place in landed if 0 <= place[0] < size and 0 <= place[1] < size)
    )''',
    variant_two='''def moves(square, size):
    """Return the squares a knight at `square` can reach on a `size` board."""
    row, column = square
    reached = []
    for down in (-2, -1, 1, 2):
        for across in (-2, -1, 1, 2):
            if abs(down) == abs(across):
                continue
            place = (row + down, column + across)
            if 0 <= place[0] < size and 0 <= place[1] < size:
                reached.append(place)
    reached.sort()
    return reached''',
    variant_three='''def moves(square, size):
    """Return the squares a knight at `square` can reach on a `size` board."""
    row, column = square
    steps = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
    landed = [(row + down, column + across) for down, across in steps]
    return [place for place in landed if 0 <= place[0] < size and 0 <= place[1] < size]''',
    variant_four='''def moves(square, size):
    """Return the squares a knight at `square` can reach on a `size` board."""
    row, column = square
    steps = ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1))
    return sorted((row + down, column + across) for down, across in steps)''',
    visible_test=_test_module(
        "knight_moves",
        "Published contract for the squares a knight can reach.",
        """
def test_a_knight_in_the_middle_reaches_eight_squares() -> None:
    assert set(moves((4, 4), 8)) == {
        (5, 6),
        (6, 5),
        (3, 6),
        (2, 5),
        (5, 2),
        (6, 3),
        (3, 2),
        (2, 3),
    }


def test_a_knight_in_the_middle_reaches_exactly_eight() -> None:
    assert len(moves((4, 4), 8)) == 8
""",
        imports="from knight_moves import moves\n",
    ),
    hidden_test=_test_module(
        "knight_moves",
        "The part of the contract the published tests do not state.",
        """
def test_a_knight_in_the_middle_reaches_exactly_eight() -> None:
    assert len(moves((4, 4), 8)) == 8


def test_a_knight_in_the_corner_is_offered_nothing_off_the_board() -> None:
    assert moves((0, 0), 8) == [(1, 2), (2, 1)]


def test_the_squares_come_back_in_ascending_order() -> None:
    assert moves((4, 4), 8) == [
        (2, 3),
        (2, 5),
        (3, 2),
        (3, 6),
        (5, 2),
        (5, 6),
        (6, 3),
        (6, 5),
    ]
""",
        imports="from knight_moves import moves\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G069 = D2TaskSpec(
    template_id="d5_numeric.twos_complement",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-twos-complement",
    module="twos_complement",
    module_doc="Reading a fixed-width register value as the signed number it stands for.",
    issue=(
        "signed() is documented to read a fixed-width register value as a signed number. "
        "Firmware reports that the most negative value of the range reads back as a large "
        "positive one, and that a value too wide for the register is read as though it fitted."
    ),
    expected=(
        "signed(value, bits) returns the signed number a `bits`-wide register holding `value` "
        "stands for, so anything from half the range upwards is negative, and raises "
        "ValueError for a value that does not fit in `bits` bits."
    ),
    baseline_reason=(
        "it treats only values strictly above the halfway point as negative, which leaves the "
        "halfway point itself positive, and it never checks the value fits the register"
    ),
    edge_cases=(
        "the halfway value is the most negative number, not a positive one",
        "a value too wide for the register is refused",
    ),
    baseline='''def signed(value, bits):
    """Return the signed number a `bits`-wide register holding `value` stands for."""
    if value > 2 ** (bits - 1):
        return value - 2**bits
    return value''',
    variant_one='''def signed(value, bits):
    """Return the signed number a `bits`-wide register holding `value` stands for."""
    if not 0 <= value < 2**bits:
        raise ValueError(f"{value} does not fit in {bits} bits")
    if value >= 2 ** (bits - 1):
        return value - 2**bits
    return value''',
    variant_two='''def signed(value, bits):
    """Return the signed number a `bits`-wide register holding `value` stands for."""
    span = 2**bits
    if value < 0 or value >= span:
        raise ValueError(f"{value} does not fit in {bits} bits")
    return (value + span // 2) % span - span // 2''',
    variant_three='''def signed(value, bits):
    """Return the signed number a `bits`-wide register holding `value` stands for."""
    if value >= 2 ** (bits - 1):
        return value - 2**bits
    return value''',
    variant_four='''def signed(value, bits):
    """Return the signed number a `bits`-wide register holding `value` stands for."""
    if not 0 <= value < 2**bits:
        raise ValueError(f"{value} does not fit in {bits} bits")
    if value > 2 ** (bits - 1):
        return value - 2**bits
    return value''',
    visible_test=_test_module(
        "twos_complement",
        "Published contract for reading a register as a signed number.",
        """
def test_a_small_value_reads_as_itself() -> None:
    assert signed(5, 8) == 5


def test_a_value_in_the_upper_half_reads_as_negative() -> None:
    assert signed(200, 8) == -56


def test_zero_reads_as_zero() -> None:
    assert signed(0, 8) == 0
""",
        imports="from twos_complement import signed\n",
    ),
    hidden_test=_test_module(
        "twos_complement",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_small_value_reads_as_itself() -> None:
    assert signed(5, 8) == 5


def test_the_halfway_value_is_the_most_negative_number() -> None:
    assert signed(128, 8) == -128


def test_a_value_too_wide_for_the_register_is_refused() -> None:
    with pytest.raises(ValueError):
        signed(300, 8)
""",
        imports="from twos_complement import signed\n",
    ),
)


_G070 = D2TaskSpec(
    template_id="d5_numeric.triangle_kind",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-triangle-kind",
    module="triangle_kind",
    module_doc="Naming what kind of triangle three measured sides make.",
    issue=(
        "classify() is documented to name the kind of triangle three sides make. Surveyors "
        "report that a triangle whose two equal sides are not the first two is called scalene, "
        "and that three lengths which could never close into a triangle are named as though "
        "they could."
    ),
    expected=(
        "classify(first, second, third) returns 'equilateral' when all three sides are equal, "
        "'isosceles' when exactly two are, whichever two they are, and 'scalene' when none "
        "are, and raises ValueError when the sides cannot close into a triangle."
    ),
    baseline_reason=(
        "it compares only the first two sides when looking for a matching pair, and it never "
        "checks that the two shorter sides together reach past the longest"
    ),
    edge_cases=(
        "two equal sides are found whichever two they are",
        "sides that cannot close into a triangle are refused",
    ),
    baseline='''def classify(first, second, third):
    """Return the kind of triangle `first`, `second` and `third` make."""
    if first == second == third:
        return "equilateral"
    if first == second:
        return "isosceles"
    return "scalene"''',
    variant_one='''def classify(first, second, third):
    """Return the kind of triangle `first`, `second` and `third` make."""
    sides = sorted((first, second, third))
    if sides[0] + sides[1] <= sides[2]:
        raise ValueError(f"{sides} cannot close into a triangle")
    if sides[0] == sides[2]:
        return "equilateral"
    if sides[0] == sides[1] or sides[1] == sides[2]:
        return "isosceles"
    return "scalene"''',
    variant_two='''def classify(first, second, third):
    """Return the kind of triangle `first`, `second` and `third` make."""
    sides = sorted((first, second, third))
    if sides[0] + sides[1] <= sides[2]:
        raise ValueError(f"{sides} cannot close into a triangle")
    distinct = len(set(sides))
    if distinct == 1:
        return "equilateral"
    if distinct == 2:
        return "isosceles"
    return "scalene"''',
    variant_three='''def classify(first, second, third):
    """Return the kind of triangle `first`, `second` and `third` make."""
    sides = sorted((first, second, third))
    if sides[0] == sides[2]:
        return "equilateral"
    if sides[0] == sides[1] or sides[1] == sides[2]:
        return "isosceles"
    return "scalene"''',
    variant_four='''def classify(first, second, third):
    """Return the kind of triangle `first`, `second` and `third` make."""
    sides = sorted((first, second, third))
    if sides[0] + sides[1] <= sides[2]:
        raise ValueError(f"{sides} cannot close into a triangle")
    if first == second == third:
        return "equilateral"
    if first == second:
        return "isosceles"
    return "scalene"''',
    visible_test=_test_module(
        "triangle_kind",
        "Published contract for naming a triangle.",
        """
def test_three_equal_sides_are_equilateral() -> None:
    assert classify(3, 3, 3) == "equilateral"


def test_the_first_two_sides_equal_is_isosceles() -> None:
    assert classify(3, 3, 4) == "isosceles"


def test_three_different_sides_are_scalene() -> None:
    assert classify(3, 4, 5) == "scalene"
""",
        imports="from triangle_kind import classify\n",
    ),
    hidden_test=_test_module(
        "triangle_kind",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_three_equal_sides_are_equilateral() -> None:
    assert classify(3, 3, 3) == "equilateral"


def test_the_equal_pair_is_found_whichever_two_it_is() -> None:
    assert classify(3, 4, 3) == "isosceles"
    assert classify(4, 3, 3) == "isosceles"


def test_sides_that_cannot_close_are_refused() -> None:
    with pytest.raises(ValueError):
        classify(1, 2, 10)
""",
        imports="from triangle_kind import classify\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G071 = D2TaskSpec(
    template_id="d5_parsing.subtitle_timestamp",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-subtitle-timestamp",
    module="subtitle_timestamp",
    module_doc="Reading a subtitle cue time into the milliseconds the player counts in.",
    issue=(
        "to_millis() is documented to read a subtitle cue time into milliseconds. Editors "
        "report that a file written with a full stop before the milliseconds instead of a "
        "comma fails outright, and that a nonsense time with seventy-five minutes in it is "
        "read as though it were fine."
    ),
    expected=(
        "to_millis(stamp) returns the cue time in milliseconds. The milliseconds are "
        "separated by either a comma or a full stop, hours may run past twenty-four because a "
        "cue time is a duration, and minutes or seconds of sixty or more are refused with "
        "ValueError."
    ),
    baseline_reason=(
        "it splits the milliseconds off at a comma only, so a full stop leaves nothing to read "
        "them from, and it converts the fields without checking any of them are in range"
    ),
    edge_cases=(
        "a full stop before the milliseconds reads the same as a comma",
        "minutes or seconds of sixty or more are refused",
    ),
    baseline='''def to_millis(stamp):
    """Return the cue time `stamp` in milliseconds."""
    clock, _, millis = stamp.partition(",")
    hours, minutes, seconds = clock.split(":")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)''',
    variant_one='''def to_millis(stamp):
    """Return the cue time `stamp` in milliseconds."""
    clock, _, millis = stamp.replace(".", ",").partition(",")
    hours, minutes, seconds = (int(field) for field in clock.split(":"))
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"{stamp!r} has a field of sixty or more")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(millis)''',
    variant_two='''def to_millis(stamp):
    """Return the cue time `stamp` in milliseconds."""
    for mark in (",", "."):
        clock, found, millis = stamp.partition(mark)
        if found:
            break
    fields = [int(field) for field in clock.split(":")]
    for field in fields[1:]:
        if field >= 60:
            raise ValueError(f"{stamp!r} has a field of sixty or more")
    total = 0
    for field in fields:
        total = total * 60 + field
    return total * 1000 + int(millis)''',
    variant_three='''def to_millis(stamp):
    """Return the cue time `stamp` in milliseconds."""
    clock, _, millis = stamp.replace(".", ",").partition(",")
    hours, minutes, seconds = clock.split(":")
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)''',
    variant_four='''def to_millis(stamp):
    """Return the cue time `stamp` in milliseconds."""
    clock, _, millis = stamp.partition(",")
    hours, minutes, seconds = (int(field) for field in clock.split(":"))
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"{stamp!r} has a field of sixty or more")
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + int(millis)''',
    visible_test=_test_module(
        "subtitle_timestamp",
        "Published contract for reading a subtitle cue time.",
        """
def test_a_second_and_a_half_reads_as_its_milliseconds() -> None:
    assert to_millis("00:00:01,500") == 1500


def test_a_full_cue_time_reads_every_field() -> None:
    assert to_millis("01:02:03,004") == 3723004
""",
        imports="from subtitle_timestamp import to_millis\n",
    ),
    hidden_test=_test_module(
        "subtitle_timestamp",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_second_and_a_half_reads_as_its_milliseconds() -> None:
    assert to_millis("00:00:01,500") == 1500


def test_a_full_stop_reads_the_same_as_a_comma() -> None:
    assert to_millis("00:00:01.500") == 1500


def test_a_field_of_sixty_or_more_is_refused() -> None:
    with pytest.raises(ValueError):
        to_millis("00:75:00,000")
""",
        imports="from subtitle_timestamp import to_millis\n",
    ),
)


_G072 = D2TaskSpec(
    template_id="d5_parsing.mime_type",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-mime-type",
    module="mime_type",
    module_doc="Taking a content type header apart into its type and its parameters.",
    issue=(
        "parse_mime() is documented to take a content type apart. Callers report that a "
        "parameter written in quotes keeps its quotes in the value, and that a parameter value "
        "which is meant to be case-sensitive, such as a multipart boundary, comes back "
        "flattened to lowercase."
    ),
    expected=(
        "parse_mime(text) returns (type, subtype, parameters). The type and subtype are "
        "lowercased because they are case-insensitive, a parameter name is lowercased for the "
        "same reason, and a parameter value keeps the case it was written in with any "
        "surrounding quotes removed."
    ),
    baseline_reason=(
        "it lowercases the parameter value along with everything else, and it takes the value "
        "exactly as written including the quotes around it"
    ),
    edge_cases=(
        "a quoted parameter value loses its quotes",
        "a parameter value keeps the case it was written in",
    ),
    baseline='''def parse_mime(text):
    """Return (type, subtype, parameters) for the content type `text`."""
    head, _, rest = text.partition(";")
    kind, _, subtype = head.strip().partition("/")
    parameters = {}
    for part in rest.split(";"):
        if not part.strip():
            continue
        name, _, value = part.strip().partition("=")
        parameters[name.lower()] = value.lower()
    return kind.lower(), subtype.lower(), parameters''',
    variant_one='''def parse_mime(text):
    """Return (type, subtype, parameters) for the content type `text`."""
    head, _, rest = text.partition(";")
    kind, _, subtype = head.strip().partition("/")
    parameters = {}
    for part in rest.split(";"):
        if not part.strip():
            continue
        name, _, value = part.strip().partition("=")
        parameters[name.lower()] = value.strip(chr(34))
    return kind.lower(), subtype.lower(), parameters''',
    variant_two='''def parse_mime(text):
    """Return (type, subtype, parameters) for the content type `text`."""
    pieces = [piece.strip() for piece in text.split(";")]
    kind, _, subtype = pieces[0].partition("/")
    quote = chr(34)
    parameters = {}
    for piece in pieces[1:]:
        if not piece:
            continue
        name, _, value = piece.partition("=")
        if len(value) >= 2 and value[0] == quote and value[-1] == quote:
            value = value[1:-1]
        parameters[name.lower()] = value
    return kind.lower(), subtype.lower(), parameters''',
    variant_three='''def parse_mime(text):
    """Return (type, subtype, parameters) for the content type `text`."""
    head, _, rest = text.partition(";")
    kind, _, subtype = head.strip().partition("/")
    parameters = {}
    for part in rest.split(";"):
        if not part.strip():
            continue
        name, _, value = part.strip().partition("=")
        parameters[name.lower()] = value.strip(chr(34)).lower()
    return kind.lower(), subtype.lower(), parameters''',
    variant_four='''def parse_mime(text):
    """Return (type, subtype, parameters) for the content type `text`."""
    head, _, rest = text.partition(";")
    kind, _, subtype = head.strip().partition("/")
    parameters = {}
    for part in rest.split(";"):
        if not part.strip():
            continue
        name, _, value = part.strip().partition("=")
        parameters[name.lower()] = value
    return kind.lower(), subtype.lower(), parameters''',
    visible_test=_test_module(
        "mime_type",
        "Published contract for taking a content type apart.",
        """
def test_a_bare_content_type_has_no_parameters() -> None:
    assert parse_mime("text/html") == ("text", "html", {})


def test_the_type_and_subtype_are_lowercased() -> None:
    assert parse_mime("Text/HTML; charset=utf-8") == ("text", "html", {"charset": "utf-8"})
""",
        imports="from mime_type import parse_mime\n",
    ),
    hidden_test=_test_module(
        "mime_type",
        "The part of the contract the published tests do not state.",
        """
def test_a_bare_content_type_has_no_parameters() -> None:
    assert parse_mime("text/html") == ("text", "html", {})


def test_a_quoted_value_loses_its_quotes() -> None:
    quoted = "text/plain; name=" + chr(34) + "a b" + chr(34)
    assert parse_mime(quoted) == ("text", "plain", {"name": "a b"})


def test_a_parameter_value_keeps_its_case() -> None:
    assert parse_mime("text/plain; boundary=AbC") == ("text", "plain", {"boundary": "AbC"})
""",
        imports="from mime_type import parse_mime\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G073 = D2TaskSpec(
    template_id="d5_transform.fill_template",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-fill-template",
    module="fill_template",
    module_doc="Filling the named holes in a message template from a set of values.",
    issue=(
        "fill() is documented to fill the named holes in a template. Callers report that a "
        "hole nobody supplied a value for brings the whole render down instead of being left "
        "as written, and that a doubled brace, which is how the template writes a literal "
        "brace, is read as the start of a hole."
    ),
    expected=(
        "fill(template, values) returns the template with each {name} hole replaced by its "
        "value. A doubled brace stands for one literal brace and opens no hole, and a hole "
        "nobody supplied a value for is left exactly as written."
    ),
    baseline_reason=(
        "it reaches for every name straight out of the values, and it treats the first brace "
        "of a doubled pair as opening a hole"
    ),
    edge_cases=(
        "a hole with no value supplied is left as written",
        "a doubled brace stands for one literal brace",
    ),
    baseline='''def fill(template, values):
    """Return `template` with its named holes filled from `values`."""
    out = []
    rest = template
    while "{" in rest:
        before, _, after = rest.partition("{")
        name, _, tail = after.partition("}")
        out.append(before)
        out.append(str(values[name]))
        rest = tail
    out.append(rest)
    return "".join(out)''',
    variant_one='''def fill(template, values):
    """Return `template` with its named holes filled from `values`."""
    out = []
    position = 0
    while position < len(template):
        letter = template[position]
        if letter in "{}" and template[position : position + 2] == letter * 2:
            out.append(letter)
            position += 2
            continue
        if letter != "{":
            out.append(letter)
            position += 1
            continue
        end = template.find("}", position)
        if end < 0:
            out.append(letter)
            position += 1
            continue
        name = template[position + 1 : end]
        out.append(str(values[name]) if name in values else template[position : end + 1])
        position = end + 1
    return "".join(out)''',
    variant_two='''def fill(template, values):
    """Return `template` with its named holes filled from `values`."""
    pieces = []
    for chunk in template.split("{{"):
        rendered = []
        for part in chunk.split("}}"):
            out = []
            rest = part
            while "{" in rest:
                before, _, after = rest.partition("{")
                name, closed, tail = after.partition("}")
                out.append(before)
                if not closed:
                    out.append("{" + name)
                    rest = ""
                    break
                out.append(str(values[name]) if name in values else "{" + name + "}")
                rest = tail
            out.append(rest)
            rendered.append("".join(out))
        pieces.append("}".join(rendered))
    return "{".join(pieces)''',
    variant_three='''def fill(template, values):
    """Return `template` with its named holes filled from `values`."""
    out = []
    rest = template
    while "{" in rest:
        before, _, after = rest.partition("{")
        name, _, tail = after.partition("}")
        out.append(before)
        out.append(str(values[name]) if name in values else "{" + name + "}")
        rest = tail
    out.append(rest)
    return "".join(out)''',
    variant_four='''def fill(template, values):
    """Return `template` with its named holes filled from `values`."""
    out = []
    position = 0
    while position < len(template):
        letter = template[position]
        if letter in "{}" and template[position : position + 2] == letter * 2:
            out.append(letter)
            position += 2
            continue
        if letter != "{":
            out.append(letter)
            position += 1
            continue
        end = template.find("}", position)
        if end < 0:
            out.append(letter)
            position += 1
            continue
        name = template[position + 1 : end]
        out.append(str(values[name]))
        position = end + 1
    return "".join(out)''',
    visible_test=_test_module(
        "fill_template",
        "Published contract for filling a message template.",
        """
def test_a_named_hole_is_filled() -> None:
    assert fill("hi {name}", {"name": "ada"}) == "hi ada"


def test_a_template_with_no_holes_comes_back_as_written() -> None:
    assert fill("no fields", {}) == "no fields"
""",
        imports="from fill_template import fill\n",
    ),
    hidden_test=_test_module(
        "fill_template",
        "The part of the contract the published tests do not state.",
        """
def test_a_named_hole_is_filled() -> None:
    assert fill("hi {name}", {"name": "ada"}) == "hi ada"


def test_a_hole_with_no_value_is_left_as_written() -> None:
    assert fill("hi {who}", {}) == "hi {who}"


def test_a_doubled_brace_stands_for_one_literal_brace() -> None:
    assert fill("a {{b}} c", {}) == "a {b} c"
""",
        imports="from fill_template import fill\n",
    ),
)


_G074 = D2TaskSpec(
    template_id="d5_transform.explode_delimited",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-explode-delimited",
    module="explode_delimited",
    module_doc="Turning one record whose field lists several values into one record each.",
    issue=(
        "explode() is documented to turn a record whose field lists several values into one "
        "record per value. Callers report that a list written with a space after each "
        "separator keeps that space in the value, and that a record which simply does not "
        "carry the field brings the whole run down with a KeyError."
    ),
    expected=(
        "explode(records, field, separator) returns one record per value of the named field, "
        "each carrying the record's other fields unchanged, with the surrounding whitespace "
        "trimmed off every value, and passes a record that does not carry the field through "
        "unchanged."
    ),
    baseline_reason=(
        "it splits on the separator and keeps whatever whitespace was written around each "
        "value, and it reaches for the field without checking the record carries it"
    ),
    edge_cases=(
        "the whitespace around each value is trimmed off",
        "a record not carrying the field passes through unchanged",
    ),
    baseline='''def explode(records, field, separator):
    """Return one record per value of `field`."""
    out = []
    for record in records:
        for value in record[field].split(separator):
            out.append({**record, field: value})
    return out''',
    variant_one='''def explode(records, field, separator):
    """Return one record per value of `field`."""
    out = []
    for record in records:
        if field not in record:
            out.append(record)
            continue
        for value in record[field].split(separator):
            out.append({**record, field: value.strip()})
    return out''',
    variant_two='''def explode(records, field, separator):
    """Return one record per value of `field`."""
    return [
        {**record, field: value.strip()}
        if field in record
        else record
        for record in records
        for value in (record[field].split(separator) if field in record else [None])
    ]''',
    variant_three='''def explode(records, field, separator):
    """Return one record per value of `field`."""
    out = []
    for record in records:
        for value in record[field].split(separator):
            out.append({**record, field: value.strip()})
    return out''',
    variant_four='''def explode(records, field, separator):
    """Return one record per value of `field`."""
    out = []
    for record in records:
        if field not in record:
            out.append(record)
            continue
        for value in record[field].split(separator):
            out.append({**record, field: value})
    return out''',
    visible_test=_test_module(
        "explode_delimited",
        "Published contract for turning a listed field into one record per value.",
        """
def test_a_two_value_field_gives_two_records() -> None:
    assert explode([{"id": 1, "tags": "a,b"}], "tags", ",") == [
        {"id": 1, "tags": "a"},
        {"id": 1, "tags": "b"},
    ]


def test_no_records_gives_no_records() -> None:
    assert explode([], "tags", ",") == []
""",
        imports="from explode_delimited import explode\n",
    ),
    hidden_test=_test_module(
        "explode_delimited",
        "The part of the contract the published tests do not state.",
        """
def test_a_two_value_field_gives_two_records() -> None:
    assert explode([{"id": 1, "tags": "a,b"}], "tags", ",") == [
        {"id": 1, "tags": "a"},
        {"id": 1, "tags": "b"},
    ]


def test_the_space_after_a_separator_is_trimmed_off() -> None:
    assert explode([{"id": 1, "tags": "a, b"}], "tags", ",") == [
        {"id": 1, "tags": "a"},
        {"id": 1, "tags": "b"},
    ]


def test_a_record_without_the_field_passes_through() -> None:
    assert explode([{"id": 1}], "tags", ",") == [{"id": 1}]
""",
        imports="from explode_delimited import explode\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G075 = D2TaskSpec(
    template_id="d5_state.leader_lease",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-leader-lease",
    module="leader_lease",
    module_doc="Handing leadership to one node at a time and taking it back when it lapses.",
    issue=(
        "renew() is documented to hand leadership to one node at a time. Operators report that "
        "a node which died still holds the lease for ever because nobody may take a lease that "
        "has already run out, and that the node currently holding it cannot renew its own "
        "lease before it lapses."
    ),
    expected=(
        "renew(state, node, now, term) returns the state with `node` holding the lease until "
        "now plus term. Leadership is free when nobody holds it or when the lease has run out "
        "at `now`, the node already holding it may always renew, and any other node asking "
        "while the lease is live is refused with RuntimeError."
    ),
    baseline_reason=(
        "it refuses whenever a holder is recorded at all, without looking at whether the lease "
        "has run out or at whether the asker is the holder"
    ),
    edge_cases=(
        "a lease that has run out may be taken by another node",
        "the node holding a live lease may renew it",
    ),
    baseline='''def renew(state, node, now, term):
    """Return `state` with `node` holding the lease until `now` plus `term`."""
    if state["holder"] is not None:
        raise RuntimeError(f"{state['holder']!r} holds the lease")
    return {"holder": node, "until": now + term}''',
    variant_one='''def renew(state, node, now, term):
    """Return `state` with `node` holding the lease until `now` plus `term`."""
    holder = state["holder"]
    live = holder is not None and state["until"] > now
    if live and holder != node:
        raise RuntimeError(f"{holder!r} holds the lease")
    return {"holder": node, "until": now + term}''',
    variant_two='''def renew(state, node, now, term):
    """Return `state` with `node` holding the lease until `now` plus `term`."""
    holder = state["holder"]
    if holder == node or holder is None or state["until"] <= now:
        return {"holder": node, "until": now + term}
    raise RuntimeError(f"{holder!r} holds the lease")''',
    variant_three='''def renew(state, node, now, term):
    """Return `state` with `node` holding the lease until `now` plus `term`."""
    holder = state["holder"]
    if holder is not None and state["until"] > now:
        raise RuntimeError(f"{holder!r} holds the lease")
    return {"holder": node, "until": now + term}''',
    variant_four='''def renew(state, node, now, term):
    """Return `state` with `node` holding the lease until `now` plus `term`."""
    holder = state["holder"]
    if holder is not None and holder != node:
        raise RuntimeError(f"{holder!r} holds the lease")
    return {"holder": node, "until": now + term}''',
    visible_test=_test_module(
        "leader_lease",
        "Published contract for handing out leadership.",
        """
import pytest


def test_a_free_lease_is_taken() -> None:
    assert renew({"holder": None, "until": 0}, "a", 5, 10) == {"holder": "a", "until": 15}


def test_another_node_is_refused_while_the_lease_is_live() -> None:
    with pytest.raises(RuntimeError):
        renew({"holder": "a", "until": 100}, "b", 5, 10)
""",
        imports="from leader_lease import renew\n",
    ),
    hidden_test=_test_module(
        "leader_lease",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_free_lease_is_taken() -> None:
    assert renew({"holder": None, "until": 0}, "a", 5, 10) == {"holder": "a", "until": 15}


def test_a_lease_that_has_run_out_may_be_taken() -> None:
    assert renew({"holder": "a", "until": 3}, "b", 5, 10) == {"holder": "b", "until": 15}


def test_the_holder_may_renew_a_live_lease() -> None:
    assert renew({"holder": "a", "until": 100}, "a", 5, 10) == {"holder": "a", "until": 15}
""",
        imports="from leader_lease import renew\n",
    ),
)


_G076 = D2TaskSpec(
    template_id="d5_state.reference_count",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-reference-count",
    module="reference_count",
    module_doc="Letting go of a shared handle and clearing it away when nobody holds it.",
    issue=(
        "release() is documented to let go of one hold on a shared handle. Callers report that "
        "a handle nobody holds any more is left behind with a count of zero rather than being "
        "cleared away, and that letting go of something never held drives the count below zero "
        "instead of being refused."
    ),
    expected=(
        "release(counts, name) returns the counts with one hold on `name` let go. A handle "
        "whose last hold is let go is cleared away rather than left at zero, letting go of a "
        "handle nobody holds is refused with ValueError, and the caller's counts are left "
        "alone."
    ),
    baseline_reason=(
        "it subtracts one from whatever it finds, defaulting to zero, so the last hold leaves "
        "a zero behind and a handle nobody holds goes to minus one"
    ),
    edge_cases=(
        "letting go of the last hold clears the handle away",
        "letting go of a handle nobody holds is refused",
    ),
    baseline='''def release(counts, name):
    """Return `counts` with one hold on `name` let go."""
    updated = dict(counts)
    updated[name] = updated.get(name, 0) - 1
    return updated''',
    variant_one='''def release(counts, name):
    """Return `counts` with one hold on `name` let go."""
    if name not in counts:
        raise ValueError(f"nobody holds {name!r}")
    updated = dict(counts)
    updated[name] -= 1
    if updated[name] == 0:
        del updated[name]
    return updated''',
    variant_two='''def release(counts, name):
    """Return `counts` with one hold on `name` let go."""
    held = counts.get(name)
    if held is None:
        raise ValueError(f"nobody holds {name!r}")
    return {
        key: (held - 1 if key == name else value)
        for key, value in counts.items()
        if key != name or held > 1
    }''',
    variant_three='''def release(counts, name):
    """Return `counts` with one hold on `name` let go."""
    updated = dict(counts)
    updated[name] = updated.get(name, 0) - 1
    if updated[name] == 0:
        del updated[name]
    return updated''',
    variant_four='''def release(counts, name):
    """Return `counts` with one hold on `name` let go."""
    if name not in counts:
        raise ValueError(f"nobody holds {name!r}")
    updated = dict(counts)
    updated[name] -= 1
    return updated''',
    visible_test=_test_module(
        "reference_count",
        "Published contract for letting go of a shared handle.",
        """
def test_one_hold_of_several_is_let_go() -> None:
    assert release({"a": 2}, "a") == {"a": 1}


def test_the_other_handles_are_left_alone() -> None:
    assert release({"a": 3, "b": 1}, "a") == {"a": 2, "b": 1}


def test_the_callers_counts_are_left_alone() -> None:
    counts = {"a": 2}
    release(counts, "a")
    assert counts == {"a": 2}
""",
        imports="from reference_count import release\n",
    ),
    hidden_test=_test_module(
        "reference_count",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_hold_of_several_is_let_go() -> None:
    assert release({"a": 2}, "a") == {"a": 1}


def test_letting_go_of_the_last_hold_clears_the_handle_away() -> None:
    assert release({"a": 1}, "a") == {}


def test_letting_go_of_a_handle_nobody_holds_is_refused() -> None:
    with pytest.raises(ValueError):
        release({"a": 1}, "b")
""",
        imports="from reference_count import release\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G077 = D2TaskSpec(
    template_id="d5_error.quorum_outcome",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-quorum-outcome",
    module="quorum_outcome",
    module_doc="Deciding whether enough members answered for the group to act.",
    issue=(
        "decide() is documented to let the group act once enough members have answered. "
        "Operators report that a run answering exactly the number needed is turned down, and "
        "that one member answering twice is counted as two members."
    ),
    expected=(
        "decide(results, needed) returns True when at least `needed` distinct members "
        "answered successfully, counting a member that answered more than once only once, and "
        "otherwise raises ValueError naming every member that failed, sorted."
    ),
    baseline_reason=(
        "it demands strictly more successes than the number needed rather than at least that "
        "many, and it counts answers rather than members"
    ),
    edge_cases=(
        "exactly the number needed is enough",
        "a member answering more than once counts once",
    ),
    baseline='''def decide(results, needed):
    """Return True when enough distinct members answered successfully."""
    good = [name for name, ok, _ in results if ok]
    if len(good) > needed:
        return True
    bad = [name for name, ok, _ in results if not ok]
    raise ValueError(f"quorum not reached, failing: {sorted(set(bad))}")''',
    variant_one='''def decide(results, needed):
    """Return True when enough distinct members answered successfully."""
    good = {name for name, ok, _ in results if ok}
    if len(good) >= needed:
        return True
    bad = {name for name, ok, _ in results if not ok}
    raise ValueError(f"quorum not reached, failing: {sorted(bad)}")''',
    variant_two='''def decide(results, needed):
    """Return True when enough distinct members answered successfully."""
    answered = {}
    for name, ok, _ in results:
        answered[name] = answered.get(name, False) or ok
    if sum(1 for ok in answered.values() if ok) >= needed:
        return True
    failing = sorted(name for name, ok in answered.items() if not ok)
    raise ValueError(f"quorum not reached, failing: {failing}")''',
    variant_three='''def decide(results, needed):
    """Return True when enough distinct members answered successfully."""
    good = [name for name, ok, _ in results if ok]
    if len(good) >= needed:
        return True
    bad = [name for name, ok, _ in results if not ok]
    raise ValueError(f"quorum not reached, failing: {sorted(set(bad))}")''',
    variant_four='''def decide(results, needed):
    """Return True when enough distinct members answered successfully."""
    good = {name for name, ok, _ in results if ok}
    if len(good) > needed:
        return True
    bad = {name for name, ok, _ in results if not ok}
    raise ValueError(f"quorum not reached, failing: {sorted(bad)}")''',
    visible_test=_test_module(
        "quorum_outcome",
        "Published contract for deciding whether the group may act.",
        """
import pytest


def test_more_than_enough_members_lets_the_group_act() -> None:
    results = [("a", True, ""), ("b", True, ""), ("c", True, "")]
    assert decide(results, 2) is True


def test_too_few_members_is_refused() -> None:
    with pytest.raises(ValueError):
        decide([("a", False, "down")], 1)
""",
        imports="from quorum_outcome import decide\n",
    ),
    hidden_test=_test_module(
        "quorum_outcome",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_more_than_enough_members_lets_the_group_act() -> None:
    results = [("a", True, ""), ("b", True, ""), ("c", True, "")]
    assert decide(results, 2) is True


def test_exactly_the_number_needed_is_enough() -> None:
    assert decide([("a", True, ""), ("b", True, "")], 2) is True


def test_one_member_answering_three_times_is_still_one_member() -> None:
    results = [("a", True, ""), ("a", True, ""), ("a", True, "")]
    with pytest.raises(ValueError):
        decide(results, 2)
""",
        imports="from quorum_outcome import decide\n",
    ),
)


_G078 = D2TaskSpec(
    template_id="d5_error.suppress_expected",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-suppress-expected",
    module="suppress_expected",
    module_doc="Running a step and swallowing only the failures that were expected.",
    issue=(
        "run_ignoring() is documented to swallow only the failures listed and answer with the "
        "fallback. Callers report that a narrower error derived from a listed one is not "
        "swallowed, and that a step which legitimately answers with nothing is treated as "
        "though it had failed and gets the fallback instead."
    ),
    expected=(
        "run_ignoring(body, ignored, fallback) returns what the body returned, including None "
        "when that is genuinely the answer. A failure of any listed kind, or of a kind derived "
        "from one, is swallowed and the fallback returned instead; anything else is raised on."
    ),
    baseline_reason=(
        "it compares the failure's exact type against the list rather than asking whether it "
        "is one of them, and it treats an answer of None as a failure worth replacing"
    ),
    edge_cases=(
        "a failure derived from a listed kind is swallowed too",
        "an answer of None is the answer, not a reason for the fallback",
    ),
    baseline='''def run_ignoring(body, ignored, fallback):
    """Run `body`, swallowing the listed failures and answering with `fallback`."""
    try:
        result = body()
    except Exception as error:
        if type(error) in ignored:
            return fallback
        raise
    return result if result is not None else fallback''',
    variant_one='''def run_ignoring(body, ignored, fallback):
    """Run `body`, swallowing the listed failures and answering with `fallback`."""
    try:
        return body()
    except Exception as error:
        if isinstance(error, tuple(ignored)):
            return fallback
        raise''',
    variant_two='''def run_ignoring(body, ignored, fallback):
    """Run `body`, swallowing the listed failures and answering with `fallback`."""
    kinds = tuple(ignored)
    try:
        return body()
    except kinds:
        return fallback''',
    variant_three='''def run_ignoring(body, ignored, fallback):
    """Run `body`, swallowing the listed failures and answering with `fallback`."""
    try:
        result = body()
    except Exception as error:
        if isinstance(error, tuple(ignored)):
            return fallback
        raise
    return result if result is not None else fallback''',
    variant_four='''def run_ignoring(body, ignored, fallback):
    """Run `body`, swallowing the listed failures and answering with `fallback`."""
    try:
        return body()
    except Exception as error:
        if type(error) in ignored:
            return fallback
        raise''',
    visible_test=_test_module(
        "suppress_expected",
        "Published contract for swallowing only the expected failures.",
        """
import pytest


def _refuse():
    raise ValueError("expected")


def _refuse_differently():
    raise RuntimeError("not expected")


def test_a_step_that_works_answers_with_its_result() -> None:
    assert run_ignoring(lambda: 7, (ValueError,), 0) == 7


def test_a_listed_failure_is_swallowed() -> None:
    assert run_ignoring(_refuse, (ValueError,), 0) == 0


def test_a_failure_that_is_not_listed_is_raised_on() -> None:
    with pytest.raises(RuntimeError):
        run_ignoring(_refuse_differently, (ValueError,), 0)
""",
        imports="from suppress_expected import run_ignoring\n",
    ),
    hidden_test=_test_module(
        "suppress_expected",
        "The part of the contract the published tests do not state.",
        """
class Narrower(ValueError):
    pass


def _refuse_narrowly():
    raise Narrower("derived from the listed kind")


def test_a_step_that_works_answers_with_its_result() -> None:
    assert run_ignoring(lambda: 7, (ValueError,), 0) == 7


def test_a_failure_derived_from_a_listed_kind_is_swallowed() -> None:
    assert run_ignoring(_refuse_narrowly, (ValueError,), 0) == 0


def test_an_answer_of_nothing_is_the_answer() -> None:
    assert run_ignoring(lambda: None, (ValueError,), 0) is None
""",
        imports="from suppress_expected import run_ignoring\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G079 = D2TaskSpec(
    template_id="d5_boundary.diagonal_read",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-diagonal-read",
    module="diagonal_read",
    module_doc="Reading the leading diagonal off a grid of rows.",
    issue=(
        "diagonal() is documented to read the leading diagonal off a grid. Callers report that "
        "a grid with more rows than columns runs off the end of a row, and that a grid whose "
        "rows are not all the same width is read as though it were rectangular."
    ),
    expected=(
        "diagonal(grid) returns the cells of the leading diagonal in order, stopping at the "
        "shorter of the two sides so a grid taller than it is wide simply runs out, and raises "
        "ValueError when the rows are not all the same width."
    ),
    baseline_reason=(
        "it walks one step per row and indexes that far into each one, which passes the end of "
        "a short row, and it never compares the widths of the rows to each other"
    ),
    edge_cases=(
        "a grid taller than it is wide stops at the shorter side",
        "rows that are not all the same width are refused",
    ),
    baseline='''def diagonal(grid):
    """Return the cells of the leading diagonal of `grid`."""
    return [grid[step][step] for step in range(len(grid))]''',
    variant_one='''def diagonal(grid):
    """Return the cells of the leading diagonal of `grid`."""
    widths = {len(row) for row in grid}
    if len(widths) > 1:
        raise ValueError(f"the rows are of widths {sorted(widths)}")
    reach = min(len(grid), widths.pop()) if grid else 0
    return [grid[step][step] for step in range(reach)]''',
    variant_two='''def diagonal(grid):
    """Return the cells of the leading diagonal of `grid`."""
    cells = []
    width = None
    for step, row in enumerate(grid):
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(f"row {step} is {len(row)} wide, not {width}")
        if step < len(row):
            cells.append(row[step])
    return cells''',
    variant_three='''def diagonal(grid):
    """Return the cells of the leading diagonal of `grid`."""
    reach = min(len(grid), len(grid[0])) if grid else 0
    return [grid[step][step] for step in range(reach)]''',
    variant_four='''def diagonal(grid):
    """Return the cells of the leading diagonal of `grid`."""
    widths = {len(row) for row in grid}
    if len(widths) > 1:
        raise ValueError(f"the rows are of widths {sorted(widths)}")
    return [grid[step][step] for step in range(len(grid))]''',
    visible_test=_test_module(
        "diagonal_read",
        "Published contract for reading a grid's leading diagonal.",
        """
def test_a_square_grid_reads_corner_to_corner() -> None:
    assert diagonal([[1, 2], [3, 4]]) == [1, 4]


def test_a_grid_of_one_cell_is_its_own_diagonal() -> None:
    assert diagonal([[5]]) == [5]
""",
        imports="from diagonal_read import diagonal\n",
    ),
    hidden_test=_test_module(
        "diagonal_read",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_square_grid_reads_corner_to_corner() -> None:
    assert diagonal([[1, 2], [3, 4]]) == [1, 4]


def test_a_grid_taller_than_it_is_wide_stops_at_the_shorter_side() -> None:
    assert diagonal([[1, 2], [3, 4], [5, 6]]) == [1, 4]


def test_rows_of_different_widths_are_refused() -> None:
    with pytest.raises(ValueError):
        diagonal([[1, 2], [3]])
""",
        imports="from diagonal_read import diagonal\n",
    ),
)


_G080 = D2TaskSpec(
    template_id="d5_boundary.increasing_runs",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-increasing-runs",
    module="increasing_runs",
    module_doc="Cutting a series wherever it stops climbing.",
    issue=(
        "runs() is documented to cut a series into the stretches over which it climbs. "
        "Analysts report that a repeated reading is treated as though the series were still "
        "climbing, and that a series with no readings at all raises."
    ),
    expected=(
        "runs(values) returns the series cut into stretches over which each reading is strictly "
        "above the one before it, so a repeat starts a new stretch, and returns no stretches "
        "at all for no readings."
    ),
    baseline_reason=(
        "it keeps a reading in the current stretch when it merely reaches the one before, and "
        "it opens the first stretch from the first reading without checking there is one"
    ),
    edge_cases=(
        "a repeated reading starts a new stretch",
        "no readings at all gives no stretches",
    ),
    baseline='''def runs(values):
    """Return `values` cut into strictly climbing stretches."""
    out = []
    current = [values[0]]
    for previous, value in zip(values, values[1:]):
        if value >= previous:
            current.append(value)
        else:
            out.append(current)
            current = [value]
    out.append(current)
    return out''',
    variant_one='''def runs(values):
    """Return `values` cut into strictly climbing stretches."""
    readings = list(values)
    if not readings:
        return []
    out = [[readings[0]]]
    for previous, value in zip(readings, readings[1:]):
        if value > previous:
            out[-1].append(value)
        else:
            out.append([value])
    return out''',
    variant_two='''def runs(values):
    """Return `values` cut into strictly climbing stretches."""
    readings = list(values)
    cuts = [
        place + 1
        for place, value in enumerate(readings[1:])
        if value <= readings[place]
    ]
    bounds = [0, *cuts, len(readings)]
    return [
        readings[start:stop] for start, stop in zip(bounds, bounds[1:]) if stop > start
    ]''',
    variant_three='''def runs(values):
    """Return `values` cut into strictly climbing stretches."""
    out = []
    current = [values[0]]
    for previous, value in zip(values, values[1:]):
        if value > previous:
            current.append(value)
        else:
            out.append(current)
            current = [value]
    out.append(current)
    return out''',
    variant_four='''def runs(values):
    """Return `values` cut into strictly climbing stretches."""
    readings = list(values)
    if not readings:
        return []
    out = []
    current = [readings[0]]
    for previous, value in zip(readings, readings[1:]):
        if value >= previous:
            current.append(value)
        else:
            out.append(current)
            current = [value]
    out.append(current)
    return out''',
    visible_test=_test_module(
        "increasing_runs",
        "Published contract for cutting a series where it stops climbing.",
        """
def test_a_fall_cuts_the_series() -> None:
    assert runs([1, 2, 1, 3]) == [[1, 2], [1, 3]]


def test_a_single_reading_is_a_stretch_of_its_own() -> None:
    assert runs([5]) == [[5]]
""",
        imports="from increasing_runs import runs\n",
    ),
    hidden_test=_test_module(
        "increasing_runs",
        "The part of the contract the published tests do not state.",
        """
def test_a_fall_cuts_the_series() -> None:
    assert runs([1, 2, 1, 3]) == [[1, 2], [1, 3]]


def test_a_repeated_reading_starts_a_new_stretch() -> None:
    assert runs([1, 1, 2]) == [[1], [1, 2]]


def test_no_readings_at_all_gives_no_stretches() -> None:
    assert runs([]) == []
""",
        imports="from increasing_runs import runs\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G081 = D2TaskSpec(
    template_id="d5_numeric.modular_inverse",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-modular-inverse",
    module="modular_inverse",
    module_doc="Finding the number that multiplies back to one under a modulus.",
    issue=(
        "inverse() is documented to return the number that multiplies `value` back to one "
        "under the modulus. Callers report that a value sharing a factor with the modulus, "
        "which has no inverse at all, comes back with a number anyway, and that the answer is "
        "sometimes negative where the caller wants it inside the modulus."
    ),
    expected=(
        "inverse(value, modulus) returns the number in the range zero up to the modulus that "
        "multiplies `value` back to one under that modulus, and raises ValueError when the "
        "value and the modulus share a factor, because then no such number exists."
    ),
    baseline_reason=(
        "it hands back the coefficient the extended algorithm leaves it with, which can be "
        "negative, and it never looks at the divisor the algorithm arrived at"
    ),
    edge_cases=(
        "a value sharing a factor with the modulus is refused",
        "the answer is brought inside the modulus rather than left negative",
    ),
    baseline='''def inverse(value, modulus):
    """Return the number that multiplies `value` back to one under `modulus`."""
    old_remainder, remainder = value, modulus
    old_factor, factor = 1, 0
    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_factor, factor = factor, old_factor - quotient * factor
    return old_factor''',
    variant_one='''def inverse(value, modulus):
    """Return the number that multiplies `value` back to one under `modulus`."""
    old_remainder, remainder = value, modulus
    old_factor, factor = 1, 0
    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_factor, factor = factor, old_factor - quotient * factor
    if old_remainder != 1:
        raise ValueError(f"{value} and {modulus} share a factor, so there is no inverse")
    return old_factor % modulus''',
    variant_two='''def inverse(value, modulus):
    """Return the number that multiplies `value` back to one under `modulus`."""
    for candidate in range(modulus):
        if value * candidate % modulus == 1:
            return candidate
    raise ValueError(f"{value} and {modulus} share a factor, so there is no inverse")''',
    variant_three='''def inverse(value, modulus):
    """Return the number that multiplies `value` back to one under `modulus`."""
    old_remainder, remainder = value, modulus
    old_factor, factor = 1, 0
    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_factor, factor = factor, old_factor - quotient * factor
    if old_remainder != 1:
        raise ValueError(f"{value} and {modulus} share a factor, so there is no inverse")
    return old_factor''',
    variant_four='''def inverse(value, modulus):
    """Return the number that multiplies `value` back to one under `modulus`."""
    old_remainder, remainder = value, modulus
    old_factor, factor = 1, 0
    while remainder != 0:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_factor, factor = factor, old_factor - quotient * factor
    return old_factor % modulus''',
    visible_test=_test_module(
        "modular_inverse",
        "Published contract for the inverse under a modulus.",
        """
def test_five_inverts_under_seven() -> None:
    assert inverse(5, 7) == 3


def test_three_inverts_under_eleven() -> None:
    assert inverse(3, 11) == 4
""",
        imports="from modular_inverse import inverse\n",
    ),
    hidden_test=_test_module(
        "modular_inverse",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_five_inverts_under_seven() -> None:
    assert inverse(5, 7) == 3


def test_a_shared_factor_means_there_is_no_inverse() -> None:
    with pytest.raises(ValueError):
        inverse(4, 8)


def test_the_answer_is_brought_inside_the_modulus() -> None:
    assert inverse(3, 7) == 5
""",
        imports="from modular_inverse import inverse\n",
    ),
)


_G082 = D2TaskSpec(
    template_id="d5_numeric.business_days",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-business-days",
    module="business_days",
    module_doc="Counting how many working days a stretch of calendar days covers.",
    issue=(
        "working_days() is documented to count the working days in a stretch of calendar days. "
        "Schedulers report that a stretch beginning at the weekend is counted as though the "
        "week never came round again, and that a stretch of negative length comes back with a "
        "negative count instead of being refused."
    ),
    expected=(
        "working_days(start_weekday, total_days) returns how many of the days are working "
        "days, counting Monday as weekday zero and treating weekdays five and six as the "
        "weekend, wrapping round the week as many times as the stretch runs, and raises "
        "ValueError for a stretch shorter than nothing."
    ),
    baseline_reason=(
        "it counts the days left over after the whole weeks by adding the offset to the "
        "starting weekday without bringing it back round the week, and it never checks the "
        "stretch is not negative"
    ),
    edge_cases=(
        "the days left over wrap round the week",
        "a stretch shorter than nothing is refused",
    ),
    baseline='''def working_days(start_weekday, total_days):
    """Return how many working days a stretch of `total_days` covers."""
    weeks, left_over = divmod(total_days, 7)
    count = weeks * 5
    for offset in range(left_over):
        if start_weekday + offset < 5:
            count += 1
    return count''',
    variant_one='''def working_days(start_weekday, total_days):
    """Return how many working days a stretch of `total_days` covers."""
    if total_days < 0:
        raise ValueError(f"a stretch cannot run for {total_days} days")
    weeks, left_over = divmod(total_days, 7)
    count = weeks * 5
    for offset in range(left_over):
        if (start_weekday + offset) % 7 < 5:
            count += 1
    return count''',
    variant_two='''def working_days(start_weekday, total_days):
    """Return how many working days a stretch of `total_days` covers."""
    if total_days < 0:
        raise ValueError(f"a stretch cannot run for {total_days} days")
    return sum(
        1 for offset in range(total_days) if (start_weekday + offset) % 7 not in (5, 6)
    )''',
    variant_three='''def working_days(start_weekday, total_days):
    """Return how many working days a stretch of `total_days` covers."""
    weeks, left_over = divmod(total_days, 7)
    count = weeks * 5
    for offset in range(left_over):
        if (start_weekday + offset) % 7 < 5:
            count += 1
    return count''',
    variant_four='''def working_days(start_weekday, total_days):
    """Return how many working days a stretch of `total_days` covers."""
    if total_days < 0:
        raise ValueError(f"a stretch cannot run for {total_days} days")
    weeks, left_over = divmod(total_days, 7)
    count = weeks * 5
    for offset in range(left_over):
        if start_weekday + offset < 5:
            count += 1
    return count''',
    visible_test=_test_module(
        "business_days",
        "Published contract for counting working days.",
        """
def test_a_working_week_from_monday() -> None:
    assert working_days(0, 5) == 5


def test_a_whole_week_from_monday_is_five_working_days() -> None:
    assert working_days(0, 7) == 5


def test_two_whole_weeks_from_monday() -> None:
    assert working_days(0, 14) == 10
""",
        imports="from business_days import working_days\n",
    ),
    hidden_test=_test_module(
        "business_days",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_working_week_from_monday() -> None:
    assert working_days(0, 5) == 5


def test_a_stretch_beginning_at_the_weekend_wraps_round() -> None:
    assert working_days(5, 3) == 1


def test_a_stretch_shorter_than_nothing_is_refused() -> None:
    with pytest.raises(ValueError):
        working_days(0, -1)
""",
        imports="from business_days import working_days\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G083 = D2TaskSpec(
    template_id="d5_parsing.email_parts",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-email-parts",
    module="email_parts",
    module_doc="Splitting an address into the part before the at sign and the part after.",
    issue=(
        "split_address() is documented to split an address into its two parts. Callers report "
        "that an address carrying more than one at sign, or none at all, is split anyway "
        "instead of being refused, and that the part before the at sign comes back flattened "
        "to lowercase even though it is case-sensitive."
    ),
    expected=(
        "split_address(text) returns (local, domain). The domain is lowercased because it is "
        "case-insensitive, the local part keeps the case it was written in, and an address "
        "that does not carry exactly one at sign is refused with ValueError."
    ),
    baseline_reason=(
        "it splits at the first at sign whatever else the address holds, and it lowercases "
        "both halves rather than only the domain"
    ),
    edge_cases=(
        "an address without exactly one at sign is refused",
        "the local part keeps the case it was written in",
    ),
    baseline='''def split_address(text):
    """Return (local, domain) for the address `text`."""
    local, _, domain = text.partition("@")
    return local.lower(), domain.lower()''',
    variant_one='''def split_address(text):
    """Return (local, domain) for the address `text`."""
    if text.count("@") != 1:
        raise ValueError(f"{text!r} does not carry exactly one at sign")
    local, _, domain = text.partition("@")
    return local, domain.lower()''',
    variant_two='''def split_address(text):
    """Return (local, domain) for the address `text`."""
    parts = text.split("@")
    if len(parts) != 2:
        raise ValueError(f"{text!r} does not carry exactly one at sign")
    return parts[0], parts[1].lower()''',
    variant_three='''def split_address(text):
    """Return (local, domain) for the address `text`."""
    if text.count("@") != 1:
        raise ValueError(f"{text!r} does not carry exactly one at sign")
    local, _, domain = text.partition("@")
    return local.lower(), domain.lower()''',
    variant_four='''def split_address(text):
    """Return (local, domain) for the address `text`."""
    local, _, domain = text.partition("@")
    return local, domain.lower()''',
    visible_test=_test_module(
        "email_parts",
        "Published contract for splitting an address.",
        """
def test_an_ordinary_address_splits_in_two() -> None:
    assert split_address("ada@example.com") == ("ada", "example.com")


def test_the_domain_is_lowercased() -> None:
    assert split_address("ada@Example.COM") == ("ada", "example.com")
""",
        imports="from email_parts import split_address\n",
    ),
    hidden_test=_test_module(
        "email_parts",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_an_ordinary_address_splits_in_two() -> None:
    assert split_address("ada@example.com") == ("ada", "example.com")


def test_an_address_without_exactly_one_at_sign_is_refused() -> None:
    with pytest.raises(ValueError):
        split_address("a@b@c")
    with pytest.raises(ValueError):
        split_address("nobody")


def test_the_local_part_keeps_its_case() -> None:
    assert split_address("Ada@example.com") == ("Ada", "example.com")
""",
        imports="from email_parts import split_address\n",
    ),
)


_G084 = D2TaskSpec(
    template_id="d5_parsing.wildcard_host",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-wildcard-host",
    module="wildcard_host",
    module_doc="Deciding whether a hostname is covered by a wildcard certificate pattern.",
    issue=(
        "matches() is documented to say whether a hostname is covered by a wildcard pattern. "
        "Security report that a pattern covering one level is matched by a host buried several "
        "levels deeper, and that a host written in capitals is not matched at all even though "
        "hostnames do not care about case."
    ),
    expected=(
        "matches(pattern, host) says whether the host is covered by the pattern. A leading "
        "'*.' stands for exactly one label, so a host with further labels in front of the "
        "matched one is not covered, and the comparison ignores case on both sides."
    ),
    baseline_reason=(
        "it asks only whether the host ends with the rest of the pattern, which any depth of "
        "label satisfies, and it compares the two exactly as written"
    ),
    edge_cases=(
        "a wildcard stands for exactly one label, not several",
        "the comparison ignores case on both sides",
    ),
    baseline='''def matches(pattern, host):
    """Say whether `host` is covered by `pattern`."""
    if pattern.startswith("*."):
        return host.endswith(pattern[1:])
    return host == pattern''',
    variant_one='''def matches(pattern, host):
    """Say whether `host` is covered by `pattern`."""
    wanted = pattern.lower()
    given = host.lower()
    if not wanted.startswith("*."):
        return given == wanted
    labels = given.split(".")
    return len(labels) == len(wanted.split(".")) and labels[1:] == wanted.split(".")[1:]''',
    variant_two='''def matches(pattern, host):
    """Say whether `host` is covered by `pattern`."""
    wanted = pattern.lower().split(".")
    given = host.lower().split(".")
    if len(wanted) != len(given):
        return False
    return all(
        piece == "*" or piece == label for piece, label in zip(wanted, given)
    )''',
    variant_three='''def matches(pattern, host):
    """Say whether `host` is covered by `pattern`."""
    if not pattern.startswith("*."):
        return host == pattern
    labels = host.split(".")
    return len(labels) == len(pattern.split(".")) and labels[1:] == pattern.split(".")[1:]''',
    variant_four='''def matches(pattern, host):
    """Say whether `host` is covered by `pattern`."""
    wanted = pattern.lower()
    given = host.lower()
    if wanted.startswith("*."):
        return given.endswith(wanted[1:])
    return given == wanted''',
    visible_test=_test_module(
        "wildcard_host",
        "Published contract for matching a host against a wildcard pattern.",
        """
def test_one_label_under_the_wildcard_matches() -> None:
    assert matches("*.example.com", "a.example.com") is True


def test_a_different_domain_does_not_match() -> None:
    assert matches("*.example.com", "a.other.com") is False


def test_a_pattern_with_no_wildcard_matches_only_itself() -> None:
    assert matches("example.com", "example.com") is True
""",
        imports="from wildcard_host import matches\n",
    ),
    hidden_test=_test_module(
        "wildcard_host",
        "The part of the contract the published tests do not state.",
        """
def test_one_label_under_the_wildcard_matches() -> None:
    assert matches("*.example.com", "a.example.com") is True


def test_a_wildcard_stands_for_exactly_one_label() -> None:
    assert matches("*.example.com", "a.b.example.com") is False


def test_the_comparison_ignores_case() -> None:
    assert matches("*.EXAMPLE.com", "a.example.COM") is True
""",
        imports="from wildcard_host import matches\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G085 = D2TaskSpec(
    template_id="d5_transform.fixed_width",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-fixed-width",
    module="fixed_width",
    module_doc="Laying records out as fixed-width lines for a system that counts columns.",
    issue=(
        "render() is documented to lay records out in columns of a fixed width. The receiving "
        "system reports that a value longer than its column pushes every column after it out "
        "of place, and that a record simply missing one of the fields brings the whole render "
        "down with a KeyError."
    ),
    expected=(
        "render(records, columns) returns one line per record, each field padded on the right "
        "to its declared width, a value longer than its column cut down to that width so the "
        "line never grows, and a field the record does not carry rendered as blanks."
    ),
    baseline_reason=(
        "it pads a value up to the width but never cuts one down, and it reaches for each "
        "field without checking the record carries it"
    ),
    edge_cases=(
        "a value longer than its column is cut down to the width",
        "a field the record does not carry is rendered as blanks",
    ),
    baseline='''def render(records, columns):
    """Return one fixed-width line per record."""
    lines = []
    for record in records:
        lines.append("".join(str(record[field]).ljust(width) for field, width in columns))
    return lines''',
    variant_one='''def render(records, columns):
    """Return one fixed-width line per record."""
    lines = []
    for record in records:
        cells = []
        for field, width in columns:
            text = str(record[field]) if field in record else ""
            cells.append(text[:width].ljust(width))
        lines.append("".join(cells))
    return lines''',
    variant_two='''def render(records, columns):
    """Return one fixed-width line per record."""
    return [
        "".join(
            f"{str(record.get(field, '')):<{width}}"[:width] for field, width in columns
        )
        for record in records
    ]''',
    variant_three='''def render(records, columns):
    """Return one fixed-width line per record."""
    lines = []
    for record in records:
        lines.append(
            "".join(str(record[field])[:width].ljust(width) for field, width in columns)
        )
    return lines''',
    variant_four='''def render(records, columns):
    """Return one fixed-width line per record."""
    lines = []
    for record in records:
        cells = []
        for field, width in columns:
            text = str(record[field]) if field in record else ""
            cells.append(text.ljust(width))
        lines.append("".join(cells))
    return lines''',
    visible_test=_test_module(
        "fixed_width",
        "Published contract for laying records out in fixed columns.",
        """
def test_each_field_is_padded_to_its_column() -> None:
    assert render([{"a": "x", "b": "yy"}], [("a", 3), ("b", 4)]) == ["x  yy  "]


def test_no_records_renders_no_lines() -> None:
    assert render([], [("a", 3)]) == []
""",
        imports="from fixed_width import render\n",
    ),
    hidden_test=_test_module(
        "fixed_width",
        "The part of the contract the published tests do not state.",
        """
def test_each_field_is_padded_to_its_column() -> None:
    assert render([{"a": "x", "b": "yy"}], [("a", 3), ("b", 4)]) == ["x  yy  "]


def test_a_value_longer_than_its_column_is_cut_down() -> None:
    assert render([{"a": "toolong"}], [("a", 3)]) == ["too"]


def test_a_field_the_record_does_not_carry_is_blanks() -> None:
    assert render([{}], [("a", 3)]) == ["   "]
""",
        imports="from fixed_width import render\n",
    ),
)


_G086 = D2TaskSpec(
    template_id="d5_transform.page_cursor",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-page-cursor",
    module="page_cursor",
    module_doc="Handing out one page of results together with where to carry on from.",
    issue=(
        "page() is documented to hand out one page and where to carry on from. Clients report "
        "that the last page comes back with a place to carry on from that is past the end, so "
        "they ask for a page that does not exist, and that a cursor below zero quietly reads "
        "backwards from the end instead of being refused."
    ),
    expected=(
        "page(records, cursor, size) returns (rows, next_cursor). Rows are the records from "
        "`cursor` onwards, at most `size` of them, next_cursor is where the following page "
        "begins or None when this page reached the end, and a cursor below zero is refused "
        "with ValueError."
    ),
    baseline_reason=(
        "it always hands back the cursor advanced by the page size, even off the end, and it "
        "slices with the cursor as given, which reads from the far end when it is negative"
    ),
    edge_cases=(
        "the last page carries on from nowhere",
        "a cursor below zero is refused",
    ),
    baseline='''def page(records, cursor, size):
    """Return one page of `records` and where to carry on from."""
    rows = records[cursor : cursor + size]
    return rows, cursor + size''',
    variant_one='''def page(records, cursor, size):
    """Return one page of `records` and where to carry on from."""
    if cursor < 0:
        raise ValueError(f"a cursor cannot be {cursor}")
    rows = records[cursor : cursor + size]
    following = cursor + size
    return rows, following if following < len(records) else None''',
    variant_two='''def page(records, cursor, size):
    """Return one page of `records` and where to carry on from."""
    if cursor < 0:
        raise ValueError(f"a cursor cannot be {cursor}")
    remaining = len(records) - cursor - size
    rows = records[cursor : cursor + size]
    return rows, None if remaining <= 0 else cursor + size''',
    variant_three='''def page(records, cursor, size):
    """Return one page of `records` and where to carry on from."""
    rows = records[cursor : cursor + size]
    following = cursor + size
    return rows, following if following < len(records) else None''',
    variant_four='''def page(records, cursor, size):
    """Return one page of `records` and where to carry on from."""
    if cursor < 0:
        raise ValueError(f"a cursor cannot be {cursor}")
    rows = records[cursor : cursor + size]
    return rows, cursor + size''',
    visible_test=_test_module(
        "page_cursor",
        "Published contract for handing out one page of results.",
        """
def test_the_first_page_carries_on_from_the_page_size() -> None:
    assert page(["a", "b", "c", "d", "e"], 0, 2) == (["a", "b"], 2)


def test_a_page_from_the_middle_carries_on_after_it() -> None:
    assert page(["a", "b", "c", "d", "e"], 1, 2) == (["b", "c"], 3)
""",
        imports="from page_cursor import page\n",
    ),
    hidden_test=_test_module(
        "page_cursor",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_page_carries_on_from_the_page_size() -> None:
    assert page(["a", "b", "c", "d", "e"], 0, 2) == (["a", "b"], 2)


def test_the_last_page_carries_on_from_nowhere() -> None:
    assert page(["a", "b", "c"], 2, 2) == (["c"], None)


def test_a_cursor_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        page(["a", "b", "c"], -1, 2)
""",
        imports="from page_cursor import page\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G087 = D2TaskSpec(
    template_id="d5_state.shelf_slots",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-shelf-slots",
    module="shelf_slots",
    module_doc="Giving an item a numbered place, reusing the ones that have been given up.",
    issue=(
        "assign() is documented to give an item the lowest free numbered place. Storekeepers "
        "report that an item already on the shelf is given a second place of its own, and that "
        "a place given up in the middle is never reused, so the numbering climbs for ever."
    ),
    expected=(
        "assign(slots, item) returns (number, slots) with the item in the lowest free place, "
        "numbering from one. An item already on the shelf keeps the place it has, and a place "
        "given up earlier is filled before a new one is opened."
    ),
    baseline_reason=(
        "it opens a place one above the highest in use whatever else is going on, without "
        "looking for the item or for a gap below"
    ),
    edge_cases=(
        "an item already on the shelf keeps the place it has",
        "a place given up earlier is filled before a new one is opened",
    ),
    baseline='''def assign(slots, item):
    """Return (number, slots) with `item` in the lowest free place."""
    number = max(slots, default=0) + 1
    return number, {**slots, number: item}''',
    variant_one='''def assign(slots, item):
    """Return (number, slots) with `item` in the lowest free place."""
    for number, held in slots.items():
        if held == item:
            return number, dict(slots)
    number = 1
    while number in slots:
        number += 1
    return number, {**slots, number: item}''',
    variant_two='''def assign(slots, item):
    """Return (number, slots) with `item` in the lowest free place."""
    held = {value: number for number, value in slots.items()}
    if item in held:
        return held[item], dict(slots)
    taken = set(slots)
    number = next(place for place in range(1, len(taken) + 2) if place not in taken)
    return number, {**slots, number: item}''',
    variant_three='''def assign(slots, item):
    """Return (number, slots) with `item` in the lowest free place."""
    for number, held in slots.items():
        if held == item:
            return number, dict(slots)
    number = max(slots, default=0) + 1
    return number, {**slots, number: item}''',
    variant_four='''def assign(slots, item):
    """Return (number, slots) with `item` in the lowest free place."""
    number = 1
    while number in slots:
        number += 1
    return number, {**slots, number: item}''',
    visible_test=_test_module(
        "shelf_slots",
        "Published contract for giving an item a numbered place.",
        """
def test_the_first_item_takes_the_first_place() -> None:
    assert assign({}, "a") == (1, {1: "a"})


def test_the_next_item_takes_the_place_after() -> None:
    assert assign({1: "a"}, "b") == (2, {1: "a", 2: "b"})
""",
        imports="from shelf_slots import assign\n",
    ),
    hidden_test=_test_module(
        "shelf_slots",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_item_takes_the_first_place() -> None:
    assert assign({}, "a") == (1, {1: "a"})


def test_an_item_already_on_the_shelf_keeps_its_place() -> None:
    assert assign({1: "a", 2: "b"}, "a") == (1, {1: "a", 2: "b"})


def test_a_place_given_up_earlier_is_filled_first() -> None:
    assert assign({2: "b"}, "c") == (1, {1: "c", 2: "b"})
""",
        imports="from shelf_slots import assign\n",
    ),
)


_G088 = D2TaskSpec(
    template_id="d5_state.upsert_version",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-upsert-version",
    module="upsert_version",
    module_doc="Writing a record only when the writer knows the version it is replacing.",
    issue=(
        "upsert() is documented to accept a write only when it follows the stored version. "
        "Callers report that a write resent after a timeout, carrying the same version and the "
        "same value, is refused as a conflict even though it is the write that already landed, "
        "and that a write skipping several versions is accepted as though nothing were missing."
    ),
    expected=(
        "upsert(store, key, version, value) returns the store with the record written when the "
        "version is exactly one above the stored one, or one for a key nobody has written yet. "
        "A write repeating the stored version with the same value is the write that already "
        "landed and changes nothing, and anything else is refused with ValueError."
    ),
    baseline_reason=(
        "it refuses any version at or below the stored one without looking at whether the "
        "value is the one already stored, and it accepts any version above it however far"
    ),
    edge_cases=(
        "a write repeating the stored version with the same value changes nothing",
        "a write skipping a version is refused",
    ),
    baseline='''def upsert(store, key, version, value):
    """Return `store` with `key` written at `version`."""
    current = store.get(key)
    if current is not None and version <= current["version"]:
        raise ValueError(f"{key!r} is already at version {current['version']}")
    updated = dict(store)
    updated[key] = {"version": version, "value": value}
    return updated''',
    variant_one='''def upsert(store, key, version, value):
    """Return `store` with `key` written at `version`."""
    current = store.get(key)
    stored = 0 if current is None else current["version"]
    if current is not None and version == stored and current["value"] == value:
        return dict(store)
    if version != stored + 1:
        raise ValueError(f"{key!r} is at version {stored}, not ready for {version}")
    updated = dict(store)
    updated[key] = {"version": version, "value": value}
    return updated''',
    variant_two='''def upsert(store, key, version, value):
    """Return `store` with `key` written at `version`."""
    written = {"version": version, "value": value}
    current = store.get(key)
    if current == written:
        return dict(store)
    stored = 0 if current is None else current["version"]
    if version - stored != 1:
        raise ValueError(f"{key!r} is at version {stored}, not ready for {version}")
    return {**store, key: written}''',
    variant_three='''def upsert(store, key, version, value):
    """Return `store` with `key` written at `version`."""
    current = store.get(key)
    if current is not None and version <= current["version"]:
        if current["value"] == value and version == current["version"]:
            return dict(store)
        raise ValueError(f"{key!r} is already at version {current['version']}")
    updated = dict(store)
    updated[key] = {"version": version, "value": value}
    return updated''',
    variant_four='''def upsert(store, key, version, value):
    """Return `store` with `key` written at `version`."""
    current = store.get(key)
    stored = 0 if current is None else current["version"]
    if version != stored + 1:
        raise ValueError(f"{key!r} is at version {stored}, not ready for {version}")
    updated = dict(store)
    updated[key] = {"version": version, "value": value}
    return updated''',
    visible_test=_test_module(
        "upsert_version",
        "Published contract for writing a record at a known version.",
        """
import pytest


def test_a_key_nobody_has_written_starts_at_one() -> None:
    assert upsert({}, "a", 1, "x") == {"a": {"version": 1, "value": "x"}}


def test_the_next_version_replaces_the_stored_one() -> None:
    store = {"a": {"version": 1, "value": "x"}}
    assert upsert(store, "a", 2, "y") == {"a": {"version": 2, "value": "y"}}


def test_repeating_the_stored_version_with_a_different_value_is_refused() -> None:
    store = {"a": {"version": 2, "value": "y"}}
    with pytest.raises(ValueError):
        upsert(store, "a", 2, "different")
""",
        imports="from upsert_version import upsert\n",
    ),
    hidden_test=_test_module(
        "upsert_version",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_key_nobody_has_written_starts_at_one() -> None:
    assert upsert({}, "a", 1, "x") == {"a": {"version": 1, "value": "x"}}


def test_the_write_that_already_landed_changes_nothing() -> None:
    store = {"a": {"version": 2, "value": "y"}}
    assert upsert(store, "a", 2, "y") == {"a": {"version": 2, "value": "y"}}


def test_a_write_skipping_a_version_is_refused() -> None:
    store = {"a": {"version": 1, "value": "x"}}
    with pytest.raises(ValueError):
        upsert(store, "a", 5, "z")
""",
        imports="from upsert_version import upsert\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G089 = D2TaskSpec(
    template_id="d5_error.short_circuit",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-short-circuit",
    module="short_circuit",
    module_doc="Running the checks in order and stopping at the first one that objects.",
    issue=(
        "first_failure() is documented to stop at the first check that objects. Callers report "
        "that every check runs anyway, so an expensive check runs even after a cheap one has "
        "already ruled the value out, and that a check which raises brings the whole run down "
        "instead of counting as an objection."
    ),
    expected=(
        "first_failure(checks, value) runs the named checks in order and returns (name, "
        "message) for the first one that objects, running none of the checks after it, and "
        "returns None when they all pass. A check that raises counts as an objection whose "
        "message is the text of what it raised."
    ),
    baseline_reason=(
        "it runs every check and picks the first objection afterwards, and it lets a check "
        "that raises escape rather than reading it as an objection"
    ),
    edge_cases=(
        "no check after the first objection is run",
        "a check that raises counts as an objection",
    ),
    baseline='''def first_failure(checks, value):
    """Return (name, message) for the first check that objects to `value`."""
    objections = []
    for name, check in checks:
        message = check(value)
        if message:
            objections.append((name, message))
    return objections[0] if objections else None''',
    variant_one='''def first_failure(checks, value):
    """Return (name, message) for the first check that objects to `value`."""
    for name, check in checks:
        try:
            message = check(value)
        except Exception as error:
            return name, str(error)
        if message:
            return name, message
    return None''',
    variant_two='''def first_failure(checks, value):
    """Return (name, message) for the first check that objects to `value`."""

    def look(name, check):
        try:
            return name, check(value)
        except Exception as error:
            return name, str(error)

    reported = (look(name, check) for name, check in checks)
    return next((report for report in reported if report[1]), None)''',
    variant_three='''def first_failure(checks, value):
    """Return (name, message) for the first check that objects to `value`."""
    for name, check in checks:
        message = check(value)
        if message:
            return name, message
    return None''',
    variant_four='''def first_failure(checks, value):
    """Return (name, message) for the first check that objects to `value`."""
    objections = []
    for name, check in checks:
        try:
            message = check(value)
        except Exception as error:
            message = str(error)
        if message:
            objections.append((name, message))
    return objections[0] if objections else None''',
    visible_test=_test_module(
        "short_circuit",
        "Published contract for running checks in order.",
        """
def test_checks_that_all_pass_report_nothing() -> None:
    checks = [("a", lambda value: None), ("b", lambda value: None)]
    assert first_failure(checks, 1) is None


def test_the_objection_is_reported_with_its_name() -> None:
    checks = [("a", lambda value: None), ("b", lambda value: "too big")]
    assert first_failure(checks, 1) == ("b", "too big")
""",
        imports="from short_circuit import first_failure\n",
    ),
    hidden_test=_test_module(
        "short_circuit",
        "The part of the contract the published tests do not state.",
        """
def _explode(value):
    raise RuntimeError("the check itself broke")


def test_checks_that_all_pass_report_nothing() -> None:
    checks = [("a", lambda value: None), ("b", lambda value: None)]
    assert first_failure(checks, 1) is None


def test_no_check_after_the_first_objection_is_run() -> None:
    ran = []

    def later(value):
        ran.append("later")
        return None

    checks = [("a", lambda value: "no"), ("b", later)]
    assert first_failure(checks, 1) == ("a", "no")
    assert ran == []


def test_a_check_that_raises_counts_as_an_objection() -> None:
    assert first_failure([("a", _explode)], 1) == ("a", "the check itself broke")
""",
        imports="from short_circuit import first_failure\n",
    ),
)


_G090 = D2TaskSpec(
    template_id="d5_error.guard_argument_types",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-guard-argument-types",
    module="guard_argument_types",
    module_doc="Refusing a call whose arguments are not the kinds the handler expects.",
    issue=(
        "check_types() is documented to refuse a call whose arguments are the wrong kind. "
        "Callers report that a True or False slips through where a whole number is expected, "
        "because a boolean counts as one, and that an argument the caller simply left out "
        "fails with a KeyError instead of the TypeError the handler catches."
    ),
    expected=(
        "check_types(values, expected) returns the values when each named argument is of the "
        "kind expected. A boolean does not count as a whole number, an argument the caller did "
        "not supply is as wrong as one of the wrong kind, and either is refused with TypeError."
    ),
    baseline_reason=(
        "it asks whether the value is an instance of the kind, which a boolean satisfies for a "
        "whole number, and it reaches for each name without checking it was supplied"
    ),
    edge_cases=(
        "a boolean does not count as a whole number",
        "an argument that was not supplied is refused with TypeError",
    ),
    baseline='''def check_types(values, expected):
    """Return `values` when each named argument is of the kind expected."""
    for name, kind in expected.items():
        if not isinstance(values[name], kind):
            raise TypeError(f"{name} should be {kind.__name__}")
    return values''',
    variant_one='''def check_types(values, expected):
    """Return `values` when each named argument is of the kind expected."""
    for name, kind in expected.items():
        if name not in values:
            raise TypeError(f"{name} was not supplied")
        given = values[name]
        if kind is int and isinstance(given, bool):
            raise TypeError(f"{name} should be {kind.__name__}, not a boolean")
        if not isinstance(given, kind):
            raise TypeError(f"{name} should be {kind.__name__}")
    return values''',
    variant_two='''def check_types(values, expected):
    """Return `values` when each named argument is of the kind expected."""
    absent = sorted(name for name in expected if name not in values)
    if absent:
        raise TypeError(f"not supplied: {absent}")
    wrong = sorted(
        name
        for name, kind in expected.items()
        if type(values[name]) is not kind and not isinstance(values[name], kind)
        or (kind is int and type(values[name]) is bool)
    )
    if wrong:
        raise TypeError(f"wrong kind: {wrong}")
    return values''',
    variant_three='''def check_types(values, expected):
    """Return `values` when each named argument is of the kind expected."""
    for name, kind in expected.items():
        given = values[name]
        if kind is int and isinstance(given, bool):
            raise TypeError(f"{name} should be {kind.__name__}, not a boolean")
        if not isinstance(given, kind):
            raise TypeError(f"{name} should be {kind.__name__}")
    return values''',
    variant_four='''def check_types(values, expected):
    """Return `values` when each named argument is of the kind expected."""
    for name, kind in expected.items():
        if name not in values:
            raise TypeError(f"{name} was not supplied")
        if not isinstance(values[name], kind):
            raise TypeError(f"{name} should be {kind.__name__}")
    return values''',
    visible_test=_test_module(
        "guard_argument_types",
        "Published contract for refusing arguments of the wrong kind.",
        """
import pytest


def test_arguments_of_the_right_kinds_come_back() -> None:
    assert check_types({"a": 1, "b": "x"}, {"a": int, "b": str}) == {"a": 1, "b": "x"}


def test_an_argument_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(TypeError):
        check_types({"a": "x"}, {"a": int})
""",
        imports="from guard_argument_types import check_types\n",
    ),
    hidden_test=_test_module(
        "guard_argument_types",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_arguments_of_the_right_kinds_come_back() -> None:
    assert check_types({"a": 1, "b": "x"}, {"a": int, "b": str}) == {"a": 1, "b": "x"}


def test_a_boolean_does_not_count_as_a_whole_number() -> None:
    with pytest.raises(TypeError):
        check_types({"a": True}, {"a": int})


def test_an_argument_that_was_not_supplied_is_refused() -> None:
    with pytest.raises(TypeError):
        check_types({}, {"a": int})
""",
        imports="from guard_argument_types import check_types\n",
    ),
)

# ------------------------------------------------------------------ boundary and collections

_G091 = D2TaskSpec(
    template_id="d5_boundary.zigzag_rows",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-zigzag-rows",
    module="zigzag_rows",
    module_doc="Dealing items into rows that turn back on themselves at each end.",
    issue=(
        "zigzag() is documented to deal items into rows that turn back at each end, so the "
        "outer rows are reached half as often as the inner ones. Callers report that the deal "
        "wraps straight round from the last row to the first instead of turning back, and that "
        "asking for no rows at all fails with a division error rather than being refused."
    ),
    expected=(
        "zigzag(items, rows) deals the items into `rows` rows, running down to the last row "
        "and then back up to the first and so on, and raises ValueError for fewer than one row."
    ),
    baseline_reason=(
        "it places each item by its position taken round the row count, which wraps from the "
        "bottom back to the top instead of turning back, and dividing by no rows at all fails "
        "on its own terms"
    ),
    edge_cases=(
        "the deal turns back at the last row rather than wrapping round",
        "fewer than one row is refused",
    ),
    baseline='''def zigzag(items, rows):
    """Deal `items` into `rows` rows, turning back at each end."""
    return [
        [item for place, item in enumerate(items) if place % rows == row]
        for row in range(rows)
    ]''',
    variant_one='''def zigzag(items, rows):
    """Deal `items` into `rows` rows, turning back at each end."""
    if rows < 1:
        raise ValueError(f"cannot deal into {rows} rows")
    lines = [[] for _ in range(rows)]
    row, step = 0, 1
    for item in items:
        lines[row].append(item)
        if rows > 1:
            if row + step < 0 or row + step >= rows:
                step = -step
            row += step
    return lines''',
    variant_two='''def zigzag(items, rows):
    """Deal `items` into `rows` rows, turning back at each end."""
    if rows < 1:
        raise ValueError(f"cannot deal into {rows} rows")
    lines = [[] for _ in range(rows)]
    cycle = 1 if rows == 1 else 2 * rows - 2
    for place, item in enumerate(items):
        within = place % cycle
        lines[within if within < rows else cycle - within].append(item)
    return lines''',
    variant_three='''def zigzag(items, rows):
    """Deal `items` into `rows` rows, turning back at each end."""
    lines = [[] for _ in range(rows)]
    cycle = 1 if rows == 1 else 2 * rows - 2
    for place, item in enumerate(items):
        within = place % cycle
        lines[within if within < rows else cycle - within].append(item)
    return lines''',
    variant_four='''def zigzag(items, rows):
    """Deal `items` into `rows` rows, turning back at each end."""
    if rows < 1:
        raise ValueError(f"cannot deal into {rows} rows")
    return [
        [item for place, item in enumerate(items) if place % rows == row]
        for row in range(rows)
    ]''',
    visible_test=_test_module(
        "zigzag_rows",
        "Published contract for dealing items into turning rows.",
        """
def test_two_rows_take_alternate_items() -> None:
    assert zigzag(["a", "b", "c", "d"], 2) == [["a", "c"], ["b", "d"]]


def test_one_row_takes_everything() -> None:
    assert zigzag(["a", "b"], 1) == [["a", "b"]]
""",
        imports="from zigzag_rows import zigzag\n",
    ),
    hidden_test=_test_module(
        "zigzag_rows",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_rows_take_alternate_items() -> None:
    assert zigzag(["a", "b", "c", "d"], 2) == [["a", "c"], ["b", "d"]]


def test_the_deal_turns_back_at_the_last_row() -> None:
    assert zigzag(["a", "b", "c", "d", "e"], 3) == [["a", "e"], ["b", "d"], ["c"]]


def test_fewer_than_one_row_is_refused() -> None:
    with pytest.raises(ValueError):
        zigzag(["a"], 0)
""",
        imports="from zigzag_rows import zigzag\n",
    ),
)


_G092 = D2TaskSpec(
    template_id="d5_boundary.first_duplicate",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d5-boundary-first-duplicate",
    module="first_duplicate",
    module_doc="Finding the point at which a stream first repeats itself.",
    issue=(
        "first_duplicate() is documented to report the entry whose repeat comes earliest. "
        "Callers report that it names the earliest entry that repeats anywhere rather than the "
        "one whose repeat arrives first, and that a stream with no repeat at all raises "
        "instead of reporting nothing."
    ),
    expected=(
        "first_duplicate(items) returns the entry whose second appearance is earliest in the "
        "stream, which is not always the earliest entry that repeats, and returns None when "
        "nothing repeats."
    ),
    baseline_reason=(
        "it walks the stream and names the first entry that appears more than once anywhere, "
        "which reads the earliest repeating entry rather than the earliest repeat, and it "
        "raises when nothing repeats"
    ),
    edge_cases=(
        "the entry named is the one whose second appearance is earliest",
        "a stream with no repeat reports nothing",
    ),
    baseline='''def first_duplicate(items):
    """Return the entry whose second appearance is earliest in `items`."""
    entries = list(items)
    for item in entries:
        if entries.count(item) > 1:
            return item
    raise ValueError("nothing repeats")''',
    variant_one='''def first_duplicate(items):
    """Return the entry whose second appearance is earliest in `items`."""
    seen = []
    for item in items:
        if item in seen:
            return item
        seen.append(item)
    return None''',
    variant_two='''def first_duplicate(items):
    """Return the entry whose second appearance is earliest in `items`."""
    entries = list(items)
    seconds = {}
    for place, item in enumerate(entries):
        if item in seconds:
            continue
        if entries[:place].count(item):
            seconds[item] = place
    if not seconds:
        return None
    return min(seconds, key=lambda item: seconds[item])''',
    variant_three='''def first_duplicate(items):
    """Return the entry whose second appearance is earliest in `items`."""
    seen = []
    for item in items:
        if item in seen:
            return item
        seen.append(item)
    raise ValueError("nothing repeats")''',
    variant_four='''def first_duplicate(items):
    """Return the entry whose second appearance is earliest in `items`."""
    entries = list(items)
    for item in entries:
        if entries.count(item) > 1:
            return item
    return None''',
    visible_test=_test_module(
        "first_duplicate",
        "Published contract for finding where a stream repeats.",
        """
def test_an_entry_repeated_at_the_end_is_named() -> None:
    assert first_duplicate(["a", "b", "a"]) == "a"


def test_an_adjacent_repeat_is_named() -> None:
    assert first_duplicate(["a", "b", "b"]) == "b"
""",
        imports="from first_duplicate import first_duplicate\n",
    ),
    hidden_test=_test_module(
        "first_duplicate",
        "The part of the contract the published tests do not state.",
        """
def test_an_entry_repeated_at_the_end_is_named() -> None:
    assert first_duplicate(["a", "b", "a"]) == "a"


def test_the_earliest_repeat_wins_over_the_earliest_repeater() -> None:
    assert first_duplicate(["a", "b", "b", "a"]) == "b"


def test_a_stream_with_no_repeat_reports_nothing() -> None:
    assert first_duplicate(["a", "b"]) is None
""",
        imports="from first_duplicate import first_duplicate\n",
    ),
)

# ---------------------------------------------------------------------------- numeric logic

_G093 = D2TaskSpec(
    template_id="d5_numeric.scientific_mantissa",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-scientific-mantissa",
    module="scientific_mantissa",
    module_doc="Splitting a measurement into the digits and the power of ten they sit on.",
    issue=(
        "to_mantissa() is documented to split a measurement into its digits and the power of "
        "ten they sit on. Instrument code reports that a reading of exactly zero fails with a "
        "maths domain error, and that a reading below zero fails the same way instead of "
        "keeping its sign on the digits."
    ),
    expected=(
        "to_mantissa(value) returns (mantissa, exponent) where the mantissa is at least one "
        "and below ten in size and the exponent is the power of ten it sits on. A reading of "
        "zero is (0.0, 0), and a reading below zero keeps its sign on the mantissa."
    ),
    baseline_reason=(
        "it takes the base-ten logarithm of the reading itself, which has no answer at zero "
        "and none below it either"
    ),
    edge_cases=(
        "a reading of exactly zero splits to (0.0, 0)",
        "a reading below zero keeps its sign on the mantissa",
    ),
    imports="import math\n",
    baseline='''def to_mantissa(value):
    """Return (mantissa, exponent) for `value`."""
    exponent = int(math.floor(math.log10(value)))
    return value / 10**exponent, exponent''',
    variant_one='''def to_mantissa(value):
    """Return (mantissa, exponent) for `value`."""
    if value == 0:
        return 0.0, 0
    exponent = int(math.floor(math.log10(abs(value))))
    return value / 10**exponent, exponent''',
    variant_two='''def to_mantissa(value):
    """Return (mantissa, exponent) for `value`."""
    if value == 0:
        return 0.0, 0
    sign = -1.0 if value < 0 else 1.0
    size = abs(value)
    exponent = 0
    while size >= 10:
        size /= 10
        exponent += 1
    while size < 1:
        size *= 10
        exponent -= 1
    return sign * size, exponent''',
    variant_three='''def to_mantissa(value):
    """Return (mantissa, exponent) for `value`."""
    if value == 0:
        return 0.0, 0
    exponent = int(math.floor(math.log10(value)))
    return value / 10**exponent, exponent''',
    variant_four='''def to_mantissa(value):
    """Return (mantissa, exponent) for `value`."""
    exponent = int(math.floor(math.log10(abs(value))))
    return value / 10**exponent, exponent''',
    visible_test=_test_module(
        "scientific_mantissa",
        "Published contract for splitting a measurement into digits and a power of ten.",
        """
import pytest


def test_a_reading_above_one_splits_on_a_positive_power() -> None:
    assert to_mantissa(1234.0) == pytest.approx((1.234, 3))


def test_a_reading_below_one_splits_on_a_negative_power() -> None:
    assert to_mantissa(0.05) == pytest.approx((5.0, -2))
""",
        imports="from scientific_mantissa import to_mantissa\n",
    ),
    hidden_test=_test_module(
        "scientific_mantissa",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_reading_above_one_splits_on_a_positive_power() -> None:
    assert to_mantissa(1234.0) == pytest.approx((1.234, 3))


def test_a_reading_of_exactly_zero_splits_to_zero() -> None:
    assert to_mantissa(0.0) == (0.0, 0)


def test_a_reading_below_zero_keeps_its_sign() -> None:
    assert to_mantissa(-1234.0) == pytest.approx((-1.234, 3))
""",
        imports="from scientific_mantissa import to_mantissa\n",
    ),
)


_G094 = D2TaskSpec(
    template_id="d5_numeric.temperature_convert",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d5-numeric-temperature-convert",
    module="temperature_convert",
    module_doc="Converting a temperature between the scales a mixed fleet of sensors reports in.",
    issue=(
        "convert() is documented to convert a temperature between scales. Operators report "
        "that converting a reading to the scale it is already in comes back very slightly "
        "changed, which makes a stored reading drift every time it passes through, and that a "
        "scale nobody has heard of fails with a KeyError rather than being refused."
    ),
    expected=(
        "convert(value, source, target) returns the temperature in the target scale, where the "
        "scales are 'C', 'F' and 'K'. Converting to the scale a reading is already in returns "
        "it exactly unchanged, and a scale outside the three is refused with ValueError."
    ),
    baseline_reason=(
        "it always converts through Celsius, so a reading already in the target scale makes a "
        "round trip that does not land exactly where it started, and it looks the scales up "
        "straight in its tables"
    ),
    edge_cases=(
        "converting to the scale a reading is already in changes nothing at all",
        "a scale outside the three is refused",
    ),
    baseline='''def convert(value, source, target):
    """Return `value` converted from the `source` scale to the `target` scale."""
    to_celsius = {"C": lambda v: v, "F": lambda v: (v - 32) * 5 / 9, "K": lambda v: v - 273.15}
    from_celsius = {"C": lambda v: v, "F": lambda v: v * 9 / 5 + 32, "K": lambda v: v + 273.15}
    return from_celsius[target](to_celsius[source](value))''',
    variant_one='''def convert(value, source, target):
    """Return `value` converted from the `source` scale to the `target` scale."""
    to_celsius = {"C": lambda v: v, "F": lambda v: (v - 32) * 5 / 9, "K": lambda v: v - 273.15}
    from_celsius = {"C": lambda v: v, "F": lambda v: v * 9 / 5 + 32, "K": lambda v: v + 273.15}
    for scale in (source, target):
        if scale not in to_celsius:
            raise ValueError(f"{scale!r} is not a scale this knows")
    if source == target:
        return value
    return from_celsius[target](to_celsius[source](value))''',
    variant_two='''def convert(value, source, target):
    """Return `value` converted from the `source` scale to the `target` scale."""
    known = ("C", "F", "K")
    if source not in known or target not in known:
        raise ValueError(f"{source!r} to {target!r} is not a conversion this knows")
    if source == target:
        return value
    celsius = value
    if source == "F":
        celsius = (value - 32) * 5 / 9
    elif source == "K":
        celsius = value - 273.15
    if target == "F":
        return celsius * 9 / 5 + 32
    if target == "K":
        return celsius + 273.15
    return celsius''',
    variant_three='''def convert(value, source, target):
    """Return `value` converted from the `source` scale to the `target` scale."""
    to_celsius = {"C": lambda v: v, "F": lambda v: (v - 32) * 5 / 9, "K": lambda v: v - 273.15}
    from_celsius = {"C": lambda v: v, "F": lambda v: v * 9 / 5 + 32, "K": lambda v: v + 273.15}
    if source == target:
        return value
    return from_celsius[target](to_celsius[source](value))''',
    variant_four='''def convert(value, source, target):
    """Return `value` converted from the `source` scale to the `target` scale."""
    to_celsius = {"C": lambda v: v, "F": lambda v: (v - 32) * 5 / 9, "K": lambda v: v - 273.15}
    from_celsius = {"C": lambda v: v, "F": lambda v: v * 9 / 5 + 32, "K": lambda v: v + 273.15}
    for scale in (source, target):
        if scale not in to_celsius:
            raise ValueError(f"{scale!r} is not a scale this knows")
    return from_celsius[target](to_celsius[source](value))''',
    visible_test=_test_module(
        "temperature_convert",
        "Published contract for converting between temperature scales.",
        """
import pytest


def test_boiling_water_in_fahrenheit() -> None:
    assert convert(100, "C", "F") == pytest.approx(212.0)


def test_freezing_water_in_kelvin() -> None:
    assert convert(0, "C", "K") == pytest.approx(273.15)


def test_freezing_water_from_fahrenheit() -> None:
    assert convert(32, "F", "C") == pytest.approx(0.0)
""",
        imports="from temperature_convert import convert\n",
    ),
    hidden_test=_test_module(
        "temperature_convert",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_boiling_water_in_fahrenheit() -> None:
    assert convert(100, "C", "F") == pytest.approx(212.0)


def test_converting_to_the_same_scale_changes_nothing_at_all() -> None:
    assert convert(25.3, "K", "K") == 25.3


def test_a_scale_nobody_has_heard_of_is_refused() -> None:
    with pytest.raises(ValueError):
        convert(1, "C", "X")
""",
        imports="from temperature_convert import convert\n",
    ),
)

# ----------------------------------------------------------------------- parsing and validation

_G095 = D2TaskSpec(
    template_id="d5_parsing.user_agent",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-user-agent",
    module="user_agent",
    module_doc="Reading the leading product and version out of a client's identification.",
    issue=(
        "first_product() is documented to read the leading product and version out of a "
        "client's identification. Callers report that a client naming no version at all brings "
        "the read down instead of coming back with no version, and that a string with a space "
        "in front of it reads an empty product."
    ),
    expected=(
        "first_product(text) returns (product, version) read from the leading token, where the "
        "version is whatever follows the slash. A token carrying no slash has no version and "
        "comes back with None in its place, and whitespace in front of the token is ignored."
    ),
    baseline_reason=(
        "it splits the token on a slash into exactly two names, which a token with no slash "
        "cannot fill, and it takes the leading token by cutting at the first space, which is "
        "empty when the string begins with one"
    ),
    edge_cases=(
        "a token carrying no slash comes back with no version",
        "whitespace in front of the token is ignored",
    ),
    baseline='''def first_product(text):
    """Return (product, version) from the leading token of `text`."""
    token = text.split(" ")[0]
    name, version = token.split("/")
    return name, version''',
    variant_one='''def first_product(text):
    """Return (product, version) from the leading token of `text`."""
    token = text.split()[0]
    name, slash, version = token.partition("/")
    return name, version if slash else None''',
    variant_two='''def first_product(text):
    """Return (product, version) from the leading token of `text`."""
    token = text.strip().split(" ")[0]
    if "/" not in token:
        return token, None
    name, _, version = token.partition("/")
    return name, version''',
    variant_three='''def first_product(text):
    """Return (product, version) from the leading token of `text`."""
    token = text.split(" ")[0]
    name, slash, version = token.partition("/")
    return name, version if slash else None''',
    variant_four='''def first_product(text):
    """Return (product, version) from the leading token of `text`."""
    token = text.split()[0]
    name, version = token.split("/")
    return name, version''',
    visible_test=_test_module(
        "user_agent",
        "Published contract for reading a client's leading product.",
        """
def test_a_product_with_a_version_and_a_comment() -> None:
    assert first_product("Mozilla/5.0 (X11)") == ("Mozilla", "5.0")


def test_a_product_on_its_own() -> None:
    assert first_product("curl/8.1.2") == ("curl", "8.1.2")
""",
        imports="from user_agent import first_product\n",
    ),
    hidden_test=_test_module(
        "user_agent",
        "The part of the contract the published tests do not state.",
        """
def test_a_product_with_a_version_and_a_comment() -> None:
    assert first_product("Mozilla/5.0 (X11)") == ("Mozilla", "5.0")


def test_a_token_with_no_slash_has_no_version() -> None:
    assert first_product("SomeBot") == ("SomeBot", None)


def test_whitespace_in_front_of_the_token_is_ignored() -> None:
    assert first_product("  curl/8.1.2") == ("curl", "8.1.2")
""",
        imports="from user_agent import first_product\n",
    ),
)


_G096 = D2TaskSpec(
    template_id="d5_parsing.algebraic_square",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d5-parsing-algebraic-square",
    module="algebraic_square",
    module_doc="Reading a named board square into the two indices the board is stored by.",
    issue=(
        "to_indices() is documented to read a named square into file and rank indices. Callers "
        "report that a square written with a capital file letter comes back with a nonsense "
        "file index, and that a square naming a file or rank that is not on the board is read "
        "as though it were."
    ),
    expected=(
        "to_indices(square) returns (file, rank) counting from zero, so 'a1' is (0, 0) and "
        "'h8' is (7, 7). The file letter is read whatever its case, and a square outside files "
        "a to h or ranks one to eight is refused with ValueError."
    ),
    baseline_reason=(
        "it takes the file letter's distance from a lowercase 'a', which is far off for a "
        "capital, and it converts both halves without checking either lands on the board"
    ),
    edge_cases=(
        "the file letter is read whatever its case",
        "a square that is not on the board is refused",
    ),
    baseline='''def to_indices(square):
    """Return (file, rank) for the named `square`."""
    return ord(square[0]) - ord("a"), int(square[1]) - 1''',
    variant_one='''def to_indices(square):
    """Return (file, rank) for the named `square`."""
    if len(square) != 2:
        raise ValueError(f"{square!r} does not name a square")
    file_index = ord(square[0].lower()) - ord("a")
    if not square[1].isdigit():
        raise ValueError(f"{square!r} does not name a square")
    rank_index = int(square[1]) - 1
    if not 0 <= file_index <= 7 or not 0 <= rank_index <= 7:
        raise ValueError(f"{square!r} is not on the board")
    return file_index, rank_index''',
    variant_two='''def to_indices(square):
    """Return (file, rank) for the named `square`."""
    files = "abcdefgh"
    ranks = "12345678"
    if len(square) != 2 or square[0].lower() not in files or square[1] not in ranks:
        raise ValueError(f"{square!r} is not on the board")
    return files.index(square[0].lower()), ranks.index(square[1])''',
    variant_three='''def to_indices(square):
    """Return (file, rank) for the named `square`."""
    return ord(square[0].lower()) - ord("a"), int(square[1]) - 1''',
    variant_four='''def to_indices(square):
    """Return (file, rank) for the named `square`."""
    files = "abcdefgh"
    ranks = "12345678"
    if len(square) != 2 or square[0] not in files or square[1] not in ranks:
        raise ValueError(f"{square!r} is not on the board")
    return files.index(square[0]), ranks.index(square[1])''',
    visible_test=_test_module(
        "algebraic_square",
        "Published contract for reading a named board square.",
        """
def test_the_bottom_left_square_is_the_origin() -> None:
    assert to_indices("a1") == (0, 0)


def test_a_square_in_the_middle() -> None:
    assert to_indices("e4") == (4, 3)


def test_the_top_right_square() -> None:
    assert to_indices("h8") == (7, 7)
""",
        imports="from algebraic_square import to_indices\n",
    ),
    hidden_test=_test_module(
        "algebraic_square",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_bottom_left_square_is_the_origin() -> None:
    assert to_indices("a1") == (0, 0)


def test_a_capital_file_letter_reads_the_same() -> None:
    assert to_indices("E4") == (4, 3)


def test_a_square_that_is_not_on_the_board_is_refused() -> None:
    with pytest.raises(ValueError):
        to_indices("z9")
""",
        imports="from algebraic_square import to_indices\n",
    ),
)

# ------------------------------------------------------------------------- data transformation

_G097 = D2TaskSpec(
    template_id="d5_transform.summarise_columns",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-summarise-columns",
    module="summarise_columns",
    module_doc="Reporting the smallest, largest and average reading of each measured column.",
    issue=(
        "summarise() is documented to report the smallest, largest and average of each column. "
        "Analysts report that a column no record carries any reading for brings the whole "
        "report down, and that a column holding True and False is averaged as though those "
        "were readings of one and zero."
    ),
    expected=(
        "summarise(records, columns) returns a mapping from column to (smallest, largest, "
        "average) over the numeric readings that column carries. A boolean is not a reading, "
        "and a column carrying no readings at all is left out of the report rather than "
        "reported as anything."
    ),
    baseline_reason=(
        "it takes every value the column carries as a reading, booleans included, and it "
        "reports on a column with no readings by asking for the smallest of nothing"
    ),
    edge_cases=(
        "a column carrying no readings is left out of the report",
        "a boolean is not counted as a reading",
    ),
    baseline='''def summarise(records, columns):
    """Return (smallest, largest, average) for each of `columns`."""
    out = {}
    for column in columns:
        values = [record[column] for record in records if column in record]
        out[column] = (min(values), max(values), sum(values) / len(values))
    return out''',
    variant_one='''def summarise(records, columns):
    """Return (smallest, largest, average) for each of `columns`."""
    out = {}
    for column in columns:
        values = [
            record[column]
            for record in records
            if column in record
            and isinstance(record[column], (int, float))
            and not isinstance(record[column], bool)
        ]
        if not values:
            continue
        out[column] = (min(values), max(values), sum(values) / len(values))
    return out''',
    variant_two='''def summarise(records, columns):
    """Return (smallest, largest, average) for each of `columns`."""

    def readings(column):
        for record in records:
            value = record.get(column)
            if type(value) in (int, float):
                yield value

    out = {}
    for column in columns:
        values = list(readings(column))
        if values:
            out[column] = (min(values), max(values), sum(values) / len(values))
    return out''',
    variant_three='''def summarise(records, columns):
    """Return (smallest, largest, average) for each of `columns`."""
    out = {}
    for column in columns:
        values = [record[column] for record in records if column in record]
        if not values:
            continue
        out[column] = (min(values), max(values), sum(values) / len(values))
    return out''',
    variant_four='''def summarise(records, columns):
    """Return (smallest, largest, average) for each of `columns`."""
    out = {}
    for column in columns:
        values = [
            record[column]
            for record in records
            if column in record
            and isinstance(record[column], (int, float))
            and not isinstance(record[column], bool)
        ]
        out[column] = (min(values), max(values), sum(values) / len(values))
    return out''',
    visible_test=_test_module(
        "summarise_columns",
        "Published contract for summarising measured columns.",
        """
def test_a_column_of_readings_is_summarised() -> None:
    assert summarise([{"a": 1}, {"a": 3}], ["a"]) == {"a": (1, 3, 2.0)}


def test_two_columns_are_summarised_apart() -> None:
    records = [{"a": 1, "b": 10}, {"a": 3, "b": 20}]
    assert summarise(records, ["a", "b"]) == {"a": (1, 3, 2.0), "b": (10, 20, 15.0)}
""",
        imports="from summarise_columns import summarise\n",
    ),
    hidden_test=_test_module(
        "summarise_columns",
        "The part of the contract the published tests do not state.",
        """
def test_a_column_of_readings_is_summarised() -> None:
    assert summarise([{"a": 1}, {"a": 3}], ["a"]) == {"a": (1, 3, 2.0)}


def test_a_column_carrying_no_readings_is_left_out() -> None:
    assert summarise([{"a": 1}], ["a", "b"]) == {"a": (1, 1, 1.0)}


def test_a_boolean_is_not_a_reading() -> None:
    assert summarise([{"a": 5}, {"a": True}], ["a"]) == {"a": (5, 5, 5.0)}
""",
        imports="from summarise_columns import summarise\n",
    ),
)


_G098 = D2TaskSpec(
    template_id="d5_transform.normalise_weights",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d5-transform-normalise-weights",
    module="normalise_weights",
    module_doc="Turning a set of weights into the shares of a whole that they stand for.",
    issue=(
        "normalise() is documented to turn weights into shares of a whole. Callers report that "
        "a set of weights that are all zero fails with a division error rather than being "
        "refused, and that a weight below zero is turned into a negative share instead of "
        "being refused."
    ),
    expected=(
        "normalise(weights) returns each weight as its share of the total, so the shares sum "
        "to one. Weights that total zero are refused with ValueError because there is no whole "
        "to take a share of, and a weight below zero is refused because a share cannot be "
        "negative."
    ),
    baseline_reason=(
        "it divides each weight by the total without checking either that the total is "
        "something to divide by or that the weights are all positive"
    ),
    edge_cases=(
        "weights totalling zero are refused",
        "a weight below zero is refused",
    ),
    baseline='''def normalise(weights):
    """Return each weight of `weights` as its share of the total."""
    total = sum(weights.values())
    return {name: weight / total for name, weight in weights.items()}''',
    variant_one='''def normalise(weights):
    """Return each weight of `weights` as its share of the total."""
    for name, weight in weights.items():
        if weight < 0:
            raise ValueError(f"{name!r} has a weight of {weight}")
    total = sum(weights.values())
    if total == 0:
        raise ValueError("the weights total nothing to take a share of")
    return {name: weight / total for name, weight in weights.items()}''',
    variant_two='''def normalise(weights):
    """Return each weight of `weights` as its share of the total."""
    negative = sorted(name for name, weight in weights.items() if weight < 0)
    if negative:
        raise ValueError(f"these weights are below zero: {negative}")
    total = sum(weights.values())
    if not total:
        raise ValueError("the weights total nothing to take a share of")
    return {name: weight / total for name, weight in weights.items()}''',
    variant_three='''def normalise(weights):
    """Return each weight of `weights` as its share of the total."""
    total = sum(weights.values())
    if total == 0:
        raise ValueError("the weights total nothing to take a share of")
    return {name: weight / total for name, weight in weights.items()}''',
    variant_four='''def normalise(weights):
    """Return each weight of `weights` as its share of the total."""
    for name, weight in weights.items():
        if weight < 0:
            raise ValueError(f"{name!r} has a weight of {weight}")
    total = sum(weights.values())
    return {name: weight / total for name, weight in weights.items()}''',
    visible_test=_test_module(
        "normalise_weights",
        "Published contract for turning weights into shares.",
        """
def test_two_weights_become_their_shares() -> None:
    assert normalise({"a": 1, "b": 3}) == {"a": 0.25, "b": 0.75}


def test_a_single_weight_takes_the_whole_share() -> None:
    assert normalise({"a": 5}) == {"a": 1.0}
""",
        imports="from normalise_weights import normalise\n",
    ),
    hidden_test=_test_module(
        "normalise_weights",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_weights_become_their_shares() -> None:
    assert normalise({"a": 1, "b": 3}) == {"a": 0.25, "b": 0.75}


def test_weights_totalling_zero_are_refused() -> None:
    with pytest.raises(ValueError):
        normalise({"a": 0, "b": 0})


def test_a_weight_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        normalise({"a": 2, "b": -1})
""",
        imports="from normalise_weights import normalise\n",
    ),
)

# ---------------------------------------------------------------------- state and idempotency

_G099 = D2TaskSpec(
    template_id="d5_state.reload_rollback",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d5-state-reload-rollback",
    module="reload_rollback",
    module_doc="Taking on a new configuration only when it is fit to be taken on.",
    issue=(
        "reload() is documented to take on a new configuration only when it passes its check. "
        "Operators report that a configuration which fails the check is taken on anyway and "
        "the service comes up broken, and that a check which itself falls over takes the "
        "reload down with it instead of counting as a failed check."
    ),
    expected=(
        "reload(state, candidate, validate) returns the state carrying the candidate as its "
        "configuration when the check passes, meaning it returned nothing. When the check "
        "objects the configuration in use is kept and the objection is recorded as the reason, "
        "and a check that falls over counts as an objection whose reason is what it raised."
    ),
    baseline_reason=(
        "it records whatever the check said and takes the candidate on regardless, and it "
        "lets a check that raises escape rather than reading it as an objection"
    ),
    edge_cases=(
        "a candidate that fails the check is not taken on",
        "a check that falls over counts as an objection",
    ),
    baseline='''def reload(state, candidate, validate):
    """Return `state` carrying `candidate` when it passes `validate`."""
    reason = validate(candidate)
    return {"config": candidate, "reason": reason}''',
    variant_one='''def reload(state, candidate, validate):
    """Return `state` carrying `candidate` when it passes `validate`."""
    try:
        reason = validate(candidate)
    except Exception as error:
        reason = str(error)
    if reason:
        return {"config": state["config"], "reason": reason}
    return {"config": candidate, "reason": None}''',
    variant_two='''def reload(state, candidate, validate):
    """Return `state` carrying `candidate` when it passes `validate`."""
    settled = dict(state)
    try:
        objection = validate(candidate)
    except Exception as error:
        objection = str(error)
    settled["reason"] = objection or None
    if not objection:
        settled["config"] = candidate
    return settled''',
    variant_three='''def reload(state, candidate, validate):
    """Return `state` carrying `candidate` when it passes `validate`."""
    reason = validate(candidate)
    if reason:
        return {"config": state["config"], "reason": reason}
    return {"config": candidate, "reason": None}''',
    variant_four='''def reload(state, candidate, validate):
    """Return `state` carrying `candidate` when it passes `validate`."""
    try:
        reason = validate(candidate)
    except Exception as error:
        reason = str(error)
    return {"config": candidate, "reason": reason}''',
    visible_test=_test_module(
        "reload_rollback",
        "Published contract for taking on a new configuration.",
        """
def test_a_candidate_that_passes_is_taken_on() -> None:
    state = {"config": {"a": 1}, "reason": None}
    assert reload(state, {"a": 2}, lambda candidate: None) == {
        "config": {"a": 2},
        "reason": None,
    }


def test_the_callers_state_is_left_alone() -> None:
    state = {"config": {"a": 1}, "reason": None}
    reload(state, {"a": 2}, lambda candidate: None)
    assert state == {"config": {"a": 1}, "reason": None}
""",
        imports="from reload_rollback import reload\n",
    ),
    hidden_test=_test_module(
        "reload_rollback",
        "The part of the contract the published tests do not state.",
        """
def _fall_over(candidate):
    raise RuntimeError("the check itself broke")


def test_a_candidate_that_passes_is_taken_on() -> None:
    state = {"config": {"a": 1}, "reason": None}
    assert reload(state, {"a": 2}, lambda candidate: None) == {
        "config": {"a": 2},
        "reason": None,
    }


def test_a_candidate_that_fails_the_check_is_not_taken_on() -> None:
    state = {"config": {"a": 1}, "reason": None}
    assert reload(state, {"a": 2}, lambda candidate: "bad") == {
        "config": {"a": 1},
        "reason": "bad",
    }


def test_a_check_that_falls_over_counts_as_an_objection() -> None:
    state = {"config": {"a": 1}, "reason": None}
    assert reload(state, {"a": 2}, _fall_over)["reason"] == "the check itself broke"
""",
        imports="from reload_rollback import reload\n",
    ),
)

# --------------------------------------------------------------------------- error handling

_G100 = D2TaskSpec(
    template_id="d5_error.summarise_failures",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d5-error-summarise-failures",
    module="summarise_failures",
    module_doc="Writing the one line about a run's failures that goes into the alert.",
    issue=(
        "summarise() is documented to write one line naming what failed. On-call report that a "
        "component failing twice is named twice and counted twice, which makes a small outage "
        "read as a large one, and that a run in which nothing failed produces a line saying "
        "nought failed followed by nothing at all."
    ),
    expected=(
        "summarise(failures) returns one line naming the distinct components that failed, "
        "sorted and counted once each however many times they failed, and returns the words "
        "'none failed' for a run in which nothing did."
    ),
    baseline_reason=(
        "it counts and names the failures rather than the components, so a repeat is counted "
        "twice, and it writes the same shape of line for a run with no failures at all"
    ),
    edge_cases=(
        "a component failing more than once is named and counted once",
        "a run in which nothing failed says so in words",
    ),
    baseline='''def summarise(failures):
    """Return the one line naming what failed."""
    names = [name for name, _ in failures]
    return f"{len(names)} failed: {', '.join(sorted(names))}"''',
    variant_one='''def summarise(failures):
    """Return the one line naming what failed."""
    names = sorted({name for name, _ in failures})
    if not names:
        return "none failed"
    return f"{len(names)} failed: {', '.join(names)}"''',
    variant_two='''def summarise(failures):
    """Return the one line naming what failed."""
    names = []
    for name, _ in failures:
        if name not in names:
            names.append(name)
    names.sort()
    return f"{len(names)} failed: {', '.join(names)}" if names else "none failed"''',
    variant_three='''def summarise(failures):
    """Return the one line naming what failed."""
    names = sorted({name for name, _ in failures})
    return f"{len(names)} failed: {', '.join(names)}"''',
    variant_four='''def summarise(failures):
    """Return the one line naming what failed."""
    names = [name for name, _ in failures]
    if not names:
        return "none failed"
    return f"{len(names)} failed: {', '.join(sorted(names))}"''',
    visible_test=_test_module(
        "summarise_failures",
        "Published contract for the one line naming what failed.",
        """
def test_two_components_are_named_in_order() -> None:
    assert summarise([("b", "down"), ("a", "slow")]) == "2 failed: a, b"


def test_one_component_is_named_alone() -> None:
    assert summarise([("a", "down")]) == "1 failed: a"
""",
        imports="from summarise_failures import summarise\n",
    ),
    hidden_test=_test_module(
        "summarise_failures",
        "The part of the contract the published tests do not state.",
        """
def test_two_components_are_named_in_order() -> None:
    assert summarise([("b", "down"), ("a", "slow")]) == "2 failed: a, b"


def test_a_component_failing_twice_is_named_once() -> None:
    assert summarise([("a", "down"), ("a", "still down")]) == "1 failed: a"


def test_a_run_with_nothing_failed_says_so_in_words() -> None:
    assert summarise([]) == "none failed"
""",
        imports="from summarise_failures import summarise\n",
    ),
)

#: The authored calibration groups, in template-id order. The target is 100; the achieved count
#: is what `scripts/corpus_d5.py` reports and what S21D5-035 divides by. A shortfall is recorded
#: rather than papered over — Section 6.2 of the backlog forbids lowering a floor to meet it.
D5_CALIBRATION_SPECS: tuple[D2TaskSpec, ...] = (
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
    _G096,
    _G097,
    _G098,
    _G099,
    _G100,
)
