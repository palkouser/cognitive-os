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


_G011 = D2TaskSpec(
    template_id="d7_boundary.queue_positions",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-queue-positions",
    module="queue_positions",
    module_doc="Telling callers where they stand in a queue.",
    issue=(
        "positions() is documented to report the earliest place an id holds and to report "
        "nothing for an id that is not queued at all. Callers report that somebody who joined "
        "twice is told the later place, and that asking about an id that has already been "
        "served fails outright instead of answering."
    ),
    expected=(
        "positions(queue, wanted) returns one place per wanted id, in the order asked, counting "
        "from one. An id appearing more than once takes its earliest place, and an id that is "
        "not in the queue gets None."
    ),
    baseline_reason=(
        "it overwrites each id's place as it walks the queue, so the last one wins, and it "
        "looks the place up in a way that has no answer for an id that never appeared"
    ),
    edge_cases=(
        "an id queued twice takes its earliest place",
        "an id that is not queued gets None",
    ),
    baseline="""def positions(queue, wanted):
    \"\"\"Report where each wanted id stands in `queue`.\"\"\"
    places = {}
    for index, item in enumerate(queue):
        places[item] = index + 1
    return [places[item] for item in wanted]""",
    variant_one="""def positions(queue, wanted):
    \"\"\"Report where each wanted id stands in `queue`.\"\"\"
    places = {}
    for index, item in enumerate(queue):
        places.setdefault(item, index + 1)
    return [places.get(item) for item in wanted]""",
    variant_two="""def positions(queue, wanted):
    \"\"\"Report where each wanted id stands in `queue`.\"\"\"
    out = []
    for item in wanted:
        place = None
        for index, queued in enumerate(queue):
            if queued == item:
                place = index + 1
                break
        out.append(place)
    return out""",
    variant_three="""def positions(queue, wanted):
    \"\"\"Report where each wanted id stands in `queue`.\"\"\"
    places = {}
    for index, item in enumerate(queue):
        places.setdefault(item, index + 1)
    return [places[item] for item in wanted]""",
    variant_four="""def positions(queue, wanted):
    \"\"\"Report where each wanted id stands in `queue`.\"\"\"
    places = {}
    for index, item in enumerate(queue):
        places[item] = index + 1
    return [places.get(item) for item in wanted]""",
    visible_test=_test_module(
        "queue_positions",
        "Published contract for reporting a place in the queue.",
        """
def test_a_place_counts_from_one() -> None:
    assert positions(["ann", "bo"], ["bo"]) == [2]


def test_the_head_of_the_queue_is_first() -> None:
    assert positions(["ann"], ["ann"]) == [1]
""",
        imports="from queue_positions import positions\n",
    ),
    hidden_test=_test_module(
        "queue_positions",
        "The part of the contract the published tests do not state.",
        """
def test_a_place_counts_from_one() -> None:
    assert positions(["ann", "bo"], ["bo"]) == [2]


def test_an_id_queued_twice_takes_its_earliest_place() -> None:
    assert positions(["ann", "bo", "ann"], ["ann"]) == [1]


def test_an_id_that_is_not_queued_has_no_place() -> None:
    assert positions(["ann"], ["zoe"]) == [None]
""",
        imports="from queue_positions import positions\n",
    ),
)

_G012 = D2TaskSpec(
    template_id="d7_transform.mask_fields",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-mask-fields",
    module="mask_fields",
    module_doc="Hiding named fields before a record is shown to anybody.",
    issue=(
        "mask() is documented to hide exactly the fields it is given. Callers report that a "
        "field whose name merely begins with a named one is hidden as well, so 'token_kind' "
        "disappears along with 'token', and that a record which never carried the field comes "
        "back carrying it with a masked value."
    ),
    expected=(
        "mask(rows, fields) returns the rows in order, each with the value of every named field "
        "replaced by '***'. Field names match exactly, never as a prefix, and a row that does "
        "not carry a named field is returned unchanged."
    ),
    baseline_reason=(
        "it compares field names with a prefix test, and it fills in every named field it did "
        "not find rather than leaving the row alone"
    ),
    edge_cases=(
        "a field whose name merely begins with a named one is left alone",
        "a row without the named field is returned unchanged",
    ),
    baseline="""def mask(rows, fields):
    \"\"\"Hide the named fields in every row.\"\"\"
    hidden = []
    for row in rows:
        shown = dict(row)
        for name in list(shown):
            for field in fields:
                if name.startswith(field):
                    shown[name] = "***"
        for field in fields:
            shown.setdefault(field, "***")
        hidden.append(shown)
    return hidden""",
    variant_one="""def mask(rows, fields):
    \"\"\"Hide the named fields in every row.\"\"\"
    hidden = []
    for row in rows:
        shown = dict(row)
        for field in fields:
            if field in shown:
                shown[field] = "***"
        hidden.append(shown)
    return hidden""",
    variant_two="""def mask(rows, fields):
    \"\"\"Hide the named fields in every row.\"\"\"
    wanted = set(fields)
    return [
        {name: ("***" if name in wanted else value) for name, value in row.items()}
        for row in rows
    ]""",
    variant_three="""def mask(rows, fields):
    \"\"\"Hide the named fields in every row.\"\"\"
    hidden = []
    for row in rows:
        shown = dict(row)
        for name in list(shown):
            for field in fields:
                if name == field:
                    shown[name] = "***"
        for field in fields:
            shown.setdefault(field, "***")
        hidden.append(shown)
    return hidden""",
    variant_four="""def mask(rows, fields):
    \"\"\"Hide the named fields in every row.\"\"\"
    hidden = []
    for row in rows:
        shown = dict(row)
        for name in list(shown):
            for field in fields:
                if name.startswith(field):
                    shown[name] = "***"
        hidden.append(shown)
    return hidden""",
    visible_test=_test_module(
        "mask_fields",
        "Published contract for hiding named fields.",
        """
def test_a_named_field_is_hidden() -> None:
    assert mask([{"token": "abc"}], ["token"]) == [{"token": "***"}]


def test_naming_no_fields_changes_nothing() -> None:
    assert mask([{"name": "ann"}], []) == [{"name": "ann"}]
""",
        imports="from mask_fields import mask\n",
    ),
    hidden_test=_test_module(
        "mask_fields",
        "The part of the contract the published tests do not state.",
        """
def test_a_named_field_is_hidden() -> None:
    assert mask([{"token": "abc"}], ["token"]) == [{"token": "***"}]


def test_a_field_that_merely_begins_with_a_named_one_is_left_alone() -> None:
    assert mask([{"token_kind": "bearer"}], ["token"]) == [{"token_kind": "bearer"}]


def test_a_row_without_the_field_is_returned_unchanged() -> None:
    assert mask([{"name": "ann"}], ["token"]) == [{"name": "ann"}]
""",
        imports="from mask_fields import mask\n",
    ),
)

_G013 = D2TaskSpec(
    template_id="d7_error.dead_letter",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-dead-letter",
    module="dead_letter",
    module_doc="Setting aside the messages that have been tried too often.",
    issue=(
        "route() is documented to set a message aside once its attempts have reached the "
        "limit. Callers report that a message sitting exactly on the limit is retried forever, "
        "and that a message which has never been attempted fails the routing outright instead "
        "of being treated as fresh."
    ),
    expected=(
        "route(messages, limit) takes (id, attempts) pairs and returns (live, dead): an id "
        "whose attempts have reached the limit is dead, and one below it is live, both in "
        "arrival order. Attempts recorded as None count as none at all."
    ),
    baseline_reason=(
        "it compares the attempts with a strict test, so the limit itself is never reached, and "
        "it compares without asking whether any attempts were recorded"
    ),
    edge_cases=(
        "a message whose attempts have reached the limit is set aside",
        "attempts recorded as None count as none at all",
    ),
    baseline="""def route(messages, limit):
    \"\"\"Split messages into the live ones and the ones tried too often.\"\"\"
    live = []
    dead = []
    for identifier, attempts in messages:
        if attempts > limit:
            dead.append(identifier)
        else:
            live.append(identifier)
    return live, dead""",
    variant_one="""def route(messages, limit):
    \"\"\"Split messages into the live ones and the ones tried too often.\"\"\"
    live = []
    dead = []
    for identifier, attempts in messages:
        tried = attempts or 0
        if tried >= limit:
            dead.append(identifier)
        else:
            live.append(identifier)
    return live, dead""",
    variant_two="""def route(messages, limit):
    \"\"\"Split messages into the live ones and the ones tried too often.\"\"\"
    counted = [
        (identifier, 0 if attempts is None else attempts) for identifier, attempts in messages
    ]
    live = [identifier for identifier, tried in counted if tried < limit]
    dead = [identifier for identifier, tried in counted if tried >= limit]
    return live, dead""",
    variant_three="""def route(messages, limit):
    \"\"\"Split messages into the live ones and the ones tried too often.\"\"\"
    live = []
    dead = []
    for identifier, attempts in messages:
        if attempts >= limit:
            dead.append(identifier)
        else:
            live.append(identifier)
    return live, dead""",
    variant_four="""def route(messages, limit):
    \"\"\"Split messages into the live ones and the ones tried too often.\"\"\"
    live = []
    dead = []
    for identifier, attempts in messages:
        tried = attempts or 0
        if tried > limit:
            dead.append(identifier)
        else:
            live.append(identifier)
    return live, dead""",
    visible_test=_test_module(
        "dead_letter",
        "Published contract for setting messages aside.",
        """
def test_a_fresh_message_stays_live() -> None:
    assert route([("a", 0)], 3) == (["a"], [])


def test_a_message_well_past_the_limit_is_set_aside() -> None:
    assert route([("b", 5)], 3) == ([], ["b"])
""",
        imports="from dead_letter import route\n",
    ),
    hidden_test=_test_module(
        "dead_letter",
        "The part of the contract the published tests do not state.",
        """
def test_a_fresh_message_stays_live() -> None:
    assert route([("a", 0)], 3) == (["a"], [])


def test_a_message_that_has_reached_the_limit_is_set_aside() -> None:
    assert route([("a", 3)], 3) == ([], ["a"])


def test_attempts_recorded_as_none_count_as_none_at_all() -> None:
    assert route([("a", None)], 3) == (["a"], [])
""",
        imports="from dead_letter import route\n",
    ),
)

_G014 = D2TaskSpec(
    template_id="d7_error.escalate_unacked",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-escalate-unacked",
    module="escalate_unacked",
    module_doc="Escalating the alerts nobody has picked up.",
    issue=(
        "escalate() is documented to escalate only what nobody has acknowledged, and to name "
        "each alert once. Callers report being paged about alerts they had already taken, and "
        "receiving the same alert twice when it was reported more than once while waiting."
    ),
    expected=(
        "escalate(alerts, patience) takes (id, waited, acknowledged) triples and returns the "
        "ids to escalate, in the order they first appear: those that have waited at least "
        "`patience` and have not been acknowledged, each named once."
    ),
    baseline_reason=(
        "it never looks at whether the alert was acknowledged, and it appends without asking "
        "whether that alert is already on the list"
    ),
    edge_cases=(
        "an acknowledged alert is never escalated",
        "an alert reported twice is escalated once",
    ),
    baseline="""def escalate(alerts, patience):
    \"\"\"Return the alerts that should be escalated.\"\"\"
    out = []
    for identifier, waited, acknowledged in alerts:
        if waited < patience:
            continue
        out.append(identifier)
    return out""",
    variant_one="""def escalate(alerts, patience):
    \"\"\"Return the alerts that should be escalated.\"\"\"
    out = []
    for identifier, waited, acknowledged in alerts:
        if waited < patience or acknowledged:
            continue
        if identifier not in out:
            out.append(identifier)
    return out""",
    variant_two="""def escalate(alerts, patience):
    \"\"\"Return the alerts that should be escalated.\"\"\"
    waiting = [
        identifier
        for identifier, waited, acknowledged in alerts
        if waited >= patience and not acknowledged
    ]
    seen = set()
    out = []
    for identifier in waiting:
        if identifier not in seen:
            seen.add(identifier)
            out.append(identifier)
    return out""",
    variant_three="""def escalate(alerts, patience):
    \"\"\"Return the alerts that should be escalated.\"\"\"
    out = []
    for identifier, waited, acknowledged in alerts:
        if waited < patience or acknowledged:
            continue
        out.append(identifier)
    return out""",
    variant_four="""def escalate(alerts, patience):
    \"\"\"Return the alerts that should be escalated.\"\"\"
    out = []
    for identifier, waited, acknowledged in alerts:
        if waited < patience:
            continue
        if identifier not in out:
            out.append(identifier)
    return out""",
    visible_test=_test_module(
        "escalate_unacked",
        "Published contract for escalating alerts.",
        """
def test_a_long_wait_is_escalated() -> None:
    assert escalate([("a", 5, False)], 3) == ["a"]


def test_a_short_wait_is_left_alone() -> None:
    assert escalate([("b", 1, False)], 3) == []
""",
        imports="from escalate_unacked import escalate\n",
    ),
    hidden_test=_test_module(
        "escalate_unacked",
        "The part of the contract the published tests do not state.",
        """
def test_a_long_wait_is_escalated() -> None:
    assert escalate([("a", 5, False)], 3) == ["a"]


def test_an_acknowledged_alert_is_never_escalated() -> None:
    assert escalate([("a", 5, True)], 3) == []


def test_an_alert_reported_twice_is_escalated_once() -> None:
    assert escalate([("a", 5, False), ("a", 6, False)], 3) == ["a"]
""",
        imports="from escalate_unacked import escalate\n",
    ),
)

