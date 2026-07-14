"""Acceptance-policy application boundary."""

from typing import Protocol
from uuid import UUID

from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.verification import VerifierResult


class AcceptancePolicyPort(Protocol):
    def validate_policy(self, policy: AcceptancePolicy) -> None: ...
    def resolve_requirements(
        self, policy: AcceptancePolicy, criterion_ids: tuple[UUID, ...]
    ) -> tuple[VerifierRequirement, ...]: ...
    def evaluate(
        self,
        policy: AcceptancePolicy,
        task_run_id: UUID,
        results: tuple[VerifierResult, ...],
        *,
        repair_budget_remaining: bool = False,
    ) -> AcceptanceDecision: ...
