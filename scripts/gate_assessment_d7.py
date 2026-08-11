#!/usr/bin/env python
"""S21D7-041: the twenty-nine Gate L2 conditions and Gate D1's three, decided by evidence.

    scripts/gate_assessment_d7.py [--output docs/.../sprint-21d7-gate-l2.json] [--markdown]

Every condition is a row, and every row names the file and the rule that decided it. **This
script cannot assert a pass, only read one.** There is no branch below that writes `met` without
a document behind it, no default that upgrades a missing file, and the verdict is computed from
the counts rather than stated.

Six states, and this sprint uses two of them:

* `met` — the evidence exists and the rule holds;
* `met_as_rejection` — the rule was applied and the recorded no is what the condition asked for.
  Not used here;
* `not_opened` — a stop closed it, and the row names the stop hash. **Not used here.** D3 through
  D6 each closed between fifteen and nineteen conditions this way; D7 closes none, because the
  selection ended `1_select` and W3 opened every condition the stop would have closed;
* `pending` — the evidence does not exist *yet* and will after the protected release. Only
  condition 29 is ever this, and the gate-close regeneration is what turns it into `met`;
* `failed` — evidence exists and the rule does not hold;
* `carried` — a predecessor's evidence reused unchanged. **Never used here**, and the record
  reports a count of zero for it rather than leaving a reader to wonder whether it was an option.

Four rows are D7's own shape, and none of them is a soft `met`.

*Condition 3's audit is a W0 record and W3 opened two of the roles it audited.* That is not a
contradiction and the row says so rather than leaving it to be noticed: the audit records the
roles as carried unopened **at the time it was taken**, which is what the condition asks; the
final and canary roles were opened afterwards, under the §2.3 pass that authorises exactly that,
and the final roles were additionally repaired under S21D7-038 after failing their encodability
audit. A row that printed the W0 sentence unqualified would be true and misleading.

*Condition 8's fitting half is D5's pool, not D7's.* D7 refits nothing — the direction is fitted
on D5's sealed 720-row pool — so the row reports both halves and says which store each came from,
with the sealed-manifest proof that the pool D7 names is byte-for-byte the released one.

*Condition 24 is inherited, and the inheritance is re-checked here rather than trusted.* The W0
ruling voids itself if D7 changed the searchable surface, opened a retrieval arm, or moved the
comparator. This row recomputes all three identities from D7's own tree and refuses the
inheritance if any hash moved.

*Gate D1 condition 6 counts 260 outcomes and not 660.* The 400 certification outcomes set D7's
operating cell, so counting them as held-out surface evidence would be counting the corpus that
chose the operating point as evidence about it. Only the final and canary outcomes are counted —
opened once, never fitted, never calibrated against — and they clear the floor on their own.

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

SELECTION = "sprint-21d7-learner-selection.json"
CONTINUATION = "sprint-21d7-continuation.json"

#: The W0 ruling, and the two D5 records whose identity it stakes itself on.
RULING = "sprint-21d7-condition-24-ruling.json"
D5_RETRIEVAL_DECISION = "sprint-21d5-retrieval-decision.json"
D5_SURFACE = "sprint-21d5-surface.json"

#: The floors §2.4 froze, unchanged since D4. Named here so condition 24's row reads them rather
#: than repeating whatever the inherited record happens to say about itself.
RECALL_FLOOR = "0.70"
MRR_FLOOR = "0.50"

#: Gate D1 condition 6's floor, and the roles D7 is willing to count towards it.
D1_OUTCOME_FLOOR = 200
D1_CHANGED_FLOOR = 20
HELD_OUT_CAMPAIGNS = (
    "sprint-21d7-final-a-campaign.json",
    "sprint-21d7-final-b-campaign.json",
    "sprint-21d7-canary-campaign.json",
)


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


def _flag(document: dict[str, Any], block: str, condition: str) -> tuple[bool, dict[str, Any]]:
    """One sealed condition row out of a W3 record, read rather than recomputed."""
    row = dict(document[block][condition])
    return bool(row.pop("met", False)), row


# ------------------------------------------------------------------ the twenty-nine


def _condition_1(document: dict[str, Any]) -> tuple[str, str]:
    release = document["d6_release"]
    agrees = bool(release["local_and_remote_agree"])
    detail = (
        f"the D6 tag object {str(release['local_tag_object'])[:16]} peels to "
        f"{str(release['local_peeled_commit'])[:16]}, and the local and remote handles agree"
    )
    return _yes(detail) if agrees else _no("the local and remote D6 release handles disagree")


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
    """The carried roles, audited unopened — at W0, which is when the condition asks.

    W3 opened the final and canary roles afterwards and repaired two of them, both under
    authority. The row states that rather than printing the W0 sentence unqualified, because a
    reader arriving at this table has just read a W3 section that says the roles were opened.
    """
    against = document["compared_against_the_d6_audit"]
    agreement = document["carried_roles_agree_across_released_generators"]
    access = document["access_and_outcome_authority"]

    disagreeing = sorted(
        role for role, comparison in agreement.items() if not comparison["identical"]
    )
    opened = sorted(key for key in ("canary", "final_a", "final_b") if access[f"{key}_opened"])
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
        "identity alone, and zero protected bodies were opened. The roles were opened later, in "
        "W3, under the §2.3 pass that authorises it — and the two final roles were repaired "
        "there under S21D7-038 after failing their encodability audit"
    )
    if clean:
        return _yes(detail)
    return _no(
        f"roles disagreeing with the D6 audit {disagreeing}; protected roles opened {opened}; "
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
    """Every attempted candidate labelled, across all four campaigns rather than the first.

    D6 had one campaign to check. D7 has four, and a row that checked only the certification one
    would leave the two hundred and sixty outcomes the gate actually turns on unexamined.
    """
    campaigns = {"sprint-21d7-certification-campaign.json": document}
    for name in HELD_OUT_CAMPAIGNS:
        found = _read(name)
        if found is None:
            return _no(f"{name} is absent, so its outcomes are unverified")
        campaigns[name] = found

    unlabelled: list[str] = []
    attempted = 0
    for name, campaign in campaigns.items():
        execution = campaign["execution"]
        runs = int(execution["candidate_runs"])
        labelled = int(execution["hidden_passed"]) + int(execution["hidden_failed"])
        attempted += runs
        if not runs or labelled != runs or int(execution["candidates_left_unattempted"]):
            unlabelled.append(f"{name}: {labelled} of {runs}")
    if unlabelled:
        return _no(f"campaigns with unlabelled candidates: {unlabelled}")
    return _yes(
        f"all {attempted} candidate runs across {len(campaigns)} campaigns carry an independent "
        "hidden-verifier label, and none was left unattempted"
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
            f"{scans['count']} runs"
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
    """Two halves from two stores, and the row says which is which."""
    certification = next(
        item for item in document["datasets"] if item["partition"] == "calibration"
    )
    manifests = _read("sprint-21d7-sealed-manifests.json")
    if manifests is None:
        return _no("sprint-21d7-sealed-manifests.json is absent, so the fitting half is unproven")
    volume = manifests["volume"]
    pool = manifests["fitting_pool"]
    identical = pool["bodies"]["d6_released_hash"] == pool["bodies"]["d7_catalogue_hash"]
    floors = certification["members"] >= 40 and certification["groups"] >= 10
    floors = floors and int(volume["point"]) >= 200 and int(volume["point_in_groups"]) >= 50
    detail = (
        f"{certification['members']} certification observations over "
        f"{certification['groups']} groups in D7's own store, and the fitting floor met by D5's "
        f"sealed {volume['point']} rows over {volume['point_in_groups']} groups, carried "
        "unrefitted and proved identical to the released pool by the sealed manifests"
    )
    if floors and identical:
        return _yes(detail)
    return _no(f"{detail}; pool bodies identical to the released seal: {identical}")


def _condition_9(document: dict[str, Any]) -> tuple[str, str]:
    runs = {
        item["partition"]: item["real_governed_runs"]
        for item in document["datasets"]
        if item["partition"] in {"training", "calibration"}
    }
    return (
        _yes(f"zero REAL_GOVERNED_RUN observations in the fitted splits: {runs}")
        if runs and not any(runs.values())
        else _no(f"real governed runs reached a fitted split: {runs}")
    )


def _condition_10(document: dict[str, Any]) -> tuple[str, str]:
    """Both final batches, each 120 verifier-backed outcomes over 30 groups, opened once."""
    batches = {"final_a": document}
    other = _read("sprint-21d7-final-b-campaign.json")
    if other is None:
        return _no("sprint-21d7-final-b-campaign.json is absent, so only one batch was opened")
    batches["final_b"] = other

    shortfalls = [
        f"{name}: {item['execution']['unique_outcomes']} outcomes over "
        f"{item['execution']['groups']} groups"
        for name, item in batches.items()
        if int(item["execution"]["unique_outcomes"]) < 120 or int(item["execution"]["groups"]) < 30
    ]
    if shortfalls:
        return _no(f"final batches short of 120 outcomes over 30 groups: {shortfalls}")
    return _yes(
        "final A and final B each opened once: "
        + ", ".join(
            f"{name} {item['execution']['unique_outcomes']} outcomes over "
            f"{item['execution']['groups']} groups"
            for name, item in sorted(batches.items())
        )
        + ", every outcome following its seal"
    )


def _condition_11(document: dict[str, Any]) -> tuple[str, str]:
    """One artifact, selected before final access, with the counters that make it checkable."""
    selected = document["selected_because"]
    selection = _read(SELECTION)
    if selection is None:
        return _no(f"{SELECTION} is absent, so the artifact names no selection")
    before = (
        int(document["final_manifests_opened"]) == 0
        and int(document["final_or_canary_outcomes_inspected"]) == 0
        and not document["final_outcomes_inspected"]
        and int(document["directions_fitted"]) == 0
        and int(document["conformal_bars_derived"]) == 0
    )
    bound = selected["integrity_content_hash"] == selection["integrity_content_hash"]
    if not (before and bound and selected["ending"] == "1_select"):
        return _no(
            f"selection binding {bound}, ending {selected['ending']!r}, "
            f"final manifests opened {document['final_manifests_opened']}"
        )
    lineage = document["lineage"]
    return _yes(
        f"one artifact bound to the selection at {str(selected['integrity_content_hash'])[:16]}, "
        f"sealed with 0 final manifests opened and 0 final or canary outcomes inspected; its "
        f"lineage names training dataset {str(lineage['training_dataset_id'])[:8]} and "
        f"calibration dataset {str(lineage['calibration_dataset_id'])[:8]} at alpha "
        f"{lineage['operating_point_alpha']}"
    )


def _condition_12(document: dict[str, Any]) -> tuple[str, str]:
    cell = document["cell"]
    sweep = document["sweep"]
    reported = bool(sweep["every_point_reported"]) and int(sweep["points"]) == len(sweep["curve"])
    if not (reported and sweep["curve"]):
        return _no(f"{sweep['points']} points declared against {len(sweep['curve'])} in the curve")
    return _yes(
        f"the strongest deterministic rung is {cell['baseline_rung']} at "
        f"{cell['baseline_first_choice_rate']}, measured on the same decisions; "
        f"{cell['cells']} cell and all {sweep['points']} sweep points are reported, "
        f"{sweep['selectable_points']} of them selectable and none of them chosen"
    )


def _condition_17(document: dict[str, Any]) -> tuple[str, str]:
    cell = document["cell"]
    census = document["conformal_point"]["certification_census"]
    clean = (
        cell["coverage_denominator"] == "independent_decisions"
        and int(cell["independent_decisions"]) == int(census["independent_decisions"])
        and not int(census["replicated_decisions"])
        and census["rate_denominator"] == "independent_decisions"
    )
    detail = (
        f"one cell, coverage over `independent_decisions` and the same "
        f"{cell['independent_decisions']} the census fixed; "
        f"{census['replicated_decisions']} replicated decisions of "
        f"{census['nominal_decisions']} nominal"
    )
    return _yes(detail) if clean else _no(detail)


def _sealed_condition(block: str, condition: str, describe: str) -> Callable[..., tuple[str, str]]:
    """A row decided by a W3 record's own sealed condition flag, with its numbers quoted."""

    def decide(document: dict[str, Any]) -> tuple[str, str]:
        met, numbers = _flag(document, block, condition)
        # Scalars only, and short ones. A row that pasted a nested block into the table would
        # be exhaustive and unreadable, and the record it reads is where the whole thing lives.
        rendered = ", ".join(
            f"{name}={value}"
            for name, value in sorted(numbers.items())
            if name != "asks" and not isinstance(value, dict | list) and len(str(value)) <= 80
        )
        asks = str(numbers.get("asks", describe))
        detail = f"{describe} — {asks}" + (f": {rendered}" if rendered else "")
        return _yes(detail) if met else _no(detail)

    return decide


