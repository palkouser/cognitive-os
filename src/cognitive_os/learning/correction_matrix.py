"""S21D2-041: the fitted matrices, and the scans that decide whether they may be fitted on.

A feature contract is a promise about what a matrix contains. This module reads the matrix
that will actually be fitted — serialized, row by row — and checks the promise against it,
because every guarantee upstream of here is about how the numbers were *produced*, and a scan
of the produced bytes is the only thing that answers what they *are*.

Seven scans, and each one exists because of a specific way a corpus can look fine and be
useless:

*A forbidden field* is the obvious one, and the allowlist already rejects by absence — so this
scan is a second reading of the same rule against the serialized column names rather than
against the encoder's output.

*Features that do not precede their outcome* would mean the row describes a decision made
after the answer was known. The projector already refuses those, so a violation here means a
row reached the matrix by some other path.

*A row that does not resolve to one source chain* — one candidate, one sealed feature record,
one observation — is a row whose provenance is a guess.

*A group crossing the split* is memorisation reported as generalisation.

*An exact duplicate carrying two labels* is a contradiction the fit would average away.

*A near-duplicate crossing the split* is the same thing wearing a different candidate ID: the
fit sees the calibration example under another name and calibration stops being held out.

*A column that derives the label* is the oracle this whole sprint exists to remove. The scan
is a perfect-separation test per column, so a seeded oracle fails it — which is what the
acceptance criterion asks for, and what the test suite injects to prove the scan works.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from itertools import product
from math import isfinite, sqrt
from uuid import UUID

from pydantic import Field

from cognitive_os.domain.common import NonEmptyStr, Sha256Hex, UtcDatetime
from cognitive_os.domain.experience import HashedExperienceContract
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_EMBEDDING,
    CorrectionFeatureContract,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (
    ENCODER_VERSION_V2,
    CorrectionFeatureVector,
)

#: Two rows this similar are the same example wearing two candidate identities. Declared here
#: rather than chosen from the observed distribution, and the observed maximum is reported
#: beside it so the choice can be judged rather than trusted.
NEAR_DUPLICATE_SIMILARITY = 0.999

#: A column whose values separate the two labels without a single exception. Stated as an exact
#: comparison because a perfect separator is exactly what an oracle is: anything less is signal.
PERFECT_SEPARATION = 1.0


@dataclass(frozen=True, slots=True)
class FittedRow:
    """One row of the matrix, and everything that says where it came from."""

    candidate_id: UUID
    task_id: UUID
    group: str
    partition: str
    vector: CorrectionFeatureVector
    accepted: bool
    sealed_at: datetime
    outcome_at: datetime
    observation_id: UUID
    sealed_feature_hash: str

    def canonical_line(self) -> str:
        """The serialized row the scans read. Identity is provenance and stays out of it."""
        values = " ".join(f"{name}={value:.6f}" for name, value in self.vector.values)
        embedding = " ".join(f"{value:.6f}" for value in self.vector.embedding)
        return f"{values} | {embedding} | accepted={int(self.accepted)}"


@dataclass(frozen=True, slots=True)
class FittedMatrix:
    """One split's rows, in a fixed order, plus the bytes a scan actually reads."""

    split: str
    rows: tuple[FittedRow, ...]

    @property
    def column_names(self) -> tuple[str, ...]:
        return self.rows[0].vector.fitted_names if self.rows else ()

    def canonical_bytes(self) -> bytes:
        ordered = sorted(self.rows, key=lambda row: str(row.candidate_id))
        return "\n".join([self.split, *[row.canonical_line() for row in ordered]]).encode()

    @property
    def content_hash(self) -> str:
        return sha256(self.canonical_bytes()).hexdigest()

    @property
    def groups(self) -> frozenset[str]:
        return frozenset(row.group for row in self.rows)

    def column(self, name: str) -> tuple[float, ...]:
        index = self.column_names.index(name)
        return tuple(row.vector.fitted_numbers[index] for row in self.rows)

    @property
    def labels(self) -> tuple[bool, ...]:
        return tuple(row.accepted for row in self.rows)


class MatrixScan(HashedExperienceContract):
    """One scan's verdict, with what it found rather than only whether it passed."""

    name: NonEmptyStr
    passed: bool
    detail: NonEmptyStr
    offenders: tuple[NonEmptyStr, ...] = ()


class FittedMatrixReport(HashedExperienceContract):
    """The immutable validation report. Every scan must pass for a fit to be legitimate."""

    encoder_version: NonEmptyStr
    feature_contract_hash: Sha256Hex
    fit_matrix_hash: Sha256Hex
    calibration_matrix_hash: Sha256Hex
    fit_rows: int = Field(ge=1)
    calibration_rows: int = Field(ge=1)
    fit_groups: int = Field(ge=1)
    calibration_groups: int = Field(ge=1)
    column_names: tuple[NonEmptyStr, ...] = Field(min_length=1)
    near_duplicate_threshold: str
    maximum_cross_split_similarity: str
    scans: tuple[MatrixScan, ...] = Field(min_length=1)
    created_at: UtcDatetime

    @property
    def clean(self) -> bool:
        return all(scan.passed for scan in self.scans)

    @property
    def failures(self) -> tuple[MatrixScan, ...]:
        return tuple(scan for scan in self.scans if not scan.passed)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def _row_signature(row: FittedRow) -> tuple[float, ...]:
    return tuple(row.vector.numbers) + tuple(row.vector.embedding)


