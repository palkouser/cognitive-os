"""S21D2-024: resolving the presealed calibration out-of-distribution perturbations.

The submanifest named four perturbations and hash-bound them before any calibration number
existed. This is where they become inputs. Nothing here decides anything: the resolved set is
retained beside the calibration partition and is never fitted, never scored and never counted
towards an outcome floor — S21D2-044 is what eventually reads it.

Every perturbation is a deterministic function of the task it perturbs, for the same reason the
corpus is: an OOD set that cannot be regenerated is an OOD set nobody can check. And every one
of them preserves behaviour, so a perturbed package still executes. A probe that broke the task
would measure whether the ranker notices broken Python, which is not the question.

What each one does, and what it deliberately does not do:

*`rename_every_identifier_in_the_visible_module`* renames what the module defines — its
function, its parameters, its locals — consistently across the module and the suites that
import it. Imported and builtin names are left alone: renaming those would not shift the
distribution, it would produce a module that does not run.

*`reorder_independent_statements_in_the_baseline`* swaps adjacent single-line assignments whose
targets neither reads. A task with no such pair records that it has none rather than being
given one, because a perturbation reported as applied when it was not is worse than an absent
one.

*`rewrite_the_issue_text_without_changing_the_contract`* substitutes phrasing in the issue text.
It is the only perturbation that touches the requirement channel rather than the candidate one.

*`substitute_equivalent_literals_in_the_visible_tests`* replaces literals with equal-valued
expressions — `3` becomes `(0 + 3)`, `"abc"` becomes `("a" "bc")` — so the token stream and the
AST both move while every assertion still asserts exactly what it did.
"""

from __future__ import annotations

import ast
import io
import itertools
import keyword
import tokenize
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256

from pydantic import Field, model_validator

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import CorrectionEvaluationCountsV3

RENAME = "rename_every_identifier_in_the_visible_module"
REORDER = "reorder_independent_statements_in_the_baseline"
REWRITE_ISSUE = "rewrite_the_issue_text_without_changing_the_contract"
SUBSTITUTE_LITERALS = "substitute_equivalent_literals_in_the_visible_tests"

#: Deterministic phrase substitutions. Meaning-preserving by inspection, which is the only way
#: to preserve it: a generated paraphrase would be a second thing to verify.
_PHRASES: tuple[tuple[str, str], ...] = (
    ("returns", "gives back"),
    ("raises", "signals"),
    ("should", "is expected to"),
    ("when", "in the case where"),
    ("but", "however it"),
    ("does not", "fails to"),
)


class PerturbationError(ValueError):
    """A perturbation could not be applied to source it was supposed to preserve."""


@dataclass(frozen=True, slots=True)
class AppliedPerturbation:
    """One perturbation against one task, and whether it had anything to change."""

    name: str
    applied: bool
    detail: str


