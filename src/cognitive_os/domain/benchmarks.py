"""Reproducible benchmark contracts."""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from pydantic import Field, model_validator

from .acceptance import AcceptanceDecision, AcceptancePolicy
from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .verifiers import VerificationBundle


class BenchmarkDomain(StrEnum):
    GENERIC = "generic"
    CONTROLLER = "controller"
    CODING = "coding"
    MEMORY = "memory"
    MATHEMATICS = "mathematics"
    LOGIC = "logic"
    PHYSICS = "physics"


class BenchmarkCaseStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMED_OUT = "timed_out"


class BenchmarkRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkResourceBudget(ImmutableContractModel):
    maximum_elapsed_seconds: float = Field(gt=0)
    maximum_provider_calls: int = Field(default=0, ge=0)
    maximum_tool_calls: int = Field(default=0, ge=0)
    maximum_input_tokens: int = Field(default=0, ge=0)
    maximum_output_tokens: int = Field(default=0, ge=0)
    maximum_cost_units: float = Field(default=0, ge=0)
    maximum_artifact_bytes: int = Field(gt=0)


def _hash_model(value: ImmutableContractModel, hash_field: str) -> Sha256Hex:
    payload = value.model_dump(mode="json", exclude={hash_field})
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class BenchmarkCase(ImmutableContractModel):
    case_id: NonEmptyStr
    version: NonEmptyStr
    domain: BenchmarkDomain
    title: NonEmptyStr
    description: NonEmptyStr
    input_artifacts: tuple[ArtifactRef, ...] = ()
    problem_request: dict[str, JsonValue]
    expected_outputs: dict[str, JsonValue]
    acceptance_policy: AcceptancePolicy
    resource_budget: BenchmarkResourceBudget
    configuration: dict[str, JsonValue] = Field(default_factory=dict)
    tags: tuple[NonEmptyStr, ...] = ()
    source: NonEmptyStr
    license: NonEmptyStr
    case_hash: str = ""

    @model_validator(mode="after")
    def seal_hash(self) -> BenchmarkCase:
        expected = _hash_model(self, "case_hash")
        if self.case_hash and self.case_hash != expected:
            raise ValueError("case hash mismatch")
        object.__setattr__(self, "case_hash", expected)
        return self


class BenchmarkManifest(ImmutableContractModel):
    benchmark_id: NonEmptyStr
    version: NonEmptyStr
    title: NonEmptyStr
    description: NonEmptyStr
    cases: tuple[BenchmarkCase, ...] = Field(min_length=1)
    default_configuration: dict[str, JsonValue] = Field(default_factory=dict)
    source: NonEmptyStr
    license: NonEmptyStr
    created_at: UtcDatetime
    manifest_hash: str = ""

    @model_validator(mode="after")
    def validate_manifest(self) -> BenchmarkManifest:
        ids = [item.case_id for item in self.cases]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("benchmark cases must be uniquely sorted by case ID")
        expected = _hash_model(self, "manifest_hash")
        if self.manifest_hash and self.manifest_hash != expected:
            raise ValueError("manifest hash mismatch")
        object.__setattr__(self, "manifest_hash", expected)
        return self


class BenchmarkCaseResult(ImmutableContractModel):
    case_id: NonEmptyStr
    status: BenchmarkCaseStatus
    task_run_id: UUID | None = None
    acceptance_decision: AcceptanceDecision | None = None
    verifier_bundles: tuple[VerificationBundle, ...] = ()
    started_at: UtcDatetime
    finished_at: UtcDatetime
    metrics: dict[str, float] = Field(default_factory=dict)
    artifact_refs: tuple[ArtifactRef, ...] = ()
    error: ErrorInfo | None = None


class BenchmarkRun(ImmutableContractModel):
    run_id: UUID
    benchmark_id: NonEmptyStr
    benchmark_version: NonEmptyStr
    manifest_hash: Sha256Hex
    git_commit: NonEmptyStr
    configuration_hash: Sha256Hex
    provider_configuration_hash: Sha256Hex
    tool_registry_hash: Sha256Hex
    verifier_registry_hash: Sha256Hex
    sandbox_image_digest: NonEmptyStr
    random_seed: int
    status: BenchmarkRunStatus
    started_at: UtcDatetime
    finished_at: UtcDatetime | None = None
    case_results: tuple[BenchmarkCaseResult, ...] = ()
    aggregate_metrics: dict[str, float] = Field(default_factory=dict)
    report_artifact: ArtifactRef | None = None
