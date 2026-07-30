"""Turn recorded coding runs into evaluation-only learned observations, §S21C3-013.

The harvester is the only thing that converts a C3 execution into something the learning
plane will look at, and it is deliberately narrow about what qualifies.

It resolves from the event, not from the campaign's memory of what it ran. A campaign that
told intake what it believed it had produced would be asserting its own results; reading the
`coding.outcome_recorded` envelope and then reading the referenced bytes back out of the
Artifact Store means the reference offered to intake describes bytes that exist right now.
Source bytes that are missing, or whose hash no longer matches, fail closed — a source that
changed after the fact is either a different outcome or a corrupted one.

What it will not do, in order of how badly it would corrupt the corpus:

* it never offers provider prose as a real governed run. The executed sandbox outcome is the
  run; the advisory text that suggested the patch stays `OPERATOR_SUPPLIED` in the C2
  governance ledger, where ADR 0087 put it;
* it never claims `DIRECT` attribution for an outcome the hidden verifier could not measure.
  An unverifiable run is offered with `UNKNOWN` attribution, which intake quarantines, and a
  quarantined observation is visible rather than absent;
* it never marks anything training-eligible. `LearnedObservationRecord.evaluation_eligible`
  is the only affirmative flag intake sets, and the C1 dataset builder plus a database CHECK
  refuse a real governed run in a training snapshot regardless of what arrives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.coding import CodingOutcomeStatus
from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedObservationRecord,
    ObservationAttribution,
)
from cognitive_os.domain.reality import RealityOutcomeReference, RealityTaskManifest
from cognitive_os.events.coding_events import CodingOutcomeRecorded

from .learned_intake import LearnedObservationIntake

#: The learning surface C3 produces evidence for. D1 pre-registers what is learned on it; C3
#: only establishes that honest evidence exists.
CODING_REPAIR_SURFACE = "coding.repair"

#: `governed_task_run` is in `REAL_GOVERNED_SOURCE_KINDS`, so intake will accept the
#: provenance below as credible. That is the whole reason this harvester has to be careful:
#: the label is available, and nothing but this code stops it being applied to prose.
CODING_TASK_RUN_SOURCE_KIND = "governed_task_run"

#: Statuses that mean the run reached a conclusion. A cancelled or budget-exhausted run is
#: not evidence about a candidate, and offering one would put "we stopped early" into the
#: corpus as though it were "this patch did not work".
_TERMINAL_STATUSES = frozenset(
    {
        CodingOutcomeStatus.ACCEPTED,
        CodingOutcomeStatus.FAILED,
        CodingOutcomeStatus.REJECTED,
        CodingOutcomeStatus.SECURITY_FAILURE,
    }
)


class OutcomeHarvestError(RuntimeError):
    """The recorded outcome could not be resolved, so it is not offered."""


@dataclass(frozen=True, slots=True)
class HarvestedOutcome:
    reference: RealityOutcomeReference
    governed: GovernedOutcomeReference
    observation: LearnedObservationRecord

    @property
    def evaluation_eligible(self) -> bool:
        return self.observation.evaluation_eligible


class RealityOutcomeHarvester:
    def __init__(
        self,
        artifacts: ArtifactStorePort,
        event_store: EventStorePort,
        intake: LearnedObservationIntake,
    ) -> None:
        self._artifacts = artifacts
        self._store = event_store
        self._intake = intake

    async def harvest(
        self,
        *,
        event_id: UUID,
        task: RealityTaskManifest,
        correlation_id: UUID,
    ) -> HarvestedOutcome:
        """Resolve one recorded outcome and offer it to intake exactly once."""
        payload = await self._resolve_event(event_id)
        if payload.task_id != task.task_id:
            raise OutcomeHarvestError("recorded outcome belongs to a different task")
        if payload.task_manifest_hash != task.content_hash:
            raise OutcomeHarvestError(
                "recorded outcome was produced against a different task manifest revision"
            )
        if payload.final_status not in _TERMINAL_STATUSES:
            raise OutcomeHarvestError(
                f"outcome status {payload.final_status.value!r} is not a terminal result"
            )

        await self._require_bytes(payload.outcome_artifact_id, payload.outcome_artifact_hash)
        await self._require_bytes(payload.hidden_evidence_artifact_id, payload.hidden_evidence_hash)

        governed = GovernedOutcomeReference(
            surface=CODING_REPAIR_SURFACE,
            source_kind=CODING_TASK_RUN_SOURCE_KIND,
            source_task_id=payload.task_id,
            source_run_id=payload.task_run_id,
            source_event_id=event_id,
            source_payload_hash=payload.outcome_artifact_hash,
            provenance_class=ProvenanceClass.REAL_GOVERNED_RUN,
            attribution=self._attribution(payload),
            usage_rights_verified=task.rights.rights_verified,
            sensitivity=task.rights.sensitivity.value,
            verifier_status="passed" if payload.hidden_verification_passed else "failed",
            verifier_evidence_hash=payload.hidden_evidence_hash,
            occurred_at=payload.occurred_at,
        )
        observation = await self._intake.offer(governed, correlation_id=correlation_id)
        return HarvestedOutcome(
            reference=self._reference(payload, event_id),
            governed=governed,
            observation=observation,
        )

    @staticmethod
    def _attribution(payload: CodingOutcomeRecorded) -> ObservationAttribution:
        """`DIRECT` only when the hidden verifier actually decided.

        The hidden run is what independently supports the claim, so an outcome recorded
        without a passing *or* failing hidden result is attributable to nothing. Rather than
        rejecting it here, it is offered as `UNKNOWN` so intake quarantines it and an operator
        can see how many runs were unmeasurable.
        """
        if payload.final_status is CodingOutcomeStatus.SECURITY_FAILURE:
            return ObservationAttribution.UNKNOWN
        return ObservationAttribution.DIRECT

    async def _resolve_event(self, event_id: UUID) -> CodingOutcomeRecorded:
        stored = await self._store.get_event(event_id)
        if stored is None:
            raise OutcomeHarvestError(f"no event with identity {event_id}")
        if stored.envelope.event_type != CodingOutcomeRecorded.event_type:
            raise OutcomeHarvestError(
                f"event {event_id} is a {stored.envelope.event_type!r}, not a recorded outcome"
            )
        return CodingOutcomeRecorded.model_validate(stored.envelope.payload)

    async def _require_bytes(self, artifact_id: UUID, expected_hash: str) -> None:
        """Read the blob back. `describe` alone would trust the metadata row.

        The inconsistent development Artifact Store pair is four rows whose files are absent,
        so metadata that says bytes exist is demonstrably not evidence that they do.
        """
        artifact = await self._artifacts.describe(artifact_id)
        if artifact is None:
            raise OutcomeHarvestError(f"recorded outcome references unknown artifact {artifact_id}")
        if artifact.content_hash != expected_hash:
            raise OutcomeHarvestError(
                f"artifact {artifact_id} no longer matches the hash the outcome recorded"
            )
        if not await self._artifacts.verify(artifact_id):
            raise OutcomeHarvestError(f"artifact {artifact_id} could not be verified on disk")

    @staticmethod
    def _reference(payload: CodingOutcomeRecorded, event_id: UUID) -> RealityOutcomeReference:
        return RealityOutcomeReference(
            task_run_id=payload.task_run_id,
            run_kind=payload.run_kind,
            task_id=payload.task_id,
            task_manifest_hash=payload.task_manifest_hash,
            candidate_id=payload.candidate_id,
            strategy=payload.candidate_strategy,
            outcome_hash=payload.outcome_hash,
            outcome_artifact_id=payload.outcome_artifact_id,
            outcome_artifact_hash=payload.outcome_artifact_hash,
            hidden_evidence_artifact_id=payload.hidden_evidence_artifact_id,
            hidden_evidence_hash=payload.hidden_evidence_hash,
            final_status=payload.final_status,
            hidden_verification_passed=payload.hidden_verification_passed,
            provider_output_id=payload.provider_output_id,
            source_event_id=event_id,
            occurred_at=payload.occurred_at,
        )
