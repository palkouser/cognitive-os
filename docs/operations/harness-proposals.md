# Operating Harness Proposals

Sprint 18 commands inspect, generate, validate, review, and queue proposal records only. They do not
apply proposals. The governing database decision is
[ADR 0067](../adr/0067-proposal-postgres-governance.md).

## Preflight and local deterministic checks

```bash
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal_preflight.py
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal_smoke_test.py
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal_benchmark.py --cases 16
```

The preflight artifact is written to
`artifacts/sprint-18/preflight/repository-inventory.json`. It is operational evidence and remains
outside version control; ADR 0061 and the migration record its reviewed hash.

Use `scripts/proposal.py --help` for the fixture-backed operator CLI. Consequential commands require
both `--proposal-id` and `--revision`; reviewer and actor values beginning with `provider` or `model`
are rejected. Provider assistance remains opt-in and credential-free baseline checks never call a
live provider.

## PostgreSQL migration and health

```bash
UV_CACHE_DIR=.cache/uv ./scripts/postgres_migrate.sh
UV_CACHE_DIR=.cache/uv uv run python scripts/proposal.py health
```

The expected head is `0010`. Before production migration, create an operator-controlled backup.
The tested migration cycle is upgrade from `0009`, downgrade to `0009`, and re-upgrade to `0010`.
Runtime access uses only the controlled creation, append, review, queue, removal, and access
functions created by the migration.

## Backup, restore, and replay

```bash
COGOS_BACKUP_ROOT=/safe/backup/root ./scripts/backup_event_store.sh
COGOS_BACKUP_ROOT=/safe/backup/root ./scripts/restore_event_store.sh --test-restore
```

The backup manifest records all ten proposal table counts, a deterministic proposal-history hash,
the Alembic revision, and the Sprint 18 preflight inventory hash. Isolated restore verifies those
values, current-to-revision integrity, artifacts, and the existing subsystem checks. Verifier
replay reads an exact stored proposal revision and rebuilds the same finding set from host rules.

## Troubleshooting

- `stale_revision` or compare-and-set failure: fetch the exact current revision and repeat review;
  never retarget a previous approval.
- `duplicate active proposal signature`: use the existing exact proposal or explicitly supersede it.
- missing source, evidence, impact, or reproduction data: repair the source pipeline outside the
  proposal engine; it has read-only authority.
- provider unavailable: deterministic generation remains available.
- provider scope, citation, type, or instruction violation: reject the draft; do not bypass a gate.
- health reports a non-`0010` head: stop proposal writes and reconcile migration state.
- restore hash mismatch: keep the isolated database, preserve logs, and do not promote the restore.

No CLI or database function implements code modification, proposal application, deployment,
training, release tagging, or Sprint 19 promotion.
