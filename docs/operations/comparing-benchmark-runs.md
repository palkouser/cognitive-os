# Comparing benchmark runs

```bash
uv run python scripts/benchmark_compare.py \
  --baseline baseline.json --candidate candidate.json \
  --fail-on-new-required-failure
```

Comparison requires equal benchmark identity and case set. Sprint 7 reports deltas and regressions without statistical-significance claims.