def _defined_names(source: str) -> tuple[str, ...]:
    """Names the module itself binds. Imports and builtins are not among them."""
    tree = ast.parse(source)
    imported: set[str] = set()
    defined: list[str] = []
    seen: set[str] = set()

    def remember(name: str) -> None:
        if name in seen or keyword.iskeyword(name) or name.startswith("__"):
            return
        seen.add(name)
        defined.append(name)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".", 1)[0])
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            remember(node.name)
            for argument in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                remember(argument.arg)
            if node.args.vararg is not None:
                remember(node.args.vararg.arg)
            if node.args.kwarg is not None:
                remember(node.args.kwarg.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            remember(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            remember(node.name)
    return tuple(name for name in defined if name not in imported)


def rename_map(source: str) -> dict[str, str]:
    """`original -> pseudonym`, in first-appearance order, stable for one module.

    Pseudonyms carry no trace of the original: a rename to `renamed_rotate_left` would leave
    the distribution exactly where it was, spelled longer.
    """
    return {name: f"q{index}" for index, name in enumerate(_defined_names(source))}


def _retoken(source: str, mapping: dict[str, str]) -> str:
    """Apply a name mapping through the tokenizer, so only real names are touched."""
    result: list[tokenize.TokenInfo] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME and token.string in mapping:
            result.append(token._replace(string=mapping[token.string]))
        else:
            result.append(token)
    return tokenize.untokenize(result)


def rename_identifiers(module: str, *others: str) -> tuple[str, ...]:
    """Rename what `module` defines, in `module` and in every source that imports from it."""
    mapping = rename_map(module)
    if not mapping:
        raise PerturbationError("the module defines no name to rename")
    return tuple(_retoken(source, mapping) for source in (module, *others))


def _swappable_pair(source: str) -> tuple[int, int] | None:
    """The first adjacent pair of single-line assignments that may trade places.

    Returns one-based line numbers. Independence is decided structurally: neither statement may
    read a name the other binds, and both must occupy exactly one line, so the swap is a line
    swap rather than a re-render of the module.
    """
    for node in ast.walk(ast.parse(source)):
        body = getattr(node, "body", None)
        if not isinstance(body, list):
            continue
        for first, second in itertools.pairwise(body):
            if not (isinstance(first, ast.Assign) and isinstance(second, ast.Assign)):
                continue
            if first.end_lineno != first.lineno or second.end_lineno != second.lineno:
                continue
            if second.lineno != first.lineno + 1:
                continue
            binds_first = {t.id for t in ast.walk(first) if isinstance(t, ast.Name)}
            binds_second = {t.id for t in ast.walk(second) if isinstance(t, ast.Name)}
            targets_first = {
                t.id
                for t in ast.walk(ast.Module(body=[first], type_ignores=[]))
                if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)
            }
            targets_second = {
                t.id
                for t in ast.walk(ast.Module(body=[second], type_ignores=[]))
                if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)
            }
            if targets_first & binds_second or targets_second & binds_first:
                continue
            return first.lineno, second.lineno
    return None


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def reorder_independent_statements(source: str) -> tuple[str, AppliedPerturbation]:
    """Swap one independent adjacent pair, or say plainly that there is none."""
    pair = _swappable_pair(source)
    if pair is None:
        return source, AppliedPerturbation(
            REORDER, False, "the baseline holds no adjacent pair of independent assignments"
        )
    first, second = pair
    lines = source.splitlines(keepends=True)
    if _indent(lines[first - 1]) != _indent(lines[second - 1]):
        return source, AppliedPerturbation(
            REORDER, False, "the candidate pair sits at two indentation levels"
        )
    lines[first - 1], lines[second - 1] = lines[second - 1], lines[first - 1]
    swapped = "".join(lines)
    ast.parse(swapped)
    return swapped, AppliedPerturbation(
        REORDER, True, f"swapped the assignments on lines {first} and {second}"
    )


def rewrite_issue_text(issue: str) -> tuple[str, AppliedPerturbation]:
    """Restate the issue in different words. The contract it describes is untouched."""
    rewritten = issue
    used: list[str] = []
    for original, replacement in _PHRASES:
        if original in rewritten:
            rewritten = rewritten.replace(original, replacement)
            used.append(original)
    rewritten = f"Reported behaviour: {rewritten}"
    return rewritten, AppliedPerturbation(
        REWRITE_ISSUE,
        True,
        f"restated the issue; substituted {len(used)} phrase(s)",
    )


def substitute_literals(source: str) -> tuple[str, AppliedPerturbation]:
    """Replace literals with equal-valued expressions, through the tokenizer."""
    changed = 0
    result: list[tokenize.TokenInfo] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        text = token.string
        if token.type == tokenize.NUMBER and text.isdigit():
            result.append(token._replace(string=f"(0 + {text})"))
            changed += 1
        elif token.type == tokenize.STRING and text[:1] in {'"', "'"} and len(text) >= 4:
            quote = text[0] * (3 if text[:3] in {'"""', "'''"} else 1)
            body = text[len(quote) : -len(quote)]
            if len(body) >= 2 and "\\" not in body and quote * 3 != text[:3]:
                result.append(
                    token._replace(string=f"({quote}{body[0]}{quote} {quote}{body[1:]}{quote})")
                )
                changed += 1
                continue
            result.append(token)
        else:
            result.append(token)
    rewritten = tokenize.untokenize(result)
    ast.parse(rewritten)
    return rewritten, AppliedPerturbation(
        SUBSTITUTE_LITERALS, changed > 0, f"substituted {changed} literal(s)"
    )


