"""Immutable contracts for governed, proposal-only harness improvements."""

from __future__ import annotations

import re
from decimal import Decimal
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import ExperienceContract, HashedExperienceContract
from .weakness import (
    ImpactScore,
    WeaknessBenchmarkCandidate,
    WeaknessEvidencePackage,
    WeaknessQueueEntry,
    WeaknessReplayCandidate,
    WeaknessReproductionAssessment,
    WeaknessRevision,
    WeaknessStatus,
)


class ProposalStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    VALIDATED = "validated"
    STAGED_FOR_REVIEW = "staged_for_review"
    APPROVED_FOR_EXPERIMENT = "approved_for_experiment"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class HarnessProposalType(StrEnum):
    PROMPT_TEMPLATE_CHANGE = "prompt_template_change"
    CONTEXT_PROFILE_CHANGE = "context_profile_change"
    RETRIEVAL_POLICY_CHANGE = "retrieval_policy_change"
    MEMORY_POLICY_CHANGE = "memory_policy_change"
    SKILL_CHANGE = "skill_change"
    STRATEGY_CHANGE = "strategy_change"
    ROUTING_POLICY_CHANGE = "routing_policy_change"
    TOOL_DEFINITION_CHANGE = "tool_definition_change"
    VERIFIER_CHANGE = "verifier_change"
    WORKFLOW_CHANGE = "workflow_change"
    RETRY_POLICY_CHANGE = "retry_policy_change"
    BENCHMARK_CHANGE = "benchmark_change"
    CONFIGURATION_CHANGE = "configuration_change"
    SOURCE_CODE_CHANGE = "source_code_change"
    DOCUMENTATION_CHANGE = "documentation_change"


class ProposalRiskLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ProposalReviewDecision(StrEnum):
    APPROVE_FOR_EXPERIMENT = "approve_for_experiment"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ProposalGenerationMode(StrEnum):
    DETERMINISTIC = "deterministic"
    PROVIDER_ASSISTED = "provider_assisted"


class ExpectedDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    MAINTAIN_WITH_LOWER_COST = "maintain_with_lower_cost"
    ELIMINATE_FAILURE = "eliminate_failure"


class RollbackType(StrEnum):
    DECLARATIVE_REVISION = "declarative_revision"
    CONFIGURATION_RESTORE = "configuration_restore"
    REPOSITORY_REVERT_PLAN = "repository_revert_plan"
    DATABASE_RESTORE_PLAN = "database_restore_plan"
    ARTIFACT_RESTORE_PLAN = "artifact_restore_plan"
    MANUAL_ONLY = "manual_only"


class ChangeSurfaceTier(StrEnum):
    TIER_0 = "tier_0"
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class ProposalVerifierStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class ProposalAccessType(StrEnum):
    READ = "read"
    EXPORT = "export"
    REVIEW = "review"
    QUEUE = "queue"


class EligibilityReason(StrEnum):
    ELIGIBLE_CONFIRMED = "eligible_confirmed"
    ELIGIBLE_POLICY_CANDIDATE = "eligible_policy_candidate"
    CANDIDATE_DISABLED = "candidate_disabled"
    STATUS_INELIGIBLE = "status_ineligible"
    STALE_REVISION = "stale_revision"
    MISSING_EVIDENCE = "missing_evidence"
    MISSING_IMPACT = "missing_impact"
    SOURCE_INTEGRITY = "source_integrity"
    DUPLICATE_ACTIVE_SIGNATURE = "duplicate_active_signature"


def _safe_scope(value: str) -> str:
    if (
        not value
        or "*" in value
        or ".." in PurePosixPath(value).parts
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
        or re.match(r"^[A-Za-z]:[\\/]", value)
    ):
        raise ValueError("proposal scope must be explicit, relative, and wildcard-free")
    return value


class ArtifactRevisionOperation(HashedExperienceContract):
    operation_type: Literal["artifact_revision"] = "artifact_revision"
    target_identity: NonEmptyStr
    target_revision: NonEmptyStr
    proposed_artifact_hash: Sha256Hex


class ConfigurationValueOperation(HashedExperienceContract):
    operation_type: Literal["configuration_value"] = "configuration_value"
    target_identity: NonEmptyStr
    target_revision: NonEmptyStr
    configuration_key: NonEmptyStr
    proposed_value_artifact_hash: Sha256Hex

    _validate_key = field_validator("configuration_key")(_safe_scope)


class RepositoryFileOperation(HashedExperienceContract):
    operation_type: Literal["repository_file"] = "repository_file"
    target_identity: NonEmptyStr
    target_revision: NonEmptyStr
    allowed_files: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    description_artifact_hash: Sha256Hex

    @field_validator("allowed_files")
    @classmethod
    def explicit_files(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({_safe_scope(item) for item in value}))


