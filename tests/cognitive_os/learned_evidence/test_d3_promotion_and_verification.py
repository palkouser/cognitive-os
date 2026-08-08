"""S21D3-048, -057 and -058: what a promotion says, who may verify it, and when bytes are read.

Three boundaries, one story. The payload says what every gate measured and what every
dependency was; the evaluator turns that into one verdict without room to round anything in
the model's favour; and verification is the only way a component reaches `VERIFIED`, because
a state a caller could simply announce is not evidence of anything.

The activation half is the same check at a later moment. D2's activation trusted a lineage
record that had been verified within the last week, which is a statement about a *record*, not
about bytes that can be replaced a second after it was written. Both moments now rehash.
"""

from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

import pytest

from cognitive_os.domain.learned import LearnedComponentState
from cognitive_os.domain.learned_evidence import (
    LearnedEvidenceKind,
    LearnedRepositoryConflict,
    LearnedRepositoryError,
)
from cognitive_os.domain.promotion_payload import (
    D3_PROMOTION_GATES,
    D3_PROMOTION_SCHEMA_VERSION,
    LEGACY_PROMOTION_SCHEMA_VERSION,
    D3PromotionPayload,
    PromotionGateOutcome,
    PromotionGateRecord,
    PromotionPayloadError,
    canonical_payload_bytes,
    load_promotion_payload,
    promotion_payload_version,
)
from cognitive_os.learning.promotion import (
    D3PromotionVerdict,
    evaluate_d3_promotion,
)

from . import fixtures as fx
from .test_inert_lifecycle import CORRELATION, OPERATOR, LifecycleHarness

# ------------------------------------------------------------------ S21D3-048: the payload


def _with_gate(name: str, outcome: PromotionGateOutcome) -> D3PromotionPayload:
    """Rebuild through `fx.d3_gate` rather than field by field.

    Copying the fields would drop condition 20's census when that row is the one being moved,
    and S21D4-048 refuses a measured metamorphic/OOD row without it — a refusal that would show
    up here as an unrelated test failing to construct its own input.
    """
    gates = tuple(
        fx.d3_gate(item.name, outcome if item.name == name else item.outcome)
        for item in fx.d3_payload().gates
    )
    return fx.d3_payload(gates=gates)


def _without_gate(name: str) -> D3PromotionPayload:
    return fx.d3_payload(gates=tuple(item for item in fx.d3_payload().gates if item.name != name))


class TestThePayloadSchema:
    def test_it_binds_every_gate_the_contract_names(self) -> None:
        payload = fx.d3_payload()

        assert set(payload.gate) == set(D3_PROMOTION_GATES)
        assert payload.missing_gates == ()
        assert payload.schema_version == D3_PROMOTION_SCHEMA_VERSION

    def test_the_two_configurations_and_the_transition_condition_are_bound_by_hash(self) -> None:
        payload = fx.d3_payload()

        assert (
            payload.canary_configuration_hash
            == fx.runtime_configuration("exact_canary").content_hash
        )
        assert (
            payload.steady_state_configuration_hash
            == fx.runtime_configuration("bounded_steady_state").content_hash
        )
        assert payload.canary_to_steady_condition_hash == fx.transition_condition().content_hash

    def test_one_configuration_cannot_serve_as_both(self) -> None:
        shared = fx.runtime_configuration("exact_canary").content_hash

        with pytest.raises(ValueError, match="canary and steady-state configurations must differ"):
            fx.d3_payload(steady_state_configuration_hash=shared)

    def test_a_gate_nobody_defined_cannot_be_invented(self) -> None:
        invented = (
            *fx.d3_payload().gates,
            PromotionGateRecord(
                name="looks_good_to_me",
                outcome=PromotionGateOutcome.PASSED,
                evidence_hash="a" * 64,
                detail="not a gate",
            ),
        )

        with pytest.raises(ValueError, match="gates that do not exist"):
            fx.d3_payload(gates=invented)

    def test_canonical_bytes_rehash_identically(self) -> None:
        assert (
            sha256(canonical_payload_bytes(fx.d3_payload())).hexdigest()
            == sha256(canonical_payload_bytes(fx.d3_payload())).hexdigest()
        )

    def test_a_configuration_without_a_kill_switch_cannot_be_sealed(self) -> None:
        with pytest.raises(ValueError, match="without a kill switch"):
            fx.runtime_configuration("exact_canary", kill_switch_enabled=False)


