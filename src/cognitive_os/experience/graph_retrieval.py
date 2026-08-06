"""Bounded retrieval over the Experience Memory Graph, one arm per comparator.

Every arm sees the same candidate pool, the same group exclusions and the same resource
policy, so a difference between two arms is a difference in ranking and nothing else.
The graph arm never reads an outcome label or a correction byte from the query's group;
the pool is filtered before any arm runs, not inside one.

Graph edit distance is NP-hard, which is why the graph arm is a *reranker* over a
shortlist and never a full-corpus scan, and why every pair comparison carries a timeout
whose expiry is recorded as a bounded result rather than retried or silently dropped.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import log2, sqrt
from time import perf_counter
from typing import Any

from cognitive_os.application.ports.embedding_provider import EmbeddingProviderPort
from cognitive_os.domain.experience_graph import (
    ActionDecisionGraph,
    ExperienceGraphQuery,
    ExperienceGraphResult,
    ExperienceGraphResultEntry,
    FailedSuccessGraphPair,
    GraphResourceLimits,
)

NO_MEMORY = "no_memory"
LEXICAL = "lexical"
EXACT_SIGNATURE = "exact_signature"
MINILM_VECTOR = "minilm_vector"
BOUNDED_GED = "minilm_shortlist_plus_bounded_ged"
RECIPROCAL_RANK_FUSION = "reciprocal_rank_fusion"

#: S21D3-016 froze it before the holdout existed: exactly two arms, equal weights, constant
#: sixty. It is a module constant rather than a parameter because a fusion constant a caller
#: can pass is a sweep, and revision 3 forbids one.
FUSION_CONSTANT = 60


@dataclass(frozen=True, slots=True)
class Candidate:
    """One retrievable pair, reduced to what an arm may see."""

    pair_id: str
    group: str
    domain: str
    task_signature: str
    text: str
    graph: ActionDecisionGraph


def candidates_from(pairs: Sequence[FailedSuccessGraphPair]) -> tuple[Candidate, ...]:
    """The successful side is what a repair request wants; the failed side is the query."""
    return tuple(
        Candidate(
            pair_id=pair.pair_id,
            group=pair.group,
            domain=pair.domain,
            task_signature=pair.task_signature,
            text=pair.successful.search_text(),
            graph=pair.successful,
        )
        for pair in pairs
    )


def eligible_pool(
    candidates: Sequence[Candidate], query: ExperienceGraphQuery
) -> tuple[Candidate, ...]:
    """Group exclusion happens once, before any arm sees the pool."""
    excluded = set(query.excluded_groups)
    return tuple(c for c in candidates if c.group not in excluded)


def _tokens(text: str) -> set[str]:
    return {token for token in text.lower().replace("=", " ").split() if len(token) > 2}


def _ranked(scored: Sequence[tuple[str, float]]) -> list[tuple[str, float]]:
    """Descending score, ties broken by pair id. The one ordering every arm shares."""
    return sorted(scored, key=lambda item: (-item[1], item[0]))


def _result(
    query: ExperienceGraphQuery,
    arm: str,
    scored: Sequence[tuple[str, float]],
    *,
    considered: int,
    limits: GraphResourceLimits,
    timed_out: int = 0,
    budget_cutoffs: int = 0,
) -> ExperienceGraphResult:
    """Rank, break ties by pair id, and truncate to the declared bound."""
    ordered = _ranked(scored)[: limits.returned_results]
    return ExperienceGraphResult(
        query_id=query.query_id,
        arm=arm,
        entries=tuple(
            ExperienceGraphResultEntry(pair_id=pair_id, rank=index, score=f"{score:.6f}", arm=arm)
            for index, (pair_id, score) in enumerate(ordered, start=1)
        ),
        candidates_considered=considered,
        timed_out=timed_out,
        budget_cutoffs=budget_cutoffs,
        limits=limits,
    )


def no_memory(query: ExperienceGraphQuery, *, limits: GraphResourceLimits) -> ExperienceGraphResult:
    """The floor. It returns nothing, and that is a result, not a failure."""
    return _result(query, NO_MEMORY, (), considered=0, limits=limits)


def _lexical_scores(
    query: ExperienceGraphQuery, pool: Sequence[Candidate]
) -> list[tuple[str, float]]:
    """Jaccard overlap over the whole pool. Untruncated, like `_vector_scores`.

    Fusion needs the rank a document holds in the *complete* lexical ordering, and a scorer
    that truncated would hand it ranks from a top-ten list instead.
    """
    wanted = _tokens(query.query_text)
    scored = []
    for candidate in pool:
        tokens = _tokens(candidate.text)
        union = wanted | tokens
        scored.append((candidate.pair_id, len(wanted & tokens) / len(union) if union else 0.0))
    return scored


def lexical(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    limits: GraphResourceLimits,
) -> ExperienceGraphResult:
    """Jaccard overlap on tokens. No index, no dependency, deterministic ties."""
    return _result(
        query,
        LEXICAL,
        _lexical_scores(query, pool),
        considered=len(pool),
        limits=limits,
    )


def exact_signature(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    limits: GraphResourceLimits,
) -> ExperienceGraphResult:
    """Task-signature equality. Precise where it fires, silent everywhere else."""
    scored = [(c.pair_id, 1.0 if c.task_signature == query.task_signature else 0.0) for c in pool]
    return _result(
        query,
        EXACT_SIGNATURE,
        [item for item in scored if item[1] > 0],
        considered=len(pool),
        limits=limits,
    )


#: The provider refuses a batch above its configured maximum, and the candidate pool is
#: larger than that once the corpus grows past a handful of groups. Chunking here keeps
#: the arm working on a real pool instead of failing on the 65th candidate.
_EMBED_BATCH = 64


async def _embed_all(
    embed: EmbeddingProviderPort,
    texts: Sequence[str],
    cache: dict[str, tuple[float, ...]] | None = None,
) -> tuple[tuple[float, ...], ...]:
    """Embed in provider-sized batches, reusing anything the caller already has.

    Candidate texts do not change between queries, so re-embedding the whole pool once
    per query is pure waste — and it was the single largest latency component, roughly
    936 ms of the graph arm's 940 ms median. The cache is the caller's, so a benchmark
    can share it across queries while a one-off call stays stateless.
    """
    if cache is None:
        cache = {}
    missing = [text for text in dict.fromkeys(texts) if text not in cache]
    for start in range(0, len(missing), _EMBED_BATCH):
        chunk = tuple(missing[start : start + _EMBED_BATCH])
        for text, vector in zip(chunk, await embed.embed_documents(chunk), strict=True):
            cache[text] = vector
    return tuple(cache[text] for text in texts)


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


async def _vector_scores(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    embed: EmbeddingProviderPort,
    cache: dict[str, tuple[float, ...]] | None = None,
) -> list[tuple[str, float]]:
    """Cosine-score the whole pool. Untruncated on purpose.

    Truncation belongs to whoever publishes a result, not to scoring. `bounded_ged` used
    to shortlist from `minilm_vector`'s public result, which `_result` had already cut to
    `returned_results` — so `vector_shortlist=20` with `returned_results=10` sent ten
    candidates to the reranker and the wider shortlist was never actually applied.
    """
    query_vector = await embed.embed_query(query.query_text)
    candidate_vectors = await _embed_all(embed, tuple(c.text for c in pool), cache)
    return [
        (candidate.pair_id, _cosine(query_vector, vector))
        for candidate, vector in zip(pool, candidate_vectors, strict=True)
    ]


async def minilm_vector(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    limits: GraphResourceLimits,
    embed: EmbeddingProviderPort,
    cache: dict[str, tuple[float, ...]] | None = None,
) -> ExperienceGraphResult:
    """Frozen MiniLM cosine ranking. A missing or wrong model must fail, never fall back.

    `embed` is the provider built by `build_embedding_provider`, which raises when the
    local model is unusable and never substitutes the hashing provider. Depending on
    that is what keeps a benchmark number from silently describing a hash.
    """
    scored = await _vector_scores(query, pool, embed=embed, cache=cache)
    return _result(query, MINILM_VECTOR, scored, considered=len(pool), limits=limits)


def _ranks(scored: Sequence[tuple[str, float]]) -> dict[str, int]:
    """Pair id to its one-based position in the shared ordering."""
    return {pair_id: rank for rank, (pair_id, _) in enumerate(_ranked(scored), start=1)}


async def reciprocal_rank_fusion(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    limits: GraphResourceLimits,
    embed: EmbeddingProviderPort,
    cache: dict[str, tuple[float, ...]] | None = None,
) -> ExperienceGraphResult:
    """Equal-weight RRF over the lexical and MiniLM rank lists. S21D3-041.

    `1/(60 + rank_lexical) + 1/(60 + rank_vector)`, and the two ranks come from the complete
    pool rather than from either arm's published top ten — fusing truncated lists would rank
    by whatever survived truncation, which is a different arm than the one that was frozen.

    A zero-score lexical document is *absent* from the lexical ranking rather than last in it.
    Jaccard returns zero for every candidate sharing no token with the query, and ordering
    those by pair id would turn an identifier into evidence. Absence contributes zero, so such
    a document is ranked by the vector arm alone.

    This calls the two scorers; it does not call `lexical` or `minilm_vector`. Those publish
    results under their own arm names, and an evidence identity is not something a fusion gets
    to reuse.
    """
    lexical_ranks = _ranks([item for item in _lexical_scores(query, pool) if item[1] > 0])
    vector_ranks = _ranks(await _vector_scores(query, pool, embed=embed, cache=cache))
    scored = [
        (
            candidate.pair_id,
            sum(
                1 / (FUSION_CONSTANT + rank)
                for rank in (
                    lexical_ranks.get(candidate.pair_id),
                    vector_ranks.get(candidate.pair_id),
                )
                if rank is not None
            ),
        )
        for candidate in pool
    ]
    # `_result` truncates once, here, after the full-pool fusion. That is the single output
    # limit revision 3 declares.
    return _result(
        query,
        RECIPROCAL_RANK_FUSION,
        [item for item in scored if item[1] > 0],
        considered=len(pool),
        limits=limits,
    )


async def bounded_ged(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    query_graph: ActionDecisionGraph,
    *,
    limits: GraphResourceLimits,
    embed: EmbeddingProviderPort,
    cache: dict[str, tuple[float, ...]] | None = None,
) -> ExperienceGraphResult:
    """MiniLM shortlist, then labelled graph edit distance with a per-pair timeout.

    The score is a similarity in [0, 1] derived from the edit distance normalised by the
    larger graph, so it composes with the other arms. A pair that exhausts its timeout
    keeps its shortlist position and is counted, which is the bounded result the resource
    policy requires instead of a silent omission.
    """
    import networkx as nx  # type: ignore[import-untyped]

    started = perf_counter()
    scores = await _vector_scores(query, pool, embed=embed, cache=cache)
    shortlist_ids = [pair_id for pair_id, _ in _ranked(scores)[: limits.vector_shortlist]]
    by_id = {candidate.pair_id: candidate for candidate in pool}

    left = _as_nx(query_graph)
    scored: list[tuple[str, float]] = []
    timed_out = 0
    cut_off = 0
    for pair_id in shortlist_ids:
        # The declared per-pair timeout multiplied by the shortlist length already exceeds
        # the total query budget, so the budget has to be enforced here as well or the
        # arm silently overruns it. A pair the budget cuts off keeps its shortlist
        # position at the fallback score and is counted, exactly like a per-pair timeout.
        # Reserve the per-pair timeout, not just the elapsed time. Checking only elapsed
        # lets a comparison start at the last moment and still run its full timeout, which
        # overshoots the budget by up to that timeout and is not a budget at all.
        remaining = limits.query_budget_seconds - (perf_counter() - started)
        if remaining <= limits.per_pair_ged_timeout_ms / 1000:
            cut_off += 1
            scored.append((pair_id, 0.0))
            continue
        right = _as_nx(by_id[pair_id].graph)
        ceiling = max(left.number_of_nodes(), right.number_of_nodes()) + max(
            left.number_of_edges(), right.number_of_edges()
        )
        distance = nx.graph_edit_distance(
            left,
            right,
            node_match=lambda a, b: a["label"] == b["label"],
            edge_match=lambda a, b: a["label"] == b["label"],
            timeout=limits.per_pair_ged_timeout_ms / 1000,
            upper_bound=ceiling,
        )
        if distance is None:
            timed_out += 1
            scored.append((pair_id, 0.0))
        else:
            scored.append((pair_id, max(0.0, 1.0 - distance / ceiling) if ceiling else 1.0))
    return _result(
        query,
        BOUNDED_GED,
        scored,
        considered=len(shortlist_ids),
        limits=limits,
        timed_out=timed_out,
        budget_cutoffs=cut_off,
    )


def _as_nx(graph: ActionDecisionGraph) -> Any:
    import networkx as nx

    converted = nx.DiGraph()
    for node in graph.nodes:
        converted.add_node(node.logical_id, label=node.label)
    for edge in graph.edges:
        converted.add_edge(edge.source_id, edge.target_id, label=edge.kind.value)
    return converted


def reciprocal_rank(result: ExperienceGraphResult, relevant: Collection[str]) -> Decimal:
    """Rank of the first relevant pair, zero when none was returned."""
    for entry in result.entries:
        if entry.pair_id in relevant:
            return Decimal(1) / Decimal(entry.rank)
    return Decimal(0)


def recall_at(result: ExperienceGraphResult, relevant: Collection[str], *, k: int) -> int:
    """Whether any relevant pair appears in the top k. Binary, so a query counts once."""
    return int(any(entry.pair_id in relevant for entry in result.entries[:k]))


def ndcg_at(result: ExperienceGraphResult, relevant: Collection[str], *, k: int) -> Decimal:
    """Binary-gain nDCG, normalised by the best achievable ordering for this query.

    Normalising by `min(len(relevant), k)` rather than by `k` keeps a query with two
    relevant pairs from being scored against an ideal it could never reach.
    """
    gain = sum(
        1 / log2(index + 1)
        for index, entry in enumerate(result.entries[:k], start=1)
        if entry.pair_id in relevant
    )
    ideal = sum(1 / log2(index + 1) for index in range(1, min(len(relevant), k) + 1))
    return Decimal(f"{gain / ideal:.6f}") if ideal else Decimal(0)
