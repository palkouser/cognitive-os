"""OpenRouter model discovery and the free-route policy.

Free model availability is dynamic. A slug that answered yesterday can be gone today, and
that is normal operation for a free tier — not a defect, not an outage, and not a reason to
hard-code a model as permanently available. Discovery therefore runs at request time against
a short-lived cache, and a missing model becomes a typed `MODEL_UNAVAILABLE` result.

The catalog is metadata only: identifiers, pricing and context length. No prompt, no
response, no credential. See ADR 0087.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from math import isfinite
from typing import cast

from pydantic import Field, ValidationError

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.providers.errors import (
    ProviderBudgetExceededError,
    ProviderInvalidResponseError,
    ProviderModelUnavailableError,
)


class CatalogModel(ImmutableContractModel):
    """One routable model, reduced to what a routing decision actually needs."""

    model_id: NonEmptyStr
    prompt_price: float = Field(ge=0)
    completion_price: float = Field(ge=0)
    context_length: int | None = Field(default=None, gt=0)

    @property
    def is_free(self) -> bool:
        """Free by *price*, not by name.

        A `:free` suffix is a naming convention and conventions drift; a zero price is the
        thing a zero-spend policy is actually asserting.
        """
        return self.prompt_price == 0 and self.completion_price == 0


class ModelCatalog(ImmutableContractModel):
    models: tuple[CatalogModel, ...]
    fetched_at_monotonic: float

    def get(self, model_id: str) -> CatalogModel | None:
        for model in self.models:
            if model.model_id == model_id:
                return model
        return None

    @property
    def free_model_ids(self) -> tuple[str, ...]:
        return tuple(model.model_id for model in self.models if model.is_free)


def _price(entry: Mapping[str, object], key: str) -> float:
    """OpenRouter prices are decimal strings. Anything not a finite, non-negative number is
    treated as *not free*.

    Failing towards "this costs money" is the safe direction: the alternative would let a
    malformed catalog entry pass a zero-spend policy.

    The live catalog carries `-1` for models whose price is not fixed — auto-routed and
    dynamically priced entries. That is emphatically not "free", and normalising it here
    rather than widening `CatalogModel` keeps the contract's `ge=0` invariant true, so no
    later `price <= 0` test can read a variable price as a free one. Found by the Sprint
    21C2 OpenRouter live smoke; the fixture catalog had no such entry.
    """
    pricing = entry.get("pricing")
    if not isinstance(pricing, Mapping):
        return float("inf")
    raw = pricing.get(key)
    try:
        value = float(cast(str | float | int, raw))
    except (TypeError, ValueError):
        return float("inf")
    if not isfinite(value) or value < 0:
        return float("inf")
    return value


def parse_catalog(payload: object, *, provider_id: str, now: float) -> ModelCatalog:
    """Turn a `/models` response into the bounded metadata the router needs."""
    data = payload.get("data") if isinstance(payload, Mapping) else None
    if not isinstance(data, Sequence) or isinstance(data, str | bytes):
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="the OpenRouter model catalog is not a list",
        )
    models: list[CatalogModel] = []
    for entry in data:
        if not isinstance(entry, Mapping):
            continue
        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier:
            continue
        context_length = entry.get("context_length")
        try:
            model = CatalogModel(
                model_id=identifier,
                prompt_price=_price(entry, "prompt"),
                completion_price=_price(entry, "completion"),
                context_length=context_length if isinstance(context_length, int) else None,
            )
        except ValidationError:
            # One unusable row must not destroy the whole catalog, and it must not become
            # routable either. Skipping leaves it absent, so `resolve_route` refuses it with
            # a typed `ProviderModelUnavailableError` rather than guessing at its price.
            continue
        models.append(model)
    if not models:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="the OpenRouter model catalog contains no usable models",
        )
    return ModelCatalog(models=tuple(models), fetched_at_monotonic=now)


def resolve_route(
    *,
    provider_id: str,
    catalog: ModelCatalog,
    requested: str,
    default_route: str,
    pinned_free_model: str | None,
    require_free_model: bool,
    maximum_spend_usd: float,
) -> str:
    """Decide which model identifier is actually sent, and refuse rather than guess.

    The router slug (`openrouter/free`) is passed through untouched: OpenRouter resolves it
    server-side and reports the model it chose, and that resolved identity is what the
    receipt records. A *pinned* model is validated against the live catalog first, because
    pinning a free slug is exactly the case where availability changes underneath us.
    """
    route = requested or default_route
    if pinned_free_model is not None and route == default_route:
        route = pinned_free_model

    if route == default_route:
        if require_free_model and not catalog.free_model_ids:
            raise ProviderModelUnavailableError(
                provider_id=provider_id,
                message="the OpenRouter catalog currently offers no free model",
                details={"requested_route": route},
            )
        return route

    model = catalog.get(route)
    if model is None:
        raise ProviderModelUnavailableError(
            provider_id=provider_id,
            message="the requested OpenRouter model is not in the current catalog",
            details={"requested_route": route},
        )
    if require_free_model and not model.is_free:
        raise ProviderBudgetExceededError(
            provider_id=provider_id,
            message="a paid model cannot be routed under a free-only policy",
            details={"requested_route": route},
        )
    if maximum_spend_usd <= 0 and not model.is_free:
        raise ProviderBudgetExceededError(
            provider_id=provider_id,
            message="paid routing is refused while the configured maximum spend is zero",
            details={"requested_route": route},
        )
    return route


def catalog_is_fresh(catalog: ModelCatalog | None, *, lifetime_seconds: float, now: float) -> bool:
    """Whether a cached catalog may still be used.

    Bounded and explicit rather than cached forever: a stale catalog would keep routing to a
    model that has already disappeared, and the failure would then surface as an upstream
    error rather than as the typed unavailability it is.
    """
    if catalog is None:
        return False
    if lifetime_seconds <= 0:
        return False
    return (now - catalog.fetched_at_monotonic) < lifetime_seconds


def monotonic_now() -> float:
    return time.monotonic()
