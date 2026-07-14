from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from cognitive_os.domain.approvals import PolicyAction, ToolPolicyDecision
from cognitive_os.domain.sandbox import SandboxLimits
from cognitive_os.domain.tools import ToolDescriptor, ToolExecutionMode, ToolRiskLevel, ToolSource


def test_tool_contracts_are_strict_and_deterministic() -> None:
    with pytest.raises(ValidationError):
        SandboxLimits(
            timeout_seconds=1,
            memory_bytes=134_217_728,
            cpu_count=1,
            pid_limit=16,
            maximum_stdout_bytes=1,
            maximum_stderr_bytes=1,
            maximum_artifact_bytes=1,
            network_enabled=True,
            unknown=True,
        )
    decision = ToolPolicyDecision(
        action=PolicyAction.DENY,
        rule_id="test",
        reason="denied",
        risk_level=ToolRiskLevel.R3,
        evaluated_at=datetime.now(UTC),
    )
    assert decision.required_approval is False


def test_tool_descriptor_rejects_non_namespaced_id() -> None:
    with pytest.raises(ValidationError):
        ToolDescriptor(
            tool_id="shell",
            version="1",
            display_name="Shell",
            description="Forbidden shell.",
            source=ToolSource.BUILT_IN,
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            risk_level=ToolRiskLevel.R3,
            execution_mode=ToolExecutionMode.SANDBOX,
            default_timeout_seconds=1,
        )
