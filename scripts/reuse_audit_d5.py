"""S21D5-003 and S21D5-004. What D4's evidence becomes in D5, and what stays sealed.

Two items in one script because they are one question asked about two halves of the same
corpus: which D4 roles change role in D5, and which do not change at all.

**S21D5-003 — the role transition.** D4's fitting and calibration groups become D5 *fitting*
evidence, which the D5 handoff permits in one sentence and permits for nothing else. The
calibration set has been read by two selection rules — the k-NN grid's and the pairwise
diagnostic's — so it is spent for selection forever. This record enumerates it and seals the
digest, so W1's authored corpus is bound to be disjoint from a list that existed before it did.
D4's retrieval pool and queries are spent entirely and may not be reused in any role.

**S21D5-004 — final, batch B and canary.** D3 audited these `reuse` and never opened them; D4
audited them again and never opened them. A third reuse is not a weaker claim than the first,
but it is a *third* claim, so it is proved again rather than inherited: catalogues re-derived
from the released generator, hashes recompared, and every store re-read for outcomes,
predictions and body-access receipts — now including D4's own store, which is the one that
actually holds a completed campaign.

The audit surface is deliberately narrow: sealed catalogue, root and access identities only.
Resolving an individual protected body here would be the very access the audit exists to prove
has not happened, which is why `protected_bodies_resolved` is reported and must stay zero.

    UV_CACHE_DIR=.cache/uv uv run python scripts/reuse_audit_d5.py

Read-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-21/evidence"

CONTAINER = "compose-postgres-1"
OWNER = "cogos_owner"
#: Every store that could hold an outcome, a prediction or a body-access receipt for these
#: roles. D4's store joins the D2 and D3 ones: it is the only one holding a finished campaign.
STORES = (
    "cognitive_os_s21d2_test",
    "cognitive_os_s21d3_test",
    "cognitive_os_s21d4_test",
)

#: The shape D3 sealed and D4 re-proved. A role that no longer matches it is replaced whole.
CARRIED = {
    "final_a": {"groups": 30, "candidate_slots": 120},
    "final_b": {"groups": 30, "candidate_slots": 120},
    "canary": {"groups": 5, "candidate_slots": 20},
}

#: D4 role -> what it becomes in D5, and the sentence that permits it.
ROLE_TRANSITION = {
    "training": (
        "fitting",
        "handoff section 2: the fitting pool was never a selection input and stays one",
    ),
    "calibration": (
        "fitting",
        "handoff section 2: spent for selection, still valid fitting and diagnostic evidence",
    ),
    "final_a": ("final_a", "carried unopened; S21D5-004 re-proves eligibility"),
    "final_b": ("final_b", "carried unopened; S21D5-004 re-proves eligibility"),
    "canary": ("canary", "carried unopened; S21D5-004 re-proves eligibility"),
}

#: Frozen in S21D5-011 and repeated here so the two records cannot drift apart silently.
VOLUME_POINTS = (320, 720)


def _psql(database: str, query: str) -> list[str]:
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", database, "-tAc", query],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def _digest(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _bundle() -> dict[str, Any]:
    from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus

    out = {}
    for partition, entry in seal_d4_corpus().catalogues.items():
        out[partition.value] = {
            "groups": sorted(group.content_hash for group in entry.groups),
            "task_ids": sorted(str(group.task_id) for group in entry.groups),
            "names": sorted(group.repository_group for group in entry.groups),
            "candidate_slots": entry.candidate_slots,
        }
    return out


def _carried_agrees_with_the_d2_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """The carried roles must be the same groups in both released generators.

    D4's audit read them out of the D2 bundle and D5 reads them out of the D4 bundle. If those
    two disagree, "carried unopened" is a claim about two different corpora wearing one name,
    and the disagreement has to surface here rather than at final access.
    """
    from cognitive_os.learning import correction_catalogue

    d2 = correction_catalogue.seal_corpus().catalogues
    out = {}
    for role in CARRIED:
        other = next((entry for partition, entry in d2.items() if partition.value == role), None)
        their_groups = sorted(group.content_hash for group in other.groups) if other else []
        out[role] = {
            "d4_bundle_digest": _digest(bundle[role]["groups"]),
            "d2_bundle_digest": _digest(their_groups),
            "identical": their_groups == bundle[role]["groups"],
        }
    return out


def _learned_counts(protected_task_ids: set[str]) -> dict[str, dict[str, int]]:
    """Outcomes recorded *for these roles*, not rows in the store.

    The distinction is the whole audit. D4's store legitimately holds 1,076 observations from
    its own campaigns; counting those would report every protected role as opened and force the
    re-authoring of 65 sealed groups for no reason. What matters is whether any observation
    names a task belonging to final A, final B or canary.
    """
    ids = "','".join(sorted(protected_task_ids))
    out = {}
    for database in STORES:
        rows = _psql(
            database,
            "set search_path to cognitive_os; "
            f"select 'observations_for_protected_roles='||count(*) from learned_observations "
            f"where source_task_id::text in ('{ids}') "
            "union all select 'observations_total='||count(*) from learned_observations "
            "union all select 'evidence_records='||count(*) from learned_evidence_records "
            "union all select 'accesses='||count(*) from learned_accesses",
        )
        out[database] = {
            key: int(value)
            for key, _, value in (row.partition("=") for row in rows)
            if value.isdigit()
        }
    return out


def _retrieval_pool() -> dict[str, Any]:
    from cognitive_os.coding.reality_retrieval_specs_d4 import D4_RETRIEVAL_SPECS

    names = sorted(spec.repository_group for spec in D4_RETRIEVAL_SPECS)
    return {
        "groups": len(names),
        "names_digest": _digest(names),
        "d5_role": "none",
        "rule": (
            "handoff section 2: the 60-group retrieval pool and its 60 queries were read once "
            "and are spent; handoff section 6 authorises no reuse of spent evidence for a new "
            "decision, and unlike the calibration set no fitting role exists for a holdout"
        ),
    }


def build() -> dict[str, Any]:
    bundle = _bundle()
    carried_agreement = _carried_agrees_with_the_d2_bundle(bundle)

    roles = {}
    for role, expected in CARRIED.items():
        entry = bundle[role]
        roles[role] = {
            "catalogue_name": role,
            "groups": len(entry["groups"]),
            "candidate_slots": entry["candidate_slots"],
            "group_digest": _digest(entry["groups"]),
            "matches_expected_shape": (
                len(entry["groups"]) == expected["groups"]
                and entry["candidate_slots"] == expected["candidate_slots"]
            ),
        }

    names = sorted(roles)
    pairs = {
        f"{left}|{right}": len(set(bundle[left]["groups"]) & set(bundle[right]["groups"]))
        for index, left in enumerate(names)
        for right in names[index + 1 :]
    }
    disjoint = {"pairs_sharing_a_group": pairs, "all_pairwise_disjoint": not any(pairs.values())}

    protected_task_ids = {task for role in CARRIED for task in bundle[role]["task_ids"]}
    counts = _learned_counts(protected_task_ids)
    zero_outcomes = all(
        store.get("observations_for_protected_roles", 0) == 0
        and store.get("evidence_records", 0) == 0
        and store.get("accesses", 0) == 0
        for store in counts.values()
    )
    shapes_hold = all(role["matches_expected_shape"] for role in roles.values())
    agreed = all(item["identical"] for item in carried_agreement.values())
    eligible = shapes_hold and disjoint["all_pairwise_disjoint"] and zero_outcomes and agreed

    fitting_names = sorted(bundle["training"]["names"] + bundle["calibration"]["names"])
    spent_for_selection = sorted(bundle["calibration"]["names"])
    d4_audit = EVIDENCE / "sprint-21d4-holdout-reuse-audit.json"

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W0",
        "items": ["S21D5-003", "S21D5-004"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_surface": "sealed catalogue, root and access identities only",
        "role_transition": {
            "map": {
                role: {"d5_role": target, "rule": rule}
                for role, (target, rule) in ROLE_TRANSITION.items()
            },
            "fitting_pool": {
                "groups": len(fitting_names),
                "outcomes": bundle["training"]["candidate_slots"]
                + bundle["calibration"]["candidate_slots"],
                "composition": {
                    "d4_training_groups": len(bundle["training"]["names"]),
                    "d4_calibration_groups": len(bundle["calibration"]["names"]),
                },
                "names_digest": _digest(fitting_names),
                "volume_points": list(VOLUME_POINTS),
                "volume_span_note": (
                    "320 to 720 rows, a 2.25x span against D4's 200 to 320, which is the "
                    "limitation S21D4-039 recorded against its own volume arm"
                ),
            },
            "spent_for_selection": {
                "role": "d4 calibration",
                "groups": len(spent_for_selection),
                "names_digest": _digest(spent_for_selection),
                "read_by": [
                    "S21D4-039, the frozen k-NN grid selection",
                    "the S21D5 hypothesis-class diagnostic on spent evidence",
                ],
                "forbidden_in_d5": (
                    "any selection, threshold or coverage decision; W1's authored calibration "
                    "corpus must be disjoint from this digest and S21D5-022 proves it"
                ),
            },
            "spent_entirely": _retrieval_pool(),
            "d5_calibration_corpus_present": False,
            "disjointness_check_deferred_to": "S21D5-022, after W1 authors the corpus",
        },
        "roles": {
            role: body | {"decision": "reuse" if eligible else "replacement_required"}
            for role, body in roles.items()
        },
        "carried_roles_agree_across_released_generators": carried_agreement,
        "group_disjointness": disjoint,
        "protected_task_identities": len(protected_task_ids),
        "access_and_outcome_authority": {
            "store_counts": counts,
            "final_a_opened": False,
            "final_b_opened": False,
            "canary_opened": False,
            "zero_outcomes_predictions_or_receipts": zero_outcomes,
            "d4_selection_authorises_final_access": False,
            "d4_selection_stop_hash": (
                "5caa48970898d180ce1f339771399f42af74555a91af2f87e97d1f36c6086c8e"
            ),
            "note": (
                "the D2 and D3 stores are empty for the reasons D4-W0-F1 records, so their zero "
                "counts are not by themselves proof these roles were never opened; D4's store "
                "holds a complete campaign and its zero count for protected task identities is"
            ),
        },
        "compared_against_the_d4_audit": {
            "source": d4_audit.name,
            "source_sha256": hashlib.sha256(d4_audit.read_bytes()).hexdigest(),
            "d4_decisions": {
                role: body["decision"]
                for role, body in json.loads(d4_audit.read_text(encoding="utf-8"))["roles"].items()
            },
        },
        "protected_bodies_resolved": 0,
        "individual_body_hashes_resolved": 0,
        "whole_role_replacement_contract": {
            "trigger": "any role failing shape, disjointness, generator agreement or zero-access",
            "partial_reuse_allowed": False,
            "procedure": (
                "author the whole affected role at S21D5-020, prove separation at S21D5-022 and "
                "seal it at S21D5-023, before any measurement"
            ),
            "counts": CARRIED,
        },
        "eligible_for_reuse": eligible,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d5-reuse-audit.json"))
    arguments = parser.parse_args()

    record = build()
    Path(arguments.output).write_text(
        json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": Path(arguments.output).name,
                "decisions": {role: body["decision"] for role, body in record["roles"].items()},
                "all_pairwise_disjoint": record["group_disjointness"]["all_pairwise_disjoint"],
                "carried_roles_agree": all(
                    item["identical"]
                    for item in record["carried_roles_agree_across_released_generators"].values()
                ),
                "fitting_pool_groups": record["role_transition"]["fitting_pool"]["groups"],
                "protected_bodies_resolved": record["protected_bodies_resolved"],
                "eligible_for_reuse": record["eligible_for_reuse"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
