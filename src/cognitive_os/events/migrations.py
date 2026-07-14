"""Explicit event-payload migration registry foundation."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy

from cognitive_os.domain.common import JsonValue

MigrationFunction = Callable[[dict[str, JsonValue]], dict[str, JsonValue]]


class MissingMigrationPathError(LookupError):
    """Raised when no complete migration path is registered."""


class MigrationRegistry:
    def __init__(self) -> None:
        self._migrations: dict[tuple[str, int, int], MigrationFunction] = {}

    def register_migration(
        self,
        event_type: str,
        from_version: int,
        to_version: int,
        function: MigrationFunction,
    ) -> None:
        if from_version < 1 or to_version <= from_version:
            raise ValueError("migration versions must increase from a positive version")
        key = (event_type, from_version, to_version)
        if key in self._migrations:
            raise ValueError(f"duplicate migration registration: {key}")
        self._migrations[key] = function

    def migrate(
        self,
        event_type: str,
        from_version: int,
        target_version: int,
        payload: dict[str, JsonValue],
    ) -> dict[str, JsonValue]:
        current = from_version
        result = deepcopy(payload)
        while current < target_version:
            candidates = sorted(
                (
                    to_version,
                    function,
                )
                for (
                    registered_type,
                    registered_from,
                    to_version,
                ), function in self._migrations.items()
                if registered_type == event_type
                and registered_from == current
                and to_version <= target_version
            )
            if not candidates:
                raise MissingMigrationPathError(
                    f"missing migration path: {event_type} v{current} to v{target_version}"
                )
            next_version, function = candidates[0]
            result = function(deepcopy(result))
            current = next_version
        if current != target_version:
            raise MissingMigrationPathError(
                f"missing migration path: {event_type} v{current} to v{target_version}"
            )
        return result
