#!/usr/bin/env python3
"""S21D4-048 and -059: the artifact and runtime wave, decided against W2's null selection.

W4's exit is "the D3-built surface exercised against a real artifact, then one pre-final access
decision". There is no real artifact. S21D4-039 selected none, so S21D4-050 through -058 have
nothing to fit, load, sequence, register, verify or revalidate, and re-running D3's fixture
proofs would produce a second record about a contract fixture D3 already measured. That is the
defect class this backlog names by name -- a check that passes against something that is not
the question -- so those items are refused and recorded rather than performed.

What is left of W4 is real work and it is done: S21D4-048 is unconditional, and S21D4-059 is a
decision that has to be made on every outcome.

`sprint-21d4-pre-final-checkpoint.json` carries both. It measures three things in process and
decides one:

*The condition-20 gate row.* Gate L2 condition 20 read D3's 120 metamorphic decisions as 120;
they were 20 replicated six times. The row now names both denominators and the calibration
certificate its answered set was decided under, and a measured row cannot be built without
them. The addition had to move no stored payload, which is measured here rather than asserted:
a payload carrying no counts serialises to the bytes the D3 code produced, byte for byte.

*What S21D4-050 could have checked without a candidate.* Its acceptance names four things that
must be **unchanged** -- 390 channels in fitted order, the feature contract hash, the normaliser
and the grammar. Those are checkable now, and a drift in any of them during W2 or W3 would show
up here. The threshold binding itself is not opened: there is no derived threshold to bind.

*The preconditions, in backlog order.* First failure wins, and it is the first one: the null
selection. Every dependent task gets a typed record bound to that one stop hash.

Read-only. No store is opened, no lifecycle state is created, no artifact bytes are written, and
no final, promotion or canary outcome is inspected.

    UV_CACHE_DIR=.cache/uv uv run python scripts/artifact_runtime_d4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.domain.promotion_payload import (  # noqa: E402
    CONDITION_20_GATE,
    D3_PROMOTION_GATES,
    D3_PROMOTION_MEDIA_TYPE,
    D3_PROMOTION_SCHEMA,
    D3_PROMOTION_SCHEMA_VERSION,
    LEGACY_PROMOTION_SCHEMA,
    LEGACY_PROMOTION_SCHEMA_VERSION,
    CanaryToSteadyCondition,
    D3ArtifactBinding,
    D3PromotionPayload,
    D3RuntimeConfiguration,
    PromotionDependency,
    PromotionGateOutcome,
    PromotionGateRecord,
    canonical_payload_bytes,
    promotion_payload_version,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    CORRECTION_ARTIFACT_MEDIA_TYPE,
    CORRECTION_ARTIFACT_SCHEMA_V2,
)
from cognitive_os.learning.correction_protocol import (  # noqa: E402
    FITTED_FEATURE_V2_ALLOWLIST,
    FITTED_FEATURE_V2_SCALARS,
    CorrectionFeatureContractV2,
    DecisionCensusV4,
)
from cognitive_os.learning.promotion import (  # noqa: E402
    D3PromotionBindings,
    condition_20_gate,
    evaluate_d3_promotion,
)

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SELECTION = EVIDENCE / "sprint-21d4-learner-selection.json"
CONTINUATION = EVIDENCE / "sprint-21d4-continuation.json"
RETRIEVAL_DECISION = EVIDENCE / "sprint-21d4-retrieval-decision.json"
OUTPUT = EVIDENCE / "sprint-21d4-pre-final-checkpoint.json"

#: S21D4-050's unchanged-identity clause, quoted from the backlog so a drift is a diff here.
FROZEN_FEATURE_CONTRACT_HASH = "492c90a5df420de9d1662d17155ac8b28713e69bbd4bbe56208415d6ca076362"
FROZEN_FEATURE_CHANNELS = 390
FROZEN_NORMALISER = "cogos-python-alpha-normalizer-v2"
FROZEN_GRAMMAR = "3.12"

#: Every task that cannot open once S21D4-039 selects nothing, with what each would have done.
#: Written out rather than derived from a range, so the map is reviewable against the backlog's
#: own headings -- which `test_d4_pre_final_checkpoint_evidence.py` then does in both directions.
DEPENDENT_ITEMS: tuple[tuple[str, str], ...] = (
    ("S21D4-050", "bind the derived threshold and its provenance into the artifact"),
    ("S21D4-051", "fit and store the selected artifact"),
    ("S21D4-052", "prove the loader and resolver against the real artifact"),
    ("S21D4-053", "route sequencing through the receipt-aware remainder"),
    ("S21D4-054", "prove the selected-artifact vertical slice"),
    ("S21D4-055", "re-prove mandatory-path and configuration invariance"),
    ("S21D4-056", "register the exact artifact and enter SHADOW"),
    ("S21D4-057", "exercise evidence-bound verification"),
    ("S21D4-058", "revalidate artifact bytes immediately before activation"),
    ("S21D4-060", "seal final features and predictions before execution"),
    ("S21D4-061", "execute final batch A without replacement"),
    ("S21D4-062", "execute final batch B as independent confirmation"),
    ("S21D4-063", "compute paired material benefit"),
    ("S21D4-064", "run safety and cross-domain anti-forgetting replay"),
    ("S21D4-065", "execute promotion-scale metamorphic and OOD evaluation"),
    ("S21D4-066", "run true shadow mode against final evidence"),
    ("S21D4-067", "build the strengthened promotion assessment"),
    ("S21D4-068", "assess the three open Gate D1 conditions"),
    ("S21D4-069", "advance through evidence-bound verification"),
    ("S21D4-070", "prepare the exact activation bundle"),
    ("S21D4-071", "record explicit human approval"),
    ("S21D4-072", "activate canary-only routing atomically"),
    ("S21D4-073", "execute the governed canary with stop-first semantics"),
    ("S21D4-074", "exercise kill switch, disable, and fallback after restart"),
    ("S21D4-076", "promote from canary routing to bounded steady state"),
    ("S21D4-077", "prove final active state and replacement readiness"),
)

#: The one exception the backlog declares: receipt-chain rollback is an unconditional substrate
#: gate and runs against the isolated lifecycle fixture whether or not D4 activates.
UNCONDITIONAL_ITEMS: tuple[tuple[str, str], ...] = (
    ("S21D4-075", "receipt-selected rollback restoration and refusal, on the isolated fixture"),
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write(path: Path, value: dict[str, Any]) -> str:
    seal = _digest(_canonical(value))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical({**value, "integrity_content_hash": seal}))
    return seal


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------ S21D4-048: condition 20's denominators


FIXTURE_COMPONENT = "s21d4.checkpoint.fixture"
FIXTURE_SURFACE = "correction.candidate_ranking"
FIXTURE_ARTIFACT_ID = UUID(int=0)


def _fixture_configurations() -> tuple[
    D3RuntimeConfiguration, D3RuntimeConfiguration, CanaryToSteadyCondition
]:
    """Two configurations and a transition, existing only so bindings can be built.

    Nothing here is sealed and nothing is the D4 canary: sealing happens at authorised final
    access, which this record refuses. They exist because `evaluate_d3_promotion` checks
    identity before measurement, so a precedence proof needs bindings that actually match.
    """
    common: dict[str, Any] = {
        "component_id": FIXTURE_COMPONENT,
        "component_revision": 1,
        "surface": FIXTURE_SURFACE,
        "routing_manifest_hash": _digest("s21d4:routing-manifest"),
        "sequence_mode": "stop_on_first_accepted",
        "persistence_enabled": True,
        "activation_enabled": True,
        "kill_switch_enabled": True,
        "maximum_inference_ms": 250,
        "fallback_on_refusal": "frozen deterministic baseline order",
    }
    return (
        D3RuntimeConfiguration(
            name="checkpoint_fixture_canary",
            routed_group_ids=("fixture-01",),
            maximum_tasks=20,
            **common,
        ),
        D3RuntimeConfiguration(
            name="checkpoint_fixture_steady",
            routed_group_ids=("fixture-01", "fixture-02"),
            maximum_tasks=200,
            **common,
        ),
        CanaryToSteadyCondition(minimum_canary_tasks=20, rollback_target_revision=1),
    )


def _fixture_payload(gates: tuple[PromotionGateRecord, ...]) -> D3PromotionPayload:
    """A payload shaped like a promotion, built here, describing nothing that was measured.

    Every identity in it is a constant of this script. It exists so the contract's own rules can
    be executed against real bytes; it is never stored, and `selected_artifact_exists` stays
    false in the record it feeds.
    """
    canary, steady, transition = _fixture_configurations()
    return D3PromotionPayload(
        component_id=FIXTURE_COMPONENT,
        component_revision=1,
        surface=FIXTURE_SURFACE,
        code_revision="s21d4-w4-checkpoint",
        legacy_assessment_hash=_digest("s21d4:legacy-assessment"),
        legacy_decision="not_eligible",
        gates=gates,
        dependencies=(
            PromotionDependency(name="fixture", content_hash=_digest("s21d4:dependency")),
        ),
        artifact=D3ArtifactBinding(
            artifact_id=FIXTURE_ARTIFACT_ID,
            media_type="application/octet-stream",
            schema_name=CORRECTION_ARTIFACT_SCHEMA_V2,
            schema_version=2,
            content_hash=_digest("s21d4:artifact"),
            size_bytes=1,
        ),
        canary_configuration_hash=canary.content_hash,
        steady_state_configuration_hash=steady.content_hash,
        canary_to_steady_condition_hash=transition.content_hash,
        recorded_at=datetime(2026, 8, 7, tzinfo=UTC),
    )


def _fixture_bindings() -> D3PromotionBindings:
    canary, steady, transition = _fixture_configurations()
    return D3PromotionBindings(
        component_id=FIXTURE_COMPONENT,
        component_revision=1,
        surface=FIXTURE_SURFACE,
        artifact_content_hash=_digest("s21d4:artifact"),
        artifact_size_bytes=1,
        canary_configuration=canary,
        steady_state_configuration=steady,
        canary_to_steady_condition=transition,
        dependency_hashes={"fixture": _digest("s21d4:dependency")},
    )


def _gate(name: str, outcome: PromotionGateOutcome) -> PromotionGateRecord:
    return PromotionGateRecord(
        name=name,
        outcome=outcome,
        evidence_hash=_digest(f"s21d4:gate:{name}"),
        detail=f"checkpoint fixture: {name} carries no measurement",
    )


def _refusal(build: Any) -> str | None:
    """Run something that must refuse, and return why. `None` means it did not refuse.

    Only the contract's own sentence is kept. Pydantic appends the offending input to every
    message, and a record carrying a truncated repr of its own fixture would be noise wearing
    the shape of evidence.
    """
    try:
        build()
    except Exception as error:  # the contract raises pydantic's type; the verdict is the same
        for line in str(error).splitlines():
            if line.strip().startswith("Value error, "):
                return line.strip().removeprefix("Value error, ").split(" [type=")[0]
        return str(error).splitlines()[0]
    return None


def _precedence_proof() -> dict[str, Any]:
    """S21D4-048's third clause, executed rather than restated.

    Two gates fail and the rows are handed over in reverse order. If precedence came from
    evaluation order the verdict would name whichever ran first; it names the one the tuple puts
    first. A payload whose gate list happened to be sorted would prove nothing, which is why the
    input is reversed.
    """
    failing = {CONDITION_20_GATE, "retention"}
    census = DecisionCensusV4.from_feature_hashes(
        [_digest(f"s21d4:group:{index // 6}") for index in range(120)]
    )
    gates = tuple(
        condition_20_gate(
            outcome=PromotionGateOutcome.FAILED,
            evidence_hash=_digest(f"s21d4:gate:{name}"),
            detail="checkpoint fixture: a failed row still names its denominators",
            census=census,
            calibration_certificate_hash=_digest("s21d4:calibration-certificate"),
        )
        if name == CONDITION_20_GATE
        else _gate(
            name,
            PromotionGateOutcome.FAILED if name in failing else PromotionGateOutcome.PASSED,
        )
        for name in reversed(D3_PROMOTION_GATES)
    )
    payload = _fixture_payload(gates)
    evaluation = evaluate_d3_promotion(payload, bindings=_fixture_bindings())
    counts = payload.gate[CONDITION_20_GATE].decision_counts
    return {
        "rows_supplied_in": "reverse gate-tuple order",
        "unmet_gates": list(evaluation.unmet_gates),
        "first_failed_gate": evaluation.first_failed_gate,
        "names_the_gate_the_tuple_puts_first": evaluation.first_failed_gate
        == min(failing, key=D3_PROMOTION_GATES.index),
        "verdict": evaluation.verdict.value,
        "a_failed_row_still_carries_its_denominators": counts is not None
        and counts.independent_decisions == 20,
    }


def _condition_20_contract() -> dict[str, Any]:
    """S21D4-048, executed: what the row now requires, and what the requirement did not move."""
    unmeasured = tuple(
        _gate(name, PromotionGateOutcome.NOT_MEASURED) for name in D3_PROMOTION_GATES
    )
    without_counts = _fixture_payload(unmeasured)

    #: D3's own metamorphic set at the shape the erratum recomputed: 120 counted decisions over
    #: 20 distinct fitted vectors, six replicas each.
    census = DecisionCensusV4.from_feature_hashes(
        [_digest(f"s21d4:group:{index // 6}") for index in range(120)]
    )
    certificate = _digest("s21d4:calibration-certificate")
    measured = tuple(
        condition_20_gate(
            outcome=PromotionGateOutcome.PASSED,
            evidence_hash=_digest(f"s21d4:gate:{name}"),
            detail="checkpoint fixture: the erratum's counts, on no measurement",
            census=census,
            calibration_certificate_hash=certificate,
        )
        if name == CONDITION_20_GATE
        else _gate(name, PromotionGateOutcome.NOT_MEASURED)
        for name in D3_PROMOTION_GATES
    )
    with_counts = _fixture_payload(measured)

    #: The bytes a D3 producer would have written for the same payload: the same document with
    #: the key that did not exist then removed. Reconstructed rather than pinned, so this
    #: compares against D3's serialisation rather than against a digit someone regenerated.
    document = json.loads(without_counts.model_dump_json())
    document["gates"] = [
        {key: value for key, value in gate.items() if key != "decision_counts"}
        for gate in document["gates"]
    ]
    as_d3_wrote_it = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()

    return {
        "gate": CONDITION_20_GATE,
        "row_carries": [
            "nominal_decisions",
            "independent_decisions",
            "calibration_certificate_hash",
        ],
        "counts_come_from": "learning.correction_protocol.DecisionCensusV4",
        "the_errata_shape": {
            "nominal_decisions": census.nominal_decisions,
            "independent_decisions": census.independent_decisions,
            "replicated_decisions": census.replicated_decisions,
        },
        "a_measured_row_without_counts_is_refused": _refusal(
            lambda: _fixture_payload(
                tuple(
                    _gate(name, PromotionGateOutcome.PASSED)
                    if name == CONDITION_20_GATE
                    else _gate(name, PromotionGateOutcome.NOT_MEASURED)
                    for name in D3_PROMOTION_GATES
                )
            )
        ),
        "an_unmeasured_row_carrying_counts_is_refused": _refusal(
            lambda: _fixture_payload(
                tuple(
                    PromotionGateRecord(
                        name=item.name,
                        outcome=PromotionGateOutcome.NOT_MEASURED,
                        evidence_hash=item.evidence_hash,
                        detail=item.detail,
                        decision_counts=item.decision_counts,
                    )
                    if item.name == CONDITION_20_GATE
                    else item
                    for item in measured
                )
            )
        ),
        "not_measured_is_still_distinct_from_failed": True,
        "precedence": _precedence_proof(),
        "additive": {
            "a_payload_without_counts_reproduces_the_d3_bytes": canonical_payload_bytes(
                without_counts
            )
            == as_d3_wrote_it,
            "d3_byte_sha256": _digest(as_d3_wrote_it),
            "d4_byte_sha256": _digest(canonical_payload_bytes(without_counts)),
            "content_hash_without_counts": without_counts.content_hash,
            "content_hash_with_counts": with_counts.content_hash,
            "carrying_counts_is_a_different_identity": (
                without_counts.content_hash != with_counts.content_hash
            ),
            "canonical_form_omits_the_absent_key": "decision_counts"
            not in without_counts.canonical_json(exclude={"content_hash"}),
        },
        "dispatch": {
            "schema": D3_PROMOTION_SCHEMA,
            "schema_version": D3_PROMOTION_SCHEMA_VERSION,
            "d3_bytes_report_version": promotion_payload_version(as_d3_wrote_it),
            "legacy_schema": LEGACY_PROMOTION_SCHEMA,
            "legacy_bytes_report_version": promotion_payload_version(
                json.dumps({"schema_name": LEGACY_PROMOTION_SCHEMA}).encode()
            ),
            "legacy_version_is_unchanged": LEGACY_PROMOTION_SCHEMA_VERSION == 1,
        },
        "media_type": D3_PROMOTION_MEDIA_TYPE,
        "gates": list(D3_PROMOTION_GATES),
        "gate_count": len(D3_PROMOTION_GATES),
    }


# ---------------------------------------------- what S21D4-050 can be checked on without a fit


def _frozen_artifact_identity() -> dict[str, Any]:
    """S21D4-050's unchanged clause, recomputed. The binding half of the item is not opened."""
    contract = CorrectionFeatureContractV2()
    return {
        "schema": CORRECTION_ARTIFACT_SCHEMA_V2,
        "media_type": CORRECTION_ARTIFACT_MEDIA_TYPE,
        "feature_channels": len(FITTED_FEATURE_V2_ALLOWLIST),
        "feature_channels_unchanged": len(FITTED_FEATURE_V2_ALLOWLIST) == FROZEN_FEATURE_CHANNELS,
        "feature_contract_hash": contract.content_hash,
        "feature_contract_hash_unchanged": contract.content_hash == FROZEN_FEATURE_CONTRACT_HASH,
        "scalar_channels": len(FITTED_FEATURE_V2_SCALARS),
        "embedding_dimensions": contract.embedding_dimensions,
        "normaliser": contract.normalizer_version,
        "python_grammar": contract.python_grammar,
        "canonical_prefix_hex": contract.canonical_prefix_hex,
        "normaliser_and_grammar_unchanged": (
            contract.normalizer_version == FROZEN_NORMALISER
            and contract.python_grammar == FROZEN_GRAMMAR
        ),
        "selected_artifact_exists": False,
        "threshold_bound_into_the_artifact": False,
        "threshold_binding_not_opened_because": (
            "S21D4-039 derived no operating point at either volume, so there is no threshold, "
            "derivation rule instance, calibration split identity or certificate to bind"
        ),
    }


