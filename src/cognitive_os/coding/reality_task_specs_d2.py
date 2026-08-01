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
        return (self.variant_one, self.variant_two, self.variant_three, self.variant_four)

    @property
    def repairs_contract(self) -> tuple[bool, ...]:
        """Provenance only. Declared so the corpus can be audited, never so it can be fitted."""
        return (True, True, False, False)


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
    edge_cases=("an empty sequence is returned unchanged", "an offset above the length wraps"),
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
    edge_cases=("a label without the prefix is unchanged", "an empty prefix removes nothing"),
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
    edge_cases=("a zero denominator returns the default", "two negative arguments give a positive"),
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
    edge_cases=("releasing an unknown slot is a no-op", "the held count never goes negative"),
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
    edge_cases=("a key whose value is None is still present", "an empty key list returns default"),
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
    edge_cases=("a short sequence still yields n parts", "a non-positive count is refused"),
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
    edge_cases=("the base is included in every entry", "an empty sequence yields nothing"),
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

#: The P-CLONE cohort: ten templates authored to measure the rejection rate before the
#: remaining eighty-five are committed to.
D2_PROBE_SPECS: tuple[D2TaskSpec, ...] = (_D1, _D2, _D3, _D4, _D5, _D6, _D7, _D8, _D9, _D10)
