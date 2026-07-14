# Database migrations

Alembic reads only `COGOS_DATABASE_ADMIN_URL`; no URL is stored in configuration. The owner
role runs migrations and the runtime role cannot alter schema objects.

```bash
./scripts/postgres_migrate.sh
./scripts/postgres_migration_check.sh
```

Downgrade tests are restricted to isolated databases ending in `_test`. Routine development
must never downgrade or truncate the persistent development database.
