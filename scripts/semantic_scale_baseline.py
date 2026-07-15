"""Create and measure the isolated Sprint 10 PostgreSQL scale fixture."""

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

import networkx as nx
from sqlalchemy import text

from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

COUNTS = {
    "claims": 10_000,
    "claim_revisions": 30_000,
    "evidence": 50_000,
    "relations": 10_000,
    "contradictions": 1_000,
    "wiki_pages": 1_000,
}

QUERIES = {
    "current_claim": """
        SELECT r.content_hash FROM cognitive_os.semantic_claims c
        JOIN cognitive_os.semantic_claim_revisions r
          ON r.claim_id=c.claim_id AND r.revision=c.current_revision
        WHERE c.scope_type='project' AND c.scope_id='scale'
          AND c.canonical_subject_key='project:0000005000'
          AND c.predicate_id='project.python_version'
    """,
    "valid_at": """
        SELECT r.content_hash FROM cognitive_os.semantic_claim_revisions r
        WHERE r.claim_id='00000000-0000-0000-0001-000000005000'
          AND r.valid_from <= TIMESTAMPTZ '2026-07-15 00:00:00+00'
          AND (r.valid_to IS NULL OR r.valid_to > TIMESTAMPTZ '2026-07-15 00:00:00+00')
        ORDER BY r.revision DESC LIMIT 1
    """,
    "known_at": """
        SELECT r.content_hash FROM cognitive_os.semantic_claim_revisions r
        WHERE r.claim_id='00000000-0000-0000-0001-000000005000'
          AND r.recorded_at <= TIMESTAMPTZ '2026-07-16 00:00:00+00'
        ORDER BY r.recorded_at DESC, r.revision DESC LIMIT 1
    """,
    "evidence_lookup": """
        SELECT evidence_id FROM cognitive_os.semantic_claim_evidence
        WHERE claim_id='00000000-0000-0000-0001-000000005000' AND claim_revision=3
        ORDER BY evidence_id
    """,
    "contradiction_lookup": """
        SELECT c.contradiction_id FROM cognitive_os.semantic_contradictions c
        JOIN cognitive_os.semantic_contradiction_claims cc
          ON cc.contradiction_id=c.contradiction_id
          AND cc.contradiction_revision=c.current_revision
        WHERE cc.claim_id='00000000-0000-0000-0001-000000000500'
          AND c.current_status='open'
    """,
    "wiki_regeneration_inputs": """
        SELECT p.page_id, r.content_hash, wc.claim_id, wc.claim_revision
        FROM cognitive_os.wiki_pages p
        JOIN cognitive_os.wiki_page_revisions r
          ON r.page_id=p.page_id AND r.revision=p.current_revision
        JOIN cognitive_os.wiki_page_claims wc
          ON wc.page_id=p.page_id AND wc.page_revision=p.current_revision
        WHERE p.page_id='00000000-0000-0000-0006-000000000500'
    """,
    "bounded_graph_projection": """
        SELECT source_claim_id, source_revision, target_claim_id, target_revision, relation_type
        FROM cognitive_os.semantic_claim_relations
        WHERE source_claim_id BETWEEN
          '00000000-0000-0000-0001-000000004900' AND
          '00000000-0000-0000-0001-000000005100'
        ORDER BY source_claim_id LIMIT 500
    """,
}


async def _reset(connection) -> None:
    tables = (
        "semantic_accesses",
        "wiki_page_claims",
        "wiki_page_revisions",
        "wiki_pages",
        "semantic_contradiction_claims",
        "semantic_contradiction_revisions",
        "semantic_contradictions",
        "semantic_claim_relations",
        "semantic_claim_evidence",
        "semantic_claim_revisions",
        "semantic_claims",
        "semantic_observations",
        "memory_accesses",
        "memory_embeddings",
        "memory_sources",
        "memory_revisions",
        "memory_items",
        "artifacts",
        "artifact_blobs",
        "events",
        "event_streams",
    )
    await connection.execute(
        text("TRUNCATE " + ",".join(f"cognitive_os.{item}" for item in tables) + " CASCADE")
    )


