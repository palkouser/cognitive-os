"""Provider-independent bounded retry and cancellation policy."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from pydantic import ConfigDict, Field

from cognitive_os.domain.base import ImmutableContractModel

from .errors import (
    ProviderCancelledError,
    ProviderConnectionError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

type Sleeper = Callable[[float], Awaitable[None]]
type RandomSource = Callable[[], float]
type AttemptObserver = Callable[[int, ProviderError], Awaitable[None]]


class RetryPolicy(ImmutableContractModel):
    maximum_attempts: int = Field(default=3, ge=1, le=10)
    initial_delay_seconds: float = Field(default=1, ge=0)
    maximum_delay_seconds: float = Field(default=10, ge=0)
    backoff_multiplier: float = Field(default=2, ge=1)
    jitter_ratio: float = Field(default=0.2, ge=0, le=1)
    retryable_error_types: tuple[type[ProviderError], ...] = (
        ProviderTimeoutError,
        ProviderConnectionError,
        ProviderRateLimitError,
        ProviderUnavailableError,
    )

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra="forbid")

    def is_retryable(self, error: ProviderError) -> bool:
        return error.retryable and isinstance(error, self.retryable_error_types)

    def delay_for_attempt(self, failed_attempt: int, random_value: float) -> float:
        base = min(
            self.maximum_delay_seconds,
            self.initial_delay_seconds * self.backoff_multiplier ** (failed_attempt - 1),
        )
        jitter = base * self.jitter_ratio * ((2 * random_value) - 1)
        return max(0, min(self.maximum_delay_seconds, base + jitter))


async def execute_with_retry[T](
    operation: Callable[[int], Awaitable[T]],
    *,
    provider_id: str,
    policy: RetryPolicy,
    sleeper: Sleeper = asyncio.sleep,
    random_source: RandomSource = random.random,
    on_retry: AttemptObserver | None = None,
) -> T:
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            return await operation(attempt)
        except asyncio.CancelledError as error:
            raise ProviderCancelledError(
                provider_id=provider_id,
                message="provider execution was cancelled",
                attempt=attempt,
            ) from error
        except ProviderError as error:
            attempted = error.with_attempt(attempt)
            if attempt >= policy.maximum_attempts or not policy.is_retryable(attempted):
                raise attempted from error
            if on_retry is not None:
                await on_retry(attempt, attempted)
            try:
                await sleeper(policy.delay_for_attempt(attempt, random_source()))
            except asyncio.CancelledError as cancellation:
                raise ProviderCancelledError(
                    provider_id=provider_id,
                    message="provider retry wait was cancelled",
                    attempt=attempt,
                ) from cancellation
    raise RuntimeError("retry loop exhausted without a result")
