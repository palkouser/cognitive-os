"""S21D7-005: W0's eight records, checked against the code and against each other.

W0 publishes no measurement, so what there is to test is whether the records say what the
sprint's own modules say, and whether the three rulings are the shape they claim. Four of these
assertions would have caught a real failure mode:

*A ruling that reads well and does nothing.* The demotion ruling's whole argument is that alpha
= 0.20 is a genuine quantile on one candidate half and the failed prefix rule on the other. That
is arithmetic over two wrong counts, and it is recomputed here from `conformal_operating_point`
rather than read back out of the record that asserts it.

*A ladder ruling that lowered the bar.* The rung was seated to make the baseline harder, so the
test recomputes the strongest released rung from the sealed groundwork record and demands the
seated baseline be at least as high on every corpus.

*A model hash that is a string in a file.* The groundwork's sealed weights are rebuilt into a
`ContainmentContrastiveModel` and re-hashed through the released class, so the hash W2 is bound
to reproduce is proved to be the hash of those weights rather than a number somebody typed.

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
from cognitive_os.learning.containment_contrastive import (
    FITTED_RELATIONAL_CHANNELS,
    HYPOTHESIS_CLASS,
    ContainmentContrastiveModel,
)
from cognitive_os.learning.correction_ladder import LADDER_RUNGS
from cognitive_os.learning.repair_containment import REPAIR_CONTAINMENT_CHANNEL

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"

GATE_CONTRACT = "9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7"
ALPHA = Decimal("0.20")
#: The wrong answered decisions the demoted half carries under this class, as the groundwork's
#: diagnostic implies them. The alpha table is a function of it.
WRONG_IN_THE_DEMOTED_HALF = 16
EXPECTED_ADMITTED = 46

#: Each W0 record and the `ensure_ascii` its writer sealed it with. Both families are
#: deterministic, and a record checked under the wrong one fails loudly rather than quietly.
RECORDS = {
    "sprint-21d7-baseline.json": True,
    "sprint-21d7-provisioning.json": True,
    "sprint-21d7-reuse-audit.json": True,
    "sprint-21d7-demotion-ruling.json": True,
    "sprint-21d7-ladder-ruling.json": True,
    "sprint-21d7-condition-24-ruling.json": True,
    "sprint-21d7-contracts.json": False,
    "sprint-21d7-pre-registration.json": False,
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


def test_the_baseline_starts_from_a_verified_d6_release() -> None:
    baseline = _load("sprint-21d7-baseline.json")
    assert baseline["d6_release"]["local_and_remote_agree"]
    assert baseline["d6_release"]["tag_type"] == "tag"
    assert baseline["success_tag_absent"]
    assert baseline["predecessor_stores_match_expectation"]
    assert baseline["branch"]["descends_from_current_origin_main"]
    assert all(run["conclusion"] == "success" for run in baseline["ci_runs"])
    assert baseline["gate_state_at_baseline"]["gate_l2"] == "does not pass"
    assert baseline["gate_state_at_baseline"]["sprint_22a"] == "blocked"
    assert baseline["gate_state_at_baseline"]["gate_l2_counts"] == {
        "met": 14,
        "not_opened": 15,
        "failed": 0,
    }


def test_the_freeze_covers_the_store_d6_actually_measured_in() -> None:
    """W0-F1. D6's measured campaign ran in a second pair no released record fingerprints."""
    stores = _load("sprint-21d7-baseline.json")["predecessor_artifact_stores"]
    assert len(stores) == 9
    measured = stores["sprint_21d6_measured"]
    assert measured["path"].endswith("artifacts-s21d6-measured")
    assert measured["files"] > 0
    # It has no released expectation, so it is recorded as a first observation rather than as a
    # match against a number that does not exist.
    assert measured["matches_expected"] is None
    assert stores["sprint_21d6"]["matches_expected"] is True


def test_the_demotion_ruling_moves_no_threshold_and_names_one_half() -> None:
    ruling = _load("sprint-21d7-demotion-ruling.json")
    assert ruling["thresholds_changed"] == 0
    assert ruling["gate_contract_sha256"] == GATE_CONTRACT
    assert ruling["gate_contract_bytes_modified"] == 0
    assert ruling["named_half"]["half"] == "d6_certification"
    assert ruling["named_half"]["re_executed"] is False
    assert ruling["named_half"]["re_scored_under"] == HYPOTHESIS_CLASS
    # The rule is stated in both directions, and the forbidden direction is the load-bearing one.
    permissions = ruling["the_rule_in_both_directions"]
    assert "set a threshold" in permissions["may"]
    assert "certify" in permissions["may_not"]
    assert "measured set" in permissions["may_not"]
    assert "re-executed" in permissions["may_not"]
    assert ruling["justification"]["read_from_sha256"] == _sha256_file(
        "sprint-21d7-transfer-gap.json"
    )


