# Cognitive OS Execution Sprint Allocation

Status: implementation sequencing plan

Revision: 3

Assessment date: 2026-07-27

Source plan: [Cognitive OS Learning, Memory, and Scale Development
Plan](development-plan.md)

Companion documents:

- [Sprint 21R technical backlog](../sprint-21/sprint-21r-technical-backlog.md)
- [Sprint 21C1 technical backlog](../sprint-21/sprint-21c1-technical-backlog.md)
- [Sprint 21C2 technical backlog](../sprint-21/sprint-21c2-technical-backlog.md)
- [Sprint 21 Gate L assessment](../sprint-21/gate-l-assessment.md)
- [Sprint 21 substrate report](../sprint-21/report.md)

Repository: `palkouser/cognitive-os`

Repository language: English only

Primary planning assumption: one protected delivery stream with bounded parallel
work inside a sprint

## 1. Purpose

This document converts the learning, memory, scale, and self-improvement development
plan into release-sized execution sprints. It preserves the plan's two hard rules:

1. Sprint 21 cannot close without at least one persistent, safe, materially useful
   learned component.
2. Sprint 22 cannot close without cross-domain continual learning, a measured
   `10^6` envelope, bounded local English capability, reduced large-LLM dependence,
   and one governed self-improvement reaching protected `main`.

The allocation is scope- and evidence-driven. The nominal timeboxes are estimates,
not permission to weaken an exit gate. An unfinished gate rolls forward as blocking
scope; a sprint is not declared complete because its calendar window ended.

## 2. Current starting state

The state verified before this allocation was written is:

| Item | Verified value |
|---|---|
| Current branch before planning edits | `main` |
| `main`, `origin/main`, and peeled parent tag | `aed2c1b0af280d3f0924a37eeddc191cd320e936` |
| Protected parent tag | `sprint-21c1-evidence-baseline`, tag object `fc7bd5cf384890d036cd70149b4408de650c8ec8` |
| Current migration head | `0014` |
| Sprint 21C1 pull request | `#213`, merged |
| Latest assessed `main` CI | run `30285564507`, successful on the parent commit |
| Gate C1 | pass, all 13 conditions closed in the final tag annotation |
| Gate L2 | closed |
| Next branch | `feature/sprint-21c2-governed-providers` |
| Next migration | `0015_create_provider_output_governance.py` |
| Reviewer limitation | one collaborator; required approval remains disabled without weakening the 27 checks or `enforce_admins` |
| Artifact limitation | development metadata/filesystem pair remains inconsistent and awaits operator-approved remediation |

Sprint 21R and Sprint 21C1 are complete. Sprint 21C2 is the next execution sprint.
All source, tag, credential, branch-protection, reviewer, and remote pull-request
state must be revalidated at sprint start because repository and remote state may
change.

## 3. Allocation principles

### 3.1. Release rule

Every execution sprint ends with:

- a coherent feature-branch commit;
- complete applicable local validation;
- protected PR review and required CI;
- merge without branch-protection bypass;
- successful post-merge `main` CI;
- an annotated, remotely verified sprint tag;
- a closure report and exact hand-off.

Intermediate green tests or PR-only CI are not a release.

### 3.2. Dependency rule

No sprint starts implementation against an unprotected predecessor. Design notes and
credential-free fixtures may be prepared in parallel, but no dependent migration,
active learned artifact, or authority-bearing provider path merges before the
predecessor tag exists.

### 3.3. Complexity rule

Reuse existing domain contracts, repositories, events, Artifact Store, benchmark
runner, Experience Compiler, Corpus Factory, semantic memory, Strategy Evolution
Graph, Coding Agent sandbox, controlled changes, and release scripts. Add a new
dependency or infrastructure authority only after a measured gap and an ADR.

### 3.4. Credential and hardware rule

- Normal CI remains credential-free and replay-based.
- Live OpenRouter, Claude Code, and Codex checks are operator-approved, bounded, and
  never required for an unrelated PR job.
- GPU-dependent work is scheduled only after a workload demonstrates need and the
  complete accelerator software path passes a reproducible preflight. The current
  host exposes an NVIDIA RTX 5070 Ti, but Sprint 21C1 remains CPU-only.
