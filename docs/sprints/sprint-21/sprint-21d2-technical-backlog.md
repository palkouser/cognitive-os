# Sprint 21D2 Technical Backlog

## Useful Learned Correction Ranking and Gate L2

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution
- **Revision:** 1
- **Prepared:** 2026-07-31
- **Required predecessor release:** `sprint-21d1-emg-baseline`
- **Required predecessor tag object:**
  `a59977dbcf23df60a700385a6fc15b012bf6d142`
- **Required predecessor release commit:**
  `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`
- **Required predecessor implementation PR:** `#217`
- **Required predecessor post-merge CI:** `30657167717`, success, 30 of 30 jobs
- **Planning head at preparation:** `origin/main` at
  `1cadbabb5cdabb32bbd502f281d734fb25a229ff`
- **Gate-close documentation PR:** `#218`
- **Planning-head CI:** `30658256397`, success, 30 of 30 jobs on the exact
  planning head
- **Required parent migration head:** `0015`
- **Implementation branch:** `feature/sprint-21d2-useful-learned-activation`
- **Planned migration:** none
- **Next available migration:** `0016`, unallocated unless an evidence kind or
  lifecycle invariant cannot be represented by the existing ledgers and Artifact Store
- **Success-path baseline tag:** `sprint-21-learning-baseline`
- **Negative-path evidence tag:** `sprint-21d2-evidence-baseline`
- **Stage gates:** Gate D1 remediation and Gate L2 — Useful Learned Activation
- **Execution profile:** local, CPU-first, single maintainer, credential-free normal
  CI, no live-provider dependency
- **Repository language:** English only

---


## 0. Authority and execution contract

This backlog is the implementation authority for Sprint 21D2. It refines:

- `docs/sprints/sprint-21/sprint-21d1-report.md`;
- `docs/sprints/sprint-21/gate-d1-assessment.md`;
- `docs/sprints/sprint-21/sprint-21d2-handoff.md`;
- the annotated `sprint-21d1-emg-baseline` release;
- PR `#218` and its exact-head planning baseline;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`.

The protected D1 assessment is historical evidence and must not be rewritten into a
pass. D2 attempts to satisfy its three open conditions with new evidence and records the
result in the D2 assessment. If implementation evidence contradicts this backlog, the implementer
must preserve evaluation separation, verifier authority, deterministic fallback,
artifact lineage, and reversible activation. The conflict and the smallest resolution
must be committed before the affected final holdout is opened.

### 0.1 Release-grade meaning of done

D2 is not complete when a model fits, a retrieval score improves, or a PR turns green.
Section 11 defines both valid release outcomes. The Gate L2 success path requires:

1. revalidation of the D1 tag object and peeled commit, current planning head, exact-head
   CI, branch protection, migration head, collaborator state, and store isolation;
2. a non-destructive D1 release erratum that preserves the protected tag and distinguishes
   release chronology from later recorded timestamps;
3. revision 2 of the learning-surface pre-registration, selecting
   `experience.correction_ranking` only after its new data plan passes the audit;
4. a rights-verified `SELF_PLAY` training and calibration corpus whose observations are
   structurally unable to include `REAL_GOVERNED_RUN` evidence;
5. two separately frozen, mutually group-disjoint `REAL_GOVERNED_RUN` evaluation batches,
   sealed before fitting and opened only after one candidate artifact is selected;
6. at least 200 final held-out verifier-backed candidate outcomes and at least 20 paired
   task-level decisions that differ from the strongest deterministic baseline, with all
   four candidates labelled in evaluation-only mode;
7. an actual fitted-feature leakage proof, not only an intended-schema review;
8. a bounded k-NN first; logistic/SGD and a small tree only under the pre-registered
   continuation rules and never after final holdout access;
9. an inert, canonical JSON model artifact loaded through a narrow verified loader, with
   no pickle, joblib, arbitrary object, or executable artifact deserialisation;
10. a material downstream benefit over the strongest honest deterministic baseline,
    positive in both evaluation batches and with a paired-bootstrap lower bound above
    zero;
11. zero safety regressions, bounded cross-domain retention, OOD abstention, shadow,
    canary, kill-switch, deterministic-fallback, restart, disable, and rollback evidence;
12. closure of D1 conditions 6, 7, and 15 without changing their thresholds;
13. on the success path, one human-approved learned component active only in the bounded
    correction-sequencing campaign path, while every correction still requires the
    independent verifier;
14. isolated PostgreSQL and Artifact Store recovery evidence, complete local validation,
    protected PR merge, successful exact-head post-merge `main` CI, and one annotated,
    remotely verified `sprint-21-learning-baseline` tag;
15. a D2 report and Gate L2 assessment that retain negative results, limitations, hashes,
    commands, and release handles; a Sprint 22A handoff exists only on the success path,
    while the negative path produces a successor-remediation handoff.

Final PR, merge, CI, and tag handles belong in the annotated tag or external release
evidence rather than a tracked self-referential report.

### 0.2 Efficiency-first implementation rule

Use, in order:

1. the existing learned domain contracts, evidence service, repositories, activation
   ledger, Artifact Store, Event Store, dataset builder, MiniLM provider, Experience
   Graph retrieval, campaign runner, verifier, and release scripts;
2. the standard library and the already locked optional dependencies;
3. one focused correction-ranking module and one narrow runtime resolver;
4. a new optional dependency only after a pre-registered simpler rung fails and an ADR
   proves that the dependency is the shortest safe implementation.

D2 must not add by default:

- a new database, graph database, vector database, event authority, or model server;
- migration `0016` merely to store JSON evidence already supported by the ledgers;
- a generic training platform, generic model factory, second Context Builder, or second
  activation state machine;
- a GNN, neural adapter, large language model, live provider, or GPU critical path;
- an FGW implementation or dependency;
- a pickle or joblib loader;
- an unrestricted online-update path;
- automatic acceptance of a correction based on a learned score.

### 0.3 Evidence-role boundary

The role boundary is structural and applies even when all development data is public:

| Evidence | Permitted D2 use | Prohibited use |
|---|---|---|
| C3/D1 `REAL_GOVERNED_RUN` outcomes | surface diagnosis, historical development comparison, retained evaluation | training, calibration, threshold choice, artifact exemplars |
| new D2 `SELF_PLAY` training groups | fitting after rights and leakage checks | final benefit claim |
| new D2 `SELF_PLAY` calibration groups | k/threshold/learner selection before final access | fitting exemplars or refitting after either final batch is opened |
| final batch A `REAL_GOVERNED_RUN` | first independent final comparison | training, calibration, feature revision |
| final batch B `REAL_GOVERNED_RUN` | second independent final comparison | training, calibration, feature revision |
| canary `REAL_GOVERNED_RUN` | bounded post-approval runtime proof | model fitting or replacement of final evidence |

All 214 C3/D1 outcomes are real governed evidence. The 120 deferred
`experience.correction_ranking` examples therefore do **not** enter a training or
calibration snapshot. Re-executing a rights-cleared task under a new `SELF_PLAY`
campaign is permitted only as a new observation with new provenance, immutable lineage,
and a group that is excluded from every D2 final and canary set.

### 0.4 Negative-result and no-retuning rule

Machine learning is mandatory for the programme, but a particular learner is not
entitled to activation. D2 must publish a negative result and record that Gate L2 does
not pass when:

- the surface loses eligibility or actionability;
- no pre-registered learner clears calibration continuation criteria;
- the final material-benefit threshold or either independent-batch direction fails;
- the paired interval includes zero;
- the retrieval usefulness floor remains open;
- safety, retention, OOD, budget, artifact, shadow, canary, restart, or rollback evidence
  fails.

After final batch A is opened, no feature, label, grouping, baseline, candidate,
hyperparameter, threshold, resource limit, or metric definition may change. Batch B is
confirmation, not a repair set. A failed final comparison requires a new pre-registration
revision and a new untouched holdout in a successor remediation sprint.

A valid negative result completes the D2 experiment but does not pass Gate L2. In that
case the activation-only work items produce immutable `not-opened` records, the protected
release uses `sprint-21d2-evidence-baseline`, and the handoff targets a remediation sprint
rather than Sprint 22A. The success tag and Sprint 22A remain forbidden.

---

## 1. Verified starting evidence and inherited limitations

### 1.1 Exact release state

At backlog preparation:

- the checkout is clean on `main`;
- `HEAD`, local `main`, and `origin/main` resolve to
  `1cadbabb5cdabb32bbd502f281d734fb25a229ff`;
- PR `#218` supplied the D1 gate-close planning evidence at that head;
- exact-head `main` CI run `30658256397` passed 30 of 30 jobs;
- annotated tag `sprint-21d1-emg-baseline` has tag-object identity
  `a59977dbcf23df60a700385a6fc15b012bf6d142` and peels to
  `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`;
- D1 implementation PR `#217` and post-merge run `30657167717` passed 30 of 30 jobs;
- Alembic head and `EXPECTED_MIGRATION_REVISION` are `0015`; `0016` is unallocated;
- branch protection retains 27 strict required contexts, `enforce_admins`, conversation
  resolution, and force-push/deletion protection;
- required approving reviews remain disabled because only one eligible collaborator
  exists.

D2 must branch from revalidated current `origin/main`, not directly from the older D1
tag commit. The tag remains the immutable implementation predecessor; the current main
head adds the gate-close record that D2 also requires.

### 1.2 D1 surface result

| Surface | D1 disposition | Evidence relevant to D2 |
|---|---|---|
| `governed.outcome_triage` | rejected | `candidate_strategy` is a perfect forbidden oracle; honest fields have no useful headroom |
| `experience.strategy_selection` | rejected | zero changeable decisions |
| `experience.correction_ranking` | deferred | 120 eligible real-run examples, balanced 60/60, 30 groups, 30 changeable rankings |
| `experience.correction_context` | selected secondary | verified advisory graph context, no execution or acceptance authority |

D1 selected no primary surface. Gate D1 conditions 6 and 7 are therefore open even
though the deferred ranking candidate has promising development counts. D2 may select
that candidate only in a new pre-registration revision with a compliant training and
final-evaluation plan.

### 1.3 D1 graph and retrieval result

The frozen D1 development evidence contains 80 failed/success pairs: 60 historical
coding pairs and 20 fresh logic/mathematics pairs, across three domains and 50 groups.
All sources resolve and all structural edit paths round-trip. The 60 historical pairs
retain `legacy_recompilation_unavailable`; 14 of the 20 fresh queries have only tier-2,
same-domain relevance judgements.

| Arm | Recall@5 | MRR@10 | nDCG@10 | p95 | Cutoffs |
|---|---:|---:|---:|---:|---:|
| lexical | 0.5250 | 0.4145 | 0.3327 | 1.78 ms | 0 |
| MiniLM vector | 0.5375 | 0.4392 | **0.3740** | 27.5 ms | 0 |
| MiniLM shortlist plus bounded GED | **0.6750** | **0.4481** | 0.3438 | 1788.9 ms | 60 |

The graph arm misses the 0.70 Recall@5 and 0.50 MRR@10 floors. Nineteen of 26 misses
are shortlist-ceiling misses and seven are ordering errors. D1's measured oracle ceiling
at shortlist width 20 is 0.9750. Width 20 is therefore D2's pre-registered first lever;
the final D2 holdout is not a width sweep.

### 1.4 Shortlist implementation defect to fix before measurement

`bounded_ged()` currently obtains its candidates from the public `minilm_vector()`
result. That public result is already truncated to `returned_results`. Consequently,
`vector_shortlist=20` with `returned_results=10` still sends only ten candidates to GED.

D2 must separate internal vector scoring/shortlisting from external result truncation.
The regression proof is exact: twenty candidates are considered by the reranker while
at most ten are returned. No width-20 metric is admissible before this defect is fixed.

### 1.5 Existing reusable authority

D2 already has:

- `SituationVector`, `FeatureSchema`, `LearnedPrediction`, `LearnedShadowResult`,
  `MandatoryPathInvariance`, `ForgettingAssessment`, `OutOfDistributionAssessment`,
  `BaselineLadder`, and `LearnedPromotionAssessment`;
- the pure-Python append-only `ExperienceKnn` pattern and deterministic fallback;
- a durable learned evidence service with exact artifact lineage, human approval,
  activation, disable, rollback, replay, and restart projections;
- a configuration boundary whose activation actor and active-component sets are empty by
  default and which forbids real-run training and model/provider self-approval;
- an Artifact Store adapter that verifies bytes and deliberately does not deserialize
  executable object graphs;
- the C3 campaign, hidden verifier, Corpus Factory, source-rights, group, and reality
  integrity infrastructure;
- D1 graph projection, retrieval, resource limits, artifact-backed evidence, and advisory
  Context Builder integration.

The missing D2 product path is focused: a correction-ranking dataset, learner and inert
artifact; a durable runtime resolver; stronger material-benefit evidence; and one bounded
approved activation.

### 1.6 Operational limitations to preserve

- The inconsistent development Artifact Store pair remains read-only with five files and
  fingerprint
  `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf`.
- The C3 source store contains 8,503 files and fingerprint
  `7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593`.
- The D1 evidence store contains 83 files and fingerprint
  `f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f`.
- D2 writes only to a new D2 evidence pair and per-command scratch roots.
- `postgres_bootstrap_roles.sh` still aborts at the inherited `ALTER ROLE ...
  NOSUPERUSER` operation, and no repository command provisions the evidence database.
  D2 records or safely repairs those local-operator gaps without weakening database
  ownership.
- `reality-inputs-core` runs but is not one of the 27 required contexts. Branch-protection
  changes require separate operator authority and are not a D2 implementation shortcut.
- The reference path is CPU-first. An available GPU does not justify a second result path.
- OpenRouter, Claude Code, and Codex are not required for D2 data completeness or CI.

### 1.7 Non-destructive D1 release erratum

The D1 tag and report bytes remain untouched. D2 must record, without rewriting history:

- PR `#217` contains 14 commits, 84 changed files, and `+44,661/-520`, while the tracked
  report/release bundle says 13 commits and 77 files;
- the authoritative Gate D1 result is 17 met, one not applicable, and three open, while
  the report prose says the other eighteen were met;
- the report says eleven waves while the execution table records thirteen rows;
- some recorded assessment/evidence times are dated 2026-08-01 although the remote merge,
  exact-head CI, tag creation, and gate-close merge occurred on 2026-07-31.

Remote Git and CI chronology is authoritative for release ordering. The erratum explains
the discrepancy and preserves every original content hash.

---

## 2. Sprint goal and gate contract

### 2.1 Goal

Test and, only if every fixed gate passes, activate one owned, bounded component on
`experience.correction_ranking` because it materially improves the first verified
correction selected over the strongest honest deterministic ordering. The component may
reorder advisory candidates; it may not accept a correction, skip the sandbox, skip the
independent verifier, or alter unrelated agent decisions.

In parallel, close D1's retrieval shortfall by correctly applying the D2 revision-2
width-20 shortlist on new unseen-task evidence. D1 pre-registered and measured width 10;
its residual evidence justifies, but did not itself pre-register, this change. Better
retrieval alone does not close Gate L2; the correction ranker must produce material
downstream benefit.

### 2.2 Gate D2 and Gate L2 pass conditions

Gate L2 passes only when every applicable condition is met:

1. the D1 tag object, peeled release commit, current `origin/main`, both exact-head CI
   runs, branch protection, migration head, collaborator count, and store fingerprints
   are revalidated;
2. D2 starts from the current planning head and preserves the D1 release as immutable
   predecessor evidence;
3. the D1 erratum is recorded without modifying the protected D1 tag or falsifying its
   chronology;
