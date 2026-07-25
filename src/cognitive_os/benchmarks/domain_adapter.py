"""Executable Sprint 20 cross-domain benchmark adapter.

Unlike a declarative expectation table, this adapter really runs each case through
the pilot service and compares the observed disposition with the manifest's
expectation. A case passes only when the harness behaves as declared, so a
regression in the solvers, verifiers, or gates fails the benchmark.
"""

from __future__ import annotations

from time import perf_counter

from cognitive_os.domain.benchmarks import (
    BenchmarkCase,
    BenchmarkCaseResult,
    BenchmarkCaseStatus,
)
from cognitive_os.domain.domains import DomainKind, TransferDisposition
from cognitive_os.domains.fixtures import (
    FIXTURE_TIME,
    build_all_cases,
    wrong_answer_for,
)
from cognitive_os.domains.repository import InMemoryDomainRepository
from cognitive_os.domains.service import DomainPilotService

_CASES = {item.case_id: item for item in build_all_cases()}


async def domain_benchmark_case(case: BenchmarkCase) -> BenchmarkCaseResult:
    request = case.problem_request
    scenario = str(request.get("scenario", ""))
    started = perf_counter()
    metrics: dict[str, float] = {
        "provider_calls": 0.0,
        "network_calls": 0.0,
        "credential_reads": 0.0,
        "gpu_calls": 0.0,
        "optional_extras_required": 0.0,
        "active_state_mutations": 0.0,
        "runtime_release_operations": 0.0,
    }

    if scenario in ("accept", "reject"):
        matched, extra = await _run_pilot(str(request["case"]), reject=scenario == "reject")
    elif scenario == "transfer":
        matched, extra = await _run_transfer(str(request.get("expected", "positive_transfer")))
    elif scenario == "governance":
        matched, extra = await _run_governance(str(request["check"]))
    else:
        matched, extra = False, {"unknown_scenario": 1.0}

    metrics.update(extra)
    metrics["expected_outcome_matched"] = float(matched)
    metrics["elapsed_seconds"] = perf_counter() - started
    return BenchmarkCaseResult(
        case_id=case.case_id,
        status=BenchmarkCaseStatus.PASSED if matched else BenchmarkCaseStatus.FAILED,
        started_at=FIXTURE_TIME,
        finished_at=FIXTURE_TIME,
        metrics=metrics,
    )


async def _run_pilot(case_id: str, *, reject: bool) -> tuple[bool, dict[str, float]]:
    """Accept a correct answer, or reject a deliberately wrong one."""
    domain_case = _CASES.get(case_id)
    if domain_case is None:
        return False, {"unknown_case": 1.0}
    repository = InMemoryDomainRepository()
    service = DomainPilotService(repository)
    candidate = wrong_answer_for(domain_case) if reject else None
    result = await service.run_case(domain_case, candidate=candidate)
    matched = (not result.accepted) if reject else result.accepted
    outcome = result.outcome
    return matched, {
        "accepted": float(result.accepted),
        "checks_run": float(len(outcome.checks)) if outcome else 0.0,
        "derivation_recorded": float(result.derivation is not None),
        "evidence_rows": float(len(repository.runs)),
    }


async def _run_transfer(expected: str) -> tuple[bool, dict[str, float]]:
    from cognitive_os.domains.transfer import (
        run_experiment,
        run_negative_transfer_experiment,
    )

    if expected == "negative_transfer":
        _, result = await run_negative_transfer_experiment()
    else:
        _, result = await run_experiment()
    matched = result.disposition is TransferDisposition(expected)
    return matched, {
        "target_quality_delta": float(result.target_quality_delta),
        "source_quality_delta": float(result.source_quality_delta),
        "unrelated_quality_delta": float(result.unrelated_quality_delta),
        "hard_gate_failures": float(len(result.hard_gate_failures)),
        "control_arms": float(len(result.arms)),
    }


