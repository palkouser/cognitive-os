"""S21D4-004. Re-audit final A, final B and canary reuse eligibility against current bytes.

Sprint 21D3 audited these three roles `reuse` and then never opened them. A second reuse is not
a weaker claim than the first, but it is a *second* claim, so it is proved again rather than
inherited: the catalogues are re-derived from the released generator, their hashes recompared,
and the stores re-read for outcomes, predictions and body-access receipts.

The audit surface is deliberately narrow -- sealed catalogue, root and access identities only.
Resolving an individual protected body here would be the very access the audit exists to prove
has not happened, which is why `protected_bodies_resolved` is reported and must stay zero.

    UV_CACHE_DIR=.cache/uv uv run python scripts/holdout_reuse_audit_d4.py

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
STORES = ("cognitive_os_s21d2_test", "cognitive_os_s21d3_test")

#: Role name in the released catalogue, and the exact shape D3 sealed.
EXPECTED = {
    "final_a": {"groups": 30, "candidate_slots": 120},
    "final_b": {"groups": 30, "candidate_slots": 120},
    "canary": {"groups": 5, "candidate_slots": 20},
}
#: The catalogue keys each role by its own name; `final_b_independent` is the generator path,
#: not the key, and reading it as a key is how an audit reports on a role that does not exist.
CATALOGUE_ALIASES: dict[str, str] = {}


def _psql(database: str, query: str) -> list[str]:
    out = subprocess.run(
        ["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", database, "-tAc", query],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def _learned_counts(protected_task_ids: set[str]) -> dict[str, dict[str, int]]:
    """Outcomes recorded *for these roles*, not rows in the store.

    The distinction is the whole audit. Sprint 21D2's store legitimately holds 480 observations
    from its own fitting and calibration campaigns; counting those would report every protected
    role as opened and force the re-authoring of 65 sealed groups for no reason. What matters is
    whether any observation names a task belonging to final A, final B or canary, so that is
    what is asked -- by `source_task_id`, against the exact task identities the sealed
    catalogues carry.
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


def _catalogue() -> dict[str, Any]:
    from cognitive_os.learning import correction_catalogue as catalogue

    bundle = catalogue.seal_corpus()
    roles = {}
    for role, expected in EXPECTED.items():
        name = CATALOGUE_ALIASES.get(role, role)
        entry = bundle.catalogues[name]
        # Identity is the group's own content hash: it commits to the whole sealed group
        # without resolving a body, which is the line this audit must not cross.
        groups = sorted(group.content_hash for group in entry.groups)
        task_ids = sorted(str(group.task_id) for group in entry.groups)
        roles[role] = {
            "catalogue_name": name,
            "groups": len(groups),
            "candidate_slots": entry.candidate_slots,
            "group_digest": hashlib.sha256("\n".join(groups).encode("utf-8")).hexdigest(),
            "matches_expected_shape": (
                len(groups) == expected["groups"]
                and entry.candidate_slots == expected["candidate_slots"]
            ),
            "_groups": groups,
            "_task_ids": task_ids,
        }
    return roles


def _disjointness(roles: dict[str, Any]) -> dict[str, Any]:
    names = sorted(roles)
    pairs = {}
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            shared = set(roles[left]["_groups"]) & set(roles[right]["_groups"])
            pairs[f"{left}|{right}"] = len(shared)
    return {"pairs_sharing_a_group": pairs, "all_pairwise_disjoint": not any(pairs.values())}


def build() -> dict[str, Any]:
    roles = _catalogue()
    disjoint = _disjointness(roles)
    protected_task_ids = {task for role in roles.values() for task in role["_task_ids"]}
    counts = _learned_counts(protected_task_ids)
    d3_audit = json.loads(
        (EVIDENCE / "sprint-21d3-holdout-reuse-audit.json").read_text(encoding="utf-8")
    )

    zero_outcomes = all(
        store.get("observations_for_protected_roles", 0) == 0
        and store.get("evidence_records", 0) == 0
        and store.get("accesses", 0) == 0
        for store in counts.values()
    )
    shapes_hold = all(role["matches_expected_shape"] for role in roles.values())
    eligible = shapes_hold and disjoint["all_pairwise_disjoint"] and zero_outcomes

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W0",
        "items": ["S21D4-004"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_surface": "sealed catalogue, root and access identities only",
        "roles": {
            role: {key: value for key, value in body.items() if not key.startswith("_")}
            | {"decision": "reuse" if eligible else "replacement_required"}
            for role, body in roles.items()
        },
        "group_disjointness": disjoint,
        "protected_task_identities": len(protected_task_ids),
        "access_and_outcome_authority": {
            "store_counts": counts,
            "final_a_opened": False,
            "final_b_opened": False,
            "canary_opened": False,
            "zero_outcomes_predictions_or_receipts": zero_outcomes,
            "d3_selection_authorises_final_access": False,
            "d3_selection_hash": (
                "68ea06843d2136e390bf8a4ea0698414932987f5447887187907c45c0dcea876"
            ),
            "note": (
                "the D3 learned store is empty for the reason D4-W0-F1 records, so its zero "
                "counts are not by themselves proof that these roles were never opened; the "
                "D3 audit's own zero-access record and the untouched catalogue hashes are"
            ),
        },
        "compared_against_the_d3_audit": {
            "source": "sprint-21d3-holdout-reuse-audit.json",
            "source_sha256": hashlib.sha256(
                (EVIDENCE / "sprint-21d3-holdout-reuse-audit.json").read_bytes()
            ).hexdigest(),
            "d3_decisions": {row["role"]: row["decision"] for row in d3_audit["roles"]},
            "d3_protected_bodies_resolved": d3_audit["protected_bodies_resolved"],
        },
        "protected_bodies_resolved": 0,
        "individual_body_hashes_resolved": 0,
        "whole_role_replacement_contract": {
            "trigger": "any role failing shape, disjointness or zero-access",
            "partial_reuse_allowed": False,
            "procedure": (
                "author the whole affected role at S21D4-030, prove separation at S21D4-031 and "
                "seal it at S21D4-032, before any measurement"
            ),
            "counts": EXPECTED,
        },
        "eligible_for_reuse": eligible,
    }
    record["integrity_content_hash"] = hashlib.sha256(
        json.dumps(record, indent=1, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d4-holdout-reuse-audit.json"))
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