4. revision 2 of the surface pre-registration names
   `experience.correction_ranking` as primary and `experience.correction_context` as
   secondary before any D2 final holdout outcome is inspected;
5. the label is the independent verifier's accepted/rejected outcome, the primary unit
   is a task-group ranking, and the executed correction is never accepted by prediction;
6. the fitted feature set contains zero hidden-verifier, solution/control, outcome,
   post-outcome timing, provider-answer, candidate-strategy, candidate/task/group identity,
   raw hash, or other answer-revealing fields;
7. task, repository, template lineage, normalized near-duplicate cluster, and source
   lineage do not cross training, calibration, final A, final B, or canary roles;
8. at least 200 verifier-backed `SELF_PLAY` observations are available for fitting and
   at least 40 separate `SELF_PLAY` observations are available for calibration;
9. the training and calibration snapshots contain zero `REAL_GOVERNED_RUN` observation
   IDs, including the 120 D1 deferred-surface examples;
10. final batches A and B each contain at least 100 new verifier-backed
    `REAL_GOVERNED_RUN` outcomes and 25 task groups, subject to a pre-fit power analysis
    that may raise but never lower those minima;
11. both final manifests are hash-bound and inaccessible to fitting code; one candidate,
    artifact, and decision threshold are selected before either final outcome is opened;
12. the strongest deterministic correction-ordering baseline and every attempted learner
    rung are recorded; k-NN is tried first and later rungs follow only their stop rules;
13. at least 20 final task decisions differ from the strongest deterministic baseline;
14. aggregate first-ranked verified success gains at least 5 percentage points, or
    relative error falls by at least 20%, over that baseline;
15. the task-paired bootstrap uses seed 21041 and 2,000 resamples and its lower confidence
    bound for the primary improvement is above zero;
16. the learned-minus-baseline direction is positive in each independent final batch;
17. coverage, abstention, confidence, attempts-to-first-accept, latency, provider calls,
    verifier calls, failures, and costs are reported with exact denominators;
18. no safety, governance, permission, secret-handling, or destructive-action case moves
    from accepted to rejected;
19. no retained domain loses more than 2 absolute percentage points, aggregate verified
    success loses no more than 1 point, and every small-suite regression is reviewed;
20. on at least 100 pre-registered OOD/adversarial decisions across at least ten groups,
    the reported false-confident action rate is at most 1%, and promotion satisfies the
    existing stricter contract of exactly zero confident errors;
21. shadow mode changes zero executed decisions and links actual outcomes only through
    independent verifier evidence;
22. the selected model artifact is canonical JSON with exact dataset, split, feature,
    embedding, code, configuration, and member hashes; unsafe artifact formats remain
    unloadable;
23. missing, corrupt, oversized, schema-invalid, wrong-model, inactive, disabled,
    unapproved, or configuration-mismatched artifacts immediately use the deterministic
    fallback with a structured health reason;
24. at least one bounded retrieval arm on new D2 unseen-task evidence reaches Recall@5
    at least 0.70 and MRR@10 at least 0.50, within 2 seconds p95, 250 ms per GED pair,
    ten returned results, deterministic ranking, and explicit cutoff reporting;
25. the fail-closed runtime configuration hash-binds the canary subset inside the
    approved bounded surface, every learned-first correction still runs the independent
    verifier, and the kill switch returns immediately to deterministic ordering;
26. exact activation, active projection, artifact loading, disable, deterministic fallback,
    prior-approved activation restoration, and rollback evidence survive process restart;
27. a human operator approves the exact promotion assessment, component revision, and
    artifact lineage; no model or provider identity approves or reviews itself;
28. PostgreSQL replay, backup/restore, corruption, artifact verification, packaging,
    schema, security, language, focused CI, and the complete local matrix pass in isolated
    stores;
29. the protected merge, exact-head post-merge `main` CI, Gate L2 assessment, D2 report,
    Sprint 22A handoff, annotated tag, and remote tag/commit verification complete.

Conditions 8, 10, 13-16, 18-20, and 24 are fixed minima. They are not reduced in
response to an inconvenient result.

### 2.3 Gate semantics

- Gate D1 conditions 6 and 7 pass only from the new, final D2 surface evidence; the D1
  120 records remain development evidence and cannot be relabelled as D2 training.
- Gate D1 condition 15 passes only on the new D2 unseen-task retrieval holdout; rerunning
  the frozen D1 80 queries is diagnostic regression evidence, not closure evidence.
- Gate L2 cannot pass on a retrieval-only win, an internal classification metric, a
  parity result, a shadow-only result, or a component that is verified but inactive.
- A component may be activated only after all pre-activation gates and explicit human
  approval. Canary failure disables it and keeps Gate L2 from passing.
- If any condition fails, D2 produces a complete negative report and a new remediation
  backlog. Sprint 22A implementation remains blocked.

---

## 3. Scope and stop rules

### 3.1 In scope

- D1 release reconciliation and immutable erratum;
- D2-specific evidence database, Artifact Store, sandbox, backup, and scratch roots;
- correction-ranking pre-registration revision 2;
- explicit campaign-aware and group-aware dataset manifests, without adding durable
  corpus roles beyond the existing `TRAINING` and `EVALUATION` values;
- rights-cleared self-play fitting/calibration evidence;
- two new final real-run evaluation batches and a separate canary set;
- correction features, deterministic baselines, bounded k-NN, conditional linear/tree
  rungs, OOD calibration, and immutable JSON artifacts;
- one runtime resolver and one bounded correction-candidate sequencer integrated with
  `RealityCampaignRunner`;
- MiniLM/GED internal width-20 shortlist repair and new unseen-task retrieval evaluation;
- material-benefit, paired uncertainty, anti-forgetting, shadow, canary, approval,
  activation, disable, restart, fallback, and rollback evidence;
- focused CLI, health, CI, operations, release, report, gate, and handoff work.

### 3.2 Explicitly out of scope

- training on any C3/D1 real governed observation;
- provider retries to manufacture labels or class balance;
- live OpenRouter, Claude Code, Codex, or external-LLM dependence;
- learned acceptance, verifier bypass, automatic patch application, or unrelated runtime
  routing;
- general multi-candidate generation in `CodingAgentFacade`; that facade remains a
  single-proposal repair loop in D2;
- online weight updates from runtime observations;
- unbounded hyperparameter search or AutoML;
- a second embedding model or a second vector store;
- FGW implementation, GNN, neural reranker, language model, or graph database;
- migration `0016` without a demonstrated existing-authority gap;
- remediation of the inconsistent development Artifact Store pair;
- branch-protection weakening or fabricated approval;
- Sprint 22 domain registry, million-item scale, acquisition factory, or local-language
  work.

### 3.3 Learner continuation rules

The ladder is selected using training and calibration evidence only:

1. Fit and calibrate bounded cosine k-NN.
2. If it meets the pre-registered calibration threshold and all safety/OOD/resource
   checks, select it and stop. Do not implement later rungs.
3. If it fails and residual evidence authorizes any parametric continuation, add a direct
   optional classical-ML dependency only through a reviewed ADR and evaluate bounded
   logistic/SGD as the mandatory first parametric probe. Do not rely accidentally on a
   transitive import.
4. If the linear rung fails and residual evidence identifies bounded non-linear feature
   interactions, evaluate one depth- and leaf-bounded tree through the same optional
   extra.
5. Stop after the tree. No random forest, boosting, neural, FGW, or provider model enters
   D2 without a new backlog revision and untouched future holdout.

The selection criterion is not maximum calibration accuracy. A rung must clear the
declared benefit proxy, coverage, OOD, reproducibility, and inference budget with no
leakage. Exactly one candidate artifact is selected before final access. If all rungs
fail, record the null result; do not open the final holdout merely to see what happens.

### 3.4 One bounded pre-final revision

Before final access, one evidence-backed feature or calibration revision is permitted
when all of the following hold:

- the revision is motivated by training/calibration residuals only;
- the original thresholds, final manifests, and group partitions do not change;
- feature timing and leakage validation rerun on the exact fitted matrix;
- every candidate is refitted and reselected under a new immutable pre-registration
  revision;
- the revision count and reason are reported.

No second revision is permitted inside D2. This bounds tuning while allowing one honest
correction to a poor pre-final encoding.

---

## 4. Minimal D2 architecture

### 4.1 Data roles and minimum campaign

The minimum campaign is:

| Role | Provenance | Minimum groups | Candidates per group | Minimum executed outcomes / sealed slots | Use |
|---|---|---:|---:|---:|---|
| training | `SELF_PLAY` | 50 | 4 | 200 | fit exemplars/parameters |
| calibration | `SELF_PLAY` | 10 | 4 | 40 | k, thresholds, rung selection |
| final A | `REAL_GOVERNED_RUN` | 25 | 4 | 100 | independent final batch 1 |
| final B | `REAL_GOVERNED_RUN` | 25 | 4 | 100 | independent final batch 2 |
| canary | `REAL_GOVERNED_RUN` | 5 | 4 | 5–20 attempts / 20 slots | bounded approved runtime proof |

The five partitions require at least 115 distinct task/template groups. D1 has only 30
such groups, so even if every existing rights-cleared task is reused exclusively for new
self-play training, D2 must add at least 85 genuinely distinct groups. The power and
retrieval-yield analyses may raise any count before member manifests are sealed and may
not lower a minimum. Existing task specifications may be re-executed for self-play only
when their complete task/template/near-duplicate group is excluded from every other D2
partition. Seed variants of one template are one group, not new independent groups.

Every task has four outcome-neutral D2 candidate recipes assigned opaque IDs before
execution. D2 must not reuse `correct_*`/`incomplete_*` strategy values whose enum family
predicts and validates the label. All four candidate manifests and patch artifacts are
built, byte-verified, and sealed before feature or prediction generation. Candidate order
is deterministically shuffled from a recorded seed and persisted as opaque candidate IDs;
recipe identity is provenance-only and never reaches a feature vector. Training, calibration, and final
campaigns use `label_all`: all four candidates run in the frozen deterministic manifest/
baseline order against the same independent hidden verifier after their pre-outcome
feature record is sealed. Training/calibration have no learned order yet; final/shadow
also seal and record the learned counterfactual order without executing it. Canary and
active campaigns use `stop_on_first_accepted`: candidates run in resolved order and execution
stops only after independent verifier acceptance. Failed, malformed, timed-out, and
rejected attempts remain in the denominator. Any infrastructure-interrupted attempt that
has no terminal record may be rerun under the same identity, but is reported; a recorded
failure is never retried merely to obtain a better label.

OOD is a submanifest/slice, not a sixth partition. The calibration OOD precheck uses
presealed perturbations of groups already assigned to calibration. The untouched
promotion OOD suite uses presealed perturbations of groups already assigned to final A or
final B and supplies at least 100 ranker decisions across at least ten such groups. The
underlying group never changes partition, and OOD variants never enter fitting.

### 4.2 Split and manifest authority

The durable `CorpusRole` contract and PostgreSQL checks remain unchanged: they support
only `TRAINING` and `EVALUATION`. The five experimental partitions are typed children of
the immutable campaign protocol, not new database enum values:

- one `TRAINING` dataset contains disjoint `fit` and `calibration` splits and accepts
  `SELF_PLAY` only;
- separately sealed `EVALUATION` datasets/manifests contain final A, final B, and, after
  execution, canary evidence and accept `REAL_GOVERNED_RUN` only;
- partition name, campaign manifest hash, group identity, and role-specific campaign
  version/profile are checked independently of the two-value durable corpus role.

Extend `LearnedDatasetBuilder` minimally so D2 can supply an immutable selection and
explicit split manifest instead of relying on observation-ID modulo assignment. The D2
builder must:

- persist a versioned D2 partition manifest containing campaign ID/hash/version,
  partition, exact member/source hashes, group mapping, and exact split assignments;
- compute a canonical split-assignment digest before dataset identity and include it in
  explicit-mode `dataset_id_for()`, so different splits over the same members cannot
  collide and return an older snapshot;
- select exact observation IDs and expected source hashes;
- enforce campaign role and allowed provenance per partition;
- assign whole task/template/near-duplicate groups;
- reject unknown, duplicate, missing, extra, cross-role, late, or hash-mismatched members;
- reject evaluation evidence in training or calibration;
- page repository listings with `limit` and `offset` until every requested observation
  is resolved; the existing 500-row default must not truncate explicit selection;
- prove that split union equals the example-manifest members, with no extras, nonempty
  `fit` and `calibration`, and whole-group disjointness;
- store example and split manifests through `ArtifactService` and learned lineage;
- keep the existing default behavior compatible for earlier tests.

No new table is required. A backward-compatible D2 split-manifest schema or its companion
partition artifact carries the extra authority; its digest is bound into dataset identity,
the stored split manifest, and artifact lineage. The legacy builder identity remains
unchanged outside explicit mode.

A focused `CorrectionRankingObservationProjector` converts terminal reality outcomes
to learned observations. It derives partition and provenance from the exact sealed
campaign manifest: training/calibration become `SELF_PLAY`; final A/B/canary become
`REAL_GOVERNED_RUN`; the surface is always `experience.correction_ranking`. Callers may
not supply arbitrary surface/provenance flags. Self-play uses a dedicated
`correction_self_play_task_run` source kind added to verifier-backed source kinds but not
real-governed kinds; final/canary use the credible existing `governed_task_run` kind. The
projector verifies event and artifact
bytes, candidate membership, task/group identity, role-specific campaign version/profile,
and feature-before-outcome chronology. `RealityOutcomeHarvester` keeps its C3-compatible
`coding.repair`/`REAL_GOVERNED_RUN` defaults.

Holdout isolation is capability-based, not a fictional `ArtifactService` ACL. Final A/B
and canary task bodies live under separately configured holdout roots/processes. Fitting
receives only training/calibration ports plus holdout manifest hashes and has no injected
artifact service, path, or credentials for those roots. S21D2-060 starts the evaluation
process with the exact authorized root only after candidate freeze; access records remain
audit evidence, not enforcement.

### 4.3 Primary surface contract

- **Surface:** `experience.correction_ranking`.
- **Decision unit:** one task group with four pre-generated correction candidates.
- **Label:** independent hidden-verifier `accepted` or `rejected` for each candidate.
- **Prediction:** confidence-scored ordering of candidate IDs, or abstention.
- **Baseline action:** strongest pre-registered deterministic ordering.
- **Shadow/final action:** record the learned counterfactual ordering while executing the
  frozen deterministic baseline order.
- **Learned action:** try candidates in learned order only inside declared canary/active
  correction-sequencing campaigns.
- **Mandatory authority:** sandbox plus independent verifier for every attempted
  candidate.
- **Primary metric:** task-group rate at which the first-ranked candidate is accepted.
- **Secondary metrics:** attempts to first accepted candidate, all-candidate ranking
  quality, coverage, abstention, confident error, latency, verifier calls, provider/LLM
  calls, and cost.

An abstention executes the deterministic ordering and is counted as fallback, not as a
correct learned prediction. A task with no accepted candidate remains in the denominator
and is reported separately; it cannot create a synthetic win.

### 4.4 Feature schema revision

The correction encoder is separate from the existing skill-selection encoder. Its
allowlist may include only pre-outcome, content-derived, bounded fields such as:

- problem domain and declared problem type;
- normalized public task/requirement embedding;
- normalized candidate correction/delta embedding;
- query-to-candidate cosine similarity;
- bounded file, hunk, line, AST, graph-node, graph-edge, path-length, and operation-kind
  counts available before execution;
- declared verifier capability requirements, without hidden test bodies or results;
- missing-value indicators and encoder version.

Numeric counts are clipped to pre-registered bounds and normalized from training data
only, with the parameters stored in the model artifact. Alternatively, the encoder may
use an explicitly weighted embedding/static two-channel distance frozen before
calibration. Raw counts may not silently dominate the normalized embedding.

