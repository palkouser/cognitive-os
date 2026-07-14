"""Public schema registry and export API."""

from .registry import SchemaEntry, build_schema_registry

__all__ = ["SchemaEntry", "build_schema_registry"]
