"""Deterministic authoritative acceptance-policy evaluation."""

from __future__ import annotations

from uuid import UUID, uuid4

from cognitive_os.domain.acceptance import (
    AcceptanceDecision,
    AcceptanceDecisionType,
    AcceptancePolicy,
    CriterionEvaluation,
    VerifierRequirement,
)
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.verification import VerifierResult


class AcceptancePolicyService:
    def __init__(
        self,
        *,
        repairable_finding_codes: frozenset[str] = frozenset(),
        clarification_finding_codes: frozenset[str] = frozenset(),
    ) -> None:
        self._repairable = repairable_finding_codes
        self._clarification = clarification_finding_codes

    def validate_policy(self, policy: AcceptancePolicy) -> None:
        AcceptancePolicy.model_validate(policy.model_dump(mode="python"))

    def resolve_requirements(
        self, policy: AcceptancePolicy, criterion_ids: tuple[UUID, ...]
    ) -> tuple[VerifierRequirement, ...]:
        requested = set(criterion_ids)
        resolved = tuple(
            item for item in policy.requirements if requested & set(item.criterion_ids)
        )
        covered = {criterion for item in resolved for criterion in item.criterion_ids}
        if requested - covered:
            raise ValueError("acceptance criteria are not fully mapped by the policy")
        return resolved

    def evaluate(
        self,
        policy: AcceptancePolicy,
        task_run_id: UUID,
        results: tuple[VerifierResult, ...],
        *,
        repair_budget_remaining: bool = False,
    ) -> AcceptanceDecision:
        self.validate_policy(policy)
        result_ids = [item.verifier_result_id for item in results]
        if len(result_ids) != len(set(result_ids)):
            return self._decision(
                policy,
                task_run_id,
                (),
                AcceptanceDecisionType.VERIFICATION_ERROR,
                False,
                0,
                "duplicate verifier result detected",
            )
        evaluations: list[CriterionEvaluation] = []
        optional_weighted = 0.0
        optional_weights = 0.0
        repairable_failure = False
        clarification_needed = False
        for requirement in sorted(policy.requirements, key=lambda item: str(item.requirement_id)):
            matching = tuple(
                item
                for item in results
                if item.verifier_id == requirement.verifier_id
                and self._version_at_least(item.verifier_version, requirement.minimum_version)
            )
            for criterion_id in sorted(requirement.criterion_ids, key=str):
                outcome, score, reason = self._classify(requirement, matching)
                evaluation = CriterionEvaluation(
                    criterion_id=criterion_id,
                    verifier_requirement_id=requirement.requirement_id,
                    result_ids=tuple(item.verifier_result_id for item in matching),
                    outcome=outcome,
                    score=score,
                    required=requirement.required,
                    reason=reason,
                )
                evaluations.append(evaluation)
                codes = {finding.code for item in matching for finding in item.findings}
                repairable_failure = repairable_failure or bool(codes & self._repairable)
                clarification_needed = clarification_needed or bool(codes & self._clarification)
                if not requirement.required and score is not None:
                    optional_weighted += requirement.weight * score
                    optional_weights += requirement.weight
        optional_score = optional_weighted / optional_weights if optional_weights else 1.0
        required = [item for item in evaluations if item.required]
        errors = [item for item in required if item.outcome is VerifierStatus.ERROR]
        unverifiable = [item for item in required if item.outcome is VerifierStatus.UNVERIFIABLE]
        failed = [
            item
            for item in required
            if item.outcome
            not in {
                VerifierStatus.PASSED,
                VerifierStatus.PARTIAL,
                VerifierStatus.ERROR,
                VerifierStatus.UNVERIFIABLE,
            }
        ]
        partial_invalid = [
            item
            for item in required
            if item.outcome is VerifierStatus.PARTIAL and not policy.allow_partial
        ]
        required_passed = not errors and not unverifiable and not failed and not partial_invalid
        if errors and len(errors) > policy.maximum_verifier_errors:
            decision, reason = (
                AcceptanceDecisionType.VERIFICATION_ERROR,
                "required verifier infrastructure failed",
            )
        elif unverifiable and len(unverifiable) > policy.maximum_unverifiable_required:
            decision, reason = (
                (AcceptanceDecisionType.NEEDS_CLARIFICATION, "required semantic input is missing")
                if clarification_needed
                else (
                    AcceptanceDecisionType.UNVERIFIABLE,
                    "required verifier evidence is unavailable",
                )
            )
        elif failed or partial_invalid:
            decision, reason = (
                (
                    AcceptanceDecisionType.NEEDS_REPAIR,
                    "required verification failed with a repairable finding",
                )
                if repairable_failure and repair_budget_remaining
                else (AcceptanceDecisionType.REJECTED, "required verification failed")
            )
        elif optional_score < policy.minimum_optional_score:
            decision, reason = (
                AcceptanceDecisionType.REJECTED,
                "optional verifier score is below policy minimum",
            )
        else:
            decision, reason = (
                AcceptanceDecisionType.ACCEPTED,
                "all required verifier evidence satisfies policy",
            )
        return self._decision(
            policy,
            task_run_id,
            tuple(evaluations),
            decision,
            required_passed,
            optional_score,
            reason,
        )

    @staticmethod
    def _classify(
        requirement: VerifierRequirement, matching: tuple[VerifierResult, ...]
    ) -> tuple[VerifierStatus, float | None, str]:
        if not matching:
            return VerifierStatus.UNVERIFIABLE, None, "required verifier result is missing"
        if any(item.status is VerifierStatus.ERROR for item in matching):
            return VerifierStatus.ERROR, None, "verifier infrastructure reported an error"
        if any(item.status is VerifierStatus.UNVERIFIABLE for item in matching):
            return VerifierStatus.UNVERIFIABLE, None, "verifier could not evaluate the subject"
        scores = [
            item.score
            if item.score is not None
            else (1.0 if item.status is VerifierStatus.PASSED else 0.0)
            for item in matching
        ]
        score = min(scores)
        if (
            all(item.status in requirement.allowed_outcomes for item in matching)
            and score >= requirement.minimum_score
        ):
            return VerifierStatus.PASSED, score, "verifier requirement passed"
        return VerifierStatus.FAILED, score, "verifier requirement did not pass"

    @staticmethod
    def _version_at_least(actual: str, minimum: str) -> bool:
        def parts(value: str) -> tuple[int, ...]:
            try:
                return tuple(int(item) for item in value.split("."))
            except ValueError:
                return ()

        return bool(parts(actual)) and parts(actual) >= parts(minimum)

    @staticmethod
    def _decision(
        policy: AcceptancePolicy,
        task_run_id: UUID,
        evaluations: tuple[CriterionEvaluation, ...],
        decision: AcceptanceDecisionType,
        required_passed: bool,
        optional_score: float,
        reason: str,
    ) -> AcceptanceDecision:
        return AcceptanceDecision(
            decision_id=uuid4(),
            task_run_id=task_run_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            decision=decision,
            criterion_evaluations=evaluations,
            required_passed=required_passed,
            optional_score=optional_score,
            reason=reason,
            created_at=utc_now(),
        )
