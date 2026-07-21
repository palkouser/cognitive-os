# Sprint 17 Weakness Mining benchmarks

The CI manifest contains 18 deterministic cases and the seed manifest contains 72. Each case runs
without credentials or network access and records outcome match, replay equality, lineage,
signal/group/queue counts, latency, provider calls, source writes, automatic confirmations, and
scope/sensitivity leaks. Required safety counters must remain zero.

`scripts/weakness_benchmark.py` measures one bounded batch. `scripts/weakness_scale_baseline.py`
uses the same CPU-only path for operator-selected sizes. Results are local measurements, not general
throughput or production-capacity claims.
