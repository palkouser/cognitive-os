"""Asynchronous provider execution boundary."""

from collections.abc import AsyncIterator
from typing import Protocol

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import (
    ModelCapabilities,
    ProviderHealth,
    ProviderIdentity,
    ProviderStreamEvent,
)


class ModelProviderPort(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def identity(self) -> ProviderIdentity: ...

    @property
    def enabled(self) -> bool: ...

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse: ...

    def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]: ...

    async def health_check(self) -> ProviderHealth: ...

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities: ...
