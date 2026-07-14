# Event-store backup

`./scripts/backup_event_store.sh` creates a custom-format `pg_dump`, SHA-256 sidecar, zstd
artifact archive, archive checksum, and JSON manifest under the configured backup root. The
default destination is `/home/palkouser/backup/cognitive-os-archive`.

The manifest records creation time, Git commit, planned Sprint baseline, database name,
Alembic revision, file names and hashes, and event and artifact counts. It contains no
password or database URL. A combined backup assumes no active Cognitive OS writer because
database and filesystem snapshots cannot be atomic together.

The local remediation run on 2026-07-14 created both archives under
`/home/palkouser/backup/cognitive-os-archive`, verified every SHA-256 sidecar, and retained
the credential-free manifest. The artifact verifier accepts an empty initialized store and
still verifies every content-addressed blob once the `sha256` hierarchy exists.
