#!/usr/bin/env python3
"""S21D7-023: seal every D7 campaign and holdout manifest, before any outcome exists.

The seal is the point at which the corpus stops being editable and starts being spent. D7 has six
things to show when it writes one, and each is checked here rather than asserted.

*No outcome exists yet.* A seal written after a result is a description of that result.

*The three protected roles are the released ones.* Final A, final B and canary were audited at
S21D7-003/004 and recorded `reuse`, so their hashes are compared against the bytes
sprint-21d6-sealed-manifests.json published. A re-derivation would produce the same number and
would hide a drift; a comparison against the released file cannot.

*The fitting pool is D5's, carried through D6, and is not re-executed.* This is where D7 differs
from D6 in the direction nobody expects: D6 refitted nothing and D7 fits, once — but it fits on
the *released matrices*, by hash, and executes not one row of the pool. So the pool is proved by
membership against W0 and by body against the released D6 catalogue, and the seal records
`re_executed: false`, which is a claim about what this sprint runs rather than about what it fits.

*The conformal half is D6's certification corpus, demoted.* Same bodies, new role: it places the
bar and certifies nothing. Proved against W0's names digest and against D6's released calibration
catalogue hash — the partition D6's certification half lives in — because a bar placed by drifted
margins is not the bar the pre-registration named.

*The certification half is the one S21D7-022 proved separated.* The separation record is bound by
hash rather than cited, so a seal cannot claim a separation that a later edit invalidated.

*Retrieval is inherited, not authored.* D7 seals two spent pools and authors none: condition 24 is
inherited under the renewed ruling this record binds, which is the sixty groups of authoring the
ruling bought. `retrieval_groups_authored` is zero and the seal carries D5's pool hash so a reader
can see whose measurement is being inherited.

`--provisional` seals an unfinished certification corpus so the chain below can be exercised
before the hundredth group exists. Such a record says so in its own bytes, carries no outcome, and
leaves the authoring capability open -- because under `--provisional` more bodies are still to be
written, and a seal that claimed otherwise would be wrong about the one thing a seal is for.

    UV_CACHE_DIR=.cache/uv uv run python scripts/sealed_manifests_d7.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/sealed_manifests_d7.py --check
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

from cognitive_os.coding.reality_task_specs_d7 import D7_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_catalogue import CANDIDATES_PER_GROUP  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import CARRIED_ROLES  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import (  # noqa: E402
    CERTIFICATION_GROUPS,
    D7_CASES,
    D7_CERTIFICATION_SEED,
    INVARIANCE_SAMPLE_GROUPS,
    INVARIANCE_TRANSFORM_SEED,
    PROMOTION_TRANSFORM_SEED,
    D7CorpusBundle,
    d7_invariance_sample_groups,
    eligible_certification_groups,
    seal_d7_corpus,
)
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d7-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d7-contracts.json"
DEMOTION = EVIDENCE / "sprint-21d7-demotion-ruling.json"
LADDER = EVIDENCE / "sprint-21d7-ladder-ruling.json"
CONDITION_24 = EVIDENCE / "sprint-21d7-condition-24-ruling.json"
D6_SEALED = EVIDENCE / "sprint-21d6-sealed-manifests.json"
SEPARATION = EVIDENCE / "sprint-21d7-corpus-separation.json"
REUSE_AUDIT = EVIDENCE / "sprint-21d7-reuse-audit.json"


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


def _released() -> dict[str, Any]:
    return json.loads(D6_SEALED.read_text())["catalogues"]


def _protected_role_proof(bundle: D7CorpusBundle) -> dict[str, Any]:
    """Compare the three carried hashes against the bytes D6 released, role by role."""
    released = _released()
    rows = {}
    for partition in CARRIED_ROLES:
        carried = bundle.catalogues[partition].content_hash
        rows[partition.value] = {
            "d7_catalogue_hash": carried,
            "d6_released_hash": released[partition.value]["content_hash"],
            "identical": carried == released[partition.value]["content_hash"],
            "obtained_by": "seal_d6_corpus(), carried; not re-derived from the specs",
            "s21d6_004_decision": "reuse",
            "carried_for": (
                "the fifth sprint running: D2 authored them, D3, D4, D5 and D6 carried"
            ),
        }
    return {
        "roles": rows,
        "all_identical": all(row["identical"] for row in rows.values()),
        "d6_evidence": D6_SEALED.name,
        "d6_evidence_sha256": _sha256(D6_SEALED.read_bytes()),
        "d6_seal_hash": bundle.d6_seal_hash,
        "why_not_re_derived": (
            "a re-derivation from the same specs would produce the same number whether or not "
            "the released catalogue had moved underneath it, so it could not tell reuse from "
            "coincidence"
        ),
    }


def _fitting_pool_proof(bundle: D7CorpusBundle) -> dict[str, Any]:
    """The 180 groups D7 fits on and does not run, proved against W0 and the released D6 bytes."""
    audit = json.loads(REUSE_AUDIT.read_text())["role_transition"]["fitting_pool"]
    released = _released()
    names = sorted(bundle.groups_of(CorrectionPartition.TRAINING))
    digest = _sha256("\n".join(names).encode("utf-8"))
    catalogue = bundle.catalogues[CorrectionPartition.TRAINING].content_hash
    return {
        "groups": len(names),
        "d7_use": audit["d7_use"],
        "membership": {
            "names_digest": digest,
            "w0_names_digest": audit["names_digest"],
            "identical": digest == audit["names_digest"],
            "proves": "which 180 groups the pool is",
            "cannot_prove": "that a body has not drifted under an unchanged group name",
        },
        "bodies": {
            "d7_catalogue_hash": catalogue,
            "d6_released_hash": released["training"]["content_hash"],
            "identical": catalogue == released["training"]["content_hash"],
            "proves": (
                "the pool D7 names is byte-for-byte the one the released D6 seal holds, which is "
                "the half of the claim the name digest cannot reach"
            ),
        },
        "re_executed": False,
        "reading": (
            "D5 re-executed this pool under its own seed because it refitted on it. D6 refitted "
            "nothing. D7 fits exactly one direction on it -- and still executes no row: the fit "
            "reads the released 720-row matrices by hash and the seven relational channels "
            "assembled beside them, so the pool contributes no candidate identity and no outcome "
            "to this sprint, and the seal claims none"
        ),
        "outcomes_if_executed": len(names) * CANDIDATES_PER_GROUP,
    }


def _conformal_half_proof(bundle: D7CorpusBundle) -> dict[str, Any]:
    """D6's certification corpus in its new role: it places the bar and certifies nothing."""
    audit = json.loads(REUSE_AUDIT.read_text())["role_transition"]["conformal_half"]
    released = _released()
    names = sorted(bundle.conformal_groups)
    digest = _sha256("\n".join(names).encode("utf-8"))
    return {
        "groups": len(names),
        "was": audit["role"],
        "membership": {
            "names_digest": digest,
            "w0_names_digest": audit["names_digest"],
            "identical": digest == audit["names_digest"],
        },
        "bodies": {
            "d7_catalogue_hash": bundle.conformal.content_hash,
            "d6_released_hash": released["calibration"]["content_hash"],
            "identical": bundle.conformal.content_hash == released["calibration"]["content_hash"],
            "partition_key": (
                "calibration: D6's certification half lives in the CALIBRATION partition of its "
                "own seal, which is the row this hash is compared against"
            ),
            "why_it_matters_here": (
                "the bar is a quantile of these groups' margins under a direction fitted in W2; "
                "a drifted body is a drifted margin and therefore a different threshold under "
                "the same carried alpha"
            ),
        },
        "use": audit["use"],
        "forbidden_in_d7": audit["forbidden_in_d7"],
        "re_executed": audit["re_executed"],
        "read_through": audit["read_through"],
        "demotion_rule": (
            "S21D7-010: evidence spent by publication is demotable to exactly one further role, "
            "the bar-setting half, and a demoted half may never certify. D5's calibration became "
            "D6's conformal half under the same principle, one step earlier along the same "
            "ladder -- and the ruling declined to demote that half a third time"
        ),
    }


