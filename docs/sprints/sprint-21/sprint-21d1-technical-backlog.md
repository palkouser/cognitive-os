# Sprint 21D1 Technical Backlog

## Pre-registered Learning Surface and Experience Memory Graph Baseline

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution
- **Revision:** 1
- **Prepared:** 2026-07-30
- **Required predecessor release:** `sprint-21c3-reality-baseline`
- **Required predecessor tag object:** `497f959bc55989541016a61bd9034e12523b8573`
- **Required predecessor commit:** `05809446c726444146d85aad22808e10ce87ca3e`
- **Required predecessor implementation PR:** `#215`
- **Required predecessor post-merge CI:** `30571166301`, success, 29 of 29 jobs
- **Planning head at preparation:** `origin/main` at
  `1856b8539b690528116816c105d82810e67f00d9`
- **Gate-close documentation PR:** `#216`
- **Planning-head CI:** `30572361952`, success on the exact planning head
- **Required parent migration head:** `0015`
- **Implementation branch:** `feature/sprint-21d1-learning-surface-emg`
- **Planned migration:** none
- **Next available migration:** `0016`, unallocated unless a measured persistence gap
  cannot be represented by existing artifact and learned-evidence authority
- **Target baseline tag:** `sprint-21d1-emg-baseline`
- **Stage gate:** Gate D1 — Pre-registered Learning Surface and EMG Baseline
- **Successor gate:** Gate L2 remains closed; training, promotion, activation, canary,
  and rollback belong to Sprint 21D2
- **Execution profile:** local, CPU-first, single maintainer, offline normal CI, no
  live-provider dependency
- **Repository language:** English only

---

## 0. Authority and execution contract

This backlog is the implementation authority for Sprint 21D1. It refines:

- `docs/sprints/sprint-21/sprint-21c3-report.md`;
- `docs/sprints/sprint-21/gate-c3-assessment.md`;
- `docs/sprints/sprint-21/sprint-21d1-handoff.md`;
- the annotated `sprint-21c3-reality-baseline` release;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`.

When a proposed implementation conflicts with a confirmed repository invariant, the
implementer must preserve evidence integrity, evaluation separation, bounded execution,
artifact lineage, and deterministic fallback. The conflict and the smallest resolution
must be recorded in an ADR or the D1 report before changing authority or evaluation
semantics.

### 0.1 Release-grade meaning of done

D1 is not complete when graph objects can be serialized. Completion requires:

1. revalidation of the C3 tag, both relevant `main` heads, exact-head CI, branch
   protection, migration head, and Artifact Store isolation;
2. a surface audit whose decision is committed before held-out metrics are read;
3. an immutable feature schema, label contract, group policy, evaluation manifest,
   decision policy, and strongest deterministic baseline for the primary surface;
4. at least 200 unique held-out verifier-backed outcomes and at least 20 decisions that
   the later learned policy could change;
5. at least 80 failed-to-success graph pairs across coding, logic, and mathematics,
   including 20 freshly reproducible non-coding pairs;
6. byte-resolvable graph, edit-path, retrieval, and metric artifacts with learned
   lineage;
7. no-memory, lexical, MiniLM vector, exact-signature, and bounded simple-graph
   comparison on a frozen unseen-task protocol;
8. advisory Experience Graph `ContextCandidate` integration without execution,
   acceptance, promotion, or activation authority;
9. an evidence-backed FGW go/no-go decision and no unused dependency;
10. deterministic replay, resource-bound, corruption, restart, backup/restore,
    PostgreSQL, and complete local verification evidence;
11. protected PR merge, successful exact-head post-merge `main` CI, one annotated and
    remotely verified D1 tag, report, gate assessment, and D2 handoff.

Final PR, merge, CI, and tag handles belong in the tag annotation or external release
evidence rather than a tracked self-referential report.

### 0.2 Efficiency-first implementation rule

Use, in order:

1. existing Experience Compiler contracts and source resolution;
2. the existing Artifact Store, Event Store, learned-evidence ledger, Context Builder,
   MiniLM provider, benchmark helpers, and release scripts;
3. the standard library;
4. the already installed `networkx` optional dependency;
5. the smallest D1-specific adapters that remain.

D1 must not add:

- a graph database;
- a second vector index or embedding model;
- a generic graph framework;
- a second context-assembly system;
- a model-serving process;
- a provider dependency on the critical path;
- a new training framework;
- migration `0016` merely to persist 80 graph pairs;
- a GNN, FGW library, or approximate graph index before a measured simpler-baseline
  gap exists.

### 0.3 Historical evidence rule

The 60 C3 coding correction manifests are immutable historical evidence. They use a
legacy wall-clock `created_at` and therefore cannot be proven equal by recompilation.
D1 must:

- leave the original records and bytes untouched;
- resolve and hash their ordered source events and outcome artifacts;
- mark every derived pair `legacy_recompilation_unavailable=true`;
- distinguish source-resolution verification from recompilation verification;
- never rewrite timestamps or manifests to make a verifier green.

Fresh D1 domain pairs must use a fixed epoch and pass byte-identical recompilation.

### 0.4 Gate L2 boundary

D1 performs surface selection, pre-registration, deterministic baselining, graph
projection, retrieval evaluation, and advisory context integration. It performs:

- no learner fitting;
- no learned-component activation;
- no promotion assessment claiming learned benefit;
- no canary that changes agent behavior;
- no use of real governed runs in a training snapshot.

An inert dataset or artifact-lineage registration is permitted. Gate L2 remains closed
until D2 proves material downstream benefit and completes shadow, OOD, anti-forgetting,
approval, activation, restart, kill-switch, and rollback evidence.

---

## 1. Starting evidence and inherited limitations

### 1.1 Exact release state

The protected C3 implementation release is the annotated
`sprint-21c3-reality-baseline` tag, which peels to
`05809446c726444146d85aad22808e10ce87ca3e`. Its implementation PR is `#215`, and
post-merge CI run `30571166301` succeeded with 29 of 29 jobs.

The C3 gate-close documentation subsequently merged through PR `#216`.
At backlog preparation, `origin/main` is
`1856b8539b690528116816c105d82810e67f00d9`, with exact-head successful CI run
`30572361952`. D1 must branch from the revalidated current `origin/main`, not discard
the gate-close documentation by branching directly from the older peeled tag.

Migration head remains `0015`; `0016` is available but unallocated.

### 1.2 C3 quantitative evidence

| Evidence | Frozen result |
|---|---:|
| Coding task packages | 30 across 6 families and 30 repository groups |
| Unique executed outcomes | 214 |
| Offline coding outcomes | 150 |
| Re-executed governed benchmark outcomes | 64 across 6 domains |
| Correction trajectories | 60 over 30 coding tasks and 4 strategies |
| Corpus items | 420, group-aware, zero split crossing |
| Accepted evaluation-only observations | 896 |
| Quarantined observations | 64 |
| Real governed runs in training snapshots | 0 |
| Local embedding dimension | 384 |
| MiniLM recall@5 | 0.917 |
| MiniLM MRR@10 | 0.711 |
| Float16 total-storage reduction | 32.4%, below the 35% migration threshold |

The 214 unique outcomes, not the 960 intake observations, are the starting denominator
for primary-surface eligibility. Duplicate intake references must never inflate sample
size.

### 1.3 Frozen material

The following identities cannot be regenerated or tuned against:

