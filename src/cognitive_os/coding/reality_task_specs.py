"""The Sprint 21C3 task corpus: thirty repair tasks across six families, §3.1 and §8.1.

Every task is built to one recipe, and the recipe is what makes the corpus measurable rather
than merely large:

* the published contract has **two** independent edge cases the visible tests do not state;
* the **baseline fails both**, while passing every visible test — so the defect is invisible
  to anyone who only reads what the repository publishes;
* `incomplete_a` fixes the first and leaves the second broken;
* `incomplete_b` fixes the second and leaves the first broken;
* `correct_narrow` fixes both with the smallest edit;
* `correct_robust` fixes both with a materially different implementation.

The two incorrect candidates therefore fail *different* hidden tests, which is what §S21C3-030
asks for, and they rewrite the same function in incompatible ways, which is why the
universal-patch adversary in §S21C3-024 cannot assemble one patch that solves the corpus.

Nothing here is parameterised. Five variants of one template would share an AST shape, land in
one near-clone group, and quietly reduce a six-family corpus to six real problems — so each
task is written out, and the near-clone detector exists to prove they stayed distinct.

Every byte is project-owned and generated, which is why the rights answer is Apache-2.0. It is
still recorded per task and still an operator input, because ADR 0088 keeps redistribution
separate from openness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cognitive_os.domain.reality import RealityTaskDifficulty, RealityTaskFamily


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """One repair task as source text. Adding a task means adding one of these."""

    template_id: str
    family: RealityTaskFamily
    repository_group: str
    module: str
    module_doc: str
    issue: str
    expected: str
    baseline_reason: str
    baseline: str
    incomplete_a: str
    incomplete_b: str
    correct_narrow: str
    correct_robust: str
    visible_test: str
    hidden_test: str
    difficulty: RealityTaskDifficulty = RealityTaskDifficulty.SINGLE_EDIT
    imports: str = ""
    edge_cases: tuple[str, str] = field(default=("", ""))


def _test_module(module: str, doc: str, body: str, *, imports: str = "") -> str:
    header = f'"""{doc}"""\n\n'
    if imports:
        header += f"{imports}\n"
    return f"{header}\n{body.strip()}\n"


# --------------------------------------------------------------- boundary and collections

_B1 = TaskSpec(
    template_id="boundary_collections.first_match",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="boundary-sequence-head",
    module="sequence_head",
    module_doc="Helpers for reading the head of a sequence.",
    issue=(
        "first_match() is documented to return the first item of a sequence, falling back to "
        "the caller's default when the sequence is empty. Callers report that it returns None "
        "for sequences that are not empty, and that the default they passed is ignored."
    ),
    expected=(
        "first_match(items, default) returns items[0] for any non-empty sequence, including "
        "when that item is falsy, and returns default when the sequence is empty."
    ),
    baseline_reason=(
        "the loop skips falsy items and the fallback returns None instead of the caller's default"
    ),
    edge_cases=("empty sequence returns the caller's default", "a falsy first item is returned"),
    baseline="""def first_match(items, default=None):
    \"\"\"Return the first item of `items`, or `default` when there is none.\"\"\"
    for item in items:
        if item:
            return item
    return None""",
    incomplete_a="""def first_match(items, default=None):
    \"\"\"Return the first item of `items`, or `default` when there is none.\"\"\"
    for item in items:
        return item
    return None""",
    incomplete_b="""def first_match(items, default=None):
    \"\"\"Return the first item of `items`, or `default` when there is none.\"\"\"
    for item in items:
        if item:
            return item
    return default""",
    correct_narrow="""def first_match(items, default=None):
    \"\"\"Return the first item of `items`, or `default` when there is none.\"\"\"
    for item in items:
        return item
    return default""",
    correct_robust="""def first_match(items, default=None):
    \"\"\"Return the first item of `items`, or `default` when there is none.\"\"\"
    return next(iter(items), default)""",
    visible_test=_test_module(
        "sequence_head",
        "Published contract for the sequence head helpers.",
        """
def test_first_of_several() -> None:
    assert first_match([3, 4, 5]) == 3


def test_first_of_one() -> None:
    assert first_match(["only"]) == "only"


def test_first_of_a_tuple() -> None:
    assert first_match((7, 8)) == 7
""",
        imports="from sequence_head import first_match\n",
    ),
    hidden_test=_test_module(
        "sequence_head",
        "The part of the contract the published tests do not state.",
        """
def test_first_of_several() -> None:
    assert first_match([3, 4, 5]) == 3


def test_empty_sequence_returns_the_caller_default() -> None:
    assert first_match([], "fallback") == "fallback"


def test_empty_sequence_without_a_default_returns_none() -> None:
    assert first_match(()) is None


def test_a_falsy_first_item_is_returned_unchanged() -> None:
    assert first_match([0, 1, 2]) == 0


def test_an_empty_string_first_item_is_returned_unchanged() -> None:
    assert first_match(["", "x"]) == ""
""",
        imports="from sequence_head import first_match\n",
    ),
)

_B2 = TaskSpec(
    template_id="boundary_collections.take_last",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="boundary-sequence-tail",
    module="sequence_tail",
    module_doc="Helpers for reading the tail of a sequence.",
    issue=(
        "take_last() returns the whole sequence when it is asked for zero items, and silently "
        "returns something for a negative count instead of rejecting it."
    ),
    expected=(
        "take_last(items, n) returns the last n items, an empty list when n is 0, every item "
        "when n exceeds the length, and raises ValueError when n is negative."
    ),
    baseline_reason="a negative index slice makes n=0 return everything and n<0 return a suffix",
    edge_cases=("n of zero returns an empty list", "a negative n raises ValueError"),
    baseline="""def take_last(items, n):
    \"\"\"Return the last `n` items of `items` as a list.\"\"\"
    return list(items[-n:])""",
    incomplete_a="""def take_last(items, n):
    \"\"\"Return the last `n` items of `items` as a list.\"\"\"
    if n == 0:
        return []
    return list(items[-n:])""",
    incomplete_b="""def take_last(items, n):
    \"\"\"Return the last `n` items of `items` as a list.\"\"\"
    if n < 0:
        raise ValueError("take_last() cannot take a negative number of items")
    return list(items[-n:])""",
    correct_narrow="""def take_last(items, n):
    \"\"\"Return the last `n` items of `items` as a list.\"\"\"
    if n < 0:
        raise ValueError("take_last() cannot take a negative number of items")
    return list(items[max(0, len(items) - n):])""",
    correct_robust="""def take_last(items, n):
    \"\"\"Return the last `n` items of `items` as a list.\"\"\"
    if n < 0:
        raise ValueError("take_last() cannot take a negative number of items")
    if n == 0:
        return []
    kept = []
    for item in items:
        kept.append(item)
        if len(kept) > n:
            kept.pop(0)
    return kept""",
    visible_test=_test_module(
        "sequence_tail",
        "Published contract for the sequence tail helpers.",
        """
def test_take_two_of_four() -> None:
    assert take_last([1, 2, 3, 4], 2) == [3, 4]


def test_take_more_than_available() -> None:
    assert take_last([1, 2], 5) == [1, 2]


def test_take_all() -> None:
    assert take_last([1, 2, 3], 3) == [1, 2, 3]
""",
        imports="from sequence_tail import take_last\n",
    ),
    hidden_test=_test_module(
        "sequence_tail",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_take_two_of_four() -> None:
    assert take_last([1, 2, 3, 4], 2) == [3, 4]


def test_take_more_than_available() -> None:
    assert take_last([1, 2], 5) == [1, 2]


def test_taking_zero_items_returns_an_empty_list() -> None:
    assert take_last([1, 2, 3], 0) == []


def test_taking_zero_from_an_empty_sequence_returns_an_empty_list() -> None:
    assert take_last([], 0) == []


def test_a_negative_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        take_last([1, 2, 3], -1)
""",
        imports="from sequence_tail import take_last\n",
    ),
)

