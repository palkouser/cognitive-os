# Sprint 16 report

Status: Released; local and remote release gates passed

## Baseline and authority

Sprint 16 branches from the exact `sprint-15-baseline` commit
`190a9ed6fe0d71071dd1cabd1d4bf7ae925ab421`. The implementation follows the Group 3 technical
specification and preserves all Sprint 9–15 authority boundaries. PostgreSQL owns governed model
capability and routing state, the event store owns lifecycle evidence, the artifact store owns large
content, the Controller remains the only execution authority, and verifiers retain final acceptance
authority. No upstream LightAgent runtime file is changed.

Static routing remains the execution baseline. Shadow routing records counterfactual decisions but
cannot call a provider, mutate Controller state, expand a budget, or claim an outcome. Adaptive
routing requires measured evidence, a passing promotion assessment, explicit operator approval,
an enabled append-only policy revision, and an exact TaskSignature allowlist.

## Delivered scope

- Immutable identities, capability sources, measurements, hierarchical cohorts, estimates,
  TaskSignatures, profile revisions, observations, policies, requests, scores, exclusions,
  decisions, outcomes, statistics, experiments, promotion assessments, fallback lineage,
  multi-model plans, accesses, references, and verifier subjects with generated JSON Schemas.
- Seven credential-free replay profiles and deterministic signatures that never contain prompt or
  instruction text. Cohorts resolve exact signature, signature without skill revisions, problem
  class/output/repository, domain/output/risk, domain, then global, with an increasing uncertainty
  penalty and risk-bound fallback.
- Provider, model, health, Context-size, structured-output, tool, modality, domain, risk,
  operator-restriction, and arbitrary declared-capability hard filters before scoring. Static
  operator priority and canonical identity ordering require no measured statistics.
- Rebuildable binary Wilson intervals and deterministic continuous estimates across exact and
  parent cohorts. Missing negatively weighted cost or latency evidence is treated pessimistically,
  never as zero cost or low latency.
- Non-interfering shadow decisions, deterministic adaptive scores, minimum-sample enforcement,
  evidence-based promotion denial or eligibility, explicit approval and bounded enablement,
  disable rollback, and exact persisted-policy checks.
- Typed provider-failure classification, immutable linked runtime fallback decisions, hard-filter
  replay, maximum depth, uncertain-side-effect retry denial, post-build Context-fit fallback, and
  bounded multi-model budget intersection.
- Controller integration that attaches the exact `RoutingReference` to each provider request,
  validates the built Context Bundle against the selected model, and performs a bounded linked
  fallback before provider execution when necessary.
- Twelve routing lifecycle event types, eighteen mandatory verifier capabilities, read-only
  provider-registry adaptation, a fail-closed configuration surface, CLI, health, smoke, benchmark,
  scale, backup, restore, security, architecture, configuration, and operations documentation.
- Migration `0008` with ten routing tables, eight append-only history triggers, initial-state and
  adaptive-approval enforcement, controlled compare-and-set profile and policy revision functions,
  exact foreign keys, least-privilege grants, PostgreSQL repository, and health checks.
- Scenario-specific 16-case CI and 64-case seed suites covering hard filters, exact and parent
  cohorts, unknown evidence, shadow replay, promotion, bounded adaptive routing, fallback,
  multi-model budgets, security, profiles, observations, signatures, and statistics.
- RouteLLM was evaluated as an algorithmic reference and LiteLLM as an optional provider gateway;
  neither was added. Existing provider adapters and standard-library scoring meet the sprint without
  a new runtime dependency, external router, model download, network requirement, or GPU.

## Local validation

- Required Ruff lint and format checks passed.
- strict MyPy passed on 427 source files; Bandit passed with no findings.
- Contract schema drift and repository English-language checks passed with 148 registered event
  types.
- Cognitive OS tests passed with **635 passed and 5 opt-in tests skipped**; contract tests passed
  **65/65**; the full repository passed with **776 passed and 36 opt-in tests skipped**.