| Material | Identity |
|---|---|
| Coding tasks | 30 templates, seed 1, UUIDv5 over template and seed |
| C3 retrieval benchmark | manifest hash `c9d2ac44731e81f2443545111c8e4832f848d63b68557862a7319cdd8beeca9d` |
| Group split | `sprint21c3-group-aware-split-v1`, seed 15, 30 groups |
| MiniLM | `sentence-transformers/all-MiniLM-L6-v2` revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| MiniLM tree digest | `98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229` |
| Historical correction manifests | 60 C3 coding trajectories |
| Development Artifact Store fingerprint | `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf`, 5 files |

### 1.4 Operational limitations

- There is one collaborator. Required approving reviews remain disabled; the 27
  required contexts and `enforce_admins` remain enabled.
- `reality-inputs-core` runs but is not one of the 27 required contexts. Changing
  branch protection needs separate operator authority.
- The inconsistent development Artifact Store pair remains untouched. D1 must record
  its fingerprint before and after and produce zero writes to it.
- OpenRouter free produced 0 correct results in 10 C3 attempts. It is not required for
  D1 and no live provider call is planned.
- The C3 provider fixture cannot rank frontier providers; it is not a D1 learning
  surface.
- The open-development policy applies only to public, rights-cleared material.
  Credentials and restricted inputs remain excluded.

---

## 2. Sprint goal and Gate D1

### 2.1 Goal

Establish an honest decision problem for D2 and prove the simplest bounded Experience
Memory Graph path before introducing a more complex learner:

- **provisional primary surface:** `governed.outcome_triage`, predicting an accepted
  verifier outcome from pre-outcome evidence so a later policy can choose
  `verify_now`, `request_repair_context`, or `abstain`;
- **provisional secondary surface:** `experience.correction_context`, retrieving a
  verified failed-to-success edit path as advisory repair context.

The surface audit may reject either provisional choice. It may not weaken the sample,
actionability, leakage, attribution, or verifier requirements to preserve the choice.

The primary policy can prioritize work but can never bypass the independent verifier.
A candidate cannot become accepted because a predictor scored it highly.

### 2.2 Gate D1 pass conditions

Gate D1 passes only when all of the following are true:

1. the C3 release tag, current `origin/main`, both exact-head CI handles, branch
   protection, migration head, and store-isolation controls are revalidated;
2. all four handoff candidate surfaces are audited for leakage, label integrity,
   class balance, group structure, attribution, deterministic headroom, actionability,
   sample size, and decision cost;
3. one primary and one secondary surface are selected and their pre-registration
   artifact is committed before held-out metrics are inspected;
4. the primary label is an independent accepted verifier outcome and the feature
   allowlist contains only data available before that outcome;
5. prohibited fields, including hidden verifier content, solution/control material,
   outcome status or hash, post-outcome timing, provider response body, and
   answer-revealing strategy labels, fail the leakage validator;
6. at least 200 unique held-out verifier-backed outcomes remain after deduplication and
   eligibility checks;
7. at least 20 primary-surface examples would change the advisory triage action
   relative to a declared deterministic baseline without bypassing verification;
8. evaluation roles, group membership, examples, features, labels, decisions,
   baselines, metrics, bootstrap procedure, and abstention handling are immutable and
   hash-bound;
9. 60 historical coding pairs resolve every required event and artifact without
   mutating the legacy manifests;
10. 20 fresh deterministic pairs cover logic and mathematics and pass byte-identical
    Experience Compiler recompilation;
11. the combined graph set contains at least 80 failed-to-success pairs across at
    least three domains, with zero group crossing and 100% source resolution;
12. every correction edit script deterministically transforms its failed graph into
    the declared successful graph and passes canonical-hash verification;
13. malformed, cyclic, oversized, over-depth, secret-bearing, unresolved, and
    poisoned graphs fail closed;
14. no-memory, lexical, MiniLM vector, exact-signature, and bounded simple-graph arms
    run on the same frozen queries and group exclusions;
15. unseen-task top-5 relevant-path recall is at least 0.70 and MRR@10 at least 0.50
    for at least one bounded retrieval arm;
16. the simple-graph arm is reported against the strongest simpler arm even when it
    ties or loses, with deterministic ranking and explicit timeout counts;
17. graph retrieval p95 is at most 2 seconds on the declared reference host, no
    individual graph-edit comparison exceeds 250 ms, and a query returns at most 10
    results;
18. Experience Graph results enter the existing Context Builder as hash-resolvable,
    verified, advisory, non-required, non-pinned candidates and confer no execution or
    acceptance authority;
19. FGW is approved for D2 only if residual error, projected material benefit,
    resource budget, dependency, and license review justify it; otherwise it is
    rejected with no new dependency;
20. integrity, replay, restart, backup/restore, scratch-store matrix, schema,
    packaging, security, language, and full regression checks pass;
21. the protected release sequence, Gate D1 assessment, D1 report, annotated tag, and
    D2 handoff complete while Gate L2 remains closed.

### 2.3 Gate semantics

A null graph result does not make the benchmark dishonest and does not require graph
complexity to be added. D1 may pass with a graph arm that loses to vector retrieval if:

- the graph construction and evaluation conditions pass;
- the loss is reported;
- the strongest simpler arm is selected for D2;
- FGW is rejected unless the pre-registered go criteria are met.

D1 fails when the primary surface lacks 200 eligible outcomes or 20 changeable
decisions, when evaluation leakage exists, when graph source lineage is unresolved, or
when the release sequence is incomplete.

---

## 3. Scope boundaries

### 3.1 In scope

- primary- and secondary-surface audit and pre-registration;
- canonical feature/label view over C3 outcome evidence;
- group-aware evaluation manifest and deterministic baselines;
- a bounded evaluation-only shortfall campaign if deduplication leaves 150–199
  eligible primary outcomes;
- 20 fresh controlled failed/success domain pairs: 10 logic and 10 mathematics;
- action-decision graph contracts and two focused source adapters;
- deterministic graph normalization, validation, canonical hashing, and edit paths;
- artifact-backed EMG root manifest and learned artifact lineage;
- lexical, exact-signature, MiniLM vector, and bounded NetworkX graph-edit baselines;
- advisory Context Builder integration;
- one operator surface by extending `scripts/experience.py`;
- focused credential-free CI and full release evidence;
- FGW/license/dependency ADR.

### 3.2 Explicitly out of scope

- learner fitting or hyperparameter tuning;
- trained-model artifacts;
- learned activation, promotion, canary, rollback, or behavior-changing routing;
- using real governed runs for training;
- new live provider campaigns;
- provider leaderboard or model-quality claims;
- graph database, GNN, graph neural embeddings, approximate graph index, or custom
  MCS implementation;
- automatic source ingestion;
- `10^6` scale claims;
- repair of the inconsistent development Artifact Store pair;
- branch-protection changes or fabricated reviews;
- modification of the 60 historical C3 correction manifests.

### 3.3 Conditional surface shortfall

If the primary audit retains:

- **200 or more** eligible outcomes: use the frozen C3 evidence and generate none;
- **150–199**: pre-register a deterministic, provider-free shortfall manifest and
  create only the number required to reach 200, capped at 50;
- **fewer than 150**: stop, keep Gate D1 open, and replan the surface. Do not generate
  an unbounded campaign inside D1.

The shortfall campaign must use new group identities, the existing sandbox and
verifiers, fixed seeds, exact counting, evaluation-only learned intake, and zero
provider/network calls. Its manifest must exist before execution.

---

## 4. Minimal architecture

### 4.1 Reuse map

