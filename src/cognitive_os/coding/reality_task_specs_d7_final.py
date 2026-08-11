"""Replacement groups for the two carried final roles, authored under S21D7-038.

W3 opened the final roles for the first time in five sprints and found four authored bodies the
source canonicaliser refuses: three bind a name through `hasattr` and one uses an assignment
expression the frozen grammar does not cover. The bodies predate the reflection ban; every sprint
since recomputed the carried digests, found them unchanged, and recorded the roles as intact.
They were intact. Nothing had ever tried to encode them.

`sprint-21d7-final-role-audit.json` is that audit and carries the authorisation §3.5 reserves for
a role that fails one. These four groups are the repair, and they exist so the frozen counts do
not move: final A stays 30 groups and 120 outcomes, final B stays 30 and 120.

The shape is `D2TaskSpec`, unchanged, under the same authoring contract as every corpus wave:

- the **baseline** passes the visible suite and fails the hidden one;
- **variant one** and **variant two** repair the contract by materially different routes;
- **variant three** fixes the first declared edge case only, **variant four** the second only.

Every module name here was checked against the released corpus before its bodies were written,
and every body binds its names locally — which is the rule the groups they replace break.

**What this module cannot claim.** These four were authored after the selection's numbers were
read. The bodies themselves are no less blind than any other corpus — the class never sees them
before execution and the labels come from the hidden verifier — but the choice of what to author
was made by someone who had seen the cell. A final batch is supposed to be the least contaminated
evidence in the sprint, and the audit record says this plainly rather than arguing it away.
"""

from __future__ import annotations

from cognitive_os.domain.reality import RealityTaskFamily

from .reality_task_specs import _test_module
from .reality_task_specs_d2 import D2TaskSpec

# --------------------------------------------------------------- final A: boundary and collections

_F001 = D2TaskSpec(
    template_id="d7f_boundary.ferry_runs",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d7f-boundary-ferry-runs",
    module="ferry_runs",
    module_doc="Filling ferry runs up to a weight ceiling, in the order vehicles arrive.",
    issue=(
        "plan() is documented to fill the current run while the next vehicle still fits. "
        "Operators report that a vehicle which exactly uses up the remaining capacity is sent "
        "to the next run instead, and that a vehicle heavier than the whole ceiling vanishes "
        "from the plan rather than sailing on its own."
    ),
    expected=(
        "plan(weights, ceiling) returns the runs in order, each a list of weights in arrival "
        "order. A vehicle joins the current run when the run's total plus its weight is at most "
        "the ceiling, and starts a new run otherwise. A vehicle heavier than the ceiling travels "
        "alone on a run of its own. No weights are dropped and an empty list plans no runs."
    ),
    baseline_reason=(
        "it compares the would-be total against the ceiling strictly, so a run is closed one "
        "vehicle early, and it skips any vehicle it cannot fit at all"
    ),
    edge_cases=(
        "a vehicle that exactly fills the remaining capacity joins the current run",
        "a vehicle heavier than the ceiling sails alone instead of being dropped",
    ),
    baseline='''def plan(weights, ceiling):
    """Fill ferry runs up to `ceiling`."""
    runs = []
    current = []
    total = 0
    for weight in weights:
        if weight > ceiling:
            continue
        if current and total + weight >= ceiling:
            runs.append(current)
            current = []
            total = 0
        current.append(weight)
        total += weight
    if current:
        runs.append(current)
    return runs''',
    variant_one='''def plan(weights, ceiling):
    """Fill ferry runs up to `ceiling`."""
    runs = []
    current = []
    total = 0
    for weight in weights:
        if weight > ceiling:
            if current:
                runs.append(current)
                current = []
                total = 0
            runs.append([weight])
            continue
        if current and total + weight > ceiling:
            runs.append(current)
            current = []
            total = 0
        current.append(weight)
        total += weight
    if current:
        runs.append(current)
    return runs''',
    variant_two='''def plan(weights, ceiling):
    """Fill ferry runs up to `ceiling`."""
    runs = []
    for weight in weights:
        if weight > ceiling:
            runs.append([weight])
            continue
        placed = False
        if runs and sum(runs[-1]) + weight <= ceiling and sum(runs[-1]) <= ceiling:
            runs[-1].append(weight)
            placed = True
        if not placed:
            runs.append([weight])
    return runs''',
    variant_three='''def plan(weights, ceiling):
    """Fill ferry runs up to `ceiling`."""
    runs = []
    current = []
    total = 0
    for weight in weights:
        if weight > ceiling:
            continue
        if current and total + weight > ceiling:
            runs.append(current)
            current = []
            total = 0
        current.append(weight)
        total += weight
    if current:
        runs.append(current)
    return runs''',
    variant_four='''def plan(weights, ceiling):
    """Fill ferry runs up to `ceiling`."""
    runs = []
    current = []
    total = 0
    for weight in weights:
        if weight > ceiling:
            if current:
                runs.append(current)
                current = []
                total = 0
            runs.append([weight])
            continue
        if current and total + weight >= ceiling:
            runs.append(current)
            current = []
            total = 0
        current.append(weight)
        total += weight
    if current:
        runs.append(current)
    return runs''',
    visible_test=_test_module(
        "ferry_runs",
        "Published contract for filling ferry runs.",
        """
def test_light_vehicles_share_one_run() -> None:
    assert plan([1, 1], 5) == [[1, 1]]


def test_a_vehicle_that_does_not_fit_starts_the_next_run() -> None:
    assert plan([4, 4], 5) == [[4], [4]]


def test_nothing_to_carry_plans_no_runs() -> None:
    assert plan([], 5) == []
""",
        imports="from ferry_runs import plan\n",
    ),
    hidden_test=_test_module(
        "ferry_runs",
        "The part of the contract the published tests do not state.",
        """
def test_light_vehicles_share_one_run() -> None:
    assert plan([1, 1], 5) == [[1, 1]]


def test_a_vehicle_filling_the_remaining_capacity_joins_the_run() -> None:
    assert plan([3, 2], 5) == [[3, 2]]


def test_an_oversized_vehicle_sails_alone() -> None:
    assert plan([9, 1], 5) == [[9], [1]]
""",
        imports="from ferry_runs import plan\n",
    ),
)