_G015 = D2TaskSpec(
    template_id="d7_numeric.overtime_pay",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-overtime-pay",
    module="overtime_pay",
    module_doc="Paying the hours beyond a threshold at the higher rate.",
    issue=(
        "pay() is documented to pay the plain rate up to the threshold and half as much again "
        "beyond it. Callers report short weeks being underpaid, as though the unworked hours "
        "were deducted, and a negative number of hours producing a negative wage instead of "
        "being refused."
    ),
    expected=(
        "pay(hours, rate, threshold) returns the wage rounded to two decimals: every hour up to "
        "the threshold at `rate`, and every hour beyond it at one and a half times `rate`. "
        "Hours below zero raise ValueError."
    ),
    baseline_reason=(
        "it adds the overtime supplement without flooring the overtime at zero, so a short "
        "week subtracts one instead, and it never checks that the hours are not negative"
    ),
    edge_cases=(
        "hours below the threshold are paid at the plain rate",
        "hours below zero raise ValueError",
    ),
    baseline="""def pay(hours, rate, threshold):
    \"\"\"Return the wage for `hours` worked.\"\"\"
    overtime = hours - threshold
    return round(hours * rate + overtime * rate * 0.5, 2)""",
    variant_one="""def pay(hours, rate, threshold):
    \"\"\"Return the wage for `hours` worked.\"\"\"
    if hours < 0:
        raise ValueError("hours worked cannot be negative")
    overtime = max(hours - threshold, 0)
    return round(hours * rate + overtime * rate * 0.5, 2)""",
    variant_two="""def pay(hours, rate, threshold):
    \"\"\"Return the wage for `hours` worked.\"\"\"
    if hours < 0:
        raise ValueError("hours worked cannot be negative")
    if hours <= threshold:
        return round(hours * rate, 2)
    plain = threshold * rate
    extra = (hours - threshold) * rate * 1.5
    return round(plain + extra, 2)""",
    variant_three="""def pay(hours, rate, threshold):
    \"\"\"Return the wage for `hours` worked.\"\"\"
    overtime = max(hours - threshold, 0)
    return round(hours * rate + overtime * rate * 0.5, 2)""",
    variant_four="""def pay(hours, rate, threshold):
    \"\"\"Return the wage for `hours` worked.\"\"\"
    if hours < 0:
        raise ValueError("hours worked cannot be negative")
    overtime = hours - threshold
    return round(hours * rate + overtime * rate * 0.5, 2)""",
    visible_test=_test_module(
        "overtime_pay",
        "Published contract for paying a week's hours.",
        """
def test_a_full_week_is_paid_at_the_plain_rate() -> None:
    assert pay(40, 10, 40) == 400.0


def test_hours_beyond_the_threshold_are_paid_higher() -> None:
    assert pay(45, 10, 40) == 475.0
""",
        imports="from overtime_pay import pay\n",
    ),
    hidden_test=_test_module(
        "overtime_pay",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_hours_beyond_the_threshold_are_paid_higher() -> None:
    assert pay(45, 10, 40) == 475.0


def test_a_short_week_is_paid_at_the_plain_rate() -> None:
    assert pay(30, 10, 40) == 300.0


def test_negative_hours_are_refused() -> None:
    with pytest.raises(ValueError):
        pay(-1, 10, 40)
""",
        imports="from overtime_pay import pay\n",
    ),
)

_G016 = D2TaskSpec(
    template_id="d7_parsing.hashtag_list",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-hashtag-list",
    module="hashtag_list",
    module_doc="Reading the tags out of a message body.",
    issue=(
        "tags() is documented to report each distinct tag once, folded to lower case, without "
        "whatever punctuation followed it. Callers report the same tag listed twice when it was "
        "written in different cases, and tags coming back with a trailing comma or full stop "
        "attached."
    ),
    expected=(
        "tags(text) returns the tags of a message, each without its leading '#', folded to "
        "lower case, in order of first appearance and without repeats. Punctuation following a "
        "tag is not part of it, and a bare '#' is not a tag."
    ),
    baseline_reason=(
        "it takes the word after the hash exactly as written, so case distinguishes two "
        "spellings of one tag, and it never trims the punctuation that follows"
    ),
    edge_cases=(
        "tags differing only in case are one tag",
        "punctuation following a tag is not part of it",
    ),
    baseline="""def tags(text):
    \"\"\"Return the tags of a message.\"\"\"
    found = []
    for word in text.split():
        if word.startswith("#") and len(word) > 1:
            tag = word[1:]
            if tag not in found:
                found.append(tag)
    return found""",
    variant_one="""def tags(text):
    \"\"\"Return the tags of a message.\"\"\"
    found = []
    for word in text.split():
        if word.startswith("#") and len(word) > 1:
            tag = word[1:].strip(".,;:!?").lower()
            if tag and tag not in found:
                found.append(tag)
    return found""",
    variant_two="""def tags(text):
    \"\"\"Return the tags of a message.\"\"\"
    found = []
    seen = set()
    for word in text.split():
        if not word.startswith("#"):
            continue
        letters = ""
        for character in word[1:]:
            if character.isalnum() or character == "_":
                letters += character
            else:
                break
        tag = letters.lower()
        if tag and tag not in seen:
            seen.add(tag)
            found.append(tag)
    return found""",
    variant_three="""def tags(text):
    \"\"\"Return the tags of a message.\"\"\"
    found = []
    for word in text.split():
        if word.startswith("#") and len(word) > 1:
            tag = word[1:].lower()
            if tag not in found:
                found.append(tag)
    return found""",
    variant_four="""def tags(text):
    \"\"\"Return the tags of a message.\"\"\"
    found = []
    for word in text.split():
        if word.startswith("#") and len(word) > 1:
            tag = word[1:].strip(".,;:!?")
            if tag and tag not in found:
                found.append(tag)
    return found""",
    visible_test=_test_module(
        "hashtag_list",
        "Published contract for reading tags out of a message.",
        """
def test_a_tag_loses_its_hash() -> None:
    assert tags("hello #run today") == ["run"]


def test_a_message_without_tags_has_none() -> None:
    assert tags("no tags here") == []
""",
        imports="from hashtag_list import tags\n",
    ),
    hidden_test=_test_module(
        "hashtag_list",
        "The part of the contract the published tests do not state.",
        """
def test_a_tag_loses_its_hash() -> None:
    assert tags("hello #run today") == ["run"]


def test_two_spellings_of_one_tag_are_one_tag() -> None:
    assert tags("#Run and #run") == ["run"]


def test_punctuation_after_a_tag_is_not_part_of_it() -> None:
    assert tags("#run, then #swim.") == ["run", "swim"]
""",
        imports="from hashtag_list import tags\n",
    ),
)

_G017 = D2TaskSpec(
    template_id="d7_state.maintenance_window",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-maintenance-window",
    module="maintenance_window",
    module_doc="Opening and closing a maintenance window without losing when it started.",
    issue=(
        "window() is documented to leave an open window alone when it is opened again, and to "
        "refuse a close that matches no open window. Callers report the start time being reset "
        "by a repeated open, so the window looks shorter than it was, and stray closes "
        "recording a window that began at nothing."
    ),
    expected=(
        "window(state, event, at) returns the state after the event. 'enter' records the start "
        "unless one is already recorded, in which case the state is unchanged; 'leave' appends "
        "(start, at) to the history and clears the start. A 'leave' with no window open raises "
        "ValueError."
    ),
    baseline_reason=(
        "it writes the start time on every open, and it closes whatever it finds without "
        "checking that a window was open"
    ),
    edge_cases=(
        "opening an already-open window keeps the original start",
        "closing with no window open raises ValueError",
    ),
    baseline="""def window(state, event, at):
    \"\"\"Apply a maintenance-window event to `state`.\"\"\"
    updated = dict(state)
    history = list(updated.get("history", []))
    if event == "enter":
        updated["started_at"] = at
        updated["history"] = history
        return updated
    history.append((updated.get("started_at"), at))
    updated["started_at"] = None
    updated["history"] = history
    return updated""",
    variant_one="""def window(state, event, at):
    \"\"\"Apply a maintenance-window event to `state`.\"\"\"
    updated = dict(state)
    history = list(updated.get("history", []))
    started = updated.get("started_at")
    if event == "enter":
        if started is None:
            updated["started_at"] = at
        updated["history"] = history
        return updated
    if started is None:
        raise ValueError("no maintenance window is open")
    history.append((started, at))
    updated["started_at"] = None
    updated["history"] = history
    return updated""",
    variant_two="""def window(state, event, at):
    \"\"\"Apply a maintenance-window event to `state`.\"\"\"
    started = state.get("started_at")
    history = list(state.get("history", []))
    if event == "enter":
        opened = at if started is None else started
        return {"started_at": opened, "history": history}
    if not started:
        raise ValueError("no maintenance window is open")
    return {"started_at": None, "history": [*history, (started, at)]}""",
    variant_three="""def window(state, event, at):
    \"\"\"Apply a maintenance-window event to `state`.\"\"\"
    updated = dict(state)
    history = list(updated.get("history", []))
    started = updated.get("started_at")
    if event == "enter":
        if started is None:
            updated["started_at"] = at
        updated["history"] = history
        return updated
    history.append((started, at))
    updated["started_at"] = None
    updated["history"] = history
    return updated""",
    variant_four="""def window(state, event, at):
    \"\"\"Apply a maintenance-window event to `state`.\"\"\"
    updated = dict(state)
    history = list(updated.get("history", []))
    started = updated.get("started_at")
    if event == "enter":
        updated["started_at"] = at
        updated["history"] = history
        return updated
    if started is None:
        raise ValueError("no maintenance window is open")
    history.append((started, at))
    updated["started_at"] = None
    updated["history"] = history
    return updated""",
    visible_test=_test_module(
        "maintenance_window",
        "Published contract for opening and closing a maintenance window.",
        """
def test_opening_records_the_start() -> None:
    assert window({}, "enter", 1) == {"started_at": 1, "history": []}


def test_closing_records_the_window() -> None:
    opened = window({}, "enter", 1)
    assert window(opened, "leave", 4) == {"started_at": None, "history": [(1, 4)]}
""",
        imports="from maintenance_window import window\n",
    ),
    hidden_test=_test_module(
        "maintenance_window",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_opening_records_the_start() -> None:
    assert window({}, "enter", 1) == {"started_at": 1, "history": []}


def test_opening_an_open_window_keeps_the_original_start() -> None:
    opened = window({}, "enter", 1)
    assert window(opened, "enter", 5)["started_at"] == 1


def test_closing_with_nothing_open_is_refused() -> None:
    with pytest.raises(ValueError):
        window({}, "leave", 5)
""",
        imports="from maintenance_window import window\n",
    ),
)


_G018 = D2TaskSpec(
    template_id="d7_numeric.receipt_total",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-receipt-total",
    module="receipt_total",
    module_doc="Totalling a receipt so the tax lands on the whole of it.",
    issue=(
        "total() is documented to add the lines up first and tax the sum. Callers report totals "
        "a penny or two out against the same receipt totalled by hand, and a line entered with "
        "a negative quantity quietly reducing the bill instead of being refused."
    ),
    expected=(
        "total(lines, tax_rate) takes (quantity, price) pairs and returns the amount due, "
        "rounded to two decimals once at the end: the sum of quantity times price, plus that "
        "sum times the rate. A negative quantity raises ValueError."
    ),
    baseline_reason=(
        "it rounds each line as it goes, so the roundings accumulate, and it adds every line up "
        "without checking the quantity"
    ),
    edge_cases=(
        "the rounding happens once, on the total, not on each line",
        "a negative quantity raises ValueError",
    ),
    baseline="""def total(lines, tax_rate):
    \"\"\"Return the amount due for a receipt.\"\"\"
    running = 0.0
    for quantity, price in lines:
        running += round(quantity * price, 2)
    return round(running + round(running * tax_rate, 2), 2)""",
    variant_one="""def total(lines, tax_rate):
    \"\"\"Return the amount due for a receipt.\"\"\"
    running = 0.0
    for quantity, price in lines:
        if quantity < 0:
            raise ValueError("a receipt line cannot carry a negative quantity")
        running += quantity * price
    return round(running * (1 + tax_rate), 2)""",
    variant_two="""def total(lines, tax_rate):
    \"\"\"Return the amount due for a receipt.\"\"\"
    quantities = [quantity for quantity, _ in lines]
    if any(quantity < 0 for quantity in quantities):
        raise ValueError("a receipt line cannot carry a negative quantity")
    subtotal = sum(quantity * price for quantity, price in lines)
    return round(subtotal + subtotal * tax_rate, 2)""",
    variant_three="""def total(lines, tax_rate):
    \"\"\"Return the amount due for a receipt.\"\"\"
    running = 0.0
    for quantity, price in lines:
        running += quantity * price
    return round(running * (1 + tax_rate), 2)""",
    variant_four="""def total(lines, tax_rate):
    \"\"\"Return the amount due for a receipt.\"\"\"
    running = 0.0
    for quantity, price in lines:
        if quantity < 0:
            raise ValueError("a receipt line cannot carry a negative quantity")
        running += round(quantity * price, 2)
    return round(running + round(running * tax_rate, 2), 2)""",
    visible_test=_test_module(
        "receipt_total",
        "Published contract for totalling a receipt.",
        """
def test_one_round_line_totals_exactly() -> None:
    assert total([(2, 10.0)], 0.1) == 22.0


def test_an_empty_receipt_is_free() -> None:
    assert total([], 0.2) == 0.0
""",
        imports="from receipt_total import total\n",
    ),
    hidden_test=_test_module(
        "receipt_total",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_one_round_line_totals_exactly() -> None:
    assert total([(2, 10.0)], 0.1) == 22.0


def test_the_rounding_happens_once_on_the_total() -> None:
    assert total([(1, 0.005), (1, 0.005)], 0.0) == 0.01


def test_a_negative_quantity_is_refused() -> None:
    with pytest.raises(ValueError):
        total([(-1, 10.0)], 0.1)
""",
        imports="from receipt_total import total\n",
    ),
)

_G019 = D2TaskSpec(
    template_id="d7_numeric.net_from_gross",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-net-from-gross",
    module="net_from_gross",
    module_doc="Taking the tax back out of a price that already includes it.",
    issue=(
        "net_of() is documented to divide the tax back out of an inclusive price. Callers "
        "report it subtracting the rate from the gross instead, which is only right when the "
        "rate is zero, and a rate of exactly minus one hundred percent producing a division by "
        "zero rather than a refusal."
    ),
    expected=(
        "net_of(gross, rate) returns the amount before tax, rounded to two decimals: the gross "
        "divided by one plus the rate. A rate of -1 or below raises ValueError, because no "
        "inclusive price can be recovered from it."
    ),
    baseline_reason=(
        "it multiplies the gross by one minus the rate, which is a different quantity, and it "
        "never checks the rate before using it"
    ),
    edge_cases=(
        "the tax is divided out rather than subtracted",
        "a rate of -1 or below raises ValueError",
    ),
    baseline="""def net_of(gross, rate):
    \"\"\"Return the amount before tax.\"\"\"
    return round(gross * (1 - rate), 2)""",
    variant_one="""def net_of(gross, rate):
    \"\"\"Return the amount before tax.\"\"\"
    if rate <= -1:
        raise ValueError("no inclusive price can be recovered at this rate")
    return round(gross / (1 + rate), 2)""",
    variant_two="""def net_of(gross, rate):
    \"\"\"Return the amount before tax.\"\"\"
    divisor = 1 + rate
    if divisor <= 0:
        raise ValueError("no inclusive price can be recovered at this rate")
    net = gross / divisor
    return round(net, 2)""",
    variant_three="""def net_of(gross, rate):
    \"\"\"Return the amount before tax.\"\"\"
    return round(gross / (1 + rate), 2)""",
    variant_four="""def net_of(gross, rate):
    \"\"\"Return the amount before tax.\"\"\"
    if rate <= -1:
        raise ValueError("no inclusive price can be recovered at this rate")
    return round(gross * (1 - rate), 2)""",
    visible_test=_test_module(
        "net_from_gross",
        "Published contract for removing tax from an inclusive price.",
        """
def test_a_rate_of_nothing_leaves_the_price_alone() -> None:
    assert net_of(100.0, 0.0) == 100.0


def test_the_net_is_below_the_gross() -> None:
    assert net_of(110.0, 0.1) < 110.0
""",
        imports="from net_from_gross import net_of\n",
    ),
    hidden_test=_test_module(
        "net_from_gross",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_rate_of_nothing_leaves_the_price_alone() -> None:
    assert net_of(100.0, 0.0) == 100.0


def test_the_tax_is_divided_out_rather_than_subtracted() -> None:
    assert net_of(110.0, 0.1) == 100.0


def test_a_rate_that_cannot_be_undone_is_refused() -> None:
    with pytest.raises(ValueError):
        net_of(100.0, -1)
""",
        imports="from net_from_gross import net_of\n",
    ),
)

_G020 = D2TaskSpec(
    template_id="d7_state.refund_once",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-refund-once",
    module="refund_once",
    module_doc="Refunding an order without refunding it twice.",
    issue=(
        "refund() is documented to pay a refund once per order and to refuse more than the "
        "order was worth. Callers report a retried request paying out a second time, and a "
        "refund larger than the order itself being accepted because only the running total was "
        "checked."
    ),
    expected=(
        "refund(state, order, amount) returns the state with the refund recorded under the "
        "order. An order already refunded is returned unchanged, whatever amount is asked for, "
        "and an amount above *that order's* value raises ValueError -- refunds paid on other "
        "orders do not reduce what this one may be refunded. `state` maps an order to its value "
        "and carries the refunds already paid."
    ),
    baseline_reason=(
        "it records the refund without asking whether one is already recorded, and it compares "
        "the amount against what is left across every order rather than against this order's "
        "own value, so an unrelated refund shrinks this one"
    ),
    edge_cases=(
        "an order already refunded is returned unchanged",
        "a refund paid on another order does not shrink this one",
    ),
    baseline="""def refund(state, order, amount):
    \"\"\"Record a refund against `order`.\"\"\"
    values = state["values"]
    refunds = dict(state["refunds"])
    if amount > values[order] - sum(refunds.values()):
        raise ValueError("the refund is larger than what is left")
    refunds[order] = amount
    return {"values": values, "refunds": refunds}""",
    variant_one="""def refund(state, order, amount):
    \"\"\"Record a refund against `order`.\"\"\"
    values = state["values"]
    refunds = dict(state["refunds"])
    if order in refunds:
        return {"values": values, "refunds": refunds}
    if amount > values[order]:
        raise ValueError("the refund is larger than the order")
    refunds[order] = amount
    return {"values": values, "refunds": refunds}""",
    variant_two="""def refund(state, order, amount):
    \"\"\"Record a refund against `order`.\"\"\"
    values = state["values"]
    refunds = state["refunds"]
    already = refunds.get(order)
    if already is not None:
        return {"values": values, "refunds": dict(refunds)}
    if values[order] < amount:
        raise ValueError("the refund is larger than the order")
    return {"values": values, "refunds": {**refunds, order: amount}}""",
    variant_three="""def refund(state, order, amount):
    \"\"\"Record a refund against `order`.\"\"\"
    values = state["values"]
    refunds = dict(state["refunds"])
    if order in refunds:
        return {"values": values, "refunds": refunds}
    if amount > values[order] - sum(refunds.values()):
        raise ValueError("the refund is larger than what is left")
    refunds[order] = amount
    return {"values": values, "refunds": refunds}""",
    variant_four="""def refund(state, order, amount):
    \"\"\"Record a refund against `order`.\"\"\"
    values = state["values"]
    refunds = dict(state["refunds"])
    if amount > values[order]:
        raise ValueError("the refund is larger than the order")
    refunds[order] = amount
    return {"values": values, "refunds": refunds}""",
    visible_test=_test_module(
        "refund_once",
        "Published contract for refunding an order.",
        """
def test_a_refund_is_recorded() -> None:
    state = {"values": {"a": 10}, "refunds": {}}
    assert refund(state, "a", 4) == {"values": {"a": 10}, "refunds": {"a": 4}}


def test_a_refund_larger_than_the_order_is_refused() -> None:
    state = {"values": {"a": 10}, "refunds": {}}
    with pytest.raises(ValueError):
        refund(state, "a", 11)
""",
        imports="import pytest\n\nfrom refund_once import refund\n",
    ),
    hidden_test=_test_module(
        "refund_once",
        "The part of the contract the published tests do not state.",
        """
def test_a_refund_is_recorded() -> None:
    state = {"values": {"a": 10}, "refunds": {}}
    assert refund(state, "a", 4) == {"values": {"a": 10}, "refunds": {"a": 4}}


def test_an_order_already_refunded_is_returned_unchanged() -> None:
    state = {"values": {"a": 10}, "refunds": {"a": 4}}
    assert refund(state, "a", 9)["refunds"] == {"a": 4}


def test_another_orders_refund_does_not_shrink_this_one() -> None:
    state = {"values": {"a": 10, "b": 8}, "refunds": {"b": 6}}
    assert refund(state, "a", 9)["refunds"] == {"b": 6, "a": 9}
""",
        imports="from refund_once import refund\n",
    ),
)

