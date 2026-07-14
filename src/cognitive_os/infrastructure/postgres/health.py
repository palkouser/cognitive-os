"""Credential-safe PostgreSQL health checks."""

from __future__ import annotations

from time import perf_counter

from pydantic import Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.infrastructure.errors import EventStoreUnavailableError


class PostgresHealth(ImmutableContractModel):
    healthy: bool
    database_version: str
    migration_revision: str | None
    latency_ms: float = Field(ge=0)


async def check_postgres_health(engine: AsyncEngine) -> PostgresHealth:
    started = perf_counter()
    try:
        async with engine.connect() as connection:
            version = await connection.scalar(text("SELECT current_setting('server_version')"))
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
    except (SQLAlchemyError, OSError, TimeoutError) as error:
        raise EventStoreUnavailableError("PostgreSQL health check failed") from error
    return PostgresHealth(
        healthy=True,
        database_version=str(version),
        migration_revision=str(revision) if revision is not None else None,
        latency_ms=(perf_counter() - started) * 1000,
    )
