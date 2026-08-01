"""S21D2-050 and S21D2-052: a model that is data, and a loader that can only build one thing.

The learned plane's standing rule is that it never executes an artifact. D2 needs a model on
disk anyway, so the model is canonical JSON and the loader is narrow: no format dispatch, no
class name in the payload, no import path. A tampered artifact can produce a wrong ranker or
no ranker — never a different kind of object.

Every test below is a refusal, a round trip, or a canonicalisation check. The refusals are
what make "inert" a property rather than an intention.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID

import pytest

from cognitive_os.domain.learned import LearnedArtifactFormat
from cognitive_os.infrastructure.learned.artifacts import UNSAFE_TO_DESERIALISE
from cognitive_os.learning.correction_artifact import (
    LOADABLE_FORMATS,
    MAXIMUM_EXEMPLARS,
    CorrectionArtifactError,
    CorrectionArtifactPayload,
    ExemplarPayload,
    build_payload,
    canonical_bytes,
    load_correction_ranker,
)
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionEncoder,
    CorrectionKnn,
    Exemplar,
    NumericBounds,
)

from .test_correction_ranking import _bounds, _features

HASH = "a" * 64
TRAINING = UUID(int=1)
CALIBRATION = UUID(int=2)


def _exemplars(count: int = 3) -> list[Exemplar]:
    encoder = CorrectionEncoder(_bounds())
    return [
        Exemplar(
            vector=encoder.encode(_features(hunk_count=index + 1)),
            accepted=index % 2 == 0,
        )
        for index in range(count)
    ]


def _payload(**overrides: object) -> CorrectionArtifactPayload:
    exemplars = _exemplars()
    payload = build_payload(
        component_revision=1,
        ranker=CorrectionKnn(exemplars),
        exemplars=exemplars,
        encoder_version="correction-ranking-v1",
        code_version="21d2",
        training_dataset_id=TRAINING,
        calibration_dataset_id=CALIBRATION,
        example_manifest_hash=HASH,
        split_manifest_hash=HASH,
        feature_schema_hash=HASH,
        embedding_model_id="sentence-transformers/all-MiniLM-L6-v2",
        embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        embedding_dimension=len(exemplars[0].vector.embedding),
        numeric_lower=dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
        numeric_upper=dict.fromkeys(NUMERIC_FEATURE_NAMES, 100.0),
    )
    return payload.model_copy(update=overrides) if overrides else payload


def _load(data: bytes, **overrides: object):
    fields: dict[str, object] = {
        "expected_component_id": CorrectionKnn.component_id,
        "expected_revision": 1,
        "expected_surface": CorrectionKnn.surface,
    }
    fields.update(overrides)
    return load_correction_ranker(data, **fields)  # type: ignore[arg-type]


class TestTheFormatIsInertAndDeclared:
    def test_json_is_a_learned_artifact_format(self) -> None:
        assert LearnedArtifactFormat.JSON.value == "json"

    def test_joblib_is_still_unsafe_and_still_not_loadable(self) -> None:
        assert LearnedArtifactFormat.JOBLIB in UNSAFE_TO_DESERIALISE
        assert LearnedArtifactFormat.JOBLIB not in LOADABLE_FORMATS

    def test_json_is_the_only_loadable_format(self) -> None:
        assert {LearnedArtifactFormat.JSON} == LOADABLE_FORMATS

    def test_the_payload_never_carries_its_own_hash(self) -> None:
        """A blob that embeds its own hash cannot be verified without excluding it first."""
        document = json.loads(canonical_bytes(_payload()).decode())

        assert "content_hash" not in document


class TestCanonicalBytesAreStable:
    def test_the_same_payload_serialises_identically(self) -> None:
        assert canonical_bytes(_payload()) == canonical_bytes(_payload())

    def test_keys_are_sorted_and_whitespace_free(self) -> None:
        data = canonical_bytes(_payload())
        document = json.loads(data.decode())

        assert (
            data
            == json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        )

    def test_a_changed_threshold_changes_the_bytes(self) -> None:
        assert canonical_bytes(_payload()) != canonical_bytes(
            _payload(confidence_floor=Decimal("0.9"))
        )


class TestTheRoundTripRebuildsTheSameRanker:
    def test_a_stored_ranker_loads_back(self) -> None:
        ranker, payload = _load(canonical_bytes(_payload()))

        assert ranker.size == 3
        assert payload.component_id == CorrectionKnn.component_id

    def test_the_reloaded_ranker_ranks_identically(self) -> None:
        """Byte replay is worth nothing if the reloaded model decides differently."""
        exemplars = _exemplars()
        original = CorrectionKnn(
            exemplars,
            similarity_floor=Decimal("0"),
            agreement_floor=Decimal("0"),
            confidence_floor=Decimal("0"),
        )
        stored = build_payload(
            component_revision=1,
            ranker=original,
            exemplars=exemplars,
            encoder_version="correction-ranking-v1",
            code_version="21d2",
            training_dataset_id=TRAINING,
            calibration_dataset_id=CALIBRATION,
            example_manifest_hash=HASH,
            split_manifest_hash=HASH,
            feature_schema_hash=HASH,
            embedding_model_id="m",
            embedding_revision="r",
            embedding_dimension=len(exemplars[0].vector.embedding),
            numeric_lower=dict.fromkeys(NUMERIC_FEATURE_NAMES, 0.0),
            numeric_upper=dict.fromkeys(NUMERIC_FEATURE_NAMES, 100.0),
        )
        reloaded, _ = _load(canonical_bytes(stored))

        encoder = CorrectionEncoder(_bounds())
        candidates = {
            "a": encoder.encode(_features()),
            "b": encoder.encode(_features(hunk_count=7)),
        }
        assert original.rank(candidates, baseline_order=("a", "b")).ordered_candidate_ids == (
            reloaded.rank(candidates, baseline_order=("a", "b")).ordered_candidate_ids
        )

    def test_the_thresholds_survive_the_round_trip(self) -> None:
        reloaded, _ = _load(canonical_bytes(_payload(k=9, confidence_floor=Decimal("0.75"))))

        assert reloaded.k == 9
        assert reloaded.confidence_floor == Decimal("0.75")


class TestTheLoaderRefusesEverythingElse:
    def test_a_wrong_media_type_is_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="media type"):
            _load(canonical_bytes(_payload()), media_type="application/octet-stream")

    def test_oversized_bytes_are_refused_before_parsing(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="above the"):
            _load(canonical_bytes(_payload()), maximum_bytes=10)

    def test_non_utf8_bytes_are_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="not UTF-8"):
            _load(b"\xff\xfe\x00")

    def test_non_json_bytes_are_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="not JSON"):
            _load(b"this is not json")

    def test_a_json_array_is_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="a JSON object"):
            _load(b"[1, 2, 3]")

    def test_a_payload_that_embeds_a_hash_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["content_hash"] = HASH

        with pytest.raises(CorrectionArtifactError, match="must not embed its own hash"):
            _load(json.dumps(document).encode())

    def test_an_unknown_field_is_refused(self) -> None:
        """`extra="forbid"`: a field nobody declared is a different artifact."""
        document = json.loads(canonical_bytes(_payload()).decode())
        document["load_this_module"] = "os.system"

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(document).encode())

    def test_a_wrong_component_is_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="belongs to component"):
            _load(canonical_bytes(_payload()), expected_component_id="learned.knn.something_else")

    def test_a_wrong_revision_is_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="is revision"):
            _load(canonical_bytes(_payload()), expected_revision=2)

    def test_a_wrong_surface_is_refused(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="serves"):
            _load(canonical_bytes(_payload()), expected_surface="skill.selection")

    @pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
    def test_a_non_finite_number_is_refused(self, value: str) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["exemplars"][0]["embedding"][0] = float(value)

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(document).encode())

    def test_exemplars_encoded_differently_are_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["exemplars"][0]["values"] = document["exemplars"][0]["values"][:-1]

        with pytest.raises(CorrectionArtifactError, match="not all encoded the same way"):
            _load(json.dumps(document).encode())

    def test_a_declared_dimension_that_disagrees_with_the_exemplars_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["embedding_dimension"] = 999

        with pytest.raises(CorrectionArtifactError, match="but the artifact declares"):
            _load(json.dumps(document).encode())

    def test_missing_numeric_bounds_are_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["numeric_lower"] = document["numeric_lower"][:-1]

        with pytest.raises(CorrectionArtifactError, match="do not cover the encoder's features"):
            _load(json.dumps(document).encode())

    def test_a_threshold_outside_the_unit_interval_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["similarity_floor"] = "1.5"

        with pytest.raises(CorrectionArtifactError, match="proportion"):
            _load(json.dumps(document).encode())

    def test_an_empty_exemplar_set_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["exemplars"] = []

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(document).encode())

    def test_too_many_exemplars_are_refused(self) -> None:
        assert MAXIMUM_EXEMPLARS == 5_000
        document = json.loads(canonical_bytes(_payload()).decode())
        document["exemplars"] = document["exemplars"] * 2_000

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(document).encode())

    def test_an_unknown_schema_name_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()).decode())
        document["schema_name"] = "something-else"

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(document).encode())


class TestExemplarPayloadValidation:
    def test_a_finite_exemplar_validates(self) -> None:
        payload = ExemplarPayload(values=(("a", 1.0),), embedding=(0.5,), accepted=True)

        assert payload.accepted

    def test_an_infinite_feature_is_refused(self) -> None:
        with pytest.raises(ValueError, match="finite number"):
            ExemplarPayload(values=(("a", float("inf")),), embedding=(0.5,), accepted=True)

    def test_an_infinite_embedding_component_is_refused(self) -> None:
        with pytest.raises(ValueError, match="finite number"):
            ExemplarPayload(values=(("a", 1.0),), embedding=(float("nan"),), accepted=True)


def test_the_bounds_helper_round_trips_through_the_payload() -> None:
    bounds = NumericBounds.from_training([dict.fromkeys(NUMERIC_FEATURE_NAMES, 3.0)])
    payload = _payload()

    assert {name for name, _ in payload.numeric_lower} == set(bounds.lower)
