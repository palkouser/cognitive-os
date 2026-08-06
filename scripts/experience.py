"""Compile and inspect governed experience fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from time import perf_counter

from cognitive_os.domain.experience import ExperienceCandidateStatus
from cognitive_os.experience.compiler import ExperienceCompiler
from cognitive_os.experience.fixtures import INITIAL_FIXTURES, build_fixture
from cognitive_os.experience.governance import (
    append_candidate_status,
    export_candidate,
    validate_candidate,
)
from cognitive_os.verification.experience import verify_compilation


def _json(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))


async def _database_health() -> int:
    from cognitive_os.infrastructure.experience.postgres.health import (
        PostgresExperienceHealthService,
    )
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresExperienceHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


def _graph_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """The two stores a graph command reads. Both must be named; neither is guessed."""
    root = args.graph_root or (
        Path(os.environ["COGOS_GRAPH_ROOT"]) if os.environ.get("COGOS_GRAPH_ROOT") else None
    )
    store = args.artifact_root or (
        Path(os.environ["COGOS_ARTIFACT_ROOT"]) if os.environ.get("COGOS_ARTIFACT_ROOT") else None
    )
    if root is None or store is None:
        raise SystemExit(
            "graph commands need --graph-root and --artifact-root, or COGOS_GRAPH_ROOT and "
            "COGOS_ARTIFACT_ROOT. Neither store is guessed."
        )
    if not root.is_file():
        raise SystemExit(f"graph root manifest {root} is not a file")
    if not store.is_dir():
        raise SystemExit(f"artifact root {store} is not a directory")
    return root, store


def _embedding_provider(model: Path | None) -> object:
    """The frozen local model, or a refusal. It is never substituted with a hashing vector."""
    from cognitive_os.config.memory_config import EmbeddingProviderConfiguration
    from cognitive_os.infrastructure.embeddings import build_embedding_provider, minilm

    if model is None:
        raise SystemExit("--model is required for the vector and graph arms")
    manifest = minilm.read_manifest(model)
    if manifest is None:
        raise SystemExit(f"no usable local embedding model at {model}")
    return build_embedding_provider(
        EmbeddingProviderConfiguration(
            provider_type="sentence_transformers",
            model_id=minilm.MODEL_ID,
            dimension=minilm.DIMENSION,
            local_model_path=model,
            local_model_digest=manifest["tree_digest"],
        )
    )


def _resource_policy(args: argparse.Namespace) -> object:
    """The frozen policy this command measures under, named by hash. §S21D3-040.

    `graph-benchmark` must name one. The class defaults are revision 1, so a benchmark that
    accepted them silently would publish revision-1 numbers under whatever revision the
    surrounding narrative happened to claim — which is exactly what the D2 retrieval
    reconciliation had to unpick afterwards.
    """
    from cognitive_os.domain.experience_graph import (
        FROZEN_GRAPH_RESOURCE_POLICIES,
        GRAPH_RESOURCE_POLICY_REVISION_1,
    )

    if args.policy_hash is None:
        if args.action == "graph-benchmark":
            raise SystemExit(
                "graph-benchmark needs --policy-hash. The frozen policies are:\n"
                + "\n".join(f"    {digest}" for digest in sorted(FROZEN_GRAPH_RESOURCE_POLICIES))
            )
        return GRAPH_RESOURCE_POLICY_REVISION_1
    policy = FROZEN_GRAPH_RESOURCE_POLICIES.get(args.policy_hash)
    if policy is None:
        raise SystemExit(f"{args.policy_hash} names no frozen resource policy")
    return policy


def _graph(args: argparse.Namespace) -> int:
    """The Experience Graph operator commands. Every one of them only reads. §S21D1-063."""
    from cognitive_os.domain.experience_graph import ExperienceGraphQuery
    from cognitive_os.experience import graph_retrieval as retrieval
    from cognitive_os.experience.graph_store import load_evidence

    limits = _resource_policy(args)

    if args.action == "graph-build":
        from cognitive_os.experience.graph_projection import project

        request, sources, profiles = build_fixture(args.fixture)
        result = ExperienceCompiler(sources, profiles).compile(request)
        graph = project(
            result,
            graph_id=f"{args.fixture}:{'accepted' if result.verifier_bundle.passed else 'failed'}",
            domain=args.domain or "coding",
            group=args.fixture,
            task_signature=args.task_signature or args.fixture,
            accepted=result.verifier_bundle.passed,
        )
        print(
            _json(
                {
                    **graph.model_dump(mode="json"),
                    "structural_hash": graph.structural_hash,
                }
            )
        )
        return 0

    root, store = _graph_paths(args)
    evidence = load_evidence(root, store)

    if args.action == "graph-verify":
        payload = {
            "graph_set_id": evidence.graph_set_id,
            "declared_pairs": evidence.declared_pairs,
            "resolved_pairs": len(evidence.pairs),
            "intact": evidence.intact,
            "missing_bytes": list(evidence.missing_bytes),
            "corrupt_bytes": list(evidence.corrupt_bytes),
            "broken_links": list(evidence.broken_links),
            "failed_round_trips": list(evidence.failed_round_trips),
            "legacy_recompilation": len(evidence.legacy_recompilation),
        }
        print(_json(payload))
        return 0 if evidence.intact else 1

    if args.action == "graph-health":
        from cognitive_os.coding.reality_integrity import experience_graph_checks

        checks = experience_graph_checks(evidence)
        payload = {
            "healthy": all(c.ok for c in checks if c.severity == "failure"),
            "checks": [
                {"name": c.name, "ok": c.ok, "severity": c.severity, "detail": c.detail}
                for c in checks
            ],
            "resource_policy": limits.model_dump(mode="json"),
            "writes": 0,
        }
        print(_json(payload))
        return 0 if payload["healthy"] else 1

    candidates = retrieval.candidates_from(evidence.pairs)

    if args.action == "graph-query":
        if not args.query_text:
            raise SystemExit("--query-text is required for graph-query")
        pair = next((p for p in evidence.pairs if p.pair_id == args.pair_id), None)
        if args.pair_id and pair is None:
            raise SystemExit(f"pair {args.pair_id} is not in this graph set")
        query = ExperienceGraphQuery(
            query_id=f"cli:{args.arm}",
            query_text=args.query_text,
            domain=args.domain or (pair.domain if pair else "coding"),
            task_signature=args.task_signature or (pair.task_signature if pair else "cli"),
            excluded_groups=tuple(args.exclude_group) or ((pair.group,) if pair else ("cli",)),
        )
        pool = retrieval.eligible_pool(candidates, query)
        needs_model = args.arm not in {
            retrieval.NO_MEMORY,
            retrieval.LEXICAL,
            retrieval.EXACT_SIGNATURE,
        }
        embed = _embedding_provider(args.model) if needs_model else None
        result = asyncio.run(_run_arm(args.arm, query, pool, pair, limits=limits, embed=embed))
        print(_json(result.model_dump(mode="json")))
        return 0

    if args.action == "graph-benchmark":
        if args.queries is None:
            raise SystemExit("--queries is required for graph-benchmark")
        print(_json(_benchmark(args, evidence, candidates, limits)))
        return 0

    raise AssertionError(args.action)


#: Bumped when the emitted payload's shape changes, so a stored benchmark says which reader
#: understands it. Revision 1 was the two-metric summary S21D3-040 replaced.
BENCHMARK_SCHEMA_VERSION = 2

#: The comparators plus the one S21D3-041 candidate, in the order they are reported.
_ARMS = (
    "no_memory",
    "exact_signature",
    "lexical",
    "minilm_vector",
    "minilm_shortlist_plus_bounded_ged",
    "reciprocal_rank_fusion",
)

#: What can still be measured when no local model is available. Listed rather than derived by
#: sniffing arm names: an arm called `lexical_plus_fusion` would be silently dropped by a
#: substring rule, and the set of model-free arms is three items that rarely change.
_ARMS_WITHOUT_A_MODEL = ("no_memory", "exact_signature", "lexical")


async def _run_arm(
    arm: str,
    query: object,
    pool: object,
    pair: object,
    *,
    limits: object,
    embed: object,
    cache: dict[str, tuple[float, ...]] | None = None,
) -> object:
    """One arm, one query. The single dispatch `graph-query` and `graph-benchmark` share."""
    from cognitive_os.experience import graph_retrieval as retrieval

    if arm == retrieval.NO_MEMORY:
        return retrieval.no_memory(query, limits=limits)
    if arm == retrieval.LEXICAL:
        return retrieval.lexical(query, pool, limits=limits)
    if arm == retrieval.EXACT_SIGNATURE:
        return retrieval.exact_signature(query, pool, limits=limits)
    if embed is None:
        raise SystemExit(f"--model is required for the {arm} arm")
    if arm == retrieval.MINILM_VECTOR:
        return await retrieval.minilm_vector(query, pool, limits=limits, embed=embed, cache=cache)
    if arm == retrieval.RECIPROCAL_RANK_FUSION:
        return await retrieval.reciprocal_rank_fusion(
            query, pool, limits=limits, embed=embed, cache=cache
        )
    if pair is None:
        raise SystemExit("--pair-id is required for the graph arm; it supplies the query graph")
    return await retrieval.bounded_ged(
        query, pool, pair.failed, limits=limits, embed=embed, cache=cache
    )


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int(len(ordered) * fraction))], 3)


def _arm_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    """One arm's complete pre-registered metric set, from its own per-query records."""
    from statistics import fmean

    latencies = [float(row["latency_ms"]) for row in rows]

    def by(key: str) -> dict[str, float]:
        groups: dict[str, list[float]] = {}
        for row in rows:
            groups.setdefault(str(row[key]), []).append(float(row["recall_at_5"]))
        return {name: round(fmean(values), 4) for name, values in sorted(groups.items())}

    return {
        "top_5_recall": round(fmean(float(row["recall_at_5"]) for row in rows), 4),
        "mrr_at_10": round(fmean(float(row["reciprocal_rank"]) for row in rows), 4),
        "ndcg_at_10": round(fmean(float(row["ndcg_at_10"]) for row in rows), 4),
        "coverage": round(fmean(1.0 if row["returned"] else 0.0 for row in rows), 4),
        "p50_latency_ms": _percentile(latencies, 0.5),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "max_latency_ms": round(max(latencies), 3),
        "timeouts": sum(int(row["timed_out"]) for row in rows),
        "budget_cutoffs": sum(int(row["budget_cutoffs"]) for row in rows),
        "mean_candidates_considered": round(
            fmean(float(row["candidates_considered"]) for row in rows), 4
        ),
        "top_5_recall_by_domain": by("domain"),
        "top_5_recall_by_tier": by("tier"),
        "queries_with_no_relevant_pair_in_top_five": sum(
            1 for row in rows if not int(row["recall_at_5"]) and int(row["candidates_considered"])
        ),
    }


