"""Credential-free bounded controller configuration."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr
from cognitive_os.domain.controller import ControllerBudget


class CheckpointConfiguration(ImmutableContractModel):
    create_after_each_step: bool = True
    create_before_wait: bool = True
    continuation_ttl_seconds: int = Field(default=86400, gt=0)


class ControllerExecutionConfiguration(ImmutableContractModel):
    sequential_only: bool = True
    stop_on_required_step_failure: bool = True
    maximum_inline_result_bytes: int = Field(default=1048576, gt=0)

    @model_validator(mode="after")
    def require_sequential(self) -> ControllerExecutionConfiguration:
        if not self.sequential_only:
            raise ValueError("Sprint 6 requires sequential execution")
        return self


class ControllerConfiguration(ImmutableContractModel):
    default_provider_id: NonEmptyStr
    problem_representation_provider_id: NonEmptyStr
    planning_provider_id: NonEmptyStr
    confidence_threshold: float = Field(default=0.75, ge=0, le=1)
    budgets: ControllerBudget
    checkpoint: CheckpointConfiguration = CheckpointConfiguration()
    execution: ControllerExecutionConfiguration = ControllerExecutionConfiguration()
    maximum_controller_iterations: int = Field(default=256, ge=1, le=256)


def load_controller_configuration(path: Path) -> ControllerConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("controller"), dict):
        raise ValueError("controller configuration requires a controller mapping")
    return ControllerConfiguration.model_validate(raw["controller"])
