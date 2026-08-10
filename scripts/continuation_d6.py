#!/usr/bin/env python3
"""S21D6-036. The typed continuation decision, and a complete map of what stays closed.

S21D6-035 measured. This reads what it measured and types the consequence: either a candidate was
selected and the artifact wave opens, or one of §3.4's endings fired and every piece of work that
depended on a candidate is recorded as not opened, bound to one stop hash.

The map is exhaustive on purpose. "Nothing else was opened" is a claim about absence, and a list
is what makes absence checkable. Every W3 deliverable is named with the reason it stays closed,
and so is every Gate L2 condition whose evidence needed a selected candidate.

The successor sentence is **read from the sealed contracts record, not composed here.** §3.4's
four endings were written in W0 with `measured_values: 0`, and the whole point of typing an
ending is that the measurement selects one of them rather than authoring one. A successor
sentence written after the result would be the measurement arguing for its own follow-up.

Two things this stop does **not** cancel, each named so a later reader cannot infer a wider
closure than the measurement supports:

- **Gate L2 condition 24**, which D6 inherits under `sprint-21d6-condition-24-ruling.json` and
  which shares no input with the correction result. The ruling voids itself if D6 touched the
  surface, the arms or the comparator; it did not, and the gate assessment re-checks that rather
  than trusting this sentence;
- **operations, release and the gate-close record**, because a negative release is a complete
  release rather than an abandoned one -- the discipline D3, D4 and D5 each kept.

    UV_CACHE_DIR=.cache/uv uv run python scripts/continuation_d6.py
"""

from __future__ import annotations

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.domain.common import utc_now  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d6-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d6-contracts.json"
AMENDMENT = EVIDENCE / "sprint-21d6-contracts-amendment-2.json"
CONDITION_24_RULING = EVIDENCE / "sprint-21d6-condition-24-ruling.json"
SELECTION = EVIDENCE / "sprint-21d6-learner-selection.json"
DIRECTIONS = EVIDENCE / "sprint-21d6-directions.json"
BASELINE = EVIDENCE / "sprint-21d6-baseline-ladder.json"
CONFORMAL_POINT = EVIDENCE / "sprint-21d6-conformal-point.json"
INVARIANCE = EVIDENCE / "sprint-21d6-invariance-regression.json"
SNAPSHOTS = EVIDENCE / "sprint-21d6-snapshots.json"
OUTPUT = EVIDENCE / "sprint-21d6-continuation.json"

#: The W3 deliverables, by the words the backlog's wave table uses. D6's backlog never allocated
#: item numbers below the wave row for W3, and inventing them here would put identifiers in the
#: evidence that no plan ever carried. The work is named instead, which is what a reader checks.
DEPENDENT_WORK: tuple[tuple[str, str], ...] = (
    ("the v3 artifact bound to the conformal point", "no candidate names a bar to bind"),
    ("loader, resolver and sequencer against a real artifact", "there is no real artifact"),
    ("final batch A on the carried role", "the 30 final_a groups stay sealed and unopened"),
    ("final batch B on the carried role", "the 30 final_b groups stay sealed and unopened"),
    ("promotion assessment and the metamorphic submanifest", "nothing was promoted"),
    ("shadow mode on a registered component", "nothing was registered"),
    ("the canary manifest, its approval and the kill switch", "the 5 canary groups stay sealed"),
    ("activation and the deliberate rollback", "there is nothing to activate or roll back"),
)

#: Gate L2 conditions whose evidence needed a candidate. Conditions 1-9, 12, 17, 28 and 29 are
#: re-evidenced by work that does not depend on one; condition 24 is inherited under its ruling.
CONDITIONS_NOT_OPENED: tuple[int, ...] = (
    10,
    11,
    13,
    14,
    15,
    16,
    18,
    19,
    20,
    21,
    22,
    23,
    25,
    26,
    27,
)

#: Gate D1 conditions in the same position, and the one that is not.
D1_NOT_OPENED: tuple[int, ...] = (6, 7)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _digest(_canonical(value))
    return sealed


def _bound_hashes() -> dict[str, str]:
    return {
        path.name: _digest(path.read_bytes())
        for path in (
            PRE_REGISTRATION,
            CONTRACTS,
            AMENDMENT,
            SNAPSHOTS,
            INVARIANCE,
            DIRECTIONS,
            BASELINE,
            CONFORMAL_POINT,
            SELECTION,
        )
    }


