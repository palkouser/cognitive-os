"""Deterministic approval providers for interactive and automated contexts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from cognitive_os.domain.approvals import ApprovalDecision, ApprovalDecisionType, ApprovalRequest


class DenyAllApprovalProvider:
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        return ApprovalDecision(
            approval_id=request.approval_id,
            decision=ApprovalDecisionType.DENY,
            decided_at=datetime.now(UTC),
            decided_by="deny-all",
            reason="approval is unavailable",
            task_run_id=request.task_run_id,
            tool_id=request.tool_id,
            tool_version=request.tool_version,
        )

    async def get_existing_task_approval(
        self, task_run_id: UUID, tool_id: str, tool_version: str, argument_hash: str
    ) -> ApprovalDecision | None:
        return None

    async def record_decision(self, decision: ApprovalDecision) -> None:
        return None


class PreconfiguredApprovalProvider(DenyAllApprovalProvider):
    def __init__(self, decisions: dict[UUID, ApprovalDecision]) -> None:
        self._decisions = decisions

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        return self._decisions.get(request.approval_id) or await super().request_approval(request)

    async def record_decision(self, decision: ApprovalDecision) -> None:
        self._decisions[decision.approval_id] = decision

    async def get_existing_task_approval(
        self, task_run_id: UUID, tool_id: str, tool_version: str, argument_hash: str
    ) -> ApprovalDecision | None:
        now = datetime.now(UTC)
        return next(
            (
                decision
                for decision in self._decisions.values()
                if decision.decision is ApprovalDecisionType.ALLOW_FOR_TASK
                and decision.task_run_id == task_run_id
                and decision.tool_id == tool_id
                and decision.tool_version == tool_version
                and decision.argument_hash in {None, argument_hash}
                and (decision.expires_at is None or decision.expires_at > now)
            ),
            None,
        )


class ConsoleApprovalProvider(PreconfiguredApprovalProvider):
    """Explicit interactive provider; never construct this provider in CI."""

    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        prompt = f"Approve {request.tool_id}@{request.tool_version} for this invocation? [y/N] "
        answer = await asyncio.to_thread(input, prompt)
        decision = (
            ApprovalDecisionType.ALLOW_ONCE
            if answer.strip().lower() == "y"
            else ApprovalDecisionType.DENY
        )
        return ApprovalDecision(
            approval_id=request.approval_id,
            decision=decision,
            decided_at=datetime.now(UTC),
            decided_by="console-operator",
            reason="explicit console decision",
            task_run_id=request.task_run_id,
            tool_id=request.tool_id,
            tool_version=request.tool_version,
        )
