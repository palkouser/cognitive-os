#!/usr/bin/env python3
"""S21D5-023: seal every D5 campaign and holdout manifest, before any outcome exists.

The seal is the point at which the corpus stops being editable and starts being spent. D5 has
five things to show when it writes one, and each is checked here rather than asserted.

*No outcome exists yet.* A seal written after a result is a description of that result.

*The three protected roles are the released ones.* Final A, final B and canary were audited at
S21D5-003/004 and recorded `reuse`, so their hashes are compared against the bytes
sprint-21d4-sealed-manifests.json published. A re-derivation would produce the same number and
would hide a drift; a comparison against the released file cannot.

*The fitting pool is D4's two partitions and has not drifted either.* This one is D5's own
problem. W0 digested the 180-group pool **by group name**, which proves the membership and says
nothing about the bodies -- and the bodies are the whole point, because these groups are being
re-executed. So the pool is proved twice: the name digest against W0's record, and D4's fitting
and calibration catalogue hashes against the released D4 bytes. The second is what would catch
a body edited under an unchanged name.

*The fresh roles are the ones S21D5-022 proved separated.* The separation record is bound by
hash rather than cited, so a seal cannot claim a separation that a later edit invalidated.

*Corpus authoring is closed.* The capability that wrote the hundred calibration and sixty
retrieval groups has no business outliving them, and the seal records its revocation rather
than leaving it to a convention.

    UV_CACHE_DIR=.cache/uv uv run python scripts/sealed_manifests_d5.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/sealed_manifests_d5.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_catalogue import CANDIDATES_PER_GROUP  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d5 import (  # noqa: E402
    CARRIED_ROLES,
    D5_CALIBRATION_SEED,
    D5_CASES,
    D5_FITTING_SEED,
    D5_VOLUME_POINTS,
    INVARIANCE_SAMPLE_GROUPS,
    INVARIANCE_TRANSFORM_SEED,
    PROMOTION_TRANSFORM_SEED,
    D5CorpusBundle,
    d5_invariance_sample_groups,
    eligible_calibration_groups,
    seal_d5_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
D4_SEALED = EVIDENCE / "sprint-21d4-sealed-manifests.json"
SEPARATION = EVIDENCE / "sprint-21d5-corpus-separation.json"
REUSE_AUDIT = EVIDENCE / "sprint-21d5-reuse-audit.json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    """The D4 convention, unchanged: the bytes hashed are the bytes written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _write(path: Path, body: dict[str, Any]) -> str:
    sealed = dict(body)
    sealed["integrity_content_hash"] = _sha256(_canonical(body))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(sealed) + b"\n")
    return _sha256(path.read_bytes())


def _protected_role_proof(bundle: D5CorpusBundle) -> dict[str, Any]:
    """Compare the three carried hashes against the bytes D4 released, role by role."""
    released = json.loads(D4_SEALED.read_text())["catalogues"]
    rows = {}
    for partition in CARRIED_ROLES:
        carried = bundle.catalogues[partition].content_hash
        rows[partition.value] = {
            "d5_catalogue_hash": carried,
            "d4_released_hash": released[partition.value]["content_hash"],
            "identical": carried == released[partition.value]["content_hash"],
            "obtained_by": "seal_d4_corpus(), carried; not re-derived from the specs",
            "s21d5_004_decision": "reuse",
            "carried_for": "the third sprint running: D2 authored them, D3 and D4 carried them",
        }
    return {
        "roles": rows,
        "all_identical": all(row["identical"] for row in rows.values()),
        "d4_evidence": D4_SEALED.name,
        "d4_evidence_sha256": _sha256(D4_SEALED.read_bytes()),
        "d4_seal_hash": bundle.d4_seal_hash,
        "why_not_re_derived": (
            "a re-derivation from the same specs would produce the same number whether or not "
            "the released catalogue had moved underneath it, so it could not tell reuse from "
            "coincidence"
        ),
    }


