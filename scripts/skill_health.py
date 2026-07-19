"""Report canonical read-only procedural Skill Engine health."""

import asyncio
import json
import os

from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.skills.postgres.health import PostgresSkillHealthService


async def run() -> int:
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url, pool_size=1, max_overflow=0)
    try:
        report = await PostgresSkillHealthService(engine).check()
    finally:
        await engine.dispose()
    print(json.dumps(report.model_dump(mode="json"), sort_keys=True, separators=(",", ":")))
    return 0 if report.healthy else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
