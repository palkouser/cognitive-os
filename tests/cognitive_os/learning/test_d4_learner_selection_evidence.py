"""S21D4-039: the risk-coverage grid, and the typed null it produced.

A null is the easiest result to fake and the hardest to read. It looks identical whether the
grid was searched and found nothing, or was never searched at all. So the tests here are mostly
about the second possibility: that every cell was measured, that the ranker was not silent,
that the stop kind was derived from the numbers rather than chosen, and that the null names
what it leaves closed.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from cognitive_os.learning.knn_calibration import declared_grid, grid_hash

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SELECTION = EVIDENCE / "sprint-21d4-learner-selection.json"
SEALS = EVIDENCE / "sprint-21d4-feature-seals.json"
SNAPSHOTS = EVIDENCE / "sprint-21d4-snapshots.json"
INVARIANCE = EVIDENCE / "sprint-21d4-invariance-regression.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

VOLUMES = ("200", "320")


def _load() -> dict[str, Any]:
    return json.loads(SELECTION.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_every_input_it_measured() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["feature_seals_sha256"] == _sha256(SEALS.read_bytes())
    assert document["snapshots_sha256"] == _sha256(SNAPSHOTS.read_bytes())
    assert document["invariance_regression_sha256"] == _sha256(INVARIANCE.read_bytes())
    assert document["final_or_canary_outcomes_inspected"] == 0
    assert document["final_outcomes_inspected"] is False


def test_the_hundred_independent_decisions_are_there() -> None:
    """The floor the whole wave exists to reach."""
    decisions = _load()["decisions"]
    assert decisions["independent_decisions"] == 100
    census = decisions["census"]
    assert census["nominal_decisions"] == 100
    assert census["independent_decisions"] == 100
    assert census["replicated_decisions"] == 0


def test_the_whole_declared_grid_was_searched_at_both_volumes() -> None:
    grid = _load()["grid"]
    assert grid["hash"] == grid_hash()
    assert grid["settings"] == len(declared_grid()) == 24
    assert grid["operating_points"] == ["0.55", "0.70", "zero_error"]
    assert grid["volume_points"] == [200, 320]
    assert grid["cells"] == grid["cells_reported"] == 24 * 3 * 2 == 144
    assert len(_load()["cells"]) == 144
    assert grid["zero_error_derivations"] == 24 * 2


def test_every_cell_is_reported_including_the_ones_that_prove_nothing() -> None:
    """§2.3 requires every grid point, including filtered and fully abstaining ones."""
    document = _load()
    for cell in document["cells"]:
        assert cell["independent_decisions"] == 100
        assert cell["coverage_denominator"] == "independent_decisions"
        assert cell["maximum_inference_ms"]
        assert "ineligible_reasons" in cell
    # Both flags exist as fields even at zero, so a reader can tell "none" from "not checked".
    assert document["grid"]["fully_abstaining_cells"] == 0
    assert document["grid"]["filtered_no_changed_decision"] == 0


def test_the_ranker_was_not_silent() -> None:
    """A null from a grid that abstained everywhere would say nothing about the hypothesis."""
    cells = _load()["cells"]
    assert all(cell["answered_decisions"] > 0 for cell in cells)
    assert min(cell["admitted_decisions"] for cell in cells) > 0


def test_the_operating_point_actually_restricts_somewhere() -> None:
    """If admission never bit, the three operating points would be one point reported thrice."""
    cells = _load()["cells"]
    restricted = [cell for cell in cells if cell["admitted_decisions"] < cell["answered_decisions"]]
    assert restricted, "no operating point ever restricted the answered set"


def test_the_baseline_was_measured_on_the_same_decisions() -> None:
    baseline = _load()["baseline"]
    assert baseline["strongest_deterministic_rung"]
    assert "same 100 calibration decisions" in baseline["measured_on"]
    # The cosine rung is not silently scored on a column v2 removed; it is reported ineligible.
    ineligible = [rung for rung in baseline["rungs"] if not rung["eligible"]]
    for rung in ineligible:
        assert rung["ineligible_reason"]
    assert any(rung["eligible"] for rung in baseline["rungs"])


def test_the_stop_kind_follows_from_the_numbers() -> None:
    """`hypothesis_class_bound` is step 5's branch, and step 4's condition must not hold."""
    document = _load()
    curve = document["risk_coverage_curve"]
    low = Decimal(curve[VOLUMES[0]]["best_zero_error_coverage"])
    high = Decimal(curve[VOLUMES[-1]]["best_zero_error_coverage"])
    assert document["decision_tree"]["stop"] == "hypothesis_class_bound"
    # Step 4 would need coverage above zero at the upper volume and higher than at the lower.
    assert not (high > 0 and high < Decimal("0.40") and high > low)
    assert low == high == 0
    assert document["decision_tree"]["outcome_4_and_5_not_guessed"] is True


def test_the_curve_reports_risk_as_well_as_coverage() -> None:
    """Zero-error coverage alone is one number and cannot show whether the grid came close."""
    curve = _load()["risk_coverage_curve"]
    for volume in VOLUMES:
        row = curve[volume]
        assert row["cells"] == 72
        assert row["cells_with_zero_confident_errors"] == 0
        assert row["fewest_confident_errors"] > 0
        assert row["most_confident_errors"] >= row["fewest_confident_errors"]
        assert len(row["coverage_range"]) == 2
        assert row["best_first_choice_rate_over_admitted"]


def test_the_residual_states_both_halves_of_the_finding() -> None:
    """The grid carries signal and still cannot be made selective. Either half alone misleads."""
    residual = _load()["residual"]
    curve = _load()["risk_coverage_curve"]
    assert residual["the_grid_carries_signal"]
    assert residual["and_cannot_be_made_selective"]
    assert residual["which_is_why_the_stop_is_hypothesis_class_and_not_volume"]
    # The signal claim has to be true of the cells, not just written down.
    assert all(curve[volume]["cells_beating_the_baseline"] == 72 for volume in VOLUMES)
    assert all(cell["beats_the_baseline"] for cell in _load()["cells"])


def test_the_null_is_immutable_and_names_what_stays_closed() -> None:
    selection = _load()["selection"]
    assert selection["outcome"] == "null"
    assert selection["immutable"] is True
    assert selection["stop_kind"] == "hypothesis_class_bound"
    assert selection["precedence"]["eligible_cells"] == 0
    assert selection["precedence"]["pool_taken_from"] == "none"
    assert len(selection["dependent_not_opened"]) >= 8
    for entry in selection["dependent_not_opened"]:
        assert entry
    assert selection["why_a_null_and_not_a_weaker_candidate"]


def test_every_ineligible_cell_says_which_condition_it_failed() -> None:
    """An unexplained ineligibility is indistinguishable from an arbitrary one."""
    document = _load()
    counts = document["section_2_3"]["ineligibility_counts"]
    assert counts
    assert sum(counts.values()) >= len([c for c in document["cells"] if c["ineligible_reasons"]])
    for cell in document["cells"]:
        for reason in cell["ineligible_reasons"]:
            assert reason in counts


def test_the_c3_exclusion_limitation_is_reported() -> None:
    """§4.3 requires this record to say the 200-to-320 span is the weaker evidence it is."""
    limitations = _load()["limitations"]
    assert "200 to 440" in limitations["s21c3_corpus_excluded"]
    assert "hypothesis_class_bound" in limitations["s21c3_corpus_excluded"]
    assert limitations["volume_spacing"]
    assert "W2-D9" in limitations["batch_dependence"]


def test_the_inference_budget_was_measured_against_its_number() -> None:
    document = _load()
    assert document["section_2_3"]["inference_budget_ms"] == "250"
    for cell in document["cells"]:
        assert Decimal(cell["maximum_inference_ms"]) >= 0
        assert cell["within_inference_budget"] is (
            Decimal(cell["maximum_inference_ms"]) <= Decimal("250")
        )


def test_first_action_preservation_came_from_the_invariance_run() -> None:
    document = _load()
    assert document["section_2_3"]["first_action_preservation_on_the_invariance_sample"] is True
    assert json.loads(INVARIANCE.read_text())["first_action"]["changes"] == 0
