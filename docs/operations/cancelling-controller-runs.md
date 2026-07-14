# Cancelling controller runs

```bash
uv run python scripts/controller_cancel.py \
  --task-run-id TASK_RUN_UUID \
  --reason "Cancelled by project owner."
```

Cancellation validates the current state, appends an expected-version-protected state change,
and then records the cancellation event. Terminal runs reject further transitions.
