"""The Sprint 21D2 task corpus, and the reason it is shaped differently from C3's.

C3's thirty tasks name their candidates `correct_narrow`, `correct_robust`, `incomplete_a` and
`incomplete_b`, and on all 120 D1 correction-ranking examples those names predicted the
verifier's answer without a single exception. A ranker fitted on that corpus learns the name.

Renaming the four to `recipe_alpha` … `recipe_delta` does not fix it. If `recipe_alpha` were
always the smallest correct edit, the new name would predict the label exactly as well as the
old one did — the oracle would simply be spelled differently. What removes it is binding recipe
to *variant* per task, deterministically, so that across the corpus each recipe is correct
about half the time and knowing the recipe tells you nothing.

So a D2 spec authors four variants and declares which of them repair the contract — the author
has to know that to write the task at all — and `recipe_binding()` decides which recipe carries
which variant, derived from the template ID. The declaration stays provenance: it is never a
feature, never reaches the fitted matrix, and the hidden verifier remains the only thing that
decides an outcome.

Every task keeps C3's recipe in the parts that make the corpus measurable: two independent edge
cases the visible tests do not state, a baseline that fails both while passing every visible
test, two variants that each fix one and miss the other, and two that fix both by materially
different routes. Nothing is parameterised — variants of one template would share an AST shape,
land in one near-clone group, and quietly shrink the corpus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256

from cognitive_os.domain.reality import (
    RealityCandidateStrategy,
    RealityTaskDifficulty,
    RealityTaskFamily,
)

from .reality_task_specs import _test_module

#: The four recipes, in the fixed order `recipe_binding` permutes.
D2_RECIPES: tuple[RealityCandidateStrategy, ...] = (
    RealityCandidateStrategy.RECIPE_ALPHA,
    RealityCandidateStrategy.RECIPE_BETA,
    RealityCandidateStrategy.RECIPE_GAMMA,
    RealityCandidateStrategy.RECIPE_DELTA,
)


@dataclass(frozen=True, slots=True)
class D2TaskSpec:
    """One repair task with four variants whose recipe binding is not their correctness.

    `variant_one` … `variant_four` are authored in a fixed order: the first two repair the
    contract, the last two each fix one edge case and miss the other. That order is an
    authoring convention and never reaches the corpus, because `recipe_binding` permutes it.
    """

    template_id: str
    family: RealityTaskFamily
    repository_group: str
    module: str
    module_doc: str
    issue: str
    expected: str
    baseline_reason: str
    baseline: str
    #: Repairs the contract, minimally.
    variant_one: str
    #: Repairs the contract, by a materially different route.
    variant_two: str
    #: Fixes the first edge case only.
    variant_three: str
    #: Fixes the second edge case only.
    variant_four: str
    visible_test: str
    hidden_test: str
    difficulty: RealityTaskDifficulty = RealityTaskDifficulty.SINGLE_EDIT
    imports: str = ""
    edge_cases: tuple[str, str] = field(default=("", ""))

    @property
    def variants(self) -> tuple[str, ...]:
        return (
            self.variant_one,
            self.variant_two,
            self.variant_three,
            self.variant_four,
        )

    @property
    def repairs_contract(self) -> tuple[bool, ...]:
        """Provenance only. Declared so the corpus can be audited, never so it can be fitted."""
        return (True, True, False, False)


#: How a C3 spec's four candidate bodies map onto the D2 authoring convention: two repairs
#: first, then the two partial fixes. Thirty C3 groups are inherited into D2's training
#: partition, and this order is what `variant_index` indexes into, in the sealed catalogue and
#: in the template registry alike. Stated once because two copies of it would be one drift away
#: from a catalogue that names a different body from the one that runs.
INHERITED_VARIANT_FIELDS: tuple[str, ...] = (
    "correct_narrow",
    "correct_robust",
    "incomplete_a",
    "incomplete_b",
)


def recipe_binding(template_id: str) -> tuple[RealityCandidateStrategy, ...]:
    """Which recipe carries which authored variant, for one task.

    Deterministic in the template ID, so the corpus regenerates identically, and different
    between tasks, so no recipe is correct more often than chance across the corpus. A fixed
    binding would put the C3 oracle back under new names.
    """
    digest = sha256(f"d2-recipe-binding:{template_id}".encode()).digest()
    remaining = list(D2_RECIPES)
    chosen: list[RealityCandidateStrategy] = []
    for index in range(len(D2_RECIPES)):
        chosen.append(remaining.pop(digest[index] % len(remaining)))
    return tuple(chosen)


def module_source(spec: D2TaskSpec, function_source: str) -> str:
    """One variant as a complete module.

    A local builder rather than the C3 `_module_source`: that one is typed against `TaskSpec`
    and a D2 spec only satisfies it by duck typing, which type-checks by accident at best.
    The output shape is identical, which is what actually has to hold.
    """
    header = f'"""{spec.module_doc}"""\n'
    if spec.imports:
        header += f"\n{spec.imports}\n"
    return f"{header}\n\n{function_source.strip()}\n"


def candidate_sources_for(
    spec: D2TaskSpec, source_path: str
) -> dict[RealityCandidateStrategy, dict[str, str]]:
    """Expand one spec into `{recipe: {path: source}}` under its own binding."""
    binding = recipe_binding(spec.template_id)
    return {
        recipe: {source_path: module_source(spec, variant)}
        for recipe, variant in zip(binding, spec.variants, strict=True)
    }


def recipe_is_repair(spec: D2TaskSpec) -> dict[RealityCandidateStrategy, bool]:
    """Provenance map for auditing: which recipe repaired the contract, for this task."""
    return dict(zip(recipe_binding(spec.template_id), spec.repairs_contract, strict=True))


# ------------------------------------------------------------------ probe cohort, S21D2-022

_D1 = D2TaskSpec(
    template_id="d2_boundary.rotate_left",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-rotation",
    module="sequence_rotation",
    module_doc="Rotating a sequence by a signed offset.",
    issue=(
        "rotate_left() is documented to rotate a sequence left by n places, wrapping around. "
        "Callers report a crash on empty input and wrong results when n exceeds the length."
    ),
    expected=(
        "rotate_left(items, n) returns items rotated left by n places for any integer n, "
        "returns an empty sequence unchanged, and wraps when n exceeds the length."
    ),
    baseline_reason="the modulo is missing and an empty sequence divides by zero",
    edge_cases=(
        "an empty sequence is returned unchanged",
        "an offset above the length wraps",
    ),
    baseline="""def rotate_left(items, n):
    \"\"\"Rotate `items` left by `n` places, wrapping around.\"\"\"
    return list(items[n:]) + list(items[:n])""",
    variant_one="""def rotate_left(items, n):
    \"\"\"Rotate `items` left by `n` places, wrapping around.\"\"\"
    if not items:
        return list(items)
    offset = n % len(items)
    return list(items[offset:]) + list(items[:offset])""",
    variant_two="""def rotate_left(items, n):
    \"\"\"Rotate `items` left by `n` places, wrapping around.\"\"\"
    from collections import deque

    rotated = deque(items)
    rotated.rotate(-n)
    return list(rotated)""",
    variant_three="""def rotate_left(items, n):
    \"\"\"Rotate `items` left by `n` places, wrapping around.\"\"\"
    if not items:
        return list(items)
    return list(items[n:]) + list(items[:n])""",
    variant_four="""def rotate_left(items, n):
    \"\"\"Rotate `items` left by `n` places, wrapping around.\"\"\"
    offset = n % len(items)
    return list(items[offset:]) + list(items[:offset])""",
    visible_test=_test_module(
        "sequence_rotation",
        "Published contract for sequence rotation.",
        """
def test_rotate_by_one() -> None:
    assert rotate_left([1, 2, 3], 1) == [2, 3, 1]


def test_rotate_by_zero() -> None:
    assert rotate_left([1, 2, 3], 0) == [1, 2, 3]
""",
        imports="from sequence_rotation import rotate_left\n",
    ),
    hidden_test=_test_module(
        "sequence_rotation",
        "The part of the contract the published tests do not state.",
        """
def test_rotate_by_one() -> None:
    assert rotate_left([1, 2, 3], 1) == [2, 3, 1]


def test_an_empty_sequence_is_returned_unchanged() -> None:
    assert rotate_left([], 3) == []


def test_an_offset_above_the_length_wraps() -> None:
    assert rotate_left([1, 2, 3], 4) == [2, 3, 1]
""",
        imports="from sequence_rotation import rotate_left\n",
    ),
)

_D2 = D2TaskSpec(
    template_id="d2_parsing.strip_prefix",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-prefixes",
    module="prefix_tools",
    module_doc="Removing a declared prefix from a label.",
    issue=(
        "strip_prefix() is documented to remove a prefix when present and to return the label "
        "untouched otherwise. Callers report that it removes characters from labels that do "
        "not carry the prefix, and that an empty prefix truncates the label."
    ),
    expected=(
        "strip_prefix(label, prefix) removes prefix only when label starts with it, returns "
        "label unchanged otherwise, and treats an empty prefix as removing nothing."
    ),
    baseline_reason="it slices by prefix length without checking that the prefix is present",
    edge_cases=(
        "a label without the prefix is unchanged",
        "an empty prefix removes nothing",
    ),
    baseline="""def strip_prefix(label, prefix):
    \"\"\"Return `label` without `prefix`, or unchanged when it is not present.\"\"\"
    return label[len(prefix):]""",
    variant_one="""def strip_prefix(label, prefix):
    \"\"\"Return `label` without `prefix`, or unchanged when it is not present.\"\"\"
    if not prefix or not label.startswith(prefix):
        return label
    return label[len(prefix):]""",
    variant_two="""def strip_prefix(label, prefix):
    \"\"\"Return `label` without `prefix`, or unchanged when it is not present.\"\"\"
    return label.removeprefix(prefix) if prefix else label""",
    variant_three="""def strip_prefix(label, prefix):
    \"\"\"Return `label` without `prefix`, or unchanged when it is not present.\"\"\"
    if prefix and not label.startswith(prefix):
        return label
    return label[len(prefix) or 1:]""",
    variant_four="""def strip_prefix(label, prefix):
    \"\"\"Return `label` without `prefix`, or unchanged when it is not present.\"\"\"
    if not prefix:
        return label
    return label[len(prefix):]""",
    visible_test=_test_module(
        "prefix_tools",
        "Published contract for prefix removal.",
        """
def test_removes_a_present_prefix() -> None:
    assert strip_prefix("app-name", "app-") == "name"


def test_removes_a_longer_prefix() -> None:
    assert strip_prefix("service-db", "service-") == "db"
""",
        imports="from prefix_tools import strip_prefix\n",
    ),
    hidden_test=_test_module(
        "prefix_tools",
        "The part of the contract the published tests do not state.",
        """
def test_removes_a_present_prefix() -> None:
    assert strip_prefix("app-name", "app-") == "name"


def test_a_label_without_the_prefix_is_unchanged() -> None:
    assert strip_prefix("name", "app-") == "name"


def test_an_empty_prefix_removes_nothing() -> None:
    assert strip_prefix("name", "") == "name"
""",
        imports="from prefix_tools import strip_prefix\n",
    ),
)

_D3 = D2TaskSpec(
    template_id="d2_numeric.safe_ratio",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-ratios",
    module="ratio_math",
    module_doc="Ratios that have to survive a zero denominator.",
    issue=(
        "safe_ratio() is documented to return the ratio of two numbers, falling back to the "
        "caller's default when the denominator is zero. Callers report a crash on a zero "
        "denominator and a wrong sign when both arguments are negative."
    ),
    expected=(
        "safe_ratio(a, b, default) returns a / b for any non-zero b, including negative "
        "values, and returns default when b is zero."
    ),
    baseline_reason="it divides unconditionally and takes the absolute value of the result",
    edge_cases=(
        "a zero denominator returns the default",
        "two negative arguments give a positive",
    ),
    baseline="""def safe_ratio(a, b, default=0.0):
    \"\"\"Return `a / b`, or `default` when `b` is zero.\"\"\"
    return abs(a / b)""",
    variant_one="""def safe_ratio(a, b, default=0.0):
    \"\"\"Return `a / b`, or `default` when `b` is zero.\"\"\"
    if b == 0:
        return default
    return a / b""",
    variant_two="""def safe_ratio(a, b, default=0.0):
    \"\"\"Return `a / b`, or `default` when `b` is zero.\"\"\"
    try:
        return a / b
    except ZeroDivisionError:
        return default""",
    variant_three="""def safe_ratio(a, b, default=0.0):
    \"\"\"Return `a / b`, or `default` when `b` is zero.\"\"\"
    if b == 0:
        return default
    return abs(a / b)""",
    variant_four="""def safe_ratio(a, b, default=0.0):
    \"\"\"Return `a / b`, or `default` when `b` is zero.\"\"\"
    return a / b""",
    visible_test=_test_module(
        "ratio_math",
        "Published contract for safe ratios.",
        """
def test_a_simple_ratio() -> None:
    assert safe_ratio(6, 3) == 2


def test_a_fractional_ratio() -> None:
    assert safe_ratio(1, 4) == 0.25
""",
        imports="from ratio_math import safe_ratio\n",
    ),
    hidden_test=_test_module(
        "ratio_math",
        "The part of the contract the published tests do not state.",
        """
def test_a_simple_ratio() -> None:
    assert safe_ratio(6, 3) == 2


def test_a_zero_denominator_returns_the_default() -> None:
    assert safe_ratio(6, 0, -1.0) == -1.0


def test_two_negative_arguments_give_a_positive() -> None:
    assert safe_ratio(-6, -3) == 2


def test_a_negative_numerator_stays_negative() -> None:
    assert safe_ratio(-6, 3) == -2
""",
        imports="from ratio_math import safe_ratio\n",
    ),
)

_D4 = D2TaskSpec(
    template_id="d2_state.release_slot",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-slot-release",
    module="slot_release",
    module_doc="Releasing a slot that may already be free.",
    issue=(
        "release() is documented to free a held slot and to be safe to call twice. Callers "
        "report a crash when releasing an unknown slot and a count that drifts below zero "
        "when the same slot is released repeatedly."
    ),
    expected=(
        "release(state, slot) frees the slot when held, is a no-op for an unknown or already "
        "free slot, and never lets the held count fall below zero."
    ),
    baseline_reason="it removes the slot unconditionally and always decrements the count",
    edge_cases=(
        "releasing an unknown slot is a no-op",
        "the held count never goes negative",
    ),
    baseline="""def release(state, slot):
    \"\"\"Free `slot` in `state`. Safe to call more than once.\"\"\"
    state["held"].remove(slot)
    state["count"] -= 1
    return state""",
    variant_one="""def release(state, slot):
    \"\"\"Free `slot` in `state`. Safe to call more than once.\"\"\"
    if slot in state["held"]:
        state["held"].remove(slot)
        state["count"] -= 1
    return state""",
    variant_two="""def release(state, slot):
    \"\"\"Free `slot` in `state`. Safe to call more than once.\"\"\"
    held = [item for item in state["held"] if item != slot]
    state["count"] = len(held)
    state["held"] = held
    return state""",
    variant_three="""def release(state, slot):
    \"\"\"Free `slot` in `state`. Safe to call more than once.\"\"\"
    held = list(state["held"])
    state["held"] = [item for item in held if item != slot]
    state["count"] = state["count"] - 1
    return state""",
    variant_four="""def release(state, slot):
    \"\"\"Free `slot` in `state`. Safe to call more than once.\"\"\"
    state["held"].remove(slot)
    state["count"] = max(0, state["count"] - 1)
    return state""",
    visible_test=_test_module(
        "slot_release",
        "Published contract for slot release.",
        """
def test_releases_a_held_slot() -> None:
    state = {"held": ["a"], "count": 1}
    assert release(state, "a")["held"] == []


def test_the_count_drops() -> None:
    state = {"held": ["a", "b"], "count": 2}
    assert release(state, "a")["count"] == 1
""",
        imports="from slot_release import release\n",
    ),
    hidden_test=_test_module(
        "slot_release",
        "The part of the contract the published tests do not state.",
        """
def test_releases_a_held_slot() -> None:
    state = {"held": ["a"], "count": 1}
    assert release(state, "a")["held"] == []


def test_releasing_an_unknown_slot_is_a_no_op() -> None:
    state = {"held": ["a"], "count": 1}
    assert release(state, "zzz")["held"] == ["a"]


def test_the_held_count_never_goes_negative() -> None:
    state = {"held": [], "count": 0}
    assert release(state, "a")["count"] == 0
""",
        imports="from slot_release import release\n",
    ),
)

_D5 = D2TaskSpec(
    template_id="d2_errors.first_present",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-first-present",
    module="lookup_chain",
    module_doc="Reading the first key a mapping actually carries.",
    issue=(
        "first_present() is documented to return the value of the first key the mapping "
        "carries, and the caller's default when none is present. Callers report that a key "
        "holding None is skipped and that an empty key list raises."
    ),
    expected=(
        "first_present(mapping, keys, default) returns the value of the first key present in "
        "the mapping even when that value is None, and default when no key is present."
    ),
    baseline_reason="it tests truthiness of the value and indexes the last key unconditionally",
    edge_cases=(
        "a key whose value is None is still present",
        "an empty key list returns default",
    ),
    baseline="""def first_present(mapping, keys, default=None):
    \"\"\"Return the value of the first key `mapping` carries, else `default`.\"\"\"
    for key in keys:
        if mapping.get(key):
            return mapping[key]
    return mapping[keys[-1]]""",
    variant_one="""def first_present(mapping, keys, default=None):
    \"\"\"Return the value of the first key `mapping` carries, else `default`.\"\"\"
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default""",
    variant_two="""def first_present(mapping, keys, default=None):
    \"\"\"Return the value of the first key `mapping` carries, else `default`.\"\"\"
    present = [key for key in keys if key in mapping]
    return mapping[present[0]] if present else default""",
    variant_three="""def first_present(mapping, keys, default=None):
    \"\"\"Return the value of the first key `mapping` carries, else `default`.\"\"\"
    for key in keys:
        if key in mapping:
            return mapping[key]
    return mapping[keys[-1]]""",
    variant_four="""def first_present(mapping, keys, default=None):
    \"\"\"Return the value of the first key `mapping` carries, else `default`.\"\"\"
    for key in keys:
        if mapping.get(key):
            return mapping[key]
    return default""",
    visible_test=_test_module(
        "lookup_chain",
        "Published contract for the lookup chain.",
        """
def test_returns_the_first_present_key() -> None:
    assert first_present({"b": 2}, ["a", "b"]) == 2


def test_prefers_the_earlier_key() -> None:
    assert first_present({"a": 1, "b": 2}, ["a", "b"]) == 1
""",
        imports="from lookup_chain import first_present\n",
    ),
    hidden_test=_test_module(
        "lookup_chain",
        "The part of the contract the published tests do not state.",
        """
def test_returns_the_first_present_key() -> None:
    assert first_present({"b": 2}, ["a", "b"]) == 2


def test_a_key_whose_value_is_none_is_still_present() -> None:
    assert first_present({"a": None, "b": 2}, ["a", "b"]) is None


def test_an_empty_key_list_returns_the_default() -> None:
    assert first_present({"a": 1}, [], "fallback") == "fallback"
""",
        imports="from lookup_chain import first_present\n",
    ),
)

_D6 = D2TaskSpec(
    template_id="d2_transform.pairs_to_mapping",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-pairs",
    module="pair_mapping",
    module_doc="Turning ordered pairs into a mapping.",
    issue=(
        "to_mapping() is documented to build a mapping from ordered pairs, keeping the first "
        "occurrence of a repeated key. Callers report that later duplicates win and that a "
        "pair of the wrong length raises an unhelpful error."
    ),
    expected=(
        "to_mapping(pairs) keeps the first value for a repeated key and raises ValueError "
        "naming the offending pair when one does not have exactly two elements."
    ),
    baseline_reason="dict() keeps the last duplicate and unpacking raises without context",
    edge_cases=("the first occurrence of a key wins", "a malformed pair names itself"),
    baseline="""def to_mapping(pairs):
    \"\"\"Build a mapping from ordered `pairs`, keeping the first of a repeated key.\"\"\"
    return dict(pairs)""",
    variant_one="""def to_mapping(pairs):
    \"\"\"Build a mapping from ordered `pairs`, keeping the first of a repeated key.\"\"\"
    result = {}
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError(f"pair {pair!r} does not have two elements")
        key, value = pair
        if key not in result:
            result[key] = value
    return result""",
    variant_two="""def to_mapping(pairs):
    \"\"\"Build a mapping from ordered `pairs`, keeping the first of a repeated key.\"\"\"
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError(f"pair {pair!r} does not have two elements")
    return dict(reversed([tuple(pair) for pair in pairs]))""",
    variant_three="""def to_mapping(pairs):
    \"\"\"Build a mapping from ordered `pairs`, keeping the first of a repeated key.\"\"\"
    result = {}
    for pair in pairs:
        key, value = pair
        if key not in result:
            result[key] = value
    return result""",
    variant_four="""def to_mapping(pairs):
    \"\"\"Build a mapping from ordered `pairs`, keeping the first of a repeated key.\"\"\"
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError(f"pair {pair!r} does not have two elements")
    return dict(pairs)""",
    visible_test=_test_module(
        "pair_mapping",
        "Published contract for pair mapping.",
        """
def test_builds_a_mapping() -> None:
    assert to_mapping([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}


def test_an_empty_input_is_an_empty_mapping() -> None:
    assert to_mapping([]) == {}
""",
        imports="from pair_mapping import to_mapping\n",
    ),
    hidden_test=_test_module(
        "pair_mapping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_builds_a_mapping() -> None:
    assert to_mapping([("a", 1), ("b", 2)]) == {"a": 1, "b": 2}


def test_the_first_occurrence_of_a_key_wins() -> None:
    assert to_mapping([("a", 1), ("a", 9)]) == {"a": 1}


def test_a_malformed_pair_names_itself() -> None:
    with pytest.raises(ValueError, match="does not have two elements"):
        to_mapping([("a", 1, 2)])
""",
        imports="from pair_mapping import to_mapping\n",
    ),
)

_D7 = D2TaskSpec(
    template_id="d2_boundary.split_evenly",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-even-split",
    module="even_split",
    module_doc="Splitting a sequence into a fixed number of parts.",
    issue=(
        "split_evenly() is documented to split a sequence into exactly n parts, distributing "
        "any remainder across the earlier parts. Callers report fewer than n parts for short "
        "sequences and a crash when n is zero."
    ),
    expected=(
        "split_evenly(items, n) returns exactly n lists for any positive n, padding with "
        "empty lists when items are fewer than n, and raises ValueError when n is not positive."
    ),
    baseline_reason="a short sequence yields fewer than n parts and a zero count divides by zero",
    edge_cases=(
        "a short sequence still yields n parts",
        "a non-positive count is refused",
    ),
    baseline="""def split_evenly(items, n):
    \"\"\"Split `items` into exactly `n` parts, remainder to the earlier parts.\"\"\"
    parts = []
    for offset in range(n):
        part = [item for index, item in enumerate(items) if index % n == offset]
        if part:
            parts.append(part)
    return parts""",
    variant_one="""def split_evenly(items, n):
    \"\"\"Split `items` into exactly `n` parts, remainder to the earlier parts.\"\"\"
    if n <= 0:
        raise ValueError("the number of parts must be positive")
    parts = [[] for _ in range(n)]
    for index, item in enumerate(items):
        parts[index % n].append(item)
    return parts""",
    variant_two="""def split_evenly(items, n):
    \"\"\"Split `items` into exactly `n` parts, remainder to the earlier parts.\"\"\"
    if n <= 0:
        raise ValueError("the number of parts must be positive")
    return [
        [item for index, item in enumerate(items) if index % n == offset]
        for offset in range(n)
    ]""",
    variant_three="""def split_evenly(items, n):
    \"\"\"Split `items` into exactly `n` parts, remainder to the earlier parts.\"\"\"
    parts = [[] for _ in range(n)]
    for index, item in enumerate(items):
        parts[index % n].append(item)
    return parts""",
    variant_four="""def split_evenly(items, n):
    \"\"\"Split `items` into exactly `n` parts, remainder to the earlier parts.\"\"\"
    if n <= 0:
        raise ValueError("the number of parts must be positive")
    parts = []
    for offset in range(n):
        part = [item for index, item in enumerate(items) if index % n == offset]
        if part:
            parts.append(part)
    return parts""",
    visible_test=_test_module(
        "even_split",
        "Published contract for even splitting.",
        """
def test_splits_into_two() -> None:
    assert split_evenly([1, 2, 3, 4], 2) == [[1, 3], [2, 4]]


def test_splits_into_one() -> None:
    assert split_evenly([1, 2], 1) == [[1, 2]]
""",
        imports="from even_split import split_evenly\n",
    ),
    hidden_test=_test_module(
        "even_split",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_splits_into_two() -> None:
    assert split_evenly([1, 2, 3, 4], 2) == [[1, 3], [2, 4]]


def test_a_short_sequence_still_yields_n_parts() -> None:
    assert len(split_evenly([1], 3)) == 3


def test_a_non_positive_count_is_refused() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        split_evenly([1, 2], 0)
""",
        imports="from even_split import split_evenly\n",
    ),
)

_D8 = D2TaskSpec(
    template_id="d2_parsing.parse_duration",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-durations",
    module="duration_parse",
    module_doc="Reading a duration written as a suffixed integer.",
    issue=(
        "parse_duration() is documented to read values like '30s' or '5m' into seconds and to "
        "refuse anything else. Callers report that a bare number is accepted as seconds "
        "without saying so, and that a negative value passes through."
    ),
    expected=(
        "parse_duration(text) accepts an integer followed by s, m or h and returns seconds; "
        "it raises ValueError for a missing suffix, an unknown suffix or a negative value."
    ),
    baseline_reason="the suffix is optional in the parse and the sign is never checked",
    edge_cases=("a bare number is refused", "a negative duration is refused"),
    baseline="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` names, e.g. '30s' or '5m'.\"\"\"
    units = {"s": 1, "m": 60, "h": 3600}
    if text and text[-1] in units:
        return int(text[:-1]) * units[text[-1]]
    return int(text)""",
    variant_one="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` names, e.g. '30s' or '5m'.\"\"\"
    units = {"s": 1, "m": 60, "h": 3600}
    if not text or text[-1] not in units:
        raise ValueError(f"duration {text!r} needs one of the suffixes s, m or h")
    value = int(text[:-1])
    if value < 0:
        raise ValueError(f"duration {text!r} is negative")
    return value * units[text[-1]]""",
    variant_two="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` names, e.g. '30s' or '5m'.\"\"\"
    import re

    units = {"s": 1, "m": 60, "h": 3600}
    match = re.fullmatch(r"(\\d+)([smh])", text or "")
    if match is None:
        raise ValueError(f"duration {text!r} is not a non-negative integer with a suffix")
    return int(match.group(1)) * units[match.group(2)]""",
    variant_three="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` names, e.g. '30s' or '5m'.\"\"\"
    units = {"s": 1, "m": 60, "h": 3600}
    if not text or text[-1] not in units:
        raise ValueError(f"duration {text!r} needs one of the suffixes s, m or h")
    return int(text[:-1]) * units[text[-1]]""",
    variant_four="""def parse_duration(text):
    \"\"\"Return the number of seconds `text` names, e.g. '30s' or '5m'.\"\"\"
    units = {"s": 1, "m": 60, "h": 3600}
    if text and text[-1] in units:
        value = int(text[:-1])
        if value < 0:
            raise ValueError(f"duration {text!r} is negative")
        return value * units[text[-1]]
    return int(text)""",
    visible_test=_test_module(
        "duration_parse",
        "Published contract for duration parsing.",
        """
def test_reads_seconds() -> None:
    assert parse_duration("30s") == 30


def test_reads_minutes() -> None:
    assert parse_duration("5m") == 300
""",
        imports="from duration_parse import parse_duration\n",
    ),
    hidden_test=_test_module(
        "duration_parse",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_hours() -> None:
    assert parse_duration("2h") == 7200


def test_a_bare_number_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_duration("30")


def test_a_negative_duration_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_duration("-5m")
""",
        imports="from duration_parse import parse_duration\n",
    ),
)

_D9 = D2TaskSpec(
    template_id="d2_numeric.running_total",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-running-total",
    module="running_totals",
    module_doc="Cumulative sums that start from a declared base.",
    issue=(
        "running_total() is documented to return the cumulative sums of a sequence starting "
        "from a base. Callers report that the base is omitted from the first entry and that "
        "an empty sequence returns the base rather than nothing."
    ),
    expected=(
        "running_total(values, base) returns one entry per value, each including the base, "
        "and returns an empty list for an empty sequence."
    ),
    baseline_reason="the running sum starts at zero rather than at the base",
    edge_cases=(
        "the base is included in every entry",
        "an empty sequence yields nothing",
    ),
    baseline="""def running_total(values, base=0):
    \"\"\"Return the cumulative sums of `values`, each including `base`.\"\"\"
    totals = [base]
    running = 0
    for value in values:
        running += value
        totals.append(running)
    return totals[1:]""",
    variant_one="""def running_total(values, base=0):
    \"\"\"Return the cumulative sums of `values`, each including `base`.\"\"\"
    totals = []
    running = base
    for value in values:
        running += value
        totals.append(running)
    return totals""",
    variant_two="""def running_total(values, base=0):
    \"\"\"Return the cumulative sums of `values`, each including `base`.\"\"\"
    from itertools import accumulate

    return list(accumulate(values, initial=base))[1:]""",
    variant_three="""def running_total(values, base=0):
    \"\"\"Return the cumulative sums of `values`, each including `base`.\"\"\"
    running = base
    totals = []
    for value in values:
        running += value
        totals.append(running)
    return totals or [base]""",
    variant_four="""def running_total(values, base=0):
    \"\"\"Return the cumulative sums of `values`, each including `base`.\"\"\"
    running = 0
    totals = []
    for value in values:
        running += value
        totals.append(running)
    return totals""",
    visible_test=_test_module(
        "running_totals",
        "Published contract for running totals.",
        """
def test_accumulates() -> None:
    assert running_total([1, 2, 3])[-1] == 6


def test_returns_one_entry_per_value() -> None:
    assert len(running_total([1, 2, 3])) == 3
""",
        imports="from running_totals import running_total\n",
    ),
    hidden_test=_test_module(
        "running_totals",
        "The part of the contract the published tests do not state.",
        """
def test_accumulates() -> None:
    assert running_total([1, 2, 3])[-1] == 6


def test_the_base_is_included_in_the_first_entry() -> None:
    assert running_total([1, 2], 10)[0] == 11


def test_an_empty_sequence_yields_nothing() -> None:
    assert running_total([], 10) == []
""",
        imports="from running_totals import running_total\n",
    ),
)

_D10 = D2TaskSpec(
    template_id="d2_state.merge_counters",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-counter-merge",
    module="counter_merge",
    module_doc="Combining two counter mappings without losing either.",
    issue=(
        "merge_counters() is documented to add two counter mappings together and to leave both "
        "inputs untouched. Callers report that the left mapping is mutated and that keys "
        "present only on the right are dropped."
    ),
    expected=(
        "merge_counters(left, right) returns a new mapping holding the sum for every key in "
        "either input, and neither argument is modified."
    ),
    baseline_reason="it updates the left mapping in place and iterates only its own keys",
    edge_cases=("the left argument is not mutated", "right-only keys survive"),
    baseline="""def merge_counters(left, right):
    \"\"\"Return the per-key sum of `left` and `right`, mutating neither.\"\"\"
    for key in left:
        left[key] = left[key] + right.get(key, 0)
    return left""",
    variant_one="""def merge_counters(left, right):
    \"\"\"Return the per-key sum of `left` and `right`, mutating neither.\"\"\"
    merged = dict(left)
    for key, value in right.items():
        merged[key] = merged.get(key, 0) + value
    return merged""",
    variant_two="""def merge_counters(left, right):
    \"\"\"Return the per-key sum of `left` and `right`, mutating neither.\"\"\"
    keys = set(left) | set(right)
    return {key: left.get(key, 0) + right.get(key, 0) for key in sorted(keys)}""",
    variant_three="""def merge_counters(left, right):
    \"\"\"Return the per-key sum of `left` and `right`, mutating neither.\"\"\"
    merged = dict(left)
    for key in merged:
        merged[key] = merged[key] + right.get(key, 0)
    return merged""",
    variant_four="""def merge_counters(left, right):
    \"\"\"Return the per-key sum of `left` and `right`, mutating neither.\"\"\"
    for key, value in right.items():
        left[key] = left.get(key, 0) + value
    return left""",
    visible_test=_test_module(
        "counter_merge",
        "Published contract for counter merging.",
        """
def test_adds_shared_keys() -> None:
    assert merge_counters({"a": 1}, {"a": 2}) == {"a": 3}


def test_keeps_left_only_keys() -> None:
    assert merge_counters({"a": 1}, {}) == {"a": 1}
""",
        imports="from counter_merge import merge_counters\n",
    ),
    hidden_test=_test_module(
        "counter_merge",
        "The part of the contract the published tests do not state.",
        """
def test_adds_shared_keys() -> None:
    assert merge_counters({"a": 1}, {"a": 2}) == {"a": 3}


def test_the_left_argument_is_not_mutated() -> None:
    left = {"a": 1}
    merge_counters(left, {"a": 2})
    assert left == {"a": 1}


def test_right_only_keys_survive() -> None:
    assert merge_counters({"a": 1}, {"b": 5}) == {"a": 1, "b": 5}
""",
        imports="from counter_merge import merge_counters\n",
    ),
)

# ------------------------------------------------------- boundary and collections, S21D2-022

