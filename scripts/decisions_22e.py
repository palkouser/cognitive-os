"""S22E-201. The two W3 gate-owner decisions, sealed with the alternatives they rejected.

W0's rule, applied to the decisions W1 forced: a reading that does not say what it chose
against is a reading nobody can audit. Both decisions were put to the gate owner with the
priced ledger, the W2-F1 correction and the recommendation in front of them, and taken on
2026-08-16.

**Decision one — §2.2(b) is walked by repairing it.** W1-F7 made the frozen chain unwalkable
as written: the provider-assisted mark cannot survive to an approved revision by any caller's
route. The ruling is that the one approved change **is the L7 repair**, and the traversal
that installs it documents its own exception — the repaired behaviour cannot be required of
the traversal that installs the repair, which is dry run 1's "both halves are true" pattern.
No frozen reading is amended. Rejected: reading "provider-assisted candidate" as satisfied in
substance by the demonstrated fact while the released mark misreports (viable, but it leaves
the loop's own defect standing and reads a frozen sentence loosely mid-sprint); and declaring
exit two unwalkable (a negative nothing forces).

**Decision two — the approved change is L7.** The arithmetic premise is recomputed by
`--check` from the sealed ledger revision rather than asserted: Gate M condition 6 is touched
only by L1 and condition 7 only by L2, the sets are disjoint, and §2.3 allows exactly one
approved change — so **Gate M cannot fully close in 22E under any selection**, and the typed
negative on exit four is certain. Given that, the selection maximises what the negative is
worth: L7 repairs the loop itself, makes §2.2(b) walkable for every successor, and is the
lowest-risk entry on the board with an executed reproduction sealed in the ledger revision.
The successor closes conditions 6 and 7 by landing L1 and L2 through the walkable chain — the
D-series precedent, where D5's and D6's negatives made the instrument sound and Gate L2
closed in D7. Rejected: **L1** (the only selection that could move a Gate M condition this
sprint, to 9 of 10 at best; its supposed mypy price was W2-F1's false rejection and does not
exist, but its ceiling is not a forecast — at least 4 of the 10 recoverable tasks must
actually verify — and it leaves the loop defect standing); **L2** (same shape, noisier: the
non-inferiority margin is 3 points and 22D W3-F3 measured the baseline itself moving 12 of
96); **L6** and **L4** (neither touches a condition nor the chain's walkability; L4 is
high-risk with zero benefit on the plan's named reading).

    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22e.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/decisions_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

LEDGER_W0 = EVIDENCE / "sprint-22e-weakness-ledger.json"
LEDGER_REVISION = EVIDENCE / "sprint-22e-weakness-ledger-2.json"
OUTPUT = EVIDENCE / "sprint-22e-decisions.json"
DECIDED_AT = "2026-08-16T15:00:00Z"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _arithmetic_premise() -> dict[str, Any]:
    """Recomputed, never asserted: one approved change cannot flip both failed conditions."""
    ledger = json.loads(LEDGER_W0.read_text(encoding="utf-8"))
    revision = json.loads(LEDGER_REVISION.read_text(encoding="utf-8"))
    entries = list(ledger["entries"]) + list(revision["added_entries"])
    touching: dict[int, list[str]] = {6: [], 7: []}
    for entry in entries:
        condition = entry.get("touches_a_gate_m_condition")
        if condition in touching:
            touching[condition].append(entry["entry_id"])
    return {
        "entries_touching_condition_6": sorted(touching[6]),
        "entries_touching_condition_7": sorted(touching[7]),
        "the_sets_are_disjoint": not set(touching[6]) & set(touching[7]),
        "approved_changes_allowed": 1,
        "gate_m_cannot_fully_close_in_22e": bool(touching[6])
        and bool(touching[7])
        and not set(touching[6]) & set(touching[7]),
        "therefore": (
            "conditions 6 and 7 need two different repairs, one may land, and the typed "
            "negative on exit four is certain under every selection — the question the gate "
            "owner decided is which negative is worth the most"
        ),
    }


def _ledger_binding(path: Path) -> dict[str, str]:
    stored = json.loads(path.read_text(encoding="utf-8"))
    return {
        "file": path.name,
        "file_sha256": _sha256(path.read_bytes()),
        "integrity_content_hash": stored["integrity_content_hash"],
    }


def _record() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": 1,
        "items": ["S22E-201"],
        "sprint": "22E",
        "wave": "W2",
        "decided_by": "the Sprint 22 gate owner",
        "decided_at": DECIDED_AT,
        "put_to_the_gate_owner_with": [
            "the sealed W0 ledger and its W2 revision (bound below)",
            "the W2-F1 correction — L1's supposed mypy price was a false rejection",
            "the recomputed arithmetic premise (below)",
            "a written recommendation, which the gate owner accepted",
        ],
        "ledger_bindings": {
            "w0": _ledger_binding(LEDGER_W0),
            "revision_2": _ledger_binding(LEDGER_REVISION),
        },
        "arithmetic_premise": _arithmetic_premise(),
        "decision_one": {
            "question": (
                "W1-F7 makes §2.2(b)'s chain unwalkable as written: the provider-assisted "
                "mark cannot survive to an approved revision by any caller's route"
            ),
            "ruling": (
                "the chain is walked by repairing it: the one approved change is the L7 "
                "repair, and the installing traversal documents its own exception — the "
                "repaired behaviour cannot be required of the traversal that installs the "
                "repair"
            ),
            "no_frozen_reading_is_amended": True,
            "rejected_alternatives": [
                {
                    "alternative": (
                        "rule that 'provider-assisted candidate' is satisfied in substance "
                        "(live draft, host verification, receipts) while the released mark "
                        "misreports, documented per dry run 1's precedent"
                    ),
                    "why_rejected": (
                        "viable and honest, but it leaves the loop's own released defect "
                        "standing and reads a frozen sentence loosely mid-sprint when a "
                        "repair through the loop itself is available"
                    ),
                },
                {
                    "alternative": "declare exit two unwalkable as written — a typed negative",
                    "why_rejected": "a negative nothing forces once the repair path exists",
                },
            ],
        },
        "decision_two": {
            "question": "which single repair is the sprint's one approved change",
            "selection": "L7",
            "selection_finding": "22E W1-F7",
            "why": [
                "the arithmetic premise: no selection fully closes Gate M this sprint, so "
                "the selection maximises what the certain typed negative is worth",
                "L7 repairs the loop itself and makes §2.2(b) walkable for every successor",
                "lowest risk on the board: one released function, an executed reproduction "
                "sealed in the ledger revision, regression evidence cheap and deterministic",
                "the D-series precedent: D5's and D6's negatives made the instrument sound "
                "and Gate L2 closed in D7 — the successor lands L1 and L2 through the "
                "walkable chain and closes conditions 6 and 7",
            ],
            "rejected_alternatives": [
                {
                    "entry": "L1",
                    "why_rejected": (
                        "the only selection that could move a Gate M condition this sprint "
                        "(condition 6, to 9 of 10 at best); its supposed mypy price was "
                        "W2-F1's false rejection and does not exist, but the +10 ceiling is "
                        "not a forecast — at least 4 of the 10 recoverable tasks must "
                        "actually verify — and it leaves the loop defect standing"
                    ),
                },
                {
                    "entry": "L2",
                    "why_rejected": (
                        "same shape as L1 and noisier: the non-inferiority margin is 3 "
                        "points and 22D W3-F3 measured the baseline itself moving 12 of 96"
                    ),
                },
                {
                    "entry": "L6 / L4",
                    "why_rejected": (
                        "neither touches a Gate M condition nor the chain's walkability; "
                        "L4 is high-risk with zero benefit on the plan's named reading"
                    ),
                },
            ],
        },
        "what_this_decides_for_the_waves": [
            "W2's remaining dry runs need no walkability exception — they stop short of merge",
            "W3 mines L7, carries the repair through the full chain, and its record states "
            "the installing traversal's exception in its own body",
            "W4 reads Gate M knowing conditions 6 and 7 fail as sealed, and the release is "
            "the designed typed negative under sprint-22e-evidence-baseline if they do",
        ],
        "recorded_at": DECIDED_AT,
    }
    record["integrity_content_hash"] = _sha256(
        canonical({key: value for key, value in record.items() if key != "integrity_content_hash"})
    )
    return record


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    mismatches: list[str] = []
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    if _sha256(canonical(body)) != record.get("integrity_content_hash"):
        mismatches.append("integrity_content_hash")
    if record["arithmetic_premise"] != _arithmetic_premise():
        mismatches.append("arithmetic_premise")
    for name, path in (("w0", LEDGER_W0), ("revision_2", LEDGER_REVISION)):
        if record["ledger_bindings"][name] != _ledger_binding(path):
            mismatches.append(f"ledger_bindings.{name}")
    if record["decision_two"]["selection"] != "L7":
        mismatches.append("decision_two.selection")
    return {
        "reproduced": not mismatches,
        "mismatches": mismatches,
        "recomputed": [
            "integrity_content_hash",
            "arithmetic_premise (from both sealed ledger records)",
            "ledger_bindings (bytes and seals of both ledgers)",
        ],
        "recorded_not_recomputed": [
            "the rulings themselves — a decision is an observation about the gate owner"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        stored = json.loads(OUTPUT.read_text(encoding="utf-8"))
        verdict = check_record(stored)
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["reproduced"] else 1

    record = _record()
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "decision_one": "the chain is walked by repairing it",
                "decision_two_selection": record["decision_two"]["selection"],
                "gate_m_cannot_fully_close_in_22e": record["arithmetic_premise"][
                    "gate_m_cannot_fully_close_in_22e"
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
