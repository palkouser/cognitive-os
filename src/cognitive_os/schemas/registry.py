"""Deterministic registry of public contract schemas."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

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
