"""S22D-W2: the three baseline arms, and the four things that would have made them lie.

W2 replaced W0's simulated answerer with three real ones and left the runner alone. What has to
be true for the three numbers to mean anything:

*The comparator's ceiling was priced before it ran.* `retrieval_only` is model-free by design,
so what it can possibly answer is decided entirely by what Layer 1 holds. S22D-200 computed and
sealed that ceiling first — and the arm then answered exactly it, which is the difference
between a result and an explanation.

*Nothing was repaired.* Each arm is asked for a strict answer form and the reader refuses what
does not match, rather than extracting a number from a sentence. A lenient reader scores itself,
and by W3 nobody could separate the model's competence from a regular expression's generosity.

*Three failure modes are counted apart.* "The arm produced no readable answer", "the verifier
could not decide this answer" and "the provider never answered" are different facts. W0-F1 was
the second being reported as the third; this keeps all three separate.

*The teacher that failed is kept.* OpenRouter's free tier allows fifty requests a day and the
arm is a hundred tasks, so that run could not have completed — and its sealed record is the
evidence for why the route changed. A teacher swapped without it is a teacher swapped until the
number was liked.

The unit-notation defect (W2-F2) is asserted here as executable evidence rather than described:
the registered physics verifiers decide `m/s**2` and error on `m/s²`, and both arms that use a
language model lose roughly a dozen tasks to it.
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

from arms_22d import (  # noqa: E402
    EXTERNAL_ATTEMPTS,
    EXTERNAL_PROVIDER_ID,
    W2_ARMS,
    ArmRefused,
    _is_quota_exhausted,
    build_prompt,
    coverage,
    read_answer,
)
from benchmark_22d import (  # noqa: E402
    ABSTENTION_VALUE,
    ArmOutcome,
    ExternalProviderRefused,
    canonical,
    run_arm,
    verify_answer,
)
from tasks_22d import MICROBENCHMARK_TASKS  # noqa: E402

COVERAGE = EVIDENCE / "sprint-22d-w2-retrieval-coverage.json"
EXTERNAL = EVIDENCE / "sprint-22d-w2-external-teacher.json"
ABANDONED = EVIDENCE / "sprint-22d-w2-external-teacher-abandoned.json"
NO_MEMORY = EVIDENCE / "sprint-22d-w2-no-memory.json"
RETRIEVAL = EVIDENCE / "sprint-22d-w2-retrieval-only.json"
ARMS = (EXTERNAL, NO_MEMORY, RETRIEVAL)

#: The cleared PDFs live outside the repository. Anything that rebuilds the coverage from them
#: skips where they are absent; every sealed record is asserted unconditionally.
_SOURCES_PRESENT = (Path.home() / "Letöltések" / "chemistry-2e_-_WEB.pdf").exists()
_NEEDS_SOURCES = pytest.mark.skipif(
    not _SOURCES_PRESENT, reason="the rights-cleared sources are not on this host"
)
_NEEDS_PHYSICS = pytest.mark.skipif(
    find_spec("pint") is None, reason="verification-physics extra is absent"
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", [COVERAGE, EXTERNAL, ABANDONED, NO_MEMORY, RETRIEVAL])
def test_every_w2_seal_is_over_its_own_body(path: Path) -> None:
    record = _load(path)
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    assert hashlib.sha256(canonical(body)).hexdigest() == record["integrity_content_hash"]


# ---------------------------------------------------------------------------
# S22D-200. The comparator, priced before it ran
# ---------------------------------------------------------------------------


def test_the_comparator_ceiling_was_published_before_any_arm_ran() -> None:
    """22C W3-F1, and this sprint has already been caught breaking it once."""
    record = _load(COVERAGE)
    assert record["items"] == ["S22D-200"]
    assert record["measured_values"] == 0
    assert record["published_before"] == "S22D-201, S22D-202 and S22D-203"


def test_the_model_free_arm_answered_exactly_what_it_was_priced_to_answer() -> None:
    """The whole value of pricing first, in one assertion.

    Four tasks were declared reachable before the arm ran and four were verified. Had this
    been measured first and priced afterwards, the same number would have been a story about
    why four was the number to expect.
    """
    priced = _load(COVERAGE)
    measured = _load(RETRIEVAL)["accounting"]
    assert priced["tasks_the_layer_could_serve"] == 4
    assert measured["verified"] == 4
    assert measured["abstained"] == len(MICROBENCHMARK_TASKS) - 4


def test_the_alias_debt_is_recorded_with_the_movement_it_caused() -> None:
    """**W1-F3, paid.** Publishing the movement is what separates a debt from a massage."""
    entry = _load(COVERAGE)["one_alias_was_added_before_any_arm_ran"]
    assert entry["finding"] == "W1-F3"
    assert entry["resolves_to"] == "g"
    assert (entry["moved_servable_from"], entry["moved_servable_to"]) == (3, 4)


@_NEEDS_SOURCES
def test_the_coverage_rebuilds_from_the_sealed_layer() -> None:
    assert coverage()["integrity_content_hash"] == _load(COVERAGE)["integrity_content_hash"]


# ---------------------------------------------------------------------------
# The three arms, and what separates them
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", list(ARMS))
def test_every_arm_read_the_whole_frozen_hundred(path: Path) -> None:
    record = _load(path)
    assert record["tasks"] == len(MICROBENCHMARK_TASKS) == 100
    assert record["measured_values"] == 100
    assert record["accounting"]["tasks"] == 100


def test_only_the_external_arm_reached_a_network() -> None:
    """§2.2(a) as a construction. The other two arms recorded zero, and the runner enforces it."""
    assert _load(EXTERNAL)["accounting"]["external_provider_calls"] == 100
    assert _load(NO_MEMORY)["accounting"]["external_provider_calls"] == 0
    assert _load(RETRIEVAL)["accounting"]["external_provider_calls"] == 0


def test_the_runner_refuses_an_external_call_from_a_local_arm() -> None:
    """Executed rather than trusted: a gate nobody has watched refuse is untested (22A W4-F2)."""

    def cheating(arm: str, task: Any) -> ArmOutcome:
        return ArmOutcome(
            task_id=str(task["task_id"]),
            arm=arm,
            answer="1",
            abstained=False,
            external_provider_calls=1,
        )

    with pytest.raises(ExternalProviderRefused):
        asyncio.run(run_arm("no_memory", MICROBENCHMARK_TASKS[:1], cheating, {}))


def test_the_model_free_arm_grounded_everything_it_asserted() -> None:
    """It answers from a span or it abstains; there is no third thing for it to do."""
    accounting = _load(RETRIEVAL)["accounting"]
    assert accounting["grounded"] == accounting["verified"] == 4
    assert accounting["ungrounded_assertions"] == 0
    assert accounting["local_model_calls"] == 0


def test_neither_language_model_arm_ever_abstained() -> None:
    """The §2.2(d) reading these two baselines actually produce.

    Both were offered the typed abstention in the prompt and neither used it once in a hundred
    tasks, so every factual output they produced is an ungrounded assertion. The exit reads
    that count being zero, and W2 establishes that it starts at thirty.
    """
    for path in (EXTERNAL, NO_MEMORY):
        accounting = _load(path)["accounting"]
        assert accounting["abstained"] == 0
        assert accounting["ungrounded_assertions"] == 30
        assert accounting["grounded"] == 0


def test_the_teacher_is_the_bar_and_it_is_a_high_one() -> None:
    """87 against 66. W3's local arm must come within three points of the first number."""
    assert _load(EXTERNAL)["accounting"]["verified"] == 87
    assert _load(NO_MEMORY)["accounting"]["verified"] == 66


