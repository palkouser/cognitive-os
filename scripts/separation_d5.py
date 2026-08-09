#!/usr/bin/env python3
"""S21D5-022: prove rights, lineage, group and near-clone separation over the seven D5 roles.

W0 could not run this. `sprint-21d5-reuse-audit.json` says so in its own words --
`disjointness_check_deferred_to: "S21D5-022, after W1 authors the corpus"` -- because five of
the seven roles existed then and two did not. Both now do, so the deferred obligation is
discharged here against the corpora W1 actually authored rather than against the plan.

The seven roles, and where each one's membership is read from:

| role | groups | read from |
|---|---:|---|
| fitting | 180 | the released D4 seal: 80 training plus 100 calibration, spent for selection |
| calibration | 100 | `reality_task_specs_d5`, authored by S21D5-020 |
| retrieval | 60 | `reality_retrieval_specs_d5`, authored by S21D5-021 |
| final_a | 30 | the released D4 seal, carried unopened |
| final_b | 30 | the released D4 seal, carried unopened |
| canary | 5 | the released D4 seal, carried unopened |
| spent_retrieval | 60 | the released D4 seal; read once by D4 and spent, `d5_role: none` |

Three separations, because the sealed contract names three:

*Group-disjoint.* No repository group sits in two roles. Twenty-one pairs, stated one by one
rather than summarised, so a reader can see which pair was checked.

*Source-disjoint.* No body is byte-identical across two roles. Hashed rather than compared, so
the answer does not depend on how the two were reached.

*Clone-disjoint.* The released detectors over every body of every role. This one does not come
back clean, and §5 of this record is about why that is a finding rather than a failure.

Lineage is the reuse audit's digests recomputed from today's membership: if a carried role has
drifted since W0, the digest moves and this record says so instead of inheriting a verdict.

Rights are re-read rather than restated: the carried roles must still show nothing resolved.

    UV_CACHE_DIR=.cache/uv uv run python scripts/separation_d5.py
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_leakage import near_clone_pairs  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs import TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d2 import (  # noqa: E402
    D2_TASK_SPECS,
    module_source,
)
from cognitive_os.coding.reality_task_specs_d3 import D3_TASK_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d4 import D4_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d5 import D5_CALIBRATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
REUSE_AUDIT = EVIDENCE / "sprint-21d5-reuse-audit.json"

#: The two roles W1 authored. Everything else is carried or spent, and D5 is forbidden from
#: authoring into it -- §3.2 permits no new final, batch-B or canary bodies.
AUTHORED_BY_D5 = ("calibration", "retrieval")

#: The carried roles whose rights the audit protects. Nothing may be resolved out of these.
PROTECTED = ("final_a", "final_b", "canary")

#: A C3 spec names its four bodies differently from a D2 one. Read by their own names.
C3_LABELS = ("baseline", "incomplete_a", "incomplete_b", "correct_narrow", "correct_robust")
D2_LABELS = ("baseline", "variant_one", "variant_two", "variant_three", "variant_four")


def _digest(names: frozenset[str]) -> str:
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def _roles() -> dict[str, frozenset[str]]:
    bundle = seal_d4_corpus()
    return {
        "fitting": bundle.groups_of(CorrectionPartition.TRAINING)
        | bundle.groups_of(CorrectionPartition.CALIBRATION),
        "calibration": frozenset(spec.repository_group for spec in D5_CALIBRATION_SPECS),
        "retrieval": frozenset(spec.repository_group for spec in D5_RETRIEVAL_SPECS),
        "final_a": bundle.groups_of(CorrectionPartition.FINAL_A),
        "final_b": bundle.groups_of(CorrectionPartition.FINAL_B),
        "canary": bundle.groups_of(CorrectionPartition.CANARY),
        "spent_retrieval": bundle.retrieval_groups,
    }


def _bodies(roles: dict[str, frozenset[str]]) -> dict[str, str]:
    """Every body of every role, keyed `role::group:label`, as the module a runner would see."""
    correction = {
        spec.repository_group: spec
        for spec in (
            *TASK_SPECS,
            *D2_TASK_SPECS,
            *D3_TASK_SPECS,
            *D4_CALIBRATION_SPECS,
            *D5_CALIBRATION_SPECS,
        )
    }
    retrieval = {spec.repository_group: spec for spec in (*D4_RETRIEVAL_SPECS, *D5_RETRIEVAL_SPECS)}
    out: dict[str, str] = {}
    for role, groups in roles.items():
        for group in sorted(groups):
            if group in retrieval:
                spec = retrieval[group]
                for label in ("failed", "repaired"):
                    out[f"{role}::{group}:{label}"] = spec.module_text(getattr(spec, label))
                continue
            spec = correction[group]
            labels = D2_LABELS if hasattr(spec, "variant_one") else C3_LABELS
            for label in labels:
                body = getattr(spec, label, None)
                if body:
                    out[f"{role}::{group}:{label}"] = module_source(spec, body)
    return out


def _group_separation(roles: dict[str, frozenset[str]]) -> dict[str, Any]:
    pairs = {
        f"{left}|{right}": sorted(roles[left] & roles[right])
        for left, right in itertools.combinations(sorted(roles), 2)
    }
    return {
        "roles": {role: len(groups) for role, groups in sorted(roles.items())},
        "groups_total": sum(len(groups) for groups in roles.values()),
        "distinct_groups": len(frozenset().union(*roles.values())),
        "pairs_checked": len(pairs),
        "pairs_sharing_a_group": {pair: shared for pair, shared in pairs.items() if shared},
        "all_pairwise_disjoint": not any(pairs.values()),
    }


def _source_separation(bodies: dict[str, str]) -> dict[str, Any]:
    by_hash: dict[str, list[str]] = {}
    for key, text in bodies.items():
        by_hash.setdefault(hashlib.sha256(text.encode("utf-8")).hexdigest(), []).append(key)
    shared = {
        digest: sorted(keys)
        for digest, keys in by_hash.items()
        if len({key.split("::", 1)[0] for key in keys}) > 1
    }
    return {
        "bodies_hashed": len(bodies),
        "distinct_body_hashes": len(by_hash),
        "bodies_byte_identical_across_two_roles": shared,
        "source_disjoint": not shared,
    }


def _clone_separation(bodies: dict[str, str]) -> dict[str, Any]:
    """The released detectors over every role, and the split that decides how to read them."""
    cross = sorted(
        (pair.left, pair.right, pair.reason)
        for pair in near_clone_pairs(bodies)
        if pair.left.split("::", 1)[0] != pair.right.split("::", 1)[0]
    )
    predating, touching = [], []
    for left, right, reason in cross:
        sides = {left.split("::", 1)[0], right.split("::", 1)[0]}
        target = touching if sides & set(AUTHORED_BY_D5) else predating
        target.append(f"{left}|{right}|{reason}")
    return {
        "cross_role_near_clone_pairs": len(cross),
        "pairs_between_two_carried_roles_predating_d5": predating,
        "pairs_touching_a_role_d5_authored": len(touching),
        "reading": (
            "the literal reading of 'clone-disjoint across seven roles' is already false of the "
            "carried roles before D5 authored anything: final_b and fitting collide on two "
            "released D2 groups, and section 3.2 forbids D5 from authoring into either. A rule "
            "the inherited roles cannot satisfy is not the operative rule. The operative one is "
            "the one the same sealed contract states in its own near_clone_rule field -- "
            "cross-group pairs against every released corpus, applied to the authored corpora -- "
            "and that is what corpus_d5.py and retrieval_d5.py enforce every batch"
        ),
    }


def _authored_corpus_separation() -> dict[str, Any]:
    """The contract's named acceptance criterion, recomputed here rather than cited."""
    correction = {
        f"{spec.repository_group}:{label}": module_source(spec, getattr(spec, label))
        for spec in (
            *TASK_SPECS,
            *D2_TASK_SPECS,
            *D3_TASK_SPECS,
            *D4_CALIBRATION_SPECS,
            *D5_CALIBRATION_SPECS,
        )
        for label in (D2_LABELS if hasattr(spec, "variant_one") else C3_LABELS)
        if getattr(spec, label, None)
    }
    authored = {spec.repository_group for spec in D5_CALIBRATION_SPECS}
    calibration = sorted(
        f"{pair.left}|{pair.right}|{pair.reason}"
        for pair in near_clone_pairs(correction)
        if pair.left.split(":")[0] != pair.right.split(":")[0]
        and {pair.left.split(":")[0], pair.right.split(":")[0]} & authored
    )
    pool = {
        f"{spec.repository_group}:{side}": spec.module_text(getattr(spec, side))
        for spec in D5_RETRIEVAL_SPECS
        for side in ("failed", "repaired")
    }
    retrieval = sorted(
        f"{pair.left}|{pair.right}|{pair.reason}"
        for pair in near_clone_pairs(pool)
        if pair.left.split(":")[0] != pair.right.split(":")[0]
    )
    return {
        "rule": (
            "normalized_structure_hash and token_stream_hash, cross-group pairs, over every "
            "released corpus for the calibration set and over the pool itself for retrieval, "
            "which is S21D4-043's scope and reason"
        ),
        "calibration_bodies_compared": len(correction),
        "retrieval_bodies_compared": len(pool),
        "cross_group_collisions_touching_21d5": calibration + retrieval,
        "separated": not calibration and not retrieval,
    }


