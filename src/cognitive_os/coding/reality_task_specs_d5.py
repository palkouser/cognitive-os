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
)
