"""S21D2-030: the shortlist the reranker receives is the one the policy declares.

The defect this file pins down is quiet by construction. `bounded_ged` shortlisted from
`minilm_vector`'s *public* result, and that result had already been truncated to
`returned_results`. So a resource policy that raised `vector_shortlist` to 20 while
returning 10 results still sent ten candidates to graph edit distance, and every metric
measured under it described width 10 while claiming width 20.

The proof is a count, not a metric: with a pool larger than both bounds, the reranker must
consider exactly `vector_shortlist` candidates while the caller still receives at most
`returned_results`.
"""

from __future__ import annotations

from hashlib import sha256

import pytest

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderHealth,
    EmbeddingProviderIdentity,
)
from cognitive_os.domain.experience_graph import (
    ActionDecisionGraph,
    ExperienceGraphEdge,
    ExperienceGraphEdgeKind,
    ExperienceGraphNode,
    ExperienceGraphNodeKind,
    ExperienceGraphQuery,
    GraphResourceLimits,
)
from cognitive_os.experience import graph_retrieval
from cognitive_os.experience.graph_retrieval import Candidate

#: Wider than either bound, so truncation at any stage is visible in the counts.
POOL_SIZE = 30


def _hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()


class DeterministicEmbedding:
    """A committed-fixture embedder: same text, same vector, no model, no network.

    CI must stay credential-free and model-free, and the property under test is a shortlist
    width rather than a similarity quality — so a hashed unit vector is the honest stub. The
    D1 diagnostic and every released metric use the real pinned MiniLM instead.
    """

    dimension = 8

    @property
    def identity(self) -> EmbeddingProviderIdentity:
        return EmbeddingProviderIdentity(
            provider_id="deterministic-test", model_id="hashed-unit", dimension=self.dimension
        )

    def _vector(self, text: str) -> tuple[float, ...]:
        digest = sha256(text.encode()).digest()
        return tuple(digest[index] / 255.0 for index in range(self.dimension))

    async def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._vector(text) for text in texts)

    async def embed_query(self, text: str) -> tuple[float, ...]:
        return self._vector(text)

    async def health_check(self) -> EmbeddingProviderHealth:
        return EmbeddingProviderHealth(identity=self.identity, available=True, device="cpu")


def _graph(index: int) -> ActionDecisionGraph:
    """Two nodes and one edge: enough for a real edit distance, cheap enough for a unit test."""
    return ActionDecisionGraph(
        graph_id=f"graph-{index:03d}",
        domain="coding",
        group=f"group-{index:03d}",
        task_signature=f"signature-{index:03d}",
        accepted=True,
        nodes=(
            ExperienceGraphNode(
                logical_id="n1",
                kind=ExperienceGraphNodeKind.OBSERVATION,
                attributes=(("detail", f"observation {index}"),),
                source_hash=_hash(f"n1-{index}"),
            ),
            ExperienceGraphNode(
                logical_id="n2",
                kind=ExperienceGraphNodeKind.CORRECTION,
                attributes=(("detail", f"correction {index}"),),
                source_hash=_hash(f"n2-{index}"),
            ),
        ),
        edges=(
            ExperienceGraphEdge(
                source_id="n1", target_id="n2", kind=ExperienceGraphEdgeKind.CORRECTED_BY
            ),
        ),
        source_manifest_hash=_hash(f"manifest-{index}"),
    )


@pytest.fixture
def pool() -> tuple[Candidate, ...]:
    return tuple(
        Candidate(
            pair_id=f"pair-{index:03d}",
            group=f"group-{index:03d}",
            domain="coding",
            task_signature=f"signature-{index:03d}",
            text=_graph(index).search_text(),
            graph=_graph(index),
        )
        for index in range(POOL_SIZE)
    )


@pytest.fixture
def query() -> ExperienceGraphQuery:
    return ExperienceGraphQuery(
        query_id="query-001",
        query_text=_graph(999).search_text(),
        domain="coding",
        task_signature="signature-999",
        excluded_groups=("group-999",),
    )


@pytest.fixture
def embed() -> DeterministicEmbedding:
    return DeterministicEmbedding()


