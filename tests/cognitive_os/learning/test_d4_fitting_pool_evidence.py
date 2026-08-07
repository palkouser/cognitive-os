"""S21D4-012: the fitting pool is the one the seal froze, and it touches no protected role.

The audit was recorded late, after S21D4-032 had already sealed the catalogue it describes.
That makes one property load-bearing above all others: the record must still describe the
sealed pool, not a pool that has drifted away from it since.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
POOL = EVIDENCE / "sprint-21d4-fitting-pool.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d4-contracts.json"


def _load() -> dict[str, Any]:
    return json.loads(POOL.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_frozen_contracts() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["contracts_sha256"] == _sha256(CONTRACTS.read_bytes())
    assert document["final_outcomes_inspected"] is False
    assert document["d4_measurements_opened"] == 0


def test_the_audited_pool_is_the_sealed_one() -> None:
    """A late audit of a pool that has since moved would describe nothing that will run."""
    bundle = seal_d4_corpus()
    fitting = bundle.catalogues[CorrectionPartition.TRAINING]
    pool = _load()["fitting_pool"]
    assert pool["catalogue_hash"] == fitting.content_hash
    assert pool["checked_against_seal"] == bundle.seal.content_hash
    assert pool["achieved_groups"] == len(fitting.groups) == 80
    assert pool["achieved_outcomes"] == fitting.candidate_slots == 320
    assert pool["meets_the_declared_pool"] is True
    audited = {row["repository_group"] for row in _load()["per_group"]}
    assert audited == {group.repository_group for group in fitting.groups}


def test_every_package_carries_a_verified_rights_record() -> None:
    document = _load()
    assert document["rights"]["all_verified"] is True
    assert document["rights"]["groups_without_one"] == []
    assert document["rights"]["groups_with_a_verified_rights_record"] == 80
    for row in document["per_group"]:
        assert row["rights"]["rights_verified"] is True
        assert row["rights"]["licence_identifier"]
        assert len(row["rights"]["rights_evidence_hash"]) == 64
        assert row["package_to_re_execute"] is True


def test_the_pool_is_disjoint_from_every_protected_role_on_every_key_it_has() -> None:
    disjointness = _load()["disjointness"]
    assert disjointness["transitively_disjoint"] is True
    assert disjointness["overlaps"] == {}
    keys = disjointness["keys_compared"]
    assert set(disjointness["roles_compared"]) == {
        "calibration",
        "final_a",
        "final_b",
        "canary",
        "retrieval",
    }
    # Task id is the key a name-only comparison would miss; it must be used wherever it exists.
    for role in ("calibration", "final_a", "final_b", "canary"):
        assert "task_id" in keys[role]
    # And it must not be claimed for the role that has none.
    assert "task_id" not in keys["retrieval"]


def test_the_provenance_is_reported_per_sprint_not_per_partition_name() -> None:
    """Fifty 'D2 training' groups are thirty C3 and twenty D2. The record has to say so."""
    pool = _load()["fitting_pool"]
    assert pool["provenance_counts"] == {"21C3": 30, "21D2": 30, "21D3": 20}
    assert sum(pool["provenance_counts"].values()) == 80
    assert pool["composition_names_released_partitions"] is True
    assert pool["declared_composition"] == {
        "d2_calibration": 10,
        "d2_training": 50,
        "d3_calibration": 20,
    }


def test_the_spent_calibration_exemplars_are_resolved_from_the_released_partitions() -> None:
    exemplars = _load()["spent_calibration_groups_as_fitting_exemplars"]
    assert exemplars["d2_calibration_groups"] == 10
    assert exemplars["d3_calibration_groups"] == 20
    assert exemplars["the_rest_are_the_d2_training_partition"] == 50
    assert exemplars["matches_the_declared_composition"] is True
    assert exemplars["declared_before_any_d4_measurement"] is True


def test_the_c3_exclusion_records_the_arithmetic_that_does_not_close() -> None:
    """The contract's 110-group figure cannot be right, and the record must not repeat it."""
    c3 = _load()["sprint_21c3_corpus"]
    assert c3["included_as_an_additional_source"] is False
    assert c3["c3_groups_inside_the_released_d2_training_partition"] == 30
    assert c3["c3_groups_available_outside_it"] == 0
    arithmetic = c3["contract_arithmetic_that_does_not_close"]
    assert "110" in arithmetic
    assert "thirty" in arithmetic
    assert "amended rather than edited" in arithmetic
    assert c3["limitation_s21d4_039_must_report"]


def test_the_volume_points_are_the_declared_ones_because_the_pool_is_full() -> None:
    volumes = _load()["volume_points"]
    assert volumes["declared"] == [200, 320]
    assert volumes["achieved"] == [200, 320]
    assert volumes["set_from_the_achieved_pool"] is False
    assert volumes["rows_at_the_upper_point"] == 320


def test_the_record_says_it_was_written_late() -> None:
    late = _load()["recorded_late"]
    assert late["planned_wave"] == "W1"
    assert late["actual_wave"] == "W2"
    assert late["why"]
    assert late["what_it_changes"]
