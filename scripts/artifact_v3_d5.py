#!/usr/bin/env python3
"""S21D5-050: prove the v3 artifact does what §4.2 said, by running it rather than describing it.

Three claims, and each is executed here:

*A direction round-trips into exactly one class.* Canonical inert JSON in, a
`PairwiseContrastiveRanker` out, the same model hash it went in with. No import path in the
bytes, no class name, no way for a tampered artifact to produce a different *kind* of thing.

*Every refusal the frozen contract names actually refuses.* Six of them, each driven with bytes
that break exactly one rule, and each recorded with the error it raised. A refusal list nobody
executes is a list of intentions.

*v1 and v2 are untouched.* The v3 schema is a third name, not a relaxation of the second, so the
released v2 shape must still hash to the golden `test_d3_artifact_and_runtime_goldens` pinned —
recomputed here rather than cited, because a schema digest that only a test knows about proves
nothing to a reader of this record.

The size claim §4.2 makes is *measured* here and asserted nowhere: a direction is 390 floats
whatever it was fitted on, where an exemplar-set artifact carries one 390-channel vector per
fitting row. S21D5-052 records the stored size of the real artifact; this records the shape of
the difference at D5's pool size so the later number has something to be read against.

    UV_CACHE_DIR=.cache/uv uv run python scripts/artifact_v3_d5.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.learning.correction_artifact import (  # noqa: E402
    CORRECTION_ARTIFACT_SCHEMA,
    CORRECTION_ARTIFACT_SCHEMA_V2,
    CORRECTION_ARTIFACT_SCHEMA_V3,
    IMPLEMENTED_HYPOTHESIS_CLASSES,
    MAXIMUM_EXEMPLARS,
    CorrectionArtifactError,
    CorrectionArtifactPayloadV3,
    build_payload_v3,
    canonical_bytes,
    correction_artifact_schema,
    load_correction_ranker_any,
    load_correction_ranker_v3,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
)
from cognitive_os.learning.correction_ranking import ENCODER_VERSION_V2  # noqa: E402
from cognitive_os.learning.pairwise_contrastive import (  # noqa: E402
    HYPOTHESIS_CLASS,
    PairwiseContrastiveModel,
    PairwiseContrastiveRanker,
)
from cognitive_os.learning.selective_operating_point import DERIVATION_RULE  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"

#: A fixture direction. Nothing here is fitted on a D5 role: S21D5-050 proves the *shape* reads
#: back, and the first fitted artifact is S21D5-052's, after a candidate is selected.
FIXTURE = {
    "descriptor": "d" * 64,
    "manifest": "a" * 64,
    "selection": "b" * 64,
    "members": "c" * 64,
    "setting": "e" * 64,
    "point": "f" * 64,
    "certificate": "9" * 64,
}

#: D5's fitting pool, for the size comparison. 180 groups times four candidates.
D5_FITTING_ROWS = 720


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _ranker(margin_floor: str = "0.25") -> PairwiseContrastiveRanker:
    model = PairwiseContrastiveModel(
        encoder_version=ENCODER_VERSION_V2,
        feature_names=FITTED_FEATURE_V2_ALLOWLIST,
        weights=tuple(0.001 * (index + 1) for index in range(len(FITTED_FEATURE_V2_ALLOWLIST))),
        regularization="1",
        fitted_group_count=180,
        fitted_pair_count=D5_FITTING_ROWS,
    )
    return PairwiseContrastiveRanker(model, margin_floor=Decimal(margin_floor))


def _payload() -> CorrectionArtifactPayloadV3:
    return build_payload_v3(
        component_revision=1,
        descriptor_hash=FIXTURE["descriptor"],
        code_revision="21d5",
        ranker=_ranker(),
        training_dataset_id=UUID(int=1),
        calibration_dataset_id=UUID(int=2),
        example_manifest_hash=FIXTURE["manifest"],
        split_manifest_hash=FIXTURE["manifest"],
        selection_manifest_hash=FIXTURE["selection"],
        member_manifest_hash=FIXTURE["members"],
        feature_schema_hash=FIXTURE["manifest"],
        embedding_revision="1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
        numeric_lower=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 0.0),
        numeric_upper=dict.fromkeys(FITTED_FEATURE_V2_SCALARS, 100.0),
        setting_identity=FIXTURE["setting"],
        operating_point_hash=FIXTURE["point"],
        calibration_certificate_hash=FIXTURE["certificate"],
    )


def _tampered(**changes: Any) -> bytes:
    document = json.loads(canonical_bytes(_payload()))
    document.update(changes)
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def _load(data: bytes, **overrides: Any) -> Any:
    fields: dict[str, Any] = {
        "expected_component_id": PairwiseContrastiveRanker.component_id,
        "expected_revision": 1,
        "expected_surface": PairwiseContrastiveRanker.surface,
        "expected_descriptor_hash": FIXTURE["descriptor"],
    }
    fields.update(overrides)
    return load_correction_ranker_v3(data, **fields)


def _round_trip() -> dict[str, Any]:
    payload = _payload()
    data = canonical_bytes(payload)
    ranker, read = _load(data)
    return {
        "schema_name": read.schema_name,
        "schema_version": read.schema_version,
        "artifact_bytes": len(data),
        "artifact_sha256": _digest(data),
        "built_class": type(ranker).__name__,
        "model_hash_in": _ranker().model.content_hash(),
        "model_hash_out": ranker.model.content_hash(),
        "model_survives_the_round_trip": ranker.model.content_hash()
        == _ranker().model.content_hash(),
        "margin_floor": str(ranker.margin_floor),
        "hypothesis_class": read.hypothesis_class,
        "weights": len(read.weights),
        "channels_are_the_v2_allowlist_in_order": read.feature_channels
        == FITTED_FEATURE_V2_ALLOWLIST,
        "encoder_version": read.encoder_version,
        "carries_no_hash_of_itself": "content_hash" not in json.loads(data),
        "carries_no_import_path": not any(
            key in json.loads(data) for key in ("class", "module", "import_path", "callable")
        ),
        "operating_point": {
            "margin_floor": str(read.margin_floor),
            "operating_point_hash": read.operating_point_hash,
            "derivation_rule_is_the_released_constant": (
                read.operating_point_derivation_rule == DERIVATION_RULE
            ),
            "calibration_certificate_hash": read.calibration_certificate_hash,
            "reading": (
                "the rule's wording names the k-NN confidence and that is correct: S21D5-016's "
                "only substitution is the quantity scored -- the top-two projection margin -- "
                "and derive_zero_error_point treats a confidence as an opaque ordered score, so "
                "the certification spine is inherited rather than rewritten"
            ),
        },
    }


def _refusals() -> dict[str, Any]:
    """Drive each frozen refusal with bytes breaking exactly one rule, and record what raised."""
    reordered = list(FITTED_FEATURE_V2_ALLOWLIST)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    cases: list[tuple[str, bytes]] = [
        ("a weight vector that is not 390 long", _tampered(weights=[0.1] * 389)),
        ("a weight vector that is not finite", _tampered(weights=[float("inf")] + [0.1] * 389)),
        (
            "a channel list that is not the v2 allowlist in fitted order",
            _tampered(feature_channels=reordered),
        ),
        ("a non-positive ridge", _tampered(regularization="0")),
        ("a negative margin floor", _tampered(margin_floor="-0.1")),
        (
            "a hypothesis_class the loader does not implement",
            _tampered(hypothesis_class="pairwise-contrastive-linear-v2"),
        ),
        (
            "a schema_name the loader does not know",
            json.dumps({"schema_name": "correction-ranking-artifact-v9"}).encode(),
        ),
    ]
    rows = []
    for action, data in cases:
        try:
            if json.loads(data).get("schema_name") == CORRECTION_ARTIFACT_SCHEMA_V3:
                _load(data)
            else:
                load_correction_ranker_any(
                    data,
                    expected_component_id=PairwiseContrastiveRanker.component_id,
                    expected_revision=1,
                    expected_surface=PairwiseContrastiveRanker.surface,
                    expected_descriptor_hash=FIXTURE["descriptor"],
                )
        except CorrectionArtifactError as error:
            rows.append({"refuses": action, "refused": True, "error": str(error)[:200]})
            continue
        rows.append({"refuses": action, "refused": False, "error": None})
    return {
        "cases": rows,
        "declared_in_the_contract": 6,
        "executed": len(rows),
        "every_declared_refusal_refuses": all(row["refused"] for row in rows),
    }


def _dispatch() -> dict[str, Any]:
    """The descriptor is required where the schema binds one and refused where it does not."""
    data = canonical_bytes(_payload())
    rows: list[dict[str, Any]] = []

    def _record(action: str, call: Any) -> None:
        try:
            call()
        except CorrectionArtifactError as error:
            rows.append({"action": action, "refused": True, "error": str(error)[:160]})
            return
        rows.append({"action": action, "refused": False, "error": None})

    _record(
        "load a v3 artifact with no descriptor to check it against",
        lambda: load_correction_ranker_any(
            data,
            expected_component_id=PairwiseContrastiveRanker.component_id,
            expected_revision=1,
            expected_surface=PairwiseContrastiveRanker.surface,
        ),
    )
    _record(
        "load a v1 artifact while passing a descriptor it has no field for",
        lambda: load_correction_ranker_any(
            json.dumps({"schema_name": CORRECTION_ARTIFACT_SCHEMA}).encode(),
            expected_component_id="learned.correction_ranking",
            expected_revision=1,
            expected_surface="experience.correction_ranking",
            expected_descriptor_hash=FIXTURE["descriptor"],
        ),
    )
    ranker, payload = load_correction_ranker_any(
        data,
        expected_component_id=PairwiseContrastiveRanker.component_id,
        expected_revision=1,
        expected_surface=PairwiseContrastiveRanker.surface,
        expected_descriptor_hash=FIXTURE["descriptor"],
    )
    return {
        "schema_read_without_running_a_loader": correction_artifact_schema(data),
        "known_schemas": sorted(
            (
                CORRECTION_ARTIFACT_SCHEMA,
                CORRECTION_ARTIFACT_SCHEMA_V2,
                CORRECTION_ARTIFACT_SCHEMA_V3,
            )
        ),
        "v3_routes_to": type(ranker).__name__,
        "v3_payload_type": type(payload).__name__,
        "asymmetry_cases": rows,
        "both_directions_refuse": all(row["refused"] for row in rows),
        "why": (
            "a caller passing a descriptor believes it is being checked, and a caller omitting "
            "one for a schema that binds it has dropped a lineage check. Trying each loader "
            "until one stops raising would report the last refusal rather than the real one"
        ),
    }


#: The v2 shape's golden digest, from `test_d3_artifact_and_runtime_goldens`. Adding a third
#: schema must not move it: an artifact hash recorded in D3's evidence is a hash of bytes
#: written under this shape, and a shape that drifted would make that hash describe nothing.
V2_SCHEMA_GOLDEN = "f009a5f90fba7bc15cfeeee03bf5df68f09ed43a50014bd43676bed50195d518"


def _predecessors_untouched() -> dict[str, Any]:
    """Recompute the released v2 schema digest. Cited digests are not evidence."""
    from cognitive_os.learning.correction_artifact import CorrectionArtifactPayloadV2

    found = _digest(
        json.dumps(
            CorrectionArtifactPayloadV2.model_json_schema(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    return {
        "v2_schema_digest": found,
        "v2_schema_golden": V2_SCHEMA_GOLDEN,
        "identical": found == V2_SCHEMA_GOLDEN,
        "source_of_the_golden": (
            "tests/cognitive_os/learning/test_d3_artifact_and_runtime_goldens.py"
        ),
        "why": (
            "every artifact hash in D3's and D4's evidence is a hash of bytes written under this "
            "shape; a shape that drifted would leave those hashes describing nothing"
        ),
    }


def _size() -> dict[str, Any]:
    """Measured, not asserted, and not a Gate L2 condition."""
    direction = len(canonical_bytes(_payload()))
    #: One exemplar is six named scalars plus 384 embedding floats plus a boolean, as canonical
    #: JSON. Measured on this fixture's own encoding rather than estimated.
    one_channel_vector = len(
        json.dumps(
            {
                "values": [[name, 0.5] for name in FITTED_FEATURE_V2_SCALARS],
                "embedding": [0.123456789] * 384,
                "accepted": True,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    projected = direction + one_channel_vector * D5_FITTING_ROWS
    return {
        "v3_direction_bytes": direction,
        "one_exemplar_bytes": one_channel_vector,
        "d5_fitting_rows": D5_FITTING_ROWS,
        "projected_exemplar_set_bytes_at_d5_pool_size": projected,
        "ratio": round(projected / direction, 1),
        "maximum_exemplars_cap": MAXIMUM_EXEMPLARS,
        "inference": (
            "one dot product per candidate over 390 channels, against a scan over the whole "
            "exemplar set"
        ),
        "asserted": False,
        "measured_for_real_at": "S21D5-052, on the fitted artifact",
    }


def _evidence() -> tuple[dict[str, Any], list[str]]:
    round_trip = _round_trip()
    refusals = _refusals()
    dispatch = _dispatch()
    predecessors = _predecessors_untouched()
    contract = CorrectionFeatureContractV2()
    body = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W1",
        "items": ["S21D5-050"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": _digest(CONTRACTS.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Prove CorrectionArtifactPayloadV3 and its schema-name dispatch by executing them: "
            "the round trip into one class, every frozen refusal, and the descriptor asymmetry "
            "the dispatcher exists to enforce. Nothing here is fitted on a D5 role."
        ),
        "why_a_third_schema": (
            "v2 declares exemplars with min_length 1 and three proportion floors. Making them "
            "optional would let an exemplar-free v2 artifact load, which is the "
            "check-that-passes-without-touching-its-question defect the D4 report catalogued "
            "twelve times"
        ),
        "unchanged_from_v2": {
            "encoder_version": ENCODER_VERSION_V2,
            "feature_contract_hash": contract.content_hash,
            "normalizer_version": contract.normalizer_version,
            "fitted_channels": len(FITTED_FEATURE_V2_ALLOWLIST),
            "reading": (
                "D5 changes no encoder, no normaliser, no channel and no fitted "
                "representation; it changes the function fitted on top of them"
            ),
        },
        "implemented_hypothesis_classes": sorted(IMPLEMENTED_HYPOTHESIS_CLASSES),
        "predecessors_untouched": predecessors,
        "round_trip": round_trip,
        "refusals": refusals,
        "dispatch": dispatch,
        "size": _size(),
        "fitted_on_a_d5_role": False,
        "spends": {
            "calibration_cases": 0,
            "final_members": 0,
            "canary_members": 0,
            "retrieval_judgements": 0,
        },
    }

    stops: list[str] = []
    if not round_trip["model_survives_the_round_trip"]:
        stops.append("artifact_v3_round_trip_lost_the_model")
    if round_trip["built_class"] != PairwiseContrastiveRanker.__name__:
        stops.append("artifact_v3_built_the_wrong_class")
    if not round_trip["carries_no_hash_of_itself"] or not round_trip["carries_no_import_path"]:
        stops.append("artifact_v3_payload_carries_what_it_must_not")
    if round_trip["hypothesis_class"] != HYPOTHESIS_CLASS:
        stops.append("artifact_v3_names_an_unimplemented_class")
    if not refusals["every_declared_refusal_refuses"]:
        stops.append("artifact_v3_a_declared_refusal_does_not_refuse")
    if not dispatch["both_directions_refuse"]:
        stops.append("artifact_v3_dispatch_drops_a_lineage_check")
    if not predecessors["identical"]:
        stops.append("artifact_v3_moved_the_released_v2_schema")
    return body, stops


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d5-artifact-v3.json")
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    arguments = parser.parse_args()

    body, stops = _evidence()
    if arguments.check:
        print(json.dumps({"stops": stops}, indent=1))
        return 1 if stops else 0

    sealed = _seal(body)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(_canonical(sealed) + b"\n")

    print(f"{arguments.output.name}  {sealed['integrity_content_hash']}")
    print(
        f"  round trip: {body['round_trip']['built_class']}, "
        f"{body['round_trip']['weights']} weights, "
        f"{body['round_trip']['artifact_bytes']} bytes"
    )
    print(
        f"  refusals:   {body['refusals']['executed']} executed, "
        f"all refuse: {body['refusals']['every_declared_refusal_refuses']}"
    )
    print(
        f"  dispatch:   {len(body['dispatch']['known_schemas'])} known schemas, "
        f"both asymmetry cases refuse: {body['dispatch']['both_directions_refuse']}"
    )
    print(f"  v2 golden:  unmoved: {body['predecessors_untouched']['identical']}")
    print(f"  size:       {body['size']['ratio']}x smaller than an exemplar set at 720 rows")
    if stops:
        print("STOPS: " + ", ".join(stops))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
