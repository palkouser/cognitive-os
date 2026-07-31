"""Read-only Context Builder adapter for verified Experience Memory Graph repair paths.

What this returns is a *suggestion with provenance*: the ordered edit operations that
turned one recorded failure into one recorded success, on a different task, in a
different group. It is never an executable patch, it is never required, it is never
pinned, and it confers no authority to accept, promote or activate anything.

Three refusals, all fail-closed:

* a request whose purpose is not repair or advisory gets nothing, because a graph
  suggestion has no business in a planning or semantic-extraction bundle;
* a pair whose group appears in the request is dropped before ranking, so a repair
  request can never retrieve its own answer;
* a candidate is `VERIFIED` only when every hash it names resolves and its source
  outcome was independently accepted. Anything else degrades to `UNVERIFIED` rather
  than being withheld silently, so a degraded store is visible in the bundle instead of
  looking like an empty corpus.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from cognitive_os.context.query import candidate_id
from cognitive_os.domain.context import (
    ContextCandidate,
    ContextComponentHealth,
    ContextComponentStatus,
    ContextPurpose,
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
from cognitive_os.domain.experience_graph import FailedSuccessGraphPair, GraphResourceLimits
from cognitive_os.domain.memory import MemoryScope, MemoryScopeType, MemorySensitivity

#: The only purposes a repair suggestion belongs in.
ADVISORY_PURPOSES = (ContextPurpose.REPAIR, ContextPurpose.ADVISORY)

#: Resolves an artifact id to whether its bytes still hash to what was recorded.
ArtifactVerifier = Callable[[UUID], Awaitable[bool]]


class ExperienceGraphContextRetriever:
    """Bounded, advisory retrieval over a frozen graph-pair set."""

    def __init__(
        self,
        pairs: Sequence[FailedSuccessGraphPair],
        *,
        artifact_ids: dict[str, UUID] | None = None,
        verifier: ArtifactVerifier | None = None,
        limits: GraphResourceLimits | None = None,
    ) -> None:
        self._pairs = tuple(sorted(pairs, key=lambda pair: pair.pair_id))
        self._artifact_ids = dict(artifact_ids or {})
        self._verifier = verifier
        self._limits = limits or GraphResourceLimits()
        self._descriptor = ContextRetrieverDescriptor(
            retriever_id="context.experience_graph",
            version="1",
            source_types=(ContextSourceType.EXPERIENCE_GRAPH,),
            supported_modes=(
                RetrievalMode.METADATA,
                RetrievalMode.LEXICAL,
                RetrievalMode.SOURCE_LOOKUP,
                RetrievalMode.GRAPH,
            ),
            deterministic=True,
            requires_postgres=False,
            # Fail closed. A candidate earns VERIFIED per retrieval, by resolving its
            # hashes, never by belonging to this source type.
            default_trust_class=ContextTrustClass.UNVERIFIED,
            maximum_candidates=self._limits.returned_results,
        )

    @property
    def descriptor(self) -> ContextRetrieverDescriptor:
        return self._descriptor

    async def health_check(self) -> ContextComponentHealth:
        """Degraded rather than unavailable when the set is empty: the deterministic path
        keeps working without graph memory, which is the whole point of it being advisory."""
        if not self._pairs:
            return ContextComponentHealth(
                status=ContextComponentStatus.DEGRADED,
                reason="no graph pairs are loaded",
            )
        return ContextComponentHealth(status=ContextComponentStatus.AVAILABLE)

    def excluded_groups(self, request: ContextRequest) -> frozenset[str]:
        """Groups the request is about, which its own candidate pool must not contain.

        A repair request names the thing it is trying to repair. Any pair whose group or
        task signature appears in that text is the request's own case, and returning it
        would be retrieving the answer to the question.
        """
        text = request.query.casefold()
        return frozenset(
            pair.group
            for pair in self._pairs
            if pair.group.casefold() in text or pair.task_signature.casefold() in text
        )

    async def _trust_for(self, pair: FailedSuccessGraphPair) -> ContextTrustClass:
        if not pair.successful.accepted:
            return ContextTrustClass.UNVERIFIED
        if self._verifier is None:
            return ContextTrustClass.UNVERIFIED
        artifact_id = self._artifact_ids.get(pair.pair_id)
        if artifact_id is None:
            return ContextTrustClass.UNVERIFIED
        try:
            resolved = await self._verifier(artifact_id)
        except Exception:  # a verifier that raises means a corrupt or missing store
            return ContextTrustClass.UNVERIFIED
        return ContextTrustClass.VERIFIED if resolved else ContextTrustClass.UNVERIFIED

    async def retrieve(
        self,
        subquery: RetrievalSubquery,
        request: ContextRequest,
        cancellation: asyncio.Event | None = None,
    ) -> tuple[ContextCandidate, ...]:
        if cancellation is not None and cancellation.is_set():
            raise asyncio.CancelledError
        if subquery.source_type is not ContextSourceType.EXPERIENCE_GRAPH:
            raise ValueError("the experience graph retriever accepts only its own subqueries")
        if request.context_purpose not in ADVISORY_PURPOSES:
            return ()

        excluded = self.excluded_groups(request)
        terms = {term.normalized for term in subquery.terms}
        scored: list[tuple[int, FailedSuccessGraphPair]] = []
        for pair in self._pairs:
            if pair.group in excluded:
                continue
            searchable = pair.successful.search_text().casefold()
            hits = sum(term in searchable for term in terms)
            if subquery.mode is RetrievalMode.LEXICAL and terms and hits == 0:
                continue
            if subquery.mode is RetrievalMode.SOURCE_LOOKUP and request.query != pair.pair_id:
                continue
            scored.append((hits, pair))

        scored.sort(key=lambda item: (-item[0], item[1].pair_id))
        candidates = []
        for rank, (hits, pair) in enumerate(scored[: self._limits.returned_results], start=1):
            candidates.append(await self._candidate(pair, subquery, hits, rank))
        return tuple(candidates)

    async def _candidate(
        self,
        pair: FailedSuccessGraphPair,
        subquery: RetrievalSubquery,
        hits: int,
        rank: int,
    ) -> ContextCandidate:
        scope = MemoryScope(scope_type=MemoryScopeType.DOMAIN, scope_id=pair.domain)
        trust = await self._trust_for(pair)
        operations = len(pair.edit_path.operations)
        return ContextCandidate(
            candidate_id=candidate_id(
                ContextSourceType.EXPERIENCE_GRAPH,
                pair.pair_id,
                "1",
                (scope,),
                pair.content_hash,
            ),
            source_type=ContextSourceType.EXPERIENCE_GRAPH,
            source_identity=pair.pair_id,
            source_revision="1",
            content_hash=pair.edit_path.content_hash,
            summary=(
                f"{operations} suggested edit operations from a verified failed-to-success "
                f"path on {pair.task_signature} in domain {pair.domain}. Advisory only; "
                f"nothing here is an executable patch."
            ),
            scopes=(scope,),
            sensitivity=MemorySensitivity.INTERNAL,
            trust_class=trust,
            retrieval_routes=(
                RetrieverRank(
                    retriever_id=self.descriptor.retriever_id,
                    mode=subquery.mode,
                    rank=rank,
                    raw_score=Decimal(max(hits, 1)),
                ),
            ),
            score_breakdown=ContextScoreBreakdown(
                verification=Decimal("1") if trust is ContextTrustClass.VERIFIED else Decimal("0"),
                salience=Decimal("0.5"),
            ),
            provenance=(
                ContextSourceReference(
                    source_type=ContextSourceType.EXPERIENCE_GRAPH,
                    source_identity=pair.pair_id,
                    source_revision="1",
                    content_hash=pair.successful.content_hash,
                ),
            ),
            known_at=pair.compiled_at,
            available_hydration_levels=(HydrationLevel.METADATA, HydrationLevel.SUMMARY),
            # The three properties that keep memory advisory. A pinned or required
            # candidate would give retrieved history authority over the current run.
            pinned=False,
            required=False,
            evidence=False,
        )


def access_record_id(subquery_id: UUID, pair_id: str) -> UUID:
    """Stable identity for one graph read, so an access log cannot double-count."""
    return uuid5(NAMESPACE_URL, f"experience-graph-context:{subquery_id}:{pair_id}")
