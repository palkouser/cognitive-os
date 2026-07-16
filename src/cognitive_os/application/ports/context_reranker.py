"""Optional advisory context-reranker boundary."""

from typing import Protocol

from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextRerankerDescriptor,
)


class ContextRerankerPort(Protocol):
    @property
    def descriptor(self) -> ContextRerankerDescriptor: ...

    async def health_check(self) -> ContextComponentHealth: ...

    async def rerank(
        self, query: str, candidates: tuple[ContextCandidate, ...]
    ) -> tuple[ContextCandidate, ...]: ...
