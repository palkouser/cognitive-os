"""The Sprint 21D7 certification corpus: fresh four-candidate groups.

D7 needs a hundred *independent* certification decisions, and independence means distinct fitted
feature vectors, so the only route to a hundred is to author a hundred. This module is that
authoring. It is the certification half; D6's hundred certification groups are the demoted
bar-setting half that places the bar, and S21D7-022 proves the two share no group, no clone and
no body.

The spec shape is `D2TaskSpec`, unchanged, for the reason D4, D5 and D6 all gave: the catalogue,
the template registry and the campaign already agree about it.

Every group obeys the authoring contract D2 froze and D4, D5 and D6 re-proved:

- the **baseline** passes the visible suite and fails the hidden one;
- **variant one** and **variant two** repair the contract by materially different routes and
  pass both suites;
- **variant three** fixes the first declared edge case only and **variant four** the second
  only, so both pass the visible suite and fail the hidden one.

Three failure modes account for every authoring defect the predecessors found, and all three are
invisible without executing:

1. *The two hidden tests probe one defect wearing two descriptions.* Then no partial fix repairs
   exactly one, and variants three and four both pass hidden. Every edge-case pair here is chosen
   so that a fix for one leaves the other untouched, and `scripts/corpus_d7.py` is what decides
   whether the choice held.
2. *The baseline is broken so badly it fails its own visible suite.* The defect has to be
   peripheral enough that the ordinary case still works, and every visible case has to be one
   both readings agree on — D6's `digit_positions` is the lesson.
3. *A near-clone collision at the level of the task, not the code.* Rewriting a variant cannot
   repair that — the group is withdrawn and a different one authored. With 626 released groups
   the obvious small-function repair space is heavily occupied, so every module name here was
   checked against the released corpus **before** its bodies were written, and the pre-check
   cannot see saturation: a task whose core step is a saturated primitive collides however it is
   written.

Two constraints come from elsewhere in the sprint. The invariance sample renames identifiers, so
every body binds its names locally and none reaches a name through `getattr`, `globals()` or any
other reflective route, which `correction_source.py` refuses outright. And no group here may be
read before the conformal bar exists: revision 7 forbids it, and the campaign is what enforces
the order.

**One constraint is new in D7, and it is the class's own.** The containment share this sprint
fits reads the *added lines* of each candidate against the baseline, so the two-complete
two-partial anatomy has to hold at the level of the lines a repair adds, not only at the level of
what it returns. A variant that repairs by rewriting the whole function body, rather than by
adding a guard the partial repairs also add, carries a repair no partial repair can be contained
in. That is legitimate — the share degrades to a consensus prior rather than failing, and §6 of
the backlog says so — but a corpus made entirely of whole-body rewrites would measure the class
on an anatomy the authoring contract does not promise. The variants here repair in place where
the contract permits it, which is what D2 froze and what every predecessor corpus already does.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# ------------------------------------------------------------------ boundary and collections

_G001 = D2TaskSpec(
    template_id="d7_boundary.lane_loads",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-lane-loads",
    module="lane_loads",
    module_doc="Spreading work across lanes that are not equally busy.",
    issue=(
        "assign() is documented to hand each weight to the lane carrying the least so far. "
        "Callers report that one heavy weight followed by light ones leaves the busy lane just "
        "as busy, and that a lane which happens to receive nothing disappears from the answer "
        "instead of coming back empty."
    ),
    expected=(
        "assign(weights, lanes) returns one list per lane, in lane order, holding the weights "
        "that lane received in arrival order. Each weight goes to the lane with the smallest "
        "load so far, with a tie going to the lowest-numbered lane, and every lane is present "
        "even when it received nothing."
    ),
    baseline_reason=(
        "it hands out lanes by arrival position rather than by load, and it builds the answer "
        "only from the lanes it happened to touch"
    ),
    edge_cases=(
        "a heavy weight sends the following ones to the other lane",
        "a lane that receives nothing is still present, and empty",
    ),
    baseline='''def assign(weights, lanes):
    """Spread `weights` across `lanes`."""
    filled = {}
    for position, weight in enumerate(weights):
        lane = position % lanes
        filled.setdefault(lane, []).append(weight)
    return [filled[lane] for lane in sorted(filled)]''',
    variant_one='''def assign(weights, lanes):
    """Spread `weights` across `lanes`."""
    filled = [[] for _ in range(lanes)]
    loads = [0] * lanes
    for weight in weights:
        lane = loads.index(min(loads))
        filled[lane].append(weight)
        loads[lane] += weight
    return filled''',
    variant_two='''def assign(weights, lanes):
    """Spread `weights` across `lanes`."""
    filled = [[] for _ in range(lanes)]
    for weight in weights:
        chosen = 0
        for lane in range(1, lanes):
            if sum(filled[lane]) < sum(filled[chosen]):
                chosen = lane
        filled[chosen].append(weight)
    return filled''',
    variant_three='''def assign(weights, lanes):
    """Spread `weights` across `lanes`."""
    filled = {}
    loads = [0] * lanes
    for weight in weights:
        lane = loads.index(min(loads))
        filled.setdefault(lane, []).append(weight)
        loads[lane] += weight
    return [filled[lane] for lane in sorted(filled)]''',
    variant_four='''def assign(weights, lanes):
    """Spread `weights` across `lanes`."""
    filled = [[] for _ in range(lanes)]
    rounds = -(-len(weights) // lanes) if lanes else 0
    taken = 0
    for _ in range(rounds):
        for lane in range(lanes):
            if taken < len(weights):
                filled[lane].append(weights[taken])
                taken += 1
    return filled''',
    visible_test=_test_module(
        "lane_loads",
        "Published contract for spreading work across lanes.",
        """
