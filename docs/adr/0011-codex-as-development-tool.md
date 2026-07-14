# ADR-0011: Codex as a development tool

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Codex assists development but must not become an implicit runtime or state store.

## Decision

Use Codex as a reviewable development aid. It is not a runtime provider, durable memory,
or issue tracker; it cannot promote untested changes or automatically access runtime data.

## Alternatives considered

Embedding IDE-agent sessions into the Cognitive OS runtime or treating them as project state.

## Consequences

Changes stay in Git and issue workflows with explicit checks and permission boundaries.

## Verification

Repository instructions, sandbox policy, secret filtering, and required checks are present.

## References

`AGENTS.md`, `.codex/config.toml`
