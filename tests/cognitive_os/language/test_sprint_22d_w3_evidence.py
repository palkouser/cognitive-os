"""S22D-W3: the fourth arm, the mixed workload, and the four exits read once.

W3 added no instrument. `run_arm` still owns verification, accounting, escalation and the walk;
the readers still refuse rather than repair; the retrieval predicate is the one S22D-200 priced
before any arm ran. What has to be true for this wave's numbers to mean anything:

*A citation was earned rather than attached.* The frozen §2.2(d) reading asks only that the
released walk resolve the cited bytes — which a runner could satisfy by stapling the retrieved
span onto whatever the model said, producing a hundred resolvable citations that support
nothing. That loophole is asserted here as executable evidence, and so is the stricter rule W3
actually ran.

*The escalation policy was executed as frozen, including where it is wrong.* `escalate` reads
three runtime signals and one of them is the grounding-span count — applied, as written, to the
seventy closed-form computations the grounding exit never reads. That is W3-F1, and it is
asserted rather than described, because a policy relaxed after a measured number exists is a
number met by moving what the number reads.

*Nothing frozen moved.* The readings hash still matches the pre-registration, `ARMS` is still
the four the allocation named, and the mixed workload is scored by the same runner under a name
of its own rather than appended to them.
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
    FACTUAL_OUTPUT_KINDS,
    MINIMUM_COST_REDUCTION_PERCENT,
    MINIMUM_GROUNDED_SPANS,
    MINIMUM_LOCAL_SUCCESS_PERCENT,
    MINIMUM_MARGIN_POINTS,
    MIXED_WORKLOAD,
    NON_INFERIORITY_MARGIN_POINTS,
    ArmOutcome,
    Citation,
    ExternalProviderRefused,
    canonical,
    disposition,
    escalate,
    readings_hash,
    run_arm,
    walk_answer_citations,
)
from tasks_22d import MICROBENCHMARK_TASKS  # noqa: E402
from w3_22d import grounded_in  # noqa: E402

LOCAL = EVIDENCE / "sprint-22d-w3-local-model.json"
MIXED = EVIDENCE / "sprint-22d-w3-mixed-workload.json"
EXITS = EVIDENCE / "sprint-22d-w3-exits.json"
COVERAGE = EVIDENCE / "sprint-22d-w2-retrieval-coverage.json"
TEACHER = EVIDENCE / "sprint-22d-w2-external-teacher.json"
RETRIEVAL = EVIDENCE / "sprint-22d-w2-retrieval-only.json"
NO_MEMORY = EVIDENCE / "sprint-22d-w2-no-memory.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22d-pre-registration.json"

W3_RECORDS = (LOCAL, MIXED, EXITS)

#: The physics verifiers need an optional extra. Anything that drives `run_arm` — which
#: requires the whole registered verifier set before it scores a single task — skips where it
#: is absent, and every sealed record is asserted unconditionally. **W2-F5**, which cost this
#: sprint two red CI runs: a portability check must reproduce the lane, not resemble it.
_NEEDS_PHYSICS = pytest.mark.skipif(
    find_spec("pint") is None, reason="verification-physics extra is absent"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sealed(path: Path) -> bool:
    stored = _load(path)
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    return hashlib.sha256(canonical(body)).hexdigest() == stored["integrity_content_hash"]


# ---------------------------------------------------------------------------
# The records exist, are sealed, and measure the frozen hundred
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", W3_RECORDS, ids=lambda item: item.name)
def test_every_w3_record_is_sealed(path: Path) -> None:
    assert path.exists(), f"{path.name} is absent"
    assert _sealed(path), f"{path.name} does not rebuild its own integrity hash"


@pytest.mark.parametrize("path", (LOCAL, MIXED), ids=lambda item: item.name)
def test_each_measured_record_covers_the_whole_hundred(path: Path) -> None:
    stored = _load(path)
    assert stored["tasks"] == len(MICROBENCHMARK_TASKS) == 100
    assert stored["measured_values"] == 100
    assert stored["accounting"]["tasks"] == 100


def test_the_local_arm_is_the_fourth_arm_and_the_workload_is_not_a_fifth() -> None:
    assert _load(LOCAL)["arm"] == "local_model"
    assert _load(MIXED)["workload"] == MIXED_WORKLOAD
    # §2.2 freezes `arms` as four and the pre-registration hashes that reading. A workload
    # appended to this tuple would have changed the hash and silently amended the plan.
    assert ARMS == ("no_memory", "retrieval_only", "external_teacher", "local_model")
    assert MIXED_WORKLOAD not in ARMS


def test_no_measured_number_moved_a_frozen_reading() -> None:
    assert _sealed(PRE_REGISTRATION)
    assert readings_hash() == _load(PRE_REGISTRATION)["readings_hash"]


# ---------------------------------------------------------------------------
# §2.2(a). The construction, not an audit
# ---------------------------------------------------------------------------


def test_the_local_microbenchmark_called_no_external_provider() -> None:
    assert _load(LOCAL)["accounting"]["external_provider_calls"] == 0
    assert _load(EXITS)["exits"]["a"]["met"] is True


@_NEEDS_PHYSICS
def test_the_runner_still_refuses_an_external_call_from_the_local_arm() -> None:
    """The refusal executed, not described. A gate that has never refused is untested."""

    def answerer(arm: str, task: Any) -> ArmOutcome:
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer="1",
            abstained=False,
            external_provider_calls=1,
        )

    with pytest.raises(ExternalProviderRefused):
        asyncio.run(run_arm("local_model", MICROBENCHMARK_TASKS[:1], answerer, {}))


@_NEEDS_PHYSICS
def test_the_runner_permits_the_external_call_the_mixed_workload_is_made_of() -> None:
    """The same seam, from the other side: the composition is *defined* by escalating."""

    def answerer(arm: str, task: Any) -> ArmOutcome:
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer="1",
            abstained=False,
            external_provider_calls=1,
        )

    # A numeric task on purpose: this asserts the seam, not the verifier's tolerance for a
    # made-up answer shape, and `mathematical_expression` is the one form a bare string fits.
    numeric = next(
        task for task in MICROBENCHMARK_TASKS if task["subject_type"] == "mathematical_expression"
    )
    accounting = asyncio.run(run_arm(MIXED_WORKLOAD, (numeric,), answerer, {}))
    assert accounting.external_provider_calls == 1


def test_the_runner_refuses_a_workload_it_does_not_know() -> None:
    with pytest.raises(ValueError, match="unknown arm"):
        asyncio.run(run_arm("local_model_v2", MICROBENCHMARK_TASKS[:1], lambda *_: None, {}))


# ---------------------------------------------------------------------------
# The retrieval predicate, unwidened
# ---------------------------------------------------------------------------


def test_the_layer_offered_exactly_what_it_was_priced_to_offer() -> None:
    """S22D-200 priced the ceiling before any arm ran; the arm met it and did not exceed it."""
    priced = {item["task_id"] for item in _load(COVERAGE)["servable"]}
    offered = {
        item["task_id"]
        for item in _load(LOCAL)["retrieval"]["per_task"]
        if item["layer_offered_a_fact"]
    }
    assert offered == priced
    assert _load(LOCAL)["retrieval"]["tasks_the_layer_offered_a_fact_for"] == len(priced)


def test_the_retrieval_log_covers_every_task_exactly_once() -> None:
    log = _load(LOCAL)["retrieval"]["per_task"]
    assert len(log) == 100
    assert len({item["task_id"] for item in log}) == 100


# ---------------------------------------------------------------------------
# A citation is earned, and the loophole that would have made it free
# ---------------------------------------------------------------------------


def test_the_grounding_rule_reads_the_value_and_not_the_shape() -> None:
    fact = {"value": "12.01", "unit": "amu"}
    assert grounded_in("12.01", fact, b"12.01") is True
    # The same claim written with a trailing zero is the same number, and the rule compares
    # numbers rather than strings so that a formatting difference is not a grounding failure.
    assert grounded_in("12.010", fact, b"12.01") is True
    assert grounded_in("12.011", fact, b"12.01") is False
    assert grounded_in("about twelve", fact, b"12.01") is False
    assert grounded_in(None, fact, b"12.01") is False


def test_the_grounding_rule_refuses_a_span_that_does_not_carry_the_value() -> None:
    """The second check, and the one that makes the citation mean something.

    A right answer cited to bytes that do not contain it is a citation that resolves and
    supports nothing — which is exactly the trivial pass §2.2(d) as frozen would have allowed.
    """
    assert grounded_in("12.01", {"value": "12.01", "unit": "amu"}, b"9.80") is False


def test_a_right_magnitude_under_a_wrong_unit_is_not_grounded() -> None:
    fact = {"value": "9.80", "unit": "m/s2"}
    assert grounded_in({"magnitude": "9.80", "unit": "m/s2"}, fact, b"9.80") is True
    assert grounded_in({"magnitude": "9.80", "unit": "ft/s2"}, fact, b"9.80") is False


def test_stapling_a_resolvable_span_would_have_passed_the_frozen_reading() -> None:
    """**W3-F2 as executable evidence.** The exit as written cannot tell support from bytes.

    This constructs the cheat W3 refused: an answer with nothing to do with the cited span,
    carrying a citation whose bytes load and hash exactly. The released walk resolves it and the
    released disposition calls it grounded. Nothing here is broken — the walk does what it says
    — but the exit sentence stops at 'the walk resolves', so the stricter rule is the runner's
    to impose and the record has to say it did.
    """
    source = b"The average atomic mass of carbon is 12.01 amu."
    span = source[4:11]
    outcome = ArmOutcome(
        task_id="s22d-fact-05",
        arm="local_model",
        answer="41.9",
        abstained=False,
        citations=(
            Citation(
                source_id="s",
                content_hash=hashlib.sha256(span).hexdigest(),
                start=4,
                end=11,
            ),
        ),
    )
    walk = walk_answer_citations(outcome, {"s": source})
    task = {"output_kind": "declarative_fact"}
    assert walk["all_citations_resolve"] is True
    assert disposition(task, outcome, walk) == "grounded"
    # And the rule W3 ran refuses the same answer.
    assert grounded_in("41.9", {"value": "12.01", "unit": "amu"}, span) is False


def test_every_grounded_output_rested_on_its_span() -> None:
    """The record's two counts are the same count, so a citation cannot appear from elsewhere."""
    stored = _load(LOCAL)
    rested = [item for item in stored["retrieval"]["per_task"] if item["answer_rests_on_the_span"]]
    assert stored["retrieval"]["tasks_whose_answer_rested_on_the_span"] == len(rested)
    assert stored["accounting"]["grounded"] == len(rested)
    assert all(
        MICROBENCHMARK_TASKS[
            [str(task["task_id"]) for task in MICROBENCHMARK_TASKS].index(item["task_id"])
        ]["output_kind"]
        in FACTUAL_OUTPUT_KINDS
        for item in rested
    )


