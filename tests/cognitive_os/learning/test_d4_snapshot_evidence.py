"""S21D4-037: two immutable snapshots, one fitted matrix, eleven scans.

The snapshot is where a campaign becomes something a learner may read, so the checks are about
the ways that transition goes wrong quietly: a dataset whose membership depends on when it was
built, a matrix that quietly carried calibration rows into the fit, a scan suite that reports
"clean" because two of its scans never ran, and a store that grew underneath a selection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SNAPSHOTS = EVIDENCE / "sprint-21d4-snapshots.json"
SEALS = EVIDENCE / "sprint-21d4-feature-seals.json"
FITTING = EVIDENCE / "sprint-21d4-self-play-campaign.json"
CALIBRATION = EVIDENCE / "sprint-21d4-calibration-campaign.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"

#: The eleven scans a v2 report must run. Named individually because "eleven scans passed" is
#: satisfied just as well by eleven copies of the cheapest one.
REQUIRED_SCANS = {
    "no_forbidden_field_reaches_the_matrix": 1,
    "every_fitted_dimension_is_finite_and_in_range": 2,
    "every_row_has_one_encoder_identity": 1,
    "every_feature_record_precedes_its_outcome": 1,
    "every_row_resolves_to_one_pre_outcome_source_chain": 1,
    "no_group_crosses_the_split": 1,
    "no_identical_row_carries_two_labels": 1,
    "no_near_duplicate_crosses_the_split": 1,
    "no_column_derives_the_label": 2,
}


def _load() -> dict[str, Any]:
    return json.loads(SNAPSHOTS.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dataset(partition: str) -> dict[str, Any]:
    return next(item for item in _load()["datasets"] if item["partition"] == partition)


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_campaigns_it_snapshotted() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["feature_seals_sha256"] == _sha256(SEALS.read_bytes())
    assert document["fitting_campaign_sha256"] == _sha256(FITTING.read_bytes())
    assert document["calibration_campaign_sha256"] == _sha256(CALIBRATION.read_bytes())
    assert document["final_outcomes_inspected"] is False


@pytest.mark.parametrize(
    ("partition", "members", "groups"), [("training", 320, 80), ("calibration", 400, 100)]
)
def test_each_dataset_is_explicit_and_rebuilds_to_one_identity(
    partition: str, members: int, groups: int
) -> None:
    dataset = _dataset(partition)
    assert dataset["identity_revision"] == 3
    assert dataset["members"] == members
    assert dataset["observation_count"] == members
    assert dataset["groups"] == groups
    assert dataset["rebuilt_identically"] is True
    assert dataset["immutable"] is True
    assert dataset["store_wide_selection"] is False
    assert dataset["latest_seal_selection"] is False
    assert dataset["real_governed_runs"] == 0
    assert dataset["usage_rights_verified"] is True


def test_the_two_datasets_are_two_identities() -> None:
    """One identity for both splits would make the fit and the holdout the same record."""
    fitting = _dataset("training")
    calibration = _dataset("calibration")
    assert fitting["dataset_id"] != calibration["dataset_id"]
    assert fitting["split_manifest_hash"] != calibration["split_manifest_hash"]
    assert fitting["example_manifest_hash"] != calibration["example_manifest_hash"]
    assert fitting["split"] == "fit"
    assert calibration["split"] == "calibration"


def test_the_labels_and_vectors_came_from_the_store_not_the_report() -> None:
    """A matrix assembled from a report agrees with that report by construction."""
    for partition in ("training", "calibration"):
        dataset = _dataset(partition)
        assert "ledger" in dataset["labels_read_from"]
        assert "artifact store" in dataset["vectors_read_from"]


def test_the_fitted_matrix_is_the_fitting_split_alone() -> None:
    matrix = _load()["fitted_matrix"]
    assert matrix["fit_rows"] == 320
    assert matrix["fit_groups"] == 80
    assert matrix["calibration_rows"] == 400
    assert matrix["calibration_groups"] == 100
    assert matrix["fitted_dimensions"] == 390
    assert matrix["fit_and_calibration_share_no_group"] is True
    assert matrix["clean"] is True
    assert matrix["encoder_version"] == "correction-ranking-v2"


def test_all_eleven_scans_ran_and_each_is_the_one_it_claims_to_be() -> None:
    """Eleven passes are satisfied by eleven copies of the cheapest scan; names are not."""
    scans = _load()["scans"]
    assert scans["count"] == scans["required"] == 11
    assert scans["all_passed"] is True
    assert scans["failed"] == []
    counted: dict[str, int] = {}
    for scan in scans["results"]:
        assert scan["passed"] is True
        assert scan["detail"]
        counted[scan["name"]] = counted.get(scan["name"], 0) + 1
    assert counted == REQUIRED_SCANS


def test_the_two_split_scans_each_ran_on_both_splits() -> None:
    """Range and label-derivation are per-split; running them twice on one split proves half."""
    results = _load()["scans"]["results"]
    for name in ("every_fitted_dimension_is_finite_and_in_range", "no_column_derives_the_label"):
        assert sum(1 for scan in results if scan["name"] == name) == 2


def test_the_near_duplicate_scan_reports_the_margin_it_passed_by() -> None:
    """A pass at 0.9999 against a 0.999 floor and a pass at 0.5 are different facts."""
    matrix = _load()["fitted_matrix"]
    highest = float(matrix["maximum_cross_split_similarity"])
    floor = float(matrix["near_duplicate_threshold"])
    assert highest < floor
    detail = next(
        scan["detail"]
        for scan in _load()["scans"]["results"]
        if scan["name"] == "no_near_duplicate_crosses_the_split"
    )
    assert matrix["maximum_cross_split_similarity"] in detail


def test_the_store_holds_more_than_the_datasets_name_and_the_record_measures_it() -> None:
    """A duplicate campaign run left rows behind. Explicit selection is why nothing moved."""
    state = _load()["store_state"]
    assert state["observations_named_by_the_two_datasets"] == 720
    assert state["observations_on_the_correction_surface"] >= 720
    assert (
        state["unreferenced_rows"]
        == state["observations_on_the_correction_surface"] - 720
        == sum(state["unreferenced_by_campaign_manifest"].values())
    )
    assert state["explicit_selection_is_why_this_is_survivable"] is True
    assert state["why_the_store_holds_more_than_the_datasets_name"]
    # Every unreferenced row must be attributable, or "unreferenced" is just "unexplained".
    assert state["unreferenced_by_campaign_manifest"]
    assert state["unreferenced_row_provenance"]