def test_the_demotion_is_chosen_by_recomputed_arithmetic_not_by_prose() -> None:
    """At m = 6 alpha 0.20 has no quantile left to take; at m = 16 it is two errors deep."""
    candidates = _load("sprint-21d7-demotion-ruling.json")["justification"]["candidates"]
    assert set(candidates) == {"d5_calibration", "d6_certification"}

    degenerate = candidates["d5_calibration"]
    named = candidates["d6_certification"]
    assert degenerate["spent_times_before_d7"] == 2
    assert named["spent_times_before_d7"] == 1
    assert named["wrong_answered_decisions"] == WRONG_IN_THE_DEMOTED_HALF

    for body in (degenerate, named):
        wrong = body["wrong_answered_decisions"]
        for alpha, row in body["rank_table"].items():
            assert conformal_rank(Decimal(alpha), wrong) == row["rank"]
            assert row["degenerates_to_the_prefix_rule"] is (row["rank"] >= wrong)

    assert degenerate["alpha_0_20_is_a_genuine_quantile"] is False
    assert named["alpha_0_20_is_a_genuine_quantile"] is True
    assert named["rank_table"][str(ALPHA)]["wrong_margins_above_the_bar"] == 2


def test_the_ladder_ruling_seats_a_sixth_rung_and_raises_the_baseline() -> None:
    ruling = _load("sprint-21d7-ladder-ruling.json")
    assert ruling["thresholds_changed"] == 0
    assert ruling["frozen_five"] == list(LADDER_RUNGS)
    assert ruling["ladder_after_this_ruling"] == [*LADDER_RUNGS, REPAIR_CONTAINMENT_CHANNEL]
    assert ruling["rung"]["reads_a_label"] is False

    # Recomputed from the sealed groundwork record: the seated baseline is never lower than the
    # strongest released rung, which is the whole point of seating it.
    groundwork = _load("sprint-21d7-transfer-gap.json")
    containment = groundwork["class_diagnostic"]["containment_rung_alone_first_choice"]
    for corpus in groundwork["transfer_gap"]["corpora"]:
        stated = ruling["what_it_costs"]["corpora"][corpus["corpus"]]
        released = {
            rung["rung"]: Decimal(str(rung["first_choice_rate"]))
            for rung in corpus["rungs"]
            if rung["eligible"]
        }
        strongest = max(released.values())
        seated = max(strongest, Decimal(str(containment[corpus["corpus"]])))
        assert Decimal(stated["strongest_released_rate"]) == strongest
        assert Decimal(stated["seated_baseline"]) == seated
        assert Decimal(stated["raises_the_baseline_by"]) >= 0
    # On D6's corpus that is a real cost, not a rounding one.
    d6 = ruling["what_it_costs"]["corpora"]["d6_certification"]
    assert Decimal(d6["raises_the_baseline_by"]) == Decimal("0.22")


def test_the_condition_24_renewal_binds_the_same_three_identities() -> None:
    ruling = _load("sprint-21d7-condition-24-ruling.json")
    assert ruling["condition"] == 24
    assert ruling["ruling"].startswith("inherited")
    assert ruling["d7_reads_no_retrieval_holdout"] is True
    assert ruling["what_it_saves"]["authored_retrieval_groups"] == 60
    assert ruling["renews"]["record_sha256"] == _sha256_file("sprint-21d6-condition-24-ruling.json")
    assert ruling["inherited_measurement"]["record_sha256"] == _sha256_file(
        "sprint-21d5-retrieval-decision.json"
    )
    voided = ruling["the_three_identities_that_void_it"]
    assert set(voided) == {"searchable_surface", "retrieval_arms", "comparator"}
    assert voided["searchable_surface"]["record_sha256"] == _sha256_file("sprint-21d5-surface.json")
    assert ruling["inherited_measurement"]["passed"] is True
    assert ruling["re_checked_at"].startswith("gate close")


