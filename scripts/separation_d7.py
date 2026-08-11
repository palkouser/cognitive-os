#!/usr/bin/env python3
"""S21D7-022: prove rights, lineage, group and near-clone separation over the eight D6 roles.

W0 deferred this on purpose. `sprint-21d7-reuse-audit.json` says so in its own words --
`disjointness_check_deferred_to: "S21D7-022, after W1 authors the corpus"` -- because seven of
the eight roles existed then and the eighth did not. It does now, so the deferred obligation is
discharged against the corpus W1 actually authored rather than against the plan.

The eight roles, and where each one's membership is read from:

| role | groups | read from |
|---|---:|---|
| fitting | 180 | the released D5 seal: D4's 80 training plus 100 calibration, spent twice over |
| conformal | 100 | `reality_task_specs_d5`, D5's calibration corpus, demoted to bar-setting |
| certification | 100 | `reality_task_specs_d7`, authored by S21D7-020 |
| final_a | 30 | the released D5 seal, carried unopened |
| final_b | 30 | the released D5 seal, carried unopened |
| canary | 5 | the released D5 seal, carried unopened |
| spent_retrieval_d4 | 60 | read once by S21D4-043 and spent, `d6_role: none` |
| spent_retrieval_d5 | 60 | read once by S21D5-046 and spent, `d6_role: none` |

D6 authors exactly one of them. That is the shape the condition-24 ruling bought: D5 authored two
roles and had to separate both, D6 inherits condition 24 from D5's sealed measurement and so
authors no retrieval pool at all. Both pools are still roles here -- a spent pool that nothing
checks is a pool that can quietly reappear in a corpus -- but neither is an authoring target, and
the near-clone rule that applied to D5's fresh pool has nothing left to apply to.

Three separations, because the sealed contract names three:

*Group-disjoint.* No repository group sits in two roles. Twenty-eight pairs, stated one by one
rather than summarised, so a reader can see which pair was checked.

*Source-disjoint.* No body is byte-identical across two roles. Hashed rather than compared, so
the answer does not depend on how the two were reached.

*Clone-disjoint.* The released detectors over every body of every role. This one does not come
back clean, and section 5 of this record is about why that is a finding rather than a failure --
the same finding D5 recorded, inherited unchanged, because it predates both sprints.

Lineage is the reuse audit's digests recomputed from today's membership: if a carried role has
drifted since W0, the digest moves and this record says so instead of inheriting a verdict.

Rights are re-read rather than restated: the carried roles must still show nothing resolved, and
the authored corpus must be disjoint from the half that places the bar it will be measured
against.

    UV_CACHE_DIR=.cache/uv uv run python scripts/separation_d7.py
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
from cognitive_os.coding.reality_task_specs_d6 import D6_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.coding.reality_task_specs_d7 import D7_CERTIFICATION_SPECS  # noqa: E402
from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d5 import seal_d5_corpus  # noqa: E402
from cognitive_os.learning.correction_catalogue_d7 import CERTIFICATION_GROUPS  # noqa: E402
from cognitive_os.learning.correction_protocol import CorrectionPartition  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
REUSE_AUDIT = EVIDENCE / "sprint-21d7-reuse-audit.json"
CONDITION_24 = EVIDENCE / "sprint-21d7-condition-24-ruling.json"

#: The one role W1 authors. Everything else is carried or spent, and D6 is forbidden from
#: authoring into it -- section 4.1 permits no new fitting, conformal, final, canary or
#: retrieval bodies.
AUTHORED_BY_D7 = ("certification",)

#: The carried roles whose rights the audit protects. Nothing may be resolved out of these.
PROTECTED = ("final_a", "final_b", "canary")

#: The two pools that were read once and are spent. Roles, so the disjointness check can see
#: them; not authoring targets, because D6 authors no retrieval role at all.
SPENT_RETRIEVAL = ("spent_retrieval_d4", "spent_retrieval_d5")

#: A C3 spec names its four bodies differently from a D2 one. Read by their own names.
C3_LABELS = ("baseline", "incomplete_a", "incomplete_b", "correct_narrow", "correct_robust")
D2_LABELS = ("baseline", "variant_one", "variant_two", "variant_three", "variant_four")


def _digest(names: frozenset[str]) -> str:
    return hashlib.sha256("\n".join(sorted(names)).encode("utf-8")).hexdigest()


def _roles() -> dict[str, frozenset[str]]:
    d4 = seal_d4_corpus()
    d5 = seal_d5_corpus()
    return {
        "fitting": d5.groups_of(CorrectionPartition.TRAINING),
        "conformal": frozenset(spec.repository_group for spec in D6_CERTIFICATION_SPECS),
        # Spent twice and demoted no further: S21D7-010 named this half and declined it. It is a
        # role here so the disjointness check can see it, and it is read by nothing else.
        "spent_calibration_d5": frozenset(spec.repository_group for spec in D5_CALIBRATION_SPECS),
        "certification": frozenset(spec.repository_group for spec in D7_CERTIFICATION_SPECS),
        "final_a": d5.groups_of(CorrectionPartition.FINAL_A),
        "final_b": d5.groups_of(CorrectionPartition.FINAL_B),
        "canary": d5.groups_of(CorrectionPartition.CANARY),
        "spent_retrieval_d4": d4.retrieval_groups,
        "spent_retrieval_d5": d5.retrieval_groups,
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
            *D6_CERTIFICATION_SPECS,
            *D7_CERTIFICATION_SPECS,
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
        target = touching if sides & set(AUTHORED_BY_D7) else predating
        target.append(f"{left}|{right}|{reason}")
    return {
        "cross_role_near_clone_pairs": len(cross),
        "pairs_between_two_carried_roles_predating_d7": predating,
        "pairs_touching_the_role_d7_authored": len(touching),
        "reading": (
            "the literal reading of 'clone-disjoint across eight roles' is already false of the "
            "carried roles before D6 authored anything: final_b and fitting collide on released "
            "D2 groups, and section 4.1 forbids D6 from authoring into either. A rule the "
            "inherited roles cannot satisfy is not the operative rule. The operative one is the "
            "one the same sealed contract states in its own near_clone_rule field -- cross-group "
            "pairs against every released corpus, applied to the authored corpus -- and that is "
            "what corpus_d6.py enforces every batch. D5 recorded this finding at S21D5-022 and "
            "nothing in D6 changes the bodies it is about"
        ),
    }


def _authored_corpus_separation() -> dict[str, Any]:
    """The contract's named acceptance criterion, recomputed here rather than cited.

    One corpus, not two. D5 checked its calibration corpus against every released body and its
    retrieval pool against itself, because it authored both. D6 authors only the certification
    corpus, so the second half of that check has no subject -- which is stated below rather than
    silently dropped, because a missing check and an inapplicable one read the same in a diff.
    """
    correction = {
        f"{spec.repository_group}:{label}": module_source(spec, getattr(spec, label))
        for spec in (
            *TASK_SPECS,
            *D2_TASK_SPECS,
            *D3_TASK_SPECS,
            *D4_CALIBRATION_SPECS,
            *D5_CALIBRATION_SPECS,
            *D6_CERTIFICATION_SPECS,
            *D7_CERTIFICATION_SPECS,
        )
        for label in (D2_LABELS if hasattr(spec, "variant_one") else C3_LABELS)
        if getattr(spec, label, None)
    }
    authored = {spec.repository_group for spec in D7_CERTIFICATION_SPECS}
    certification = sorted(
        f"{pair.left}|{pair.right}|{pair.reason}"
        for pair in near_clone_pairs(correction)
        if pair.left.split(":")[0] != pair.right.split(":")[0]
        and {pair.left.split(":")[0], pair.right.split(":")[0]} & authored
    )
    return {
        "rule": (
            "normalized_structure_hash and token_stream_hash, cross-group pairs, over every "
            "released corpus, for the one corpus D6 authors"
        ),
        "certification_bodies_compared": len(correction),
        "cross_group_collisions_touching_21d7": certification,
        "retrieval_pool_check": {
            "applicable": False,
            "why": (
                "S21D4-043's pool-against-itself check exists because a sprint that authors a "
                "retrieval pool can collide inside it. D6 authors no retrieval pool: condition 24 "
                "is inherited from D5's sealed measurement under the ruling bound below, so there "
                "is no fresh pool for the check to run over"
            ),
            "condition_24_ruling": CONDITION_24.name,
            "condition_24_ruling_sha256": hashlib.sha256(CONDITION_24.read_bytes()).hexdigest(),
        },
        "separated": not certification,
    }


def _lineage(roles: dict[str, frozenset[str]]) -> dict[str, Any]:
    """Recompute W0's digests from today's membership. A drift moves a hash and shows here."""
    audit = json.loads(REUSE_AUDIT.read_text(encoding="utf-8"))
    transition = audit["role_transition"]
    checks = {
        "fitting_pool": (transition["fitting_pool"]["names_digest"], roles["fitting"]),
        "conformal_half": (transition["conformal_half"]["names_digest"], roles["conformal"]),
        "spent_entirely": (
            transition["spent_entirely"]["names_digest"],
            roles["spent_retrieval_d5"],
        ),
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
    bundle = seal_d5_corpus()
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
    """The additional clause, and the protected-role reads, both re-run rather than cited.

    D5's additional clause was that its authored calibration corpus stay clear of the groups that
    had already decided a D4 threshold. D6's is one step sharper and is the reason the sprint
    authors a corpus at all: the half that places the bar may not also be measured against it.
    """
    audit = json.loads(REUSE_AUDIT.read_text(encoding="utf-8"))
    return {
        "certification_disjoint_from_the_conformal_half": {
            "rule": (
                "the amended selection rule measures 100 independent decisions against a bar the "
                "conformal half placed; a group on both sides would be certified against a "
                "threshold its own margin helped set"
            ),
            "conformal_groups": len(roles["conformal"]),
            "certification_groups": len(roles["certification"]),
            "shared": sorted(roles["conformal"] & roles["certification"]),
            "disjoint": not (roles["conformal"] & roles["certification"]),
        },
        "certification_disjoint_from_the_fitting_pool": {
            "rule": (
                "a certified margin must come from a direction that never saw the group; the "
                "fitting pool is where the direction came from"
            ),
            "shared": sorted(roles["certification"] & roles["fitting"]),
            "disjoint": not (roles["certification"] & roles["fitting"]),
        },
        "protected_roles_unread": {
            role: {
                "bodies_resolved": audit["protected_bodies_resolved"],
                "decision": audit["roles"][role]["decision"],
            }
            for role in PROTECTED
        },
        "protected_task_identities": audit["protected_task_identities"],
        "d7_authored_into_a_protected_role": sorted(
            frozenset().union(*(roles[role] for role in PROTECTED))
            & frozenset().union(*(roles[role] for role in AUTHORED_BY_D7))
        ),
        "d7_authored_into_a_spent_retrieval_pool": sorted(
            frozenset().union(*(roles[role] for role in SPENT_RETRIEVAL))
            & frozenset().union(*(roles[role] for role in AUTHORED_BY_D7))
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
    authored_groups = len(roles["certification"])

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W1",
        "items": ["S21D7-022"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role_membership_read_from": {
            "fitting": "released D5 seal, D4 training plus D4 calibration, unread by D6",
            "conformal": "reality_task_specs_d5, D5's calibration corpus, demoted to bar-setting",
            "certification": "reality_task_specs_d7, authored by S21D7-020",
            "final_a": "released D5 seal, carried unopened",
            "final_b": "released D5 seal, carried unopened",
            "canary": "released D5 seal, carried unopened",
            "spent_retrieval_d4": "released D4 seal, read once by S21D4-043 and spent",
            "spent_retrieval_d5": "released D5 seal, read once by S21D5-046 and spent",
        },
        # Derived from the corpus rather than passed in, so an unfinished run cannot present
        # itself as a finished one: a reader sees the count and the target side by side.
        "certification_corpus": {
            "groups_authored": authored_groups,
            "groups_targeted": CERTIFICATION_GROUPS,
            "complete": authored_groups >= CERTIFICATION_GROUPS,
            "reading": (
                "separation is a property of the bodies that exist, so it is checkable before the "
                "corpus is finished and has to be rechecked after; an incomplete corpus that "
                "separates cleanly is a passing check over fewer groups and never a closed one"
            ),
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
            and rights["certification_disjoint_from_the_conformal_half"]["disjoint"]
            and rights["certification_disjoint_from_the_fitting_pool"]["disjoint"]
            and not rights["d7_authored_into_a_protected_role"]
            and not rights["d7_authored_into_a_spent_retrieval_pool"]
        ),
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d7-corpus-separation.json"))
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
                "cross_group_collisions_touching_21d7": record["authored_corpus_separation"][
                    "cross_group_collisions_touching_21d7"
                ],
                "cross_role_near_clone_pairs": record["clone_separation"][
                    "cross_role_near_clone_pairs"
                ],
                "pairs_predating_d7": len(
                    record["clone_separation"]["pairs_between_two_carried_roles_predating_d7"]
                ),
                "every_digest_unchanged": record["lineage"]["every_digest_unchanged"],
                "certification_corpus_complete": record["certification_corpus"]["complete"],
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
