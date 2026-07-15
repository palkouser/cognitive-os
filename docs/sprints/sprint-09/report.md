# Sprint 9 report

Status: Implementation complete; remote CI and baseline tag pending

## Baseline

Sprint 9 branches from the validated `sprint-8-baseline` commit
`64e4fa0af91f6c0d621c1fac49a625376ea5e454`. The pre-change credential-free regression was
630 passed and 18 skipped. The active branch is `feature/sprint-9-governed-memory-plane`.

## Delivered scope

- ADR 0035 and active repository policy establish PostgreSQL memory authority, existing event and
  artifact authority, provider non-authority, and exact-only retrieval.
- Fail-closed host configuration covers content, source, revision, query, vector, batch, worker,
  sensitivity, audit, export, and benchmark limits. Provider direct writes, automatic promotion,
  network model download, HNSW, and IVFFlat are sealed off.
- Nine typed memory content families, identity, scope, creator, revision, provenance, mutation,
  retrieval, embedding, audit, and trace contracts are immutable and exported as 35 deterministic
  Memory Plane schemas. There is no `fact` or hybrid retrieval value.
- Nine lifecycle events use the existing event catalog. Dedicated memory streams use
  expected-version writes; replay rejects creation duplication, revision gaps, rewrites, and
  illegal transitions. Health diagnostics compare creation events and table rows.
- Alembic revision `0002` creates `memory_items`, `memory_revisions`, `memory_sources`,
  `memory_embeddings`, and `memory_accesses` with pgvector 0.8.2 on PostgreSQL 18. Revision and
  access history is protected by database triggers and runtime grants; current projection advances
  only through an exact-revision function. No approximate index exists.
- Persistence-neutral and PostgreSQL repositories implement idempotent creation, append-only
  revisions, deterministic reads, source history, PostgreSQL full text, exact cosine vector
  retrieval, embeddings, and access audit. Canonical content hashes are checked on reconstruction.
- Governance denies provider-only, automatic-by-default, secret-bearing, oversized, out-of-scope,
  over-sensitive, and self-authorized verified writes without partial rows. Promotion requires a
  trusted actor plus accepted trajectory evidence and rejects explicit source conflicts.
- Accepted Sprint 8 trajectories deterministically project episode, task summary, verification
  summary, and bounded repository code context. Rejected, incomplete, or hash-mismatched
  trajectories fail before persistence. Repeated ingestion is idempotent and uses no model call.
- A dependency-free deterministic hashing provider and optional local-only Sentence Transformers
  adapter implement the embedding port. Models must be preconfigured locally and no health check
  downloads data. Embeddings bind memory revision, model identity, dimension, and content hash.
- Single-mode retrieval enforces scope, status, sensitivity, and query budgets. Every returned row
  has an append-only audit attempt; configured audit failure is fail-closed. The LightAgent adapter
  has no database import or verified-write authority.
- Read-only health and credential-free smoke commands, combined memory-aware backup manifests,
  isolated restore validation, four-case CI and sixteen-case seed benchmark manifests, dedicated CI
  gates, architecture, data-model, security, configuration, benchmark, and operations documents are
  included.

## Local validation

- Full repository regression: **658 passed, 20 opt-in tests skipped**.
- Focused Memory Plane unit/schema suite: **30 passed** after the final event integration update.
- PostgreSQL repository integration: **2 passed** against real PostgreSQL 18 and pgvector 0.8.2.
- Migration: upgrade `0001 -> 0002`, downgrade `0002 -> 0001`, re-upgrade, and Alembic drift check
  passed. Alembic reports no new upgrade operations.
- Credential-free smoke: **4 memories**, verified promotion, **64-dimensional** embedding, one text
  and one exact-vector match, **2/2 access records**, retraction, and **3 preserved revisions**.
- Health report: Alembic `0002`, pgvector `0.8.2`, all five tables present, zero projection errors,
  zero missing provenance, zero orphan embeddings, zero event/table gaps, and zero ANN indexes.
- Checksummed isolated restore retained **4 memory items, 6 revisions, and 1 embedding**; restored
  exact cosine self-similarity was **1.000000**.
- Memory benchmarks: **4/4 CI** and **16/16 seed** cases matched declared outcomes with zero scope
  leaks, zero sensitivity leaks, complete provenance, and complete access-audit metrics.
- Ruff, Ruff format for 397 files, strict MyPy for 259 source files, Bandit, schema drift,
  repository-language policy, and `git diff --check` passed.
- Dependency audit reported **no known vulnerabilities**; the local development package is the
  expected non-PyPI skip.
- Isolated wheel/sdist installation and editable-install verification both passed on Python 3.12.

## Security status

The runtime role has SELECT/INSERT only on immutable memory history and cannot update or delete it.
The migration uses the separately controlled bootstrap connection for extension management; it
does not grant provider or runtime superuser access. Exact vector statements bind validated finite
values and require provider, model, dimension, and content hash. Access logs contain identifiers,
rank, score, scope, sensitivity, and hashes, never memory content.

## Known limitations and deferred work

- A real optional Sentence Transformers model was not configured, so its live CPU load/inference
  path remains opt-in; deterministic embeddings cover normal CI.
- The suggested 10,000-record exact-retrieval scale baseline and external local LongMemEval and
  MemoryAgentBench compatibility importers are P1/P2 follow-up measurements, not merge blockers.
- Semantic claims, belief state, inferred contradiction, knowledge graphs, Wiki rendering, hybrid
  retrieval, reranking, Context Builder, skills, strategies, and autonomous learning remain
  explicitly deferred to Sprint 10 or later.
- Lifecycle persistence and the PostgreSQL projection are separate authoritative/audit writes. The
  health command reports divergence and never performs destructive automatic repair.

## Restore point and hand-off

The Sprint 9 tag will be `sprint-9-baseline` and is created only after the remote pull-request CI is
green. Before publication, restore Sprint 8 with `git switch --detach sprint-8-baseline`. After
publication, restore Sprint 9 with `git switch --detach sprint-9-baseline`.

Sprint 10 can consume typed observations and corrections, verified episode/task/verification
summaries, exact source lookup, immutable revision history, and access audit without replacing the
Sprint 9 persistence or governance foundations.
