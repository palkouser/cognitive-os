#!/usr/bin/env python3
"""S21D5-042. Replay the development benchmarks, and predict that nothing moves.

Development only. It selects nothing, closes no gate and never touches the D5 retrieval pool.
It exists because pointing a code path at unseen evidence before checking it on published
evidence is how a sprint discovers a defect in the one measurement it cannot repeat.

D4's replay had one arm it expected to move: the bounded-GED comparator had just been given a
fixed iteration budget. **D5 changed no arm, no comparator, no weight and no fusion constant.**
`structure_fallback` is a projection flag, off by default at every released call site, and every
stored development graph was projected without it. So the prediction here is stronger and
simpler than D4's, and it is declared before the run:

    every arm reproduces its predecessor value exactly, on every pool that resolves.

An arm that moves is a defect in something this wave believed it had not touched.

One pool cannot be replayed, and that is a finding rather than a gap in this record.
`sprint-21d4-retrieval-emg-root.json` declares sixty pairs whose blobs are in no store — see
S21D5-W3-F1 in `sprint-21d5-surface.json`. D4's released result stands as evidence of what was
measured; it is simply no longer re-runnable, and this record says so with the load that failed
rather than by omitting the pool.

    UV_CACHE_DIR=.cache/uv uv run python scripts/retrieval_development_d5.py \\
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.domain.common import utc_now  # noqa: E402
from cognitive_os.domain.experience_graph import (  # noqa: E402
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
)
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET  # noqa: E402
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d5-pre-registration.json"
CONTRACTS = EVIDENCE / "sprint-21d5-contracts.json"
SURFACE = EVIDENCE / "sprint-21d5-surface.json"
OUTPUT = EVIDENCE / "sprint-21d5-retrieval-development.json"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")

ARM_ORDER = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)

#: The metrics compared against the predecessor record, per arm. Latency is deliberately absent:
#: it is a property of this host on this afternoon, and comparing it across sprints would report
#: the machine rather than the arm.
COMPARED = ("top_5_recall", "mrr_at_10", "ndcg_at_10", "coverage", "timeouts", "budget_cutoffs")

POOLS = (
    {
        "name": "d1_eighty_query_development_set",
        "root": EVIDENCE / "sprint-21d1-emg-root.json",
        "artifacts": DATA / "artifacts-s21d1",
        "queries": EVIDENCE / "sprint-21d1-graph-queries.json",
        "predecessor": EVIDENCE / "sprint-21d4-retrieval-development.json",
        "predecessor_path": ("pools", "d1_eighty_query_development_set", "arms"),
        "frozen_in": "Sprint 21D1, before any ranking was produced",
    },
    {
        "name": "d3_spent_retrieval_holdout",
        "root": EVIDENCE / "sprint-21d3-retrieval-emg-root.json",
        "artifacts": DATA / "artifacts-s21d3",
        "queries": EVIDENCE / "sprint-21d3-retrieval-queries.json",
        "predecessor": EVIDENCE / "sprint-21d4-retrieval-development.json",
        "predecessor_path": ("pools", "d3_spent_retrieval_holdout", "arms"),
        "frozen_in": "Sprint 21D3, before the holdout was resolved; spent",
    },
    {
        "name": "d4_spent_retrieval_holdout",
        "root": EVIDENCE / "sprint-21d4-retrieval-emg-root.json",
        "artifacts": DATA / "artifacts-s21d4",
        "queries": EVIDENCE / "sprint-21d4-retrieval-queries.json",
        "predecessor": EVIDENCE / "sprint-21d4-retrieval-holdout-result.json",
        "predecessor_path": ("arms",),
        "frozen_in": "Sprint 21D4, before its holdout was resolved; spent",
    },
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _at(document: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        document = document[key]
    return document


def _resolves(pool: dict[str, Any]) -> dict[str, Any]:
    """Whether this pool's graphs are still in a store, before anything tries to rank them."""
    evidence = load_evidence(pool["root"], pool["artifacts"])
    graphs = [side for pair in evidence.pairs for side in (pair.failed, pair.successful)]
    return {
        "declared_pairs": evidence.declared_pairs,
        "resolved_pairs": len(evidence.pairs),
        "intact": evidence.intact,
        "missing_bytes": len(evidence.missing_bytes),
        "graphs": len(graphs),
        "graphs_carrying_terms": sum(1 for graph in graphs if graph.search_terms),
        "reading": (
            "these graphs were projected before structure_fallback existed and before the "
            "surface field existed at all, so the complete surface contributes no term here "
            "and any movement in the numbers below comes from somewhere else"
        ),
    }


def _benchmark(pool: dict[str, Any], model: Path) -> dict[str, Any]:
    """The operator command, run exactly as an operator would run it."""
    done = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "scripts" / "experience.py"),
            "graph-benchmark",
            "--graph-root",
            str(pool["root"]),
            "--artifact-root",
            str(pool["artifacts"]),
            "--queries",
            str(pool["queries"]),
            "--model",
            str(model),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        ],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
        check=False,
    )
    if done.returncode != 0:
        raise SystemExit(f"graph-benchmark refused:\n{done.stderr}")
    return dict(json.loads(done.stdout))


