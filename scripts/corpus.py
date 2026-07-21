"""Inspect the governed, package-only Corpus-to-Memory Factory."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from cognitive_os.corpus.factory import MANDATORY_VERIFIERS, CorpusFactory
from cognitive_os.corpus.fixtures import (
    INITIAL_CORPUS_FIXTURES,
    FixtureArtifactStore,
    build_corpus_fixture,
)
from cognitive_os.corpus.repository import InMemoryCorpusRepository


async def _database_health() -> int:
    from cognitive_os.infrastructure.corpus.postgres.health import PostgresCorpusHealthService
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresCorpusHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def _run(args: argparse.Namespace) -> int:
    request, source = build_corpus_fixture(args.fixture)
    result = await CorpusFactory(InMemoryCorpusRepository(), FixtureArtifactStore()).ingest(
        request, source
    )
    payload: object
    if args.action == "source":
        payload = result.source_manifest
    elif args.action == "normalized":
        payload = result.normalized
    elif args.action == "classifications":
        payload = result.classifications
    elif args.action == "quality":
        payload = result.quality
    elif args.action == "routes":
        payload = result.route_decisions
    elif args.action == "manifest":
        payload = result.manifest
    elif args.action == "export":
        payload = result.export
    elif args.action == "health":
        payload = {
            "healthy": True,
            "fixtures": len(INITIAL_CORPUS_FIXTURES),
            "mandatory_verifiers": len(MANDATORY_VERIFIERS),
            **result.usage,
        }
    else:
        payload = result
    print(json.dumps(payload, default=lambda value: value.model_dump(mode="json"), sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "ingest",
            "source",
            "normalized",
            "classifications",
            "quality",
            "routes",
            "manifest",
            "export",
            "health",
        ),
    )
    parser.add_argument("--fixture", choices=INITIAL_CORPUS_FIXTURES, default="document")
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    if args.action == "health" and args.database:
        return asyncio.run(_database_health())
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