def _inherited_retrieval_proof(bundle: D7CorpusBundle) -> dict[str, Any]:
    """Two spent pools, no fresh one. The condition-24 ruling, bound rather than described."""
    released = _released()
    inherited = bundle.seal.inherited_retrieval_pool_hash
    return {
        "retrieval_groups_authored": bundle.seal.retrieval_groups_authored,
        "inherited_pool_hash": inherited,
        "d6_released_hash": released["inherited_retrieval"]["content_hash"],
        "identical_to_the_released_pool": (
            inherited == released["inherited_retrieval"]["content_hash"]
        ),
        "spent_pools": {
            "d5": {"hash": inherited, "read_once_by": "S21D5-046", "d7_role": "none"},
            "d4": {"read_once_by": "S21D4-043", "d7_role": "none"},
        },
        "condition_24": {
            "ruling": "inherited from D5's sealed measurement, conditionally, renewed for D7",
            "record": CONDITION_24.name,
            "record_sha256": _sha256(CONDITION_24.read_bytes()),
            "authored_groups_saved": 60,
        },
        "why_no_fresh_pool": (
            "a pool read once has had its queries answered, so neither spent pool can be measured "
            "against again -- and D7 authors no replacement because the gate owner renewed the "
            "ruling that condition "
            "24 inherited rather than re-measured. The seal names the inherited pool so that the "
            "measurement being carried has an identity a reader can check"
        ),
    }