TypedProposalOperation = Annotated[
    ArtifactRevisionOperation | ConfigurationValueOperation | RepositoryFileOperation,
    Field(discriminator="operation_type"),
]


class HarnessProposalIdentity(HashedExperienceContract):
    proposal_id: UUID
    canonical_name: NonEmptyStr
    proposal_type: HarnessProposalType
    scope: NonEmptyStr
    created_at: UtcDatetime
    created_by: NonEmptyStr
    schema_version: int = Field(default=1, gt=0)


class ProposalSourceSnapshot(ExperienceContract):
    proposal_id: UUID
    weakness_id: UUID
    weakness_revision: int = Field(gt=0)
    weakness_status: WeaknessStatus
    weakness_record: WeaknessRevision
    weakness_queue_entry: WeaknessQueueEntry
    weakness_evidence_package: WeaknessEvidencePackage
    impact_score: ImpactScore
    reproduction_assessment: WeaknessReproductionAssessment
    related_benchmark_candidates: tuple[WeaknessBenchmarkCandidate, ...] = ()
    related_replay_candidates: tuple[WeaknessReplayCandidate, ...] = ()
    source_hashes: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    registry_snapshots: dict[NonEmptyStr, Sha256Hex]
    policy_snapshot: Sha256Hex
    created_at: UtcDatetime
    snapshot_hash: str = ""

    @model_validator(mode="after")
    def seal_snapshot(self) -> ProposalSourceSnapshot:
        if self.weakness_id != self.weakness_record.weakness_id:
            raise ValueError("proposal source weakness identity mismatch")
        if self.weakness_revision != self.weakness_record.revision:
            raise ValueError("proposal source weakness revision mismatch")
        if self.weakness_queue_entry.weakness_revision != self.weakness_revision:
            raise ValueError("proposal source queue revision mismatch")
        expected = self.canonical_hash(exclude={"snapshot_hash"})
        if self.snapshot_hash and self.snapshot_hash != expected:
            raise ValueError("proposal source snapshot hash mismatch")
        object.__setattr__(self, "snapshot_hash", expected)
        return self

    @property
    def content_hash(self) -> str:
        return self.snapshot_hash


class ChangeSpecification(HashedExperienceContract):
    change_surface: NonEmptyStr
    change_surface_tier: ChangeSurfaceTier
    current_identity: NonEmptyStr
    current_revision: NonEmptyStr
    proposed_operation: TypedProposalOperation
    proposed_schema: Sha256Hex
    proposed_body_artifact: Sha256Hex
    allowed_files: tuple[NonEmptyStr, ...] = ()
    allowed_configuration_keys: tuple[NonEmptyStr, ...] = ()
    allowed_registry_targets: tuple[NonEmptyStr, ...] = ()
    forbidden_surfaces: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    expected_artifacts: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    compatibility_requirements: tuple[NonEmptyStr, ...] = ()

    @field_validator(
        "allowed_files",
        "allowed_configuration_keys",
        "allowed_registry_targets",
    )
    @classmethod
    def explicit_scope(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({_safe_scope(item) for item in value}))


class ExpectedBenefit(HashedExperienceContract):
    target_metrics: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    baseline_values: dict[NonEmptyStr, Decimal]
    expected_direction: ExpectedDirection
    minimum_material_improvement: Decimal = Field(gt=0)
    applicable_task_signatures: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    limitations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    hypothesis_only: Literal[True] = True


class ProposalRiskAssessment(HashedExperienceContract):
    risk_level: ProposalRiskLevel
    blast_radius: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    affected_authorities: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    affected_tasks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    affected_data: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    security_risks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    privacy_risks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    compatibility_risks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    performance_risks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    recovery_risks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    unknowns: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    required_approvals: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    change_surface_tier: ChangeSurfaceTier


class ProposalValidationPlan(HashedExperienceContract):
    target_benchmarks: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    historical_regression_manifests: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    unrelated_domain_manifests: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    security_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    policy_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    migration_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    dependency_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    performance_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    cost_latency_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    backup_restore_gates: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    acceptance_thresholds: dict[NonEmptyStr, Decimal]
    failure_conditions: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    required_verifiers: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    required_artifacts: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]


class RollbackOperation(HashedExperienceContract):
    operation_type: Literal[
        "restore_revision", "restore_configuration", "restore_artifact", "manual_restore"
    ]
    target_identity: NonEmptyStr
    baseline_reference: NonEmptyStr


class ProposalRollbackPlan(HashedExperienceContract):
    rollback_type: RollbackType
    baseline_references: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    state_snapshot_requirements: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    artifact_requirements: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    rollback_commands_as_typed_operations: Annotated[
        tuple[RollbackOperation, ...], Field(min_length=1)
    ]
    verification_steps: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    maximum_rollback_time: int = Field(gt=0)
    manual_steps: tuple[NonEmptyStr, ...]
    limitations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]


