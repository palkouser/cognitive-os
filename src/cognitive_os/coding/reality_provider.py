"""Ask a real provider to repair a task, and classify what comes back, §S21C3-032.

The three providers answer the *same* task in the *same* shape, exactly as the C2 advisory
boundary does, so one deterministic path handles all of them and a receipt from one is
comparable with a receipt from another.

What a provider is shown is the task projection and nothing else. §4.13 requires the content
to be *inlined and hash-pinned* rather than referenced, and that is not a convenience: a
provider handed a path could read the control bundle, and a provider handed a repository
reference could read the answer out of the history. Everything in the prompt comes from
`RealityTaskProjection`, which is structurally incapable of carrying control material, and
`prompt_leaks` re-checks the assembled text against the task's control tokens before it is
sent — because "the type says it cannot happen" and "it did not happen" are different claims.

Four things can come back, and all four are outcomes:

* a *malformed* answer — not valid against the schema, or not a diff the patch plane can read;
* a *refusal* — the provider declined; recorded, never retried into a success;
* an *incorrect* patch — applied and executed, and the hidden suite disagreed;
* a *correct* patch — applied, executed, and the hidden suite agreed.

Only the last two reach a sandbox. The first two are recorded as what they are, because a
campaign that dropped them would report accuracy over a denominator it had quietly chosen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid5

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.reality import (
    RealityCandidateSource,
    RealityTaskManifest,
    RealityTaskProjection,
)

from .diff import apply_file_patch, parse_unified_diff

#: Fixed forever, like the offline candidate namespace: a provider answer re-recorded is the
#: same candidate rather than a new one.
REALITY_PROVIDER_NAMESPACE = UUID("5e91c7a3-40b8-5d26-b3f1-8c07e42d9165")

PROVIDER_PROFILE_ID = "reality.provider"
PROVIDER_PROFILE_VERSION = 1

#: Which adapter produced which candidate source. Nothing else may be mapped here: a source
#: outside `PROVIDER_CANDIDATE_SOURCES` would let a network answer be recorded as curated.
ADAPTER_SOURCES: dict[str, RealityCandidateSource] = {
    "openrouter": RealityCandidateSource.OPENROUTER,
    "claude_code": RealityCandidateSource.CLAUDE_CODE,
    "codex_cli": RealityCandidateSource.CODEX_CLI,
}


class ProviderOutcomeClass(StrEnum):
    """What the provider's answer was, before any question of correctness."""

    MALFORMED = "malformed"
    REFUSED = "refused"
    PATCH_PROPOSED = "patch_proposed"


class RepairPatch(ImmutableContractModel):
    """The one shape all three providers are asked for.

    `refused` is a first-class answer rather than an error. A provider that declines has told
    us something true, and forcing it to emit a diff would turn a refusal into a malformed
    answer and lose the distinction §S21C3-032 asks us to report.
    """

    refused: bool
    refusal_reason: str
    unified_diff: str
    explanation: str


REPAIR_JSON_SCHEMA: dict[str, Any] = RepairPatch.model_json_schema()


def _strict(node: Any) -> Any:
    """The strict JSON-Schema subset every structured-output backend demands.

    Same rewrite the advisory schema needs, and for the same reason C2 found the hard way:
    Pydantic omits defaulted fields from `required`, and `codex exec --output-schema`
    rejects the whole turn when it does.
    """
    if isinstance(node, dict):
        rewritten = {key: _strict(value) for key, value in node.items()}
        properties = rewritten.get("properties")
        if isinstance(properties, dict):
            rewritten["required"] = sorted(properties)
            rewritten["additionalProperties"] = False
        return rewritten
    if isinstance(node, list):
        return [_strict(item) for item in node]
    return node


STRICT_REPAIR_JSON_SCHEMA: dict[str, Any] = _strict(REPAIR_JSON_SCHEMA)


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    """One provider answer, classified. Correctness is not decided here."""

    task_id: UUID
    provider_id: str
    outcome_class: ProviderOutcomeClass
    path: str | None = None
    unified_diff: str | None = None
    patched_source: str | None = None
    reason: str | None = None

    @property
    def candidate_id(self) -> UUID:
        return uuid5(
            REALITY_PROVIDER_NAMESPACE,
            f"{self.task_id}:{self.provider_id}:{self.patch_hash or self.outcome_class.value}",
        )

    @property
    def patch_hash(self) -> str | None:
        return None if self.unified_diff is None else sha256(self.unified_diff.encode()).hexdigest()

    @property
    def executable(self) -> bool:
        return self.outcome_class is ProviderOutcomeClass.PATCH_PROPOSED