| Need | Existing authority to reuse | D1 addition |
|---|---|---|
| outcome evidence | `CodingOutcomeRecorder`, learned intake, Event/Artifact Stores | pre-outcome view and eligibility audit |
| trajectories | `ExperienceCompiler`, domain learning services | two graph adapters |
| corpus roles | Corpus Factory and learned dataset records | evaluation and graph-set manifests |
| embeddings | frozen MiniLM provider | graph/query text projection |
| graph algorithms | optional `networkx>=3.6,<4` | bounded validation and GED rerank |
| artifact lineage | `LearnedArtifactStore`, `LearnedArtifactLineage` | graph-root and metric lineages |
| context | `ContextCandidate`, retriever registry, Context Builder | `EXPERIENCE_GRAPH` source and retriever |
| operations | `scripts/experience.py`, `reality_integrity` | graph commands and authority links |
| persistence | PostgreSQL IDs/metadata plus Artifact Store bytes | no new schema by default |

### 4.2 Primary surface contract

`governed.outcome_triage` has:

- one sample per unique authoritative outcome;
- label `accepted_by_independent_verifier: bool`;
- advisory actions `verify_now`, `request_repair_context`, and `abstain`;
- a versioned feature allowlist limited to values available before terminal outcome;
- exact source event/artifact hashes outside the feature vector;
- group identity that prevents the same task/repository family appearing on both
  sides of a later fit/evaluation boundary;
- an explicit cost matrix that never rewards skipping final verification.

Provider or model identity may be audited as an attribution feature but cannot act as
approval authority and is excluded from the default feature schema unless it adds
pre-registered value without collapsing a group into an identity lookup.

### 4.3 Primary baselines

The frozen baseline ladder is:

1. `always_verify_now`;
2. majority-outcome prediction;
3. visible-contract rule using only allowed pre-outcome checks;
4. grouped frequency lookup with unseen-group abstention.

D2 must beat the strongest valid rung, not only the majority baseline. The D1 result
bundle records coverage, accepted/rejected confusion, calibration bins, abstention,
decision changes, hidden-verifier executions projected, latency, and per-domain/group
results.

### 4.4 Action-decision graph

Add focused contracts under the existing experience domain:

- `ExperienceGraphNodeKind`;
- `ExperienceGraphEdgeKind`;
- `ExperienceGraphNode`;
- `ExperienceGraphEdge`;
- `ActionDecisionGraph`;
- `FailedSuccessGraphPair`;
- `GraphEditOperation`;
- `GraphEditPath`;
- `ExperienceMemoryGraphManifest`;
- `ExperienceGraphQuery`;
- `ExperienceGraphResult`;
- `GraphResourceLimits`.

Minimum node kinds:

- observation;
- reasoning;
- tool action;
- tool result;
- verifier;
- correction;
- accepted outcome.

Minimum edge kinds:

- `next`;
- `branches_to`;
- `caused_by`;
- `supports`;
- `contradicts`;
- `corrected_by`;
- `recovers_to`.

Nodes and edges have stable logical IDs, typed attributes, source hashes, and canonical
ordering. Host paths, credentials, raw authorization material, hidden controls, and
unbounded output bodies are forbidden.

### 4.5 Focused adapters

Implement only:

1. `CodingCorrectionGraphAdapter`, deriving a pair from an immutable C3
   `CorrectionTrajectoryManifest` and resolved outcome events/artifacts;
2. `DomainTrajectoryGraphAdapter`, deriving a pair from a fresh deterministic
   `ExperienceCompilationResult`.

The adapters emit the same graph contract. They do not become a generic source-plugin
platform.

### 4.6 Graph normalization and edit path

Normalization must:

- remove non-semantic clocks and environment paths;
- retain domain, task signature, action type, verifier result, correction relation,
  source identity, and content hashes;
- sort nodes and edges canonically;
- reject duplicate logical IDs or unresolved sources;
- prove a directed acyclic action sequence;
- produce a SHA-256 canonical graph hash.

The initial edit path uses deterministic labeled set differences:

- insert/delete/relabel node;
- insert/delete/relabel edge;
- stable ordering by operation type and logical ID.

Applying the script to the failed graph must reconstruct the successful graph exactly.
NetworkX GED is a ranking signal, not the authority for the stored edit script.

### 4.7 Resource bounds

The pre-registered defaults are:

| Resource | Bound |
|---|---:|
| nodes per graph | 64 |
| edges per graph | 128 |
| path depth | 32 |
| vector shortlist | 10 |
| returned results | 10 |
| per-pair GED timeout | 250 ms |
| complete query budget | 2 s |
| cross-task similarity neighbors | 3 |

Any change must be committed before the affected benchmark. A timeout produces an
explicit bounded result and metric, never a silent omission or unbounded retry.

### 4.8 EMG persistence

Persist graph pairs, edit paths, query manifests, and metrics as canonical JSON artifacts.
Store a compact root manifest containing:

- graph-set identity and schema versions;
- source event/artifact IDs and hashes;
- pair and graph hashes;
- group/domain/task identities;
- legacy recompilation flags;
- MiniLM identity;
- graph-resource policy;
- cross-task similarity edges;
- child artifact references.

Register root and result artifacts through existing `LearnedArtifactLineage` attached
to a D1 evaluation dataset. Use roles `DATASET`, `SPLIT_MANIFEST`, `REPORT`, and
`METRIC_BUNDLE` as appropriate. PostgreSQL remains authoritative for dataset and
lineage identity; graph payload bytes remain in the Artifact Store.

Migration `0016` is justified only if a demonstrated query or integrity requirement
cannot be met by this representation. Convenience is not sufficient.

### 4.9 Retrieval arms

All arms receive the same query, group exclusions, candidate pool, resource policy, and
relevance judgments:

1. no memory;
2. lexical text ranking;
3. exact task/action signature;
4. frozen MiniLM cosine ranking;
5. MiniLM shortlist plus bounded labeled GED reranking.

Report top-k recall, MRR@10, nDCG@10, coverage, abstention, timeout/failure count,
ranking stability, p50/p95 latency, peak memory, and results by domain and seen/unseen
task. The graph arm cannot use outcome labels or correction bytes from the query group.

### 4.10 Context Builder boundary

Add `ContextSourceType.EXPERIENCE_GRAPH` and the corresponding default trust mapping.
`ExperienceGraphContextRetriever` may emit `ContextTrustClass.VERIFIED` only when:

- graph root, pair, edit-path, and source artifact hashes all resolve;
- the source outcome was independently verified;
- the query group is excluded from the candidate source group;
- no safety or size bound failed.

The result is:

- purpose `REPAIR` or `ADVISORY`;
- never required;
- never pinned;
- bounded and provenance-rich;
- a suggested correction path, not an executable patch;
- unable to accept, promote, or activate anything.

### 4.11 FGW decision

Do not install FGW in D1. Approve a D2 experiment only when:

- the simple graph arm leaves a named structural error class;
- projected improvement is at least 0.05 absolute top-5 recall or MRR over the
  strongest simpler arm;
- the 2-second query budget and bounded memory remain credible;
- a maintained dependency has acceptable transitive dependencies and license;
- the implementation is clean-room and does not copy incompatible source.

The referenced EMG preprint is CC BY-NC-SA 4.0. Its concepts may inform the design, but
paper code or assets must not be copied into this Apache-licensed repository. A no-go
decision is a valid D1 output.

### 4.12 Expected focused code boundary

Prefer the following small boundary; adjust names only when the current package layout
demonstrably offers a closer existing home:

