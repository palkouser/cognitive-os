# Controller checkpoint and recovery

```mermaid
flowchart LR
  A[Load checkpoint] --> B{Hash and scope valid?}
  B -- no --> C[Full replay]
  B -- yes --> D[Replay later events]
  C --> E[Classify active child call]
  D --> E
  E --> F[Resume, or pause uncertain side effect]
```

Checkpoints are deterministic, hashed artifacts bound to task and stream version. Full replay
is always available. A requested child with no start may be reevaluated; a started child with
no terminal event is uncertain. Uncertain provider calls and side-effecting tools are not
blindly repeated. Expected-version conflicts stop the writer and require replay.