class ProposalAlternative(HashedExperienceContract):
    alternative_id: UUID
    kind: NonEmptyStr
    summary: NonEmptyStr
    change_surface: NonEmptyStr
    expected_tradeoffs: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    required_dependencies: tuple[NonEmptyStr, ...]
    validation_delta: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    rollback_delta: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    risk_delta: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    source_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]


class MinimalityAssessment(HashedExperienceContract):
    primary_weakness_signature: Sha256Hex
    included_surfaces: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    excluded_surfaces: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    required_compatibility_changes: tuple[NonEmptyStr, ...]
    optional_changes_split_out: tuple[NonEmptyStr, ...]
    is_effect_isolatable: bool
    is_exact_rollback_possible: bool
    omnibus_reasons: tuple[NonEmptyStr, ...]
    result: Literal["passed", "failed"]

    @model_validator(mode="after")
    def consistent_result(self) -> MinimalityAssessment:
        passed = (
            len(self.included_surfaces) == 1
            and not self.omnibus_reasons
            and self.is_effect_isolatable
            and self.is_exact_rollback_possible
        )
        if (self.result == "passed") != passed:
            raise ValueError("minimality result does not match its evidence")
        return self


class ProposalVerifierFinding(HashedExperienceContract):
    capability_id: NonEmptyStr
    verifier_revision: int = Field(default=1, gt=0)
    status: ProposalVerifierStatus
    severity: Literal["info", "warning", "error"]
    reason_code: NonEmptyStr
    input_hash: Sha256Hex
    limitations: tuple[NonEmptyStr, ...] = ()


class ProposalVerifierBundle(HashedExperienceContract):
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    input_hash: Sha256Hex
    findings: Annotated[tuple[ProposalVerifierFinding, ...], Field(min_length=1)]
    status: ProposalVerifierStatus
    verifier_registry_hash: Sha256Hex
    created_at: UtcDatetime


class HarnessProposalRevision(HashedExperienceContract):
    proposal_id: UUID
    revision: int = Field(gt=0)
    previous_revision: int | None = Field(default=None, gt=0)
    status: ProposalStatus
    generation_mode: ProposalGenerationMode
    proposal_signature: Sha256Hex
    source_snapshot: ProposalSourceSnapshot
    change_specification: ChangeSpecification
    expected_benefit: ExpectedBenefit
    risk_assessment: ProposalRiskAssessment
    validation_plan: ProposalValidationPlan
    rollback_plan: ProposalRollbackPlan
    alternatives: Annotated[tuple[ProposalAlternative, ...], Field(min_length=2)]
    minimality_assessment: MinimalityAssessment
    limitations: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    artifact_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1)]
    verifier_bundle: ProposalVerifierBundle | None = None
    created_at: UtcDatetime
    created_by: NonEmptyStr
    reason: NonEmptyStr
    schema_version: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def validate_revision_chain(self) -> HarnessProposalRevision:
        if self.revision == 1 and self.previous_revision is not None:
            raise ValueError("initial proposal revision cannot have a predecessor")
        if self.revision > 1 and self.previous_revision != self.revision - 1:
            raise ValueError("proposal revisions must be contiguous")
        if self.status in {
            ProposalStatus.VALIDATED,
            ProposalStatus.STAGED_FOR_REVIEW,
            ProposalStatus.APPROVED_FOR_EXPERIMENT,
        } and (
            self.verifier_bundle is None
            or self.verifier_bundle.status is not ProposalVerifierStatus.PASSED
        ):
            raise ValueError("verified proposal state requires a passing verifier bundle")
        return self


class ProposalReview(HashedExperienceContract):
    review_id: UUID
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    reviewer_identity: NonEmptyStr
    reviewer_authority: NonEmptyStr
    review_decision: ProposalReviewDecision
    rationale: NonEmptyStr
    required_changes: tuple[NonEmptyStr, ...]
    policy_snapshot_hash: Sha256Hex
    verifier_bundle_hash: Sha256Hex
    proposal_content_hash: Sha256Hex
    created_at: UtcDatetime

    @field_validator("reviewer_identity", "reviewer_authority")
    @classmethod
    def reject_provider_review(cls, value: str) -> str:
        if value.lower().startswith(("provider", "model")):
            raise ValueError("provider actors cannot review proposals")
        return value


