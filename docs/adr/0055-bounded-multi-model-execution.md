# ADR 0055: Bounded multi-model execution

## Status

Accepted for Sprint 16.

## Decision

Multi-model patterns compile to ordinary Controller steps. Each role receives an exact routing
decision, provider request, and validated Context Bundle. The effective budget is the minimum of
Controller, routing policy, strategy, and pattern budgets. Provider outputs remain proposals and
registered verifiers retain final acceptance authority.

## Rejected alternatives

A second Controller, autonomous agent teams, unbounded debate, model self-selection, hidden calls,
critic acceptance authority, and retry after uncertain side effects are rejected.