def build_prompt(projection: RealityTaskProjection, sources: dict[str, str]) -> str:
    """Everything the provider sees, inlined and hash-pinned. §4.13.

    `sources` are the provider-visible file bodies, keyed by path; each is pinned to the hash
    the projection recorded, so a provider is shown the same bytes the sandbox will run. No
    path is offered as a location to read — the whole repository is in the message or it is
    not available at all.
    """
    files = []
    for entry in projection.files:
        body = sources.get(entry.path)
        if body is None:
            continue
        files.append(f"--- FILE {entry.path} (sha256 {entry.file_hash}) ---\n{body.rstrip()}\n")
    allowed = ", ".join(projection.allowed_paths) or "(none declared)"
    forbidden = ", ".join(projection.forbidden_paths) or "(none declared)"
    return "\n".join(
        (
            "Repair the defect described below.",
            "",
            f"ISSUE: {projection.issue_description}",
            f"EXPECTED BEHAVIOUR: {projection.expected_behavior}",
            "",
            f"The published test command is: {' '.join(projection.visible_test_command)}",
            "The published tests already pass on this code. They do not cover the defect.",
            "Fix the behaviour the issue describes, not only what the tests check.",
            "",
            f"You may edit: {allowed}",
            f"You must not edit: {forbidden}",
            "",
            "Reply with a unified diff against the files below, with a `diff --git` header.",
            "Change exactly one file. If you will not answer, set refused and say why.",
            "",
            *files,
        )
    )


def prompt_leaks(prompt: str, tokens: frozenset[str]) -> tuple[str, ...]:
    """Control tokens present in an assembled prompt. Must be empty before sending.

    The projection type cannot carry control material, and this checks the rendered text
    anyway. The two are not the same claim: the prompt is assembled from more than the
    projection, and the cost of being wrong is the answer key in a network request.
    """
    return tuple(sorted(token for token in tokens if token in prompt))


def classify(
    answer: RepairPatch,
    *,
    task: RealityTaskManifest,
    provider_id: str,
    sources: dict[str, str],
) -> ProviderCandidate:
    """Turn one provider answer into a candidate, or say why it is not one.

    A diff that does not apply is malformed, not incorrect. The distinction matters for the
    denominator: an unreadable answer says something about the provider's output format, and
    an applied patch that fails the hidden suite says something about its repair ability.
    """
    if answer.refused:
        return ProviderCandidate(
            task_id=task.task_id,
            provider_id=provider_id,
            outcome_class=ProviderOutcomeClass.REFUSED,
            reason=answer.refusal_reason.strip() or "provider refused without a reason",
        )
    diff = answer.unified_diff.strip()
    if not diff:
        return _malformed(task, provider_id, "the answer declared a patch but carried no diff")
    try:
        parsed = parse_unified_diff(diff if diff.endswith("\n") else diff + "\n")
    except Exception as error:  # every parse failure is the same finding here
        return _malformed(task, provider_id, f"unreadable diff: {error}")
    if len(parsed) != 1:
        return _malformed(task, provider_id, f"expected one changed file, got {len(parsed)}")

    target = parsed[0].new_path
    if target is None:
        # A deletion, or a header the parser could not resolve to a destination. Either way
        # there is no file to run the hidden suite against.
        return _malformed(task, provider_id, "the diff names no destination file")
    before = sources.get(target)
    if before is None:
        return _malformed(task, provider_id, f"patch targets {target!r}, which was not shown")
    if _is_forbidden(target, task.projection):
        return _malformed(task, provider_id, f"patch targets forbidden path {target!r}")
    try:
        applied = apply_file_patch(before.encode(), parsed[0])
    except Exception as error:
        # `apply_file_patch` raises on a context mismatch rather than returning `None`, so a
        # campaign that only checked for `None` would crash on the commonest provider mistake
        # instead of recording it. Every apply failure is the same finding: malformed.
        return _malformed(task, provider_id, f"the diff does not apply: {error}")
    if applied is None:
        return _malformed(task, provider_id, "the diff does not apply to the source it was given")
    try:
        patched = applied.decode()
    except UnicodeDecodeError:
        return _malformed(task, provider_id, "the patched file is not valid UTF-8")
    return ProviderCandidate(
        task_id=task.task_id,
        provider_id=provider_id,
        outcome_class=ProviderOutcomeClass.PATCH_PROPOSED,
        path=target,
        unified_diff=diff,
        patched_source=patched,
    )


def _malformed(task: RealityTaskManifest, provider_id: str, reason: str) -> ProviderCandidate:
    return ProviderCandidate(
        task_id=task.task_id,
        provider_id=provider_id,
        outcome_class=ProviderOutcomeClass.MALFORMED,
        reason=reason,
    )


def _is_forbidden(path: str, projection: RealityTaskProjection) -> bool:
    return any(
        path == item or path.startswith(f"{item.rstrip('/')}/")
        for item in projection.forbidden_paths
    )


def assignment(template_ids: tuple[str, ...], providers: tuple[str, ...]) -> dict[str, str]:
    """Freeze which provider gets which task, before anything is executed. §4.13.

    Derived from the template ID rather than shuffled, so the assignment is the same on a
    resumed campaign and cannot be chosen after seeing which tasks a provider got right.
    """
    ordered = sorted(template_ids)
    return {
        template_id: providers[index % len(providers)] for index, template_id in enumerate(ordered)
    }


PROVIDER_SYSTEM_INSTRUCTIONS: NonEmptyStr = (
    "You are repairing a small Python defect. Reply only with the requested JSON object. "
    "Do not ask questions and do not request additional files: everything available is in "
    "the message."
)
