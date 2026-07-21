"""Application boundary for the governed Corpus Factory."""

from typing import Protocol
from uuid import UUID

from cognitive_os.corpus.sources import InspectedSource
from cognitive_os.domain.corpus import CorpusFactoryRequest, CorpusFactoryResult


class CorpusFactoryPort(Protocol):
    async def ingest(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> CorpusFactoryResult: ...

    async def resume(
        self, request: CorpusFactoryRequest, source: InspectedSource
    ) -> CorpusFactoryResult: ...

    def cancel(self, request_id: UUID) -> None: ...
