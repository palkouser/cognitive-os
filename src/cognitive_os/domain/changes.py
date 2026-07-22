"""Immutable contracts for regression-gated controlled changes."""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, StringConstraints, field_validator, model_validator

from .common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract

GitCommitHex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]


class ChangeExperimentStatus(StrEnum):
    REQUESTED = "requested"
    APPROVED_FOR_ISOLATION = "approved_for_isolation"
    PREPARING = "preparing"
    IMPLEMENTING = "implementing"
    IMPLEMENTED = "implemented"
    EVALUATING = "evaluating"
    FAILED = "failed"
    REJECTED = "rejected"
    ELIGIBLE_FOR_PROMOTION = "eligible_for_promotion"
    APPROVED_FOR_PROMOTION = "approved_for_promotion"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class ChangeSurfaceTier(StrEnum):
    TIER_0_METADATA = "tier_0_metadata"
    TIER_1_GOVERNED_DECLARATIVE = "tier_1_governed_declarative"
    TIER_2_REPOSITORY = "tier_2_repository"
    TIER_3_CRITICAL = "tier_3_critical"


class ImplementationChannel(StrEnum):
    DETERMINISTIC_TRANSFORMATION = "deterministic_transformation"
    COGNITIVE_OS_CODING_AGENT = "cognitive_os_coding_agent"
    CLAUDE_CODE_ROLE = "claude_code_role"
    EXTERNAL_EVOLUTION_ADAPTER = "external_evolution_adapter"


class PromotionDecision(StrEnum):
    ELIGIBLE_FOR_OPERATOR_APPROVAL = "eligible_for_operator_approval"
    INSUFFICIENT_IMPROVEMENT = "insufficient_improvement"
    TARGET_FAILURE = "target_failure"
    HISTORICAL_REGRESSION = "historical_regression"
    UNRELATED_DOMAIN_REGRESSION = "unrelated_domain_regression"
    SECURITY_REGRESSION = "security_regression"
    POLICY_REGRESSION = "policy_regression"
    PERFORMANCE_REGRESSION = "performance_regression"
    COMPATIBILITY_FAILURE = "compatibility_failure"
    MIGRATION_FAILURE = "migration_failure"
    RECOVERY_FAILURE = "recovery_failure"
    ROLLBACK_FAILURE = "rollback_failure"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    REJECTED = "rejected"


class IsolationKind(StrEnum):
    LINKED_WORKTREE = "linked_worktree"
    DECLARATIVE_COPY = "declarative_copy"


class NetworkPolicy(StrEnum):
    DISABLED = "disabled"
    APPROVED_PROVIDER_ONLY = "approved_provider_only"


class PromotionMode(StrEnum):
    REPOSITORY_BUNDLE_ONLY = "repository_bundle_only"
    GOVERNED_DESTINATION_ADAPTER = "governed_destination_adapter"
    MANUAL_REVIEW_ONLY = "manual_review_only"


class EvaluationRunStatus(StrEnum):
    REQUESTED = "requested"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandidateStatus(StrEnum):
    CAPTURED = "captured"
    VERIFIED = "verified"
    REJECTED = "rejected"


class GateSeverity(StrEnum):
    REQUIRED = "required"
    DIAGNOSTIC = "diagnostic"


class ChangeOperationType(StrEnum):
    REPLACE_EXACT_TEXT = "replace_exact_text"
    SET_CONFIGURATION_VALUE = "set_configuration_value"
    APPEND_DECLARATIVE_REVISION = "append_declarative_revision"
    WRITE_APPROVED_ARTIFACT = "write_approved_artifact"


class ExperimentFailureCode(StrEnum):
    STALE_PROPOSAL = "stale_proposal"
    UNAPPROVED_PROPOSAL = "unapproved_proposal"
    HASH_MISMATCH = "hash_mismatch"
    BASELINE_MISMATCH = "baseline_mismatch"
    ACTIVE_STATE_MUTATION = "active_state_mutation"
    SCOPE_ESCAPE = "scope_escape"
    SECURITY_REGRESSION = "security_regression"
    POLICY_REGRESSION = "policy_regression"
    MIGRATION_FAILURE = "migration_failure"
    DEPENDENCY_EXPANSION = "dependency_expansion"
    PERFORMANCE_REGRESSION = "performance_regression"
    RECOVERY_FAILURE = "recovery_failure"
    ROLLBACK_FAILURE = "rollback_failure"
    MISSING_APPROVAL = "missing_approval"


class ChangeAccessType(StrEnum):
    READ = "read"
    CREATE = "create"
    EVALUATE = "evaluate"
    APPROVE = "approve"
    PROMOTE = "promote"
    ROLLBACK = "rollback"


