# Event-store backup

`./scripts/backup_event_store.sh` creates a custom-format `pg_dump`, SHA-256 sidecar, zstd
artifact archive, archive checksum, and JSON manifest under the configured backup root. The
default destination is `/home/palkouser/backup/cognitive-os-archive`.

The manifest records creation time, Git commit, planned Sprint baseline, database name,
Alembic revision, file names and hashes, and event and artifact counts. It contains no
password or database URL. A combined backup assumes no active Cognitive OS writer because
database and filesystem snapshots cannot be atomic together.
