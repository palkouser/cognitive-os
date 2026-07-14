import os
import sys
from pathlib import Path

import pytest

from cognitive_os.tools.mcp.client import McpStdioClient
from cognitive_os.tools.mcp.config import McpServerConfiguration
from cognitive_os.tools.mcp.discovery import discover_into_registry
from cognitive_os.tools.registry import ToolRegistry


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("COGOS_RUN_MCP_INTEGRATION") != "1", reason="opt-in STDIO subprocess test"
)
async def test_explicit_stdio_server_discovery_and_call() -> None:
    root = Path.cwd()
    client = McpStdioClient(
        McpServerConfiguration(
            enabled=True,
            command=Path(sys.executable),
            arguments=(str(root / "tests/fixtures/mcp/echo_server.py"),),
            working_directory=root,
            environment_allowlist=(),
        )
    )
    try:
        await client.start()
        tools = await client.list_tools()
        assert [tool.name for tool in tools.tools] == ["echo"]
        registry = ToolRegistry()
        assert await discover_into_registry("local-test", client, registry) == (
            "mcp.local-test.echo",
        )
        assert registry.list_all()[0].risk_level.value == "r2"
        result = await client.call_tool("echo", {"value": "safe"})
        assert result.isError is False
        assert len(result.content) == 1
    finally:
        await client.close()
