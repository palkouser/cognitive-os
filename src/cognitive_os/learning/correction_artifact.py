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
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from math import isfinite
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex
from cognitive_os.domain.learned import LearnedArtifactFormat, LearnedComponentState
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (
    ENCODER_VERSION_V2,
    NUMERIC_FEATURE_NAMES,
    CorrectionFeatureVector,
    CorrectionKnn,
    Exemplar,
)
from cognitive_os.learning.pairwise_contrastive import (
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
)
from cognitive_os.learning.selective_operating_point import DERIVATION_RULE

CORRECTION_ARTIFACT_MEDIA_TYPE = "application/vnd.cognitive-os.correction-ranker+json"
CORRECTION_ARTIFACT_SCHEMA = "correction-ranker-artifact"
CORRECTION_ARTIFACT_SCHEMA_VERSION = 1

#: S21D3-050. The v2 schema is a second name, not a second version number under the first.
#: A v1 reader handed v2 bytes must fail on the name it does not know rather than on a
#: field it happens to be missing, because the second failure depends on which fields the
#: two shapes happen to share and the first does not.
CORRECTION_ARTIFACT_SCHEMA_V2 = "correction-ranking-artifact-v2"
CORRECTION_ARTIFACT_SCHEMA_V2_VERSION = 2

#: S21D5-050. A third name for the same reason the second one exists. v2 is k-NN-shaped by
#: construction — `exemplars` with `min_length=1`, `k`, `embedding_weight` and three proportion
#: floors — and a direction has none of those. Relaxing them so a direction could reuse the
#: schema would let an exemplar-free v2 artifact load, which is exactly the
#: check-that-passes-without-touching-its-question defect the D4 report catalogued twelve times.
CORRECTION_ARTIFACT_SCHEMA_V3 = "correction-ranking-artifact-v3"
CORRECTION_ARTIFACT_SCHEMA_V3_VERSION = 3

#: The hypothesis classes this loader can build. A payload naming anything else is refused
#: before construction: an artifact whose class the reader does not implement is not a model
#: the reader can be wrong about, it is bytes it cannot read at all.
IMPLEMENTED_HYPOTHESIS_CLASSES = frozenset({HYPOTHESIS_CLASS})

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