_G021 = D2TaskSpec(
    template_id="d7_parsing.plate_format",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-plate-format",
    module="plate_format",
    module_doc="Reading a vehicle plate into its parts, however it was typed.",
    issue=(
        "split_plate() is documented to accept a plate however it was spaced and to insist on "
        "the shape itself. Callers report plates typed with a space in the middle being "
        "rejected, and plates whose letter block is the wrong length being accepted as long as "
        "the total length came out right."
    ),
    expected=(
        "split_plate(text) returns (letters, digits) for a plate of exactly three letters "
        "followed by exactly three digits. Spaces anywhere are ignored and the letters come "
        "back in upper case. Anything else raises ValueError."
    ),
    baseline_reason=(
        "it splits at a fixed offset without removing the spaces first, and it checks only the "
        "overall length rather than the two blocks"
    ),
    edge_cases=(
        "spaces anywhere in the plate are ignored",
        "a plate whose blocks are the wrong shape raises ValueError",
    ),
    baseline="""def split_plate(text):
    \"\"\"Split a plate into its letters and its digits.\"\"\"
    if len(text) != 6:
        raise ValueError("a plate is three letters and three digits")
    return text[:3].upper(), text[3:]""",
    variant_one="""def split_plate(text):
    \"\"\"Split a plate into its letters and its digits.\"\"\"
    packed = text.replace(" ", "")
    letters = packed[:3]
    digits = packed[3:]
    if len(packed) != 6 or not letters.isalpha() or not digits.isdigit():
        raise ValueError("a plate is three letters and three digits")
    return letters.upper(), digits""",
    variant_two="""def split_plate(text):
    \"\"\"Split a plate into its letters and its digits.\"\"\"
    packed = "".join(character for character in text if character != " ")
    letters = "".join(character for character in packed if character.isalpha())
    digits = "".join(character for character in packed if character.isdigit())
    if len(letters) != 3 or len(digits) != 3 or letters + digits != packed:
        raise ValueError("a plate is three letters and three digits")
    return letters.upper(), digits""",
    variant_three="""def split_plate(text):
    \"\"\"Split a plate into its letters and its digits.\"\"\"
    packed = text.replace(" ", "")
    if len(packed) != 6:
        raise ValueError("a plate is three letters and three digits")
    return packed[:3].upper(), packed[3:]""",
    variant_four="""def split_plate(text):
    \"\"\"Split a plate into its letters and its digits.\"\"\"
    letters = text[:3]
    digits = text[3:]
    if len(text) != 6 or not letters.isalpha() or not digits.isdigit():
        raise ValueError("a plate is three letters and three digits")
    return letters.upper(), digits""",
    visible_test=_test_module(
        "plate_format",
        "Published contract for reading a vehicle plate.",
        """
def test_a_plain_plate_splits_into_its_blocks() -> None:
    assert split_plate("ABC123") == ("ABC", "123")


def test_the_letters_come_back_in_upper_case() -> None:
    assert split_plate("abc123") == ("ABC", "123")
""",
        imports="from plate_format import split_plate\n",
    ),
    hidden_test=_test_module(
        "plate_format",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_plain_plate_splits_into_its_blocks() -> None:
    assert split_plate("ABC123") == ("ABC", "123")


def test_spaces_in_the_plate_are_ignored() -> None:
    assert split_plate("ABC 123") == ("ABC", "123")


def test_blocks_of_the_wrong_shape_are_refused() -> None:
    with pytest.raises(ValueError):
        split_plate("AB1123")
""",
        imports="from plate_format import split_plate\n",
    ),
)

_G022 = D2TaskSpec(
    template_id="d7_transform.milestone_progress",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-milestone-progress",
    module="milestone_progress",
    module_doc="Reporting how far a plan has got, milestone by milestone.",
    issue=(
        "progress() is documented to weigh each milestone by its size and to report a plan with "
        "nothing in it as nothing done. Callers report a plan of one large and one tiny "
        "milestone reading fifty percent when only the tiny one is finished, and an empty plan "
        "failing outright instead of reporting zero."
    ),
    expected=(
        "progress(milestones) takes (size, done) pairs and returns the share of the total size "
        "that is finished, as a percentage rounded to one decimal. A plan with no milestones, "
        "or one whose sizes add to zero, reports 0.0."
    ),
    baseline_reason=(
        "it counts milestones rather than weighing them by size, and it divides by the count "
        "without checking that there is one"
    ),
    edge_cases=(
        "milestones are weighed by their size, not counted",
        "a plan with nothing in it reports zero",
    ),
    baseline="""def progress(milestones):
    \"\"\"Return the percentage of the plan that is finished.\"\"\"
    done = sum(1 for _size, finished in milestones if finished)
    return round(100.0 * done / len(milestones), 1)""",
    variant_one="""def progress(milestones):
    \"\"\"Return the percentage of the plan that is finished.\"\"\"
    total = sum(size for size, _finished in milestones)
    if total == 0:
        return 0.0
    done = sum(size for size, finished in milestones if finished)
    return round(100.0 * done / total, 1)""",
    variant_two="""def progress(milestones):
    \"\"\"Return the percentage of the plan that is finished.\"\"\"
    total = 0
    done = 0
    for size, finished in milestones:
        total += size
        if finished:
            done += size
    if not total:
        return 0.0
    return round(100.0 * done / total, 1)""",
    variant_three="""def progress(milestones):
    \"\"\"Return the percentage of the plan that is finished.\"\"\"
    total = sum(size for size, _finished in milestones)
    done = sum(size for size, finished in milestones if finished)
    return round(100.0 * done / total, 1)""",
    variant_four="""def progress(milestones):
    \"\"\"Return the percentage of the plan that is finished.\"\"\"
    if not milestones:
        return 0.0
    done = sum(1 for _size, finished in milestones if finished)
    return round(100.0 * done / len(milestones), 1)""",
    visible_test=_test_module(
        "milestone_progress",
        "Published contract for reporting progress through a plan.",
        """
def test_equal_milestones_split_the_plan_evenly() -> None:
    assert progress([(1, True), (1, False)]) == 50.0


def test_a_finished_plan_is_complete() -> None:
    assert progress([(3, True)]) == 100.0
""",
        imports="from milestone_progress import progress\n",
    ),
    hidden_test=_test_module(
        "milestone_progress",
        "The part of the contract the published tests do not state.",
        """
def test_equal_milestones_split_the_plan_evenly() -> None:
    assert progress([(1, True), (1, False)]) == 50.0


def test_milestones_are_weighed_by_their_size() -> None:
    assert progress([(9, False), (1, True)]) == 10.0


def test_a_plan_with_nothing_in_it_reports_zero() -> None:
    assert progress([]) == 0.0
""",
        imports="from milestone_progress import progress\n",
    ),
)

_G023 = D2TaskSpec(
    template_id="d7_boundary.rota_swap",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-rota-swap",
    module="rota_swap",
    module_doc="Swapping two shifts on a rota without disturbing the rest of it.",
    issue=(
        "swap() is documented to exchange the two named shifts and to leave a rota that does "
        "not hold both of them exactly as it was. Callers report the whole rota coming back "
        "reordered when only two entries should have moved, and a swap naming a shift nobody "
        "is on silently moving somebody else."
    ),
    expected=(
        "swap(rota, first, second) returns the rota with the entries at the two named shifts "
        "exchanged, every other entry in its place. A rota that does not hold both shifts is "
        "returned unchanged, and swapping a shift with itself changes nothing."
    ),
    baseline_reason=(
        "it rebuilds the rota in sorted order rather than in place, and it looks the shifts up "
        "without checking that both are on the rota"
    ),
    edge_cases=(
        "every other entry keeps its place",
        "a rota missing one of the shifts is returned unchanged",
    ),
    baseline="""def swap(rota, first, second):
    \"\"\"Exchange the entries at two shifts.\"\"\"
    entries = dict(rota)
    held = entries.get(first)
    entries[first] = entries.get(second)
    entries[second] = held
    return dict(sorted(entries.items()))""",
    variant_one="""def swap(rota, first, second):
    \"\"\"Exchange the entries at two shifts.\"\"\"
    if first not in rota or second not in rota:
        return dict(rota)
    entries = dict(rota)
    entries[first], entries[second] = entries[second], entries[first]
    return entries""",
    variant_two="""def swap(rota, first, second):
    \"\"\"Exchange the entries at two shifts.\"\"\"
    if not (first in rota and second in rota):
        return {shift: person for shift, person in rota.items()}
    swapped = {}
    for shift, person in rota.items():
        if shift == first:
            swapped[shift] = rota[second]
        elif shift == second:
            swapped[shift] = rota[first]
        else:
            swapped[shift] = person
    return swapped""",
    variant_three="""def swap(rota, first, second):
    \"\"\"Exchange the entries at two shifts.\"\"\"
    entries = dict(rota)
    held = entries.get(first)
    entries[first] = entries.get(second)
    entries[second] = held
    return entries""",
    variant_four="""def swap(rota, first, second):
    \"\"\"Exchange the entries at two shifts.\"\"\"
    if first not in rota or second not in rota:
        return dict(sorted(rota.items()))
    entries = dict(rota)
    entries[first], entries[second] = entries[second], entries[first]
    return dict(sorted(entries.items()))""",
    visible_test=_test_module(
        "rota_swap",
        "Published contract for swapping two shifts.",
        """
def test_two_shifts_exchange_their_people() -> None:
    assert swap({"mon": "ann", "tue": "bo"}, "mon", "tue") == {"mon": "bo", "tue": "ann"}


def test_swapping_a_shift_with_itself_changes_nothing() -> None:
    assert swap({"mon": "ann"}, "mon", "mon") == {"mon": "ann"}
""",
        imports="from rota_swap import swap\n",
    ),
    hidden_test=_test_module(
        "rota_swap",
        "The part of the contract the published tests do not state.",
        """
def test_two_shifts_exchange_their_people() -> None:
    assert swap({"mon": "ann", "tue": "bo"}, "mon", "tue") == {"mon": "bo", "tue": "ann"}


def test_every_other_entry_keeps_its_place() -> None:
    rota = {"tue": "bo", "mon": "ann", "wed": "cy"}
    assert list(swap(rota, "mon", "wed")) == ["tue", "mon", "wed"]


def test_a_rota_missing_a_shift_is_returned_unchanged() -> None:
    assert swap({"mon": "ann"}, "mon", "sun") == {"mon": "ann"}
""",
        imports="from rota_swap import swap\n",
    ),
)

_G024 = D2TaskSpec(
    template_id="d7_error.invoice_lookup",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-invoice-lookup",
    module="invoice_lookup",
    module_doc="Finding an invoice, and saying which of the two things went wrong.",
    issue=(
        "find_invoice() is documented to tell a number nobody has apart from a number that is "
        "not an invoice number at all. Callers report both arriving as the same error, so a "
        "retry cannot tell a typo from an invoice that has not been raised yet, and a badly "
        "formed number that somehow reached the ledger is handed back instead of refused."
    ),
    expected=(
        "find_invoice(invoices, number) returns the invoice recorded under the number. A number "
        "that is not well formed - anything that is not 'INV-' followed by something - raises "
        "ValueError whether or not the ledger holds it, and a well formed number the ledger "
        "does not hold raises LookupError."
    ),
    baseline_reason=(
        "it looks the number up before asking whether the number is well formed, and it reports "
        "a number nobody has with the error reserved for a malformed one"
    ),
    edge_cases=(
        "a malformed number recorded in the ledger is refused rather than returned",
        "a well formed number nobody has raises LookupError",
    ),
    baseline="""def find_invoice(invoices, number):
    \"\"\"Return the invoice recorded under a number.\"\"\"
    if number in invoices:
        return invoices[number]
    if not number.startswith("INV-") or not number[4:]:
        raise ValueError("malformed invoice number: " + number)
    raise ValueError("no invoice on file: " + number)""",
    variant_one="""def find_invoice(invoices, number):
    \"\"\"Return the invoice recorded under a number.\"\"\"
    if not number.startswith("INV-") or not number[4:]:
        raise ValueError("malformed invoice number: " + number)
    if number not in invoices:
        raise LookupError("no invoice on file: " + number)
    return invoices[number]""",
    variant_two="""def find_invoice(invoices, number):
    \"\"\"Return the invoice recorded under a number.\"\"\"
    prefix, _, tail = number.partition("-")
    if prefix != "INV" or not tail:
        raise ValueError("malformed invoice number: " + number)
    try:
        return invoices[number]
    except KeyError as missing:
        raise LookupError("no invoice on file: " + number) from missing""",
    variant_three="""def find_invoice(invoices, number):
    \"\"\"Return the invoice recorded under a number.\"\"\"
    if not number.startswith("INV-") or not number[4:]:
        raise ValueError("malformed invoice number: " + number)
    if number in invoices:
        return invoices[number]
    raise ValueError("no invoice on file: " + number)""",
    variant_four="""def find_invoice(invoices, number):
    \"\"\"Return the invoice recorded under a number.\"\"\"
    if number in invoices:
        return invoices[number]
    if not number.startswith("INV-") or not number[4:]:
        raise ValueError("malformed invoice number: " + number)
    raise LookupError("no invoice on file: " + number)""",
    visible_test=_test_module(
        "invoice_lookup",
        "Published contract for looking an invoice up.",
        """
import pytest


def test_a_recorded_invoice_comes_back() -> None:
    assert find_invoice({"INV-1": {"total": 10}}, "INV-1") == {"total": 10}


def test_a_number_that_is_not_an_invoice_number_is_refused() -> None:
    with pytest.raises(ValueError):
        find_invoice({"INV-1": {"total": 10}}, "2024-11")
""",
        imports="from invoice_lookup import find_invoice\n",
    ),
    hidden_test=_test_module(
        "invoice_lookup",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_recorded_invoice_comes_back() -> None:
    assert find_invoice({"INV-1": {"total": 10}}, "INV-1") == {"total": 10}


def test_a_malformed_number_in_the_ledger_is_still_refused() -> None:
    with pytest.raises(ValueError):
        find_invoice({"2024-11": {"total": 10}}, "2024-11")


def test_a_well_formed_number_nobody_has_is_a_lookup_failure() -> None:
    with pytest.raises(LookupError):
        find_invoice({"INV-1": {"total": 10}}, "INV-2")
""",
        imports="from invoice_lookup import find_invoice\n",
    ),
)

_G025 = D2TaskSpec(
    template_id="d7_error.password_policy",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-password-policy",
    module="password_policy",
    module_doc="Reporting everything wrong with a password rather than the first thing.",
    issue=(
        "check() is documented to report every rule a password breaks, so somebody fixing one "
        "does not come straight back with the next. Callers report being told one thing at a "
        "time, and a password of exactly the stated minimum length being called too short."
    ),
    expected=(
        "check(password) returns the names of every rule the password breaks, in the order "
        "too_short, no_digit, no_upper, and an empty result when it breaks none. A password of "
        "exactly eight characters is long enough."
    ),
    baseline_reason=(
        "it returns at the first rule that fails instead of collecting them, and its length "
        "test refuses the minimum length itself"
    ),
    edge_cases=(
        "every broken rule is reported, not only the first",
        "a password of exactly the minimum length is long enough",
    ),
    baseline="""def check(password):
    \"\"\"Report the rules a password breaks.\"\"\"
    if len(password) <= 8:
        return ("too_short",)
    if not any(character.isdigit() for character in password):
        return ("no_digit",)
    if not any(character.isupper() for character in password):
        return ("no_upper",)
    return ()""",
    variant_one="""def check(password):
    \"\"\"Report the rules a password breaks.\"\"\"
    broken = []
    if len(password) < 8:
        broken.append("too_short")
    if not any(character.isdigit() for character in password):
        broken.append("no_digit")
    if not any(character.isupper() for character in password):
        broken.append("no_upper")
    return tuple(broken)""",
    variant_two="""def check(password):
    \"\"\"Report the rules a password breaks.\"\"\"
    rules = (
        ("too_short", lambda text: len(text) >= 8),
        ("no_digit", lambda text: any(character.isdigit() for character in text)),
        ("no_upper", lambda text: any(character.isupper() for character in text)),
    )
    return tuple(name for name, holds in rules if not holds(password))""",
    variant_three="""def check(password):
    \"\"\"Report the rules a password breaks.\"\"\"
    broken = []
    if len(password) <= 8:
        broken.append("too_short")
    if not any(character.isdigit() for character in password):
        broken.append("no_digit")
    if not any(character.isupper() for character in password):
        broken.append("no_upper")
    return tuple(broken)""",
    variant_four="""def check(password):
    \"\"\"Report the rules a password breaks.\"\"\"
    if len(password) < 8:
        return ("too_short",)
    if not any(character.isdigit() for character in password):
        return ("no_digit",)
    if not any(character.isupper() for character in password):
        return ("no_upper",)
    return ()""",
    visible_test=_test_module(
        "password_policy",
        "Published contract for the password rules.",
        """
def test_a_password_missing_a_digit_is_reported() -> None:
    assert check("longenoughA") == ("no_digit",)


def test_a_password_breaking_nothing_reports_nothing() -> None:
    assert check("longenoughA1") == ()
""",
        imports="from password_policy import check\n",
    ),
    hidden_test=_test_module(
        "password_policy",
        "The part of the contract the published tests do not state.",
        """
def test_a_password_missing_a_digit_is_reported() -> None:
    assert check("longenoughA") == ("no_digit",)


def test_every_broken_rule_is_reported() -> None:
    assert check("abcdefghi") == ("no_digit", "no_upper")


def test_exactly_the_minimum_length_is_long_enough() -> None:
    assert check("Abcdefg1") == ()
""",
        imports="from password_policy import check\n",
    ),
)

# ------------------------------------------------------------------ data transformation