_D11 = D2TaskSpec(
    template_id="d2_boundary.index_of_max",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-peak-position",
    module="peak_position",
    module_doc="Locating the largest value in a sequence.",
    issue=(
        "index_of_max() is documented to return the position of the largest value, keeping "
        "the earliest position when several values tie. Callers report the last one winning."
    ),
    expected=(
        "index_of_max(values) returns the index of the largest value, keeps the earliest index "
        "when values tie, and raises ValueError when there are no values."
    ),
    baseline_reason="comparing with >= lets a later equal value take the position",
    edge_cases=("a tie keeps the first index", "no values are refused"),
    baseline="""def index_of_max(values):
    \"\"\"Return the index of the largest of `values`.\"\"\"
    best = 0
    for index, value in enumerate(values):
        if value >= values[best]:
            best = index
    return best""",
    variant_one="""def index_of_max(values):
    \"\"\"Return the index of the largest of `values`.\"\"\"
    if not values:
        raise ValueError("there are no values to compare")
    best = 0
    for index, value in enumerate(values):
        if value > values[best]:
            best = index
    return best""",
    variant_two="""def index_of_max(values):
    \"\"\"Return the index of the largest of `values`.\"\"\"
    ordered = list(values)
    if not ordered:
        raise ValueError("there are no values to compare")
    return max(range(len(ordered)), key=lambda index: (ordered[index], -index))""",
    variant_three="""def index_of_max(values):
    \"\"\"Return the index of the largest of `values`.\"\"\"
    if not values:
        raise ValueError("there are no values to compare")
    best = 0
    for index, value in enumerate(values):
        if value >= values[best]:
            best = index
    return best""",
    variant_four="""def index_of_max(values):
    \"\"\"Return the index of the largest of `values`.\"\"\"
    best = 0
    for index, value in enumerate(values):
        if value > values[best]:
            best = index
    return best""",
    visible_test=_test_module(
        "peak_position",
        "Published contract for locating the largest value.",
        """
def test_finds_the_largest() -> None:
    assert index_of_max([1, 5, 2]) == 1


def test_a_single_value_sits_at_index_zero() -> None:
    assert index_of_max([7]) == 0
""",
        imports="from peak_position import index_of_max\n",
    ),
    hidden_test=_test_module(
        "peak_position",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_finds_the_largest() -> None:
    assert index_of_max([1, 5, 2]) == 1


def test_a_tie_keeps_the_first_index() -> None:
    assert index_of_max([3, 1, 3]) == 0


def test_no_values_are_refused() -> None:
    with pytest.raises(ValueError):
        index_of_max([])
""",
        imports="from peak_position import index_of_max\n",
    ),
)

_D12 = D2TaskSpec(
    template_id="d2_boundary.pad_to",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-padding",
    module="sequence_padding",
    module_doc="Padding a sequence to a fixed width.",
    issue=(
        "pad_to() is documented to return a sequence of exactly the requested size. Callers "
        "report longer inputs coming back untouched and negative sizes being accepted."
    ),
    expected=(
        "pad_to(items, size, filler) returns exactly `size` items, padding with `filler` and "
        "truncating anything longer, and raises ValueError when `size` is negative."
    ),
    baseline_reason="a repeat count below zero yields nothing, so long inputs are never trimmed",
    edge_cases=("a longer sequence is truncated", "a negative size is refused"),
    baseline="""def pad_to(items, size, filler):
    \"\"\"Return `items` at exactly `size` places, padding with `filler`.\"\"\"
    padded = list(items)
    return padded + [filler] * (size - len(padded))""",
    variant_one="""def pad_to(items, size, filler):
    \"\"\"Return `items` at exactly `size` places, padding with `filler`.\"\"\"
    if size < 0:
        raise ValueError("the size must not be negative")
    padded = list(items)[:size]
    return padded + [filler] * (size - len(padded))""",
    variant_two="""def pad_to(items, size, filler):
    \"\"\"Return `items` at exactly `size` places, padding with `filler`.\"\"\"
    from itertools import chain, islice, repeat

    if size < 0:
        raise ValueError("the size must not be negative")
    return list(islice(chain(items, repeat(filler)), size))""",
    variant_three="""def pad_to(items, size, filler):
    \"\"\"Return `items` at exactly `size` places, padding with `filler`.\"\"\"
    padded = list(items)[:size]
    return padded + [filler] * (size - len(padded))""",
    variant_four="""def pad_to(items, size, filler):
    \"\"\"Return `items` at exactly `size` places, padding with `filler`.\"\"\"
    if size < 0:
        raise ValueError("the size must not be negative")
    padded = list(items)
    return padded + [filler] * (size - len(padded))""",
    visible_test=_test_module(
        "sequence_padding",
        "Published contract for padding.",
        """
def test_pads_to_the_requested_size() -> None:
    assert pad_to([1, 2], 4, 0) == [1, 2, 0, 0]


def test_a_sequence_already_at_the_size_is_unchanged() -> None:
    assert pad_to([1, 2], 2, 0) == [1, 2]
""",
        imports="from sequence_padding import pad_to\n",
    ),
    hidden_test=_test_module(
        "sequence_padding",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_pads_to_the_requested_size() -> None:
    assert pad_to([1, 2], 4, 0) == [1, 2, 0, 0]


def test_a_longer_sequence_is_truncated() -> None:
    assert pad_to([1, 2, 3], 2, 0) == [1, 2]


def test_a_negative_size_is_refused() -> None:
    with pytest.raises(ValueError):
        pad_to([1], -1, 0)
""",
        imports="from sequence_padding import pad_to\n",
    ),
)

_D13 = D2TaskSpec(
    template_id="d2_boundary.interleave",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-interleave",
    module="sequence_interleave",
    module_doc="Interleaving two sequences.",
    issue=(
        "interleave() is documented to alternate two sequences and keep whatever is left of "
        "the longer one. Callers report the tail disappearing and a crash on generators."
    ),
    expected=(
        "interleave(left, right) alternates the two, starting with left, appends the remainder "
        "of the longer one, and accepts any iterable rather than only a sequence."
    ),
    baseline_reason="indexing to the shorter length drops the tail and demands len()",
    edge_cases=("the longer tail is kept", "any iterable is accepted"),
    baseline="""def interleave(left, right):
    \"\"\"Alternate `left` and `right`, keeping the longer tail.\"\"\"
    merged = []
    for index in range(min(len(left), len(right))):
        merged.append(left[index])
        merged.append(right[index])
    return merged""",
    variant_one="""def interleave(left, right):
    \"\"\"Alternate `left` and `right`, keeping the longer tail.\"\"\"
    first = list(left)
    second = list(right)
    merged = []
    for index in range(max(len(first), len(second))):
        if index < len(first):
            merged.append(first[index])
        if index < len(second):
            merged.append(second[index])
    return merged""",
    variant_two="""def interleave(left, right):
    \"\"\"Alternate `left` and `right`, keeping the longer tail.\"\"\"
    from itertools import chain, zip_longest

    missing = object()
    paired = zip_longest(left, right, fillvalue=missing)
    return [item for item in chain.from_iterable(paired) if item is not missing]""",
    variant_three="""def interleave(left, right):
    \"\"\"Alternate `left` and `right`, keeping the longer tail.\"\"\"
    merged = []
    for index in range(max(len(left), len(right))):
        if index < len(left):
            merged.append(left[index])
        if index < len(right):
            merged.append(right[index])
    return merged""",
    variant_four="""def interleave(left, right):
    \"\"\"Alternate `left` and `right`, keeping the longer tail.\"\"\"
    first = list(left)
    second = list(right)
    merged = []
    for index in range(min(len(first), len(second))):
        merged.append(first[index])
        merged.append(second[index])
    return merged""",
    visible_test=_test_module(
        "sequence_interleave",
        "Published contract for interleaving.",
        """
def test_alternates_two_equal_sequences() -> None:
    assert interleave([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_two_empty_sequences_give_an_empty_result() -> None:
    assert interleave([], []) == []
""",
        imports="from sequence_interleave import interleave\n",
    ),
    hidden_test=_test_module(
        "sequence_interleave",
        "The part of the contract the published tests do not state.",
        """
def test_alternates_two_equal_sequences() -> None:
    assert interleave([1, 3], [2, 4]) == [1, 2, 3, 4]


def test_the_longer_tail_is_kept() -> None:
    assert interleave([1, 3, 5, 7], [2, 4]) == [1, 2, 3, 4, 5, 7]


def test_any_iterable_is_accepted() -> None:
    assert interleave(iter([1, 3]), iter([2, 4])) == [1, 2, 3, 4]
""",
        imports="from sequence_interleave import interleave\n",
    ),
)

_D14 = D2TaskSpec(
    template_id="d2_boundary.drop_leading_blanks",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-leading-blanks",
    module="line_trimming",
    module_doc="Trimming blank lines from the front of a file.",
    issue=(
        "drop_leading_blanks() is documented to remove blank lines from the front of a file "
        "only. Callers report interior blank lines vanishing and indented blank lines staying."
    ),
    expected=(
        "drop_leading_blanks(lines) removes blank lines from the front only, treats a line of "
        "whitespace as blank, and leaves interior and trailing blank lines in place."
    ),
    baseline_reason="filtering every line drops interior blanks and only an empty string counts",
    edge_cases=(
        "an interior blank line is kept",
        "a whitespace-only line counts as blank",
    ),
    baseline="""def drop_leading_blanks(lines):
    \"\"\"Drop blank lines from the front of `lines`.\"\"\"
    kept = []
    for line in lines:
        if line != "":
            kept.append(line)
    return kept""",
    variant_one="""def drop_leading_blanks(lines):
    \"\"\"Drop blank lines from the front of `lines`.\"\"\"
    kept = list(lines)
    index = 0
    while index < len(kept) and not kept[index].strip():
        index += 1
    return kept[index:]""",
    variant_two="""def drop_leading_blanks(lines):
    \"\"\"Drop blank lines from the front of `lines`.\"\"\"
    from itertools import dropwhile

    return list(dropwhile(lambda line: not line.strip(), lines))""",
    variant_three="""def drop_leading_blanks(lines):
    \"\"\"Drop blank lines from the front of `lines`.\"\"\"
    kept = list(lines)
    index = 0
    while index < len(kept) and kept[index] == "":
        index += 1
    return kept[index:]""",
    variant_four="""def drop_leading_blanks(lines):
    \"\"\"Drop blank lines from the front of `lines`.\"\"\"
    kept = []
    for line in lines:
        if line.strip():
            kept.append(line)
    return kept""",
    visible_test=_test_module(
        "line_trimming",
        "Published contract for trimming leading blanks.",
        """
def test_drops_a_leading_blank() -> None:
    assert drop_leading_blanks(["", "body"]) == ["body"]


def test_a_file_without_leading_blanks_is_unchanged() -> None:
    assert drop_leading_blanks(["body", "tail"]) == ["body", "tail"]
""",
        imports="from line_trimming import drop_leading_blanks\n",
    ),
    hidden_test=_test_module(
        "line_trimming",
        "The part of the contract the published tests do not state.",
        """
def test_drops_a_leading_blank() -> None:
    assert drop_leading_blanks(["", "body"]) == ["body"]


def test_an_interior_blank_line_is_kept() -> None:
    assert drop_leading_blanks(["body", "", "tail"]) == ["body", "", "tail"]


def test_a_whitespace_only_line_counts_as_blank() -> None:
    assert drop_leading_blanks(["   ", "body"]) == ["body"]
""",
        imports="from line_trimming import drop_leading_blanks\n",
    ),
)

_D15 = D2TaskSpec(
    template_id="d2_boundary.slice_around",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-neighbourhood",
    module="neighbourhood",
    module_doc="Reading the neighbourhood of a position.",
    issue=(
        "slice_around() is documented to return the items within a radius of a position, "
        "clipped at both ends. Callers near the start get items from the far end instead."
    ),
    expected=(
        "slice_around(items, index, radius) returns the items within `radius` places of "
        "`index`, clipped at both ends, and raises ValueError for a negative radius."
    ),
    baseline_reason="a negative slice start counts from the end instead of clipping at zero",
    edge_cases=(
        "an index near the start does not wrap",
        "a negative radius is refused",
    ),
    baseline="""def slice_around(items, index, radius):
    \"\"\"Return the items within `radius` places of `index`.\"\"\"
    return list(items[index - radius : index + radius + 1])""",
    variant_one="""def slice_around(items, index, radius):
    \"\"\"Return the items within `radius` places of `index`.\"\"\"
    if radius < 0:
        raise ValueError("the radius must not be negative")
    start = max(index - radius, 0)
    return list(items[start : index + radius + 1])""",
    variant_two="""def slice_around(items, index, radius):
    \"\"\"Return the items within `radius` places of `index`.\"\"\"
    if radius < 0:
        raise ValueError("the radius must not be negative")
    return [item for position, item in enumerate(items) if abs(position - index) <= radius]""",
    variant_three="""def slice_around(items, index, radius):
    \"\"\"Return the items within `radius` places of `index`.\"\"\"
    start = max(index - radius, 0)
    return list(items[start : index + radius + 1])""",
    variant_four="""def slice_around(items, index, radius):
    \"\"\"Return the items within `radius` places of `index`.\"\"\"
    if radius < 0:
        raise ValueError("the radius must not be negative")
    return list(items[index - radius : index + radius + 1])""",
    visible_test=_test_module(
        "neighbourhood",
        "Published contract for neighbourhood slicing.",
        """
def test_returns_the_neighbourhood() -> None:
    assert slice_around([1, 2, 3, 4, 5], 2, 1) == [2, 3, 4]


def test_a_zero_radius_returns_one_item() -> None:
    assert slice_around([1, 2, 3], 1, 0) == [2]
""",
        imports="from neighbourhood import slice_around\n",
    ),
    hidden_test=_test_module(
        "neighbourhood",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_returns_the_neighbourhood() -> None:
    assert slice_around([1, 2, 3, 4, 5], 2, 1) == [2, 3, 4]


def test_an_index_near_the_start_does_not_wrap() -> None:
    assert slice_around([1, 2, 3, 4, 5], 0, 2) == [1, 2, 3]


def test_a_negative_radius_is_refused() -> None:
    with pytest.raises(ValueError):
        slice_around([1, 2, 3], 1, -1)
""",
        imports="from neighbourhood import slice_around\n",
    ),
)

_D16 = D2TaskSpec(
    template_id="d2_boundary.longest_run",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-longest-run",
    module="run_length",
    module_doc="Measuring runs of equal consecutive items.",
    issue=(
        "longest_run() is documented to return the length of the longest run of equal "
        "consecutive items. Callers report a run at the very end being ignored."
    ),
    expected=(
        "longest_run(items) returns the length of the longest run of equal consecutive items, "
        "counts a run that reaches the end of the sequence, and returns zero for no items."
    ),
    baseline_reason="the best is only updated when a run breaks, and it starts at one",
    edge_cases=("an empty sequence has no run", "a run at the end is counted"),
    baseline="""def longest_run(items):
    \"\"\"Return the length of the longest run of equal consecutive items.\"\"\"
    best = 1
    current = 1
    for index in range(1, len(items)):
        if items[index] == items[index - 1]:
            current += 1
        else:
            best = max(best, current)
            current = 1
    return best""",
    variant_one="""def longest_run(items):
    \"\"\"Return the length of the longest run of equal consecutive items.\"\"\"
    best = 0
    current = 0
    previous = object()
    for item in items:
        current = current + 1 if item == previous else 1
        previous = item
        best = max(best, current)
    return best""",
    variant_two="""def longest_run(items):
    \"\"\"Return the length of the longest run of equal consecutive items.\"\"\"
    from itertools import groupby

    return max((len(list(group)) for _, group in groupby(items)), default=0)""",
    variant_three="""def longest_run(items):
    \"\"\"Return the length of the longest run of equal consecutive items.\"\"\"
    if not items:
        return 0
    best = 1
    current = 1
    for index in range(1, len(items)):
        if items[index] == items[index - 1]:
            current += 1
        else:
            best = max(best, current)
            current = 1
    return best""",
    variant_four="""def longest_run(items):
    \"\"\"Return the length of the longest run of equal consecutive items.\"\"\"
    best = 1
    current = 1
    for index in range(1, len(items)):
        if items[index] == items[index - 1]:
            current += 1
        else:
            current = 1
        best = max(best, current)
    return best""",
    visible_test=_test_module(
        "run_length",
        "Published contract for run lengths.",
        """
def test_counts_a_run_of_two() -> None:
    assert longest_run([1, 1, 2, 3]) == 2


def test_a_sequence_without_repeats_has_a_run_of_one() -> None:
    assert longest_run([1, 2, 3]) == 1
""",
        imports="from run_length import longest_run\n",
    ),
    hidden_test=_test_module(
        "run_length",
        "The part of the contract the published tests do not state.",
        """
def test_counts_a_run_of_two() -> None:
    assert longest_run([1, 1, 2, 3]) == 2


def test_an_empty_sequence_has_no_run() -> None:
    assert longest_run([]) == 0


def test_a_run_at_the_end_is_counted() -> None:
    assert longest_run([1, 2, 2, 2]) == 3
""",
        imports="from run_length import longest_run\n",
    ),
)

_D17 = D2TaskSpec(
    template_id="d2_boundary.trim_edges",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-edge-trim",
    module="edge_trimming",
    module_doc="Trimming a fixed number of items from both ends.",
    issue=(
        "trim_edges() is documented to drop a fixed count from each end. Callers report a "
        "crash when the count exceeds what the sequence holds, and negative counts accepted."
    ),
    expected=(
        "trim_edges(items, count) drops `count` items from each end, returns an empty list "
        "when twice the count reaches the length, and raises ValueError for a negative count."
    ),
    baseline_reason="popping from both ends runs off the end and a negative count loops zero times",
    edge_cases=(
        "trimming more than the sequence holds leaves nothing",
        "a negative count is refused",
    ),
    baseline="""def trim_edges(items, count):
    \"\"\"Drop `count` items from each end of `items`.\"\"\"
    trimmed = list(items)
    for _ in range(count):
        trimmed.pop(0)
        trimmed.pop()
    return trimmed""",
    variant_one="""def trim_edges(items, count):
    \"\"\"Drop `count` items from each end of `items`.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    trimmed = list(items)
    if count * 2 >= len(trimmed):
        return []
    return trimmed[count : len(trimmed) - count]""",
    variant_two="""def trim_edges(items, count):
    \"\"\"Drop `count` items from each end of `items`.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    size = len(items)
    return [item for index, item in enumerate(items) if count <= index < size - count]""",
    variant_three="""def trim_edges(items, count):
    \"\"\"Drop `count` items from each end of `items`.\"\"\"
    trimmed = list(items)
    if count * 2 >= len(trimmed):
        return []
    return trimmed[count : len(trimmed) - count]""",
    variant_four="""def trim_edges(items, count):
    \"\"\"Drop `count` items from each end of `items`.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    trimmed = list(items)
    for _ in range(count):
        trimmed.pop(0)
        trimmed.pop()
    return trimmed""",
    visible_test=_test_module(
        "edge_trimming",
        "Published contract for edge trimming.",
        """
def test_trims_one_from_each_end() -> None:
    assert trim_edges([1, 2, 3, 4], 1) == [2, 3]


def test_trimming_nothing_leaves_the_sequence() -> None:
    assert trim_edges([1, 2, 3], 0) == [1, 2, 3]
""",
        imports="from edge_trimming import trim_edges\n",
    ),
    hidden_test=_test_module(
        "edge_trimming",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_trims_one_from_each_end() -> None:
    assert trim_edges([1, 2, 3, 4], 1) == [2, 3]


def test_trimming_more_than_the_sequence_holds_leaves_nothing() -> None:
    assert trim_edges([1, 2, 3], 2) == []


def test_a_negative_count_is_refused() -> None:
    with pytest.raises(ValueError):
        trim_edges([1, 2, 3], -1)
""",
        imports="from edge_trimming import trim_edges\n",
    ),
)

_D18 = D2TaskSpec(
    template_id="d2_boundary.every_nth",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-stride",
    module="stride_sampling",
    module_doc="Sampling a sequence at a fixed stride.",
    issue=(
        "every_nth() is documented to return a list holding every n-th item. Callers report a "
        "tuple coming back for a tuple, and a negative stride quietly reversing the sequence."
    ),
    expected=(
        "every_nth(items, step) returns a list of every `step`-th item starting with the "
        "first, whatever sequence type it was given, and raises ValueError unless step > 0."
    ),
    baseline_reason="a bare slice inherits the input type and accepts a negative stride",
    edge_cases=("a non-positive step is refused", "a tuple still yields a list"),
    baseline="""def every_nth(items, step):
    \"\"\"Return every `step`-th item of `items`, starting with the first.\"\"\"
    return items[::step]""",
    variant_one="""def every_nth(items, step):
    \"\"\"Return every `step`-th item of `items`, starting with the first.\"\"\"
    if step <= 0:
        raise ValueError("the step must be positive")
    return list(items[::step])""",
    variant_two="""def every_nth(items, step):
    \"\"\"Return every `step`-th item of `items`, starting with the first.\"\"\"
    from itertools import islice

    if step <= 0:
        raise ValueError("the step must be positive")
    return list(islice(items, 0, None, step))""",
    variant_three="""def every_nth(items, step):
    \"\"\"Return every `step`-th item of `items`, starting with the first.\"\"\"
    if step <= 0:
        raise ValueError("the step must be positive")
    return items[::step]""",
    variant_four="""def every_nth(items, step):
    \"\"\"Return every `step`-th item of `items`, starting with the first.\"\"\"
    return list(items[::step])""",
    visible_test=_test_module(
        "stride_sampling",
        "Published contract for stride sampling.",
        """
def test_takes_every_second_item() -> None:
    assert every_nth([1, 2, 3, 4, 5], 2) == [1, 3, 5]


def test_a_step_of_one_takes_everything() -> None:
    assert every_nth([1, 2, 3], 1) == [1, 2, 3]
""",
        imports="from stride_sampling import every_nth\n",
    ),
    hidden_test=_test_module(
        "stride_sampling",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_takes_every_second_item() -> None:
    assert every_nth([1, 2, 3, 4, 5], 2) == [1, 3, 5]


def test_a_non_positive_step_is_refused() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        every_nth([1, 2, 3], -1)


def test_a_tuple_still_yields_a_list() -> None:
    assert every_nth((1, 2, 3, 4), 2) == [1, 3]
""",
        imports="from stride_sampling import every_nth\n",
    ),
)

_D19 = D2TaskSpec(
    template_id="d2_boundary.insert_sorted",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-sorted-insert",
    module="sorted_insertion",
    module_doc="Inserting into an already sorted list.",
    issue=(
        "insert_sorted() is documented to return a new sorted list. Callers report their own "
        "list changing underneath them, and a None value being inserted rather than refused."
    ),
    expected=(
        "insert_sorted(items, value) returns a new list with `value` in sorted position, "
        "leaves the caller's list untouched, and raises ValueError when `value` is None."
    ),
    baseline_reason="the insert lands in the caller's list and None is never checked for",
    edge_cases=("the input is not mutated", "a None value is refused"),
    baseline="""def insert_sorted(items, value):
    \"\"\"Return `items` with `value` inserted in sorted position.\"\"\"
    for index, existing in enumerate(items):
        if existing > value:
            items.insert(index, value)
            return items
    items.append(value)
    return items""",
    variant_one="""def insert_sorted(items, value):
    \"\"\"Return `items` with `value` inserted in sorted position.\"\"\"
    if value is None:
        raise ValueError("the value must not be None")
    merged = list(items)
    for index, existing in enumerate(merged):
        if existing > value:
            merged.insert(index, value)
            return merged
    merged.append(value)
    return merged""",
    variant_two="""def insert_sorted(items, value):
    \"\"\"Return `items` with `value` inserted in sorted position.\"\"\"
    from bisect import bisect_right

    if value is None:
        raise ValueError("the value must not be None")
    merged = list(items)
    merged.insert(bisect_right(merged, value), value)
    return merged""",
    variant_three="""def insert_sorted(items, value):
    \"\"\"Return `items` with `value` inserted in sorted position.\"\"\"
    merged = list(items)
    for index, existing in enumerate(merged):
        if existing > value:
            merged.insert(index, value)
            return merged
    merged.append(value)
    return merged""",
    variant_four="""def insert_sorted(items, value):
    \"\"\"Return `items` with `value` inserted in sorted position.\"\"\"
    if value is None:
        raise ValueError("the value must not be None")
    for index, existing in enumerate(items):
        if existing > value:
            items.insert(index, value)
            return items
    items.append(value)
    return items""",
    visible_test=_test_module(
        "sorted_insertion",
        "Published contract for sorted insertion.",
        """
def test_inserts_in_the_middle() -> None:
    assert insert_sorted([1, 3, 5], 4) == [1, 3, 4, 5]


def test_inserts_at_the_end() -> None:
    assert insert_sorted([1, 2], 9) == [1, 2, 9]
""",
        imports="from sorted_insertion import insert_sorted\n",
    ),
    hidden_test=_test_module(
        "sorted_insertion",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_inserts_in_the_middle() -> None:
    assert insert_sorted([1, 3, 5], 4) == [1, 3, 4, 5]


def test_the_input_is_not_mutated() -> None:
    original = [1, 3]
    insert_sorted(original, 2)
    assert original == [1, 3]


def test_a_none_value_is_refused() -> None:
    with pytest.raises(ValueError):
        insert_sorted([1, 2], None)
""",
        imports="from sorted_insertion import insert_sorted\n",
    ),
)

_D20 = D2TaskSpec(
    template_id="d2_boundary.flatten_once",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-flatten",
    module="nested_flattening",
    module_doc="Flattening one level of nesting.",
    issue=(
        "flatten_once() is documented to flatten one level and pass anything that is not a "
        "collection straight through. Callers report strings coming back as characters."
    ),
    expected=(
        "flatten_once(nested) flattens one level, keeps a string element whole rather than "
        "splitting it into characters, and passes a non-iterable element through unchanged."
    ),
    baseline_reason="iterating every element splits strings and raises on anything scalar",
    edge_cases=(
        "a string element is kept whole",
        "a non-iterable element passes through",
    ),
    baseline="""def flatten_once(nested):
    \"\"\"Flatten one level of `nested`.\"\"\"
    flat = []
    for element in nested:
        for item in element:
            flat.append(item)
    return flat""",
    variant_one="""def flatten_once(nested):
    \"\"\"Flatten one level of `nested`.\"\"\"
    flat = []
    for element in nested:
        if isinstance(element, (list, tuple, set)):
            flat.extend(element)
        else:
            flat.append(element)
    return flat""",
    variant_two="""def flatten_once(nested):
    \"\"\"Flatten one level of `nested`.\"\"\"
    from itertools import chain

    def widen(element):
        if isinstance(element, str) or not hasattr(element, "__iter__"):
            return [element]
        return list(element)

    return list(chain.from_iterable(widen(element) for element in nested))""",
    variant_three="""def flatten_once(nested):
    \"\"\"Flatten one level of `nested`.\"\"\"
    flat = []
    for element in nested:
        if isinstance(element, str):
            flat.append(element)
        else:
            flat.extend(element)
    return flat""",
    variant_four="""def flatten_once(nested):
    \"\"\"Flatten one level of `nested`.\"\"\"
    flat = []
    for element in nested:
        try:
            flat.extend(element)
        except TypeError:
            flat.append(element)
    return flat""",
    visible_test=_test_module(
        "nested_flattening",
        "Published contract for flattening.",
        """
def test_flattens_one_level() -> None:
    assert flatten_once([[1, 2], [3]]) == [1, 2, 3]


def test_an_empty_inner_list_contributes_nothing() -> None:
    assert flatten_once([[1], []]) == [1]
""",
        imports="from nested_flattening import flatten_once\n",
    ),
    hidden_test=_test_module(
        "nested_flattening",
        "The part of the contract the published tests do not state.",
        """
def test_flattens_one_level() -> None:
    assert flatten_once([[1, 2], [3]]) == [1, 2, 3]


def test_a_string_element_is_kept_whole() -> None:
    assert flatten_once([[1], "ab"]) == [1, "ab"]


def test_a_non_iterable_element_passes_through() -> None:
    assert flatten_once([[1], 5]) == [1, 5]
""",
        imports="from nested_flattening import flatten_once\n",
    ),
)