def _explicit_relative(value: str) -> str:
    posix = PurePosixPath(value)
    if (
        not value
        or "*" in value
        or ".." in posix.parts
        or posix.is_absolute()
        or PureWindowsPath(value).is_absolute()
        or re.match(r"^[A-Za-z]:[\\/]", value)
    ):
        raise ValueError("change scope must be explicit, relative, and wildcard-free")
    return value


class ChangeResourceBudget(HashedExperienceContract):
    cpu_limit: int = Field(ge=1, le=64)
    memory_mb: int = Field(ge=128, le=262144)
    wall_time_seconds: int = Field(ge=1, le=86400)
    disk_mb: int = Field(ge=16, le=1048576)
    max_iterations: int = Field(ge=1, le=1000)


class ActiveStateProtectionSnapshot(HashedExperienceContract):
    repository_commit: GitCommitHex
    repository_status_hash: Sha256Hex
    repository_manifest_hash: Sha256Hex
    active_database_fingerprint: Sha256Hex
    active_artifact_namespace_hash: Sha256Hex
    captured_at: UtcDatetime


class ChangeExperiment(HashedExperienceContract):
    experiment_id: UUID
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    proposal_content_hash: Sha256Hex
    proposal_approval_reference: Sha256Hex
    baseline_tag: NonEmptyStr
    baseline_commit: GitCommitHex
    change_surface_tier: ChangeSurfaceTier
    isolation_profile: Sha256Hex
    implementation_profile: Sha256Hex
    evaluation_profile: Sha256Hex
    promotion_policy: Sha256Hex
    surface_registry_hash: Sha256Hex
    requested_by: NonEmptyStr
    approved_by: NonEmptyStr
    created_at: UtcDatetime


class ChangeExperimentRevision(HashedExperienceContract):
    experiment_id: UUID
    revision: int = Field(gt=0)
    previous_revision: int | None = Field(default=None, gt=0)
    status: ChangeExperimentStatus
    status_reason: NonEmptyStr
    isolation_manifest_ref: Sha256Hex | None = None
    implementation_plan_ref: Sha256Hex | None = None
    candidate_refs: tuple[Sha256Hex, ...] = ()
    evaluation_run_refs: tuple[Sha256Hex, ...] = ()
    promotion_assessment_ref: Sha256Hex | None = None
    promotion_ref: Sha256Hex | None = None
    rollback_ref: Sha256Hex | None = None
    artifact_refs: tuple[Sha256Hex, ...] = ()
    created_at: UtcDatetime
    created_by: NonEmptyStr

    @model_validator(mode="after")
    def contiguous(self) -> ChangeExperimentRevision:
        if (self.revision == 1) != (self.previous_revision is None):
            raise ValueError(
                "initial change revision must be the only revision without a predecessor"
            )
        if self.revision > 1 and self.previous_revision != self.revision - 1:
            raise ValueError("change revisions must be contiguous")
        return self


class ChangeIsolationManifest(HashedExperienceContract):
    experiment_id: UUID
    isolation_kind: IsolationKind
    worktree_path_reference: NonEmptyStr
    baseline_commit: GitCommitHex
    allowed_repository_paths: tuple[NonEmptyStr, ...]
    allowed_configuration_keys: tuple[NonEmptyStr, ...]
    database_clone_reference: NonEmptyStr
    artifact_namespace: NonEmptyStr
    sandbox_profile: Sha256Hex
    network_policy: NetworkPolicy
    provider_policy: Sha256Hex
    tool_policy: Sha256Hex
    resource_budget: ChangeResourceBudget
    active_state_protection_snapshot: ActiveStateProtectionSnapshot
    created_at: UtcDatetime

    @field_validator("allowed_repository_paths", "allowed_configuration_keys")
    @classmethod
    def explicit_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({_explicit_relative(item) for item in value}))

    @field_validator("worktree_path_reference", "database_clone_reference", "artifact_namespace")
    @classmethod
    def opaque_reference(cls, value: str) -> str:
        if value.startswith(("/", "~")) or "password" in value.lower():
            raise ValueError(
                "isolation manifests expose opaque references, not host paths or secrets"
            )
        return value


class ChangeOperation(HashedExperienceContract):
    operation_type: ChangeOperationType
    target: NonEmptyStr
    expected_before_hash: Sha256Hex
    value_artifact_hash: Sha256Hex

    _target_is_explicit = field_validator("target")(_explicit_relative)