_G026 = D2TaskSpec(
    template_id="d7_transform.enrich_rows",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-enrich-rows",
    module="enrich_rows",
    module_doc="Attaching a label to every row, including the rows nobody labelled.",
    issue=(
        "enrich() is documented to return one row out for every row in, in the order they "
        "arrived. Callers report rows disappearing from the result when the label table does "
        "not mention them, and the rows that survive coming back in the table's order rather "
        "than their own."
    ),
    expected=(
        "enrich(rows, labels) returns one new row per row, in the order the rows arrived, each "
        "carrying its own fields together with a 'label' taken from the table under the row's "
        "'id'. A row the table does not mention is labelled 'unknown'."
    ),
    baseline_reason=(
        "it walks the label table and looks for rows inside it, so a row nobody labelled is "
        "never reached at all and the rows that are reached come back in the table's order"
    ),
    edge_cases=(
        "a row the table does not mention is labelled unknown",
        "the rows come back in their own order",
    ),
    baseline="""def enrich(rows, labels):
    \"\"\"Attach a label to every row.\"\"\"
    enriched = []
    for identifier, label in labels.items():
        for row in rows:
            if row["id"] == identifier:
                enriched.append({**row, "label": label})
    return enriched""",
    variant_one="""def enrich(rows, labels):
    \"\"\"Attach a label to every row.\"\"\"
    return [{**row, "label": labels.get(row["id"], "unknown")} for row in rows]""",
    variant_two="""def enrich(rows, labels):
    \"\"\"Attach a label to every row.\"\"\"
    enriched = []
    for row in rows:
        labelled = dict(row)
        if row["id"] in labels:
            labelled["label"] = labels[row["id"]]
        else:
            labelled["label"] = "unknown"
        enriched.append(labelled)
    return enriched""",
    variant_three="""def enrich(rows, labels):
    \"\"\"Attach a label to every row.\"\"\"
    enriched = []
    for row in rows:
        for identifier, label in labels.items():
            if row["id"] == identifier:
                enriched.append({**row, "label": label})
    return enriched""",
    variant_four="""def enrich(rows, labels):
    \"\"\"Attach a label to every row.\"\"\"
    enriched = []
    for identifier, label in labels.items():
        for row in rows:
            if row["id"] == identifier:
                enriched.append({**row, "label": label})
    for row in rows:
        if row["id"] not in labels:
            enriched.append({**row, "label": "unknown"})
    return enriched""",
    visible_test=_test_module(
        "enrich_rows",
        "Published contract for labelling rows.",
        """
def test_every_labelled_row_carries_its_label() -> None:
    assert enrich([{"id": 1}, {"id": 2}], {1: "a", 2: "b"}) == [
        {"id": 1, "label": "a"},
        {"id": 2, "label": "b"},
    ]


def test_a_rows_own_fields_are_kept() -> None:
    assert enrich([{"id": 7, "name": "x"}], {7: "seven"}) == [
        {"id": 7, "name": "x", "label": "seven"}
    ]
""",
        imports="from enrich_rows import enrich\n",
    ),
    hidden_test=_test_module(
        "enrich_rows",
        "The part of the contract the published tests do not state.",
        """
def test_every_labelled_row_carries_its_label() -> None:
    assert enrich([{"id": 1}, {"id": 2}], {1: "a", 2: "b"}) == [
        {"id": 1, "label": "a"},
        {"id": 2, "label": "b"},
    ]


def test_a_row_the_table_does_not_mention_is_labelled_unknown() -> None:
    assert enrich([{"id": 1}, {"id": 9}], {1: "a"}) == [
        {"id": 1, "label": "a"},
        {"id": 9, "label": "unknown"},
    ]


def test_the_rows_come_back_in_their_own_order() -> None:
    assert enrich([{"id": 2}, {"id": 1}], {1: "a", 2: "b"}) == [
        {"id": 2, "label": "b"},
        {"id": 1, "label": "a"},
    ]
""",
        imports="from enrich_rows import enrich\n",
    ),
)

_G027 = D2TaskSpec(
    template_id="d7_transform.apply_defaults",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-apply-defaults",
    module="apply_defaults",
    module_doc="Filling in the settings nobody chose, and only those.",
    issue=(
        "apply() is documented to fill in what the settings do not say and to leave what they "
        "do say alone. Callers report a setting deliberately turned off coming back on, and the "
        "mapping they passed in coming back changed under them."
    ),
    expected=(
        "apply(settings, defaults) returns the settings with every default the settings do not "
        "hold filled in. A setting the settings hold is kept whatever its value, including zero "
        "or an empty string, and the caller's mappings are left as they were."
    ),
    baseline_reason=(
        "it decides a setting is missing by asking whether its value is falsy, and it writes the "
        "defaults into the caller's own mapping"
    ),
    edge_cases=(
        "a setting held with a falsy value is a choice, not a gap",
        "the caller's settings are not modified",
    ),
    baseline="""def apply(settings, defaults):
    \"\"\"Fill in the settings that were not chosen.\"\"\"
    for key, value in defaults.items():
        if not settings.get(key):
            settings[key] = value
    return settings""",
    variant_one="""def apply(settings, defaults):
    \"\"\"Fill in the settings that were not chosen.\"\"\"
    filled = dict(settings)
    for key, value in defaults.items():
        if key not in filled:
            filled[key] = value
    return filled""",
    variant_two="""def apply(settings, defaults):
    \"\"\"Fill in the settings that were not chosen.\"\"\"
    filled = dict(settings)
    for key in defaults:
        filled.setdefault(key, defaults[key])
    return filled""",
    variant_three="""def apply(settings, defaults):
    \"\"\"Fill in the settings that were not chosen.\"\"\"
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = value
    return settings""",
    variant_four="""def apply(settings, defaults):
    \"\"\"Fill in the settings that were not chosen.\"\"\"
    filled = dict(settings)
    for key, value in defaults.items():
        if not filled.get(key):
            filled[key] = value
    return filled""",
    visible_test=_test_module(
        "apply_defaults",
        "Published contract for filling in defaults.",
        """
def test_a_setting_nobody_chose_is_filled_in() -> None:
    assert apply({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_a_setting_that_was_chosen_is_kept() -> None:
    assert apply({"a": 1}, {"a": 9}) == {"a": 1}
""",
        imports="from apply_defaults import apply\n",
    ),
    hidden_test=_test_module(
        "apply_defaults",
        "The part of the contract the published tests do not state.",
        """
def test_a_setting_nobody_chose_is_filled_in() -> None:
    assert apply({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_a_setting_turned_off_stays_off() -> None:
    assert apply({"retries": 0}, {"retries": 3}) == {"retries": 0}


def test_the_callers_settings_are_left_alone() -> None:
    settings = {"a": 1}
    apply(settings, {"b": 2})
    assert settings == {"a": 1}
""",
        imports="from apply_defaults import apply\n",
    ),
)

# ------------------------------------------------------------------ parsing and validation

_G028 = D2TaskSpec(
    template_id="d7_parsing.coupon_value",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-coupon-value",
    module="coupon_value",
    module_doc="Reading a coupon into what it takes off and how it takes it.",
    issue=(
        "parse_coupon() is documented to ignore the spaces people type around a coupon and to "
        "refuse a percentage larger than the whole. Callers report a coupon pasted with spaces "
        "being rejected outright, and a coupon of '120%' being accepted and then taking more "
        "off an order than the order is worth."
    ),
    expected=(
        "parse_coupon(text) returns (code, kind, amount) for a coupon written as a code, a "
        "colon and an amount. An amount ending in '%' is of kind 'percent' and any other is "
        "'fixed'. Spaces around either part are ignored, a percent above one hundred raises "
        "ValueError, and so does a text with no colon in it."
    ),
    baseline_reason=(
        "it reads the two parts exactly as they were typed, spaces and all, and it converts a "
        "percentage without ever asking how large it is"
    ),
    edge_cases=(
        "spaces around the code and the amount are ignored",
        "a percent above the whole is refused",
    ),
    baseline="""def parse_coupon(text):
    \"\"\"Read a coupon into its code, its kind and its amount.\"\"\"
    code, separator, amount = text.partition(":")
    if not separator:
        raise ValueError("not a coupon: " + text)
    if amount.endswith("%"):
        return code, "percent", int(amount[:-1])
    return code, "fixed", int(amount)""",
    variant_one="""def parse_coupon(text):
    \"\"\"Read a coupon into its code, its kind and its amount.\"\"\"
    code, separator, amount = text.partition(":")
    if not separator:
        raise ValueError("not a coupon: " + text)
    code = code.strip()
    amount = amount.strip()
    if amount.endswith("%"):
        percent = int(amount[:-1])
        if percent > 100:
            raise ValueError("percent above the whole: " + text)
        return code, "percent", percent
    return code, "fixed", int(amount)""",
    variant_two="""def parse_coupon(text):
    \"\"\"Read a coupon into its code, its kind and its amount.\"\"\"
    if ":" not in text:
        raise ValueError("not a coupon: " + text)
    head, _, tail = text.partition(":")
    amount = tail.strip()
    kind = "percent" if amount[-1:] == "%" else "fixed"
    value = int(amount.rstrip("%"))
    if kind == "percent" and value > 100:
        raise ValueError("percent above the whole: " + text)
    return head.strip(), kind, value""",
    variant_three="""def parse_coupon(text):
    \"\"\"Read a coupon into its code, its kind and its amount.\"\"\"
    code, separator, amount = text.partition(":")
    if not separator:
        raise ValueError("not a coupon: " + text)
    code = code.strip()
    amount = amount.strip()
    if amount.endswith("%"):
        return code, "percent", int(amount[:-1])
    return code, "fixed", int(amount)""",
    variant_four="""def parse_coupon(text):
    \"\"\"Read a coupon into its code, its kind and its amount.\"\"\"
    code, separator, amount = text.partition(":")
    if not separator:
        raise ValueError("not a coupon: " + text)
    if amount.endswith("%"):
        percent = int(amount[:-1])
        if percent > 100:
            raise ValueError("percent above the whole: " + text)
        return code, "percent", percent
    return code, "fixed", int(amount)""",
    visible_test=_test_module(
        "coupon_value",
        "Published contract for reading a coupon.",
        """
import pytest


def test_a_fixed_coupon_reads_as_its_amount() -> None:
    assert parse_coupon("SAVE:250") == ("SAVE", "fixed", 250)


def test_a_percentage_coupon_reads_as_a_percent() -> None:
    assert parse_coupon("SAVE:20%") == ("SAVE", "percent", 20)


def test_a_text_with_no_colon_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_coupon("SAVE20")
""",
        imports="from coupon_value import parse_coupon\n",
    ),
    hidden_test=_test_module(
        "coupon_value",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_percentage_coupon_reads_as_a_percent() -> None:
    assert parse_coupon("SAVE:20%") == ("SAVE", "percent", 20)


def test_the_spaces_people_type_are_ignored() -> None:
    assert parse_coupon(" SAVE : 20% ") == ("SAVE", "percent", 20)


def test_a_percent_above_the_whole_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_coupon("SAVE:120%")
""",
        imports="from coupon_value import parse_coupon\n",
    ),
)

_G029 = D2TaskSpec(
    template_id="d7_parsing.timezone_offset",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-timezone-offset",
    module="timezone_offset",
    module_doc="Reading a zone offset into the minutes it stands for.",
    issue=(
        "parse_offset() is documented to read an offset such as '-08:30' into signed minutes. "
        "Callers report offsets west of the meridian coming back with their minutes pointing "
        "the other way, and 'Z' being refused although it is the offset of no offset at all."
    ),
    expected=(
        "parse_offset(text) returns the offset in minutes: '+05:30' is 330, '-08:30' is -510, "
        "and 'Z' is 0. The sign applies to the whole offset, not only to its hours, and an "
        "offset whose minutes are sixty or more raises ValueError."
    ),
    baseline_reason=(
        "it applies the sign to the hours and then adds the minutes on top, so a negative "
        "offset lands short of where it should by twice its minutes, and it has no reading "
        "for 'Z' at all"
    ),
    edge_cases=(
        "a negative offset carries its sign into its minutes",
        "'Z' reads as no offset",
    ),
    baseline="""def parse_offset(text):
    \"\"\"Read a zone offset into signed minutes.\"\"\"
    sign = -1 if text[0] == "-" else 1
    hours, _, minutes = text[1:].partition(":")
    if int(minutes) >= 60:
        raise ValueError("minutes out of range: " + text)
    return sign * int(hours) * 60 + int(minutes)""",
    variant_one="""def parse_offset(text):
    \"\"\"Read a zone offset into signed minutes.\"\"\"
    if text == "Z":
        return 0
    sign = -1 if text[0] == "-" else 1
    hours, _, minutes = text[1:].partition(":")
    if int(minutes) >= 60:
        raise ValueError("minutes out of range: " + text)
    return sign * (int(hours) * 60 + int(minutes))""",
    variant_two="""def parse_offset(text):
    \"\"\"Read a zone offset into signed minutes.\"\"\"
    if text.upper() == "Z":
        return 0
    head, _, tail = text.partition(":")
    minutes = int(tail)
    if minutes >= 60:
        raise ValueError("minutes out of range: " + text)
    hours = int(head)
    total = abs(hours) * 60 + minutes
    return -total if head.startswith("-") else total""",
    variant_three="""def parse_offset(text):
    \"\"\"Read a zone offset into signed minutes.\"\"\"
    sign = -1 if text[0] == "-" else 1
    hours, _, minutes = text[1:].partition(":")
    if int(minutes) >= 60:
        raise ValueError("minutes out of range: " + text)
    return sign * (int(hours) * 60 + int(minutes))""",
    variant_four="""def parse_offset(text):
    \"\"\"Read a zone offset into signed minutes.\"\"\"
    if text == "Z":
        return 0
    sign = -1 if text[0] == "-" else 1
    hours, _, minutes = text[1:].partition(":")
    if int(minutes) >= 60:
        raise ValueError("minutes out of range: " + text)
    return sign * int(hours) * 60 + int(minutes)""",
    visible_test=_test_module(
        "timezone_offset",
        "Published contract for reading a zone offset.",
        """
import pytest


def test_an_offset_east_reads_as_minutes() -> None:
    assert parse_offset("+05:30") == 330


def test_minutes_beyond_the_hour_are_refused() -> None:
    with pytest.raises(ValueError):
        parse_offset("+05:60")
""",
        imports="from timezone_offset import parse_offset\n",
    ),
    hidden_test=_test_module(
        "timezone_offset",
        "The part of the contract the published tests do not state.",
        """
def test_an_offset_east_reads_as_minutes() -> None:
    assert parse_offset("+05:30") == 330


def test_an_offset_west_carries_its_sign_into_its_minutes() -> None:
    assert parse_offset("-08:30") == -510


def test_the_zone_of_no_offset_reads_as_zero() -> None:
    assert parse_offset("Z") == 0
""",
        imports="from timezone_offset import parse_offset\n",
    ),
)

# ------------------------------------------------------------------ state and idempotency

_G030 = D2TaskSpec(
    template_id="d7_state.seat_checkout",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-seat-checkout",
    module="seat_checkout",
    module_doc="Taking a seat, once, and refusing somebody else's.",
    issue=(
        "checkout() is documented to be safe to send twice: the same holder taking the same "
        "seat again is not an error. Callers report the retry of a request that already "
        "succeeded being refused, and a seat somebody else holds being taken from them."
    ),
    expected=(
        "checkout(seats, seat, holder) returns the seats with the seat held by the holder. The "
        "same holder taking a seat they already hold changes nothing, a seat somebody else "
        "holds raises ValueError, and the caller's mapping is left as it was."
    ),
    baseline_reason=(
        "it writes the holder in without asking who is already there, and it writes into the "
        "caller's own mapping"
    ),
    edge_cases=(
        "a seat somebody else holds is refused",
        "the caller's mapping is not modified",
    ),
    baseline="""def checkout(seats, seat, holder):
    \"\"\"Record a seat as held by a holder.\"\"\"
    seats[seat] = holder
    return seats""",
    variant_one="""def checkout(seats, seat, holder):
    \"\"\"Record a seat as held by a holder.\"\"\"
    held = seats.get(seat)
    if held is not None and held != holder:
        raise ValueError("seat already held: " + str(seat))
    taken = dict(seats)
    taken[seat] = holder
    return taken""",
    variant_two="""def checkout(seats, seat, holder):
    \"\"\"Record a seat as held by a holder.\"\"\"
    if seat in seats and seats[seat] != holder:
        raise ValueError("seat already held: " + str(seat))
    return {**seats, seat: holder}""",
    variant_three="""def checkout(seats, seat, holder):
    \"\"\"Record a seat as held by a holder.\"\"\"
    held = seats.get(seat)
    if held is not None and held != holder:
        raise ValueError("seat already held: " + str(seat))
    seats[seat] = holder
    return seats""",
    variant_four="""def checkout(seats, seat, holder):
    \"\"\"Record a seat as held by a holder.\"\"\"
    taken = {other: who for other, who in seats.items() if other != seat}
    taken[seat] = holder
    return taken""",
    visible_test=_test_module(
        "seat_checkout",
        "Published contract for taking a seat.",
        """
def test_a_free_seat_is_taken() -> None:
    assert checkout({}, "12B", "ann") == {"12B": "ann"}


def test_taking_a_seat_twice_changes_nothing() -> None:
    assert checkout({"12B": "ann"}, "12B", "ann") == {"12B": "ann"}
""",
        imports="from seat_checkout import checkout\n",
    ),
    hidden_test=_test_module(
        "seat_checkout",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_free_seat_is_taken() -> None:
    assert checkout({}, "12B", "ann") == {"12B": "ann"}


def test_a_seat_somebody_else_holds_is_refused() -> None:
    with pytest.raises(ValueError):
        checkout({"12B": "ann"}, "12B", "bo")


def test_the_callers_mapping_is_left_alone() -> None:
    seats = {"1A": "cy"}
    checkout(seats, "12B", "ann")
    assert seats == {"1A": "cy"}
""",
        imports="from seat_checkout import checkout\n",
    ),
)

