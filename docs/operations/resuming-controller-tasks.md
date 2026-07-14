# Resuming controller tasks

Place question-ID keys and JSON values in an answers file, then run:

```bash
uv run python scripts/controller_resume.py \
  --task-run-id TASK_RUN_UUID \
  --continuation-token 'ONE_TIME_VALUE' \
  --answers-file answers.json
```

The command never prints the supplied token. A successful call consumes it before revising
the representation. Reuse, expiry, task mismatch, or a stale stream version is rejected.
