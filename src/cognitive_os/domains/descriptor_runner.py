"""Running a descriptor-registered domain's task through the released governed path.

Sprint 22A W2, §3.3: the mechanics pilot has to *solve and verify*, not merely register.
The two components the domain path contributes — the `domains.solve` tool and the
`domains.checker` verifier — both resolve a task **by its problem type alone**, so a domain
that arrived as a package uses them exactly as the released four do, with no change to
either. That is the substance of "no core branching": the solve is authorised, audited and
timed by the real Tool Plane, and the judgement is made by the real registered verifier
under the real verification service.

**What this composition deliberately stops short of.** `run_case_controlled` drives the
Cognitive Controller, and its entry point is a `DomainBenchmarkCase` whose `domain` field is
a `DomainKind`; the controller then maps that enum through two per-domain tables. Reaching
it from a descriptor-registered domain would mean widening a released contract and adding
core branching — precisely what Sprint 22A's exit criterion forbids. So the pilot runs
through the two governed components that are open to it, and the Controller's own state
machine is named in the W2 record as the boundary rather than quietly crossed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.domains import AnswerType
from cognitive_os.domain.enums import VerifierStatus
from cognitive_os.domain.tools import (
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolInvocation,
)
from cognitive_os.domain.verifiers import (
    VerificationRequest,
    VerificationSubject,
    VerificationSubjectType,
)
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.verification.factory import build_builtin_registry

from . import registry

SOLVE_TOOL_ID = "domains.solve"
CHECKER_VERIFIER_ID = "domains.checker"

#: The verification subject a candidate presents, chosen by what kind of answer it is
#: rather than by which domain produced it. The released controller keys the same choice on
#: `DomainKind`, which is exactly the branch a descriptor-registered domain cannot use — and
#: does not need, because the answer type already carries the information.
_SUBJECT_TYPES: dict[AnswerType, VerificationSubjectType] = {
    AnswerType.QUANTITY: VerificationSubjectType.PHYSICAL_QUANTITY,
    AnswerType.EXACT: VerificationSubjectType.MATHEMATICAL_EXPRESSION,
    AnswerType.APPROXIMATE: VerificationSubjectType.MATHEMATICAL_EXPRESSION,
    AnswerType.SYMBOLIC: VerificationSubjectType.MATHEMATICAL_EXPRESSION,
    AnswerType.BOOLEAN: VerificationSubjectType.LOGICAL_PROBLEM,
}


@dataclass(frozen=True, slots=True)
class DescriptorRun:
    """One task solved and judged, with both authorities' verdicts kept apart."""

    problem_type: str
    domain_id: str
    tool_status: str
    candidate: dict[str, Any]
    verifier_status: str
    message: str
    required_capabilities: tuple[str, ...]
    accepted: bool
    event_types: tuple[str, ...]


def build_tool_execution(store: MemoryEventStore) -> ToolExecutionService:
    """The released domain path's own Tool Plane composition, reused rather than rebuilt.

    A second copy of a policy construction is how two Tool Planes quietly drift apart: the
    released one grants no filesystem root and enables exactly one tool, and a pilot that
    built its own would be free to loosen either without anyone noticing.
    """
    from .runner import build_tool_execution as released_composition

    return released_composition(store)


async def run_descriptor_case(
    problem_type: str,
    formal_inputs: dict[str, Any],
    *,
    candidate_override: dict[str, Any] | None = None,
    required_capabilities: tuple[str, ...] = (),
    store: MemoryEventStore | None = None,
) -> DescriptorRun:
    """Solve one registered task through the Tool Plane and judge it with the verifier.

    `candidate_override` submits an answer the solver did not produce. The tool call, the
    verification request and the acceptance rule are identical either way, which is what
    makes a fabricated answer detectable here rather than trusted.

    `required_capabilities` adds capabilities the caller requires on top of the entry's own,
    mirroring the released `run_case_controlled`. A declared capability the checker never
    exercises must block acceptance rather than pass unnoticed, and this is how a descriptor
    that names a verifier nothing runs is caught (§3.5).
    """
    if store is None:
        store = MemoryEventStore()
    entry = registry.resolve(problem_type)

    invocation = ToolInvocation(
        tool_call_id=uuid4(),
        task_run_id=uuid4(),
        correlation_id=uuid4(),
        tool_id=SOLVE_TOOL_ID,
        tool_version="1",
        arguments={
            "problem_type": problem_type,
            "formal_inputs": registry.solver_inputs(entry, dict(formal_inputs)),
        },
        requested_at=datetime.now(UTC),
        requested_by=f"sprint-22a:{entry.domain_id}",
    )
    execution = await build_tool_execution(store).execute(
        invocation,
        ToolExecutionContext(
            workspace=str(Path.cwd()),
            timeout_seconds=30,
            maximum_stdout_bytes=65_536,
            maximum_stderr_bytes=65_536,
            maximum_artifact_bytes=65_536,
        ),
    )
    if execution.status is not ToolExecutionStatus.COMPLETED:
        return DescriptorRun(
            problem_type=problem_type,
            domain_id=entry.domain_id,
            tool_status=execution.status.value,
            candidate={},
            verifier_status="not_reached",
            message="the solve did not complete, so there was nothing to verify",
            required_capabilities=entry.required_verifiers,
            accepted=False,
            event_types=store.event_types(),
        )

    produced = execution.result
    if not isinstance(produced, dict):
        raise TypeError(f"{SOLVE_TOOL_ID} returned {type(produced).__name__}, not an object")
    candidate: dict[str, Any] = candidate_override or dict(produced)
    verification_id = uuid5(NAMESPACE_URL, f"sprint-22a:{problem_type}:{uuid4()}")
    request = VerificationRequest(
        verification_id=verification_id,
        task_run_id=invocation.task_run_id,
        criterion_id=uuid4(),
        verifier_id=CHECKER_VERIFIER_ID,
        verifier_version="1",
        subject=VerificationSubject(
            subject_type=_SUBJECT_TYPES.get(
                entry.answer_type, VerificationSubjectType.STRUCTURED_VALUE
            ),
            inline_value=candidate,
        ),
        configuration={
            "problem_type": problem_type,
            "formal_inputs": dict(formal_inputs),
            # Every capability the entry requires must actually be exercised. A declared
            # verifier that never ran is a missing verifier, not a pass — the released
            # checker enforces that, and a pilot is held to it from its first run.
            "required_capabilities": list(
                dict.fromkeys((*entry.required_verifiers, *required_capabilities))
            ),
        },
        requested_at=utc_now(),
        correlation_id=invocation.correlation_id,
    )
    outcome = await VerificationService(
        build_builtin_registry(), VerifierEventService(store)
    ).execute(request)
    result = outcome.result
    status = result.status if result else VerifierStatus.UNVERIFIABLE
    # A pass carries no finding by construction; a failure carries the first check that
    # disagreed, and an unverifiable outcome carries its error. Reporting whichever exists
    # keeps a refusal's reason in the record instead of only its verdict.
    message = ""
    if result is not None:
        message = result.findings[0].message if result.findings else ""
        if not message and result.error is not None:
            message = result.error.message
    return DescriptorRun(
        problem_type=problem_type,
        domain_id=entry.domain_id,
        tool_status=execution.status.value,
        candidate=candidate,
        verifier_status=status.value,
        message=message,
        required_capabilities=entry.required_verifiers,
        accepted=status is VerifierStatus.PASSED,
        event_types=store.event_types(),
    )


__all__ = ["DescriptorRun", "build_tool_execution", "run_descriptor_case"]