# ---------------------------------------------------------------------------
# The escalation policy, executed as frozen
# ---------------------------------------------------------------------------


def test_the_escalation_policy_is_the_one_w0_froze() -> None:
    stored = _load(MIXED)["escalation"]
    assert stored["frozen_in"] == "W0, before any measured number existed"
    assert "grounded_span_count < MINIMUM_GROUNDED_SPANS" in stored["policy"]
    assert MINIMUM_GROUNDED_SPANS == 1


def test_every_escalation_follows_from_the_policy_and_nothing_else() -> None:
    """Recomputed from the per-task signals, so the decision cannot have been taken elsewhere."""
    for item in _load(MIXED)["escalation"]["per_task"]:
        expected = (
            item["local_abstained"]
            or item["local_grounded_spans"] < MINIMUM_GROUNDED_SPANS
            or not item["local_answer_form_valid"]
        )
        assert item["escalated"] is bool(expected), item["task_id"]
        assert item["answered_by"] == ("external_teacher" if expected else "local_model")


def test_the_policy_escalates_output_kinds_the_grounding_exit_never_reads() -> None:
    """**W3-F1.** A closed-form computation has no source to rest on and cannot be grounded.

    `escalate` reads the grounding-span count without asking what kind of output it is, so every
    arithmetic task escalates for lacking a citation §2.2(d) never wanted from it. It ran as
    frozen: §2.3 forbids tuning the escalation threshold after a measured number exists, and
    this is what that costs.
    """
    escalated = {
        item["task_id"] for item in _load(MIXED)["escalation"]["per_task"] if item["escalated"]
    }
    closed_form = {
        str(task["task_id"])
        for task in MICROBENCHMARK_TASKS
        if task["output_kind"] not in FACTUAL_OUTPUT_KINDS
    }
    assert closed_form <= escalated
    assert _load(MIXED)["escalation"]["escalated_by_output_kind"]["closed_form_computation"] == len(
        closed_form
    )


