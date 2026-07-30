"""S21C1-043: quarantine review, and the ways review must not become a rewrite.

Review is the one place a human changes what the learning plane believes about a governed
outcome. The tests fix what that authority is bounded by: only a human may exercise it,
only with a reason, only on something actually quarantined, and never by editing the
record that put it there.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.application.services.learned_intake import LearnedObservationIntake
from cognitive_os.application.services.learned_quarantine import (
    MAX_REVIEW_PAGE,
    LearnedQuarantineReview,
)
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedApprovalAuthorityKind,
    LearnedRepositoryError,
    ObservationAttribution,
    ObservationStatus,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.learned.memory_repository import (
    InMemoryLearnedEvidenceRepository,
)

from . import fixtures as fx

CORRELATION = uuid4()
REVIEWER = "release-operator"
HUMAN = LearnedApprovalAuthorityKind.HUMAN_OPERATOR


def reference(**overrides: object) -> GovernedOutcomeReference:
    fields: dict[str, object] = {
        "surface": fx.surface(),
        "source_kind": "governed_task_run",
        "source_run_id": uuid4(),
        "source_payload_hash": "a" * 64,
        "provenance_class": ProvenanceClass.SELF_PLAY,
        # Unknown attribution is the ordinary way into quarantine.
        "attribution": ObservationAttribution.UNKNOWN,
        "usage_rights_verified": True,
        "sensitivity": "internal",
        "verifier_status": "passed",
        "verifier_evidence_hash": "b" * 64,
        "occurred_at": fx.FIXTURE_NOW,
    }
    fields.update(overrides)
    return GovernedOutcomeReference(**fields)  # type: ignore[arg-type]


def make_review(
    *, reviewers: frozenset[str] = frozenset({REVIEWER})
) -> tuple[LearnedQuarantineReview, LearnedObservationIntake, InMemoryLearnedEvidenceRepository]:
    repository = InMemoryLearnedEvidenceRepository()
    service = LearnedEvidenceService(
        repository,
        events=LearnedEventService(MemoryEventStore()),
        clock=lambda: fx.FIXTURE_NOW,
    )
    return (
        LearnedQuarantineReview(service, reviewers=reviewers, clock=lambda: fx.FIXTURE_NOW),
        LearnedObservationIntake(service),
        repository,
    )


class TestListingIsBoundedAndRedacted:
    @pytest.mark.asyncio
    async def test_entries_carry_identity_and_hashes_and_no_body(self) -> None:
        review, intake, _ = make_review()
        await intake.offer(reference(), correlation_id=CORRELATION)
        entries, _ = await review.list_quarantined(
            actor=REVIEWER, authority="operator", purpose="triage"
        )
        assert len(entries) == 1
        dumped = entries[0].model_dump(mode="json")
        assert dumped["source_payload_hash"] == "a" * 64
        assert "payload" not in dumped
        assert "body" not in dumped
        assert "decision_reason" not in dumped, "the code is shown, the prose is not"
        assert dumped["decision_code"] == "quarantined_attribution_unknown"

    @pytest.mark.asyncio
    async def test_a_read_of_sensitive_entries_produces_an_access_record(self) -> None:
        review, intake, repository = make_review()
        await intake.offer(reference(sensitivity="restricted"), correlation_id=CORRELATION)
        entries, access = await review.list_quarantined(
            actor=REVIEWER, authority="operator", purpose="weekly triage"
        )
        assert len(entries) == 1
        assert access is not None
        assert access.actor == REVIEWER
        assert access.purpose == "weekly triage"
        assert repository.counts()["accesses"] == 1

    @pytest.mark.asyncio
    async def test_a_public_only_read_produces_no_audit_noise(self) -> None:
        """An audit trail nobody can distinguish from noise is one nobody reads."""
        review, intake, repository = make_review()
        await intake.offer(reference(sensitivity="public"), correlation_id=CORRELATION)
        entries, access = await review.list_quarantined(
            actor=REVIEWER, authority="operator", purpose="triage"
        )
        assert entries and access is None
        assert repository.counts()["accesses"] == 0

    @pytest.mark.asyncio
    async def test_the_listing_is_capped(self) -> None:
        review, _, _ = make_review()
        entries, _ = await review.list_quarantined(
            actor=REVIEWER, authority="operator", purpose="triage", limit=10_000
        )
        assert len(entries) <= MAX_REVIEW_PAGE


class TestOnlyAnAuthorisedHumanMayReview:
    @pytest.mark.asyncio
    async def test_a_model_identity_cannot_review(self) -> None:
        """The same failure as approving one's own activation, refused the same way."""
        review, intake, _ = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        with pytest.raises(LearnedRepositoryError, match="cannot review learned evidence"):
            await review.review(
                stored.observation_id,
                accept=True,
                reviewer="candidate-model",
                reviewer_kind=LearnedApprovalAuthorityKind.MODEL,
                authority="model",
                reason="looks fine to me",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_an_unnamed_reviewer_cannot_review(self) -> None:
        review, intake, _ = make_review(reviewers=frozenset())
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        with pytest.raises(LearnedRepositoryError, match="not authorised to review"):
            await review.review(
                stored.observation_id,
                accept=True,
                reviewer=REVIEWER,
                reviewer_kind=HUMAN,
                authority="operator",
                reason="attribution established from the run trace",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_a_review_without_a_reason_is_refused(self) -> None:
        review, intake, _ = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        with pytest.raises(LearnedRepositoryError, match="must say why"):
            await review.review(
                stored.observation_id,
                accept=False,
                reviewer=REVIEWER,
                reviewer_kind=HUMAN,
                authority="operator",
                reason="   ",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_reviewing_something_not_quarantined_is_refused(self) -> None:
        review, intake, _ = make_review()
        accepted = await intake.offer(
            reference(attribution=ObservationAttribution.DIRECT), correlation_id=CORRELATION
        )
        assert accepted.status is ObservationStatus.ACCEPTED
        with pytest.raises(LearnedRepositoryError, match="no quarantined observation"):
            await review.review(
                accepted.observation_id,
                accept=True,
                reviewer=REVIEWER,
                reviewer_kind=HUMAN,
                authority="operator",
                reason="already accepted",
                correlation_id=CORRELATION,
            )


class TestReviewAppendsAndNeverRewrites:
    @pytest.mark.asyncio
    async def test_an_accepted_review_leaves_the_quarantine_record_in_place(self) -> None:
        """The queue stays a history of what was once uncertain."""
        review, intake, repository = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        outcome = await review.review(
            stored.observation_id,
            accept=True,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="attribution established from the run trace",
            correlation_id=CORRELATION,
        )
        assert outcome.status == "accepted"
        assert outcome.replacement_id != stored.observation_id

        service = review._service
        quarantined = await service.list_observations(status=ObservationStatus.QUARANTINED)
        accepted = await service.list_observations(status=ObservationStatus.ACCEPTED)
        assert len(quarantined) == 1, "the original entry must survive its review"
        assert quarantined[0].observation_id == stored.observation_id
        assert len(accepted) == 1
        assert repository.counts()["observations"] == 2

    @pytest.mark.asyncio
    async def test_an_accepted_review_states_the_attribution_it_established(self) -> None:
        """An accepted observation may not carry `unknown`, so review must resolve it."""
        review, intake, _ = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        await review.review(
            stored.observation_id,
            accept=True,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="the outcome contributed, though not solely",
            correlation_id=CORRELATION,
        )
        accepted = await review._service.list_observations(status=ObservationStatus.ACCEPTED)
        assert accepted[0].attribution is ObservationAttribution.CONTRIBUTING

    @pytest.mark.asyncio
    async def test_a_rejecting_review_appends_a_rejection(self) -> None:
        review, intake, repository = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        outcome = await review.review(
            stored.observation_id,
            accept=False,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="the run trace does not support any attribution",
            correlation_id=CORRELATION,
        )
        assert outcome.status == "rejected"
        rejected = await review._service.list_observations(status=ObservationStatus.REJECTED)
        assert len(rejected) == 1
        assert not rejected[0].evaluation_eligible
        assert repository.counts()["observations"] == 2

    @pytest.mark.asyncio
    async def test_a_repeated_review_is_a_free_no_op(self) -> None:
        review, intake, repository = make_review()
        stored = await intake.offer(reference(), correlation_id=CORRELATION)
        first = await review.review(
            stored.observation_id,
            accept=True,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="attribution established from the run trace",
            correlation_id=CORRELATION,
        )
        second = await review.review(
            stored.observation_id,
            accept=True,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="attribution established from the run trace",
            correlation_id=CORRELATION,
        )
        assert first.replacement_id == second.replacement_id
        assert repository.counts()["observations"] == 2

    @pytest.mark.asyncio
    async def test_review_cannot_accept_an_observation_without_usage_rights(self) -> None:
        """Review resolves ambiguity; it does not grant rights nobody verified."""
        review, intake, _ = make_review()
        rejected = await intake.offer(
            reference(usage_rights_verified=False), correlation_id=CORRELATION
        )
        assert rejected.status is ObservationStatus.REJECTED
        with pytest.raises(LearnedRepositoryError, match="no quarantined observation"):
            await review.review(
                rejected.observation_id,
                accept=True,
                reviewer=REVIEWER,
                reviewer_kind=HUMAN,
                authority="operator",
                reason="we would like to use it anyway",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_a_sensitive_review_produces_an_access_record(self) -> None:
        review, intake, repository = make_review()
        stored = await intake.offer(reference(sensitivity="restricted"), correlation_id=CORRELATION)
        outcome = await review.review(
            stored.observation_id,
            accept=False,
            reviewer=REVIEWER,
            reviewer_kind=HUMAN,
            authority="operator",
            reason="the run trace does not support any attribution",
            correlation_id=CORRELATION,
        )
        assert outcome.access_id is not None
        assert repository.counts()["accesses"] == 1
