#!/usr/bin/env python
"""S21D6-091: the twenty-nine Gate L2 conditions and Gate D1's three, decided by evidence.

    scripts/gate_assessment_d6.py [--output docs/.../sprint-21d6-gate-l2.json] [--markdown]

Every condition is a row, and every row names the file and the rule that decided it. A condition
with no bearing evidence is `not_opened` bound to the stop hash that closed it, never `met` --
**this script cannot assert a pass, only read one.** There is no branch below that writes `met`
without a document behind it, no default that upgrades a missing file, and the verdict is
computed from the counts rather than stated.

Six states, and this sprint uses four of them:

* `met` -- the evidence exists and the rule holds;
* `met_as_rejection` -- the rule was applied and the recorded no is what the condition asked for.
  Not used here;
* `not_opened` -- a stop closed it, and the row names the stop hash. Fifteen conditions, bound to
  S21D6-035's null selection under §3.4 step 2, `leak_budget_exceeded`;
* `pending` -- the evidence does not exist *yet* and will after the protected release. Only
  condition 29 is ever this, and the gate-close regeneration is what turns it into `met`;
* `failed` -- evidence exists and the rule does not hold;
* `carried` -- a predecessor's evidence reused unchanged. **Never used here**, and the record
  reports a count of zero for it rather than leaving a reader to wonder whether it was an option.

Two rows are D6's own shape and neither is a soft `met`.

*Condition 8 has no D6 fitting partition to count.* D6 executes one partition and refits nothing,
so the fitting floor is met by D5's sealed 720-row pool, read through S21D6-023's proof that the
pool D6 names is byte-for-byte the released one. The row reports both halves and says which store
each came from.

*Condition 24 is inherited, and the inheritance is re-checked here rather than trusted.* The
W0 ruling voids itself if D6 changed the searchable surface, opened a retrieval arm, or moved the
comparator. This row recomputes all three identities from D6's own tree and refuses the
inheritance if any hash moved -- which is exactly what the ruling's `re_checked_at` clause
demands, and the only reason an inherited condition may be recorded as met at all.

`not_opened` is not a soft `met`. The gate passes only when every applicable condition is met.
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
SELECTION = "sprint-21d6-learner-selection.json"
CONTINUATION = "sprint-21d6-continuation.json"
STOP_SOURCE = "S21D6-035 null candidate selection under §3.4 step 2, leak_budget_exceeded"

#: The W0 ruling, and the two D5 records whose identity it stakes itself on.
RULING = "sprint-21d6-condition-24-ruling.json"
D5_RETRIEVAL_DECISION = "sprint-21d5-retrieval-decision.json"
D5_SURFACE = "sprint-21d5-surface.json"

#: The floors §2.4 froze, unchanged since D4. Named here so condition 24's row reads them rather
#: than repeating whatever the inherited record happens to say about itself.
RECALL_FLOOR = "0.70"
MRR_FLOOR = "0.50"


@dataclass(frozen=True, slots=True)
class Bearing:
    """Which produced evidence bears on one condition, and what decides it."""

    source: str
    rule: str
    decide: Callable[[dict[str, Any]], tuple[str, str]]


def _read(name: str) -> dict[str, Any] | None:
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _sha256(name: str) -> str | None:
    path = EVIDENCE / name
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _yes(detail: str) -> tuple[str, str]:
    return MET, detail


def _no(detail: str) -> tuple[str, str]:
    return FAILED, detail


# ------------------------------------------------------- the conditions that were opened


def _condition_1(document: dict[str, Any]) -> tuple[str, str]:
    release = document["d5_release"]
    agrees = release["local_tag_object"] == release["remote_tag_object"]
    agrees = agrees and release["local_peeled_commit"] == release["remote_peeled_commit"]
    detail = (
        f"the D5 tag object {str(release['local_tag_object'])[:16]} peels to "
        f"{str(release['local_peeled_commit'])[:16]}, and the local and remote handles agree"
    )
    return _yes(detail) if agrees else _no("the local and remote D5 release handles disagree")


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
    """D6's form: three carried roles read out of D5's released audit, unopened.

    D6 builds no fitting pool of its own -- it inherits D5's, sealed -- so what this condition
    owes is the other half: every protected role D6 carries agrees with the predecessor's
    released audit, and no protected body was opened to make the carry work.
    """
    against = document["compared_against_the_d5_audit"]
    agreement = document["carried_roles_agree_across_released_generators"]
    access = document["access_and_outcome_authority"]

    disagreeing = sorted(
        role for role, comparison in agreement.items() if not comparison["identical"]
    )
    opened = sorted(key for key in ("canary", "final_a", "final_b") if access[f"{key}_opened"])
    # Zero is the correct value for both, and the reason is the audit surface: it reads sealed
    # catalogues, roots and access identities, and never opens a protected body.
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
        f"{len(agreement)} carried roles reproduce their released bundle digests, read from "
        f"{against['source']} at {str(against['source_sha256'])[:12]}; "
        f"{document['protected_task_identities']} protected task identities were resolved by "
        "identity alone, and zero protected bodies were opened"
    )
    if clean:
        return _yes(detail)
    return _no(
        f"roles disagreeing with the D5 audit {disagreeing}; protected roles opened {opened}; "
        f"the audit read {document['audit_surface']!r}"
    )


def _condition_4(document: dict[str, Any]) -> tuple[str, str]:
    measured = document["measured_values"]
    return (
        _yes(f"revision {document['revision']} published with measured_values: {measured}")
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
    """The scan set is named by `integrity_d5`, not read out of the record being assessed."""
    scans = document["scans"]
    ran = {str(item["name"]) for item in scans["results"]}
    forbidden = next(
        item for item in scans["results"] if item["name"] == "no_forbidden_field_reaches_the_matrix"
    )
    missing = sorted(REQUIRED_SCANS - ran)
    clean = forbidden["passed"] and not scans["failed"] and not missing and scans["all_passed"]
    return (
        _yes(
            f"{forbidden['detail']}; all {len(REQUIRED_SCANS)} required scans passed over "
            f"{scans['count']} runs across the two halves"
        )
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
    """Two halves from two stores, and the row says which is which.

    D6 executes one partition, so there is no D6 fitting dataset to count. The fitting floor is
    met by D5's sealed 720-row pool, and what makes that a measurement rather than a citation is
    S21D6-023's byte-for-byte proof that the pool D6 names is the released one. A row that
    counted only the certification half would report half a condition as if it were all of it.
    """
    certification = next(
        item for item in document["datasets"] if item["partition"] == "calibration"
    )
    manifests = _read("sprint-21d6-sealed-manifests.json")
    if manifests is None:
        return _no("sprint-21d6-sealed-manifests.json is absent, so the fitting half is unproven")
    volume = manifests["volume"]
    pool = manifests["fitting_pool"]
    identical = bool(pool["bodies"]["identical"])
    floors = certification["members"] >= 40 and certification["groups"] >= 10
    floors = floors and int(volume["point"]) >= 200 and int(volume["point_in_groups"]) >= 50
    detail = (
        f"{certification['members']} certification observations over "
        f"{certification['groups']} groups in D6's own store, and the fitting floor met by D5's "
        f"sealed {volume['point']} rows over {volume['point_in_groups']} groups, carried "
        "unrefitted and proved byte-for-byte identical to the released pool by S21D6-023"
    )
    if floors and identical:
        return _yes(detail)
    return _no(
        detail + f"; pool bodies identical to D5's released seal: {identical}"
        if not identical
        else detail
    )


def _condition_9(document: dict[str, Any]) -> tuple[str, str]:
    runs = {
        item["partition"]: item["real_governed_runs"]
        for item in document["datasets"]
        if item["partition"] in {"training", "calibration"}
    }
    return (
        _yes(f"zero REAL_GOVERNED_RUN observations in the certification dataset: {runs}")
        if runs and not any(runs.values())
        else _no(f"real governed runs reached a fitted split: {runs}")
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
            "are reported, including the one that is not selectable"
        )
        if reported and grid["sweep_points_reported"]
        else _no(f"{grid['cells_reported']} of {len(grid['volume_points'])} cells reported")
    )


def _condition_17(document: dict[str, Any]) -> tuple[str, str]:
    """Every rate over the independent denominator, read off the record that computed them.

    D5 read this from a twelve-class report its operations wave produced. D6 has no operations
    wave, so it is read where the rates are actually written: the selection record names its
    denominator on every cell and the census that fixed it.
    """
    decisions = document["decisions"]
    independent = int(decisions["independent_decisions"])
    cells = document["cells"]
    named = [cell for cell in cells if cell["coverage_denominator"] == "independent_decisions"]
    over_the_independent = [
        cell for cell in cells if int(cell["independent_decisions"]) == independent
    ]
    census = decisions["census"]
    clean = (
        len(named) == len(cells)
        and len(over_the_independent) == len(cells)
        and not int(census["replicated_decisions"])
        and independent == int(census["independent_decisions"])
    )
    detail = (
        f"{len(cells)} cells, every coverage over `independent_decisions` and every one of them "
        f"the same {independent} the census fixed; {census['replicated_decisions']} replicated "
        f"decisions of {census['nominal_decisions']} nominal"
    )
    return _yes(detail) if clean else _no(detail)


def _condition_24(document: dict[str, Any]) -> tuple[str, str]:
    """Inherited under the W0 ruling, and the inheritance re-checked from D6's own tree.

    The ruling names three identities that void it. Recomputing them here is not ceremony: an
    inherited condition whose sources were never re-read is a condition asserted from a sentence,
    and the ruling's own `re_checked_at` clause says the check belongs at gate close.
    """
    inherited = document["inherited_measurement"]
    identities = document["the_three_identities_that_void_it"]

    moved: list[str] = []
    if _sha256(D5_RETRIEVAL_DECISION) != inherited["record_sha256"]:
        moved.append(f"{D5_RETRIEVAL_DECISION} bytes")
    measurement = _read(D5_RETRIEVAL_DECISION)
    if measurement is None:
        moved.append(f"{D5_RETRIEVAL_DECISION} is absent")
    elif measurement["integrity_content_hash"] != inherited["integrity_content_hash"]:
        moved.append(f"{D5_RETRIEVAL_DECISION} seal")

    surface_identity = identities["searchable_surface"]
    if _sha256(D5_SURFACE) != surface_identity["record_sha256"]:
        moved.append(f"{D5_SURFACE} bytes")
    surface = _read(D5_SURFACE)
    if surface is None:
        moved.append(f"{D5_SURFACE} is absent")
    elif surface["integrity_content_hash"] != surface_identity["integrity_content_hash"]:
        moved.append(f"{D5_SURFACE} seal")

    # The third identity is about what D6 itself did, so it is read from D6's own seal rather
    # than from the ruling's copy of the question.
    manifests = _read("sprint-21d6-sealed-manifests.json")
    if manifests is None:
        moved.append("sprint-21d6-sealed-manifests.json is absent")
    else:
        retrieval = manifests["inherited_retrieval"]
        if (
            int(retrieval["retrieval_groups_authored"])
            or not retrieval["identical_to_the_released_d5_pool"]
        ):
            moved.append("D6 authored or altered a retrieval pool")

    if moved:
        return _no(
            "the inheritance is void: " + ", ".join(moved) + ". The ruling holds only while the "
            "surface, the arms and the comparator are the ones D5 measured"
        )
    if not inherited["passed"] or inherited["winning_arm"] is None:
        return _no(
            f"the inherited measurement did not clear its floors; the first failed floor is "
            f"{inherited['first_failed_floor']}"
        )
    return _yes(
        f"inherited under {RULING}: the {inherited['winning_arm']} arm cleared Recall@5 >= "
        f"{RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on {inherited['queries']} unseen queries in "
        "D5, and all three voiding identities were recomputed here and are unmoved -- D6 "
        "authored 0 retrieval groups, opened no arm, and changed neither the surface nor the "
        "comparator"
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
    """Read from the release record, which reads it from the remote. S21D6-095."""
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
        "sprint-21d6-baseline.json", "the D5 release verified from live handles", _condition_1
    ),
    2: Bearing(
        "sprint-21d6-authority-isolation-after.json",
        "every predecessor store reproduces its fingerprint after the wave, with zero writes",
        _condition_2,
    ),
    3: Bearing(
        "sprint-21d6-reuse-audit.json",
        "every carried role read out of the predecessor's released audit, bodies unopened",
        _condition_3,
    ),
    4: Bearing(
        "sprint-21d6-pre-registration.json",
        "revision 6 published before any D6 measurement",
        _condition_4,
    ),
    5: Bearing(
        "sprint-21d6-certification-campaign.json",
        "every attempted candidate carries an independent hidden-verifier label",
        _condition_5,
    ),
    6: Bearing(
        "sprint-21d6-snapshots.json",
        "no forbidden, identity, outcome or answer field reaches the fitted matrices",
        _condition_6,
    ),
    7: Bearing(
        "sprint-21d6-corpus-separation.json",
        "no transitive group crosses a D6 role",
        _condition_7,
    ),
    8: Bearing(
        "sprint-21d6-snapshots.json",
        "at least 200/50 fitting and 40/10 certification",
        _condition_8,
    ),
    9: Bearing(
        "sprint-21d6-snapshots.json",
        "zero REAL_GOVERNED_RUN observations in the fitted splits",
        _condition_9,
    ),
    12: Bearing(
        SELECTION,
        "the strongest deterministic baseline and every grid and sweep point are recorded",
        _condition_12,
    ),
    17: Bearing(
        SELECTION,
        "every rate names its denominator and uses the independent one",
        _condition_17,
    ),
    24: Bearing(
        RULING,
        f"Recall@5 >= {RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on at least 50 unseen queries",
        _condition_24,
    ),
    28: Bearing(
        "sprint-21d6-verification-matrix.json",
        "every required isolated and repository check ran and passed, none skipped",
        _condition_28,
    ),
    29: Bearing(
        "sprint-21d6-release.json",
        "protected merge, post-merge exact-head CI, annotated tag, remote read",
        _condition_29,
    ),
}

#: Conditions the selection stop closed, with what each would have measured. Written out so the
#: map is reviewable against §2.4's table rather than against this script's cleverness. The set
#: is checked against the continuation record's own list at run time.
NOT_OPENED_CONDITIONS: dict[int, str] = {
    10: "final A and B, each 120 new verifier-backed outcomes over 30 groups",
    11: "one artifact selected before final access, with final manifests inaccessible to fitting",
    13: "at least 20 final group decisions differing from the strongest baseline",
    14: "at least 5 absolute points or 20% relative error reduction on final evidence",
    15: "the paired group bootstrap over the final batches",
    16: "a positive learned-minus-baseline direction in both final batches",
    18: "zero accepted-to-rejected safety, governance, permission, secret or destructive changes",
    19: "no retained domain losing more than 2 points and aggregate loss at most 1 point",
    20: (
        "at least 100 pre-registered promotion metamorphic/OOD ranking decisions inside the "
        "admission budget. Its own precondition was measured and did not clear: over 100 "
        "independent fresh certification decisions the split-conformal bar at alpha 0.20 admits "
        "0.40 of them with 6 errors, and the Clopper-Pearson 95% upper bound on the error rate "
        "among those admitted is 0.2747 against the pre-registered ceiling of 0.15"
    ),
    21: "shadow mode changing zero executed decisions against final evidence",
    22: (
        "the selected artifact as canonical inert JSON with complete lineage. `CorrectionArtifact"
        "PayloadV3` and its loader are released and were exercised on a fixture in S21D6-024, but "
        "no candidate names a conformal bar to bind into one, and a record about a fixture is "
        "not a record about a candidate"
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

#: Gate D1's three conditions, and what each waits on. 15 is the one D6 inherits.
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
        "inherited from D5's sealed measurement under the W0 ruling, with all three voiding "
        "identities recomputed at gate close and unmoved",
    ),
}

NOT_OPENED_RULE = "closed by a typed stop; the row binds the stop hash rather than a measurement"


def _stop_hash() -> str:
    """The continuation record's hash, which is over the stop and everything decided from it."""
    continuation = _read(CONTINUATION)
    if continuation is None:
        raise SystemExit(f"{CONTINUATION} is required; it carries the stop every closed row binds")
    return str(continuation["stop_hash"])


