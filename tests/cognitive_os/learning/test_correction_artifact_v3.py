"""S21D5-050: the v3 artifact, its refusals, and the schema-name dispatch.

v3 exists because v2 is k-NN-shaped by construction. Every test here is about one of the two
things that makes a third schema worth its weight: that a direction round-trips through inert
canonical JSON into exactly one class, and that each refusal the frozen contract names actually
refuses — before anything is built, not after something wrong has been handed back.

The dispatch tests are the other half. A caller holding unknown bytes must get one refusal that
names the schema, not the last failure of three loaders tried in turn.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from cognitive_os.learning.correction_artifact import (
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    CORRECTION_ARTIFACT_SCHEMA,
    CORRECTION_ARTIFACT_SCHEMA_V2,
    CORRECTION_ARTIFACT_SCHEMA_V3,
    CorrectionArtifactError,
    CorrectionArtifactPayloadV3,
    build_payload_v3,
    canonical_bytes,
    correction_artifact_schema,
    load_correction_ranker_any,
    load_correction_ranker_v3,
)
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
)
from cognitive_os.learning.correction_ranking import ENCODER_VERSION_V2, CorrectionKnn
from cognitive_os.learning.pairwise_contrastive import (
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
)
from cognitive_os.learning.selective_operating_point import DERIVATION_RULE

DESCRIPTOR = "d" * 64
MANIFEST = "a" * 64
SELECTION = "b" * 64
MEMBERS = "c" * 64
SETTING = "e" * 64
POINT = "f" * 64
CERTIFICATE = "9" * 64
TRAINING = UUID(int=1)
CALIBRATION = UUID(int=2)


def _model(**overrides: Any) -> PairwiseContrastiveModel:
    fields: dict[str, Any] = {
        "encoder_version": ENCODER_VERSION_V2,
        "feature_names": FITTED_FEATURE_V2_ALLOWLIST,
        "weights": tuple(0.001 * (index + 1) for index in range(len(FITTED_FEATURE_V2_ALLOWLIST))),
        "regularization": "1",
        "fitted_group_count": 180,
        "fitted_pair_count": 720,
    }
    fields.update(overrides)
    return PairwiseContrastiveModel(**fields)


def _ranker(margin_floor: Decimal = Decimal("0.25")) -> PairwiseContrastiveRanker:
    return PairwiseContrastiveRanker(_model(), margin_floor=margin_floor)


def _payload(**overrides: Any) -> CorrectionArtifactPayloadV3:
    payload = build_payload_v3(
        component_revision=1,
        descriptor_hash=DESCRIPTOR,
        code_revision="21d5",
        ranker=_ranker(),
        training_dataset_id=TRAINING,
        calibration_dataset_id=CALIBRATION,
        example_manifest_hash=MANIFEST,
        split_manifest_hash=MANIFEST,
        selection_manifest_hash=SELECTION,
        member_manifest_hash=MEMBERS,
        feature_schema_hash=MANIFEST,
        embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        numeric_lower=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 0.0),
        numeric_upper=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 100.0),
        setting_identity=SETTING,
        operating_point_hash=POINT,
        calibration_certificate_hash=CERTIFICATE,
    )
    return payload.model_copy(update=overrides) if overrides else payload


def _load(data: bytes, **overrides: Any):
    fields: dict[str, Any] = {
        "expected_component_id": PairwiseContrastiveRanker.component_id,
        "expected_revision": 1,
        "expected_surface": PairwiseContrastiveRanker.surface,
        "expected_descriptor_hash": DESCRIPTOR,
    }
    fields.update(overrides)
    return load_correction_ranker_v3(data, **fields)


def _tampered(**changes: Any) -> bytes:
    """Mutate the canonical document directly: `model_copy` does not re-run the validators,
    and what is under test is what the *loader* does with bytes it did not build."""
    document = json.loads(canonical_bytes(_payload()))
    document.update(changes)
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


# ------------------------------------------------------------------- the round trip


def test_a_direction_round_trips_into_exactly_one_class() -> None:
    ranker, payload = _load(canonical_bytes(_payload()))
    assert isinstance(ranker, PairwiseContrastiveRanker)
    assert payload.schema_name == CORRECTION_ARTIFACT_SCHEMA_V3
    assert payload.schema_version == 3
    assert ranker.model.weights == _model().weights
    assert ranker.margin_floor == Decimal("0.25")
    assert ranker.model.content_hash() == _model().content_hash()


def test_the_payload_carries_no_hash_of_itself() -> None:
    """The Artifact Store's hash over the canonical bytes is the content authority."""
    assert "content_hash" not in json.loads(canonical_bytes(_payload()))


def test_the_direction_is_390_weights_in_allowlist_order() -> None:
    payload = _payload()
    assert payload.feature_channels == FITTED_FEATURE_V2_ALLOWLIST
    assert len(payload.weights) == len(FITTED_FEATURE_V2_ALLOWLIST) == 390


def test_the_artifact_does_not_grow_with_the_fitting_pool() -> None:
    """The measured claim §4.2 makes: a direction fitted on 720 pairs is the same 390 floats
    as one fitted on 72. A v2 artifact carries one vector per fitting row."""
    small = canonical_bytes(
        _payload().model_copy(update={"fitted_pair_count": 72, "fitted_group_count": 18})
    )
    assert len(canonical_bytes(_payload())) == pytest.approx(len(small), abs=8)


def test_the_canonicaliser_is_carried_from_v2_unchanged() -> None:
    payload = _payload()
    assert payload.encoder_version == ENCODER_VERSION_V2
    assert tuple(name for name, _ in payload.numeric_lower) == FITTED_FEATURE_V2_SCALARS


