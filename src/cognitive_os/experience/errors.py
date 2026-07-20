"""Experience Compiler errors."""


class ExperienceError(RuntimeError):
    """Base compiler error."""


class ExperienceSourceError(ExperienceError):
    """An authoritative source is absent, stale, or invalid."""


class ExperiencePolicyError(ExperienceError):
    """A governance boundary would be violated."""


class ExperienceConflictError(ExperienceError):
    """An append-only or idempotency precondition failed."""
