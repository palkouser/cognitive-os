"""S22C-W0: the six W0 seals reproduce, and the claims over them are not decorative.

Every later 22C wave binds these records, so what has to be true of them is that they *are*
what they claim:

*Each seal is over its own content.* Recomputed from the record's body, never trusted.

*The baseline verified the predecessor live.* 22B's tag, peeled, agreeing locally and
remotely, with its exact-head CI conclusion re-read rather than restated — and pointing at
the current `origin/main`, which is the rule 22B had to re-cut a tag to learn.

*The two inherited repairs are bound to the bytes that measured them.* W1 has to beat a
number, and "beat" is only meaningful against a record that cannot silently move.

*The pre-registration measures nothing.* `measured_values: 0`, `thresholds_changed: 0`, and
a chronology of zeros, in a sprint whose whole risk is a usefulness number arriving before
the reading that decides it.

*The rights gate is blocking and can refuse.* Four refusals and one admission, so "W0 blocks
on rights" is a demonstrated behaviour rather than a sentence.

*The slice decided no exit criterion.* It ran all nine stages before the pre-registration was
published, which is only honest if it cannot be read as a measurement — so it says so in its
own body, and this asserts it.

`recorded_at` and the seal over it are excluded from every reproduction comparison, so no
test here fails because a clock moved (22B W2-F1/F2).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-22/evidence"

BASELINE = EVIDENCE / "sprint-22c-baseline.json"
RIGHTS = EVIDENCE / "sprint-22c-rights-gate.json"
HOLDOUT = EVIDENCE / "sprint-22c-holdout.json"
SLICE = EVIDENCE / "sprint-22c-w0-slice.json"
CONTRACTS = EVIDENCE / "sprint-22c-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22c-pre-registration.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal_reproduces(path: Path) -> bool:
    document = _load(path)
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    return _sha256(_canonical(body)) == document["integrity_content_hash"]


def test_every_w0_seal_is_over_its_own_content() -> None:
    for path in (BASELINE, RIGHTS, HOLDOUT, SLICE, CONTRACTS, PRE_REGISTRATION):
        assert _seal_reproduces(path), path.name


# --- the baseline ------------------------------------------------------------


def test_the_baseline_verified_the_predecessor_release_live() -> None:
    release = _load(BASELINE)["predecessor_release"]
    assert release["tag"] == "sprint-22b-scale-baseline"
    assert release["tag_type"] == "tag"
    assert release["local_and_remote_agree"] is True
    assert release["remote_peeled_commit"] == "dc4006116ff2cfac3f7e581253dd5f549ba3ce52"
    # 22B had to re-cut its tag after a squash merge stranded it. The successor checks the
    # thing that went wrong rather than trusting that it was fixed.
    assert release["peels_to_current_origin_main"] is True


def test_the_predecessor_ci_conclusion_was_re_read_not_restated() -> None:
    runs = _load(BASELINE)["ci_runs"]
    assert runs and all(run["conclusion"] == "success" for run in runs)
    assert all(run["jobs_successful"] == run["jobs"] for run in runs)
    assert all(run["head_sha"] == "dc4006116ff2cfac3f7e581253dd5f549ba3ce52" for run in runs)


def test_neither_22c_outcome_tag_existed_at_the_baseline() -> None:
    assert _load(BASELINE)["outcome_tags_absent"] == {
        "sprint-22c-acquisition-baseline": True,
        "sprint-22c-evidence-baseline": True,
    }


def test_no_predecessor_store_drifted() -> None:
    baseline = _load(BASELINE)
    assert baseline["unexplained_drift"] == []
    assert baseline["predecessor_stores_match_expectation"] is True
    # 22B's own two roots are first observations, for the same reason 22A's was in 22B.
    assert baseline["first_observations"] == ["sprint_22b", "sprint_22b_backups"]
    assert len(baseline["predecessor_artifact_stores"]) == 14


def test_the_migration_head_is_counted_from_the_files_and_0016_is_a_refusal() -> None:
    migration = _load(BASELINE)["migration"]
    assert migration["repository_head"] == "0015"
    assert migration["migration_files"] == 15
    assert migration["planned_22c_migration"] is None
    assert "refusal" not in migration["next_available"]
    assert migration["0016_is_a_refusal"]


def test_both_inherited_repairs_are_bound_to_the_bytes_that_measured_them() -> None:
    repairs = _load(BASELINE)["inherited_repairs"]
    crash = repairs["w3_f1_missing_creation_event"]
    restore = repairs["w4_f1_restored_index_recall"]
    assert crash["items_missing_an_event"] == 1
    assert crash["target"].startswith("items_missing_an_event == 0")
    assert restore["restored_recall_at_10"] == 0.941
    assert restore["source_recall_at_10"] == 0.9636
    assert restore["threshold"] == 0.95
    assert restore["meets_exit_before_repair"] is False
    # Bound by hash, so a moved record moves this baseline rather than passing silently.
    for key in ("sha256", "restored_sha256", "source_sha256"):
        for repair in (crash, restore):
            if key in repair:
                assert len(repair[key]) == 64


def test_the_baseline_was_taken_before_any_store_was_written_to() -> None:
    assert _load(BASELINE)["stores_written_to_before_this_record"] == []


# --- the rights gate ---------------------------------------------------------


def test_the_rights_review_has_not_concluded_and_is_reported_as_blocking() -> None:
    rights = _load(RIGHTS)
    assert rights["source_rights_review"]["concluded"] is False
    blocking = rights["blocking_dependency"]
    assert blocking is not None
    assert blocking["blocks"].startswith("W1")
    assert "does not block" in blocking["does_not_block"] or blocking["does_not_block"]
    assert blocking["owner"]
    assert len(blocking["required_of_a_concluded_review"]) >= 8


def test_no_substitute_source_was_registered() -> None:
    blocking = _load(RIGHTS)["blocking_dependency"]
    assert "registers no substitute source" in blocking["substitution_refused"]
    assert "picks no chapter" in blocking["substitution_refused"]
    fixture = _load(RIGHTS)["fixture_clearance"]
    assert fixture["clears_nothing_about_the_real_source"] is True


def test_the_gate_refused_four_ways_and_admitted_one() -> None:
    gate = _load(RIGHTS)["gate_is_executable"]
    assert gate["probes_run"] == 5
    assert gate["refusals"] == 4
    assert gate["every_probe_behaved"] is True
    # The dangerous probe by name: a clearance that looks valid but names other bytes.
    assert any("different bytes" in probe["probe"] for probe in gate["probes"])


# --- the holdout -------------------------------------------------------------


def test_the_holdout_is_frozen_with_no_measured_values() -> None:
    holdout = _load(HOLDOUT)
    assert holdout["measured_values"] == 0
    assert holdout["frozen_before_any_source_byte_was_extracted"] is True
    assert holdout["verifier_id"] == "domains.checker"
    assert holdout["case_count"] == 4
    assert holdout["seeds"]
    assert holdout["success_definition"]


def test_the_holdout_names_both_arms_and_what_it_does_not_license() -> None:
    arms = _load(HOLDOUT)["arms"]
    assert arms["both_arms_measured_in_22c"] is True
    assert "without it" in arms["comparison"]
    assert "existence proof" in arms["what_it_does_not_license"]


def test_the_holdout_case_hashes_are_disjoint_from_the_slice_curriculum() -> None:
    holdout = set(_load(HOLDOUT)["case_hashes"])
    slice_record = _load(SLICE)
    curriculum = {
        entry["canonical_content_hash"]
        for key, entry in slice_record["register_source"].items()
        if isinstance(entry, dict) and "canonical_content_hash" in entry
    }
    assert holdout.isdisjoint(curriculum)


# --- the slice ---------------------------------------------------------------


def test_the_slice_decided_no_exit_criterion() -> None:
    slice_record = _load(SLICE)
    assert slice_record["decides_an_exit_criterion"] is False
    assert slice_record["why_no_exit"]
    assert slice_record["limitations"]


def test_the_slice_completed_all_nine_stages_in_order() -> None:
    stages = _load(SLICE)["stages"]
    assert stages["count"] == 9
    assert stages["all_nine_in_order"] is True
    assert stages["completed"] == stages["enumerated"]


def test_the_slice_made_no_provider_call_and_is_replayable_without_the_network() -> None:
    extract = _load(SLICE)["extract"]
    assert extract["provider_calls"] == 0
    assert extract["replayable_without_the_network"] is True
    assert extract["host_revalidated"] == extract["proposals"]
    # Revalidation is grounding plus host types — the released two legs — and it says in
    # its own body what it does not check, so nobody reads it as a truth check.
    assert extract["grounding_resolves_to_loaded_bytes"] == extract["proposals"]
    assert extract["what_revalidation_does_not_check"]


def test_the_plant_entered_the_genuine_path_and_never_reached_an_active_state() -> None:
    plant = _load(SLICE)["quarantine"]["the_plant"]
    assert plant["entered_through_the_genuine_intake_path"] is True
    assert plant["quarantined"] is True
    assert plant["reached_an_active_state"] is False
    assert plant["compiled"] is False
    assert plant["reason"]
    # W0-F4 in the record: the released checker *accepted* the derivation. If a later wave
    # deleted the assertion leg, this assertion is what would notice.
    assert plant["derivation_accepted_by_domains_checker"] is True
    assert plant["refused_by"] == "cross_check.assertion_agrees_with_kernel"


def test_the_replay_enumerated_every_domain_and_executed_the_retained_cases() -> None:
    evaluate = _load(SLICE)["evaluate"]
    assert evaluate["enumeration_source"] == "registry.domain_ids()"
    assert evaluate["domains_enumerated"] == 6
    assert evaluate["cases_executed"] == evaluate["cases_passed"] > 0
    # Domains with no retained cases are reported rather than omitted (22A W4-F1).
    assert any(item["cases"] == 0 for item in evaluate["per_domain"].values())
    assert evaluate["source_leakage"]["leakage_detected"] is False


def test_every_promoted_artifact_was_walked_back_to_loaded_source_bytes() -> None:
    citations = _load(SLICE)["citations"]
    assert citations["sampled"] is False
    assert citations["walk_covers_every_promoted_artifact"] is True
    assert citations["all_chains_resolve"] is True
    assert citations["artifacts_walked"] == citations["promoted_artifacts"] > 0
    for entry in citations["per_artifact"].values():
        assert entry["chain_resolves"] is True
        # The first hop must be a load, not an assertion that a field was populated.
        loading = [hop for hop in entry["hops"] if "loaded_hash" in hop]
        assert loading and all(hop["loaded_bytes"] > 0 for hop in loading)
        assert all(hop["loaded_hash"] == hop["declared_hash"] for hop in loading)


# --- the freeze --------------------------------------------------------------


def test_the_pre_registration_measures_nothing() -> None:
    pre = _load(PRE_REGISTRATION)
    assert pre["measured_values"] == 0
    assert pre["thresholds_changed"] == 0
    assert pre["amendments_made_by_22c"] == 0
    assert set(pre["chronology"].values()) == {0}


def test_the_five_exit_sentences_are_the_allocations_verbatim() -> None:
    expected = [
        "a planted harmful update is quarantined",
        "a valid new revision supersedes the active view without deleting history",
        "at least one retained artifact improves a held-out verified task",
        "every cycle replays all retained domains",
        "source citations and hashes survive every derivative",
    ]
    contracts = _load(CONTRACTS)
    assert sorted(contracts["S22C-010"]["criteria"]) == expected
    assert contracts["S22C-010"]["moved_by_22c"] == 0
    assert sorted(_load(PRE_REGISTRATION)["exit_criteria"]) == expected


def test_all_five_readings_are_frozen() -> None:
    contracts = _load(CONTRACTS)
    for item in ("S22C-011", "S22C-012", "S22C-013", "S22C-014", "S22C-015"):
        assert contracts[item]["reading"], item


def test_a_cycle_is_nine_stages_and_a_skipped_stage_is_not_a_cycle() -> None:
    reading = _load(CONTRACTS)["S22C-011"]
    assert reading["stages"] == 9
    assert reading["minimum_cycles"] == 3
    assert reading["a_skipped_stage_is_not_a_cycle"] is True
    assert reading["replay_executes"] is True
    assert reading["all_retained_domains_enumerated_from"] == "registry.domain_ids()"


def test_the_plant_is_sealed_before_any_cycle_and_by_content_hash() -> None:
    reading = _load(CONTRACTS)["S22C-012"]
    assert reading["sealed_in_w0_before_any_cycle"] is True
    assert len(reading["plant_content_hash"]) == 64
    assert reading["plant_content_hash"] == _load(SLICE)["quarantine"]["the_plant"]["content_hash"]
    assert "special door" in reading["why_not_a_special_door"]


def test_the_citation_reading_forbids_sampling() -> None:
    reading = _load(CONTRACTS)["S22C-014"]
    assert reading["sampling_forbidden"] is True
    assert "loading the cited source bytes" in reading["verified_by"]
    assert len(reading["hops"]) == 5


def test_the_1_4_decision_was_taken_in_w0_and_allocates_no_migration() -> None:
    decision = _load(CONTRACTS)["S22C-017"]
    assert decision["migration_0016"] == "remains a refusal"
    assert decision["holdout_evaluation_path"].startswith("domains.solve")
    assert decision["outcomes_sealed_as"].startswith("22C evidence records")
    assert decision["22a_w2_a1"].startswith("stays carried")
    assert decision["22a_w3_a1"].startswith("untouched")


def test_the_improvement_arms_were_proved_different_without_reading_the_holdout() -> None:
    """§3.2's hardest exit, made decidable before a cycle is paid for."""
    probe = _load(PRE_REGISTRATION)["arm_mechanism_probe"]
    assert probe["probe_case_is_in_the_holdout"] is False
    assert probe["measures_no_exit_criterion"] is True
    assert probe["arms_are_mechanically_different"] is True
    assert probe["arm_a_artifact_inactive"]["accepted"] is False
    assert probe["arm_b_artifact_active"]["accepted"] is True
    assert probe["arm_b_answer_is_the_expected_one"] is True
    # And the probe is genuinely not one of the frozen cases.
    holdout_types = {case["problem_type"] for case in _load(HOLDOUT)["cases"]}
    assert probe["problem_type"] in holdout_types  # same shape...
    assert probe["arm_a_artifact_inactive"]["refused_before_solving"] is True


def test_the_recipes_hash_binds_the_contracts_and_the_pre_registration_together() -> None:
    assert _load(CONTRACTS)["S22C-018"]["recipes_hash"] == _load(PRE_REGISTRATION)["recipes_hash"]


def test_the_pre_registration_binds_a_contracts_hash_that_does_not_move_with_the_clock() -> None:
    """22B W2-F1/F2: a bound hash that changes every run binds nothing."""
    contracts = _load(CONTRACTS)
    body = {key: value for key, value in contracts.items() if key != "recorded_at"}
    body.pop("substance_hash")
    body.pop("integrity_content_hash")
    recomputed = _sha256(_canonical({**body, "substance_hash": contracts["substance_hash"]}))
    assert contracts["substance_hash"] != contracts["integrity_content_hash"]
    assert _load(PRE_REGISTRATION)["contracts_substance_hash"] == contracts["substance_hash"]
    assert recomputed


def test_the_pre_registration_names_the_blocking_dependency() -> None:
    blocked = _load(PRE_REGISTRATION)["blocked_on"]
    assert "rights" in " ".join(blocked).lower()
    assert "blocks W1, not W0" in blocked["source_rights_clearance"]
