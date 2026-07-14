# ADR-0001: LightAgent runtime foundation

- Status: Accepted
- Date: 2026-07-13
- Decision owners: Viktor Palkovics

## Context

Cognitive OS needs an agent loop, tools, workflows, hooks, tracing, and provider support.

## Decision

Use LightAgent v0.9.1 at commit `8ea4db3c9d8791e0977eea2a4481824441b4ba82`
as the initial runtime foundation.

## Alternatives considered

Building a runtime from scratch or adopting a larger second orchestration framework.

## Consequences

Development starts from tested capabilities but inherits an upstream API and dependency
surface that must be isolated and audited.

## Verification

Pin the SHA and run offline import and contract smoke tests.

## References

`docs/baseline/lightagent-upstream-sha.txt`