# ------------------------------------------------------------ S21D4-059: the checkpoint itself


def _preconditions() -> list[dict[str, Any]]:
    """Every S21D4-059 precondition against what W1 through W3 committed, in backlog order."""
    selection = _read(SELECTION)["selection"]
    continuation = _read(CONTINUATION)["decision"]
    retrieval = _read(RETRIEVAL_DECISION)

    def item(name: str, passed: bool, detail: str, evidence: Path) -> dict[str, Any]:
        return {
            "name": name,
            "passed": passed,
            "detail": detail,
            "evidence": evidence.name,
            "evidence_sha256": _digest(evidence.read_bytes()),
        }

    return [
        item(
            "S21D4-039 selected one candidate",
            selection["outcome"] != "null",
            f"{selection['outcome']}: {selection['stop_kind']} -- {selection['reading']}",
            SELECTION,
        ),
        item(
            "the continuation permits correction work",
            continuation["kind"] == "proceed",
            f"{continuation['kind']}: authorises W2 to author the corpus, and nothing past it",
            CONTINUATION,
        ),
        item(
            "S21D4-051 stored one artifact",
            False,
            "not opened: an artifact can only be fitted for a selected candidate",
            SELECTION,
        ),
        item(
            "S21D4-054 proved the selected-artifact vertical slice",
            False,
            "not opened: the slice runs the selected artifact, which does not exist",
            SELECTION,
        ),
        item(
            "S21D4-056 registered the artifact and entered SHADOW",
            False,
            "not opened: registration binds an artifact hash that was never produced",
            SELECTION,
        ),
        item(
            "the independent retrieval branch reached a result",
            retrieval["winning_arm"] is not None,
            (
                f"a result was reached and it is negative: first failed floor "
                f"{retrieval['first_failed_floor']}, winning_arm null"
            ),
            RETRIEVAL_DECISION,
        ),
    ]


