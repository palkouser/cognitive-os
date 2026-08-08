"""The Sprint 21D5 retrieval source pool, §S21D5-021.

D5 needs its own unseen-task queries for the reason D4 needed its own: a pool authored before
the arms are frozen puts the retrieval evidence inside the window the D5 contracts seal. Sixty
fresh groups are authored here, disjoint from every released corpus and from D5's own
calibration corpus, and S21D5-043 keeps whichever survive integrity filtering.

The spec shape is `D3RetrievalSpec`, unchanged, for the reason that kept the calibration corpus
on `D2TaskSpec`: the projection, the holdout and the query builder already agree about it.

A retrieval group is one defect and its repair, not four candidates around two independent edge
cases. Retrieval is evaluated on projected graphs and edit paths, and `project_correction` needs
one thing from a trajectory: a step the verifier rejected, then one it accepted.

Three things are executed rather than declared, and `scripts/retrieval_d5.py` is what decides
each of them:

1. **The pair is causal.** The failed body fails the hidden suite and the repair passes it.
2. **Both sides carry a searchable surface.** This is the S21D4 residual and the reason the D4
   pool reached 41 of 60: ten repairs were pure arithmetic over their own parameters, the
   normaliser left nothing of them, and an empty document cannot be found by any arm. Every
   side here is projected under `structure_fallback` and its terms counted.
3. **The two sides carry *different* surfaces.** A pair whose failed and repaired documents are
   identical is retrievable and uninformative: it drags MRR down while looking healthy. Nothing
   in D4 measured this per pair, and it is the constraint that shaped these bodies -- each
   repair either introduces or drops a name the normaliser preserves (a builtin, a method, a
   module, an exception) or changes the control flow enough that the fallback bags differ.

The families are the retrieval relevance judgement, so each carries ten groups and each group's
vocabulary is drawn from what that family's work actually calls: `split`/`strip`/`partition`
for parsing, `append`/`range`/`sorted` for collections, `divmod`/`abs`/`round` for numeric,
`items`/`setdefault`/`get` for transformation and state, `ValueError`/`RuntimeError` for error
handling. That is the signal an arm has to find, and it is put there deliberately rather than
hoped for.
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
    *,
    imports: str = "",
) -> D3RetrievalSpec:
    """One row of the table, under a `d5r-` repository prefix.

    A local builder rather than D3's or D4's: the three differ in the prefix alone, and
    importing a private helper to pass it a flag would be a wider change than repeating it.
    """
    return D3RetrievalSpec(
        template_id=name,
        family=family,
        repository_group=f"d5r-{name.split('.', 1)[1].replace('_', '-')}",
        module=module,
        module_doc=doc,
        issue=issue,
        expected=expected,
        failure_reason=reason,
        failed=failed,
        repaired=repaired,
        hidden_test=_hidden(module, test_body, imports=imports or f"from {module} import *\n"),
    )


D5_RETRIEVAL_SPECS: tuple[D3RetrievalSpec, ...] = (
    # ------------------------------------------------------------ boundary and collections
    _spec(
        "d5r_boundary.adjacent_pairs",
        _BOUNDARY,
        "adjacent_pairs",
        "Reading a series as the pairs of neighbours it contains.",
        "adjacent_pairs() drops the last pair of a series.",
        "adjacent_pairs(items) returns each neighbouring pair in order.",
        "it stops one short because the loop bound counts pairs as though they were items",
        """def adjacent_pairs(items):
    out = []
    for place in range(len(items) - 2):
        out.append((items[place], items[place + 1]))
    return out""",
        """def adjacent_pairs(items):
    return list(zip(items, items[1:]))""",
        """
def test_every_neighbouring_pair_is_returned() -> None:
    assert adjacent_pairs([1, 2, 3]) == [(1, 2), (2, 3)]


def test_a_single_item_has_no_neighbours() -> None:
    assert adjacent_pairs([1]) == []
""",
    ),
    _spec(
        "d5r_boundary.pad_to_length",
        _BOUNDARY,
        "pad_to_length",
        "Bringing a short row up to the width the table expects.",
        "pad_to_length() cuts a row down instead of leaving a long one alone.",
        "pad_to_length(row, width, filler) appends filler until the row reaches width.",
        "it slices the row to the width, which shortens a row that was already long enough",
        """def pad_to_length(row, width, filler):
    return (list(row) + [filler] * width)[:width]""",
        """def pad_to_length(row, width, filler):
    out = list(row)
    while len(out) < width:
        out.append(filler)
    return out""",
        """
def test_a_short_row_is_brought_up_to_width() -> None:
    assert pad_to_length([1], 3, 0) == [1, 0, 0]


def test_a_long_row_is_left_alone() -> None:
    assert pad_to_length([1, 2, 3, 4], 3, 0) == [1, 2, 3, 4]
""",
    ),
    _spec(
        "d5r_boundary.position_of",
        _BOUNDARY,
        "position_of",
        "Saying where in a list an entry sits.",
        "position_of() answers zero for an entry that is not in the list at all.",
        "position_of(items, wanted) returns the index of the entry, or minus one when absent.",
        "the position starts at zero and is returned whether or not the loop ever matched",
        """def position_of(items, wanted):
    found = 0
    for place in range(len(items)):
        if items[place] == wanted:
            found = place
    return found""",
        """def position_of(items, wanted):
    for place, item in enumerate(items):
        if item == wanted:
            return place
    return -1""",
        """
def test_an_entry_reports_its_index() -> None:
    assert position_of(["a", "b"], "b") == 1


def test_an_entry_that_is_absent_reports_minus_one() -> None:
    assert position_of(["a", "b"], "z") == -1
""",
    ),
    _spec(
        "d5r_boundary.drop_both_ends",
        _BOUNDARY,
        "drop_both_ends",
        "Dropping the header and the footer off a block of lines.",
        "drop_both_ends() leaves the header behind.",
        "drop_both_ends(lines) returns the lines with the first and the last removed.",
        "it stops before the end without also starting after the beginning",
        """def drop_both_ends(lines):
    return lines[:-1]""",
        """def drop_both_ends(lines):
    if len(lines) <= 2:
        return []
    return lines[1:-1]""",
        """
def test_the_header_and_the_footer_both_go() -> None:
    assert drop_both_ends(["h", "a", "b", "f"]) == ["a", "b"]


def test_a_block_of_two_leaves_nothing() -> None:
    assert drop_both_ends(["h", "f"]) == []