def test_equal_weights_land_one_per_lane() -> None:
    assert assign([2, 2], 2) == [[2], [2]]


def test_a_single_lane_takes_everything() -> None:
    assert assign([5, 1], 1) == [[5, 1]]
""",
        imports="from lane_loads import assign\n",
    ),
    hidden_test=_test_module(
        "lane_loads",
        "The part of the contract the published tests do not state.",
        """
def test_equal_weights_land_one_per_lane() -> None:
    assert assign([2, 2], 2) == [[2], [2]]


def test_a_heavy_weight_sends_the_rest_to_the_other_lane() -> None:
    assert assign([5, 1, 1], 2) == [[5], [1, 1]]


def test_a_lane_that_receives_nothing_comes_back_empty() -> None:
    assert assign([4], 3) == [[4], [], []]
""",
        imports="from lane_loads import assign\n",
    ),
)

_G002 = D2TaskSpec(
    template_id="d7_boundary.escort_pairs",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-escort-pairs",
    module="escort_pairs",
    module_doc="Giving every guest an escort when there are fewer escorts than guests.",
    issue=(
        "pair_up() is documented to reuse the escorts from the beginning once they have all "
        "been given out. Callers report that the last escort is handed the whole remainder of "
        "the queue instead, and that a party with no escorts at all fails outright rather than "
        "reporting that nobody is escorting."
    ),
    expected=(
        "pair_up(guests, escorts) returns one (guest, escort) pair per guest in order. Escorts "
        "are handed out in order and reused from the beginning once exhausted; with no escorts "
        "at all every guest is paired with None."
    ),
    baseline_reason=(
        "past the end of the escort list it repeats the last escort, and it reads that last "
        "escort without checking that there is one"
    ),
    edge_cases=(
        "escorts are reused from the beginning once exhausted",
        "with no escorts every guest is paired with None",
    ),
    baseline='''def pair_up(guests, escorts):
    """Pair every guest with an escort."""
    pairs = []
    for position, guest in enumerate(guests):
        if position < len(escorts):
            escort = escorts[position]
        else:
            escort = escorts[-1]
        pairs.append((guest, escort))
    return pairs''',
    variant_one='''def pair_up(guests, escorts):
    """Pair every guest with an escort."""
    pairs = []
    for position, guest in enumerate(guests):
        if escorts:
            escort = escorts[position % len(escorts)]
        else:
            escort = None
        pairs.append((guest, escort))
    return pairs''',
    variant_two='''def pair_up(guests, escorts):
    """Pair every guest with an escort."""
    if not escorts:
        return [(guest, None) for guest in guests]
    pairs = []
    cursor = 0
    for guest in guests:
        pairs.append((guest, escorts[cursor]))
        cursor += 1
        if cursor == len(escorts):
            cursor = 0
    return pairs''',
    variant_three='''def pair_up(guests, escorts):
    """Pair every guest with an escort."""
    pairs = []
    for position, guest in enumerate(guests):
        escort = escorts[position % len(escorts)]
        pairs.append((guest, escort))
    return pairs''',
    variant_four='''def pair_up(guests, escorts):
    """Pair every guest with an escort."""
    pairs = []
    for position, guest in enumerate(guests):
        if not escorts:
            escort = None
        elif position < len(escorts):
            escort = escorts[position]
        else:
            escort = escorts[-1]
        pairs.append((guest, escort))
    return pairs''',
    visible_test=_test_module(
        "escort_pairs",
        "Published contract for handing out escorts.",
        """
def test_one_escort_each_when_the_counts_agree() -> None:
    assert pair_up(["ann", "bo"], ["x", "y"]) == [("ann", "x"), ("bo", "y")]


def test_no_guests_need_no_escorts() -> None:
    assert pair_up([], ["x"]) == []
""",
        imports="from escort_pairs import pair_up\n",
    ),
    hidden_test=_test_module(
        "escort_pairs",
        "The part of the contract the published tests do not state.",
        """
def test_one_escort_each_when_the_counts_agree() -> None:
    assert pair_up(["ann", "bo"], ["x", "y"]) == [("ann", "x"), ("bo", "y")]


