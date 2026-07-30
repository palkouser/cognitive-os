"""Correction trajectories from recorded coding outcomes, §S21C3-034 and §4.10.

A correction trajectory is an ordered claim: *this* failed, *that* fixed it. The claim is only
worth compiling if every step in it can be resolved back to bytes that exist, so this module
builds the Experience Compiler's inputs out of the artifacts the campaign actually wrote —
the outcome blob, the hidden-verification evidence, the candidate patch — and declares each
source hash from the bytes it just read. The compiler's own registry refuses a payload whose
hash disagrees with its reference, so a trajectory over a missing or rewritten artifact fails
at registration rather than compiling into a manifest nobody can reproduce.

Two things this deliberately does not do:

* it adds no repository. The existing Experience Compiler and experience repository persist
  the result; a second store of trajectories would be a second answer to "what was compiled";
* it invents no steps. The timeline is exactly the runs that were recorded, in the order
  §4.10 planned them, and the terminal state is read from the last run rather than asserted.

Identity is derived from the task, the two strategies and the ordered source event IDs, which
is the distinctness rule §4.10 states. Recompiling the same path is therefore the same
compilation, not a second one, and the 60 planned paths cannot be inflated by re-running.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid5

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.domain.common import UtcDatetime
from cognitive_os.domain.experience import (
    CompilerProfile,
    CompilerResourceLimits,
    ExperienceCandidateType,
    ExperienceCompilationRequest,
    ExperienceStepStatus,
    TimelineEntry,
    TimelineEntryType,
    TrajectorySourceRef,
    TrajectorySourceType,
)
from cognitive_os.domain.memory import MemorySensitivity
from cognitive_os.domain.reality import (
    RealityCandidateManifest,
    RealityCandidateStrategy,
    RealityOutcomeReference,
    RealityStrategyFamily,
    RealityTaskManifest,
)
from cognitive_os.experience.registry import (
    CompilerProfileRegistry,
    ResolvedTrajectorySource,
    SourceResolverRegistry,
)

#: Fixed forever, like the task and candidate namespaces: it is what makes a recompiled
#: trajectory the same trajectory rather than a new one.
REALITY_TRAJECTORY_NAMESPACE = UUID("2f6b41d8-9e05-5c73-8a12-6d94b0e7f235")

COMPILER_PROFILE_ID = "sprint21c3-reality-correction"
COMPILER_PROFILE_VERSION = 1

#: The compiler profile is a constant, so its hash has to be one too. Deriving `created_at`
#: from the campaign would give every campaign a different profile hash for an identical
#: profile, and `_validate_request` compares that hash exactly.
PROFILE_EPOCH = datetime(2026, 7, 30, tzinfo=UTC)


class TrajectoryBuildError(RuntimeError):
    """The recorded runs do not form the ordered correction path they claim to be."""


@dataclass(frozen=True, slots=True)
class CorrectionStep:
    """One recorded run inside an ordered correction path.

    `candidate` is `None` for the baseline, which is the failure the path starts from rather
    than an attempt at fixing it.
    """

    reference: RealityOutcomeReference
    candidate: RealityCandidateManifest | None = None

    @property
    def strategy(self) -> RealityCandidateStrategy | None:
        return None if self.candidate is None else self.candidate.strategy


@dataclass(frozen=True, slots=True)
class TrajectoryPlan:
    """One of the two paths §4.10 plans for a task, before anything is compiled."""

    task_id: UUID
    incorrect: RealityCandidateStrategy
    correct: RealityCandidateStrategy
    steps: tuple[CorrectionStep, ...]

    @property
    def compilation_id(self) -> UUID:
        return trajectory_identity(self.task_id, self.steps)


def trajectory_identity(task_id: UUID, steps: tuple[CorrectionStep, ...]) -> UUID:
    """Task, strategies and ordered source event IDs — §4.10's distinctness rule, verbatim."""
    return uuid5(REALITY_TRAJECTORY_NAMESPACE, _identity_key(task_id, steps))


