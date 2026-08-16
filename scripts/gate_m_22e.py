"""S22E-400: Gate M read once, against the readings W0 froze before any candidate existed.

**Nothing here decides what a condition means.** The ten conditions, the record each one reads,
the path inside it, and the reading that turns a value into a verdict were all published in W0's
pre-registration and sealed before a single measurement existed. This driver imports that binding
table rather than retyping it (22B W1-F2), resolves each path with the pre-registration's own
`resolve_binding`, and applies the verdict rule declared below beside the reading it implements.

**An unresolvable binding raises.** §2.2(d)'s rule, and the reason W0 ran `--verify-bindings`
against every predecessor record: a gate that renders a missing number as `false` is a gate that
reports a bookkeeping error as a failed condition. Two bindings were wrong when first drafted and
W0 is where that cost minutes instead of a wave.

**Conditions 6 and 7 are expected to fail, and that expectation is itself sealed.** They read
22D's negative, no re-measurement is licensed for them (S22E-301), and rereading a sealed number
is precisely what the licence rule forbids. So Gate M cannot close in 22E, the decision record
said so as the arithmetic premise of its own selection, and this driver measures it rather than
discovering it.

    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/gate_m_22e.py
    UV_CACHE_DIR=.cache/uv uv run --exact python scripts/gate_m_22e.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
sys.path.insert(0, str(REPO / "scripts"))

OUTPUT = EVIDENCE / "sprint-22e-gate-m.json"
RECORDED_AT = "2026-08-16T00:00:00Z"

#: The five gate families condition 9 names, and the CI lane each is satisfied by. Declared here
#: so that "the gates pass" is an enumeration a test can check rather than a word (22A W4-F1).
CONDITION_9_FAMILIES = {
    "security": "security",
    "provider": "provider-offline",
    "migration": "migration",
    "distribution": "build",
    "repository_language": "quality",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


#: How each condition's resolved value becomes a verdict. One rule per condition, written next to
#: the reading it implements, so that a reader can check the rule against the sentence rather
#: than against this driver's behaviour.
VERDICTS: dict[int, Callable[[Any], bool]] = {
    # D7's sealed close: Gate L2's own count of conditions met, all twenty-nine.
    1: lambda value: value == 29,
    # 22A's four exits, verdict word for word.
    2: lambda value: value == "pass",
    # 22B's five exits, its own conjunction.
    3: lambda value: value is True,
    # 22C's replay exit specifically. The record keys each criterion by its sentence; the value
    # is that criterion's own object, and `met` is the field it publishes.
    4: lambda value: bool(value.get("met")) if isinstance(value, dict) else value is True,
    # 22D's grounded holdout answers: four verified on arm B.
    5: lambda value: value == 4,
    # 22D exit (b), local verified success against the 70 % floor. Sealed `False`.
    6: lambda value: value is True,
    # 22D exit (c), calls or equivalent cost against the 25 % target. Sealed `False`.
    7: lambda value: value is True,
    # This sprint's one approved change, green at its exact merged head.
    8: lambda value: value == "success",
    # The CI lanes at the release head: every named family must have a passing lane.
    9: lambda value: (
        isinstance(value, dict)
        and all(value.get(lane) == "success" for lane in CONDITION_9_FAMILIES.values())
    ),
    # The programme tag peeling to the verified protected commit. `null` means it was not
    # created, which on a typed negative is the correct and expected state.
    10: lambda value: isinstance(value, str) and len(value) == 40,
}


def read_gate() -> dict[str, Any]:
    from pre_registration_22e import GATE_M_CONDITIONS, _gate_m_bindings, resolve_binding

    rows = []
    for binding in _gate_m_bindings():
        number = binding["condition"]
        value = resolve_binding(binding["reads_record"], binding["reads_path"])
        met = VERDICTS[number](value)
        row = {
            "condition": number,
            "sentence": GATE_M_CONDITIONS[number - 1],
            "reads": f"{binding['reads_record']}#{binding['reads_path']}",
            "value": value if not isinstance(value, dict) else sorted(value),
            "met": met,
            "reading": binding["reading"],
            "source_kind": binding["source_kind"],
        }
        if "expected_value" in binding:
            row["w0_expected_value"] = binding["expected_value"]
            row["value_is_what_w0_expected"] = value == binding["expected_value"]
        if "expected_at_w0" in binding:
            row["w0_expected_verdict"] = binding["expected_at_w0"]
        if "re_measurement_licensed_by" in binding:
            row["re_measurement_licensed_by"] = binding["re_measurement_licensed_by"]
        rows.append(row)
    return {"conditions": rows}


def build() -> dict[str, Any]:
    gate = read_gate()
    rows = gate["conditions"]
    met = [row["condition"] for row in rows if row["met"]]
    failed = [row["condition"] for row in rows if not row["met"]]
    licence = json.loads(
        (EVIDENCE / "sprint-22e-w3-remeasurement.json").read_text(encoding="utf-8")
    )

    return {
        "items": ["S22E-400"],
        "sprint": "22E",
        "wave": "W4",
        "schema_version": 1,
        "gate": "M",
        "read_once": True,
        "conditions": rows,
        "counts": {
            "total": len(rows),
            "met": len(met),
            "failed": len(failed),
        },
        "conditions_met": met,
        "conditions_failed": failed,
        "all_conditions_pass": not failed,
        "every_reading_was_frozen_before_any_measurement": True,
        "why_the_failures_are_not_surprises": {
            "conditions": [6, 7],
            "they_read": "22D's sealed exit record, unchanged by this sprint",
            "re_measurement_licensed": licence["resolution"]["re_measurement_licensed"],
            "because": licence["resolution"]["because"],
            "predicted_in": (
                "the gate owner's decision record, as the arithmetic premise of the selection"
            ),
        },
        "what_could_have_changed_them": (
            "a released repair affecting the measurement, landed through the governed path, "
            "followed by a re-measurement on the frozen instrument — not a rereading"
        ),
        "recorded_at": RECORDED_AT,
    }


def check_record(record: dict[str, Any]) -> dict[str, Any]:
    """Every condition is resolved again from its own sealed record and re-judged."""
    body = {key: value for key, value in record.items() if key != "integrity_content_hash"}
    rebuilt = build()
    drift = [
        row["condition"]
        for row, again in zip(record["conditions"], rebuilt["conditions"], strict=True)
        if row["met"] != again["met"] or row["value"] != again["value"]
    ]
    return {
        "seal_recomputes": _sha256(canonical(body)) == record["integrity_content_hash"],
        "every_condition_resolves_again": True,
        "conditions_that_moved": drift,
        "counts_unchanged": record["counts"] == rebuilt["counts"],
        "recorded_not_recomputed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()

    if arguments.check:
        verdict = check_record(json.loads(OUTPUT.read_text(encoding="utf-8")))
        print(json.dumps(verdict, indent=1, sort_keys=True))
        return 0 if verdict["seal_recomputes"] and not verdict["conditions_that_moved"] else 1

    record = build()
    record["integrity_content_hash"] = _sha256(canonical(record))
    OUTPUT.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "counts": record["counts"],
                "conditions_failed": record["conditions_failed"],
                "all_conditions_pass": record["all_conditions_pass"],
                "integrity_content_hash": record["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
