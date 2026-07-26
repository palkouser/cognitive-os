"""Sprint 20 cross-domain pilot: contracts, kernels, acceptance, and transfer."""

from decimal import Decimal
from fractions import Fraction
from uuid import uuid4

import pytest

from cognitive_os.benchmarks.domain_adapter import (
    _GOVERNANCE,
    domain_case_ids,
    governance_checks,
)
from cognitive_os.domain.domains import (
    AnswerType,
    DomainAnswer,
    DomainKind,
    DomainRunStatus,
    TransferArm,
    TransferDisposition,
    VerificationDisposition,
    compose_disposition,
)
from cognitive_os.domains import kernels
from cognitive_os.domains.fixtures import (
    FALLIBLE_CODING_CASES,
    FIXTURE_TIME,
    MINIMUM_FALLIBLE_CODING_CASES,
    build_all_cases,
    wrong_answer_for,
)
from cognitive_os.domains.registry import (
    UnsupportedProblemType,
    entries,
    problem_types,
    resolve,
    snapshot_hash,
)
from cognitive_os.domains.repository import DomainConflictError, InMemoryDomainRepository
from cognitive_os.domains.service import DomainPilotService
from cognitive_os.domains.transfer import run_experiment, run_negative_transfer_experiment
from cognitive_os.verification.mathematics.parsing import (
    UnsafeExpressionError,
    parse_expression,
)

ALL_CASES = build_all_cases()


# --------------------------------------------------------------- registry


def test_every_domain_has_registered_task_classes() -> None:
    assert len(problem_types(DomainKind.MATHEMATICS)) >= 8
    assert len(problem_types(DomainKind.PHYSICS)) >= 8
    assert len(problem_types(DomainKind.LOGIC)) >= 8
    assert snapshot_hash() == snapshot_hash()


def test_unregistered_problem_type_fails_closed() -> None:
    with pytest.raises(UnsupportedProblemType):
        resolve("perpetual-motion")


def test_every_entry_resolves_exactly_once() -> None:
    names = [item.problem_type for item in entries()]
    assert len(names) == len(set(names))
    assert names == sorted(names)


# ---------------------------------------------------------------- kernels


@pytest.mark.parametrize(
    ("expression", "expected"),
    (
        ("1/3 + 1/6", Fraction(1, 2)),
        ("2 ** 10", Fraction(1024)),
        ("sqrt(49/4)", Fraction(7, 2)),
        ("(2/3 - 1/6) * 4/5", Fraction(2, 5)),
    ),
)
def test_exact_arithmetic_stays_exact(expression: str, expected: Fraction) -> None:
    assert kernels.evaluate_exact(parse_expression(expression)) == expected


@pytest.mark.parametrize("expression", ("sqrt(2)", "1/0", "pi"))
def test_inexact_results_raise_rather_than_rounding(expression: str) -> None:
    with pytest.raises(kernels.InexactError):
        kernels.evaluate_exact(parse_expression(expression))


def test_integer_digit_ceiling_fails_closed() -> None:
    with pytest.raises(kernels.BudgetExceededError):
        kernels.evaluate_exact(parse_expression("99 ** 500"), maximum_integer_digits=16)


@pytest.mark.parametrize(
    ("magnitude", "source", "target", "expected"),
    (
        (Fraction(90), "km/h", "m/s", Fraction(25)),
        (Fraction(1), "h", "s", Fraction(3600)),
        (Fraction(100), "degC", "degF", Fraction(212)),
        (Fraction(0), "degC", "K", Fraction(5463, 20)),
        (Fraction(32), "degF", "degC", Fraction(0)),
    ),
)
def test_unit_conversion_is_exact(
    magnitude: Fraction, source: str, target: str, expected: Fraction
) -> None:
    assert kernels.convert(magnitude, source, target) == expected


def test_incompatible_units_are_rejected() -> None:
    with pytest.raises(kernels.UnitError):
        kernels.convert(Fraction(1), "m", "s")


def test_derived_units_reduce_to_base_dimensions() -> None:
    assert kernels.dimension_of("N") == kernels.dimension_of("kg*m/s^2")
    assert kernels.dimension_of("J") == kernels.dimension_of("N*m")
    assert kernels.dimension_of("J") != kernels.dimension_of("N")


def test_unknown_and_injected_units_are_rejected() -> None:
    for unit in ("furlong", "m; DROP TABLE", "__import__", "m/s/s"):
        with pytest.raises(kernels.UnitError):
            kernels.parse_unit(unit)


