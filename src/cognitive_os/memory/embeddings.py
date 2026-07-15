"""Explicit revision-specific embedding creation service."""

from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.embedding_provider import EmbeddingProviderPort
from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import Sha256Hex, utc_now
from cognitive_os.domain.memory import MemoryEmbeddingRecord

from .errors import MemoryIntegrityError, MemoryNotFoundError


class MemoryEmbeddingService:
    def __init__(
        self,
        repository: MemoryRepositoryPort,
        providers: dict[str, EmbeddingProviderPort],
    ) -> None:
        self._repository = repository
        self._providers = dict(providers)

    async def create(
        self,
        memory_id: UUID,
        revision_number: int,
        content_hash: Sha256Hex,
        provider_id: str,
    ) -> MemoryEmbeddingRecord:
        revision = await self._repository.get_revision(memory_id, revision_number)
        if revision is None:
            raise MemoryNotFoundError("memory revision does not exist")
        if revision.content_hash != content_hash:
            raise MemoryIntegrityError("stale content hash blocks embedding creation")
        provider = self._providers.get(provider_id)
        if provider is None:
            raise MemoryNotFoundError("embedding provider is not configured")
        vector = await provider.embed_query(revision.content.render_search_text())
        identity = provider.identity
        record = MemoryEmbeddingRecord(
            embedding_id=uuid5(
                NAMESPACE_URL,
                f"embedding:{memory_id}:{revision_number}:{identity.provider_id}:"
                f"{identity.model_id}:{content_hash}",
            ),
            memory_id=memory_id,
            revision=revision_number,
            provider_id=identity.provider_id,
            model_id=identity.model_id,
            dimension=identity.dimension,
            content_hash=content_hash,
            vector=vector,
            created_at=utc_now(),
        )
        await self._repository.record_embedding(record)
        return record