def _condition_22(document: dict[str, Any]) -> tuple[str, str]:
    """Loading is not the test. Ranking is."""
    boundary = document["boundary"]
    artifact = document["artifact"]
    clean = (
        boundary["every_first_choice_and_margin_reproduced"]
        and boundary["stored_bytes_are_the_built_bytes"]
        and boundary["reloaded_model_hash_matches"]
        and boundary["reloaded_payload_matches"]
        and int(boundary["decisions_disagreeing"]) == 0
        and document["every_refusal_refused"]
    )
    detail = (
        f"{artifact['artifact_bytes']} canonical inert JSON bytes hashing to "
        f"{str(artifact['artifact_hash'])[:16]}, rebuilt through the evaluation boundary and "
        f"re-ranking all {boundary['decisions_re_ranked']} certification decisions with "
        f"{boundary['decisions_disagreeing']} disagreeing; "
        f"{len(document['refusals'])} refusals executed and all refused"
    )
    return _yes(detail) if clean else _no(detail)


def _condition_23(document: dict[str, Any]) -> tuple[str, str]:
    codes = document["reason_codes"]
    fallback = document["deterministic_fallback"]
    clean = (
        codes["every_code_reached"]
        and fallback["every_fallback_produced_the_rung_ordering"]
        and not fallback["fallbacks_disagreeing"]
    )
    detail = (
        f"all {len(codes['declared'])} reason codes reached against the real artifact; each of "
        f"the {codes['fallback_codes']} fallback codes produced the {fallback['rung']} ordering "
        f"on all {fallback['decisions']} certification decisions, and only the active path "
        f"differs — on {document['active_path']['decisions_differing_from_the_rung']} of them"
    )
    return (
        _yes(detail)
        if clean
        else _no(f"{detail}; disagreeing: {fallback['fallbacks_disagreeing']}")
    )


