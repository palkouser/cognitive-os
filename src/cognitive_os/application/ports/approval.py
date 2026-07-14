"""Approval persistence and decision boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.approvals import ApprovalDecision, ApprovalRequest


class ApprovalPort(Protocol):
    async def request_approval(self, request: ApprovalRequest) -> ApprovalDecision: ...
    async def get_existing_task_approval(
        self, task_run_id: UUID, tool_id: str, tool_version: str, argument_hash: str
    ) -> ApprovalDecision | None: ...
    async def record_decision(self, decision: ApprovalDecision) -> None: ...
