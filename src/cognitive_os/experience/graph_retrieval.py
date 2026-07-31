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

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from math import sqrt
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


def _result(
    query: ExperienceGraphQuery,
    arm: str,
    scored: Sequence[tuple[str, float]],
    *,
    considered: int,
    limits: GraphResourceLimits,
    timed_out: int = 0,
) -> ExperienceGraphResult:
    """Rank, break ties by pair id, and truncate to the declared bound."""
    ordered = sorted(scored, key=lambda item: (-item[1], item[0]))[: limits.returned_results]
    return ExperienceGraphResult(
        query_id=query.query_id,
        arm=arm,
        entries=tuple(
            ExperienceGraphResultEntry(pair_id=pair_id, rank=index, score=f"{score:.6f}", arm=arm)
            for index, (pair_id, score) in enumerate(ordered, start=1)
        ),
        candidates_considered=considered,
        timed_out=timed_out,
        limits=limits,
    )


def no_memory(query: ExperienceGraphQuery, *, limits: GraphResourceLimits) -> ExperienceGraphResult:
    """The floor. It returns nothing, and that is a result, not a failure."""
    return _result(query, NO_MEMORY, (), considered=0, limits=limits)


def lexical(
    query: ExperienceGraphQuery, pool: Sequence[Candidate], *, limits: GraphResourceLimits
) -> ExperienceGraphResult:
    """Jaccard overlap on tokens. No index, no dependency, deterministic ties."""
    wanted = _tokens(query.query_text)
    scored = []
    for candidate in pool:
        tokens = _tokens(candidate.text)
        union = wanted | tokens
        scored.append((candidate.pair_id, len(wanted & tokens) / len(union) if union else 0.0))
    return _result(query, LEXICAL, scored, considered=len(pool), limits=limits)


def exact_signature(
    query: ExperienceGraphQuery, pool: Sequence[Candidate], *, limits: GraphResourceLimits
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


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm = sqrt(sum(a * a for a in left)) * sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


async def minilm_vector(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    *,
    limits: GraphResourceLimits,
    embed: EmbeddingProviderPort,
) -> ExperienceGraphResult:
    """Frozen MiniLM cosine ranking. A missing or wrong model must fail, never fall back.

    `embed` is the provider built by `build_embedding_provider`, which raises when the
    local model is unusable and never substitutes the hashing provider. Depending on
    that is what keeps a benchmark number from silently describing a hash.
    """
    query_vector = await embed.embed_query(query.query_text)
    candidate_vectors = await embed.embed_documents(tuple(c.text for c in pool))
    scored = [
        (candidate.pair_id, _cosine(query_vector, vector))
        for candidate, vector in zip(pool, candidate_vectors, strict=True)
    ]
    return _result(query, MINILM_VECTOR, scored, considered=len(pool), limits=limits)


async def bounded_ged(
    query: ExperienceGraphQuery,
    pool: Sequence[Candidate],
    query_graph: ActionDecisionGraph,
    *,
    limits: GraphResourceLimits,
    embed: EmbeddingProviderPort,
) -> ExperienceGraphResult:
    """MiniLM shortlist, then labelled graph edit distance with a per-pair timeout.

    The score is a similarity in [0, 1] derived from the edit distance normalised by the
    larger graph, so it composes with the other arms. A pair that exhausts its timeout
    keeps its shortlist position and is counted, which is the bounded result the resource
    policy requires instead of a silent omission.
    """
    import networkx as nx  # type: ignore[import-untyped]

    shortlist_result = await minilm_vector(query, pool, limits=limits, embed=embed)
    shortlist_ids = [entry.pair_id for entry in shortlist_result.entries][: limits.vector_shortlist]
    by_id = {candidate.pair_id: candidate for candidate in pool}

    left = _as_nx(query_graph)
    scored: list[tuple[str, float]] = []
    timed_out = 0
    for pair_id in shortlist_ids:
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
    )


def _as_nx(graph: ActionDecisionGraph) -> Any:
    import networkx as nx

    converted = nx.DiGraph()
    for node in graph.nodes:
        converted.add_node(node.logical_id, label=node.label)
    for edge in graph.edges:
        converted.add_edge(edge.source_id, edge.target_id, label=edge.kind.value)
    return converted


def reciprocal_rank(result: ExperienceGraphResult, relevant: str) -> Decimal:
    """MRR contribution of one query, zero when the relevant pair was not returned."""
    for entry in result.entries:
        if entry.pair_id == relevant:
            return Decimal(1) / Decimal(entry.rank)
    return Decimal(0)


def recall_at(result: ExperienceGraphResult, relevant: str, *, k: int) -> int:
    return int(any(e.pair_id == relevant for e in result.entries[:k]))
