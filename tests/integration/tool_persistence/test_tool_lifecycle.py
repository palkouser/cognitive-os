from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from cognitive_os.application.services.approval_service import DenyAllApprovalProvider
from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.domain.approvals import PolicyAction, ToolPolicyDecision
from cognitive_os.domain.tools import ToolExecutionContext, ToolInvocation
from cognitive_os.events.tool_event_service import ToolEventService
from cognitive_os.tools.host import FilesystemTool
from cognitive_os.tools.registry import ToolRegistry


class MemoryEventStore:
    def __init__(self) -> None:
        self.events = []

    async def get_stream_version(self, stream_id):
        return len(self.events) or None

    async def append(self, events, *, expected_version):
        assert expected_version == len(self.events)
        self.events.extend(events)
        return object()


class StaticPolicy:
    def __init__(self, action: PolicyAction) -> None:
        self.action = action

    async def evaluate(self, invocation, descriptor):
        return ToolPolicyDecision(
            action=self.action,
            rule_id="test",
            reason="test decision",
            risk_level=descriptor.risk_level,
            evaluated_at=datetime.now(UTC),
            required_approval=self.action is PolicyAction.REQUIRE_APPROVAL,
        )


@pytest.mark.asyncio
async def test_denied_tool_has_no_started_event(tmp_path: Path) -> None:
    invocation = ToolInvocation(
        tool_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        tool_id="filesystem.read",
        tool_version="1",
        arguments={"path": str(tmp_path / "safe.txt")},
        requested_at=datetime.now(UTC),
        requested_by="test",
    )
    context = ToolExecutionContext(
        workspace=str(tmp_path),
        timeout_seconds=5,
        maximum_stdout_bytes=100,
        maximum_stderr_bytes=100,
        maximum_artifact_bytes=100,
    )
    registry = ToolRegistry()
    registry.register(FilesystemTool("read", (tmp_path,)))
    store = MemoryEventStore()
    result = await ToolExecutionService(
        registry,
        StaticPolicy(PolicyAction.DENY),
        DenyAllApprovalProvider(),
        ToolEventService(store),
    ).execute(invocation, context)
    assert result.status.value == "denied"
    assert [event.event_type for event in store.events] == [
        "tool_call.requested",
        "tool_call.denied",
    ]