_D21 = D2TaskSpec(
    template_id="d2_boundary.bounds",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-extent",
    module="extent",
    module_doc="Reporting the extent of a set of values.",
    issue=(
        "bounds() is documented to report the smallest and largest value. Callers report zero "
        "appearing in the answer for values that are all positive, and no error on no values."
    ),
    expected=(
        "bounds(values) returns (minimum, maximum) over the values themselves, raises "
        "ValueError when there are none, and reports a single value as both bounds."
    ),
    baseline_reason="both accumulators are seeded at zero rather than from the first value",
    edge_cases=("an empty sequence is refused", "a single value is both bounds"),
    baseline="""def bounds(values):
    \"\"\"Return the smallest and largest of `values`.\"\"\"
    low = 0
    high = 0
    for value in values:
        low = min(low, value)
        high = max(high, value)
    return low, high""",
    variant_one="""def bounds(values):
    \"\"\"Return the smallest and largest of `values`.\"\"\"
    ordered = list(values)
    if not ordered:
        raise ValueError("the bounds of no values are undefined")
    low = ordered[0]
    high = ordered[0]
    for value in ordered[1:]:
        low = min(low, value)
        high = max(high, value)
    return low, high""",
    variant_two="""def bounds(values):
    \"\"\"Return the smallest and largest of `values`.\"\"\"
    ordered = sorted(values)
    if not ordered:
        raise ValueError("the bounds of no values are undefined")
    return ordered[0], ordered[-1]""",
    variant_three="""def bounds(values):
    \"\"\"Return the smallest and largest of `values`.\"\"\"
    ordered = list(values)
    if not ordered:
        raise ValueError("the bounds of no values are undefined")
    low = 0
    high = 0
    for value in ordered:
        low = min(low, value)
        high = max(high, value)
    return low, high""",
    variant_four="""def bounds(values):
    \"\"\"Return the smallest and largest of `values`.\"\"\"
    low = None
    high = None
    for value in values:
        low = value if low is None else min(low, value)
        high = value if high is None else max(high, value)
    return low, high""",
    visible_test=_test_module(
        "extent",
        "Published contract for extents.",
        """
def test_reports_both_bounds() -> None:
    assert bounds([3, -1, 7]) == (-1, 7)


def test_a_symmetric_range() -> None:
    assert bounds([-2, 0, 2]) == (-2, 2)
""",
        imports="from extent import bounds\n",
    ),
    hidden_test=_test_module(
        "extent",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reports_both_bounds() -> None:
    assert bounds([3, -1, 7]) == (-1, 7)


def test_no_values_are_refused() -> None:
    with pytest.raises(ValueError):
        bounds([])


def test_a_single_value_is_both_bounds() -> None:
    assert bounds([5]) == (5, 5)
""",
        imports="from extent import bounds\n",
    ),
)

_D22 = D2TaskSpec(
    template_id="d2_boundary.balanced_halves",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-halves",
    module="half_split",
    module_doc="Splitting a sequence into two halves.",
    issue=(
        "balanced_halves() is documented to split a sequence in two, giving the odd item to "
        "the first half. Callers report the odd item landing in the second half instead."
    ),
    expected=(
        "balanced_halves(items) returns (first, second) with the odd item in the first half, "
        "and accepts any iterable rather than only a sequence."
    ),
    baseline_reason="the midpoint rounds down and the length is taken before materialising",
    edge_cases=("an odd item goes to the first half", "any iterable is accepted"),
    baseline="""def balanced_halves(items):
    \"\"\"Split `items` in two, the odd item going to the first half.\"\"\"
    middle = len(items) // 2
    return list(items[:middle]), list(items[middle:])""",
    variant_one="""def balanced_halves(items):
    \"\"\"Split `items` in two, the odd item going to the first half.\"\"\"
    ordered = list(items)
    middle = (len(ordered) + 1) // 2
    return ordered[:middle], ordered[middle:]""",
    variant_two="""def balanced_halves(items):
    \"\"\"Split `items` in two, the odd item going to the first half.\"\"\"
    ordered = list(items)
    middle = -(-len(ordered) // 2)
    first = [item for position, item in enumerate(ordered) if position < middle]
    second = [item for position, item in enumerate(ordered) if position >= middle]
    return first, second""",
    variant_three="""def balanced_halves(items):
    \"\"\"Split `items` in two, the odd item going to the first half.\"\"\"
    middle = (len(items) + 1) // 2
    return list(items[:middle]), list(items[middle:])""",
    variant_four="""def balanced_halves(items):
    \"\"\"Split `items` in two, the odd item going to the first half.\"\"\"
    ordered = list(items)
    middle = len(ordered) // 2
    return ordered[:middle], ordered[middle:]""",
    visible_test=_test_module(
        "half_split",
        "Published contract for halving.",
        """
def test_splits_an_even_sequence() -> None:
    assert balanced_halves([1, 2, 3, 4]) == ([1, 2], [3, 4])


def test_an_empty_sequence_gives_two_empty_halves() -> None:
    assert balanced_halves([]) == ([], [])
""",
        imports="from half_split import balanced_halves\n",
    ),
    hidden_test=_test_module(
        "half_split",
        "The part of the contract the published tests do not state.",
        """
def test_splits_an_even_sequence() -> None:
    assert balanced_halves([1, 2, 3, 4]) == ([1, 2], [3, 4])


def test_an_odd_item_goes_to_the_first_half() -> None:
    assert balanced_halves([1, 2, 3]) == ([1, 2], [3])


def test_any_iterable_is_accepted() -> None:
    assert balanced_halves(iter([1, 2, 3, 4])) == ([1, 2], [3, 4])
""",
        imports="from half_split import balanced_halves\n",
    ),
)

_D23 = D2TaskSpec(
    template_id="d2_boundary.dedupe_adjacent",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-adjacent-dedupe",
    module="adjacent_dedupe",
    module_doc="Collapsing runs of equal adjacent items.",
    issue=(
        "dedupe_adjacent() is documented to collapse runs of equal *adjacent* items. Callers "
        "report values that recur later in the sequence disappearing, and a crash on lists."
    ),
    expected=(
        "dedupe_adjacent(items) collapses runs of equal adjacent items, keeps a repeat that is "
        "not adjacent, and accepts unhashable items."
    ),
    baseline_reason="a set of everything seen makes the check global and demands hashability",
    edge_cases=(
        "a repeat that is not adjacent is kept",
        "unhashable items are accepted",
    ),
    baseline="""def dedupe_adjacent(items):
    \"\"\"Collapse runs of equal adjacent items in `items`.\"\"\"
    seen = set()
    kept = []
    for item in items:
        if item not in seen:
            kept.append(item)
            seen.add(item)
    return kept""",
    variant_one="""def dedupe_adjacent(items):
    \"\"\"Collapse runs of equal adjacent items in `items`.\"\"\"
    kept = []
    for item in items:
        if not kept or kept[-1] != item:
            kept.append(item)
    return kept""",
    variant_two="""def dedupe_adjacent(items):
    \"\"\"Collapse runs of equal adjacent items in `items`.\"\"\"
    from itertools import groupby

    return [key for key, _ in groupby(items)]""",
    variant_three="""def dedupe_adjacent(items):
    \"\"\"Collapse runs of equal adjacent items in `items`.\"\"\"
    kept = []
    previous = set()
    for item in items:
        if item not in previous:
            kept.append(item)
        previous = {item}
    return kept""",
    variant_four="""def dedupe_adjacent(items):
    \"\"\"Collapse runs of equal adjacent items in `items`.\"\"\"
    kept = []
    for item in items:
        if item not in kept:
            kept.append(item)
    return kept""",
    visible_test=_test_module(
        "adjacent_dedupe",
        "Published contract for adjacent deduplication.",
        """
def test_collapses_a_run() -> None:
    assert dedupe_adjacent([1, 1, 2, 3]) == [1, 2, 3]


def test_a_sequence_without_runs_is_unchanged() -> None:
    assert dedupe_adjacent([1, 2, 3]) == [1, 2, 3]
""",
        imports="from adjacent_dedupe import dedupe_adjacent\n",
    ),
    hidden_test=_test_module(
        "adjacent_dedupe",
        "The part of the contract the published tests do not state.",
        """
def test_collapses_a_run() -> None:
    assert dedupe_adjacent([1, 1, 2, 3]) == [1, 2, 3]


def test_a_repeat_that_is_not_adjacent_is_kept() -> None:
    assert dedupe_adjacent([1, 2, 1]) == [1, 2, 1]


def test_unhashable_items_are_accepted() -> None:
    assert dedupe_adjacent([[1], [1], [2]]) == [[1], [2]]
""",
        imports="from adjacent_dedupe import dedupe_adjacent\n",
    ),
)

_D24 = D2TaskSpec(
    template_id="d2_boundary.first_gap",
    family=RealityTaskFamily.BOUNDARY_COLLECTIONS,
    repository_group="d2-boundary-first-gap",
    module="gap_finding",
    module_doc="Finding the first missing non-negative integer.",
    issue=(
        "first_gap() is documented to return the smallest non-negative integer missing from a "
        "sorted list. Callers report duplicates pushing the answer past the real gap."
    ),
    expected=(
        "first_gap(numbers) returns the smallest missing non-negative integer, is unaffected "
        "by duplicates, and raises ValueError when any number is negative."
    ),
    baseline_reason="counting every value at or below the candidate advances once per duplicate",
    edge_cases=("a duplicate does not shift the gap", "a negative number is refused"),
    baseline="""def first_gap(numbers):
    \"\"\"Return the smallest non-negative integer missing from `numbers`.\"\"\"
    candidate = 0
    for value in numbers:
        if value <= candidate:
            candidate += 1
    return candidate""",
    variant_one="""def first_gap(numbers):
    \"\"\"Return the smallest non-negative integer missing from `numbers`.\"\"\"
    if any(value < 0 for value in numbers):
        raise ValueError("the numbers must be non-negative")
    present = set(numbers)
    candidate = 0
    while candidate in present:
        candidate += 1
    return candidate""",
    variant_two="""def first_gap(numbers):
    \"\"\"Return the smallest non-negative integer missing from `numbers`.\"\"\"
    candidate = 0
    for value in sorted(set(numbers)):
        if value < 0:
            raise ValueError("the numbers must be non-negative")
        if value != candidate:
            break
        candidate += 1
    return candidate""",
    variant_three="""def first_gap(numbers):
    \"\"\"Return the smallest non-negative integer missing from `numbers`.\"\"\"
    candidate = 0
    for value in sorted(set(numbers)):
        if value <= candidate:
            candidate += 1
    return candidate""",
    variant_four="""def first_gap(numbers):
    \"\"\"Return the smallest non-negative integer missing from `numbers`.\"\"\"
    if any(value < 0 for value in numbers):
        raise ValueError("the numbers must be non-negative")
    candidate = 0
    for value in numbers:
        if value <= candidate:
            candidate += 1
    return candidate""",
    visible_test=_test_module(
        "gap_finding",
        "Published contract for gap finding.",
        """
def test_finds_the_first_gap() -> None:
    assert first_gap([0, 1, 3]) == 2


def test_a_complete_run_gaps_after_the_end() -> None:
    assert first_gap([0, 1, 2]) == 3
""",
        imports="from gap_finding import first_gap\n",
    ),
    hidden_test=_test_module(
        "gap_finding",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_finds_the_first_gap() -> None:
    assert first_gap([0, 1, 3]) == 2


def test_a_duplicate_does_not_shift_the_gap() -> None:
    assert first_gap([0, 0, 1]) == 2


def test_a_negative_number_is_refused() -> None:
    with pytest.raises(ValueError):
        first_gap([-1, 0])
""",
        imports="from gap_finding import first_gap\n",
    ),
)

# ----------------------------------------------------------- parsing and validation, S21D2-022

_D25 = D2TaskSpec(
    template_id="d2_parsing.parse_range",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-range",
    module="range_parsing",
    module_doc="Reading an inclusive numeric range.",
    issue=(
        "parse_range() is documented to read '3-7' as an inclusive range. Callers report a "
        "crash on a bare number and no complaint at all about a range written backwards."
    ),
    expected=(
        "parse_range(text) returns (low, high) for 'low-high', reads a bare number as a range "
        "of one, and raises ValueError when the high bound is below the low one."
    ),
    baseline_reason="unpacking demands two parts and neither bound is ever compared",
    edge_cases=("a bare number is a range of one", "a reversed range is refused"),
    baseline="""def parse_range(text):
    \"\"\"Read `text` as an inclusive numeric range.\"\"\"
    low, high = text.split("-")
    return int(low), int(high)""",
    variant_one="""def parse_range(text):
    \"\"\"Read `text` as an inclusive numeric range.\"\"\"
    parts = text.split("-")
    if len(parts) == 1:
        only = int(parts[0])
        return only, only
    low = int(parts[0])
    high = int(parts[1])
    if low > high:
        raise ValueError(f"{text!r} is a reversed range")
    return low, high""",
    variant_two="""def parse_range(text):
    \"\"\"Read `text` as an inclusive numeric range.\"\"\"
    head, separator, tail = text.partition("-")
    low = int(head)
    high = int(tail) if separator else low
    if high < low:
        raise ValueError(f"{text!r} is a reversed range")
    return low, high""",
    variant_three="""def parse_range(text):
    \"\"\"Read `text` as an inclusive numeric range.\"\"\"
    parts = text.split("-")
    if len(parts) == 1:
        only = int(parts[0])
        return only, only
    return int(parts[0]), int(parts[1])""",
    variant_four="""def parse_range(text):
    \"\"\"Read `text` as an inclusive numeric range.\"\"\"
    low, high = text.split("-")
    if int(low) > int(high):
        raise ValueError(f"{text!r} is a reversed range")
    return int(low), int(high)""",
    visible_test=_test_module(
        "range_parsing",
        "Published contract for range parsing.",
        """
def test_reads_a_range() -> None:
    assert parse_range("3-7") == (3, 7)


def test_reads_a_range_of_two() -> None:
    assert parse_range("1-2") == (1, 2)
""",
        imports="from range_parsing import parse_range\n",
    ),
    hidden_test=_test_module(
        "range_parsing",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_a_range() -> None:
    assert parse_range("3-7") == (3, 7)


def test_a_bare_number_is_a_range_of_one() -> None:
    assert parse_range("5") == (5, 5)


def test_a_reversed_range_is_refused() -> None:
    with pytest.raises(ValueError, match="reversed"):
        parse_range("7-3")
""",
        imports="from range_parsing import parse_range\n",
    ),
)

_D26 = D2TaskSpec(
    template_id="d2_parsing.strip_comment",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-comment",
    module="comment_stripping",
    module_doc="Removing trailing comments from a configuration line.",
    issue=(
        "strip_comment() is documented to remove a trailing comment. Callers report quoted "
        "values being cut in half and colour codes losing everything after the hash."
    ),
    expected=(
        "strip_comment(line) removes a trailing comment, keeps a hash inside a quoted string, "
        "and only treats a hash as a comment when it opens the line or follows whitespace."
    ),
    baseline_reason="splitting on the first hash ignores quoting and what precedes the hash",
    edge_cases=(
        "a hash inside quotes is kept",
        "a hash without leading space is not a comment",
    ),
    baseline="""def strip_comment(line):
    \"\"\"Return `line` with any trailing comment removed.\"\"\"
    return line.split("#")[0].rstrip()""",
    variant_one="""def strip_comment(line):
    \"\"\"Return `line` with any trailing comment removed.\"\"\"
    quote = ""
    for index, character in enumerate(line):
        if quote:
            if character == quote:
                quote = ""
        elif character in "'\\"":
            quote = character
        elif character == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()""",
    variant_two="""def strip_comment(line):
    \"\"\"Return `line` with any trailing comment removed.\"\"\"
    import re

    pattern = re.compile(r'''('[^']*'|"[^"]*")|(?:^|(?<=\\s))#.*$''')

    def keep_quoted(match):
        return match.group(1) or ""

    return pattern.sub(keep_quoted, line).rstrip()""",
    variant_three="""def strip_comment(line):
    \"\"\"Return `line` with any trailing comment removed.\"\"\"
    quote = ""
    for index, character in enumerate(line):
        if quote:
            if character == quote:
                quote = ""
        elif character in "'\\"":
            quote = character
        elif character == "#":
            return line[:index].rstrip()
    return line.rstrip()""",
    variant_four="""def strip_comment(line):
    \"\"\"Return `line` with any trailing comment removed.\"\"\"
    for index, character in enumerate(line):
        if character == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index].rstrip()
    return line.rstrip()""",
    visible_test=_test_module(
        "comment_stripping",
        "Published contract for comment stripping.",
        """
def test_removes_a_trailing_comment() -> None:
    assert strip_comment("value = 1  # why") == "value = 1"


def test_a_line_without_a_comment_is_unchanged() -> None:
    assert strip_comment("value = 1") == "value = 1"
""",
        imports="from comment_stripping import strip_comment\n",
    ),
    hidden_test=_test_module(
        "comment_stripping",
        "The part of the contract the published tests do not state.",
        """
def test_removes_a_trailing_comment() -> None:
    assert strip_comment("value = 1  # why") == "value = 1"


def test_a_hash_inside_quotes_is_kept() -> None:
    assert strip_comment("name = 'a # b'") == "name = 'a # b'"


def test_a_hash_without_leading_space_is_not_a_comment() -> None:
    assert strip_comment("colour=#fff") == "colour=#fff"
""",
        imports="from comment_stripping import strip_comment\n",
    ),
)

_D27 = D2TaskSpec(
    template_id="d2_parsing.parse_size",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-size",
    module="size_parsing",
    module_doc="Reading a byte size with an optional unit.",
    issue=(
        "parse_size() is documented to read sizes like '10kb'. Callers report a crash on an "
        "upper-case unit and on a plain number of bytes with no unit at all."
    ),
    expected=(
        "parse_size(text) returns the size in bytes, accepts the unit in any case, and reads "
        "a bare number as a count of bytes."
    ),
    baseline_reason="the last two characters are always taken as the unit and matched exactly",
    edge_cases=("the unit is case insensitive", "a bare number means bytes"),
    baseline="""def parse_size(text):
    \"\"\"Return the size `text` describes, in bytes.\"\"\"
    units = {"b": 1, "kb": 1024, "mb": 1024 * 1024}
    return int(text[:-2]) * units[text[-2:]]""",
    variant_one="""def parse_size(text):
    \"\"\"Return the size `text` describes, in bytes.\"\"\"
    units = {"b": 1, "kb": 1024, "mb": 1024 * 1024}
    cleaned = text.strip().lower()
    for suffix in ("mb", "kb", "b"):
        if cleaned.endswith(suffix):
            return int(cleaned[: -len(suffix)]) * units[suffix]
    return int(cleaned)""",
    variant_two="""def parse_size(text):
    \"\"\"Return the size `text` describes, in bytes.\"\"\"
    import re

    units = {"": 1, "b": 1, "kb": 1024, "mb": 1024 * 1024}
    match = re.fullmatch(r"\\s*(\\d+)\\s*([a-zA-Z]*)\\s*", text)
    if match is None:
        raise ValueError(f"{text!r} is not a size")
    return int(match.group(1)) * units[match.group(2).lower()]""",
    variant_three="""def parse_size(text):
    \"\"\"Return the size `text` describes, in bytes.\"\"\"
    units = {"b": 1, "kb": 1024, "mb": 1024 * 1024}
    cleaned = text.lower()
    return int(cleaned[:-2]) * units[cleaned[-2:]]""",
    variant_four="""def parse_size(text):
    \"\"\"Return the size `text` describes, in bytes.\"\"\"
    units = {"b": 1, "kb": 1024, "mb": 1024 * 1024}
    if text.isdigit():
        return int(text)
    return int(text[:-2]) * units[text[-2:]]""",
    visible_test=_test_module(
        "size_parsing",
        "Published contract for size parsing.",
        """
def test_reads_kilobytes() -> None:
    assert parse_size("10kb") == 10240


def test_reads_megabytes() -> None:
    assert parse_size("2mb") == 2097152
""",
        imports="from size_parsing import parse_size\n",
    ),
    hidden_test=_test_module(
        "size_parsing",
        "The part of the contract the published tests do not state.",
        """
def test_reads_kilobytes() -> None:
    assert parse_size("10kb") == 10240


def test_the_unit_is_case_insensitive() -> None:
    assert parse_size("10KB") == 10240


def test_a_bare_number_means_bytes() -> None:
    assert parse_size("512") == 512
""",
        imports="from size_parsing import parse_size\n",
    ),
)

_D28 = D2TaskSpec(
    template_id="d2_parsing.parse_time_of_day",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-clock",
    module="clock_parsing",
    module_doc="Reading a time of day.",
    issue=(
        "parse_time_of_day() is documented to read '14:30'. Callers report an hour of 25 being "
        "accepted, and a crash on a single-digit hour such as '9:05'."
    ),
    expected=(
        "parse_time_of_day(text) returns (hour, minute), accepts a single-digit hour, and "
        "raises ValueError for an hour or minute outside a real day."
    ),
    baseline_reason="fixed character offsets assume two digits and nothing checks the range",
    edge_cases=("an hour beyond the day is refused", "a single-digit hour is accepted"),
    baseline="""def parse_time_of_day(text):
    \"\"\"Read `text` as a time of day.\"\"\"
    return int(text[:2]), int(text[3:])""",
    variant_one="""def parse_time_of_day(text):
    \"\"\"Read `text` as a time of day.\"\"\"
    hour_text, _, minute_text = text.partition(":")
    hour = int(hour_text)
    minute = int(minute_text)
    if not 0 <= hour < 24 or not 0 <= minute < 60:
        raise ValueError(f"{text!r} is not a time of day")
    return hour, minute""",
    variant_two="""def parse_time_of_day(text):
    \"\"\"Read `text` as a time of day.\"\"\"
    import re

    match = re.fullmatch(r"([01]?\\d|2[0-3]):([0-5]\\d)", text)
    if match is None:
        raise ValueError(f"{text!r} is not a time of day")
    return int(match.group(1)), int(match.group(2))""",
    variant_three="""def parse_time_of_day(text):
    \"\"\"Read `text` as a time of day.\"\"\"
    hour = int(text[:2])
    minute = int(text[3:])
    if not 0 <= hour < 24:
        raise ValueError(f"{text!r} is not a time of day")
    return hour, minute""",
    variant_four="""def parse_time_of_day(text):
    \"\"\"Read `text` as a time of day.\"\"\"
    hour_text, _, minute_text = text.partition(":")
    return int(hour_text), int(minute_text)""",
    visible_test=_test_module(
        "clock_parsing",
        "Published contract for clock parsing.",
        """
def test_reads_a_time() -> None:
    assert parse_time_of_day("14:30") == (14, 30)


def test_reads_midnight() -> None:
    assert parse_time_of_day("00:00") == (0, 0)
""",
        imports="from clock_parsing import parse_time_of_day\n",
    ),
    hidden_test=_test_module(
        "clock_parsing",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_a_time() -> None:
    assert parse_time_of_day("14:30") == (14, 30)


def test_an_hour_beyond_the_day_is_refused() -> None:
    with pytest.raises(ValueError):
        parse_time_of_day("25:00")


def test_a_single_digit_hour_is_accepted() -> None:
    assert parse_time_of_day("9:05") == (9, 5)
""",
        imports="from clock_parsing import parse_time_of_day\n",
    ),
)

_D29 = D2TaskSpec(
    template_id="d2_parsing.parse_flags",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-flags",
    module="flag_parsing",
    module_doc="Reading a comma-separated flag list.",
    issue=(
        "parse_flags() is documented to read a comma-separated flag list. Callers report empty "
        "entries appearing in the result and the same flag listed twice being kept twice."
    ),
    expected=(
        "parse_flags(text) returns the flags in order, drops empty entries, and keeps only the "
        "first occurrence of a repeated flag."
    ),
    baseline_reason="every segment is kept, including the empty ones and the repeats",
    edge_cases=("an empty segment is dropped", "a repeated flag is kept once"),
    baseline="""def parse_flags(text):
    \"\"\"Read `text` as a list of flags.\"\"\"
    return [part.strip() for part in text.split(",")]""",
    variant_one="""def parse_flags(text):
    \"\"\"Read `text` as a list of flags.\"\"\"
    flags = []
    for part in text.split(","):
        name = part.strip()
        if name and name not in flags:
            flags.append(name)
    return flags""",
    variant_two="""def parse_flags(text):
    \"\"\"Read `text` as a list of flags.\"\"\"
    stripped = (part.strip() for part in text.split(","))
    return list(dict.fromkeys(part for part in stripped if part))""",
    variant_three="""def parse_flags(text):
    \"\"\"Read `text` as a list of flags.\"\"\"
    return [name for part in text.split(",") if (name := part.strip())]""",
    variant_four="""def parse_flags(text):
    \"\"\"Read `text` as a list of flags.\"\"\"
    flags = []
    for part in text.split(","):
        name = part.strip()
        if name not in flags:
            flags.append(name)
    return flags""",
    visible_test=_test_module(
        "flag_parsing",
        "Published contract for flag parsing.",
        """
def test_reads_three_flags() -> None:
    assert parse_flags("a, b, c") == ["a", "b", "c"]


def test_reads_a_single_flag() -> None:
    assert parse_flags("only") == ["only"]
""",
        imports="from flag_parsing import parse_flags\n",
    ),
    hidden_test=_test_module(
        "flag_parsing",
        "The part of the contract the published tests do not state.",
        """
def test_reads_three_flags() -> None:
    assert parse_flags("a, b, c") == ["a", "b", "c"]


def test_an_empty_segment_is_dropped() -> None:
    assert parse_flags("a,,b") == ["a", "b"]


def test_a_repeated_flag_is_kept_once() -> None:
    assert parse_flags("a,b,a") == ["a", "b"]
""",
        imports="from flag_parsing import parse_flags\n",
    ),
)

_D30 = D2TaskSpec(
    template_id="d2_parsing.normalize_slashes",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-path",
    module="path_normalising",
    module_doc="Normalising a slash-separated path.",
    issue=(
        "normalize_slashes() is documented to tidy a path. Callers report absolute paths "
        "coming back relative, and '.' segments surviving the tidy-up."
    ),
    expected=(
        "normalize_slashes(path) collapses repeated slashes, drops a trailing one, keeps a "
        "leading slash when there was one, and drops any '.' segment."
    ),
    baseline_reason="joining the non-empty segments discards the leading slash and keeps dots",
    edge_cases=("a leading slash is preserved", "a dot segment is dropped"),
    baseline="""def normalize_slashes(path):
    \"\"\"Return `path` with its separators tidied.\"\"\"
    return "/".join(part for part in path.split("/") if part)""",
    variant_one="""def normalize_slashes(path):
    \"\"\"Return `path` with its separators tidied.\"\"\"
    parts = [part for part in path.split("/") if part and part != "."]
    joined = "/".join(parts)
    return "/" + joined if path.startswith("/") else joined""",
    variant_two="""def normalize_slashes(path):
    \"\"\"Return `path` with its separators tidied.\"\"\"
    import re

    collapsed = re.sub(r"/+", "/", path)
    kept = [part for part in collapsed.split("/") if part != "."]
    joined = "/".join(kept)
    if len(joined) > 1:
        joined = joined.rstrip("/")
    return joined""",
    variant_three="""def normalize_slashes(path):
    \"\"\"Return `path` with its separators tidied.\"\"\"
    parts = [part for part in path.split("/") if part]
    joined = "/".join(parts)
    return "/" + joined if path.startswith("/") else joined""",
    variant_four="""def normalize_slashes(path):
    \"\"\"Return `path` with its separators tidied.\"\"\"
    return "/".join(part for part in path.split("/") if part and part != ".")""",
    visible_test=_test_module(
        "path_normalising",
        "Published contract for path normalisation.",
        """
def test_collapses_repeated_slashes() -> None:
    assert normalize_slashes("a//b") == "a/b"


def test_removes_a_trailing_slash() -> None:
    assert normalize_slashes("a/b/") == "a/b"
""",
        imports="from path_normalising import normalize_slashes\n",
    ),
    hidden_test=_test_module(
        "path_normalising",
        "The part of the contract the published tests do not state.",
        """
def test_collapses_repeated_slashes() -> None:
    assert normalize_slashes("a//b") == "a/b"


def test_a_leading_slash_is_preserved() -> None:
    assert normalize_slashes("/a/b") == "/a/b"


def test_a_dot_segment_is_dropped() -> None:
    assert normalize_slashes("a/./b") == "a/b"
""",
        imports="from path_normalising import normalize_slashes\n",
    ),
)

_D31 = D2TaskSpec(
    template_id="d2_parsing.is_valid_code",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-checksum",
    module="checksum_validation",
    module_doc="Validating a code whose last digit is a checksum.",
    issue=(
        "is_valid_code() is documented to validate a code whose final digit is the sum of the "
        "others modulo ten. Callers report a one-character code being answered rather than "
        "refused, and errors that name a single character instead of the code they passed."
    ),
    expected=(
        "is_valid_code(text) returns whether the final digit is the checksum of the rest, "
        "raises a ValueError naming the whole code for a code shorter than two characters, "
        "and raises a ValueError naming the whole code when any character is not a digit."
    ),
    baseline_reason="nothing checks the length, and int() is left to complain about a fragment",
    edge_cases=(
        "a single digit is refused",
        "a non-digit names the whole code",
    ),
    baseline="""def is_valid_code(text):
    \"\"\"Report whether the last digit of `text` checksums the rest.\"\"\"
    total = sum(int(character) for character in text[:-1])
    return total % 10 == int(text[-1])""",
    variant_one="""def is_valid_code(text):
    \"\"\"Report whether the last digit of `text` checksums the rest.\"\"\"
    if len(text) < 2 or not text.isdigit():
        raise ValueError(f"{text!r} is not a code")
    total = sum(int(character) for character in text[:-1])
    return total % 10 == int(text[-1])""",
    variant_two="""def is_valid_code(text):
    \"\"\"Report whether the last digit of `text` checksums the rest.\"\"\"
    digits = []
    for character in text:
        if not character.isdigit():
            raise ValueError(f"{text!r} is not a code")
        digits.append(int(character))
    if len(digits) < 2:
        raise ValueError(f"{text!r} is not a code")
    *payload, check = digits
    return sum(payload) % 10 == check""",
    variant_three="""def is_valid_code(text):
    \"\"\"Report whether the last digit of `text` checksums the rest.\"\"\"
    if len(text) < 2:
        raise ValueError(f"{text!r} is not a code")
    total = sum(int(character) for character in text[:-1])
    return total % 10 == int(text[-1])""",
    variant_four="""def is_valid_code(text):
    \"\"\"Report whether the last digit of `text` checksums the rest.\"\"\"
    if not text.isdigit():
        raise ValueError(f"{text!r} is not a code")
    total = sum(int(character) for character in text[:-1])
    return total % 10 == int(text[-1])""",
    visible_test=_test_module(
        "checksum_validation",
        "Published contract for code validation.",
        """
def test_accepts_a_valid_code() -> None:
    assert is_valid_code("1236") is True


def test_rejects_a_wrong_check_digit() -> None:
    assert is_valid_code("1235") is False
""",
        imports="from checksum_validation import is_valid_code\n",
    ),
    hidden_test=_test_module(
        "checksum_validation",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_accepts_a_valid_code() -> None:
    assert is_valid_code("1236") is True


def test_a_single_digit_is_refused() -> None:
    with pytest.raises(ValueError):
        is_valid_code("7")


def test_a_non_digit_names_the_whole_code() -> None:
    with pytest.raises(ValueError, match="12x3"):
        is_valid_code("12x3")
""",
        imports="from checksum_validation import is_valid_code\n",
    ),
)

_D32 = D2TaskSpec(
    template_id="d2_parsing.parse_query",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-query",
    module="query_parsing",
    module_doc="Reading a query string into pairs.",
    issue=(
        "parse_query() is documented to read 'a=1&b=2' into pairs. Callers report a crash on "
        "values that themselves contain an equals sign, and on keys with no value at all."
    ),
    expected=(
        "parse_query(text) returns the pairs, splits each chunk at its first equals sign only, "
        "and maps a key written without a value to an empty string."
    ),
    baseline_reason="unpacking a full split demands exactly one equals sign in every chunk",
    edge_cases=(
        "a value containing an equals sign is kept whole",
        "a key without a value maps to an empty string",
    ),
    baseline="""def parse_query(text):
    \"\"\"Read `text` as query-string pairs.\"\"\"
    pairs = {}
    for chunk in text.split("&"):
        key, value = chunk.split("=")
        pairs[key] = value
    return pairs""",
    variant_one="""def parse_query(text):
    \"\"\"Read `text` as query-string pairs.\"\"\"
    pairs = {}
    for chunk in text.split("&"):
        key, separator, value = chunk.partition("=")
        pairs[key] = value if separator else ""
    return pairs""",
    variant_two="""def parse_query(text):
    \"\"\"Read `text` as query-string pairs.\"\"\"
    chunks = (chunk.partition("=") for chunk in text.split("&"))
    return {key: value for key, _, value in chunks}""",
    variant_three="""def parse_query(text):
    \"\"\"Read `text` as query-string pairs.\"\"\"
    pairs = {}
    for chunk in text.split("&"):
        key, value = chunk.split("=", 1)
        pairs[key] = value
    return pairs""",
    variant_four="""def parse_query(text):
    \"\"\"Read `text` as query-string pairs.\"\"\"
    pairs = {}
    for chunk in text.split("&"):
        if "=" not in chunk:
            pairs[chunk] = ""
            continue
        key, value = chunk.split("=")
        pairs[key] = value
    return pairs""",
    visible_test=_test_module(
        "query_parsing",
        "Published contract for query parsing.",
        """
def test_reads_two_pairs() -> None:
    assert parse_query("a=1&b=2") == {"a": "1", "b": "2"}


def test_reads_one_pair() -> None:
    assert parse_query("only=1") == {"only": "1"}
""",
        imports="from query_parsing import parse_query\n",
    ),
    hidden_test=_test_module(
        "query_parsing",
        "The part of the contract the published tests do not state.",
        """
def test_reads_two_pairs() -> None:
    assert parse_query("a=1&b=2") == {"a": "1", "b": "2"}


def test_a_value_containing_an_equals_sign_is_kept_whole() -> None:
    assert parse_query("a=1=2") == {"a": "1=2"}


def test_a_key_without_a_value_maps_to_an_empty_string() -> None:
    assert parse_query("flag") == {"flag": ""}
""",
        imports="from query_parsing import parse_query\n",
    ),
)

_D33 = D2TaskSpec(
    template_id="d2_parsing.is_valid_name",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-name",
    module="name_validation",
    module_doc="Validating a generated attribute name.",
    issue=(
        "is_valid_name() is documented to accept only names that could be written in source. "
        "Callers report names beginning with a digit and language keywords being accepted."
    ),
    expected=(
        "is_valid_name(text) returns True only for a name that could be an identifier: no "
        "leading digit, no keyword, and nothing but letters, digits and underscores."
    ),
    baseline_reason="checking the characters says nothing about the first one or about keywords",
    edge_cases=("a leading digit is invalid", "a keyword is invalid"),
    baseline="""def is_valid_name(text):
    \"\"\"Report whether `text` could be an attribute name.\"\"\"
    return bool(text) and all(character.isalnum() or character == "_" for character in text)""",
    variant_one="""def is_valid_name(text):
    \"\"\"Report whether `text` could be an attribute name.\"\"\"
    import keyword

    if not text or text[0].isdigit():
        return False
    if keyword.iskeyword(text):
        return False
    return all(character.isalnum() or character == "_" for character in text)""",
    variant_two="""def is_valid_name(text):
    \"\"\"Report whether `text` could be an attribute name.\"\"\"
    import keyword

    return text.isidentifier() and not keyword.iskeyword(text)""",
    variant_three="""def is_valid_name(text):
    \"\"\"Report whether `text` could be an attribute name.\"\"\"
    if not text or text[0].isdigit():
        return False
    return all(character.isalnum() or character == "_" for character in text)""",
    variant_four="""def is_valid_name(text):
    \"\"\"Report whether `text` could be an attribute name.\"\"\"
    import keyword

    if keyword.iskeyword(text):
        return False
    return bool(text) and all(character.isalnum() or character == "_" for character in text)""",
    visible_test=_test_module(
        "name_validation",
        "Published contract for name validation.",
        """
def test_accepts_a_plain_name() -> None:
    assert is_valid_name("total_count") is True


def test_rejects_a_name_with_a_space() -> None:
    assert is_valid_name("two words") is False
""",
        imports="from name_validation import is_valid_name\n",
    ),
    hidden_test=_test_module(
        "name_validation",
        "The part of the contract the published tests do not state.",
        """
def test_accepts_a_plain_name() -> None:
    assert is_valid_name("total_count") is True


def test_a_leading_digit_is_invalid() -> None:
    assert is_valid_name("1abc") is False


def test_a_keyword_is_invalid() -> None:
    assert is_valid_name("class") is False
""",
        imports="from name_validation import is_valid_name\n",
    ),
)

_D34 = D2TaskSpec(
    template_id="d2_parsing.parse_csv_row",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-csv-row",
    module="row_parsing",
    module_doc="Reading one row of comma-separated values.",
    issue=(
        "parse_csv_row() is documented to read one row. Callers report quoted fields being cut "
        "at the comma inside them, and a row ending in a comma losing its final empty field."
    ),
    expected=(
        "parse_csv_row(text) returns the fields, does not split at a comma inside quotes, and "
        "keeps a trailing empty field."
    ),
    baseline_reason="splitting on every comma ignores quoting, and empty fields are filtered out",
    edge_cases=(
        "a comma inside quotes does not split",
        "a trailing empty field is kept",
    ),
    baseline="""def parse_csv_row(text):
    \"\"\"Read `text` as one row of comma-separated values.\"\"\"
    return [field for field in text.split(",") if field]""",
    variant_one="""def parse_csv_row(text):
    \"\"\"Read `text` as one row of comma-separated values.\"\"\"
    import csv

    return next(csv.reader([text]))""",
    variant_two="""def parse_csv_row(text):
    \"\"\"Read `text` as one row of comma-separated values.\"\"\"
    fields = []
    current = []
    quoted = False
    for character in text:
        if character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    fields.append("".join(current))
    return fields""",
    variant_three="""def parse_csv_row(text):
    \"\"\"Read `text` as one row of comma-separated values.\"\"\"
    fields = []
    current = []
    quoted = False
    for character in text:
        if character == '"':
            quoted = not quoted
        elif character == "," and not quoted:
            if current:
                fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if current:
        fields.append("".join(current))
    return fields""",
    variant_four="""def parse_csv_row(text):
    \"\"\"Read `text` as one row of comma-separated values.\"\"\"
    return text.split(",")""",
    visible_test=_test_module(
        "row_parsing",
        "Published contract for row parsing.",
        """
def test_reads_three_fields() -> None:
    assert parse_csv_row("a,b,c") == ["a", "b", "c"]


def test_reads_a_single_field() -> None:
    assert parse_csv_row("only") == ["only"]
""",
        imports="from row_parsing import parse_csv_row\n",
    ),
    hidden_test=_test_module(
        "row_parsing",
        "The part of the contract the published tests do not state.",
        """
def test_reads_three_fields() -> None:
    assert parse_csv_row("a,b,c") == ["a", "b", "c"]


def test_a_comma_inside_quotes_does_not_split() -> None:
    assert parse_csv_row('a,"b,c",d') == ["a", "b,c", "d"]


def test_a_trailing_empty_field_is_kept() -> None:
    assert parse_csv_row("a,b,") == ["a", "b", ""]
""",
        imports="from row_parsing import parse_csv_row\n",
    ),
)

_D35 = D2TaskSpec(
    template_id="d2_parsing.titlecase_words",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-title",
    module="title_casing",
    module_doc="Title-casing a heading.",
    issue=(
        "titlecase_words() is documented to title-case a heading. Callers report hyphenated "
        "words only having their first part capitalised, and acronyms being flattened."
    ),
    expected=(
        "titlecase_words(text) capitalises each word, capitalises both parts of a hyphenated "
        "word, and leaves a word that is already all upper case alone."
    ),
    baseline_reason="capitalize() lowercases everything after the first letter of each word",
    edge_cases=("a hyphenated word capitalises both parts", "an acronym is left alone"),
    baseline="""def titlecase_words(text):
    \"\"\"Return `text` with each word title-cased.\"\"\"
    return " ".join(word.capitalize() for word in text.split(" "))""",
    variant_one="""def titlecase_words(text):
    \"\"\"Return `text` with each word title-cased.\"\"\"

    def fix(word):
        if word.isupper():
            return word
        return "-".join(part.capitalize() for part in word.split("-"))

    return " ".join(fix(word) for word in text.split(" "))""",
    variant_two="""def titlecase_words(text):
    \"\"\"Return `text` with each word title-cased.\"\"\"
    words = []
    for word in text.split(" "):
        if word.isupper():
            words.append(word)
            continue
        rebuilt = ""
        capitalise = True
        for character in word:
            rebuilt += character.upper() if capitalise else character.lower()
            capitalise = character == "-"
        words.append(rebuilt)
    return " ".join(words)""",
    variant_three="""def titlecase_words(text):
    \"\"\"Return `text` with each word title-cased.\"\"\"

    def fix(word):
        return "-".join(part.capitalize() for part in word.split("-"))

    return " ".join(fix(word) for word in text.split(" "))""",
    variant_four="""def titlecase_words(text):
    \"\"\"Return `text` with each word title-cased.\"\"\"
    words = []
    for word in text.split(" "):
        words.append(word if word.isupper() else word.capitalize())
    return " ".join(words)""",
    visible_test=_test_module(
        "title_casing",
        "Published contract for title casing.",
        """
def test_capitalises_each_word() -> None:
    assert titlecase_words("hello there") == "Hello There"


def test_lowercases_the_rest_of_a_word() -> None:
    assert titlecase_words("hELLO") == "Hello"
""",
        imports="from title_casing import titlecase_words\n",
    ),
    hidden_test=_test_module(
        "title_casing",
        "The part of the contract the published tests do not state.",
        """
def test_capitalises_each_word() -> None:
    assert titlecase_words("hello there") == "Hello There"


def test_a_hyphenated_word_capitalises_both_parts() -> None:
    assert titlecase_words("well-known issue") == "Well-Known Issue"


def test_an_acronym_is_left_alone() -> None:
    assert titlecase_words("the HTTP layer") == "The HTTP Layer"
""",
        imports="from title_casing import titlecase_words\n",
    ),
)

_D36 = D2TaskSpec(
    template_id="d2_parsing.parse_ints",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-int-list",
    module="integer_list",
    module_doc="Reading a comma-separated list of integers.",
    issue=(
        "parse_ints() is documented to read a comma-separated list of integers. Callers report "
        "a crash on an empty setting, and errors that name a fragment instead of the setting."
    ),
    expected=(
        "parse_ints(text) returns the integers, returns an empty list for an empty or blank "
        "string, and raises a ValueError naming the whole input when an entry is not a number."
    ),
    baseline_reason="int() is left to complain, and it complains about a fragment it was handed",
    edge_cases=(
        "an empty string is an empty list",
        "a non-numeric entry names the whole input",
    ),
    baseline="""def parse_ints(text):
    \"\"\"Read `text` as a list of integers.\"\"\"
    return [int(part) for part in text.split(",")]""",
    variant_one="""def parse_ints(text):
    \"\"\"Read `text` as a list of integers.\"\"\"
    if not text.strip():
        return []
    values = []
    for part in text.split(","):
        stripped = part.strip()
        if not stripped.lstrip("+-").isdigit():
            raise ValueError(f"{text!r} is not a list of integers")
        values.append(int(stripped))
    return values""",
    variant_two="""def parse_ints(text):
    \"\"\"Read `text` as a list of integers.\"\"\"
    parts = [part.strip() for part in text.split(",") if part.strip()]
    try:
        return [int(part) for part in parts]
    except ValueError as error:
        raise ValueError(f"{text!r} is not a list of integers") from error""",
    variant_three="""def parse_ints(text):
    \"\"\"Read `text` as a list of integers.\"\"\"
    if not text.strip():
        return []
    return [int(part) for part in text.split(",")]""",
    variant_four="""def parse_ints(text):
    \"\"\"Read `text` as a list of integers.\"\"\"
    values = []
    for part in text.split(","):
        stripped = part.strip()
        if not stripped.lstrip("+-").isdigit():
            raise ValueError(f"{text!r} is not a list of integers")
        values.append(int(stripped))
    return values""",
    visible_test=_test_module(
        "integer_list",
        "Published contract for integer lists.",
        """
def test_reads_three_numbers() -> None:
    assert parse_ints("1, 2, 3") == [1, 2, 3]


def test_reads_one_number() -> None:
    assert parse_ints("7") == [7]
""",
        imports="from integer_list import parse_ints\n",
    ),
    hidden_test=_test_module(
        "integer_list",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_three_numbers() -> None:
    assert parse_ints("1, 2, 3") == [1, 2, 3]


def test_an_empty_string_is_an_empty_list() -> None:
    assert parse_ints("") == []


def test_a_non_numeric_entry_names_the_whole_input() -> None:
    with pytest.raises(ValueError, match="1,x"):
        parse_ints("1,x")
""",
        imports="from integer_list import parse_ints\n",
    ),
)