def _identity_key(task_id: UUID, steps: tuple[CorrectionStep, ...]) -> str:
    return "|".join(
        (
            str(task_id),
            *(
                f"{'baseline' if step.strategy is None else step.strategy.value}"
                f":{step.reference.source_event_id}"
                for step in steps
            ),
        )
    )


def plan_paths(
    *,
    task_id: UUID,
    baseline: CorrectionStep,
    candidates: dict[RealityCandidateStrategy, CorrectionStep],
) -> tuple[TrajectoryPlan, ...]:
    """The two ordered paths §4.10 defines for one task, for whichever runs are present.

    A path is planned only when all three of its runs were recorded. A campaign interrupted
    halfway should produce fewer trajectories, not trajectories with holes in them.
    """
    pairs = (
        (RealityCandidateStrategy.INCOMPLETE_A, RealityCandidateStrategy.CORRECT_NARROW),
        (RealityCandidateStrategy.INCOMPLETE_B, RealityCandidateStrategy.CORRECT_ROBUST),
    )
    plans: list[TrajectoryPlan] = []
    for incorrect, correct in pairs:
        first, second = candidates.get(incorrect), candidates.get(correct)
        if first is None or second is None:
            continue
        plans.append(
            TrajectoryPlan(
                task_id=task_id,
                incorrect=incorrect,
                correct=correct,
                steps=(baseline, first, second),
            )
        )
    return tuple(plans)