def test_escalate_is_pure_and_reads_three_signals() -> None:
    grounded = ArmOutcome(
        task_id="t",
        arm="local_model",
        answer="1",
        abstained=False,
        citations=(Citation(source_id="s", content_hash="x", start=0, end=1),),
    )
    assert escalate(grounded) is False
    assert escalate(ArmOutcome(task_id="t", arm="local_model", answer=None, abstained=True)) is True
    assert (
        escalate(
            ArmOutcome(
                task_id="t",
                arm="local_model",
                answer="1",
                abstained=False,
                citations=grounded.citations,
                answer_form_valid=False,
            )
        )
        is True
    )


# ---------------------------------------------------------------------------
# The accounting, one definition applied to both sides
# ---------------------------------------------------------------------------


def test_the_mixed_workload_charges_the_local_call_it_made_and_did_not_keep() -> None:
    """A workload billing only the answer it used would report a saving it did not make."""
    mixed = _load(MIXED)["accounting"]
    local = _load(LOCAL)["accounting"]
    assert mixed["local_model_calls"] == local["local_model_calls"] == 100
    assert mixed["local_compute_seconds"] > 0
    assert mixed["external_provider_calls"] > 0


def test_the_exits_are_read_from_sealed_records_only() -> None:
    stored = _load(EXITS)
    assert stored["read_once"] is True
    assert set(stored["sources"]) == {
        LOCAL.name,
        MIXED.name,
        TEACHER.name,
        NO_MEMORY.name,
        RETRIEVAL.name,
    }


