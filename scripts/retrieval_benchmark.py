#!/usr/bin/env python3
"""Measure retrieval quality and storage cost on the frozen benchmark. §S21C3-054, §S21C3-055.

    scripts/retrieval_benchmark.py --model /abs/path/to/all-MiniLM-L6-v2 \
        --evidence docs/sprints/sprint-21/evidence/sprint-21c3-w5-retrieval.json

Three arms answer the same sixty queries over the same sixty records, through the same Memory
Plane and the same exact-cosine query path:

* **lexical** — the plane's own text mode, no embedding at all;
* **deterministic** — the hashing provider, at 384 dimensions, labelled non-production;
* **minilm** — the frozen local model.

The deterministic arm is in the comparison because §4.15 asks MiniLM to beat it by a stated
margin, and it is labelled everywhere it appears because a hashing vector that reached a
production evidence file under a model's name would be a lie the file could not detect.

The precision comparison then loads the *same* MiniLM vectors into temporary `vector(384)` and
`halfvec(384)` tables and asks the same questions of both. Temporary, because §4.16's decision
comes after the measurement: creating migration `0016` in order to benchmark it would be
deciding first and measuring afterwards.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import resource
import statistics
import sys
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import text as sql
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderPort,
)
from cognitive_os.coding.reality_retrieval import (
    BENCHMARK_PROFILE_ID,
    BenchmarkCase,
    RetrievalBenchmark,
    build_benchmark,
    cross_group_leakage,
    kind_counts,
)
from cognitive_os.domain.memory import (
    MemoryCreator,
    MemoryCreatorType,
    MemoryMetadataFilter,
    MemoryProvenanceBundle,
    MemoryQuery,
    MemoryQueryBudget,
    MemoryRetrievalMode,
    MemoryScope,
    MemoryScopeType,
    MemorySensitivity,
    MemorySourceIdentity,
    MemorySourceRef,
    MemorySourceType,
    MemoryTextQuery,
    MemoryType,
    MemoryVectorQuery,
    MemoryWriteRequest,
    ObservationMemoryContent,
)
from cognitive_os.infrastructure.embeddings import (
    DeterministicEmbeddingProvider,
    LocalSentenceTransformerProvider,
    minilm,
)
from cognitive_os.infrastructure.memory.postgres.repository import (
    PostgresMemoryRepository,
)
from cognitive_os.memory.retrieval import MemoryRetrievalService

BENCHMARK_NAMESPACE = UUID("7d4e0b26-91c5-5f38-a70d-3e14b8c9d502")
BENCHMARK_SCOPE = MemoryScope(
    scope_type=MemoryScopeType.PROJECT, scope_id="cognitive-os-retrieval-benchmark"
)

#: §4.15, verbatim. Not parameters — a threshold a runner can lower is not a threshold.
RECALL_AT_5_MINIMUM = 0.80
MRR_AT_10_MINIMUM = 0.65
DETERMINISTIC_MARGIN = 0.15

#: §4.16.
STORAGE_REDUCTION_MINIMUM = 0.35
QUALITY_LOSS_MAXIMUM = 0.01
LATENCY_REGRESSION_MAXIMUM = 0.10


# ---------------------------------------------------------------- ingest


def _memory_id(document_id: str) -> UUID:
    return uuid5(BENCHMARK_NAMESPACE, document_id)


def _write_request(document: Any) -> MemoryWriteRequest:
    content_hash = sha256(document.text.encode()).hexdigest()
    return MemoryWriteRequest(
        request_id=uuid5(BENCHMARK_NAMESPACE, f"request:{document.document_id}"),
        idempotency_key=sha256(
            f"{BENCHMARK_PROFILE_ID}:{document.document_id}".encode()
        ).hexdigest(),
        memory_id=_memory_id(document.document_id),
        memory_type=MemoryType.OBSERVATION,
        scope=BENCHMARK_SCOPE,
        title=document.title,
        content=ObservationMemoryContent(
            observation=document.text,
            evidence_summary=f"{BENCHMARK_PROFILE_ID} record from group {document.group}",
        ),
        confidence=1.0,
        salience=0.5,
        sensitivity=MemorySensitivity.PUBLIC,
        provenance=MemoryProvenanceBundle(
            sources=(
                MemorySourceRef(
                    identity=MemorySourceIdentity(
                        source_type=MemorySourceType.CODING_TRAJECTORY,
                        source_id=uuid5(BENCHMARK_NAMESPACE, f"source:{document.document_id}"),
                        content_hash=content_hash,
                    ),
                    source_hash=content_hash,
                ),
            )
        ),
        actor=MemoryCreator(
            creator_type=MemoryCreatorType.APPROVED_INTERNAL_SERVICE,
            creator_id="retrieval-benchmark",
        ),
    )


async def _ingest(
    repository: PostgresMemoryRepository, benchmark: RetrievalBenchmark
) -> dict[str, tuple[int, str]]:
    """Write every record through the Memory Plane. Re-running is a no-op, by idempotency key."""
    written = {}
    for document in benchmark.documents:
        _, revision = await repository.create_memory(_write_request(document))
        written[document.document_id] = (revision.revision, revision.content_hash)
    return written


async def _embed_all(
    repository: PostgresMemoryRepository,
    benchmark: RetrievalBenchmark,
    revisions: dict[str, tuple[int, str]],
    provider: EmbeddingProviderPort,
) -> tuple[float, dict[str, tuple[float, ...]]]:
    """Embed and store every record. Returns wall time and the vectors, for §4.16."""
    from cognitive_os.memory.embeddings import MemoryEmbeddingService

    service = MemoryEmbeddingService(repository, {provider.identity.provider_id: provider})
    vectors: dict[str, tuple[float, ...]] = {}
    started = perf_counter()
    for document in benchmark.documents:
        revision, content_hash = revisions[document.document_id]
        record = await service.create(
            _memory_id(document.document_id),
            revision,
            content_hash,
            provider.identity.provider_id,
        )
        vectors[document.document_id] = record.vector
    return perf_counter() - started, vectors


# ---------------------------------------------------------------- metrics


def _ndcg(ranked: list[str], relevant: set[str], k: int) -> float:
    from math import log2

    gain = sum(1.0 / log2(index + 2) for index, doc in enumerate(ranked[:k]) if doc in relevant)
    ideal = sum(1.0 / log2(index + 2) for index in range(min(len(relevant), k)))
    return gain / ideal if ideal else 0.0


def _case_metrics(ranked: list[str], case: BenchmarkCase) -> dict[str, float]:
    relevant = set(case.relevant)
    first = next((index + 1 for index, doc in enumerate(ranked[:10]) if doc in relevant), 0)
    return {
        "recall@5": len(relevant & set(ranked[:5])) / len(relevant),
        "recall@10": len(relevant & set(ranked[:10])) / len(relevant),
        "mrr@10": 1.0 / first if first else 0.0,
        "ndcg@10": _ndcg(ranked, relevant, 10),
    }


def _aggregate(per_case: dict[str, dict[str, float]], cases: tuple[BenchmarkCase, ...]) -> dict:
    families = sorted({case.family for case in cases})
    keys = ("recall@5", "recall@10", "mrr@10", "ndcg@10")

    def mean(selected: list[dict[str, float]], key: str) -> float:
        return round(statistics.fmean(item[key] for item in selected), 4) if selected else 0.0

    everything = list(per_case.values())
    by_family = {}
    for family in families:
        selected = [per_case[case.case_id] for case in cases if case.family == family]
        by_family[family] = {key: mean(selected, key) for key in keys}
    by_kind = {}
    for kind in sorted({case.kind for case in cases}):
        selected = [per_case[case.case_id] for case in cases if case.kind == kind]
        by_kind[kind] = {key: mean(selected, key) for key in keys}
    return {
        "aggregate": {key: mean(everything, key) for key in keys},
        "by_family": by_family,
        "by_kind": by_kind,
    }


# ---------------------------------------------------------------- arms


async def _run_arm(
    repository: PostgresMemoryRepository,
    benchmark: RetrievalBenchmark,
    *,
    provider: EmbeddingProviderPort | None,
    pass_label: str,
    disjunctive: bool = False,
) -> tuple[dict[str, list[str]], list[float]]:
    """One arm's ranked results and per-query search latencies.

    `pass_label` makes every execution's query id distinct. The Memory Plane derives an access
    record's identity from the query id, so two retrievals sharing one would be the *same*
    access — and the repeat pass this benchmark needs would collide with the pass it is
    checking. An audit log that deduplicated repeated reads would be the wrong audit log.
    """
    service = MemoryRetrievalService(repository, fail_closed_on_audit_error=True)
    rankings: dict[str, list[str]] = {}
    latencies: list[float] = []
    identifiers = {
        _memory_id(document.document_id): document.document_id for document in benchmark.documents
    }
    budget = MemoryQueryBudget(maximum_results=10, maximum_candidates=1000)
    filters = MemoryMetadataFilter(scopes=(BENCHMARK_SCOPE,))
    for case in benchmark.cases:
        if provider is None:
            # `websearch_to_tsquery` conjoins every term, so a fifteen-word question asks for
            # documents containing all fifteen lemmas. The `OR` form is the same plane, the
            # same index and the same ranking — only the caller's query is written the way a
            # search box would write it. Both are measured; the gap between them is the point.
            phrase = " OR ".join(case.text.split()) if disjunctive else case.text
            query = MemoryQuery(
                query_id=uuid5(NAMESPACE_URL, f"{pass_label}:{case.case_id}"),
                mode=MemoryRetrievalMode.TEXT,
                text=MemoryTextQuery(text=phrase),
                filters=filters,
                budget=budget,
            )
        else:
            vector = await provider.embed_query(case.text)
            query = MemoryQuery(
                query_id=uuid5(NAMESPACE_URL, f"{pass_label}:{case.case_id}"),
                mode=MemoryRetrievalMode.VECTOR,
                vector=MemoryVectorQuery(
                    provider_id=provider.identity.provider_id,
                    model_id=provider.identity.model_id,
                    dimension=provider.identity.dimension,
                    vector=vector,
                ),
                filters=filters,
                budget=budget,
            )
        started = perf_counter()
        page, _ = await service.retrieve(query)
        latencies.append((perf_counter() - started) * 1000)
        rankings[case.case_id] = [
            identifiers[result.memory_id]
            for result in page.results
            if result.memory_id in identifiers
        ]
    return rankings, latencies


def _percentiles(latencies: list[float]) -> dict[str, float]:
    ordered = sorted(latencies)
    return {
        "p50_ms": round(ordered[len(ordered) // 2], 3),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
    }


# ---------------------------------------------------------------- §4.16


def _literal(vector: tuple[float, ...]) -> str:
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


async def _precision_comparison(
    engine: Any,
    benchmark: RetrievalBenchmark,
    vectors: dict[str, tuple[float, ...]],
    query_literals: dict[str, str],
) -> dict[str, Any]:
    """Identical vectors, identical queries, two column types. §S21C3-055."""
    async with engine.connect() as connection:
        for kind, column in (("f32", "vector(384)"), ("f16", "halfvec(384)")):
            await connection.execute(
                sql(
                    f"CREATE TEMP TABLE bench_{kind} (document_id text primary key, "
                    f"embedding {column} not null)"
                )
            )
        results: dict[str, Any] = {}
        for kind, cast_to in (("f32", "vector"), ("f16", "halfvec")):
            started = perf_counter()
            for document_id, vector in vectors.items():
                await connection.execute(
                    sql(
                        f"INSERT INTO bench_{kind} (document_id, embedding) "
                        f"VALUES (:document_id, CAST(:embedding AS {cast_to}(384)))"
                    ),
                    {"document_id": document_id, "embedding": _literal(vector)},
                )
            load_seconds = perf_counter() - started
            operator_class = "vector_cosine_ops" if kind == "f32" else "halfvec_cosine_ops"
            index_started = perf_counter()
            await connection.execute(
                sql(
                    f"CREATE INDEX bench_{kind}_hnsw ON bench_{kind} "
                    f"USING hnsw (embedding {operator_class})"
                )
            )
            index_seconds = perf_counter() - index_started
            total_bytes = await connection.scalar(
                sql(f"SELECT pg_total_relation_size('pg_temp.bench_{kind}')")
            )
            table_bytes = await connection.scalar(
                sql(f"SELECT pg_relation_size('pg_temp.bench_{kind}')")
            )
            results[kind] = {
                "load_seconds": round(load_seconds, 4),
                "index_seconds": round(index_seconds, 4),
                "total_bytes": int(total_bytes or 0),
                "table_bytes": int(table_bytes or 0),
            }

        # The same query vectors both column types are asked with, embedded once.
        for kind, cast_to in (("f32", "vector"), ("f16", "halfvec")):
            rankings: dict[str, list[str]] = {}
            latencies: list[float] = []
            for case in benchmark.cases:
                literal = query_literals[case.case_id]
                started = perf_counter()
                rows = (
                    await connection.execute(
                        sql(
                            f"SELECT document_id FROM bench_{kind} "
                            f"ORDER BY embedding <=> CAST(:probe AS {cast_to}(384)) "
                            "LIMIT 10"
                        ),
                        {"probe": literal},
                    )
                ).scalars()
                latencies.append((perf_counter() - started) * 1000)
                rankings[case.case_id] = list(rows)
            per_case = {
                case.case_id: _case_metrics(rankings[case.case_id], case)
                for case in benchmark.cases
            }
            results[kind].update(_aggregate(per_case, benchmark.cases))
            results[kind].update(_percentiles(latencies))
            results[kind]["rankings"] = rankings

        # The whole conversion, not just the ALTER: an HNSW index built for `vector_cosine_ops`
        # refuses the new column type, so a real migration 0016 would have to drop it, convert,
        # and rebuild. Timing only the ALTER would report a migration nobody could run.
        rehearsal_started = perf_counter()
        await connection.execute(sql("DROP INDEX bench_f32_hnsw"))
        await connection.execute(
            sql("ALTER TABLE bench_f32 ALTER COLUMN embedding TYPE halfvec(384)")
        )
        await connection.execute(
            sql(
                "CREATE INDEX bench_f32_hnsw ON bench_f32 USING hnsw (embedding halfvec_cosine_ops)"
            )
        )
        results["migration_rehearsal_seconds"] = round(perf_counter() - rehearsal_started, 4)
        for kind in ("f32", "f16"):
            await connection.execute(sql(f"DROP TABLE bench_{kind}"))
        remaining = await connection.scalar(
            sql(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname LIKE 'pg_temp%' AND c.relname LIKE 'bench_%'"
            )
        )
        results["temporary_objects_remaining"] = int(remaining or 0)

    agreement = sum(
        len(
            set(results["f32"]["rankings"][case.case_id][:10])
            & set(results["f16"]["rankings"][case.case_id][:10])
        )
        for case in benchmark.cases
    ) / (10 * len(benchmark.cases))
    results["top10_agreement"] = round(agreement, 4)
    for kind in ("f32", "f16"):
        del results[kind]["rankings"]
    return results


# ---------------------------------------------------------------- main


async def _main(arguments: argparse.Namespace) -> int:
    run_nonce = uuid4().hex[:12]
    benchmark = build_benchmark()
    leakage = cross_group_leakage(benchmark)
    print(
        f"benchmark {benchmark.manifest_hash} — {len(benchmark.documents)} records, "
        f"{len(benchmark.cases)} queries, kinds {kind_counts(benchmark)}"
    )
    if leakage:
        print(f"refused: cross-group relevance in {leakage}")
        return 1

    status, reason = minilm.health(arguments.model)
    if status is not minilm.ModelHealth.HEALTHY:
        print(f"refused: local model is {status.value}: {reason}")
        return 1
    manifest = minilm.read_manifest(arguments.model) or {}
    local = LocalSentenceTransformerProvider(
        arguments.model,
        model_id=minilm.MODEL_ID,
        model_digest=manifest["tree_digest"],
        dimension=minilm.DIMENSION,
        maximum_batch_size=64,
    )
    hashing = DeterministicEmbeddingProvider(dimension=minilm.DIMENSION)

    engine = create_async_engine(arguments.database_url, pool_pre_ping=True)
    repository = PostgresMemoryRepository(engine)
    evidence: dict[str, Any] = {
        "profile_id": BENCHMARK_PROFILE_ID,
        "benchmark_manifest_hash": benchmark.manifest_hash,
        "documents": len(benchmark.documents),
        "cases": len(benchmark.cases),
        "query_kinds": kind_counts(benchmark),
        "cross_group_leakage": list(leakage),
        "model": {
            "model_id": minilm.MODEL_ID,
            "revision": minilm.REVISION,
            "dimension": minilm.DIMENSION,
            "licence": minilm.LICENCE,
            "tree_digest": manifest.get("tree_digest"),
        },
        "arms": {},
    }
    try:
        revisions = await _ingest(repository, benchmark)
        print(f"ingested {len(revisions)} records through the Memory Plane")

        embed_seconds = {}
        vectors: dict[str, dict[str, tuple[float, ...]]] = {}
        for name, provider in (("deterministic", hashing), ("minilm", local)):
            seconds, produced = await _embed_all(repository, benchmark, revisions, provider)
            embed_seconds[name] = round(seconds, 3)
            vectors[name] = produced
            print(f"embedded 60 records with {name} in {seconds:.2f}s")

        arms: tuple[tuple[str, EmbeddingProviderPort | None, bool], ...] = (
            ("lexical", None, False),
            ("lexical_or", None, True),
            ("deterministic", hashing, False),
            ("minilm", local, False),
        )
        for name, provider, disjunctive in arms:
            rankings, latencies = await _run_arm(
                repository,
                benchmark,
                provider=provider,
                pass_label=f"{run_nonce}:{name}:1",
                disjunctive=disjunctive,
            )
            repeat, _ = await _run_arm(
                repository,
                benchmark,
                provider=provider,
                pass_label=f"{run_nonce}:{name}:2",
                disjunctive=disjunctive,
            )
            per_case = {
                case.case_id: _case_metrics(rankings[case.case_id], case)
                for case in benchmark.cases
            }
            arm: dict[str, Any] = {
                "production": name == "minilm",
                "label": "non-production hashing vector" if name == "deterministic" else name,
                "ingest_seconds": embed_seconds.get(name),
                "stable_across_repeats": rankings == repeat,
                **_aggregate(per_case, benchmark.cases),
                **_percentiles(latencies),
            }
            evidence["arms"][name] = arm
            print(
                f"{name:<14} recall@5={arm['aggregate']['recall@5']:.3f} "
                f"mrr@10={arm['aggregate']['mrr@10']:.3f} "
                f"ndcg@10={arm['aggregate']['ndcg@10']:.3f} "
                f"p95={arm['p95_ms']:.1f}ms stable={arm['stable_across_repeats']}"
            )

        query_literals = {
            case.case_id: _literal(await local.embed_query(case.text)) for case in benchmark.cases
        }
        evidence["precision_comparison"] = await _precision_comparison(
            engine, benchmark, vectors["minilm"], query_literals
        )
    finally:
        await engine.dispose()

    evidence["peak_rss_mib"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    evidence["thresholds"] = _verdict(evidence)
    arguments.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(f"\n{arguments.evidence}")
    for name, passed in evidence["thresholds"]["section_4_15"].items():
        print(f"  4.15 {name}: {'PASS' if passed else 'FAIL'}")
    print(f"  4.16 half precision chosen: {evidence['thresholds']['half_precision_chosen']}")
    return 0 if all(evidence["thresholds"]["section_4_15"].values()) else 1


def _verdict(evidence: dict[str, Any]) -> dict[str, Any]:
    minilm_arm = evidence["arms"]["minilm"]["aggregate"]
    hashing_arm = evidence["arms"]["deterministic"]["aggregate"]
    comparison = evidence["precision_comparison"]
    f32, f16 = comparison["f32"], comparison["f16"]
    reduction = (f32["total_bytes"] - f16["total_bytes"]) / f32["total_bytes"]
    latency_change = (f16["p95_ms"] - f32["p95_ms"]) / f32["p95_ms"] if f32["p95_ms"] else 0.0
    half = {
        "storage_reduction": round(reduction, 4),
        "storage_reduction_at_least_35pct": reduction >= STORAGE_REDUCTION_MINIMUM,
        "recall@10_loss": round(f32["aggregate"]["recall@10"] - f16["aggregate"]["recall@10"], 4),
        "mrr@10_loss": round(f32["aggregate"]["mrr@10"] - f16["aggregate"]["mrr@10"], 4),
        "p95_change": round(latency_change, 4),
        "quality_within_tolerance": (
            f32["aggregate"]["recall@10"] - f16["aggregate"]["recall@10"] <= QUALITY_LOSS_MAXIMUM
            and f32["aggregate"]["mrr@10"] - f16["aggregate"]["mrr@10"] <= QUALITY_LOSS_MAXIMUM
        ),
        "latency_within_tolerance": latency_change <= LATENCY_REGRESSION_MAXIMUM,
    }
    return {
        "section_4_15": {
            "recall@5>=0.80": minilm_arm["recall@5"] >= RECALL_AT_5_MINIMUM,
            "mrr@10>=0.65": minilm_arm["mrr@10"] >= MRR_AT_10_MINIMUM,
            "recall@5 beats deterministic by >=0.15": (
                minilm_arm["recall@5"] - hashing_arm["recall@5"] >= DETERMINISTIC_MARGIN
            ),
            "zero cross-group leakage": not evidence["cross_group_leakage"],
            "rankings stable across repeats": all(
                arm["stable_across_repeats"] for arm in evidence["arms"].values()
            ),
        },
        "recall@5_margin_over_deterministic": round(
            minilm_arm["recall@5"] - hashing_arm["recall@5"], 4
        ),
        "section_4_16": half,
        # §4.16 is explicit that a passing benchmark does not by itself justify migration 0016
        # at C3 corpus size. That judgement is S21C3-056's and lives in the ADR, not here.
        "half_precision_chosen": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True, help="absolute local model directory")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--database-url", default=os.environ.get("COGOS_DATABASE_URL", ""))
    arguments = parser.parse_args()
    if not arguments.database_url:
        print("refused: --database-url or COGOS_DATABASE_URL is required")
        return 2
    arguments.model = arguments.model.resolve()
    return asyncio.run(_main(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
