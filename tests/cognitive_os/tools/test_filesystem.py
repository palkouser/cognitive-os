from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.domain.tools import ToolExecutionContext, ToolInvocation
from cognitive_os.tools.errors import ToolPolicyError
from cognitive_os.tools.host import FilesystemTool


@pytest.mark.asyncio
async def test_filesystem_read_is_bounded_and_cannot_escape(tmp_path: Path) -> None:
    target = tmp_path / "safe.txt"
    target.write_text("hello", encoding="utf-8")
    tool = FilesystemTool("read", (tmp_path,), maximum_bytes=4)
    context = ToolExecutionContext(
        workspace=str(tmp_path),
        timeout_seconds=5,
        maximum_stdout_bytes=100,
        maximum_stderr_bytes=100,
        maximum_artifact_bytes=100,
    )

    def invocation(path: str) -> ToolInvocation:
        return ToolInvocation(
            tool_call_id=uuid4(),
            task_run_id=uuid4(),
            correlation_id=uuid4(),
            tool_id="filesystem.read",
            tool_version="1",
            arguments={"path": path},
            requested_at=datetime.now(UTC),
            requested_by="test",
        )

    result = await tool.execute(invocation(str(target)), context)
    assert result.result == {"content": "hell", "truncated": True}
    with pytest.raises(ToolPolicyError):
        await tool.execute(invocation("/etc/passwd"), context)
