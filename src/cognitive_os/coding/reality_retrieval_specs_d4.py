"""The Sprint 21D4 retrieval source pool, §S21D4-030.

D4 needs its own unseen-task queries for the same reason it needs its own calibration corpus:
D3's pool was authored before D3's arms were frozen, so reusing it would put the retrieval
evidence inside the window the D4 contracts seal. Sixty fresh groups are authored here, and
S21D4-031 keeps whichever survive integrity filtering.

The spec shape is D3's `D3RetrievalSpec`, unchanged and deliberately so. The projection, the
holdout and the query builder already agree about it; a second dataclass carrying the same
fields under a D4 name would give them a second thing to agree about, which is the same
argument that kept the calibration corpus on `D2TaskSpec`.

A retrieval group stays lighter than a correction group. Retrieval is evaluated on projected
graphs and edit paths rather than on ranked candidates, and `project_correction` needs one thing
from a trajectory: a step the verifier rejected, then one it accepted. So each group here is one
defect and its repair, not four candidates around two independent edge cases.

Both bodies are executed rather than declared: the failed body must fail the hidden suite and
the repaired body must pass it. That is what makes the pair causal evidence instead of two files
that happen to differ.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_retrieval_specs_d3 import D3RetrievalSpec, _hidden

_BOUNDARY = RealityTaskFamily.BOUNDARY_COLLECTIONS
_PARSING = RealityTaskFamily.PARSING_VALIDATION
_STATE = RealityTaskFamily.STATE_IDEMPOTENCY
_NUMERIC = RealityTaskFamily.NUMERIC_LOGIC
_ERRORS = RealityTaskFamily.ERROR_HANDLING
_TRANSFORM = RealityTaskFamily.DATA_TRANSFORMATION


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
) -> D3RetrievalSpec:
    """One row of the table, under a `d4r-` repository prefix.

    A local builder rather than D3's: the two differ in the prefix alone, and importing a
    private helper to pass it a flag would be a wider change than repeating four lines.
    """
    return D3RetrievalSpec(
        template_id=name,
        family=family,
        repository_group=f"d4r-{name.split('.', 1)[1].replace('_', '-')}",
        module=module,
        module_doc=doc,
        issue=issue,
        expected=expected,
        failure_reason=reason,
        failed=failed,
        repaired=repaired,
        hidden_test=_hidden(module, test_body, imports=f"from {module} import *\n"),
    )


D4_RETRIEVAL_SPECS: tuple[D3RetrievalSpec, ...] = (
    # ------------------------------------------------------------ boundary and collections
    _spec(
        "d4r_boundary.first_missing_positive",
        _BOUNDARY,
        "missing_positive",
        "Finding the smallest counting number a batch does not use.",
        "first_missing_positive() answers one past the batch even when a number is skipped.",
        "first_missing_positive(numbers) returns the smallest counting number not in numbers.",
        "it counts the batch instead of looking for the gap in it",
        """def first_missing_positive(numbers):
    return len(numbers) + 1""",
        """def first_missing_positive(numbers):
    present = set(numbers)
    candidate = 1
    while candidate in present:
        candidate += 1
    return candidate""",
        """
def test_the_gap_is_found() -> None:
    assert first_missing_positive([1, 2, 4]) == 3


def test_an_unbroken_run_answers_one_past_the_end() -> None:
    assert first_missing_positive([1, 2, 3]) == 4
""",
    ),
    _spec(
        "d4r_boundary.last_n",
        _BOUNDARY,
        "tail_slice",
        "Taking the last few entries of a log.",
        "last_n() hands back the whole log when asked for none of it.",
        "last_n(items, count) returns the final count entries, and nothing for a count of zero.",
        "the slice items[-count:] means the whole sequence when count is zero",
        """def last_n(items, count):
    return items[-count:]""",
        """def last_n(items, count):
    if count <= 0:
        return []
    return items[-count:]""",
        """
def test_asking_for_none_returns_none() -> None:
    assert last_n([1, 2, 3], 0) == []


def test_asking_for_two_returns_the_last_two() -> None:
    assert last_n([1, 2, 3], 2) == [2, 3]
""",
    ),
    _spec(
        "d4r_boundary.starts_with",
        _BOUNDARY,
        "opening_match",
        "Asking whether a sequence opens with a given run.",
        "starts_with() says yes when the run turns up anywhere, not only at the opening.",
        "starts_with(items, opening) is true only when the run sits at the very front.",
        "it asks whether the run appears at all rather than where it appears",
        """def starts_with(items, opening):
    return all(entry in items for entry in opening)""",
        """def starts_with(items, opening):
    return list(items[: len(opening)]) == list(opening)""",
        """
def test_a_run_that_turns_up_later_does_not_count() -> None:
    assert starts_with([1, 2, 3], [2, 3]) is False


def test_a_run_at_the_front_counts() -> None:
    assert starts_with([1, 2, 3], [1, 2]) is True
""",
    ),
    _spec(
        "d4r_boundary.second_largest",
        _BOUNDARY,
        "runner_up",
        "Reporting the runner-up among a set of readings.",
        "second_largest() reports the winner again when the winner is tied with itself.",
        "second_largest(values) returns the largest value strictly below the largest.",
        "it sorts and takes the second entry, which for a tied winner is the winner",
        """def second_largest(values):
    return sorted(values, reverse=True)[1]""",
        """def second_largest(values):
    distinct = sorted(set(values), reverse=True)
    return distinct[1]""",
        """
def test_a_tied_winner_does_not_win_twice() -> None:
    assert second_largest([9, 9, 4]) == 4


def test_an_ordinary_runner_up() -> None:
    assert second_largest([1, 9, 4]) == 4
""",
    ),
    _spec(
        "d4r_boundary.drop_trailing",
        _BOUNDARY,
        "trailing_drop",
        "Dropping the padding entries a record ends with.",
        "drop_trailing() removes every padding entry rather than only the ones at the end.",
        "drop_trailing(items, padding) drops padding from the end only and keeps it elsewhere.",
        "it filters the whole sequence instead of stopping at the last real entry",
        """def drop_trailing(items, padding):
    return [item for item in items if item != padding]""",
        """def drop_trailing(items, padding):
    kept = list(items)
    while kept and kept[-1] == padding:
        kept.pop()
    return kept""",
        """
def test_only_the_padding_at_the_end_goes() -> None:
    assert drop_trailing([1, 0, 2, 0, 0], 0) == [1, 0, 2]


def test_a_record_of_nothing_but_padding() -> None:
    assert drop_trailing([0, 0], 0) == []
