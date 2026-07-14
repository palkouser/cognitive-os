"""Single controlled lifecycle for Tool Plane execution."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

from cognitive_os.application.ports.approval import ApprovalPort
from cognitive_os.application.ports.tool import ToolPolicyPort, ToolRegistryPort
from cognitive_os.domain.approvals import ApprovalDecisionType, ApprovalRequest, PolicyAction
from cognitive_os.domain.tools import (
    ToolExecutionContext,
    ToolExecutionResult,
    ToolExecutionStatus,
    ToolInvocation,
)
from cognitive_os.events.tool_event_service import ToolEventService
from cognitive_os.tools.errors import ToolApprovalError, ToolPlaneError
from cognitive_os.tools.validation import validate_value


class ToolExecutionService:
    def __init__(
        self,
        registry: ToolRegistryPort,
        policy: ToolPolicyPort,
        approvals: ApprovalPort,
        events: ToolEventService,
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._approvals = approvals
        self._events = events

    async def execute(
        self, invocation: ToolInvocation, context: ToolExecutionContext
    ) -> ToolExecutionResult:
        tool = self._registry.require(invocation.tool_id, invocation.tool_version)
        descriptor = tool.descriptor
        arguments = validate_value(invocation.arguments, descriptor.input_schema)
        decision = await self._policy.evaluate(invocation, descriptor)
        await self._events.requested(invocation, descriptor.risk_level)
        if decision.action is PolicyAction.DENY:
            await self._events.denied(invocation, decision.reason)
            return _denied(invocation, decision.reason)
        actor = "tool-policy"
        if decision.action is PolicyAction.REQUIRE_APPROVAL:
            argument_hash = sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
            request = ApprovalRequest(
                approval_id=uuid4(),
                tool_call_id=invocation.tool_call_id,
                task_run_id=invocation.task_run_id,
                tool_id=descriptor.tool_id,
                tool_version=descriptor.version,
                arguments_summary=invocation.arguments,
                risk_level=descriptor.risk_level,
                side_effects=descriptor.side_effects,
                reason=decision.reason,
                requested_at=datetime.now(UTC),
            )
            approval = await self._approvals.get_existing_task_approval(
                invocation.task_run_id, descriptor.tool_id, descriptor.version, argument_hash
            )
            approval = approval or await self._approvals.request_approval(request)
            await self._approvals.record_decision(approval)
            if approval.decision not in {
                ApprovalDecisionType.ALLOW_ONCE,
                ApprovalDecisionType.ALLOW_FOR_TASK,
            }:
                await self._events.denied(invocation, "approval denied")
                raise ToolApprovalError("tool approval was denied")
            actor = approval.decided_by
        await self._events.authorized(invocation, actor)
        await self._events.started(invocation)
        try:
            async with asyncio.timeout(context.timeout_seconds):
                result = await tool.execute(invocation, context)
            validate_value(result.result, descriptor.output_schema)
            await self._events.completed(invocation, result)
            return result
        except TimeoutError:
            await self._events.timed_out(invocation, context.timeout_seconds)
            raise
        except asyncio.CancelledError:
            await self._events.failed(invocation, "tool execution was cancelled")
            raise
        except ToolPlaneError:
            await self._events.failed(invocation, "tool execution failed")
            raise


def _denied(invocation: ToolInvocation, reason: str) -> ToolExecutionResult:
    now = datetime.now(UTC)
    return ToolExecutionResult(
        tool_call_id=invocation.tool_call_id,
        tool_id=invocation.tool_id,
        tool_version=invocation.tool_version,
        status=ToolExecutionStatus.DENIED,
        started_at=now,
        finished_at=now,
        warnings=(reason,),
    )
