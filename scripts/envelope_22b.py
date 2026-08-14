"""S22B-030. The W2 retrieval envelope, assembled from the sealed measurement records.

The drivers measure and this reads. Keeping the two apart is not tidiness: `scale_22b.py`'s
bytes are pinned by the pre-registration, so an assembler living inside it would make every
change to a *summary* a change to the pinned experiment. It also means this file can be read
by someone checking the arithmetic without re-reading fourteen hundred lines of driver.

Three things happen here that no measurement record can do for itself:

**Coverage is counted, not asserted.** 22A W4-F1 — count what a coverage word covers. "Seven
shapes, both datasets" is a claim with a number behind it, so the matrix is built from the
records that exist and compared against the pre-registered shape list. A missing cell is a
failure here, not a footnote in a report.

**The exit readings are derived once.** Three of the five exit criteria are decided by W2, and
each is read out of exactly one field of one record, named by path. A reading nobody can trace
to a field is a reading that can drift between the record and the prose about it.

**Limitations travel.** Every limitation the drivers sealed is collected rather than restated,
because a summary that paraphrases its sources is where caveats go to get softer.

    UV_CACHE_DIR=.cache/uv uv run python scripts/envelope_22b.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/envelope_22b.py --check

Read-only: it touches no database and writes exactly one evidence file.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"
OUTPUT = EVIDENCE / "sprint-22b-w2-envelope.json"

DATASETS = ("clustered", "uniform")

#: Every source this record is assembled from, by dataset. Named rather than globbed: a glob
#: would quietly assemble whatever happened to be on disk, and an envelope missing a dataset
#: would then look complete.
SOURCES = {
    "envelope": "sprint-22b-w2-envelope-{dataset}.json",
    "recall": "sprint-22b-w2-recall-{dataset}.json",
}

PRE_REGISTRATION = EVIDENCE / "sprint-22b-pre-registration.json"
HOST = EVIDENCE / "sprint-22b-reference-host-2.json"

#: W3-F4. This used to bind `sprint-22b-driver-rebind.json` by hash, and that was wrong in a way
#: only a later wave could reveal: the re-binding record is **rewritten every time a wave fixes
#: a driver**, so W3's two re-bindings made W2's sealed summary stop reproducing from its own
#: sources — a `--check` failure with nothing whatsoever wrong with the measurements.
#:
#: The binding was also redundant. What the re-binding asserts is not a file's bytes but an
#: executed proof that the current driver draws the same corpus, and `pre_registration_22b.py
#: --check` re-executes that proof on every run rather than trusting any stored hash. A summary
#: should bind what cannot move underneath it: the recipes, the publication, the host, and the
#: four measurement records it is assembled from. All four are still bound below.

#: The three exits W2 decides, each as a path into one measurement record. The other two are
#: W1's (governed ingest, met) and W3's (restore reproduces), and W4 reads all five together.
#:
#: **Which dataset each one reads, and why the two latency exits read both.** §2.2a froze the
#: dataset for the recall floor and only for the recall floor — the two latency numbers are
#: written in the allocation without a dataset, and W0 did not add one. That leaves a choice
#: this record refuses to make in its own favour: it takes the *worse* of the two datasets, so
#: an exit is met only when it is met everywhere it was measured. Reading the friendlier
#: dataset would be picking the reading after the numbers exist, which is the one move §2.2's
#: whole section exists to prevent.
EXIT_READINGS = {
    "recall_at_10": {
        "source": "recall",
        "dataset": "clustered",
        "field": "recall_at_k",
        "threshold": 0.95,
        "comparison": ">=",
        "why_this_dataset": "§2.2a froze it: the clustered geometry, and no other",
    },
    "warm_filtered_ann_p95_ms": {
        "source": "envelope",
        "dataset": "worst_of_both",
        "field": "measured.filtered_ann.p95_ms",
        "threshold": 300,
        "comparison": "<=",
        "why_this_dataset": (
            "no reading fixed a dataset for the latency exits, so the worse of the two decides "
            "and both are reported"
        ),
    },
    "bounded_graph_assisted_p95_ms": {
        "source": "envelope",
        "dataset": "worst_of_both",
        "field": "measured.bounded_graph_assisted.p95_ms",
        "threshold": 500,
        "comparison": "<=",
        "why_this_dataset": (
            "no reading fixed a dataset for the latency exits, so the worse of the two decides "
            "and both are reported"
        ),
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SystemExit(f"{path.name} does not exist: W2 cannot be assembled from a missing run")
    return json.loads(path.read_text(encoding="utf-8"))


def _drivers() -> Any:
    """The driver module, so the shape list is read from the recipes rather than restated."""
    path = REPO / "scripts/scale_22b.py"
    spec = importlib.util.spec_from_file_location("scale_22b_envelope", path)
    if spec is None or spec.loader is None:
        raise SystemExit("the 22B driver module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _at(record: dict[str, Any], field: str) -> Any:
    value: Any = record
    for part in field.split("."):
        value = value[part]
    return value


def _records() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        kind: {dataset: _load(EVIDENCE / name.format(dataset=dataset)) for dataset in DATASETS}
        for kind, name in SOURCES.items()
    }


def _coverage(records: dict[str, dict[str, dict[str, Any]]], shapes: tuple[str, ...]) -> dict:
    """The matrix, built from what exists and counted against what was pre-registered."""
    matrix: dict[str, dict[str, Any]] = {}
    probes = 0
    for dataset in DATASETS:
        measured = records["envelope"][dataset]["measured"]
        matrix[dataset] = {}
        for shape in shapes:
            cell = measured.get(shape)
            matrix[dataset][shape] = None if cell is None else int(cell["probes"])
            probes += 0 if cell is None else int(cell["probes"])
    missing = [
        f"{dataset}/{shape}"
        for dataset in DATASETS
        for shape in shapes
        if matrix[dataset][shape] is None
    ]
    return {
        "shapes_pre_registered": list(shapes),
        "shapes_pre_registered_count": len(shapes),
        "datasets_covered": list(DATASETS),
        "datasets_covered_count": len(DATASETS),
        "cells_required": len(shapes) * len(DATASETS),
        "cells_measured": len(shapes) * len(DATASETS) - len(missing),
        "missing_cells": missing,
        "measured_probes_total": probes,
        "probes_per_cell": records["envelope"][DATASETS[0]]["probes_per_shape"],
        "warmup_per_cell": records["envelope"][DATASETS[0]]["warmup_per_shape"],
        "matrix": matrix,
        "complete": not missing,
        "what_the_count_covers": (
            "one measured cell is one shape driven over one dataset at the pre-registered probe "
            "count, after a restart and its own warmup. 22A W4-F1: the number is here so the "
            "word 'every' has something behind it"
        ),
    }


def _table(records: dict[str, dict[str, dict[str, Any]]], shapes: tuple[str, ...]) -> dict:
    """Warm p50/p95/max and the cold first probe, per shape per dataset."""
    table: dict[str, dict[str, Any]] = {}
    for dataset in DATASETS:
        measured = records["envelope"][dataset]["measured"]
        table[dataset] = {}
        for shape in shapes:
            cell = measured.get(shape)
            if cell is None:
                continue
            cold = cell.get("cold_first_probe_ms")
            if cold is None and isinstance(cell.get("cold_first_probe"), dict):
                cold = cell["cold_first_probe"]["total_ms"]
            table[dataset][shape] = {
                "warm_p50_ms": cell["p50_ms"],
                "warm_p95_ms": cell["p95_ms"],
                "warm_max_ms": cell["max_ms"],
                "cold_first_probe_ms": cold,
                "probes": cell["probes"],
                "reads_an_exit": cell.get("reads_an_exit", False),
            }
    return table


def _readings(records: dict[str, dict[str, dict[str, Any]]]) -> dict:
    readings: dict[str, Any] = {}
    for name, spec in EXIT_READINGS.items():
        kind, field, comparison = str(spec["source"]), str(spec["field"]), spec["comparison"]
        threshold = spec["threshold"]
        per_dataset = {
            dataset: _at(records[kind][dataset], field)
            for dataset in (DATASETS if spec["dataset"] == "worst_of_both" else (spec["dataset"],))
        }
        # The worst reading decides: the minimum when more is better, the maximum when less is.
        decided_by = (
            min(per_dataset, key=lambda d: per_dataset[d])
            if comparison == ">="
            else max(per_dataset, key=lambda d: per_dataset[d])
        )
        value = per_dataset[decided_by]
        met = value >= threshold if comparison == ">=" else value <= threshold
        readings[name] = {
            "measured": value,
            "threshold": threshold,
            "comparison": comparison,
            "dataset": spec["dataset"],
            "decided_by_dataset": decided_by,
            "per_dataset": per_dataset,
            "why_this_dataset": spec["why_this_dataset"],
            "met": bool(met),
            "read_from": f"{SOURCES[kind].format(dataset=decided_by)}#{field}",
        }
    return readings


def _limitations(records: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Every limitation the drivers sealed, carried rather than paraphrased."""
    collected: list[dict[str, Any]] = []
    for dataset in DATASETS:
        envelope = records["envelope"][dataset]
        collected.append(
            {
                "where": f"{dataset}/restart",
                "limitation": envelope["restart"]["limitation"],
            }
        )
        collected.append(
            {
                "where": f"{dataset}/server_memory",
                "limitation": envelope["server_memory"]["reading"],
                "index_over_shared_buffers": envelope["server_memory"]["index_over_shared_buffers"],
            }
        )
        for shape, cell in envelope["measured"].items():
            if cell.get("limitation"):
                collected.append({"where": f"{dataset}/{shape}", "limitation": cell["limitation"]})
    return collected


