"""Fail-closed host configuration for controlled changes."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.changes import ImplementationChannel, NetworkPolicy, PromotionMode


class ChangeIntakeConfiguration(ImmutableContractModel):
    require_exact_proposal_revision: bool = True
    require_approved_for_experiment: bool = True
    require_passing_proposal_verifier_bundle: bool = True
    require_frozen_source_snapshot: bool = True


class ChangeIsolationConfiguration(ImmutableContractModel):
    workspace_root: Path
    require_external_worktree_root: bool = True
    require_database_clone: bool = True
    require_artifact_namespace: bool = True
    network_default: NetworkPolicy = NetworkPolicy.DISABLED
    max_parallel_experiments: int = Field(default=2, ge=1, le=2)
    normal_cpu_limit: int = Field(default=4, ge=1, le=64)
    normal_memory_gb: int = Field(default=8, ge=1, le=256)
    normal_wall_time_seconds: int = Field(default=3600, ge=1, le=86400)

    @model_validator(mode="after")
    def external_absolute_root(self) -> ChangeIsolationConfiguration:
        if not self.workspace_root.is_absolute() or self.workspace_root == Path("/"):
            raise ValueError("controlled-change workspace root must be a bounded absolute path")
        return self


class ChangeImplementationConfiguration(ImmutableContractModel):
    allowed_channels: tuple[ImplementationChannel, ...] = (
        ImplementationChannel.DETERMINISTIC_TRANSFORMATION,
        ImplementationChannel.COGNITIVE_OS_CODING_AGENT,
        ImplementationChannel.CLAUDE_CODE_ROLE,
    )
    external_evolution_adapter_enabled: bool = False
    require_typed_operations: bool = True
    forbid_active_checkout: bool = True
    forbid_active_database: bool = True
    forbid_release_operations: bool = True


class ChangeEvaluationConfiguration(ImmutableContractModel):
    fail_fast_on_hard_failure: bool = True
    require_target_benchmark: bool = True
    require_historical_regression: bool = True
    require_unrelated_domain_regression: bool = True
    require_security_policy_gates: bool = True
    require_migration_schema_gates: bool = True
    require_dependency_packaging_gates: bool = True
    require_backup_restore_rollback: bool = True


class ChangePromotionConfiguration(ImmutableContractModel):
    require_separate_approval: bool = True
    tier_0_mode: PromotionMode = PromotionMode.REPOSITORY_BUNDLE_ONLY
    tier_1_mode: PromotionMode = PromotionMode.GOVERNED_DESTINATION_ADAPTER
    tier_2_mode: PromotionMode = PromotionMode.REPOSITORY_BUNDLE_ONLY
    tier_3_mode: PromotionMode = PromotionMode.MANUAL_REVIEW_ONLY
    runtime_git_merge_enabled: bool = False
    runtime_tag_enabled: bool = False
    runtime_publish_enabled: bool = False


class ChangeRollbackConfiguration(ImmutableContractModel):
    require_pre_promotion_validation: bool = True
    preserve_failed_history: bool = True


class ControlledChangeConfiguration(ImmutableContractModel):
    enabled: bool = True
    intake: ChangeIntakeConfiguration = Field(default_factory=ChangeIntakeConfiguration)
    isolation: ChangeIsolationConfiguration
    implementation: ChangeImplementationConfiguration = Field(
        default_factory=ChangeImplementationConfiguration
    )
    evaluation: ChangeEvaluationConfiguration = Field(default_factory=ChangeEvaluationConfiguration)
    promotion: ChangePromotionConfiguration = Field(default_factory=ChangePromotionConfiguration)
    rollback: ChangeRollbackConfiguration = Field(default_factory=ChangeRollbackConfiguration)

    @model_validator(mode="after")
    def authority_is_fail_closed(self) -> ControlledChangeConfiguration:
        required = (
            self.enabled,
            self.intake.require_exact_proposal_revision,
            self.intake.require_approved_for_experiment,
            self.intake.require_passing_proposal_verifier_bundle,
            self.intake.require_frozen_source_snapshot,
            self.isolation.require_external_worktree_root,
            self.isolation.require_database_clone,
            self.isolation.require_artifact_namespace,
            self.implementation.require_typed_operations,
            self.implementation.forbid_active_checkout,
            self.implementation.forbid_active_database,
            self.implementation.forbid_release_operations,
            self.promotion.require_separate_approval,
            self.rollback.require_pre_promotion_validation,
            self.rollback.preserve_failed_history,
        )
        forbidden = (
            self.implementation.external_evolution_adapter_enabled,
            self.promotion.runtime_git_merge_enabled,
            self.promotion.runtime_tag_enabled,
            self.promotion.runtime_publish_enabled,
        )
        if not all(required) or any(forbidden):
            raise ValueError("controlled-change configuration cannot weaken authority boundaries")
        if self.isolation.network_default is not NetworkPolicy.DISABLED:
            raise ValueError("network must default to disabled")
        return self


def load_controlled_change_configuration(path: Path) -> ControlledChangeConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("controlled_changes"), dict):
        raise ValueError("configuration requires a controlled_changes mapping")
    return ControlledChangeConfiguration.model_validate(raw["controlled_changes"])
