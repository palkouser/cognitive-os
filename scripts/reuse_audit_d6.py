"""S21D6-003 and S21D6-004. What D5's evidence becomes in D6, and what stays sealed.

Two items in one script for the reason [`reuse_audit_d5.py`](reuse_audit_d5.py) gives: they are
one question asked about two halves of the same corpus.

**S21D6-003 — the role transition.** D5's 100 calibration groups become D6's **conformal**
evidence: the half that places the bar. That is a threshold-setting use, which is what a spent
calibration role is licensed for — D4's calibration became D5's fitting pool under the same
principle one step earlier. It is emphatically *not* a certifying use, and this record seals the
digest so W1's authored certification corpus is bound to be disjoint from a list that existed
before it did. D5's 180-group fitting pool stays fitting evidence and is read only through the
sealed direction it already produced. D5's retrieval pool is spent entirely.

**S21D6-004 — final, batch B and canary.** D3, D4 and D5 each audited these `reuse` and none
opened them. A fourth reuse is a fourth claim, so it is proved again rather than inherited:
catalogues re-derived from the released generator, hashes recompared, and every store re-read for
outcomes, predictions and body-access receipts — now including D5's store, which holds a complete
calibration campaign and no protected-role access.

The audit surface stays narrow: sealed catalogue, root and access identities only.
`protected_bodies_resolved` is reported and must stay zero.

    UV_CACHE_DIR=.cache/uv uv run python scripts/reuse_audit_d6.py

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
#: Every store that could hold an outcome, a prediction or a body-access receipt for these roles.
#: D5's store joins the list: it is the one holding the most recent finished campaign.
STORES = (
    "cognitive_os_s21d2_test",
    "cognitive_os_s21d3_test",
    "cognitive_os_s21d4_test",
    "cognitive_os_s21d5_test",
)

#: The shape D3 sealed and D4 and D5 re-proved. A role that no longer matches it is replaced whole.
CARRIED = {
    "final_a": {"groups": 30, "candidate_slots": 120},
    "final_b": {"groups": 30, "candidate_slots": 120},
    "canary": {"groups": 5, "candidate_slots": 20},
}

#: D5 role -> what it becomes in D6, and the sentence that permits it.
ROLE_TRANSITION = {
    "training": (
        "fitting",
        "the D5 fitting pool was never a selection input and stays one; D6 refits nothing and "
        "reads it only through the direction it already produced",
    ),
    "calibration": (
        "conformal",
        "backlog §4.1: a spent calibration role is licensed for threshold-setting, which is what "
        "the conformal half is, and never for certifying; D4's calibration became D5's fitting "
        "pool under the same principle",
    ),
    "final_a": ("final_a", "carried unopened; S21D6-004 re-proves eligibility"),
    "final_b": ("final_b", "carried unopened; S21D6-004 re-proves eligibility"),
    "canary": ("canary", "carried unopened; S21D6-004 re-proves eligibility"),
}

#: The one cell revision 6 pre-registers, repeated here so the two records cannot drift silently.
SELECTED_DIRECTION = "9fd297fb407015374485e8f7ef8fbb557e6f89f7ac3286e2572769fdab937d74"
FITTING_ROWS = 720


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
    from cognitive_os.learning.correction_catalogue_d5 import seal_d5_corpus

    out = {}
    for partition, entry in seal_d5_corpus().catalogues.items():
        out[partition.value] = {
            "groups": sorted(group.content_hash for group in entry.groups),
            "task_ids": sorted(str(group.task_id) for group in entry.groups),
            "names": sorted(group.repository_group for group in entry.groups),
            "candidate_slots": entry.candidate_slots,
        }
    return out


def _carried_agrees_with_the_d4_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """The carried roles must be the same groups in both released generators.

    D5's audit compared its D4-sourced carried roles against the D2 bundle; D6 compares the D5
    bundle against the D4 one it was carried from. Same failure this catches: two different
    corpora wearing one name.
    """
    from cognitive_os.learning.correction_catalogue_d4 import seal_d4_corpus

    d4 = seal_d4_corpus().catalogues
    out = {}
    for role in CARRIED:
        other = next((entry for partition, entry in d4.items() if partition.value == role), None)
        their_groups = sorted(group.content_hash for group in other.groups) if other else []
        out[role] = {
            "d5_bundle_digest": _digest(bundle[role]["groups"]),
            "d4_bundle_digest": _digest(their_groups),
            "identical": their_groups == bundle[role]["groups"],
        }
    return out


def _learned_counts(protected_task_ids: set[str]) -> dict[str, dict[str, int]]:
    """Outcomes recorded *for these roles*, not rows in the store."""
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


def _retrieval_pool(bundle_names: list[str]) -> dict[str, Any]:
    from cognitive_os.coding.reality_retrieval_specs_d5 import D5_RETRIEVAL_SPECS

    names = sorted(spec.repository_group for spec in D5_RETRIEVAL_SPECS)
    ruling = EVIDENCE / "sprint-21d6-condition-24-ruling.json"
    return {
        "groups": len(names),
        "names_digest": _digest(names),
        "d6_role": "none",
        "rule": (
            "the 60-group retrieval pool and its 60 queries were read once by S21D5-046 and are "
            "spent; no fitting role exists for a holdout, and D6 authors no replacement because "
            "condition 24 is inherited rather than re-measured"
        ),
        "condition_24": {
            "ruling": "inherited from D5's sealed measurement, conditionally",
            "record": ruling.name,
            "record_sha256": hashlib.sha256(ruling.read_bytes()).hexdigest()
            if ruling.exists()
            else None,
            "authored_groups_saved": 60,
        },
        "disjoint_from_every_catalogue_role": not (set(names) & set(bundle_names)),
    }


def build() -> dict[str, Any]:
    bundle = _bundle()
    carried_agreement = _carried_agrees_with_the_d4_bundle(bundle)

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
        store.get("observations_for_protected_roles", 0) == 0 and store.get("accesses", 0) == 0
        for store in counts.values()
    )
    shapes_hold = all(role["matches_expected_shape"] for role in roles.values())
    agreed = all(item["identical"] for item in carried_agreement.values())
    eligible = shapes_hold and disjoint["all_pairwise_disjoint"] and zero_outcomes and agreed

    conformal_names = sorted(bundle["calibration"]["names"])
    fitting_names = sorted(bundle["training"]["names"])
    every_catalogue_name = sorted(name for entry in bundle.values() for name in entry["names"])
    d5_audit = EVIDENCE / "sprint-21d5-reuse-audit.json"

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W0",
        "items": ["S21D6-003", "S21D6-004"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_surface": "sealed catalogue, root and access identities only",
        "role_transition": {
            "map": {
                role: {"d6_role": target, "rule": rule}
                for role, (target, rule) in ROLE_TRANSITION.items()
            },
            "conformal_half": {
                "role": "d5 calibration",
                "groups": len(conformal_names),
                "outcomes": bundle["calibration"]["candidate_slots"],
                "names_digest": _digest(conformal_names),
                "wrong_answered_decisions_at_720": 12,
                #: D5 re-executed its inherited fitting pool under new run identities. D6 does
                #: not re-execute anything: the outcomes are read out of the sealed campaign, so
                #: the margins that place the bar are the margins D5 sealed, not new ones.
                "re_executed": False,
                "use": (
                    "the margins of its wrong answered decisions place the conformal bar, and "
                    "nothing else. It certifies no coverage, no error rate and no candidate"
                ),
                "read_through": {
                    "direction": SELECTED_DIRECTION,
                    "fitting_rows": FITTING_ROWS,
                    "calibration_matrix": (
                        "106061126df8326128a5fea97b3690f5f02465c16805e6742c09cd5e3e7c7ca4"
                    ),
                    "refitted": False,
                },
                "forbidden_in_d6": (
                    "any coverage, error-rate or selection claim; W1's authored certification "
                    "corpus must be disjoint from this digest and S21D6-022 proves it"
                ),
            },
            "fitting_pool": {
                "role": "d5 fitting",
                "groups": len(fitting_names),
                "outcomes": bundle["training"]["candidate_slots"],
                "names_digest": _digest(fitting_names),
                "d6_use": (
                    "none directly; the direction fitted on it is read out of the sealed matrices "
                    "and rehashed, and no row of it is re-executed"
                ),
            },
            "spent_entirely": _retrieval_pool(every_catalogue_name),
            "d6_certification_corpus_present": False,
            "disjointness_check_deferred_to": "S21D6-022, after W1 authors the corpus",
            "why_the_halves_cannot_both_come_from_d5": (
                "§2.3 requires 100 independent decisions in the measured set and D5 authored "
                "exactly 100. A 50/50 split of them certifies 50, which fails a condition the "
                "amendment does not touch, so the certification half is authored fresh"
            ),
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
            "d5_selection_authorises_final_access": False,
            "d5_selection_stop_hash": (
                "4d45fc00188c00cafd7a95fe4bad8c338150a6d203b2d2c5cf10aa1d413c8ae2"
            ),
            "note": (
                "the D2 and D3 stores are empty for the reasons D4-W0-F1 records. D4's and D5's "
                "stores each hold a complete campaign, and it is their zero count for protected "
                "task identities that carries the claim. `evidence_records` is not required to "
                "be zero: D5 legitimately wrote its own campaign's records, and none of them "
                "names a protected task"
            ),
        },
        "compared_against_the_d5_audit": {
            "source": d5_audit.name,
            "source_sha256": hashlib.sha256(d5_audit.read_bytes()).hexdigest(),
            "d5_decisions": {
                role: body["decision"]
                for role, body in json.loads(d5_audit.read_text(encoding="utf-8"))["roles"].items()
            },
        },
        "protected_bodies_resolved": 0,
        "individual_body_hashes_resolved": 0,
        "whole_role_replacement_contract": {
            "trigger": "any role failing shape, disjointness, generator agreement or zero-access",
            "partial_reuse_allowed": False,
            "procedure": (
                "author the whole affected role at S21D6-020, prove separation at S21D6-022 and "
                "seal it at S21D6-023, before any measurement"
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
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d6-reuse-audit.json"))
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
                "conformal_half_groups": record["role_transition"]["conformal_half"]["groups"],
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