| Area | Expected location |
|---|---|
| graph contracts | `src/cognitive_os/domain/experience_graph.py` |
| projection and edit paths | `src/cognitive_os/experience/graph_projection.py` |
| bounded retrieval | `src/cognitive_os/experience/graph_retrieval.py` |
| primary-surface audit/evaluation | existing `src/cognitive_os/learning/` modules |
| context source/retriever | existing `domain/context.py` and `context/retrieval.py` |
| artifact/ledger use | existing learned application and infrastructure services |
| benchmark adapter | existing `src/cognitive_os/benchmarks/` conventions |
| operator entry point | extend `scripts/experience.py` |
| unified status | extend `coding/reality_integrity.py` |
| focused tests | matching `tests/cognitive_os/` and `tests/contract/` packages |
| PostgreSQL contracts | existing learned-store integration suite |

Do not add a top-level `emg` subsystem that duplicates experience, context, benchmark, or
learned-evidence ownership. Generated graph evidence belongs under the isolated evidence
root and is not committed as thousands of individual repository files.

### 4.13 End-to-end data flow

```text
C3 outcomes ──> eligibility/leakage audit ──> frozen primary baseline
      │
      ├── 60 historical correction manifests ──> coding graph adapter ──┐
      │                                                                │
fresh logic/math failed + success ──> Experience Compiler ──> domain adapter
                                                                       │
                         canonical graph pairs + edit paths <───────────┘
                                      │
                       Artifact Store + learned lineage
                                      │
          lexical / signature / MiniLM / bounded GED benchmark
                                      │
                         advisory ContextCandidate only
```

The primary baseline and EMG benchmark share release evidence but remain different
surfaces. Graph pairs are not multiplied into fake independent primary examples, and
intake observations are not multiplied into fake outcome identities.

---

## 5. Detailed work items

The execution contains 54 independently reviewable tasks in eight epics. `P0` is
gate-blocking. `P1` is required unless the referenced precondition makes it
inapplicable.

## EPIC S21D1-E00 — Baseline, evidence, and release control

### S21D1-000 — Revalidate the exact D1 starting point

- **Priority:** P0
- **Deliver:** a checked baseline note with current branch, `origin/main`, C3 tag
  object and peeled commit, PRs `#215/#216`, exact CI runs, migration heads, branch
  protection, required contexts, and collaborator count.
- **Acceptance:** D1 branches from the current verified `origin/main`; the C3 tag is
  verified as predecessor evidence; any drift is reconciled before code changes.
- **Evidence:** command transcript and hashes in the D1 report.

### S21D1-001 — Isolate the D1 evidence pair

- **Priority:** P0
- **Depends on:** S21D1-000
- **Deliver:** D1-specific PostgreSQL environment, Artifact Store root, sandbox root,
  backup root, and scratch roots.
- **Acceptance:** the development-pair fingerprint equals the full inherited hash
  before and after D1 and receives zero writes; the verification matrix targets only
  scratch stores.
- **Evidence:** before/after fingerprint and resolved configuration without secrets.

### S21D1-002 — Freeze the C3 evidence inventory

- **Priority:** P0
- **Depends on:** S21D1-001
- **Deliver:** canonical inventory for 214 outcomes, 60 correction manifests, 30
  groups, 420 corpus items, 960 intake observations, MiniLM identity, and source hashes.
- **Acceptance:** unique outcomes are reconciled separately from intake observations;
  every counted row has one authority and unresolved items are quarantined.
- **Evidence:** signed/hash-bound inventory artifact and count reconciliation.

### S21D1-003 — Record inherited limitations without workarounds

- **Priority:** P0
- **Deliver:** D1 limitation register naming single-maintainer review mode, the
  non-required C3 check, store inconsistency, OpenRouter non-criticality, and legacy
  recompilation status.
- **Acceptance:** no required check or `enforce_admins` is weakened; no approval is
  fabricated; no store remediation or provider retry is smuggled into D1.
- **Evidence:** report section and release annotation.

### S21D1-004 — Open the draft implementation PR in wave 1

- **Priority:** P0
- **Depends on:** S21D1-000
- **Deliver:** draft PR against current protected `main` with backlog, scope, gate,
  migration default, and initial baseline evidence.
- **Acceptance:** PR CI exercises the branch before bulk graph artifacts are created;
  branch protection remains unchanged.
- **Evidence:** PR URL and initial check run.

## EPIC S21D1-E01 — Surface audit and immutable pre-registration

### S21D1-010 — Add surface-audit contracts

- **Priority:** P0
- **Deliver:** contracts for surface candidate, eligibility reason, label source,
  feature timing, group identity, action, baseline, sample audit, and decision record.
- **Acceptance:** canonical JSON/hash behavior, UTC rules, enums, and fail-closed
  validation follow existing learned contracts; no new repository is introduced.
- **Evidence:** unit tests and schema export.

### S21D1-011 — Audit all four candidate surfaces

- **Priority:** P0
- **Depends on:** S21D1-002, S21D1-010
- **Deliver:** audit of correction ranking, correction-context retrieval,
  verifier-outcome triage, and strategy selection.
- **Acceptance:** each records eligible count, label provenance, positive/negative
  balance, group count, deterministic headroom, changeable decisions, attribution,
  action cost, leakage risks, and disposition.
- **Evidence:** immutable surface-audit artifact with no held-out metric lookup.

### S21D1-012 — Define the pre-outcome feature allowlist

- **Priority:** P0
- **Depends on:** S21D1-011
- **Deliver:** versioned feature schema and field-time/source map for the provisional
  outcome-triage surface.
- **Acceptance:** hidden tests, solution/control content, terminal status/hash,
  provider response body, post-outcome timing, and answer-revealing strategy names are
  absent; every included field proves pre-outcome availability.
- **Evidence:** schema, fixtures, and field-lineage tests.

### S21D1-013 — Add a feature and label leakage validator

- **Priority:** P0
- **Depends on:** S21D1-012
- **Deliver:** validator for forbidden fields, hidden-control tokens, post-outcome
  timestamps, exact/near duplicates, same-group crossing, and label-derived features.
- **Acceptance:** seeded leaks fail with stable reason codes; valid pre-outcome records
  pass; validator output is included in surface evidence.
- **Evidence:** positive, negative, and adversarial tests.

### S21D1-014 — Select primary and secondary surfaces

- **Priority:** P0
- **Depends on:** S21D1-011, S21D1-013
- **Deliver:** signed/hash-bound decision selecting one primary and one secondary
  surface with explicit rejected alternatives.
- **Acceptance:** selection occurs before held-out metrics; primary has projected
  eligibility for 200 outcomes and 20 changes; secondary has graph-pair feasibility;
  otherwise Gate D1 remains open.
- **Evidence:** commit containing decision artifact hash and timestamp ordering.

### S21D1-015 — Publish the pre-registration bundle

- **Priority:** P0
- **Depends on:** S21D1-014
- **Deliver:** immutable bundle for feature schema, label, action policy, costs,
  exclusions, groups, baselines, metrics, thresholds, bootstrap, resource limits,
  random seeds, and stop rules.
- **Acceptance:** held-out evaluator refuses a missing or hash-mismatched bundle; later
  changes create a new revision and invalidate affected results.
- **Evidence:** Artifact Store bytes, learned lineage, event, and replay test.

### S21D1-016 — Execute only a bounded sample-shortfall campaign

- **Priority:** P1, conditional
- **Depends on:** S21D1-015
- **Deliver:** pre-registered, fixed-seed, provider-free evaluation-only campaign for
  the exact shortfall when eligibility is 150–199.