_G031 = D2TaskSpec(
    template_id="d7_boundary.shortlist_ties",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-shortlist-ties",
    module="shortlist_ties",
    module_doc="Taking the top of a ranking without cutting a tie in half.",
    issue=(
        "shortlist() is documented to keep a tie whole even when that makes the list longer "
        "than the limit, because cutting between two equal scores decides by nothing. Callers "
        "report exactly that cut being made, and tied entries coming back in alphabetical order "
        "rather than the order they were submitted in."
    ),
    expected=(
        "shortlist(scored, limit) takes (name, score) pairs in any order and returns the names "
        "of the highest scores, highest first, tied names in the order they arrived. A tie "
        "straddling the cut is kept whole, so the result can be longer than the limit, and a "
        "limit of zero or less returns nothing."
    ),
    baseline_reason=(
        "it cuts the ranking at the limit whatever lies on either side of the cut, and it "
        "breaks ties by name instead of leaving them in the order they arrived"
    ),
    edge_cases=(
        "a tie straddling the cut is kept whole",
        "tied names keep the order they arrived in",
    ),
    baseline="""def shortlist(scored, limit):
    \"\"\"Return the names at the top of the ranking.\"\"\"
    ranked = sorted(scored, key=lambda entry: (-entry[1], entry[0]))
    return [name for name, _ in ranked[:limit]]""",
    variant_one="""def shortlist(scored, limit):
    \"\"\"Return the names at the top of the ranking.\"\"\"
    ranked = sorted(scored, key=lambda entry: -entry[1])
    kept = ranked[:limit]
    if kept:
        cut = kept[-1][1]
        kept = [entry for entry in ranked if entry[1] >= cut]
    return [name for name, _ in kept]""",
    variant_two="""def shortlist(scored, limit):
    \"\"\"Return the names at the top of the ranking.\"\"\"
    if limit <= 0:
        return []
    ranked = sorted(scored, key=lambda entry: -entry[1])
    scores = [score for _, score in ranked]
    cut = scores[min(limit, len(scores)) - 1]
    return [name for name, score in ranked if score >= cut]""",
    variant_three="""def shortlist(scored, limit):
    \"\"\"Return the names at the top of the ranking.\"\"\"
    ranked = sorted(scored, key=lambda entry: (-entry[1], entry[0]))
    kept = ranked[:limit]
    if kept:
        cut = kept[-1][1]
        kept = [entry for entry in ranked if entry[1] >= cut]
    return [name for name, _ in kept]""",
    variant_four="""def shortlist(scored, limit):
    \"\"\"Return the names at the top of the ranking.\"\"\"
    ranked = sorted(scored, key=lambda entry: -entry[1])
    return [name for name, _ in ranked[:limit]]""",
    visible_test=_test_module(
        "shortlist_ties",
        "Published contract for the shortlist.",
        """
def test_the_highest_scores_come_first() -> None:
    assert shortlist([("a", 5), ("b", 9), ("c", 1)], 2) == ["b", "a"]


def test_a_limit_of_nothing_shortlists_nobody() -> None:
    assert shortlist([("a", 5)], 0) == []
""",
        imports="from shortlist_ties import shortlist\n",
    ),
    hidden_test=_test_module(
        "shortlist_ties",
        "The part of the contract the published tests do not state.",
        """
def test_the_highest_scores_come_first() -> None:
    assert shortlist([("a", 5), ("b", 9), ("c", 1)], 2) == ["b", "a"]


def test_a_tie_straddling_the_cut_is_kept_whole() -> None:
    assert shortlist([("a", 9), ("b", 5), ("c", 5)], 2) == ["a", "b", "c"]


def test_tied_names_keep_the_order_they_arrived_in() -> None:
    assert shortlist([("b", 5), ("a", 5)], 2) == ["b", "a"]
""",
        imports="from shortlist_ties import shortlist\n",
    ),
)

_G032 = D2TaskSpec(
    template_id="d7_numeric.overdraft_fees",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-overdraft-fees",
    module="overdraft_fees",
    module_doc="Counting the times a balance fell past what the account is allowed.",
    issue=(
        "overdraft_fees() is documented to follow the balance through every movement on the "
        "account. Callers report being charged for movements they had already covered by paying "
        "money in, and being charged for landing exactly on the agreed limit rather than past it."
    ),
    expected=(
        "overdraft_fees(balance, amounts, allowance) applies each amount to the balance in "
        "order, money in as well as money out, and counts one fee for each amount that leaves "
        "the balance further down than the allowance. A balance sitting exactly on the "
        "allowance is within it."
    ),
    baseline_reason=(
        "it applies only the amounts that take money out, so paying money in never restores the "
        "balance, and its comparison charges a fee for landing exactly on the allowance"
    ),
    edge_cases=(
        "money paid in counts towards the balance too",
        "a balance exactly on the allowance is within it",
    ),
    baseline="""def overdraft_fees(balance, amounts, allowance):
    \"\"\"Count the fees the movements on an account earn.\"\"\"
    fees = 0
    running = balance
    for amount in amounts:
        if amount < 0:
            running += amount
        if running <= -allowance:
            fees += 1
    return fees""",
    variant_one="""def overdraft_fees(balance, amounts, allowance):
    \"\"\"Count the fees the movements on an account earn.\"\"\"
    fees = 0
    running = balance
    for amount in amounts:
        running += amount
        if running < -allowance:
            fees += 1
    return fees""",
    variant_two="""def overdraft_fees(balance, amounts, allowance):
    \"\"\"Count the fees the movements on an account earn.\"\"\"
    running = balance
    breaches = []
    for amount in amounts:
        running = running + amount
        breaches.append(running + allowance < 0)
    return sum(1 for breached in breaches if breached)""",
    variant_three="""def overdraft_fees(balance, amounts, allowance):
    \"\"\"Count the fees the movements on an account earn.\"\"\"
    fees = 0
    running = balance
    for amount in amounts:
        running += amount
        if running <= -allowance:
            fees += 1
    return fees""",
    variant_four="""def overdraft_fees(balance, amounts, allowance):
    \"\"\"Count the fees the movements on an account earn.\"\"\"
    fees = 0
    running = balance
    for amount in amounts:
        if amount < 0:
            running += amount
        if running < -allowance:
            fees += 1
    return fees""",
    visible_test=_test_module(
        "overdraft_fees",
        "Published contract for counting overdraft fees.",
        """
def test_a_movement_past_the_allowance_earns_a_fee() -> None:
    assert overdraft_fees(100, [-50, -100], 0) == 1


def test_an_account_nobody_touched_earns_nothing() -> None:
    assert overdraft_fees(100, [], 0) == 0
""",
        imports="from overdraft_fees import overdraft_fees\n",
    ),
    hidden_test=_test_module(
        "overdraft_fees",
        "The part of the contract the published tests do not state.",
        """
def test_a_movement_past_the_allowance_earns_a_fee() -> None:
    assert overdraft_fees(100, [-50, -100], 0) == 1


def test_money_paid_in_restores_the_balance() -> None:
    assert overdraft_fees(100, [-150, 100, -10], 20) == 1


def test_landing_exactly_on_the_allowance_is_free() -> None:
    assert overdraft_fees(0, [-20], 20) == 0
""",
        imports="from overdraft_fees import overdraft_fees\n",
    ),
)

_G033 = D2TaskSpec(
    template_id="d7_state.beacon_seen",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-beacon-seen",
    module="beacon_seen",
    module_doc="Keeping the last time a beacon was heard from, against reports that arrive late.",
    issue=(
        "record() is documented to keep the latest sighting of a beacon whatever order the "
        "reports arrive in. Callers report a report that took a long route home dragging a "
        "beacon's last sighting backwards, and the first sighting of a beacon never being "
        "announced as the new beacon it is."
    ),
    expected=(
        "record(seen, beacon, at) returns (seen, is_new): the beacon's time is moved on only "
        "when `at` is later than the time already recorded, an unseen beacon is recorded at "
        "`at`, and is_new says whether this was the beacon's first sighting."
    ),
    baseline_reason=(
        "it writes the time in whatever it is, later or earlier than the one already there, and "
        "it asks whether the beacon is new after it has already recorded it"
    ),
    edge_cases=(
        "a first sighting is reported as new",
        "a report older than the one recorded does not move the time back",
    ),
    baseline="""def record(seen, beacon, at):
    \"\"\"Record a sighting of a beacon.\"\"\"
    updated = dict(seen)
    updated[beacon] = at
    return updated, beacon not in updated""",
    variant_one="""def record(seen, beacon, at):
    \"\"\"Record a sighting of a beacon.\"\"\"
    first = beacon not in seen
    updated = dict(seen)
    if first or at > seen[beacon]:
        updated[beacon] = at
    return updated, first""",
    variant_two="""def record(seen, beacon, at):
    \"\"\"Record a sighting of a beacon.\"\"\"
    updated = dict(seen)
    last = updated.get(beacon)
    if last is None or at > last:
        updated[beacon] = at
    return updated, last is None""",
    variant_three="""def record(seen, beacon, at):
    \"\"\"Record a sighting of a beacon.\"\"\"
    first = beacon not in seen
    updated = dict(seen)
    updated[beacon] = at
    return updated, first""",
    variant_four="""def record(seen, beacon, at):
    \"\"\"Record a sighting of a beacon.\"\"\"
    updated = dict(seen)
    last = updated.get(beacon)
    if last is None or at > last:
        updated[beacon] = at
    return updated, beacon not in updated""",
    visible_test=_test_module(
        "beacon_seen",
        "Published contract for recording a sighting.",
        """
def test_a_later_report_moves_the_time_on() -> None:
    assert record({"b1": 10}, "b1", 20) == ({"b1": 20}, False)


def test_the_other_beacons_are_left_where_they_are() -> None:
    assert record({"b1": 10, "b2": 5}, "b1", 20)[0] == {"b1": 20, "b2": 5}
""",
        imports="from beacon_seen import record\n",
    ),
    hidden_test=_test_module(
        "beacon_seen",
        "The part of the contract the published tests do not state.",
        """
def test_a_later_report_moves_the_time_on() -> None:
    assert record({"b1": 10}, "b1", 20) == ({"b1": 20}, False)


def test_a_first_sighting_is_reported_as_new() -> None:
    assert record({}, "b1", 10) == ({"b1": 10}, True)


def test_a_report_from_before_does_not_move_the_time_back() -> None:
    assert record({"b1": 20}, "b1", 10)[0] == {"b1": 20}
""",
        imports="from beacon_seen import record\n",
    ),
)

_G034 = D2TaskSpec(
    template_id="d7_error.halt_on_fatal",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-halt-on-fatal",
    module="halt_on_fatal",
    module_doc="Stopping a run at the step that cannot be survived, and only there.",
    issue=(
        "run() is documented to stop at a fatal step and to carry on past a warning. Callers "
        "report a run abandoned at the first warning, and the report coming back without the "
        "fatal step in it at all - so the record of the run does not say why it stopped."
    ),
    expected=(
        "run(steps) calls each step in turn and returns the statuses they reported, in order. A "
        "step reporting 'fatal' stops the run and is itself the last status reported; a step "
        "reporting 'warn' is recorded and the run carries on."
    ),
    baseline_reason=(
        "it stops at any status that is not 'ok', warnings included, and it breaks out of the "
        "run before recording the status that stopped it"
    ),
    edge_cases=(
        "a warning is recorded and the run carries on",
        "the fatal status is in the report",
    ),
    baseline="""def run(steps):
    \"\"\"Call each step until one of them cannot be survived.\"\"\"
    collected = []
    for step in steps:
        status = step()
        if status != "ok":
            break
        collected.append(status)
    return collected""",
    variant_one="""def run(steps):
    \"\"\"Call each step until one of them cannot be survived.\"\"\"
    collected = []
    for step in steps:
        status = step()
        collected.append(status)
        if status == "fatal":
            break
    return collected""",
    variant_two="""def run(steps):
    \"\"\"Call each step until one of them cannot be survived.\"\"\"
    collected = []
    for step in steps:
        collected.append(step())
        if collected[-1] == "fatal":
            return collected
    return collected""",
    variant_three="""def run(steps):
    \"\"\"Call each step until one of them cannot be survived.\"\"\"
    collected = []
    for step in steps:
        status = step()
        if status == "fatal":
            break
        collected.append(status)
    return collected""",
    variant_four="""def run(steps):
    \"\"\"Call each step until one of them cannot be survived.\"\"\"
    collected = []
    for step in steps:
        status = step()
        collected.append(status)
        if status != "ok":
            break
    return collected""",
    visible_test=_test_module(
        "halt_on_fatal",
        "Published contract for running the steps.",
        """
def test_a_run_nothing_went_wrong_in_reports_every_step() -> None:
    assert run([lambda: "ok", lambda: "ok"]) == ["ok", "ok"]


def test_a_run_with_no_steps_reports_nothing() -> None:
    assert run([]) == []
""",
        imports="from halt_on_fatal import run\n",
    ),
    hidden_test=_test_module(
        "halt_on_fatal",
        "The part of the contract the published tests do not state.",
        """
def test_a_run_nothing_went_wrong_in_reports_every_step() -> None:
    assert run([lambda: "ok", lambda: "ok"]) == ["ok", "ok"]


def test_a_warning_does_not_stop_the_run() -> None:
    assert run([lambda: "warn", lambda: "ok"]) == ["warn", "ok"]


def test_the_fatal_step_is_in_the_report() -> None:
    assert run([lambda: "fatal", lambda: "ok"]) == ["fatal"]
""",
        imports="from halt_on_fatal import run\n",
    ),
)

_G035 = D2TaskSpec(
    template_id="d7_boundary.turnstile_occupancy",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-turnstile-occupancy",
    module="turnstile_occupancy",
    module_doc="Following how many people are inside, and how many there were at the worst moment.",
    issue=(
        "occupancy() is documented to report how full a room was after every turn of the "
        "turnstile, and how full it ever got. Callers report counts below nobody at all after a "
        "morning where somebody left by a door the turnstile never saw, and a peak that is "
        "simply the last count rather than the highest one."
    ),
    expected=(
        "occupancy(events) reads 'in' and 'out' events in order and returns (readings, peak): "
        "one reading per event of how many are inside afterwards, never below nobody, and the "
        "highest reading the room ever reached."
    ),
    baseline_reason=(
        "it counts an 'out' event down whether or not there is anybody to count out, and it "
        "reports the count it finished on as the peak"
    ),
    edge_cases=(
        "the count never falls below nobody at all",
        "the peak is the highest reading rather than the last",
    ),
    baseline="""def occupancy(events):
    \"\"\"Report how full the room was after each event, and at its fullest.\"\"\"
    inside = 0
    readings = []
    for event in events:
        inside += 1 if event == "in" else -1
        readings.append(inside)
    return readings, inside""",
    variant_one="""def occupancy(events):
    \"\"\"Report how full the room was after each event, and at its fullest.\"\"\"
    inside = 0
    peak = 0
    readings = []
    for event in events:
        inside += 1 if event == "in" else -1
        inside = max(inside, 0)
        readings.append(inside)
        peak = max(peak, inside)
    return readings, peak""",
    variant_two="""def occupancy(events):
    \"\"\"Report how full the room was after each event, and at its fullest.\"\"\"
    readings = []
    inside = 0
    for event in events:
        step = 1 if event == "in" else -1
        inside = inside + step if inside + step > 0 else 0
        readings.append(inside)
    return readings, max(readings) if readings else 0""",
    variant_three="""def occupancy(events):
    \"\"\"Report how full the room was after each event, and at its fullest.\"\"\"
    inside = 0
    readings = []
    for event in events:
        inside += 1 if event == "in" else -1
        inside = max(inside, 0)
        readings.append(inside)
    return readings, inside""",
    variant_four="""def occupancy(events):
    \"\"\"Report how full the room was after each event, and at its fullest.\"\"\"
    inside = 0
    peak = 0
    readings = []
    for event in events:
        inside += 1 if event == "in" else -1
        readings.append(inside)
        peak = max(peak, inside)
    return readings, peak""",
    visible_test=_test_module(
        "turnstile_occupancy",
        "Published contract for following the occupancy.",
        """
def test_a_morning_of_arrivals_fills_the_room() -> None:
    assert occupancy(["in", "in"]) == ([1, 2], 2)


def test_a_turnstile_nobody_used_reports_nothing() -> None:
    assert occupancy([]) == ([], 0)
""",
        imports="from turnstile_occupancy import occupancy\n",
    ),
    hidden_test=_test_module(
        "turnstile_occupancy",
        "The part of the contract the published tests do not state.",
        """
def test_a_morning_of_arrivals_fills_the_room() -> None:
    assert occupancy(["in", "in"]) == ([1, 2], 2)


def test_the_count_never_falls_below_nobody() -> None:
    assert occupancy(["out", "in"]) == ([0, 1], 1)


def test_the_peak_is_the_highest_reading_not_the_last() -> None:
    assert occupancy(["in", "in", "out"]) == ([1, 2, 1], 2)
""",
        imports="from turnstile_occupancy import occupancy\n",
    ),
)