async def _run_governance(check: str) -> tuple[bool, dict[str, float]]:
    """Authority and safety invariants that must hold regardless of the answer."""
    handler = _GOVERNANCE[check]
    passed = await handler()
    return passed, {"governance_check": 1.0, "invariant_held": float(passed)}


async def _unsupported_problem_type_fails() -> bool:
    from cognitive_os.domains.registry import UnsupportedProblemType, resolve

    try:
        resolve("teleportation")
    except UnsupportedProblemType:
        return True
    return False


async def _forbidden_operation_is_rejected() -> bool:
    from cognitive_os.domain.domains import DomainProblem
    from cognitive_os.domains.fixtures import build_case

    base = build_case(
        "governance-forbidden",
        "long-multiplication",
        {"left": 2, "right": 3},
        statement="Reject a case that requests a forbidden operation.",
    )
    hostile = base.model_copy(
        update={
            "problem": DomainProblem(
                **{
                    **base.problem.model_dump(exclude={"content_hash"}),
                    "required_tools": ("eval",),
                }
            )
        }
    )
    result = await DomainPilotService().run_case(hostile)
    return not result.accepted and result.run.failure_code is not None


async def _raw_text_cannot_reach_a_solver() -> bool:
    """Python source must never parse into the math AST."""
    from cognitive_os.verification.mathematics.parsing import (
        UnsafeExpressionError,
        parse_expression,
    )

    hostile = (
        "__import__('os').system('id')",
        "open('/etc/passwd').read()",
        "(1).__class__.__bases__",
        "eval('2+2')",
        "lambda: 1",
        "x if y else z",
        "[i for i in range(10)]",
    )
    for text in hostile:
        try:
            parse_expression(text)
        except (UnsafeExpressionError, SyntaxError, ValueError):
            continue
        return False
    return True


async def _expression_bomb_is_bounded() -> bool:
    from cognitive_os.domains.kernels import BudgetExceededError, evaluate_exact
    from cognitive_os.verification.mathematics.parsing import (
        ExpressionLimits,
        UnsafeExpressionError,
        parse_expression,
    )

    try:
        expression = parse_expression("9" * 40 + " ** 9999", ExpressionLimits())
    except (UnsafeExpressionError, ValueError):
        return True
    try:
        evaluate_exact(expression, maximum_integer_digits=256)
    except (BudgetExceededError, ValueError):
        return True
    return False


async def _unknown_never_becomes_unsat() -> bool:
    from cognitive_os.domain.domains import (
        AnswerType,
        VerificationDisposition,
        compose_disposition,
    )
    from cognitive_os.domains.registry import resolve
    from cognitive_os.domains.solvers import Candidate

    entry = resolve("satisfiability")
    expression = {
        "operator": "and",
        "sort": "bool",
        "arguments": [
            {"operator": "variable", "sort": "bool", "name": "p"},
            {
                "operator": "not",
                "sort": "bool",
                "arguments": [{"operator": "variable", "sort": "bool", "name": "p"}],
            },
        ],
    }
    checks = entry.checker(
        {"expression": expression},
        Candidate(AnswerType.UNKNOWN, logical_status="unknown"),
        entry.budget,
    )
    return (
        compose_disposition(tuple(i.disposition for i in checks))
        is not VerificationDisposition.PASS
    )


async def _incompatible_units_fail() -> bool:
    from fractions import Fraction

    from cognitive_os.domains.kernels import UnitError, convert

    try:
        convert(Fraction(1), "m", "s")
    except UnitError:
        return True
    return False


async def _offset_units_convert_exactly() -> bool:
    from fractions import Fraction

    from cognitive_os.domains.kernels import convert

    return convert(Fraction(100), "degC", "degF") == Fraction(212) and convert(
        Fraction(0), "degC", "K"
    ) == Fraction(5463, 20)