def _assemble() -> dict[str, Any]:
    drivers = _drivers()
    shapes = tuple(sorted(drivers.QUERY_SHAPES))
    records = _records()

    recipes = {records["envelope"][dataset]["recipes_hash"] for dataset in DATASETS}
    recipes |= {records["recall"][dataset]["recipes_hash"] for dataset in DATASETS}
    if recipes != {drivers.recipes_hash()}:
        raise SystemExit(
            "the measurement records were not all produced under one set of recipes: "
            f"{sorted(recipes)} against {drivers.recipes_hash()}"
        )

    coverage = _coverage(records, shapes)
    readings = _readings(records)
    document = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W2",
        "items": ["S22B-030", "S22B-031", "S22B-032"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        # Top level, and not only inside `binds`, because that is where
        # `pre_registration_22b.py --check-chronology` looks: this record has to be checkable
        # as "published after the pre-registration it claims to follow" without the checker
        # knowing anything about W2's own layout.
        "pre_registration_sha256": _sha256(PRE_REGISTRATION.read_bytes()),
        "binds": {
            "recipes_hash": drivers.recipes_hash(),
            "host_id": _load(HOST)["host_id"],
            "host_integrity_content_hash": _load(HOST)["integrity_content_hash"],
            "sources": {
                kind: {
                    dataset: _sha256((EVIDENCE / name.format(dataset=dataset)).read_bytes())
                    for dataset in DATASETS
                }
                for kind, name in SOURCES.items()
            },
        },
        "coverage": coverage,
        # W2's row says "name every mode and dataset covered". The seven shapes are the
        # envelope's rows; the two released retrieval modes that are driven *inside* them are
        # named here rather than left for a reader to infer from a composition string.
        "supporting_modes_driven": {
            name: {
                "mode": entry["mode"],
                "driven_by": entry["used_by"],
                "an_envelope_row": False,
            }
            for name, entry in drivers.SUPPORTING_MODES.items()
        },
        "envelope": _table(records, shapes),
        "recall": {
            dataset: {
                "recall_at_k": records["recall"][dataset]["recall_at_k"],
                "k": records["recall"][dataset]["k"],
                "probes": records["recall"][dataset]["probes"],
                "ground_truth": records["recall"][dataset]["ground_truth"],
                "reads_the_recall_exit": records["recall"][dataset]["reads_the_recall_exit"],
            }
            for dataset in DATASETS
        },
        "exit_readings": readings,
        "exits_decided_by_w2": len(readings),
        "exits_met": sum(1 for reading in readings.values() if reading["met"]),
        "limitations": _limitations(records),
        "diagnostics_read_no_exit": True,
        "one_host": (
            "every number here is a property of the declared reference host and of its "
            "PostgreSQL memory settings, which 22B seals and does not tune (§1.4, §2.3)"
        ),
    }
    document["integrity_content_hash"] = _sha256(_canonical(document))
    return document


