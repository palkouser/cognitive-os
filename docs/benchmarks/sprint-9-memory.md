# Sprint 9 memory benchmarks

Credential-free fixtures use fixed UUIDs, timestamps, accepted trajectories, corrections,
candidate/verified/retracted states, and deterministic 64-dimensional hashing vectors. Expected
metadata, text, exact-vector, scope, sensitivity, revision, and audit results are declared rather
than judged by a model.

Safety metrics are provenance completeness, scope leaks, sensitivity leaks, and unexplained audit
gaps; every value must be zero except provenance completeness, which must be one. Retrieval reports
Recall@k, MRR, and latency without describing deterministic hashes as semantic quality. Local scale
measurement is exact-only and records corpus size, p50/p95 latency, storage size, and query plans.
LongMemEval and MemoryAgentBench imports are local-file compatibility paths only and are excluded
from normal CI.
