# Recovering controller runs

```bash
uv run python scripts/controller_replay.py --task-run-id TASK_RUN_UUID --verify-checkpoints
```

Recovery validates checkpoint hashes and scope, replays later events, and classifies any
active provider or tool child call. An uncertain side effect pauses for explicit operator
resolution; it is not automatically repeated.
