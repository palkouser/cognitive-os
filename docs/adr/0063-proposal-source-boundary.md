# ADR 0063: Weakness source boundary

## Status

Accepted for Sprint 18.

## Decision

The Harness Proposal Engine reads an exact Weakness Mining revision, evidence package, impact
score, reproduction assessment, queue record, and registry snapshots. It freezes their hashes in
an immutable source snapshot and never changes the source subsystem.

## Alternatives

Reading current mutable projections without revision checks and repairing weakness records during
proposal generation were rejected.

## Consequences

Stale, missing, or mismatched evidence fails closed. Confirmed weaknesses are eligible by default;
high-impact candidates require explicit policy.

## Rollback and migration impact

Source systems need no migration or rollback. Historical external references remain evidence even
if the current weakness revision later changes.
