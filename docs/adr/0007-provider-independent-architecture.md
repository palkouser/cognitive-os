# ADR-0007: Provider-independent architecture

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Models differ in API, availability, cost, and capabilities.

## Decision

All providers sit behind normalized interfaces. Subscriptions and credentials do not
change state ownership, and provider-specific sessions are never durable memory.

## Alternatives considered

Binding the runtime and stored state directly to a single provider SDK.

## Consequences

Adapters and contract tests are required, but provider replacement remains possible.

## Verification

Mock and replay providers must support offline application tests.

## References

ADR-0004.