- **Acceptance:** at most 50 new outcomes, new groups, actual sandbox/verifier runs,
  immutable event/artifact evidence, zero network/provider use, zero training intake.
- **Evidence:** campaign manifest, exact outcome denominator, or explicit not-needed
  record.

## EPIC S21D1-E02 — Primary dataset, baselines, and evaluator

### S21D1-020 — Build the canonical outcome view

- **Priority:** P0
- **Depends on:** S21D1-013, S21D1-016 if applicable
- **Deliver:** one canonical record per unique outcome with features, label reference,
  group, domain, provenance, eligibility, and source hashes.
- **Acceptance:** no raw hidden evidence or provider answer enters features; duplicate
  observations collapse to one outcome; unresolved labels are excluded with reasons.
- **Evidence:** deterministic manifest hash and count reconciliation.

### S21D1-021 — Freeze evaluation roles and groups

- **Priority:** P0
- **Depends on:** S21D1-020
- **Deliver:** group-aware evaluation manifest separating frozen held-out real runs,
  benchmark roles, and future rights-cleared training candidates.
- **Acceptance:** one group has one role; all real governed runs remain
  evaluation-only; exact and normalized duplicate checks report zero crossing.
- **Evidence:** learned split manifest, artifact lineage, and database constraint tests.

### S21D1-022 — Prove sample and decision sufficiency

- **Priority:** P0
- **Depends on:** S21D1-021
- **Deliver:** eligibility report with unique count, class balance, group/domain
  coverage, and changeable-decision count.
- **Acceptance:** at least 200 held-out outcomes and 20 changeable advisory decisions;
  fewer outcomes or decisions blocks the gate rather than weakening definitions.
- **Evidence:** resolvable example IDs and decision counterfactual table.

### S21D1-023 — Implement the deterministic baseline ladder

- **Priority:** P0
- **Depends on:** S21D1-015, S21D1-020
- **Deliver:** `always_verify_now`, majority, visible-contract, and grouped-frequency
  baselines with unseen-group abstention.
- **Acceptance:** every baseline consumes exactly the allowlisted feature view; no
  fitting on held-out labels; identical input yields identical decision and reason.
- **Evidence:** unit tests, frozen outputs, and baseline artifact.

### S21D1-024 — Implement the held-out evaluator

- **Priority:** P0
- **Depends on:** S21D1-022, S21D1-023
- **Deliver:** evaluator for outcome metrics, advisory actions, projected verifier
  work, coverage, abstention, calibration, per-domain/group results, and errors.
- **Acceptance:** it verifies the pre-registration hash before reading examples,
  reports all samples, and never converts a prediction into accepted status.
- **Evidence:** metric-bundle artifact and controlled-fixture tests.

### S21D1-025 — Add paired uncertainty and material-benefit preparation

- **Priority:** P0
- **Depends on:** S21D1-024
- **Deliver:** deterministic paired bootstrap implementation and D2 comparison
  contract.
- **Acceptance:** fixed seed, sample IDs, confidence interval, per-batch output, and
  lower-bound rule are recorded; D1 makes no learned-benefit claim.
- **Evidence:** known-distribution and edge-case tests.

### S21D1-026 — Freeze the primary-surface baseline report

- **Priority:** P0
- **Depends on:** S21D1-024, S21D1-025
- **Deliver:** complete baseline report over at least 200 eligible held-out outcomes.
- **Acceptance:** strongest valid deterministic rung is named; results by domain,
  class, group, abstention, and decision cost are present; failures remain visible.
- **Evidence:** metric lineage and exact evaluator command.

## EPIC S21D1-E03 — Fresh cross-domain failed/success evidence

### S21D1-030 — Freeze the non-coding pair manifest

- **Priority:** P0
- **Deliver:** 10 logic and 10 mathematics cases selected from existing governed
  domain fixtures with stable case IDs, fixed epoch, wrong-answer override, expected
  success path, groups, and rights.
- **Acceptance:** selection is committed before execution; no case overlaps the query
  group it may later retrieve from; physics is not claimed without a pair.
- **Evidence:** canonical selection artifact.

### S21D1-031 — Execute 20 controlled failed runs

- **Priority:** P0
- **Depends on:** S21D1-030
- **Deliver:** actual verifier-backed failures using existing
  `run_case_with_learning(..., candidate_override=...)`.
- **Acceptance:** all 20 fail for task-semantic reasons, not infrastructure; event and
  artifact sources resolve; fixed identities make resume idempotent.
- **Evidence:** outcome ledger and failure classifications.

### S21D1-032 — Execute 20 corresponding successful runs

- **Priority:** P0
- **Depends on:** S21D1-031
- **Deliver:** accepted baseline/corrected runs for the same 20 task signatures.
- **Acceptance:** each passes the independent verifier and pairs one-to-one with a
  failed source without copying an evaluation answer into an input feature.
- **Evidence:** outcome ledger and pair table.

### S21D1-033 — Compile fresh domain trajectories

- **Priority:** P0
- **Depends on:** S21D1-031, S21D1-032
- **Deliver:** Experience Compiler outputs and manifests for all 20 failed/success
  pairs using the fixed epoch.
- **Acceptance:** compile, restart, recompile, and canonical equality pass for 20 of
  20; source and verifier integrity checks pass.
- **Evidence:** compilation bundles and verifier report.

### S21D1-034 — Resolve the 60 historical coding pairs

- **Priority:** P0
- **Depends on:** S21D1-002
- **Deliver:** resolution report mapping every historical manifest to ordered events,
  outcome artifacts, hashes, task, failed strategy, and corrected strategy.
- **Acceptance:** 60 of 60 sources resolve; each is marked
  `legacy_recompilation_unavailable`; no historical bytes or timestamps change.
- **Evidence:** read-only resolver output and before/after artifact hashes.

### S21D1-035 — Freeze the combined pair set

- **Priority:** P0
- **Depends on:** S21D1-033, S21D1-034
- **Deliver:** 80-pair root selection across coding, logic, and mathematics.
- **Acceptance:** at least 80 unique pairs, three domains, 50 task signatures, zero
  cross-group pair leakage, 100% source resolution, and explicit verification mode.
- **Evidence:** pair-set artifact and learned dataset record.

## EPIC S21D1-E04 — Action-decision graph projection and lineage

### S21D1-040 — Add graph contracts and schema exports

- **Priority:** P0
- **Depends on:** S21D1-035
- **Deliver:** the contracts listed in §4.4 with canonical validation and resource
  policy.
- **Acceptance:** stable JSON/schema/hash, typed nodes/edges, bounded collections,
  unique IDs, and no host-path fields; old schema exports remain unchanged except
  additive D1 artifacts.
- **Evidence:** contract, serialization, invalid-input, and schema-drift tests.

### S21D1-041 — Implement the coding correction adapter

- **Priority:** P0
- **Depends on:** S21D1-034, S21D1-040
- **Deliver:** focused adapter from resolved C3 correction evidence to failed and
  successful action-decision graphs.
- **Acceptance:** 60 pairs project deterministically; every graph node traces to a
  resolved source; legacy status is retained and never upgraded to recompiled.
- **Evidence:** golden hashes and source-resolution tests.

### S21D1-042 — Implement the domain trajectory adapter

- **Priority:** P0
- **Depends on:** S21D1-033, S21D1-040
- **Deliver:** focused adapter from `ExperienceCompilationResult` to the same graph
  contracts.
- **Acceptance:** 20 pairs project identically across fresh recompilation; no
  coding-specific branch leaks into domain contracts.
- **Evidence:** logic/mathematics golden tests.

