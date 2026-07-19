"""Immutable contracts for governed procedural skills."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, JsonValue, NonEmptyStr, Sha256Hex, TokenUsage, UtcDatetime
from .context import ContextBundleReference
from .memory import MemorySensitivity


class SkillContract(ImmutableContractModel):
    """Contract with canonical serialization and hashing."""

    def canonical_json(self, *, exclude: set[str] | None = None) -> str:
        return json.dumps(
            self.model_dump(mode="json", exclude=exclude or set()),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def canonical_hash(self, *, exclude: set[str] | None = None) -> str:
        return sha256(self.canonical_json(exclude=exclude).encode()).hexdigest()


class SkillStatus(StrEnum):
    DRAFT = "draft"
    STAGED = "staged"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class SkillScopeType(StrEnum):
    GLOBAL = "global"
    PROJECT = "project"
    REPOSITORY = "repository"
    DOMAIN = "domain"
    PROVIDER = "provider"


class SkillCreatorType(StrEnum):
    OPERATOR = "operator"
    USER = "user"
    IMPORT_SERVICE = "import_service"
    SYSTEM = "system"
    PROVIDER = "provider"


class SkillSourceType(StrEnum):
    MANUAL = "manual"
    IMPORTED_PACKAGE = "imported_package"
    REPOSITORY = "repository"
    ARTIFACT = "artifact"


class SkillRequirementType(StrEnum):
    TOOL = "tool"
    VERIFIER = "verifier"
    PROVIDER = "provider"
    CONTEXT = "context"
    APPROVAL = "approval"
    ARTIFACT = "artifact"


class SkillPreconditionType(StrEnum):
    PROBLEM_DOMAIN_MATCH = "problem_domain_match"
    PROBLEM_SIGNATURE_MATCH = "problem_signature_match"
    REPOSITORY_PROFILE_MATCH = "repository_profile_match"
    ARTIFACT_PRESENCE = "artifact_presence"
    TOOL_CAPABILITY = "tool_capability"
    VERIFIER_CAPABILITY = "verifier_capability"
    PROVIDER_CAPABILITY = "provider_capability"
    SCOPE_MATCH = "scope_match"
    RISK_CEILING = "risk_ceiling"
    EXPLICIT_PERMISSION = "explicit_permission"
    FEATURE_FLAG = "feature_flag"


class SkillStepType(StrEnum):
    CONTROLLER_STEP_TEMPLATE = "controller_step_template"
    PROVIDER_ACTION_TEMPLATE = "provider_action_template"
    TOOL_ACTION = "tool_action"
    VERIFICATION_ACTION = "verification_action"
    APPROVAL_POINT = "approval_point"
    CLARIFICATION_ACTION = "clarification_action"
    CONTEXT_BUILD = "context_build"
    ARTIFACT_TRANSFORM = "artifact_transform"
    DETERMINISTIC_BRANCH = "deterministic_branch"


class SkillFailurePolicyType(StrEnum):
    FAIL_IMMEDIATELY = "fail_immediately"
    RETURN_TO_CONTROLLER_REPAIR = "return_to_controller_repair"
    REQUEST_CLARIFICATION = "request_clarification"
    REQUEST_MANUAL_APPROVAL = "request_manual_approval"
    INVOKE_FALLBACK_SKILL = "invoke_fallback_skill"
    MARK_UNSUITABLE = "mark_unsuitable"


class SkillExecutionStatus(StrEnum):
    PREPARING = "preparing"
    RUNNING = "running"
    WAITING = "waiting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNVERIFIABLE = "unverifiable"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SkillApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    INAPPLICABLE = "inapplicable"
    REQUIRES_PERMISSION = "requires_permission"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"


class SkillSelectionReason(StrEnum):
    EXACT_SIGNATURE = "exact_signature"
    SCOPE_SPECIFICITY = "scope_specificity"
    VERIFIED_STATISTICS = "verified_statistics"
    CANONICAL_TIE_BREAK = "canonical_tie_break"


class SkillExclusionReason(StrEnum):
    STATUS = "status"
    SCOPE = "scope"
    SENSITIVITY = "sensitivity"
    PRECONDITION = "precondition"
    MISSING_REQUIREMENT = "missing_requirement"
    PERMISSION_REQUIRED = "permission_required"
    INVALID_PACKAGE = "invalid_package"
    FALLBACK_INVALID = "fallback_invalid"


class SkillPackageFileType(StrEnum):
    INSTRUCTIONS = "instructions"
    METADATA = "metadata"
    RESOURCE = "resource"
    TEMPLATE = "template"
    SCRIPT = "script"
    TEST = "test"


class SkillAccessType(StrEnum):
    REGISTRY_QUERY = "registry_query"
    CONTEXT_RETRIEVAL = "context_retrieval"
    SUMMARY_HYDRATION = "summary_hydration"
    FULL_HYDRATION = "full_hydration"
    RESOURCE_HYDRATION = "resource_hydration"
    SELECTION = "selection"
    EXECUTION = "execution"
    EXPORT = "export"


class SkillPromotionOutcome(StrEnum):
    VERIFY = "verify"
    REMAIN_STAGED = "remain_staged"
    RETURN_TO_DRAFT = "return_to_draft"
    REQUIRES_REVIEW = "requires_review"
    REJECT = "reject"
    VERIFICATION_ERROR = "verification_error"


class SkillActor(SkillContract):
    creator_type: SkillCreatorType
    creator_id: NonEmptyStr


class SkillScope(SkillContract):
    scope_type: SkillScopeType
    scope_id: NonEmptyStr

    @field_validator("scope_id")
    @classmethod
    def reject_host_path(cls, value: str) -> str:
        if (
            PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
            or re.match(r"^[A-Za-z]:[\\/]", value)
        ):
            raise ValueError("skill scope must not contain a raw host path")
        return value

    @model_validator(mode="after")
    def global_scope_is_explicit(self) -> SkillScope:
        if self.scope_type is SkillScopeType.GLOBAL and self.scope_id != "global":
            raise ValueError("global skill scope requires the literal global scope ID")
        return self


class SkillSourceRef(SkillContract):
    source_type: SkillSourceType
    source_id: NonEmptyStr
    source_revision: NonEmptyStr
    content_hash: Sha256Hex

    @field_validator("source_id", "source_revision")
    @classmethod
    def logical_identity(cls, value: str) -> str:
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError("skill source identity must be logical")
        return value


class SkillProblemSignature(SkillContract):
    problem_domain: NonEmptyStr
    task_type: NonEmptyStr | None = None
    repository_language: NonEmptyStr | None = None
    repository_profile: NonEmptyStr | None = None
    requested_output_type: NonEmptyStr | None = None
    risk_level: NonEmptyStr | None = None
    required_tool_capabilities: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    required_verifier_capabilities: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    relevant_artifact_types: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)


class SkillFieldSpecification(SkillContract):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    json_type: str = Field(pattern=r"^(string|integer|number|boolean|object|array)$")
    required: bool = True
    artifact_media_types: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    requires_evidence: bool = False

    @field_validator("name")
    @classmethod
    def reject_secret_fields(cls, value: str) -> str:
        if any(token in value for token in ("password", "secret", "token", "api_key")):
            raise ValueError("secret-bearing skill fields are prohibited")
        return value


class SkillInputSpecification(SkillContract):
    fields: tuple[SkillFieldSpecification, ...] = Field(default=(), max_length=64)


class SkillOutputSpecification(SkillContract):
    fields: tuple[SkillFieldSpecification, ...] = Field(default=(), max_length=64)


class SkillInputBinding(SkillContract):
    name: NonEmptyStr
    value: JsonValue = None
    artifact: ArtifactRef | None = None

    @model_validator(mode="after")
    def exactly_one_value(self) -> SkillInputBinding:
        if (self.value is None) == (self.artifact is None):
            raise ValueError("input binding requires exactly one value or artifact")
        return self


class SkillOutputBinding(SkillContract):
    name: NonEmptyStr
    value: JsonValue = None
    artifact: ArtifactRef | None = None
    evidence_artifacts: tuple[ArtifactRef, ...] = ()


class SkillPrecondition(SkillContract):
    precondition_id: NonEmptyStr
    precondition_type: SkillPreconditionType
    parameters: dict[str, JsonValue]
    required: bool = True

    @model_validator(mode="after")
    def validate_parameters(self) -> SkillPrecondition:
        required = {
            SkillPreconditionType.PROBLEM_DOMAIN_MATCH: "allowed",
            SkillPreconditionType.PROBLEM_SIGNATURE_MATCH: "signature_hash",
            SkillPreconditionType.REPOSITORY_PROFILE_MATCH: "allowed",
            SkillPreconditionType.ARTIFACT_PRESENCE: "artifact_type",
            SkillPreconditionType.TOOL_CAPABILITY: "capability",
            SkillPreconditionType.VERIFIER_CAPABILITY: "capability",
            SkillPreconditionType.PROVIDER_CAPABILITY: "capability",
            SkillPreconditionType.SCOPE_MATCH: "scope_type",
            SkillPreconditionType.RISK_CEILING: "maximum",
            SkillPreconditionType.EXPLICIT_PERMISSION: "permission",
            SkillPreconditionType.FEATURE_FLAG: "flag",
        }[self.precondition_type]
        if required not in self.parameters:
            raise ValueError(f"{self.precondition_type.value} requires {required}")
        if any(key.startswith("__") for key in self.parameters):
            raise ValueError("private or executable precondition parameters are prohibited")
        return self


class SkillStep(SkillContract):
    step_id: NonEmptyStr
    step_type: SkillStepType
    capability_id: NonEmptyStr
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    mandatory: bool = True

    @model_validator(mode="after")
    def prohibit_direct_authority(self) -> SkillStep:
        serialized = json.dumps(self.parameters, sort_keys=True).casefold()
        forbidden = ("shell", "command", "database_url", "credential", "password", "sudo")
        if any(token in serialized for token in forbidden):
            raise ValueError("skill step contains prohibited direct authority")
        return self


class SkillRequirement(SkillContract):
    requirement_id: NonEmptyStr
    requirement_type: SkillRequirementType
    capability_id: NonEmptyStr
    version_constraint: NonEmptyStr | None = None
    required: bool = True
    permission: NonEmptyStr | None = None


class SkillToolRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.TOOL


class SkillVerifierRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.VERIFIER


class SkillProviderRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.PROVIDER

    @field_validator("capability_id", "version_constraint", "permission")
    @classmethod
    def no_credentials(cls, value: str | None) -> str | None:
        if value and any(token in value.casefold() for token in ("key=", "token=", "password=")):
            raise ValueError("provider requirements cannot contain credentials")
        return value


class SkillContextRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.CONTEXT


class SkillApprovalRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.APPROVAL


class SkillArtifactRequirement(SkillRequirement):
    requirement_type: SkillRequirementType = SkillRequirementType.ARTIFACT


class SkillResourceBudget(SkillContract):
    maximum_steps: int = Field(default=64, ge=1, le=64)
    maximum_provider_calls: int = Field(default=8, ge=0, le=8)
    maximum_tool_calls: int = Field(default=32, ge=0, le=32)
    maximum_context_builds: int = Field(default=8, ge=0, le=8)
    maximum_execution_seconds: int = Field(default=1800, ge=1, le=1800)
    maximum_repairs: int = Field(default=3, ge=0, le=3)
    maximum_context_tokens: int = Field(default=32_768, ge=1, le=1_000_000)


class SkillFallbackReference(SkillContract):
    skill_id: UUID
    revision: int | None = Field(default=None, ge=1)


class SkillFailurePolicy(SkillContract):
    policy_type: SkillFailurePolicyType
    fallback: SkillFallbackReference | None = None
    maximum_fallback_depth: int = Field(default=0, ge=0, le=4)

    @model_validator(mode="after")
    def fallback_shape(self) -> SkillFailurePolicy:
        invoked = self.policy_type is SkillFailurePolicyType.INVOKE_FALLBACK_SKILL
        if invoked != (self.fallback is not None and self.maximum_fallback_depth > 0):
            raise ValueError("fallback policy requires a bounded fallback reference")
        return self


class SkillPackageFile(SkillContract):
    relative_path: NonEmptyStr
    file_type: SkillPackageFileType
    media_type: NonEmptyStr
    size_bytes: int = Field(ge=0, le=2_097_152)
    content_hash: Sha256Hex

    @field_validator("relative_path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or ".git" in path.parts or "\\" in value:
            raise ValueError("unsafe skill package path")
        return path.as_posix()


class SkillPackageManifest(SkillContract):
    format_version: str = Field(default="1", pattern=r"^1$")
    files: Annotated[tuple[SkillPackageFile, ...], Field(min_length=2, max_length=256)]
    total_bytes: int = Field(ge=1, le=16_777_216)
    package_hash: str = ""

    @model_validator(mode="after")
    def validate_and_seal(self) -> SkillPackageManifest:
        paths = [item.relative_path.casefold() for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate normalized skill package path")
        if {item.relative_path for item in self.files}.isdisjoint({"SKILL.md"}) or {
            item.relative_path for item in self.files
        }.isdisjoint({"metadata.yaml"}):
            raise ValueError("skill package requires SKILL.md and metadata.yaml")
        if self.total_bytes != sum(item.size_bytes for item in self.files):
            raise ValueError("skill package total byte count mismatch")
        expected = self.canonical_hash(exclude={"package_hash"})
        if self.package_hash and self.package_hash != expected:
            raise ValueError("skill package hash mismatch")
        object.__setattr__(self, "package_hash", expected)
        return self


class SkillIdentity(SkillContract):
    skill_id: UUID
    canonical_name: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    scope: SkillScope
    created_at: UtcDatetime
    created_by: SkillActor

    @field_validator("canonical_name", mode="before")
    @classmethod
    def canonicalize_name(cls, value: object) -> object:
        return re.sub(r"[^a-z0-9]+", "-", str(value).strip().casefold()).strip("-")


class SkillRevision(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    previous_revision: int | None = Field(default=None, ge=1)
    status: SkillStatus
    display_name: Annotated[str, Field(min_length=1, max_length=256)]
    description: Annotated[str, Field(min_length=1, max_length=4096)]
    purpose: Annotated[str, Field(min_length=1, max_length=4096)]
    domains: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1, max_length=16)]
    problem_signatures: tuple[SkillProblemSignature, ...] = Field(default=(), max_length=32)
    preconditions: tuple[SkillPrecondition, ...] = Field(default=(), max_length=32)
    input_specification: SkillInputSpecification = SkillInputSpecification()
    output_specification: SkillOutputSpecification = SkillOutputSpecification()
    steps: Annotated[tuple[SkillStep, ...], Field(min_length=1, max_length=64)]
    requirements: tuple[SkillRequirement, ...] = Field(default=(), max_length=96)
    failure_policy: SkillFailurePolicy
    resource_budget: SkillResourceBudget
    package_artifact: ArtifactRef
    package_hash: Sha256Hex
    source_refs: Annotated[tuple[SkillSourceRef, ...], Field(min_length=1, max_length=64)]
    sensitivity: MemorySensitivity
    regression_profile: NonEmptyStr
    created_at: UtcDatetime
    created_by: SkillActor
    reason: NonEmptyStr
    content_hash: str = ""

    @model_validator(mode="after")
    def chain_bound_and_seal(self) -> SkillRevision:
        expected_previous = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected_previous:
            raise ValueError("skill revision must reference its immediate predecessor")
        if len({item.step_id for item in self.steps}) != len(self.steps):
            raise ValueError("skill step IDs must be unique")
        if len({item.requirement_id for item in self.requirements}) != len(self.requirements):
            raise ValueError("skill requirement IDs must be unique")
        if len(self.steps) > self.resource_budget.maximum_steps:
            raise ValueError("skill steps exceed the skill resource budget")
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("skill revision hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class SkillItem(SkillContract):
    identity: SkillIdentity
    current_revision: int = Field(ge=1)
    current_status: SkillStatus
    idempotency_key: Sha256Hex


class SkillRegistrySnapshot(SkillContract):
    registry_hash: Sha256Hex
    precondition_registry_hash: Sha256Hex
    context_registry_hash: Sha256Hex
    tool_registry_hash: Sha256Hex
    verifier_registry_hash: Sha256Hex
    provider_registry_hash: Sha256Hex


class SkillApplicabilityInput(SkillContract):
    problem_domain: NonEmptyStr
    task_type: NonEmptyStr | None = None
    repository_language: NonEmptyStr | None = None
    repository_profile: NonEmptyStr | None = None
    requested_output_type: NonEmptyStr | None = None
    risk_level: NonEmptyStr = "low"
    scope: SkillScope
    sensitivity_limit: MemorySensitivity
    available_artifact_types: frozenset[NonEmptyStr] = frozenset()
    tool_capabilities: frozenset[NonEmptyStr] = frozenset()
    verifier_capabilities: frozenset[NonEmptyStr] = frozenset()
    provider_capabilities: frozenset[NonEmptyStr] = frozenset()
    context_capabilities: frozenset[NonEmptyStr] = frozenset()
    permissions: frozenset[NonEmptyStr] = frozenset()
    feature_flags: frozenset[NonEmptyStr] = frozenset()


class SkillPreconditionResult(SkillContract):
    precondition_id: NonEmptyStr
    passed: bool
    reason_code: NonEmptyStr
    evidence_hash: Sha256Hex


class SkillApplicabilityResult(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    status: SkillApplicabilityStatus
    results: tuple[SkillPreconditionResult, ...]
    evaluation_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> SkillApplicabilityResult:
        expected = self.canonical_hash(exclude={"evaluation_hash"})
        if self.evaluation_hash and self.evaluation_hash != expected:
            raise ValueError("skill applicability hash mismatch")
        object.__setattr__(self, "evaluation_hash", expected)
        return self


class SkillSelectionRequest(SkillContract):
    request_id: UUID
    task_run_id: UUID
    applicability_input: SkillApplicabilityInput
    registry_snapshot: SkillRegistrySnapshot
    allowed_statuses: tuple[SkillStatus, ...] = (SkillStatus.VERIFIED,)
    provider_suggestion: UUID | None = None
    maximum_candidates: int = Field(default=32, ge=1, le=200)
    created_at: UtcDatetime


class SkillSelectionCandidate(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    applicability: SkillApplicabilityResult
    specificity_score: int = Field(ge=0)
    scope_score: int = Field(ge=0)
    statistics_score: int = Field(ge=0)
    safety_penalty: int = Field(ge=0)
    estimated_context_tokens: int = Field(ge=0)


class SkillSelectionExclusion(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    reason: SkillExclusionReason
    detail_code: NonEmptyStr


class SkillSelectionDecision(SkillContract):
    request_id: UUID
    selected_skill_id: UUID | None = None
    selected_revision: int | None = Field(default=None, ge=1)
    reason: SkillSelectionReason | None = None
    candidates: tuple[SkillSelectionCandidate, ...]
    exclusions: tuple[SkillSelectionExclusion, ...]
    selection_profile_hash: Sha256Hex
    registry_snapshot: SkillRegistrySnapshot
    decision_hash: str = ""

    @model_validator(mode="after")
    def selected_pair_and_hash(self) -> SkillSelectionDecision:
        if (self.selected_skill_id is None) != (self.selected_revision is None):
            raise ValueError("selected skill identity and revision must be paired")
        expected = self.canonical_hash(exclude={"decision_hash"})
        if self.decision_hash and self.decision_hash != expected:
            raise ValueError("skill selection hash mismatch")
        object.__setattr__(self, "decision_hash", expected)
        return self


class SkillExecutionRequest(SkillContract):
    execution_id: UUID
    skill_id: UUID
    skill_revision: int = Field(ge=1)
    task_run_id: UUID
    problem_reference: UUID
    plan_reference: UUID
    input_bindings: tuple[SkillInputBinding, ...]
    context_bundle_reference: ContextBundleReference | None = None
    controller_budget: SkillResourceBudget
    expected_registry_snapshots: SkillRegistrySnapshot
    requested_by: SkillActor
    package_hash: Sha256Hex
    created_at: UtcDatetime


class SkillExecutionStepResult(SkillContract):
    step_id: NonEmptyStr
    status: SkillExecutionStatus
    output_artifacts: tuple[ArtifactRef, ...] = ()
    provider_call_ids: tuple[UUID, ...] = ()
    tool_call_ids: tuple[UUID, ...] = ()
    verifier_result_ids: tuple[UUID, ...] = ()
    reason: NonEmptyStr | None = None


class SkillExecutionResult(SkillContract):
    execution_id: UUID
    skill_id: UUID
    skill_revision: int = Field(ge=1)
    task_run_id: UUID
    status: SkillExecutionStatus
    step_results: tuple[SkillExecutionStepResult, ...]
    verification_bundle: ArtifactRef | None = None
    acceptance_decision_id: UUID | None = None
    artifacts: tuple[ArtifactRef, ...] = ()
    usage: TokenUsage = TokenUsage()
    warnings: tuple[NonEmptyStr, ...] = ()
    failure: NonEmptyStr | None = None
    fallback_execution_id: UUID | None = None
    started_at: UtcDatetime
    finished_at: UtcDatetime
    result_hash: str = ""

    @model_validator(mode="after")
    def terminal_and_seal(self) -> SkillExecutionResult:
        if self.finished_at < self.started_at:
            raise ValueError("skill execution finishes before it starts")
        if self.status is SkillExecutionStatus.ACCEPTED and self.acceptance_decision_id is None:
            raise ValueError("accepted skill execution requires an acceptance decision")
        expected = self.canonical_hash(exclude={"result_hash"})
        if self.result_hash and self.result_hash != expected:
            raise ValueError("skill execution result hash mismatch")
        object.__setattr__(self, "result_hash", expected)
        return self


class SkillStatistics(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    projection_revision: int = Field(ge=1)
    executions: int = Field(ge=0)
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)
    unverifiable: int = Field(ge=0)
    failed: int = Field(ge=0)
    repairs: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    token_usage: int = Field(ge=0)
    policy_denials: int = Field(ge=0)
    safety_failures: int = Field(ge=0)
    fallback_uses: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    source_execution_ids: tuple[UUID, ...]
    projection_hash: str = ""

    @model_validator(mode="after")
    def counts_and_seal(self) -> SkillStatistics:
        if self.accepted + self.rejected + self.unverifiable + self.failed > self.executions:
            raise ValueError("skill statistic terminal counts exceed executions")
        expected = self.canonical_hash(exclude={"projection_hash"})
        if self.projection_hash and self.projection_hash != expected:
            raise ValueError("skill statistics hash mismatch")
        object.__setattr__(self, "projection_hash", expected)
        return self


class SkillAccessRecord(SkillContract):
    access_id: UUID
    skill_id: UUID
    revision: int = Field(ge=1)
    access_type: SkillAccessType
    task_run_id: UUID | None = None
    context_request_id: UUID | None = None
    query_hash: Sha256Hex | None = None
    scope: SkillScope
    sensitivity: MemorySensitivity
    accessed_at: UtcDatetime


class SkillVerificationSnapshot(SkillContract):
    skill_id: UUID
    revision: int = Field(ge=1)
    package_hash: Sha256Hex
    package_integrity: bool
    package_schema: bool
    path_safety: bool
    package_secrets: bool
    precondition_determinism: bool
    tool_requirements: bool
    verifier_requirements: bool
    provider_requirements: bool
    context_requirements: bool
    execution_conformance: bool
    output_schema: bool
    regression_suite: bool
    no_permission_expansion: bool

    @property
    def passed(self) -> bool:
        values = self.model_dump(exclude={"skill_id", "revision", "package_hash"})
        return all(bool(value) for value in values.values())


class SkillPromotionDecision(SkillContract):
    decision_id: UUID
    skill_id: UUID
    revision: int = Field(ge=1)
    outcome: SkillPromotionOutcome
    verifier_bundle: ArtifactRef
    regression_summary: ArtifactRef
    decided_by: SkillActor
    reason_codes: tuple[NonEmptyStr, ...]
    decided_at: UtcDatetime


PUBLIC_SKILL_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    SkillActor,
    SkillScope,
    SkillSourceRef,
    SkillProblemSignature,
    SkillFieldSpecification,
    SkillInputSpecification,
    SkillOutputSpecification,
    SkillInputBinding,
    SkillOutputBinding,
    SkillPrecondition,
    SkillStep,
    SkillRequirement,
    SkillToolRequirement,
    SkillVerifierRequirement,
    SkillProviderRequirement,
    SkillContextRequirement,
    SkillApprovalRequirement,
    SkillArtifactRequirement,
    SkillResourceBudget,
    SkillFallbackReference,
    SkillFailurePolicy,
    SkillPackageFile,
    SkillPackageManifest,
    SkillIdentity,
    SkillRevision,
    SkillItem,
    SkillRegistrySnapshot,
    SkillApplicabilityInput,
    SkillPreconditionResult,
    SkillApplicabilityResult,
    SkillSelectionRequest,
    SkillSelectionCandidate,
    SkillSelectionExclusion,
    SkillSelectionDecision,
    SkillExecutionRequest,
    SkillExecutionStepResult,
    SkillExecutionResult,
    SkillStatistics,
    SkillAccessRecord,
    SkillVerificationSnapshot,
    SkillPromotionDecision,
)
