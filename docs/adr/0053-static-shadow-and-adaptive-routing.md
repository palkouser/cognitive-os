# ADR 0053: Static, shadow, and adaptive routing

## Status

Accepted for Sprint 16.

## Decision

Static routing is the default control. Shadow routing records a separate deterministic decision but
cannot alter provider requests, Controller plans, budgets, Context Bundles, tools, or outcomes.
Adaptive execution requires a promotion assessment, explicit operator approval, an append-only
enabled policy revision, and bounded TaskSignature scope. Disablement preserves history and restores
static routing.

## Rejected alternatives

Automatic promotion, hidden feature activation, live bandit exploration, provider-written weights,
and shadow execution are rejected.
