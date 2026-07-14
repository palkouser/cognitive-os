"""Strict Tool Plane configuration."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cognitive_os.domain.approvals import PolicyAction
from cognitive_os.domain.sandbox import SandboxLimits


class SandboxConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    image: str = "cognitive-os-sandbox:sprint-5"
    limits: SandboxLimits


class ToolPlaneConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    workspace_roots: tuple[Path, ...]
    default_policy: dict[str, PolicyAction]
    sandbox: SandboxConfiguration
    tools: dict[str, bool] = Field(default_factory=dict)

    @field_validator("workspace_roots")
    @classmethod
    def validate_roots(cls, roots: tuple[Path, ...]) -> tuple[Path, ...]:
        if not roots:
            raise ValueError("at least one workspace root is required")
        return tuple(root.expanduser().resolve() for root in roots)


def load_tool_configuration(path: Path) -> ToolPlaneConfiguration:
    with path.open(encoding="utf-8") as stream:
        raw: Any = yaml.safe_load(stream)
    return ToolPlaneConfiguration.model_validate(raw)
