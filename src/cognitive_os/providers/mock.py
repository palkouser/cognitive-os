"""Deterministic offline provider for tests and local workflows."""

from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable

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

from .errors import ProviderError, ProviderInvalidResponseError

type Sleeper = Callable[[float], Awaitable[None]]
type MockOutcome = ModelProviderResponse | ProviderError | tuple[ProviderStreamEvent, ...]


class MockProvider:
    def __init__(
        self,
        *,
        provider_id: str = "mock",
        outcomes: Iterable[MockOutcome] = (),
        capabilities: ModelCapabilities | None = None,
        health_status: ProviderStatus = ProviderStatus.AVAILABLE,
        artificial_latency: float = 0,
        sleeper: Sleeper | None = None,
    ) -> None:
        self._identity = ProviderIdentity(
            provider_id=provider_id,
            display_name="Deterministic mock provider",
            provider_kind=ProviderKind.MOCK,
            adapter_version="1",
        )
        self._outcomes = deque(outcomes)
        self._capabilities = capabilities or ModelCapabilities(
            model_id="mock-model",
            provider_id=provider_id,
            supports_streaming=True,
            supports_tool_calls=True,
            supports_parallel_tool_calls=True,
            supports_structured_output=True,
            supports_seed=True,
            maximum_context_tokens=131072,
            maximum_output_tokens=32768,
        )
        self._health_status = health_status
        self._artificial_latency = artificial_latency
        self._sleeper = sleeper
        self.received_requests: list[ModelProviderRequest] = []

    @property
    def provider_id(self) -> str:
        return self._identity.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return len(self.received_requests)

    def enqueue(self, outcome: MockOutcome) -> None:
        self._outcomes.append(outcome)

    async def _delay(self) -> None:
        if self._artificial_latency and self._sleeper is not None:
            await self._sleeper(self._artificial_latency)

    def _next_outcome(self) -> MockOutcome:
        if not self._outcomes:
            raise ProviderInvalidResponseError(
                provider_id=self.provider_id,
                message="mock provider outcome queue is empty",
            )
        return self._outcomes.popleft()

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        self.received_requests.append(request)
        await self._delay()
        outcome = self._next_outcome()
        if isinstance(outcome, ProviderError):
            raise outcome
        if isinstance(outcome, tuple):
            raise ProviderInvalidResponseError(
                provider_id=self.provider_id,
                message="stream outcome cannot satisfy a completion request",
            )
        return outcome.model_copy(update={"model_call_id": request.model_call_id})

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        self.received_requests.append(request)
        await self._delay()
        outcome = self._next_outcome()
        if isinstance(outcome, ProviderError):
            raise outcome
        if not isinstance(outcome, tuple):
            raise ProviderInvalidResponseError(
                provider_id=self.provider_id,
                message="completion outcome cannot satisfy a stream request",
            )
        for event in outcome:
            yield event

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            status=self._health_status,
            checked_at=utc_now(),
            latency_ms=0,
            configured_model=self._capabilities.model_id,
            resolved_model=self._capabilities.model_id,
            message="mock provider is configured",
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        return self._capabilities.model_copy(update={"model_id": model_id})
