# Sprint 10 semantic benchmarks

The four-case CI and twenty-case seed manifests execute credential-free semantic domain checks
through the existing benchmark runner. Cases cover grounding and rejection, duplicate identity,
promotion prerequisites, provider proposal and commit rejection, temporal succession and overlap,
valid and system time, retraction, relation integrity, critical contradiction handling, and current
or historical Wiki lineage.

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint10-semantic-ci.yaml \
  --mode semantic-replay --report-directory /tmp/sprint10-semantic-ci
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint10-semantic-seed.yaml \
  --mode semantic-replay --report-directory /tmp/sprint10-semantic-seed
```

Every case emits grounding, evidence, promotion, duplicate, contradiction precision/recall,
temporal, provenance, Wiki lineage, scope, sensitivity, future-leak, and operation-latency metrics.
Safety counters are mandatory. Every manifest case declares exact expected observation, claim,
revision, contradiction, and Wiki-page counts. Without a database URL the adapter runs the
credential-free deterministic domain checks. With `COGOS_DATABASE_URL` and
`COGOS_ARTIFACT_ROOT`, the same runner materializes stable case-isolated fixtures through the
PostgreSQL repository, compares the exact projections, records benchmark lifecycle events, and
stores the report as an artifact. Stable namespaced IDs make retries deterministic; the dedicated
test-database lifecycle owns cleanup. PostgreSQL integration also verifies this adapter against the
real repository. No case needs an external model or dataset.

The local P1 scale baseline is published in
[`sprint-10-scale-baseline.json`](sprint-10-scale-baseline.json). The deterministic isolated
PostgreSQL fixture contains 10,000 claims, 30,000 claim revisions, 50,000 evidence links, 10,000
relations, 1,000 contradictions, and 1,000 Wiki pages. On the recorded x86_64 Linux environment
with PostgreSQL 18.4 and Python 3.12.13, p95 latency was 0.236 ms for current lookup, 0.248 ms for
valid-at, 0.258 ms for known-at, 0.226 ms for evidence, 0.342 ms for contradictions, 0.225 ms for
Wiki regeneration inputs, and 1.393 ms for the bounded SQL plus NetworkX projection. The database
size was 73,692,863 bytes. All captured `EXPLAIN (FORMAT JSON)` plans used an index; no ANN index
or graph database was present.

Reproduce the measurement only against an isolated database whose name ends in `_test`:

```bash
uv run python scripts/semantic_scale_baseline.py --iterations 30
```
