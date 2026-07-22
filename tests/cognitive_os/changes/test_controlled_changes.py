from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from cognitive_os.changes.fixtures import fixture_approved_proposal
from cognitive_os.changes.repository import InMemoryChangeRepository
from cognitive_os.changes.service import (
    EVALUATION_GROUPS,
    LEGAL_TRANSITIONS,
    ChangeAuthorityError,
    ChangeIntegrityError,
    ChangeSurfaceRegistry,
    ControlledChangeService,
    assess_candidate,
    build_evaluation_matrix,
    can_transition,
    compare_results,
    deterministic_replace,
)
from cognitive_os.config.change_config import (
    ChangeIsolationConfiguration,
    ChangePromotionConfiguration,
    ControlledChangeConfiguration,
    load_controlled_change_configuration,
)
from cognitive_os.domain.changes import (
    ActiveStateProtectionSnapshot,
    ChangeExperimentStatus,
    ChangeSurfaceTier,
    EvaluationCaseResult,
    ExperimentFailureCode,
    ImplementationChannel,
    PromotionDecision,
    PromotionMode,
    RollbackManifest,
    TypedPromotionStep,
)
from cognitive_os.domain.proposals import HarnessProposalType
from cognitive_os.events.change_event_service import ChangeEventService
from cognitive_os.proposals.fixtures import FIXTURE_TIME

BASELINE = "a" * 40
HASH = "b" * 64


class MemoryEventStore:
    def __init__(self) -> None:
        self.events = []

    async def get_stream_version(self, stream_id):
        del stream_id
        return len(self.events) or None

    async def append(self, events, *, expected_version):
        assert expected_version == len(self.events)
        self.events.extend(events)
        return SimpleNamespace(current_stream_version=len(self.events))


def snapshot() -> ActiveStateProtectionSnapshot:
    return ActiveStateProtectionSnapshot(
        repository_commit=BASELINE,
        repository_status_hash=HASH,
        repository_manifest_hash="c" * 64,
        active_database_fingerprint="d" * 64,
        active_artifact_namespace_hash="e" * 64,
        captured_at=FIXTURE_TIME,
    )


async def prepared(
    proposal_type: HarnessProposalType = HarnessProposalType.SOURCE_CODE_CHANGE,
):
    source, proposal = await fixture_approved_proposal(proposal_type)
    repository = InMemoryChangeRepository()
    service = ControlledChangeService(repository, source)
    experiment, revision, exact = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag="sprint-18-baseline",
        baseline_commit=BASELINE,
        actor="experiment-requester",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    manifest, verifier = await service.prepare_isolation(
        experiment, exact, snapshot(), created_at=FIXTURE_TIME
    )
    return service, repository, experiment, revision, exact, manifest, verifier


@pytest.mark.asyncio
async def test_service_emits_lifecycle_evidence_from_real_boundaries() -> None:
    source, proposal = await fixture_approved_proposal()
    repository = InMemoryChangeRepository()
    events = MemoryEventStore()
    service = ControlledChangeService(
        repository,
        source,
        event_service=ChangeEventService(events),
    )
    experiment, revision, exact = await service.request_experiment(
        proposal.proposal_id,
        proposal.revision,
        baseline_tag="sprint-18-baseline",
        baseline_commit=BASELINE,
        actor="experiment-requester",
        isolation_approver="isolation-approver",
        created_at=FIXTURE_TIME,
    )
    await service.prepare_isolation(experiment, exact, snapshot(), created_at=FIXTURE_TIME)
    for status in (
        ChangeExperimentStatus.APPROVED_FOR_ISOLATION,
        ChangeExperimentStatus.PREPARING,
        ChangeExperimentStatus.IMPLEMENTING,
    ):
        revision = await service.transition(
            experiment.experiment_id,
            revision.revision,
            status,
            actor="experiment-operator",
            reason=f"advance to {status.value}",
            created_at=FIXTURE_TIME,
        )
    assert [item.event_type for item in events.events] == [
        "change.experiment_created",
        "change.isolation_prepared",
        "change.implementation_started",
    ]


