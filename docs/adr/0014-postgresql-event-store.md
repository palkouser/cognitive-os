# ADR 0014: PostgreSQL event store

Status: Accepted

PostgreSQL is the authoritative Cognitive OS event store. The adapter uses SQLAlchemy's
asynchronous Core API, asyncpg, explicit statements and transactions, while Alembic owns
schema migration. ORM entities, relationship loading, and database models in the domain
package are prohibited.

The Sprint 2 `EventEnvelope` remains the persisted contract. Global position, database
storage time, trace ID, and span ID are storage metadata outside the envelope. Every append
uses an exact expected stream version; `(stream_id, stream_version)` is unique and event rows
are append-only. The runtime role cannot update or delete event history.

The external eventsourcing library is a design reference only, not a dependency. Projections,
snapshots, subscriptions, partitioning, and multi-node replication are deferred.
