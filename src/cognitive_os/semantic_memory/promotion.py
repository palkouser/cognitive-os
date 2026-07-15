"""Persisted host verifier gate for supported semantic claims."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.semantic_memory import (
    ClaimPromotionDecision,
    ClaimPromotionOutcome,
    ClaimRevision,
    ClaimRevisionReference,
    EvidenceLink,
    SemanticActor,
    semantic_hash,
)
from cognitive_os.domain.verifiers import (
    VerificationExecutionStatus,
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.events.semantic_memory_event_service import SemanticMemoryEventService
from cognitive_os.verification.registry import VerifierRegistry
from cognitive_os.verification.semantic import REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES

from .service import SemanticMemoryService


class SemanticPromotionGate:
    def __init__(
        self,
        semantic_memory: SemanticMemoryService,
        verification: VerificationService,
        registry: VerifierRegistry,
        events: SemanticMemoryEventService,
        *,
        clock: Callable[[], datetime] = utc_now,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._semantic_memory = semantic_memory
        self._verification = verification
        self._registry = registry
        self._events = events
        self._clock = clock
        self._id_factory = id_factory

    async def decide(
        self,
        revision: ClaimRevision,
        evidence: tuple[EvidenceLink, ...],
        *,
        task_run_id: UUID,
        actor: SemanticActor,
    ) -> ClaimPromotionDecision:
        if revision.previous_revision is None:
            raise ValueError("promotion requires an existing claim revision")
        snapshot = await self._semantic_memory.build_promotion_snapshot(revision, evidence)
        results = []
        failures = []
        decision_id = self._id_factory()
        for capability in REQUIRED_SEMANTIC_PROMOTION_CAPABILITIES:
            verifier_id = f"semantic.{capability}"
            execution = await self._verification.execute(
                VerificationRequest(
                    verification_id=self._id_factory(),
                    task_run_id=task_run_id,
                    criterion_id=self._id_factory(),
                    verifier_id=verifier_id,
                    verifier_version="1",
                    subject=VerificationSubject(
                        subject_type=VerificationSubjectType.SEMANTIC_SNAPSHOT,
                        inline_value=snapshot,
                    ),
                    requested_at=self._clock(),
                    correlation_id=decision_id,
                )
            )
            result = execution.result
            if (
                execution.status is not VerificationExecutionStatus.COMPLETED
                or result is None
                or result.status is not VerifierStatus.PASSED
            ):
                failures.append(verifier_id)
            if result is not None:
                results.append(result.model_dump(mode="json"))
        decision = ClaimPromotionDecision(
            decision_id=decision_id,
            claim=ClaimRevisionReference(
                claim_id=revision.claim_id,
                revision=revision.previous_revision,
            ),
            outcome=(
                ClaimPromotionOutcome.SUPPORTED if not failures else ClaimPromotionOutcome.REJECTED
            ),
            verifier_bundle_hash=semantic_hash(results),
            registry_snapshot_hash=self._registry.snapshot(),
            reason_codes=(tuple(failures) if failures else ("required_verifiers_passed",)),
            decided_at=self._clock(),
            decided_by=actor,
        )
        await self._events.record_promotion_decision(decision)
        return decision
