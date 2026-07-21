# ADR 0052: Model Capability Registry authority

## Status

Accepted for Sprint 16.

## Decision

The existing provider layer owns configuration, credentials, enablement, health, transport, retry,
and execution. PostgreSQL owns credential-free model identity references, declared and measured
evidence, cohort statistics, uncertainty, and append-only capability revisions. Health is sampled at
decision time and is not copied into a permanent capability claim.

Provider self-description is advisory. Deterministic benchmarks, replay evidence, and verified task
outcomes may create measured observations only with exact lineage. Restore rebuilds statistics and
current projections without changing provider configuration.

## Rejected alternatives

Provider-owned capability promotion, credential duplication, a new provider gateway, RouteLLM as
authority, and mutable profile rows are rejected.