def _volume_proof(bundle: D7CorpusBundle) -> dict[str, Any]:
    """One point, not a ladder, and the arithmetic that keeps it off the inside of a group."""
    point = bundle.seal.volume_point
    return {
        "point": point,
        "point_in_groups": point // CANDIDATES_PER_GROUP,
        "lands_on_a_whole_group": point % CANDIDATES_PER_GROUP == 0,
        "is_the_whole_fitting_pool": point == bundle.seal.fitting_groups * CANDIDATES_PER_GROUP,
        "why_whole_groups": (
            "fitting on three of a group's four candidates puts the fourth's siblings in the "
            "exemplar set, and the difference that produces is not a volume effect"
        ),
        "why_one_point": (
            "S21D5-011's ladder answered the volume question -- coverage moved one point across a "
            "2.25x span -- so D7 fits at the single point that answer leaves standing. A second "
            "point here would be a search revision 7 forbids by name, not a replication"
        ),
    }


def _manifest_rows(bundle: D7CorpusBundle) -> dict[str, Any]:
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
    # The conformal half sits beside the catalogues rather than inside them: it shares the
    # CALIBRATION partition with the certification half in the protocol's vocabulary, so a
    # dictionary keyed by partition cannot hold both. Named separately is what stops one being
    # read as the other.
    rows["conformal"] = {
        "content_hash": bundle.conformal.content_hash,
        "groups": len(bundle.conformal.groups),
        "candidate_slots": bundle.conformal.candidate_slots,
        "campaign_seed": bundle.conformal.campaign_seed,
        "generator_path": bundle.conformal.generator_path,
        "shares_the_calibration_partition_with": "certification, under the key `calibration`",
    }
    rows["inherited_retrieval"] = {
        "content_hash": bundle.seal.inherited_retrieval_pool_hash,
        "groups_authored_by_d7": bundle.seal.retrieval_groups_authored,
        "authored_by": "S21D5-021",
    }
    return rows


