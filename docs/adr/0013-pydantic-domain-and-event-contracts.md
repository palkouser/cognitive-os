# ADR 0013: Pydantic domain and event contracts

- Status: Accepted
- Date: 2026-07-14

## Context

Future Cognitive OS components need a provider-neutral and persistence-neutral contract
boundary with validation, deterministic JSON, and reviewable schemas.

## Decision

Pydantic v2 is the contract-model foundation. Contract models reject unknown fields.
Persisted timestamps are timezone-aware and normalized to UTC. Event payloads and envelopes
are frozen, use tuples for collections where practical, and expose JSON as the stable
persistence boundary.

Entity and event identifiers use UUID4. Stream ordering uses a separate positive stream
version. Every event type declares a positive integer schema version. ORM and database
classes remain separate from domain contracts, and Sprint 2 implements no event-store
backend.

## Consequences

All persisted contracts have explicit validation and schema generation. Frozen Pydantic
models do not imply deep immutability for arbitrary mappings, so dynamic JSON mappings are
copied at validation and serialized immediately at the event boundary.