- CPU-first retrieval, classical ML, graph projection, and local inference remain the
  default execution path.

## 4. Sprint summary

| Order | Sprint | Nominal timebox | Primary outcome | Required predecessor | Target tag |
|---:|---|---:|---|---|---|
| 1 | Sprint 21R | 1 week | Reconciled and protected learning substrate | `main` at revalidated base | `sprint-21-substrate-baseline` |
| 2 | Sprint 21C1 | 2 weeks | Persistent Learned Evidence Store and harvester | Sprint 21R | `sprint-21c1-evidence-baseline` |
| 3 | Sprint 21C2 | 2 weeks | Governed OpenRouter, Claude Code, and Codex providers | Sprint 21C1 | `sprint-21c2-provider-baseline` |
| 4 | Sprint 21C3 | 2 weeks | Executable coding corpus, real outcomes, local embeddings | Sprint 21C2 | `sprint-21c3-reality-baseline` |
| 5 | Sprint 21D1 | 2 weeks | Pre-registered learning surface and EMG baseline | Sprint 21C3 | `sprint-21d1-emg-baseline` |
| 6 | Sprint 21D2 | 2 weeks | Materially useful learned activation and Gate L2 | Sprint 21D1 | `sprint-21-learning-baseline` |
| 7 | Sprint 22A | 2 weeks | Data-driven domain expansion | Gate L2 | `sprint-22a-domain-baseline` |
| 8 | Sprint 22B | 2 weeks | Measured `10^6` storage and retrieval envelope | Sprint 22A | `sprint-22b-scale-baseline` |
| 9 | Sprint 22C | 2 weeks | Continual campaigns and Knowledge Acquisition Factory | Sprint 22B | `sprint-22c-acquisition-baseline` |
| 10 | Sprint 22D | 2 weeks | Bounded local English and LLM-dependence reduction | Sprint 22C | `sprint-22d-language-baseline` |
| 11 | Sprint 22E | 2 weeks | Governed self-improvement and Gate M | Sprint 22D | `sprint-22-baseline` |
| 12 | Sprint 23A | 2 weeks | Controlled alpha package | Gate M | `sprint-23-alpha` |

Nominal total: 23 weeks for one primary delivery stream. Independent fixture,
documentation, and benchmark work can shorten elapsed time, but the protected
release order remains serial.

Sprint 21R and Sprint 21C1 completed on 2026-07-26. Sprint 21C2 is now the active
planned delivery.

## 5. Detailed sprint allocation

### Sprint 21R — Learning Substrate Reconciliation and Protected Release

Objective:

Convert the existing four-commit learning branch into an audited, protected,
post-merge-verified substrate without adding Sprint 21C behavior.

In scope:

- exact local/remote baseline reconciliation;
- current four-commit scope inventory;
- refreshed Gate L assessment at the real head;
- Sprint 21 substrate report;
- local quality, tests, benchmarks, PostgreSQL, migration, backup/restore, security,
  packaging, and language evidence;
- protected PR, merge, post-merge CI, annotated tag, and hand-off.

Out of scope:

- migration `0014`;
- learned evidence persistence;
- provider adapters;
- real coding corpus expansion;
- active learned-component promotion.

Exit:

- `sprint-21-substrate-baseline` peels to the same commit as verified
  `origin/main`;
- the report states that the substrate is released but Gate L2 remains open;
- Sprint 21C1 can branch from the tag without unresolved release debt.

Detailed backlog:

[Sprint 21R Technical Backlog](../sprint-21/sprint-21r-technical-backlog.md)

Completion:

- released as `sprint-21-substrate-baseline`;
- peeled tag, `origin/main`, and final CI head resolve to
  `e9001a9338c9507a60ca43f4e3e4bee7e28ef79b`;
- Gate R0 passed and Gate L remained a no-go.

### Sprint 21C1 — Persistent Learned Evidence

Objective:

Turn the current in-memory learning contracts into durable, replayable,
rollback-capable evidence and artifact state.

Primary scope:

- migration `0014_create_learned_evidence_store.py` from verified head `0013`;
- corpus, feature, split, example, artifact, evaluation, promotion, activation, and
  rollback records;
