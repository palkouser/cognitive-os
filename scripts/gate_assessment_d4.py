#!/usr/bin/env python
"""S21D4-091: the twenty-nine Gate L2 conditions and Gate D1's three, decided by evidence.

    scripts/gate_assessment_d4.py [--output docs/.../sprint-21d4-gate-l2.json] [--markdown]

Every condition is a row, and every row names the file and the rule that decided it. A condition
with no bearing evidence is `not_opened` bound to the stop hash that closed it, never `met` —
this script cannot assert a pass, only read one.

Six states, and three of them carry the sprint:

* `met` — the evidence exists and the rule holds;
* `met_as_rejection` — the rule was applied, the answer was no, and the recorded no is what the
  condition asked for. Condition 24's floors were measured on sixty unseen queries and missed by
  0.0089;
* `not_opened` — a stop closed it, and the row names the stop hash;
* `pending` — the evidence does not exist *yet* and will after the protected release. Only
  condition 29 is ever this, and the gate-close regeneration is what turns it into `met`;
* `failed` — evidence exists and the rule does not hold;
* `carried` — a predecessor's evidence reused unchanged. **Never used here.** §2.2 is explicit
  that D4 inherits no pass from D3, so the state exists in the vocabulary and the record reports
  a count of zero for it rather than leaving a reader to wonder whether it was an option.

`not_opened` is not a soft `met`. The gate passes only when every applicable condition is met,
which is why a sprint with zero failures can still not pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"

MET = "met"
MET_AS_REJECTION = "met_as_rejection"
CARRIED = "carried"
NOT_OPENED = "not_opened"
PENDING = "pending"
FAILED = "failed"

#: The stop that closed every conditional condition, and where it is written down.
SELECTION = "sprint-21d4-learner-selection.json"
STOP_SOURCE = "S21D4-039 null candidate selection"

#: The retrieval branch reached its own result, and it is bound to its own stop.
RETRIEVAL_DECISION = "sprint-21d4-retrieval-decision.json"


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
    release = document["d3_release"]
    agrees = release["local_tag_object"] == release["remote_tag_object"]
    agrees = agrees and release["local_peeled_commit"] == release["remote_peeled_commit"]
    detail = (
        f"the D3 tag object {str(release['local_tag_object'])[:16]} peels to "
        f"{str(release['local_peeled_commit'])[:16]}, and the local and remote handles agree"
    )
    return _yes(detail) if agrees else _no("the local and remote D3 release handles disagree")


def _condition_2(document: dict[str, Any]) -> tuple[str, str]:
    before = document["predecessor_fingerprints_before"]
    after = document["predecessor_fingerprints_after"]
    unchanged = before == after
    detail = f"{len(before)} predecessor stores fingerprinted before and after; unchanged"
    return _yes(detail) if unchanged and before else _no("a predecessor fingerprint moved")


def _condition_3(document: dict[str, Any]) -> tuple[str, str]:
    counts = document["decision_independence"]["counts"]
    return _yes(
        f"D3's {counts['nominal_decisions']} metamorphic decisions recomputed as "
        f"{counts['independent_decisions']} independent and "
        f"{counts['replicated_decisions']} replicated, from D3's own evidence"
    )


def _condition_4(document: dict[str, Any]) -> tuple[str, str]:
    measured = document["measured_values"]
    return (
        _yes(f"revision 4 published with measured_values: {measured}")
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
    scans = document["scans"]
    forbidden = next(
        item for item in scans["results"] if item["name"] == "no_forbidden_field_reaches_the_matrix"
    )
    return (
        _yes(f"{forbidden['detail']}; {scans['count']} of {scans['required']} scans passed")
        if forbidden["passed"] and not scans["failed"]
        else _no(f"scans that failed: {scans['failed']}")
    )


def _condition_7(document: dict[str, Any]) -> tuple[str, str]:
    separation = document["role_separation"]
    crossings = separation["groups_crossing_a_role"]
    shared = sum(separation["pairs_sharing_a_group"].values())
    return (
        _yes(
            f"{len(separation['group_counts'])} roles, all pairwise disjoint; "
            f"{len(separation['pairs_sharing_a_group'])} role pairs share zero groups"
        )
        if not crossings and not shared and separation["all_pairwise_disjoint"]
        else _no(f"{len(crossings)} groups cross a role boundary and {shared} pairs share one")
    )


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
        if not any(runs.values())
        else _no(f"real governed runs reached a fitting or calibration split: {runs}")
    )


def _condition_12(document: dict[str, Any]) -> tuple[str, str]:
    baseline = document["baseline"]
    grid = document["grid"]
    return (
        _yes(
            f"the strongest deterministic rung is {baseline['strongest_deterministic_rung']}, "
            f"measured on the same decisions, and all {grid['cells_reported']} of "
            f"{grid['cells']} frozen cells are reported"
        )
        if grid["cells_reported"] == grid["cells"]
        else _no(f"{grid['cells_reported']} of {grid['cells']} cells reported")
    )


def _condition_17(document: dict[str, Any]) -> tuple[str, str]:
    """Read from the twelve-class report the operations run made with both authorities.

    The `decision_independence` class is the condition: it scans every committed file for a rate
    taken over the counted decisions rather than the distinct ones, and fails when it finds one
    or when it finds nothing to scan.
    """
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
    winner = document["winning_arm"]
    if winner is not None:
        return _yes(f"{winner} cleared both floors on {document['queries']} unseen queries")
    return (
        MET_AS_REJECTION,
        f"the floors were measured on {document['queries']} unseen queries and no arm cleared "
        f"them; the first failed floor is {document['first_failed_floor']}, and nothing was "
        "reopened to close it",
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


#: Condition number to the evidence that bears on it and the rule that reads it.
BEARINGS: dict[int, Bearing] = {
    1: Bearing(
        "sprint-21d4-baseline.json", "the D3 release verified from live handles", _condition_1
    ),
    2: Bearing(
        "sprint-21d4-authority-isolation.json",
        "every predecessor store reproduces its fingerprint before and after",
        _condition_2,
    ),
    3: Bearing(
        "sprint-21d4-d3-reconciliation.json",
        "D3's replica identity recomputed from D3's own evidence",
        _condition_3,
    ),
    4: Bearing(
        "sprint-21d4-pre-registration.json",
        "revision 4 published before any D4 measurement",
        _condition_4,
    ),
    5: Bearing(
        "sprint-21d4-calibration-campaign.json",
        "every attempted candidate carries an independent hidden-verifier label",
        _condition_5,
    ),
    6: Bearing(
        "sprint-21d4-snapshots.json",
        "no forbidden, identity, outcome or answer field reaches the fitted matrix",
        _condition_6,
    ),
    7: Bearing(
        "sprint-21d4-separation.json",
        "no transitive group crosses a D4 role",
        _condition_7,
    ),
    8: Bearing(
        "sprint-21d4-snapshots.json",
        "at least 200/50 fitting and 40/10 calibration",
        _condition_8,
    ),
    9: Bearing(
        "sprint-21d4-snapshots.json",
        "zero REAL_GOVERNED_RUN observations in fitting and calibration",
        _condition_9,
    ),
    12: Bearing(
        SELECTION,
        "the strongest deterministic baseline and every frozen rung are recorded",
        _condition_12,
    ),
    17: Bearing(
        "sprint-21d4-operations.json",
        "every rate names its denominator and uses the independent one",
        _condition_17,
    ),
    24: Bearing(
        RETRIEVAL_DECISION,
        "Recall@5 >= 0.70 and MRR@10 >= 0.50 on at least 50 distinct unseen queries",
        _condition_24,
    ),
    28: Bearing(
        "sprint-21d4-verification-matrix.json",
        "every required isolated and repository check ran and passed, none skipped",
        _condition_28,
    ),
}

#: Conditions the selection stop closed, with what each would have measured. Written out so the
#: map is reviewable against Section 2.2's table rather than against this script's cleverness.
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
        "zero confident errors. Its own precondition was measured and returned nothing: the "
        "zero-error operating point was derived over 100 independent calibration decisions at "
        "both volumes and no cell reached zero confident errors on a non-empty admitted set, "
        "which is the stop that closed everything below it"
    ),
    21: "shadow mode changing zero executed decisions against final evidence",
    22: (
        "the selected artifact as canonical inert JSON with complete lineage. D3 met this "
        "against a contract fixture it built; W4 declined to build a second one, because a "
        "record about a fixture is not a record about a candidate and §2.2 gives D4 no pass to "
        "inherit"
    ),
    23: (
        "the runtime resolver reaching every reason code against the real artifact, each with an "
        "immediate deterministic fallback. S21D4-075 proved restoration and rollback on the "
        "isolated lifecycle fixture, which is a different claim and is recorded as one"
    ),
    25: "a hash-bound canary manifest with the verifier mandatory and the kill switch immediate",
    26: (
        "activation, loading, disable, restoration and rollback surviving restart on a real "
        "activation. The rollback and refusal halves were proved on the isolated fixture by "
        "S21D4-075; no real activation existed to prove the rest against"
    ),
    27: "an exact human approval over the existing fields, with no self-approval",
}

#: The one condition that is neither met nor stopped: its evidence is created by the release.
PENDING_CONDITIONS: dict[int, str] = {
    29: (
        "the protected merge, its exact-head post-merge main CI, the annotated tag and the "
        "remote verification. The gate-close regeneration is what decides this row"
    )
}

#: Gate D1's three open conditions, and what each waits on.
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
        "measured and not reached: the fusion arm cleared Recall@5 at 0.7500 and missed MRR@10 "
        "at 0.4911 against a floor of 0.50",
    ),
}


def _stop_hash() -> str:
    selection = _read(SELECTION)
    if selection is None:
        raise SystemExit(f"{SELECTION} is required; it carries the stop every closed row binds")
    return str(selection["integrity_content_hash"])


def _rows() -> list[dict[str, Any]]:
    stop = _stop_hash()
    rows: list[dict[str, Any]] = []
    for condition in range(1, 30):
        if condition in BEARINGS:
            bearing = BEARINGS[condition]
            document = _read(bearing.source)
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
        elif condition in PENDING_CONDITIONS:
            rows.append(
                {
                    "condition": condition,
                    "state": PENDING,
                    "rule": "protected merge, post-merge exact-head CI, annotated tag, remote read",
                    "evidence": None,
                    "detail": PENDING_CONDITIONS[condition],
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


NOT_OPENED_RULE = "closed by a typed stop; the row binds the stop hash rather than a measurement"


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
            row["state"] = "remains_open"
            row["evidence"] = RETRIEVAL_DECISION
            row["evidence_sha256"] = _sha256(RETRIEVAL_DECISION)
            row["first_failed_floor"] = retrieval["first_failed_floor"]
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
    """The D4 convention: the bytes that are hashed are the bytes that are written."""
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False, default=str).encode(
        "utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d4-gate-l2.json")
    parser.add_argument("--markdown", action="store_true", help="print the condition table")
    arguments = parser.parse_args()

    rows = _rows()
    d1_rows = _d1_rows()
    counts = {
        state: sum(1 for row in rows if row["state"] == state)
        for state in (MET, MET_AS_REJECTION, CARRIED, NOT_OPENED, PENDING, FAILED)
    }
    contracts = _read("sprint-21d4-contracts.json")
    if contracts is None:
        raise SystemExit("the frozen revision-4 contract record is required")

    report = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W8",
        "item": "S21D4-091",
        "purpose": (
            "The twenty-nine Gate L2 conditions and Gate D1's three open ones, each decided by "
            "the evidence that bears on it. No condition may be asserted; every row names its "
            "file and rule, or the stop hash that closed it."
        ),
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256("sprint-21d4-pre-registration.json"),
        "gate_contract_hash": contracts["contracts"]["gates_and_stops"]["content_hash"],
        "gate_l2_conditions": contracts["contracts"]["gates_and_stops"]["gate_l2_conditions"],
        "thresholds_changed": contracts["contracts"]["gates_and_stops"][
            "gate_l2_thresholds_changed"
        ],
        "final_outcomes_inspected": False,
        "gate_l2": rows,
        "gate_d1_open": d1_rows,
        "counts": counts,
        "stops": {
            "selection": {"hash": _stop_hash(), "source": STOP_SOURCE},
            "retrieval": {
                "source": "S21D4-046 negative retrieval decision",
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
        "verdict_reason": (
            f"the gate passes only when every applicable condition is met; {counts[NOT_OPENED]} "
            f"were never opened, condition 24 is met as a rejection, and {counts[PENDING]} "
            "awaits the protected release"
        ),
        "provisional_until": (
            "the protected merge, its exact-head post-merge main CI, and remote tag verification"
        ),
        "no_condition_is_carried_from_d3": counts[CARRIED] == 0,
    }
    if arguments.markdown:
        # A reader, not a writer. Rendering the table used to rewrite the record with a fresh
        # `recorded_at`, so quoting the table into the assessment document moved the hash the
        # document had just cited.
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
