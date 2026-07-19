"""Read-only Context Builder adapter for verified strategies."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.strategy_repository import StrategyRepositoryPort
from cognitive_os.context.query import candidate_id, reseal_candidate
from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextComponentStatus,
    ContextRequest,
    ContextRetrieverDescriptor,
    ContextScoreBreakdown,
    ContextSourceReference,
    ContextSourceType,
    ContextTrustClass,
    HydrationLevel,
    RetrievalMode,
    RetrievalSubquery,
    RetrieverRank,
)
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType
from cognitive_os.domain.strategies import (
    StrategyAccessRecord,
    StrategyAccessType,
    StrategyRevision,
    StrategyScope,
    StrategyScopeType,
    StrategyStatus,
)
from cognitive_os.memory.governance import sensitivity_allows

from .engine import StrategyRegistry


def _context_scope(scope: StrategyScope) -> MemoryScope:
    return MemoryScope(
        scope_type={
            StrategyScopeType.GLOBAL: MemoryScopeType.GLOBAL,
            StrategyScopeType.PROJECT: MemoryScopeType.PROJECT,
            StrategyScopeType.REPOSITORY: MemoryScopeType.REPOSITORY,
            StrategyScopeType.DOMAIN: MemoryScopeType.DOMAIN,
        }[scope.scope_type],
        scope_id=scope.scope_id,
    )


class StrategyContextRetriever:
    def __init__(
        self,
        registry: StrategyRegistry,
        repository: StrategyRepositoryPort,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._revisions: dict[UUID, StrategyRevision] = {}
        self._requests: dict[UUID, ContextRequest] = {}
        self._descriptor = ContextRetrieverDescriptor(
            retriever_id="context.strategy",
            version="1",
            source_types=(ContextSourceType.STRATEGY,),
            supported_modes=(
                RetrievalMode.METADATA,
                RetrievalMode.LEXICAL,
                RetrievalMode.SOURCE_LOOKUP,
                RetrievalMode.GRAPH,
            ),
            deterministic=True,
            requires_postgres=True,
            default_trust_class=ContextTrustClass.VERIFIED,
            maximum_candidates=200,
        )

    @property
    def descriptor(self) -> ContextRetrieverDescriptor:
        return self._descriptor

    async def health_check(self) -> ContextComponentHealth:
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)

    async def retrieve(
        self,
        subquery: RetrievalSubquery,
        request: ContextRequest,
        cancellation: asyncio.Event | None = None,
    ) -> tuple[ContextCandidate, ...]:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        if subquery.source_type is not ContextSourceType.STRATEGY:
            raise ValueError("strategy retriever accepts only strategy subqueries")
        terms = {term.normalized for term in subquery.terms}
        matches: list[tuple[int, ContextCandidate, StrategyAccessRecord]] = []
        for item, revision in self._registry.query(statuses=(StrategyStatus.VERIFIED,)):
            scope = _context_scope(item.identity.scope)
            if scope not in request.required_scopes or not sensitivity_allows(
                revision.sensitivity, request.sensitivity_limit
            ):
                continue
            searchable = " ".join(
                (
                    item.identity.canonical_name,
                    item.identity.problem_class_id,
                    revision.display_name,
                    revision.description,
                    *(phase.display_name for phase in revision.phases),
                )
            ).casefold()
            hits = sum(term in searchable for term in terms)
            exact = request.query.casefold() in {
                str(revision.strategy_id).casefold(),
                item.identity.canonical_name,
                f"{revision.strategy_id}@{revision.revision}".casefold(),
            }
            if subquery.mode is RetrievalMode.LEXICAL and terms and hits == 0:
                continue
            if subquery.mode is RetrievalMode.SOURCE_LOOKUP and not exact:
                continue
            if subquery.mode is RetrievalMode.GRAPH:
                hits = len(self._registry.edge_set(revision.strategy_id, revision.revision).edges)
            summary = f"{revision.display_name}: {revision.description}"
            identity = str(revision.strategy_id)
            context_id = candidate_id(
                ContextSourceType.STRATEGY,
                identity,
                str(revision.revision),
                (scope,),
                revision.content_hash,
            )
            access_id = uuid5(
                NAMESPACE_URL,
                f"strategy-context:{subquery.subquery_id}:"
                f"{revision.strategy_id}:{revision.revision}",
            )
            candidate = ContextCandidate(
                candidate_id=context_id,
                source_type=ContextSourceType.STRATEGY,
                source_identity=identity,
                source_revision=str(revision.revision),
                content_hash=revision.content_hash,
                summary=summary,
                scopes=(scope,),
                sensitivity=revision.sensitivity,
                trust_class=ContextTrustClass.VERIFIED,
                retrieval_routes=(
                    RetrieverRank(
                        retriever_id=self.descriptor.retriever_id,
                        mode=subquery.mode,
                        rank=1,
                        raw_score=Decimal(max(hits, 1)),
                    ),
                ),
                score_breakdown=ContextScoreBreakdown(
                    verification=Decimal("1"), salience=Decimal("0.5")
                ),
                provenance=(
                    ContextSourceReference(
                        source_type=ContextSourceType.STRATEGY,
                        source_identity=identity,
                        source_revision=str(revision.revision),
                        content_hash=revision.content_hash,
                    ),
                ),
                known_at=revision.created_at,
                available_hydration_levels=(
                    HydrationLevel.METADATA,
                    HydrationLevel.SUMMARY,
                    HydrationLevel.EXCERPT,
                    HydrationLevel.FULL,
                ),
                evidence=True,
                access_audit_ids=(access_id,),
            )
            self._revisions[context_id] = revision
            self._requests[context_id] = request
            matches.append(
                (
                    hits,
                    candidate,
                    StrategyAccessRecord(
                        access_id=access_id,
                        strategy_id=revision.strategy_id,
                        revision=revision.revision,
                        access_type=StrategyAccessType.CONTEXT_RETRIEVAL,
                        task_run_id=request.task_run_id,
                        context_request_id=request.context_request_id,
                        query_hash=sha256(request.query.encode()).hexdigest(),
                        scope=item.identity.scope,
                        sensitivity=request.sensitivity_limit,
                        accessed_at=request.created_at,
                    ),
                )
            )
        matches.sort(key=lambda value: (-value[0], str(value[1].candidate_id)))
        limited = matches[: min(subquery.maximum_results, self.descriptor.maximum_candidates)]
        await self._repository.record_access(tuple(value[2] for value in limited))
        return tuple(
            reseal_candidate(
                value[1],
                retrieval_routes=(value[1].retrieval_routes[0].model_copy(update={"rank": rank}),),
            )
            for rank, value in enumerate(limited, start=1)
        )

    async def hydrate(
        self,
        candidate: ContextCandidate,
        level: HydrationLevel,
        cancellation: asyncio.Event | None = None,
    ) -> ContextCandidate:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        revision = self._revisions.get(candidate.candidate_id)
        request = self._requests.get(candidate.candidate_id)
        if revision is None or request is None:
            raise ValueError("strategy candidate was not returned by this retriever")
        current = self._registry.resolve(revision.strategy_id, revision.revision)
        if current.content_hash != revision.content_hash:
            raise ValueError("strategy revision changed after retrieval")
        if level is HydrationLevel.METADATA:
            content = None
            access_type = StrategyAccessType.CONTEXT_RETRIEVAL
        elif level is HydrationLevel.SUMMARY:
            content = candidate.summary
            access_type = StrategyAccessType.SUMMARY_HYDRATION
        elif level is HydrationLevel.EXCERPT:
            edges = self._registry.edge_set(revision.strategy_id, revision.revision).edges
            content = (
                "\n".join(
                    f"{edge.edge_type.value}:"
                    f"{edge.target.target_type.value}:"
                    f"{edge.target.target_id}@{edge.target.target_revision}"
                    for edge in edges
                )
                or "No lineage edges."
            )
            access_type = StrategyAccessType.SUMMARY_HYDRATION
        elif level is HydrationLevel.FULL:
            content = revision.canonical_json()
            access_type = StrategyAccessType.FULL_HYDRATION
        else:
            raise ValueError("unsupported strategy hydration level")
        access_id = uuid5(
            NAMESPACE_URL,
            f"strategy-hydration:{request.context_request_id}:"
            f"{candidate.candidate_id}:{level.value}",
        )
        item = next(
            value[0]
            for value in self._registry.query(statuses=(StrategyStatus.VERIFIED,))
            if value[1].strategy_id == revision.strategy_id
        )
        await self._repository.record_access(
            (
                StrategyAccessRecord(
                    access_id=access_id,
                    strategy_id=revision.strategy_id,
                    revision=revision.revision,
                    access_type=access_type,
                    task_run_id=request.task_run_id,
                    context_request_id=request.context_request_id,
                    query_hash=sha256(request.query.encode()).hexdigest(),
                    scope=item.identity.scope,
                    sensitivity=request.sensitivity_limit,
                    accessed_at=request.created_at,
                ),
            )
        )
        return reseal_candidate(
            candidate,
            content=content,
            content_hash=(
                sha256(content.encode()).hexdigest()
                if content is not None
                else candidate.content_hash
            ),
            selected_hydration_level=level,
            access_audit_ids=tuple(sorted({*candidate.access_audit_ids, access_id})),
        )
