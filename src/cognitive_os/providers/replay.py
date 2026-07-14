"""Sanitized deterministic normalized-response replay."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, utc_now
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

from .errors import ProviderInvalidResponseError


def request_fingerprint(request: ModelProviderRequest) -> str:
    semantic = request.model_dump(
        mode="json",
        exclude={
            "model_call_id",
            "task_run_id",
            "step_id",
            "correlation_id",
            "metadata",
        },
    )
    encoded = json.dumps(semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


class ReplayFixture(ImmutableContractModel):
    fixture_version: int = Field(default=1, ge=1, le=1)
    request_fingerprint: Sha256Hex
    provider_id: NonEmptyStr = "replay"
    source_provider: NonEmptyStr
    response: ModelProviderResponse
    stream_events: tuple[ProviderStreamEvent, ...] = ()

    @model_validator(mode="after")
    def sequence_is_contiguous(self) -> ReplayFixture:
        if self.stream_events and tuple(event.sequence for event in self.stream_events) != tuple(
            range(1, len(self.stream_events) + 1)
        ):
            raise ValueError("replay stream sequence must be contiguous")
        return self


class ReplayProvider:
    def __init__(self, fixtures: Iterable[ReplayFixture], *, provider_id: str = "replay") -> None:
        self._identity = ProviderIdentity(
            provider_id=provider_id,
            display_name="Deterministic replay provider",
            provider_kind=ProviderKind.REPLAY,
            adapter_version="1",
        )
        self._fixtures: dict[str, ReplayFixture] = {}
        for fixture in fixtures:
            if fixture.request_fingerprint in self._fixtures:
                raise ValueError("duplicate replay request fingerprint")
            self._fixtures[fixture.request_fingerprint] = fixture

    @classmethod
    def from_directory(cls, directory: Path) -> ReplayProvider:
        fixtures: list[ReplayFixture] = []
        for path in sorted(directory.glob("*.json")):
            try:
                fixtures.append(ReplayFixture.model_validate_json(path.read_text(encoding="utf-8")))
            except (ValueError, OSError) as error:
                raise ProviderInvalidResponseError(
                    provider_id="replay",
                    error_code="malformed_replay_fixture",
                    message=f"invalid replay fixture: {path.name}",
                ) from error
        return cls(fixtures)

    @property
    def provider_id(self) -> str:
        return self._identity.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return True

    def _require_fixture(self, request: ModelProviderRequest) -> ReplayFixture:
        fixture = self._fixtures.get(request_fingerprint(request))
        if fixture is None:
            raise ProviderInvalidResponseError(
                provider_id=self.provider_id,
                error_code="replay_fixture_not_found",
                message="no replay fixture matches the normalized request",
            )
        return fixture

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        fixture = self._require_fixture(request)
        return fixture.response.model_copy(
            update={
                "model_call_id": request.model_call_id,
                "provider_id": self.provider_id,
                "requested_model": request.requested_model,
            }
        )

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        fixture = self._require_fixture(request)
        if not fixture.stream_events:
            raise ProviderInvalidResponseError(
                provider_id=self.provider_id,
                error_code="replay_stream_unavailable",
                message="matching replay fixture has no stream events",
            )
        for event in fixture.stream_events:
            yield event

    async def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.AVAILABLE,
            checked_at=utc_now(),
            latency_ms=0,
            message=f"{len(self._fixtures)} replay fixtures loaded",
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=model_id,
            provider_id=self.provider_id,
            supports_streaming=True,
            supports_tool_calls=True,
            supports_parallel_tool_calls=True,
            supports_structured_output=True,
            maximum_context_tokens=131072,
            maximum_output_tokens=32768,
        )
