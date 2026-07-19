# ADR 0046: Strategy-to-Controller plan instantiation

## Status

Accepted for Sprint 13.

## Decision

A strategy phase is declarative coordination data, not an executable action. Before execution, the
host resolves every mutable skill binding to an exact verified Sprint 12 revision, validates the
phase DAG and deterministic branches, and intersects budgets:

```text
effective = min(host, Controller, strategy, phase, skill)
```

Each phase becomes an existing `ExecutionPlan` step with strategy revision, phase ID, exact skill
revision, static model role, tool and verifier requirements, Context purpose, effective budget,
branch, and fallback provenance retained in the immutable plan-instantiation package. Approval and
clarification phases use existing Controller waiting and continuation behavior.

The existing Controller remains the only runtime state machine. A strategy cannot add actions,
change transitions, increase budgets, weaken approval or verification, bypass Context validation,
or expand workspace permissions. Unknown branch signals and stale skill, registry, Context, or plan
snapshots fail closed. Cancellation propagates; resume revalidates exact snapshots and never repeats
an uncertain provider side effect.
