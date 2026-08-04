from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import pytest

from cognitive_os.learning.correction_features import (
    PendingFeatureV2,
    SealedFeatureRecordSetV2,
    SealedFeatureRecordV2,
    feature_input_v2,
    raw_numeric_row_v2,
    seal_feature_records_v2,
)
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (
    ENCODER_VERSION,
    ENCODER_VERSION_V2,
    CorrectionEncoderV2,
    CorrectionEncodingError,
    CorrectionFeatureVector,
    NumericBoundsV2,
)
from cognitive_os.learning.correction_source import canonical_source_bytes


def _embedding(seed: int = 0) -> tuple[float, ...]:
    return tuple(((index + seed) % 17 - 8) / 10 for index in range(384))


def _features(source: str, seed: int = 0):
    return feature_input_v2(
        candidate_source=source,
        canonical_candidate_source_embedding=_embedding(seed),
    )


def _bounds(*features) -> NumericBoundsV2:
    rows = [raw_numeric_row_v2(item) for item in features]
    # A second distinct row makes the clip/scale parameters replay-visible in the test.
    rows.append({name: value + 2.0 for name, value in rows[0].items()})
    return NumericBoundsV2.from_training(rows)


def test_v2_encodes_exactly_six_scalars_and_384_named_embedding_channels() -> None:
    features = _features("def add(x, y):\n    return x + y\n")
    vector = CorrectionEncoderV2(_bounds(features)).encode(features)

    assert vector.encoder_version == ENCODER_VERSION_V2
    assert vector.names == FITTED_FEATURE_V2_SCALARS
    assert vector.fitted_names == FITTED_FEATURE_V2_ALLOWLIST
    assert len(vector.fitted_numbers) == 390
    assert "changed_file_count" not in vector.fitted_names
    assert "query_to_candidate_cosine" not in vector.fitted_names


def test_excluded_inputs_and_coherent_rename_leave_v2_features_identical() -> None:
    left = "def total(values):\n    return sum(item for item in values)\n"
    right = "def aggregate(numbers):\n    return sum(number for number in numbers)\n"
    embedding = _embedding()
    left_features = _features(left)
    right_features = feature_input_v2(
        candidate_source=right,
        canonical_candidate_source_embedding=embedding,
    )
    bounds = _bounds(left_features, right_features)

    assert canonical_source_bytes(left) == canonical_source_bytes(right)
    assert CorrectionEncoderV2(bounds).encode(left_features) == CorrectionEncoderV2(bounds).encode(
        right_features
    )


def test_semantic_mutation_changes_bytes_hash_and_seeded_vector() -> None:
    left = "def accepted(value):\n    return value > 3\n"
    right = "def accepted(value):\n    return value >= 3\n"
    left_features = _features(left, 0)
    right_features = _features(right, 1)
    bounds = _bounds(left_features, right_features)
    encoder = CorrectionEncoderV2(bounds)

    assert left_features.canonical_candidate_source != right_features.canonical_candidate_source
    assert (
        sha256(left_features.canonical_candidate_source).digest()
        != sha256(right_features.canonical_candidate_source).digest()
    )
    assert encoder.encode(left_features) != encoder.encode(right_features)


def test_v1_and_v2_vectors_are_explicitly_incompatible() -> None:
    v1 = CorrectionFeatureVector(
        encoder_version=ENCODER_VERSION,
        values=(("candidate_source_ast_node_count", 0.0),),
        embedding=(0.0,) * 384,
    )
    features = _features("value = 1\n")
    v2 = CorrectionEncoderV2(_bounds(features)).encode(features)

    assert v1.encoder_version != v2.encoder_version
    assert v1.canonical_bytes() != v2.canonical_bytes()
    assert v1.content_hash() != v2.content_hash()


def test_v2_embedding_shape_and_values_fail_closed() -> None:
    short = feature_input_v2(
        candidate_source="value = 1\n", canonical_candidate_source_embedding=(0.0,) * 383
    )
    with pytest.raises(CorrectionEncodingError, match="384 embedding"):
        CorrectionEncoderV2(_bounds(short)).encode(short)

    invalid = feature_input_v2(
        candidate_source="value = 1\n",
        canonical_candidate_source_embedding=(*((0.0,) * 383), float("nan")),
    )
    with pytest.raises(CorrectionEncodingError, match="finite"):
        CorrectionEncoderV2(_bounds(invalid)).encode(invalid)


def test_v2_bounds_and_replayed_feature_hash_fail_closed() -> None:
    with pytest.raises(CorrectionEncodingError, match="exactly six"):
        NumericBoundsV2(lower={}, upper={})
    invalid_row = {name: 0.0 for name in FITTED_FEATURE_V2_SCALARS}
    invalid_row[FITTED_FEATURE_V2_SCALARS[0]] = float("nan")
    with pytest.raises(CorrectionEncodingError, match="finite"):
        NumericBoundsV2.from_training((invalid_row,))

    features = _features("value = 1\n")
    vector = CorrectionEncoderV2(_bounds(features)).encode(features)
    with pytest.raises(ValueError, match="hash does not match"):
        SealedFeatureRecordV2(
            candidate_id=UUID(int=1),
            task_id=UUID(int=2),
            repository_group="group-a",
            encoder_version=ENCODER_VERSION_V2,
            canonical_source_hash="a" * 64,
            values=vector.values,
            embedding=vector.embedding,
            feature_vector_hash="b" * 64,
        )


def test_v2_seal_replays_exactly_and_refuses_post_outcome_creation() -> None:
    sealed_at = datetime(2026, 8, 4, 9, tzinfo=UTC)
    source = "def increment(value):\n    return value + 1\n"
    features = _features(source)
    bounds = _bounds(features)
    pending = [
        PendingFeatureV2(
            candidate_id=UUID(int=1),
            task_id=UUID(int=2),
            repository_group="group-a",
            candidate_source=source,
            canonical_candidate_source_embedding=_embedding(),
        )
    ]
    arguments = dict(
        pending=pending,
        partition="training",
        campaign_manifest_hash="a" * 64,
        bounds=bounds,
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        embedding_tree_digest="b" * 64,
        code_revision="test-revision",
        sealed_at=sealed_at,
    )

    first = seal_feature_records_v2(**arguments)
    replay = seal_feature_records_v2(**arguments)
    assert first.canonical_json() == replay.canonical_json()
    assert first.content_hash == replay.content_hash
    assert first.sealed_at == sealed_at
    assert first.feature_contract_hash == CorrectionFeatureContractV2().content_hash
    assert first.record_for(UUID(int=1)).feature_vector_hash

    tampered = first.model_dump(exclude={"content_hash"})
    tampered["numeric_lower"] = (
        (FITTED_FEATURE_V2_SCALARS[0], float("inf")),
        *first.numeric_lower[1:],
    )
    with pytest.raises(ValueError, match="invalid bounds"):
        SealedFeatureRecordSetV2(**tampered)

    with pytest.raises(ValueError, match="strictly before"):
        seal_feature_records_v2(
            **arguments,
            earliest_outcome_at=sealed_at - timedelta(microseconds=1),
        )