class ChangeImplementationPlan(HashedExperienceContract):
    proposal_reference: Sha256Hex
    ordered_operations: Annotated[tuple[ChangeOperation, ...], Field(min_length=1)]
    expected_files: tuple[NonEmptyStr, ...]
    expected_schema_changes: tuple[NonEmptyStr, ...]
    expected_artifacts: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    allowed_tools: tuple[NonEmptyStr, ...]
    allowed_provider_roles: tuple[NonEmptyStr, ...]
    forbidden_operations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    checkpoint_policy: NonEmptyStr
    failure_policy: NonEmptyStr
    validation_plan_reference: Sha256Hex
    rollback_plan_reference: Sha256Hex

    @field_validator("expected_files")
    @classmethod
    def explicit_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({_explicit_relative(item) for item in value}))


class DependencyDelta(HashedExperienceContract):
    added: tuple[NonEmptyStr, ...] = ()
    removed: tuple[NonEmptyStr, ...] = ()
    lockfile_hash_before: Sha256Hex
    lockfile_hash_after: Sha256Hex
    approved: bool = False


class ChangeCandidate(HashedExperienceContract):
    candidate_id: UUID
    experiment_id: UUID
    candidate_revision: int = Field(gt=0)
    status: CandidateStatus
    implementation_channel: ImplementationChannel
    implementation_artifact: Sha256Hex
    patch_artifact: Sha256Hex
    configuration_artifact: Sha256Hex | None = None
    migration_artifact: Sha256Hex | None = None
    dependency_delta: DependencyDelta
    changed_files: tuple[NonEmptyStr, ...]
    changed_contracts: tuple[NonEmptyStr, ...]
    changed_schemas: tuple[NonEmptyStr, ...]
    changed_events: tuple[NonEmptyStr, ...]
    changed_permissions: tuple[NonEmptyStr, ...]
    build_manifest: Sha256Hex
    created_at: UtcDatetime

    @field_validator("changed_files")
    @classmethod
    def explicit_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({_explicit_relative(item) for item in value}))


class EvaluationGate(HashedExperienceContract):
    gate_id: NonEmptyStr
    command_reference: Sha256Hex
    manifest_hash: Sha256Hex
    severity: GateSeverity
    threshold: Decimal


class EvaluationMatrix(HashedExperienceContract):
    target_benchmarks: tuple[EvaluationGate, ...]
    focused_tests: tuple[EvaluationGate, ...]
    historical_regressions: tuple[EvaluationGate, ...]
    unrelated_domain_regressions: tuple[EvaluationGate, ...]
    security_tests: tuple[EvaluationGate, ...]
    policy_tests: tuple[EvaluationGate, ...]
    migration_tests: tuple[EvaluationGate, ...]
    schema_tests: tuple[EvaluationGate, ...]
    backup_restore_tests: tuple[EvaluationGate, ...]
    performance_tests: tuple[EvaluationGate, ...]
    resource_tests: tuple[EvaluationGate, ...]
    compatibility_tests: tuple[EvaluationGate, ...]
    packaging_tests: tuple[EvaluationGate, ...]
    required_thresholds: dict[NonEmptyStr, Decimal]
    hard_failures: tuple[ExperimentFailureCode, ...]
    execution_order: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def complete(self) -> EvaluationMatrix:
        groups = (
            self.target_benchmarks,
            self.focused_tests,
            self.historical_regressions,
            self.unrelated_domain_regressions,
            self.security_tests,
            self.policy_tests,
            self.migration_tests,
            self.schema_tests,
            self.backup_restore_tests,
            self.performance_tests,
            self.resource_tests,
            self.compatibility_tests,
            self.packaging_tests,
        )
        ids = tuple(gate.gate_id for group in groups for gate in group)
        if not all(groups) or tuple(self.execution_order) != ids or len(set(ids)) != len(ids):
            raise ValueError("evaluation matrix must contain every gate exactly once in order")
        return self


class EvaluationCaseResult(HashedExperienceContract):
    gate_id: NonEmptyStr
    passed: bool
    measured_value: Decimal
    threshold: Decimal
    evidence_artifact: Sha256Hex
    failure_code: ExperimentFailureCode | None = None


class EvaluationRun(HashedExperienceContract):
    evaluation_run_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    matrix_hash: Sha256Hex
    baseline_reference: Sha256Hex
    candidate_reference: Sha256Hex
    started_at: UtcDatetime
    completed_at: UtcDatetime | None = None
    status: EvaluationRunStatus
    case_result_artifacts: tuple[Sha256Hex, ...]
    raw_log_artifacts: tuple[Sha256Hex, ...]
    resource_profile: dict[NonEmptyStr, JsonValue]