def test_no_d7_measurement_existed_when_the_rulings_were_signed() -> None:
    for name in ("sprint-21d7-demotion-ruling.json", "sprint-21d7-ladder-ruling.json"):
        chronology = _load(name)["chronology"]
        assert chronology["d7_conformal_bars_derived"] == 0
        assert chronology["d7_certification_outcomes"] == 0
        assert chronology["d7_directions_fitted"] == 0
        assert chronology["d7_certification_corpus_authored"] is False
        assert chronology["d7_measurement_records_present"] == []


def test_the_carried_roles_are_reusable_and_still_unopened() -> None:
    audit = _load("sprint-21d7-reuse-audit.json")
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
    # W0-F1 again, from the other end: the store D6 measured in is audited, and it is its zero
    # for protected identities against 400-odd real observations that carries the claim.
    for store in ("cognitive_os_s21d5_test", "cognitive_os_s21d6_measured"):
        assert authority["store_counts"][store]["observations_total"] > 0
        assert authority["store_counts"][store]["observations_for_protected_roles"] == 0


def test_d6s_certification_becomes_a_bar_setter_and_never_a_certifier() -> None:
    transition = _load("sprint-21d7-reuse-audit.json")["role_transition"]
    assert transition["map"]["calibration"]["d7_role"] == "conformal"
    assert transition["conformal_half"]["groups"] == 100
    assert transition["conformal_half"]["re_executed"] is False
    assert "certifies no coverage" in transition["conformal_half"]["use"]
    assert transition["d7_certification_corpus_present"] is False
    assert transition["spent_entirely"]["d7_role"] == "none"
    # The half that was not taken is recorded with its reason rather than left unmentioned.
    assert transition["the_alternative_half_not_taken"]["role"] == "d5 calibration"
    # The fitting pool is used as a fitting pool, which is the one thing this sprint fits on.
    assert transition["fitting_pool"]["groups"] == 180
    assert transition["fitting_pool"]["outcomes"] == 720


def test_revision_seven_is_published_with_nothing_measured_and_nothing_amended() -> None:
    pre = _load("sprint-21d7-pre-registration.json")
    assert pre["revision"] == 7
    assert pre["measured_values"] == 0
    assert not any(pre["chronology"].values())
    assert pre["supersedes"]["revision"] == 6
    assert pre["supersedes"]["sha256"] == _sha256_file("sprint-21d6-pre-registration.json")
    # D6's amendment is carried, not re-made: D7 refuses a second amendment in advance.
    assert pre["amendments"] == ["sprint-21d6-contracts-amendment-2.json"]
    assert pre["amendments_made_by_this_sprint"] == 0
    for name, expected in pre["evidence_children_sha256"].items():
        assert _sha256_file(name) == expected
    assert pre["contracts_sha256"] == _sha256_file("sprint-21d7-contracts.json")
    # The class was found after reading spent evidence; that is disclosed, not counted as zero.
    disclosed = pre["design_inputs_from_released_and_groundwork_evidence"]
    assert "sprint-21d7-transfer-gap.json" in disclosed


