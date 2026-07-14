# ADR-0005: Event-sourced audit history

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Agent actions and state transitions require replayable provenance and failure analysis.

## Decision

Use an append-only, versioned event history as the primary audit record; telemetry and
provider logs are secondary projections.

## Alternatives considered

Mutable state only, log files, and an observability platform as the source of truth.

## Consequences

Replay and auditing improve, while schema evolution and storage lifecycle become core
engineering responsibilities.

## Verification

Later event-store tests cover append, concurrency, hashing, replay, and recovery.

## References

Cognitive OS Sprint 0–5 specification, Sprint 3.
