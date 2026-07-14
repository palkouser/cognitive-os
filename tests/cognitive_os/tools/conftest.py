from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionMode,
    ToolInvocation,
    ToolRiskLevel,
    ToolSideEffect,
    ToolSource,
)


@pytest.fixture
def descriptor() -> ToolDescriptor:
    return ToolDescriptor(
        tool_id="test.echo",
        version="1",
        display_name="Echo",
        description="Echo a value.",
        source=ToolSource.BUILT_IN,
        input_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        risk_level=ToolRiskLevel.R0,
        side_effects=(ToolSideEffect.NONE,),
        execution_mode=ToolExecutionMode.HOST_READ_ONLY,
        provider_visible=True,
        idempotent=True,
        deterministic=True,
        default_timeout_seconds=5,
    )


@pytest.fixture
def invocation(tmp_path: Path) -> ToolInvocation:
    return ToolInvocation(
        tool_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        tool_id="test.echo",
        tool_version="1",
        arguments={"value": "hello"},
        requested_at=datetime.now(UTC),
        requested_by="test",
    )


@pytest.fixture
def context(tmp_path: Path) -> ToolExecutionContext:
    return ToolExecutionContext(
        workspace=str(tmp_path),
        timeout_seconds=5,
        maximum_stdout_bytes=1024,
        maximum_stderr_bytes=1024,
        maximum_artifact_bytes=4096,
    )
