"""S21D3-050 and S21D3-052: the v2 artifact, and the one door an unapproved model may enter by.

v1 named an encoder version and left the reader to trust the string. The v2 artifact names the
canonicaliser that produced it — normaliser, grammar, canonical prefix, payload expression, and
the frozen feature contract's own hash — so a replayed encoding is checkable rather than assumed.

The direct evaluation boundary exists because calibration, the final batches and shadow all need
a ranker before any resolver would hand one out. The risk is that such a path becomes a way
around the resolver, so it is a capability naming one artifact hash, one purpose and one
lifecycle state, and it rehashes the bytes before it reads a single field of them.
"""

from __future__ import annotations

import ast
import json
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest

from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.learning.correction_artifact import (
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    CORRECTION_ARTIFACT_SCHEMA_V2,
    CorrectionArtifactError,
    CorrectionArtifactPayloadV2,
    DirectEvaluationCapability,
    EvaluationPurpose,
    build_payload_v2,
    build_ranker_for_evaluation,
    canonical_bytes,
    load_correction_ranker,
    load_correction_ranker_v2,
)
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import (
    CorrectionEncoderV2,
    CorrectionKnn,
    Exemplar,
)

from .test_correction_ranking_v2 import _bounds, _features

DESCRIPTOR = "d" * 64
MANIFEST = "a" * 64
SELECTION = "b" * 64
MEMBERS = "c" * 64
SETTING = "e" * 64
TRAINING = UUID(int=1)
CALIBRATION = UUID(int=2)

SOURCES = (
    "def add(x, y):\n    return x + y\n",
    "def total(values):\n    return sum(values)\n",
    "def first(values):\n    return values[0]\n",
)


def _exemplars() -> list[Exemplar]:
    features = [_features(source, seed=index) for index, source in enumerate(SOURCES)]
    encoder = CorrectionEncoderV2(_bounds(*features))
    return [
        Exemplar(vector=encoder.encode(item), accepted=index % 2 == 0)
        for index, item in enumerate(features)
    ]


def _payload(**overrides: object) -> CorrectionArtifactPayloadV2:
    exemplars = _exemplars()
    payload = build_payload_v2(
        component_revision=1,
        descriptor_hash=DESCRIPTOR,
        code_revision="21d3",
        ranker=CorrectionKnn(exemplars),
        exemplars=exemplars,
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
    )
    return payload.model_copy(update=overrides) if overrides else payload


def _load(data: bytes, **overrides: object):
    fields: dict[str, object] = {
        "expected_component_id": CorrectionKnn.component_id,
        "expected_revision": 1,
        "expected_surface": CorrectionKnn.surface,
        "expected_descriptor_hash": DESCRIPTOR,
    }
    fields.update(overrides)
    return load_correction_ranker_v2(data, **fields)  # type: ignore[arg-type]


def _capability(**overrides: object) -> DirectEvaluationCapability:
    fields: dict[str, object] = {
        "purpose": EvaluationPurpose.CALIBRATION,
        "component_state": LearnedComponentState.SHADOW,
        "artifact_hash": sha256(canonical_bytes(_payload())).hexdigest(),
        "component_id": CorrectionKnn.component_id,
        "component_revision": 1,
        "surface": CorrectionKnn.surface,
        "descriptor_hash": DESCRIPTOR,
        "training_dataset_id": TRAINING,
        "split_manifest_hash": MANIFEST,
        "member_manifest_hash": MEMBERS,
        "selection_manifest_hash": SELECTION,
    }
    fields.update(overrides)
    return DirectEvaluationCapability(**fields)  # type: ignore[arg-type]


# ------------------------------------------------------------------ the v2 schema


class TestTheV2ArtifactSaysWhatProducedIt:
    def test_the_payload_names_the_canonicaliser_rather_than_referencing_it(self) -> None:
        contract = CorrectionFeatureContractV2()
        payload = _payload()

        assert payload.schema_name == CORRECTION_ARTIFACT_SCHEMA_V2
        assert payload.normalizer_version == contract.normalizer_version
        assert payload.python_grammar == contract.python_grammar
        assert payload.canonical_prefix_hex == contract.canonical_prefix_hex
        assert payload.canonical_payload == contract.canonical_payload
        assert payload.feature_contract_hash == contract.content_hash
        assert payload.embedding_tree_digest == contract.embedding_tree_digest

    def test_the_channels_are_the_fitted_allowlist_in_fitted_order(self) -> None:
        payload = _payload()

        assert payload.feature_channels == FITTED_FEATURE_V2_ALLOWLIST
        assert len(payload.feature_channels) == 390
        assert tuple(name for name, _ in payload.numeric_lower) == FITTED_FEATURE_V2_SCALARS

    def test_a_reordered_channel_list_is_a_different_model_and_is_refused(self) -> None:
        document = json.loads(canonical_bytes(_payload()))
        document["feature_channels"] = [
            *FITTED_FEATURE_V2_ALLOWLIST[1::-1],
            *FITTED_FEATURE_V2_ALLOWLIST[2:],
        ]

        with pytest.raises(CorrectionArtifactError, match="fitted allowlist in fitted order"):
            _load(json.dumps(document).encode())

    def test_canonical_bytes_are_order_independent_and_rehash_identically(self) -> None:
        payload = _payload()
        data = canonical_bytes(payload)
        shuffled = dict(reversed(list(json.loads(data).items())))

        assert json.dumps(shuffled, sort_keys=True, separators=(",", ":")).encode() == data
        assert sha256(canonical_bytes(_payload())).hexdigest() == sha256(data).hexdigest()

    def test_no_executable_type_class_or_import_path_is_present(self) -> None:
        document = json.loads(canonical_bytes(_payload()))
        flattened = json.dumps(document)

        assert not {"class", "type", "module", "import", "callable", "py/object"} & set(document)
        assert "cognitive_os." not in flattened
        assert "__" not in flattened


