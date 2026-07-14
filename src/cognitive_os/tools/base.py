"""Helpers shared by built-in tools."""

from datetime import UTC, datetime

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.tools import ToolExecutionResult, ToolExecutionStatus, ToolInvocation


def completed(
    invocation: ToolInvocation, started_at: datetime, result: JsonValue
) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool_call_id=invocation.tool_call_id,
        tool_id=invocation.tool_id,
        tool_version=invocation.tool_version,
        status=ToolExecutionStatus.COMPLETED,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        exit_code=0,
        result=result,
    )
