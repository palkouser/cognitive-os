# Sprint 14 Experience Compiler benchmarks

The CI manifest contains 12 credential-free cases covering success, repair, failure, cancellation,
incomplete history, stale evidence, verifier conflict, first-incorrect ambiguity, provider evidence,
candidate authority, idempotency, and manifest regeneration. The seed manifest contains 48 cases
distributed across source validation, reconstruction, segmentation, assessment, paths, contribution,
generalizability, candidate generation, and security.

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint14-experience-ci.yaml \
  --mode experience-replay --report-directory .cache/benchmarks/sprint14-ci --seed 14
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint14-experience-seed.yaml \
  --mode experience-replay --report-directory .cache/benchmarks/sprint14-seed --seed 14
```

Metrics retain raw accuracy, latency, artifact-size, provenance, idempotency, scope, sensitivity,
automatic-promotion, destination-write, and access-audit values. A passing benchmark requires exact
deterministic manifests and zero governance violations; it does not claim causal or model superiority.
