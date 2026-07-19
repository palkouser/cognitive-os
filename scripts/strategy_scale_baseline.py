"""Create and measure the isolated Sprint 13 PostgreSQL strategy scale fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import resource
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

from sqlalchemy import text

from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

COUNTS = {
    "strategy_identities": 1_000,
    "strategy_revisions": 5_000,
    "graph_edges": 100_000,
    "selections": 25_000,
    "outcomes": 25_000,
    "accesses": 250_000,
}

QUERIES = {
    "registry_load": """
        SELECT i.strategy_id, i.current_revision, i.current_status, r.content_hash
        FROM cognitive_os.strategy_items i
        JOIN cognitive_os.strategy_revisions r
          ON r.strategy_id=i.strategy_id AND r.revision=i.current_revision
        ORDER BY i.strategy_id LIMIT 1000
    """,
    "candidate_query": """
        SELECT strategy_id, current_revision FROM cognitive_os.strategy_items
        WHERE scope_type='project' AND scope_id='scale' AND current_status='verified'
        ORDER BY canonical_name LIMIT 200
    """,
    "applicability": """
        SELECT strategy_id, revision, content_hash FROM cognitive_os.strategy_revisions
        WHERE problem_class_id='coding.scale' AND status='verified'
        ORDER BY strategy_id LIMIT 200
    """,
    "selection": """
        SELECT i.strategy_id, i.current_revision, count(o.outcome_id) AS outcomes,
               count(o.outcome_id) FILTER (WHERE o.status='accepted') AS accepted
        FROM cognitive_os.strategy_items i
        LEFT JOIN cognitive_os.strategy_outcomes o
          ON o.strategy_id=i.strategy_id AND o.revision=i.current_revision
        WHERE i.problem_class_id='coding.scale' AND i.current_status='verified'
        GROUP BY i.strategy_id, i.current_revision
        ORDER BY accepted DESC, i.strategy_id LIMIT 200
    """,
    "neighbourhood_query": """
        SELECT target_type, target_id, target_revision, edge_type, edge_hash
        FROM cognitive_os.strategy_edges
        WHERE strategy_id='00000000-0000-0013-0001-000000000500'::uuid AND revision=5
        ORDER BY edge_hash LIMIT 200
    """,
    "lineage_query": """
        WITH RECURSIVE lineage(strategy_id, revision, depth) AS (
          VALUES ('00000000-0000-0013-0001-000000001000'::uuid, 5, 0)
          UNION ALL
          SELECT e.target_id::uuid, e.target_revision::integer, l.depth+1
          FROM lineage l JOIN cognitive_os.strategy_edges e
            ON e.strategy_id=l.strategy_id AND e.revision=l.revision
          WHERE e.edge_type='derived_from' AND e.target_type='strategy_revision'
            AND l.depth < 16
        ) SELECT * FROM lineage ORDER BY depth
    """,
    "statistics_rebuild": """
        SELECT strategy_id, revision, cohort_id, count(*) AS executions,
               count(*) FILTER (WHERE status='accepted') AS accepted
        FROM cognitive_os.strategy_outcomes
        GROUP BY strategy_id, revision, cohort_id
        ORDER BY strategy_id, revision LIMIT 1000
    """,
    "graph_snapshot": """
        SELECT e.strategy_id, e.revision,
               jsonb_agg(jsonb_build_object(
                 'edge_type',e.edge_type,'target_type',e.target_type,
                 'target_id',e.target_id,'target_revision',e.target_revision)
                 ORDER BY e.edge_hash) AS edges
        FROM cognitive_os.strategy_edges e
        WHERE e.strategy_id='00000000-0000-0013-0001-000000000500'::uuid AND e.revision=5
        GROUP BY e.strategy_id, e.revision
    """,
}


async def _reset(connection) -> None:
    tables = (
        "strategy_accesses",
        "strategy_statistics",
        "strategy_outcomes",
        "strategy_selections",
        "strategy_edges",
        "strategy_sources",
        "strategy_revisions",
        "strategy_items",
    )
    await connection.execute(
        text("TRUNCATE " + ",".join(f"cognitive_os.{item}" for item in tables) + " CASCADE")
    )


async def _fixture(connection) -> None:
    await _reset(connection)
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_items
            SELECT ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid,
              'scale-strategy-'||lpad(i::text,4,'0'), 'project', 'scale', 'coding.scale',
              5, 'verified', md5('strategy:'||i)||md5('strategy:'||i),
              jsonb_build_object('strategy_id',i), TIMESTAMPTZ '2026-01-01 00:00:00+00'
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_revisions
            SELECT ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid, r,
              CASE WHEN r=1 THEN NULL ELSE r-1 END,
              CASE WHEN r=5 THEN 'verified' ELSE 'draft' END,
              'coding.scale', md5(i::text||':'||r)||md5(i::text||':'||r), 'internal',
              jsonb_build_object('strategy_id',i,'revision',r),
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + r*INTERVAL '1 day'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,5) r
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_sources
            SELECT strategy_id, revision, 0, 'repository', 'scale', revision::text,
                   md5(strategy_id::text||revision)||md5(strategy_id::text||revision)
            FROM cognitive_os.strategy_revisions
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_edges
            SELECT ('00000000-0000-0013-0002-'||
              lpad(((i-1)*100+(r-1)*20+n)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid, r,
              CASE WHEN n=1 AND i>1 THEN 'derived_from' ELSE 'uses_skill' END,
              CASE WHEN n=1 AND i>1 THEN 'strategy_revision' ELSE 'skill_revision' END,
              CASE WHEN n=1 AND i>1
                THEN ('00000000-0000-0013-0001-'||lpad((i-1)::text,12,'0'))
                ELSE 'scale-skill-'||n END,
              CASE WHEN n=1 AND i>1 THEN '5' ELSE '1' END,
              md5('target:'||i||':'||r||':'||n)||md5('target:'||i||':'||r||':'||n),
              1.0, md5('edge:'||i||':'||r||':'||n)||md5('edge:'||i||':'||r||':'||n),
              jsonb_build_object('strategy_id',i,'revision',r,'edge',n),
              TIMESTAMPTZ '2026-01-01 00:00:00+00'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,5) r
            CROSS JOIN generate_series(1,20) n
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_selections
            SELECT ('00000000-0000-0013-0003-'||lpad(((i-1)*25+s)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0004-'||lpad(((i-1)*25+s)::text,12,'0'))::uuid,
              'selected', ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid, 5,
              md5('selection:'||i||':'||s)||md5('selection:'||i||':'||s),
              jsonb_build_object('registry_snapshot',jsonb_build_object('hash',repeat('a',64))),
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + s*INTERVAL '1 second'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,25) s
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_outcomes
            SELECT ('00000000-0000-0013-0005-'||lpad(((i-1)*25+o)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0006-'||lpad(((i-1)*25+o)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0003-'||lpad(((i-1)*25+o)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0004-'||lpad(((i-1)*25+o)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid, 5, 'all',
              'accepted', md5('outcome:'||i||':'||o)||md5('outcome:'||i||':'||o),
              jsonb_build_object('outcome',o),
              TIMESTAMPTZ '2026-01-01 00:01:00+00' + o*INTERVAL '1 second'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,25) o
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.strategy_accesses
            SELECT ('00000000-0000-0013-0007-'||lpad(((i-1)*250+a)::text,12,'0'))::uuid,
              ('00000000-0000-0013-0001-'||lpad(i::text,12,'0'))::uuid, 5,
              'registry_query',
              ('00000000-0000-0013-0004-'||lpad(((i-1)*250+a)::text,12,'0'))::uuid,
              NULL, 'project', 'scale', 'internal',
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + a*INTERVAL '1 second',
              jsonb_build_object('access',a)
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,250) a
            """
        )
    )


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percentile))]


