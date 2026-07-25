# ADR 0075: Cross-domain persistence, provenance, and migration 0012

## Status

Accepted for Sprint 20.

## Decision

Migration `0012` adds seven tables: `domain_pilot_runs`, `domain_problem_references`,
`domain_derivation_references`, `domain_verification_results`, `domain_transfer_experiments`,
`domain_transfer_results`, and `domain_accesses`. Only metadata and hashes are stored; statements,
derivations, solver traces, and transfer reports stay in the Artifact Store and are referenced by
digest, so these tables cannot grow into a second evidence store.

Every table except the run header carries an append-only trigger. Writes go through
`record_domain_pilot_run`, `record_domain_transfer_result`, and `record_domain_access`, which are
`SECURITY DEFINER` with a pinned `search_path`. `cogos_app` holds `SELECT` on the tables and
`EXECUTE` on those functions; `cogos_owner` owns them. Constraints enforce the domain vocabulary,
sha256 hash shape, three distinct transfer domains, and the mutual exclusion of a hard gate failure
with a positive transfer. Re-recording identical content is idempotent; re-recording the same
identity with different content raises.

The expected Alembic head moved from `0011` to `0012`. It had been duplicated as a literal in ten
health adapters; it is now `EXPECTED_MIGRATION_REVISION` in
`cognitive_os.infrastructure.postgres.tables`, bumped once per migration rather than once per
adapter.

Benchmark cases, constants, and unit definitions require `ProvenanceRef` with source, revision,
licence, redistribution flag, and contamination notes before activation. All Sprint 20 fixtures are
authored in this repository under Apache-2.0 and derive from no public benchmark set, so no
third-party benchmark material is redistributed and there is no contamination path from a published
evaluation set.

## Alternatives and consequences

Reusing the Sprint 19 change tables was rejected: transfer arms and domain dispositions have no
natural home there and would have overloaded the change vocabulary. Storing derivations inline was
rejected because solver traces are unbounded in principle.

The consequence is that `0012` is small and deliberately non-empty, and that the domain evidence
path is auditable with the same tooling as every prior sprint.

## Verification

`tests/integration/postgres/test_domain_postgres.py` verifies table, function, and trigger
presence, refusal of unknown domains and malformed hashes, refusal of divergent rewrites, the
positive-transfer hard-gate constraint, the distinct-domain constraint, append-only update and
delete refusal, and that `cogos_app` holds exactly `SELECT`. The `0011 -> 0012 -> 0011 -> 0012`
round trip was executed against PostgreSQL 18 with pgvector 0.8.2.