@dataclass(frozen=True, slots=True)
class PerturbedSources:
    """One task package after all four perturbations, and what each of them did."""

    module_source: str
    visible_test: str
    hidden_test: str
    issue: str
    applied: tuple[AppliedPerturbation, ...]


def perturb(
    *, module_source: str, visible_test: str, hidden_test: str, issue: str
) -> PerturbedSources:
    """Apply the four declared perturbations to one task, in a fixed order.

    The order is not arbitrary: renaming runs first so the later two work on the names the
    probe will actually carry, and the hidden suite is renamed with the rest because it imports
    the same module and would otherwise stop importing at all.
    """
    renamed_module, renamed_visible, renamed_hidden = rename_identifiers(
        module_source, visible_test, hidden_test
    )
    rename_applied = AppliedPerturbation(
        RENAME, True, f"renamed {len(rename_map(module_source))} defined name(s)"
    )
    reordered, reorder_applied = reorder_independent_statements(renamed_module)
    substituted, literals_applied = substitute_literals(renamed_visible)
    rewritten, issue_applied = rewrite_issue_text(issue)
    return PerturbedSources(
        module_source=reordered,
        visible_test=substituted,
        hidden_test=renamed_hidden,
        issue=rewritten,
        applied=(rename_applied, reorder_applied, issue_applied, literals_applied),
    )


class PerturbedTask(HashedExperienceContract):
    """One calibration group's OOD probe, bound to the submanifest that named it."""

    template_id: NonEmptyStr
    repository_group: NonEmptyStr
    perturbations_applied: tuple[NonEmptyStr, ...] = Field(min_length=1)
    perturbations_not_applicable: tuple[NonEmptyStr, ...] = ()
    module_source_hash: Sha256Hex
    visible_test_hash: Sha256Hex
    issue_text_hash: Sha256Hex
    #: Executed once when the set was resolved. A probe that no longer runs is not a probe.
    visible_suite_passes: bool
    fitted: bool = False
    scored: bool = False


class ResolvedOodSet(HashedExperienceContract):
    """The resolved probe set, bound to the submanifest hash it was declared under."""

    kind: NonEmptyStr
    submanifest_hash: Sha256Hex
    perturbation_seed: int
    tasks: tuple[PerturbedTask, ...] = Field(min_length=1)
    retained_outside_fitting: bool = True

    def model_post_init(self, context: object) -> None:
        if not self.retained_outside_fitting or any(task.fitted for task in self.tasks):
            raise ValueError("a calibration OOD probe that reaches fitting is not a probe")


# Revision 3 is additive. The D2 contracts above remain readable byte for byte.


def transformation_case_id(*, stage: str, source_group_id: str, case_name: str, seed: int) -> str:
    """The pre-registered case identity: one group, one composition, one seed, one decision."""
    return sha256(f"{stage}:{source_group_id}:{case_name}:{seed}".encode()).hexdigest()


class OodCaseManifestV3(HashedExperienceContract):
    """One independently countable transformation case and its exact four candidates."""

    case_id: Sha256Hex
    stage: NonEmptyStr
    source_group_id: NonEmptyStr
    case_name: NonEmptyStr
    transformations: tuple[NonEmptyStr, ...] = Field(min_length=1)
    seed: int = Field(ge=0)
    candidate_ids: tuple[NonEmptyStr, ...] = Field(min_length=4, max_length=4)
    source_manifest_hash: Sha256Hex

    @model_validator(mode="after")
    def identity_and_candidate_set_are_exact(self) -> OodCaseManifestV3:
        expected = transformation_case_id(
            stage=self.stage,
            source_group_id=self.source_group_id,
            case_name=self.case_name,
            seed=self.seed,
        )
        if self.case_id != expected:
            raise ValueError("OOD case identity does not match stage, group, case, and seed")
        if len(set(self.candidate_ids)) != 4:
            raise ValueError("an OOD ranking decision requires four distinct candidates")
        return self


