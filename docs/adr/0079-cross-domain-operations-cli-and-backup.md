# ADR 0079: Cross-domain pilot gets an operator CLI and backup/restore coverage

## Status

Accepted for Sprint 20.

## Decision

Two operations gaps are closed, matching the pattern every other governed subsystem in this
repository already follows.

### CLI

`scripts/domain.py` is a new operator script, following the exact shape of `scripts/weakness.py`,
`scripts/experience.py`, `scripts/proposal.py`, and `scripts/change.py`: a single `action` positional
argument, a `--database` flag that switches `health` to a read-only Postgres check, and one JSON
object printed to stdout per invocation. It contributes no new logic — every action is a thin call
into the domain package's existing composition functions:

| Action | Composes |
|---|---|
| `run` / `run-skill` | `run_case_controlled` / `run_case_as_skill` (governed execution, ADR 0076) |
| `learn` | `run_case_with_learning` (ADR 0077) |
| `mine` / `propose` / `experiment` | `mine_domain_weaknesses` / `propose_from_domain_weakness` / `run_isolated_experiment` (ADR 0078) |
| `health` | the benchmark adapter's `_GOVERNANCE` sweep, or `PostgresDomainHealthService` with `--database` |

There was previously no `scripts/domain.py` at all — the closure report's prior rounds correctly
named this a gap, since every sibling subsystem (weakness, proposal, change, experience, corpus,
skill, strategy, semantic, context) already has one.

### Backup and restore

`src/cognitive_os/infrastructure/domains/postgres/health.py` adds `PostgresDomainHealthService`,
matching the shape of `PostgresWeaknessHealthService` and `PostgresExperienceHealthService`: table,
trigger, and controlled-function counts against the expected schema shape (7 tables, 6 append-only
triggers, 3 controlled functions — `record_domain_pilot_run`, `record_domain_transfer_result`,
`record_domain_access`), plus three orphan/violation checks — evidence rows without a parent run,
transfer results without an experiment, and any restored row that violates the
positive-transfer-versus-hard-gate constraint migration `0012` already enforces at the database
level.

`scripts/backup_event_store.sh` and `scripts/restore_event_store.sh` gain `domain_counts` (pilot
runs, problem/derivation/verification references, accesses, transfer experiments, transfer results)
and `domain_history_sha256`, following exactly the pattern the weakness, proposal, and controlled-change
additions from earlier sprints already established in these same two scripts. Restore additionally
computes `domain_integrity` and folds it into the script's final all-checks gate, the same way
`weakness_integrity`, `proposal_integrity`, and `change_integrity` already are.

## Two things this round deliberately does not do

Learning-plane and weakness-mining evidence (compilations, memories, semantic observations and
claims, corpus declarations, mined signals, proposals, change experiments) is still not written to
PostgreSQL — that decision was made in ADR 0077 and ADR 0078 and is unchanged. This round only adds
coverage for the domain execution tables that migration `0012` already created (`domain_pilot_runs`
and the transfer-experiment tables); it does not create new tables or persist anything new.

No wheel or sdist build was added. That is a separate backlog item (S20-064) and was not part of
this round's scope.

## Alternatives and consequences

Adding domain subcommands to some single top-level `cognitive-os` CLI was considered and rejected:
no such CLI exists in this repository. Every governed subsystem — weakness, proposal, change,
experience, corpus, skill, strategy, semantic, context, routing — already ships as its own
`scripts/<subsystem>.py`, and introducing a different structure for one subsystem would be the
inconsistency, not the fix.

A full `PostgresDomainRepository` (mirroring `PostgresWeaknessRepository`) was considered and
rejected as out of scope: the mandatory domain execution path is deliberately offline and
credential-free (ADR 0076), and nothing in this sprint writes a `domain_pilot_run` row through
application code — only the raw SQL functions the migration itself defines are exercised, by the
existing `test_domain_postgres.py` suite. A health service needs no repository; it only reads.

## Verification

`scripts/domain.py`: all seven actions run successfully offline, including `--wrong` and `--case`
overrides on `run` and `learn`, and `health --database` against a real PostgreSQL instance reports
`healthy: true`.

`PostgresDomainHealthService`: a new integration test
(`test_domain_health_reports_healthy_after_recording_evidence`) records one pilot run and one
transfer result through the existing migration functions and asserts `table_count == 7`,
`append_only_trigger_count == 6`, `controlled_function_count == 3`, and all three orphan/violation
counts are zero. PostgreSQL integration suite: 40/40 (was 39/39).

Backup and restore: verified end to end against an isolated database, not the shared development
database, to avoid depending on that database's own pre-existing state. A full backup/restore round
trip with one recorded `domain_pilot_runs` row reproduced the exact row and matched both
`domain_counts` and `domain_history_sha256`; a backup manifest with a deliberately corrupted
`domain_counts` value was rejected by the restore script with exit `1` and the message "restored
domain counts do not match the backup manifest" — proving the check fails closed rather than passing
silently.

While validating this round's backup script change, a real bug in an earlier edit was caught before
being applied: a first pass at inserting the `domain_counts_json` block between the existing
`change_history_sha256` line and the following line accidentally dropped the `change_candidates`
history union clause from `change_history_sha256`, which would have silently narrowed what the
controlled-change history digest covers. Caught by diffing the edited line against the untouched
copy in `restore_event_store.sh` (which must stay byte-identical to the corresponding line in
`backup_event_store.sh`) before running either script, and corrected before any backup ran.