_D37 = D2TaskSpec(
    template_id="d2_parsing.parse_coordinate",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-coordinate",
    module="coordinate_parsing",
    module_doc="Reading a two-dimensional coordinate.",
    issue=(
        "parse_coordinate() is documented to read '3,4'. Callers report a crash when the pair "
        "is written in parentheses, and errors that do not say what was actually passed in."
    ),
    expected=(
        "parse_coordinate(text) returns (x, y) as floats, tolerates surrounding parentheses, "
        "and raises a ValueError naming the whole input when there are not exactly two parts."
    ),
    baseline_reason="the brackets reach float() and the unpacking error names neither argument",
    edge_cases=(
        "parentheses are tolerated",
        "a three-component input names itself",
    ),
    baseline="""def parse_coordinate(text):
    \"\"\"Read `text` as a two-dimensional coordinate.\"\"\"
    x, y = text.split(",")
    return float(x), float(y)""",
    variant_one="""def parse_coordinate(text):
    \"\"\"Read `text` as a two-dimensional coordinate.\"\"\"
    cleaned = text.strip().lstrip("(").rstrip(")")
    parts = cleaned.split(",")
    if len(parts) != 2:
        raise ValueError(f"{text!r} is not a coordinate")
    return float(parts[0]), float(parts[1])""",
    variant_two="""def parse_coordinate(text):
    \"\"\"Read `text` as a two-dimensional coordinate.\"\"\"
    numbers = []
    for part in text.replace("(", "").replace(")", "").split(","):
        numbers.append(float(part))
    if len(numbers) != 2:
        raise ValueError(f"{text!r} is not a coordinate")
    return numbers[0], numbers[1]""",
    variant_three="""def parse_coordinate(text):
    \"\"\"Read `text` as a two-dimensional coordinate.\"\"\"
    cleaned = text.strip().lstrip("(").rstrip(")")
    x, y = cleaned.split(",")
    return float(x), float(y)""",
    variant_four="""def parse_coordinate(text):
    \"\"\"Read `text` as a two-dimensional coordinate.\"\"\"
    parts = text.split(",")
    if len(parts) != 2:
        raise ValueError(f"{text!r} is not a coordinate")
    return float(parts[0]), float(parts[1])""",
    visible_test=_test_module(
        "coordinate_parsing",
        "Published contract for coordinate parsing.",
        """
def test_reads_a_pair() -> None:
    assert parse_coordinate("3,4") == (3.0, 4.0)


def test_reads_a_negative_pair() -> None:
    assert parse_coordinate("-1,-2") == (-1.0, -2.0)
""",
        imports="from coordinate_parsing import parse_coordinate\n",
    ),
    hidden_test=_test_module(
        "coordinate_parsing",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_a_pair() -> None:
    assert parse_coordinate("3,4") == (3.0, 4.0)


def test_parentheses_are_tolerated() -> None:
    assert parse_coordinate("(3,4)") == (3.0, 4.0)


def test_a_three_component_input_names_itself() -> None:
    with pytest.raises(ValueError, match="1,2,3"):
        parse_coordinate("1,2,3")
""",
        imports="from coordinate_parsing import parse_coordinate\n",
    ),
)

_D38 = D2TaskSpec(
    template_id="d2_parsing.parse_percent",
    family=RealityTaskFamily.PARSING_VALIDATION,
    repository_group="d2-parsing-percent",
    module="percent_parsing",
    module_doc="Reading a percentage as a fraction.",
    issue=(
        "parse_percent() is documented to read '45%' as 0.45. Callers report the sign being "
        "mandatory, and figures above one hundred percent silently coming back as one."
    ),
    expected=(
        "parse_percent(text) returns the fraction, treats the percent sign as optional, and "
        "does not clamp a figure above one hundred percent."
    ),
    baseline_reason="the last character is always dropped and the result is capped at one",
    edge_cases=(
        "the percent sign is optional",
        "a value above one hundred is not clamped",
    ),
    baseline="""def parse_percent(text):
    \"\"\"Read `text` as a fraction of one.\"\"\"
    return min(float(text[:-1]) / 100, 1.0)""",
    variant_one="""def parse_percent(text):
    \"\"\"Read `text` as a fraction of one.\"\"\"
    cleaned = text.strip()
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    return float(cleaned) / 100""",
    variant_two="""def parse_percent(text):
    \"\"\"Read `text` as a fraction of one.\"\"\"
    from decimal import Decimal

    cleaned = text.strip().rstrip("%")
    return float(Decimal(cleaned) / Decimal(100))""",
    variant_three="""def parse_percent(text):
    \"\"\"Read `text` as a fraction of one.\"\"\"
    cleaned = text.strip()
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1]
    return min(float(cleaned) / 100, 1.0)""",
    variant_four="""def parse_percent(text):
    \"\"\"Read `text` as a fraction of one.\"\"\"
    return float(text[:-1]) / 100""",
    visible_test=_test_module(
        "percent_parsing",
        "Published contract for percentage parsing.",
        """
def test_reads_a_percentage() -> None:
    assert parse_percent("45%") == 0.45


def test_reads_a_whole_percentage() -> None:
    assert parse_percent("100%") == 1.0
""",
        imports="from percent_parsing import parse_percent\n",
    ),
    hidden_test=_test_module(
        "percent_parsing",
        "The part of the contract the published tests do not state.",
        """
def test_reads_a_percentage() -> None:
    assert parse_percent("45%") == 0.45


def test_the_percent_sign_is_optional() -> None:
    assert parse_percent("45") == 0.45


def test_a_value_above_one_hundred_is_not_clamped() -> None:
    assert parse_percent("150%") == 1.5
""",
        imports="from percent_parsing import parse_percent\n",
    ),
)

# ------------------------------------------------------------------- numeric logic, S21D2-022

_D39 = D2TaskSpec(
    template_id="d2_numeric.median",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-median",
    module="middle_value",
    module_doc="Reporting the middle of a set of values.",
    issue=(
        "median() is documented to report the middle value, averaging the middle two when "
        "there is an even number of them. Callers report the upper of the two coming back."
    ),
    expected=(
        "median(values) returns the middle value, averages the middle two when the count is "
        "even, and raises ValueError when there are no values."
    ),
    baseline_reason="the midpoint index is taken whatever the parity, and nothing checks for none",
    edge_cases=("an even count averages the middle two", "no values are refused"),
    baseline="""def median(values):
    \"\"\"Return the middle of `values`.\"\"\"
    ordered = sorted(values)
    return ordered[len(ordered) // 2]""",
    variant_one="""def median(values):
    \"\"\"Return the middle of `values`.\"\"\"
    ordered = sorted(values)
    if not ordered:
        raise ValueError("the median of no values is undefined")
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2""",
    variant_two="""def median(values):
    \"\"\"Return the middle of `values`.\"\"\"
    from statistics import StatisticsError
    from statistics import median as middle

    try:
        return middle(values)
    except StatisticsError as error:
        raise ValueError("the median of no values is undefined") from error""",
    variant_three="""def median(values):
    \"\"\"Return the middle of `values`.\"\"\"
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2""",
    variant_four="""def median(values):
    \"\"\"Return the middle of `values`.\"\"\"
    ordered = sorted(values)
    if not ordered:
        raise ValueError("the median of no values is undefined")
    return ordered[len(ordered) // 2]""",
    visible_test=_test_module(
        "middle_value",
        "Published contract for the median.",
        """
def test_finds_the_middle_of_three() -> None:
    assert median([3, 1, 2]) == 2


def test_finds_the_middle_of_five() -> None:
    assert median([5, 1, 4, 2, 3]) == 3
""",
        imports="from middle_value import median\n",
    ),
    hidden_test=_test_module(
        "middle_value",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_finds_the_middle_of_three() -> None:
    assert median([3, 1, 2]) == 2


def test_an_even_count_averages_the_middle_two() -> None:
    assert median([1, 2, 3, 4]) == 2.5


def test_no_values_are_refused() -> None:
    with pytest.raises(ValueError):
        median([])
""",
        imports="from middle_value import median\n",
    ),
)

_D40 = D2TaskSpec(
    template_id="d2_numeric.round_half_up",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-rounding",
    module="rounding",
    module_doc="Rounding for figures that are reported to people.",
    issue=(
        "round_half_up() is documented to round a half away from zero, which is what a reader "
        "expects. Callers report halves going to the even neighbour instead."
    ),
    expected=(
        "round_half_up(value, digits) rounds a half away from zero rather than to even, and "
        "raises ValueError when the digit count is negative."
    ),
    baseline_reason="the built-in rounds halves to even and happily accepts negative digits",
    edge_cases=("a half rounds away from zero", "a negative digit count is refused"),
    baseline="""def round_half_up(value, digits):
    \"\"\"Round `value` to `digits` places, halves away from zero.\"\"\"
    return round(value, digits)""",
    variant_one="""def round_half_up(value, digits):
    \"\"\"Round `value` to `digits` places, halves away from zero.\"\"\"
    from decimal import ROUND_HALF_UP, Decimal

    if digits < 0:
        raise ValueError("the number of digits must not be negative")
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))""",
    variant_two="""def round_half_up(value, digits):
    \"\"\"Round `value` to `digits` places, halves away from zero.\"\"\"
    from math import copysign, floor

    if digits < 0:
        raise ValueError("the number of digits must not be negative")
    scale = 10**digits
    shifted = abs(value) * scale
    return copysign(floor(shifted + 0.5) / scale, value)""",
    variant_three="""def round_half_up(value, digits):
    \"\"\"Round `value` to `digits` places, halves away from zero.\"\"\"
    from decimal import ROUND_HALF_UP, Decimal

    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))""",
    variant_four="""def round_half_up(value, digits):
    \"\"\"Round `value` to `digits` places, halves away from zero.\"\"\"
    if digits < 0:
        raise ValueError("the number of digits must not be negative")
    return round(value, digits)""",
    visible_test=_test_module(
        "rounding",
        "Published contract for reporting rounding.",
        """
def test_rounds_down_below_a_half() -> None:
    assert round_half_up(1.24, 1) == 1.2


def test_rounds_up_above_a_half() -> None:
    assert round_half_up(1.26, 1) == 1.3
""",
        imports="from rounding import round_half_up\n",
    ),
    hidden_test=_test_module(
        "rounding",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_rounds_down_below_a_half() -> None:
    assert round_half_up(1.24, 1) == 1.2


def test_a_half_rounds_away_from_zero() -> None:
    assert round_half_up(2.5, 0) == 3.0


def test_a_negative_digit_count_is_refused() -> None:
    with pytest.raises(ValueError):
        round_half_up(1234.0, -1)
""",
        imports="from rounding import round_half_up\n",
    ),
)

_D41 = D2TaskSpec(
    template_id="d2_numeric.weighted_mean",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-weighted-mean",
    module="weighted_average",
    module_doc="Averaging values that carry weights.",
    issue=(
        "weighted_mean() is documented to need one weight per value. Callers report a short "
        "weight list quietly dropping values, and a crash when the weights cancel out."
    ),
    expected=(
        "weighted_mean(values, weights) raises ValueError when the two lists differ in length "
        "and when the weights sum to zero, and otherwise returns the weighted mean."
    ),
    baseline_reason="zip stops at the shorter list and the divisor is never checked",
    edge_cases=(
        "mismatched lengths are refused",
        "weights summing to zero are refused",
    ),
    baseline="""def weighted_mean(values, weights):
    \"\"\"Return the mean of `values` weighted by `weights`.\"\"\"
    total = sum(value * weight for value, weight in zip(values, weights))
    return total / sum(weights)""",
    variant_one="""def weighted_mean(values, weights):
    \"\"\"Return the mean of `values` weighted by `weights`.\"\"\"
    if len(values) != len(weights):
        raise ValueError("there must be one weight per value")
    divisor = sum(weights)
    if divisor == 0:
        raise ValueError("the weights must not sum to zero")
    return sum(value * weight for value, weight in zip(values, weights)) / divisor""",
    variant_two="""def weighted_mean(values, weights):
    \"\"\"Return the mean of `values` weighted by `weights`.\"\"\"
    paired = list(zip(values, weights, strict=True))
    divisor = 0
    total = 0
    for value, weight in paired:
        total += value * weight
        divisor += weight
    if not divisor:
        raise ValueError("the weights must not sum to zero")
    return total / divisor""",
    variant_three="""def weighted_mean(values, weights):
    \"\"\"Return the mean of `values` weighted by `weights`.\"\"\"
    if len(values) != len(weights):
        raise ValueError("there must be one weight per value")
    total = sum(value * weight for value, weight in zip(values, weights))
    return total / sum(weights)""",
    variant_four="""def weighted_mean(values, weights):
    \"\"\"Return the mean of `values` weighted by `weights`.\"\"\"
    divisor = sum(weights)
    if divisor == 0:
        raise ValueError("the weights must not sum to zero")
    return sum(value * weight for value, weight in zip(values, weights)) / divisor""",
    visible_test=_test_module(
        "weighted_average",
        "Published contract for weighted means.",
        """
def test_weights_evenly() -> None:
    assert weighted_mean([1, 2, 3], [1, 1, 1]) == 2


def test_weights_the_first_value_heavily() -> None:
    assert weighted_mean([10, 0], [3, 1]) == 7.5
""",
        imports="from weighted_average import weighted_mean\n",
    ),
    hidden_test=_test_module(
        "weighted_average",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_weights_evenly() -> None:
    assert weighted_mean([1, 2, 3], [1, 1, 1]) == 2


def test_mismatched_lengths_are_refused() -> None:
    with pytest.raises(ValueError):
        weighted_mean([1, 2, 3], [1, 1])


def test_weights_summing_to_zero_are_refused() -> None:
    with pytest.raises(ValueError):
        weighted_mean([1, 2], [1, -1])
""",
        imports="from weighted_average import weighted_mean\n",
    ),
)

_D42 = D2TaskSpec(
    template_id="d2_numeric.percent_change",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-change",
    module="change_ratio",
    module_doc="Reporting the change between two figures.",
    issue=(
        "percent_change() is documented to report the change from one figure to another. "
        "Callers report drops being shown as rises, and a crash when the old figure is zero."
    ),
    expected=(
        "percent_change(old, new) returns the signed percentage change, so a decrease is "
        "negative, and raises ValueError when the old figure is zero."
    ),
    baseline_reason="the magnitude is taken before the sign survives, and zero is never checked",
    edge_cases=("a decrease is negative", "a change from zero is refused"),
    baseline="""def percent_change(old, new):
    \"\"\"Return the percentage change from `old` to `new`.\"\"\"
    return abs(new - old) / old * 100""",
    variant_one="""def percent_change(old, new):
    \"\"\"Return the percentage change from `old` to `new`.\"\"\"
    if old == 0:
        raise ValueError("a change from zero has no percentage")
    return (new - old) / old * 100""",
    variant_two="""def percent_change(old, new):
    \"\"\"Return the percentage change from `old` to `new`.\"\"\"
    try:
        ratio = (new - old) / old
    except ZeroDivisionError as error:
        raise ValueError("a change from zero has no percentage") from error
    return ratio * 100""",
    variant_three="""def percent_change(old, new):
    \"\"\"Return the percentage change from `old` to `new`.\"\"\"
    if old == 0:
        raise ValueError("a change from zero has no percentage")
    return abs(new - old) / old * 100""",
    variant_four="""def percent_change(old, new):
    \"\"\"Return the percentage change from `old` to `new`.\"\"\"
    return (new - old) / old * 100""",
    visible_test=_test_module(
        "change_ratio",
        "Published contract for change reporting.",
        """
def test_reports_an_increase() -> None:
    assert percent_change(200, 250) == 25.0


def test_reports_no_change_as_zero() -> None:
    assert percent_change(50, 50) == 0.0
""",
        imports="from change_ratio import percent_change\n",
    ),
    hidden_test=_test_module(
        "change_ratio",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reports_an_increase() -> None:
    assert percent_change(200, 250) == 25.0


def test_a_decrease_is_negative() -> None:
    assert percent_change(200, 150) == -25.0


def test_a_change_from_zero_is_refused() -> None:
    with pytest.raises(ValueError):
        percent_change(0, 10)
""",
        imports="from change_ratio import percent_change\n",
    ),
)

_D43 = D2TaskSpec(
    template_id="d2_numeric.digit_root",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-digit-root",
    module="digit_summing",
    module_doc="Reducing a number to its digital root.",
    issue=(
        "digit_root() is documented to sum the digits repeatedly until one digit is left. "
        "Callers report two-digit answers coming back, and a crash on negative numbers."
    ),
    expected=(
        "digit_root(number) reduces to a single digit, repeating the sum as often as needed, "
        "and uses the magnitude of a negative number."
    ),
    baseline_reason="the digits are summed once and the minus sign is fed to int()",
    edge_cases=(
        "a negative number uses its magnitude",
        "a multi-digit sum is reduced again",
    ),
    baseline="""def digit_root(number):
    \"\"\"Return the digital root of `number`.\"\"\"
    return sum(int(character) for character in str(number))""",
    variant_one="""def digit_root(number):
    \"\"\"Return the digital root of `number`.\"\"\"
    remaining = abs(number)
    while remaining > 9:
        remaining = sum(int(character) for character in str(remaining))
    return remaining""",
    variant_two="""def digit_root(number):
    \"\"\"Return the digital root of `number`.\"\"\"
    magnitude = abs(number)
    if magnitude == 0:
        return 0
    return 1 + (magnitude - 1) % 9""",
    variant_three="""def digit_root(number):
    \"\"\"Return the digital root of `number`.\"\"\"
    return sum(int(character) for character in str(abs(number)))""",
    variant_four="""def digit_root(number):
    \"\"\"Return the digital root of `number`.\"\"\"
    remaining = number
    while remaining > 9:
        remaining = sum(int(character) for character in str(remaining))
    return remaining""",
    visible_test=_test_module(
        "digit_summing",
        "Published contract for digital roots.",
        """
def test_sums_the_digits() -> None:
    assert digit_root(12) == 3


def test_a_single_digit_is_itself() -> None:
    assert digit_root(7) == 7
""",
        imports="from digit_summing import digit_root\n",
    ),
    hidden_test=_test_module(
        "digit_summing",
        "The part of the contract the published tests do not state.",
        """
def test_sums_the_digits() -> None:
    assert digit_root(12) == 3


def test_a_negative_number_uses_its_magnitude() -> None:
    assert digit_root(-12) == 3


def test_a_multi_digit_sum_is_reduced_again() -> None:
    assert digit_root(99) == 9
""",
        imports="from digit_summing import digit_root\n",
    ),
)

_D44 = D2TaskSpec(
    template_id="d2_numeric.moving_average",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-moving-average",
    module="sliding_mean",
    module_doc="Averaging a series over a sliding window.",
    issue=(
        "moving_average() is documented to emit one average per full window. Callers report "
        "extra entries at the end computed over fewer values, and a crash on a zero window."
    ),
    expected=(
        "moving_average(values, window) emits one average per full window and none for a "
        "partial one, and raises ValueError when the window is not positive."
    ),
    baseline_reason="the loop runs once per value, so the last few windows run off the end",
    edge_cases=("a partial window is not emitted", "a non-positive window is refused"),
    baseline="""def moving_average(values, window):
    \"\"\"Return the average of each full `window` of `values`.\"\"\"
    return [sum(values[index : index + window]) / window for index in range(len(values))]""",
    variant_one="""def moving_average(values, window):
    \"\"\"Return the average of each full `window` of `values`.\"\"\"
    if window <= 0:
        raise ValueError("the window must be positive")
    return [
        sum(values[index : index + window]) / window
        for index in range(len(values) - window + 1)
    ]""",
    variant_two="""def moving_average(values, window):
    \"\"\"Return the average of each full `window` of `values`.\"\"\"
    from collections import deque

    if window <= 0:
        raise ValueError("the window must be positive")
    recent = deque(maxlen=window)
    averages = []
    for value in values:
        recent.append(value)
        if len(recent) == window:
            averages.append(sum(recent) / window)
    return averages""",
    variant_three="""def moving_average(values, window):
    \"\"\"Return the average of each full `window` of `values`.\"\"\"
    averages = []
    for index in range(len(values) - window + 1):
        averages.append(sum(values[index : index + window]) / window)
    return averages""",
    variant_four="""def moving_average(values, window):
    \"\"\"Return the average of each full `window` of `values`.\"\"\"
    if window <= 0:
        raise ValueError("the window must be positive")
    return [sum(values[index : index + window]) / window for index in range(len(values))]""",
    visible_test=_test_module(
        "sliding_mean",
        "Published contract for sliding averages.",
        """
def test_averages_pairs() -> None:
    assert moving_average([1, 2, 3], 2)[:2] == [1.5, 2.5]


def test_a_window_of_one_returns_the_values() -> None:
    assert moving_average([1, 2], 1) == [1.0, 2.0]
""",
        imports="from sliding_mean import moving_average\n",
    ),
    hidden_test=_test_module(
        "sliding_mean",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_averages_pairs() -> None:
    assert moving_average([1, 2, 3], 2) == [1.5, 2.5]


def test_a_partial_window_is_not_emitted() -> None:
    assert len(moving_average([1, 2, 3, 4], 3)) == 2


def test_a_non_positive_window_is_refused() -> None:
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)
""",
        imports="from sliding_mean import moving_average\n",
    ),
)

_D45 = D2TaskSpec(
    template_id="d2_numeric.nearest_multiple",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-snap",
    module="multiple_snapping",
    module_doc="Snapping a figure to the nearest multiple.",
    issue=(
        "nearest_multiple() is documented to snap upward when a figure sits exactly between "
        "two multiples. Callers report it snapping down, and a crash on a base of zero."
    ),
    expected=(
        "nearest_multiple(value, base) returns the nearest multiple of `base`, snaps upward on "
        "an exact tie, and raises ValueError when the base is zero."
    ),
    baseline_reason="the built-in round sends a tie to the even neighbour and zero divides",
    edge_cases=("a tie snaps upward", "a zero base is refused"),
    baseline="""def nearest_multiple(value, base):
    \"\"\"Snap `value` to the nearest multiple of `base`.\"\"\"
    return round(value / base) * base""",
    variant_one="""def nearest_multiple(value, base):
    \"\"\"Snap `value` to the nearest multiple of `base`.\"\"\"
    from math import floor

    if base == 0:
        raise ValueError("the base must not be zero")
    return floor(value / base + 0.5) * base""",
    variant_two="""def nearest_multiple(value, base):
    \"\"\"Snap `value` to the nearest multiple of `base`.\"\"\"
    if not base:
        raise ValueError("the base must not be zero")
    lower = (value // base) * base
    upper = lower + base
    return upper if value - lower >= upper - value else lower""",
    variant_three="""def nearest_multiple(value, base):
    \"\"\"Snap `value` to the nearest multiple of `base`.\"\"\"
    if base == 0:
        raise ValueError("the base must not be zero")
    return round(value / base) * base""",
    variant_four="""def nearest_multiple(value, base):
    \"\"\"Snap `value` to the nearest multiple of `base`.\"\"\"
    from math import floor

    return floor(value / base + 0.5) * base""",
    visible_test=_test_module(
        "multiple_snapping",
        "Published contract for snapping.",
        """
def test_snaps_down() -> None:
    assert nearest_multiple(12, 5) == 10


def test_snaps_up() -> None:
    assert nearest_multiple(13, 5) == 15
""",
        imports="from multiple_snapping import nearest_multiple\n",
    ),
    hidden_test=_test_module(
        "multiple_snapping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_snaps_down() -> None:
    assert nearest_multiple(12, 5) == 10


def test_a_tie_snaps_upward() -> None:
    assert nearest_multiple(5, 10) == 10


def test_a_zero_base_is_refused() -> None:
    with pytest.raises(ValueError):
        nearest_multiple(7, 0)
""",
        imports="from multiple_snapping import nearest_multiple\n",
    ),
)

_D46 = D2TaskSpec(
    template_id="d2_numeric.scale_to_unit",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-unit-scale",
    module="unit_scaling",
    module_doc="Scaling a series into the unit interval.",
    issue=(
        "scale_to_unit() is documented to scale a series into the range zero to one. Callers "
        "report a crash when every value is the same, and another when there are no values."
    ),
    expected=(
        "scale_to_unit(values) scales into the unit interval, maps a series of equal values to "
        "zero rather than dividing by a zero span, and returns nothing for no values."
    ),
    baseline_reason="the span is used as a divisor without ever being checked for zero",
    edge_cases=("equal values map to zero", "no values scale to nothing"),
    baseline="""def scale_to_unit(values):
    \"\"\"Scale `values` into the interval from zero to one.\"\"\"
    low = min(values)
    high = max(values)
    return [(value - low) / (high - low) for value in values]""",
    variant_one="""def scale_to_unit(values):
    \"\"\"Scale `values` into the interval from zero to one.\"\"\"
    ordered = list(values)
    if not ordered:
        return []
    low = min(ordered)
    high = max(ordered)
    if high == low:
        return [0.0 for _ in ordered]
    return [(value - low) / (high - low) for value in ordered]""",
    variant_two="""def scale_to_unit(values):
    \"\"\"Scale `values` into the interval from zero to one.\"\"\"
    ordered = list(values)
    scaled = []
    for value in ordered:
        span = max(ordered) - min(ordered)
        scaled.append((value - min(ordered)) / span if span else 0.0)
    return scaled""",
    variant_three="""def scale_to_unit(values):
    \"\"\"Scale `values` into the interval from zero to one.\"\"\"
    ordered = list(values)
    if not ordered:
        return []
    low = min(ordered)
    high = max(ordered)
    return [(value - low) / (high - low) for value in ordered]""",
    variant_four="""def scale_to_unit(values):
    \"\"\"Scale `values` into the interval from zero to one.\"\"\"
    low = min(values)
    high = max(values)
    if high == low:
        return [0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]""",
    visible_test=_test_module(
        "unit_scaling",
        "Published contract for unit scaling.",
        """
def test_scales_to_the_unit_interval() -> None:
    assert scale_to_unit([0, 5, 10]) == [0.0, 0.5, 1.0]


def test_scales_a_negative_range() -> None:
    assert scale_to_unit([-2, 0, 2]) == [0.0, 0.5, 1.0]
""",
        imports="from unit_scaling import scale_to_unit\n",
    ),
    hidden_test=_test_module(
        "unit_scaling",
        "The part of the contract the published tests do not state.",
        """
def test_scales_to_the_unit_interval() -> None:
    assert scale_to_unit([0, 5, 10]) == [0.0, 0.5, 1.0]


def test_equal_values_map_to_zero() -> None:
    assert scale_to_unit([3, 3]) == [0.0, 0.0]


def test_no_values_scale_to_nothing() -> None:
    assert scale_to_unit([]) == []
""",
        imports="from unit_scaling import scale_to_unit\n",
    ),
)

_D47 = D2TaskSpec(
    template_id="d2_numeric.factorial",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-factorial",
    module="factorial_maths",
    module_doc="Computing factorials for a combinatorics helper.",
    issue=(
        "factorial() is documented to return one for zero and to refuse negative arguments. "
        "Callers report zero coming back for zero and negative arguments being echoed."
    ),
    expected=(
        "factorial(n) returns the product of one through n, returns one for zero, and raises "
        "ValueError for a negative argument."
    ),
    baseline_reason="the accumulator is seeded with n itself, so zero and negatives fall through",
    edge_cases=("zero factorial is one", "a negative argument is refused"),
    baseline="""def factorial(n):
    \"\"\"Return the factorial of `n`.\"\"\"
    result = n
    for value in range(1, n):
        result *= value
    return result""",
    variant_one="""def factorial(n):
    \"\"\"Return the factorial of `n`.\"\"\"
    if n < 0:
        raise ValueError("the factorial of a negative number is undefined")
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result""",
    variant_two="""def factorial(n):
    \"\"\"Return the factorial of `n`.\"\"\"
    if n < 0:
        raise ValueError("the factorial of a negative number is undefined")
    if n < 2:
        return 1
    return n * factorial(n - 1)""",
    variant_three="""def factorial(n):
    \"\"\"Return the factorial of `n`.\"\"\"
    result = 1
    for value in range(2, n + 1):
        result *= value
    return result""",
    variant_four="""def factorial(n):
    \"\"\"Return the factorial of `n`.\"\"\"
    if n < 0:
        raise ValueError("the factorial of a negative number is undefined")
    result = n
    for value in range(1, n):
        result *= value
    return result""",
    visible_test=_test_module(
        "factorial_maths",
        "Published contract for factorials.",
        """
def test_computes_a_small_factorial() -> None:
    assert factorial(5) == 120


def test_one_factorial_is_one() -> None:
    assert factorial(1) == 1
""",
        imports="from factorial_maths import factorial\n",
    ),
    hidden_test=_test_module(
        "factorial_maths",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_computes_a_small_factorial() -> None:
    assert factorial(5) == 120


def test_zero_factorial_is_one() -> None:
    assert factorial(0) == 1


def test_a_negative_argument_is_refused() -> None:
    with pytest.raises(ValueError):
        factorial(-3)
""",
        imports="from factorial_maths import factorial\n",
    ),
)

_D48 = D2TaskSpec(
    template_id="d2_numeric.average_present",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-present-average",
    module="present_average",
    module_doc="Averaging a series that has gaps in it.",
    issue=(
        "average_present() is documented to average the readings that are present and to fall "
        "back to a default when none are. Callers report zero readings being treated as gaps."
    ),
    expected=(
        "average_present(values, default) averages every value that is not None, counts a "
        "reading of zero as present, and returns the default when nothing is present."
    ),
    baseline_reason="a truthiness test drops zero readings and leaves an empty divisor",
    edge_cases=("all missing values give the default", "a zero is counted"),
    baseline="""def average_present(values, default):
    \"\"\"Average the readings in `values` that are present.\"\"\"
    present = [value for value in values if value]
    return sum(present) / len(present)""",
    variant_one="""def average_present(values, default):
    \"\"\"Average the readings in `values` that are present.\"\"\"
    present = [value for value in values if value is not None]
    if not present:
        return default
    return sum(present) / len(present)""",
    variant_two="""def average_present(values, default):
    \"\"\"Average the readings in `values` that are present.\"\"\"
    total = 0
    count = 0
    for value in values:
        if value is None:
            continue
        total += value
        count += 1
    return total / count if count else default""",
    variant_three="""def average_present(values, default):
    \"\"\"Average the readings in `values` that are present.\"\"\"
    present = [value for value in values if value]
    if not present:
        return default
    return sum(present) / len(present)""",
    variant_four="""def average_present(values, default):
    \"\"\"Average the readings in `values` that are present.\"\"\"
    present = [value for value in values if value is not None]
    return sum(present) / len(present)""",
    visible_test=_test_module(
        "present_average",
        "Published contract for averaging with gaps.",
        """
def test_averages_the_present_values() -> None:
    assert average_present([1, None, 3], 0) == 2.0


def test_averages_a_single_value() -> None:
    assert average_present([4], 0) == 4.0
""",
        imports="from present_average import average_present\n",
    ),
    hidden_test=_test_module(
        "present_average",
        "The part of the contract the published tests do not state.",
        """
def test_averages_the_present_values() -> None:
    assert average_present([1, None, 3], 0) == 2.0


def test_all_missing_values_give_the_default() -> None:
    assert average_present([None, None], -1) == -1


def test_a_zero_is_counted() -> None:
    assert average_present([0, 4], 0) == 2.0
""",
        imports="from present_average import average_present\n",
    ),
)

_D49 = D2TaskSpec(
    template_id="d2_numeric.gcd_all",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-gcd",
    module="common_divisor",
    module_doc="Finding the common divisor of a set of figures.",
    issue=(
        "gcd_all() is documented to return a positive divisor. Callers report negative answers "
        "when one of the figures is negative, and a crash when the list is empty."
    ),
    expected=(
        "gcd_all(values) returns the greatest common divisor as a positive number whatever the "
        "signs of the inputs, and raises ValueError when there are no values."
    ),
    baseline_reason="Euclid's algorithm keeps the sign of its operands and the list is not checked",
    edge_cases=("the result is positive whatever the signs", "no values are refused"),
    baseline="""def gcd_all(values):
    \"\"\"Return the greatest common divisor of `values`.\"\"\"
    result = values[0]
    for value in values[1:]:
        left, right = result, value
        while right:
            left, right = right, left % right
        result = left
    return result""",
    variant_one="""def gcd_all(values):
    \"\"\"Return the greatest common divisor of `values`.\"\"\"
    ordered = list(values)
    if not ordered:
        raise ValueError("the divisor of no values is undefined")
    result = abs(ordered[0])
    for value in ordered[1:]:
        left, right = result, abs(value)
        while right:
            left, right = right, left % right
        result = left
    return result""",
    variant_two="""def gcd_all(values):
    \"\"\"Return the greatest common divisor of `values`.\"\"\"
    from functools import reduce
    from math import gcd

    ordered = list(values)
    if not ordered:
        raise ValueError("the divisor of no values is undefined")
    return reduce(gcd, (abs(value) for value in ordered))""",
    variant_three="""def gcd_all(values):
    \"\"\"Return the greatest common divisor of `values`.\"\"\"
    result = abs(values[0])
    for value in values[1:]:
        left, right = result, abs(value)
        while right:
            left, right = right, left % right
        result = left
    return result""",
    variant_four="""def gcd_all(values):
    \"\"\"Return the greatest common divisor of `values`.\"\"\"
    ordered = list(values)
    if not ordered:
        raise ValueError("the divisor of no values is undefined")
    result = ordered[0]
    for value in ordered[1:]:
        left, right = result, value
        while right:
            left, right = right, left % right
        result = left
    return result""",
    visible_test=_test_module(
        "common_divisor",
        "Published contract for common divisors.",
        """
def test_finds_a_common_divisor() -> None:
    assert gcd_all([12, 18]) == 6


def test_finds_the_divisor_of_three_values() -> None:
    assert gcd_all([12, 18, 24]) == 6
""",
        imports="from common_divisor import gcd_all\n",
    ),
    hidden_test=_test_module(
        "common_divisor",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_finds_a_common_divisor() -> None:
    assert gcd_all([12, 18]) == 6


def test_the_result_is_positive_whatever_the_signs() -> None:
    assert gcd_all([4, -6]) == 2


def test_no_values_are_refused() -> None:
    with pytest.raises(ValueError):
        gcd_all([])
""",
        imports="from common_divisor import gcd_all\n",
    ),
)

