# Deterministic hybrid retrieval

Hybrid means fusion of exact ranked lists: PostgreSQL full text, exact pgvector cosine, bounded
relational graph traversal, recency, metadata lookup, and repository/workspace search. It does not
mean approximate or learned retrieval.

Profile `context-rrf-v1` uses one-based weighted Reciprocal Rank Fusion with `k=60`, followed by
explicit trust, scope, verification, recency, salience, graph, and contradiction modifiers. Decimal
scores are quantized to nine places and canonical candidate ID breaks ties. Every contribution is
stored in the trace.

Exact source identity merges lexical/vector or semantic/graph routes. Exact equal content within the
same scope keeps the more authoritative source and all secondary provenance. Wiki renderings merge
through exact claim lineage; the claim revision remains authoritative. Different scopes never merge.

Selection greedily places required and pinned items, then evidence, recent, source-diverse, and
remaining ranked items under per-source, item, hydration, byte, and token limits. Relevant disputed
counterparts remain visible when they fit. Required content that cannot fit fails closed.

The optional no-op reranker tests the adapter contract. A local CrossEncoder may be loaded from an
absolute preconfigured path on CPU with a recorded model digest and no download. It is not enabled
without a versioned benchmark promotion decision. RAGatouille remains rejected as an unmeasured
experiment.

## ANN and migration decision

Outcome: `defer`. Exact search remains the only baseline. The Sprint 10 10,000-claim relational
scale artifact reports bounded query plans and no ANN index; the Sprint 11 exact functional suite
does not establish a vector-latency need. HNSW, IVFFlat, and Alembic `0004` therefore remain absent.
Reconsider only after an isolated 10,000-or-larger exact-vector context workload records p50/p95,
recall, database size, and plans showing a measured failure. No performance claim is made from the
credential-free fixture.

See [ADR 0039](../adr/0039-deterministic-hybrid-ranking.md).