class TestLegacyPayloadsStayReadable:
    def test_a_v1_document_is_dispatched_as_legacy_rather_than_coerced(self) -> None:
        legacy = fx.promotion_assessment().model_dump_json().encode()

        assert promotion_payload_version(legacy) == LEGACY_PROMOTION_SCHEMA_VERSION
        with pytest.raises(PromotionPayloadError, match="schema version 1 bytes"):
            load_promotion_payload(legacy)

    def test_a_v2_document_round_trips(self) -> None:
        data = canonical_payload_bytes(fx.d3_payload())

        assert promotion_payload_version(data) == D3_PROMOTION_SCHEMA_VERSION
        assert load_promotion_payload(data).content_hash == fx.d3_payload().content_hash

    @pytest.mark.parametrize(
        ("data", "message"),
        [
            (b"\xff\xfe not utf 8", "not UTF-8"),
            (b"{not json", "not JSON"),
            (b"[1, 2, 3]", "is a JSON object"),
            (b'{"schema_name": "something-else"}', "unknown promotion payload schema"),
        ],
    )
    def test_unreadable_bytes_are_refused_by_name(self, data: bytes, message: str) -> None:
        with pytest.raises(PromotionPayloadError, match=message):
            promotion_payload_version(data)


class TestTheEvaluatorTruthTable:
    def test_every_gate_passing_and_every_binding_holding_is_eligible(self) -> None:
        evaluation = evaluate_d3_promotion(fx.d3_payload(), bindings=fx.d3_bindings())

        assert evaluation.eligible
        assert evaluation.first_failed_gate is None
        assert evaluation.unmet_gates == ()

    def test_a_failed_gate_is_named_and_distinguished_from_an_unmeasured_one(self) -> None:
        failed = evaluate_d3_promotion(
            _with_gate("retention", PromotionGateOutcome.FAILED), bindings=fx.d3_bindings()
        )
        unmeasured = evaluate_d3_promotion(
            _with_gate("retention", PromotionGateOutcome.NOT_MEASURED), bindings=fx.d3_bindings()
        )

        assert failed.verdict is D3PromotionVerdict.GATE_FAILED
        assert unmeasured.verdict is D3PromotionVerdict.GATE_NOT_MEASURED
        assert failed.first_failed_gate == unmeasured.first_failed_gate == "retention"

    def test_an_absent_gate_refuses_as_firmly_as_a_failed_one(self) -> None:
        evaluation = evaluate_d3_promotion(_without_gate("shadow"), bindings=fx.d3_bindings())

        assert evaluation.verdict is D3PromotionVerdict.GATE_NOT_MEASURED
        assert evaluation.first_failed_gate == "shadow"
        assert "records no 'shadow' gate at all" in evaluation.reason

    def test_precedence_is_fixed_so_two_runs_cannot_name_different_failures(self) -> None:
        """`benefit` precedes `retention`, whatever order the gates appear in the payload."""
        payload = fx.d3_payload(
            gates=tuple(
                fx.d3_gate(
                    item.name,
                    (
                        PromotionGateOutcome.FAILED
                        if item.name in {"retention", "benefit"}
                        else item.outcome
                    ),
                )
                for item in reversed(fx.d3_payload().gates)
            )
        )

        evaluation = evaluate_d3_promotion(payload, bindings=fx.d3_bindings())

        assert evaluation.first_failed_gate == "benefit"
        assert evaluation.unmet_gates == ("benefit", "retention")

    @pytest.mark.parametrize(
        ("override", "expected"),
        [
            ({"component_revision": 9}, "component_revision"),
            ({"artifact_content_hash": "b" * 64}, "artifact_content_hash"),
            ({"artifact_size_bytes": 999_999}, "artifact_size_bytes"),
        ],
    )
    def test_a_payload_about_another_promotion_is_a_binding_mismatch(
        self, override: dict[str, object], expected: str
    ) -> None:
        evaluation = evaluate_d3_promotion(fx.d3_payload(), bindings=fx.d3_bindings(**override))

        assert evaluation.verdict is D3PromotionVerdict.BINDING_MISMATCH
        assert expected in evaluation.reason

    def test_a_missing_dependency_and_a_stale_one_are_reported_apart(self) -> None:
        missing = evaluate_d3_promotion(
            fx.d3_payload(),
            bindings=fx.d3_bindings(
                dependency_hashes={**fx.D3_DEPENDENCIES, "shadow_manifest": "9" * 64}
            ),
        )
        stale = evaluate_d3_promotion(
            fx.d3_payload(),
            bindings=fx.d3_bindings(
                dependency_hashes={**fx.D3_DEPENDENCIES, "feature_contract": "9" * 64}
            ),
        )

        assert "dependency:shadow_manifest:missing" in missing.reason
        assert "dependency:feature_contract:stale_or_wrong" in stale.reason

    def test_a_configuration_that_changed_after_the_payload_was_written_is_refused(self) -> None:
        evaluation = evaluate_d3_promotion(
            fx.d3_payload(),
            bindings=fx.d3_bindings(
                canary_configuration=fx.runtime_configuration("exact_canary", maximum_tasks=40)
            ),
        )

        assert evaluation.verdict is D3PromotionVerdict.BINDING_MISMATCH
        assert "canary_configuration_hash" in evaluation.reason


