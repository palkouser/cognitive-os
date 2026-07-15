"""Typed Memory Plane failures."""


class MemoryError(Exception):
    """Base governed-memory failure."""


class MemoryNotFoundError(MemoryError):
    """Requested memory or revision does not exist."""


class MemoryConcurrencyError(MemoryError):
    """Expected revision did not match current state."""


class MemoryPolicyDeniedError(MemoryError):
    def __init__(self, reason_codes: tuple[str, ...]) -> None:
        self.reason_codes = reason_codes
        super().__init__("memory write denied: " + ", ".join(reason_codes))


class MemoryIntegrityError(MemoryError):
    """Stored memory failed canonical validation."""


class MemoryAuditError(MemoryError):
    """Required append-only access audit failed."""


class EmbeddingUnavailableError(MemoryError):
    """Configured embedding provider is unavailable."""
