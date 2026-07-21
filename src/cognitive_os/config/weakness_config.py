"""Fail-closed host configuration for diagnostic weakness mining."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class WeaknessConfiguration(ImmutableContractModel):
    maximum_mining_runs: int = Field(default=100_000, ge=1, le=100_000)
    maximum_concurrent_mining_runs: int = Field(default=4, ge=1, le=4)
    maximum_source_records_per_run: int = Field(default=100_000, ge=1, le=100_000)
    maximum_source_artifacts_per_run: int = Field(default=10_000, ge=0, le=10_000)
    maximum_signals_per_run: int = Field(default=100_000, ge=1, le=100_000)
    maximum_signals_per_signature: int = Field(default=10_000, ge=1, le=10_000)
    maximum_groups_per_run: int = Field(default=25_000, ge=1, le=25_000)
    maximum_cluster_members: int = Field(default=10_000, ge=1, le=10_000)
    maximum_clusters_per_run: int = Field(default=10_000, ge=1, le=10_000)
    maximum_sources_per_signal: int = Field(default=64, ge=1, le=64)
    maximum_sources_per_weakness: int = Field(default=2_048, ge=1, le=2_048)
    maximum_counterexamples: int = Field(default=256, ge=0, le=256)
    maximum_evidence_package_bytes: int = Field(default=33_554_432, ge=1, le=33_554_432)
    maximum_summary_bytes: int = Field(default=65_536, ge=1, le=65_536)
    maximum_queue_entries: int = Field(default=100_000, ge=1, le=100_000)
    maximum_queue_dependencies: int = Field(default=32, ge=0, le=32)
    maximum_group_query_depth: int = Field(default=8, ge=1, le=8)
    maximum_mining_seconds: int = Field(default=1_800, ge=1, le=1_800)
    minimum_signals_for_confirmation: int = Field(default=2, ge=1)
    minimum_distinct_tasks_for_confirmation: int = Field(default=2, ge=1)
    minimum_reproduction_count: int = Field(default=2, ge=1)
    minimum_monitoring_task_count: int = Field(default=10, ge=1)
    minimum_resolution_task_count: int = Field(default=20, ge=1)
    minimum_evidence_coverage: float = Field(default=0.80, ge=0, le=1)
    allow_single_critical_safety_confirmation: bool = True
    critical_safety_confirmation_requires_operator: bool = True
    exact_grouping_enabled: bool = True
    optional_clustering_enabled: bool = False
    clustering_can_mutate_authority: bool = False
    provider_assisted_clustering_enabled: bool = False
    automatic_confirmation_enabled: bool = False
    automatic_resolution_enabled: bool = False
    automatic_proposal_creation_enabled: bool = False
    automatic_source_modification_enabled: bool = False
    external_network_sources_enabled: bool = False

    @model_validator(mode="after")
    def reject_forbidden_authority(self) -> "WeaknessConfiguration":
        if not self.exact_grouping_enabled or any(
            (
                self.clustering_can_mutate_authority,
                self.provider_assisted_clustering_enabled,
                self.automatic_confirmation_enabled,
                self.automatic_resolution_enabled,
                self.automatic_proposal_creation_enabled,
                self.automatic_source_modification_enabled,
                self.external_network_sources_enabled,
            )
        ):
            raise ValueError("weakness mining cannot receive modification or provider authority")
        return self


def load_weakness_configuration(path: Path) -> WeaknessConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("weakness"), dict):
        raise ValueError("weakness configuration requires a weakness mapping")
    return WeaknessConfiguration.model_validate(raw["weakness"])