class CorrectionArtifactPayloadV2(ImmutableContractModel):
    """The v2 ranker as bytes: the canonicaliser that produced it, and what it was fitted on.

    Everything v1 could not say. v1 named an `encoder_version` string and left the reader to
    trust that the string meant the canonicaliser it thinks it means; v2 names the normaliser,
    the grammar, the canonical prefix and the payload expression, so a replayed encoding is
    checkable rather than assumed. It also names the channels in order, because a bound set
    that covers the right feature *names* proves nothing about the order the values were
    written in, and a reordered channel list is a silently different model.

    Still deliberately absent, exactly as in v1: any hash of itself, any class or import
    path, any dataset body, any candidate or task identity, any label.
    """

    schema_name: NonEmptyStr = CORRECTION_ARTIFACT_SCHEMA_V2
    schema_version: int = Field(default=CORRECTION_ARTIFACT_SCHEMA_V2_VERSION, ge=2)

    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    learner_kind: NonEmptyStr
    #: The descriptor these bytes were fitted for. Lineage the loader can check without
    #: reaching for the ledger, so a v2 artifact cannot be read against another component's
    #: descriptor and still look valid.
    descriptor_hash: Sha256Hex
    code_revision: NonEmptyStr

    #: The v2 canonicaliser, spelled out rather than referenced.
    encoder_version: NonEmptyStr = ENCODER_VERSION_V2
    normalizer_version: NonEmptyStr
    python_grammar: NonEmptyStr
    canonical_prefix_hex: NonEmptyStr
    canonical_payload: NonEmptyStr
    feature_contract_hash: Sha256Hex

    #: Named channels in fitted order: six scalars then 384 embedding components.
    feature_channels: tuple[NonEmptyStr, ...] = Field(min_length=1)

    training_dataset_id: UUID
    calibration_dataset_id: UUID
    example_manifest_hash: Sha256Hex
    split_manifest_hash: Sha256Hex
    selection_manifest_hash: Sha256Hex
    member_manifest_hash: Sha256Hex
    feature_schema_hash: Sha256Hex

    embedding_model_id: NonEmptyStr
    embedding_revision: NonEmptyStr
    embedding_tree_digest: NonEmptyStr
    embedding_dimension: int = Field(ge=1)

    numeric_lower: tuple[tuple[NonEmptyStr, float], ...]
    numeric_upper: tuple[tuple[NonEmptyStr, float], ...]

    exemplars: tuple[ExemplarPayload, ...] = Field(min_length=1, max_length=MAXIMUM_EXEMPLARS)

    #: The frozen grid point this artifact is. Named so two artifacts fitted from the same
    #: rows under different settings cannot be confused for one another.
    setting_identity: Sha256Hex
    k: int = Field(ge=1)
    embedding_weight: Decimal
    similarity_floor: Decimal
    agreement_floor: Decimal
    confidence_floor: Decimal

    maximum_inference_ms: int = Field(ge=1)
    declared_limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def the_payload_is_internally_consistent(self) -> CorrectionArtifactPayloadV2:
        if self.schema_name != CORRECTION_ARTIFACT_SCHEMA_V2:
            raise ValueError(f"unknown artifact schema {self.schema_name!r}")
        if self.encoder_version != ENCODER_VERSION_V2:
            raise ValueError(f"a v2 artifact carries {ENCODER_VERSION_V2!r}, not its predecessor")
        for name, value in (
            ("embedding_weight", self.embedding_weight),
            ("similarity_floor", self.similarity_floor),
            ("agreement_floor", self.agreement_floor),
            ("confidence_floor", self.confidence_floor),
        ):
            if not Decimal("0") <= value <= Decimal("1"):
                raise ValueError(f"{name} must be a proportion in [0, 1]")

        if self.feature_channels != FITTED_FEATURE_V2_ALLOWLIST:
            raise ValueError("the stored channels are not the v2 fitted allowlist in fitted order")
        bound_names = tuple(name for name, _ in self.numeric_lower)
        if bound_names != FITTED_FEATURE_V2_SCALARS:
            raise ValueError("the stored numeric bounds are not the six v2 scalars in order")
        if tuple(name for name, _ in self.numeric_upper) != bound_names:
            raise ValueError("the lower and upper bounds describe different features")

        shapes = {
            (len(item.embedding), tuple(n for n, _ in item.values)) for item in self.exemplars
        }
        if len(shapes) != 1:
            raise ValueError("exemplars were not all encoded the same way")
        dimension, names = next(iter(shapes))
        if dimension != self.embedding_dimension:
            raise ValueError(
                f"exemplars carry {dimension}-dimensional embeddings but the artifact declares "
                f"{self.embedding_dimension}"
            )
        if names != FITTED_FEATURE_V2_SCALARS:
            raise ValueError("exemplar scalars are not the six v2 channels in fitted order")
        return self