_B3 = TaskSpec(
    template_id="boundary_collections.chunk",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="boundary-chunking",
    module="chunking",
    module_doc="Split a sequence into fixed-size chunks.",
    issue=(
        "chunk() drops the final partial chunk, so callers silently lose the tail of every "
        "sequence whose length is not a multiple of the chunk size. It also accepts a chunk "
        "size of zero and returns nonsense rather than refusing."
    ),
    expected=(
        "chunk(items, size) returns consecutive chunks covering every item, with a shorter "
        "final chunk when needed, and raises ValueError when size is less than one."
    ),
    baseline_reason="the range stops one full chunk early and a non-positive size is not rejected",
    edge_cases=("the final partial chunk is included", "a size below one raises ValueError"),
    baseline="""def chunk(items, size):
    \"\"\"Split `items` into consecutive chunks of at most `size` items.\"\"\"
    step = size if size > 0 else 1
    return [list(items[index:index + size]) for index in range(0, len(items) - size + 1, step)]""",
    incomplete_a="""def chunk(items, size):
    \"\"\"Split `items` into consecutive chunks of at most `size` items.\"\"\"
    step = size if size > 0 else 1
    return [list(items[index:index + size]) for index in range(0, len(items), step)]""",
    incomplete_b="""def chunk(items, size):
    \"\"\"Split `items` into consecutive chunks of at most `size` items.\"\"\"
    if size < 1:
        raise ValueError("chunk() needs a size of at least one")
    return [list(items[index:index + size]) for index in range(0, len(items) - size + 1, size)]""",
    correct_narrow="""def chunk(items, size):
    \"\"\"Split `items` into consecutive chunks of at most `size` items.\"\"\"
    if size < 1:
        raise ValueError("chunk() needs a size of at least one")
    return [list(items[index:index + size]) for index in range(0, len(items), size)]""",
    correct_robust="""def chunk(items, size):
    \"\"\"Split `items` into consecutive chunks of at most `size` items.\"\"\"
    if size < 1:
        raise ValueError("chunk() needs a size of at least one")
    chunks = []
    current = []
    for item in items:
        current.append(item)
        if len(current) == size:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks""",
    visible_test=_test_module(
        "chunking",
        "Published contract for the chunking helper.",
        """
def test_exact_multiple() -> None:
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_single_chunk() -> None:
    assert chunk([1, 2], 2) == [[1, 2]]


def test_empty_input() -> None:
    assert chunk([], 3) == []
""",
        imports="from chunking import chunk\n",
    ),
    hidden_test=_test_module(
        "chunking",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_exact_multiple() -> None:
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_the_final_partial_chunk_is_kept() -> None:
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_every_item_survives_chunking() -> None:
    items = list(range(7))
    assert [item for group in chunk(items, 3) for item in group] == items


def test_a_size_of_zero_is_rejected() -> None:
    with pytest.raises(ValueError):
        chunk([1, 2, 3], 0)


def test_a_negative_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        chunk([1, 2, 3], -2)
""",
        imports="from chunking import chunk\n",
    ),
)

_B4 = TaskSpec(
    template_id="boundary_collections.dedupe",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="boundary-deduplication",
    module="deduplication",
    module_doc="Remove duplicates while keeping the original order.",
    issue=(
        "dedupe() is documented to keep the first occurrence of every item in the order it "
        "appeared. It returns items in sorted order instead, and drops zeros and empty "
        "strings entirely."
    ),
    expected=(
        "dedupe(items) returns each distinct item once, in first-appearance order, including "
        "falsy items."
    ),
    baseline_reason=(
        "a sorted set comprehension loses the order and a truthiness filter drops falsy items"
    ),
    edge_cases=("first-appearance order is preserved", "falsy items are kept"),
    baseline="""def dedupe(items):
    \"\"\"Return the distinct items of `items` in first-appearance order.\"\"\"
    return sorted({item for item in items if item})""",
    incomplete_a="""def dedupe(items):
    \"\"\"Return the distinct items of `items` in first-appearance order.\"\"\"
    seen = set()
    unique = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique""",
    incomplete_b="""def dedupe(items):
    \"\"\"Return the distinct items of `items` in first-appearance order.\"\"\"
    return sorted(set(items))""",
    correct_narrow="""def dedupe(items):
    \"\"\"Return the distinct items of `items` in first-appearance order.\"\"\"
    seen = set()
    unique = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique""",
    correct_robust="""def dedupe(items):
    \"\"\"Return the distinct items of `items` in first-appearance order.\"\"\"
    return list(dict.fromkeys(items))""",
    visible_test=_test_module(
        "deduplication",
        "Published contract for the deduplication helper.",
        """
def test_removes_repeats() -> None:
    assert dedupe([1, 2, 2, 3]) == [1, 2, 3]


def test_already_unique_ascending() -> None:
    assert dedupe([1, 2, 3]) == [1, 2, 3]


def test_empty_input() -> None:
    assert dedupe([]) == []
""",
        imports="from deduplication import dedupe\n",
    ),
    hidden_test=_test_module(
        "deduplication",
        "The part of the contract the published tests do not state.",
        """
def test_removes_repeats() -> None:
    assert dedupe([1, 2, 2, 3]) == [1, 2, 3]


def test_first_appearance_order_is_preserved() -> None:
    assert dedupe([3, 1, 3, 2]) == [3, 1, 2]


def test_descending_input_is_not_sorted() -> None:
    assert dedupe([9, 5, 1]) == [9, 5, 1]


def test_zero_is_kept() -> None:
    assert dedupe([0, 1, 0]) == [0, 1]


def test_an_empty_string_is_kept() -> None:
    assert dedupe(["", "a", ""]) == ["", "a"]
""",
        imports="from deduplication import dedupe\n",
    ),
)

_B5 = TaskSpec(
    template_id="boundary_collections.window_pairs",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="boundary-windowing",
    module="windowing",
    module_doc="Build sliding windows over a sequence.",
    issue=(
        "window_pairs() wraps around, so the last item is paired with the first and a "
        "one-item sequence produces a pair with itself. It also returns lists where the "
        "documented contract is tuples."
    ),
    expected=(
        "window_pairs(items) returns (items[i], items[i + 1]) tuples for consecutive items "
        "only, and an empty list for sequences shorter than two."
    ),
    baseline_reason="a modulo index wraps the window and the pairs are built as lists",
    edge_cases=("the window never wraps around", "each pair is a tuple"),
    baseline="""def window_pairs(items):
    \"\"\"Return consecutive (current, next) pairs from `items`.\"\"\"
    return [[items[index], items[(index + 1) % len(items)]] for index in range(len(items))]""",
    incomplete_a="""def window_pairs(items):
    \"\"\"Return consecutive (current, next) pairs from `items`.\"\"\"
    return [[items[index], items[index + 1]] for index in range(len(items) - 1)]""",
    incomplete_b="""def window_pairs(items):
    \"\"\"Return consecutive (current, next) pairs from `items`.\"\"\"
    return [(items[index], items[(index + 1) % len(items)]) for index in range(len(items))]""",
    correct_narrow="""def window_pairs(items):
    \"\"\"Return consecutive (current, next) pairs from `items`.\"\"\"
    return [(items[index], items[index + 1]) for index in range(len(items) - 1)]""",
    correct_robust="""def window_pairs(items):
    \"\"\"Return consecutive (current, next) pairs from `items`.\"\"\"
    sequence = list(items)
    return list(zip(sequence, sequence[1:], strict=False))""",
    visible_test=_test_module(
        "windowing",
        "Published contract for the windowing helper.",
        """
def test_first_pair_of_three() -> None:
    assert list(window_pairs([1, 2, 3])[0]) == [1, 2]


def test_second_pair_of_three() -> None:
    assert list(window_pairs([1, 2, 3])[1]) == [2, 3]


def test_empty_input() -> None:
    assert window_pairs([]) == []
""",
        imports="from windowing import window_pairs\n",
    ),
    hidden_test=_test_module(
        "windowing",
        "The part of the contract the published tests do not state.",
        """
def test_pairs_do_not_wrap_around() -> None:
    assert window_pairs([1, 2, 3]) == [(1, 2), (2, 3)]


def test_a_single_item_produces_no_pair() -> None:
    assert window_pairs([1]) == []


def test_empty_input_produces_no_pair() -> None:
    assert window_pairs([]) == []


def test_each_pair_is_a_tuple() -> None:
    assert all(isinstance(pair, tuple) for pair in window_pairs([1, 2, 3]))


def test_pair_count_is_one_less_than_the_input() -> None:
    assert len(window_pairs([1, 2, 3, 4])) == 3
""",
        imports="from windowing import window_pairs\n",
    ),
)


# ------------------------------------------------------------------- parsing and validation

_P1 = TaskSpec(
    template_id="parsing_validation.key_values",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="parsing-key-values",
    module="key_values",
    module_doc="Parse a comma-separated list of key=value pairs.",
    issue=(
        "parse_key_values() raises on input that ends with a separator, and on any value that "
        "itself contains an equals sign. Both shapes are produced by the upstream exporter."
    ),
    expected=(
        "parse_key_values(text) ignores blank segments and splits each segment on its first "
        "equals sign only, so a value may contain further equals signs."
    ),
    baseline_reason=(
        "an unbounded split rejects values containing '=' and blank segments are not skipped"
    ),
    edge_cases=("blank segments are ignored", "a value may contain an equals sign"),
    baseline="""def parse_key_values(text):
    \"\"\"Parse `text` into a dict of key to value.\"\"\"
    return dict(segment.split("=") for segment in text.split(","))""",
    incomplete_a="""def parse_key_values(text):
    \"\"\"Parse `text` into a dict of key to value.\"\"\"
    return dict(segment.split("=") for segment in text.split(",") if segment.strip())""",
    incomplete_b="""def parse_key_values(text):
    \"\"\"Parse `text` into a dict of key to value.\"\"\"
    return dict(segment.split("=", 1) for segment in text.split(","))""",
    correct_narrow="""def parse_key_values(text):
    \"\"\"Parse `text` into a dict of key to value.\"\"\"
    return dict(
        segment.split("=", 1) for segment in text.split(",") if segment.strip()
    )""",
    correct_robust="""def parse_key_values(text):
    \"\"\"Parse `text` into a dict of key to value.\"\"\"
    pairs = {}
    for segment in text.split(","):
        if not segment.strip():
            continue
        key, separator, value = segment.partition("=")
        if not separator:
            raise ValueError("each segment must contain an equals sign")
        pairs[key] = value
    return pairs""",
    visible_test=_test_module(
        "key_values",
        "Published contract for the key/value parser.",
        """
def test_two_pairs() -> None:
    assert parse_key_values("a=1,b=2") == {"a": "1", "b": "2"}


def test_single_pair() -> None:
    assert parse_key_values("mode=fast") == {"mode": "fast"}


def test_empty_value() -> None:
    assert parse_key_values("a=") == {"a": ""}
""",
        imports="from key_values import parse_key_values\n",
    ),
    hidden_test=_test_module(
        "key_values",
        "The part of the contract the published tests do not state.",
        """
def test_two_pairs() -> None:
    assert parse_key_values("a=1,b=2") == {"a": "1", "b": "2"}


def test_a_trailing_separator_is_ignored() -> None:
    assert parse_key_values("a=1,b=2,") == {"a": "1", "b": "2"}


def test_a_blank_segment_in_the_middle_is_ignored() -> None:
    assert parse_key_values("a=1,,b=2") == {"a": "1", "b": "2"}


def test_a_value_may_contain_an_equals_sign() -> None:
    assert parse_key_values("token=a=b") == {"token": "a=b"}


def test_a_base64_style_value_survives() -> None:
    assert parse_key_values("data=eyJhIjoxfQ==") == {"data": "eyJhIjoxfQ=="}
""",
        imports="from key_values import parse_key_values\n",
    ),
)

_P2 = TaskSpec(
    template_id="parsing_validation.parse_bool",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="parsing-booleans",
    module="booleans",
    module_doc="Parse textual boolean settings.",
    issue=(
        "parse_bool() treats every value it does not recognise as false, so a typo in a "
        "configuration file silently disables a feature instead of being reported. It is also "
        "case-sensitive, so 'True' from a Windows-generated file reads as false."
    ),
    expected=(
        "parse_bool(text) accepts 'true' and 'false' in any case with surrounding whitespace, "
        "and raises ValueError for anything else."
    ),
    baseline_reason=(
        "an exact string comparison is case-sensitive and maps every other value to false"
    ),
    edge_cases=("parsing is case-insensitive", "an unrecognised value raises ValueError"),
    baseline="""def parse_bool(text):
    \"\"\"Return the boolean `text` denotes.\"\"\"
    return text == "true\"""",
    incomplete_a="""def parse_bool(text):
    \"\"\"Return the boolean `text` denotes.\"\"\"
    return text.strip().lower() == "true\"""",
    incomplete_b="""def parse_bool(text):
    \"\"\"Return the boolean `text` denotes.\"\"\"
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(f"not a boolean: {text!r}")""",
    correct_narrow="""def parse_bool(text):
    \"\"\"Return the boolean `text` denotes.\"\"\"
    normalized = text.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"not a boolean: {text!r}")""",
    correct_robust="""def parse_bool(text):
    \"\"\"Return the boolean `text` denotes.\"\"\"
    known = {"true": True, "false": False}
    normalized = text.strip().lower()
    if normalized not in known:
        raise ValueError(f"not a boolean: {text!r}")
    return known[normalized]""",
    visible_test=_test_module(
        "booleans",
        "Published contract for the boolean parser.",
        """
def test_true() -> None:
    assert parse_bool("true") is True


def test_false() -> None:
    assert parse_bool("false") is False
""",
        imports="from booleans import parse_bool\n",
    ),
    hidden_test=_test_module(
        "booleans",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_true() -> None:
    assert parse_bool("true") is True


def test_uppercase_true() -> None:
    assert parse_bool("TRUE") is True


def test_mixed_case_false_with_whitespace() -> None:
    assert parse_bool("  False  ") is False


def test_an_unknown_word_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_an_empty_string_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_bool("")
""",
        imports="from booleans import parse_bool\n",
    ),
)

_P3 = TaskSpec(
    template_id="parsing_validation.split_fields",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="parsing-delimited-fields",
    module="delimited",
    module_doc="Split one delimited record into its fields.",
    imports="import csv\n",
    issue=(
        "split_fields() breaks a quoted field that contains the delimiter into two fields, and "
        "drops empty fields entirely, so a record's field count changes depending on its "
        "contents."
    ),
    expected=(
        "split_fields(line) honours double quotes around a field containing the delimiter, and "
        "keeps empty fields so the field count is stable."
    ),
    baseline_reason="a plain split ignores quoting and a truthiness filter removes empty fields",
    edge_cases=("a quoted delimiter stays inside its field", "empty fields are kept"),
    baseline="""def split_fields(line):
    \"\"\"Split one delimited record into a list of field values.\"\"\"
    return [field for field in line.split(",") if field]""",
    incomplete_a="""def split_fields(line):
    \"\"\"Split one delimited record into a list of field values.\"\"\"
    return line.split(",")""",
    incomplete_b="""def split_fields(line):
    \"\"\"Split one delimited record into a list of field values.\"\"\"
    return [field for field in next(csv.reader([line])) if field]""",
    correct_narrow="""def split_fields(line):
    \"\"\"Split one delimited record into a list of field values.\"\"\"
    return next(csv.reader([line]))""",
    correct_robust="""def split_fields(line):
    \"\"\"Split one delimited record into a list of field values.\"\"\"
    fields = []
    current = []
    quoted = False
    for character in line:
        if character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    fields.append("".join(current))
    return fields""",
    visible_test=_test_module(
        "delimited",
        "Published contract for the delimited record splitter.",
        """
def test_three_fields() -> None:
    assert split_fields("a,b,c") == ["a", "b", "c"]


def test_single_field() -> None:
    assert split_fields("only") == ["only"]


def test_numeric_fields_stay_text() -> None:
    assert split_fields("1,2") == ["1", "2"]
""",
        imports="from delimited import split_fields\n",
    ),
    hidden_test=_test_module(
        "delimited",
        "The part of the contract the published tests do not state.",
        """
def test_three_fields() -> None:
    assert split_fields("a,b,c") == ["a", "b", "c"]


def test_a_quoted_delimiter_stays_inside_its_field() -> None:
    assert split_fields('a,"b,c",d') == ["a", "b,c", "d"]


def test_a_quoted_field_loses_its_quotes() -> None:
    assert split_fields('"one"') == ["one"]


def test_a_trailing_empty_field_is_kept() -> None:
    assert split_fields("a,b,") == ["a", "b", ""]


def test_an_empty_field_in_the_middle_is_kept() -> None:
    assert split_fields("a,,c") == ["a", "", "c"]
""",
        imports="from delimited import split_fields\n",
    ),
)

_P4 = TaskSpec(
    template_id="parsing_validation.parse_version",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="parsing-versions",
    module="versions",
    module_doc="Parse dotted version strings into comparable tuples.",
    issue=(
        "parse_version() returns tuples of different lengths depending on how many components "
        "the caller wrote, so '1.2' and '1.2.0' do not compare equal. It also accepts four or "
        "more components without complaint."
    ),
    expected=(
        "parse_version(text) always returns a three-element tuple, padding missing components "
        "with zero, and raises ValueError for more than three components."
    ),
    baseline_reason=(
        "the component count is whatever the caller wrote and is never padded or bounded"
    ),
    edge_cases=(
        "a short version is padded to three components",
        "more than three components is rejected",
    ),
    baseline="""def parse_version(text):
    \"\"\"Parse `text` into a (major, minor, patch) tuple of ints.\"\"\"
    return tuple(int(part) for part in text.split("."))""",
    incomplete_a="""def parse_version(text):
    \"\"\"Parse `text` into a (major, minor, patch) tuple of ints.\"\"\"
    parts = [int(part) for part in text.split(".")]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)""",
    incomplete_b="""def parse_version(text):
    \"\"\"Parse `text` into a (major, minor, patch) tuple of ints.\"\"\"
    parts = text.split(".")
    if len(parts) > 3:
        raise ValueError(f"too many version components: {text!r}")
    return tuple(int(part) for part in parts)""",
    correct_narrow="""def parse_version(text):
    \"\"\"Parse `text` into a (major, minor, patch) tuple of ints.\"\"\"
    parts = text.split(".")
    if len(parts) > 3:
        raise ValueError(f"too many version components: {text!r}")
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)""",
    correct_robust="""def parse_version(text):
    \"\"\"Parse `text` into a (major, minor, patch) tuple of ints.\"\"\"
    parts = text.split(".")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"a version has one to three components: {text!r}")
    padded = (*parts, "0", "0")[:3]
    return tuple(int(part) for part in padded)""",
    visible_test=_test_module(
        "versions",
        "Published contract for the version parser.",
        """
