"""The cross-domain path runs under Controller, Tool Plane, and Skill Engine authority."""

from uuid import uuid4

import pytest

from cognitive_os.domain.controller import ControllerState
from cognitive_os.domain.domains import DomainKind, VerificationDisposition
from cognitive_os.domain.skills import SkillExecutionStatus
from cognitive_os.domains.context import (
    RequiredContextMissingError,
    assert_required_context,
    build_domain_context,
    required_items,
)
from cognitive_os.domains.controller import (
    CHECKER_VERIFIER_ID,
    SOLVE_TOOL_ID,
    DomainPlanner,
    DomainProblemEngine,
    domain_budget,
    start_request,
)
from cognitive_os.domains.fixtures import build_all_cases, wrong_answer_for
from cognitive_os.domains.runner import run_case_controlled
from cognitive_os.domains.skill_execution import domain_task_signature
from cognitive_os.domains.skill_runner import run_case_as_skill
from cognitive_os.events.memory_store import MemoryEventStore

ALL_CASES = build_all_cases()
SAMPLE = (ALL_CASES[0], ALL_CASES[20], ALL_CASES[40])


# ------------------------------------------------- Controller-owned execution


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ALL_CASES, ids=lambda item: item.case_id)
async def test_every_case_terminates_in_its_declared_controller_state(case: object) -> None:
    """The controlled path lands in exactly the state the case declares.

    Sprint 21C.1: the coding domain's deliberately fallible baselines end
    FAILED and not accepted; everything else ends COMPLETED and accepted. Both
    halves are asserted per case, so a fixture that stops failing — or a
    regression that turns a working case into a failure — is caught here rather
    than being absorbed by a domain-wide exemption.
    """
    run = await run_case_controlled(case)  # type: ignore[arg-type]
    if case.expected_disposition is VerificationDisposition.PASS:  # type: ignore[attr-defined]
        assert run.state is ControllerState.COMPLETED, run.decision_reason
        assert run.accepted, run.decision_reason
    else:
        assert run.state is ControllerState.FAILED, run.decision_reason
        assert not run.accepted, run.decision_reason
    assert run.decision_reason


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ALL_CASES, ids=lambda item: item.case_id)
async def test_wrong_answers_are_rejected_by_the_acceptance_service(case: object) -> None:
    run = await run_case_controlled(
        case,  # type: ignore[arg-type]
        candidate_override=wrong_answer_for(case),  # type: ignore[arg-type]
    )
    assert not run.accepted


@pytest.mark.asyncio
async def test_the_controller_owns_the_plan_and_the_tool_plane_audits_the_solve() -> None:
    store = MemoryEventStore()
    run = await run_case_controlled(ALL_CASES[0], store=store)
    events = run.event_types

    # The plan is created by the Controller, not by the domain package.
    assert "plan.created" in events
    assert "problem.representation_created" in events
    assert "controller.state_changed" in events

    # Every solve is a Tool Plane call with a full authorisation trail.
    for expected in (
        "tool_call.requested",
        "tool_call.authorized",
        "tool_call.started",
        "tool_call.completed",
    ):
        assert expected in events, expected

    # Acceptance is recorded by the Acceptance Service.
    assert "controller.acceptance_decision_recorded" in events
    assert events.index("tool_call.completed") < events.index(
        "controller.acceptance_decision_recorded"
    )


@pytest.mark.asyncio
async def test_verification_runs_through_the_registered_verifier() -> None:
    run = await run_case_controlled(ALL_CASES[0])
    assert run.event_types.count("verifier.completed") >= 2
    assert run.verifier_calls >= 2


@pytest.mark.asyncio
async def test_domain_plans_contain_only_bounded_tool_actions() -> None:
    case = ALL_CASES[0]
    engine = DomainProblemEngine(case)
    request = start_request(case)
    problem = await engine.represent(
        type(
            "Seed",
            (),
            {
                "task_id": request.task_id,
                "task_run_id": request.task_run_id,
                "title": request.title,
                "request_hash": "a" * 64,
            },
        )()
    )
    plan = await DomainPlanner(case, engine.step_id).create_plan(problem, domain_budget())
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.action_type.value == "tool"
    assert action.tool_id == SOLVE_TOOL_ID
    assert action.provider_id is None and action.provider_instructions is None
    assert action.verifier_ids == (CHECKER_VERIFIER_ID,)
    assert len(plan.plan.steps) <= domain_budget().maximum_plan_steps


@pytest.mark.asyncio
async def test_the_mandatory_path_makes_no_real_provider_call() -> None:
    run = await run_case_controlled(ALL_CASES[0])
    # The Controller charges one nominal provider call for representation; no
    # provider action is ever planned or executed.
    assert run.tool_calls == 1
    assert run.provider_calls <= 1
    assert "model_call.completed" not in run.event_types


