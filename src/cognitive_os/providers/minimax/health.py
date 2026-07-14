"""MiniMax model discovery and normalized health mapping."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.provider import ProviderHealth, ProviderStatus
from cognitive_os.providers.errors import (
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderError,
)

type Clock = Callable[[], float]


def model_ids(response: object) -> tuple[str, ...]:
    data = getattr(response, "data", None)
    if not isinstance(data, Sequence):
        raise ValueError("model list response has no data sequence")
    result = tuple(
        identifier for model in data if isinstance((identifier := getattr(model, "id", None)), str)
    )
    if not result:
        raise ValueError("model list response contains no model IDs")
    return result


def health_from_models(
    *,
    provider_id: str,
    configured_model: str,
    models: tuple[str, ...],
    latency_ms: float,
) -> ProviderHealth:
    present = configured_model in models
    return ProviderHealth(
        provider_id=provider_id,
        status=ProviderStatus.AVAILABLE if present else ProviderStatus.DEGRADED,
        checked_at=utc_now(),
        latency_ms=latency_ms,
        configured_model=configured_model,
        resolved_model=configured_model if present else None,
        message="configured model is available" if present else "configured model is absent",
    )


def health_from_error(provider_id: str, model: str, error: ProviderError) -> ProviderHealth:
    if isinstance(error, ProviderAuthenticationError):
        status = ProviderStatus.UNAUTHENTICATED
    elif isinstance(error, ProviderConfigurationError):
        status = ProviderStatus.MISCONFIGURED
    else:
        status = ProviderStatus.UNAVAILABLE
    return ProviderHealth(
        provider_id=provider_id,
        status=status,
        checked_at=utc_now(),
        configured_model=model,
        message=error.message,
    )


def elapsed_ms(started: float, clock: Clock = time.monotonic) -> float:
    return max(0, (clock() - started) * 1000)
