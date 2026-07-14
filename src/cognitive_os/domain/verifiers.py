"""Typed contracts for verifier discovery, execution, and aggregation."""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from pathlib import PurePosixPath, PureWindowsPath
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .enums import RiskLevel, VerifierStatus
from .problems import CriterionType, ProblemDomain
from .verification import VerifierResult


class VerifierKind(StrEnum):
    GENERIC = "generic"
    CODING = "coding"
    MATHEMATICS = "mathematics"
    LOGIC = "logic"
    PHYSICS = "physics"
    POLICY = "policy"
    ADVISORY = "advisory"


class VerifierDeterminism(StrEnum):
    DETERMINISTIC = "deterministic"
    SEEDED = "seeded"
    NON_DETERMINISTIC = "non_deterministic"


class VerificationExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"
    UNSUPPORTED = "unsupported"
    CONFIGURATION_ERROR = "configuration_error"


class VerificationSubjectType(StrEnum):
    STRUCTURED_VALUE = "structured_value"
    ARTIFACT = "artifact"
    WORKSPACE = "workspace"
    EXECUTION_PLAN = "execution_plan"
    EXECUTION_STEP = "execution_step"
    MODEL_RESPONSE = "model_response"
    TOOL_RESULT = "tool_result"
    MATHEMATICAL_EXPRESSION = "mathematical_expression"
    LOGICAL_PROBLEM = "logical_problem"
    PHYSICAL_QUANTITY = "physical_quantity"


class VerifierHealthStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class VerifierHealth(ImmutableContractModel):
    status: VerifierHealthStatus
    reason: NonEmptyStr | None = None


class VerifierCapability(ImmutableContractModel):
    capability_id: NonEmptyStr
    subject_type: VerificationSubjectType
    problem_domains: tuple[ProblemDomain, ...]
    criterion_types: tuple[CriterionType, ...]
    supported_media_types: tuple[NonEmptyStr, ...] = ()
    requires_sandbox: bool = False
    requires_network: bool = False
    supports_batch: bool = False

    @model_validator(mode="after")
    def validate_capability(self) -> VerifierCapability:
        if not self.problem_domains or not self.criterion_types:
            raise ValueError("verifier capability requires domains and criterion types")
        if self.supports_batch:
            raise ValueError("Sprint 7 built-in verifiers do not support batches")
        return self


class VerifierDescriptor(ImmutableContractModel):
    verifier_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
    version: NonEmptyStr
    display_name: NonEmptyStr
    description: NonEmptyStr
    kind: VerifierKind
    capabilities: tuple[VerifierCapability, ...] = Field(min_length=1)
    determinism: VerifierDeterminism
    requires_sandbox: bool = False
    requires_network: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    default_timeout_seconds: float = Field(gt=0, le=3600)
    maximum_input_bytes: int = Field(gt=0)
    configuration_schema: dict[str, JsonValue] = Field(default_factory=dict)
    descriptor_hash: str = ""

    @model_validator(mode="after")
    def seal_hash(self) -> VerifierDescriptor:
        expected = self.computed_hash()
        if self.descriptor_hash and self.descriptor_hash != expected:
            raise ValueError("descriptor hash does not match descriptor content")
        object.__setattr__(self, "descriptor_hash", expected)
        return self

    def computed_hash(self) -> str:
        payload = self.model_dump(mode="json", exclude={"descriptor_hash"})
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class VerificationSubject(ImmutableContractModel):
    subject_type: VerificationSubjectType
    inline_value: JsonValue = None
    artifact_refs: tuple[ArtifactRef, ...] = ()
    workspace_path: str | None = None
    source_event_ids: tuple[UUID, ...] = ()

    @field_validator("workspace_path")
    @classmethod
    def safe_workspace_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        posix, windows = PurePosixPath(value), PureWindowsPath(value)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or ".." in posix.parts
            or ".." in windows.parts
        ):
            raise ValueError("workspace path must be a safe relative path")
        return value

    @model_validator(mode="after")
    def validate_sources(self) -> VerificationSubject:
        if self.inline_value is None and not self.artifact_refs and self.workspace_path is None:
            raise ValueError("at least one verification subject source is required")
        if (
            self.workspace_path is not None
            and self.subject_type is not VerificationSubjectType.WORKSPACE
        ):
            raise ValueError("workspace path is valid only for workspace subjects")
        if len({item.artifact_id for item in self.artifact_refs}) != len(self.artifact_refs):
            raise ValueError("artifact references must be unique")
        if len(set(self.source_event_ids)) != len(self.source_event_ids):
            raise ValueError("source event IDs must be unique")
        return self


class VerificationRequest(ImmutableContractModel):
    verification_id: UUID
    task_run_id: UUID
    step_id: UUID | None = None
    criterion_id: UUID
    verifier_id: NonEmptyStr
    verifier_version: NonEmptyStr
    subject: VerificationSubject
    configuration: dict[str, JsonValue] = Field(default_factory=dict)
    requested_at: UtcDatetime
    correlation_id: UUID
    causation_event_id: UUID | None = None


TERMINAL_EXECUTION_STATUSES = frozenset(
    {
        VerificationExecutionStatus.COMPLETED,
        VerificationExecutionStatus.FAILED,
        VerificationExecutionStatus.TIMED_OUT,
        VerificationExecutionStatus.CANCELLED,
        VerificationExecutionStatus.UNSUPPORTED,
        VerificationExecutionStatus.CONFIGURATION_ERROR,
    }
)


class VerificationExecution(ImmutableContractModel):
    verification_id: UUID
    verifier_id: NonEmptyStr
    verifier_version: NonEmptyStr
    status: VerificationExecutionStatus
    started_at: UtcDatetime | None = None
    finished_at: UtcDatetime | None = None
    result: VerifierResult | None = None
    evidence_artifacts: tuple[ArtifactRef, ...] = ()
    configuration_hash: Sha256Hex
    error: ErrorInfo | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> VerificationExecution:
        terminal = self.status in TERMINAL_EXECUTION_STATUSES
        if terminal != (self.finished_at is not None):
            raise ValueError("terminal execution status requires a finish time")
        if self.status is VerificationExecutionStatus.COMPLETED and self.result is None:
            raise ValueError("completed verification requires a result")
        if (
            self.status
            in {VerificationExecutionStatus.FAILED, VerificationExecutionStatus.CONFIGURATION_ERROR}
            and self.error is None
        ):
            raise ValueError("failed verification execution requires a structured error")
        if (
            self.status is VerificationExecutionStatus.TIMED_OUT
            and self.result
            and self.result.status is VerifierStatus.PASSED
        ):
            raise ValueError("timed-out verification cannot pass")
        return self


class VerificationBundle(ImmutableContractModel):
    bundle_id: UUID
    task_run_id: UUID
    criterion_results: tuple[UUID, ...]
    verifier_results: tuple[VerifierResult, ...]
    required_passed: bool
    optional_score: float = Field(ge=0, le=1)
    failed_required_criteria: tuple[UUID, ...] = ()
    unverifiable_required_criteria: tuple[UUID, ...] = ()
    errored_required_criteria: tuple[UUID, ...] = ()
    created_at: UtcDatetime
