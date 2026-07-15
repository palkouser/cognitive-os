# Cognitive OS roadmap status

Sprint 9 Governed Memory Plane v1 and Sprint 10 Temporal Semantic Memory and LLM Wiki v3 form Gate
C, the persistent cognitive substrate. Sprint 10 is implemented on
`feature/sprint-10-temporal-semantic-memory`; its baseline tag is created only after merge and green
remote CI.

LLM Wiki is a concept specification implemented as a deterministic derived projection. Graphiti is
an algorithm and temporal-memory reference donor, Cognee is an ingestion and graph reference, and
NetworkX is an optional narrow analytical dependency. None is authoritative.

Sprint 11 remains responsible for Context Builder, candidate generation, hybrid fusion,
deduplication, reranking, temporal filtering, context budgets, progressive disclosure, retrieval
traces, and provider-specific context bundles. It consumes Sprint 9 and Sprint 10 read contracts
without replacing their persistence or automatically granting provider write authority.