# ------------------------------------------------ S21D3-057: the only path to VERIFIED


async def _shadowing() -> LifecycleHarness:
    harness = LifecycleHarness()
    await harness.register()
    await harness.service.advance_component(
        fx.INERT.component_id,
        LearnedComponentState.SHADOW,
        descriptor=fx.descriptor(),
        actor=OPERATOR,
        authority="operator",
        reason="observe in shadow",
        idempotency_key="to-shadow",
        correlation_id=CORRELATION,
    )
    return harness


class TestVerificationIsTheOnlyWayIn:
    @pytest.mark.asyncio
    async def test_the_generic_transition_refuses_verified(self) -> None:
        harness = await _shadowing()

        with pytest.raises(LearnedRepositoryError, match="not an ordinary transition"):
            await harness.service.advance_component(
                fx.INERT.component_id,
                LearnedComponentState.VERIFIED,
                descriptor=fx.descriptor(),
                actor=OPERATOR,
                authority="operator",
                reason="announce it",
                idempotency_key="announce",
                correlation_id=CORRELATION,
            )

    @pytest.mark.asyncio
    async def test_verification_records_the_assessment_hash_on_the_transition(self) -> None:
        harness = await _shadowing()
        await harness.record_d3_promotion()

        revision = await harness.verify()

        assert revision.state_after is LearnedComponentState.VERIFIED
        assert revision.promotion_assessment_hash == harness.d3_assessment.content_hash

    @pytest.mark.asyncio
    async def test_an_assessment_nobody_stored_is_refused(self) -> None:
        harness = await _shadowing()

        with pytest.raises(LearnedRepositoryError, match="no promotion assessment is recorded"):
            await harness.verify()

    @pytest.mark.asyncio
    async def test_a_stale_assessment_is_named_as_stale_rather_than_missing(self) -> None:
        harness = await _shadowing()
        await harness.record_d3_promotion()
        newer = fx.d3_payload(code_revision="21d3-rebuilt")

        with pytest.raises(LearnedRepositoryError, match="stale or was never stored"):
            await harness.verify(payload=newer, assessment=fx.d3_assessment(newer))

    @pytest.mark.asyncio
    async def test_an_evidence_row_resolving_no_payload_artifact_is_refused(self) -> None:
        harness = await _shadowing()
        await harness.service.record_evidence(
            fx.evidence(
                LearnedEvidenceKind.PROMOTION_ASSESSMENT,
                harness.d3_assessment.content_hash,
                schema_version="2",
            ),
            correlation_id=CORRELATION,
            actor=OPERATOR,
            authority="operator",
            reason="record without bytes",
        )

        with pytest.raises(LearnedRepositoryError, match="resolves no payload artifact"):
            await harness.verify()

    @pytest.mark.asyncio
    async def test_a_substituted_payload_artifact_is_refused(self) -> None:
        harness = await _shadowing()
        await harness.record_d3_promotion()
        substituted = fx.d3_assessment(harness.payload, payload_artifact_id=uuid4())

        with pytest.raises(LearnedRepositoryError, match="stale or was never stored"):
            await harness.verify(assessment=substituted)

    @pytest.mark.asyncio
    async def test_payload_bytes_that_no_longer_hash_to_their_record_are_refused(self) -> None:
        harness = await _shadowing()
        await harness.record_d3_promotion()
        harness.artifacts.corrupt()

        with pytest.raises(LearnedRepositoryError) as error:
            await harness.verify()

        assert error.value.conflict is LearnedRepositoryConflict.INTEGRITY_FAILURE

    @pytest.mark.asyncio
    async def test_model_artifact_metadata_drift_is_refused(self) -> None:
        harness = await _shadowing()
        await harness.record_d3_promotion()
        harness.artifacts.add(fx.artifact_ref(size_bytes=fx.ARTIFACT_SIZE + 1))

        with pytest.raises(LearnedRepositoryError, match="no longer matches its record"):
            await harness.verify()

    @pytest.mark.asyncio
    async def test_an_ineligible_payload_cannot_verify(self) -> None:
        harness = await _shadowing()
        failing = _with_gate("safety", PromotionGateOutcome.FAILED)
        harness.payload = failing
        harness.d3_assessment = fx.d3_assessment(failing)
        await harness.record_d3_promotion()

        with pytest.raises(LearnedRepositoryError, match="not eligible: safety failed"):
            await harness.verify()

    @pytest.mark.asyncio
    async def test_a_registered_component_cannot_skip_shadow(self) -> None:
        harness = LifecycleHarness()
        await harness.register()
        await harness.record_d3_promotion()

        with pytest.raises(LearnedRepositoryError, match="only a shadowing component"):
            await harness.verify()


