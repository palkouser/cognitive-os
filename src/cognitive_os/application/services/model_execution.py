"""Provider selection, capability enforcement, retry, timing, and persistence."""

from __future__ import annotations

import asyncio
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from cognitive_os.domain.common import TokenUsage, UtcDatetime, utc_now
from cognitive_os.domain.context import ContextBundleReference
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ModelFinishReason,
    ProviderStreamEvent,
    ResponseFormat,
)
from cognitive_os.events.provider_event_service import (
    ProviderArtifactPolicy,
    ProviderArtifactService,
    ProviderEventService,
)
from cognitive_os.providers.errors import (
    ProviderCancelledError,
    ProviderContextValidationError,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnsupportedCapabilityError,
)
from cognitive_os.providers.registry import ProviderRegistry, select_provider
from cognitive_os.providers.retry import RetryPolicy, execute_with_retry

type MonotonicClock = Callable[[], float]
type ContextReferenceValidator = Callable[[ContextBundleReference], Awaitable[bool]]


class ModelExecutionService:
    def __init__(
        self,
        registry: ProviderRegistry,
        *,
        default_provider_id: str,
        retry_policy: RetryPolicy | None = None,
        event_service: ProviderEventService | None = None,
        artifact_service: ProviderArtifactService | None = None,
        context_reference_validator: ContextReferenceValidator | None = None,
        monotonic_clock: MonotonicClock = time.monotonic,
    ) -> None:
        self._registry = registry
        self._default_provider_id = default_provider_id
        self._retry_policy = retry_policy or RetryPolicy()
        self._events = event_service
        self._artifacts = artifact_service
        self._context_reference_validator = context_reference_validator
        self._monotonic = monotonic_clock

    @property
    def artifact_persistence_enabled(self) -> bool:
        return (
            self._artifacts is not None
            and self._artifacts.policy is not ProviderArtifactPolicy.NONE
        )

    async def execute(
        self,
        request: ModelProviderRequest,
        *,
        provider_id: str | None = None,
    ) -> ModelProviderResponse:
        await self._validate_context_reference(request)
        provider = select_provider(self._registry, provider_id, self._default_provider_id)
        capabilities = await provider.get_model_capabilities(request.requested_model)
        self._validate_capabilities(request, capabilities)

        request_artifact = None
        if self._artifacts is not None:
            request_artifact = await self._artifacts.store_request(request)
        if self._events is not None:
            await self._events.requested(
                request,
                provider_id=provider.provider_id,
                request_artifact=request_artifact,
            )

        started_at: UtcDatetime = utc_now()
        started_monotonic = self._monotonic()

        async def run_attempt(attempt: int) -> ModelProviderResponse:
            if self._events is not None:
                await self._events.started(request)
            try:
                async with asyncio.timeout(request.timeout_seconds):
                    response = await provider.complete(request)
            except TimeoutError as error:
                raise ProviderTimeoutError(
                    provider_id=provider.provider_id,
                    message="provider request exceeded its timeout",
                    attempt=attempt,
                ) from error
            return response

        async def on_retry(attempt: int, _error: ProviderError) -> None:
            if self._events is not None:
                await self._events.retried(
                    request,
                    previous_attempt=attempt,
                    next_attempt=attempt + 1,
                )

        try:
            response = await execute_with_retry(
                run_attempt,
                provider_id=provider.provider_id,
                policy=self._retry_policy,
                on_retry=on_retry,
            )
        except ProviderTimeoutError:
            if self._events is not None:
                await self._events.timed_out(request)
            raise
        except ProviderCancelledError as error:
            if self._events is not None:
                await self._events.failed(request, error)
            raise
        except ProviderError as error:
            if self._events is not None:
                await self._events.failed(request, error)
            raise

        measured_latency = max(0, (self._monotonic() - started_monotonic) * 1000)
        response = response.model_copy(update={"latency_ms": measured_latency})
        response_artifact = None
        if self._artifacts is not None:
            response_artifact = await self._artifacts.store_response(response)
        if self._events is not None:
            await self._events.completed(
                request,
                response,
                started_at=started_at,
                response_artifact=response_artifact,
            )
        return response

    async def stream(
        self,
        request: ModelProviderRequest,
        *,
        provider_id: str | None = None,
    ) -> AsyncIterator[ProviderStreamEvent]:
        await self._validate_context_reference(request)
        provider = select_provider(self._registry, provider_id, self._default_provider_id)
        capabilities = await provider.get_model_capabilities(request.requested_model)
        self._validate_capabilities(request, capabilities)
        if not capabilities.supports_streaming:
            raise ProviderUnsupportedCapabilityError(
                provider_id=provider.provider_id,
                message="provider does not support requested streaming",
                details={"capability": "streaming"},
            )

        request_artifact = None
        if self._artifacts is not None:
            request_artifact = await self._artifacts.store_request(request)
        if self._events is not None:
            await self._events.requested(
                request,
                provider_id=provider.provider_id,
                request_artifact=request_artifact,
            )

        started_at: UtcDatetime = utc_now()
        started_monotonic = self._monotonic()
        global_sequence = 0
        content_parts: list[str] = []
        usage: TokenUsage | None = None
        finish_reason = ModelFinishReason.COMPLETED

        for attempt in range(1, self._retry_policy.maximum_attempts + 1):
            if self._events is not None:
                await self._events.started(request)
            emitted_payload = False
            try:
                async with asyncio.timeout(request.timeout_seconds):
                    async for event in provider.stream(request):
                        if event.text_delta:
                            content_parts.append(event.text_delta)
                            emitted_payload = True
                        if event.tool_call_delta:
                            emitted_payload = True
                        if event.usage is not None:
                            usage = event.usage
                        if event.finish_reason is not None:
                            finish_reason = event.finish_reason
                        global_sequence += 1
                        yield event.model_copy(update={"sequence": global_sequence})
                break
            except TimeoutError:
                failure: ProviderError = ProviderTimeoutError(
                    provider_id=provider.provider_id,
                    message="provider stream exceeded its timeout",
                    attempt=attempt,
                )
            except asyncio.CancelledError as error:
                cancellation = ProviderCancelledError(
                    provider_id=provider.provider_id,
                    message="provider stream was cancelled",
                    attempt=attempt,
                )
                if self._events is not None:
                    await self._events.failed(request, cancellation)
                raise cancellation from error
            except ProviderError as error:
                failure = error.with_attempt(attempt)

            can_retry = (
                not emitted_payload
                and attempt < self._retry_policy.maximum_attempts
                and self._retry_policy.is_retryable(failure)
            )
            if can_retry:
                if self._events is not None:
                    await self._events.retried(
                        request,
                        previous_attempt=attempt,
                        next_attempt=attempt + 1,
                    )
                random_value = secrets.randbelow(1_000_001) / 1_000_000
                await asyncio.sleep(self._retry_policy.delay_for_attempt(attempt, random_value))
                continue
            if isinstance(failure, ProviderTimeoutError) and self._events is not None:
                await self._events.timed_out(request)
            elif self._events is not None:
                await self._events.failed(request, failure)
            raise failure

        measured_latency = max(0, (self._monotonic() - started_monotonic) * 1000)
        response = ModelProviderResponse(
            model_call_id=request.model_call_id,
            provider_id=provider.provider_id,
            requested_model=request.requested_model,
            resolved_model=request.requested_model,
            content="".join(content_parts) or None,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=measured_latency,
        )
        response_artifact = None
        if self._artifacts is not None:
            response_artifact = await self._artifacts.store_response(response)
        if self._events is not None:
            await self._events.completed(
                request,
                response,
                started_at=started_at,
                response_artifact=response_artifact,
            )

    @staticmethod
    def _validate_capabilities(request: ModelProviderRequest, capabilities: object) -> None:
        if not isinstance(capabilities, ModelCapabilities):
            raise TypeError("provider returned an invalid capability contract")
        unsupported: str | None = None
        if request.tools and not capabilities.supports_tool_calls:
            unsupported = "tool calls"
        elif (
            request.response_format is not ResponseFormat.TEXT
            and not capabilities.supports_structured_output
        ):
            unsupported = "structured output"
        elif (
            capabilities.maximum_context_tokens is not None
            and request.context_budget > capabilities.maximum_context_tokens
        ):
            unsupported = "context budget"
        elif (
            request.max_output_tokens is not None
            and capabilities.maximum_output_tokens is not None
            and request.max_output_tokens > capabilities.maximum_output_tokens
        ):
            unsupported = "output token limit"
        if unsupported is not None:
            raise ProviderUnsupportedCapabilityError(
                provider_id=capabilities.provider_id,
                message=f"provider does not support requested {unsupported}",
                details={"capability": unsupported},
            )

    async def _validate_context_reference(self, request: ModelProviderRequest) -> None:
        reference = request.context_bundle_reference
        if reference is None:
            return
        if self._context_reference_validator is None:
            raise ProviderContextValidationError(
                provider_id="context-builder",
                message="Context Bundle validation is unavailable",
            )
        try:
            valid = await self._context_reference_validator(reference)
        except Exception as error:
            raise ProviderContextValidationError(
                provider_id="context-builder",
                message="Context Bundle validation failed",
            ) from error
        if not valid:
            raise ProviderContextValidationError(
                provider_id="context-builder",
                message="Context Bundle is invalid or stale",
            )
