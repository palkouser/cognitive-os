"""Collection boundary for optional external-service tests."""

from importlib.util import find_spec

collect_ignore = ["postgres"] if find_spec("sqlalchemy") is None else []
