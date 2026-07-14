from pathlib import Path

import pytest

from cognitive_os.domain.approvals import PolicyAction
from cognitive_os.domain.tools import ToolExecutionMode, ToolRiskLevel
from cognitive_os.tools.policy import ToolPolicyEngine


@pytest.mark.asyncio
async def test_policy_denies_r3_and_path_escape(descriptor, invocation, tmp_path: Path) -> None:
    engine = ToolPolicyEngine((tmp_path,), frozenset({descriptor.tool_id}))
    r3 = descriptor.model_copy(update={"risk_level": ToolRiskLevel.R3, "descriptor_hash": ""})
    assert (await engine.evaluate(invocation, r3)).action is PolicyAction.DENY
    escaped = invocation.model_copy(update={"arguments": {"path": "/etc/passwd"}})
    assert (await engine.evaluate(escaped, descriptor)).action is PolicyAction.DENY


@pytest.mark.asyncio
async def test_policy_requires_approval_for_r2(descriptor, invocation, tmp_path: Path) -> None:
    engine = ToolPolicyEngine((tmp_path,), frozenset({descriptor.tool_id}))
    r2 = descriptor.model_copy(
        update={
            "risk_level": ToolRiskLevel.R2,
            "execution_mode": ToolExecutionMode.MCP,
            "descriptor_hash": "",
        }
    )
    assert (await engine.evaluate(invocation, r2)).action is PolicyAction.REQUIRE_APPROVAL
