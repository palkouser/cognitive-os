# ADR-0008: Tool security boundaries

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Generated commands and foreign repositories are untrusted and may have side effects.

## Decision

Tool execution requires typed schemas, risk and side-effect metadata, explicit policy,
path scoping, timeouts, audit events, and sandboxing. Untrusted execution cannot write
directly to trusted stores.

## Alternatives considered

Direct unrestricted shell and tool execution by the agent runtime.

## Consequences

Some operations need user approval and isolated runners, adding latency and complexity.

## Verification

Security tests must cover denial, timeout, path escape, redaction, and audit behavior.

## References

`docs/security/trust-boundaries.md`