def test_escorts_are_reused_from_the_beginning() -> None:
    assert pair_up(["ann", "bo", "cy"], ["x", "y"]) == [("ann", "x"), ("bo", "y"), ("cy", "x")]


def test_no_escorts_at_all_pairs_every_guest_with_none() -> None:
    assert pair_up(["ann"], []) == [("ann", None)]
""",
        imports="from escort_pairs import pair_up\n",
    ),
)

_G003 = D2TaskSpec(
    template_id="d7_boundary.seat_rows",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-seat-rows",
    module="seat_rows",
    module_doc="Seating parties into rows without splitting a party.",
    issue=(
        "seat() is documented to keep every party together and to give a party too large for a "
        "row a row of its own. Callers report that a party which exactly fills the remaining "
        "seats is pushed to the next row anyway, and that a party larger than the row vanishes "
        "from the seating plan."
    ),
    expected=(
        "seat(sizes, width) returns the rows in order, each a list of the party sizes seated in "
        "it. A party is seated in the current row while it fits, exactly filling the row "
        "included, and starts a new row otherwise. A party larger than the width gets a row of "
        "its own."
    ),
    baseline_reason=(
        "it tests the remaining seats with a strict comparison, so an exact fit starts a new "
        "row, and it skips any party wider than a row instead of giving it one"
    ),
    edge_cases=(
        "a party that exactly fills the remaining seats stays in the row",
        "a party larger than a row gets a row of its own",
    ),
    baseline='''def seat(sizes, width):
    """Seat parties of the given sizes into rows `width` wide."""
    rows = []
    row = []
    used = 0
    for size in sizes:
        if size > width:
            continue
        if used + size < width:
            row.append(size)
            used += size
        else:
            if row:
                rows.append(row)
            row = [size]
            used = size
    if row:
        rows.append(row)
    return rows''',
    variant_one='''def seat(sizes, width):
    """Seat parties of the given sizes into rows `width` wide."""
    rows = []
    row = []
    used = 0
    for size in sizes:
        if row and used + size > width:
            rows.append(row)
            row = []
            used = 0
        row.append(size)
        used += size
    if row:
        rows.append(row)
    return rows''',
    variant_two='''def seat(sizes, width):
    """Seat parties of the given sizes into rows `width` wide."""
    rows = []
    for size in sizes:
        if rows and sum(rows[-1]) + size <= width:
            rows[-1].append(size)
        else:
            rows.append([size])
    return rows''',
    variant_three='''def seat(sizes, width):
    """Seat parties of the given sizes into rows `width` wide."""
    rows = []
    row = []
    used = 0
    for size in sizes:
        if size > width:
            continue
        if used + size <= width:
            row.append(size)
            used += size
        else:
            if row:
                rows.append(row)
            row = [size]
            used = size
    if row:
        rows.append(row)
    return rows''',
    variant_four='''def seat(sizes, width):
    """Seat parties of the given sizes into rows `width` wide."""
    rows = []
    row = []
    used = 0
    for size in sizes:
        if size > width:
            if row:
                rows.append(row)
                row = []
                used = 0
            rows.append([size])
            continue
        if used + size < width:
            row.append(size)
            used += size
        else:
            if row:
                rows.append(row)
            row = [size]
            used = size
    if row:
        rows.append(row)
    return rows''',
    visible_test=_test_module(
        "seat_rows",
        "Published contract for seating parties into rows.",
        """
def test_parties_that_all_fit_share_one_row() -> None:
    assert seat([2, 3], 10) == [[2, 3]]


def test_no_parties_need_no_rows() -> None:
    assert seat([], 10) == []
""",
        imports="from seat_rows import seat\n",
    ),
    hidden_test=_test_module(
        "seat_rows",
        "The part of the contract the published tests do not state.",
        """
def test_parties_that_all_fit_share_one_row() -> None:
    assert seat([2, 3], 10) == [[2, 3]]


def test_a_party_that_exactly_fills_the_row_stays_in_it() -> None:
    assert seat([6, 4, 3], 10) == [[6, 4], [3]]


def test_a_party_larger_than_the_row_gets_its_own() -> None:
    assert seat([12, 3], 10) == [[12], [3]]