def _submanifest_rows(bundle: D7CorpusBundle) -> dict[str, Any]:
    invariance = bundle.invariance_transformations
    promotion = bundle.promotion_transformations
    provisional = bundle.seal.provisional
    return {
        "certification_invariance": {
            "content_hash": invariance.content_hash,
            "source_manifest_hash": invariance.source_manifest_hash,
            "generator_code_hash": invariance.generator_code_hash,
            "hard_coded_oracle_hash": invariance.hard_coded_oracle_hash,
            "cases": len(D7_CASES),
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
                "the first twenty groups of the family-interleaved certification manifest, so the "
                "choice can be checked against the sealed catalogue afterwards"
            ),
            "sample_groups_named": list(d7_invariance_sample_groups(provisional=provisional)),
        },
        "promotion": {
            "content_hash": promotion.content_hash,
            "source_manifest_hash": promotion.source_manifest_hash,
            "generator_code_hash": promotion.generator_code_hash,
            "hard_coded_oracle_hash": promotion.hard_coded_oracle_hash,
            "cases": len(D7_CASES),
            "groups": 60,
            "nominal_decisions": len(promotion.cases),
            "independent_decisions": len(promotion.cases) // len(D7_CASES),
            "reported_side_by_side": True,
            "seed": PROMOTION_TRANSFORM_SEED,
            "distinct_from_every_predecessor_promotion_set_by_seed": (
                "D4, D5, D6 and D7 transform the same sixty final groups under the same two "
                "released cases, so the seed is the only thing separating their case identities; "
                "it is D7's own and the four sets share no case id"
            ),
        },
    }