""",
    ),
    _spec(
        "d4r_boundary.middle_item",
        _BOUNDARY,
        "middle_pick",
        "Picking the middle entry of a sorted sample.",
        "middle_item() takes the later of the two middles when the sample is of even size.",
        "middle_item(items) returns the middle entry, and the earlier middle for an even size.",
        "the halving rounds up where the contract rounds down",
        """def middle_item(items):
    return items[len(items) // 2]""",
        """def middle_item(items):
    return items[(len(items) - 1) // 2]""",
        """
def test_an_even_sample_takes_the_earlier_middle() -> None:
    assert middle_item([1, 2, 3, 4]) == 2


def test_an_odd_sample_takes_the_middle() -> None:
    assert middle_item([1, 2, 3]) == 2
""",
    ),
    _spec(
        "d4r_boundary.take_while_rising",
        _BOUNDARY,
        "rising_prefix",
        "Taking the opening run of readings that never falls.",
        "take_while_rising() stops at two equal readings, which is not a fall.",
        "take_while_rising(values) returns the opening run in which no reading falls.",
        "the comparison is strict, so a flat step reads as the end of the run",
        """def take_while_rising(values):
    run = []
    for value in values:
        if run and value <= run[-1]:
            break
        run.append(value)
    return run""",
        """def take_while_rising(values):
    run = []
    for value in values:
        if run and value < run[-1]:
            break
        run.append(value)
    return run""",
        """
def test_a_flat_step_does_not_end_the_run() -> None:
    assert take_while_rising([1, 2, 2, 3, 1]) == [1, 2, 2, 3]


def test_a_fall_ends_the_run() -> None:
    assert take_while_rising([3, 1]) == [3]
""",
    ),
    _spec(
        "d4r_boundary.positions_of",
        _BOUNDARY,
        "all_positions",
        "Listing every position a value occupies.",
        "positions_of() reports only the first position and stops there.",
        "positions_of(items, value) returns every index holding value, in order.",
        "it returns from inside the loop on the first match",
        """def positions_of(items, value):
    for index, entry in enumerate(items):
        if entry == value:
            return [index]
    return []""",
        """def positions_of(items, value):
    return [index for index, entry in enumerate(items) if entry == value]""",
        """
def test_every_position_is_reported() -> None:
    assert positions_of([1, 2, 1, 1], 1) == [0, 2, 3]


def test_a_value_that_is_not_there() -> None:
    assert positions_of([1, 2], 9) == []
""",
    ),
    _spec(
        "d4r_boundary.split_in_half",
        _BOUNDARY,
        "half_division",
        "Cutting a work list into two halves.",
        "split_in_half() gives the odd entry to the second half instead of the first.",
        "split_in_half(items) returns (first, second) with the odd entry in the first half.",
        "the cut point rounds down where the contract rounds up",
        """def split_in_half(items):
    cut = len(items) // 2
    return items[:cut], items[cut:]""",
        """def split_in_half(items):
    cut = (len(items) + 1) // 2
    return items[:cut], items[cut:]""",
        """
def test_an_odd_count_puts_the_extra_in_the_first_half() -> None:
    assert split_in_half([1, 2, 3]) == ([1, 2], [3])


def test_an_even_count_splits_evenly() -> None:
    assert split_in_half([1, 2, 3, 4]) == ([1, 2], [3, 4])
""",
    ),
    _spec(
        "d4r_boundary.nth_from_end",
        _BOUNDARY,
        "from_the_end",
        "Reading an entry counted back from the end.",
        "nth_from_end() is one out: asking for the first from the end gives the second.",
        "nth_from_end(items, count) counts from one, so a count of one is the final entry.",
        "it uses the count as an offset from the end rather than a one-based position",
        """def nth_from_end(items, count):
    return items[-count - 1]""",
        """def nth_from_end(items, count):
    return items[-count]""",
        """
def test_one_from_the_end_is_the_last_entry() -> None:
    assert nth_from_end([1, 2, 3], 1) == 3


def test_two_from_the_end() -> None:
    assert nth_from_end([1, 2, 3], 2) == 2
""",
    ),
    # ------------------------------------------------------------------ parsing and validation
    _spec(
        "d4r_parsing.strip_prefix_once",
        _PARSING,
        "prefix_removal",
        "Taking a known prefix off a label.",
        "strip_prefix_once() eats any of the prefix's letters from the front, not the prefix.",
        "strip_prefix_once(label, prefix) removes the prefix once and otherwise changes nothing.",
        "lstrip takes a set of characters, not a prefix, so it keeps eating",
        """def strip_prefix_once(label, prefix):
    return label.lstrip(prefix)""",
        """def strip_prefix_once(label, prefix):
    if label.startswith(prefix):
        return label[len(prefix) :]
    return label""",
        """
def test_only_the_prefix_goes() -> None:
    assert strip_prefix_once("app_apple", "app_") == "apple"


def test_a_label_without_the_prefix_is_untouched() -> None:
    assert strip_prefix_once("apple", "app_") == "apple"
""",
    ),
    _spec(
        "d4r_parsing.parse_dotted_name",
        _PARSING,
        "dotted_names",
        "Reading a dotted name as its parts.",
        "parse_dotted_name() swallows an empty part instead of refusing the name.",
        "parse_dotted_name(text) returns the parts and raises ValueError for an empty one.",
        "it drops the empty part instead of refusing the name that carries one",
        """def parse_dotted_name(text):
    return list(filter(None, text.split(".")))""",
        """def parse_dotted_name(text):
    parts = text.split(".")
    if any(not part for part in parts):
        raise ValueError("a dotted name has no empty parts")
    return parts""",
        """
import pytest

from dotted_names import parse_dotted_name


def test_an_ordinary_name() -> None:
    assert parse_dotted_name("a.b.c") == ["a", "b", "c"]


def test_an_empty_part_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_dotted_name("a..c")
""",
    ),
    _spec(
        "d4r_parsing.join_path",
        _PARSING,
        "path_joining",
        "Joining path segments into one path.",
        "join_path() doubles the separator when a segment already ends with one.",
        "join_path(segments) joins with exactly one separator between neighbouring segments.",
        "it joins the raw segments without trimming the separators they carry",
        """def join_path(segments):
    return "/".join(segments)""",
        """def join_path(segments):
    return "/".join(segment.strip("/") for segment in segments if segment.strip("/"))""",
        """
def test_a_segment_that_already_ends_with_a_separator() -> None:
    assert join_path(["a/", "b"]) == "a/b"


def test_plain_segments() -> None:
    assert join_path(["a", "b", "c"]) == "a/b/c"
""",
    ),
    _spec(
        "d4r_parsing.parse_int_or_none",
        _PARSING,
        "lenient_integers",
        "Reading a number that may not be there.",
        "parse_int_or_none() answers nothing for a number written below zero.",
        "parse_int_or_none(text) returns the integer, negative ones included, or None.",
        "isdigit is false for a leading minus sign, so a negative number reads as no number",
        """def parse_int_or_none(text):
    if text.isdigit():
        return int(text)
    return None""",
        """def parse_int_or_none(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None""",
        """
def test_a_number_below_zero_is_read() -> None:
    assert parse_int_or_none("-5") == -5


def test_text_that_is_not_a_number_answers_nothing() -> None:
    assert parse_int_or_none("later") is None
""",
    ),
    _spec(
        "d4r_parsing.normalise_whitespace",
        _PARSING,
        "whitespace_normalising",
        "Squeezing the runs of blanks in a line down to one.",
        "normalise_whitespace() squeezes a doubled blank but leaves a longer run standing.",
        "normalise_whitespace(text) trims the ends and squeezes every inner run to one space.",
        "one pass over the text turns two blanks into one and never comes back for three",
        """def normalise_whitespace(text):
    squeezed = text.replace("  ", " ")
    return squeezed.strip()""",
        """def normalise_whitespace(text):
    return " ".join(text.split())""",
        """
def test_a_run_inside_the_line_is_squeezed() -> None:
    assert normalise_whitespace("  a   b  ") == "a b"


def test_a_line_already_tidy() -> None:
    assert normalise_whitespace("a b") == "a b"
""",
    ),
    _spec(
        "d4r_parsing.parse_flag_value",
        _PARSING,
        "flag_values",
        "Reading a command-line flag and whatever it carries.",
        "parse_flag_value() brings the caller down on a flag written with no value.",
        "parse_flag_value(text) returns (name, value), and (name, True) for a bare flag.",
        "it splits at the equals sign and unpacks two parts whether or not there are two",
        """def parse_flag_value(text):
    name, value = text.lstrip("-").split("=")
    return name, value""",
        """def parse_flag_value(text):
    name, sign, value = text.lstrip("-").partition("=")
    return name, value if sign else True""",
        """
def test_a_bare_flag_carries_a_yes() -> None:
    assert parse_flag_value("--verbose") == ("verbose", True)


def test_a_flag_with_a_value() -> None:
    assert parse_flag_value("--name=ada") == ("name", "ada")
""",
    ),
    _spec(
        "d4r_parsing.parse_mac_address",
        _PARSING,
        "mac_addresses",
        "Reading a hardware address as its six bytes.",
        "parse_mac_address() accepts an address with the wrong number of parts.",
        "parse_mac_address(text) returns six byte values and refuses any other count.",
        "it converts whatever parts it finds without counting them first",
        """def parse_mac_address(text):
    return [int(part, 16) for part in text.split(":")]""",
        """def parse_mac_address(text):
    parts = text.split(":")
    if len(parts) != 6:
        raise ValueError("a hardware address has six parts")
    return [int(part, 16) for part in parts]""",
        """
import pytest

from mac_addresses import parse_mac_address


def test_a_full_address() -> None:
    assert parse_mac_address("00:1b:44:11:3a:b7") == [0, 27, 68, 17, 58, 183]


def test_too_few_parts_are_refused() -> None:
    with pytest.raises(ValueError):
        parse_mac_address("00:1b:44")
""",
    ),
    _spec(
        "d4r_parsing.title_from_slug",
        _PARSING,
        "slug_titles",
        "Turning a page slug back into a title.",
        "title_from_slug() capitalises the first word only and leaves the rest lower case.",
        "title_from_slug(slug) capitalises every word and separates them with spaces.",
        "capitalize works on the whole string, which lower-cases everything after the first letter",
        """def title_from_slug(slug):
    return slug.replace("-", " ").capitalize()""",
        """def title_from_slug(slug):
    return " ".join(word.capitalize() for word in slug.split("-") if word)""",
        """
def test_every_word_is_capitalised() -> None:
    assert title_from_slug("my-page-title") == "My Page Title"


def test_a_single_word() -> None:
    assert title_from_slug("index") == "Index"
""",
    ),
    _spec(
        "d4r_parsing.parse_grouped_number",
        _PARSING,
        "grouped_numbers",
        "Reading a number written with thousands separators.",
        "parse_grouped_number() reads past the first separator only and refuses the rest.",
        "parse_grouped_number(text) returns the integer, ignoring the thousands separators.",
        "only the first separator is taken out, and int() refuses the ones still there",
        """def parse_grouped_number(text):
    return int(text.replace(",", "", 1))""",
        """def parse_grouped_number(text):
    return int(text.replace(",", ""))""",
        """
def test_a_number_with_separators() -> None:
    assert parse_grouped_number("1,234,567") == 1234567


def test_a_number_without_them() -> None:
    assert parse_grouped_number("42") == 42
""",
    ),
    _spec(
        "d4r_parsing.trailing_number",
        _PARSING,
        "name_suffixes",
        "Reading the number a name ends with.",
        "trailing_number() reports the first number in the name rather than the last.",
        "trailing_number(name) returns the number the name ends with, or None for none.",
        "it scans forward for digits instead of back from the end",
        """def trailing_number(name):
    digits = ""
    for letter in name:
        if letter.isdigit():
            digits += letter
        elif digits:
            break
    return int(digits) if digits else None""",
        """def trailing_number(name):
    digits = ""
    for letter in reversed(name):
        if not letter.isdigit():
            break
        digits = letter + digits
    return int(digits) if digits else None""",
        """
def test_the_number_at_the_end_wins() -> None:
    assert trailing_number("host1-worker27") == 27


def test_a_name_ending_in_a_letter_has_no_number() -> None:
    assert trailing_number("worker") is None
""",
    ),
    # ------------------------------------------------------------------- state and idempotency
    _spec(
        "d4r_state.add_tag",
        _STATE,
        "tag_addition",
        "Adding a tag to a record.",
        "add_tag() adds the same tag again every time it is called.",
        "add_tag(record, tag) adds the tag once however often it is called.",
        "it appends without asking whether the tag is already there",
        """def add_tag(record, tag):
    tagged = dict(record)
    tagged["tags"] = [*record["tags"], tag]
    return tagged""",
        """def add_tag(record, tag):
    tags = record["tags"]
    if tag in tags:
        return dict(record)
    return {**record, "tags": [*tags, tag]}""",
        """
def test_adding_the_same_tag_twice_adds_it_once() -> None:
    once = add_tag({"tags": []}, "urgent")
    assert add_tag(once, "urgent")["tags"] == ["urgent"]


def test_a_second_tag_is_added() -> None:
    assert add_tag({"tags": ["urgent"]}, "late")["tags"] == ["urgent", "late"]
""",
    ),
    _spec(
        "d4r_state.remove_member",
        _STATE,
        "member_removal",
        "Removing someone from a group.",
        "remove_member() brings the caller down when the member has already gone.",
        "remove_member(group, name) returns (group, removed) and is quiet about an absent name.",
        "list.remove raises for a name that is not there",
        """def remove_member(group, name):
    members = list(group)
    members.remove(name)
    return members, True""",
        """def remove_member(group, name):
    if name not in group:
        return list(group), False
    members = list(group)
    members.remove(name)
    return members, True""",
        """
def test_removing_someone_who_has_already_gone() -> None:
    assert remove_member(["ada"], "bo") == (["ada"], False)


def test_removing_a_member() -> None:
    assert remove_member(["ada", "bo"], "bo") == (["ada"], True)
""",
    ),
    _spec(
        "d4r_state.set_default",
        _STATE,
        "default_setting",
        "Filling in a setting the caller left out.",
        "set_default() overwrites a setting the caller did choose.",
        "set_default(settings, name, value) writes the value only when the name is absent.",
        "it assigns unconditionally instead of asking whether the name is already there",
        """def set_default(settings, name, value):
    return {**settings, **{name: value}}""",
        """def set_default(settings, name, value):
    if name in settings:
        return dict(settings)
    filled = dict(settings)
    filled[name] = value
    return filled""",
        """
def test_a_setting_the_caller_chose_is_left_alone() -> None:
    assert set_default({"level": "debug"}, "level", "info") == {"level": "debug"}


def test_a_setting_left_out_is_filled_in() -> None:
    assert set_default({}, "level", "info") == {"level": "info"}
""",
    ),
    _spec(
        "d4r_state.mark_read",
        _STATE,
        "read_marking",
        "Recording when a message was first read.",
        "mark_read() moves the time forward every time the message is opened again.",
        "mark_read(message, at) keeps the time of the first reading.",
        "it writes the stamp without asking whether one is already recorded",
        """def mark_read(message, at):
    return {**message, "read_at": at}""",
        """def mark_read(message, at):
    if message.get("read_at") is not None:
        return dict(message)
    read = dict(message)
    read["read_at"] = at
    return read""",
        """
def test_the_first_reading_is_the_one_recorded() -> None:
    once = mark_read({"read_at": None}, 10)
    assert mark_read(once, 20)["read_at"] == 10


def test_an_unread_message_records_the_time() -> None:
    assert mark_read({"read_at": None}, 10)["read_at"] == 10
""",
    ),
    _spec(
        "d4r_state.move_between_queues",
        _STATE,
        "queue_moving",
        "Moving a job from one queue to another.",
        "move_between_queues() leaves the job in the queue it came from as well.",
        "move_between_queues(queues, job, source, target) moves the job rather than copying it.",
        "it appends to the target without taking the job out of the source",
        """def move_between_queues(queues, job, source, target):
    moved = {name: list(items) for name, items in queues.items()}
    moved[target].append(job)
    return moved""",
        """def move_between_queues(queues, job, source, target):
    moved = {name: list(items) for name, items in queues.items()}
    if job in moved[source]:
        moved[source].remove(job)
        moved[target].append(job)
    return moved""",
        """
def test_the_job_leaves_the_queue_it_came_from() -> None:
    moved = move_between_queues({"ready": ["j1"], "running": []}, "j1", "ready", "running")
    assert moved == {"ready": [], "running": ["j1"]}


def test_a_job_that_is_not_in_the_source_moves_nowhere() -> None:
    moved = move_between_queues({"ready": [], "running": []}, "j1", "ready", "running")
    assert moved == {"ready": [], "running": []}
""",
    ),
    _spec(
        "d4r_state.append_capped",
        _STATE,
        "capped_history",
        "Keeping a history of only the most recent entries.",
        "append_capped() lets the history grow without end.",
        "append_capped(history, entry, cap) keeps at most cap entries, dropping the oldest.",
        "it appends and never trims to the cap it was given",
        """def append_capped(history, entry, cap):
    return [*history, entry]""",
        """def append_capped(history, entry, cap):
    return [*history, entry][-cap:]""",
        """
def test_the_oldest_entry_is_dropped() -> None:
    assert append_capped(["a", "b"], "c", 2) == ["b", "c"]


def test_a_history_below_the_cap_keeps_everything() -> None:
    assert append_capped(["a"], "b", 3) == ["a", "b"]
""",
    ),
    _spec(
        "d4r_state.disable_feature",
        _STATE,
        "feature_disabling",
        "Turning a feature off.",
        "disable_feature() brings the caller down when the feature is already off.",
        "disable_feature(flags, name) turns the feature off and is quiet about one already off.",
        "it reaches for the flag and asserts its state instead of settling it",
        """def disable_feature(flags, name):
    if not flags[name]:
        raise ValueError("already off")
    turned = dict(flags)
    turned[name] = False
    return turned""",
        """def disable_feature(flags, name):
    turned = dict(flags)
    turned[name] = False
    return turned""",
        """
def test_turning_off_a_feature_already_off() -> None:
    assert disable_feature({"beta": False}, "beta") == {"beta": False}


def test_turning_off_a_feature_that_is_on() -> None:
    assert disable_feature({"beta": True}, "beta") == {"beta": False}
""",
    ),
    _spec(
        "d4r_state.acknowledge_all",
        _STATE,
        "bulk_acknowledgement",
        "Marking every unread alert as seen.",
        "acknowledge_all() restamps the alerts that were seen long ago.",
        "acknowledge_all(alerts, at) stamps only the alerts nobody has seen yet.",
        "it stamps every alert rather than only the ones still unseen",
        """def acknowledge_all(alerts, at):
    return {name: at for name in alerts}""",
        """def acknowledge_all(alerts, at):
    return {
        name: at if seen is None else seen for name, seen in alerts.items()
    }""",
        """
def test_an_alert_seen_long_ago_keeps_its_stamp() -> None:
    assert acknowledge_all({"disk": 5, "cpu": None}, 20) == {"disk": 5, "cpu": 20}


def test_an_unseen_alert_is_stamped() -> None:
    assert acknowledge_all({"cpu": None}, 20) == {"cpu": 20}
""",
    ),
    _spec(
        "d4r_state.claim_ticket",
        _STATE,
        "ticket_claiming",
        "Claiming a ticket nobody is working on.",
        "claim_ticket() takes a ticket out from under whoever already holds it.",
        "claim_ticket(tickets, number, owner) claims only an unclaimed ticket.",
        "it writes the new owner without asking whether there is one",
        """def claim_ticket(tickets, number, owner):
    claimed = dict(tickets)
    claimed[number] = owner
    return claimed, True""",
        """def claim_ticket(tickets, number, owner):
    if tickets.get(number) is not None:
        return dict(tickets), tickets[number] == owner
    claimed = dict(tickets)
    claimed[number] = owner
    return claimed, True""",
        """
def test_a_ticket_someone_else_holds_is_not_taken() -> None:
    assert claim_ticket({7: "ada"}, 7, "bo") == ({7: "ada"}, False)


def test_an_unclaimed_ticket_is_claimed() -> None:
    assert claim_ticket({7: None}, 7, "bo") == ({7: "bo"}, True)
""",
    ),
    _spec(
        "d4r_state.pin_version",
        _STATE,
        "version_pinning",
        "Pinning a dependency to a version.",
        "pin_version() accepts a pin that moves the dependency backwards.",
        "pin_version(pins, name, version) refuses a version below the one already pinned.",
        "it writes the version without comparing it with the pin already in place",
        """def pin_version(pins, name, version):
    return dict(pins, **{name: version})""",
        """def pin_version(pins, name, version):
    if name in pins and version < pins[name]:
        raise ValueError("a pin does not move backwards")
    pinned = dict(pins)
    pinned[name] = version
    return pinned""",
        """
import pytest

from version_pinning import pin_version


def test_moving_a_pin_backwards_is_refused() -> None:
    with pytest.raises(ValueError):
        pin_version({"lib": 5}, "lib", 3)


def test_moving_a_pin_forwards() -> None:
    assert pin_version({"lib": 5}, "lib", 7) == {"lib": 7}
""",
    ),
    # ------------------------------------------------------------------------- numeric logic
    _spec(
        "d4r_numeric.spread_of",
        _NUMERIC,
        "reading_spread",
        "Reporting how far apart the readings lie.",
        "spread_of() brings the caller down on a sample with no readings in it.",
        "spread_of(values) returns the largest reading less the smallest, and 0 for none.",
        "max and min both refuse an empty sample",
        """def spread_of(values):
    return max(values) - min(values)""",
        """def spread_of(values):
    if not values:
        return 0
    return max(values) - min(values)""",
        """
def test_a_sample_with_no_readings() -> None:
    assert spread_of([]) == 0


def test_the_spread_of_three_readings() -> None:
    assert spread_of([3, 9, 5]) == 6
""",
    ),
    _spec(
        "d4r_numeric.truncate_to",
        _NUMERIC,
        "decimal_truncation",
        "Cutting a value down to a number of decimal places.",
        "truncate_to() rounds the value up where the contract only cuts it.",
        "truncate_to(value, places) drops the digits past `places` without rounding.",
        "round() carries where truncation does not",
        """def truncate_to(value, places):
    scale = 10**places
    return round(value * scale) / scale""",
        """def truncate_to(value, places):
    scale = 10**places
    return int(value * scale) / scale""",
        """
def test_the_digits_are_cut_not_rounded() -> None:
    assert truncate_to(1.789, 2) == 1.78


def test_a_value_that_needs_no_cutting() -> None:
    assert truncate_to(1.5, 2) == 1.5
""",
    ),
    _spec(
        "d4r_numeric.sign_of",
        _NUMERIC,
        "value_signs",
        "Reporting the sign of a reading.",
        "sign_of() calls zero positive.",
        "sign_of(value) returns -1, 0 or 1 as the value is below, at, or above zero.",
        "it asks only whether the value is below zero and calls everything else positive",
        """def sign_of(value):
    return -1 if value < 0 else 1""",
        """def sign_of(value):
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0""",
        """
def test_zero_has_no_sign() -> None:
    assert sign_of(0) == 0


def test_a_reading_below_zero() -> None:
    assert sign_of(-4) == -1
""",
    ),
    _spec(
        "d4r_numeric.count_multiples",
        _NUMERIC,
        "multiple_counting",
        "Counting the multiples of a step up to a limit.",
        "count_multiples() leaves out a limit that is itself a multiple.",
        "count_multiples(step, limit) counts the multiples from step to limit inclusive.",
        "the range stops one short of the limit it was given",
        """def count_multiples(step, limit):
    return len([value for value in range(step, limit, step)])""",
        """def count_multiples(step, limit):
    return limit // step""",
        """
def test_a_limit_that_is_itself_a_multiple() -> None:
    assert count_multiples(3, 9) == 3


def test_a_limit_between_two_multiples() -> None:
    assert count_multiples(3, 10) == 3
""",
    ),
    _spec(
        "d4r_numeric.mean_absolute_error",
        _NUMERIC,
        "absolute_error",
        "Measuring how far predictions sat from the outcomes.",
        "mean_absolute_error() lets errors either side of the mark cancel one another out.",
        "mean_absolute_error(predicted, actual) averages the distances, whichever way they fall.",
        "it averages the signed differences rather than their sizes",
        """def mean_absolute_error(predicted, actual):
    gaps = [one - other for one, other in zip(predicted, actual)]
    return sum(gaps) / len(gaps)""",
        """def mean_absolute_error(predicted, actual):
    gaps = [abs(one - other) for one, other in zip(predicted, actual)]
    return sum(gaps) / len(gaps)""",
        """
def test_errors_either_side_do_not_cancel() -> None:
    assert mean_absolute_error([10, 10], [8, 12]) == 2.0


def test_errors_all_one_way() -> None:
    assert mean_absolute_error([10, 10], [8, 8]) == 2.0
""",
    ),
    _spec(
        "d4r_numeric.apply_discount",
        _NUMERIC,
        "discounting",
        "Taking a percentage discount off a price.",
        "apply_discount() takes far more off than the percentage asks for.",
        "apply_discount(price, percent) returns the price less that percentage of it.",
        "the percentage is applied as a bare fraction, never divided by a hundred",
        """def apply_discount(price, percent):
    return price - price * percent""",
        """def apply_discount(price, percent):
    return price - price * percent / 100""",
        """
def test_a_tenth_off() -> None:
    assert apply_discount(200, 10) == 180.0


def test_nothing_off() -> None:
    assert apply_discount(200, 0) == 200.0
""",
    ),
    _spec(
        "d4r_numeric.within_tolerance",
        _NUMERIC,
        "tolerance_checks",
        "Deciding whether two readings agree closely enough.",
        "within_tolerance() rejects a pair sitting exactly at the tolerance.",
        "within_tolerance(one, other, tolerance) accepts a gap at the tolerance as well as below.",
        "the comparison is strict where the contract includes the boundary",
        """def within_tolerance(one, other, tolerance):
    return abs(one - other) < tolerance""",
        """def within_tolerance(one, other, tolerance):
    return abs(one - other) <= tolerance""",
        """
def test_a_gap_exactly_at_the_tolerance_is_close_enough() -> None:
    assert within_tolerance(10, 12, 2) is True


def test_a_gap_beyond_the_tolerance() -> None:
    assert within_tolerance(10, 13, 2) is False
""",
    ),
    _spec(
        "d4r_numeric.minutes_to_clock",
        _NUMERIC,
        "clock_rendering",
        "Writing a count of minutes as a time on the clock.",
        "minutes_to_clock() writes a single-digit minute without its leading zero.",
        "minutes_to_clock(minutes) returns hours and minutes with the minutes always two digits.",
        "the minutes are written as a plain number rather than padded",
        """def minutes_to_clock(minutes):
    return "{}:{}".format(minutes // 60, minutes % 60)""",
        """def minutes_to_clock(minutes):
    return "{}:{:02d}".format(minutes // 60, minutes % 60)""",
        """
def test_a_single_digit_minute_is_padded() -> None:
    assert minutes_to_clock(125) == "2:05"


def test_a_two_digit_minute() -> None:
    assert minutes_to_clock(150) == "2:30"
""",
    ),
    _spec(
        "d4r_numeric.cumulative_share",
        _NUMERIC,
        "cumulative_shares",
        "Reporting how much of a total each step has covered.",
        "cumulative_share() divides by the running total rather than the grand total.",
        "cumulative_share(values) returns the running total as a share of the whole, ending at 1.",
        "the divisor moves with the loop instead of being the sum of everything",
        """def cumulative_share(values):
    shares = []
    running = 0
    for value in values:
        running += value
        shares.append(value / running)
    return shares""",
        """def cumulative_share(values):
    whole = sum(values)
    shares = []
    running = 0
    for value in values:
        running += value
        shares.append(running / whole)
    return shares""",
        """
def test_the_shares_end_at_the_whole() -> None:
    assert cumulative_share([1, 1, 2]) == [0.25, 0.5, 1.0]


def test_a_single_value_covers_everything() -> None:
    assert cumulative_share([5]) == [1.0]
""",
    ),
    _spec(
        "d4r_numeric.next_multiple_at_least",
        _NUMERIC,
        "multiple_rounding",
        "Rounding a size up to a whole number of blocks.",
        "next_multiple_at_least() rounds a size that already fits up to the next block anyway.",
        "next_multiple_at_least(value, step) returns the smallest multiple of step at least value.",
        "it adds a whole step before dividing, which pushes an exact fit over the edge",
        """def next_multiple_at_least(value, step):
    return (value // step + 1) * step""",
        """def next_multiple_at_least(value, step):
    return -(-value // step) * step""",
        """
def test_a_size_that_already_fits_is_left_alone() -> None:
    assert next_multiple_at_least(10, 5) == 10


def test_a_size_between_two_blocks() -> None:
    assert next_multiple_at_least(11, 5) == 15
""",
    ),
    # ------------------------------------------------------------------------ error handling
    _spec(
        "d4r_errors.first_failure",
        _ERRORS,
        "first_failing",
        "Naming the first check a value fails.",
        "first_failure() names the last failing check instead of the first.",
        "first_failure(value, checks) returns the name of the earliest check the value fails.",
        "it keeps overwriting the answer instead of stopping at the first failure",
        """def first_failure(value, checks):
    failed = None
    for name, check in checks:
        if not check(value):
            failed = name
    return failed""",
        """def first_failure(value, checks):
    for name, check in checks:
        if not check(value):
            return name
    return None""",
        """
def test_the_earliest_failing_check_is_named() -> None:
    checks = (("positive", lambda n: n > 0), ("even", lambda n: n % 2 == 0))
    assert first_failure(-3, checks) == "positive"


def test_a_value_that_passes_everything() -> None:
    checks = (("positive", lambda n: n > 0),)
    assert first_failure(4, checks) is None
""",
    ),
    _spec(
        "d4r_errors.has_blocking_error",
        _ERRORS,
        "blocking_errors",
        "Deciding whether a report holds anything that must stop the run.",
        "has_blocking_error() treats a warning as reason enough to stop.",
        "has_blocking_error(report) is true only for a finding of blocking severity.",
        "it asks whether there are findings rather than what severity they carry",
        """def has_blocking_error(report):
    return len(report["findings"]) > 0""",
        """def has_blocking_error(report):
    return any(finding["severity"] == "blocking" for finding in report["findings"])""",
        """
def test_a_report_of_warnings_alone_does_not_block() -> None:
    assert has_blocking_error({"findings": [{"severity": "warning"}]}) is False


def test_a_blocking_finding_blocks() -> None:
    assert has_blocking_error({"findings": [{"severity": "blocking"}]}) is True
""",
    ),
    _spec(
        "d4r_errors.safe_get",
        _ERRORS,
        "nested_lookup",
        "Reading a value out of a nested record.",
        "safe_get() brings the caller down when a section along the way is missing.",
        "safe_get(record, path, default) returns the default whenever the path runs out.",
        "each step assumes the one before it found a mapping",
        """def safe_get(record, path, default):
    found = record
    for name in path:
        found = found[name]
    return found""",
        """def safe_get(record, path, default):
    found = record
    for name in path:
        if not isinstance(found, dict) or name not in found:
            return default
        found = found[name]
    return found""",
        """
def test_a_missing_section_gives_the_default() -> None:
    assert safe_get({"a": {}}, ("a", "b", "c"), "none") == "none"


def test_a_path_that_reaches_a_value() -> None:
    assert safe_get({"a": {"b": 1}}, ("a", "b"), "none") == 1
""",
    ),
    _spec(
        "d4r_errors.reraise_as",
        _ERRORS,
        "error_retyping",
        "Raising a failure again under the kind the caller expects.",
        "reraise_as() throws the original message away.",
        "reraise_as(action, kind) raises `kind` carrying the original failure's message.",
        "the new error is raised bare rather than with what the first one said",
        """def reraise_as(action, kind):
    try:
        return action()
    except Exception:
        raise kind() from None""",
        """def reraise_as(action, kind):
    try:
        return action()
    except Exception as original:
        raise kind(str(original)) from original""",
        """
def test_the_original_message_survives() -> None:
    def failing():
        raise KeyError("no such row")

    try:
        reraise_as(failing, RuntimeError)
    except RuntimeError as raised:
        assert "no such row" in str(raised)
    else:
        raise AssertionError("nothing was raised")


def test_a_call_that_succeeds_is_passed_through() -> None:
    assert reraise_as(lambda: 7, RuntimeError) == 7
""",
    ),
    _spec(
        "d4r_errors.warn_once",
        _ERRORS,
        "single_warning",
        "Warning about a problem the first time it is seen.",
        "warn_once() records the same warning again every time it is met.",
        "warn_once(seen, key, message) records the message only the first time for that key.",
        "it appends without asking whether the key has been warned about",
        """def warn_once(seen, key, message):
    return {**seen, key: [*seen.get(key, []), message]}""",
        """def warn_once(seen, key, message):
    if key in seen:
        return dict(seen)
    return {**seen, key: [message]}""",
        """
def test_the_second_warning_for_a_key_is_not_recorded() -> None:
    once = warn_once({}, "disk", "nearly full")
    assert warn_once(once, "disk", "nearly full") == {"disk": ["nearly full"]}


def test_a_new_key_is_warned_about() -> None:
    assert warn_once({}, "disk", "nearly full") == {"disk": ["nearly full"]}
""",
    ),
    _spec(
        "d4r_errors.time_left",
        _ERRORS,
        "deadline_budget",
        "Reporting how long is left before a deadline.",
        "time_left() reports a negative budget once the deadline has gone by.",
        "time_left(deadline, now) returns whole seconds and never reports below zero.",
        "the subtraction is handed back without a floor under it",
        """def time_left(deadline, now):
    return int(deadline - now)""",
        """def time_left(deadline, now):
    return max(0, int(deadline - now))""",
        """
def test_a_deadline_already_gone_by_leaves_nothing() -> None:
    assert time_left(10, 25) == 0


def test_a_deadline_still_ahead() -> None:
    assert time_left(30, 10) == 20
""",
    ),
    _spec(
        "d4r_errors.describe_exception",
        _ERRORS,
        "error_description",
        "Writing a failure down for a log line.",
        "describe_exception() names the kind and drops the message that says what happened.",
        "describe_exception(error) writes the kind and the message, kind first.",
        "the message never reaches the line",
        """def describe_exception(error):
    return type(error).__name__""",
        """def describe_exception(error):
    return "{}: {}".format(type(error).__name__, error)""",
        """
def test_the_kind_is_named() -> None:
    assert describe_exception(ValueError("bad input")) == "ValueError: bad input"


def test_a_failure_with_no_message_still_names_its_kind() -> None:
    assert describe_exception(KeyError()) == "KeyError: "
""",
    ),
    _spec(
        "d4r_errors.is_retryable_status",
        _ERRORS,
        "status_retries",
        "Deciding whether a status code is worth another go.",
        "is_retryable_status() retries a request the server has told us is wrong.",
        "is_retryable_status(code) accepts 429 and the 500s and refuses the other 400s.",
        "it treats every code at or above 400 as a passing trouble",
        """def is_retryable_status(code):
    return code >= 400""",
        """def is_retryable_status(code):
    return code == 429 or 500 <= code < 600""",
        """
def test_a_request_the_server_calls_wrong_is_not_retried() -> None:
    assert is_retryable_status(400) is False


def test_being_asked_to_slow_down_is_retried() -> None:
    assert is_retryable_status(429) is True
    assert is_retryable_status(503) is True
""",
    ),
    _spec(
        "d4r_errors.drop_noise",
        _ERRORS,
        "noise_filtering",
        "Clearing the known noise out of a log.",
        "drop_noise() keeps the noisy lines and drops everything else.",
        "drop_noise(lines, noise) returns the lines holding none of the noise patterns.",
        "the condition is the wrong way round",
        """def drop_noise(lines, noise):
    return [line for line in lines if any(pattern in line for pattern in noise)]""",
        """def drop_noise(lines, noise):
    return [line for line in lines if not any(pattern in line for pattern in noise)]""",
        """
def test_the_noisy_line_goes_and_the_rest_stays() -> None:
    assert drop_noise(["disk failed", "heartbeat ok"], ("heartbeat",)) == ["disk failed"]


def test_nothing_known_to_be_noise_keeps_everything() -> None:
    assert drop_noise(["a", "b"], ()) == ["a", "b"]
""",
    ),
    _spec(
        "d4r_errors.exit_code_for_report",
        _ERRORS,
        "report_exit_codes",
        "Choosing the exit code a report deserves.",
        "exit_code_for_report() gives a misuse of the tool the same code as a genuine failure.",
        "exit_code_for_report(report) returns 0 for a clean run, 2 for misuse and 1 otherwise.",
        "it looks only at whether anything went wrong, not at what kind of wrong",
        """def exit_code_for_report(report):
    return 1 if report["errors"] else 0""",
        """def exit_code_for_report(report):
    if not report["errors"]:
        return 0
    if any(error["kind"] == "usage" for error in report["errors"]):
        return 2
    return 1""",
        """
def test_a_misuse_of_the_tool_has_its_own_code() -> None:
    assert exit_code_for_report({"errors": [{"kind": "usage"}]}) == 2


def test_a_clean_run() -> None:
    assert exit_code_for_report({"errors": []}) == 0
""",
    ),
    # ------------------------------------------------------------------- data transformation
    _spec(
        "d4r_transform.pluck_nested",
        _TRANSFORM,
        "nested_plucking",
        "Reading one nested field out of every record.",
        "pluck_nested() reads only the top level and never follows the path down.",
        "pluck_nested(records, path) returns the value at the dotted path from each record.",
        "it looks the whole path up as a single field name",
        """def pluck_nested(records, path):
    return [record.get(path) for record in records]""",
        """def pluck_nested(records, path):
    plucked = []
    for record in records:
        found = record
        for name in path.split("."):
            found = found.get(name) if isinstance(found, dict) else None
        plucked.append(found)
    return plucked""",
        """
def test_the_path_is_followed_down() -> None:
    records = [{"user": {"name": "ada"}}, {"user": {"name": "bo"}}]
    assert pluck_nested(records, "user.name") == ["ada", "bo"]


def test_a_record_missing_the_path() -> None:
    assert pluck_nested([{"user": {}}], "user.name") == [None]
""",
    ),
    _spec(
        "d4r_transform.max_by",
        _TRANSFORM,
        "largest_record",
        "Picking the record with the largest reading.",
        "max_by() returns the last of several records tied at the top rather than the first.",
        "max_by(records, field) returns the earliest record holding the largest value.",
        "it takes a reading equal to the best so far as a better one",
        """def max_by(records, field):
    best = records[0]
    for record in records:
        if record[field] >= best[field]:
            best = record
    return best""",
        """def max_by(records, field):
    best = records[0]
    for record in records:
        if record[field] > best[field]:
            best = record
    return best""",
        """
def test_the_first_of_a_tie_wins() -> None:
    records = [{"id": "a", "n": 9}, {"id": "b", "n": 9}]
    assert max_by(records, "n")["id"] == "a"


def test_the_largest_reading_wins() -> None:
    records = [{"id": "a", "n": 1}, {"id": "b", "n": 9}]
    assert max_by(records, "n")["id"] == "b"
""",
    ),
    _spec(
        "d4r_transform.partition_by",
        _TRANSFORM,
        "record_partition",
        "Sorting records into the ones that match and the rest.",
        "partition_by() hands back the matches and loses everything else.",
        "partition_by(records, check) returns (matching, rest) with every record in exactly one.",
        "the second list is never built",
        """def partition_by(records, check):
    return [record for record in records if check(record)], []""",
        """def partition_by(records, check):
    matching = []
    rest = []
    for record in records:
        (matching if check(record) else rest).append(record)
    return matching, rest""",
        """
def test_the_rest_are_kept_too() -> None:
    assert partition_by([1, 2, 3], lambda n: n % 2) == ([1, 3], [2])


def test_records_that_all_match() -> None:
    assert partition_by([1, 3], lambda n: n % 2) == ([1, 3], [])
""",
    ),
    _spec(
        "d4r_transform.stringify_keys",
        _TRANSFORM,
        "key_stringifying",
        "Writing every key of a record as text.",
        "stringify_keys() converts the top level and leaves the nested sections alone.",
        "stringify_keys(record) writes every key as text, all the way down.",
        "it never looks inside a value that is itself a record",
        """def stringify_keys(record):
    converted = {}
    for name, value in record.items():
        converted[str(name)] = value
    return converted""",
        """def stringify_keys(record):
    return {
        str(name): (stringify_keys(value) if isinstance(value, dict) else value)
        for name, value in record.items()
    }""",
        """
def test_a_nested_section_is_converted_too() -> None:
    assert stringify_keys({1: {2: "x"}}) == {"1": {"2": "x"}}


def test_a_flat_record() -> None:
    assert stringify_keys({1: "x"}) == {"1": "x"}
""",
    ),
    _spec(
        "d4r_transform.drop_columns",
        _TRANSFORM,
        "column_dropping",
        "Dropping named columns from a record.",
        "drop_columns() brings the caller down on a column the record does not carry.",
        "drop_columns(record, names) drops the named columns and ignores one that is not there.",
        "del refuses a name the record does not carry",
        """def drop_columns(record, names):
    kept = dict(record)
    for name in names:
        del kept[name]
    return kept""",
        """def drop_columns(record, names):
    return {name: value for name, value in record.items() if name not in names}""",
        """
def test_a_column_that_is_not_there_is_ignored() -> None:
    assert drop_columns({"a": 1}, ("a", "b")) == {}


def test_the_named_column_goes() -> None:
    assert drop_columns({"a": 1, "b": 2}, ("a",)) == {"b": 2}
""",
    ),
    _spec(
        "d4r_transform.reverse_index",
        _TRANSFORM,
        "reverse_indexing",
        "Turning a mapping round to find the keys under each value.",
        "reverse_index() keeps only the first key that carried each value.",
        "reverse_index(mapping) maps each value to every key that carried it, in order.",
        "setdefault writes the first key and never comes back for the others",
        """def reverse_index(mapping):
    found = {}
    for key, value in mapping.items():
        found.setdefault(value, [key])
    return found""",
        """def reverse_index(mapping):
    reversed_pairs = {}
    for key, value in mapping.items():
        reversed_pairs.setdefault(value, []).append(key)
    return reversed_pairs""",
        """
def test_every_key_under_a_shared_value_is_kept() -> None:
    assert reverse_index({"a": 1, "b": 1}) == {1: ["a", "b"]}


def test_a_value_carried_by_one_key() -> None:
    assert reverse_index({"a": 1}) == {1: ["a"]}
""",
    ),
    _spec(
        "d4r_transform.apply_to_values",
        _TRANSFORM,
        "value_mapping",
        "Putting every value of a record through a function.",
        "apply_to_values() puts the keys through it as well.",
        "apply_to_values(record, change) changes the values and leaves the keys as they were.",
        "the comprehension calls the function on both halves of the pair",
        """def apply_to_values(record, change):
    return {change(name): change(value) for name, value in record.items()}""",
        """def apply_to_values(record, change):
    return {name: change(value) for name, value in record.items()}""",
        """
def test_the_keys_are_left_as_they_were() -> None:
    assert apply_to_values({"a": "x"}, str.upper) == {"a": "X"}


def test_two_values_are_both_changed() -> None:
    assert apply_to_values({"a": "x", "b": "y"}, str.upper) == {"a": "X", "b": "Y"}
""",
    ),
    _spec(
        "d4r_transform.sort_records_by",
        _TRANSFORM,
        "record_sorting",
        "Ordering records by one of their fields.",
        "sort_records_by() brings the caller down on a record that does not carry the field.",
        "sort_records_by(records, field) orders by the field and puts records without it last.",
        "the sort key reaches for a field that need not be there",
        """def sort_records_by(records, field):
    return sorted(records, key=lambda record: record[field])""",
        """def sort_records_by(records, field):
    return sorted(
        records, key=lambda record: (0, record[field]) if field in record else (1,)
    )""",
        """
def test_a_record_without_the_field_goes_last() -> None:
    records = [{"n": 2}, {}, {"n": 1}]
    assert sort_records_by(records, "n") == [{"n": 1}, {"n": 2}, {}]


def test_records_that_all_carry_the_field() -> None:
    assert sort_records_by([{"n": 2}, {"n": 1}], "n") == [{"n": 1}, {"n": 2}]
""",
    ),
    _spec(
        "d4r_transform.split_field",
        _TRANSFORM,
        "field_splitting",
        "Splitting one written field into a list.",
        "split_field() leaves the spaces around each part where they were.",
        "split_field(record, name, separator) splits the field and trims each part.",
        "split alone keeps whatever sat next to the separator",
        """def split_field(record, name, separator):
    return {**record, name: record[name].split(separator)}""",
        """def split_field(record, name, separator):
    parts = [part.strip() for part in record[name].split(separator)]
    return {**record, name: [part for part in parts if part]}""",
        """
def test_the_parts_are_trimmed() -> None:
    assert split_field({"tags": "a, b"}, "tags", ",")["tags"] == ["a", "b"]


def test_a_single_part() -> None:
    assert split_field({"tags": "a"}, "tags", ",")["tags"] == ["a"]
""",
    ),
    _spec(
        "d4r_transform.normalise_booleans",
        _TRANSFORM,
        "boolean_normalising",
        "Reading the yes and no answers in a record as booleans.",
        "normalise_booleans() misses an answer written with a capital letter.",
        "normalise_booleans(record) converts only the known words and leaves the rest alone.",
        "it matches the words exactly as written and knows only two of them",
        """def normalise_booleans(record):
    words = {"yes": True, "no": False}
    return {name: words.get(value, value) for name, value in record.items()}""",
        """def normalise_booleans(record):
    words = {"yes": True, "true": True, "no": False, "false": False}
    return {
        name: words.get(value.lower(), value) if isinstance(value, str) else value
        for name, value in record.items()
    }""",
        """
def test_a_word_that_is_not_an_answer_is_left_alone() -> None:
    assert normalise_booleans({"name": "ada"}) == {"name": "ada"}


def test_the_known_words_become_booleans() -> None:
    assert normalise_booleans({"a": "yes", "b": "No"}) == {"a": True, "b": False}
""",
    ),
)