class ProposalQueueEntry(HashedExperienceContract):
    queue_entry_id: UUID
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    proposal_content_hash: Sha256Hex
    proposal_status: ProposalStatus
    blocked_by_dependency: bool
    operator_priority: int = Field(ge=0, le=100)
    weakness_priority: int = Field(ge=0, le=100)
    evidence_confidence: Decimal = Field(ge=0, le=1)
    risk_rank: int = Field(ge=0, le=3)
    expected_value_rank: int = Field(ge=0, le=100)
    experiment_cost_rank: int = Field(ge=0, le=100)
    blast_radius_rank: int = Field(ge=0, le=100)
    rollback_readiness_rank: int = Field(ge=0, le=100)
    dependency_count: int = Field(ge=0)
    canonical_name: NonEmptyStr
    active: bool = True
    created_at: UtcDatetime


class ProposalQueueSnapshot(HashedExperienceContract):
    snapshot_id: UUID
    entries: tuple[ProposalQueueEntry, ...]
    policy_hash: Sha256Hex
    created_at: UtcDatetime


class ProposalStatistics(HashedExperienceContract):
    proposals_by_type: dict[HarnessProposalType, int]
    proposals_by_status: dict[ProposalStatus, int]
    proposals_by_risk: dict[ProposalRiskLevel, int]
    proposals_by_tier: dict[ChangeSurfaceTier, int]
    review_outcomes: dict[ProposalReviewDecision, int]
    verifier_failure_reasons: dict[NonEmptyStr, int]
    provider_fallback_count: int = Field(ge=0)


class ProviderProposalDraft(HashedExperienceContract):
    proposal_type: HarnessProposalType
    summary: NonEmptyStr
    proposed_body: NonEmptyStr
    rationale: NonEmptyStr
    alternative_drafts: tuple[NonEmptyStr, ...]
    affected_component_hints: tuple[NonEmptyStr, ...]
    validation_rationale: NonEmptyStr
    rollback_rationale: NonEmptyStr
    limitations: tuple[NonEmptyStr, ...]
    cited_host_source_ref_ids: tuple[NonEmptyStr, ...]


class ProposalEligibilityResult(HashedExperienceContract):
    eligible: bool
    reason: EligibilityReason
    policy_snapshot_hash: Sha256Hex
    source_hashes: tuple[Sha256Hex, ...]


class ProposalTypeRegistration(HashedExperienceContract):
    proposal_type: HarnessProposalType
    supported_weakness_types: tuple[NonEmptyStr, ...]
    change_surface_tier: ChangeSurfaceTier
    template_id: NonEmptyStr
    template_version: int = Field(gt=0)
    operation_type: Literal["artifact_revision", "configuration_value", "repository_file"]
    allowed_target_identity_kinds: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    mandatory_verifier_capabilities: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    mandatory_validation_sections: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    mandatory_rollback_sections: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    provider_assistance_permitted: bool
    manual_review_required: Literal[True] = True
    dependency_requirements: tuple[NonEmptyStr, ...] = ()
    license_requirements: tuple[NonEmptyStr, ...] = ()


class ProposalAccessRecord(HashedExperienceContract):
    access_id: UUID
    access_type: ProposalAccessType
    actor_id: NonEmptyStr
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    proposal_content_hash: Sha256Hex
    reason: NonEmptyStr
    accessed_at: UtcDatetime


class ProposalRunManifest(HashedExperienceContract):
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    source_snapshot_hash: Sha256Hex
    registry_hash: Sha256Hex
    policy_hash: Sha256Hex
    proposal_hash: Sha256Hex
    verifier_bundle_hash: Sha256Hex
    artifact_hashes: tuple[Sha256Hex, ...]
    no_destination_writes: Literal[True] = True
    created_at: UtcDatetime


class ProposalVerificationSubject(HashedExperienceContract):
    subject_type: NonEmptyStr
    proposal_id: UUID
    proposal_revision: int = Field(gt=0)
    subject_hash: Sha256Hex
    bounded_metadata: dict[NonEmptyStr, JsonValue] = Field(default_factory=dict)


PUBLIC_PROPOSAL_CONTRACTS = (
    ArtifactRevisionOperation,
    ConfigurationValueOperation,
    RepositoryFileOperation,
    HarnessProposalIdentity,
    ProposalSourceSnapshot,
    ChangeSpecification,
    ExpectedBenefit,
    ProposalRiskAssessment,
    ProposalValidationPlan,
    RollbackOperation,
    ProposalRollbackPlan,
    ProposalAlternative,
    MinimalityAssessment,
    ProposalVerifierFinding,
    ProposalVerifierBundle,
    HarnessProposalRevision,
    ProposalReview,
    ProposalQueueEntry,
    ProposalQueueSnapshot,
    ProposalStatistics,
    ProviderProposalDraft,
    ProposalEligibilityResult,
    ProposalTypeRegistration,
    ProposalAccessRecord,
    ProposalRunManifest,
    ProposalVerificationSubject,
)
