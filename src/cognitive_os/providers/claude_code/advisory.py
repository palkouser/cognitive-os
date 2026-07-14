"""Claude Code bounded read-only advisory provider."""

from __future__ import annotations

from collections.abc import AsyncIterator

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
from cognitive_os.providers.errors import ProviderUnsupportedCapabilityError

from .config import ClaudeCodeProviderConfig
from .mapping import advisory_schema_json, map_advisory_response
from .process import ClaudeProcessRunner

_ADVISORY_POLICY = """Analyze only.
Do not edit files.
Do not create files.
Do not run destructive commands.
Return the requested structured advisory result.
"""


class ClaudeCodeAdvisoryProvider:
    def __init__(
        self,
        config: ClaudeCodeProviderConfig,
        *,
        runner: ClaudeProcessRunner | None = None,
    ) -> None:
        self.config = config
        self._runner = runner or ClaudeProcessRunner(config)
        self._identity = ProviderIdentity(
            provider_id=config.provider_id,
            display_name="Claude Code advisory provider",
            provider_kind=ProviderKind.CLI_AGENT,
            adapter_version="1",
        )

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def identity(self) -> ProviderIdentity:
        return self._identity

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    async def complete(self, request: ModelProviderRequest) -> ModelProviderResponse:
        prompt_parts = [_ADVISORY_POLICY]
        if request.system_instructions:
            prompt_parts.append(request.system_instructions)
        prompt_parts.extend(message.content for message in request.messages)
        result = await self._runner.run(
            prompt="\n\n".join(prompt_parts),
            schema=advisory_schema_json(),
        )
        return map_advisory_response(
            result.stdout,
            request,
            provider_id=self.provider_id,
            duration_ms=result.duration_ms,
        )

    async def stream(self, request: ModelProviderRequest) -> AsyncIterator[ProviderStreamEvent]:
        del request
        raise ProviderUnsupportedCapabilityError(
            provider_id=self.provider_id,
            message="Claude Code advisory streaming is unsupported",
        )
        yield

    async def health_check(self) -> ProviderHealth:
        available, message = await self._runner.availability()
        return ProviderHealth(
            provider_id=self.provider_id,
            status=ProviderStatus.AVAILABLE if available else ProviderStatus.UNAVAILABLE,
            checked_at=utc_now(),
            configured_model="claude-code",
            message=message,
        )

    async def get_model_capabilities(self, model_id: str) -> ModelCapabilities:
        return ModelCapabilities(
            model_id=model_id,
            provider_id=self.provider_id,
            supports_streaming=False,
            supports_tool_calls=False,
            supports_parallel_tool_calls=False,
            supports_structured_output=True,
            supports_system_messages=True,
            supports_seed=False,
            maximum_context_tokens=None,
            maximum_output_tokens=None,
        )
