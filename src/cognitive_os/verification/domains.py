"""Registered verifier that runs the independent cross-domain checker.

This is the seam that puts domain acceptance under the existing Acceptance
Service. The Controller builds acceptance criteria of type `DOMAIN_VERIFIER`
pointing at `domains.checker`; `ControllerVerificationService` resolves them
through the `VerifierRegistry` like any other verifier, so the domain path has no
acceptance authority of its own.

The subject is the candidate answer produced by the `domains.solve` tool. The
checker recomputes by an independent route and never reads the solver's own
reasoning as truth.
"""

from __future__ import annotations

from cognitive_os.domain.common import ErrorInfo
from cognitive_os.domain.enums import RiskLevel, VerifierStatus
from cognitive_os.domain.problems import CriterionType, ProblemDomain
from cognitive_os.domain.verification import VerifierResult
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubjectType,
    VerifierCapability,
    VerifierDescriptor,
    VerifierDeterminism,
    VerifierKind,
)

from .base import BaseVerifier

VERIFIER_ID = "domains.checker"

_SUBJECT_TYPES = (
    VerificationSubjectType.MATHEMATICAL_EXPRESSION,
    VerificationSubjectType.PHYSICAL_QUANTITY,
    VerificationSubjectType.LOGICAL_PROBLEM,
    VerificationSubjectType.STRUCTURED_VALUE,
)


def _descriptor() -> VerifierDescriptor:
    return VerifierDescriptor(
        verifier_id=VERIFIER_ID,
        version="1",
        display_name="Cross-domain independent checker",
        description=(
            "Recompute a candidate mathematics, physics, or logic answer by an independent "
            "route and judge it. Dependency-free, deterministic, and offline."
        ),
        kind=VerifierKind.GENERIC,
        capabilities=tuple(
            VerifierCapability(
                capability_id=f"{VERIFIER_ID}.{subject.value}.v1",
                subject_type=subject,
                problem_domains=(
                    ProblemDomain.MATHEMATICS,
                    ProblemDomain.PHYSICS,
                    ProblemDomain.LOGIC,
                ),
                criterion_types=(CriterionType.DOMAIN_VERIFIER,),
            )
            for subject in _SUBJECT_TYPES
        ),
        determinism=VerifierDeterminism.DETERMINISTIC,
        risk_level=RiskLevel.LOW,
        default_timeout_seconds=30,
        maximum_input_bytes=262_144,
        configuration_schema={
            "type": "object",
            "properties": {
                "problem_type": {"type": "string"},
                "formal_inputs": {"type": "object"},
                # Capabilities the plan requires. One that the checker never
                # exercises is a missing verifier, not a pass.
                "required_capabilities": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["problem_type", "formal_inputs"],
        },
    )


class DomainCheckVerifier(BaseVerifier):
    def __init__(self) -> None:
        super().__init__(_descriptor())

    async def verify(self, request: VerificationRequest) -> VerifierResult:
        from cognitive_os.domain.domains import VerificationDisposition, compose_disposition
        from cognitive_os.domains.registry import UnsupportedProblemType, resolve
        from cognitive_os.domains.solvers import SolverError
        from cognitive_os.tools.domains import candidate_from

        configuration = request.configuration
        try:
            entry = resolve(str(configuration["problem_type"]))
        except (KeyError, UnsupportedProblemType) as error:
            return self.result(
                request,
                VerifierStatus.UNVERIFIABLE,
                error=ErrorInfo(code="unsupported_problem_type", message=str(error)),
            )

        subject = request.subject.inline_value
        if not isinstance(subject, dict):
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(
                    code="invalid_domain_subject",
                    message="the verification subject must be a candidate answer object",
                ),
            )
        if subject.get("subject_absent") is True:
            # No answer was produced, so there is nothing to recompute. That is
            # undecided, not refuted: reporting `FAILED` would claim the checker
            # disproved an answer it never saw.
            return self.result(
                request,
                VerifierStatus.UNVERIFIABLE,
                error=ErrorInfo(
                    code="missing_subject_output",
                    message="the step under verification produced no candidate answer",
                ),
            )

        try:
            candidate = candidate_from(dict(subject))
            checks = entry.checker(
                dict(configuration["formal_inputs"]),  # type: ignore[arg-type]
                candidate,
                entry.budget,
            )
        except SolverError as error:
            return self.result(
                request,
                VerifierStatus.UNVERIFIABLE,
                error=ErrorInfo(code=error.code.value, message=str(error)),
            )
        except (KeyError, TypeError, ValueError) as error:
            return self.result(
                request,
                VerifierStatus.ERROR,
                error=ErrorInfo(code="invalid_domain_check", message=str(error)),
            )

        # A plan may require a capability the checker never exercised — including
        # one declared by the skill revision that was selected to run. That is a
        # missing verifier, not a pass, so it is injected as an explicit failure.
        # The direct `DomainPilotService` path has always done this; the governed
        # path did not, which let a declared-but-unrun verifier pass silently.
        declared = configuration.get("required_capabilities")
        required = declared if isinstance(declared, list) else []
        covered = {item.capability for item in checks}
        missing = tuple(item for item in required if isinstance(item, str) and item not in covered)
        if missing:
            return self.result(
                request,
                VerifierStatus.UNVERIFIABLE,
                code="domains.checker.unsupported",
                error=ErrorInfo(
                    code="missing_required_verifier",
                    message=f"required verifier did not run: {sorted(missing)}",
                ),
            )

        disposition = compose_disposition(tuple(item.disposition for item in checks))
        failed = [item for item in checks if item.disposition is not VerificationDisposition.PASS]
        # Anything short of a full pass stays non-passing. `INCONCLUSIVE`,
        # `UNSUPPORTED`, and `RESOURCE_EXHAUSTED` become `UNVERIFIABLE` rather
        # than `FAILED`, so an undecided check is never reported as a refutation.
        status = {
            VerificationDisposition.PASS: VerifierStatus.PASSED,
            VerificationDisposition.PARTIAL: VerifierStatus.PARTIAL,
            VerificationDisposition.FAIL: VerifierStatus.FAILED,
        }.get(disposition, VerifierStatus.UNVERIFIABLE)
        return self.result(
            request,
            status,
            code=f"domains.checker.{disposition.value}",
            message=failed[0].detail if failed else "all independent checks agree",
            score=1 if status is VerifierStatus.PASSED else 0,
        )
