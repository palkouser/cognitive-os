# Sprint 13 report

Status: Released on `main`; remote CI passed and `sprint-13-baseline` published

## Baseline and authority

Sprint 13 branches from `sprint-12-baseline` on
`feature/sprint-13-strategy-evolution-graph`. PostgreSQL remains authoritative for strategy
identity, revisions, edges, selections, outcomes, statistics, and access records. The event store
retains lifecycle evidence, the artifact store retains verifier and regression evidence, and the
existing Controller remains the only execution authority. No upstream LightAgent runtime file is
changed.

The implementation was merged through PR `#196` at
`ffa8b07496dc5c673970b45f184b1a4931db5728` after every required remote check passed. The
`sprint-13-baseline` annotated tag identifies the final CI-validated release-report merge commit.

## Delivered scope

- Immutable strategy, applicability, graph, selection, plan, execution, outcome, statistics,
  access, verification, and promotion contracts with exported JSON Schemas.
- Migration `0005` with eight Strategy Evolution Graph tables, exact revision advancement,
  append-only history triggers, least-privilege grants, PostgreSQL repository, and read-only health.
- Host-owned lifecycle policy, deterministic applicability and ranking, cold-start approval,
  exact-revision skill resolution, bounded graph traversal, comparison, DOT/Mermaid export, and
  optional NetworkX projection.
- Existing-Controller `ExecutionPlan` instantiation with phase provenance, budget intersection,
  deterministic branch evaluation, cancellation/resume boundaries, static fallback, and outcome
  lineage.
- Strategy Context retrieval with exact snapshots, progressive hydration, access audits,
  trust-separated rendering, and the existing safety and sensitivity boundaries.
- Thirteen mandatory verifier capabilities covering schema, phases, graph and targets,
  applicability, skills and capabilities, fallbacks, budgets, plans, outcomes, statistics, and
  permission containment.
- Seven manually authored, credential-free initial strategies: Python bug fix, missing
  implementation, type correction, verification-driven repair, provider fallback, advisory
  review, and clarification first.
- Guarded lifecycle, registry, selection, graph, comparison, plan, statistics, access, health, and
  explicit Controller-adapter command surfaces with canonical JSON output.
- Twelve lifecycle event types, deterministic replay validation, backup/restore manifest coverage,
  a smoke path, 10-case CI and 40-case seed benchmarks, CI gates, operations documentation, and
  ADRs 0044–0046.

## Validation

- Required checks: Ruff passed; Ruff format passed; Cognitive OS tests: **592 passed, 5 opt-in
  tests skipped**.
- Full repository regression: **733 passed, 30 opt-in tests skipped**; contract tests: **65
  passed**; PostgreSQL and Controller integration: **19 passed**.
- Strict MyPy passed on **366 source files**. Bandit, schema drift, repository-language policy,
  secret baseline, wheel/sdist installation, editable installation, and `git diff --check` passed.
- Migration `0005` upgrade, downgrade-to-`0004`, re-upgrade, Alembic drift, runtime grant,
  append-only trigger, repository concurrency, and health checks passed.
- Strategy benchmarks matched **10/10 CI** and **40/40 seed** outcomes with zero unauthorized
  executions, invalid graph edges, prohibited cycles, scope leaks, sensitivity leaks, or permission
  expansions.
- The deterministic smoke verified seven strategies, resolved five exact skill revisions, produced
  no permission expansion, reproduced registry and graph state after restore, and emitted registry
  hash `e17e2fb0e6b84b8a67e6392bac7ad0536a7f132e96d39bab89c45c387fcbac7d` and smoke
  hash `84dbb31412cd601930229e1b99f08df928153f8c1448ca1b222df0027aa0f31e`.
- The isolated PostgreSQL scale fixture matched 1,000 identities, 5,000 revisions, 100,000 edges,
  25,000 selections, 25,000 outcomes, and 250,000 accesses. Candidate query p95 was **1.273 ms**,
  neighbourhood p95 **0.299 ms**, lineage p95 **0.366 ms**, statistics rebuild p95 **5.658 ms**,
  and graph snapshot p95 **0.313 ms**. Strategy relations occupied **149,258,240 bytes**.

## Restore instructions

Apply migration `0005`, create a backup with `scripts/backup_event_store.sh`, and validate only into
an isolated restore database with `scripts/restore_event_store.sh --test-restore`. The restore gate
checks exact strategy counts, append-only history hashes, current projection integrity,
outcome-to-selection lineage, artifact content, and existing semantic, Wiki, and skill state.

## Known limitations

Execution, resume, cancellation, and outcome commands require the running application Controller
adapter; the standalone CLI does not invoke tools or providers. NetworkX remains optional analysis,
not authority. Automatic strategy generation or promotion, learned ranking, adaptive routing,
dynamic capability registration, external graph databases, provider authority, and permission or
budget expansion remain disabled.

## Gate F and Sprint 14 hand-off

Gate F — Strategy-aware execution — is complete locally: Cognitive OS can represent versioned
problem-solving strategies, bind verified skills and existing capabilities, select applicable
strategies deterministically, instantiate bounded Controller plans, record complete outcomes, and
preserve strategy lineage and rebuildable statistics.

Sprint 14 Experience Compiler can consume the published strategy identity, revision, selection,
plan, execution, outcome, statistics, graph, comparison, access, problem-class, and failure-mode
contracts. It must not replace Strategy Registry authority, lifecycle policy, graph validation,
selection, Controller plan instantiation, outcome recording, statistics, or Context retrieval.
