"""S21D4-038: forty transformations that repeat twenty decisions and add none.

The record has to survive one specific kind of reading: "everything was zero, so everything is
fine". Zero changed vectors is also what a canonicaliser that erased all meaning would produce,
and zero label changes is also what a harness that never ran anything would produce. So the
tests here check the zeros *and* the controls that make the zeros mean something.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.learning.correction_catalogue_d4 import (
    D4_CASES,
    INVARIANCE_SAMPLE_GROUPS,
    invariance_sample_groups,
    seal_d4_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
REGRESSION = EVIDENCE / "sprint-21d4-invariance-regression.json"
SEALED_MANIFESTS = EVIDENCE / "sprint-21d4-sealed-manifests.json"
CALIBRATION = EVIDENCE / "sprint-21d4-calibration-campaign.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(REGRESSION.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_seal_and_the_campaign_it_compares_against() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["sealed_manifests_sha256"] == _sha256(SEALED_MANIFESTS.read_bytes())
    assert document["calibration_campaign_sha256"] == _sha256(CALIBRATION.read_bytes())
    assert document["final_outcomes_inspected"] is False


def test_the_sample_is_the_one_the_seal_declared() -> None:
    """Choosing twenty groups after seeing the bodies is not a pre-registered sample."""
    bundle = seal_d4_corpus()
    declared = invariance_sample_groups(bundle.catalogues[CorrectionPartition.CALIBRATION])
    submanifest = _load()["submanifest"]
    assert submanifest["hash"] == bundle.invariance_transformations.content_hash
    assert submanifest["source_groups"] == INVARIANCE_SAMPLE_GROUPS == 20
    assert list(submanifest["sample_groups_named"]) == list(declared)
    assert submanifest["sample_matches_the_seal"] is True
    assert submanifest["nominal_cases"] == submanifest["applicable_cases"] == 40
    assert submanifest["not_applicable"] == []
    assert submanifest["cases_by_name"] == dict.fromkeys(D4_CASES, 20)


def test_the_transformed_set_adds_no_independent_decision() -> None:
    """The number S21D4-032 sealed as zero, now executed rather than claimed."""
    independence = _load()["independence"]
    seal = seal_d4_corpus().seal
    assert independence["transformed_decisions"] == seal.invariance_transformed_decisions == 40
    assert independence["independent_decisions"] == seal.invariance_independent_decisions == 0
    assert independence["candidate_vectors_compared"] == 160
    assert independence["vectors_unchanged"] == 160
    assert independence["vectors_changed"] == 0
    assert independence["changed"] == []


def test_the_census_counts_the_replicas_as_replicas() -> None:
    """80 clean vectors, 160 transformed copies of them, and a census that says so."""
    census = _load()["independence"]["census_over_clean_and_transformed"]
    assert census["nominal_decisions"] == 320
    assert census["independent_decisions"] == 80
    assert census["replicated_decisions"] == 240
    assert census["rate_denominator"] == "independent_decisions"
    assert _load()["independence"]["distinct_clean_vectors"] == 80


def test_the_verifier_did_not_change_its_mind_and_actually_ran() -> None:
    """Zero label changes means nothing if nothing was executed."""
    verifier = _load()["verifier"]
    assert verifier["candidate_outcomes_executed"] == 160
    assert verifier["label_changes"] == 0
    assert verifier["changed"] == []
    assert verifier["governed_runs"] == 0
    # Half the corpus is a correct repair, so a run that executed nothing would show zero here.
    assert 0 < verifier["accepted"] < 160


def test_the_first_action_did_not_move() -> None:
    first = _load()["first_action"]
    assert first["cases_compared"] == 40
    assert first["changes"] == 0
    assert first["changed"] == []


def test_the_transformed_features_were_sealed_before_they_ran() -> None:
    chronology = _load()["chronology"]
    assert chronology["every_transformed_seal_precedes_its_execution"] is True
    assert chronology["features_sealed_at"] < chronology["first_transformed_execution_at"]
    assert "never on the transformed set" in chronology["bounds_fitted_on"]


def test_the_semantic_control_stops_the_vacuous_reading() -> None:
    """A canonicaliser mapping every program to one value would pass invariance perfectly."""
    control = _load()["semantic_mutation_control"]
    assert control["all_changed_the_canonical_representation"] is True
    assert len(control["mutations"]) >= 4
    for mutation in control["mutations"]:
        assert mutation["canonical_hash_changed"] is True
    # Four mutations plus the probe must be five distinct canonical forms, not one repeated.
    assert control["distinct_canonical_hashes"] == len(control["mutations"]) + 1


def test_nothing_transformed_entered_a_dataset() -> None:
    document = _load()
    assert document["entered_any_dataset"] is False
    assert document["fitted"] is False
    assert document["final_or_canary_access"] == 0
    assert document["stops"] == []


def test_the_batch_dependence_finding_is_measured_not_asserted() -> None:
    """W2-D9 is the defect this run exists to have found; a ledger entry alone would not do."""
    findings = {entry["id"]: entry for entry in _load()["findings"]}
    assert {"W2-D9", "W2-D10"} <= set(findings)
    measured = findings["W2-D9"]["measured"]
    assert measured["identical"] is False
    assert measured["hash_changes"] is True
    assert float(measured["maximum_absolute_difference"]) > 0
    assert findings["W2-D10"]["affects_any_number"] is False
    assert findings["W2-D10"]["sealed_record_amended_not_edited"] is True
