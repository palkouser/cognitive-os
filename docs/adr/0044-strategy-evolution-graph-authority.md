# ADR 0044: Strategy Evolution Graph authority

## Status

Accepted for Sprint 13.

## Decision

PostgreSQL owns strategy identities, immutable revisions, typed graph edges, selections, outcomes,
statistics projections, and access records. The event store owns lifecycle evidence. The artifact
store owns large selection traces, plan packages, comparison reports, and graph snapshots.

```text
operator -> strategy service -> PostgreSQL
                         |----> event store
                         `----> artifact store
PostgreSQL -> bounded query -> optional NetworkX projection -> read-only view
```

Only strategy identity, strategy revision, problem class, and failure-mode descriptors are native
strategy nodes. Skills, tools, model roles, verifiers, Context profiles, task runs, plans, outcomes,
artifacts, corrections, acceptance decisions, and semantic claims remain typed exact references to
their authoritative subsystem. Every edge records its source strategy revision and provenance.

Edges are removed only by appending a new strategy revision with a new edge set. NetworkX is an
optional bounded analytical projection and cannot mutate state. Graph snapshots contain exact
references, query limits, registry hashes, and a canonical hash; replay and restore reconstruct the
same snapshot from PostgreSQL plus artifact metadata.

## Rejected alternatives

Neo4j, Apache AGE, Graphiti, and Cognee are not introduced. They add a second authority, operational
state, and synchronization failure modes without a Sprint 13 requirement. Graphiti and Cognee are
design references only.
