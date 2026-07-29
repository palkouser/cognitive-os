"""Leakage and corpus-shortcut analysis, §S21C3-024 and §4.12.

Four things can make a corpus look better than it is, and each has a check here:

*The answer is in the question.* A hidden test name, a control hash or a golden source line
that reaches a provider request, a feature row or an embedding input means the score measures
retrieval, not repair. `control_tokens` names everything that must never appear outside the
control bundle, and `scan_for_control_leaks` looks for it in whatever text a caller is about
to publish.

*The tasks are the same task.* Thirty near-clones is six problems wearing thirty hats, and a
group-aware split cannot protect an evaluation whose groups are copies of each other.
`normalized_structure_hash` erases identifiers and literals, so two tasks that differ only in
naming collide and are reported.

*A fix from one task solves another.* This is the meaningful form of the universal-patch
adversary. Concatenating every declared answer trivially "solves" the corpus, because each
task's own answer is in the pile — that proves nothing. What must not happen is a *donor*
task's correction, dropped into a *recipient* task's file, making the recipient pass.
`cross_task_transfers` enumerates those attempts for the sandbox to execute.

*The task can be looked up.* If a provider-visible field carries the template ID, the seed or
the generator profile, a model does not have to repair anything to answer. `lookup_key_leaks`
checks the projection for exactly those.

Nothing here executes anything. It reads text and reports; the sandbox decides whether a
transferred patch actually passes, because only an execution can answer that.
"""

from __future__ import annotations

import ast
import io
import tokenize
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from cognitive_os.domain.reality import (
    RealityCandidateStrategy,
    RealityTaskManifest,
    RealityTaskProjection,
)

from .reality_tasks import TaskTemplate

#: Minimum length for a token to be worth searching for. Shorter strings collide with ordinary
#: English and would make every scan report a leak, which is the same as reporting none.
_MINIMUM_TOKEN_LENGTH = 8


@dataclass(frozen=True, slots=True)
class ControlLeak:
    """One control token found somewhere it must not be."""

    surface: str
    token: str
    kind: str


@dataclass(frozen=True, slots=True)
class NearClonePair:
    """Two tasks whose code is structurally the same after normalization."""

    left: str
    right: str
    reason: str


@dataclass(frozen=True, slots=True)
class CrossTaskTransfer:
    """A donor task's correction, aimed at a recipient task's file.

    The sandbox runs it. The corpus is sound only if every one of these leaves the recipient's
    hidden suite failing — a transfer that passes means the two tasks were one task.
    """

    donor_template_id: str
    recipient_template_id: str
    strategy: RealityCandidateStrategy
    path: str
    source: str
    same_family: bool


def control_tokens(task: RealityTaskManifest, item: TaskTemplate) -> frozenset[str]:
    """Everything about this task that a provider, feature or embedding must never see."""
    tokens: set[str] = {
        task.hidden_verifier_bundle_hash,
        task.control_material_manifest_hash,
        task.baseline_failure_reason,
        str(task.hidden_verifier_bundle_artifact_id),
    }
    # A control path is only secret if it is *only* in the control bundle. Both trees carry a
    # `conftest.py`, and the workspace's is a file the provider is meant to see, so treating
    # the name as a control token would report ninety leaks that are one filename collision.
    for path, text in item.control_files.items():
        if path not in item.visible_files:
            tokens.add(path)
        tokens.update(_test_function_names(text))
    for strategy in (
        RealityCandidateStrategy.CORRECT_NARROW,
        RealityCandidateStrategy.CORRECT_ROBUST,
    ):
        for source in item.candidate_sources[strategy].values():
            tokens.update(_significant_lines(source, item))
    return frozenset(token for token in tokens if len(token) >= _MINIMUM_TOKEN_LENGTH)


def scan_for_control_leaks(
    surfaces: Mapping[str, str], tokens: Iterable[str]
) -> tuple[ControlLeak, ...]:
    """Report every control token that appears in any named surface."""
    known = tuple(tokens)
    return tuple(
        ControlLeak(surface=name, token=token, kind=_token_kind(token))
        for name, text in sorted(surfaces.items())
        for token in known
        if token in text
    )


def projection_surfaces(projection: RealityTaskProjection) -> dict[str, str]:
    """Every provider-visible string a task hands out, named for reporting."""
    return {
        "projection.issue_description": projection.issue_description,
        "projection.expected_behavior": projection.expected_behavior,
        "projection.visible_test_command": " ".join(projection.visible_test_command),
        "projection.allowed_paths": " ".join(projection.allowed_paths),
        "projection.forbidden_paths": " ".join(projection.forbidden_paths),
        "projection.files": " ".join(
            f"{entry.path} {entry.file_hash}" for entry in projection.files
        ),
        "projection.serialized": projection.model_dump_json(),
    }


def lookup_key_leaks(task: RealityTaskManifest, template_id: str) -> tuple[ControlLeak, ...]:
    """A projection that names its template, seed or generator is a lookup, not a repair task."""
    keys = {
        "template_id": template_id,
        "generator_profile": task.generator_profile_id,
        "repository_group": task.repository_group,
    }
    serialized = task.projection.model_dump_json()
    return tuple(
        ControlLeak(surface="projection.serialized", token=value, kind=name)
        for name, value in sorted(keys.items())
        if value and value in serialized
    )


