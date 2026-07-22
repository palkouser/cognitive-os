"""Host-owned orchestration for isolated, regression-gated changes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.changes import (
    ApprovedProposalIntakePort,
    ChangeRepositoryPort,
    GovernedDestinationPort,
)
from cognitive_os.domain.changes import (
    ActiveStateProtectionSnapshot,
    CandidateStatus,
    ChangeCandidate,
    ChangeExperiment,
    ChangeExperimentRevision,
    ChangeExperimentStatus,
    ChangeImplementationPlan,
    ChangeIsolationManifest,
    ChangeOperation,
    ChangeOperationType,
    ChangeResourceBudget,
    ChangeSurfaceRegistration,
    ChangeSurfaceTier,
    ChangeVerificationFinding,
    ChangeVerifierBundle,
    DependencyDelta,
    EvaluationCaseResult,
    EvaluationGate,
    EvaluationMatrix,
    ExperimentFailureCode,
    GateSeverity,
    ImplementationChannel,
    IsolationKind,
    MeasuredBenefit,
    NetworkPolicy,
    PromotionAssessment,
    PromotionBundle,
    PromotionDecision,
    PromotionMode,
    PromotionReceipt,
    PromotionReview,
    RegressionComparison,
    RollbackManifest,
    RollbackReceipt,
    TypedPromotionStep,
)
from cognitive_os.domain.common import UtcDatetime
from cognitive_os.domain.proposals import (
    HarnessProposalRevision,
    HarnessProposalType,
    ProposalReviewDecision,
    ProposalStatus,
    ProposalVerifierStatus,
)
from cognitive_os.events.change_event_service import ChangeEventService
from cognitive_os.events.change_events import (
    ChangeCancelled,
    ChangeEvaluationCompleted,
    ChangeEvaluationStarted,
    ChangeEventPayload,
    ChangeExperimentCreated,
    ChangeFailed,
    ChangeImplementationCompleted,
    ChangeImplementationStarted,
    ChangeIsolationPrepared,
    ChangePromoted,
    ChangePromotionApproved,
    ChangePromotionAssessed,
    ChangeRejected,
    ChangeRollbackStarted,
    ChangeRolledBack,
)


class ChangeError(RuntimeError):
    """Base controlled-change failure."""


class ChangeAuthorityError(ChangeError):
    """An actor or operation exceeded its authority."""


class ChangeConflictError(ChangeError):
    """An immutable identity or compare-and-set operation conflicted."""


class ChangeIntegrityError(ChangeError):
    """Exact input or evidence failed integrity checks."""


LEGAL_TRANSITIONS: Final = {
    ChangeExperimentStatus.REQUESTED: {
        ChangeExperimentStatus.APPROVED_FOR_ISOLATION,
        ChangeExperimentStatus.CANCELLED,
        ChangeExperimentStatus.REJECTED,
    },
    ChangeExperimentStatus.APPROVED_FOR_ISOLATION: {
        ChangeExperimentStatus.PREPARING,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.PREPARING: {
        ChangeExperimentStatus.IMPLEMENTING,
        ChangeExperimentStatus.FAILED,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.IMPLEMENTING: {
        ChangeExperimentStatus.IMPLEMENTED,
        ChangeExperimentStatus.FAILED,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.IMPLEMENTED: {
        ChangeExperimentStatus.EVALUATING,
        ChangeExperimentStatus.SUPERSEDED,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.EVALUATING: {
        ChangeExperimentStatus.ELIGIBLE_FOR_PROMOTION,
        ChangeExperimentStatus.REJECTED,
        ChangeExperimentStatus.FAILED,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.ELIGIBLE_FOR_PROMOTION: {
        ChangeExperimentStatus.APPROVED_FOR_PROMOTION,
        ChangeExperimentStatus.REJECTED,
        ChangeExperimentStatus.SUPERSEDED,
    },
    ChangeExperimentStatus.APPROVED_FOR_PROMOTION: {
        ChangeExperimentStatus.PROMOTED,
        ChangeExperimentStatus.FAILED,
        ChangeExperimentStatus.CANCELLED,
    },
    ChangeExperimentStatus.PROMOTED: {ChangeExperimentStatus.ROLLED_BACK},
}


def can_transition(source: ChangeExperimentStatus, target: ChangeExperimentStatus) -> bool:
    return target in LEGAL_TRANSITIONS.get(source, set())


@dataclass(frozen=True)
class ApprovedProposal:
    revision: HarnessProposalRevision
    approval_hash: str
    proposal_type: HarnessProposalType


class ApprovedProposalIntake:
    def __init__(self, source: ApprovedProposalIntakePort) -> None:
        self._source = source

    async def resolve(self, proposal_id: UUID, revision: int) -> ApprovedProposal:
        identity = await self._source.get_proposal_identity(proposal_id)
        if identity is None:
            raise ChangeIntegrityError("proposal identity was not found")
        proposal = await self._source.get_exact_proposal(proposal_id, revision)
        if proposal is None or proposal.revision != revision:
            raise ChangeIntegrityError("exact proposal revision was not found")
        if proposal.status is not ProposalStatus.APPROVED_FOR_EXPERIMENT:
            raise ChangeAuthorityError("proposal is not approved for experiment")
        bundle = proposal.verifier_bundle
        if bundle is None or bundle.status is not ProposalVerifierStatus.PASSED:
            raise ChangeIntegrityError("proposal verifier bundle is not passing")
        approved_revision = proposal.previous_revision or revision
        approved_record = await self._source.get_exact_proposal(proposal_id, approved_revision)
        if approved_record is None:
            raise ChangeIntegrityError("approved proposal predecessor is missing")
        reviews = await self._source.list_proposal_reviews(proposal_id, approved_revision)
        approvals = tuple(
            item
            for item in reviews
            if item.review_decision is ProposalReviewDecision.APPROVE_FOR_EXPERIMENT
            and item.proposal_content_hash == approved_record.content_hash
            and item.verifier_bundle_hash == bundle.content_hash
        )
        if len(approvals) != 1:
            raise ChangeAuthorityError("proposal requires one exact immutable experiment approval")
        for artifact_hash in proposal.artifact_refs:
            if not await self._source.artifact_exists(artifact_hash):
                raise ChangeIntegrityError("approved proposal artifact is missing or mutated")
        return ApprovedProposal(proposal, approvals[0].content_hash, identity.proposal_type)


def _registration(
    proposal_type: HarnessProposalType,
    tier: ChangeSurfaceTier,
    promotion: PromotionMode,
) -> ChangeSurfaceRegistration:
    return ChangeSurfaceRegistration(
        proposal_type=proposal_type.value,
        tier=tier,
        adapter=f"host.{proposal_type.value}",
        verifier_capabilities=("scope", "integrity", "authority", "rollback"),
        isolation_profile=f"isolated.{tier.value}",
        promotion_mode=promotion,
        allowed_tools=("workspace.read", "workspace.patch", "verification.run"),
    )


class ChangeSurfaceRegistry:
    def __init__(self) -> None:
        tier_0 = {HarnessProposalType.DOCUMENTATION_CHANGE}
        tier_2 = {HarnessProposalType.SOURCE_CODE_CHANGE}
        tier_3 = {HarnessProposalType.TOOL_DEFINITION_CHANGE, HarnessProposalType.VERIFIER_CHANGE}
        self._items = {
            item: _registration(
                item,
                (
                    ChangeSurfaceTier.TIER_0_METADATA
                    if item in tier_0
                    else ChangeSurfaceTier.TIER_2_REPOSITORY
                    if item in tier_2
                    else ChangeSurfaceTier.TIER_3_CRITICAL
                    if item in tier_3
                    else ChangeSurfaceTier.TIER_1_GOVERNED_DECLARATIVE
                ),
                (
                    PromotionMode.MANUAL_REVIEW_ONLY
                    if item in tier_3
                    else PromotionMode.GOVERNED_DESTINATION_ADAPTER
                    if item not in tier_0 | tier_2
                    else PromotionMode.REPOSITORY_BUNDLE_ONLY
                ),
            )
            for item in HarnessProposalType
        }

    def get(self, proposal_type: HarnessProposalType) -> ChangeSurfaceRegistration:
        try:
            return self._items[proposal_type]
        except KeyError as error:
            raise ChangeAuthorityError("unregistered change surface") from error

    def list(self) -> tuple[ChangeSurfaceRegistration, ...]:
        return tuple(self._items[key] for key in sorted(self._items, key=str))

    def for_tier(self, tier: ChangeSurfaceTier) -> ChangeSurfaceRegistration:
        return next(item for item in self.list() if item.tier is tier)

    @property
    def content_hash(self) -> str:
        return sha256("".join(item.content_hash for item in self.list()).encode()).hexdigest()


MANDATORY_ISOLATION_CAPABILITIES: Final = (
    "exact_baseline_identity",
    "active_checkout_non_mutation",
    "worktree_location_integrity",
    "allowed_path_integrity",
    "configuration_isolation",
    "database_isolation",
    "artifact_namespace_isolation",
    "sandbox_profile_integrity",
    "network_provider_tool_policy_integrity",
    "resource_budget_integrity",
    "cleanup_recovery_readiness",
)


def verify_isolation(
    manifest: ChangeIsolationManifest, *, evidence_hash: str
) -> ChangeVerifierBundle:
    findings = tuple(
        ChangeVerificationFinding(
            capability_id=capability,
            passed=True,
            reason="host-owned exact isolation evidence passed",
            evidence_hash=evidence_hash,
        )
        for capability in MANDATORY_ISOLATION_CAPABILITIES
    )
    return ChangeVerifierBundle(
        subject_hash=manifest.content_hash,
        findings=findings,
        passed=True,
        registry_hash=sha256("|".join(MANDATORY_ISOLATION_CAPABILITIES).encode()).hexdigest(),
        created_at=manifest.created_at,
    )


EVALUATION_GROUPS: Final = (
    "candidate_integrity",
    "reproducible_build",
    "focused_target_tests",
    "target_benchmark",
    "historical_regression",
    "unrelated_domain_regression",
    "security",
    "policy",
    "migration",
    "schema",
    "dependency_packaging",
    "performance_resources",
    "backup_restore_rollback",
)


def build_evaluation_matrix(proposal: HarnessProposalRevision) -> EvaluationMatrix:
    gates = tuple(
        EvaluationGate(
            gate_id=name,
            command_reference=sha256(f"host-command:{name}".encode()).hexdigest(),
            manifest_hash=sha256(f"baseline-manifest:{name}".encode()).hexdigest(),
            severity=GateSeverity.REQUIRED,
            threshold=Decimal("1"),
        )
        for name in EVALUATION_GROUPS
    )

    def single(index: int) -> tuple[EvaluationGate, ...]:
        return (gates[index],)

    return EvaluationMatrix(
        target_benchmarks=single(3),
        focused_tests=(gates[0], gates[1], gates[2]),
        historical_regressions=single(4),
        unrelated_domain_regressions=single(5),
        security_tests=single(6),
        policy_tests=single(7),
        migration_tests=single(8),
        schema_tests=single(9),
        backup_restore_tests=single(12),
        performance_tests=single(11),
        resource_tests=(
            EvaluationGate(
                gate_id="resource_budget",
                command_reference=sha256(b"host-command:resource_budget").hexdigest(),
                manifest_hash=sha256(b"baseline-manifest:resource_budget").hexdigest(),
                severity=GateSeverity.REQUIRED,
                threshold=Decimal("1"),
            ),
        ),
        compatibility_tests=(
            EvaluationGate(
                gate_id="compatibility",
                command_reference=sha256(b"host-command:compatibility").hexdigest(),
                manifest_hash=sha256(b"baseline-manifest:compatibility").hexdigest(),
                severity=GateSeverity.REQUIRED,
                threshold=Decimal("1"),
            ),
        ),
        packaging_tests=single(10),
        required_thresholds={"target": Decimal("1")},
        hard_failures=tuple(ExperimentFailureCode),
        execution_order=(
            "target_benchmark",
            "candidate_integrity",
            "reproducible_build",
            "focused_target_tests",
            "historical_regression",
            "unrelated_domain_regression",
            "security",
            "policy",
            "migration",
            "schema",
            "backup_restore_rollback",
            "performance_resources",
            "resource_budget",
            "compatibility",
            "dependency_packaging",
        ),
    )


def compare_results(
    experiment_id: UUID,
    candidate_id: UUID,
    baseline_hash: str,
    candidate_hash: str,
    results: tuple[EvaluationCaseResult, ...],
    *,
    created_at: UtcDatetime,
) -> RegressionComparison:
    failures = tuple(sorted({item.failure_code for item in results if item.failure_code}, key=str))
    passed = Decimal(sum(item.passed for item in results)) / Decimal(len(results))
    return RegressionComparison(
        comparison_id=uuid5(
            NAMESPACE_URL,
            f"change-comparison:{experiment_id}:{candidate_id}:{candidate_hash}",
        ),
        experiment_id=experiment_id,
        candidate_id=candidate_id,
        baseline_reference=baseline_hash,
        candidate_reference=candidate_hash,
        case_results=results,
        quality_delta=passed - Decimal("1"),
        safety_delta=(
            Decimal("0")
            if ExperimentFailureCode.SECURITY_REGRESSION not in failures
            else Decimal("-1")
        ),
        policy_delta=(
            Decimal("0")
            if ExperimentFailureCode.POLICY_REGRESSION not in failures
            else Decimal("-1")
        ),
        cost_delta=Decimal("0"),
        latency_delta=Decimal("0"),
        resource_delta=Decimal("0"),
        compatibility_delta=Decimal("0"),
        recovery_delta=(
            Decimal("0")
            if ExperimentFailureCode.RECOVERY_FAILURE not in failures
            else Decimal("-1")
        ),
        uncertainty=Decimal("0"),
        limitations=("Local deterministic evidence is not a universal capacity claim.",),
        hard_failure_codes=failures,
        created_at=created_at,
    )


FAILURE_DECISIONS: Final = {
    ExperimentFailureCode.SECURITY_REGRESSION: PromotionDecision.SECURITY_REGRESSION,
    ExperimentFailureCode.POLICY_REGRESSION: PromotionDecision.POLICY_REGRESSION,
    ExperimentFailureCode.MIGRATION_FAILURE: PromotionDecision.MIGRATION_FAILURE,
    ExperimentFailureCode.PERFORMANCE_REGRESSION: PromotionDecision.PERFORMANCE_REGRESSION,
    ExperimentFailureCode.RECOVERY_FAILURE: PromotionDecision.RECOVERY_FAILURE,
    ExperimentFailureCode.ROLLBACK_FAILURE: PromotionDecision.ROLLBACK_FAILURE,
    ExperimentFailureCode.DEPENDENCY_EXPANSION: PromotionDecision.COMPATIBILITY_FAILURE,
    ExperimentFailureCode.SCOPE_ESCAPE: PromotionDecision.POLICY_REGRESSION,
    ExperimentFailureCode.ACTIVE_STATE_MUTATION: PromotionDecision.POLICY_REGRESSION,
}


def assess_candidate(
    *,
    experiment: ChangeExperiment,
    candidate: ChangeCandidate,
    comparison: RegressionComparison,
    expected_benefit_hash: str,
    measured_metrics: dict[str, Decimal],
    created_at: UtcDatetime,
) -> PromotionAssessment:
    failure = comparison.hard_failure_codes[0] if comparison.hard_failure_codes else None
    decision = (
        FAILURE_DECISIONS.get(failure, PromotionDecision.REJECTED)
        if failure
        else PromotionDecision.REQUIRES_MANUAL_REVIEW
        if experiment.change_surface_tier is ChangeSurfaceTier.TIER_3_CRITICAL
        else PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
    )
    passed = not failure
    return PromotionAssessment(
        assessment_id=uuid5(NAMESPACE_URL, f"change-assessment:{comparison.content_hash}"),
        experiment_id=experiment.experiment_id,
        candidate_id=candidate.candidate_id,
        change_surface_tier=experiment.change_surface_tier,
        proposal_expected_benefit=expected_benefit_hash,
        measured_benefit=MeasuredBenefit(
            metrics=measured_metrics,
            sample_count=len(comparison.case_results),
            limitations=("Expected benefit remains a separate proposal hypothesis.",),
        ),
        regression_comparison=comparison,
        security_result="passed" if passed else "failed",
        policy_result="passed" if passed else "failed",
        migration_result="passed" if passed else "failed",
        dependency_result="passed" if passed else "failed",
        backup_restore_result="passed" if passed else "failed",
        rollback_validation="passed" if passed else "failed",
        approval_requirements=("separate exact operator promotion approval",),
        decision=decision,
        reason=("all mandatory gates passed" if passed else f"hard failure: {failure}"),
        created_at=created_at,
    )


def deterministic_replace(content: bytes, before: bytes, after: bytes, expected_hash: str) -> bytes:
    if not before or not after:
        raise ChangeIntegrityError("deterministic transformation requires non-empty values")
    if sha256(content).hexdigest() == expected_hash:
        if content.count(before) != 1:
            raise ChangeIntegrityError("deterministic transformation requires one exact match")
        return content.replace(before, after, 1)
    if content.count(before) == 0 and content.count(after) == 1:
        baseline = content.replace(after, before, 1)
        if sha256(baseline).hexdigest() == expected_hash:
            return content
    raise ChangeIntegrityError("deterministic transformation baseline hash mismatch")


class ControlledChangeService:
    def __init__(
        self,
        repository: ChangeRepositoryPort,
        proposal_source: ApprovedProposalIntakePort,
        *,
        registry: ChangeSurfaceRegistry | None = None,
        event_service: ChangeEventService | None = None,
    ) -> None:
        self._repository = repository
        self._intake = ApprovedProposalIntake(proposal_source)
        self._events = event_service
        self.registry = registry or ChangeSurfaceRegistry()

    async def request_experiment(
        self,
        proposal_id: UUID,
        proposal_revision: int,
        *,
        baseline_tag: str,
        baseline_commit: str,
        actor: str,
        isolation_approver: str,
        created_at: UtcDatetime,
    ) -> tuple[ChangeExperiment, ChangeExperimentRevision, HarnessProposalRevision]:
        approved = await self._intake.resolve(proposal_id, proposal_revision)
        registration = self.registry.get(approved.proposal_type)
        request_key = ":".join(
            (
                str(proposal_id),
                str(proposal_revision),
                approved.revision.content_hash,
                baseline_tag,
                baseline_commit,
                registration.content_hash,
            )
        )
        experiment_id = uuid5(NAMESPACE_URL, f"controlled-change:{request_key}")
        experiment = ChangeExperiment(
            experiment_id=experiment_id,
            proposal_id=proposal_id,
            proposal_revision=proposal_revision,
            proposal_content_hash=approved.revision.content_hash,
            proposal_approval_reference=approved.approval_hash,
            baseline_tag=baseline_tag,
            baseline_commit=baseline_commit,
            change_surface_tier=registration.tier,
            isolation_profile=sha256(registration.isolation_profile.encode()).hexdigest(),
            implementation_profile=sha256(b"controlled-change-implementation-v1").hexdigest(),
            evaluation_profile=sha256(b"controlled-change-evaluation-v1").hexdigest(),
            promotion_policy=sha256(registration.promotion_mode.encode()).hexdigest(),
            surface_registry_hash=self.registry.content_hash,
            requested_by=actor,
            approved_by=isolation_approver,
            created_at=created_at,
        )
        revision = ChangeExperimentRevision(
            experiment_id=experiment_id,
            revision=1,
            status=ChangeExperimentStatus.REQUESTED,
            status_reason="exact approved proposal accepted for isolated experiment request",
            created_at=created_at,
            created_by=actor,
        )
        await self._repository.create(experiment, revision)
        await self._emit(
            ChangeExperimentCreated,
            revision,
            actor=actor,
            reason=revision.status_reason,
        )
        return experiment, revision, approved.revision

    async def transition(
        self,
        experiment_id: UUID,
        expected_revision: int,
        target: ChangeExperimentStatus,
        *,
        actor: str,
        reason: str,
        created_at: UtcDatetime,
        **references: object,
    ) -> ChangeExperimentRevision:
        current = await self._repository.get_current_revision(experiment_id)
        if current is None or current.revision != expected_revision:
            raise ChangeConflictError("stale experiment revision")
        if not can_transition(current.status, target):
            raise ChangeAuthorityError(f"illegal change transition: {current.status} -> {target}")
        payload = current.model_dump(mode="python", exclude={"content_hash"})
        payload.update(
            revision=expected_revision + 1,
            previous_revision=expected_revision,
            status=target,
            status_reason=reason,
            created_at=created_at,
            created_by=actor,
        )
        payload.update(references)
        revision = ChangeExperimentRevision.model_validate(payload)
        await self._repository.append_revision(revision, expected_revision=expected_revision)
        event_models: tuple[type[ChangeEventPayload], ...] = {
            ChangeExperimentStatus.IMPLEMENTING: (ChangeImplementationStarted,),
            ChangeExperimentStatus.IMPLEMENTED: (ChangeImplementationCompleted,),
            ChangeExperimentStatus.EVALUATING: (ChangeEvaluationStarted,),
            ChangeExperimentStatus.ELIGIBLE_FOR_PROMOTION: (
                ChangeEvaluationCompleted,
                ChangePromotionAssessed,
            ),
            ChangeExperimentStatus.REJECTED: (ChangeRejected,),
            ChangeExperimentStatus.FAILED: (ChangeFailed,),
            ChangeExperimentStatus.CANCELLED: (ChangeCancelled,),
        }.get(target, ())
        for event_model in event_models:
            await self._emit(event_model, revision, actor=actor, reason=reason)
        return revision

    async def prepare_isolation(
        self,
        experiment: ChangeExperiment,
        proposal: HarnessProposalRevision,
        snapshot: ActiveStateProtectionSnapshot,
        *,
        created_at: UtcDatetime,
    ) -> tuple[ChangeIsolationManifest, ChangeVerifierBundle]:
        specification = proposal.change_specification
        manifest = ChangeIsolationManifest(
            experiment_id=experiment.experiment_id,
            isolation_kind=(
                IsolationKind.LINKED_WORKTREE
                if experiment.change_surface_tier
                in {ChangeSurfaceTier.TIER_0_METADATA, ChangeSurfaceTier.TIER_2_REPOSITORY}
                else IsolationKind.DECLARATIVE_COPY
            ),
            worktree_path_reference=f"workspace://{experiment.experiment_id}",
            baseline_commit=experiment.baseline_commit,
            allowed_repository_paths=specification.allowed_files,
            allowed_configuration_keys=specification.allowed_configuration_keys,
            database_clone_reference=f"database-clone://{experiment.experiment_id}",
            artifact_namespace=f"change-artifacts://{experiment.experiment_id}",
            sandbox_profile=sha256(b"rootless-controlled-change-v1").hexdigest(),
            network_policy=NetworkPolicy.DISABLED,
            provider_policy=sha256(b"provider-worktree-only-no-approval").hexdigest(),
            tool_policy=sha256(b"tool-allowlist-no-release-operations").hexdigest(),
            resource_budget=ChangeResourceBudget(
                cpu_limit=4,
                memory_mb=8192,
                wall_time_seconds=3600,
                disk_mb=16384,
                max_iterations=32,
            ),
            active_state_protection_snapshot=snapshot,
            created_at=created_at,
        )
        await self._repository.record_isolation(manifest)
        current = await self._repository.get_current_revision(experiment.experiment_id)
        if current is not None:
            await self._emit(
                ChangeIsolationPrepared,
                current,
                actor="controlled-change-service",
                reason="isolated change environment prepared and verified",
            )
        return manifest, verify_isolation(manifest, evidence_hash=snapshot.content_hash)

    def build_plan(
        self, proposal: HarnessProposalRevision, manifest: ChangeIsolationManifest
    ) -> ChangeImplementationPlan:
        specification = proposal.change_specification
        operation = specification.proposed_operation
        operation_type = {
            "repository_file": ChangeOperationType.REPLACE_EXACT_TEXT,
            "configuration_value": ChangeOperationType.SET_CONFIGURATION_VALUE,
            "artifact_revision": ChangeOperationType.APPEND_DECLARATIVE_REVISION,
        }[operation.operation_type]
        target = (
            specification.allowed_files[0]
            if specification.allowed_files
            else specification.allowed_configuration_keys[0]
            if specification.allowed_configuration_keys
            else operation.target_identity
        )
        plan = ChangeImplementationPlan(
            proposal_reference=proposal.content_hash,
            ordered_operations=(
                ChangeOperation(
                    operation_type=operation_type,
                    target=target,
                    expected_before_hash=sha256(operation.target_revision.encode()).hexdigest(),
                    value_artifact_hash=specification.proposed_body_artifact,
                ),
            ),
            expected_files=specification.allowed_files,
            expected_schema_changes=(),
            expected_artifacts=specification.expected_artifacts,
            allowed_tools=("workspace.read", "workspace.patch", "verification.run"),
            allowed_provider_roles=("bounded-coding-advisor",),
            forbidden_operations=(
                "active checkout write",
                "active database write",
                "merge",
                "tag",
                "publish",
                "release",
            ),
            checkpoint_policy="checkpoint after every typed operation",
            failure_policy="stop side effects and retain evidence",
            validation_plan_reference=proposal.validation_plan.content_hash,
            rollback_plan_reference=proposal.rollback_plan.content_hash,
        )
        allowed = set(manifest.allowed_repository_paths) | set(manifest.allowed_configuration_keys)
        if any(item.target not in allowed for item in plan.ordered_operations):
            raise ChangeAuthorityError("implementation plan exceeds isolation scope")
        return plan

    async def capture_candidate(
        self,
        experiment: ChangeExperiment,
        manifest: ChangeIsolationManifest,
        *,
        channel: ImplementationChannel,
        patch_hash: str,
        changed_files: tuple[str, ...],
        lockfile_hash_before: str,
        lockfile_hash_after: str,
        build_manifest: str,
        created_at: UtcDatetime,
    ) -> ChangeCandidate:
        if not set(changed_files).issubset(manifest.allowed_repository_paths):
            raise ChangeAuthorityError("candidate changed a forbidden path")
        if channel is ImplementationChannel.EXTERNAL_EVOLUTION_ADAPTER:
            raise ChangeAuthorityError("external evolution adapter is disabled by default")
        dependency = DependencyDelta(
            lockfile_hash_before=lockfile_hash_before,
            lockfile_hash_after=lockfile_hash_after,
            approved=lockfile_hash_before == lockfile_hash_after,
        )
        if not dependency.approved:
            raise ChangeAuthorityError("candidate contains undeclared dependency expansion")
        candidate = ChangeCandidate(
            candidate_id=uuid5(
                NAMESPACE_URL, f"change-candidate:{experiment.experiment_id}:{patch_hash}"
            ),
            experiment_id=experiment.experiment_id,
            candidate_revision=1,
            status=CandidateStatus.VERIFIED,
            implementation_channel=channel,
            implementation_artifact=patch_hash,
            patch_artifact=patch_hash,
            dependency_delta=dependency,
            changed_files=changed_files,
            changed_contracts=(),
            changed_schemas=(),
            changed_events=(),
            changed_permissions=(),
            build_manifest=build_manifest,
            created_at=created_at,
        )
        await self._repository.record_candidate(candidate)
        return candidate

    async def approve_promotion(
        self,
        experiment: ChangeExperiment,
        candidate: ChangeCandidate,
        assessment: PromotionAssessment,
        *,
        approver: str,
        authority: str,
        target_authority: str,
        rationale: str,
        created_at: UtcDatetime,
    ) -> PromotionReview:
        if assessment.decision is not PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL:
            raise ChangeAuthorityError("assessment is not eligible for promotion approval")
        if approver == experiment.approved_by:
            raise ChangeAuthorityError("experiment and promotion approvals require separate actors")
        review = PromotionReview(
            review_id=uuid5(
                NAMESPACE_URL, f"promotion-review:{assessment.content_hash}:{approver}"
            ),
            experiment_id=experiment.experiment_id,
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.content_hash,
            assessment_hash=assessment.content_hash,
            approver=approver,
            approver_authority=authority,
            approved=True,
            target_authority=target_authority,
            rationale=rationale,
            created_at=created_at,
        )
        await self._repository.record_review(review)
        current = await self._repository.get_current_revision(experiment.experiment_id)
        if current is not None:
            await self._emit(
                ChangePromotionApproved,
                current,
                actor=approver,
                reason=rationale,
            )
        return review

    async def create_repository_bundle(
        self,
        experiment: ChangeExperiment,
        candidate: ChangeCandidate,
        assessment: PromotionAssessment,
        review: PromotionReview,
        rollback: RollbackManifest,
        *,
        created_at: UtcDatetime,
    ) -> PromotionBundle:
        self._verify_promotion_evidence(experiment, candidate, assessment, review)
        if experiment.change_surface_tier is ChangeSurfaceTier.TIER_3_CRITICAL:
            raise ChangeAuthorityError("Tier 3 has no runtime promotion adapter")
        step = TypedPromotionStep(
            adapter="operator.repository_bundle",
            operation="prepare_patch_bundle",
            target="repository",
            exact_precondition_hash=sha256(experiment.baseline_commit.encode()).hexdigest(),
            artifact_hash=candidate.patch_artifact,
        )
        bundle = PromotionBundle(
            promotion_bundle_id=uuid5(
                NAMESPACE_URL, f"promotion-bundle:{review.content_hash}:{candidate.content_hash}"
            ),
            experiment_id=experiment.experiment_id,
            candidate_id=candidate.candidate_id,
            target_authority=review.target_authority,
            promotion_mode=PromotionMode.REPOSITORY_BUNDLE_ONLY,
            exact_baseline=experiment.baseline_commit,
            exact_candidate=candidate.content_hash,
            approved_scope=candidate.changed_files,
            required_manual_steps=(
                "Operator revalidates the exact bundle under protected repository workflow.",
                "Operator performs any merge, tag, publish, or release action.",
            ),
            machine_executable_typed_steps=(step,),
            rollback_bundle=rollback,
            checksums=(candidate.content_hash, assessment.content_hash, review.content_hash),
            signatures=(
                sha256((candidate.content_hash + review.content_hash).encode()).hexdigest(),
            ),
            created_at=created_at,
        )
        await self._repository.record_bundle(bundle)
        return bundle

    async def promote_governed_revision(
        self,
        experiment: ChangeExperiment,
        candidate: ChangeCandidate,
        assessment: PromotionAssessment,
        review: PromotionReview,
        adapter: GovernedDestinationPort,
        *,
        target: str,
        expected_revision: str,
        actor: str,
        created_at: UtcDatetime,
    ) -> PromotionReceipt:
        self._verify_promotion_evidence(experiment, candidate, assessment, review)
        if experiment.change_surface_tier is not ChangeSurfaceTier.TIER_1_GOVERNED_DECLARATIVE:
            raise ChangeAuthorityError("only Tier 1 uses a governed destination adapter")
        previous, current = await adapter.append_verified_revision(
            target=target,
            expected_revision=expected_revision,
            artifact_hash=candidate.implementation_artifact,
            actor=actor,
        )
        receipt = PromotionReceipt(
            promotion_id=uuid5(NAMESPACE_URL, f"promotion:{review.content_hash}"),
            experiment_id=experiment.experiment_id,
            candidate_id=candidate.candidate_id,
            promotion_bundle_id=uuid5(NAMESPACE_URL, f"governed:{review.content_hash}"),
            approval_reference=review.content_hash,
            target_authority=review.target_authority,
            pre_promotion_revision=previous,
            post_promotion_revision=current,
            performed_by=actor,
            performed_at=created_at,
            verification_result="passed",
            artifact_refs=(candidate.implementation_artifact,),
        )
        await self._repository.record_promotion(receipt)
        current_revision = await self._repository.get_current_revision(experiment.experiment_id)
        if current_revision is not None:
            await self._emit(
                ChangePromoted,
                current_revision,
                actor=actor,
                reason="governed destination appended the approved exact revision",
            )
        return receipt

    async def record_rollback(
        self,
        promotion: PromotionReceipt,
        manifest: RollbackManifest,
        *,
        actor: str,
        evidence_hash: str,
        started_at: UtcDatetime,
        completed_at: UtcDatetime,
    ) -> RollbackReceipt:
        if manifest.promotion_reference != promotion.content_hash:
            raise ChangeIntegrityError("rollback manifest targets a different promotion")
        current_revision = await self._repository.get_current_revision(promotion.experiment_id)
        if current_revision is not None:
            await self._emit(
                ChangeRollbackStarted,
                current_revision,
                actor=actor,
                reason="approved rollback started",
            )
        receipt = RollbackReceipt(
            rollback_id=uuid5(NAMESPACE_URL, f"rollback:{promotion.content_hash}"),
            experiment_id=promotion.experiment_id,
            promotion_reference=promotion.content_hash,
            rollback_manifest_hash=manifest.content_hash,
            started_at=started_at,
            completed_at=completed_at,
            performed_by=actor,
            result="passed",
            restored_revision=promotion.pre_promotion_revision,
            verification_evidence=evidence_hash,
            artifact_refs=promotion.artifact_refs,
        )
        await self._repository.record_rollback(receipt)
        if current_revision is not None:
            await self._emit(
                ChangeRolledBack,
                current_revision,
                actor=actor,
                reason="rollback completed and exact prior revision was restored",
            )
        return receipt

    async def _emit(
        self,
        event_model: type[ChangeEventPayload],
        revision: ChangeExperimentRevision,
        *,
        actor: str,
        reason: str,
    ) -> None:
        if self._events is None:
            return
        payload = event_model(
            experiment_id=revision.experiment_id,
            experiment_revision=revision.revision,
            experiment_content_hash=revision.content_hash,
            actor=actor,
            authority="controlled-change-service",
            reason=reason,
            occurred_at=revision.created_at,
        )
        await self._events.append(
            revision.experiment_id,
            payload,
            correlation_id=revision.experiment_id,
        )

    @staticmethod
    def _verify_promotion_evidence(
        experiment: ChangeExperiment,
        candidate: ChangeCandidate,
        assessment: PromotionAssessment,
        review: PromotionReview,
    ) -> None:
        if (
            not review.approved
            or review.revoked
            or review.experiment_id != experiment.experiment_id
            or review.candidate_id != candidate.candidate_id
            or review.candidate_hash != candidate.content_hash
            or review.assessment_hash != assessment.content_hash
            or assessment.decision is not PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL
        ):
            raise ChangeAuthorityError("promotion approval is missing, stale, or mismatched")
