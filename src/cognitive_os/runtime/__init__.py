"""Compatibility boundary for the repository-local LightAgent runtime."""

from .optional_dependencies import (
    OptionalDependencyError,
    legacy_memory_available,
    require_legacy_memory,
)

__all__ = ["OptionalDependencyError", "legacy_memory_available", "require_legacy_memory"]
