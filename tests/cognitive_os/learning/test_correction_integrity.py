"""S21D2-081: a check that has never failed is a check nobody has tested.

Every test here builds evidence that is broken in exactly one way and asserts that the check
named for that class refuses it, with a reason stable enough to grep for. The two classes D2
never opened get their own tests: they must report as `not_opened` bound to the decision that
closed them, and a report that quietly turned them into passing zeroes would be a report
claiming to have checked something it never looked at.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

import pytest

from cognitive_os.coding.reality_integrity import FAILURE, NOT_OPENED, IntegrityCheck
from cognitive_os.learning.correction_integrity import (
    ActiveComponent,
    CorrectionEvidence,
    InheritedPair,
    LineageRow,
    ObservedCorrection,
    SealedPartition,
    SequenceReceipt,
    StopRecord,
    correction_checks,
    correction_counts,
)

NAMESPACE = UUID("5e2c8a41-9b76-5d03-8f14-3a7e6c2b91d5")
SEALED_AT = datetime(2026, 8, 2, 5, 32, tzinfo=UTC)
RAN_AT = SEALED_AT + timedelta(minutes=3)
TRAINING_MANIFEST = "a" * 64
CALIBRATION_MANIFEST = "b" * 64
STOP = StopRecord(
    name="candidate_selection",
    content_hash="c" * 64,
    reason="the calibrated rung reversed confidently under a semantics-preserving perturbation",
)


def _task(index: int) -> UUID:
    return uuid5(NAMESPACE, f"task:{index}")


def _seal(
    partition: str = "training",
    *,
    manifest: str = TRAINING_MANIFEST,
    tasks: tuple[int, ...] = (0, 1, 2),
    groups: tuple[str, ...] = ("group-0", "group-1", "group-2"),
    sealed_at: datetime = SEALED_AT,
    reproduces: bool = True,
    declared: bool = True,
) -> SealedPartition:
    return SealedPartition(
        partition=partition,
        campaign_manifest_hash=manifest,
        feature_set_hash="d" * 64,
        sealed_at=sealed_at,
        artifact_id=uuid5(NAMESPACE, f"seal:{partition}:{sealed_at.isoformat()}"),
        candidate_ids=frozenset(uuid5(NAMESPACE, f"candidate:{partition}:{i}") for i in tasks),
        task_ids=frozenset(_task(index) for index in tasks),
        groups=frozenset(groups),
        bytes_reproduce_the_seal=reproduces,
        declared=declared,
    )


def _observation(
    index: int,
    *,
    manifest: str = TRAINING_MANIFEST,
    source_kind: str = "correction_self_play_task_run",
    provenance: str = "self_play",
    recorded_at: datetime = RAN_AT,
    task_index: int | None = None,
) -> ObservedCorrection:
    return ObservedCorrection(
        observation_id=uuid5(NAMESPACE, f"observation:{manifest}:{index}"),
        source_task_id=_task(index if task_index is None else task_index),
        source_run_id=uuid5(NAMESPACE, f"run:{index}"),
        source_kind=source_kind,
        provenance_class=provenance,
        status="accepted",
        evaluation_eligible=True,
        campaign_manifest_hash=manifest,
        recorded_at=recorded_at,
    )


def _lineage(*, declared: str = "e" * 64, observed: str | None = None, bytes_present: bool = True):
    return LineageRow(
        lineage_id=uuid5(NAMESPACE, "lineage"),
        artifact_id=uuid5(NAMESPACE, "artifact"),
        role="split_manifest",
        declared_content_hash=declared,
        observed_content_hash=declared if observed is None else observed,
        bytes_present=bytes_present,
    )


def _receipt(version: int, *, manifest: str = TRAINING_MANIFEST) -> SequenceReceipt:
    return SequenceReceipt(
        campaign_id=uuid5(NAMESPACE, "campaign"),
        stream_version=version,
        task_id=_task(version),
        campaign_manifest_hash=manifest,
        attempted_order=(uuid5(NAMESPACE, f"attempt:{version}"),),
        intentionally_unattempted=(),
    )


def _evidence(**overrides) -> CorrectionEvidence:  # type: ignore[no-untyped-def]
    payload: dict[str, object] = {
        "observations": tuple(_observation(index) for index in range(3))
        + tuple(
            _observation(index, manifest=CALIBRATION_MANIFEST, task_index=index + 10)
            for index in range(2)
        ),
        "seals": (
            _seal(),
            _seal(
                "calibration",
                manifest=CALIBRATION_MANIFEST,
                tasks=(10, 11),
                groups=("group-10", "group-11"),
            ),
        ),
        "lineage": (_lineage(),),
        "receipts": tuple(_receipt(version) for version in (1, 2, 3)),
        "components": (),
        "inherited": (),
        "selection_stop": STOP,
    }
    payload.update(overrides)
    return CorrectionEvidence(**payload)  # type: ignore[arg-type]


def _check(evidence: CorrectionEvidence, name: str) -> IntegrityCheck:
    return next(check for check in correction_checks(evidence) if check.name == name)


class TestACleanStorePasses:
    def test_every_check_that_ran_passed(self) -> None:
        checks = correction_checks(_evidence())

        assert [check.name for check in checks if not check.ok] == []

    def test_the_healthy_detail_names_counts_rather_than_only_ok(self) -> None:
        """`ok: true` with no number is an assertion, not a report. §S21D2-081 acceptance."""
        detail = _check(_evidence(), "every_correction_observation_carries_its_sealed_role").detail

        assert "5 observations" in detail
        assert "2 sealed" in detail

    def test_the_counts_name_the_exact_hashes_the_seals_carry(self) -> None:
        counts = correction_counts(_evidence())

        assert counts["observations"] == 5
        assert counts["observations_in_a_fittable_partition"] == 5
        assert counts["real_governed_run_observations"] == 0
        assert counts["sealed_partitions"]["training"]["campaign_manifest_hash"] == (
            TRAINING_MANIFEST
        )
        assert counts["sealed_partitions"]["calibration"]["candidate_slots"] == 2


class TestRoleAndGroupCrossing:
    def test_a_governed_role_on_a_self_play_partition_is_caught(self) -> None:
        broken = _evidence(
            observations=(
                _observation(0, source_kind="governed_task_run", provenance="real_governed_run"),
            )
        )

        check = _check(broken, "every_correction_observation_carries_its_sealed_role")

        assert not check.ok
        assert "disagrees with their seal" in check.detail

    def test_an_observation_naming_no_sealed_campaign_is_caught(self) -> None:
        broken = _evidence(observations=(_observation(0, manifest="f" * 64),))

        check = _check(broken, "every_correction_observation_carries_its_sealed_role")

        assert not check.ok
        assert "no seal names" in check.detail

    def test_a_group_in_two_partitions_is_caught(self) -> None:
        broken = _evidence(
            seals=(
                _seal(),
                _seal(
                    "calibration",
                    manifest=CALIBRATION_MANIFEST,
                    tasks=(10, 11),
                    groups=("group-1", "group-11"),
                ),
            )
        )

        check = _check(broken, "no_correction_group_crosses_a_partition")

        assert not check.ok
        assert "group-1 in ['calibration', 'training']" in check.detail


class TestChronology:
    def test_an_outcome_recorded_before_its_seal_is_caught(self) -> None:
        broken = _evidence(
            observations=(_observation(0, recorded_at=SEALED_AT - timedelta(seconds=1)),)
        )

        check = _check(broken, "every_correction_observation_follows_its_feature_seal")

        assert not check.ok
        assert "before the features that describe them" in check.detail

    def test_the_healthy_detail_states_both_ends_of_the_window(self) -> None:
        check = _check(_evidence(), "every_correction_observation_follows_its_feature_seal")

        assert SEALED_AT.isoformat() in check.detail
        assert RAN_AT.isoformat() in check.detail


class TestACampaignThatWasExecutedTwice:
    """The store's real shape. Found by running the check, not by reading the code.

    W4-F2 made the D2 campaign execute the same candidates twice, each execution sealing its
    own feature set. Measured against only the seal the evidence names, half the store looked
    like outcomes that preceded their own features. They did not: each was pre-outcome under
    the seal it ran under, and the earlier seal is still in the store to prove it.
    """

    @staticmethod
    def _twice() -> CorrectionEvidence:
        first = SEALED_AT - timedelta(minutes=6)
        return _evidence(
            seals=(
                _seal(sealed_at=first, reproduces=True),
                _seal(),
                _seal(
                    "calibration",
                    manifest=CALIBRATION_MANIFEST,
                    tasks=(10, 11),
                    groups=("group-10", "group-11"),
                ),
            ),
            observations=(
                _observation(0, recorded_at=first + timedelta(seconds=2)),
                _observation(1, recorded_at=RAN_AT),
            ),
        )

    def test_a_row_written_under_a_superseded_seal_is_not_a_chronology_failure(self) -> None:
        check = _check(self._twice(), "every_correction_observation_follows_its_feature_seal")

        assert check.ok

    def test_a_row_before_even_the_earliest_seal_is_still_caught(self) -> None:
        evidence = self._twice()
        broken = _evidence(
            seals=evidence.seals,
            observations=(_observation(0, recorded_at=SEALED_AT - timedelta(hours=1)),),
        )

        check = _check(broken, "every_correction_observation_follows_its_feature_seal")

        assert not check.ok

    def test_the_second_seal_is_reported_as_news_rather_than_hidden(self) -> None:
        check = _check(self._twice(), "each_campaign_manifest_was_sealed_once")

        assert not check.ok
        assert check.severity == "warning"
        assert "explicit member list" in check.detail

    def test_one_seal_per_manifest_passes_that_check(self) -> None:
        check = _check(_evidence(), "each_campaign_manifest_was_sealed_once")

        assert check.ok
        assert "2 campaign manifests, one seal each" in check.detail

    def test_only_declared_seals_are_hash_checked_and_the_rest_are_counted(self) -> None:
        evidence = _evidence(
            seals=(_seal(), _seal(sealed_at=SEALED_AT - timedelta(minutes=6), declared=False))
        )

        check = _check(evidence, "every_sealed_feature_set_reproduces_its_hash")

        assert check.ok
        assert "1 further seals found in the store and not hash-checked" in check.detail

    def test_a_discovered_seal_that_does_not_reproduce_is_not_reported_as_damage(self) -> None:
        """It carries no independently recorded hash, so there is nothing to disagree with."""
        evidence = _evidence(
            seals=(
                _seal(),
                _seal(
                    sealed_at=SEALED_AT - timedelta(minutes=6),
                    declared=False,
                    reproduces=False,
                ),
            )
        )

        assert _check(evidence, "every_sealed_feature_set_reproduces_its_hash").ok


class TestManifestMembership:
    def test_an_observation_for_a_task_no_manifest_holds_is_caught(self) -> None:
        broken = _evidence(observations=(_observation(0, task_index=99),))

        check = _check(broken, "every_correction_observation_is_a_sealed_member")

        assert not check.ok
        assert "naming a task no sealed manifest holds" in check.detail


class TestArtifactLineage:
    def test_a_lineage_row_with_no_bytes_is_caught(self) -> None:
        broken = _evidence(lineage=(_lineage(bytes_present=False),))

        check = _check(broken, "every_correction_lineage_row_resolves_to_its_bytes")

        assert not check.ok
        assert "1 rows with no bytes" in check.detail

    def test_a_declared_hash_the_store_disagrees_with_is_caught(self) -> None:
        broken = _evidence(lineage=(_lineage(observed="9" * 64),))

        check = _check(broken, "every_correction_lineage_row_resolves_to_its_bytes")

        assert not check.ok
        assert "is not what the store holds" in check.detail

    def test_a_seal_whose_bytes_do_not_reproduce_its_hash_is_caught(self) -> None:
        """The seal is the authority for six other checks, so it is verified before it is used."""
        broken = _evidence(seals=(_seal(reproduces=False),))

        check = _check(broken, "every_sealed_feature_set_reproduces_its_hash")

        assert not check.ok
        assert "do not hash to the name" in check.detail


class TestTheReceiptChain:
    def test_a_gap_in_the_compare_and_set_chain_is_caught(self) -> None:
        broken = _evidence(receipts=tuple(_receipt(version) for version in (1, 2, 4)))

        check = _check(broken, "every_campaign_receipt_chains_to_its_predecessor")

        assert not check.ok
        assert "not contiguous" in check.detail

    def test_a_receipt_for_an_unsealed_manifest_is_caught(self) -> None:
        broken = _evidence(receipts=(_receipt(1, manifest="7" * 64),))

        check = _check(broken, "every_campaign_receipt_chains_to_its_predecessor")

        assert not check.ok
        assert "unsealed manifest" in check.detail

    def test_the_healthy_detail_names_the_range_it_verified(self) -> None:
        check = _check(_evidence(), "every_campaign_receipt_chains_to_its_predecessor")

        assert "1..3" in check.detail


class TestTheClassesTheStopClosed:
    def test_activation_is_reported_as_not_opened_bound_to_the_stop(self) -> None:
        check = _check(_evidence(), "the_correction_surface_has_a_sound_activation_state")

        assert check.severity == NOT_OPENED
        assert check.bound_hash == STOP.content_hash
        assert "no component was ever registered" in check.detail

    def test_model_identity_is_reported_as_not_opened_bound_to_the_stop(self) -> None:
        check = _check(_evidence(), "every_active_component_resolves_to_the_model_it_declares")

        assert check.severity == NOT_OPENED
        assert check.bound_hash == STOP.content_hash

    def test_a_component_the_stop_record_denies_flips_it_to_a_failure(self) -> None:
        """S21D2-084's not-opened tampering case, and the hole it was written to find.

        `not_opened` short-circuited on the presence of a stop record alone, so a fabricated
        component on the stopped surface was the one thing this report could not see. The
        stop record claims the store is empty; that claim is now checked.
        """
        smuggled = ActiveComponent(
            component_id=uuid5(NAMESPACE, "smuggled"),
            surface="experience.correction_ranking",
            revision=1,
            state="registered",
            artifact_id=None,
            artifact_content_hash=None,
        )
        evidence = _evidence(components=(smuggled,))

        activation = _check(evidence, "the_correction_surface_has_a_sound_activation_state")
        identity = _check(evidence, "every_active_component_resolves_to_the_model_it_declares")

        assert not activation.ok and activation.severity == FAILURE
        assert "the store holds 1" in activation.detail
        assert not identity.ok and identity.severity == FAILURE
        assert activation.bound_hash is None

    def test_a_component_on_another_surface_does_not_contradict_the_stop(self) -> None:
        other = ActiveComponent(
            component_id=uuid5(NAMESPACE, "other"),
            surface="experience.retrieval",
            revision=1,
            state="active",
            artifact_id=None,
            artifact_content_hash=None,
        )

        check = _check(
            _evidence(components=(other,)),
            "the_correction_surface_has_a_sound_activation_state",
        )

        assert check.severity == NOT_OPENED

    def test_without_a_stop_record_the_same_classes_are_really_checked(self) -> None:
        """The `not_opened` state is a consequence of a record, never a way to skip a check."""
        component = ActiveComponent(
            component_id=uuid5(NAMESPACE, "component"),
            surface="experience.correction_ranking",
            revision=1,
            state="active",
            artifact_id=uuid5(NAMESPACE, "artifact"),
            artifact_content_hash="e" * 64,
        )
        evidence = _evidence(selection_stop=None, components=(component,))

        activation = _check(evidence, "the_correction_surface_has_a_sound_activation_state")
        identity = _check(evidence, "every_active_component_resolves_to_the_model_it_declares")

        assert activation.severity == FAILURE and activation.ok
        assert identity.severity == FAILURE and identity.ok

    def test_two_active_revisions_on_one_surface_are_caught(self) -> None:
        components = tuple(
            ActiveComponent(
                component_id=uuid5(NAMESPACE, f"component:{index}"),
                surface="experience.correction_ranking",
                revision=index,
                state="active",
                artifact_id=uuid5(NAMESPACE, "artifact"),
                artifact_content_hash="e" * 64,
            )
            for index in (1, 2)
        )

        check = _check(
            _evidence(selection_stop=None, components=components),
            "the_correction_surface_has_a_sound_activation_state",
        )

        assert not check.ok
        assert "more than one active revision" in check.detail

    def test_an_active_component_whose_artifact_hashes_to_something_else_is_caught(
        self,
    ) -> None:
        component = ActiveComponent(
            component_id=uuid5(NAMESPACE, "component"),
            surface="experience.correction_ranking",
            revision=1,
            state="active",
            artifact_id=uuid5(NAMESPACE, "artifact"),
            artifact_content_hash="0" * 64,
        )

        check = _check(
            _evidence(selection_stop=None, components=(component,)),
            "every_active_component_resolves_to_the_model_it_declares",
        )

        assert not check.ok
        assert "hashes to something else" in check.detail


class TestStoreIsolation:
    def test_a_store_that_moved_is_caught_and_named(self, tmp_path: Path) -> None:
        root = tmp_path / "artifacts-s21c3"
        root.mkdir()
        (root / "one").write_bytes(b"x")
        pair = InheritedPair(
            name="artifacts_s21c3",
            root=root,
            expected_digest="0" * 64,
            expected_files=1,
        )

        check = _check(_evidence(inherited=(pair,)), "artifacts_s21c3_is_untouched")

        assert not check.ok
        assert "expected 0000" in check.detail

    def test_an_absent_store_is_a_failure_rather_than_a_pass(self, tmp_path: Path) -> None:
        pair = InheritedPair(
            name="artifacts_s21d1",
            root=tmp_path / "gone",
            expected_digest="0" * 64,
            expected_files=0,
        )

        check = _check(_evidence(inherited=(pair,)), "artifacts_s21d1_is_untouched")

        assert not check.ok
        assert "is not present to compare" in check.detail


class TestTheNotOpenedStateCannotBeUnbound:
    def test_a_not_opened_check_without_a_hash_is_refused(self) -> None:
        with pytest.raises(ValueError, match="without naming the decision"):
            IntegrityCheck(name="a", ok=True, severity=NOT_OPENED, detail="d")

    def test_a_ran_check_cannot_borrow_a_stop_hash(self) -> None:
        with pytest.raises(ValueError, match="binds a stop hash"):
            IntegrityCheck(name="a", ok=True, severity=FAILURE, detail="d", bound_hash="c" * 64)
