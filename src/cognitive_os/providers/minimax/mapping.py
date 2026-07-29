"""MiniMax-specific mapping on top of the shared OpenAI-compatible one.

Only the differences live here. MiniMax emits `<think>` reasoning tags ahead of assistant
content, which is a MiniMax habit rather than a property of the OpenAI shape, so it is
stripped here and the rest of the mapping is the shared one.
"""

from __future__ import annotations

from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.providers.openai_compatible import (
    map_finish_reason,
    map_request,
    strip_code_fences,
)
from cognitive_os.providers.openai_compatible import (
    map_response as map_openai_response,
)

__all__ = ["map_finish_reason", "map_request", "map_response"]


def strip_reasoning_prefix(content: str) -> str:
    """Remove MiniMax reasoning tags, then any fence the shared transform would remove."""
    stripped = content.lstrip()
    if stripped.startswith("<think>"):
        closing_tag = stripped.find("</think>")
        if closing_tag < 0:
            return content
        stripped = stripped[closing_tag + len("</think>") :].lstrip()
    return strip_code_fences(stripped)


def map_response(
    response: object,
    request: ModelProviderRequest,
    *,
    provider_id: str,
    latency_ms: float,
) -> ModelProviderResponse:
    return map_openai_response(
        response,
        request,
        provider_id=provider_id,
        latency_ms=latency_ms,
        content_transform=strip_reasoning_prefix,
    )
