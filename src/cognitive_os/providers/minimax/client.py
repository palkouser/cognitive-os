"""Lazy MiniMax OpenAI-compatible client and provider implementation."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Protocol, cast

import openai
from openai import AsyncOpenAI

from cognitive_os.config.provider_config import MiniMaxProviderConfig
from cognitive_os.config.secret_loading import get_required_secret
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ProviderHealth,
    ProviderIdentity,
    ProviderKind,
    ProviderStreamEvent,
    ProviderStreamEventType,
)
from cognitive_os.providers.errors import (
    ProviderAuthenticationError,
    ProviderAuthorizationError,
    ProviderConnectionError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

from .health import elapsed_ms, health_from_error, health_from_models, model_ids
from .mapping import map_finish_reason, map_request, map_response


class CompletionResource(Protocol):
    async def create(self, **kwargs: object) -> object: ...


class ChatResource(Protocol):
    completions: CompletionResource


class ModelResource(Protocol):
    async def list(self) -> object: ...


class OpenAIClientPort(Protocol):
    chat: ChatResource
    models: ModelResource

    async def close(self) -> None: ...


class MiniMaxProvider:
    def __init__(
        self,
        config: MiniMaxProviderConfig,
        *,
        client: OpenAIClientPort | None = None,
    ) -> None:
        self.config = config
        self._client = client
        self._identity = ProviderIdentity(
            provider_id=config.provider_id,
            display_name="MiniMax OpenAI-compatible provider",
            provider_kind=ProviderKind.NETWORK_API,
            adapter_version="1",
        )

    def __repr__(self) -> str:
        return f"MiniMaxProvider(provider_id={self.provider_id!r}, model={self.config.model!r})"

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def _get_client(self) -> OpenAIClientPort:
        if self._client is None:
            secret = get_required_secret(
                self.config.api_key_environment_variable,
                provider_id=self.provider_id,
            )
            sdk_client = AsyncOpenAI(
                api_key=secret.get_secret_value(),
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
                max_retries=0,
            )
            self._client = cast(OpenAIClientPort, sdk_client)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        started = time.monotonic()
        try:
            raw = await self._get_client().chat.completions.create(**map_request(request))
            return map_response(
                raw,
                request,
                provider_id=self.provider_id,
                latency_ms=(time.monotonic() - started) * 1000,
            )
        except ProviderError:
            raise
        except Exception as error:
            raise map_sdk_error(self.provider_id, error) from error

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        sequence = 1
        tool_arguments: dict[int, str] = {}
        finish_reason = None
        yield ProviderStreamEvent(
            sequence=sequence,
            event_type=ProviderStreamEventType.RESPONSE_STARTED,
        )
        try:
            raw_stream = await self._get_client().chat.completions.create(
                **map_request(request), stream=True
            )
            stream = cast(AsyncIterator[object], raw_stream)
            async for chunk in stream:
                choices = getattr(chunk, "choices", ())
                if choices:
                    choice = choices[0]
                    delta = getattr(choice, "delta", None)
                    text = getattr(delta, "content", None)
                    if isinstance(text, str) and text:
                        sequence += 1
                        yield ProviderStreamEvent(
                            sequence=sequence,
                            event_type=ProviderStreamEventType.TEXT_DELTA,
                            text_delta=text,
                        )
                    for tool_delta in getattr(delta, "tool_calls", ()) or ():
                        index = getattr(tool_delta, "index", 0)
                        function = getattr(tool_delta, "function", None)
                        arguments = getattr(function, "arguments", "") or ""
                        tool_arguments[index] = tool_arguments.get(index, "") + arguments
                        sequence += 1
                        yield ProviderStreamEvent(
                            sequence=sequence,
                            event_type=ProviderStreamEventType.TOOL_CALL_DELTA,
                            tool_call_delta={
                                "index": index,
                                "tool_call_id": getattr(tool_delta, "id", None),
                                "name": getattr(function, "name", None),
                                "arguments_delta": arguments,
                                "arguments_accumulated": tool_arguments[index],
                            },
                        )
                    raw_finish = getattr(choice, "finish_reason", None)
                    if raw_finish is not None:
                        finish_reason, _warnings = map_finish_reason(raw_finish)
                    else:
                        finish_reason = None
            sequence += 1
            yield ProviderStreamEvent(
                sequence=sequence,
                event_type=ProviderStreamEventType.RESPONSE_COMPLETED,
                finish_reason=finish_reason,
            )
        except Exception as error:
            raise map_sdk_error(self.provider_id, error) from error

    async def health_check(self) -> ProviderHealth:
        started = time.monotonic()
        try:
            response = await self._get_client().models.list()
            return health_from_models(
                provider_id=self.provider_id,
                configured_model=self.config.model,
                models=model_ids(response),
                latency_ms=elapsed_ms(started),
            )
        except ProviderError as error:
            return health_from_error(self.provider_id, self.config.model, error)
        except Exception as error:
            return health_from_error(
                self.provider_id,
                self.config.model,
                map_sdk_error(self.provider_id, error),
            )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=model_id,
            provider_id=self.provider_id,
            supports_streaming=True,
            supports_tool_calls=self.config.supports_tool_calls,
            supports_parallel_tool_calls=False,
            supports_structured_output=self.config.supports_structured_output,
            supports_system_messages=True,
            supports_seed=False,
            maximum_context_tokens=self.config.maximum_context_tokens,
            maximum_output_tokens=self.config.default_max_output_tokens,
        )


def map_sdk_error(provider_id: str, error: Exception) -> ProviderError:
    message = "MiniMax provider request failed"
    if isinstance(error, openai.AuthenticationError):
        return ProviderAuthenticationError(provider_id=provider_id, message=message)
    if isinstance(error, openai.PermissionDeniedError):
        return ProviderAuthorizationError(provider_id=provider_id, message=message)
    if isinstance(error, openai.RateLimitError):
        return ProviderRateLimitError(provider_id=provider_id, message=message)
    if isinstance(error, openai.APITimeoutError):
        return ProviderTimeoutError(provider_id=provider_id, message=message)
    if isinstance(error, openai.APIConnectionError):
        return ProviderConnectionError(provider_id=provider_id, message=message)
    if isinstance(error, openai.BadRequestError):
        return ProviderInvalidRequestError(provider_id=provider_id, message=message)
    if isinstance(error, openai.InternalServerError):
        return ProviderUnavailableError(provider_id=provider_id, message=message)
    return ProviderInvalidResponseError(provider_id=provider_id, message=message)
