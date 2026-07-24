"""Cross-domain tasks executed by the Cognitive Controller and the Tool Plane.

This is the governed execution path. Nothing here owns planning, execution, or
acceptance:

- `DomainProblemEngine` implements `ProblemRepresentationPort`. It turns a domain
  case into a real `ProblemRepresentation` whose acceptance criteria are
  `DOMAIN_VERIFIER` criteria pointing at the registered `domains.checker`.
- `DomainPlanner` implements `PlanningPort` and emits a `ControllerExecutionPlan`
  whose single action is a `TOOL` action against `domains.solve`.
- `DomainActionExecutor` implements `ControllerActionExecutor` and runs that
  action through `ToolExecutionService`, so the Tool Plane authorises, audits, and
  times every solve.

The Controller then drives its own state machine, applies its own budgets, and
calls its own `ControllerVerificationService`, which resolves `domains.checker`
through the `VerifierRegistry` and hands the results to the Acceptance Service.
The domain path therefore contributes a solver and a checker, and borrows every
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.controller import StartControllerRequest
from cognitive_os.application.services.cognitive_controller import ActionOutcome
from cognitive_os.domain.common import ActorRef, utc_now
from cognitive_os.domain.controller import (
    ControllerActionType,
    ControllerBudget,
    ControllerState,
)
from cognitive_os.domain.domains import DomainBenchmarkCase, DomainKind
from cognitive_os.domain.enums import ActorType, RiskLevel
from cognitive_os.domain.execution import ExecutionPlan, PlanStepDefinition
from cognitive_os.domain.planning import ControllerExecutionPlan, ControllerStepAction
from cognitive_os.domain.problems import (
    AcceptanceCriterion,
    ConstraintCategory,
    ConstraintSource,
    CriterionType,
    ProblemAssumption,
    ProblemConstraint,
    ProblemDomain,
    ProblemGoal,
    ProblemOutputRequirement,
    ProblemRepresentation,
)
from cognitive_os.domain.tools import (
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolInvocation,
)
from cognitive_os.domain.verifiers import VerificationSubjectType

SOLVE_TOOL_ID = "domains.solve"
SOLVE_TOOL_VERSION = "1"
CHECKER_VERIFIER_ID = "domains.checker"

_ACTOR = ActorRef(actor_type=ActorType.SYSTEM, actor_id="cross-domain-pilot")

_PROBLEM_DOMAINS: dict[DomainKind, ProblemDomain] = {
    DomainKind.MATHEMATICS: ProblemDomain.MATHEMATICS,
    DomainKind.PHYSICS: ProblemDomain.PHYSICS,
    DomainKind.LOGIC: ProblemDomain.LOGIC,
}

#: The verifier subject type each domain reports, so the Acceptance Service sees
#: a typed subject rather than an opaque blob.
_SUBJECT_TYPES: dict[DomainKind, VerificationSubjectType] = {
    DomainKind.MATHEMATICS: VerificationSubjectType.MATHEMATICAL_EXPRESSION,
    DomainKind.PHYSICS: VerificationSubjectType.PHYSICAL_QUANTITY,
    DomainKind.LOGIC: VerificationSubjectType.LOGICAL_PROBLEM,
}


def _uuid(kind: str, case_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"domain-{kind}:{case_id}")


def domain_budget() -> ControllerBudget:
    """Bounded budget for a provider-free domain run.

    The Controller charges one *nominal* provider call for problem representation
    because that step is normally a model call. `DomainProblemEngine` is
    deterministic and contacts no provider, but the ledger entry is the
    Controller's accounting and is not overridden here. The allowance is therefore
    2: one for that nominal charge, one of headroom for a repair cycle. No provider
    is configured, so a real model call cannot occur.
    """
    return ControllerBudget(
        maximum_provider_calls=2,
        maximum_tool_calls=4,
        maximum_plan_steps=4,
        maximum_repair_cycles=1,
        maximum_clarification_cycles=1,
        maximum_elapsed_seconds=120,
    )


class DomainProblemEngine:
    """`ProblemRepresentationPort` over one cross-domain benchmark case."""

    def __init__(self, case: DomainBenchmarkCase) -> None:
        self._case = case
        self.step_id = _uuid("step", case.case_id)

    async def represent(self, request: Any) -> ProblemRepresentation:
        case = self._case
        problem = case.problem
        return ProblemRepresentation(
            problem_id=_uuid("representation", case.case_id),
            task_id=request.task_id,
            task_run_id=request.task_run_id,
            domain=_PROBLEM_DOMAINS[case.domain],
            title=request.title,
            summary=problem.statement,
            goals=(
                ProblemGoal(
                    goal_id=_uuid("goal", case.case_id),
                    description=f"Determine {', '.join(problem.unknowns)}",
                    priority=1,
                    success_evidence=tuple(dict.fromkeys(case.required_verifiers)),
                ),
            ),
            constraints=tuple(
                ProblemConstraint(
                    constraint_id=_uuid(f"constraint-{index}", case.case_id),
                    category=category,
                    description=text,
                    hard=True,
                    source=source,
                )
                for index, (category, source, text) in enumerate(
                    (
                        *(
                            (ConstraintCategory.DOMAIN, ConstraintSource.USER, item)
                            for item in problem.constraints
                        ),
                        # Forbidden operations are security constraints, not task
                        # preferences, so they are hard and policy-sourced.
                        *(
                            (
                                ConstraintCategory.SECURITY,
                                ConstraintSource.TOOL_POLICY,
                                f"forbidden operation: {item}",
                            )
                            for item in case.forbidden_operations
                        ),
                    )
                )
            ),
            assumptions=tuple(
                ProblemAssumption(
                    assumption_id=_uuid(f"assumption-{index}", case.case_id),
                    description=text,
                    confidence=1,
                    requires_validation=False,
                    source=ConstraintSource.USER,
                )
                for index, text in enumerate(problem.assumptions)
            ),
            output_requirements=(
                ProblemOutputRequirement(
                    requirement_id=_uuid("output", case.case_id),
                    output_type=case.expected_answer.answer_type.value,
                    description=f"A verified {case.problem_type} answer with its derivation",
                ),
            ),
            acceptance_criteria=(
                # The domain result is judged by the registered independent checker,
                # resolved through the Verifier Registry by the Controller itself.
                AcceptanceCriterion(
                    criterion_id=_uuid("criterion", case.case_id),
                    description=f"Independent checker accepts the {case.problem_type} answer",
                    criterion_type=CriterionType.DOMAIN_VERIFIER,
                    required=True,
                    weight=1,
                    verifier_id=CHECKER_VERIFIER_ID,
                    configuration={
                        "problem_type": case.problem_type,
                        "formal_inputs": dict(problem.formal_inputs),
                        "output_id": str(self.step_id),
                        "subject_type": _SUBJECT_TYPES[case.domain].value,
                    },
                ),
                # The solve step must actually have completed; a missing tool result
                # cannot be silently treated as an absent-but-acceptable answer.
                AcceptanceCriterion(
                    criterion_id=_uuid("criterion-step", case.case_id),
                    description="The governed solve step completed",
                    criterion_type=CriterionType.STEP_COMPLETED,
                    required=True,
                    weight=1,
                    configuration={"step_id": str(self.step_id)},
                ),
            ),
            risk_level=RiskLevel.LOW,
            confidence=1,
            created_at=utc_now(),
            revision=1,
            source_request_hash=request.request_hash,
        )

    async def revise(
        self, current: ProblemRepresentation, clarification: Any
    ) -> ProblemRepresentation:
        return current.model_copy(
            update={"revision": current.revision + 1, "clarification_questions": ()}
        )


class DomainPlanner:
    """`PlanningPort` producing a single bounded Tool Plane action."""

    def __init__(self, case: DomainBenchmarkCase, step_id: UUID) -> None:
        self._case = case
        self._step_id = step_id

    async def create_plan(
        self, problem: ProblemRepresentation, budget: ControllerBudget
    ) -> ControllerExecutionPlan:
        case = self._case
        structural = ExecutionPlan(
            plan_id=_uuid("plan", case.case_id),
            task_run_id=problem.task_run_id,
            version=1,
            created_at=utc_now(),
            created_by=_ACTOR,
            steps=(
                PlanStepDefinition(
                    step_id=self._step_id,
                    sequence=1,
                    step_type="tool",
                    title=f"Solve {case.problem_type} deterministically",
                ),
            ),
        )
        return ControllerExecutionPlan(
            plan=structural,
            actions=(
                ControllerStepAction(
                    step_id=self._step_id,
                    action_type=ControllerActionType.TOOL,
                    tool_id=SOLVE_TOOL_ID,
                    tool_version=SOLVE_TOOL_VERSION,
                    tool_arguments={
                        "problem_type": case.problem_type,
                        "formal_inputs": dict(case.problem.formal_inputs),
                    },
                    verifier_ids=(CHECKER_VERIFIER_ID,),
                ),
            ),
            created_at=utc_now(),
            created_by=_ACTOR,
        )

    async def revise_plan(
        self, current: ControllerExecutionPlan, reason: str, budget: ControllerBudget
    ) -> ControllerExecutionPlan:
        return current.model_copy(
            update={"plan": current.plan.model_copy(update={"version": current.plan.version + 1})}
        )


class DomainActionExecutor:
    """`ControllerActionExecutor` that routes every solve through the Tool Plane.

    `candidate_override` injects an externally proposed answer — a provider
    fixture or a deliberately wrong one. The tool still runs and is still audited;
    only the answer handed to the verifier changes, so a fabricated answer travels
    the identical acceptance path and is caught by the same checker.
    """

    def __init__(
        self,
        tool_execution: Any,
        *,
        candidate_override: Any | None = None,
        workspace: str = ".",
    ) -> None:
        self._tool_execution = tool_execution
        self._override = candidate_override
        self._workspace = workspace
        self.invocations: list[UUID] = []

    async def execute(
        self, action: ControllerStepAction, request: StartControllerRequest
    ) -> ActionOutcome:
        if action.action_type is not ControllerActionType.TOOL or action.tool_id is None:
            return ActionOutcome(succeeded=False, warning="domain plans contain only tool actions")

        invocation = ToolInvocation(
            tool_call_id=_uuid(f"call-{action.step_id}", str(request.task_run_id)),
            task_run_id=request.task_run_id,
            step_id=action.step_id,
            tool_id=action.tool_id,
            tool_version=action.tool_version or SOLVE_TOOL_VERSION,
            arguments=dict(action.tool_arguments or {}),
            requested_at=utc_now(),
            requested_by="cross-domain-pilot",
            correlation_id=request.correlation_id,
        )
        context = ToolExecutionContext(
            workspace=self._workspace,
            timeout_seconds=30,
            maximum_stdout_bytes=262_144,
            maximum_stderr_bytes=65_536,
            maximum_artifact_bytes=1_048_576,
        )
        result = await self._tool_execution.execute(invocation, context)
        self.invocations.append(invocation.tool_call_id)
        if result.status is not ToolExecutionStatus.COMPLETED:
            return ActionOutcome(
                succeeded=False,
                tool_call_id=invocation.tool_call_id,
                warning=f"tool status {result.status.value}",
            )

        from cognitive_os.tools.domains import serialise_solution

        output = result.result
        if self._override is not None:
            # Replace only the answer; the derivation and tool evidence stay as
            # produced, so the record shows what was computed and what was claimed.
            override = serialise_solution(_SolutionView(self._override, dict(output or {})))
            output = override
        return ActionOutcome(succeeded=True, output=output, tool_call_id=invocation.tool_call_id)


@dataclass(frozen=True, slots=True)
class _SolutionView:
    """Adapts an injected candidate to the shape `serialise_solution` expects."""

    candidate: Any
    _payload: dict[str, Any]

    @property
    def steps(self) -> tuple[Any, ...]:
        from cognitive_os.domains.solvers import Step

        return tuple(
            Step(
                operation=str(item.get("operation", "step")),
                detail=str(item.get("detail", "")),
                output=str(item.get("output", "")),
                inputs=tuple(item.get("inputs", ())),
            )
            for item in self._payload.get("steps", ())
        )

    @property
    def tool_evidence(self) -> tuple[str, ...]:
        return tuple(self._payload.get("tool_evidence", ()))

    @property
    def assumptions(self) -> tuple[str, ...]:
        return tuple(self._payload.get("assumptions", ()))

    @property
    def limitations(self) -> tuple[str, ...]:
        return tuple(self._payload.get("limitations", ()))


def start_request(case: DomainBenchmarkCase) -> StartControllerRequest:
    """Deterministic Controller entry point for one case."""
    return StartControllerRequest(
        task_id=_uuid("task", case.case_id),
        task_run_id=_uuid("task-run", case.case_id),
        correlation_id=_uuid("correlation", case.case_id),
        title=f"{case.domain.value}: {case.problem_type}",
        raw_request=case.problem.statement,
    )


def request_hash(case: DomainBenchmarkCase) -> str:
    return sha256(case.content_hash.encode()).hexdigest()


__all__ = [
    "CHECKER_VERIFIER_ID",
    "SOLVE_TOOL_ID",
    "DomainActionExecutor",
    "DomainPlanner",
    "DomainProblemEngine",
    "domain_budget",
    "start_request",
]


def accepted_states() -> frozenset[ControllerState]:
    return frozenset({ControllerState.COMPLETED})
