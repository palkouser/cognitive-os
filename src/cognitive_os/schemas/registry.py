"""Deterministic registry of public contract schemas."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from cognitive_os.config.coding_config import CodingConfiguration
from cognitive_os.config.context_config import ContextConfiguration
from cognitive_os.config.memory_config import MemoryConfiguration
from cognitive_os.config.semantic_memory_config import SemanticMemoryConfiguration
from cognitive_os.config.skill_config import SkillConfiguration
from cognitive_os.domain import (
    ApprovalDecision,
    ApprovalRequest,
    ClarificationRequest,
    ClarificationResponse,
    ContinuationTokenRecord,
    ControllerBudget,
    ControllerDecision,
    ControllerExecutionPlan,
    ControllerStateSnapshot,
    ControllerUsage,
    ExecutionPlan,
    ExecutionStep,
    ModelCallRequestRecord,
    ModelCallResultRecord,
    ModelCapabilities,
    ModelProviderRequest,
    ModelProviderResponse,
    ProblemRepresentation,
    ProviderHealth,
    ProviderIdentity,
    ProviderStreamEvent,
    SandboxLimits,
    SandboxRequest,
    SandboxResult,
    Task,
    TaskRun,
    ToolCallRequestRecord,
    ToolCallResultRecord,
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolInvocation,
    ToolPolicyDecision,
    VerifierResult,
)
from cognitive_os.domain.acceptance import (
    AcceptanceDecision,
    AcceptancePolicy,
    CriterionEvaluation,
    VerifierRequirement,
)
from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkManifest,
    BenchmarkResourceBudget,
    BenchmarkRun,
)
from cognitive_os.domain.coding import (
    ChangedFileManifest,
    CodingCommandPolicy,
    CodingCommandReport,
    CodingLimits,
    CodingOutcome,
    CodingPatchPlan,
    CodingProblemExtension,
    CodingTrajectoryPackage,
    CodingVerificationSummary,
    DependencyChangePolicy,
    PatchApplicationResult,
    PatchAttempt,
    PatchProposal,
    PathPolicy,
    RepositoryContextBundle,
    RepositoryFileEntry,
    RepositoryIndex,
    RepositoryProfile,
    RepositoryProfileMismatch,
    RepositorySearchRequest,
    RepositorySearchResult,
    UnifiedDiffArtifact,
    WorkspaceCleanupResult,
    WorkspaceDescriptor,
    WorkspaceIntegritySnapshot,
    WorkspaceRequest,
)
from cognitive_os.domain.context import PUBLIC_CONTEXT_CONTRACTS
from cognitive_os.domain.memory import PUBLIC_MEMORY_CONTRACTS
from cognitive_os.domain.semantic_memory import PUBLIC_SEMANTIC_CONTRACTS
from cognitive_os.domain.skills import PUBLIC_SKILL_CONTRACTS
from cognitive_os.domain.verifiers import (
    VerificationBundle,
    VerificationExecution,
    VerificationRequest,
    VerificationSubject,
    VerifierCapability,
    VerifierDescriptor,
)
from cognitive_os.events.base import EventEnvelope
from cognitive_os.events.catalog import DEFAULT_EVENT_MODELS


@dataclass(frozen=True)
class SchemaEntry:
    model: type[BaseModel]
    path: str
    event_type: str | None = None
    schema_version: int | None = None


DOMAIN_SCHEMAS: tuple[tuple[type[BaseModel], str], ...] = (
    (CodingConfiguration, "v1/config/coding-configuration.schema.json"),
    (ContextConfiguration, "v1/config/context-configuration.schema.json"),
    (MemoryConfiguration, "v1/config/memory-configuration.schema.json"),
    (SemanticMemoryConfiguration, "v1/config/semantic-memory-configuration.schema.json"),
    (SkillConfiguration, "v1/config/skill-configuration.schema.json"),
    *tuple(
        (
            model,
            "v1/context/"
            + "".join(
                ("-" + character.lower()) if character.isupper() else character
                for character in model.__name__
            ).lstrip("-")
            + ".schema.json",
        )
        for model in PUBLIC_CONTEXT_CONTRACTS
    ),
    *tuple(
        (
            model,
            "v1/memory/"
            + "".join(
                ("-" + character.lower()) if character.isupper() else character
                for character in model.__name__
            ).lstrip("-")
            + ".schema.json",
        )
        for model in PUBLIC_MEMORY_CONTRACTS
    ),
    *tuple(
        (
            model,
            "v1/semantic-memory/"
            + "".join(
                ("-" + character.lower()) if character.isupper() else character
                for character in model.__name__
            ).lstrip("-")
            + ".schema.json",
        )
        for model in PUBLIC_SEMANTIC_CONTRACTS
    ),
    *tuple(
        (
            model,
            "v1/skills/"
            + "".join(
                ("-" + character.lower()) if character.isupper() else character
                for character in model.__name__
            ).lstrip("-")
            + ".schema.json",
        )
        for model in PUBLIC_SKILL_CONTRACTS
    ),
    (CodingLimits, "v1/domain/coding-limits.schema.json"),
    (CodingCommandPolicy, "v1/domain/coding-command-policy.schema.json"),
    (PathPolicy, "v1/domain/path-policy.schema.json"),
    (DependencyChangePolicy, "v1/domain/dependency-change-policy.schema.json"),
    (CodingProblemExtension, "v1/domain/coding-problem-extension.schema.json"),
    (RepositoryProfileMismatch, "v1/domain/repository-profile-mismatch.schema.json"),
    (RepositoryProfile, "v1/domain/repository-profile.schema.json"),
    (WorkspaceRequest, "v1/domain/workspace-request.schema.json"),
    (WorkspaceDescriptor, "v1/domain/workspace-descriptor.schema.json"),
    (WorkspaceIntegritySnapshot, "v1/domain/workspace-integrity-snapshot.schema.json"),
    (WorkspaceCleanupResult, "v1/domain/workspace-cleanup-result.schema.json"),
    (RepositoryFileEntry, "v1/domain/repository-file-entry.schema.json"),
    (RepositoryIndex, "v1/domain/repository-index.schema.json"),
    (RepositorySearchRequest, "v1/domain/repository-search-request.schema.json"),
    (RepositorySearchResult, "v1/domain/repository-search-result.schema.json"),
    (RepositoryContextBundle, "v1/domain/repository-context-bundle.schema.json"),
    (CodingPatchPlan, "v1/domain/coding-patch-plan.schema.json"),
    (PatchProposal, "v1/domain/patch-proposal.schema.json"),
    (PatchApplicationResult, "v1/domain/patch-application-result.schema.json"),
    (PatchAttempt, "v1/domain/patch-attempt.schema.json"),
    (ChangedFileManifest, "v1/domain/changed-file-manifest.schema.json"),
    (UnifiedDiffArtifact, "v1/domain/unified-diff-artifact.schema.json"),
    (CodingCommandReport, "v1/domain/coding-command-report.schema.json"),
    (CodingVerificationSummary, "v1/domain/coding-verification-summary.schema.json"),
    (CodingOutcome, "v1/domain/coding-outcome.schema.json"),
    (CodingTrajectoryPackage, "v1/domain/coding-trajectory-package.schema.json"),
    (VerifierCapability, "v1/domain/verifier-capability.schema.json"),
    (VerifierDescriptor, "v1/domain/verifier-descriptor.schema.json"),
    (VerificationSubject, "v1/domain/verification-subject.schema.json"),
    (VerificationRequest, "v1/domain/verification-request.schema.json"),
    (VerificationExecution, "v1/domain/verification-execution.schema.json"),
    (VerificationBundle, "v1/domain/verification-bundle.schema.json"),
    (VerifierRequirement, "v1/domain/verifier-requirement.schema.json"),
    (AcceptancePolicy, "v1/domain/acceptance-policy.schema.json"),
    (CriterionEvaluation, "v1/domain/criterion-evaluation.schema.json"),
    (AcceptanceDecision, "v1/domain/acceptance-decision.schema.json"),
    (BenchmarkResourceBudget, "v1/domain/benchmark-resource-budget.schema.json"),
    (BenchmarkCase, "v1/domain/benchmark-case.schema.json"),
    (BenchmarkManifest, "v1/domain/benchmark-manifest.schema.json"),
    (BenchmarkCaseResult, "v1/domain/benchmark-case-result.schema.json"),
    (BenchmarkRun, "v1/domain/benchmark-run.schema.json"),
    (ApprovalDecision, "v1/domain/approval-decision.schema.json"),
    (ApprovalRequest, "v1/domain/approval-request.schema.json"),
    (ProblemRepresentation, "v1/domain/problem-representation.schema.json"),
    (ControllerBudget, "v1/domain/controller-budget.schema.json"),
    (ControllerUsage, "v1/domain/controller-usage.schema.json"),
    (ControllerDecision, "v1/domain/controller-decision.schema.json"),
    (ControllerStateSnapshot, "v1/domain/controller-state-snapshot.schema.json"),
    (ControllerExecutionPlan, "v1/domain/controller-execution-plan.schema.json"),
    (ClarificationRequest, "v1/domain/clarification-request.schema.json"),
    (ClarificationResponse, "v1/domain/clarification-response.schema.json"),
    (ContinuationTokenRecord, "v1/domain/continuation-token-record.schema.json"),
    (Task, "v1/domain/task.schema.json"),
    (TaskRun, "v1/domain/task-run.schema.json"),
    (ExecutionPlan, "v1/domain/execution-plan.schema.json"),
    (ExecutionStep, "v1/domain/execution-step.schema.json"),
    (ModelCallRequestRecord, "v1/domain/model-call-request.schema.json"),
    (ModelCallResultRecord, "v1/domain/model-call-result.schema.json"),
    (ModelProviderRequest, "v1/domain/model-provider-request.schema.json"),
    (ModelProviderResponse, "v1/domain/model-provider-response.schema.json"),
    (ProviderIdentity, "v1/domain/provider-identity.schema.json"),
    (ModelCapabilities, "v1/domain/model-capabilities.schema.json"),
    (ProviderHealth, "v1/domain/provider-health.schema.json"),
    (ProviderStreamEvent, "v1/domain/provider-stream-event.schema.json"),
    (ToolCallRequestRecord, "v1/domain/tool-call-request.schema.json"),
    (ToolCallResultRecord, "v1/domain/tool-call-result.schema.json"),
    (ToolDescriptor, "v1/domain/tool-descriptor.schema.json"),
    (ToolExecutionContext, "v1/domain/tool-execution-context.schema.json"),
    (ToolExecutionResult, "v1/domain/tool-execution-result.schema.json"),
    (ToolInvocation, "v1/domain/tool-invocation.schema.json"),
    (ToolPolicyDecision, "v1/domain/tool-policy-decision.schema.json"),
    (SandboxLimits, "v1/domain/sandbox-limits.schema.json"),
    (SandboxRequest, "v1/domain/sandbox-request.schema.json"),
    (SandboxResult, "v1/domain/sandbox-result.schema.json"),
    (VerifierResult, "v1/domain/verifier-result.schema.json"),
    (EventEnvelope, "v1/events/event-envelope.schema.json"),
)


def build_schema_registry() -> tuple[SchemaEntry, ...]:
    entries = [SchemaEntry(model=model, path=path) for model, path in DOMAIN_SCHEMAS]
    entries.extend(
        SchemaEntry(
            model=model,
            path=f"v1/events/{model.event_type}.v{model.schema_version}.schema.json",
            event_type=model.event_type,
            schema_version=model.schema_version,
        )
        for model in DEFAULT_EVENT_MODELS
    )
    return tuple(sorted(entries, key=lambda entry: entry.path))