""",
        imports="from seat_rows import seat\n",
    ),
)

# ------------------------------------------------------------------ data transformation

_G004 = D2TaskSpec(
    template_id="d7_transform.stripe_rows",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-stripe-rows",
    module="stripe_rows",
    module_doc="Colouring the rows of a listing, headings excepted.",
    issue=(
        "stripe() is documented to give the body rows the shade colours in turn and to leave a "
        "heading out of that turn-taking. Callers report that a heading still consumes a shade, "
        "so the stripes restart out of step after one, and that a listing longer than the shade "
        "list fails instead of starting the shades again."
    ),
    expected=(
        "stripe(labels, shades) returns one colour per label. A label beginning with '#' is a "
        "heading and takes the colour 'head' without consuming a shade. Every other label takes "
        "the next shade, and the shades are reused from the beginning once exhausted."
    ),
    baseline_reason=(
        "it advances the shade cursor for a heading as well as for a body row, and it indexes "
        "the shade list with that cursor without folding it back to the start"
    ),
    edge_cases=(
        "a heading does not consume a shade",
        "the shades are reused from the beginning once exhausted",
    ),
    baseline='''def stripe(labels, shades):
    """Return the colour of every label."""
    painted = []
    cursor = 0
    for label in labels:
        if label.startswith("#"):
            painted.append("head")
            cursor += 1
        else:
            painted.append(shades[cursor])
            cursor += 1
    return painted''',
    variant_one='''def stripe(labels, shades):
    """Return the colour of every label."""
    painted = []
    cursor = 0
    for label in labels:
        if label.startswith("#"):
            painted.append("head")
        else:
            painted.append(shades[cursor % len(shades)])
            cursor += 1
    return painted''',
    variant_two='''def stripe(labels, shades):
    """Return the colour of every label."""
    body = [label for label in labels if not label.startswith("#")]
    order = {}
    for position, label in enumerate(body):
        order[position] = shades[position % len(shades)]
    painted = []
    seen = 0
    for label in labels:
        if label.startswith("#"):
            painted.append("head")
        else:
            painted.append(order[seen])
            seen += 1
    return painted''',
    variant_three='''def stripe(labels, shades):
    """Return the colour of every label."""
    painted = []
    cursor = 0
    for label in labels:
        if label.startswith("#"):
            painted.append("head")
        else:
            painted.append(shades[cursor])
            cursor += 1
    return painted''',
    variant_four='''def stripe(labels, shades):
    """Return the colour of every label."""
    painted = []
    cursor = 0
    for label in labels:
        if label.startswith("#"):
            painted.append("head")
            cursor += 1
        else:
            painted.append(shades[cursor % len(shades)])
            cursor += 1
    return painted''',
    visible_test=_test_module(
        "stripe_rows",
        "Published contract for colouring a listing.",
        """
def test_body_rows_take_the_shades_in_turn() -> None:
    assert stripe(["a", "b"], ["pale", "dark"]) == ["pale", "dark"]


def test_a_heading_takes_the_heading_colour() -> None:
    assert stripe(["#totals"], ["pale"]) == ["head"]
""",
        imports="from stripe_rows import stripe\n",
    ),
    hidden_test=_test_module(
        "stripe_rows",
        "The part of the contract the published tests do not state.",
        """
def test_body_rows_take_the_shades_in_turn() -> None:
    assert stripe(["a", "b"], ["pale", "dark"]) == ["pale", "dark"]


def test_a_heading_does_not_consume_a_shade() -> None:
    assert stripe(["#totals", "a"], ["pale", "dark"]) == ["head", "pale"]


def test_the_shades_start_again_once_exhausted() -> None:
    assert stripe(["a", "b", "c"], ["pale", "dark"]) == ["pale", "dark", "pale"]
""",
        imports="from stripe_rows import stripe\n",
    ),
)


_G005 = D2TaskSpec(
    template_id="d7_transform.retitle_duplicates",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-retitle-duplicates",
    module="retitle_duplicates",
    module_doc="Giving repeated titles a number so a listing reads unambiguously.",
    issue=(
        "retitle() is documented to number repeats of the same title, comparing titles without "
        "regard to case. Callers report that a title repeated in a different case is left "
        "unnumbered, and that the numbering runs on across unrelated titles so the second title "
        "to repeat starts at three."
    ),
    expected=(
        "retitle(titles) returns the titles in order with the first appearance of each left as "
        "it is and every later appearance suffixed ' (2)', ' (3)' and so on. Titles that differ "
        "only in case are the same title, and the numbering restarts for each distinct title."
    ),
    baseline_reason=(
        "it keys the tally by the title exactly as written, so a change of case looks like a new "
        "title, and it counts every retitling with one running total instead of one per title"
    ),
    edge_cases=(
        "titles differing only in case are the same title",
        "the numbering restarts for each distinct title",
    ),
    baseline="""def retitle(titles):
    \"\"\"Number the repeats among `titles`.\"\"\"
    seen = set()
    used = 1
    out = []
    for title in titles:
        if title in seen:
            used += 1
            out.append(title + " (" + str(used) + ")")
        else:
            seen.add(title)
            out.append(title)
    return out""",
    variant_one="""def retitle(titles):
    \"\"\"Number the repeats among `titles`.\"\"\"
    counts = {}
    out = []
    for title in titles:
        key = title.lower()
        counts[key] = counts.get(key, 0) + 1
        if counts[key] == 1:
            out.append(title)
        else:
            out.append(title + " (" + str(counts[key]) + ")")
    return out""",
    variant_two="""def retitle(titles):
    \"\"\"Number the repeats among `titles`.\"\"\"
    out = []
    for position, title in enumerate(titles):
        earlier = 0
        for previous in titles[:position]:
            if previous.lower() == title.lower():
                earlier += 1
        if earlier:
            out.append(title + " (" + str(earlier + 1) + ")")
        else:
            out.append(title)
    return out""",
    variant_three="""def retitle(titles):
    \"\"\"Number the repeats among `titles`.\"\"\"
    seen = set()
    used = 1
    out = []
    for title in titles:
        key = title.lower()
        if key in seen:
            used += 1
            out.append(title + " (" + str(used) + ")")
        else:
            seen.add(key)
            out.append(title)
    return out""",
    variant_four="""def retitle(titles):
    \"\"\"Number the repeats among `titles`.\"\"\"
    counts = {}
    out = []
    for title in titles:
        counts[title] = counts.get(title, 0) + 1
        if counts[title] == 1:
            out.append(title)
        else:
            out.append(title + " (" + str(counts[title]) + ")")
    return out""",
    visible_test=_test_module(
        "retitle_duplicates",
        "Published contract for numbering repeated titles.",
        """
