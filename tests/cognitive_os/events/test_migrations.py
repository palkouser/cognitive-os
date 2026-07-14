import pytest

from cognitive_os.events.migrations import MigrationRegistry, MissingMigrationPathError


def test_registered_migration_does_not_mutate_input() -> None:
    registry = MigrationRegistry()
    registry.register_migration("example.created", 1, 2, lambda value: {**value, "name": "new"})
    original = {"name": "old"}
    migrated = registry.migrate("example.created", 1, 2, original)
    assert migrated == {"name": "new"}
    assert original == {"name": "old"}


def test_missing_migration_path_fails() -> None:
    with pytest.raises(MissingMigrationPathError):
        MigrationRegistry().migrate("example.created", 1, 2, {})
