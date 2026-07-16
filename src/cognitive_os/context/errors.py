"""Typed Context Builder failures."""


class ContextBuilderError(RuntimeError):
    """Base Context Builder failure."""


class ContextBudgetError(ContextBuilderError):
    """Required context cannot fit the host-owned budget."""


class ContextSafetyError(ContextBuilderError):
    """Context failed a safety boundary."""


class ContextSourceStaleError(ContextBuilderError):
    """A required mutable source changed before provider execution."""


class ContextRetrieverError(ContextBuilderError):
    """A requested retriever is invalid or unavailable."""
