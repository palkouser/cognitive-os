# Sprint 17 closure report

## Outcome

Sprint 17 is complete. Cognitive OS now has a governed, deterministic, diagnostic-only Weakness
Mining Engine. It consumes exact read-only revisions from existing authoritative subsystems,
records evidence-backed signals, produces authoritative exact groups and advisory no-op clusters,
scores 13 impact dimensions, packages complete lineage, creates candidate-only revisions, and
orders eligible records in the Weakness Queue. It cannot mutate sources, confirm findings
automatically, execute repairs, promote candidates, or grant provider/model authority.

Gate H and Sprint Group 3 are complete. Sprint 18 may consume the proposal-only replay and
benchmark candidate contracts, but no execution or destination-write authority transfers.

## Delivered

- 29 weakness types, immutable public contracts, fail-closed configuration, and generated schemas;
- deterministic source, failure-code, and extractor registries, signatures, exact groups,
  counterexamples, no-op clustering, comparison, impact, evidence, lifecycle, and queue services;
- 14 versioned lifecycle events and 15 mandatory verifier capabilities;
- PostgreSQL migration `0009` with ten tables, eight append-only histories, controlled lifecycle
  and queue functions, runtime grants, repository adapter, and health checks;
- backup manifest counts and historical hashes plus isolated restore verification;
- CLI, smoke path, 18-case CI manifest, 72-case seed manifest, and bounded CPU scale measurement;
- five authority ADRs, architecture, security, operations, benchmark, dependency, README, and
  roadmap documentation;
- no new runtime, ML, clustering, graph-store, network-model, or GPU dependency.

## Validation evidence

- required Ruff check and format check passed;
- strict MyPy, Bandit, schema drift, language policy, secret scan, and dependency audit passed;
- Cognitive OS suite: 643 passed, 5 opt-in tests skipped;
- full repository suite: 784 passed, 38 opt-in/integration tests skipped;
- local PostgreSQL integration: 27 passed;
- migration downgrade to `0008`, upgrade to `0009`, and drift check passed;
- isolated database and artifact backup/restore passed with weakness counts and history hash;
- wheel, sdist, wheel-install, semantic-extra install, and editable-install checks passed;
- PR #204: every one of 24 CI jobs passed;
- merged-main CI run `29859816381`: every one of 24 jobs passed;
- implementation commit `b66e10c`; implementation merge commit `2351f8b`.

## Restore

Use `scripts/backup_event_store.sh`, then `scripts/restore_event_store.sh --test-restore` against an
isolated `_test` database. Accept the restore only when checksums, all weakness table counts,
weakness history hash, orphan checks, artifact verification, and deterministic group, impact,
evidence, and queue replay agree. Full commands and boundaries are in
`docs/operations/weakness-mining.md`.

## Known limitations

- exact signatures intentionally favour explainability over semantic recall;
- default clustering is no-op and advisory; optional clustering libraries were not added;
- correlation remains non-causal unless an existing authoritative record states otherwise;
- candidate weaknesses, replay cases, and benchmark cases require later explicit review;
- scale output is a local CPU measurement, not a production-capacity claim;
- the five skipped Cognitive OS tests remain explicit opt-in external/backend tests and are not
  Sprint 17 failures.

## Release

The release baseline tag is `sprint-17-baseline`. It is created only after this report merges and
the final `main` CI run succeeds.
