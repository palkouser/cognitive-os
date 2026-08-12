"""S22B-010 through S22B-016. Revision 1, frozen before a single corpus row exists.

The D-series pre-registered learners. Sprint 22A pre-registered a vocabulary and a refusal.
22B pre-registers **readings** — because a measurement sprint fails in a way neither of those
could: not by fitting the wrong thing, but by quietly redefining a hard number as a property
of a friendlier setup. Every field below exists so that a later wave which wants to meet an
exit has to meet it, rather than re-read it.

Nothing here is a threshold. The five exit numbers are the execution sprint allocation's,
verbatim, and this publication moves none of them; there is no gate-owner amendment path in
22B's plan at all, so `amendments_made_by_22b` is structurally zero rather than merely unused.

The recipes are **imported from the module that implements them** and hashed from it, never
retyped, so a driver that drifts drifts this record too and `--check` catches it. The
reference host is bound by its own invariants hash, so a number measured on another machine
cannot borrow this authority.

    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22b.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22b.py --check
    UV_CACHE_DIR=.cache/uv uv run python scripts/pre_registration_22b.py --check-chronology \\
        --later docs/sprints/sprint-22/evidence/sprint-22b-<later>.json

Publishing this closes the window in which a dataset, a probe protocol, a filter selectivity
or a graph configuration could be chosen. Everything after it is measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

EVIDENCE = REPO / "docs/sprints/sprint-22/evidence"

OUTPUTS = {
    "contracts": EVIDENCE / "sprint-22b-contracts.json",
    "pre_registration": EVIDENCE / "sprint-22b-pre-registration.json",
}

#: W1-F2. Revision 1 pinned `scale_22b.py`'s **bytes**, which made every defect fix in a
#: driver a contract violation — and W1's first act was a defect fix the sprint could not
#: proceed without. The thing that must not move is the *corpus and the readings*, not the
#: implementation that produces them.
#:
#: The pin is not loosened and the pre-registration is never edited. Instead a driver change
#: must be **re-bound** through this record, which re-derives the pinned implementation from
#: git history and *executes* both implementations to prove they draw the same rows. A change
#: that alters a drawn row, or the recipes hash, or the shape enumeration, cannot be re-bound
#: at all — it is a finding, and the sprint stops on it.
REBIND = EVIDENCE / "sprint-22b-driver-rebind.json"

#: How much of the corpus the identity proof draws from each implementation, per dataset. The
#: draw order is a single RNG stream, so a divergence anywhere shows up at the first row after
#: it; the offset window catches a change that only affects addressing.
REBIND_SAMPLE_ROWS = 1_500
REBIND_OFFSET = 1_400
REBIND_OFFSET_ROWS = 100

#: The W0 authority records this publication rests on. Each establishes authority or proves a
#: driver runs; none decides an exit criterion.
W0_CHILDREN = (
    "sprint-22b-baseline.json",
    "sprint-22b-reference-host.json",
    "sprint-22b-w0-slice.json",
)

DRIVERS = REPO / "scripts/scale_22b.py"

MIGRATION_HEAD = "0015"

#: The five exit numbers, carried verbatim from the execution sprint allocation. 22B changes
#: none of them and may not: a sprint that moves its own exit has measured nothing.
EXIT_CRITERIA = {
    "recall_at_10": {
        "threshold": 0.95,
        "comparison": ">=",
        "dataset": "clustered",
        "at_items": 1_000_000,
    },
    "warm_filtered_ann_p95_ms": {"threshold": 300, "comparison": "<=", "at_items": 1_000_000},
    "bounded_graph_assisted_p95_ms": {
        "threshold": 500,
        "comparison": "<=",
        "at_items": 1_000_000,
    },
    "governed_ingest_items_per_second": {
        "threshold": 100,
        "comparison": ">=",
        "path": "governed write path on the declared reference host",
    },
    "restore_reproduces": {
        "threshold": "exact counts, hashes, active views and learned artifact pointers",
        "comparison": "all of",
    },
}


def _drivers() -> Any:
    """The driver module, loaded so the recipes are read rather than restated."""
    spec = importlib.util.spec_from_file_location("scale_22b_pre_registration", DRIVERS)
    if spec is None or spec.loader is None:
        raise SystemExit("the 22B driver module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seal(document: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(document)
    sealed["content_hash"] = _sha256(_canonical(document))
    return sealed


def _contracts() -> dict[str, Any]:
    """The six frozen revision-1 contracts, S22B-010 through S22B-015."""
    drivers = _drivers()
    baseline = _load(EVIDENCE / "sprint-22b-baseline.json")
    host = _load(EVIDENCE / "sprint-22b-reference-host.json")

    return {
        "exit_criteria": _seal(
            {
                "item": "S22B-010",
                "criteria": EXIT_CRITERIA,
                "source": "the execution sprint allocation, verbatim",
                "moved_by_22b": 0,
                "may_be_moved_by_a_wave": False,
                "why_frozen_now": (
                    "four of the five are single numbers, and a single number is the easiest "
                    "thing in a measurement sprint to soften once it is missed"
                ),
                "partial_outcome_is_typed": (
                    "four of five met is a typed negative with a measured slope under "
                    "sprint-22b-evidence-baseline, not a failure to have tried and not a pass"
                ),
            }
        ),
        "dataset_recipes": _seal(
            {
                "item": "S22B-011",
                "section": "§2.2a — which dataset the recall floor reads",
                "recipes": drivers.DATASETS,
                "generators_are_the_released_harness": (
                    "both datasets are drawn by scripts/memory_ann_baseline.py's own "
                    "generators, the ones that sealed the 10^5 envelope on 2026-07-25. A 10^6 "
                    "recall number is comparable to that record only if the same function drew "
                    "both corpora, so the geometry is reused rather than re-implemented"
                ),
                "recall_exit_reads": "clustered",
                "uniform_reads_no_exit": True,
                "why_frozen_now": (
                    "after the numbers exist, choosing which dataset the floor reads would be "
                    "a result rather than a reading"
                ),
                "prior_art_1e5": {
                    "clustered_recall": baseline["prior_art"]["envelope_1e5_clustered"][
                        "ann_recall_at_result_limit"
                    ],
                    "uniform_recall": baseline["prior_art"]["envelope_1e5_uniform"][
                        "ann_recall_at_result_limit"
                    ],
                    "bound_by": "sprint-22b-baseline.json, which binds both envelope files",
                },
            }
        ),
        "probe_protocol": _seal(
            {
                "item": "S22B-012",
                "section": "§2.2b — what warm means",
                "protocol": drivers.PROBE_PROTOCOL,
                "measured_probes": drivers.PROBE_PROTOCOL["measured_probes"],
                "warmup_probes": drivers.PROBE_PROTOCOL["warmup_probes"],
                "cold_is_recorded_beside_every_warm_number": True,
                "may_be_reduced_by_a_wave": False,
                "why_frozen_now": (
                    "'warm' is the single most elastic word available to a sprint that misses "
                    "a latency exit, and 500 probes cost wall-clock that a pressed wave would "
                    "otherwise be tempted to save"
                ),
            }
        ),
        "throughput_reading": _seal(
            {
                "item": "S22B-013",
                "section": "§2.2c — which path each throughput claim measures",
                "ingest_exit_reads": (
                    "the governed write path: a real memory record with provenance, an event "
                    "and a revision, per item"
                ),
                "sustained_over_at_least": 50_000,
                "reported_per_decile": True,
                "bulk_engine_load_reads_an_exit": False,
                "embedding_writes_are_inside_the_ingest_loop": False,
                "why_embeddings_are_separate": (
                    "W0-F6: the hybrid recipe needs embedded items, and the obvious fix — "
                    "embedding inside the ingest loop — would change what the frozen ingest "
                    "reading measures. Embedding is its own measured step, read by no exit"
                ),
                "the_forbidden_move": (
                    "relabelling the bulk engine load as ingest. It is the one move §3.2 "
                    "forbids by name, and the gap between the two numbers is the finding"
                ),
            }
        ),
        "bounded_graph_configuration": _seal(
            {
                "item": "S22B-014",
                "section": "§2.2d — what bounded graph-assisted is",
                "configuration": drivers.bounded_graph_configuration(),
                "limits_hash": drivers.BOUNDED_GRAPH_LIMITS.canonical_hash(),
                "every_field_is_a_released_limit": (
                    "the configuration is a GraphResourceLimits instance; 22B introduces no "
                    "new knob, it fixes released ones"
                ),
                "may_be_tuned_after_a_number_exists": False,
                "on_a_miss": (
                    "report the miss and the measured slope. Tuning the recipe against the "
                    "exit and calling the tuning a configuration is the failure this contract "
                    "exists to make visible"
                ),
                "cutoffs_are_reported_beside_every_p95": True,
            }
        ),
        "filter_selectivity": _seal(
            {
                "item": "S22B-015",
                "section": "a sixth reading the plan did not enumerate — W0-D1",
                "predicate": drivers.FILTER_PREDICATE,
                "why_this_is_here": (
                    "§2.2 froze the five readings that could bend, and the filtered-ANN exit "
                    "turned out to rest on a sixth: a metadata predicate has a selectivity, "
                    "and 300 ms is a function of how much the filter removes. Choosing it "
                    "after the numbers exist would meet the exit by filtering to a friendlier "
                    "slice. W0 freezes it under the same rule as the other five rather than "
                    "leaving it to whichever wave first needs it"
                ),
                "decided_by": "the wave, under §2.3's last bullet; no threshold moved",
                "may_be_changed_after_a_number_exists": False,
            }
        ),
        "restore_checklist": _seal(
            {
                "item": "S22B-016",
                "section": "§2.2e — what restore must reproduce",
                "checklist": list(drivers.RESTORE_CHECKLIST),
                "live_learned_artifact": drivers.LIVE_LEARNED_ARTIFACT,
                "verified_by_query_not_by_digest": (
                    "D7 W3-F1: a digest proves bytes, not usability. The active view is "
                    "queried, and the learned artifact's bytes are loaded"
                ),
                "the_checklist_can_fail": (
                    "demonstrated in W0: run against a store that never held the artifact, the "
                    "pointer does not resolve and the checklist says so rather than passing "
                    "vacuously (22A W4-F2)"
                ),
            }
        ),
        "reference_host": _seal(
            {
                "item": "S22B-002",
                "section": "§1.4 — the reference host, declared once",
                "host_id": host["host_id"],
                "invariants_hash": host["invariants_hash"],
                "cpu": host["invariants"]["cpu"]["model"],
                "logical_cpus": host["invariants"]["cpu"]["logical_cpus"],
                "memory_total_kib": host["invariants"]["memory"]["total_kib"],
                "postgres_version": host["invariants"]["postgres"]["server_version"],
                "pgvector_version": host["invariants"]["postgres"]["extensions"].get("vector"),
                "storage_device": host["invariants"]["storage_postgres_data"]["device"],
                "postgres_settings_are_sealed": True,
                "why_settings_are_not_tuned": (
                    "the 10^5 envelope 22B extends was measured under these settings. Raising "
                    "maintenance_work_mem would buy a faster build at the price of the only "
                    "comparison the sprint has"
                ),
                "a_number_measured_elsewhere_closes_nothing": True,
            }
        ),
    }


def _write() -> None:
    recorded_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    drivers = _drivers()
    contracts = _contracts()

    contracts_document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W0",
        "items": [f"S22B-{number:03d}" for number in range(10, 17)],
        "recorded_at": recorded_at,
        "revision": 1,
        "contracts": contracts,
        "drivers_module": str(DRIVERS.relative_to(REPO)),
        "drivers_module_sha256": _sha256(DRIVERS.read_bytes()),
        "recipes_hash": drivers.recipes_hash(),
        "query_shapes_covered": sorted(drivers.QUERY_SHAPES),
        "query_shape_count": len(drivers.QUERY_SHAPES),
        "why_the_shapes_are_enumerated": (
            "22A W4-F1: a claim about coverage has to name the things covered. W2 says 'seven "
            "retrieval shapes'; this list is the seven, and a test asserts the enumeration"
        ),
        "inherited_unchanged": {
            "execution_contract": (
                "sections 0.1 through 0.4 of the Sprint 21D4 technical backlog, incorporated "
                "by reference, plus the six standing rules §0 graduates from 22A and D7"
            ),
            "migration_head": MIGRATION_HEAD,
            "0016": "a refusal, not a plan item",
            "carried_forward_by_name": ["W2-A1", "W3-A1"],
            "learning_surface": (
                "the live correction component keeps routing its canary groups; 22B drives no "
                "learner and touches no canary routing"
            ),
        },
        "what_this_revision_freezes": [
            "the five exit numbers, verbatim",
            "both dataset recipes, their generators and their seeds",
            "the warm/cold probe protocol and the probe counts",
            "which path each throughput claim measures",
            "the bounded graph-assisted configuration",
            "the filtered-ANN predicate and its selectivity",
            "the restore checklist and the live learned artifact it must load",
            "the declared reference host",
        ],
        "thresholds_changed": {"count": 0, "amendments_made_by_22b": 0},
        "measured_values": 0,
    }
    contracts_document["integrity_content_hash"] = _sha256(_canonical(contracts_document))
    OUTPUTS["contracts"].write_text(
        json.dumps(contracts_document, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pre: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W0",
        "items": ["S22B-016"],
        "recorded_at": recorded_at,
        "revision": 1,
        "supersedes": None,
        "why_revision_1": (
            "22B inherits 22A's execution contract but not its pre-registration: a vocabulary "
            "and a refusal are not readings, and nothing in 22A's revision 1 constrains a "
            "measurement"
        ),
        "contracts_sha256": _sha256(OUTPUTS["contracts"].read_bytes()),
        "contract_hashes": {name: body["content_hash"] for name, body in contracts.items()},
        "evidence_children_sha256": {
            name: _sha256((EVIDENCE / name).read_bytes()) for name in W0_CHILDREN
        },
        "drivers_module_sha256": _sha256(DRIVERS.read_bytes()),
        "recipes_hash": drivers.recipes_hash(),
        "reference_host_invariants_hash": _load(EVIDENCE / "sprint-22b-reference-host.json")[
            "invariants_hash"
        ],
        "predecessor": {
            "tag": "sprint-22a-domain-baseline",
            "commit": "291482448114ffed95a975c2b6a0d2be47a6a092",
            "verified_live_in": "sprint-22b-baseline.json",
        },
        "chronology": {
            "corpus_rows_at_10_6": 0,
            "exit_criteria_decided": 0,
            "envelopes_sealed": 0,
            "governed_items_ingested_at_scale": 0,
            "backups_taken": 0,
            "restores_verified": 0,
            "migrations_allocated": 0,
            "thresholds_moved": 0,
        },
        "measured_values": 0,
        "why_the_w0_slice_is_not_a_measured_value": (
            "sprint-22b-w0-slice.json runs every driver over a few hundred rows to prove they "
            "compose and can fail. Every 22B exit is a claim at 10^6 items, so no number in "
            "that record is one of the five, and the record says so in its own body"
        ),
        "outcome_tags": {
            "pass": "sprint-22b-scale-baseline",
            "stop": "sprint-22b-evidence-baseline",
        },
        "what_this_publication_forbids": [
            "moving any of the five exit numbers, in either direction",
            "reading the recall floor on the uniform dataset, or on any dataset but clustered",
            "reducing the probe count, or calling a measurement warm without the restart",
            "relabelling the bulk engine load as governed ingest",
            "folding embedding writes into the governed-ingest loop",
            "tuning the bounded graph configuration after its first measured number exists",
            "changing the filtered-ANN predicate or its selectivity after a number exists",
            "verifying a restore by comparing hashes instead of querying and loading",
            "allocating migration 0016, or any other storage-schema change",
            "shrinking the dataset to make a wave fit inside a timeout",
            "swapping the released HNSW substrate for another index type mid-measurement",
            "claiming W2-A1 or W3-A1 resolved by walking past them",
        ],
    }
    pre["integrity_content_hash"] = _sha256(_canonical(pre))
    OUTPUTS["pre_registration"].write_text(
        json.dumps(pre, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "revision": 1,
                "contracts": sorted(contracts),
                "contracts_sha256": pre["contracts_sha256"],
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "recipes_hash": pre["recipes_hash"],
                "reference_host_invariants_hash": pre["reference_host_invariants_hash"],
                "query_shapes": contracts_document["query_shape_count"],
                "exit_criteria": len(EXIT_CRITERIA),
                "measured_values": 0,
                "thresholds_changed": 0,
                "migration_head": MIGRATION_HEAD,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _module_from_source(source: str, name: str) -> Any:
    """Load a driver implementation from source text, with its repository root preserved.

    The module resolves `REPO` from its own `__file__`, so a historical copy written to a
    scratch directory would fail to import the released generators it composes over. The root
    is pinned to this repository instead, which is the whole point: both implementations must
    draw from the *same* released harness.
    """
    scratch = Path(tempfile.mkdtemp(prefix="scale22b-rebind-")) / f"{name}.py"
    scratch.write_text(
        source.replace(
            "REPO = Path(__file__).resolve().parent.parent", f"REPO = Path({str(REPO)!r})"
        ),
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location(name, scratch)
    if spec is None or spec.loader is None:
        raise SystemExit(f"could not load driver implementation {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pinned_source(pinned_hash: str) -> tuple[str, str]:
    """The exact bytes revision 1 pinned, found in history rather than reconstructed."""
    commits = subprocess.run(
        ["git", "log", "--format=%H", "--", "scripts/scale_22b.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    for commit in commits:
        blob = subprocess.run(
            ["git", "show", f"{commit}:scripts/scale_22b.py"],
            cwd=REPO,
            capture_output=True,
            check=True,
        ).stdout
        if _sha256(blob) == pinned_hash:
            return blob.decode("utf-8"), commit
    raise SystemExit(
        "the implementation revision 1 pinned is not in this repository's history, so the "
        "corpus it drew cannot be reproduced and no re-binding is possible"
    )


def _identity_proof() -> dict[str, Any]:
    """Execute both implementations and compare what they draw. Recomputed, never asserted."""
    pre = _load(OUTPUTS["pre_registration"])
    pinned_hash = pre["drivers_module_sha256"]
    current_hash = _sha256(DRIVERS.read_bytes())
    source, commit = _pinned_source(pinned_hash)

    pinned = _module_from_source(source, "scale_22b_pinned")
    current = _module_from_source(DRIVERS.read_text(encoding="utf-8"), "scale_22b_current")

    datasets: dict[str, Any] = {}
    for dataset in sorted(pinned.DATASETS):
        head_before = pinned.corpus_rows(dataset, REBIND_SAMPLE_ROWS)
        head_after = current.corpus_rows(dataset, REBIND_SAMPLE_ROWS)
        window_before = pinned.corpus_rows(dataset, REBIND_OFFSET_ROWS, offset=REBIND_OFFSET)
        window_after = current.corpus_rows(dataset, REBIND_OFFSET_ROWS, offset=REBIND_OFFSET)
        datasets[dataset] = {
            "rows_compared": REBIND_SAMPLE_ROWS + REBIND_OFFSET_ROWS,
            "head_identical": head_before == head_after,
            "offset_window_identical": window_before == window_after,
            "addressing_agrees_with_stream": head_after[REBIND_OFFSET:] == window_after,
            "rows_sha256_before": _sha256(_canonical(head_before + window_before)),
            "rows_sha256_after": _sha256(_canonical(head_after + window_after)),
        }

    return {
        "from_sha256": pinned_hash,
        "from_commit": commit,
        "to_sha256": current_hash,
        "datasets": datasets,
        "corpus_identical": all(
            entry["head_identical"]
            and entry["offset_window_identical"]
            and entry["rows_sha256_before"] == entry["rows_sha256_after"]
            for entry in datasets.values()
        ),
        "recipes_hash_before": pinned.recipes_hash(),
        "recipes_hash_after": current.recipes_hash(),
        "recipes_unchanged": pinned.recipes_hash() == current.recipes_hash(),
        "query_shapes_before": sorted(pinned.QUERY_SHAPES),
        "query_shapes_after": sorted(current.QUERY_SHAPES),
        "shapes_unchanged": sorted(pinned.QUERY_SHAPES) == sorted(current.QUERY_SHAPES),
    }


def _rebind(reason: str) -> None:
    proof = _identity_proof()
    if not (proof["corpus_identical"] and proof["recipes_unchanged"] and proof["shapes_unchanged"]):
        raise SystemExit(
            "this driver change alters the corpus, the recipes or the measured shapes. It "
            "cannot be re-bound: that is a finding, and the sprint stops on it rather than "
            "re-pointing its own authority at a different experiment"
        )
    record = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W1",
        "items": ["S22B-020"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
        "reason": reason,
        "proof": proof,
        "what_this_is_not": (
            "not an amendment. No reading moved, no threshold moved and the pre-registration "
            "is not edited: revision 1 still pins the implementation it pinned. This record "
            "carries the executed proof that the implementation now in the tree draws the same "
            "corpus, so the pin follows the defect fix instead of forbidding it"
        ),
        "what_cannot_be_re_bound": (
            "a change that alters a drawn row, the recipes hash or the seven measured shapes. "
            "The proof is executed on every --check, so this record cannot outlive its truth"
        ),
    }
    record["integrity_content_hash"] = _sha256(_canonical(record))
    REBIND.write_text(
        json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": REBIND.name,
                "from_sha256": proof["from_sha256"][:16],
                "from_commit": proof["from_commit"][:12],
                "to_sha256": proof["to_sha256"][:16],
                "corpus_identical": proof["corpus_identical"],
                "recipes_unchanged": proof["recipes_unchanged"],
                "shapes_unchanged": proof["shapes_unchanged"],
                "rows_compared": sum(
                    entry["rows_compared"] for entry in proof["datasets"].values()
                ),
            },
            indent=1,
            sort_keys=True,
        )
    )


def _drivers_are_bound(pre: dict[str, Any]) -> dict[str, Any]:
    """The module pin, satisfied directly or through a re-binding whose proof still executes."""
    current = _sha256(DRIVERS.read_bytes())
    if current == pre["drivers_module_sha256"]:
        return {"bound": "directly", "sha256": current}
    if not REBIND.exists():
        raise SystemExit(
            "scripts/scale_22b.py changed after the pre-registration was published, and no "
            "re-binding record justifies it"
        )
    record = _load(REBIND)
    _verify_seal(REBIND, record)
    if record["pre_registration_sha256"] != _sha256(OUTPUTS["pre_registration"].read_bytes()):
        raise SystemExit("the re-binding record does not belong to this pre-registration")
    if record["proof"]["from_sha256"] != pre["drivers_module_sha256"]:
        raise SystemExit("the re-binding record starts from a different implementation")
    if record["proof"]["to_sha256"] != current:
        raise SystemExit(
            "scripts/scale_22b.py has changed again since it was re-bound; re-run --rebind"
        )
    # Executed, not read back: the record's own claim is recomputed here, so a re-binding
    # cannot outlive the identity it asserts (22A W4-F2).
    proof = _identity_proof()
    if not (proof["corpus_identical"] and proof["recipes_unchanged"] and proof["shapes_unchanged"]):
        raise SystemExit("the re-binding record's identity proof no longer reproduces")
    return {
        "bound": "through a re-binding",
        "sha256": current,
        "from_sha256": record["proof"]["from_sha256"],
        "reason": record["reason"],
        "proof_recomputed": True,
    }


HOST_CHANGE = EVIDENCE / "sprint-22b-host-change.json"


def _host_is_bound(pre: dict[str, Any]) -> dict[str, Any]:
    """The declared host, either the one revision 1 bound or a sealed successor to it.

    W1-F5 forced this. A driver re-binding can prove nothing changed; a host change cannot —
    the machine really is different, and pretending otherwise would be the exact dishonesty
    §1.4 and §4 exist to prevent. So the successor is admitted only through a sealed record
    that names both hosts, the invariant groups that differ, and what the delta can and cannot
    affect. Every number measured afterwards binds the successor, and the chain says so.
    """
    original = _load(EVIDENCE / "sprint-22b-reference-host.json")
    if original["invariants_hash"] == pre["reference_host_invariants_hash"] and not (
        HOST_CHANGE.exists()
    ):
        return {"host_id": original["host_id"], "bound": "as published"}
    if not HOST_CHANGE.exists():
        raise SystemExit(
            "the reference-host record no longer matches the one 22B bound, and no host-change "
            "record justifies it"
        )
    change = _load(HOST_CHANGE)
    _verify_seal(HOST_CHANGE, change)
    if change["from_invariants_hash"] != pre["reference_host_invariants_hash"]:
        raise SystemExit("the host-change record starts from a host 22B never bound")
    if change["from_invariants_hash"] != original["invariants_hash"]:
        raise SystemExit("the superseded host record has been edited rather than superseded")
    successor = _load(EVIDENCE / "sprint-22b-reference-host-2.json")
    _verify_seal(EVIDENCE / "sprint-22b-reference-host-2.json", successor)
    if successor["invariants_hash"] != change["to_invariants_hash"]:
        raise SystemExit("the successor host record does not match the sealed change")
    if _sha256(_canonical(successor["invariants"])) != successor["invariants_hash"]:
        raise SystemExit("the successor host's invariants hash does not reproduce")
    if not change["postgres_settings_unchanged"]:
        raise SystemExit(
            "the host change moved a sealed PostgreSQL setting. §2.3 forbids tuning a "
            "pre-registered configuration, and a host change is not a licence to do it"
        )
    return {
        "host_id": successor["host_id"],
        "bound": "through a sealed host change",
        "from_host_id": change["from_host_id"],
        "invariant_groups_changed": change["invariant_groups_changed"],
        "reason": change["reason"],
    }


def _verify_seal(path: Path, document: dict[str, Any]) -> None:
    body = {key: value for key, value in document.items() if key != "integrity_content_hash"}
    if _sha256(_canonical(body)) != document.get("integrity_content_hash"):
        raise SystemExit(f"{path.name} integrity hash does not match its content")


def _check() -> None:
    drivers = _drivers()
    documents = {name: _load(path) for name, path in OUTPUTS.items()}
    for name, document in documents.items():
        _verify_seal(OUTPUTS[name], document)

    pre = documents["pre_registration"]
    if _sha256(OUTPUTS["contracts"].read_bytes()) != pre["contracts_sha256"]:
        raise SystemExit("the contracts file changed after the pre-registration was published")
    for name, expected in pre["evidence_children_sha256"].items():
        if _sha256((EVIDENCE / name).read_bytes()) != expected:
            raise SystemExit(f"W0 authority record changed after publication: {name}")
    for name, expected in pre["contract_hashes"].items():
        body = dict(documents["contracts"]["contracts"][name])
        if body.pop("content_hash") != expected or _sha256(_canonical(body)) != expected:
            raise SystemExit(f"contract {name} does not reproduce its frozen hash")

    # The recipes are recomputed from the driver module, never read back as a literal, so a
    # driver whose frozen parameters drift fails here rather than at a wave's convenience.
    if drivers.recipes_hash() != pre["recipes_hash"]:
        raise SystemExit(
            "the 22B recipes have drifted from the pre-registration: a dataset, a probe "
            "protocol, a filter selectivity or the graph configuration changed after "
            "publication"
        )
    binding = _drivers_are_bound(pre)

    contracts = documents["contracts"]["contracts"]
    if contracts["exit_criteria"]["criteria"] != EXIT_CRITERIA:
        raise SystemExit("an exit criterion has drifted from this script's constants")
    if contracts["dataset_recipes"]["recall_exit_reads"] != "clustered":
        raise SystemExit("the recall floor's dataset has been re-read")
    if contracts["probe_protocol"]["measured_probes"] != drivers.PROBE_PROTOCOL["measured_probes"]:
        raise SystemExit("the probe count has drifted from the frozen protocol")
    if (
        contracts["bounded_graph_configuration"]["limits_hash"]
        != drivers.BOUNDED_GRAPH_LIMITS.canonical_hash()
    ):
        raise SystemExit("the bounded graph configuration has been tuned after publication")
    if contracts["filter_selectivity"]["predicate"] != drivers.FILTER_PREDICATE:
        raise SystemExit("the filtered-ANN predicate or its selectivity has changed")

    host = _host_is_bound(pre)

    if any(pre["chronology"].values()) or pre["measured_values"]:
        raise SystemExit("the pre-registration contains measured values")
    if documents["contracts"]["thresholds_changed"]["count"]:
        raise SystemExit("revision 1 moves a threshold; 22B moves none")
    if documents["contracts"]["query_shape_count"] != 7:
        raise SystemExit("the seven W2 retrieval shapes are no longer seven (22A W4-F1)")

    print(
        json.dumps(
            {
                "checked": sorted(OUTPUTS),
                "contracts_verified": len(pre["contract_hashes"]),
                "w0_children_verified": len(pre["evidence_children_sha256"]),
                "exit_criteria_verified": len(EXIT_CRITERIA),
                "query_shapes_verified": documents["contracts"]["query_shape_count"],
                "recipes_hash_reproduces": True,
                "drivers_module": binding,
                "reference_host": host,
                "pre_registration_sha256": _sha256(OUTPUTS["pre_registration"].read_bytes()),
                "measured_values_before_publication": 0,
                "thresholds_changed": 0,
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check_chronology(later: tuple[Path, ...]) -> None:
    pre_path = OUTPUTS["pre_registration"]
    pre = _load(pre_path)
    _verify_seal(pre_path, pre)
    expected = _sha256(pre_path.read_bytes())
    published = datetime.fromisoformat(pre["recorded_at"].replace("Z", "+00:00"))

    accepted = []
    for path in later:
        document = _load(path)
        if document.get("pre_registration_sha256") != expected:
            raise SystemExit(f"{path.name} does not carry the pre-registration sha256")
        recorded = datetime.fromisoformat(document["recorded_at"].replace("Z", "+00:00"))
        if recorded < published:
            raise SystemExit(f"{path.name} predates the pre-registration it claims to follow")
        accepted.append(path.name)

    print(
        json.dumps(
            {"pre_registration_sha256": expected, "accepted": sorted(accepted)},
            indent=1,
            sort_keys=True,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--rebind",
        metavar="REASON",
        help="re-bind the driver module pin after a defect fix, with an executed identity proof",
    )
    parser.add_argument("--check-chronology", action="store_true")
    parser.add_argument("--later", nargs="*", default=[])
    arguments = parser.parse_args()

    if arguments.rebind:
        _rebind(arguments.rebind)
    if arguments.check:
        _check()
    if arguments.check_chronology:
        _check_chronology(tuple(Path(item) for item in arguments.later))
    if not arguments.check and not arguments.check_chronology and not arguments.rebind:
        _write()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