def test_exit_b_reads_the_margin_the_allocation_named() -> None:
    exit_b = _load(EXITS)["exits"]["b"]
    local = _load(LOCAL)["accounting"]["verified_percent"]
    retrieval = _load(RETRIEVAL)["accounting"]["verified_percent"]
    assert exit_b["local_model_verified_percent"] == local
    assert exit_b["retrieval_only_verified_percent"] == retrieval
    assert exit_b["margin_points"] == round(local - retrieval, 4)
    assert exit_b["minimum_local_success_percent"] == MINIMUM_LOCAL_SUCCESS_PERCENT
    assert exit_b["minimum_margin_points"] == MINIMUM_MARGIN_POINTS
    assert exit_b["met"] is bool(
        local >= MINIMUM_LOCAL_SUCCESS_PERCENT
        and round(local - retrieval, 4) >= MINIMUM_MARGIN_POINTS
    )


def test_exit_b_reports_the_layer_contribution_beside_the_one_it_reads() -> None:
    """**W2-F3, carried.** local minus retrieval isolates the model; local minus no_memory the
    layer. The allocation reads the first, so the second is reported rather than substituted."""
    exit_b = _load(EXITS)["exits"]["b"]
    assert exit_b["layer_contribution_points"] == round(
        _load(LOCAL)["accounting"]["verified_percent"]
        - _load(NO_MEMORY)["accounting"]["verified_percent"],
        4,
    )


def test_exit_c_reads_both_quantities_separately() -> None:
    """So a reduction cannot be claimed on whichever of the two moved further."""
    exit_c = _load(EXITS)["exits"]["c"]
    teacher = _load(TEACHER)["accounting"]
    mixed = _load(MIXED)["accounting"]
    assert exit_c["external_provider_calls"]["baseline"] == teacher["external_provider_calls"]
    assert exit_c["accounted_cost_units"]["baseline"] == teacher["accounted_cost_units"]
    assert exit_c["external_provider_calls"]["mixed"] == mixed["external_provider_calls"]
    assert exit_c["accounted_cost_units"]["mixed"] == mixed["accounted_cost_units"]
    assert exit_c["met"] is bool(
        exit_c["external_provider_calls"]["reduction_percent"] >= MINIMUM_COST_REDUCTION_PERCENT
        and exit_c["accounted_cost_units"]["reduction_percent"] >= MINIMUM_COST_REDUCTION_PERCENT
        and exit_c["non_inferiority"]["met"]
    )


def test_the_non_inferiority_margin_is_the_one_frozen_before_any_arm_ran() -> None:
    non_inferiority = _load(EXITS)["exits"]["c"]["non_inferiority"]
    assert non_inferiority["margin_points"] == NON_INFERIORITY_MARGIN_POINTS == 3.0
    assert non_inferiority["absolute_drop_points"] == round(
        _load(TEACHER)["accounting"]["verified_percent"]
        - _load(MIXED)["accounting"]["verified_percent"],
        4,
    )
    assert non_inferiority["met"] is bool(
        non_inferiority["absolute_drop_points"] <= NON_INFERIORITY_MARGIN_POINTS
    )


