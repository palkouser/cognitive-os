"""Durable provider-call lifecycle and normalized artifact persistence."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from cognitive_os.application.ports.artifact_store import ArtifactStorePort
from cognitive_os.application.ports.event_store import EventStorePort
from cognitive_os.domain.common import ActorRef, ArtifactRef, ErrorInfo, utc_now
from cognitive_os.domain.enums import ActorType, CallStatus, PrivacyClass, StreamType
from cognitive_os.domain.model_calls import (
    ModelCallRequestRecord,
    ModelCallResultRecord,
    ModelParameters,
)
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.events.base import EventPayload, create_event_envelope
from cognitive_os.events.model_events import (
    ModelCallCompleted,
    ModelCallFailed,
    ModelCallRequested,
    ModelCallRetried,
    ModelCallStarted,
    ModelCallTimedOut,
)
from cognitive_os.providers.errors import ProviderError, ProviderPersistenceError


class ProviderArtifactPolicy(StrEnum):
    NONE = "none"
    NORMALIZED_ONLY = "normalized_only"
    NORMALIZED_AND_RAW_SANITIZED = "normalized_and_raw_sanitized"


_SECRET_ENVIRONMENT_NAME = re.compile(
    r"(^|_)(api_?key|authorization|credential|password|secret|token)($|_)",
    re.IGNORECASE,
)


def sanitize_provider_artifact(value: object) -> object:
    secrets = tuple(
        secret
        for name, secret in os.environ.items()
        if _SECRET_ENVIRONMENT_NAME.search(name) and len(secret) >= 8
    )

    def sanitize(item: object) -> object:
        if isinstance(item, Mapping):
            return {
                str(key): (
                    "<redacted>" if _SECRET_ENVIRONMENT_NAME.search(str(key)) else sanitize(nested)
                )
                for key, nested in item.items()
            }
        if isinstance(item, list | tuple):
            return [sanitize(nested) for nested in item]
        if isinstance(item, str):
            result = item
            for secret in secrets:
                result = result.replace(secret, "<redacted>")
            return result
        return item

    return sanitize(value)


class ProviderArtifactService:
    def __init__(
        self,
        artifact_store: ArtifactStorePort,
        *,
        policy: ProviderArtifactPolicy = ProviderArtifactPolicy.NORMALIZED_ONLY,
    ) -> None:
        self._artifact_store = artifact_store
        self.policy = policy

    async def store_request(self, request: ModelProviderRequest) -> ArtifactRef | None:
        if self.policy is ProviderArtifactPolicy.NONE:
            return None
        return await self._store(
            request.model_dump(mode="json"),
            media_type="application/vnd.cognitive-os.provider-request+json",
        )

    async def store_response(self, response: ModelProviderResponse) -> ArtifactRef | None:
        if self.policy is ProviderArtifactPolicy.NONE:
            return None
        return await self._store(
            response.model_dump(mode="json"),
            media_type="application/vnd.cognitive-os.provider-response+json",
        )

    async def _store(self, value: object, *, media_type: str) -> ArtifactRef:
        encoded = json.dumps(
            sanitize_provider_artifact(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        try:
            return await self._artifact_store.put_bytes(encoded, media_type=media_type)
        except Exception as error:
            raise ProviderPersistenceError(
                provider_id="artifact-store",
                error_code="provider_artifact_persistence",
                message="provider artifact persistence failed",
            ) from error


class ProviderEventService:
    def __init__(self, event_store: EventStorePort) -> None:
        self._event_store = event_store
        self._actor = ActorRef(actor_type=ActorType.SYSTEM, actor_id="provider-execution")

    async def requested(
        self,
        request: ModelProviderRequest,
        *,
        provider_id: str,
        request_artifact: ArtifactRef | None = None,
    ) -> None:
        record = ModelCallRequestRecord(
            model_call_id=request.model_call_id,
            task_run_id=request.task_run_id,
            step_id=request.step_id,
            provider=provider_id,
            requested_model=request.requested_model,
            input_artifacts=(request_artifact,) if request_artifact else (),
            parameters=ModelParameters(
                temperature=request.temperature,
                max_output_tokens=request.max_output_tokens,
                context_budget=request.context_budget,
                timeout_seconds=request.timeout_seconds,
                tool_choice=request.tool_choice.value,
            ),
            requested_at=utc_now(),
        )
        await self._append(request, ModelCallRequested(request=record))

    async def started(self, request: ModelProviderRequest) -> None:
        await self._append(
            request,
            ModelCallStarted(model_call_id=request.model_call_id, started_at=utc_now()),
        )

    async def retried(
        self,
        request: ModelProviderRequest,
        *,
        previous_attempt: int,
        next_attempt: int,
    ) -> None:
        await self._append(
            request,
            ModelCallRetried(
                model_call_id=request.model_call_id,
                previous_attempt=previous_attempt,
                next_attempt=next_attempt,
            ),
        )

    async def completed(
        self,
        request: ModelProviderRequest,
        response: ModelProviderResponse,
        *,
        started_at: datetime,
        response_artifact: ArtifactRef | None = None,
    ) -> None:
        now = utc_now()
        result = ModelCallResultRecord(
            model_call_id=request.model_call_id,
            resolved_model=response.resolved_model,
            status=CallStatus.COMPLETED,
            started_at=started_at,
            finished_at=now,
            content_artifact=response_artifact,
            usage=response.usage,
            finish_reason=response.finish_reason.value,
            latency_ms=response.latency_ms,
            warnings=response.warnings,
        )
        await self._append(request, ModelCallCompleted(result=result))

    async def failed(self, request: ModelProviderRequest, error: ProviderError) -> None:
        info = ErrorInfo(
            code=error.error_code,
            message=error.message,
            error_type=type(error).__name__,
            retryable=error.retryable,
            details={
                "attempt": error.attempt,
                "provider_request_id": error.provider_request_id,
            },
        )
        await self._append(
            request,
            ModelCallFailed(
                model_call_id=request.model_call_id,
                finished_at=utc_now(),
                error=info,
            ),
        )

    async def timed_out(self, request: ModelProviderRequest) -> None:
        await self._append(
            request,
            ModelCallTimedOut(
                model_call_id=request.model_call_id,
                timed_out_at=utc_now(),
                timeout_seconds=request.timeout_seconds,
            ),
        )

    async def _append(self, request: ModelProviderRequest, payload: EventPayload) -> None:
        try:
            current = await self._event_store.get_stream_version(request.model_call_id)
            expected = current or 0
            envelope = create_event_envelope(
                payload=payload,
                stream_id=request.model_call_id,
                stream_type=StreamType.MODEL_CALL,
                stream_version=expected + 1,
                correlation_id=UUID(str(request.correlation_id)),
                causation_event_id=None,
                actor=self._actor,
                source_component="provider-execution",
                privacy_class=PrivacyClass.SENSITIVE,
            )
            await self._event_store.append((envelope,), expected_version=expected)
        except ProviderPersistenceError:
            raise
        except Exception as error:
            raise ProviderPersistenceError(
                provider_id="event-store",
                error_code="provider_event_persistence",
                message="provider lifecycle event persistence failed",
            ) from error
