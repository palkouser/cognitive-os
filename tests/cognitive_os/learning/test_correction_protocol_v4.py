"""S21D4-020: the counting rule, and the collapse that made it necessary.

The first test is the whole reason revision 4 exists. D3's grid reported 120 metamorphic
ranking decisions per setting; S21D4-001 recomputed that those were 20 decisions encoded six
times, because a semantics-preserving transformation produces the same fitted vector by
construction. The rest of the tests are about what a payload is then allowed to say.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from cognitive_os.learning.correction_protocol import (
    INDEPENDENT_DENOMINATOR,
    CorrectionDecisionSetV4,
    CorrectionEvaluationCountsV3,
    DecisionCensusV4,
    decision_census,
)

EVIDENCE = Path(__file__).resolve().parents[3] / "docs/sprints/sprint-21/evidence"


def _set(**overrides: object) -> CorrectionDecisionSetV4:
    fields: dict[str, object] = {
        "label": "calibration_clean",
        "census": DecisionCensusV4.from_feature_hashes([f"v{index}" for index in range(20)]),
        "answered_decisions": 19,
        "correct_decisions": 13,
        "confident_errors": 6,
        "changed_actions": 14,
    }
    fields.update(overrides)
    return CorrectionDecisionSetV4(**fields)  # type: ignore[arg-type]


def test_six_semantics_preserving_transformations_are_one_decision() -> None:
    """Twenty groups, six cases each, one fitted vector per group. D3's 120 was 20."""
    hashes = [f"group-{group}" for group in range(20) for _ in range(6)]
    nominal, independent, replicated = decision_census(hashes)
    assert (nominal, independent, replicated) == (120, 20, 100)

    census = DecisionCensusV4.from_feature_hashes(hashes)
    assert census.nominal_decisions == 120
    assert census.independent_decisions == 20
    assert census.replicated_decisions == 100
    assert census.rate_denominator == INDEPENDENT_DENOMINATOR


def test_a_census_that_does_not_add_up_is_refused() -> None:
    with pytest.raises(ValueError, match="nominal decisions must equal"):
        DecisionCensusV4(nominal_decisions=120, independent_decisions=20, replicated_decisions=99)


def test_a_payload_may_not_name_the_nominal_denominator() -> None:
    with pytest.raises(ValueError, match="replicated denominator"):
        DecisionCensusV4(
            nominal_decisions=20,
            independent_decisions=20,
            replicated_decisions=0,
            rate_denominator="nominal_decisions",
        )


def test_every_rate_is_taken_over_the_independent_denominator() -> None:
    """The numbers are D3's first setting, counted the way revision 4 counts."""
    measured = _set()
    assert measured.coverage == Decimal(19) / Decimal(20)
    assert measured.accuracy == Decimal(13) / Decimal(19)
    assert measured.confident_error_rate == Decimal(6) / Decimal(19)


def test_rates_over_an_empty_or_silent_set_are_null_rather_than_zero() -> None:
    empty = _set(
        census=DecisionCensusV4.from_feature_hashes([]),
        answered_decisions=0,
        correct_decisions=0,
        confident_errors=0,
        changed_actions=0,
    )
    assert empty.coverage is None
    assert empty.accuracy is None
    assert empty.confident_error_rate is None

    silent = _set(answered_decisions=0, correct_decisions=0, confident_errors=0, changed_actions=0)
    assert silent.coverage == Decimal(0)
    assert silent.accuracy is None


def test_a_decision_set_cannot_answer_more_than_it_counted() -> None:
    with pytest.raises(ValueError, match="more answered decisions than independent"):
        _set(answered_decisions=21)


@pytest.mark.parametrize("field", ["correct_decisions", "confident_errors", "changed_actions"])
def test_an_abstention_cannot_be_correct_wrong_or_a_changed_action(field: str) -> None:
    counts = {
        "answered_decisions": 10,
        "correct_decisions": 0,
        "confident_errors": 0,
        "changed_actions": 0,
        field: 11,
    }
    with pytest.raises(ValueError, match="counts an abstention as an answer"):
        _set(**counts)


def test_an_answer_is_correct_or_a_confident_error_but_not_both() -> None:
    with pytest.raises(ValueError, match="either correct or a confident error"):
        _set(answered_decisions=19, correct_decisions=15, confident_errors=6)


def test_the_released_d3_counts_still_read_through_revision_three() -> None:
    """Revision 4 is additive: the D3 evidence is read through the D3 class, unchanged."""
    selection = json.loads((EVIDENCE / "sprint-21d3-learner-selection.json").read_text())
    counts = [
        CorrectionEvaluationCountsV3.model_validate(setting["metamorphic"]["counts"])
        for setting in selection["settings"]
    ]
    assert len(counts) == 24
    assert all(item.ranking_decisions == 120 for item in counts)
    assert all(
        item.content_hash == setting["metamorphic"]["counts"]["content_hash"]
        for item, setting in zip(counts, selection["settings"], strict=True)
    )


def test_the_published_schema_requires_the_triple() -> None:
    """S21D4-020's refusal: a payload without the triple is refused by the exported schema."""
    schema = DecisionCensusV4.model_json_schema(mode="serialization")
    assert {
        "nominal_decisions",
        "independent_decisions",
        "replicated_decisions",
    } <= set(schema["required"])
    assert "census" in CorrectionDecisionSetV4.model_json_schema(mode="serialization")["required"]