@pytest.mark.asyncio
async def test_the_problem_representation_carries_domain_evidence() -> None:
    case = next(item for item in ALL_CASES if item.domain is DomainKind.PHYSICS)
    engine = DomainProblemEngine(case)
    request = start_request(case)
    problem = await engine.represent(
        type(
            "Seed",
            (),
            {
                "task_id": request.task_id,
                "task_run_id": request.task_run_id,
                "title": request.title,
                "request_hash": "a" * 64,
            },
        )()
    )
    assert problem.domain.value == "physics"
    assert problem.assumptions
    assert any(item.category.value == "security" for item in problem.constraints)
    assert all(item.hard for item in problem.constraints)
    criteria = {item.criterion_type.value for item in problem.acceptance_criteria}
    assert criteria == {"domain_verifier", "step_completed"}
    assert all(item.required for item in problem.acceptance_criteria)


# --------------------------------------------------------- required context


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_context_bundle_covers_every_required_item(case: object) -> None:
    service, request = build_domain_context(
        case,  # type: ignore[arg-type]
        task_run_id=uuid4(),
        step_id=uuid4(),
    )
    built = await service.build_context(request)
    assert built.bundle is not None
    covered = assert_required_context(case, built.bundle)  # type: ignore[arg-type]
    assert len(covered) == len(required_items(case))  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize("omit", ("assumption:", "unit:", "provenance:"))
async def test_omitting_required_evidence_fails_closed(omit: str) -> None:
    case = next(item for item in ALL_CASES if item.domain is DomainKind.PHYSICS)
    service, request = build_domain_context(case, task_run_id=uuid4(), step_id=uuid4(), omit=omit)
    built = await service.build_context(request)
    with pytest.raises(RequiredContextMissingError):
        assert_required_context(case, built.bundle)


@pytest.mark.asyncio
async def test_omitting_task_state_is_refused_by_the_context_builder() -> None:
    from cognitive_os.context.errors import ContextRetrieverError

    service, request = build_domain_context(
        ALL_CASES[0], task_run_id=uuid4(), step_id=uuid4(), omit="task:"
    )
    with pytest.raises(ContextRetrieverError):
        await service.build_context(request)


def test_physics_cases_declare_their_units_as_required_context() -> None:
    for case in (item for item in ALL_CASES if item.domain is DomainKind.PHYSICS):
        identities = [item.identity for item in required_items(case)]
        assert any(item.startswith("unit:") for item in identities), case.case_id


# ------------------------------------------------------------------ routing


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_task_signature_is_tool_only_and_carries_exact_revisions(case: object) -> None:
    signature = domain_task_signature(case)  # type: ignore[arg-type]
    assert signature.required_tool_capabilities == ("domains.solve",)
    assert signature.verifier_profile == CHECKER_VERIFIER_ID
    assert signature.skill_revisions and signature.strategy_revisions
    assert signature.problem_class == case.problem_type  # type: ignore[attr-defined]


def test_task_signatures_are_deterministic_and_carry_no_prompt_text() -> None:
    for case in SAMPLE:
        first, second = domain_task_signature(case), domain_task_signature(case)
        assert first.content_hash == second.content_hash
        serialised = first.canonical_json()
        assert case.problem.statement not in serialised


def test_distinct_problem_classes_get_distinct_signatures() -> None:
    """No two different problem classes may share a routing signature.

    The reverse is allowed: one class can yield several signatures when its cases
    differ in a routing-relevant way — `satisfiability` produces both a
    `satisfiable` and an `unsatisfiable` output type, which a router should be
    able to tell apart.
    """
    owners: dict[str, set[str]] = {}
    for case in ALL_CASES:
        owners.setdefault(domain_task_signature(case).content_hash, set()).add(case.problem_type)
    collisions = {digest: names for digest, names in owners.items() if len(names) > 1}
    assert not collisions, collisions
    assert len(owners) >= len({item.problem_type for item in ALL_CASES})


# ------------------------------------------------------------ Skill Engine


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_cases_execute_as_exact_verified_skill_revisions(case: object) -> None:
    run = await run_case_as_skill(case)  # type: ignore[arg-type]
    assert run.result.status is SkillExecutionStatus.ACCEPTED
    assert run.result.acceptance_decision_id is not None
    assert run.controlled.state is ControllerState.COMPLETED
    # The skill reached the same governed path, including the Tool Plane trail.
    assert "tool_call.completed" in run.controlled.event_types


@pytest.mark.asyncio
@pytest.mark.parametrize("case", SAMPLE, ids=lambda item: item.case_id)
async def test_skill_execution_rejects_a_wrong_answer(case: object) -> None:
    run = await run_case_as_skill(
        case,  # type: ignore[arg-type]
        candidate_override=wrong_answer_for(case),  # type: ignore[arg-type]
    )
    assert run.result.status is SkillExecutionStatus.REJECTED
    assert run.result.acceptance_decision_id is None


