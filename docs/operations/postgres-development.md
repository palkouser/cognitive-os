# PostgreSQL development

The Ubuntu 26.04 development host uses Docker Engine 29.6.1, Compose 5.3.1, and Buildx
0.35.0 from Docker's official repository. Docker runs as the enabled user-level rootless
service, and the active context is `rootless`. Do not use `sudo docker`, the `docker` group,
or `/var/run/docker.sock`.

PostgreSQL 18.4 client tools come from the official PGDG repository. Do not install or start
a native PostgreSQL server. Copy `.env.postgres.example` to ignored
`.env.postgres.local`, set private passwords and admin, runtime, and test URLs, and restrict
the file to mode 0600. Never commit or print the local file.

The integration-test URL must target an isolated database whose name ends in `_test`. The
integration wrapper derives the matching owner URL from `COGOS_DATABASE_ADMIN_URL` and the
database name in `COGOS_TEST_DATABASE_URL`; it refuses to run against any other database.

```bash
./scripts/postgres_up.sh
./scripts/postgres_wait.sh
./scripts/postgres_bootstrap_roles.sh
./scripts/postgres_migrate.sh
./scripts/postgres_status.sh
```

The service uses PostgreSQL 18.4, binds only to `127.0.0.1:55432`, initializes UTF-8 with
checksums, uses UTC, and persists data beneath the configured NVMe path. Stop it with
`./scripts/postgres_down.sh`; this does not delete its data.

Verify the local workflow with:

```bash
./scripts/postgres_migration_check.sh
./scripts/run_postgres_integration_tests.sh
```

The remediation run reached Alembic revision `0001`, passed all 9 PostgreSQL integration
and concurrency tests, and passed the 316-test repository regression with the MCP,
PostgreSQL, and OpenTelemetry extras. Do not use `--all-extras` for the default-environment
contract suite: legacy optional dependencies are intentionally required to be absent there.

## Migration 0013: approximate vector index build time

Migration 0013 creates one HNSW index per declared embedding dimension. On an empty or
small `memory_embeddings` this is instant. On a populated table it is not: building over
100 000 768-dimensional vectors took **over six minutes** on the development container
(`maintenance_work_mem = 64MB`, `shared_buffers = 128MB`, two parallel maintenance
workers), which exceeds the application's 30-second `command_timeout` by two orders of
magnitude.

Before applying 0013 to a populated deployment:

- raise `maintenance_work_mem` for the session — an HNSW build that does not fit in memory
  falls back to a much slower on-disk pass, and pgvector says so in a `NOTICE`;
- run the migration through a client without the application's command timeout;
- expect writes to `memory_embeddings` to block for the duration, since `CREATE INDEX`
  without `CONCURRENTLY` takes a lock. Alembic runs inside a transaction, so
  `CONCURRENTLY` is not available here; schedule accordingly.

A failed build leaves an **invalid** index behind. `pg_indexes` still lists it and the
planner ignores it entirely, so the Memory Plane health check tests
`pg_index.indisvalid AND indisready` rather than mere presence — a build that failed
reports as `missing_approximate_indexes`, not as healthy.

Measure a deployment's own envelope with `scripts/memory_ann_baseline.py`, which creates
and drops its own scratch table and never writes to governed tables.
