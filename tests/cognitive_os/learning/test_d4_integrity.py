"""S21D4-081: one seeded violation per class, the four states, and the twelfth class.

The report is only worth running if each class can actually fail, so every class here is driven
twice: once against the committed evidence, and once against a copy of it with exactly one thing
broken. A class that cannot be made to fail is a class that proves nothing.

The twelfth class gets a fourth test the other eleven do not need. `decision_independence` scans
for denominators, and the way a scan fails silently is by finding none — so it is driven against
an evidence directory with every count removed, and must report `failed` rather than the `clean`
that an empty scan would otherwise produce.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.learning.correction_protocol import CorrectionFeatureContractV2
from cognitive_os.learning.integrity_d4 import (
    D4_INTEGRITY_CLASSES,
    D4IntegrityState,
    d4_integrity,
    path_and_size_fingerprint,
)

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
DATA_ROOT = Path("/home/palkouser/projekt/cognitive-os-data")


@pytest.fixture
def committed(tmp_path: Path) -> Path:
    """A writable copy of the committed evidence, so a seeded violation damages nothing."""
    target = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, target)
    return target


def _edit(directory: Path, name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = directory / name
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(directory: Path, name: str, **kwargs: Any) -> D4IntegrityState:
    report = d4_integrity(directory, **kwargs)
    return next(item.state for item in report.classes if item.name == name)


class TestTheCommittedEvidence:
    def test_every_class_is_covered_exactly_once_and_in_order(self) -> None:
        report = d4_integrity(EVIDENCE)

        assert tuple(item.name for item in report.classes) == D4_INTEGRITY_CLASSES
        assert len(set(D4_INTEGRITY_CLASSES)) == 12
        assert D4_INTEGRITY_CLASSES[-1] == "decision_independence"

    def test_nothing_fails_and_the_report_says_which_classes_it_could_not_check(self) -> None:
        report = d4_integrity(EVIDENCE)

        assert report.failed == ()
        assert report.healthy
        assert set(report.warnings) == {"artifact_bytes", "isolation"}
        assert report.not_opened == ("lifecycle",)

    def test_the_lifecycle_class_is_not_opened_rather_than_clean(self) -> None:
        """It is a decision bound to a stop hash, not a class that happened to pass."""
        lifecycle = next(
            item for item in d4_integrity(EVIDENCE).classes if item.name == "lifecycle"
        )

        assert lifecycle.state is D4IntegrityState.NOT_OPENED
        assert "dependent tasks bound to stop" in lifecycle.detail

    def test_the_new_class_counted_something(self) -> None:
        """A denominator check reporting clean over zero denominators is worth nothing."""
        independence = next(
            item for item in d4_integrity(EVIDENCE).classes if item.name == "decision_independence"
        )

        assert independence.state is D4IntegrityState.CLEAN
        assert "independent_decisions" in independence.detail
        assert len(independence.evidence) > 1


class TestOneSeededViolationPerClass:
    def test_a_dataset_that_does_not_rebuild_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-snapshots.json",
            lambda d: d["datasets"][0].update(rebuilt_identically=False),
        )

        assert _state(committed, "explicit_member_selection") is D4IntegrityState.FAILED

    def test_a_contradicted_receipt_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-calibration-campaign.json",
            lambda d: d["resume"].update(receipt_is_resumable=False),
        )

        assert _state(committed, "duplicate_executions_or_seals") is D4IntegrityState.FAILED

    def test_a_replay_that_started_a_container_is_caught(self, committed: Path) -> None:
        """A resume that re-executed work is a duplicate execution, not a resume."""
        _edit(
            committed,
            "sprint-21d4-self-play-campaign.json",
            lambda d: d["resume"].update(containers_started_on_the_replay=1),
        )

        assert _state(committed, "duplicate_executions_or_seals") is D4IntegrityState.FAILED

    def test_evidence_bound_to_other_pre_registration_bytes_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d4-learner-selection.json",
            lambda d: d.update(pre_registration_sha256="9" * 64),
        )

        assert _state(committed, "chronology") is D4IntegrityState.FAILED

    def test_a_contract_record_naming_a_different_feature_hash_is_caught(
        self, committed: Path
    ) -> None:
        """Seeded as drift rather than as deletion.

        Emptying the `contracts` block does not seed anything: the frozen hash appears in the
        record's `unchanged_from_d3` block too, and the check reads the whole document at any
        depth. The failure this class exists for is an encoder whose contract no longer hashes
        to what was frozen, so every occurrence is replaced rather than one removed.
        """
        path = committed / "sprint-21d4-contracts.json"
        declared = CorrectionFeatureContractV2().content_hash
        text = path.read_text(encoding="utf-8")
        assert text.count(declared) >= 1
        path.write_text(text.replace(declared, "0" * 64), encoding="utf-8")

        assert _state(committed, "feature_schema") is D4IntegrityState.FAILED

    def test_a_matrix_that_scanned_fewer_dimensions_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-snapshots.json",
            lambda d: d["fitted_matrix"].update(fitted_dimensions=6),
        )

        assert _state(committed, "matrix_embedding_scans") is D4IntegrityState.FAILED

    def test_a_failed_scan_is_caught_even_when_the_dimensions_are_right(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d4-snapshots.json",
            lambda d: d["scans"].update(failed=["no_forbidden_field_reaches_the_matrix"]),
        )

        assert _state(committed, "matrix_embedding_scans") is D4IntegrityState.FAILED

    def test_transformed_cases_counted_as_new_decisions_are_caught(self, committed: Path) -> None:
        """D3's collapse, seeded: forty transformed decisions reported as forty distinct ones."""
        _edit(
            committed,
            "sprint-21d4-invariance-regression.json",
            lambda d: d["independence"]["census_over_clean_and_transformed"].update(
                nominal_decisions=320, independent_decisions=320, replicated_decisions=0
            ),
        )

        assert _state(committed, "ood_units") is D4IntegrityState.FAILED

    def test_a_file_claiming_it_inspected_a_final_outcome_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-retrieval-holdout-result.json",
            lambda d: d.update(final_outcomes_inspected=True),
        )

        assert _state(committed, "holdout_access") is D4IntegrityState.FAILED

    def test_a_second_holdout_execution_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-retrieval-holdout-result.json",
            lambda d: d.update(executions=2),
        )

        assert _state(committed, "retrieval_one_read") is D4IntegrityState.FAILED

    def test_an_alternative_reopened_after_the_negative_holdout_is_caught(
        self, committed: Path
    ) -> None:
        """Reading the holdout once and then tuning against it is the same failure, later."""
        _edit(
            committed,
            "sprint-21d4-retrieval-decision.json",
            lambda d: d["no_alternative_opened"].update(fusion_variants=3),
        )

        assert _state(committed, "retrieval_one_read") is D4IntegrityState.FAILED

    def test_a_blob_that_does_not_hash_to_its_name_is_caught(self, committed: Path) -> None:
        assert (
            _state(committed, "artifact_bytes", blob_hashes={"a" * 64: "b" * 64})
            is D4IntegrityState.FAILED
        )

    def test_a_declared_blob_with_no_bytes_is_caught(self, committed: Path) -> None:
        """W7-A3's shape: rehashing only the files that exist calls a partial store clean."""
        assert (
            _state(committed, "artifact_bytes", blob_hashes={"a" * 64: None})
            is D4IntegrityState.FAILED
        )

    def test_a_checkpoint_claiming_authorised_access_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-pre-final-checkpoint.json",
            lambda d: d["decision"].update(authorised=True),
        )

        assert _state(committed, "lifecycle") is D4IntegrityState.FAILED

    def test_a_not_opened_map_with_two_stop_hashes_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-pre-final-checkpoint.json",
            lambda d: d["not_opened"][0].update(stop_hash="0" * 64),
        )

        assert _state(committed, "lifecycle") is D4IntegrityState.FAILED

    def test_a_moved_predecessor_fingerprint_is_caught(self, committed: Path) -> None:
        assert (
            _state(committed, "isolation", predecessor_fingerprints={"sprint_21d3": "0" * 64})
            is D4IntegrityState.FAILED
        )

    def test_a_rate_over_a_nominal_denominator_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-seal-resume.json",
            lambda d: d["partitions"][0]["census"].update(rate_denominator="nominal_decisions"),
        )

        assert _state(committed, "decision_independence") is D4IntegrityState.FAILED

    def test_a_census_that_does_not_add_up_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-d3-grid-replay.json",
            lambda d: d["per_setting"][0]["new"]["census"].update(replicated_decisions=7),
        )

        assert _state(committed, "decision_independence") is D4IntegrityState.FAILED

    def test_more_distinct_decisions_than_counted_ones_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d4-learner-selection.json",
            lambda d: d["cells"][0].update(independent_decisions=1000),
        )

        assert _state(committed, "decision_independence") is D4IntegrityState.FAILED


