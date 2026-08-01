"""Turning executed correction runs into observations whose role the caller cannot choose.

S21D2-029. The role boundary is the sprint: self-play evidence may be fitted on and real
governed evidence may not, and the two are produced by the same runner, the same sandbox and
the same hidden verifier. The only thing that distinguishes them is which sealed partition the
task belonged to.

So the partition decides, and nothing else can. `project()` takes a manifest and an executed
outcome; it does not take a surface, a provenance class or a source kind, because a projector
that accepted those would make the boundary a convention. Training and calibration become
`SELF_PLAY` under a source kind that is verifier-backed but never real-governed; final A, final
B and canary become `REAL_GOVERNED_RUN` under the existing `governed_task_run`.

The existing `RealityOutcomeHarvester` is untouched and keeps its C3-compatible defaults.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid5

from cognitive_os.application.services.learned_intake import CORRECTION_SELF_PLAY_SOURCE_KIND
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    LearnedObservationRecord,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationAttribution,
    ObservationStatus,
)
from cognitive_os.domain.reality import (
    D2_NEUTRAL_RECIPES,
    LABEL_PREDICTING_STRATEGIES,
    RealityOutcomeReference,
)
from cognitive_os.learning.correction_protocol import (
    PARTITION_PROVENANCE,
    CorrectionPartition,
)

CORRECTION_SURFACE = "experience.correction_ranking"
GOVERNED_SOURCE_KIND = "governed_task_run"

#: Fixed forever: an observation ID derived from the outcome makes reprojection idempotent
#: rather than duplicating evidence on a rerun.
CORRECTION_OBSERVATION_NAMESPACE = UUID("6d3f92ae-51c7-5b04-8e6a-2c9f4d7b1e35")

_SOURCE_KIND: dict[CorrectionPartition, str] = {
    CorrectionPartition.TRAINING: CORRECTION_SELF_PLAY_SOURCE_KIND,
    CorrectionPartition.CALIBRATION: CORRECTION_SELF_PLAY_SOURCE_KIND,
    CorrectionPartition.FINAL_A: GOVERNED_SOURCE_KIND,
    CorrectionPartition.FINAL_B: GOVERNED_SOURCE_KIND,
    CorrectionPartition.CANARY: GOVERNED_SOURCE_KIND,
}


@dataclass(frozen=True, slots=True)
class SealedCampaignMember:
    """One candidate slot as the sealed manifest describes it, before it was executed."""

    candidate_id: UUID
    task_id: UUID
    group: str
    partition: CorrectionPartition
    campaign_id: UUID
    campaign_manifest_hash: str
    campaign_version: int
    verifier_profile_hash: str
    #: When the pre-outcome feature record was sealed. The chronology check is against this.
    feature_sealed_at: datetime


@dataclass(frozen=True, slots=True)
class SealedCampaignManifest:
    """The authority for who belonged to which partition. Not derived from the outcomes."""

    campaign_id: UUID
    manifest_hash: str
    members: Mapping[UUID, SealedCampaignMember]

    def member_for(self, candidate_id: UUID) -> SealedCampaignMember:
        member = self.members.get(candidate_id)
        if member is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"candidate {candidate_id} is not a member of campaign {self.campaign_id}",
            )
        return member


class CorrectionRankingObservationProjector:
    """Projects terminal correction outcomes into role-bound learned observations."""

    surface = CORRECTION_SURFACE

    def __init__(self, manifest: SealedCampaignManifest) -> None:
        self._manifest = manifest

    def project(
        self,
        outcome: RealityOutcomeReference,
        *,
        campaign_version: int,
        verifier_profile_hash: str,
        usage_rights_verified: bool,
        sensitivity: str = "internal",
    ) -> LearnedObservationRecord:
        """One outcome, one observation, with the partition deciding everything that matters."""
        if outcome.candidate_id is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a baseline run is not a correction-ranking observation",
            )
        member = self._manifest.member_for(outcome.candidate_id)

        if outcome.task_id != member.task_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"candidate {outcome.candidate_id} belongs to task {member.task_id}, but the "
                f"outcome names {outcome.task_id}",
            )
        if member.campaign_version != campaign_version:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"campaign version {campaign_version} does not match the sealed "
                f"{member.campaign_version}",
            )
        if member.verifier_profile_hash != verifier_profile_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the verifier profile differs from the one the manifest sealed",
            )
        if outcome.occurred_at < member.feature_sealed_at:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the outcome precedes its own feature record, so the features are not pre-outcome",
            )
        if outcome.strategy is not None and outcome.strategy in LABEL_PREDICTING_STRATEGIES:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"recipe {outcome.strategy.value!r} predicts its own label and cannot produce a "
                f"D2 correction-ranking observation",
            )
        if outcome.strategy is not None and outcome.strategy not in D2_NEUTRAL_RECIPES:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"recipe {outcome.strategy.value!r} is not a D2 neutral recipe",
            )

        provenance = ProvenanceClass(PARTITION_PROVENANCE[member.partition])
        return LearnedObservationRecord(
            observation_id=uuid5(
                CORRECTION_OBSERVATION_NAMESPACE,
                f"{member.campaign_manifest_hash}|{outcome.task_run_id}|{outcome.outcome_hash}",
            ),
            surface=self.surface,
            source_kind=_SOURCE_KIND[member.partition],
            source_task_id=outcome.task_id,
            source_run_id=outcome.task_run_id,
            source_event_id=outcome.source_event_id,
            source_payload_hash=outcome.outcome_hash,
            provenance_class=provenance,
            attribution=ObservationAttribution.DIRECT,
            status=ObservationStatus.ACCEPTED,
            verifier_status="passed" if outcome.hidden_verification_passed else "failed",
            verifier_evidence_hash=outcome.hidden_evidence_hash,
            usage_rights_verified=usage_rights_verified,
            sensitivity=sensitivity,
            decision_reason=(
                f"correction-ranking outcome from the sealed {member.partition.value} partition, "
                f"decided by the independent hidden verifier"
            ),
            evaluation_eligible=True,
            idempotency_key=f"{member.campaign_manifest_hash}:{outcome.task_run_id}",
            recorded_at=outcome.occurred_at,
        )
