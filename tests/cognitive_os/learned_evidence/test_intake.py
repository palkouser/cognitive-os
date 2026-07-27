"""S21C1-041: governed outcome intake, and the four ways it must not go wrong.

Intake is the point where material from the running system first reaches the learning
plane, so its failure modes are the expensive ones: a fixture mistaken for a real run
contaminates every later comparison, an unattributable outcome accepted quietly becomes
evidence, and a source that changed under a stable identity silently rewrites history.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import (
    REAL_GOVERNED_SOURCE_KINDS,
    LearnedObservationIntake,
    classify,
    idempotency_key_for,
    observation_id_for,
)
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationAttribution,
    ObservationDecisionCode,
    ObservationStatus,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx

CORRELATION = uuid4()
RUN_ID = uuid4()


def reference(**overrides: object) -> GovernedOutcomeReference:
    fields: dict[str, object] = {
        "surface": fx.surface(),
        "source_kind": "governed_task_run",
        "source_run_id": RUN_ID,
        "source_payload_hash": "a" * 64,
        "provenance_class": ProvenanceClass.SELF_PLAY,
        "attribution": ObservationAttribution.DIRECT,
        "usage_rights_verified": True,
        "sensitivity": "internal",
        "verifier_status": "passed",
        "verifier_evidence_hash": "b" * 64,
    }
    fields.update(overrides)
    return GovernedOutcomeReference(**fields)  # type: ignore[arg-type]


def make_intake() -> tuple[LearnedObservationIntake, InMemoryLearnedEvidenceRepository]:
    repository = InMemoryLearnedEvidenceRepository()
    service = LearnedEvidenceService(
        repository,
        events=LearnedEventService(MemoryEventStore()),
        clock=lambda: fx.FIXTURE_NOW,
    )
    return LearnedObservationIntake(service, clock=lambda: fx.FIXTURE_NOW), repository


class TestASourceMustBeTraceable:
    def test_an_outcome_naming_no_source_is_refused(self) -> None:
        """Evidence nobody can trace back to a run is not evidence."""
        with pytest.raises(ValueError, match="must name the task, run or event"):
            GovernedOutcomeReference(
                surface=fx.surface(),
                source_kind="governed_task_run",
                source_payload_hash="a" * 64,
                provenance_class=ProvenanceClass.SELF_PLAY,
                attribution=ObservationAttribution.DIRECT,
                usage_rights_verified=True,
                sensitivity="internal",
            )

    def test_identity_ignores_content(self) -> None:
        """Identity is who the outcome is; the hash is what it said."""
        assert reference().identity == reference(source_payload_hash="9" * 64).identity


class TestClassification:
    def test_a_complete_governed_outcome_is_accepted(self) -> None:
        code, _ = classify(reference())
        assert code is ObservationDecisionCode.ACCEPTED
        assert code.status is ObservationStatus.ACCEPTED

    def test_missing_usage_rights_is_rejected_not_quarantined(self) -> None:
        """A rejection must not be reportable as something an operator could wave through."""
        code, _ = classify(reference(usage_rights_verified=False))
        assert code is ObservationDecisionCode.REJECTED_USAGE_RIGHTS_UNVERIFIED
        assert code.status is ObservationStatus.REJECTED

    def test_unknown_attribution_is_quarantined(self) -> None:
        code, _ = classify(reference(attribution=ObservationAttribution.UNKNOWN))
        assert code is ObservationDecisionCode.QUARANTINED_ATTRIBUTION_UNKNOWN
        assert code.status is ObservationStatus.QUARANTINED

    def test_a_verifier_backed_outcome_without_evidence_is_quarantined(self) -> None:
        code, _ = classify(reference(verifier_evidence_hash=None))
        assert code is ObservationDecisionCode.QUARANTINED_VERIFIER_EVIDENCE_MISSING

    def test_an_unrecognised_sensitivity_is_quarantined(self) -> None:
        """It decides whether reads must be audited, so an unknown label is not a detail."""
        code, _ = classify(reference(sensitivity="probably-fine"))
        assert code is ObservationDecisionCode.QUARANTINED_SOURCE_INCOMPLETE

    def test_rights_are_checked_before_attribution(self) -> None:
        code, _ = classify(
            reference(usage_rights_verified=False, attribution=ObservationAttribution.UNKNOWN)
        )
        assert code is ObservationDecisionCode.REJECTED_USAGE_RIGHTS_UNVERIFIED


class TestNoFixtureBecomesARealGovernedRun:
    def test_an_ineligible_source_kind_cannot_claim_a_real_governed_run(self) -> None:
        """The contamination this prevents is permanent and silent.

        A real governed run is the uncontaminated yardstick every later distribution
        comparison is measured against. A self-play fixture wearing that label would not
        fail anything; it would just make the measurements mean less than they claim.
        """
        code, detail = classify(
            reference(
                source_kind="fixture_replay",
                provenance_class=ProvenanceClass.REAL_GOVERNED_RUN,
            )
        )
        assert code is ObservationDecisionCode.REJECTED_PROVENANCE_NOT_CREDIBLE
        assert "fixture_replay" in detail

    @pytest.mark.parametrize("source_kind", sorted(REAL_GOVERNED_SOURCE_KINDS))
    def test_the_allowlisted_source_kinds_may_claim_it(self, source_kind: str) -> None:
        code, _ = classify(
            reference(
                source_kind=source_kind,
                provenance_class=ProvenanceClass.REAL_GOVERNED_RUN,
                verifier_evidence_hash="b" * 64,
            )
        )
        assert code is ObservationDecisionCode.ACCEPTED

    @pytest.mark.asyncio
    async def test_an_accepted_real_run_is_never_training_eligible(self) -> None:
        intake, _ = make_intake()
        stored = await intake.offer(
            reference(provenance_class=ProvenanceClass.REAL_GOVERNED_RUN),
            correlation_id=CORRELATION,
        )
        assert stored.status is ObservationStatus.ACCEPTED
        assert stored.evaluation_eligible
        assert not stored.training_eligible


class TestIntakeIsIdempotentAndFailsClosed:
    @pytest.mark.asyncio
    async def test_repeated_intake_of_the_same_outcome_yields_the_same_receipt(self) -> None:
        intake, repository = make_intake()
        first = await intake.offer(reference(), correlation_id=CORRELATION)
        second = await intake.offer(reference(), correlation_id=CORRELATION)
        assert first.observation_id == second.observation_id
        assert first.content_hash == second.content_hash
        assert repository.counts()["observations"] == 1

    @pytest.mark.asyncio
    async def test_changed_content_under_the_same_identity_fails_closed(self) -> None:
        """Either it is a different outcome or a corrupted one. Both need a human."""
        intake, repository = make_intake()
        await intake.offer(reference(), correlation_id=CORRELATION)
        with pytest.raises(LearnedRepositoryError) as raised:
            await intake.offer(reference(source_payload_hash="9" * 64), correlation_id=CORRELATION)
        assert raised.value.conflict is LearnedRepositoryConflict.IDEMPOTENCY_KEY_REUSED
        assert repository.counts()["observations"] == 1

    def test_the_observation_id_covers_content_and_the_key_does_not(self) -> None:
        changed = reference(source_payload_hash="9" * 64)
        assert observation_id_for(reference()) != observation_id_for(changed)
        assert idempotency_key_for(reference()) == idempotency_key_for(changed)

    @pytest.mark.asyncio
    async def test_a_different_source_is_a_different_observation(self) -> None:
        intake, repository = make_intake()
        await intake.offer(reference(), correlation_id=CORRELATION)
        await intake.offer(reference(source_run_id=uuid4()), correlation_id=CORRELATION)
        assert repository.counts()["observations"] == 2


class TestEveryDecisionIsRecorded:
    @pytest.mark.asyncio
    async def test_a_rejection_is_appended_rather_than_dropped(self) -> None:
        """A refused outcome that left no trace makes the quarantine queue a half-truth."""
        intake, repository = make_intake()
        stored = await intake.offer(
            reference(usage_rights_verified=False), correlation_id=CORRELATION
        )
        assert stored.status is ObservationStatus.REJECTED
        assert not stored.evaluation_eligible
        assert repository.counts()["observations"] == 1
        assert stored.decision_reason.startswith("rejected_usage_rights_unverified:")

    @pytest.mark.asyncio
    async def test_a_quarantine_is_appended_and_listable(self) -> None:
        intake, _ = make_intake()
        await intake.offer(
            reference(attribution=ObservationAttribution.UNKNOWN), correlation_id=CORRELATION
        )
        service = intake._service
        quarantined = await service.list_observations(status=ObservationStatus.QUARANTINED)
        assert len(quarantined) == 1
        assert quarantined[0].decision_reason.startswith("quarantined_attribution_unknown:")

    @pytest.mark.asyncio
    async def test_intake_emits_a_correlated_event_and_records_no_failure(self) -> None:
        intake, _ = make_intake()
        await intake.offer(reference(), correlation_id=CORRELATION)
        assert intake._service.correlation_failures == ()

    @pytest.mark.asyncio
    async def test_a_batch_stops_at_the_first_refusal(self) -> None:
        """Continuing past a changed source would bury the signal under successful appends."""
        intake, repository = make_intake()
        good = reference()
        changed = reference(source_payload_hash="9" * 64)
        with pytest.raises(LearnedRepositoryError):
            await intake.offer_all(
                (good, changed, reference(source_run_id=uuid4())), correlation_id=CORRELATION
            )
        assert repository.counts()["observations"] == 1

    @pytest.mark.asyncio
    async def test_the_observation_stores_a_reference_and_not_a_body(self) -> None:
        """A learning plane that copied sensitive bodies would widen what it audits."""
        intake, _ = make_intake()
        stored = await intake.offer(reference(sensitivity="restricted"), correlation_id=CORRELATION)
        dumped = stored.model_dump(mode="json")
        assert set(dumped) == set(type(stored).model_fields)
        assert "payload" not in dumped
        assert "body" not in dumped
        assert dumped["source_payload_hash"] == "a" * 64