_D50 = D2TaskSpec(
    template_id="d2_numeric.human_size",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-human-size",
    module="human_sizes",
    module_doc="Rendering a byte count for a person to read.",
    issue=(
        "human_size() is documented to render whole bytes without a decimal place. Callers "
        "report '512.0 B' in their reports, and negative counts being rendered rather than "
        "refused."
    ),
    expected=(
        "human_size(count) renders a count below a kilobyte as whole bytes with no decimal "
        "place, and raises ValueError for a negative count."
    ),
    baseline_reason="one format string is used for every unit and the sign is never checked",
    edge_cases=(
        "a small count stays in whole bytes",
        "a negative count is refused",
    ),
    baseline="""def human_size(count):
    \"\"\"Render `count` bytes for a person to read.\"\"\"
    units = ["B", "KB", "MB"]
    index = 0
    size = float(count)
    while size >= 1024:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}\"""",
    variant_one="""def human_size(count):
    \"\"\"Render `count` bytes for a person to read.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    units = ["B", "KB", "MB"]
    index = 0
    size = float(count)
    while size >= 1024:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[index]}\"""",
    variant_two="""def human_size(count):
    \"\"\"Render `count` bytes for a person to read.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    if count < 1024:
        return f"{count} B"
    scaled = count / 1024
    for unit in ("KB", "MB"):
        if scaled < 1024:
            return f"{scaled:.1f} {unit}"
        scaled /= 1024
    return f"{scaled:.1f} GB\"""",
    variant_three="""def human_size(count):
    \"\"\"Render `count` bytes for a person to read.\"\"\"
    units = ["B", "KB", "MB"]
    index = 0
    size = float(count)
    while size >= 1024:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} B"
    return f"{size:.1f} {units[index]}\"""",
    variant_four="""def human_size(count):
    \"\"\"Render `count` bytes for a person to read.\"\"\"
    if count < 0:
        raise ValueError("the count must not be negative")
    units = ["B", "KB", "MB"]
    index = 0
    size = float(count)
    while size >= 1024:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}\"""",
    visible_test=_test_module(
        "human_sizes",
        "Published contract for human-readable sizes.",
        """
def test_reports_kilobytes() -> None:
    assert human_size(1536) == "1.5 KB"


def test_reports_megabytes() -> None:
    assert human_size(2 * 1024 * 1024) == "2.0 MB"
""",
        imports="from human_sizes import human_size\n",
    ),
    hidden_test=_test_module(
        "human_sizes",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reports_kilobytes() -> None:
    assert human_size(1536) == "1.5 KB"


def test_a_small_count_stays_in_whole_bytes() -> None:
    assert human_size(512) == "512 B"


def test_a_negative_count_is_refused() -> None:
    with pytest.raises(ValueError):
        human_size(-1)
""",
        imports="from human_sizes import human_size\n",
    ),
)

_D51 = D2TaskSpec(
    template_id="d2_numeric.interpolate",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-interpolation",
    module="interpolation",
    module_doc="Interpolating between two bounds.",
    issue=(
        "interpolate() is documented to work within the unit interval and to land exactly on "
        "the high bound at one. Callers report a fraction of two extrapolating instead of "
        "being refused, and a value just past the bound at one."
    ),
    expected=(
        "interpolate(low, high, fraction) raises ValueError for a fraction outside zero to "
        "one, and returns exactly the high bound at a fraction of one."
    ),
    baseline_reason=(
        "adding a scaled difference to the low bound reintroduces the rounding it just lost"
    ),
    edge_cases=(
        "the end is exactly the high bound",
        "a fraction outside the unit interval is refused",
    ),
    baseline="""def interpolate(low, high, fraction):
    \"\"\"Interpolate between `low` and `high` at `fraction`.\"\"\"
    return low + (high - low) * fraction""",
    variant_one="""def interpolate(low, high, fraction):
    \"\"\"Interpolate between `low` and `high` at `fraction`.\"\"\"
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("the fraction must lie between zero and one")
    if fraction == 1.0:
        return high
    return low + (high - low) * fraction""",
    variant_two="""def interpolate(low, high, fraction):
    \"\"\"Interpolate between `low` and `high` at `fraction`.\"\"\"
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError("the fraction must lie between zero and one")
    return low * (1.0 - fraction) + high * fraction""",
    variant_three="""def interpolate(low, high, fraction):
    \"\"\"Interpolate between `low` and `high` at `fraction`.\"\"\"
    if fraction == 1.0:
        return high
    return low + (high - low) * fraction""",
    variant_four="""def interpolate(low, high, fraction):
    \"\"\"Interpolate between `low` and `high` at `fraction`.\"\"\"
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("the fraction must lie between zero and one")
    return low + (high - low) * fraction""",
    visible_test=_test_module(
        "interpolation",
        "Published contract for interpolation.",
        """
def test_interpolates_the_midpoint() -> None:
    assert interpolate(0.0, 10.0, 0.5) == 5.0


def test_the_start_is_the_low_bound() -> None:
    assert interpolate(2.0, 6.0, 0.0) == 2.0
""",
        imports="from interpolation import interpolate\n",
    ),
    hidden_test=_test_module(
        "interpolation",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_interpolates_the_midpoint() -> None:
    assert interpolate(0.0, 10.0, 0.5) == 5.0


def test_the_end_is_exactly_the_high_bound() -> None:
    assert interpolate(0.2, 0.9, 1.0) == 0.9


def test_a_fraction_outside_the_unit_interval_is_refused() -> None:
    with pytest.raises(ValueError):
        interpolate(0.0, 1.0, 2.0)
""",
        imports="from interpolation import interpolate\n",
    ),
)

_D52 = D2TaskSpec(
    template_id="d2_numeric.progress_bar",
    family=RealityTaskFamily.NUMERIC_LOGIC,
    repository_group="d2-numeric-progress",
    module="progress_bar",
    module_doc="Drawing a fixed-width progress bar.",
    issue=(
        "progress_bar() is documented to draw a bar of exactly the requested width. Callers "
        "report a crash before any work is known, and bars wider than they asked for."
    ),
    expected=(
        "progress_bar(done, total, width) returns a bar of exactly `width` characters, draws "
        "an empty bar when the total is zero, and does not widen when `done` exceeds `total`."
    ),
    baseline_reason="the fraction is neither guarded against a zero total nor capped at one",
    edge_cases=(
        "a zero total draws an empty bar",
        "overshooting does not widen the bar",
    ),
    baseline="""def progress_bar(done, total, width):
    \"\"\"Draw a bar of `width` characters showing `done` of `total`.\"\"\"
    filled = round(width * done / total)
    return "#" * filled + "-" * (width - filled)""",
    variant_one="""def progress_bar(done, total, width):
    \"\"\"Draw a bar of `width` characters showing `done` of `total`.\"\"\"
    if total <= 0:
        return "-" * width
    filled = min(round(width * done / total), width)
    return "#" * filled + "-" * (width - filled)""",
    variant_two="""def progress_bar(done, total, width):
    \"\"\"Draw a bar of `width` characters showing `done` of `total`.\"\"\"
    fraction = 0.0 if total <= 0 else done / total
    fraction = max(0.0, min(fraction, 1.0))
    filled = round(width * fraction)
    return "#" * filled + "-" * (width - filled)""",
    variant_three="""def progress_bar(done, total, width):
    \"\"\"Draw a bar of `width` characters showing `done` of `total`.\"\"\"
    if total <= 0:
        return "-" * width
    filled = round(width * done / total)
    return "#" * filled + "-" * (width - filled)""",
    variant_four="""def progress_bar(done, total, width):
    \"\"\"Draw a bar of `width` characters showing `done` of `total`.\"\"\"
    filled = min(round(width * done / total), width)
    return "#" * filled + "-" * (width - filled)""",
    visible_test=_test_module(
        "progress_bar",
        "Published contract for progress bars.",
        """
def test_draws_a_half_bar() -> None:
    assert progress_bar(5, 10, 10) == "#####-----"


def test_draws_a_full_bar() -> None:
    assert progress_bar(10, 10, 10) == "##########"
""",
        imports="from progress_bar import progress_bar\n",
    ),
    hidden_test=_test_module(
        "progress_bar",
        "The part of the contract the published tests do not state.",
        """
def test_draws_a_half_bar() -> None:
    assert progress_bar(5, 10, 10) == "#####-----"


def test_a_zero_total_draws_an_empty_bar() -> None:
    assert progress_bar(0, 0, 10) == "----------"


def test_overshooting_does_not_widen_the_bar() -> None:
    assert len(progress_bar(15, 10, 10)) == 10
""",
        imports="from progress_bar import progress_bar\n",
    ),
)

# -------------------------------------------------------------- state and idempotency, S21D2-022

_D53 = D2TaskSpec(
    template_id="d2_state.toggle_flag",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-toggle",
    module="flag_state",
    module_doc="Flipping a feature flag.",
    issue=(
        "toggle_flag() is documented to return a new settings mapping. Callers report their "
        "own mapping changing underneath them and a crash on a flag nobody has set yet."
    ),
    expected=(
        "toggle_flag(state, name) returns a new mapping with the flag flipped, leaves the "
        "caller's mapping untouched, and treats a flag that is not set as off."
    ),
    baseline_reason="the assignment lands in the caller's mapping and the lookup has no default",
    edge_cases=("the input is not mutated", "an unknown flag turns on"),
    baseline="""def toggle_flag(state, name):
    \"\"\"Return the settings with the flag `name` flipped.\"\"\"
    state[name] = not state[name]
    return state""",
    variant_one="""def toggle_flag(state, name):
    \"\"\"Return the settings with the flag `name` flipped.\"\"\"
    updated = dict(state)
    updated[name] = not updated.get(name, False)
    return updated""",
    variant_two="""def toggle_flag(state, name):
    \"\"\"Return the settings with the flag `name` flipped.\"\"\"
    return {**state, name: not state.get(name, False)}""",
    variant_three="""def toggle_flag(state, name):
    \"\"\"Return the settings with the flag `name` flipped.\"\"\"
    updated = dict(state)
    updated[name] = not updated[name]
    return updated""",
    variant_four="""def toggle_flag(state, name):
    \"\"\"Return the settings with the flag `name` flipped.\"\"\"
    state[name] = not state.get(name, False)
    return state""",
    visible_test=_test_module(
        "flag_state",
        "Published contract for flag toggling.",
        """
def test_turns_a_flag_off() -> None:
    assert toggle_flag({"debug": True}, "debug") == {"debug": False}


def test_turns_a_flag_on() -> None:
    assert toggle_flag({"debug": False}, "debug") == {"debug": True}
""",
        imports="from flag_state import toggle_flag\n",
    ),
    hidden_test=_test_module(
        "flag_state",
        "The part of the contract the published tests do not state.",
        """
def test_turns_a_flag_off() -> None:
    assert toggle_flag({"debug": True}, "debug") == {"debug": False}


def test_the_input_is_not_mutated() -> None:
    original = {"debug": True}
    toggle_flag(original, "debug")
    assert original == {"debug": True}


def test_an_unknown_flag_turns_on() -> None:
    assert toggle_flag({}, "trace") == {"trace": True}
""",
        imports="from flag_state import toggle_flag\n",
    ),
)

_D54 = D2TaskSpec(
    template_id="d2_state.apply_once",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-apply-once",
    module="event_application",
    module_doc="Applying an event to a running total exactly once.",
    issue=(
        "apply_once() is documented to apply each event once, however often it is delivered. "
        "Callers report redelivered events being counted again, and their state changing."
    ),
    expected=(
        "apply_once(state, event_id, amount) applies the amount only for an event it has not "
        "seen, and returns a new state rather than changing the one it was given."
    ),
    baseline_reason="the identifier is recorded but never consulted, and the writes are in place",
    edge_cases=("replaying an event is a no-op", "the input is not mutated"),
    baseline="""def apply_once(state, event_id, amount):
    \"\"\"Apply `amount` for `event_id`, once.\"\"\"
    state["total"] = state.get("total", 0) + amount
    state.setdefault("applied", []).append(event_id)
    return state""",
    variant_one="""def apply_once(state, event_id, amount):
    \"\"\"Apply `amount` for `event_id`, once.\"\"\"
    applied = list(state.get("applied", []))
    if event_id in applied:
        return dict(state)
    applied.append(event_id)
    return {**state, "total": state.get("total", 0) + amount, "applied": applied}""",
    variant_two="""def apply_once(state, event_id, amount):
    \"\"\"Apply `amount` for `event_id`, once.\"\"\"
    updated = dict(state.items())
    seen = tuple(updated.get("applied", ()))
    if event_id in seen:
        updated["applied"] = list(seen)
    else:
        updated["total"] = updated.get("total", 0) + amount
        updated["applied"] = [*seen, event_id]
    return updated""",
    variant_three="""def apply_once(state, event_id, amount):
    \"\"\"Apply `amount` for `event_id`, once.\"\"\"
    if event_id in state.get("applied", []):
        return state
    state["total"] = state.get("total", 0) + amount
    state.setdefault("applied", []).append(event_id)
    return state""",
    variant_four="""def apply_once(state, event_id, amount):
    \"\"\"Apply `amount` for `event_id`, once.\"\"\"
    applied = list(state.get("applied", []))
    applied.append(event_id)
    return {**state, "total": state.get("total", 0) + amount, "applied": applied}""",
    visible_test=_test_module(
        "event_application",
        "Published contract for event application.",
        """
def test_applies_an_event() -> None:
    assert apply_once({}, "e1", 5)["total"] == 5


def test_applies_two_different_events() -> None:
    first = apply_once({}, "e1", 5)
    assert apply_once(first, "e2", 3)["total"] == 8
""",
        imports="from event_application import apply_once\n",
    ),
    hidden_test=_test_module(
        "event_application",
        "The part of the contract the published tests do not state.",
        """
def test_applies_an_event() -> None:
    assert apply_once({}, "e1", 5)["total"] == 5


def test_replaying_an_event_is_a_no_op() -> None:
    once = apply_once({}, "e1", 5)
    assert apply_once(once, "e1", 5)["total"] == 5


def test_the_input_is_not_mutated() -> None:
    original = {"total": 1, "applied": []}
    apply_once(original, "e1", 5)
    assert original == {"total": 1, "applied": []}
""",
        imports="from event_application import apply_once\n",
    ),
)

_D55 = D2TaskSpec(
    template_id="d2_state.bump_version",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-bump",
    module="version_state",
    module_doc="Advancing a schema version counter.",
    issue=(
        "bump_version() is documented to return the new state and the version it just wrote. "
        "Callers report the previous version coming back, and a crash on a first bump."
    ),
    expected=(
        "bump_version(state, key) returns (state, version) where the version is the one just "
        "written, and a key that has never been bumped starts at one."
    ),
    baseline_reason="the returned number is read back after the write and then decremented",
    edge_cases=("a missing key starts at one", "the returned version is the new one"),
    baseline="""def bump_version(state, key):
    \"\"\"Advance the version stored under `key`.\"\"\"
    state[key] += 1
    return state, state[key] - 1""",
    variant_one="""def bump_version(state, key):
    \"\"\"Advance the version stored under `key`.\"\"\"
    updated = dict(state)
    version = updated.get(key, 0) + 1
    updated[key] = version
    return updated, version""",
    variant_two="""def bump_version(state, key):
    \"\"\"Advance the version stored under `key`.\"\"\"
    current = state.get(key, 0)
    return {**state, key: current + 1}, current + 1""",
    variant_three="""def bump_version(state, key):
    \"\"\"Advance the version stored under `key`.\"\"\"
    updated = dict(state)
    updated[key] = updated.get(key, 0) + 1
    return updated, updated[key] - 1""",
    variant_four="""def bump_version(state, key):
    \"\"\"Advance the version stored under `key`.\"\"\"
    state[key] += 1
    return state, state[key]""",
    visible_test=_test_module(
        "version_state",
        "Published contract for version bumping.",
        """
def test_bumps_a_known_version() -> None:
    assert bump_version({"schema": 3}, "schema")[0] == {"schema": 4}


def test_bumps_twice() -> None:
    once, _ = bump_version({"schema": 1}, "schema")
    assert bump_version(once, "schema")[0] == {"schema": 3}
""",
        imports="from version_state import bump_version\n",
    ),
    hidden_test=_test_module(
        "version_state",
        "The part of the contract the published tests do not state.",
        """
def test_bumps_a_known_version() -> None:
    assert bump_version({"schema": 3}, "schema")[0] == {"schema": 4}


def test_a_missing_key_starts_at_one() -> None:
    assert bump_version({}, "schema")[0] == {"schema": 1}


def test_the_returned_version_is_the_new_one() -> None:
    assert bump_version({"schema": 3}, "schema")[1] == 4
""",
        imports="from version_state import bump_version\n",
    ),
)

_D56 = D2TaskSpec(
    template_id="d2_state.enqueue_unique",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-unique-queue",
    module="unique_queue",
    module_doc="Appending to a queue that holds each item once.",
    issue=(
        "enqueue_unique() is documented to leave an item that is already queued exactly where "
        "it is. Callers report re-queued items jumping to the back, and their list changing."
    ),
    expected=(
        "enqueue_unique(queue, item) returns a new list, appends an item that is not queued, "
        "and leaves an item that is already queued in its original place."
    ),
    baseline_reason="the item is removed and re-appended, in the caller's own list",
    edge_cases=("the input is not mutated", "an item already queued keeps its place"),
    baseline="""def enqueue_unique(queue, item):
    \"\"\"Return `queue` with `item` present exactly once.\"\"\"
    if item in queue:
        queue.remove(item)
    queue.append(item)
    return queue""",
    variant_one="""def enqueue_unique(queue, item):
    \"\"\"Return `queue` with `item` present exactly once.\"\"\"
    if item in queue:
        return list(queue)
    return [*queue, item]""",
    variant_two="""def enqueue_unique(queue, item):
    \"\"\"Return `queue` with `item` present exactly once.\"\"\"
    from itertools import chain

    seen = set(queue)
    extra = () if item in seen else (item,)
    return list(chain(queue, extra))""",
    variant_three="""def enqueue_unique(queue, item):
    \"\"\"Return `queue` with `item` present exactly once.\"\"\"
    updated = list(queue)
    if item in updated:
        updated.remove(item)
    updated.append(item)
    return updated""",
    variant_four="""def enqueue_unique(queue, item):
    \"\"\"Return `queue` with `item` present exactly once.\"\"\"
    if item not in queue:
        queue.append(item)
    return queue""",
    visible_test=_test_module(
        "unique_queue",
        "Published contract for unique queueing.",
        """
def test_appends_a_new_item() -> None:
    assert enqueue_unique(["a"], "b") == ["a", "b"]


def test_appends_to_an_empty_queue() -> None:
    assert enqueue_unique([], "a") == ["a"]
""",
        imports="from unique_queue import enqueue_unique\n",
    ),
    hidden_test=_test_module(
        "unique_queue",
        "The part of the contract the published tests do not state.",
        """
def test_appends_a_new_item() -> None:
    assert enqueue_unique(["a"], "b") == ["a", "b"]


def test_the_input_is_not_mutated() -> None:
    original = ["a"]
    enqueue_unique(original, "b")
    assert original == ["a"]


def test_an_item_already_queued_keeps_its_place() -> None:
    assert enqueue_unique(["a", "b"], "a") == ["a", "b"]
""",
        imports="from unique_queue import enqueue_unique\n",
    ),
)

_D57 = D2TaskSpec(
    template_id="d2_state.reset_counters",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-reset",
    module="counter_reset",
    module_doc="Resetting named counters and reporting what changed.",
    issue=(
        "reset_counters() is documented to report how many counters it actually changed. "
        "Callers report counters that were already at zero being counted, and names they "
        "asked for going missing entirely."
    ),
    expected=(
        "reset_counters(state, names) returns (state, changed) with every named counter at "
        "zero including ones that did not exist, and `changed` counting only real resets."
    ),
    baseline_reason="an unknown name is skipped, and every known one is counted as a reset",
    edge_cases=(
        "an unknown name is created at zero",
        "a counter already at zero is not counted",
    ),
    baseline="""def reset_counters(state, names):
    \"\"\"Reset the counters in `names`, reporting how many changed.\"\"\"
    updated = dict(state)
    changed = 0
    for name in names:
        if name in updated:
            updated[name] = 0
            changed += 1
    return updated, changed""",
    variant_one="""def reset_counters(state, names):
    \"\"\"Reset the counters in `names`, reporting how many changed.\"\"\"
    updated = dict(state)
    changed = 0
    for name in names:
        if updated.get(name, 0) != 0:
            changed += 1
        updated[name] = 0
    return updated, changed""",
    variant_two="""def reset_counters(state, names):
    \"\"\"Reset the counters in `names`, reporting how many changed.\"\"\"
    wanted = list(names)
    changed = sum(1 for name in wanted if state.get(name, 0))
    return {**state, **dict.fromkeys(wanted, 0)}, changed""",
    variant_three="""def reset_counters(state, names):
    \"\"\"Reset the counters in `names`, reporting how many changed.\"\"\"
    updated = dict(state)
    changed = 0
    for name in names:
        updated[name] = 0
        changed += 1
    return updated, changed""",
    variant_four="""def reset_counters(state, names):
    \"\"\"Reset the counters in `names`, reporting how many changed.\"\"\"
    updated = dict(state)
    changed = 0
    for name in names:
        if name in updated:
            if updated[name]:
                changed += 1
            updated[name] = 0
    return updated, changed""",
    visible_test=_test_module(
        "counter_reset",
        "Published contract for counter resets.",
        """
def test_resets_a_counter() -> None:
    assert reset_counters({"hits": 5}, ["hits"])[0] == {"hits": 0}


def test_counts_the_reset() -> None:
    assert reset_counters({"hits": 5}, ["hits"])[1] == 1
""",
        imports="from counter_reset import reset_counters\n",
    ),
    hidden_test=_test_module(
        "counter_reset",
        "The part of the contract the published tests do not state.",
        """
def test_resets_a_counter() -> None:
    assert reset_counters({"hits": 5}, ["hits"])[0] == {"hits": 0}


def test_an_unknown_name_is_created_at_zero() -> None:
    assert reset_counters({}, ["misses"])[0] == {"misses": 0}


def test_a_counter_already_at_zero_is_not_counted() -> None:
    assert reset_counters({"hits": 0}, ["hits"])[1] == 0
""",
        imports="from counter_reset import reset_counters\n",
    ),
)

_D58 = D2TaskSpec(
    template_id="d2_state.close_session",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-session-close",
    module="session_state",
    module_doc="Closing a session in a session table.",
    issue=(
        "close_session() is documented to leave an already-closed session alone and to refuse "
        "a session it does not know. Callers report close times being overwritten by retries, "
        "and unknown identifiers quietly creating entries."
    ),
    expected=(
        "close_session(state, session_id, closed_at) closes an open session, leaves an "
        "already-closed one exactly as it was, and raises KeyError for an unknown session."
    ),
    baseline_reason="the entry is written unconditionally, whether or not one was there",
    edge_cases=(
        "closing twice keeps the first time",
        "an unknown session is refused",
    ),
    baseline="""def close_session(state, session_id, closed_at):
    \"\"\"Close `session_id` at `closed_at`.\"\"\"
    updated = dict(state)
    updated[session_id] = {"open": False, "closed_at": closed_at}
    return updated""",
    variant_one="""def close_session(state, session_id, closed_at):
    \"\"\"Close `session_id` at `closed_at`.\"\"\"
    if session_id not in state:
        raise KeyError(session_id)
    session = state[session_id]
    if not session["open"]:
        return dict(state)
    return {**state, session_id: {"open": False, "closed_at": closed_at}}""",
    variant_two="""def close_session(state, session_id, closed_at):
    \"\"\"Close `session_id` at `closed_at`.\"\"\"
    sessions = dict(state)
    session = sessions[session_id]
    if session["open"]:
        sessions[session_id] = {"open": False, "closed_at": closed_at}
    return sessions""",
    variant_three="""def close_session(state, session_id, closed_at):
    \"\"\"Close `session_id` at `closed_at`.\"\"\"
    updated = dict(state)
    session = updated.get(session_id, {"open": True})
    if session["open"]:
        updated[session_id] = {"open": False, "closed_at": closed_at}
    return updated""",
    variant_four="""def close_session(state, session_id, closed_at):
    \"\"\"Close `session_id` at `closed_at`.\"\"\"
    if session_id not in state:
        raise KeyError(session_id)
    return {**state, session_id: {"open": False, "closed_at": closed_at}}""",
    visible_test=_test_module(
        "session_state",
        "Published contract for session closing.",
        """
def test_closes_an_open_session() -> None:
    state = {"s1": {"open": True, "closed_at": None}}
    assert close_session(state, "s1", 10)["s1"] == {"open": False, "closed_at": 10}


def test_leaves_other_sessions_alone() -> None:
    state = {
        "s1": {"open": True, "closed_at": None},
        "s2": {"open": True, "closed_at": None},
    }
    assert close_session(state, "s1", 10)["s2"] == {"open": True, "closed_at": None}
""",
        imports="from session_state import close_session\n",
    ),
    hidden_test=_test_module(
        "session_state",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_closes_an_open_session() -> None:
    state = {"s1": {"open": True, "closed_at": None}}
    assert close_session(state, "s1", 10)["s1"] == {"open": False, "closed_at": 10}


def test_closing_twice_keeps_the_first_time() -> None:
    state = {"s1": {"open": False, "closed_at": 10}}
    assert close_session(state, "s1", 99)["s1"]["closed_at"] == 10


def test_an_unknown_session_is_refused() -> None:
    with pytest.raises(KeyError):
        close_session({}, "s9", 10)
""",
        imports="from session_state import close_session\n",
    ),
)

_D59 = D2TaskSpec(
    template_id="d2_state.record_attempt",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-attempts",
    module="attempt_tracking",
    module_doc="Counting attempts against a limit.",
    issue=(
        "record_attempt() is documented to stop counting at the limit and to report exhaustion "
        "when the limit is reached. Callers report counts running past the limit, and the "
        "exhaustion flag arriving one attempt late."
    ),
    expected=(
        "record_attempt(state, key, limit) returns (state, exhausted) with the count capped at "
        "the limit and `exhausted` true as soon as the count reaches it."
    ),
    baseline_reason="nothing caps the count, and exhaustion is tested with a strict comparison",
    edge_cases=(
        "the count stops at the limit",
        "reaching the limit is exhaustion",
    ),
    baseline="""def record_attempt(state, key, limit):
    \"\"\"Record one attempt against `key`, capped at `limit`.\"\"\"
    updated = dict(state)
    updated[key] = updated.get(key, 0) + 1
    return updated, updated[key] > limit""",
    variant_one="""def record_attempt(state, key, limit):
    \"\"\"Record one attempt against `key`, capped at `limit`.\"\"\"
    updated = dict(state)
    updated[key] = min(updated.get(key, 0) + 1, limit)
    return updated, updated[key] >= limit""",
    variant_two="""def record_attempt(state, key, limit):
    \"\"\"Record one attempt against `key`, capped at `limit`.\"\"\"
    current = state.get(key, 0)
    following = current + 1 if current < limit else limit
    return {**state, key: following}, not following < limit""",
    variant_three="""def record_attempt(state, key, limit):
    \"\"\"Record one attempt against `key`, capped at `limit`.\"\"\"
    updated = dict(state)
    updated[key] = min(updated.get(key, 0) + 1, limit)
    return updated, updated[key] > limit""",
    variant_four="""def record_attempt(state, key, limit):
    \"\"\"Record one attempt against `key`, capped at `limit`.\"\"\"
    updated = dict(state)
    updated[key] = updated.get(key, 0) + 1
    return updated, updated[key] >= limit""",
    visible_test=_test_module(
        "attempt_tracking",
        "Published contract for attempt counting.",
        """
def test_records_a_first_attempt() -> None:
    assert record_attempt({}, "login", 3)[0] == {"login": 1}


def test_is_not_exhausted_early() -> None:
    assert record_attempt({}, "login", 3)[1] is False
""",
        imports="from attempt_tracking import record_attempt\n",
    ),
    hidden_test=_test_module(
        "attempt_tracking",
        "The part of the contract the published tests do not state.",
        """
def test_records_a_first_attempt() -> None:
    assert record_attempt({}, "login", 3)[0] == {"login": 1}


def test_the_count_stops_at_the_limit() -> None:
    assert record_attempt({"login": 3}, "login", 3)[0] == {"login": 3}


def test_reaching_the_limit_is_exhaustion() -> None:
    assert record_attempt({"login": 2}, "login", 3)[1] is True
""",
        imports="from attempt_tracking import record_attempt\n",
    ),
)

_D60 = D2TaskSpec(
    template_id="d2_state.swap_owner",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-ownership",
    module="ownership",
    module_doc="Handing a resource from one owner to another.",
    issue=(
        "swap_owner() is documented to record a handover only when the owner really changes. "
        "Callers report the history growing on repeated assignments to the same owner, and "
        "unknown resources being created rather than refused."
    ),
    expected=(
        "swap_owner(state, resource, new_owner) records a handover only when the owner "
        "changes, and raises KeyError for a resource that is not there."
    ),
    baseline_reason="the history is appended before the current owner is ever compared",
    edge_cases=(
        "handing to the same owner is a no-op",
        "an unknown resource is refused",
    ),
    baseline="""def swap_owner(state, resource, new_owner):
    \"\"\"Hand `resource` to `new_owner`.\"\"\"
    updated = dict(state)
    entry = dict(updated.get(resource, {"owner": None, "history": []}))
    entry["history"] = [*entry["history"], new_owner]
    entry["owner"] = new_owner
    updated[resource] = entry
    return updated""",
    variant_one="""def swap_owner(state, resource, new_owner):
    \"\"\"Hand `resource` to `new_owner`.\"\"\"
    if resource not in state:
        raise KeyError(resource)
    entry = state[resource]
    if entry["owner"] == new_owner:
        return dict(state)
    changed = {"owner": new_owner, "history": [*entry["history"], new_owner]}
    return {**state, resource: changed}""",
    variant_two="""def swap_owner(state, resource, new_owner):
    \"\"\"Hand `resource` to `new_owner`.\"\"\"
    updated = dict(state)
    entry = dict(updated[resource])
    if entry["owner"] != new_owner:
        entry["owner"] = new_owner
        entry["history"] = entry["history"] + [new_owner]
        updated[resource] = entry
    return updated""",
    variant_three="""def swap_owner(state, resource, new_owner):
    \"\"\"Hand `resource` to `new_owner`.\"\"\"
    updated = dict(state)
    entry = dict(updated.get(resource, {"owner": None, "history": []}))
    if entry["owner"] != new_owner:
        entry["owner"] = new_owner
        entry["history"] = [*entry["history"], new_owner]
    updated[resource] = entry
    return updated""",
    variant_four="""def swap_owner(state, resource, new_owner):
    \"\"\"Hand `resource` to `new_owner`.\"\"\"
    if resource not in state:
        raise KeyError(resource)
    entry = dict(state[resource])
    entry["history"] = [*entry["history"], new_owner]
    entry["owner"] = new_owner
    return {**state, resource: entry}""",
    visible_test=_test_module(
        "ownership",
        "Published contract for ownership handovers.",
        """
def test_hands_a_resource_over() -> None:
    state = {"disk": {"owner": "a", "history": ["a"]}}
    assert swap_owner(state, "disk", "b")["disk"]["owner"] == "b"


def test_records_the_handover() -> None:
    state = {"disk": {"owner": "a", "history": ["a"]}}
    assert swap_owner(state, "disk", "b")["disk"]["history"] == ["a", "b"]
""",
        imports="from ownership import swap_owner\n",
    ),
    hidden_test=_test_module(
        "ownership",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_hands_a_resource_over() -> None:
    state = {"disk": {"owner": "a", "history": ["a"]}}
    assert swap_owner(state, "disk", "b")["disk"]["owner"] == "b"


def test_handing_to_the_same_owner_is_a_no_op() -> None:
    state = {"disk": {"owner": "a", "history": ["a"]}}
    assert swap_owner(state, "disk", "a")["disk"]["history"] == ["a"]


def test_an_unknown_resource_is_refused() -> None:
    with pytest.raises(KeyError):
        swap_owner({}, "tape", "a")
""",
        imports="from ownership import swap_owner\n",
    ),
)