The actual fitted matrix must exclude:

- `candidate_strategy`, generator role, provider/model identity, candidate ID, task ID,
  group ID, repository ID, task signature/hash, source hash, artifact hash, or split name;
- hidden tests, golden solution, control patch, expected answer, verifier command body,
  verifier output, status, score, error, timeout result, accepted hash, or outcome ID;
- post-outcome timestamps, retry count, review result, promotion state, or any field
  derived from the label;
- unrestricted prompt/response bodies, credentials, authorization data, or host paths.

Identifiers remain in provenance and split manifests but never enter similarity,
calibration, or model features. The leakage validator must inspect serialized fitted
features and artifact members, not only the encoder source or declared schema.

### 4.5 Deterministic baseline ladder

Every final comparison includes, at minimum:

1. fixed input order as a trivial floor;
2. deterministic static ordering from declared pre-outcome patch bounds and verifier
   prerequisites;
3. lexical query/candidate similarity;
4. frozen MiniLM cosine ordering;
5. width-20 bounded graph/context ordering when it meets the resource contract;
6. every learned rung actually attempted.

The strongest non-learned first-choice success on sealed calibration evidence is named
before final access. The final learned component is compared against that exact baseline,
not the majority, no-memory arm, or whichever deterministic rung is easiest to beat.

### 4.6 Correction ranker

Add one focused module, expected at
`src/cognitive_os/learning/correction_ranking.py`. Reuse the `ExperienceKnn` design but
do not change the existing skill-selection component's identity or descriptor.

The first candidate is a pure-Python cosine k-NN over frozen MiniLM embeddings and the
small bounded numeric feature vector. It must provide:

- immutable training exemplars;
- deterministic score ties resolved by the frozen deterministic baseline order, never
  by candidate/task identity;
- calibrated `k`, similarity floor, neighbour agreement, confidence floor, and OOD
  threshold;
- ranked candidate scores plus neighbour explanations;
- explicit abstention and deterministic fallback;
- fixed CPU, memory, artifact-size, and per-task inference bounds;
- pinned MiniLM and software identities, finite tolerance-bounded vector replay, 100%
  ranking/decision agreement, and exact artifact-byte replay.

Calibration searches only a small pre-registered grid. No arbitrary hyperparameter
optimizer is introduced.

### 4.7 Conditional parametric rungs

If the continuation rule opens a later rung, use a direct, named optional extra and a
pinned library API. Do not implement a bespoke optimizer merely to avoid one explicit
dependency, and do not treat a transitive dependency as a supported contract.

- Logistic/SGD uses the identical frozen feature matrix, groups, and calibration metric.
- The optional tree has fixed maximum depth, minimum leaf size, random seed, and class
  weighting before fitting.
- Both emit inert JSON coefficients or a validated tree structure; neither loads pickle
  or joblib.
- Both preserve abstention by calibrated confidence/OOD gating.
- Dependency, license, package size, offline install, security scan, and distribution
  verification evidence are required only if the rung is opened.

### 4.8 Canonical JSON artifact and loader

Add `JSON` to `LearnedArtifactFormat` and define a versioned correction-ranker artifact
contract containing:

- component ID, revision, surface, learner kind, code/version identity, and parent
  artifact if any;
- training/calibration dataset IDs and manifest hashes;
- feature schema and fitted-feature hashes;
- MiniLM model ID, revision, tree digest, dimension, and normalization;
- ordered exemplar vectors and labels, or inert coefficients/tree nodes;
- calibrated thresholds, resource limits, seeds, and declared limitations;
- member hashes; the Artifact Store hash of the canonical bytes is the content authority.

The payload must not embed a self-referential blob hash. Canonical JSON is serialized
without a `content_hash` member and `sha256(canonical_bytes)` is recorded by the Artifact
Store and lineage contract.

A narrow loader reads bytes through the existing `ArtifactService` only after lineage
verification. It enforces content hash, media type, maximum size, UTF-8 JSON, Pydantic
schema, canonical ordering, finite numeric values, dimensions, member counts, model
identity, and descriptor/revision match. It returns a correction ranker, not an arbitrary
Python object. `LearnedArtifactVerifierPort` remains a verifier and is not broadened into
a general deserializer. `JOBLIB` remains in `UNSAFE_TO_DESERIALISE` and has no runtime
load path.

### 4.9 Runtime resolver and bounded candidate sequencer

Add one narrow application service, expected at
`src/cognitive_os/application/services/learned_runtime.py`. It reads durable active state
once per task and returns an immutable resolved component snapshot; it does not replay
durable state into `LearnedComponentRegistry` or create a second lifecycle authority. It
reconciles:

1. the durable active revision for `experience.correction_ranking`;
2. the configuration allowlist and explicit activation actor policy;
3. the exact verified model-artifact lineage and descriptor revision;
4. the local MiniLM capability and artifact identity.

Only when all four agree does the correction-ranking path receive the learned ordering.
Otherwise it receives the existing deterministic ordering and a structured health
reason. One surface may have at most one active revision.

Add one bounded `CorrectionCandidateSequencer` and integrate it with
`RealityCampaignRunner` over the prebuilt, ordered four-candidate manifests. In
`label_all` mode it always executes all candidates in frozen deterministic baseline order;
it records a learned counterfactual ordering only when one exists, preserving unbiased
training/calibration/final labels and genuine shadow behavior. Final/shadow evaluation
loads the already selected SHADOW artifact directly through the narrow loader and an
explicit immutable evaluation snapshot; it never asks the ACTIVE-only runtime resolver.
In `stop_on_first_accepted` mode, used only after activation, the sequencer obtains learned
ordering through that resolver, tries candidates in resolved learned or fallback order,
and stops only when the existing independent
verifier accepts one. This is the actual D2 decision seam: it changes first choice and
verifier attempt count only after approval, not candidate bytes or acceptance authority.
Post-stop audit execution, if required, is a separately identified evaluation campaign
and never masquerades as the runtime choice.

Each sequence appends a bounded `RealityCampaignSequenceRecorded` event to the existing
Event Store stream keyed by `RealityCampaignManifest.campaign_id`, using expected-version
compare-and-set. Its versioned canonical payload names campaign/partition/manifest hashes,
mode, frozen baseline and resolved orders, attempted candidate/run keys in actual order,
accepted event and verifier-evidence hashes, stop reason, and intentionally unattempted
keys. The append is the durable terminal authority for that sequence; no process-local
receipt or second database is permitted. Extend the existing coding-event registration
and event service narrowly for this SYSTEM stream. `RealityCampaignLedger.plan_resume()`
reads both the planned task-run streams and the campaign receipt stream, validates one
compatible terminal receipt per sequence, and treats intentionally unattempted keys as a
separate state: never outcomes and never remaining work. If a crash leaves an accepted
terminal outcome without the final receipt, the read-only ledger returns a typed
receipt-repair action and no further candidates for that sequence; the runner appends the
reconciled receipt through the same compare-and-set writer before replanning. Restart and
concurrent-resume tests prove zero post-stop execution, exactly one receipt, and exact
attempted-order replay.

The approved runtime scope is the controlled correction-sequencing campaign path only.
`CodingAgentFacade` still proposes one candidate at a time and is explicitly not covered
by the D2 activation claim. The sequencer does not create candidates, change patch bytes,
execute a retrieved graph path, accept a result, or alter Context Builder authority. The
Experience Graph Context Candidate remains verified, advisory, non-required, non-pinned,
and body-free.

### 4.10 EMG shortlist remediation

Refactor vector scoring into an internal untruncated score path. Public vector retrieval
still returns no more than `returned_results`; bounded GED receives exactly
`vector_shortlist` candidates when that many eligible candidates exist.

Resource-policy revision 2 fixes:

- `vector_shortlist=20`;
- `returned_results=10`;
- maximum 64 nodes, 128 edges, and depth 32;
- 250 ms per GED comparison;
- 2 seconds total per query with per-pair timeout reserved before work starts;
- explicit cutoff and incomplete-comparison counts.

The frozen D1 80-query set is used only as a regression/development diagnostic. The
pre-fit campaign-sizing calculation must overproduce enough final groups for at least 50
qualifying failed-state queries under a conservative yield assumption; fifty final
groups alone do not guarantee fifty failed/successful graph pairs. Final condition-15
evidence uses at least 50 new unseen-task queries from the two D2 final batches, with
each query's complete group excluded. If unexpected outcomes leave fewer than 50,
condition 15 stays open; post-result replacement groups are prohibited. No width or
threshold is selected on that final result.

FGW remains no-go in D2. If the final width-20 residual becomes ordering-dominant, the
result may justify a future ADR/backlog revision with a new holdout; it cannot authorize
retuning and retesting on the same final queries.

### 4.11 Material-benefit assessment

Extend the existing promotion evidence with a hash-bound material-benefit assessment,
rather than replacing the lifecycle service. It records:

- exact baseline and candidate artifact identities;
- batch A, batch B, and aggregate group/outcome counts;
- paired first-choice results and changed-decision identities;
- absolute improvement, relative error reduction, verifier-attempt comparison, descriptive
  provider/LLM zero/zero counts, coverage, abstention, latency, and failures;
- paired bootstrap seed, resample count, interval, and lower bound;
- per-domain and per-slice gains/losses;
- forgetting, invariance, OOD, and shadow evidence hashes;
- the single promotion decision and reason.

Represent this as a backward-compatible D2 schema/version of
`LearnedPromotionAssessment`: add the exact material-benefit, batch, bootstrap,
retention, OOD, shadow, retrieval/D1-remediation, and reproducibility hashes required for
the D2 correction descriptor. The D2 builder and validator require them for an eligible
decision; they are optional only for older historical schemas and cannot authorize the
D2 component. This is JSON payload evolution, not a table change.

The promotion builder derives the strongest baseline from the ladder. It refuses an
eligible verdict below any sample, changed-decision, two-batch, interval, safety,
retention, OOD, or reproducibility condition. The record uses the existing promotion
evidence role and JSON payload authority, so no migration is expected.

The richer canonical assessment bytes are stored in the Artifact Store and named by
`LearnedEvidenceRecord.payload_artifact_id`; activation re-verifies media type, bytes, and
payload hash for the D2 schema. Older C1 smoke assessments without payload artifacts
remain valid under their older schema and do not become material-benefit evidence.

Canary cannot be part of this pre-approval assessment. S21D2-073 produces a separate
post-activation canary assessment; the final Gate L2 assessment binds both the promotion
and canary hashes before Gate L2 can pass.

### 4.12 Lifecycle sequence

The required state and runtime sequence is:

```text
REGISTERED
    -> SHADOW          deterministic ordering executes; learned ordering is recorded
    -> VERIFIED        final benefit, forgetting, OOD and invariance evidence pass
    -> human approval  exact assessment + revision + model lineage
    -> ACTIVE          approved bounded surface; config routes only canary subset
    -> DISABLED        kill switch; deterministic fallback proven after restart
    -> ACTIVE          roll_back restores the exact prior approved activation
    -> ACTIVE          bounded steady-state correction-ranking scope
```

The human approval and activation receipt bind only fields their current contracts
actually carry: component ID/revision, surface, promotion-assessment hash, model-lineage
ID, approval identity/hash, actor/reason, and time. They authorize the final bounded
correction-sequencing surface. Canary routing is a separately hash-recorded, fail-closed
manifest/configuration subset of that already approved scope, not a new lifecycle state
and not a field invented in the approval contract. The resolver requires both active
state and that config during canary. Missing or mismatched config falls back.

Make the evidence boundary structural: generic `advance_component()` refuses both
`VERIFIED` and `ACTIVE`. A focused `verify_component()` alone performs `SHADOW ->
VERIFIED`, revalidates the exact eligible stored promotion assessment and D2 payload
artifact, and writes its hash on the lifecycle revision. Existing C1 call sites/tests are
updated to the focused method without weakening historical schema compatibility.

A failed canary remains disabled and must not be rolled back into service. The rollback
proof therefore runs on a separate scratch lifecycle unless the real canary succeeded.
Successful rollback restores the prior receipt selected by the existing receipt chain;
callers cannot nominate an arbitrary revision. Expansion from successful canary routing
to the already approved steady-state subset is a config change, not a second activation.
Extend the JSON receipt contract backward-compatibly so every D2 disable records cause and
`rollback_permitted`. Canary failure writes `false`; `roll_back()` checks the latest
disable receipt and refuses structurally. Successful-canary kill-switch proof writes
`true`. Historical receipts keep their previous semantics; every D2 caller must set the
field explicitly.

### 4.13 Evidence roots and persistence

D2 uses:

- one D2 evidence PostgreSQL database;
- one D2 learning/evidence Artifact Store root plus separately configured final A/B and
  canary holdout roots that are not injected into fitting;
- separate sandbox and backup roots;
- a unique scratch database and artifact root for every destructive or truncating matrix
  row;
- immutable before/after fingerprints for development, C3, D1, and D2 stores.

All manifests, model bytes, predictions, metrics, assessments, approvals, receipts, and
recovery outputs are content-addressed or hash-bound through existing authority. Large
payloads remain in the Artifact Store. Secrets, API keys, authorization headers, and
restricted inputs remain excluded despite the project's open-development data policy.

### 4.14 Expected focused code boundary

Likely existing files to extend:

- `src/cognitive_os/domain/learned.py`;
- `src/cognitive_os/domain/learned_evidence.py` only if the richer evidence contract
  cannot remain in `domain.learned`;
- `src/cognitive_os/learning/leakage.py`;
- `src/cognitive_os/learning/promotion.py`;
- `src/cognitive_os/application/services/learned_datasets.py`;
- `src/cognitive_os/application/services/learned_intake.py` for accepted evaluation-only
  runtime intake versus typed quarantine;
- `src/cognitive_os/application/services/reality_campaign.py` for the versioned ordered
  candidate/partition manifests and receipt-aware `RealityCampaignLedger.plan_resume()`;
- `src/cognitive_os/application/services/reality_campaign_runner.py`;
- `src/cognitive_os/application/services/learned_evidence.py` only for exact-evidence
  validation, not a second lifecycle;
- `src/cognitive_os/coding/outcome_recording.py` so every referenced task/candidate/artifact
  is validated before an append-only outcome is written;
- `src/cognitive_os/domain/reality.py` for backward-compatible manifest/sequence-receipt
  contracts;
- `src/cognitive_os/events/coding_events.py` and
  `src/cognitive_os/events/coding_event_service.py` for the bounded campaign-sequence event
  and compare-and-set SYSTEM-stream append;
- `src/cognitive_os/infrastructure/learned/artifacts.py`;
- `src/cognitive_os/experience/graph_retrieval.py`;
- `src/cognitive_os/experience/graph_context.py` only if the selected secondary path
  requires the corrected ordering;
- `src/cognitive_os/config/learned_config.py`;
- `scripts/learned.py`, `scripts/experience.py`, and `.github/workflows/ci.yml`.

Expected new focused modules:

- `src/cognitive_os/learning/correction_ranking.py`;
- `src/cognitive_os/application/services/correction_ranking_observations.py`;
- `src/cognitive_os/application/services/correction_candidate_sequencer.py`;
- at most `src/cognitive_os/application/services/learned_runtime.py`;
- focused tests under `tests/cognitive_os/learning/` and the existing learned-evidence,
  experience, coding, configuration, and PostgreSQL test trees.

Do not create a package hierarchy or framework for hypothetical second learned
components.

### 4.15 End-to-end data flow