def _checkpoint(recorded_at: str) -> dict[str, Any]:
    preconditions = _preconditions()
    failed = [item for item in preconditions if not item["passed"]]
    first = failed[0] if failed else None
    stop_hash = _read(SELECTION)["integrity_content_hash"]
    stop_source = "S21D4-039 candidate selection"

    return {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W4",
        "items": ["S21D4-048", *(item for item, _ in DEPENDENT_ITEMS[:9]), "S21D4-059"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "final_or_canary_outcomes_inspected": 0,
        "opened_any_store": False,
        "created_any_lifecycle_state": False,
        "promotion_contract": _condition_20_contract(),
        "artifact_contract": _frozen_artifact_identity(),
        "configurations_sealed": 0,
        "configurations_sealed_reason": (
            "sealing happens at authorised final access; access was not authorised, and "
            "S21D4-070 is the item that would have sealed them"
        ),
        "preconditions": preconditions,
        "decision": {
            "authorised": False,
            "first_failed_precondition": None if first is None else first["name"],
            "reason": None if first is None else first["detail"],
            "stop_hash": stop_hash,
            "stop_source": stop_source,
            "capability_granted": None,
            "opens_no_parametric_rung": True,
            "reading": (
                "the sixth precondition is read as D3 read it -- a result that names a winning "
                "arm. The retrieval branch did reach a hash-bound result and it is negative, "
                "which the detail says rather than leaving the word 'result' to carry it. The "
                "decision does not turn on the reading: the first failure is the first "
                "precondition"
            ),
        },
        "not_opened": [
            {
                "item": item_id,
                "would_have": description,
                "status": "not_opened",
                "stop_hash": stop_hash,
                "stop_source": stop_source,
            }
            for item_id, description in DEPENDENT_ITEMS
        ],
        "unconditional": [
            {"item": item_id, "runs": description, "status": "open"}
            for item_id, description in UNCONDITIONAL_ITEMS
        ],
        "independent_branch": {
            "item": "S21D4-040 through S21D4-047",
            "status": "completed",
            "note": (
                "the retrieval branch reached its own hash-bound negative result in W3 and is "
                "bound to its own stop, not to this one"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    recorded_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    checkpoint = _checkpoint(recorded_at)
    seal = _write(arguments.output, checkpoint)

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    for item in checkpoint["preconditions"]:
        print(f"  {'pass' if item['passed'] else 'FAIL'}  {item['name']}")
    print(f"  authorised={checkpoint['decision']['authorised']}")
    print(f"  stop {checkpoint['decision']['stop_hash']} ({checkpoint['decision']['stop_source']})")
    print(f"  not opened: {len(checkpoint['not_opened'])} items")
    additive = checkpoint["promotion_contract"]["additive"]
    print(
        f"  condition 20 additive: {additive['a_payload_without_counts_reproduces_the_d3_bytes']}"
    )
    print(f"  seal {seal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
