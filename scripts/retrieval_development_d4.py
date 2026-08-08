#!/usr/bin/env python3
"""S21D4-042. Replay both development sets under the widened surface and the decided comparator.

Development only. It selects nothing, closes no gate and never touches the D4 retrieval pool.
It exists so that two changes made in W3 are measured on query sets whose answers are already
published, before either is pointed at evidence nobody has seen:

*The widened surface (S21D4-040).* Every graph in both stored roots was projected before the
field existed and carries no terms, so the surface change is a code path here rather than a
data change -- and the replay's job is to show that a code path that widens nothing moves
nothing. The term counts are measured rather than assumed.

*The decided comparator (S21D4-041).* This one is expected to move, and in a stated direction.
S21D3-042 recorded `minilm_shortlist_plus_bounded_ged: false` for repeated-ranking agreement on
the D1 set: the arm did not reproduce its own ranking across two passes of a single run. Under
a fixed iteration budget it has to.

So every arm falls into exactly one of two boxes declared before the run: reproduces its
predecessor value, or is the one arm whose comparator changed. An arm that moves without having
been changed is a defect, not a result.

    UV_CACHE_DIR=.cache/uv uv run python scripts/retrieval_development_d4.py \\
        --model /home/palkouser/projekt/cognitive-os-data/models/all-MiniLM-L6-v2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

REPOSITORY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY / "src"))

from cognitive_os.coding.reality_integrity import fingerprint  # noqa: E402
from cognitive_os.domain.experience_graph import (  # noqa: E402
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
)
from cognitive_os.experience.graph_retrieval import GED_ITERATION_BUDGET  # noqa: E402
from cognitive_os.experience.graph_store import load_evidence  # noqa: E402

EVIDENCE = REPOSITORY / "docs/sprints/sprint-21/evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d4-pre-registration.json"
SURFACE = EVIDENCE / "sprint-21d4-surface.json"
GED_DECISION = EVIDENCE / "sprint-21d4-ged-decision.json"
OUTPUT = EVIDENCE / "sprint-21d4-retrieval-development.json"

DATA = Path("/home/palkouser/projekt/cognitive-os-data")

#: The comparators, then the one candidate, in the order they are reported.
ARM_ORDER = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)

#: The one arm W3 changed. Declared here, before the replay runs, so "expected to move" is a
#: prediction rather than a description written after seeing which numbers moved.
CHANGED_ARM = "minilm_shortlist_plus_bounded_ged"

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
        "predecessor": EVIDENCE / "sprint-21d3-d1-retrieval-development.json",
        "predecessor_arms": "arms",
        "predecessor_agreement": "repeated_ranking_agreement_by_arm",
        "frozen_in": "Sprint 21D1, before any ranking was produced",
    },
    {
        "name": "d3_spent_retrieval_holdout",
        "root": EVIDENCE / "sprint-21d3-retrieval-emg-root.json",
        "artifacts": DATA / "artifacts-s21d3",
        "queries": EVIDENCE / "sprint-21d3-retrieval-queries.json",
        "predecessor": EVIDENCE / "sprint-21d3-retrieval-holdout-result.json",
        "predecessor_arms": "arms",
        "predecessor_agreement": None,
        "frozen_in": "Sprint 21D3, before the holdout was resolved; spent",
    },
)


def _digest(value: bytes | str) -> str:
    return sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, indent=1, sort_keys=True, ensure_ascii=False).encode("utf-8")


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


def _terms_in(pool: dict[str, Any]) -> dict[str, Any]:
    """How much of the widened surface these stored graphs actually carry. Measured."""
    evidence = load_evidence(pool["root"], pool["artifacts"])
    graphs = [side for pair in evidence.pairs for side in (pair.failed, pair.successful)]
    return {
        "graphs": len(graphs),
        "graphs_carrying_terms": sum(1 for graph in graphs if graph.search_terms),
        "reading": (
            "Projected before the field existed, so the widened surface contributes no term "
            "here and any movement in these numbers comes from somewhere else."
        ),
    }


def _comparison(pool: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Every arm against its predecessor value, split by whether W3 changed that arm."""
    predecessor = json.loads(pool["predecessor"].read_text())
    recorded = predecessor[pool["predecessor_arms"]]
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
            "arm_was_changed_in_w3": arm == CHANGED_ARM,
        }
    unchanged_arms_that_moved = sorted(
        arm
        for arm, row in rows.items()
        if not row["reproduced"] and not row["arm_was_changed_in_w3"]
    )
    return {
        "predecessor": str(pool["predecessor"].relative_to(REPOSITORY)),
        "predecessor_sha256": _digest(pool["predecessor"].read_bytes()),
        "per_arm": rows,
        "unchanged_arms_that_moved": unchanged_arms_that_moved,
        "every_unchanged_arm_reproduced": not unchanged_arms_that_moved,
        "the_changed_arm_moved": not rows[CHANGED_ARM]["reproduced"],
    }


