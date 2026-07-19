"""Create and measure the isolated Sprint 12 PostgreSQL skill scale fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

from sqlalchemy import text

from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

COUNTS = {
    "skill_identities": 1_000,
    "skill_revisions": 5_000,
    "requirements": 20_000,
    "executions": 10_000,
    "execution_steps": 100_000,
    "accesses": 100_000,
}

QUERIES = {
    "registry_load": """
        SELECT i.skill_id, i.current_revision, i.current_status, r.package_hash
        FROM cognitive_os.skill_items i
        JOIN cognitive_os.skill_revisions r
          ON r.skill_id=i.skill_id AND r.revision=i.current_revision
        ORDER BY i.skill_id LIMIT 1000
    """,
    "candidate_query": """
        SELECT skill_id, current_revision FROM cognitive_os.skill_items
        WHERE scope_type='project' AND scope_id='scale' AND current_status='verified'
        ORDER BY skill_id LIMIT 200
    """,
    "requirement_filter": """
        SELECT skill_id, revision FROM cognitive_os.skill_requirements
        WHERE requirement_type='tool' AND capability_id='repository.read'
        ORDER BY skill_id, revision LIMIT 200
    """,
    "context_metadata_retrieval": """
        SELECT skill_id, revision, package_hash FROM cognitive_os.skill_revisions
        WHERE status='verified' AND domains_json @> '["coding"]'::jsonb
        ORDER BY skill_id, revision DESC LIMIT 200
    """,
    "statistics_rebuild": """
        SELECT skill_id, revision, count(*) AS executions,
               count(*) FILTER (WHERE status='accepted') AS accepted
        FROM cognitive_os.skill_executions
        GROUP BY skill_id, revision ORDER BY skill_id, revision LIMIT 1000
    """,
    "health_projection": """
        SELECT count(*) FROM cognitive_os.skill_items i
        LEFT JOIN cognitive_os.skill_revisions r
          ON r.skill_id=i.skill_id AND r.revision=i.current_revision
        WHERE r.skill_id IS NULL OR r.status<>i.current_status
    """,
}


async def _reset(connection) -> None:
    tables = (
        "skill_accesses",
        "skill_statistics",
        "skill_execution_steps",
        "skill_executions",
        "skill_package_artifacts",
        "skill_requirements",
        "skill_sources",
        "skill_revisions",
        "skill_items",
    )
    await connection.execute(
        text("TRUNCATE " + ",".join(f"cognitive_os.{item}" for item in tables) + " CASCADE")
    )


async def _fixture(connection) -> None:
    await _reset(connection)
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.artifact_blobs
              (content_hash,size_bytes,storage_key)
            VALUES (repeat('a',64),0,'scale/skill-package')
            ON CONFLICT DO NOTHING
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.artifacts (artifact_id,content_hash,media_type)
            VALUES ('00000000-0000-0012-0099-000000000001',repeat('a',64),
                    'application/vnd.cognitive-os.skill-package+json')
            ON CONFLICT DO NOTHING
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_items
            SELECT ('00000000-0000-0012-0001-'||lpad(i::text,12,'0'))::uuid,
              'scale-skill-'||i, 'project', 'scale', 5, 'verified',
              md5('skill:'||i)||md5('skill:'||i),
              jsonb_build_object('skill_id',i), TIMESTAMPTZ '2026-01-01 00:00:00+00'
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_revisions
            SELECT ('00000000-0000-0012-0001-'||lpad(i::text,12,'0'))::uuid, r,
              CASE WHEN r=1 THEN NULL ELSE r-1 END,
              CASE WHEN r=5 THEN 'verified' ELSE 'draft' END,
              repeat('a',64), md5(i::text||':'||r)||md5(i::text||':'||r),
              'internal', '["coding"]'::jsonb,
              jsonb_build_object('skill_id',i,'revision',r),
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + r*INTERVAL '1 day'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,5) r
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_package_artifacts
            SELECT skill_id, revision, '00000000-0000-0012-0099-000000000001', repeat('a',64)
            FROM cognitive_os.skill_revisions
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_sources
            SELECT skill_id, revision, 0, 'repository', 'scale', revision::text,
                   md5(skill_id::text||revision)||md5(skill_id::text||revision)
            FROM cognitive_os.skill_revisions
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_requirements
            SELECT skill_id, revision, 'requirement-'||n, 'tool', 'repository.read',
                   jsonb_build_object('required',true)
            FROM cognitive_os.skill_revisions CROSS JOIN generate_series(1,4) n
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_executions
            SELECT ('00000000-0000-0012-0002-'||lpad(((i-1)*10+e)::text,12,'0'))::uuid,
              ('00000000-0000-0012-0001-'||lpad(i::text,12,'0'))::uuid, 5,
              ('00000000-0000-0012-0004-'||lpad(i::text,12,'0'))::uuid,
              'accepted', md5(i::text||':'||e)||md5(i::text||':'||e),
              jsonb_build_object('execution',e),
              TIMESTAMPTZ '2026-01-01 00:00:00+00',
              TIMESTAMPTZ '2026-01-01 00:00:01+00'
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,10) e
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_execution_steps
            SELECT execution_id, s-1, 'step-'||s, 'accepted',
                   jsonb_build_object('step',s)
            FROM cognitive_os.skill_executions CROSS JOIN generate_series(1,10) s
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.skill_accesses
            SELECT ('00000000-0000-0012-0003-'||lpad(((i-1)*100+a)::text,12,'0'))::uuid,
              ('00000000-0000-0012-0001-'||lpad(i::text,12,'0'))::uuid, 5,
              'registry_query',
              ('00000000-0000-0012-0004-'||lpad(i::text,12,'0'))::uuid,
              NULL, 'project', 'scale', 'internal',
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + a*INTERVAL '1 second',
              jsonb_build_object('access',a)
            FROM generate_series(1,1000) i CROSS JOIN generate_series(1,100) a
            """
        )
    )


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percentile))]


