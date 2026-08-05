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
from importlib.util import find_spec

import pytest

from cognitive_os.application.ports.embedding_provider import (
    EmbeddingProviderHealth,
    EmbeddingProviderIdentity,
)
from cognitive_os.domain.experience_graph import (
    GRAPH_RESOURCE_POLICY_REVISION_2,
    GRAPH_RESOURCE_POLICY_REVISION_2_HASH,
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

#: `graph_edit_distance` imports numpy and scipy unconditionally, so the reranker needs the
#: whole `semantic-graph` extra. The dedicated experience lanes install it and prove the
#: shortlist width there; the general test lane runs without extras and skips, as it already
#: does for every other optional-dependency test. The vector-only tests below stay unmarked,
#: because they need no extra and should run everywhere.
needs_bounded_ged = pytest.mark.skipif(
    find_spec("networkx") is None or find_spec("scipy") is None,
    reason="semantic-graph extra is absent",
)


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


class TestThePublicVectorArmIsUnchanged:
    """Deliberately unmarked: it needs no extra, so it guards the public arm everywhere."""

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


@needs_bounded_ged
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

    @needs_bounded_ged
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
    @needs_bounded_ged
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


class TestTheFrozenResourcePolicy:
    """S21D2-031: revision 2 is a policy, not a set of numbers passed around by hand."""

    def test_it_matches_the_hash_the_pre_registration_recorded(self) -> None:
        """The bundle froze a hash before any D2 measurement existed; this is that object."""
        assert (
            GRAPH_RESOURCE_POLICY_REVISION_2.content_hash == GRAPH_RESOURCE_POLICY_REVISION_2_HASH
        )

    def test_only_the_shortlist_and_the_pair_timeout_moved(self) -> None:
        """Node, edge, depth, budget, result and neighbour bounds are revision 1's."""
        default = GraphResourceLimits()
        frozen = GRAPH_RESOURCE_POLICY_REVISION_2

        assert frozen.vector_shortlist == 20
        assert frozen.per_pair_ged_timeout_ms == 90
        assert frozen.nodes_per_graph == default.nodes_per_graph
        assert frozen.edges_per_graph == default.edges_per_graph
        assert frozen.path_depth == default.path_depth
        assert frozen.returned_results == default.returned_results
        assert frozen.query_budget_seconds == default.query_budget_seconds
        assert frozen.cross_task_similarity_neighbors == default.cross_task_similarity_neighbors

    def test_the_defaults_did_not_move_with_it(self) -> None:
        """Sprint 21D1's stored results were produced under the defaults and must stay valid."""
        assert GraphResourceLimits().vector_shortlist == 10
        assert GraphResourceLimits().per_pair_ged_timeout_ms == 250

    @pytest.mark.asyncio
    async def test_every_result_carries_the_policy_it_was_produced_under(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """A number without its policy is a number nobody can compare against another one."""
        result = await graph_retrieval.minilm_vector(
            query, pool, limits=GRAPH_RESOURCE_POLICY_REVISION_2, embed=embed
        )

        assert result.limits.content_hash == GRAPH_RESOURCE_POLICY_REVISION_2_HASH

    @needs_bounded_ged
    @pytest.mark.asyncio
    async def test_a_comparison_never_starts_unless_its_timeout_is_reserved(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """The budget is a budget only if a comparison cannot start and then overrun it.

        With a one-second budget and a per-pair timeout of a full second, no comparison can
        both start and finish inside the budget, so every shortlisted pair must be cut off
        rather than one being allowed to start at the last moment and run its whole timeout.
        """
        limits = GraphResourceLimits(
            vector_shortlist=20,
            returned_results=10,
            per_pair_ged_timeout_ms=1000,
            query_budget_seconds=1,
        )

        result = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )

        # S21D3-040: a cutoff is not a timeout. Nothing here ran long enough to expire; the
        # budget refused to start twenty comparisons, and the field says which happened.
        assert result.budget_cutoffs == result.candidates_considered == 20
        assert result.timed_out == 0

    @needs_bounded_ged
    @pytest.mark.asyncio
    async def test_an_incomplete_comparison_is_counted_rather_than_dropped(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """A cut-off pair keeps its shortlist place. Omitting it would shrink the denominator."""
        limits = GraphResourceLimits(
            vector_shortlist=20,
            returned_results=10,
            per_pair_ged_timeout_ms=1000,
            query_budget_seconds=1,
        )

        result = await graph_retrieval.bounded_ged(
            query, pool, _graph(999), limits=limits, embed=embed
        )

        assert result.candidates_considered == 20
        assert len(result.entries) == 10
        assert result.timed_out + result.budget_cutoffs > 0


class TestTheFixedReciprocalRankFusionArm:
    """S21D3-041: two frozen rank lists, equal weights, constant sixty, one truncation."""

    @staticmethod
    def _expected(
        lexical_order: list[str], vector_order: list[str], pair_ids: list[str]
    ) -> list[str]:
        """The frozen formula, evaluated from the contract rather than from the arm.

        `CorrectionRetrievalProtocolV3.fused_score` is what S21D3-016 published, exact
        Decimals and all. Deriving the expectation from it makes this an oracle instead of
        a restatement of `reciprocal_rank_fusion`'s own arithmetic.
        """
        from cognitive_os.learning.correction_protocol import CorrectionRetrievalProtocolV3

        protocol = CorrectionRetrievalProtocolV3()
        lexical_rank = {pair_id: rank for rank, pair_id in enumerate(lexical_order, start=1)}
        vector_rank = {pair_id: rank for rank, pair_id in enumerate(vector_order, start=1)}
        scored = [
            (
                pair_id,
                protocol.fused_score(lexical_rank.get(pair_id), vector_rank.get(pair_id)),
            )
            for pair_id in pair_ids
        ]
        return [
            pair_id
            for pair_id, score in sorted(scored, key=lambda item: (-item[1], item[0]))
            if score > 0
        ]

    def test_the_frozen_test_vector_orders_b_then_a_then_c(self) -> None:
        """The exact example S21D3-016 published, including the arm-missing document."""
        assert self._expected(["a", "b"], ["b", "c", "a"], ["a", "b", "c"]) == ["b", "a", "c"]

    @pytest.mark.asyncio
    async def test_the_published_order_is_the_fusion_of_both_complete_rank_lists(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Ranks come from the whole pool, not from either arm's top ten."""
        limits = GraphResourceLimits(returned_results=10)
        lexical_order = [
            pair_id
            for pair_id, score in graph_retrieval._ranked(
                graph_retrieval._lexical_scores(query, pool)
            )
            if score > 0
        ]
        vector_order = [
            pair_id
            for pair_id, _ in graph_retrieval._ranked(
                await graph_retrieval._vector_scores(query, pool, embed=embed)
            )
        ]

        fused = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=limits, embed=embed
        )

        expected = self._expected(lexical_order, vector_order, [c.pair_id for c in pool])
        assert [entry.pair_id for entry in fused.entries] == expected[:10]
        assert len(vector_order) == POOL_SIZE
        assert fused.candidates_considered == POOL_SIZE

    @pytest.mark.asyncio
    async def test_a_document_no_lexical_score_reached_is_ranked_by_the_other_arm_alone(
        self,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Missing membership contributes zero. It does not contribute a last place."""
        query = ExperienceGraphQuery(
            query_id="query-002",
            query_text="wholly unrelated vocabulary nothing shares",
            domain="coding",
            task_signature="signature-999",
            excluded_groups=("group-999",),
        )
        limits = GraphResourceLimits(returned_results=10)

        assert all(score == 0.0 for _, score in graph_retrieval._lexical_scores(query, pool))

        fused = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=limits, embed=embed
        )
        vector = await graph_retrieval.minilm_vector(query, pool, limits=limits, embed=embed)

        assert [e.pair_id for e in fused.entries] == [e.pair_id for e in vector.entries]
        assert fused.entries[0].score == f"{1 / (graph_retrieval.FUSION_CONSTANT + 1):.6f}"

    @pytest.mark.asyncio
    async def test_ties_fall_back_to_the_pair_id_order_every_arm_shares(
        self, embed: DeterministicEmbedding
    ) -> None:
        """Two candidates with one text hold one rank pair, so only the id can separate them."""
        shared = _graph(1).search_text()
        pool = tuple(
            Candidate(
                pair_id=pair_id,
                group=f"group-{pair_id}",
                domain="coding",
                task_signature="signature-shared",
                text=shared,
                graph=_graph(1),
            )
            for pair_id in ("pair-b", "pair-a")
        )
        query = ExperienceGraphQuery(
            query_id="query-003",
            query_text=shared,
            domain="coding",
            task_signature="signature-query",
            excluded_groups=("group-query",),
        )

        fused = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=GraphResourceLimits(), embed=embed
        )

        assert [entry.pair_id for entry in fused.entries] == ["pair-a", "pair-b"]

    @pytest.mark.asyncio
    async def test_the_output_is_truncated_once_and_only_after_fusion(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Both inputs see thirty candidates; the caller sees ten. §4.6's single truncation."""
        limits = GraphResourceLimits(returned_results=10)

        fused = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=limits, embed=embed
        )
        wider = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=GraphResourceLimits(returned_results=20), embed=embed
        )

        assert len(fused.entries) == 10
        assert len(wider.entries) == 20
        # Widening the output must not reorder it: a second truncation before fusion would.
        assert [e.pair_id for e in wider.entries][:10] == [e.pair_id for e in fused.entries]

    @pytest.mark.asyncio
    async def test_the_input_arms_keep_their_own_evidence_identities(
        self,
        query: ExperienceGraphQuery,
        pool: tuple[Candidate, ...],
        embed: DeterministicEmbedding,
    ) -> None:
        """Fusion publishes its own arm name and leaves the comparators' results alone."""
        limits = GraphResourceLimits(returned_results=10)

        fused = await graph_retrieval.reciprocal_rank_fusion(
            query, pool, limits=limits, embed=embed
        )
        vector = await graph_retrieval.minilm_vector(query, pool, limits=limits, embed=embed)
        lexical = graph_retrieval.lexical(query, pool, limits=limits)

        assert fused.arm == graph_retrieval.RECIPROCAL_RANK_FUSION
        assert vector.arm == graph_retrieval.MINILM_VECTOR
        assert lexical.arm == graph_retrieval.LEXICAL
        assert {entry.arm for entry in fused.entries} == {graph_retrieval.RECIPROCAL_RANK_FUSION}
        assert fused.timed_out == fused.budget_cutoffs == 0
