"""Inspect governed model capabilities and deterministic routing decisions."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from cognitive_os.routing.fixtures import build_routing_request, replay_profiles, static_policy
from cognitive_os.routing.repository import InMemoryCapabilityRepository
from cognitive_os.routing.service import RoutingService


async def _database_health() -> int:
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
    from cognitive_os.infrastructure.routing.postgres.health import PostgresRoutingHealthService

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresRoutingHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def _run(args: argparse.Namespace) -> int:
    repository = InMemoryCapabilityRepository()
    service = RoutingService(repository)
    for profile in replay_profiles():
        await service.register_profile(profile)
    policy = static_policy()
    await service.create_policy(policy)
    if args.action == "models":
        payload: object = await repository.query_profiles()
    elif args.action == "decision":
        payload = await service.route_static(build_routing_request(args.fixture), policy)
    elif args.action == "statistics":
        from cognitive_os.routing.fixtures import build_observations

        for observation in build_observations(64):
            await service.ingest_observation(observation)
        payload = await service.rebuild_statistics()
    else:
        payload = {
            "healthy": True,
            "profiles": len(replay_profiles()),
            "control_mode": "static",
            "shadow_execution": False,
            "learned_routing": False,
            "credential_storage": False,
        }
    print(json.dumps(payload, default=lambda value: value.model_dump(mode="json"), sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("models", "decision", "statistics", "health"))
    parser.add_argument("--fixture", type=int, default=0)
    parser.add_argument("--database", action="store_true")
    args = parser.parse_args()
    if args.action == "health" and args.database:
        return asyncio.run(_database_health())
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
