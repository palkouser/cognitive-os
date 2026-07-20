# Trajectory reconstruction

Each `TrajectorySourceRef` carries a logical identity, exact revision or event-stream upper version,
SHA-256 hash, scope, sensitivity, and required flag. Raw host paths and parent traversal are rejected.
The frozen resolver registry verifies source bytes before returning immutable timeline entries.

Canonical ordering uses sequence, UTC start time, source type and identity, then timeline-entry ID.
The compiler records every tie-break. Missing sequence values produce gaps; collisions produce
conflicts. Plan revisions, Controller states, Context use, provider and tool calls, skill and strategy
executions, verifiers, acceptance, corrections, denials, and cancellation remain typed evidence.

Normalization summarizes bounded payload metadata and never mutates a source body. Repeated
reconstruction of the same snapshot produces the same hash. A source change or stream-version
advance requires a new snapshot and compilation.
