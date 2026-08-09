"""S21D5-081: one seeded violation per class over D5's evidence, and the three D5 wrote itself.

Same discipline as D4's: every class is driven twice, once against the committed evidence and
once against a copy with exactly one thing broken, because a class that cannot be made to fail
is a class that proves nothing.

Three classes are D5's own and get the sharper tests. `feature_schema` now asks a second
question — the sealed hypothesis class must be one a loader implements — so it is broken both
ways. `matrix_embedding_scans` reads a two-matrix record and must notice a dropped scan, which
is the shape a count read out of the record it checks can never notice. And `lifecycle` reads a
typed stop, so an ending outside the four §3.3 published has to fail even when everything else
about the record is intact.

The nine shared classes are the released D4 implementations reading a D5 prefix. They are
driven here anyway: what is being tested is not the code, which `test_d4_integrity` already
covers, but that D5's own documents reach it and can break it.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from cognitive_os.learning.correction_protocol import CorrectionFeatureContractV2
from cognitive_os.learning.integrity_d5 import (
    D5_INTEGRITY_CLASSES,
    REQUIRED_SCANS,
    D5IntegrityState,
    d5_integrity,
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


def _state(directory: Path, name: str, **kwargs: Any) -> D5IntegrityState:
    report = d5_integrity(directory, **kwargs)
    return next(item.state for item in report.classes if item.name == name)


class TestTheCommittedEvidence:
    def test_every_class_is_covered_exactly_once_and_in_order(self) -> None:
        report = d5_integrity(EVIDENCE)

        assert tuple(item.name for item in report.classes) == D5_INTEGRITY_CLASSES
        assert len(set(D5_INTEGRITY_CLASSES)) == 12

    def test_nothing_fails_and_the_report_says_which_classes_it_could_not_check(self) -> None:
        report = d5_integrity(EVIDENCE)

        assert report.failed == ()
        assert report.healthy
        assert set(report.warnings) == {"artifact_bytes", "isolation"}
        assert report.not_opened == ("lifecycle",)

    def test_the_lifecycle_class_names_the_typed_stop_rather_than_passing(self) -> None:
        """D5 ended at a published ending; the class reports which one, not that all is well."""
        lifecycle = next(
            item for item in d5_integrity(EVIDENCE).classes if item.name == "lifecycle"
        )

        assert lifecycle.state is D5IntegrityState.NOT_OPENED
        assert "selective_margin_bound" in lifecycle.detail

    def test_the_retrieval_class_reads_a_passing_branch_the_same_way(self) -> None:
        """D4's holdout failed a floor and D5's did not; one read is one read either way."""
        retrieval = next(
            item for item in d5_integrity(EVIDENCE).classes if item.name == "retrieval_one_read"
        )

        assert retrieval.state is D5IntegrityState.CLEAN
        assert "'lexical'" in retrieval.detail

    def test_the_independence_class_counted_something(self) -> None:
        """A denominator check reporting clean over zero denominators is worth nothing."""
        independence = next(
            item for item in d5_integrity(EVIDENCE).classes if item.name == "decision_independence"
        )

        assert independence.state is D5IntegrityState.CLEAN
        assert "independent_decisions" in independence.detail
        assert len(independence.evidence) > 1


class TestOneSeededViolationPerClass:
    def test_a_dataset_that_does_not_rebuild_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-snapshots.json",
            lambda d: d["datasets"][0].update(rebuilt_identically=False),
        )

        assert _state(committed, "explicit_member_selection") is D5IntegrityState.FAILED

    def test_a_contradicted_receipt_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-calibration-campaign.json",
            lambda d: d["resume"].update(receipt_is_resumable=False),
        )

        assert _state(committed, "duplicate_executions_or_seals") is D5IntegrityState.FAILED

    def test_a_record_bound_to_other_pre_registration_bytes_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d5-learner-selection.json",
            lambda d: d.update(pre_registration_sha256="4" * 64),
        )

        assert _state(committed, "chronology") is D5IntegrityState.FAILED

    def test_a_contract_record_that_lost_the_feature_hash_is_caught(self, committed: Path) -> None:
        declared = CorrectionFeatureContractV2().content_hash
        _edit(
            committed,
            "sprint-21d5-contracts.json",
            lambda d: d.update(
                json.loads(json.dumps(d).replace(declared, "0" * 64)),
            ),
        )

        assert _state(committed, "feature_schema") is D5IntegrityState.FAILED

    def test_a_sealed_class_no_loader_implements_is_caught(self, committed: Path) -> None:
        """S21D5-037's question, asked of the sealed contract instead of the certificate."""
        _edit(
            committed,
            "sprint-21d5-contracts.json",
            lambda d: d["contracts"]["hypothesis_class"].update(name="pairwise-contrastive-v9"),
        )

        assert _state(committed, "feature_schema") is D5IntegrityState.FAILED

    def test_a_dropped_scan_is_caught(self, committed: Path) -> None:
        """The vacuity case: a record that ran three scans and calls them all of them."""
        _edit(
            committed,
            "sprint-21d5-snapshots.json",
            lambda d: d["scans"].update(results=d["scans"]["results"][:3], count=3),
        )

        assert _state(committed, "matrix_embedding_scans") is D5IntegrityState.FAILED

    def test_two_matrices_that_share_a_group_are_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-snapshots.json",
            lambda d: d["fitted_matrices"].update(fit_and_calibration_share_no_group=False),
        )

        assert _state(committed, "matrix_embedding_scans") is D5IntegrityState.FAILED

    def test_a_census_calling_every_transform_a_new_decision_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d5-invariance-regression.json",
            lambda d: d["independence"]["census_over_clean_and_transformed"].update(
                independent_decisions=d["independence"]["census_over_clean_and_transformed"][
                    "nominal_decisions"
                ],
                replicated_decisions=0,
            ),
        )

        assert _state(committed, "ood_units") is D5IntegrityState.FAILED

    def test_a_claimed_final_inspection_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-surface.json",
            lambda d: d.update(final_outcomes_inspected=True),
        )

        assert _state(committed, "holdout_access") is D5IntegrityState.FAILED

    def test_a_continuation_record_clocking_a_final_outcome_is_caught(
        self, committed: Path
    ) -> None:
        _edit(
            committed,
            "sprint-21d5-continuation.json",
            lambda d: d.update(final_or_canary_outcomes_inspected=1),
        )

        assert _state(committed, "holdout_access") is D5IntegrityState.FAILED

    def test_a_second_holdout_read_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-retrieval-holdout-result.json",
            lambda d: d.update(executions=2),
        )

        assert _state(committed, "retrieval_one_read") is D5IntegrityState.FAILED

    def test_an_alternative_reopened_after_the_read_is_caught(self, committed: Path) -> None:
        """A passing holdout followed by tuning is the same failure, later and cheaper to hide."""
        _edit(
            committed,
            "sprint-21d5-retrieval-decision.json",
            lambda d: d["no_alternative_opened"].update(
                **{next(iter(d["no_alternative_opened"])): 3}
            ),
        )

        assert _state(committed, "retrieval_one_read") is D5IntegrityState.FAILED

    def test_a_declared_blob_with_no_bytes_is_caught(self) -> None:
        assert (
            _state(EVIDENCE, "artifact_bytes", blob_hashes={"a" * 64: None})
            is D5IntegrityState.FAILED
        )

    def test_a_blob_that_does_not_hash_to_its_name_is_caught(self) -> None:
        assert (
            _state(EVIDENCE, "artifact_bytes", blob_hashes={"a" * 64: "b" * 64})
            is D5IntegrityState.FAILED
        )

    def test_an_ending_outside_the_published_four_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-continuation.json",
            lambda d: d["decision"].update(stop_kind="margin_looked_low"),
        )

        assert _state(committed, "lifecycle") is D5IntegrityState.FAILED

    def test_a_selection_no_later_evidence_supports_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-continuation.json",
            lambda d: d["decision"].update(stop_kind="select"),
        )

        assert _state(committed, "lifecycle") is D5IntegrityState.FAILED

    def test_a_dependent_item_with_no_reason_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-continuation.json",
            lambda d: d["not_opened"]["items"][0].update(why=""),
        )

        assert _state(committed, "lifecycle") is D5IntegrityState.FAILED

    def test_a_predecessor_store_that_moved_is_caught(self) -> None:
        assert (
            _state(EVIDENCE, "isolation", predecessor_fingerprints={"sprint_21d4": "0" * 64})
            is D5IntegrityState.FAILED
        )

    def test_a_census_claiming_more_distinct_than_counted_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-invariance-regression.json",
            lambda d: d["independence"]["census_over_clean_and_transformed"].update(
                independent_decisions=10_000
            ),
        )

        assert _state(committed, "decision_independence") is D5IntegrityState.FAILED

    def test_a_rate_over_a_nominal_denominator_is_caught(self, committed: Path) -> None:
        _edit(
            committed,
            "sprint-21d5-learner-selection.json",
            lambda d: d.update(
                json.loads(
                    json.dumps(d).replace(
                        '"rate_denominator": "independent_decisions"',
                        '"rate_denominator": "nominal_decisions"',
                    )
                )
            ),
        )

        assert _state(committed, "decision_independence") is D5IntegrityState.FAILED


