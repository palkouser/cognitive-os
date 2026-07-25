"""Measure the vector retrieval capacity envelope at a chosen corpus size.

Sprint 21.3. Loads synthetic embeddings straight into `memory_embeddings`, builds the
approximate index, and measures exhaustive and approximate retrieval over the same
corpus and the same probes, so recall and latency are comparable rather than merely
adjacent numbers.

The synthetic rows bypass the governed write path deliberately: this measures the
retrieval *engine*, and pushing 10^6 revisions through governance would measure
governance. That is stated as a limitation on every envelope this script produces, so no
reader can mistake it for a governed-throughput result.

    COGOS_DATABASE_ADMIN_URL=... scripts/memory_ann_baseline.py --vectors 100000

Requires an admin URL: it creates, populates, and drops a scratch table.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import text

from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import RetrievalCapacityEnvelope
from cognitive_os.domain.memory import MemoryRetrievalMode
from cognitive_os.infrastructure.memory.postgres.tables import approximate_index_name
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

#: A scratch table shaped like `memory_embeddings`' vector columns only. Measuring
#: against a copy keeps a million synthetic rows out of the governed table, where they
#: would violate the embedding/revision foreign key anyway.
SCRATCH_TABLE = "memory_ann_baseline_scratch"


def _vector_literal(rnd: random.Random, dimension: int) -> str:
    return "[" + ",".join(f"{rnd.gauss(0.0, 1.0):.6f}" for _ in range(dimension)) + "]"


def _clustered_literal(
    rnd: random.Random, dimension: int, centres: Sequence[Sequence[float]], spread: float
) -> str:
    """A vector drawn near one of `centres`.

    Independent Gaussian noise in 768 dimensions is the adversarial case for graph-based
    approximate search: every point is nearly equidistant from every other, so there is
    no neighbourhood structure for the graph to exploit and recall collapses. Real
    embeddings are strongly clustered, so a run over uniform noise measures a floor and
    not the behaviour a deployment would see. Both are worth measuring; neither alone is
    the answer, which is why the distribution is recorded on every envelope.
    """
    centre = centres[rnd.randrange(len(centres))]
    return (
        "["
        + ",".join(f"{centre[axis] + rnd.gauss(0.0, spread):.6f}" for axis in range(dimension))
        + "]"
    )


def _baseline_index_name(dimension: int) -> str:
    """The scratch index, named after the real one so a drift in either is visible."""
    return f"{approximate_index_name(dimension)}_baseline"


async def _load(
    engine: object, *, vectors: int, dimension: int, batch: int, clusters: int, spread: float
) -> Sequence[Sequence[float]]:
    """Populate the scratch table, returning the cluster centres probes should reuse."""
    rnd = random.Random(20_250_321)
    centres = [[rnd.gauss(0.0, 1.0) for _ in range(dimension)] for _ in range(max(clusters, 0))]
    async with engine.begin() as connection:  # type: ignore[attr-defined]
        await connection.execute(text(f"DROP TABLE IF EXISTS cognitive_os.{SCRATCH_TABLE}"))
        await connection.execute(
            text(
                f"CREATE TABLE cognitive_os.{SCRATCH_TABLE} ("
                "embedding_id bigserial PRIMARY KEY, dimension int NOT NULL, "
                "embedding vector NOT NULL)"
            )
        )
    loaded = 0
    while loaded < vectors:
        count = min(batch, vectors - loaded)
        rows = ",".join(
            "({dim}, '{vec}')".format(
                dim=dimension,
                vec=(
                    _clustered_literal(rnd, dimension, centres, spread)
                    if centres
                    else _vector_literal(rnd, dimension)
                ),
            )
            for _ in range(count)
        )
        async with engine.begin() as connection:  # type: ignore[attr-defined]
            await connection.execute(
                text(
                    f"INSERT INTO cognitive_os.{SCRATCH_TABLE} (dimension, embedding) VALUES {rows}"
                )
            )
        loaded += count
    return centres


async def _build_index(engine: object, *, dimension: int) -> tuple[float, int]:
    name = _baseline_index_name(dimension)
    started = perf_counter()
    async with engine.begin() as connection:  # type: ignore[attr-defined]
        await connection.execute(
            text(
                f"CREATE INDEX {name} ON cognitive_os.{SCRATCH_TABLE} "
                f"USING hnsw ((embedding::vector({dimension})) vector_cosine_ops) "
                f"WHERE dimension = {dimension}"
            )
        )
        await connection.execute(text(f"ANALYZE cognitive_os.{SCRATCH_TABLE}"))
    elapsed = perf_counter() - started
    async with engine.connect() as connection:  # type: ignore[attr-defined]
        size = int(
            await connection.scalar(
                text("SELECT pg_relation_size(CAST(:name AS regclass))"),
                {"name": f"cognitive_os.{name}"},
            )
            or 0
        )
    return elapsed, size


async def _measure(
    engine: object,
    *,
    dimension: int,
    vectors: int,
    queries: int,
    result_limit: int,
    candidate_limit: int,
    ef_search: int,
    index_build_seconds: float,
    index_size_bytes: int,
    centres: Sequence[Sequence[float]],
    spread: float,
) -> list[RetrievalCapacityEnvelope]:
    """Run both modes over the same probes, against the scratch table.

    The SQL mirrors `PostgresMemoryRepository._vector_distance` exactly: the exhaustive
    form compares the undimensioned column, the approximate form casts to the indexed
    dimension. If those two shapes ever diverge from the repository, the integration
    test that asserts the repository's own plans is the one that fails.

    This measures the index. `cognitive_os.learning.capacity.measure_capacity` measures
    the same thing through `MemoryRepositoryPort`, including the Python re-scoring and
    the access audit — the two answer different questions and neither substitutes.
    """
    rnd = random.Random(777)
    # Probes are drawn from the same distribution as the corpus. A uniform probe against a
    # clustered corpus would sit in empty space, where nothing is a near neighbour.
    probes = [
        _clustered_literal(rnd, dimension, centres, spread)
        if centres
        else _vector_literal(rnd, dimension)
        for _ in range(queries)
    ]
    # Same rule as the repository: an ef_search below the LIMIT truncates silently.
    ef_search = max(ef_search, candidate_limit)
    limitations = (
        "synthetic vectors loaded outside the governed write path: this measures the "
        "retrieval engine, not governed ingestion throughput",
        (
            f"corpus drawn from {len(centres)} gaussian clusters with spread {spread}, "
            "which approximates the neighbourhood structure real embeddings have"
        )
        if centres
        else (
            "corpus drawn from independent gaussian noise, which has no neighbourhood "
            "structure: this is the adversarial floor for graph-based approximate search, "
            "not the behaviour a deployment with real embeddings would see"
        ),
    )

    exact_latencies: list[float] = []
    approx_latencies: list[float] = []
    overlaps: list[float] = []
    index_confirmed = False
    async with engine.connect() as connection:  # type: ignore[attr-defined]
        for probe in probes:
            exact_sql = text(
                f"SELECT embedding_id FROM cognitive_os.{SCRATCH_TABLE} "
                f"WHERE dimension = {dimension} "
                f"ORDER BY embedding <=> '{probe}'::vector LIMIT {candidate_limit}"
            )
            started = perf_counter()
            truth = tuple((await connection.execute(exact_sql)).scalars())[:result_limit]
            exact_latencies.append((perf_counter() - started) * 1_000)

            await connection.execute(text(f"SET LOCAL hnsw.ef_search = {ef_search}"))
            approx_sql = text(
                f"SELECT embedding_id FROM cognitive_os.{SCRATCH_TABLE} "
                f"WHERE dimension = {dimension} "
                f"ORDER BY (embedding::vector({dimension})) <=> '{probe}'::vector "
                f"LIMIT {candidate_limit}"
            )
            started = perf_counter()
            found = tuple((await connection.execute(approx_sql)).scalars())[:result_limit]
            approx_latencies.append((perf_counter() - started) * 1_000)
            if truth:
                overlaps.append(len(set(found) & set(truth)) / len(truth))
            if not index_confirmed:
                # Read the plan back rather than trust that the index was used. A
                # cost-based planner declines it on a small corpus, and the recall then
                # comes out at 1 because the query was exhaustive — a clean-looking
                # number that says nothing about the index.
                plan = "\n".join(
                    (
                        await connection.execute(text(f"EXPLAIN (COSTS OFF) {approx_sql.text}"))
                    ).scalars()
                )
                index_confirmed = f"Index Scan using {_baseline_index_name(dimension)}" in plan

    def p95(values: list[float]) -> Decimal:
        raw = quantiles(values, n=20, method="inclusive")[18] if len(values) > 1 else values[0]
        return Decimal(f"{raw:.3f}")

    def p50(values: list[float]) -> Decimal:
        return Decimal(f"{median(values):.3f}")

    distribution = f"clusters{len(centres)}" if centres else "uniform"
    shared = {
        "embedding_dimension": dimension,
        "corpus_vector_count": vectors,
        "queries_measured": queries,
        "result_limit": result_limit,
        "candidate_limit": candidate_limit,
        "created_at": utc_now(),
    }
    return [
        RetrievalCapacityEnvelope(
            envelope_id=uuid5(
                NAMESPACE_URL, f"baseline:exact:{dimension}:{vectors}:{distribution}"
            ),
            retrieval_mode=MemoryRetrievalMode.VECTOR.value,
            latency_p50_ms=p50(exact_latencies),
            latency_p95_ms=p95(exact_latencies),
            limitations=limitations,
            **shared,
        ),
        RetrievalCapacityEnvelope(
            envelope_id=uuid5(
                NAMESPACE_URL, f"baseline:approximate:{dimension}:{vectors}:{distribution}"
            ),
            retrieval_mode=MemoryRetrievalMode.VECTOR_APPROXIMATE.value,
            latency_p50_ms=p50(approx_latencies),
            latency_p95_ms=p95(approx_latencies),
            recall_at_result_limit=Decimal(f"{sum(overlaps) / len(overlaps):.3f}"),
            index_build_seconds=Decimal(f"{index_build_seconds:.3f}"),
            index_size_bytes=index_size_bytes,
            ef_search=ef_search,
            index_scan_confirmed=index_confirmed,
            limitations=(
                limitations
                if index_confirmed
                else (
                    *limitations,
                    f"the planner declined the index at {vectors} vectors and scanned "
                    "exhaustively, so these are not approximate-retrieval numbers",
                )
            ),
            **shared,
        ),
    ]


async def _run(args: argparse.Namespace) -> int:
    url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not url:
        raise SystemExit("COGOS_DATABASE_ADMIN_URL is required: the baseline creates a table")
    # The application default of 30 s is right for queries and far too short for a bulk
    # load and an HNSW build over 10^6 vectors, which take minutes. Deployments must
    # allow for the same when running migration 0013 against a populated table.
    engine = create_postgres_engine(
        url, pool_size=1, max_overflow=0, command_timeout_seconds=args.command_timeout
    )
    try:
        load_started = perf_counter()
        centres = await _load(
            engine,
            vectors=args.vectors,
            dimension=args.dimension,
            batch=args.batch,
            clusters=args.clusters,
            spread=args.cluster_spread,
        )
        load_seconds = perf_counter() - load_started
        build_seconds, index_bytes = await _build_index(engine, dimension=args.dimension)
        envelopes = await _measure(
            engine,
            dimension=args.dimension,
            vectors=args.vectors,
            queries=args.queries,
            result_limit=args.result_limit,
            candidate_limit=args.candidate_limit,
            ef_search=args.ef_search,
            index_build_seconds=build_seconds,
            index_size_bytes=index_bytes,
            centres=centres,
            spread=args.cluster_spread,
        )
    finally:
        if not args.keep:
            async with engine.begin() as connection:
                await connection.execute(text(f"DROP TABLE IF EXISTS cognitive_os.{SCRATCH_TABLE}"))
        await engine.dispose()

    report = {
        "load_seconds": round(load_seconds, 3),
        "index_build_seconds": round(build_seconds, 3),
        "index_size_bytes": index_bytes,
        "envelopes": [json.loads(envelope.canonical_json()) for envelope in envelopes],
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=int, default=100_000)
    parser.add_argument("--dimension", type=int, default=768)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--result-limit", type=int, default=20)
    parser.add_argument("--candidate-limit", type=int, default=1_000)
    parser.add_argument("--ef-search", type=int, default=200)
    parser.add_argument("--batch", type=int, default=1_000)
    parser.add_argument(
        "--clusters",
        type=int,
        default=64,
        help="gaussian cluster count; 0 draws independent noise, the adversarial floor",
    )
    parser.add_argument("--cluster-spread", type=float, default=0.35)
    parser.add_argument("--command-timeout", type=float, default=3_600.0)
    parser.add_argument("--keep", action="store_true", help="leave the scratch table in place")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.vectors < 1 or args.queries < 1:
        raise SystemExit("--vectors and --queries must be positive")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
