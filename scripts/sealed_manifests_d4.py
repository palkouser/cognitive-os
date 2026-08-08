#!/usr/bin/env python3
"""S21D4-032: seal every D4 campaign and holdout manifest, before any outcome exists.

The seal is the point at which the corpus stops being editable and starts being spent. Three
things have to be true when it is written, and all three are checked here rather than asserted:

*No outcome exists yet.* A seal written after a result is a description of that result.

*The carried roles are the released ones.* Final A, final B and canary were audited at
S21D4-004 and recorded `reuse`, so their hashes are compared against the bytes
sprint-21d3-sealed-manifests.json published. A re-derivation would produce the same number and
would hide a drift; a comparison against the released file cannot.

*Corpus authoring is closed.* The capability that wrote the hundred groups has no business
outliving them, and the seal records its revocation rather than leaving it to a convention.

    UV_CACHE_DIR=.cache/uv uv run python scripts/sealed_manifests_d4.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import (  # noqa: E402
    CARRIED_ROLES,
    D4_CALIBRATION_SEED,
    D4_CASES,
    D4_FITTING_SEED,
    INVARIANCE_SAMPLE_GROUPS,
    INVARIANCE_TRANSFORM_SEED,
    PROMOTION_TRANSFORM_SEED,
    eligible_calibration_groups,
    invariance_sample_groups,
    seal_d4_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
D3_SEALED = EVIDENCE / "sprint-21d3-sealed-manifests.json"
SEPARATION = EVIDENCE / "sprint-21d4-separation.json"
CORPUS = EVIDENCE / "sprint-21d4-corpus.json"


def _sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    """The D4 convention: the bytes hashed are the bytes written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write(path: Path, body: dict[str, Any]) -> str:
    sealed = dict(body)
    sealed["integrity_content_hash"] = _sha256(_canonical(body))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(sealed) + b"\n")
    return _sha256(path.read_bytes())


def _carried_role_proof(bundle: Any) -> dict[str, Any]:
    """Compare the three carried hashes against the bytes D3 released, role by role."""
    released = json.loads(D3_SEALED.read_text())["catalogues"]
    rows = {}
    for partition in CARRIED_ROLES:
        carried = bundle.catalogues[partition].content_hash
        rows[partition.value] = {
            "d4_catalogue_hash": carried,
            "d3_released_hash": released[partition.value]["content_hash"],
            "identical": carried == released[partition.value]["content_hash"],
            "obtained_by": "seal_d3_corpus(), carried; not re-derived from the specs",
            "s21d4_004_decision": "reuse",
        }
    return {
        "roles": rows,
        "all_identical": all(row["identical"] for row in rows.values()),
        "d3_evidence": D3_SEALED.name,
        "d3_evidence_sha256": _sha256(D3_SEALED.read_bytes()),
        "d3_seal_hash": bundle.d3_seal_hash,
        "why_not_re_derived": (
            "a re-derivation from the same specs would produce the same number whether or not "
            "the released catalogue had moved underneath it, so it could not tell reuse from "
            "coincidence"
        ),
    }


def _manifest_rows(bundle: Any) -> dict[str, Any]:
    catalogues = bundle.catalogues
    rows = {
        partition.value: {
            "content_hash": catalogue.content_hash,
            "groups": len(catalogue.groups),
            "candidate_slots": catalogue.candidate_slots,
            "campaign_seed": catalogue.campaign_seed,
            "generator_path": catalogue.generator_path,
            "corpus_role": str(catalogue.corpus_role),
            "provenance": str(catalogue.provenance),
            "outcomes_present": catalogue.outcomes_present,
        }
        for partition, catalogue in catalogues.items()
    }
    rows["retrieval"] = {
        "content_hash": bundle.retrieval_pool.content_hash,
        "groups": len(bundle.retrieval_pool.groups),
        "minimum_source_groups": bundle.retrieval_pool.minimum_source_groups,
        "minimum_qualifying_queries": bundle.retrieval_pool.minimum_qualifying_queries,
        "queries_resolved": bundle.retrieval_pool.queries_resolved,
    }
    return rows


def _submanifest_rows(bundle: Any) -> dict[str, Any]:
    invariance = bundle.invariance_transformations
    promotion = bundle.promotion_transformations
    return {
        "calibration_invariance": {
            "content_hash": invariance.content_hash,
            "source_manifest_hash": invariance.source_manifest_hash,
            "generator_code_hash": invariance.generator_code_hash,
            "hard_coded_oracle_hash": invariance.hard_coded_oracle_hash,
            "cases": D4_CASES,
            "sample_groups": INVARIANCE_SAMPLE_GROUPS,
            "transformed_decisions": len(invariance.cases),
            "independent_decisions": 0,
            "seed": INVARIANCE_TRANSFORM_SEED,
            "why_zero_independent": (
                "a transformation of a group repeats that group's fitted feature vector, so it "
                "repeats a decision; the transformed set is a regression test and never an "
                "accuracy sample"
            ),
            "sample_selection_rule": (
                "the first twenty groups of the family-interleaved calibration manifest, so the "
                "choice can be checked against the sealed catalogue afterwards"
            ),
            "sample_groups_named": list(
                invariance_sample_groups(bundle.catalogues[CorrectionPartition.CALIBRATION])
            ),
        },
        "promotion": {
            "content_hash": promotion.content_hash,
            "source_manifest_hash": promotion.source_manifest_hash,
            "generator_code_hash": promotion.generator_code_hash,
            "hard_coded_oracle_hash": promotion.hard_coded_oracle_hash,
            "cases": D4_CASES,
            "groups": 60,
            "nominal_decisions": len(promotion.cases),
            "independent_decisions": len(promotion.cases) // len(D4_CASES),
            "reported_side_by_side": True,
            "seed": PROMOTION_TRANSFORM_SEED,
        },
    }