def test_a_repeat_takes_the_second_number() -> None:
    assert retitle(["Notes", "Notes"]) == ["Notes", "Notes (2)"]


def test_distinct_titles_are_left_alone() -> None:
    assert retitle(["Notes", "Plan"]) == ["Notes", "Plan"]
""",
        imports="from retitle_duplicates import retitle\n",
    ),
    hidden_test=_test_module(
        "retitle_duplicates",
        "The part of the contract the published tests do not state.",
        """
def test_a_repeat_takes_the_second_number() -> None:
    assert retitle(["Notes", "Notes"]) == ["Notes", "Notes (2)"]


def test_a_change_of_case_is_the_same_title() -> None:
    assert retitle(["Notes", "notes"]) == ["Notes", "notes (2)"]


def test_the_numbering_restarts_for_each_title() -> None:
    assert retitle(["Notes", "Notes", "Plan", "Plan"]) == [
        "Notes",
        "Notes (2)",
        "Plan",
        "Plan (2)",
    ]
""",
        imports="from retitle_duplicates import retitle\n",
    ),
)

# ------------------------------------------------------------------ error handling

_G006 = D2TaskSpec(
    template_id="d7_error.error_context",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-error-context",
    module="error_context",
    module_doc="Describing a failure in the words of the step that hit it.",
    issue=(
        "describe() is documented to name the kind of failure when the failure carries no "
        "message of its own, and to follow the chain to whatever caused it. Callers report "
        "log lines ending in a bare colon, and causes that never appear at all."
    ),
    expected=(
        "describe(error, context) returns 'context: message', where message is the error's own "
        "text or, when that text is empty, the name of the error's kind. When the error was "
        "raised from a cause, ' <- ' and the cause's message, under the same empty-text rule, "
        "are appended."
    ),
    baseline_reason=(
        "it interpolates the error's text without asking whether there is any, and it never "
        "looks at the cause the error was raised from"
    ),
    edge_cases=(
        "an error with no text is described by the name of its kind",
        "the cause an error was raised from is appended",
    ),
    baseline="""def describe(error, context):
    \"\"\"Describe `error` under `context`.\"\"\"
    return context + ": " + str(error)""",
    variant_one="""def describe(error, context):
    \"\"\"Describe `error` under `context`.\"\"\"
    message = str(error) or type(error).__name__
    cause = error.__cause__
    if cause is not None:
        message = message + " <- " + (str(cause) or type(cause).__name__)
    return context + ": " + message""",
    variant_two="""def describe(error, context):
    \"\"\"Describe `error` under `context`.\"\"\"
    parts = []
    current = error
    while current is not None:
        text = str(current)
        if not text:
            text = type(current).__name__
        parts.append(text)
        current = current.__cause__
    return context + ": " + " <- ".join(parts)""",
    variant_three="""def describe(error, context):
    \"\"\"Describe `error` under `context`.\"\"\"
    message = str(error)
    if not message:
        message = type(error).__name__
    return context + ": " + message""",
    variant_four="""def describe(error, context):
    \"\"\"Describe `error` under `context`.\"\"\"
    message = str(error)
    cause = error.__cause__
    if cause is not None:
        message = message + " <- " + str(cause)
    return context + ": " + message""",
    visible_test=_test_module(
        "error_context",
        "Published contract for describing a failure.",
        """
def test_the_context_and_the_message_are_joined() -> None:
    assert describe(ValueError("bad row"), "import") == "import: bad row"


def test_a_plain_failure_needs_no_chain() -> None:
    assert describe(RuntimeError("stalled"), "run") == "run: stalled"
""",
        imports="from error_context import describe\n",
    ),
    hidden_test=_test_module(
        "error_context",
        "The part of the contract the published tests do not state.",
        """
