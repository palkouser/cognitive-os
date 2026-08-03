"""S21D2-029: the caller cannot choose the role, because the sealed partition already did.

Self-play evidence may be fitted on and real governed evidence may not. Both come out of the
same runner, the same sandbox and the same hidden verifier, so the only thing that separates
them is which sealed partition the task belonged to — which is why `project()` takes a manifest
and an outcome and refuses to take a surface, a provenance class or a source kind.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from cognitive_os.application.services.correction_ranking_observations import (
    CORRECTION_SURFACE,
    GOVERNED_SOURCE_KIND,
    CorrectionRankingObservationProjector,
    SealedCampaignManifest,
    SealedCampaignMember,
)
from cognitive_os.application.services.learned_intake import (
    CORRECTION_SELF_PLAY_SOURCE_KIND,
    REAL_GOVERNED_SOURCE_KINDS,
    VERIFIER_BACKED_SOURCE_KINDS,
)
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import LearnedRepositoryError
from cognitive_os.domain.reality import (
    RealityCandidateStrategy,
    RealityOutcomeReference,
    RealityRunKind,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

SEALED_AT = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
CAMPAIGN = UUID(int=5)
MANIFEST_HASH = "b" * 64
VERIFIER_HASH = "c" * 64
CANDIDATE = UUID(int=21)
TASK = UUID(int=22)


def _member(**overrides: object) -> SealedCampaignMember:
    fields: dict[str, object] = {
        "candidate_id": CANDIDATE,
        "task_id": TASK,
        "group": "group-a",
        "partition": CorrectionPartition.TRAINING,
        "campaign_id": CAMPAIGN,
        "campaign_manifest_hash": MANIFEST_HASH,
        "campaign_version": 1,
        "verifier_profile_hash": VERIFIER_HASH,
        "feature_sealed_at": SEALED_AT,
    }
    fields.update(overrides)
    return SealedCampaignMember(**fields)  # type: ignore[arg-type]


def _projector(**overrides: object) -> CorrectionRankingObservationProjector:
    member = _member(**overrides)
    return CorrectionRankingObservationProjector(
        SealedCampaignManifest(
            campaign_id=CAMPAIGN, manifest_hash=MANIFEST_HASH, members={member.candidate_id: member}
        )
    )


def _outcome(**overrides: object) -> RealityOutcomeReference:
    fields: dict[str, object] = {
        "task_run_id": uuid4(),
        "run_kind": RealityRunKind.CANDIDATE,
        "task_id": TASK,
        "task_manifest_hash": "d" * 64,
        "candidate_id": CANDIDATE,
        "strategy": RealityCandidateStrategy.RECIPE_ALPHA,
        "outcome_hash": "e" * 64,
        "outcome_artifact_id": uuid4(),
        "outcome_artifact_hash": "f" * 64,
        "hidden_evidence_artifact_id": uuid4(),
        "hidden_evidence_hash": "0" * 64,
        "final_status": CodingOutcomeStatus.ACCEPTED,
        "hidden_verification_passed": True,
        "source_event_id": uuid4(),
        "occurred_at": SEALED_AT + timedelta(seconds=30),
    }
    fields.update(overrides)
    return RealityOutcomeReference(**fields)  # type: ignore[arg-type]


def _project(projector: CorrectionRankingObservationProjector, outcome: RealityOutcomeReference):
    return projector.project(
        outcome,
        campaign_version=1,
        verifier_profile_hash=VERIFIER_HASH,
        usage_rights_verified=True,
    )


class TestThePartitionDecidesTheRole:
    @pytest.mark.parametrize(
        ("partition", "provenance", "source_kind"),
        [
            (
                CorrectionPartition.TRAINING,
                ProvenanceClass.SELF_PLAY,
                CORRECTION_SELF_PLAY_SOURCE_KIND,
            ),
            (
                CorrectionPartition.CALIBRATION,
                ProvenanceClass.SELF_PLAY,
                CORRECTION_SELF_PLAY_SOURCE_KIND,
            ),
            (CorrectionPartition.FINAL_A, ProvenanceClass.REAL_GOVERNED_RUN, GOVERNED_SOURCE_KIND),
            (CorrectionPartition.FINAL_B, ProvenanceClass.REAL_GOVERNED_RUN, GOVERNED_SOURCE_KIND),
            (CorrectionPartition.CANARY, ProvenanceClass.REAL_GOVERNED_RUN, GOVERNED_SOURCE_KIND),
        ],
    )
    def test_each_partition_maps_to_its_declared_role(
        self, partition: CorrectionPartition, provenance: ProvenanceClass, source_kind: str
    ) -> None:
        record = _project(_projector(partition=partition), _outcome())

        assert record.provenance_class is provenance
        assert record.source_kind == source_kind
        assert record.surface == CORRECTION_SURFACE

    def test_the_self_play_source_kind_is_verifier_backed_but_not_real_governed(self) -> None:
        """The whole distinction: same verifier, different eligibility."""
        assert CORRECTION_SELF_PLAY_SOURCE_KIND in VERIFIER_BACKED_SOURCE_KINDS
        assert CORRECTION_SELF_PLAY_SOURCE_KIND not in REAL_GOVERNED_SOURCE_KINDS

    def test_a_training_observation_is_training_eligible(self) -> None:
        record = _project(_projector(partition=CorrectionPartition.TRAINING), _outcome())

        assert record.training_eligible

    def test_a_final_observation_is_not_training_eligible(self) -> None:
        record = _project(_projector(partition=CorrectionPartition.FINAL_A), _outcome())

        assert not record.training_eligible


class TestProjectionIsIdempotentAndBound:
    def test_the_same_outcome_projects_to_the_same_identity(self) -> None:
        projector = _projector()
        outcome = _outcome()

        assert _project(projector, outcome).observation_id == (
            _project(projector, outcome).observation_id
        )

    def test_the_verifier_verdict_travels_with_the_observation(self) -> None:
        record = _project(_projector(), _outcome(hidden_verification_passed=False))

        assert record.verifier_status == "failed"


class TestEverythingElseIsRefused:
    def test_a_candidate_outside_the_manifest_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="not a member of campaign"):
            _project(_projector(), _outcome(candidate_id=uuid4()))

    def test_a_baseline_run_is_not_a_ranking_observation(self) -> None:
        outcome = _outcome(
            run_kind=RealityRunKind.BASELINE,
            candidate_id=None,
            strategy=None,
            hidden_verification_passed=False,
        )

        with pytest.raises(LearnedRepositoryError, match="not a correction-ranking observation"):
            _project(_projector(), outcome)

    def test_a_candidate_from_a_different_task_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="belongs to task"):
            _project(_projector(), _outcome(task_id=uuid4()))

    def test_a_campaign_version_mismatch_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="does not match the sealed"):
            _projector().project(
                _outcome(),
                campaign_version=2,
                verifier_profile_hash=VERIFIER_HASH,
                usage_rights_verified=True,
            )

    def test_a_verifier_profile_mismatch_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="verifier profile differs"):
            _projector().project(
                _outcome(),
                campaign_version=1,
                verifier_profile_hash="9" * 64,
                usage_rights_verified=True,
            )

    def test_an_outcome_that_precedes_its_own_features_is_refused(self) -> None:
        """Chronology is the pre-outcome guarantee; without it the allowlist proves nothing."""
        with pytest.raises(LearnedRepositoryError, match="precedes its own feature record"):
            _project(_projector(), _outcome(occurred_at=SEALED_AT - timedelta(seconds=1)))

    def test_a_label_predicting_recipe_is_refused(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="predicts its own label"):
            _project(
                _projector(),
                _outcome(strategy=RealityCandidateStrategy.CORRECT_NARROW),
            )

    def test_a_provider_recipe_is_refused_as_not_a_d2_neutral_one(self) -> None:
        with pytest.raises(LearnedRepositoryError, match="not a D2 neutral recipe"):
            _project(
                _projector(),
                _outcome(strategy=RealityCandidateStrategy.PROVIDER_PROPOSED),
            )


def test_the_projector_exposes_no_way_to_choose_the_surface_or_provenance() -> None:
    """A projector that accepted them would make the role boundary a convention."""
    import inspect

    parameters = set(inspect.signature(CorrectionRankingObservationProjector.project).parameters)

    assert not parameters & {"surface", "provenance_class", "source_kind", "partition"}
