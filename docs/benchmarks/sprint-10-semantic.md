# Sprint 10 semantic benchmarks

The four-case CI and twenty-case seed manifests execute credential-free semantic domain checks
through the existing benchmark runner. Cases cover grounding and rejection, duplicate identity,
promotion prerequisites, provider-policy rejection, temporal succession and overlap, valid and
system time, retraction, relation integrity, contradiction handling, and current or historical Wiki
lineage.

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
Safety counters are mandatory. PostgreSQL migration, projection, audit, concurrency, health, and
lineage behavior are covered by the adjacent PostgreSQL integration and smoke gates; benchmark
cases need no external model or dataset.

The optional 10,000-claim scale workload remains a local P1 measurement, not a merge gate. Any
published scale result must include p50/p95 latency, database size, query plans, and exact workload
counts; no result is claimed until that workload is run on identified hardware.
