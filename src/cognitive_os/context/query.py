"""Locale-independent query normalization and bounded decomposition."""

import re
import unicodedata
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.domain.context import (
    CodeQuerySeed,
    ContextCandidate,
    ContextQueryPlan,
    ContextRequest,
    ContextSourceType,
    GraphQuerySeed,
    QueryTerm,
    RetrievalMode,
    RetrievalSubquery,
    SemanticQuerySeed,
    TemporalQuerySelector,
)
from cognitive_os.domain.memory import MemoryScope

_PATH = re.compile(r"(?<![\w/])(?:[\w.-]+/)+[\w.-]+")
_SYMBOL = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")
_WORD = re.compile(r"[\w.+-]+", re.UNICODE)


def normalize_query(value: str, *, maximum_length: int = 8_192) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).split())
    if not normalized:
        raise ValueError("context query must not be empty")
    if len(normalized) > maximum_length:
        raise ValueError("context query exceeds the host limit")
    return normalized


def _modes(source_type: ContextSourceType) -> tuple[RetrievalMode, ...]:
    if source_type is ContextSourceType.MEMORY:
        return (RetrievalMode.LEXICAL, RetrievalMode.EXACT_VECTOR, RetrievalMode.RECENT)
    if source_type is ContextSourceType.SEMANTIC_GRAPH:
        return (RetrievalMode.GRAPH,)
    if source_type in {ContextSourceType.EVENT, ContextSourceType.USER_CORRECTION}:
        return (RetrievalMode.RECENT,)
    if source_type in {ContextSourceType.REPOSITORY_INDEX, ContextSourceType.WORKSPACE}:
        return (RetrievalMode.CODE,)
    if source_type is ContextSourceType.SEMANTIC_CLAIM:
        return (RetrievalMode.SOURCE_LOOKUP,)
    if source_type in {ContextSourceType.PROCEDURAL_SKILL, ContextSourceType.STRATEGY}:
        return (RetrievalMode.METADATA, RetrievalMode.LEXICAL, RetrievalMode.SOURCE_LOOKUP)
    return (RetrievalMode.METADATA,)


def build_query_plan(request: ContextRequest) -> ContextQueryPlan:
    normalized = normalize_query(request.query)
    raw_hash = sha256(request.query.encode()).hexdigest()
    tokens = tuple(dict.fromkeys(match.group(0).casefold() for match in _WORD.finditer(normalized)))
    terms = tuple(QueryTerm(value=value, normalized=value) for value in tokens[:64])
    paths = tuple(dict.fromkeys(match.group(0) for match in _PATH.finditer(normalized)))[:64]
    symbols = tuple(dict.fromkeys(match.group(0) for match in _SYMBOL.finditer(normalized)))[:64]
    subqueries: list[RetrievalSubquery] = []
    for source_type in sorted(request.allowed_source_types, key=lambda item: item.value):
        for mode in _modes(source_type):
            seed = f"{request.context_request_id}:{source_type.value}:{mode.value}:{raw_hash}"
            subqueries.append(
                RetrievalSubquery(
                    subquery_id=uuid5(NAMESPACE_URL, seed),
                    source_type=source_type,
                    mode=mode,
                    terms=terms,
                    code=(
                        CodeQuerySeed(paths=paths, symbols=symbols)
                        if mode is RetrievalMode.CODE
                        else None
                    ),
                    semantic=(
                        SemanticQuerySeed(subject_keys=(), predicate_ids=())
                        if source_type is ContextSourceType.SEMANTIC_CLAIM
                        else None
                    ),
                    graph=(GraphQuerySeed(node_ids=()) if mode is RetrievalMode.GRAPH else None),
                    temporal=TemporalQuerySelector(
                        valid_at=request.valid_at, known_at=request.known_at
                    ),
                    maximum_results=min(200, request.budget.maximum_candidates),
                )
            )
    subqueries.sort(
        key=lambda item: (item.source_type.value, item.mode.value, str(item.subquery_id))
    )
    if len(subqueries) > request.budget.maximum_retriever_calls:
        raise ValueError("query decomposition exceeds the retriever-call budget")
    return ContextQueryPlan(
        query_plan_id=uuid5(NAMESPACE_URL, f"context-query-plan:{request.canonical_hash()}"),
        raw_query_hash=raw_hash,
        normalized_query=normalized,
        subqueries=tuple(subqueries),
    )


def candidate_id(
    source_type: ContextSourceType,
    source_identity: str,
    source_revision: str,
    scopes: tuple[MemoryScope, ...],
    content_or_metadata_hash: str,
) -> UUID:
    scope_hash = sha256(
        "|".join(
            scope.canonical_hash()
            for scope in sorted(scopes, key=lambda item: (item.scope_type.value, item.scope_id))
        ).encode()
    ).hexdigest()
    return uuid5(
        NAMESPACE_URL,
        ":".join(
            (
                "context-candidate-v1",
                source_type.value,
                source_identity,
                source_revision,
                scope_hash,
                content_or_metadata_hash,
            )
        ),
    )


def reseal_candidate(candidate: ContextCandidate, **updates: object) -> ContextCandidate:
    """Revalidate a candidate after a deterministic transformation."""
    return ContextCandidate.model_validate({**candidate.model_dump(mode="python"), **updates})
