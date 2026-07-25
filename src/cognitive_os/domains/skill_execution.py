"""Domain cases executed as registered skills through the Skill Engine.

`SkillExecutionService` already enforces what matters: only an exact `VERIFIED`
revision may run, the package hash must match, the registry snapshot must be
current, the package artifact must verify, and a valid Context Bundle must exist
before the first step. This module supplies the two things it needs from the
domain side — a Context request factory and an `ExistingControllerSkillRunner` —
so the domain skill runs under those checks rather than beside them.

The runner is the Controller path from `runner.py`, so a skill execution and a
bare controlled run take the identical route through the Tool Plane and the
Acceptance Service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.domains import DomainBenchmarkCase, DomainKind
from cognitive_os.domain.routing import (
    ContextSizeClass,
    CostClass,
    ExecutionRole,
    LatencyClass,
    TaskComplexityClass,
    TaskSignature,
)
from cognitive_os.domain.skills import (
    SkillActor,
    SkillCreatorType,
    SkillExecutionRequest,
    SkillExecutionResult,
    SkillExecutionStatus,
    SkillExecutionStepResult,
    SkillInputBinding,
    SkillRequirementType,
    SkillRevision,
    SkillSelectionDecision,
    SkillSelectionReason,
)
from cognitive_os.routing.service import build_task_signature

from .context import build_domain_context
from .fixtures import FIXTURE_TIME
from .registry import resolve
from .runner import ControlledRun, run_case_controlled

#: The mandatory domain path is tool-only. The signature records that explicitly
#: so a router can never conclude a provider is required for acceptance.
TOOL_ONLY_ROUTE = "deterministic-tool-only"

_DOMAIN_NAMES: dict[DomainKind, str] = {
    DomainKind.MATHEMATICS: "mathematics",
    DomainKind.PHYSICS: "physics",
    DomainKind.LOGIC: "logic",
}


def domain_task_signature(case: DomainBenchmarkCase) -> TaskSignature:
    """Canonical routing signature for one domain case.

    Carries no prompt or instruction text — only the declared capabilities, exact
    skill and strategy revisions, and verifier profile. This is the observation
    Sprint 21 needs to evaluate learned routing against the deterministic
    baseline, and it is produced whether or not a provider is ever consulted.
    """
    entry = resolve(case.problem_type)
    return build_task_signature(
        problem_domain=_DOMAIN_NAMES[case.domain],
        problem_class=case.problem_type,
        output_type=case.expected_answer.answer_type.value,
        repository_profile="cognitive-os",
        estimated_complexity=TaskComplexityClass.SMALL,
        required_tool_capabilities=("domains.solve",),
        required_structured_output=True,
        context_size_class=ContextSizeClass.SMALL,
        risk_level="standard",
        verifier_profile="domains.checker",
        latency_class=LatencyClass.LOW,
        cost_class=CostClass.LOW,
        strategy_revisions=entry.strategies,
        skill_revisions=entry.skills,
        execution_role=ExecutionRole.PRIMARY,
    )


@dataclass(frozen=True, slots=True)
class DomainSkillRun:
    """A domain case executed as a skill, with the governed run it produced."""

    result: SkillExecutionResult
    controlled: ControlledRun
    signature: TaskSignature
    #: The Skill Engine's selection decision. Present since the domain path stopped
    #: resolving its skill by static table position; `None` only when a caller forced a
    #: specific revision and no selection was asked for.
    selection: SkillSelectionDecision | None = None

    @property
    def accepted(self) -> bool:
        return self.result.status is SkillExecutionStatus.ACCEPTED

    @property
    def selected_by_statistics(self) -> bool:
        """Whether accumulated outcomes, rather than a name, broke the tie."""
        return (
            self.selection is not None
            and self.selection.reason is SkillSelectionReason.VERIFIED_STATISTICS
        )


def declared_verifier_capabilities(revision: SkillRevision) -> tuple[str, ...]:
    """The verifier capabilities a skill revision declares it will run.

    Read from the package's own `requirements`, so the declaration stays where the
    skill author wrote it rather than being duplicated in a lookup table here.
    """
    return tuple(
        sorted(
            {
                requirement.capability_id
                for requirement in revision.requirements
                if requirement.requirement_type is SkillRequirementType.VERIFIER
                and requirement.required
            }
        )
    )


class DomainSkillRunner:
    """`ExistingControllerSkillRunner` backed by the governed Controller path."""

    def __init__(self, case: DomainBenchmarkCase, *, candidate_override: Any | None = None) -> None:
        self._case = case
        self._override = candidate_override
        self.last_run: ControlledRun | None = None

    async def start(
        self, request: SkillExecutionRequest, revision: SkillRevision
    ) -> SkillExecutionResult:
        # The revision is not decoration. A skill package declares the verifier
        # capability it claims to run, so executing this revision must require that
        # capability: selecting a skill whose declared verifier never runs on this
        # case cannot yield an accepted result. Before this, the revision was
        # ignored entirely and every skill produced an identical outcome, which
        # made the Skill Engine's selection causally inert on the domain path.
        run = await run_case_controlled(
            self._case,
            candidate_override=self._override,
            required_capabilities=declared_verifier_capabilities(revision),
        )
        self.last_run = run
        status = (
            SkillExecutionStatus.ACCEPTED
            if run.completed and run.accepted
            else SkillExecutionStatus.REJECTED
        )
        return SkillExecutionResult(
            execution_id=request.execution_id,
            skill_id=request.skill_id,
            skill_revision=request.skill_revision,
            task_run_id=request.task_run_id,
            status=status,
            step_results=(
                SkillExecutionStepResult(
                    step_id="execute",
                    status=status,
                    reason=run.decision_reason or None,
                ),
            ),
            # The Acceptance Service owns the decision; the skill records its
            # identifier rather than deciding anything itself.
            acceptance_decision_id=(
                uuid5(NAMESPACE_URL, f"domain-acceptance:{self._case.case_id}")
                if status is SkillExecutionStatus.ACCEPTED
                else None
            ),
            failure=None if status is SkillExecutionStatus.ACCEPTED else "verification rejected",
            started_at=FIXTURE_TIME,
            finished_at=FIXTURE_TIME,
        )

    async def resume(self, execution_id: UUID) -> SkillExecutionResult:
        raise NotImplementedError("domain skill executions are single-shot and never wait")

    async def cancel(self, execution_id: UUID, reason: str) -> SkillExecutionResult:
        raise NotImplementedError("domain skill executions complete within one bounded step")


def domain_context_request_factory(case: DomainBenchmarkCase) -> Any:
    """Context request factory for the Skill Engine, over the case's required items."""

    def factory(request: SkillExecutionRequest, revision: SkillRevision) -> Any:
        _, context_request = build_domain_context(
            case,
            task_run_id=request.task_run_id,
            step_id=uuid5(NAMESPACE_URL, f"domain-skill-step:{case.case_id}"),
        )
        return context_request

    return factory


def domain_input_bindings(case: DomainBenchmarkCase) -> tuple[SkillInputBinding, ...]:
    return (
        SkillInputBinding(
            name="problem",
            value={
                "problem_type": case.problem_type,
                "domain": case.domain.value,
            },
        ),
    )


def domain_actor() -> SkillActor:
    return SkillActor(creator_type=SkillCreatorType.OPERATOR, creator_id="cross-domain-pilot")
