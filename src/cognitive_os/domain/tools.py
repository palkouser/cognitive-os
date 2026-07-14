"""Typed, implementation-neutral Tool Plane contracts."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .base import ImmutableContractModel
from .common import ArtifactRef, ErrorInfo, JsonValue


class ToolSource(StrEnum):
    BUILT_IN = "built_in"
    MCP = "mcp"


class ToolRiskLevel(StrEnum):
    R0 = "r0"
    R1 = "r1"
    R2 = "r2"
    R3 = "r3"


class ToolSideEffect(StrEnum):
    NONE = "none"
    LOCAL_READ = "local_read"
    LOCAL_WRITE = "local_write"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    PRIVILEGED = "privileged"


class ToolExecutionMode(StrEnum):
    HOST_READ_ONLY = "host_read_only"
    SANDBOX = "sandbox"
    MCP = "mcp"


class ToolExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    DENIED = "denied"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class ToolDescriptor(ImmutableContractModel):
    tool_id: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)+$")
    version: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=4000)
    source: ToolSource
    input_schema: dict[str, JsonValue]
    output_schema: dict[str, JsonValue]
    risk_level: ToolRiskLevel
    side_effects: tuple[ToolSideEffect, ...] = (ToolSideEffect.NONE,)
    execution_mode: ToolExecutionMode
    provider_visible: bool = False
    idempotent: bool = False
    deterministic: bool = False
    default_timeout_seconds: float = Field(gt=0, le=3600)
    required_permissions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    descriptor_hash: str = ""

    @model_validator(mode="after")
    def verify_hash(self) -> ToolDescriptor:
        expected = self.computed_hash()
        if self.descriptor_hash and self.descriptor_hash != expected:
            raise ValueError("descriptor hash does not match descriptor content")
        object.__setattr__(self, "descriptor_hash", expected)
        return self

    def computed_hash(self) -> str:
        content = self.model_dump(mode="json", exclude={"descriptor_hash"})
        encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()


class ToolInvocation(ImmutableContractModel):
    tool_call_id: UUID
    task_run_id: UUID
    step_id: UUID | None = None
    correlation_id: UUID
    tool_id: str
    tool_version: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)
    requested_at: datetime
    requested_by: str

    @field_validator("arguments", mode="before")
    @classmethod
    def copy_arguments(cls, value: Any) -> Any:
        return dict(value) if isinstance(value, dict) else value


class ToolExecutionResult(ImmutableContractModel):
    tool_call_id: UUID
    tool_id: str
    tool_version: str
    status: ToolExecutionStatus
    started_at: datetime
    finished_at: datetime
    exit_code: int | None = None
    result: JsonValue = None
    result_artifacts: tuple[ArtifactRef, ...] = ()
    stdout_artifact: ArtifactRef | None = None
    stderr_artifact: ArtifactRef | None = None
    warnings: tuple[str, ...] = ()
    errors: tuple[ErrorInfo, ...] = ()
    sandbox_id: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> ToolExecutionResult:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        return self


class ToolExecutionContext(ImmutableContractModel):
    workspace: str
    timeout_seconds: float = Field(gt=0, le=3600)
    maximum_stdout_bytes: int = Field(gt=0)
    maximum_stderr_bytes: int = Field(gt=0)
    maximum_artifact_bytes: int = Field(gt=0)