""",
    ),
    _spec(
        "d5r_boundary.largest_three",
        _BOUNDARY,
        "largest_three",
        "Picking the three biggest readings off a run.",
        "largest_three() hands the three back smallest first.",
        "largest_three(values) returns the three biggest readings, biggest first.",
        "it sorts ascending and takes the tail, which leaves the order back to front",
        """def largest_three(values):
    return sorted(values)[-3:]""",
        """def largest_three(values):
    return sorted(values, reverse=True)[:3]""",
        """
def test_the_biggest_three_come_back_biggest_first() -> None:
    assert largest_three([5, 1, 9, 3]) == [9, 5, 3]


def test_fewer_than_three_readings_all_come_back() -> None:
    assert largest_three([2, 7]) == [7, 2]
""",
    ),
    _spec(
        "d5r_boundary.split_in_half",
        _BOUNDARY,
        "split_in_half",
        "Cutting a list into two halves for two workers.",
        "split_in_half() loses the middle entry of an odd-length list.",
        "split_in_half(items) returns (front, back) covering every entry once.",
        "it rounds the cut down for the front and up for the back, skipping the middle entry",
        """def split_in_half(items):
    middle = len(items) // 2
    return items[:middle], items[middle + 1:]""",
        """def split_in_half(items):
    middle, _ = divmod(len(items), 2)
    return items[:middle], items[middle:]""",
        """
def test_an_even_list_splits_evenly() -> None:
    assert split_in_half([1, 2, 3, 4]) == ([1, 2], [3, 4])


def test_an_odd_list_keeps_its_middle_entry() -> None:
    assert split_in_half([1, 2, 3]) == ([1], [2, 3])
""",
    ),
    _spec(
        "d5r_boundary.count_within",
        _BOUNDARY,
        "count_within",
        "Counting the readings that fall inside a band.",
        "count_within() leaves out a reading sitting exactly on the upper edge.",
        "count_within(values, low, high) counts the readings from low to high inclusive.",
        "the upper comparison is strict, so a reading on the edge is counted as outside",
        """def count_within(values, low, high):
    total = 0
    for value in values:
        if low <= value < high:
            total += 1
    return total""",
        """def count_within(values, low, high):
    return sum(1 for value in values if low <= value <= high)""",
        """
def test_a_reading_on_the_upper_edge_counts() -> None:
    assert count_within([1, 5, 9], 1, 5) == 2


def test_a_reading_outside_the_band_does_not_count() -> None:
    assert count_within([1, 5, 9], 2, 6) == 1
""",
    ),
    _spec(
        "d5r_boundary.every_other",
        _BOUNDARY,
        "every_other",
        "Thinning a series by keeping every second reading.",
        "every_other() keeps the readings it was meant to drop.",
        "every_other(values) returns the readings at the even positions, starting at the first.",
        "the slice starts at one rather than at nothing, so it keeps the odd positions",
        """def every_other(values):
    return values[1::2]""",
        """def every_other(values):
    return [value for place, value in enumerate(values) if place % 2 == 0]""",
        """
def test_the_first_reading_is_kept() -> None:
    assert every_other([1, 2, 3, 4, 5]) == [1, 3, 5]


def test_a_single_reading_is_kept() -> None:
    assert every_other([7]) == [7]
""",
    ),
    _spec(
        "d5r_boundary.insert_in_order",
        _BOUNDARY,
        "insert_in_order",
        "Putting one more reading into a list that is already sorted.",
        "insert_in_order() puts the reading on the end whatever its value.",
        "insert_in_order(values, value) returns the list with value in its sorted place.",
        "it appends rather than looking for the place the reading belongs in",
        """def insert_in_order(values, value):
    return [*values, value]""",
        """def insert_in_order(values, value):
    out = list(values)
    place = len(out)
    for index, held in enumerate(out):
        if held > value:
            place = index
            break
    out.insert(place, value)
    return out""",
        """
def test_a_reading_lands_in_its_sorted_place() -> None:
    assert insert_in_order([1, 3, 5], 4) == [1, 3, 4, 5]


def test_a_reading_below_everything_lands_first() -> None:
    assert insert_in_order([1, 3, 5], 0) == [0, 1, 3, 5]
""",
    ),
    _spec(
        "d5r_boundary.shortest_row",
        _BOUNDARY,
        "shortest_row",
        "Finding the narrowest row of a table.",
        "shortest_row() answers with the length rather than with the row.",
        "shortest_row(rows) returns the row holding the fewest entries.",
        "it returns the measurement it minimised over instead of the row it belongs to",
        """def shortest_row(rows):
    return min(len(row) for row in rows)""",
        """def shortest_row(rows):
    return min(rows, key=len)""",
        """
def test_the_narrowest_row_comes_back() -> None:
    assert shortest_row([[1, 2, 3], [4], [5, 6]]) == [4]


def test_a_single_row_is_its_own_narrowest() -> None:
    assert shortest_row([[1, 2]]) == [1, 2]
""",
    ),
    # ------------------------------------------------------------- parsing and validation
    _spec(
        "d5r_parsing.trim_comment",
        _PARSING,
        "trim_comment",
        "Taking the trailing comment off a configuration line.",
        "trim_comment() leaves the whitespace the comment was sitting behind.",
        "trim_comment(line) returns the line up to the hash, with trailing spaces removed.",
        "it cuts at the hash and hands back what is left exactly as written",
        """def trim_comment(line):
    return line.split("#")[0]""",
        """def trim_comment(line):
    head, _, _ = line.partition("#")
    return head.rstrip()""",
        """
def test_the_comment_and_the_space_before_it_both_go() -> None:
    assert trim_comment("value = 1   # why") == "value = 1"


def test_a_line_with_no_comment_is_left_alone() -> None:
    assert trim_comment("value = 1") == "value = 1"
""",
    ),
    _spec(
        "d5r_parsing.read_flag",
        _PARSING,
        "read_flag",
        "Reading a written yes or no out of a settings file.",
        "read_flag() refuses a value that is merely spelled in capitals.",
        "read_flag(text) reads yes, true and on as true whatever their case.",
        "it compares the written value against lowercase words without lowering it first",
        """def read_flag(text):
    return text.strip() in ("yes", "true", "on")""",
        """def read_flag(text):
    return text.strip().lower() in ("yes", "true", "on")""",
        """
def test_a_written_yes_reads_as_true() -> None:
    assert read_flag(" yes ") is True


def test_capitals_read_the_same_as_lowercase() -> None:
    assert read_flag("TRUE") is True
""",
    ),
    _spec(
        "d5r_parsing.leading_number",
        _PARSING,
        "leading_number",
        "Reading the number off the front of a measurement.",
        "leading_number() reads the unit along with the number and fails.",
        "leading_number(text) returns the digits at the front of the text as a whole number.",
        "it converts the whole string rather than the digits at the front of it",
        """def leading_number(text):
    return int(text.strip())""",
        """def leading_number(text):
    digits = ""
    for letter in text.strip():
        if not letter.isdigit():
            break
        digits += letter
    return int(digits)""",
        """
