"""The Sprint 21D3 retrieval source pool, §S21D3-030.

Gate L2 condition 24 and Gate D1 condition 15 need at least fifty *new* unseen-task queries, and
S21D3-016 froze the arms before any of them existed. So the pool is overproduced: sixty task
groups are authored here, W3 keeps whichever survive integrity filtering, and the floor is met
with room rather than by admitting a marginal query once the numbers are visible.

A retrieval group is lighter than a correction group on purpose. Retrieval is evaluated on
projected graphs and edit paths, not on ranked candidates, and `project_correction` needs one
thing from a trajectory: at least one step the verifier rejected, then one it accepted. Four
candidates per group would buy nothing that the failed/repaired pair does not already give,
and would cost sixty groups' worth of authoring for evidence no arm reads.

The two bodies are executed rather than declared: S21D3-030 requires the failed body to fail its
hidden suite and the repaired body to pass it, which is what makes the pair *causal* evidence
instead of two files that differ.
"""

from __future__ import annotations

from dataclasses import dataclass

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module

_BOUNDARY = RealityTaskFamily.BOUNDARY_COLLECTIONS
_PARSING = RealityTaskFamily.PARSING_VALIDATION
_STATE = RealityTaskFamily.STATE_IDEMPOTENCY
_NUMERIC = RealityTaskFamily.NUMERIC_LOGIC
_ERRORS = RealityTaskFamily.ERROR_HANDLING
_TRANSFORM = RealityTaskFamily.DATA_TRANSFORMATION


@dataclass(frozen=True, slots=True)
class D3RetrievalSpec:
    """One retrieval source group: the failed state, the repair, and why the first failed."""

    template_id: str
    family: RealityTaskFamily
    repository_group: str
    module: str
    module_doc: str
    issue: str
    expected: str
    failure_reason: str
    #: Passes nothing that matters: the hidden suite rejects it.
    failed: str
    #: The accepted repair. The hidden suite passes.
    repaired: str
    hidden_test: str

    def module_text(self, body: str) -> str:
        return f'"""{self.module_doc}"""\n\n\n{body.strip()}\n'

    @property
    def task_signature(self) -> str:
        """The stable pair identity the graph projection and the holdout both address."""
        return self.template_id.replace(".", ":")


def _hidden(module: str, body: str, *, imports: str = "") -> str:
    return _test_module(module, "The contract the repair has to satisfy.", body, imports=imports)


def _spec(
    name: str,
    family: RealityTaskFamily,
    module: str,
    doc: str,
    issue: str,
    expected: str,
    reason: str,
    failed: str,
    repaired: str,
    test_body: str,
    *,
    imports: str = "",
) -> D3RetrievalSpec:
    """One row of the table. A helper because sixty literal constructors is sixty chances to
    disagree about field order, not because the shape needs a builder."""
    return D3RetrievalSpec(
        template_id=name,
        family=family,
        repository_group=f"d3r-{name.split('.', 1)[1].replace('_', '-')}",
        module=module,
        module_doc=doc,
        issue=issue,
        expected=expected,
        failure_reason=reason,
        failed=failed,
        repaired=repaired,
        hidden_test=_hidden(module, test_body, imports=imports or f"from {module} import *\n"),
    )


