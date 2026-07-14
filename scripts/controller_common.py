"""Credential-safe PostgreSQL controller CLI composition."""

import os
from uuid import UUID

from cognitive_os.events.catalog import build_default_event_catalog
from cognitive_os.infrastructure.postgres.engine import create_postgres_engine
from cognitive_os.infrastructure.postgres.event_store import PostgresEventStore


def build_event_store():
    database_url = os.environ.get("COGOS_DATABASE_URL")
    if not database_url:
        raise RuntimeError("COGOS_DATABASE_URL is required")
    engine = create_postgres_engine(database_url)
    return engine, PostgresEventStore(engine, build_default_event_catalog())


def parse_task_run_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as error:
        raise ValueError("task-run ID must be a UUID") from error