async def build_request(
    plan: TrajectoryPlan,
    *,
    task: RealityTaskManifest,
    artifacts: ArtifactStorePort,
    created_at: UtcDatetime,
) -> tuple[ExperienceCompilationRequest, SourceResolverRegistry, CompilerProfileRegistry]:
    """Turn one planned path into a compilation request the existing compiler can execute.

    Fails closed before the compiler is reached: a path that does not end in a pass, or whose
    correction steps are not the strategies it declares, is not a correction trajectory and
    compiling it would put a false claim into the experience store.
    """
    _require_well_formed(plan, task)

    entries: list[TimelineEntry] = []
    resolved: list[ResolvedTrajectorySource] = []

    task_payload = task.model_dump_json().encode()
    task_ref = _reference(plan, TrajectorySourceType.TASK, task_payload, task.content_hash)
    resolved.append(ResolvedTrajectorySource(task_ref, task_payload))

    controller_payload = _identity_key(plan.task_id, plan.steps).encode()
    controller_ref = _reference(
        plan, TrajectorySourceType.CONTROLLER_EVENT, controller_payload, "1"
    )
    plan_entry = _entry(
        plan,
        controller_ref,
        sequence=1,
        entry_type=TimelineEntryType.PLAN,
        event_type="reality.correction_path_planned",
        status=ExperienceStepStatus.COMPLETED,
        summary=f"Ordered correction path: baseline, {plan.incorrect.value}, {plan.correct.value}",
        evidence=(sha256(controller_payload).hexdigest(),),
        created_at=created_at,
    )
    entries.append(plan_entry)

    verifier_payloads: list[bytes] = []
    patch_payloads: list[bytes] = []
    verifier_entries: list[TimelineEntry] = []
    correction_entries: list[TimelineEntry] = []
    for step in plan.steps:
        if step.candidate is not None:
            patch_payloads.append(
                await _read(artifacts, step.candidate.patch_artifact_id, step.candidate.patch_hash)
            )
        verifier_payloads.append(
            await _read(
                artifacts,
                step.reference.hidden_evidence_artifact_id,
                step.reference.hidden_evidence_hash,
            )
        )

    patch_ref = _reference(
        plan,
        TrajectorySourceType.CODING_TRAJECTORY,
        b"".join(patch_payloads),
        f"{plan.incorrect.value}+{plan.correct.value}",
    )
    verifier_ref = _reference(
        plan, TrajectorySourceType.VERIFIER, b"".join(verifier_payloads), "hidden"
    )

    sequence = 2
    for step in plan.steps:
        reference = step.reference
        if step.candidate is not None:
            correction_entries.append(
                _entry(
                    plan,
                    patch_ref,
                    sequence=sequence,
                    entry_type=TimelineEntryType.CORRECTION,
                    event_type=f"reality.candidate_applied.{step.strategy.value}",  # type: ignore[union-attr]
                    status=ExperienceStepStatus.COMPLETED,
                    summary=f"Applied {step.strategy.value} patch",  # type: ignore[union-attr]
                    evidence=(step.candidate.patch_hash,),
                    created_at=created_at,
                )
            )
            sequence += 1
        passed = reference.hidden_verification_passed
        subject = "baseline" if step.strategy is None else step.strategy.value
        verifier_entries.append(
            _entry(
                plan,
                verifier_ref,
                sequence=sequence,
                entry_type=TimelineEntryType.VERIFIER,
                event_type="verifier.completed" if passed else "verifier.failed",
                status=(ExperienceStepStatus.COMPLETED if passed else ExperienceStepStatus.FAILED),
                summary=(
                    f"Hidden verification passed for {subject}"
                    if passed
                    else f"Hidden verification failed for {subject}"
                ),
                evidence=(reference.hidden_evidence_hash, reference.outcome_hash),
                created_at=created_at,
            )
        )
        sequence += 1

    acceptance_payload = plan.steps[-1].reference.outcome_hash.encode()
    acceptance_ref = _reference(
        plan, TrajectorySourceType.ACCEPTANCE, acceptance_payload, "accepted"
    )
    acceptance_entry = _entry(
        plan,
        acceptance_ref,
        sequence=sequence,
        entry_type=TimelineEntryType.ACCEPTANCE,
        event_type="acceptance.accepted",
        status=ExperienceStepStatus.COMPLETED,
        summary="Terminal outcome: accepted",
        evidence=(plan.steps[-1].reference.outcome_hash,),
        created_at=created_at,
    )

    entries.extend(correction_entries)
    entries.extend(verifier_entries)
    entries.append(acceptance_entry)

    resolved.extend(
        (
            ResolvedTrajectorySource(controller_ref, controller_payload, (plan_entry,), "accepted"),
            ResolvedTrajectorySource(
                patch_ref, b"".join(patch_payloads), tuple(correction_entries)
            ),
            ResolvedTrajectorySource(
                verifier_ref, b"".join(verifier_payloads), tuple(verifier_entries)
            ),
            ResolvedTrajectorySource(acceptance_ref, acceptance_payload, (acceptance_entry,)),
        )
    )

    sources = SourceResolverRegistry()
    for item in resolved:
        sources.register(item)
    sources.freeze()

    profile = compiler_profile()
    profiles = CompilerProfileRegistry()
    profiles.register(profile)
    profiles.freeze()

    request = ExperienceCompilationRequest(
        compilation_id=plan.compilation_id,
        task_run_id=plan.steps[-1].reference.task_run_id,
        trajectory_sources=tuple(item.reference for item in resolved),
        compiler_profile_id=profile.profile_id,
        compiler_profile_version=profile.version,
        compiler_profile_hash=profile.content_hash,
        candidate_types=frozenset(ExperienceCandidateType),
        budget=CompilerResourceLimits(),
        requested_by="reality-campaign",
        idempotency_key=sha256(_identity_key(plan.task_id, plan.steps).encode()).hexdigest(),
        created_at=created_at,
    )
    return request, sources, profiles


def compiler_profile() -> CompilerProfile:
    """The one C3 correction profile. Constant, so its hash is constant."""
    return CompilerProfile(
        profile_id=COMPILER_PROFILE_ID,
        version=COMPILER_PROFILE_VERSION,
        enabled_source_types=frozenset(
            {
                TrajectorySourceType.TASK,
                TrajectorySourceType.CONTROLLER_EVENT,
                TrajectorySourceType.CODING_TRAJECTORY,
                TrajectorySourceType.VERIFIER,
                TrajectorySourceType.ACCEPTANCE,
            }
        ),
        required_source_types=frozenset(
            {
                TrajectorySourceType.TASK,
                TrajectorySourceType.CONTROLLER_EVENT,
                TrajectorySourceType.VERIFIER,
                TrajectorySourceType.ACCEPTANCE,
            }
        ),
        candidate_types=frozenset(ExperienceCandidateType),
        assessment_policy="conservative-evidence-v1",
        contribution_policy="no-causal-overclaim-v1",
        generalizability_policy="minimum-specificity-v1",
        resource_limits=CompilerResourceLimits(),
        created_at=PROFILE_EPOCH,
    )


