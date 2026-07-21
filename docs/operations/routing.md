# Routing operations

Run credential-free inspection with:

```bash
uv run python scripts/routing.py models
uv run python scripts/routing.py decision --fixture 2
uv run python scripts/routing.py statistics
uv run python scripts/routing_smoke_test.py
uv run python scripts/routing.py health --database
```

Apply migration `0008` with `scripts/postgres_migrate.sh`. Backup and restore use the existing event
store scripts and include routing profiles, policies, observations, decisions, outcomes, statistics,
experiments, accesses, and their history hash. Restore only to an isolated `_test` database, rebuild
statistics, replay decisions, and confirm provider configuration was not modified. Health is
read-only and reports migration, tables, triggers, functions, orphan outcomes, invalid policies,
statistics and access gaps; it never repairs state.
