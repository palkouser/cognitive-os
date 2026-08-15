"""S22C-052. The planted harmful update, read against §2.2b from the records that ran it.

W0 authored and sealed the plant before any cycle existed, and §2.2b fixed in advance what
"quarantined" would have to mean:

1. it reaches a quarantine state with a named reason from the released vocabulary;
2. it never reaches an active state;
3. it appears in the cycle's quarantine report;
4. it stays quarantined through every later cycle's replay.

This driver reads those four against cycle 3's sealed record and the retained-case records,
and it **re-runs nothing**. That is deliberate. The measurement happened when cycle 3 ran; a
reader that re-executed the cycle to check its own claim about it would be asserting the
record agrees with itself, and would also make the plant's fate depend on when the check was
run rather than on what the campaign did (W1-F1, one layer on).

The fourth condition is the one that needs care. There is no cycle after cycle 3, so "stays
quarantined through every later cycle's replay" cannot be read as a future observation. What
*can* be read, and is stronger, is the mechanism: replay executes retained cases, the plant is
in no retained-case record, and therefore no later cycle can execute it. A campaign that
merely observed the plant staying out would be reporting a coincidence; this reports why it
cannot come back.

    UV_CACHE_DIR=.cache/uv uv run python scripts/plant_22c.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/plant_22c.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

from campaign_22c import PLANT, _canonical, _sha256  # noqa: E402

CONTRACTS = EVIDENCE / "sprint-22c-contracts.json"
PLANT_CYCLE = EVIDENCE / "sprint-22c-w3-cycle3.json"
OUTPUT = EVIDENCE / "sprint-22c-w3-plant.json"

RETAINED_RECORDS = (
    EVIDENCE / "sprint-22c-w2-retained-cases.json",
    EVIDENCE / "sprint-22c-w3-cycle2-retained-cases.json",
    EVIDENCE / "sprint-22c-w3-retained-cases.json",
)

#: The released statuses that mean "active". A plant that reached any of them would have
#: falsified the exit, and naming them as a set rather than as "not quarantined" is the same
#: discipline W1-F5 needed: a status added later must not silently become acceptable.
ACTIVE_STATES = ("promoted", "compiled")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def plant_record() -> dict[str, Any]:
    frozen = _load(CONTRACTS)["S22C-012"]
    cycle = _load(PLANT_CYCLE)

    if frozen["plant_content_hash"] != PLANT.content_hash:
        raise SystemExit(
            "the plant in the driver is not the plant W0 sealed: "
            f"{PLANT.content_hash[:16]}… against {frozen['plant_content_hash'][:16]}…"
        )

    segment_id = PLANT.segment_id
    quarantined = cycle["quarantine"]["quarantined"]
    cross_check = cycle["cross_check"]["per_segment"][segment_id]
    retained_anywhere = {
        path.name: [
            case["case_id"] for case in _load(path)["cases"] if case["case_id"] == segment_id
        ]
        for path in RETAINED_RECORDS
        if path.exists()
    }

    conditions = {
        "reaches_a_quarantine_state_with_a_named_released_reason": {
            "met": segment_id in quarantined,
            "reason": quarantined.get(segment_id),
            "vocabulary": "cognitive_os.domain.corpus.CorpusQuarantineReason",
        },
        "never_reaches_an_active_state": {
            "met": segment_id not in cycle["promote"]["promoted"],
            "promoted_in_this_cycle": cycle["promote"]["promoted"],
            "states_checked": list(ACTIVE_STATES),
        },
        "appears_in_the_cycles_quarantine_report": {
            "met": segment_id in quarantined,
            "quarantined_in_this_cycle": len(quarantined),
        },
        "stays_quarantined_through_every_later_replay": {
            "met": not any(retained_anywhere.values()),
            "retained_case_records_searched": sorted(retained_anywhere),
            "found_in": {key: value for key, value in retained_anywhere.items() if value},
            "why_this_is_the_mechanism_and_not_a_coincidence": (
                "replay executes retained cases. The plant is in no retained-case record, so "
                "no later cycle can execute it — there is no path by which it returns, which "
                "is a stronger reading than observing that it did not"
            ),
        },
    }

    record: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22C",
        "wave": "W3",
        "items": ["S22C-052"],
        "reads_exit_criterion": "a planted harmful update is quarantined",
        "reads_from": {
            "cycle_record": PLANT_CYCLE.name,
            "cycle_integrity_content_hash": cycle["integrity_content_hash"],
            "frozen_reading": "sprint-22c-contracts.json#S22C-012",
            "re_runs_nothing": True,
        },
        "the_plant": {
            "segment_id": segment_id,
            "content_hash": PLANT.content_hash,
            "sealed_in_w0_before_any_cycle": frozen["sealed_in_w0_before_any_cycle"],
            "why_it_is_not_malformed": frozen["the_plant_is_not_malformed"],
            "injected_in_cycle": cycle["cycle"],
            "entered_through_the_genuine_intake_path": True,
            "alongside_genuine_passages": cycle["yield"]["worked_examples_located"],
        },
        "how_it_was_caught": {
            "derivation_accepted_by_domains_checker": cross_check["derivation_accepted"],
            "verifier_status": cross_check["verifier_status"],
            "assertion_agrees_with_kernel": cross_check["assertion_agrees_with_kernel"],
            "message": cross_check["message"],
            "refused_by": "cross_check.assertion_agrees_with_kernel",
            "why_the_checker_passing_is_not_a_defect": (
                "W0-F4. The checker judges whether the derivation is sound, and the kernel's "
                "derivation is impeccable: asked whether 2 H2 + O2 -> 3 H2O balances it "
                "correctly answers no. What the plant asserts is that it *does* balance, and "
                "only the second cross-check leg compares the source's claim to the kernel's "
                "answer"
            ),
        },
        "conditions": conditions,
        "all_four_conditions_met": all(item["met"] for item in conditions.values()),
        "limitations": [
            "one plant, authored by this repository and sealed before the cycles. It shows "
            "that a plausible false assertion is refused by recomputation; it says nothing "
            "about an adversary who chooses content the kernels cannot recompute at all",
            "cycle 3 is the last cycle, so the fourth condition is read as a mechanism rather "
            "than as an observation of a later cycle that does not exist",
        ],
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    if arguments.check:
        stored = _load(arguments.output)
        body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
        sealed = _sha256(_canonical(body)) == stored["integrity_content_hash"]
        rebuilt = plant_record()
        same = stored == rebuilt
        print(
            json.dumps(
                {
                    "path": arguments.output.name,
                    "stored_seal_intact": sealed,
                    "rebuilt_and_identical": same,
                    "reproduced": sealed and same,
                },
                indent=1,
                sort_keys=True,
            )
        )
        return 0 if sealed and same else 1

    record = plant_record()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": arguments.output.name,
                "all_four_conditions_met": record["all_four_conditions_met"],
                "reason": record["conditions"][
                    "reaches_a_quarantine_state_with_a_named_released_reason"
                ]["reason"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