```text
rights-cleared task and four opaque correction candidates
        |
        +--> role-specific SELF_PLAY label_all campaign --> sandbox + hidden verifier
        |                               |
        |                               v
        |                   training/calibration observations
        |                               |
        |                     group-aware immutable manifests
        |                               |
        |             strongest baseline -> kNN -> conditional later rung
        |                               |
        |                canonical JSON candidate artifact selected
        |
        +--> sealed REAL_GOVERNED_RUN final A and B label_all manifests
                                        |
                            prediction manifest written first
                                        |
                            all candidates independently verified
                                        |
                         paired benefit + retrieval + retention/OOD
                                        |
                     registered -> shadow -> verified -> human approval
                                        |
                   durable activation + canary config subset
                                        |
              stop-on-first-verified canary -> kill switch/restart/rollback proof
                                        |
                  bounded campaign sequencing + mandatory verifier
```

---

## 5. Detailed work items

The execution contains 81 independently reviewable tasks in ten epics. `P0` is
gate-blocking. `P1` is required only when its stated continuation condition is true.
No P1 learner rung may be opened after either final holdout batch has been accessed.

Conditional P0 work has five explicit boundaries:

- `design-conditional` opens only when S21D2-010 selects a feasible primary surface;
- `candidate-conditional` opens only when S21D2-049 selects a learner;
- `final-conditional` opens only when candidate/artifact/OOD prechecks authorize final
  access;
- `pass-conditional` opens only when the pre-activation assessment is eligible.
- `activation-conditional` opens only after S21D2-072 records a successful activation;
  it remains open after either a successful or failed governed canary.

At any valid pre-registered stop, each transitively dependent experimental task is closed
by an immutable `not-opened` record naming the upstream decision hash, whether or not its
heading repeats a conditional label. That record satisfies its DAG dependency but never
counts as success evidence. Baseline reconciliation, the applicable fixture/implementation
matrix, report, documentation, protected release, negative Gate L2 assessment, and
successor-remediation handoff can never be skipped.

## EPIC S21D2-E00 — Baseline, chronology, and isolation

### S21D2-000 — Revalidate the exact D2 starting point

- **Priority:** P0
- **Deliver:** a baseline record containing local and remote `main`, D1 tag object and
  peeled commit, PRs `#217/#218`, both exact-head CI runs, migration heads, branch
  protection, required contexts, collaborator count, and working-tree state.
- **Acceptance:** the branch starts from revalidated current `origin/main`; the D1 tag is
  independently verified; any drift is reconciled before code or evidence changes.
- **Evidence:** `sprint-21d2-baseline.json` plus command transcript in the report.

### S21D2-001 — Record the immutable D1 baseline erratum

- **Priority:** P0
- **Depends on:** S21D2-000
- **Deliver:** one hash-bound erratum naming the commit/file-count, Gate-condition,
  execution-row, and chronology discrepancies from section 1.7.
- **Acceptance:** no D1 tag, report, assessment, or release artifact byte changes; remote
  Git/CI timestamps are distinguished from recorded evidence times.
- **Evidence:** `sprint-21d2-d1-erratum.json` and a report section resolving each item.

### S21D2-002 — Create isolated D2 authorities

- **Priority:** P0
- **Depends on:** S21D2-000
- **Deliver:** D2-specific PostgreSQL environment, Artifact Store, sandbox, backup root,
  and unique matrix scratch roots.
- **Acceptance:** resolved paths cannot target the development, C3, or D1 evidence pairs;
  destructive tests require `COGOS_TRUNCATABLE_DATABASE` consent on scratch databases.
- **Evidence:** redacted resolved configuration and before/after store fingerprints.

### S21D2-003 — Freeze the inherited evidence-role inventory

- **Priority:** P0
- **Depends on:** S21D2-001, S21D2-002
- **Deliver:** exact inventory of 214 outcomes, 120 deferred ranking examples, 80 graph
  pairs, 80 graph queries, MiniLM identity, source roles, observation IDs, and hashes.
- **Acceptance:** all inherited outcomes are marked development/evaluation-only; zero
  inherited real-run observation is eligible for D2 training or calibration.
- **Evidence:** immutable inventory plus a negative training-membership proof.

### S21D2-004 — Open the draft implementation PR in wave 1

- **Priority:** P0
- **Depends on:** S21D2-000
- **Deliver:** draft PR against current protected `main`, naming this backlog, branch,
  gate, migration default, data roles, and first vertical slice.
- **Acceptance:** CI exercises the branch before bulk evidence generation; branch
  protection and reviewer settings remain unchanged.
- **Evidence:** PR URL and initial check run.

## EPIC S21D2-E01 — Surface revision and immutable experimental design

### S21D2-010 — Re-audit correction ranking as the primary candidate

- **Priority:** P0
- **Depends on:** S21D2-003
- **Deliver:** revision-2 audit of label authority, actionability, balance, group
  structure, attribution, deterministic headroom, data roles, and decision cost.
- **Acceptance:** selection is permitted only if the planned self-play and final sets can
  meet 200/40/100/100 minima and at least 20 paired changes without verifier bypass; a
  rejection is a terminal design stop with an explicit reason and downstream not-opened
  chain.
- **Evidence:** `sprint-21d2-surface-audit.json`, created before final outcomes exist.

### S21D2-011 — Freeze the ranking and action contract

- **Priority:** P0
- **Depends on:** S21D2-010
- **Deliver:** task-level decision, four-candidate, verifier label, abstention, fallback,
  and action-cost contracts.
- **Acceptance:** a score can change only candidate order; rejected candidates never
  become accepted; verification cannot be assigned a greater cost than unsafe skipping.
- **Evidence:** domain contract tests and schema export.

### S21D2-012 — Freeze feature timing and fitted-field exclusions

- **Priority:** P0
- **Depends on:** S21D2-011
- **Deliver:** `correction-ranking-v1` feature schema, source/timing map, and explicit
  fitted-field projection.
- **Acceptance:** every allowed field proves pre-outcome availability; every prohibited
  identity, oracle, hidden-control, and post-outcome field fails with a stable reason.
- **Evidence:** schema, positive fixtures, seeded-oracle tests, and fitted-matrix scan.

### S21D2-013 — Define transitive group and near-duplicate policy

- **Priority:** P0
- **Depends on:** S21D2-010
- **Deliver:** group identity derived from task, repository, generator-template lineage,
  normalized source similarity, and source lineage.
- **Acceptance:** seed variants and transitive near-duplicate clusters remain one group;
  one group belongs to exactly one of training, calibration, final A, final B, or canary.
- **Evidence:** group manifest and adversarial crossing tests.

### S21D2-014 — Complete the paired power and retrieval-yield analysis

- **Priority:** P0
- **Depends on:** S21D2-011
- **Deliver:** pre-fit calculation over task-group pairs for the +5-point/20%-error gate,
  expected discordant-pair rate, two batches, 2,000-resample interval, and conservative
  yield of qualifying failed-state retrieval queries.
- **Acceptance:** final count is at least 50 groups and 200 outcomes; if the calculation
  or the 50-query retrieval requirement needs more, group counts rise before sealing and
  never fall afterward.
- **Evidence:** canonical power-analysis artifact with assumptions and limitations.

### S21D2-015 — Freeze campaign and split protocols

- **Priority:** P0
- **Depends on:** S21D2-012, S21D2-013, S21D2-014
- **Deliver:** role, minimum-count, candidate-count, seed, rights, source, verifier,
  timeout, failure, retry, duplicate, and child-manifest policies for all five partitions.
- **Acceptance:** this task freezes executable selection rules, not member hashes that do
  not exist yet; late/extra rows and wrong provenance fail; training code has no API that
  returns final or canary members/outcomes.
- **Evidence:** hash-bound campaign protocol and split-policy tests.

### S21D2-016 — Freeze metrics, baselines, bootstrap, and budgets

- **Priority:** P0
- **Depends on:** S21D2-015
- **Deliver:** primary/secondary metrics, strongest-baseline rule, changed-decision rule,
  paired-bootstrap seed and resamples, calibration-OOD and untouched promotion-OOD suite
  protocols, OOD/retention thresholds, and CPU budgets.
- **Acceptance:** metrics use task groups as the paired unit; abstentions and no-solution
  tasks remain in exact denominators; no final result can select a metric or threshold.
- **Evidence:** evaluator manifest and property tests.

### S21D2-017 — Publish pre-registration revision 2

- **Priority:** P0
- **Depends on:** S21D2-010; S21D2-011 through S21D2-016 only when the design branch opens
- **Deliver:** on selection, one content-addressed bundle selecting correction ranking as
  primary, correction context as secondary, and naming all available protocol, feature,
  learner, retrieval, gate, and stop-rule hashes; on rejection, a hash-bound null-primary
  decision with the S21D2-010 reason and not-opened root.
- **Acceptance:** fitting and final evaluators reject a missing or mismatched bundle;
  exact member manifests created later are hash-bound children governed by this bundle,
  not retroactively inserted into it; any permitted pre-final revision creates a new
  immutable identity; the null path cannot be interpreted as learner authorization.
- **Evidence:** Artifact Store bytes, learned lineage, Event Store reference, and
  chronology proving publication before fitting.

## EPIC S21D2-E02 — Governed training, calibration, and sealed holdouts

### S21D2-020 — Add explicit manifest selection to the dataset builder

- **Priority:** P0
- **Depends on:** S21D2-015
- **Deliver:** backward-compatible explicit member/group/partition input and complete
  paginated resolution for `LearnedDatasetBuilder`, with a versioned partition/split
  manifest and exact split-assignment digest in explicit dataset identity.
- **Acceptance:** default C1 behavior remains green; explicit mode rejects extra,
  missing, duplicate, wrong-hash, wrong-role, cross-group, and real-run training members;
  more than 500 observations resolve through bounded `limit`/`offset` pages; split union
  exactly equals members, fit/calibration are nonempty, groups do not cross, and two exact
  split assignments over the same members produce different dataset IDs.
- **Evidence:** unit, contract, in-memory, and PostgreSQL parity tests.

### S21D2-021 — Build the four-candidate task package

- **Priority:** P0
- **Depends on:** S21D2-011, S21D2-013
- **Deliver:** rights-clean task package with four opaque, deterministically shuffled
  candidate IDs, public inputs, hidden verifier reference, outcome-neutral D2 recipe
  identities, candidate provenance, and a role-specific campaign version/profile that
  participates in `RealityRunIdentity`; all four manifests/patch artifacts are built and
  sealed before features.
- **Acceptance:** strategy/recipe metadata is stored outside the feature projection;
  existing `correct_*`/`incomplete_*` values are forbidden in D2; hidden-verifier outcomes
  may contradict recipe quality and remain valid labels; identical task/verifier inputs
  apply to all candidates; candidate creation has no outcome field. Refactor every
  fallible run/candidate/outcome invariant shared by `CodingOutcomeRecorded` and
  `RealityOutcomeReference` into one pure validator invoked while constructing the event
  payload before append. After append, reference construction adds only the returned UUID
  `source_event_id` and is provably non-failing; a rejected invariant leaves artifacts
  unreferenced but no partial authoritative event.
- **Evidence:** enum/schema export, four-manifest/patch seal, deterministic order replay,
  contradictory-outcome cases, validation-before-append regression, hidden-control, and
  leakage tests.

### S21D2-022 — Expand and seal the five-partition task corpus

- **Priority:** P0
- **Depends on:** S21D2-017, S21D2-021
- **Deliver:** outcome-free catalogues for at least 50 training, 10 calibration, 25 final
  A, 25 final B, and five canary groups, four candidates each; at least 115 distinct
  groups overall and at least 85 genuinely new relative to D1's 30 groups; plus a
  hash-bound OOD precheck submanifest over calibration groups and a separately untouched
  promotion OOD submanifest over final A/B groups, specifying at least 100 future ranker
  decisions across at least ten final groups.
- **Acceptance:** all task/template/source-lineage and transitive near-duplicate checks
  pass; every source licence/right and hidden verifier replay is verified before any
  candidate execution; prior public tasks are confined to one partition permanently.
- **Evidence:** five sealed catalogues, corpus-expansion count proof, source-rights report,
  generator replay, verifier replay, both OOD manifests, and pairwise group-disjointness
  matrix.

### S21D2-023 — Execute and ingest self-play training evidence

- **Priority:** P0
- **Depends on:** S21D2-017, S21D2-020, S21D2-022, S21D2-029, S21D2-058
- **Deliver:** at least 200 unique `SELF_PLAY` candidate outcomes through the existing
  sandbox and independent verifier.
- **Acceptance:** `label_all` executes every manifest candidate; terminal
  timeouts/malformed/rejected rows persist and are never replaced; an unrecorded
  infrastructure interruption may rerun but is counted separately; every feature record
  precedes its outcome; zero network/provider use.
- **Evidence:** campaign ledger, Artifact Store bytes, Event Store references, and count
  reconciliation.

### S21D2-024 — Execute and ingest self-play calibration evidence

- **Priority:** P0
- **Depends on:** S21D2-017, S21D2-020, S21D2-022, S21D2-029, S21D2-058
- **Deliver:** at least 10 new groups and 40 unique `SELF_PLAY` calibration outcomes.
- **Acceptance:** no training, inherited, final, or canary group crosses calibration;
  the presealed calibration OOD perturbations are resolved and retained outside fitting;
  calibration is not merged into fitting before final candidate selection.
- **Evidence:** calibration campaign, calibration-OOD inputs, and group-disjointness report.

### S21D2-025 — Materialise immutable training and calibration snapshots

- **Priority:** P0
- **Depends on:** S21D2-023, S21D2-024
- **Deliver:** one exact `CorpusRole.TRAINING` dataset with explicit disjoint `fit` and
  `calibration` splits, plus feature matrices, label balances, distribution summaries,
  manifests, and lineages.
- **Acceptance:** training has at least 200 and calibration at least 40 observations;
  provenance is `SELF_PLAY` only; every member and group matches revision 2.
- **Evidence:** durable records plus restart/replay identity test.

### S21D2-026 — Seal final batch A without outcomes

- **Priority:** P0
- **Depends on:** S21D2-015, S21D2-022
- **Deliver:** at least 25 new groups and 100 candidate slots with exact task, group,
  candidate, verifier, seed, and rights identities, but no verifier outcomes.
- **Acceptance:** groups are new relative to training/calibration/D1 and batch B; access
  is capability-isolated: fitting receives only the manifest hash and no holdout root/
  artifact port; the separately configured evaluation process can open bodies only after
  S21D2-060 authorization.
- **Evidence:** sealed batch-A manifest, process/config boundary, and no-capability
  premature-access test.

### S21D2-027 — Seal final batch B without outcomes

- **Priority:** P0
- **Depends on:** S21D2-015, S21D2-022
- **Deliver:** a second independently generated set of at least 25 groups and 100
  candidate slots.
- **Acceptance:** batch B is disjoint from every earlier role and generated with a
  separately recorded seed/path; its holdout root is not injected into fitting and its
  outcomes remain absent until candidate freeze.
- **Evidence:** sealed batch-B manifest and cross-manifest group proof.

### S21D2-028 — Seal a separate canary manifest

- **Priority:** P0
- **Depends on:** S21D2-015, S21D2-022
- **Deliver:** at least five new task groups and 20 candidate slots, with explicit canary
  routing bounds and kill-switch identity.
- **Acceptance:** canary groups cross no earlier role; no canary outcome is used in fit,
  calibration, final comparison, or promotion decision.
- **Evidence:** canary manifest, group proof, and routing-policy hash.

### S21D2-029 — Project role-bound correction-ranking observations

- **Priority:** P0
- **Depends on:** S21D2-015, S21D2-020, S21D2-021
- **Deliver:** focused `CorrectionRankingObservationProjector` that reads the exact
  sealed partition manifest and emits only `experience.correction_ranking` observations.
