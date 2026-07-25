# Memory Plane configuration

Copy `config/memory.example.yaml` to a host-private configuration path. Unknown fields fail
validation. The example defines inline/search/source/revision/query/vector/batch/worker limits,
allowed types and scopes, sensitivity ceiling, access-audit behavior, export root, and benchmark
limits.

Deterministic embeddings need no optional ML package. A Sentence Transformers provider requires
an absolute preconfigured local directory and artifact digest. Missing models fail as unavailable;
health checks never download. Network model download stays sealed to false.

## Approximate vector retrieval

`approximate_vector_index_dimensions` is empty by default, which keeps every vector search
exhaustive — the Sprint 9 behavior. Listing a dimension permits callers to issue
`MemoryRetrievalMode.VECTOR_APPROXIMATE` for that dimension; exact search remains available
and unchanged, and no caller receives approximate results without asking for them. The
recorded `retrieval_mode` distinguishes the two for the life of the audit row.

A dimension is only permitted if migration 0013 created its index and a configured embedding
provider produces it. pgvector cannot index above 2 000 dimensions at all, so wider
embeddings stay exhaustive-only. See
[ADR 0082](../adr/0082-approximate-vector-retrieval-and-capacity-envelope.md), and measure a
deployment with `scripts/memory_ann_baseline.py`.

Install PostgreSQL support with `uv sync --extra memory-postgres`. Install local model support
separately with `uv sync --extra local-embeddings`; this extra is not needed for core, PostgreSQL,
CI, deterministic embeddings, or exact-vector tests.
