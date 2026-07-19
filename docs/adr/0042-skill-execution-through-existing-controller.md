# ADR 0042: Skill execution through the existing Controller

## Status

Accepted for Sprint 12.

## Decision

The execution path is:

`SkillExecutionService → Cognitive Controller → Context Builder → Model Execution Service → Tool
Execution Service → Verifier Registry → Acceptance Service`.

The Skill Engine does not introduce a second Controller, provider runtime, tool registry, verifier
registry, approval service, or acceptance authority. A request binds an exact verified revision,
package hash, registry snapshots, task run, input schema, and resource budget. The Context Builder
constructs and revalidates a trust-separated bundle before the existing Controller adapter starts.

Skill steps are declarative capability references. They are not shell snippets, direct database
operations, dynamic Python callables, or provider-authored authority. Waiting executions remain in
the Controller continuation path; terminal results are immutable and drive rebuildable statistics.

## Consequences and verification

Stale registry snapshots, mismatched package hashes, unavailable artifacts, excessive budgets,
unknown inputs, and non-verified revisions fail closed. Unit tests use a Controller adapter stub to
prove identity preservation without implementing another control loop.
