"""Credential-free lifecycle smoke for the durable learned evidence store.

Drives the inert reference component through its whole governed lifecycle against a real
database — register, lineage, evidence, verify, approve, activate, disable, roll back —
and then replays history and checks health. It is the one learned code path that writes,
and it starts by truncating every learned evidence table, so it is fenced four times: the
database name must end in `_test`, `COGOS_TRUNCATABLE_DATABASE` must nominate that exact
database, the learned store must hold nothing this smoke did not create, and the component
it drives is the abstaining reference one, which cannot change a decision even if something
did activate it.

The two middle fences were added late, after this smoke erased Sprint 21D3's committed
campaign. A `_test` suffix is shared by every sprint's evidence database, so the name check
alone consented to nothing. See `_require_nomination` and `_require_erasable`.

The component it activates is never a shipped default. Nothing here demonstrates that the
system learns anything; it demonstrates that the record of an activation survives a
process boundary and still verifies. See ADR 0086.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4, uuid5

from sqlalchemy import text

from cognitive_os.application.services.learned_evidence import LearnedEvidenceService
from cognitive_os.domain.learned import (
    LearnedArtifactFormat,
    LearnedComponentState,
    LearnedPromotionAssessment,
)
from cognitive_os.domain.learned_evidence import (
    LearnedActivationApproval,
    LearnedApprovalAuthorityKind,
    LearnedArtifactRole,
    LearnedEvidenceKind,
    LearnedEvidenceRecord,
)
from cognitive_os.domain.promotion_payload import (
    CONDITION_20_GATE,
    D3_PROMOTION_GATES,
    D3_PROMOTION_MEDIA_TYPE,
    CanaryToSteadyCondition,
    D3ArtifactBinding,
    D3PromotionAssessment,
    D3PromotionPayload,
    D3RuntimeConfiguration,
    PromotionDependency,
    PromotionGateOutcome,
    PromotionGateRecord,
    canonical_payload_bytes,
)
from cognitive_os.events.learned_event_service import LearnedEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.infrastructure.artifacts.filesystem import ContentAddressedFilesystem
from cognitive_os.infrastructure.artifacts.service import ArtifactService
from cognitive_os.infrastructure.learned.artifacts import LearnedArtifactStore
from cognitive_os.infrastructure.learned.postgres.health import PostgresLearnedHealthService
from cognitive_os.infrastructure.learned.postgres.repository import (
    PostgresLearnedEvidenceRepository,
)
from cognitive_os.infrastructure.learned.postgres.tables import LEARNED_EVIDENCE_TABLES
from cognitive_os.infrastructure.learned.reference import AlwaysAbstainingRanker
from cognitive_os.infrastructure.postgres.artifact_repository import PostgresArtifactRepository
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.truncation import (
    TruncationNotNominated,
    TruncationRefused,
    require_nominated_for_truncation,
)
from cognitive_os.learning.correction_protocol import DecisionCensusV4
from cognitive_os.learning.promotion import D3PromotionBindings, condition_20_gate

SMOKE_NAMESPACE = UUID("7e2b5c98-40a1-5d37-8f6b-1c94ae30d752")
SMOKE_OPERATOR = "learned-smoke-operator"
SMOKE_ARTIFACT = b"learned smoke fixture: inert bytes, referenced and never loaded\n"
SMOKE_TIME = datetime(2026, 7, 27, tzinfo=UTC)


class SmokeRefused(RuntimeError):
    """The smoke declined to run, which is a success for the guard that refused it."""


def _require_isolated(url: str) -> None:
    if "_test" not in url:
        raise SmokeRefused(
            "the learned smoke writes, so it only runs against an isolated *_test database"
        )


def _require_nomination(database: str) -> None:
    """The database must be nominated for erasure by name, in the environment. D4-W0-F1.

    This is `tests/integration/postgres/conftest.py`'s rule, not a new one. That fixture
    truncates the whole schema and learned the same lesson at W6-F2: "ends with `_test`" is a
    naming convention, not consent, because every sprint's *evidence* database ends in `_test`
    too. It answered by requiring `COGOS_TRUNCATABLE_DATABASE` to name the connected database.

    This smoke truncates nine tables and was never given the same treatment, so on 2026-08-05 it
    erased Sprint 21D3's 280 committed self-play observations and both of its materialised
    revision-3 datasets -- two minutes before the W7 backup meant to preserve them, which is why
    that restore proof verified matching counts of nothing. Nothing was recoverable, because
    every backup was taken after the erasure.

    One rule for both truncating paths, deliberately. A second mechanism answering the same
    question differently is how an operator ends up knowing one fence and meeting the other.

    W7-F1 found that "both" was never the whole list -- five test modules truncated the same
    nine tables behind the older `_test` fence -- so the rule moved to
    `infrastructure.postgres.engine`, where every path that connects can reach it, and this
    function is now one of its callers rather than one of its implementations.
    """
    try:
        require_nominated_for_truncation(database)
    except TruncationNotNominated as reason:
        raise SmokeRefused(
            "the learned smoke truncates every learned evidence table, so the database must be "
            "nominated for erasure: set COGOS_TRUNCATABLE_DATABASE to the database you mean. "
            "It must never name a store that holds evidence."
        ) from reason
    except TruncationRefused as reason:
        raise SmokeRefused(str(reason)) from reason


async def _require_erasable(connection: Any) -> None:
    """Second fence: refuse a nominated store that still holds evidence. D4-W0-F1.

    Nomination is consent, and consent can be given by mistake -- an operator following a
    runbook against the wrong sprint's environment nominates exactly the database that must not
    be erased. So the store is also asked what it holds. Observations and datasets are the
    record of executed runs and no later backup can bring them back; this smoke writes neither,
    so one row of either means the database belongs to somebody else. A component that is not
    the inert reference one means the same.

    Kept deliberately, against the usual rule about second mechanisms, because the failure it
    prevents is irreversible data loss rather than an incorrect result. Repeated smoke runs stay
    idempotent: the reference component's own rows are the one thing allowed to be here.
    """
    # Spelled out rather than looped over a table name. The names are hard-coded either way, so
    # nothing was injectable, but SQL assembled by interpolation is a shape worth not having in
    # a path that decides whether a store gets erased -- and two literals are shorter than the
    # suppression comment the alternative needs.
    findings: list[str] = []
    observations = await connection.scalar(
        text("SELECT count(*) FROM cognitive_os.learned_observations")
    )
    if observations:
        findings.append(f"{observations} row(s) in learned_observations")
    datasets = await connection.scalar(text("SELECT count(*) FROM cognitive_os.learned_datasets"))
    if datasets:
        findings.append(f"{datasets} row(s) in learned_datasets")
    foreign = await connection.scalar(
        text("SELECT count(*) FROM cognitive_os.learned_components WHERE component_id <> :own"),
        {"own": AlwaysAbstainingRanker.component_id},
    )
    if foreign:
        findings.append(f"{foreign} learned component(s) other than the reference one")
    if findings:
        raise SmokeRefused(
            "refusing to truncate a learned store that holds evidence this smoke did not "
            f"create: {'; '.join(findings)}. It was nominated by COGOS_TRUNCATABLE_DATABASE, so "
            "check that the nomination names the scratch database you meant rather than a "
            "sprint's evidence store."
        )


async def run_learned_smoke() -> dict[str, Any]:
    """Run the full lifecycle and return a JSON-serialisable report."""
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL") or os.environ.get(
        "COGOS_DATABASE_URL"
    )
    root = os.environ.get("COGOS_ARTIFACT_ROOT")
    if not database_url:
        raise SmokeRefused("COGOS_DATABASE_ADMIN_URL or COGOS_DATABASE_URL is required")
    if not root:
        raise SmokeRefused("COGOS_ARTIFACT_ROOT is required")
    _require_isolated(database_url)

    engine = create_postgres_engine(database_url, pool_size=2, max_overflow=1)
    try:
        async with engine.connect() as connection:
            name = str(await connection.scalar(text("SELECT current_database()")))
        if not name.endswith("_test"):
            raise SmokeRefused(f"refusing to write learned smoke evidence to {name}")
        _require_nomination(name)
        async with engine.begin() as connection:
            await _require_erasable(connection)
            tables = ", ".join(f"cognitive_os.{table.name}" for table in LEARNED_EVIDENCE_TABLES)
            await connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

        repository = PostgresLearnedEvidenceRepository(engine)
        artifacts = LearnedArtifactStore(
            ArtifactService(
                ContentAddressedFilesystem(Path(root)), PostgresArtifactRepository(engine)
            )
        )
        return await _drive(engine, repository, artifacts, database=name)
    finally:
        await engine.dispose()


async def _drive(
    engine: Any,
    repository: PostgresLearnedEvidenceRepository,
    artifacts: LearnedArtifactStore,
    *,
    database: str,
) -> dict[str, Any]:
    component = AlwaysAbstainingRanker()
    descriptor = component.descriptor
    correlation = uuid5(SMOKE_NAMESPACE, "correlation")
    service = LearnedEvidenceService(
        repository,
        artifacts=artifacts,
        events=LearnedEventService(MemoryEventStore()),
        activation_actors=frozenset({SMOKE_OPERATOR}),
        clock=lambda: datetime.now(UTC),
    )

    await service.register_component(
        descriptor,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: register the inert reference component",
        idempotency_key="smoke-register",
        correlation_id=correlation,
    )

    reference = await artifacts.store(SMOKE_ARTIFACT, media_type="application/octet-stream")
    lineage = await artifacts.build_lineage(
        lineage_id=uuid5(SMOKE_NAMESPACE, "lineage"),
        artifact_id=reference.artifact_id,
        role=LearnedArtifactRole.MODEL,
        declared_format=LearnedArtifactFormat.NONE,
        component_id=descriptor.component_id,
        verified_by=SMOKE_OPERATOR,
    )
    await service.register_artifact_lineage(
        lineage,
        correlation_id=correlation,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: link the verified artifact",
    )

    await service.advance_component(
        descriptor.component_id,
        LearnedComponentState.SHADOW,
        descriptor=descriptor,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: advance to shadow",
        idempotency_key="smoke-shadow",
        correlation_id=correlation,
    )

    # S21D3-057. `VERIFIED` is no longer an ordinary transition, so the smoke stores a real
    # D3 promotion payload and verifies against it. That is a better smoke than the one it
    # replaces: the payload bytes go through the same Artifact Store the model bytes did, and
    # verification re-reads both rather than trusting this function's word for either.
    payload = _promotion_payload(descriptor, reference)
    payload_reference = await artifacts.store(
        canonical_payload_bytes(payload), media_type=D3_PROMOTION_MEDIA_TYPE
    )
    d3_assessment = D3PromotionAssessment(
        assessment_id=uuid5(SMOKE_NAMESPACE, "d3-assessment"),
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        payload_artifact_id=payload_reference.artifact_id,
        payload_content_hash=payload_reference.content_hash,
        decision="eligible",
        reason="learned smoke: shape-only payload, every gate recorded as passed",
        recorded_at=SMOKE_TIME,
    )
    await service.record_evidence(
        LearnedEvidenceRecord(
            evidence_id=uuid5(SMOKE_NAMESPACE, "d3-promotion-evidence"),
            evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
            component_id=descriptor.component_id,
            surface=descriptor.surface,
            schema_version="2",
            payload_hash=d3_assessment.content_hash,
            payload_artifact_id=payload_reference.artifact_id,
            recorded_by=SMOKE_OPERATOR,
            recorded_at=SMOKE_TIME,
        ),
        correlation_id=correlation,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: record the D3 promotion payload",
    )
    await service.verify_component(
        descriptor.component_id,
        descriptor=descriptor,
        assessment=d3_assessment,
        payload=payload,
        bindings=_promotion_bindings(descriptor, reference),
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: verify against the stored payload",
        idempotency_key="smoke-verified",
        correlation_id=correlation,
    )

    assessment = _assessment(descriptor)
    await service.record_evidence(
        LearnedEvidenceRecord(
            evidence_id=uuid5(SMOKE_NAMESPACE, "promotion-evidence"),
            evidence_kind=LearnedEvidenceKind.PROMOTION_ASSESSMENT,
            component_id=descriptor.component_id,
            surface=descriptor.surface,
            schema_version="1",
            payload_hash=assessment.content_hash,
            recorded_by=SMOKE_OPERATOR,
            recorded_at=SMOKE_TIME,
        ),
        correlation_id=correlation,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: record the promotion assessment",
    )

    approval = LearnedActivationApproval(
        approval_id=uuid5(SMOKE_NAMESPACE, "approval"),
        component_id=descriptor.component_id,
        component_revision=3,
        surface=descriptor.surface,
        promotion_assessment_hash=assessment.content_hash,
        artifact_lineage_id=lineage.lineage_id,
        approved=True,
        approver=SMOKE_OPERATOR,
        approver_kind=LearnedApprovalAuthorityKind.HUMAN_OPERATOR,
        reason="learned smoke: approval issued inside an isolated database",
        approved_at=SMOKE_TIME,
    )
    await service.record_approval(approval, correlation_id=correlation)

    activation = await service.activate(
        descriptor=descriptor,
        component_revision=3,
        promotion_assessment=assessment,
        approval=approval,
        lineage=lineage,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: activate the inert fixture",
        idempotency_key="smoke-activate",
        correlation_id=correlation,
    )
    await service.disable(
        descriptor.component_id,
        descriptor=descriptor,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: withdraw the fixture",
        idempotency_key="smoke-disable",
        correlation_id=correlation,
        # A healthy fixture parked on purpose, so its prior activation may be restored.
        rollback_permitted=True,
    )
    rollback = await service.roll_back(
        descriptor.component_id,
        descriptor=descriptor,
        actor=SMOKE_OPERATOR,
        authority="operator",
        reason="learned smoke: restore the prior activation",
        idempotency_key="smoke-rollback",
        correlation_id=correlation,
    )

    # A second service over the same database. If the first held authoritative state,
    # this is where the system would quietly forget what was active.
    restarted = LearnedEvidenceService(repository, artifacts=artifacts)
    row = await restarted.get_component(descriptor.component_id)
    active = await restarted.active_component_for(descriptor.surface)
    replay = await repository.replay()
    health = await PostgresLearnedHealthService(engine).check()

    return {
        "database": database,
        "component_id": descriptor.component_id,
        "final_state": row.current_state.value if row else None,
        "final_revision": row.current_revision if row else None,
        "active_after_restart": active.component_id if active else None,
        "activation_receipt": str(activation.receipt_id),
        "rollback_receipt": str(rollback.receipt_id),
        "rollback_target": str(rollback.rollback_target_receipt_id),
        "replay_matches": replay.projection_matches,
        "replay_revisions": replay.replayed_revisions,
        "health_failures": list(health.integrity_failures),
        "correlation_failures": [item.subject for item in service.correlation_failures],
        "healthy": bool(
            row
            and row.current_state is LearnedComponentState.ACTIVE
            and replay.projection_matches
            and replay.hash_chain_verified
            and health.healthy
            and rollback.rollback_target_receipt_id == activation.receipt_id
        ),
    }


def _assessment(descriptor: Any) -> LearnedPromotionAssessment:
    """A shape-only assessment. It makes no accuracy claim and proves no uplift."""
    from decimal import Decimal

    from cognitive_os.domain.learned import (
        BaselineKind,
        BaselineLadder,
        BaselineRung,
        ForgettingAssessment,
        ForgettingVerdict,
        LearnedPromotionDecision,
        MandatoryPathInvariance,
        OutOfDistributionAssessment,
    )

    digest = "f" * 64
    return LearnedPromotionAssessment(
        assessment_id=uuid5(SMOKE_NAMESPACE, "assessment"),
        component_id=descriptor.component_id,
        descriptor=descriptor,
        baseline_metric=Decimal("0.60"),
        candidate_metric=Decimal("0.70"),
        minimum_material_improvement=Decimal("0.05"),
        forgetting=ForgettingAssessment(
            assessment_id=uuid5(SMOKE_NAMESPACE, "forgetting"),
            session_id=uuid4(),
            baseline_manifest_hash=digest,
            per_domain_before=(("mathematics", 100),),
            per_domain_after=(("mathematics", 100),),
            regressed_cases=(),
            retained_case_count=100,
            tolerance=0,
            verdict=ForgettingVerdict.RETAINED,
            created_at=SMOKE_TIME,
        ),
        invariance=MandatoryPathInvariance(
            record_id=uuid5(SMOKE_NAMESPACE, "invariance"),
            component_id=descriptor.component_id,
            case_set_hash=digest,
            case_count=100,
            decision_hash_absent=digest,
            decision_hash_disabled=digest,
            decision_hash_abstaining=digest,
            created_at=SMOKE_TIME,
        ),
        baseline_ladder=BaselineLadder(
            ladder_id=uuid5(SMOKE_NAMESPACE, "ladder"),
            surface=descriptor.surface,
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
                    name=descriptor.deterministic_baseline,
                    kind=BaselineKind.DETERMINISTIC,
                    score=Decimal("0.60"),
                    evaluated_count=100,
                    abstained=0,
                    confident_errors=40,
                ),
            ),
            created_at=SMOKE_TIME,
        ),
        out_of_distribution=OutOfDistributionAssessment(
            assessment_id=uuid5(SMOKE_NAMESPACE, "ood"),
            component_id=descriptor.component_id,
            held_out_groups=("mathematics",),
            evaluated_count=100,
            abstained=100,
            confident_errors=0,
            confidence_threshold=Decimal("0.5"),
            created_at=SMOKE_TIME,
        ),
        decision=LearnedPromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
        reason="learned smoke: shape only, no accuracy claim is made",
        created_at=SMOKE_TIME,
    )


def _runtime_configuration(name: str, descriptor: Any) -> D3RuntimeConfiguration:
    return D3RuntimeConfiguration(
        name=name,
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        routed_group_ids=("smoke-group-a",) if name == "exact_canary" else ("smoke-group-b",),
        routing_manifest_hash="c" * 64,
        sequence_mode="stop_on_first_accepted",
        persistence_enabled=True,
        activation_enabled=True,
        maximum_tasks=20 if name == "exact_canary" else 200,
        kill_switch_enabled=True,
        maximum_inference_ms=250,
        fallback_on_refusal="frozen deterministic baseline order",
    )


def _transition_condition() -> CanaryToSteadyCondition:
    return CanaryToSteadyCondition(minimum_canary_tasks=20, rollback_target_revision=1)


#: Shape-only, exactly like `_assessment`: every gate is recorded as passed so the smoke can
#: reach `VERIFIED`, and nothing here is a claim that anything was measured.
_SMOKE_DEPENDENCIES: dict[str, str] = {"smoke_fixture": "1" * 64}


def _smoke_gate(name: str) -> PromotionGateRecord:
    """One shape-only gate row, and condition 20's denominators when it is that row.

    S21D4-048 refuses a measured metamorphic/OOD row that does not name how many decisions it
    counted and how many of them were distinct. The smoke has no decisions, so its census says
    so: twenty fixture decisions, none replicated, under a fixture certificate. The detail
    string carries the same disclaimer every other row here carries.
    """
    evidence_hash = sha256(f"smoke:{name}".encode()).hexdigest()
    detail = f"learned smoke: {name} is shape-only and makes no accuracy claim"
    if name != CONDITION_20_GATE:
        return PromotionGateRecord(
            name=name,
            outcome=PromotionGateOutcome.PASSED,
            evidence_hash=evidence_hash,
            detail=detail,
        )
    return condition_20_gate(
        outcome=PromotionGateOutcome.PASSED,
        evidence_hash=evidence_hash,
        detail=detail,
        census=DecisionCensusV4.from_feature_hashes(
            [sha256(f"smoke:decision:{index}".encode()).hexdigest() for index in range(20)]
        ),
        calibration_certificate_hash=sha256(b"smoke:calibration-certificate").hexdigest(),
    )


def _promotion_payload(descriptor: Any, reference: Any) -> D3PromotionPayload:
    return D3PromotionPayload(
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        code_revision="learned-smoke",
        legacy_assessment_hash=_assessment(descriptor).content_hash,
        legacy_decision="eligible_for_operator_approval",
        gates=tuple(_smoke_gate(name) for name in D3_PROMOTION_GATES),
        dependencies=tuple(
            PromotionDependency(name=name, content_hash=value)
            for name, value in sorted(_SMOKE_DEPENDENCIES.items())
        ),
        artifact=D3ArtifactBinding(
            artifact_id=reference.artifact_id,
            media_type=reference.media_type,
            schema_name="learned-smoke-inert-bytes",
            schema_version=1,
            content_hash=reference.content_hash,
            size_bytes=reference.size_bytes,
        ),
        canary_configuration_hash=_runtime_configuration("exact_canary", descriptor).content_hash,
        steady_state_configuration_hash=_runtime_configuration(
            "bounded_steady_state", descriptor
        ).content_hash,
        canary_to_steady_condition_hash=_transition_condition().content_hash,
        recorded_at=SMOKE_TIME,
    )


def _promotion_bindings(descriptor: Any, reference: Any) -> D3PromotionBindings:
    return D3PromotionBindings(
        component_id=descriptor.component_id,
        component_revision=2,
        surface=descriptor.surface,
        artifact_content_hash=reference.content_hash,
        artifact_size_bytes=reference.size_bytes,
        canary_configuration=_runtime_configuration("exact_canary", descriptor),
        steady_state_configuration=_runtime_configuration("bounded_steady_state", descriptor),
        canary_to_steady_condition=_transition_condition(),
        dependency_hashes=dict(_SMOKE_DEPENDENCIES),
    )
