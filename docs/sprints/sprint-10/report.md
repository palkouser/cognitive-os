# Sprint 10 report

Status: Complete; remote CI green, merged to `main`, and baseline published

## Baseline

Sprint 10 branches from the validated `sprint-9-baseline` commit
`df317c4cae44f205641d94bb281537af611be6e6`. The pre-change credential-free regression was
658 passed and 20 skipped. Implementation used
`feature/sprint-10-temporal-semantic-memory` and merged through pull request 193.

## Delivered scope

- ADRs 0036 and 0037 establish append-only bitemporal claims, PostgreSQL authority, exact
  claim-revision relations and lineage, optional bounded NetworkX projection, and deterministic
  non-authoritative Wiki rendering. No graph database or approximate graph index is introduced.
- Fail-closed host configuration bounds observations, source spans, claims, evidence, relations,
  contradictions, temporal queries, graph projections, Wiki pages, and sensitivity. Provider
  direct commits, autonomous extraction or promotion, hybrid retrieval, and graph databases remain
  disabled.
- Immutable contracts cover typed semantic values, observations and audited observation queries,
  claims and revisions,
  multidimensional confidence, evidence, relations, contradictions, extraction proposals and
  decisions, temporal queries, access records, Wiki pages and lineage, and promotion decisions.
  Public contracts and lifecycle event payloads are exported as deterministic schemas.
- A frozen host-owned predicate registry, canonical identities and values, exact duplicate search,
  half-open temporal intervals, source-span validation, and deterministic functional, Boolean,
  exclusive-value, and evidence-conflict rules provide bounded semantic decisions.
- Deterministic extractors map code-context, accepted episode, task-summary,
  verification-summary, correction, and user-instruction Memory Plane revisions to proposed claims.
  Every claim is grounded through its own exact source field; repeated extraction is idempotent.
  Pre-write validation and an explicit append-only resumable transaction policy prevent rejected
  validation from leaving projections and prevent partial claim/evidence bundles.
- Explicit provider extraction sends only host-selected exact excerpts, fixed predicates, scope,
  sensitivity, schema, and budgets through `ModelExecutionService`; normalized requests and
  responses are persisted as artifacts. Host validation rejects extra fields, fabricated spans,
  unknown predicates, tool calls, changed budgets, and direct writes. Proposal and commit remain
  separate CLI operations.
- Claim creation, support, dispute, supersession, retraction, contradiction resolution and reopen,
  evidence re-evaluation, relation-cycle checks, and expected-revision concurrency preserve all
  prior history. Initial and later claim revision/evidence writes are transactional, and every
  evidence re-evaluation persists its typed result as an audit event.
- Sixteen registered semantic verifiers cover grounding, provenance, temporal integrity,
  relations, evidence, contradiction state, confidence, promotion, and Wiki integrity. Supported
  promotion requires all twelve mandatory verifier results, a decision persisted before the state
  transition, and exact evidence. Four Wiki capabilities are explicitly optional; provider
  confidence is never authoritative.
- Alembic revision `0003` creates twelve semantic and Wiki tables with append-only triggers,
  expected-revision projection functions, temporal and lookup indexes, and least-privilege runtime
  grants. There is no HNSW or IVFFlat index.
- Persistence-neutral and SQLAlchemy Core PostgreSQL repositories implement observation, claim,
  evidence, relation, contradiction, bitemporal query, Wiki revision, lineage, and access-audit
  operations. Health checks detect projection, temporal, lineage, prohibited-index, missing-event,
  orphan-event, and event-version divergence.
- Deterministic current and historical LLM Wiki v3 pages render fixed supported, disputed,
  contradiction, superseded, evidence, and revision sections with escaped content, exact lineage,
  append-only revision history, idempotent regeneration, and restore-time hash verification. Wiki
  output cannot serve as evidence.
- A bounded standard-library graph path and optional NetworkX 3.x analytical extra expose exact,
  reproducible neighbourhoods without changing authority. Core installation does not include
  NetworkX.
- The semantic CLI exposes observation, extraction, claim lifecycle, evidence, contradiction,
  temporal query, timeline, graph, Wiki, and verification operations. Credential-free health,
  smoke, benchmark, backup, isolated restore, and Wiki-regeneration paths are included.
- Architecture, data model, Wiki, security, configuration, benchmark, operations, dependency,
  donor, optional-feature, and roadmap documentation are current. CI adds semantic core,
  PostgreSQL smoke/health, benchmark, schema, install-extra, migration, and restore coverage.

## Local validation

- Required Cognitive OS checks: Ruff passed; Ruff format passed for **443 files**; Cognitive OS
  tests: **552 passed, 5 opt-in tests skipped**.
- Full repository credential-free regression: **693 passed, 28 opt-in tests skipped**.
- Focused temporal semantic-memory and benchmark-adapter suite: **41 passed**.
- Strict MyPy: **290 source files**, no issues. Bandit, schema drift, repository-language policy,
  and `git diff --check` passed.
- Dependency audit reported **no known vulnerabilities**; the local development package is the
  expected non-PyPI skip.
- Migration `0003`: downgrade to `0002`, re-upgrade to head, current-head validation, and Alembic
  drift check passed with no new upgrade operations.