_G036 = D2TaskSpec(
    template_id="d7_transform.scan_summary",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-scan-summary",
    module="scan_summary",
    module_doc="Summarising a day of badge scans into where each badge was last seen.",
    issue=(
        "summarise() is documented to report the gate a badge was seen at last, and to list the "
        "badges in the order the day saw them. Callers report the first gate of the day coming "
        "back instead of the most recent one, and the badges arriving in alphabetical order, "
        "which loses who arrived first."
    ),
    expected=(
        "summarise(scans) takes (badge, gate) pairs in the order they happened and returns a "
        "mapping from badge to (count, gate): how many times the badge was seen and the gate it "
        "was seen at last. The badges come back in the order they were first seen."
    ),
    baseline_reason=(
        "it keeps the gate it recorded when it first met the badge and never replaces it, and "
        "it sorts the summary by badge before returning it"
    ),
    edge_cases=(
        "the gate reported is the last one, not the first",
        "the badges come back in the order they were first seen",
    ),
    baseline="""def summarise(scans):
    \"\"\"Summarise the scans by badge.\"\"\"
    summary = {}
    for badge, gate in scans:
        if badge not in summary:
            summary[badge] = (0, gate)
        count, first = summary[badge]
        summary[badge] = (count + 1, first)
    return dict(sorted(summary.items()))""",
    variant_one="""def summarise(scans):
    \"\"\"Summarise the scans by badge.\"\"\"
    summary = {}
    for badge, gate in scans:
        count = summary[badge][0] if badge in summary else 0
        summary[badge] = (count + 1, gate)
    return summary""",
    variant_two="""def summarise(scans):
    \"\"\"Summarise the scans by badge.\"\"\"
    summary = {}
    for badge, gate in scans:
        if badge not in summary:
            summary[badge] = (1, gate)
        else:
            summary[badge] = (summary[badge][0] + 1, gate)
    return summary""",
    variant_three="""def summarise(scans):
    \"\"\"Summarise the scans by badge.\"\"\"
    summary = {}
    for badge, gate in scans:
        count = summary[badge][0] if badge in summary else 0
        summary[badge] = (count + 1, gate)
    return dict(sorted(summary.items()))""",
    variant_four="""def summarise(scans):
    \"\"\"Summarise the scans by badge.\"\"\"
    summary = {}
    for badge, gate in scans:
        if badge not in summary:
            summary[badge] = (0, gate)
        count, first = summary[badge]
        summary[badge] = (count + 1, first)
    return summary""",
    visible_test=_test_module(
        "scan_summary",
        "Published contract for summarising the scans.",
        """
def test_a_single_scan_is_summarised() -> None:
    assert summarise([("b1", "north")]) == {"b1": (1, "north")}


def test_two_scans_at_one_gate_are_counted() -> None:
    assert summarise([("b1", "north"), ("b1", "north")]) == {"b1": (2, "north")}
""",
        imports="from scan_summary import summarise\n",
    ),
    hidden_test=_test_module(
        "scan_summary",
        "The part of the contract the published tests do not state.",
        """
def test_a_single_scan_is_summarised() -> None:
    assert summarise([("b1", "north")]) == {"b1": (1, "north")}


def test_the_gate_reported_is_the_last_one() -> None:
    assert summarise([("b1", "north"), ("b1", "south")]) == {"b1": (2, "south")}


def test_the_badges_come_back_in_the_order_first_seen() -> None:
    assert list(summarise([("z", "north"), ("a", "north")])) == ["z", "a"]
""",
        imports="from scan_summary import summarise\n",
    ),
)

_G037 = D2TaskSpec(
    template_id="d7_parsing.berth_window",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-berth-window",
    module="berth_window",
    module_doc="Reading the window a berth is booked for, including the one that ends at midnight.",
    issue=(
        "parse_window() is documented to accept a window running to the end of the day and to "
        "refuse one that does not run forwards. Callers report a booking to '24:00' being "
        "rejected as a bad time, and a window typed the wrong way round being accepted and "
        "then holding the berth for a negative length of time."
    ),
    expected=(
        "parse_window(text) reads 'HH:MM-HH:MM' and returns (start, end) as minutes past "
        "midnight. An end of '24:00' is the end of the day, minutes beyond fifty-nine or a time "
        "past the end of the day raise ValueError, and so does a window whose end does not come "
        "after its start."
    ),
    baseline_reason=(
        "its hour test stops at twenty-three, so the end of the day is not a time it can read, "
        "and it never compares the end with the start"
    ),
    edge_cases=(
        "a window ending at the end of the day is read",
        "a window that does not run forwards is refused",
    ),
    baseline="""def parse_window(text):
    \"\"\"Read a booking window into minutes past midnight.\"\"\"
    start_text, _, end_text = text.partition("-")
    times = []
    for piece in (start_text, end_text):
        hours, _, minutes = piece.partition(":")
        if not 0 <= int(hours) <= 23 or not 0 <= int(minutes) <= 59:
            raise ValueError("not a time: " + piece)
        times.append(int(hours) * 60 + int(minutes))
    return times[0], times[1]""",
    variant_one="""def parse_window(text):
    \"\"\"Read a booking window into minutes past midnight.\"\"\"
    start_text, _, end_text = text.partition("-")
    times = []
    for piece in (start_text, end_text):
        hours, _, minutes = piece.partition(":")
        if not 0 <= int(hours) <= 24 or not 0 <= int(minutes) <= 59:
            raise ValueError("not a time: " + piece)
        total = int(hours) * 60 + int(minutes)
        if total > 24 * 60:
            raise ValueError("not a time: " + piece)
        times.append(total)
    if times[1] <= times[0]:
        raise ValueError("window does not run forwards: " + text)
    return times[0], times[1]""",
    variant_two="""def parse_window(text):
    \"\"\"Read a booking window into minutes past midnight.\"\"\"
    start_text, _, end_text = text.partition("-")
    times = []
    for piece in (start_text, end_text):
        hours, _, minutes = piece.partition(":")
        total = int(hours) * 60 + int(minutes)
        if not 0 <= int(minutes) < 60 or not 0 <= total <= 24 * 60:
            raise ValueError("not a time: " + piece)
        times.append(total)
    start, end = times
    if end <= start:
        raise ValueError("window does not run forwards: " + text)
    return start, end""",
    variant_three="""def parse_window(text):
    \"\"\"Read a booking window into minutes past midnight.\"\"\"
    start_text, _, end_text = text.partition("-")
    times = []
    for piece in (start_text, end_text):
        hours, _, minutes = piece.partition(":")
        total = int(hours) * 60 + int(minutes)
        if not 0 <= int(minutes) < 60 or not 0 <= total <= 24 * 60:
            raise ValueError("not a time: " + piece)
        times.append(total)
    return times[0], times[1]""",
    variant_four="""def parse_window(text):
    \"\"\"Read a booking window into minutes past midnight.\"\"\"
    start_text, _, end_text = text.partition("-")
    times = []
    for piece in (start_text, end_text):
        hours, _, minutes = piece.partition(":")
        if not 0 <= int(hours) <= 23 or not 0 <= int(minutes) <= 59:
            raise ValueError("not a time: " + piece)
        times.append(int(hours) * 60 + int(minutes))
    if times[1] <= times[0]:
        raise ValueError("window does not run forwards: " + text)
    return times[0], times[1]""",
    visible_test=_test_module(
        "berth_window",
        "Published contract for reading a booking window.",
        """
import pytest


def test_a_window_reads_as_minutes_past_midnight() -> None:
    assert parse_window("08:00-12:30") == (480, 750)


def test_minutes_beyond_the_hour_are_refused() -> None:
    with pytest.raises(ValueError):
        parse_window("08:00-12:70")
""",
        imports="from berth_window import parse_window\n",
    ),
    hidden_test=_test_module(
        "berth_window",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_window_reads_as_minutes_past_midnight() -> None:
    assert parse_window("08:00-12:30") == (480, 750)


def test_a_window_running_to_the_end_of_the_day_is_read() -> None:
    assert parse_window("22:00-24:00") == (1320, 1440)


def test_a_window_that_does_not_run_forwards_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_window("12:00-09:00")
""",
        imports="from berth_window import parse_window\n",
    ),
)

_G038 = D2TaskSpec(
    template_id="d7_error.stall_fallback",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-stall-fallback",
    module="stall_fallback",
    module_doc="Falling back to the second source, for the one reason that justifies it.",
    issue=(
        "read() is documented to fall back only when the first source cannot find the thing. "
        "Callers report the fallback hiding faults that have nothing to do with a missing "
        "record, and an answer of 'nothing' from the first source being overridden by the "
        "second although 'nothing' was the answer."
    ),
    expected=(
        "read(primary, backup) returns what the primary source answers. Only a LookupError from "
        "the primary sends the question to the backup; any other error is the caller's to see, "
        "and an empty answer is still the primary's answer."
    ),
    baseline_reason=(
        "it catches every error the primary can raise rather than the one it knows how to "
        "survive, and it treats an empty answer as no answer at all"
    ),
    edge_cases=(
        "an empty answer is still the primary's answer",
        "an error that is not a lookup failure reaches the caller",
    ),
    baseline="""def read(primary, backup):
    \"\"\"Read from the primary source, falling back to the backup.\"\"\"
    try:
        value = primary()
    except Exception:
        return backup()
    if not value:
        return backup()
    return value""",
    variant_one="""def read(primary, backup):
    \"\"\"Read from the primary source, falling back to the backup.\"\"\"
    try:
        return primary()
    except LookupError:
        return backup()""",
    variant_two="""def read(primary, backup):
    \"\"\"Read from the primary source, falling back to the backup.\"\"\"
    answered = False
    value = None
    try:
        value = primary()
        answered = True
    except LookupError:
        answered = False
    return value if answered else backup()""",
    variant_three="""def read(primary, backup):
    \"\"\"Read from the primary source, falling back to the backup.\"\"\"
    try:
        value = primary()
    except LookupError:
        return backup()
    if not value:
        return backup()
    return value""",
    variant_four="""def read(primary, backup):
    \"\"\"Read from the primary source, falling back to the backup.\"\"\"
    try:
        return primary()
    except Exception:
        return backup()""",
    visible_test=_test_module(
        "stall_fallback",
        "Published contract for reading with a fallback.",
        """
def _missing():
    raise LookupError("no record")


def test_the_primary_answer_is_the_answer() -> None:
    assert read(lambda: "first", lambda: "second") == "first"


def test_a_missing_record_goes_to_the_backup() -> None:
    assert read(_missing, lambda: "second") == "second"
""",
        imports="from stall_fallback import read\n",
    ),
    hidden_test=_test_module(
        "stall_fallback",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _broken():
    raise ValueError("the source is on fire")


def test_the_primary_answer_is_the_answer() -> None:
    assert read(lambda: "first", lambda: "second") == "first"


def test_an_empty_answer_is_still_the_primarys_answer() -> None:
    assert read(lambda: "", lambda: "second") == ""


def test_an_error_that_is_not_a_lookup_failure_reaches_the_caller() -> None:
    with pytest.raises(ValueError):
        read(_broken, lambda: "second")
""",
        imports="from stall_fallback import read\n",
    ),
)

