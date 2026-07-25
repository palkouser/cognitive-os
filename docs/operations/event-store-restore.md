# Event-store restore

Only isolated restore verification is automated:

```bash
./scripts/restore_event_store.sh --test-restore
```

Configure a dedicated restore database whose name ends in `_test`. The script verifies
checksums, recreates only that database, restores the custom dump and artifact archive into
temporary targets, and validates revision, record counts, current strategy projections,
outcome-to-selection lineage, and semantic, skill, strategy, experience, corpus, routing,
weakness, proposal, controlled-change, and cross-domain pilot history digests and referential
integrity (every reference row resolves to its parent run or experiment, and no positive-transfer
result carries a hard gate failure). It refuses an unrestricted or development target.

The local remediation run on 2026-07-14 restored the verified database dump into
`cognitive_os_restore_test`, extracted artifacts into a temporary directory, and validated
the Alembic revision and record counts without modifying `cognitive_os_dev` or the live
artifact root.

Verified for the Sprint 20 cross-domain pilot addition on 2026-07-25: restoring a backup with one
recorded domain pilot run reproduced the exact row, `domain_counts` and `domain_history_sha256`
matched the backup manifest, and `domain_integrity` passed. A backup manifest with a deliberately
wrong `domain_counts` value was rejected with exit `1` and no silent partial restore.
