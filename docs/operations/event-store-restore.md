# Event-store restore

Only isolated restore verification is automated:

```bash
./scripts/restore_event_store.sh --test-restore
```

Configure a dedicated restore database whose name ends in `_test`. The script verifies
checksums, recreates only that database, restores the custom dump and artifact archive into
temporary targets, and validates revision, record counts, current strategy projections,
outcome-to-selection lineage, and semantic, skill, and strategy history digests. It refuses an
unrestricted or development target.

The local remediation run on 2026-07-14 restored the verified database dump into
`cognitive_os_restore_test`, extracted artifacts into a temporary directory, and validated
the Alembic revision and record counts without modifying `cognitive_os_dev` or the live
artifact root.
