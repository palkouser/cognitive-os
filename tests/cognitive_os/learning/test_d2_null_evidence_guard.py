"""S21D2-085b: the published D2 evidence must keep saying what the stop decided.

085 splits. `085a` gave the branch a CI lane for the correction-ranking spine in W2. This is
`085b`, which the wave plan reserved for final-evidence coverage after S21D2-067 — and D2
stopped at S21D2-049 with a null, so there is no final evidence to cover. What replaces it is
not less work but a different guarantee: that the evidence files this sprint ships never come
to claim something the stop closed.

That guarantee needs a test rather than a review, because the failure mode is editing. A file
gains a field, a later sprint copies a template, a number is filled in "for completeness" —
and a record that said "not opened" starts saying "zero", which reads as a measurement. Every
assertion here is over the committed evidence, offline, with no database and no credentials.

The one thing this file must never become is a test that passes because the evidence is
missing. Each class asserts the file exists and is loadable before it asserts anything about
its contents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

EVIDENCE = Path(__file__).resolve().parents[3] / "docs" / "sprints" / "sprint-21" / "evidence"
SELECTION = EVIDENCE / "sprint-21d2-learner-selection.json"
CAMPAIGN = EVIDENCE / "sprint-21d2-self-play-campaign.json"
OPERATIONS = EVIDENCE / "sprint-21d2-operations.json"


def _load(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"{path.name} is not present; the guard has nothing to guard"
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


class TestTheSelectionStaysANull:
    def test_no_candidate_was_selected(self) -> None:
        selection = _load(SELECTION)["candidate_selection"]

        assert selection["selected"] is False
        assert selection["learner_kind"] is None
        assert selection["null_reason"]

    def test_the_null_never_authorises_final_access(self) -> None:
        """The fourth one-way door. A null closes it and cannot be edited into opening it."""
        assert _load(SELECTION)["candidate_selection"]["authorises_final_access"] is False

    def test_the_continuation_stopped_rather_than_opening_a_later_rung(self) -> None:
        continuation = _load(SELECTION)["continuation"]

        assert continuation["outcome"] == "fail_and_stop"
        assert continuation["later_rungs_opened"] == []

    def test_the_failure_kind_is_one_that_does_not_authorise_a_parametric_rung(self) -> None:
        from cognitive_os.learning.knn_calibration import FailureKind

        kind = FailureKind(_load(SELECTION)["continuation"]["failure_kind"])

        assert not kind.authorises_parametric_continuation


class TestNoFinalOrLifecycleEvidenceIsClaimed:
    def test_no_final_or_canary_body_was_opened(self) -> None:
        provenance = _load(CAMPAIGN)["provenance"]

        assert provenance["final_batch_a_opened"] is False
        assert provenance["final_batch_b_opened"] is False
        assert provenance["canary_opened"] is False

    def test_no_real_governed_run_was_written(self) -> None:
        """The inherited constraint with no expiry: C3 and D1 outcomes are never trained on."""
        assert _load(CAMPAIGN)["provenance"]["real_governed_run_observations_written"] == 0

    @pytest.mark.parametrize(
        "field",
        [
            "learned_components",
            "learned_component_revisions",
            "learned_evidence_records",
            "learned_activation_approvals",
            "learned_activation_history",
        ],
    )
    def test_the_restored_store_holds_no_lifecycle_object(self, field: str) -> None:
        counts = _load(OPERATIONS)["restore"]["negative_release_state"]["counts"]

        assert counts[field] == 0


class TestTheNotOpenedClassesStayBound:
    def test_every_not_opened_check_names_the_decision_that_closed_it(self) -> None:
        report = _load(OPERATIONS)["restore"]["restored_integrity_report"]
        stop = _load(SELECTION)["candidate_selection"]["content_hash"]
        not_opened = report["not_opened"]

        assert not_opened, "a null path with no not-opened class means the report stopped saying so"
        assert set(not_opened.values()) == {stop}

    def test_a_not_opened_class_is_never_counted_as_a_pass(self) -> None:
        """`healthy` is decided by failures. A class nobody looked at decides nothing."""
        report = _load(OPERATIONS)["restore"]["restored_integrity_report"]
        by_name = {check["name"]: check for check in report["checks"]}

        for name in report["not_opened"]:
            assert by_name[name]["severity"] == "not_opened"
            assert by_name[name]["bound_hash"]

    def test_the_two_closed_classes_are_the_two_the_stop_closed(self) -> None:
        report = _load(OPERATIONS)["restore"]["restored_integrity_report"]

        assert set(report["not_opened"]) == {
            "the_correction_surface_has_a_sound_activation_state",
            "every_active_component_resolves_to_the_model_it_declares",
        }


class TestTheCiLaneStillRunsWhatTheEvidenceSays:
    """S21D2-085b's own guard: a recorded CI step that no longer exists is a false claim."""

    def test_every_recorded_step_is_still_in_the_workflow(self) -> None:
        import yaml

        coverage = _load(OPERATIONS)["ci_coverage"]
        root = Path(__file__).resolve().parents[3]
        workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text("utf-8"))
        steps = {
            step.get("name"): " ".join(step.get("run", "").split())
            for step in workflow["jobs"][coverage["lane"]]["steps"]
        }

        for name, command in coverage["steps_added_and_their_exact_local_equivalents"].items():
            assert steps.get(name) == command


class TestTheOperationsEvidenceStillProvesWhatItClaims:
    def test_every_corruption_case_failed_closed(self) -> None:
        matrix = _load(OPERATIONS)["corruption_matrix"]

        assert matrix
        open_cases = [row["case"] for row in matrix if not row["observed"].get("failed_closed")]
        assert open_cases == []

    def test_the_restore_reproduced_the_source_exactly(self) -> None:
        restore = _load(OPERATIONS)["restore"]

        assert restore["counts_match"]
        assert restore["hashed_rows_match"]
        assert restore["integrity_report_matches"]
        assert all(restore["resume_inputs_match"].values())
        assert restore["artifact_bytes"]["content_hash_mismatches"] == []

    def test_no_inherited_store_was_written_to(self) -> None:
        assert _load(OPERATIONS)["isolation"]["inherited_stores_unchanged"] is True
        assert _load(OPERATIONS)["isolation"]["d2_evidence_pair_unchanged"] is True