def test_the_local_arm_is_far_cheaper_in_tokens_than_the_teacher() -> None:
    """The quantity §2.2(c)'s reduction is read on, before W3 reads it."""
    external = _load(EXTERNAL)["accounting"]["output_tokens"]
    local = _load(NO_MEMORY)["accounting"]["output_tokens"]
    assert external > local * 10


# ---------------------------------------------------------------------------
# Three failure modes, kept apart
# ---------------------------------------------------------------------------


def test_malformed_answers_are_counted_apart_from_undecidable_ones() -> None:
    """W0-F1 generalised: an unreadable answer is not a verifier that could not decide."""
    for path in (EXTERNAL, NO_MEMORY):
        record = _load(path)
        assert record["malformed_answers"] == len(record["malformed_task_ids"])
        assert record["malformed_answers"] < record["accounting"]["undecidable"]


def test_the_reader_refuses_rather_than_repairs() -> None:
    """A reader that extracts a number from a sentence is scoring itself."""
    quantity = next(t for t in MICROBENCHMARK_TASKS if t["subject_type"] == "physical_quantity")
    answer, abstained, valid = read_answer(quantity, "about 3500 newtons, I think")
    assert valid is False and abstained is False
    assert answer == "about 3500 newtons, I think", "recorded as it arrived, not rewritten"
    shaped, _, ok = read_answer(quantity, "3500 N")
    assert ok is True and shaped == {"magnitude": "3500", "unit": "N"}