_D61 = D2TaskSpec(
    template_id="d2_state.drain",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-drain",
    module="buffer_draining",
    module_doc="Taking a bounded batch off a buffer.",
    issue=(
        "drain() is documented to take at most `limit` items. Callers report a limit of zero "
        "draining the whole buffer, and a negative limit being accepted silently."
    ),
    expected=(
        "drain(buffer, limit) returns (taken, remaining), takes nothing for a limit of zero, "
        "and raises ValueError for a negative limit."
    ),
    baseline_reason="a zero limit is falsy, so the guard hands back everything instead of nothing",
    edge_cases=("a zero limit takes nothing", "a negative limit is refused"),
    baseline="""def drain(buffer, limit):
    \"\"\"Take at most `limit` items off `buffer`.\"\"\"
    taken = buffer[:limit] if limit else buffer
    return taken, buffer[limit:]""",
    variant_one="""def drain(buffer, limit):
    \"\"\"Take at most `limit` items off `buffer`.\"\"\"
    if limit < 0:
        raise ValueError("the limit must not be negative")
    return list(buffer[:limit]), list(buffer[limit:])""",
    variant_two="""def drain(buffer, limit):
    \"\"\"Take at most `limit` items off `buffer`.\"\"\"
    if limit < 0:
        raise ValueError("the limit must not be negative")
    taken = []
    remaining = []
    for index, item in enumerate(buffer):
        target = taken if index < limit else remaining
        target.append(item)
    return taken, remaining""",
    variant_three="""def drain(buffer, limit):
    \"\"\"Take at most `limit` items off `buffer`.\"\"\"
    return list(buffer[:limit]), list(buffer[limit:])""",
    variant_four="""def drain(buffer, limit):
    \"\"\"Take at most `limit` items off `buffer`.\"\"\"
    if limit < 0:
        raise ValueError("the limit must not be negative")
    taken = buffer[:limit] if limit else buffer
    return taken, buffer[limit:]""",
    visible_test=_test_module(
        "buffer_draining",
        "Published contract for draining.",
        """
def test_takes_the_first_two() -> None:
    assert drain([1, 2, 3], 2) == ([1, 2], [3])


def test_a_large_limit_takes_everything() -> None:
    assert drain([1, 2], 5) == ([1, 2], [])
""",
        imports="from buffer_draining import drain\n",
    ),
    hidden_test=_test_module(
        "buffer_draining",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_takes_the_first_two() -> None:
    assert drain([1, 2, 3], 2) == ([1, 2], [3])


def test_a_zero_limit_takes_nothing() -> None:
    assert drain([1, 2], 0) == ([], [1, 2])


def test_a_negative_limit_is_refused() -> None:
    with pytest.raises(ValueError):
        drain([1, 2], -1)
""",
        imports="from buffer_draining import drain\n",
    ),
)

_D62 = D2TaskSpec(
    template_id="d2_state.extend_lease",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-lease",
    module="lease_state",
    module_doc="Extending a lease that a holder already has.",
    issue=(
        "extend_lease() is documented to add to whatever a holder already has. Callers report "
        "extensions replacing the lease instead, and a zero extension being accepted."
    ),
    expected=(
        "extend_lease(state, holder, amount) adds the amount to any existing lease, and raises "
        "ValueError when the amount is not positive."
    ),
    baseline_reason="the new amount is written over the old one, and it is never checked",
    edge_cases=(
        "an extension adds to the existing lease",
        "a non-positive extension is refused",
    ),
    baseline="""def extend_lease(state, holder, amount):
    \"\"\"Extend the lease held by `holder` by `amount`.\"\"\"
    leases = dict(state)
    leases.update({holder: amount})
    return leases""",
    variant_one="""def extend_lease(state, holder, amount):
    \"\"\"Extend the lease held by `holder` by `amount`.\"\"\"
    if amount <= 0:
        raise ValueError("the extension must be positive")
    updated = dict(state)
    updated[holder] = updated.get(holder, 0) + amount
    return updated""",
    variant_two="""def extend_lease(state, holder, amount):
    \"\"\"Extend the lease held by `holder` by `amount`.\"\"\"
    if not amount > 0:
        raise ValueError("the extension must be positive")
    return {**state, holder: state.get(holder, 0) + amount}""",
    variant_three="""def extend_lease(state, holder, amount):
    \"\"\"Extend the lease held by `holder` by `amount`.\"\"\"
    updated = dict(state)
    updated[holder] = updated.get(holder, 0) + amount
    return updated""",
    variant_four="""def extend_lease(state, holder, amount):
    \"\"\"Extend the lease held by `holder` by `amount`.\"\"\"
    if amount <= 0:
        raise ValueError("the extension must be positive")
    updated = dict(state)
    updated[holder] = amount
    return updated""",
    visible_test=_test_module(
        "lease_state",
        "Published contract for lease extension.",
        """
def test_grants_a_lease_to_a_new_holder() -> None:
    assert extend_lease({}, "a", 10) == {"a": 10}


def test_leaves_other_holders_alone() -> None:
    assert extend_lease({"b": 5}, "a", 10)["b"] == 5
""",
        imports="from lease_state import extend_lease\n",
    ),
    hidden_test=_test_module(
        "lease_state",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_grants_a_lease_to_a_new_holder() -> None:
    assert extend_lease({}, "a", 10) == {"a": 10}


def test_an_extension_adds_to_the_existing_lease() -> None:
    assert extend_lease({"a": 10}, "a", 5) == {"a": 15}


def test_a_non_positive_extension_is_refused() -> None:
    with pytest.raises(ValueError):
        extend_lease({"a": 10}, "a", 0)
""",
        imports="from lease_state import extend_lease\n",
    ),
)

_D63 = D2TaskSpec(
    template_id="d2_state.promote",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-promote",
    module="priority_state",
    module_doc="Moving an entry one place up a priority order.",
    issue=(
        "promote() is documented to leave an entry that is already first exactly where it is. "
        "Callers report the first entry swapping with the last, and their own list changing."
    ),
    expected=(
        "promote(order, name) returns a new list with `name` one place earlier, and returns "
        "the order unchanged when `name` is already first."
    ),
    baseline_reason="index minus one wraps to the end of the list, and the swap is in place",
    edge_cases=(
        "promoting the first item is a no-op",
        "the input is not mutated",
    ),
    baseline="""def promote(order, name):
    \"\"\"Move `name` one place up `order`.\"\"\"
    index = order.index(name)
    order[index - 1], order[index] = order[index], order[index - 1]
    return order""",
    variant_one="""def promote(order, name):
    \"\"\"Move `name` one place up `order`.\"\"\"
    updated = list(order)
    index = updated.index(name)
    if index == 0:
        return updated
    updated[index - 1], updated[index] = updated[index], updated[index - 1]
    return updated""",
    variant_two="""def promote(order, name):
    \"\"\"Move `name` one place up `order`.\"\"\"
    updated = list(order)
    index = updated.index(name)
    if index > 0:
        updated.pop(index)
        updated.insert(index - 1, name)
    return updated""",
    variant_three="""def promote(order, name):
    \"\"\"Move `name` one place up `order`.\"\"\"
    index = order.index(name)
    if index == 0:
        return order
    order[index - 1], order[index] = order[index], order[index - 1]
    return order""",
    variant_four="""def promote(order, name):
    \"\"\"Move `name` one place up `order`.\"\"\"
    updated = list(order)
    index = updated.index(name)
    updated[index - 1], updated[index] = updated[index], updated[index - 1]
    return updated""",
    visible_test=_test_module(
        "priority_state",
        "Published contract for promotion.",
        """
def test_promotes_a_middle_item() -> None:
    assert promote(["a", "b", "c"], "b") == ["b", "a", "c"]


def test_promotes_the_last_item() -> None:
    assert promote(["a", "b", "c"], "c") == ["a", "c", "b"]
""",
        imports="from priority_state import promote\n",
    ),
    hidden_test=_test_module(
        "priority_state",
        "The part of the contract the published tests do not state.",
        """
def test_promotes_a_middle_item() -> None:
    assert promote(["a", "b", "c"], "b") == ["b", "a", "c"]


def test_promoting_the_first_item_is_a_no_op() -> None:
    assert promote(["a", "b"], "a") == ["a", "b"]


def test_the_input_is_not_mutated() -> None:
    original = ["a", "b"]
    promote(original, "b")
    assert original == ["a", "b"]
""",
        imports="from priority_state import promote\n",
    ),
)

_D64 = D2TaskSpec(
    template_id="d2_state.deactivate_all",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-deactivate",
    module="bulk_deactivation",
    module_doc="Deactivating every entry and reporting what changed.",
    issue=(
        "deactivate_all() is documented to report how many entries it actually deactivated. "
        "Callers report entries that were already inactive being counted, and the entries "
        "they passed in coming back changed."
    ),
    expected=(
        "deactivate_all(state) returns (state, count) with every entry inactive, counting only "
        "entries that were active, and without changing the mapping it was given."
    ),
    baseline_reason="each entry is written in place and counted whatever its previous value",
    edge_cases=(
        "an entry already inactive is not counted",
        "the input entries are not mutated",
    ),
    baseline="""def deactivate_all(state):
    \"\"\"Deactivate every entry, reporting how many changed.\"\"\"
    count = 0
    for entry in state.values():
        entry["active"] = False
        count += 1
    return state, count""",
    variant_one="""def deactivate_all(state):
    \"\"\"Deactivate every entry, reporting how many changed.\"\"\"
    updated = {}
    count = 0
    for key, entry in state.items():
        if entry["active"]:
            count += 1
        updated[key] = {**entry, "active": False}
    return updated, count""",
    variant_two="""def deactivate_all(state):
    \"\"\"Deactivate every entry, reporting how many changed.\"\"\"
    count = sum(1 for entry in state.values() if entry["active"])
    updated = {key: dict(entry, active=False) for key, entry in state.items()}
    return updated, count""",
    variant_three="""def deactivate_all(state):
    \"\"\"Deactivate every entry, reporting how many changed.\"\"\"
    count = 0
    for entry in state.values():
        if entry["active"]:
            count += 1
        entry["active"] = False
    return state, count""",
    variant_four="""def deactivate_all(state):
    \"\"\"Deactivate every entry, reporting how many changed.\"\"\"
    updated = {}
    count = 0
    for key, entry in state.items():
        updated[key] = {**entry, "active": False}
        count += 1
    return updated, count""",
    visible_test=_test_module(
        "bulk_deactivation",
        "Published contract for bulk deactivation.",
        """
def test_deactivates_everything() -> None:
    state = {"a": {"active": True}, "b": {"active": True}}
    assert deactivate_all(state)[0] == {"a": {"active": False}, "b": {"active": False}}


def test_counts_the_deactivations() -> None:
    state = {"a": {"active": True}, "b": {"active": True}}
    assert deactivate_all(state)[1] == 2
""",
        imports="from bulk_deactivation import deactivate_all\n",
    ),
    hidden_test=_test_module(
        "bulk_deactivation",
        "The part of the contract the published tests do not state.",
        """
def test_deactivates_everything() -> None:
    state = {"a": {"active": True}, "b": {"active": True}}
    assert deactivate_all(state)[0] == {"a": {"active": False}, "b": {"active": False}}


def test_an_entry_already_inactive_is_not_counted() -> None:
    state = {"a": {"active": True}, "b": {"active": False}}
    assert deactivate_all(state)[1] == 1


def test_the_input_entries_are_not_mutated() -> None:
    original = {"a": {"active": True}}
    deactivate_all(original)
    assert original == {"a": {"active": True}}
""",
        imports="from bulk_deactivation import deactivate_all\n",
    ),
)

_D65 = D2TaskSpec(
    template_id="d2_state.retire_key",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-retire",
    module="key_retirement",
    module_doc="Retiring a key and reporting whether it was there.",
    issue=(
        "retire_key() is documented to be safe to call for a key that is already gone. Callers "
        "report a crash on retrying a retirement, and their own mapping losing entries."
    ),
    expected=(
        "retire_key(state, key) returns (state, was_present), leaves the caller's mapping "
        "untouched, and reports False rather than raising for a key that is not there."
    ),
    baseline_reason="the deletion is in place and assumes the key exists",
    edge_cases=(
        "retiring an absent key reports false",
        "the input is not mutated",
    ),
    baseline="""def retire_key(state, key):
    \"\"\"Retire `key`, reporting whether it was there.\"\"\"
    del state[key]
    return state, True""",
    variant_one="""def retire_key(state, key):
    \"\"\"Retire `key`, reporting whether it was there.\"\"\"
    updated = dict(state)
    present = key in updated
    updated.pop(key, None)
    return updated, present""",
    variant_two="""def retire_key(state, key):
    \"\"\"Retire `key`, reporting whether it was there.\"\"\"
    updated = {name: value for name, value in state.items() if name != key}
    return updated, len(updated) != len(state)""",
    variant_three="""def retire_key(state, key):
    \"\"\"Retire `key`, reporting whether it was there.\"\"\"
    present = key in state
    state.pop(key, None)
    return state, present""",
    variant_four="""def retire_key(state, key):
    \"\"\"Retire `key`, reporting whether it was there.\"\"\"
    updated = dict(state)
    del updated[key]
    return updated, True""",
    visible_test=_test_module(
        "key_retirement",
        "Published contract for key retirement.",
        """
def test_retires_a_key() -> None:
    assert retire_key({"a": 1, "b": 2}, "a")[0] == {"b": 2}


def test_reports_a_retired_key() -> None:
    assert retire_key({"a": 1}, "a")[1] is True
""",
        imports="from key_retirement import retire_key\n",
    ),
    hidden_test=_test_module(
        "key_retirement",
        "The part of the contract the published tests do not state.",
        """
def test_retires_a_key() -> None:
    assert retire_key({"a": 1, "b": 2}, "a")[0] == {"b": 2}


def test_retiring_an_absent_key_reports_false() -> None:
    assert retire_key({"a": 1}, "z") == ({"a": 1}, False)


def test_the_input_is_not_mutated() -> None:
    original = {"a": 1}
    retire_key(original, "a")
    assert original == {"a": 1}
""",
        imports="from key_retirement import retire_key\n",
    ),
)

_D66 = D2TaskSpec(
    template_id="d2_state.mark_seen",
    family=RealityTaskFamily.STATE_IDEMPOTENCY,
    repository_group="d2-state-seen",
    module="seen_tracking",
    module_doc="Recording each item the first time it is seen.",
    issue=(
        "mark_seen() is documented to record each item once. Callers report duplicates piling "
        "up in the record, and the list they passed in growing behind their back."
    ),
    expected=(
        "mark_seen(state, item) returns (record, was_new) with the item recorded only the "
        "first time, and without changing the list it was given."
    ),
    baseline_reason="the append happens whatever the answer, and it happens to the caller's list",
    edge_cases=(
        "an item seen before is not recorded twice",
        "the input is not mutated",
    ),
    baseline="""def mark_seen(state, item):
    \"\"\"Record `item`, reporting whether it was new.\"\"\"
    was_new = item not in state
    state.append(item)
    return state, was_new""",
    variant_one="""def mark_seen(state, item):
    \"\"\"Record `item`, reporting whether it was new.\"\"\"
    seen = list(state)
    if item in seen:
        return seen, False
    seen.append(item)
    return seen, True""",
    variant_two="""def mark_seen(state, item):
    \"\"\"Record `item`, reporting whether it was new.\"\"\"
    was_new = item not in state
    return list(state) + ([item] if was_new else []), was_new""",
    variant_three="""def mark_seen(state, item):
    \"\"\"Record `item`, reporting whether it was new.\"\"\"
    was_new = item not in state
    if was_new:
        state.append(item)
    return state, was_new""",
    variant_four="""def mark_seen(state, item):
    \"\"\"Record `item`, reporting whether it was new.\"\"\"
    seen = list(state)
    was_new = item not in seen
    seen.append(item)
    return seen, was_new""",
    visible_test=_test_module(
        "seen_tracking",
        "Published contract for sighting records.",
        """
def test_records_a_new_item() -> None:
    assert mark_seen([], "a") == (["a"], True)


def test_records_a_second_item() -> None:
    assert mark_seen(["a"], "b") == (["a", "b"], True)
""",
        imports="from seen_tracking import mark_seen\n",
    ),
    hidden_test=_test_module(
        "seen_tracking",
        "The part of the contract the published tests do not state.",
        """
def test_records_a_new_item() -> None:
    assert mark_seen([], "a") == (["a"], True)


def test_an_item_seen_before_is_not_recorded_twice() -> None:
    assert mark_seen(["a"], "a") == (["a"], False)


def test_the_input_is_not_mutated() -> None:
    original = ["a"]
    mark_seen(original, "b")
    assert original == ["a"]
""",
        imports="from seen_tracking import mark_seen\n",
    ),
)

# ------------------------------------------------------------------ error handling, S21D2-022

_D67 = D2TaskSpec(
    template_id="d2_errors.safe_index",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-safe-index",
    module="index_access",
    module_doc="Reading a position out of a sequence safely.",
    issue=(
        "safe_index() is documented to fall back to the caller's default rather than raising. "
        "Callers report crashes past the end, and negative positions reading from the back."
    ),
    expected=(
        "safe_index(items, index, default) returns the item at `index`, returns the default "
        "when the index is past the end, and raises ValueError for a negative index."
    ),
    baseline_reason="the subscript is handed straight to the sequence, which does neither",
    edge_cases=(
        "a negative index is refused",
        "an index past the end gives the default",
    ),
    baseline="""def safe_index(items, index, default):
    \"\"\"Return the item at `index`, or `default`.\"\"\"
    return items[index]""",
    variant_one="""def safe_index(items, index, default):
    \"\"\"Return the item at `index`, or `default`.\"\"\"
    if index < 0:
        raise ValueError("the index must not be negative")
    if index >= len(items):
        return default
    return items[index]""",
    variant_two="""def safe_index(items, index, default):
    \"\"\"Return the item at `index`, or `default`.\"\"\"
    if index < 0:
        raise ValueError("the index must not be negative")
    try:
        return items[index]
    except IndexError:
        return default""",
    variant_three="""def safe_index(items, index, default):
    \"\"\"Return the item at `index`, or `default`.\"\"\"
    if index < 0:
        raise ValueError("the index must not be negative")
    return items[index]""",
    variant_four="""def safe_index(items, index, default):
    \"\"\"Return the item at `index`, or `default`.\"\"\"
    try:
        return items[index]
    except IndexError:
        return default""",
    visible_test=_test_module(
        "index_access",
        "Published contract for safe indexing.",
        """
def test_reads_an_item() -> None:
    assert safe_index([1, 2, 3], 1, 0) == 2


def test_reads_the_first_item() -> None:
    assert safe_index([9], 0, 0) == 9
""",
        imports="from index_access import safe_index\n",
    ),
    hidden_test=_test_module(
        "index_access",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reads_an_item() -> None:
    assert safe_index([1, 2, 3], 1, 0) == 2


def test_a_negative_index_is_refused() -> None:
    with pytest.raises(ValueError):
        safe_index([1, 2, 3], -1, 0)


def test_an_index_past_the_end_gives_the_default() -> None:
    assert safe_index([1, 2], 5, 0) == 0
""",
        imports="from index_access import safe_index\n",
    ),
)

_D68 = D2TaskSpec(
    template_id="d2_errors.require_keys",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-required-keys",
    module="key_requirements",
    module_doc="Checking that a configuration carries what it must.",
    issue=(
        "require_keys() is documented to name everything that is missing, so a caller can fix "
        "it all at once. Callers report one name at a time, and keys set to None being called "
        "missing."
    ),
    expected=(
        "require_keys(mapping, required) names every missing key in one error, and treats a "
        "key that is present with a value of None as present."
    ),
    baseline_reason="the loop raises on the first miss, and a falsy value counts as absent",
    edge_cases=(
        "every missing key is named",
        "a key present but none counts as present",
    ),
    baseline="""def require_keys(mapping, required):
    \"\"\"Return `mapping` once every key in `required` is present.\"\"\"
    for key in required:
        if not mapping.get(key):
            raise KeyError(f"missing: {key}")
    return mapping""",
    variant_one="""def require_keys(mapping, required):
    \"\"\"Return `mapping` once every key in `required` is present.\"\"\"
    missing = [key for key in required if key not in mapping]
    if missing:
        raise KeyError("missing: " + ", ".join(sorted(missing)))
    return mapping""",
    variant_two="""def require_keys(mapping, required):
    \"\"\"Return `mapping` once every key in `required` is present.\"\"\"
    absent = set(required) - set(mapping)
    if absent:
        raise KeyError("missing: " + ", ".join(sorted(absent)))
    return mapping""",
    variant_three="""def require_keys(mapping, required):
    \"\"\"Return `mapping` once every key in `required` is present.\"\"\"
    missing = [key for key in required if not mapping.get(key)]
    if missing:
        raise KeyError("missing: " + ", ".join(sorted(missing)))
    return mapping""",
    variant_four="""def require_keys(mapping, required):
    \"\"\"Return `mapping` once every key in `required` is present.\"\"\"
    for key in required:
        if key not in mapping:
            raise KeyError(f"missing: {key}")
    return mapping""",
    visible_test=_test_module(
        "key_requirements",
        "Published contract for required keys.",
        """
import pytest


def test_accepts_a_complete_mapping() -> None:
    assert require_keys({"a": 1, "b": 2}, ["a", "b"]) == {"a": 1, "b": 2}


def test_names_a_missing_key() -> None:
    with pytest.raises(KeyError, match="a"):
        require_keys({}, ["a"])
""",
        imports="from key_requirements import require_keys\n",
    ),
    hidden_test=_test_module(
        "key_requirements",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_accepts_a_complete_mapping() -> None:
    assert require_keys({"a": 1, "b": 2}, ["a", "b"]) == {"a": 1, "b": 2}


def test_every_missing_key_is_named() -> None:
    with pytest.raises(KeyError, match="a, b"):
        require_keys({}, ["a", "b"])


def test_a_key_present_but_none_counts_as_present() -> None:
    assert require_keys({"a": None}, ["a"]) == {"a": None}
""",
        imports="from key_requirements import require_keys\n",
    ),
)

_D69 = D2TaskSpec(
    template_id="d2_errors.retry_call",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-retry",
    module="retrying",
    module_doc="Retrying an action a bounded number of times.",
    issue=(
        "retry_call() is documented to give up by re-raising, so a caller can see why. Callers "
        "report None coming back after every attempt failed, and zero attempts being accepted."
    ),
    expected=(
        "retry_call(action, attempts) returns the first success, re-raises the last failure "
        "when every attempt fails, and raises ValueError when the attempt count is not "
        "positive."
    ),
    baseline_reason="the loop falls out of the bottom and returns None, swallowing the failure",
    edge_cases=(
        "a non-positive attempt count is refused",
        "the last failure is reraised",
    ),
    baseline="""def retry_call(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    for _ in range(attempts):
        try:
            return action()
        except Exception:
            continue
    return None""",
    variant_one="""def retry_call(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("the attempt count must be positive")
    last = None
    for _ in range(attempts):
        try:
            return action()
        except Exception as error:
            last = error
    raise last""",
    variant_two="""def retry_call(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("the attempt count must be positive")
    for remaining in range(attempts - 1, -1, -1):
        try:
            return action()
        except Exception:
            if remaining == 0:
                raise""",
    variant_three="""def retry_call(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    if attempts <= 0:
        raise ValueError("the attempt count must be positive")
    for _ in range(attempts):
        try:
            return action()
        except Exception:
            continue
    return None""",
    variant_four="""def retry_call(action, attempts):
    \"\"\"Call `action` until it succeeds, at most `attempts` times.\"\"\"
    last = None
    for _ in range(attempts):
        try:
            return action()
        except Exception as error:
            last = error
    raise last""",
    visible_test=_test_module(
        "retrying",
        "Published contract for retrying.",
        """
def test_returns_a_first_time_success() -> None:
    assert retry_call(lambda: 7, 3) == 7


def test_succeeds_on_the_second_attempt() -> None:
    calls = []

    def action():
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("not yet")
        return "ok"

    assert retry_call(action, 3) == "ok"
""",
        imports="from retrying import retry_call\n",
    ),
    hidden_test=_test_module(
        "retrying",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_returns_a_first_time_success() -> None:
    assert retry_call(lambda: 7, 3) == 7


def test_a_non_positive_attempt_count_is_refused() -> None:
    with pytest.raises(ValueError):
        retry_call(lambda: 7, 0)


def test_the_last_failure_is_reraised() -> None:
    def action():
        raise RuntimeError("always")

    with pytest.raises(RuntimeError, match="always"):
        retry_call(action, 2)
""",
        imports="from retrying import retry_call\n",
    ),
)

_D70 = D2TaskSpec(
    template_id="d2_errors.checked_divmod",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-divmod",
    module="checked_division",
    module_doc="Division that reports its own domain errors.",
    issue=(
        "checked_divmod() is documented to truncate towards zero, so the remainder carries the "
        "numerator's sign. Callers report the language's flooring behaviour instead, and a "
        "raw ZeroDivisionError rather than a domain error."
    ),
    expected=(
        "checked_divmod(numerator, denominator) truncates towards zero so the remainder takes "
        "the numerator's sign, and raises ValueError when the denominator is zero."
    ),
    baseline_reason="the built-in floors towards minus infinity and raises its own error",
    edge_cases=(
        "a zero denominator is refused",
        "the remainder follows the numerator",
    ),
    baseline="""def checked_divmod(numerator, denominator):
    \"\"\"Return (quotient, remainder), truncating towards zero.\"\"\"
    return divmod(numerator, denominator)""",
    variant_one="""def checked_divmod(numerator, denominator):
    \"\"\"Return (quotient, remainder), truncating towards zero.\"\"\"
    if denominator == 0:
        raise ValueError("the denominator must not be zero")
    quotient = abs(numerator) // abs(denominator)
    if (numerator < 0) != (denominator < 0):
        quotient = -quotient
    return quotient, numerator - quotient * denominator""",
    variant_two="""def checked_divmod(numerator, denominator):
    \"\"\"Return (quotient, remainder), truncating towards zero.\"\"\"
    from math import trunc

    if not denominator:
        raise ValueError("the denominator must not be zero")
    quotient = trunc(numerator / denominator)
    return quotient, numerator - quotient * denominator""",
    variant_three="""def checked_divmod(numerator, denominator):
    \"\"\"Return (quotient, remainder), truncating towards zero.\"\"\"
    if denominator == 0:
        raise ValueError("the denominator must not be zero")
    return divmod(numerator, denominator)""",
    variant_four="""def checked_divmod(numerator, denominator):
    \"\"\"Return (quotient, remainder), truncating towards zero.\"\"\"
    quotient = abs(numerator) // abs(denominator)
    if (numerator < 0) != (denominator < 0):
        quotient = -quotient
    return quotient, numerator - quotient * denominator""",
    visible_test=_test_module(
        "checked_division",
        "Published contract for checked division.",
        """
def test_divides_evenly() -> None:
    assert checked_divmod(8, 2) == (4, 0)


def test_reports_a_remainder() -> None:
    assert checked_divmod(7, 2) == (3, 1)
""",
        imports="from checked_division import checked_divmod\n",
    ),
    hidden_test=_test_module(
        "checked_division",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_divides_evenly() -> None:
    assert checked_divmod(8, 2) == (4, 0)


def test_a_zero_denominator_is_refused() -> None:
    with pytest.raises(ValueError):
        checked_divmod(7, 0)


def test_the_remainder_follows_the_numerator() -> None:
    assert checked_divmod(7, -2) == (-3, 1)
""",
        imports="from checked_division import checked_divmod\n",
    ),
)

_D71 = D2TaskSpec(
    template_id="d2_errors.assert_unique",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-uniqueness",
    module="uniqueness_check",
    module_doc="Refusing a list that repeats itself.",
    issue=(
        "assert_unique() is documented to name every repeated value in one error. Callers "
        "report one at a time, and a crash on lists whose items cannot be hashed."
    ),
    expected=(
        "assert_unique(items) returns the items when they are all distinct, names every "
        "repeated value in one error, and works on items that cannot be hashed."
    ),
    baseline_reason="the set demands hashability and the raise happens at the first repeat",
    edge_cases=(
        "every duplicate is named",
        "unhashable items are accepted",
    ),
    baseline="""def assert_unique(items):
    \"\"\"Return `items` if nothing in it repeats.\"\"\"
    seen = set()
    for item in items:
        if item in seen:
            raise ValueError(f"duplicate: {item}")
        seen.add(item)
    return list(items)""",
    variant_one="""def assert_unique(items):
    \"\"\"Return `items` if nothing in it repeats.\"\"\"
    ordered = list(items)
    duplicates = []
    for index, item in enumerate(ordered):
        if item in ordered[:index] and item not in duplicates:
            duplicates.append(item)
    if duplicates:
        raise ValueError("duplicates: " + ", ".join(str(item) for item in duplicates))
    return ordered""",
    variant_two="""def assert_unique(items):
    \"\"\"Return `items` if nothing in it repeats.\"\"\"
    from collections import Counter

    ordered = list(items)
    try:
        repeated = [item for item, count in Counter(ordered).items() if count > 1]
    except TypeError:
        repeated = []
        for item in ordered:
            if ordered.count(item) > 1 and item not in repeated:
                repeated.append(item)
    if repeated:
        raise ValueError("duplicates: " + ", ".join(str(item) for item in repeated))
    return ordered""",
    variant_three="""def assert_unique(items):
    \"\"\"Return `items` if nothing in it repeats.\"\"\"
    from collections import Counter

    ordered = list(items)
    repeated = [item for item, count in Counter(ordered).items() if count > 1]
    if repeated:
        raise ValueError("duplicates: " + ", ".join(str(item) for item in repeated))
    return ordered""",
    variant_four="""def assert_unique(items):
    \"\"\"Return `items` if nothing in it repeats.\"\"\"
    seen = []
    for item in items:
        if item in seen:
            raise ValueError(f"duplicate: {item}")
        seen.append(item)
    return list(items)""",
    visible_test=_test_module(
        "uniqueness_check",
        "Published contract for uniqueness.",
        """
import pytest


def test_accepts_unique_items() -> None:
    assert assert_unique([1, 2, 3]) == [1, 2, 3]


def test_names_a_duplicate() -> None:
    with pytest.raises(ValueError, match="2"):
        assert_unique([1, 2, 2])
""",
        imports="from uniqueness_check import assert_unique\n",
    ),
    hidden_test=_test_module(
        "uniqueness_check",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_accepts_unique_items() -> None:
    assert assert_unique([1, 2, 3]) == [1, 2, 3]


def test_every_duplicate_is_named() -> None:
    with pytest.raises(ValueError, match="1.*2"):
        assert_unique([1, 1, 2, 2])


def test_unhashable_items_are_accepted() -> None:
    assert assert_unique([[1], [2]]) == [[1], [2]]
""",
        imports="from uniqueness_check import assert_unique\n",
    ),
)

_D72 = D2TaskSpec(
    template_id="d2_errors.ensure_range",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-range-guard",
    module="range_guard",
    module_doc="Guarding a value against a declared range.",
    issue=(
        "ensure_range() is documented to treat the bounds as inclusive. Callers report values "
        "exactly on a bound being refused, and bounds passed the wrong way round going "
        "unremarked while every value fails."
    ),
    expected=(
        "ensure_range(value, low, high) accepts a value on either bound, and raises a "
        "ValueError about the bounds themselves when they are the wrong way round."
    ),
    baseline_reason="a strict comparison excludes the bounds and never questions their order",
    edge_cases=(
        "the bounds are inclusive",
        "reversed bounds are refused",
    ),
    baseline="""def ensure_range(value, low, high):
    \"\"\"Return `value` if it lies within `low` and `high`.\"\"\"
    if low < value < high:
        return value
    raise ValueError(f"{value} is out of range")""",
    variant_one="""def ensure_range(value, low, high):
    \"\"\"Return `value` if it lies within `low` and `high`.\"\"\"
    if low > high:
        raise ValueError("the bounds are the wrong way round")
    if low <= value <= high:
        return value
    raise ValueError(f"{value} is out of range")""",
    variant_two="""def ensure_range(value, low, high):
    \"\"\"Return `value` if it lies within `low` and `high`.\"\"\"
    if high < low:
        raise ValueError("the bounds are the wrong way round")
    if value < low or value > high:
        raise ValueError(f"{value} is out of range")
    return value""",
    variant_three="""def ensure_range(value, low, high):
    \"\"\"Return `value` if it lies within `low` and `high`.\"\"\"
    if low <= value <= high:
        return value
    raise ValueError(f"{value} is out of range")""",
    variant_four="""def ensure_range(value, low, high):
    \"\"\"Return `value` if it lies within `low` and `high`.\"\"\"
    if low > high:
        raise ValueError("the bounds are the wrong way round")
    if low < value < high:
        return value
    raise ValueError(f"{value} is out of range")""",
    visible_test=_test_module(
        "range_guard",
        "Published contract for range guarding.",
        """
import pytest


def test_accepts_a_value_inside_the_range() -> None:
    assert ensure_range(5, 1, 10) == 5


def test_refuses_a_value_above_the_range() -> None:
    with pytest.raises(ValueError):
        ensure_range(11, 1, 10)
""",
        imports="from range_guard import ensure_range\n",
    ),
    hidden_test=_test_module(
        "range_guard",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_accepts_a_value_inside_the_range() -> None:
    assert ensure_range(5, 1, 10) == 5


def test_the_bounds_are_inclusive() -> None:
    assert ensure_range(1, 1, 10) == 1


def test_reversed_bounds_are_refused() -> None:
    with pytest.raises(ValueError, match="wrong way round"):
        ensure_range(5, 10, 1)
""",
        imports="from range_guard import ensure_range\n",
    ),
)

