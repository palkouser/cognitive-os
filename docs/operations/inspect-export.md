# Inspect AI export

```bash
uv run --extra benchmark-inspect python scripts/inspect_export.py \
  --manifest benchmarks/manifests/sprint7-ci.yaml \
  --output-directory /tmp/cognitive-os-inspect-export
```

The output is secondary and contains no credentials. The exporter has no Inspect runtime
dependency; invoking Inspect itself remains explicit and deferred until its Click constraint is
security-compatible.
