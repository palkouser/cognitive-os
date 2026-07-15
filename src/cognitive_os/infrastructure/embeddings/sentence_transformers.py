"""Optional local-only Sentence Transformers adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderHealth,
    EmbeddingProviderIdentity,
    EmbeddingProviderPort,
)
from cognitive_os.domain.common import Sha256Hex
from cognitive_os.memory.errors import EmbeddingUnavailableError


class LocalSentenceTransformerProvider(EmbeddingProviderPort):
    def __init__(
        self,
        model_path: Path,
        *,
        model_id: str,
        model_digest: Sha256Hex,
        dimension: int,
        maximum_batch_size: int = 64,
    ) -> None:
        if not model_path.is_absolute():
            raise ValueError("local model path must be absolute")
        self._model_path = model_path
        self._identity = EmbeddingProviderIdentity(
            provider_id="sentence-transformers-local",
            model_id=model_id,
            dimension=dimension,
            local_artifact_digest=model_digest,
        )
        self._maximum_batch_size = maximum_batch_size
        self._model: Any | None = None

    @property
    def identity(self) -> EmbeddingProviderIdentity:
        return self._identity

    def _load(self) -> Any:
        if not self._model_path.is_dir():
            raise EmbeddingUnavailableError("preconfigured local model directory is unavailable")
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise EmbeddingUnavailableError(
                    "local-embeddings extra is not installed"
                ) from error
            self._model = SentenceTransformer(
                str(self._model_path), device="cpu", local_files_only=True
            )
        return self._model

    async def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts or len(texts) > self._maximum_batch_size:
            raise ValueError("embedding batch is empty or exceeds the configured maximum")
        vectors = self._load().encode(list(texts), normalize_embeddings=True)
        result = tuple(tuple(float(value) for value in vector) for vector in vectors)
        if any(len(vector) != self.identity.dimension for vector in result):
            raise ValueError("local model output dimension mismatch")
        return result

    async def embed_query(self, text: str) -> tuple[float, ...]:
        return (await self.embed_documents((text,)))[0]

    async def health_check(self) -> EmbeddingProviderHealth:
        try:
            self._load()
        except EmbeddingUnavailableError as error:
            return EmbeddingProviderHealth(
                identity=self.identity,
                available=False,
                device="cpu",
                reason=str(error),
            )
        return EmbeddingProviderHealth(
            identity=self.identity,
            available=True,
            device="cpu",
            reason="preconfigured local model available",
        )