### S21D1-043 — Normalize, validate, and hash graphs

- **Priority:** P0
- **Depends on:** S21D1-041, S21D1-042
- **Deliver:** canonical normalizer and NetworkX DAG validator.
- **Acceptance:** equivalent source order produces the same hash; cycles, duplicate
  IDs, unknown node/edge kinds, unresolved hashes, oversized graphs, excessive depth,
  hidden tokens, and secret patterns fail closed.
- **Evidence:** property, adversarial, and resource-bound tests.

### S21D1-044 — Derive and verify deterministic edit paths

- **Priority:** P0
- **Depends on:** S21D1-043
- **Deliver:** ordered node/edge insert, delete, and relabel operations for every pair.
- **Acceptance:** applying each path to its failed graph yields the successful graph
  hash for 80 of 80 pairs; no operation references an absent logical ID.
- **Evidence:** round-trip and mutation tests.

### S21D1-045 — Build the EMG root and similarity links

- **Priority:** P0
- **Depends on:** S21D1-044
- **Deliver:** root manifest, graph-pair index, and at most three MiniLM cross-task
  similarity neighbors per pair.
- **Acceptance:** same-group links are forbidden; all child hashes resolve; rerun
  produces byte-identical manifest and neighbor ordering.
- **Evidence:** root hash, link audit, and deterministic replay.

### S21D1-046 — Persist graph artifacts through existing authority

- **Priority:** P0
- **Depends on:** S21D1-045
- **Deliver:** canonical graph/edit/root artifacts plus learned dataset and artifact
  lineages in both in-memory and PostgreSQL stores.
- **Acceptance:** declared and observed hashes match; restart resolves all bytes; one
  corrupt/missing child makes the graph set unusable; no new table or migration.
- **Evidence:** shared store-contract tests and repository integration tests.

### S21D1-047 — Record the migration decision

- **Priority:** P0
- **Depends on:** S21D1-046
- **Deliver:** ADR or report decision for migration `0016`.
- **Acceptance:** default result is “not required” with measured artifact size and
  query behavior; any contrary decision identifies an unmet integrity/query need and
  includes full migration, grant, backup/restore, and downgrade work.
- **Evidence:** decision artifact and unchanged Alembic head, unless justified.

## EPIC S21D1-E05 — Retrieval baselines and Context Builder integration

### S21D1-050 — Freeze graph queries and relevance judgments

- **Priority:** P0
- **Depends on:** S21D1-035, S21D1-045
- **Deliver:** at least 80 query records with relevant path IDs, seen/unseen flag,
  group exclusions, domain, task signature, and query text/hash.
- **Acceptance:** queries and judgments are committed before rankings; the source pair
  and same group are absent from candidate pools.
- **Evidence:** immutable query/relevance artifact and leakage report.

### S21D1-051 — Implement no-memory, lexical, and signature arms

- **Priority:** P0
- **Depends on:** S21D1-050
- **Deliver:** deterministic comparison arms sharing one result contract.
- **Acceptance:** stable tie-breaking, identical candidate pool, explicit no-result
  behavior, and no hidden label access.
- **Evidence:** golden rankings and edge-case tests.

### S21D1-052 — Implement the frozen MiniLM vector arm

- **Priority:** P0
- **Depends on:** S21D1-050
- **Deliver:** normalized 384-dimensional query/graph text embeddings and exact cosine
  ranking using the frozen C3 model identity.
- **Acceptance:** missing or wrong model revision fails capability; no hash-embedding
  fallback is counted; repeated rankings agree 100%.
- **Evidence:** model health, vector hashes, and deterministic ranking tests.

### S21D1-053 — Implement bounded simple-graph reranking

- **Priority:** P0
- **Depends on:** S21D1-043, S21D1-052
- **Deliver:** labeled GED-based rerank over the ten-item MiniLM shortlist using the
  exact pre-registered node/edge costs, upper bound, and timeout.
- **Acceptance:** each pair stops within 250 ms; full query stops within 2 seconds;
  timeout and fallback score are explicit; no unbounded retry or full-corpus GED.
- **Evidence:** forced-timeout, upper-bound, deterministic-order, and performance tests.

### S21D1-054 — Benchmark all retrieval arms

- **Priority:** P0
- **Depends on:** S21D1-051, S21D1-052, S21D1-053
- **Deliver:** one metric bundle for all arms on identical frozen queries.
- **Acceptance:** top-5 recall, MRR@10, nDCG@10, coverage, timeouts, p50/p95, memory,
  seen/unseen, and per-domain results are reported; strongest simpler arm is named.
- **Evidence:** benchmark command, host declaration, raw rows, and metric lineage.

### S21D1-055 — Add the Experience Graph context source

- **Priority:** P0
- **Depends on:** S21D1-046
- **Deliver:** additive `ContextSourceType.EXPERIENCE_GRAPH`, default trust mapping,
  fixtures, schema export, and backward-compatibility coverage.
- **Acceptance:** existing context fixtures and clients remain valid; unknown older
  payloads are not silently reinterpreted; graph candidates default only to the
  declared trust policy.
- **Evidence:** context contract and schema tests.

### S21D1-056 — Implement `ExperienceGraphContextRetriever`

- **Priority:** P0
- **Depends on:** S21D1-053, S21D1-055
- **Deliver:** retriever loading the root manifest, enforcing group/resource policies,
  and returning bounded correction-path candidates.
- **Acceptance:** verified trust requires all source hashes; missing/corrupt evidence
  fails closed; candidates are advisory, non-required, non-pinned, and contain exact
  provenance.
- **Evidence:** in-memory and persisted integration tests.

### S21D1-057 — Exercise the complete advisory context path

- **Priority:** P0
- **Depends on:** S21D1-056
- **Deliver:** Context Builder integration from repair request through ranked bundle
  and trace.
- **Acceptance:** graph candidates compete under existing ranking and token budgets;
  source limits apply; no retrieved edit is executed; deterministic fallback works
  when the retriever is unavailable.
- **Evidence:** end-to-end tests and trace artifacts.

## EPIC S21D1-E06 — Decision, operations, and CI

### S21D1-060 — Evaluate graph residuals and headroom

- **Priority:** P0
- **Depends on:** S21D1-054
- **Deliver:** error taxonomy comparing graph rerank with the strongest simpler arm.
- **Acceptance:** names structural errors, ties, regressions, timeouts, domain
  concentration, and projected maximum gain without inspecting a future D2 holdout.
- **Evidence:** residual report linked to raw result IDs.

### S21D1-061 — Complete dependency and license review

- **Priority:** P0
- **Depends on:** S21D1-060
- **Deliver:** review of NetworkX usage, possible FGW libraries, transitive
  dependencies, paper license, repository license, and clean-room boundary.
- **Acceptance:** no EMG paper code/assets are copied; every proposed dependency has
  source, license, maintenance, and necessity evidence.
- **Evidence:** ADR references and dependency scan.

### S21D1-062 — Record the FGW go/no-go decision

- **Priority:** P0
- **Depends on:** S21D1-060, S21D1-061
- **Deliver:** ADR naming simpler baseline, residual class, projected threshold,
  latency/memory budget, dependency, license, and D2 disposition.
- **Acceptance:** “go” meets all §4.11 conditions; “no-go” leaves no unused package or
  speculative abstraction.
- **Evidence:** accepted ADR and lockfile diff check.

### S21D1-063 — Extend the existing experience CLI

- **Priority:** P0
- **Depends on:** S21D1-046, S21D1-054
- **Deliver:** focused `scripts/experience.py` commands for graph build, verify, query,
  benchmark, and health; machine-readable canonical JSON.
