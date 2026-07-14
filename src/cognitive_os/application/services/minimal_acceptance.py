"""Deterministic aggregation of Sprint 6 structural acceptance evidence."""

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.problems import AcceptanceCriterion, CriterionType
from cognitive_os.verification.minimal import (
    CriterionOutcome,
    MinimalAcceptanceDecision,
    MinimalCriterionResult,
    validate_schema,
)


class MinimalAcceptanceService:
    def evaluate(
        self,
        criteria: tuple[AcceptanceCriterion, ...],
        *,
        completed_step_ids: frozenset[str] = frozenset(),
        successful_tool_call_ids: frozenset[str] = frozenset(),
        artifacts: dict[str, bool] | None = None,
        outputs: dict[str, object] | None = None,
    ) -> MinimalAcceptanceDecision:
        artifacts = artifacts or {}
        outputs = outputs or {}
        results = tuple(
            self._evaluate_one(
                item, completed_step_ids, successful_tool_call_ids, artifacts, outputs
            )
            for item in criteria
        )
        required_passed = tuple(
            item.criterion_id
            for item in results
            if item.required and item.outcome is CriterionOutcome.PASSED
        )
        failed = tuple(
            item.criterion_id for item in results if item.outcome is CriterionOutcome.FAILED
        )
        unverifiable = tuple(
            item.criterion_id for item in results if item.outcome is CriterionOutcome.UNVERIFIABLE
        )
        accepted = all(
            not item.required or item.outcome is CriterionOutcome.PASSED for item in results
        )
        return MinimalAcceptanceDecision(
            accepted=accepted,
            results=results,
            required_passed=required_passed,
            failed_criteria=failed,
            unverifiable_criteria=unverifiable,
            decision_reason=(
                "all required structural criteria passed"
                if accepted
                else "one or more required structural criteria did not pass"
            ),
            created_at=utc_now(),
        )

    @staticmethod
    def _evaluate_one(
        criterion: AcceptanceCriterion,
        completed: frozenset[str],
        tools: frozenset[str],
        artifacts: dict[str, bool],
        outputs: dict[str, object],
    ) -> MinimalCriterionResult:
        configuration = criterion.configuration
        passed = False
        reason = "criterion failed"
        outcome = CriterionOutcome.FAILED
        if criterion.criterion_type is CriterionType.STEP_COMPLETED:
            passed = str(configuration.get("step_id", "")) in completed
        elif criterion.criterion_type is CriterionType.TOOL_SUCCEEDED:
            passed = str(configuration.get("tool_call_id", "")) in tools
        elif criterion.criterion_type is CriterionType.ARTIFACT_EXISTS:
            passed = artifacts.get(str(configuration.get("artifact_id", "")), False)
        elif criterion.criterion_type is CriterionType.SCHEMA:
            key = str(configuration.get("output_id", ""))
            passed, reason = validate_schema(outputs.get(key), configuration.get("schema", {}))
        elif criterion.criterion_type in {
            CriterionType.MANUAL,
            CriterionType.DOMAIN_VERIFIER,
            CriterionType.EXACT_MATCH,
        }:
            outcome = CriterionOutcome.UNVERIFIABLE
            reason = "criterion requires Sprint 7 verification or manual review"
        if outcome is not CriterionOutcome.UNVERIFIABLE:
            outcome = CriterionOutcome.PASSED if passed else CriterionOutcome.FAILED
            reason = (
                reason
                if criterion.criterion_type is CriterionType.SCHEMA
                else (
                    "criterion evidence is present" if passed else "criterion evidence is missing"
                )
            )
        return MinimalCriterionResult(
            criterion_id=criterion.criterion_id,
            outcome=outcome,
            reason=reason,
            required=criterion.required,
        )