_G039 = D2TaskSpec(
    template_id="d7_state.crate_move",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-crate-move",
    module="crate_move",
    module_doc="Moving an item between crates, so that it is in exactly one of them afterwards.",
    issue=(
        "move() is documented to leave an item in the crate it was moved to and nowhere else. "
        "Callers report stock counts doubling because the item stayed in the crate it came "
        "from, and an item nobody was holding appearing in a crate out of nowhere."
    ),
    expected=(
        "move(crates, item, target) returns the crates with the item in the target crate and in "
        "no other. An item already in the target leaves the crates as they were, and an item no "
        "crate holds raises KeyError."
    ),
    baseline_reason=(
        "it adds the item to the target without taking it out of the crate it was in, and it "
        "never asks whether any crate was holding it"
    ),
    edge_cases=(
        "the item leaves the crate it came from",
        "an item no crate holds is refused",
    ),
    baseline="""def move(crates, item, target):
    \"\"\"Move an item into the target crate.\"\"\"
    moved = {name: list(items) for name, items in crates.items()}
    moved[target].append(item)
    return moved""",
    variant_one="""def move(crates, item, target):
    \"\"\"Move an item into the target crate.\"\"\"
    source = None
    for name, items in crates.items():
        if item in items:
            source = name
            break
    if source is None:
        raise KeyError(item)
    moved = {name: list(items) for name, items in crates.items()}
    if source != target:
        moved[source].remove(item)
        moved[target].append(item)
    return moved""",
    variant_two="""def move(crates, item, target):
    \"\"\"Move an item into the target crate.\"\"\"
    holders = [name for name, items in crates.items() if item in items]
    if not holders:
        raise KeyError(item)
    moved = {}
    for name, items in crates.items():
        moved[name] = [held for held in items if held != item or name == target]
    if holders[0] != target:
        moved[target].append(item)
    return moved""",
    variant_three="""def move(crates, item, target):
    \"\"\"Move an item into the target crate.\"\"\"
    moved = {}
    for name, items in crates.items():
        moved[name] = [held for held in items if held != item or name == target]
    if item not in moved[target]:
        moved[target].append(item)
    return moved""",
    variant_four="""def move(crates, item, target):
    \"\"\"Move an item into the target crate.\"\"\"
    if not any(item in items for items in crates.values()):
        raise KeyError(item)
    moved = {name: list(items) for name, items in crates.items()}
    moved[target].append(item)
    return moved""",
    visible_test=_test_module(
        "crate_move",
        "Published contract for moving an item between crates.",
        """
def test_the_item_arrives_in_the_target_crate() -> None:
    assert move({"a": ["p"], "b": []}, "p", "b")["b"] == ["p"]


def test_the_crates_keep_their_names() -> None:
    assert sorted(move({"a": ["p"], "b": []}, "p", "b")) == ["a", "b"]
""",
        imports="from crate_move import move\n",
    ),
    hidden_test=_test_module(
        "crate_move",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_item_arrives_in_the_target_crate() -> None:
    assert move({"a": ["p"], "b": []}, "p", "b")["b"] == ["p"]


def test_the_item_leaves_the_crate_it_came_from() -> None:
    assert move({"a": ["p"], "b": []}, "p", "b") == {"a": [], "b": ["p"]}


def test_an_item_no_crate_holds_is_refused() -> None:
    with pytest.raises(KeyError):
        move({"a": [], "b": []}, "z", "b")
""",
        imports="from crate_move import move\n",
    ),
)

_G040 = D2TaskSpec(
    template_id="d7_numeric.fresh_average",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-fresh-average",
    module="fresh_average",
    module_doc="Averaging the readings that are still worth reading.",
    issue=(
        "fresh_average() is documented to average the readings that are not yet too old. "
        "Callers report a reading arriving exactly at the age limit being thrown away, and the "
        "average coming back far too low on a run where most readings were stale - as though "
        "the stale ones had been counted as nothing rather than not counted."
    ),
    expected=(
        "fresh_average(readings, now, max_age) averages the values of the (at, value) readings "
        "whose age is at most max_age, and returns None when no reading is fresh. A reading "
        "exactly at the age limit is still fresh, and a stale reading is not part of the "
        "average at all."
    ),
    baseline_reason=(
        "its age test excludes the limit itself, and it divides the fresh total by how many "
        "readings there were rather than by how many it counted"
    ),
    edge_cases=(
        "a reading exactly at the age limit is still fresh",
        "a stale reading is not counted in the average",
    ),
    baseline="""def fresh_average(readings, now, max_age):
    \"\"\"Average the readings that are not yet too old.\"\"\"
    total = 0
    for at, value in readings:
        if now - at < max_age:
            total += value
    if not readings:
        return None
    return total / len(readings)""",
    variant_one="""def fresh_average(readings, now, max_age):
    \"\"\"Average the readings that are not yet too old.\"\"\"
    fresh = [value for at, value in readings if now - at <= max_age]
    if not fresh:
        return None
    return sum(fresh) / len(fresh)""",
    variant_two="""def fresh_average(readings, now, max_age):
    \"\"\"Average the readings that are not yet too old.\"\"\"
    total = 0
    kept = 0
    for at, value in readings:
        if now - at <= max_age:
            total += value
            kept += 1
    return total / kept if kept else None""",
    variant_three="""def fresh_average(readings, now, max_age):
    \"\"\"Average the readings that are not yet too old.\"\"\"
    total = 0
    for at, value in readings:
        if now - at <= max_age:
            total += value
    if not readings:
        return None
    return total / len(readings)""",
    variant_four="""def fresh_average(readings, now, max_age):
    \"\"\"Average the readings that are not yet too old.\"\"\"
    fresh = [value for at, value in readings if now - at < max_age]
    if not fresh:
        return None
    return sum(fresh) / len(fresh)""",
    visible_test=_test_module(
        "fresh_average",
        "Published contract for averaging the fresh readings.",
        """
def test_fresh_readings_are_averaged() -> None:
    assert fresh_average([(10, 4), (12, 6)], 12, 5) == 5.0


def test_no_readings_at_all_average_to_nothing() -> None:
    assert fresh_average([], 0, 5) is None
""",
        imports="from fresh_average import fresh_average\n",
    ),
    hidden_test=_test_module(
        "fresh_average",
        "The part of the contract the published tests do not state.",
        """
def test_fresh_readings_are_averaged() -> None:
    assert fresh_average([(10, 4), (12, 6)], 12, 5) == 5.0


def test_a_reading_exactly_at_the_limit_is_still_fresh() -> None:
    assert fresh_average([(5, 10)], 10, 5) == 10.0


def test_a_stale_reading_is_not_counted_in_the_average() -> None:
    assert fresh_average([(0, 100), (10, 4)], 10, 5) == 4.0
""",
        imports="from fresh_average import fresh_average\n",
    ),
)

_G041 = D2TaskSpec(
    template_id="d7_boundary.pinned_prune",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-pinned-prune",
    module="pinned_prune",
    module_doc="Pruning a log down to a size, without pruning what somebody pinned.",
    issue=(
        "prune() is documented to keep the most recent entries and to keep a pinned entry "
        "whatever its age. Callers report pinned entries disappearing, and the entries that "
        "survive being the oldest ones rather than the newest - the opposite of what a log is "
        "pruned for."
    ),
    expected=(
        "prune(entries, keep) takes (name, pinned) entries oldest first and returns the ones to "
        "keep, in the order they arrived: the `keep` most recent unpinned entries together with "
        "every pinned entry, whose age does not count against it."
    ),
    baseline_reason=(
        "it takes a slice from the start of the log, which keeps the oldest entries rather than "
        "the newest, and the slice knows nothing about which entries were pinned"
    ),
    edge_cases=(
        "a pinned entry is kept whatever its age",
        "the entries kept are the most recent ones",
    ),
    baseline="""def prune(entries, keep):
    \"\"\"Prune the log down to the entries worth keeping.\"\"\"
    return list(entries[:keep])""",
    variant_one="""def prune(entries, keep):
    \"\"\"Prune the log down to the entries worth keeping.\"\"\"
    unpinned = [name for name, pinned in entries if not pinned]
    recent = set(unpinned[-keep:]) if keep > 0 else set()
    return [entry for entry in entries if entry[1] or entry[0] in recent]""",
    variant_two="""def prune(entries, keep):
    \"\"\"Prune the log down to the entries worth keeping.\"\"\"
    allowance = keep
    kept = []
    for name, pinned in reversed(entries):
        if pinned:
            kept.append((name, pinned))
        elif allowance > 0:
            kept.append((name, pinned))
            allowance -= 1
    return list(reversed(kept))""",
    variant_three="""def prune(entries, keep):
    \"\"\"Prune the log down to the entries worth keeping.\"\"\"
    unpinned = [name for name, pinned in entries if not pinned]
    oldest = set(unpinned[:keep])
    return [entry for entry in entries if entry[1] or entry[0] in oldest]""",
    variant_four="""def prune(entries, keep):
    \"\"\"Prune the log down to the entries worth keeping.\"\"\"
    return list(entries[-keep:]) if keep > 0 else []""",
    visible_test=_test_module(
        "pinned_prune",
        "Published contract for pruning the log.",
        """
def test_a_log_within_the_size_is_kept_whole() -> None:
    assert prune([("a", False), ("b", False)], 2) == [("a", False), ("b", False)]


def test_an_empty_log_prunes_to_nothing() -> None:
    assert prune([], 1) == []
""",
        imports="from pinned_prune import prune\n",
    ),
    hidden_test=_test_module(
        "pinned_prune",
        "The part of the contract the published tests do not state.",
        """
def test_a_log_within_the_size_is_kept_whole() -> None:
    assert prune([("a", False), ("b", False)], 2) == [("a", False), ("b", False)]


def test_a_pinned_entry_does_not_count_against_the_size() -> None:
    entries = [("a", True), ("b", False), ("c", False)]
    assert prune(entries, 2) == [("a", True), ("b", False), ("c", False)]


def test_the_entries_kept_are_the_most_recent() -> None:
    entries = [("a", False), ("b", False), ("c", False)]
    assert prune(entries, 2) == [("b", False), ("c", False)]
""",
        imports="from pinned_prune import prune\n",
    ),
)

_G042 = D2TaskSpec(
    template_id="d7_transform.mark_changes",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-mark-changes",
    module="mark_changes",
    module_doc="Marking the rows where the field being followed actually moved.",
    issue=(
        "mark() is documented to follow one named field and to mark the first row as a change, "
        "because there is nothing before it to be the same as. Callers report the first row "
        "coming back unmarked, and rows marked as changes when some other field moved and the "
        "field being followed did not."
    ),
    expected=(
        "mark(rows, field) returns each row with a 'changed' flag saying whether the named "
        "field differs from the row immediately before it. The first row is always a change, "
        "and no other field takes part in the comparison."
    ),
    baseline_reason=(
        "it compares whole rows rather than the named field, and it marks the first row as "
        "unchanged because there is no row before it to differ from"
    ),
    edge_cases=(
        "the first row is always a change",
        "only the named field decides whether a row changed",
    ),
    baseline="""def mark(rows, field):
    \"\"\"Mark the rows where the followed field moved.\"\"\"
    marked = []
    previous = None
    for index, row in enumerate(rows):
        changed = index > 0 and row != previous
        marked.append({**row, "changed": changed})
        previous = row
    return marked""",
    variant_one="""def mark(rows, field):
    \"\"\"Mark the rows where the followed field moved.\"\"\"
    marked = []
    previous = None
    for index, row in enumerate(rows):
        changed = index == 0 or row[field] != previous
        marked.append({**row, "changed": changed})
        previous = row[field]
    return marked""",
    variant_two="""def mark(rows, field):
    \"\"\"Mark the rows where the followed field moved.\"\"\"
    marked = []
    for index, row in enumerate(rows):
        if index == 0:
            changed = True
        else:
            changed = row[field] != rows[index - 1][field]
        marked.append({**row, "changed": changed})
    return marked""",
    variant_three="""def mark(rows, field):
    \"\"\"Mark the rows where the followed field moved.\"\"\"
    marked = []
    previous = None
    for index, row in enumerate(rows):
        changed = index == 0 or row != previous
        marked.append({**row, "changed": changed})
        previous = row
    return marked""",
    variant_four="""def mark(rows, field):
    \"\"\"Mark the rows where the followed field moved.\"\"\"
    marked = []
    previous = None
    for index, row in enumerate(rows):
        changed = index > 0 and row[field] != previous
        marked.append({**row, "changed": changed})
        previous = row[field]
    return marked""",
    visible_test=_test_module(
        "mark_changes",
        "Published contract for marking the changes.",
        """
def test_a_moved_field_is_a_change() -> None:
    assert mark([{"v": 1}, {"v": 2}], "v")[1]["changed"] is True


def test_a_field_that_stayed_put_is_not_a_change() -> None:
    assert mark([{"v": 1}, {"v": 1}], "v")[1]["changed"] is False
""",
        imports="from mark_changes import mark\n",
    ),
    hidden_test=_test_module(
        "mark_changes",
        "The part of the contract the published tests do not state.",
        """
def test_a_moved_field_is_a_change() -> None:
    assert mark([{"v": 1}, {"v": 2}], "v")[1]["changed"] is True


def test_the_first_row_is_always_a_change() -> None:
    assert mark([{"v": 1}], "v")[0]["changed"] is True


def test_only_the_followed_field_decides() -> None:
    rows = [{"v": 1, "other": "a"}, {"v": 1, "other": "b"}]
    assert mark(rows, "v")[1]["changed"] is False
""",
        imports="from mark_changes import mark\n",
    ),
)

_G043 = D2TaskSpec(
    template_id="d7_error.retry_window",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-retry-window",
    module="retry_window",
    module_doc="Deciding whether an error is worth another attempt, and whether there is time.",
    issue=(
        "should_retry() is documented to retry only the two kinds of error a retry can help "
        "with. Callers report errors nobody classified being retried simply because they were "
        "not marked fatal, and a retry being started exactly at the deadline it was supposed to "
        "respect."
    ),
    expected=(
        "should_retry(kind, attempt, attempts_allowed, now, deadline) is true only when the "
        "kind is 'timeout' or 'unavailable', the attempt is below the number allowed, and now "
        "is strictly before the deadline. Everything else is false."
    ),
    baseline_reason=(
        "it treats every kind except 'fatal' as worth retrying rather than the two that are, "
        "and its deadline test admits the deadline itself"
    ),
    edge_cases=(
        "a kind nobody classified as retryable is not retried",
        "the deadline itself is already too late",
    ),
    baseline="""def should_retry(kind, attempt, attempts_allowed, now, deadline):
    \"\"\"Say whether this error is worth another attempt.\"\"\"
    if kind == "fatal":
        return False
    return attempt < attempts_allowed and now <= deadline""",
    variant_one="""def should_retry(kind, attempt, attempts_allowed, now, deadline):
    \"\"\"Say whether this error is worth another attempt.\"\"\"
    if kind not in {"timeout", "unavailable"}:
        return False
    return attempt < attempts_allowed and now < deadline""",
    variant_two="""def should_retry(kind, attempt, attempts_allowed, now, deadline):
    \"\"\"Say whether this error is worth another attempt.\"\"\"
    retryable = kind in ("timeout", "unavailable")
    within_attempts = attempt < attempts_allowed
    before_deadline = deadline > now
    return bool(retryable and within_attempts and before_deadline)""",
    variant_three="""def should_retry(kind, attempt, attempts_allowed, now, deadline):
    \"\"\"Say whether this error is worth another attempt.\"\"\"
    if kind not in {"timeout", "unavailable"}:
        return False
    return attempt < attempts_allowed and now <= deadline""",
    variant_four="""def should_retry(kind, attempt, attempts_allowed, now, deadline):
    \"\"\"Say whether this error is worth another attempt.\"\"\"
    if kind == "fatal":
        return False
    return attempt < attempts_allowed and now < deadline""",
    visible_test=_test_module(
        "retry_window",
        "Published contract for the retry decision.",
        """
def test_a_timeout_with_attempts_and_time_left_is_retried() -> None:
    assert should_retry("timeout", 0, 3, 5, 10) is True


def test_a_fatal_error_is_never_retried() -> None:
    assert should_retry("fatal", 0, 3, 5, 10) is False


def test_an_exhausted_attempt_count_stops_the_retries() -> None:
    assert should_retry("timeout", 3, 3, 5, 10) is False
""",
        imports="from retry_window import should_retry\n",
    ),
    hidden_test=_test_module(
        "retry_window",
        "The part of the contract the published tests do not state.",
        """
def test_a_timeout_with_attempts_and_time_left_is_retried() -> None:
    assert should_retry("timeout", 0, 3, 5, 10) is True


def test_a_kind_nobody_classified_is_not_retried() -> None:
    assert should_retry("corrupt", 0, 3, 5, 10) is False


def test_the_deadline_itself_is_already_too_late() -> None:
    assert should_retry("timeout", 0, 3, 10, 10) is False
""",
        imports="from retry_window import should_retry\n",
    ),
)

_G044 = D2TaskSpec(
    template_id="d7_parsing.stamp_parts",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-stamp-parts",
    module="stamp_parts",
    module_doc="Reading a timestamp written either of the two ways people write it.",
    issue=(
        "parse_stamp() is documented to accept a stamp whose date and time are separated by a "
        "space as readily as one separated by a 'T'. Callers report the spaced form being "
        "rejected outright, and a stamp naming a thirteenth month being read without complaint "
        "and carried into the rest of the system."
    ),
    expected=(
        "parse_stamp(text) returns (year, month, day, minutes), where minutes is the time as "
        "minutes past midnight or None when the stamp carries no time. The date and the time "
        "may be separated by a space or by a 'T'. A month outside one to twelve or a day "
        "outside one to thirty-one raises ValueError."
    ),
    baseline_reason=(
        "it looks for a 'T' and nothing else, so a spaced stamp is read as a date it cannot "
        "make sense of, and it never asks whether the month and day it read are real"
    ),
    edge_cases=(
        "a space separates the date from the time as well as a 'T'",
        "a month outside the year is refused",
    ),
    baseline="""def parse_stamp(text):
    \"\"\"Read a timestamp into its parts.\"\"\"
    date_text, separator, time_text = text.partition("T")
    year, month, day = (int(part) for part in date_text.split("-"))
    if not separator:
        return year, month, day, None
    hours, _, minutes = time_text.partition(":")
    return year, month, day, int(hours) * 60 + int(minutes)""",
    variant_one="""def parse_stamp(text):
    \"\"\"Read a timestamp into its parts.\"\"\"
    date_text, _, time_text = text.replace("T", " ").partition(" ")
    year, month, day = (int(part) for part in date_text.split("-"))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise ValueError("not a date: " + text)
    if not time_text:
        return year, month, day, None
    hours, _, minutes = time_text.partition(":")
    return year, month, day, int(hours) * 60 + int(minutes)""",
    variant_two="""def parse_stamp(text):
    \"\"\"Read a timestamp into its parts.\"\"\"
    date_text = text
    time_text = ""
    for separator in ("T", " "):
        if separator in text:
            date_text, time_text = text.split(separator, 1)
            break
    parts = date_text.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    if month < 1 or month > 12 or day < 1 or day > 31:
        raise ValueError("not a date: " + text)
    if not time_text:
        return year, month, day, None
    hours, _, minutes = time_text.partition(":")
    return year, month, day, int(hours) * 60 + int(minutes)""",
    variant_three="""def parse_stamp(text):
    \"\"\"Read a timestamp into its parts.\"\"\"
    date_text, _, time_text = text.replace("T", " ").partition(" ")
    year, month, day = (int(part) for part in date_text.split("-"))
    if not time_text:
        return year, month, day, None
    hours, _, minutes = time_text.partition(":")
    return year, month, day, int(hours) * 60 + int(minutes)""",
    variant_four="""def parse_stamp(text):
    \"\"\"Read a timestamp into its parts.\"\"\"
    date_text, separator, time_text = text.partition("T")
    year, month, day = (int(part) for part in date_text.split("-"))
    if not 1 <= month <= 12 or not 1 <= day <= 31:
        raise ValueError("not a date: " + text)
    if not separator:
        return year, month, day, None
    hours, _, minutes = time_text.partition(":")
    return year, month, day, int(hours) * 60 + int(minutes)""",
    visible_test=_test_module(
        "stamp_parts",
        "Published contract for reading a timestamp.",
        """
def test_a_date_on_its_own_carries_no_time() -> None:
    assert parse_stamp("2026-08-10") == (2026, 8, 10, None)


def test_a_stamp_written_with_a_t_is_read() -> None:
    assert parse_stamp("2026-08-10T09:15") == (2026, 8, 10, 555)
""",
        imports="from stamp_parts import parse_stamp\n",
    ),
    hidden_test=_test_module(
        "stamp_parts",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_stamp_written_with_a_t_is_read() -> None:
    assert parse_stamp("2026-08-10T09:15") == (2026, 8, 10, 555)


def test_a_stamp_written_with_a_space_is_read_too() -> None:
    assert parse_stamp("2026-08-10 09:15") == (2026, 8, 10, 555)


def test_a_month_outside_the_year_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_stamp("2026-13-10")
""",
        imports="from stamp_parts import parse_stamp\n",
    ),
)