class OodSubmanifestV3(HashedExperienceContract):
    """Exact case membership; generation stays independent of the production normalizer."""

    revision: int = 3
    stage: NonEmptyStr
    source_manifest_hash: Sha256Hex
    generator_code_hash: Sha256Hex
    hard_coded_oracle_hash: Sha256Hex
    cases: tuple[OodCaseManifestV3, ...] = Field(min_length=1)
    fitted: bool = False

    @model_validator(mode="after")
    def cases_share_one_authority_and_never_fit(self) -> OodSubmanifestV3:
        if self.fitted:
            raise ValueError("metamorphic OOD cases cannot enter fitting")
        if len({case.case_id for case in self.cases}) != len(self.cases):
            raise ValueError("an OOD submanifest cannot repeat a case")
        for case in self.cases:
            if case.stage != self.stage or case.source_manifest_hash != self.source_manifest_hash:
                raise ValueError("an OOD case is bound to another stage or source manifest")
        return self


class OodCaseResultV3(HashedExperienceContract):
    """One transformed ranking decision and four separately verified candidate labels."""

    case_id: Sha256Hex
    source_group_id: NonEmptyStr
    clean_answered: bool
    answered: bool
    abstained: bool
    clean_first_choice_correct: bool
    baseline_first_choice_correct: bool
    clean_changed_action: bool
    action_preserved: bool | None = None
    transformed_changed_action: bool = False
    confident_error: bool = False
    verifier_failures: int = Field(default=0, ge=0, le=4)
    label_changes: int = Field(default=0, ge=0, le=4)
    candidate_outcomes: int = Field(default=4, ge=4, le=4)

    @model_validator(mode="after")
    def decision_and_outcome_units_are_coherent(self) -> OodCaseResultV3:
        if self.answered == self.abstained:
            raise ValueError("one OOD decision must be answered or abstained, exclusively")
        paired = self.clean_answered and self.answered
        if paired != (self.action_preserved is not None):
            raise ValueError("action preservation is defined exactly for covered pairs")
        if self.confident_error and not self.answered:
            raise ValueError("an abstention cannot be a confident error")
        if self.transformed_changed_action and not self.answered:
            raise ValueError("an abstention cannot be a changed transformed action")
        return self


class OodPrecheckV3(HashedExperienceContract):
    """Unit-correct OOD result with both error denominators and non-silence gates."""

    revision: int = 3
    submanifest_hash: Sha256Hex
    counts: CorrectionEvaluationCountsV3
    clean_first_choice_rate: Decimal
    baseline_first_choice_rate: Decimal
    clean_coverage: Decimal
    equivalence_coverage: Decimal
    action_preservation_rate: Decimal
    confident_error_rate_all_decisions: Decimal
    confident_error_rate_answered_decisions: Decimal | None
    verifier_failures: int = Field(ge=0)
    label_changes: int = Field(ge=0)
    changed_clean_decisions: int = Field(ge=0)
    clean_coverage_floor: Decimal = Decimal("0.80")
    equivalence_coverage_floor: Decimal = Decimal("0.80")
    maximum_coverage_loss: Decimal = Decimal("0.05")
    required_action_preservation: Decimal = Decimal("1.00")
    confident_errors_allowed: int = 0
    selection_eligible: bool
    ineligible_reasons: tuple[NonEmptyStr, ...] = ()
    entered_any_dataset: bool = False

    @model_validator(mode="after")
    def metrics_and_non_silence_rule_are_exact(self) -> OodPrecheckV3:
        if self.entered_any_dataset:
            raise ValueError("an OOD precheck that entered a dataset is not a precheck")
        decisions = Decimal(self.counts.ranking_decisions)
        answered = Decimal(self.counts.answered_decisions)
        expected_all = Decimal(self.counts.confident_errors) / decisions
        expected_answered = Decimal(self.counts.confident_errors) / answered if answered else None
        if self.confident_error_rate_all_decisions != expected_all:
            raise ValueError("confident-error/all-decisions rate uses the wrong denominator")
        if self.confident_error_rate_answered_decisions != expected_answered:
            raise ValueError("confident-error/answered rate uses the wrong denominator")
        reasons: list[str] = []
        if self.clean_first_choice_rate <= self.baseline_first_choice_rate:
            reasons.append("clean_first_choice_does_not_beat_baseline")
        if self.clean_coverage < self.clean_coverage_floor:
            reasons.append("clean_coverage_below_floor")
        if self.equivalence_coverage < self.equivalence_coverage_floor:
            reasons.append("equivalence_coverage_below_floor")
        if self.clean_coverage - self.equivalence_coverage > self.maximum_coverage_loss:
            reasons.append("equivalence_coverage_loss_exceeds_limit")
        if self.counts.confident_errors > self.confident_errors_allowed:
            reasons.append("confident_equivalence_error")
        if self.action_preservation_rate != self.required_action_preservation:
            reasons.append("covered_action_not_preserved")
        if self.changed_clean_decisions < 1:
            reasons.append("no_changed_clean_decision")
        if self.selection_eligible != (not reasons) or self.ineligible_reasons != tuple(reasons):
            raise ValueError("selection eligibility does not match the frozen non-silence rule")
        return self


