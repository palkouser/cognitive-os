"""Composition that runs a cross-domain case through the real governed stack.

Everything assembled here is an existing Cognitive OS service. The domain sprint
contributes exactly two things to this pipeline — the `domains.solve` tool and the
`domains.checker` verifier — and borrows planning, execution, budgets, state
transitions, verification, and acceptance from the components that already own
them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cognitive_os.application.services.acceptance_service import AcceptancePolicyService
from cognitive_os.application.services.approval_service import DenyAllApprovalProvider
from cognitive_os.application.services.cognitive_controller import (
    BoundedCognitiveController,
)
from cognitive_os.application.services.controller_recovery import (
    ControllerRecoveryService,
)
from cognitive_os.application.services.controller_verification import (
    ControllerVerificationService,
)
from cognitive_os.application.services.minimal_acceptance import (
    MinimalAcceptanceService,
)
from cognitive_os.application.services.tool_execution import ToolExecutionService
from cognitive_os.application.services.verification_service import VerificationService
from cognitive_os.config.controller_config import ControllerConfiguration
from cognitive_os.domain.controller import ControllerState
from cognitive_os.domain.domains import DomainBenchmarkCase
from cognitive_os.events.controller_event_service import ControllerEventService
from cognitive_os.events.memory_store import MemoryEventStore
from cognitive_os.events.tool_event_service import ToolEventService
from cognitive_os.events.verifier_event_service import VerifierEventService
from cognitive_os.tools.domains import DomainSolveTool
from cognitive_os.tools.policy import ToolPolicyEngine
from cognitive_os.tools.registry import ToolRegistry
from cognitive_os.verification.factory import build_builtin_registry

from .controller import (
    SOLVE_TOOL_ID,
    DomainActionExecutor,
    DomainPlanner,
    DomainProblemEngine,
    domain_budget,
    start_request,
)


@dataclass(frozen=True, slots=True)
class ControlledRun:
    """One case executed end to end under Controller and Tool Plane authority."""

    state: ControllerState
    accepted: bool
    tool_calls: int
    provider_calls: int
    verifier_calls: int
    problem_id: Any
    plan_id: Any
    event_types: tuple[str, ...]
    decision_reason: str

    @property
    def completed(self) -> bool:
        return self.state is ControllerState.COMPLETED


def domain_configuration() -> ControllerConfiguration:
    """Provider-free: the mandatory domain path names no model and calls none."""
    return ControllerConfiguration(
        default_provider_id="none",
        problem_representation_provider_id="none",
        planning_provider_id="none",
        budgets=domain_budget(),
    )


def build_tool_execution(store: MemoryEventStore) -> ToolExecutionService:
    """Tool Plane with only the deterministic domain solver enabled."""
    from pathlib import Path

    registry = ToolRegistry()
    registry.register(DomainSolveTool())
    registry.freeze()
    return ToolExecutionService(
        registry,
        # Least privilege: exactly one enabled tool, and no filesystem root is
        # granted because the solver never touches a path.
        ToolPolicyEngine((Path.cwd(),), frozenset({SOLVE_TOOL_ID})),
        DenyAllApprovalProvider(),
        ToolEventService(store),
    )


async def run_case_controlled(
    case: DomainBenchmarkCase,
    *,
    candidate_override: Any | None = None,
    store: MemoryEventStore | None = None,
    required_capabilities: tuple[str, ...] = (),
) -> ControlledRun:
    """Execute one domain case through the Cognitive Controller.

    `candidate_override` submits an externally proposed answer. The plan, the tool
    call, and the acceptance path are unchanged, which is what makes a fabricated
    answer detectable rather than trusted.

    `required_capabilities` adds verifier capabilities the caller requires on top
    of the case's own — a selected skill revision declares the verifier it claims
    to run, and a declared capability the checker never exercises must block
    acceptance instead of passing unnoticed.
    """
    # `is None`, not truthiness: an empty store is falsy through `__len__`, and
    # `or` would silently swap a caller's store for a private one whose events
    # they can never read.
    if store is None:
        store = MemoryEventStore()
    problem_engine = DomainProblemEngine(case, required_capabilities=required_capabilities)
    planner = DomainPlanner(case, problem_engine.step_id)
    tool_execution = build_tool_execution(store)
    executor = DomainActionExecutor(tool_execution, candidate_override=candidate_override)

    verifier_registry = build_builtin_registry()
    verification = ControllerVerificationService(
        VerificationService(verifier_registry, VerifierEventService(store)),
        AcceptancePolicyService(),
    )

    controller = BoundedCognitiveController(
        problem_engine=problem_engine,
        planning=planner,
        action_executor=executor,
        acceptance=MinimalAcceptanceService(),
        verification=verification,
        events=ControllerEventService(store),
        recovery=ControllerRecoveryService(store),
        configuration=domain_configuration(),
        tool_descriptors=(DomainSolveTool.descriptor,),
    )

    result = await controller.start(start_request(case))
    decision = result.acceptance_decision
    return ControlledRun(
        state=result.state,
        accepted=bool(decision and decision.accepted),
        tool_calls=result.usage.tool_calls,
        provider_calls=result.usage.provider_calls,
        verifier_calls=result.usage.verifier_calls,
        problem_id=result.problem_representation.problem_id
        if result.problem_representation
        else None,
        plan_id=result.plan.plan.plan_id if result.plan else None,
        event_types=store.event_types(),
        decision_reason=decision.decision_reason if decision else (result.error or ""),
    )