- PostgreSQL and in-memory repositories using existing conventions;
- Artifact Store split for large payloads;
- event replay, idempotency, compare-and-set, restart, and corruption checks;
- first real-run harvester contracts and quarantine states;
- grants, health, backup, restore, schema export, CLI diagnostics.

Required outputs:

- persistent learned-state schema and repository;
- deterministic event and artifact lineage;
- restart and rollback demonstration;
- harvester intake capable of accepting verified executions without claiming
  synthetic fixtures as real runs.

Exit:

- active/candidate artifact state survives restart;
- duplicate ingestion is idempotent;
- hash mismatch and unauthorized write fail closed;
- migration round trip, backup, restore, and replay pass;
- no learned component is activated merely because persistence exists.

Detailed backlog:

[Sprint 21C1 Technical Backlog](../sprint-21/sprint-21c1-technical-backlog.md)

### Sprint 21C2 — Governed Teacher and Provider Boundary

Objective:

Create safe, replayable access to OpenRouter, Claude Code, and Codex for local
operator-initiated teaching, review, and candidate generation.

Primary scope:

- generic OpenAI-compatible adapter using the existing OpenAI client;
- OpenRouter health, model discovery, resolved-model recording, quota and typed
  failure handling;
- hardening of the existing Claude Code advisory adapter;
- new Codex CLI read-only advisory adapter;
- structured schemas, timeouts, output caps, redaction, mutation guards, and process
  cleanup;
- teacher-output retention purpose, rights, sensitivity, and expiry metadata;
- credential-free replay fixtures and opt-in bounded live smoke commands.

Exit:

- offline CI covers every provider contract and failure class;
- one operator-approved live smoke exists for each provider;
- no credential, secret, raw authorization header, or uncontrolled tool authority is
  retained;
- provider output cannot write active memory or approve itself.

Detailed backlog:

[Sprint 21C2 Technical Backlog](../sprint-21/sprint-21c2-technical-backlog.md)

### Sprint 21C3 — Reality-Grade Learning Inputs

Objective:

Produce honest, executable learning data and local semantic retrieval suitable for a
material-benefit evaluation.

Primary scope:

- at least 30 rights-clean coding repair tasks using the existing worktree and
  rootless sandbox;
- hidden failing/passing tests and multiple genuine candidate strategies;
- repository/task-family isolation and leakage detection;
- at least 200 verified outcomes and 50 failed-to-corrected trajectories;
- local CPU embedding model with complete model/license/version metadata;
- measured full-precision versus half-precision storage decision;
- corpus and outcome statistics by domain, source, attribution, and verifier.

Exit:

- code actually executes under the hidden verifier;
- at least 10 tasks contain an initial failure followed by verified correction;
- no “apply all fixture edits” shortcut can solve the corpus;
- fake/hash embeddings are excluded from production evidence;
- Sprint 21D1 has sufficient honest data to pre-register a learning surface.

### Sprint 21D1 — Learning Surface and Experience Memory Graph

Objective:

Freeze an honest learned-decision problem and establish the simplest useful
failed-to-success experience graph retrieval.

Primary scope:

- leakage, class-balance, actionability, attribution, sample-size, and headroom audit;
- one primary and one secondary surface selected before held-out evaluation;
- canonical feature, split, evaluator, and baseline manifests;
- action-decision graphs derived from existing normalized trajectories;
- exact signature, vector, text, and simple graph/edit-path baselines;
- advisory correction-path Context Candidates;
- bounded node, edge, depth, time, and result policies;
- dependency/license decision for FGW.

Exit:

- primary surface has at least 200 held-out outcomes and 20 changeable decisions;
- at least 50 failed-to-success graph pairs cover at least two domains;
- unseen-task results are separate;
- simple graph retrieval is compared honestly with no-memory, text, and vector
  baselines;
- FGW is either justified for Sprint 21D2 or explicitly rejected.

### Sprint 21D2 — Useful Learned Activation and Gate L2

Objective:

Activate one owned learned component because it improves verified downstream
behavior while retaining safe fallback and every earlier capability.

Primary scope:

- calibrated k-NN;
- logistic/SGD or a small tree only if the simpler rung fails;
- FGW comparison only when Sprint 21D1 approved it;
- immutable artifact fitting and evaluation;
- paired material-benefit comparison;
- cross-domain anti-forgetting;
- OOD abstention;
- shadow, disagreement review, canary, kill switch, restart, and rollback;
- complete Gate L2 closure and protected release.

Exit:

- at least one learned component meets the pre-registered material-benefit threshold;
- benefit persists across two independent evaluation batches;
- safety cases have zero accepted-to-rejected transitions;
- OOD false-confident action rate is at most 1% on the declared adversarial suite;
- rollback and deterministic fallback are demonstrated after restart;
- `sprint-21-learning-baseline` is protected and verified.

Failure to activate a materially useful learned component blocks Gate L2. The team
must improve the corpus, surface, verifier, or bounded learner; it may not redefine
machine learning as optional.

### Sprint 22A — Data-Driven Domain Registry

Objective:

Prove that Cognitive OS can expand beyond four example subjects without creating
domain silos or core branching.

Primary scope:

- stable string domain IDs and versioned descriptors;
- parent, related-domain, concept, capability, verifier, tool, unit, corpus, transfer,
  lifecycle, and provenance metadata;
- backward-compatible adapter for logic, mathematics, physics, and coding;
- mechanics/engineering and chemistry pilots;
- multi-domain knowledge membership and shared semantic concepts;
- untrusted-package rejection and diagnostics.

Exit:

- both new domains register without changing the core controller or storage schema;
- cross-domain items are stored once and exposed through multiple governed views;
- global and per-domain replay remain green;
- invalid domain packages fail closed.

### Sprint 22B — Million-Item Scale and Recovery

Objective:

Demonstrate that learned memory, temporal revision, and graph-assisted retrieval
remain operable at `10^6` items.

Primary scope:

- deterministic uniform and clustered million-item datasets;
- exact, ANN, filtered, hybrid, temporal, graph-assisted, and stale-item retrieval;
- real embedding dimensions;
- incremental insert, supersession, tombstone, bloat, reindex, and concurrent-read
  behavior;
- CPU, RAM, disk, ingest, latency, recall, and storage reports;
- backup, restore, hash, active-revision, and artifact-pointer verification.

Exit:

- recall@10 is at least 0.95;
- warm filtered ANN p95 is at most 300 ms;
- bounded graph-assisted p95 is at most 500 ms;
- ingest sustains at least 100 items/s on the declared reference host;
- restore reproduces exact counts, hashes, active views, and learned artifact
  pointers.

### Sprint 22C — Continual Learning and Knowledge Acquisition

Objective:

Run repeated governed learning cycles and transform rights-cleared technical
literature into usable Cognitive OS knowledge.

Primary scope:

- campaign manifests for source, domain, goals, budget, providers, curriculum,
  holdouts, and stop conditions;
- rolling time/source evaluation and drift/forgetting alerts;
- source registration, rights, extraction, normalization, cross-check, quarantine,
  compilation, evaluation, and promotion;
- one rights-cleared technical chapter or paper across two domains;
- at least three campaign cycles;
- contradiction and supersession demonstrations.

Exit:

- every cycle replays all retained domains;
- a planted harmful update is quarantined;
- a valid new revision supersedes the active view without deleting history;
- source citations and hashes survive every derivative;
- at least one retained artifact improves a held-out verified task.

### Sprint 22D — Local English and LLM-Dependence Reduction

Objective:

Demonstrate bounded technical English capability on local owned resources and reduce
large-LLM use without reducing verified quality.

Primary scope:

- frozen 100-task English technical microbenchmark;
- no-memory, retrieval-only, external-teacher, and local-model baselines;
- one CPU-viable permissively licensed quantized model;
- retrieval-augmented local inference;
- optional adapter feasibility only after GPU and rights preflight;
- stable mixed workload and provider/local compute accounting;
- confidence-based external escalation.

Exit:

- no large external LLM is called during the local microbenchmark;
- local verified success is at least 70% and at least 10 points above retrieval-only;
- large-LLM calls or equivalent cost fall at least 25% at non-inferior success;
- factual output is grounded or explicitly uncertain;
- prior domain, learning, and safety gates remain green.

