"""Fail-closed host configuration for governed strategies."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class StrategyConfiguration(ImmutableContractModel):
    maximum_problem_classes: int = Field(default=10_000, ge=1, le=10_000)
    maximum_revisions_per_strategy: int = Field(default=1_000, ge=1, le=1_000)
    maximum_phases: int = Field(default=32, ge=1, le=32)
    maximum_phase_dependencies: int = Field(default=64, ge=0, le=64)
    maximum_phase_branches: int = Field(default=16, ge=0, le=16)
    maximum_skill_bindings: int = Field(default=32, ge=0, le=32)
    maximum_fallback_skills: int = Field(default=16, ge=0, le=16)
    maximum_model_role_bindings: int = Field(default=16, ge=0, le=16)
    maximum_tool_requirements: int = Field(default=32, ge=0, le=32)
    maximum_verifier_requirements: int = Field(default=32, ge=0, le=32)
    maximum_context_requirements: int = Field(default=16, ge=0, le=16)
    maximum_known_failure_modes: int = Field(default=32, ge=0, le=32)
    maximum_stop_conditions: int = Field(default=16, ge=1, le=16)
    maximum_source_references: int = Field(default=64, ge=1, le=64)
    maximum_graph_edges_per_revision: int = Field(default=256, ge=0, le=256)
    maximum_graph_query_depth: int = Field(default=8, ge=1, le=8)
    maximum_graph_query_nodes: int = Field(default=5_000, ge=1, le=5_000)
    maximum_graph_query_edges: int = Field(default=10_000, ge=1, le=10_000)
    maximum_lineage_depth: int = Field(default=128, ge=1, le=128)
    maximum_selection_candidates: int = Field(default=256, ge=1, le=256)
    maximum_selection_trace_bytes: int = Field(default=1_048_576, ge=1, le=1_048_576)
    maximum_strategy_executions_per_task: int = Field(default=4, ge=1, le=4)
    maximum_strategy_fallback_depth: int = Field(default=4, ge=0, le=4)
    maximum_plan_steps: int = Field(default=128, ge=1, le=128)
    maximum_plan_branches: int = Field(default=32, ge=0, le=32)
    maximum_repairs_per_execution: int = Field(default=3, ge=0, le=3)
    maximum_execution_seconds: int = Field(default=3_600, ge=1, le=3_600)
    minimum_statistics_sample: int = Field(default=5, ge=1, le=1_000)
    minimum_comparative_sample: int = Field(default=10, ge=1, le=1_000)
    cold_start_requires_approval: bool = True
    cold_start_allowed_without_alternative: bool = True
    accepted_outcome_weight: float = Field(default=1.0, ge=-1, le=1)
    verifier_quality_weight: float = Field(default=0.25, ge=-1, le=1)
    repair_cost_weight: float = Field(default=-0.15, ge=-1, le=1)
    latency_weight: float = Field(default=-0.10, ge=-1, le=1)
    token_cost_weight: float = Field(default=-0.10, ge=-1, le=1)
    safety_failure_weight: float = Field(default=-1.0, ge=-1, le=1)
    fallback_frequency_weight: float = Field(default=-0.20, ge=-1, le=1)
    specificity_weight: float = Field(default=0.20, ge=-1, le=1)
    allow_provider_strategy_selection: bool = False
    allow_automatic_strategy_creation: bool = False
    allow_automatic_strategy_promotion: bool = False
    allow_learned_strategy_ranking: bool = False
    allow_dynamic_skill_registration: bool = False
    allow_dynamic_tool_registration: bool = False
    allow_dynamic_verifier_registration: bool = False
    allow_external_graph_database: bool = False

    @model_validator(mode="after")
    def prohibit_deferred_authority(self) -> "StrategyConfiguration":
        if any(
            (
                self.allow_provider_strategy_selection,
                self.allow_automatic_strategy_creation,
                self.allow_automatic_strategy_promotion,
                self.allow_learned_strategy_ranking,
                self.allow_dynamic_skill_registration,
                self.allow_dynamic_tool_registration,
                self.allow_dynamic_verifier_registration,
                self.allow_external_graph_database,
            )
        ):
            raise ValueError("deferred or provider-authoritative strategy features are forbidden")
        if self.minimum_comparative_sample < self.minimum_statistics_sample:
            raise ValueError("comparative sample threshold is below the ranking threshold")
        return self


def load_strategy_configuration(path: Path) -> StrategyConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("strategies"), dict):
        raise ValueError("strategy configuration requires a strategies mapping")
    return StrategyConfiguration.model_validate(raw["strategies"])
