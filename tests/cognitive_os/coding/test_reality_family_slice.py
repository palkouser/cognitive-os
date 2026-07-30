"""One representative task from each of the six families, end to end and offline. §S21C3-063.

The other C3 tests each check one plane deeply against a synthetic manifest. This one is
shallow and wide on purpose: it takes a *real* generated task from every family and walks it
through the whole credential-free chain — generation, the control-material boundary, outcome
recording into an Artifact Store and an Event Store, trajectory planning, and the corpus
request — asserting only that the chain holds.

That is the check a CI lane can actually run. No Docker, no PostgreSQL, no network, no
provider credentials, no local embedding model, no GPU. A family whose fixtures rotted, or
whose task text started leaking control material, fails here rather than in a campaign that
needs containers and half an hour.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from cognitive_os.coding import reality_corpus_items, reality_leakage, reality_trajectories
from cognitive_os.coding.hidden_verification import HiddenVerificationStatus
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.coding.reality_tasks import (
    available_templates,
    build_manifest,
    template,
    write_task,
)
from cognitive_os.coding.reality_trajectories import CorrectionStep
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.reality import RealityCandidateStrategy
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.memory_store import MemoryEventStore

from .reality_fixtures import (
    InMemoryArtifactStore,
    candidate_manifest,
    coding_outcome,
    hidden_evidence,
)

EPOCH = datetime(2026, 7, 30, tzinfo=UTC)
FIXTURE_ARTIFACT = UUID("00000000-0000-0000-0000-0000000021c3")


#: The first template of each family, in template order. One per family, not one per task:
#: the point is coverage of the six shapes at CI cost, not a second campaign.
def _one_per_family() -> list[str]:
    seen: dict[str, str] = {}
    for template_id in available_templates():
        seen.setdefault(template_id.split(".")[0], template_id)
    return list(seen.values())


REPRESENTATIVE = _one_per_family()


def _manifest(template_id: str):  # type: ignore[no-untyped-def]
    return build_manifest(
        template_id,
        seed=1,
        hidden_bundle_artifact_id=FIXTURE_ARTIFACT,
        hidden_bundle_hash="0" * 64,
        created_at=EPOCH,
    )


def test_every_family_is_represented() -> None:
    """Six families, six representatives. A dropped family must fail, not silently shrink."""
    assert len(REPRESENTATIVE) == 6
    assert len({item.split(".")[0] for item in REPRESENTATIVE}) == 6


@pytest.mark.parametrize("template_id", REPRESENTATIVE)
def test_the_control_bundle_never_lands_inside_the_workspace(template_id: str, tmp_path) -> None:  # type: ignore[no-untyped-def]
    task = write_task(
        template_id,
        root=tmp_path / template_id,
        seed=1,
        hidden_bundle_artifact_id=FIXTURE_ARTIFACT,
        hidden_bundle_hash="0" * 64,
        created_at=EPOCH,
    )

    assert task.control.is_dir() and task.workspace.is_dir()
    assert task.control not in task.workspace.parents
    assert not list(task.workspace.rglob("*hidden*"))


@pytest.mark.parametrize("template_id", REPRESENTATIVE)
def test_no_control_token_reaches_the_projection(template_id: str) -> None:
    """The projection is the only thing a candidate or a provider is shown."""
    task = _manifest(template_id)
    tokens = reality_leakage.control_tokens(task, template(template_id))
    shown = "\n".join(
        (
            task.projection.issue_description,
            task.projection.expected_behavior,
            *(entry.path for entry in task.projection.files),
        )
    )

    assert tokens, "the control bundle must contribute at least one token to look for"
    assert [token for token in tokens if token in shown] == []


@pytest.mark.parametrize("template_id", REPRESENTATIVE)
def test_the_corpus_request_declares_the_group_and_the_rights(template_id: str) -> None:
    task = _manifest(template_id)

    request = reality_corpus_items.task_package_request(task, created_at=EPOCH)

    assert request.split_group_key == task.repository_group
    assert task.repository_group in request.scope
    assert request.usage_rights


@pytest.mark.parametrize("template_id", REPRESENTATIVE)
@pytest.mark.asyncio
async def test_a_recorded_correction_path_plans_and_compiles_a_request(template_id: str) -> None:
    """Generation to trajectory request, with real bytes behind every step and no container."""
    task = _manifest(template_id)
    artifacts = InMemoryArtifactStore()
    events = MemoryEventStore()
    recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)

    async def record(strategy: RealityCandidateStrategy | None, *, passed: bool) -> CorrectionStep:
        task_run_id = uuid4()
        candidate = None
        if strategy is not None:
            patch = await artifacts.put_bytes(
                f"diff --git a/src/x.py b/src/x.py\n{strategy.value}\n".encode(),
                media_type="text/x-diff",
            )
            candidate = candidate_manifest(task, strategy).model_copy(
                update={"patch_artifact_id": patch.artifact_id, "patch_hash": patch.content_hash}
            )
        recorded = await recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=(CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED),
                marker=strategy.value if strategy else "baseline",
            ),
            task=task,
            evidence=hidden_evidence(
                task=task,
                task_run_id=task_run_id,
                status=(
                    HiddenVerificationStatus.PASSED if passed else HiddenVerificationStatus.FAILED
                ),
            ),
            candidate=candidate,
            correlation_id=task_run_id,
        )
        return CorrectionStep(reference=recorded.reference, candidate=candidate)

    steps = (
        await record(None, passed=False),
        await record(RealityCandidateStrategy.INCOMPLETE_A, passed=False),
        await record(RealityCandidateStrategy.CORRECT_NARROW, passed=True),
    )
    plan = reality_trajectories.TrajectoryPlan(
        task_id=task.task_id,
        incorrect=RealityCandidateStrategy.INCOMPLETE_A,
        correct=RealityCandidateStrategy.CORRECT_NARROW,
        steps=steps,
    )

    request, _, _ = await reality_trajectories.build_request(
        plan, task=task, artifacts=artifacts, created_at=EPOCH
    )

    assert request.compilation_id == plan.compilation_id
    assert request.created_at == EPOCH


@pytest.mark.parametrize("template_id", REPRESENTATIVE)
@pytest.mark.asyncio
async def test_the_same_request_built_twice_is_byte_identical(template_id: str) -> None:
    """W6-F1's regression, at the level that made it possible.

    `ExperienceCompilerService` verifies a persisted manifest by recompiling and comparing for
    exact equality. That only works if the request is a pure function of the task and its
    recorded outcomes — so a caller that passes a clock makes every trajectory it writes
    unverifiable a second later. Here the epoch is fixed and the two requests must match.
    """
    task = _manifest(template_id)
    artifacts = InMemoryArtifactStore()
    events = MemoryEventStore()
    recorder = CodingOutcomeRecorder(artifacts, CodingEventService(events), events)
    steps = []
    for strategy, passed in (
        (None, False),
        (RealityCandidateStrategy.INCOMPLETE_A, False),
        (RealityCandidateStrategy.CORRECT_NARROW, True),
    ):
        task_run_id = uuid4()
        candidate = None
        if strategy is not None:
            patch = await artifacts.put_bytes(
                f"diff --git a/src/x.py b/src/x.py\n{strategy.value}\n".encode(),
                media_type="text/x-diff",
            )
            candidate = candidate_manifest(task, strategy).model_copy(
                update={"patch_artifact_id": patch.artifact_id, "patch_hash": patch.content_hash}
            )
        recorded = await recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=(CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED),
                marker=strategy.value if strategy else "baseline",
            ),
            task=task,
            evidence=hidden_evidence(
                task=task,
                task_run_id=task_run_id,
                status=(
                    HiddenVerificationStatus.PASSED if passed else HiddenVerificationStatus.FAILED
                ),
            ),
            candidate=candidate,
            correlation_id=task_run_id,
        )
        steps.append(CorrectionStep(reference=recorded.reference, candidate=candidate))
    plan = reality_trajectories.TrajectoryPlan(
        task_id=task.task_id,
        incorrect=RealityCandidateStrategy.INCOMPLETE_A,
        correct=RealityCandidateStrategy.CORRECT_NARROW,
        steps=tuple(steps),
    )

    first, _, _ = await reality_trajectories.build_request(
        plan, task=task, artifacts=artifacts, created_at=EPOCH
    )
    second, _, _ = await reality_trajectories.build_request(
        plan, task=task, artifacts=artifacts, created_at=EPOCH
    )

    assert first.content_hash == second.content_hash