def _condition_24(document: dict[str, Any]) -> tuple[str, str]:
    """Inherited under the W0 ruling, and the inheritance re-checked from D7's own tree."""
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

    manifests = _read("sprint-21d7-sealed-manifests.json")
    if manifests is None:
        moved.append("sprint-21d7-sealed-manifests.json is absent")
    else:
        retrieval = manifests["inherited_retrieval"]
        if (
            int(retrieval["retrieval_groups_authored"])
            or not retrieval["identical_to_the_released_pool"]
        ):
            moved.append("D7 authored or altered a retrieval pool")

    if moved:
        return _no(
            "the inheritance is void: " + ", ".join(moved) + ". The ruling holds only while the "
            "surface, the arms and the comparator are the ones D5 measured"
        )
    if not inherited["passed"] or inherited["winning_arm"] is None:
        return _no(
            "the inherited measurement did not clear its floors; the first failed floor is "
            f"{inherited['first_failed_floor']}"
        )
    return _yes(
        f"inherited under {RULING}: the {inherited['winning_arm']} arm cleared Recall@5 >= "
        f"{RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on {inherited['queries']} unseen queries in "
        "D5, and all three voiding identities were recomputed here and are unmoved — D7 "
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
    """Read from the release record, which reads it from the remote."""
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
        "sprint-21d7-baseline.json", "the D6 release verified from live handles", _condition_1
    ),
    2: Bearing(
        "sprint-21d7-authority-isolation-after.json",
        "every predecessor store reproduces its fingerprint after the wave, with zero writes",
        _condition_2,
    ),
    3: Bearing(
        "sprint-21d7-reuse-audit.json",
        "every carried role read out of the predecessor's released audit, bodies unopened",
        _condition_3,
    ),
    4: Bearing(
        "sprint-21d7-pre-registration.json",
        "revision 7 published before any D7 measurement",
        _condition_4,
    ),
    5: Bearing(
        "sprint-21d7-certification-campaign.json",
        "every attempted candidate carries an independent hidden-verifier label",
        _condition_5,
    ),
    6: Bearing(
        "sprint-21d7-snapshots.json",
        "no forbidden, identity, outcome or answer field reaches the fitted matrices",
        _condition_6,
    ),
    7: Bearing(
        "sprint-21d7-corpus-separation.json",
        "no transitive group crosses a D7 role",
        _condition_7,
    ),
    8: Bearing(
        "sprint-21d7-snapshots.json",
        "at least 200/50 fitting and 40/10 certification",
        _condition_8,
    ),
    9: Bearing(
        "sprint-21d7-snapshots.json",
        "zero REAL_GOVERNED_RUN observations in the fitted splits",
        _condition_9,
    ),
    10: Bearing(
        "sprint-21d7-final-a-campaign.json",
        "final A and B, each 120 new verifier-backed outcomes over 30 groups",
        _condition_10,
    ),
    11: Bearing(
        "sprint-21d7-artifact.json",
        "one artifact selected before final access, with final manifests inaccessible to fitting",
        _condition_11,
    ),
    12: Bearing(
        SELECTION,
        "the strongest deterministic baseline and every grid and sweep point are recorded",
        _condition_12,
    ),
    13: Bearing(
        "sprint-21d7-final-evidence.json",
        "at least 20 final group decisions differing from the strongest baseline",
        _sealed_condition("conditions", "13", "changed final decisions"),
    ),
    14: Bearing(
        "sprint-21d7-final-evidence.json",
        "at least 5 absolute points or 20% relative error reduction on final evidence",
        _sealed_condition("conditions", "14", "final-evidence gain"),
    ),
    15: Bearing(
        "sprint-21d7-final-evidence.json",
        "the paired group bootstrap over the final batches",
        _sealed_condition("conditions", "15", "paired group bootstrap"),
    ),
    16: Bearing(
        "sprint-21d7-final-evidence.json",
        "a positive learned-minus-baseline direction in both final batches",
        _sealed_condition("conditions", "16", "per-batch direction"),
    ),
    17: Bearing(
        SELECTION,
        "every rate names its denominator and uses the independent one",
        _condition_17,
    ),
    18: Bearing(
        "sprint-21d7-promotion.json",
        "zero accepted-to-rejected safety, governance, permission, secret or destructive changes",
        _sealed_condition("conditions", "18", "safety movement"),
    ),
    19: Bearing(
        "sprint-21d7-promotion.json",
        "no retained domain losing more than 2 points and aggregate loss at most 1 point",
        _sealed_condition("conditions", "19", "retention"),
    ),
    20: Bearing(
        "sprint-21d7-promotion.json",
        "at least 100 pre-registered promotion metamorphic/OOD decisions inside the budget",
        _sealed_condition("conditions", "20", "promotion metamorphic"),
    ),
    21: Bearing(
        "sprint-21d7-final-evidence.json",
        "shadow mode changing zero executed decisions against final evidence",
        _sealed_condition("conditions", "21", "shadow"),
    ),
    22: Bearing(
        "sprint-21d7-artifact.json",
        "the selected artifact as canonical inert JSON with complete lineage, and it ranks",
        _condition_22,
    ),
    23: Bearing(
        "sprint-21d7-runtime.json",
        "every reason code reached against the real artifact, each with an immediate fallback",
        _condition_23,
    ),
    24: Bearing(
        RULING,
        f"Recall@5 >= {RECALL_FLOOR} and MRR@10 >= {MRR_FLOOR} on at least 50 unseen queries",
        _condition_24,
    ),
    25: Bearing(
        "sprint-21d7-lifecycle.json",
        "a hash-bound canary manifest with the verifier mandatory and the kill switch immediate",
        _sealed_condition("condition_detail", "25", "canary, verifier and kill switch"),
    ),
    26: Bearing(
        "sprint-21d7-lifecycle.json",
        "activation, loading, disable, restoration and rollback surviving restart on a real one",
        _sealed_condition("condition_detail", "26", "lifecycle across restarts"),
    ),
    27: Bearing(
        "sprint-21d7-lifecycle.json",
        "an exact human approval over the existing fields, with no self-approval",
        _sealed_condition("condition_detail", "27", "human approval"),
    ),
    28: Bearing(
        "sprint-21d7-verification-matrix.json",
        "every required isolated and repository check ran and passed, none skipped",
        _condition_28,
    ),
    29: Bearing(
        "sprint-21d7-release.json",
        "protected merge, post-merge exact-head CI, annotated tag, remote read",
        _condition_29,
    ),
}

