"""S21D3-010..017: revision 3 freezes units, one feature change, and every gate."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from cognitive_os.learning.correction_protocol import (
    FITTED_FEATURE_V2_EMBEDDING,
    FITTED_FEATURE_V2_REMOVED,
    CorrectionDatasetProtocolV3,
    CorrectionDiagnosticProtocolV3,
    CorrectionEvaluationCountsV3,
    CorrectionFeatureContract,
    CorrectionFeatureContractV2,
    CorrectionPowerYieldAnalysisV3,
    CorrectionRankingUnitContractV3,
    CorrectionRetrievalProtocolV3,
    CorrectionSurfaceContract,
    CorrectionTransformationProtocolV3,
    D3GateBinding,
    D3GateManifest,
    D3OpenGateBinding,
)


def gate_manifest() -> D3GateManifest:
    return D3GateManifest(
        gate_l2=tuple(
            D3GateBinding(
                condition=condition,
                metric_or_invariant=f"condition_{condition}_metric",
                floor_or_rule=f"condition_{condition}_rule",
                evidence_handle=f"sprint-21d3-condition-{condition}.json",
                predecessor_reuse=condition in {1, 2, 3},
                stop_status="future_required",
            )
            for condition in range(1, 30)
        ),
        gate_d1_open=tuple(
            D3OpenGateBinding(
                condition=condition,
                closure_rule=f"condition_{condition}_closure",
                evidence_handle=f"sprint-21d3-d1-{condition}.json",
            )
            for condition in (6, 7, 15)
        ),
    )


class TestUnitCorrectRanking:
    def test_one_group_is_one_decision_and_four_outcomes(self) -> None:
        counts = CorrectionEvaluationCountsV3(
            task_groups=1,
            metamorphic_cases=1,
            ranking_decisions=1,
            candidate_outcomes=4,
            answered_decisions=1,
            abstained_decisions=0,
            changed_actions=1,
            confident_errors=0,
        )

        assert counts.ranking_decisions == 1
        assert counts.candidate_outcomes == 4
        assert CorrectionRankingUnitContractV3().content_hash

    def test_candidate_slots_cannot_be_reported_as_decisions(self) -> None:
        with pytest.raises(ValidationError, match="candidate outcomes must equal"):
            CorrectionEvaluationCountsV3(
                task_groups=10,
                metamorphic_cases=40,
                ranking_decisions=40,
                candidate_outcomes=40,
                answered_decisions=38,
                abstained_decisions=2,
                changed_actions=9,
                confident_errors=1,
            )

    def test_decisions_must_partition_into_answered_and_abstained(self) -> None:
        with pytest.raises(ValidationError, match="answered plus abstained"):
            CorrectionEvaluationCountsV3(
                task_groups=1,
                metamorphic_cases=0,
                ranking_decisions=1,
                candidate_outcomes=4,
                answered_decisions=1,
                abstained_decisions=1,
                changed_actions=0,
                confident_errors=0,
            )


class TestTheDiagnosticHasNoSelectionAuthority:
    def test_the_spent_members_and_setting_are_hash_bound(self) -> None:
        protocol = CorrectionDiagnosticProtocolV3()

        assert protocol.d2_groups == protocol.d2_ranking_decisions == 10
        assert protocol.d2_candidate_outcomes == 40
        assert protocol.d2_selection_hash.startswith("274a7a93")
        assert not protocol.selection_authority

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("selection_authority", True),
            ("development_only", False),
            ("new_d3_members_included", True),
        ],
    )
    def test_the_diagnostic_cannot_select_or_expand(self, field: str, value: bool) -> None:
        with pytest.raises(ValidationError, match="development-only"):
            CorrectionDiagnosticProtocolV3(**{field: value})  # type: ignore[arg-type]


class TestTheSingleFeatureRevision:
    def test_v2_names_every_embedding_dimension_and_removes_the_registered_channels(
        self,
    ) -> None:
        contract = CorrectionFeatureContractV2()

        assert len(FITTED_FEATURE_V2_EMBEDDING) == contract.embedding_dimensions == 384
        assert set(FITTED_FEATURE_V2_EMBEDDING) <= set(contract.allowlist)
        assert all(contract.rejects(field) for field in FITTED_FEATURE_V2_REMOVED)
        assert contract.canonical_prefix_bytes.endswith(b"python-grammar=3.12\n")

    def test_a_removed_v1_input_cannot_be_put_back(self) -> None:
        with pytest.raises(ValidationError, match="removed or forbidden"):
            CorrectionFeatureContractV2(
                allowlist=(
                    *CorrectionFeatureContractV2().allowlist,
                    "query_to_candidate_cosine",
                )
            )

    def test_the_released_v1_hash_did_not_change(self) -> None:
        assert (
            CorrectionFeatureContract().content_hash
            == "550646d6a2b22852ef26e6ab4960c98aeea2541da1afa39104d5828a0b4165c8"
        )
        assert (
            CorrectionSurfaceContract().content_hash
            == "f2a15b8c523de24fe514d47ec13c2407074917a8c376e048b5038dd6d2d03ca6"
        )


class TestExplicitDatasetAuthority:
    def test_revision_three_binds_schema_selection_and_partition(self) -> None:
        protocol = CorrectionDatasetProtocolV3()

        assert "feature_schema_hash" in protocol.identity_formula
        assert "canonical_selection_partition_digest" in protocol.identity_formula
        assert protocol.legacy_default_identities_readable_and_unchanged
        assert not protocol.migration_required

    @pytest.mark.parametrize(
        "field",
        ["store_wide_selection_allowed", "latest_seal_selection_allowed"],
    )
    def test_query_shaped_selection_is_refused(self, field: str) -> None:
        with pytest.raises(ValidationError, match="not evidence authorities"):
            CorrectionDatasetProtocolV3(**{field: True})  # type: ignore[arg-type]


class TestPowerAndTransformationCounts:
    def test_the_fixed_plan_has_both_reserves(self) -> None:
        analysis = CorrectionPowerYieldAnalysisV3()

        assert analysis.nominal_decisions_per_stage == 120
        assert analysis.minimum_valid_decisions_per_stage == 100
        assert int(analysis.retrieval_source_groups * analysis.assumed_retrieval_yield) == 51

    def test_candidate_slots_cannot_replace_the_metamorphic_decision_floor(
        self,
    ) -> None:
        with pytest.raises(ValidationError, match="fourfold"):
            CorrectionPowerYieldAnalysisV3(minimum_candidate_outcomes_per_stage=404)

    def test_retrieval_overproduction_must_still_yield_fifty_queries(self) -> None:
        with pytest.raises(ValidationError, match="fifty qualifying"):
            CorrectionPowerYieldAnalysisV3(assumed_retrieval_yield=Decimal("0.80"))

    def test_the_six_cases_create_120_group_decisions(self) -> None:
        protocol = CorrectionTransformationProtocolV3()

        assert len(protocol.cases) == 6
        assert protocol.groups_per_stage * len(protocol.cases) == 120
        assert not protocol.d2_calibration_ood_members_reused_for_selection


class TestTheSingleRetrievalCandidate:
    def test_the_exact_rrf_vector_has_one_order(self) -> None:
        protocol = CorrectionRetrievalProtocolV3()
        scores = {
            "a": protocol.fused_score(1, 3),
            "b": protocol.fused_score(2, 1),
            "c": protocol.fused_score(None, 2),
        }

        assert sorted(scores, key=scores.get, reverse=True) == ["b", "a", "c"]  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("field", "value"),
        [("bounded_ged_in_fusion", True), ("parameter_sweep_allowed", True)],
    )
    def test_no_second_arm_or_sweep_can_open(self, field: str, value: bool) -> None:
        with pytest.raises(ValidationError, match="outside the frozen RRF"):
            CorrectionRetrievalProtocolV3(**{field: value})  # type: ignore[arg-type]

    def test_early_truncation_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            CorrectionRetrievalProtocolV3(output_truncations=2)


class TestEveryGateIsBound:
    def test_the_manifest_has_all_29_plus_the_three_open_d1_conditions(self) -> None:
        manifest = gate_manifest()

        assert len(manifest.gate_l2) == 29
        assert {item.condition for item in manifest.gate_d1_open} == {6, 7, 15}
        assert manifest.bootstrap_seed == 21041
        assert manifest.bootstrap_resamples == 2000

    def test_a_duplicate_gate_cannot_hide_a_missing_gate(self) -> None:
        manifest = gate_manifest()
        duplicate = (*manifest.gate_l2[:-1], manifest.gate_l2[0])

        with pytest.raises(ValidationError, match="1 through 29"):
            D3GateManifest(gate_l2=duplicate, gate_d1_open=manifest.gate_d1_open)

    def test_a_conditional_child_must_name_the_parent_stop_hash(self) -> None:
        manifest = gate_manifest()

        with pytest.raises(ValidationError, match="parent stop hash"):
            D3GateManifest(
                gate_l2=manifest.gate_l2,
                gate_d1_open=manifest.gate_d1_open,
                typed_not_opened_required_fields=(
                    "status",
                    "item",
                    "reason",
                    "content_hash",
                ),
            )
