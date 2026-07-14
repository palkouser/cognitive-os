"""Durable Tool Plane lifecycle and artifact persistence."""

import json
from datetime import UTC, datetime

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef, ErrorInfo
from cognitive_os.domain.enums import (
    ActorType,
    CallStatus,
    PermissionDecision,
    PrivacyClass,
    RiskLevel,
    StreamType,
)
from cognitive_os.domain.tool_calls import ToolCallRequestRecord, ToolCallResultRecord
from cognitive_os.domain.tools import ToolExecutionResult, ToolInvocation, ToolRiskLevel
from cognitive_os.events.base import EventPayload, create_event_envelope
from cognitive_os.events.provider_event_service import sanitize_provider_artifact
from cognitive_os.events.tool_events import (
    ToolCallAuthorized,
    ToolCallCompleted,
    ToolCallDenied,
    ToolCallFailed,
    ToolCallRequested,
    ToolCallStarted,
    ToolCallTimedOut,
)
from cognitive_os.tools.errors import ToolPersistenceError


class ToolArtifactService:
    def __init__(self, artifact_store: ArtifactStorePort, *, inline_limit: int = 4096) -> None:
        self._store = artifact_store
        self._inline_limit = inline_limit

    async def store_json(self, value: object, *, media_type: str) -> object:
        encoded = json.dumps(
            sanitize_provider_artifact(value), sort_keys=True, separators=(",", ":")
        ).encode()
        if len(encoded) <= self._inline_limit:
            return sanitize_provider_artifact(value)
        return await self._store.put_bytes(encoded, media_type=media_type)

    async def store_output(
        self, value: bytes, *, media_type: str, limit: int
    ) -> tuple[object, bool]:
        allowed = value[:limit]
        reference = await self._store.put_bytes(allowed, media_type=media_type)
        return reference, len(value) > limit


class ToolEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="tool-execution")

    async def requested(self, invocation: ToolInvocation, risk: ToolRiskLevel) -> None:
        mapping = {
            ToolRiskLevel.R0: RiskLevel.LOW,
            ToolRiskLevel.R1: RiskLevel.MEDIUM,
            ToolRiskLevel.R2: RiskLevel.HIGH,
            ToolRiskLevel.R3: RiskLevel.CRITICAL,
        }
        await self._append(
            invocation,
            ToolCallRequested(
                request=ToolCallRequestRecord(
                    tool_call_id=invocation.tool_call_id,
                    task_run_id=invocation.task_run_id,
                    step_id=invocation.step_id,
                    tool_id=invocation.tool_id,
                    tool_version=invocation.tool_version,
                    arguments=invocation.arguments,
                    requested_at=invocation.requested_at,
                    risk_level=mapping[risk],
                    permission_decision=PermissionDecision.PENDING,
                )
            ),
        )

    async def authorized(self, invocation: ToolInvocation, actor: str) -> None:
        await self._append(
            invocation,
            ToolCallAuthorized(
                tool_call_id=invocation.tool_call_id,
                authorized_at=datetime.now(UTC),
                authorized_by=actor,
            ),
        )

    async def denied(self, invocation: ToolInvocation, reason: str) -> None:
        await self._append(
            invocation,
            ToolCallDenied(
                tool_call_id=invocation.tool_call_id,
                denied_at=datetime.now(UTC),
                denied_by="tool-policy",
                reason=reason,
            ),
        )

    async def started(self, invocation: ToolInvocation) -> None:
        await self._append(
            invocation,
            ToolCallStarted(tool_call_id=invocation.tool_call_id, started_at=datetime.now(UTC)),
        )

    async def completed(self, invocation: ToolInvocation, result: ToolExecutionResult) -> None:
        await self._append(
            invocation,
            ToolCallCompleted(
                result=ToolCallResultRecord(
                    tool_call_id=invocation.tool_call_id,
                    status=CallStatus.COMPLETED,
                    started_at=result.started_at,
                    finished_at=result.finished_at,
                    exit_code=result.exit_code,
                    stdout_artifact=result.stdout_artifact,
                    stderr_artifact=result.stderr_artifact,
                    result_artifacts=result.result_artifacts,
                    sandbox_id=result.sandbox_id,
                    warnings=result.warnings,
                )
            ),
        )

    async def failed(self, invocation: ToolInvocation, message: str) -> None:
        await self._append(
            invocation,
            ToolCallFailed(
                tool_call_id=invocation.tool_call_id,
                finished_at=datetime.now(UTC),
                error=ErrorInfo(code="tool_execution_failed", message=message, retryable=False),
            ),
        )

    async def timed_out(self, invocation: ToolInvocation, timeout: float) -> None:
        await self._append(
            invocation,
            ToolCallTimedOut(
                tool_call_id=invocation.tool_call_id,
                timed_out_at=datetime.now(UTC),
                timeout_seconds=timeout,
            ),
        )

    async def _append(self, invocation: ToolInvocation, payload: EventPayload) -> None:
        try:
            current = await self._store.get_stream_version(invocation.tool_call_id)
            expected = current or 0
            envelope = create_event_envelope(
                payload=payload,
                stream_id=invocation.tool_call_id,
                stream_type=StreamType.TOOL_CALL,
                stream_version=expected + 1,
                correlation_id=invocation.correlation_id,
                causation_event_id=None,
                actor=self._actor,
                source_component="tool-execution",
                privacy_class=PrivacyClass.SENSITIVE,
            )
            await self._store.append((envelope,), expected_version=expected)
        except Exception as error:
            raise ToolPersistenceError("tool lifecycle event persistence failed") from error
