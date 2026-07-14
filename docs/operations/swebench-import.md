# SWE-bench manifest import

```bash
uv run python scripts/swebench_import.py \
  --input /path/to/records.jsonl \
  --output-manifest /tmp/swebench-local.yaml \
  --license MIT --limit 5
```

The command performs no network access, clone, image download, patch application, or task execution. Gold patches are represented only by protected evaluation hashes and never enter provider-visible input.
