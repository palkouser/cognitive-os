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

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.experience import HashedExperienceContract

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