class TestAClassNobodyCheckedIsNeverAPass:
    @pytest.mark.parametrize(
        ("name", "kwargs"),
        [("artifact_bytes", {}), ("isolation", {})],
    )
    def test_the_two_optional_authorities_warn_rather_than_pass(
        self, name: str, kwargs: dict[str, Any]
    ) -> None:
        assert _state(EVIDENCE, name, **kwargs) is D4IntegrityState.WARNING

    def test_an_opened_store_holding_nothing_fails_rather_than_warns(self) -> None:
        """`None` is "not checked"; an empty mapping is "checked, and it is empty"."""
        assert _state(EVIDENCE, "artifact_bytes", blob_hashes={}) is D4IntegrityState.FAILED

    def test_a_denominator_scan_that_found_nothing_fails(self, tmp_path: Path) -> None:
        """The twelfth class's own vacuity guard, which the other eleven do not need."""
        empty = tmp_path / "evidence"
        empty.mkdir()
        (empty / "sprint-21d4-pre-registration.json").write_text(
            json.dumps({"recorded_at": "2026-08-06T00:00:00Z"}), encoding="utf-8"
        )

        assert _state(empty, "decision_independence") is D4IntegrityState.FAILED


class TestAStoredPassWithoutItsEvidenceFailsClosed:
    @pytest.mark.parametrize(
        ("name", "file"),
        [
            ("explicit_member_selection", "sprint-21d4-snapshots.json"),
            ("duplicate_executions_or_seals", "sprint-21d4-calibration-campaign.json"),
            ("chronology", "sprint-21d4-pre-registration.json"),
            ("feature_schema", "sprint-21d4-contracts.json"),
            ("matrix_embedding_scans", "sprint-21d4-snapshots.json"),
            ("ood_units", "sprint-21d4-invariance-regression.json"),
            ("retrieval_one_read", "sprint-21d4-retrieval-decision.json"),
            ("lifecycle", "sprint-21d4-pre-final-checkpoint.json"),
            ("isolation", "sprint-21d4-baseline.json"),
        ],
    )
    def test_deleting_the_file_a_class_reads_makes_it_failed(
        self, committed: Path, name: str, file: str
    ) -> None:
        (committed / file).unlink()

        assert _state(committed, name) is D4IntegrityState.FAILED


def test_the_predecessor_fingerprint_is_the_released_one_over_five_stores() -> None:
    """W7-A1: a second implementation of a fingerprint is a second answer to one question."""
    baseline = json.loads((EVIDENCE / "sprint-21d4-baseline.json").read_text(encoding="utf-8"))
    declared = baseline["predecessor_artifact_stores"]
    assert len(declared) == 5

    present = {
        name: DATA_ROOT / directory
        for name, directory in (
            ("development", "artifacts"),
            ("sprint_21c3", "artifacts-s21c3"),
            ("sprint_21d1", "artifacts-s21d1"),
            ("sprint_21d2", "artifacts-s21d2"),
            ("sprint_21d3", "artifacts-s21d3"),
        )
        if (DATA_ROOT / directory).is_dir()
    }
    if not present:
        pytest.skip("the predecessor data root is not on this machine")

    for name, root in present.items():
        assert (
            path_and_size_fingerprint(root) == declared[name]["path_and_size_fingerprint_sha256"]
        ), f"{name} no longer reproduces the fingerprint the baseline released"
