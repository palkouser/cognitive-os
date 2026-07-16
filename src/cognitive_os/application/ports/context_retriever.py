"""Read-only Context Retriever boundary."""

import asyncio
from typing import Protocol

from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextRequest,
    ContextRetrieverDescriptor,
    HydrationLevel,
    RetrievalSubquery,
)


class ContextRetrieverPort(Protocol):
    @property
    def descriptor(self) -> ContextRetrieverDescriptor: ...

    async def health_check(self) -> ContextComponentHealth: ...

    async def retrieve(
        self,
        subquery: RetrievalSubquery,
        request: ContextRequest,
        cancellation: asyncio.Event | None = None,
    ) -> tuple[ContextCandidate, ...]: ...

    async def hydrate(
        self,
        candidate: ContextCandidate,
        level: HydrationLevel,
        cancellation: asyncio.Event | None = None,
    ) -> ContextCandidate: ...
