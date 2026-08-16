"""S22E-301: the re-measurement licence, resolved against the change that actually landed.

§3's W3 row makes the re-measurement conditional — "**if** the landed repair touches a Gate M
condition" — and the pre-registration states the licence rule W0 froze. This driver resolves
that condition instead of assuming its answer, and seals the resolution either way.

**Why a record exists for a re-measurement that does not happen.** A wave that simply did not
re-run an instrument leaves no evidence distinguishing "not licensed" from "not attempted", and
§3.2's rule about economised cells applies exactly here: a measurement skipped silently reads,
later, as a measurement that was never owed. The three inputs are read from their own sealed
records and their seals recomputed, so the conclusion is derived rather than asserted.

**What this record does not do.** It does not read a Gate M condition. W4 does that, against the
freshest evidence that honestly exists; this record only fixes what "freshest" is allowed to mean
for conditions 6 and 7.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/remeasurement_22e.py
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/remeasurement_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22e-w3-remeasurement.json"
RECORDED_AT = "2026-08-16T00:00:00Z"

ENTRY_ID = "L7"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def sealed(name: str) -> dict[str, Any]:
    """Read a sealed evidence record and refuse it if it does not recompute its own seal."""
    stored = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))
    body = {key: value for key, value in stored.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != stored["integrity_content_hash"]:
        raise ValueError(f"{name} does not recompute its own seal")
    return stored


def build() -> dict[str, Any]:
    ledger = sealed("sprint-22e-weakness-ledger-2.json")
    decisions = sealed("sprint-22e-decisions.json")
    registration = sealed("sprint-22e-pre-registration.json")
    landed = sealed("sprint-22e-w3-approved-change.json")

    entry = next(item for item in ledger["added_entries"] if item["entry_id"] == ENTRY_ID)
    touches = entry["touches_a_gate_m_condition"]
    premise = decisions["arithmetic_premise"]
    licence = registration["re_measurement_licence"]

    # The rule's antecedent, resolved from the records rather than from the wave's memory of
    # them. `touches_a_gate_m_condition` is `null` on L7 and the decision record's premise says
    # which entries do touch 6 and 7 — neither of them is the one that landed.
    licensed = touches is not None
    return {
        "items": ["S22E-301"],
        "sprint": "22E",
        "wave": "W3",
        "schema_version": 1,
        "the_change_that_landed": {
            "entry_id": ENTRY_ID,
            "finding": entry["finding"],
            "selected_by": decisions["decided_by"],
            "selection_record_hash": decisions["integrity_content_hash"],
            "approved_change_record_hash": landed["integrity_content_hash"],
            "touches_a_gate_m_condition": touches,
        },
        "licence": {
            "rule": licence["rule"],
            "instrument": licence["instrument"],
            "what_cannot_change_a_verdict": licence["what_cannot_change_a_verdict"],
            "pre_registration_hash": registration["integrity_content_hash"],
        },
        "resolution": {
            "re_measurement_licensed": licensed,
            "instrument_re_run": False,
            "because": (
                "the licence is conditional on the landed repair touching a Gate M condition; "
                "the ledger records L7 as touching none, and the gate owner's own arithmetic "
                "premise names L1 for condition 6 and L2 for condition 7 — disjoint sets, "
                "neither of which is what landed"
            ),
            "entries_touching_condition_6": premise["entries_touching_condition_6"],
            "entries_touching_condition_7": premise["entries_touching_condition_7"],
            "the_sets_are_disjoint": premise["the_sets_are_disjoint"],
            "conditions_still_reading_a_predecessor_seal": [6, 7],
            "what_they_read": "22D's sealed exit-criteria record, unchanged by this sprint",
        },
        "what_this_costs_the_sprint": {
            "gate_m_cannot_fully_close_in_22e": premise["gate_m_cannot_fully_close_in_22e"],
            "predicted_before_any_candidate_existed": True,
            "where": (
                "the gate owner's decision record states it as the arithmetic premise of the "
                "selection, and the backlog's §4 states it as a risk the evidence cannot retire"
            ),
            "the_selection_was_made_knowing_this": decisions["decision_two"]["why"][0],
        },
        "why_a_record_exists_for_a_measurement_that_did_not_run": (
            "a re-measurement skipped in silence is indistinguishable later from one that was "
            "never owed; §3.2's rule about economised cells is that the reduction is declared"
        ),
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Every input is re-read and its seal recomputed; the conclusion is re-derived from them."""
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    rebuilt = build()
    rebuilt.pop("integrity_content_hash", None)
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "rebuilds_byte_identical": canonical(rebuilt) == canonical(body),
        "every_source_record_still_seals": True,
        "conclusion_is_still_not_licensed": rebuilt["resolution"]["re_measurement_licensed"]
        is False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if all(verdict.values()) else 1

    record = build()
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "re_measurement_licensed": record["resolution"]["re_measurement_licensed"],
                "conditions_still_reading_a_predecessor_seal": record["resolution"][
                    "conditions_still_reading_a_predecessor_seal"
                ],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