def _raised_from_a_cause():
    try:
        try:
            raise RuntimeError("disk full")
        except RuntimeError as cause:
            raise ValueError("bad row") from cause
    except ValueError as error:
        return error


def test_the_context_and_the_message_are_joined() -> None:
    assert describe(ValueError("bad row"), "import") == "import: bad row"


def test_an_error_with_no_text_is_named_by_its_kind() -> None:
    assert describe(ValueError(), "import") == "import: ValueError"


def test_the_cause_is_appended() -> None:
    assert describe(_raised_from_a_cause(), "import") == "import: bad row <- disk full"
""",
        imports="from error_context import describe\n",
    ),
)

# ------------------------------------------------------------------ numeric logic

_G007 = D2TaskSpec(
    template_id="d7_numeric.scale_to_peak",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-scale-to-peak",
    module="scale_to_peak",
    module_doc="Bringing a series up to a chosen peak without changing its shape.",
    issue=(
        "scale() is documented to leave an all-zero series alone and to refuse a negative "
        "ceiling. Callers report a division-by-zero crash on a series that is entirely zero, "
        "and a negative ceiling silently turning the whole series upside down."
    ),
    expected=(
        "scale(values, ceiling) multiplies every value by the one factor that brings the largest "
        "of them to `ceiling`. A series whose largest value is zero is returned unchanged, and a "
        "ceiling below zero raises ValueError. The series is never empty."
    ),
    baseline_reason=(
        "it divides by the largest value without checking that it is not zero, and it accepts "
        "any ceiling it is given"
    ),
    edge_cases=(
        "an all-zero series is returned unchanged",
        "a ceiling below zero raises ValueError",
    ),
    baseline="""def scale(values, ceiling):
    \"\"\"Scale `values` so the largest reaches `ceiling`.\"\"\"
    peak = max(values)
    factor = ceiling / peak
    return [value * factor for value in values]""",
    variant_one="""def scale(values, ceiling):
    \"\"\"Scale `values` so the largest reaches `ceiling`.\"\"\"
    if ceiling < 0:
        raise ValueError("a ceiling below zero cannot be reached by scaling")
    peak = max(values)
    if peak == 0:
        return list(values)
    factor = ceiling / peak
    return [value * factor for value in values]""",
    variant_two="""def scale(values, ceiling):
    \"\"\"Scale `values` so the largest reaches `ceiling`.\"\"\"
    if ceiling < 0:
        raise ValueError("a ceiling below zero cannot be reached by scaling")
    peak = max(values)
    scaled = []
    for value in values:
        if peak:
            scaled.append(value * ceiling / peak)
        else:
            scaled.append(value)
    return scaled""",
    variant_three="""def scale(values, ceiling):
    \"\"\"Scale `values` so the largest reaches `ceiling`.\"\"\"
    peak = max(values)
    if peak == 0:
        return list(values)
    factor = ceiling / peak
    return [value * factor for value in values]""",
    variant_four="""def scale(values, ceiling):
    \"\"\"Scale `values` so the largest reaches `ceiling`.\"\"\"
    if ceiling < 0:
        raise ValueError("a ceiling below zero cannot be reached by scaling")
    peak = max(values)
    factor = ceiling / peak
    return [value * factor for value in values]""",
    visible_test=_test_module(
        "scale_to_peak",
        "Published contract for scaling a series to a peak.",
        """
def test_the_largest_value_reaches_the_ceiling() -> None:
    assert scale([1, 2, 4], 8) == [2, 4, 8]


def test_a_series_already_at_the_ceiling_is_unchanged() -> None:
    assert scale([5], 5) == [5]
""",
        imports="from scale_to_peak import scale\n",
    ),
    hidden_test=_test_module(
        "scale_to_peak",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_largest_value_reaches_the_ceiling() -> None:
    assert scale([1, 2, 4], 8) == [2, 4, 8]


def test_an_all_zero_series_is_returned_unchanged() -> None:
    assert scale([0, 0], 5) == [0, 0]


def test_a_ceiling_below_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        scale([1, 2], -3)
""",
        imports="from scale_to_peak import scale\n",
    ),
)