@pytest.mark.asyncio
async def test_exact_proposal_to_repository_bundle_is_deterministic() -> None:
    service, repository, experiment, revision, proposal, manifest, verifier = await prepared()
    assert verifier.passed and len(verifier.findings) == 11
    plan = service.build_plan(proposal, manifest)
    assert plan.ordered_operations[0].target in manifest.allowed_repository_paths

    candidate = await service.capture_candidate(
        experiment,
        manifest,
        channel=ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
        patch_hash="1" * 64,
        changed_files=manifest.allowed_repository_paths,
        lockfile_hash_before="2" * 64,
        lockfile_hash_after="2" * 64,
        build_manifest="3" * 64,
        created_at=FIXTURE_TIME,
    )
    matrix = build_evaluation_matrix(proposal)
    assert len(matrix.execution_order) == len(EVALUATION_GROUPS) + 2
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
        BASELINE.ljust(64, "0"),
        candidate.content_hash,
        results,
        created_at=FIXTURE_TIME,
    )
    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=comparison,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"pass_rate": Decimal("1")},
        created_at=FIXTURE_TIME,
    )
    await repository.record_comparison(comparison)
    await repository.record_assessment(assessment)
    assert assessment.decision is PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
    review = await service.approve_promotion(
        experiment,
        candidate,
        assessment,
        approver="promotion-approver",
        authority="promotion-review",
        target_authority="protected-repository",
        rationale="exact evidence reviewed",
        created_at=FIXTURE_TIME,
    )
    rollback = RollbackManifest(
        promotion_reference=assessment.content_hash,
        pre_promotion_state=experiment.baseline_commit.ljust(64, "0"),
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
        manual_steps=("Operator applies the reviewed revert through branch protection.",),
        created_at=FIXTURE_TIME,
    )
    bundle = await service.create_repository_bundle(
        experiment, candidate, assessment, review, rollback, created_at=FIXTURE_TIME
    )
    assert bundle.promotion_mode is PromotionMode.REPOSITORY_BUNDLE_ONLY
    assert "merge" in bundle.required_manual_steps[1]
    assert not hasattr(service, "merge")
    assert revision.status is ChangeExperimentStatus.REQUESTED


class Destination:
    async def append_verified_revision(self, *, target, expected_revision, artifact_hash, actor):
        assert target and artifact_hash and actor
        return expected_revision, str(int(expected_revision) + 1)


@pytest.mark.asyncio
async def test_tier_one_promotion_requires_separate_approval_and_rolls_back() -> None:
    service, _, experiment, _, proposal, manifest, _ = await prepared(
        HarnessProposalType.CONFIGURATION_CHANGE
    )
    candidate = await service.capture_candidate(
        experiment,
        manifest,
        channel=ImplementationChannel.DETERMINISTIC_TRANSFORMATION,
        patch_hash="1" * 64,
        changed_files=(),
        lockfile_hash_before="2" * 64,
        lockfile_hash_after="2" * 64,
        build_manifest="3" * 64,
        created_at=FIXTURE_TIME,
    )
    result = EvaluationCaseResult(
        gate_id="complete",
        passed=True,
        measured_value=Decimal("1"),
        threshold=Decimal("1"),
        evidence_artifact="4" * 64,
    )
    comparison = compare_results(
        experiment.experiment_id,
        candidate.candidate_id,
        "5" * 64,
        candidate.content_hash,
        (result,),
        created_at=FIXTURE_TIME,
    )
    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=comparison,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"quality": Decimal("1")},
        created_at=FIXTURE_TIME,
    )
    with pytest.raises(ChangeAuthorityError, match="separate actors"):
        await service.approve_promotion(
            experiment,
            candidate,
            assessment,
            approver="isolation-approver",
            authority="promotion-review",
            target_authority="configuration-registry",
            rationale="same actor is forbidden",
            created_at=FIXTURE_TIME,
        )
    review = await service.approve_promotion(
        experiment,
        candidate,
        assessment,
        approver="promotion-approver",
        authority="promotion-review",
        target_authority="configuration-registry",
        rationale="independent approval",
        created_at=FIXTURE_TIME,
    )
    receipt = await service.promote_governed_revision(
        experiment,
        candidate,
        assessment,
        review,
        Destination(),
        target="retrieval-profile",
        expected_revision="1",
        actor="destination-service",
        created_at=FIXTURE_TIME,
    )
    rollback = RollbackManifest(
        promotion_reference=receipt.content_hash,
        pre_promotion_state="6" * 64,
        post_promotion_state="7" * 64,
        rollback_operations=(
            TypedPromotionStep(
                adapter="configuration-registry",
                operation="append_revision",
                target="retrieval-profile",
                exact_precondition_hash="7" * 64,
                artifact_hash="6" * 64,
            ),
        ),
        artifact_restore_requirements=(),
        database_restore_requirements=(),
        verification_plan="8" * 64,
        maximum_recovery_objective=300,
        manual_steps=(),
        created_at=FIXTURE_TIME,
    )
    restored = await service.record_rollback(
        receipt,
        rollback,
        actor="destination-service",
        evidence_hash="9" * 64,
        started_at=FIXTURE_TIME,
        completed_at=FIXTURE_TIME,
    )
    assert restored.restored_revision == "1"


