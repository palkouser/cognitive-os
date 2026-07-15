"""Provider-neutral embedding boundary."""

from __future__ import annotations

from typing import Protocol

from cognitive_os.domain.base import ImmutableContractModel
from cognitive_os.domain.common import NonEmptyStr, Sha256Hex


class EmbeddingProviderIdentity(ImmutableContractModel):
    provider_id: NonEmptyStr
    model_id: NonEmptyStr
    dimension: int
    local_artifact_digest: Sha256Hex | None = None


class EmbeddingProviderHealth(ImmutableContractModel):
    identity: EmbeddingProviderIdentity
    available: bool
    device: NonEmptyStr
    reason: str | None = None


class EmbeddingProviderPort(Protocol):
    @property
    def identity(self) -> EmbeddingProviderIdentity: ...

    async def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]: ...

    async def embed_query(self, text: str) -> tuple[float, ...]: ...

    async def health_check(self) -> EmbeddingProviderHealth: ...
