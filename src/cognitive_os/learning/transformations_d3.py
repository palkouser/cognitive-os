"""S21D3-015: the six metamorphic transformations, generated independently of the encoder.

D2 measured one opaque combined perturbation and could say only that *something* moved. Revision
3 replaces it with six independently countable cases per group — two identifier renames, two
contract-preserving issue rewrites, and the two declared combinations — so a confident reversal
names the channel that caused it.

The rule this module exists to honour is §9's *superficial rename fix*: an encoder must not be
its own oracle. `correction_source.py` decides what a canonical candidate looks like; if the
same code also produced the renames that are supposed to prove it invariant, an invariance pass
would prove that a function agrees with itself. So the renames here are built from
`calibration_ood`'s released token-stream primitives — a different algorithm, released before
the v2 encoder existed — and `GOLDEN_RENAMES` pins the output of both maps against hard-coded
text that neither implementation can move.

Rename A and rename B are independent by construction rather than by hope: A allocates
pseudonyms in first-binding order, B allocates a different alphabet in reverse order, so no
name keeps its position in both. A group where the two maps agree on any name is refused.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from hashlib import sha256

from cognitive_os.learning import calibration_ood
from cognitive_os.learning.calibration_ood import PerturbationError

RENAME_A = "identifier_rename_a"
RENAME_B = "identifier_rename_b"
ISSUE_A = "issue_rewrite_a"
ISSUE_B = "issue_rewrite_b"
RENAME_A_ISSUE_A = "identifier_rename_a_plus_issue_rewrite_a"
RENAME_B_ISSUE_B = "identifier_rename_b_plus_issue_rewrite_b"

#: The six nominal cases, in the order revision 3 froze them.
CASES: tuple[str, ...] = (RENAME_A, RENAME_B, ISSUE_A, ISSUE_B, RENAME_A_ISSUE_A, RENAME_B_ISSUE_B)

#: Optional boundary probes. Reported with their applicability and never counted towards the
#: hundred-decision floor, because §2.3 excludes them from condition 20's denominator.
OPTIONAL_PROBES: tuple[str, ...] = (
    "baseline_independent_statement_reorder",
    "visible_test_equivalent_literal_substitution",
)

#: Rewrite B's phrase table. Disjoint from `calibration_ood._PHRASES` in what it replaces, so
#: applying B to a text A already touched is still a second independent rewrite.
_PHRASES_B: tuple[tuple[str, str], ...] = (
    ("Callers report", "Users are seeing"),
    ("is documented to", "is supposed to"),
    ("instead of", "rather than"),
    ("crash", "hard failure"),
    ("rejected", "turned away"),
    ("accepted", "let through"),
)


def rename_map_a(module_source: str) -> dict[str, str]:
    """The released map: `q0`, `q1`, … in first-binding order."""
    return calibration_ood.rename_map(module_source)


def rename_map_b(module_source: str) -> dict[str, str]:
    """An independent map: a different alphabet, allocated in reverse binding order."""
    names = calibration_ood._defined_names(module_source)
    return {name: f"w{index}" for index, name in enumerate(reversed(names))}


def rewrite_issue_a(issue: str) -> str:
    """The released rewrite, unchanged."""
    rewritten, _ = calibration_ood.rewrite_issue_text(issue)
    return rewritten


def rewrite_issue_b(issue: str) -> str:
    """A second rewrite over a disjoint phrase table, with its own framing sentence."""
    rewritten = issue
    for original, replacement in _PHRASES_B:
        rewritten = rewritten.replace(original, replacement)
    return f"{rewritten} (restated by the reporter)"


@dataclass(frozen=True, slots=True)
class TransformedPackage:
    """One task package after one case: the same contract, spelled differently."""

    case_name: str
    module_source: str
    variants: tuple[str, ...]
    visible_test: str
    hidden_test: str
    issue: str
    renamed_names: int


def _eligible_map(module_source: str, mapping: dict[str, str]) -> dict[str, str]:
    if not mapping:
        raise PerturbationError("the module binds no source-local name to rename")
    if len(set(mapping.values())) != len(mapping):
        raise PerturbationError("a rename map allocates one pseudonym twice")
    collisions = set(mapping) & set(mapping.values())
    if collisions:
        raise PerturbationError(f"a pseudonym collides with an existing name: {sorted(collisions)}")
    return mapping


def _keyword_argument_names(module_source: str) -> set[str]:
    """Names used as call keywords. A token-stream rename cannot tell `f(key=1)`'s `key` from
    a binding, and renaming it would call a foreign function with an argument it has never
    heard of, so a package that has one is refused rather than perturbed."""
    return {
        node.arg
        for node in ast.walk(ast.parse(module_source))
        if isinstance(node, ast.keyword) and node.arg is not None
    }


def eligible(module_source: str) -> bool:
    """Whether all six cases apply to this package.

    A group is eligible when both maps exist, neither collides with an existing name or a call
    keyword, and the two disagree on every name — otherwise rename A and rename B would be one
    case reported twice.
    """
    try:
        first = _eligible_map(module_source, rename_map_a(module_source))
        second = _eligible_map(module_source, rename_map_b(module_source))
    except (PerturbationError, SyntaxError):
        return False
    if set(first) & _keyword_argument_names(module_source):
        return False
    return all(first[name] != second[name] for name in first)


def transform(
    case_name: str,
    *,
    module_source: str,
    variants: tuple[str, ...],
    visible_test: str,
    hidden_test: str,
    issue: str,
) -> TransformedPackage:
    """Apply one frozen case to one package. Deterministic in its inputs and nothing else."""
    if case_name not in CASES:
        raise PerturbationError(f"{case_name!r} is not one of the six frozen cases")

    renames = 0
    sources = (module_source, *variants, visible_test, hidden_test)
    if case_name in {RENAME_A, RENAME_A_ISSUE_A}:
        mapping = _eligible_map(module_source, rename_map_a(module_source))
        sources = calibration_ood.rename_identifiers(*sources, mapping=mapping)
        renames = len(mapping)
    elif case_name in {RENAME_B, RENAME_B_ISSUE_B}:
        mapping = _eligible_map(module_source, rename_map_b(module_source))
        sources = calibration_ood.rename_identifiers(*sources, mapping=mapping)
        renames = len(mapping)

    rewritten = issue
    if case_name in {ISSUE_A, RENAME_A_ISSUE_A}:
        rewritten = rewrite_issue_a(issue)
    elif case_name in {ISSUE_B, RENAME_B_ISSUE_B}:
        rewritten = rewrite_issue_b(issue)

    return TransformedPackage(
        case_name=case_name,
        module_source=sources[0],
        variants=tuple(sources[1 : 1 + len(variants)]),
        visible_test=sources[-2],
        hidden_test=sources[-1],
        issue=rewritten,
        renamed_names=renames,
    )


#: The second oracle. Hard-coded input and output text, so a change to either rename map or
#: either rewrite fails here before it can reach a metamorphic case — and so the encoder cannot
#: quietly agree with a generator that moved with it.
GOLDEN_RENAMES: tuple[tuple[str, str, str], ...] = (
    (
        RENAME_A,
        "def widen(edge, span):\n    total = edge + span\n    return total\n",
        "def q0(q1, q2):\n    q3 = q1 + q2\n    return q3\n",
    ),
    (
        RENAME_B,
        "def widen(edge, span):\n    total = edge + span\n    return total\n",
        "def w3(w2, w1):\n    w0 = w2 + w1\n    return w0\n",
    ),
)

GOLDEN_ISSUES: tuple[tuple[str, str, str], ...] = (
    (
        ISSUE_A,
        "widen() returns the sum but raises when the span is absent.",
        "Reported behaviour: widen() gives back the sum however it signals in the case where "
        "the span is absent.",
    ),
    (
        ISSUE_B,
        "widen() is documented to add a span. Callers report a crash instead of a result.",
        "widen() is supposed to add a span. Users are seeing a hard failure rather than a "
        "result. (restated by the reporter)",
    ),
)


def check_golden_pairs() -> None:
    """Run the hard-coded oracle. Raises rather than returning a report: there is one answer."""
    for case_name, source, expected in GOLDEN_RENAMES:
        produced = transform(
            case_name,
            module_source=source,
            variants=(),
            visible_test="",
            hidden_test="",
            issue="",
        ).module_source
        if produced != expected:
            raise PerturbationError(f"{case_name} no longer reproduces its golden output")
    for case_name, issue, expected in GOLDEN_ISSUES:
        rewrite = rewrite_issue_a if case_name == ISSUE_A else rewrite_issue_b
        if rewrite(issue) != expected:
            raise PerturbationError(f"{case_name} no longer reproduces its golden output")


def hard_coded_oracle_hash() -> str:
    """Hash of the golden table, bound into the submanifest before any case is scored."""
    body = "\n".join(
        f"{name}␟{source}␟{expected}"
        for name, source, expected in (*GOLDEN_RENAMES, *GOLDEN_ISSUES)
    )
    return sha256(body.encode()).hexdigest()


def generator_code_hash() -> str:
    """Hash of the generator's own bytes and of the released primitives it stands on.

    Recorded in the submanifest so a later reader can tell whether the code that produced a
    case is the code that was frozen, without trusting the version string next to it.
    """
    digest = sha256()
    for module in (calibration_ood, __import__(__name__, fromlist=["_"])):
        digest.update(inspect.getsource(module).encode())
    return digest.hexdigest()