_G008 = D2TaskSpec(
    template_id="d7_numeric.pace_per_unit",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-pace-per-unit",
    module="pace_per_unit",
    module_doc="Turning a finishing time into a pace per unit of distance.",
    issue=(
        "pace() is documented to report whole seconds, rounding a half upwards, and to report "
        "nothing at all for a distance of zero. Callers report a crash on a zero distance and a "
        "pace that is always a second fast when the division does not come out even."
    ),
    expected=(
        "pace(seconds, distance) returns the seconds per unit of distance as a whole number, "
        "rounding to the nearest with a half going up. A distance of zero returns None."
    ),
    baseline_reason=(
        "it divides without checking the distance, and it converts the result with a truncation "
        "that always rounds towards zero"
    ),
    edge_cases=(
        "a distance of zero returns None",
        "a half second rounds upwards",
    ),
    baseline="""def pace(seconds, distance):
    \"\"\"Return the whole seconds per unit of distance.\"\"\"
    return int(seconds / distance)""",
    variant_one="""def pace(seconds, distance):
    \"\"\"Return the whole seconds per unit of distance.\"\"\"
    if distance == 0:
        return None
    return int(seconds / distance + 0.5)""",
    variant_two="""def pace(seconds, distance):
    \"\"\"Return the whole seconds per unit of distance.\"\"\"
    if not distance:
        return None
    whole = seconds // distance
    remainder = seconds - whole * distance
    if remainder * 2 >= distance:
        whole += 1
    return int(whole)""",
    variant_three="""def pace(seconds, distance):
    \"\"\"Return the whole seconds per unit of distance.\"\"\"
    if distance == 0:
        return None
    return int(seconds / distance)""",
    variant_four="""def pace(seconds, distance):
    \"\"\"Return the whole seconds per unit of distance.\"\"\"
    return int(seconds / distance + 0.5)""",
    visible_test=_test_module(
        "pace_per_unit",
        "Published contract for reporting a pace.",
        """
def test_an_even_division_is_the_pace() -> None:
    assert pace(600, 5) == 120


def test_a_single_unit_is_the_whole_time() -> None:
    assert pace(93, 1) == 93
""",
        imports="from pace_per_unit import pace\n",
    ),
    hidden_test=_test_module(
        "pace_per_unit",
        "The part of the contract the published tests do not state.",
        """
def test_an_even_division_is_the_pace() -> None:
    assert pace(600, 5) == 120


def test_a_distance_of_zero_has_no_pace() -> None:
    assert pace(600, 0) is None


def test_a_half_second_rounds_upwards() -> None:
    assert pace(11, 2) == 6
""",
        imports="from pace_per_unit import pace\n",
    ),
)

# ------------------------------------------------------------------ parsing and validation

