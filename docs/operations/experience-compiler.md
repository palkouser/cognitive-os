# Experience Compiler operations

Run the credential-free smoke and fixtures:

```bash
uv run python scripts/experience_smoke_test.py
uv run python scripts/experience.py compile --fixture repaired-bug-fix
uv run python scripts/experience.py verify --fixture repaired-bug-fix
uv run python scripts/experience.py timeline --fixture repaired-bug-fix
uv run python scripts/experience.py candidates --fixture repaired-bug-fix
```

Inspect PostgreSQL health with configured runtime credentials:

```bash
uv run python scripts/experience.py health --database
```

Apply migration `0006` with `scripts/postgres_migrate.sh`. Back up with
`scripts/backup_event_store.sh` and restore only to an isolated `_test` database with
`scripts/restore_event_store.sh --test-restore`. Restore validation compares compiler counts and
snapshot-history hashes. It never repairs production state.

Cancellation stops work between deterministic stages and retains completed immutable artifacts.
Resume is safe only when source, profile, registry, and stage hashes remain exact; otherwise create a
new compilation.
