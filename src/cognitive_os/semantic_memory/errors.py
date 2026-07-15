"""Typed semantic-memory failures."""


class SemanticMemoryError(RuntimeError):
    """Base semantic-memory failure."""


class SemanticConcurrencyError(SemanticMemoryError):
    """An expected revision or identity was stale."""


class SemanticIntegrityError(SemanticMemoryError):
    """Stored semantic state failed an invariant."""


class SemanticPolicyError(SemanticMemoryError):
    """Host semantic policy denied an operation."""