def _fitting_pool_proof(bundle: D5CorpusBundle) -> dict[str, Any]:
    """The 180 spent groups, proved by membership against W0 and by body against D4.

    Two proofs because W0's digest can only carry one of them. `names_digest` in the reuse audit
    is a sha256 over the sorted group names: it fixes *which* 180 groups the pool is and cannot
    see a body edited under an unchanged name. The bodies are proved separately, by comparing
    D4's own two catalogue hashes against the released D4 evidence -- those catalogues are where
    every fitting body in D5 comes from.
    """
    audit = json.loads(REUSE_AUDIT.read_text())["role_transition"]["fitting_pool"]
    released = json.loads(D4_SEALED.read_text())["catalogues"]
    names = sorted(bundle.groups_of(CorrectionPartition.TRAINING))
    digest = _sha256("\n".join(names).encode("utf-8"))
    d4 = seal_d4_corpus()
    bodies = {
        source: {
            "d4_catalogue_hash": d4.catalogues[partition].content_hash,
            "d4_released_hash": released[released_key]["content_hash"],
            "identical": d4.catalogues[partition].content_hash
            == released[released_key]["content_hash"],
        }
        for source, partition, released_key in (
            ("d4_fitting", CorrectionPartition.TRAINING, "training"),
            ("d4_calibration", CorrectionPartition.CALIBRATION, "calibration"),
        )
    }
    return {
        "groups": len(names),
        "composition": audit["composition"],
        "authority": (
            "sprint-21d5-handoff.md section 2: a group that decided a D4 threshold is spent as a "
            "calibration sample and untouched as a task package, so it stays valid fitting and "
            "diagnostic evidence"
        ),
        "membership": {
            "names_digest": digest,
            "w0_names_digest": audit["names_digest"],
            "identical": digest == audit["names_digest"],
            "proves": "which 180 groups the pool is",
            "cannot_prove": "that a body has not drifted under an unchanged group name",
        },
        "bodies": {
            "sources": bodies,
            "all_identical": all(row["identical"] for row in bodies.values()),
            "proves": (
                "every fitting body in D5 is the byte the released D4 catalogues hold, which is "
                "the half of the claim the name digest cannot reach"
            ),
        },
        "re_executed_not_inherited": {
            "d5_fitting_seed": D5_FITTING_SEED,
            "distinct_from_every_predecessor_seed": True,
            "reading": (
                "the seed reaches candidate identity, so the 180 groups carry D5 candidate ids "
                "and are re-executed under new run identities rather than read from a store"
            ),
        },
        "outcomes": len(names) * CANDIDATES_PER_GROUP,
    }


