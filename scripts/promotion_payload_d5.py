#!/usr/bin/env python3
"""S21D5-037. Condition 20 names its hypothesis class, and four payload shapes still read.

D4 made the metamorphic/OOD row carry two denominators and the certificate its answered set was
decided under. That says how many decisions were counted and which threshold answered them, and
not *what* was thresholded. A k-NN neighbourhood's acceptance mass and a projection margin are
different quantities, and after D5 both are things a stored payload could be about.

So the row names the class, and this record measures the three properties that makes true:

1. a class no loader implements is refused where the row is built, not at activation;
2. the D3, D4 and legacy shapes still dispatch on their schema name and reload to their
   recorded identity, byte for byte;
3. a row that names the class is new bytes and a new identity, because absent must never be a
   synonym for present-and-hidden.

Nothing is promoted here. No payload is stored, no gate is evaluated, and there is no candidate
to promote — S21D5-035 selected none. This item depends on S21D5-016, not on a selection: it is
the contract the successor sprint inherits, and a contract with nothing to carry yet is still
the contract.

    UV_CACHE_DIR=.cache/uv uv run python scripts/promotion_payload_d5.py
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.benchmarks.learned_fixtures import (  # noqa: E402
    promotion_payload_v2,
)
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.experience import CANONICAL_ABSENT_WHEN_EMPTY  # noqa: E402
from cognitive_os.domain.promotion_payload import (  # noqa: E402
    CONDITION_20_GATE,
    D3_PROMOTION_SCHEMA,
    D3_PROMOTION_SCHEMA_VERSION,
    LEGACY_PROMOTION_SCHEMA,
    LEGACY_PROMOTION_SCHEMA_VERSION,
    D3PromotionPayload,
    PromotionGateOutcome,
    PromotionPayloadError,
    canonical_payload_bytes,
    load_promotion_payload,
    promotion_payload_version,
)
from cognitive_os.learning.correction_artifact import (  # noqa: E402
    IMPLEMENTED_HYPOTHESIS_CLASSES,
)
from cognitive_os.learning.correction_protocol import DecisionCensusV4  # noqa: E402
from cognitive_os.learning.pairwise_contrastive import HYPOTHESIS_CLASS  # noqa: E402
from cognitive_os.learning.promotion import condition_20_gate  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
ARTIFACT_V3 = EVIDENCE / "sprint-21d5-artifact-v3.json"
SCHEMA = REPOSITORY / "schemas/v1/learned/d3-promotion-payload.schema.json"
MANIFEST = REPOSITORY / "schemas/manifest.json"
OUTPUT = EVIDENCE / "sprint-21d5-promotion-payload.json"

CERTIFICATE = sha256(b"s21d5:promotion-payload-record:certificate").hexdigest()

#: The D5 promotion role's shape: 60 final groups, two cases each, 120 nominal decisions over 60
#: distinct fitted vectors. Fixture hashes — this record measures the shape, not an outcome.
PROMOTION_FEATURE_HASHES = [
    sha256(f"s21d5:promotion:group-{index // 2}".encode()).hexdigest() for index in range(120)
]


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _schema_hash(model: type) -> str:
    return sha256(
        json.dumps(model.model_json_schema(), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _payload_with(gate: Any) -> D3PromotionPayload:
    released = promotion_payload_v2()
    return D3PromotionPayload(
        **{
            **{
                key: value
                for key, value in released
                if key not in {"content_hash", "gates", "schema_name", "schema_version"}
            },
            "gates": tuple(
                gate if item.name == CONDITION_20_GATE else item for item in released.gates
            ),
        }
    )


def _row(hypothesis_class: str | None) -> Any:
    return condition_20_gate(
        outcome=PromotionGateOutcome.PASSED,
        evidence_hash=_digest("s21d5:promotion-metamorphic-ood"),
        detail="120 nominal decisions over 60 distinct fitted vectors",
        census=DecisionCensusV4.from_feature_hashes(PROMOTION_FEATURE_HASHES),
        calibration_certificate_hash=CERTIFICATE,
        hypothesis_class=hypothesis_class,
    )


def _without_the_class(payload: D3PromotionPayload) -> bytes:
    """The exact bytes a D4 producer would have written for this payload.

    Reconstructed by deleting the key rather than by pinning a digest: a pinned digest proves
    the bytes did not change since someone last regenerated it, which is a different claim.
    """
    document = json.loads(payload.model_dump_json(exclude_none=True))
    for row in document["gates"]:
        if row.get("decision_counts") is not None:
            row["decision_counts"].pop("hypothesis_class", None)
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _refusals() -> list[dict[str, Any]]:
    """Each refusal exercised rather than described."""
    cases: list[tuple[str, Any]] = [
        ("a class no loader implements", lambda: _row("graph-neural-ranker-v1")),
        ("an empty class name", lambda: _row("")),
        (
            "a census on a row nobody measured",
            lambda: condition_20_gate(
                outcome=PromotionGateOutcome.NOT_MEASURED,
                evidence_hash=_digest("unmeasured"),
                detail="nobody ran it",
                census=DecisionCensusV4.from_feature_hashes(PROMOTION_FEATURE_HASHES),
                calibration_certificate_hash=CERTIFICATE,
                hypothesis_class=HYPOTHESIS_CLASS,
            ),
        ),
        (
            "bytes declaring a schema nobody publishes",
            lambda: promotion_payload_version(b'{"schema_name":"d9-promotion-payload"}'),
        ),
        ("bytes that are not JSON", lambda: promotion_payload_version(b"not json")),
        (
            "legacy bytes read through the D3 loader",
            lambda: load_promotion_payload(
                json.dumps({"schema_name": LEGACY_PROMOTION_SCHEMA}).encode()
            ),
        ),
    ]
    results: list[dict[str, Any]] = []
    for name, call in cases:
        try:
            call()
        except (ValueError, PromotionPayloadError) as error:
            results.append({"case": name, "refused": True, "error": str(error)[:200]})
        else:
            results.append({"case": name, "refused": False, "error": None})
    return results


def _run(output: Path) -> int:
    released = promotion_payload_v2()
    d4_shaped = _payload_with(_row(None))
    d5_shaped = _payload_with(_row(HYPOTHESIS_CLASS))

    d4_bytes = canonical_payload_bytes(d4_shaped)
    d5_bytes = canonical_payload_bytes(d5_shaped)
    reconstructed = _without_the_class(d4_shaped)
    d4_reloaded = load_promotion_payload(d4_bytes)
    d5_reloaded = load_promotion_payload(d5_bytes)

    refusals = _refusals()
    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-037"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
            "contracts_sha256": _digest(CONTRACTS.read_bytes()),
            "artifact_v3_sha256": _digest(ARTIFACT_V3.read_bytes()),
            "final_outcomes_inspected": False,
            "payloads_stored": 0,
            "gates_evaluated": 0,
            "candidate_promoted": None,
            "schema": {
                "name": D3_PROMOTION_SCHEMA,
                "version": D3_PROMOTION_SCHEMA_VERSION,
                "version_moved": False,
                "model_schema_hash": _schema_hash(D3PromotionPayload),
                "published_file_sha256": _digest(SCHEMA.read_bytes()),
                "manifest_sha256": _digest(MANIFEST.read_bytes()),
                "why_the_version_does_not_move": (
                    "bumping the name or the version would make every D3 and D4 payload "
                    "unreadable through load_promotion_payload, which is the opposite of what "
                    "this item asks for. The field is additive and optional; the dispatch is "
                    "unchanged"
                ),
            },
            "condition_20_row": {
                "gate": CONDITION_20_GATE,
                "carries": [
                    "nominal_decisions",
                    "independent_decisions",
                    "calibration_certificate_hash",
                    "hypothesis_class",
                ],
                "nominal_decisions": d5_reloaded.gate[
                    CONDITION_20_GATE
                ].decision_counts.nominal_decisions,  # type: ignore[union-attr]
                "independent_decisions": d5_reloaded.gate[
                    CONDITION_20_GATE
                ].decision_counts.independent_decisions,  # type: ignore[union-attr]
                "hypothesis_class": HYPOTHESIS_CLASS,
                "implemented_classes": sorted(IMPLEMENTED_HYPOTHESIS_CLASSES),
                "counts_come_from": (
                    "DecisionCensusV4, the one place the independence rule is implemented; a "
                    "builder taking two integers would let a replicated set through wearing a "
                    "different field name"
                ),
                "class_checked_against": (
                    "the classes the artifact loader implements, so a class nobody can load is "
                    "refused where the row is built rather than at activation, where the bytes "
                    "would already be stored"
                ),
            },
            "additive": {
                "canonical_absent_when_empty": list(CANONICAL_ABSENT_WHEN_EMPTY),
                "released_benchmark_payload_hash": released.content_hash,
                "released_benchmark_bytes_sha256": _digest(canonical_payload_bytes(released)),
                "a_d4_shaped_payload_hashes_as_it_did": d4_bytes == reconstructed,
                "d4_shaped_bytes_sha256": _digest(d4_bytes),
                "reconstructed_without_the_key_sha256": _digest(reconstructed),
                "naming_the_class_is_new_bytes": d5_bytes != d4_bytes,
                "naming_the_class_is_a_new_identity": (
                    d5_shaped.content_hash != d4_shaped.content_hash
                ),
                "how_the_identity_is_kept_stable": (
                    "canonical_payload_bytes excludes nulls, which keeps the stored bytes "
                    "stable and does nothing for canonical_json, which is what the contract "
                    "hashes. hypothesis_class is named in CANONICAL_ABSENT_WHEN_EMPTY for the "
                    "second half. The D5 test that measures this is what found the difference"
                ),
            },
            "dispatch": [
                {
                    "shape": "legacy v1 assessment",
                    "schema_name": LEGACY_PROMOTION_SCHEMA,
                    "version_reported": promotion_payload_version(
                        json.dumps({"schema_name": LEGACY_PROMOTION_SCHEMA}).encode()
                    ),
                    "expected": LEGACY_PROMOTION_SCHEMA_VERSION,
                },
                {
                    "shape": "D3/D4 payload with no hypothesis class",
                    "schema_name": D3_PROMOTION_SCHEMA,
                    "version_reported": promotion_payload_version(d4_bytes),
                    "expected": D3_PROMOTION_SCHEMA_VERSION,
                    "reloads_to_its_recorded_identity": (
                        d4_reloaded.content_hash == d4_shaped.content_hash
                    ),
                    "hypothesis_class_after_reload": (
                        d4_reloaded.gate[CONDITION_20_GATE].decision_counts.hypothesis_class  # type: ignore[union-attr]
                    ),
                },
                {
                    "shape": "D5 payload naming the class",
                    "schema_name": D3_PROMOTION_SCHEMA,
                    "version_reported": promotion_payload_version(d5_bytes),
                    "expected": D3_PROMOTION_SCHEMA_VERSION,
                    "reloads_to_its_recorded_identity": (
                        d5_reloaded.content_hash == d5_shaped.content_hash
                    ),
                    "hypothesis_class_after_reload": (
                        d5_reloaded.gate[CONDITION_20_GATE].decision_counts.hypothesis_class  # type: ignore[union-attr]
                    ),
                },
            ],
            "refusals": refusals,
            "every_refusal_refused": all(bool(item["refused"]) for item in refusals),
            "not_a_refusal_and_deliberately_so": {
                "case": "a JSON object carrying no schema_name at all",
                "version_reported": promotion_payload_version(b'{"a":1}'),
                "why": (
                    "the legacy shape predates the field, so an object without one is read as "
                    "version 1 rather than rejected. That is released behaviour and the reason "
                    "the D3 loader refuses it a step later, by version, instead of here"
                ),
            },
            "what_this_does_not_claim": (
                "no D5 promotion payload exists. S21D5-035 selected no candidate, so there is "
                "nothing to promote and S21D5-067, which would build the real payload, stays "
                "closed. This is the shape a successor writes into, measured now because it "
                "depends on the pre-registration rather than on a result"
            ),
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "schema_version_moved": evidence["schema"]["version_moved"],
                "model_schema_hash": evidence["schema"]["model_schema_hash"],
                "a_d4_shaped_payload_hashes_as_it_did": evidence["additive"][
                    "a_d4_shaped_payload_hashes_as_it_did"
                ],
                "naming_the_class_is_a_new_identity": evidence["additive"][
                    "naming_the_class_is_a_new_identity"
                ],
                "shapes_dispatched": len(evidence["dispatch"]),
                "every_refusal_refused": evidence["every_refusal_refused"],
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    ok = (
        bool(evidence["additive"]["a_d4_shaped_payload_hashes_as_it_did"])
        and bool(evidence["additive"]["naming_the_class_is_a_new_identity"])
        and bool(evidence["every_refusal_refused"])
        and all(item["version_reported"] == item["expected"] for item in evidence["dispatch"])
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _run(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
