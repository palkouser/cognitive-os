"""Minimal read-only retrievers over existing Cognitive OS source contracts."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from decimal import Decimal
from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.application.ports.semantic_memory_repository import SemanticMemoryRepositoryPort
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
from cognitive_os.domain.memory import (
    MemoryAccessKind,
    MemoryAccessRecord,
    MemoryMetadataFilter,
    MemoryQuery,
    MemoryQueryBudget,
    MemoryRetrievalMode,
    MemoryStatus,
    MemoryTextQuery,
    MemoryVectorQuery,
)
from cognitive_os.domain.semantic_memory import BeliefStatus, TemporalClaimQuery, TemporalQueryMode
from cognitive_os.memory.retrieval import MemoryRetrievalService
from cognitive_os.semantic_memory.service import SemanticMemoryService

from .query import candidate_id, reseal_candidate

type CandidateLoader = Callable[
    [RetrievalSubquery, ContextRequest], Awaitable[tuple[ContextCandidate, ...]]
]
type CandidateHydrator = Callable[[ContextCandidate, HydrationLevel], Awaitable[ContextCandidate]]

_SOURCE_TRUST = {
    ContextSourceType.TASK_STATE: ContextTrustClass.SYSTEM,
    ContextSourceType.EXECUTION_PLAN: ContextTrustClass.SYSTEM,
    ContextSourceType.EVENT: ContextTrustClass.UNVERIFIED,
    ContextSourceType.PROVIDER_RESULT: ContextTrustClass.UNVERIFIED,
    ContextSourceType.TOOL_RESULT: ContextTrustClass.VERIFIED,
    ContextSourceType.ARTIFACT: ContextTrustClass.EXTERNAL,
    ContextSourceType.MEMORY: ContextTrustClass.UNVERIFIED,
    ContextSourceType.SEMANTIC_CLAIM: ContextTrustClass.VERIFIED,
    ContextSourceType.SEMANTIC_GRAPH: ContextTrustClass.VERIFIED,
    ContextSourceType.WIKI: ContextTrustClass.VERIFIED,
    ContextSourceType.REPOSITORY_INDEX: ContextTrustClass.SYSTEM,
    ContextSourceType.WORKSPACE: ContextTrustClass.SYSTEM,
    ContextSourceType.USER_CORRECTION: ContextTrustClass.USER_PROVIDED,
    ContextSourceType.PROCEDURAL_SKILL: ContextTrustClass.VERIFIED,
    ContextSourceType.STRATEGY: ContextTrustClass.VERIFIED,
}


class CallbackContextRetriever:
    """Descriptor-bound adapter for host sources that already expose typed read methods."""

    def __init__(
        self,
        descriptor: ContextRetrieverDescriptor,
        loader: CandidateLoader,
        hydrator: CandidateHydrator | None = None,
    ) -> None:
        self._descriptor = descriptor
        self._loader = loader
        self._hydrator = hydrator

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
        if subquery.source_type not in self.descriptor.source_types:
            raise ValueError("subquery source type is not supported by this retriever")
        values = await self._loader(subquery, request)
        if len(values) > min(subquery.maximum_results, self.descriptor.maximum_candidates):
            values = values[: min(subquery.maximum_results, self.descriptor.maximum_candidates)]
        return values

    async def hydrate(
        self,
        candidate: ContextCandidate,
        level: HydrationLevel,
        cancellation: asyncio.Event | None = None,
    ) -> ContextCandidate:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        if level not in candidate.available_hydration_levels:
            raise ValueError("requested hydration level is unavailable")
        if self._hydrator is None:
            if candidate.content is None and level is not HydrationLevel.METADATA:
                raise ValueError("candidate body hydration is unavailable")
            return reseal_candidate(candidate, selected_hydration_level=level)
        return await self._hydrator(candidate, level)


def host_context_retriever(
    source_type: ContextSourceType,
    loader: CandidateLoader,
    hydrator: CandidateHydrator | None = None,
) -> CallbackContextRetriever:
    """Create one explicit adapter for an existing host-owned source read contract."""
    modes = {
        ContextSourceType.EVENT: (RetrievalMode.RECENT,),
        ContextSourceType.MEMORY: (
            RetrievalMode.METADATA,
            RetrievalMode.LEXICAL,
            RetrievalMode.EXACT_VECTOR,
            RetrievalMode.RECENT,
            RetrievalMode.SOURCE_LOOKUP,
        ),
        ContextSourceType.SEMANTIC_GRAPH: (RetrievalMode.GRAPH,),
        ContextSourceType.REPOSITORY_INDEX: (RetrievalMode.CODE,),
        ContextSourceType.WORKSPACE: (RetrievalMode.CODE,),
        ContextSourceType.USER_CORRECTION: (RetrievalMode.RECENT,),
        ContextSourceType.PROCEDURAL_SKILL: (
            RetrievalMode.METADATA,
            RetrievalMode.LEXICAL,
            RetrievalMode.SOURCE_LOOKUP,
        ),
        ContextSourceType.STRATEGY: (
            RetrievalMode.METADATA,
            RetrievalMode.LEXICAL,
            RetrievalMode.SOURCE_LOOKUP,
            RetrievalMode.GRAPH,
        ),
    }.get(source_type, (RetrievalMode.METADATA, RetrievalMode.SOURCE_LOOKUP))
    return CallbackContextRetriever(
        ContextRetrieverDescriptor(
            retriever_id=f"context.{source_type.value}",
            version="1",
            source_types=(source_type,),
            supported_modes=modes,
            deterministic=True,
            requires_artifact_store=source_type
            in {
                ContextSourceType.ARTIFACT,
                ContextSourceType.PROVIDER_RESULT,
                ContextSourceType.TOOL_RESULT,
                ContextSourceType.WIKI,
            },
            requires_workspace=source_type is ContextSourceType.WORKSPACE,
            default_trust_class=_SOURCE_TRUST[source_type],
            maximum_candidates=200,
        ),
        loader,
        hydrator,
    )


class InMemoryContextRetriever(CallbackContextRetriever):
    """Credential-free deterministic fixture retriever for every source contract."""

    def __init__(
        self,
        *,
        retriever_id: str,
        source_types: tuple[ContextSourceType, ...],
        candidates: tuple[ContextCandidate, ...],
        bodies: Mapping[UUID, Mapping[HydrationLevel, str]] | None = None,
        modes: tuple[RetrievalMode, ...] = tuple(RetrievalMode),
        trust_class: ContextTrustClass = ContextTrustClass.UNVERIFIED,
    ) -> None:
        self._candidates = candidates
        self._bodies = bodies or {}
        descriptor = ContextRetrieverDescriptor(
            retriever_id=retriever_id,
            version="1",
            source_types=source_types,
            supported_modes=modes,
            default_trust_class=trust_class,
            maximum_candidates=200,
        )
        super().__init__(descriptor, self._load, self._hydrate)

    async def _load(
        self, subquery: RetrievalSubquery, request: ContextRequest
    ) -> tuple[ContextCandidate, ...]:
        query_terms = {item.normalized for item in subquery.terms}
        matches = []
        for candidate in self._candidates:
            if candidate.source_type is not subquery.source_type:
                continue
            if not any(scope in request.required_scopes for scope in candidate.scopes):
                continue
            text = (candidate.summary or candidate.content or candidate.source_identity).casefold()
            lexical_hits = sum(term in text for term in query_terms)
            if subquery.mode is RetrievalMode.LEXICAL and query_terms and not lexical_hits:
                continue
            score = Decimal(lexical_hits or 1) / Decimal(max(len(query_terms), 1))
            route = RetrieverRank(
                retriever_id=self.descriptor.retriever_id,
                mode=subquery.mode,
                rank=1,
                raw_score=score,
            )
            matches.append(reseal_candidate(candidate, retrieval_routes=(route,)))
        matches.sort(key=lambda item: (-item.retrieval_routes[0].raw_score, str(item.candidate_id)))
        return tuple(
            reseal_candidate(
                item,
                retrieval_routes=(item.retrieval_routes[0].model_copy(update={"rank": rank}),),
            )
            for rank, item in enumerate(matches, start=1)
        )

    async def _hydrate(
        self, candidate: ContextCandidate, level: HydrationLevel
    ) -> ContextCandidate:
        body = self._bodies.get(candidate.candidate_id, {}).get(level)
        if body is None:
            if level is HydrationLevel.METADATA:
                return reseal_candidate(candidate, selected_hydration_level=level)
            if candidate.content is None:
                raise ValueError("fixture hydration body is unavailable")
            body = candidate.content
        return reseal_candidate(
            candidate,
            content=body,
            content_hash=sha256(body.encode()).hexdigest(),
            selected_hydration_level=level,
        )


class MemoryContextRetriever(CallbackContextRetriever):
    """Memory Plane adapter preserving existing retrieval and access audit."""

    def __init__(
        self,
        service: MemoryRetrievalService,
        repository: MemoryRepositoryPort,
        *,
        vector_query: Callable[[str], MemoryVectorQuery | None] | None = None,
    ) -> None:
        self._service = service
        self._repository = repository
        self._vector_query = vector_query
        self._bodies: dict[UUID, str] = {}
        self._accesses: dict[UUID, MemoryAccessRecord] = {}
        super().__init__(
            ContextRetrieverDescriptor(
                retriever_id="context.memory",
                version="1",
                source_types=(ContextSourceType.MEMORY, ContextSourceType.USER_CORRECTION),
                supported_modes=(
                    RetrievalMode.METADATA,
                    RetrievalMode.LEXICAL,
                    RetrievalMode.EXACT_VECTOR,
                    RetrievalMode.RECENT,
                    RetrievalMode.SOURCE_LOOKUP,
                ),
                deterministic=True,
                requires_postgres=False,
                default_trust_class=ContextTrustClass.UNVERIFIED,
                maximum_candidates=200,
            ),
            self._load,
            self._hydrate,
        )

    async def _load(
        self, subquery: RetrievalSubquery, request: ContextRequest
    ) -> tuple[ContextCandidate, ...]:
        mode = {
            RetrievalMode.LEXICAL: MemoryRetrievalMode.TEXT,
            RetrievalMode.EXACT_VECTOR: MemoryRetrievalMode.VECTOR,
        }.get(subquery.mode, MemoryRetrievalMode.METADATA)
        vector = (
            self._vector_query(request.query)
            if mode is MemoryRetrievalMode.VECTOR and self._vector_query
            else None
        )
        if mode is MemoryRetrievalMode.VECTOR and vector is None:
            return ()
        query_id = uuid5(NAMESPACE_URL, f"memory-context:{subquery.subquery_id}")
        query = MemoryQuery(
            query_id=query_id,
            mode=mode,
            filters=MemoryMetadataFilter(
                memory_types=frozenset(request.allowed_memory_types),
                scopes=request.required_scopes,
                sensitivity_ceiling=request.sensitivity_limit,
            ),
            text=(
                MemoryTextQuery(text=request.query) if mode is MemoryRetrievalMode.TEXT else None
            ),
            vector=vector,
            budget=MemoryQueryBudget(
                maximum_results=min(subquery.maximum_results, 100),
                maximum_candidates=request.budget.maximum_candidates,
            ),
        )
        page, _ = await self._service.retrieve(query, task_run_id=request.task_run_id)
        candidates = []
        for result in page.results:
            revision = await self._repository.get_revision(result.memory_id, result.revision)
            if revision is None:
                continue
            body = revision.content.render_search_text()
            source_type = (
                ContextSourceType.USER_CORRECTION
                if revision.content.memory_type.value == "correction"
                else ContextSourceType.MEMORY
            )
            if source_type is not subquery.source_type:
                continue
            digest = sha256(body.encode()).hexdigest()
            identity = str(result.memory_id)
            context_id = candidate_id(
                source_type, identity, str(result.revision), (result.scope,), digest
            )
            self._bodies[context_id] = body
            access_id = uuid5(
                NAMESPACE_URL,
                f"{query_id}:{result.memory_id}:{result.revision}:{result.rank}",
            )
            access_record = MemoryAccessRecord(
                access_id=access_id,
                query_id=query_id,
                task_run_id=request.task_run_id,
                memory_id=result.memory_id,
                revision=result.revision,
                retrieval_mode=mode,
                retrieval_rank=result.rank,
                retrieval_score=result.score,
                accessed_at=request.created_at,
                scope=result.scope,
                sensitivity=result.sensitivity,
                query_hash=query.model_copy(update={"cursor": None}).canonical_hash(),
                filter_hash=query.filters.canonical_hash(),
            )
            self._accesses[context_id] = access_record
            candidates.append(
                ContextCandidate(
                    candidate_id=context_id,
                    source_type=source_type,
                    source_identity=identity,
                    source_revision=str(result.revision),
                    content_hash=digest,
                    summary=result.title,
                    scopes=(result.scope,),
                    sensitivity=result.sensitivity,
                    trust_class=(
                        ContextTrustClass.VERIFIED
                        if result.status is MemoryStatus.VERIFIED
                        else ContextTrustClass.USER_PROVIDED
                        if source_type is ContextSourceType.USER_CORRECTION
                        else ContextTrustClass.UNVERIFIED
                    ),
                    retrieval_routes=(
                        RetrieverRank(
                            retriever_id=self.descriptor.retriever_id,
                            mode=subquery.mode,
                            rank=result.rank,
                            raw_score=Decimal(str(result.score)),
                        ),
                    ),
                    score_breakdown=ContextScoreBreakdown(salience=Decimal(str(revision.salience))),
                    provenance=(
                        ContextSourceReference(
                            source_type=source_type,
                            source_identity=identity,
                            source_revision=str(result.revision),
                            content_hash=revision.content_hash,
                        ),
                    ),
                    known_at=revision.created_at,
                    available_hydration_levels=(
                        HydrationLevel.METADATA,
                        HydrationLevel.SUMMARY,
                        HydrationLevel.FULL,
                    ),
                    evidence=result.status is MemoryStatus.VERIFIED,
                    recent=subquery.mode is RetrievalMode.RECENT,
                    access_audit_ids=(access_id,),
                )
            )
        if subquery.mode is RetrievalMode.RECENT:
            candidates.sort(key=lambda item: (item.known_at, str(item.candidate_id)), reverse=True)
        return tuple(candidates)

    async def _hydrate(
        self, candidate: ContextCandidate, level: HydrationLevel
    ) -> ContextCandidate:
        if level is HydrationLevel.METADATA:
            body = None
        else:
            body = (
                candidate.summary
                if level is HydrationLevel.SUMMARY
                else self._bodies[candidate.candidate_id]
            )
        retrieved = self._accesses[candidate.candidate_id]
        used_access_id = uuid5(NAMESPACE_URL, f"context-used:{retrieved.access_id}")
        await self._repository.record_access(
            (
                retrieved.model_copy(
                    update={
                        "access_id": used_access_id,
                        "access_kind": MemoryAccessKind.USED_IN_CONTEXT,
                    }
                ),
            )
        )
        if body is None:
            return reseal_candidate(
                candidate,
                selected_hydration_level=level,
                access_audit_ids=tuple((*candidate.access_audit_ids, used_access_id)),
            )
        return reseal_candidate(
            candidate,
            content=body,
            content_hash=sha256(body.encode()).hexdigest(),
            selected_hydration_level=level,
            access_audit_ids=tuple((*candidate.access_audit_ids, used_access_id)),
        )


class SemanticClaimContextRetriever(CallbackContextRetriever):
    """Bitemporal semantic-claim adapter with exact claim revision lineage."""

    def __init__(
        self,
        service: SemanticMemoryService,
        repository: SemanticMemoryRepositoryPort,
    ) -> None:
        self._service = service
        self._repository = repository
        self._bodies: dict[UUID, str] = {}
        super().__init__(
            ContextRetrieverDescriptor(
                retriever_id="context.semantic",
                version="1",
                source_types=(ContextSourceType.SEMANTIC_CLAIM,),
                supported_modes=(RetrievalMode.SOURCE_LOOKUP,),
                deterministic=True,
                requires_postgres=False,
                default_trust_class=ContextTrustClass.VERIFIED,
                maximum_candidates=200,
            ),
            self._load,
            self._hydrate,
        )

    async def _load(
        self, subquery: RetrievalSubquery, request: ContextRequest
    ) -> tuple[ContextCandidate, ...]:
        mode = TemporalQueryMode.BITEMPORAL
        query = TemporalClaimQuery(
            query_id=uuid5(NAMESPACE_URL, f"semantic-context:{subquery.subquery_id}"),
            mode=mode,
            scopes=request.required_scopes,
            sensitivity_ceiling=request.sensitivity_limit,
            valid_at=request.valid_at,
            known_at=request.known_at,
        )
        result, access_records = await self._service.query_claims_with_access(query)
        access_by_claim = {
            (item.claim_id, item.claim_revision): item.access_id for item in access_records
        }
        values = []
        for rank, revision in enumerate(result.claims, start=1):
            claim = await self._repository.get_claim(revision.claim_id)
            if claim is None:
                continue
            identity = str(revision.claim_id)
            digest = sha256(revision.statement.encode()).hexdigest()
            context_id = candidate_id(
                ContextSourceType.SEMANTIC_CLAIM,
                identity,
                str(revision.revision),
                (claim.identity.scope,),
                digest,
            )
            self._bodies[context_id] = revision.statement
            values.append(
                ContextCandidate(
                    candidate_id=context_id,
                    source_type=ContextSourceType.SEMANTIC_CLAIM,
                    source_identity=identity,
                    source_revision=str(revision.revision),
                    content_hash=digest,
                    summary=revision.statement,
                    scopes=(claim.identity.scope,),
                    sensitivity=claim.sensitivity,
                    trust_class={
                        BeliefStatus.SUPPORTED: ContextTrustClass.VERIFIED,
                        BeliefStatus.DISPUTED: ContextTrustClass.DISPUTED,
                    }.get(revision.belief_status, ContextTrustClass.UNVERIFIED),
                    retrieval_routes=(
                        RetrieverRank(
                            retriever_id=self.descriptor.retriever_id,
                            mode=subquery.mode,
                            rank=rank,
                            raw_score=Decimal(1) / Decimal(rank),
                        ),
                    ),
                    provenance=(
                        ContextSourceReference(
                            source_type=ContextSourceType.SEMANTIC_CLAIM,
                            source_identity=identity,
                            source_revision=str(revision.revision),
                            content_hash=revision.content_hash,
                        ),
                    ),
                    valid_at=revision.valid_interval.valid_from,
                    known_at=revision.recorded_at,
                    available_hydration_levels=(
                        HydrationLevel.METADATA,
                        HydrationLevel.SUMMARY,
                        HydrationLevel.FULL,
                    ),
                    evidence=revision.belief_status is BeliefStatus.SUPPORTED,
                    access_audit_ids=(access_by_claim[(revision.claim_id, revision.revision)],),
                )
            )
        return tuple(values)

    async def _hydrate(
        self, candidate: ContextCandidate, level: HydrationLevel
    ) -> ContextCandidate:
        if level is HydrationLevel.METADATA:
            return reseal_candidate(candidate, selected_hydration_level=level)
        body = candidate.summary or self._bodies[candidate.candidate_id]
        return reseal_candidate(
            candidate,
            content=body,
            content_hash=sha256(body.encode()).hexdigest(),
            selected_hydration_level=level,
        )
