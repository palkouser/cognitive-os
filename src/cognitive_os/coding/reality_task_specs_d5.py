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
    baseline_reason="it truncates the rank instead of taking its ceiling and indexes an empty list",
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
)
