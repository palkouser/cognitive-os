#!/usr/bin/env python
"""S21D5-091: the twenty-nine Gate L2 conditions and Gate D1's three, decided by evidence.

    scripts/gate_assessment_d5.py [--output docs/.../sprint-21d5-gate-l2.json] [--markdown]

Every condition is a row, and every row names the file and the rule that decided it. A condition
with no bearing evidence is `not_opened` bound to the stop hash that closed it, never `met` —
**this script cannot assert a pass, only read one.** There is no branch below that writes `met`
without a document behind it, no default that upgrades a missing file, and the verdict is
computed from the counts rather than stated.

Six states, and this sprint uses four of them:

* `met` — the evidence exists and the rule holds;
* `met_as_rejection` — the rule was applied and the recorded no is what the condition asked for.
  **D4 used this for condition 24 and D5 does not**: the floors were measured again on a fresh
  holdout and the `lexical` arm cleared both, so 24 is `met` on a measurement rather than on a
  refusal to reopen;
* `not_opened` — a stop closed it, and the row names the stop hash. Fifteen conditions, bound to
  S21D5-035's null selection under §3.3 step 5;
* `pending` — the evidence does not exist *yet* and will after the protected release. Only
  condition 29 is ever this, and the gate-close regeneration is what turns it into `met`;
* `failed` — evidence exists and the rule does not hold;
* `carried` — a predecessor's evidence reused unchanged. **Never used here.** §2.2 is explicit
  that D5 inherits no pass from D4, so the state exists in the vocabulary and the record reports
  a count of zero for it rather than leaving a reader to wonder whether it was an option.

`not_opened` is not a soft `met`. The gate passes only when every applicable condition is met,
which is why a sprint with zero failures and one more met condition than its predecessor still
does not pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.learning.integrity_d5 import REQUIRED_SCANS

REPOSITORY = Path(__file__).resolve().parent.parent
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"

MET = "met"
MET_AS_REJECTION = "met_as_rejection"
CARRIED = "carried"
NOT_OPENED = "not_opened"
PENDING = "pending"
FAILED = "failed"

#: The stop that closed every conditional condition, and where it is written down.
SELECTION = "sprint-21d5-learner-selection.json"
STOP_SOURCE = "S21D5-035 null candidate selection under §3.3 step 5, selective_margin_bound"

#: The retrieval branch reached its own result, and this sprint's is a pass.
RETRIEVAL_DECISION = "sprint-21d5-retrieval-decision.json"

#: The floors §2.4 froze, unchanged from D4. Named here so condition 24's row reads them rather
#: than repeating whatever the decision record happens to say about itself.
RECALL_FLOOR = "0.70"
MRR_FLOOR = "0.50"


@dataclass(frozen=True, slots=True)
class Bearing:
    """Which produced evidence bears on one condition, and what decides it.

    Written out per condition rather than inferred. The frozen contract declares what the
    *positive* path would have produced and most of those files do not exist, so naming the file
    that actually bears on the condition is the whole content of this assessment.
    """

    source: str
    rule: str
    decide: Callable[[dict[str, Any]], tuple[str, str]]


def _read(name: str) -> dict[str, Any] | None:
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _sha256(name: str) -> str | None:
    path = EVIDENCE / name
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _dataset(document: dict[str, Any], partition: str) -> dict[str, Any]:
    return next(item for item in document["datasets"] if item["partition"] == partition)


def _yes(detail: str) -> tuple[str, str]:
    return MET, detail


def _no(detail: str) -> tuple[str, str]:
    return FAILED, detail


# --------------------------------------------------------------- the conditions that were opened


def _condition_1(document: dict[str, Any]) -> tuple[str, str]:
    release = document["d4_release"]
    agrees = release["local_tag_object"] == release["remote_tag_object"]
    agrees = agrees and release["local_peeled_commit"] == release["remote_peeled_commit"]
    detail = (
        f"the D4 tag object {str(release['local_tag_object'])[:16]} peels to "
        f"{str(release['local_peeled_commit'])[:16]}, and the local and remote handles agree"
    )
    return _yes(detail) if agrees else _no("the local and remote D4 release handles disagree")


def _condition_2(document: dict[str, Any]) -> tuple[str, str]:
    stores = document["predecessor_artifact_stores"]
    drifted = document["drifted_stores"]
    clean = not drifted and document["zero_predecessor_writes"] and stores
    detail = (
        f"{len(stores)} predecessor stores re-fingerprinted after the wave against "
        f"{document['compared_against']}; none drifted and zero writes reached one"
    )
    return _yes(detail) if clean else _no(f"predecessor stores that drifted: {sorted(drifted)}")


def _condition_3(document: dict[str, Any]) -> tuple[str, str]:
    """D5's form: the role transition audited from the predecessors' own evidence.

    D2 recorded D1's erratum, D3 reconciled D2's denominators, D4 recomputed D3's replica
    identity. D4 published no erratum, so what D5 owes this condition is the other half of the
    same obligation: every role it reuses is read out of the predecessor's released audit and
    agrees with it, and no protected body is modified to make the reuse work.
    """
    transition = document["role_transition"]
    against = document["compared_against_the_d4_audit"]
    agreement = document["carried_roles_agree_across_released_generators"]
    access = document["access_and_outcome_authority"]
    pool = transition["fitting_pool"]

    disagreeing = sorted(
        role for role, comparison in agreement.items() if not comparison["identical"]
    )
    opened = sorted(key for key in ("canary", "final_a", "final_b") if access[f"{key}_opened"])
    # Zero is the correct value for both, and the reason is the audit surface: it reads sealed
    # catalogues, roots and access identities, and never opens a protected body. A row that
    # required these to be non-zero would fail on exactly the state the audit exists to produce.
    untouched = (
        document["protected_bodies_resolved"] == 0
        and document["individual_body_hashes_resolved"] == 0
        and document["audit_surface"] == "sealed catalogue, root and access identities only"
    )
    clean = (
        document["eligible_for_reuse"]
        and document["group_disjointness"]["all_pairwise_disjoint"]
        and agreement
        and not disagreeing
        and not opened
        and untouched
        and access["zero_outcomes_predictions_or_receipts"]
    )
    detail = (
        f"the {pool['groups']}-group fitting pool is {pool['composition']['d4_training_groups']} "
        f"D4 training and {pool['composition']['d4_calibration_groups']} D4 calibration groups, "
        f"read from {against['source']} at {str(against['source_sha256'])[:12]}; "
        f"{len(agreement)} carried roles reproduce their released bundle digests, "
        f"{document['protected_task_identities']} protected task identities were resolved by "
        "identity alone, and zero protected bodies were opened"
    )
    if clean:
        return _yes(detail)
    return _no(
        f"roles disagreeing with the D4 audit {disagreeing}; protected roles opened {opened}; "
        f"the audit read {document['audit_surface']!r}"
    )


def _condition_4(document: dict[str, Any]) -> tuple[str, str]:
    measured = document["measured_values"]
    return (
        _yes(f"revision 5 published with measured_values: {measured}")
        if measured == 0
        else _no(f"the pre-registration already carried {measured} measured values")
    )


def _condition_5(document: dict[str, Any]) -> tuple[str, str]:
    execution = document["execution"]
    attempted = int(execution["candidate_runs"])
    verified = int(execution["hidden_passed"]) + int(execution["hidden_failed"])
    return (
        _yes(f"all {attempted} candidate runs carry an independent hidden-verifier label")
        if attempted and verified == attempted
        else _no(f"{verified} of {attempted} attempted candidates were independently verified")
    )


def _condition_6(document: dict[str, Any]) -> tuple[str, str]:
    """The scan set is named by `integrity_d5`, not read out of the record being assessed.

    D4's snapshot record declared `scans.required` beside `scans.count` and this row compared
    them. D5's does not, and a row that fell back to `count` would compare a number with itself
    — S21D5-W7-A1 is the same defect caught in the integrity class.
    """
    scans = document["scans"]
    ran = {str(item["name"]) for item in scans["results"]}
    forbidden = next(
        item for item in scans["results"] if item["name"] == "no_forbidden_field_reaches_the_matrix"
    )
    missing = sorted(REQUIRED_SCANS - ran)
    clean = forbidden["passed"] and not scans["failed"] and not missing and scans["all_passed"]
    return (
        _yes(f"{forbidden['detail']}; all {len(REQUIRED_SCANS)} required scans passed")
        if clean
        else _no(f"scans that failed: {scans['failed']}; scans that never ran: {missing}")
    )


def _condition_7(document: dict[str, Any]) -> tuple[str, str]:
    separation = document["group_separation"]
    shared = sum(separation["pairs_sharing_a_group"].values())
    distinct = separation["distinct_groups"] == separation["groups_total"]
    clean = separation["all_pairwise_disjoint"] and not shared and distinct
    detail = (
        f"{len(separation['roles'])} roles over {separation['groups_total']} groups, all "
        f"pairwise disjoint; {separation['pairs_checked']} role pairs share zero groups"
    )
    return _yes(detail) if clean else _no(f"{shared} role pairs share a group")


def _condition_8(document: dict[str, Any]) -> tuple[str, str]:
    fitting = _dataset(document, "training")
    calibration = _dataset(document, "calibration")
    floors = fitting["members"] >= 200 and fitting["groups"] >= 50
    floors = floors and calibration["members"] >= 40 and calibration["groups"] >= 10
    detail = (
        f"{fitting['members']} fitting observations over {fitting['groups']} groups and "
        f"{calibration['members']} calibration observations over {calibration['groups']} groups"
    )
    return _yes(detail) if floors else _no(detail)


def _condition_9(document: dict[str, Any]) -> tuple[str, str]:
    runs = {
        item["partition"]: item["real_governed_runs"]
        for item in document["datasets"]
        if item["partition"] in {"training", "calibration"}
    }
    return (
        _yes(f"zero REAL_GOVERNED_RUN observations in fitting and calibration: {runs}")
        if runs and not any(runs.values())
        else _no(f"real governed runs reached a fitting or calibration split: {runs}")
    )


def _condition_12(document: dict[str, Any]) -> tuple[str, str]:
    baseline = document["baseline"]
    grid = document["grid"]
    reported = grid["cells_reported"] == len(grid["volume_points"])
    return (
        _yes(
            f"the strongest deterministic rung is {baseline['strongest_deterministic_rung']} at "
            f"{baseline['first_choice_rate']}, measured on the same decisions; all "
            f"{grid['cells_reported']} cells and {grid['sweep_points_reported']} sweep points "
            "are reported, including the ones that are not selectable"
        )
        if reported and grid["sweep_points_reported"]
        else _no(f"{grid['cells_reported']} of {len(grid['volume_points'])} cells reported")
    )


def _condition_17(document: dict[str, Any]) -> tuple[str, str]:
    """Read from the twelve-class report the operations run made with both authorities."""
    report = document["restore"]["evidence_report_on_the_restored_copy"]
    independence = next(
        item for item in report["classes"] if item["class"] == "decision_independence"
    )
    return (
        _yes(independence["detail"])
        if independence["state"] == "clean"
        else _no(independence["detail"])
    )


def _condition_24(document: dict[str, Any]) -> tuple[str, str]:
    """D4 recorded this as a rejection. D5 measures it again and reads what came back."""
    winner = document["winning_arm"]
    if winner is None:
        return (
            MET_AS_REJECTION,
            f"the floors were measured on {document['queries']} unseen queries and no arm "
            f"cleared them; the first failed floor is {document['first_failed_floor']}, and "
            "nothing was reopened to close it",
        )
    return _yes(
        f"the {winner} arm cleared Recall@5 >= {RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on "
        f"{document['queries']} unseen queries read once; the condition is recorded as "
        f"{document['gate_l2_condition_24']}"
    )


def _condition_28(document: dict[str, Any]) -> tuple[str, str]:
    totals = document["totals"]
    clean = not document["failed_rows"] and not document["skipped_rows"]
    clean = clean and not document["structural_findings"]
    detail = (
        f"{totals['passed']} of {totals['rows']} release-matrix rows passed, "
        f"{totals['skipped']} skipped, {len(document['structural_findings'])} structural findings"
    )
    return _yes(detail) if clean else _no(detail)


def _condition_29(document: dict[str, Any]) -> tuple[str, str]:
    """Read from the release record, which reads it from the remote. S21D5-095.

    Absent until the protected release happens, which is why this condition is `pending` in the
    provisional assessment and decided here only in the gate-close regeneration.
    """
    release = document["release"]
    if document["findings"]:
        return _no(f"the release record carries findings: {document['findings']}")
    return _yes(
        f"PR #{release['implementation_pull_request']} squash-merged into protected main at "
        f"{release['implementation_merged_at']}, exact-head main CI run "
        f"{release['exact_head_main_ci']['run']} {release['exact_head_main_ci']['jobs']}, and the "
        f"annotated tag {release['tag']} object {str(release['tag_object'])[:16]} peels to "
        f"{str(release['peeled_commit'])[:16]}"
    )


#: Condition number to the evidence that bears on it and the rule that reads it.
BEARINGS: dict[int, Bearing] = {
    1: Bearing(
        "sprint-21d5-baseline.json", "the D4 release verified from live handles", _condition_1
    ),
    2: Bearing(
        "sprint-21d5-authority-isolation-after.json",
        "every predecessor store reproduces its fingerprint after the wave, with zero writes",
        _condition_2,
    ),
    3: Bearing(
        "sprint-21d5-reuse-audit.json",
        "every reused role read out of the predecessor's released audit, bodies unmodified",
        _condition_3,
    ),
    4: Bearing(
        "sprint-21d5-pre-registration.json",
        "revision 5 published before any D5 measurement",
        _condition_4,
    ),
    5: Bearing(
        "sprint-21d5-calibration-campaign.json",
        "every attempted candidate carries an independent hidden-verifier label",
        _condition_5,
    ),
    6: Bearing(
        "sprint-21d5-snapshots.json",
        "no forbidden, identity, outcome or answer field reaches the fitted matrices",
        _condition_6,
    ),
    7: Bearing(
        "sprint-21d5-corpus-separation.json",
        "no transitive group crosses a D5 role",
        _condition_7,
    ),
    8: Bearing(
        "sprint-21d5-snapshots.json",
        "at least 200/50 fitting and 40/10 calibration",
        _condition_8,
    ),
    9: Bearing(
        "sprint-21d5-snapshots.json",
        "zero REAL_GOVERNED_RUN observations in fitting and calibration",
        _condition_9,
    ),
    12: Bearing(
        SELECTION,
        "the strongest deterministic baseline and every grid and sweep point are recorded",
        _condition_12,
    ),
    17: Bearing(
        "sprint-21d5-operations.json",
        "every rate names its denominator and uses the independent one",
        _condition_17,
    ),
    24: Bearing(
        RETRIEVAL_DECISION,
        f"Recall@5 >= {RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on at least 50 unseen queries",
        _condition_24,
    ),
    28: Bearing(
        "sprint-21d5-verification-matrix.json",
        "every required isolated and repository check ran and passed, none skipped",
        _condition_28,
    ),
    29: Bearing(
        "sprint-21d5-release.json",
        "protected merge, post-merge exact-head CI, annotated tag, remote read",
        _condition_29,
    ),
}

#: Conditions the selection stop closed, with what each would have measured. Written out so the
#: map is reviewable against §2.2's table rather than against this script's cleverness. The set
#: is checked against the continuation record's own list at run time.
NOT_OPENED_CONDITIONS: dict[int, str] = {
    10: "final A and B, each 120 new verifier-backed outcomes over 30 groups",
    11: "one artifact selected before final access, with final manifests inaccessible to fitting",
    13: "at least 20 final group decisions differing from the strongest baseline",
    14: "at least 5 absolute points or 20% relative error reduction on final evidence",
    15: "the paired group bootstrap at seed 21041 over 2,000 resamples",
    16: "a positive learned-minus-baseline direction in both final batches",
    18: "zero accepted-to-rejected safety, governance, permission, secret or destructive changes",
    19: "no retained domain losing more than 2 points and aggregate loss at most 1 point",
    20: (
        "at least 100 pre-registered promotion metamorphic/OOD ranking decisions with exactly "
        "zero confident errors. Its own precondition was measured and did not clear: over 100 "
        "independent fresh calibration decisions the zero-error operating point admits 0.26 of "
        "them at 320 fitting rows and 0.27 at 720, against §2.3's floor of 0.40, with zero "
        "confident errors in both. The margin certifies honestly and does not certify enough"
    ),
    21: "shadow mode changing zero executed decisions against final evidence",
    22: (
        "the selected artifact as canonical inert JSON with complete lineage. `CorrectionArtifact"
        "PayloadV3` and its loader are released and exercised, but no candidate names an "
        "operating point to bind into one, and a record about a fixture is not a record about a "
        "candidate"
    ),
    23: (
        "the runtime resolver reaching every reason code against the real artifact, each with an "
        "immediate deterministic fallback"
    ),
    25: "a hash-bound canary manifest with the verifier mandatory and the kill switch immediate",
    26: "activation, loading, disable, restoration and rollback surviving restart on a real one",
    27: "an exact human approval over the existing fields, with no self-approval",
}

#: The one condition that is neither met nor stopped: its evidence is created by the release.
PENDING_CONDITIONS: dict[int, str] = {
    29: (
        "the protected merge, its exact-head post-merge main CI, the annotated tag and the "
        "remote verification. The gate-close regeneration is what decides this row"
    )
}

#: Gate D1's three conditions, and what each waits on. 15 is the one D5 closes.
GATE_D1: dict[int, tuple[str, str]] = {
    6: (
        "at least 200 unique eligible verifier-backed primary-surface outcomes",
        "closed by the selection stop: the outcomes that would close it are final and canary "
        "outcomes, and neither was authorised",
    ),
    7: (
        "at least 20 primary-surface examples change the advisory action",
        "closed by the selection stop: condition 13's evidence read against the D1 contract, "
        "and condition 13 never opened",
    ),
    15: (
        "a new retrieval holdout reaches both floors",
        "measured and reached on sixty freshly authored unseen-task queries read once",
    ),
}

NOT_OPENED_RULE = "closed by a typed stop; the row binds the stop hash rather than a measurement"


def _stop_hash() -> str:
    selection = _read(SELECTION)
    if selection is None:
        raise SystemExit(f"{SELECTION} is required; it carries the stop every closed row binds")
    return str(selection["integrity_content_hash"])


def _continuation_agrees() -> dict[str, Any]:
    """The not-opened set is the continuation record's, not this script's.

    S21D5-036 wrote which fifteen conditions the stop closed and bound them to one hash. A
    second list here that quietly disagreed would be an assessment writing its own scope.
    """
    continuation = _read("sprint-21d5-continuation.json")
    if continuation is None:
        raise SystemExit("sprint-21d5-continuation.json is required; it declares the closed set")
    declared = sorted(int(item) for item in continuation["not_opened"]["gate_l2_conditions"])
    mapped = sorted(NOT_OPENED_CONDITIONS)
    if declared != mapped:
        raise SystemExit(
            f"the continuation record closes {declared} and this assessment maps {mapped}; "
            "one of the two is wrong and neither may be guessed"
        )
    return {
        "source": "sprint-21d5-continuation.json",
        "source_sha256": _sha256("sprint-21d5-continuation.json"),
        "conditions": declared,
        "stop_hash": str(continuation["stop_hash"]),
        "stop_kind": str(continuation["decision"]["stop_kind"]),
    }


def _rows() -> list[dict[str, Any]]:
    stop = _stop_hash()
    rows: list[dict[str, Any]] = []
    for condition in range(1, 30):
        if condition in BEARINGS:
            bearing = BEARINGS[condition]
            document = _read(bearing.source)
            if document is None and condition in PENDING_CONDITIONS:
                # The release has not happened yet. `pending` is neither a stop nor a pass, and
                # the gate-close regeneration is what turns it into one.
                rows.append(
                    {
                        "condition": condition,
                        "state": PENDING,
                        "rule": bearing.rule,
                        "evidence": None,
                        "detail": PENDING_CONDITIONS[condition],
                    }
                )
                continue
            if document is None:
                rows.append(
                    {
                        "condition": condition,
                        "state": FAILED,
                        "rule": bearing.rule,
                        "evidence": bearing.source,
                        "detail": f"{bearing.source} is absent, so this condition decided nothing",
                    }
                )
                continue
            state, detail = bearing.decide(document)
            rows.append(
                {
                    "condition": condition,
                    "state": state,
                    "rule": bearing.rule,
                    "evidence": bearing.source,
                    "evidence_sha256": _sha256(bearing.source),
                    "detail": detail,
                }
            )
        else:
            rows.append(
                {
                    "condition": condition,
                    "state": NOT_OPENED,
                    "rule": NOT_OPENED_RULE,
                    "evidence": SELECTION,
                    "evidence_sha256": _sha256(SELECTION),
                    "stop_hash": stop,
                    "stop_source": STOP_SOURCE,
                    "detail": f"would have measured {NOT_OPENED_CONDITIONS[condition]}",
                }
            )
    return rows


def _d1_rows() -> list[dict[str, Any]]:
    stop = _stop_hash()
    retrieval = _read(RETRIEVAL_DECISION)
    rows = []
    for condition, (closure, detail) in GATE_D1.items():
        row: dict[str, Any] = {
            "condition": condition,
            "closure_rule": closure,
            "state": NOT_OPENED,
            "detail": detail,
        }
        if condition == 15 and retrieval is not None:
            # Read, not asserted: the record says whether the floors were reached, and the row
            # reports whichever answer is in it.
            reached = retrieval["winning_arm"] is not None
            row["state"] = "closed" if reached else "remains_open"
            row["evidence"] = RETRIEVAL_DECISION
            row["evidence_sha256"] = _sha256(RETRIEVAL_DECISION)
            row["winning_arm"] = retrieval["winning_arm"]
            row["first_failed_floor"] = retrieval["first_failed_floor"]
            row["recorded_as"] = retrieval["gate_d1_condition_15"]
            if not reached:
                row["detail"] = "measured and not reached"
        else:
            row["stop_hash"] = stop
            row["stop_source"] = STOP_SOURCE
        rows.append(row)
    return rows


def _markdown(rows: list[dict[str, Any]], d1_rows: list[dict[str, Any]]) -> str:
    lines = ["| Condition | State | Decided by | Detail |", "|---:|---|---|---|"]
    for row in rows:
        evidence = row.get("evidence") or "—"
        lines.append(f"| {row['condition']} | `{row['state']}` | `{evidence}` | {row['detail']} |")
    lines.append("")
    lines.append("| Gate D1 | State | Closure rule | Detail |")
    lines.append("|---:|---|---|---|")
    for row in d1_rows:
        lines.append(
            f"| {row['condition']} | `{row['state']}` | {row['closure_rule']} | {row['detail']} |"
        )
    return "\n".join(lines)


def _canonical(value: object) -> bytes:
    """The bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def _verdict_reason(counts: dict[str, int]) -> str:
    """Computed from the counts. A sentence written here would be an assertion."""
    unmet = [
        f"{counts[NOT_OPENED]} never opened" if counts[NOT_OPENED] else "",
        f"{counts[MET_AS_REJECTION]} met as a rejection" if counts[MET_AS_REJECTION] else "",
        f"{counts[PENDING]} awaiting the protected release" if counts[PENDING] else "",
        f"{counts[FAILED]} failed" if counts[FAILED] else "",
    ]
    named = ", ".join(item for item in unmet if item)
    if not named:
        return f"all {counts[MET]} applicable conditions are met"
    return f"the gate passes only when every applicable condition is met; {named}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d5-gate-l2.json")
    parser.add_argument("--markdown", action="store_true", help="print the condition table")
    arguments = parser.parse_args()

    closed = _continuation_agrees()
    rows = _rows()
    d1_rows = _d1_rows()
    counts = {
        state: sum(1 for row in rows if row["state"] == state)
        for state in (MET, MET_AS_REJECTION, CARRIED, NOT_OPENED, PENDING, FAILED)
    }
    contracts = _read("sprint-21d5-contracts.json")
    if contracts is None:
        raise SystemExit("the frozen revision-5 contract record is required")
    carried = contracts["unchanged_from_d4"]

    report = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W8",
        "item": "S21D5-091",
        "purpose": (
            "The twenty-nine Gate L2 conditions and Gate D1's three, each decided by the "
            "evidence that bears on it. No condition may be asserted; every row names its file "
            "and rule, or the stop hash that closed it."
        ),
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256("sprint-21d5-pre-registration.json"),
        "gate_contract_hash": carried["gate_contract"],
        "gate_l2_conditions": carried["gate_conditions"],
        "thresholds_changed": carried["thresholds_changed"],
        "final_outcomes_inspected": False,
        "gate_l2": rows,
        "gate_d1": d1_rows,
        "counts": counts,
        "closed_set_read_from_the_continuation_record": closed,
        "stops": {
            "selection": {"hash": _stop_hash(), "source": STOP_SOURCE},
            "retrieval": {
                "source": "S21D5-046 retrieval decision",
                "winning_arm": (_read(RETRIEVAL_DECISION) or {}).get("winning_arm"),
                "first_failed_floor": (_read(RETRIEVAL_DECISION) or {}).get("first_failed_floor"),
            },
        },
        "verdict": (
            "gate_l2_passes"
            if counts[FAILED] == 0
            and counts[NOT_OPENED] == 0
            and counts[PENDING] == 0
            and counts[MET_AS_REJECTION] == 0
            else "gate_l2_does_not_pass"
        ),
        "verdict_reason": _verdict_reason(counts),
        "provisional_until": (
            "the protected merge, its exact-head post-merge main CI, and remote tag verification"
        ),
        "no_condition_is_carried_from_d4": counts[CARRIED] == 0,
    }
    if arguments.markdown:
        # A reader, not a writer. Rendering the table must not rewrite the record with a fresh
        # `recorded_at`, or quoting the table into the assessment moves the hash it just cited.
        print(_markdown(rows, d1_rows))
        return 0

    seal = hashlib.sha256(_canonical(report)).hexdigest()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(_canonical({**report, "integrity_content_hash": seal}))
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "counts": counts,
                "verdict": report["verdict"],
                "seal": seal,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