_D73 = D2TaskSpec(
    template_id="d2_errors.wrap_error",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-wrapping",
    module="error_wrapping",
    module_doc="Translating errors at a module boundary.",
    issue=(
        "wrap_error() is documented to leave an error that is already of the right kind alone "
        "and to keep the original as the cause. Callers report identity being lost on "
        "re-wrapping, and tracebacks with nothing underneath them."
    ),
    expected=(
        "wrap_error(action, kind) lets an error already of `kind` propagate unchanged, and "
        "chains the original error as the cause of anything it does wrap."
    ),
    baseline_reason="every error is rebuilt, and the new one is raised without a cause",
    edge_cases=(
        "an error of the right kind passes through",
        "the original error is chained",
    ),
    baseline="""def wrap_error(action, kind):
    \"\"\"Run `action`, translating any failure into `kind`.\"\"\"
    try:
        return action()
    except Exception as error:
        raise kind(str(error))""",
    variant_one="""def wrap_error(action, kind):
    \"\"\"Run `action`, translating any failure into `kind`.\"\"\"
    try:
        return action()
    except kind:
        raise
    except Exception as error:
        raise kind(str(error)) from error""",
    variant_two="""def wrap_error(action, kind):
    \"\"\"Run `action`, translating any failure into `kind`.\"\"\"
    try:
        return action()
    except Exception as error:
        if isinstance(error, kind):
            raise
        raise kind(str(error)) from error""",
    variant_three="""def wrap_error(action, kind):
    \"\"\"Run `action`, translating any failure into `kind`.\"\"\"
    try:
        return action()
    except kind:
        raise
    except Exception as error:
        raise kind(str(error))""",
    variant_four="""def wrap_error(action, kind):
    \"\"\"Run `action`, translating any failure into `kind`.\"\"\"
    try:
        return action()
    except Exception as error:
        raise kind(str(error)) from error""",
    visible_test=_test_module(
        "error_wrapping",
        "Published contract for error translation.",
        """
import pytest


def test_returns_a_result() -> None:
    assert wrap_error(lambda: 7, ValueError) == 7


def test_wraps_a_foreign_error() -> None:
    def action():
        raise RuntimeError("bad")

    with pytest.raises(ValueError):
        wrap_error(action, ValueError)
""",
        imports="from error_wrapping import wrap_error\n",
    ),
    hidden_test=_test_module(
        "error_wrapping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_returns_a_result() -> None:
    assert wrap_error(lambda: 7, ValueError) == 7


def test_an_error_of_the_right_kind_passes_through() -> None:
    original = ValueError("mine")

    def action():
        raise original

    with pytest.raises(ValueError) as caught:
        wrap_error(action, ValueError)
    assert caught.value is original


def test_the_original_error_is_chained() -> None:
    def action():
        raise RuntimeError("bad")

    with pytest.raises(ValueError) as caught:
        wrap_error(action, ValueError)
    assert isinstance(caught.value.__cause__, RuntimeError)
""",
        imports="from error_wrapping import wrap_error\n",
    ),
)

_D74 = D2TaskSpec(
    template_id="d2_errors.collect_failures",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-collect",
    module="failure_collection",
    module_doc="Running a batch of actions and reporting what failed.",
    issue=(
        "collect_failures() is documented to run every action and to say which one failed. "
        "Callers report the batch stopping at the first failure, and failures arriving with "
        "no indication of where they came from."
    ),
    expected=(
        "collect_failures(actions) runs every action whatever happens, and reports each "
        "failure as a (position, error) pair."
    ),
    baseline_reason="the loop breaks on the first failure and records only the error object",
    edge_cases=(
        "a failure does not stop the rest",
        "a failure carries the position it came from",
    ),
    baseline="""def collect_failures(actions):
    \"\"\"Run every action, returning (results, failures).\"\"\"
    results = []
    failures = []
    for action in actions:
        try:
            results.append(action())
        except Exception as error:
            failures.append(error)
            break
    return results, failures""",
    variant_one="""def collect_failures(actions):
    \"\"\"Run every action, returning (results, failures).\"\"\"
    results = []
    failures = []
    for index, action in enumerate(actions):
        try:
            results.append(action())
        except Exception as error:
            failures.append((index, error))
    return results, failures""",
    variant_two="""def collect_failures(actions):
    \"\"\"Run every action, returning (results, failures).\"\"\"
    results = []
    failures = []
    index = 0
    for action in actions:
        try:
            outcome = action()
        except Exception as error:
            failures.append((index, error))
        else:
            results.append(outcome)
        index += 1
    return results, failures""",
    variant_three="""def collect_failures(actions):
    \"\"\"Run every action, returning (results, failures).\"\"\"
    results = []
    failures = []
    for action in actions:
        try:
            results.append(action())
        except Exception as error:
            failures.append(error)
    return results, failures""",
    variant_four="""def collect_failures(actions):
    \"\"\"Run every action, returning (results, failures).\"\"\"
    results = []
    failures = []
    for index, action in enumerate(actions):
        try:
            results.append(action())
        except Exception as error:
            failures.append((index, error))
            break
    return results, failures""",
    visible_test=_test_module(
        "failure_collection",
        "Published contract for batch running.",
        """
def test_collects_every_result() -> None:
    assert collect_failures([lambda: 1, lambda: 2])[0] == [1, 2]


def test_reports_no_failures_when_all_succeed() -> None:
    assert collect_failures([lambda: 1])[1] == []
""",
        imports="from failure_collection import collect_failures\n",
    ),
    hidden_test=_test_module(
        "failure_collection",
        "The part of the contract the published tests do not state.",
        """
def boom():
    raise RuntimeError("boom")


def test_collects_every_result() -> None:
    assert collect_failures([lambda: 1, lambda: 2])[0] == [1, 2]


def test_a_failure_does_not_stop_the_rest() -> None:
    assert collect_failures([boom, lambda: 2])[0] == [2]


def test_a_failure_carries_the_position_it_came_from() -> None:
    failures = collect_failures([lambda: 1, boom])[1]
    assert failures[0][0] == 1
""",
        imports="from failure_collection import collect_failures\n",
    ),
)

_D75 = D2TaskSpec(
    template_id="d2_errors.remaining_budget",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-budget",
    module="budgeting",
    module_doc="Reporting what is left of a time budget.",
    issue=(
        "remaining_budget() is documented never to report less than nothing. Callers report "
        "negative budgets being handed to sleep calls, and a total of zero being accepted."
    ),
    expected=(
        "remaining_budget(total, spent) never reports below zero, and raises ValueError when "
        "the total is not positive."
    ),
    baseline_reason="the subtraction is returned as it stands and the total is never checked",
    edge_cases=(
        "overspending reports zero",
        "a non-positive total is refused",
    ),
    baseline="""def remaining_budget(total, spent):
    \"\"\"Return what is left of `total` after `spent`.\"\"\"
    return total - spent""",
    variant_one="""def remaining_budget(total, spent):
    \"\"\"Return what is left of `total` after `spent`.\"\"\"
    if total <= 0:
        raise ValueError("the total budget must be positive")
    return max(total - spent, 0)""",
    variant_two="""def remaining_budget(total, spent):
    \"\"\"Return what is left of `total` after `spent`.\"\"\"
    if not total > 0:
        raise ValueError("the total budget must be positive")
    left = total - spent
    return left if left > 0 else 0""",
    variant_three="""def remaining_budget(total, spent):
    \"\"\"Return what is left of `total` after `spent`.\"\"\"
    return max(total - spent, 0)""",
    variant_four="""def remaining_budget(total, spent):
    \"\"\"Return what is left of `total` after `spent`.\"\"\"
    if total <= 0:
        raise ValueError("the total budget must be positive")
    return total - spent""",
    visible_test=_test_module(
        "budgeting",
        "Published contract for budget reporting.",
        """
def test_reports_what_is_left() -> None:
    assert remaining_budget(10, 3) == 7


def test_reports_a_spent_budget_as_zero() -> None:
    assert remaining_budget(10, 10) == 0
""",
        imports="from budgeting import remaining_budget\n",
    ),
    hidden_test=_test_module(
        "budgeting",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_reports_what_is_left() -> None:
    assert remaining_budget(10, 3) == 7


def test_overspending_reports_zero() -> None:
    assert remaining_budget(10, 15) == 0


def test_a_non_positive_total_is_refused() -> None:
    with pytest.raises(ValueError):
        remaining_budget(0, 1)
""",
        imports="from budgeting import remaining_budget\n",
    ),
)

_D76 = D2TaskSpec(
    template_id="d2_errors.guarded_int",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-guarded-int",
    module="guarded_conversion",
    module_doc="Reading a whole number from an untrusted setting.",
    issue=(
        "guarded_int() is documented to fall back to the caller's default for anything that is "
        "not a number. Callers report a crash on a setting that is absent, and booleans "
        "arriving as one and zero."
    ),
    expected=(
        "guarded_int(text, default) returns the default for None and for a boolean, and "
        "otherwise reads the value or falls back to the default."
    ),
    baseline_reason="only ValueError is caught, and a boolean is an integer as far as int() cares",
    edge_cases=(
        "none gives the default",
        "a boolean gives the default",
    ),
    baseline="""def guarded_int(text, default):
    \"\"\"Read `text` as a whole number, or return `default`.\"\"\"
    try:
        return int(text)
    except ValueError:
        return default""",
    variant_one="""def guarded_int(text, default):
    \"\"\"Read `text` as a whole number, or return `default`.\"\"\"
    if text is None or isinstance(text, bool):
        return default
    try:
        return int(text)
    except (TypeError, ValueError):
        return default""",
    variant_two="""def guarded_int(text, default):
    \"\"\"Read `text` as a whole number, or return `default`.\"\"\"
    if isinstance(text, bool) or not isinstance(text, (int, str, float)):
        return default
    try:
        return int(text)
    except ValueError:
        return default""",
    variant_three="""def guarded_int(text, default):
    \"\"\"Read `text` as a whole number, or return `default`.\"\"\"
    if text is None:
        return default
    try:
        return int(text)
    except ValueError:
        return default""",
    variant_four="""def guarded_int(text, default):
    \"\"\"Read `text` as a whole number, or return `default`.\"\"\"
    if isinstance(text, bool):
        return default
    try:
        return int(text)
    except ValueError:
        return default""",
    visible_test=_test_module(
        "guarded_conversion",
        "Published contract for guarded conversion.",
        """
def test_reads_a_number() -> None:
    assert guarded_int("42", 0) == 42


def test_falls_back_on_nonsense() -> None:
    assert guarded_int("abc", -1) == -1
""",
        imports="from guarded_conversion import guarded_int\n",
    ),
    hidden_test=_test_module(
        "guarded_conversion",
        "The part of the contract the published tests do not state.",
        """
def test_reads_a_number() -> None:
    assert guarded_int("42", 0) == 42


def test_none_gives_the_default() -> None:
    assert guarded_int(None, -1) == -1


def test_a_boolean_gives_the_default() -> None:
    assert guarded_int(True, -1) == -1
""",
        imports="from guarded_conversion import guarded_int\n",
    ),
)

_D77 = D2TaskSpec(
    template_id="d2_errors.validate_bounds",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-bounds-report",
    module="bounds_validation",
    module_doc="Reporting which readings fall outside a range.",
    issue=(
        "validate_bounds() is documented to report every offending position so an operator can "
        "see the whole picture. Callers report one position at a time, and readings sitting "
        "exactly on a bound being flagged."
    ),
    expected=(
        "validate_bounds(values, low, high) returns the positions of every reading outside the "
        "range, and treats the bounds as inclusive."
    ),
    baseline_reason=(
        "the first offender returns immediately, and the comparison excludes the bounds"
    ),
    edge_cases=(
        "every offending index is reported",
        "a value on a bound is in range",
    ),
    baseline="""def validate_bounds(values, low, high):
    \"\"\"Return the positions of readings outside `low` to `high`.\"\"\"
    for index, value in enumerate(values):
        if not low < value < high:
            return [index]
    return []""",
    variant_one="""def validate_bounds(values, low, high):
    \"\"\"Return the positions of readings outside `low` to `high`.\"\"\"
    return [index for index, value in enumerate(values) if not low <= value <= high]""",
    variant_two="""def validate_bounds(values, low, high):
    \"\"\"Return the positions of readings outside `low` to `high`.\"\"\"
    offending = []
    for index, value in enumerate(values):
        if value < low or value > high:
            offending.append(index)
    return offending""",
    variant_three="""def validate_bounds(values, low, high):
    \"\"\"Return the positions of readings outside `low` to `high`.\"\"\"
    return [index for index, value in enumerate(values) if not low < value < high]""",
    variant_four="""def validate_bounds(values, low, high):
    \"\"\"Return the positions of readings outside `low` to `high`.\"\"\"
    for index, value in enumerate(values):
        if not low <= value <= high:
            return [index]
    return []""",
    visible_test=_test_module(
        "bounds_validation",
        "Published contract for bounds reporting.",
        """
def test_reports_nothing_for_values_in_range() -> None:
    assert validate_bounds([2, 3], 1, 10) == []


def test_reports_a_value_above_the_range() -> None:
    assert validate_bounds([2, 99], 1, 10) == [1]
""",
        imports="from bounds_validation import validate_bounds\n",
    ),
    hidden_test=_test_module(
        "bounds_validation",
        "The part of the contract the published tests do not state.",
        """
def test_reports_nothing_for_values_in_range() -> None:
    assert validate_bounds([2, 3], 1, 10) == []


def test_every_offending_index_is_reported() -> None:
    assert validate_bounds([99, 3, -5], 1, 10) == [0, 2]


def test_a_value_on_a_bound_is_in_range() -> None:
    assert validate_bounds([1, 10], 1, 10) == []
""",
        imports="from bounds_validation import validate_bounds\n",
    ),
)

_D78 = D2TaskSpec(
    template_id="d2_errors.exit_code_for",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-exit-codes",
    module="exit_codes",
    module_doc="Choosing a process exit code for a failure.",
    issue=(
        "exit_code_for() is documented to answer for any error at all. Callers report a crash "
        "on kinds it does not know, and their own error subclasses missing their base's code."
    ),
    expected=(
        "exit_code_for(error) returns the code for the closest declared kind, returns a "
        "generic code for anything undeclared, and matches subclasses of a declared kind."
    ),
    baseline_reason="the exact type is looked up, so subclasses and unknowns both miss",
    edge_cases=(
        "an unknown error maps to a generic code",
        "a subclass maps to its base",
    ),
    baseline="""def exit_code_for(error):
    \"\"\"Return the process exit code for `error`.\"\"\"
    codes = {ValueError: 2, KeyError: 3, TimeoutError: 4}
    return codes[type(error)]""",
    variant_one="""def exit_code_for(error):
    \"\"\"Return the process exit code for `error`.\"\"\"
    codes = {ValueError: 2, KeyError: 3, TimeoutError: 4}
    for kind, code in codes.items():
        if isinstance(error, kind):
            return code
    return 1""",
    variant_two="""def exit_code_for(error):
    \"\"\"Return the process exit code for `error`.\"\"\"
    codes = ((ValueError, 2), (KeyError, 3), (TimeoutError, 4))
    matched = [code for kind, code in codes if isinstance(error, kind)]
    return matched[0] if matched else 1""",
    variant_three="""def exit_code_for(error):
    \"\"\"Return the process exit code for `error`.\"\"\"
    codes = {ValueError: 2, KeyError: 3, TimeoutError: 4}
    return codes.get(type(error), 1)""",
    variant_four="""def exit_code_for(error):
    \"\"\"Return the process exit code for `error`.\"\"\"
    codes = {ValueError: 2, KeyError: 3, TimeoutError: 4}
    for kind, code in codes.items():
        if isinstance(error, kind):
            return code
    raise KeyError(type(error))""",
    visible_test=_test_module(
        "exit_codes",
        "Published contract for exit codes.",
        """
def test_maps_a_value_error() -> None:
    assert exit_code_for(ValueError("x")) == 2


def test_maps_a_timeout() -> None:
    assert exit_code_for(TimeoutError("x")) == 4
""",
        imports="from exit_codes import exit_code_for\n",
    ),
    hidden_test=_test_module(
        "exit_codes",
        "The part of the contract the published tests do not state.",
        """
class NarrowValueError(ValueError):
    pass


def test_maps_a_value_error() -> None:
    assert exit_code_for(ValueError("x")) == 2


def test_an_unknown_error_maps_to_a_generic_code() -> None:
    assert exit_code_for(RuntimeError("x")) == 1


def test_a_subclass_maps_to_its_base() -> None:
    assert exit_code_for(NarrowValueError("x")) == 2
""",
        imports="from exit_codes import exit_code_for\n",
    ),
)

_D79 = D2TaskSpec(
    template_id="d2_errors.pluck_present",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-pluck",
    module="present_plucking",
    module_doc="Reading the settings a caller asked for, skipping the absent ones.",
    issue=(
        "pluck_present() is documented to answer in the order the caller asked. Callers report "
        "the mapping's own order coming back, and settings explicitly set to None vanishing."
    ),
    expected=(
        "pluck_present(mapping, keys) returns the values for the keys that are present, in the "
        "order the keys were asked for, counting a key set to None as present."
    ),
    baseline_reason="iterating the mapping fixes the order, and the None filter drops real values",
    edge_cases=(
        "a key present but none is included",
        "the order follows the requested keys",
    ),
    baseline="""def pluck_present(mapping, keys):
    \"\"\"Return the values in `mapping` for the keys that are present.\"\"\"
    return [value for key, value in mapping.items() if key in keys and value is not None]""",
    variant_one="""def pluck_present(mapping, keys):
    \"\"\"Return the values in `mapping` for the keys that are present.\"\"\"
    return [mapping[key] for key in keys if key in mapping]""",
    variant_two="""def pluck_present(mapping, keys):
    \"\"\"Return the values in `mapping` for the keys that are present.\"\"\"
    absent = object()
    found = ((key, mapping.get(key, absent)) for key in keys)
    return [value for _, value in found if value is not absent]""",
    variant_three="""def pluck_present(mapping, keys):
    \"\"\"Return the values in `mapping` for the keys that are present.\"\"\"
    return [value for key, value in mapping.items() if key in keys]""",
    variant_four="""def pluck_present(mapping, keys):
    \"\"\"Return the values in `mapping` for the keys that are present.\"\"\"
    return [mapping[key] for key in keys if key in mapping and mapping[key] is not None]""",
    visible_test=_test_module(
        "present_plucking",
        "Published contract for plucking present settings.",
        """
def test_plucks_present_keys() -> None:
    assert pluck_present({"a": 1, "b": 2}, ["a", "b"]) == [1, 2]


def test_skips_a_missing_key() -> None:
    assert pluck_present({"a": 1}, ["a", "z"]) == [1]
""",
        imports="from present_plucking import pluck_present\n",
    ),
    hidden_test=_test_module(
        "present_plucking",
        "The part of the contract the published tests do not state.",
        """
def test_plucks_present_keys() -> None:
    assert pluck_present({"a": 1, "b": 2}, ["a", "b"]) == [1, 2]


def test_a_key_present_but_none_is_included() -> None:
    assert pluck_present({"a": None}, ["a"]) == [None]


def test_the_order_follows_the_requested_keys() -> None:
    assert pluck_present({"a": 1, "b": 2}, ["b", "a"]) == [2, 1]
""",
        imports="from present_plucking import pluck_present\n",
    ),
)

_D80 = D2TaskSpec(
    template_id="d2_errors.as_type",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-type-check",
    module="type_checking",
    module_doc="Coercing a value at an interface boundary.",
    issue=(
        "as_type() is documented to leave a value that is already the right type alone, and to "
        "say what it could not read. Callers report copies being made of values they passed "
        "in, and errors from deep inside a constructor."
    ),
    expected=(
        "as_type(value, kind) returns a value that is already of `kind` unchanged, and raises "
        "a TypeError naming both the type it was given and the type it wanted."
    ),
    baseline_reason="the constructor is called unconditionally and its own error is left to escape",
    edge_cases=(
        "a value already of the type is returned unchanged",
        "the error names both types",
    ),
    baseline="""def as_type(value, kind):
    \"\"\"Return `value` as `kind`.\"\"\"
    return kind(value)""",
    variant_one="""def as_type(value, kind):
    \"\"\"Return `value` as `kind`.\"\"\"
    if isinstance(value, kind):
        return value
    try:
        return kind(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"cannot read {type(value).__name__} as {kind.__name__}") from error""",
    variant_two="""def as_type(value, kind):
    \"\"\"Return `value` as `kind`.\"\"\"
    if type(value) is kind:
        return value
    try:
        converted = kind(value)
    except Exception as error:
        raise TypeError(f"cannot read {type(value).__name__} as {kind.__name__}") from error
    return converted""",
    variant_three="""def as_type(value, kind):
    \"\"\"Return `value` as `kind`.\"\"\"
    if isinstance(value, kind):
        return value
    return kind(value)""",
    variant_four="""def as_type(value, kind):
    \"\"\"Return `value` as `kind`.\"\"\"
    try:
        return kind(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"cannot read {type(value).__name__} as {kind.__name__}") from error""",
    visible_test=_test_module(
        "type_checking",
        "Published contract for boundary coercion.",
        """
def test_converts_a_string_to_an_int() -> None:
    assert as_type("42", int) == 42


def test_converts_a_tuple_to_a_list() -> None:
    assert as_type((1, 2), list) == [1, 2]
""",
        imports="from type_checking import as_type\n",
    ),
    hidden_test=_test_module(
        "type_checking",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_converts_a_string_to_an_int() -> None:
    assert as_type("42", int) == 42


def test_a_value_already_of_the_type_is_returned_unchanged() -> None:
    items = [1, 2]
    assert as_type(items, list) is items


def test_the_error_names_both_types() -> None:
    with pytest.raises(TypeError, match="str as int"):
        as_type("abc", int)
""",
        imports="from type_checking import as_type\n",
    ),
)

_D81 = D2TaskSpec(
    template_id="d2_errors.should_abort",
    family=RealityTaskFamily.ERROR_HANDLING,
    repository_group="d2-errors-abort",
    module="abort_policy",
    module_doc="Deciding when a run has failed often enough to stop.",
    issue=(
        "should_abort() is documented to abort once the threshold is reached. Callers report "
        "having to exceed it, and a window of zero looking at the whole history."
    ),
    expected=(
        "should_abort(failures, window, threshold) counts the failures in the last `window` "
        "results, aborts as soon as the threshold is reached, and looks at nothing when the "
        "window is zero."
    ),
    baseline_reason="a strict comparison needs one more failure, and a zero slice bound is the lot",
    edge_cases=(
        "reaching the threshold is enough",
        "a window of zero looks at nothing",
    ),
    baseline="""def should_abort(failures, window, threshold):
    \"\"\"Report whether the last `window` results warrant aborting.\"\"\"
    recent = failures[-window:]
    return sum(recent) > threshold""",
    variant_one="""def should_abort(failures, window, threshold):
    \"\"\"Report whether the last `window` results warrant aborting.\"\"\"
    recent = list(failures)[-window:] if window > 0 else []
    return sum(recent) >= threshold""",
    variant_two="""def should_abort(failures, window, threshold):
    \"\"\"Report whether the last `window` results warrant aborting.\"\"\"
    from collections import deque

    recent = deque(failures, maxlen=window) if window > 0 else ()
    return sum(recent) >= threshold""",
    variant_three="""def should_abort(failures, window, threshold):
    \"\"\"Report whether the last `window` results warrant aborting.\"\"\"
    recent = failures[-window:]
    return sum(recent) >= threshold""",
    variant_four="""def should_abort(failures, window, threshold):
    \"\"\"Report whether the last `window` results warrant aborting.\"\"\"
    recent = list(failures)[-window:] if window > 0 else []
    return sum(recent) > threshold""",
    visible_test=_test_module(
        "abort_policy",
        "Published contract for the abort policy.",
        """
def test_aborts_when_failures_pass_the_threshold() -> None:
    assert should_abort([1, 1, 1], 3, 2) is True


def test_does_not_abort_below_the_threshold() -> None:
    assert should_abort([0, 0, 1], 3, 2) is False
""",
        imports="from abort_policy import should_abort\n",
    ),
    hidden_test=_test_module(
        "abort_policy",
        "The part of the contract the published tests do not state.",
        """
def test_aborts_when_failures_pass_the_threshold() -> None:
    assert should_abort([1, 1, 1], 3, 2) is True


def test_reaching_the_threshold_is_enough() -> None:
    assert should_abort([0, 1, 1], 3, 2) is True


def test_a_window_of_zero_looks_at_nothing() -> None:
    assert should_abort([1, 1, 1], 0, 1) is False
""",
        imports="from abort_policy import should_abort\n",
    ),
)

# ------------------------------------------------------------- data transformation, S21D2-022

_D82 = D2TaskSpec(
    template_id="d2_transform.pluck",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-pluck",
    module="field_plucking",
    module_doc="Reading one field out of a list of records.",
    issue=(
        "pluck() is documented to return one value per record. Callers report short lists when "
        "some records lack the field, and unhelpful crashes when one entry is not a record."
    ),
    expected=(
        "pluck(records, field, default) returns one value per record, substituting the default "
        "where the field is absent, and raises a TypeError naming the position of any entry "
        "that is not a mapping."
    ),
    baseline_reason="records without the field are filtered out rather than defaulted",
    edge_cases=(
        "a record missing the field gives the default",
        "a record that is not a mapping names its position",
    ),
    baseline="""def pluck(records, field, default):
    \"\"\"Return the `field` of every record, or `default`.\"\"\"
    return [record[field] for record in records if field in record]""",
    variant_one="""def pluck(records, field, default):
    \"\"\"Return the `field` of every record, or `default`.\"\"\"
    values = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"record {index} is not a mapping")
        values.append(record.get(field, default))
    return values""",
    variant_two="""def pluck(records, field, default):
    \"\"\"Return the `field` of every record, or `default`.\"\"\"
    for index, record in enumerate(records):
        if not hasattr(record, "get"):
            raise TypeError(f"record {index} is not a mapping")
    return [record.get(field, default) for record in records]""",
    variant_three="""def pluck(records, field, default):
    \"\"\"Return the `field` of every record, or `default`.\"\"\"
    return [record.get(field, default) for record in records]""",
    variant_four="""def pluck(records, field, default):
    \"\"\"Return the `field` of every record, or `default`.\"\"\"
    values = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(f"record {index} is not a mapping")
        if field in record:
            values.append(record[field])
    return values""",
    visible_test=_test_module(
        "field_plucking",
        "Published contract for field plucking.",
        """
def test_plucks_a_field() -> None:
    assert pluck([{"a": 1}, {"a": 2}], "a", 0) == [1, 2]


def test_plucks_from_one_record() -> None:
    assert pluck([{"a": 9}], "a", 0) == [9]
""",
        imports="from field_plucking import pluck\n",
    ),
    hidden_test=_test_module(
        "field_plucking",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_plucks_a_field() -> None:
    assert pluck([{"a": 1}, {"a": 2}], "a", 0) == [1, 2]


def test_a_record_missing_the_field_gives_the_default() -> None:
    assert pluck([{"a": 1}, {}], "a", 0) == [1, 0]


def test_a_record_that_is_not_a_mapping_names_its_position() -> None:
    with pytest.raises(TypeError, match="record 1"):
        pluck([{"a": 1}, 5], "a", 0)
""",
        imports="from field_plucking import pluck\n",
    ),
)

_D83 = D2TaskSpec(
    template_id="d2_transform.index_by",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-index",
    module="record_indexing",
    module_doc="Building a lookup table from a list of records.",
    issue=(
        "index_by() is documented to keep the first record for a repeated key, so replays do "
        "not overwrite the original. Callers report the later one winning, and a crash on "
        "records that do not carry the key at all."
    ),
    expected=(
        "index_by(records, key) keeps the first record for each key value, and skips a record "
        "that does not carry the key rather than raising."
    ),
    baseline_reason="a comprehension writes every record, so the last one written wins",
    edge_cases=(
        "the first record wins a duplicate key",
        "a record missing the key is skipped",
    ),
    baseline="""def index_by(records, key):
    \"\"\"Index `records` by the value of `key`.\"\"\"
    return {record[key]: record for record in records}""",
    variant_one="""def index_by(records, key):
    \"\"\"Index `records` by the value of `key`.\"\"\"
    indexed = {}
    for record in records:
        if key not in record:
            continue
        indexed.setdefault(record[key], record)
    return indexed""",
    variant_two="""def index_by(records, key):
    \"\"\"Index `records` by the value of `key`.\"\"\"
    backwards = {}
    for record in reversed(list(records)):
        if key in record:
            backwards[record[key]] = record
    return dict(reversed(list(backwards.items())))""",
    variant_three="""def index_by(records, key):
    \"\"\"Index `records` by the value of `key`.\"\"\"
    indexed = {}
    for record in records:
        indexed.setdefault(record[key], record)
    return indexed""",
    variant_four="""def index_by(records, key):
    \"\"\"Index `records` by the value of `key`.\"\"\"
    return {record[key]: record for record in records if key in record}""",
    visible_test=_test_module(
        "record_indexing",
        "Published contract for record indexing.",
        """
def test_indexes_by_a_field() -> None:
    assert index_by([{"id": 1}, {"id": 2}], "id") == {1: {"id": 1}, 2: {"id": 2}}


def test_indexes_one_record() -> None:
    assert index_by([{"id": 7}], "id") == {7: {"id": 7}}
""",
        imports="from record_indexing import index_by\n",
    ),
    hidden_test=_test_module(
        "record_indexing",
        "The part of the contract the published tests do not state.",
        """
def test_indexes_by_a_field() -> None:
    assert index_by([{"id": 1}, {"id": 2}], "id") == {1: {"id": 1}, 2: {"id": 2}}


def test_the_first_record_wins_a_duplicate_key() -> None:
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}]
    assert index_by(records, "id")[1]["v"] == "a"


def test_a_record_missing_the_key_is_skipped() -> None:
    assert index_by([{"id": 1}, {"other": 2}], "id") == {1: {"id": 1}}
""",
        imports="from record_indexing import index_by\n",
    ),
)

_D84 = D2TaskSpec(
    template_id="d2_transform.transpose",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-transpose",
    module="row_transposition",
    module_doc="Turning rows into columns.",
    issue=(
        "transpose() is documented to refuse a grid whose rows are not all the same width, and "
        "to cope with no rows at all. Callers report crashes on both."
    ),
    expected=(
        "transpose(rows) swaps rows and columns, raises ValueError when the rows are not all "
        "the same width, and returns nothing for no rows."
    ),
    baseline_reason="the width is read off the first row, which need not exist or be typical",
    edge_cases=(
        "ragged rows are refused",
        "no rows transpose to nothing",
    ),
    baseline="""def transpose(rows):
    \"\"\"Turn the rows of `rows` into columns.\"\"\"
    width = len(rows[0])
    return [[row[index] for row in rows] for index in range(width)]""",
    variant_one="""def transpose(rows):
    \"\"\"Turn the rows of `rows` into columns.\"\"\"
    if not rows:
        return []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("the rows are not all the same width")
    return [[row[index] for row in rows] for index in range(width)]""",
    variant_two="""def transpose(rows):
    \"\"\"Turn the rows of `rows` into columns.\"\"\"
    ordered = list(rows)
    if len({len(row) for row in ordered}) > 1:
        raise ValueError("the rows are not all the same width")
    return [list(column) for column in zip(*ordered)]""",
    variant_three="""def transpose(rows):
    \"\"\"Turn the rows of `rows` into columns.\"\"\"
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("the rows are not all the same width")
    return [[row[index] for row in rows] for index in range(width)]""",
    variant_four="""def transpose(rows):
    \"\"\"Turn the rows of `rows` into columns.\"\"\"
    if not rows:
        return []
    width = len(rows[0])
    return [[row[index] for row in rows] for index in range(width)]""",
    visible_test=_test_module(
        "row_transposition",
        "Published contract for transposition.",
        """
def test_transposes_a_grid() -> None:
    assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]


def test_transposes_a_single_row() -> None:
    assert transpose([[1, 2]]) == [[1], [2]]
""",
        imports="from row_transposition import transpose\n",
    ),
    hidden_test=_test_module(
        "row_transposition",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_transposes_a_grid() -> None:
    assert transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]


def test_ragged_rows_are_refused() -> None:
    with pytest.raises(ValueError):
        transpose([[1, 2], [3]])


def test_no_rows_transpose_to_nothing() -> None:
    assert transpose([]) == []
""",
        imports="from row_transposition import transpose\n",
    ),
)

_D85 = D2TaskSpec(
    template_id="d2_transform.rank_records",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-ranking",
    module="record_ranking",
    module_doc="Attaching competition ranks to a table of records.",
    issue=(
        "rank_records() is documented to attach a rank to each record without reordering the "
        "table, and to give tied records the same rank. Callers report their table coming "
        "back sorted, and tied records being separated by an arbitrary place."
    ),
    expected=(
        "rank_records(records, field) attaches a rank counting down from the largest value, "
        "gives records that tie the same rank with the next rank skipping accordingly, and "
        "returns the records in the order it was given them."
    ),
    baseline_reason="the sorted order is returned as the answer and the place is the rank",
    edge_cases=(
        "a tie shares a rank and the next one skips",
        "the original record order is kept",
    ),
    baseline="""def rank_records(records, field):
    \"\"\"Attach a competition rank on `field` to every record.\"\"\"
    ordered = sorted(records, key=lambda record: record[field], reverse=True)
    return [{**record, "rank": index + 1} for index, record in enumerate(ordered)]""",
    variant_one="""def rank_records(records, field):
    \"\"\"Attach a competition rank on `field` to every record.\"\"\"
    scores = sorted({record[field] for record in records}, reverse=True)
    ranks = {}
    position = 1
    for score in scores:
        ranks[score] = position
        position += sum(1 for record in records if record[field] == score)
    return [{**record, "rank": ranks[record[field]]} for record in records]""",
    variant_two="""def rank_records(records, field):
    \"\"\"Attach a competition rank on `field` to every record.\"\"\"
    values = [record[field] for record in records]
    ranked = []
    for record in records:
        better = sum(1 for value in values if value > record[field])
        ranked.append({**record, "rank": better + 1})
    return ranked""",
    variant_three="""def rank_records(records, field):
    \"\"\"Attach a competition rank on `field` to every record.\"\"\"
    ordered = sorted(records, key=lambda record: record[field], reverse=True)
    ranked = []
    for record in ordered:
        better = sum(1 for other in ordered if other[field] > record[field])
        ranked.append({**record, "rank": better + 1})
    return ranked""",
    variant_four="""def rank_records(records, field):
    \"\"\"Attach a competition rank on `field` to every record.\"\"\"
    ordered = sorted(records, key=lambda record: record[field], reverse=True)
    places = {id(record): index + 1 for index, record in enumerate(ordered)}
    return [{**record, "rank": places[id(record)]} for record in records]""",
    visible_test=_test_module(
        "record_ranking",
        "Published contract for ranking records.",
        """
def test_ranks_by_a_field() -> None:
    records = [{"n": "a", "v": 10}, {"n": "b", "v": 5}]
    assert [record["rank"] for record in rank_records(records, "v")] == [1, 2]


def test_keeps_the_other_fields() -> None:
    assert rank_records([{"n": "a", "v": 10}], "v")[0]["n"] == "a"
""",
        imports="from record_ranking import rank_records\n",
    ),
    hidden_test=_test_module(
        "record_ranking",
        "The part of the contract the published tests do not state.",
        """
def test_ranks_by_a_field() -> None:
    records = [{"n": "a", "v": 10}, {"n": "b", "v": 5}]
    assert [record["rank"] for record in rank_records(records, "v")] == [1, 2]


def test_a_tie_shares_a_rank_and_the_next_one_skips() -> None:
    records = [
        {"n": "a", "v": 10},
        {"n": "b", "v": 5},
        {"n": "c", "v": 5},
        {"n": "d", "v": 1},
    ]
    assert [record["rank"] for record in rank_records(records, "v")] == [1, 2, 2, 4]


def test_the_original_record_order_is_kept() -> None:
    records = [{"n": "a", "v": 5}, {"n": "b", "v": 10}]
    assert [record["n"] for record in rank_records(records, "v")] == ["a", "b"]
""",
        imports="from record_ranking import rank_records\n",
    ),
)

_D86 = D2TaskSpec(
    template_id="d2_transform.chunk_mapping",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-chunk-mapping",
    module="mapping_chunking",
    module_doc="Splitting a mapping into batches.",
    issue=(
        "chunk_mapping() is documented to return every entry across its batches. Callers "
        "report the last few entries going missing, and an unhelpful error on a size of zero."
    ),
    expected=(
        "chunk_mapping(mapping, size) returns batches of at most `size` entries covering all "
        "of them, and raises a ValueError about the size when it is not positive."
    ),
    baseline_reason="the range stops a full batch short, so a partial final batch is never taken",
    edge_cases=(
        "the final partial chunk is kept",
        "a non-positive size is refused",
    ),
    baseline="""def chunk_mapping(mapping, size):
    \"\"\"Split `mapping` into batches of `size` entries.\"\"\"
    items = list(mapping.items())
    return [
        dict(items[start : start + size]) for start in range(0, len(items) - size + 1, size)
    ]""",
    variant_one="""def chunk_mapping(mapping, size):
    \"\"\"Split `mapping` into batches of `size` entries.\"\"\"
    if size <= 0:
        raise ValueError("the chunk size must be positive")
    items = list(mapping.items())
    return [dict(items[start : start + size]) for start in range(0, len(items), size)]""",
    variant_two="""def chunk_mapping(mapping, size):
    \"\"\"Split `mapping` into batches of `size` entries.\"\"\"
    if size <= 0:
        raise ValueError("the chunk size must be positive")
    chunks = []
    current = {}
    for key, value in mapping.items():
        current[key] = value
        if len(current) == size:
            chunks.append(current)
            current = {}
    if current:
        chunks.append(current)
    return chunks""",
    variant_three="""def chunk_mapping(mapping, size):
    \"\"\"Split `mapping` into batches of `size` entries.\"\"\"
    if size <= 0:
        raise ValueError("the chunk size must be positive")
    items = list(mapping.items())
    return [
        dict(items[start : start + size]) for start in range(0, len(items) - size + 1, size)
    ]""",
    variant_four="""def chunk_mapping(mapping, size):
    \"\"\"Split `mapping` into batches of `size` entries.\"\"\"
    items = list(mapping.items())
    return [dict(items[start : start + size]) for start in range(0, len(items), size)]""",
    visible_test=_test_module(
        "mapping_chunking",
        "Published contract for mapping batches.",
        """
def test_chunks_evenly() -> None:
    assert chunk_mapping({"a": 1, "b": 2, "c": 3, "d": 4}, 2) == [
        {"a": 1, "b": 2},
        {"c": 3, "d": 4},
    ]


def test_a_chunk_of_one() -> None:
    assert chunk_mapping({"a": 1}, 1) == [{"a": 1}]
""",
        imports="from mapping_chunking import chunk_mapping\n",
    ),
    hidden_test=_test_module(
        "mapping_chunking",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_chunks_evenly() -> None:
    assert chunk_mapping({"a": 1, "b": 2, "c": 3, "d": 4}, 2) == [
        {"a": 1, "b": 2},
        {"c": 3, "d": 4},
    ]


def test_the_final_partial_chunk_is_kept() -> None:
    assert len(chunk_mapping({"a": 1, "b": 2, "c": 3}, 2)) == 2


def test_a_non_positive_size_is_refused() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        chunk_mapping({"a": 1}, 0)
""",
        imports="from mapping_chunking import chunk_mapping\n",
    ),
)

