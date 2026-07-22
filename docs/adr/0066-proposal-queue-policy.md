# ADR 0066: Proposal queue and duplicate policy

## Status

Accepted for Sprint 18.

## Decision

The review queue uses a deterministic tuple: dependency block, operator priority, weakness
priority, evidence confidence, risk, expected value, cost, blast radius, rollback readiness,
dependency count, canonical name, UUID, and revision. One active deterministic signature is
allowed; repeat generation is idempotent.

## Alternatives

Learned ranking, provider priority, insertion-order ties, and merging merely similar proposals were
rejected.

## Consequences

Exact duplicates are stable while related proposals remain independent. Queue additions and
removals are append-only records.

## Rollback and migration impact

Removing an entry appends an inactive record. It neither deletes proposal history nor changes any
target subsystem.