- PostgreSQL repository, runtime-grant, append-only-history, benchmark-adapter, and concurrency
  integration: **16 passed** against the dedicated test database. Concurrent claim revision
  writers produced exactly one winner.
- Credential-free Memory Plane smoke retained **4 memories**, a **64-dimensional** deterministic
  embedding, one text match, one exact-vector match, and **2 access records**.
- Credential-free semantic smoke produced **3 claims**, **1 relation**, **1 contradiction**,
  **8 semantic access records**, **4 Wiki access records**, **12/12 required verifier results**
  from the 16-verifier registry, current and historical Wiki lineage, and a historical temporal
  result.
- Semantic health reported Alembic `0003`, all twelve tables, and zero projection, interval,
  evidence, lineage, revision, graph-limit, ANN-index, missing-event, orphan-event, or
  event/projection-version findings.
- Semantic benchmarks: **4/4 CI** and **20/20 seed** cases matched expected outcomes. Metrics report
  zero unsupported promotions, scope leaks, sensitivity leaks, and future-revision leaks, with
  complete deterministic provenance and Wiki lineage. Each case declares and compares exact
  observation, claim, revision, contradiction, and Wiki-page counts; the four-case PostgreSQL gate
  uses the same adapter and persists benchmark events and its report artifact.
- The local scale baseline populated **10,000 claims, 30,000 claim revisions, 50,000 evidence
  links, 10,000 relations, 1,000 contradictions, and 1,000 Wiki pages**. All seven captured query
  plans used indexes. P95 ranged from **0.225 ms** for Wiki inputs to **1.393 ms** for the bounded
  SQL plus NetworkX projection; database size was **73,692,863 bytes**. Exact plans and environment
  metadata are published in `docs/benchmarks/sprint-10-scale-baseline.json`.
- Checksummed isolated restore retained **4 memory items, 6 memory revisions, 1 embedding,
  5 observations, 7 claims, 8 claim revisions, 4 evidence links, 1 relation, 2 contradictions,
  3 Wiki pages, and 3 Wiki revisions** after smoke and the PostgreSQL benchmark. The canonical
  history and as-of query result digests matched before and after restore; the report artifact file
  matched its metadata size and hash; restored Wiki content and lineage hashes regenerated exactly.
- Core wheel, semantic-extra wheel, source distribution, and editable installation passed in
  isolated Python 3.12 environments. The core wheel excluded optional dependencies; the semantic
  extra installed NetworkX 3.6.1.

## Remote validation and release status

Pull request 193 passed all 17 required jobs in CI run
[`29445260234`](https://github.com/palkouser/cognitive-os/actions/runs/29445260234) and merged to
`main` as `ea38d5148a4dfc3446e775a8d853964004e1c38a`. The merged commit then passed all 17 jobs,
including PostgreSQL smoke, benchmark, and isolated backup/restore, in main CI run
[`29445335821`](https://github.com/palkouser/cognitive-os/actions/runs/29445335821). The final
release-report merge passed the same required main gate before `sprint-10-baseline` was published.

Gate C is complete: Sprint 9 supplies the governed Memory Plane and Sprint 10 supplies the governed
temporal semantic substrate.

## Security status

PostgreSQL remains authoritative. Runtime grants cannot update or delete semantic observations,
claim revisions, evidence, relations, contradiction history, Wiki history, lineage, or access
records. Providers receive no database credentials, write tool, predicate expansion, scope
expansion, verifier authority, or supported-promotion authority. Exact source hashes and ranges,
scope and sensitivity checks, bounded input/output sizes, Markdown escaping, and access audit fail
closed. Access rows contain identifiers, ranks, time selectors, scopes, sensitivities, and hashes,
not claim prose. No graph database, hybrid retrieval, autonomous memory promotion, model download,
credential, or secret is introduced.

## Known limitations and deferred work

- Provider extraction is explicit opt-in and requires a preconfigured structured-output provider,
  durable artifact storage, a host-owned schema, and a separate approved commit step. It never
  runs automatically and provider availability is not part of credential-free CI.
- NetworkX is optional and analytical only. The standard-library bounded traversal is the core
  path; neither path changes PostgreSQL authority.
- Projection writes and lifecycle event appends use separate authoritative/audit transactions.
  Health diagnostics expose divergence and never repair it destructively.
- Hybrid lexical/vector/graph retrieval, reranking, Context Builder, generated Wiki narrative,
  semantic belief inference, skills, strategies, and autonomous learning remain deferred to
  Sprint 11 or later.

## Restore point and Sprint 11 hand-off

Restore the released Sprint 10 baseline with `git switch --detach sprint-10-baseline`. The validated
predecessor remains available as `sprint-9-baseline`.

Sprint 11 can consume stable read contracts for current supported, proposed and disputed claims;
valid-at and known-at results; claim history; evidence bundles; open contradictions; exact claim
relations; Wiki revisions; semantic access records; confidence dimensions; provenance; scope; and
sensitivity. It can add bounded retrieval composition and Context Bundles without replacing the
Sprint 9 Memory Plane or Sprint 10 temporal claim history.
