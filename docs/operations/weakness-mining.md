# Operating Weakness Mining

Run the credential-free path:

```bash
uv run python scripts/weakness_smoke_test.py
uv run python scripts/weakness.py mine --cases 18
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint17-weakness-ci.yaml \
  --mode weakness-replay --report-directory /tmp/sprint17-weakness
uv run python scripts/weakness_scale_baseline.py --cases 10000
```

With an isolated configured PostgreSQL database, apply migration `0009` and inspect persistence:

```bash
./scripts/postgres_migrate.sh
uv run python scripts/weakness.py health --database
```

Health requires ten tables, eight append-only triggers, five controlled functions, no orphan
revisions or queue entries, and Alembic head `0009`. Backup the shared PostgreSQL and artifact
stores with `scripts/backup_event_store.sh`; validate an isolated restore with
`scripts/restore_event_store.sh --test-restore`. The dump is the authority for weakness rows and
the artifact archive retains referenced large evidence. Rebuild exact groups, impact, evidence,
and queue snapshots and compare hashes before accepting a restore.

Known limits: the default clusterer is intentionally no-op, causal relationships remain unknown
unless supplied by an existing authority, replay candidates are proposal-only, and the supplied
scale command reports measurements rather than unsupported capacity claims.