def _timing(values: list[float]) -> dict[str, float | int]:
    return {
        "iterations": len(values),
        "p50_ms": round(median(values), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "maximum_ms": round(max(values), 3),
    }


async def run(output: Path, iterations: int, *, cleanup: bool) -> None:
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.begin() as connection:
            database = str(await connection.scalar(text("SELECT current_database()")))
            if not database.endswith("_test"):
                raise RuntimeError("strategy scale baseline requires an isolated _test database")
            await _fixture(connection)
        measurements = {}
        plans = {}
        async with engine.connect() as connection:
            for name, sql in QUERIES.items():
                elapsed = []
                for _ in range(iterations):
                    started = perf_counter()
                    await connection.execute(text(sql))
                    elapsed.append((perf_counter() - started) * 1000)
                measurements[name] = _timing(elapsed)
                plans[name] = await connection.scalar(text("EXPLAIN (FORMAT JSON) " + sql))
            edge_rows = (
                await connection.execute(
                    text(
                        "SELECT strategy_id::text, target_id FROM cognitive_os.strategy_edges "
                        "ORDER BY edge_id LIMIT 10000"
                    )
                )
            ).all()
            actual = {
                "strategy_identities": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_items")
                ),
                "strategy_revisions": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_revisions")
                ),
                "graph_edges": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_edges")
                ),
                "selections": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_selections")
                ),
                "outcomes": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_outcomes")
                ),
                "accesses": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.strategy_accesses")
                ),
            }
            database_size = int(
                await connection.scalar(text("SELECT pg_database_size(current_database())")) or 0
            )
            relation_size = int(
                await connection.scalar(
                    text(
                        "SELECT sum(pg_total_relation_size(quote_ident(schemaname)||'.'||"
                        "quote_ident(tablename))) FROM pg_tables "
                        "WHERE schemaname='cognitive_os' AND tablename LIKE 'strategy_%'"
                    )
                )
                or 0
            )
            postgres_version = str(await connection.scalar(text("SHOW server_version")))
        core_timings = []
        networkx_timings = []
        for _ in range(iterations):
            started = perf_counter()
            adjacency: dict[str, set[str]] = {}
            for source, target in edge_rows:
                adjacency.setdefault(str(source), set()).add(str(target))
            core_timings.append((perf_counter() - started) * 1000)
            try:
                import networkx as nx
            except ImportError:
                continue
            started = perf_counter()
            graph = nx.DiGraph()
            graph.add_edges_from((str(source), str(target)) for source, target in edge_rows)
            networkx_timings.append((perf_counter() - started) * 1000)
        measurements["core_graph_projection_10000_edges"] = _timing(core_timings)
        measurements["networkx_graph_projection_10000_edges"] = (
            _timing(networkx_timings) if networkx_timings else {"available": False}
        )
        fixture = {key: int(value or 0) for key, value in actual.items()}
        if fixture != COUNTS:
            raise RuntimeError(f"strategy scale fixture count mismatch: {fixture}")
        report = {
            "fixture": fixture,
            "measurements": measurements,
            "plans": plans,
            "environment": {
                "database_size_bytes": database_size,
                "strategy_relation_size_bytes": relation_size,
                "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "machine": platform.machine(),
                "platform": platform.platform(),
                "postgresql": postgres_version,
                "python": sys.version.split()[0],
                "processor": platform.processor() or "unknown",
            },
            "architecture": {
                "postgresql_authoritative": True,
                "graph_database": False,
                "learned_ranking": False,
                "network_required": False,
                "cpu_only": True,
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "fixture": fixture}, sort_keys=True))
    finally:
        if cleanup:
            async with engine.begin() as connection:
                await _reset(connection)
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmarks/sprint-13-scale-baseline.json"),
    )
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    if args.iterations < 5:
        raise ValueError("at least five measurement iterations are required")
    asyncio.run(run(args.output, args.iterations, cleanup=args.cleanup))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
