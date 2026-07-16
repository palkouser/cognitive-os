"""Optional local-only advisory rerankers."""

from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, cast

from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextComponentStatus,
    ContextRerankerDescriptor,
    RerankerType,
)


class CrossEncoderModel(Protocol):
    def predict(self, sentences: list[tuple[str, str]]) -> Iterable[float]: ...


class NoOpContextReranker:
    descriptor = ContextRerankerDescriptor(
        reranker_id="context.noop",
        version="1",
        reranker_type=RerankerType.NONE,
        deterministic=True,
    )

    async def health_check(self) -> ContextComponentHealth:
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)

    async def rerank(
        self, query: str, candidates: tuple[ContextCandidate, ...]
    ) -> tuple[ContextCandidate, ...]:
        return candidates


class LocalCrossEncoderReranker:
    """Opt-in CPU adapter; deterministic RRF remains the default."""

    def __init__(self, model: CrossEncoderModel, *, model_digest: str) -> None:
        self._model = model
        self.descriptor = ContextRerankerDescriptor(
            reranker_id="context.cross_encoder",
            version="1",
            reranker_type=RerankerType.LOCAL_CROSS_ENCODER,
            deterministic=True,
            model_digest=model_digest,
        )

    @classmethod
    def from_local_path(cls, path: Path, *, model_digest: str) -> LocalCrossEncoderReranker:
        if not path.is_absolute() or not path.exists():
            raise ValueError("CrossEncoder model path must be absolute and preconfigured")
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(str(path), device="cpu", local_files_only=True)
        return cls(cast(CrossEncoderModel, model), model_digest=model_digest)

    async def health_check(self) -> ContextComponentHealth:
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)

    async def rerank(
        self, query: str, candidates: tuple[ContextCandidate, ...]
    ) -> tuple[ContextCandidate, ...]:
        pairs = [
            (query, (item.content or item.summary or item.source_identity)[:32_768])
            for item in candidates
        ]
        scores = [float(item) for item in self._model.predict(pairs)]
        if len(scores) != len(candidates) or not all(math.isfinite(item) for item in scores):
            raise ValueError("CrossEncoder returned invalid advisory scores")
        return tuple(
            candidate
            for _, candidate in sorted(
                zip(scores, candidates, strict=True),
                key=lambda item: (-item[0], str(item[1].candidate_id)),
            )
        )