async def run(output: Path, iterations: int, *, cleanup: bool) -> None:
    database_url = os.environ.get("COGOS_DATABASE_ADMIN_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_ADMIN_URL is required")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        async with engine.begin() as connection:
            database = str(await connection.scalar(text("SELECT current_database()")))
            if not database.endswith("_test"):
                raise RuntimeError("skill scale baseline requires an isolated _test database")
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
                measurements[name] = {
                    "iterations": iterations,
                    "p50_ms": round(median(elapsed), 3),
                    "p95_ms": round(_percentile(elapsed, 0.95), 3),
                    "maximum_ms": round(max(elapsed), 3),
                }
                plans[name] = await connection.scalar(text("EXPLAIN (FORMAT JSON) " + sql))
            actual = {
                "skill_identities": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_items")
                ),
                "skill_revisions": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_revisions")
                ),
                "requirements": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_requirements")
                ),
                "executions": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_executions")
                ),
                "execution_steps": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_execution_steps")
                ),
                "accesses": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.skill_accesses")
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
                        "WHERE schemaname='cognitive_os' AND tablename LIKE 'skill_%'"
                    )
                )
                or 0
            )
            postgres_version = str(await connection.scalar(text("SHOW server_version")))
        fixture = {key: int(value or 0) for key, value in actual.items()}
        if fixture != COUNTS:
            raise RuntimeError(f"skill scale fixture count mismatch: {fixture}")
        report = {
            "fixture": fixture,
            "measurements": measurements,
            "plans": plans,
            "environment": {
                "database_size_bytes": database_size,
                "skill_relation_size_bytes": relation_size,
                "machine": platform.machine(),
                "platform": platform.platform(),
                "postgresql": postgres_version,
                "python": sys.version.split()[0],
                "processor": platform.processor() or "unknown",
            },
            "architecture": {
                "postgresql_authoritative": True,
                "context_builder_database": False,
                "learned_ranking": False,
                "network_required": False,
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
        default=Path("docs/benchmarks/sprint-12-scale-baseline.json"),
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
