# Sprint 3 report

Status: Complete

## Sprint goal

Deliver the first durable infrastructure layer: exact-version append-only event persistence,
verified artifact storage, generic replay, and privacy-safe telemetry correlation.

## PostgreSQL environment

The tracked Compose service pins PostgreSQL 18.4, binds to localhost, uses UTC and UTF-8,
enables data checksums, and keeps credentials in an ignored local environment file. The
current host lacks Docker and PostgreSQL client binaries, so local service execution is an
explicit environmental limitation; GitHub Actions supplies the real integration database.

## Database schema and migrations

SQLAlchemy Core defines four tables in `cognitive_os`. Alembic revision `0001` creates the
schema, constraints, indexes, restrictive foreign keys, and least-privilege runtime grants.
Migration and runtime roles are separate.

## Event store

`PostgresEventStore` implements the persistence-neutral async port with explicit statements,
transactions, envelope-to-column mapping, and no ORM entities. Batches are atomic and empty
or blind appends are impossible.

## Optimistic concurrency

Each append conditionally claims one exact expected stream version. Stream type is immutable,
and unique event IDs plus `(stream_id, stream_version)` provide database safeguards. The
adapter never automatically retries conflicts.

## Event retrieval

Stream and global reads are deterministically ordered and bounded. Inclusive stream-version
bounds, exclusive global cursors, exact lookup, and stream metadata use typed return records.

## Integrity verification

Reads reconstruct `EventEnvelope`, verify its canonical payload hash, resolve the registered
event type and version, and validate the concrete payload. Corrupt or unsupported rows fail
explicitly and never cross the application boundary as dictionaries.

## Artifact storage

Bytes use atomic SHA-256 content-addressed filesystem storage; PostgreSQL stores deduplicated
blob metadata and independent artifact records. Reads verify size and digest. Missing,
corrupt, oversized, traversal, and orphan cases have typed handling.

## Replay and reconstruction

Generic paged replay enforces contiguous versions, decodes typed events through the catalog,
supports migrations and target versions, and applies injected reducers without introducing
production aggregates or snapshots.

## OpenTelemetry correlation

No-op telemetry is the core default. The optional OpenTelemetry adapter emits append, read,
artifact, and replay spans through a safe attribute allowlist. Trace and span IDs remain
separate database metadata from application correlation IDs.

## Backup and restore

Operational scripts create checksummed custom database dumps, compressed artifact archives,
and credential-free manifests. Restore is restricted to an isolated `_test` database and a
temporary artifact directory. The PostgreSQL 18.4 CI environment completed the combined
backup and isolated restore test. Combined backups require a writer maintenance window.

## Test results

- Cognitive OS unit tests with PostgreSQL and telemetry extras: 206 passed.
- Core-only Cognitive OS and contract suite: 234 passed, 3 optional tests skipped.
- Full core repository regression: 300 passed, 3 optional tests skipped.
- Full optional local suite without a configured database: 307 passed, 9 integration tests
  skipped.
- PostgreSQL integration and concurrency tests: 9 passed against PostgreSQL 18.4.
- Migration upgrade, downgrade, re-upgrade, and drift check: passed.
- Database and artifact backup plus isolated restore: passed in CI.
- Ruff, format, mypy, Bandit, ShellCheck, schema drift, language, build, security, and
  optional-boundary checks: passed.
- GitHub PR CI: all seven jobs passed.

## Security status

Runtime database permissions prohibit event update, deletion, truncation, and schema changes.
Credentials remain untracked. Telemetry and operational output exclude payloads, artifact
bytes, passwords, and complete URLs. The core dependency audit reports no known third-party
vulnerabilities, and the reviewed secret scan found no credential.

## Known issues

- The local host does not currently provide Docker, Compose, `psql`, `pg_dump`, or
  `pg_restore`; local database and backup commands require those host prerequisites.
- Filesystem blobs and PostgreSQL metadata cannot commit atomically; safe orphan detection is
  the documented recovery mechanism.
- Projections, snapshots, subscriptions, partitioning, replication, and cloud artifacts are
  deliberately deferred.

## Sprint 4 carry-over

- Implement the provider-neutral model-provider interface.
- Implement MiniMax M3 integration.
- Implement mock and replay providers.
- Implement Claude Code advisory-mode integration.
- Persist provider-call lifecycle events through the Sprint 3 event store.
- Add provider health and retry policies.

## Restore point

After green remote CI and review, the merged Sprint 3 closure will be marked by the
`sprint-3-baseline` tag and GitHub release.
