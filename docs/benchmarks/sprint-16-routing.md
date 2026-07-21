# Sprint 16 routing benchmarks

The credential-free CI gate runs 16 deterministic cases and the seed gate runs at least 64. They
cover capability registration, TaskSignatures, observation ingestion, statistics and uncertainty,
hard filtering, static and shadow routing, promotion denial and approval, fallback, multi-model
budgets, security, and replay hashes.

```bash
uv run python scripts/routing_benchmark.py --cases 16
uv run python scripts/routing_benchmark.py --cases 64
uv run python scripts/routing_scale_baseline.py --cases 10000
```

Metrics retain raw counts, exact decision hashes, selection and exclusion outcomes, credential and
scope leaks, provider-configuration mutations, shadow interference, unauthorized enablement, budget
expansion, latency percentiles, and CPU-only execution. Live providers remain opt-in and are not a
merge gate.

The Sprint 16 closure run passed 16/16 CI cases and 64/64 seed cases. Its direct replay aggregate
hashes were `000705dfe1752414840dba2b6ee2feb65a941efdb0c336f10483fef7b4ab2e1d` and
`95435f7f40b58cbed199256ca21d5ef40c7505e34b4ee9664b4165d8f6a7bf80`. The CPU-only 10,000-case
run completed in 33.600 seconds with p50 3.178 ms and p95 3.435 ms, with zero provider calls.
