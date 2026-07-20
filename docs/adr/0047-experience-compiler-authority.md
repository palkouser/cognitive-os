# ADR 0047: Experience Compiler authority

## Status

Accepted for Sprint 14.

## Decision

The compiler reads exact immutable records from existing authoritative services and writes only
compilation metadata, snapshots, assessments, candidates, decisions, accesses, events, and
artifact references. It cannot write to a source or candidate destination.

```text
source systems --read--> source registry --> immutable snapshot
                                          --> deterministic compiler
PostgreSQL <--compilation metadata--------------|
event store <--lifecycle evidence---------------|
artifact store <--large immutable packages------|
Sprint 15 destination adapters <--export package only
```

PostgreSQL owns compilation metadata and append-only history. The event store owns lifecycle
evidence. The artifact store owns large reconstruction, analysis, verifier, candidate, and export
bodies. Source services remain authoritative for their records, and destination services remain
authoritative for validation and promotion.

Recovery is idempotent: the compiler revalidates the exact snapshot, profile, registry, and stage
hashes. A changed source requires a new compilation. A failed persistence write is retried with the
same idempotency key; conflicting content fails closed. Sprint 15 consumes checksummed candidate
exports and returns optional staging receipts without changing compiler authority.

## Rejected alternatives

A compiler-owned source database, direct destination writes, provider-owned persistence, and a
second controller were rejected because they duplicate authority and make replay ambiguous.