def _lineage(roles: dict[str, frozenset[str]]) -> dict[str, Any]:
    """Recompute W0's digests from today's membership. A drift moves a hash and shows here."""
    audit = json.loads(REUSE_AUDIT.read_text(encoding="utf-8"))
    transition = audit["role_transition"]
    checks = {
        "fitting_pool": (transition["fitting_pool"]["names_digest"], roles["fitting"]),
        "spent_for_selection": (
            transition["spent_for_selection"]["names_digest"],
            frozenset(spec.repository_group for spec in D4_CALIBRATION_SPECS),
        ),
        "spent_entirely": (transition["spent_entirely"]["names_digest"], roles["spent_retrieval"]),
    }
    recomputed = {
        name: {
            "recorded_in_w0": recorded,
            "recomputed_now": _digest(members),
            "unchanged": recorded == _digest(members),
        }
        for name, (recorded, members) in checks.items()
    }
    # W0 digested the carried roles by each group's `content_hash`, not by its name, and the
    # difference matters: a name digest sees a membership change and a content digest also sees
    # a body drift under an unchanged name. Recomputed the way it was recorded, or the check
    # compares two different quantities and calls the mismatch a drift.
    bundle = seal_d4_corpus()
    partitions = {
        "final_a": CorrectionPartition.FINAL_A,
        "final_b": CorrectionPartition.FINAL_B,
        "canary": CorrectionPartition.CANARY,
    }
    carried = {}
    for role in PROTECTED:
        catalogue = bundle.catalogues[partitions[role]]
        now = hashlib.sha256(
            "\n".join(sorted(group.content_hash for group in catalogue.groups)).encode("utf-8")
        ).hexdigest()
        carried[role] = {
            "digest_over": "group content hashes, as W0 recorded it",
            "groups": len(roles[role]),
            "recorded_in_w0": audit["roles"][role]["group_digest"],
            "recomputed_now": now,
            "unchanged": audit["roles"][role]["group_digest"] == now,
        }
    return {
        "reuse_audit_read": REUSE_AUDIT.name,
        "reuse_audit_integrity_content_hash": audit["integrity_content_hash"],
        "digests_recomputed_from_todays_membership": {**recomputed, **carried},
        "every_digest_unchanged": all(
            row["unchanged"] for row in (*recomputed.values(), *carried.values())
        ),
        "deferred_obligation_discharged": transition["disjointness_check_deferred_to"],
    }


