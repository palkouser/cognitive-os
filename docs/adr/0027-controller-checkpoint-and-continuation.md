# ADR 0027: Controller checkpoint and continuation

Status: Accepted

Checkpoints use deterministic Cognitive OS JSON, include the runtime projection and typed
problem/plan state, and are integrity-bound with SHA-256. They are task-run and stream-version
scoped and must validate before use. Full replay remains available when a checkpoint is absent
or safely rejectable.

Continuation tokens use `secrets.token_urlsafe(32)`. Only their SHA-256 hashes are persisted.
A token is bound to task run, checkpoint, event-stream version, and expiry, and is single-use.
No token is logged, traced, included in an exception, or committed in a fixture. No new
long-term secret is required.