def _agreement(pool: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Repeated-order agreement now, beside what the predecessor recorded."""
    predecessor = json.loads(pool["predecessor"].read_text())
    key = pool["predecessor_agreement"]
    before = (
        predecessor.get(key)
        if key
        else predecessor.get("benchmark", {}).get("repeated_ranking_agreement_by_arm")
    )
    now = payload["repeated_ranking_agreement_by_arm"]
    return {
        "recorded": before,
        "measured": now,
        "arms_that_do_not_reproduce_their_own_ranking": sorted(
            arm for arm, stable in now.items() if not stable
        ),
        "every_arm_reproduces_its_own_ranking": all(now.values()),
        "the_changed_arm_now_reproduces_itself": bool(now[CHANGED_ARM]),
        "the_changed_arm_did_not_before": (before is not None and before.get(CHANGED_ARM) is False),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()
    model = arguments.model.resolve()

    before = {pool["name"]: fingerprint(pool["artifacts"]) for pool in POOLS}
    pools: dict[str, Any] = {}
    for pool in POOLS:
        payload = _benchmark(pool, model)
        pools[pool["name"]] = {
            "root": str(pool["root"].relative_to(REPOSITORY)),
            "artifact_root": str(pool["artifacts"]),
            "access": "read_only",
            "frozen_in": pool["frozen_in"],
            "query_set": {
                **payload["query_manifest"],
                "path": str(pool["queries"].relative_to(REPOSITORY)),
            },
            "graph_set": payload["graph_set"],
            "resource_policy": payload["resource_policy"],
            "model": payload["model"],
            "benchmark_content_hash": payload["content_hash"],
            "benchmark_schema_version": payload["schema_version"],
            "widened_surface": _terms_in(pool),
            "arms": {arm: payload["arms"][arm] for arm in ARM_ORDER},
            "repeated_ranking_agreement": _agreement(pool, payload),
            "against_the_predecessor": _comparison(pool, payload),
        }
    after = {pool["name"]: fingerprint(pool["artifacts"]) for pool in POOLS}

    held = all(
        row["against_the_predecessor"]["every_unchanged_arm_reproduced"]
        and row["repeated_ranking_agreement"]["every_arm_reproduces_its_own_ranking"]
        for row in pools.values()
    )
    evidence = {
        "schema_version": 1,
        "sprint": "21D4",
        "wave": "W3",
        "items": ["S21D4-042"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _digest(PRE_REGISTRATION.read_bytes()),
        "surface_sha256": _digest(SURFACE.read_bytes()),
        "ged_decision_sha256": _digest(GED_DECISION.read_bytes()),
        "label": "development_only",
        "gating": False,
        "purpose": (
            "Measure the widened searchable surface and the decided bounded-GED comparator on "
            "two query sets whose answers are already published. It closes no gate: D1 "
            "condition 15 and Gate L2 condition 24 are decided only by the D4 unseen-task "
            "holdout, which this command does not read."
        ),
        "changed_arm": CHANGED_ARM,
        "ged_iteration_budget": GED_ITERATION_BUDGET,
        "expectation_declared_before_the_run": (
            "Every arm except the one whose comparator W3 decided reproduces its predecessor "
            "value exactly. The changed arm may move, and must now reproduce its own ranking "
            "across two passes."
        ),
        "pools": pools,
        "every_unchanged_arm_reproduced": all(
            row["against_the_predecessor"]["every_unchanged_arm_reproduced"]
            for row in pools.values()
        ),
        "every_arm_reproduces_its_own_ranking": all(
            row["repeated_ranking_agreement"]["every_arm_reproduces_its_own_ranking"]
            for row in pools.values()
        ),
        "store_writes": {
            "fingerprints_before": before,
            "fingerprints_after": after,
            "unchanged": before == after,
        },
        "d4_retrieval_pool_read": False,
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
        agreement = row["repeated_ranking_agreement"]
        comparison = row["against_the_predecessor"]
        print(f"  {name}")
        print(
            f"    graphs carrying terms: {row['widened_surface']['graphs_carrying_terms']}"
            f" of {row['widened_surface']['graphs']}"
        )
        print(f"    unchanged arms that moved: {comparison['unchanged_arms_that_moved'] or 'none'}")
        print(
            f"    {CHANGED_ARM}: moved={comparison['the_changed_arm_moved']}, "
            f"reproduces itself={agreement['the_changed_arm_now_reproduces_itself']} "
            f"(before: {(agreement['recorded'] or {}).get(CHANGED_ARM)})"
        )
    print(f"  store writes: {0 if before == after else -1}")
    print(f"  seal {sealed['integrity_content_hash']}")
    return 0 if held and before == after else 1


if __name__ == "__main__":
    raise SystemExit(main())
