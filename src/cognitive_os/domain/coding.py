"""Typed contracts for the Python Coding Agent authority boundary."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, Field, field_validator, model_validator

from .acceptance import AcceptanceDecision
from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, JsonValue, NonEmptyStr, Sha256Hex, UtcDatetime
from .verifiers import VerificationBundle


def _relative_path(value: str) -> str:
    if not value or value == "." or "\x00" in value or any(ord(char) < 32 for char in value):
        raise ValueError("path must be a non-empty printable relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("./"):
        raise ValueError("path must not be absolute or traverse parent directories")
    normalized = path.as_posix()
    if normalized == "." or normalized.startswith(".git/") or normalized == ".git":
        raise ValueError("Git administrative paths are forbidden")
    return normalized


RelativeRepositoryPath = Annotated[str, AfterValidator(_relative_path)]


class CodingRecord(ImmutableContractModel):
    """Immutable coding record with deterministic canonical serialization."""

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def canonical_hash(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()


class RepositoryProfileStatus(StrEnum):
    SUPPORTED = "supported"
    PROFILE_MISMATCH = "profile_mismatch"


class WorkspaceState(StrEnum):
    REQUESTED = "requested"
    VALIDATING = "validating"
    PREPARED = "prepared"
    MOUNTED = "mounted"
    ACTIVE = "active"
    COLLECTING = "collecting"
    ARCHIVED = "archived"
    REMOVED = "removed"
    FAILED = "failed"
    RECOVERY_REQUIRED = "recovery_required"


class WorkspaceRecoveryClassification(StrEnum):
    NOT_PREPARED = "not_prepared"
    PREPARED_CLEAN = "prepared_clean"
    PREPARED_WITH_CHANGES = "prepared_with_changes"
    VERIFICATION_IN_PROGRESS = "verification_in_progress"
    SAFE_TO_RESUME = "safe_to_resume"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"
    ORPHANED = "orphaned"
    CORRUPT = "corrupt"


class PatchAttemptStatus(StrEnum):
    PROPOSED = "proposed"
    APPLIED = "applied"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class CodingCommandStatus(StrEnum):
    PASSED = "passed"
    SUBJECT_FAILED = "subject_failed"
    EXECUTION_ERROR = "execution_error"
    TIMED_OUT = "timed_out"
    UNAVAILABLE = "unavailable"


class CodingOutcomeStatus(StrEnum):
    ACCEPTED = "accepted"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"
    SECURITY_FAILURE = "security_failure"


class ChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class WorkspaceDisposition(StrEnum):
    REMOVE = "remove"
    ARCHIVE = "archive"
    PRESERVE_FOR_REVIEW = "preserve_for_review"
    PRESERVE_AFTER_FAILURE = "preserve_after_failure"


class RepositoryProfileMismatch(CodingRecord):
    reason_code: NonEmptyStr
    message: NonEmptyStr
    details: dict[str, JsonValue] = Field(default_factory=dict)


class RepositoryProfile(CodingRecord):
    status: RepositoryProfileStatus
    git_repository: bool
    has_pyproject: bool
    python_version: str | None = None
    has_pytest: bool = False
    has_ruff: bool = False
    has_mypy: bool = False
    package_layout: NonEmptyStr | None = None
    rootless_docker: bool = False
    mismatches: tuple[RepositoryProfileMismatch, ...] = ()

    @model_validator(mode="after")
    def status_matches_reasons(self) -> RepositoryProfile:
        if self.status is RepositoryProfileStatus.SUPPORTED and self.mismatches:
            raise ValueError("supported profile cannot contain mismatches")
        if self.status is RepositoryProfileStatus.PROFILE_MISMATCH and not self.mismatches:
            raise ValueError("profile mismatch requires at least one reason")
        return self


class RepositoryReference(CodingRecord):
    repository_path: Path = Field(exclude=True)
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    repository_identity: Sha256Hex

    @field_validator("repository_path")
    @classmethod
    def absolute_repository_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("repository path must be absolute host configuration")
        return value


class CodingLimits(CodingRecord):
    maximum_patch_attempts: int = Field(default=3, ge=1, le=3)
    maximum_repair_cycles: int = Field(default=3, ge=0, le=3)
    maximum_changed_files: int = Field(default=20, ge=1, le=20)
    maximum_diff_lines: int = Field(default=1000, ge=1, le=1000)
    maximum_repository_files: int = Field(default=10_000, ge=1, le=10_000)
    maximum_indexed_file_bytes: int = Field(default=1_000_000, ge=1, le=1_000_000)
    maximum_total_index_bytes: int = Field(default=50_000_000, ge=1, le=50_000_000)
    maximum_recent_commits: int = Field(default=50, ge=0, le=50)
    maximum_search_results: int = Field(default=200, ge=1, le=200)
    maximum_file_read_bytes: int = Field(default=262_144, ge=1, le=262_144)
    sandbox_cpu_limit: int = Field(default=4, ge=1, le=4)
    sandbox_memory_mb: int = Field(default=8192, ge=128, le=8192)
    allow_network: bool = False
    allow_dependency_changes: bool = False
    allow_commit: bool = False
    allow_push: bool = False
    allow_merge: bool = False

    @model_validator(mode="after")
    def deny_unsupported_authority(self) -> CodingLimits:
        if self.allow_network or self.allow_commit or self.allow_push or self.allow_merge:
            raise ValueError("network, commit, push, and merge are forbidden in Sprint 8")
        return self


class CodingCommandPolicy(CodingRecord):
    allowed_executables: tuple[NonEmptyStr, ...] = (
        "pytest",
        "ruff",
        "mypy",
        "controlled-import",
    )
    project_commands: dict[str, tuple[NonEmptyStr, ...]] = Field(default_factory=dict)

    @field_validator("allowed_executables")
    @classmethod
    def sealed_executables(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {"pytest", "ruff", "mypy", "controlled-import"}
        if not set(values) <= allowed:
            raise ValueError("unknown executable in coding command policy")
        return tuple(sorted(set(values)))


class PathPolicy(CodingRecord):
    allowed_paths: tuple[RelativeRepositoryPath, ...] = ()
    forbidden_paths: tuple[RelativeRepositoryPath, ...] = ()
    allow_delete_baseline_files: bool = False

    @model_validator(mode="after")
    def no_collision(self) -> PathPolicy:
        allowed = {item.casefold() for item in self.allowed_paths}
        forbidden = {item.casefold() for item in self.forbidden_paths}
        if allowed & forbidden:
            raise ValueError("path cannot be both allowed and forbidden")
        return self


class DependencyChangePolicy(CodingRecord):
    allow_dependency_changes: bool = False
    protected_patterns: tuple[str, ...] = (
        "pyproject.toml",
        "uv.lock",
        "requirements*.txt",
        "poetry.lock",
        "Pipfile*",
        "setup.py",
        "setup.cfg",
    )
    allow_installation: bool = False

    @model_validator(mode="after")
    def installation_never_allowed(self) -> DependencyChangePolicy:
        if self.allow_installation:
            raise ValueError("package installation is outside Sprint 8 authority")
        return self


class CodingProblemExtension(CodingRecord):
    repository_path: Path = Field(exclude=True)
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    issue_description: NonEmptyStr
    reproduction_steps: tuple[NonEmptyStr, ...] = ()
    expected_behavior: NonEmptyStr
    forbidden_paths: tuple[RelativeRepositoryPath, ...] = ()
    allowed_paths: tuple[RelativeRepositoryPath, ...] = ()
    test_commands: tuple[tuple[NonEmptyStr, ...], ...] = ()
    quality_commands: tuple[tuple[NonEmptyStr, ...], ...] = ()
    maximum_diff_lines: int = Field(default=1000, ge=1, le=1000)
    allow_dependency_changes: bool = False

    @field_validator("repository_path")
    @classmethod
    def repository_path_is_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("repository path must be absolute")
        return value


class WorkspaceRequest(CodingRecord):
    task_run_id: UUID
    repository: RepositoryReference
    idempotency_key: Sha256Hex


class WorkspaceDescriptor(CodingRecord):
    workspace_id: UUID
    task_run_id: UUID
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    workspace_revision: int = Field(ge=0)
    state: WorkspaceState
    logical_name: NonEmptyStr
    created_at: UtcDatetime
    mount_descriptor_hash: Sha256Hex | None = None


class WorkspaceIntegritySnapshot(CodingRecord):
    workspace_id: UUID
    workspace_revision: int = Field(ge=0)
    git_head: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    status_hash: Sha256Hex
    file_manifest_hash: Sha256Hex
    captured_at: UtcDatetime


class WorkspaceCleanupResult(CodingRecord):
    workspace_id: UUID
    disposition: WorkspaceDisposition
    completed: bool
    archive_artifact: ArtifactRef | None = None
    error: ErrorInfo | None = None


class RepositoryFileEntry(CodingRecord):
    path: RelativeRepositoryPath
    size_bytes: int = Field(ge=0)
    content_hash: Sha256Hex | None = None
    file_type: NonEmptyStr
    language: str | None = None
    generated: bool = False
    binary: bool = False
    test_file: bool = False
    configuration: bool = False
    symlink: bool = False
    ignored_reason: str | None = None


class ImportEntry(CodingRecord):
    module: NonEmptyStr
    names: tuple[NonEmptyStr, ...] = ()
    line: int = Field(ge=1)


class PythonSymbolEntry(CodingRecord):
    name: NonEmptyStr
    kind: NonEmptyStr
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    decorators: tuple[NonEmptyStr, ...] = ()
    has_docstring: bool = False

    @model_validator(mode="after")
    def ordered_lines(self) -> PythonSymbolEntry:
        if self.end_line < self.start_line:
            raise ValueError("symbol end line precedes start line")
        return self


class PythonModuleEntry(CodingRecord):
    path: RelativeRepositoryPath
    module: NonEmptyStr
    symbols: tuple[PythonSymbolEntry, ...] = ()
    imports: tuple[ImportEntry, ...] = ()
    exported_names: tuple[NonEmptyStr, ...] = ()
    parse_error: str | None = None


class RepositoryIndex(CodingRecord):
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    workspace_revision: int = Field(ge=0)
    files: tuple[RepositoryFileEntry, ...]
    modules: tuple[PythonModuleEntry, ...] = ()
    warnings: tuple[NonEmptyStr, ...] = ()
    truncated: bool = False
    total_files_seen: int = Field(ge=0)
    total_bytes_indexed: int = Field(ge=0)

    @model_validator(mode="after")
    def deterministic_order(self) -> RepositoryIndex:
        if [item.path for item in self.files] != sorted(item.path for item in self.files):
            raise ValueError("repository files must be sorted")
        if [item.path for item in self.modules] != sorted(item.path for item in self.modules):
            raise ValueError("Python modules must be sorted")
        return self


class RepositorySearchRequest(CodingRecord):
    query: Annotated[str, Field(min_length=1, max_length=256)]
    regex: bool = False
    path_filters: tuple[RelativeRepositoryPath, ...] = ()
    maximum_results: int = Field(default=200, ge=1, le=200)


class RepositorySearchResult(CodingRecord):
    path: RelativeRepositoryPath
    line: int = Field(ge=1)
    text: str = Field(max_length=2000)


class RepositoryContextBundle(CodingRecord):
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    workspace_revision: int = Field(ge=0)
    index_hash: Sha256Hex
    profile_summary: dict[str, JsonValue]
    search_results: tuple[RepositorySearchResult, ...] = ()
    excerpts: tuple[dict[str, JsonValue], ...] = ()
    exclusions: tuple[NonEmptyStr, ...] = ()
    truncated: bool = False


class CodingPatchPlan(CodingRecord):
    summary: NonEmptyStr
    target_files: tuple[RelativeRepositoryPath, ...] = Field(min_length=1, max_length=20)
    intended_changes: tuple[NonEmptyStr, ...] = Field(min_length=1)
    tests_to_run: tuple[tuple[NonEmptyStr, ...], ...] = ()
    risks: tuple[NonEmptyStr, ...] = ()
    dependency_changes_requested: bool = False

    @field_validator("target_files")
    @classmethod
    def unique_targets(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("patch plan target files must be unique")
        return values


class PatchProposal(CodingRecord):
    expected_workspace_revision: int = Field(ge=0)
    plan_hash: Sha256Hex
    unified_diff: str = Field(min_length=1, max_length=2_000_000)
    target_files: tuple[RelativeRepositoryPath, ...] = Field(min_length=1, max_length=20)
    rationale: NonEmptyStr


class ChangedFile(CodingRecord):
    path: RelativeRepositoryPath
    change_type: ChangeType
    before_hash: Sha256Hex | None = None
    after_hash: Sha256Hex | None = None
    added_lines: int = Field(default=0, ge=0)
    deleted_lines: int = Field(default=0, ge=0)


class ChangedFileManifest(CodingRecord):
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    workspace_revision: int = Field(ge=0)
    files: tuple[ChangedFile, ...]
    total_diff_lines: int = Field(ge=0)

    @model_validator(mode="after")
    def sorted_and_consistent(self) -> ChangedFileManifest:
        if [item.path for item in self.files] != sorted(item.path for item in self.files):
            raise ValueError("changed files must be sorted")
        calculated = sum(item.added_lines + item.deleted_lines for item in self.files)
        if calculated != self.total_diff_lines:
            raise ValueError("diff line count does not match changed files")
        return self


class PatchApplicationResult(CodingRecord):
    applied: bool
    reason_code: str | None = None
    workspace_revision: int = Field(ge=0)
    manifest: ChangedFileManifest | None = None
    diff_hash: Sha256Hex | None = None


class PatchAttempt(CodingRecord):
    attempt_number: int = Field(ge=1, le=3)
    repair_cycle: int = Field(ge=0, le=3)
    proposal_hash: Sha256Hex
    status: PatchAttemptStatus
    application_result: PatchApplicationResult | None = None
    recorded_at: UtcDatetime


class UnifiedDiffArtifact(CodingRecord):
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    diff_hash: Sha256Hex
    artifact: ArtifactRef
    truncated: bool = False


class CodingCommandReport(CodingRecord):
    command_identity: NonEmptyStr
    argv_hash: Sha256Hex
    sandbox_digest: NonEmptyStr
    started_at: UtcDatetime
    finished_at: UtcDatetime
    status: CodingCommandStatus
    exit_code: int | None = None
    timed_out: bool = False
    stdout_artifact: ArtifactRef | None = None
    stderr_artifact: ArtifactRef | None = None
    truncated: bool = False
    resource_usage: dict[str, float] = Field(default_factory=dict)
    baseline_status: CodingCommandStatus | None = None
    error: ErrorInfo | None = None


class CodingVerificationSummary(CodingRecord):
    focused_bundles: tuple[VerificationBundle, ...] = ()
    full_bundle: VerificationBundle | None = None
    registry_snapshot_hash: Sha256Hex
    required_criteria_resolved: bool


class ManualReviewNote(CodingRecord):
    category: NonEmptyStr
    message: NonEmptyStr
    advisory: bool = True


class RiskRecord(CodingRecord):
    code: NonEmptyStr
    message: NonEmptyStr
    severity: NonEmptyStr
    mitigated: bool = False


class CodingOutcome(CodingRecord):
    task_run_id: UUID
    status: CodingOutcomeStatus
    repository_profile: RepositoryProfile
    base_commit: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
    patch_attempts: tuple[PatchAttempt, ...] = ()
    changed_files: ChangedFileManifest | None = None
    verification: CodingVerificationSummary | None = None
    acceptance_decision: AcceptanceDecision | None = None
    command_reports: tuple[CodingCommandReport, ...] = ()
    provider_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    elapsed_seconds: float = Field(default=0, ge=0)
    policy_denials: tuple[NonEmptyStr, ...] = ()
    risks: tuple[RiskRecord, ...] = ()
    manual_review_notes: tuple[ManualReviewNote, ...] = ()
    workspace_disposition: WorkspaceDisposition
    completed_at: UtcDatetime

    @model_validator(mode="after")
    def accepted_requires_decision(self) -> CodingOutcome:
        if self.status is CodingOutcomeStatus.ACCEPTED and (
            self.acceptance_decision is None
            or self.acceptance_decision.decision.value != "accepted"
        ):
            raise ValueError("accepted coding outcome requires an accepted decision")
        return self


class CodingTrajectoryPackage(CodingRecord):
    problem: CodingProblemExtension
    repository_profile: RepositoryProfile
    context_hash: Sha256Hex
    patch_plan: CodingPatchPlan | None = None
    patch_attempts: tuple[PatchAttempt, ...] = ()
    verifier_failures: tuple[dict[str, JsonValue], ...] = ()
    repair_decisions: tuple[dict[str, JsonValue], ...] = ()
    final_diff: UnifiedDiffArtifact | None = None
    acceptance_decision: AcceptanceDecision | None = None
    command_reports: tuple[CodingCommandReport, ...] = ()
    usage_metrics: dict[str, float] = Field(default_factory=dict)
    risks: tuple[RiskRecord, ...] = ()
    provenance: dict[str, JsonValue]


def command_hash(argv: tuple[str, ...]) -> str:
    """Hash a sealed argv vector for audit without invoking a shell."""
    if not argv or any(re.search(r"[|;&<>`\n\r]", value) for value in argv):
        raise ValueError("command contains shell syntax or is empty")
    return sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest()
