"""S21D3-081: one seeded violation per integrity class, and the four states.

The report is only worth running if each class can actually fail, so every class here is
driven twice: once against the committed evidence, and once against a copy of it with exactly
one thing broken. A class that cannot be made to fail is a class that proves nothing.

Three properties matter as much as the individual checks.

*A class nobody checked is never clean.* The artifact and isolation classes need authorities
this process may not have, and they report `warning` when it does not — which is the distinction
the whole sprint keeps re-learning, and the reason `not_measured` exists in the promotion
payload as well.

*A stored state claiming a pass without its evidence fails closed.* Deleting the file a class
reads makes that class `failed`, never `clean` and never `not_opened`.

*`not_opened` is a decision, not a gap.* The lifecycle class is `not_opened` because the
checkpoint says so by hash, and it becomes `failed` the moment that record claims otherwise.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from cognitive_os.learning.integrity_d3 import (
    D3_INTEGRITY_CLASSES,
    D3IntegrityState,
    d3_integrity,
    path_and_size_fingerprint,
)

REPOSITORY = Path(__file__).resolve().parents[3]
EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"


@pytest.fixture
def committed(tmp_path: Path) -> Path:
    """A writable copy of the committed evidence, so a seeded violation damages nothing."""
    target = tmp_path / "evidence"
    shutil.copytree(EVIDENCE, target)
    return target


def _edit(directory: Path, name: str, mutate: Callable[[dict], None]) -> None:
    path = directory / name
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _state(directory: Path, name: str, **kwargs: object) -> D3IntegrityState:
    report = d3_integrity(directory, **kwargs)  # type: ignore[arg-type]
    return next(item.state for item in report.classes if item.name == name)


class TestTheCommittedEvidence:
    def test_every_class_is_covered_exactly_once_and_in_order(self) -> None:
        report = d3_integrity(EVIDENCE)

        assert tuple(item.name for item in report.classes) == D3_INTEGRITY_CLASSES
        assert len(set(D3_INTEGRITY_CLASSES)) == 11

    def test_nothing_fails_and_the_report_says_which_classes_it_could_not_check(self) -> None:
        report = d3_integrity(EVIDENCE)

        assert report.failed == ()
        assert report.healthy
        assert set(report.warnings) == {"artifact_bytes", "isolation"}
        assert report.not_opened == ("lifecycle",)

    def test_the_lifecycle_class_is_not_opened_rather_than_clean(self) -> None:
        """It is a decision bound to a stop hash, not a class that happened to pass."""
        report = d3_integrity(EVIDENCE)
        lifecycle = next(item for item in report.classes if item.name == "lifecycle")

        assert lifecycle.state is D3IntegrityState.NOT_OPENED
        assert "dependent tasks bound to stop" in lifecycle.detail


class TestOneSeededViolationPerClass:
    def test_a_dataset_that_does_not_rebuild_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-self-play-campaign.json",
            lambda d: d["snapshot"]["datasets"]["calibration"].update(rebuilt_identically=False),
        )

        assert _state(committed, "explicit_member_selection") is D3IntegrityState.FAILED

    def test_a_contradicted_receipt_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-self-play-campaign.json",
            lambda d: d["resume"]["calibration"].update(is_resumable=False, refused=["group-a"]),
        )

        assert _state(committed, "duplicate_executions_or_seals") is D3IntegrityState.FAILED

    def test_evidence_bound_to_other_pre_registration_bytes_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d3-learner-selection.json",
            lambda d: d.update(pre_registration_sha256="9" * 64),
        )

        assert _state(committed, "chronology") is D3IntegrityState.FAILED

    def test_evidence_recorded_before_publication_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-corpus.json",
            lambda d: d.update(recorded_at="2020-01-01T00:00:00Z"),
        )

        assert _state(committed, "chronology") is D3IntegrityState.FAILED

    def test_a_feature_contract_that_drifted_from_the_frozen_hash_is_caught(
        self, committed: Path
    ) -> None:
        path = committed / "sprint-21d3-contracts.json"
        path.write_text(json.dumps({"contracts": {"feature": "0" * 64}}), encoding="utf-8")

        assert _state(committed, "feature_schema") is D3IntegrityState.FAILED

    def test_a_matrix_that_did_not_scan_the_embedding_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-vertical-slice.json",
            lambda d: d.update(fitted_columns=6),
        )

        assert _state(committed, "matrix_embedding_scans") is D3IntegrityState.FAILED

    def test_ood_decisions_counted_as_candidate_outcomes_are_caught(self, committed: Path) -> None:
        """The exact D2 defect: one number serving as both denominators."""
        _edit(
            committed,
            "sprint-21d3-calibration-metamorphic.json",
            lambda d: d.update(valid_decisions=d["candidate_outcomes"]),
        )

        assert _state(committed, "ood_units") is D3IntegrityState.FAILED

    def test_a_file_claiming_a_final_outcome_was_inspected_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-separation.json",
            lambda d: d.update(final_outcomes_inspected=True),
        )

        assert _state(committed, "holdout_access") is D3IntegrityState.FAILED

    def test_a_holdout_read_more_than_once_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d3-retrieval-holdout-result.json",
            lambda d: d["benchmark"].update(executions=2),
        )

        assert _state(committed, "retrieval_one_read") is D3IntegrityState.FAILED

    def test_a_blob_that_does_not_hash_to_its_name_is_caught(self, committed: Path) -> None:
        assert (
            _state(committed, "artifact_bytes", blob_hashes={"a" * 64: "b" * 64})
            is D3IntegrityState.FAILED
        )

    def test_a_declared_blob_with_no_bytes_is_caught(self, committed: Path) -> None:
        """W7-A3: rehashing only what exists calls a store one blob smaller perfectly clean."""
        assert (
            _state(committed, "artifact_bytes", blob_hashes={"a" * 64: None})
            is D3IntegrityState.FAILED
        )

    def test_present_and_correct_blobs_are_clean(self, committed: Path) -> None:
        assert (
            _state(committed, "artifact_bytes", blob_hashes={"a" * 64: "a" * 64})
            is D3IntegrityState.CLEAN
        )

    def test_an_authorised_checkpoint_with_no_supporting_evidence_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d3-pre-final-checkpoint.json",
            lambda d: d["decision"].update(authorised=True),
        )

        assert _state(committed, "lifecycle") is D3IntegrityState.FAILED

    def test_dependent_records_bound_to_two_different_stops_are_caught(
        self, committed: Path
    ) -> None:
        def two_stops(document: dict) -> None:
            document["not_opened"][0]["stop_hash"] = "7" * 64

        _edit(committed, "sprint-21d3-pre-final-checkpoint.json", two_stops)

        assert _state(committed, "lifecycle") is D3IntegrityState.FAILED

    def test_a_predecessor_store_whose_fingerprint_moved_is_caught(self, committed: Path) -> None:
        assert (
            _state(
                committed,
                "isolation",
                predecessor_fingerprints={"development": "0" * 64},
            )
            is D3IntegrityState.FAILED
        )


class TestTheTwoStatesThatAreNotPassOrFail:
    @pytest.mark.parametrize("name", ["artifact_bytes", "isolation"])
    def test_a_class_nobody_checked_warns_rather_than_passing(self, name: str) -> None:
        report = d3_integrity(EVIDENCE)
        item = next(entry for entry in report.classes if entry.name == name)

        assert item.state is D3IntegrityState.WARNING
        assert "not checked" in item.detail

    @pytest.mark.parametrize(
        ("name", "file"),
        [
            ("duplicate_executions_or_seals", "sprint-21d3-self-play-campaign.json"),
            ("feature_schema", "sprint-21d3-contracts.json"),
            ("matrix_embedding_scans", "sprint-21d3-vertical-slice.json"),
            ("ood_units", "sprint-21d3-calibration-metamorphic.json"),
            ("retrieval_one_read", "sprint-21d3-retrieval-holdout-result.json"),
            ("lifecycle", "sprint-21d3-pre-final-checkpoint.json"),
            ("isolation", "sprint-21d3-baseline.json"),
        ],
    )
    def test_missing_evidence_fails_closed_rather_than_reading_as_not_opened(
        self, committed: Path, name: str, file: str
    ) -> None:
        (committed / file).unlink()

        assert _state(committed, name) is D3IntegrityState.FAILED

    def test_a_warning_does_not_make_the_report_unhealthy(self) -> None:
        report = d3_integrity(EVIDENCE)

        assert report.warnings
        assert report.healthy


class TestTheFingerprintIsTheReleasedOne:
    def test_it_reproduces_the_published_predecessor_digests(self) -> None:
        """W7-A1: a second implementation of this hash reported all four stores as moved."""
        baseline = json.loads((EVIDENCE / "sprint-21d3-baseline.json").read_text(encoding="utf-8"))
        stores = baseline["predecessor_artifact_stores"]
        roots = {
            name: Path(value["absolute_root"])
            for name, value in stores.items()
            if Path(value["absolute_root"]).is_dir()
        }
        if not roots:
            pytest.skip("the predecessor stores are not present on this host")

        for name, root in roots.items():
            assert (
                path_and_size_fingerprint(root)
                == (stores[name]["path_and_size_fingerprint_sha256"])
            )