def test_the_number_in_front_of_a_unit_is_read() -> None:
    assert leading_number("42kg") == 42


def test_a_bare_number_reads_as_itself() -> None:
    assert leading_number(" 7 ") == 7
""",
    ),
    _spec(
        "d5r_parsing.strip_scheme",
        _PARSING,
        "strip_scheme",
        "Taking the scheme off the front of an address.",
        "strip_scheme() removes a fixed number of characters whatever the scheme was.",
        "strip_scheme(url) returns the address with any scheme and its separator removed.",
        "it cuts a fixed seven characters, which is right for one scheme and wrong for others",
        """def strip_scheme(url):
    return url[7:]""",
        """def strip_scheme(url):
    _, found, rest = url.partition("://")
    if not found:
        return url
    return rest""",
        """
def test_a_secure_address_loses_its_scheme() -> None:
    assert strip_scheme("https://example.com/a") == "example.com/a"


def test_an_address_with_no_scheme_is_left_alone() -> None:
    assert strip_scheme("example.com/a") == "example.com/a"
""",
    ),
    _spec(
        "d5r_parsing.two_letter_code",
        _PARSING,
        "two_letter_code",
        "Checking a country code before it reaches the address file.",
        "two_letter_code() accepts a code carrying digits.",
        "two_letter_code(text) accepts exactly two letters and nothing else.",
        "it checks the length without checking that both characters are letters",
        """def two_letter_code(text):
    return len(text) == 2""",
        """def two_letter_code(text):
    return len(text) == 2 and text.isalpha()""",
        """
def test_two_letters_are_accepted() -> None:
    assert two_letter_code("gb") is True


def test_two_characters_with_a_digit_are_refused() -> None:
    assert two_letter_code("g1") is False
""",
    ),
    _spec(
        "d5r_parsing.split_name_pair",
        _PARSING,
        "split_name_pair",
        "Reading a surname and a forename out of one written field.",
        "split_name_pair() falls over on a surname carrying a comma of its own.",
        "split_name_pair(text) splits at the first comma only and trims both halves.",
        "it splits at every comma and unpacks the result into exactly two names",
        """def split_name_pair(text):
    surname, forename = text.split(",")
    return surname.strip(), forename.strip()""",
        """def split_name_pair(text):
    surname, _, forename = text.partition(",")
    return surname.strip(), forename.strip()""",
        """
def test_an_ordinary_pair_splits_and_trims() -> None:
    assert split_name_pair("Lovelace, Ada") == ("Lovelace", "Ada")


def test_a_forename_carrying_a_comma_survives() -> None:
    assert split_name_pair("Windsor, Anne, HRH") == ("Windsor", "Anne, HRH")
""",
    ),
    _spec(
        "d5r_parsing.decimal_places",
        _PARSING,
        "decimal_places",
        "Counting how many decimal places a written figure carries.",
        "decimal_places() counts one place for a figure that carries none.",
        "decimal_places(text) returns how many digits follow the decimal point, or nothing.",
        "it counts the pieces the split produced rather than the digits after the point",
        """def decimal_places(text):
    return len(text.split(".")) - 1""",
        """def decimal_places(text):
    _, found, rest = text.partition(".")
    if not found:
        return 0
    return len(rest)""",
        """
def test_a_figure_with_two_places() -> None:
    assert decimal_places("1.25") == 2


def test_a_whole_figure_carries_no_places() -> None:
    assert decimal_places("12") == 0
""",
    ),
    _spec(
        "d5r_parsing.quoted_inner",
        _PARSING,
        "quoted_inner",
        "Reading what sits inside a quoted field.",
        "quoted_inner() strips quotes from anywhere rather than only from the two ends.",
        "quoted_inner(text) returns what sits between the opening and closing quotes.",
        "stripping by character removes every quote at either end, however many there are",
        """def quoted_inner(text):
    return text.strip(chr(34))""",
        """def quoted_inner(text):
    quote = chr(34)
    if len(text) >= 2 and text.startswith(quote) and text.endswith(quote):
        return text[1:-1]
    return text""",
        """
def test_the_two_outer_quotes_are_removed() -> None:
    assert quoted_inner(chr(34) + "a b" + chr(34)) == "a b"


def test_an_inner_quote_at_the_edge_survives() -> None:
    assert quoted_inner(chr(34) + chr(34) + "a" + chr(34) + chr(34)) == chr(34) + "a" + chr(34)
""",
    ),
    _spec(
        "d5r_parsing.header_continuation",
        _PARSING,
        "header_continuation",
        "Recognising the folded continuation of a header line.",
        "header_continuation() calls an empty line a continuation.",
        "header_continuation(line) is true only for a non-empty line beginning with whitespace.",
        "an empty line begins with nothing, and nothing is not whitespace, but the check "
        "compares the stripped line rather than asking what the first character is",
        """def header_continuation(line):
    return line != line.lstrip()""",
        """def header_continuation(line):
    return bool(line.strip()) and line[:1].isspace()""",
        """
def test_an_indented_line_continues_the_header() -> None:
    assert header_continuation("    more") is True


def test_a_line_of_only_whitespace_does_not() -> None:
    assert header_continuation("    ") is False
""",
    ),
    _spec(
        "d5r_parsing.protocol_port",
        _PARSING,
        "protocol_port",
        "Reading the port off the end of a host and port pair.",
        "protocol_port() reads the wrong number out of an address carrying several colons.",
        "protocol_port(text) returns the number after the last colon.",
        "it splits at the first colon, which is the wrong one when the host holds colons",
        """def protocol_port(text):
    return int(text.split(":")[1])""",
        """def protocol_port(text):
    _, _, tail = text.rpartition(":")
    return int(tail)""",
        """
def test_an_ordinary_host_and_port() -> None:
    assert protocol_port("example.com:8080") == 8080


def test_a_host_carrying_colons_reads_the_last_one() -> None:
    assert protocol_port("fe80::1:9000") == 9000