# ------------------------------------------------------------------ final A: parsing and validation

_F002 = D2TaskSpec(
    template_id="d7f_parsing.mailbox_address",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d7f-parsing-mailbox-address",
    module="mailbox_address",
    module_doc="Reading a display name and an address out of a mailbox line.",
    issue=(
        "read() is documented to accept both a bare address and one behind a display name. "
        "Callers report that a bare address comes back empty, and that a display name made of "
        "more than one word loses everything after the first."
    ),
    expected=(
        "read(text) returns (name, address). With a display name written before an address in "
        "angle brackets, the name is everything before the bracket with surrounding whitespace "
        "removed, and the address is what the brackets hold. A bare address with no brackets "
        "returns an empty name and that address. Whitespace around the whole line is ignored."
    ),
    baseline_reason=(
        "it reads the display name as the first whitespace-separated word, and it answers with "
        "two empty strings when there is no angle bracket to look between"
    ),
    edge_cases=(
        "a bare address with no brackets keeps the address and returns an empty name",
        "a display name of several words survives whole",
    ),
    baseline='''def read(text):
    """Read (name, address) out of a mailbox line."""
    line = text.strip()
    if "<" not in line:
        return ("", "")
    before, rest = line.split("<", 1)
    address = rest.split(">", 1)[0]
    words = before.split()
    name = words[0] if words else ""
    return (name, address)''',
    variant_one='''def read(text):
    """Read (name, address) out of a mailbox line."""
    line = text.strip()
    if "<" not in line:
        return ("", line)
    before, rest = line.split("<", 1)
    address = rest.split(">", 1)[0]
    return (before.strip(), address)''',
    variant_two='''def read(text):
    """Read (name, address) out of a mailbox line."""
    line = text.strip()
    opened = line.find("<")
    if opened < 0:
        return ("", line)
    closed = line.find(">", opened)
    end = len(line) if closed < 0 else closed
    return (line[:opened].strip(), line[opened + 1 : end])''',
    variant_three='''def read(text):
    """Read (name, address) out of a mailbox line."""
    line = text.strip()
    if "<" not in line:
        return ("", line)
    before, rest = line.split("<", 1)
    address = rest.split(">", 1)[0]
    words = before.split()
    name = words[0] if words else ""
    return (name, address)''',
    variant_four='''def read(text):
    """Read (name, address) out of a mailbox line."""
    line = text.strip()
    if "<" not in line:
        return ("", "")
    before, rest = line.split("<", 1)
    address = rest.split(">", 1)[0]
    return (before.strip(), address)''',
    visible_test=_test_module(
        "mailbox_address",
        "Published contract for reading a mailbox line.",
        """
def test_a_one_word_name_and_an_address() -> None:
    assert read("Ann <ann@example.test>") == ("Ann", "ann@example.test")


def test_surrounding_whitespace_is_ignored() -> None:
    assert read("  Ann <ann@example.test>  ") == ("Ann", "ann@example.test")
""",
        imports="from mailbox_address import read\n",
    ),
    hidden_test=_test_module(
        "mailbox_address",
        "The part of the contract the published tests do not state.",
        """
def test_a_one_word_name_and_an_address() -> None:
    assert read("Ann <ann@example.test>") == ("Ann", "ann@example.test")


def test_a_bare_address_keeps_the_address() -> None:
    assert read("ann@example.test") == ("", "ann@example.test")


def test_a_name_of_several_words_survives_whole() -> None:
    assert read("Ann Lee <ann@example.test>") == ("Ann Lee", "ann@example.test")
""",
        imports="from mailbox_address import read\n",
    ),
)

