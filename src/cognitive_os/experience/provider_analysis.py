"""Bounded parsing of optional provider-assisted proposals."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex

from .errors import ExperiencePolicyError


class ProviderAnalysisProposal(ImmutableContractModel):
    proposal_type: Literal[
        "failure_grouping",
        "lesson",
        "missing_precondition",
        "candidate_abstraction",
        "generalization_description",
    ]
    summary: NonEmptyStr
    evidence_refs: Annotated[tuple[Sha256Hex, ...], Field(min_length=1, max_length=32)]
    causal_claim: bool = False
    destination_action: None = None


def parse_provider_proposals(
    value: object,
    *,
    allowed_evidence: frozenset[str],
    maximum_proposals: int = 64,
) -> tuple[ProviderAnalysisProposal, ...]:
    if not isinstance(value, list) or len(value) > maximum_proposals:
        raise ExperiencePolicyError("provider proposal output is not a bounded list")
    proposals = tuple(ProviderAnalysisProposal.model_validate(item) for item in value)
    for proposal in proposals:
        if not set(proposal.evidence_refs) <= allowed_evidence:
            raise ExperiencePolicyError("provider proposal contains fabricated evidence")
        if proposal.causal_claim:
            raise ExperiencePolicyError("provider causal claim is non-authoritative")
    return proposals
