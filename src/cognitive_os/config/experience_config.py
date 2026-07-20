"""Fail-closed host configuration for the Experience Compiler."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class ExperienceConfiguration(ImmutableContractModel):
    maximum_sources_per_compilation: int = Field(default=512, ge=1, le=512)
    maximum_events_per_compilation: int = Field(default=100_000, ge=1, le=100_000)
    maximum_artifacts_per_compilation: int = Field(default=2_048, ge=1, le=2_048)
    maximum_segments: int = Field(default=2_048, ge=1, le=2_048)
    maximum_steps: int = Field(default=10_000, ge=1, le=10_000)
    maximum_failed_branches: int = Field(default=512, ge=0, le=512)
    maximum_corrections: int = Field(default=256, ge=0, le=256)
    maximum_contributions: int = Field(default=4_096, ge=0, le=4_096)
    maximum_candidates: int = Field(default=256, ge=1, le=256)
    maximum_candidate_sources: int = Field(default=128, ge=1, le=128)
    maximum_inline_summary_bytes: int = Field(default=65_536, ge=1, le=65_536)
    maximum_analysis_artifact_bytes: int = Field(default=16_777_216, ge=1, le=16_777_216)
    maximum_candidate_artifact_bytes: int = Field(default=8_388_608, ge=1, le=8_388_608)
    maximum_manifest_bytes: int = Field(default=2_097_152, ge=1, le=2_097_152)
    maximum_provider_excerpt_bytes: int = Field(default=131_072, ge=1, le=131_072)
    maximum_provider_proposals: int = Field(default=64, ge=0, le=64)
    maximum_compilation_seconds: int = Field(default=1_800, ge=1, le=1_800)
    maximum_provider_calls_per_compilation: int = Field(default=2, ge=0, le=2)
    minimum_generalizability_sample_count: int = Field(default=2, ge=2, le=10_000)
    minimum_reproducibility_count: int = Field(default=2, ge=2, le=10_000)
    minimum_candidate_evidence_sources: int = Field(default=1, ge=1, le=128)
    allow_provider_assisted_analysis: bool = False
    allow_provider_source_creation: bool = False
    allow_provider_causal_decision: bool = False
    allow_automatic_candidate_routing: bool = False
    allow_automatic_destination_write: bool = False
    allow_automatic_promotion: bool = False
    allow_external_network_sources: bool = False

    @model_validator(mode="after")
    def prohibit_deferred_authority(self) -> "ExperienceConfiguration":
        if any(
            (
                self.allow_provider_source_creation,
                self.allow_provider_causal_decision,
                self.allow_automatic_candidate_routing,
                self.allow_automatic_destination_write,
                self.allow_automatic_promotion,
                self.allow_external_network_sources,
            )
        ):
            raise ValueError("deferred or provider-authoritative experience features are forbidden")
        return self


def load_experience_configuration(path: Path) -> ExperienceConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("experience"), dict):
        raise ValueError("experience configuration requires an experience mapping")
    return ExperienceConfiguration.model_validate(raw["experience"])
