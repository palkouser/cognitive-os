"""Fail-closed host configuration for governed harness proposals."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.proposals import HarnessProposalType


class ProposalEligibilityConfiguration(ImmutableContractModel):
    confirmed_weaknesses: bool = True
    high_impact_candidates: bool = False
    require_current_revision: bool = True
    require_verified_evidence: bool = True
    require_valid_impact_score: bool = True
    reject_unresolved_source_integrity: bool = True


class ProposalGenerationConfiguration(ImmutableContractModel):
    deterministic_enabled: bool = True
    provider_assisted_enabled: bool = False
    max_proposals_per_weakness: int = Field(default=3, ge=1, le=3)
    max_alternatives_per_proposal: int = Field(default=7, ge=2, le=7)
    max_parallel_analysis_workers: int = Field(default=4, ge=1, le=4)


class ProposalScopeConfiguration(ImmutableContractModel):
    supported_proposal_types: tuple[HarnessProposalType, ...] = tuple(HarnessProposalType)
    reject_untyped_operations: bool = True
    reject_arbitrary_shell: bool = True
    reject_omnibus_proposals: bool = True


class ProposalReviewConfiguration(ImmutableContractModel):
    explicit_operator_review_required: bool = True
    provider_may_approve: bool = False
    automatic_approval: bool = False


class ProposalQueueConfiguration(ImmutableContractModel):
    deterministic_ordering: bool = True
    executable_payloads_forbidden: bool = True


class ProposalStorageConfiguration(ImmutableContractModel):
    large_bodies_in_artifact_store: bool = True
    inline_secret_material_forbidden: bool = True


class ProposalProviderConfiguration(ImmutableContractModel):
    tools_enabled: bool = False
    repository_write_enabled: bool = False
    destination_write_enabled: bool = False
    approval_enabled: bool = False


class ProposalConfiguration(ImmutableContractModel):
    enabled: bool = True
    eligibility: ProposalEligibilityConfiguration = Field(
        default_factory=ProposalEligibilityConfiguration
    )
    generation: ProposalGenerationConfiguration = Field(
        default_factory=ProposalGenerationConfiguration
    )
    scope: ProposalScopeConfiguration = Field(default_factory=ProposalScopeConfiguration)
    review: ProposalReviewConfiguration = Field(default_factory=ProposalReviewConfiguration)
    queue: ProposalQueueConfiguration = Field(default_factory=ProposalQueueConfiguration)
    storage: ProposalStorageConfiguration = Field(default_factory=ProposalStorageConfiguration)
    provider: ProposalProviderConfiguration = Field(default_factory=ProposalProviderConfiguration)

    @model_validator(mode="after")
    def reject_authority_expansion(self) -> ProposalConfiguration:
        if (
            not self.enabled
            or not self.eligibility.confirmed_weaknesses
            or not self.generation.deterministic_enabled
            or set(self.scope.supported_proposal_types) != set(HarnessProposalType)
            or not self.scope.reject_untyped_operations
            or not self.scope.reject_arbitrary_shell
            or not self.scope.reject_omnibus_proposals
            or not self.review.explicit_operator_review_required
            or not self.queue.deterministic_ordering
            or not self.queue.executable_payloads_forbidden
            or not self.storage.large_bodies_in_artifact_store
            or not self.storage.inline_secret_material_forbidden
            or any(
                (
                    self.review.provider_may_approve,
                    self.review.automatic_approval,
                    self.provider.tools_enabled,
                    self.provider.repository_write_enabled,
                    self.provider.destination_write_enabled,
                    self.provider.approval_enabled,
                )
            )
        ):
            raise ValueError("proposal configuration cannot grant execution or approval authority")
        return self


def load_proposal_configuration(path: Path) -> ProposalConfiguration:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("harness_proposals"), dict):
        raise ValueError("proposal configuration requires a harness_proposals mapping")
    return ProposalConfiguration.model_validate(raw["harness_proposals"])
