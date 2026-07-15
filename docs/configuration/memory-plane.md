# Memory Plane configuration

Copy `config/memory.example.yaml` to a host-private configuration path. Unknown fields fail
validation. The example defines inline/search/source/revision/query/vector/batch/worker limits,
allowed types and scopes, sensitivity ceiling, access-audit behavior, export root, and benchmark
limits.

Deterministic embeddings need no optional ML package. A Sentence Transformers provider requires
an absolute preconfigured local directory and artifact digest. Missing models fail as unavailable;
health checks never download. Network model download and approximate vector indexes are sealed to
false in Sprint 9.

Install PostgreSQL support with `uv sync --extra memory-postgres`. Install local model support
separately with `uv sync --extra local-embeddings`; this extra is not needed for core, PostgreSQL,
CI, deterministic embeddings, or exact-vector tests.
