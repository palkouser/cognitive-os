"""Bounded verifier configuration loading."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class VerifierEntryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    timeout_seconds: float = Field(default=30, gt=0, le=3600)
    maximum_output_bytes: int = Field(default=1_048_576, gt=0)
    maximum_expression_nodes: int = Field(default=512, gt=0, le=4096)
    maximum_symbol_count: int = Field(default=32, gt=0, le=256)
    maximum_ast_nodes: int = Field(default=1024, gt=0, le=8192)


class VerificationLimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    maximum_evidence_artifacts: int = Field(default=32, gt=0, le=256)
    maximum_inline_subject_bytes: int = Field(default=1_048_576, gt=0)
    maximum_finding_count: int = Field(default=256, gt=0, le=4096)
    parallel_execution: bool = False

    @model_validator(mode="after")
    def sequential_only(self) -> VerificationLimitsConfig:
        if self.parallel_execution:
            raise ValueError("parallel verifier execution is not supported in Sprint 7")
        return self


class VerifierConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verifiers: dict[str, VerifierEntryConfig] = Field(default_factory=dict)
    verification: VerificationLimitsConfig = Field(default_factory=VerificationLimitsConfig)


def load_verifier_config(path: Path) -> VerifierConfig:
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return VerifierConfig.model_validate(value)
