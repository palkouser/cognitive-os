"""S21D5-037: condition 20 names the class that produced its confidences, and moves no bytes.

D4 made the row carry two denominators and a certificate hash. That is enough to know how many
decisions were counted and which threshold answered them, and not enough to know *what* was
thresholded: the k-NN's neighbourhood acceptance mass and the pairwise direction's projection
margin are different quantities, and a certificate hash alone cannot tell a reader which one a
zero-confident-error claim is about.

So the row names the class. Three things have to hold at once:

*A class no loader implements is refused where the payload is built*, not at activation, where
the bytes would already be stored.

*The D3 and D4 payloads stay readable and byte-identical.* The field is optional and excluded
when unset, so a payload written before it existed hashes exactly as it did. Measured against a
payload reconstructed without the key, rather than against a golden digit a regeneration would
silently update.

*A row that names the class is new bytes and a new identity*, because absent must not be a
synonym for present-and-hidden.
"""

from __future__ import annotations

import json
from hashlib import sha256

import pytest

from cognitive_os.domain.promotion_payload import (
    CONDITION_20_GATE,
    D3PromotionPayload,
    PromotionDecisionCounts,
    PromotionGateOutcome,
    canonical_payload_bytes,
    load_promotion_payload,
    promotion_payload_version,
)
from cognitive_os.learning.correction_artifact import IMPLEMENTED_HYPOTHESIS_CLASSES
from cognitive_os.learning.correction_protocol import DecisionCensusV4
from cognitive_os.learning.pairwise_contrastive import HYPOTHESIS_CLASS
from cognitive_os.learning.promotion import condition_20_gate

from . import fixtures as fx

#: D5's promotion set as the corpus contract sizes it: 60 final groups, two cases each.
D5_PROMOTION_FEATURE_HASHES = [
    sha256(f"d5-group-{index // 2}".encode()).hexdigest() for index in range(120)
]
CERTIFICATE = sha256(b"s21d5:calibration-certificate").hexdigest()


def _census() -> DecisionCensusV4:
    return DecisionCensusV4.from_feature_hashes(D5_PROMOTION_FEATURE_HASHES)


def _row(**overrides: object) -> object:
    arguments: dict[str, object] = {
        "outcome": PromotionGateOutcome.PASSED,
        "evidence_hash": sha256(b"d5-ood").hexdigest(),
        "detail": "120 nominal decisions over 60 distinct fitted vectors",
        "census": _census(),
        "calibration_certificate_hash": CERTIFICATE,
        "hypothesis_class": HYPOTHESIS_CLASS,
    }
    arguments.update(overrides)
    return condition_20_gate(**arguments)  # type: ignore[arg-type]


def _payload_with(gate: object) -> D3PromotionPayload:
    return fx.d3_payload(
        gates=tuple(
            gate if item.name == CONDITION_20_GATE else item  # type: ignore[misc]
            for item in fx.d3_payload().gates
        )
    )


def _without_hypothesis_class(payload: D3PromotionPayload) -> bytes:
    """The exact bytes a D4 producer would have written for this payload.

    Reconstructed by deleting the key rather than by pinning a digest: a pinned digest proves
    the bytes did not change since someone last regenerated it, which is a different claim.
    """
    document = json.loads(payload.model_dump_json(exclude_none=True))
    for row in document["gates"]:
        if row.get("decision_counts") is not None:
            row["decision_counts"].pop("hypothesis_class", None)
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class TestTheRowNamesTheClass:
    def test_a_measured_row_carries_both_counts_the_certificate_and_the_class(self) -> None:
        census = _census()
        assert (census.nominal_decisions, census.independent_decisions) == (120, 60)

        gate = _row()

        assert gate.name == CONDITION_20_GATE  # type: ignore[attr-defined]
        counts = gate.decision_counts  # type: ignore[attr-defined]
        assert counts is not None
        assert counts.nominal_decisions == 120
        assert counts.independent_decisions == 60
        assert counts.calibration_certificate_hash == CERTIFICATE
        assert counts.hypothesis_class == HYPOTHESIS_CLASS

    def test_a_class_no_loader_implements_is_refused_at_build_time(self) -> None:
        assert "graph-neural-ranker-v1" not in IMPLEMENTED_HYPOTHESIS_CLASSES
        with pytest.raises(ValueError, match="no loader"):
            _row(hypothesis_class="graph-neural-ranker-v1")

    def test_the_refusal_names_the_classes_that_are_implemented(self) -> None:
        with pytest.raises(ValueError, match=HYPOTHESIS_CLASS):
            _row(hypothesis_class="")

    def test_a_row_nobody_measured_still_carries_no_counts_and_no_class(self) -> None:
        with pytest.raises(ValueError, match="no census"):
            _row(outcome=PromotionGateOutcome.NOT_MEASURED)


class TestTheExtensionIsAdditive:
    def test_a_d4_shaped_row_hashes_as_it_did_before_the_field_existed(self) -> None:
        payload = _payload_with(_row(hypothesis_class=None))

        assert "hypothesis_class" not in payload.canonical_json(exclude={"content_hash"})
        assert canonical_payload_bytes(payload) == _without_hypothesis_class(payload)

    def test_naming_the_class_is_new_bytes_and_a_new_identity(self) -> None:
        without = _payload_with(_row(hypothesis_class=None))
        named = _payload_with(_row())

        assert named.content_hash != without.content_hash
        assert b"hypothesis_class" in canonical_payload_bytes(named)
        assert b"hypothesis_class" not in canonical_payload_bytes(without)

    def test_d4_bytes_still_dispatch_and_reload_to_their_recorded_identity(self) -> None:
        payload = _payload_with(_row(hypothesis_class=None))
        data = _without_hypothesis_class(payload)

        assert promotion_payload_version(data) == 2
        reloaded = load_promotion_payload(data)
        counts = reloaded.gate[CONDITION_20_GATE].decision_counts
        assert counts is not None
        assert counts.hypothesis_class is None
        assert reloaded.content_hash == json.loads(data.decode())["content_hash"]

    def test_d5_bytes_reload_through_the_same_schema_name_dispatch(self) -> None:
        payload = _payload_with(_row())
        data = canonical_payload_bytes(payload)

        assert promotion_payload_version(data) == 2
        reloaded = load_promotion_payload(data)
        counts = reloaded.gate[CONDITION_20_GATE].decision_counts
        assert counts is not None
        assert counts.hypothesis_class == HYPOTHESIS_CLASS
        assert reloaded.content_hash == payload.content_hash

    def test_the_field_is_not_reachable_through_the_domain_model_without_a_value(self) -> None:
        """The domain keeps the shape; `condition_20_gate` keeps the list of live classes.

        A domain model that owned the implemented-class list would be a second place for it to
        go stale, so the model accepts any non-empty string and the builder is where a class
        nobody can load is refused. This pins that division rather than leaving it to a comment.
        """
        counts = PromotionDecisionCounts(
            nominal_decisions=120,
            independent_decisions=60,
            calibration_certificate_hash=CERTIFICATE,
            hypothesis_class="a-class-the-loader-does-not-know",
        )
        assert counts.hypothesis_class == "a-class-the-loader-does-not-know"
        with pytest.raises(ValueError, match="no loader"):
            _row(hypothesis_class="a-class-the-loader-does-not-know")