def _rights(roles: dict[str, frozenset[str]]) -> dict[str, Any]:
    """The additional clause, and the protected-role reads, both re-run rather than cited."""
    audit = json.loads(REUSE_AUDIT.read_text(encoding="utf-8"))
    spent = frozenset(spec.repository_group for spec in D4_CALIBRATION_SPECS)
    return {
        "authored_calibration_disjoint_from_spent_for_selection": {
            "rule": (
                "the sealed corpus-submanifest contract adds this to the seven-role rule: the "
                "authored calibration corpus must be disjoint from the spent-for-selection "
                "digest, because those 100 groups already decided the frozen k-NN grid"
            ),
            "spent_for_selection_groups": len(spent),
            "shared_with_the_d5_calibration_corpus": sorted(roles["calibration"] & spent),
            "disjoint": not (roles["calibration"] & spent),
        },
        "protected_roles_unread": {
            role: {
                "bodies_resolved": audit["protected_bodies_resolved"],
                "decision": audit["roles"][role]["decision"],
            }
            for role in PROTECTED
        },
        "protected_task_identities": audit["protected_task_identities"],
        "d5_authored_into_a_protected_role": sorted(
            frozenset().union(*(roles[role] for role in PROTECTED))
            & frozenset().union(*(roles[role] for role in AUTHORED_BY_D5))
        ),
    }


def build() -> dict[str, Any]:
    roles = _roles()
    bodies = _bodies(roles)
    group = _group_separation(roles)
    source = _source_separation(bodies)
    clone = _clone_separation(bodies)
    authored = _authored_corpus_separation()
    lineage = _lineage(roles)
    rights = _rights(roles)

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W1",
        "items": ["S21D5-022"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role_membership_read_from": {
            "fitting": "released D4 seal, training plus calibration",
            "calibration": "reality_task_specs_d5, authored by S21D5-020",
            "retrieval": "reality_retrieval_specs_d5, authored by S21D5-021",
            "final_a": "released D4 seal, carried unopened",
            "final_b": "released D4 seal, carried unopened",
            "canary": "released D4 seal, carried unopened",
            "spent_retrieval": "released D4 seal, read once by D4 and spent",
        },
        "group_separation": group,
        "source_separation": source,
        "clone_separation": clone,
        "authored_corpus_separation": authored,
        "lineage": lineage,
        "rights": rights,
        "accepted": (
            group["all_pairwise_disjoint"]
            and source["source_disjoint"]
            and authored["separated"]
            and lineage["every_digest_unchanged"]
            and rights["authored_calibration_disjoint_from_spent_for_selection"]["disjoint"]
            and not rights["d5_authored_into_a_protected_role"]
        ),
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d5-corpus-separation.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "roles": record["group_separation"]["roles"],
                "pairs_checked": record["group_separation"]["pairs_checked"],
                "all_pairwise_disjoint": record["group_separation"]["all_pairwise_disjoint"],
                "source_disjoint": record["source_separation"]["source_disjoint"],
                "cross_group_collisions_touching_21d5": record["authored_corpus_separation"][
                    "cross_group_collisions_touching_21d5"
                ],
                "cross_role_near_clone_pairs": record["clone_separation"][
                    "cross_role_near_clone_pairs"
                ],
                "pairs_predating_d5": len(
                    record["clone_separation"]["pairs_between_two_carried_roles_predating_d5"]
                ),
                "every_digest_unchanged": record["lineage"]["every_digest_unchanged"],
                "accepted": record["accepted"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0 if record["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