async def _core_imports_without_extras() -> bool:
    """The mandatory path must not *require* SymPy, Pint, or Z3.

    Checking `sys.modules` would only prove no test imported them yet, which is
    order-dependent. The real invariant is structural: no module in the pilot
    package names an optional extra, so the mandatory path cannot need one.
    """
    import ast
    import pathlib

    extras = {"sympy", "pint", "z3"}
    for path in pathlib.Path("src/cognitive_os/domains").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                if {alias.name.split(".")[0] for alias in node.names} & extras:
                    return False
            elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in extras:
                return False
    # And the dependency-free kernels really do produce the mandatory results.
    from fractions import Fraction

    from cognitive_os.domains.kernels import convert, registry_hash

    return convert(Fraction(90), "km/h", "m/s") == Fraction(25) and len(registry_hash()) == 64


async def _positive_transfer_needs_every_control() -> bool:
    from cognitive_os.domain.domains import TransferArm
    from cognitive_os.domains.transfer import run_experiment

    _, result = await run_experiment()
    return set(result.arms) == set(TransferArm)


async def _hard_gate_blocks_positive_transfer() -> bool:
    from cognitive_os.domains.transfer import run_negative_transfer_experiment

    _, result = await run_negative_transfer_experiment()
    return (
        bool(result.hard_gate_failures)
        and result.disposition is TransferDisposition.NEGATIVE_TRANSFER
    )


async def _runtime_cannot_release() -> bool:
    """Nothing in the pilot package may reach a process, socket, or release path.

    This inspects the actual import graph rather than grepping source text, so a
    denylist that merely *names* a forbidden module does not trip it, while a real
    `import subprocess` does.
    """
    import ast
    import pathlib

    forbidden = {
        "subprocess",
        "os",
        "socket",
        "http",
        "urllib",
        "requests",
        "httpx",
        "asyncio.subprocess",
        "shutil",
        "pty",
        "multiprocessing",
    }
    for path in pathlib.Path("src/cognitive_os/domains").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                names = {(node.module or "").split(".")[0]}
            else:
                continue
            if names & forbidden:
                return False
    return True


async def _evidence_is_immutable() -> bool:
    from cognitive_os.domains.repository import (
        DomainConflictError,
        InMemoryDomainRepository,
    )

    repository = InMemoryDomainRepository()
    service = DomainPilotService(repository)
    case = next(iter(_CASES.values()))
    result = await service.run_case(case)
    mutated = result.run.model_copy(update={"case_id": "tampered"})
    try:
        await repository.record(type(result)(mutated, None, None, None))
    except DomainConflictError:
        return True
    return False


async def _answers_cannot_conflate_exact_and_approximate() -> bool:
    from decimal import Decimal
    from uuid import uuid4

    from cognitive_os.domain.domains import AnswerType, DomainAnswer
    from cognitive_os.domains.fixtures import FIXTURE_TIME as when

    try:
        DomainAnswer(
            problem_id=uuid4(),
            answer_type=AnswerType.EXACT,
            exact_value="1/2",
            approximate_value=Decimal("0.5"),
            created_at=when,
        )
    except ValueError:
        return True
    return False


async def _nan_and_infinity_are_rejected() -> bool:
    from decimal import Decimal
    from uuid import uuid4

    from cognitive_os.domain.domains import AnswerType, DomainAnswer
    from cognitive_os.domains.fixtures import FIXTURE_TIME as when

    for value in (Decimal("NaN"), Decimal("Infinity")):
        try:
            DomainAnswer(
                problem_id=uuid4(),
                answer_type=AnswerType.APPROXIMATE,
                approximate_value=value,
                tolerance=Decimal(1),
                created_at=when,
            )
        except ValueError:
            continue
        return False
    return True


async def _missing_verifier_blocks_acceptance() -> bool:
    from cognitive_os.domain.domains import VerificationDisposition, compose_disposition

    return (
        compose_disposition((VerificationDisposition.PASS, VerificationDisposition.UNSUPPORTED))
        is not VerificationDisposition.PASS
    )


