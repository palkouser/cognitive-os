# Event-store backup

`./scripts/backup_event_store.sh` creates a custom-format `pg_dump`, SHA-256 sidecar, zstd
artifact archive, archive checksum, and JSON manifest under the configured backup root. The
default destination is `/home/palkouser/backup/cognitive-os-archive`.

The manifest records creation time, Git commit, planned Sprint baseline, database name,
Alembic revision, file names and hashes, event and artifact counts, and governed memory, semantic,
skill, strategy, experience, corpus, routing, weakness, proposal, controlled-change, and
cross-domain pilot counts. Canonical history digests cover semantic claims, skills, strategies,
experience snapshots, corpus items, routing decisions, weakness revisions, proposal revisions,
change experiments, and cross-domain pilot runs and transfer results. It contains no
password or database URL. A combined backup assumes no active Cognitive OS writer because
database and filesystem snapshots cannot be atomic together.

The local remediation run on 2026-07-14 created both archives under
`/home/palkouser/backup/cognitive-os-archive`, verified every SHA-256 sidecar, and retained
the credential-free manifest. The artifact verifier accepts an empty initialized store and
still verifies every content-addressed blob once the `sha256` hierarchy exists.

Verified for the Sprint 20 cross-domain pilot addition on 2026-07-25: a full backup and isolated
restore round trip against `cognitive_os_integration_test`, with one recorded `domain_pilot_runs`
row, confirmed `domain_counts` and `domain_history_sha256` reflect real data, and that a tampered
`domain_counts` value in the manifest causes the restore verification to fail closed (exit 1).