class MeasuredBenefit(HashedExperienceContract):
    metrics: dict[NonEmptyStr, Decimal]
    sample_count: int = Field(ge=0)
    limitations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]


class RegressionComparison(HashedExperienceContract):
    comparison_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    baseline_reference: Sha256Hex
    candidate_reference: Sha256Hex
    case_results: Annotated[tuple[EvaluationCaseResult, ...], Field(min_length=1)]
    quality_delta: Decimal
    safety_delta: Decimal
    policy_delta: Decimal
    cost_delta: Decimal
    latency_delta: Decimal
    resource_delta: Decimal
    compatibility_delta: Decimal
    recovery_delta: Decimal
    uncertainty: Decimal = Field(ge=0)
    limitations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    hard_failure_codes: tuple[ExperimentFailureCode, ...]
    created_at: UtcDatetime

    @model_validator(mode="after")
    def failures_match_results(self) -> RegressionComparison:
        expected = tuple(
            sorted(
                {item.failure_code for item in self.case_results if item.failure_code},
                key=str,
            )
        )
        if tuple(sorted(set(self.hard_failure_codes), key=str)) != expected:
            raise ValueError("comparison hard failures must match raw case evidence")
        return self


class PromotionAssessment(HashedExperienceContract):
    assessment_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    change_surface_tier: ChangeSurfaceTier
    proposal_expected_benefit: Sha256Hex
    measured_benefit: MeasuredBenefit
    regression_comparison: RegressionComparison
    security_result: Literal["passed", "failed"]
    policy_result: Literal["passed", "failed"]
    migration_result: Literal["passed", "failed", "not_applicable"]
    dependency_result: Literal["passed", "failed"]
    backup_restore_result: Literal["passed", "failed"]
    rollback_validation: Literal["passed", "failed"]
    approval_requirements: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    decision: PromotionDecision
    reason: NonEmptyStr
    created_at: UtcDatetime

    @model_validator(mode="after")
    def enforce_decision(self) -> PromotionAssessment:
        failed = bool(self.regression_comparison.hard_failure_codes) or "failed" in {
            self.security_result,
            self.policy_result,
            self.migration_result,
            self.dependency_result,
            self.backup_restore_result,
            self.rollback_validation,
        }
        if failed and self.decision in {
            PromotionDecision.ELIGIBLE_FOR_OPERATOR_APPROVAL,
            PromotionDecision.REQUIRES_MANUAL_REVIEW,
        }:
            raise ValueError("hard failures cannot produce a promotable assessment")
        if (
            self.change_surface_tier is ChangeSurfaceTier.TIER_3_CRITICAL
            and self.decision is not PromotionDecision.REQUIRES_MANUAL_REVIEW
            and not failed
        ):
            raise ValueError("Tier 3 assessments require manual review")
        return self


class PromotionReview(HashedExperienceContract):
    review_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    candidate_hash: Sha256Hex
    assessment_hash: Sha256Hex
    approver: NonEmptyStr
    approver_authority: NonEmptyStr
    approved: bool
    target_authority: NonEmptyStr
    expires_at: UtcDatetime | None = None
    revoked: bool = False
    rationale: NonEmptyStr
    created_at: UtcDatetime

    @field_validator("approver", "approver_authority")
    @classmethod
    def human_authority(cls, value: str) -> str:
        if value.lower().startswith(("provider", "model", "candidate", "experiment")):
            raise ValueError("provider, model, candidate, and experiment actors cannot approve")
        return value


class TypedPromotionStep(HashedExperienceContract):
    adapter: NonEmptyStr
    operation: Literal["append_revision", "verify_revision", "prepare_patch_bundle"]
    target: NonEmptyStr
    exact_precondition_hash: Sha256Hex
    artifact_hash: Sha256Hex


class RollbackManifest(HashedExperienceContract):
    promotion_reference: Sha256Hex
    pre_promotion_state: Sha256Hex
    post_promotion_state: Sha256Hex
    rollback_operations: Annotated[tuple[TypedPromotionStep, ...], Field(min_length=1)]
    artifact_restore_requirements: tuple[Sha256Hex, ...]
    database_restore_requirements: tuple[Sha256Hex, ...]
    verification_plan: Sha256Hex
    maximum_recovery_objective: int = Field(gt=0)
    manual_steps: tuple[NonEmptyStr, ...]
    created_at: UtcDatetime