@pytest.mark.asyncio
async def test_hard_regression_and_tier_three_fail_closed() -> None:
    _, _, experiment, _, proposal, _, _ = await prepared(HarnessProposalType.TOOL_DEFINITION_CHANGE)
    candidate = type("Candidate", (), {"candidate_id": proposal.proposal_id})()
    failure = EvaluationCaseResult(
        gate_id="security",
        passed=False,
        measured_value=Decimal("0"),
        threshold=Decimal("1"),
        evidence_artifact="1" * 64,
        failure_code=ExperimentFailureCode.SECURITY_REGRESSION,
    )
    comparison = compare_results(
        experiment.experiment_id,
        proposal.proposal_id,
        "2" * 64,
        "3" * 64,
        (failure,),
        created_at=FIXTURE_TIME,
    )
    assert comparison.hard_failure_codes == (ExperimentFailureCode.SECURITY_REGRESSION,)
    assert (
        ChangeSurfaceRegistry().for_tier(ChangeSurfaceTier.TIER_3_CRITICAL).promotion_mode
        is PromotionMode.MANUAL_REVIEW_ONLY
    )
    assert experiment.change_surface_tier is ChangeSurfaceTier.TIER_3_CRITICAL
    assert candidate.candidate_id == proposal.proposal_id
    passing = compare_results(
        experiment.experiment_id,
        proposal.proposal_id,
        "4" * 64,
        "5" * 64,
        (
            EvaluationCaseResult(
                gate_id="complete",
                passed=True,
                measured_value=Decimal("1"),
                threshold=Decimal("1"),
                evidence_artifact="6" * 64,
            ),
        ),
        created_at=FIXTURE_TIME,
    )
    assessment = assess_candidate(
        experiment=experiment,
        candidate=candidate,
        comparison=passing,
        expected_benefit_hash=proposal.expected_benefit.content_hash,
        measured_metrics={"quality": Decimal("1")},
        created_at=FIXTURE_TIME,
    )
    assert assessment.decision is PromotionDecision.REQUIRES_MANUAL_REVIEW


@pytest.mark.asyncio
async def test_unapproved_and_scope_escape_inputs_are_rejected() -> None:
    source, proposal = await fixture_approved_proposal()
    repository = InMemoryChangeRepository()
    service = ControlledChangeService(repository, source)
    source.artifact_hashes = frozenset()
    with pytest.raises(ChangeIntegrityError, match="artifact"):
        await service.request_experiment(
            proposal.proposal_id,
            proposal.revision,
            baseline_tag="sprint-18-baseline",
            baseline_commit=BASELINE,
            actor="requester",
            isolation_approver="isolation-approver",
            created_at=FIXTURE_TIME,
        )
    with pytest.raises(ValidationError, match="bounded absolute"):
        ChangeIsolationConfiguration(workspace_root=Path("relative"))


def test_lifecycle_configuration_and_transformation_are_fail_closed(tmp_path: Path) -> None:
    assert can_transition(
        ChangeExperimentStatus.REQUESTED, ChangeExperimentStatus.APPROVED_FOR_ISOLATION
    )
    assert not can_transition(ChangeExperimentStatus.REQUESTED, ChangeExperimentStatus.PROMOTED)
    content = b"before value"
    transformed = deterministic_replace(content, b"before", b"after", sha256(content).hexdigest())
    assert transformed == b"after value"
    with pytest.raises(ChangeIntegrityError):
        deterministic_replace(content, b"missing", b"after", sha256(content).hexdigest())
    path = tmp_path / "changes.yaml"
    path.write_text(
        "controlled_changes:\n"
        "  isolation:\n"
        "    workspace_root: /tmp/cognitive-os-change-workspaces\n",
        encoding="utf-8",
    )
    assert load_controlled_change_configuration(path).promotion.require_separate_approval
    with pytest.raises(ValidationError):
        ControlledChangeConfiguration(
            isolation=ChangeIsolationConfiguration(
                workspace_root=Path("/tmp/cognitive-os-change-workspaces")
            ),
            promotion=ChangePromotionConfiguration(runtime_git_merge_enabled=True),
        )


def test_lifecycle_matrix_is_exact() -> None:
    for source in ChangeExperimentStatus:
        for target in ChangeExperimentStatus:
            assert can_transition(source, target) == (
                target in LEGAL_TRANSITIONS.get(source, set())
            )


@given(st.text(alphabet="0123456789", max_size=64))
def test_deterministic_transform_is_idempotent(suffix: str) -> None:
    content = f"before:{suffix}".encode()
    expected_hash = sha256(content).hexdigest()
    transformed = deterministic_replace(content, b"before", b"after", expected_hash)
    assert deterministic_replace(transformed, b"before", b"after", expected_hash) == transformed