class TestShortlistWidthIsTheDeclaredWidth:
    @pytest.mark.asyncio
    async def test_twenty_are_considered_while_at_most_ten_are_returned(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """The exact D2 revision-2 policy, and the exact regression that motivated it."""
        limits = GraphResourceLimits(vector_shortlist=20, returned_results=10)

        result = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )

        assert result.candidates_considered == 20
        assert len(result.entries) <= 10

    @pytest.mark.asyncio
    async def test_the_public_vector_arm_still_truncates_to_the_returned_bound(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Widening the internal shortlist must not widen what a caller receives."""
        limits = GraphResourceLimits(vector_shortlist=20, returned_results=10)

        result = await graph_retrieval.minilm_vector(query, pool, limits=limits, embed=embed)

        assert len(result.entries) == 10
        assert result.candidates_considered == POOL_SIZE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("width", [1, 5, 10, 20, 25])
    async def test_the_reranker_considers_exactly_the_declared_width(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
        width: int,
    ) -> None:
        """Width 10 must keep behaving as before, or this is a change and not a fix."""
        limits = GraphResourceLimits(vector_shortlist=width, returned_results=10)

        result = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )

        assert result.candidates_considered == width

    @pytest.mark.asyncio
    async def test_a_shortlist_wider_than_the_pool_considers_the_whole_pool(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """`vector_shortlist` is a ceiling. A thin pool is reported, never padded."""
        limits = GraphResourceLimits(vector_shortlist=100, returned_results=10)

        result = await graph_retrieval.bounded_ged(
            query, pool[:7], _graph(999), limits=limits, embed=embed
        )

        assert result.candidates_considered == 7


class TestOrderingIsUnchanged:
    @pytest.mark.asyncio
    async def test_the_shortlist_is_the_vector_arms_own_ranking(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """One ordering, shared. A separate sort here would rerank a different ten pairs."""
        limits = GraphResourceLimits(vector_shortlist=10, returned_results=10)

        vector = await graph_retrieval.minilm_vector(query, pool, limits=limits, embed=embed)
        scores = await graph_retrieval._vector_scores(query, pool, embed=embed)
        shortlist = [pair_id for pair_id, _ in graph_retrieval._ranked(scores)[:10]]

        assert [entry.pair_id for entry in vector.entries] == shortlist

    @pytest.mark.asyncio
    async def test_ranking_is_deterministic_across_repeated_calls(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        limits = GraphResourceLimits(vector_shortlist=20, returned_results=10)

        first = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )
        second = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )

        assert [e.pair_id for e in first.entries] == [e.pair_id for e in second.entries]
        assert [e.score for e in first.entries] == [e.score for e in second.entries]

    @pytest.mark.asyncio
    async def test_equal_scores_break_by_pair_id_not_by_pool_order(
        self, query: ExperienceGraphQuery, embed: DeterministicEmbedding
    ) -> None:
        """Identical text scores identically; the tie must not depend on how the pool arrived."""
        identical = tuple(
            Candidate(
                pair_id=f"pair-{index:03d}",
                group=f"group-{index:03d}",
                domain="coding",
                task_signature="shared",
                text="one identical projection",
                graph=_graph(index),
            )
            for index in range(5)
        )
        limits = GraphResourceLimits(vector_shortlist=5, returned_results=5)

        forward = await graph_retrieval.minilm_vector(query, identical, limits=limits, embed=embed)
        reversed_pool = await graph_retrieval.minilm_vector(
            query, identical[::-1], limits=limits, embed=embed
        )

        assert [e.pair_id for e in forward.entries] == sorted(c.pair_id for c in identical)
        assert [e.pair_id for e in reversed_pool.entries] == [e.pair_id for e in forward.entries]


class TestTheCacheStillWorksAcrossArms:
    @pytest.mark.asyncio
    async def test_a_shared_cache_is_populated_once_and_reused(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Embedding the pool once per benchmark, not once per arm, is why the cache exists."""
        limits = GraphResourceLimits(vector_shortlist=20, returned_results=10)
        cache: dict[str, tuple[float, ...]] = {}

        await graph_retrieval.minilm_vector(query, pool, limits=limits, embed=embed, cache=cache)
        after_vector = dict(cache)
        await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed, cache=cache
        )

        assert len(after_vector) == POOL_SIZE
        assert cache == after_vector
