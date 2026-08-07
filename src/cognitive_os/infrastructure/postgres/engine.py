"""Asynchronous PostgreSQL engine lifecycle, and the one rule every truncating path obeys."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

#: The environment variable that nominates one database for erasure, by name.
TRUNCATABLE_DATABASE = "COGOS_TRUNCATABLE_DATABASE"


class TruncationNotNominated(RuntimeError):
    """Nobody nominated a database, so nobody asked for this. Usually a skip."""


class TruncationRefused(RuntimeError):
    """A database was nominated and a different one is connected. Always loud."""


def require_nominated_for_truncation(database: str) -> None:
    """Refuse to erase a database that was not named for erasure. S21D4-084, finding W7-F1.

    Lives here because everything that connects goes through this module, and because the
    alternative — a copy of the rule beside each `TRUNCATE` — is exactly what went wrong.

    W6-F2 established the rule for the integration fixture and D4-W0-F1 established it for the
    learned smoke, each in its own file. Five more paths kept the older fence, "the database
    name ends in `_test`", which is a naming convention rather than consent: every sprint's
    *evidence* database ends in `_test` too. On 2026-08-07 a release-matrix run with the D4
    environment sourced put `cognitive_os_s21d4_test` in front of those five, and they truncated
    1,076 committed observations, 9 datasets and 18 artifact lineages. That store had a backup
    from three minutes earlier; D3's, erased the same way in W0-F1, did not.

    So there is one implementation and every truncating path calls it. A second mechanism
    answering the same question differently is how an operator ends up knowing one fence and
    meeting the other.
    """
    nominated = os.environ.get(TRUNCATABLE_DATABASE)
    if nominated is None:
        raise TruncationNotNominated(f"no database is nominated by {TRUNCATABLE_DATABASE}")
    if nominated != database:
        raise TruncationRefused(
            f"refusing to TRUNCATE {database}: {TRUNCATABLE_DATABASE} names {nominated}. "
            "Nominating one database and connecting to another is a misconfiguration, and the "
            "next statement would have been a TRUNCATE."
        )


def create_postgres_engine(
    database_url: str,
    *,
    pool_size: int = 5,
    max_overflow: int = 5,
    pool_timeout_seconds: float = 30.0,
    command_timeout_seconds: float = 30.0,
) -> AsyncEngine:
    url = make_url(database_url)
    if url.drivername != "postgresql+asyncpg":
        raise ValueError("database URL must use postgresql+asyncpg")
    if pool_size < 1 or max_overflow < 0:
        raise ValueError("connection pool bounds are invalid")
    if pool_timeout_seconds <= 0 or command_timeout_seconds <= 0:
        raise ValueError("database timeouts must be positive")
    return create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout_seconds,
        connect_args={
            "command_timeout": command_timeout_seconds,
            "server_settings": {
                "application_name": "cognitive-os",
                "timezone": "UTC",
            },
        },
    )


@asynccontextmanager
async def postgres_transaction(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with engine.begin() as connection:
        yield connection


async def dispose_postgres_engine(engine: AsyncEngine) -> None:
    await engine.dispose()