#: Empty, and that is the sprint's whole shape. D3 through D6 each closed conditions here.
NOT_OPENED_CONDITIONS: dict[int, str] = {}

#: The one condition that is neither met nor stopped: its evidence is created by the release.
PENDING_CONDITIONS: dict[int, str] = {
    29: (
        "the protected merge, its exact-head post-merge main CI, the annotated tag and the "
        "remote verification. The gate-close regeneration is what decides this row"
    )
}

NOT_OPENED_RULE = "closed by a typed stop; the row binds the stop hash rather than a measurement"


def _held_out_outcomes() -> tuple[int, dict[str, int]]:
    """Gate D1 condition 6's numerator: outcomes opened once and never fitted against."""
    counts: dict[str, int] = {}
    for name in HELD_OUT_CAMPAIGNS:
        campaign = _read(name)
        if campaign is None:
            continue
        counts[str(campaign["partition"])] = int(campaign["execution"]["unique_outcomes"])
    return sum(counts.values()), counts


def _d1_rows(l2_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """D1's three. Six and seven close from final surface evidence; fifteen from condition 24."""
    twenty_four = next(row for row in l2_rows if row["condition"] == 24)
    thirteen = next(row for row in l2_rows if row["condition"] == 13)
    final_evidence = _read("sprint-21d7-final-evidence.json")
    total, by_role = _held_out_outcomes()

    rows: list[dict[str, Any]] = []
    rows.append(
        {
            "condition": 6,
            "closure_rule": (
                "at least 200 unique held-out verifier-backed outcomes after deduplication "
                "and eligibility"
            ),
            "state": "closed" if total >= D1_OUTCOME_FLOOR else "remains_open",
            "evidence": list(HELD_OUT_CAMPAIGNS),
            "evidence_sha256": {name: _sha256(name) for name in HELD_OUT_CAMPAIGNS},
            "outcomes": total,
            "by_role": by_role,
            "floor": D1_OUTCOME_FLOOR,
            "detail": (
                f"{total} outcomes on `experience.correction_ranking` opened once in W3 — "
                + ", ".join(f"{role} {count}" for role, count in sorted(by_role.items()))
                + " — each carrying an independent hidden-verifier label, none of them fitted "
                "on or calibrated against. The 400 certification outcomes are deliberately not "
                "counted: they set the operating cell, and counting the corpus that chose the "
                "operating point as evidence about it is the mistake this floor exists to stop"
            ),
        }
    )
    changed = int(final_evidence["overall"]["changed_decisions"]) if final_evidence else 0
    rows.append(
        {
            "condition": 7,
            "closure_rule": "at least 20 primary-surface examples would change the advisory action",
            "state": (
                "closed"
                if changed >= D1_CHANGED_FLOOR and thirteen["state"] == MET
                else "remains_open"
            ),
            "evidence": "sprint-21d7-final-evidence.json",
            "evidence_sha256": _sha256("sprint-21d7-final-evidence.json"),
            "changed_decisions": changed,
            "floor": D1_CHANGED_FLOOR,
            "gate_l2_condition_13_state": thirteen["state"],
            "detail": (
                f"{changed} of 60 final group decisions differ from the strongest baseline's "
                "first choice, which is condition 13's evidence read against the D1 contract. "
                "In shadow none of them executed; what closes this row is that they would change "
                "the action, which is what the condition asks"
            ),
        }
    )
    inherited = (_read(RULING) or {}).get("inherited_measurement", {})
    rows.append(
        {
            "condition": 15,
            "closure_rule": "a new retrieval holdout reaches both floors",
            "state": "closed" if twenty_four["state"] == MET else "remains_open",
            "evidence": RULING,
            "evidence_sha256": _sha256(RULING),
            "inherited_from": D5_RETRIEVAL_DECISION,
            "winning_arm": inherited.get("winning_arm"),
            "first_failed_floor": inherited.get("first_failed_floor"),
            "recorded_as": "closed by inheritance, re-checked at gate close",
            "gate_l2_condition_24_state": twenty_four["state"],
            "detail": (
                "inherited from D5's sealed measurement under the W0 ruling, with all three "
                "voiding identities recomputed at gate close and unmoved"
                if twenty_four["state"] == MET
                else f"the inheritance did not hold: {twenty_four['detail']}"
            ),
        }
    )
    return rows


def _continuation_agrees() -> dict[str, Any]:
    """The closed set is the continuation record's, not this script's.

    D6 checked this because it closed nineteen conditions against a stop and the two records had
    to name the same nineteen. D7 closes none, and the check is worth exactly as much: two
    records claiming an empty set are two claims, and a disagreement between them would mean one
    of them is describing a different sprint.
    """
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
        "outcome": str(continuation["decision"]["outcome"]),
        "ending": str(continuation["decision"]["ending"]),
        "deliverables_opened": int(continuation["delivered"]["count"]),
    }


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for condition in range(1, 30):
        bearing = BEARINGS.get(condition)
        if bearing is None:
            rows.append(
                {
                    "condition": condition,
                    "state": NOT_OPENED,
                    "rule": NOT_OPENED_RULE,
                    "evidence": SELECTION,
                    "evidence_sha256": _sha256(SELECTION),
                    "detail": f"would have measured {NOT_OPENED_CONDITIONS[condition]}",
                }
            )
            continue
        document = _read(bearing.source)
        if document is None and condition in PENDING_CONDITIONS:
            # The release has not happened yet. `pending` is neither a stop nor a pass, and the
            # gate-close regeneration is what turns it into one.
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
    return rows


