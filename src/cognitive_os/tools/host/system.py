"""Non-sensitive system information tool."""

import platform
from datetime import UTC, datetime

from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolExecutionResult,
    ToolInvocation,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)

from ..base import completed


class SystemInfoTool:
    descriptor = ToolDescriptor(
        tool_id="system.info",
        version="1",
        display_name="System information",
        description="Return non-sensitive operating system and Python information.",
        source=ToolSource.BUILT_IN,
        input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        output_schema={"type": "object"},
        risk_level=ToolRiskLevel.R0,
        side_effects=(ToolSideEffect.LOCAL_READ,),
        execution_mode=ToolExecutionMode.HOST_READ_ONLY,
        provider_visible=True,
        idempotent=True,
        deterministic=True,
        default_timeout_seconds=5,
    )

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        return completed(
            invocation,
            datetime.now(UTC),
            {
                "system": platform.system(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
        )
