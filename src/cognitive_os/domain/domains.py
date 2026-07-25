"""Immutable contracts for the mathematics, physics, and logic cross-domain pilot."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .common import ArtifactRef, JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .experience import HashedExperienceContract


class DomainKind(StrEnum):
    MATHEMATICS = "mathematics"
    PHYSICS = "physics"
    LOGIC = "logic"


class DomainRunStatus(StrEnum):
    REQUESTED = "requested"
    PLANNED = "planned"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnswerType(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    SYMBOLIC = "symbolic"
    QUANTITY = "quantity"
    BOOLEAN = "boolean"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNKNOWN = "unknown"
    COUNTEREXAMPLE = "counterexample"
    STRUCTURED = "structured"


class VerificationDisposition(StrEnum):
    PASS = "pass"  # nosec B105 - verification disposition value, not a credential
    PARTIAL = "partial"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"
    UNSUPPORTED = "unsupported"
    RESOURCE_EXHAUSTED = "resource_exhausted"


class TransferDisposition(StrEnum):
    POSITIVE_TRANSFER = "positive_transfer"
    NEUTRAL_TRANSFER = "neutral_transfer"
    NEGATIVE_TRANSFER = "negative_transfer"
    INCONCLUSIVE = "inconclusive"
    INVALID_EXPERIMENT = "invalid_experiment"


class TransferArm(StrEnum):
    """Required control groups; a positive result needs every arm present."""

    SOURCE_RETENTION = "source_retention"
    TARGET_BASELINE = "target_baseline"
    UNCHANGED_SOURCE_REVISION = "unchanged_source_revision"
    MINIMALLY_ADAPTED = "minimally_adapted"
    DOMAIN_SPECIFIC = "domain_specific"
    NO_SKILL_CONTROL = "no_skill_control"
    UNRELATED_DOMAIN = "unrelated_domain"


class DomainFailureCode(StrEnum):
    UNSUPPORTED_PROBLEM_TYPE = "unsupported_problem_type"
    MISSING_REQUIRED_VERIFIER = "missing_required_verifier"
    MISSING_REQUIRED_EVIDENCE = "missing_required_evidence"
    FORBIDDEN_OPERATION = "forbidden_operation"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    TOOL_UNAVAILABLE = "tool_unavailable"
    SOLVER_UNKNOWN = "solver_unknown"
    INVALID_DERIVATION = "invalid_derivation"


class ResourceBudget(HashedExperienceContract):
    """Ceilings validated before execution and enforced during it."""

    timeout_seconds: int = Field(default=10, gt=0, le=300)
    maximum_nodes: int = Field(default=512, gt=0, le=8192)
    maximum_depth: int = Field(default=32, gt=0, le=256)
    maximum_symbols: int = Field(default=32, gt=0, le=1024)
    maximum_integer_digits: int = Field(default=256, gt=0, le=4096)
    maximum_output_bytes: int = Field(default=65_536, gt=0, le=4_194_304)
    maximum_retries: int = Field(default=0, ge=0, le=3)


class ProvenanceRef(HashedExperienceContract):
    """Source, licence, and contamination metadata required before activation."""

    source: NonEmptyStr
    revision: NonEmptyStr
    licence: NonEmptyStr
    redistributable: bool
    checksum: Sha256Hex | None = None
    contamination_notes: NonEmptyStr | None = None
    effective_date: UtcDatetime | None = None


class DomainProblem(HashedExperienceContract):
    problem_id: UUID
    domain: DomainKind
    problem_type: NonEmptyStr
    statement_artifact: ArtifactRef | None = None
    statement: NonEmptyStr
    formal_inputs: dict[str, JsonValue] = Field(default_factory=dict)
    knowns: dict[str, JsonValue] = Field(default_factory=dict)
    unknowns: tuple[NonEmptyStr, ...] = ()
    constraints: tuple[NonEmptyStr, ...] = ()
    assumptions: tuple[NonEmptyStr, ...] = ()
    required_units: tuple[NonEmptyStr, ...] = ()
    required_tools: tuple[NonEmptyStr, ...] = ()
    required_verifiers: tuple[NonEmptyStr, ...] = Field(min_length=1)
    expected_output_schema: dict[str, JsonValue] = Field(default_factory=dict)
    risk: NonEmptyStr = "low"
    source_refs: tuple[ProvenanceRef, ...] = ()
    schema_version: int = Field(default=1, ge=1)
    created_at: UtcDatetime

    @model_validator(mode="after")
    def require_unknowns_and_provenance(self) -> DomainProblem:
        if not self.unknowns:
            raise ValueError("domain problem must declare at least one unknown")
        if self.domain is DomainKind.PHYSICS and not self.required_units:
            raise ValueError("physics problems must declare required units")
        return self


class DerivationStep(HashedExperienceContract):
    """One typed step; provider prose alone can never constitute a derivation."""

    index: int = Field(ge=0)
    operation: NonEmptyStr
    detail: NonEmptyStr
    inputs: tuple[NonEmptyStr, ...] = ()
    output: NonEmptyStr
    tool_evidence: NonEmptyStr | None = None


class DomainDerivation(HashedExperienceContract):
    derivation_id: UUID
    problem_id: UUID
    steps: tuple[DerivationStep, ...] = Field(min_length=1)
    expressions: tuple[NonEmptyStr, ...] = ()
    equations: tuple[NonEmptyStr, ...] = ()
    unit_states: tuple[NonEmptyStr, ...] = ()
    logical_constraints: tuple[NonEmptyStr, ...] = ()
    assumptions: tuple[NonEmptyStr, ...] = ()
    intermediate_results: tuple[NonEmptyStr, ...] = ()
    tool_evidence: tuple[NonEmptyStr, ...] = ()
    provider_evidence: tuple[NonEmptyStr, ...] = ()
    limitations: tuple[NonEmptyStr, ...] = ()
    trace_artifact: ArtifactRef | None = None
    created_at: UtcDatetime

    @field_validator("steps")
    @classmethod
    def ordered_steps(cls, value: tuple[DerivationStep, ...]) -> tuple[DerivationStep, ...]:
        if [item.index for item in value] != list(range(len(value))):
            raise ValueError("derivation steps must be contiguous and ordered from zero")
        return value


class DomainAnswer(HashedExperienceContract):
    problem_id: UUID
    answer_type: AnswerType
    exact_value: NonEmptyStr | None = None
    approximate_value: Decimal | None = None
    tolerance: Decimal | None = Field(default=None, ge=0)
    units: NonEmptyStr | None = None
    symbolic_form: NonEmptyStr | None = None
    logical_status: NonEmptyStr | None = None
    structured_value: dict[str, JsonValue] = Field(default_factory=dict)
    proof_or_derivation_reference: UUID | None = None
    uncertainty: Decimal | None = Field(default=None, ge=0)
    limitations: tuple[NonEmptyStr, ...] = ()
    created_at: UtcDatetime

    @field_validator("approximate_value", "tolerance", "uncertainty")
    @classmethod
    def finite(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not value.is_finite():
            raise ValueError("domain answer values must be finite")
        return value

    @model_validator(mode="after")
    def exact_and_approximate_stay_separate(self) -> DomainAnswer:
        if self.answer_type is AnswerType.EXACT:
            if self.exact_value is None:
                raise ValueError("exact answers require an exact value")
            if self.approximate_value is not None:
                raise ValueError("exact answers must not carry an approximate value")
        if self.answer_type is AnswerType.APPROXIMATE and (
            self.approximate_value is None or self.tolerance is None
        ):
            raise ValueError("approximate answers require a value and a tolerance")
        if self.answer_type is AnswerType.QUANTITY and self.units is None:
            raise ValueError("quantity answers require units")
        structured_types = {
            AnswerType.STRUCTURED,
            AnswerType.COUNTEREXAMPLE,
            AnswerType.SATISFIABLE,
        }
        if self.answer_type in structured_types and not self.structured_value:
            raise ValueError(f"{self.answer_type.value} answers require a structured value")
        return self


class DomainVerificationPlan(HashedExperienceContract):
    """Frozen before execution: nothing runs without a plan."""

    problem_id: UUID
    required_capabilities: tuple[NonEmptyStr, ...] = Field(min_length=1)
    symbolic_checks: tuple[NonEmptyStr, ...] = ()
    numeric_checks: tuple[NonEmptyStr, ...] = ()
    unit_checks: tuple[NonEmptyStr, ...] = ()
    constraint_checks: tuple[NonEmptyStr, ...] = ()
    property_checks: tuple[NonEmptyStr, ...] = ()
    edge_cases: tuple[NonEmptyStr, ...] = ()
    alternative_solution_checks: tuple[NonEmptyStr, ...] = ()
    acceptance_policy: NonEmptyStr = "all_required_checks_must_pass"
    forbidden_operations: tuple[NonEmptyStr, ...] = ()
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)


class DomainBenchmarkCase(HashedExperienceContract):
    case_id: NonEmptyStr
    domain: DomainKind
    problem_type: NonEmptyStr
    difficulty: NonEmptyStr
    problem_artifact: ArtifactRef | None = None
    problem: DomainProblem
    plan: DomainVerificationPlan
    expected_answer: DomainAnswer
    expected_disposition: VerificationDisposition
    expected_properties: dict[str, JsonValue] = Field(default_factory=dict)
    required_tools: tuple[NonEmptyStr, ...] = ()
    required_verifiers: tuple[NonEmptyStr, ...] = Field(min_length=1)
    forbidden_operations: tuple[NonEmptyStr, ...] = ()
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    licence_and_source: ProvenanceRef
    contamination_notes: NonEmptyStr | None = None

    @model_validator(mode="after")
    def case_matches_problem(self) -> DomainBenchmarkCase:
        if self.plan.problem_id != self.problem.problem_id:
            raise ValueError("verification plan must reference the case problem")
        if self.expected_answer.problem_id != self.problem.problem_id:
            raise ValueError("expected answer must reference the case problem")
        if self.domain is not self.problem.domain:
            raise ValueError("benchmark case domain must match the problem domain")
        return self


class VerificationCheckResult(HashedExperienceContract):
    capability: NonEmptyStr
    disposition: VerificationDisposition
    detail: NonEmptyStr
    evidence: JsonValue = None


class DomainVerificationOutcome(HashedExperienceContract):
    """Deterministic acceptance receipt; no component may accept itself."""

    problem_id: UUID
    checks: tuple[VerificationCheckResult, ...] = Field(min_length=1)
    disposition: VerificationDisposition
    failure_code: DomainFailureCode | None = None
    resource_use: dict[str, JsonValue] = Field(default_factory=dict)
    created_at: UtcDatetime

    @model_validator(mode="after")
    def disposition_is_derived(self) -> DomainVerificationOutcome:
        expected = compose_disposition(tuple(item.disposition for item in self.checks))
        if self.disposition is not expected:
            raise ValueError("outcome disposition must be derived from its checks")
        return self


#: Worst-first precedence. Anything short of a full pass never becomes a pass,
#: so `unknown`, timeout, and unsupported checks stay non-passing by construction.
_DISPOSITION_PRECEDENCE: tuple[VerificationDisposition, ...] = (
    VerificationDisposition.FAIL,
    VerificationDisposition.RESOURCE_EXHAUSTED,
    VerificationDisposition.UNSUPPORTED,
    VerificationDisposition.INCONCLUSIVE,
    VerificationDisposition.PARTIAL,
    VerificationDisposition.PASS,
)


def compose_disposition(
    dispositions: tuple[VerificationDisposition, ...],
) -> VerificationDisposition:
    """Return the worst disposition; an empty check set is a failure, not a pass."""
    if not dispositions:
        return VerificationDisposition.FAIL
    return next(item for item in _DISPOSITION_PRECEDENCE if item in dispositions)


class DomainPilotRun(HashedExperienceContract):
    run_id: UUID
    case_id: NonEmptyStr
    domain: DomainKind
    status: DomainRunStatus
    problem_hash: Sha256Hex
    plan_hash: Sha256Hex
    derivation_hash: Sha256Hex | None = None
    answer_hash: Sha256Hex | None = None
    outcome_hash: Sha256Hex | None = None
    skill_revisions: tuple[NonEmptyStr, ...] = ()
    strategy_revisions: tuple[NonEmptyStr, ...] = ()
    failure_code: DomainFailureCode | None = None
    created_at: UtcDatetime


class TransferMetrics(HashedExperienceContract):
    """Matched-resource measurements; every arm reports the same fields."""

    solved: int = Field(ge=0)
    total: int = Field(gt=0)
    verifier_failures: int = Field(default=0, ge=0)
    repairs: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    cpu_ms: int = Field(default=0, ge=0)
    peak_memory_bytes: int = Field(default=0, ge=0)
    safety_violations: int = Field(default=0, ge=0)
    policy_violations: int = Field(default=0, ge=0)

    @property
    def quality(self) -> Decimal:
        return Decimal(self.solved) / Decimal(self.total)


class TransferThresholds(HashedExperienceContract):
    """Predeclared before the run; post-hoc substitution is a contract error."""

    minimum_target_quality_gain: Decimal = Field(default=Decimal("0.10"))
    maximum_source_quality_loss: Decimal = Field(default=Decimal("0.02"))
    maximum_unrelated_quality_loss: Decimal = Field(default=Decimal("0.02"))
    maximum_latency_ratio: Decimal = Field(default=Decimal("1.50"), gt=0)
    maximum_tool_call_ratio: Decimal = Field(default=Decimal("1.50"), gt=0)

    @field_validator(
        "minimum_target_quality_gain",
        "maximum_source_quality_loss",
        "maximum_unrelated_quality_loss",
        "maximum_latency_ratio",
        "maximum_tool_call_ratio",
    )
    @classmethod
    def finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("transfer thresholds must be finite")
        return value


class TransferExperiment(HashedExperienceContract):
    experiment_id: UUID
    source_domain: DomainKind
    target_domain: DomainKind
    unrelated_domain: DomainKind
    component_kind: NonEmptyStr
    component_id: NonEmptyStr
    component_revision: NonEmptyStr
    routing_policy: NonEmptyStr
    case_manifest: NonEmptyStr
    thresholds: TransferThresholds
    seed: int = Field(ge=0)
    environment: NonEmptyStr
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    created_at: UtcDatetime

    @model_validator(mode="after")
    def domains_are_distinct(self) -> TransferExperiment:
        if len({self.source_domain, self.target_domain, self.unrelated_domain}) != 3:
            raise ValueError("source, target, and unrelated domains must be distinct")
        if self.component_kind not in {"skill", "strategy"}:
            raise ValueError("transfer component kind must be skill or strategy")
        return self


class TransferResult(HashedExperienceContract):
    experiment_id: UUID
    arms: dict[TransferArm, TransferMetrics]
    target_quality_delta: Decimal
    source_quality_delta: Decimal
    unrelated_quality_delta: Decimal
    disposition: TransferDisposition
    hard_gate_failures: tuple[NonEmptyStr, ...] = ()
    positive_evidence: tuple[NonEmptyStr, ...] = ()
    negative_evidence: tuple[NonEmptyStr, ...] = ()
    uncertainty: NonEmptyStr
    limitations: tuple[NonEmptyStr, ...] = ()
    report_artifact: ArtifactRef | None = None
    created_at: UtcDatetime

    @model_validator(mode="after")
    def controls_cannot_be_omitted(self) -> TransferResult:
        missing = set(TransferArm) - set(self.arms)
        if missing:
            raise ValueError(f"transfer result is missing control arms: {sorted(missing)}")
        if self.disposition is TransferDisposition.POSITIVE_TRANSFER and self.hard_gate_failures:
            raise ValueError("positive transfer cannot be declared with a hard gate failure")
        return self


DOMAIN_CONTRACT_MODELS: tuple[type[HashedExperienceContract], ...] = (
    ResourceBudget,
    ProvenanceRef,
    DomainProblem,
    DerivationStep,
    DomainDerivation,
    DomainAnswer,
    DomainVerificationPlan,
    DomainBenchmarkCase,
    VerificationCheckResult,
    DomainVerificationOutcome,
    DomainPilotRun,
    TransferMetrics,
    TransferThresholds,
    TransferExperiment,
    TransferResult,
)
