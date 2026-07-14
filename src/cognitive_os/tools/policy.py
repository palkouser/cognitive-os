"""Deterministic deny-first Tool Plane policy."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cognitive_os.domain.approvals import PolicyAction, ToolPolicyDecision
from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionMode,
    ToolInvocation,
    ToolRiskLevel,
)


class ToolPolicyEngine:
    def __init__(self, workspace_roots: tuple[Path, ...], enabled_tools: frozenset[str]) -> None:
        self._roots = tuple(root.resolve() for root in workspace_roots)
        self._enabled = enabled_tools

    async def evaluate(
        self, invocation: ToolInvocation, descriptor: ToolDescriptor
    ) -> ToolPolicyDecision:
        if descriptor.tool_id not in self._enabled:
            return self._decision(
                PolicyAction.DENY, "tool.disabled", "tool is disabled", descriptor
            )
        if invocation.tool_version != descriptor.version:
            return self._decision(
                PolicyAction.DENY, "tool.version", "tool version mismatch", descriptor
            )
        if descriptor.risk_level is ToolRiskLevel.R3:
            return self._decision(PolicyAction.DENY, "risk.r3", "R3 tools are denied", descriptor)
        if (
            descriptor.risk_level is ToolRiskLevel.R1
            and descriptor.execution_mode is not ToolExecutionMode.SANDBOX
        ):
            return self._decision(
                PolicyAction.DENY, "risk.r1.host", "R1 tools require sandbox execution", descriptor
            )
        path = invocation.arguments.get("path")
        if isinstance(path, str) and not self.path_is_allowed(path):
            return self._decision(
                PolicyAction.DENY, "path.scope", "path is outside configured roots", descriptor
            )
        if descriptor.risk_level is ToolRiskLevel.R2:
            return self._decision(
                PolicyAction.REQUIRE_APPROVAL, "risk.r2", "R2 requires approval", descriptor
            )
        return self._decision(
            PolicyAction.ALLOW, "risk.default", "tool is allowed by default policy", descriptor
        )

    def path_is_allowed(self, value: str) -> bool:
        candidate = Path(value).resolve()
        return any(candidate == root or candidate.is_relative_to(root) for root in self._roots)

    @staticmethod
    def _decision(
        action: PolicyAction, rule: str, reason: str, descriptor: ToolDescriptor
    ) -> ToolPolicyDecision:
        return ToolPolicyDecision(
            action=action,
            rule_id=rule,
            reason=reason,
            risk_level=descriptor.risk_level,
            evaluated_at=datetime.now(UTC),
            required_approval=action is PolicyAction.REQUIRE_APPROVAL,
        )