def test_three_components() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)


def test_zero_version() -> None:
    assert parse_version("0.0.0") == (0, 0, 0)


def test_large_components() -> None:
    assert parse_version("10.20.30") == (10, 20, 30)
""",
        imports="from versions import parse_version\n",
    ),
    hidden_test=_test_module(
        "versions",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_three_components() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)


def test_two_components_are_padded() -> None:
    assert parse_version("1.2") == (1, 2, 0)


def test_one_component_is_padded() -> None:
    assert parse_version("4") == (4, 0, 0)


def test_a_short_version_equals_its_padded_form() -> None:
    assert parse_version("1.2") == parse_version("1.2.0")


def test_four_components_are_rejected() -> None:
    with pytest.raises(ValueError):
        parse_version("1.2.3.4")
""",
        imports="from versions import parse_version\n",
    ),
)

_P5 = TaskSpec(
    template_id="parsing_validation.normalize_header",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="parsing-header-names",
    module="header_names",
    module_doc="Normalize protocol header names for lookup.",
    issue=(
        "normalize_header() lowercases the name and nothing else, so a header written with "
        "underscores never matches the same header written with dashes, and an empty name is "
        "accepted and produces an empty key."
    ),
    expected=(
        "normalize_header(name) trims whitespace, lowercases, converts underscores to dashes, "
        "and raises ValueError for a name that is empty or only whitespace."
    ),
    baseline_reason="underscores are not converted and an empty name is not rejected",
    edge_cases=("underscores normalize to dashes", "an empty name raises ValueError"),
    baseline="""def normalize_header(name):
    \"\"\"Return the canonical lookup form of header `name`.\"\"\"
    return name.lower()""",
    incomplete_a="""def normalize_header(name):
    \"\"\"Return the canonical lookup form of header `name`.\"\"\"
    return name.strip().lower().replace("_", "-")""",
    incomplete_b="""def normalize_header(name):
    \"\"\"Return the canonical lookup form of header `name`.\"\"\"
    if not name.strip():
        raise ValueError("a header name cannot be empty")
    return name.strip().lower()""",
    correct_narrow="""def normalize_header(name):
    \"\"\"Return the canonical lookup form of header `name`.\"\"\"
    if not name.strip():
        raise ValueError("a header name cannot be empty")
    return name.strip().lower().replace("_", "-")""",
    correct_robust="""def normalize_header(name):
    \"\"\"Return the canonical lookup form of header `name`.\"\"\"
    trimmed = name.strip()
    if not trimmed:
        raise ValueError("a header name cannot be empty")
    return "-".join(part for part in trimmed.lower().replace("_", "-").split("-"))""",
    visible_test=_test_module(
        "header_names",
        "Published contract for header-name normalization.",
        """
def test_lowercases() -> None:
    assert normalize_header("Content-Type") == "content-type"


def test_already_normal() -> None:
    assert normalize_header("accept") == "accept"
""",
        imports="from header_names import normalize_header\n",
    ),
    hidden_test=_test_module(
        "header_names",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_lowercases() -> None:
    assert normalize_header("Content-Type") == "content-type"


def test_underscores_become_dashes() -> None:
    assert normalize_header("Content_Type") == "content-type"


def test_underscore_and_dash_forms_agree() -> None:
    assert normalize_header("X_Request_Id") == normalize_header("X-Request-Id")


def test_an_empty_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_header("")


def test_a_whitespace_only_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        normalize_header("   ")
""",
        imports="from header_names import normalize_header\n",
    ),
)


# --------------------------------------------------------------------- state and idempotency

_S1 = TaskSpec(
    template_id="state_idempotency.register",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="state-registry",
    module="registry",
    module_doc="A small name-to-value registry with idempotent registration.",
    issue=(
        "register() overwrites whatever was there and always reports the registration as new, "
        "so a retried startup silently replaces a value and the caller cannot tell a repeat "
        "from a genuine conflict."
    ),
    expected=(
        "register(registry, name, value) returns True the first time, returns False when the "
        "same name is registered with an equal value, and raises ValueError when the same name "
        "is registered with a different value."
    ),
    baseline_reason="every call writes and returns True, so repeats and conflicts look identical",
    edge_cases=(
        "re-registering an equal value returns False",
        "a conflicting value raises ValueError",
    ),
    baseline="""def register(registry, name, value):
    \"\"\"Register `value` under `name`. Return whether the registration was new.\"\"\"
    registry[name] = value
    return True""",
    incomplete_a="""def register(registry, name, value):
    \"\"\"Register `value` under `name`. Return whether the registration was new.\"\"\"
    if name in registry:
        return False
    registry[name] = value
    return True""",
    incomplete_b="""def register(registry, name, value):
    \"\"\"Register `value` under `name`. Return whether the registration was new.\"\"\"
    if name in registry and registry[name] != value:
        raise ValueError(f"{name!r} is already registered with a different value")
    registry[name] = value
    return True""",
    correct_narrow="""def register(registry, name, value):
    \"\"\"Register `value` under `name`. Return whether the registration was new.\"\"\"
    if name in registry:
        if registry[name] != value:
            raise ValueError(f"{name!r} is already registered with a different value")
        return False
    registry[name] = value
    return True""",
    correct_robust="""def register(registry, name, value):
    \"\"\"Register `value` under `name`. Return whether the registration was new.\"\"\"
    missing = object()
    existing = registry.get(name, missing)
    if existing is missing:
        registry[name] = value
        return True
    if existing != value:
        raise ValueError(f"{name!r} is already registered with a different value")
    return False""",
    visible_test=_test_module(
        "registry",
        "Published contract for the registry.",
        """
def test_first_registration_is_new() -> None:
    assert register({}, "a", 1) is True


def test_the_value_is_stored() -> None:
    registry = {}
    register(registry, "a", 1)
    assert registry["a"] == 1


def test_two_different_names() -> None:
    registry = {}
    register(registry, "a", 1)
    register(registry, "b", 2)
    assert registry == {"a": 1, "b": 2}
""",
        imports="from registry import register\n",
    ),
    hidden_test=_test_module(
        "registry",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_first_registration_is_new() -> None:
    assert register({}, "a", 1) is True


def test_registering_an_equal_value_again_is_not_new() -> None:
    registry = {"a": 1}
    assert register(registry, "a", 1) is False


def test_registering_an_equal_value_again_leaves_the_registry_alone() -> None:
    registry = {"a": 1}
    register(registry, "a", 1)
    assert registry == {"a": 1}


def test_a_conflicting_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        register({"a": 1}, "a", 2)


def test_a_conflicting_value_does_not_overwrite() -> None:
    registry = {"a": 1}
    with pytest.raises(ValueError):
        register(registry, "a", 2)
    assert registry["a"] == 1
""",
        imports="from registry import register\n",
    ),
)