def test_every_revision_seven_contract_reproduces_its_frozen_hash() -> None:
    contracts = _load("sprint-21d7-contracts.json")
    pre = _load("sprint-21d7-pre-registration.json")
    assert contracts["revision"] == 7
    assert contracts["measured_values"] == 0
    assert contracts["thresholds_changed"] == {"count": 0, "amendments_made_by_d7": 0}
    assert set(contracts["contracts"]) == set(pre["contract_hashes"])
    for name, body in contracts["contracts"].items():
        frozen = dict(body)
        stated = frozen.pop("content_hash")
        recomputed = hashlib.sha256(
            json.dumps(frozen, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert recomputed == stated == pre["contract_hashes"][name]


def test_the_feature_contract_fits_seven_relational_channels_and_no_embedding() -> None:
    contract = _load("sprint-21d7-contracts.json")["contracts"]["feature_contract_v3"]
    assert contract["allowlist"] == list(FITTED_RELATIONAL_CHANNELS)
    assert contract["channels"] == 7
    assert contract["derived_half"]["channel"] == REPAIR_CONTAINMENT_CHANNEL
    assert contract["derived_half"]["envelope"] is None
    assert contract["embedding"]["channels"] == 384
    assert contract["embedding"]["computed_and_sealed"] is True
    assert contract["embedding"]["read_by_any_v3_channel"] is False
    # The one relation the rename cases move, banned by name rather than by intent.
    assert "source-to-requirement" in contract["channel_rules"]["banned"]
    assert "query_to_candidate_cosine" in contract["channel_rules"]["banned"]


def test_the_carried_alpha_is_a_quantile_on_the_half_it_is_taken_from() -> None:
    """Revision 7's central arithmetic, recomputed rather than read back.

    Alpha does not move; the half does. At m = 16 the rank is 14, so two wrong margins stay
    above the bar and the quantile has content. Any alpha below 2/17 would put the rank back on
    the whole set, which is the prefix rule D5 stopped on.
    """
    contract = _load("sprint-21d7-contracts.json")["contracts"]["admission_rule"]
    alpha = Decimal(contract["alpha"])
    assert alpha == ALPHA
    assert contract["alpha_may_be_rechosen"] is False
    assert contract["wrong_decisions_in_the_bar_setting_half"] == WRONG_IN_THE_DEMOTED_HALF
    assert conformal_rank(alpha, WRONG_IN_THE_DEMOTED_HALF) == contract["rank_at_this_alpha"] == 14
    assert contract["wrong_margins_left_above_the_bar"] == 2
    # W0-F2: the published floor is derived, not typed, and it is checked from the side that
    # matters — at the floor the rank still reaches the whole set, so it really is the bound
    # below which this alpha would buy nothing.
    floor = Decimal(contract["alpha_floor_below_which_the_bar_is_the_failed_rule"])
    assert floor < alpha
    assert contract["alpha_floor_exact"] == f"2/{WRONG_IN_THE_DEMOTED_HALF + 1}"
    assert conformal_rank(floor, WRONG_IN_THE_DEMOTED_HALF) >= WRONG_IN_THE_DEMOTED_HALF


def test_the_ceiling_admits_what_the_selection_rule_says_it_admits() -> None:
    """C = 0.15 permits two errors in the 46 admitted decisions the design expects, not three."""
    rule = _load("sprint-21d7-contracts.json")["contracts"]["selection_rule"]
    ceiling = Decimal(rule["ceiling_c"])
    table = rule["bound_at_the_expected_coverage"]
    for errors, stated in table.items():
        assert round(admitted_error_upper_bound(int(errors), EXPECTED_ADMITTED), 6) == stated
    assert Decimal(str(table["2"])) <= ceiling < Decimal(str(table["3"]))
    assert rule["thresholds_changed_by_this_revision"] == 0
    assert Decimal(rule["coverage_floor"]) == Decimal("0.40")
    assert rule["ladder"]["rungs"] == [*LADDER_RUNGS, REPAIR_CONTAINMENT_CHANNEL]


def test_the_decision_tree_publishes_six_endings_before_any_number_exists() -> None:
    tree = _load("sprint-21d7-contracts.json")["contracts"]["decision_tree"]
    assert tree["endings_are_six_different_sprints"]
    assert tree["no_ending_may_be_chosen_after_the_measurement"]
    assert set(tree["endings"]) == {
        "0_successor_contract_refused",
        "1_select",
        "2_leak_budget_exceeded",
        "3_margin_coverage_bound",
        "4_baseline_not_beaten",
        "5_invariance_violated",
    }
    # The ending the ladder ruling made reachable names the ruling that made it reachable.
    assert "S21D7-011" in tree["endings"]["4_baseline_not_beaten"]


def test_the_sealed_model_hash_is_the_hash_of_the_sealed_weights() -> None:
    """W2 is bound to reproduce this hash, so W0 proves it describes the weights beside it."""
    diagnostic = _load("sprint-21d7-transfer-gap.json")["class_diagnostic"]
    model = ContainmentContrastiveModel(
        channel_names=FITTED_RELATIONAL_CHANNELS,
        weights=tuple(float(diagnostic["weights"][name]) for name in FITTED_RELATIONAL_CHANNELS),
        regularization=str(diagnostic["fitted_on"]["regularization"]),
        fitted_group_count=diagnostic["fitted_on"]["groups"],
        fitted_pair_count=diagnostic["fitted_on"]["pairs"],
    )

    assert model.content_hash() == diagnostic["model_hash"]
    assert diagnostic["hypothesis_class"] == HYPOTHESIS_CLASS
    assert set(diagnostic["weights"]) == set(FITTED_RELATIONAL_CHANNELS)
    # And the cell revision 7 pre-registers is bound to that same hash.
    cell = _load("sprint-21d7-contracts.json")["contracts"]["candidate_cell"]
    assert cell["model_hash_to_reproduce"] == diagnostic["model_hash"]
    assert cell["hypothesis_class"] == HYPOTHESIS_CLASS
    assert cell["cells"] == 1
