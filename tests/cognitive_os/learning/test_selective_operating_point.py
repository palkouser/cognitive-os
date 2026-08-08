"""S21D4-021: the zero-error operating point on hand-computed vectors.

Every vector below is small enough to check by eye, which is the point: a threshold rule whose
correctness has to be taken on trust is a threshold rule that can quietly move.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_os.learning.selective_operating_point import (
    AMENDED_DERIVATION_STEP,
    DERIVATION_RULE,
    SEALED_DERIVATION_STEP,
    OperatingPointError,
    OperatingPointV4,
    ScoredDecision,
    derive_zero_error_point,
    zero_error_upper_bound,
)

DERIVED_AT = datetime(2026, 8, 6, 12, tzinfo=UTC)
SOURCE = "a" * 64
EVIDENCE = Path(__file__).resolve().parents[3] / "docs/sprints/sprint-21/evidence"
AMENDMENT = EVIDENCE / "sprint-21d4-contracts-amendment-1.json"


def _decisions(*rows: tuple[str, bool, bool]) -> tuple[ScoredDecision, ...]:
    return tuple(
        ScoredDecision(
            decision_id=f"d{index}",
            feature_hash=f"v{index}",
            score=Decimal(score),
            answered=answered,
            correct=correct,
        )
        for index, (score, answered, correct) in enumerate(rows)
    )


def _derive(decisions: tuple[ScoredDecision, ...], **overrides: object) -> OperatingPointV4:
    fields: dict[str, object] = {
        "split": "calibration",
        "calibration_source_hash": SOURCE,
        "derived_at": DERIVED_AT,
    }
    fields.update(overrides)
    return derive_zero_error_point(decisions, **fields)  # type: ignore[arg-type]


def test_the_point_admits_everything_above_the_highest_wrong_answer() -> None:
    """Scores 0.9 0.8 0.7 correct, 0.6 wrong, 0.5 correct. The bar is 0.6, three admitted."""
    point = _derive(
        _decisions(
            ("0.9", True, True),
            ("0.8", True, True),
            ("0.7", True, True),
            ("0.6", True, False),
            ("0.5", True, True),
        )
    )
    assert point.zero_error_point_exists
    assert point.threshold == "0.6"
    assert point.admitted_decisions == 3
    assert point.errors_above_threshold == 0
    assert point.coverage == "0.6"  # three of five independent decisions
    # Zero errors in three decisions bounds the true rate at 63%, which is the number D4 exists
    # to make small: the same rule over a hundred admitted decisions bounds it at 3%.
    assert point.zero_error_upper_bound_95 == "0.631597"


def test_a_wrong_answer_tied_with_correct_ones_excludes_the_whole_tie() -> None:
    """Three decisions at 0.7, one of them wrong. Admitting any of them admits an error."""
    point = _derive(
        _decisions(
            ("0.9", True, True),
            ("0.7", True, True),
            ("0.7", True, False),
            ("0.7", True, True),
        )
    )
    assert point.threshold == "0.7"
    assert point.admitted_decisions == 1
    assert point.coverage == "0.25"


def test_all_correct_admits_every_answered_decision() -> None:
    """No answered decision is wrong, so the rule names no score and the record says so.

    The first assertion here was `threshold is None or zero_error_point_exists`, which passes
    on either branch and passed while `threshold` held the string `"None"`. S21D4-033 hit that
    on the vertical slice; the assertion is now the one that would have failed.
    """
    point = _derive(_decisions(("0.9", True, True), ("0.5", True, True), ("0.1", False, False)))
    assert point.zero_error_point_exists
    assert point.threshold is None
    assert point.every_answered_decision_was_correct
    assert point.admitted_decisions == 2
    assert point.coverage == str(Decimal(2) / Decimal(3))
    assert point.zero_error_upper_bound_95 == "0.776393"


def test_a_point_without_a_threshold_must_say_why_it_has_none() -> None:
    """`threshold=None` alone cannot tell "nothing was wrong" from "nothing was admitted"."""
    point = _derive(_decisions(("0.9", True, True), ("0.5", True, True), ("0.1", False, False)))
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["every_answered_decision_was_correct"] = False
    with pytest.raises(ValidationError, match="names its threshold"):
        OperatingPointV4.model_validate(body)


def test_a_zero_error_point_that_names_a_threshold_it_did_not_derive_is_refused() -> None:
    point = _derive(_decisions(("0.9", True, True), ("0.5", True, True), ("0.1", False, False)))
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["threshold"] = "0.4"
    with pytest.raises(ValidationError, match="names no threshold"):
        OperatingPointV4.model_validate(body)


def test_all_wrong_derives_no_point_at_all() -> None:
    point = _derive(_decisions(("0.9", True, False), ("0.5", True, False)))
    assert not point.zero_error_point_exists
    assert point.threshold is None
    assert point.coverage is None
    assert point.zero_error_upper_bound_95 is None
    assert point.admitted_decisions == 0


def test_an_all_abstaining_set_derives_no_point_either() -> None:
    point = _derive(_decisions(("0.9", False, False), ("0.5", False, False)))
    assert not point.zero_error_point_exists
    assert point.census.independent_decisions == 2


def test_an_empty_set_derives_no_point_and_no_bound() -> None:
    point = _derive(())
    assert not point.zero_error_point_exists
    assert point.census.nominal_decisions == 0


def test_only_the_calibration_split_may_derive_a_threshold() -> None:
    for split in ("final_a", "final_b", "promotion", "metamorphic", "canary"):
        with pytest.raises(OperatingPointError, match="calibration split only"):
            _derive(_decisions(("0.9", True, True)), split=split)


def test_replicated_decisions_are_refused_rather_than_deduplicated() -> None:
    replicated = tuple(
        ScoredDecision(
            decision_id=f"d{index}",
            feature_hash="one-and-the-same-vector",
            score=Decimal("0.9"),
            answered=True,
            correct=True,
        )
        for index in range(6)
    )
    with pytest.raises(OperatingPointError, match="repeat another's fitted vector"):
        _derive(replicated)


def test_a_second_different_derivation_is_refused() -> None:
    first = _derive(_decisions(("0.9", True, True), ("0.6", True, False)))
    with pytest.raises(OperatingPointError, match="second, different operating point"):
        _derive(
            _decisions(("0.9", True, True), ("0.6", True, True)),
            previous=first,
        )


def test_re_deriving_the_same_point_after_a_restart_is_allowed_and_identical() -> None:
    """The single-shot rule refuses a different answer, not a reproduction of the same one."""
    rows = _decisions(("0.9", True, True), ("0.8", True, True), ("0.6", True, False))
    first = _derive(rows)
    again = _derive(rows, derived_at=datetime(2027, 1, 1, tzinfo=UTC), previous=first)
    assert again.derivation_hash == first.derivation_hash
    assert (again.threshold, again.coverage, again.admitted_decisions) == (
        first.threshold,
        first.coverage,
        first.admitted_decisions,
    )
    assert again.derived_at != first.derived_at


def test_the_derivation_hash_moves_when_the_calibration_source_does() -> None:
    rows = _decisions(("0.9", True, True), ("0.6", True, False))
    assert (
        _derive(rows).derivation_hash
        != _derive(rows, calibration_source_hash="b" * 64).derivation_hash
    )


def test_the_bound_is_the_one_the_contracts_froze() -> None:
    """The four values S21D4-014 declared, recomputed rather than restated."""
    assert {n: round(zero_error_upper_bound(n), 6) for n in (20, 60, 100, 300)} == {
        20: 0.139108,
        60: 0.048703,
        100: 0.029513,
        300: 0.009936,
    }
    with pytest.raises(ValueError, match="bounds nothing"):
        zero_error_upper_bound(0)


def test_a_stored_point_cannot_be_edited_into_admitting_an_error() -> None:
    point = _derive(_decisions(("0.9", True, True), ("0.6", True, False)))
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["errors_above_threshold"] = 1
    with pytest.raises(ValueError, match="admits no error"):
        OperatingPointV4.model_validate(body)


def test_stored_bytes_claiming_another_split_are_refused_too() -> None:
    point = _derive(_decisions(("0.9", True, True), ("0.6", True, False)))
    body = point.model_dump(mode="json", exclude={"content_hash"})
    body["split"] = "final_a"
    with pytest.raises(ValueError, match="fitted to a holdout"):
        OperatingPointV4.model_validate(body)


def test_amendment_one_is_the_operative_derivation_step() -> None:
    """The contract record and this module must not drift: the amendment carries the digest."""
    amendment = json.loads(AMENDMENT.read_text())
    assert amendment["amends"]["contract"] == "selective_operating_point"
    assert amendment["amends"]["bytes_modified"] == 0
    assert amendment["defect"]["sealed_sentence"] == SEALED_DERIVATION_STEP
    assert amendment["amended_sentence"] == AMENDED_DERIVATION_STEP
    assert amendment["operative_rule"] == DERIVATION_RULE
    assert (
        amendment["operative_rule_sha256"]
        == hashlib.sha256(DERIVATION_RULE.encode("utf-8")).hexdigest()
    )
    assert AMENDED_DERIVATION_STEP in DERIVATION_RULE
    assert SEALED_DERIVATION_STEP not in DERIVATION_RULE


def test_amendment_one_predates_every_number_it_governs() -> None:
    chronology = json.loads(AMENDMENT.read_text())["chronology"]
    assert chronology["d4_threshold_derivations_at_amendment_time"] == 0
    assert chronology["d4_calibration_measurements_at_amendment_time"] == 0
    assert chronology["fresh_calibration_set_resolved"] is False


def test_the_amended_rule_is_the_one_the_derivation_actually_applies() -> None:
    """Lowest threshold with a clean admitted set, not the largest one that admits nothing."""
    rows = _decisions(("0.9", True, True), ("0.8", True, True), ("0.6", True, False))
    point = _derive(rows)
    assert point.derivation_rule == DERIVATION_RULE
    assert point.threshold == "0.6"
    assert point.admitted_decisions == 2  # not 0, which the sealed wording also permitted
