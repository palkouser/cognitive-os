"""Inspect the deterministic controlled-change lifecycle without active-state mutation."""

import argparse
import asyncio
import json
import os

from cognitive_os.changes.demo import run_demo


async def database_health() -> int:
    from cognitive_os.infrastructure.changes.postgres.health import PostgresChangeHealthService
    from cognitive_os.infrastructure.postgres.engine import create_postgres_engine

    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required for database health")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresChangeHealthService(engine).check()
    finally:
        await engine.dispose()
    print(report.model_dump_json())
    return 0 if report.healthy else 1


async def run(action: str, database: bool) -> int:
    if action == "health" and database:
        return await database_health()
    result = await run_demo()
    mapping = {
        "request": "experiment",
        "approve-isolation": "revision",
        "prepare": "isolation",
        "implement": "candidate",
        "evaluate": "comparison",
        "assess": "assessment",
        "approve-promotion": "promotion_review",
        "promote": "promotion_bundle",
        "rollback": "promotion_bundle",
        "show": "experiment",
        "list": "revision",
        "artifacts": "candidate",
    }
    if action == "health":
        print(
            json.dumps(
                {
                    "healthy": True,
                    "change_surfaces": 15,
                    "runtime_release_operations": 0,
                },
                sort_keys=True,
            )
        )
    else:
        print(result[mapping[action]].model_dump_json())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "request",
            "approve-isolation",
            "prepare",
            "implement",
            "evaluate",
            "assess",
            "approve-promotion",
            "promote",
            "rollback",
            "show",
            "list",
            "artifacts",
            "health",
        ),
    )
    parser.add_argument("--database", action="store_true")
    parser.add_argument("--experiment-id")
    parser.add_argument("--revision", type=int)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    consequential = {
        "approve-isolation",
        "prepare",
        "implement",
        "evaluate",
        "assess",
        "approve-promotion",
        "promote",
        "rollback",
    }
    if args.action in consequential and not args.confirm:
        parser.error("authority-sensitive fixture actions require --confirm")
    if args.action in consequential and (not args.experiment_id or args.revision is None):
        parser.error("authority-sensitive actions require exact --experiment-id and --revision")
    return asyncio.run(run(args.action, args.database))


if __name__ == "__main__":
    raise SystemExit(main())
