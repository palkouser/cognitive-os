"""Typed Corpus Factory failures."""


class CorpusError(RuntimeError):
    """Base Corpus Factory failure."""


class CorpusSourceError(CorpusError):
    """Unsafe, malformed, or unverifiable source."""


class CorpusPolicyError(CorpusError):
    """Host policy denied a corpus operation."""


class CorpusConflictError(CorpusError):
    """Append-only identity or compare-and-set conflict."""


class CorpusNormalizationError(CorpusError):
    """Deterministic normalization failed."""
