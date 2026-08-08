"""S21D4-033: the vertical-slice record still says what it said, and still spends nothing.

Not a second copy of `vertical_slice_d4.py`'s own checks. These are the ways a spine proof
stops being one after it is written: the fixture group quietly acquiring a role, a refusal
recorded without ever having been raised, and a replay reported by a pass that never ran.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cognitive_os.coding.reality_fixture_spec_d4 import D4_FIXTURE_SPEC
from cognitive_os.coding.reality_tasks import d4_templates, template
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus
from cognitive_os.learning.correction_protocol import CorrectionPartition

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
SLICE = EVIDENCE / "sprint-21d4-vertical-slice.json"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"


def _load() -> dict[str, Any]:
    return json.loads(SLICE.read_text())


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_the_record_reproduces_its_integrity_hash() -> None:
    document = _load()
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    canonical = json.dumps(body, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert _sha256(canonical) == document["integrity_content_hash"]


def test_the_record_is_bound_to_the_pre_registration() -> None:
    document = _load()
    assert document["pre_registration_sha256"] == _sha256(PRE_REGISTRATION.read_bytes())
    assert document["final_outcomes_inspected"] is False


def test_the_fixture_group_is_in_no_role_now_either() -> None:
    """The record checked this when it ran. A role added since would make it a stale claim."""
    bundle = seal_d4_corpus()
    boundary = _load()["role_boundary"]
    assert boundary["checked_against_seal"] == bundle.seal.content_hash
    for partition in CorrectionPartition:
        if partition in bundle.catalogues:
            assert D4_FIXTURE_SPEC.repository_group not in bundle.groups_of(partition)
    assert D4_FIXTURE_SPEC.repository_group not in bundle.retrieval_groups
    assert boundary["roles_containing_this_group"] == []
    assert boundary["in_any_scored_role"] is False
    assert boundary["calibration_cases_spent"] == 0
    assert boundary["final_members_spent"] == 0
    assert boundary["canary_members_spent"] == 0
    assert boundary["retrieval_judgements_spent"] == 0


def test_the_fixture_is_registered_but_is_not_a_calibration_template() -> None:
    """It has to be addressable by the runner and countable by nobody."""
    assert D4_FIXTURE_SPEC.template_id in d4_templates()
    assert template(D4_FIXTURE_SPEC.template_id).repository_group == "d4-fixture-wrap-words"
    calibration = seal_d4_corpus().catalogues[CorrectionPartition.CALIBRATION]
    assert D4_FIXTURE_SPEC.template_id not in {group.template_id for group in calibration.groups}


def test_the_slice_ran_containers_and_the_replay_ran_none() -> None:
    """Either count alone reads as the other: five and zero is the claim, not five or zero."""
    document = _load()
    execution = document["execution"]
    restart = document["restart"]
    assert execution["sandboxed"] is True
    assert execution["candidates_executed"] == 4
    assert execution["containers_started"] == 5
    assert restart["containers_started_on_the_replay"] == 0
    assert restart["runs_replayed"] == 5
    assert restart["run_identities_resolved_from_the_receipt"] == 5
    assert restart["replayed_outcomes_are_the_recorded_ones"] is True
    assert restart["task_manifest_hash_reproduced"] is True
    assert restart["dataset_record_reproduced"] is True
    assert restart["receipt_effective_remainder"] == []


def test_the_verifier_decided_every_label_after_the_seal() -> None:
    execution = _load()["execution"]
    assert execution["verifier_decided_every_label"] is True
    assert execution["every_feature_record_precedes_its_outcome"] is True
    assert execution["baseline_passed_hidden_verification"] is False
    # The fixture declares two correct repairs and two partial ones.
    assert execution["accepted_candidates"] == 2
    assert execution["observations_projected"] == 4


def test_the_dataset_is_explicit_and_carries_no_governed_run() -> None:
    dataset = _load()["dataset"]
    assert dataset["identity_revision"] == 3
    assert dataset["real_governed_runs"] == 0
    assert dataset["provenance_counts"] == {"self_play": 4}
    assert dataset["store_wide_selection"] is False
    assert dataset["latest_seal_selection"] is False
    assert dataset["rebuilt_identically"] is True
    assert dataset["fitted_columns"] == 390
    assert dataset["every_scan_ran"] >= 11
    assert all(scan["passed"] is not None for scan in dataset["scans"])


def test_the_ranking_ran_against_a_derived_point_not_a_constant() -> None:
    point = _load()["ranking"]["operating_point"]
    assert point["split"] == "calibration"
    assert point["is_the_d4_operating_point"] is False
    assert point["reproduced_after_a_second_derivation"] is True
    assert point["independent_decisions"] == point["nominal_decisions"] == 4
    assert len(point["scored_decisions"]) == 4
    # A point that exists must name its threshold and its cost; one that does not must name
    # neither. Anything else is a threshold nobody derived.
    if point["zero_error_point_exists"]:
        assert point["coverage"] is not None
        assert point["zero_error_upper_bound_95"] is not None
    else:
        assert point["threshold"] is None
        assert point["coverage"] is None
        assert point["admitted_decisions"] == 0
    assert point["reading"]


def test_every_refusal_names_the_error_it_actually_raised() -> None:
    """A recorded refusal with no exception text is a call nobody made."""
    document = _load()
    refusals = document["artifact"]["refusals"] + document["capabilities"]["refusals"]
    assert len(refusals) == 8
    for entry in refusals:
        assert entry["refused"] == "true"
        assert ":" in entry["error"]
        assert entry["error"].split(":")[0].endswith("Error") or entry["error"].startswith(
            "ValueError"
        )
    # The three artifact refusals must hit three different gates, or two of them prove nothing.
    messages = [entry["error"] for entry in document["artifact"]["refusals"]]
    assert any("this capability authorises" in item for item in messages)
    assert any("not JSON" in item for item in messages)
    assert any("above the" in item and "byte bound" in item for item in messages)


def test_the_final_and_retrieval_splits_are_refused_by_name() -> None:
    actions = {entry["action"] for entry in _load()["capabilities"]["refusals"]}
    assert "derive a threshold from the final A split" in actions
    assert "derive a threshold from the final B split" in actions
    assert "derive a threshold from the retrieval split" in actions


def test_the_artifact_reloaded_into_the_same_ranker() -> None:
    artifact = _load()["artifact"]
    assert artifact["store_returned_the_bytes_written"] is True
    assert artifact["reload_reproduced_the_payload"] is True
    assert artifact["reload_reproduced_the_ranking"] is True
    assert artifact["feature_channels"] == 390
    # The slice is a wiring proof and the bytes it writes have to say so.
    assert artifact["declared_limitations"]


def test_the_defect_ledger_keeps_what_this_wave_found() -> None:
    ledger = _load()["authoring_defect_ledger"]
    identifiers = {entry["id"] for entry in ledger}
    assert {"W2-D7", "W2-D8"} <= identifiers
    threshold = next(entry for entry in ledger if entry["id"] == "W2-D7")
    assert threshold["contract_changed"] is False
    assert threshold["d4_threshold_derivations_before_the_fix"] == 0
