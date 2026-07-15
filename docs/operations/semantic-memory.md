# Semantic-memory operations

Apply migration `0003`, then run read-only health and the isolated smoke path:

```bash
uv run alembic -c infra/postgres/alembic.ini upgrade head
uv run python scripts/semantic_health.py
uv run python scripts/semantic_smoke_test.py
```

`COGOS_DATABASE_URL` is required. Smoke refuses databases whose name does not end in `_test` and
uses no credentials, provider call, graph database, or network access.

The standard-library CLI is `uv run python scripts/semantic.py`. Its command groups cover
`observation create|get|list|sources`, explicit `extract-memory`, extraction reports, claim
get/history/promote/dispute/supersede/retract, evidence listing, contradiction
list/inspect/resolve/reopen, current/valid-at/known-at queries, timelines, bounded graph neighbours,
and Wiki render/render-as-of/get/history/verify/regenerate. Mutations require validated contract
JSON; claim and contradiction transitions require an exact expected revision. Observation creation
supports `--dry-run`. Artifact and trajectory extraction fail closed unless a deterministic host
extractor is configured; provider extraction never turns on implicitly.

Back up with `scripts/backup_event_store.sh`. The manifest records semantic observations, claims,
revisions, evidence, relations, contradictions, Wiki pages, and Wiki revisions. Restore only with
`scripts/restore_event_store.sh --test-restore`; it verifies checksums, counts, current projections,
temporal intervals, the canonical historical semantic digest, contradiction history, every
metadata-referenced artifact file, and Wiki content and lineage hashes in an isolated test
database. Backup also fails before publishing its manifest if artifact metadata references a
missing, size-mismatched, or hash-mismatched file. Preserve the source database and investigate any
health warning rather than repairing history destructively.
