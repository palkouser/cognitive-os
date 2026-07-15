# ADR 0035: Governed Memory Plane authority

- Status: Accepted
- Date: 2026-07-15

## Context

Cognitive OS needs durable experience across task sessions without allowing model output,
LightAgent, or an imported memory framework to become a competing authority. Sprint 8
provides accepted trajectories, verifier evidence, artifacts, and canonical hashes that can
be projected deterministically.

## Decision

PostgreSQL owns authoritative Memory Plane state. `memory_items` is the current projection;
`memory_revisions` is append-only history. The existing event store owns system and memory
lifecycle events. Events support correlation, audit, replay comparison, and recovery
evidence, but do not form a second memory database. The artifact store owns large referenced
content. Memory rows retain typed references and verified digests.

```text
authoritative events ─┐
artifact references ──┼─> governed Memory Service ─> PostgreSQL memory tables
accepted evidence ────┘             │                         │
                                    └─> lifecycle events      └─> exact retrieval
provider / LightAgent ─> narrow adapter ─> policy and access audit
```

Providers are non-authoritative and receive neither database access nor promotion authority.
LightAgent uses a narrow adapter and cannot persist unrestricted conversation history.
Exact vector search is the only vector mode in Sprint 9; approximate indexes and hybrid
retrieval are prohibited. Semantic claims, contradiction inference, skills, and strategies
are deferred.

Every mutation uses an expected revision. New revisions and provenance are append-only.
Lifecycle events and tables are compared by a read-only consistency check. On divergence,
normal writes fail closed and operators restore or reconcile from validated PostgreSQL,
event, and artifact backups without destructive automatic repair.

## Alternatives considered

- Event stream as the only memory store: rejected because bounded metadata, full-text, and
  exact-vector querying need an authoritative query model without replaying all history.
- Framework-owned stores (Cognee, Graphiti, LangMem, agentmemory, or LightAgent memory):
  rejected because they create a competing authority and weaken Cognitive OS governance.
- Provider-generated summaries as verified memory: rejected because plausibility is not
  authoritative evidence.
- HNSW, IVFFlat, or hybrid retrieval: deferred until measured exact-retrieval behavior and
  later Context Builder requirements exist.

## Consequences

Memory writes require validated provenance, host policy, sensitivity and scope controls.
Large content stays in the artifact store. Recovery must validate revision continuity,
canonical hashes, source availability, lifecycle-event correspondence, and access audit.
PostgreSQL and pgvector become optional infrastructure dependencies while core installation
and tests remain credential-free and GPU-free.
