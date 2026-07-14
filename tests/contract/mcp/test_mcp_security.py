from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.tools.errors import ToolValidationError
from cognitive_os.tools.mcp.config import McpServerConfiguration
from cognitive_os.tools.mcp.mapping import map_mcp_tool


def test_mcp_requires_absolute_non_installer_command(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        McpServerConfiguration(command=Path("server"), working_directory=tmp_path)
    with pytest.raises(ValidationError):
        McpServerConfiguration(command=Path("/usr/bin/npx"), working_directory=tmp_path)


def test_mcp_tools_default_to_r2_and_reject_remote_schema() -> None:
    descriptor = map_mcp_tool("local-test", "echo", "untrusted", {"type": "object"})
    assert descriptor.tool_id == "mcp.local-test.echo"
    assert descriptor.risk_level.value == "r2"
    assert descriptor.provider_visible is False
    with pytest.raises(ToolValidationError):
        map_mcp_tool("server", "bad", None, {"type": "object", "$ref": "https://evil.test"})