- The isolated PostgreSQL and Controller integration set passed **25/25**. Migration `0008`
  upgrade, downgrade to `0007`, re-upgrade, single-head verification, runtime grants, controlled
  revision functions, append-only history, and routing health passed.
- The isolated database and artifact backup/restore round trip passed with routing counts, history
  hash, foreign-key integrity, current-revision integrity, and access integrity verified.
- Dependency lock validation, `pip-audit`, source/wheel build, wheel installation, semantic extra,
  and editable installation passed. No known dependency vulnerability was found.
- The credential-free smoke completed the full static, shadow, promotion, approval, adaptive,
  outcome projection, and disable path. Its static decision hash is
  `0f64d07ad4817d7250e11fa0bcaeb3bc3aa3cfbf1c34611f7f3e4cb26ced98ef`; it recorded 33 decisions,
  33 accesses, 65 observations, and 155 cohort statistics with zero provider calls, unauthorized
  enablements, budget expansions, or counterfactual outcome claims.
- The direct 16-case and 64-case replay hashes are
  `000705dfe1752414840dba2b6ee2feb65a941efdb0c336f10483fef7b4ab2e1d` and
  `95435f7f40b58cbed199256ca21d5ef40c7505e34b4ee9664b4165d8f6a7bf80`. The manifest-driven
  scenario suites passed 16/16 and 64/64 with zero credential leaks, scope leaks, shadow
  interference, unauthorized enablements, or budget expansion.
- The CPU-only scale path routed **10,000** requests in **33.600 seconds**, with p50 **3.178 ms**
  and p95 **3.435 ms**, and zero provider calls.

The developer database predates the final Sprint 14 numeric confidence type, so local Alembic
autogenerate reports that historical `0006` database-state mismatch (`TEXT` versus `NUMERIC(5,4)`).
It is not introduced by migration `0008`; the clean PostgreSQL CI migration job remains the release
authority for the drift gate.

## Remote release validation

- Pull request [#202](https://github.com/palkouser/cognitive-os/pull/202) merged the Sprint 16
  implementation into `main` as `ef0ab73ad390207d0a08fd2b3f462ddebb664503`.
- The implementation commit is `74bc59d`; the compatibility correction commit is
  `73c385d213a6d800d7759ac03eb3286d7c027e1b`. The correction preserves the existing offline replay
  fingerprint when no routing reference is attached while binding the fingerprint to a present
  routing reference.
- Pull-request CI run
  [29855075979](https://github.com/palkouser/cognitive-os/actions/runs/29855075979) passed all 23 jobs,
  including model routing, provider offline replay, migration, PostgreSQL integration, security,
  quality, build, and full-repository tests.
- Post-merge `main` CI run
  [29855237569](https://github.com/palkouser/cognitive-os/actions/runs/29855237569) passed all 23 jobs
  against the merge commit. This is the authoritative remote release gate for the implementation.

## Restore instructions

Apply migration `0008`, create a backup with `scripts/backup_event_store.sh`, and restore only into
an isolated `_test` database with `scripts/restore_event_store.sh --test-restore`. The manifest
contains profile, profile-revision, policy, policy-revision, observation, decision, outcome,
statistics, experiment, and access counts plus the combined immutable routing-history hash.

## Known limitations

Capability estimates are deterministic descriptive statistics, not causal claims. Static routing
remains available without measurements; adaptive execution remains disabled until a bounded policy
revision passes the explicit promotion path. Provider-declared evidence is proposal-only. Live
provider benchmarks, learned weights, exploration, automatic promotion, external routing runtimes,
and unbounded multi-model orchestration remain opt-in or out of scope.

## Gate H and Sprint 17 hand-off

Sprint 16 completes the model-capability and governed-routing half of Gate H. Sprint 17 may consume
exact model identities, TaskSignatures, profile and policy revisions, immutable decisions,
verified outcomes, cohort statistics, experiment results, and access evidence. It must not treat
provider prose or shadow output as authority, bypass hard filters or Controller budgets, infer
acceptance, mutate provider configuration, weaken fallback safety, or enable adaptive routing
without explicit evidence and operator approval.