def _evidence(recorded_at: str) -> tuple[dict[str, Any], list[str]]:
    bundle = seal_d4_corpus()
    seal = bundle.seal
    carried = _carried_role_proof(bundle)

    groups = {
        partition.value: sorted(bundle.groups_of(partition)) for partition in bundle.catalogues
    }
    groups["retrieval"] = sorted(bundle.retrieval_groups)
    names = sorted(groups)
    crossings = {}
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            crossings[f"{left}|{right}"] = sorted(set(groups[left]) & set(groups[right]))

    eligible = eligible_calibration_groups()

    body = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W2",
        "items": ["S21D4-032"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Seal the fitting, calibration, final A, final B, canary and retrieval manifests "
            "before any outcome exists, carrying the three roles S21D4-004 recorded as reuse "
            "rather than re-deriving them, and close the corpus-authoring capability."
        ),
        "bound_evidence": {
            "corpus": {"file": CORPUS.name, "sha256": _sha256(CORPUS.read_bytes())},
            "separation": {"file": SEPARATION.name, "sha256": _sha256(SEPARATION.read_bytes())},
        },
        "catalogues": _manifest_rows(bundle),
        "transformation_submanifests": _submanifest_rows(bundle),
        "carried_roles": carried,
        "role_disjointness": {
            "pairs_sharing_a_group": {name: len(shared) for name, shared in crossings.items()},
            "all_pairwise_disjoint": not any(crossings.values()),
        },
        "seeds": {
            "fitting": D4_FITTING_SEED,
            "calibration": D4_CALIBRATION_SEED,
            "invariance": INVARIANCE_TRANSFORM_SEED,
            "promotion": PROMOTION_TRANSFORM_SEED,
            "distinct_from_every_predecessor_seed": True,
        },
        "eligibility": {
            "rule": "both D4 cases apply: the rename map exists and the issue rewrite lands",
            "eligible_calibration_groups": len(eligible),
            "calibration_groups": seal.calibration_groups,
            "ineligible": sorted(
                {spec.template_id for spec in D4_CALIBRATION_SPECS} - set(eligible)
            ),
        },
        "seal": {
            "content_hash": seal.content_hash,
            "revision": seal.revision,
            "fitting_catalogue_hash": seal.fitting_catalogue_hash,
            "calibration_catalogue_hash": seal.calibration_catalogue_hash,
            "final_a_catalogue_hash": seal.final_a_catalogue_hash,
            "final_b_catalogue_hash": seal.final_b_catalogue_hash,
            "canary_catalogue_hash": seal.canary_catalogue_hash,
            "invariance_submanifest_hash": seal.invariance_submanifest_hash,
            "promotion_submanifest_hash": seal.promotion_submanifest_hash,
            "retrieval_pool_hash": seal.retrieval_pool_hash,
            "candidate_slots": seal.candidate_slots,
            "outcomes_present": seal.outcomes_present,
            "corpus_authoring_capability_revoked": seal.corpus_authoring_capability_revoked,
        },
        "capability_revocation": {
            "capability": "isolated_corpus_authoring_validator",
            "revoked": True,
            "when": "at this seal, before any D4 outcome exists",
            "why": (
                "the capability that wrote the hundred groups has no business outliving them; "
                "an authoring validator still open once outcomes exist is a channel from a role "
                "into the corpus that describes it"
            ),
        },
    }

    stops: list[str] = []
    if not carried["all_identical"]:
        stops.append("sealed_manifests_carried_role_drift")
    if not body["role_disjointness"]["all_pairwise_disjoint"]:
        stops.append("sealed_manifests_role_crossing")
    if seal.outcomes_present:
        stops.append("sealed_manifests_outcome_present")
    if not seal.corpus_authoring_capability_revoked:
        stops.append("sealed_manifests_capability_open")
    if seal.invariance_independent_decisions != 0:
        stops.append("sealed_manifests_replica_counted_as_independent")
    if len(eligible) < INVARIANCE_SAMPLE_GROUPS:
        stops.append("sealed_manifests_too_few_eligible_groups")
    return body, stops


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE)
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    arguments = parser.parse_args()

    recorded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body, stops = _evidence(recorded_at)

    if arguments.check:
        print(json.dumps({"stops": stops}, indent=1))
        return 1 if stops else 0

    path = arguments.output_root / "sprint-21d4-sealed-manifests.json"
    written = _write(path, body)

    print(f"{path.name}  {written}")
    for name, row in body["catalogues"].items():
        print(f"  {name:12} {row['groups']:4} groups  {row['content_hash'][:16]}")
    invariance = body["transformation_submanifests"]["calibration_invariance"]
    promotion = body["transformation_submanifests"]["promotion"]
    print(
        f"  invariance   {invariance['transformed_decisions']} transformed / "
        f"{invariance['independent_decisions']} independent"
    )
    print(
        f"  promotion    {promotion['nominal_decisions']} nominal / "
        f"{promotion['independent_decisions']} independent"
    )
    print(f"  carried roles identical to D3: {body['carried_roles']['all_identical']}")
    print(f"  seal: {body['seal']['content_hash']}")
    if stops:
        print("STOPS: " + ", ".join(stops))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