def test_the_typed_abstention_is_recognised_and_carries_no_answer() -> None:
    task = MICROBENCHMARK_TASKS[0]
    answer, abstained, valid = read_answer(task, ABSTENTION_VALUE)
    assert (answer, abstained, valid) == (None, True, True)
    assert ABSTENTION_VALUE in build_prompt(task), "an arm cannot emit what it was never offered"


# ---------------------------------------------------------------------------
# W2-F2. The instrument's unit notation, as executable evidence
# ---------------------------------------------------------------------------


@_NEEDS_PHYSICS
def test_the_registered_verifiers_decide_ascii_units_and_error_on_typographic_ones() -> None:
    """**W2-F2.** The finding, executed rather than asserted in prose.

    `9.8 m/s²` and `9.8 m/s**2` are the same answer. One is decided and the other is an error,
    and an error is counted as a failure for every arm — so a dozen tasks per model arm turn on
    typography rather than on physics. Worse than the lost points: an undecidable verdict hides
    whether the answer was right *or* wrong, in both directions.
    """
    task = next(t for t in MICROBENCHMARK_TASKS if str(t["task_id"]) == "s22d-quantity-02")

    async def decide(unit: str) -> tuple[bool, bool]:
        outcome = ArmOutcome(
            task_id=str(task["task_id"]),
            arm="no_memory",
            answer={"magnitude": "4", "unit": unit},
            abstained=False,
        )
        return await verify_answer(task, outcome)

    assert asyncio.run(decide("m/s**2")) == (True, False)
    assert asyncio.run(decide("m/s^2")) == (True, False)
    assert asyncio.run(decide("m/s²")) == (False, True), "undecidable, for a typographic reason"


def test_both_model_arms_lost_about_a_dozen_tasks_to_the_instrument() -> None:
    for path in (EXTERNAL, NO_MEMORY):
        assert 10 <= _load(path)["accounting"]["undecidable"] <= 15


# ---------------------------------------------------------------------------
# W2-F4. The abandoned teacher, kept as the reason for the swap
# ---------------------------------------------------------------------------


def test_the_abandoned_run_is_kept_and_is_not_the_baseline() -> None:
    """A route swapped without the evidence for the swap is a route swapped until it flattered."""
    abandoned = _load(ABANDONED)
    assert abandoned["arm"] == "external_teacher"
    assert abandoned["governance"]["tasks_that_exhausted_their_attempts"] == 68
    assert abandoned["accounting"]["external_provider_calls"] == 239
    # The record of *record* is the one that completed, and it is a different file.
    assert _load(EXTERNAL)["governance"]["tasks_that_exhausted_their_attempts"] == 0


def test_the_teacher_of_record_is_named_and_is_a_frozen_external_provider() -> None:
    """The enumeration did not widen: the teacher is one of W0's four, not a fifth."""
    from benchmark_22d import EXTERNAL_PROVIDER_IDS

    teacher = _load(EXTERNAL)["governance"]["teacher"]
    assert teacher["provider_id"] == EXTERNAL_PROVIDER_ID
    assert teacher["provider_id"] in EXTERNAL_PROVIDER_IDS


def test_a_spent_allowance_stops_the_arm_rather_than_being_retried() -> None:
    """**W2-F4.** A retry that cannot tell "try again" from "you have no budget left"
    turns a bounded failure into an exhausted quota — which is exactly what happened.
    """

    class Quota(Exception):
        status_code = 429

    class Capacity(Exception):
        status_code = 404

    assert _is_quota_exhausted(Quota()) is True
    assert _is_quota_exhausted(Capacity()) is False
    wrapped = RuntimeError("provider failed")
    wrapped.__cause__ = Quota()
    assert _is_quota_exhausted(wrapped) is True
    assert EXTERNAL_ATTEMPTS == 3


def test_every_attempt_was_counted_as_a_call() -> None:
    """The conservative direction: a bigger baseline makes §2.2(c)'s reduction harder."""
    abandoned = _load(ABANDONED)["governance"]
    calls = _load(ABANDONED)["accounting"]["external_provider_calls"]
    assert calls == abandoned["receipts"] + abandoned["failed_attempts"]


def test_w2_ran_three_arms_and_left_the_fourth_to_w3() -> None:
    assert set(W2_ARMS) == {"external_teacher", "no_memory", "retrieval_only"}
    assert "local_model" not in W2_ARMS


def test_the_arm_refuses_when_the_layer_it_retrieves_from_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import arms_22d

    monkeypatch.setattr(arms_22d, "ACQUISITION", tmp_path / "absent.json")
    with pytest.raises(ArmRefused, match="no layer to retrieve from"):
        arms_22d.retained_facts()