# ----------------------------------------------------------------- final A: data transformation

_F003 = D2TaskSpec(
    template_id="d7f_transform.pledge_totals",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7f-transform-pledge-totals",
    module="pledge_totals",
    module_doc="Adding up what each member pledged, in the order they first pledged.",
    issue=(
        "totals() is documented to keep members in the order they first appear and to leave out "
        "anyone whose pledges cancel to nothing. Callers report that the answer comes back "
        "sorted by name, and that a member who pledged and then withdrew still appears with a "
        "zero beside them."
    ),
    expected=(
        "totals(pledges) takes (member, amount) pairs and returns a mapping from member to the "
        "sum of their amounts, in the order each member first pledged. A member whose amounts "
        "sum to zero is left out entirely. No pledges at all returns an empty mapping."
    ),
    baseline_reason=(
        "it builds the answer by walking the members in sorted order, and it writes every "
        "member it saw including the ones that cancelled out"
    ),
    edge_cases=(
        "members keep the order they first pledged in rather than alphabetical order",
        "a member whose amounts cancel to zero is left out",
    ),
    baseline='''def totals(pledges):
    """Total each member's pledges."""
    sums = {}
    for member, amount in pledges:
        sums[member] = sums.get(member, 0) + amount
    answer = {}
    for member in sorted(sums):
        answer[member] = sums[member]
    return answer''',
    variant_one='''def totals(pledges):
    """Total each member's pledges."""
    sums = {}
    order = []
    for member, amount in pledges:
        if member not in sums:
            order.append(member)
            sums[member] = 0
        sums[member] = sums[member] + amount
    answer = {}
    for member in order:
        if sums[member] != 0:
            answer[member] = sums[member]
    return answer''',
    variant_two='''def totals(pledges):
    """Total each member's pledges."""
    answer = {}
    for member, amount in pledges:
        answer[member] = answer.get(member, 0) + amount
    for member in [name for name in answer if answer[name] == 0]:
        del answer[member]
    return answer''',
    variant_three='''def totals(pledges):
    """Total each member's pledges."""
    sums = {}
    order = []
    for member, amount in pledges:
        if member not in sums:
            order.append(member)
            sums[member] = 0
        sums[member] = sums[member] + amount
    answer = {}
    for member in order:
        answer[member] = sums[member]
    return answer''',
    variant_four='''def totals(pledges):
    """Total each member's pledges."""
    sums = {}
    for member, amount in pledges:
        sums[member] = sums.get(member, 0) + amount
    answer = {}
    for member in sorted(sums):
        if sums[member] != 0:
            answer[member] = sums[member]
    return answer''',
    visible_test=_test_module(
        "pledge_totals",
        "Published contract for totalling pledges.",
        """
def test_two_members_in_alphabetical_arrival_order() -> None:
    assert list(totals([("ana", 1), ("bo", 2)]).items()) == [("ana", 1), ("bo", 2)]


def test_repeated_pledges_add_up() -> None:
    assert list(totals([("ana", 1), ("ana", 2)]).items()) == [("ana", 3)]


def test_nothing_pledged_totals_nothing() -> None:
    assert totals([]) == {}
""",
        imports="from pledge_totals import totals\n",
    ),
    hidden_test=_test_module(
        "pledge_totals",
        "The part of the contract the published tests do not state.",
        """
def test_repeated_pledges_add_up() -> None:
    assert list(totals([("ana", 1), ("ana", 2)]).items()) == [("ana", 3)]


def test_members_keep_the_order_they_first_pledged_in() -> None:
    assert list(totals([("bo", 1), ("ana", 2)]).items()) == [("bo", 1), ("ana", 2)]


def test_a_member_who_cancelled_out_is_left_out() -> None:
    assert list(totals([("ana", 1), ("ana", -1), ("bo", 2)]).items()) == [("bo", 2)]
""",
        imports="from pledge_totals import totals\n",
    ),
)

# ----------------------------------------------------------------- final B: data transformation

