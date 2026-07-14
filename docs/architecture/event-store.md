# Event store architecture

PostgreSQL is the authoritative source of Cognitive OS history. Logs and traces are
diagnostics, not state. `EventStorePort` separates application code from the optional
`PostgresEventStore` adapter, and the Sprint 2 `EventEnvelope` remains the durable contract.

Each append validates a non-empty, single-stream batch before opening one explicit database
transaction. The transaction claims the exact expected stream version, inserts every event,
and returns monotonically increasing global positions. Failure rolls back the stream update
and all event rows. Event history is append-only for the runtime role.

Database-only metadata consists of global position, `stored_at`, trace ID, and span ID.
Envelope fields are mapped to explicit columns. Stream reads order by stream version; global
reads order by global position. Raw SQLAlchemy rows never cross the adapter boundary.
