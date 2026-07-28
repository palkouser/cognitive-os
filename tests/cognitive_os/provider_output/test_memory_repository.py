"""The in-memory reference, bound to the shared contract.

Credential-free and database-free, so the whole suite runs on the offline lane. That the
same file also runs against PostgreSQL is what makes the port a specification rather than
a description of whichever implementation was written first.
"""

from __future__ import annotations

from uuid import UUID, uuid5

from cognitive_os.application.ports.provider_output import ProviderOutputRepositoryPort
from cognitive_os.infrastructure.learned.memory_provider_output import (
    InMemoryProviderOutputRepository,
)

from . import fixtures as fx
from .repository_contract import ProviderOutputRepositoryContract


class TestInMemoryProviderOutputRepository(ProviderOutputRepositoryContract):
    async def make_repository(self) -> ProviderOutputRepositoryPort:
        return InMemoryProviderOutputRepository()

    async def link_evidence(self) -> tuple[UUID, UUID | None, str | None]:
        """Invented identities: the in-memory store has no foreign keys to satisfy.

        Deliberately still *stable*, so a record built here hashes the same on every run and
        the contract's hash assertions mean something.
        """
        return (
            uuid5(fx.FIXTURE_NAMESPACE, "completed-event"),
            uuid5(fx.FIXTURE_NAMESPACE, "response-artifact"),
            fx.HASH_B,
        )
