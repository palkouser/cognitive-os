from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid5

import pytest

from cognitive_os.learning.correction_matrix import FittedMatrix, FittedRow, scan_matrices
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_EMBEDDING,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import CorrectionFeatureVector

NAMESPACE = UUID("b34cf59d-7148-54e5-85d5-65f167b45bd4")
SEALED_AT = datetime(2026, 8, 4, 8, tzinfo=UTC)
OUTCOME_AT = datetime(2026, 8, 4, 9, tzinfo=UTC)


def _embedding(seed: int, accepted: bool, *, invalid: bool = False) -> tuple[float, ...]:
    digest = sha256(str(seed).encode()).digest()
    values = [((digest[index % len(digest)] / 255) * 1.8) - 0.9 for index in range(384)]
    values[5] = float(accepted)  # the deliberately label-perfect embedding dimension
    if invalid:
        values[8] = float("inf")
    return tuple(values)


def _row(seed: int, split: str, *, invalid: bool = False) -> FittedRow:
    accepted = bool(seed % 2)
    vector = CorrectionFeatureVector(
        encoder_version="correction-ranking-v2",
        values=tuple((name, 0.5) for name in FITTED_FEATURE_V2_SCALARS),
        embedding=_embedding(seed, accepted, invalid=invalid),
    )
    return FittedRow(
        candidate_id=uuid5(NAMESPACE, f"candidate:{split}:{seed}"),
        task_id=uuid5(NAMESPACE, f"task:{split}:{seed}"),
        group=f"{split}-group-{seed}",
        partition=split,
        vector=vector,
        accepted=accepted,
        sealed_at=SEALED_AT,
        outcome_at=OUTCOME_AT,
        observation_id=uuid5(NAMESPACE, f"observation:{split}:{seed}"),
        sealed_feature_hash=vector.content_hash(),
    )


def _matrix(split: str, start: int, *, invalid: bool = False) -> FittedMatrix:
    return FittedMatrix(
        split=split,
        rows=tuple(
            _row(seed, split, invalid=invalid and seed == start) for seed in range(start, start + 8)
        ),
    )


def _scan(report, name: str):
    return next(item for item in report.scans if item.name == name)


def test_v2_matrix_exposes_and_scans_all_390_fitted_dimensions() -> None:
    report = scan_matrices(
        _matrix("fit", 0),
        _matrix("calibration", 100),
        created_at=OUTCOME_AT,
        contract=CorrectionFeatureContractV2(),
    )

    assert len(report.column_names) == 390
    assert report.column_names[-384:] == FITTED_FEATURE_V2_EMBEDDING
    oracle_scan = _scan(report, "no_column_derives_the_label")
    assert not oracle_scan.passed
    assert "canonical_candidate_source_embedding_005" in oracle_scan.offenders
    assert _scan(report, "every_row_has_one_encoder_identity").passed


def test_v2_matrix_rejects_an_unstable_embedding_dimension() -> None:
    report = scan_matrices(
        _matrix("fit", 0, invalid=True),
        _matrix("calibration", 100),
        created_at=OUTCOME_AT,
        contract=CorrectionFeatureContractV2(),
    )

    validity = _scan(report, "every_fitted_dimension_is_finite_and_in_range")
    assert not validity.passed
    assert any("canonical_candidate_source_embedding_008" in item for item in validity.offenders)


def test_matrix_refuses_mixed_encoder_versions_regardless_of_first_row() -> None:
    fit = _matrix("fit", 0)
    first = fit.rows[0]
    mixed = FittedMatrix(
        split=fit.split,
        rows=(
            replace(
                first,
                vector=CorrectionFeatureVector(
                    encoder_version="correction-ranking-v1",
                    values=first.vector.values,
                    embedding=first.vector.embedding,
                ),
            ),
            *fit.rows[1:],
        ),
    )

    with pytest.raises(ValueError, match="same encoder version"):
        scan_matrices(
            mixed,
            _matrix("calibration", 100),
            created_at=OUTCOME_AT,
            contract=CorrectionFeatureContractV2(),
        )


def test_matrix_refuses_a_row_with_reordered_fitted_columns() -> None:
    fit = _matrix("fit", 0)
    second = fit.rows[1]
    reordered = replace(
        second,
        vector=CorrectionFeatureVector(
            encoder_version=second.vector.encoder_version,
            values=tuple(reversed(second.vector.values)),
            embedding=second.vector.embedding,
        ),
    )

    with pytest.raises(ValueError, match="same ordered columns"):
        scan_matrices(
            FittedMatrix(split=fit.split, rows=(fit.rows[0], reordered, *fit.rows[2:])),
            _matrix("calibration", 100),
            created_at=OUTCOME_AT,
            contract=CorrectionFeatureContractV2(),
        )


def test_released_v1_vector_bytes_remain_exact() -> None:
    vector = CorrectionFeatureVector(
        encoder_version="correction-ranking-v1",
        values=(("changed_file_count", 0.25), ("hunk_count", 0.5)),
        embedding=(0.125, -0.25),
    )

    assert vector.canonical_bytes() == (
        b"correction-ranking-v1\nchanged_file_count=0.250000\n"
        b"hunk_count=0.500000\ne0=0.125000\ne1=-0.250000"
    )
