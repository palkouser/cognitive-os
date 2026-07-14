# Event-store restore

Only isolated restore verification is automated:

```bash
./scripts/restore_event_store.sh --test-restore
```

Configure a dedicated restore database whose name ends in `_test`. The script verifies
checksums, recreates only that database, restores the custom dump and artifact archive into
temporary targets, and validates revision and record counts. It refuses an unrestricted or
development target.
