# ADR-0002: Thin fork and upstream policy

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Upstream updates must remain reviewable while Cognitive OS develops its own behavior.

## Decision

Keep upstream files in place, put owned code in `cognitive_os/`, integrate through
adapters and hooks, and perform upstream syncs only on `upstream-sync/*` branches.

## Alternatives considered

A full rewrite, permanent hard fork, or direct development inside `LightAgent/`.

## Consequences

The ownership boundary stays visible; unavoidable upstream patches require separate
documentation and regression coverage.

## Verification

Review diffs by ownership boundary and reject undocumented upstream changes.

## References

`AGENTS.md`