class CorrectionArtifactPayloadV3(ImmutableContractModel):
    """The v3 ranker as bytes: a fitted direction where v2 carried an exemplar set.

    Everything v2 says about *how the features were made* is here unchanged and checked the
    same way — normaliser, grammar, canonical prefix and payload, feature contract, the 390
    channels in fitted order, the six numeric bounds, the embedding model and its tree digest.
    D5 changes no encoder, no channel and no fitted representation; it changes the function
    fitted on top of them.

    What replaces the exemplar set is one direction: 390 weights in allowlist order, the ridge
    that regularised them, the pair and group counts they were fitted from, and the margin
    floor below which the ranker declines. Where a v2 artifact grows with its fitting pool —
    one 390-channel vector per row, 720 of them at D5's size — a v3 artifact is the same 390
    floats whatever it was fitted on.

    The operating point comes in with S21D4-050's fields: the derived point's identity, the
    derivation rule and the calibration certificate hash. The rule is checked against the
    released constant, not merely stored, because a model carrying its own account of how its
    threshold was derived can say anything. Its wording names the k-NN confidence, and that is
    correct: §S21D5-016's only substitution is the *quantity* scored — the top-two projection
    margin instead of neighbourhood acceptance mass — and `derive_zero_error_point` treats a
    confidence as an opaque ordered score, so the certification spine is inherited rather than
    rewritten. Which quantity was scored is named by `hypothesis_class`.

    Still deliberately absent, exactly as in v1 and v2: any hash of itself, any class or import
    path, any dataset body, any candidate or task identity, any label.
    """

    schema_name: NonEmptyStr = CORRECTION_ARTIFACT_SCHEMA_V3
    schema_version: int = Field(default=CORRECTION_ARTIFACT_SCHEMA_V3_VERSION, ge=3)

    component_id: NonEmptyStr
    component_revision: int = Field(ge=1)
    surface: NonEmptyStr
    learner_kind: NonEmptyStr
    descriptor_hash: Sha256Hex
    code_revision: NonEmptyStr

    #: The v2 canonicaliser, carried verbatim. A v3 artifact under another normaliser would be
    #: a different model reading different numbers under the same channel names.
    encoder_version: NonEmptyStr = ENCODER_VERSION_V2
    normalizer_version: NonEmptyStr
    python_grammar: NonEmptyStr
    canonical_prefix_hex: NonEmptyStr
    canonical_payload: NonEmptyStr
    feature_contract_hash: Sha256Hex

    feature_channels: tuple[NonEmptyStr, ...] = Field(min_length=1)

    training_dataset_id: UUID
    calibration_dataset_id: UUID
    example_manifest_hash: Sha256Hex
    split_manifest_hash: Sha256Hex
    selection_manifest_hash: Sha256Hex
    member_manifest_hash: Sha256Hex
    feature_schema_hash: Sha256Hex

    embedding_model_id: NonEmptyStr
    embedding_revision: NonEmptyStr
    embedding_tree_digest: NonEmptyStr
    embedding_dimension: int = Field(ge=1)

    numeric_lower: tuple[tuple[NonEmptyStr, float], ...]
    numeric_upper: tuple[tuple[NonEmptyStr, float], ...]

    #: The direction. One weight per fitted channel, in `FITTED_FEATURE_V2_ALLOWLIST` order —
    #: the names are not repeated here because `feature_channels` already carries them and two
    #: orderings of one list is a way for them to disagree.
    weights: tuple[float, ...] = Field(min_length=1)
    regularization: Decimal
    fitted_group_count: int = Field(ge=1)
    fitted_pair_count: int = Field(ge=1)
    hypothesis_class: NonEmptyStr

    #: The operating point, S21D4-050's fields. `margin_floor` is the derived threshold itself.
    margin_floor: Decimal
    operating_point_hash: Sha256Hex
    operating_point_derivation_rule: NonEmptyStr
    calibration_certificate_hash: Sha256Hex

    #: The frozen grid point this artifact is, so two directions fitted from the same rows
    #: under different ridges cannot be confused for one another.
    setting_identity: Sha256Hex

    maximum_inference_ms: int = Field(ge=1)
    declared_limitations: tuple[NonEmptyStr, ...] = ()

    @model_validator(mode="after")
    def the_payload_is_internally_consistent(self) -> CorrectionArtifactPayloadV3:
        if self.schema_name != CORRECTION_ARTIFACT_SCHEMA_V3:
            raise ValueError(f"unknown artifact schema {self.schema_name!r}")
        if self.encoder_version != ENCODER_VERSION_V2:
            raise ValueError(
                f"a v3 artifact carries {ENCODER_VERSION_V2!r}: D5 changes the fitted function, "
                "not the encoder"
            )
        if self.hypothesis_class not in IMPLEMENTED_HYPOTHESIS_CLASSES:
            raise ValueError(
                f"hypothesis class {self.hypothesis_class!r} is not one this loader implements; "
                f"known: {sorted(IMPLEMENTED_HYPOTHESIS_CLASSES)}"
            )
        if self.operating_point_derivation_rule != DERIVATION_RULE:
            raise ValueError(
                "the artifact states a derivation rule that is not the released one; a model "
                "may not carry its own account of how its threshold was derived"
            )

        if self.feature_channels != FITTED_FEATURE_V2_ALLOWLIST:
            raise ValueError("the stored channels are not the v2 fitted allowlist in fitted order")
        if len(self.weights) != len(FITTED_FEATURE_V2_ALLOWLIST):
            raise ValueError(
                f"the direction carries {len(self.weights)} weights against "
                f"{len(FITTED_FEATURE_V2_ALLOWLIST)} fitted channels"
            )
        if any(not isfinite(weight) for weight in self.weights):
            raise ValueError("a fitted weight must be a finite number")
        if self.regularization <= 0:
            raise ValueError("the ridge term must be positive; zero is a different class")
        if self.margin_floor < 0:
            raise ValueError("a negative margin floor admits decisions the model disowns")

        bound_names = tuple(name for name, _ in self.numeric_lower)
        if bound_names != FITTED_FEATURE_V2_SCALARS:
            raise ValueError("the stored numeric bounds are not the six v2 scalars in order")
        if tuple(name for name, _ in self.numeric_upper) != bound_names:
            raise ValueError("the lower and upper bounds describe different features")
        return self


