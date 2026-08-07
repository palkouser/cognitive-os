"""S21D4-048: condition 20's denominators, and the bytes the addition was not allowed to move.

D3 recorded 120 metamorphic ranking decisions and Gate L2 condition 20 read them as 120. They
were 20 decisions replicated six times. Nothing in the payload could have caught it, because the
row named one number and there was no second number to disagree with it.

Two halves, and the second is the one that is easy to get wrong. The first is that a measured
metamorphic/OOD row now cannot exist without both counts and the certificate its answered set
was decided under. The second is that adding that field moved nothing: a payload carrying no
counts hashes exactly as it did before the field existed, and re-serialises to the same bytes.
Both are measured here against a payload reconstructed without the new key, rather than asserted
against a golden digit that a regeneration would silently update.
"""

from __future__ import annotations

import json
from hashlib import sha256

import pytest
from pydantic import ValidationError

from cognitive_os.domain.promotion_payload import (
    CONDITION_20_GATE,
    D3_PROMOTION_GATES,
    D3PromotionPayload,
    PromotionDecisionCounts,
    PromotionGateOutcome,
    PromotionGateRecord,
    PromotionPayloadError,
    canonical_payload_bytes,
    load_promotion_payload,
    promotion_payload_version,
)
from cognitive_os.learning.correction_protocol import DecisionCensusV4
from cognitive_os.learning.promotion import (
    D3PromotionVerdict,
    condition_20_gate,
    evaluate_d3_promotion,
)

from . import fixtures as fx

#: D3's own metamorphic set, as the D4 erratum recomputed it: six semantics-preserving
#: transformations of each of twenty groups encode to twenty distinct fitted vectors.
D3_METAMORPHIC_FEATURE_HASHES = [
    sha256(f"group-{index // 6}".encode()).hexdigest() for index in range(120)
]
CERTIFICATE = sha256(b"s21d4:calibration-certificate").hexdigest()


def _census() -> DecisionCensusV4:
    return DecisionCensusV4.from_feature_hashes(D3_METAMORPHIC_FEATURE_HASHES)


def _sealed_as_d3_would_have(gates: tuple[PromotionGateRecord, ...]) -> bytes:
    """Bytes exactly as a D3 producer wrote them, seal included.

    `model_construct` skips the validators, which is the only way to build a shape D4 refuses:
    the point is to hand the loader real historical bytes rather than a corruption. The seal is
    then computed the way the contract computes it, so the refusal under test is the census rule
    and not a hash mismatch standing in front of it.
    """
    fields = dict(fx.d3_payload())
    fields["gates"] = gates
    fields["content_hash"] = ""
    draft = D3PromotionPayload.model_construct(**fields)
    fields["content_hash"] = draft.canonical_hash(exclude={"content_hash"})
    return canonical_payload_bytes(D3PromotionPayload.model_construct(**fields))


def _without_decision_counts(payload: D3PromotionPayload) -> bytes:
    """The exact bytes the D3 code would have written for this payload.

    Reconstructed by deleting the key rather than by pinning a digest: a pinned digest proves
    the bytes did not change since someone last regenerated it, which is a different claim.
    """
    document = json.loads(payload.model_dump_json())
    document["gates"] = [
        {key: value for key, value in gate.items() if key != "decision_counts"}
        for gate in document["gates"]
    ]
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class TestAMeasuredConditionTwentyRowNamesBothDenominators:
    def test_the_counts_come_from_a_census_rather_than_from_two_integers(self) -> None:
        census = _census()
        assert (census.nominal_decisions, census.independent_decisions) == (120, 20)

        gate = condition_20_gate(
            outcome=PromotionGateOutcome.PASSED,
            evidence_hash=sha256(b"ood").hexdigest(),
            detail="120 nominal decisions over 20 distinct fitted vectors",
            census=census,
            calibration_certificate_hash=CERTIFICATE,
        )

        assert gate.name == CONDITION_20_GATE
        assert gate.decision_counts is not None
        assert gate.decision_counts.nominal_decisions == 120
        assert gate.decision_counts.independent_decisions == 20
        assert gate.decision_counts.calibration_certificate_hash == CERTIFICATE

    def test_a_measured_row_without_counts_is_refused(self) -> None:
        gates = tuple(
            PromotionGateRecord(
                name=name,
                outcome=PromotionGateOutcome.PASSED,
                evidence_hash=sha256(name.encode()).hexdigest(),
                detail=f"fixture: {name}",
            )
            for name in D3_PROMOTION_GATES
        )

        with pytest.raises(ValidationError, match="nominal and independent decision counts"):
            fx.d3_payload(gates=gates)

    def test_a_failed_row_still_has_to_name_them(self) -> None:
        """`failed` is a measurement with a verdict; only `not_measured` has neither."""
        with pytest.raises(ValidationError, match="nominal and independent decision counts"):
            fx.d3_payload(
                gates=tuple(
                    PromotionGateRecord(
                        name=item.name,
                        outcome=(
                            PromotionGateOutcome.FAILED
                            if item.name == CONDITION_20_GATE
                            else item.outcome
                        ),
                        evidence_hash=item.evidence_hash,
                        detail=item.detail,
                    )
                    for item in fx.d3_payload().gates
                )
            )

    def test_not_measured_stays_distinct_from_failed_and_carries_no_counts(self) -> None:
        payload = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(item.name, PromotionGateOutcome.NOT_MEASURED)
                if item.name == CONDITION_20_GATE
                else item
                for item in fx.d3_payload().gates
            )
        )

        assert payload.gate[CONDITION_20_GATE].decision_counts is None
        evaluation = evaluate_d3_promotion(payload, bindings=fx.d3_bindings())
        assert evaluation.verdict is D3PromotionVerdict.GATE_NOT_MEASURED
        assert evaluation.first_failed_gate == CONDITION_20_GATE

    def test_a_gate_nobody_ran_may_not_claim_a_census(self) -> None:
        counts = PromotionDecisionCounts(
            nominal_decisions=120,
            independent_decisions=20,
            calibration_certificate_hash=CERTIFICATE,
        )

        with pytest.raises(ValidationError, match="counted no decisions"):
            fx.d3_payload(
                gates=tuple(
                    PromotionGateRecord(
                        name=item.name,
                        outcome=(
                            PromotionGateOutcome.NOT_MEASURED
                            if item.name == CONDITION_20_GATE
                            else item.outcome
                        ),
                        evidence_hash=item.evidence_hash,
                        detail=item.detail,
                        decision_counts=(
                            counts if item.name == CONDITION_20_GATE else item.decision_counts
                        ),
                    )
                    for item in fx.d3_payload().gates
                )
            )

    def test_the_builder_refuses_to_manufacture_a_census_for_an_unmeasured_gate(self) -> None:
        with pytest.raises(ValueError, match="a gate nobody ran has no census"):
            condition_20_gate(
                outcome=PromotionGateOutcome.NOT_MEASURED,
                evidence_hash=sha256(b"ood").hexdigest(),
                detail="never ran",
                census=_census(),
                calibration_certificate_hash=CERTIFICATE,
            )

    def test_more_independent_than_counted_decisions_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="more independent decisions"):
            PromotionDecisionCounts(
                nominal_decisions=20,
                independent_decisions=120,
                calibration_certificate_hash=CERTIFICATE,
            )


