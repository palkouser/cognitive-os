"""Strict local STDIO MCP configuration."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class McpServerConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = False
    transport: str = "stdio"
    command: Path
    arguments: tuple[str, ...] = ()
    working_directory: Path
    environment_allowlist: tuple[str, ...] = ()
    startup_timeout_seconds: float = Field(default=15, gt=0, le=120)
    call_timeout_seconds: float = Field(default=60, gt=0, le=600)

    @field_validator("command")
    @classmethod
    def command_is_absolute(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("MCP command must be absolute")
        if value.name in {"npx", "uvx", "pip", "pipx"}:
            raise ValueError("automatic MCP package acquisition is forbidden")
        return value

    @field_validator("transport")
    @classmethod
    def stdio_only(cls, value: str) -> str:
        if value != "stdio":
            raise ValueError("Sprint 5 supports only MCP STDIO")
        return value


class McpConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    servers: dict[str, McpServerConfiguration]


def load_mcp_configuration(path: Path) -> McpConfiguration:
    with path.open(encoding="utf-8") as stream:
        raw: Any = yaml.safe_load(stream)
    return McpConfiguration.model_validate(raw)
