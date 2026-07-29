"""A scriptable OpenRouter transport with no network behind it.

The adapter's transport port is two methods wide precisely so this file can exist: every
OpenRouter failure class gets an offline fixture, and the credential-free lane needs no key,
no network and no live catalog to exercise them.

Nothing here is labelled as a live or real governed outcome. The catalog entries are
invented, the model identifiers are `vendor/...`, and no fixture may be mistaken for a
recorded provider response.
"""

from __future__ import annotations

from typing import Any

import httpx
import openai

#: A catalog with two free models and one paid one, which is the shape every routing
#: decision in the suite needs to distinguish.
CATALOG_PAYLOAD: dict[str, Any] = {
    "data": [
        {
            "id": "vendor/small-model:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "context_length": 32768,
        },
        {
            "id": "vendor/other-model:free",
            "pricing": {"prompt": "0.0", "completion": "0.0"},
            "context_length": 8192,
        },
        {
            "id": "vendor/premium-model",
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
            "context_length": 200000,
        },
    ]
}

EMPTY_CATALOG_PAYLOAD: dict[str, Any] = {"data": []}

PAID_ONLY_CATALOG_PAYLOAD: dict[str, Any] = {
    "data": [
        {
            "id": "vendor/premium-model",
            "pricing": {"prompt": "0.000003", "completion": "0.000015"},
            "context_length": 200000,
        }
    ]
}


def completion_payload(
    *,
    content: str = '{"summary": "the helper subtracts where it should add", "findings": []}',
    model: str = "vendor/small-model:free",
    provider: str = "SomeUpstream",
    finish_reason: str = "stop",
) -> dict[str, Any]:
    return {
        "id": "gen-0123456789",
        "model": model,
        "provider": provider,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {"prompt_tokens": 42, "completion_tokens": 17, "total_tokens": 59},
    }


def _response(status: int) -> httpx.Response:
    return httpx.Response(status_code=status, request=httpx.Request("POST", "https://test/v1"))


def authentication_error() -> Exception:
    return openai.AuthenticationError("invalid key", response=_response(401), body=None)


def authorization_error() -> Exception:
    """OpenRouter answers 403 when a data policy forbids the requested routing."""
    return openai.PermissionDeniedError("data policy", response=_response(403), body=None)


def rate_limit_error() -> Exception:
    return openai.RateLimitError("slow down", response=_response(429), body=None)


def credits_exhausted_error() -> Exception:
    """402 arrives as a `BadRequestError` subclass in the SDK's status mapping."""
    return openai.APIStatusError("insufficient credits", response=_response(402), body=None)


def upstream_error() -> Exception:
    return openai.InternalServerError("upstream failed", response=_response(502), body=None)


def timeout_error() -> Exception:
    return openai.APITimeoutError(request=httpx.Request("POST", "https://test/v1"))


def connection_error() -> Exception:
    return openai.APIConnectionError(request=httpx.Request("POST", "https://test/v1"))


def bad_request_error() -> Exception:
    return openai.BadRequestError("no endpoints found", response=_response(400), body=None)


class FakeOpenRouterTransport:
    """Records what it was asked for and returns, or raises, what the test scripted."""

    def __init__(
        self,
        *,
        catalog: dict[str, Any] | None = None,
        completion: dict[str, Any] | None = None,
        completion_error: Exception | None = None,
        catalog_error: Exception | None = None,
    ) -> None:
        self.catalog_payload = CATALOG_PAYLOAD if catalog is None else catalog
        self.completion_response = completion_payload() if completion is None else completion
        self.completion_error = completion_error
        self.catalog_error = catalog_error
        self.completion_payloads: list[dict[str, Any]] = []
        self.catalog_calls = 0
        self.closed = False

    async def create_completion(self, payload: dict[str, Any]) -> object:
        self.completion_payloads.append(payload)
        if self.completion_error is not None:
            raise self.completion_error
        return self.completion_response

    async def list_models(self) -> object:
        self.catalog_calls += 1
        if self.catalog_error is not None:
            raise self.catalog_error
        return self.catalog_payload

    async def close(self) -> None:
        self.closed = True
