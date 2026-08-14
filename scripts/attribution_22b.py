"""S22B-042. Which of two events moved the envelope: W3's mutations, or the restore.

W4 re-measured the envelope on the restored store and three shapes came back much slower. The
obvious reading — *the restore changed the envelope* — is wrong for those three, and the record
that said so would have been the sprint's most confident error.

Two things happened between W2's envelope and W4's, not one. W3 put twenty-five thousand
governed transitions through the store, and then the store was backed up and restored. Three of
the seven shapes read the **governed** store rather than the corpus (`varies_with_the_dataset:
false`), and W3 is what changed it: `stale_item` returned **zero rows** in W2 because no item
was stale yet, and twenty afterwards. A shape that starts finding rows gets slower for a reason
that has nothing to do with a restore.

So each shape is re-measured a third time — on the **source** store, now, with both stores
present — and the W2 -> W4 difference is split at that point:

    w3_effect      = source_now - w2_source     (what the mutations did)
    restore_effect = restored   - source_now    (what the restore did)

**This control is post hoc.** It was designed after the restored numbers existed, which is
exactly the situation §2.3 is suspicious of. Two things keep it honest: it reads **no exit
criterion** — all five are decided on W2's sealed measurements, which this cannot touch — and it
is reported whichever way it comes out. It came out against the wave's first reading.

    UV_CACHE_DIR=.cache/uv uv run python scripts/attribution_22b.py
    UV_CACHE_DIR=.cache/uv uv run python scripts/attribution_22b.py --check

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
OUTPUT = EVIDENCE / "sprint-22b-w4-attribution.json"

#: The envelope at each of the three points, on the clustered corpus. The source control is two
#: records because the driver was run twice — five shapes, then the two that need the frozen
#: MiniLM — and they are unioned rather than merged into one hand-written file, so every number
#: still sits in the record the driver actually wrote.
W2_SOURCE = "sprint-22b-w2-envelope-clustered.json"
SOURCE_NOW = (
    "sprint-22b-w4-source-envelope-clustered.json",
    "sprint-22b-w4-source-envelope-clustered-graph-and-exact.json",
)
RESTORED = "sprint-22b-w4-restored-envelope-clustered.json"

#: Recall, at the same three points, on both corpora. Uniform's third point is worth having
#: because its index was rebuilt *inside the source store* by W3's `REINDEX CONCURRENTLY`, which
#: separates "any rebuild moves the graph" from "the restore moves the graph".
RECALL: dict[str, dict[str, str]] = {
    "clustered": {
        "w2_source": "sprint-22b-w2-recall-clustered.json",
        "source_now": "sprint-22b-w4-source-recall-clustered.json",
        "restored": "sprint-22b-w4-restored-recall-clustered.json",
    },
    "uniform": {
        "w2_source": "sprint-22b-w2-recall-uniform.json",
        "source_now": "sprint-22b-w4-source-recall-uniform.json",
        "restored": "sprint-22b-w4-restored-recall-uniform.json",
    },
}

#: A difference counts as material only if it clears **both** bars. The absolute bar stops a
#: 1.5 ms shape from being called a 200 % regression; the relative bar stops a 4 ms move on a
#: 1200 ms shape from being called a change at all.
MATERIAL_MS = 2.0
MATERIAL_FRACTION = 0.05


def _helpers() -> Any:
    """`envelope_22b.py`, for the one implementation of loading and sealing in this sprint."""
    path = REPO / "scripts/envelope_22b.py"
    spec = importlib.util.spec_from_file_location("envelope_22b_helpers", path)
    if spec is None or spec.loader is None:
        raise SystemExit("the W2 envelope assembler could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _material(delta: float, base: float) -> bool:
    return abs(delta) >= MATERIAL_MS and (not base or abs(delta) / base >= MATERIAL_FRACTION)


def _attribute(w3_material: bool, restore_material: bool) -> str:
    if w3_material and restore_material:
        return "both"
    if w3_material:
        return "w3_mutations"
    if restore_material:
        return "restore"
    return "neither"


def _source_now(load: Any) -> dict[str, Any]:
    """Union the control records, refusing an overlap rather than silently preferring one."""
    measured: dict[str, Any] = {}
    for filename in SOURCE_NOW:
        for shape, reading in load(EVIDENCE / filename)["measured"].items():
            if shape in measured:
                raise SystemExit(f"{shape} was measured by two control records")
            measured[shape] = reading
    return measured


def _assemble() -> dict[str, Any]:
    helpers = _helpers()
    load, sha256, canonical = helpers._load, helpers._sha256, helpers._canonical

    w2 = load(EVIDENCE / W2_SOURCE)
    restored = load(EVIDENCE / RESTORED)
    now = _source_now(load)

    declared = set(w2["shapes_in_the_pre_registration"])
    if set(now) != declared:
        missing = sorted(declared - set(now))
        raise SystemExit(f"the control does not cover every shape: {missing} unattributed")

    shapes: dict[str, Any] = {}
    for shape in sorted(declared):
        before = float(w2["measured"][shape]["p95_ms"])
        middle = float(now[shape]["p95_ms"])
        after = float(restored["measured"][shape]["p95_ms"])
        w3_effect = round(middle - before, 3)
        restore_effect = round(after - middle, 3)
        w3_material = _material(w3_effect, before)
        restore_material = _material(restore_effect, middle)
        shapes[shape] = {
            "w2_source_p95_ms": before,
            "source_now_p95_ms": middle,
            "restored_p95_ms": after,
            "w3_effect_ms": w3_effect,
            "restore_effect_ms": restore_effect,
            "w3_effect_is_material": w3_material,
            "restore_effect_is_material": restore_material,
            "attributed_to": _attribute(w3_material, restore_material),
            # The three governed shapes share one store with both corpora, so a change in them
            # is a change in what W3 did to it, not in what the million rows look like.
            "reads_the_governed_store_not_the_corpus": bool(
                w2["measured"][shape].get("varies_with_the_dataset") is False
            ),
            "rows_returned": {
                "w2_source": w2["measured"][shape].get("last_result", {}).get("results"),
                "source_now": now[shape].get("last_result", {}).get("results"),
                "restored": restored["measured"][shape].get("last_result", {}).get("results"),
            },
        }

    recall: dict[str, Any] = {}
    for dataset, sources in RECALL.items():
        values = {point: load(EVIDENCE / name)["recall_at_k"] for point, name in sources.items()}
        recall[dataset] = {
            **values,
            "w3_effect": round(values["source_now"] - values["w2_source"], 4),
            "restore_effect": round(values["restored"] - values["source_now"], 4),
            "source_is_unchanged_since_w2": values["source_now"] == values["w2_source"],
            "read_from": sources,
        }

    changed_by_restore = sorted(
        shape for shape, entry in shapes.items() if entry["attributed_to"] == "restore"
    )
    document: dict[str, Any] = {
        "schema_version": 1,
        "sprint": "22B",
        "wave": "W4",
        "items": ["S22B-042"],
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "reads_an_exit_criterion": False,
        "pre_registered": False,
        "why_it_is_post_hoc": (
            "the control was designed after the restored numbers existed. It decides nothing: "
            "all five exit criteria are read from W2's and W1's and W3's sealed measurements, "
            "which this record cannot reach. It changes what the wave's finding is *about*"
        ),
        "materiality": {
            "absolute_ms": MATERIAL_MS,
            "relative_fraction": MATERIAL_FRACTION,
            "rule": "a difference is material only if it clears both bars",
        },
        "dataset": "clustered",
        "why_clustered": (
            "the clustered corpus is the one the recall exit is defined over and the one every "
            "mutation wave left alone, so a change in it is a change in the index rather than "
            "in the rows"
        ),
        "shapes": shapes,
        "shapes_attributed_to_the_restore": changed_by_restore,
        "shapes_attributed_to_w3_mutations": sorted(
            shape
            for shape, entry in shapes.items()
            if entry["attributed_to"] in {"w3_mutations", "both"}
        ),
        "recall": recall,
        "finding": (
            "the restore changes exactly one thing in the envelope: the clustered corpus HNSW "
            "graph, which pg_restore rebuilds. Approximate retrieval over it is 163 % slower and "
            "its recall@10 falls from 0.9636 to 0.9410, below the 0.95 floor. Every other shape "
            "that looked slower on the restored store was slowed by W3's mutations instead, and "
            "on those the restored store is *faster* than the mutated source, because a restore "
            "also compacts what mutation left behind"
        ),
        "what_the_first_reading_got_wrong": (
            "that the restore had changed the whole envelope. Three of the seven shapes read the "
            "governed store rather than the corpus, and W3 is what changed it: stale_item "
            "returned zero rows in W2 and twenty afterwards"
        ),
        "sources_sha256": {
            name: sha256((EVIDENCE / name).read_bytes())
            for name in (
                W2_SOURCE,
                *SOURCE_NOW,
                RESTORED,
                *(source for group in RECALL.values() for source in group.values()),
            )
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
                "shapes_attributed_to_the_restore": document["shapes_attributed_to_the_restore"],
                "shapes_attributed_to_w3_mutations": document["shapes_attributed_to_w3_mutations"],
                "clustered_recall": document["recall"]["clustered"],
                "integrity_content_hash": document["integrity_content_hash"],
            },
            indent=1,
            sort_keys=True,
        )
    )


def _check() -> None:
    """Recompute from the sealed measurements and refuse any difference (22A W4-F2)."""
    helpers = _helpers()
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
        raise SystemExit(f"the attribution record no longer reproduces: {differing}")
    print(
        json.dumps(
            {
                "reproduces_from_sources": True,
                "shapes_attributed_to_the_restore": stored["shapes_attributed_to_the_restore"],
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
