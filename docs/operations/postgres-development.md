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