_S2 = TaskSpec(
    template_id="state_idempotency.advance",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="state-machine",
    module="state_machine",
    module_doc="A four-state run lifecycle.",
    imports=(
        "TRANSITIONS = {\n"
        '    "new": {"start": "running"},\n'
        '    "running": {"finish": "done", "fail": "failed"},\n'
        "}\n"
        'KNOWN_EVENTS = frozenset({"start", "finish", "fail"})\n'
    ),
    issue=(
        "advance() returns the current state for anything it does not recognise, so a "
        "misspelled event and an event sent in the wrong order both look like a successful "
        "no-op instead of a bug the caller can see."
    ),
    expected=(
        "advance(state, event) returns the next state for a valid transition and raises "
        "ValueError both for an unknown event name and for a known event that is not valid in "
        "the current state."
    ),
    baseline_reason="an unconditional fallback to the current state hides every invalid event",
    edge_cases=(
        "an unknown event raises ValueError",
        "a known but out-of-order event raises ValueError",
    ),
    baseline="""def advance(state, event):
    \"\"\"Return the state reached from `state` by `event`.\"\"\"
    return TRANSITIONS.get(state, {}).get(event, state)""",
    incomplete_a="""def advance(state, event):
    \"\"\"Return the state reached from `state` by `event`.\"\"\"
    if event not in KNOWN_EVENTS:
        raise ValueError(f"unknown event: {event!r}")
    return TRANSITIONS.get(state, {}).get(event, state)""",
    incomplete_b="""def advance(state, event):
    \"\"\"Return the state reached from `state` by `event`.\"\"\"
    transitions = TRANSITIONS.get(state, {})
    if event in KNOWN_EVENTS and event not in transitions:
        raise ValueError(f"{event!r} is not valid in state {state!r}")
    return transitions.get(event, state)""",
    correct_narrow="""def advance(state, event):
    \"\"\"Return the state reached from `state` by `event`.\"\"\"
    if event not in KNOWN_EVENTS:
        raise ValueError(f"unknown event: {event!r}")
    transitions = TRANSITIONS.get(state, {})
    if event not in transitions:
        raise ValueError(f"{event!r} is not valid in state {state!r}")
    return transitions[event]""",
    correct_robust="""def advance(state, event):
    \"\"\"Return the state reached from `state` by `event`.\"\"\"
    allowed = {
        (current, name): target
        for current, moves in TRANSITIONS.items()
        for name, target in moves.items()
    }
    if event not in KNOWN_EVENTS:
        raise ValueError(f"unknown event: {event!r}")
    if (state, event) not in allowed:
        raise ValueError(f"{event!r} is not valid in state {state!r}")
    return allowed[(state, event)]""",
    visible_test=_test_module(
        "state_machine",
        "Published contract for the run lifecycle.",
        """
def test_start() -> None:
    assert advance("new", "start") == "running"


def test_finish() -> None:
    assert advance("running", "finish") == "done"


def test_fail() -> None:
    assert advance("running", "fail") == "failed"
""",
        imports="from state_machine import advance\n",
    ),
    hidden_test=_test_module(
        "state_machine",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_start() -> None:
    assert advance("new", "start") == "running"


def test_an_unknown_event_is_rejected() -> None:
    with pytest.raises(ValueError):
        advance("new", "explode")


def test_an_unknown_event_from_a_terminal_state_is_rejected() -> None:
    with pytest.raises(ValueError):
        advance("done", "explode")


def test_finishing_before_starting_is_rejected() -> None:
    with pytest.raises(ValueError):
        advance("new", "finish")


def test_starting_twice_is_rejected() -> None:
    with pytest.raises(ValueError):
        advance("running", "start")
""",
        imports="from state_machine import advance\n",
    ),
)

_S3 = TaskSpec(
    template_id="state_idempotency.merge_settings",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="state-settings-merge",
    module="settings_merge",
    module_doc="Layer an override mapping over a base mapping.",
    issue=(
        "merge_settings() mutates the base mapping the caller passed in, and treats an "
        "explicit None in the override as a value, so an unset option wipes out the base "
        "setting for every later caller too."
    ),
    expected=(
        "merge_settings(base, override) returns a new mapping in which override entries whose "
        "value is None are ignored, and leaves base unchanged."
    ),
    baseline_reason=(
        "update() writes into the caller's mapping and copies None values over real ones"
    ),
    edge_cases=("None override values are ignored", "the base mapping is not mutated"),
    baseline="""def merge_settings(base, override):
    \"\"\"Return `base` with `override` layered on top.\"\"\"
    base.update(override)
    return base""",
    incomplete_a="""def merge_settings(base, override):
    \"\"\"Return `base` with `override` layered on top.\"\"\"
    merged = dict(base)
    merged.update(override)
    return merged""",
    incomplete_b="""def merge_settings(base, override):
    \"\"\"Return `base` with `override` layered on top.\"\"\"
    for key, value in override.items():
        if value is not None:
            base[key] = value
    return base""",
    correct_narrow="""def merge_settings(base, override):
    \"\"\"Return `base` with `override` layered on top.\"\"\"
    merged = dict(base)
    for key, value in override.items():
        if value is not None:
            merged[key] = value
    return merged""",
    correct_robust="""def merge_settings(base, override):
    \"\"\"Return `base` with `override` layered on top.\"\"\"
    applied = {key: value for key, value in override.items() if value is not None}
    return {**base, **applied}""",
    visible_test=_test_module(
        "settings_merge",
        "Published contract for settings merging.",
        """
def test_new_key_is_added() -> None:
    assert merge_settings({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_existing_key_is_overridden() -> None:
    assert merge_settings({"a": 1}, {"a": 9}) == {"a": 9}


def test_empty_override_changes_nothing() -> None:
    assert merge_settings({"a": 1}, {}) == {"a": 1}
""",
        imports="from settings_merge import merge_settings\n",
    ),
    hidden_test=_test_module(
        "settings_merge",
        "The part of the contract the published tests do not state.",
        """
def test_new_key_is_added() -> None:
    assert merge_settings({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_a_none_override_is_ignored() -> None:
    assert merge_settings({"a": 1}, {"a": None}) == {"a": 1}


def test_a_none_override_does_not_introduce_a_key() -> None:
    assert merge_settings({"a": 1}, {"b": None}) == {"a": 1}


def test_the_base_mapping_is_not_mutated() -> None:
    base = {"a": 1}
    merge_settings(base, {"a": 9, "b": 2})
    assert base == {"a": 1}


def test_merging_twice_from_the_same_base_agrees() -> None:
    base = {"a": 1}
    first = merge_settings(base, {"b": 2})
    second = merge_settings(base, {"b": 2})
    assert first == second
""",
        imports="from settings_merge import merge_settings\n",
    ),
)

_S4 = TaskSpec(
    template_id="state_idempotency.acquire_slot",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="state-slot-allocation",
    module="slot_allocation",
    module_doc="Allocate bounded, stable worker slots by name.",
    issue=(
        "acquire() hands out a new slot every time it is called, so a worker that reconnects "
        "occupies two slots, and the declared capacity is never enforced."
    ),
    expected=(
        "acquire(slots, name, capacity) returns the same slot index for a name that already "
        "holds one, and raises RuntimeError when a new name would exceed capacity."
    ),
    baseline_reason="no existing-name check and no capacity check, so reconnects leak slots",
    edge_cases=("re-acquiring returns the same slot", "exceeding capacity raises RuntimeError"),
    baseline="""def acquire(slots, name, capacity):
    \"\"\"Return the slot index held by `name`, allocating one if needed.\"\"\"
    index = len(slots)
    slots[name] = index
    return index""",
    incomplete_a="""def acquire(slots, name, capacity):
    \"\"\"Return the slot index held by `name`, allocating one if needed.\"\"\"
    if name in slots:
        return slots[name]
    index = len(slots)
    slots[name] = index
    return index""",
    incomplete_b="""def acquire(slots, name, capacity):
    \"\"\"Return the slot index held by `name`, allocating one if needed.\"\"\"
    if len(slots) >= capacity:
        raise RuntimeError("no free slot")
    index = len(slots)
    slots[name] = index
    return index""",
    correct_narrow="""def acquire(slots, name, capacity):
    \"\"\"Return the slot index held by `name`, allocating one if needed.\"\"\"
    if name in slots:
        return slots[name]
    if len(slots) >= capacity:
        raise RuntimeError("no free slot")
    index = len(slots)
    slots[name] = index
    return index""",
    correct_robust="""def acquire(slots, name, capacity):
    \"\"\"Return the slot index held by `name`, allocating one if needed.\"\"\"
    existing = slots.get(name)
    if existing is not None:
        return existing
    taken = set(slots.values())
    for index in range(capacity):
        if index not in taken:
            slots[name] = index
            return index
    raise RuntimeError("no free slot")""",
    visible_test=_test_module(
        "slot_allocation",
        "Published contract for slot allocation.",
        """
def test_first_slot_is_zero() -> None:
    assert acquire({}, "a", 4) == 0


def test_second_name_gets_the_next_slot() -> None:
    slots = {}
    acquire(slots, "a", 4)
    assert acquire(slots, "b", 4) == 1


def test_the_slot_is_recorded() -> None:
    slots = {}
    acquire(slots, "a", 4)
    assert slots["a"] == 0
""",
        imports="from slot_allocation import acquire\n",
    ),
    hidden_test=_test_module(
        "slot_allocation",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_first_slot_is_zero() -> None:
    assert acquire({}, "a", 4) == 0


def test_re_acquiring_returns_the_same_slot() -> None:
    slots = {}
    first = acquire(slots, "a", 4)
    assert acquire(slots, "a", 4) == first


def test_re_acquiring_does_not_consume_another_slot() -> None:
    slots = {}
    acquire(slots, "a", 4)
    acquire(slots, "a", 4)
    assert len(slots) == 1


def test_exceeding_capacity_is_rejected() -> None:
    slots = {}
    acquire(slots, "a", 1)
    with pytest.raises(RuntimeError):
        acquire(slots, "b", 1)


def test_capacity_of_zero_rejects_the_first_name() -> None:
    with pytest.raises(RuntimeError):
        acquire({}, "a", 0)
""",
        imports="from slot_allocation import acquire\n",
    ),
)

_S5 = TaskSpec(
    template_id="state_idempotency.checkpoint",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="state-checkpoint-history",
    module="checkpoint_history",
    module_doc="Bounded checkpoint history with repeat suppression.",
    issue=(
        "checkpoint() records the label even when it repeats the current one, so a retried "
        "step fills the history with duplicates. The history also grows without bound, so a "
        "long-running job eventually carries thousands of entries no one reads."
    ),
    expected=(
        "checkpoint(history, label, limit) does not record a label equal to the current last "
        "entry, and keeps at most `limit` entries by dropping the oldest."
    ),
    baseline_reason=(
        "every call appends unconditionally and nothing ever trims the history to its limit"
    ),
    edge_cases=("a repeat of the last label is suppressed", "the history is trimmed to its limit"),
    baseline="""def checkpoint(history, label, limit=3):
    \"\"\"Return a new history with `label` recorded, keeping at most `limit` entries.\"\"\"
    return [*history, label]""",
    incomplete_a="""def checkpoint(history, label, limit=3):
    \"\"\"Return a new history with `label` recorded, keeping at most `limit` entries.\"\"\"
    if history and history[-1] == label:
        return list(history)
    return [*history, label]""",
    incomplete_b="""def checkpoint(history, label, limit=3):
    \"\"\"Return a new history with `label` recorded, keeping at most `limit` entries.\"\"\"
    return [*history, label][-limit:]""",
    correct_narrow="""def checkpoint(history, label, limit=3):
    \"\"\"Return a new history with `label` recorded, keeping at most `limit` entries.\"\"\"
    if history and history[-1] == label:
        return list(history)
    return [*history, label][-limit:]""",
    correct_robust="""def checkpoint(history, label, limit=3):
    \"\"\"Return a new history with `label` recorded, keeping at most `limit` entries.\"\"\"
    from collections import deque

    window = deque(history, maxlen=limit)
    if window and window[-1] == label:
        return list(window)
    window.append(label)
    return list(window)""",
    visible_test=_test_module(
        "checkpoint_history",
        "Published contract for checkpoint history.",
        """
def test_first_entry() -> None:
    assert checkpoint([], "a") == ["a"]


def test_second_distinct_entry() -> None:
    assert checkpoint(["a"], "b") == ["a", "b"]


def test_returning_to_an_earlier_label() -> None:
    assert checkpoint(["a", "b"], "a") == ["a", "b", "a"]
""",
        imports="from checkpoint_history import checkpoint\n",
    ),
    hidden_test=_test_module(
        "checkpoint_history",
        "The part of the contract the published tests do not state.",
        """
def test_first_entry() -> None:
    assert checkpoint([], "a") == ["a"]


def test_a_repeat_of_the_last_label_is_suppressed() -> None:
    assert checkpoint(["a"], "a") == ["a"]


def test_a_repeat_at_the_end_of_a_longer_history_is_suppressed() -> None:
    assert checkpoint(["a", "b"], "b") == ["a", "b"]


def test_the_history_is_trimmed_to_its_limit() -> None:
    assert checkpoint(["a", "b", "c"], "d") == ["b", "c", "d"]


def test_a_smaller_limit_trims_further() -> None:
    assert checkpoint(["a", "b"], "c", 2) == ["b", "c"]
""",
        imports="from checkpoint_history import checkpoint\n",
    ),
)

# ------------------------------------------------------------------------------ numeric logic

_N1 = TaskSpec(
    template_id="numeric_logic.mean",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="numeric-averages",
    module="averages",
    module_doc="Small statistics helpers.",
    issue=(
        "mean() returns 0.0 for an empty sequence, which callers cannot tell apart from a "
        "genuine mean of zero, and it truncates instead of dividing, so the mean of 1 and 2 "
        "is reported as 1."
    ),
    expected=(
        "mean(values) raises ValueError for an empty sequence and returns the exact "
        "arithmetic mean as a float."
    ),
    baseline_reason="an empty sequence returns 0.0 and floor division truncates the result",
    edge_cases=("an empty sequence raises ValueError", "the division is exact, not truncated"),
    baseline="""def mean(values):
    \"\"\"Return the arithmetic mean of `values`.\"\"\"
    if not values:
        return 0.0
    return sum(values) // len(values)""",
    incomplete_a="""def mean(values):
    \"\"\"Return the arithmetic mean of `values`.\"\"\"
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) // len(values)""",
    incomplete_b="""def mean(values):
    \"\"\"Return the arithmetic mean of `values`.\"\"\"
    if not values:
        return 0.0
    return sum(values) / len(values)""",
    correct_narrow="""def mean(values):
    \"\"\"Return the arithmetic mean of `values`.\"\"\"
    if not values:
        raise ValueError("mean() requires at least one value")
    return sum(values) / len(values)""",
    correct_robust="""def mean(values):
    \"\"\"Return the arithmetic mean of `values`.\"\"\"
    materialized = list(values)
    if len(materialized) == 0:
        raise ValueError("mean() requires at least one value")
    return float(sum(materialized)) / len(materialized)""",
    visible_test=_test_module(
        "averages",
        "Published contract for the statistics helpers.",
        """
def test_mean_of_two_and_four() -> None:
    assert mean([2, 4]) == 3.0


def test_mean_of_one_two_three() -> None:
    assert mean([1, 2, 3]) == 2.0


def test_mean_of_a_single_value() -> None:
    assert mean([7]) == 7.0
""",
        imports="from averages import mean\n",
    ),
    hidden_test=_test_module(
        "averages",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_mean_of_two_and_four() -> None:
    assert mean([2, 4]) == 3.0


def test_an_empty_sequence_is_rejected() -> None:
    with pytest.raises(ValueError):
        mean([])


def test_an_empty_tuple_is_rejected() -> None:
    with pytest.raises(ValueError):
        mean(())


def test_the_division_is_exact() -> None:
    assert mean([1, 2]) == 1.5


def test_a_fractional_mean_of_three_values() -> None:
    assert mean([1, 2, 2]) == pytest.approx(5 / 3)
""",
        imports="from averages import mean\n",
    ),
)

_N2 = TaskSpec(
    template_id="numeric_logic.percentage",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="numeric-percentages",
    module="percentages",
    module_doc="Report a part of a whole as a percentage.",
    issue=(
        "percentage() crashes with ZeroDivisionError when the whole is zero instead of "
        "reporting the caller's mistake, and returns full floating point noise where the "
        "documented contract is two decimal places."
    ),
    expected=(
        "percentage(part, whole) raises ValueError when whole is zero and otherwise returns "
        "the percentage rounded to two decimal places."
    ),
    baseline_reason="the division is unguarded and the result is never rounded",
    edge_cases=("a whole of zero raises ValueError", "the result is rounded to two decimals"),
    baseline="""def percentage(part, whole):
    \"\"\"Return `part` of `whole` as a percentage rounded to two decimals.\"\"\"
    return part / whole * 100""",
    incomplete_a="""def percentage(part, whole):
    \"\"\"Return `part` of `whole` as a percentage rounded to two decimals.\"\"\"
    if whole == 0:
        raise ValueError("percentage() needs a non-zero whole")
    return part / whole * 100""",
    incomplete_b="""def percentage(part, whole):
    \"\"\"Return `part` of `whole` as a percentage rounded to two decimals.\"\"\"
    return round(part / whole * 100, 2)""",
    correct_narrow="""def percentage(part, whole):
    \"\"\"Return `part` of `whole` as a percentage rounded to two decimals.\"\"\"
    if whole == 0:
        raise ValueError("percentage() needs a non-zero whole")
    return round(part / whole * 100, 2)""",
    correct_robust="""def percentage(part, whole):
    \"\"\"Return `part` of `whole` as a percentage rounded to two decimals.\"\"\"
    if not whole:
        raise ValueError("percentage() needs a non-zero whole")
    scaled = part * 100 / whole
    return float(round(scaled, 2))""",
    visible_test=_test_module(
        "percentages",
        "Published contract for the percentage helper.",
        """
def test_a_quarter() -> None:
    assert percentage(1, 4) == 25.0


def test_a_half() -> None:
    assert percentage(1, 2) == 50.0


def test_everything() -> None:
    assert percentage(3, 3) == 100.0
""",
        imports="from percentages import percentage\n",
    ),
    hidden_test=_test_module(
        "percentages",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_quarter() -> None:
    assert percentage(1, 4) == 25.0


def test_a_zero_whole_is_rejected() -> None:
    with pytest.raises(ValueError):
        percentage(1, 0)


def test_a_zero_part_of_a_zero_whole_is_rejected() -> None:
    with pytest.raises(ValueError):
        percentage(0, 0)


def test_a_recurring_result_is_rounded() -> None:
    assert percentage(1, 3) == 33.33


def test_a_two_thirds_result_is_rounded() -> None:
    assert percentage(2, 3) == 66.67
""",
        imports="from percentages import percentage\n",
    ),
)

_N3 = TaskSpec(
    template_id="numeric_logic.clamp",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="numeric-clamping",
    module="clamping",
    module_doc="Constrain a value to an inclusive range.",
    issue=(
        "clamp() silently returns the value untouched when the bounds are reversed, hiding a "
        "caller bug, and it also ignores a range whose two bounds are equal, so a degenerate "
        "range does not pin the value."
    ),
    expected=(
        "clamp(value, low, high) raises ValueError when low is above high, and returns low "
        "when low equals high."
    ),
    baseline_reason="a strict low < high guard falls through for both reversed and equal bounds",
    edge_cases=("reversed bounds raise ValueError", "equal bounds pin the value"),
    baseline="""def clamp(value, low, high):
    \"\"\"Return `value` constrained to the inclusive range [low, high].\"\"\"
    return min(max(value, low), high) if low < high else value""",
    incomplete_a="""def clamp(value, low, high):
    \"\"\"Return `value` constrained to the inclusive range [low, high].\"\"\"
    if low > high:
        raise ValueError("clamp() needs low to be at most high")
    return min(max(value, low), high) if low < high else value""",
    incomplete_b="""def clamp(value, low, high):
    \"\"\"Return `value` constrained to the inclusive range [low, high].\"\"\"
    return min(max(value, low), high) if low <= high else value""",
    correct_narrow="""def clamp(value, low, high):
    \"\"\"Return `value` constrained to the inclusive range [low, high].\"\"\"
    if low > high:
        raise ValueError("clamp() needs low to be at most high")
    return min(max(value, low), high)""",
    correct_robust="""def clamp(value, low, high):
    \"\"\"Return `value` constrained to the inclusive range [low, high].\"\"\"
    if low > high:
        raise ValueError("clamp() needs low to be at most high")
    if value < low:
        return low
    if value > high:
        return high
    return value""",
    visible_test=_test_module(
        "clamping",
        "Published contract for the clamp helper.",
        """
def test_inside_the_range() -> None:
    assert clamp(5, 1, 10) == 5


def test_below_the_range() -> None:
    assert clamp(0, 1, 10) == 1


def test_above_the_range() -> None:
    assert clamp(20, 1, 10) == 10
""",
        imports="from clamping import clamp\n",
    ),
    hidden_test=_test_module(
        "clamping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_inside_the_range() -> None:
    assert clamp(5, 1, 10) == 5


def test_reversed_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        clamp(5, 10, 1)


def test_reversed_bounds_are_rejected_even_inside_them() -> None:
    with pytest.raises(ValueError):
        clamp(0, 3, 2)


def test_equal_bounds_pin_a_larger_value() -> None:
    assert clamp(5, 2, 2) == 2


def test_equal_bounds_pin_a_smaller_value() -> None:
    assert clamp(-5, 2, 2) == 2
""",
        imports="from clamping import clamp\n",
    ),
)

_N4 = TaskSpec(
    template_id="numeric_logic.divide_evenly",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="numeric-distribution",
    module="distribution",
    module_doc="Split a total into whole-number parts.",
    issue=(
        "divide_evenly() loses the remainder, so the parts it returns do not add up to the "
        "total it was given, and it raises ZeroDivisionError rather than reporting an invalid "
        "part count."
    ),
    expected=(
        "divide_evenly(total, parts) returns `parts` whole numbers that sum to `total`, and "
        "raises ValueError when parts is less than one."
    ),
    baseline_reason="floor division discards the remainder and a part count below one is unguarded",
    edge_cases=("a part count below one raises ValueError", "the parts sum to the total"),
    baseline="""def divide_evenly(total, parts):
    \"\"\"Split `total` into `parts` whole numbers that sum to `total`.\"\"\"
    return [total // parts] * parts""",
    incomplete_a="""def divide_evenly(total, parts):
    \"\"\"Split `total` into `parts` whole numbers that sum to `total`.\"\"\"
    if parts < 1:
        raise ValueError("divide_evenly() needs at least one part")
    return [total // parts] * parts""",
    incomplete_b="""def divide_evenly(total, parts):
    \"\"\"Split `total` into `parts` whole numbers that sum to `total`.\"\"\"
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]""",
    correct_narrow="""def divide_evenly(total, parts):
    \"\"\"Split `total` into `parts` whole numbers that sum to `total`.\"\"\"
    if parts < 1:
        raise ValueError("divide_evenly() needs at least one part")
    base, remainder = divmod(total, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]""",
    correct_robust="""def divide_evenly(total, parts):
    \"\"\"Split `total` into `parts` whole numbers that sum to `total`.\"\"\"
    if parts < 1:
        raise ValueError("divide_evenly() needs at least one part")
    shares = []
    remaining_total = total
    remaining_parts = parts
    while remaining_parts:
        share = -(-remaining_total // remaining_parts) if remaining_total >= 0 else 0
        shares.append(share)
        remaining_total -= share
        remaining_parts -= 1
    return shares""",
    visible_test=_test_module(
        "distribution",
        "Published contract for even distribution.",
        """
def test_exact_thirds() -> None:
    assert divide_evenly(9, 3) == [3, 3, 3]


def test_exact_halves() -> None:
    assert divide_evenly(4, 2) == [2, 2]


def test_one_part_takes_everything() -> None:
    assert divide_evenly(5, 1) == [5]
""",
        imports="from distribution import divide_evenly\n",
    ),
    hidden_test=_test_module(
        "distribution",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_exact_thirds() -> None:
    assert divide_evenly(9, 3) == [3, 3, 3]


def test_a_remainder_is_distributed() -> None:
    assert sum(divide_evenly(10, 3)) == 10


def test_every_share_differs_by_at_most_one() -> None:
    shares = divide_evenly(10, 3)
    assert max(shares) - min(shares) <= 1


def test_zero_parts_are_rejected() -> None:
    with pytest.raises(ValueError):
        divide_evenly(10, 0)


def test_negative_parts_are_rejected() -> None:
    with pytest.raises(ValueError):
        divide_evenly(10, -1)
""",
        imports="from distribution import divide_evenly\n",
    ),
)

_N5 = TaskSpec(
    template_id="numeric_logic.compound",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="numeric-compounding",
    module="compounding",
    module_doc="Compound a principal over whole periods.",
    issue=(
        "compound() accepts a negative number of periods and quietly discounts instead of "
        "refusing, and it returns unrounded floating point noise where the documented "
        "contract is a currency amount."
    ),
    expected=(
        "compound(principal, rate, periods) raises ValueError for a negative period count and "
        "returns the amount rounded to two decimal places."
    ),
    baseline_reason=(
        "the exponent is unguarded for negative periods and the result is never rounded"
    ),
    edge_cases=(
        "a negative period count raises ValueError",
        "the amount is rounded to two decimals",
    ),
    baseline="""def compound(principal, rate, periods):
    \"\"\"Return `principal` compounded at `rate` over `periods`, to two decimals.\"\"\"
    return principal * (1 + rate) ** periods""",
    incomplete_a="""def compound(principal, rate, periods):
    \"\"\"Return `principal` compounded at `rate` over `periods`, to two decimals.\"\"\"
    if periods < 0:
        raise ValueError("compound() needs a non-negative period count")
    return principal * (1 + rate) ** periods""",
    incomplete_b="""def compound(principal, rate, periods):
    \"\"\"Return `principal` compounded at `rate` over `periods`, to two decimals.\"\"\"
    return round(principal * (1 + rate) ** periods, 2)""",
    correct_narrow="""def compound(principal, rate, periods):
    \"\"\"Return `principal` compounded at `rate` over `periods`, to two decimals.\"\"\"
    if periods < 0:
        raise ValueError("compound() needs a non-negative period count")
    return round(principal * (1 + rate) ** periods, 2)""",
    correct_robust="""def compound(principal, rate, periods):
    \"\"\"Return `principal` compounded at `rate` over `periods`, to two decimals.\"\"\"
    if periods < 0:
        raise ValueError("compound() needs a non-negative period count")
    amount = float(principal)
    for _ in range(periods):
        amount *= 1 + rate
    return round(amount, 2)""",
    visible_test=_test_module(
        "compounding",
        "Published contract for the compounding helper.",
        """
def test_no_growth() -> None:
    assert compound(100, 0.0, 5) == 100.0


def test_no_periods() -> None:
    assert compound(100, 0.1, 0) == 100.0


def test_doubling_once() -> None:
    assert compound(100, 1.0, 1) == 200.0
""",
        imports="from compounding import compound\n",
    ),
    hidden_test=_test_module(
        "compounding",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_no_growth() -> None:
    assert compound(100, 0.0, 5) == 100.0


def test_a_negative_period_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        compound(100, 0.1, -1)


def test_a_large_negative_period_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        compound(100, 0.1, -12)


def test_two_periods_are_rounded_to_currency() -> None:
    assert compound(100, 0.1, 2) == 121.0


def test_three_periods_are_rounded_to_currency() -> None:
    assert compound(100, 0.1, 3) == 133.1
""",
        imports="from compounding import compound\n",
    ),
)


# ---------------------------------------------------------------------------- error handling

_H1 = TaskSpec(
    template_id="error_handling.lookup",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="errors-nested-lookup",
    module="nested_lookup",
    module_doc="Read a value out of nested mappings by dotted path.",
    issue=(
        "lookup() reports only the missing segment, so an operator reading the log sees "
        "KeyError('id') with no idea which of the eleven paths containing 'id' failed. An "
        "empty path is also accepted and fails with a confusing KeyError on the empty string."
    ),
    expected=(
        "lookup(mapping, path) raises KeyError naming the full path when a segment is missing, "
        "and raises ValueError for an empty path."
    ),
    baseline_reason=(
        "the KeyError carries only the failing segment and an empty path is not rejected"
    ),
    edge_cases=("a missing segment names the full path", "an empty path raises ValueError"),
    baseline="""def lookup(mapping, path):
    \"\"\"Return the value at dotted `path` inside `mapping`.\"\"\"
    current = mapping
    for part in path.split("."):
        current = current[part]
    return current""",
    incomplete_a="""def lookup(mapping, path):
    \"\"\"Return the value at dotted `path` inside `mapping`.\"\"\"
    current = mapping
    for part in path.split("."):
        try:
            current = current[part]
        except KeyError:
            raise KeyError(path) from None
    return current""",
    incomplete_b="""def lookup(mapping, path):
    \"\"\"Return the value at dotted `path` inside `mapping`.\"\"\"
    if not path:
        raise ValueError("lookup() needs a non-empty path")
    current = mapping
    for part in path.split("."):
        current = current[part]
    return current""",
    correct_narrow="""def lookup(mapping, path):
    \"\"\"Return the value at dotted `path` inside `mapping`.\"\"\"
    if not path:
        raise ValueError("lookup() needs a non-empty path")
    current = mapping
    for part in path.split("."):
        try:
            current = current[part]
        except KeyError:
            raise KeyError(path) from None
    return current""",
    correct_robust="""def lookup(mapping, path):
    \"\"\"Return the value at dotted `path` inside `mapping`.\"\"\"
    parts = path.split(".") if path else []
    if not parts:
        raise ValueError("lookup() needs a non-empty path")
    current = mapping
    for part in parts:
        if part not in current:
            raise KeyError(path)
        current = current[part]
    return current""",
    visible_test=_test_module(
        "nested_lookup",
        "Published contract for the nested lookup helper.",
        """
def test_one_level() -> None:
    assert lookup({"a": 1}, "a") == 1


def test_two_levels() -> None:
    assert lookup({"a": {"b": 2}}, "a.b") == 2


def test_three_levels() -> None:
    assert lookup({"a": {"b": {"c": 3}}}, "a.b.c") == 3
""",
        imports="from nested_lookup import lookup\n",
    ),
    hidden_test=_test_module(
        "nested_lookup",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_levels() -> None:
    assert lookup({"a": {"b": 2}}, "a.b") == 2


def test_a_missing_leaf_names_the_full_path() -> None:
    with pytest.raises(KeyError) as info:
        lookup({"a": {}}, "a.b")
    assert "a.b" in str(info.value)


def test_a_missing_branch_names_the_full_path() -> None:
    with pytest.raises(KeyError) as info:
        lookup({}, "a.b.c")
    assert "a.b.c" in str(info.value)


def test_an_empty_path_is_rejected() -> None:
    with pytest.raises(ValueError):
        lookup({"a": 1}, "")
""",
        imports="from nested_lookup import lookup\n",
    ),
)

_H2 = TaskSpec(
    template_id="error_handling.first_success",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="errors-fallback-chain",
    module="fallback_chain",
    module_doc="Try a chain of actions until one succeeds.",
    issue=(
        "first_success() returns None when every action fails, so the caller gets a value that "
        "looks like a result and the underlying errors are lost. It also returns None for an "
        "empty chain instead of reporting that there was nothing to try."
    ),
    expected=(
        "first_success(actions) raises ValueError for an empty chain, and re-raises the last "
        "error when every action failed."
    ),
    baseline_reason=(
        "every failure path returns None, so errors and an empty chain both look like a result"
    ),
    edge_cases=("an empty chain raises ValueError", "the last error is re-raised when all fail"),
    baseline="""def first_success(actions):
    \"\"\"Return the result of the first action that does not raise.\"\"\"
    for action in actions:
        try:
            return action()
        except Exception:
            continue
    return None""",
    incomplete_a="""def first_success(actions):
    \"\"\"Return the result of the first action that does not raise.\"\"\"
    if not actions:
        raise ValueError("first_success() needs at least one action")
    for action in actions:
        try:
            return action()
        except Exception:
            continue
    return None""",
    incomplete_b="""def first_success(actions):
    \"\"\"Return the result of the first action that does not raise.\"\"\"
    last_error = None
    for action in actions:
        try:
            return action()
        except Exception as error:
            last_error = error
    if last_error is not None:
        raise last_error
    return None""",
    correct_narrow="""def first_success(actions):
    \"\"\"Return the result of the first action that does not raise.\"\"\"
    if not actions:
        raise ValueError("first_success() needs at least one action")
    last_error = None
    for action in actions:
        try:
            return action()
        except Exception as error:
            last_error = error
    raise last_error""",
    correct_robust="""def first_success(actions):
    \"\"\"Return the result of the first action that does not raise.\"\"\"
    chain = list(actions)
    if not chain:
        raise ValueError("first_success() needs at least one action")
    errors = []
    for action in chain:
        try:
            return action()
        except Exception as error:
            errors.append(error)
    raise errors[-1]""",
    visible_test=_test_module(
        "fallback_chain",
        "Published contract for the fallback chain.",
        """
def boom():
    raise RuntimeError("no")


def test_first_action_wins() -> None:
    assert first_success([lambda: 1]) == 1


def test_a_failing_action_is_skipped() -> None:
    assert first_success([boom, lambda: 2]) == 2


def test_the_first_success_stops_the_chain() -> None:
    assert first_success([lambda: 3, lambda: 4]) == 3
""",
        imports="from fallback_chain import first_success\n",
    ),
    hidden_test=_test_module(
        "fallback_chain",
        "The part of the contract the published tests do not state.",
        """
import pytest


def boom():
    raise RuntimeError("no")


def test_a_failing_action_is_skipped() -> None:
    assert first_success([boom, lambda: 2]) == 2


def test_an_empty_chain_is_rejected() -> None:
    with pytest.raises(ValueError):
        first_success([])


def test_the_error_is_re_raised_when_every_action_fails() -> None:
    with pytest.raises(RuntimeError):
        first_success([boom, boom])


def test_a_single_failing_action_re_raises() -> None:
    with pytest.raises(RuntimeError):
        first_success([boom])
""",
        imports="from fallback_chain import first_success\n",
    ),
)

_H3 = TaskSpec(
    template_id="error_handling.parse_or_default",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="errors-lenient-parsing",
    module="lenient_parsing",
    module_doc="Parse an integer setting, falling back to a default.",
    issue=(
        "parse_or_default() swallows every exception, so a caller that passes None instead of "
        "a string gets the default rather than a bug report. It also treats a parsed zero as "
        "absent and substitutes the default for it."
    ),
    expected=(
        "parse_or_default(text, default) returns the default only for text that is not a valid "
        "integer, returns 0 for '0', and lets a TypeError from a non-string argument propagate."
    ),
    baseline_reason="a bare except hides caller bugs and `or default` replaces a legitimate zero",
    edge_cases=(
        "a non-string argument raises TypeError",
        "a parsed zero is returned, not replaced",
    ),
    baseline="""def parse_or_default(text, default=0):
    \"\"\"Return the integer in `text`, or `default` when it is not one.\"\"\"
    try:
        return int(text) or default
    except Exception:
        return default""",
    incomplete_a="""def parse_or_default(text, default=0):
    \"\"\"Return the integer in `text`, or `default` when it is not one.\"\"\"
    try:
        return int(text) or default
    except ValueError:
        return default""",
    incomplete_b="""def parse_or_default(text, default=0):
    \"\"\"Return the integer in `text`, or `default` when it is not one.\"\"\"
    try:
        return int(text)
    except Exception:
        return default""",
    correct_narrow="""def parse_or_default(text, default=0):
    \"\"\"Return the integer in `text`, or `default` when it is not one.\"\"\"
    try:
        return int(text)
    except ValueError:
        return default""",
    correct_robust="""def parse_or_default(text, default=0):
    \"\"\"Return the integer in `text`, or `default` when it is not one.\"\"\"
    if not isinstance(text, str):
        raise TypeError("parse_or_default() needs a string")
    stripped = text.strip()
    try:
        return int(stripped)
    except ValueError:
        return default""",
    visible_test=_test_module(
        "lenient_parsing",
        "Published contract for the lenient integer parser.",
        """
def test_a_valid_integer() -> None:
    assert parse_or_default("12") == 12


def test_an_invalid_value_uses_the_default() -> None:
    assert parse_or_default("x", 5) == 5


def test_a_negative_integer() -> None:
    assert parse_or_default("-3") == -3
""",
        imports="from lenient_parsing import parse_or_default\n",
    ),
    hidden_test=_test_module(
        "lenient_parsing",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_valid_integer() -> None:
    assert parse_or_default("12") == 12


def test_a_non_string_argument_is_a_caller_bug() -> None:
    with pytest.raises(TypeError):
        parse_or_default(None)


def test_a_list_argument_is_a_caller_bug() -> None:
    with pytest.raises(TypeError):
        parse_or_default(["1"])


def test_a_parsed_zero_is_returned() -> None:
    assert parse_or_default("0", 9) == 0


def test_a_parsed_zero_without_a_default_is_zero() -> None:
    assert parse_or_default("0") == 0
""",
        imports="from lenient_parsing import parse_or_default\n",
    ),
)

_H4 = TaskSpec(
    template_id="error_handling.close_all",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="errors-bulk-cleanup",
    module="bulk_cleanup",
    module_doc="Close a set of resources during shutdown.",
    issue=(
        "close_all() stops at the first resource whose close() raises, so everything after it "
        "leaks. It also returns nothing, leaving the shutdown log with no record of how many "
        "resources were actually released."
    ),
    expected=(
        "close_all(resources) attempts to close every resource even when one raises, and "
        "returns the number closed successfully."
    ),
    baseline_reason="an unguarded loop aborts on the first failure and no count is returned",
    edge_cases=("every resource is closed even if one raises", "the number closed is returned"),
    baseline="""def close_all(resources):
    \"\"\"Close every resource and return how many closed successfully.\"\"\"
    for resource in resources:
        resource.close()""",
    incomplete_a="""def close_all(resources):
    \"\"\"Close every resource and return how many closed successfully.\"\"\"
    for resource in resources:
        try:
            resource.close()
        except Exception:
            continue""",
    incomplete_b="""def close_all(resources):
    \"\"\"Close every resource and return how many closed successfully.\"\"\"
    closed = 0
    for resource in resources:
        resource.close()
        closed += 1
    return closed""",
    correct_narrow="""def close_all(resources):
    \"\"\"Close every resource and return how many closed successfully.\"\"\"
    closed = 0
    for resource in resources:
        try:
            resource.close()
        except Exception:
            continue
        closed += 1
    return closed""",
    correct_robust="""def close_all(resources):
    \"\"\"Close every resource and return how many closed successfully.\"\"\"
    outcomes = []
    for resource in resources:
        try:
            resource.close()
            outcomes.append(True)
        except Exception:
            outcomes.append(False)
    return sum(1 for outcome in outcomes if outcome)""",
    visible_test=_test_module(
        "bulk_cleanup",
        "Published contract for bulk cleanup.",
        """
class Resource:
    def __init__(self, fails=False):
        self.fails = fails
        self.closed = False

    def close(self):
        if self.fails:
            raise RuntimeError("cannot close")
        self.closed = True


def test_every_resource_is_closed() -> None:
    resources = [Resource(), Resource()]
    close_all(resources)
    assert all(resource.closed for resource in resources)


def test_an_empty_set_is_accepted() -> None:
    close_all([])


def test_a_single_resource_is_closed() -> None:
    resource = Resource()
    close_all([resource])
    assert resource.closed
""",
        imports="from bulk_cleanup import close_all\n",
    ),
    hidden_test=_test_module(
        "bulk_cleanup",
        "The part of the contract the published tests do not state.",
        """
class Resource:
    def __init__(self, fails=False):
        self.fails = fails
        self.closed = False

    def close(self):
        if self.fails:
            raise RuntimeError("cannot close")
        self.closed = True


def test_a_failure_does_not_strand_later_resources() -> None:
    last = Resource()
    close_all([Resource(fails=True), last])
    assert last.closed


def test_a_failure_in_the_middle_does_not_strand_the_rest() -> None:
    resources = [Resource(), Resource(fails=True), Resource()]
    close_all(resources)
    assert [resource.closed for resource in resources] == [True, False, True]


def test_the_number_closed_is_returned() -> None:
    assert close_all([Resource(), Resource()]) == 2


def test_an_empty_set_closes_nothing() -> None:
    assert close_all([]) == 0
""",
        imports="from bulk_cleanup import close_all\n",
    ),
)

_H5 = TaskSpec(
    template_id="error_handling.require",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="errors-preconditions",
    module="preconditions",
    module_doc="Check a precondition and report it as a domain error.",
    imports=(
        "class ValidationError(Exception):\n"
        '    """Raised when a declared precondition does not hold."""\n'
    ),
    issue=(
        "require() reports a violated precondition as AssertionError, which callers cannot "
        "distinguish from a genuine internal bug and which disappears entirely under python -O. "
        "It also accepts an empty message, producing an error with nothing in it."
    ),
    expected=(
        "require(condition, message) raises ValidationError with the message when the condition "
        "is false, and raises ValueError when the message itself is empty."
    ),
    baseline_reason="an assert statement raises the wrong type and does not check the message",
    edge_cases=(
        "an empty message raises ValueError",
        "a violated precondition raises ValidationError",
    ),
    baseline="""def require(condition, message):
    \"\"\"Raise ValidationError with `message` unless `condition` holds.\"\"\"
    assert condition, message""",
    incomplete_a="""def require(condition, message):
    \"\"\"Raise ValidationError with `message` unless `condition` holds.\"\"\"
    if not message:
        raise ValueError("require() needs a message")
    assert condition, message""",
    incomplete_b="""def require(condition, message):
    \"\"\"Raise ValidationError with `message` unless `condition` holds.\"\"\"
    if not condition:
        raise ValidationError(message)""",
    correct_narrow="""def require(condition, message):
    \"\"\"Raise ValidationError with `message` unless `condition` holds.\"\"\"
    if not message:
        raise ValueError("require() needs a message")
    if not condition:
        raise ValidationError(message)""",
    correct_robust="""def require(condition, message):
    \"\"\"Raise ValidationError with `message` unless `condition` holds.\"\"\"
    if not str(message).strip():
        raise ValueError("require() needs a message")
    if condition:
        return None
    raise ValidationError(message)""",
    visible_test=_test_module(
        "preconditions",
        "Published contract for the precondition helper.",
        """
import pytest


def test_a_satisfied_precondition_returns_none() -> None:
    assert require(True, "ok") is None


def test_a_violated_precondition_raises() -> None:
    with pytest.raises(Exception):
        require(False, "bad")


def test_a_truthy_condition_is_accepted() -> None:
    assert require(1, "ok") is None
""",
        imports="from preconditions import require\n",
    ),
    hidden_test=_test_module(
        "preconditions",
        "The part of the contract the published tests do not state.",
        """
import pytest
from preconditions import ValidationError


def test_a_satisfied_precondition_returns_none() -> None:
    assert require(True, "ok") is None


def test_an_empty_message_is_rejected() -> None:
    with pytest.raises(ValueError):
        require(True, "")


def test_an_empty_message_is_rejected_even_when_violated() -> None:
    with pytest.raises(ValueError):
        require(False, "")


def test_a_violated_precondition_raises_the_domain_error() -> None:
    with pytest.raises(ValidationError):
        require(False, "bad")


def test_the_message_reaches_the_domain_error() -> None:
    with pytest.raises(ValidationError) as info:
        require(False, "the widget must exist")
    assert "widget" in str(info.value)
""",
        imports="from preconditions import require\n",
    ),
)

# ----------------------------------------------------------------------- data transformation

_D1 = TaskSpec(
    template_id="data_transformation.group_by",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="transform-grouping",
    module="grouping",
    module_doc="Group rows by the value of one field.",
    issue=(
        "group_by() returns its groups in sorted order rather than the order they first "
        "appeared, which reorders every downstream report. A row that is missing the grouping "
        "field is also collected under a None group instead of being reported."
    ),
    expected=(
        "group_by(rows, key) returns groups in first-appearance order and raises KeyError "
        "naming the field when a row does not have it."
    ),
    baseline_reason="the result is sorted and a missing field is silently grouped under None",
    edge_cases=("groups keep first-appearance order", "a row missing the field raises KeyError"),
    baseline="""def group_by(rows, key):
    \"\"\"Group `rows` into a dict keyed by each row's `key` value.\"\"\"
    groups = {}
    for row in rows:
        groups.setdefault(row.get(key), []).append(row)
    return dict(sorted(groups.items(), key=lambda item: str(item[0])))""",
    incomplete_a="""def group_by(rows, key):
    \"\"\"Group `rows` into a dict keyed by each row's `key` value.\"\"\"
    groups = {}
    for row in rows:
        groups.setdefault(row.get(key), []).append(row)
    return groups""",
    incomplete_b="""def group_by(rows, key):
    \"\"\"Group `rows` into a dict keyed by each row's `key` value.\"\"\"
    groups = {}
    for row in rows:
        if key not in row:
            raise KeyError(key)
        groups.setdefault(row[key], []).append(row)
    return dict(sorted(groups.items(), key=lambda item: str(item[0])))""",
    correct_narrow="""def group_by(rows, key):
    \"\"\"Group `rows` into a dict keyed by each row's `key` value.\"\"\"
    groups = {}
    for row in rows:
        if key not in row:
            raise KeyError(key)
        groups.setdefault(row[key], []).append(row)
    return groups""",
    correct_robust="""def group_by(rows, key):
    \"\"\"Group `rows` into a dict keyed by each row's `key` value.\"\"\"
    ordered = {}
    for row in rows:
        try:
            value = row[key]
        except KeyError:
            raise KeyError(key) from None
        ordered.setdefault(value, [])
        ordered[value].append(row)
    return ordered""",
    visible_test=_test_module(
        "grouping",
        "Published contract for the grouping helper.",
        """
def test_two_groups() -> None:
    rows = [{"k": "a", "v": 1}, {"k": "b", "v": 2}]
    assert group_by(rows, "k") == {"a": [rows[0]], "b": [rows[1]]}


def test_one_group_with_two_rows() -> None:
    rows = [{"k": "a"}, {"k": "a"}]
    assert group_by(rows, "k") == {"a": rows}


def test_no_rows() -> None:
    assert group_by([], "k") == {}
""",
        imports="from grouping import group_by\n",
    ),
    hidden_test=_test_module(
        "grouping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_groups() -> None:
    rows = [{"k": "a", "v": 1}, {"k": "b", "v": 2}]
    assert group_by(rows, "k") == {"a": [rows[0]], "b": [rows[1]]}


def test_groups_keep_first_appearance_order() -> None:
    rows = [{"k": "b"}, {"k": "a"}]
    assert list(group_by(rows, "k")) == ["b", "a"]


def test_a_later_first_appearance_stays_later() -> None:
    rows = [{"k": "z"}, {"k": "m"}, {"k": "z"}]
    assert list(group_by(rows, "k")) == ["z", "m"]


def test_a_row_missing_the_field_is_reported() -> None:
    with pytest.raises(KeyError):
        group_by([{"other": 1}], "k")


def test_a_missing_field_names_the_field() -> None:
    with pytest.raises(KeyError) as info:
        group_by([{"k": "a"}, {"other": 1}], "k")
    assert "k" in str(info.value)
""",
        imports="from grouping import group_by\n",
    ),
)

_D2 = TaskSpec(
    template_id="data_transformation.invert",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="transform-inversion",
    module="inversion",
    module_doc="Invert a mapping of key to value.",
    issue=(
        "invert() stringifies every value on its way to becoming a key, so an integer identifier "
        "comes back as text and no longer matches the original. Duplicate values also collapse "
        "silently, so the inverted mapping quietly loses entries."
    ),
    expected=(
        "invert(mapping) returns values as keys unchanged, and raises ValueError when two keys "
        "share a value."
    ),
    baseline_reason="str() rewrites every key and duplicate values overwrite each other",
    edge_cases=("value types are preserved", "duplicate values raise ValueError"),
    baseline="""def invert(mapping):
    \"\"\"Return `mapping` with keys and values swapped.\"\"\"
    return {str(value): key for key, value in mapping.items()}""",
    incomplete_a="""def invert(mapping):
    \"\"\"Return `mapping` with keys and values swapped.\"\"\"
    return {value: key for key, value in mapping.items()}""",
    incomplete_b="""def invert(mapping):
    \"\"\"Return `mapping` with keys and values swapped.\"\"\"
    values = list(mapping.values())
    if len(set(values)) != len(values):
        raise ValueError("cannot invert a mapping with duplicate values")
    return {str(value): key for key, value in mapping.items()}""",
    correct_narrow="""def invert(mapping):
    \"\"\"Return `mapping` with keys and values swapped.\"\"\"
    values = list(mapping.values())
    if len(set(values)) != len(values):
        raise ValueError("cannot invert a mapping with duplicate values")
    return {value: key for key, value in mapping.items()}""",
    correct_robust="""def invert(mapping):
    \"\"\"Return `mapping` with keys and values swapped.\"\"\"
    inverted = {}
    for key, value in mapping.items():
        if value in inverted:
            raise ValueError(f"duplicate value: {value!r}")
        inverted[value] = key
    return inverted""",
    visible_test=_test_module(
        "inversion",
        "Published contract for mapping inversion.",
        """
def test_one_entry() -> None:
    assert invert({"a": "x"}) == {"x": "a"}


def test_two_entries() -> None:
    assert invert({"a": "x", "b": "y"}) == {"x": "a", "y": "b"}


def test_empty_mapping() -> None:
    assert invert({}) == {}
""",
        imports="from inversion import invert\n",
    ),
    hidden_test=_test_module(
        "inversion",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_entry() -> None:
    assert invert({"a": "x"}) == {"x": "a"}


def test_integer_values_stay_integers() -> None:
    assert invert({"a": 1}) == {1: "a"}


def test_a_round_trip_preserves_the_mapping() -> None:
    original = {"a": 1, "b": 2}
    assert invert(invert(original)) == original


def test_duplicate_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        invert({"a": "x", "b": "x"})


def test_duplicate_integer_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        invert({"a": 1, "b": 1})
""",
        imports="from inversion import invert\n",
    ),
)

_D3 = TaskSpec(
    template_id="data_transformation.rename_keys",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="transform-key-renaming",
    module="key_renaming",
    module_doc="Rename keys in a mapping.",
    issue=(
        "rename_keys() edits the mapping it was handed, so a caller that renamed a projection "
        "finds the stored record changed too. Renaming onto a key that already exists also "
        "destroys the existing entry without a word."
    ),
    expected=(
        "rename_keys(mapping, renames) returns a new mapping and raises ValueError when a "
        "rename target already exists."
    ),
    baseline_reason="pop and assign mutate the caller's mapping and overwrite the collision target",
    edge_cases=(
        "the input mapping is not mutated",
        "a rename onto an existing key raises ValueError",
    ),
    baseline="""def rename_keys(mapping, renames):
    \"\"\"Return `mapping` with keys renamed according to `renames`.\"\"\"
    for old, new in renames.items():
        if old in mapping:
            mapping[new] = mapping.pop(old)
    return mapping""",
    incomplete_a="""def rename_keys(mapping, renames):
    \"\"\"Return `mapping` with keys renamed according to `renames`.\"\"\"
    renamed = dict(mapping)
    for old, new in renames.items():
        if old in renamed:
            renamed[new] = renamed.pop(old)
    return renamed""",
    incomplete_b="""def rename_keys(mapping, renames):
    \"\"\"Return `mapping` with keys renamed according to `renames`.\"\"\"
    for old, new in renames.items():
        if old in mapping:
            if new in mapping:
                raise ValueError(f"rename target already exists: {new!r}")
            mapping[new] = mapping.pop(old)
    return mapping""",
    correct_narrow="""def rename_keys(mapping, renames):
    \"\"\"Return `mapping` with keys renamed according to `renames`.\"\"\"
    renamed = dict(mapping)
    for old, new in renames.items():
        if old in renamed:
            if new in renamed:
                raise ValueError(f"rename target already exists: {new!r}")
            renamed[new] = renamed.pop(old)
    return renamed""",
    correct_robust="""def rename_keys(mapping, renames):
    \"\"\"Return `mapping` with keys renamed according to `renames`.\"\"\"
    collisions = {
        new for old, new in renames.items() if old in mapping and new in mapping
    }
    if collisions:
        raise ValueError(f"rename targets already exist: {sorted(collisions)}")
    return {renames.get(key, key): value for key, value in mapping.items()}""",
    visible_test=_test_module(
        "key_renaming",
        "Published contract for key renaming.",
        """
def test_one_rename() -> None:
    assert rename_keys({"a": 1}, {"a": "b"}) == {"b": 1}


def test_an_unmatched_rename_is_ignored() -> None:
    assert rename_keys({"a": 1}, {"z": "y"}) == {"a": 1}


def test_no_renames() -> None:
    assert rename_keys({"a": 1}, {}) == {"a": 1}
""",
        imports="from key_renaming import rename_keys\n",
    ),
    hidden_test=_test_module(
        "key_renaming",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_rename() -> None:
    assert rename_keys({"a": 1}, {"a": "b"}) == {"b": 1}


def test_the_input_mapping_is_not_mutated() -> None:
    mapping = {"a": 1}
    rename_keys(mapping, {"a": "b"})
    assert mapping == {"a": 1}


def test_renaming_twice_from_the_same_mapping_agrees() -> None:
    mapping = {"a": 1}
    assert rename_keys(mapping, {"a": "b"}) == rename_keys(mapping, {"a": "b"})


def test_a_collision_is_rejected() -> None:
    with pytest.raises(ValueError):
        rename_keys({"a": 1, "b": 2}, {"a": "b"})


def test_a_collision_does_not_destroy_the_target() -> None:
    mapping = {"a": 1, "b": 2}
    with pytest.raises(ValueError):
        rename_keys(mapping, {"a": "b"})
    assert mapping["b"] == 2
""",
        imports="from key_renaming import rename_keys\n",
    ),
)

_D4 = TaskSpec(
    template_id="data_transformation.to_records",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="transform-columns-to-rows",
    module="columns_to_rows",
    module_doc="Turn a column-oriented table into row records.",
    issue=(
        "to_records() truncates to the shortest column when the columns have different lengths, "
        "so rows disappear without any error. It also accepts a table with no columns at all and "
        "returns an empty result that looks like an empty table."
    ),
    expected=(
        "to_records(columns) raises ValueError when the columns have different lengths, and "
        "raises ValueError when no columns are given."
    ),
    baseline_reason="zip stops at the shortest column and an empty column set is not rejected",
    edge_cases=("ragged columns raise ValueError", "an empty column set raises ValueError"),
    baseline="""def to_records(columns):
    \"\"\"Turn a mapping of column name to values into a list of row dicts.\"\"\"
    names = list(columns)
    return [
        dict(zip(names, values, strict=False))
        for values in zip(*columns.values(), strict=False)
    ]""",
    incomplete_a="""def to_records(columns):
    \"\"\"Turn a mapping of column name to values into a list of row dicts.\"\"\"
    names = list(columns)
    lengths = {len(values) for values in columns.values()}
    if len(lengths) > 1:
        raise ValueError("every column must have the same length")
    return [
        dict(zip(names, values, strict=False))
        for values in zip(*columns.values(), strict=False)
    ]""",
    incomplete_b="""def to_records(columns):
    \"\"\"Turn a mapping of column name to values into a list of row dicts.\"\"\"
    if not columns:
        raise ValueError("to_records() needs at least one column")
    names = list(columns)
    return [
        dict(zip(names, values, strict=False))
        for values in zip(*columns.values(), strict=False)
    ]""",
    correct_narrow="""def to_records(columns):
    \"\"\"Turn a mapping of column name to values into a list of row dicts.\"\"\"
    if not columns:
        raise ValueError("to_records() needs at least one column")
    lengths = {len(values) for values in columns.values()}
    if len(lengths) > 1:
        raise ValueError("every column must have the same length")
    names = list(columns)
    return [
        dict(zip(names, values, strict=False))
        for values in zip(*columns.values(), strict=False)
    ]""",
    correct_robust="""def to_records(columns):
    \"\"\"Turn a mapping of column name to values into a list of row dicts.\"\"\"
    if not columns:
        raise ValueError("to_records() needs at least one column")
    names = list(columns)
    height = len(columns[names[0]])
    for name in names:
        if len(columns[name]) != height:
            raise ValueError(f"column {name!r} has a different length")
    return [{name: columns[name][index] for name in names} for index in range(height)]""",
    visible_test=_test_module(
        "columns_to_rows",
        "Published contract for the column-to-row transform.",
        """
def test_two_columns() -> None:
    assert to_records({"a": [1, 2], "b": [3, 4]}) == [{"a": 1, "b": 3}, {"a": 2, "b": 4}]


def test_one_column() -> None:
    assert to_records({"a": [1]}) == [{"a": 1}]


def test_one_column_with_no_values() -> None:
    assert to_records({"a": []}) == []
""",
        imports="from columns_to_rows import to_records\n",
    ),
    hidden_test=_test_module(
        "columns_to_rows",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_columns() -> None:
    assert to_records({"a": [1, 2], "b": [3, 4]}) == [{"a": 1, "b": 3}, {"a": 2, "b": 4}]


def test_a_short_column_is_rejected() -> None:
    with pytest.raises(ValueError):
        to_records({"a": [1, 2], "b": [3]})


def test_a_long_column_is_rejected() -> None:
    with pytest.raises(ValueError):
        to_records({"a": [1], "b": [3, 4]})


def test_an_empty_column_set_is_rejected() -> None:
    with pytest.raises(ValueError):
        to_records({})
""",
        imports="from columns_to_rows import to_records\n",
    ),
)

_D5 = TaskSpec(
    template_id="data_transformation.summarize",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="transform-summaries",
    module="summaries",
    module_doc="Summarize one numeric field across rows.",
    issue=(
        "summarize() crashes with ZeroDivisionError on an empty result set, which every report "
        "with a filter eventually produces. A non-numeric value also produces a TypeError from "
        "deep inside sum() that never names the field responsible."
    ),
    expected=(
        "summarize(rows, field) returns zeroed counts for no rows, and raises TypeError naming "
        "the field when a value is not numeric."
    ),
    baseline_reason="the mean divides by zero for no rows and sum() reports no field name",
    edge_cases=("no rows returns zeroed counts", "a non-numeric value names the field"),
    baseline="""def summarize(rows, field):
    \"\"\"Return count, total and mean of `field` across `rows`.\"\"\"
    values = [row[field] for row in rows]
    return {
        "count": len(values),
        "total": sum(values),
        "mean": sum(values) / len(values),
    }""",
    incomplete_a="""def summarize(rows, field):
    \"\"\"Return count, total and mean of `field` across `rows`.\"\"\"
    values = [row[field] for row in rows]
    if not values:
        return {"count": 0, "total": 0, "mean": 0.0}
    return {
        "count": len(values),
        "total": sum(values),
        "mean": sum(values) / len(values),
    }""",
    incomplete_b="""def summarize(rows, field):
    \"\"\"Return count, total and mean of `field` across `rows`.\"\"\"
    values = []
    for row in rows:
        value = row[field]
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise TypeError(f"field {field!r} is not numeric")
        values.append(value)
    return {
        "count": len(values),
        "total": sum(values),
        "mean": sum(values) / len(values),
    }""",
    correct_narrow="""def summarize(rows, field):
    \"\"\"Return count, total and mean of `field` across `rows`.\"\"\"
    values = []
    for row in rows:
        value = row[field]
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise TypeError(f"field {field!r} is not numeric")
        values.append(value)
    if not values:
        return {"count": 0, "total": 0, "mean": 0.0}
    return {
        "count": len(values),
        "total": sum(values),
        "mean": sum(values) / len(values),
    }""",
    correct_robust="""def summarize(rows, field):
    \"\"\"Return count, total and mean of `field` across `rows`.\"\"\"
    values = [row[field] for row in rows]
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"field {field!r} is not numeric")
    count = len(values)
    total = sum(values)
    return {"count": count, "total": total, "mean": total / count if count else 0.0}""",
    visible_test=_test_module(
        "summaries",
        "Published contract for the summary helper.",
        """
def test_two_rows() -> None:
    assert summarize([{"v": 1}, {"v": 3}], "v") == {"count": 2, "total": 4, "mean": 2.0}


def test_one_row() -> None:
    assert summarize([{"v": 5}], "v") == {"count": 1, "total": 5, "mean": 5.0}


def test_float_values() -> None:
    assert summarize([{"v": 1.5}, {"v": 2.5}], "v")["total"] == 4.0
""",
        imports="from summaries import summarize\n",
    ),
    hidden_test=_test_module(
        "summaries",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_two_rows() -> None:
    assert summarize([{"v": 1}, {"v": 3}], "v") == {"count": 2, "total": 4, "mean": 2.0}


def test_no_rows_returns_zeroed_counts() -> None:
    assert summarize([], "v") == {"count": 0, "total": 0, "mean": 0.0}


def test_no_rows_does_not_raise() -> None:
    assert summarize([], "anything")["count"] == 0


def test_a_non_numeric_value_names_the_field() -> None:
    with pytest.raises(TypeError) as info:
        summarize([{"v": "x"}], "v")
    assert "v" in str(info.value)


def test_a_non_numeric_value_among_numbers_names_the_field() -> None:
    with pytest.raises(TypeError) as info:
        summarize([{"v": 1}, {"v": None}], "v")
    assert "v" in str(info.value)
""",
        imports="from summaries import summarize\n",
    ),
)


TASK_SPECS: tuple[TaskSpec, ...] = (
    _B1,
    _B2,
    _B3,
    _B4,
    _B5,
    _P1,
    _P2,
    _P3,
    _P4,
    _P5,
    _S1,
    _S2,
    _S3,
    _S4,
    _S5,
    _N1,
    _N2,
    _N3,
    _N4,
    _N5,
    _H1,
    _H2,
    _H3,
    _H4,
    _H5,
    _D1,
    _D2,
    _D3,
    _D4,
    _D5,
)
