# Running controller tasks

Start PostgreSQL and apply migrations, then run:

```bash
uv run python scripts/controller_run.py \
  --request-file tests/fixtures/controller/simple-task.md \
  --provider replay \
  --controller-config config/controller.local.yaml \
  --json
```

Normal offline execution uses reviewed replay data and requires no provider credential. The
result contains task-run ID, state, usage, acceptance, safe errors, and a continuation token
only when one was newly issued.
