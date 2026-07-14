# ADR-0004: Local state ownership

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Provider sessions are replaceable and cannot be the durable system record.

## Decision

Cognitive OS owns all durable task, event, memory, strategy, verification, routing, and
evolution state in local stores under explicit schemas.

## Alternatives considered

Provider conversation history or framework-specific memory as the source of truth.

## Consequences

Providers remain replaceable; Cognitive OS must implement persistence and migration.

## Verification

Provider replacement tests must preserve all durable state.

## References

`docs/architecture/project-charter.md`
