"""Fail-closed Python Coding Agent host configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, field_validator, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.coding import CodingCommandPolicy, CodingLimits, PathPolicy


class CodingCleanupPolicy(ImmutableContractModel):
    success: str = "archive"
    failure: str = "preserve_after_failure"
    cancellation: str = "archive"


class CodingArtifactPolicy(ImmutableContractModel):
    retention_days: int = Field(default=30, ge=1, le=3650)
    maximum_archive_bytes: int = Field(default=50_000_000, ge=1)
    include_command_output: bool = True


class CodingConfiguration(ImmutableContractModel):
    worktree_root: Path
    archive_root: Path
    allowed_repository_roots: tuple[Path, ...] = Field(min_length=1)
    supported_python_version: str = "3.12"
    limits: CodingLimits = CodingLimits()
    commands: CodingCommandPolicy
    paths: PathPolicy
    cleanup: CodingCleanupPolicy = CodingCleanupPolicy()
    artifacts: CodingArtifactPolicy = CodingArtifactPolicy()

    @field_validator("worktree_root", "archive_root")
    @classmethod
    def absolute_host_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            raise ValueError("host paths must be absolute")
        return value

    @field_validator("allowed_repository_roots")
    @classmethod
    def absolute_repository_roots(cls, values: tuple[Path, ...]) -> tuple[Path, ...]:
        if any(not value.is_absolute() for value in values):
            raise ValueError("repository roots must be absolute")
        return values

    @model_validator(mode="after")
    def distinct_private_roots(self) -> CodingConfiguration:
        if self.worktree_root == self.archive_root:
            raise ValueError("worktree and archive roots must differ")
        return self


def load_coding_configuration(path: Path) -> CodingConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("coding"), dict):
        raise ValueError("coding configuration requires a coding mapping")
    return CodingConfiguration.model_validate(raw["coding"])
