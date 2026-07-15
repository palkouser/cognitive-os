# Memory Plane operations

The Compose service uses `pgvector/pgvector:0.8.2-pg18-bookworm`, binds to localhost, initializes
UTF-8 with checksums, and stores UTC timestamps. The privileged bootstrap connection is used only
for migrations such as `CREATE EXTENSION vector`; the runtime role remains separate.

```bash
docker compose --env-file .env.postgres.local -f infra/compose/postgres.yml up -d
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os-cache/uv \
  uv run alembic -c infra/postgres/alembic.ini upgrade head
```

Run PostgreSQL integration tests only against an `_test` database. Migration validation performs
upgrade, downgrade to revision `0001`, re-upgrade, and `alembic check`. Schema inspection must find
the five memory tables and zero HNSW/IVFFlat indexes.

`scripts/backup_event_store.sh` now produces a combined database/artifact backup manifest with
memory, revision, and embedding counts. `scripts/restore_event_store.sh --test-restore` restores
only to an isolated test database and checks projection status, revision continuity, and hashes.
Never repair divergence destructively; preserve the database and compare tables, lifecycle events,
artifacts, and the last validated backup.