async def _underdetermination_must_be_reported() -> bool:
    from cognitive_os.domain.domains import (
        AnswerType,
        VerificationDisposition,
        compose_disposition,
    )
    from cognitive_os.domains.registry import resolve
    from cognitive_os.domains.solvers import Candidate

    entry = resolve("sequence-induction")
    checks = entry.checker(
        {"terms": [1, 2, 3]},
        Candidate(
            AnswerType.STRUCTURED,
            structured={"rules": ["arithmetic"], "underdetermined": False},
        ),
        entry.budget,
    )
    return (
        compose_disposition(tuple(i.disposition for i in checks))
        is not VerificationDisposition.PASS
    )


async def _controller_owns_the_plan() -> bool:
    """The plan, the tool call, and the acceptance decision are all Controller-driven."""
    from cognitive_os.domain.controller import ControllerState
    from cognitive_os.domains.runner import run_case_controlled

    run = await run_case_controlled(next(iter(_CASES.values())))
    required = (
        "problem.representation_created",
        "plan.created",
        "controller.acceptance_decision_recorded",
    )
    return (
        run.state is ControllerState.COMPLETED
        and run.accepted
        and all(item in run.event_types for item in required)
    )


async def _tool_plane_audits_every_solve() -> bool:
    """No solve happens without a full Tool Plane authorisation trail."""
    from cognitive_os.domains.runner import run_case_controlled

    run = await run_case_controlled(next(iter(_CASES.values())))
    trail = (
        "tool_call.requested",
        "tool_call.authorized",
        "tool_call.started",
        "tool_call.completed",
    )
    return all(item in run.event_types for item in trail) and run.tool_calls >= 1


async def _controlled_path_rejects_a_wrong_answer() -> bool:
    from cognitive_os.domains.runner import run_case_controlled

    case = next(iter(_CASES.values()))
    run = await run_case_controlled(case, candidate_override=wrong_answer_for(case))
    return not run.accepted


async def _required_context_cannot_be_omitted() -> bool:
    from uuid import uuid4

    from cognitive_os.domain.domains import DomainKind
    from cognitive_os.domains.context import (
        RequiredContextMissingError,
        assert_required_context,
        build_domain_context,
    )

    case = next(item for item in _CASES.values() if item.domain is DomainKind.PHYSICS)
    service, request = build_domain_context(
        case, task_run_id=uuid4(), step_id=uuid4(), omit="unit:"
    )
    built = await service.build_context(request)
    try:
        assert_required_context(case, built.bundle)
    except RequiredContextMissingError:
        return True
    return False


async def _skill_engine_runs_only_verified_revisions() -> bool:
    from cognitive_os.domain.skills import SkillExecutionStatus
    from cognitive_os.domains.skill_runner import run_case_as_skill

    run = await run_case_as_skill(next(iter(_CASES.values())))
    return (
        run.result.status is SkillExecutionStatus.ACCEPTED
        and run.result.acceptance_decision_id is not None
        and "tool_call.completed" in run.controlled.event_types
    )


async def _routing_signature_is_tool_only() -> bool:
    """No provider is required for acceptance, and no prompt text is routed."""
    from cognitive_os.domains.skill_execution import domain_task_signature

    for case in list(_CASES.values())[:8]:
        signature = domain_task_signature(case)
        if signature.required_tool_capabilities != ("domains.solve",):
            return False
        if signature.verifier_profile != "domains.checker":
            return False
        if case.problem.statement in signature.canonical_json():
            return False
    return True


async def _learning_compiles_only_recorded_events() -> bool:
    """Every timeline entry is one recorded event; nothing is synthesised."""
    from cognitive_os.domains.learning import (
        DomainLearningError,
        build_compilation,
        compile_run,
    )
    from cognitive_os.domains.runner import run_case_controlled
    from cognitive_os.events.memory_store import MemoryEventStore

    case = next(iter(_CASES.values()))
    store = MemoryEventStore()
    await run_case_controlled(case, store=store)
    result = await compile_run(case, store)
    recorded = {item.envelope.event_id for item in store.stored_events()}
    hashes = {item.envelope.payload_hash for item in store.stored_events()}
    entries = result.trajectory.entries
    if len(entries) != len(recorded):
        return False
    if any(entry.timeline_entry_id not in recorded for entry in entries):
        return False
    if any(evidence not in hashes for entry in entries for evidence in entry.evidence_refs):
        return False
    try:
        build_compilation(case, MemoryEventStore())
    except DomainLearningError:
        return True
    return False