#: Every artifact shape this module can read. Named so a dispatcher can be typed without
#: widening to `object`, and so adding a fourth is a change here rather than in every caller.
AnyCorrectionArtifactPayload = (
    CorrectionArtifactPayload | CorrectionArtifactPayloadV2 | CorrectionArtifactPayloadV3
)


def canonical_bytes(payload: AnyCorrectionArtifactPayload) -> bytes:
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


def _document(data: bytes, *, media_type: str, maximum_bytes: int, schema: str) -> dict[str, Any]:
    """The byte-level refusals, shared by both schema versions.

    The schema name is checked here rather than left to the model, so v1/v2 confusion is
    reported as what it is instead of as whichever field the two shapes disagree about
    first — and so it is reported before any payload is constructed at all.
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
    if document.get("schema_name") != schema:
        raise CorrectionArtifactError(
            f"artifact declares schema {document.get('schema_name')!r}, not {schema!r}"
        )
    return document


def load_correction_ranker(
    data: bytes,
    *,
    expected_component_id: str,
    expected_revision: int,
    expected_surface: str,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[CorrectionKnn, CorrectionArtifactPayload]:
    """Read verified v1 bytes into a `CorrectionKnn`, or refuse. Never anything else.

    Every check is a refusal to hand back something that looks like a model: wrong media
    type, oversized, not UTF-8, not JSON, not this schema, the wrong component, the wrong
    revision, the wrong surface, or numbers that are not numbers. The caller has already
    verified the bytes against their lineage hash; this verifies that they *say* what the
    lineage claims.
    """
    document = _document(
        data, media_type=media_type, maximum_bytes=maximum_bytes, schema=CORRECTION_ARTIFACT_SCHEMA
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


def load_correction_ranker_v2(
    data: bytes,
    *,
    expected_component_id: str,
    expected_revision: int,
    expected_surface: str,
    expected_descriptor_hash: str,
    contract: CorrectionFeatureContractV2 | None = None,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[CorrectionKnn, CorrectionArtifactPayloadV2]:
    """Read verified v2 bytes into a `CorrectionKnn`, or refuse before building anything.

    Beyond v1's refusals, the lineage is mandatory rather than declarative: the descriptor
    hash the caller expects, and the canonicaliser identity the frozen v2 feature contract
    declares, both have to be the ones in the bytes. An artifact that names the right
    component under the wrong normaliser is a different model with the same label.
    """
    declared = contract or CorrectionFeatureContractV2()
    document = _document(
        data,
        media_type=media_type,
        maximum_bytes=maximum_bytes,
        schema=CORRECTION_ARTIFACT_SCHEMA_V2,
    )
    try:
        payload = CorrectionArtifactPayloadV2.model_validate(document)
    except Exception as error:  # pydantic raises its own type; the verdict is the same
        raise CorrectionArtifactError(
            f"artifact does not match the declared schema: {error}"
        ) from error

    for label, found, expected in (
        ("component", payload.component_id, expected_component_id),
        ("revision", payload.component_revision, expected_revision),
        ("surface", payload.surface, expected_surface),
        ("descriptor", payload.descriptor_hash, expected_descriptor_hash),
        ("normaliser", payload.normalizer_version, declared.normalizer_version),
        ("grammar", payload.python_grammar, declared.python_grammar),
        ("canonical prefix", payload.canonical_prefix_hex, declared.canonical_prefix_hex),
        ("canonical payload", payload.canonical_payload, declared.canonical_payload),
        ("feature contract", payload.feature_contract_hash, declared.content_hash),
        ("embedding model", payload.embedding_model_id, declared.embedding_model),
        ("embedding tree", payload.embedding_tree_digest, declared.embedding_tree_digest),
        ("embedding dimension", payload.embedding_dimension, declared.embedding_dimensions),
    ):
        if found != expected:
            raise CorrectionArtifactError(
                f"artifact {label} is {found!r}, not the expected {expected!r}"
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


def load_correction_ranker_v3(
    data: bytes,
    *,
    expected_component_id: str,
    expected_revision: int,
    expected_surface: str,
    expected_descriptor_hash: str,
    contract: CorrectionFeatureContractV2 | None = None,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[PairwiseContrastiveRanker, CorrectionArtifactPayloadV3]:
    """Read verified v3 bytes into a `PairwiseContrastiveRanker`, or refuse before building.

    Exactly as strict as v2 and in the same order: the byte-level refusals, then the schema,
    then every declared identity against what the caller expected and what the frozen feature
    contract declares. This loader can build one class and no other, which is the property that
    makes a tampered artifact a refusal or a wrong ranker and never a different kind of thing.
    """
    declared = contract or CorrectionFeatureContractV2()
    document = _document(
        data,
        media_type=media_type,
        maximum_bytes=maximum_bytes,
        schema=CORRECTION_ARTIFACT_SCHEMA_V3,
    )
    try:
        payload = CorrectionArtifactPayloadV3.model_validate(document)
    except Exception as error:  # pydantic raises its own type; the verdict is the same
        raise CorrectionArtifactError(
            f"artifact does not match the declared schema: {error}"
        ) from error

    for label, found, expected in (
        ("component", payload.component_id, expected_component_id),
        ("revision", payload.component_revision, expected_revision),
        ("surface", payload.surface, expected_surface),
        ("descriptor", payload.descriptor_hash, expected_descriptor_hash),
        ("normaliser", payload.normalizer_version, declared.normalizer_version),
        ("grammar", payload.python_grammar, declared.python_grammar),
        ("canonical prefix", payload.canonical_prefix_hex, declared.canonical_prefix_hex),
        ("canonical payload", payload.canonical_payload, declared.canonical_payload),
        ("feature contract", payload.feature_contract_hash, declared.content_hash),
        ("embedding model", payload.embedding_model_id, declared.embedding_model),
        ("embedding tree", payload.embedding_tree_digest, declared.embedding_tree_digest),
        ("embedding dimension", payload.embedding_dimension, declared.embedding_dimensions),
    ):
        if found != expected:
            raise CorrectionArtifactError(
                f"artifact {label} is {found!r}, not the expected {expected!r}"
            )
    if payload.component_id != PairwiseContrastiveRanker.component_id:
        raise CorrectionArtifactError("artifact does not describe the correction ranker")

    try:
        model = PairwiseContrastiveModel(
            encoder_version=payload.encoder_version,
            feature_names=tuple(payload.feature_channels),
            weights=tuple(payload.weights),
            regularization=str(payload.regularization),
            fitted_group_count=payload.fitted_group_count,
            fitted_pair_count=payload.fitted_pair_count,
        )
    except ValueError as error:
        raise CorrectionArtifactError(f"the stored direction is not a model: {error}") from error
    return PairwiseContrastiveRanker(model, margin_floor=payload.margin_floor), payload


def correction_artifact_schema(data: bytes) -> str:
    """The schema name the bytes declare, or a refusal. Reads nothing else.

    Separate from the loaders because a caller holding unknown bytes should be able to learn
    which reader they are for without running one and catching its refusal.
    """
    try:
        document: Any = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CorrectionArtifactError("artifact bytes are not UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise CorrectionArtifactError("a correction artifact is a JSON object")
    name = document.get("schema_name")
    if not isinstance(name, str) or not name:
        raise CorrectionArtifactError("the artifact declares no schema name")
    return name


def load_correction_ranker_any(
    data: bytes,
    *,
    expected_component_id: str,
    expected_revision: int,
    expected_surface: str,
    expected_descriptor_hash: str | None = None,
    contract: CorrectionFeatureContractV2 | None = None,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[CorrectionKnn | PairwiseContrastiveRanker, AnyCorrectionArtifactPayload]:
    """Route bytes to the one reader their `schema_name` names. Never guesses.

    The descriptor is required for v2 and v3 and refused for v1, rather than ignored where it
    does not apply: a caller that passes a descriptor hash believes it is being checked, and a
    schema with no descriptor field would silently not check it. That asymmetry is the whole
    reason this dispatcher exists as one function instead of a caller trying each loader until
    one stops raising — which would report the last refusal rather than the real one.
    """
    schema = correction_artifact_schema(data)
    if schema == CORRECTION_ARTIFACT_SCHEMA:
        if expected_descriptor_hash is not None:
            raise CorrectionArtifactError(
                "a v1 artifact carries no descriptor hash, so one cannot be checked against it"
            )
        return load_correction_ranker(
            data,
            expected_component_id=expected_component_id,
            expected_revision=expected_revision,
            expected_surface=expected_surface,
            media_type=media_type,
            maximum_bytes=maximum_bytes,
        )
    if schema in (CORRECTION_ARTIFACT_SCHEMA_V2, CORRECTION_ARTIFACT_SCHEMA_V3):
        if expected_descriptor_hash is None:
            raise CorrectionArtifactError(
                f"{schema!r} binds a descriptor hash; loading one without the descriptor to "
                "check against would drop a lineage check the schema exists to carry"
            )
        loader = (
            load_correction_ranker_v2
            if schema == CORRECTION_ARTIFACT_SCHEMA_V2
            else load_correction_ranker_v3
        )
        return loader(
            data,
            expected_component_id=expected_component_id,
            expected_revision=expected_revision,
            expected_surface=expected_surface,
            expected_descriptor_hash=expected_descriptor_hash,
            contract=contract,
            media_type=media_type,
            maximum_bytes=maximum_bytes,
        )
    known = sorted(
        (
            CORRECTION_ARTIFACT_SCHEMA,
            CORRECTION_ARTIFACT_SCHEMA_V2,
            CORRECTION_ARTIFACT_SCHEMA_V3,
        )
    )
    raise CorrectionArtifactError(
        f"artifact declares schema {schema!r}, which this loader does not know; known: {known}"
    )


def build_payload_v3(
    *,
    component_revision: int,
    descriptor_hash: str,
    code_revision: str,
    ranker: PairwiseContrastiveRanker,
    training_dataset_id: UUID,
    calibration_dataset_id: UUID,
    example_manifest_hash: str,
    split_manifest_hash: str,
    selection_manifest_hash: str,
    member_manifest_hash: str,
    feature_schema_hash: str,
    embedding_revision: str,
    numeric_lower: Mapping[str, float],
    numeric_upper: Mapping[str, float],
    setting_identity: str,
    operating_point_hash: str,
    calibration_certificate_hash: str,
    contract: CorrectionFeatureContractV2 | None = None,
    maximum_inference_ms: int = 250,
    declared_limitations: Sequence[str] = (),
) -> CorrectionArtifactPayloadV3:
    """Assemble a v3 payload from a fitted ranker, taking the canonicaliser from the contract.

    The canonicaliser fields and the derivation rule are copied from their frozen sources
    rather than passed in, for the same reason v2 copies its: a builder that let a caller name
    its own normaliser — or its own account of how the threshold was derived — would let the
    loader's identity check pass on an artifact nobody fitted under the frozen contract.
    """
    declared = contract or CorrectionFeatureContractV2()
    model = ranker.model
    return CorrectionArtifactPayloadV3(
        component_id=PairwiseContrastiveRanker.component_id,
        component_revision=component_revision,
        surface=PairwiseContrastiveRanker.surface,
        learner_kind="pairwise_contrastive_linear",
        descriptor_hash=descriptor_hash,
        code_revision=code_revision,
        normalizer_version=declared.normalizer_version,
        python_grammar=declared.python_grammar,
        canonical_prefix_hex=declared.canonical_prefix_hex,
        canonical_payload=declared.canonical_payload,
        feature_contract_hash=declared.content_hash,
        feature_channels=FITTED_FEATURE_V2_ALLOWLIST,
        training_dataset_id=training_dataset_id,
        calibration_dataset_id=calibration_dataset_id,
        example_manifest_hash=example_manifest_hash,
        split_manifest_hash=split_manifest_hash,
        selection_manifest_hash=selection_manifest_hash,
        member_manifest_hash=member_manifest_hash,
        feature_schema_hash=feature_schema_hash,
        embedding_model_id=declared.embedding_model,
        embedding_revision=embedding_revision,
        embedding_tree_digest=declared.embedding_tree_digest,
        embedding_dimension=declared.embedding_dimensions,
        numeric_lower=tuple(
            (name, float(numeric_lower[name])) for name in FITTED_FEATURE_V2_SCALARS
        ),
        numeric_upper=tuple(
            (name, float(numeric_upper[name])) for name in FITTED_FEATURE_V2_SCALARS
        ),
        weights=tuple(model.weights),
        regularization=Decimal(model.regularization),
        fitted_group_count=model.fitted_group_count,
        fitted_pair_count=model.fitted_pair_count,
        hypothesis_class=HYPOTHESIS_CLASS,
        margin_floor=ranker.margin_floor,
        operating_point_hash=operating_point_hash,
        operating_point_derivation_rule=DERIVATION_RULE,
        calibration_certificate_hash=calibration_certificate_hash,
        setting_identity=setting_identity,
        maximum_inference_ms=maximum_inference_ms,
        declared_limitations=tuple(declared_limitations),
    )


def build_payload_v2(
    *,
    component_revision: int,
    descriptor_hash: str,
    code_revision: str,
    ranker: CorrectionKnn,
    exemplars: Sequence[Exemplar],
    training_dataset_id: UUID,
    calibration_dataset_id: UUID,
    example_manifest_hash: str,
    split_manifest_hash: str,
    selection_manifest_hash: str,
    member_manifest_hash: str,
    feature_schema_hash: str,
    embedding_revision: str,
    numeric_lower: Mapping[str, float],
    numeric_upper: Mapping[str, float],
    setting_identity: str,
    contract: CorrectionFeatureContractV2 | None = None,
    maximum_inference_ms: int = 250,
    declared_limitations: Sequence[str] = (),
) -> CorrectionArtifactPayloadV2:
    """Assemble a v2 payload from a fitted ranker, taking the canonicaliser from the contract.

    The canonicaliser fields are copied rather than passed: a builder that let a caller name
    its own normaliser would let the loader's identity check pass on an artifact nobody fitted
    under the frozen contract.
    """
    declared = contract or CorrectionFeatureContractV2()
    return CorrectionArtifactPayloadV2(
        component_id=CorrectionKnn.component_id,
        component_revision=component_revision,
        surface=CorrectionKnn.surface,
        learner_kind="bounded_cosine_knn",
        descriptor_hash=descriptor_hash,
        code_revision=code_revision,
        normalizer_version=declared.normalizer_version,
        python_grammar=declared.python_grammar,
        canonical_prefix_hex=declared.canonical_prefix_hex,
        canonical_payload=declared.canonical_payload,
        feature_contract_hash=declared.content_hash,
        feature_channels=FITTED_FEATURE_V2_ALLOWLIST,
        training_dataset_id=training_dataset_id,
        calibration_dataset_id=calibration_dataset_id,
        example_manifest_hash=example_manifest_hash,
        split_manifest_hash=split_manifest_hash,
        selection_manifest_hash=selection_manifest_hash,
        member_manifest_hash=member_manifest_hash,
        feature_schema_hash=feature_schema_hash,
        embedding_model_id=declared.embedding_model,
        embedding_revision=embedding_revision,
        embedding_tree_digest=declared.embedding_tree_digest,
        embedding_dimension=declared.embedding_dimensions,
        numeric_lower=tuple(
            (name, float(numeric_lower[name])) for name in FITTED_FEATURE_V2_SCALARS
        ),
        numeric_upper=tuple(
            (name, float(numeric_upper[name])) for name in FITTED_FEATURE_V2_SCALARS
        ),
        exemplars=tuple(
            ExemplarPayload(
                values=item.vector.values, embedding=item.vector.embedding, accepted=item.accepted
            )
            for item in exemplars
        ),
        setting_identity=setting_identity,
        k=ranker.k,
        embedding_weight=ranker.embedding_weight,
        similarity_floor=ranker.similarity_floor,
        agreement_floor=ranker.agreement_floor,
        confidence_floor=ranker.confidence_floor,
        maximum_inference_ms=maximum_inference_ms,
        declared_limitations=tuple(declared_limitations),
    )


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


# --------------------------------------------------------------- the direct evaluation boundary


class EvaluationPurpose(StrEnum):
    """The three reads an unapproved artifact is allowed to serve. Routing is not among them."""

    CALIBRATION = "calibration"
    FINAL = "final"
    SHADOW = "shadow"


#: The only lifecycle states the direct builder will read an artifact in. A component past
#: SHADOW has a resolver, an approval and a configuration; giving it a second way in would
#: make all three optional.
DIRECT_EVALUATION_STATES = frozenset(
    {LearnedComponentState.REGISTERED, LearnedComponentState.SHADOW}
)


@dataclass(frozen=True, slots=True)
class DirectEvaluationCapability:
    """Authority to turn one exact artifact into a ranker, outside the runtime.

    S21D3-052. Controlled evaluation needs a model before any resolver would hand one out:
    calibration and the final batches read it while the component is unapproved, and shadow
    reads it while the component is in SHADOW. The danger is that such a path becomes a way
    around the resolver, so this is not a flag — it is a capability naming one artifact hash,
    one purpose, and one lifecycle state, and every identity the bytes must agree with.

    `LearnedRuntimeResolver` neither holds nor constructs one of these. That is the boundary:
    the application runtime cannot select this path, because nothing on it has the authority
    to say which artifact would be read.
    """

    purpose: EvaluationPurpose
    component_state: LearnedComponentState
    artifact_hash: str
    component_id: str
    component_revision: int
    surface: str
    descriptor_hash: str
    training_dataset_id: UUID
    split_manifest_hash: str
    member_manifest_hash: str
    selection_manifest_hash: str

    def __post_init__(self) -> None:
        if self.component_state not in DIRECT_EVALUATION_STATES:
            raise CorrectionArtifactError(
                f"the direct evaluation boundary is closed in {self.component_state.value}: "
                "an approved component is read through the runtime resolver"
            )


def build_ranker_for_evaluation(
    data: bytes,
    *,
    capability: DirectEvaluationCapability,
    contract: CorrectionFeatureContractV2 | None = None,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[CorrectionKnn, CorrectionArtifactPayloadV2]:
    """Rehash the exact bytes, check every declared identity, then build. In that order.

    The rehash comes first because every check after it is a statement about *these* bytes.
    Validating a payload and then trusting that the store handed over the artifact the
    capability named is the time-of-check/time-of-use hole this exists to close.
    """
    digest = sha256(data).hexdigest()
    if digest != capability.artifact_hash:
        raise CorrectionArtifactError(
            f"artifact bytes hash to {digest}, not the {capability.artifact_hash} this "
            "capability authorises"
        )
    ranker, payload = load_correction_ranker_v2(
        data,
        expected_component_id=capability.component_id,
        expected_revision=capability.component_revision,
        expected_surface=capability.surface,
        expected_descriptor_hash=capability.descriptor_hash,
        contract=contract,
        media_type=media_type,
        maximum_bytes=maximum_bytes,
    )
    _evaluation_lineage(payload, capability)
    return ranker, payload


def _evaluation_lineage(
    payload: CorrectionArtifactPayloadV2 | CorrectionArtifactPayloadV3,
    capability: DirectEvaluationCapability,
) -> None:
    """The four dataset identities the capability names, checked against the payload's own."""
    for label, found, expected in (
        ("training dataset", payload.training_dataset_id, capability.training_dataset_id),
        ("split manifest", payload.split_manifest_hash, capability.split_manifest_hash),
        ("member manifest", payload.member_manifest_hash, capability.member_manifest_hash),
        (
            "selection manifest",
            payload.selection_manifest_hash,
            capability.selection_manifest_hash,
        ),
    ):
        if found != expected:
            raise CorrectionArtifactError(
                f"artifact {label} is {found!r}, not the expected {expected!r}"
            )


