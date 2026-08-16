"""S22D-W0: the four seals reproduce, and the readings they freeze are not decorative.

Every later 22D wave is bound to these records by hash, so what has to be true of them is
that they *are* what they claim.

*The enumeration is an enumeration.* §2.2(a) reads "no large external LLM" as a construction
over a named list, and 22A W4-F1's rule is that a coverage word is an enumeration with a test
asserting it. If the provider union grows a fifth adapter, this file fails — which is the
only mechanism that keeps the first exit true after W0 stops looking.

*Nothing has been measured.* `measured_values: 0` on the hundred and on the holdout alike, in
a sprint where four of five exits are read off one authored instrument.

*The escalation policy is fixed.* §3.2 names it as the place this sprint could cheat without
noticing, so its whole truth table is sealed and compared, not its prose description.

*The typed abstention is typed.* An outcome cannot carry both an abstention and an answer,
because "explicitly uncertain" collapses into prose-matching the moment it can.

*The refusals refuse.* A gate that has never refused anything is a gate nobody has tested
(22A W4-F2), so the external-provider refusal, the uncleared-weights refusal and the
missing-verifier refusal are each executed here rather than described.

*The slice can print more than one outcome.* 22C W4's lesson: a record whose verdict cannot
flip has verified nothing either way, so this drives the third §2.2(d) case to non-zero.

`recorded_at` and the seal over it are excluded from every reproduction comparison, so no
test here fails because a clock moved (22B W2-F1/F2).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPOSITORY / "scripts"))

from benchmark_22d import (  # noqa: E402
    ARMS,
    BENCHMARK_VERIFIER_IDS,
    EXTERNAL_PROVIDER_IDS,
    FACTUAL_OUTPUT_KINDS,
    FIXTURE_RUNTIME,
    OUTPUT_KINDS,
    ArmOutcome,
    BenchmarkVerifiersUnavailable,
    Citation,
    ExternalProviderRefused,
    canonical,
    escalate,
    readings_hash,
    refuse_external_providers,
    require_benchmark_verifiers,
    run_arm,
    verify_answer,
)
from holdout_22d import HOLDOUT_CASES, PROBE_CASE  # noqa: E402
from tasks_22d import (  # noqa: E402
    FIXTURE_ANSWERS,
    FIXTURE_SOURCES,
    FIXTURE_TASKS,
    MICROBENCHMARK_TASKS,
    manifest,
)

from cognitive_os.config.provider_config import ProviderAdapterConfig  # noqa: E402

PREFLIGHT = EVIDENCE / "sprint-22d-preflight.json"
SLICE = EVIDENCE / "sprint-22d-w0-slice.json"
HOLDOUT = EVIDENCE / "sprint-22d-holdout.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22d-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-22d-contracts.json"

_PHYSICS = pytest.mark.skipif(
    find_spec("pint") is None, reason="verification-physics extra is absent"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seal_recomputes(record: dict[str, Any]) -> bool:
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    digest = hashlib.sha256(canonical(body)).hexdigest()
    return digest == record["integrity_content_hash"]


@pytest.mark.parametrize("path", [PREFLIGHT, SLICE, HOLDOUT, PRE_REGISTRATION])
def test_every_w0_seal_is_over_its_own_body(path: Path) -> None:
    assert path.exists(), f"{path.name} was not published"
    assert _seal_recomputes(_load(path))


def test_the_external_provider_enumeration_matches_the_released_union() -> None:
    """22A W4-F1. A fifth adapter must break this file, not slip past the first exit."""
    members = ProviderAdapterConfig.__origin__.__args__  # type: ignore[attr-defined]
    derived = tuple(sorted(item.model_fields["provider_id"].default for item in members))
    assert derived == EXTERNAL_PROVIDER_IDS
    assert _load(PREFLIGHT)["provider_enumeration"]["enumeration_matches_the_union"]


def test_every_external_provider_is_refused_and_the_local_model_is_not() -> None:
    for provider_id in EXTERNAL_PROVIDER_IDS:
        with pytest.raises(ExternalProviderRefused):
            refuse_external_providers([provider_id])
    refuse_external_providers(["local-model-under-measurement"])


def test_uncleared_weights_are_refused() -> None:
    """§3.2: never substitute a 'temporary' model; unclear weights are unreleasable evidence."""
    with pytest.raises(RuntimeError, match="OperatorLicenseClearance"):
        FIXTURE_RUNTIME.require_cleared()


def test_the_model_licence_gate_blocks_with_a_named_owner() -> None:
    gate = _load(PREFLIGHT)["model_licence_gate"]
    if gate["concluded"]:
        pytest.skip("the gate owner has issued a model clearance since W0")
    assert gate["owner"]
    assert "W2 local model" in gate["blocks"]
    assert _load(PREFLIGHT)["w2_may_proceed"] is False


def test_nothing_has_been_measured() -> None:
    record = _load(PRE_REGISTRATION)
    assert record["microbenchmark"]["measured_values"] == 0
    assert record["holdout"]["measured_values"] == 0
    assert record["amendments_made_by_22d"] == 0
    assert _load(HOLDOUT)["measured_values"] == 0


def test_the_hundred_is_a_hundred_and_its_hashes_are_sealed() -> None:
    published, sealed = manifest(), _load(PRE_REGISTRATION)["microbenchmark"]
    assert published["task_count"] == 100
    assert published["manifest_hash"] == sealed["manifest_hash"]
    assert published["task_hashes"] == sealed["task_hashes"]


def test_every_frozen_task_uses_a_frozen_verifier_and_a_frozen_output_kind() -> None:
    for task in (*MICROBENCHMARK_TASKS, *FIXTURE_TASKS):
        assert task["verifier_id"] in BENCHMARK_VERIFIER_IDS
        assert task["output_kind"] in OUTPUT_KINDS
        assert (task["output_kind"] in FACTUAL_OUTPUT_KINDS) == (
            task["grounding_source"] is not None
        )


def test_the_factual_output_enumeration_is_exhaustive_and_sealed() -> None:
    """§2.2(d): the enumeration of what counts as a factual output is frozen and asserted."""
    factual = [
        str(task["task_id"])
        for task in MICROBENCHMARK_TASKS
        if task["output_kind"] in FACTUAL_OUTPUT_KINDS
    ]
    sealed = _load(CONTRACTS)["S22D-014"]
    assert sealed["factual_task_ids"] == factual
    assert sealed["factual_output_count"] == len(factual) == 30
    assert set(sealed["dispositions"]) == {
        "grounded",
        "typed_abstention",
        "ungrounded_assertion",
    }


@_PHYSICS
def test_every_frozen_task_is_decidable_by_its_registered_verifier() -> None:
    """**W0-F1.** Fifty of the hundred are undecidable without the physics extra.

    An answer the verifier cannot decide is a failure for every arm, by §2.2(b). A *verifier*
    that cannot start is an environment defect, and the difference is fifty tasks scoring
    zero for a reason no number in the record would have mentioned.
    """

    def expected(task: dict[str, Any]) -> Any:
        configuration = task["verifier_configuration"]
        match task["verifier_id"]:
            case "physics.unit_conversion":
                return {
                    "magnitude": configuration["expected_magnitude"],
                    "unit": configuration["target_unit"],
                }
            case "physics.quantity":
                return configuration["expected"]
            case "physics.dimension":
                return {"magnitude": "1", "unit": configuration["expected_unit"]}
            case _:
                return configuration["expected"]

    async def check() -> list[str]:
        undecided = []
        for task in (*MICROBENCHMARK_TASKS, *FIXTURE_TASKS):
            outcome = ArmOutcome(
                task_id=str(task["task_id"]),
                arm="local_model",
                answer=expected(task),
                abstained=False,
            )
            verified, undecidable = await verify_answer(task, outcome)
            if not verified or undecidable:
                undecided.append(str(task["task_id"]))
        return undecided

    assert asyncio.run(check()) == []


def test_a_missing_verifier_extra_is_a_refusal_rather_than_a_silent_undecidable() -> None:
    if find_spec("pint") is None:
        with pytest.raises(BenchmarkVerifiersUnavailable):
            require_benchmark_verifiers()
    else:
        assert require_benchmark_verifiers() == BENCHMARK_VERIFIER_IDS


def test_an_abstention_carries_no_answer_and_an_answer_is_not_an_abstention() -> None:
    with pytest.raises(ValueError, match="abstention carries no answer"):
        ArmOutcome(task_id="t", arm="local_model", answer="4", abstained=True)
    with pytest.raises(ValueError, match="must carry an answer"):
        ArmOutcome(task_id="t", arm="local_model", answer=None, abstained=False)


def test_the_escalation_policy_truth_table_is_the_one_that_was_sealed() -> None:
    """§3.2 and §2.3: not touched after the first measured number exists."""
    sealed = _load(CONTRACTS)["S22D-016"]["truth_table"]
    for row in sealed:
        outcome = ArmOutcome(
            task_id="_policy",
            arm="local_model",
            answer=None if row["abstained"] else "0",
            abstained=row["abstained"],
            citations=tuple(
                Citation(source_id="_", content_hash="0" * 64, start=0, end=1)
                for _ in range(row["grounded_spans"])
            ),
            answer_form_valid=row["answer_form_valid"],
        )
        assert escalate(outcome) is row["escalates"]
    assert set(_load(CONTRACTS)["S22D-016"]["signals"]) == {
        "abstained",
        "grounded_span_count",
        "answer_form_valid",
    }


def test_no_holdout_case_carries_its_tolerance_as_its_expected_answer() -> None:
    """**W0-F4.** The cheap guard on the slip that no decidability check can see.

    `{"expected": "0.005", "relative_tolerance": "0.005"}` is a well-formed configuration that
    passes when handed its own expectation, so an unwinnable case looks exactly like a winnable
    one. Expected answers are now computed from the withheld fact rather than typed beside it;
    this asserts the shape that mistake leaves behind, in case a later case is added by hand.
    """
    for case in (*HOLDOUT_CASES, PROBE_CASE):
        configuration = case["verifier_configuration"]
        assert configuration["expected"] != configuration["relative_tolerance"], case["case_id"]


def test_the_holdout_is_fresh_disjoint_and_its_arms_differ() -> None:
    record = _load(HOLDOUT)
    assert record["disjointness"]["disjoint"] is True
    assert record["arm_mechanism_probe"]["arms_are_mechanically_different"] is True
    assert record["arm_mechanism_probe"]["arm_a_refuses_rather_than_guessing"] is True
    assert record["arm_mechanism_probe"]["probe_is_outside_the_holdout"] is True
    assert str(PROBE_CASE["case_id"]) not in {str(case["case_id"]) for case in HOLDOUT_CASES}


@_PHYSICS
def test_the_slice_ran_four_arms_and_called_nothing_external_outside_the_teacher() -> None:
    record = _load(SLICE)
    assert record["arms_run"] == list(ARMS)
    assert record["external_calls_outside_the_teacher_arm"] == 0
    assert record["every_refusal_refused"] is True
    assert record["at_least_one_typed_abstention"] is True
    assert record["at_least_one_resolved_citation_walk"] is True
    assert record["arms_are_mechanically_different"] is True
    assert record["readings_hash"] == readings_hash()


@_PHYSICS
def test_an_arm_other_than_the_teacher_may_not_record_an_external_call() -> None:
    sources = {key: value.encode("utf-8") for key, value in FIXTURE_SOURCES.items()}

    def cheat(arm: str, task: dict[str, Any]) -> ArmOutcome:
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer="0",
            abstained=False,
            external_provider_calls=1,
        )

    with pytest.raises(ExternalProviderRefused):
        asyncio.run(run_arm("local_model", FIXTURE_TASKS[:1], cheat, sources))


@_PHYSICS
def test_the_third_disposition_can_be_non_zero_so_the_record_can_print_two_outcomes() -> None:
    """22C W4: a record that can only print one outcome has verified nothing either way.

    The sealed slice reads zero ungrounded assertions on the local arm. That is only evidence
    if an ungrounded local answer would have been counted, so this drives one.
    """
    record = _load(SLICE)
    assert record["ungrounded_assertions_by_arm"]["local_model"] == 0
    assert record["ungrounded_assertions_by_arm"]["no_memory"] > 0

    sources = {key: value.encode("utf-8") for key, value in FIXTURE_SOURCES.items()}
    factual = next(task for task in FIXTURE_TASKS if task["output_kind"] in FACTUAL_OUTPUT_KINDS)

    def ungrounded(arm: str, task: dict[str, Any]) -> ArmOutcome:
        answer = FIXTURE_ANSWERS[str(task["task_id"])]["local_model"]["answer"]
        return ArmOutcome(task_id=str(task["task_id"]), arm=arm, answer=answer, abstained=False)

    accounting = asyncio.run(run_arm("local_model", [factual], ungrounded, sources))
    assert accounting.ungrounded_assertions == 1
    assert accounting.verified == 1, "a correct answer can still be an ungrounded assertion"