def test_unit_registry_hash_is_stable() -> None:
    assert kernels.registry_hash() == kernels.registry_hash()
    assert len(kernels.registry_hash()) == 64


def test_propositional_classification_is_exhaustive() -> None:
    def variable(name: str) -> object:
        return {"operator": "variable", "sort": "bool", "name": name}

    from cognitive_os.verification.logic.ast import LogicExpression

    excluded_middle = LogicExpression.model_validate(
        {
            "operator": "or",
            "sort": "bool",
            "arguments": [
                variable("p"),
                {"operator": "not", "sort": "bool", "arguments": [variable("p")]},
            ],
        }
    )
    assert kernels.classify(excluded_middle) == "tautology"
    assert kernels.counterexample(excluded_middle) is None


def test_truth_table_row_ceiling_fails_closed() -> None:
    from cognitive_os.verification.logic.ast import LogicExpression

    expression = LogicExpression.model_validate(
        {
            "operator": "or",
            "sort": "bool",
            "arguments": [
                {"operator": "variable", "sort": "bool", "name": f"v{index}"} for index in range(6)
            ],
        }
    )
    with pytest.raises(kernels.BudgetExceededError):
        kernels.truth_table(expression, maximum_rows=8)


# --------------------------------------------------------------- contracts


def test_exact_answers_cannot_carry_an_approximation() -> None:
    with pytest.raises(ValueError, match="approximate"):
        DomainAnswer(
            problem_id=uuid4(),
            answer_type=AnswerType.EXACT,
            exact_value="1/2",
            approximate_value=Decimal("0.5"),
            created_at=FIXTURE_TIME,
        )


@pytest.mark.parametrize("value", (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")))
def test_non_finite_answers_are_rejected(value: Decimal) -> None:
    with pytest.raises(ValueError):
        DomainAnswer(
            problem_id=uuid4(),
            answer_type=AnswerType.APPROXIMATE,
            approximate_value=value,
            tolerance=Decimal(1),
            created_at=FIXTURE_TIME,
        )


def test_quantity_answers_require_units() -> None:
    with pytest.raises(ValueError, match="units"):
        DomainAnswer(
            problem_id=uuid4(),
            answer_type=AnswerType.QUANTITY,
            exact_value="25",
            created_at=FIXTURE_TIME,
        )


@pytest.mark.parametrize(
    ("dispositions", "expected"),
    (
        ((VerificationDisposition.PASS,), VerificationDisposition.PASS),
        (
            (VerificationDisposition.PASS, VerificationDisposition.FAIL),
            VerificationDisposition.FAIL,
        ),
        (
            (VerificationDisposition.PASS, VerificationDisposition.INCONCLUSIVE),
            VerificationDisposition.INCONCLUSIVE,
        ),
        (
            (VerificationDisposition.PASS, VerificationDisposition.UNSUPPORTED),
            VerificationDisposition.UNSUPPORTED,
        ),
        ((), VerificationDisposition.FAIL),
    ),
)
def test_acceptance_never_upgrades_a_non_pass(
    dispositions: tuple[VerificationDisposition, ...], expected: VerificationDisposition
) -> None:
    assert compose_disposition(dispositions) is expected


def test_contract_hashes_are_stable_and_round_trip() -> None:
    case = ALL_CASES[0]
    assert case.content_hash == type(case).model_validate(case.model_dump()).content_hash


# ------------------------------------------------------------ pilot service


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ALL_CASES, ids=lambda item: item.case_id)
async def test_every_case_reaches_its_declared_disposition(case: object) -> None:
    """Each case ends where its contract says it will — accepted, or not.

    Sprint 21C.1 made this two-sided. Math, physics and logic declare
    `expected_disposition=PASS` and must be accepted, as before. The coding
    fixtures listed in `FALLIBLE_CODING_CASES` declare FAIL, because their
    registered single-edit baseline cannot solve them; those must be rejected.
    Asserting the declaration rather than allowing any outcome is what keeps
    the Gate L v2 condition 8b headroom measurable: a fallible fixture that
    silently starts passing fails here.
    """
    result = await DomainPilotService().run_case(case)  # type: ignore[arg-type]
    expected_pass = case.expected_disposition is VerificationDisposition.PASS  # type: ignore[attr-defined]
    accepted = result.run.status is DomainRunStatus.ACCEPTED
    assert accepted is expected_pass, [
        (item.capability, item.disposition, item.detail)
        for item in result.outcome.checks  # type: ignore[union-attr]
    ]
    assert result.derivation is not None and result.derivation.steps
    assert result.answer is not None


@pytest.mark.asyncio
async def test_the_coding_baseline_outcome_table_is_pinned() -> None:
    """Sprint 21C.1 exit evidence: the baseline outcome table, measured.

    Gate L v2 condition 8b needs coding cases whose registered baseline
    genuinely fails, and needs that to be a measurement rather than a claim.
    This test produces the whole table in one place and pins three things:
    which cases fail, how many, and that the count clears the plan's minimum
    with room to spare.

    It is deliberately easy to break. Two of the original fixtures did not fail
    at all — one carried a no-op patch, the other's "indirect" test name still
    contained the target function, so a substring match found it — and every
    surrounding gate stayed green while the headroom evidence was two cases
    thinner than it claimed.
    """
    coding = [case for case in ALL_CASES if case.domain is DomainKind.CODING]
    assert len(coding) >= 16, "the plan's seed-case floor for the fourth domain"

    rejected = set()
    for case in coding:
        result = await DomainPilotService().run_case(case)
        if not result.accepted:
            rejected.add(case.case_id)

    assert rejected == FALLIBLE_CODING_CASES, {
        "unexpectedly_passing": sorted(FALLIBLE_CODING_CASES - rejected),
        "unexpectedly_failing": sorted(rejected - FALLIBLE_CODING_CASES),
    }
    assert len(rejected) > MINIMUM_FALLIBLE_CODING_CASES, (
        "the fallible set must clear the plan's minimum with margin, so that one "
        "fixture drifting does not put Gate L v2 condition 8b on the boundary"
    )
    # Every problem type contributes headroom, not just the repair families.
    by_type = {case.problem_type for case in coding if case.case_id in rejected}
    assert by_type == set(problem_types(DomainKind.CODING))


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ALL_CASES, ids=lambda item: item.case_id)
async def test_wrong_answers_are_rejected(case: object) -> None:
    result = await DomainPilotService().run_case(
        case,  # type: ignore[arg-type]
        candidate=wrong_answer_for(case),  # type: ignore[arg-type]
    )
    assert not result.accepted