def separation(values: Sequence[float], labels: Sequence[bool]) -> float:
    """How well one column orders the labels, as the area under the ROC curve.

    Returned folded to `[0.5, 1]`: a column that predicts the label perfectly *inverted* is
    exactly as much an oracle as one that predicts it directly.
    """
    positives = [value for value, label in zip(values, labels, strict=True) if label]
    negatives = [value for value, label in zip(values, labels, strict=True) if not label]
    if not positives or not negatives:
        return PERFECT_SEPARATION
    wins = sum(
        1.0 if high > low else 0.5 if high == low else 0.0
        for high, low in product(positives, negatives)
    )
    area = wins / (len(positives) * len(negatives))
    return max(area, 1.0 - area)


def _forbidden_fields(
    matrix: FittedMatrix, contract: CorrectionFeatureContract | CorrectionFeatureContractV2
) -> MatrixScan:
    offenders = tuple(name for name in matrix.column_names if contract.rejects(name))
    return MatrixScan(
        name="no_forbidden_field_reaches_the_matrix",
        passed=not offenders,
        detail=(
            f"{len(matrix.column_names)} columns, all on the {contract.encoder_version} allowlist"
            if not offenders
            else f"{len(offenders)} column(s) are not on the allowlist"
        ),
        offenders=offenders,
    )


def _chronology(rows: Sequence[FittedRow]) -> MatrixScan:
    offenders = tuple(str(row.candidate_id) for row in rows if row.outcome_at < row.sealed_at)
    return MatrixScan(
        name="every_feature_record_precedes_its_outcome",
        passed=not offenders,
        detail=(
            f"{len(rows)} rows were sealed before the verifier ran"
            if not offenders
            else f"{len(offenders)} row(s) postdate their own outcome"
        ),
        offenders=offenders,
    )


def _source_chain(rows: Sequence[FittedRow]) -> MatrixScan:
    """One candidate, one sealed feature record, one observation. Anything else is a guess."""
    offenders: list[str] = []
    seen_candidates: set[UUID] = set()
    seen_observations: set[UUID] = set()
    for row in rows:
        if row.candidate_id in seen_candidates or row.observation_id in seen_observations:
            offenders.append(str(row.candidate_id))
        seen_candidates.add(row.candidate_id)
        seen_observations.add(row.observation_id)
        if row.vector.content_hash() != row.sealed_feature_hash:
            offenders.append(str(row.candidate_id))
    return MatrixScan(
        name="every_row_resolves_to_one_pre_outcome_source_chain",
        passed=not offenders,
        detail=(
            f"{len(rows)} rows, each reproducing the feature hash its seal recorded"
            if not offenders
            else f"{len(set(offenders))} row(s) are duplicated or do not reproduce their seal"
        ),
        offenders=tuple(sorted(set(offenders))),
    )


def _group_split(fit: FittedMatrix, calibration: FittedMatrix) -> MatrixScan:
    shared = sorted(fit.groups & calibration.groups)
    return MatrixScan(
        name="no_group_crosses_the_split",
        passed=not shared,
        detail=(
            f"{len(fit.groups)} fit groups and {len(calibration.groups)} calibration groups "
            "share none"
            if not shared
            else f"{len(shared)} group(s) appear in both splits"
        ),
        offenders=tuple(shared),
    )


def _contradictions(rows: Sequence[FittedRow]) -> MatrixScan:
    by_signature: dict[tuple[float, ...], set[bool]] = {}
    for row in rows:
        by_signature.setdefault(_row_signature(row), set()).add(row.accepted)
    offenders = tuple(
        str(index) for index, labels in enumerate(by_signature.values()) if len(labels) > 1
    )
    return MatrixScan(
        name="no_identical_row_carries_two_labels",
        passed=not offenders,
        detail=(
            f"{len(by_signature)} distinct feature signatures, none labelled both ways"
            if not offenders
            else f"{len(offenders)} signature(s) appear with both labels"
        ),
        offenders=offenders,
    )


def _near_duplicates(
    fit: FittedMatrix, calibration: FittedMatrix, *, threshold: float
) -> tuple[MatrixScan, float]:
    offenders: list[str] = []
    highest = 0.0
    for held in calibration.rows:
        signature = _row_signature(held)
        for fitted in fit.rows:
            similarity = _cosine(signature, _row_signature(fitted))
            highest = max(highest, similarity)
            if similarity >= threshold:
                offenders.append(f"{fitted.candidate_id}~{held.candidate_id}")
    return (
        MatrixScan(
            name="no_near_duplicate_crosses_the_split",
            passed=not offenders,
            detail=(
                f"highest cross-split similarity {highest:.6f} against a floor of {threshold}"
                if not offenders
                else f"{len(offenders)} pair(s) at or above {threshold}"
            ),
            offenders=tuple(sorted(set(offenders))),
        ),
        highest,
    )