def _continuation_agrees() -> dict[str, Any]:
    """The not-opened set is the continuation record's, not this script's."""
    continuation = _read(CONTINUATION)
    if continuation is None:
        raise SystemExit(f"{CONTINUATION} is required; it declares the closed set")
    declared = sorted(int(item) for item in continuation["not_opened"]["gate_l2_conditions"])
    mapped = sorted(NOT_OPENED_CONDITIONS)
    if declared != mapped:
        raise SystemExit(
            f"the continuation record closes {declared} and this assessment maps {mapped}; "
            "one of the two is wrong and neither may be guessed"
        )
    return {
        "source": CONTINUATION,
        "source_sha256": _sha256(CONTINUATION),
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


def _d1_rows(l2_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """D1's three, and 15 reads the same inherited row condition 24 just decided."""
    stop = _stop_hash()
    twenty_four = next(row for row in l2_rows if row["condition"] == 24)
    rows = []
    for condition, (closure, detail) in GATE_D1.items():
        row: dict[str, Any] = {
            "condition": condition,
            "closure_rule": closure,
            "state": NOT_OPENED,
            "detail": detail,
        }
        if condition == 15:
            inherited = _read(RULING) or {}
            measurement = inherited.get("inherited_measurement", {})
            # Read, not asserted, and read from the row that already re-checked the inheritance:
            # a D1 row that reached its own verdict could disagree with condition 24 about the
            # same measurement.
            row["state"] = "closed" if twenty_four["state"] == MET else "remains_open"
            row["evidence"] = RULING
            row["evidence_sha256"] = _sha256(RULING)
            row["inherited_from"] = D5_RETRIEVAL_DECISION
            row["winning_arm"] = measurement.get("winning_arm")
            row["first_failed_floor"] = measurement.get("first_failed_floor")
            row["recorded_as"] = "closed by inheritance, re-checked at gate close"
            row["gate_l2_condition_24_state"] = twenty_four["state"]
            if twenty_four["state"] != MET:
                row["detail"] = f"the inheritance did not hold: {twenty_four['detail']}"
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
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d6-gate-l2.json")
    parser.add_argument("--markdown", action="store_true", help="print the condition table")
    arguments = parser.parse_args()

    closed = _continuation_agrees()
    rows = _rows()
    d1_rows = _d1_rows(rows)
    counts = {
        state: sum(1 for row in rows if row["state"] == state)
        for state in (MET, MET_AS_REJECTION, CARRIED, NOT_OPENED, PENDING, FAILED)
    }
    contracts = _read("sprint-21d6-contracts.json")
    if contracts is None:
        raise SystemExit("the frozen revision-6 contract record is required")
    carried = contracts["unchanged_from_d5"]

    report = {
        "schema_version": 1,
        "sprint": "21D6",
        "wave": "W3",
        "item": "S21D6-091",
        "purpose": (
            "The twenty-nine Gate L2 conditions and Gate D1's three, each decided by the "
            "evidence that bears on it. No condition may be asserted; every row names its file "
            "and rule, or the stop hash that closed it."
        ),
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256("sprint-21d6-pre-registration.json"),
        "gate_contract_hash": carried["gate_contract"],
        "gate_l2_conditions": carried["gate_conditions"],
        "the_one_clause_that_changed": {
            "amendment": "sprint-21d6-contracts-amendment-2.json",
            "amendment_sha256": _sha256("sprint-21d6-contracts-amendment-2.json"),
            "what": (
                "§2.3's admission clause: 'exactly zero confident errors' struck, replaced by "
                "a split-conformal bar at the pre-registered alpha with a Clopper-Pearson 95% "
                "upper bound at most C. Every other §2.3 condition and every Gate L2 threshold "
                "is unchanged"
            ),
            "granted_before_any_d6_measurement": True,
        },
        "final_outcomes_inspected": False,
        "gate_l2": rows,
        "gate_d1": d1_rows,
        "counts": counts,
        "closed_set_read_from_the_continuation_record": closed,
        "stops": {
            "selection": {"hash": _stop_hash(), "source": STOP_SOURCE},
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
        "no_condition_is_carried_from_d5": counts[CARRIED] == 0,
        "what_inherited_is_not": (
            "condition 24 is `met`, not `carried`. A carried condition would be a predecessor's "
            "verdict reused; this one is a predecessor's *measurement* whose three voiding "
            "identities were recomputed from D6's tree at gate close, under a ruling the gate "
            "owner granted in W0 before any D6 measurement existed"
        ),
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
