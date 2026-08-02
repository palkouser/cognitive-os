"""S21D2-041: the scans have to fail on a corpus that is wrong, or they prove nothing.

Every test here builds a matrix that is broken in exactly one way and asserts the scan named
for that way refuses it. The acceptance criterion asks specifically for a seeded oracle and a
seeded identity column to fail, so those two are injected rather than described.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid5

import pytest

from cognitive_os.learning.correction_matrix import (
    NEAR_DUPLICATE_SIMILARITY,
    FittedMatrix,
    FittedRow,
    scan_matrices,
    separation,
)
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionFeatureVector,
)

NAMESPACE = UUID("5e2c8a41-9b76-5d03-8f14-3a7e6c2b91d5")
SEALED_AT = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
RAN_AT = datetime(2026, 8, 2, 13, 0, tzinfo=UTC)
COLUMNS = (
    *NUMERIC_FEATURE_NAMES,
    "query_to_candidate_cosine",
    "missing_value_indicators",
    "declared_verifier_capabilities",
)


def _spread(seed: int, salt: str, count: int) -> tuple[float, ...]:
    """A well-separated pseudorandom vector.

    Modular arithmetic on a small seed produces near-collinear rows — and a zero row for seed
    zero, whose cosine against anything is zero. A digest gives rows that differ the way real
    ones do, which is what a near-duplicate scan has to be exercised against.
    """
    digest = sha256(f"{salt}:{seed}".encode()).digest()
    return tuple(round((digest[index] + 1) / 256, 6) for index in range(count))


def _vector(seed: int, *, extra: tuple[tuple[str, float], ...] = ()) -> CorrectionFeatureVector:
    numbers = _spread(seed, "values", len(COLUMNS))
    return CorrectionFeatureVector(
        encoder_version="correction-ranking-v1",
        values=tuple(zip(COLUMNS, numbers, strict=True)) + extra,
        embedding=_spread(seed, "embedding", 8),
    )


def _row(
    seed: int,
    *,
    group: str,
    accepted: bool,
    partition: str = "training",
    vector: CorrectionFeatureVector | None = None,
    sealed_at: datetime = SEALED_AT,
    outcome_at: datetime = RAN_AT,
    sealed_hash: str | None = None,
    candidate_id: UUID | None = None,
    observation_id: UUID | None = None,
) -> FittedRow:
    built = vector if vector is not None else _vector(seed)
    return FittedRow(
        candidate_id=candidate_id or uuid5(NAMESPACE, f"candidate:{seed}"),
        task_id=uuid5(NAMESPACE, f"task:{group}"),
        group=group,
        partition=partition,
        vector=built,
        accepted=accepted,
        sealed_at=sealed_at,
        outcome_at=outcome_at,
        observation_id=observation_id or uuid5(NAMESPACE, f"observation:{seed}"),
        sealed_feature_hash=sealed_hash or built.content_hash(),
    )


def _matrices(
    fit_rows: tuple[FittedRow, ...] | None = None,
    calibration_rows: tuple[FittedRow, ...] | None = None,
) -> tuple[FittedMatrix, FittedMatrix]:
    fit = FittedMatrix(
        split="fit",
        rows=fit_rows
        or tuple(
            _row(seed, group=f"fit-group-{seed // 2}", accepted=bool(seed % 2))
            for seed in range(24)
        ),
    )
    calibration = FittedMatrix(
        split="calibration",
        rows=calibration_rows
        or tuple(
            _row(
                seed,
                group=f"calibration-group-{seed // 2}",
                accepted=bool(seed % 2),
                partition="calibration",
            )
            for seed in range(100, 116)
        ),
    )
    return fit, calibration


def _scan(fit: FittedMatrix, calibration: FittedMatrix):
    return scan_matrices(fit, calibration, created_at=RAN_AT)


def _verdict(report, name: str) -> bool:
    return next(scan.passed for scan in report.scans if scan.name == name)


class TestACleanCorpusPasses:
    def test_every_scan_passes_on_a_well_formed_pair(self) -> None:
        report = _scan(*_matrices())

        assert report.clean
        assert report.failures == ()

    def test_the_report_names_the_matrices_it_read(self) -> None:
        fit, calibration = _matrices()
        report = _scan(fit, calibration)

        assert report.fit_matrix_hash == fit.content_hash
        assert report.calibration_matrix_hash == calibration.content_hash

    def test_an_empty_split_is_refused_rather_than_reported_clean(self) -> None:
        _, calibration = _matrices()
        with pytest.raises(ValueError, match="both splits"):
            _scan(FittedMatrix(split="fit", rows=()), calibration)


class TestTheSeededOracleFails:
    def test_a_column_equal_to_the_label_is_caught(self) -> None:
        """The acceptance criterion's own test: seed an oracle, and the scan must refuse it."""
        rows = tuple(
            _row(
                seed,
                group=f"fit-group-{seed // 2}",
                accepted=bool(seed % 2),
                vector=_vector(seed, extra=(("seeded_oracle", float(seed % 2)),)),
            )
            for seed in range(24)
        )
        _, calibration = _matrices()
        calibration = FittedMatrix(
            split="calibration",
            rows=tuple(
                _row(
                    seed,
                    group=f"calibration-group-{seed // 2}",
                    accepted=bool(seed % 2),
                    partition="calibration",
                    vector=_vector(seed, extra=(("seeded_oracle", float(seed % 2)),)),
                )
                for seed in range(100, 116)
            ),
        )

        report = _scan(FittedMatrix(split="fit", rows=rows), calibration)

        assert not report.clean
        assert not _verdict(report, "no_column_derives_the_label")

    def test_a_seeded_identity_column_is_caught_by_the_allowlist(self) -> None:
        """An identity column is not on the allowlist, so absence refuses it."""
        rows = tuple(
            _row(
                seed,
                group=f"fit-group-{seed // 2}",
                accepted=bool(seed % 2),
                vector=_vector(seed, extra=(("candidate_id", float(seed)),)),
            )
            for seed in range(24)
        )
        _, calibration = _matrices()
        calibration = FittedMatrix(
            split="calibration",
            rows=tuple(
                _row(
                    seed,
                    group=f"calibration-group-{seed // 2}",
                    accepted=bool(seed % 2),
                    partition="calibration",
                    vector=_vector(seed, extra=(("candidate_id", float(seed)),)),
                )
                for seed in range(100, 116)
            ),
        )

        report = _scan(FittedMatrix(split="fit", rows=rows), calibration)

        assert not _verdict(report, "no_forbidden_field_reaches_the_matrix")

    def test_separation_folds_a_perfectly_inverted_column(self) -> None:
        """A column that predicts the label backwards is exactly as much an oracle."""
        assert separation((1.0, 2.0, 3.0, 4.0), (True, True, False, False)) == 1.0
        assert separation((4.0, 3.0, 2.0, 1.0), (True, True, False, False)) == 1.0