- **Acceptance:** no second operator entry point; read-only commands do not write;
  write commands require explicit configured stores; failures return non-zero.
- **Evidence:** CLI smoke and invalid-config tests.

### S21D1-064 — Extend unified integrity reporting

- **Priority:** P0
- **Depends on:** S21D1-046, S21D1-057
- **Deliver:** D1 authority links and graph status in the existing reality integrity
  report rather than an unrelated second release report.
- **Acceptance:** it distinguishes failure from warning, legacy non-recompilation from
  unresolved sources, and retriever availability from graph corruption.
- **Evidence:** healthy, degraded, corrupt, and missing-artifact fixtures.

### S21D1-065 — Prove restart, replay, backup, and restore

- **Priority:** P0
- **Depends on:** S21D1-046, S21D1-064
- **Deliver:** operational evidence that dataset/lineage rows and graph bytes survive
  restart and restore with exact counts and hashes.
- **Acceptance:** restored root, children, split, metrics, and event links match;
  graph query results are deterministic after restart; corrupt bytes are rejected.
- **Evidence:** backup/restore manifest and before/after query hashes.

### S21D1-066 — Add focused credential-free CI

- **Priority:** P0
- **Depends on:** S21D1-057, S21D1-064
- **Deliver:** offline D1 lane using small deterministic graph fixtures, existing
  cached/test embeddings where appropriate, resource-bound tests, and PostgreSQL
  contracts.
- **Acceptance:** zero credentials, network, provider, or GPU; production evidence
  never silently uses fake embeddings; runtime is bounded and failures upload useful
  logs.
- **Evidence:** workflow job and local equivalent command.

### S21D1-067 — Run the complete release matrix on scratch stores

- **Priority:** P0
- **Depends on:** S21D1-065, S21D1-066
- **Deliver:** updated verification matrix covering schemas, unit/integration/full
  suite, migrations, PostgreSQL, artifact integrity, restore, security, packaging,
  language, graph benchmark, and report checks.
- **Acceptance:** every test row uses scratch stores; evidence stores remain untouched;
  every command records expected and actual exit status.
- **Evidence:** full local matrix artifact and duration.

## EPIC S21D1-E07 — Gate, documentation, and protected release

### S21D1-070 — Update architecture and operator documentation

- **Priority:** P0
- **Depends on:** S21D1-063, S21D1-064
- **Deliver:** graph contracts, authority, resource policy, CLI, recovery, Context
  Builder boundary, and limitations in project docs.
- **Acceptance:** documentation makes clear that EMG is advisory and D1 does not
  train or activate a component; commands and paths are exact.
- **Evidence:** link and command validation.

### S21D1-071 — Produce the Gate D1 assessment

- **Priority:** P0
- **Depends on:** all implementation and evidence P0 tasks
- **Deliver:** condition-by-condition assessment of the 21 Gate D1 conditions.
- **Acceptance:** every condition has a resolvable artifact, command, CI, or release
  handle; unmet conditions keep the gate open; graph null results remain visible.
- **Evidence:** `docs/sprints/sprint-21/gate-d1-assessment.md`.

### S21D1-072 — Complete the Sprint 21D1 report

- **Priority:** P0
- **Depends on:** S21D1-067, S21D1-071
- **Deliver:** scope, commits, files, defects, tests, datasets, primary baseline,
  graph results, performance, FGW decision, limitations, and exact gate status.
- **Acceptance:** outcome and graph denominators reconcile to authority; no metric is
  described as learned benefit or activation; legacy constraints are explicit.
- **Evidence:** `docs/sprints/sprint-21/sprint-21d1-report.md`.

### S21D1-073 — Complete the protected D1 release

- **Priority:** P0
- **Depends on:** S21D1-072
- **Deliver:** coherent commits, green PR checks, protected merge, exact-head
  post-merge `main` CI, annotated `sprint-21d1-emg-baseline`, remote tag verification.
- **Acceptance:** no protection bypass; tag is created once after final main CI and
  peels to the verified release commit; annotation records gate and limitations.
- **Evidence:** PR, merge commit, CI run, local/remote tag object and peeled SHA.

### S21D1-074 — Prepare the Sprint 21D2 handoff

- **Priority:** P0
- **Depends on:** S21D1-073
- **Deliver:** exact APIs, feature/split/evaluator/baseline manifests, strongest
  retrieval arm, graph root, training-eligible inputs, frozen holdouts, FGW decision,
  material-benefit rule, risks, and release handles.
- **Acceptance:** D2 can fit the bounded learner without reopening D1 choices or
  viewing the wrong split; Gate L2 is explicitly closed at handoff.
- **Evidence:** `docs/sprints/sprint-21/sprint-21d2-handoff.md`.

---

## 6. Execution waves and dependencies

| Wave | Tasks | Exit |
|---|---|---|
| W0 — release authority | 000–003 | exact baseline, frozen inventory, isolated stores |
| W1 — audit and PR | 004, 010–015 | draft PR and immutable surface pre-registration |
| W2 — primary baseline | 016, 020–026 | at least 200 eligible outcomes and strongest baseline |
| W3 — cross-domain evidence | 030–035 | 80 frozen pairs across three domains |
| W4 — graph vertical | 040–047 | canonical graphs, verified edits, persisted root |
| W5 — retrieval and context | 050–057 | all arms benchmarked and advisory context path green |
| W6 — decision and operations | 060–067 | FGW decision, CLI, integrity, recovery, full matrix |
| W7 — release | 070–074 | docs, gate, report, protected tag, D2 handoff |

No wave may claim completion while a P0 dependency is red.

### 6.1 First vertical slice

Before bulk projection, prove one fresh logic pair end to end:

1. fixed failed and successful governed runs;
2. exact Experience Compiler recompilation;
3. two canonical graphs;
4. deterministic edit path and round-trip;
5. Artifact Store bytes and learned lineage;
6. one frozen query;
7. lexical, vector, and bounded graph ranking;
8. advisory Context Candidate;
9. restart and exact replay.

This slice tests every D1 authority without relying on the legacy C3 timestamps.

### 6.2 Pull-request strategy

Use one D1 implementation PR by default. A separate preliminary documentation/ADR PR
is warranted only if the surface pre-registration must merge before anyone can run the
held-out evaluator. Do not split bulk generated graph artifacts into a PR that bypasses
the contracts and integrity checks they depend on.

---

## 7. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| baseline | tag, current main, CI, migration, protection | wrong D1 parent |
| storage isolation | full dev fingerprint unchanged | evidence contaminated operator store |
| surface audit | four candidates, no held-out metrics | cherry-picked problem |
| pre-registration | feature/label/action/group/baseline hashes | mutable evaluation |
| leakage | field timing, control tokens, duplicates, groups | target visible in input |
| sample | 200 unique outcomes, 20 changes | primary is not actionable |
| primary baseline | strongest deterministic rung | easy comparator omitted |
| source pairs | 60 historical plus 20 fresh | graph evidence inflated |
| historical status | source-resolved, not recompiled | legacy limit hidden |
| fresh compile | 20 exact recompilations | new evidence is non-deterministic |
| graph contract | DAG, canonical hash, bounds | graph payload ungoverned |
| edit path | 80 exact round-trips | correction does not reproduce success |
| graph lineage | all artifact/event hashes resolve | memory cannot be audited |
| retrieval | same frozen queries and pools | arms are incomparable |
| unseen tasks | separate results, group excluded | retrieval leaks task identity |
| resource policy | 64/128/32, 250 ms, 2 s, 10 results | graph search unbounded |
| context | verified advisory non-pinned candidate | memory gains authority |
| FGW | residual, threshold, budget, license | complexity is speculative |
| durability | restart and restore exact hashes | graph memory is ephemeral |
| CI | credential-free focused lane | remote integration untested |
| release | exact-head main CI and remote tag | baseline is not protected |