- **Acceptance:** training/calibration map only to `SELF_PLAY`; final A/B/canary map only
  to `REAL_GOVERNED_RUN`; self-play source kind is
  `correction_self_play_task_run`, verifier-backed but never real-governed; final/canary
  source kind is `governed_task_run`; caller-supplied surface/provenance/source kind is
  impossible; event and artifact bytes, candidate membership, task/group, campaign
  version/profile, and feature-before-outcome chronology are checked. The existing C3
  harvester remains backward compatible.
- **Evidence:** projector unit/contract tests, wrong-role/campaign negative cases, and
  in-memory/PostgreSQL parity.

## EPIC S21D2-E03 — D1 retrieval remediation

### S21D2-030 — Separate internal vector scores from public truncation

- **Priority:** P0
- **Depends on:** S21D2-000, S21D2-004
- **Deliver:** one internal MiniLM scoring path used by vector output and GED shortlist,
  without duplicating embedding or ranking logic.
- **Acceptance:** public vector results still return at most ten; GED considers twenty
  when `vector_shortlist=20`; tie order and cache behavior remain deterministic.
- **Evidence:** exact 20-considered/10-returned regression test.

### S21D2-031 — Freeze graph resource-policy revision 2

- **Priority:** P0
- **Depends on:** S21D2-030, S21D2-017
- **Deliver:** width-20 policy with unchanged node/edge/depth, pair-timeout, query-budget,
  result, cutoff, and fallback semantics.
- **Acceptance:** a comparison never starts unless its timeout is reserved; incomplete
  results stay counted; policy identity is embedded in every result.
- **Evidence:** contract tests and canonical resource-policy artifact.

### S21D2-032 — Run D1 diagnostic regression after the fix

- **Priority:** P0
- **Depends on:** S21D2-031
- **Deliver:** width-20 vector and bounded-GED diagnostics on the frozen D1 80-query set.
- **Acceptance:** results are labelled development-only; old width-10 evidence remains
  immutable; latency, cutoffs, coverage, recall, MRR, nDCG, and residual types are shown.
- **Evidence:** `sprint-21d2-d1-retrieval-diagnostic.json`.

### S21D2-033 — Build the new unseen-task retrieval holdout

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-026, S21D2-027, S21D2-049, S21D2-061, S21D2-062
- **Deliver:** at least 50 query/relevance records derived from final A/B groups after
  candidate freeze, with complete own-group exclusions and judgement tiers.
- **Acceptance:** no D1 query is reused; relevance is sealed before any D2 ranking result;
  query A/B identities remain separately reportable.
- **Evidence:** graph-query/relevance manifest and chronology proof.

### S21D2-034 — Evaluate all pre-registered bounded retrieval arms once

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-031, S21D2-033, S21D2-061, S21D2-062
- **Deliver:** no-memory, lexical, exact-signature, MiniLM vector, and width-20 bounded-
  GED results on the identical new pool/query set.
- **Acceptance:** all pre-registered arms, budgets, cutoffs, ties, failures, exact
  denominators, and batch-separated metrics are immutable and reproducible.
- **Gate effect:** condition 15 passes only if one bounded arm reaches both 0.70 Recall@5
  and 0.50 MRR@10; otherwise this task completes as negative evidence.
- **Evidence:** `sprint-21d2-retrieval-benchmark.json` and deterministic replay.

### S21D2-035 — Classify post-width-20 residuals

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-034
- **Deliver:** per-query candidate-generation, rerank-ordering, relevance, timeout, tie,
  and data-quality residual taxonomy.
- **Acceptance:** no final retuning follows; any ordering-dominant result can only inform
  a future ADR with a new holdout; ADR 0090 remains the D2 no-go authority.
- **Evidence:** residual artifact and explicit FGW continuation decision.

### S21D2-036 — Preserve the advisory context boundary

- **Priority:** P0
- **Depends on:** S21D2-030
- **Deliver:** context integration tests over corrected retrieval ordering.
- **Acceptance:** graph candidates remain hash-resolvable, verified, body-free,
  non-required, non-pinned, non-evidence, and unable to execute or accept a correction.
- **Evidence:** Context Builder unit/integration tests and health output.

## EPIC S21D2-E04 — Features, baselines, learner ladder, and candidate freeze

### S21D2-040 — Implement the correction feature encoder

- **Priority:** P0
- **Depends on:** S21D2-012, S21D2-021
- **Deliver:** bounded text/embedding/static-feature encoder for the ranking surface,
  separate from `skill.selection`, plus a pre-outcome feature-record contract.
- **Acceptance:** identical inputs produce identical bytes; missing values are explicit;
  numeric features use frozen clipping/scaling or explicit channel weights; raw
  IDs/hashes and prohibited bodies cannot enter output; feature records can be sealed
  before sandbox/verifier execution.
- **Evidence:** golden vectors, cross-domain fixtures, and schema/hash tests.

### S21D2-041 — Validate the exact fitted matrices

- **Priority:** P0
- **Depends on:** S21D2-025, S21D2-040
- **Deliver:** leakage, temporal-order, duplicate, near-duplicate, group, and label-derived
  scans over serialized training and calibration matrices.
- **Acceptance:** seeded oracle and identity columns fail; valid matrices have zero
  forbidden fields and every row resolves to one pre-outcome source chain.
- **Evidence:** immutable fitted-feature validation report.

### S21D2-042 — Implement and freeze the baseline ladder

- **Priority:** P0
- **Depends on:** S21D2-025, S21D2-040
- **Deliver:** fixed-order, deterministic structural, lexical, MiniLM, eligible bounded
  graph, and learned-rung comparison on calibration groups.
- **Acceptance:** every rung uses identical groups and labels; strongest non-learned rung
  is derived rather than caller-supplied and frozen before final access.
- **Evidence:** baseline-ladder artifact and straw-man rejection tests.

### S21D2-043 — Implement bounded cosine k-NN

- **Priority:** P0
- **Depends on:** S21D2-040
- **Deliver:** focused correction ranker with immutable exemplars, neighbour scores,
  deterministic ties, confidence, OOD abstention, and explanations.
- **Acceptance:** no default dependency; task/candidate identity is absent from distance;
  equal scores preserve frozen baseline order; health fails clearly when exemplars or
  MiniLM are unavailable.
- **Evidence:** unit, property, determinism, and budget tests.

### S21D2-044 — Calibrate k-NN on the sealed calibration set

- **Priority:** P0
- **Depends on:** S21D2-022, S21D2-041, S21D2-042, S21D2-043
- **Deliver:** results for the small pre-registered grid of `k`, similarity, agreement,
  confidence, and OOD thresholds, plus a sealed calibration/adversarial OOD precheck.
- **Acceptance:** training is fit-only and calibration is selection-only; all attempted
  settings remain visible; the S21D2-022/024 calibration-OOD submanifest is used exactly;
  any confident OOD precheck error blocks final access; one
  setting is selected by the declared rule or k-NN fails.
- **Evidence:** calibration matrix, predictions, OOD precheck, residuals, and selected-
  settings hash.

### S21D2-045 — Apply the k-NN continuation decision

- **Priority:** P0
- **Depends on:** S21D2-044
- **Deliver:** immutable pass/stop or fail/continue record.
- **Acceptance:** a passing k-NN stops later learner work; a failure names whether signal
  is linear, non-linear, data-deficient, OOD-deficient, or absent using calibration only.
- **Evidence:** ladder decision artifact and code-path test preventing speculative rungs.

### S21D2-046 — Evaluate logistic/SGD only if authorized

- **Priority:** P1, conditional
- **Depends on:** failed S21D2-045 decision that authorizes parametric continuation
- **Deliver:** dependency/ADR decision, direct optional extra if approved, one bounded
  linear candidate, inert coefficient artifact, and calibration comparison.
- **Acceptance:** identical frozen features/groups; fixed seed and regularization grid;
  offline install, license, security, and distribution checks pass.
- **Evidence:** ADR, dependency diff, predictions, calibration report, or not-opened proof.

### S21D2-047 — Evaluate one small tree only if authorized

- **Priority:** P1, conditional
- **Depends on:** failed-nonlinear S21D2-046 decision
- **Deliver:** one fixed depth/leaf/class-weight tree and inert validated node structure.
- **Acceptance:** no ensemble or unbounded search; identical data; OOD/abstention wrapper;
  dependency evidence is reused rather than duplicated.
- **Evidence:** tree artifact, calibration comparison, or not-opened proof.

### S21D2-048 — Exercise the one permitted pre-final revision

- **Priority:** P1, conditional
- **Depends on:** S21D2-045, or S21D2-046/S21D2-047 when opened
- **Deliver:** one revised feature/calibration bundle only when residual evidence meets
  section 3.4; otherwise an explicit not-used record.
- **Acceptance:** final membership and thresholds do not change; all candidates rerun;
  revision 3 predates candidate freeze; a second revision is rejected.
- **Evidence:** revision diff, reason, complete rerun, chronology, or not-used artifact.

### S21D2-049 — Select at most one candidate before final access

- **Priority:** P0
- **Depends on:** S21D2-045, plus S21D2-046 through S21D2-048 when applicable
- **Deliver:** either one selected learner with settings, feature hash, training/
  calibration hashes, baseline identity, and limitations, or an immutable null-selection
  decision naming the failed continuation rule.
- **Acceptance:** at most one candidate satisfies the contract; a selection or null result
  is committed before any final verifier outcome or relevance ranking is read. Selection
  freezes the candidate but does not itself authorize final access; a null result keeps
  final access closed and drives downstream not-opened records.
- **Evidence:** candidate-selection/null artifact, commit/time order, and access guard.

## EPIC S21D2-E05 — Immutable artifact and runtime wiring

### S21D2-050 — Add the canonical JSON artifact format

- **Priority:** P0
- **Depends on:** S21D2-012, S21D2-017, S21D2-040
- **Deliver:** `LearnedArtifactFormat.JSON` and the versioned correction-ranker artifact
  contract from section 4.8.
- **Acceptance:** canonical bytes and their external Artifact Store hash are stable; the
  payload contains no self-referential hash; NaN/infinity, duplicates, wrong dimensions,
  excessive members, and missing member hashes fail validation.
- **Evidence:** schema export, round-trip, adversarial, and size-bound tests.

### S21D2-051 — Fit and store the selected immutable artifact

- **Priority:** P0, candidate-conditional
- **Depends on:** S21D2-049, S21D2-050
- **Deliver:** one model artifact written through `ArtifactService`, with exact MODEL
  lineage binding the component ID, artifact schema, descriptor version, fitted feature
  bundle, and dataset/split identities. No lifecycle revision is claimed before
  registration; S21D2-059 allocates it.
- **Acceptance:** fit reads only training plus allowed calibration metadata; bytes include
  every identity required for replay; declared and observed hashes agree; lineage does
  not invent a component revision or parent-lineage field absent from the contract.
- **Evidence:** artifact ID/hash, lineage, descriptor, and independent rebuild comparison.

### S21D2-052 — Implement the narrow verified loader

- **Priority:** P0
- **Depends on:** S21D2-043, S21D2-050
- **Deliver:** correction-artifact loader with integrity, media, size, JSON, schema,
  dimension, model, descriptor, and revision checks.
- **Acceptance:** it constructs only a known correction ranker; no import/eval/object
  graph path exists; joblib/pickle and unknown formats remain rejected.
- **Evidence:** fixture loads plus missing, corrupt, tampered, oversized, wrong-model,
  wrong-revision, and unsafe-format tests; S21D2-060 supplies the selected-artifact load.

### S21D2-053 — Implement the durable runtime resolver

- **Priority:** P0
- **Depends on:** S21D2-052
- **Deliver:** one application-layer resolver for durable active state, configuration
  allowlist, exact artifact lineage, descriptor, and MiniLM health, returning an
  immutable task-lifetime snapshot.
- **Acceptance:** disagreement or absence returns deterministic fallback with a stable
  health reason; more than one active revision fails closed; the in-memory registry is
  not used as a second durable lifecycle authority.
- **Evidence:** resolver truth-table tests in memory and PostgreSQL.

### S21D2-054 — Implement bounded candidate sequencing

- **Priority:** P0
- **Depends on:** S21D2-053
- **Deliver:** `CorrectionCandidateSequencer` integrated into `RealityCampaignRunner`,
  with explicit `label_all` and `stop_on_first_accepted` modes over four prebuilt,
  validated, outcome-neutral candidate manifests, plus a versioned
  `RealityCampaignSequenceRecorded` receipt persisted with compare-and-set on the Event
  Store campaign stream.
- **Acceptance:** all four candidate artifacts are built and sealed before the first
  attempt. The runner preserves the manifest's opaque candidate-ID order and never keys,
  deduplicates, or sorts by recipe/strategy name. Training/calibration `label_all` records
  and executes only the frozen baseline order because no learner exists yet. Final/shadow
  `label_all` additionally records the counterfactual learned order but executes every
  candidate in the frozen baseline order; it obtains the selected artifact through the
  narrow direct loader and immutable evaluation snapshot, never through the ACTIVE-only
  resolver. Only
  post-activation canary/active mode uses the durable active resolver, tries the resolved
  order, and stops after independent verifier acceptance. Learned output may only permute
  opaque IDs; candidate bytes, sandbox, verifier, and acceptance rules remain unchanged.
  The receipt binds mode, manifest hash, baseline and resolved order, actual attempt
  order, accepted candidate/position, stop reason, and intentionally unattempted IDs.
  `RealityCampaignLedger.plan_resume()` consumes that stream, never schedules an
  intentionally unattempted candidate, and returns a blocking repair action for an
  accepted persisted outcome if a crash occurred before receipt append. The runner seals
  that receipt before replanning. `CodingAgentFacade` is untouched.
- **Evidence:** ordered-manifest and receipt schemas, crash/resume and idempotency tests,
  Event Store campaign-stream replay/CAS tests, accepted-outcome-before-receipt recovery,
  plus end-to-end label-all, stop-first, active, absent, disabled, abstaining,
  corrupt-artifact, no-accepted-candidate, and verifier-failure cases.

### S21D2-055 — Add structured runtime health and reason codes

- **Priority:** P0
- **Depends on:** S21D2-053, S21D2-054
- **Deliver:** health state for component, durable revision, config, artifact, embedding,
  OOD, and fallback status without example/model payload disclosure.
- **Acceptance:** every fallback cause is observable and deterministic; health never
  claims active when runtime uses the baseline.
- **Evidence:** health fixtures, CLI output tests, and integrity integration.

### S21D2-056 — Preserve default-off configuration

- **Priority:** P0
- **Depends on:** S21D2-053
- **Deliver:** configuration support for the one correction component and separately
  hash-bound canary/steady-state routing subsets while retaining empty activation actors
  and components by default.
- **Acceptance:** tracked default/example configuration is fail-closed; D2 release evidence
  uses an explicit operator configuration; model/provider self-approval stays impossible.
- **Evidence:** configuration validation and default-invariance tests.

### S21D2-057 — Prove mandatory-path invariance

- **Priority:** P0, candidate-conditional
- **Depends on:** S21D2-051, S21D2-054, S21D2-056
- **Deliver:** exact decision hashes with the component absent, present-disabled,
  abstaining, and artifact-unavailable. Extend `MandatoryPathInvariance`
  backward-compatibly with an optional fourth artifact-unavailable hash: older schemas
  may omit it, but the D2 schema and promotion validator require it.
- **Acceptance:** all deterministic mandatory-path hashes match; verifier invocation and
  acceptance rules are byte-identical in every mode; an older three-hash record cannot
  make the D2 component eligible.
- **Evidence:** `MandatoryPathInvariance` record and replay test.

### S21D2-058 — Prove the first vertical slice before bulk campaigns

