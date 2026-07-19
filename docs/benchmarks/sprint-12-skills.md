# Sprint 12 Skill Engine benchmarks

The eight-case CI manifest and 32-case seed manifest are credential-free deterministic replay
fixtures. They cover package integrity, lifecycle chains, selection stability, scope, sensitivity,
permissions, Context hydration, Controller reuse, verification, statistics, access audit, backup,
and replay.

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint12-skill-ci.yaml \
  --mode skill-replay \
  --report-directory .pytest_cache/sprint12-skill-benchmark
```

The gate requires all cases to pass with zero scope leaks, sensitivity leaks, and permission
expansions. The exact baseline remains dependency-light and does not download models or use a GPU.

The isolated PostgreSQL scale baseline populated 1,000 identities, 5,000 revisions, 20,000
requirements, 10,000 executions, 100,000 execution steps, and 100,000 accesses. Across 30 measured
iterations, p95 latency ranged from 0.515 ms for candidate lookup to 2.682 ms for statistics
rebuild; registry load p95 was 2.655 ms. Skill relations occupied 55,058,432 bytes. Exact counts,
environment data, and query plans are in `sprint-12-scale-baseline.json`.