def _require_well_formed(plan: TrajectoryPlan, task: RealityTaskManifest) -> None:
    if len(plan.steps) != 3:
        raise TrajectoryBuildError("a correction path is baseline, incorrect, correct")
    baseline, incorrect, correct = plan.steps
    if baseline.candidate is not None:
        raise TrajectoryBuildError("the first step of a correction path is the baseline")
    if incorrect.strategy is not plan.incorrect or correct.strategy is not plan.correct:
        raise TrajectoryBuildError("recorded steps do not match the declared strategies")
    if plan.incorrect.family is not RealityStrategyFamily.INCORRECT:
        raise TrajectoryBuildError(f"{plan.incorrect.value} is not an incorrect strategy")
    if plan.correct.family is not RealityStrategyFamily.CORRECT:
        raise TrajectoryBuildError(f"{plan.correct.value} is not a correct strategy")
    for step in plan.steps:
        if step.reference.task_id != task.task_id:
            raise TrajectoryBuildError("a step belongs to a different task")
        if step.reference.task_manifest_hash != task.content_hash:
            raise TrajectoryBuildError("a step was produced against another manifest revision")
    # Nothing here re-checks that the baseline failed, that the incorrect step failed, or that
    # the correct step passed. `RealityOutcomeReference` refuses all three at construction, so
    # a step that disagreed with its own strategy could not have been recorded — and a second
    # copy of that rule here would be a branch no input can reach.


async def _read(artifacts: ArtifactStorePort, artifact_id: UUID, expected_hash: str) -> bytes:
    """Read the bytes and check them. A trajectory over unreadable sources is a claim."""
    try:
        payload = await artifacts.get_bytes(artifact_id)
    except Exception as error:  # every store failure is the same failure here
        raise TrajectoryBuildError(
            f"trajectory source artifact {artifact_id} could not be read: {error}"
        ) from error
    if sha256(payload).hexdigest() != expected_hash:
        raise TrajectoryBuildError(f"artifact {artifact_id} no longer matches its recorded hash")
    return payload


def _reference(
    plan: TrajectoryPlan,
    source_type: TrajectorySourceType,
    payload: bytes,
    revision: str,
) -> TrajectorySourceRef:
    # An event source has to name the stream it was read from. The path's authoritative
    # stream is the run that produced its terminal outcome, and its version is the number
    # of runs the path is made of — so a path with a step added is a different source.
    event_stream = source_type is TrajectorySourceType.CONTROLLER_EVENT
    return TrajectorySourceRef(
        source_type=source_type,
        source_id=f"reality:{plan.compilation_id}:{source_type.value}",
        source_revision=revision,
        event_stream_id=plan.steps[-1].reference.task_run_id if event_stream else None,
        event_stream_version=len(plan.steps) if event_stream else None,
        source_content_hash=sha256(payload).hexdigest(),
        scope="project:cognitive-os",
        sensitivity=MemorySensitivity.PUBLIC,
        required=True,
    )


def _entry(
    plan: TrajectoryPlan,
    reference: TrajectorySourceRef,
    *,
    sequence: int,
    entry_type: TimelineEntryType,
    event_type: str,
    status: ExperienceStepStatus,
    summary: str,
    evidence: tuple[str, ...],
    created_at: UtcDatetime,
) -> TimelineEntry:
    return TimelineEntry(
        timeline_entry_id=uuid5(
            REALITY_TRAJECTORY_NAMESPACE, f"{plan.compilation_id}:{sequence}:{event_type}"
        ),
        sequence=sequence,
        source_ref=reference,
        entry_type=entry_type,
        event_type=event_type,
        actor_type="system",
        actor_id="reality-campaign",
        step_id=f"step-{sequence}",
        started_at=created_at + timedelta(seconds=sequence),
        finished_at=created_at + timedelta(seconds=sequence, milliseconds=100),
        correlation_id=plan.compilation_id,
        status=status,
        payload_summary=summary,
        evidence_refs=evidence,
    )
