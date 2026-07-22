"""Credential-free deterministic end-to-end controlled-change demonstration."""

from decimal import Decimal
from hashlib import sha256

from cognitive_os.domain.changes import (
    ActiveStateProtectionSnapshot,
    EvaluationCaseResult,
    ImplementationChannel,
    RollbackManifest,
    TypedPromotionStep,
)
from cognitive_os.proposals.fixtures import FIXTURE_TIME

from .fixtures import fixture_approved_proposal
from .repository import InMemoryChangeRepository
from .service import (
    ControlledChangeService,
    assess_candidate,
    build_evaluation_matrix,
    compare_results,
)


async def run_demo() -> dict[str, object]:
    source, proposal = await fixture_approved_proposal()
    repository = InMemoryChangeRepository()
    service = ControlledChangeService(repository, source)
    baseline = "a" * 40
    experiment, revision, proposal = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag="sprint-18-baseline",
        baseline_commit=baseline,
        actor="operator",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    snapshot = ActiveStateProtectionSnapshot(
        repository_commit=baseline,
        repository_status_hash="b" * 64,
        repository_manifest_hash="c" * 64,
        active_database_fingerprint="d" * 64,
        active_artifact_namespace_hash="e" * 64,
        captured_at=FIXTURE_TIME,
    )
    isolation, verifier = await service.prepare_isolation(
        experiment, proposal, snapshot, created_at=FIXTURE_TIME
    )
    plan = service.build_plan(proposal, isolation)
    candidate = await service.capture_candidate(
        experiment,
        isolation,
        channel=ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
        patch_hash="1" * 64,
        changed_files=isolation.allowed_repository_paths,
        lockfile_hash_before="2" * 64,
        lockfile_hash_after="2" * 64,
        build_manifest="3" * 64,
        created_at=FIXTURE_TIME,
    )
    matrix = build_evaluation_matrix(proposal)
    results = tuple(
        EvaluationCaseResult(
            gate_id=gate_id,
            passed=True,
            measured_value=Decimal("1"),
            threshold=Decimal("1"),
            evidence_artifact=sha256(gate_id.encode()).hexdigest(),
        )
        for gate_id in matrix.execution_order
    )
    comparison = compare_results(
        experiment.experiment_id,
        candidate.candidate_id,
        sha256(b"baseline-evaluation").hexdigest(),
        candidate.content_hash,
        results,
        created_at=FIXTURE_TIME,
    )
    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=comparison,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"case_pass_rate": Decimal("1")},
        created_at=FIXTURE_TIME,
    )
    review = await service.approve_promotion(
        experiment,
        candidate,
        assessment,
        approver="promotion-approver",
        authority="promotion-review",
        target_authority="protected-repository",
        rationale="exact immutable evidence passed",
        created_at=FIXTURE_TIME,
    )
    rollback = RollbackManifest(
        promotion_reference=assessment.content_hash,
        pre_promotion_state=sha256(b"baseline-state").hexdigest(),
        post_promotion_state=candidate.content_hash,
        rollback_operations=(
            TypedPromotionStep(
                adapter="operator.repository_bundle",
                operation="prepare_patch_bundle",
                target="repository",
                exact_precondition_hash=candidate.content_hash,
                artifact_hash=candidate.patch_artifact,
            ),
        ),
        artifact_restore_requirements=(candidate.patch_artifact,),
        database_restore_requirements=(),
        verification_plan=matrix.content_hash,
        maximum_recovery_objective=300,
        manual_steps=("Operator uses the protected repository revert workflow.",),
        created_at=FIXTURE_TIME,
    )
    bundle = await service.create_repository_bundle(
        experiment, candidate, assessment, review, rollback, created_at=FIXTURE_TIME
    )
    return {
        "experiment": experiment,
        "revision": revision,
        "isolation": isolation,
        "isolation_verifier": verifier,
        "implementation_plan": plan,
        "candidate": candidate,
        "evaluation_matrix": matrix,
        "comparison": comparison,
        "assessment": assessment,
        "promotion_review": review,
        "promotion_bundle": bundle,
    }
