# Harness Proposal Engine benchmarks

Sprint 18 uses deterministic, credential-free fixtures. The CI manifest contains 16 cases and the
seed manifest contains 64 cases across all 15 proposal types, lifecycle boundaries, provider
fallback, review, queue ordering, replay, and adversarial authority cases.

```bash
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal_benchmark.py --cases 16
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal_benchmark.py --cases 64
UV_CACHE_DIR=.cache/uv uv run python scripts/benchmark_run.py --adapter proposal-replay --manifest benchmarks/manifests/sprint18-proposal-ci.yaml
```

Acceptance requires 100% deterministic pass rate, stable output hashes for repeated inputs, zero
destination writes, and no provider credential. Reports are evidence about proposal construction;
they do not measure whether a proposed change improves the harness. Live-provider experiments are
explicit opt-in work outside baseline CI.

The benchmark adapter returns bounded status, proposal hash, verifier status, finding count,
generation mode, and the no-destination-write invariant. Large reports belong in the Artifact
Store. The manifest and replay hashes allow comparison to an exact baseline without granting
implementation or promotion authority.
