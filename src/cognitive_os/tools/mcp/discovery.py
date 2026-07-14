"""Explicit MCP discovery and Tool Registry integration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
)

from ..registry import ToolRegistry
from .client import McpStdioClient
from .mapping import map_mcp_tool


class McpToolAdapter:
    def __init__(
        self, descriptor: ToolDescriptor, remote_name: str, client: McpStdioClient
    ) -> None:
        self.descriptor = descriptor
        self._remote_name = remote_name
        self._client = client

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        started = datetime.now(UTC)
        response: Any = await self._client.call_tool(
            self._remote_name, cast(dict[str, object], invocation.arguments)
        )
        if getattr(response, "isError", False):
            raise RuntimeError("MCP tool returned an error")
        content = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item)
            for item in response.content
        ]
        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            tool_id=invocation.tool_id,
            tool_version=invocation.tool_version,
            status=ToolExecutionStatus.COMPLETED,
            started_at=started,
            finished_at=datetime.now(UTC),
            result={"content": cast(list[JsonValue], content)},
        )


async def discover_into_registry(
    server_id: str, client: McpStdioClient, registry: ToolRegistry
) -> tuple[str, ...]:
    response: Any = await client.list_tools()
    registered: list[str] = []
    for tool in response.tools:
        schema = cast(dict[str, JsonValue], tool.inputSchema)
        descriptor = map_mcp_tool(server_id, tool.name, tool.description, schema)
        registry.register(McpToolAdapter(descriptor, tool.name, client))
        registered.append(descriptor.tool_id)
    return tuple(registered)