def _comparison(pool: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Every arm against its predecessor value. No arm is exempt this time."""
    recorded = _at(json.loads(pool["predecessor"].read_text()), pool["predecessor_path"])
    rows: dict[str, Any] = {}
    for arm in ARM_ORDER:
        measured, before = payload["arms"][arm], recorded[arm]
        values = {
            metric: {"recorded": before[metric], "measured": measured[metric]}
            for metric in COMPARED
        }
        rows[arm] = {
            **values,
            "reproduced": all(item["recorded"] == item["measured"] for item in values.values()),
        }
    moved = sorted(arm for arm, row in rows.items() if not row["reproduced"])
    return {
        "predecessor": str(pool["predecessor"].relative_to(REPOSITORY)),
        "predecessor_sha256": _digest(pool["predecessor"].read_bytes()),
        "predecessor_path": list(pool["predecessor_path"]),
        "per_arm": rows,
        "arms_that_moved": moved,
        "every_arm_reproduced": not moved,
        "no_arm_was_exempt": (
            "D4's replay excused one arm because W3 had just decided its comparator. D5 "
            "changed no arm, so every one of the six is held to its recorded value"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    model = arguments.model.resolve()

    before = {pool["name"]: fingerprint(pool["artifacts"]) for pool in POOLS}
    pools: dict[str, Any] = {}
    unreplayable: list[str] = []
    for pool in POOLS:
        resolution = _resolves(pool)
        row: dict[str, Any] = {
            "root": str(pool["root"].relative_to(REPOSITORY)),
            "artifact_root": str(pool["artifacts"]),
            "access": "read_only",
            "frozen_in": pool["frozen_in"],
            "graph_resolution": resolution,
        }
        if not resolution["resolved_pairs"]:
            unreplayable.append(pool["name"])
            row["replayed"] = False
            row["why_not"] = (
                "the root declares pairs whose blobs are in no store; see S21D5-W3-F1 in "
                "sprint-21d5-surface.json. Recorded with the failed load rather than omitted"
            )
            pools[pool["name"]] = row
            continue
        payload = _benchmark(pool, model)
        pools[pool["name"]] = {
            **row,
            "replayed": True,
            "query_set": {
                **payload["query_manifest"],
                "path": str(pool["queries"].relative_to(REPOSITORY)),
            },
            "graph_set": payload["graph_set"],
            "resource_policy": payload["resource_policy"],
            "model": payload["model"],
            "benchmark_content_hash": payload["content_hash"],
            "benchmark_schema_version": payload["schema_version"],
            "arms": {arm: payload["arms"][arm] for arm in ARM_ORDER},
            "repeated_ranking_agreement_by_arm": payload["repeated_ranking_agreement_by_arm"],
            "every_arm_reproduces_its_own_ranking": all(
                payload["repeated_ranking_agreement_by_arm"].values()
            ),
            "against_the_predecessor": _comparison(pool, payload),
        }
    after = {pool["name"]: fingerprint(pool["artifacts"]) for pool in POOLS}

    replayed = [row for row in pools.values() if row["replayed"]]
    held = all(
        row["against_the_predecessor"]["every_arm_reproduced"]
        and row["every_arm_reproduces_its_own_ranking"]
        for row in replayed
    )
    evidence = {
        "schema_version": 1,
        "sprint": "21D5",
        "wave": "W3",
        "items": ["S21D5-042"],
        "recorded_at": utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "contracts_sha256": _digest(CONTRACTS.read_bytes()),
        "surface_sha256": _digest(SURFACE.read_bytes()),
        "label": "development_only",
        "gating": False,
        "purpose": (
            "measure the released arms on query sets whose answers are already published, "
            "before the D5 holdout is resolved. It closes no gate: Gate D1 condition 15 and "
            "Gate L2 condition 24 are decided only by the D5 unseen-task holdout, which this "
            "command does not read"
        ),
        "arms_changed_in_this_sprint": [],
        "ged_iteration_budget": GED_ITERATION_BUDGET,
        "expectation_declared_before_the_run": (
            "every arm reproduces its predecessor value exactly, on every pool that resolves. "
            "D5 changed no arm, no comparator, no weight and no fusion constant, and "
            "structure_fallback is a projection flag that no stored development graph was "
            "projected under. An arm that moves is a defect in something this wave believed it "
            "had not touched"
        ),
        "pools": pools,
        "pools_replayed": len(replayed),
        "pools_that_could_not_be_replayed": unreplayable,
        "every_arm_reproduced": all(
            row["against_the_predecessor"]["every_arm_reproduced"] for row in replayed
        ),
        "every_arm_reproduces_its_own_ranking": all(
            row["every_arm_reproduces_its_own_ranking"] for row in replayed
        ),
        "store_writes": {
            "fingerprints_before": before,
            "fingerprints_after": after,
            "unchanged": before == after,
        },
        "d5_retrieval_pool_read": False,
        "final_or_canary_outcomes_inspected": 0,
        "final_outcomes_inspected": False,
    }
    sealed = dict(evidence)
    sealed["integrity_content_hash"] = _digest(_canonical(evidence))
    arguments.output.write_text(
        json.dumps(sealed, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    for name, row in pools.items():
        if not row["replayed"]:
            print(f"  {name}: not replayable ({row['graph_resolution']['missing_bytes']} missing)")
            continue
        comparison = row["against_the_predecessor"]
        print(f"  {name}")
        print(
            f"    graphs carrying terms: {row['graph_resolution']['graphs_carrying_terms']}"
            f" of {row['graph_resolution']['graphs']}"
        )
        print(f"    arms that moved: {comparison['arms_that_moved'] or 'none'}")
        print(
            f"    every arm reproduces its own ranking: "
            f"{row['every_arm_reproduces_its_own_ranking']}"
        )
    print(f"  store writes: {0 if before == after else -1}")
    print(f"  seal {sealed['integrity_content_hash']}")
    return 0 if held and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
