# ADR 0062: Proposal identity, revisions, and storage

## Status

Accepted for Sprint 18.

## Decision

A proposal has a stable UUID, deterministic signature, and immutable contiguous revisions.
PostgreSQL owns identity, revision metadata, reviews, queue history, and access records. The
Artifact Store owns large source snapshots, proposal bodies, and reports by content hash.

## Alternatives

Mutable rows, content-addressing only, and large JSON bodies in PostgreSQL were rejected because
they weaken review replay or duplicate authoritative storage.

## Consequences

Every consequential operation names an exact proposal revision and hash. Current rows are derived
projections; history remains append-only.

## Rollback and migration impact

Migration `0010` can be downgraded only after preserving proposal artifacts and history. Rollback
does not apply a proposal to any destination.
