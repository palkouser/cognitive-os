"""Measured retrieval capacity: recall and latency against exhaustive ground truth.

Requirement 4 makes runtime scalability a criterion for choosing a learning method
rather than a target to hit later, so this module measures rather than asserts. A Tier A
non-parametric method depends entirely on retrieval, and its viability is decided by
numbers this harness produces.

Two things are measured together on purpose. Approximate latency on its own always looks
good — the index is fast precisely because it may skip the answer — so recall against the
exhaustive result is computed for the same queries, in the same corpus, and an envelope
that omits it is refused by the contract.

Recall is reported at the result limit rather than at the candidate limit. The repository
over-fetches candidates and then re-scores them exactly, so a true neighbour that the
index returned anywhere in the candidate set still lands in the right rank. Recall at the
candidate limit would understate the retrieval the caller actually sees.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from statistics import median, quantiles
from time import perf_counter
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from cognitive_os.application.ports.memory_repository import MemoryRepositoryPort
from cognitive_os.domain.common import utc_now
from cognitive_os.domain.learned import RetrievalCapacityEnvelope
from cognitive_os.domain.memory import (
    MemoryQuery,
    MemoryQueryBudget,
    MemoryRetrievalMode,
    MemoryVectorQuery,
)


def _percentile_95(values: Sequence[float]) -> float:
    if len(values) < 2:
        return values[0]
    return quantiles(values, n=20, method="inclusive")[18]


def _quantise(value: float) -> Decimal:
    return Decimal(f"{value:.3f}")


async def _timed_ids(
    repository: MemoryRepositoryPort,
    probe: MemoryVectorQuery,
    *,
    mode: MemoryRetrievalMode,
    budget: MemoryQueryBudget,
) -> tuple[tuple[UUID, ...], float]:
    query = MemoryQuery(query_id=uuid4(), mode=mode, vector=probe, budget=budget)
    started = perf_counter()
    page = await repository.search(query)
    elapsed_ms = (perf_counter() - started) * 1_000
    return tuple(result.memory_id for result in page.results), elapsed_ms


async def measure_capacity(
    repository: MemoryRepositoryPort,
    probes: Sequence[MemoryVectorQuery],
    *,
    mode: MemoryRetrievalMode,
    corpus_vector_count: int,
    budget: MemoryQueryBudget | None = None,
    ef_search: int | None = None,
    index_build_seconds: float | None = None,
    index_size_bytes: int | None = None,
    limitations: Sequence[str] = (),
) -> RetrievalCapacityEnvelope:
    """Measure one mode over one corpus, computing recall only where it can be wrong.

    For an approximate mode every probe is run twice — once approximately, once
    exhaustively — and recall is the mean overlap of the two result sets. The exhaustive
    run is the ground truth, so the measurement costs a full scan per probe by design;
    a cheaper reference would be a reference to nothing.
    """
    if not probes:
        raise ValueError("capacity measurement requires at least one probe")
    if not mode.is_vector:
        raise ValueError("capacity is measured for vector retrieval modes only")
    resolved_budget = budget or MemoryQueryBudget()
    approximate = mode is MemoryRetrievalMode.VECTOR_APPROXIMATE

    latencies: list[float] = []
    overlaps: list[float] = []
    for probe in probes:
        found, elapsed_ms = await _timed_ids(repository, probe, mode=mode, budget=resolved_budget)
        latencies.append(elapsed_ms)
        if not approximate:
            continue
        truth, _ = await _timed_ids(
            repository, probe, mode=MemoryRetrievalMode.VECTOR, budget=resolved_budget
        )
        if truth:
            overlaps.append(len(set(found) & set(truth)) / len(truth))

    recall = None
    if approximate:
        # No exhaustive result anywhere means recall is undefined, not perfect.
        if not overlaps:
            raise ValueError("recall is undefined: no probe returned an exhaustive result")
        recall = _quantise(sum(overlaps) / len(overlaps))

    if len({probe.dimension for probe in probes}) != 1:
        raise ValueError("one envelope covers one embedding dimension")
    dimension = probes[0].dimension

    return RetrievalCapacityEnvelope(
        envelope_id=uuid5(
            NAMESPACE_URL,
            f"capacity:{mode.value}:{dimension}:{corpus_vector_count}:{len(probes)}",
        ),
        retrieval_mode=mode.value,
        embedding_dimension=dimension,
        corpus_vector_count=corpus_vector_count,
        queries_measured=len(probes),
        result_limit=resolved_budget.maximum_results,
        candidate_limit=resolved_budget.maximum_candidates,
        latency_p50_ms=_quantise(median(latencies)),
        latency_p95_ms=_quantise(_percentile_95(latencies)),
        recall_at_result_limit=recall,
        index_build_seconds=(
            None if index_build_seconds is None else _quantise(index_build_seconds)
        ),
        index_size_bytes=index_size_bytes,
        ef_search=ef_search if approximate else None,
        limitations=tuple(limitations) or ("no limitation was declared by the caller",),
        created_at=utc_now(),
    )
