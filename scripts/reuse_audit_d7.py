"""S21D7-003 and S21D7-004. What D6's evidence becomes in D7, and what stays sealed.

Two items in one script for the reason [`reuse_audit_d6.py`](reuse_audit_d6.py) gives: they are
one question asked about two halves of the same corpus.

**S21D7-003 — the role transition.** D6's 100 *certification* groups become D7's **conformal**
evidence: the half that places the bar. That is the same one-step demotion D6 applied to D5's
calibration half, one sprint on, and §2.2a of the backlog rules it explicitly — a demoted half
may set a threshold and may never certify. The alternative, D5's calibration half, is recorded
here with the reason it was not taken rather than left unmentioned: under the containment class
it carries about six wrong decisions, where alpha = 0.20 collapses back onto the zero-error
prefix rule and the bar has no conformal content.

The 180-group fitting pool stays fitting evidence, and this is the sprint where that matters:
D7 fits a *new* direction on it. That is its licensed role and the reason it was never a
selection input. D6's retrieval pool is spent entirely and D7 authors no replacement.

**S21D7-004 — final, batch B and canary.** D3, D4, D5 and D6 each audited these `reuse` and
none opened them. A fifth reuse is a fifth claim, so it is proved again rather than inherited:
catalogues re-derived from the released generator, hashes recompared against the generator they
were carried from, and every store re-read for outcomes, predictions and body-access receipts —
now including D6's store, which holds a complete certification campaign and no protected access.

The audit surface stays narrow: sealed catalogue, root and access identities only.
`protected_bodies_resolved` is reported and must stay zero.

    UV_CACHE_DIR=.cache/uv uv run python scripts/reuse_audit_d7.py

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
#: Both of D6's stores join the list, and the second one is W0-F1: `cognitive_os_s21d6_measured`
#: is where D6's *measured* certification campaign ran, after its seal stage refused the trial
#: store. An audit that read only `cognitive_os_s21d6_test` would have proved zero protected
#: outcomes in the store where D6 did the least work.
STORES = (
    "cognitive_os_s21d2_test",
    "cognitive_os_s21d3_test",
    "cognitive_os_s21d4_test",
    "cognitive_os_s21d5_test",
    "cognitive_os_s21d6_test",
    "cognitive_os_s21d6_measured",
)

#: The shape D3 sealed and D4, D5 and D6 re-proved. A role that no longer matches it is replaced
#: whole.
CARRIED = {
    "final_a": {"groups": 30, "candidate_slots": 120},
    "final_b": {"groups": 30, "candidate_slots": 120},
    "canary": {"groups": 5, "candidate_slots": 20},
}

#: D6 role -> what it becomes in D7, and the sentence that permits it.
ROLE_TRANSITION = {
    "training": (
        "fitting",
        "the 180-group pool's licensed role is fitting and D7 uses it as one: the containment "
        "class is fitted on it once, in W2. It was never a selection input and does not become "
        "one",
    ),
    "calibration": (
        "conformal",
        "backlog §2.2a: D6's 100 certification decisions are spent by publication and demotable "
        "to exactly one further role, the bar-setting half. A demoted half may set a threshold "
        "and may never certify; D6 applied the same one-step demotion to D5's calibration half",
    ),
    "final_a": ("final_a", "carried unopened; S21D7-004 re-proves eligibility"),
    "final_b": ("final_b", "carried unopened; S21D7-004 re-proves eligibility"),
    "canary": ("canary", "carried unopened; S21D7-004 re-proves eligibility"),
}

#: The released D6 certification matrix the demoted half is rebuilt from, and the diagnostic
#: model hash W2 must reproduce before anything reads a margin. Repeated from the sealed
#: groundwork record so the two cannot drift silently.
CERTIFICATION_MATRIX = "747eb9664bbcfd3b0abb0859b74e58ec7fb46b9153bab904094b91cded3dcefc"
GROUNDWORK_MODEL_HASH = "d80160c4aa795fadd98fb4e6d4f64b7b29a2a3685c537454b8aff95daa124859"
HYPOTHESIS_CLASS = "containment-contrastive-linear-v1"
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
    from cognitive_os.learning.correction_catalogue_d6 import seal_d6_corpus

    out = {}
    for partition, entry in seal_d6_corpus().catalogues.items():
        out[partition.value] = {
            "groups": sorted(group.content_hash for group in entry.groups),
            "task_ids": sorted(str(group.task_id) for group in entry.groups),
            "names": sorted(group.repository_group for group in entry.groups),
            "candidate_slots": entry.candidate_slots,
        }
    return out


def _carried_agrees_with_the_d5_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """The carried roles must be the same groups in both released generators.

    D6's audit compared its D5-sourced carried roles against the D4 bundle; D7 compares the D6
    bundle against the D5 one it was carried from. Same failure this catches: two different
    corpora wearing one name.
    """
    from cognitive_os.learning.correction_catalogue_d5 import seal_d5_corpus

    d5 = seal_d5_corpus().catalogues
    out = {}
    for role in CARRIED:
        other = next((entry for partition, entry in d5.items() if partition.value == role), None)
        their_groups = sorted(group.content_hash for group in other.groups) if other else []
        out[role] = {
            "d6_bundle_digest": _digest(bundle[role]["groups"]),
            "d5_bundle_digest": _digest(their_groups),
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
    ruling = EVIDENCE / "sprint-21d7-condition-24-ruling.json"
    return {
        "groups": len(names),
        "names_digest": _digest(names),
        "d7_role": "none",
        "rule": (
            "the 60-group retrieval pool and its 60 queries were read once by S21D5-046 and are "
            "spent; D6 authored no replacement under its own inheritance ruling and neither does "
            "D7, whose renewed ruling rests on the same three identities"
        ),
        "condition_24": {
            "ruling": "inherited from D5's sealed measurement, conditionally, renewed for D7",
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
    carried_agreement = _carried_agrees_with_the_d5_bundle(bundle)

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
    d6_audit = EVIDENCE / "sprint-21d6-reuse-audit.json"

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W0",
        "items": ["S21D7-003", "S21D7-004"],
        "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "audit_surface": "sealed catalogue, root and access identities only",
        "role_transition": {
            "map": {
                role: {"d7_role": target, "rule": rule}
                for role, (target, rule) in ROLE_TRANSITION.items()
            },
            "conformal_half": {
                "role": "d6 certification",
                "groups": len(conformal_names),
                "outcomes": bundle["calibration"]["candidate_slots"],
                "names_digest": _digest(conformal_names),
                "spent_by": "publication in the D6 release; the full sweep over it is published",
                #: D6 read its own certification half once and published it. D7 does not
                #: re-execute it: the margins that place the bar are re-scored out of the sealed
                #: campaign under the direction W2 fits, so no outcome is produced a second time.
                "re_executed": False,
                "use": (
                    "the margins of its wrong answered decisions place the conformal bar, and "
                    "nothing else. It certifies no coverage, no error rate and no candidate"
                ),
                "read_through": {
                    "hypothesis_class": HYPOTHESIS_CLASS,
                    "direction": "fitted once in W2 on the 720-row pool; it does not pre-exist",
                    "groundwork_model_hash_to_reproduce": GROUNDWORK_MODEL_HASH,
                    "fitting_rows": FITTING_ROWS,
                    "certification_matrix": CERTIFICATION_MATRIX,
                    "refitted": False,
                    "note": (
                        "'refitted' is about this half: no direction is fitted on the conformal "
                        "half's rows. The class itself is fitted, once, on the fitting pool"
                    ),
                },
                "forbidden_in_d7": (
                    "any coverage, error-rate or selection claim; W1's authored certification "
                    "corpus must be disjoint from this digest and S21D7-022 proves it"
                ),
            },
            "the_alternative_half_not_taken": {
                "role": "d5 calibration",
                "spent_twice": "as D5's calibration, then as D6's bar-setting half",
                "wrong_decisions_under_the_new_class": "about 6",
                "why_not": (
                    "backlog §3.2: at m = 6 the finite-sample rank ceil((1-alpha)(m+1)) is 6 of "
                    "6, so alpha = 0.20 collapses back onto the zero-error prefix rule D5 "
                    "stopped on and the bar carries no conformal content. A third spend would "
                    "also be one demotion step further than any ruling has permitted"
                ),
            },
            "fitting_pool": {
                "role": "d6 training, carried from D5 unchanged",
                "groups": len(fitting_names),
                "outcomes": bundle["training"]["candidate_slots"],
                "names_digest": _digest(fitting_names),
                "d7_use": (
                    "the one licensed fitting use: W2 fits the containment direction on its 720 "
                    "rows once, seals it by content hash and reproduces it across a restart"
                ),
            },
            "spent_entirely": _retrieval_pool(every_catalogue_name),
            "d7_certification_corpus_present": False,
            "disjointness_check_deferred_to": "S21D7-022, after W1 authors the corpus",
            "why_the_halves_cannot_both_come_from_d6": (
                "§2.3 requires 100 independent decisions in the measured set and D6 authored "
                "exactly 100. A 50/50 split of them certifies 50, which fails a condition no "
                "ruling touches, so the certification half is authored fresh"
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
            "d6_selection_authorises_final_access": False,
            "d6_selection_stop_hash": (
                "648368477dd3a73c900c2a87486964322b4efeecc585048e4fe68146b1e06d56"
            ),
            "note": (
                "the D2 and D3 stores are empty for the reasons D4-W0-F1 records. D4's, D5's and "
                "D6's stores each hold a complete campaign, and it is their zero count for "
                "protected task identities that carries the claim. `evidence_records` is not "
                "required to be zero: each sprint legitimately wrote its own campaign's records, "
                "and none of them names a protected task"
            ),
        },
        "compared_against_the_d6_audit": {
            "source": d6_audit.name,
            "source_sha256": hashlib.sha256(d6_audit.read_bytes()).hexdigest(),
            "d6_decisions": {
                role: body["decision"]
                for role, body in json.loads(d6_audit.read_text(encoding="utf-8"))["roles"].items()
            },
        },
        "protected_bodies_resolved": 0,
        "individual_body_hashes_resolved": 0,
        "whole_role_replacement_contract": {
            "trigger": "any role failing shape, disjointness, generator agreement or zero-access",
            "partial_reuse_allowed": False,
            "procedure": (
                "author the whole affected role at S21D7-020, prove separation at S21D7-022 and "
                "seal it at S21D7-023, before any measurement"
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
    parser.add_argument("--output", default=str(EVIDENCE / "sprint-21d7-reuse-audit.json"))
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