class TestTheOtherFiveScans:
    def test_an_outcome_before_its_feature_record_is_caught(self) -> None:
        fit, calibration = _matrices()
        broken = FittedMatrix(
            split="fit",
            rows=(
                _row(0, group="fit-group-0", accepted=True, outcome_at=SEALED_AT.replace(hour=9)),
                *fit.rows[1:],
            ),
        )

        report = _scan(broken, calibration)

        assert not _verdict(report, "every_feature_record_precedes_its_outcome")

    def test_a_row_that_does_not_reproduce_its_seal_is_caught(self) -> None:
        fit, calibration = _matrices()
        broken = FittedMatrix(
            split="fit",
            rows=(
                _row(0, group="fit-group-0", accepted=True, sealed_hash="f" * 64),
                *fit.rows[1:],
            ),
        )

        report = _scan(broken, calibration)

        assert not _verdict(report, "every_row_resolves_to_one_pre_outcome_source_chain")

    def test_a_duplicated_candidate_is_caught(self) -> None:
        fit, calibration = _matrices()
        duplicate = _row(
            5, group="fit-group-9", accepted=True, candidate_id=fit.rows[0].candidate_id
        )
        report = _scan(FittedMatrix(split="fit", rows=(*fit.rows, duplicate)), calibration)

        assert not _verdict(report, "every_row_resolves_to_one_pre_outcome_source_chain")

    def test_a_group_in_both_splits_is_caught(self) -> None:
        fit, _ = _matrices()
        crossing = FittedMatrix(
            split="calibration",
            rows=(
                _row(200, group="fit-group-0", accepted=True, partition="calibration"),
                _row(201, group="calibration-group-1", accepted=False, partition="calibration"),
            ),
        )

        report = _scan(fit, crossing)

        assert not _verdict(report, "no_group_crosses_the_split")

    def test_one_signature_with_two_labels_is_caught(self) -> None:
        fit, calibration = _matrices()
        contradiction = _row(
            0,
            group="fit-group-9",
            accepted=not fit.rows[0].accepted,
            candidate_id=uuid5(NAMESPACE, "contradiction"),
            observation_id=uuid5(NAMESPACE, "contradiction-observation"),
        )

        report = _scan(FittedMatrix(split="fit", rows=(*fit.rows, contradiction)), calibration)

        assert not _verdict(report, "no_identical_row_carries_two_labels")

    def test_a_near_duplicate_across_the_split_is_caught(self) -> None:
        fit, _ = _matrices()
        leaked = FittedMatrix(
            split="calibration",
            rows=(
                _row(
                    300,
                    group="calibration-group-0",
                    accepted=fit.rows[0].accepted,
                    partition="calibration",
                    vector=fit.rows[0].vector,
                ),
                _row(301, group="calibration-group-1", accepted=False, partition="calibration"),
            ),
        )

        report = _scan(fit, leaked)

        assert not _verdict(report, "no_near_duplicate_crosses_the_split")
        assert float(report.maximum_cross_split_similarity) >= NEAR_DUPLICATE_SIMILARITY
