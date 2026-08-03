"""Deterministic fixtures for the Sprint 21C1 learned evidence benchmark.

Every builder here is credential-free and produces the same bytes and hashes on every
run. The component driven through the lifecycle is `AlwaysAbstainingRanker`, which
abstains unconditionally: the benchmark measures whether governance held, never whether
anything was learned.

These live under `benchmarks/` rather than in `tests/` because the benchmark runner is
shipped code and cannot import a test package. They are fixtures for a gate, not a
default runtime component, and nothing here is registered anywhere. See ADR 0086.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4, uuid5

from cognitive_os.domain.common import ArtifactRef
from cognitive_os.domain.learned import (
    BaselineKind,
    BaselineLadder,
    BaselineRung,
    CorpusRole,
    ForgettingAssessment,
    ForgettingVerdict,
    LearnedComponentState,
    LearnedPromotionAssessment,
    LearnedPromotionDecision,
    MandatoryPathInvariance,
    OutOfDistributionAssessment,
    ProvenanceClass,
)
from cognitive_os.domain.learned_evidence import (
    GovernedOutcomeReference,
    LearnedActivationApproval,
    LearnedApprovalAuthorityKind,
    LearnedArtifactLineage,
    LearnedArtifactRole,
    LearnedComponentRevisionRecord,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
    LearnedReplayResult,
    ObservationAttribution,
)
from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker

if TYPE_CHECKING:
    from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore

NAMESPACE = UUID("2f9c8d41-6b05-5a73-9e18-4c07b2fd6a39")
FIXTURE_TIME = datetime(2026, 7, 27, tzinfo=UTC)
OPERATOR = "benchmark-operator"
SURFACE = "skill.selection"

ARTIFACT_BYTES = b"learned benchmark fixture: inert bytes, referenced and never loaded\n"
ARTIFACT_HASH = sha256(ARTIFACT_BYTES).hexdigest()
ARTIFACT_ID = uuid5(NAMESPACE, "artifact")
COMPONENT = AlwaysAbstainingRanker()


class BenchmarkArtifactVerifier:
    """An Artifact Store stub with no way to load bytes, only to describe and verify."""

    def __init__(
        self, *, known: bool = True, verifies: bool = True, size: int | None = None
    ) -> None:
        self._known = known
        self._verifies = verifies
        self._size = size if size is not None else len(ARTIFACT_BYTES)

    async def artifact_metadata(self, artifact_id: UUID) -> ArtifactRef | None:
        if not self._known:
            return None
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type="application/octet-stream",
            content_hash=ARTIFACT_HASH,
            size_bytes=self._size,
            storage_key=f"sha256/{ARTIFACT_HASH[:2]}/{ARTIFACT_HASH}",
            created_at=FIXTURE_TIME,
        )

    async def verify_artifact(self, artifact_id: UUID) -> bool:
        return self._verifies and self._known


def descriptor() -> Any:
    return COMPONENT.descriptor


def lineage(**overrides: Any) -> LearnedArtifactLineage:
    fields: dict[str, Any] = {
        "lineage_id": uuid5(NAMESPACE, "lineage"),
        "artifact_id": ARTIFACT_ID,
        "role": LearnedArtifactRole.MODEL,
        "component_id": COMPONENT.component_id,
        "media_type": "application/octet-stream",
        "declared_format": "none",
        "declared_content_hash": ARTIFACT_HASH,
        "observed_content_hash": ARTIFACT_HASH,
        "size_bytes": len(ARTIFACT_BYTES),
        "verified_by": OPERATOR,
        "verified_at": FIXTURE_TIME,
    }
    fields.update(overrides)
    return LearnedArtifactLineage(**fields)


def promotion_assessment() -> LearnedPromotionAssessment:
    digest = "f" * 64
    return LearnedPromotionAssessment(
        assessment_id=uuid5(NAMESPACE, "assessment"),
        component_id=COMPONENT.component_id,
        descriptor=descriptor(),
        baseline_metric=Decimal("0.60"),
        candidate_metric=Decimal("0.70"),
        minimum_material_improvement=Decimal("0.05"),
        forgetting=ForgettingAssessment(
            assessment_id=uuid5(NAMESPACE, "forgetting"),
            session_id=uuid5(NAMESPACE, "session"),
            baseline_manifest_hash=digest,
            per_domain_before=(("mathematics", 100),),
            per_domain_after=(("mathematics", 100),),
            regressed_cases=(),
            retained_case_count=100,
            tolerance=0,
            verdict=ForgettingVerdict.RETAINED,
            created_at=FIXTURE_TIME,
        ),
        invariance=MandatoryPathInvariance(
            record_id=uuid5(NAMESPACE, "invariance"),
            component_id=COMPONENT.component_id,
            case_set_hash=digest,
            case_count=100,
            decision_hash_absent=digest,
            decision_hash_disabled=digest,
            decision_hash_abstaining=digest,
            created_at=FIXTURE_TIME,
        ),
        baseline_ladder=BaselineLadder(
            ladder_id=uuid5(NAMESPACE, "ladder"),
            surface=SURFACE,
            split="group-aware-by-case",
            rungs=(
                BaselineRung(
                    name="majority",
                    kind=BaselineKind.TRIVIAL,
                    score=Decimal("0.40"),
                    evaluated_count=100,
                    abstained=0,
                    confident_errors=60,
                ),
                BaselineRung(
                    name=descriptor().deterministic_baseline,
                    kind=BaselineKind.DETERMINISTIC,
                    score=Decimal("0.60"),
                    evaluated_count=100,
                    abstained=0,
                    confident_errors=40,
                ),
            ),
            created_at=FIXTURE_TIME,
        ),
        out_of_distribution=OutOfDistributionAssessment(
            assessment_id=uuid5(NAMESPACE, "ood"),
            component_id=COMPONENT.component_id,
            held_out_groups=("mathematics",),
            evaluated_count=100,
            abstained=100,
            confident_errors=0,
            confidence_threshold=Decimal("0.5"),
            created_at=FIXTURE_TIME,
        ),
        decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
        reason="benchmark fixture: shape only, no accuracy claim is made",
        created_at=FIXTURE_TIME,
    )


async def drive_to(service: Any, target: LearnedComponentState) -> Any:
    """Register and advance to `target` through the ordinary governed path."""
    correlation = uuid5(NAMESPACE, "correlation")
    record = await service.register_component(
        descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="benchmark: register the inert fixture",
        idempotency_key="bench-register",
        correlation_id=correlation,
    )
    order = (LearnedComponentState.SHADOW, LearnedComponentState.VERIFIED)
    for state in order:
        if target is LearnedComponentState.REGISTERED:
            break
        await service.advance_component(
            COMPONENT.component_id,
            state,
            descriptor=descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason=f"benchmark: advance to {state.value}",
            idempotency_key=f"bench-{state.value}",
            correlation_id=correlation,
        )
        if state is target:
            break
    if target is LearnedComponentState.DISABLED:
        await service.advance_component(
            COMPONENT.component_id,
            LearnedComponentState.DISABLED,
            descriptor=descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="benchmark: disable",
            idempotency_key="bench-disabled",
            correlation_id=correlation,
        )
    if target is LearnedComponentState.RETRACTED:
        await service.advance_component(
            COMPONENT.component_id,
            LearnedComponentState.RETRACTED,
            descriptor=descriptor(),
            actor=OPERATOR,
            authority="operator",
            reason="benchmark: retract",
            idempotency_key="bench-retracted",
            correlation_id=correlation,
        )
    return record


async def _prepare_activation(service: Any, *, defect: str) -> tuple[Any, Any]:
    """Everything an activation needs, with exactly one thing wrong when asked."""
    correlation = uuid5(NAMESPACE, "correlation")
    await drive_to(service, LearnedComponentState.VERIFIED)
    stored_lineage = lineage()
    if defect != "unverified_artifact":
        await service.register_artifact_lineage(
            stored_lineage,
            correlation_id=correlation,
            actor=OPERATOR,
            authority="operator",
            reason="benchmark: link the artifact",
        )
    assessment = promotion_assessment()
    if defect != "unrecorded_assessment":
        await service.record_evidence(
            LearnedEvidenceRecord(
                evidence_id=uuid5(NAMESPACE, "promotion-evidence"),
                evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
                component_id=COMPONENT.component_id,
                surface=SURFACE,
                schema_version="1",
                payload_hash=assessment.content_hash,
                recorded_by=OPERATOR,
                recorded_at=FIXTURE_TIME,
            ),
            correlation_id=correlation,
            actor=OPERATOR,
            authority="operator",
            reason="benchmark: record the assessment",
        )
    approval = LearnedActivationApproval(
        approval_id=uuid5(NAMESPACE, f"approval-{defect}"),
        component_id=COMPONENT.component_id,
        component_revision=2 if defect == "wrong_revision" else 3,
        surface=SURFACE,
        promotion_assessment_hash="9" * 64
        if defect == "wrong_assessment"
        else assessment.content_hash,
        artifact_lineage_id=stored_lineage.lineage_id,
        approved=defect != "refused_approval",
        approver="candidate-model" if defect == "model_approver" else OPERATOR,
        approver_kind=LearnedApprovalAuthorityKind.MODEL
        if defect == "model_approver"
        else LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
        reason="benchmark approval",
        approved_at=FIXTURE_TIME,
    )
    if defect != "unrecorded_approval":
        await service.record_approval(approval, correlation_id=correlation)
    return assessment, (approval, stored_lineage)


async def attempt_activation(service: Any, *, defect: str) -> Any:
    """Activate with one named defect injected. Raises when the defect is fatal."""
    assessment, (approval, stored_lineage) = await _prepare_activation(service, defect=defect)
    return await service.activate(
        descriptor=descriptor(),
        component_revision=3,
        promotion_assessment=assessment,
        approval=approval,
        lineage=stored_lineage,
        actor="unauthorised-job" if defect == "unauthorised_actor" else OPERATOR,
        authority="operator",
        reason="benchmark: activate the inert fixture",
        idempotency_key="bench-activate",
        correlation_id=uuid5(NAMESPACE, "correlation"),
    )


async def activate_disable_rollback(service: Any) -> tuple[Any, Any]:
    """The whole activation chain, returning the activation and rollback receipts."""
    correlation = uuid5(NAMESPACE, "correlation")
    activation = await attempt_activation(service, defect="none")
    await service.disable(
        COMPONENT.component_id,
        descriptor=descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="benchmark: withdraw",
        idempotency_key="bench-disable",
        correlation_id=correlation,
        # A healthy fixture parked on purpose, so its prior activation may be restored.
        rollback_permitted=True,
    )
    rollback = await service.roll_back(
        COMPONENT.component_id,
        descriptor=descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="benchmark: restore the prior activation",
        idempotency_key="bench-rollback",
        correlation_id=correlation,
    )
    return activation, rollback


async def attempt_lineage(service: Any, *, defect: str) -> Any:
    """Register lineage against a stub store carrying one named artifact defect."""
    from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
    from cognitive_os.infrastructure.learned.memory_repository import (
        InMemoryLearnedEvidenceRepository,
    )

    verifier = BenchmarkArtifactVerifier(
        known=defect != "missing_artifact",
        verifies=defect != "corrupted_artifact",
        size=1 if defect == "size_mismatch" else None,
    )
    scoped = LearnedEvidenceService(
        service._repository
        if hasattr(service, "_repository")
        else InMemoryLearnedEvidenceRepository(),
        artifacts=verifier,
        clock=lambda: FIXTURE_TIME,
    )
    declared = (
        lineage(declared_content_hash="9" * 64, observed_content_hash="9" * 64)
        if defect == "hash_mismatch"
        else lineage()
    )
    return await scoped.register_artifact_lineage(
        declared,
        correlation_id=uuid5(NAMESPACE, "correlation"),
        actor=OPERATOR,
        authority="operator",
        reason="benchmark: link the artifact",
    )


def outcome_reference(defect: str) -> GovernedOutcomeReference:
    """One governed outcome, with exactly one thing wrong when asked."""
    return GovernedOutcomeReference(
        surface=SURFACE,
        source_kind="fixture_replay" if defect == "fixture_as_real_run" else "governed_task_run",
        source_run_id=uuid5(NAMESPACE, f"run-{defect}"),
        source_payload_hash="a" * 64,
        provenance_class=ProvenanceClass.REAL_GOVERNED_RUN
        if defect in ("fixture_as_real_run", "real_run")
        else ProvenanceClass.SELF_PLAY,
        attribution=ObservationAttribution.UNKNOWN
        if defect == "unknown_attribution"
        else ObservationAttribution.DIRECT,
        usage_rights_verified=defect != "missing_rights",
        sensitivity="probably-fine" if defect == "unknown_sensitivity" else "internal",
        verifier_status="passed",
        verifier_evidence_hash=None if defect == "missing_verifier_evidence" else "b" * 64,
        occurred_at=FIXTURE_TIME,
    )


async def build_dataset_pair(variation: str) -> tuple[Any, Any, bool]:
    """Build a snapshot twice under a named variation. Returns both, plus whether refused."""
    from cognitive_os.application.services.learned_datasets import LearnedDatasetBuilder
    from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
    from cognitive_os.application.services.learned_intake import LearnedObservationIntake
    from cognitive_os.domain.learned_evidence import LearnedRepositoryError
    from cognitive_os.infrastructure.learned.memory_repository import (
        InMemoryLearnedEvidenceRepository,
    )

    repository = InMemoryLearnedEvidenceRepository()
    service = LearnedEvidenceService(repository, clock=lambda: FIXTURE_TIME)
    intake = LearnedObservationIntake(service)
    correlation = uuid5(NAMESPACE, "correlation")
    provenance = (
        ProvenanceClass.REAL_GOVERNED_RUN
        if variation == "real_run_training"
        else ProvenanceClass.SELF_PLAY
    )
    for index in range(6):
        await intake.offer(
            GovernedOutcomeReference(
                surface=SURFACE,
                source_kind="governed_task_run",
                source_run_id=uuid5(NAMESPACE, f"dataset-run-{index}"),
                source_payload_hash=f"{index:064x}",
                provenance_class=provenance,
                attribution=ObservationAttribution.DIRECT,
                usage_rights_verified=True,
                sensitivity="internal",
                verifier_status="passed",
                verifier_evidence_hash="b" * 64,
                occurred_at=FIXTURE_TIME,
            ),
            correlation_id=correlation,
        )

    # The stub satisfies the surface the builder actually uses. The cast is the honest
    # way to say "same shape, no database" rather than widening the builder's annotation.
    builder = LearnedDatasetBuilder(
        repository,
        cast("LearnedArtifactStore", _DatasetArtifactStore()),
        clock=lambda: FIXTURE_TIME,
    )
    role = CorpusRole.TRAINING if variation == "real_run_training" else CorpusRole.EVALUATION
    try:
        first = await builder.build(surface=SURFACE, corpus_role=role, feature_schema_hash="5" * 64)
    except LearnedRepositoryError:
        return None, None, True

    if variation == "added_member":
        await intake.offer(
            GovernedOutcomeReference(
                surface=SURFACE,
                source_kind="governed_task_run",
                source_run_id=uuid5(NAMESPACE, "dataset-run-extra"),
                source_payload_hash=f"{99:064x}",
                provenance_class=provenance,
                attribution=ObservationAttribution.DIRECT,
                usage_rights_verified=True,
                sensitivity="internal",
                verifier_status="passed",
                verifier_evidence_hash="b" * 64,
                occurred_at=FIXTURE_TIME,
            ),
            correlation_id=correlation,
        )
    if variation == "changed_split":
        second = await builder.build(
            surface=SURFACE,
            corpus_role=role,
            feature_schema_hash="5" * 64,
            split_policy="leave-one-domain-out",
        )
    else:
        second = await builder.build(
            surface=SURFACE, corpus_role=role, feature_schema_hash="5" * 64
        )
    return first, second, False


class _DatasetArtifactStore:
    """Stores manifest bytes in memory, keyed by content hash. No filesystem, no database.

    Deduplicates exactly as the real content-addressed store does, so a benchmark that
    builds the same dataset twice observes the same behaviour it would in production.
    """

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._references: dict[UUID, str] = {}

    async def store(self, data: bytes, *, media_type: str) -> ArtifactRef:
        digest = sha256(data).hexdigest()
        self._blobs[digest] = data
        artifact_id = uuid4()
        self._references[artifact_id] = digest
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type=media_type,
            content_hash=digest,
            size_bytes=len(data),
            storage_key=f"sha256/{digest[:2]}/{digest}",
            created_at=FIXTURE_TIME,
        )

    async def artifact_metadata(self, artifact_id: UUID) -> ArtifactRef | None:
        digest = self._references.get(artifact_id)
        if digest is None:
            return None
        data = self._blobs[digest]
        return ArtifactRef(
            artifact_id=artifact_id,
            media_type="application/json",
            content_hash=digest,
            size_bytes=len(data),
            storage_key=f"sha256/{digest[:2]}/{digest}",
            created_at=FIXTURE_TIME,
        )

    async def verify_artifact(self, artifact_id: UUID) -> bool:
        digest = self._references.get(artifact_id)
        return digest is not None and sha256(self._blobs[digest]).hexdigest() == digest

    async def build_lineage(self, **kwargs: Any) -> LearnedArtifactLineage:
        metadata = await self.artifact_metadata(kwargs["artifact_id"])
        if metadata is None:
            raise ValueError("unknown benchmark artifact")
        return LearnedArtifactLineage(
            lineage_id=kwargs["lineage_id"],
            artifact_id=kwargs["artifact_id"],
            role=kwargs["role"],
            component_id=kwargs.get("component_id"),
            dataset_id=kwargs.get("dataset_id"),
            media_type=metadata.media_type,
            declared_format=kwargs["declared_format"],
            declared_content_hash=metadata.content_hash,
            observed_content_hash=metadata.content_hash,
            size_bytes=metadata.size_bytes,
            verified_by=kwargs["verified_by"],
            verified_at=FIXTURE_TIME,
        )


async def replay_after(defect: str) -> LearnedReplayResult:
    """Replay a healthy history, or one with a named piece of damage."""
    from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
    from cognitive_os.infrastructure.learned.memory_repository import (
        InMemoryLearnedEvidenceRepository,
    )

    repository = InMemoryLearnedEvidenceRepository()
    service = LearnedEvidenceService(
        repository,
        artifacts=BenchmarkArtifactVerifier(),
        activation_actors=frozenset({OPERATOR}),
        clock=lambda: FIXTURE_TIME,
    )
    await drive_to(service, LearnedComponentState.VERIFIED)

    if defect == "missing_revision":
        repository._revisions[COMPONENT.component_id].pop(1)
    elif defect == "orphan_projection":
        repository._revisions[COMPONENT.component_id].clear()
    elif defect == "broken_predecessor":
        history = repository._revisions[COMPONENT.component_id]
        history[-1] = LearnedComponentRevisionRecord.model_construct(
            **{**history[-1].model_dump(), "previous_revision": 99}
        )
    elif defect == "hash_mismatch":
        history = repository._revisions[COMPONENT.component_id]
        history[-1] = LearnedComponentRevisionRecord.model_construct(
            **{**history[-1].model_dump(), "content_hash": "0" * 64}
        )
    return await repository.replay()


async def governance_check(name: str) -> bool:
    """Standing guarantees, each expressed as one boolean a reader can check by hand."""
    from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
    from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
    from cognitive_os.infrastructure.learned.memory_repository import (
        InMemoryLearnedEvidenceRepository,
    )
    from cognitive_os.learning.registry import transition_is_legal

    if name == "no_default_active_component":
        service = LearnedEvidenceService(InMemoryLearnedEvidenceRepository())
        for surface in (SURFACE, "acceptance.prediction", "context.reranking"):
            if await service.active_component_for(surface) is not None:
                return False
        return True
    if name == "activation_requires_named_actor":
        service = LearnedEvidenceService(InMemoryLearnedEvidenceRepository())
        return service._activation_actors == frozenset()
    if name == "disabled_cannot_reach_active_generically":
        return not transition_is_legal(LearnedComponentState.DISABLED, LearnedComponentState.ACTIVE)
    if name == "artifact_store_exposes_no_loader":
        return not any(
            hasattr(LearnedArtifactStore, item)
            for item in ("load", "loads", "open", "deserialise", "deserialize", "get_bytes")
        )
    if name == "retracted_is_terminal":
        return not any(
            transition_is_legal(LearnedComponentState.RETRACTED, state)
            for state in LearnedComponentState
        )
    return False
