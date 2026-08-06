#!/usr/bin/env python
"""S21D3-091: the twenty-nine Gate L2 conditions and Gate D1's three, decided by evidence.

    scripts/gate_assessment_d3.py [--output docs/.../sprint-21d3-gate-l2.json] [--markdown]

Every condition is a row, and every row names the file and the rule that decided it. A
condition with no bearing evidence is `not_opened` bound to the stop hash that closed it, never
`met` — the assessment cannot assert a pass, only read one.

Five states, because two of them carry the sprint:

* `met` — the evidence exists and the rule holds;
* `met_as_rejection` — the rule was applied, the answer was no, and the recorded no *is* the
  condition being satisfied. Condition 24's floors were measured and not cleared;
* `carried` — the predecessor's evidence is reused unchanged, as revision 3 permits;
* `not_opened` — a stop closed it, and the row names the stop hash;
* `failed` — evidence exists and the rule does not hold.

`not_opened` is not a soft `met`. The gate passes only when every applicable condition is met,
which is why a sprint with 0 failures can still not pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Bearing:
    """Which produced evidence bears on one condition, and what decides it.

    Written out per condition rather than inferred, because the manifest's declared handle is
    the file the *positive* path would have produced and most of those do not exist. Naming the
    file that actually bears on the condition is the whole content of this assessment.
    """

    source: str
    rule: str
    decide: Any


def _campaign(document: dict[str, Any]) -> dict[str, Any]:
    return {part["partition"]: part for part in document["partitions"]}


def _bearings() -> dict[int, Bearing]:
    """Condition number to the evidence that decides it. Absent means no evidence bears."""
    bearings: dict[int, Bearing] = {
        1: Bearing(
            "sprint-21d3-baseline.json",
            "the branch descends from the frozen baseline and the D2 release is re-read",
            lambda d: bool(d["d2_release"]) and d["zero_predecessor_writes"],
        ),
        2: Bearing(
            "sprint-21d3-baseline.json",
            "all four predecessor store fingerprints reproduce",
            lambda d: all(
                item["matches_expected"] for item in d["predecessor_artifact_stores"].values()
            ),
        ),
        3: Bearing(
            "sprint-21d3-d2-reconciliation.json",
            "the D2 denominator and retrieval reconciliation is published and immutable",
            lambda d: bool(d.get("integrity_content_hash")),
        ),
        4: Bearing(
            "sprint-21d3-pre-registration.json",
            "zero D3 measurements precede publication",
            lambda d: all(
                value == 0
                for key, value in d["chronology"].items()
                if key != "immutable_d2_reconciliation_replays"
            ),
        ),
        5: Bearing(
            "sprint-21d3-runtime-invariance.json",
            "the mandatory decision is identical under every fallback configuration, and only "
            "a bounded campaign configuration reorders",
            lambda d: (
                d["mandatory_path_invariance"]["identical"]
                and d["mandatory_path_invariance"]["only_a_bounded_campaign_may_reorder"]
            ),
        ),
        6: Bearing(
            "sprint-21d3-vertical-slice.json",
            "the fitted matrix scans all 390 v2 columns and carries no forbidden field",
            lambda d: (
                d["fitted_columns"] == 390 and d["encoder_version"] == "correction-ranking-v2"
            ),
        ),
        7: Bearing(
            "sprint-21d3-separation.json",
            "zero groups cross a role and no near clone survives",
            lambda d: (
                not d["groups_crossing_any_role"]
                and not d["near_clone"]["cross_group_collisions_touching_d3"]
            ),
        ),
        8: Bearing(
            "sprint-21d3-self-play-campaign.json",
            "200 fitting outcomes over 50 groups and 80 calibration over 20",
            lambda d: (
                d["snapshot"]["datasets"]["fitting"]["observation_count"] == 200
                and d["snapshot"]["datasets"]["fitting"]["groups"] == 50
                and d["snapshot"]["datasets"]["calibration"]["observation_count"] == 80
                and d["snapshot"]["datasets"]["calibration"]["groups"] == 20
            ),
        ),
        9: Bearing(
            "sprint-21d3-self-play-campaign.json",
            "zero real governed runs entered fitting or calibration",
            lambda d: all(
                row["real_governed_runs"] == 0 for row in d["snapshot"]["datasets"].values()
            ),
        ),
        12: Bearing(
            "sprint-21d3-learner-selection.json",
            "every attempted rung is retained on the ladder and every frozen setting measured",
            lambda d: bool(d["baseline_ladder"]["rungs"]) and d["grid"]["settings_attempted"] == 24,
        ),
        17: Bearing(
            "sprint-21d3-calibration-metamorphic.json",
            "ranking decisions and candidate outcomes are counted apart",
            lambda d: d["valid_decisions"] != d["candidate_outcomes"],
        ),
        20: Bearing(
            "sprint-21d3-calibration-metamorphic.json",
            "at least 100 ranking decisions over at least 10 groups",
            lambda d: d["valid_decisions"] >= 100 and d["source_groups"] >= 10,
        ),
        22: Bearing(
            "sprint-21d3-runtime-invariance.json",
            "the artifact is canonical JSON and every unsafe or wrong-schema load refuses",
            lambda d: d["direct_loader"]["every_case_refused"],
        ),
        23: Bearing(
            "sprint-21d3-runtime-invariance.json",
            "every runtime reason code is reachable and each falls back deterministically",
            lambda d: d["resolver_matrix"]["every_reason_code_is_reachable"],
        ),
        24: Bearing(
            "sprint-21d3-retrieval-holdout-result.json",
            "Recall@5 >= 0.70 and MRR@10 >= 0.50 on at least 50 distinct unseen queries",
            lambda d: d["decision"]["winning_arm"] is not None,
        ),
        28: Bearing(
            "sprint-21d3-verification-matrix.json",
            "every required isolated and repository check ran and passed, none skipped",
            lambda d: not d["failed_rows"] and d["every_row_decided"],
        ),
    }
    # S21D3-095. Condition 29 bears only once the release record exists. Before that it stays
    # in _PENDING and reads `not opened`, which is what a release in progress is. Adding the
    # bearing unconditionally would report `failed` on every pre-release run, and a condition
    # that fails because the work has not happened yet is not a failed condition.
    if (EVIDENCE / "sprint-21d3-release.json").is_file():
        bearings[29] = Bearing(
            "sprint-21d3-release.json",
            "the protected merge, its exact-head post-merge main CI and the remote tag agree",
            lambda d: (
                d["release"]["implementation_merge_commit"]
                == d["release"]["peeled_commit"]
                == d["release"]["remote_main"]
                == d["release"]["exact_head_main_ci_head_sha"]
                and d["release"]["exact_head_main_ci_conclusion"] == "success"
                and d["release"]["tag_object"] == d["release"]["remote_tag_object"]
                and d["release"]["tag_type"] == "tag"
                and d["branch_protection_after_release"]["unchanged_from_the_w0_reading"]
            ),
        )
    return bearings


#: Conditions closed by a stop rather than by evidence, and which stop closed each. The two
#: stops are named rather than shared: a reader has to be able to tell which experiment ended.
_STOPS: dict[int, str] = {
    10: "selection",
    11: "selection",
    13: "selection",
    14: "selection",
    15: "selection",
    16: "selection",
    18: "selection",
    19: "selection",
    21: "selection",
    25: "selection",
    26: "selection",
    27: "selection",
}

#: The one condition that is neither evidence nor stop: the release itself, still in progress
#: while this assessment is written.
_PENDING = {29: "the protected implementation release and its post-merge CI"}


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(name: str) -> dict[str, Any] | None:
    path = EVIDENCE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def _stop_hashes() -> dict[str, dict[str, str]]:
    selection = _read("sprint-21d3-learner-selection.json")
    holdout = _read("sprint-21d3-retrieval-holdout-result.json")
    if selection is None or holdout is None:  # pragma: no cover - both are committed
        raise SystemExit("the selection and holdout records are required to name the stops")
    return {
        "selection": {
            "hash": selection["selection"]["content_hash"],
            "source": "S21D3-039 null candidate selection",
        },
        "retrieval": {
            "hash": holdout["decision"]["stop_hash"],
            "source": "S21D3-045 negative retrieval result",
        },
    }


def _rows() -> list[dict[str, Any]]:
    manifest = _read("sprint-21d3-gate-manifest.json")
    if manifest is None:  # pragma: no cover - committed in W0
        raise SystemExit("the frozen gate manifest is required")
    bearings = _bearings()
    stops = _stop_hashes()
    rows: list[dict[str, Any]] = []

    for declared in manifest["manifest"]["gate_l2"]:
        number = declared["condition"]
        row: dict[str, Any] = {
            "condition": number,
            "metric_or_invariant": declared["metric_or_invariant"],
            "floor_or_rule": declared["floor_or_rule"],
            "frozen_content_hash": declared["content_hash"],
            "declared_handle": declared["evidence_handle"],
        }
        bearing = bearings.get(number)
        if bearing is not None:
            document = _read(bearing.source)
            if document is None:
                row |= {"state": FAILED, "evidence": bearing.source, "detail": "evidence absent"}
            else:
                held = bool(bearing.decide(document))
                if number == 24:
                    # Measured, and the answer was no. The recorded rejection is the condition
                    # being satisfied as a condition, and the gate failing as a gate.
                    row |= {
                        "state": MET if held else MET_AS_REJECTION,
                        "detail": (
                            "both floors cleared"
                            if held
                            else "the floors were measured on 60 unseen queries and no arm "
                            "cleared them; the first failed floor is recall_at_5"
                        ),
                    }
                elif declared.get("predecessor_reuse") and number in {1, 2, 3}:
                    row |= {"state": MET if held else FAILED, "detail": bearing.rule}
                else:
                    row |= {"state": MET if held else FAILED, "detail": bearing.rule}
                row |= {
                    "evidence": bearing.source,
                    "evidence_sha256": _hash(
                        (EVIDENCE / bearing.source).read_text(encoding="utf-8")
                    ),
                    "rule": bearing.rule,
                }
        elif number in _STOPS:
            stop = stops[_STOPS[number]]
            row |= {
                "state": NOT_OPENED,
                "stop_hash": stop["hash"],
                "stop_source": stop["source"],
                "detail": f"closed by the {_STOPS[number]} stop before it could be measured",
            }
        elif number in _PENDING:
            row |= {
                "state": NOT_OPENED,
                "detail": f"in progress: {_PENDING[number]}",
                "provisional": True,
            }
        else:  # pragma: no cover - every condition is covered by one of the three branches
            row |= {"state": FAILED, "detail": "no rule and no stop covers this condition"}
        rows.append(row)
    return rows


def _d1_rows() -> list[dict[str, Any]]:
    manifest = _read("sprint-21d3-gate-manifest.json")
    holdout = _read("sprint-21d3-retrieval-holdout-result.json")
    if manifest is None or holdout is None:  # pragma: no cover
        raise SystemExit("the gate manifest and holdout record are required")
    stops = _stop_hashes()
    rows = []
    for declared in manifest["manifest"]["gate_d1_open"]:
        number = declared["condition"]
        row = {
            "condition": number,
            "closure_rule": declared["closure_rule"],
            "frozen_content_hash": declared["content_hash"],
            "declared_handle": declared["evidence_handle"],
        }
        if number == 15:
            row |= {
                "state": NOT_OPENED,
                "detail": (
                    "D3 was condition 15's remediation route. The holdout was executed once on "
                    "60 unseen queries and no arm cleared either floor, so the condition "
                    f"{holdout['decision']['gate_d1_condition_15']}"
                ),
                "evidence": "sprint-21d3-retrieval-holdout-result.json",
                "stop_hash": stops["retrieval"]["hash"],
                "stop_source": stops["retrieval"]["source"],
            }
        else:
            row |= {
                "state": NOT_OPENED,
                "detail": (
                    "closed by the selection stop: the outcomes that would close it are final "
                    "and canary outcomes, which were never authorised"
                ),
                "stop_hash": stops["selection"]["hash"],
                "stop_source": stops["selection"]["source"],
            }
        rows.append(row)
    return rows


def _markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["| # | Condition | State | Decided by |", "|---|---|---|---|"]
    for row in rows:
        state = row["state"].replace("_", " ")
        evidence = row.get("evidence", row.get("stop_source", "—"))
        lines.append(
            f"| {row['condition']} | {row['metric_or_invariant']} | **{state}** | "
            f"{row['detail']} ({evidence}) |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EVIDENCE / "sprint-21d3-gate-l2.json")
    parser.add_argument("--markdown", action="store_true", help="print the condition table")
    arguments = parser.parse_args()

    rows = _rows()
    d1 = _d1_rows()
    counts = {
        state: sum(1 for row in rows if row["state"] == state)
        for state in (MET, MET_AS_REJECTION, CARRIED, NOT_OPENED, FAILED)
    }
    report = {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W8",
        "item": "S21D3-091",
        "purpose": (
            "The twenty-nine Gate L2 conditions and Gate D1's three open ones, each decided by "
            "the evidence that bears on it. No condition may be asserted; every row names its "
            "file and rule, or the stop hash that closed it."
        ),
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _hash(
            (EVIDENCE / "sprint-21d3-pre-registration.json").read_text(encoding="utf-8")
        ),
        "final_outcomes_inspected": False,
        "gate_manifest_hash": _read("sprint-21d3-gate-manifest.json")["manifest"][  # type: ignore[index]
            "content_hash"
        ],
        "verdict": "gate_l2_does_not_pass",
        "verdict_reason": (
            "the gate passes only when every applicable condition is met; "
            f"{counts[NOT_OPENED]} were never opened and condition 24 is met as a rejection"
        ),
        "counts": counts,
        "stops": _stop_hashes(),
        "gate_l2": rows,
        "gate_d1_open": d1,
        "provisional_until": (
            "the protected merge, its exact-head post-merge main CI, and remote tag verification"
        ),
    }
    report["integrity_content_hash"] = _hash(json.dumps(report, sort_keys=True, default=str))

    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if arguments.markdown:
        print(_markdown(rows))
    else:
        print(json.dumps({"output": arguments.output.name, "counts": counts}, indent=2))
    return 0 if counts[FAILED] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