_G045 = D2TaskSpec(
    template_id="d7_state.stocktake",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-stocktake",
    module="stocktake",
    module_doc="Adjusting a stock count, and refusing the adjustments that cannot be true.",
    issue=(
        "adjust() is documented to refuse an adjustment that would take a count below nothing "
        "rather than quietly settling on nothing. Callers report shortfalls disappearing that "
        "way, so nobody finds out stock is missing, and an item nobody stocks appearing in the "
        "count as though it had always been there."
    ),
    expected=(
        "adjust(stock, item, delta) returns the stock with the item's count moved by delta. An "
        "adjustment taking the count below nothing raises ValueError and changes nothing, and "
        "an item the stock does not list raises KeyError."
    ),
    baseline_reason=(
        "it settles a count that would go below nothing at nothing instead of refusing it, and "
        "it reads a missing item as a count of nothing rather than as an item it does not stock"
    ),
    edge_cases=(
        "taking out more than there is is refused",
        "an item the stock does not list is refused",
    ),
    baseline="""def adjust(stock, item, delta):
    \"\"\"Move an item's stock count by a delta.\"\"\"
    updated = dict(stock)
    updated[item] = max(0, updated.get(item, 0) + delta)
    return updated""",
    variant_one="""def adjust(stock, item, delta):
    \"\"\"Move an item's stock count by a delta.\"\"\"
    if item not in stock:
        raise KeyError(item)
    total = stock[item] + delta
    if total < 0:
        raise ValueError("stock cannot go below nothing: " + str(item))
    updated = dict(stock)
    updated[item] = total
    return updated""",
    variant_two="""def adjust(stock, item, delta):
    \"\"\"Move an item's stock count by a delta.\"\"\"
    total = stock[item] + delta
    if total < 0:
        raise ValueError("stock cannot go below nothing: " + str(item))
    return {**stock, item: total}""",
    variant_three="""def adjust(stock, item, delta):
    \"\"\"Move an item's stock count by a delta.\"\"\"
    total = stock.get(item, 0) + delta
    if total < 0:
        raise ValueError("stock cannot go below nothing: " + str(item))
    updated = dict(stock)
    updated[item] = total
    return updated""",
    variant_four="""def adjust(stock, item, delta):
    \"\"\"Move an item's stock count by a delta.\"\"\"
    if item not in stock:
        raise KeyError(item)
    updated = dict(stock)
    updated[item] = max(0, stock[item] + delta)
    return updated""",
    visible_test=_test_module(
        "stocktake",
        "Published contract for adjusting the stock.",
        """
def test_stock_coming_in_is_added() -> None:
    assert adjust({"nails": 10}, "nails", 5) == {"nails": 15}


def test_stock_going_out_to_nothing_is_allowed() -> None:
    assert adjust({"nails": 10}, "nails", -10) == {"nails": 0}
""",
        imports="from stocktake import adjust\n",
    ),
    hidden_test=_test_module(
        "stocktake",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_stock_coming_in_is_added() -> None:
    assert adjust({"nails": 10}, "nails", 5) == {"nails": 15}


def test_taking_out_more_than_there_is_is_refused() -> None:
    with pytest.raises(ValueError):
        adjust({"nails": 1}, "nails", -2)


def test_an_item_the_stock_does_not_list_is_refused() -> None:
    with pytest.raises(KeyError):
        adjust({"nails": 1}, "screws", 5)
""",
        imports="from stocktake import adjust\n",
    ),
)

_G046 = D2TaskSpec(
    template_id="d7_boundary.page_span",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7-boundary-page-span",
    module="page_span",
    module_doc="Saying which items are on a page, and which pages there are not.",
    issue=(
        "span() is documented to stop the last page at the last item and to refuse a page there "
        "is nothing on. Callers report the final page claiming items that do not exist, and a "
        "page number past the end of the list coming back as a span rather than as the mistake "
        "it is."
    ),
    expected=(
        "span(total, page_size, page) returns the (first, last) item numbers on a page, "
        "counting items and pages from one and including both ends. The last page stops at the "
        "total, and a page beyond the last one raises ValueError."
    ),
    baseline_reason=(
        "it takes the page size as the length of every page including the last, and it never "
        "asks whether the page it was given is a page at all"
    ),
    edge_cases=(
        "the last page stops at the last item",
        "a page beyond the end is refused",
    ),
    baseline="""def span(total, page_size, page):
    \"\"\"Return the first and last item numbers on a page.\"\"\"
    first = (page - 1) * page_size + 1
    return first, first + page_size - 1""",
    variant_one="""def span(total, page_size, page):
    \"\"\"Return the first and last item numbers on a page.\"\"\"
    first = (page - 1) * page_size + 1
    if first > total:
        raise ValueError("page beyond the end: " + str(page))
    return first, min(first + page_size - 1, total)""",
    variant_two="""def span(total, page_size, page):
    \"\"\"Return the first and last item numbers on a page.\"\"\"
    pages = -(-total // page_size)
    if page < 1 or page > pages:
        raise ValueError("page beyond the end: " + str(page))
    first = (page - 1) * page_size + 1
    last = page * page_size
    return first, last if last < total else total""",
    variant_three="""def span(total, page_size, page):
    \"\"\"Return the first and last item numbers on a page.\"\"\"
    first = (page - 1) * page_size + 1
    return first, min(first + page_size - 1, total)""",
    variant_four="""def span(total, page_size, page):
    \"\"\"Return the first and last item numbers on a page.\"\"\"
    first = (page - 1) * page_size + 1
    if first > total:
        raise ValueError("page beyond the end: " + str(page))
    return first, first + page_size - 1""",
    visible_test=_test_module(
        "page_span",
        "Published contract for the span of a page.",
        """
def test_the_first_page_starts_at_the_first_item() -> None:
    assert span(10, 5, 1) == (1, 5)


def test_a_page_that_fills_exactly_ends_at_the_total() -> None:
    assert span(10, 5, 2) == (6, 10)
""",
        imports="from page_span import span\n",
    ),
    hidden_test=_test_module(
        "page_span",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_the_first_page_starts_at_the_first_item() -> None:
    assert span(10, 5, 1) == (1, 5)


def test_the_last_page_stops_at_the_last_item() -> None:
    assert span(7, 5, 2) == (6, 7)


def test_a_page_beyond_the_end_is_refused() -> None:
    with pytest.raises(ValueError):
        span(7, 5, 3)
""",
        imports="from page_span import span\n",
    ),
)

_G047 = D2TaskSpec(
    template_id="d7_numeric.vote_threshold",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d7-numeric-vote-threshold",
    module="vote_threshold",
    module_doc="Deciding a motion on the votes that were actually cast.",
    issue=(
        "passes() is documented to need more than half of the votes cast, and to treat an "
        "abstention as a vote not cast. Callers report motions passing on a dead tie, and "
        "motions failing because the people who abstained were counted as though they had "
        "voted against."
    ),
    expected=(
        "passes(votes) is true when the votes for a motion are strictly more than half of the "
        "votes cast. Only 'for' and 'against' are cast; an abstention takes no part in the "
        "count on either side."
    ),
    baseline_reason=(
        "it passes a motion whose votes for are exactly half, and it counts every vote in the "
        "room as cast, abstentions included"
    ),
    edge_cases=(
        "a tie does not pass the motion",
        "an abstention is not a vote cast",
    ),
    baseline="""def passes(votes):
    \"\"\"Say whether the motion carries.\"\"\"
    for_votes = sum(1 for vote in votes if vote == "for")
    return for_votes * 2 >= len(votes)""",
    variant_one="""def passes(votes):
    \"\"\"Say whether the motion carries.\"\"\"
    cast = [vote for vote in votes if vote in ("for", "against")]
    for_votes = sum(1 for vote in cast if vote == "for")
    return for_votes * 2 > len(cast)""",
    variant_two="""def passes(votes):
    \"\"\"Say whether the motion carries.\"\"\"
    for_votes = 0
    against = 0
    for vote in votes:
        if vote == "for":
            for_votes += 1
        elif vote == "against":
            against += 1
    return for_votes > against""",
    variant_three="""def passes(votes):
    \"\"\"Say whether the motion carries.\"\"\"
    for_votes = sum(1 for vote in votes if vote == "for")
    return for_votes * 2 > len(votes)""",
    variant_four="""def passes(votes):
    \"\"\"Say whether the motion carries.\"\"\"
    cast = [vote for vote in votes if vote in ("for", "against")]
    for_votes = sum(1 for vote in cast if vote == "for")
    return for_votes * 2 >= len(cast)""",
    visible_test=_test_module(
        "vote_threshold",
        "Published contract for deciding the motion.",
        """
def test_a_majority_carries_the_motion() -> None:
    assert passes(["for", "for", "against"]) is True


def test_a_room_against_it_does_not() -> None:
    assert passes(["against", "against"]) is False
""",
        imports="from vote_threshold import passes\n",
    ),
    hidden_test=_test_module(
        "vote_threshold",
        "The part of the contract the published tests do not state.",
        """
def test_a_majority_carries_the_motion() -> None:
    assert passes(["for", "for", "against"]) is True


def test_a_tie_does_not_carry_the_motion() -> None:
    assert passes(["for", "against"]) is False


def test_an_abstention_is_not_a_vote_cast() -> None:
    assert passes(["for", "abstain", "abstain"]) is True
""",
        imports="from vote_threshold import passes\n",
    ),
)

_G048 = D2TaskSpec(
    template_id="d7_transform.priority_arrange",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7-transform-priority-arrange",
    module="priority_arrange",
    module_doc="Putting the named names first, and keeping everybody else.",
    issue=(
        "arrange() is documented to bring the named names to the front in the order the list "
        "names them, and to keep everybody else behind them. Callers report the named names "
        "coming back in whatever order they happened to be in already, and the unnamed ones "
        "disappearing from the arrangement altogether."
    ),
    expected=(
        "arrange(rows, priority) returns the names with those the priority list names first, in "
        "the priority list's order, followed by the names it does not mention, in the order "
        "they arrived."
    ),
    baseline_reason=(
        "it walks the rows and keeps the ones the priority list mentions, which orders them by "
        "the rows rather than by the list, and drops everybody the list does not mention"
    ),
    edge_cases=(
        "the named names come in the priority list's order",
        "the names nobody prioritised are kept behind them",
    ),
    baseline="""def arrange(rows, priority):
    \"\"\"Arrange the names, prioritised ones first.\"\"\"
    return [name for name in rows if name in priority]""",
    variant_one="""def arrange(rows, priority):
    \"\"\"Arrange the names, prioritised ones first.\"\"\"
    named = [name for name in priority if name in rows]
    rest = [name for name in rows if name not in priority]
    return named + rest""",
    variant_two="""def arrange(rows, priority):
    \"\"\"Arrange the names, prioritised ones first.\"\"\"
    ranked = []
    for wanted in priority:
        for name in rows:
            if name == wanted:
                ranked.append(name)
    for name in rows:
        if name not in priority:
            ranked.append(name)
    return ranked""",
    variant_three="""def arrange(rows, priority):
    \"\"\"Arrange the names, prioritised ones first.\"\"\"
    return [name for name in priority if name in rows]""",
    variant_four="""def arrange(rows, priority):
    \"\"\"Arrange the names, prioritised ones first.\"\"\"
    named = [name for name in rows if name in priority]
    rest = [name for name in rows if name not in priority]
    return named + rest""",
    visible_test=_test_module(
        "priority_arrange",
        "Published contract for the arrangement.",
        """
def test_names_already_in_order_stay_in_order() -> None:
    assert arrange(["a", "b"], ["a", "b"]) == ["a", "b"]


def test_nothing_to_arrange_arranges_to_nothing() -> None:
    assert arrange([], ["a"]) == []
""",
        imports="from priority_arrange import arrange\n",
    ),
    hidden_test=_test_module(
        "priority_arrange",
        "The part of the contract the published tests do not state.",
        """
def test_names_already_in_order_stay_in_order() -> None:
    assert arrange(["a", "b"], ["a", "b"]) == ["a", "b"]


def test_the_named_names_come_in_the_priority_order() -> None:
    assert arrange(["b", "a"], ["a", "b"]) == ["a", "b"]


def test_the_names_nobody_prioritised_are_kept_behind() -> None:
    assert arrange(["a", "z"], ["a"]) == ["a", "z"]
""",
        imports="from priority_arrange import arrange\n",
    ),
)

_G049 = D2TaskSpec(
    template_id="d7_error.partial_collect",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d7-error-partial-collect",
    module="partial_collect",
    module_doc="Gathering from every source, and knowing when there is nothing to report.",
    issue=(
        "collect() is documented to ask every source even when one of them fails, and to treat "
        "a run where every source failed as a failure rather than as an empty answer. Callers "
        "report the gather stopping at the first bad source, and an empty result arriving with "
        "no sign that nothing worked."
    ),
    expected=(
        "collect(sources) asks each (name, source) in turn and returns (values, failures): what "
        "answered, and (name, message) for what raised. A source that fails does not stop the "
        "others, and a run in which every source failed raises RuntimeError instead."
    ),
    baseline_reason=(
        "it breaks out of the gather at the first source that raises, and it reports a run "
        "where nothing answered as an empty result rather than as a failure"
    ),
    edge_cases=(
        "a failing source does not stop the sources after it",
        "a run in which every source failed is itself a failure",
    ),
    baseline="""def collect(sources):
    \"\"\"Gather from every source, recording what failed.\"\"\"
    values = []
    failures = []
    for name, source in sources:
        try:
            values.append(source())
        except Exception as error:
            failures.append((name, str(error)))
            break
    return values, failures""",
    variant_one="""def collect(sources):
    \"\"\"Gather from every source, recording what failed.\"\"\"
    values = []
    failures = []
    for name, source in sources:
        try:
            values.append(source())
        except Exception as error:
            failures.append((name, str(error)))
    if failures and not values:
        raise RuntimeError("every source failed")
    return values, failures""",
    variant_two="""def collect(sources):
    \"\"\"Gather from every source, recording what failed.\"\"\"
    answered = []
    broken = []
    for name, source in sources:
        try:
            answer = source()
        except Exception as error:
            broken.append((name, str(error)))
            continue
        answered.append(answer)
    if broken and len(broken) == len(sources):
        raise RuntimeError("every source failed")
    return answered, broken""",
    variant_three="""def collect(sources):
    \"\"\"Gather from every source, recording what failed.\"\"\"
    values = []
    failures = []
    for name, source in sources:
        try:
            values.append(source())
        except Exception as error:
            failures.append((name, str(error)))
    return values, failures""",
    variant_four="""def collect(sources):
    \"\"\"Gather from every source, recording what failed.\"\"\"
    values = []
    failures = []
    for name, source in sources:
        try:
            values.append(source())
        except Exception as error:
            failures.append((name, str(error)))
            break
    if failures and not values:
        raise RuntimeError("every source failed")
    return values, failures""",
    visible_test=_test_module(
        "partial_collect",
        "Published contract for gathering from the sources.",
        """
def test_every_source_answering_is_gathered() -> None:
    assert collect([("a", lambda: 1), ("b", lambda: 2)]) == ([1, 2], [])


def test_no_sources_at_all_gather_nothing() -> None:
    assert collect([]) == ([], [])
""",
        imports="from partial_collect import collect\n",
    ),
    hidden_test=_test_module(
        "partial_collect",
        "The part of the contract the published tests do not state.",
        """
import pytest


def _boom():
    raise ValueError("boom")


def test_every_source_answering_is_gathered() -> None:
    assert collect([("a", lambda: 1), ("b", lambda: 2)]) == ([1, 2], [])


def test_a_failing_source_does_not_stop_the_ones_after_it() -> None:
    assert collect([("a", _boom), ("b", lambda: 2)]) == ([2], [("a", "boom")])


def test_a_run_where_everything_failed_is_a_failure() -> None:
    with pytest.raises(RuntimeError):
        collect([("a", _boom)])
""",
        imports="from partial_collect import collect\n",
    ),
)

_G050 = D2TaskSpec(
    template_id="d7_parsing.signed_amount",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7-parsing-signed-amount",
    module="signed_amount",
    module_doc="Reading an amount off a statement, in the notation statements are written in.",
    issue=(
        "parse_amount() is documented to read the notation an accounts statement uses: a "
        "negative amount in brackets, and thousands grouped with commas. Callers report both "
        "forms being rejected as though they were not numbers, which is every amount on a "
        "statement above a thousand and every amount below nothing."
    ),
    expected=(
        "parse_amount(text) returns the amount in cents. An amount wrapped in brackets is "
        "negative, commas grouping the thousands are ignored, and text that is not an amount "
        "at all raises ValueError."
    ),
    baseline_reason=(
        "it hands the text straight to the number reader, which knows nothing about brackets "
        "standing for a minus sign and nothing about commas grouping the thousands"
    ),
    edge_cases=(
        "an amount in brackets is negative",
        "commas grouping the thousands are ignored",
    ),
    baseline="""def parse_amount(text):
    \"\"\"Read a statement amount into cents.\"\"\"
    return int(round(float(text.strip()) * 100))""",
    variant_one="""def parse_amount(text):
    \"\"\"Read a statement amount into cents.\"\"\"
    body = text.strip()
    negative = body.startswith("(") and body.endswith(")")
    if negative:
        body = body[1:-1]
    value = int(round(float(body.replace(",", "")) * 100))
    return -value if negative else value""",
    variant_two="""def parse_amount(text):
    \"\"\"Read a statement amount into cents.\"\"\"
    body = text.strip().replace(",", "")
    sign = 1
    if body[:1] == "(" and body[-1:] == ")":
        sign = -1
        body = body[1:-1]
    return sign * int(round(float(body) * 100))""",
    variant_three="""def parse_amount(text):
    \"\"\"Read a statement amount into cents.\"\"\"
    body = text.strip()
    negative = body.startswith("(") and body.endswith(")")
    if negative:
        body = body[1:-1]
    value = int(round(float(body) * 100))
    return -value if negative else value""",
    variant_four="""def parse_amount(text):
    \"\"\"Read a statement amount into cents.\"\"\"
    return int(round(float(text.strip().replace(",", "")) * 100))""",
    visible_test=_test_module(
        "signed_amount",
        "Published contract for reading a statement amount.",
        """
import pytest


def test_a_plain_amount_reads_as_cents() -> None:
    assert parse_amount("12.34") == 1234


def test_something_that_is_not_an_amount_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_amount("not money")
""",
        imports="from signed_amount import parse_amount\n",
    ),
    hidden_test=_test_module(
        "signed_amount",
        "The part of the contract the published tests do not state.",
        """
def test_a_plain_amount_reads_as_cents() -> None:
    assert parse_amount("12.34") == 1234


def test_an_amount_in_brackets_is_negative() -> None:
    assert parse_amount("(12.34)") == -1234


def test_commas_grouping_the_thousands_are_ignored() -> None:
    assert parse_amount("1,234.50") == 123450
""",
        imports="from signed_amount import parse_amount\n",
    ),
)

_G051 = D2TaskSpec(
    template_id="d7_state.versioned_apply",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d7-state-versioned-apply",
    module="versioned_apply",
    module_doc="Applying a change to a record somebody else may have changed first.",
    issue=(
        "apply() is documented to refuse a change written against a version that has moved on, "
        "and to leave the version alone when the change asks for what the record already says. "
        "Callers report stale changes overwriting newer ones, and versions climbing on retries "
        "that changed nothing at all."
    ),
    expected=(
        "apply(record, change, expected_version) returns the record with the change applied and "
        "its version raised by one. A change asking for what the record already says leaves the "
        "record exactly as it was, version included, and a version that has moved on since the "
        "change was written raises ValueError."
    ),
    baseline_reason=(
        "it applies the change and raises the version whatever the change asks for, and it "
        "never compares the version it was handed with the version on the record"
    ),
    edge_cases=(
        "a change that changes nothing leaves the version alone",
        "a change written against a version that has moved on is refused",
    ),
    baseline="""def apply(record, change, expected_version):
    \"\"\"Apply a change to a versioned record.\"\"\"
    updated = dict(record)
    updated.update(change)
    updated["version"] = record["version"] + 1
    return updated""",
    variant_one="""def apply(record, change, expected_version):
    \"\"\"Apply a change to a versioned record.\"\"\"
    if record["version"] != expected_version:
        raise ValueError("version has moved on: " + str(expected_version))
    if all(record.get(key) == value for key, value in change.items()):
        return dict(record)
    updated = dict(record)
    updated.update(change)
    updated["version"] = record["version"] + 1
    return updated""",
    variant_two="""def apply(record, change, expected_version):
    \"\"\"Apply a change to a versioned record.\"\"\"
    if expected_version != record["version"]:
        raise ValueError("version has moved on: " + str(expected_version))
    moved = {key: value for key, value in change.items() if record.get(key) != value}
    if not moved:
        return dict(record)
    return {**record, **moved, "version": record["version"] + 1}""",
    variant_three="""def apply(record, change, expected_version):
    \"\"\"Apply a change to a versioned record.\"\"\"
    if all(record.get(key) == value for key, value in change.items()):
        return dict(record)
    updated = dict(record)
    updated.update(change)
    updated["version"] = record["version"] + 1
    return updated""",
    variant_four="""def apply(record, change, expected_version):
    \"\"\"Apply a change to a versioned record.\"\"\"
    if record["version"] != expected_version:
        raise ValueError("version has moved on: " + str(expected_version))
    updated = dict(record)
    updated.update(change)
    updated["version"] = record["version"] + 1
    return updated""",
    visible_test=_test_module(
        "versioned_apply",
        "Published contract for applying a change.",
        """
def test_a_change_is_applied_and_the_version_rises() -> None:
    record = {"version": 1, "name": "a"}
    assert apply(record, {"name": "b"}, 1) == {"version": 2, "name": "b"}


def test_the_version_rises_by_exactly_one() -> None:
    record = {"version": 3, "name": "a"}
    assert apply(record, {"name": "c"}, 3)["version"] == 4
""",
        imports="from versioned_apply import apply\n",
    ),
    hidden_test=_test_module(
        "versioned_apply",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_a_change_is_applied_and_the_version_rises() -> None:
    record = {"version": 1, "name": "a"}
    assert apply(record, {"name": "b"}, 1) == {"version": 2, "name": "b"}


def test_a_change_that_changes_nothing_leaves_the_version_alone() -> None:
    record = {"version": 1, "name": "a"}
    assert apply(record, {"name": "a"}, 1) == {"version": 1, "name": "a"}


def test_a_version_that_has_moved_on_is_refused() -> None:
    with pytest.raises(ValueError):
        apply({"version": 2, "name": "a"}, {"name": "b"}, 1)
""",
        imports="from versioned_apply import apply\n",
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
)

__all__ = ["D7_CERTIFICATION_SPECS", "D2TaskSpec", "RealityTaskFamily", "_test_module"]
