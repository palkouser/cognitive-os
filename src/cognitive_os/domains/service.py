"""Governed orchestration for cross-domain pilot runs.

The service owns no truth of its own. It resolves the registry entry, freezes the
plan, invokes the solver, and then hands the candidate answer to a *separate*
checker whose disposition it records verbatim. Acceptance is composed from those
checks by `compose_disposition`, so no component in this path can accept itself.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.common import JsonValue
from cognitive_os.domain.domains import (
    DerivationStep,
    DomainAnswer,
    DomainBenchmarkCase,
    DomainDerivation,
    DomainFailureCode,
    DomainPilotRun,
    DomainRunStatus,
    DomainVerificationOutcome,
    VerificationCheckResult,
    VerificationDisposition,
    compose_disposition,
)
from cognitive_os.events.domain_events import (
    DomainCaseCompleted,
    DomainCaseFailed,
    DomainCaseStarted,
    DomainEventPayload,
)

from .registry import UnsupportedProblemType, resolve, solver_inputs
from .solvers import Candidate, Solution, SolverError, Step

FIXTURE_TIME = datetime(2026, 7, 24, tzinfo=UTC)

#: Operations that may never be requested by a case, whatever its plan says.
FORBIDDEN_ALWAYS = frozenset(
    {
        "eval",
        "exec",
        "import",
        "pickle",
        "subprocess",
        "network",
        "raw_smtlib",
        "unrestricted_parse",
    }
)


class DomainPolicyError(Exception):
    """Raised when a case violates an authority or resource invariant."""

    def __init__(self, code: DomainFailureCode, message: str) -> None:
        super().__init__(message)
        self.code = code


class DomainPilotResult:
    """Everything one case produced, kept together for evidence and replay."""

    __slots__ = ("answer", "derivation", "outcome", "run")

    def __init__(
        self,
        run: DomainPilotRun,
        derivation: DomainDerivation | None,
        answer: DomainAnswer | None,
        outcome: DomainVerificationOutcome | None,
    ) -> None:
        self.run = run
        self.derivation = derivation
        self.answer = answer
        self.outcome = outcome

    @property
    def accepted(self) -> bool:
        return self.run.status is DomainRunStatus.ACCEPTED


class DomainPilotService:
    def __init__(
        self,
        repository: object | None = None,
        events: object | None = None,
        *,
        clock: Callable[[], datetime] = lambda: FIXTURE_TIME,
    ) -> None:
        self._repository = repository
        self._events = events
        self._clock = clock

    async def run_case(
        self,
        case: DomainBenchmarkCase,
        *,
        candidate: Candidate | None = None,
        correlation_id: UUID | None = None,
    ) -> DomainPilotResult:
        """Execute one benchmark case end to end.

        `candidate` injects an externally proposed answer (a provider fixture or a
        deliberately wrong one). The verification path is identical either way,
        which is what makes a wrong provider answer detectable rather than trusted.
        """
        now = self._clock()
        # A run is one execution, not one case: the injected candidate is part of
        # the identity, so a solver run and a provider-fixture run never collide.
        run_id = uuid5(
            NAMESPACE_URL,
            f"domain-pilot:{case.case_id}:{case.content_hash}:{_candidate_key(candidate)}",
        )
        correlation = correlation_id or run_id
        await self._emit(
            DomainCaseStarted, case, run_id, correlation, "case accepted for execution"
        )

        try:
            entry = resolve(case.problem.problem_type)
        except UnsupportedProblemType:
            return await self._fail(
                case,
                run_id,
                correlation,
                DomainFailureCode.UNSUPPORTED_PROBLEM_TYPE,
                f"problem type {case.problem.problem_type!r} is not registered",
            )

        try:
            self._enforce_policy(case, entry.required_verifiers)
        except DomainPolicyError as error:
            return await self._fail(case, run_id, correlation, error.code, str(error))

        inputs = dict(case.problem.formal_inputs)
        budget = case.plan.resource_budget

        try:
            solution = entry.solver(solver_inputs(entry, inputs), budget)
        except SolverError as error:
            return await self._fail(case, run_id, correlation, error.code, str(error))
        except (KeyError, TypeError, ValueError) as error:
            return await self._fail(
                case, run_id, correlation, DomainFailureCode.INVALID_DERIVATION, str(error)
            )

        proposed = candidate if candidate is not None else solution.candidate

        try:
            checks = entry.checker(inputs, proposed, budget)
        except SolverError as error:
            return await self._fail(case, run_id, correlation, error.code, str(error))
        except (KeyError, TypeError, ValueError) as error:
            return await self._fail(
                case, run_id, correlation, DomainFailureCode.INVALID_DERIVATION, str(error)
            )

        derivation = _build_derivation(case, solution, now)
        answer = _build_answer(case, proposed, derivation, now)

        results = tuple(
            VerificationCheckResult(
                capability=item.capability,
                disposition=item.disposition,
                detail=item.detail,
            )
            for item in checks
        )
        # A plan may require a capability the checker never exercised. That is a
        # missing verifier, not a pass, so it is injected as an explicit failure.
        covered = {item.capability for item in results}
        missing = tuple(item for item in entry.required_verifiers if item not in covered)
        if missing:
            results += tuple(
                VerificationCheckResult(
                    capability=item,
                    disposition=VerificationDisposition.UNSUPPORTED,
                    detail="required verifier did not run",
                )
                for item in missing
            )

        disposition = compose_disposition(tuple(item.disposition for item in results))
        outcome = DomainVerificationOutcome(
            problem_id=case.problem.problem_id,
            checks=results,
            disposition=disposition,
            failure_code=(DomainFailureCode.MISSING_REQUIRED_VERIFIER if missing else None),
            resource_use={
                "steps": len(solution.steps),
                "checks": len(results),
                "timeout_seconds": budget.timeout_seconds,
            },
            created_at=now,
        )

        status = {
            VerificationDisposition.PASS: DomainRunStatus.ACCEPTED,
            VerificationDisposition.PARTIAL: DomainRunStatus.PARTIALLY_ACCEPTED,
        }.get(disposition, DomainRunStatus.REJECTED)

        run = DomainPilotRun(
            run_id=run_id,
            case_id=case.case_id,
            domain=case.domain,
            status=status,
            problem_hash=case.problem.content_hash,
            plan_hash=case.plan.content_hash,
            derivation_hash=derivation.content_hash,
            answer_hash=answer.content_hash,
            outcome_hash=outcome.content_hash,
            skill_revisions=entry.skills,
            strategy_revisions=entry.strategies,
            failure_code=outcome.failure_code,
            created_at=now,
        )
        result = DomainPilotResult(run, derivation, answer, outcome)
        await self._persist(result)
        await self._emit(
            DomainCaseCompleted if result.accepted else DomainCaseFailed,
            case,
            run_id,
            correlation,
            f"verification disposition {disposition.value}",
        )
        return result

    def _enforce_policy(self, case: DomainBenchmarkCase, required: tuple[str, ...]) -> None:
        requested = {item.casefold() for item in case.plan.forbidden_operations}
        declared = {item.casefold() for item in case.problem.required_tools}
        if breach := (declared & (FORBIDDEN_ALWAYS | requested)):
            raise DomainPolicyError(
                DomainFailureCode.FORBIDDEN_OPERATION,
                f"case requests forbidden operations: {sorted(breach)}",
            )
        if not case.plan.required_capabilities:
            raise DomainPolicyError(
                DomainFailureCode.MISSING_REQUIRED_VERIFIER, "no verification plan capabilities"
            )
        if case.problem.domain is not case.domain:
            raise DomainPolicyError(
                DomainFailureCode.UNSUPPORTED_PROBLEM_TYPE, "case and problem domains disagree"
            )

    async def _fail(
        self,
        case: DomainBenchmarkCase,
        run_id: UUID,
        correlation: UUID,
        code: DomainFailureCode,
        detail: str,
    ) -> DomainPilotResult:
        now = self._clock()
        outcome = DomainVerificationOutcome(
            problem_id=case.problem.problem_id,
            checks=(
                VerificationCheckResult(
                    capability="domains.policy",
                    disposition=VerificationDisposition.FAIL,
                    detail=detail,
                ),
            ),
            disposition=VerificationDisposition.FAIL,
            failure_code=code,
            created_at=now,
        )
        run = DomainPilotRun(
            run_id=run_id,
            case_id=case.case_id,
            domain=case.domain,
            status=DomainRunStatus.FAILED,
            problem_hash=case.problem.content_hash,
            plan_hash=case.plan.content_hash,
            outcome_hash=outcome.content_hash,
            failure_code=code,
            created_at=now,
        )
        result = DomainPilotResult(run, None, None, outcome)
        await self._persist(result)
        await self._emit(DomainCaseFailed, case, run_id, correlation, detail)
        return result

    async def _persist(self, result: DomainPilotResult) -> None:
        if self._repository is not None:
            await self._repository.record(result)  # type: ignore[attr-defined]

    async def _emit(
        self,
        payload_type: type[DomainEventPayload],
        case: DomainBenchmarkCase,
        run_id: UUID,
        correlation: UUID,
        reason: str,
    ) -> None:
        if self._events is None:
            return
        await self._events.append(  # type: ignore[attr-defined]
            run_id,
            payload_type(
                pilot_id=run_id,
                domain=case.domain.value,
                case_id=case.case_id,
                content_hash=case.content_hash,
                actor="cross-domain-pilot",
                authority="acceptance-service",
                reason=reason,
                occurred_at=self._clock(),
            ),
            correlation_id=correlation,
        )


def _build_derivation(
    case: DomainBenchmarkCase, solution: Solution, now: datetime
) -> DomainDerivation:
    steps = solution.steps or (Step("noop", "no steps recorded", "none"),)
    return DomainDerivation(
        derivation_id=uuid5(NAMESPACE_URL, f"domain-derivation:{case.case_id}"),
        problem_id=case.problem.problem_id,
        steps=tuple(
            DerivationStep(
                index=index,
                operation=item.operation,
                detail=item.detail,
                inputs=item.inputs,
                output=item.output,
            )
            for index, item in enumerate(steps)
        ),
        assumptions=solution.assumptions,
        tool_evidence=solution.tool_evidence,
        limitations=solution.limitations,
        created_at=now,
    )


def _candidate_key(candidate: Candidate | None) -> str:
    """Stable identity for an injected candidate; `solver` when none was given."""
    if candidate is None:
        return "solver"
    from hashlib import sha256

    return sha256(repr(candidate).encode()).hexdigest()[:32]


def _jsonable(value: object) -> dict[str, JsonValue]:
    """Normalise solver payloads to JSON-safe values so hashes stay stable."""
    import json

    decoded: dict[str, JsonValue] = json.loads(json.dumps(value, sort_keys=True, default=str))
    return decoded


def _build_answer(
    case: DomainBenchmarkCase,
    candidate: Candidate,
    derivation: DomainDerivation,
    now: datetime,
) -> DomainAnswer:
    return DomainAnswer(
        problem_id=case.problem.problem_id,
        answer_type=candidate.answer_type,
        exact_value=candidate.exact_value,
        approximate_value=candidate.approximate_value,
        tolerance=candidate.tolerance,
        units=candidate.units,
        symbolic_form=candidate.symbolic_form,
        logical_status=candidate.logical_status,
        structured_value=_jsonable(candidate.structured),
        proof_or_derivation_reference=derivation.derivation_id,
        limitations=tuple(str(item) for item in derivation.limitations),
        created_at=now,
    )
