# ADR 0065: Proposal review authority

## Status

Accepted for Sprint 18.

## Decision

Only an explicit non-provider reviewer may approve an exact, verifier-passing proposal revision
for a future isolated experiment. This decision is distinct from implementation, merge, release,
deployment, and any Sprint 19 promotion approval.

## Alternatives

Automatic approval, model self-approval, inherited weakness confirmation, and approval of a moving
current revision were rejected.

## Consequences

Reviews record reviewer authority, rationale, policy hash, verifier hash, and proposal hash.
Abstention does not advance lifecycle state.

## Rollback and migration impact

Reviews are append-only. A later retraction or supersession preserves the decision; no rollback
path mutates a destination.
