"""Explicit static provider registration and selection."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable

from cognitive_os.application.ports.model_provider import ModelProviderPort
from cognitive_os.domain.common import ErrorInfo, utc_now
from cognitive_os.domain.provider import ProviderHealth, ProviderStatus

from .errors import ProviderConfigurationError


class ProviderRegistry:
    def __init__(self, providers: Iterable[ModelProviderPort] = ()) -> None:
        self._providers: dict[str, ModelProviderPort] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ModelProviderPort) -> None:
        if not provider.enabled:
            raise ProviderConfigurationError(
                provider_id=provider.provider_id,
                error_code="disabled_provider",
                message="disabled provider cannot be registered for selection",
            )
        if provider.provider_id in self._providers:
            raise ProviderConfigurationError(
                provider_id=provider.provider_id,
                error_code="duplicate_provider",
                message="provider ID is already registered",
            )
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ModelProviderPort | None:
        return self._providers.get(provider_id)

    def require(self, provider_id: str) -> ModelProviderPort:
        provider = self.get(provider_id)
        if provider is None:
            raise ProviderConfigurationError(
                provider_id=provider_id,
                error_code="unknown_provider",
                message="provider is not registered",
            )
        return provider

    def list_provider_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    async def health_check_all(self) -> tuple[ProviderHealth, ...]:
        results = await asyncio.gather(
            *(self._safe_health(self._providers[key]) for key in sorted(self._providers))
        )
        return tuple(results)

    @staticmethod
    async def _safe_health(provider: ModelProviderPort) -> ProviderHealth:
        try:
            return await provider.health_check()
        except Exception as error:
            return ProviderHealth(
                provider_id=provider.provider_id,
                status=ProviderStatus.UNAVAILABLE,
                checked_at=utc_now(),
                message="provider health check failed",
                error=ErrorInfo(
                    code="provider_health_failure",
                    message="provider health check failed",
                    error_type=type(error).__name__,
                ),
            )


def select_provider(
    registry: ProviderRegistry,
    provider_id: str | None,
    default_provider_id: str,
) -> ModelProviderPort:
    return registry.require(provider_id or default_provider_id)
