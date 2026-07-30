"""S21C3-034 and S21C3-035: what the downstream planes must refuse, and how a group is kept.

Whether a trajectory *compiles* is a question for the Experience Compiler and a container;
`tests/integration/coding/test_reality_downstream_slice.py` asks it. What is asked here is
the cheaper and more dangerous half: what a correction path must refuse to be, and whether
one task's material stays in one split.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.coding import reality_corpus_items, reality_trajectories
from cognitive_os.coding.hidden_verification import HiddenVerificationStatus
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_trajectories import CorrectionStep, TrajectoryBuildError
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.reality import RealityCandidateStrategy
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.memory_store import MemoryEventStore

from .reality_fixtures import (
    FIXTURE_TIME,
    InMemoryArtifactStore,
    candidate_manifest,
    coding_outcome,
    hidden_evidence,
    task_manifest,
)

BASELINE = None
PATH_A = (RealityCandidateStrategy.INCOMPLETE_A, RealityCandidateStrategy.CORRECT_NARROW)
PATH_B = (RealityCandidateStrategy.INCOMPLETE_B, RealityCandidateStrategy.CORRECT_ROBUST)


class _Recorded:
    """Three recorded runs for one task, with real patch bytes behind every candidate."""

    def __init__(self) -> None:
        self.artifacts = InMemoryArtifactStore()
        self.events = MemoryEventStore()
        self.recorder = CodingOutcomeRecorder(
            self.artifacts, CodingEventService(self.events), self.events
        )
        self.task = task_manifest()

    async def run(
        self, strategy: RealityCandidateStrategy | None, *, passed: bool
    ) -> CorrectionStep:
        task_run_id = uuid4()
        candidate = None
        if strategy is not None:
            patch = await self.artifacts.put_bytes(
                f"diff --git a/src/stats.py b/src/stats.py\n{strategy.value}\n".encode(),
                media_type="text/x-diff",
            )
            candidate = candidate_manifest(self.task, strategy).model_copy(
                update={
                    "patch_artifact_id": patch.artifact_id,
                    "patch_hash": patch.content_hash,
                }
            )
        recorded = await self.recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=(CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED),
                marker=strategy.value if strategy else "baseline",
            ),
            task=self.task,
            evidence=hidden_evidence(
                task=self.task,
                task_run_id=task_run_id,
                status=(
                    HiddenVerificationStatus.PASSED if passed else HiddenVerificationStatus.FAILED
                ),
            ),
            candidate=candidate,
            correlation_id=task_run_id,
        )
        return CorrectionStep(reference=recorded.reference, candidate=candidate)


async def _path(*, correct_passed: bool = True) -> tuple[_Recorded, dict[str, CorrectionStep]]:
    recorded = _Recorded()
    steps = {
        "baseline": await recorded.run(BASELINE, passed=False),
        "incomplete": await recorded.run(RealityCandidateStrategy.INCOMPLETE_A, passed=False),
        "correct": await recorded.run(
            RealityCandidateStrategy.CORRECT_NARROW, passed=correct_passed
        ),
    }
    return recorded, steps


def _plan(task_id, steps: tuple[CorrectionStep, ...]):  # type: ignore[no-untyped-def]
    return reality_trajectories.TrajectoryPlan(
        task_id=task_id, incorrect=PATH_A[0], correct=PATH_A[1], steps=steps
    )


# ------------------------------------------------------------------------- S21C3-034


def test_the_two_planned_paths_are_the_two_section_four_ten_defines() -> None:
    task = task_manifest()
    baseline = CorrectionStep(reference=_stub_reference(task))
    candidates = {
        strategy: CorrectionStep(reference=_stub_reference(task)) for strategy in (*PATH_A, *PATH_B)
    }

    plans = reality_trajectories.plan_paths(
        task_id=task.task_id, baseline=baseline, candidates=candidates
    )

    assert [(item.incorrect, item.correct) for item in plans] == [PATH_A, PATH_B]


def test_a_path_missing_one_of_its_runs_is_not_planned() -> None:
    """An interrupted campaign yields fewer trajectories, never trajectories with holes."""
    task = task_manifest()
    baseline = CorrectionStep(reference=_stub_reference(task))

    plans = reality_trajectories.plan_paths(
        task_id=task.task_id,
        baseline=baseline,
        candidates={PATH_A[0]: CorrectionStep(reference=_stub_reference(task))},
    )

    assert plans == ()


@pytest.mark.asyncio
async def test_identity_is_derived_from_the_task_strategies_and_ordered_events() -> None:
    recorded, steps = await _path()
    plan = _plan(recorded.task.task_id, (steps["baseline"], steps["incomplete"], steps["correct"]))

    first, _, _ = await reality_trajectories.build_request(
        plan, task=recorded.task, artifacts=recorded.artifacts, created_at=FIXTURE_TIME
    )
    second, _, _ = await reality_trajectories.build_request(
        plan, task=recorded.task, artifacts=recorded.artifacts, created_at=FIXTURE_TIME
    )

    assert first.compilation_id == second.compilation_id
    assert first.idempotency_key == second.idempotency_key


@pytest.mark.asyncio
async def test_a_correction_that_did_not_pass_never_becomes_a_recorded_step() -> None:
    """'Corrected' is a claim about an execution, and it fails one plane earlier than this.

    The trajectory builder does not need a rule against a correct strategy that failed,
    because `RealityOutcomeReference` refuses to exist in that state: such a run cannot be
    recorded, so it can never be offered as the last step of a correction path.
    """
    with pytest.raises(ValueError, match="declared correct but failed"):
        await _path(correct_passed=False)


@pytest.mark.asyncio
async def test_a_path_that_starts_from_a_pass_is_refused() -> None:
    recorded, steps = await _path()
    plan = _plan(recorded.task.task_id, (steps["correct"], steps["incomplete"], steps["correct"]))

    with pytest.raises(TrajectoryBuildError, match="first step of a correction path"):
        await reality_trajectories.build_request(
            plan, task=recorded.task, artifacts=recorded.artifacts, created_at=FIXTURE_TIME
        )


@pytest.mark.asyncio
async def test_a_missing_source_artifact_fails_closed() -> None:
    """A trajectory over bytes nobody can read is a claim, not a compilation."""
    recorded, steps = await _path()
    plan = _plan(recorded.task.task_id, (steps["baseline"], steps["incomplete"], steps["correct"]))
    recorded.artifacts.forget(steps["correct"].reference.hidden_evidence_artifact_id)

    with pytest.raises(TrajectoryBuildError, match="could not be read"):
        await reality_trajectories.build_request(
            plan, task=recorded.task, artifacts=recorded.artifacts, created_at=FIXTURE_TIME
        )


@pytest.mark.asyncio
async def test_a_changed_source_artifact_fails_closed() -> None:
    recorded, steps = await _path()
    plan = _plan(recorded.task.task_id, (steps["baseline"], steps["incomplete"], steps["correct"]))
    recorded.artifacts.corrupt(steps["incomplete"].reference.outcome_artifact_id)
    recorded.artifacts.corrupt(steps["incomplete"].reference.hidden_evidence_artifact_id)

    with pytest.raises(TrajectoryBuildError, match="no longer matches"):
        await reality_trajectories.build_request(
            plan, task=recorded.task, artifacts=recorded.artifacts, created_at=FIXTURE_TIME
        )


@pytest.mark.asyncio
async def test_a_step_from_another_manifest_revision_is_refused() -> None:
    recorded, steps = await _path()
    plan = _plan(recorded.task.task_id, (steps["baseline"], steps["incomplete"], steps["correct"]))

    with pytest.raises(TrajectoryBuildError, match="another manifest revision"):
        await reality_trajectories.build_request(
            plan,
            task=task_manifest(task_id=recorded.task.task_id, seed=99),
            artifacts=recorded.artifacts,
            created_at=FIXTURE_TIME,
        )


def test_the_compiler_profile_hash_is_a_constant() -> None:
    """A profile whose hash moved would make every recompilation a different compilation."""
    assert (
        reality_trajectories.compiler_profile().content_hash
        == reality_trajectories.compiler_profile().content_hash
    )


# ------------------------------------------------------------------------- S21C3-035


def test_the_task_package_and_its_corrections_declare_the_same_group() -> None:
    """§4.12: the split follows the repository group, never the individual item."""
    task = task_manifest()
    package = reality_corpus_items.task_package_request(task, created_at=FIXTURE_TIME)

    assert package.split_group_key == task.repository_group
    assert task.repository_group in package.scope


def test_corpus_requests_are_derived_so_a_re_ingest_is_the_same_request() -> None:
    task = task_manifest()

    first = reality_corpus_items.task_package_request(task, created_at=FIXTURE_TIME)
    second = reality_corpus_items.task_package_request(task, created_at=FIXTURE_TIME)

    assert first.request_id == second.request_id
    assert first.content_hash == second.content_hash


def test_self_play_material_is_public_and_carries_the_project_licence() -> None:
    task = task_manifest()
    package = reality_corpus_items.task_package_request(task, created_at=FIXTURE_TIME)

    assert package.sensitivity.value == "public"
    assert package.license_identifiers == ("Apache-2.0",)
    assert package.created_by == reality_corpus_items.CORPUS_ACTOR


def _stub_reference(task):  # type: ignore[no-untyped-def]
    from cognitive_os.domain.reality import RealityOutcomeReference, RealityRunKind

    from .reality_fixtures import digest

    run = uuid4()
    return RealityOutcomeReference(
        task_run_id=run,
        run_kind=RealityRunKind.BASELINE,
        task_id=task.task_id,
        task_manifest_hash=task.content_hash,
        outcome_hash=digest(f"outcome:{run}"),
        outcome_artifact_id=uuid4(),
        outcome_artifact_hash=digest(f"artifact:{run}"),
        hidden_evidence_artifact_id=uuid4(),
        hidden_evidence_hash=digest(f"evidence:{run}"),
        final_status=CodingOutcomeStatus.FAILED,
        hidden_verification_passed=False,
        source_event_id=uuid4(),
        occurred_at=FIXTURE_TIME,
    )
