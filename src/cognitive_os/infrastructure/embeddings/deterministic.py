"""Credential-free deterministic embeddings for tests and reproducible fixtures."""

from __future__ import annotations

import math
import re
from hashlib import sha256

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderHealth,
    EmbeddingProviderIdentity,
    EmbeddingProviderPort,
)


class DeterministicEmbeddingProvider(EmbeddingProviderPort):
    """Hashing-vector provider; deliberately not a semantic-quality model."""

    def __init__(self, *, dimension: int = 64, maximum_batch_size: int = 64) -> None:
        if dimension < 1 or dimension > 4096:
            raise ValueError("embedding dimension must be between 1 and 4096")
        if maximum_batch_size < 1 or maximum_batch_size > 64:
            raise ValueError("embedding batch size must be between 1 and 64")
        self._identity = EmbeddingProviderIdentity(
            provider_id="deterministic-test",
            model_id="sha256-token-hashing-v1",
            dimension=dimension,
        )
        self._maximum_batch_size = maximum_batch_size

    @property
    def identity(self) -> EmbeddingProviderIdentity:
        return self._identity

    async def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts or len(texts) > self._maximum_batch_size:
            raise ValueError("embedding batch is empty or exceeds the configured maximum")
        return tuple(self._embed(text) for text in texts)

    async def embed_query(self, text: str) -> tuple[float, ...]:
        return self._embed(text)

    async def health_check(self) -> EmbeddingProviderHealth:
        return EmbeddingProviderHealth(
            identity=self.identity,
            available=True,
            device="cpu",
            reason="test-only deterministic hashing vector",
        )

    def _embed(self, text: str) -> tuple[float, ...]:
        normalized = " ".join(text.casefold().split())
        values = [0.0] * self.identity.dimension
        for token in re.findall(r"[a-z0-9_]+", normalized):
            digest = sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.identity.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign
        if not any(values):
            digest = sha256(normalized.encode()).digest()
            values[int.from_bytes(digest[:4], "big") % self.identity.dimension] = 1.0
        norm = math.sqrt(sum(value * value for value in values))
        return tuple(value / norm for value in values)
