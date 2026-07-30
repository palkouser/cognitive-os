"""OpenRouter request extras and response metadata, on top of the shared OpenAI mapping.

Three things are genuinely OpenRouter-specific and live here: the data-policy preferences
sent with every request, the attribution headers, and the routing metadata read back off a
response. Everything else is the OpenAI chat-completions shape and is not duplicated.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cognitive_os.config.provider_config import OpenRouterProviderConfig
from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.model_requests import ModelProviderRequest
from cognitive_os.providers.openai_compatible import map_request

#: Response fields the adapter is willing to read back. Everything else in an OpenRouter
#: response — and in particular anything under `provider`, `error.metadata` or the raw body
#: — stays unread, because an allowlist is the only way to be sure a future field carrying a
#: request identity or an upstream error body does not quietly reach an event.
SAFE_ROUTING_FIELDS = ("id", "model", "provider")


def data_policy_payload(config: OpenRouterProviderConfig) -> dict[str, JsonValue]:
    """The provider-selection preferences sent with every completion.

    `data_collection: "deny"` and `zdr: True` are the strict settings. Under ADR 0088 they
    are no longer the defaults for this project, whose material is classified `public`;
    they remain what an operator sets for anything that is not. ADR 0087 still forbids
    applying a relaxed policy to internal or restricted content whatever the file says, and
    credentials never reach a provider request in either configuration.
    """
    preferences: dict[str, JsonValue] = {
        "data_collection": "allow" if config.allow_data_collection else "deny",
    }
    if config.require_zero_data_retention:
        preferences["zdr"] = True
    return preferences


def attribution_headers(config: OpenRouterProviderConfig) -> dict[str, str]:
    """Optional, non-identifying attribution. Never a credential and never an account."""
    headers: dict[str, str] = {}
    if config.application_referer:
        headers["HTTP-Referer"] = config.application_referer
    if config.application_title:
        headers["X-Title"] = config.application_title
    return headers


def build_completion_payload(
    request: ModelProviderRequest,
    config: OpenRouterProviderConfig,
    *,
    route: str,
) -> dict[str, Any]:
    """The shared OpenAI payload, plus OpenRouter's provider preferences and caps."""
    payload: dict[str, Any] = dict(map_request(request))
    requested_tokens = payload.get("max_tokens")
    capped = (
        min(requested_tokens, config.maximum_output_tokens)
        if isinstance(requested_tokens, int)
        else config.maximum_output_tokens
    )
    preferences = data_policy_payload(config)
    if config.require_free_model:
        # Belt and braces with `resolve_route`: the server-side price cap means a catalog
        # that went stale between discovery and the call still cannot bill anything.
        preferences["max_price"] = {"prompt": 0, "completion": 0}
    payload["model"] = route
    payload["max_tokens"] = capped
    # `provider` is an OpenRouter extension, not a chat-completions field. The OpenAI client
    # validates its keyword arguments, so passing it at the top level raises
    # `TypeError: unexpected keyword argument 'provider'` and the data policy never reaches
    # the wire at all. `extra_body` is the client's documented passthrough and is where a
    # vendor extension belongs. Found by the Sprint 21C2 OpenRouter live smoke; the fake
    # transport in CI accepted the payload dict as given and could not have caught it.
    extra_body = dict(payload.get("extra_body") or {})
    extra_body["provider"] = preferences
    payload["extra_body"] = extra_body
    return payload


def safe_routing_metadata(response: object) -> dict[str, JsonValue]:
    """The allowlisted routing fields, as plain scalars.

    `provider` is the upstream vendor name OpenRouter selected — useful for a receipt and
    safe to record. Nested objects are dropped rather than flattened: a field this adapter
    has not reasoned about should not reach an event because it happened to be a string.
    """
    metadata: dict[str, JsonValue] = {}
    for field in SAFE_ROUTING_FIELDS:
        value = (
            response.get(field) if isinstance(response, Mapping) else getattr(response, field, None)
        )
        if isinstance(value, str) and value:
            metadata[field] = value
    return metadata