def _successors() -> dict[str, str]:
    """§3.4's endings, read out of the record W0 sealed with `measured_values: 0`.

    The keys are the stop kinds; the sealed record spells them with an ordinal prefix, which is
    stripped so a stop kind written by S21D6-035 finds its own sentence.
    """
    endings = json.loads(CONTRACTS.read_text(encoding="utf-8"))["contracts"]["decision_tree"][
        "endings"
    ]
    return {name.split("_", 1)[1]: str(text) for name, text in endings.items()}


def _run(output: Path) -> int:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    block = selection["selection"]
    tree = selection["decision_tree"]
    outcome = str(block["outcome"])
    stop_kind = block.get("stop_kind")
    bound = _bound_hashes()
    successors = _successors()

    # The stop hash is over the stop and everything it was decided from, so a later record that
    # claims this stop has one value to quote and no room to quote it from a different reading.
    stop_hash = _digest(
        _canonical(
            {
                "outcome": outcome,
                "stop_kind": stop_kind,
                "reading": tree["reading"],
                "selection_integrity_content_hash": selection["integrity_content_hash"],
                "bound": bound,
            }
        )
    )

    if outcome == "candidate":
        decision = {
            "kind": "proceed",
            "stop_kind": None,
            "reason": (
                "S21D6-035 selected one candidate under the amended §2.3, so the artifact wave "
                "opens on it"
            ),
            "opens": [work for work, _ in DEPENDENT_WORK],
        }
        not_opened: list[dict[str, str]] = []
        conditions: list[int] = []
        d1_conditions: list[int] = []
    else:
        if stop_kind not in successors:
            raise SystemExit(
                f"the selection record names {stop_kind!r}, which is not one of the endings the "
                f"sealed contract published: {sorted(successors)}"
            )
        decision = {
            "kind": "stop",
            "stop_kind": str(stop_kind),
            "reason": str(tree["reading"]),
            "opens": [],
        }
        not_opened = [
            {"work": work, "wave": "W3", "why": f"{why}; S21D6-035 selected none"}
            for work, why in DEPENDENT_WORK
        ]
        conditions = list(CONDITIONS_NOT_OPENED)
        d1_conditions = list(D1_NOT_OPENED)

    selectable = next(cell for cell in selection["cells"] if cell["selectable"])
    measured = {
        "independent_decisions": selection["decisions"]["independent_decisions"],
        "baseline_first_choice_rate": selection["baseline"]["first_choice_rate"],
        "strongest_deterministic_rung": selection["baseline"]["strongest_deterministic_rung"],
        "alpha": selection["section_2_3_as_amended"]["alpha"],
        "ceiling_c": selection["section_2_3_as_amended"]["ceiling_c"],
        "conformal_coverage": {
            volume: value["conformal_coverage"]
            for volume, value in selection["risk_coverage_curve"].items()
        },
        "first_choice_rate_over_all_answered": {
            volume: value["first_choice_rate_over_all_answered"]
            for volume, value in selection["risk_coverage_curve"].items()
        },
        "errors_admitted": {
            str(cell["volume_rows"]): cell["errors_admitted"] for cell in selection["cells"]
        },
        "error_upper_bound_95": {
            str(cell["volume_rows"]): cell["error_upper_bound_95"] for cell in selection["cells"]
        },
        "realised_leak_rate": {
            str(cell["volume_rows"]): cell["leak"]["realised_leak_rate"]
            for cell in selection["cells"]
        },
        "what_the_zero_error_prefix_rule_would_have_admitted": {
            volume: value["what_the_zero_error_prefix_rule_would_have_admitted"]
            for volume, value in selection["risk_coverage_curve"].items()
        },
        "ineligibility_counts": selection["section_2_3_as_amended"]["ineligibility_counts"],
        "the_one_failing_condition_on_the_selectable_cell": selectable["ineligible_reasons"],
    }

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D6",
            "wave": "W2",
            "items": ["S21D6-036"],
            "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pre_registration_sha256": bound[PRE_REGISTRATION.name],
            "bound_hashes": bound,
            "final_or_canary_outcomes_inspected": 0,
            "measurements_opened": 0,
            "decision": decision,
            "stop_hash": stop_hash,
            "measured": measured,
            "immutable": outcome != "candidate",
            "not_opened": {
                "work": not_opened,
                "count": len(not_opened),
                "gate_l2_conditions": conditions,
                "gate_d1_conditions": d1_conditions,
                "why_a_list_and_not_a_sentence": (
                    "absence is what a list makes checkable. A later record that opens one of "
                    "these has to remove it from a named set rather than reinterpret a phrase"
                ),
            },
            "successor_experiment": (
                None if outcome == "candidate" else successors[str(stop_kind)]
            ),
            "successor_sentence_read_from": {
                "record": CONTRACTS.name,
                "sha256": bound[CONTRACTS.name],
                "why": (
                    "§3.4's endings were written in W0 with measured_values: 0. Typing an ending "
                    "means the measurement selects one of them; a successor sentence composed "
                    "after the result would be the measurement arguing for its own follow-up"
                ),
            },
            # The sealed sentence stays exactly as written; what the measurement found is
            # recorded beside it, never in place of it. Step 2's sentence sizes the successor as
            # a volume problem -- more wrong decisions in the conformal half buy a tighter alpha
            # -- and that premise is checkable on the published sweep.
            "successor_sentence_qualified_by_the_measurement": {
                "the_sealed_sentence_assumes": (
                    "that a tighter alpha would have cleared the ceiling, so that the binding "
                    "constraint is the number of wrong decisions available in the conformal half"
                ),
                "what_the_sweep_shows": {
                    str(cell["volume_rows"]): {
                        "pair_is_reachable_at_any_threshold": cell["joint_feasibility"][
                            "pair_is_reachable_at_any_threshold"
                        ],
                        "sweep_points": cell["joint_feasibility"]["sweep_points"],
                        "best_bound_at_or_above_the_coverage_floor": cell["joint_feasibility"][
                            "best_bound_at_or_above_the_coverage_floor"
                        ],
                        "best_coverage_under_the_ceiling": cell["joint_feasibility"][
                            "best_coverage_under_the_ceiling"
                        ],
                    }
                    for cell in selection["cells"]
                },
                "reading": (
                    "no threshold on either published curve satisfies the amended pair, so a "
                    "tighter alpha moves the bar along a curve every point of which misses. On "
                    "this evidence the binding constraint is the ranker's error rate on a fresh "
                    "corpus, not the volume of the conformal half. §2.1 drew exactly this "
                    "distinction for the pre-amendment pair, and 'infeasible' and 'unmet' size "
                    "two different successors"
                    if not any(
                        cell["joint_feasibility"]["pair_is_reachable_at_any_threshold"]
                        for cell in selection["cells"]
                    )
                    else "a reported point satisfies the pair, so the sealed sentence's premise "
                    "holds and the successor is the volume question it names"
                ),
                "what_this_does_not_do": (
                    "it does not change the typed ending, choose a threshold, or author a "
                    "successor. Every point it reads is already published and none is selectable"
                ),
            },
            "not_cancelled_by_this_stop": {
                "gate_l2_condition_24": {
                    "record": CONDITION_24_RULING.name,
                    "sha256": _digest(CONDITION_24_RULING.read_bytes()),
                    "why": (
                        "the ruling inherits D5's sealed retrieval measurement for any sprint "
                        "that changes neither the surface, the arms nor the comparator. The "
                        "correction stop touches none of the three, so it cannot void it -- and "
                        "the gate assessment re-checks the three identities rather than trusting "
                        "this sentence"
                    ),
                },
                "operations_release_and_gate_close": {
                    "why": (
                        "a negative release is a complete release, not an abandoned one. The "
                        "evidence baseline is protected and verified from the remote exactly as "
                        "a passing release would be"
                    ),
                },
            },
            "what_this_decision_does_not_authorise": [
                "reading any D6 final, promotion or canary outcome",
                "re-deriving the conformal bar, re-choosing alpha, C or the selectable cell",
                "lowering the 0.40 coverage floor, the 0.15 ceiling or any other §2.3 threshold",
                "refitting either direction or re-choosing the hypothesis class",
                "a second split of the calibration evidence or a second alpha",
                "claiming Gate L2 passes, or unblocking Sprint 22A",
            ],
        }
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": output.name,
                "decision": decision["kind"],
                "stop_kind": decision["stop_kind"],
                "stop_hash": stop_hash,
                "work_not_opened": len(not_opened),
                "gate_l2_conditions_not_opened": len(conditions),
                "integrity_content_hash": evidence["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    return _run(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