---

## 8. Quantitative acceptance thresholds

### 8.1 Primary surface

- at least 200 unique held-out verifier-backed outcomes;
- at least 20 changeable advisory decisions;
- zero duplicate outcome identities;
- zero forbidden or post-outcome features;
- zero same-group crossing;
- 100% labels resolved to independent verifier evidence;
- strongest deterministic baseline named;
- all results include coverage and abstention.

These thresholds establish a learnable decision problem. They do not establish learned
benefit.

### 8.2 Graph set

- at least 80 failed-to-success pairs;
- exactly 60 historical coding pairs unless source integrity rejects one;
- at least 10 fresh logic and 10 fresh mathematics pairs;
- at least three domains and 50 task signatures;
- 100% source resolution;
- 20 of 20 fresh exact recompilations;
- 80 of 80 edit-path round-trips;
- zero group leakage;
- zero over-limit accepted graphs.

If a historical source fails integrity, it is quarantined and the gate stays open until
the 80-pair threshold is restored with freshly governed evidence.

### 8.3 Retrieval

- at least 80 frozen query/relevant records;
- unseen-task results reported separately;
- at least one bounded arm has top-5 relevant-path recall at least 0.70;
- at least one bounded arm has MRR@10 at least 0.50;
- repeated-ranking agreement 100%;
- per-pair GED at most 250 ms;
- graph query p95 at most 2 seconds;
- no more than 10 returned results;
- zero silent timeouts or dropped queries.

The graph arm has no mandatory uplift threshold in D1. Its measured comparison decides
whether graph structure proceeds to D2.

### 8.4 Safety and durability

- zero credentials, authorization values, hidden controls, or host paths in graphs;
- zero writes to the inconsistent development Artifact Store pair;
- zero real governed runs in training snapshots;
- zero retrieved paths executed automatically;
- zero activation or promotion records;
- 100% artifact-lineage declared/observed hash agreement;
- exact restore counts and hashes;
- deterministic fallback on missing graph memory.

---

## 9. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| 214 outcomes collapse below 200 | duplicate/ineligible source audit | use bounded shortfall only at 150–199; otherwise replan |
| feature leaks outcome | field is post-outcome or answer-revealing | reject schema revision and rerun pre-registration |
| triage can bypass verifier | high score treated as acceptance | block release; predictor is advisory only |
| class balance is artificial | strategy name encodes correct/incorrect | remove feature and invalidate results |
| historical C3 compile mismatch | wall-clock manifest differs | retain legacy flag; verify sources; never rewrite |
| historical artifact unresolved | missing/corrupt source | quarantine pair and replace with fresh evidence |
| fresh domain case does not fail | wrong override accepted | replace before graph projection; record attempt |
| graph pair is not causal | failed and success task signatures differ | reject pair |
| edit script does not round-trip | final hash mismatch | reject graph normalization or adapter |
| graph contains hidden control | token/path scan hits | quarantine source projection and fix adapter |
| GED stalls | timeout or large graph | enforce shortlist/limits; record timeout; no retry |
| graph beats vector through leakage | same group in index | invalidate benchmark |
| graph loses to vector | no structural headroom | keep vector, reject FGW unless residual criteria pass |
| FGW license is incompatible | dependency/code terms conflict | no-go; do not vendor or copy |
| graph DB proposed | convenience or future scale | reject until a measured existing-store gap |
| migration `0016` appears early | no unmet persistence invariant | remove migration |
| development store targeted | fingerprint/root resolves to old pair | stop and reconfigure; do not repair |
| OpenRouter outage | live route unavailable | irrelevant to D1; remain offline |
| report claims learned benefit | only baselines were measured | correct report; Gate L2 remains closed |
| release matrix erases evidence | row uses evidence root | block release; use scratch root as in C3 fix |

---

## 10. External technical basis

D1 uses external work only to justify bounded design choices:

- The Experience Memory Graph preprint describes transforming failed and expert
  trajectories into directed action-decision graphs and using graph-edit paths as
  test-time guidance: <https://arxiv.org/abs/2607.13884>.
- The preprint is licensed CC BY-NC-SA 4.0, which reinforces the clean-room,
  concept-only boundary for this Apache-licensed repository:
  <https://creativecommons.org/licenses/by-nc-sa/4.0/>.
- NetworkX documents graph edit distance as an NP-hard operation and provides
  `upper_bound` and `timeout`; D1 therefore shortlists with MiniLM and enforces strict
  per-pair and total-query budgets:
  <https://networkx.org/documentation/stable/reference/algorithms/similarity.html> and
  <https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.similarity.graph_edit_distance.html>.

These sources do not override repository evidence, licenses, or the pre-registered
benchmark.

---

## 11. Definition of Done

Sprint 21D1 is complete only when:

- all P0 work is complete;
- the current protected parent and predecessor release evidence are exact;
- the surface audit and selection predate held-out evaluation;
- the primary feature/label/action/group/baseline protocol is immutable;
- at least 200 unique held-out outcomes and 20 changeable decisions qualify;
- strongest deterministic primary baseline results are persisted;
- 60 legacy coding pairs resolve without rewriting;
- 20 fresh domain pairs compile and recompile exactly;
- at least 80 graph pairs across three domains are canonical and source-bound;
- all 80 edit paths reproduce successful graph hashes;
- graph resources and safety inputs fail closed;
- all retrieval arms use identical frozen queries and group exclusions;
- unseen-task results, failures, and timeouts are visible;
- at least one bounded retrieval arm meets the declared usefulness floor;
- graph results enter Context Builder only as verified advisory candidates;
- FGW has an evidence-backed go/no-go decision and no unused dependency;
- migration head remains `0015` unless an unavoidable measured gap justified `0016`;
- restart, replay, backup/restore, scratch matrix, and full regressions pass;
- the protected PR merges without weakened controls;
- exact-head post-merge `main` CI succeeds;
- annotated `sprint-21d1-emg-baseline` is verified remotely;
- Gate D1 passes;
- Gate L2 remains closed;
- D2 receives frozen training/evaluation boundaries and the strongest honest baseline.

---

## 12. Expected deliverables

At minimum:

- this backlog;
- updated D1 handoff, development plan, and sprint allocation;
- surface-audit, decision, and pre-registration artifacts;
- feature, label, group, example, and baseline manifests;
- primary baseline metric bundle over at least 200 outcomes;
- 20 fresh domain correction compilations;
- 80 failed-to-success graph-pair artifacts;
- canonical edit paths and EMG root manifest;
- learned dataset and artifact lineages;
- frozen graph query/relevance manifest;
- lexical, signature, MiniLM, and bounded graph benchmark;
- Experience Graph context source and retriever;
- extended experience CLI and unified integrity report;
- migration decision;
- FGW dependency/license ADR;
- focused credential-free CI;
- restart and backup/restore evidence;
- complete scratch-store verification matrix;
- `docs/sprints/sprint-21/gate-d1-assessment.md`;
- `docs/sprints/sprint-21/sprint-21d1-report.md`;
- annotated `sprint-21d1-emg-baseline`;
- `docs/sprints/sprint-21/sprint-21d2-handoff.md`.
