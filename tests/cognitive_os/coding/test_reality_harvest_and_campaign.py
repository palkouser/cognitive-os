"""S21C3-013 and S21C3-014: what reaches the learning plane, and what the denominator counts."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

import pytest

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.application.services.reality_campaign import (
    CampaignLedgerError,
    RealityCampaignLedger,
    count_outcomes,
)
from cognitive_os.application.services.reality_outcome_harvester import (
    OutcomeHarvestError,
    RealityOutcomeHarvester,
)
from cognitive_os.coding.hidden_verification import HiddenVerificationStatus
from cognitive_os.coding.outcome_recording import CodingOutcomeRecorder
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import LearnedRepositoryError, ObservationStatus
from cognitive_os.domain.reality import (
    RealityCampaignManifest,
    RealityCandidateSource,
    RealityCandidateStrategy,
    RealityOutcomeCountReason,
    RealityRunIdentity,
    RealityRunKind,
    RealityTaskManifest,
)
from cognitive_os.events.coding_event_service import CodingEventService
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from .reality_fixtures import (
    FIXTURE_TIME,
    InMemoryArtifactStore,
    candidate_manifest,
    coding_outcome,
    digest,
    hidden_evidence,
    task_manifest,
)


class _Harness:
    def __init__(self, *, intake_clock: Callable[[], datetime] | None = None) -> None:
        self.artifacts = InMemoryArtifactStore()
        self.store = MemoryEventStore()
        self.recorder = CodingOutcomeRecorder(
            self.artifacts, CodingEventService(self.store), self.store
        )
        service = LearnedEvidenceService(
            InMemoryLearnedEvidenceRepository(), events=LearnedEventService(self.store)
        )
        self.intake = (
            LearnedObservationIntake(service, clock=intake_clock)
            if intake_clock is not None
            else LearnedObservationIntake(service)
        )
        self.harvester = RealityOutcomeHarvester(self.artifacts, self.store, self.intake)
        self.ledger = RealityCampaignLedger(self.store)

    async def record_candidate(
        self, task: RealityTaskManifest, strategy: RealityCandidateStrategy, *, passed: bool
    ) -> object:
        task_run_id = uuid4()
        return await self.recorder.record(
            outcome=coding_outcome(
                task_run_id=task_run_id,
                status=CodingOutcomeStatus.ACCEPTED if passed else CodingOutcomeStatus.FAILED,
                marker=strategy.value,
            ),
            task=task,
            evidence=hidden_evidence(
                task=task,
                task_run_id=task_run_id,
                status=HiddenVerificationStatus.PASSED
                if passed
                else HiddenVerificationStatus.FAILED,
            ),
            candidate=candidate_manifest(task, strategy),
            correlation_id=task_run_id,
        )

    async def record(
        self,
        task: RealityTaskManifest,
        *,
        status: HiddenVerificationStatus = HiddenVerificationStatus.FAILED,
        outcome_status: CodingOutcomeStatus = CodingOutcomeStatus.FAILED,
        marker: str = "run",
        run_identity: RealityRunIdentity | None = None,
    ) -> tuple[object, object]:
        task_run_id = uuid4()
        recorded = await self.recorder.record(
            outcome=coding_outcome(task_run_id=task_run_id, status=outcome_status, marker=marker),
            task=task,
            evidence=hidden_evidence(task=task, task_run_id=task_run_id, status=status),
            candidate=None,
            correlation_id=task_run_id,
            run_identity=run_identity,
        )
        return recorded, task_run_id


@pytest.mark.asyncio
async def test_a_harvested_outcome_is_evaluation_eligible_and_never_training_eligible() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)

    harvested = await harness.harvester.harvest(
        event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
        task=task,
        correlation_id=uuid4(),
    )

    assert harvested.governed.provenance_class is ProvenanceClass.REAL_GOVERNED_RUN
    assert harvested.governed.source_kind == "governed_task_run"
    assert harvested.observation.status is ObservationStatus.ACCEPTED
    assert harvested.evaluation_eligible is True
    assert "training" not in harvested.observation.decision_reason


@pytest.mark.asyncio
async def test_a_failed_candidate_is_still_accepted_evidence() -> None:
    """Failures are outcomes. A corpus of successes measures the campaign, not the candidates."""
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task, status=HiddenVerificationStatus.FAILED)

    harvested = await harness.harvester.harvest(
        event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
        task=task,
        correlation_id=uuid4(),
    )

    assert harvested.governed.verifier_status == "failed"
    assert harvested.evaluation_eligible is True


@pytest.mark.asyncio
async def test_missing_source_bytes_fail_closed() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)
    harness.artifacts.forget(recorded.reference.outcome_artifact_id)  # type: ignore[attr-defined]

    with pytest.raises(OutcomeHarvestError, match="could not be verified"):
        await harness.harvester.harvest(
            event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
            task=task,
            correlation_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_changed_source_bytes_fail_closed() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)
    harness.artifacts.corrupt(recorded.reference.outcome_artifact_id)  # type: ignore[attr-defined]

    with pytest.raises(OutcomeHarvestError, match="could not be verified"):
        await harness.harvester.harvest(
            event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
            task=task,
            correlation_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_an_outcome_from_another_manifest_revision_is_refused() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)

    with pytest.raises(OutcomeHarvestError, match="different task manifest revision"):
        await harness.harvester.harvest(
            event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
            task=task_manifest(task_id=task.task_id, seed=99),
            correlation_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_a_non_terminal_outcome_is_not_offered() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task, outcome_status=CodingOutcomeStatus.CANCELLED)

    with pytest.raises(OutcomeHarvestError, match="not a terminal result"):
        await harness.harvester.harvest(
            event_id=recorded.reference.source_event_id,  # type: ignore[attr-defined]
            task=task,
            correlation_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_an_event_that_is_not_a_recorded_outcome_is_refused() -> None:
    harness = _Harness()

    with pytest.raises(OutcomeHarvestError, match="no event with identity"):
        await harness.harvester.harvest(
            event_id=uuid4(), task=task_manifest(), correlation_id=uuid4()
        )


@pytest.mark.asyncio
async def test_re_offering_the_same_outcome_is_a_free_no_op_under_a_stable_clock() -> None:
    """The C1 intake promises crash-safe re-offering. It keeps that promise on a fixed clock.

    See `test_re_offering_under_a_moving_clock_is_refused` for the case where it does not,
    which is a defect this sprint inherited rather than introduced.
    """
    harness = _Harness(intake_clock=lambda: FIXTURE_TIME)
    task = task_manifest()
    recorded, _ = await harness.record(task)
    event_id = recorded.reference.source_event_id  # type: ignore[attr-defined]

    first = await harness.harvester.harvest(event_id=event_id, task=task, correlation_id=uuid4())
    second = await harness.harvester.harvest(event_id=event_id, task=task, correlation_id=uuid4())

    assert first.observation.observation_id == second.observation.observation_id
    assert first.observation.content_hash == second.observation.content_hash


@pytest.mark.asyncio
async def test_re_offering_under_a_moving_clock_is_refused() -> None:
    """Documents an inherited defect, so the sprint does not discover it in W3.

    `LearnedObservationIntake` stamps `recorded_at` from its clock and the observation record
    is hash-bound, so the same outcome offered twice at different moments is refused as an
    idempotency-key conflict — even though the module docstring states intake "can be re-run
    after a crash without producing a second record". Recorded here rather than worked around:
    S21C3-036 and S21C3-062 need re-offering to be safe, and the fix belongs to the C1 intake
    (ADR 0086), not to the C3 harvester.
    """
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)
    event_id = recorded.reference.source_event_id  # type: ignore[attr-defined]

    await harness.harvester.harvest(event_id=event_id, task=task, correlation_id=uuid4())

    with pytest.raises(LearnedRepositoryError, match="idempotency_key_reused"):
        await harness.harvester.harvest(event_id=event_id, task=task, correlation_id=uuid4())


@pytest.mark.asyncio
async def test_a_replayed_recording_does_not_count_twice() -> None:
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)
    reference = recorded.reference  # type: ignore[attr-defined]

    count = count_outcomes([reference, reference])

    assert count.unique == 1
    assert count.duplicates_excluded == 1
    assert count.excluded[0].reason is RealityOutcomeCountReason.DUPLICATE_EVENT_ID


@pytest.mark.asyncio
async def test_two_executions_with_identical_outcome_bytes_count_once() -> None:
    """Deterministic replay is legitimate and must not inflate the denominator."""
    harness = _Harness()
    task = task_manifest()
    recorded, _ = await harness.record(task)
    original = recorded.reference  # type: ignore[attr-defined]
    twin = original.model_copy(
        update={
            "source_event_id": uuid4(),
            "task_run_id": uuid4(),
            "content_hash": "",
        }
    )

    count = count_outcomes([original, twin])

    assert count.unique == 1
    assert count.excluded[0].reason is RealityOutcomeCountReason.DUPLICATE_OUTCOME_HASH


@pytest.mark.asyncio
async def test_distinct_executions_all_count_and_failures_are_visible() -> None:
    harness = _Harness()
    task = task_manifest()
    failed = await harness.record_candidate(
        task, RealityCandidateStrategy.INCOMPLETE_A, passed=False
    )
    passed = await harness.record_candidate(
        task, RealityCandidateStrategy.CORRECT_NARROW, passed=True
    )

    count = count_outcomes([failed.reference, passed.reference])  # type: ignore[attr-defined]

    assert count.unique == 2
    assert count.duplicates_excluded == 0
    assert count.passed == 1
    assert count.failed == 1


def _identity(task: RealityTaskManifest, *, version: int = 1) -> RealityRunIdentity:
    return RealityRunIdentity(
        task_id=task.task_id,
        task_manifest_hash=task.content_hash,
        run_kind=RealityRunKind.BASELINE,
        source=RealityCandidateSource.BASELINE,
        generator_profile_id="reality.tasks",
        verifier_profile_hash=digest("verifier profile"),
        campaign_version=version,
    )


def _campaign(*identities: RealityRunIdentity) -> RealityCampaignManifest:
    return RealityCampaignManifest(
        campaign_id=uuid4(),
        campaign_version=identities[0].campaign_version,
        planned_runs=identities,
        verifier_profile_hash=digest("verifier profile"),
        created_at=FIXTURE_TIME,
    )


@pytest.mark.asyncio
async def test_resume_skips_work_the_event_store_already_shows_as_done() -> None:
    harness = _Harness()
    first, second = task_manifest(), task_manifest()
    plan = _campaign(_identity(first), _identity(second))

    _, done_run_id = await harness.record(first, run_identity=_identity(first))

    resume = await harness.ledger.plan_resume(plan, task_run_ids=[done_run_id])

    assert [item.task_id for item in resume.completed] == [first.task_id]
    assert [item.task_id for item in resume.remaining] == [second.task_id]
    assert resume.is_complete is False


@pytest.mark.asyncio
async def test_a_completed_campaign_has_nothing_left_to_run() -> None:
    harness = _Harness()
    task = task_manifest()
    identity = _identity(task)
    _, run_id = await harness.record(task, run_identity=identity)

    resume = await harness.ledger.plan_resume(_campaign(identity), task_run_ids=[run_id])

    assert resume.is_complete is True
    assert resume.unplanned_keys == frozenset()


@pytest.mark.asyncio
async def test_a_new_campaign_revision_does_not_inherit_completion() -> None:
    """Changed inputs require a new revision, and a new revision starts empty."""
    harness = _Harness()
    task = task_manifest()
    _, run_id = await harness.record(task, run_identity=_identity(task, version=1))

    resume = await harness.ledger.plan_resume(
        _campaign(_identity(task, version=2)), task_run_ids=[run_id]
    )

    assert resume.is_complete is False
    assert len(resume.unplanned_keys) == 1


@pytest.mark.asyncio
async def test_an_outcome_from_a_stale_task_revision_stops_the_resume() -> None:
    harness = _Harness()
    task = task_manifest()
    _, run_id = await harness.record(task, run_identity=_identity(task))
    revised = task_manifest(task_id=task.task_id, seed=99)

    with pytest.raises(CampaignLedgerError, match="new campaign revision, not a resume"):
        await harness.ledger.plan_resume(_campaign(_identity(revised)), task_run_ids=[run_id])


@pytest.mark.asyncio
async def test_a_run_recorded_outside_a_campaign_is_not_resumable_against_one() -> None:
    harness = _Harness()
    task = task_manifest()
    _, run_id = await harness.record(task)

    resume = await harness.ledger.plan_resume(_campaign(_identity(task)), task_run_ids=[run_id])

    assert resume.is_complete is False
    assert resume.unplanned_keys == frozenset()


@pytest.mark.asyncio
async def test_provider_prose_cannot_become_the_real_governed_run() -> None:
    """The executed sandbox outcome is the run; the advisory text stays operator-supplied."""
    harness = _Harness()
    task = task_manifest()
    provider_output_id = uuid4()
    task_run_id = uuid4()
    recorded = await harness.recorder.record(
        outcome=coding_outcome(task_run_id=task_run_id),
        task=task,
        evidence=hidden_evidence(task=task, task_run_id=task_run_id),
        candidate=candidate_manifest(
            task,
            RealityCandidateStrategy.PROVIDER_PROPOSED,
            source=RealityCandidateSource.OPENROUTER,
            provider_id="openrouter",
            provider_output_id=provider_output_id,
        ),
        correlation_id=task_run_id,
    )

    harvested = await harness.harvester.harvest(
        event_id=recorded.reference.source_event_id, task=task, correlation_id=uuid4()
    )

    assert harvested.governed.source_kind == "governed_task_run"
    assert harvested.governed.source_payload_hash == recorded.reference.outcome_artifact_hash
    assert harvested.governed.source_run_id == task_run_id
    assert harvested.reference.provider_output_id == provider_output_id