- **Priority:** P0
- **Depends on:** S21D2-004, S21D2-020, S21D2-022, S21D2-029, S21D2-040, S21D2-043,
  S21D2-050, S21D2-052, S21D2-054, S21D2-056
- **Deliver:** one training group and one synthetic sealed-evaluation group through
  feature sealing, role-bound projection, explicit dataset split, fixture k-NN fit,
  canonical JSON storage/load, `label_all` sequencing, fallback, restart, and scratch
  restore. Exercise `stop_on_first_accepted` only through an isolated scratch component
  with a fixture ACTIVE receipt/config; it is not a SHADOW or final execution mode.
- **Acceptance:** every new authority runs before bulk evidence; final A/B/canary bodies
  remain inaccessible; CI uses deterministic committed vector fixtures, while this local
  release slice separately verifies real pinned MiniLM bytes.
- **Evidence:** vertical-slice manifest, chronology and access-denial proof, CI fixture
  result, isolated scratch activation/sequence receipt, local MiniLM identity/hash,
  restart replay, and restore report.

### S21D2-059 — Register the selected artifact and enter shadow

- **Priority:** P0, candidate-conditional
- **Depends on:** S21D2-051, S21D2-052, S21D2-057
- **Deliver:** durable descriptor registration that allocates the initial lifecycle
  revision, reuses the verified MODEL lineage from S21D2-051, and performs the legal
  `REGISTERED -> SHADOW` transition before any governed shadow prediction or execution.
- **Acceptance:** component ID, descriptor version, artifact schema/bytes/hash, lineage,
  and the newly allocated lifecycle revisions agree; no pre-registration record claims
  that revision. The lifecycle ledger precedes S21D2-060 and S21D2-066; registration and
  SHADOW authorize no activation.
- **Evidence:** descriptor, MODEL lineage, lifecycle revisions, chronology, and replay.

## EPIC S21D2-E06 — Final evaluation and promotion evidence

### S21D2-060 — Seal predictions before executing final candidates

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-026, S21D2-027, S21D2-042, S21D2-049, S21D2-051,
  S21D2-052, S21D2-059
- **Deliver:** baseline and learned ranking/confidence/abstention for every final A/B task,
  preceded by a hash-bound final-access authorization that rechecks S21D2-044/049/051/052/
  057/059. Only after that decision may a dedicated evaluation worker receive the scoped
  capability for the selected final-A or final-B holdout root. Predictions are generated
  through the narrow direct loader from the selected SHADOW artifact and immutable
  evaluation snapshot, not the ACTIVE-only resolver, and are bound to manifest/artifact
  hashes before `label_all` verifier execution.
- **Acceptance:** predictions contain no final outcome; missing predictions block the
  corresponding execution; late prediction writes are rejected; predictions cannot
  change the frozen baseline execution order in final evaluation; final bodies/outcomes
  remain unreadable until the access decision is stored. Fitting, calibration, and
  candidate-selection processes never receive a final-root capability; capability use,
  root identity, worker identity, and decision hash are recorded.
- **Evidence:** final-access decision, capability allow/deny log, prediction manifests,
  direct-loader identity, and timestamp/hash-order proof.

### S21D2-061 — Execute final batch A without outcome replacement

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-060
- **Deliver:** all batch-A candidates executed in `label_all` mode through the same
  sandbox and hidden verifier, then role-bound projected into an exact
  `CorpusRole.EVALUATION` final-A dataset with immutable outcome evidence and lineage.
- **Acceptance:** at least 25 groups and 100 terminal outcomes; one computed terminal
  outcome per run identity and zero retry-to-success. An unrecorded infrastructure-
  interrupted attempt may rerun but is separately reported; every row resolves to a
  sealed prediction and independent verifier artifact; the evaluation snapshot contains
  only final-A `REAL_GOVERNED_RUN` members and preserves its sealed promotion-OOD slice.
- **Evidence:** batch-A ledger, artifacts, evaluation dataset/manifests/lineage, exact
  denominator, and integrity report.

### S21D2-062 — Execute final batch B without outcome replacement

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-060
- **Deliver:** independently generated `label_all` batch-B execution, verifier evidence,
  and a separate exact `CorpusRole.EVALUATION` final-B dataset/lineage.
- **Acceptance:** at least 25 groups and 100 outcomes; identical protocol to A; no setting
  changed after A; failures remain counted; only final-B `REAL_GOVERNED_RUN` members enter
  its evaluation snapshot, which preserves its sealed promotion-OOD slice.
- **Evidence:** batch-B ledger, artifacts, evaluation dataset/manifests/lineage, exact
  denominator, and protocol-diff proof.

### S21D2-063 — Compute paired material benefit

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-061, S21D2-062
- **Deliver:** per-task baseline/learned first choice, changed decisions, success, relative
  error, attempts, verifier-call proxy, coverage, abstention, latency, and bootstrap
  results. Provider/LLM cost is descriptive zero/zero, not an alternative passing gate.
- **Acceptance:** at least 200 outcomes are reconciled; every planned group, failure,
  abstention, changed decision, and paired resample is retained and reproducible.
- **Gate effect:** material benefit passes only with at least 20 changed tasks, the fixed
  aggregate threshold, a positive direction in A and B, and a 95% paired lower bound
  above zero; otherwise the result is a valid negative.
- **Evidence:** `sprint-21d2-material-benefit.json`, predictions, seed 21041, and 2,000
  reproducible resamples.

### S21D2-064 — Run cross-domain anti-forgetting replay

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-022, S21D2-054, S21D2-063
- **Deliver:** frozen retained replay for every accepted domain, learned surface, safety,
  governance, permission, secret, and destructive-action case.
- **Acceptance:** every planned case executes or has a typed failure; per-domain,
  aggregate, and case-level changes are itemized and reproducible.
- **Gate effect:** any safety accepted-to-rejected transition, domain loss below -2
  points, or aggregate loss below -1 point makes promotion ineligible.
- **Evidence:** `ForgettingAssessment`, per-domain before/after, and case-level diff.

### S21D2-065 — Run OOD and adversarial evaluation

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-054, S21D2-063
- **Deliver:** unseen domain/type, low-similarity, poisoned metadata, missing feature,
  oversized patch, distribution shift, and candidate-order adversaries across at least
  100 decisions and ten final A/B groups from the untouched submanifest sealed in
  S21D2-022 and resolved through the S21D2-061/062 evaluation datasets.
- **Acceptance:** every declared OOD decision, confidence, action, fallback, failure, and
  exact denominator is retained; every abstention executes baseline ordering.
- **Gate effect:** the report threshold is at most 1%, while any confident OOD error makes
  promotion ineligible under the existing contract.
- **Evidence:** `OutOfDistributionAssessment`, exact cases, confidence, and fallback logs.

### S21D2-066 — Run shadow mode against final evidence

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-059, S21D2-060, S21D2-061, S21D2-062
- **Deliver:** shadow predictions and disagreements while deterministic ordering remains
  the executed decision.
- **Acceptance:** zero executed-decision changes; `shadow_actual_outcome` remains `None`;
  final `label_all` execution order equals the frozen deterministic baseline; actual
  verifier outcomes join only by independent evidence hash.
- **Evidence:** `LearnedShadowResult` records and outcome-link manifest.

### S21D2-067 — Build the strengthened promotion assessment

- **Priority:** P0, final-conditional
- **Depends on:** S21D2-057, S21D2-063, S21D2-064, S21D2-065, S21D2-066,
  S21D2-068
- **Deliver:** backward-compatible D2 `LearnedPromotionAssessment` schema plus exact
  baseline ladder, material benefit, two batches, bootstrap, forgetting, invariance, OOD,
  distribution, shadow, retrieval/D1-remediation, artifact, and reproducibility hashes.
- **Acceptance:** eligibility is derived and impossible unless every pre-activation gate
  passes; the D2 descriptor cannot use an older sparse assessment; a negative result
  names the deepest failure and remains non-activatable.
- **Evidence:** canonical assessment bytes in the Artifact Store, a D2-schema
  `PROMOTION_ASSESSMENT` evidence record with `payload_artifact_id`, and mutation/
  adversarial/activation-time byte-verification tests.

### S21D2-068 — Assess closure of D1 conditions 6, 7, and 15

- **Priority:** P0
- **Depends on:** S21D2-034, S21D2-035, S21D2-063
- **Deliver:** D2 remediation record mapping new evidence to the three original conditions.
- **Acceptance:** on an opened final path, condition 6 uses at least 200 final outcomes,
  condition 7 uses at least 20 changed decisions, and condition 15 uses the new retrieval
  holdout and original floors. On any lawful pre-final stop, the record binds all upstream
  not-opened hashes and leaves conditions 6, 7, and 15 unresolved/not assessed rather
  than inventing denominators.
- **Evidence:** `sprint-21d2-gate-d1-remediation.json`, without editing historical Gate D1.

### S21D2-069 — Advance the governed component to VERIFIED

- **Priority:** P0, pass-conditional
- **Depends on:** eligible S21D2-067
- **Deliver:** focused `verify_component()` authority for the legal `SHADOW -> VERIFIED`
  transition after final, retrieval, benefit, forgetting, invariance, OOD, and shadow
  evidence all pass. Generic `advance_component()` must refuse both VERIFIED and ACTIVE.
- **Acceptance:** `verify_component()` reloads the exact stored eligible promotion record,
  verifies its D2 payload artifact bytes and dependency hashes, checks component/current
  revision/surface identity, and writes the assessment hash on the new lifecycle revision.
  The lifecycle cannot reach VERIFIED through a generic state argument, an ineligible or
  stale assessment, or before any dependency; a negative result produces a hash-bound
  not-opened record. Existing older-schema tests remain compatible without authorizing D2.
- **Evidence:** lifecycle revision, assessment/payload links, chronology, replay, generic-
  bypass rejection, stale/tampered evidence, and illegal-transition tests.

## EPIC S21D2-E07 — Approval, canary, activation, and rollback

### S21D2-070 — Prepare the exact activation bundle

- **Priority:** P0, pass-conditional
- **Depends on:** S21D2-069
- **Deliver:** re-verify the exact selected model bytes, record a fresh MODEL lineage for
  the same artifact, and assemble descriptor, current revision, D2 promotion payload,
  lineage, and activation-actor identities.
- **Acceptance:** the lineage verification is within the service's maximum age at
  activation; D2 assessment bytes are fetched and re-hashed; stale or mismatched state
  refuses bundle creation. A negative path records not-opened.
- **Evidence:** canonical activation bundle, fresh lineage, byte-verification transcript,
  and stale/tampered negative tests.

### S21D2-071 — Record explicit human approval

- **Priority:** P0, pass-conditional manual operator checkpoint
- **Depends on:** S21D2-070
- **Deliver:** `LearnedActivationApproval` naming exactly its existing contract fields:
  component ID/revision, surface, promotion-assessment hash, model-lineage ID, approval
  decision, human approver identity/kind, reason, and approval time.
- **Acceptance:** the positive approver kind is `HUMAN_OPERATOR`; refusal or mismatch is
  retained and blocks activation; no model/provider identity can approve. Scope,
  limitation, and expiry are not falsely claimed as approval fields; the activation
  caller remains controlled by `activation_actors`.
- **Evidence:** durable `LearnedActivationApproval` and authorization tests.

### S21D2-072 — Activate the approved surface with canary-only runtime routing

- **Priority:** P0, pass-conditional
- **Depends on:** S21D2-028, S21D2-071
- **Deliver:** the existing activation receipt for the exact approved bounded surface,
  plus a separately hash-recorded fail-closed runtime configuration selecting only the
  canary manifest/groups. The `activate()` transaction itself reloads the exact D2
  `PROMOTION_ASSESSMENT` evidence record and its `payload_artifact_id` and invokes
  `ArtifactService.verify_artifact` for the expected media type, schema/version, hash, and
  size before changing lifecycle state.
- **Acceptance:** the receipt binds only its real contract fields; the resolver requires
  both ACTIVE state and the matching canary config, so non-canary and config-mismatch
  tasks remain deterministic. Promotion, approval, lineage, revision, and fresh artifact
  verification are checked against stored state inside activation, not only during bundle
  preparation. Missing payload identity, wrong evidence role, stale revision, corrupt
  bytes, hash/size/media/schema mismatch, or verification-after-transition ordering blocks
  activation atomically.
- **Evidence:** activation receipt, canary-config hash/evidence, routing truth table,
  activation-time byte-verification trace, and tamper/order tests.

### S21D2-073 — Execute the governed canary

- **Priority:** P0, pass-conditional
- **Depends on:** S21D2-072
- **Deliver:** at least five task-group decisions over 20 presealed candidate slots using
  `stop_on_first_accepted`, with every actual attempt sandboxed and independently verified.
- **Acceptance:** no unverified correction is accepted; stop position, attempts, fallback,
  intentionally unattempted candidate IDs, all safety/retention/OOD/resource results, and
  any separately identified post-stop `label_all` audit are retained without presenting
  unexecuted candidates as outcomes or rescheduling them after restart.
- **Gate effect:** any safety, retention, OOD, resource, or routing failure disables the
  component exactly once with the typed failure cause and
  `rollback_permitted=false`, and makes Gate L2 ineligible; complete negative canary
  evidence still closes this work item.
- **Evidence:** canary campaign/config, actual outcomes, role-bound
  `CorpusRole.EVALUATION` canary dataset/manifests/lineage, decision traces, optional
  separate audit campaign, sequence receipts, disable receipt when failed, and operational
  assessment.

### S21D2-074 — Exercise the kill switch and fallback after restart

- **Priority:** P0, activation-conditional
- **Depends on:** S21D2-073
- **Deliver:** durable disable followed by process restart and a deterministic correction
  run. After a successful canary, the explicit kill-switch disable records its cause and
  `rollback_permitted=true`. After a failed canary, reuse S21D2-073's existing
  `rollback_permitted=false` receipt and do not issue a second disable.
- **Acceptance:** active lookup is empty/disabled, model bytes cannot affect order, and
  baseline decision matches its frozen digest immediately. Exactly one applicable disable
  receipt exists for the tested transition and later code cannot accidentally turn a
  failed canary into a rollback-permitted state.
- **Evidence:** reused or newly written disable receipt, receipt-chain audit, before/after
  health, restart transcript, and decision hash.

### S21D2-075 — Restore the prior approved activation through rollback

- **Priority:** P0
- **Depends on:** S21D2-004; S21D2-058 when the design path opens; S21D2-074 on every
  path where S21D2-072 activated the real component
- **Deliver:** `roll_back()` restoration of the exact prior activation selected from a
  durable receipt chain, followed by another restart. Use the real component only after
  a successful canary. After failed canary, directly prove refusal against S21D2-074's
  reused failure receipt and perform permitted restoration only on an isolated scratch
  component. If the design path never opened, use the minimal existing lifecycle fixture
  rather than fabricating a D2 model.
- **Acceptance:** a failed real canary remains disabled; callers cannot nominate a target;
  low-level `roll_back()` structurally refuses a latest disable receipt with
  `rollback_permitted=false`; approval/assessment/lineage hashes revalidate; the permitted
  scratch and successful-real paths restore only the chain-selected prior activation and
  are labelled distinctly.
- **Evidence:** rollback receipt, chain audit, active projection, replay proof, and proof
  that failed-canary rollback is refused even on a direct service call.

### S21D2-076 — Promote from canary routing to bounded steady state

- **Priority:** P0, pass-conditional
- **Depends on:** successful S21D2-073, S21D2-075
- **Deliver:** configuration/manifest revision expanding only the declared
  `experience.correction_ranking` scope.