""",
    ),
    # ---------------------------------------------------------------------- numeric logic
    _spec(
        "d5r_numeric.round_to_step",
        _NUMERIC,
        "round_to_step",
        "Snapping a reading onto the nearest step of a scale.",
        "round_to_step() always rounds down instead of to the nearest step.",
        "round_to_step(value, step) returns the nearest multiple of step.",
        "integer division floors, so a reading past the halfway point still snaps downwards",
        """def round_to_step(value, step):
    return (value // step) * step""",
        """def round_to_step(value, step):
    return round(value / step) * step""",
        """
def test_a_reading_past_halfway_snaps_upwards() -> None:
    assert round_to_step(7, 5) == 5
    assert round_to_step(8, 5) == 10


def test_a_reading_already_on_a_step_stays() -> None:
    assert round_to_step(10, 5) == 10
""",
    ),
    _spec(
        "d5r_numeric.percentage_of",
        _NUMERIC,
        "percentage_of",
        "Working out what share of a whole a part represents.",
        "percentage_of() falls over when the whole is nothing.",
        "percentage_of(part, whole) returns the share as a percentage, or nothing for no whole.",
        "it divides by the whole without asking whether there is one",
        """def percentage_of(part, whole):
    return part * 100 / whole""",
        """def percentage_of(part, whole):
    if not whole:
        return 0.0
    return part * 100 / whole""",
        """
def test_a_quarter_reads_as_twenty_five() -> None:
    assert percentage_of(1, 4) == 25.0


def test_a_whole_of_nothing_reads_as_nothing() -> None:
    assert percentage_of(1, 0) == 0.0
""",
    ),
    _spec(
        "d5r_numeric.distance_apart",
        _NUMERIC,
        "distance_apart",
        "Measuring how far apart two readings are.",
        "distance_apart() answers with a negative distance.",
        "distance_apart(left, right) returns how far apart the two are, never below zero.",
        "it subtracts in a fixed order rather than measuring the size of the difference",
        """def distance_apart(left, right):
    return right - left""",
        """def distance_apart(left, right):
    return abs(right - left)""",
        """
def test_the_larger_reading_first_still_measures_positively() -> None:
    assert distance_apart(9, 4) == 5


def test_two_equal_readings_are_no_distance_apart() -> None:
    assert distance_apart(3, 3) == 0
""",
    ),
    _spec(
        "d5r_numeric.split_pence",
        _NUMERIC,
        "split_pence",
        "Turning an amount in pence into pounds and the pence left over.",
        "split_pence() reports the whole amount as the pence left over.",
        "split_pence(pence) returns (pounds, pence) with the pence below a hundred.",
        "it divides for the pounds but hands back the original amount as the remainder",
        """def split_pence(pence):
    return pence // 100, pence""",
        """def split_pence(pence):
    return divmod(pence, 100)""",
        """
def test_an_amount_splits_into_pounds_and_pence() -> None:
    assert split_pence(345) == (3, 45)


def test_a_whole_number_of_pounds_leaves_no_pence() -> None:
    assert split_pence(200) == (2, 0)
""",
    ),
    _spec(
        "d5r_numeric.average_reading",
        _NUMERIC,
        "average_reading",
        "Averaging a run of readings.",
        "average_reading() truncates the average to a whole number.",
        "average_reading(values) returns the mean of the readings.",
        "the division floors, so an average between two whole numbers loses its fraction",
        """def average_reading(values):
    return sum(values) // len(values)""",
        """def average_reading(values):
    return float(sum(values)) / len(values)""",
        """
def test_an_average_between_two_whole_numbers_keeps_its_fraction() -> None:
    assert average_reading([1, 2]) == 1.5


def test_equal_readings_average_to_themselves() -> None:
    assert average_reading([4, 4]) == 4.0
""",
    ),
    _spec(
        "d5r_numeric.growth_factor",
        _NUMERIC,
        "growth_factor",
        "Compounding a growth rate over a number of periods.",
        "growth_factor() multiplies the rate by the periods instead of compounding it.",
        "growth_factor(rate, periods) returns the factor a rate compounds to.",
        "repeated growth is a power, not a product with the number of periods",
        """def growth_factor(rate, periods):
    return 1 + rate * periods""",
        """def growth_factor(rate, periods):
    return pow(1 + rate, periods)""",
        """
def test_two_periods_of_growth_compound() -> None:
    assert growth_factor(1.0, 2) == 4.0


def test_no_periods_leave_the_factor_at_one() -> None:
    assert growth_factor(1.0, 0) == 1.0
""",
    ),
    _spec(
        "d5r_numeric.is_multiple",
        _NUMERIC,
        "is_multiple",
        "Asking whether one number divides another exactly.",
        "is_multiple() falls over when asked about a divisor of nothing.",
        "is_multiple(value, divisor) says whether the divisor goes in exactly.",
        "the remainder is taken without asking whether there is anything to divide by",
        """def is_multiple(value, divisor):
    return value % divisor == 0""",
        """def is_multiple(value, divisor):
    if divisor == 0:
        return value == 0
    return value % divisor == 0""",
        """
def test_a_multiple_is_recognised() -> None:
    assert is_multiple(9, 3) is True


def test_a_divisor_of_nothing_only_divides_nothing() -> None:
    assert is_multiple(9, 0) is False
""",
    ),
    _spec(
        "d5r_numeric.clamp_reading",
        _NUMERIC,
        "clamp_reading",
        "Holding a reading inside the range the dial can show.",
        "clamp_reading() lets a reading below the floor through.",
        "clamp_reading(value, low, high) holds the reading between low and high.",
        "only the ceiling is applied, so the floor never takes effect",
        """def clamp_reading(value, low, high):
    if value > high:
        return high
    return value""",
        """def clamp_reading(value, low, high):
    return max(low, min(value, high))""",
        """
def test_a_reading_below_the_floor_is_raised_to_it() -> None:
    assert clamp_reading(-5, 0, 10) == 0


def test_a_reading_above_the_ceiling_is_lowered_to_it() -> None:
    assert clamp_reading(15, 0, 10) == 10
""",
    ),
    _spec(
        "d5r_numeric.digit_count",
        _NUMERIC,
        "digit_count",
        "Counting how many digits a whole number is written with.",
        "digit_count() counts the minus sign of a negative number as a digit.",
        "digit_count(number) returns how many digits the number is written with.",
        "the length of the written number includes the sign the number carries",
        """def digit_count(number):
    return len(str(number))""",
        """def digit_count(number):
    return len(str(abs(number)))""",
        """
def test_a_three_digit_number() -> None:
    assert digit_count(123) == 3


def test_a_negative_number_is_counted_by_its_digits_alone() -> None:
    assert digit_count(-123) == 3
""",
    ),
    _spec(
        "d5r_numeric.truncate_to_step",
        _NUMERIC,
        "truncate_to_step",
        "Cutting a reading back to a whole step of the scale, towards zero.",
        "truncate_to_step() cuts a reading below zero further away from zero, not towards it.",
        "truncate_to_step(value, step) cuts the reading back to a whole step towards zero.",
        "integer division floors, which moves a negative reading down rather than towards zero",
        """def truncate_to_step(value, step):
    whole = value // step
    return whole * step""",
        """def truncate_to_step(value, step):
    whole = int(value / step)
    return whole * step""",
        """
def test_a_reading_above_zero_is_cut_back() -> None:
    assert truncate_to_step(7, 5) == 5


def test_a_reading_below_zero_is_cut_towards_zero() -> None:
    assert truncate_to_step(-7, 5) == -5
""",
    ),
    # ------------------------------------------------------------------ data transformation
    _spec(
        "d5r_transform.field_totals",
        _TRANSFORM,
        "field_totals",
        "Adding up one field across a run of records.",
        "field_totals() falls over on a record that does not carry the field.",
        "field_totals(records, field) totals the field, skipping records that lack it.",
        "the field is read straight out of each record without asking whether it is there",
        """def field_totals(records, field):
    return sum(record[field] for record in records)""",
        """def field_totals(records, field):
    return sum(record.get(field, 0) for record in records)""",
        """
def test_the_field_is_totalled() -> None:
    assert field_totals([{"n": 1}, {"n": 2}], "n") == 3


def test_a_record_without_the_field_is_skipped() -> None:
    assert field_totals([{"n": 1}, {}], "n") == 1
""",
    ),
    _spec(
        "d5r_transform.drop_fields",
        _TRANSFORM,
        "drop_fields",
        "Removing the fields a downstream reader must not see.",
        "drop_fields() edits the caller's record instead of returning a new one.",
        "drop_fields(record, names) returns a copy without the named fields.",
        "it deletes from the record it was handed, so the caller's copy changes too",
        """def drop_fields(record, names):
    for name in names:
        if name in record:
            del record[name]
    return record""",
        """def drop_fields(record, names):
    return {key: value for key, value in record.items() if key not in names}""",
        """
def test_the_named_fields_are_removed() -> None:
    assert drop_fields({"a": 1, "b": 2}, ["b"]) == {"a": 1}


def test_the_callers_record_is_left_alone() -> None:
    record = {"a": 1, "b": 2}
    drop_fields(record, ["b"])
    assert record == {"a": 1, "b": 2}
""",
    ),
    _spec(
        "d5r_transform.count_by_field",
        _TRANSFORM,
        "count_by_field",
        "Tallying how many records carry each value of a field.",
        "count_by_field() falls over on the first value it has not seen before.",
        "count_by_field(records, field) returns a tally of the field's values.",
        "the tally is read before it is written, so a fresh value has nothing to read",
        """def count_by_field(records, field):
    tally = {}
    for record in records:
        tally[record[field]] += 1
    return tally""",
        """def count_by_field(records, field):
    tally = {}
    for record in records:
        value = record[field]
        tally[value] = tally.get(value, 0) + 1
    return tally""",
        """
def test_values_are_tallied() -> None:
    records = [{"k": "a"}, {"k": "b"}, {"k": "a"}]
    assert count_by_field(records, "k") == {"a": 2, "b": 1}


def test_no_records_tally_to_nothing() -> None:
    assert count_by_field([], "k") == {}
""",
    ),
    _spec(
        "d5r_transform.reorder_fields",
        _TRANSFORM,
        "reorder_fields",
        "Putting the fields of a record into the order the report declares.",
        "reorder_fields() loses the fields the report does not name.",
        "reorder_fields(record, order) returns the record with the named fields first.",
        "it builds the answer from the named fields alone and never adds the rest",
        """def reorder_fields(record, order):
    return {name: record[name] for name in order if name in record}""",
        """def reorder_fields(record, order):
    out = {name: record[name] for name in order if name in record}
    out.update({key: value for key, value in record.items() if key not in out})
    return out""",
        """
def test_the_named_fields_come_first() -> None:
    record = {"c": 3, "a": 1, "b": 2}
    assert list(reorder_fields(record, ["a", "b"])) == ["a", "b", "c"]


def test_no_field_is_lost() -> None:
    record = {"c": 3, "a": 1}
    assert reorder_fields(record, ["a"]) == {"a": 1, "c": 3}
""",
    ),
    _spec(
        "d5r_transform.values_in_order",
        _TRANSFORM,
        "values_in_order",
        "Reading a mapping's values out in the order of its keys.",
        "values_in_order() reads them in whatever order the mapping was built.",
        "values_in_order(mapping) returns the values ordered by their keys.",
        "it reads the values straight off the mapping rather than ordering the keys first",
        """def values_in_order(mapping):
    out = []
    for value in mapping.values():
        out.append(value)
    return out""",
        """def values_in_order(mapping):
    return [mapping[key] for key in sorted(mapping)]""",
        """
def test_the_values_follow_the_sorted_keys() -> None:
    assert values_in_order({"b": 2, "a": 1}) == [1, 2]


def test_an_empty_mapping_reads_as_nothing() -> None:
    assert values_in_order({}) == []
""",
    ),
    _spec(
        "d5r_transform.merge_defaults",
        _TRANSFORM,
        "merge_defaults",
        "Filling in the settings a caller did not supply.",
        "merge_defaults() lets the defaults overwrite what the caller supplied.",
        "merge_defaults(supplied, defaults) fills in only what the caller left out.",
        "the two are merged with the defaults last, which is the wrong way round",
        """def merge_defaults(supplied, defaults):
    return {**supplied, **defaults}""",
        """def merge_defaults(supplied, defaults):
    return dict(defaults) | supplied""",
        """
def test_a_supplied_setting_wins_over_its_default() -> None:
    assert merge_defaults({"a": 1}, {"a": 9, "b": 2}) == {"a": 1, "b": 2}


def test_a_setting_left_out_takes_its_default() -> None:
    assert merge_defaults({}, {"a": 9}) == {"a": 9}
""",
    ),
    _spec(
        "d5r_transform.keys_with_value",
        _TRANSFORM,
        "keys_with_value",
        "Finding every key a mapping files under one value.",
        "keys_with_value() answers with only the last key it found.",
        "keys_with_value(mapping, wanted) returns every key holding that value, sorted.",
        "the answer is reassigned each time round the loop instead of collected",
        """def keys_with_value(mapping, wanted):
    found = []
    for key, value in mapping.items():
        if value == wanted:
            found = [key]
    return found""",
        """def keys_with_value(mapping, wanted):
    return sorted(key for key, value in mapping.items() if value == wanted)""",
        """
def test_every_key_holding_the_value_is_returned() -> None:
    assert keys_with_value({"a": 1, "b": 1, "c": 2}, 1) == ["a", "b"]


def test_a_value_nothing_holds_returns_nothing() -> None:
    assert keys_with_value({"a": 1}, 9) == []
""",
    ),
    _spec(
        "d5r_transform.rename_one_field",
        _TRANSFORM,
        "rename_one_field",
        "Renaming one field of a record for a downstream reader.",
        "rename_one_field() leaves the old name behind beside the new one.",
        "rename_one_field(record, old, new) returns the record with the field renamed.",
        "the new name is added but the old one is never taken away",
        """def rename_one_field(record, old, new):
    out = dict(record)
    out[new] = out[old]
    return out""",
        """def rename_one_field(record, old, new):
    out = dict(record)
    out[new] = out.pop(old)
    return out""",
        """
def test_the_field_is_renamed() -> None:
    assert rename_one_field({"a": 1, "z": 9}, "a", "b") == {"b": 1, "z": 9}


def test_the_old_name_is_gone() -> None:
    assert "a" not in rename_one_field({"a": 1}, "a", "b")
""",
    ),
    _spec(
        "d5r_transform.stack_rows",
        _TRANSFORM,
        "stack_rows",
        "Stacking several blocks of rows into one.",
        "stack_rows() nests the blocks instead of stacking them.",
        "stack_rows(blocks) returns one list holding every row of every block in order.",
        "it appends each block whole, which builds a list of blocks rather than of rows",
        """def stack_rows(blocks):
    out = []
    for block in blocks:
        out.append(block)
    return out""",
        """def stack_rows(blocks):
    out = []
    for block in blocks:
        out.extend(block)
    return out""",
        """
def test_the_rows_of_every_block_come_through() -> None:
    assert stack_rows([[1, 2], [3]]) == [1, 2, 3]


def test_no_blocks_stack_to_nothing() -> None:
    assert stack_rows([]) == []
""",
    ),
    _spec(
        "d5r_transform.longest_field_value",
        _TRANSFORM,
        "longest_field_value",
        "Finding the widest value a column carries.",
        "longest_field_value() answers with the width rather than with the value.",
        "longest_field_value(records, field) returns the longest value the field carries.",
        "it maximises over the widths and returns the width it maximised",
        """def longest_field_value(records, field):
    return max(len(str(record[field])) for record in records)""",
        """def longest_field_value(records, field):
    return max((record[field] for record in records), key=lambda value: len(str(value)))""",
        """
def test_the_widest_value_comes_back() -> None:
    assert longest_field_value([{"n": "ab"}, {"n": "abcd"}], "n") == "abcd"


def test_a_single_record_carries_its_own_widest() -> None:
    assert longest_field_value([{"n": "x"}], "n") == "x"
""",
    ),
    # ----------------------------------------------------------------- state and idempotency
    _spec(
        "d5r_state.mark_seen",
        _STATE,
        "mark_seen",
        "Recording that an identifier has been dealt with.",
        "mark_seen() records the same identifier twice.",
        "mark_seen(seen, identifier) returns the record with the identifier in it once.",
        "it appends without asking whether the identifier is already recorded",
        """def mark_seen(seen, identifier):
    out = list(seen)
    out.append(identifier)
    return out""",
        """def mark_seen(seen, identifier):
    return list(dict.fromkeys([*seen, identifier]))""",
        """
def test_a_fresh_identifier_is_recorded() -> None:
    assert mark_seen(["a"], "b") == ["a", "b"]


def test_an_identifier_already_recorded_is_not_recorded_twice() -> None:
    assert mark_seen(["a"], "a") == ["a"]
""",
    ),
    _spec(
        "d5r_state.bump_counter",
        _STATE,
        "bump_counter",
        "Raising the count a name is filed under.",
        "bump_counter() changes the caller's tally rather than returning a new one.",
        "bump_counter(counts, name) returns a new tally with the name's count one higher.",
        "the tally it was handed is written to directly, so the caller's copy moves too",
        """def bump_counter(counts, name):
    counts[name] = counts.get(name, 0) + 1
    return counts""",
        """def bump_counter(counts, name):
    out = dict(counts)
    out[name] = out.get(name, 0) + 1
    return out""",
        """
def test_the_count_goes_up() -> None:
    assert bump_counter({"a": 1}, "a") == {"a": 2}


def test_the_callers_tally_is_left_alone() -> None:
    counts = {"a": 1}
    bump_counter(counts, "a")
    assert counts == {"a": 1}
""",
    ),
    _spec(
        "d5r_state.forget_after",
        _STATE,
        "forget_after",
        "Dropping the entries a store has held past their moment.",
        "forget_after() drops an entry sitting exactly on the cutoff.",
        "forget_after(entries, cutoff) keeps every entry stamped at or after the cutoff.",
        "the comparison is strict, so an entry stamped exactly at the cutoff is dropped",
        """def forget_after(entries, cutoff):
    return {name: stamp for name, stamp in entries.items() if stamp > cutoff}""",
        """def forget_after(entries, cutoff):
    return dict(pair for pair in entries.items() if pair[1] >= cutoff)""",
        """
def test_an_entry_after_the_cutoff_is_kept() -> None:
    assert forget_after({"a": 9}, 5) == {"a": 9}


def test_an_entry_exactly_on_the_cutoff_is_kept() -> None:
    assert forget_after({"a": 5}, 5) == {"a": 5}
""",
    ),
    _spec(
        "d5r_state.take_slot",
        _STATE,
        "take_slot",
        "Handing out the next free slot of a fixed set.",
        "take_slot() hands out a slot that is already taken.",
        "take_slot(taken, size) returns the lowest slot not already taken, or nothing.",
        "it counts the taken slots and hands back that number, which is taken when there is a gap",
        """def take_slot(taken, size):
    return len(taken)""",
        """def take_slot(taken, size):
    for slot in range(size):
        if slot not in taken:
            return slot
    return None""",
        """
def test_the_lowest_free_slot_is_handed_out() -> None:
    assert take_slot({1}, 3) == 0


def test_a_gap_below_a_taken_slot_is_filled_first() -> None:
    assert take_slot({0, 2}, 3) == 1
""",
    ),
    _spec(
        "d5r_state.close_once",
        _STATE,
        "close_once",
        "Closing a handle that may be closed more than once.",
        "close_once() reports a second close as though it had done something.",
        "close_once(state) returns (changed, state) with changed true only the first time.",
        "it reports a change every time rather than only when the state actually moved",
        """def close_once(state):
    return True, {**state, "closed": True}""",
        """def close_once(state):
    if state.get("closed"):
        return False, dict(state)
    return True, {**state, "closed": True}""",
        """
def test_the_first_close_changes_the_state() -> None:
    assert close_once({"closed": False}) == (True, {"closed": True})


def test_a_second_close_changes_nothing() -> None:
    assert close_once({"closed": True}) == (False, {"closed": True})
""",
    ),
    _spec(
        "d5r_state.latest_wins",
        _STATE,
        "latest_wins",
        "Keeping the most recent reading each sensor sent.",
        "latest_wins() keeps the first reading rather than the most recent one.",
        "latest_wins(readings) returns the last reading each sensor sent.",
        "the entry is only written when the sensor is unknown, so a later reading is ignored",
        """def latest_wins(readings):
    out = {}
    for sensor, value in readings:
        if sensor not in out:
            out[sensor] = value
    return out""",
        """def latest_wins(readings):
    out = {}
    for sensor, value in readings:
        out[sensor] = value
    return out""",
        """
def test_the_most_recent_reading_is_kept() -> None:
    assert latest_wins([("a", 1), ("a", 2)]) == {"a": 2}


def test_each_sensor_keeps_its_own() -> None:
    assert latest_wins([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}
""",
    ),
    _spec(
        "d5r_state.release_hold",
        _STATE,
        "release_hold",
        "Giving back a hold on a shared resource.",
        "release_hold() lets the count fall below nothing.",
        "release_hold(counts, name) lowers the count by one and never goes below zero.",
        "it subtracts without a floor, so releasing more often than holding goes negative",
        """def release_hold(counts, name):
    out = dict(counts)
    out[name] = out.get(name, 0) - 1
    return out""",
        """def release_hold(counts, name):
    out = dict(counts)
    out[name] = max(out.get(name, 0) - 1, 0)
    return out""",
        """
def test_a_hold_is_given_back() -> None:
    assert release_hold({"a": 2}, "a") == {"a": 1}


def test_the_count_never_falls_below_nothing() -> None:
    assert release_hold({"a": 0}, "a") == {"a": 0}
""",
    ),
    _spec(
        "d5r_state.apply_once_by_key",
        _STATE,
        "apply_once_by_key",
        "Applying an instruction that may arrive more than once.",
        "apply_once_by_key() applies a repeated instruction a second time.",
        "apply_once_by_key(state, key, amount) adds the amount only the first time the key "
        "arrives.",
        "the key is recorded but never consulted before the amount is added",
        """def apply_once_by_key(state, key, amount):
    total = state["total"] + amount
    return {"total": total, "keys": [*state["keys"], key]}""",
        """def apply_once_by_key(state, key, amount):
    if key in state["keys"]:
        return {"total": state["total"], "keys": list(state["keys"])}
    return {"total": state["total"] + amount, "keys": [*state["keys"], key]}""",
        """
def test_a_fresh_key_is_applied() -> None:
    state = {"total": 0, "keys": []}
    assert apply_once_by_key(state, "k", 5) == {"total": 5, "keys": ["k"]}


def test_a_repeated_key_is_not_applied_again() -> None:
    state = {"total": 5, "keys": ["k"]}
    assert apply_once_by_key(state, "k", 5) == {"total": 5, "keys": ["k"]}
""",
    ),
    _spec(
        "d5r_state.advance_stage",
        _STATE,
        "advance_stage",
        "Moving a job on to the stage after the one it is at.",
        "advance_stage() runs off the end of the list of stages.",
        "advance_stage(stage, stages) returns the next stage, or the last one at the end.",
        "the position is raised without checking there is a stage after it",
        """def advance_stage(stage, stages):
    return stages[stages.index(stage) + 1]""",
        """def advance_stage(stage, stages):
    place = stages.index(stage)
    if place + 1 >= len(stages):
        return stage
    return stages[place + 1]""",
        """
def test_a_job_moves_on_to_the_next_stage() -> None:
    assert advance_stage("a", ["a", "b", "c"]) == "b"


def test_a_job_at_the_last_stage_stays_there() -> None:
    assert advance_stage("c", ["a", "b", "c"]) == "c"
""",
    ),
    _spec(
        "d5r_state.reset_between_runs",
        _STATE,
        "reset_between_runs",
        "Clearing the per-run scratch space without losing the settings.",
        "reset_between_runs() clears the settings along with the scratch space.",
        "reset_between_runs(state) returns the state with the scratch space empty and the "
        "settings kept.",
        "it builds a fresh state from nothing rather than from the settings it must keep",
        """def reset_between_runs(state):
    return {"settings": {}, "scratch": {}}""",
        """def reset_between_runs(state):
    return {"settings": dict(state["settings"]), "scratch": {}}""",
        """
def test_the_scratch_space_is_cleared() -> None:
    state = {"settings": {"a": 1}, "scratch": {"x": 2}}
    assert reset_between_runs(state)["scratch"] == {}


def test_the_settings_are_kept() -> None:
    state = {"settings": {"a": 1}, "scratch": {"x": 2}}
    assert reset_between_runs(state)["settings"] == {"a": 1}
""",
    ),
    # ------------------------------------------------------------------------ error handling
    _spec(
        "d5r_errors.require_positive",
        _ERRORS,
        "require_positive",
        "Refusing a size that cannot be a size.",
        "require_positive() lets a size of nothing through.",
        "require_positive(value) returns the value and refuses anything at or below zero.",
        "the guard tests for a negative only, so nothing at all passes it",
        """def require_positive(value):
    if value < 0:
        raise ValueError("a size must be positive")
    return value""",
        """def require_positive(value):
    if value <= 0:
        raise ValueError(f"a size must be positive, got {value}")
    return int(value)""",
        """
import pytest


def test_a_real_size_is_returned() -> None:
    assert require_positive(3) == 3


def test_a_size_of_nothing_is_refused() -> None:
    with pytest.raises(ValueError):
        require_positive(0)
""",
    ),
    _spec(
        "d5r_errors.reason_text",
        _ERRORS,
        "reason_text",
        "Writing the reason a step failed into the report.",
        "reason_text() writes the exception object rather than what it says.",
        "reason_text(error) returns the text of the failure, never an empty line.",
        "the object is formatted rather than read, and an error carrying no message reads empty",
        """def reason_text(error):
    return format(error)""",
        """def reason_text(error):
    said = str(error)
    if said:
        return said
    return type(error).__name__""",
        """
def test_the_message_is_written() -> None:
    assert reason_text(ValueError("no room")) == "no room"


def test_an_error_carrying_no_message_names_its_kind() -> None:
    assert reason_text(ValueError()) == "ValueError"
""",
    ),
    _spec(
        "d5r_errors.attempt_with_default",
        _ERRORS,
        "attempt_with_default",
        "Falling back to a default when a lookup will not work.",
        "attempt_with_default() swallows the interruption that should stop the run.",
        "attempt_with_default(step, default) returns the default for an ordinary failure only.",
        "catching every interruption there is means a cancellation is treated as a failure",
        """def attempt_with_default(step, default):
    try:
        return step()
    except BaseException:
        return default""",
        """def attempt_with_default(step, default):
    try:
        return step()
    except Exception:
        return default""",
        """
import pytest


def _refuse():
    raise ValueError("no")


def _cancel():
    raise KeyboardInterrupt


def test_an_ordinary_failure_takes_the_default() -> None:
    assert attempt_with_default(_refuse, 0) == 0


def test_a_cancellation_stops_the_run() -> None:
    with pytest.raises(KeyboardInterrupt):
        attempt_with_default(_cancel, 0)
""",
    ),
    _spec(
        "d5r_errors.close_every_handle",
        _ERRORS,
        "close_every_handle",
        "Closing every handle even when one of them objects.",
        "close_every_handle() stops at the first handle that objects.",
        "close_every_handle(handles) closes them all and returns how many closed cleanly.",
        "one handle raising leaves the loop, so the handles after it are never closed",
        """def close_every_handle(handles):
    closed = 0
    for handle in handles:
        handle()
        closed += 1
    return closed""",
        """def close_every_handle(handles):
    closed = 0
    for handle in handles:
        try:
            handle()
        except Exception:
            continue
        closed += 1
    return closed""",
        """
def _refuse():
    raise RuntimeError("stuck")


def test_every_handle_is_closed() -> None:
    assert close_every_handle([lambda: None, lambda: None]) == 2


def test_a_handle_that_objects_does_not_stop_the_rest() -> None:
    assert close_every_handle([_refuse, lambda: None]) == 1
""",
    ),
    _spec(
        "d5r_errors.name_the_kind",
        _ERRORS,
        "name_the_kind",
        "Naming what kind of failure the log is about to record.",
        "name_the_kind() names the exact kind rather than the family it belongs to.",
        "name_the_kind(error) reports 'value' for a ValueError and any kind derived from one.",
        "comparing the exact type misses a narrower error derived from the one being looked for",
        """def name_the_kind(error):
    if type(error) is ValueError:
        return "value"
    return "other" """,
        """def name_the_kind(error):
    if isinstance(error, ValueError):
        return "value"
    return "other" """,
        """
class Narrower(ValueError):
    pass


def test_a_value_error_is_named() -> None:
    assert name_the_kind(ValueError("x")) == "value"


def test_a_narrower_error_is_named_the_same() -> None:
    assert name_the_kind(Narrower("x")) == "value"
""",
    ),
    _spec(
        "d5r_errors.first_objection",
        _ERRORS,
        "first_objection",
        "Reporting the first thing wrong with a submission.",
        "first_objection() reports the last objection rather than the first.",
        "first_objection(objections) returns the first objection, or nothing when there are none.",
        "the answer is reassigned each time round the loop instead of returned at once",
        """def first_objection(objections):
    found = None
    for objection in objections:
        if objection:
            found = objection
    return found""",
        """def first_objection(objections):
    for objection in objections:
        if objection:
            return objection
    return None""",
        """
def test_the_first_objection_is_reported() -> None:
    assert first_objection(["too short", "too loud"]) == "too short"


def test_no_objections_report_nothing() -> None:
    assert first_objection([]) is None
""",
    ),
    _spec(
        "d5r_errors.retry_budget_left",
        _ERRORS,
        "retry_budget_left",
        "Saying how many attempts a caller has left.",
        "retry_budget_left() reports a negative budget once the attempts are spent.",
        "retry_budget_left(attempts, allowed) returns what is left, never below nothing.",
        "the subtraction has no floor under it",
        """def retry_budget_left(attempts, allowed):
    return allowed - len(attempts)""",
        """def retry_budget_left(attempts, allowed):
    return max(allowed - len(attempts), 0)""",
        """
def test_the_budget_left_after_one_attempt() -> None:
    assert retry_budget_left(["a"], 3) == 2


def test_a_spent_budget_reads_as_nothing_left() -> None:
    assert retry_budget_left(["a", "b", "c", "d", "e"], 3) == 0
""",
    ),
    _spec(
        "d5r_errors.wrap_with_context",
        _ERRORS,
        "wrap_with_context",
        "Adding the step's name to a failure before it goes up.",
        "wrap_with_context() loses the original failure as the cause.",
        "wrap_with_context(step, error) raises a RuntimeError naming the step, with the "
        "original attached as its cause.",
        "raising without `from` leaves the new error with no cause recorded",
        """def wrap_with_context(step, error):
    raise RuntimeError(f"{step} failed")""",
        """def wrap_with_context(step, error):
    raise RuntimeError(f"{step} failed: {str(error)}") from error""",
        """
import pytest


def test_the_step_is_named() -> None:
    with pytest.raises(RuntimeError, match="upload"):
        wrap_with_context("upload", ValueError("no room"))


def test_the_original_failure_is_the_cause() -> None:
    original = ValueError("no room")
    with pytest.raises(RuntimeError) as caught:
        wrap_with_context("upload", original)
    assert caught.value.__cause__ is original
""",
    ),
    _spec(
        "d5r_errors.count_failures",
        _ERRORS,
        "count_failures",
        "Counting how many steps of a run went wrong.",
        "count_failures() counts a step that reported nothing as a failure.",
        "count_failures(outcomes) counts the outcomes carrying a reason.",
        "an outcome of None is not a reason, but the count tests the key rather than the value",
        """def count_failures(outcomes):
    return sum(1 for outcome in outcomes if "reason" in outcome)""",
        """def count_failures(outcomes):
    return sum(1 for outcome in outcomes if outcome.get("reason"))""",
        """
def test_a_step_carrying_a_reason_counts() -> None:
    assert count_failures([{"reason": "no room"}]) == 1


def test_a_step_whose_reason_is_nothing_does_not_count() -> None:
    assert count_failures([{"reason": None}]) == 0
""",
    ),
    _spec(
        "d5r_errors.exit_status_for",
        _ERRORS,
        "exit_status_for",
        "Choosing the status a run should leave behind it.",
        "exit_status_for() leaves a clean status behind a run that had warnings only.",
        "exit_status_for(report) returns 0 only for a run with neither errors nor warnings.",
        "only the errors are looked at, so a run carrying warnings alone still reads as clean",
        """def exit_status_for(report):
    if report.get("errors"):
        return 1
    return 0""",
        """def exit_status_for(report):
    if report.get("errors"):
        return 1
    return 2 if len(report.get("warnings", ())) else 0""",
        """
def test_a_run_with_errors_reads_as_failed() -> None:
    assert exit_status_for({"errors": ["x"]}) == 1


def test_a_run_with_warnings_alone_does_not_read_as_clean() -> None:
    assert exit_status_for({"warnings": ["x"]}) == 2
""",
    ),
)
