"""S22B-040. All five exit criteria, read once, against the sealed measurements.

Four waves each decided part of the sprint. This record is the only place where all five
numbers are read together, and it is deliberately not a summary written by hand: every value is
traced to one field of one sealed record, the thresholds come from the frozen contracts rather
than from this file, and `--check` rebuilds the whole document from its sources and refuses any
difference.

**It also carries the one comparison W4 exists to make.** §3's W4 row says a restore that
changes the envelope is a finding, so the three exits W2 decided are re-read against the
*restored* store's own re-measurement and reported side by side. A restored number that missed
its threshold would make the restore the finding, not the envelope.

Helpers are imported from `envelope_22b.py` rather than copied: there is one implementation of
"trace a field path into a sealed record" in this sprint, and a second one could disagree.

    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22b.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/exit_criteria_22b.py --check

Read-only: it touches no database and writes exactly one evidence file.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22b-exit-criteria.json"

CONTRACTS = EVIDENCE / "sprint-22b-contracts.json"
PRE_REGISTRATION = EVIDENCE / "sprint-22b-pre-registration.json"

#: Where each exit criterion's measured value lives, as one record and one field path. The
#: thresholds are **not** here — they are read from the frozen contracts, so this file cannot
#: soften one by restating it.
SOURCES: dict[str, dict[str, str]] = {
    "governed_ingest_items_per_second": {
        "wave": "W1",
        "record": "sprint-22b-w1-governed-ingest.json",
        "field": "items_per_second",
    },
    "recall_at_10": {
        "wave": "W2",
        "record": "sprint-22b-w2-envelope.json",
        "field": "exit_readings.recall_at_10.measured",
    },
    "warm_filtered_ann_p95_ms": {
        "wave": "W2",
        "record": "sprint-22b-w2-envelope.json",
        "field": "exit_readings.warm_filtered_ann_p95_ms.measured",
    },
    "bounded_graph_assisted_p95_ms": {
        "wave": "W2",
        "record": "sprint-22b-w2-envelope.json",
        "field": "exit_readings.bounded_graph_assisted_p95_ms.measured",
    },
    "restore_reproduces": {
        "wave": "W3",
        "record": "sprint-22b-w3-restore-checklist.json",
        "field": "all_four_met",
    },
}

#: The three exits W4 re-reads on the restored store, and where the restored value comes from.
#: The datasets match what `envelope_22b.py` decided: recall on clustered, the two latency exits
#: on the worse of the two datasets.
RESTORED: dict[str, dict[str, Any]] = {
    "recall_at_10": {
        "records": ["sprint-22b-w4-restored-recall-clustered.json"],
        "field": "recall_at_k",
        "worse": "min",
    },
    "warm_filtered_ann_p95_ms": {
        "records": [
            "sprint-22b-w4-restored-envelope-clustered.json",
            "sprint-22b-w4-restored-envelope-uniform.json",
        ],
        "field": "measured.filtered_ann.p95_ms",
        "worse": "max",
    },
    "bounded_graph_assisted_p95_ms": {
        "records": [
            "sprint-22b-w4-restored-envelope-clustered.json",
            "sprint-22b-w4-restored-envelope-uniform.json",
        ],
        "field": "measured.bounded_graph_assisted.p95_ms",
        "worse": "max",
    },
}


def _envelope_module() -> Any:
    """`envelope_22b.py`, for the one implementation of loading, sealing and field tracing."""
    path = REPO / "scripts/envelope_22b.py"
    spec = importlib.util.spec_from_file_location("envelope_22b_helpers", path)
    if spec is None or spec.loader is None:
        raise SystemExit("the W2 envelope assembler could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _met(value: Any, threshold: Any, comparison: str) -> bool:
    if comparison == ">=":
        return bool(value >= threshold)
    if comparison == "<=":
        return bool(value <= threshold)
    if comparison == "all of":
        return value is True
    raise SystemExit(f"unknown comparison {comparison!r}")


def _assemble() -> dict[str, Any]:
    helpers = _envelope_module()
    load, sha256, canonical, at = helpers._load, helpers._sha256, helpers._canonical, helpers._at

    contracts = load(CONTRACTS)
    if load(PRE_REGISTRATION)["contracts_sha256"] != sha256(CONTRACTS.read_bytes()):
        raise SystemExit("the publication no longer binds the contracts this record reads")
    criteria = contracts["contracts"]["exit_criteria"]["criteria"]
    if set(criteria) != set(SOURCES):
        raise SystemExit(
            f"the frozen criteria and the traced sources disagree: {sorted(criteria)} against "
            f"{sorted(SOURCES)}"
        )

    readings: dict[str, Any] = {}
    for name, source in SOURCES.items():
        record = load(EVIDENCE / source["record"])
        value = at(record, source["field"])
        threshold = criteria[name]["threshold"]
        comparison = criteria[name]["comparison"]
        readings[name] = {
            "wave": source["wave"],
            "threshold": threshold,
            "comparison": comparison,
            "measured": value,
            "met": _met(value, threshold, comparison),
            "read_from": f"{source['record']}#{source['field']}",
        }

    restored: dict[str, Any] = {}
    for name, spec in RESTORED.items():
        values = {}
        for filename in spec["records"]:
            record = load(EVIDENCE / filename)
            values[record.get("dataset", filename)] = at(record, str(spec["field"]))
        chosen = min(values.values()) if spec["worse"] == "min" else max(values.values())
        source_value = readings[name]["measured"]
        threshold = readings[name]["threshold"]
        comparison = readings[name]["comparison"]
        restored[name] = {
            "restored_per_dataset": values,
            "restored": chosen,
            "source": source_value,
            # Carried here as well as in `criteria`, so a reader comparing a restored number to
            # its floor never has to hold two parts of the document in their head at once.
            "threshold": threshold,
            "comparison": comparison,
            "delta": round(chosen - source_value, 4),
            "delta_percent": (
                round((chosen - source_value) / source_value * 100, 2) if source_value else None
            ),
            "restored_still_meets_the_threshold": _met(chosen, threshold, comparison),
            "measured_on": sorted(
                {load(EVIDENCE / name_).get("database", "?") for name_ in spec["records"]}
            ),
        }

    document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W4",
        "items": ["S22B-040", "S22B-041"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": sha256(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": sha256(CONTRACTS.read_bytes()),
        "thresholds_moved_by_22b": 0,
        "criteria": readings,
        "criteria_total": len(readings),
        "criteria_met": sum(1 for reading in readings.values() if reading["met"]),
        "all_met": all(reading["met"] for reading in readings.values()),
        "post_restore": restored,
        "post_restore_all_still_met": all(
            entry["restored_still_meets_the_threshold"] for entry in restored.values()
        ),
        # A restored number that moved says nothing about *what* moved it: W3 mutated the store
        # between the two measurements, and the attribution record is where that is separated.
        "attributed_by": "sprint-22b-w4-attribution.json",
        "what_a_restored_miss_would_mean": (
            "§3's W4 row: a restore that changes the envelope is a finding. The restored numbers "
            "are reported beside the source ones whatever they say, and a restored value that "
            "missed its threshold would be reported as a finding about the restore rather than "
            "quietly averaged with the number that met it"
        ),
        "outcome": (
            "pass" if all(reading["met"] for reading in readings.values()) else "typed negative"
        ),
        "sources_sha256": {
            name: sha256((EVIDENCE / source["record"]).read_bytes())
            for name, source in SOURCES.items()
        },
        "restored_sources_sha256": {
            filename: sha256((EVIDENCE / filename).read_bytes())
            for spec in RESTORED.values()
            for filename in spec["records"]
        },
    }
    document["integrity_content_hash"] = sha256(canonical(document))
    return document


def _write() -> None:
    document = _assemble()
    OUTPUT.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "criteria_met": document["criteria_met"],
                "criteria_total": document["criteria_total"],
                "post_restore_all_still_met": document["post_restore_all_still_met"],
                "outcome": document["outcome"],
                "integrity_content_hash": document["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    """Recompute from the sealed sources and refuse any difference (22A W4-F2)."""
    helpers = _envelope_module()
    stored = helpers._load(OUTPUT)
    rebuilt = _assemble()
    skip = {"recorded_at", "integrity_content_hash"}
    stored_body = {key: value for key, value in stored.items() if key not in skip}
    rebuilt_body = {key: value for key, value in rebuilt.items() if key not in skip}
    if stored_body != rebuilt_body:
        differing = sorted(
            key
            for key in set(stored_body) | set(rebuilt_body)
            if stored_body.get(key) != rebuilt_body.get(key)
        )
        raise SystemExit(f"the exit-criteria record no longer reproduces: {differing}")
    print(
        json.dumps(
            {
                "reproduces_from_sources": True,
                "criteria_met": stored["criteria_met"],
                "criteria_total": stored["criteria_total"],
                "all_met": stored["all_met"],
                "post_restore_all_still_met": stored["post_restore_all_still_met"],
                "integrity_content_hash": stored["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="recompute the record from sources")
    arguments = parser.parse_args()
    if arguments.check:
        _check()
    else:
        _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
