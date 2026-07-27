"""Quarantine review and read audit for governed observations.

Quarantine is where intake puts what it could not decide. Someone has to look, and the
looking itself is the risk this module manages: a reviewer needs enough to judge, an
audit trail needs to record that they looked, and neither needs the sensitive body.

Three rules make review safe to give to a human:

* **the original is never rewritten.** A review appends a *replacement* record and leaves
  the quarantine entry exactly where it was, so the queue remains a record of what was
  once uncertain rather than a list of what nobody got around to;
* **only a human operator may review.** A model or provider identity clearing its own
  evidence is the same failure as a component approving its own activation, and it is
  refused in the same way;
* **listing is a read, and reads of sensitive material are audited.** The listing returns
  identity, classification and hashes — never a body — and appends an access record
  naming who looked and why.

See ADR 0086.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid5

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime, utc_now
from cognitive_os.domain.learned_evidence import (
    LearnedAccessRecord,
    LearnedApprovalAuthorityKind,
    LearnedObservationRecord,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
    ObservationAttribution,
    ObservationStatus,
)

from .learned_evidence import LearnedEvidenceService

#: Fixed forever: a review's identity must not move when the code around it changes.
REVIEW_NAMESPACE = UUID("c3a17f40-58d6-5e29-9b74-2f81dc0a6e35")

#: Sensitivities whose reads must leave an access record. `public` is excluded because an
#: audit trail nobody can distinguish from noise is an audit trail nobody reads.
AUDITED_SENSITIVITIES: frozenset[str] = frozenset({"internal", "restricted"})

#: The largest quarantine page a reviewer can pull in one call.
MAX_REVIEW_PAGE = 200


class QuarantineEntry(ImmutableContractModel):
    """What a reviewer is shown: enough to judge, and no example body.

    Every field here is identity, classification or a hash. The observation record itself
    never held a body, so this is not a filtered view of something more revealing — it is
    the shape the learning plane stores, restated as what a reviewer needs.
    """

    observation_id: UUID
    surface: NonEmptyStr
    source_kind: NonEmptyStr
    source_task_id: UUID | None = None
    source_run_id: UUID | None = None
    source_event_id: UUID | None = None
    source_payload_hash: Sha256Hex
    provenance_class: NonEmptyStr
    attribution: NonEmptyStr
    sensitivity: NonEmptyStr
    #: The stable code intake assigned, without the prose that followed it.
    decision_code: NonEmptyStr
    verifier_status: NonEmptyStr | None = None
    recorded_at: UtcDatetime


class QuarantineReviewOutcome(ImmutableContractModel):
    """The result of one review: what was decided, and what it produced."""

    observation_id: UUID
    replacement_id: UUID
    status: NonEmptyStr
    reviewer: NonEmptyStr
    reason: NonEmptyStr
    access_id: UUID | None = None
    reviewed_count: int = Field(default=1, ge=1)


def _decision_code(observation: LearnedObservationRecord) -> str:
    """The code intake recorded, which is the first token of the decision reason."""
    return observation.decision_reason.split(":", 1)[0].strip() or "unknown"


class LearnedQuarantineReview:
    """Bounded, audited review of quarantined governed outcomes."""

    def __init__(
        self,
        service: LearnedEvidenceService,
        *,
        reviewers: frozenset[str] = frozenset(),
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """`reviewers` is empty by default, so a fresh deployment can review nothing."""
        self._service = service
        self._reviewers = reviewers
        self._clock = clock

    async def list_quarantined(
        self,
        *,
        actor: str,
        authority: str,
        purpose: str,
        surface: str | None = None,
        limit: int = 50,
    ) -> tuple[tuple[QuarantineEntry, ...], LearnedAccessRecord | None]:
        """Redacted quarantine entries, plus the access record the read produced.

        The access record is returned rather than hidden so a caller cannot claim to have
        listed without the audit; if every entry is public, there is nothing to audit and
        the record is `None`.
        """
        observations = await self._service.list_observations(
            surface=surface, status=ObservationStatus.QUARANTINED, limit=min(limit, MAX_REVIEW_PAGE)
        )
        entries = tuple(
            QuarantineEntry(
                observation_id=item.observation_id,
                surface=item.surface,
                source_kind=item.source_kind,
                source_task_id=item.source_task_id,
                source_run_id=item.source_run_id,
                source_event_id=item.source_event_id,
                source_payload_hash=item.source_payload_hash,
                provenance_class=item.provenance_class.value,
                attribution=item.attribution.value,
                sensitivity=item.sensitivity,
                decision_code=_decision_code(item),
                verifier_status=item.verifier_status,
                recorded_at=item.recorded_at,
            )
            for item in observations
        )
        access = None
        if any(entry.sensitivity in AUDITED_SENSITIVITIES for entry in entries):
            access = await self._audit(
                actor=actor,
                authority=authority,
                target_type="quarantine_queue",
                target_id=surface or "*",
                purpose=purpose,
                decision=f"listed {len(entries)} quarantined observations",
            )
        return entries, access

    async def review(
        self,
        observation_id: UUID,
        *,
        accept: bool,
        reviewer: str,
        reviewer_kind: LearnedApprovalAuthorityKind,
        authority: str,
        reason: str,
        correlation_id: UUID,
    ) -> QuarantineReviewOutcome:
        """Append a replacement decision. The quarantine record itself is untouched.

        The replacement carries its own idempotency key, derived from the original, so a
        repeated review is a free no-op while the original entry stays exactly where it
        was — which is what makes the queue a history rather than a worklist.
        """
        if reviewer_kind is not LearnedApprovalAuthorityKind.HUMAN_OPERATOR:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a model or provider identity cannot review learned evidence: clearing "
                "one's own quarantine is the same failure as approving one's own activation",
            )
        if reviewer not in self._reviewers:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                f"{reviewer!r} is not authorised to review quarantined observations",
            )
        if not reason.strip():
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "a review must say why; an unreasoned decision is not reviewable later",
            )

        original = await self._require_quarantined(observation_id)
        if accept and not original.usage_rights_verified:
            raise LearnedRepositoryError(
                LearnedRepositoryConflict.EVIDENCE_MISMATCH,
                "an observation without verified usage rights cannot be accepted by review",
            )
        status = ObservationStatus.ACCEPTED if accept else ObservationStatus.REJECTED
        replacement = LearnedObservationRecord(
            observation_id=uuid5(REVIEW_NAMESPACE, f"{observation_id}|{status.value}"),
            surface=original.surface,
            source_kind=original.source_kind,
            source_task_id=original.source_task_id,
            source_run_id=original.source_run_id,
            source_event_id=original.source_event_id,
            source_payload_hash=original.source_payload_hash,
            provenance_class=original.provenance_class,
            # Review resolves the ambiguity that caused the quarantine, so an accepted
            # replacement must state the attribution the reviewer actually established.
            attribution=original.attribution if not accept else _attributed(original),
            status=status,
            verifier_status=original.verifier_status,
            verifier_evidence_hash=original.verifier_evidence_hash,
            usage_rights_verified=original.usage_rights_verified,
            sensitivity=original.sensitivity,
            decision_reason=f"reviewed_{status.value}: {reason.strip()}",
            evaluation_eligible=accept,
            idempotency_key=f"review:{original.idempotency_key}:{status.value}",
            recorded_at=self._clock(),
        )
        stored = await self._service.record_observation(
            replacement, correlation_id=correlation_id, actor=reviewer, authority=authority
        )
        access = None
        if original.sensitivity in AUDITED_SENSITIVITIES:
            access = await self._audit(
                actor=reviewer,
                authority=authority,
                target_type="observation",
                target_id=str(observation_id),
                purpose=f"quarantine review: {reason.strip()}",
                decision=status.value,
            )
        return QuarantineReviewOutcome(
            observation_id=observation_id,
            replacement_id=stored.observation_id,
            status=status.value,
            reviewer=reviewer,
            reason=reason.strip(),
            access_id=access.access_id if access is not None else None,
        )

    async def _require_quarantined(self, observation_id: UUID) -> LearnedObservationRecord:
        for item in await self._service.list_observations(
            status=ObservationStatus.QUARANTINED, limit=MAX_REVIEW_PAGE
        ):
            if item.observation_id == observation_id:
                return item
        raise LearnedRepositoryError(
            LearnedRepositoryConflict.NOT_FOUND,
            f"no quarantined observation {observation_id}",
        )

    async def _audit(
        self,
        *,
        actor: str,
        authority: str,
        target_type: str,
        target_id: str,
        purpose: str,
        decision: str,
    ) -> LearnedAccessRecord:
        recorded_at = self._clock()
        record = LearnedAccessRecord(
            access_id=uuid5(
                REVIEW_NAMESPACE,
                f"{actor}|{target_type}|{target_id}|{purpose}|{decision}|{recorded_at.isoformat()}",
            ),
            actor=actor,
            authority=authority,
            target_type=target_type,
            target_id=target_id,
            purpose=purpose,
            decision=decision,
            recorded_at=recorded_at,
        )
        return await self._service.record_access(record, correlation_id=record.access_id)


def _attributed(original: LearnedObservationRecord) -> ObservationAttribution:
    """The attribution an accepted review asserts.

    An accepted observation may not carry `unknown` attribution — the contract refuses
    it — so a reviewer who accepts is asserting that the outcome contributed. That is the
    weaker of the two positive claims, which is the right default for a human resolving
    an ambiguity the classifier could not.
    """
    if original.attribution is ObservationAttribution.UNKNOWN:
        return ObservationAttribution.CONTRIBUTING
    return original.attribution
