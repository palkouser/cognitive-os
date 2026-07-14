"""Normalize Claude Code advisory JSON output."""

from __future__ import annotations

import json
from typing import Any

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, TokenUsage
from cognitive_os.domain.model_requests import (
    ModelProviderRequest,
    ModelProviderResponse,
)
from cognitive_os.domain.provider import ModelFinishReason
from cognitive_os.providers.errors import ProviderInvalidResponseError


class AdvisoryFinding(ImmutableContractModel):
    title: NonEmptyStr
    severity: NonEmptyStr
    description: NonEmptyStr
    evidence: tuple[str, ...] = ()


class AdvisoryResult(ImmutableContractModel):
    summary: NonEmptyStr
    findings: tuple[AdvisoryFinding, ...] = ()
    recommendations: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    verification_steps: tuple[str, ...] = ()


ADVISORY_JSON_SCHEMA: dict[str, Any] = AdvisoryResult.model_json_schema()


def map_advisory_response(
    raw_stdout: str,
    request: ModelProviderRequest,
    *,
    provider_id: str,
    duration_ms: float,
) -> ModelProviderResponse:
    try:
        document = json.loads(raw_stdout)
        if not isinstance(document, dict):
            raise ValueError("Claude result must be an object")
        structured = document.get("structured_output", document.get("result", document))
        if isinstance(structured, str):
            structured = json.loads(structured)
        advisory = AdvisoryResult.model_validate(structured)
        model = document.get("model", "claude-code")
        if not isinstance(model, str) or not model:
            model = "claude-code"
        usage_data = document.get("usage")
        usage = _map_usage(usage_data)
        warnings: list[str] = []
        if "total_cost_usd" in document:
            warnings.append("cost metadata was reported by Claude Code")
        return ModelProviderResponse(
            model_call_id=request.model_call_id,
            provider_id=provider_id,
            requested_model=request.requested_model,
            resolved_model=model,
            content=advisory.summary,
            structured_output=advisory.model_dump(mode="json"),
            finish_reason=ModelFinishReason.COMPLETED,
            usage=usage,
            latency_ms=duration_ms,
            warnings=tuple(warnings),
        )
    except (ValueError, json.JSONDecodeError) as error:
        raise ProviderInvalidResponseError(
            provider_id=provider_id,
            message="Claude Code returned invalid advisory JSON",
        ) from error


def _map_usage(value: object) -> TokenUsage | None:
    if not isinstance(value, dict):
        return None
    input_tokens = value.get("input_tokens")
    output_tokens = value.get("output_tokens")
    return TokenUsage(
        input_tokens=input_tokens if isinstance(input_tokens, int) else None,
        output_tokens=output_tokens if isinstance(output_tokens, int) else None,
    )


def advisory_schema_json() -> str:
    return json.dumps(ADVISORY_JSON_SCHEMA, sort_keys=True, separators=(",", ":"))