D3_RETRIEVAL_SPECS: tuple[D3RetrievalSpec, ...] = (
    # ------------------------------------------------------------ boundary and collections
    _spec(
        "d3r_boundary.last_index_of",
        _BOUNDARY,
        "last_index_lookup",
        "Finding the last position a value occupies.",
        "last_index_of() hands back the first position instead of the last one.",
        "last_index_of(items, value) returns the highest index holding value, or -1.",
        "it scans forward and returns on the first hit instead of remembering the last",
        """def last_index_of(items, value):
    for index, entry in enumerate(items):
        if entry == value:
            return index
    return -1""",
        """def last_index_of(items, value):
    found = -1
    for index, entry in enumerate(items):
        if entry == value:
            found = index
    return found""",
        """
def test_the_last_position_is_reported() -> None:
    assert last_index_of([1, 2, 1], 1) == 2


def test_a_missing_value_reports_minus_one() -> None:
    assert last_index_of([1, 2], 9) == -1
""",
        imports="from last_index_lookup import last_index_of\n",
    ),
    _spec(
        "d3r_boundary.drop_while_blank",
        _BOUNDARY,
        "blank_prefix",
        "Dropping the blank lines a file starts with.",
        "drop_while_blank() removes every blank line rather than only the leading run.",
        "drop_while_blank(lines) drops blank lines until the first non-blank and keeps the rest.",
        "it filters the whole sequence instead of stopping at the first non-blank line",
        """def drop_while_blank(lines):
    return [line for line in lines if line.strip()]""",
        """def drop_while_blank(lines):
    remaining = list(lines)
    while remaining and not remaining[0].strip():
        remaining.pop(0)
    return remaining""",
        """
def test_only_the_leading_run_is_dropped() -> None:
    assert drop_while_blank(["", " ", "a", "", "b"]) == ["a", "", "b"]
""",
        imports="from blank_prefix import drop_while_blank\n",
    ),
    _spec(
        "d3r_boundary.batch_evenly",
        _BOUNDARY,
        "even_batches",
        "Splitting work into a fixed number of batches.",
        "batch_evenly() returns fewer batches than asked for when the work is short.",
        "batch_evenly(items, count) always returns count lists, padding with empty ones.",
        "it derives the batch count from the item count instead of from the request",
        """def batch_evenly(items, count):
    size = max(1, len(items) // count)
    return [items[start : start + size] for start in range(0, len(items), size)]""",
        """def batch_evenly(items, count):
    collected = list(items)
    batches = []
    for index in range(count):
        batches.append(collected[index::count])
    return batches""",
        """
def test_the_requested_number_of_batches_is_returned() -> None:
    assert len(batch_evenly([1, 2], 4)) == 4


def test_every_item_lands_in_exactly_one_batch() -> None:
    batches = batch_evenly([1, 2, 3, 4, 5], 2)
    assert sorted(item for batch in batches for item in batch) == [1, 2, 3, 4, 5]
""",
        imports="from even_batches import batch_evenly\n",
    ),
    _spec(
        "d3r_boundary.longest_prefix",
        _BOUNDARY,
        "shared_prefix",
        "The longest opening two labels agree on.",
        "longest_prefix() returns the shorter label whenever one starts the other.",
        "longest_prefix(left, right) returns the longest opening both labels share.",
        "it returns early on a startswith check instead of comparing character by character",
        """def longest_prefix(left, right):
    if left.startswith(right) or right.startswith(left):
        return min(left, right)
    return ""
""",
        """def longest_prefix(left, right):
    shared = []
    for first, second in zip(left, right):
        if first != second:
            break
        shared.append(first)
    return "".join(shared)""",
        """
def test_a_partial_overlap_is_reported() -> None:
    assert longest_prefix("about", "above") == "abo"


def test_no_overlap_is_empty() -> None:
    assert longest_prefix("ab", "cd") == ""
""",
        imports="from shared_prefix import longest_prefix\n",
    ),
    _spec(
        "d3r_boundary.stride_take",
        _BOUNDARY,
        "stride_sampling",
        "Sampling a sequence at a fixed stride.",
        "stride_take() loses the first element when the stride is above one.",
        "stride_take(items, stride) returns items at positions 0, stride, 2*stride and so on.",
        "the slice starts at the stride rather than at zero",
        """def stride_take(items, stride):
    return list(items)[stride::stride]""",
        """def stride_take(items, stride):
    return list(items)[::stride]""",
        """
def test_the_first_item_is_always_sampled() -> None:
    assert stride_take([1, 2, 3, 4, 5], 2) == [1, 3, 5]
""",
        imports="from stride_sampling import stride_take\n",
    ),
    _spec(
        "d3r_boundary.without_none",
        _BOUNDARY,
        "none_filter",
        "Dropping absent readings from a sequence.",
        "without_none() drops zeros and empty strings along with the absent readings.",
        "without_none(items) drops only the None entries and keeps every falsy value.",
        "it tests the item for truth rather than for being None",
        """def without_none(items):
    return [item for item in items if item]""",
        """def without_none(items):
    return [item for item in items if item is not None]""",
        """
def test_falsy_readings_survive() -> None:
    assert without_none([0, None, "", 3]) == [0, "", 3]
""",
        imports="from none_filter import without_none\n",
    ),
    _spec(
        "d3r_boundary.split_at_first",
        _BOUNDARY,
        "first_split",
        "Cutting a sequence in two at a marker.",
        "split_at_first() keeps the marker in the tail half.",
        "split_at_first(items, marker) returns (head, tail) with the marker in neither half.",
        "the tail slice starts on the marker instead of after it",
        """def split_at_first(items, marker):
    collected = list(items)
    cut = collected.index(marker)
    return collected[:cut], collected[cut:]""",
        """def split_at_first(items, marker):
    collected = list(items)
    cut = collected.index(marker)
    return collected[:cut], collected[cut + 1 :]""",
        """
def test_the_marker_is_in_neither_half() -> None:
    assert split_at_first([1, 2, 3], 2) == ([1], [3])
""",
        imports="from first_split import split_at_first\n",
    ),
    _spec(
        "d3r_boundary.count_runs",
        _BOUNDARY,
        "run_counting",
        "Counting the runs of equal neighbours.",
        "count_runs() reports one run too many for a sequence that ends on a change.",
        "count_runs(items) returns the number of maximal runs of equal neighbours.",
        "it counts changes and adds one without checking for an empty sequence",
        """def count_runs(items):
    changes = 0
    collected = list(items)
    for first, second in zip(collected, collected[1:]):
        if first != second:
            changes += 1
    return changes + 1""",
        """def count_runs(items):
    collected = list(items)
    if not collected:
        return 0
    runs = 1
    for first, second in zip(collected, collected[1:]):
        if first != second:
            runs += 1
    return runs""",
        """
def test_an_empty_sequence_has_no_runs() -> None:
    assert count_runs([]) == 0


def test_neighbouring_duplicates_form_one_run() -> None:
    assert count_runs([1, 1, 2]) == 2
""",
        imports="from run_counting import count_runs\n",
    ),
    _spec(
        "d3r_boundary.rotate_right",
        _BOUNDARY,
        "right_rotation",
        "Rotating a sequence towards its end.",
        "rotate_right() rotates the wrong way for an offset above the length.",
        "rotate_right(items, offset) rotates right, wrapping for any non-negative offset.",
        "the offset is not reduced modulo the length before it slices",
        """def rotate_right(items, offset):
    collected = list(items)
    return collected[-offset:] + collected[:-offset]""",
        """def rotate_right(items, offset):
    collected = list(items)
    if not collected:
        return collected
    step = offset % len(collected)
    return collected[-step:] + collected[:-step] if step else collected""",
        """
def test_an_offset_above_the_length_wraps() -> None:
    assert rotate_right([1, 2, 3], 4) == [3, 1, 2]


def test_an_empty_sequence_rotates_to_itself() -> None:
    assert rotate_right([], 2) == []
""",
        imports="from right_rotation import rotate_right\n",
    ),
    _spec(
        "d3r_boundary.take_between",
        _BOUNDARY,
        "between_markers",
        "Reading what sits between two markers.",
        "take_between() includes the closing marker in its answer.",
        "take_between(items, opening, closing) returns what sits strictly between them.",
        "the closing bound is inclusive because the slice uses the marker index plus one",
        """def take_between(items, opening, closing):
    collected = list(items)
    start = collected.index(opening)
    stop = collected.index(closing)
    return collected[start + 1 : stop + 1]""",
        """def take_between(items, opening, closing):
    collected = list(items)
    start = collected.index(opening)
    stop = collected.index(closing)
    return collected[start + 1 : stop]""",
        """
def test_neither_marker_is_included() -> None:
    assert take_between([1, 2, 3, 4], 1, 4) == [2, 3]
""",
        imports="from between_markers import take_between\n",
    ),
    # ------------------------------------------------------------- parsing and validation
    _spec(
        "d3r_parsing.strip_quotes",
        _PARSING,
        "quote_stripping",
        "Removing matching quotes from a field.",
        "strip_quotes() removes a leading quote even when the field does not close it.",
        "strip_quotes(field) removes quotes only when the field opens and closes with the same "
        "quote.",
        "it strips both ends independently instead of requiring a matching pair",
        """def strip_quotes(field):
    stripped = field.strip("\\"'")
    return stripped""",
        """def strip_quotes(field):
    for quote in ('"', "'"):
        if len(field) >= 2 and field.startswith(quote) and field.endswith(quote):
            return field[1:-1]
    return field""",
        """
def test_a_matching_pair_is_removed() -> None:
    assert strip_quotes('"a"') == "a"


def test_an_unclosed_quote_is_left_alone() -> None:
    assert strip_quotes('"a') == '"a'
""",
        imports="from quote_stripping import strip_quotes\n",
    ),
    _spec(
        "d3r_parsing.parse_hex_byte",
        _PARSING,
        "hex_bytes",
        "Reading a two-digit hexadecimal byte.",
        "parse_hex_byte() accepts values that are longer than one byte.",
        "parse_hex_byte(text) returns the byte value and rejects anything but two hex digits.",
        "int(text, 16) is called without checking the length first",
        """def parse_hex_byte(text):
    return int(text, 16)""",
        """def parse_hex_byte(text):
    if len(text) != 2:
        raise ValueError(f"not a byte: {text!r}")
    return int(text, 16)""",
        """
import pytest

from hex_bytes import parse_hex_byte


def test_a_two_digit_byte() -> None:
    assert parse_hex_byte("ff") == 255


def test_a_longer_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_hex_byte("fff")
""",
        imports="",
    ),
    _spec(
        "d3r_parsing.split_once_right",
        _PARSING,
        "right_split",
        "Splitting a label at its last separator.",
        "split_once_right() splits at the first separator rather than the last.",
        "split_once_right(text, sep) returns (head, tail) split at the final separator.",
        "it calls split instead of rsplit",
        """def split_once_right(text, sep):
    head, _, tail = text.partition(sep)
    return head, tail""",
        """def split_once_right(text, sep):
    head, _, tail = text.rpartition(sep)
    return head, tail""",
        """
def test_the_final_separator_decides() -> None:
    assert split_once_right("a.b.c", ".") == ("a.b", "c")
""",
        imports="from right_split import split_once_right\n",
    ),
    _spec(
        "d3r_parsing.normalise_case",
        _PARSING,
        "case_folding",
        "Comparing labels without regard to case.",
        "normalise_case() leaves accented and Turkish letters comparing unequal.",
        "normalise_case(label) folds case so equal-meaning labels compare equal.",
        "lower() is not a case fold and misses several scripts",
        """def normalise_case(label):
    folded = label.lower()
    return folded""",
        """def normalise_case(label):
    folded = label.casefold()
    return folded""",
        """
def test_a_sharp_s_folds_to_a_double_s() -> None:
    assert normalise_case("STRASSE") == normalise_case("stra\\u00dfe")
""",
        imports="from case_folding import normalise_case\n",
    ),
    _spec(
        "d3r_parsing.parse_key_list",
        _PARSING,
        "key_lists",
        "Reading a comma-separated list of keys.",
        "parse_key_list() returns one empty key for empty text.",
        "parse_key_list(text) returns the trimmed non-empty keys, or an empty list.",
        "split on empty text yields a single empty piece and nothing filters it out",
        """def parse_key_list(text):
    pieces = text.split(",")
    return [piece.strip() for piece in pieces]""",
        """def parse_key_list(text):
    return [piece.strip() for piece in text.split(",") if piece.strip()]""",
        """
def test_empty_text_has_no_keys() -> None:
    assert parse_key_list("") == []


def test_spaces_are_trimmed() -> None:
    assert parse_key_list("a, b") == ["a", "b"]
""",
        imports="from key_lists import parse_key_list\n",
    ),
    _spec(
        "d3r_parsing.is_identifier",
        _PARSING,
        "identifier_rules",
        "Deciding whether a label may be used as an identifier.",
        "is_identifier() accepts labels that start with a digit.",
        "is_identifier(label) accepts a non-empty label of letters, digits and underscores that "
        "does not start with a digit.",
        "the check tests the characters but never the first one",
        """def is_identifier(label):
    if not label:
        return False
    return all(part.isalnum() or part == "_" for part in label)""",
        """def is_identifier(label):
    if not label:
        return False
    if label[0].isdigit():
        return False
    return all(part.isalnum() or part == "_" for part in label)""",
        """
def test_a_leading_digit_is_refused() -> None:
    assert is_identifier("1a") is False


def test_an_underscore_start_is_allowed() -> None:
    assert is_identifier("_a") is True
""",
        imports="from identifier_rules import is_identifier\n",
    ),
    _spec(
        "d3r_parsing.parse_port",
        _PARSING,
        "port_numbers",
        "Reading a network port from text.",
        "parse_port() accepts ports outside the permitted range.",
        "parse_port(text) returns a port between 1 and 65535 and refuses anything else.",
        "the conversion succeeds and the range is never checked",
        """def parse_port(text):
    port = int(text)
    return port""",
        """def parse_port(text):
    port = int(text)
    if not 1 <= port <= 65535:
        raise ValueError(f"port out of range: {text!r}")
    return port""",
        """
import pytest

from port_numbers import parse_port


def test_a_valid_port() -> None:
    assert parse_port("8080") == 8080


def test_a_port_above_the_range_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_port("70000")
""",
        imports="",
    ),
    _spec(
        "d3r_parsing.trim_comment",
        _PARSING,
        "comment_trimming",
        "Dropping a trailing comment from a configuration line.",
        "trim_comment() cuts inside quoted text that contains a hash.",
        "trim_comment(line) drops a trailing comment but never one inside a quoted value.",
        "it splits on the hash without tracking whether it is inside quotes",
        """def trim_comment(line):
    return line.split("#", 1)[0].rstrip()""",
        """def trim_comment(line):
    inside = False
    for position, letter in enumerate(line):
        if letter == '"':
            inside = not inside
        elif letter == "#" and not inside:
            return line[:position].rstrip()
    return line.rstrip()""",
        """
def test_a_hash_inside_quotes_survives() -> None:
    assert trim_comment('name = "a#b"  # note') == 'name = "a#b"'
""",
        imports="from comment_trimming import trim_comment\n",
    ),
    _spec(
        "d3r_parsing.parse_bool_word",
        _PARSING,
        "bool_words",
        "Reading a truth value written as a word.",
        "parse_bool_word() treats every unknown word as false.",
        "parse_bool_word(word) maps the known words and raises ValueError for anything else.",
        "the mapping falls back to False rather than refusing an unknown word",
        """def parse_bool_word(word):
    return word.strip().lower() in {"yes", "true", "on", "1"}""",
        """def parse_bool_word(word):
    cleaned = word.strip().lower()
    if cleaned in {"yes", "true", "on", "1"}:
        return True
    if cleaned in {"no", "false", "off", "0"}:
        return False
    raise ValueError(f"not a truth value: {word!r}")""",
        """
import pytest

from bool_words import parse_bool_word


def test_a_known_false_word() -> None:
    assert parse_bool_word("off") is False


def test_an_unknown_word_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_bool_word("maybe")
""",
        imports="",
    ),
    _spec(
        "d3r_parsing.expand_range_text",
        _PARSING,
        "range_text",
        "Reading a numeric range written with a dash.",
        "expand_range_text() drops the final value of the range.",
        "expand_range_text(text) returns every value from the first bound to the last inclusive.",
        "the range stops one short because the upper bound is exclusive",
        """def expand_range_text(text):
    low, high = (int(piece) for piece in text.split("-"))
    return list(range(low, high))""",
        """def expand_range_text(text):
    low, high = (int(piece) for piece in text.split("-"))
    return list(range(low, high + 1))""",
        """
def test_the_upper_bound_is_included() -> None:
    assert expand_range_text("2-4") == [2, 3, 4]
""",
        imports="from range_text import expand_range_text\n",
    ),
    # -------------------------------------------------------------- state and idempotency
    _spec(
        "d3r_state.register_once",
        _STATE,
        "single_registration",
        "Registering a handler at most once.",
        "register_once() appends the same handler twice when it is registered again.",
        "register_once(registry, handler) records the handler once however often it is called.",
        "it appends without checking whether the handler is already registered",
        """def register_once(registry, handler):
    registry += [handler]
    return registry""",
        """def register_once(registry, handler):
    if handler in registry:
        return registry
    registry.append(handler)
    return registry""",
        """
def test_a_repeated_registration_is_a_no_op() -> None:
    registry = []
    register_once(registry, "a")
    register_once(registry, "a")
    assert registry == ["a"]
""",
        imports="from single_registration import register_once\n",
    ),
    _spec(
        "d3r_state.release_lock",
        _STATE,
        "lock_release",
        "Releasing a lock a caller may not hold.",
        "release_lock() crashes when the lock was never taken.",
        "release_lock(locks, name) releases the lock when held and reports whether it did.",
        "it deletes the key without checking that it is there",
        """def release_lock(locks, name):
    del locks[name]
    return True""",
        """def release_lock(locks, name):
    if name not in locks:
        return False
    del locks[name]
    return True""",
        """
def test_releasing_an_untaken_lock_reports_false() -> None:
    assert release_lock({}, "a") is False
""",
        imports="from lock_release import release_lock\n",
    ),
    _spec(
        "d3r_state.increment_counter",
        _STATE,
        "counter_bumping",
        "Increasing a named counter.",
        "increment_counter() crashes the first time a counter is used.",
        "increment_counter(counters, name) starts an unseen counter at zero before increasing it.",
        "the lookup assumes the key exists",
        """def increment_counter(counters, name):
    counters[name] += 1
    return counters[name]""",
        """def increment_counter(counters, name):
    counters[name] = counters.get(name, 0) + 1
    return counters[name]""",
        """
def test_an_unseen_counter_starts_at_zero() -> None:
    assert increment_counter({}, "a") == 1
""",
        imports="from counter_bumping import increment_counter\n",
    ),
    _spec(
        "d3r_state.close_twice",
        _STATE,
        "idempotent_close",
        "Closing a resource that may already be closed.",
        "close_twice() reports a second close as a fresh one.",
        "close_resource(state) closes an open resource and reports False for one that is "
        "already closed.",
        "it sets the flag and reports success without reading the previous state",
        """def close_resource(state):
    state["open"] = False
    return True""",
        """def close_resource(state):
    if not state.get("open", False):
        return False
    state["open"] = False
    return True""",
        """
def test_a_second_close_reports_false() -> None:
    state = {"open": True}
    assert close_resource(state) is True
    assert close_resource(state) is False
""",
        imports="from idempotent_close import close_resource\n",
    ),
    _spec(
        "d3r_state.apply_migration",
        _STATE,
        "migration_steps",
        "Applying a migration step only when it is new.",
        "apply_migration() re-applies a step that has already run.",
        "apply_migration(applied, name, step) runs a named step once and records the name.",
        "the recorded set is consulted after the step has already run",
        """def apply_migration(applied, name, step):
    step()
    applied.add(name)
    return name""",
        """def apply_migration(applied, name, step):
    if name in applied:
        return name
    step()
    applied.add(name)
    return name""",
        """
def test_a_recorded_step_does_not_run_again() -> None:
    calls = []
    applied = set()
    apply_migration(applied, "one", lambda: calls.append(1))
    apply_migration(applied, "one", lambda: calls.append(1))
    assert len(calls) == 1
""",
        imports="from migration_steps import apply_migration\n",
    ),
    _spec(
        "d3r_state.touch_entry",
        _STATE,
        "entry_touching",
        "Recording that an entry was seen.",
        "touch_entry() overwrites the first-seen stamp on every touch.",
        "touch_entry(entries, name, stamp) keeps the first stamp and updates the last one.",
        "both stamps are written on every call",
        """def touch_entry(entries, name, stamp):
    entries[name] = {"first": stamp, "last": stamp}
    return entries[name]""",
        """def touch_entry(entries, name, stamp):
    entry = entries.setdefault(name, {"first": stamp, "last": stamp})
    entry["last"] = stamp
    return entry""",
        """
def test_the_first_stamp_survives_a_second_touch() -> None:
    entries = {}
    touch_entry(entries, "a", 1)
    touch_entry(entries, "a", 5)
    assert entries["a"] == {"first": 1, "last": 5}
""",
        imports="from entry_touching import touch_entry\n",
    ),
    _spec(
        "d3r_state.drain_queue",
        _STATE,
        "queue_draining",
        "Draining a queue into a list.",
        "drain_queue() leaves the queue holding the items it returned.",
        "drain_queue(queue) returns every queued item and leaves the queue empty.",
        "it copies the queue instead of consuming it",
        """def drain_queue(queue):
    return [item for item in queue]""",
        """def drain_queue(queue):
    drained = list(queue)
    queue.clear()
    return drained""",
        """
def test_the_queue_is_empty_afterwards() -> None:
    queue = [1, 2]
    assert drain_queue(queue) == [1, 2]
    assert queue == []
""",
        imports="from queue_draining import drain_queue\n",
    ),
    _spec(
        "d3r_state.bump_revision",
        _STATE,
        "revision_bumping",
        "Bumping a revision only when something changed.",
        "bump_revision() bumps even when the payload is unchanged.",
        "bump_revision(record, payload) bumps the revision only for a changed payload.",
        "the revision is increased before the payload is compared",
        """def bump_revision(record, payload):
    record["revision"] += 1
    record["payload"] = payload
    return record["revision"]""",
        """def bump_revision(record, payload):
    if record.get("payload") == payload:
        return record["revision"]
    record["revision"] += 1
    record["payload"] = payload
    return record["revision"]""",
        """
def test_an_unchanged_payload_does_not_bump() -> None:
    record = {"revision": 1, "payload": "a"}
    assert bump_revision(record, "a") == 1
""",
        imports="from revision_bumping import bump_revision\n",
    ),
    _spec(
        "d3r_state.reserve_capacity",
        _STATE,
        "capacity_reserving",
        "Reserving capacity that may not be there.",
        "reserve_capacity() lets the free pool go negative.",
        "reserve_capacity(pool, amount) reserves only what is available and reports the result.",
        "the subtraction happens before the availability check",
        """def reserve_capacity(pool, amount):
    pool["free"] -= amount
    return True""",
        """def reserve_capacity(pool, amount):
    if amount > pool["free"]:
        return False
    pool["free"] -= amount
    return True""",
        """
def test_an_oversized_reservation_is_refused() -> None:
    pool = {"free": 2}
    assert reserve_capacity(pool, 5) is False
    assert pool["free"] == 2
""",
        imports="from capacity_reserving import reserve_capacity\n",
    ),
    _spec(
        "d3r_state.forget_expired",
        _STATE,
        "expiry_sweeping",
        "Forgetting sessions that have run out.",
        "forget_expired() mutates the mapping while it is walking it.",
        "forget_expired(sessions, now) removes the expired sessions and returns their names.",
        "the dictionary is deleted from inside its own iteration",
        """def forget_expired(sessions, now):
    gone = []
    for name, deadline in sessions.items():
        if deadline < now:
            del sessions[name]
            gone.append(name)
    return gone""",
        """def forget_expired(sessions, now):
    gone = [name for name, deadline in sessions.items() if deadline < now]
    for name in gone:
        del sessions[name]
    return gone""",
        """
def test_expired_sessions_are_removed() -> None:
    sessions = {"a": 1, "b": 9}
    assert forget_expired(sessions, 5) == ["a"]
    assert sessions == {"b": 9}
""",
        imports="from expiry_sweeping import forget_expired\n",
    ),
    # -------------------------------------------------------------------- numeric logic
    _spec(
        "d3r_numeric.percent_of",
        _NUMERIC,
        "percentages",
        "Reporting a value as a percentage of a whole.",
        "percent_of() crashes when the whole is zero.",
        "percent_of(part, whole) returns the percentage, and 0.0 when the whole is zero.",
        "the division has no guard",
        """def percent_of(part, whole):
    return 100 * (part / whole)""",
        """def percent_of(part, whole):
    if whole == 0:
        return 0.0
    return part / whole * 100""",
        """
def test_a_zero_whole_gives_zero() -> None:
    assert percent_of(3, 0) == 0.0
""",
        imports="from percentages import percent_of\n",
    ),
    _spec(
        "d3r_numeric.mean_of",
        _NUMERIC,
        "arithmetic_mean",
        "The arithmetic mean of a sample.",
        "mean_of() crashes on an empty sample.",
        "mean_of(values) returns the mean, and 0.0 for an empty sample.",
        "the length is used as a divisor without being checked",
        """def mean_of(values):
    collected = list(values)
    return sum(collected) / len(collected)""",
        """def mean_of(values):
    collected = list(values)
    if not collected:
        return 0.0
    return sum(collected) / len(collected)""",
        """
def test_an_empty_sample_has_a_mean_of_zero() -> None:
    assert mean_of([]) == 0.0
""",
        imports="from arithmetic_mean import mean_of\n",
    ),
    _spec(
        "d3r_numeric.clamp_between",
        _NUMERIC,
        "value_clamping",
        "Holding a value inside a range.",
        "clamp_between() returns the wrong bound when the caller swaps them.",
        "clamp_between(value, low, high) clamps into the range whichever way round it was given.",
        "the bounds are used in the order they arrive",
        """def clamp_between(value, low, high):
    return max(low, min(high, value))""",
        """def clamp_between(value, low, high):
    lower, upper = sorted((low, high))
    return max(lower, min(upper, value))""",
        """
def test_swapped_bounds_still_clamp() -> None:
    assert clamp_between(5, 9, 1) == 5
""",
        imports="from value_clamping import clamp_between\n",
    ),
    _spec(
        "d3r_numeric.ceil_divide",
        _NUMERIC,
        "ceiling_division",
        "Dividing and rounding up.",
        "ceil_divide() rounds down for an exact division of negatives.",
        "ceil_divide(total, size) returns the smallest count of size that covers total.",
        "float division loses precision for large integers",
        """def ceil_divide(total, size):
    import math

    return int(math.ceil(total / size))""",
        """def ceil_divide(total, size):
    return -(-total // size)""",
        """
def test_large_integers_stay_exact() -> None:
    assert ceil_divide(10**18 + 1, 10**18) == 2
""",
        imports="from ceiling_division import ceil_divide\n",
    ),
    _spec(
        "d3r_numeric.running_max",
        _NUMERIC,
        "running_maximum",
        "The running maximum of a series.",
        "running_max() starts from zero instead of from the first reading.",
        "running_max(values) returns the maximum seen so far at each position.",
        "the accumulator is seeded with zero rather than with the first value",
        """def running_max(values):
    best = 0
    seen = []
    for value in values:
        best = max(best, value)
        seen.append(best)
    return seen""",
        """def running_max(values):
    best = None
    seen = []
    for value in values:
        best = value if best is None else max(best, value)
        seen.append(best)
    return seen""",
        """
def test_a_negative_series_does_not_see_zero() -> None:
    assert running_max([-3, -5]) == [-3, -3]
""",
        imports="from running_maximum import running_max\n",
    ),
    _spec(
        "d3r_numeric.sum_positive",
        _NUMERIC,
        "positive_sums",
        "Adding up only the positive readings.",
        "sum_positive() adds every reading rather than only the positive ones.",
        "sum_positive(values) adds the readings strictly above zero.",
        "the filter is missing altogether",
        """def sum_positive(values):
    return sum(value for value in values)""",
        """def sum_positive(values):
    return sum(value for value in values if value > 0)""",
        """
def test_zero_is_not_positive() -> None:
    assert sum_positive([0, 2, -1]) == 2
""",
        imports="from positive_sums import sum_positive\n",
    ),
    _spec(
        "d3r_numeric.scale_series",
        _NUMERIC,
        "series_scaling",
        "Scaling a series onto the unit interval.",
        "scale_series() crashes when every reading is the same.",
        "scale_series(values) scales onto zero-to-one, returning zeros for a flat series.",
        "the span is used as a divisor without being checked for zero",
        """def scale_series(values):
    collected = list(values)
    low = min(collected)
    span = max(collected) - low
    return [(value - low) / span for value in collected]""",
        """def scale_series(values):
    collected = list(values)
    low = min(collected)
    span = max(collected) - low
    if span == 0:
        return [0.0 for _ in collected]
    return [(value - low) / span for value in collected]""",
        """
def test_a_flat_series_scales_to_zeros() -> None:
    assert scale_series([2, 2]) == [0.0, 0.0]
""",
        imports="from series_scaling import scale_series\n",
    ),
    _spec(
        "d3r_numeric.compound_growth",
        _NUMERIC,
        "growth_compounding",
        "Compounding a growth rate over periods.",
        "compound_growth() compounds one period too many.",
        "compound_growth(start, rate, periods) applies the rate exactly periods times.",
        "the loop bound is off by one",
        """def compound_growth(start, rate, periods):
    value = start
    for _ in range(periods + 1):
        value = value * (1 + rate)
    return value""",
        """def compound_growth(start, rate, periods):
    value = start
    for _ in range(periods):
        value = value * (1 + rate)
    return value""",
        """
def test_zero_periods_leave_the_start_alone() -> None:
    assert compound_growth(100, 0.1, 0) == 100
""",
        imports="from growth_compounding import compound_growth\n",
    ),
    _spec(
        "d3r_numeric.digit_sum",
        _NUMERIC,
        "digit_sums",
        "Adding the digits of an integer.",
        "digit_sum() crashes on a negative number.",
        "digit_sum(number) adds the digits of the magnitude of the number.",
        "the sign character reaches int()",
        """def digit_sum(number):
    total = 0
    for digit in str(number):
        total += int(digit)
    return total""",
        """def digit_sum(number):
    total = 0
    for digit in str(abs(number)):
        total += int(digit)
    return total""",
        """
def test_a_negative_number_uses_its_magnitude() -> None:
    assert digit_sum(-123) == 6
""",
        imports="from digit_sums import digit_sum\n",
    ),
    _spec(
        "d3r_numeric.median_of",
        _NUMERIC,
        "median_values",
        "The median of a sample.",
        "median_of() reports the upper middle value for an even sample.",
        "median_of(values) averages the two middle values of an even sample.",
        "the even case picks one element instead of averaging two",
        """def median_of(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    return ordered[middle]""",
        """def median_of(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2""",
        """
def test_an_even_sample_averages_the_middle_pair() -> None:
    assert median_of([1, 2, 3, 4]) == 2.5
""",
        imports="from median_values import median_of\n",
    ),
    # ------------------------------------------------------------------- error handling
    _spec(
        "d3r_errors.lookup_or_raise",
        _ERRORS,
        "strict_lookup",
        "Looking a key up strictly.",
        "lookup_or_raise() raises KeyError where the contract promises a domain error.",
        "lookup_or_raise(mapping, key) raises LookupError with the key in its message.",
        "the raw subscript escapes instead of being translated",
        """def lookup_or_raise(mapping, key):
    return mapping[key]""",
        """def lookup_or_raise(mapping, key):
    try:
        return mapping[key]
    except KeyError as error:
        raise LookupError(f"unknown key: {key!r}") from error""",
        """
import pytest

from strict_lookup import lookup_or_raise


def test_an_unknown_key_reports_itself() -> None:
    with pytest.raises(LookupError, match="unknown key"):
        lookup_or_raise({}, "zed")
""",
        imports="",
    ),
    _spec(
        "d3r_errors.close_all_quietly",
        _ERRORS,
        "quiet_closing",
        "Closing every resource even when one fails.",
        "close_all_quietly() stops at the first resource that raises.",
        "close_all_quietly(resources) closes every resource and reports how many failed.",
        "the loop has no guard around the individual close",
        """def close_all_quietly(resources):
    failures = 0
    for resource in resources:
        resource.close()
    return failures""",
        """def close_all_quietly(resources):
    failures = 0
    for resource in resources:
        try:
            resource.close()
        except Exception:
            failures += 1
    return failures""",
        """
class Boom:
    def close(self):
        raise RuntimeError("no")


class Fine:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_a_failing_close_does_not_stop_the_rest() -> None:
    fine = Fine()
    assert close_all_quietly([Boom(), fine]) == 1
    assert fine.closed is True
""",
        imports="from quiet_closing import close_all_quietly\n",
    ),
    _spec(
        "d3r_errors.default_on_error",
        _ERRORS,
        "error_defaults",
        "Falling back to a default when a call fails.",
        "default_on_error() swallows KeyboardInterrupt along with real failures.",
        "default_on_error(action, default) falls back for ordinary failures only.",
        "a bare except catches the control-flow exceptions too",
        """def default_on_error(action, default):
    try:
        return action()
    except BaseException:
        return default""",
        """def default_on_error(action, default):
    try:
        return action()
    except Exception:
        return default""",
        """
import pytest

from error_defaults import default_on_error


def test_a_keyboard_interrupt_is_not_swallowed() -> None:
    def action():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        default_on_error(action, "fallback")
""",
        imports="",
    ),
    _spec(
        "d3r_errors.require_fields",
        _ERRORS,
        "field_requirements",
        "Refusing a record that is missing fields.",
        "require_fields() names only the first missing field.",
        "require_fields(record, fields) names every missing field in one error.",
        "it raises inside the loop instead of collecting first",
        """def require_fields(record, fields):
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError(f"missing: {missing[0]}")
    return record""",
        """def require_fields(record, fields):
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError(f"missing: {', '.join(sorted(missing))}")
    return record""",
        """
import pytest

from field_requirements import require_fields


def test_every_missing_field_is_named() -> None:
    with pytest.raises(ValueError, match="a, b"):
        require_fields({}, ["a", "b"])
""",
        imports="",
    ),
    _spec(
        "d3r_errors.wrap_timeout",
        _ERRORS,
        "timeout_wrapping",
        "Reporting a timeout as a domain error.",
        "wrap_timeout() loses the original error as a cause.",
        "wrap_timeout(action) raises TimeoutError chained to the original failure.",
        "the re-raise drops the cause",
        """def wrap_timeout(action):
    try:
        return action()
    except OSError:
        raise TimeoutError("timed out")""",
        """def wrap_timeout(action):
    try:
        return action()
    except OSError as error:
        raise TimeoutError("timed out") from error""",
        """
import pytest

from timeout_wrapping import wrap_timeout


def test_the_original_failure_is_the_cause() -> None:
    def action():
        raise OSError("socket")

    with pytest.raises(TimeoutError) as caught:
        wrap_timeout(action)
    assert isinstance(caught.value.__cause__, OSError)
""",
        imports="",
    ),
    _spec(
        "d3r_errors.retry_with_backoff",
        _ERRORS,
        "backoff_retry",
        "Retrying with a growing pause.",
        "retry_with_backoff() pauses after the final attempt as well.",
        "retry_with_backoff(action, attempts, pause) pauses only between attempts.",
        "the pause is unconditional inside the loop",
        """def retry_with_backoff(action, attempts, pause):
    waits = []
    for index in range(attempts):
        try:
            return action(), waits
        except Exception:
            waits.append(pause * (index + 1))
    return None, waits""",
        """def retry_with_backoff(action, attempts, pause):
    waits = []
    for index in range(attempts):
        try:
            return action(), waits
        except Exception:
            if index + 1 < attempts:
                waits.append(pause * (index + 1))
    return None, waits""",
        """
def test_no_pause_follows_the_final_attempt() -> None:
    def action():
        raise RuntimeError("no")

    assert retry_with_backoff(action, 2, 1) == (None, [1])
""",
        imports="from backoff_retry import retry_with_backoff\n",
    ),
    _spec(
        "d3r_errors.split_results",
        _ERRORS,
        "result_splitting",
        "Separating the successes from the failures.",
        "split_results() reports a failure as a success when it is falsy.",
        "split_results(results) splits on the recorded outcome flag, not on truthiness.",
        "the partition tests the value rather than the flag",
        """def split_results(results):
    good = [value for ok, value in results if value]
    bad = [value for ok, value in results if not value]
    return good, bad""",
        """def split_results(results):
    good = [value for ok, value in results if ok]
    bad = [value for ok, value in results if not ok]
    return good, bad""",
        """
def test_a_falsy_success_stays_a_success() -> None:
    assert split_results([(True, 0), (False, 9)]) == ([0], [9])
""",
        imports="from result_splitting import split_results\n",
    ),
    _spec(
        "d3r_errors.guard_division",
        _ERRORS,
        "guarded_division",
        "Dividing with a guarded fallback.",
        "guard_division() returns the fallback for a valid division that yields zero.",
        "guard_division(top, bottom, fallback) falls back only when the divisor is zero.",
        "the fallback is chosen by testing the result instead of the divisor",
        """def guard_division(top, bottom, fallback):
    result = top / bottom if bottom else None
    return result or fallback""",
        """def guard_division(top, bottom, fallback):
    if bottom == 0:
        return fallback
    return top / bottom""",
        """
def test_a_zero_result_is_not_a_failure() -> None:
    assert guard_division(0, 4, "fallback") == 0.0
""",
        imports="from guarded_division import guard_division\n",
    ),
    _spec(
        "d3r_errors.collect_errors",
        _ERRORS,
        "error_collection",
        "Running every check and collecting what failed.",
        "collect_errors() stops running checks after the first failure.",
        "collect_errors(checks, value) runs every check and returns each failure message.",
        "the generator short-circuits on the first failure",
        """def collect_errors(checks, value):
    for check in checks:
        problem = check(value)
        if problem:
            return [problem]
    return []""",
        """def collect_errors(checks, value):
    problems = []
    for check in checks:
        problem = check(value)
        if problem:
            problems.append(problem)
    return problems""",
        """
def test_every_failing_check_is_reported() -> None:
    checks = [lambda value: "a", lambda value: "b"]
    assert collect_errors(checks, 1) == ["a", "b"]
""",
        imports="from error_collection import collect_errors\n",
    ),
    _spec(
        "d3r_errors.exit_status",
        _ERRORS,
        "exit_status",
        "Turning a result into a process exit status.",
        "exit_status() reports success for a run that produced warnings and errors.",
        "exit_status(report) returns 0 only when the report holds no errors.",
        "it reads the wrong counter",
        """def exit_status(report):
    return 0 if report.get("warnings", 0) == 0 else 1""",
        """def exit_status(report):
    return 0 if report.get("errors", 0) == 0 else 1""",
        """
def test_errors_decide_the_status() -> None:
    assert exit_status({"warnings": 0, "errors": 2}) == 1
""",
        imports="from exit_status import exit_status\n",
    ),
    # ---------------------------------------------------------------- data transformation
    _spec(
        "d3r_transform.invert_mapping",
        _TRANSFORM,
        "mapping_inversion",
        "Inverting a mapping.",
        "invert_mapping() keeps the last key for a repeated value instead of the first.",
        "invert_mapping(mapping) maps each value to the first key that carried it.",
        "later keys overwrite earlier ones",
        """def invert_mapping(mapping):
    return dict((value, key) for key, value in mapping.items())""",
        """def invert_mapping(mapping):
    inverted = {}
    for key, value in mapping.items():
        inverted.setdefault(value, key)
    return inverted""",
        """
def test_the_first_key_wins() -> None:
    assert invert_mapping({"a": 1, "b": 1}) == {1: "a"}
""",
        imports="from mapping_inversion import invert_mapping\n",
    ),
    _spec(
        "d3r_transform.group_pairs",
        _TRANSFORM,
        "pair_grouping",
        "Grouping pairs by their first element.",
        "group_pairs() keeps only the last value for each key.",
        "group_pairs(pairs) collects every value under its key, in order.",
        "assignment replaces the list instead of extending it",
        """def group_pairs(pairs):
    grouped = {}
    for key, value in pairs:
        grouped[key] = [value]
    return grouped""",
        """def group_pairs(pairs):
    grouped = {}
    for key, value in pairs:
        grouped.setdefault(key, []).append(value)
    return grouped""",
        """
def test_every_value_is_collected() -> None:
    assert group_pairs([("a", 1), ("a", 2)]) == {"a": [1, 2]}
""",
        imports="from pair_grouping import group_pairs\n",
    ),
    _spec(
        "d3r_transform.flatten_nested",
        _TRANSFORM,
        "nested_flattening",
        "Flattening one level of nesting.",
        "flatten_nested() flattens strings into their characters.",
        "flatten_nested(items) flattens lists and tuples and leaves text alone.",
        "text is iterable, and the check only asks whether an item can be iterated",
        """def flatten_nested(items):
    flat = []
    for item in items:
        try:
            flat.extend(iter(item))
        except TypeError:
            flat.append(item)
    return flat""",
        """def flatten_nested(items):
    flat = []
    for item in items:
        if isinstance(item, list | tuple):
            flat.extend(item)
        else:
            flat.append(item)
    return flat""",
        """
def test_text_is_not_split_into_characters() -> None:
    assert flatten_nested([[1], "ab"]) == [1, "ab"]
""",
        imports="from nested_flattening import flatten_nested\n",
    ),
    _spec(
        "d3r_transform.rename_columns",
        _TRANSFORM,
        "column_renaming",
        "Renaming the columns of a record.",
        "rename_columns() drops the columns that have no new name.",
        "rename_columns(record, names) renames the named columns and keeps the rest.",
        "the comprehension iterates the rename table rather than the record",
        """def rename_columns(record, names):
    return {names[key]: value for key, value in record.items() if key in names}""",
        """def rename_columns(record, names):
    return {names.get(key, key): value for key, value in record.items()}""",
        """
def test_unnamed_columns_survive() -> None:
    assert rename_columns({"a": 1, "b": 2}, {"a": "x"}) == {"x": 1, "b": 2}
""",
        imports="from column_renaming import rename_columns\n",
    ),
    _spec(
        "d3r_transform.dedupe_stable",
        _TRANSFORM,
        "stable_dedupe",
        "Removing duplicates without reordering.",
        "dedupe_stable() returns the items in an arbitrary order.",
        "dedupe_stable(items) keeps the first occurrence of each item, in order.",
        "a set loses the ordering the contract promises",
        """def dedupe_stable(items):
    unique = set(items)
    return sorted(unique)""",
        """def dedupe_stable(items):
    seen = {}
    for item in items:
        seen[item] = None
    return list(seen)""",
        """
def test_the_first_occurrences_keep_their_order() -> None:
    assert dedupe_stable([3, 1, 3, 2]) == [3, 1, 2]
""",
        imports="from stable_dedupe import dedupe_stable\n",
    ),
    _spec(
        "d3r_transform.to_columns",
        _TRANSFORM,
        "record_columns",
        "Turning records into columns.",
        "to_columns() drops a column that is missing from the first record.",
        "to_columns(records) reports every column any record carries, filling gaps with None.",
        "the column set comes from the first record only",
        """def to_columns(records):
    if not records:
        return {}
    names = list(records[0])
    return {name: [record.get(name) for record in records] for name in names}""",
        """def to_columns(records):
    names = list(dict.fromkeys(name for record in records for name in record))
    return {name: [record.get(name) for record in records] for name in names}""",
        """
def test_a_later_column_is_not_lost() -> None:
    assert to_columns([{"a": 1}, {"b": 2}]) == {"a": [1, None], "b": [None, 2]}
""",
        imports="from record_columns import to_columns\n",
    ),
    _spec(
        "d3r_transform.sum_by_key",
        _TRANSFORM,
        "keyed_sums",
        "Adding values up by key.",
        "sum_by_key() replaces the running total instead of adding to it.",
        "sum_by_key(pairs) returns the total per key.",
        "the accumulator is assigned rather than increased",
        """def sum_by_key(pairs):
    totals = {}
    for key, value in pairs:
        totals[key] = value
    return totals""",
        """def sum_by_key(pairs):
    totals = {}
    for key, value in pairs:
        totals[key] = totals.get(key, 0) + value
    return totals""",
        """
def test_values_under_one_key_are_added() -> None:
    assert sum_by_key([("a", 1), ("a", 2)]) == {"a": 3}
""",
        imports="from keyed_sums import sum_by_key\n",
    ),
    _spec(
        "d3r_transform.order_by_rank",
        _TRANSFORM,
        "rank_ordering",
        "Ordering records by a declared rank.",
        "order_by_rank() puts the unranked records first instead of last.",
        "order_by_rank(records, ranks) orders by rank and puts unranked records at the end.",
        "a missing rank sorts as zero rather than as the largest possible rank",
        """def order_by_rank(records, ranks):
    return sorted(records, key=lambda record: ranks.get(record, 0))""",
        """def order_by_rank(records, ranks):
    limit = len(records) + len(ranks) + 1
    return sorted(records, key=lambda record: ranks.get(record, limit))""",
        """
def test_unranked_records_go_last() -> None:
    assert order_by_rank(["a", "b"], {"b": 1}) == ["b", "a"]
""",
        imports="from rank_ordering import order_by_rank\n",
    ),
    _spec(
        "d3r_transform.merge_deep",
        _TRANSFORM,
        "deep_merging",
        "Merging nested mappings.",
        "merge_deep() replaces a nested mapping instead of merging into it.",
        "merge_deep(base, extra) merges nested mappings one level down.",
        "the update is shallow",
        """def merge_deep(base, extra):
    return {**base, **extra}""",
        """def merge_deep(base, extra):
    merged = dict(base)
    for key, value in extra.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = merge_deep(current, value)
        else:
            merged[key] = value
    return merged""",
        """
def test_a_nested_mapping_is_merged() -> None:
    assert merge_deep({"a": {"x": 1}}, {"a": {"y": 2}}) == {"a": {"x": 1, "y": 2}}
""",
        imports="from deep_merging import merge_deep\n",
    ),
    _spec(
        "d3r_transform.zip_records",
        _TRANSFORM,
        "record_zipping",
        "Pairing two series into records.",
        "zip_records() silently drops the tail when the series differ in length.",
        "zip_records(names, values) refuses two series of different lengths.",
        "zip stops at the shorter series without saying so",
        """def zip_records(names, values):
    return [{"name": name, "value": value} for name, value in zip(names, values)]""",
        """def zip_records(names, values):
    if len(names) != len(values):
        raise ValueError("the two series have different lengths")
    return [{"name": name, "value": value} for name, value in zip(names, values)]""",
        """
import pytest

from record_zipping import zip_records


def test_mismatched_lengths_are_refused() -> None:
    with pytest.raises(ValueError):
        zip_records(["a", "b"], [1])
""",
        imports="",
    ),
)
