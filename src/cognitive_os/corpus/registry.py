"""Small frozen registries for Corpus Factory policies and processors."""

from __future__ import annotations

from collections.abc import Callable

from cognitive_os.domain.corpus import DestinationPolicyReference
from cognitive_os.experience.registry import canonical_hash

from .errors import CorpusPolicyError


class FrozenRegistry[T]:
    def __init__(self) -> None:
        self._items: dict[str, T] = {}
        self._frozen = False

    def register(self, identity: str, item: T) -> None:
        if self._frozen:
            raise CorpusPolicyError("registry is frozen")
        if identity in self._items:
            raise CorpusPolicyError(f"duplicate corpus registry identity: {identity}")
        self._items[identity] = item

    def freeze(self) -> None:
        self._frozen = True

    def resolve(self, identity: str) -> T:
        try:
            return self._items[identity]
        except KeyError as error:
            raise CorpusPolicyError(
                f"corpus registry identity is unavailable: {identity}"
            ) from error

    def values(self) -> tuple[T, ...]:
        return tuple(self._items[key] for key in sorted(self._items))

    def snapshot_hash(self) -> str:
        values = [
            item.content_hash if hasattr(item, "content_hash") else identity
            for identity, item in sorted(self._items.items())
        ]
        return canonical_hash(values)


Normalizer = Callable[[bytes, str], tuple[bytes, tuple[str, ...]]]
NormalizerRegistry = FrozenRegistry[Normalizer]
DestinationPolicyRegistry = FrozenRegistry[DestinationPolicyReference]
LicenseRegistry = FrozenRegistry[dict[str, bool]]
