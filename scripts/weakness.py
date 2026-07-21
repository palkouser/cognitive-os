"""Inspect deterministic, diagnostic-only weakness mining."""

from __future__ import annotations

import argparse
import asyncio
import os

from cognitive_os.domain.weakness import MiningProfile, MiningRequest
from cognitive_os.weakness.fixtures import (
    FixtureSignalExtractor,
    FixtureSourceResolver,
    fixture_profile,
    fixture_request,
    fixture_sources,
)
from cognitive_os.weakness.repository import InMemoryWeaknessRepository
from cognitive_os.weakness.service import (
    SignalExtractorRegistry,
    SourceResolverRegistry,
    WeaknessMiningService,
)


def fixture_service(
    cases: int,
) -> tuple[WeaknessMiningService, MiningRequest, MiningProfile]:
    sources = fixture_sources(cases)
    source_registry = SourceResolverRegistry()
    for source_type in sorted({item.source_type for item in sources}, key=str):
        source_registry.register(FixtureSourceResolver(source_type, sources))
    source_registry.freeze()
    extractors = SignalExtractorRegistry()
    extractors.register(FixtureSignalExtractor())
    extractors.freeze()
    profile = fixture_profile(sources)
    return (
        WeaknessMiningService(InMemoryWeaknessRepository(), source_registry, extractors),
        fixture_request(profile, cases),
        profile,
    )


async def _database_health() -> int:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
    from cognitive_os.infrastructure.weakness.postgres.health import (
        PostgresWeaknessHealthService,
    )

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresWeaknessHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def _run(cases: int) -> int:
    service, request, profile = fixture_service(cases)
    result = await service.mine(request, profile)
    print(result.model_dump_json())
    return int(result.manifest is None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("mine", "groups", "queue", "health"))
    parser.add_argument("--cases", type=int, default=18)
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    if args.cases < 1:
        raise SystemExit("--cases must be positive")
    if args.action == "health" and args.database:
        return asyncio.run(_database_health())
    return asyncio.run(_run(args.cases))


if __name__ == "__main__":
    raise SystemExit(main())
