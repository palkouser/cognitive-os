"""Deterministic registry of public contract schemas."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from cognitive_os.domain import (
    ExecutionPlan,
    ExecutionStep,
    ModelCallRequestRecord,
    ModelCallResultRecord,
    ModelCapabilities,
    ModelProviderRequest,
    ModelProviderResponse,
    ProviderHealth,
    ProviderIdentity,
    ProviderStreamEvent,
    Task,
    TaskRun,
    ToolCallRequestRecord,
    ToolCallResultRecord,
    VerifierResult,
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
