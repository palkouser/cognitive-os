"""Validated provider configuration without credential values."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

import yaml
from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.provider import ProviderKind


class MiniMaxKeyType(StrEnum):
    PAY_AS_YOU_GO = "pay_as_you_go"
    SUBSCRIPTION = "subscription"


class ClaudeOutputFormat(StrEnum):
    JSON = "json"
    STREAM_JSON = "stream-json"


class MiniMaxProviderConfig(ImmutableContractModel):
    provider_id: NonEmptyStr = "minimax"
    kind: Literal[ProviderKind.NETWORK_API] = ProviderKind.NETWORK_API
    base_url: str = "https://api.minimax.io/v1"
    model: NonEmptyStr = "MiniMax-M3"
    api_key_environment_variable: NonEmptyStr = "COGOS_MINIMAX_API_KEY"
    key_type: MiniMaxKeyType
    timeout_seconds: float = Field(default=120, gt=0)
    maximum_attempts: int = Field(default=3, ge=1, le=10)
    maximum_context_tokens: int = Field(default=131072, ge=1, le=131072)
    default_max_output_tokens: int = Field(default=8192, ge=1)
    supports_tool_calls: bool = False
    supports_structured_output: bool = False
    enabled: bool = True

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("base_url must be an absolute HTTP or HTTPS URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url must not contain credentials, query, or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def output_fits_context(self) -> MiniMaxProviderConfig:
        if self.default_max_output_tokens > self.maximum_context_tokens:
            raise ValueError("default output tokens cannot exceed the context limit")
        return self


class ClaudeCodeProviderConfig(ImmutableContractModel):
    provider_id: NonEmptyStr = "claude-code"
    kind: Literal[ProviderKind.CLI_AGENT] = ProviderKind.CLI_AGENT
    executable: NonEmptyStr = "claude"
    working_directory: Path
    timeout_seconds: float = Field(default=300, gt=0)
    maximum_turns: int = Field(default=3, ge=1, le=20)
    maximum_budget_usd: float | None = Field(default=None, gt=0)
    output_format: ClaudeOutputFormat = ClaudeOutputFormat.JSON
    enabled: bool = False


ProviderAdapterConfig = Annotated[
    MiniMaxProviderConfig | ClaudeCodeProviderConfig,
    Field(discriminator="kind"),
]


class ProviderConfiguration(ImmutableContractModel):
    default_provider_id: NonEmptyStr
    providers: dict[str, ProviderAdapterConfig]

    @model_validator(mode="after")
    def validate_provider_ids(self) -> ProviderConfiguration:
        if not self.providers:
            raise ValueError("at least one provider configuration is required")
        for key, provider in self.providers.items():
            if key != provider.provider_id:
                raise ValueError("provider mapping key must equal provider_id")
        if self.default_provider_id not in self.providers:
            raise ValueError("default provider is not configured")
        return self


def load_provider_configuration(path: Path) -> ProviderConfiguration:
    with path.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    if not isinstance(document, dict):
        raise ValueError("provider configuration must be a YAML mapping")
    providers = document.get("providers")
    if isinstance(providers, dict):
        document = dict(document)
        document["providers"] = {
            key: ({"provider_id": key, **value} if isinstance(value, dict) else value)
            for key, value in providers.items()
        }
    return ProviderConfiguration.model_validate(document)