def test_the_local_runtime_repeated_itself_on_every_identical_prompt() -> None:
    """Ninety-six byte-identical prompts, same weights, same seed, twice — and the same answers.

    Had these diverged, the difference could not have been the layer, the prompt or the model,
    and every other number in this wave would be a single sample rather than a measurement.
    """
    local = _load(EXITS)["stability"]["the_local_runtime"]
    assert local["tasks_compared"] == 96
    assert local["divergent_tasks"] == 0
    assert local["repeated_itself"] is True


def test_the_external_baseline_did_not_repeat_itself() -> None:
    """**W3-F3.** The mixed workload is an accidental second run of the baseline, and it moved.

    Every escalated task re-asked the teacher the prompt W2 already asked it, through the same
    provider. Twelve of ninety-six verdicts changed. The non-inferiority margin is three points
    and is read against one run of that baseline.
    """
    external = _load(EXITS)["stability"]["the_external_teacher"]
    assert external["tasks_compared"] == 96
    assert external["identical_prompts"] is True
    assert external["divergent_tasks"] > 0
    assert external["repeated_itself"] is False
    assert external["net_movement_points"] == (
        external["verified_here"] - external["verified_there"]
    )


def test_the_baseline_drift_is_recorded_beside_the_exit_and_not_folded_into_it() -> None:
    """§2.3 forbids amending the margin after a measured number exists, so the exit reads as
    frozen and the qualification lives next to it. An exit quietly widened by its own noise is
    the failure mode the whole pre-registration exists to prevent."""
    stored = _load(EXITS)
    non_inferiority = stored["exits"]["c"]["non_inferiority"]
    assert non_inferiority["met"] is bool(
        non_inferiority["absolute_drop_points"] <= non_inferiority["margin_points"]
    )
    assert stored["stability"]["reading"] == "observation"
    assert (
        "recorded beside it rather than folded into it"
        in (
            stored["stability"]["the_external_teacher"][
                "why_this_qualifies_the_non_inferiority_reading"
            ]
        )
    )


def test_exit_d_is_read_over_the_two_systems_this_sprint_proposes() -> None:
    exit_d = _load(EXITS)["exits"]["d"]
    assert exit_d["read_over"] == ["local_model", MIXED_WORKLOAD]
    assert (
        exit_d["ungrounded_assertions"]["local_model"]
        == (_load(LOCAL)["accounting"]["ungrounded_assertions"])
    )
    assert (
        exit_d["ungrounded_assertions"][MIXED_WORKLOAD]
        == (_load(MIXED)["accounting"]["ungrounded_assertions"])
    )
    assert exit_d["met"] is bool(
        exit_d["ungrounded_assertions"]["local_model"] == 0
        and exit_d["ungrounded_assertions"][MIXED_WORKLOAD] == 0
    )


def test_every_factual_output_falls_in_exactly_one_of_the_three_cases() -> None:
    """§2.2(d)'s binary plus the third case it counts. Exhaustive, per arm, over the thirty."""
    factual = [task for task in MICROBENCHMARK_TASKS if task["output_kind"] in FACTUAL_OUTPUT_KINDS]
    assert len(factual) == 30
    for path in (LOCAL, MIXED):
        stored = _load(path)["accounting"]
        cases = sum(
            1
            for row in stored["per_task"].values()
            if row["disposition"] in {"grounded", "typed_abstention", "ungrounded_assertion"}
        )
        assert cases == len(factual), path.name


def test_exit_e_is_left_where_the_wave_table_puts_it() -> None:
    assert "W4" in _load(EXITS)["exit_e_is_not_read_here"]
    assert set(_load(EXITS)["exits_read_here"]) == {"a", "b", "c", "d"}


def test_the_outcome_word_follows_from_the_four_readings() -> None:
    stored = _load(EXITS)
    met = [key for key, value in stored["exits"].items() if value["met"]]
    assert stored["exits_met"] == met
    assert stored["outcome"] == ("pass" if len(met) == 4 else "typed_negative")


def test_undecidable_tasks_are_counted_as_failures_and_reported() -> None:
    exit_b = _load(EXITS)["exits"]["b"]
    assert exit_b["undecidable_counts_as"].startswith("failure for every arm")
    for arm, path in (("local_model", LOCAL), (MIXED_WORKLOAD, MIXED)):
        stored = _load(path)["accounting"]
        assert exit_b["undecidable_tasks"][arm] == stored["undecidable"]
        # A task the verifier could not decide never counted as a pass anywhere.
        assert stored["verified"] + stored["undecidable"] <= 100
