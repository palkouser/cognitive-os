#!/usr/bin/env python3
"""S21D5-036. The typed continuation decision, and a complete map of what stays closed.

S21D5-035 measured. This reads what it measured and types the consequence: either a candidate
was selected and the artifact wave opens, or one of Section 3.3's stops fired and every item
that depended on a candidate is recorded as not opened, bound to one stop hash.

The map is exhaustive on purpose. "Nothing else was opened" is a claim about absence, and a
list is what makes absence checkable. Every W4, W5 and W6 item is named with the reason it
stays closed, and so is every Gate L2 condition whose evidence needed a selected candidate.

Three things a correction stop does **not** cancel, each named here so a later reader cannot
infer a wider closure than the measurement supports:

- the **retrieval branch**, which reads its own holdout, closes Gate D1 condition 15 on its own
  evidence, and shares no input with the correction result;
- **S21D5-037**, which extends the promotion payload schema and depends on the pre-registration
  rather than on a selection, and **S21D5-075**, which the backlog marks unconditional;
- **operations, release and the gate-close record**, because Section 8.2 is explicit that a
  negative release is a complete release rather than an abandoned one.

    UV_CACHE_DIR=.cache/uv uv run python scripts/continuation_d5.py
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
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SELECTION = EVIDENCE / "sprint-21d5-learner-selection.json"
DIRECTION_FIT = EVIDENCE / "sprint-21d5-direction-fit.json"
BASELINE = EVIDENCE / "sprint-21d5-baseline-ladder.json"
OPERATING_POINT = EVIDENCE / "sprint-21d5-operating-point.json"
INVARIANCE = EVIDENCE / "sprint-21d5-invariance-regression.json"
SNAPSHOTS = EVIDENCE / "sprint-21d5-snapshots.json"
OUTPUT = EVIDENCE / "sprint-21d5-continuation.json"

#: Every item whose evidence needed a selected candidate, with the reason it stays closed.
#: S21D5-050 is absent because it is done; S21D5-075 is absent because the backlog marks it
#: unconditional; S21D5-037 is absent because it depends on S21D5-016, not on a selection.
DEPENDENT_ITEMS: tuple[tuple[str, str, str], ...] = (
    ("S21D5-051", "W4", "binds a derived threshold into the artifact; no candidate names one"),
    ("S21D5-052", "W4", "fits and stores the selected artifact; nothing was selected"),
    ("S21D5-053", "W4", "proves the loader and resolver against the real artifact"),
    ("S21D5-054", "W4", "routes sequencing through the receipt-aware remainder"),
    ("S21D5-055", "W4", "the selected-artifact vertical slice"),
    ("S21D5-056", "W4", "re-proves mandatory-path and configuration invariance"),
    ("S21D5-057", "W4", "registers the exact artifact and enters SHADOW"),
    ("S21D5-058", "W4", "evidence-bound verification and byte revalidation"),
    ("S21D5-059", "W4", "the pre-final access checkpoint; there is nothing to authorise"),
    ("S21D5-060", "W5", "seals final features and predictions before execution"),
    ("S21D5-061", "W5", "executes final batch A; the final roles stay sealed and unopened"),
    ("S21D5-062", "W5", "executes final batch B"),
    ("S21D5-063", "W5", "paired material benefit at bootstrap seed 21041"),
    ("S21D5-064", "W5", "safety and cross-domain anti-forgetting replay"),
    ("S21D5-065", "W5", "promotion-scale metamorphic and OOD evaluation"),
    ("S21D5-066", "W5", "true shadow mode"),
    ("S21D5-067", "W5", "the strengthened promotion assessment"),
    ("S21D5-068", "W5", "assesses Gate D1 conditions 6, 7 and 15 through the promotion gate"),
    ("S21D5-069", "W5", "advances SHADOW to VERIFIED"),
    ("S21D5-070", "W6", "prepares the activation bundle"),
    ("S21D5-071", "W6", "records human approval"),
    ("S21D5-072", "W6", "activates canary-only routing"),
    ("S21D5-073", "W6", "executes the governed canary"),
    ("S21D5-074", "W6", "kill switch and cause-bound disable"),
    ("S21D5-076", "W6", "bounded steady state"),
    ("S21D5-077", "W6", "final active state and replacement readiness"),
)

#: Gate L2 conditions whose evidence needed a candidate. Conditions 1-9, 12, 17, 28 and 29 are
#: re-evidenced by items that do not depend on one; condition 24 belongs to the retrieval branch.
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

#: §8.2: the stop kind names the successor experiment. One sentence per ending, written before
#: the measurement was read and selected by it rather than composed after it.
SUCCESSORS = {
    "volume_bound": (
        "a corpus sprint with a target volume derived from this yield curve; the residual is "
        "evidence volume and the curve across the 2.25x span is what sizes the successor"
    ),
    "selective_margin_bound": (
        "a sprint that pre-registers a different confidence construction over this same ranker "
        "-- split-conformal over the margin is the obvious candidate -- and not a different "
        "ranker, not a third hypothesis class and not a larger corpus. The direction ranks; the "
        "margin is what cannot certify enough of what it ranks"
    ),
    "hypothesis_class_bound": (
        "a question about why the authored distributions differ, in those words: the "
        "spent-evidence estimate did not transfer to a fresh corpus, and that is the finding, "
        "not which class comes third"
    ),
}

RETRIEVAL_BRANCH = ("S21D5-040", "S21D5-041", "S21D5-042", "S21D5-043", "S21D5-044", "S21D5-045")


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
            SNAPSHOTS,
            INVARIANCE,
            DIRECTION_FIT,
            BASELINE,
            OPERATING_POINT,
            SELECTION,
        )
    }


def _run(output: Path) -> int:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    block = selection["selection"]
    tree = selection["decision_tree"]
    outcome = str(block["outcome"])
    stop_kind = block.get("stop_kind")
    bound = _bound_hashes()

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
                "S21D5-035 selected one candidate under Section 2.3, so the artifact wave opens "
                "on it"
            ),
            "opens": [item for item, _, _ in DEPENDENT_ITEMS],
        }
        not_opened: list[dict[str, str]] = []
        conditions: list[int] = []
    else:
        if stop_kind not in SUCCESSORS:
            raise SystemExit(f"the selection record names an unknown stop kind {stop_kind!r}")
        decision = {
            "kind": "stop",
            "stop_kind": str(stop_kind),
            "reason": str(tree["reading"]),
            "opens": [],
        }
        not_opened = [
            {"item": item, "wave": wave, "why": f"{why}; S21D5-035 selected no candidate"}
            for item, wave, why in DEPENDENT_ITEMS
        ]
        conditions = list(CONDITIONS_NOT_OPENED)

    measured = {
        "independent_decisions": selection["decisions"]["independent_decisions"],
        "baseline_first_choice_rate": selection["baseline"]["first_choice_rate"],
        "strongest_deterministic_rung": selection["baseline"]["strongest_deterministic_rung"],
        "zero_error_coverage": {
            volume: value["zero_error_coverage"]
            for volume, value in selection["risk_coverage_curve"].items()
        },
        "first_choice_rate_over_all_answered": {
            volume: value["first_choice_rate_over_all_answered"]
            for volume, value in selection["risk_coverage_curve"].items()
        },
        "confident_errors_at_the_derived_point": {
            str(cell["volume_rows"]): cell["confident_errors"] for cell in selection["cells"]
        },
        "ineligibility_counts": selection["section_2_3"]["ineligibility_counts"],
        "eligible_cells": selection["section_2_3"]["eligible_cells"],
    }

    evidence = _seal(
        {
            "schema_version": 1,
            "sprint": "21D5",
            "wave": "W2",
            "items": ["S21D5-036"],
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
                "items": not_opened,
                "count": len(not_opened),
                "gate_l2_conditions": conditions,
                "why_a_list_and_not_a_sentence": (
                    "absence is what a list makes checkable. A later record that opens one of "
                    "these has to remove it from a named set rather than reinterpret a phrase"
                ),
            },
            "successor_experiment": (
                None if outcome == "candidate" else SUCCESSORS[str(stop_kind)]
            ),
            "not_cancelled_by_this_stop": {
                "retrieval_branch": {
                    "items": list(RETRIEVAL_BRANCH),
                    "plus": ["S21D5-046", "S21D5-047"],
                    "why": (
                        "the two branches are independent after W0. The retrieval branch reads "
                        "its own freshly authored holdout, decides Gate L2 condition 24 and "
                        "Gate D1 condition 15 on that evidence, and shares no input with the "
                        "correction measurement. Section 8.2 requires the retrieval result to "
                        "be retained when it is valid, whichever way this branch went"
                    ),
                },
                "d1_condition_15": (
                    "decidable by S21D5-046 on retrieval evidence even though S21D5-068, which "
                    "would have assessed it through the promotion gate, stays closed"
                ),
                "s21d5_037": (
                    "the promotion payload schema extension depends on S21D5-016, not on a "
                    "selection; it is a contract, and a contract with no payload to carry is "
                    "still the contract the successor sprint inherits"
                ),
                "s21d5_075": "the backlog marks receipt-selected rollback unconditional",
                "operations_release_and_gate_close": {
                    "items": [
                        "S21D5-080",
                        "S21D5-081",
                        "S21D5-082",
                        "S21D5-083",
                        "S21D5-084",
                        "S21D5-085",
                        "S21D5-086",
                        "S21D5-090",
                        "S21D5-091",
                        "S21D5-092",
                        "S21D5-093",
                        "S21D5-094",
                        "S21D5-095",
                    ],
                    "why": (
                        "Section 8.2: a negative release is a complete release, not an "
                        "abandoned one. The evidence baseline is protected and verified from "
                        "the remote exactly as a passing release would be"
                    ),
                },
            },
            "what_this_decision_does_not_authorise": [
                "reading any D5 final, promotion or canary outcome",
                "re-deriving the operating point or re-fitting either direction",
                "lowering the 0.40 coverage floor or any other Section 2.3 threshold",
                "re-choosing the hypothesis class, its regulariser or its confidence",
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
                "items_not_opened": len(not_opened),
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