- **Acceptance:** component remains unable to bypass verification or affect another
  surface; missing/corrupt/OOD paths still fall back; the successful canary evidence and
  new config hash are recorded separately. This expands only an already approved scope.
- **Evidence:** scope diff, resolver tests, and steady-state smoke run.

### S21D2-077 — Prove final active state and replacement readiness

- **Priority:** P0, pass-conditional
- **Depends on:** S21D2-076
- **Deliver:** final health, active projection, exact artifact identity, disable/rollback
  handles, and a final-state manifest that records the prospective successor's parent
  artifact identity without inventing a parent field in MODEL lineage. Valid governed
  runtime observations enter accepted evaluation-only intake; only unresolved, invalid,
  or policy-ineligible inputs enter quarantine.
- **Acceptance:** active state survives restart and restore; runtime rows cannot update the
  artifact, exemplars, coefficients, or thresholds. Accepted `REAL_GOVERNED_RUN`
  evaluation rows are permanently training-ineligible under the current contract and no
  snapshot may select them for fitting; any future use requires an explicit contract and
  policy revision plus newly eligible evidence, not merely a new snapshot. A future
  revision can be staged from the recorded parent artifact without mutating this one.
- **Evidence:** final active-state manifest, accepted-versus-quarantined intake tests,
  parent-artifact identity check, and no-online-update tests.

## EPIC S21D2-E08 — Operations, CI, recovery, and complete validation

E08 and E09 are mandatory on every outcome. An upstream conditional dependency may be
satisfied by its valid stop/not-opened hash; these tasks then validate, preserve, and
report only the implemented fixture/null/negative path plus common authorities. E08/E09
themselves never become not-opened.

### S21D2-080 — Extend the existing learned and experience CLIs narrowly

- **Priority:** P0
- **Depends on:** S21D2-030, S21D2-050, S21D2-052, S21D2-055
- **Deliver:** commands for correction dataset/fit/evaluate/health, retrieval policy,
  exact release-bundle application, and explicit null/not-opened reporting using existing
  scripts.
- **Acceptance:** no bypass flag, arbitrary deserializer, generic activate-anything path,
  credential echo, or default live provider; mutations require exact bundle and actor;
  an early null path exposes its stop/not-opened status without pretending fit/evaluate
  commands ran.
- **Evidence:** CLI help, success/failure contract tests, and redacted operator transcript.

### S21D2-081 — Extend unified integrity and health reporting

- **Priority:** P0
- **Depends on:** S21D2-020, S21D2-029, S21D2-052, S21D2-055
- **Deliver:** checks for role/group crossing, chronology, manifest membership, artifact
  lineage, active state, receipt chain, model identity, and store isolation.
- **Acceptance:** one seeded violation in each class fails with a stable reason; healthy
  output names exact counts and hashes rather than only `ok`; classes absent by a lawful
  stop are reported with the bound not-opened hash, not as healthy zero-count evidence.
- **Evidence:** integrity fixtures and CLI output.

### S21D2-082 — Close or document local evidence-database provisioning

- **Priority:** P0
- **Depends on:** S21D2-002
- **Deliver:** the smallest safe repository-supported provisioning/preflight path, or an
  explicit operator runbook if host authority prevents automation.
- **Acceptance:** D2 evidence setup is reproducible without reusing the development DB;
  `ALTER ROLE ... NOSUPERUSER` cannot leave a falsely successful partial bootstrap.
- **Evidence:** isolated preflight/provision transcript and negative case.

### S21D2-083 — Prove replay, restart, backup, and restore

- **Priority:** P0
- **Depends on:** S21D2-081; S21D2-077 additionally on the success path
- **Deliver:** backup and test restore of datasets, manifests, campaign sequence receipts,
  model bytes, assessment, artifact filesystem, and every lifecycle object that exists on
  the selected outcome path.
- **Acceptance:** restored counts and hashes match; on success the runtime resolves the
  same active model, while a negative release restores the exact inactive/SHADOW evidence
  state; `RealityCampaignLedger.plan_resume()` returns the same attempted and intentionally
  unattempted sets; missing metadata, receipt, or bytes fail restore verification.
- **Evidence:** backup manifest, restore report, and outcome-appropriate restore smoke.

### S21D2-084 — Exercise corruption and isolation failures

- **Priority:** P0
- **Depends on:** S21D2-052, S21D2-083
- **Deliver:** tampered JSON, missing bytes, metadata-only artifact, wrong root, stale
  verification, wrong model, partial DB restore, and poisoned feature scenarios.
- **Acceptance:** every case fails closed or falls back as designed; no test writes to the
  D2 evidence root unless that row owns it; all source-store fingerprints remain exact.
  An early-null path tests not-opened-evidence tampering and common store isolation instead
  of claiming nonexistent model cases ran.
- **Evidence:** negative matrix rows and before/after fingerprints.

### S21D2-085 — Add focused credential-free CI

- **Priority:** P0
- **Depends on:** S21D2-030, S21D2-043, S21D2-052, S21D2-054, S21D2-067
- **Deliver:** focused correction-ranking, dataset, artifact, runtime, lifecycle, and
  retrieval coverage for every implemented path, plus null/not-opened access-guard
  coverage, in normal CI with required extras.
- **Acceptance:** zero network, provider credential, GPU, mutable user store, or live
  service beyond the isolated PostgreSQL lane; CI fails on schema/evidence drift; a
  stopped design validates fixtures/null guards without claiming final/lifecycle evidence.
- **Evidence:** workflow diff and exact local-equivalent commands.

### S21D2-086 — Run the complete release matrix on scratch stores

- **Priority:** P0
- **Depends on:** S21D2-032, S21D2-034, S21D2-035, S21D2-036, S21D2-068,
  S21D2-075, S21D2-080, S21D2-081, S21D2-082, S21D2-083, S21D2-084, S21D2-085;
  S21D2-077 additionally on the success path
- **Deliver:** one expected-status matrix covering targeted tests, full suite, lint,
  formatting, typing, schema export, language, security, packaging, PostgreSQL,
  migration, artifact recovery, benchmarks, and CLI smoke.
- **Acceptance:** every row has expected and actual exit; no unexplained skipped row;
  conditional not-opened rows name their stop-decision hashes; evidence stores remain
  byte-identical during destructive rows; failures are retained.
- **Evidence:** `sprint-21d2-verification-matrix.json` plus logs and elapsed times.

## EPIC S21D2-E09 — Gate, documentation, protected release, and handoff

### S21D2-090 — Update architecture and operator documentation

- **Priority:** P0
- **Depends on:** S21D2-054, S21D2-083; S21D2-077 additionally on the success path
- **Deliver:** on implemented paths, correction-ranking data roles, artifact format,
  runtime resolver, fallback, approval, canary, kill-switch, restart, rollback, and
  evidence-store operations; on an early null path, the stop/not-opened and evidence-
  recovery procedure without nonexistent commands.
- **Acceptance:** commands use placeholders and exact prerequisites; unsafe formats and
  real-run training remain explicitly prohibited; no secret appears; documentation
  distinguishes implemented operations from not-opened future work.
- **Evidence:** documentation links, language check, and command smoke.

### S21D2-091 — Prepare the pre-release Gate L2 assessment

- **Priority:** P0
- **Depends on:** S21D2-068, S21D2-086; S21D2-077 additionally on the success path
- **Deliver:** condition-by-condition Gate L2 draft with direct evidence handles and a
  separate mapping of D1 remediation; the protected-release condition remains pending.
- **Acceptance:** any failed release-independent condition yields `does not pass`; when
  all are green the only permitted result is `conditional pass pending protected release`.
  Gate L2 has not passed at this task.
- **Evidence:** `docs/sprints/sprint-21/gate-l2-assessment.md`.

### S21D2-092 — Complete the Sprint 21D2 report

- **Priority:** P0
- **Depends on:** S21D2-086, S21D2-091
- **Deliver:** implementation scope, exact data denominators, every attempted or not-
  opened learner/retrieval/benefit/safety/OOD/lifecycle path, operations, deviations, and
  limitations.
- **Acceptance:** negative and positive results receive equal detail; no PR/tag claim is
  self-referential; D1 erratum and unchanged source-store fingerprints are included.
- **Evidence:** `docs/sprints/sprint-21/sprint-21d2-report.md`.

### S21D2-093 — Prepare the outcome-specific handoff

- **Priority:** P0
- **Depends on:** S21D2-091
- **Deliver:** on conditional success, a provisional Sprint 22A handoff with exact active
  component/artifact, bounded campaign-only scope, retained suites, metrics, fallback,
  limitations, APIs, hashes, and release prerequisites; on a negative result, a successor-
  remediation handoff naming the failed condition and required new holdout.
- **Acceptance:** no draft claims Gate L2 passed or Sprint 22A unblocked before release;
  the negative path does not create an S22A handoff; neither path reinterprets correction
  ranking as a universal domain model or claims coverage of `CodingAgentFacade`.
- **Evidence:** outcome-appropriate handoff at the repository's agreed path.

### S21D2-094 — Complete the protected implementation release

- **Priority:** P0
- **Depends on:** S21D2-090, S21D2-091, S21D2-092, S21D2-093
- **Deliver:** final PR review, all required checks, merge without bypass, exact-head
  post-merge `main` CI, the outcome-appropriate annotated tag, and remote verification.
- **Acceptance:** branch protection is unchanged; PR head, merge commit, CI head, peeled
  tag commit, and remote main agree as required; a success uses
  `sprint-21-learning-baseline`, while a negative result uses only
  `sprint-21d2-evidence-baseline`; the tag is created once after green CI.
- **Evidence:** PR URL, check list, CI run URL, tag object, peeled commit, and remote refs.

### S21D2-095 — Complete the post-release Gate L2 result

- **Priority:** P0
- **Depends on:** S21D2-094
- **Deliver:** update the Gate L2 assessment and outcome-specific handoff with exact
  implementation PR, merge, exact-head CI, tag object/peel, store fingerprints,
  migration head, component state, and limitations; merge those gate-result documents
  through a protected follow-up PR and verify its exact-head `main` CI.
- **Acceptance:** current `origin/main`, gate-close CI, and remote annotated tag are
  re-read after push; condition 29 changes from pending only with exact handles. On
  success, Gate L2 passes and Sprint 22A becomes unblocked only here. On a negative path,
  Gate L2 remains `does not pass` and only the remediation handoff is released.
- **Evidence:** final Gate L2 assessment, gate-result PR/CI, tag annotation, handoff, and
  remote verification transcript.

---

## 6. Execution waves and dependencies

| Wave | Tasks | Exit |
|---|---|---|
| W0 — authority | 000–003 | exact current baseline, immutable erratum, isolated stores |
| W1 — design and PR | 004, 010–017 | draft PR and pre-registration revision 2 protocols |
| W2 — implementation spine | 020–021, 029, 040, 043, 050, 052–056 | paging, role projector, encoder, fixture learner/loader, resolver, sequencer |
| W3 — corpus, holdouts, slice | 022, 026–028, 058 | 115-group corpus, untouched member manifests, end-to-end slice |
| W4 — training/calibration | 023–025 | 200 fit and 40 calibration self-play outcomes |
| W5 — retrieval repair | 030–032, 036 | real width-20 shortlist and D1 diagnostic |
| W6 — learner selection | 041–042, 044–049, 051, 057, 059 | selected artifact, final invariance, REGISTERED then SHADOW; no final access |
| W7 — final evidence | 060–068, 033–035 | two label-all batches, benefit, retrieval, retention, OOD, shadow, D1 result |
| W8 — governed activation | 069–077 | VERIFIED, exact approval, canary, kill switch, restart, rollback, active state |
| W9 — operations | 080–086 | CLI, health, recovery, isolated full matrix |
| W10 — release | 090–095 | Gate L2 result, report, handoff, protected tag and remote verification |

No wave may claim completion with a red P0 dependency. W7 may begin only after the
selected artifact, verified reload, SHADOW transition, and prediction manifests are
immutable. W8 is pass-conditional except for S21D2-075's isolated scratch rollback
contract proof, which remains mandatory on every outcome. Real activation requires a
positive promotion assessment; an operator cannot approve a failed assessment into
eligibility. On a negative path the inapplicable conditional W8 tasks record not-opened
evidence while the scratch proof and W9/W10 still complete.

### 6.1 First vertical slice

Before bulk campaigns, prove one training group and one synthetic sealed-evaluation
group end to end:

1. rights-clean task package and four opaque candidates;
2. pre-outcome features stored before verifier results;
3. role-bound self-play projection, sandbox execution, and independent labels;
4. explicit group-aware dataset manifest and lineage;
5. one k-NN fit and canonical JSON artifact;
6. verified reload through the narrow loader;
7. `label_all` plus isolated scratch-ACTIVE `stop_on_first_accepted` sequencing with
   mandatory verification and a restart-safe receipt;
8. missing/corrupt artifact fallback;
9. restart/replay and scratch backup/restore;
10. the sealed-evaluation fixture refusing access before candidate freeze.

This slice exercises every new authority without spending or exposing the final
holdouts.

### 6.2 Pull-request strategy

Use one D2 implementation PR by default so the selected artifact, runtime, assessment,
and release evidence remain reviewable as one coherent change. A preliminary
pre-registration-only PR is warranted only if independent execution must begin before
the implementation branch can merge that authority. Generated final outcomes must not
be split into an ungoverned artifact-only PR.

---

## 7. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| release baseline | D1 tag object/peel, current main, PR/CI, protection, migration | wrong implementation parent |
| D1 erratum | discrepancy list and immutable original hashes | history silently rewritten |
| store isolation | full development/C3/D1 fingerprints unchanged | evidence contaminated another authority |
| surface revision | primary/secondary decision before final access | problem chosen after results |
| data roles | two durable corpus roles plus exact five-partition campaign membership | evaluation leaked into fitting |
| split integrity | transitive groups disjoint, exact union, split digest in dataset identity | task/template memorisation or stale snapshot reuse |
| holdout authority | separate roots/processes and decision-bound capabilities | fitting or selection could read final bodies |
| candidate construction | four neutral prebuilt artifacts, opaque order, validation before append | recipe leaked the label or partial evidence became durable |
| chronology | features/predictions precede hidden outcomes | post-outcome leakage |
| fitted features | exact artifact matrix passes allowlist | intended schema differs from trained input |
| sample | 200 training, 40 calibration, final 100+100 | underpowered or ineligible surface |
| final access | one artifact selected before A/B open | holdout used for model choice |
| baseline ladder | strongest honest deterministic rung | learned win uses a straw man |
| learner ladder | k-NN first; conditional rungs and stop records | complexity/tuning was speculative |
| model artifact | canonical JSON and exact lineage | active model cannot be reproduced |
| unsafe format | joblib/pickle load impossible | artifact data becomes executable code |
| runtime resolver | durable/config/artifact/model agreement and immutable task snapshot | active claim differs from runtime |
| verifier boundary | label-all evaluation, stop-first runtime, every attempt verified | reordering is decorative or model gained acceptance authority |
| sequence recovery | campaign-stream CAS receipt preserves attempts, stop and intentionally unattempted IDs | restart duplicates work or fabricates outcomes |
| material benefit | 20 changes, threshold, two batches, paired lower bound >0 | useful-learning claim unsupported |
| forgetting | safety zero; domain/aggregate tolerances | prior capability regressed |
| OOD | report <=1%, promotion exactly zero confident errors, fallback | model acts outside known support |
| shadow | deterministic execution unchanged | shadow altered behavior |
| retrieval shortlist | 20 considered, <=10 returned | D1 lever was not actually applied |
| retrieval usefulness | new unseen-task 0.70 recall and 0.50 MRR | D1 condition 15 still open |
| lifecycle verification | focused VERIFIED transition reloads exact eligible payload | generic state advance bypassed evidence |
| approval | exact existing human approval fields, assessment bytes, fresh lineage | component self-authorized or evidence drifted |
| activation integrity | `activate()` verifies payload bytes/media/schema/hash/size in transaction | bundle-time check went stale before activation |
| canary | config-bounded subset, stop-first, independently verified | unbounded or decorative activation |
| kill switch | durable disable and restart fallback | unsafe component cannot be stopped |
| rollback | cause-bound disable receipt and permitted prior receipt restored after restart | failed canary revived or replacement is irreversible |
| runtime intake | valid rows accepted as evaluation-only; unresolved/invalid rows quarantined | evidence lost or active model updated online |
| recovery | exact database/artifact restore | learning state is ephemeral or split-brain |
| CI/release | full matrix, protected merge, exact-head CI, remote tag | baseline is not release-grade |

