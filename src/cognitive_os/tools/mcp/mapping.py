"""Untrusted MCP metadata normalization."""

import re

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionMode,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)
from cognitive_os.tools.validation import validate_schema


def map_mcp_tool(
    server_id: str, name: str, description: str | None, schema: dict[str, JsonValue]
) -> ToolDescriptor:
    safe_server = re.sub(r"[^a-z0-9_-]", "-", server_id.lower())
    safe_name = re.sub(r"[^a-z0-9_-]", "-", name.lower())
    validate_schema(schema)
    return ToolDescriptor(
        tool_id=f"mcp.{safe_server}.{safe_name}",
        version="1",
        display_name=name[:120],
        description=(description or "MCP tool")[:4000],
        source=ToolSource.MCP,
        input_schema=schema,
        output_schema={"type": "object"},
        risk_level=ToolRiskLevel.R2,
        side_effects=(ToolSideEffect.NETWORK_WRITE,),
        execution_mode=ToolExecutionMode.MCP,
        provider_visible=False,
        default_timeout_seconds=60,
    )
