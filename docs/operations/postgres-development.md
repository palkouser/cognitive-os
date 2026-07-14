# PostgreSQL development

Install Docker with Compose and PostgreSQL client tools on the host, then copy
`.env.postgres.example` to ignored `.env.postgres.local`. Set private passwords and admin,
runtime, and test URLs. Never commit the local file.

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