def _benchmark(
    args: argparse.Namespace, evidence: object, candidates: object, limits: object
) -> dict[str, object]:
    """Every arm over a frozen query manifest, reported together. Read-only throughout.

    Two identical passes run before any metric is read. The second is not a second
    measurement: it is the only way `repeated_ranking_agreement` can be a measured fact
    rather than an assertion about determinism nobody checked.
    """
    from hashlib import sha256

    from cognitive_os.domain.experience_graph import ExperienceGraphQuery
    from cognitive_os.experience import graph_retrieval as retrieval
    from cognitive_os.infrastructure.embeddings import minilm

    manifest_bytes = args.queries.read_bytes()
    manifest = json.loads(manifest_bytes)
    by_id = {pair.pair_id: pair for pair in evidence.pairs}  # type: ignore[attr-defined]
    embed = _embedding_provider(args.model) if args.model else None
    cache: dict[str, tuple[float, ...]] = {}

    async def one_pass() -> dict[str, list[dict[str, object]]]:
        rows: dict[str, list[dict[str, object]]] = {}
        for record in manifest:
            relevant = set(record["relevant_pair_ids"])
            pair = by_id.get(record["query_id"].removeprefix("q:"))
            if pair is None:
                raise SystemExit(f"query {record['query_id']} names a pair this set does not hold")
            query = ExperienceGraphQuery(
                query_id=record["query_id"],
                query_text=pair.failed.search_text(),
                domain=record["domain"],
                task_signature=record["task_signature"],
                excluded_groups=tuple(record["excluded_groups"]),
            )
            pool = retrieval.eligible_pool(candidates, query)  # type: ignore[arg-type]
            for arm in _ARMS if embed is not None else _ARMS_WITHOUT_A_MODEL:
                started = perf_counter()
                result = await _run_arm(
                    arm, query, pool, pair, limits=limits, embed=embed, cache=cache
                )
                latency = (perf_counter() - started) * 1000
                rows.setdefault(arm, []).append(
                    {
                        "query_id": record["query_id"],
                        "domain": record["domain"],
                        "tier": record.get("relevance_tier", 1),
                        "latency_ms": round(latency, 3),
                        "returned": len(result.entries),
                        "candidates_considered": result.candidates_considered,
                        "timed_out": result.timed_out,
                        "budget_cutoffs": result.budget_cutoffs,
                        "recall_at_5": retrieval.recall_at(result, relevant, k=5),
                        "reciprocal_rank": float(retrieval.reciprocal_rank(result, relevant)),
                        "ndcg_at_10": float(retrieval.ndcg_at(result, relevant, k=10)),
                        "first_relevant_rank": next(
                            (e.rank for e in result.entries if e.pair_id in relevant), 0
                        ),
                        # The ranking itself, so a residual or a complementarity analysis
                        # reads what the arm returned rather than re-running it.
                        "ranked_pair_ids": [e.pair_id for e in result.entries],
                    }
                )
        return rows

    def _orderings(rows: dict[str, list[dict[str, object]]], arm: str) -> list[object]:
        return [row["ranked_pair_ids"] for row in rows[arm]]

    async def both() -> tuple[
        dict[str, list[dict[str, object]]], dict[str, bool], dict[str, list[dict[str, object]]]
    ]:
        rows = await one_pass()
        repeat = await one_pass()
        # Per arm, because one non-deterministic arm must not be reported as though the
        # whole benchmark were unstable — and a stable aggregate must not hide it either.
        agreement = {arm: _orderings(rows, arm) == _orderings(repeat, arm) for arm in rows}
        return rows, agreement, {arm: repeat[arm] for arm in rows if not agreement[arm]}

    rows, agreement, unstable = asyncio.run(both())
    model = minilm.read_manifest(args.model) if args.model else None
    payload: dict[str, object] = {
        "schema_version": BENCHMARK_SCHEMA_VERSION,
        "queries": len(manifest),
        "arms_without_a_model": embed is None,
        "repeated_ranking_agreement": all(agreement.values()),
        "repeated_ranking_agreement_by_arm": dict(sorted(agreement.items())),
        # The second pass's own metrics, for the arms that disagreed with the first. An
        # unstable arm should be reported with the size of its instability, not just a flag.
        "repeat_pass_arms": {
            arm: _arm_metrics(records) for arm, records in sorted(unstable.items())
        },
        "resource_policy": {
            "content_hash": limits.content_hash,  # type: ignore[attr-defined]
            **limits.model_dump(mode="json"),  # type: ignore[attr-defined]
        },
        "query_manifest": {
            "path": str(args.queries),
            "sha256": sha256(manifest_bytes).hexdigest(),
            "queries": len(manifest),
        },
        "graph_set": {
            "graph_set_id": evidence.graph_set_id,  # type: ignore[attr-defined]
            "declared_pairs": evidence.declared_pairs,  # type: ignore[attr-defined]
            "resolved_pairs": len(evidence.pairs),  # type: ignore[attr-defined]
            "intact": evidence.intact,  # type: ignore[attr-defined]
            "root_sha256": sha256(args.graph_root.read_bytes()).hexdigest(),
            "eligible_candidates": len(candidates),  # type: ignore[arg-type]
        },
        "model": (
            None
            if model is None
            else {
                "model_id": minilm.MODEL_ID,
                "revision": minilm.REVISION,
                "dimension": minilm.DIMENSION,
                "tree_digest": model["tree_digest"],
            }
        ),
        "arms": {arm: _arm_metrics(records) for arm, records in sorted(rows.items())},
        "per_query": {arm: records for arm, records in sorted(rows.items())},
    }
    payload["content_hash"] = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def _run(args: argparse.Namespace) -> int:
    request, sources, profiles = build_fixture(args.fixture)
    compiler = ExperienceCompiler(sources, profiles)
    if args.action == "cancel":
        compiler.cancel(request.compilation_id)
        print(_json({"compilation_id": request.compilation_id, "status": "cancelled"}))
        return 0
    result = compiler.compile(request)
    if args.action in {"compile", "resume", "get", "regenerate"}:
        payload = {
            "decision": result.decision.model_dump(mode="json"),
            "manifest": result.manifest.model_dump(mode="json"),
        }
    elif args.action == "snapshot":
        payload = result.snapshot.model_dump(mode="json")
    elif args.action == "sources":
        payload = [item.model_dump(mode="json") for item in result.snapshot.source_refs]
    elif args.action == "timeline":
        payload = result.trajectory.model_dump(mode="json")
    elif args.action == "segments":
        payload = [item.model_dump(mode="json") for item in result.segments]
    elif args.action == "assessments":
        payload = [item.model_dump(mode="json") for item in result.assessments]
    elif args.action == "paths":
        payload = {
            "successful": (
                result.analysis.successful_path.model_dump(mode="json")
                if result.analysis.successful_path
                else None
            ),
            "failed": [item.model_dump(mode="json") for item in result.analysis.failed_branches],
            "recovery": [item.model_dump(mode="json") for item in result.analysis.recovery_paths],
        }
    elif args.action == "corrections":
        payload = [item.model_dump(mode="json") for item in result.analysis.corrections]
    elif args.action == "contributions":
        payload = [item.model_dump(mode="json") for item in result.analysis.contributions]
    elif args.action == "generalizability":
        payload = result.analysis.generalizability.model_dump(mode="json")
    elif args.action == "candidates":
        payload = [item.model_dump(mode="json") for item in result.candidates]
    elif args.action in {
        "candidate",
        "validate-candidate",
        "reject-candidate",
        "export-candidate",
    }:
        candidate = next(
            (item for item in result.candidates if str(item.candidate_id) == args.candidate_id),
            result.candidates[0] if args.candidate_id is None else None,
        )
        if candidate is None:
            raise SystemExit("candidate is unavailable")
        if args.action == "validate-candidate":
            payload = {
                "candidate_id": str(candidate.candidate_id),
                "errors": validate_candidate(candidate, result.snapshot.content_hash),
            }
        elif args.action == "reject-candidate":
            payload = append_candidate_status(
                candidate,
                (),
                ExperienceCandidateStatus.REJECTED,
                actor_id=args.actor_id,
                reason=args.reason,
            ).model_dump(mode="json")
        elif args.action == "export-candidate":
            if args.output is None:
                raise SystemExit("--output is required for candidate export")
            package = export_candidate(candidate)
            args.output.mkdir(parents=True, exist_ok=True)
            for name, data in package.items():
                (args.output / name).write_bytes(data)
            payload = {
                "candidate_id": str(candidate.candidate_id),
                "files": sorted(package),
            }
        else:
            payload = candidate.model_dump(mode="json")
    elif args.action == "manifest":
        payload = result.manifest.model_dump(mode="json")
    elif args.action == "verify":
        payload = {
            "passed": result.verifier_bundle.passed and not verify_compilation(result),
            "bundle": result.verifier_bundle.model_dump(mode="json"),
            "failures": verify_compilation(result),
        }
    elif args.action == "health":
        payload = {
            "healthy": not verify_compilation(result),
            "fixtures": len(INITIAL_FIXTURES),
            "source_registry_hash": sources.snapshot_hash(),
            "profile_registry_hash": profiles.snapshot_hash(),
            "mandatory_verifiers": len(result.verifier_bundle.results),
            "destination_writes": 0,
            "automatic_promotions": 0,
        }
    else:
        raise AssertionError(args.action)
    print(_json(payload))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "compile",
            "resume",
            "cancel",
            "get",
            "snapshot",
            "sources",
            "timeline",
            "segments",
            "assessments",
            "paths",
            "corrections",
            "contributions",
            "generalizability",
            "candidates",
            "candidate",
            "validate-candidate",
            "reject-candidate",
            "export-candidate",
            "manifest",
            "verify",
            "regenerate",
            "health",
            "graph-build",
            "graph-verify",
            "graph-query",
            "graph-benchmark",
            "graph-health",
        ),
    )
    parser.add_argument("--fixture", choices=INITIAL_FIXTURES, default="direct-success")
    parser.add_argument("--candidate-id")
    parser.add_argument("--actor-id", default="operator")
    parser.add_argument("--reason", default="operator decision")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--graph-root", type=Path, help="the graph set's root manifest")
    parser.add_argument("--artifact-root", type=Path, help="the content-addressed store to read")
    parser.add_argument("--model", type=Path, help="the frozen local embedding model directory")
    parser.add_argument("--queries", type=Path, help="a frozen query manifest for the benchmark")
    parser.add_argument(
        "--policy-hash",
        help="the frozen resource policy this measurement runs under; required by graph-benchmark",
    )
    parser.add_argument("--query-text")
    parser.add_argument("--pair-id")
    parser.add_argument("--domain")
    parser.add_argument("--task-signature")
    parser.add_argument("--exclude-group", action="append", default=[])
    parser.add_argument(
        "--arm",
        default="lexical",
        choices=_ARMS,
    )
    args = parser.parse_args()
    if args.action == "health" and args.database:
        return asyncio.run(_database_health())
    if args.action.startswith("graph-"):
        return _graph(args)
    return _run(args)


if __name__ == "__main__":
    raise SystemExit(main())
