"""Explicit bounded SQL statements for exact governed-memory retrieval."""

from __future__ import annotations

from sqlalchemy import Select, and_, func, or_, select

from cognitive_os.domain.memory import MemoryQuery, MemoryRetrievalMode

from .tables import memory_items, memory_revisions


def current_memory_statement(query: MemoryQuery) -> Select[tuple[object, ...]]:
    statement = (
        select(memory_items, memory_revisions)
        .join(
            memory_revisions,
            and_(
                memory_revisions.c.memory_id == memory_items.c.memory_id,
                memory_revisions.c.revision == memory_items.c.current_revision,
            ),
        )
        .where(memory_items.c.status.in_([status.value for status in query.filters.statuses]))
    )
    if query.filters.memory_types:
        statement = statement.where(
            memory_items.c.memory_type.in_(
                [memory_type.value for memory_type in query.filters.memory_types]
            )
        )
    if query.filters.scopes:
        scope_predicates = tuple(
            and_(
                memory_items.c.scope_type == scope.scope_type.value,
                memory_items.c.scope_id == scope.scope_id,
            )
            for scope in query.filters.scopes
        )
        statement = statement.where(or_(*scope_predicates))
    if query.mode is MemoryRetrievalMode.TEXT:
        if query.text is None:
            raise ValueError("text retrieval requires a text query")
        statement = statement.where(
            memory_revisions.c.search_document.op("@@")(
                func.websearch_to_tsquery(query.text.language, query.text.text)
            )
        )
    return statement.limit(query.budget.maximum_candidates)
