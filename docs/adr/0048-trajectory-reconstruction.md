# ADR 0048: Deterministic trajectory reconstruction

## Status

Accepted for Sprint 14.

## Decision

Every source binds an exact identity, revision or stream upper version, content hash, scope, and
sensitivity. Reconstruction orders entries by authoritative sequence, UTC timestamp, source
identity, and entry identity. The recorded ordering decision makes the final tie-break explicit.

```text
stream sequence -> causation/correlation metadata -> UTC time -> source identity -> entry ID
```

Sequence gaps become `TrajectoryGap`; duplicate claimed sequences become `TrajectoryConflict`.
Superseded plan revisions, retries, repairs, cancellations, denials, and unknown event types remain
visible. Provider output cannot change sequence or source identity. Conflicting timestamps do not
override an authoritative stream sequence. A replay recomputes the same reconstruction hash.

An incomplete or conflicted trajectory may still be inspected and conservatively compiled, but it
cannot receive a fully verified manifest or complete-experience candidates.

## Rejected alternatives

Timestamp-only ordering, provider-authored ordering, silent gap repair, and destructive event
normalization were rejected because they erase authoritative evidence.
