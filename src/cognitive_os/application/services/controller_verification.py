"""Sequential Verifier Registry integration for the Cognitive Controller."""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import cast
from uuid import uuid4

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.domain.acceptance import AcceptanceDecision, AcceptancePolicy, VerifierRequirement
from cognitive_os.domain.common import JsonValue, utc_now
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.problems import AcceptanceCriterion, CriterionType, ProblemRepresentation
from cognitive_os.domain.verification import VerificationSubjectRef, VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationBundle,
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.verification.errors import VerificationError
from cognitive_os.verification.minimal import (
    CriterionOutcome,
    MinimalAcceptanceDecision,
    MinimalCriterionResult,
)


@dataclass(frozen=True, slots=True)
class ControllerVerificationOutcome:
    minimal: MinimalAcceptanceDecision
    decision: AcceptanceDecision
    bundle: VerificationBundle
    verifier_calls: int
    elapsed_seconds: float


class ControllerVerificationService:
    def __init__(
        self, verification: VerificationService, acceptance: AcceptancePolicyService
    ) -> None:
        self._verification = verification
        self._acceptance = acceptance

    async def verify(
        self,
        problem: ProblemRepresentation,
        *,
        completed_step_ids: frozenset[str],
        successful_tool_call_ids: frozenset[str],
        artifacts: dict[str, bool] | None = None,
        outputs: dict[str, object] | None = None,
        repair_budget_remaining: bool = False,
        maximum_calls: int = 64,
    ) -> ControllerVerificationOutcome:
        started = monotonic()
        artifacts, outputs = artifacts or {}, outputs or {}
        requirements = tuple(self._requirement(item) for item in problem.acceptance_criteria)
        policy = AcceptancePolicy(
            policy_id=uuid4(),
            version="1",
            name="Controller task acceptance",
            description="Generated deterministic policy from the active problem representation.",
            requirements=requirements,
            created_at=utc_now(),
        )
        results: list[VerifierResult] = []
        for criterion, requirement in zip(problem.acceptance_criteria, requirements, strict=True):
            if len(results) >= maximum_calls:
                break
            subject = self._subject(
                criterion, completed_step_ids, successful_tool_call_ids, artifacts, outputs
            )
            request = VerificationRequest(
                verification_id=uuid4(),
                task_run_id=problem.task_run_id,
                criterion_id=criterion.criterion_id,
                verifier_id=requirement.verifier_id,
                verifier_version=requirement.minimum_version,
                subject=subject,
                configuration=criterion.configuration,
                requested_at=utc_now(),
                correlation_id=problem.task_run_id,
            )
            try:
                execution = await self._verification.execute(request)
                if execution.result:
                    results.append(execution.result)
            except VerificationError:
                now = utc_now()
                results.append(
                    VerifierResult(
                        verifier_result_id=uuid4(),
                        verifier_id=requirement.verifier_id,
                        verifier_version=requirement.minimum_version,
                        subject=VerificationSubjectRef(
                            subject_type=subject.subject_type.value,
                            subject_id=str(request.verification_id),
                        ),
                        status=VerifierStatus.UNVERIFIABLE,
                        started_at=now,
                        finished_at=now,
                    )
                )
        decision = self._acceptance.evaluate(
            policy,
            problem.task_run_id,
            tuple(results),
            repair_budget_remaining=repair_budget_remaining,
        )
        evaluations = {item.criterion_id: item for item in decision.criterion_evaluations}
        minimal_results = tuple(
            MinimalCriterionResult(
                criterion_id=criterion.criterion_id,
                outcome=self._minimal_outcome(evaluations[criterion.criterion_id].outcome),
                reason=evaluations[criterion.criterion_id].reason,
                required=criterion.required,
            )
            for criterion in problem.acceptance_criteria
        )
        minimal = MinimalAcceptanceDecision(
            accepted=decision.decision.value == "accepted",
            results=minimal_results,
            required_passed=tuple(
                item.criterion_id
                for item in minimal_results
                if item.required and item.outcome is CriterionOutcome.PASSED
            ),
            failed_criteria=tuple(
                item.criterion_id
                for item in minimal_results
                if item.outcome is CriterionOutcome.FAILED
            ),
            unverifiable_criteria=tuple(
                item.criterion_id
                for item in minimal_results
                if item.outcome is CriterionOutcome.UNVERIFIABLE
            ),
            decision_reason=decision.reason,
            created_at=decision.created_at,
        )
        bundle = VerificationBundle(
            bundle_id=uuid4(),
            task_run_id=problem.task_run_id,
            criterion_results=tuple(item.criterion_id for item in decision.criterion_evaluations),
            verifier_results=tuple(results),
            required_passed=decision.required_passed,
            optional_score=decision.optional_score,
            failed_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.FAILED
            ),
            unverifiable_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.UNVERIFIABLE
            ),
            errored_required_criteria=tuple(
                item.criterion_id
                for item in decision.criterion_evaluations
                if item.required and item.outcome is VerifierStatus.ERROR
            ),
            created_at=utc_now(),
        )
        return ControllerVerificationOutcome(
            minimal, decision, bundle, len(results), monotonic() - started
        )

    @staticmethod
    def _requirement(criterion: AcceptanceCriterion) -> VerifierRequirement:
        defaults = {
            CriterionType.SCHEMA: "generic.json_schema",
            CriterionType.EXACT_MATCH: "generic.exact",
            CriterionType.STEP_COMPLETED: "generic.step_completed",
            CriterionType.TOOL_SUCCEEDED: "generic.tool_succeeded",
            CriterionType.ARTIFACT_EXISTS: "generic.artifact_integrity",
        }
        verifier_id = criterion.verifier_id or defaults.get(criterion.criterion_type)
        if verifier_id is None:
            verifier_id = "generic.manual_unavailable"
        return VerifierRequirement(
            requirement_id=uuid4(),
            verifier_id=verifier_id,
            minimum_version="1",
            criterion_ids=(criterion.criterion_id,),
            required=criterion.required,
            weight=criterion.weight,
            allowed_outcomes=(VerifierStatus.PASSED,),
        )

    @staticmethod
    def _subject(
        criterion: AcceptanceCriterion,
        completed: frozenset[str],
        tools: frozenset[str],
        artifacts: dict[str, bool],
        outputs: dict[str, object],
    ) -> VerificationSubject:
        configuration = criterion.configuration
        if criterion.criterion_type is CriterionType.STEP_COMPLETED:
            return VerificationSubject(
                subject_type=VerificationSubjectType.EXECUTION_STEP,
                inline_value={"completed": str(configuration.get("step_id", "")) in completed},
            )
        if criterion.criterion_type is CriterionType.TOOL_SUCCEEDED:
            return VerificationSubject(
                subject_type=VerificationSubjectType.TOOL_RESULT,
                inline_value={"succeeded": str(configuration.get("tool_call_id", "")) in tools},
            )
        if criterion.criterion_type is CriterionType.ARTIFACT_EXISTS:
            return VerificationSubject(
                subject_type=VerificationSubjectType.STRUCTURED_VALUE,
                inline_value={
                    "exists": artifacts.get(str(configuration.get("artifact_id", "")), False)
                },
            )
        type_name = configuration.get(
            "subject_type", VerificationSubjectType.STRUCTURED_VALUE.value
        )
        subject_type = VerificationSubjectType(str(type_name))
        output_id = str(configuration.get("output_id", ""))
        return VerificationSubject(
            subject_type=subject_type,
            inline_value=cast(
                JsonValue,
                outputs.get(output_id, configuration.get("actual")),
            ),
        )

    @staticmethod
    def _minimal_outcome(outcome: VerifierStatus) -> CriterionOutcome:
        if outcome is VerifierStatus.PASSED:
            return CriterionOutcome.PASSED
        if outcome is VerifierStatus.FAILED:
            return CriterionOutcome.FAILED
        return CriterionOutcome.UNVERIFIABLE
