# Running benchmarks

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint7-seed.yaml \
  --mode controller-replay \
  --report-directory /tmp/cognitive-os-benchmark-reports
```

Runs are local, sequential, seeded, credential-free by default, and never download datasets.
