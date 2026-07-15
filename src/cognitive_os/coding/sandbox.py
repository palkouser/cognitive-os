"""Auditable Coding Agent sandbox mount and resource policy."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.coding import CodingLimits, CodingRecord


class CodingSandboxMountDescriptor(CodingRecord):
    """A provider-safe description of the only writable sandbox mount."""

    workspace_id: str
    host_workspace: Path = Field(exclude=True)
    container_workspace: str = "/workspace"
    read_only_root: bool = True
    workspace_writable: bool = True
    network_mode: str = "none"
    drop_all_capabilities: bool = True
    no_new_privileges: bool = True
    user: str
    cpu_limit: int = Field(ge=1, le=4)
    memory_mb: int = Field(ge=128, le=8192)

    @field_validator("host_workspace")
    @classmethod
    def absolute_workspace(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("sandbox host workspace must be absolute")
        return value

    @model_validator(mode="after")
    def enforce_security_boundary(self) -> CodingSandboxMountDescriptor:
        if (
            self.container_workspace != "/workspace"
            or not self.read_only_root
            or not self.workspace_writable
            or self.network_mode != "none"
            or not self.drop_all_capabilities
            or not self.no_new_privileges
        ):
            raise ValueError("Coding Agent sandbox boundary cannot be weakened")
        return self


def build_sandbox_mount_descriptor(
    workspace_id: str, workspace: Path, limits: CodingLimits
) -> CodingSandboxMountDescriptor:
    """Build a sealed descriptor without exposing the main repository to the container."""
    resolved = workspace.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("sandbox workspace is unavailable")
    return CodingSandboxMountDescriptor(
        workspace_id=workspace_id,
        host_workspace=resolved,
        user=f"{os.getuid()}:{os.getgid()}",
        cpu_limit=limits.sandbox_cpu_limit,
        memory_mb=limits.sandbox_memory_mb,
    )
