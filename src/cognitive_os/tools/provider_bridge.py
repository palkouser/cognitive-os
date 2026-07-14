"""Normalized provider proposal to controlled Tool Plane bridge."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.domain.model_requests import (
    NormalizedToolCall,
    ProviderMessage,
    ProviderMessageRole,
    ProviderToolDefinition,
)
from cognitive_os.domain.tools import ToolExecutionContext, ToolInvocation

from .registry import ToolRegistry


class ProviderToolBridge:
    def __init__(self, registry: ToolRegistry, execution: ToolExecutionService) -> None:
        self._registry = registry
        self._execution = execution

    def definitions(self) -> tuple[ProviderToolDefinition, ...]:
        return tuple(
            ProviderToolDefinition(
                name=item.tool_id, description=item.description, input_schema=item.input_schema
            )
            for item in self._registry.list_provider_visible()
        )

    async def execute_sequentially(
        self,
        calls: tuple[NormalizedToolCall, ...],
        *,
        task_run_id: UUID,
        correlation_id: UUID,
        context: ToolExecutionContext,
    ) -> tuple[ProviderMessage, ...]:
        messages: list[ProviderMessage] = []
        for call in calls:
            tool = next(
                (
                    item
                    for item in self._registry.list_provider_visible()
                    if item.tool_id == call.name
                ),
                None,
            )
            if tool is None:
                raise ValueError("provider proposed an unavailable tool")
            result = await self._execution.execute(
                ToolInvocation(
                    tool_call_id=uuid5(NAMESPACE_URL, call.tool_call_id),
                    task_run_id=task_run_id,
                    correlation_id=correlation_id,
                    tool_id=tool.tool_id,
                    tool_version=tool.version,
                    arguments=call.arguments,
                    requested_at=datetime.now(UTC),
                    requested_by="provider",
                ),
                context,
            )
            messages.append(
                ProviderMessage(
                    role=ProviderMessageRole.TOOL,
                    content=str(result.result),
                    tool_call_id=call.tool_call_id,
                )
            )
        return tuple(messages)
