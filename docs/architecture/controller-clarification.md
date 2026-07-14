# Controller clarification

```mermaid
sequenceDiagram
  Controller->>Event Store: clarification requested
  Controller->>Artifact Store: verified checkpoint
  Controller-->>User: one-time plaintext continuation token
  User->>Controller: token and typed answers
  Controller->>Event Store: validate version, consume token, revise problem
  Controller->>Controller: resume from representing_problem
```

Only token hashes enter persistence. Answers must match the requested question IDs and their
JSON Schemas. Expired, altered, consumed, wrong-task, wrong-checkpoint, stale-version, and
terminal-run continuations fail before representation revision.
