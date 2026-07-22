# ADR 0067: Proposal PostgreSQL governance

## Status

Accepted for Sprint 18.

## Decision

Migration `0010` adds ten proposal tables, append-only history triggers, narrow security-definer
functions, indexes, constraints, and least-privilege grants. Backup manifests include proposal
counts, a deterministic history hash, and the Sprint 18 inventory hash.

## Alternatives

Direct runtime writes, overwriteable history, broad grants, and a second database were rejected.

## Consequences

All mutations use controlled functions and compare-and-set revisions. Restore checks counts,
history, projection integrity, artifacts, and existing subsystem evidence.

## Rollback and migration impact

The tested path is `0009 -> 0010 -> 0009 -> 0010`. Downgrade drops only Sprint 18 functions,
triggers, and tables after an operator-controlled backup.
