"""Immutable contracts for governed strategic memory."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, JsonValue, NonEmptyStr, Sha256Hex, TokenUsage, UtcDatetime
from .context import ContextBundleReference
from .execution import ExecutionPlan
from .memory import MemorySensitivity
from .skills import SkillProblemSignature, SkillRegistrySnapshot


class StrategyContract(ImmutableContractModel):
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


class StrategyStatus(StrEnum):
    DRAFT = "draft"
    STAGED = "staged"
    VERIFIED = "verified"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    RETRACTED = "retracted"


class StrategyScopeType(StrEnum):
    GLOBAL = "global"
    PROJECT = "project"
    REPOSITORY = "repository"
    DOMAIN = "domain"


class StrategyCreatorType(StrEnum):
    OPERATOR = "operator"
    USER = "user"
    IMPORT_SERVICE = "import_service"
    SYSTEM = "system"
    PROVIDER = "provider"


class StrategySourceType(StrEnum):
    MANUAL = "manual"
    REPOSITORY = "repository"
    ARTIFACT = "artifact"
    SEMANTIC_CLAIM = "semantic_claim"
    TASK_OUTCOME = "task_outcome"


class StrategyPhaseType(StrEnum):
    CONTEXT = "context"
    SKILL = "skill"
    PROVIDER = "provider"
    TOOL = "tool"
    VERIFICATION = "verification"
    APPROVAL = "approval"
    CLARIFICATION = "clarification"
    ACCEPTANCE = "acceptance"
    REPAIR = "repair"
    TERMINAL = "terminal"


class StrategyBindingType(StrEnum):
    EXACT_SKILL_REVISION = "exact_skill_revision"
    CURRENT_VERIFIED_SKILL = "current_verified_skill"
    SKILL_SELECTION_QUERY = "skill_selection_query"
    PREFERRED_SKILL_WITH_FALLBACKS = "preferred_skill_with_fallbacks"


class StrategyEdgeType(StrEnum):
    APPLIES_TO_PROBLEM_CLASS = "applies_to_problem_class"
    USES_SKILL = "uses_skill"
    ALLOWS_FALLBACK_SKILL = "allows_fallback_skill"
    USES_TOOL = "uses_tool"
    USES_MODEL_ROLE = "uses_model_role"
    REQUIRES_VERIFIER = "requires_verifier"
    USES_CONTEXT_PROFILE = "uses_context_profile"
    HAS_PHASE = "has_phase"
    PHASE_PRECEDES = "phase_precedes"
    PHASE_BRANCHES_TO = "phase_branches_to"
    FALLBACK_TO = "fallback_to"
    SPECIALIZES = "specializes"
    GENERALIZES = "generalizes"
    SUPERSEDES = "supersedes"
    DERIVED_FROM = "derived_from"
    CORRECTS = "corrects"
    FAILED_WITH = "failed_with"
    SUCCEEDED_WITH = "succeeded_with"
    OBSERVED_IN = "observed_in"
    PRODUCED_OUTCOME = "produced_outcome"


class StrategyTargetType(StrEnum):
    STRATEGY_REVISION = "strategy_revision"
    PROBLEM_CLASS = "problem_class"
    FAILURE_MODE = "failure_mode"
    PHASE = "phase"
    SKILL_REVISION = "skill_revision"
    TOOL = "tool"
    MODEL_ROLE = "model_role"
    VERIFIER = "verifier"
    CONTEXT_PROFILE = "context_profile"
    TASK_RUN = "task_run"
    CONTROLLER_PLAN = "controller_plan"
    CONTEXT_BUNDLE = "context_bundle"
    CORRECTION_EVENT = "correction_event"
    ACCEPTANCE_DECISION = "acceptance_decision"
    OUTCOME = "outcome"
    ARTIFACT = "artifact"
    SEMANTIC_CLAIM_REVISION = "semantic_claim_revision"


class StrategyApplicabilityConditionType(StrEnum):
    PROBLEM_CLASS_MATCH = "problem_class_match"
    PROBLEM_SIGNATURE_MATCH = "problem_signature_match"
    REPOSITORY_PROFILE_MATCH = "repository_profile_match"
    RISK_RANGE = "risk_range"
    REQUIRED_OUTPUT = "required_output"
    AVAILABLE_SKILL = "available_skill"
    AVAILABLE_TOOL = "available_tool"
    AVAILABLE_VERIFIER = "available_verifier"
    PROVIDER_ROLE_AVAILABLE = "provider_role_available"
    CONTEXT_PROFILE_AVAILABLE = "context_profile_available"
    EXPLICIT_PERMISSION = "explicit_permission"
    FEATURE_FLAG = "feature_flag"


class StrategyApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    INAPPLICABLE = "inapplicable"
    REQUIRES_APPROVAL = "requires_approval"
    UNAVAILABLE = "unavailable"
    INSUFFICIENTLY_MEASURED = "insufficiently_measured"
    INVALID = "invalid"


class StrategySelectionStatus(StrEnum):
    SELECTED = "selected"
    NO_APPLICABLE_STRATEGY = "no_applicable_strategy"
    REQUIRES_APPROVAL = "requires_approval"
    INVALID = "invalid"


class StrategyExecutionStatus(StrEnum):
    PREPARING = "preparing"
    RUNNING = "running"
    WAITING = "waiting"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNVERIFIABLE = "unverifiable"
    FAILED = "failed"
    CANCELLED = "cancelled"
    POLICY_DENIED = "policy_denied"


class StrategyOutcomeStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNVERIFIABLE = "unverifiable"
    CANCELLED = "cancelled"
    POLICY_DENIED = "policy_denied"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


class StrategyExclusionReason(StrEnum):
    STATUS = "status"
    SCOPE = "scope"
    SENSITIVITY = "sensitivity"
    APPLICABILITY = "applicability"
    MISSING_SKILL = "missing_skill"
    MISSING_TOOL = "missing_tool"
    MISSING_VERIFIER = "missing_verifier"
    MISSING_MODEL_ROLE = "missing_model_role"
    MISSING_CONTEXT_PROFILE = "missing_context_profile"
    APPROVAL_REQUIRED = "approval_required"
    OPERATOR_RESTRICTION = "operator_restriction"
    INVALID_GRAPH = "invalid_graph"
    UNSAFE_HISTORY = "unsafe_history"


class StrategyAccessType(StrEnum):
    REGISTRY_QUERY = "registry_query"
    GRAPH_QUERY = "graph_query"
    CONTEXT_RETRIEVAL = "context_retrieval"
    SUMMARY_HYDRATION = "summary_hydration"
    FULL_HYDRATION = "full_hydration"
    SELECTION = "selection"
    COMPARISON = "comparison"
    EXECUTION = "execution"


class StrategyColdStartStatus(StrEnum):
    MEASURED = "measured"
    INSUFFICIENTLY_MEASURED = "insufficiently_measured"
    APPROVED_COLD_START = "approved_cold_start"
    COLD_START_DENIED = "cold_start_denied"


class StrategyBranchSignal(StrEnum):
    VERIFIER_OUTCOME = "verifier_outcome"
    ACCEPTANCE_STATUS = "acceptance_status"
    TOOL_STATUS = "tool_status"
    PROVIDER_STATUS = "provider_status"
    CLARIFICATION_STATUS = "clarification_status"
    REPAIR_COUNT = "repair_count"
    BUDGET_STATE = "budget_state"
    ARTIFACT_PROPERTY = "artifact_property"


class StrategyPromotionOutcome(StrEnum):
    VERIFY = "verify"
    REMAIN_STAGED = "remain_staged"
    RETURN_TO_DRAFT = "return_to_draft"
    REQUIRES_REVIEW = "requires_review"
    REJECT = "reject"
    VERIFICATION_ERROR = "verification_error"


class StrategyActor(StrategyContract):
    creator_type: StrategyCreatorType
    creator_id: NonEmptyStr


class StrategyScope(StrategyContract):
    scope_type: StrategyScopeType
    scope_id: NonEmptyStr

    @field_validator("scope_id")
    @classmethod
    def reject_host_path(cls, value: str) -> str:
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError("strategy scope must not contain a raw host path")
        return value

    @model_validator(mode="after")
    def global_scope_is_explicit(self) -> StrategyScope:
        if self.scope_type is StrategyScopeType.GLOBAL and self.scope_id != "global":
            raise ValueError("global strategy scope requires the literal global scope ID")
        return self


class StrategySourceRef(StrategyContract):
    source_type: StrategySourceType
    source_id: NonEmptyStr
    source_revision: NonEmptyStr
    content_hash: Sha256Hex

    @field_validator("source_id", "source_revision")
    @classmethod
    def logical_identity(cls, value: str) -> str:
        if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError("strategy source identity must be logical")
        return value


class StrategyTargetReference(StrategyContract):
    target_type: StrategyTargetType
    target_id: NonEmptyStr
    target_revision: NonEmptyStr
    content_hash: Sha256Hex
    scope: StrategyScope | None = None


class ProblemClassDescriptor(StrategyContract):
    problem_class_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
    version: int = Field(ge=1)
    display_name: NonEmptyStr
    description: NonEmptyStr
    problem_domains: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1, max_length=16)]
    problem_signature_constraints: tuple[SkillProblemSignature, ...] = Field(
        default=(), max_length=32
    )
    repository_profile_constraints: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    minimum_risk: NonEmptyStr = "low"
    maximum_risk: NonEmptyStr = "high"
    required_output_types: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    created_at: UtcDatetime
    created_by: StrategyActor
    content_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> ProblemClassDescriptor:
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("problem-class descriptor hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class FailureModeDescriptor(StrategyContract):
    failure_mode_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
    version: int = Field(ge=1)
    display_name: NonEmptyStr
    category: NonEmptyStr
    description: NonEmptyStr
    detection_signals: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    severity: NonEmptyStr
    recoverable: bool
    content_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> FailureModeDescriptor:
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("failure-mode descriptor hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class StrategyApplicabilityCondition(StrategyContract):
    condition_id: NonEmptyStr
    condition_type: StrategyApplicabilityConditionType
    parameters: dict[str, JsonValue]
    required: bool = True

    @model_validator(mode="after")
    def typed_parameters(self) -> StrategyApplicabilityCondition:
        required = {
            StrategyApplicabilityConditionType.PROBLEM_CLASS_MATCH: "problem_class_id",
            StrategyApplicabilityConditionType.PROBLEM_SIGNATURE_MATCH: "signature_hash",
            StrategyApplicabilityConditionType.REPOSITORY_PROFILE_MATCH: "allowed",
            StrategyApplicabilityConditionType.RISK_RANGE: "maximum",
            StrategyApplicabilityConditionType.REQUIRED_OUTPUT: "output_type",
            StrategyApplicabilityConditionType.AVAILABLE_SKILL: "binding_id",
            StrategyApplicabilityConditionType.AVAILABLE_TOOL: "capability_id",
            StrategyApplicabilityConditionType.AVAILABLE_VERIFIER: "capability_id",
            StrategyApplicabilityConditionType.PROVIDER_ROLE_AVAILABLE: "role_id",
            StrategyApplicabilityConditionType.CONTEXT_PROFILE_AVAILABLE: "profile_id",
            StrategyApplicabilityConditionType.EXPLICIT_PERMISSION: "permission",
            StrategyApplicabilityConditionType.FEATURE_FLAG: "flag",
        }[self.condition_type]
        if required not in self.parameters:
            raise ValueError(f"{self.condition_type.value} requires {required}")
        serialized = json.dumps(self.parameters, sort_keys=True).casefold()
        if any(token in serialized for token in ("__", "eval", "lambda", "credential")):
            raise ValueError("strategy applicability contains executable or credential data")
        return self


class StrategyApplicabilityProfile(StrategyContract):
    conditions: tuple[StrategyApplicabilityCondition, ...] = Field(default=(), max_length=64)

    @model_validator(mode="after")
    def unique_conditions(self) -> StrategyApplicabilityProfile:
        if len({item.condition_id for item in self.conditions}) != len(self.conditions):
            raise ValueError("strategy applicability condition IDs must be unique")
        return self


class StrategyApplicabilityEvidence(StrategyContract):
    condition_id: NonEmptyStr
    passed: bool
    reason_code: NonEmptyStr
    evidence_hash: Sha256Hex


class StrategyApplicabilityInput(StrategyContract):
    problem_class_id: NonEmptyStr
    problem_signature: SkillProblemSignature
    repository_profile: NonEmptyStr | None = None
    required_output_type: NonEmptyStr | None = None
    risk_level: NonEmptyStr = "low"
    scope: StrategyScope
    sensitivity_limit: MemorySensitivity
    available_skill_bindings: frozenset[NonEmptyStr] = frozenset()
    available_tool_capabilities: frozenset[NonEmptyStr] = frozenset()
    available_verifier_capabilities: frozenset[NonEmptyStr] = frozenset()
    available_model_roles: frozenset[NonEmptyStr] = frozenset()
    available_context_profiles: frozenset[NonEmptyStr] = frozenset()
    permissions: frozenset[NonEmptyStr] = frozenset()
    feature_flags: frozenset[NonEmptyStr] = frozenset()


class StrategyApplicabilityResult(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    status: StrategyApplicabilityStatus
    evidence: tuple[StrategyApplicabilityEvidence, ...]
    evaluation_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> StrategyApplicabilityResult:
        expected = self.canonical_hash(exclude={"evaluation_hash"})
        if self.evaluation_hash and self.evaluation_hash != expected:
            raise ValueError("strategy applicability hash mismatch")
        object.__setattr__(self, "evaluation_hash", expected)
        return self


class StrategyRequirement(StrategyContract):
    requirement_id: NonEmptyStr
    capability_id: NonEmptyStr
    required: bool = True
    permission: NonEmptyStr | None = None


class StrategyModelRoleBinding(StrategyContract):
    role_id: NonEmptyStr
    provider_profile_id: NonEmptyStr
    required_capabilities: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def no_credentials(self) -> StrategyModelRoleBinding:
        serialized = self.canonical_json().casefold()
        if any(token in serialized for token in ("key=", "token=", "password=")):
            raise ValueError("model-role binding cannot contain credentials")
        return self


class StrategyContextProfile(StrategyContract):
    profile_id: NonEmptyStr
    context_purpose: NonEmptyStr
    required_source_types: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    maximum_tokens: int = Field(default=32_768, ge=1, le=1_000_000)


class StrategyBudgetProfile(StrategyContract):
    maximum_steps: int = Field(default=128, ge=1, le=128)
    maximum_provider_calls: int = Field(default=8, ge=0, le=8)
    maximum_tool_calls: int = Field(default=32, ge=0, le=32)
    maximum_context_builds: int = Field(default=8, ge=0, le=8)
    maximum_execution_seconds: int = Field(default=3_600, ge=1, le=3_600)
    maximum_repairs: int = Field(default=3, ge=0, le=3)
    maximum_context_tokens: int = Field(default=32_768, ge=1, le=1_000_000)


class StrategyRepairPolicy(StrategyContract):
    maximum_repairs: int = Field(default=0, ge=0, le=3)
    no_progress_limit: int = Field(default=1, ge=1, le=3)
    require_reverification: bool = True


class StrategyStopCondition(StrategyContract):
    condition_id: NonEmptyStr
    signal: StrategyBranchSignal
    expected_value: JsonValue
    terminal_status: StrategyExecutionStatus


class StrategySkillBinding(StrategyContract):
    binding_id: NonEmptyStr
    binding_type: StrategyBindingType
    skill_id: UUID | None = None
    revision: int | None = Field(default=None, ge=1)
    selection_signature: SkillProblemSignature | None = None
    fallback_references: tuple[tuple[UUID, int | None], ...] = Field(default=(), max_length=16)
    required: bool = True
    input_mapping: dict[str, NonEmptyStr] = Field(default_factory=dict)
    output_mapping: dict[str, NonEmptyStr] = Field(default_factory=dict)

    @model_validator(mode="after")
    def binding_shape(self) -> StrategySkillBinding:
        exact = self.binding_type is StrategyBindingType.EXACT_SKILL_REVISION
        query = self.binding_type is StrategyBindingType.SKILL_SELECTION_QUERY
        if exact and (self.skill_id is None or self.revision is None):
            raise ValueError("exact skill binding requires identity and revision")
        if query and self.selection_signature is None:
            raise ValueError("skill selection binding requires a problem signature")
        if (
            self.binding_type is StrategyBindingType.CURRENT_VERIFIED_SKILL
            and self.skill_id is None
        ):
            raise ValueError("current verified skill binding requires a skill identity")
        if self.binding_type is StrategyBindingType.PREFERRED_SKILL_WITH_FALLBACKS and (
            self.skill_id is None or not self.fallback_references
        ):
            raise ValueError("preferred skill binding requires a skill and fallbacks")
        return self


class StrategyBranchCondition(StrategyContract):
    signal: StrategyBranchSignal
    expected_value: JsonValue


class StrategyBranch(StrategyContract):
    branch_id: NonEmptyStr
    source_phase_id: NonEmptyStr
    target_phase_id: NonEmptyStr
    condition: StrategyBranchCondition
    priority: int = Field(default=0, ge=0, le=100)


class StrategyBranchDecision(StrategyContract):
    branch_id: NonEmptyStr
    source_phase_id: NonEmptyStr
    target_phase_id: NonEmptyStr
    signal: StrategyBranchSignal
    evidence_hash: Sha256Hex
    decided_at: UtcDatetime


class StrategyPhase(StrategyContract):
    phase_id: NonEmptyStr
    sequence: int = Field(ge=1, le=128)
    phase_type: StrategyPhaseType
    display_name: NonEmptyStr
    purpose: NonEmptyStr
    dependencies: tuple[NonEmptyStr, ...] = Field(default=(), max_length=64)
    skill_binding_ids: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    model_role_ids: tuple[NonEmptyStr, ...] = Field(default=(), max_length=16)
    tool_requirements: tuple[StrategyRequirement, ...] = Field(default=(), max_length=32)
    verifier_requirements: tuple[StrategyRequirement, ...] = Field(default=(), max_length=32)
    context_profile_id: NonEmptyStr | None = None
    budget: StrategyBudgetProfile
    approval_requirement: NonEmptyStr | None = None
    completion_signals: tuple[StrategyBranchCondition, ...] = Field(default=(), max_length=16)
    failure_target_phase_id: NonEmptyStr | None = None

    @model_validator(mode="after")
    def phase_is_declarative(self) -> StrategyPhase:
        if self.phase_id in self.dependencies:
            raise ValueError("strategy phase cannot depend on itself")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("strategy phase dependencies must be unique")
        return self


class StrategyIdentity(StrategyContract):
    strategy_id: UUID
    canonical_name: str = Field(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
    scope: StrategyScope
    problem_class_id: NonEmptyStr
    created_at: UtcDatetime
    created_by: StrategyActor

    @field_validator("canonical_name", mode="before")
    @classmethod
    def canonicalize_name(cls, value: object) -> object:
        return re.sub(r"[^a-z0-9]+", "-", str(value).strip().casefold()).strip("-")


class StrategyRevision(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1, le=1_000)
    previous_revision: int | None = Field(default=None, ge=1)
    status: StrategyStatus
    display_name: Annotated[str, Field(min_length=1, max_length=256)]
    description: Annotated[str, Field(min_length=1, max_length=4_096)]
    applicability_profile: StrategyApplicabilityProfile
    phases: Annotated[tuple[StrategyPhase, ...], Field(min_length=1, max_length=32)]
    branches: tuple[StrategyBranch, ...] = Field(default=(), max_length=32)
    skill_bindings: tuple[StrategySkillBinding, ...] = Field(default=(), max_length=32)
    model_role_bindings: tuple[StrategyModelRoleBinding, ...] = Field(default=(), max_length=16)
    context_profiles: tuple[StrategyContextProfile, ...] = Field(default=(), max_length=16)
    budget_profile: StrategyBudgetProfile
    repair_policy: StrategyRepairPolicy
    stop_conditions: Annotated[
        tuple[StrategyStopCondition, ...], Field(min_length=1, max_length=16)
    ]
    fallback_strategy_refs: tuple[StrategyTargetReference, ...] = Field(default=(), max_length=4)
    known_failure_modes: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    expected_risks: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    source_refs: Annotated[tuple[StrategySourceRef, ...], Field(min_length=1, max_length=64)]
    sensitivity: MemorySensitivity
    regression_profile: NonEmptyStr
    created_at: UtcDatetime
    created_by: StrategyActor
    reason: NonEmptyStr
    content_hash: str = ""

    @model_validator(mode="after")
    def validate_graph_and_seal(self) -> StrategyRevision:
        expected_previous = None if self.revision == 1 else self.revision - 1
        if self.previous_revision != expected_previous:
            raise ValueError("strategy revision must reference its immediate predecessor")
        phase_ids = [item.phase_id for item in self.phases]
        if len(phase_ids) != len(set(phase_ids)):
            raise ValueError("strategy phase IDs must be unique")
        known_phases = set(phase_ids)
        if any(set(item.dependencies) - known_phases for item in self.phases):
            raise ValueError("strategy phase dependency is unavailable")
        if any(
            item.source_phase_id not in known_phases or item.target_phase_id not in known_phases
            for item in self.branches
        ):
            raise ValueError("strategy branch references an unavailable phase")
        binding_ids = {item.binding_id for item in self.skill_bindings}
        if len(binding_ids) != len(self.skill_bindings):
            raise ValueError("strategy skill binding IDs must be unique")
        if any(set(item.skill_binding_ids) - binding_ids for item in self.phases):
            raise ValueError("strategy phase references an unavailable skill binding")
        expected = self.canonical_hash(exclude={"content_hash"})
        if self.content_hash and self.content_hash != expected:
            raise ValueError("strategy revision hash mismatch")
        object.__setattr__(self, "content_hash", expected)
        return self


class StrategyItem(StrategyContract):
    identity: StrategyIdentity
    current_revision: int = Field(ge=1)
    current_status: StrategyStatus
    idempotency_key: Sha256Hex


class StrategyEdge(StrategyContract):
    edge_id: UUID
    source_strategy_id: UUID
    source_revision: int = Field(ge=1)
    target: StrategyTargetReference
    edge_type: StrategyEdgeType
    source_refs: Annotated[tuple[StrategySourceRef, ...], Field(min_length=1, max_length=64)]
    weight: Decimal = Field(default=Decimal("1"), ge=-1, le=1, allow_inf_nan=False)
    created_at: UtcDatetime
    edge_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> StrategyEdge:
        if (
            self.edge_type is StrategyEdgeType.SUPERSEDES
            and self.target.target_type is StrategyTargetType.STRATEGY_REVISION
            and self.target.target_id == str(self.source_strategy_id)
            and self.target.target_revision == str(self.source_revision)
        ):
            raise ValueError("strategy revision cannot supersede itself")
        expected = self.canonical_hash(exclude={"edge_hash"})
        if self.edge_hash and self.edge_hash != expected:
            raise ValueError("strategy edge hash mismatch")
        object.__setattr__(self, "edge_hash", expected)
        return self


class StrategyEdgeSet(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    edges: tuple[StrategyEdge, ...] = Field(default=(), max_length=256)

    @model_validator(mode="after")
    def unique_edges(self) -> StrategyEdgeSet:
        hashes = [item.edge_hash for item in self.edges]
        if len(hashes) != len(set(hashes)):
            raise ValueError("duplicate canonical strategy edge")
        if any(
            item.source_strategy_id != self.strategy_id or item.source_revision != self.revision
            for item in self.edges
        ):
            raise ValueError("strategy edge set contains another source revision")
        return self


class StrategyRegistrySnapshot(StrategyContract):
    strategy_registry_hash: Sha256Hex
    problem_class_registry_hash: Sha256Hex
    target_resolver_registry_hash: Sha256Hex
    skill_registry: SkillRegistrySnapshot
    tool_registry_hash: Sha256Hex
    verifier_registry_hash: Sha256Hex
    provider_registry_hash: Sha256Hex
    context_registry_hash: Sha256Hex


class StrategySelectionRequest(StrategyContract):
    selection_id: UUID
    task_run_id: UUID
    problem_reference: UUID
    applicability_input: StrategyApplicabilityInput
    registry_snapshot: StrategyRegistrySnapshot
    controller_budget: StrategyBudgetProfile
    operator_restrictions: tuple[NonEmptyStr, ...] = Field(default=(), max_length=32)
    approval_granted: bool = False
    provider_suggestion: UUID | None = None
    maximum_candidates: int = Field(default=64, ge=1, le=256)
    created_at: UtcDatetime


class StrategySelectionCandidate(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    canonical_name: NonEmptyStr
    applicability: StrategyApplicabilityResult
    cold_start_status: StrategyColdStartStatus
    score_breakdown: dict[str, Decimal]
    total_score: Decimal = Field(allow_inf_nan=False)


class StrategySelectionExclusion(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    reason: StrategyExclusionReason
    detail_code: NonEmptyStr


class ResolvedSkillBinding(StrategyContract):
    binding_id: NonEmptyStr
    skill_id: UUID
    revision: int = Field(ge=1)
    package_hash: Sha256Hex
    fallback: bool = False


class StrategySelectionDecision(StrategyContract):
    selection_id: UUID
    task_run_id: UUID
    status: StrategySelectionStatus
    selected_strategy_id: UUID | None = None
    selected_revision: int | None = Field(default=None, ge=1)
    candidates: tuple[StrategySelectionCandidate, ...]
    exclusions: tuple[StrategySelectionExclusion, ...]
    skill_resolution_preview: tuple[ResolvedSkillBinding, ...] = ()
    registry_snapshot: StrategyRegistrySnapshot
    statistics_snapshot_hash: Sha256Hex
    ranking_profile_id: NonEmptyStr
    ranking_profile_hash: Sha256Hex
    cold_start_status: StrategyColdStartStatus | None = None
    approval_required: bool = False
    reason: NonEmptyStr
    created_at: UtcDatetime
    decision_hash: str = ""

    @model_validator(mode="after")
    def selected_pair_and_seal(self) -> StrategySelectionDecision:
        if (self.selected_strategy_id is None) != (self.selected_revision is None):
            raise ValueError("selected strategy identity and revision must be paired")
        if self.status is StrategySelectionStatus.SELECTED and self.selected_strategy_id is None:
            raise ValueError("selected strategy decision requires an exact revision")
        expected = self.canonical_hash(exclude={"decision_hash"})
        if self.decision_hash and self.decision_hash != expected:
            raise ValueError("strategy selection decision hash mismatch")
        object.__setattr__(self, "decision_hash", expected)
        return self


class StrategyPlanStepBinding(StrategyContract):
    step_id: UUID
    phase_id: NonEmptyStr
    skill_binding: ResolvedSkillBinding | None = None
    model_role_id: NonEmptyStr | None = None
    tool_capabilities: tuple[NonEmptyStr, ...] = ()
    verifier_capabilities: tuple[NonEmptyStr, ...] = ()
    context_profile_id: NonEmptyStr | None = None
    effective_budget: StrategyBudgetProfile
    branch_ids: tuple[NonEmptyStr, ...] = ()
    fallback_provenance: tuple[NonEmptyStr, ...] = ()


class StrategyPlanInstantiation(StrategyContract):
    instantiation_id: UUID
    selection_id: UUID
    strategy_id: UUID
    strategy_revision: int = Field(ge=1)
    task_run_id: UUID
    plan: ExecutionPlan
    step_bindings: tuple[StrategyPlanStepBinding, ...]
    registry_snapshot: StrategyRegistrySnapshot
    plan_artifact: ArtifactRef | None = None
    created_at: UtcDatetime
    plan_hash: str = ""

    @model_validator(mode="after")
    def complete_mapping_and_seal(self) -> StrategyPlanInstantiation:
        plan_steps = {item.step_id for item in self.plan.steps}
        bindings = [item.step_id for item in self.step_bindings]
        if len(bindings) != len(set(bindings)) or set(bindings) != plan_steps:
            raise ValueError("strategy plan steps require one-to-one provenance bindings")
        expected = self.canonical_hash(exclude={"plan_hash"})
        if self.plan_hash and self.plan_hash != expected:
            raise ValueError("strategy plan hash mismatch")
        object.__setattr__(self, "plan_hash", expected)
        return self


class StrategyExecutionRequest(StrategyContract):
    execution_id: UUID
    selection: StrategySelectionDecision
    task_run_id: UUID
    problem_reference: UUID
    controller_budget: StrategyBudgetProfile
    requested_by: StrategyActor
    created_at: UtcDatetime


class StrategyPhaseExecution(StrategyContract):
    phase_id: NonEmptyStr
    status: StrategyExecutionStatus
    branch_decision: StrategyBranchDecision | None = None
    skill_execution_ids: tuple[UUID, ...] = ()
    provider_call_ids: tuple[UUID, ...] = ()
    tool_call_ids: tuple[UUID, ...] = ()
    context_bundle_references: tuple[ContextBundleReference, ...] = ()
    verifier_result_ids: tuple[UUID, ...] = ()
    fallback_path: tuple[NonEmptyStr, ...] = ()
    latency_ms: int = Field(default=0, ge=0)
    token_usage: int = Field(default=0, ge=0)


class StrategyOutcome(StrategyContract):
    outcome_id: UUID
    execution_id: UUID
    selection_id: UUID
    task_run_id: UUID
    problem_signature: SkillProblemSignature
    strategy_id: UUID
    strategy_revision: int = Field(ge=1)
    resolved_skills: tuple[ResolvedSkillBinding, ...]
    plan_instantiation_id: UUID
    plan_hash: Sha256Hex
    phase_executions: tuple[StrategyPhaseExecution, ...]
    provider_decision_ids: tuple[UUID, ...] = ()
    context_bundle_references: tuple[ContextBundleReference, ...] = ()
    provider_call_ids: tuple[UUID, ...] = ()
    tool_call_ids: tuple[UUID, ...] = ()
    verifier_bundle: ArtifactRef | None = None
    acceptance_decision_id: UUID | None = None
    safety_decision_ids: tuple[UUID, ...] = ()
    failure_mode_ids: tuple[NonEmptyStr, ...] = ()
    repair_count: int = Field(default=0, ge=0, le=3)
    fallback_count: int = Field(default=0, ge=0, le=4)
    status: StrategyOutcomeStatus
    usage: TokenUsage = TokenUsage()
    elapsed_ms: int = Field(ge=0)
    policy_reasons: tuple[NonEmptyStr, ...] = ()
    started_at: UtcDatetime
    finished_at: UtcDatetime
    outcome_hash: str = ""

    @model_validator(mode="after")
    def complete_accepted_lineage_and_seal(self) -> StrategyOutcome:
        if self.finished_at < self.started_at:
            raise ValueError("strategy outcome finishes before it starts")
        if self.status is StrategyOutcomeStatus.ACCEPTED and (
            self.acceptance_decision_id is None
            or self.verifier_bundle is None
            or not self.phase_executions
        ):
            raise ValueError("accepted strategy outcome requires complete authoritative evidence")
        expected = self.canonical_hash(exclude={"outcome_hash"})
        if self.outcome_hash and self.outcome_hash != expected:
            raise ValueError("strategy outcome hash mismatch")
        object.__setattr__(self, "outcome_hash", expected)
        return self


class StrategyExecutionResult(StrategyContract):
    execution_id: UUID
    strategy_id: UUID
    strategy_revision: int = Field(ge=1)
    task_run_id: UUID
    status: StrategyExecutionStatus
    plan_instantiation: StrategyPlanInstantiation
    phase_executions: tuple[StrategyPhaseExecution, ...]
    outcome: StrategyOutcome | None = None
    failure: NonEmptyStr | None = None
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    result_hash: str = ""

    @model_validator(mode="after")
    def terminal_and_seal(self) -> StrategyExecutionResult:
        terminal = self.status not in {
            StrategyExecutionStatus.PREPARING,
            StrategyExecutionStatus.RUNNING,
            StrategyExecutionStatus.WAITING,
        }
        if terminal != (self.finished_at is not None):
            raise ValueError("terminal strategy execution requires a finish time")
        if self.status is StrategyExecutionStatus.ACCEPTED and (
            self.outcome is None or self.outcome.status is not StrategyOutcomeStatus.ACCEPTED
        ):
            raise ValueError("accepted strategy execution requires an accepted outcome")
        expected = self.canonical_hash(exclude={"result_hash"})
        if self.result_hash and self.result_hash != expected:
            raise ValueError("strategy execution result hash mismatch")
        object.__setattr__(self, "result_hash", expected)
        return self


class StrategyStatistics(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    cohort_id: NonEmptyStr
    projection_revision: int = Field(ge=1)
    executions: int = Field(ge=0)
    accepted: int = Field(ge=0)
    rejected: int = Field(ge=0)
    unverifiable: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    policy_denied: int = Field(ge=0)
    infrastructure_failures: int = Field(ge=0)
    verifier_quality: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    repairs: int = Field(ge=0)
    fallbacks: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    context_builds: int = Field(ge=0)
    token_usage: int = Field(ge=0)
    elapsed_ms: int = Field(ge=0)
    safety_failures: int = Field(ge=0)
    confidence_lower_bound: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    confidence_formula_version: NonEmptyStr = "wilson-v1"
    sparse_sample: bool
    source_outcome_ids: tuple[UUID, ...]
    projection_hash: str = ""

    @model_validator(mode="after")
    def counts_and_seal(self) -> StrategyStatistics:
        terminal = (
            self.accepted
            + self.rejected
            + self.unverifiable
            + self.cancelled
            + self.policy_denied
            + self.infrastructure_failures
        )
        if terminal != self.executions or self.executions != len(self.source_outcome_ids):
            raise ValueError("strategy statistics terminal counts do not match outcomes")
        expected = self.canonical_hash(exclude={"projection_hash"})
        if self.projection_hash and self.projection_hash != expected:
            raise ValueError("strategy statistics hash mismatch")
        object.__setattr__(self, "projection_hash", expected)
        return self


class StrategyStatisticsSnapshot(StrategyContract):
    statistics: tuple[StrategyStatistics, ...]
    snapshot_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> StrategyStatisticsSnapshot:
        expected = self.canonical_hash(exclude={"snapshot_hash"})
        if self.snapshot_hash and self.snapshot_hash != expected:
            raise ValueError("strategy statistics snapshot hash mismatch")
        object.__setattr__(self, "snapshot_hash", expected)
        return self


class StrategyAccessRecord(StrategyContract):
    access_id: UUID
    strategy_id: UUID
    revision: int = Field(ge=1)
    access_type: StrategyAccessType
    task_run_id: UUID | None = None
    context_request_id: UUID | None = None
    query_hash: Sha256Hex | None = None
    scope: StrategyScope
    sensitivity: MemorySensitivity
    accessed_at: UtcDatetime


class StrategyGraphSnapshot(StrategyContract):
    snapshot_id: UUID
    nodes: tuple[StrategyTargetReference, ...] = Field(max_length=5_000)
    edges: tuple[StrategyEdge, ...] = Field(max_length=10_000)
    query_parameters: dict[str, JsonValue]
    registry_snapshot: StrategyRegistrySnapshot
    created_at: UtcDatetime
    snapshot_hash: str = ""

    @model_validator(mode="after")
    def stable_order_and_seal(self) -> StrategyGraphSnapshot:
        if tuple(self.nodes) != tuple(
            sorted(
                self.nodes,
                key=lambda item: (
                    item.target_type.value,
                    item.target_id,
                    item.target_revision,
                ),
            )
        ):
            raise ValueError("strategy graph snapshot nodes require canonical ordering")
        if tuple(self.edges) != tuple(sorted(self.edges, key=lambda item: item.edge_hash)):
            raise ValueError("strategy graph snapshot edges require canonical ordering")
        expected = self.canonical_hash(exclude={"snapshot_hash"})
        if self.snapshot_hash and self.snapshot_hash != expected:
            raise ValueError("strategy graph snapshot hash mismatch")
        object.__setattr__(self, "snapshot_hash", expected)
        return self


class StrategyComparisonRequest(StrategyContract):
    comparison_id: UUID
    left_strategy_id: UUID
    left_revision: int = Field(ge=1)
    right_strategy_id: UUID
    right_revision: int = Field(ge=1)
    cohort_id: NonEmptyStr
    created_at: UtcDatetime


class StrategyComparisonResult(StrategyContract):
    comparison_id: UUID
    structural_changes: tuple[NonEmptyStr, ...]
    statistics_delta: dict[str, Decimal]
    sufficient_sample: bool
    source_outcome_ids: tuple[UUID, ...]
    report_artifact: ArtifactRef | None = None
    comparison_hash: str = ""

    @model_validator(mode="after")
    def seal(self) -> StrategyComparisonResult:
        expected = self.canonical_hash(exclude={"comparison_hash"})
        if self.comparison_hash and self.comparison_hash != expected:
            raise ValueError("strategy comparison hash mismatch")
        object.__setattr__(self, "comparison_hash", expected)
        return self


class StrategyVerificationSnapshot(StrategyContract):
    strategy_id: UUID
    revision: int = Field(ge=1)
    schema_conformance: bool
    phase_structure: bool
    graph_integrity: bool
    edge_targets: bool
    applicability_determinism: bool
    skill_integrity: bool
    capability_integrity: bool
    fallback_acyclic: bool
    budget_conformance: bool
    plan_instantiation_conformance: bool
    outcome_lineage: bool
    statistics_reproducibility: bool
    no_permission_expansion: bool

    @property
    def passed(self) -> bool:
        return all(
            bool(value) for value in self.model_dump(exclude={"strategy_id", "revision"}).values()
        )


class StrategyPromotionDecision(StrategyContract):
    decision_id: UUID
    strategy_id: UUID
    revision: int = Field(ge=1)
    outcome: StrategyPromotionOutcome
    verifier_bundle: ArtifactRef
    regression_summary: ArtifactRef
    decided_by: StrategyActor
    reason_codes: tuple[NonEmptyStr, ...]
    decided_at: UtcDatetime


PUBLIC_STRATEGY_CONTRACTS: tuple[type[ImmutableContractModel], ...] = (
    StrategyActor,
    StrategyScope,
    StrategySourceRef,
    StrategyTargetReference,
    ProblemClassDescriptor,
    FailureModeDescriptor,
    StrategyApplicabilityCondition,
    StrategyApplicabilityProfile,
    StrategyApplicabilityEvidence,
    StrategyApplicabilityInput,
    StrategyApplicabilityResult,
    StrategyRequirement,
    StrategyModelRoleBinding,
    StrategyContextProfile,
    StrategyBudgetProfile,
    StrategyRepairPolicy,
    StrategyStopCondition,
    StrategySkillBinding,
    StrategyBranchCondition,
    StrategyBranch,
    StrategyBranchDecision,
    StrategyPhase,
    StrategyIdentity,
    StrategyRevision,
    StrategyItem,
    StrategyEdge,
    StrategyEdgeSet,
    StrategyRegistrySnapshot,
    StrategySelectionRequest,
    StrategySelectionCandidate,
    StrategySelectionExclusion,
    ResolvedSkillBinding,
    StrategySelectionDecision,
    StrategyPlanStepBinding,
    StrategyPlanInstantiation,
    StrategyExecutionRequest,
    StrategyPhaseExecution,
    StrategyOutcome,
    StrategyExecutionResult,
    StrategyStatistics,
    StrategyStatisticsSnapshot,
    StrategyAccessRecord,
    StrategyGraphSnapshot,
    StrategyComparisonRequest,
    StrategyComparisonResult,
    StrategyVerificationSnapshot,
    StrategyPromotionDecision,
)