class PromotionBundle(HashedExperienceContract):
    promotion_bundle_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    target_authority: NonEmptyStr
    promotion_mode: PromotionMode
    exact_baseline: GitCommitHex
    exact_candidate: Sha256Hex
    approved_scope: tuple[NonEmptyStr, ...]
    required_manual_steps: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    machine_executable_typed_steps: tuple[TypedPromotionStep, ...]
    rollback_bundle: RollbackManifest
    checksums: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    signatures: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    created_at: UtcDatetime

    @model_validator(mode="after")
    def forbid_release_steps(self) -> PromotionBundle:
        forbidden = {"merge", "tag", "publish", "release"}
        text = " ".join(step.operation for step in self.machine_executable_typed_steps).lower()
        if any(word in text for word in forbidden):
            raise ValueError(
                "runtime promotion bundle cannot execute merge, tag, publish, or release"
            )
        return self


class PromotionReceipt(HashedExperienceContract):
    promotion_id: UUID
    experiment_id: UUID
    candidate_id: UUID
    promotion_bundle_id: UUID
    approval_reference: Sha256Hex
    target_authority: NonEmptyStr
    pre_promotion_revision: NonEmptyStr
    post_promotion_revision: NonEmptyStr
    performed_by: NonEmptyStr
    performed_at: UtcDatetime
    verification_result: Literal["passed", "failed"]
    artifact_refs: tuple[Sha256Hex, ...]


class RollbackReceipt(HashedExperienceContract):
    rollback_id: UUID
    experiment_id: UUID
    promotion_reference: Sha256Hex
    rollback_manifest_hash: Sha256Hex
    started_at: UtcDatetime
    completed_at: UtcDatetime
    performed_by: NonEmptyStr
    result: Literal["passed", "failed"]
    restored_revision: NonEmptyStr
    verification_evidence: Sha256Hex
    artifact_refs: tuple[Sha256Hex, ...]


class ChangeSurfaceRegistration(HashedExperienceContract):
    proposal_type: NonEmptyStr
    tier: ChangeSurfaceTier
    adapter: NonEmptyStr
    verifier_capabilities: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    isolation_profile: NonEmptyStr
    promotion_mode: PromotionMode
    allowed_files: tuple[NonEmptyStr, ...] = ()
    allowed_configuration_keys: tuple[NonEmptyStr, ...] = ()
    allowed_tools: tuple[NonEmptyStr, ...] = ()


class ChangeAccessRecord(HashedExperienceContract):
    access_id: UUID
    experiment_id: UUID
    access_type: ChangeAccessType
    actor: NonEmptyStr
    authority: NonEmptyStr
    exact_revision: int = Field(gt=0)
    reason: NonEmptyStr
    created_at: UtcDatetime


class ChangeRunManifest(HashedExperienceContract):
    run_manifest_id: UUID
    experiment_id: UUID
    experiment_revision: int = Field(gt=0)
    proposal_hash: Sha256Hex
    baseline_commit: GitCommitHex
    isolation_hash: Sha256Hex
    candidate_hash: Sha256Hex | None = None
    matrix_hash: Sha256Hex | None = None
    assessment_hash: Sha256Hex | None = None
    active_checkout_mutations: Literal[0] = 0
    active_database_writes: Literal[0] = 0
    runtime_release_operations: Literal[0] = 0
    created_at: UtcDatetime


class ChangeVerificationFinding(HashedExperienceContract):
    capability_id: NonEmptyStr
    passed: bool
    reason: NonEmptyStr
    evidence_hash: Sha256Hex


class ChangeVerifierBundle(HashedExperienceContract):
    subject_hash: Sha256Hex
    findings: Annotated[tuple[ChangeVerificationFinding, ...], Field(min_length=1)]
    passed: bool
    registry_hash: Sha256Hex
    created_at: UtcDatetime

    @model_validator(mode="after")
    def aggregate(self) -> ChangeVerifierBundle:
        if self.passed != all(item.passed for item in self.findings):
            raise ValueError("change verifier aggregate does not match findings")
        return self


PUBLIC_CHANGE_CONTRACTS = (
    ChangeResourceBudget,
    ActiveStateProtectionSnapshot,
    ChangeExperiment,
    ChangeExperimentRevision,
    ChangeIsolationManifest,
    ChangeOperation,
    ChangeImplementationPlan,
    DependencyDelta,
    ChangeCandidate,
    EvaluationGate,
    EvaluationMatrix,
    EvaluationCaseResult,
    EvaluationRun,
    MeasuredBenefit,
    RegressionComparison,
    PromotionAssessment,
    PromotionReview,
    TypedPromotionStep,
    RollbackManifest,
    PromotionBundle,
    PromotionReceipt,
    RollbackReceipt,
    ChangeSurfaceRegistration,
    ChangeAccessRecord,
    ChangeRunManifest,
    ChangeVerificationFinding,
    ChangeVerifierBundle,
)
