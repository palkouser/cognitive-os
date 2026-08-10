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

D7_CERTIFICATION_SPECS: tuple[D2TaskSpec, ...] = (
    _G001,
    _G002,
    _G003,
    _G004,
)

__all__ = ["D7_CERTIFICATION_SPECS", "D2TaskSpec", "RealityTaskFamily", "_test_module"]
