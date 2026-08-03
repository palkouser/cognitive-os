"""The correction ranker as inert bytes, and the only thing allowed to read them back.

S21D2-050 and S21D2-052. An artifact is data supplied by whatever produced it. The learned
plane's standing rule is that it never executes such data, which is why `LearnedArtifactStore`
has no `load` and why `JOBLIB` stays in `UNSAFE_TO_DESERIALISE` with no runtime path. D2 needs
a model on disk anyway, so the model has to be something that can be *read* rather than
*reconstructed*: canonical JSON, a declared schema, finite numbers, and a loader that can only
ever build one class.

Two details are easy to get wrong and are fixed here deliberately.

The payload does not contain its own hash. A blob that embeds `content_hash` cannot be
verified without first knowing which bytes to exclude, and every implementation disagrees
about that. The Artifact Store's hash over the canonical bytes is the content authority, and
the payload names everything else it depends on.

The loader returns a `CorrectionKnn`, not an object. There is no format dispatch, no class
name in the payload and no import path — so a tampered artifact can produce a wrong ranker or
no ranker, and never a different kind of thing.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from math import isfinite
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.learned import LearnedArtifactFormat
from cognitive_os.learning.correction_ranking import (
    NUMERIC_FEATURE_NAMES,
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
)

CORRECTION_ARTIFACT_MEDIA_TYPE = "application/vnd.cognitive-os.correction-ranker+json"
CORRECTION_ARTIFACT_SCHEMA = "correction-ranker-artifact"
CORRECTION_ARTIFACT_SCHEMA_VERSION = 1

#: A bound, not a target. An exemplar set larger than this is a corpus, and a corpus loaded
#: into every runtime task is a latency budget nobody agreed to.
MAXIMUM_EXEMPLARS = 5_000
MAXIMUM_ARTIFACT_BYTES = 64 * 1024 * 1024


class CorrectionArtifactError(ValueError):
    """The bytes are not a usable correction-ranker artifact. Never a partial load."""


class ExemplarPayload(ImmutableContractModel):
    """One fitted exemplar: the vector it was encoded to, and the verifier's answer."""

    #: `(name, value)` pairs in the encoder's fixed order. Names travel with values so a
    #: reordered encoder cannot silently realign an old exemplar onto new features.
    values: tuple[tuple[NonEmptyStr, float], ...] = Field(min_length=1)
    embedding: tuple[float, ...] = Field(min_length=1)
    accepted: bool

    @model_validator(mode="after")
    def numbers_are_finite(self) -> ExemplarPayload:
        for _, value in self.values:
            if not isfinite(value):
                raise ValueError("a fitted feature must be a finite number")
        if any(not isfinite(item) for item in self.embedding):
            raise ValueError("an embedding component must be a finite number")
        return self


class CorrectionArtifactPayload(ImmutableContractModel):
    """Everything needed to rebuild the exact ranker, and nothing that answers a label.

    Deliberately absent: any `content_hash` of itself, any class or import path, any dataset
    body, any candidate or task identity. The dataset and split IDs are here because replay
    needs to name what it was fitted on; the members are not, because they live in manifests.
    """

    schema_name: NonEmptyStr = CORRECTION_ARTIFACT_SCHEMA
    schema_version: int = Field(default=CORRECTION_ARTIFACT_SCHEMA_VERSION, ge=1)

    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    learner_kind: NonEmptyStr
    encoder_version: NonEmptyStr
    code_version: NonEmptyStr

    training_dataset_id: UUID
    calibration_dataset_id: UUID
    example_manifest_hash: Sha256Hex
    split_manifest_hash: Sha256Hex
    feature_schema_hash: Sha256Hex

    embedding_model_id: NonEmptyStr
    embedding_revision: NonEmptyStr
    embedding_dimension: int = Field(ge=1)

    #: Clip-and-scale parameters, so a replayed encoding is the fitted encoding.
    numeric_lower: tuple[tuple[NonEmptyStr, float], ...]
    numeric_upper: tuple[tuple[NonEmptyStr, float], ...]

    exemplars: tuple[ExemplarPayload, ...] = Field(min_length=1, max_length=MAXIMUM_EXEMPLARS)

    k: int = Field(ge=1)
    embedding_weight: Decimal
    similarity_floor: Decimal
    agreement_floor: Decimal
    confidence_floor: Decimal

    maximum_inference_ms: int = Field(ge=1)
    declared_limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def the_payload_is_internally_consistent(self) -> CorrectionArtifactPayload:
        if self.schema_name != CORRECTION_ARTIFACT_SCHEMA:
            raise ValueError(f"unknown artifact schema {self.schema_name!r}")
        for name, value in (
            ("embedding_weight", self.embedding_weight),
            ("similarity_floor", self.similarity_floor),
            ("agreement_floor", self.agreement_floor),
            ("confidence_floor", self.confidence_floor),
        ):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be a proportion in [0, 1]")

        bound_names = {name for name, _ in self.numeric_lower}
        if bound_names != set(NUMERIC_FEATURE_NAMES):
            raise ValueError("the stored numeric bounds do not cover the encoder's features")
        if {name for name, _ in self.numeric_upper} != bound_names:
            raise ValueError("the lower and upper bounds describe different features")

        shapes = {
            (item.embedding.__len__(), tuple(n for n, _ in item.values)) for item in self.exemplars
        }
        if len(shapes) != 1:
            raise ValueError("exemplars were not all encoded the same way")
        dimension, _ = next(iter(shapes))
        if dimension != self.embedding_dimension:
            raise ValueError(
                f"exemplars carry {dimension}-dimensional embeddings but the artifact declares "
                f"{self.embedding_dimension}"
            )
        return self