async def _fixture(connection) -> None:
    await _reset(connection)
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_claims
            SELECT ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid,
              md5('claim:'||i)||md5('claim:'||i), 'project', 'scale',
              'project:'||lpad(i::text,10,'0'), 'project.python_version', 3,
              'supported', 'internal', TIMESTAMPTZ '2026-01-01 00:00:00+00',
              'approved_internal_service', 'scale-baseline'
            FROM generate_series(1,10000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_claim_revisions
            SELECT ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid, r,
              CASE WHEN r=1 THEN NULL ELSE r-1 END,
              jsonb_build_object('value_type','literal','literal_kind','version',
                'value','3.'||(10+r),'unit',NULL),
              'Scale claim '||i||' revision '||r,
              CASE WHEN r=1 THEN 'proposed' ELSE 'supported' END,
              jsonb_build_object('extraction_confidence',1,'source_reliability',1,
                'grounding_confidence',1,'evidence_confidence',1,
                'verification_confidence',1,'consistency_confidence',1,
                'overall_confidence',1,'aggregation_policy_version','1'), 1,
              TIMESTAMPTZ '2026-01-01 00:00:00+00' + (r-1)*INTERVAL '30 days', NULL,
              'scale baseline', TIMESTAMPTZ '2026-01-01 00:00:00+00' + r*INTERVAL '1 day',
              'approved_internal_service', 'scale-baseline', repeat('b',64), NULL,
              md5(i::text||':'||r)||md5(i::text||':'||r)
            FROM generate_series(1,10000) i CROSS JOIN generate_series(1,3) r
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_claim_evidence
            SELECT ('00000000-0000-0000-0002-'||lpad(e::text,12,'0'))::uuid,
              ('00000000-0000-0000-0001-'||lpad((((e-1)%10000)+1)::text,12,'0'))::uuid,
              3, 'artifact',
              ('00000000-0000-0000-0003-'||lpad(e::text,12,'0'))::uuid, NULL,
              repeat('c',64), jsonb_build_object('mode','artifact_bytes','start',0,'end',1),
              'supports', 1, TIMESTAMPTZ '2026-07-15 00:00:00+00',
              'approved_internal_service', 'scale-baseline'
            FROM generate_series(1,50000) e
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_claim_relations
            SELECT ('00000000-0000-0000-0004-'||lpad(i::text,12,'0'))::uuid,
              ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid, 3,
              ('00000000-0000-0000-0001-'||lpad(((i%10000)+1)::text,12,'0'))::uuid, 3,
              'related_to', TIMESTAMPTZ '2026-01-01 00:00:00+00', NULL,
              jsonb_build_object('source_type','artifact','source_id',
                '00000000-0000-0000-0003-'||lpad(i::text,12,'0'),
                'revision',NULL,'content_hash',repeat('c',64)),
              TIMESTAMPTZ '2026-07-15 00:00:00+00'
            FROM generate_series(1,10000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_contradictions
            SELECT ('00000000-0000-0000-0005-'||lpad(i::text,12,'0'))::uuid,
              1, 'open', 'high', TIMESTAMPTZ '2026-07-15 00:00:00+00'
            FROM generate_series(1,1000) i;
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_contradiction_revisions
            SELECT ('00000000-0000-0000-0005-'||lpad(i::text,12,'0'))::uuid,
              1, NULL, 'open', 'high', '[]'::jsonb, 'scale conflict', NULL,
              TIMESTAMPTZ '2026-07-15 00:00:00+00', repeat('d',64)
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.semantic_contradiction_claims
            SELECT ('00000000-0000-0000-0005-'||lpad(i::text,12,'0'))::uuid, 1,
              ('00000000-0000-0000-0001-'||lpad(c::text,12,'0'))::uuid, 3
            FROM generate_series(1,1000) i
            CROSS JOIN LATERAL (VALUES (i), (i+1000)) claims(c)
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.wiki_pages
            SELECT ('00000000-0000-0000-0006-'||lpad(i::text,12,'0'))::uuid,
              'project','scale','project:'||lpad(i::text,10,'0'),'subject',NULL,1,
              TIMESTAMPTZ '2026-07-15 00:00:00+00'
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.wiki_page_revisions
            SELECT ('00000000-0000-0000-0006-'||lpad(i::text,12,'0'))::uuid,
              1,NULL,'3','# project:'||lpad(i::text,10,'0'),NULL,NULL,
              TIMESTAMPTZ '2026-07-15 00:00:00+00',repeat('e',64),repeat('f',64)
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(
        text(
            """
            INSERT INTO cognitive_os.wiki_page_claims
            SELECT ('00000000-0000-0000-0006-'||lpad(i::text,12,'0'))::uuid,1,
              ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid,3,
              'current_supported',0
            FROM generate_series(1,1000) i
            """
        )
    )
    await connection.execute(text("ANALYZE cognitive_os.semantic_claims"))
    await connection.execute(text("ANALYZE cognitive_os.semantic_claim_revisions"))
    await connection.execute(text("ANALYZE cognitive_os.semantic_claim_evidence"))
    await connection.execute(text("ANALYZE cognitive_os.semantic_claim_relations"))
    await connection.execute(text("ANALYZE cognitive_os.semantic_contradiction_claims"))
    await connection.execute(text("ANALYZE cognitive_os.wiki_pages"))


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percentile))]


