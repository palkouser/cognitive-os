# Inspecting controller state

```bash
uv run python scripts/controller_inspect.py --task-run-id TASK_RUN_UUID --json
```

Inspection replays the authoritative task-run stream and prints the typed projection. Full
sensitive artifacts and continuation values are excluded by default.