def _label_derived(matrix: FittedMatrix) -> MatrixScan:
    labels = matrix.labels
    offenders = tuple(
        name
        for name in matrix.column_names
        if separation(matrix.column(name), labels) >= PERFECT_SEPARATION
    )
    return MatrixScan(
        name="no_column_derives_the_label",
        passed=not offenders,
        detail=(
            f"no column of {len(matrix.column_names)} separates the labels without exception"
            if not offenders
            else f"{len(offenders)} column(s) separate the labels perfectly"
        ),
        offenders=offenders,
    )


def _finite_and_in_range(matrix: FittedMatrix) -> MatrixScan:
    """Every v2 scalar is in [0, 1], every MiniLM channel in [-1, 1], and all are finite."""
    embedding = set(FITTED_FEATURE_V2_EMBEDDING)
    offenders: list[str] = []
    for name in matrix.column_names:
        low = -1.0 if name in embedding else 0.0
        for index, value in enumerate(matrix.column(name)):
            if not isfinite(value) or not low <= value <= 1.0:
                offenders.append(f"{name}[{index}]")
    return MatrixScan(
        name="every_fitted_dimension_is_finite_and_in_range",
        passed=not offenders,
        detail=(
            f"all {len(matrix.column_names)} fitted dimensions are finite and in range"
            if not offenders
            else f"{len(offenders)} fitted value(s) are non-finite or out of range"
        ),
        offenders=tuple(offenders),
    )


def _encoder_identity(rows: Sequence[FittedRow], expected: str) -> MatrixScan:
    offenders = tuple(
        str(row.candidate_id) for row in rows if row.vector.encoder_version != expected
    )
    return MatrixScan(
        name="every_row_has_one_encoder_identity",
        passed=not offenders,
        detail=(
            f"all {len(rows)} rows use {expected}"
            if not offenders
            else f"{len(offenders)} row(s) use another encoder"
        ),
        offenders=offenders,
    )


def scan_matrices(
    fit: FittedMatrix,
    calibration: FittedMatrix,
    *,
    created_at: datetime,
    contract: CorrectionFeatureContract | CorrectionFeatureContractV2 | None = None,
    near_duplicate_threshold: float = NEAR_DUPLICATE_SIMILARITY,
) -> FittedMatrixReport:
    """Run every scan over the serialized matrices and record what each one found."""
    if not fit.rows or not calibration.rows:
        raise ValueError("a matrix scan needs both splits; an empty one cannot be checked")
    encoder_version = fit.rows[0].vector.encoder_version
    if any(row.vector.encoder_version != encoder_version for row in (*fit.rows, *calibration.rows)):
        raise ValueError("every fitted row must use the same encoder version")
    expected_columns = fit.rows[0].vector.fitted_names
    if any(
        row.vector.fitted_names != expected_columns
        or len(row.vector.fitted_numbers) != len(expected_columns)
        for row in (*fit.rows, *calibration.rows)
    ):
        raise ValueError("every fitted row must use the same ordered columns")
    if fit.column_names != calibration.column_names:
        raise ValueError("the two splits were encoded differently and cannot be compared")
    if contract is None:
        feature_contract = (
            CorrectionFeatureContractV2()
            if encoder_version == ENCODER_VERSION_V2
            else CorrectionFeatureContract()
        )
    else:
        feature_contract = contract
    combined = fit.rows + calibration.rows
    near_duplicate, highest = _near_duplicates(fit, calibration, threshold=near_duplicate_threshold)
    scans: tuple[MatrixScan, ...] = (
        _forbidden_fields(fit, feature_contract),
        _chronology(combined),
        _source_chain(combined),
        _group_split(fit, calibration),
        _contradictions(combined),
        near_duplicate,
        _label_derived(fit),
        _label_derived(calibration),
    )
    if encoder_version == ENCODER_VERSION_V2:
        scans = (
            scans[0],
            _finite_and_in_range(fit),
            _finite_and_in_range(calibration),
            _encoder_identity(combined, encoder_version),
            *scans[1:],
        )
    return FittedMatrixReport(
        encoder_version=encoder_version,
        feature_contract_hash=feature_contract.content_hash,
        fit_matrix_hash=fit.content_hash,
        calibration_matrix_hash=calibration.content_hash,
        fit_rows=len(fit.rows),
        calibration_rows=len(calibration.rows),
        fit_groups=len(fit.groups),
        calibration_groups=len(calibration.groups),
        column_names=fit.column_names,
        near_duplicate_threshold=f"{near_duplicate_threshold}",
        maximum_cross_split_similarity=f"{highest:.6f}",
        scans=scans,
        created_at=created_at,
    )
