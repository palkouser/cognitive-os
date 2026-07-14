"""Tool Plane application boundaries."""

from typing import Protocol

from cognitive_os.domain.approvals import ApprovalRequest, ToolPolicyDecision
from cognitive_os.domain.tools import (
    ToolDescriptor,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolInvocation,
)


class ToolPort(Protocol):
    @property
    def descriptor(self) -> ToolDescriptor: ...

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult: ...


class ToolRegistryPort(Protocol):
    def require(self, tool_id: str, version: str) -> ToolPort: ...

    def list_provider_visible(self) -> tuple[ToolDescriptor, ...]: ...


class ToolPolicyPort(Protocol):
    async def evaluate(
        self, invocation: ToolInvocation, descriptor: ToolDescriptor
    ) -> ToolPolicyDecision: ...


class ApprovalPort(Protocol):
    async def request_approval(self, request: ApprovalRequest) -> bool: ...
