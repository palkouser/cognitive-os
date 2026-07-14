"""Asynchronous PostgreSQL engine lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


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