_F004 = D2TaskSpec(
    template_id="d7f_transform.tariff_steps",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d7f-transform-tariff-steps",
    module="tariff_steps",
    module_doc="Charging a usage figure against a stepped tariff, and saying how far it reached.",
    issue=(
        "charge() is documented to report the cost together with how many steps the usage "
        "actually reached into. Callers report that a zero reading is counted as having reached "
        "the first step, and that usage beyond the last limit stops being charged instead of "
        "continuing at the last rate."
    ),
    expected=(
        "charge(usage, steps) takes (limit, rate) pairs in increasing limit order and returns "
        "(total, entered). A step is entered when the usage is strictly above the step's lower "
        "bound, which is the previous limit and zero for the first step; each entered step "
        "prices the part of the usage inside it. Usage above the last limit is priced at the "
        "last step's rate and enters no further step."
    ),
    baseline_reason=(
        "it decides it has run out of usage only once the lower bound is strictly past it, so a "
        "zero reading still enters the first step, and it stops charging at the last limit"
    ),
    edge_cases=(
        "a zero reading enters no step at all",
        "usage beyond the last limit is charged at the last rate",
    ),
    baseline='''def charge(usage, steps):
    """Price `usage` against a stepped tariff."""
    total = 0
    previous = 0
    entered = 0
    for limit, rate in steps:
        if previous > usage:
            break
        entered += 1
        inside = min(usage, limit) - previous
        total += inside * rate
        previous = limit
    return (total, entered)''',
    variant_one='''def charge(usage, steps):
    """Price `usage` against a stepped tariff."""
    total = 0
    previous = 0
    entered = 0
    last_rate = 0
    for limit, rate in steps:
        last_rate = rate
        if previous >= usage:
            break
        entered += 1
        inside = min(usage, limit) - previous
        total += inside * rate
        previous = limit
    if usage > previous:
        total += (usage - previous) * last_rate
    return (total, entered)''',
    variant_two='''def charge(usage, steps):
    """Price `usage` against a stepped tariff."""
    total = 0
    entered = 0
    lower = 0
    rate_here = 0
    for limit, rate in steps:
        rate_here = rate
        if usage > lower:
            entered += 1
            upper = limit if limit < usage else usage
            total += (upper - lower) * rate
        lower = limit
    if usage > lower:
        total += (usage - lower) * rate_here
    return (total, entered)''',
    variant_three='''def charge(usage, steps):
    """Price `usage` against a stepped tariff."""
    total = 0
    previous = 0
    entered = 0
    for limit, rate in steps:
        if previous >= usage:
            break
        entered += 1
        inside = min(usage, limit) - previous
        total += inside * rate
        previous = limit
    return (total, entered)''',
    variant_four='''def charge(usage, steps):
    """Price `usage` against a stepped tariff."""
    total = 0
    previous = 0
    entered = 0
    last_rate = 0
    for limit, rate in steps:
        last_rate = rate
        if previous > usage:
            break
        entered += 1
        inside = min(usage, limit) - previous
        total += inside * rate
        previous = limit
    if usage > previous:
        total += (usage - previous) * last_rate
    return (total, entered)''',
    visible_test=_test_module(
        "tariff_steps",
        "Published contract for a stepped tariff.",
        """
def test_usage_inside_the_first_step() -> None:
    assert charge(3, [(10, 2), (20, 5)]) == (6, 1)


def test_usage_spanning_two_steps() -> None:
    assert charge(15, [(10, 2), (20, 5)]) == (45, 2)
""",
        imports="from tariff_steps import charge\n",
    ),
    hidden_test=_test_module(
        "tariff_steps",
        "The part of the contract the published tests do not state.",
        """
def test_usage_inside_the_first_step() -> None:
    assert charge(3, [(10, 2), (20, 5)]) == (6, 1)


def test_a_zero_reading_enters_no_step() -> None:
    assert charge(0, [(10, 2), (20, 5)]) == (0, 0)


def test_usage_beyond_the_last_limit_is_charged_at_the_last_rate() -> None:
    assert charge(25, [(10, 2), (20, 5)]) == (95, 2)
""",
        imports="from tariff_steps import charge\n",
    ),
)

#: The replacements, in the order the roles take them: the first three stand in for final A's
#: refused groups and the fourth for final B's.
D7_FINAL_A_REPLACEMENTS: tuple[D2TaskSpec, ...] = (_F001, _F002, _F003)
D7_FINAL_B_REPLACEMENTS: tuple[D2TaskSpec, ...] = (_F004,)
D7_FINAL_REPLACEMENT_SPECS: tuple[D2TaskSpec, ...] = (
    *D7_FINAL_A_REPLACEMENTS,
    *D7_FINAL_B_REPLACEMENTS,
)

#: The groups these replace, by role. Named here so the catalogue substitution cannot drift
#: from the audit that authorised it.
D7_FINAL_WITHDRAWN: dict[str, tuple[str, ...]] = {
    "final_a": ("d2-boundary-flatten", "d2-parsing-flags", "d2-transform-pluck"),
    "final_b": ("d2-transform-stringify",),
}