def _evidence(recorded_at: str, *, provisional: bool) -> tuple[dict[str, Any], list[str]]:
    bundle = seal_d7_corpus(provisional=provisional)
    seal = bundle.seal
    protected = _protected_role_proof(bundle)
    fitting = _fitting_pool_proof(bundle)
    conformal = _conformal_half_proof(bundle)
    retrieval = _inherited_retrieval_proof(bundle)
    volume = _volume_proof(bundle)

    groups = {
        partition.value: sorted(bundle.groups_of(partition)) for partition in bundle.catalogues
    }
    groups["conformal"] = sorted(bundle.conformal_groups)
    names = sorted(groups)
    crossings = {}
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            crossings[f"{left}|{right}"] = sorted(set(groups[left]) & set(groups[right]))

    eligible = eligible_certification_groups()
    # The sample names repository groups and eligibility names template ids, so one of the two
    # has to be translated before they can be subtracted. Comparing them raw would report every
    # sampled group as ineligible and read like a corpus defect.
    template_of = {spec.repository_group: spec.template_id for spec in D7_CERTIFICATION_SPECS}
    ineligible_in_sample = sorted(
        group
        for group in d7_invariance_sample_groups(provisional=provisional)
        if template_of[group] not in set(eligible)
    )

    body = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W1",
        "items": ["S21D7-023"],
        "provisional": provisional,
        "recorded_at": recorded_at,
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "final_outcomes_inspected": False,
        "purpose": (
            "Seal the fitting, conformal, certification, final A, final B and canary manifests "
            "before any outcome exists: carrying the three protected roles S21D7-004 recorded as "
            "reuse rather than re-deriving them, proving the 180-group fitting pool and the "
            "100-group conformal half both by membership and by body against the released D5 "
            "bytes, naming the inherited retrieval pool D6 does not author, and closing the "
            "corpus-authoring capability."
        ),
        "bound_evidence": {
            "contracts": {"file": CONTRACTS.name, "sha256": _sha256(CONTRACTS.read_bytes())},
            "demotion_ruling": {"file": DEMOTION.name, "sha256": _sha256(DEMOTION.read_bytes())},
            "ladder_ruling": {"file": LADDER.name, "sha256": _sha256(LADDER.read_bytes())},
            "condition_24_ruling": {
                "file": CONDITION_24.name,
                "sha256": _sha256(CONDITION_24.read_bytes()),
            },
            "reuse_audit": {"file": REUSE_AUDIT.name, "sha256": _sha256(REUSE_AUDIT.read_bytes())},
            "separation": {"file": SEPARATION.name, "sha256": _sha256(SEPARATION.read_bytes())},
            "d6_sealed_manifests": {
                "file": D6_SEALED.name,
                "sha256": _sha256(D6_SEALED.read_bytes()),
            },
        },
        "catalogues": _manifest_rows(bundle),
        "transformation_submanifests": _submanifest_rows(bundle),
        "protected_roles": protected,
        "fitting_pool": fitting,
        "conformal_half": conformal,
        "inherited_retrieval": retrieval,
        "volume": volume,
        "role_disjointness": {
            "pairs_sharing_a_group": {name: len(shared) for name, shared in crossings.items()},
            "all_pairwise_disjoint": not any(crossings.values()),
            "proved_at": (
                "S21D7-022, over all nine roles including the two spent retrieval pools and the "
                "twice-spent D5 calibration half"
            ),
            "separation_accepted": json.loads(SEPARATION.read_text())["accepted"],
            "separation_covered_groups": json.loads(SEPARATION.read_text())["certification_corpus"][
                "groups_authored"
            ],
        },
        "seeds": {
            "certification": D7_CERTIFICATION_SEED,
            "invariance": INVARIANCE_TRANSFORM_SEED,
            "promotion": PROMOTION_TRANSFORM_SEED,
            "distinct_from_every_predecessor_seed": True,
            "no_fitting_seed": (
                "D7 fits a direction but executes no fitting row, so it has no fitting seed to be "
                "distinct from; the pool carries D5's candidate identities and D7 adds none"
            ),
        },
        "eligibility": {
            "rule": "both D6 cases apply: the rename map exists and the issue rewrite lands",
            "eligible_certification_groups": len(eligible),
            "certification_groups": seal.certification_groups,
            "ineligible": sorted(
                {spec.template_id for spec in D7_CERTIFICATION_SPECS} - set(eligible)
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
            "conformal_catalogue_hash": seal.conformal_catalogue_hash,
            "certification_catalogue_hash": seal.certification_catalogue_hash,
            "final_a_catalogue_hash": seal.final_a_catalogue_hash,
            "final_b_catalogue_hash": seal.final_b_catalogue_hash,
            "canary_catalogue_hash": seal.canary_catalogue_hash,
            "invariance_submanifest_hash": seal.invariance_submanifest_hash,
            "promotion_submanifest_hash": seal.promotion_submanifest_hash,
            "inherited_retrieval_pool_hash": seal.inherited_retrieval_pool_hash,
            "retrieval_groups_authored": seal.retrieval_groups_authored,
            "volume_point": seal.volume_point,
            "candidate_slots": seal.candidate_slots,
            "outcomes_present": seal.outcomes_present,
            "corpus_authoring_capability_revoked": seal.corpus_authoring_capability_revoked,
            "provisional": seal.provisional,
        },
        "capability_revocation": {
            "capability": "isolated_corpus_authoring_validator",
            "revoked": seal.corpus_authoring_capability_revoked,
            "when": (
                "at this seal, before any D6 outcome exists"
                if seal.corpus_authoring_capability_revoked
                else "not yet: the certification corpus is unfinished and this seal is provisional"
            ),
            "why": (
                "the capability that wrote the hundred certification groups has no business "
                "outliving them; an authoring validator still open once outcomes exist is a "
                "channel from a role into the corpus that describes it"
            ),
            "what_it_closes": ["scripts/corpus_d7.py"],
            "no_retrieval_authoring_to_close": (
                "D5 also closed scripts/retrieval_d5.py here. Neither D6 nor D7 opened an "
                "equivalent, because condition 24 is inherited rather than re-measured"
            ),
        },
    }

    stops: list[str] = []
    if not protected["all_identical"]:
        stops.append("sealed_manifests_protected_role_drift")
    if not fitting["membership"]["identical"]:
        stops.append("sealed_manifests_fitting_membership_drift")
    if not fitting["bodies"]["identical"]:
        stops.append("sealed_manifests_fitting_body_drift")
    if fitting["re_executed"]:
        stops.append("sealed_manifests_fitting_pool_re_executed")
    if not conformal["membership"]["identical"]:
        stops.append("sealed_manifests_conformal_membership_drift")
    if not conformal["bodies"]["identical"]:
        stops.append("sealed_manifests_conformal_body_drift")
    if not body["role_disjointness"]["all_pairwise_disjoint"]:
        stops.append("sealed_manifests_role_crossing")
    if not body["role_disjointness"]["separation_accepted"]:
        stops.append("sealed_manifests_separation_not_accepted")
    if body["role_disjointness"]["separation_covered_groups"] != seal.certification_groups:
        stops.append("sealed_manifests_separation_covers_a_different_corpus")
    if not retrieval["identical_to_the_released_pool"] or seal.retrieval_groups_authored:
        stops.append("sealed_manifests_retrieval_role_authored")
    if not volume["lands_on_a_whole_group"] or not volume["is_the_whole_fitting_pool"]:
        stops.append("sealed_manifests_volume_point_splits_a_group")
    if seal.outcomes_present:
        stops.append("sealed_manifests_outcome_present")
    if not seal.corpus_authoring_capability_revoked and not provisional:
        stops.append("sealed_manifests_capability_open")
    if seal.invariance_independent_decisions != 0:
        stops.append("sealed_manifests_replica_counted_as_independent")
    if ineligible_in_sample:
        stops.append("sealed_manifests_ineligible_group_inside_the_invariance_sample")
    if provisional and seal.certification_groups >= CERTIFICATION_GROUPS:
        stops.append("sealed_manifests_provisional_over_a_complete_corpus")
    if not provisional and seal.certification_groups < CERTIFICATION_GROUPS:
        stops.append("sealed_manifests_incomplete_corpus_sealed_as_final")
    return body, stops


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=EVIDENCE)
    parser.add_argument("--check", action="store_true", help="verify without rewriting")
    parser.add_argument(
        "--provisional",
        action="store_true",
        help="seal an unfinished certification corpus, to exercise the chain below",
    )
    arguments = parser.parse_args()

    recorded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    body, stops = _evidence(recorded_at, provisional=arguments.provisional)

    if arguments.check:
        print(json.dumps({"provisional": arguments.provisional, "stops": stops}, indent=1))
        return 1 if stops else 0

    path = arguments.output_root / "sprint-21d7-sealed-manifests.json"
    written = _write(path, body)

    print(f"{path.name}  {written}")
    for name, row in sorted(body["catalogues"].items()):
        groups = row.get("groups", row.get("groups_authored_by_d7"))
        print(f"  {name:20} {groups:4} groups  {row['content_hash'][:16]}")
    invariance = body["transformation_submanifests"]["certification_invariance"]
    promotion = body["transformation_submanifests"]["promotion"]
    print(
        f"  invariance   {invariance['transformed_decisions']} transformed / "
        f"{invariance['independent_decisions']} independent"
    )
    print(
        f"  promotion    {promotion['nominal_decisions']} nominal / "
        f"{promotion['independent_decisions']} independent"
    )
    print(f"  protected roles identical to D6: {body['protected_roles']['all_identical']}")
    print(
        f"  fitting pool: membership {body['fitting_pool']['membership']['identical']}, "
        f"body {body['fitting_pool']['bodies']['identical']}, "
        f"re-executed {body['fitting_pool']['re_executed']}"
    )
    print(
        f"  conformal half: membership {body['conformal_half']['membership']['identical']}, "
        f"body {body['conformal_half']['bodies']['identical']}"
    )
    print(f"  retrieval authored by D7: {body['seal']['retrieval_groups_authored']}")
    print(f"  volume: {body['volume']['point']} outcomes over the whole pool")
    print(f"  seal: {body['seal']['content_hash']}  provisional={body['provisional']}")
    if stops:
        print("STOPS: " + ", ".join(stops))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
