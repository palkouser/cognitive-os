"""Fail-closed host configuration for governed model routing."""

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel


class RoutingConfiguration(ImmutableContractModel):
    maximum_models: int = Field(default=256, ge=1, le=256)
    maximum_profile_revisions: int = Field(default=1_000, ge=1, le=1_000)
    maximum_policy_revisions: int = Field(default=1_000, ge=1, le=1_000)
    maximum_candidate_models: int = Field(default=32, ge=1, le=32)
    maximum_fallback_models: int = Field(default=8, ge=0, le=8)
    maximum_task_signature_dimensions: int = Field(default=32, ge=1, le=32)
    maximum_observations_per_import: int = Field(default=10_000, ge=1, le=10_000)
    maximum_experiment_cases: int = Field(default=10_000, ge=1, le=10_000)
    maximum_role_assignments: int = Field(default=8, ge=1, le=8)
    maximum_multi_model_calls: int = Field(default=8, ge=1, le=8)
    maximum_fallback_depth: int = Field(default=4, ge=0, le=4)
    maximum_decision_trace_bytes: int = Field(default=1_048_576, ge=1, le=1_048_576)
    maximum_statistics_cohorts: int = Field(default=100_000, ge=1, le=100_000)
    maximum_routing_seconds: int = Field(default=10, ge=1, le=10)
    minimum_measured_samples: int = Field(default=5, ge=1)
    minimum_adaptive_samples: int = Field(default=30, ge=1)
    minimum_shadow_cases: int = Field(default=50, ge=1)
    minimum_promotion_benchmark_cases: int = Field(default=30, ge=1)
    minimum_live_outcome_cases: int = Field(default=10, ge=1)
    minimum_required_quality_improvement: float = Field(default=0.02, ge=0, le=1)
    maximum_allowed_safety_regression: float = Field(default=0.0, ge=0, le=1)
    maximum_allowed_policy_regression: float = Field(default=0.0, ge=0, le=1)
    static_policy_id: str = "default-static"
    adaptive_execution_enabled: bool = False
    shadow_routing_enabled: bool = True
    shadow_execution_enabled: bool = False
    exploration_enabled: bool = False
    learned_routing_enabled: bool = False
    allow_provider_declared_capabilities: bool = True
    allow_provider_self_reported_measurements: bool = False
    allow_unknown_cost: bool = True
    allow_unknown_latency: bool = True
    allow_automatic_policy_promotion: bool = False
    allow_automatic_provider_enablement: bool = False
    allow_credential_storage: bool = False
    allow_external_routing_runtime: bool = False
    allow_unbounded_multi_model_patterns: bool = False

    @model_validator(mode="after")
    def reject_forbidden_authority(self) -> "RoutingConfiguration":
        if any(
            (
                self.shadow_execution_enabled,
                self.exploration_enabled,
                self.learned_routing_enabled,
                self.allow_provider_self_reported_measurements,
                self.allow_automatic_policy_promotion,
                self.allow_automatic_provider_enablement,
                self.allow_credential_storage,
                self.allow_external_routing_runtime,
                self.allow_unbounded_multi_model_patterns,
            )
        ):
            raise ValueError(
                "routing authority, credentials, exploration, and shadow execution are forbidden"
            )
        if self.adaptive_execution_enabled:
            raise ValueError(
                "adaptive execution requires a persisted approved policy, not configuration"
            )
        return self


def load_routing_configuration(path: Path) -> RoutingConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("routing"), dict):
        raise ValueError("routing configuration requires a routing mapping")
    return RoutingConfiguration.model_validate(raw["routing"])