def build_ood_precheck_v3(
    manifest: OodSubmanifestV3, results: tuple[OodCaseResultV3, ...]
) -> OodPrecheckV3:
    """Aggregate cases without ever treating their four candidate slots as decisions."""
    expected = {case.case_id: case for case in manifest.cases}
    if len(results) != len(expected) or {item.case_id for item in results} != set(expected):
        raise ValueError("OOD results must resolve every manifest case exactly once")
    for result in results:
        if result.source_group_id != expected[result.case_id].source_group_id:
            raise ValueError("OOD result resolves to another source group")
    decisions = len(results)
    answered = sum(item.answered for item in results)
    abstained = sum(item.abstained for item in results)
    errors = sum(item.confident_error for item in results)
    paired = [item for item in results if item.action_preserved is not None]
    clean_answered = sum(item.clean_answered for item in results)
    counts = CorrectionEvaluationCountsV3(
        task_groups=len({item.source_group_id for item in results}),
        metamorphic_cases=decisions,
        ranking_decisions=decisions,
        candidate_outcomes=sum(item.candidate_outcomes for item in results),
        answered_decisions=answered,
        abstained_decisions=abstained,
        changed_actions=sum(item.transformed_changed_action for item in results),
        confident_errors=errors,
    )
    clean_rate = Decimal(sum(item.clean_first_choice_correct for item in results)) / Decimal(
        decisions
    )
    baseline_rate = Decimal(sum(item.baseline_first_choice_correct for item in results)) / Decimal(
        decisions
    )
    clean_coverage = Decimal(clean_answered) / Decimal(decisions)
    equivalence_coverage = Decimal(answered) / Decimal(decisions)
    preservation = (
        Decimal(sum(bool(item.action_preserved) for item in paired)) / Decimal(len(paired))
        if paired
        else Decimal("0")
    )
    provisional = {
        "clean_first_choice_does_not_beat_baseline": clean_rate <= baseline_rate,
        "clean_coverage_below_floor": clean_coverage < Decimal("0.80"),
        "equivalence_coverage_below_floor": equivalence_coverage < Decimal("0.80"),
        "equivalence_coverage_loss_exceeds_limit": (
            clean_coverage - equivalence_coverage > Decimal("0.05")
        ),
        "confident_equivalence_error": errors > 0,
        "covered_action_not_preserved": preservation != Decimal("1.00"),
        "no_changed_clean_decision": not any(item.clean_changed_action for item in results),
    }
    reasons = tuple(name for name, failed in provisional.items() if failed)
    return OodPrecheckV3(
        submanifest_hash=manifest.content_hash,
        counts=counts,
        clean_first_choice_rate=clean_rate,
        baseline_first_choice_rate=baseline_rate,
        clean_coverage=clean_coverage,
        equivalence_coverage=equivalence_coverage,
        action_preservation_rate=preservation,
        confident_error_rate_all_decisions=Decimal(errors) / Decimal(decisions),
        confident_error_rate_answered_decisions=(
            Decimal(errors) / Decimal(answered) if answered else None
        ),
        verifier_failures=sum(item.verifier_failures for item in results),
        label_changes=sum(item.label_changes for item in results),
        changed_clean_decisions=sum(item.clean_changed_action for item in results),
        selection_eligible=not reasons,
        ineligible_reasons=reasons,
    )