---

## 8. Quantitative acceptance thresholds

### 8.1 Dataset and separation

- training: at least 50 groups, four candidates per group, and 200 unique outcomes;
- calibration: at least 10 groups and 40 unique outcomes;
- final A: at least 25 groups and 100 unique outcomes;
- final B: at least 25 groups and 100 unique outcomes;
- canary: at least five groups, 20 sealed candidate slots, and every actually attempted
  stop-first outcome retained; any all-candidate labels come from a separately identified
  post-stop evaluation campaign;
- at least 115 groups across the five partitions and at least 85 genuinely new groups
  relative to D1;
- zero observation, task, repository, generator-template, transitive near-duplicate, or
  source-lineage group crossing;
- zero `REAL_GOVERNED_RUN` members in training or calibration;
- zero retries whose purpose is to replace a failed outcome;
- 100% source-rights, manifest-member, artifact, and verifier resolution;
- final counts may increase under pre-fit power analysis but never decrease.

### 8.2 Learned material benefit

- at least 20 task-level final ranking decisions differ from the strongest deterministic
  baseline;
- at least +5 percentage points absolute first-choice verified success, or at least 20%
  relative error reduction;
- paired bootstrap: seed 21041, 2,000 task-group resamples, 95% lower bound above zero;
- learned-minus-baseline direction strictly positive in final A and final B;
- all abstentions use baseline results and stay in the denominator;
- all malformed, timeout, verifier-failed, and no-accepted-candidate tasks stay visible;
- inference latency and artifact size remain within their pre-registered CPU budgets.

### 8.3 Retention, OOD, and authority

- zero accepted-to-rejected transitions in safety, governance, permission, secret, and
  destructive-action cases;
- no retained domain declines by more than 2 absolute percentage points;
- aggregate verified success declines by no more than 1 absolute point;
- every regression in a small retained suite is reviewed case by case;
- OOD false-confident action rate at most 1% in the report and exactly zero for promotion
  under `LearnedPromotionAssessment`;
- shadow changes zero executed decisions;
- every canary/active learned-first candidate passes the same independent verifier before
  acceptance;
- configuration-off, no-active, disabled, abstaining, missing-artifact, corrupt-artifact,
  model-mismatch, and OOD cases all exercise deterministic fallback;
- activation, disable, active pointer, artifact identity, and rollback receipts survive
  restart and test restore;
- zero model/provider approvals and zero unrestricted runtime updates.

### 8.4 Retrieval remediation

- internal GED shortlist considers 20 candidates where the eligible pool permits;
- no more than 10 results are returned;
- at least 50 new unseen-task D2 queries across both final batches;
- at least one bounded arm reaches Recall@5 >=0.70 and MRR@10 >=0.50;
- repeated-ranking agreement 100%;
- per-pair GED timeout at most 250 ms;
- total graph-query p95 at most 2 seconds;
- 64 nodes, 128 edges, depth 32, and exact group exclusions remain enforced;
- zero silent timeouts, silent cutoffs, query drops, or D1-final result blending; all
  reported cutoffs remain in the denominator.

### 8.5 Release and persistence

- migration stays at `0015` unless an approved measured gap justifies `0016`;
- 100% declared/observed artifact hash agreement;
- exact backup/restore counts, hashes, outcome-appropriate component projection, and model
  identity when a candidate exists;
- zero writes to the development, C3, or D1 stores;
- every verification-matrix row has its expected status and evidence;
- all required PR checks and exact-head post-merge `main` CI pass;
- exactly one outcome-appropriate annotated tag is verified remotely:
  `sprint-21-learning-baseline` on success or `sprint-21d2-evidence-baseline` on a negative
  result.

---

## 9. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| inherited real runs enter fit | any C3/D1 observation ID in training/calibration | reject snapshot and invalidate every derived artifact |
| seed variant counted as new group | common template lineage crosses roles | merge transitive group, rebuild manifests before fitting |
| candidate recipe leaks label | label-named recipe/strategy, contradictory-outcome validator, or recipe field in fitted data | replace with neutral prebuilt recipes, validate references before append, reject schema, and rerun from pre-registration |
| patch identity becomes shortcut | IDs/hashes improve calibration | remove identity, invalidate artifact, use permitted pre-final revision only |
| hidden outcome read early | final root capability reaches fitting/selection or result is accessed before candidate freeze | invalidate both final batches and create new isolated untouched evidence |
| split identity omits assignment | same members with different splits resolve to one dataset ID | reject explicit snapshot and bind canonical split digest before identity |
| all four candidates share a label | task is not rankable | retain denominator, report, and apply power rule; do not cherry-pick replacement |
| baseline selected after results | strongest rung changes on final data | invalidate comparison and keep Gate L2 from passing |
| k-NN fails | calibration continuation gate fails | follow declared linear/tree ladder; do not lower threshold |
| transitive sklearn import proposed | package happens to arrive via MiniLM | add reviewed direct optional contract or do not use it |
| later learner passes by tuning | unregistered search/settings | invalidate candidate and return to sealed calibration protocol |
| JSON artifact contains executable form | pickle/joblib/code/import payload | reject artifact and block release |
| artifact loader becomes generic | caller chooses arbitrary class/format | narrow to correction artifact; remove generic path |
| config says active but store disagrees | missing/mismatched durable receipt | fail closed to deterministic order and unhealthy status |
| runner reorders by strategy | dict key or sort loses opaque manifest order | block execution; use prebuilt ordered manifests only |
| restart retries post-stop candidates | campaign receipt absent, conflicting, or ignored | return a blocking repair action, append exactly one CAS receipt, and preserve intentionally unattempted IDs |
| learned score accepts patch | verifier not invoked | block release; restore ordering-only boundary |
| shadow result invents outcome | shadow record carries learned counterfactual result | reject record; join actual verifier evidence separately |
| final A fails | tempting threshold/feature change | do not use B as repair; complete negative assessment |
| batch effects hide failure | aggregate positive, either batch non-positive | fail material-benefit gate |
| bootstrap unit is candidate row | four correlated rows sampled independently | invalidate interval; resample task groups |
| OOD abstains too often | apparent safety with no usable coverage | report coverage; fail pre-registered usefulness requirement |
| width 20 still means 10 | GED gets public truncated result | block benchmark until 20-considered test passes |
| graph p95 exceeds budget | wider shortlist exhausts query budget | graph arm fails; retain vector arm; no budget increase on final |
| final residual suggests FGW | ordering becomes dominant after final | record future hypothesis only; require new backlog/holdout |
| canary fails | safety, benefit, OOD, or budget red | disable immediately; do not restore the real active state; run rollback proof only on scratch |
| failed canary gets a second disable | later kill-switch call overwrites rollback semantics | reuse the failure receipt; never change `rollback_permitted=false` |
| generic transition reaches VERIFIED | caller supplies state without eligible payload recheck | refuse in `advance_component()`; use focused `verify_component()` only |
| promotion payload changes before activation | bundle check and activation observe different bytes | verify exact role/media/schema/hash/size again inside `activate()` and fail atomically |
| rollback has no prior receipt | first activation chain incomplete | prove disable fallback; repair lifecycle evidence before Gate L2 |
| evidence matrix erases data | a truncating row targets evidence root | stop, restore if needed, and rerun only on fresh scratch root |
| development store is targeted | resolved path/fingerprint matches old pair | stop; reconfigure; never remediate it inside D2 |
| database bootstrap partially succeeds | inherited role command aborts | fail preflight visibly; use safe operator runbook or focused repair |
| single reviewer treated as blocker | no second collaborator | retain checks/admin enforcement; do not fabricate review or delay evidence work |
| provider is unavailable | live external route fails | irrelevant to D2; remain deterministic and offline |
| active component does not pass | any Gate L2 condition red | publish null result and successor remediation; Sprint 22A stays blocked |

---

## 10. Stop, rollback, and failure decisions

### 10.1 Before final access

- If surface/data eligibility fails, stop fitting and repair the corpus under a new
  pre-registration revision.
- If every learner rung fails calibration, stop without opening final A/B.
- If artifact rebuild, loader, fallback, invariance, or OOD prechecks fail, stop before
  final access.
- A single allowed feature revision does not permit threshold or final-manifest changes.

### 10.2 After final access

- Any change to the selected candidate invalidates A and B.
- A negative A result is recorded; B still runs only if the pre-registration says it is
  required for the complete independent result, never to select a revision.
- Any aggregate, per-batch, interval, safety, retention, OOD, or retrieval failure keeps
  Gate L2 from passing.
- The next attempt requires new final groups; D2 evidence remains immutable development
  evidence for that successor.

### 10.3 After activation

- Canary failure triggers `disable` and deterministic fallback; rollback must not restore
  a failed canary.
- Missing/corrupt artifact, model/config mismatch, or unhealthy MiniLM triggers fallback
  without an operator round trip.
- Rollback restores only the prior approval-bound receipt chosen by the ledger.
- Valid governed runtime observations enter accepted evaluation-only intake; unresolved,
  invalid, or policy-ineligible observations enter quarantine. Neither path modifies
  active exemplars, coefficients, or thresholds. Under the current contract, accepted
  `REAL_GOVERNED_RUN` rows remain permanently training-ineligible.

---

## 11. Definition of Done

### 11.1 Required for every outcome

Sprint execution is complete only when:

- current main and the protected D1 release are revalidated separately, and the immutable
  D1 erratum plus all source-store fingerprints are recorded;
- revision 2, or the single permitted pre-final revision 3, governs every observation,
  dataset, fitted feature, learner decision, and opened holdout;
- when the design branch opens, the two durable corpus roles, five campaign partitions,
  split-bound dataset identity, role-bound projector, paginated explicit selection,
  outcome-neutral prebuilt candidate manifests, capability-isolated holdouts, 115-group
  corpus, and first vertical slice are evidenced; otherwise S21D2-017 supplies the
  immutable null decision and transitive not-opened chain;
- every P0/P1 task either completes with execution evidence or has a valid transitive
  not-opened record bound to its stop decision; baseline, validation, reporting,
  documentation, and release tasks are never not-opened;
- every executed matrix passes leakage, chronology, duplicate, role, group, artifact,
  security, language, packaging, PostgreSQL, recovery, and deterministic CI checks;
- source stores remain unchanged, D2 backup/restore reproduces the exact outcome-path
  state, and migration remains `0015` unless an approved measured gap required `0016`;
- the report, Gate L2 result, and outcome-specific handoff retain all failures and exact
  evidence/release handles;
- the protected implementation PR and outcome-appropriate gate-result PR merge without
  weakened controls, exact-head `main` CI passes after each, and the remotely verified
  annotated tag is the one permitted for that outcome.

### 11.2 Additional success-path requirements

Gate L2 passes only when:

- at least 200 training and 40 calibration self-play outcomes pass fitted-matrix checks;
- one inert canonical JSON learner artifact is selected under the latest valid pre-final
  registration and reloaded before final access;
- final A and B each contain at least 25 groups and 100 new real-run terminal outcomes;
- the strongest deterministic baseline is frozen, at least 20 decisions change, material
  benefit passes in aggregate and in both batches, and the paired lower bound is positive;
- safety, retention, final OOD, invariance, shadow, retrieval-floor, and D1-remediation
  evidence all pass;
- the component moves through REGISTERED, SHADOW, and VERIFIED in chronological order;
  only the focused verifier transition reaches VERIFIED, while fresh model lineage, D2
  promotion bytes, and exact existing approval fields are checked;
- the bounded campaign sequencer changes real stop-first behavior while every attempt
  remains independently verified and its restart-safe receipt preserves intentionally
  unattempted IDs; `CodingAgentFacade` is not claimed as covered;
- activation re-verifies promotion bytes inside its transaction; canary-config routing,
  cause-bound kill switch, restart, failed-canary rollback refusal, scratch/eligible
  rollback, steady-state config, and final active-state evidence pass;
- `sprint-21-learning-baseline` is annotated once and verified remotely; the post-release
  Gate L2 result passes and only then does Sprint 22A receive an exact handoff.

### 11.3 Valid negative-path completion

A negative Sprint 21D2 is complete when the first failed pre-registered stop condition is
immutable, no forbidden downstream data is opened, every dependent task has a not-opened
record, applicable fixture/local validation and protected CI pass, and the complete
negative evidence is released under `sprint-21d2-evidence-baseline`. Gate L2 remains
`does not pass`, the unresolved D1 conditions remain explicit, Sprint 22A stays blocked,
and the handoff names the successor remediation and new-holdout requirement.

A green implementation PR without either the full success release or a valid protected
negative release is only a checkpoint, not Sprint 21D2 completion.

---

## 12. Expected deliverables

At minimum:

- this backlog and updated D2 handoff, development plan, and sprint allocation;
- D2 baseline, D1 erratum, store-isolation, and inherited-evidence inventories;
- surface audit and pre-registration revision 2;
- on the opened design path, campaign, group, feature, metric, baseline, learner,
  resource, and stop-rule manifests;
- on the opened design path, at least 115 disjoint group catalogues, including at least
  85 genuinely new groups, and at least 200 self-play training/40 calibration outcomes;
- on the opened design path, sealed final A/B and canary manifests;
- on the final-access path, at least 200 final real-run terminal outcomes;
- on the activation path, at least five canary decisions over 20 sealed candidate slots
  and every actually attempted outcome, with any label-all audit separately identified;
- on the opened design path, explicit group-aware dataset builder, durable dataset/
  lineage records, role-bound projector, neutral candidate packages, capability-isolated
  holdouts, two-mode sequencer and receipt, feature encoder, baseline ladder, bounded
  k-NN, JSON contract/loader/resolver, and any authorized later rung; otherwise their
  transitive not-opened records;
- on the candidate path, selected artifact, final resolver/invariance, health, and SHADOW
  integration; otherwise their candidate-stop records;
- on every path, the corrected width-20 shortlist and D1 diagnostic; on the final path,
  the new retrieval holdout, benchmark, residuals, and FGW continuation decision;
  otherwise their final-stop records;
- on the final path, material-benefit, bootstrap, distribution, forgetting, invariance,
  OOD, shadow, and D1-remediation assessments; otherwise an exact D1 unresolved/not-
  assessed record bound to upstream stop hashes;
- scratch rollback evidence on every path; on success, human approval, activation,
  canary, disable, eligible-real rollback, and final active-state evidence; otherwise
  exact not-opened records for inapplicable activation tasks and a remediation decision;
- updated learned/experience CLI, integrity health, operator runbook, and architecture;
- focused credential-free CI and complete isolated verification matrix;
- `docs/sprints/sprint-21/gate-l2-assessment.md`;
- `docs/sprints/sprint-21/sprint-21d2-report.md`;
- a Sprint 22A handoff only on success, otherwise a successor-remediation handoff;
- protected PR, exact-head post-merge CI, outcome-appropriate annotated tag, gate-result
  PR/CI, and remote verification evidence.
