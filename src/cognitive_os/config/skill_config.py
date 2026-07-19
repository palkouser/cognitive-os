"""Fail-closed host configuration for governed procedural skills."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class SkillConfiguration(ImmutableContractModel):
    maximum_package_files: int = Field(default=256, ge=2, le=256)
    maximum_package_bytes: int = Field(default=16_777_216, ge=1, le=16_777_216)
    maximum_single_file_bytes: int = Field(default=2_097_152, ge=1, le=2_097_152)
    maximum_metadata_bytes: int = Field(default=131_072, ge=1, le=131_072)
    maximum_instruction_bytes: int = Field(default=262_144, ge=1, le=262_144)
    maximum_resource_bytes: int = Field(default=8_388_608, ge=1, le=8_388_608)
    maximum_archive_expansion_ratio: int = Field(default=20, ge=1, le=20)
    maximum_directory_depth: int = Field(default=12, ge=1, le=12)
    maximum_preconditions: int = Field(default=32, ge=0, le=32)
    maximum_steps: int = Field(default=64, ge=1, le=64)
    maximum_fallback_depth: int = Field(default=4, ge=0, le=4)
    maximum_tool_requirements: int = Field(default=32, ge=0, le=32)
    maximum_verifier_requirements: int = Field(default=32, ge=0, le=32)
    maximum_provider_requirements: int = Field(default=16, ge=0, le=16)
    maximum_context_requirements: int = Field(default=16, ge=0, le=16)
    maximum_source_references: int = Field(default=64, ge=1, le=64)
    maximum_executions_per_task: int = Field(default=8, ge=1, le=8)
    maximum_repairs_per_execution: int = Field(default=3, ge=0, le=3)
    maximum_provider_calls_per_execution: int = Field(default=8, ge=0, le=8)
    maximum_tool_calls_per_execution: int = Field(default=32, ge=0, le=32)
    maximum_context_builds_per_execution: int = Field(default=8, ge=0, le=8)
    maximum_execution_seconds: int = Field(default=1800, ge=1, le=1800)
    minimum_regression_cases: int = Field(default=1, ge=1, le=100)
    minimum_verified_executions_for_statistics: int = Field(default=3, ge=1, le=100)
    minimum_statistics_sample_for_ranking: int = Field(default=5, ge=1, le=100)
    allow_imported_verified_status: bool = False
    allow_dynamic_tool_registration: bool = False
    allow_dynamic_verifier_registration: bool = False
    allow_arbitrary_precondition_code: bool = False
    allow_direct_script_execution: bool = False
    allow_network_package_download: bool = False
    allow_automatic_skill_generation: bool = False
    allow_automatic_skill_promotion: bool = False
    allow_provider_skill_selection: bool = False
    allow_unverified_skill_execution: bool = False
    allow_global_scope: bool = False

    @model_validator(mode="after")
    def prohibit_deferred_authority(self) -> SkillConfiguration:
        forbidden = (
            self.allow_imported_verified_status,
            self.allow_dynamic_tool_registration,
            self.allow_dynamic_verifier_registration,
            self.allow_arbitrary_precondition_code,
            self.allow_direct_script_execution,
            self.allow_network_package_download,
            self.allow_automatic_skill_generation,
            self.allow_automatic_skill_promotion,
            self.allow_provider_skill_selection,
            self.allow_unverified_skill_execution,
        )
        if any(forbidden):
            raise ValueError("deferred or provider-authoritative skill features are forbidden")
        if (
            self.minimum_verified_executions_for_statistics
            > self.minimum_statistics_sample_for_ranking
        ):
            raise ValueError("statistics ranking threshold is below the verified sample threshold")
        return self


def load_skill_configuration(path: Path) -> SkillConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("skills"), dict):
        raise ValueError("skill configuration requires a skills mapping")
    return SkillConfiguration.model_validate(raw["skills"])