class TestTheChecksThatCouldPassOverNothing:
    """Four scans that would report clean over an empty question, and do not."""

    def test_an_evidence_directory_with_no_denominators_fails_rather_than_passing(
        self, tmp_path: Path
    ) -> None:
        empty = tmp_path / "evidence"
        empty.mkdir()
        (empty / "sprint-21d5-nothing.json").write_text("{}", encoding="utf-8")

        assert _state(empty, "decision_independence") is D5IntegrityState.FAILED

    def test_a_store_that_was_opened_and_holds_nothing_fails(self) -> None:
        assert _state(EVIDENCE, "artifact_bytes", blob_hashes={}) is D5IntegrityState.FAILED

    def test_a_report_without_a_store_warns_rather_than_passing(self) -> None:
        assert _state(EVIDENCE, "artifact_bytes") is D5IntegrityState.WARNING

    def test_a_report_without_a_data_root_warns_rather_than_passing(self) -> None:
        assert _state(EVIDENCE, "isolation") is D5IntegrityState.WARNING


class TestBothAuthorities:
    """What the report says when it is given what a credential-free lane cannot give it."""

    @pytest.mark.skipif(not DATA_ROOT.is_dir(), reason="the data root is not on this machine")
    def test_every_declared_predecessor_reproduces_its_released_fingerprint(self) -> None:
        baseline = json.loads((EVIDENCE / "sprint-21d5-baseline.json").read_text(encoding="utf-8"))
        declared = baseline["predecessor_artifact_stores"]
        taken = {
            name: path_and_size_fingerprint(DATA_ROOT / directory)
            for name, directory in (
                ("development", "artifacts"),
                ("sprint_21c3", "artifacts-s21c3"),
                ("sprint_21d1", "artifacts-s21d1"),
                ("sprint_21d2", "artifacts-s21d2"),
                ("sprint_21d3", "artifacts-s21d3"),
                ("sprint_21d4", "artifacts-s21d4"),
            )
            if (DATA_ROOT / directory).is_dir()
        }

        assert set(taken) == set(declared)
        assert _state(EVIDENCE, "isolation", predecessor_fingerprints=taken) is (
            D5IntegrityState.CLEAN
        )

    def test_the_required_scan_set_is_the_one_the_committed_record_ran(self) -> None:
        """The constant is a floor, and a floor nobody meets is a floor nobody checked."""
        snapshots = json.loads(
            (EVIDENCE / "sprint-21d5-snapshots.json").read_text(encoding="utf-8")
        )
        ran = {item["name"] for item in snapshots["scans"]["results"]}

        assert ran == REQUIRED_SCANS
