"""Deterministic intake of governed outcomes into the learning plane.

Intake decides one thing: whether an outcome that already happened may be used as
*evaluation* evidence. It does not decide that anything should be learned from it, and
accepting an outcome never enrols it in training — selection into a dataset is a separate
immutable manifest, and a real governed run is excluded from training snapshots by the
contract and by a database CHECK regardless of what intake decided.

Three properties make this safe to run repeatedly against live surfaces:

* it reads. Source records are resolved by identity and hash, never modified and never
  copied — the observation stores a reference, so a sensitive body is not duplicated
  into the learning plane;
* it is deterministic. Every field of the observation, `recorded_at` included, is a
  function of the reference — no clock is read here — so the same outcome yields the same
  observation ID *and the same content hash*, and intake can be re-run after a crash
  without producing a second record or an idempotency conflict;
* it fails closed. The same source identity presenting *different* content is refused
  rather than accepted as an update, because an outcome that changed after the fact is
  either a different outcome or a corrupted one, and both need a human.

See ADR 0086.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from cognitive_os.domain.learned import ProvenanceClass
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedObservationRecord,
    ObservationAttribution,
    ObservationDecisionCode,
    ObservationStatus,
)

from .learned_evidence import LearnedEvidenceService

#: Fixed forever: changing it would give an already-recorded outcome a second identity.
OBSERVATION_NAMESPACE = UUID("4d1e7a86-2c95-5b30-9f47-8ea0d1c63b52")

#: Source kinds whose outcomes may legitimately be classed as a real governed run.
#:
#: Everything else is downgraded to self-play, whatever the caller declared. Sprint 21C1
#: must not let a fixture be misclassified as a real run: a real run is evaluation-only
#: and uncontaminated by training, and a self-play fixture that borrowed that label would
#: quietly become the yardstick every later comparison is measured against.
REAL_GOVERNED_SOURCE_KINDS: frozenset[str] = frozenset(
    {"governed_task_run", "governed_benchmark_case", "governed_change_evaluation"}
)

#: Sensitivity labels intake will accept. An unrecognised label is not a small problem:
#: it decides whether a read has to be audited, so an unknown one is quarantined.
KNOWN_SENSITIVITIES: frozenset[str] = frozenset({"public", "internal", "restricted"})

#: Source kinds produced by the Sprint 21C2 advisory providers.
#:
#: They belong to `VERIFIER_BACKED_SOURCE_KINDS` and must never be added to
#: `REAL_GOVERNED_SOURCE_KINDS`. A provider answering a question is not a governed run of
#: this system, and a provider output that borrowed that label would become evaluation-only
#: evidence that nothing actually evaluated. See ADR 0087.
PROVIDER_ADVISORY_SOURCE_KINDS: frozenset[str] = frozenset(
    {"openrouter_advisory", "claude_code_advisory", "codex_cli_advisory"}
)

#: Source kinds whose outcome is only meaningful with verifier evidence behind it.
VERIFIER_BACKED_SOURCE_KINDS: frozenset[str] = (
    frozenset({"governed_task_run", "governed_benchmark_case"}) | PROVIDER_ADVISORY_SOURCE_KINDS
)


def classify(reference: GovernedOutcomeReference) -> tuple[ObservationDecisionCode, str]:
    """Decide accept, quarantine or reject, and say why in a stable code.

    Order matters. Rights are checked first because a rejection for missing rights must
    not be reported as a quarantine that someone could later wave through; ambiguity is
    checked before completeness because an outcome nobody can attribute is unusable even
    if every other field is present.
    """
    if not reference.usage_rights_verified:
        return (
            ObservationDecisionCode.REJECTED_USAGE_RIGHTS_UNVERIFIED,
            "usage rights were not verified for this source",
        )
    if (
        reference.provenance_class is ProvenanceClass.REAL_GOVERNED_RUN
        and reference.source_kind not in REAL_GOVERNED_SOURCE_KINDS
    ):
        return (
            ObservationDecisionCode.REJECTED_PROVENANCE_NOT_CREDIBLE,
            f"source kind {reference.source_kind!r} cannot produce a real governed run",
        )
    if reference.attribution is ObservationAttribution.UNKNOWN:
        return (
            ObservationDecisionCode.QUARANTINED_ATTRIBUTION_UNKNOWN,
            "the outcome cannot be attributed to the decision under study",
        )
    if (
        reference.source_kind in VERIFIER_BACKED_SOURCE_KINDS
        and reference.verifier_evidence_hash is None
    ):
        return (
            ObservationDecisionCode.QUARANTINED_VERIFIER_EVIDENCE_MISSING,
            f"a {reference.source_kind} outcome needs verifier evidence to be evaluable",
        )
    if reference.sensitivity not in KNOWN_SENSITIVITIES:
        return (
            ObservationDecisionCode.QUARANTINED_SOURCE_INCOMPLETE,
            f"sensitivity {reference.sensitivity!r} is not a label this system recognises",
        )
    return ObservationDecisionCode.ACCEPTED, "governed outcome accepted as evaluation evidence"


def observation_id_for(reference: GovernedOutcomeReference) -> UUID:
    """Derived from source identity and content, so re-intake is genuinely idempotent."""
    return uuid5(OBSERVATION_NAMESPACE, f"{reference.identity}|{reference.source_payload_hash}")


def idempotency_key_for(reference: GovernedOutcomeReference) -> str:
    """Source identity *without* the payload hash.

    That asymmetry is the fail-closed rule: re-offering the same outcome reuses the key
    with identical content and is a free no-op, while the same source presenting changed
    content reuses the key with different content and is refused.
    """
    return f"observation:{reference.identity}"


class LearnedObservationIntake:
    """Turns governed outcome references into durable, classified observations."""

    def __init__(
        self,
        service: LearnedEvidenceService,
        *,
        actor: str = "learned-intake",
        authority: str = "system",
    ) -> None:
        self._service = service
        self._actor = actor
        self._authority = authority

    async def offer(
        self, reference: GovernedOutcomeReference, *, correlation_id: UUID
    ) -> LearnedObservationRecord:
        """Classify one outcome and persist the decision. Raises on a changed source.

        The record is appended whatever the decision is. A rejection that left no trace
        would make the quarantine queue look like the whole story, and an operator would
        have no way to see what intake refused.
        """
        code, reason = classify(reference)
        status = code.status
        accepted = status is ObservationStatus.ACCEPTED
        observation = LearnedObservationRecord(
            observation_id=observation_id_for(reference),
            surface=reference.surface,
            source_kind=reference.source_kind,
            source_task_id=reference.source_task_id,
            source_run_id=reference.source_run_id,
            source_event_id=reference.source_event_id,
            source_payload_hash=reference.source_payload_hash,
            provenance_class=reference.provenance_class,
            attribution=reference.attribution,
            status=status,
            verifier_status=reference.verifier_status,
            verifier_evidence_hash=reference.verifier_evidence_hash,
            usage_rights_verified=reference.usage_rights_verified,
            sensitivity=reference.sensitivity,
            decision_reason=f"{code.value}: {reason}",
            evaluation_eligible=accepted,
            idempotency_key=idempotency_key_for(reference),
            recorded_at=reference.occurred_at,
        )
        return await self._service.record_observation(
            observation,
            correlation_id=correlation_id,
            actor=self._actor,
            authority=self._authority,
        )

    async def offer_all(
        self, references: tuple[GovernedOutcomeReference, ...], *, correlation_id: UUID
    ) -> tuple[LearnedObservationRecord, ...]:
        """Intake in the caller's order, stopping at the first refusal.

        Not "best effort": a changed source means something upstream is wrong, and
        continuing past it would bury that signal under a pile of successful appends.
        """
        return tuple(
            [await self.offer(reference, correlation_id=correlation_id) for reference in references]
        )