### Sprint 22E — Governed Self-Improvement and Gate M

Objective:

Close the evidence loop from weakness to protected improvement without granting
providers autonomous repository authority.

Primary scope:

- weakness-to-proposal linkage;
- provider-assisted bounded candidate generation;
- isolated Coding Agent worktree and sandbox evaluation;
- controlled-change regression, security, migration, packaging, and rollback gates;
- three dry-run proposals;
- one user-approved low-risk repository improvement;
- Experience Compiler and EMG feedback;
- complete Gate M release.

Exit:

- rejected proposals cause zero active-state mutation;
- one approved change reaches protected `main` through PR and post-merge CI;
- failed and successful experience is retained and retrievable;
- all Gate M conditions pass;
- `sprint-22-baseline` peels to the verified protected commit.

### Sprint 23A — Controlled Alpha

Objective:

Package and document the proven learning system without introducing a new learning
architecture.

Primary scope:

- install, upgrade, configuration, and clean default package;
- provider and local-model operator setup;
- source-rights, retention, backup, restore, and rollback runbooks;
- campaign and benchmark examples;
- observability for learning, forgetting, drift, provider use, cost, and graph
  retrieval;
- alpha limitations, safety boundaries, and recovery drills;
- release candidate and alpha tag.

Exit:

- clean wheel and editable installs pass;
- one supported learned configuration satisfies the Cognitive OS product claim;
- unavailable heavy extras fail to explicit capability states;
- operator runbooks reproduce backup, restore, rollback, and provider-offline modes;
- alpha limitations are explicit;
- `sprint-23-alpha` is protected, post-merge verified, and published.

## 6. Critical path

```text
Sprint 21R protected substrate
  -> Sprint 21C1 persistent evidence
  -> Sprint 21C2 governed providers
  -> Sprint 21C3 executable corpus and real outcomes
  -> Sprint 21D1 learning surface and EMG baseline
  -> Sprint 21D2 useful activation and Gate L2
  -> Sprint 22A data-driven domains
  -> Sprint 22B million-item scale
  -> Sprint 22C continual acquisition
  -> Sprint 22D local English and LLM reduction
  -> Sprint 22E governed self-improvement and Gate M
  -> Sprint 23A controlled alpha
```

## 7. Permitted parallel preparation

The following preparation may overlap without changing merge order:

- Sprint 21C2 replay fixtures may be drafted while Sprint 21C1 persistence is being
  implemented.
- Sprint 21C3 rights-clean task sourcing may begin while provider adapters are under
  review, but golden data must not enter active training.
- Sprint 21D1 graph normalizer prototypes may use replay fixtures after persistent
  trajectory identity is frozen.
- Sprint 22A descriptor examples may be prepared after Gate L2 contracts freeze.
- Sprint 22C source-rights review may begin during the scale sprint.
- Sprint 22D local-model hardware benchmarks may begin after CPU/GPU preflight, but
  no adapter training may use an unapproved corpus.

Parallel preparation does not authorize dependent merges or active-state mutation.

## 8. Programme-level stop conditions

Stop the current sprint and report a blocked gate when:

- the required predecessor tag does not match protected `main`;
- a migration head or schema baseline is ambiguous;
- required PR or post-merge CI is red;
- a corpus has unresolved rights or evaluation leakage;
- a provider path exposes credentials or mutates the working tree;
- an active learned candidate regresses a safety case;
- backup, restore, rollback, or artifact hashes cannot be reproduced;
- a supposed learned benefit exists only on internal prediction accuracy and not on
  downstream verified outcomes.

An infrastructure-only CI failure on an unchanged head should be inspected and rerun
before code is changed. A repeatable product failure requires a targeted fix and full
revalidation.

## 9. Programme completion definition

The allocation is complete only when:

- all twelve sprint closure reports map scope to exact evidence;
- every target tag is annotated, pushed, peeled, and tied to successful protected
  `main` CI;
- Gate L2 and Gate M remain reproducible from retained artifacts;
- Cognitive OS owns and can restore its learned evidence, active model pointer,
  semantic revisions, experience graphs, and source lineage;
- at least one learned runtime path remains materially useful with safe fallback;
- the controlled alpha can be installed and operated from the documented release.