def test_the_derivation_rule_is_the_released_one() -> None:
    """Not merely stored: a model carrying its own account of how its threshold was derived
    could say anything, so the builder copies the constant and the loader checks it."""
    assert _payload().operating_point_derivation_rule == DERIVATION_RULE


# ------------------------------------------------------------------- the frozen refusals


def test_a_weight_vector_of_the_wrong_length_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="389 weights"):
        _load(_tampered(weights=[0.1] * 389))


def test_a_non_finite_weight_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="finite"):
        _load(_tampered(weights=[float("inf")] + [0.1] * 389))


def test_a_channel_list_that_is_not_the_allowlist_is_refused() -> None:
    reordered = list(FITTED_FEATURE_V2_ALLOWLIST)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(CorrectionArtifactError, match="fitted allowlist in fitted order"):
        _load(_tampered(feature_channels=reordered))


def test_a_non_positive_ridge_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="ridge term must be positive"):
        _load(_tampered(regularization="0"))


def test_a_negative_margin_floor_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="negative margin floor"):
        _load(_tampered(margin_floor="-0.1"))


def test_a_hypothesis_class_the_loader_does_not_implement_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="not one this loader implements"):
        _load(_tampered(hypothesis_class="pairwise-contrastive-linear-v2"))


def test_a_rewritten_derivation_rule_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="not the released one"):
        _load(_tampered(operating_point_derivation_rule="whatever I felt like"))


def test_a_v2_encoder_substitution_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="changes the fitted function"):
        _load(_tampered(encoder_version="correction-ranking-v1"))


def test_version_confusion_fails_on_the_name_before_anything_is_built() -> None:
    """A v3 reader handed v2 bytes must fail on the name it does not know, not on whichever
    field the two shapes happen to disagree about first."""
    with pytest.raises(CorrectionArtifactError, match="declares schema"):
        _load(_tampered(schema_name=CORRECTION_ARTIFACT_SCHEMA_V2))


def test_the_wrong_descriptor_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="artifact descriptor"):
        _load(canonical_bytes(_payload()), expected_descriptor_hash="0" * 64)


def test_a_payload_embedding_its_own_hash_is_refused() -> None:
    with pytest.raises(CorrectionArtifactError, match="must not embed its own hash"):
        _load(_tampered(content_hash="0" * 64))


# ------------------------------------------------------------------- the dispatch


def test_the_schema_name_is_readable_without_running_a_loader() -> None:
    assert correction_artifact_schema(canonical_bytes(_payload())) == CORRECTION_ARTIFACT_SCHEMA_V3


def test_the_dispatch_routes_v3_to_the_pairwise_ranker() -> None:
    ranker, payload = load_correction_ranker_any(
        canonical_bytes(_payload()),
        expected_component_id=PairwiseContrastiveRanker.component_id,
        expected_revision=1,
        expected_surface=PairwiseContrastiveRanker.surface,
        expected_descriptor_hash=DESCRIPTOR,
    )
    assert isinstance(ranker, PairwiseContrastiveRanker)
    assert isinstance(payload, CorrectionArtifactPayloadV3)


def test_the_dispatch_refuses_a_v3_load_with_no_descriptor_to_check() -> None:
    """Not ignored where it does not apply: dropping the check silently is the failure this
    dispatcher exists to make impossible."""
    with pytest.raises(CorrectionArtifactError, match="binds a descriptor hash"):
        load_correction_ranker_any(
            canonical_bytes(_payload()),
            expected_component_id=PairwiseContrastiveRanker.component_id,
            expected_revision=1,
            expected_surface=PairwiseContrastiveRanker.surface,
        )


def test_the_dispatch_refuses_a_descriptor_for_a_schema_that_has_none() -> None:
    """A caller passing a descriptor believes it is being checked. v1 has no field to check it
    against, so accepting the argument would be a check that never happened."""
    with pytest.raises(CorrectionArtifactError, match="v1 artifact carries no descriptor"):
        load_correction_ranker_any(
            json.dumps({"schema_name": CORRECTION_ARTIFACT_SCHEMA}).encode(),
            expected_component_id=CorrectionKnn.component_id,
            expected_revision=1,
            expected_surface=CorrectionKnn.surface,
            expected_descriptor_hash=DESCRIPTOR,
        )


def test_the_dispatch_refuses_a_schema_it_does_not_know() -> None:
    with pytest.raises(CorrectionArtifactError, match="does not know"):
        load_correction_ranker_any(
            json.dumps({"schema_name": "correction-ranking-artifact-v9"}).encode(),
            expected_component_id=PairwiseContrastiveRanker.component_id,
            expected_revision=1,
            expected_surface=PairwiseContrastiveRanker.surface,
            expected_descriptor_hash=DESCRIPTOR,
        )


def test_the_dispatch_refuses_bytes_that_declare_no_schema() -> None:
    with pytest.raises(CorrectionArtifactError, match="declares no schema name"):
        correction_artifact_schema(json.dumps({"weights": []}).encode())


def test_the_wrong_media_type_is_refused_before_the_schema() -> None:
    with pytest.raises(CorrectionArtifactError, match="media type"):
        _load(canonical_bytes(_payload()), media_type="application/json")
    assert CORRECTION_ARTIFACT_MEDIA_TYPE.endswith("+json")


def test_the_built_payload_names_the_implemented_class() -> None:
    assert _payload().hypothesis_class == HYPOTHESIS_CLASS