async def _execute_sample(connection, name: str, sql: str) -> None:
    result = await connection.execute(text(sql))
    if name != "bounded_graph_projection":
        result.all()
        return
    graph = nx.DiGraph()
    graph.add_edges_from((str(row[0]), str(row[2])) for row in result.all())
    nx.number_weakly_connected_components(graph)
    tuple(nx.simple_cycles(graph, length_bound=8))


async def run(output: Path, iterations: int, *, reset_only: bool = False) -> None:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url, pool_size=2, max_overflow=0)
    try:
        async with engine.begin() as connection:
            database = str(await connection.scalar(text("SELECT current_database()")))
            if not database.endswith("_test"):
                raise RuntimeError("semantic scale baseline requires an isolated _test database")
            if reset_only:
                await _reset(connection)
                print(json.dumps({"database": database, "reset": True}, sort_keys=True))
                return
            await _fixture(connection)
        measurements = {}
        plans = {}
        async with engine.connect() as connection:
            for name, sql in QUERIES.items():
                await _execute_sample(connection, name, sql)
                elapsed = []
                for _ in range(iterations):
                    started = perf_counter()
                    await _execute_sample(connection, name, sql)
                    elapsed.append((perf_counter() - started) * 1000)
                measurements[name] = {
                    "iterations": iterations,
                    "p50_ms": round(median(elapsed), 3),
                    "p95_ms": round(_percentile(elapsed, 0.95), 3),
                    "maximum_ms": round(max(elapsed), 3),
                }
                plan = await connection.scalar(text("EXPLAIN (FORMAT JSON) " + sql))
                plans[name] = plan
                if "Index" not in json.dumps(plan):
                    raise RuntimeError(f"scale query plan does not use an index: {name}")
            actual_counts = {
                "claims": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.semantic_claims")
                ),
                "claim_revisions": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.semantic_claim_revisions")
                ),
                "evidence": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.semantic_claim_evidence")
                ),
                "relations": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.semantic_claim_relations")
                ),
                "contradictions": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.semantic_contradictions")
                ),
                "wiki_pages": await connection.scalar(
                    text("SELECT count(*) FROM cognitive_os.wiki_pages")
                ),
            }
            database_size = int(
                await connection.scalar(text("SELECT pg_database_size(current_database())")) or 0
            )
            postgres_version = str(await connection.scalar(text("SHOW server_version")))
        normalized_counts = {key: int(value or 0) for key, value in actual_counts.items()}
        if normalized_counts != COUNTS:
            raise RuntimeError(f"semantic scale fixture count mismatch: {normalized_counts}")
        report = {
            "fixture": normalized_counts,
            "measurements": measurements,
            "plans": plans,
            "environment": {
                "database_size_bytes": database_size,
                "machine": platform.machine(),
                "platform": platform.platform(),
                "postgresql": postgres_version,
                "python": sys.version.split()[0],
                "processor": platform.processor() or "unknown",
            },
            "architecture": {
                "ann_index": False,
                "graph_database": False,
                "networkx_projection_bounded_rows": 500,
                "postgresql_authoritative": True,
            },
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "fixture": normalized_counts}, sort_keys=True))
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/benchmarks/sprint-10-scale-baseline.json"),
    )
    parser.add_argument("--iterations", type=int, default=30)
    parser.add_argument("--reset-only", action="store_true")
    args = parser.parse_args()
    if args.iterations < 5:
        raise ValueError("at least five measurement iterations are required")
    asyncio.run(run(args.output, args.iterations, reset_only=args.reset_only))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
