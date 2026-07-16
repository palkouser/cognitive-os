# Sprint 11 report

Status: Implemented and locally validated; remote CI, review, merge, and baseline publication are
pending

## Baseline

Sprint 11 branches from the validated `sprint-10-baseline` commit `b8185db` on
`feature/sprint-11-context-builder`. No upstream LightAgent runtime file was changed.

## Delivered scope

- ADRs 0038–0040 establish host authority, deterministic hybrid ranking, immutable artifact
  persistence, and provider attachment rules. PostgreSQL, the event store, and artifact store keep
  their Sprint 9–10 authority; no second database or new migration is introduced.
- Strict immutable contracts and 38 exported context schemas cover requests, budgets, query plans,
  candidates, source references, ranking, traces, bundle revisions, provider references,
  exclusions, warnings, snapshots, health, and registry descriptors.
- A frozen retriever registry exposes explicit adapters for task and plan state, events, provider
  and tool results, artifacts, governed memory and corrections, semantic claims and bounded graph
  reads, Wiki lineage, repository indexes, and workspace reads. Memory and semantic adapters reuse
  their existing governed read and access-audit boundaries.
- Deterministic query normalization and bounded decomposition route exact metadata, lexical,
  vector, graph, recency, source-lookup, and code reads. Network retrieval, provider query
  expansion, provider source selection, approximate search, and automatic memory writes fail
  closed.
- Weighted reciprocal-rank fusion, explicit trust and verification modifiers, exact identity,
  content, and Wiki-lineage deduplication, deterministic source diversity, contradiction
  visibility, quotas, and stable tie-breaking produce auditable selection decisions.
- Progressive metadata, summary, excerpt, and full hydration obey provider, output, system, task,
  safety, candidate, item, per-source, elapsed-time, excerpt-byte, total-byte, and trace-byte
  limits. Required content fails instead of silently reducing the output reservation.
- Fixed trust-class sections keep retrieved content inside escaped data boundaries. Scope,
  sensitivity, secret, provenance, raw-path, stale-source, and suspicious-instruction checks run
  before provider execution; the provider gate rejects absent, forged, stale, or unvalidated
  Context Bundle references.
- Request, trace, rendered context, and bundle revisions are persisted as verified artifacts. Four
  append-only lifecycle events record requested, created, failed, and attached states; exact
  source, claim, memory-access, and bundle lineage is retained.
- Eight registered context verifier capabilities cover provenance, scope, sensitivity, budget,
  determinism, trace completeness, safety boundaries, and rendered-content integrity.
- Controller action execution builds and validates context immediately before a model call, sends
  it as a separate data message, attaches the typed reference, preserves output reservation, and
  records the exact attached bundle revision.
- A local-only optional CrossEncoder adapter can use an already configured model path and CPU. It
  cannot download a model or replace deterministic host ranking. RAGatouille and ANN were not
  added; exact search remains the measured default and migration `0004` is unnecessary.
- The context CLI supports build, get, trace, sources, exclusions, warnings, verify, regenerate,
  and health operations. Credential-free smoke fixtures cover all 13 source types.
- Six-case CI and 32-case seed benchmarks measure recall, precision, MRR, nDCG, required and
  evidence coverage, trace completeness, and zero scope, sensitivity, and unsafe-content leaks.
  CI now has a dedicated context job plus PostgreSQL-service smoke and benchmark gates.
- Architecture, bundle, hybrid retrieval, configuration, operations, security, benchmark, donor,
  roadmap, README, and repository-scope documentation are current.

## Local validation

- Required checks: Ruff passed; Ruff format passed for **479 files**; Cognitive OS tests:
  **574 passed, 5 opt-in tests skipped**.
- Full repository regression: **715 passed, 28 opt-in tests skipped**; contract tests:
  **65 passed**.
- Focused Context Builder and benchmark-adapter suite: **22 passed**.
- Strict MyPy: **316 source files**, no issues. Bandit, schema drift, repository-language policy,
  YAML parsing, and `git diff --check` passed.
- Dependency audit found no known vulnerabilities; the local development package is the expected
  non-PyPI skip.
- PostgreSQL and controller integration: **17 passed** against the dedicated
  `cognitive_os_integration_test` database.
- Context benchmarks: **6/6 CI** and **32/32 seed** cases matched the expected results.
- Repeated smoke builds selected the same 13 candidates and produced bundle hash
  `a0929e04d6b52a1eae284947e5abaf45f722ddfbbbdda96d55ac96adb2ee6b7d` and trace hash
  `7de285be4c9219ddb396b5e18ebebbd794df0468e8d54d00389466eefce8df66`, with zero scope,
  sensitivity, or secret leaks.
- Core wheel, semantic-extra wheel, and source distribution built and installed in isolated Python
  3.12 environments. The core wheel excluded optional dependencies and the semantic extra retained
  NetworkX 3.6.1.

## Security and authority status

Providers receive no database credentials, retrieval authority, query-expansion authority,
ranking authority, policy authority, or memory-write authority. Retrieved prose is data, never a
system or developer instruction. Context state is append-only and evidence-backed; Wiki output is
lineage-bearing retrieval material but never independent evidence. Default execution is local,
credential-free, exact, bounded, and fail-closed.

## Deferred and release work

- Learned reranking remains an opt-in local advisory experiment and is outside credential-free CI.
- ANN, unrestricted entity resolution, external retrieval, autonomous memory creation, generated
  skills, procedural learning, and provider-authored authoritative context remain deferred.
- Remote pull-request CI, review, merge to `main`, and publication of `sprint-11-baseline` require
  repository-owner workflow and are not claimed by this local report.
