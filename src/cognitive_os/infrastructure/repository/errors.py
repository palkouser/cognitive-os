"""Trusted repository service failures."""


class RepositoryError(RuntimeError):
    """Base repository service error."""


class RepositoryPolicyError(RepositoryError):
    """Repository operation violated host policy."""


class GitCommandError(RepositoryError):
    """Allowlisted Git command failed."""


class GitCommandTimeout(GitCommandError):
    """Allowlisted Git command exceeded its deadline."""