class TestTheD4GateCensusIsAdditive:
    """What the moved schema pin used to protect, asserted where it can actually be checked."""

    def test_a_payload_without_counts_hashes_as_it_did_before_the_field_existed(self) -> None:
        payload = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(item.name, PromotionGateOutcome.NOT_MEASURED)
                if item.name == CONDITION_20_GATE
                else item
                for item in fx.d3_payload().gates
            )
        )

        assert "decision_counts" not in payload.canonical_json(exclude={"content_hash"})
        assert canonical_payload_bytes(payload) == _without_decision_counts(payload)

    def test_a_payload_carrying_counts_is_new_bytes_and_a_new_identity(self) -> None:
        """The other direction: absent must not be a synonym for zero-and-hidden."""
        without = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(item.name, PromotionGateOutcome.NOT_MEASURED)
                if item.name == CONDITION_20_GATE
                else item
                for item in fx.d3_payload().gates
            )
        )
        with_counts = fx.d3_payload(
            gates=tuple(
                condition_20_gate(
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=item.evidence_hash,
                    detail=item.detail,
                    census=_census(),
                    calibration_certificate_hash=CERTIFICATE,
                )
                if item.name == CONDITION_20_GATE
                else item
                for item in fx.d3_payload().gates
            )
        )

        assert with_counts.content_hash != without.content_hash
        assert b"decision_counts" in canonical_payload_bytes(with_counts)

    def test_d3_bytes_still_dispatch_and_reload_to_their_recorded_identity(self) -> None:
        """The acceptance's readability half: v2 bytes are read as v2, not as a broken v3."""
        payload = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(item.name, PromotionGateOutcome.NOT_MEASURED)
                if item.name == CONDITION_20_GATE
                else item
                for item in fx.d3_payload().gates
            )
        )
        data = _without_decision_counts(payload)

        assert promotion_payload_version(data) == 2
        reloaded = load_promotion_payload(data)
        assert reloaded.gate[CONDITION_20_GATE].decision_counts is None
        assert reloaded.content_hash == json.loads(data.decode())["content_hash"]

    def test_a_d3_payload_that_claimed_condition_20_without_denominators_is_refused(self) -> None:
        """W4-D1, and it is the intended direction rather than an accident.

        A D3 payload asserting `metamorphic_ood: passed` is asserting the exact claim the D4
        erratum disproved — 120 decisions that were 20 replicated six times. Refusing to reload
        it is refusing to re-serve a claim this sprint measured as wrong. Dispatch still reports
        it as version 2, and the seal still verifies; it is the row that is refused, not the
        schema that is misread or the bytes that are called corrupt.
        """
        claimed = _sealed_as_d3_would_have(
            tuple(
                PromotionGateRecord(
                    name=item.name,
                    outcome=PromotionGateOutcome.PASSED,
                    evidence_hash=item.evidence_hash,
                    detail=item.detail,
                )
                for item in fx.d3_payload().gates
            )
        )

        assert promotion_payload_version(claimed) == 2
        with pytest.raises(PromotionPayloadError, match="nominal and independent decision counts"):
            load_promotion_payload(claimed)

    def test_precedence_is_still_fixed_by_the_gate_tuple(self) -> None:
        """The addition touched a row, not the order failures are reported in."""
        payload = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(item.name, PromotionGateOutcome.FAILED)
                if item.name in {CONDITION_20_GATE, "retention"}
                else item
                for item in reversed(fx.d3_payload().gates)
            )
        )

        evaluation = evaluate_d3_promotion(payload, bindings=fx.d3_bindings())

        assert evaluation.first_failed_gate == CONDITION_20_GATE
        assert evaluation.unmet_gates == (CONDITION_20_GATE, "retention")
        assert D3_PROMOTION_GATES.index(CONDITION_20_GATE) < D3_PROMOTION_GATES.index("retention")
