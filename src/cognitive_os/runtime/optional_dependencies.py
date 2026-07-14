"""Capability checks for optional legacy integrations."""

from __future__ import annotations

from importlib.util import find_spec


class OptionalDependencyError(ImportError):
    """Raised when an explicitly requested optional feature is unavailable."""


def legacy_memory_available() -> bool:
    """Return whether the optional Mem0 integration is installed."""
    return find_spec("mem0") is not None


def require_legacy_memory() -> None:
    """Require the legacy memory extra before activating its adapter."""
    if not legacy_memory_available():
        raise OptionalDependencyError(
            "Legacy LightAgent memory support is not installed. "
            "Install the 'lightagent-legacy-memory' optional extra to enable it."
        )
