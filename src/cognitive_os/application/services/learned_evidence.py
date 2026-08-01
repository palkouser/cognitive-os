"""The one way durable learned state changes.

Everything a caller may do to learned evidence goes through this service, and the
service composes three things it does not re-implement: the transition policy that the
in-memory registry already enforces, the immutable contracts in
`cognitive_os.domain.learned_evidence`, and a persistence port whose every write is
append-only.

Four boundaries live here because they cannot live in a single contract — each needs to
compare a request against durable state:

* an activation names the exact promotion assessment, approval and artifact lineage that
  authorised it, and every one of those must match what is actually stored;
* a real governed run is evaluation-only, so it can never be selected for training;
* an artifact reference is verified against the Artifact Store before lineage is
  recorded, and never deserialised;
* activation is refused outright unless the caller was explicitly authorised for it, so
  a default deployment cannot activate anything at all.

The service performs no provider call, no network access and no artifact execution.
Nothing here makes the system learn; it records what would have to be true for an
activation to be legitimate. See ADR 0086.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid5

from cognitive_os.application.ports.learned_evidence import (
    LearnedArtifactVerifierPort,
    LearnedEvidenceRepositoryPort,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import (
    LearnedComponentDescriptor,
    LearnedComponentState,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    ProvenanceClass,
)
from cognitive_os.domain.learned_evidence import (
    LearnedAccessRecord,
    LearnedActivationAction,
    LearnedActivationApproval,
    LearnedActivationReceipt,
    LearnedApprovalAuthorityKind,
    LearnedArtifactLineage,
    LearnedArtifactRole,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedObservationRecord,
    LearnedProjectionRow,
    LearnedReplayResult,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationStatus,
)
from cognitive_os.events.learned_event_service import LearnedCorrelationGap, LearnedEventService
from cognitive_os.events.learned_events import (
    LearnedAccessRecorded,
    LearnedActivationApprovalRecorded,
    LearnedArtifactLineageLinked,
    LearnedBaselineLadderEvaluated,
    LearnedCapacityMeasured,
    LearnedComponentDisabled,
    LearnedComponentEnabled,
    LearnedComponentRegistered,
    LearnedComponentRetracted,
    LearnedComponentRolledBack,
    LearnedDistributionCompared,
    LearnedEventPayload,
    LearnedForgettingAssessed,
    LearnedInvarianceVerified,
    LearnedObservationRecorded,
    LearnedOutOfDistributionAssessed,
    LearnedPromotionAssessed,
    LearnedShadowPredictionRecorded,
    LearnedSubjectEventPayload,
)
from cognitive_os.learning.registry import durable_transition_is_legal, transition_is_legal

#: How long an artifact verification stays usable as activation evidence. An activation
#: justified by a months-old hash check is justified by a memory, not by the bytes.
DEFAULT_ARTIFACT_VERIFICATION_MAX_AGE = timedelta(days=7)

#: Correlation failures kept for inspection. Bounded so a long-running process with an
#: unhealthy Event Store cannot grow this list without limit.
_MAX_RETAINED_CORRELATION_FAILURES = 256

#: Lifecycle states whose entry an existing learned event type describes *exactly*.
#:
#: Deliberately partial. Entering `SHADOW` is not the same fact as
#: `learned.shadow_prediction_recorded`, and entering `VERIFIED` has no existing event at
#: all. Reusing a near-miss event type would put a claim in the audit stream that did not
#: happen, and inventing event types beyond the four Sprint 21C1 authorises would widen
#: the schema for no use case. So those two steps are recorded in the learned ledger —
#: which is the authority — and are correlated by nothing. Health reads this same map, so
#: an absent event for those states is a known silence rather than an unexplained gap.
STATE_EVENT_TYPES: dict[LearnedComponentState, type[LearnedEventPayload]] = {
    LearnedComponentState.REGISTERED: LearnedComponentRegistered,
    LearnedComponentState.ACTIVE: LearnedComponentEnabled,
    LearnedComponentState.DISABLED: LearnedComponentDisabled,
    LearnedComponentState.RETRACTED: LearnedComponentRetracted,
}

#: Which existing learned event type describes each evidence kind. Every kind maps to an
#: event whose semantics already match exactly; nothing is invented to fill the table.
EVIDENCE_EVENT_TYPES: dict[LearnedEvidenceKind, type[LearnedEventPayload]] = {
    LearnedEvidenceKind.PREDICTION: LearnedShadowPredictionRecorded,
    LearnedEvidenceKind.SHADOW_RESULT: LearnedShadowPredictionRecorded,
    LearnedEvidenceKind.MANDATORY_PATH_INVARIANCE: LearnedInvarianceVerified,
    LearnedEvidenceKind.FORGETTING_ASSESSMENT: LearnedForgettingAssessed,
    LearnedEvidenceKind.DISTRIBUTION_COMPARISON: LearnedDistributionCompared,
    LearnedEvidenceKind.RETRIEVAL_CAPACITY: LearnedCapacityMeasured,
    LearnedEvidenceKind.BASELINE_LADDER: LearnedBaselineLadderEvaluated,
    LearnedEvidenceKind.OUT_OF_DISTRIBUTION_ASSESSMENT: LearnedOutOfDistributionAssessed,
    LearnedEvidenceKind.PROMOTION_ASSESSMENT: LearnedPromotionAssessed,
}


class LearnedEvidenceService:
    """Lifecycle, evidence, intake and activation over a durable learned store."""

    def __init__(
        self,
        repository: LearnedEvidenceRepositoryPort,
        *,
        artifacts: LearnedArtifactVerifierPort | None = None,
        events: LearnedEventService | None = None,
        activation_actors: frozenset[str] = frozenset(),
        artifact_verification_max_age: timedelta = DEFAULT_ARTIFACT_VERIFICATION_MAX_AGE,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """`activation_actors` is empty by default, which is the whole point.

        Persistence support for activation is not authorisation to activate. A caller
        that has not been named here cannot reach `ACTIVE` through this service, so a
        default deployment activates nothing even if every other precondition is met.
        """
        self._repository = repository
        self._artifacts = artifacts
        self._events = events
        self._activation_actors = activation_actors
        self._max_verification_age = artifact_verification_max_age
        self._clock = clock
        self._correlation_failures: list[LearnedCorrelationGap] = []

    # ------------------------------------------------------------------ lifecycle

    async def register_component(
        self,
        descriptor: LearnedComponentDescriptor,
        *,
        actor: str,
        authority: str,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID,
        descriptor_version: str | None = None,
    ) -> LearnedComponentRevisionRecord:
        """Create revision 1 in `REGISTERED`. Registration authorises nothing further."""
        revision = LearnedComponentRevisionRecord(
            component_id=descriptor.component_id,
            revision=1,
            surface=descriptor.surface,
            state_after=LearnedComponentState.REGISTERED,
            descriptor_hash=descriptor.content_hash,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=self._clock(),
        )
        stored = await self._repository.register_component(
            revision=revision, descriptor_version=descriptor_version or descriptor.version
        )
        await self._correlate_state(stored, correlation_id)
        return stored

    async def advance_component(
        self,
        component_id: str,
        target: LearnedComponentState,
        *,
        descriptor: LearnedComponentDescriptor,
        actor: str,
        authority: str,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID,
    ) -> LearnedComponentRevisionRecord:
        """One ordinary lifecycle step.

        `ACTIVE` is refused here even when the transition table would allow it. Reaching
        the active state requires evidence this method has no way to check, so it has a
        method of its own; otherwise the evidence requirement would be advisory.
        """
        if target is LearnedComponentState.ACTIVE:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "activation is not an ordinary transition: use activate() or roll_back(), "
                "which require the promotion assessment and approval that authorise it",
            )
        current = await self._require_component(component_id)
        self._require_descriptor_matches(descriptor, current)
        if not transition_is_legal(current.current_state, target):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id}: {current.current_state.value} -> {target.value}",
            )
        revision = LearnedComponentRevisionRecord(
            component_id=component_id,
            revision=current.current_revision + 1,
            previous_revision=current.current_revision,
            surface=current.surface,
            state_before=current.current_state,
            state_after=target,
            descriptor_hash=descriptor.content_hash,
            artifact_lineage_id=current.artifact_lineage_id,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=self._clock(),
        )
        stored = await self._repository.advance_component(
            revision=revision, expected_revision=current.current_revision
        )
        await self._correlate_state(stored, correlation_id)
        return stored

    async def get_component(self, component_id: str) -> LearnedProjectionRow | None:
        return await self._repository.get_component(component_id)

    async def active_component_for(self, surface: str) -> LearnedProjectionRow | None:
        """The durable projection is the activation authority, not an in-memory map."""
        return await self._repository.active_component_for(surface)

    async def component_history(
        self, component_id: str, *, limit: int = 100, offset: int = 0
    ) -> tuple[LearnedComponentRevisionRecord, ...]:
        return await self._repository.component_history(component_id, limit=limit, offset=offset)

    # ------------------------------------------------------------------- lineage

    async def register_artifact_lineage(
        self,
        lineage: LearnedArtifactLineage,
        *,
        correlation_id: UUID,
        actor: str,
        authority: str,
        reason: str,
    ) -> LearnedArtifactLineage:
        """Record a reference to bytes that already exist, after checking they do.

        The bytes are hashed, never interpreted. `LearnedArtifactFormat.JOBLIB` may
        appear in a descriptor as a legacy value, and nothing in this path loads it.
        """
        if self._artifacts is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "artifact lineage cannot be registered without an Artifact Store to "
                "verify it against; an unverified reference is not lineage",
            )
        metadata = await self._artifacts.artifact_metadata(lineage.artifact_id)
        if metadata is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"artifact {lineage.artifact_id} is not in the Artifact Store",
            )
        if metadata.content_hash != lineage.declared_content_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"artifact {lineage.artifact_id} is recorded with a different content hash "
                "than this lineage declares",
            )
        if metadata.size_bytes != lineage.size_bytes:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"artifact {lineage.artifact_id} is {metadata.size_bytes} bytes, "
                f"not the {lineage.size_bytes} this lineage declares",
            )
        if not await self._artifacts.verify_artifact(lineage.artifact_id):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.INTEGRITY_FAILURE,
                f"artifact {lineage.artifact_id} does not hash to its recorded content hash",
            )
        stored = await self._repository.record_artifact_lineage(lineage)
        await self._correlate(
            LearnedArtifactLineageLinked(
                subject_type="artifact_lineage",
                subject_id=str(stored.lineage_id),
                component_id=stored.component_id,
                surface=stored.component_id or str(stored.dataset_id),
                content_hash=stored.content_hash,
                actor=actor,
                authority=authority,
                reason=reason,
                occurred_at=stored.verified_at,
            ),
            subject=str(stored.lineage_id),
            correlation_id=correlation_id,
        )
        return stored

    # ------------------------------------------------------------------ evidence

    async def record_evidence(
        self,
        evidence: LearnedEvidenceRecord,
        *,
        correlation_id: UUID,
        actor: str,
        authority: str,
        reason: str,
    ) -> LearnedEvidenceRecord:
        """Append one typed evidence record. Evidence never changes a lifecycle state."""
        stored = await self._repository.record_evidence(evidence)
        if stored.component_id is not None:
            await self._correlate(
                EVIDENCE_EVENT_TYPES[stored.evidence_kind](
                    component_id=stored.component_id,
                    surface=stored.surface,
                    content_hash=stored.content_hash,
                    actor=actor,
                    authority=authority,
                    reason=reason,
                    occurred_at=stored.recorded_at,
                ),
                subject=stored.component_id,
                correlation_id=correlation_id,
            )
        return stored

    async def list_evidence(
        self,
        *,
        component_id: str | None = None,
        evidence_kind: LearnedEvidenceKind | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedEvidenceRecord, ...]:
        return await self._repository.list_evidence(
            component_id=component_id, evidence_kind=evidence_kind, limit=limit, offset=offset
        )

    # -------------------------------------------------------------------- intake

    async def record_observation(
        self,
        observation: LearnedObservationRecord,
        *,
        correlation_id: UUID,
        actor: str,
        authority: str,
    ) -> LearnedObservationRecord:
        """Accept, quarantine or reject one governed outcome.

        A real governed run is evaluation-only. The contract already refuses to call it
        training-eligible; this restates the rule at intake so the store never holds an
        accepted real run that some later selection step could read as trainable.
        """
        if (
            observation.provenance_class is ProvenanceClass.REAL_GOVERNED_RUN
            and observation.status is ObservationStatus.ACCEPTED
            and observation.training_eligible
        ):  # pragma: no cover - unreachable while the contract holds; asserted by test
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a real governed run is evaluation-only and can never be training-eligible",
            )
        stored = await self._repository.record_observation(observation)
        await self._correlate(
            LearnedObservationRecorded(
                subject_type="observation",
                subject_id=str(stored.observation_id),
                surface=stored.surface,
                content_hash=stored.content_hash,
                actor=actor,
                authority=authority,
                reason=stored.decision_reason,
                occurred_at=stored.recorded_at,
            ),
            subject=str(stored.observation_id),
            correlation_id=correlation_id,
        )
        return stored

    async def list_observations(
        self,
        *,
        surface: str | None = None,
        status: ObservationStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[LearnedObservationRecord, ...]:
        return await self._repository.list_observations(
            surface=surface, status=status, limit=limit, offset=offset
        )

    # ---------------------------------------------------------------- activation

    async def record_approval(
        self,
        approval: LearnedActivationApproval,
        *,
        correlation_id: UUID,
    ) -> LearnedActivationApproval:
        """Append an approval decision, including a refusal.

        A refusal is appended rather than dropped: proof that an activation was refused
        is exactly as auditable as proof that one was granted. The contract already
        refuses a *positive* approval from a model or provider identity, so a component
        cannot approve itself, while a model-issued refusal remains recordable.
        """
        stored = await self._repository.record_approval(approval)
        await self._correlate(
            LearnedActivationApprovalRecorded(
                component_id=stored.component_id,
                surface=stored.surface,
                content_hash=stored.content_hash,
                actor=stored.approver,
                authority=stored.approver_kind.value,
                reason=stored.reason,
                occurred_at=stored.approved_at,
            ),
            subject=stored.component_id,
            correlation_id=correlation_id,
        )
        return stored

    async def activate(
        self,
        *,
        descriptor: LearnedComponentDescriptor,
        component_revision: int,
        promotion_assessment: LearnedPromotionAssessment,
        approval: LearnedActivationApproval,
        lineage: LearnedArtifactLineage,
        actor: str,
        authority: str,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID,
    ) -> LearnedActivationReceipt:
        """Make one component active on its surface, or refuse and say exactly why.

        Every argument is checked against durable state rather than trusted: the
        assessment, the approval and the lineage must be the ones actually stored, and
        the component must still be at the revision the assessment was made about.
        """
        self._require_activation_authority(actor)
        component_id = descriptor.component_id
        current = await self._require_component(component_id)
        self._require_descriptor_matches(descriptor, current)

        if current.current_revision != component_revision:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.STALE_REVISION,
                f"{component_id} moved to revision {current.current_revision} after this "
                f"activation was prepared for revision {component_revision}",
            )
        if not transition_is_legal(current.current_state, LearnedComponentState.ACTIVE):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id} is {current.current_state.value}; only a verified "
                "component may be activated",
            )
        if not descriptor.promotable:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                "a component that cannot abstain cannot become active",
            )
        if (
            promotion_assessment.decision
            is not LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        ):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"the promotion assessment decided {promotion_assessment.decision.value}, "
                "which is not eligibility for operator approval",
            )
        if promotion_assessment.component_id != component_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the promotion assessment is about a different component",
            )
        await self._require_stored_assessment(promotion_assessment)
        await self._require_verified_lineage(lineage, component_id)
        await self._require_positive_approval(
            approval,
            component_id=component_id,
            component_revision=component_revision,
            surface=current.surface,
            promotion_assessment=promotion_assessment,
            lineage=lineage,
        )

        holder = await self._repository.active_component_for(current.surface)
        if holder is not None and holder.component_id != component_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE,
                f"surface {current.surface!r} is held by {holder.component_id}; disable it "
                "before activating another component",
            )

        previous = await self._repository.latest_activation_for(current.surface)
        now = self._clock()
        revision = LearnedComponentRevisionRecord(
            component_id=component_id,
            revision=current.current_revision + 1,
            previous_revision=current.current_revision,
            surface=current.surface,
            state_before=current.current_state,
            state_after=LearnedComponentState.ACTIVE,
            descriptor_hash=descriptor.content_hash,
            artifact_lineage_id=lineage.lineage_id,
            promotion_assessment_hash=promotion_assessment.content_hash,
            activation_approval_hash=approval.content_hash,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        receipt = LearnedActivationReceipt(
            receipt_id=_derive_receipt_id(revision),
            action=LearnedActivationAction.ACTIVATION,
            component_id=component_id,
            component_revision=revision.revision,
            surface=current.surface,
            artifact_lineage_id=lineage.lineage_id,
            promotion_assessment_hash=promotion_assessment.content_hash,
            approval_id=approval.approval_id,
            approval_hash=approval.content_hash,
            previous_receipt_id=previous.receipt_id if previous else None,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        stored_revision, stored_receipt = await self._repository.record_activation_step(
            revision=revision,
            expected_revision=current.current_revision,
            receipt=receipt,
        )
        await self._correlate_state(stored_revision, correlation_id)
        return stored_receipt

    async def disable(
        self,
        component_id: str,
        *,
        descriptor: LearnedComponentDescriptor,
        actor: str,
        authority: str,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID,
        rollback_permitted: bool,
    ) -> LearnedActivationReceipt:
        """Take a component off its surface. Always available, never gated on evidence.

        Disabling narrows what the system does, so it deliberately needs no approval:
        a governance control that is hard to switch off is not a control.

        `rollback_permitted` has no default on purpose. A disable that follows a failed
        canary and a disable that parks a healthy component look identical from here, and
        only the caller knows which one it is; a default would guess, and guessing the
        permissive answer is how a failed component gets restored by the rollback path.
        """
        current = await self._require_component(component_id)
        self._require_descriptor_matches(descriptor, current)
        if not transition_is_legal(current.current_state, LearnedComponentState.DISABLED):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id}: {current.current_state.value} -> disabled",
            )
        previous = await self._repository.latest_activation_for(current.surface)
        now = self._clock()
        revision = LearnedComponentRevisionRecord(
            component_id=component_id,
            revision=current.current_revision + 1,
            previous_revision=current.current_revision,
            surface=current.surface,
            state_before=current.current_state,
            state_after=LearnedComponentState.DISABLED,
            descriptor_hash=descriptor.content_hash,
            artifact_lineage_id=current.artifact_lineage_id,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        receipt = LearnedActivationReceipt(
            receipt_id=_derive_receipt_id(revision),
            action=LearnedActivationAction.DISABLE,
            component_id=component_id,
            component_revision=revision.revision,
            surface=current.surface,
            previous_receipt_id=previous.receipt_id if previous else None,
            rollback_permitted=rollback_permitted,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        stored_revision, stored_receipt = await self._repository.record_activation_step(
            revision=revision,
            expected_revision=current.current_revision,
            receipt=receipt,
        )
        await self._correlate_state(stored_revision, correlation_id)
        return stored_receipt

    async def roll_back(
        self,
        component_id: str,
        *,
        descriptor: LearnedComponentDescriptor,
        actor: str,
        authority: str,
        reason: str,
        idempotency_key: str,
        correlation_id: UUID,
    ) -> LearnedActivationReceipt:
        """Restore the exact prior activation named by this component's receipt chain.

        Not a generic re-activation: the target is read from the stored chain, never
        supplied by the caller, and its promotion, approval and lineage hashes are
        re-verified against what is stored before the component returns to `ACTIVE`. The
        ordinary transition table still refuses `DISABLED -> ACTIVE`, which is why this
        is a separate operation rather than an argument to `advance_component`.
        """
        self._require_activation_authority(actor)
        current = await self._require_component(component_id)
        self._require_descriptor_matches(descriptor, current)
        if current.current_state is not LearnedComponentState.DISABLED:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id} is {current.current_state.value}; only a disabled "
                "component can be rolled back to its prior activation",
            )

        refusal = await self._latest_disable(component_id)
        if refusal is not None and refusal.rollback_permitted is False:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id} was disabled with rollback_permitted=false "
                f"(receipt {refusal.receipt_id}); the disable that ended this activation was "
                "a refusal, not a pause, and restoring it is what the flag exists to prevent",
            )

        target = await self._prior_activation(component_id)
        if target is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"{component_id} has no prior activation to restore",
            )
        if target.approval_id is None or target.approval_hash is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the prior activation names no approval, so it cannot be restored",
            )
        approval = await self._repository.get_approval(target.approval_id)
        if approval is None or approval.content_hash != target.approval_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the approval that authorised the prior activation is missing or has "
                "changed; a rollback cannot invent the authority it restores",
            )
        if target.artifact_lineage_id is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the prior activation names no artifact lineage",
            )
        lineage = await self._repository.get_artifact_lineage(target.artifact_lineage_id)
        if lineage is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND,
                f"artifact lineage {target.artifact_lineage_id} is missing",
            )
        await self._require_verified_lineage(lineage, component_id)

        holder = await self._repository.active_component_for(current.surface)
        if holder is not None and holder.component_id != component_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.SURFACE_ALREADY_ACTIVE,
                f"surface {current.surface!r} is held by {holder.component_id}",
            )

        latest = await self._repository.latest_activation_for(current.surface)
        now = self._clock()
        revision = LearnedComponentRevisionRecord(
            component_id=component_id,
            revision=current.current_revision + 1,
            previous_revision=current.current_revision,
            surface=current.surface,
            state_before=current.current_state,
            state_after=LearnedComponentState.ACTIVE,
            descriptor_hash=descriptor.content_hash,
            artifact_lineage_id=target.artifact_lineage_id,
            promotion_assessment_hash=target.promotion_assessment_hash,
            activation_approval_hash=target.approval_hash,
            rollback_target_revision=target.component_revision,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        if not durable_transition_is_legal(
            current.current_state,
            LearnedComponentState.ACTIVE,
            rollback_target_revision=revision.rollback_target_revision,
        ):  # pragma: no cover - defensive; the state check above already guarantees it
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.ILLEGAL_TRANSITION,
                f"{component_id}: {current.current_state.value} -> active",
            )
        receipt = LearnedActivationReceipt(
            receipt_id=_derive_receipt_id(revision),
            action=LearnedActivationAction.ROLLBACK,
            component_id=component_id,
            component_revision=revision.revision,
            surface=current.surface,
            artifact_lineage_id=target.artifact_lineage_id,
            promotion_assessment_hash=target.promotion_assessment_hash,
            approval_id=target.approval_id,
            approval_hash=target.approval_hash,
            previous_receipt_id=latest.receipt_id if latest else None,
            rollback_target_receipt_id=target.receipt_id,
            actor=actor,
            authority=authority,
            reason=reason,
            idempotency_key=idempotency_key,
            recorded_at=now,
        )
        stored_revision, stored_receipt = await self._repository.record_activation_step(
            revision=revision,
            expected_revision=current.current_revision,
            receipt=receipt,
        )
        await self._correlate(
            LearnedComponentRolledBack(
                component_id=component_id,
                surface=current.surface,
                content_hash=stored_revision.content_hash,
                actor=actor,
                authority=authority,
                reason=reason,
                occurred_at=stored_revision.recorded_at,
            ),
            subject=component_id,
            correlation_id=correlation_id,
        )
        return stored_receipt

    # ---------------------------------------------------------------- audit

    async def record_access(
        self, access: LearnedAccessRecord, *, correlation_id: UUID
    ) -> LearnedAccessRecord:
        """Audit a read or export of sensitive learned material, by reference only."""
        stored = await self._repository.record_access(access)
        await self._correlate(
            LearnedAccessRecorded(
                subject_type=stored.target_type,
                subject_id=stored.target_id,
                surface=stored.target_type,
                content_hash=stored.content_hash,
                actor=stored.actor,
                authority=stored.authority,
                reason=stored.purpose,
                occurred_at=stored.recorded_at,
            ),
            subject=stored.target_id,
            correlation_id=correlation_id,
        )
        return stored

    async def replay(self) -> LearnedReplayResult:
        """Rebuild every projection from history and report whether they agree."""
        return await self._repository.replay()

    @property
    def correlation_failures(self) -> tuple[LearnedCorrelationGap, ...]:
        """Audit events this process could not append.

        Warning-level: the learned write already committed and remains authoritative.
        Health re-derives the same gaps statelessly from the Event Store, so a restart
        does not hide them.
        """
        return tuple(self._correlation_failures)

    # ------------------------------------------------------------------ internals

    def _require_activation_authority(self, actor: str) -> None:
        if actor not in self._activation_actors:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"{actor!r} is not authorised to activate learned components; runtime "
                "activation is disabled unless an authorised caller invokes it",
            )

    async def _require_component(self, component_id: str) -> LearnedProjectionRow:
        current = await self._repository.get_component(component_id)
        if current is None:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.NOT_FOUND, f"unknown learned component: {component_id}"
            )
        return current

    @staticmethod
    def _require_descriptor_matches(
        descriptor: LearnedComponentDescriptor, current: LearnedProjectionRow
    ) -> None:
        """The descriptor a caller presents must be the one the store already knows.

        Without this, a caller could describe a component one way at registration and
        another way at activation, and the promotable check would be about a descriptor
        the store never saw.
        """
        if descriptor.component_id != current.component_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"descriptor is for {descriptor.component_id}, not {current.component_id}",
            )
        if descriptor.content_hash != current.descriptor_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"{current.component_id} is registered with a different descriptor hash",
            )

    async def _require_stored_assessment(self, assessment: LearnedPromotionAssessment) -> None:
        stored = await self._repository.list_evidence(
            component_id=assessment.component_id,
            evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
            limit=1000,
        )
        if not any(record.payload_hash == assessment.content_hash for record in stored):
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the promotion assessment was never recorded as evidence, so the "
                "activation cannot be justified by it after the fact",
            )

    async def _require_verified_lineage(
        self, lineage: LearnedArtifactLineage, component_id: str
    ) -> None:
        stored = await self._repository.get_artifact_lineage(lineage.lineage_id)
        if stored is None or stored.content_hash != lineage.content_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the artifact lineage presented is not the one recorded",
            )
        if stored.component_id != component_id:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"artifact lineage {stored.lineage_id} belongs to {stored.component_id}",
            )
        if stored.role is not LearnedArtifactRole.MODEL:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"an activation must name a model artifact, not a {stored.role.value}",
            )
        age = self._clock() - stored.verified_at
        if age > self._max_verification_age:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"artifact verification is {age} old, beyond the "
                f"{self._max_verification_age} an activation may rely on",
            )

    async def _require_positive_approval(
        self,
        approval: LearnedActivationApproval,
        *,
        component_id: str,
        component_revision: int,
        surface: str,
        promotion_assessment: LearnedPromotionAssessment,
        lineage: LearnedArtifactLineage,
    ) -> None:
        stored = await self._repository.get_approval(approval.approval_id)
        if stored is None or stored.content_hash != approval.content_hash:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "the approval presented is not the one recorded",
            )
        if not stored.approved:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"approval {stored.approval_id} refused this activation",
            )
        if stored.approver_kind is not LearnedApprovalAuthorityKind.HUMAN_OPERATOR:
            # pragma: no cover - the contract refuses this shape; asserted by test
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a model or provider identity cannot approve an activation",
            )
        mismatches = [
            name
            for name, expected, found in (
                ("component_id", component_id, stored.component_id),
                ("component_revision", component_revision, stored.component_revision),
                ("surface", surface, stored.surface),
                (
                    "promotion_assessment_hash",
                    promotion_assessment.content_hash,
                    stored.promotion_assessment_hash,
                ),
                ("artifact_lineage_id", lineage.lineage_id, stored.artifact_lineage_id),
            )
            if expected != found
        ]
        if mismatches:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"the approval does not authorise this exact activation: {sorted(mismatches)}",
            )

    async def _latest_disable(self, component_id: str) -> LearnedActivationReceipt | None:
        """The disable that put this component into its current state.

        Walked from the surface head rather than read off the component row, because the
        refusal has to be structural: it must come from the durable chain, not from a state
        column a later write could overwrite.
        """
        current = await self._repository.get_component(component_id)
        if current is None:  # pragma: no cover - callers check first
            return None
        receipt = await self._repository.latest_activation_for(current.surface)
        while receipt is not None:
            if receipt.component_id == component_id:
                if receipt.action is LearnedActivationAction.DISABLE:
                    return receipt
                if receipt.action is LearnedActivationAction.ACTIVATION:
                    return None
            if receipt.previous_receipt_id is None:
                return None
            receipt = await self._repository.get_activation_receipt(receipt.previous_receipt_id)
        return None

    async def _prior_activation(self, component_id: str) -> LearnedActivationReceipt | None:
        """Walk this component's receipt chain back to the activation it last held."""
        current = await self._repository.get_component(component_id)
        if current is None:  # pragma: no cover - callers check first
            return None
        receipt = await self._repository.latest_activation_for(current.surface)
        while receipt is not None:
            if (
                receipt.action is LearnedActivationAction.ACTIVATION
                and receipt.component_id == component_id
            ):
                return receipt
            if receipt.previous_receipt_id is None:
                return None
            receipt = await self._repository.get_activation_receipt(receipt.previous_receipt_id)
        return None

    async def _correlate_state(
        self, revision: LearnedComponentRevisionRecord, correlation_id: UUID
    ) -> None:
        payload_model = STATE_EVENT_TYPES.get(revision.state_after)
        if payload_model is None:
            return
        await self._correlate(
            payload_model(
                component_id=revision.component_id,
                surface=revision.surface,
                content_hash=revision.content_hash,
                actor=revision.actor,
                authority=revision.authority,
                reason=revision.reason,
                occurred_at=revision.recorded_at,
            ),
            subject=revision.component_id,
            correlation_id=correlation_id,
        )

    async def _correlate(
        self,
        payload: LearnedEventPayload | LearnedSubjectEventPayload,
        *,
        subject: str,
        correlation_id: UUID,
    ) -> None:
        """Append the audit event, and never let its failure undo a committed write.

        The learned ledger has already committed by the time this runs. Raising here
        would make the Event Store a second authority over learned correctness, which
        ADR 0086 rejects: the caller would see a failure for a change that happened.
        """
        if self._events is None:
            return
        try:
            await self._events.append(subject, payload, correlation_id=correlation_id)
        except Exception as error:
            # Any append failure is a warning, so the except is deliberately broad: a
            # narrower clause would let an unanticipated store error escape and undo a
            # committed learned write in the caller's eyes.
            self._record_correlation_failure(payload, subject=subject, error=error)

    def _record_correlation_failure(
        self,
        payload: LearnedEventPayload | LearnedSubjectEventPayload,
        *,
        subject: str,
        error: Exception,
    ) -> None:
        if len(self._correlation_failures) >= _MAX_RETAINED_CORRELATION_FAILURES:
            self._correlation_failures.pop(0)
        self._correlation_failures.append(
            LearnedCorrelationGap(
                subject=subject,
                content_hash=payload.content_hash,
                expected_event_type=payload.event_type,
                detail=f"{type(error).__name__}: {error}",
            )
        )


def _derive_receipt_id(revision: LearnedComponentRevisionRecord) -> UUID:
    """A receipt ID derived from the revision it records, not a fresh random one.

    Idempotency has to survive a retry that recreates the receipt object. A random ID
    would make the second attempt look like a different receipt, so the append would be
    accepted and the ledger would hold two receipts for one state change.
    """
    return uuid5(_RECEIPT_NAMESPACE, revision.content_hash)


#: Fixed forever: changing it would give a replayed activation a different receipt ID.
_RECEIPT_NAMESPACE = UUID("2b7f5c14-9d3a-5e46-8c02-7a1f6d9b4e33")