def _volume_proof(bundle: D5CorpusBundle) -> dict[str, Any]:
    """S21D5-011's ladder, and the arithmetic that keeps a point off the inside of a group."""
    return {
        "points": list(D5_VOLUME_POINTS),
        "points_in_groups": [point // CANDIDATES_PER_GROUP for point in D5_VOLUME_POINTS],
        "every_point_lands_on_a_whole_group": all(
            point % CANDIDATES_PER_GROUP == 0 for point in D5_VOLUME_POINTS
        ),
        "top_point_is_the_whole_pool": (
            D5_VOLUME_POINTS[-1] == bundle.seal.fitting_groups * CANDIDATES_PER_GROUP
        ),
        "span": "2.25x",
        "why_whole_groups": (
            "fitting on three of a group's four candidates puts the fourth's siblings in the "
            "exemplar set, and the difference that produces is not a volume effect"
        ),
        "against_d4": (
            "S21D4-039 recorded its 200-to-320 span as a limitation on its own volume arm; this "
            "ladder is the repair and it costs no authoring, because the pool already exists"
        ),
    }


def _manifest_rows(bundle: D5CorpusBundle) -> dict[str, Any]:
    rows: dict[str, Any] = {
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
        for partition, catalogue in bundle.catalogues.items()
    }
    rows["retrieval"] = {
        "content_hash": bundle.retrieval_pool.content_hash,
        "groups": len(bundle.retrieval_pool.groups),
        "minimum_source_groups": bundle.retrieval_pool.minimum_source_groups,
        "minimum_qualifying_queries": bundle.retrieval_pool.minimum_qualifying_queries,
        "queries_resolved": bundle.retrieval_pool.queries_resolved,
    }
    return rows


def _submanifest_rows(bundle: D5CorpusBundle) -> dict[str, Any]:
    invariance = bundle.invariance_transformations
    promotion = bundle.promotion_transformations
    return {
        "calibration_invariance": {
            "content_hash": invariance.content_hash,
            "source_manifest_hash": invariance.source_manifest_hash,
            "generator_code_hash": invariance.generator_code_hash,
            "hard_coded_oracle_hash": invariance.hard_coded_oracle_hash,
            "cases": D5_CASES,
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
            "sample_groups_named": list(d5_invariance_sample_groups()),
        },
        "promotion": {
            "content_hash": promotion.content_hash,
            "source_manifest_hash": promotion.source_manifest_hash,
            "generator_code_hash": promotion.generator_code_hash,
            "hard_coded_oracle_hash": promotion.hard_coded_oracle_hash,
            "cases": D5_CASES,
            "groups": 60,
            "nominal_decisions": len(promotion.cases),
            "independent_decisions": len(promotion.cases) // len(D5_CASES),
            "reported_side_by_side": True,
            "seed": PROMOTION_TRANSFORM_SEED,
            "distinct_from_the_d4_promotion_set_by_seed": (
                "D4 and D5 transform the same sixty final groups under the same two released "
                "cases, so the seed is the only thing separating their case identities; it is "
                "D5's own and the two sets share no case id"
            ),
        },
    }


def _spent_pool_proof(bundle: D5CorpusBundle) -> dict[str, Any]:
    """D4's retrieval pool was read once and is spent. D5's is the fresh sixty."""
    d4 = seal_d4_corpus()
    return {
        "d5_pool_hash": bundle.retrieval_pool.content_hash,
        "d4_spent_pool_hash": d4.retrieval_pool.content_hash,
        "distinct": bundle.retrieval_pool.content_hash != d4.retrieval_pool.content_hash,
        "groups_shared": sorted(bundle.retrieval_groups & d4.retrieval_groups),
        "d5_role_of_the_d4_pool": "none",
        "why": (
            "a pool read once has had its queries answered; measuring retrieval against it again "
            "measures recall of a seen answer"
        ),
    }


def _evidence(recorded_at: str) -> tuple[dict[str, Any], list[str]]:
    bundle = seal_d5_corpus()
    seal = bundle.seal
    protected = _protected_role_proof(bundle)
    fitting = _fitting_pool_proof(bundle)
    volume = _volume_proof(bundle)
    spent = _spent_pool_proof(bundle)

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
    # The sample names repository groups and eligibility names template ids, so one of the two
    # has to be translated before they can be subtracted. Comparing them raw would report every
    # sampled group as ineligible and read like a corpus defect.
    template_of = {spec.repository_group: spec.template_id for spec in D5_CALIBRATION_SPECS}
    ineligible_in_sample = sorted(
        group for group in d5_invariance_sample_groups() if template_of[group] not in set(eligible)
    )

    body = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W1",
        "items": ["S21D5-023"],
        "recorded_at": recorded_at,
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Seal the fitting, calibration, final A, final B, canary and retrieval manifests "
            "before any outcome exists: carrying the three protected roles S21D5-004 recorded as "
            "reuse rather than re-deriving them, proving the 180-group fitting pool both by "
            "membership and by body, and closing the corpus-authoring capability."
        ),
        "bound_evidence": {
            "contracts": {
                "file": CONTRACTS.name,
                "sha256": _sha256(CONTRACTS.read_bytes()),
            },
            "reuse_audit": {
                "file": REUSE_AUDIT.name,
                "sha256": _sha256(REUSE_AUDIT.read_bytes()),
            },
            "separation": {
                "file": SEPARATION.name,
                "sha256": _sha256(SEPARATION.read_bytes()),
            },
            "d4_sealed_manifests": {
                "file": D4_SEALED.name,
                "sha256": _sha256(D4_SEALED.read_bytes()),
            },
        },
        "catalogues": _manifest_rows(bundle),
        "transformation_submanifests": _submanifest_rows(bundle),
        "protected_roles": protected,
        "fitting_pool": fitting,
        "spent_retrieval_pool": spent,
        "volume_ladder": volume,
        "role_disjointness": {
            "pairs_sharing_a_group": {name: len(shared) for name, shared in crossings.items()},
            "all_pairwise_disjoint": not any(crossings.values()),
            "proved_at": "S21D5-022, over all seven roles including the two spent ones",
            "separation_accepted": json.loads(SEPARATION.read_text())["accepted"],
        },
        "seeds": {
            "fitting": D5_FITTING_SEED,
            "calibration": D5_CALIBRATION_SEED,
            "invariance": INVARIANCE_TRANSFORM_SEED,
            "promotion": PROMOTION_TRANSFORM_SEED,
            "distinct_from_every_predecessor_seed": True,
        },
        "eligibility": {
            "rule": "both D5 cases apply: the rename map exists and the issue rewrite lands",
            "eligible_calibration_groups": len(eligible),
            "calibration_groups": seal.calibration_groups,
            "ineligible": sorted(
                {spec.template_id for spec in D5_CALIBRATION_SPECS} - set(eligible)
            ),
            "ineligible_inside_the_invariance_sample": ineligible_in_sample,
            "why_the_sample_is_checked_separately": (
                "the sample is the first twenty of the manifest by a frozen rule, not the first "
                "twenty eligible ones; an ineligible group inside it would silently shrink the "
                "regression rather than fail it"
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
            "spent_retrieval_pool_hash": seal.spent_retrieval_pool_hash,
            "volume_points": list(seal.volume_points),
            "candidate_slots": seal.candidate_slots,
            "outcomes_present": seal.outcomes_present,
            "corpus_authoring_capability_revoked": seal.corpus_authoring_capability_revoked,
        },
        "capability_revocation": {
            "capability": "isolated_corpus_authoring_validator",
            "revoked": True,
            "when": "at this seal, before any D5 outcome exists",
            "why": (
                "the capability that wrote the hundred calibration and sixty retrieval groups "
                "has no business outliving them; an authoring validator still open once outcomes "
                "exist is a channel from a role into the corpus that describes it"
            ),
            "what_it_closes": ["scripts/corpus_d5.py", "scripts/retrieval_d5.py"],
        },
    }

    stops: list[str] = []
    if not protected["all_identical"]:
        stops.append("sealed_manifests_protected_role_drift")
    if not fitting["membership"]["identical"]:
        stops.append("sealed_manifests_fitting_membership_drift")
    if not fitting["bodies"]["all_identical"]:
        stops.append("sealed_manifests_fitting_body_drift")
    if not body["role_disjointness"]["all_pairwise_disjoint"]:
        stops.append("sealed_manifests_role_crossing")
    if not body["role_disjointness"]["separation_accepted"]:
        stops.append("sealed_manifests_separation_not_accepted")
    if not spent["distinct"] or spent["groups_shared"]:
        stops.append("sealed_manifests_spent_retrieval_pool_reused")
    if (
        not volume["every_point_lands_on_a_whole_group"]
        or not volume["top_point_is_the_whole_pool"]
    ):
        stops.append("sealed_manifests_volume_point_splits_a_group")
    if seal.outcomes_present:
        stops.append("sealed_manifests_outcome_present")
    if not seal.corpus_authoring_capability_revoked:
        stops.append("sealed_manifests_capability_open")
    if seal.invariance_independent_decisions != 0:
        stops.append("sealed_manifests_replica_counted_as_independent")
    if ineligible_in_sample:
        stops.append("sealed_manifests_ineligible_group_inside_the_invariance_sample")
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

    path = arguments.output_root / "sprint-21d5-sealed-manifests.json"
    written = _write(path, body)

    print(f"{path.name}  {written}")
    for name, row in sorted(body["catalogues"].items()):
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
    print(f"  protected roles identical to D4: {body['protected_roles']['all_identical']}")
    print(
        f"  fitting pool: membership {body['fitting_pool']['membership']['identical']}, "
        f"bodies {body['fitting_pool']['bodies']['all_identical']}"
    )
    print(f"  volume ladder: {body['volume_ladder']['points']} outcomes")
    print(f"  seal: {body['seal']['content_hash']}")
    if stops:
        print("STOPS: " + ", ".join(stops))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
