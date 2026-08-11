"""S21D7-024: the second class through the v3 schema, and the confusion it must refuse.

D7 fits a seven-channel relational direction where D5 fitted a 390-channel one. The two share
the v3 artifact schema because they share everything the schema is about — the canonicaliser,
the envelope, the operating point and the margin that point is taken over — and differ only in
which numbers describe a candidate.

Sharing a schema is exactly where a reader can start building the wrong thing, so what is tested
here is the seam rather than the round trip alone:

*A payload's class decides its channel list.* Seven channels are legitimate for the containment
class and forbidden for the released one, and the reverse is equally true. A validator that kept
one fixed allowlist would have made this artifact unrepresentable; one that dropped the check
would let a 390-weight direction load as a seven-channel model.

*Class and component must agree.* An artifact naming one class and the other's component is not
a model either reader can build, and the loader says so instead of building whichever it happens
to dispatch on first.

*The released class is untouched.* Its allowlist, its component id and its refusals are what
they were, which is what `§3.5`'s "no change to the released class" means in code.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from cognitive_os.learning.containment_contrastive import (
    FITTED_RELATIONAL_CHANNELS,
    ContainmentContrastiveModel,
    ContainmentContrastiveRanker,
)
from cognitive_os.learning.containment_contrastive import (
    HYPOTHESIS_CLASS as CONTAINMENT_HYPOTHESIS_CLASS,
)
from cognitive_os.learning.correction_artifact import (
    FITTED_CHANNELS_BY_CLASS,
    IMPLEMENTED_HYPOTHESIS_CLASSES,
    CorrectionArtifactError,
    CorrectionArtifactPayloadV3,
    build_payload_v3,
    canonical_bytes,
    load_correction_ranker_v3,
)
from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
)
from cognitive_os.learning.pairwise_contrastive import (
    HYPOTHESIS_CLASS,
    PairwiseContrastiveRanker,
)

DESCRIPTOR = "d" * 64
MANIFEST = "a" * 64
SELECTION = "b" * 64
MEMBERS = "c" * 64
SETTING = "e" * 64
POINT = "f" * 64
CERTIFICATE = "9" * 64
TRAINING = UUID(int=1)
CALIBRATION = UUID(int=2)


def _ranker(margin_floor: Decimal = Decimal("0.25")) -> ContainmentContrastiveRanker:
    model = ContainmentContrastiveModel(
        channel_names=FITTED_RELATIONAL_CHANNELS,
        weights=tuple(0.5 * (index + 1) for index in range(len(FITTED_RELATIONAL_CHANNELS))),
        regularization="1",
        fitted_group_count=180,
        fitted_pair_count=720,
    )
    return ContainmentContrastiveRanker(model, margin_floor=margin_floor)


def _payload(**overrides: Any) -> CorrectionArtifactPayloadV3:
    payload = build_payload_v3(
        component_revision=1,
        descriptor_hash=DESCRIPTOR,
        code_revision="21d7",
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
    if not overrides:
        return payload
    # Rebuilt through the constructor rather than copied: `model_copy` does not re-run the
    # validators, and every override below exists to make one of them fire.
    fields = payload.model_dump()
    fields.update(overrides)
    return CorrectionArtifactPayloadV3(**fields)


def _load(data: bytes, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "expected_component_id": ContainmentContrastiveRanker.component_id,
        "expected_revision": 1,
        "expected_surface": ContainmentContrastiveRanker.surface,
        "expected_descriptor_hash": DESCRIPTOR,
    }
    fields.update(overrides)
    return load_correction_ranker_v3(data, **fields)


def _tampered(**changes: Any) -> bytes:
    """Mutate the canonical document directly: what is under test is what the *loader* does
    with bytes it did not build, and `model_copy` does not re-run the validators."""
    document = json.loads(canonical_bytes(_payload()))
    document.update(changes)
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def test_the_relational_direction_round_trips_into_its_own_class() -> None:
    ranker, payload = _load(canonical_bytes(_payload()))

    assert isinstance(ranker, ContainmentContrastiveRanker)
    assert payload.hypothesis_class == CONTAINMENT_HYPOTHESIS_CLASS
    assert payload.learner_kind == "containment_contrastive_linear"
    assert payload.component_id == ContainmentContrastiveRanker.component_id
    assert tuple(payload.feature_channels) == FITTED_RELATIONAL_CHANNELS
    assert len(payload.weights) == 7
    assert ranker.model.weights == _ranker().model.weights
    assert ranker.margin_floor == Decimal("0.25")


def test_the_builder_takes_the_identity_off_the_ranker_it_was_handed() -> None:
    """A builder naming one class's component would wrap the other's direction in it."""
    assert {HYPOTHESIS_CLASS, CONTAINMENT_HYPOTHESIS_CLASS} == IMPLEMENTED_HYPOTHESIS_CLASSES
    assert FITTED_CHANNELS_BY_CLASS[CONTAINMENT_HYPOTHESIS_CLASS] == FITTED_RELATIONAL_CHANNELS
    assert FITTED_CHANNELS_BY_CLASS[HYPOTHESIS_CLASS] == FITTED_FEATURE_V2_ALLOWLIST
    assert _payload().surface == ContainmentContrastiveRanker.surface
    assert ContainmentContrastiveRanker.component_id != PairwiseContrastiveRanker.component_id


def test_the_channel_list_is_the_one_the_declared_class_fits() -> None:
    """Seven channels are legitimate here and forbidden for the released class."""
    with pytest.raises(ValueError, match="fitted allowlist"):
        _payload(feature_channels=FITTED_FEATURE_V2_ALLOWLIST)
    with pytest.raises(ValueError, match="weights against"):
        _payload(weights=(1.0,) * len(FITTED_FEATURE_V2_ALLOWLIST))


def test_a_class_and_a_component_that_disagree_are_refused() -> None:
    """The confusion a shared schema makes possible, named rather than dispatched around."""
    with pytest.raises(CorrectionArtifactError, match="belongs to another one"):
        _load(
            _tampered(component_id=PairwiseContrastiveRanker.component_id),
            expected_component_id=PairwiseContrastiveRanker.component_id,
        )


def test_the_released_class_still_refuses_the_relational_channels() -> None:
    """§3.5: the released class is unchanged, and this is what unchanged means in code."""
    with pytest.raises(ValueError, match="fitted allowlist"):
        _payload(
            hypothesis_class=HYPOTHESIS_CLASS,
            component_id=PairwiseContrastiveRanker.component_id,
        )


def test_a_class_the_loader_does_not_implement_is_still_refused() -> None:
    with pytest.raises(ValueError, match="not one this loader implements"):
        _payload(hypothesis_class="containment-contrastive-linear-v2")
