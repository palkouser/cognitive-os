"""Offline candidate patches and manifests, §S21C3-030.

Each of the thirty tasks gets four candidates, and each candidate is a *unified diff* rather
than a file drop. That matters for two reasons: the diff is what the existing patch plane
consumes, so a candidate travels the same road a provider's answer will; and a diff that does
not apply is a candidate that never ran, which the campaign has to be able to tell apart from
a candidate that ran and failed.

Identity is derived, never allocated. `candidate_id` is a uuid5 over the task and the strategy,
so regenerating the corpus produces the same 120 candidates rather than 120 new ones — and a
campaign resumed against a regenerated corpus recognises its own completed work.

The manifests carry no expected result. `strategy` records what the generator was aiming at;
whether it hit is the hidden verifier's answer and lives in the outcome.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import unified_diff
from hashlib import sha256
from random import Random
from uuid import UUID, uuid5

from cognitive_os.domain.common import UtcDatetime
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityTaskManifest,
)

from .diff import apply_file_patch, parse_unified_diff
from .reality_tasks import GENERATOR_PROFILE_ID, GENERATOR_PROFILE_VERSION, TaskTemplate, template

#: Fixed forever, like the task namespace: it is what makes a regenerated candidate the same
#: candidate.
REALITY_CANDIDATE_NAMESPACE = UUID("0b8c5f31-7a24-5d6e-9c18-4f37b2ae61d0")

CANDIDATE_PATCH_MEDIA_TYPE = "text/x-diff"


class CandidateGenerationError(RuntimeError):
    """The generated diff does not reproduce the candidate it claims to be."""


@dataclass(frozen=True, slots=True)
class GeneratedCandidate:
    """One candidate: the diff that produces it, and the identity that names it."""

    task_id: UUID
    candidate_id: UUID
    strategy: RealityCandidateStrategy
    path: str
    unified_diff: str

    @property
    def patch_hash(self) -> str:
        return sha256(self.unified_diff.encode()).hexdigest()


def candidate_id_for(task_id: UUID, strategy: RealityCandidateStrategy) -> UUID:
    return uuid5(REALITY_CANDIDATE_NAMESPACE, f"{task_id}:{strategy.value}")


def opaque_candidate_id(task_id: UUID, *, campaign_seed: int, position: int) -> UUID:
    """A candidate identity derived from its position, not from the recipe that built it.

    S21D2-021. `candidate_id_for` derives the UUID from the strategy value, so a candidate ID
    is a reversible encoding of the recipe: anyone holding the task ID can recompute all four
    and read off which is which. That is harmless while the corpus makes no claim about its
    recipes, and it is a leak the moment a ranker is fitted on the corpus — a per-task
    constant that identifies the label without ever appearing in the feature schema.

    Positions come from `shuffled_recipe_positions`, so the mapping is fixed and replayable
    from a recorded seed but is not derivable from the identity alone.
    """
    if position < 0:
        raise ValueError("a candidate position is a zero-based index")
    return uuid5(REALITY_CANDIDATE_NAMESPACE, f"{task_id}:d2:{campaign_seed}:{position}")


def shuffled_recipe_positions(
    task_id: UUID,
    recipes: Sequence[RealityCandidateStrategy],
    *,
    campaign_seed: int,
) -> tuple[RealityCandidateStrategy, ...]:
    """Deterministically permute the recipes for one task, from a recorded campaign seed.

    Without this, position zero is the same recipe in every task and the ranker's first slot
    carries a constant prior. `Random` is seeded per task so two tasks in one campaign shuffle
    differently while either replays exactly.
    """
    if len(set(recipes)) != len(recipes):
        raise ValueError("a task cannot generate the same recipe twice")
    ordered = list(recipes)
    # nosec B311 - a replayable permutation, not a secret. Cryptographic randomness would be
    # the wrong tool here: the whole requirement is that a recorded seed reproduces the order.
    Random(f"{task_id}:{campaign_seed}").shuffle(ordered)  # nosec B311
    return tuple(ordered)


def build_candidate(
    task: RealityTaskManifest,
    strategy: RealityCandidateStrategy,
    *,
    candidate_id: UUID | None = None,
) -> GeneratedCandidate:
    """Produce the diff from the task's baseline to one candidate, and check it applies.

    The check is not ceremony. A candidate whose diff does not reproduce its own declared
    source would be recorded as an executed outcome for source nobody ran, and the corpus
    would carry an answer that was never tested.

    `candidate_id` overrides the derived identity, and D2 always supplies it: the sealed
    catalogue named every candidate by its position before anything ran, and re-deriving one
    from the recipe here would put the reversible C3 encoding back on top of the opaque ID the
    seal committed to. Absent, the C3 derivation is unchanged.
    """
    item = template(_template_id_of(task))
    path = next(iter(item.sources(strategy)))
    before = item.visible_files[path]
    after = item.sources(strategy)[path]
    body = "".join(
        unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )
    # `difflib` emits the file headers but not the `diff --git` line the repository's parser
    # keys on, so a candidate built without it would be a diff the patch plane cannot read.
    diff = f"diff --git a/{path} b/{path}\n{body}" if body else ""
    if not diff:
        raise CandidateGenerationError(
            f"candidate {strategy.value} for {task.task_id} changes nothing"
        )
    parsed = parse_unified_diff(diff)
    if len(parsed) != 1 or parsed[0].new_path != path:
        raise CandidateGenerationError(f"candidate {strategy.value} does not patch {path!r}")
    applied = apply_file_patch(before.encode(), parsed[0])
    if applied is None or applied.decode() != after:
        raise CandidateGenerationError(
            f"candidate {strategy.value} for {task.task_id} does not reproduce its own source"
        )
    return GeneratedCandidate(
        task_id=task.task_id,
        candidate_id=candidate_id or candidate_id_for(task.task_id, strategy),
        strategy=strategy,
        path=path,
        unified_diff=diff,
    )


def build_manifest(
    task: RealityTaskManifest,
    candidate: GeneratedCandidate,
    *,
    patch_artifact_id: UUID,
    created_at: UtcDatetime,
) -> RealityCandidateManifest:
    """Bind one candidate to its task, its patch bytes and the profile that produced it."""
    if candidate.task_id != task.task_id:
        raise CandidateGenerationError("candidate belongs to a different task")
    return RealityCandidateManifest(
        candidate_id=candidate.candidate_id,
        task_id=task.task_id,
        task_manifest_hash=task.content_hash,
        strategy=candidate.strategy,
        source=RealityCandidateSource.CURATED,
        patch_artifact_id=patch_artifact_id,
        patch_hash=candidate.patch_hash,
        generator_profile_id=GENERATOR_PROFILE_ID,
        generator_profile_version=GENERATOR_PROFILE_VERSION,
        created_at=created_at,
    )


def candidate_source(task: RealityTaskManifest, strategy: RealityCandidateStrategy) -> str:
    """The full file text one candidate produces, for callers that write rather than patch."""
    item = template(_template_id_of(task))
    return next(iter(item.sources(strategy).values()))


def baseline_source(task: RealityTaskManifest) -> str:
    item = template(_template_id_of(task))
    return item.visible_files[_source_path(item)]


def _source_path(item: TaskTemplate) -> str:
    """The one file every candidate of this task replaces.

    Read off whichever recipe comes first rather than off `correct_narrow`: a D2 template's
    candidates are keyed by the neutral recipes, so naming a C3 strategy here would raise a
    `KeyError` on half the corpus. Every candidate of a template patches the same path, which
    `build_candidate` verifies per candidate, so the first one answers for all four.
    """
    return next(iter(next(iter(item.candidate_sources.values()))))


def _template_id_of(task: RealityTaskManifest) -> str:
    """Recover the template a manifest came from, without storing it in the projection.

    The template ID is in `rights.source_identity` because that is where the corpus records
    what the material *is*. Putting it in the provider-visible projection would hand a
    provider a lookup key into the generator, which §4.12 forbids as a corpus shortcut.
    """
    prefix = "cognitive-os:generated:"
    identity = task.rights.source_identity
    if not identity.startswith(prefix):
        raise CandidateGenerationError(f"task {task.task_id} was not produced by this generator")
    return identity.removeprefix(prefix)