@pytest.mark.asyncio
async def test_runs_are_deterministic_and_replayable() -> None:
    case = ALL_CASES[0]
    first = await DomainPilotService().run_case(case)
    second = await DomainPilotService().run_case(case)
    assert first.run.content_hash == second.run.content_hash
    assert first.outcome.content_hash == second.outcome.content_hash  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_evidence_is_append_only() -> None:
    repository = InMemoryDomainRepository()
    service = DomainPilotService(repository)
    result = await service.run_case(ALL_CASES[0])
    from cognitive_os.domains.service import DomainPilotResult

    tampered = DomainPilotResult(
        result.run.model_copy(update={"case_id": "tampered"}), None, None, None
    )
    with pytest.raises(DomainConflictError):
        await repository.record(tampered)


class _MemoryEventStore:
    """Minimal append-only stream, mirroring the Sprint 19 test stub."""

    def __init__(self) -> None:
        self.events: list[object] = []

    async def get_stream_version(self, stream_id: object) -> int | None:
        del stream_id
        return len(self.events) or None

    async def append(self, events: tuple[object, ...], *, expected_version: int) -> object:
        from types import SimpleNamespace

        assert expected_version == len(self.events)
        self.events.extend(events)
        return SimpleNamespace(current_stream_version=len(self.events))

    async def read_stream(self, stream_id: object) -> tuple[object, ...]:
        from types import SimpleNamespace

        # Filter by stream so a replay assertion cannot pass by accident.
        return tuple(
            SimpleNamespace(envelope=item)
            for item in self.events
            if getattr(item, "stream_id", stream_id) == stream_id
        )


@pytest.mark.asyncio
async def test_lifecycle_events_replay_in_order() -> None:
    from cognitive_os.events.domain_event_service import DomainEventService

    store = _MemoryEventStore()
    service = DomainPilotService(events=DomainEventService(store))
    result = await service.run_case(ALL_CASES[0])
    replayed = await DomainEventService(store).replay(result.run.run_id)
    assert [item.event_type for item in replayed] == [
        "domain.case_started",
        "domain.case_completed",
    ]
    assert all(item.domain == "mathematics" for item in replayed)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_failed_case_emits_a_failure_event() -> None:
    from cognitive_os.events.domain_event_service import DomainEventService

    store = _MemoryEventStore()
    service = DomainPilotService(events=DomainEventService(store))
    case = ALL_CASES[0]
    result = await service.run_case(case, candidate=wrong_answer_for(case))
    replayed = await DomainEventService(store).replay(result.run.run_id)
    assert [item.event_type for item in replayed] == [
        "domain.case_started",
        "domain.case_failed",
    ]


