#!/usr/bin/env python
"""S21D3-042: replay the frozen D1 eighty-query set and reconcile it with the record.

Development only. Nothing here closes a gate, selects a weight or touches the new holdout:
it exists so that the repaired benchmark surface (S21D3-040) and the fixed RRF arm
(S21D3-041) are *measured* on a query set whose answers are already published, before either
is pointed at evidence nobody has seen.

The replay runs the operator command rather than importing its internals, because the thing
under test is the command an operator would run. It then checks the three arms whose values
S21D3-001 fixed as authoritative, and reports RRF beside them without tuning it — the fusion
constant, the weights and the two input arms were frozen in W0.

    scripts/retrieval_development_d3.py --model <frozen-minilm>
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

EVIDENCE = REPOSITORY / "docs" / "sprints" / "sprint-21" / "evidence"
PRE_REGISTRATION = EVIDENCE / "sprint-21d3-pre-registration.json"
RECONCILIATION = EVIDENCE / "sprint-21d3-d2-reconciliation.json"
OUTPUT = EVIDENCE / "sprint-21d3-d1-retrieval-development.json"

D1_ROOT = EVIDENCE / "sprint-21d1-emg-root.json"
D1_QUERIES = EVIDENCE / "sprint-21d1-graph-queries.json"
D1_ARTIFACTS = Path("/home/palkouser/projekt/cognitive-os-data/artifacts-s21d1")

#: The comparators, then the one candidate. `no_memory` and `exact_signature` return nothing
#: on this set by construction — every query excludes its own group — and are still measured,
#: because a floor that is only asserted is not a floor.
ARM_ORDER = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)

#: S21D3-001 named the authoritative development values by JSON pointer into the D2
#: diagnostic. Reproduction is checked against those, not against the D2 narrative.
AUTHORITATIVE = {
    "lexical": "lexical",
    "minilm_vector": "minilm_vector",
    "minilm_shortlist_plus_bounded_ged": "width_20_bounded_graph",
}


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _write(path: Path, value: dict[str, Any]) -> None:
    sealed = dict(value)
    sealed["integrity_content_hash"] = _hash(_canonical_bytes(value).decode())
    path.write_text(
        json.dumps(sealed, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _benchmark(model: Path) -> dict[str, Any]:
    """The operator command, run exactly as an operator would run it."""
    done = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY / "scripts" / "experience.py"),
            "graph-benchmark",
            "--graph-root",
            str(D1_ROOT),
            "--artifact-root",
            str(D1_ARTIFACTS),
            "--queries",
            str(D1_QUERIES),
            "--model",
            str(model),
            "--policy-hash",
            GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
        ],
        capture_output=True,
        text=True,
        cwd=REPOSITORY,
    )
    if done.returncode != 0:
        raise SystemExit(f"graph-benchmark refused:\n{done.stderr}")
    return json.loads(done.stdout)


def _reproduction(payload: dict[str, Any]) -> dict[str, Any]:
    """Every authoritative value against the one this replay produced.

    "Within deterministic precision" is only a meaningful bar for an arm that *is*
    deterministic, so each row carries whether the arm reproduced its own ranking across the
    two passes of this very run. An arm that cannot reproduce itself on one host in one
    minute was never going to reproduce a number recorded on another host in July.
    """
    canonical = json.loads(RECONCILIATION.read_text())["retrieval"]["canonical_development_values"]
    stable = payload["repeated_ranking_agreement_by_arm"]
    rows: dict[str, Any] = {}
    for arm, name in AUTHORITATIVE.items():
        recorded, measured = canonical[name], payload["arms"][arm]
        values = {
            "recall_at_5": {
                "recorded": recorded["recall_at_5"],
                "measured": measured["top_5_recall"],
            },
            "mrr_at_10": {"recorded": recorded["mrr_at_10"], "measured": measured["mrr_at_10"]},
            "ndcg_at_10": {"recorded": recorded["ndcg_at_10"], "measured": measured["ndcg_at_10"]},
            "timeouts": {"recorded": recorded["timeouts"], "measured": measured["timeouts"]},
        }
        rows[arm] = {
            **values,
            "deterministic": stable[arm],
            "reproduced": all(item["recorded"] == item["measured"] for item in values.values()),
            "second_pass": payload["repeat_pass_arms"].get(arm),
        }
    return rows


def _complementarity(payload: dict[str, Any]) -> dict[str, Any]:
    """Which queries each arm answers, and which the fusion answers that its inputs do not.

    Complementarity is the only honest reason to fuse two arms at all: if the vector arm
    already answers every query the lexical arm does, the fusion has nothing to add and its
    aggregate can only move by reordering. Counted per query on top-five recall, which is the
    unit Gate L2 condition 24 floors.
    """
    solved = {
        arm: {row["query_id"] for row in rows if row["recall_at_5"]}
        for arm, rows in payload["per_query"].items()
    }
    lexical, vector = solved["lexical"], solved["minilm_vector"]
    fused = solved["reciprocal_rank_fusion"]
    union = lexical | vector
    return {
        "queries_solved": {arm: len(members) for arm, members in sorted(solved.items())},
        "lexical_only": len(lexical - vector),
        "vector_only": len(vector - lexical),
        "both": len(lexical & vector),
        "either_input_arm": len(union),
        "fusion_solved": len(fused),
        "fusion_lost_from_the_union": sorted(union - fused),
        "fusion_gained_over_the_union": sorted(fused - union),
        "reading": (
            "the union of two top-five sets is not a ceiling on the fused top five. A pair "
            "ranked moderately well by both arms — sixth here, seventh there — outscores a "
            "pair one arm ranked first and the other did not rank at all, so the fusion can "
            "surface a query neither input answered inside its own five, and can drop one a "
            "single arm answered alone"
        ),
    }


def _residuals(payload: dict[str, Any]) -> dict[str, Any]:
    """Queries no arm answered, by domain and tier. The part a fusion cannot repair."""
    per_query = payload["per_query"]
    unanswered = {
        row["query_id"]
        for row in per_query["lexical"]
        if not any(
            item["recall_at_5"]
            for arm in per_query
            for item in per_query[arm]
            if item["query_id"] == row["query_id"]
        )
    }
    by_domain: dict[str, int] = {}
    by_tier: dict[str, int] = {}
    for row in per_query["lexical"]:
        if row["query_id"] in unanswered:
            by_domain[row["domain"]] = by_domain.get(row["domain"], 0) + 1
            by_tier[str(row["tier"])] = by_tier.get(str(row["tier"]), 0) + 1
    return {
        "no_arm_found_a_relevant_pair_in_top_five": len(unanswered),
        "by_domain": dict(sorted(by_domain.items())),
        "by_tier": dict(sorted(by_tier.items())),
        "query_ids": sorted(unanswered),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args()

    before = fingerprint(D1_ARTIFACTS)
    payload = _benchmark(arguments.model.resolve())
    after = fingerprint(D1_ARTIFACTS)

    reproduction = _reproduction(payload)
    arms = {arm: payload["arms"][arm] for arm in ARM_ORDER}
    evidence = {
        "schema_version": 1,
        "sprint": "21D3",
        "wave": "W3",
        "items": ["S21D3-042"],
        "recorded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "pre_registration_sha256": _hash(PRE_REGISTRATION.read_text()),
        "label": "development_only",
        "gating": False,
        "purpose": (
            "Measure the repaired benchmark surface and the fixed RRF arm on the frozen "
            "Sprint 21D1 eighty-query development set, whose authoritative values S21D3-001 "
            "already fixed. It closes no gate: D1 condition 15 and Gate L2 condition 24 are "
            "decided only by the new unseen-task holdout."
        ),
        "query_set": {
            **payload["query_manifest"],
            "path": str(D1_QUERIES.relative_to(REPOSITORY)),
            "frozen_in": "Sprint 21D1, before any ranking was produced",
        },
        "graph_set": {
            **payload["graph_set"],
            "root": str(D1_ROOT.relative_to(REPOSITORY)),
            "artifact_root": str(D1_ARTIFACTS),
            "access": "read_only",
        },
        "resource_policy": payload["resource_policy"],
        "model": payload["model"],
        "benchmark_content_hash": payload["content_hash"],
        "benchmark_schema_version": payload["schema_version"],
        "repeated_ranking_agreement": payload["repeated_ranking_agreement"],
        "repeated_ranking_agreement_by_arm": payload["repeated_ranking_agreement_by_arm"],
        "arms": arms,
        "per_query": payload["per_query"],
        "reproduction_of_the_authoritative_values": reproduction,
        "deterministic_arms_reproduced": all(
            row["reproduced"] for row in reproduction.values() if row["deterministic"]
        ),
        "non_deterministic_arms": sorted(
            arm
            for arm, stable in payload["repeated_ranking_agreement_by_arm"].items()
            if not stable
        ),
        "rrf_tuning": {
            "constant": 60,
            "lexical_weight": 1,
            "vector_weight": 1,
            "frozen_by": "sprint-21d3-pre-registration.json, retrieval_v3",
            "sweeps_run": 0,
            "arms_added_or_removed": 0,
        },
        "complementarity": _complementarity(payload),
        "residuals": _residuals(payload),
        "d1_store_writes": 0 if fingerprint(D1_ARTIFACTS) == before else -1,
        "d1_store_fingerprint_unchanged": before == after,
        "d1_or_d2_evidence_files_written": 0,
    }
    _write(arguments.output, evidence)

    print(f"{arguments.output.relative_to(REPOSITORY)}")
    for arm in ARM_ORDER:
        row = arms[arm]
        print(
            f"  {arm:<34} recall@5={row['top_5_recall']:.4f} mrr@10={row['mrr_at_10']:.4f} "
            f"ndcg@10={row['ndcg_at_10']:.4f} p95={row['p95_latency_ms']:.1f}ms "
            f"timeouts={row['timeouts']} cutoffs={row['budget_cutoffs']}"
        )
    print(f"  deterministic arms reproduced: {evidence['deterministic_arms_reproduced']}")
    print(f"  non-deterministic arms: {evidence['non_deterministic_arms'] or 'none'}")
    return 0 if evidence["deterministic_arms_reproduced"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
