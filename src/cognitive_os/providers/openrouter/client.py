"""The OpenRouter adapter: the installed OpenAI client, a live catalog, and typed failures.

No new dependency. OpenRouter is OpenAI-API-compatible, `openai` is already declared, and
the MiniMax adapter already proves the request and response mapping against that client, so
adding LiteLLM or an OpenRouter SDK would have bought a second retry policy and a second
error taxonomy to reach a boundary the repository already has.

Nothing here retains a raw provider payload. Responses are normalized through the shared
mapping, routing metadata is read through an allowlist, and errors are constructed without
the body, the request identity or the headers. See ADR 0087.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any, Protocol, cast

from openai import AsyncOpenAI

from cognitive_os.config.provider_config import OpenRouterProviderConfig
from cognitive_os.config.secret_loading import get_required_secret
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ProviderHealth,
    ProviderIdentity,
    ProviderKind,
    ProviderStatus,
    ProviderStreamEvent,
)
from cognitive_os.providers.errors import (
    ProviderConfigurationError,
    ProviderError,
    ProviderUnsupportedCapabilityError,
)
from cognitive_os.providers.minimax.health import elapsed_ms, health_from_error
from cognitive_os.providers.openai_compatible import map_response, map_sdk_error, strip_code_fences

from .discovery import (
    ModelCatalog,
    catalog_is_fresh,
    monotonic_now,
    parse_catalog,
    resolve_route,
)
from .mapping import attribution_headers, build_completion_payload, safe_routing_metadata

_FAILURE_MESSAGE = "OpenRouter provider request failed"


class OpenRouterTransport(Protocol):
    """The two calls this adapter makes. Narrow on purpose: a fake implements both in ten
    lines, so every failure class has an offline fixture and normal CI needs no network."""

    async def create_completion(self, payload: dict[str, Any]) -> object: ...

    async def list_models(self) -> object: ...

    async def close(self) -> None: ...


class OpenAiTransport:
    """The real transport: the installed `AsyncOpenAI` client pointed at OpenRouter."""

    def __init__(self, config: OpenRouterProviderConfig) -> None:
        self._config = config
        self._client: AsyncOpenAI | None = None

    def _client_or_create(self) -> AsyncOpenAI:
        if self._client is None:
            secret = get_required_secret(
                self._config.api_key_environment_variable,
                provider_id=self._config.provider_id,
            )
            self._client = AsyncOpenAI(
                api_key=secret.get_secret_value(),
                base_url=self._config.base_url,
                timeout=self._config.timeout_seconds,
                # Retries belong to the repository's retry policy, which knows which
                # failures are safe to repeat. Two independent retry layers would multiply.
                max_retries=0,
                default_headers=attribution_headers(self._config) or None,
            )
        return self._client

    async def create_completion(self, payload: dict[str, Any]) -> object:
        return await self._client_or_create().chat.completions.create(**payload)

    async def list_models(self) -> object:
        response = await self._client_or_create().models.list()
        return {"data": [model.model_dump() for model in response.data]}

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


class OpenRouterProvider:
    """A `ModelProviderPort` over OpenRouter with runtime discovery and a zero-spend default."""

    def __init__(
        self,
        config: OpenRouterProviderConfig,
        *,
        transport: OpenRouterTransport | None = None,
        clock: object = monotonic_now,
    ) -> None:
        self.config = config
        self._transport = transport or cast(OpenRouterTransport, OpenAiTransport(config))
        self._clock = cast(Any, clock)
        self._catalog: ModelCatalog | None = None
        self._identity = ProviderIdentity(
            provider_id=config.provider_id,
            display_name="OpenRouter OpenAI-compatible provider",
            provider_kind=ProviderKind.NETWORK_API,
            adapter_version="1",
        )

    def __repr__(self) -> str:
        return (
            f"OpenRouterProvider(provider_id={self.provider_id!r}, "
            f"route={self.config.default_route!r})"
        )

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    async def close(self) -> None:
        await self._transport.close()

    # ------------------------------------------------------------------- discovery

    async def catalog(self, *, force: bool = False) -> ModelCatalog:
        """The model catalog, cached for the configured lifetime and no longer."""
        now = self._clock()
        if not force and catalog_is_fresh(
            self._catalog, lifetime_seconds=self.config.catalog_cache_seconds, now=now
        ):
            return cast(ModelCatalog, self._catalog)
        try:
            payload = await self._transport.list_models()
        except ProviderError:
            raise
        except Exception as error:
            raise map_sdk_error(self.provider_id, error, message=_FAILURE_MESSAGE) from error
        self._catalog = parse_catalog(payload, provider_id=self.provider_id, now=now)
        return self._catalog

    async def resolved_route_for(self, requested_model: str) -> str:
        catalog = await self.catalog()
        return resolve_route(
            provider_id=self.provider_id,
            catalog=catalog,
            requested=requested_model,
            default_route=self.config.default_route,
            pinned_free_model=self.config.pinned_free_model,
            require_free_model=self.config.require_free_model,
            maximum_spend_usd=self.config.maximum_spend_usd,
        )

    # ---------------------------------------------------------------------- execute

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        route = await self.resolved_route_for(request.requested_model)
        payload = build_completion_payload(request, self.config, route=route)
        started = time.monotonic()
        try:
            raw = await self._transport.create_completion(payload)
        except ProviderError:
            raise
        except Exception as error:
            raise map_sdk_error(self.provider_id, error, message=_FAILURE_MESSAGE) from error
        response = map_response(
            raw,
            request,
            provider_id=self.provider_id,
            latency_ms=(time.monotonic() - started) * 1000,
            content_transform=strip_code_fences,
        )
        upstream = safe_routing_metadata(raw).get("provider")
        if isinstance(upstream, str):
            # A warning rather than a metadata field on the response contract: the contract
            # is provider-neutral, and the receipt is where routing detail belongs.
            response = response.model_copy(
                update={"warnings": (*response.warnings, f"routed via {upstream}")}
            )
        return response

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        del request
        raise ProviderUnsupportedCapabilityError(
            provider_id=self.provider_id,
            message="OpenRouter advisory streaming is not part of the governed boundary",
        )
        yield  # pragma: no cover - unreachable, present so this is an async generator

    # ----------------------------------------------------------------------- health

    async def health_check(self) -> ProviderHealth:
        """Read-only. Reaches the catalog and never runs a completion.

        A health check that completed would spend budget, produce provider-side retention
        and create a model call nobody asked for, every time an operator asked whether the
        provider was reachable.
        """
        started = time.monotonic()
        try:
            get_required_secret(
                self.config.api_key_environment_variable, provider_id=self.provider_id
            )
        except ProviderConfigurationError as error:
            return ProviderHealth(
                provider_id=self.provider_id,
                status=ProviderStatus.UNAUTHENTICATED,
                checked_at=utc_now(),
                configured_model=self.config.default_route,
                message=error.message,
            )
        try:
            catalog = await self.catalog(force=True)
        except ProviderError as error:
            return health_from_error(self.provider_id, self.config.default_route, error)

        free = catalog.free_model_ids
        ready = bool(free) or not self.config.require_free_model
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.AVAILABLE if ready else ProviderStatus.DEGRADED,
            checked_at=utc_now(),
            latency_ms=elapsed_ms(started),
            configured_model=self.config.default_route,
            resolved_model=self.config.pinned_free_model,
            message=(
                f"catalog reachable with {len(free)} free models"
                if ready
                else "catalog reachable but currently offers no free model"
            ),
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        catalog_model = self._catalog.get(model_id) if self._catalog is not None else None
        context = (
            catalog_model.context_length
            if catalog_model is not None and catalog_model.context_length is not None
            else self.config.maximum_context_tokens
        )
        return ModelCapabilities(
            model_id=model_id,
            provider_id=self.provider_id,
            supports_streaming=False,
            supports_tool_calls=False,
            supports_parallel_tool_calls=False,
            supports_structured_output=True,
            supports_system_messages=True,
            supports_seed=False,
            maximum_context_tokens=min(context, self.config.maximum_context_tokens),
            maximum_output_tokens=self.config.maximum_output_tokens,
        )
