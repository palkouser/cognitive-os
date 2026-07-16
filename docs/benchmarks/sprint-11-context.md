# Sprint 11 Context Builder benchmarks

The deterministic fixture uses stable UUIDs and timestamps for every source type, lexical/vector/
graph/recency/code routes, a duplicate Wiki lineage, a material contradiction, suspicious retrieved
text, exact source provenance, and an artifact-backed bundle. It needs no credential, model, network,
GPU, or PostgreSQL server.

The six-case CI manifest covers hybrid RRF, deduplication, token packing, contradiction visibility,
injection handling, and Controller attachment. The 32-case seed manifest additionally covers each
retrieval family, source diversity, temporal selectors, sensitivity, trace completeness, and replay.
Both assert the exact 13-candidate order, bundle hash, and trace hash.

Run:

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint11-context-ci.yaml \
  --mode context-replay --report-directory .tmp-benchmark-reports/context-ci
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint11-context-seed.yaml \
  --mode context-replay --report-directory .tmp-benchmark-reports/context-seed
```

Per-case metrics include Recall@k, Precision@k, MRR, nDCG, required/evidence coverage, token count,
budget utilization, latency, duplicate rate, contradiction visibility, source diversity, scope and
sensitivity leaks, unsafe inclusion, and trace completeness. Zero denominators are defined and all
safety metrics are mandatory. Fixture latency is reported but is not a PostgreSQL or production
performance claim.

LongMemEval and MemoryAgentBench compatibility remain local-file, optional, and non-blocking; no
external benchmark runtime or download is introduced.