# ------------------------------------- S21D3-058: bytes are read again, immediately before


class TestActivationRevalidatesTheBytes:
    @pytest.mark.asyncio
    async def test_activation_rehashes_the_model_artifact_rather_than_trusting_the_lineage(
        self,
    ) -> None:
        harness = LifecycleHarness()
        await harness.register()
        await harness.gather_evidence()
        approval = await harness.approve()
        before = list(harness.artifacts.verify_calls)

        await harness.activate(approval)

        assert harness.artifacts.verify_calls[len(before) :].count(fx.ARTIFACT_ID) == 1

    @pytest.mark.asyncio
    async def test_bytes_replaced_after_verification_leave_the_state_unchanged(self) -> None:
        """Time-of-check/time-of-use: the lineage read succeeded, the bytes then changed."""
        harness = LifecycleHarness()
        await harness.register()
        await harness.gather_evidence()
        approval = await harness.approve()
        harness.artifacts.corrupt()

        with pytest.raises(LearnedRepositoryError) as error:
            await harness.activate(approval)

        row = await harness.service.get_component(fx.INERT.component_id)
        assert error.value.conflict is LearnedRepositoryConflict.INTEGRITY_FAILURE
        assert row is not None
        assert row.current_state is LearnedComponentState.VERIFIED
        assert await harness.service.active_component_for(fx.surface()) is None

    @pytest.mark.asyncio
    async def test_a_substituted_artifact_row_leaves_the_state_unchanged(self) -> None:
        harness = LifecycleHarness()
        await harness.register()
        await harness.gather_evidence()
        approval = await harness.approve()
        harness.artifacts.add(fx.artifact_ref(media_type="application/x-python-pickle"))

        with pytest.raises(LearnedRepositoryError, match="no longer matches its record"):
            await harness.activate(approval)

        row = await harness.service.get_component(fx.INERT.component_id)
        assert row is not None
        assert row.current_state is LearnedComponentState.VERIFIED

    @pytest.mark.asyncio
    async def test_no_artifact_is_ever_deserialised_on_either_path(self) -> None:
        """The store stub has no load, open or deserialise method. That is the whole proof."""
        harness = LifecycleHarness()

        assert not any(
            hasattr(harness.artifacts, name) for name in ("load", "open", "deserialise", "read")
        )
