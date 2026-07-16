# ADR 0039: Deterministic hybrid ranking

## Status

Accepted for Sprint 11.

## Decision

Ranking profile `context-rrf-v1` uses weighted Reciprocal Rank Fusion:

```text
rrf(candidate) = sum(retriever_weight / (60 + one_based_rank))
final = rrf + trust + scope + verification + recency + salience + graph - contradiction
```

Every contribution is host-owned, recorded in the score breakdown, and quantized to nine decimal
places. Missing routes contribute zero. Canonical candidate ID is the final tie-breaker. Exact source
identity is deduplicated before ranking; exact content deduplication prefers authoritative source
types while retaining secondary provenance and routes. Different scopes do not merge.

Selection is deterministic and greedy: required and pinned candidates first, then ranked candidates
subject to token budget, per-source caps, minimum source diversity, recent/evidence quotas, and
material contradiction visibility. A relevant disputed item is penalized and labelled, not silently
discarded.

For example, equal-weight candidates at ranks 1 and 2 receive `1/61 = 0.016393443` and
`1/62 = 0.016129032`; equal final scores sort by candidate ID. Identical inputs and profile hashes
therefore produce byte-identical order.

An optional reranker may return advisory ordering evidence only. It cannot modify candidates,
provenance, authority, filters, or the baseline score. Learned ranking and adaptive weights are not
implemented.

## Rejected alternatives

- Raw score blending is not comparable across source-specific retrievers.
- Floating-point accumulation without quantization is not replay-stable.
- Provider or learned ranking is not an authority boundary and lacks a deterministic baseline.