def canonical_bytes(payload: CorrectionArtifactPayload) -> bytes:
    """The exact bytes the Artifact Store hashes. Sorted keys, no whitespace, UTF-8.

    Canonical rather than merely valid: two builds of the same model must produce the same
    hash, or the lineage that binds a model to its evidence proves nothing.
    """
    return json.dumps(
        json.loads(payload.model_dump_json()),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def _rebuild_vector(payload: ExemplarPayload, encoder_version: str) -> CorrectionFeatureVector:
    return CorrectionFeatureVector(
        encoder_version=encoder_version,
        values=tuple((name, value) for name, value in payload.values),
        embedding=tuple(payload.embedding),
    )


def load_correction_ranker(
    data: bytes,
    *,
    expected_component_id: str,
    expected_revision: int,
    expected_surface: str,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[CorrectionKnn, CorrectionArtifactPayload]:
    """Read verified bytes into a `CorrectionKnn`, or refuse. Never anything else.

    Every check is a refusal to hand back something that looks like a model: wrong media
    type, oversized, not UTF-8, not JSON, not this schema, the wrong component, the wrong
    revision, the wrong surface, or numbers that are not numbers. The caller has already
    verified the bytes against their lineage hash; this verifies that they *say* what the
    lineage claims.
    """
    if media_type != CORRECTION_ARTIFACT_MEDIA_TYPE:
        raise CorrectionArtifactError(
            f"media type {media_type!r} is not {CORRECTION_ARTIFACT_MEDIA_TYPE!r}"
        )
    if len(data) > maximum_bytes:
        raise CorrectionArtifactError(
            f"artifact is {len(data)} bytes, above the {maximum_bytes}-byte bound"
        )
    try:
        document: Any = json.loads(data.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise CorrectionArtifactError("artifact bytes are not UTF-8") from error
    except json.JSONDecodeError as error:
        raise CorrectionArtifactError("artifact bytes are not JSON") from error
    if not isinstance(document, dict):
        raise CorrectionArtifactError("a correction artifact is a JSON object")
    if "content_hash" in document:
        raise CorrectionArtifactError(
            "the payload must not embed its own hash; the Artifact Store is the authority"
        )

    try:
        payload = CorrectionArtifactPayload.model_validate(document)
    except Exception as error:  # pydantic raises its own type; the verdict is the same
        raise CorrectionArtifactError(
            f"artifact does not match the declared schema: {error}"
        ) from error

    if payload.component_id != expected_component_id:
        raise CorrectionArtifactError(
            f"artifact belongs to component {payload.component_id!r}, not {expected_component_id!r}"
        )
    if payload.component_revision != expected_revision:
        raise CorrectionArtifactError(
            f"artifact is revision {payload.component_revision}, not {expected_revision}"
        )
    if payload.surface != expected_surface:
        raise CorrectionArtifactError(
            f"artifact serves {payload.surface!r}, not {expected_surface!r}"
        )
    if payload.component_id != CorrectionKnn.component_id:
        raise CorrectionArtifactError("artifact does not describe the correction ranker")

    ranker = CorrectionKnn(
        [
            Exemplar(vector=_rebuild_vector(item, payload.encoder_version), accepted=item.accepted)
            for item in payload.exemplars
        ],
        k=payload.k,
        embedding_weight=payload.embedding_weight,
        similarity_floor=payload.similarity_floor,
        agreement_floor=payload.agreement_floor,
        confidence_floor=payload.confidence_floor,
    )
    return ranker, payload


def build_payload(
    *,
    component_revision: int,
    ranker: CorrectionKnn,
    exemplars: Sequence[Exemplar],
    encoder_version: str,
    code_version: str,
    training_dataset_id: UUID,
    calibration_dataset_id: UUID,
    example_manifest_hash: str,
    split_manifest_hash: str,
    feature_schema_hash: str,
    embedding_model_id: str,
    embedding_revision: str,
    embedding_dimension: int,
    numeric_lower: Mapping[str, float],
    numeric_upper: Mapping[str, float],
    maximum_inference_ms: int = 250,
    declared_limitations: Sequence[str] = (),
) -> CorrectionArtifactPayload:
    """Assemble the payload from a fitted ranker. Kept beside the loader so they cannot drift."""
    return CorrectionArtifactPayload(
        component_id=CorrectionKnn.component_id,
        component_revision=component_revision,
        surface=CorrectionKnn.surface,
        learner_kind="bounded_cosine_knn",
        encoder_version=encoder_version,
        code_version=code_version,
        training_dataset_id=training_dataset_id,
        calibration_dataset_id=calibration_dataset_id,
        example_manifest_hash=example_manifest_hash,
        split_manifest_hash=split_manifest_hash,
        feature_schema_hash=feature_schema_hash,
        embedding_model_id=embedding_model_id,
        embedding_revision=embedding_revision,
        embedding_dimension=embedding_dimension,
        numeric_lower=tuple((name, float(numeric_lower[name])) for name in NUMERIC_FEATURE_NAMES),
        numeric_upper=tuple((name, float(numeric_upper[name])) for name in NUMERIC_FEATURE_NAMES),
        exemplars=tuple(
            ExemplarPayload(
                values=item.vector.values, embedding=item.vector.embedding, accepted=item.accepted
            )
            for item in exemplars
        ),
        k=ranker.k,
        embedding_weight=ranker.embedding_weight,
        similarity_floor=ranker.similarity_floor,
        agreement_floor=ranker.agreement_floor,
        confidence_floor=ranker.confidence_floor,
        maximum_inference_ms=maximum_inference_ms,
        declared_limitations=tuple(declared_limitations),
    )


#: Named so a caller cannot accidentally hand the loader a format it must never read.
LOADABLE_FORMATS = frozenset({LearnedArtifactFormat.JSON})
