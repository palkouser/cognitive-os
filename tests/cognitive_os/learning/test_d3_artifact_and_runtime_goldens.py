"""S21D3-048, -050 and -059: the goldens, and the not-opened map the wave actually wrote.

Three things this file pins that nothing else can.

The two schemas have golden hashes. A schema is a promise about bytes that already exist; if
its JSON representation changes without anyone noticing, every artifact and payload hash in
the sprint's evidence becomes a hash of something the code no longer describes.

The gate list has a fixed order. Precedence is what makes two evaluations of the same payload
name the same failure, and an order that drifted would make the recorded reason a function of
which day it was run.

The not-opened map is complete. Section 11.1 requires a typed record for every dependent
conditional task, and "we listed the ones we remembered" is exactly the failure a checklist
prevents — so the map is compared against the E05/E06/E07 items the backlog itself declares.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from cognitive_os.domain.promotion_payload import (
    D3_PROMOTION_GATES,
    D3_PROMOTION_SCHEMA,
    D3_PROMOTION_SCHEMA_VERSION,
    D3PromotionPayload,
    D3RuntimeConfiguration,
)
from cognitive_os.learning.correction_artifact import (
    CORRECTION_ARTIFACT_SCHEMA_V2,
    CORRECTION_ARTIFACT_SCHEMA_V2_VERSION,
    CorrectionArtifactPayloadV2,
)

REPOSITORY = Path(__file__).resolve().parents[3]
BACKLOG = REPOSITORY / "docs/sprints/sprint-21/sprint-21d3-technical-backlog.md"
CHECKPOINT = REPOSITORY / "docs/sprints/sprint-21/evidence/sprint-21d3-pre-final-checkpoint.json"
INVARIANCE = REPOSITORY / "docs/sprints/sprint-21/evidence/sprint-21d3-runtime-invariance.json"

#: The exact D3 candidate-path items that cannot open without a selected artifact, plus every
#: E06 and E07 item. S21D3-075 is the declared exception: it is an unconditional substrate gate
#: that runs against the isolated lifecycle fixture, so it is never `not_opened`.
EXPECTED_NOT_OPENED = {
    "S21D3-051",
    "S21D3-054",
    "S21D3-056",
    *(f"S21D3-0{number}" for number in range(60, 70)),
    *(f"S21D3-0{number}" for number in (70, 71, 72, 73, 74, 76, 77)),
}


def _schema_hash(model: type) -> str:
    return sha256(
        json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TestTheGoldenSchemas:
    def test_the_d3_promotion_payload_schema_is_the_one_the_evidence_was_written_under(
        self,
    ) -> None:
        assert D3_PROMOTION_SCHEMA == "d3-promotion-payload"
        assert D3_PROMOTION_SCHEMA_VERSION == 2
        assert (
            _schema_hash(D3PromotionPayload)
            == "3d44b33fef639b80e3437594b45fe8d7483da497526060c0e38da63bf6dd329e"
        )

    def test_the_v2_correction_artifact_schema_is_the_one_the_loader_was_written_for(self) -> None:
        assert CORRECTION_ARTIFACT_SCHEMA_V2 == "correction-ranking-artifact-v2"
        assert CORRECTION_ARTIFACT_SCHEMA_V2_VERSION == 2
        assert (
            _schema_hash(CorrectionArtifactPayloadV2)
            == "f009a5f90fba7bc15cfeeee03bf5df68f09ed43a50014bd43676bed50195d518"
        )

    def test_the_runtime_configuration_schema_is_pinned_too(self) -> None:
        """Both sealed configuration hashes are hashes *of this shape*."""
        assert (
            _schema_hash(D3RuntimeConfiguration)
            == "0b5e5d2f878ade7f91fa13588007a0810f37fdbe1c8bc123a5bab4d8b00dd249"
        )


class TestTheGateOrderIsFixed:
    def test_every_gate_is_unique_and_the_order_is_the_declared_precedence(self) -> None:
        assert len(set(D3_PROMOTION_GATES)) == len(D3_PROMOTION_GATES) == 20
        assert D3_PROMOTION_GATES[0] == "feature_contract"
        assert D3_PROMOTION_GATES[-1] == "canary_to_steady_transition"

    def test_identity_gates_precede_measurement_gates_which_precede_runtime_gates(self) -> None:
        position = {name: index for index, name in enumerate(D3_PROMOTION_GATES)}

        assert position["feature_contract"] < position["matrix"] < position["benefit"]
        assert position["benefit"] < position["artifact"] < position["canary_configuration"]


class TestTheWaveEvidence:
    def test_the_checkpoint_refuses_final_access_and_names_the_selection_as_the_stop(self) -> None:
        checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

        assert checkpoint["decision"]["authorised"] is False
        assert checkpoint["decision"]["stop_source"] == "S21D3-039 candidate selection"
        assert checkpoint["final_or_canary_outcomes_inspected"] == 0
        assert checkpoint["artifact_contract"]["selected_artifact_exists"] is False

    def test_every_dependent_item_carries_a_typed_record_bound_to_one_stop_hash(self) -> None:
        checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        records = checkpoint["not_opened"]
        stop = checkpoint["decision"]["stop_hash"]

        assert {item["item"] for item in records} == EXPECTED_NOT_OPENED
        assert {item["status"] for item in records} == {"not_opened"}
        assert {item["stop_hash"] for item in records} == {stop}

    def test_the_unconditional_substrate_gate_is_not_in_the_not_opened_map(self) -> None:
        checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

        assert "S21D3-075" not in {item["item"] for item in checkpoint["not_opened"]}
        assert [item["item"] for item in checkpoint["unconditional"]] == ["S21D3-075"]

    def test_no_configuration_is_sealed_when_access_was_not_authorised(self) -> None:
        checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

        assert all(
            value["sealed"] is False for value in checkpoint["runtime_configurations"].values()
        )
        assert checkpoint["canary_to_steady_condition"]["sealed"] is False

    def test_every_named_dependent_item_exists_in_the_backlog(self) -> None:
        """A map naming an item nobody planned would be a map of this script's imagination."""
        backlog = BACKLOG.read_text(encoding="utf-8")

        for item in sorted(EXPECTED_NOT_OPENED):
            assert f"### {item} " in backlog

    def test_the_mandatory_path_is_identical_under_every_fallback_configuration(self) -> None:
        invariance = json.loads(INVARIANCE.read_text(encoding="utf-8"))["mandatory_path_invariance"]

        assert invariance["identical"] is True
        assert len(invariance["configurations_compared"]) >= 15
        assert invariance["only_a_bounded_campaign_may_reorder"] is True

    def test_every_runtime_reason_code_was_reached_by_the_matrix(self) -> None:
        matrix = json.loads(INVARIANCE.read_text(encoding="utf-8"))["resolver_matrix"]

        assert matrix["unreached_reason_codes"] == []
        assert matrix["every_reason_code_is_reachable"] is True
        assert matrix["purity"]["provider_network_gpu_or_credential_calls_possible"] is False

    def test_the_measured_evidence_says_which_artifact_it_measured(self) -> None:
        invariance = json.loads(INVARIANCE.read_text(encoding="utf-8"))

        assert invariance["artifact_under_test"] == "contract_fixture"
        assert invariance["creates_lifecycle_state"] is False
        assert invariance["writes_to_any_artifact_store"] is False

    @pytest.mark.parametrize("path", [CHECKPOINT, INVARIANCE])
    def test_the_evidence_binds_the_pre_registration_bytes(self, path: Path) -> None:
        document = json.loads(path.read_text(encoding="utf-8"))

        assert document["pre_registration_sha256"] == (
            "191b3757ded21a1c2c85459a34902f8dee3f2f35b0979b557f84c1a37fe6a191"
        )
        assert document["final_outcomes_inspected"] is False