_D87 = D2TaskSpec(
    template_id="d2_transform.flatten_mapping",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-flatten-mapping",
    module="mapping_flattening",
    module_doc="Flattening nested settings into dotted keys.",
    issue=(
        "flatten_mapping() is documented to flatten however deep the nesting goes, and to "
        "refuse a key that already holds the separator because the result would be ambiguous. "
        "Callers report dictionaries surviving two levels down and ambiguous keys going "
        "through."
    ),
    expected=(
        "flatten_mapping(nested, separator) flattens all the way down, and raises ValueError "
        "for any key that already contains the separator."
    ),
    baseline_reason="the inner loop reads one level and never recurses, and no key is checked",
    edge_cases=(
        "nesting is flattened all the way down",
        "a key already holding the separator is refused",
    ),
    baseline="""def flatten_mapping(nested, separator):
    \"\"\"Flatten `nested` into keys joined by `separator`.\"\"\"
    flat = {}
    for key, value in nested.items():
        if isinstance(value, dict):
            for inner, leaf in value.items():
                flat[f"{key}{separator}{inner}"] = leaf
        else:
            flat[key] = value
    return flat""",
    variant_one="""def flatten_mapping(nested, separator):
    \"\"\"Flatten `nested` into keys joined by `separator`.\"\"\"
    flat = {}
    for key, value in nested.items():
        if separator in str(key):
            raise ValueError(f"{key!r} already contains the separator")
        if isinstance(value, dict):
            for inner, leaf in flatten_mapping(value, separator).items():
                flat[f"{key}{separator}{inner}"] = leaf
        else:
            flat[key] = value
    return flat""",
    variant_two="""def flatten_mapping(nested, separator):
    \"\"\"Flatten `nested` into keys joined by `separator`.\"\"\"
    flat = {}
    pending = [((), nested)]
    while pending:
        prefix, current = pending.pop()
        for key, value in current.items():
            if separator in str(key):
                raise ValueError(f"{key!r} already contains the separator")
            path = (*prefix, str(key))
            if isinstance(value, dict):
                pending.append((path, value))
            else:
                flat[separator.join(path)] = value
    return flat""",
    variant_three="""def flatten_mapping(nested, separator):
    \"\"\"Flatten `nested` into keys joined by `separator`.\"\"\"
    flat = {}
    for key, value in nested.items():
        if isinstance(value, dict):
            for inner, leaf in flatten_mapping(value, separator).items():
                flat[f"{key}{separator}{inner}"] = leaf
        else:
            flat[key] = value
    return flat""",
    variant_four="""def flatten_mapping(nested, separator):
    \"\"\"Flatten `nested` into keys joined by `separator`.\"\"\"
    flat = {}
    for key, value in nested.items():
        if separator in str(key):
            raise ValueError(f"{key!r} already contains the separator")
        if isinstance(value, dict):
            for inner, leaf in value.items():
                flat[f"{key}{separator}{inner}"] = leaf
        else:
            flat[key] = value
    return flat""",
    visible_test=_test_module(
        "mapping_flattening",
        "Published contract for flattening settings.",
        """
def test_flattens_one_level() -> None:
    assert flatten_mapping({"a": {"b": 1}}, ".") == {"a.b": 1}


def test_keeps_a_top_level_leaf() -> None:
    assert flatten_mapping({"a": 1}, ".") == {"a": 1}
""",
        imports="from mapping_flattening import flatten_mapping\n",
    ),
    hidden_test=_test_module(
        "mapping_flattening",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_flattens_one_level() -> None:
    assert flatten_mapping({"a": {"b": 1}}, ".") == {"a.b": 1}


def test_nesting_is_flattened_all_the_way_down() -> None:
    assert flatten_mapping({"a": {"b": {"c": 1}}}, ".") == {"a.b.c": 1}


def test_a_key_already_holding_the_separator_is_refused() -> None:
    with pytest.raises(ValueError):
        flatten_mapping({"a.b": 1}, ".")
""",
        imports="from mapping_flattening import flatten_mapping\n",
    ),
)

_D88 = D2TaskSpec(
    template_id="d2_transform.zip_to_records",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-zip-records",
    module="record_zipping",
    module_doc="Turning a header row and data rows into records.",
    issue=(
        "zip_to_records() is documented to refuse a malformed sheet rather than quietly "
        "losing data. Callers report rows of the wrong width being truncated, and repeated "
        "headers silently collapsing two columns into one."
    ),
    expected=(
        "zip_to_records(headers, rows) raises a ValueError naming the position of any row "
        "whose width does not match the headers, and refuses repeated headers."
    ),
    baseline_reason="zip stops at the shorter side, and a repeated key overwrites the earlier one",
    edge_cases=(
        "a row of the wrong width names its position",
        "repeated headers are refused",
    ),
    baseline="""def zip_to_records(headers, rows):
    \"\"\"Build one record per row, keyed by `headers`.\"\"\"
    return [dict(zip(headers, row)) for row in rows]""",
    variant_one="""def zip_to_records(headers, rows):
    \"\"\"Build one record per row, keyed by `headers`.\"\"\"
    if len(set(headers)) != len(headers):
        raise ValueError("the headers repeat")
    records = []
    for index, row in enumerate(rows):
        if len(row) != len(headers):
            raise ValueError(f"row {index} has the wrong width")
        records.append(dict(zip(headers, row)))
    return records""",
    variant_two="""def zip_to_records(headers, rows):
    \"\"\"Build one record per row, keyed by `headers`.\"\"\"
    names = list(headers)
    if len(set(names)) < len(names):
        raise ValueError("the headers repeat")
    records = []
    for index, row in enumerate(rows):
        try:
            records.append(dict(zip(names, row, strict=True)))
        except ValueError as error:
            raise ValueError(f"row {index} has the wrong width") from error
    return records""",
    variant_three="""def zip_to_records(headers, rows):
    \"\"\"Build one record per row, keyed by `headers`.\"\"\"
    records = []
    for index, row in enumerate(rows):
        if len(row) != len(headers):
            raise ValueError(f"row {index} has the wrong width")
        records.append(dict(zip(headers, row)))
    return records""",
    variant_four="""def zip_to_records(headers, rows):
    \"\"\"Build one record per row, keyed by `headers`.\"\"\"
    if len(set(headers)) != len(headers):
        raise ValueError("the headers repeat")
    return [dict(zip(headers, row)) for row in rows]""",
    visible_test=_test_module(
        "record_zipping",
        "Published contract for building records.",
        """
def test_builds_records() -> None:
    assert zip_to_records(["a", "b"], [[1, 2]]) == [{"a": 1, "b": 2}]


def test_builds_two_records() -> None:
    assert zip_to_records(["a"], [[1], [2]]) == [{"a": 1}, {"a": 2}]
""",
        imports="from record_zipping import zip_to_records\n",
    ),
    hidden_test=_test_module(
        "record_zipping",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_builds_records() -> None:
    assert zip_to_records(["a", "b"], [[1, 2]]) == [{"a": 1, "b": 2}]


def test_a_row_of_the_wrong_width_names_its_position() -> None:
    with pytest.raises(ValueError, match="row 1"):
        zip_to_records(["a", "b"], [[1, 2], [3]])


def test_repeated_headers_are_refused() -> None:
    with pytest.raises(ValueError, match="repeat"):
        zip_to_records(["a", "a"], [[1, 2]])
""",
        imports="from record_zipping import zip_to_records\n",
    ),
)

_D89 = D2TaskSpec(
    template_id="d2_transform.sort_by_order",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-order",
    module="key_ordering",
    module_doc="Reordering a mapping for presentation.",
    issue=(
        "sort_by_order() is documented to be a reordering, not a filter. Callers report keys "
        "they did not name disappearing, and a crash when the order names a key that the "
        "mapping does not carry."
    ),
    expected=(
        "sort_by_order(mapping, order) puts the named keys first in the order given, then "
        "everything else in its original order, and ignores a name that is not there."
    ),
    baseline_reason="the comprehension is driven by the order alone, so it filters and it demands",
    edge_cases=(
        "unnamed keys go last in their original order",
        "a name that is not there is ignored",
    ),
    baseline="""def sort_by_order(mapping, order):
    \"\"\"Return `mapping` with the keys in `order` first.\"\"\"
    return {key: mapping[key] for key in order}""",
    variant_one="""def sort_by_order(mapping, order):
    \"\"\"Return `mapping` with the keys in `order` first.\"\"\"
    ordered = {}
    for key in order:
        if key in mapping:
            ordered[key] = mapping[key]
    for key, value in mapping.items():
        ordered.setdefault(key, value)
    return ordered""",
    variant_two="""def sort_by_order(mapping, order):
    \"\"\"Return `mapping` with the keys in `order` first.\"\"\"
    wanted = [key for key in order if key in mapping]
    rest = [key for key in mapping if key not in wanted]
    return {key: mapping[key] for key in wanted + rest}""",
    variant_three="""def sort_by_order(mapping, order):
    \"\"\"Return `mapping` with the keys in `order` first.\"\"\"
    ordered = {key: mapping[key] for key in order}
    for key, value in mapping.items():
        ordered.setdefault(key, value)
    return ordered""",
    variant_four="""def sort_by_order(mapping, order):
    \"\"\"Return `mapping` with the keys in `order` first.\"\"\"
    return {key: mapping[key] for key in order if key in mapping}""",
    visible_test=_test_module(
        "key_ordering",
        "Published contract for key ordering.",
        """
def test_reorders_the_keys() -> None:
    assert list(sort_by_order({"a": 1, "b": 2}, ["b", "a"])) == ["b", "a"]


def test_keeps_the_values() -> None:
    assert sort_by_order({"a": 1, "b": 2}, ["b", "a"])["a"] == 1
""",
        imports="from key_ordering import sort_by_order\n",
    ),
    hidden_test=_test_module(
        "key_ordering",
        "The part of the contract the published tests do not state.",
        """
def test_reorders_the_keys() -> None:
    assert list(sort_by_order({"a": 1, "b": 2}, ["b", "a"])) == ["b", "a"]


def test_unnamed_keys_go_last_in_their_original_order() -> None:
    assert list(sort_by_order({"a": 1, "b": 2, "c": 3}, ["c"])) == ["c", "a", "b"]


def test_a_name_that_is_not_there_is_ignored() -> None:
    assert list(sort_by_order({"a": 1}, ["z", "a"])) == ["a"]
""",
        imports="from key_ordering import sort_by_order\n",
    ),
)

_D90 = D2TaskSpec(
    template_id="d2_transform.roll_up",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-rollup",
    module="rolling_up",
    module_doc="Totalling a measure across a grouping field.",
    issue=(
        "roll_up() is documented to treat an absent measure as nothing and to say which field "
        "was not a number. Callers report crashes on records that omit the measure, and "
        "errors from deep inside the addition."
    ),
    expected=(
        "roll_up(records, key, value) totals the measure per group, treats a record without "
        "the measure as contributing zero, and raises a ValueError naming the measure field "
        "when a value is not a number."
    ),
    baseline_reason="the measure is subscripted directly and its type is never examined",
    edge_cases=(
        "a record without the value contributes nothing",
        "a non-numeric value names the field",
    ),
    baseline="""def roll_up(records, key, value):
    \"\"\"Total `value` across the groups named by `key`.\"\"\"
    totals = {}
    for record in records:
        totals[record[key]] = totals.get(record[key], 0) + record[value]
    return totals""",
    variant_one="""def roll_up(records, key, value):
    \"\"\"Total `value` across the groups named by `key`.\"\"\"
    totals = {}
    for record in records:
        amount = record.get(value, 0)
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"{value!r} is not a number in every record")
        totals[record[key]] = totals.get(record[key], 0) + amount
    return totals""",
    variant_two="""def roll_up(records, key, value):
    \"\"\"Total `value` across the groups named by `key`.\"\"\"
    from collections import defaultdict

    totals = defaultdict(int)
    for record in records:
        amount = record.get(value, 0)
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"{value!r} is not a number in every record")
        totals[record[key]] += amount
    return dict(totals)""",
    variant_three="""def roll_up(records, key, value):
    \"\"\"Total `value` across the groups named by `key`.\"\"\"
    totals = {}
    for record in records:
        totals[record[key]] = totals.get(record[key], 0) + record.get(value, 0)
    return totals""",
    variant_four="""def roll_up(records, key, value):
    \"\"\"Total `value` across the groups named by `key`.\"\"\"
    totals = {}
    for record in records:
        amount = record[value]
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError(f"{value!r} is not a number in every record")
        totals[record[key]] = totals.get(record[key], 0) + amount
    return totals""",
    visible_test=_test_module(
        "rolling_up",
        "Published contract for rolling up.",
        """
def test_rolls_up_by_a_key() -> None:
    records = [{"g": "a", "n": 1}, {"g": "a", "n": 2}, {"g": "b", "n": 5}]
    assert roll_up(records, "g", "n") == {"a": 3, "b": 5}


def test_rolls_up_one_record() -> None:
    assert roll_up([{"g": "a", "n": 4}], "g", "n") == {"a": 4}
""",
        imports="from rolling_up import roll_up\n",
    ),
    hidden_test=_test_module(
        "rolling_up",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_rolls_up_by_a_key() -> None:
    records = [{"g": "a", "n": 1}, {"g": "a", "n": 2}, {"g": "b", "n": 5}]
    assert roll_up(records, "g", "n") == {"a": 3, "b": 5}


def test_a_record_without_the_value_contributes_nothing() -> None:
    assert roll_up([{"g": "a", "n": 1}, {"g": "a"}], "g", "n") == {"a": 1}


def test_a_non_numeric_value_names_the_field() -> None:
    with pytest.raises(ValueError, match="'n'"):
        roll_up([{"g": "a", "n": "x"}], "g", "n")
""",
        imports="from rolling_up import roll_up\n",
    ),
)

_D91 = D2TaskSpec(
    template_id="d2_transform.dedupe_records",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-record-dedupe",
    module="record_dedupe",
    module_doc="Removing repeated records by an identifying field.",
    issue=(
        "dedupe_records() is documented to keep the first record for each identifier, and to "
        "leave records without one alone. Callers report the last record winning, and a crash "
        "on records that carry no identifier at all."
    ),
    expected=(
        "dedupe_records(records, field) keeps the first record for each value of `field`, and "
        "keeps every record that does not carry the field."
    ),
    baseline_reason="each write overwrites the previous one, and the subscript assumes the field",
    edge_cases=(
        "the first record of a value is the one kept",
        "a record without the field is kept",
    ),
    baseline="""def dedupe_records(records, field):
    \"\"\"Keep the first record for each value of `field`.\"\"\"
    seen = {}
    for record in records:
        seen[record[field]] = record
    return list(seen.values())""",
    variant_one="""def dedupe_records(records, field):
    \"\"\"Keep the first record for each value of `field`.\"\"\"
    seen = set()
    kept = []
    for record in records:
        if field not in record:
            kept.append(record)
            continue
        marker = record[field]
        if marker in seen:
            continue
        seen.add(marker)
        kept.append(record)
    return kept""",
    variant_two="""def dedupe_records(records, field):
    \"\"\"Keep the first record for each value of `field`.\"\"\"
    kept = []
    for record in records:
        if field in record and any(
            other[field] == record[field] for other in kept if field in other
        ):
            continue
        kept.append(record)
    return kept""",
    variant_three="""def dedupe_records(records, field):
    \"\"\"Keep the first record for each value of `field`.\"\"\"
    seen = {}
    extra = []
    for record in records:
        if field not in record:
            extra.append(record)
            continue
        seen[record[field]] = record
    return list(seen.values()) + extra""",
    variant_four="""def dedupe_records(records, field):
    \"\"\"Keep the first record for each value of `field`.\"\"\"
    seen = {}
    for record in records:
        seen.setdefault(record[field], record)
    return list(seen.values())""",
    visible_test=_test_module(
        "record_dedupe",
        "Published contract for record deduplication.",
        """
def test_dedupes_by_a_field() -> None:
    records = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    assert dedupe_records(records, "id") == records


def test_collapses_a_repeat() -> None:
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}]
    assert len(dedupe_records(records, "id")) == 1
""",
        imports="from record_dedupe import dedupe_records\n",
    ),
    hidden_test=_test_module(
        "record_dedupe",
        "The part of the contract the published tests do not state.",
        """
def test_dedupes_by_a_field() -> None:
    records = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}]
    assert dedupe_records(records, "id") == records


def test_the_first_record_of_a_value_is_the_one_kept() -> None:
    records = [{"id": 1, "v": "a"}, {"id": 1, "v": "b"}]
    assert dedupe_records(records, "id")[0]["v"] == "a"


def test_a_record_without_the_field_is_kept() -> None:
    assert len(dedupe_records([{"id": 1}, {"other": 2}], "id")) == 2
""",
        imports="from record_dedupe import dedupe_records\n",
    ),
)

_D92 = D2TaskSpec(
    template_id="d2_transform.split_mapping",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-split-mapping",
    module="mapping_splitting",
    module_doc="Separating the settings a caller asked for from the rest.",
    issue=(
        "split_mapping() is documented to accept any iterable of keys and to ignore names that "
        "are not there. Callers report a crash on unknown names, and everything landing in "
        "the second half when they pass a generator."
    ),
    expected=(
        "split_mapping(mapping, keys) returns (selected, rest), leaves out a requested key "
        "that is not present, and accepts any iterable of keys, not only a re-readable one."
    ),
    baseline_reason="the keys are read twice, and the subscript assumes each one is present",
    edge_cases=(
        "a key that is not there is simply absent",
        "any iterable of keys is accepted",
    ),
    baseline="""def split_mapping(mapping, keys):
    \"\"\"Split `mapping` into the entries named by `keys` and the rest.\"\"\"
    selected = {key: mapping[key] for key in keys}
    rest = {key: value for key, value in mapping.items() if key not in keys}
    return selected, rest""",
    variant_one="""def split_mapping(mapping, keys):
    \"\"\"Split `mapping` into the entries named by `keys` and the rest.\"\"\"
    wanted = list(keys)
    selected = {key: mapping[key] for key in wanted if key in mapping}
    rest = {key: value for key, value in mapping.items() if key not in wanted}
    return selected, rest""",
    variant_two="""def split_mapping(mapping, keys):
    \"\"\"Split `mapping` into the entries named by `keys` and the rest.\"\"\"
    wanted = set(keys)
    selected = {}
    rest = {}
    for key, value in mapping.items():
        target = selected if key in wanted else rest
        target[key] = value
    return selected, rest""",
    variant_three="""def split_mapping(mapping, keys):
    \"\"\"Split `mapping` into the entries named by `keys` and the rest.\"\"\"
    selected = {key: mapping[key] for key in keys if key in mapping}
    rest = {key: value for key, value in mapping.items() if key not in keys}
    return selected, rest""",
    variant_four="""def split_mapping(mapping, keys):
    \"\"\"Split `mapping` into the entries named by `keys` and the rest.\"\"\"
    wanted = list(keys)
    selected = {key: mapping[key] for key in wanted}
    rest = {key: value for key, value in mapping.items() if key not in wanted}
    return selected, rest""",
    visible_test=_test_module(
        "mapping_splitting",
        "Published contract for splitting a mapping.",
        """
def test_splits_a_mapping() -> None:
    assert split_mapping({"a": 1, "b": 2}, ["a"]) == ({"a": 1}, {"b": 2})


def test_selecting_nothing_leaves_everything() -> None:
    assert split_mapping({"a": 1}, []) == ({}, {"a": 1})
""",
        imports="from mapping_splitting import split_mapping\n",
    ),
    hidden_test=_test_module(
        "mapping_splitting",
        "The part of the contract the published tests do not state.",
        """
def test_splits_a_mapping() -> None:
    assert split_mapping({"a": 1, "b": 2}, ["a"]) == ({"a": 1}, {"b": 2})


def test_a_key_that_is_not_there_is_simply_absent() -> None:
    assert split_mapping({"a": 1}, ["a", "z"]) == ({"a": 1}, {})


def test_any_iterable_of_keys_is_accepted() -> None:
    assert split_mapping({"a": 1, "b": 2}, iter(["a"])) == ({"a": 1}, {"b": 2})
""",
        imports="from mapping_splitting import split_mapping\n",
    ),
)

_D93 = D2TaskSpec(
    template_id="d2_transform.merge_lists",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-merge-lists",
    module="list_merging",
    module_doc="Merging two mappings whose values are lists.",
    issue=(
        "merge_lists() is documented to concatenate the lists under a shared key, and to hand "
        "back lists of its own. Callers report the right-hand value replacing the left, and "
        "appending to the result changing the mapping they passed in."
    ),
    expected=(
        "merge_lists(left, right) concatenates the lists under a shared key, left first, and "
        "shares no list object with either input."
    ),
    baseline_reason="update() replaces the value and hands the right-hand list straight through",
    edge_cases=(
        "shared keys are concatenated",
        "neither input list is shared with the result",
    ),
    baseline="""def merge_lists(left, right):
    \"\"\"Merge two mappings of lists, concatenating shared keys.\"\"\"
    merged = dict(left)
    merged.update(right)
    return merged""",
    variant_one="""def merge_lists(left, right):
    \"\"\"Merge two mappings of lists, concatenating shared keys.\"\"\"
    merged = {key: list(values) for key, values in left.items()}
    for key, values in right.items():
        merged[key] = merged.get(key, []) + list(values)
    return merged""",
    variant_two="""def merge_lists(left, right):
    \"\"\"Merge two mappings of lists, concatenating shared keys.\"\"\"
    keys = list(left) + [key for key in right if key not in left]
    return {key: [*left.get(key, []), *right.get(key, [])] for key in keys}""",
    variant_three="""def merge_lists(left, right):
    \"\"\"Merge two mappings of lists, concatenating shared keys.\"\"\"
    merged = dict(left)
    for key, values in right.items():
        if key in merged:
            merged[key] = merged[key] + values
        else:
            merged[key] = values
    return merged""",
    variant_four="""def merge_lists(left, right):
    \"\"\"Merge two mappings of lists, concatenating shared keys.\"\"\"
    merged = {key: list(values) for key, values in left.items()}
    for key, values in right.items():
        merged[key] = list(values)
    return merged""",
    visible_test=_test_module(
        "list_merging",
        "Published contract for merging lists.",
        """
def test_merges_two_keys() -> None:
    assert merge_lists({"a": [1]}, {"b": [2]}) == {"a": [1], "b": [2]}


def test_takes_a_key_from_the_right() -> None:
    assert merge_lists({}, {"b": [2]}) == {"b": [2]}
""",
        imports="from list_merging import merge_lists\n",
    ),
    hidden_test=_test_module(
        "list_merging",
        "The part of the contract the published tests do not state.",
        """
def test_merges_two_keys() -> None:
    assert merge_lists({"a": [1]}, {"b": [2]}) == {"a": [1], "b": [2]}


def test_shared_keys_are_concatenated() -> None:
    assert merge_lists({"a": [1]}, {"a": [2]}) == {"a": [1, 2]}


def test_neither_input_list_is_shared_with_the_result() -> None:
    right = {"b": [2]}
    merge_lists({}, right)["b"].append(99)
    assert right == {"b": [2]}
""",
        imports="from list_merging import merge_lists\n",
    ),
)

_D94 = D2TaskSpec(
    template_id="d2_transform.stringify_values",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-stringify",
    module="value_stringifying",
    module_doc="Rendering a settings mapping as text for export.",
    issue=(
        "stringify_values() is documented to render an absent value as an empty field and to "
        "refuse a container, because a flat export cannot hold one. Callers report the word "
        "'None' in their exports and lists rendered as their repr."
    ),
    expected=(
        "stringify_values(mapping) renders None as an empty string and raises TypeError for "
        "any value that is a container."
    ),
    baseline_reason="str() renders anything at all, including None and a list",
    edge_cases=(
        "none becomes an empty string",
        "a container is refused",
    ),
    baseline="""def stringify_values(mapping):
    \"\"\"Render every value of `mapping` as text.\"\"\"
    return {key: str(value) for key, value in mapping.items()}""",
    variant_one="""def stringify_values(mapping):
    \"\"\"Render every value of `mapping` as text.\"\"\"
    rendered = {}
    for key, value in mapping.items():
        if isinstance(value, (list, dict, set, tuple)):
            raise TypeError(f"{key!r} holds a container")
        rendered[key] = "" if value is None else str(value)
    return rendered""",
    variant_two="""def stringify_values(mapping):
    \"\"\"Render every value of `mapping` as text.\"\"\"

    def render(key, value):
        if hasattr(value, "__len__") and not isinstance(value, str):
            raise TypeError(f"{key!r} holds a container")
        return "" if value is None else str(value)

    return {key: render(key, value) for key, value in mapping.items()}""",
    variant_three="""def stringify_values(mapping):
    \"\"\"Render every value of `mapping` as text.\"\"\"
    return {key: "" if value is None else str(value) for key, value in mapping.items()}""",
    variant_four="""def stringify_values(mapping):
    \"\"\"Render every value of `mapping` as text.\"\"\"
    rendered = {}
    for key, value in mapping.items():
        if isinstance(value, (list, dict, set, tuple)):
            raise TypeError(f"{key!r} holds a container")
        rendered[key] = str(value)
    return rendered""",
    visible_test=_test_module(
        "value_stringifying",
        "Published contract for rendering values.",
        """
def test_renders_numbers() -> None:
    assert stringify_values({"a": 1, "b": 2.5}) == {"a": "1", "b": "2.5"}


def test_leaves_text_alone() -> None:
    assert stringify_values({"a": "x"}) == {"a": "x"}
""",
        imports="from value_stringifying import stringify_values\n",
    ),
    hidden_test=_test_module(
        "value_stringifying",
        "The part of the contract the published tests do not state.",
        """
import pytest


def test_renders_numbers() -> None:
    assert stringify_values({"a": 1, "b": 2.5}) == {"a": "1", "b": "2.5"}


def test_none_becomes_an_empty_string() -> None:
    assert stringify_values({"a": None}) == {"a": ""}


def test_a_container_is_refused() -> None:
    with pytest.raises(TypeError):
        stringify_values({"a": [1, 2]})
""",
        imports="from value_stringifying import stringify_values\n",
    ),
)

_D95 = D2TaskSpec(
    template_id="d2_transform.pivot",
    family=RealityTaskFamily.DATA_TRANSFORMATION,
    repository_group="d2-transform-pivot",
    module="pair_pivoting",
    module_doc="Pivoting records into a two-dimensional table.",
    issue=(
        "pivot() is documented to total a cell that several records land in, and to treat a "
        "record with no measure as contributing nothing. Callers report cells holding only "
        "the last record's figure, and crashes on records that omit the measure."
    ),
    expected=(
        "pivot(records, row_key, column_key, value_key) totals every record that lands in a "
        "cell, and treats a record without the measure as contributing zero."
    ),
    baseline_reason="the cell is assigned rather than accumulated, and the measure is subscripted",
    edge_cases=(
        "a repeated cell sums",
        "a missing value contributes zero",
    ),
    baseline="""def pivot(records, row_key, column_key, value_key):
    \"\"\"Pivot `records` into a table of rows by columns.\"\"\"
    table = {}
    for record in records:
        table.setdefault(record[row_key], {})[record[column_key]] = record[value_key]
    return table""",
    variant_one="""def pivot(records, row_key, column_key, value_key):
    \"\"\"Pivot `records` into a table of rows by columns.\"\"\"
    table = {}
    for record in records:
        row = table.setdefault(record[row_key], {})
        column = record[column_key]
        row[column] = row.get(column, 0) + record.get(value_key, 0)
    return table""",
    variant_two="""def pivot(records, row_key, column_key, value_key):
    \"\"\"Pivot `records` into a table of rows by columns.\"\"\"
    from collections import defaultdict

    table = defaultdict(lambda: defaultdict(int))
    for record in records:
        table[record[row_key]][record[column_key]] += record.get(value_key, 0)
    return {row: dict(columns) for row, columns in table.items()}""",
    variant_three="""def pivot(records, row_key, column_key, value_key):
    \"\"\"Pivot `records` into a table of rows by columns.\"\"\"
    table = {}
    for record in records:
        row = table.setdefault(record[row_key], {})
        column = record[column_key]
        row[column] = row.get(column, 0) + record[value_key]
    return table""",
    variant_four="""def pivot(records, row_key, column_key, value_key):
    \"\"\"Pivot `records` into a table of rows by columns.\"\"\"
    table = {}
    for record in records:
        table.setdefault(record[row_key], {})[record[column_key]] = record.get(value_key, 0)
    return table""",
    visible_test=_test_module(
        "pair_pivoting",
        "Published contract for pivoting.",
        """
def test_pivots_two_records() -> None:
    records = [{"r": "x", "c": "p", "v": 1}, {"r": "y", "c": "q", "v": 2}]
    assert pivot(records, "r", "c", "v") == {"x": {"p": 1}, "y": {"q": 2}}


def test_pivots_two_columns_of_one_row() -> None:
    records = [{"r": "x", "c": "p", "v": 1}, {"r": "x", "c": "q", "v": 2}]
    assert pivot(records, "r", "c", "v") == {"x": {"p": 1, "q": 2}}
""",
        imports="from pair_pivoting import pivot\n",
    ),
    hidden_test=_test_module(
        "pair_pivoting",
        "The part of the contract the published tests do not state.",
        """
def test_pivots_two_records() -> None:
    records = [{"r": "x", "c": "p", "v": 1}, {"r": "y", "c": "q", "v": 2}]
    assert pivot(records, "r", "c", "v") == {"x": {"p": 1}, "y": {"q": 2}}


def test_a_repeated_cell_sums() -> None:
    records = [{"r": "x", "c": "p", "v": 1}, {"r": "x", "c": "p", "v": 2}]
    assert pivot(records, "r", "c", "v") == {"x": {"p": 3}}


def test_a_missing_value_contributes_zero() -> None:
    assert pivot([{"r": "x", "c": "p"}], "r", "c", "v") == {"x": {"p": 0}}
""",
        imports="from pair_pivoting import pivot\n",
    ),
)

#: The P-CLONE cohort: ten templates authored to measure the rejection rate before the
#: remaining eighty-five were committed to. Kept as its own name because the probe evidence
#: reports a defect rate over exactly these ten and that claim has to stay checkable.
D2_PROBE_SPECS: tuple[D2TaskSpec, ...] = (
    _D1,
    _D2,
    _D3,
    _D4,
    _D5,
    _D6,
    _D7,
    _D8,
    _D9,
    _D10,
)

#: The whole D2 corpus. S21D2-014 raised the final batches to thirty each, which put the
#: total group floor at 125 and the genuinely-new floor at 95 against C3's thirty.
D2_TASK_SPECS: tuple[D2TaskSpec, ...] = (
    *D2_PROBE_SPECS,
    _D11,
    _D12,
    _D13,
    _D14,
    _D15,
    _D16,
    _D17,
    _D18,
    _D19,
    _D20,
    _D21,
    _D22,
    _D23,
    _D24,
    _D25,
    _D26,
    _D27,
    _D28,
    _D29,
    _D30,
    _D31,
    _D32,
    _D33,
    _D34,
    _D35,
    _D36,
    _D37,
    _D38,
    _D39,
    _D40,
    _D41,
    _D42,
    _D43,
    _D44,
    _D45,
    _D46,
    _D47,
    _D48,
    _D49,
    _D50,
    _D51,
    _D52,
    _D53,
    _D54,
    _D55,
    _D56,
    _D57,
    _D58,
    _D59,
    _D60,
    _D61,
    _D62,
    _D63,
    _D64,
    _D65,
    _D66,
    _D67,
    _D68,
    _D69,
    _D70,
    _D71,
    _D72,
    _D73,
    _D74,
    _D75,
    _D76,
    _D77,
    _D78,
    _D79,
    _D80,
    _D81,
    _D82,
    _D83,
    _D84,
    _D85,
    _D86,
    _D87,
    _D88,
    _D89,
    _D90,
    _D91,
    _D92,
    _D93,
    _D94,
    _D95,
)