@pytest.mark.asyncio
async def test_skill_execution_refuses_a_tampered_package_hash() -> None:
    """The composition really is subject to the Skill Engine's integrity checks."""
    from uuid import NAMESPACE_URL, uuid5

    from cognitive_os.domain.skills import SkillExecutionRequest, SkillStatus
    from cognitive_os.domains.fixtures import FIXTURE_TIME
    from cognitive_os.domains.registry import resolve
    from cognitive_os.domains.skill_execution import (
        DomainSkillRunner,
        domain_actor,
        domain_context_request_factory,
        domain_input_bindings,
    )
    from cognitive_os.domains.skill_runner import _context_builder, _hash
    from cognitive_os.skills.errors import SkillPolicyError
    from cognitive_os.skills.execution import SkillExecutionService
    from cognitive_os.skills.fixtures import sprint12_verified_skills

    case = ALL_CASES[0]
    repository, registry, artifacts = await sprint12_verified_skills()
    wanted = resolve(case.problem_type).skills[0]
    item, revision = next(
        (i, r) for i, r in registry.query() if i.identity.canonical_name == wanted
    )
    assert revision.status is SkillStatus.VERIFIED

    def snapshot():
        from cognitive_os.domain.skills import SkillRegistrySnapshot

        return SkillRegistrySnapshot(
            registry_hash=registry.snapshot_hash(),
            precondition_registry_hash=_hash("domain-precondition-registry-v1"),
            context_registry_hash=_hash("domain-context-registry-v1"),
            tool_registry_hash=_hash("domain-tool-registry-v1"),
            verifier_registry_hash=_hash("domain-verifier-registry-v1"),
            provider_registry_hash=_hash("domain-provider-registry-v1"),
        )

    service = SkillExecutionService(
        repository,
        artifacts,
        _context_builder(case),
        DomainSkillRunner(case),
        domain_context_request_factory(case),
        snapshot,
    )
    with pytest.raises(SkillPolicyError, match="package hash"):
        await service.start_execution(
            SkillExecutionRequest(
                execution_id=uuid5(NAMESPACE_URL, "tampered-execution"),
                skill_id=item.identity.skill_id,
                skill_revision=revision.revision,
                task_run_id=uuid5(NAMESPACE_URL, "tampered-task"),
                problem_reference=case.problem.problem_id,
                plan_reference=uuid5(NAMESPACE_URL, "tampered-plan"),
                input_bindings=domain_input_bindings(case),
                controller_budget=revision.resource_budget,
                expected_registry_snapshots=snapshot(),
                requested_by=domain_actor(),
                package_hash="f" * 64,
                created_at=FIXTURE_TIME,
            )
        )


@pytest.mark.asyncio
async def test_a_skill_revision_is_honoured_rather_than_ignored() -> None:
    """Selecting a skill must have a consequence.

    `DomainSkillRunner.start` previously ignored the revision it was handed and ran
    the identical governed path for every skill, which made Skill Engine selection
    causally inert: any ranking of any skill produced the same outcome. A skill
    package declares the verifier capability it claims to run, so executing a
    revision now requires that capability, and a declared verifier that never runs
    on this case cannot yield an accepted result.
    """
    case = next(item for item in ALL_CASES if item.domain is DomainKind.MATHEMATICS)

    matching = await run_case_controlled(
        case, required_capabilities=("mathematics.exact_arithmetic",)
    )
    assert matching.accepted

    # Declared but never exercised on a long-multiplication case: a symbolic
    # equivalence check is not part of this problem type's verification.
    mismatched = await run_case_controlled(
        case, required_capabilities=("mathematics.symbolic_equivalence",)
    )
    assert not mismatched.accepted


@pytest.mark.asyncio
async def test_declared_verifier_capabilities_come_from_the_package() -> None:
    from cognitive_os.domains.skill_execution import declared_verifier_capabilities
    from cognitive_os.skills.fixtures import sprint12_verified_skills

    _, registry, _ = await sprint12_verified_skills()
    declared = {
        item.identity.canonical_name: declared_verifier_capabilities(revision)
        for item, revision in registry.query()
    }
    assert declared["exact-arithmetic-decomposition"] == ("mathematics.exact_arithmetic",)
    assert declared["unit-aware-physics-calculation"] == ("physics.dimension",)
    assert declared["constraint-solving"] == ("logic.satisfiable",)
    # A skill that declares no verifier imposes no additional requirement.
    assert declared["evidence-collection"] == ()


@pytest.mark.asyncio
async def test_an_unexercised_required_capability_blocks_acceptance_on_the_governed_path() -> None:
    """The governed path enforces required capabilities, not only the direct path.

    `DomainPilotService` has always injected `UNSUPPORTED` for a required verifier
    that never ran. The Controller path did not, so a declared-but-unrun verifier
    passed silently.
    """
    case = ALL_CASES[0]
    run = await run_case_controlled(case, required_capabilities=("nonexistent.capability",))
    assert not run.accepted
    assert "verif" in run.decision_reason.lower() or run.decision_reason
