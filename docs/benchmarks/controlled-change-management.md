# Controlled-change benchmark methodology

The CI manifest contains 18 deterministic cases. The seed manifest repeats the same authority and
failure classes over 72 stable case identities. Both are credential-free and CPU-only.

Coverage includes Tier 0/1/2 success, Tier 1 rollback, Tier 3 manual review, proposal integrity,
worktree and database scope escape, provider scope, dependency and migration failures, historical
and unrelated-domain regressions, backup/restore and rollback failures, and concurrent promotion
conflict.

Reports include exact case and manifest hashes, aggregate pass rate, promotion eligibility,
hard-failure rejection, separate approval, rollback readiness, provider calls, and active-state or
runtime-release operation counts. Local latency and resource results describe only the recorded
hardware/software profile; they are not universal capacity claims.

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint19-change-ci.yaml \
  --mode change-replay \
  --report-directory artifacts/sprint-19/benchmarks/ci
```