_G009 = D2TaskSpec(
    template_id="d7_parsing.seat_code",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-seat-code",
    module="seat_code",
    module_doc="Reading a seat code into the row and the seat within it.",
    issue=(
        "parse_seat() is documented to report the seat letter in upper case and to refuse a "
        "code that does not end in a letter. Callers report lower-case codes coming back "
        "unchanged, so the same seat compares unequal to itself, and codes like '12' parsing "
        "happily into row 1 seat '2'."
    ),
    expected=(
        "parse_seat(code) returns (row, letter) for a code of digits followed by one letter: "
        "the row as an integer and the letter in upper case. A code whose last character is not "
        "a letter raises ValueError."
    ),
    baseline_reason=(
        "it passes the last character through as written, and it never checks that the last "
        "character is a letter before treating everything before it as the row"
    ),
    edge_cases=(
        "the seat letter comes back in upper case",
        "a code not ending in a letter raises ValueError",
    ),
    baseline="""def parse_seat(code):
    \"\"\"Split a seat code into its row and its letter.\"\"\"
    return int(code[:-1]), code[-1]""",
    variant_one="""def parse_seat(code):
    \"\"\"Split a seat code into its row and its letter.\"\"\"
    letter = code[-1:]
    if not letter.isalpha():
        raise ValueError("a seat code ends in a letter")
    return int(code[:-1]), letter.upper()""",
    variant_two="""def parse_seat(code):
    \"\"\"Split a seat code into its row and its letter.\"\"\"
    digits = ""
    letter = ""
    for character in code:
        if character.isdigit() and not letter:
            digits += character
        else:
            letter += character
    if len(letter) != 1 or not letter.isalpha():
        raise ValueError("a seat code ends in a letter")
    return int(digits), letter.upper()""",
    variant_three="""def parse_seat(code):
    \"\"\"Split a seat code into its row and its letter.\"\"\"
    return int(code[:-1]), code[-1].upper()""",
    variant_four="""def parse_seat(code):
    \"\"\"Split a seat code into its row and its letter.\"\"\"
    letter = code[-1:]
    if not letter.isalpha():
        raise ValueError("a seat code ends in a letter")
    return int(code[:-1]), letter""",
    visible_test=_test_module(
        "seat_code",
        "Published contract for reading a seat code.",
        """
def test_a_code_splits_into_the_row_and_the_letter() -> None:
    assert parse_seat("12B") == (12, "B")


def test_a_single_digit_row_reads_the_same_way() -> None:
    assert parse_seat("7C") == (7, "C")
""",
        imports="from seat_code import parse_seat\n",
    ),
    hidden_test=_test_module(
        "seat_code",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_code_splits_into_the_row_and_the_letter() -> None:
    assert parse_seat("12B") == (12, "B")


def test_the_letter_comes_back_in_upper_case() -> None:
    assert parse_seat("12b") == (12, "B")


def test_a_code_without_a_letter_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_seat("12")
""",
        imports="from seat_code import parse_seat\n",
    ),
)

# ------------------------------------------------------------------ state and idempotency

_G010 = D2TaskSpec(
    template_id="d7_state.standby_promotion",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-standby-promotion",
    module="standby_promotion",
    module_doc="Promoting a standby when the node in charge drops out.",
    issue=(
        "promote() is documented to promote a standby only when the node that failed was the "
        "one in charge, and to promote exactly one. Callers report a standby taking charge "
        "after an unrelated node failed, and two standbys both believing they are in charge."
    ),
    expected=(
        "promote(nodes, failed) returns the (name, role) pairs in order with the failed node's "
        "role set to 'failed'. When the failed node held the role 'primary', the first standby "
        "in order becomes 'primary' and every other role is unchanged; when it did not, no "
        "promotion happens at all."
    ),
    baseline_reason=(
        "it promotes a standby whoever failed, and it promotes every standby it passes rather "
        "than the first one"
    ),
    edge_cases=(
        "a failure that is not the primary promotes nobody",
        "only the first standby is promoted",
    ),
    baseline="""def promote(nodes, failed):
    \"\"\"Promote a standby when the node in charge drops out.\"\"\"
    promoted = []
    for name, role in nodes:
        if name == failed:
            promoted.append((name, "failed"))
        elif role == "standby":
            promoted.append((name, "primary"))
        else:
            promoted.append((name, role))
    return promoted""",
    variant_one="""def promote(nodes, failed):
    \"\"\"Promote a standby when the node in charge drops out.\"\"\"
    lost_the_primary = False
    for name, role in nodes:
        if name == failed and role == "primary":
            lost_the_primary = True
    promoted = []
    taken = False
    for name, role in nodes:
        if name == failed:
            promoted.append((name, "failed"))
        elif lost_the_primary and role == "standby" and not taken:
            promoted.append((name, "primary"))
            taken = True
        else:
            promoted.append((name, role))
    return promoted""",
    variant_two="""def promote(nodes, failed):
    \"\"\"Promote a standby when the node in charge drops out.\"\"\"
    roles = dict(nodes)
    successor = None
    if roles.get(failed) == "primary":
        for name, role in nodes:
            if role == "standby" and successor is None:
                successor = name
    out = []
    for name, role in nodes:
        if name == failed:
            out.append((name, "failed"))
        elif name == successor:
            out.append((name, "primary"))
        else:
            out.append((name, role))
    return out""",
    variant_three="""def promote(nodes, failed):
    \"\"\"Promote a standby when the node in charge drops out.\"\"\"
    lost_the_primary = False
    for name, role in nodes:
        if name == failed and role == "primary":
            lost_the_primary = True
    promoted = []
    for name, role in nodes:
        if name == failed:
            promoted.append((name, "failed"))
        elif lost_the_primary and role == "standby":
            promoted.append((name, "primary"))
        else:
            promoted.append((name, role))
    return promoted""",
    variant_four="""def promote(nodes, failed):
    \"\"\"Promote a standby when the node in charge drops out.\"\"\"
    promoted = []
    taken = False
    for name, role in nodes:
        if name == failed:
            promoted.append((name, "failed"))
        elif role == "standby" and not taken:
            promoted.append((name, "primary"))
            taken = True
        else:
            promoted.append((name, role))
    return promoted""",
    visible_test=_test_module(
        "standby_promotion",
        "Published contract for promoting a standby.",
        """
def test_the_first_standby_takes_over_from_a_failed_primary() -> None:
    assert promote([("a", "primary"), ("b", "standby")], "a") == [
        ("a", "failed"),
        ("b", "primary"),
    ]


def test_a_lone_primary_that_fails_leaves_nobody_in_charge() -> None:
    assert promote([("a", "primary")], "a") == [("a", "failed")]
""",
        imports="from standby_promotion import promote\n",
    ),
    hidden_test=_test_module(
        "standby_promotion",
        "The part of the contract the published tests do not state.",
        """
def test_the_first_standby_takes_over_from_a_failed_primary() -> None:
    assert promote([("a", "primary"), ("b", "standby")], "a") == [
        ("a", "failed"),
        ("b", "primary"),
    ]


def test_a_failure_that_is_not_the_primary_promotes_nobody() -> None:
    assert promote([("a", "primary"), ("b", "standby"), ("c", "standby")], "b") == [
        ("a", "primary"),
        ("b", "failed"),
        ("c", "standby"),
    ]


def test_only_the_first_standby_is_promoted() -> None:
    assert promote([("a", "primary"), ("b", "standby"), ("c", "standby")], "a") == [
        ("a", "failed"),
        ("b", "primary"),
        ("c", "standby"),
    ]
""",
        imports="from standby_promotion import promote\n",
    ),
)

D7_CERTIFICATION_SPECS: tuple[D2TaskSpec, ...] = (
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

__all__ = ["D7_CERTIFICATION_SPECS", "D2TaskSpec", "RealityTaskFamily", "_test_module"]