class TestVersionConfusionFailsBeforeAnythingIsBuilt:
    def test_the_v1_loader_refuses_v2_bytes_by_name(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="not 'correction-ranker-artifact'"):
            load_correction_ranker(
                canonical_bytes(_payload()),
                expected_component_id=CorrectionKnn.component_id,
                expected_revision=1,
                expected_surface=CorrectionKnn.surface,
            )

    def test_the_v2_loader_refuses_v1_bytes_by_name(self) -> None:
        v1 = json.loads(canonical_bytes(_payload()))
        v1["schema_name"] = "correction-ranker-artifact"

        with pytest.raises(CorrectionArtifactError, match="not 'correction-ranking-artifact-v2'"):
            _load(json.dumps(v1).encode())

    def test_a_missing_lineage_field_fails_before_model_construction(self) -> None:
        stripped = json.loads(canonical_bytes(_payload()))
        del stripped["member_manifest_hash"]

        with pytest.raises(CorrectionArtifactError, match="does not match the declared schema"):
            _load(json.dumps(stripped).encode())

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("normalizer_version", "cogos-python-alpha-normalizer-v1", "normaliser"),
            ("python_grammar", "3.11", "grammar"),
            ("feature_contract_hash", "f" * 64, "feature contract"),
            ("embedding_tree_digest", "0000000", "embedding tree"),
            ("descriptor_hash", "9" * 64, "descriptor"),
        ],
    )
    def test_a_canonicaliser_or_lineage_identity_that_drifted_is_refused(
        self, field: str, value: str, message: str
    ) -> None:
        document = json.loads(canonical_bytes(_payload()))
        document[field] = value

        with pytest.raises(CorrectionArtifactError, match=message):
            _load(json.dumps(document).encode())

    def test_a_valid_v2_artifact_round_trips_into_the_only_class_it_can_build(self) -> None:
        ranker, payload = _load(canonical_bytes(_payload()))

        assert isinstance(ranker, CorrectionKnn)
        assert payload.setting_identity == SETTING
        assert payload.embedding_weight == Decimal(str(ranker.embedding_weight))


# --------------------------------------------------- the direct evaluation boundary


class TestTheDirectEvaluationBoundary:
    def test_it_builds_a_ranker_from_the_exact_authorised_bytes(self) -> None:
        data = canonical_bytes(_payload())

        ranker, payload = build_ranker_for_evaluation(data, capability=_capability())

        assert isinstance(ranker, CorrectionKnn)
        assert payload.selection_manifest_hash == SELECTION

    def test_bytes_that_are_not_the_authorised_ones_are_refused_before_parsing(self) -> None:
        other = canonical_bytes(_payload(code_revision="21d3-rebuilt"))

        with pytest.raises(
            CorrectionArtifactError, match=r"not the \S+ this capability authorises"
        ):
            build_ranker_for_evaluation(other, capability=_capability())

    @pytest.mark.parametrize(
        "state",
        [
            LearnedComponentState.VERIFIED,
            LearnedComponentState.ACTIVE,
            LearnedComponentState.DISABLED,
            LearnedComponentState.RETRACTED,
        ],
    )
    def test_the_boundary_is_closed_past_shadow(self, state: LearnedComponentState) -> None:
        """An approved component is read through the resolver, or it is not read at all."""
        with pytest.raises(CorrectionArtifactError, match="direct evaluation boundary is closed"):
            _capability(component_state=state)

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("training_dataset_id", UUID(int=99)),
            ("split_manifest_hash", "1" * 64),
            ("member_manifest_hash", "2" * 64),
            ("selection_manifest_hash", "3" * 64),
        ],
    )
    def test_every_declared_identity_must_be_the_one_in_the_bytes(
        self, field: str, value: object
    ) -> None:
        with pytest.raises(CorrectionArtifactError, match="not the expected"):
            build_ranker_for_evaluation(
                canonical_bytes(_payload()), capability=_capability(**{field: value})
            )

    def test_the_application_runtime_cannot_reach_this_path(self) -> None:
        """The resolver imports no builder, at any depth. That is the boundary.

        Walked as imports rather than searched as text: the module names this one in a comment
        explaining why it does *not* import it, and a substring check would call that a
        violation while missing a lazy import inside a function.
        """
        from cognitive_os.application.services import learned_runtime

        tree = ast.parse(Path(learned_runtime.__file__).read_text(encoding="utf-8"))
        imported = {
            name.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for name in node.names
        } | {
            f"{node.module}.{name.name}"
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
            for name in node.names
        }

        assert not any("correction_artifact" in name for name in imported)
        assert not hasattr(learned_runtime.LearnedRuntimeResolver, "build_ranker_for_evaluation")

    def test_the_media_type_is_still_the_only_one_that_loads(self) -> None:
        with pytest.raises(CorrectionArtifactError, match="media type"):
            build_ranker_for_evaluation(
                canonical_bytes(_payload()),
                capability=_capability(),
                media_type="application/octet-stream",
            )
        assert CORRECTION_ARTIFACT_MEDIA_TYPE.endswith("+json")