def build_ranker_for_evaluation_v3(
    data: bytes,
    *,
    capability: DirectEvaluationCapability,
    contract: CorrectionFeatureContractV2 | None = None,
    media_type: str = CORRECTION_ARTIFACT_MEDIA_TYPE,
    maximum_bytes: int = MAXIMUM_ARTIFACT_BYTES,
) -> tuple[PairwiseContrastiveRanker, CorrectionArtifactPayloadV3]:
    """The v3 door through the same boundary, in the same order: rehash, then read, then check.

    A separate function rather than a widened `build_ranker_for_evaluation`, because that one's
    return type is `CorrectionKnn` and every released caller depends on getting exactly that.
    A caller holding bytes of unknown schema uses `load_correction_ranker_any`; a caller opening
    the evaluation boundary already knows which model it authorised.
    """
    digest = sha256(data).hexdigest()
    if digest != capability.artifact_hash:
        raise CorrectionArtifactError(
            f"artifact bytes hash to {digest}, not the {capability.artifact_hash} this "
            "capability authorises"
        )
    ranker, payload = load_correction_ranker_v3(
        data,
        expected_component_id=capability.component_id,
        expected_revision=capability.component_revision,
        expected_surface=capability.surface,
        expected_descriptor_hash=capability.descriptor_hash,
        contract=contract,
        media_type=media_type,
        maximum_bytes=maximum_bytes,
    )
    _evaluation_lineage(payload, capability)
    return ranker, payload
