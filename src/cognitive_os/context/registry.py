"""Frozen deterministic Context Retriever registry."""

import json
from hashlib import sha256

from cognitive_os.application.ports.context_retriever import ContextRetrieverPort
from cognitive_os.domain.context import ContextSourceType

from .errors import ContextRetrieverError


class ContextRetrieverRegistry:
    def __init__(self) -> None:
        self._retrievers: dict[tuple[str, str], ContextRetrieverPort] = {}
        self._unavailable: dict[tuple[str, str], tuple[ContextRetrieverPort, str]] = {}
        self._frozen = False

    def register(
        self, retriever: ContextRetrieverPort, *, unavailable_reason: str | None = None
    ) -> None:
        if self._frozen:
            raise ContextRetrieverError("context retriever registry is frozen")
        descriptor = retriever.descriptor
        key = descriptor.retriever_id, descriptor.version
        if key in self._retrievers or key in self._unavailable:
            raise ContextRetrieverError(f"duplicate context retriever: {key[0]}@{key[1]}")
        if unavailable_reason:
            self._unavailable[key] = retriever, unavailable_reason
        else:
            self._retrievers[key] = retriever

    def freeze(self) -> None:
        self._frozen = True

    def list_available(self) -> tuple[ContextRetrieverPort, ...]:
        return tuple(self._retrievers[key] for key in sorted(self._retrievers))

    def resolve(self, source_type: ContextSourceType) -> ContextRetrieverPort:
        matches = [
            item for item in self.list_available() if source_type in item.descriptor.source_types
        ]
        if not matches:
            raise ContextRetrieverError(f"no available retriever for source: {source_type.value}")
        return matches[0]

    def snapshot(self) -> str:
        records = []
        for key in sorted((*self._retrievers, *self._unavailable)):
            if key in self._retrievers:
                retriever, available, reason = self._retrievers[key], True, None
            else:
                retriever, reason = self._unavailable[key]
                available = False
            records.append(
                {
                    **retriever.descriptor.model_dump(mode="json"),
                    "available": available,
                    "reason": reason,
                }
            )
        return sha256(
            json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def health_snapshot(self) -> tuple[dict[str, object], ...]:
        rows = []
        for key in sorted((*self._retrievers, *self._unavailable)):
            if key in self._retrievers:
                retriever, available, reason = self._retrievers[key], True, None
            else:
                retriever, reason = self._unavailable[key]
                available = False
            rows.append(
                {
                    "retriever_id": retriever.descriptor.retriever_id,
                    "version": retriever.descriptor.version,
                    "source_types": [item.value for item in retriever.descriptor.source_types],
                    "available": available,
                    "reason": reason,
                    "requires_network": retriever.descriptor.requires_network,
                    "maximum_candidates": retriever.descriptor.maximum_candidates,
                }
            )
        return tuple(rows)