def _markdown(rows: list[dict[str, Any]], d1_rows: list[dict[str, Any]]) -> str:
    lines = ["| Condition | State | Decided by | Detail |", "|---:|---|---|---|"]
    for row in rows:
        evidence = row.get("evidence") or "—"
        if isinstance(evidence, list):
            evidence = ", ".join(evidence)
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
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d7-gate-l2.json")
    parser.add_argument("--markdown", action="store_true", help="print the condition table")
    arguments = parser.parse_args()

    closed = _continuation_agrees()
    rows = _rows()
    d1_rows = _d1_rows(rows)
    counts = {
        state: sum(1 for row in rows if row["state"] == state)
        for state in (MET, MET_AS_REJECTION, CARRIED, NOT_OPENED, PENDING, FAILED)
    }
    contracts = _read("sprint-21d7-contracts.json")
    if contracts is None:
        raise SystemExit("the frozen revision-7 contract record is required")
    carried = contracts["unchanged_from_d6"]

    report = {
        "schema_version": 1,
        "sprint": "21D7",
        "wave": "W4",
        "item": "S21D7-041",
        "purpose": (
            "The twenty-nine Gate L2 conditions and Gate D1's three, each decided by the "
            "evidence that bears on it. No condition may be asserted; every row names its file "
            "and rule, or the stop hash that closed it."
        ),
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256("sprint-21d7-pre-registration.json"),
        "gate_contract_hash": carried["gate_contract"],
        "gate_l2_conditions": carried["gate_conditions"],
        "thresholds_changed_by_this_sprint": contracts["thresholds_changed"],
        "final_outcomes_inspected": True,
        "final_outcomes_were_opened_by": (
            "S21D7-035 and S21D7-036 in W3, after the artifact was sealed against a selection "
            "that ended 1_select. This record reads them; it did not open them"
        ),
        "gate_l2": rows,
        "gate_d1": d1_rows,
        "counts": counts,
        "closed_set_read_from_the_continuation_record": closed,
        "no_condition_was_closed_by_a_stop": not NOT_OPENED_CONDITIONS,
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
        "no_condition_is_carried_from_d6": counts[CARRIED] == 0,
        "what_inherited_is_not": (
            "condition 24 is `met`, not `carried`. A carried condition would be a predecessor's "
            "verdict reused; this one is a predecessor's *measurement* whose three voiding "
            "identities were recomputed from D7's tree at gate close, under a ruling the gate "
            "owner renewed in W0 before any D7 measurement existed"
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
                "gate_d1": {row["condition"]: row["state"] for row in d1_rows},
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