def normalized_structure_hash(source: str) -> str:
    """Hash the shape of the code with identifiers and literals erased.

    Two tasks that differ only in what things are called produce the same value, which is
    exactly the collision a near-clone corpus would hide behind distinct names.
    """
    tree = ast.parse(source)
    return sha256(ast.dump(_Anonymizer().visit(tree), annotate_fields=False).encode()).hexdigest()


def token_stream_hash(source: str) -> str:
    """Hash the token stream with names and literals canonicalized.

    A second opinion on top of the AST hash: it survives formatting differences the AST erases
    and catches reorderings the AST dump would treat as distinct.
    """
    pieces: list[str] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE, tokenize.ENCODING}:
            continue
        if token.type == tokenize.NAME:
            pieces.append(token.string if _is_keyword(token.string) else "N")
        elif token.type in {tokenize.NUMBER, tokenize.STRING}:
            pieces.append("L")
        elif token.string.strip():
            pieces.append(token.string)
    return sha256(" ".join(pieces).encode()).hexdigest()


def near_clone_pairs(sources: Mapping[str, str]) -> tuple[NearClonePair, ...]:
    """Report every pair of tasks that collide on either normalization."""
    structure: dict[str, list[str]] = {}
    tokens: dict[str, list[str]] = {}
    for name, source in sorted(sources.items()):
        structure.setdefault(normalized_structure_hash(source), []).append(name)
        tokens.setdefault(token_stream_hash(source), []).append(name)
    pairs: list[NearClonePair] = []
    for reason, groups in (("normalized_ast", structure), ("token_stream", tokens)):
        for members in groups.values():
            for index, left in enumerate(members):
                for right in members[index + 1 :]:
                    pairs.append(NearClonePair(left=left, right=right, reason=reason))
    return tuple(pairs)


def cross_task_transfers(
    templates: Mapping[str, TaskTemplate],
    *,
    strategy: RealityCandidateStrategy = RealityCandidateStrategy.CORRECT_NARROW,
    same_family_only: bool = True,
) -> tuple[CrossTaskTransfer, ...]:
    """Enumerate donor-to-recipient correction transfers for the sandbox to refute.

    Same-family by default because that is where a shortcut would actually live: a correction
    transferred across families lands in a file whose function is not even called by the
    recipient's tests, and refuting that would be refuting nothing.
    """
    transfers: list[CrossTaskTransfer] = []
    for donor_id, donor in sorted(templates.items()):
        donor_source = next(iter(donor.candidate_sources[strategy].values()))
        for recipient_id, recipient in sorted(templates.items()):
            if donor_id == recipient_id:
                continue
            same_family = donor.family is recipient.family
            if same_family_only and not same_family:
                continue
            transfers.append(
                CrossTaskTransfer(
                    donor_template_id=donor_id,
                    recipient_template_id=recipient_id,
                    strategy=strategy,
                    path=next(iter(recipient.candidate_sources[strategy])),
                    source=donor_source,
                    same_family=same_family,
                )
            )
    return tuple(transfers)


def duplicate_candidate_sources(
    templates: Mapping[str, TaskTemplate],
) -> tuple[NearClonePair, ...]:
    """Two tasks whose declared answer is byte-identical are one task with two names."""
    seen: dict[str, str] = {}
    duplicates: list[NearClonePair] = []
    for template_id, item in sorted(templates.items()):
        for strategy, files in sorted(
            item.candidate_sources.items(), key=lambda pair: pair[0].value
        ):
            for source in files.values():
                digest = sha256(source.encode()).hexdigest()
                previous = seen.get(digest)
                if previous is not None and previous != template_id:
                    duplicates.append(
                        NearClonePair(
                            left=previous,
                            right=template_id,
                            reason=f"identical {strategy.value} source",
                        )
                    )
                seen.setdefault(digest, template_id)
    return tuple(duplicates)


class _Anonymizer(ast.NodeTransformer):
    """Erase every name and literal, keeping only the shape."""

    def visit_Name(self, node: ast.Name) -> ast.AST:
        return ast.copy_location(ast.Name(id="_", ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.copy_location(ast.arg(arg="_", annotation=None), node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        node.name = "_"
        node.body = [item for item in node.body if not _is_docstring(item)]
        return node

    def visit_Attribute(self, node: ast.Attribute) -> ast.AST:
        self.generic_visit(node)
        node.attr = "_"
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.copy_location(ast.Constant(value=None), node)

    def visit_keyword(self, node: ast.keyword) -> ast.AST:
        self.generic_visit(node)
        node.arg = "_"
        return node


def _is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


def _is_keyword(value: str) -> bool:
    import keyword

    return keyword.iskeyword(value) or keyword.issoftkeyword(value)


def _test_function_names(text: str) -> set[str]:
    return {
        line.removeprefix("def ").split("(")[0]
        for line in text.splitlines()
        if line.startswith("def test_")
    }


def _significant_lines(source: str, item: TaskTemplate) -> set[str]:
    """Lines unique to a correction: present in the answer and absent from the baseline.

    Comparing against the baseline is what keeps the signature lines and the docstring — which
    a provider is *supposed* to see — out of the control-token set.
    """
    baseline: set[str] = set()
    for text in item.visible_files.values():
        baseline.update(line.strip() for line in text.splitlines())
    return {
        line.strip()
        for line in source.splitlines()
        if line.strip() and line.strip() not in baseline
    }


def _token_kind(token: str) -> str:
    if len(token) == 64 and all(character in "0123456789abcdef" for character in token):
        return "hash"
    if token.startswith("test_"):
        return "hidden_test_name"
    if token.endswith(".py"):
        return "control_path"
    return "golden_source_line"
