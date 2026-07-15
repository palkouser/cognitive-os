# ADR 0037: Relational semantic graph and derived Wiki

- Status: Accepted
- Date: 2026-07-15

## Context

Claim relations and readable knowledge pages are useful, but neither may bypass the Sprint 9 and
Sprint 10 governance authorities.

## Decision

PostgreSQL owns claim-revision edges, contradictions, and page lineage. Bounded in-process graph
analysis may project exact revision nodes but is optional and non-authoritative. No graph database
is introduced.

```text
authoritative source revision -> semantic observation -> claim revision
                                                   |-> relational claim edges
                                                   |-> deterministic Markdown renderer
                                                   `-> exact Wiki claim lineage
```

```text
Memory Plane / event store / artifact store
                    |
          Semantic Memory Service
             |             |
 PostgreSQL semantic rows  |-- bounded stdlib or optional NetworkX projection
             |
      deterministic Wiki renderer -> Wiki revision + exact lineage
```

Wiki v3 renders fixed ordered sections from an exact claim snapshot. Every displayed fact points to
a claim revision. Page revisions, Markdown hashes, renderer version, temporal parameters, and
lineage hashes are append-only. Renderer output is escaped data, contains no provider-generated
narrative, and cannot be cited as independent evidence.

If rendering fails, no claim changes. A missing claim revision blocks commit. Regeneration compares
the byte hash and never mutates semantic state. Recovery restores PostgreSQL and artifacts, then
rebuilds pages from exact lineage.

## Alternatives considered

- Graphiti, Cognee, or another graph authority: rejected as a competing store.
- Provider-authored Wiki prose: rejected because it loses deterministic grounding.
- Wiki pages as evidence: rejected because it creates a circular authority path.

## Consequences

Graph traversal is bounded by host limits. Wiki pages remain disposable projections; claim and
evidence history remains the security and recovery boundary.
