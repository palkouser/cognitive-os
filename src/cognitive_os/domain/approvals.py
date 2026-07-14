"""Tool policy and approval contracts."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import ImmutableContractModel
from .common import JsonValue
from .tools import ToolRiskLevel, ToolSideEffect


class PolicyAction(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class ApprovalDecisionType(StrEnum):
    ALLOW_ONCE = "allow_once"
    ALLOW_FOR_TASK = "allow_for_task"
    DENY = "deny"
    DENY_AND_BLOCK_RULE = "deny_and_block_rule"


class ToolPolicyDecision(ImmutableContractModel):
    action: PolicyAction
    rule_id: str
    reason: str
    risk_level: ToolRiskLevel
    evaluated_at: datetime
    required_approval: bool = False
    effective_limits: dict[str, JsonValue] = Field(default_factory=dict)


class ApprovalRequest(ImmutableContractModel):
    approval_id: UUID
    tool_call_id: UUID
    task_run_id: UUID
    tool_id: str
    tool_version: str
    arguments_summary: dict[str, JsonValue]
    risk_level: ToolRiskLevel
    side_effects: tuple[ToolSideEffect, ...]
    filesystem_scope: tuple[str, ...] = ()
    network_scope: tuple[str, ...] = ()
    reason: str
    requested_at: datetime


class ApprovalDecision(ImmutableContractModel):
    approval_id: UUID
    decision: ApprovalDecisionType
    decided_at: datetime
    decided_by: str
    reason: str
    task_run_id: UUID
    tool_id: str
    tool_version: str
    argument_hash: str | None = None
    expires_at: datetime | None = None