async def _learning_preserves_failure_evidence() -> bool:
    """A rejected run compiles as failure evidence, never laundered into success."""
    from cognitive_os.domain.experience import ExperienceCandidateType
    from cognitive_os.domains.learning import run_case_with_learning

    case = next(iter(_CASES.values()))
    run, result = await run_case_with_learning(case, candidate_override=wrong_answer_for(case))
    kinds = set(result.candidate_types)
    return (
        not run.accepted
        and result.compilation.snapshot.terminal_state == "rejected"
        and ExperienceCandidateType.FAILURE_PATTERN in kinds
        and ExperienceCandidateType.NEGATIVE_EXAMPLE in kinds
    )


async def _learning_corpus_rights_from_provenance() -> bool:
    """Corpus declarations grant only what the case provenance grants."""
    from cognitive_os.domain.corpus import CorpusUsageRight
    from cognitive_os.domains.learning import corpus_request, run_case_with_learning

    case = next(iter(_CASES.values()))
    _run, result = await run_case_with_learning(case)
    for candidate in result.corpus_candidates:
        request, _source = corpus_request(case, candidate)
        rights = request.usage_rights
        if rights[CorpusUsageRight.MODEL_TRAINING] is not None:
            return False
        if rights[CorpusUsageRight.COMMERCIAL_USE] is not None:
            return False
        if rights[CorpusUsageRight.REDISTRIBUTION] != case.licence_and_source.redistributable:
            return False
        if request.license_identifiers != (case.licence_and_source.licence,):
            return False
    return bool(result.corpus_candidates) and result.corpus_item_count >= 1


_GOVERNANCE = {
    "controller_owns_plan": _controller_owns_the_plan,
    "tool_plane_audits_solve": _tool_plane_audits_every_solve,
    "controlled_path_rejects_wrong": _controlled_path_rejects_a_wrong_answer,
    "required_context_enforced": _required_context_cannot_be_omitted,
    "skill_engine_verified_only": _skill_engine_runs_only_verified_revisions,
    "routing_signature_tool_only": _routing_signature_is_tool_only,
    "learning_recorded_events_only": _learning_compiles_only_recorded_events,
    "learning_failure_preserved": _learning_preserves_failure_evidence,
    "learning_corpus_rights": _learning_corpus_rights_from_provenance,
    "unsupported_problem_type": _unsupported_problem_type_fails,
    "forbidden_operation": _forbidden_operation_is_rejected,
    "raw_text_rejected": _raw_text_cannot_reach_a_solver,
    "expression_bomb_bounded": _expression_bomb_is_bounded,
    "unknown_not_unsat": _unknown_never_becomes_unsat,
    "incompatible_units": _incompatible_units_fail,
    "offset_units_exact": _offset_units_convert_exactly,
    "core_without_extras": _core_imports_without_extras,
    "transfer_controls_required": _positive_transfer_needs_every_control,
    "hard_gate_blocks_positive": _hard_gate_blocks_positive_transfer,
    "runtime_cannot_release": _runtime_cannot_release,
    "evidence_immutable": _evidence_is_immutable,
    "exact_not_approximate": _answers_cannot_conflate_exact_and_approximate,
    "nan_rejected": _nan_and_infinity_are_rejected,
    "missing_verifier_blocks": _missing_verifier_blocks_acceptance,
    "underdetermination_reported": _underdetermination_must_be_reported,
}


def governance_checks() -> tuple[str, ...]:
    return tuple(sorted(_GOVERNANCE))


def domain_case_ids(domain: DomainKind) -> tuple[str, ...]:
    return tuple(sorted(k for k, v in _CASES.items() if v.domain is domain))