# ------------------------------------------------------------------ security


@pytest.mark.parametrize(
    "hostile",
    (
        "__import__('os').system('id')",
        "open('/etc/passwd').read()",
        "(1).__class__.__bases__",
        "eval('2+2')",
        "lambda: 1",
        "[i for i in range(10)]",
        "x if y else z",
        "globals()",
    ),
)
def test_python_source_never_parses_into_the_math_ast(hostile: str) -> None:
    with pytest.raises((UnsafeExpressionError, SyntaxError, ValueError)):
        parse_expression(hostile)


def test_pilot_package_imports_no_process_or_network_module() -> None:
    import ast
    import pathlib

    forbidden = {"subprocess", "os", "socket", "urllib", "http", "requests", "httpx", "shutil"}
    for path in pathlib.Path("src/cognitive_os/domains").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert not {a.name.split(".")[0] for a in node.names} & forbidden, path
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in forbidden, path


def test_mandatory_path_never_names_an_optional_extra() -> None:
    """Structural, so the result does not depend on what another test imported."""
    import ast
    import pathlib

    extras = {"sympy", "pint", "z3"}
    for path in pathlib.Path("src/cognitive_os/domains").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert not {a.name.split(".")[0] for a in node.names} & extras, path
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] not in extras, path


# ------------------------------------------------------------------ transfer


@pytest.mark.asyncio
async def test_skill_transfer_is_positive_with_every_control() -> None:
    _, result = await run_experiment(
        source_domain=DomainKind.MATHEMATICS,
        target_domain=DomainKind.PHYSICS,
        unrelated_domain=DomainKind.LOGIC,
        component_kind="skill",
        component_id="verification-driven-arithmetic-repair",
    )
    assert set(result.arms) == set(TransferArm)
    assert result.disposition is TransferDisposition.POSITIVE_TRANSFER
    assert result.target_quality_delta > 0
    assert not result.hard_gate_failures
    assert result.source_quality_delta >= 0
    assert result.unrelated_quality_delta >= 0
    assert result.limitations and result.uncertainty


@pytest.mark.asyncio
async def test_strategy_transfer_is_positive_with_every_control() -> None:
    _, result = await run_experiment(
        source_domain=DomainKind.MATHEMATICS,
        target_domain=DomainKind.LOGIC,
        unrelated_domain=DomainKind.PHYSICS,
        component_kind="strategy",
        component_id="decompose-compute-verify",
    )
    assert result.disposition is TransferDisposition.POSITIVE_TRANSFER
    assert result.target_quality_delta > 0
    assert not result.hard_gate_failures


@pytest.mark.asyncio
async def test_hard_gate_blocks_a_narrow_optimisation() -> None:
    _, result = await run_negative_transfer_experiment()
    assert result.hard_gate_failures
    assert result.disposition is TransferDisposition.NEGATIVE_TRANSFER


@pytest.mark.asyncio
async def test_transfer_results_are_replayable() -> None:
    _, first = await run_experiment()
    _, second = await run_experiment()
    assert first.disposition is second.disposition
    assert first.target_quality_delta == second.target_quality_delta


@pytest.mark.asyncio
async def test_transfer_result_rejects_a_missing_control_arm() -> None:
    from cognitive_os.domain.domains import TransferResult

    _, result = await run_experiment()
    partial = dict(result.arms)
    partial.pop(TransferArm.SOURCE_RETENTION)
    with pytest.raises(ValueError, match="missing control arms"):
        TransferResult(
            **{
                **result.model_dump(exclude={"content_hash", "arms"}),
                "arms": partial,
            }
        )


@pytest.mark.asyncio
async def test_positive_transfer_cannot_coexist_with_a_hard_gate() -> None:
    from cognitive_os.domain.domains import TransferResult

    _, result = await run_experiment()
    with pytest.raises(ValueError, match="hard gate"):
        TransferResult(
            **{
                **result.model_dump(exclude={"content_hash"}),
                "hard_gate_failures": ("source retention regressed",),
                "disposition": TransferDisposition.POSITIVE_TRANSFER,
            }
        )


# ---------------------------------------------------------------- governance


@pytest.mark.asyncio
@pytest.mark.parametrize("check", governance_checks())
async def test_governance_invariants_hold(check: str) -> None:
    assert await _GOVERNANCE[check]() is True


def test_case_coverage_spans_all_three_domains() -> None:
    for domain in DomainKind:
        assert len(domain_case_ids(domain)) >= 15
