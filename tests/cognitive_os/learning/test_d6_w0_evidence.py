"""S21D6-018: W0's five records, checked against the code and against each other.

W0 publishes no measurement, so what there is to test is whether the records say what the
sprint's own modules say, and whether the two governance decisions are the shape they claim.
Three of these assertions would have caught a real failure mode:

*A contract that drifts from its implementation.* The admission contract states a rank and a
leak count; both are recomputed here from `conformal_operating_point` rather than read back out
of the record that asserts them.

*An alpha that reads well and does nothing.* The pre-registration's central claim is that alpha
below 2/13 reproduces the rule D5 stopped on. That is arithmetic over the sealed m = 12, and it
is checked here rather than trusted.

*A seal that stopped sealing.* Every W0 record is re-hashed from its own bytes, in the
convention its writer used.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.learning.conformal_operating_point import (
    admitted_error_upper_bound,
    conformal_rank,
)

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"

GATE_CONTRACT = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"
#: The sealed count of wrong answered decisions in the conformal half, at 720 rows.
WRONG_AT_720 = 12

#: Each W0 record and the `ensure_ascii` its writer sealed it with. The two families exist
#: because the pre-registration family predates the others; both are deterministic, and a record
#: checked under the wrong one fails loudly rather than quietly.
RECORDS = {
    "sprint-21d6-baseline.json": True,
    "sprint-21d6-provisioning.json": True,
    "sprint-21d6-reuse-audit.json": True,
    "sprint-21d6-contracts-amendment-2.json": True,
    "sprint-21d6-condition-24-ruling.json": True,
    "sprint-21d6-contracts.json": False,
    "sprint-21d6-pre-registration.json": False,
}


def _load(name: str) -> dict[str, Any]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _sha256_file(name: str) -> str:
    return hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()


@pytest.mark.parametrize(("name", "ensure_ascii"), sorted(RECORDS.items()))
def test_every_w0_record_reproduces_its_seal(name: str, ensure_ascii: bool) -> None:
    document = _load(name)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    recomputed = hashlib.sha256(
        json.dumps(body, indent=1, sort_keys=True, ensure_ascii=ensure_ascii).encode("utf-8")
    ).hexdigest()
    assert recomputed == document["integrity_content_hash"]


def test_the_baseline_starts_from_a_verified_d5_release() -> None:
    baseline = _load("sprint-21d6-baseline.json")
    assert baseline["d5_release"]["local_and_remote_agree"]
    assert baseline["d5_release"]["tag_type"] == "tag"
    assert baseline["success_tag_absent"]
    assert baseline["predecessor_stores_match_expectation"]
    assert baseline["branch"]["descends_from_current_origin_main"]
    # Seven roots, and D5's own joins the list the way D4's did when D5 started.
    assert len(baseline["predecessor_artifact_stores"]) == 7
    assert baseline["predecessor_artifact_stores"]["sprint_21d5"]["matches_expected"] is None
    assert all(run["conclusion"] == "success" for run in baseline["ci_runs"])
    assert baseline["gate_state_at_baseline"]["gate_l2"] == "does not pass"
    assert baseline["gate_state_at_baseline"]["sprint_22a"] == "blocked"


def test_the_amendment_changes_one_clause_and_leaves_the_gate_contract_hash_alone() -> None:
    amendment = _load("sprint-21d6-contracts-amendment-2.json")
    assert amendment["amends"]["gate_contract_sha256"] == GATE_CONTRACT
    assert amendment["amends"]["gate_contract_bytes_modified"] == 0
    assert amendment["amends"]["thresholds_changed"] == 1
    assert amendment["amends"]["conditions_affected"] == [14]
    for key in ("struck_sentence", "amended_sentence"):
        assert (
            hashlib.sha256(amendment[key].encode("utf-8")).hexdigest() == amendment[f"{key}_sha256"]
        )
    assert "zero confident errors" in amendment["struck_sentence"]
    assert "split-conformal bar" in amendment["amended_sentence"]


def test_the_amendment_is_justified_by_a_recomputed_infeasibility_not_by_prose() -> None:
    """The claim is that no zero-error threshold reaches the floor, on either cell."""
    justification = _load("sprint-21d6-contracts-amendment-2.json")["justification"]
    assert justification["read_from_sha256"] == _sha256_file("sprint-21d5-learner-selection.json")
    assert justification["infeasible_on_every_cell"]
    assert set(justification["cells"]) == {"320", "720"}
    for cell in justification["cells"].values():
        assert not cell["zero_error_coverage_reaches_the_floor"]
        assert Decimal(cell["best_zero_error_coverage"]) < Decimal("0.40")
    # And the one tolerated error is what buys the floor, at the cell revision 6 selects.
    at_720 = justification["cells"]["720"]["best_coverage_at_error_count"]
    assert Decimal(at_720["0"]["coverage"]) == Decimal("0.27")
    assert Decimal(at_720["1"]["coverage"]) >= Decimal("0.40")


def test_no_d6_measurement_existed_when_the_amendment_was_signed() -> None:
    chronology = _load("sprint-21d6-contracts-amendment-2.json")["chronology"]
    assert chronology["d6_conformal_bars_derived"] == 0
    assert chronology["d6_calibration_outcomes"] == 0
    assert chronology["d6_certification_corpus_authored"] is False
    assert chronology["d6_measurement_records_present"] == []


def test_the_condition_24_ruling_is_an_inheritance_with_a_falsifier() -> None:
    ruling = _load("sprint-21d6-condition-24-ruling.json")
    assert ruling["condition"] == 24
    assert ruling["ruling"].startswith("inherited")
    assert ruling["d6_reads_no_retrieval_holdout"] is True
    assert ruling["what_it_saves"]["authored_retrieval_groups"] == 60
    # The inheritance is only as good as the hashes it binds, so they must still resolve.
    assert ruling["inherited_measurement"]["record_sha256"] == _sha256_file(
        "sprint-21d5-retrieval-decision.json"
    )
    voided = ruling["the_three_identities_that_void_it"]
    assert set(voided) == {"searchable_surface", "retrieval_arms", "comparator"}
    assert voided["searchable_surface"]["record_sha256"] == _sha256_file("sprint-21d5-surface.json")
    assert ruling["inherited_measurement"]["passed"] is True
    assert ruling["re_checked_at"].startswith("gate close")


def test_the_carried_roles_are_reusable_and_still_unopened() -> None:
    audit = _load("sprint-21d6-reuse-audit.json")
    assert audit["eligible_for_reuse"]
    assert {role: body["decision"] for role, body in audit["roles"].items()} == {
        "final_a": "reuse",
        "final_b": "reuse",
        "canary": "reuse",
    }
    assert audit["protected_bodies_resolved"] == 0
    assert audit["individual_body_hashes_resolved"] == 0
    assert audit["group_disjointness"]["all_pairwise_disjoint"]
    authority = audit["access_and_outcome_authority"]
    assert authority["zero_outcomes_predictions_or_receipts"]
    # D4's and D5's stores hold real campaigns; it is their zero for protected identities that
    # carries the claim, so a test that only saw empty stores would be proving nothing.
    for store in ("cognitive_os_s21d4_test", "cognitive_os_s21d5_test"):
        assert authority["store_counts"][store]["observations_total"] > 0
        assert authority["store_counts"][store]["observations_for_protected_roles"] == 0


def test_d5s_calibration_becomes_a_bar_setter_and_never_a_certifier() -> None:
    transition = _load("sprint-21d6-reuse-audit.json")["role_transition"]
    assert transition["map"]["calibration"]["d6_role"] == "conformal"
    assert transition["conformal_half"]["groups"] == 100
    assert transition["conformal_half"]["re_executed"] is False
    assert transition["conformal_half"]["read_through"]["refitted"] is False
    assert "certifies no coverage" in transition["conformal_half"]["use"]
    assert transition["d6_certification_corpus_present"] is False
    assert transition["spent_entirely"]["d6_role"] == "none"
    assert transition["spent_entirely"]["condition_24"]["authored_groups_saved"] == 60


def test_revision_six_is_published_with_nothing_measured() -> None:
    pre = _load("sprint-21d6-pre-registration.json")
    assert pre["revision"] == 6
    assert pre["measured_values"] == 0
    assert not any(pre["chronology"].values())
    assert pre["supersedes"]["revision"] == 5
    assert pre["amendments"] == ["sprint-21d6-contracts-amendment-2.json"]
    for name, expected in pre["evidence_children_sha256"].items():
        assert _sha256_file(name) == expected
    assert pre["contracts_sha256"] == _sha256_file("sprint-21d6-contracts.json")
    # Design inputs are disclosed rather than counted as zero; the distinction is the point.
    assert "sprint-21d5-learner-selection.json" in pre["design_inputs_from_released_evidence"]


def test_every_revision_six_contract_reproduces_its_frozen_hash() -> None:
    contracts = _load("sprint-21d6-contracts.json")
    pre = _load("sprint-21d6-pre-registration.json")
    assert contracts["revision"] == 6
    assert contracts["measured_values"] == 0
    assert contracts["thresholds_changed"]["count"] == 1
    assert set(contracts["contracts"]) == set(pre["contract_hashes"])
    for name, body in contracts["contracts"].items():
        frozen = dict(body)
        stated = frozen.pop("content_hash")
        recomputed = hashlib.sha256(
            json.dumps(frozen, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert recomputed == stated == pre["contract_hashes"][name]


def test_the_pre_registered_alpha_is_the_one_that_moves_the_bar() -> None:
    """Revision 6's central arithmetic, recomputed rather than read back.

    With m = 12 the rank is 12 for every alpha below 2/13, and a bar at the 12th of 12 wrong
    margins is the largest of them — the zero-error prefix rule D5 stopped on. Alpha 0.20 is the
    first round value whose rank is 11, leaving exactly one wrong margin above the bar.
    """
    contract = _load("sprint-21d6-contracts.json")["contracts"]["admission_rule"]
    alpha = Decimal(contract["alpha"])
    assert alpha == Decimal("0.20")
    assert conformal_rank(alpha, WRONG_AT_720) == contract["rank_at_this_alpha"] == 11
    assert WRONG_AT_720 - conformal_rank(alpha, WRONG_AT_720) == 1
    assert contract["wrong_margins_left_above_the_bar"] == 1
    for collapses in ("0.05", "0.10", "0.15"):
        assert conformal_rank(Decimal(collapses), WRONG_AT_720) >= WRONG_AT_720
    assert Decimal(contract["alpha_floor_below_which_the_bar_is_the_failed_rule"]) < alpha


def test_the_ceiling_admits_what_the_selection_rule_says_it_admits() -> None:
    """C = 0.15 permits up to three errors in 58 admitted decisions, and not four."""
    rule = _load("sprint-21d6-contracts.json")["contracts"]["selection_rule"]
    ceiling = Decimal(rule["ceiling_c"])
    table = rule["bound_at_the_expected_coverage"]
    for errors, stated in table.items():
        assert round(admitted_error_upper_bound(int(errors), 58), 6) == stated
    assert Decimal(str(table["3"])) <= ceiling < Decimal(str(table["4"]))
    # The claim the amendment rests on: the struck rule's own bound was no better.
    assert admitted_error_upper_bound(1, 58) < admitted_error_upper_bound(0, 27)


def test_the_decision_tree_publishes_four_endings_before_any_number_exists() -> None:
    tree = _load("sprint-21d6-contracts.json")["contracts"]["decision_tree"]
    assert tree["endings_are_four_different_sprints"]
    assert tree["no_ending_may_be_chosen_after_the_measurement"]
    assert set(tree["endings"]) == {
        "0_admission_contract_refused",
        "1_select",
        "2_leak_budget_exceeded",
        "3_margin_coverage_bound",
        "4_no_quantile",
    }


def test_one_cell_is_selectable_and_the_other_is_only_reported() -> None:
    cell = _load("sprint-21d6-contracts.json")["contracts"]["candidate_cell"]
    assert cell["selected_direction_fitting_rows"] == 720
    assert cell["refitted"] is False
    assert cell["reported_but_not_selectable"]["fitting_rows"] == 320
    assert cell["selected_direction"] != cell["reported_but_not_selectable"]["direction"]