def _write() -> None:
    document = _assemble()
    OUTPUT.write_text(
        json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": OUTPUT.name,
                "cells_measured": document["coverage"]["cells_measured"],
                "cells_required": document["coverage"]["cells_required"],
                "exits_met": document["exits_met"],
                "exits_decided_by_w2": document["exits_decided_by_w2"],
                "integrity_content_hash": document["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    """Recompute the whole record from its sources and refuse any difference.

    22A W4-F2: a claim that nothing changed has to be able to notice that something did. So
    this rebuilds the document rather than re-hashing the stored one, and compares every field
    except the timestamp — which is the one field a rebuild is *expected* to move.
    """
    stored = _load(OUTPUT)
    rebuilt = _assemble()
    stored_body = {
        k: v for k, v in stored.items() if k not in {"recorded_at", "integrity_content_hash"}
    }
    rebuilt_body = {
        k: v for k, v in rebuilt.items() if k not in {"recorded_at", "integrity_content_hash"}
    }
    if stored_body != rebuilt_body:
        differing = sorted(
            key
            for key in set(stored_body) | set(rebuilt_body)
            if stored_body.get(key) != rebuilt_body.get(key)
        )
        raise SystemExit(f"the W2 envelope no longer reproduces from its sources: {differing}")
    if not stored["coverage"]["complete"]:
        raise SystemExit(f"coverage is incomplete: {stored['coverage']['missing_cells']}")
    print(
        json.dumps(
            {
                "reproduces_from_sources": True,
                "cells_measured": stored["coverage"]["cells_measured"],
                "cells_required": stored["coverage"]["cells_required"],
                "exit_readings": {
                    name: reading["met"] for name, reading in stored["exit_readings"].items()
                },
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
