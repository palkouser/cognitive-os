"""S21D4-034: the 720 v2 feature records were sealed, and sealed before anything ran.

The seal is only worth anything if it precedes the first container, so the tests that matter
are the ones that would fail if it did not: an outcome present at seal time, a stream that
already carried events, a partition whose bounds were refitted on itself, or a count that
quietly grew a role the wave may not open.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.learning.correction_artifact import FITTED_FEATURE_V2_ALLOWLIST
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_features import FITTED_FEATURE_V2_SCALARS
from cognitive_os.learning.correction_protocol import (
    CorrectionFeatureContractV2,
    CorrectionPartition,
)

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SEALS = EVIDENCE / "sprint-21d4-feature-seals.json"
POOL = EVIDENCE / "sprint-21d4-fitting-pool.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d4-sealed-manifests.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(SEALS.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _partition(name: str) -> dict[str, Any]:
    return next(item for item in _load()["partitions"] if item["partition"] == name)


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_pool_and_the_manifests_it_sealed_against() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["fitting_pool_sha256"] == _sha256(POOL.read_bytes())
    assert document["sealed_manifests_sha256"] == _sha256(SEALED_MANIFESTS.read_bytes())
    assert document["final_outcomes_inspected"] is False


def test_seven_hundred_and_twenty_records_over_the_two_open_partitions() -> None:
    document = _load()
    counts = document["counts"]
    assert counts["feature_records_sealed"] == 720
    assert counts["partitions_opened"] == ["training", "calibration"]
    assert _partition("training")["feature_records"] == 320
    assert _partition("calibration")["feature_records"] == 400


def test_the_backlog_count_is_reconciled_rather_than_met_or_ignored() -> None:
    """840 minus 720 is one final partition. Delivering 720 silently would read as a shortfall."""
    counts = _load()["counts"]
    assert counts["declared_in_the_backlog"] == 840
    assert counts["difference"] == counts["final_partition_slots_not_sealed"] == 120
    bundle = seal_d4_corpus()
    assert bundle.catalogues[CorrectionPartition.FINAL_A].candidate_slots == 120
    assert "does not open a final role" in counts["reading"]


def test_no_container_ran_and_no_observation_was_written() -> None:
    document = _load()
    assert document["containers_started"] == 0
    assert document["learned_observations_written"] == 0
    for name in ("training", "calibration"):
        chronology = _partition(name)["chronology"]
        assert chronology["outcomes_present_at_seal_time"] is False
        assert chronology["containers_started_by_this_command"] == 0
        # Zero, not null: null would mean the stream was never looked up.
        assert chronology["campaign_stream_version_before_the_seal"] == 0


def test_a_post_outcome_seal_was_attempted_for_each_partition_and_refused() -> None:
    refusals = _load()["refusals"]
    assert len(refusals) == 2
    for entry in refusals:
        assert entry["refused"] == "true"
        assert "strictly before every outcome" in entry["error"]
    assert {entry["action"] for entry in refusals} == {
        "seal training again with an outcome already in hand",
        "seal calibration again with an outcome already in hand",
    }


def test_each_seal_is_bound_to_the_catalogue_that_selected_its_groups() -> None:
    bundle = seal_d4_corpus()
    for name, partition in (
        ("training", CorrectionPartition.TRAINING),
        ("calibration", CorrectionPartition.CALIBRATION),
    ):
        row = _partition(name)
        catalogue = bundle.catalogues[partition]
        assert row["campaign_manifest_hash"] == catalogue.content_hash
        assert row["groups"] == len(catalogue.groups)
        assert row["feature_records"] == catalogue.candidate_slots


def test_the_bounds_were_fitted_on_fitting_and_reused() -> None:
    """Refitting on calibration carries calibration statistics into the encoder."""
    for name in ("training", "calibration"):
        assert _partition(name)["bounds_fitted_on"] == "training"


def test_every_vector_is_reproducible_from_its_source_alone() -> None:
    """The operative proof that no verdict entered the vector: re-encode and demand the hash."""
    for name in ("training", "calibration"):
        row = _partition(name)
        assert row["reencodes_identically_from_source_alone"] is True
        assert row["reserialises_identically"] is True
        assert row["stored_seal_time_preserved"] is True


def test_the_fitted_channels_are_the_frozen_allowlist() -> None:
    contract = CorrectionFeatureContractV2()
    document = _load()
    assert document["feature_contract_hash"] == contract.content_hash
    for name in ("training", "calibration"):
        envelope = _partition(name)["envelope"]
        assert envelope["fitted_channels"] == len(FITTED_FEATURE_V2_ALLOWLIST) == 390
        assert envelope["channels_are_the_frozen_allowlist_in_order"] is True
        assert envelope["every_record_carries_the_same_six_scalars_in_order"] is True
        assert tuple(envelope["scalar_channels"]) == FITTED_FEATURE_V2_SCALARS
        assert envelope["embedding_dimension"] == 384
        # The one channel whose name reads like a verdict, and what it actually is.
        assert "declared_verifier_capability_count" in envelope["scalar_channels"]
        assert "not a verdict" in envelope["declared_verifier_capability_count_reading"]


def test_no_two_candidates_encode_to_one_vector() -> None:
    """720 records that collapsed onto fewer vectors would be fewer decisions than they look."""
    for name, expected in (("training", 320), ("calibration", 400)):
        envelope = _partition(name)["envelope"]
        assert envelope["distinct_feature_vector_hashes"] == expected
        assert envelope["distinct_canonical_source_hashes"] == expected


def test_the_seal_carries_what_a_resume_needs() -> None:
    """A campaign that cannot find the bundle it sealed against re-mints every run identity."""
    for name, groups in (("training", 80), ("calibration", 100)):
        row = _partition(name)
        assert len(row["bundle_artifacts"]) == groups
        assert len(row["task_manifest_hashes"]) == groups
        assert len(row["member_hashes"]) == row["feature_records"]
        assert row["feature_seal_artifact_id"]
