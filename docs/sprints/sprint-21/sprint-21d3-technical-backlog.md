# Sprint 21D3 Technical Backlog

## Invariant Correction Ranking, Independent Retrieval Closure, and Gate L2

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution
- **Revision:** 1
- **Prepared:** 2026-08-03
- **Required predecessor release:** `sprint-21d2-evidence-baseline`, a negative release
- **Required predecessor tag object:**
  `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`
- **Required predecessor release commit:**
  `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5`
- **Required predecessor implementation PR:** `#219`
- **Required predecessor PR-head CI:** `30787401395`, success, 30 of 30 jobs on
  `139a149c1f6ee592cb534dec3c832d2b1c4a4e91`
- **Required predecessor post-merge CI:** `30788129259`, success, 30 of 30 jobs
- **Planning head at preparation:** `origin/main` at
  `9fe03cea3975e81bbae57b870e7bc50d8cc29f49`
- **Gate-close documentation PR:** `#220`
- **Gate-close PR-head CI:** `30789042482`, success, 30 of 30 jobs on
  `e40a67d7c73b08ce1304b55f5707f22f33d5f50e`
- **Planning-head CI:** `30789985887`, success, 30 of 30 jobs on the exact
  planning head
- **Required parent migration head:** `0015`
- **Implementation branch:** `feature/sprint-21d3-invariant-correction-ranking`
- **Planned migration:** none
- **Next available migration:** `0016`, unallocated unless a measured durable-authority
  gap cannot be represented by the existing learned ledgers, Event Store, and Artifact Store
- **Success-path baseline tag:** `sprint-21-learning-baseline`
- **Negative-path evidence tag:** `sprint-21d3-evidence-baseline`
- **Stage gates:** Gate D1 conditions 6, 7, and 15; Gate L2
- **Execution profile:** local, CPU-first, single maintainer, credential-free normal CI,
  no live-provider, network, credential, or GPU dependency
- **Repository language:** English only

---

## 0. Authority and execution contract

This backlog is the implementation authority for Sprint 21D3. It refines:

- [Sprint 21D2 report](sprint-21d2-report.md);
- [Sprint 21D3 handoff](sprint-21d3-handoff.md);
- [Gate L2 assessment](gate-l2-assessment.md), which remains the immutable D2
  assessment rather than the D3 result;
- the annotated `sprint-21d2-evidence-baseline` release;
- PR `#220` and its exact-head planning baseline;
- [Sprint 22 development plan](../sprint-22/development-plan.md);
- [execution sprint allocation](../sprint-22/execution-sprint-allocation.md).

D3 is a bounded remediation experiment. Machine learning remains mandatory for the
programme, but neither the D2 k-NN configuration nor any D3 candidate is entitled to
activation. The sprint must preserve the D2 negative result, correct the measurement
contracts that D2 exposed, change the correction feature contract once under a new
pre-registration, and evaluate that change on fresh calibration evidence and untouched final
evidence. Retrieval is an independent blocking branch because D1 condition 15 and Gate L2
condition 24 cannot be inferred from correction-ranking success.

If implementation evidence contradicts this backlog, preserve evaluation separation,
independent-verifier authority, deterministic fallback, exact artifact lineage, and reversible
activation. Record the conflict and the smallest resolution before any affected holdout is
opened. Do not silently reinterpret a denominator, replace a sealed member, or tune against a
failed holdout.

### 0.1 Release-grade meaning of done

D3 is not complete when an encoder is invariant on a unit test, k-NN calibrates, retrieval
improves on D1 development data, or a PR turns green. Section 11 defines two valid outcomes.
Every outcome requires:

1. revalidation of the D2 tag, current `origin/main`, all four implementation/gate-close
   PR-head and post-merge exact-head CI runs, branch
   protection, migration head, collaborator state, and four predecessor Artifact Store pairs;
2. a non-destructive D2 evidence-reconciliation record that fixes no historical bytes but
   establishes the authoritative D3 denominators and retrieval numbers;
3. pre-registration revision 3 published before any new channel measurement, new feature
   encoding, fresh campaign, or retrieval score;
4. a channel-isolation diagnostic using D2 data for diagnosis only and an explicitly bounded
   response that cannot become an open-ended feature search;
5. a fresh `SELF_PLAY` campaign whose revision-3 features are sealed before execution and
   whose explicit snapshots contain zero `REAL_GOVERNED_RUN` rows;
6. a fresh, group-disjoint calibration and metamorphic/OOD selection set that D2 never scored;
7. independently sealed correction final A, final B, canary, and retrieval holdouts, with
   correction and retrieval membership mutually disjoint;
8. exactly one revised k-NN candidate or a hash-bound null selected before final correction
   outcomes become accessible;
9. one pre-registered retrieval candidate plus the unchanged comparators evaluated once on at
   least 50 new unseen-task queries;
10. either every fixed Gate L2 condition passing followed by the existing governed lifecycle,
    or the first failed pre-registered stop condition followed by complete `not_opened`
    evidence for dependent work;
11. isolated PostgreSQL and Artifact Store recovery evidence, complete local validation,
    protected PR merge, successful exact-head post-merge `main` CI, and one annotated remotely
    verified outcome-specific tag;
12. a D3 report, a versioned D3 Gate L2 assessment, and an outcome-specific handoff.

Final PR, merge, CI, and tag identities belong in the annotated tag or external release
evidence rather than as self-referential claims inside the implementation commit.

### 0.2 Efficiency-first implementation rule

Use, in order:

1. the released D2 correction contracts, feature sealing, explicit snapshot builder,
   campaign sequencer, verifier, k-NN, ladder, canonical JSON artifact, runtime resolver,
   lifecycle ledgers, graph retrieval, operations scripts, and release scripts;
2. the Python standard library and already locked dependencies;
3. one production identifier-normalisation authority, tested with an independently released
   perturbation generator and hard-coded pairs so the encoder cannot act as its own oracle;
4. one fixed equal-weight reciprocal-rank-fusion retrieval arm, without a weight sweep;
5. a successor sprint only after a new D3 residual proves a need for a different learner or
   retrieval family.

D3 must not add by default:

- migration `0016`, a new database engine/service/authority, graph database, vector database,
  event authority, or model server. A new isolated logical database in the existing PostgreSQL
  authority remains required for D3 evidence;
- a generic feature platform, learner factory, hyperparameter service, or second activation
  state machine;
- a new embedding model, live LLM, GNN, FGW implementation, GPU path, or network dependency;
- logistic regression, SGD, a tree, or another parametric rung merely because D2 failed OOD;
- a pickle, joblib, arbitrary-object, or executable-artifact loader;
- automatic acceptance of a correction based on a learned score;
- deletion or deduplication of D2's duplicate but real observations or seals.

### 0.3 Evidence-role boundary

| Evidence | Permitted D3 use | Prohibited use |
|---|---|---|
| D2 training, calibration, and failed calibration OOD | frozen channel diagnosis, implementation regression, historical development comparison | D3 candidate selection, threshold choice, final claim |
| 214 inherited C3/D1 `REAL_GOVERNED_RUN` outcomes | retained evaluation and historical diagnosis | fitting, calibration, exemplars, threshold choice |
| D3 `SELF_PLAY` training campaign | fitting after rights, chronology, and leakage checks | final benefit claim |
| fresh D3 `SELF_PLAY` calibration and metamorphic set | k/threshold selection before final access | fitting exemplars, refit after selection or final access |
| correction final A `REAL_GOVERNED_RUN` | first independent final comparison | training, calibration, feature or threshold revision |
| correction final B `REAL_GOVERNED_RUN` | independent confirmation | training, calibration, feature or threshold revision |
| new unseen-task retrieval holdout | one final comparison of frozen retrieval arms | correction selection, retrieval tuning, weight selection |
| canary `REAL_GOVERNED_RUN` | bounded post-approval runtime proof | fitting or replacement of final evidence |

D2's 480 stored observations represent 240 pieces of intended training/calibration work under
two real executions. A D3 snapshot must name every included observation and feature record.
Queries such as "all observations on this surface" or "latest seal for this partition" are
invalid evidence selection.

If S21D3-004 requires a replacement final/canary role, its new bodies have one narrow exception:
an isolated corpus-authoring validator may parse and execute them before deterministic role
allocation. Those throwaway results remain outside every learned/evaluation store and metric,
the authoring capability is revoked at S21D3-032, and the sealed replacement bodies are then
inaccessible to fitting, calibration, model selection, and ordinary operators until S21D3-059.
This exception does not reopen or resolve the inherited D2 protected bodies.

### 0.4 Negative-result and no-retuning rule

Publish a negative D3 result and keep Gate L2 closed when the first applicable condition below
occurs:

- the revision-3 diagnostic finds structural-channel drift outside the pre-registered response;
- canonical correction features do not satisfy their exact rename invariants;
- no revised k-NN setting clears fresh calibration, non-silence, and metamorphic/OOD rules;
- no retrieval arm clears both fixed usefulness floors on the new retrieval holdout;
- final benefit, paired interval, independent-batch direction, safety, retention, promotion
  OOD, shadow, budget, artifact, approval, canary, restart, disable, or rollback evidence fails;
- an authority, chronology, leakage, overlap, body-access, hash, or recovery invariant fails.

After the fresh calibration/OOD set is resolved, D3 may not change the feature contract,
perturbations, grid, eligibility rule, baseline, or calibration membership. After candidate
selection, no fit, refit, threshold change, artifact replacement, or final-manifest change is
allowed. Final B confirms final A; it is not a repair set. The retrieval holdout is read once
after every arm and resource limit is hash-bound.

A negative release uses `sprint-21d3-evidence-baseline`; it creates no success tag and does not
unblock Sprint 22A. Dependent items must have a typed `not_opened` record bound to the first
failed decision, not merely a sentence in the report.

---

## 1. Verified starting state and reconciliations

### 1.1 Exact release state at preparation

| Item | Verified value |
|---|---|
| Current planning head | `origin/main` at `9fe03cea3975e81bbae57b870e7bc50d8cc29f49` |
| Planning-head source | gate-close PR `#220`, squash-merged |
| Planning-head CI | `30789985887`, 30 of 30 successful on the exact head |
| D2 tag | annotated `sprint-21d2-evidence-baseline`; object `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29` |
| D2 peeled commit | `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` |
| D2 implementation | PR `#219`; post-merge CI `30788129259`, 30 of 30 successful |
| Migration | `0015` head; `0016` unallocated |
| Protection | 27 strict required contexts, `enforce_admins`, conversation resolution, no force-push or branch deletion |
| Reviewer state | one collaborator; approving-review requirement unset without fabricating a reviewer |
| Learned component state | 0 components, 0 approvals, 0 activations for `experience.correction_ranking` |
| Gate state | Gate D1 conditions 6, 7, and 15 open; Gate L2 does not pass; Sprint 22A blocked |

The D3 implementation branch must be created from a freshly fetched and revalidated
`origin/main`, not from the peeled D2 tag and not from a local branch whose tree merely happens
to match it.

### 1.2 Immutable predecessor Artifact Store pairs

| Pair | Files | Fingerprint | D3 access |
|---|---:|---|---|
| development `artifacts` | 5 | `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf` | read-only diagnostic only |
| C3 `artifacts-s21c3` | 8,503 | `7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593` | read-only |
| D1 `artifacts-s21d1` | 83 | `f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f` | read-only |
| D2 `artifacts-s21d2` | 1,511 | `39417f1a03f6824cfe6f9c4b7e6bd5a3cd34da8329fb95cff0a35595899438aa` | read-only predecessor evidence |

D3 writes only to a new database and a new Artifact Store root. Every destructive operations
case uses disposable copies. The inconsistent five-file development pair remains untouched
unless a separate operator-authorised remediation explicitly changes that scope.

### 1.3 D2 correction result

- 125 sealed repository groups and 500 candidate slots exist.
- D2 fitted 200 `SELF_PLAY` observations over 50 groups and calibrated on 40 separate
  `SELF_PLAY` observations over 10 groups.
- Zero `REAL_GOVERNED_RUN` observations entered either snapshot.
- The strongest deterministic calibration baseline was 0.3 first-choice acceptance.
- Bounded k-NN reached 0.9 at 0.9 clean calibration coverage, then produced confident wrong
  answers under semantics-preserving transformation.
- The selection record `274a7a932ce110d12892f3dab102f10308ad556c563483d414979cbc69950536`
  is a null and does not authorise final access.
- The continuation record `4e5a690f16b64c22239d9e95f841a1350eeb1ad914694dd496488214a289f321`
  is `fail_and_stop` with failure kind `ood_deficient`.
- No candidate, artifact, final outcome, component revision, approval, or activation exists.

### 1.4 Mandatory D2 denominator correction

D2's evidence reports its ten-group calibration OOD probe as "40 decisions" by summing the
four candidate slots in each group. The code, however, calls `rank()` once per group and then
increments `answered`, `abstained`, and `confident_errors` once for that group-level ranking.
The programme contract names the primary unit as a task-group ranking.

D3 therefore freezes these terms before any experiment:

- **candidate outcome:** one independently verified accepted/rejected label for one candidate;
- **ranking decision:** one call that orders the four candidates for one task group, or
  abstains and invokes the deterministic order;
- **metamorphic case:** one semantics-preserving transformation of one task group, producing
  exactly one ranking decision and four candidate outcomes;
- **changed decision:** a group-level first action that differs from the declared deterministic
  baseline; four candidate labels never count as four decisions.

Under that contract D2 measured ten calibration OOD ranking decisions, not forty. This does
not rehabilitate D2; it makes the shortfall stricter. D3 Gate L2 condition 20 requires at least
100 actual ranking decisions over at least ten groups. Candidate-outcome counts must always be
reported separately.

### 1.5 Mandatory D2 retrieval reconciliation

The machine-readable D2 diagnostic and its narrative disagree. The canonical computed fields
in `sprint-21d2-d1-retrieval-diagnostic.json` are:

| Arm | Recall@5 | MRR@10 | nDCG@10 | Timeouts |
|---|---:|---:|---:|---:|
| width-20 bounded graph | 0.5875 | 0.3634 | 0.2333 | 0 |
| MiniLM vector | 0.5375 | 0.4392 | 0.3740 | 0 |
| lexical | 0.5250 | 0.4145 | 0.3327 | 0 |

The D2 report prints graph MRR/nDCG as 0.3628/0.2327 and MiniLM recall as 0.6750; the same
diagnostic's free-text finding repeats 0.3628/0.2327 while its computed fields contain
0.3634/0.2333. D3 must publish a non-destructive reconciliation record that identifies the
calculation source, replays the frozen 80-query measurement, and establishes one authoritative
development baseline. It must not rewrite the D2 tag or describe D1/D2 development evidence as
holdout closure.

### 1.6 Untouched correction-holdout inventory

The sealed D2 catalogues resolve the count the handoff left open:

| Role | Groups | Candidate slots | Outcome state |
|---|---:|---:|---|
| final A | 30 | 120 | unexecuted |
| final B | 30 | 120 | unexecuted |
| canary | 5 | 20 | unexecuted |

All 65 groups are pairwise disjoint. D3 may reuse the exact manifests only if a day-one audit
proves unchanged content hashes, zero authoritative outcomes, zero prediction access, fitting
capability isolation, no D2 selection authority, and valid revision-3 child binding. If any
member fails, replace the whole affected role before fitting; never cherry-pick passing members
or reduce final A/B from 30 groups to the 25-group gate floor.

The D2 promotion submanifest is bound to all 60 final groups but its stated 240 "future
decisions" uses the candidate-slot denominator. It provides at most 60 group rankings for one
combined case. D3 must seal additional transformation cases before candidate selection so at
least 100 actual ranking decisions can be executed after final access.

### 1.7 Reusable released authority

D3 reuses without reimplementation:

- D2's oracle-free four-candidate corpus recipes and near-clone checks;
- role-bound observation projection and explicit-member snapshots;
- pre-outcome feature sealing, campaign bundle persistence, resume receipts, and chronology
  refusal;
- fitted-matrix allowlist/denylist scans and seeded leakage violations;
- deterministic baseline ladder and bounded pure-Python k-NN;
- canonical JSON artifact, narrow loader, runtime fallback reasons, and candidate sequencer;
- learned evidence, promotion, activation, disable, restoration, and rollback ledgers;
- Experience Graph projection, lexical/vector/bounded-GED retrieval, resource limits, and
  advisory Context Builder boundary;
- D2 backup, restart, restore, corruption, isolation, and verification-matrix scripts.

The expected code change is a focused revision, not a second learning subsystem.

---

## 2. Sprint goal and fixed gate contract

### 2.1 Goal

Determine whether a pre-registered, identifier-invariant correction feature encoding lets the
existing bounded k-NN retain useful ranking signal on fresh data, while independently testing
one minimal retrieval fusion on a new unseen-task holdout. On a complete pass, promote exactly
one correction-ranking artifact through the released governed lifecycle. On any stop, publish
a complete negative release that makes the next engineering decision from new evidence.

### 2.2 Fixed Gate L2 conditions D3 must evidence

D3 does not inherit a blanket pass from D2. Stable infrastructure is reusable, but every
condition tied to the revised feature matrix, candidate artifact, final outcomes, retrieval
holdout, or lifecycle must be remeasured.

| Condition | Required D3 evidence |
|---:|---|
| 1-3 | current baseline, immutable predecessor, and D2 reconciliation evidence |
| 4 | revision-3 pre-registration before any D3 candidate/development/holdout measurement or holdout access; immutable predecessor reconciliation replay is baseline-only |
| 5 | verifier remains label and acceptance authority; prediction only orders attempts |
| 6 | revision-3 fitted matrix contains no forbidden, identity, outcome, or answer field |
| 7 | transitive task/repository/template/clone/source groups do not cross any D3 role |
| 8 | at least 200 fitting observations/50 groups and 40 calibration observations/10 groups; D3 targets 200/50 and 80/20 |
| 9 | zero `REAL_GOVERNED_RUN` observations in fitting and calibration |
| 10 | final A and B each contain 120 new verifier-backed outcomes over 30 groups when D2 seals are reusable |
| 11 | final manifests inaccessible to fitting and one artifact selected before final access |
| 12 | strongest deterministic baseline and every attempted rung recorded; revised k-NN first |
| 13 | at least 20 final group decisions differ from the strongest baseline |
| 14 | at least 5 percentage points absolute gain or at least 20% relative error reduction |
| 15 | paired group bootstrap, seed 21041, 2,000 resamples, 95% lower bound above zero |
| 16 | learned-minus-baseline direction positive in both final A and final B |
| 17 | exact denominators for coverage, abstention, confidence, attempts, latency, calls, failures, and cost |
| 18 | zero safety/governance/permission/secret/destructive accepted-to-rejected regressions |
| 19 | no retained domain loss above 2 points and aggregate loss at most 1 point |
| 20 | at least 100 actual pre-registered metamorphic/OOD ranking decisions over at least 10 groups, report false-confident rate at most 1%, promotion exactly zero confident errors; operational corruption/runtime cases are reported separately and do not inflate this denominator |
| 21 | shadow changes zero executed decisions and outcome linkage uses only verifier evidence |
| 22 | selected artifact is canonical inert JSON with complete lineage and unsafe formats remain unloadable |
| 23 | every artifact/configuration/lifecycle failure immediately uses the deterministic fallback with a structured reason |
| 24 | at least one bounded arm reaches Recall@5 at least 0.70 and MRR@10 at least 0.50 on at least 50 new unseen-task queries within the fixed resource budget |
| 25 | canary manifest hash-bound, verifier mandatory, kill switch immediate |
| 26 | activation, loading, disable, restoration, and rollback survive restart |
| 27 | human approval uses exactly the existing fields: `approval_id`, `component_id`, `component_revision`, `surface`, `promotion_assessment_hash`, `artifact_lineage_id`, `approved`, `approver`, `approver_kind`, `reason`, and `approved_at`; canary/steady configuration hashes and their transition condition are dependencies of the approved assessment, not invented approval fields; no self-approval |
| 28 | isolated replay, backup/restore, corruption, artifact, packaging, schema, security, language, focused CI, and complete local matrix |
| 29 | protected merge, post-merge exact-head CI, outcome-specific report/assessment/handoff, annotated tag, and remote verification |

Gate D1 condition 6 closes when at least 200 unique, eligible, verifier-backed primary-surface
outcomes exist. Condition 7 closes when at least 20 primary-surface examples can change the
advisory action under the frozen learned policy. Neither condition requires activation, so its
valid evidence remains closed if a later retrieval or canary gate fails. Condition 15 closes
independently only if the new retrieval holdout reaches both floors. A correction-ranking pass
cannot waive retrieval failure, and retrieval success cannot activate a failed ranker.

### 2.3 Added D3 non-silence and invariance rules

Condition 20 is a safety ceiling, not a permission to pass by abstaining everywhere. D3 uses
pre-registered semantics-preserving metamorphic/OOD equivalence cases: two independent identifier
renames, two independent contract-preserving issue rewrites, and two declared combinations. If
the clean decision is covered, each transformed case must preserve the first action and must not
lose coverage. Malformed inputs, corrupt artifacts, missing configuration, oversized payloads,
permission violations, and other operational adversarial cases remain mandatory runtime and
corruption tests, but they are not metamorphic ranking decisions and cannot inflate condition
20's denominator.

Fresh calibration selection requires all of:

- clean first-choice rate above the strongest deterministic baseline;
- clean group coverage at least 0.80;
- equivalence-case coverage at least 0.80 and no lower than clean coverage by more than 0.05;
- exactly zero confident equivalence/OOD errors;
- 100% action preservation on covered clean/transformed pairs;
- at least one changed clean decision, so identity with the fallback is not called useful.

These stricter D3 rules supplement rather than relax the fixed gate. Promotion still reports
all abstentions and rates over all pre-registered decisions.

---

## 3. Scope, experimental revisions, and stop rules

### 3.1 In scope

- exact baseline, store, seal, denominator, holdout, and retrieval reconciliation;
- revision-3 pre-registration with one bounded diagnostic decision tree;
- per-perturbation and per-feature-channel invariance attribution on D2 development data;
- `correction-ranking-v2`, embedding alpha-normalised candidate source rather than a raw
  unified diff, and excluding both unstable requirement-to-delta cosine and diff-shape fields;
- fresh pre-outcome feature seals and a new self-play campaign;
- 20 new calibration groups, six nominal always-applicable cases per eligible group, and at
  least 100 fresh metamorphic selection decisions after validation;
- correction final A/B and canary reuse only after the untouched-holdout audit;
- at least 100 correctly counted final metamorphic/OOD ranking decisions;
- one fixed equal-weight reciprocal-rank-fusion arm over lexical and MiniLM vector ranks;
- a distinct, newly sealed retrieval holdout with at least 50 qualifying queries;
- revised matrix, calibration, artifact, runtime, final, retention, shadow, promotion,
  activation, recovery, release, and gate evidence;
- a complete typed negative path at every conditional boundary.

### 3.2 Explicitly out of scope

- tuning to D2's failed OOD examples or treating them as D3 selection evidence;
- changing Gate L2 or D1 thresholds, bootstrap seed, resource limits, or reviewer controls;
- a universal correction model, cross-surface learner, or `CodingAgentFacade` coverage claim;
- `REAL_GOVERNED_RUN` fitting, online learning, autonomous weight updates, or verifier bypass;
- a parametric learner, new embedding model, fine-tuning, GNN, FGW, GPU, or live provider;
- repair of the inconsistent development Artifact Store pair;
- repair of `postgres_bootstrap_roles.sh` beyond the existing provisioning route;
- Sprint 22A domain expansion or any claim that Gate L2 is passed before the final release gate;
- deleting D2 observations, seals, failed selections, or historical narrative discrepancies.

### 3.3 Revision-3 diagnostic decision tree

Revision 3 must publish this response before reading any per-channel number:

1. Reproduce D2's clean and combined-perturbation result exactly enough to validate the
   diagnostic harness. If the reproduction cannot resolve the same members, labels, settings,
   and selection hash, stop with `diagnostic_not_reproducible`.
2. Apply identifier rename, issue rewrite, baseline statement reorder, and visible-test literal
   substitution separately. Record raw inputs, encoded values, embedding cosine drift, nearest
   neighbours, ranking, confidence, and abstention.
3. If rename moves any non-lexical structural field, or the test-only perturbation reaches a
   fitted field, stop with `feature_boundary_wrong`.
4. If the moved channels are the raw candidate-delta embedding, its derived
   query-to-candidate cosine, or baseline-relative diff-shape counts, proceed with the already
   declared `correction-ranking-v2`: embed alpha-normalised candidate source and remove the
   requirement/cosine and diff-shape channels.
5. If another unanticipated fitted channel independently causes a confident action reversal,
   stop with `unregistered_feature_response`. Do not invent a second encoder inside D3.

The diagnostic decides whether the pre-registered intervention is applicable; it does not
choose between feature variants, tune a tolerance, or provide candidate-selection evidence.

### 3.4 Learner continuation rule

D3 evaluates revised bounded k-NN with the already declared grid shape and fixed embedding
weight first. No parametric rung opens inside D3. A fresh residual may recommend a specific D4
rung only when:

- the revision-3 invariance and fresh OOD rules pass;
- the revised matrix passes every leakage and chronology check;
- no k-NN setting provides material calibration lift for a reason classified as capacity or
  boundary shape rather than invariance, data integrity, or silence;
- the recommendation is recorded without opening either correction final batch.

This prevents D2's OOD failure from becoming authority to add a dependency and keeps D3 to one
scientific intervention.

### 3.5 Holdout and retuning stop line

- D2 development diagnosis may run only after revision 3 is hash-bound.
- Fresh calibration/OOD data may be resolved only after the feature contract, grid, coverage
  rules, transformation recipes, and exact member/case submanifests are frozen.
- The selected candidate, fitted artifact bytes, threshold, dataset hash, split hash, feature
  hash, code revision, and final prediction-seal procedure must be fixed before final access.
- Retrieval arms, fusion constant, ties, resources, queries, judgements, and metric code must
  be fixed before the retrieval holdout is resolved.
- Any final or retrieval failure closes the associated branch. No new revision, arm, or member
  replacement is permitted in D3.

---

## 4. Minimal D3 architecture

### 4.1 Correction feature contract revision

`correction-ranking-v2` replaces the unstable baseline-relative text boundary with one exact
Python 3.12 AST byte grammar:

1. parse candidate source with the standard-library Python 3.12 AST and symbol-table rules;
2. assign module, class, function, lambda, and comprehension scopes deterministic AST-preorder
   indices; within each scope inventory every source-local binding in lexical first-binding order
   and consistently replace its definitions and resolved uses, including function/class names,
   parameters, locals, matching local-call keyword names, and `global`/`nonlocal` references, with
   reserved `__cogos_sNNNN_bNNNN` placeholders. Imports and aliases, attributes, builtins,
   magic names, and string literals remain unchanged; reflection-unsafe rename targets are
   ineligible for metamorphic generation, and an existing reserved prefix or ambiguous binding
   fails closed;
3. serialize exactly
   `b"cogos-correction-source-ast-v2\npython-grammar=3.12\n" +
   ast.dump(normalized_tree, annotate_fields=True, include_attributes=False).encode("utf-8")`.
   Comments, locations, formatting, and input mapping order are absent. Embed these bytes with
   the same frozen local MiniLM identity and revision, and bind the grammar, normalizer version,
   and implementation tree hash;
4. retain candidate-source AST node count, statement-graph node/edge/path counts, missing-value
   indicators, and declared verifier-capability count;
5. remove the four raw unified-diff shape counts, `task_requirement_embedding`, and
   `query_to_candidate_cosine` from the fitted v2 allowlist and vector. A baseline-only reorder
   and an issue paraphrase must have no path into the representation;
6. expose the 384 embedding dimensions under a semantic channel identity to fitted-matrix
   validation. The allowlist, finite/range scans, duplicate-label scan, and seeded
   label-separation violation must inspect them rather than only the scalar names;
7. keep identity, recipe, verifier, outcome, hidden-control, hash, and post-outcome fields on
   the denylist;
8. store the canonicalisation version, normalisation parameters, embedding identity, feature
   member hashes, and code revision in the artifact.

Exact property contracts:

- an independently generated coherent rename of an eligible local binding produces
  byte-identical canonical candidate source,
  feature numbers, feature vector, neighbour ordering, ranking, and confidence;
- issue rewriting, baseline-only independent-statement reordering, and test-only literal
  substitution produce byte-identical candidate features because none is a v2 input;
- every seeded semantic operator or branch-condition mutation produces a different canonical
  representation and hash; seeded tests also require vector movement, without claiming that an
  embedding is mathematically injective;
- unsupported syntax, inconsistent renaming, parse failure, or mapping collision fails closed;
- test-only content never reaches a fitted feature;
- encoding remains deterministic across process restart and input mapping order.

### 4.2 Fresh campaign and data roles

| Role | D3 target | Provenance | Purpose |
|---|---:|---|---|
| fitting | 50 groups / 200 outcomes | `SELF_PLAY` | fit v2 k-NN after v2 feature seals |
| calibration | 20 new groups / 80 outcomes | `SELF_PLAY` | select k/threshold on unseen clean groups |
| calibration metamorphic | 120 nominal cases over 20 groups; at least 100 valid group decisions and 400 executed candidate outcomes | throwaway verifier-backed precheck, never fitted | selection safety and invariance |
| final A | exact reusable seal: 30 groups / 120 outcomes, or fully replaced role | `REAL_GOVERNED_RUN` | first final comparison |
| final B | exact reusable seal: 30 groups / 120 outcomes, or fully replaced role | `REAL_GOVERNED_RUN` | independent confirmation |
| promotion metamorphic/OOD | 120 nominal cases over 20 manifest-ordered eligible final groups; at least 100 valid group decisions | verifier-backed evaluation only | Gate condition 20 |
| canary | 5 groups / 20 presealed slots | `REAL_GOVERNED_RUN` | post-approval canary |
| retrieval | overproduce at least 60 new disjoint task groups until at least 50 queries qualify | evaluation only | D1 condition 15 / Gate condition 24 |

The 50 fitting task groups may reuse the rights-cleared D2 training task packages, but they must
run as a new campaign with new run identities after v2 feature sealing. Existing D2 outcomes
cannot be re-encoded under a later seal and called pre-outcome evidence. The 20 calibration
groups must be genuinely new and group/clone/source-disjoint from every D2 calibration, final,
canary, and D3 retrieval group.

### 4.3 Metamorphic decision matrix

Each eligible calibration or promotion group receives six separately identifiable cases, not
one opaque combined perturbation:

1. identifier-rename variant A;
2. identifier-rename variant B;
3. contract-preserving issue-rewrite variant A;
4. contract-preserving issue-rewrite variant B;
5. rename A plus issue rewrite A;
6. rename B plus issue rewrite B.

The task-package eligibility contract requires a safely renameable local binding, making all six
nominal cases applicable. The two rename maps and two issue rewrites come from a released
perturbation generator independent of the production normalizer, with hard-coded golden pairs as
a second oracle. Independent-statement reorder and test-only equivalent-literal substitution are
optional boundary probes: they are reported with explicit applicability but never contribute to
the 100-decision condition-20 floor.

Every valid case creates one group-ranking decision and four independently executed candidate
outcomes. Twenty calibration groups and twenty manifest-ordered eligible promotion groups create
120 nominal cases per stage, leaving a twenty-case reserve while still requiring at least 100
valid decisions. Failure to leave 100 valid cases is a stop, not authority to substitute groups
after scores are read. Revision 3 freezes transformation recipes, case-ID derivation, seeds,
eligibility/applicability rules, label authority, decision semantics, and counting code; exact
member/case hashes are sealed after task authoring and before any candidate score or verifier run.

### 4.4 Corrected OOD metrics

For every setting and every final artifact report:

- total task groups;
- total metamorphic cases attempted, applicable, and not applicable;
- ranking decisions, candidate outcomes, answered decisions, abstained decisions, and coverage;
- clean/transformed paired action agreement;
- confidence drift and action reversals by perturbation channel;
- confident wrong first actions and false-confident rate over all ranking decisions;
- verifier failures and label changes separately from ranker errors;
- no rate whose numerator and denominator use different units.

The selection contract rejects zero or near-zero coverage according to Section 2.3. An
abstention executes the deterministic order and remains in the decision denominator.

### 4.5 Bounded correction ranker and artifact

D3 retains:

- k in `{3, 5, 7}`;
- similarity floor in `{0.30, 0.50}`;
- agreement floor in `{0.60, 0.80}`;
- confidence floor in `{0.55, 0.70}`;
- embedding weight fixed at `0.7`;
- strongest honest deterministic baseline derived by contract;
- baseline order as tie-break and fallback;
- canonical JSON artifacts only;
- independent verifier on every attempted correction.

The artifact schema increments for `correction-ranking-v2` and refuses v1/v2 confusion. A v1
artifact cannot load under a v2 revision; wrong encoder, normaliser, MiniLM tree, dataset,
member list, setting, code, surface, descriptor, artifact hash, lifecycle state, or activation
configuration immediately returns a structured baseline fallback.

### 4.6 Independent retrieval remediation

D3 adds one minimal candidate arm:

- compute released lexical and MiniLM vector scores over the complete same eligible pool through
  reusable untruncated scorers;
- rank only strictly positive lexical scores; zero-score lexical documents are absent from that
  arm so pair-ID ordering cannot become artificial evidence. MiniLM ranks the complete eligible
  pool;
- combine their ranks with equal-weight reciprocal-rank fusion,
  `score(d) = 1/(60 + rank_lexical(d)) + 1/(60 + rank_vector(d))`;
- missing membership in an arm contributes zero;
- ties use the existing stable pair-id tie-break;
- fuse the two full-pool rank lists, then apply the output limit once and publish at most ten
  results;
- do not include bounded GED in the fusion, tune weights, sweep the fusion constant, or inspect
  the new holdout while implementing it.

The comparators remain no-memory, exact signature, lexical, MiniLM vector, and width-20
bounded GED. Resource policy revision 2 remains: at most 64 nodes, 128 edges, path depth 32,
20-vector shortlist, 90 ms per GED comparison, two seconds per query, and ten returned results.
All arms run once on the new holdout. A D1 development rerun may validate implementation but
cannot select weights or close the gate.

### 4.7 Lifecycle sequence

The positive path reuses the released sequence without shortcuts:

```text
pre-registration revision 3
  -> feature-v2 seals
  -> fresh SELF_PLAY fitting and calibration outcomes
  -> explicit snapshots and matrix validation
  -> fresh calibration metamorphic/OOD selection
  -> one candidate selection and canonical artifact
  -> REGISTERED -> SHADOW
  -> final A/B prediction seals, outcomes, benefit, retention, promotion OOD
  -> independent retrieval holdout result
  -> promotion assessment -> VERIFIED
  -> exact human approval
  -> canary-only activation
  -> kill switch, restart, disable, restoration, permitted rollback
  -> bounded steady state
```

Every arrow has a hash-bound receipt. A failure replaces every downstream arrow with a
`not_opened` record bound to the first stop hash.

### 4.8 Expected focused code boundary

Expected modifications are bounded primarily to:

- `src/cognitive_os/learning/correction_protocol.py`;
- `src/cognitive_os/learning/correction_features.py`;
- one small production identifier-normalisation module if extraction prevents duplicate logic;
- `src/cognitive_os/learning/calibration_ood.py`;
- `src/cognitive_os/learning/correction_ranking.py` for v2 vector identity and named embedding
  channels;
- `src/cognitive_os/learning/correction_matrix.py` so the fitted embedding dimensions are
  included in the actual leakage and validity scans;
- `src/cognitive_os/learning/knn_calibration.py` for unit-correct denominators and coverage rules;
- `src/cognitive_os/learning/correction_artifact.py` for v2 identity refusal;
- `src/cognitive_os/application/services/learned_datasets.py` for schema- and
  selection-sensitive explicit dataset identity;
- `src/cognitive_os/application/services/reality_campaign.py` for receipt-aware resume binding;
- `src/cognitive_os/application/services/learned_evidence.py` for focused verification and
  activation-time artifact revalidation;
- `src/cognitive_os/domain/learned.py` (or one dedicated domain module) and
  `src/cognitive_os/learning/promotion.py` for the versioned D3 promotion payload and evaluator;
- `src/cognitive_os/experience/graph_retrieval.py` for reciprocal-rank fusion;
- narrow D3 campaign, selection, evaluation, operations, and verification scripts;
- focused tests under `tests/cognitive_os/learning`, `tests/cognitive_os/experience`, and
  operations/integration suites;
- D3 evidence, operations, architecture, report, assessment, and handoff documents.

No database migration is expected because all new payloads fit existing append-only evidence
and artifact authorities.

---

## 5. Detailed work items

Every item below is independently reviewable. "Evidence" means a committed, canonical,
machine-readable artifact unless the item explicitly names a test or document. Conditional
items produce a typed `not_opened` result when their dependency closes. S21D3-075 is the explicit
exception: receipt-chain rollback/refusal is an unconditional substrate gate and uses the minimal
isolated lifecycle fixture when no real D3 activation exists.

## EPIC S21D3-E00 — Baseline, reconciliation, and isolation

### S21D3-000 — Revalidate the exact D3 starting point

- **Deliverable:** `evidence/sprint-21d3-baseline.json` generated from fresh local and remote
  reads before implementation.
- **Acceptance:** records local/remote branch heads; D2 tag object and peeled commit; PRs `#219`
  and `#220`; all four PR-head/post-merge CI runs; 27 required contexts; `enforce_admins`; collaborator and
  review state; migration head; component/approval/activation counts; and all four predecessor
  store fingerprints. The implementation branch is proved to descend from current
  `origin/main`.
- **Evidence:** commands, timestamps, resolved SHAs, remote URLs, CI conclusions, protection
  JSON hash, and zero-write fingerprint receipts.
- **Dependencies:** none.

### S21D3-001 — Publish the immutable D2 evidence reconciliation

- **Deliverable:** `evidence/sprint-21d3-d2-reconciliation.json` plus a short referenced
  erratum in the D3 report/handoff.
- **Acceptance:** distinguishes ranking decisions from candidate outcomes; proves D2 had ten
  OOD decision opportunities; identifies every retrieval metric/narrative mismatch; reruns the
  frozen calculation code without modifying D1/D2 evidence; names the authoritative computed
  development values and hashes the source evidence.
- **Evidence:** old/new unit labels, formulas, exact JSON pointers, replay command, result hash,
  and `protected_objects_unchanged: true`.
- **Dependencies:** S21D3-000.

### S21D3-002 — Provision isolated D3 authorities

- **Deliverable:** a D3 PostgreSQL database, Artifact Store root, evidence output root, backup
  root, restore database, and scratch roots, all outside predecessor pairs.
- **Acceptance:** provisioning uses `scripts/postgres_provision_evidence.sh`; shell operations
  receive the explicit `COGOS_POSTGRES_ENV_FILE`; permissions pass; migration reaches `0015`;
  no D3 process has a predecessor Artifact Store as its writable root.
- **Evidence:** redacted environment manifest, database role/privilege check, migration output,
  absolute-root inventory, and before/after predecessor fingerprints.
- **Dependencies:** S21D3-000.

### S21D3-003 — Freeze the predecessor evidence and seal inventory

- **Deliverable:** `evidence/sprint-21d3-predecessor-inventory.json`.
- **Acceptance:** enumerates the explicit 240-member D2 learning snapshot, all 480 stored
  observations, every partition seal and its chronology, campaign bundle identities, D2
  feature/member hashes, selection/continuation hashes, and zero final/canary outcomes. It
  rejects store-wide or latest-seal selection.
- **Evidence:** exact observation, feature, group, campaign, partition, manifest, and seal
  counts; duplicate-execution warning; integrity content hash.
- **Dependencies:** S21D3-002.

### S21D3-004 — Audit correction final and canary reuse eligibility

- **Deliverable:** one eligibility record per final A, final B, and canary manifest.
- **Acceptance:** using only the sealed catalogue/root/access identities, verifies exact 30/120,
  30/120, and 5/20 membership; unchanged catalogue, source-file, and manifest hashes; pairwise
  group/clone/source disjointness; zero outcomes, predictions, and body-access receipts;
  capability isolation from fitting; and no D2 final-access authority. It records exactly
  `reuse` or `replacement_required` for each whole role without resolving protected bodies or
  individual body hashes. Revision 3 pre-registers the complete replacement procedure and exact
  role counts; S21D3-030 authors any required whole replacement after S21D3-018, S21D3-031 proves
  separation, and S21D3-032 seals it before measurement. No partial role reuse is permitted.
- **Evidence:** role decision, catalogue/root/access hashes, zero-access proof, and conditional
  replacement contract. Individual reused-role bodies and all v2 feature hashes remain
  inaccessible until the S21D3-059/S21D3-060 final-access boundary; replacement authoring uses
  only the isolated Section 0.3 exception and cannot resolve a reused body.
- **Dependencies:** S21D3-003.

### S21D3-005 — Open the draft implementation PR in wave 1

- **Deliverable:** a draft PR from `feature/sprint-21d3-invariant-correction-ranking` to
  protected `main` after baseline/pre-registration scaffolding exists.
- **Acceptance:** PR description states the negative predecessor, current gate state, no
  migration by default, positive/negative release routes, exact holdout stop lines, and the
  single-reviewer limitation. No administrator bypass or protection change is requested.
- **Evidence:** PR number, initial head SHA, and required-check inventory in the execution log.
- **Dependencies:** S21D3-000 through S21D3-004 and S21D3-018 document scaffold.

## EPIC S21D3-E01 — Revision-3 experimental contract

### S21D3-010 — Freeze unit-correct ranking and OOD terminology

- **Deliverable:** revision-3 evaluator contract models and pre-registration section defining
  group ranking, candidate outcome, metamorphic case, coverage, abstention, changed action, and
  confident error.
- **Acceptance:** `decisions == answered + abstained`; every decision resolves four candidate
  labels; all reported rates name their numerator and denominator unit; schema validation
  refuses the D2-style candidate-slot decision count.
- **Evidence:** canonical contract hash and unit tests with one 4-candidate group counted as one
  decision/four outcomes.
- **Dependencies:** S21D3-001.

### S21D3-011 — Freeze the per-channel diagnostic protocol

- **Deliverable:** a manifest for clean, rename-only, issue-only, baseline-reorder-only,
  test-only, and combined cases on the spent D2 diagnostic groups.
- **Acceptance:** names the exact D2 members and setting; records inputs, each scalar,
  semantically named embedding channel, cosine/hash drift, neighbours, ranking, confidence,
  abstention, and verifier labels; binds the five-step response in Section 3.3 before execution.
- **Evidence:** manifest hash, perturbation code hashes, seeds, applicability rules, and
  `selection_authority: false`.
- **Dependencies:** S21D3-010.

### S21D3-012 — Freeze `correction-ranking-v2`

- **Deliverable:** a complete feature-contract revision before any diagnostic number is read.
- **Acceptance:** specifies canonical candidate-source normalization, removed input channels,
  retained scalar channels, named embedding dimensions, MiniLM model/tree identity, bounds,
  missing-value behavior, denylist, exact invariants, fail-closed cases, and artifact schema
  identity.
- **Evidence:** canonical feature-contract hash and a diff from v1 listing every added, removed,
  and semantically changed field.
- **Dependencies:** S21D3-010.

### S21D3-013 — Freeze dataset, grouping, and explicit-selection authority

- **Deliverable:** revision-3 dataset/split protocol.
- **Acceptance:** dataset identity includes feature-schema hash and canonical selection/partition
  digest; explicit manifests contain campaign identity, partition, observation-to-group mapping,
  and member hashes; existing records with different schema/split/role/surface are refused;
  legacy default identities remain readable and unchanged.
- **Evidence:** identity formula, role matrix, transitive grouping rule, and seeded mismatch
  cases.
- **Dependencies:** S21D3-003, S21D3-012.

### S21D3-014 — Complete correction and retrieval power/yield analysis

- **Deliverable:** `evidence/sprint-21d3-power-and-yield.json` produced without outcome access.
- **Acceptance:** justifies 50/200 fitting, 20/80 calibration, exact 30/120 final A/B, 5/20
  canary, 120 nominal and at least 100 valid calibration metamorphic decisions, 120 nominal and
  at least 100 valid promotion decisions over twenty eligible groups, and
  retrieval overproduction sufficient to leave at least 50 qualifying unseen queries. It
  reports detectable paired effects and expected changed-decision yield under conservative
  assumptions.
- **Evidence:** formulas, assumptions, floors, overproduction count, and deterministic seed.
- **Dependencies:** S21D3-004, S21D3-010.

### S21D3-015 — Freeze fresh calibration and promotion transformation manifests

- **Deliverable:** transformation recipes, case-ID derivation, and unopened submanifest contracts
  for the fresh calibration and final promotion sets.
- **Acceptance:** freezes the six nominal cases in Section 4.3, the released independent
  generator tree hash for reused primitives, complete algorithms plus golden input/output hashes
  for any new variant, hard-coded-oracle hashes, deterministic seeds, task
  eligibility/applicability rules,
  manifest-order selection, independent verifier-label rules, and the 120-nominal/100-valid floor
  for each stage. It does not claim not-yet-authored case, source, candidate, or body hashes;
  S21D3-032 resolves exact group/case/member identities after authoring and before execution. No
  D2 calibration-OOD member is reused for selection. Optional reorder/test-only probes are
  reported separately and cannot satisfy condition 20.
- **Evidence:** recipe-contract content hash and static proof that candidate-outcome cardinality
  cannot be substituted for ranking-decision cardinality.
- **Dependencies:** S21D3-010, S21D3-012, S21D3-014.

### S21D3-016 — Freeze the retrieval candidate and benchmark contract

- **Deliverable:** retrieval protocol revision 3 naming equal-weight lexical+MiniLM RRF with
  constant 60, unchanged comparators, exact tie-break, resource policy revision 2, metric code,
  new-holdout separation, and a one-read rule.
- **Acceptance:** both input arms rank the complete eligible pool before fusion; only strictly
  positive lexical results receive lexical ranks, zero-score documents are absent, MiniLM ranks
  the complete pool, a missing arm contributes zero, and output truncation occurs once after
  fusion. No weight/constant/arm sweep; `scripts/experience.py` or its D3 wrapper must
  require the intended policy hash rather than silently use revision-1 defaults; all metrics,
  latency, cutoffs, coverage, candidate counts, model/policy/query hashes are declared.
- **Evidence:** protocol and policy hashes plus a test vector with exact fused ordering.
- **Dependencies:** S21D3-001, S21D3-014.

### S21D3-017 — Freeze metrics, fixed gates, and stop records

- **Deliverable:** a machine-readable D3 gate manifest mapping all 29 Gate L2 and three open
  Gate D1 conditions to metrics, floors, evidence handles, predecessor reuse, and stop status.
- **Acceptance:** includes Section 2.3 non-silence rules, seed 21041/2,000 bootstrap resamples,
  benefit/retention/retrieval budgets, first-failure precedence, and typed `not_opened` payloads.
  No threshold differs from the existing gate except stricter D3 safeguards.
- **Evidence:** gate-manifest hash and schema tests rejecting missing denominators or conditional
  children without a parent stop hash.
- **Dependencies:** S21D3-010 through S21D3-016.

### S21D3-018 — Publish pre-registration revision 3

- **Deliverable:** `evidence/sprint-21d3-pre-registration.json`, committed before any new
  D3 candidate/development/holdout channel measurement, feature implementation result,
  campaign, or retrieval score. S21D3-001's immutable predecessor reconciliation replay is a
  baseline audit and is explicitly exempt.
- **Acceptance:** binds S21D3-010 through S21D3-017, current code/tree hashes, all data roles,
  final/canary reuse decision and conditional whole-role replacement procedure (not
  not-yet-authored members), new retrieval plan, intervention, fixed k-NN grid, RRF arm,
  non-silence rules, and positive/negative exits. It records zero final outcomes inspected and
  zero D3 candidate/development/holdout measurements executed.
- **Evidence:** commit SHA, content hash, clock, predecessor hashes, and an automated chronology
  check used by all later evidence.
- **Dependencies:** S21D3-010 through S21D3-017.

## EPIC S21D3-E02 — Feature, matrix, dataset, and receipt corrections

### S21D3-020 — Create the production alpha-normalisation authority

- **Deliverable:** the small production standard-library Python 3.12 AST canonicalizer specified
  exactly in Section 4.1.
- **Acceptance:** module/class/function/lambda/comprehension scope-aware lexical first-binding
  placeholders; every source-local definition and resolved use is replaced consistently;
  imports/aliases, attributes, builtins, magic names, and strings remain unchanged; exact prefix
  and `ast.dump` byte
  grammar; formatting and input mapping order cannot affect output; unsupported syntax,
  reflective ambiguity, reserved-prefix collision, parse failure, and mapping collision refuse.
  Metamorphic pairs come from the independently released generator and hard-coded pairs, never
  from this production canonicalizer.
- **Evidence:** golden bytes/hashes and property tests for module/function/class names,
  parameters, locals, comprehensions, exception targets, matching keyword calls, nested scopes,
  global/nonlocal resolution, excluded imports/attributes/builtins/magic names, reflection, and
  collisions.
- **Dependencies:** S21D3-018.

### S21D3-021 — Implement `correction-ranking-v2`

- **Deliverable:** v2 feature input/vector/encoder wired through feature sealing.
- **Acceptance:** embeds canonical candidate source; removes raw diff counts, task embedding,
  and query/delta cosine from the fitted representation; retains declared source-structural and
  capability fields; produces exact equality under all excluded-input perturbations; every
  seeded semantic operator/condition mutation changes the canonical bytes and hash, and seeded
  cases also demonstrate vector movement without asserting universal embedding injectivity.
- **Evidence:** encoder contract tests, golden canonical bytes/hash, v1/v2 incompatibility tests,
  deterministic restart test, and feature-timing proof.
- **Dependencies:** S21D3-020.

### S21D3-022 — Make matrix validation inspect the fitted embedding

- **Deliverable:** revised fitted-matrix projection and audits with semantically named embedding
  dimensions/channels.
- **Acceptance:** allowlist, finite/range, identity, duplicate-label, near-duplicate, and perfect
  label-separation checks inspect every fitted scalar and embedding dimension; a seeded unstable
  or label-perfect embedding dimension is detected; the released seeded oracle/identity tests
  remain green.
- **Evidence:** matrix schema/hash, exact fitted dimension count, scan results, and focused tests.
- **Dependencies:** S21D3-021.

### S21D3-023 — Make explicit dataset identity feature- and partition-sensitive

- **Deliverable:** a backward-compatible explicit-selection identity revision in
  `learned_datasets.py` and an artifact-stored selection manifest extending the existing
  `LearnedSplitManifest` artifact/lineage role.
- **Acceptance:** new identity includes feature schema plus canonical selection/partition
  digest; campaign and group mapping persist; an existing mismatched dataset is refused rather
  than returned; the D2 legacy dataset remains readable under its old identity; no migration is
  required. No new `LearnedArtifactRole` value is introduced because the PostgreSQL role check
  remains at migration `0015`.
- **Evidence:** unit/integration tests for same members/different schema, same schema/different
  role, reordered equivalent selection, cross-surface collision, and restart replay.
- **Dependencies:** S21D3-013, S21D3-021.

### S21D3-024 — Correct the OOD case and counting contracts

- **Deliverable:** explicit case identities in the OOD submanifest and unit-correct precheck,
  calibration, assessment, report, and CLI models.
- **Acceptance:** each case binds source group, transformation/composition, seed, candidate set,
  and manifest; decision count equals answered plus abstained; candidate outcomes are separate;
  both errors/all-decisions and errors/answered are emitted; selection enforces the Section 2.3
  coverage/action rules. Pair generation follows the independently frozen S21D3-015 algorithms
  and golden outputs; it never calls the production S21D3-020 canonicalizer as its oracle.
- **Evidence:** schema migration at the JSON-contract level only, rejection tests for D2-style
  `groups * candidates`, and golden 10-group/50-case count examples.
- **Dependencies:** S21D3-010, S21D3-015.

### S21D3-025 — Bind receipt-aware resume to the exact campaign

- **Deliverable:** strengthened resume validation, one authoritative effective-remainder API,
  and a versioned campaign receipt manifest extending the existing campaign manifest.
- **Acceptance:** the receipt manifest binds bundle IDs, feature seal/root, and exact selected
  member/order identities. The existing `RealityCampaignSequenceRecorded` event retains its
  campaign-manifest hash, mode, and orders and binds that receipt manifest; event replay validates
  the hash/mode/order. A receipt's manifest, mode, candidate order, bundle identity, feature seal,
  and selected members must match the current campaign; callers cannot schedule
  `candidates_left_alone` through the ordinary remainder; only exactly named missing outcomes
  rerun. No event-field or migration change is expected; if implementation proves a payload
  revision necessary, update the event catalog, schema export, and golden fixtures compatibly.
- **Evidence:** stale/tampered manifest, changed mode/order, restart-after-first-accept,
  missing-outcome, unsealed-task, and repeated-resume tests.
- **Dependencies:** S21D3-013, S21D3-023.

### S21D3-026 — Run the frozen D2 per-channel diagnostic

- **Deliverable:** `evidence/sprint-21d3-channel-invariance-diagnostic.json` generated strictly
  from the pre-registered S21D3-011 manifest.
- **Acceptance:** reproduces D2 clean/combined behavior; reports every channel and case
  separately; includes executed labels and exact setting; carries `development_only`; cannot be
  imported by calibration selection; no response threshold is computed from the results. A
  version-dispatched v1 path preserves D2 feature/vector/matrix serialization byte for byte. If
  that cannot be guaranteed, execute the immutable diagnostic code in an isolated checkout at
  `sprint-21d2-evidence-baseline` and let D3 consume only its hashed result; v2 code may not alter
  any D2 member, matrix, or diagnostic hash.
- **Evidence:** resolved-member hash, code/protocol hashes, per-channel table, reproduction
  status, and zero new D3 calibration/final access.
- **Dependencies:** S21D3-018, S21D3-022, S21D3-024.

### S21D3-027 — Record diagnostic applicability or stop

- **Deliverable:** a typed continuation decision bound to S21D3-026.
- **Acceptance:** proceeds only when the observed moved channels fall inside Section 3.3 and v2
  satisfies the declared exact invariants; otherwise records the first failure, closes campaign,
  fitting, final, promotion, and activation work, while leaving independent retrieval and
  release work open.
- **Evidence:** decision hash, rule evaluation trace, opened/not-opened task list, and no
  improvised feature branch.
- **Dependencies:** S21D3-026.

### S21D3-028 — Prove feature sealing and resume chronology for v2

- **Deliverable:** an end-to-end pre-outcome feature-seal/resume test for one task group.
- **Acceptance:** v2 canonical bytes seal before execution; replay reproduces the same feature
  and seal hashes; a fresh post-outcome seal is refused; stored seal time is preserved; campaign
  receipt and dataset member resolve the same feature record after restart.
- **Evidence:** ordered timestamps, hashes, event/artifact lineage, and seeded W4-F3 regression.
- **Dependencies:** S21D3-021, S21D3-023, S21D3-025.

## EPIC S21D3-E03 — Fresh self-play, calibration, and candidate selection

### S21D3-030 — Author the new calibration and retrieval task groups

- **Deliverable:** 20 fresh four-candidate calibration groups and an overproduced retrieval
  source pool of at least 60 fresh failed/success task groups; conditionally, complete
  replacement roles of exactly 30 final-A groups, 30 final-B groups, and/or 5 canary groups for
  every role marked `replacement_required` by S21D3-004.
- **Acceptance:** tasks use the released neutral per-task recipe binding and independent hidden
  verifier; cover declared coding families without copying D2 calibration/final/canary tasks;
  retrieval tasks yield causal failed/success evidence suitable for graph projection; all
  baselines and variants parse and execute; calibration and replacement-final packages satisfy
  the six-case eligibility contract. A failed role is replaced as a whole and no partial role or
  late substitution is allowed. Replacement bodies and their authoring replay are visible only
  to a dedicated isolated corpus-authoring validator before deterministic role assignment;
  authoring replays are explicitly throwaway fixture validation, never authoritative learning
  observations, evaluation outcomes, or outcome-floor members.
- **Evidence:** template inventory, authoring-defect ledger, exact counts, whole-role replacement
  inventory, and a sanitised validator report containing only package hashes and parse/execution
  pass/fail—not candidate scores, verifier labels, bodies, or suitability metrics—before any
  learning score is computed.
- **Dependencies:** S21D3-018.

### S21D3-031 — Prove rights, lineage, group, and near-clone separation

- **Deliverable:** one transitive separation and rights report covering D2 inherited roles plus
  every new D3 calibration, retrieval, and conditional replacement item.
- **Acceptance:** zero task/repository/template/source/near-clone group crosses fitting,
  calibration, final A, final B, canary, or retrieval; every source has permitted self-play and
  evaluation rights. Newly authored D3 calibration/retrieval/replacement candidates differ from
  all C3/D1/D2 candidates below the frozen near-clone ceiling. Explicitly inherited fitting and
  reused final/canary members instead prove exact identity/hash reconciliation and zero
  cross-role overlap. Seeded collisions are detected.
- **Evidence:** full pairwise role matrix, cluster membership, maximum similarities, source
  lineage hashes, and rights decisions.
- **Dependencies:** S21D3-030.

### S21D3-032 — Seal all D3 campaign and holdout manifests

- **Deliverable:** hash-bound manifests for 50 reused fitting groups, 20 new calibration groups,
  final A, final B, canary, calibration metamorphic cases, promotion cases, and the distinct
  retrieval pool.
- **Acceptance:** every member, role, group, feature-contract hash, campaign mode, bundle ID,
  seed, capability, exact case ID, source-group identity, and available catalogue/member hash is
  explicit; final/canary bodies remain inaccessible to fitting;
  correction and retrieval groups share none; every manifest records `outcomes_present: false`
  at seal. Exact transformed-body, feature, and prediction hashes are intentionally deferred to
  S21D3-038 or S21D3-060, but every case identity is sealed before its score or execution. The
  promotion manifest enumerates six candidate case IDs for every one of the 60 final groups; the
  pre-registered manifest-order rule later selects the first 20 eligible groups without reading
  outcomes. For replacement roles, sealing records the authoring-validator capability closure;
  no authoring scratch result is copied into the D3 Event Store, Artifact Store, or metrics, and
  all replacement body capabilities remain closed until S21D3-059.
- **Evidence:** manifest hashes, pairwise disjointness, capability-isolation proof, zero-outcome
  counts, and replacement-role proof if S21D3-004 rejected reuse.
- **Dependencies:** S21D3-004, S21D3-015, S21D3-031.

### S21D3-033 — Prove one complete v2 campaign vertical slice

- **Deliverable:** one group from preparation through package, v2 feature seal, self-play
  execution, verifier outcome, receipt, role-bound observation, explicit dataset selection,
  fitted row, k-NN ranking, abstention/fallback, and restart replay.
- **Acceptance:** uses a dedicated fixture group excluded from fitting, calibration, final,
  canary, and retrieval roles; no final/retrieval capability is present; the verifier decides
  labels and acceptance; prediction only changes candidate order; every hash resolves; the same input and
  receipt replay without a duplicate outcome.
- **Evidence:** vertical-slice JSON, event/artifact lineage, focused PostgreSQL test, and
  predecessor fingerprint check.
- **Dependencies:** S21D3-028, S21D3-032.

### S21D3-034 — Seal every fitting and calibration v2 feature before execution

- **Deliverable:** 280 canonical v2 feature records and partition-level seals: 200 fitting and
  80 calibration.
- **Acceptance:** all records precede the first corresponding container start; hashes bind
  a provenance envelope containing candidate/group/partition identity to canonical source,
  scalar/embedding vector, contract, and MiniLM tree; no outcome, recipe, hidden control, or
  candidate identity enters `CorrectionFeatureVector`, matrix columns, or model similarity.
- **Evidence:** feature-seal manifest, earliest/latest timestamps, member hashes, exact counts,
  and chronology verifier output.
- **Dependencies:** S21D3-027 `proceed`, S21D3-032, S21D3-033.

### S21D3-035 — Execute and ingest the v2 fitting campaign

- **Deliverable:** 200 new verifier-backed `SELF_PLAY` observations over the exact 50 fitting
  groups.
- **Acceptance:** new campaign/run identities; four candidates per group; explicit receipt-aware
  resume; no final/calibration/retrieval member; exactly 200 selected outcomes regardless of
  store surface totals; acceptance balance and failures reported rather than repaired after
  inspection.
- **Evidence:** campaign/receipt hashes, run and observation IDs, verifier outputs, counts by
  group/label/provenance, retry/resume report, and zero predecessor writes.
- **Dependencies:** S21D3-034.

### S21D3-036 — Execute and ingest the fresh calibration campaign

- **Deliverable:** 80 new verifier-backed `SELF_PLAY` observations over the exact 20 calibration
  groups.
- **Acceptance:** separate campaign and bundle identities; no fitting/final/canary/retrieval
  member; calibration observations never become exemplars; all labels resolve to presealed v2
  features; no candidate score is computed until all 80 outcomes are frozen.
- **Evidence:** campaign/receipt hashes, exact explicit member list, role/provenance counts,
  chronology and overlap checks.
- **Dependencies:** S21D3-034.

### S21D3-037 — Materialise and validate explicit revision-3 snapshots

- **Deliverable:** separate immutable fitting and calibration datasets plus a fitted matrix
  artifact built only from the fitting snapshot.
- **Acceptance:** identities include v2 feature and selection digests; 200/50 fitting and 80/20
  calibration exact; zero real-run rows; every member resolves one feature/outcome chain;
  matrix scans inspect all scalar and embedding dimensions; every seeded leakage/identity/oracle
  violation fails.
- **Evidence:** dataset, split, matrix, bounds, member/group maps, scan report, and content hashes.
- **Dependencies:** S21D3-022, S21D3-023, S21D3-035, S21D3-036.

### S21D3-038 — Resolve the fresh calibration metamorphic set

- **Deliverable:** at least 100 previously unscored group-level cases with four independently
  executed labels each, from 120 nominal cases derived only from the 20 fresh calibration groups.
- **Acceptance:** cases match S21D3-015's frozen recipes and S21D3-032's exact sealed case
  submanifest; per-channel and combined cases are distinct; all applicable transformed packages
  execute; labels are not carried from clean
  tasks without verification; every transformed feature record is sealed before its transformed
  candidate execution; no case enters fitting; actual decision/outcome/applicability counts meet
  their floors. Optional reorder/test-only boundary probes are reported separately and do not
  contribute to the 100 valid decisions.
- **Evidence:** resolved-set/submanifest hashes, 100+ decision IDs, 400+ candidate outcome
  results, applicability ledger, verifier logs, and zero final access.
- **Dependencies:** S21D3-024, S21D3-032, S21D3-036, S21D3-037.

### S21D3-039 — Calibrate revised k-NN and select at most one candidate

- **Deliverable:** complete deterministic ladder, all 24 fixed k-NN settings, corrected OOD
  prechecks, continuation classification, and one candidate-selection record or null.
- **Acceptance:** strongest non-learned baseline is derived; every setting records clean rate,
  coverage, changed actions, per-case coverage/action preservation, errors over all/answered,
  latency, and filter reason; Section 2.3 rules apply; deterministic tie-break chooses at most
  one eligible setting; selection occurs before final access and cannot authorise a parametric
  rung.
- **Evidence:** ladder/grid/selection hashes, exact denominators, selected setting and lineage or
  first-failure null, plus dependent `not_opened` mapping.
- **Dependencies:** S21D3-037, S21D3-038.

## EPIC S21D3-E04 — Independent retrieval remediation and holdout

### S21D3-040 — Repair the reusable retrieval benchmark boundary

- **Deliverable:** an operator benchmark that requires an explicit frozen policy identity and
  emits the complete pre-registered metric set.
- **Acceptance:** revision-1 defaults cannot be used silently; expected policy hash is checked;
  output includes Recall@5, MRR@10, nDCG@10, p50/p95/max latency, timeouts, cutoffs, coverage,
  candidate counts, query/model/policy/manifests, and repeated-order agreement.
- **Evidence:** CLI tests for correct/wrong/missing policy; canonical benchmark schema and hash.
- **Dependencies:** S21D3-016, S21D3-018.

### S21D3-041 — Implement fixed equal-weight reciprocal-rank fusion

- **Deliverable:** one deterministic RRF arm in the existing graph retrieval module.
- **Acceptance:** reusable untruncated scorers rank the complete eligible pool; only positive
  lexical scores enter the lexical ranking, MiniLM ranks the complete pool, and a missing arm
  contributes zero. Exactly lexical plus MiniLM ranks, constant 60, equal weights, existing
  stable final tie-break, and one post-fusion truncation to at most ten outputs; no GED, weight
  fitting, new index, or dependency; input arms retain their own evidence identities.
- **Evidence:** exact-order examples, tie/missing/duplicate tests, deterministic replay, and
  resource-bound assertions.
- **Dependencies:** S21D3-016.

### S21D3-042 — Reproduce and reconcile the frozen D1 development benchmark

- **Deliverable:** `evidence/sprint-21d3-d1-retrieval-development.json` covering unchanged
  comparators and RRF on the frozen 80-query D1 set.
- **Acceptance:** reproduces the authoritative values recorded by S21D3-001 within deterministic
  precision; records RRF without tuning it; identifies query-level complementarity/residuals;
  labels the complete output development-only and non-gating.
- **Evidence:** old query/root/model/policy hashes, all arm metrics, per-query rankings, latency,
  and zero D1 store writes.
- **Dependencies:** S21D3-040, S21D3-041.

### S21D3-043 — Resolve and seal the distinct retrieval holdout

- **Deliverable:** a new unseen-task query/pair/judgement set, overproduced until at least 50
  qualifying queries remain after integrity filtering.
- **Acceptance:** no correction fitting/calibration/final/canary group overlap; no D1/D2 query,
  task signature, source lineage, or near-clone reuse; relevance judgements and tiers frozen
  before ranking; every query/pair source and edit path resolves; all arms remain unable to read
  judgements.
- **Evidence:** query and pair root hashes, group/clone matrix, judgement manifest, exact query
  count by domain/tier, and capability proof.
- **Dependencies:** S21D3-031, S21D3-032, S21D3-040, S21D3-041.

### S21D3-044 — Project and verify the new retrieval graph pairs

- **Deliverable:** bounded failed/success graphs and canonical edit paths for every holdout pair.
- **Acceptance:** source resolution and edit-path round-trip are 100%; graphs respect 64-node,
  128-edge, and depth-32 bounds; relevance evidence is independent of the arm; projection does
  not create execution or correction authority.
- **Evidence:** graph-root artifact, pair/member hashes, integrity report, resource distributions,
  and seeded corrupt/missing-path refusals.
- **Dependencies:** S21D3-043.

### S21D3-045 — Evaluate all frozen retrieval arms exactly once

- **Deliverable:** final unseen-task retrieval benchmark for no-memory, exact signature,
  lexical, MiniLM vector, width-20 bounded GED, and RRF.
- **Acceptance:** one execution after query/judgement resolution; identical eligible pool and
  limits for comparable arms; at least 50 queries; no tuning or rerun after metrics are read;
  complete accuracy/resource denominators and query-level residuals recorded.
- **Evidence:** signed/hash-bound benchmark, command/environment, arm and per-domain/tier metrics,
  latency/timeouts/cutoffs, and one-read receipt.
- **Dependencies:** S21D3-042, S21D3-044.

### S21D3-046 — Decide D1 condition 15 and Gate L2 condition 24

- **Deliverable:** independent retrieval gate decision bound to S21D3-045.
- **Acceptance:** passes only if one arm reaches both Recall@5 `>= 0.70` and MRR@10 `>= 0.50`
  inside all fixed budgets. Otherwise records the first failed floor and a negative retrieval
  result; no alternative fusion, width, weight, metric, or holdout member opens in D3.
- **Evidence:** rule trace, winning arm or null, gate-condition mapping, and residual
  classification.
- **Dependencies:** S21D3-045.

### S21D3-047 — Preserve the advisory Experience Graph boundary

- **Deliverable:** Context Builder and authority-invariance proof for every retrieval outcome.
- **Acceptance:** retrieval may add advisory context with provenance and trust but cannot execute
  an edit, accept a correction, mutate active memory, approve a component, or bypass the
  verifier; no-memory fallback remains valid; retrieval failure cannot corrupt the correction
  campaign.
- **Evidence:** focused unit/integration tests and mandatory-path hash comparison.
- **Dependencies:** S21D3-041, S21D3-046.

## EPIC S21D3-E05 — Artifact, runtime, and lifecycle readiness

### S21D3-048 — Version the D3 promotion payload and evaluator contract

- **Deliverable:** a backward-compatible D3 promotion payload schema and deterministic evaluator
  in `src/cognitive_os/domain/learned.py` (or one dedicated domain module) and
  `src/cognitive_os/learning/promotion.py`.
- **Acceptance:** preserves all legacy assessment fields and additionally binds matrix,
  calibration, dataset/split/member/feature, benefit, paired interval, independent-batch
  direction, safety, retention, metamorphic/OOD, shadow, retrieval, resource, fallback, artifact
  metadata/media/schema/hash/size, component/revision/surface, and every dependency hash. It also
  binds the exact canary configuration hash, exact bounded steady-state configuration hash, and
  the successful-canary/rollback transition condition. The assessment content hash commits to
  the D3 payload-artifact ID and byte hash; the stored evidence `payload_hash` equals that
  assessment content hash and its existing `payload_artifact_id` resolves the same verified
  bytes. The payload is stored through the existing `PROMOTION_ASSESSMENT`
  evidence/payload-artifact authority; no new artifact role, lineage role, table, event
  authority, or migration is introduced. Legacy payloads remain readable through explicit
  version dispatch.
- **Evidence:** canonical schema and golden hash, evaluator truth table, missing/stale/wrong
  dependency cases, legacy compatibility tests, and PostgreSQL/Artifact Service round-trip.
- **Dependencies:** S21D3-017, S21D3-021, S21D3-023.

### S21D3-050 — Version the canonical correction artifact for v2

- **Deliverable:** inert JSON artifact schema carrying v2 canonicaliser, named feature channels,
  bounds, MiniLM identity/tree, dataset/split/selection/member hashes, setting, code revision,
  descriptor, and declared limitations.
- **Acceptance:** canonical bytes are order-independent and re-hash identically; executable
  type/class/import paths are absent; unsafe formats remain unreachable; v1/v2 confusion and
  missing lineage fail before model construction.
- **Evidence:** schema/golden-byte tests, malformed/oversized/unsafe cases, and exact lineage
  round-trip.
- **Dependencies:** S21D3-021, S21D3-023.

### S21D3-051 — Fit and store the selected artifact, or record not opened

- **Deliverable:** one artifact for the S21D3-039 candidate, written through Artifact Service,
  or a `not_opened` record bound to the null selection.
- **Acceptance:** fit uses only the explicit 200-row fitting snapshot and frozen bounds/setting;
  bytes, metadata, media/schema/hash/size, feature members, and selection record agree; no
  calibration exemplar or final member enters the artifact.
- **Evidence:** artifact ID/hash/size, fit input hashes, 0 real-run proof, reproducible-byte test,
  or stop hash.
- **Dependencies:** S21D3-039, S21D3-050.

### S21D3-052 — Enforce the narrow v2 loader and runtime resolver

- **Deliverable:** two explicit fail-closed boundaries: (1) a direct hash-verified inert
  artifact-to-ranker builder for controlled calibration/final/shadow evaluation while the
  component is unapproved or SHADOW, and (2) the production `LearnedRuntimeResolver`, which
  remains ACTIVE/configuration/approval gated for canary and steady runtime routing.
- **Acceptance:** both boundaries rehash exact bytes and validate schema/model/encoder/
  normaliser/dataset/split/member identities. The direct builder accepts only an exact artifact
  hash under an evaluation capability and cannot be selected by the application runtime. The
  resolver additionally refuses config/component/lifecycle/approval mismatches; missing,
  corrupt, oversized, inactive, disabled, or unapproved runtime states return named
  deterministic fallbacks; two active revisions fail rather than choose one.
- **Evidence:** focused direct-loader and resolver tests for every reason code, capability-refusal
  tests, and real Artifact Service byte paths.
- **Dependencies:** S21D3-050.

### S21D3-053 — Route candidate sequencing through receipt-aware effective remainder

- **Deliverable:** the released bounded sequencer updated to consult only S21D3-025's
  receipt-aware remainder on restart/resume/canary.
- **Acceptance:** learned ranking changes attempt order only; every attempt executes the hidden
  verifier; first accepted candidate stops later attempts; intentionally left-alone candidates
  never re-enter through an ordinary resume plan; abstention/loader failure uses exact baseline
  order.
- **Evidence:** first-accept, no-accept, abstain, crash-at-each-boundary, missing-outcome, and
  repeated-resume tests.
- **Dependencies:** S21D3-025, S21D3-052.

### S21D3-054 — Prove the selected-artifact vertical slice

- **Deliverable:** one isolated offline task through stored v2 artifact, the direct inert loader,
  learned ordering, verifier, receipt, outcome linkage, restart, and deterministic fallback.
- **Acceptance:** exact selected artifact/evaluation configuration is used without lifecycle
  registration or actual ACTIVE/SHADOW projection; prediction never accepts; outcome linkage is
  verifier-derived; corrupt bytes produce the baseline; restart reloads identical inert bytes and
  ranking without re-fitting. Production resolver behavior remains a focused fixture test until
  S21D3-056 registers the real D3 component.
- **Evidence:** vertical-slice artifact/event/receipt hashes and focused PostgreSQL integration.
- **Dependencies:** S21D3-051 selected, S21D3-052, S21D3-053.

### S21D3-055 — Re-prove mandatory-path and configuration invariance

- **Deliverable:** hashes over direct-evaluation loading plus component-absent, present-disabled,
  SHADOW, loader-refused, and ACTIVE-canary resolver fixtures before any final evidence.
- **Acceptance:** mandatory deterministic cases are byte-identical; only the bounded correction
  campaign may change ordering; zero provider/network/GPU/credential calls; wrong configuration
  reports the actual fallback reason rather than an optimistic component state. Test fixtures are
  labelled as contract tests and are not represented as the real D3 lifecycle projection.
- **Evidence:** `MandatoryPathInvariance`, runtime health matrix, and call counters.
- **Dependencies:** S21D3-052, S21D3-054.

### S21D3-056 — Register the exact artifact and enter SHADOW

- **Deliverable:** descriptor, component revision, artifact-lineage evidence, and
  `REGISTERED -> SHADOW` transition for the selected artifact; otherwise bound not-opened
  evidence.
- **Acceptance:** revision names v2 feature/artifact/dataset/selection hashes and declared
  limitations; no activation or final outcome exists; replay and restart yield the same SHADOW
  projection; generic transition APIs cannot jump to VERIFIED or ACTIVE.
- **Evidence:** ledger/event IDs, component/revision/artifact hashes, replay proof, or stop hash.
- **Dependencies:** S21D3-051 selected, S21D3-054, S21D3-055, and the implementation portion of
  S21D3-057.

### S21D3-057 — Add focused evidence-bound verification

- **Deliverable:** `verify_component()` as the only `SHADOW -> VERIFIED` path.
- **Acceptance:** generic advancement refuses VERIFIED and ACTIVE; verification reloads the
  exact eligible stored S21D3-048 payload, checks every dependency, current
  component/revision/surface, Artifact Store metadata/media/schema/hash/size, and rehashed bytes;
  transition records the assessment hash atomically.
- **Evidence:** unit/PostgreSQL tests for success, missing/stale/wrong assessment, substituted
  artifact, metadata drift, byte corruption, wrong revision/surface, and replay.
- **Dependencies:** S21D3-048, S21D3-052.

### S21D3-058 — Revalidate artifact bytes immediately before activation

- **Deliverable:** activation-time lineage and byte verification using the same narrow verifier
  authority as S21D3-057.
- **Acceptance:** approval and activation cannot rely on an earlier successful read; any payload
  artifact, metadata, schema, hash, size, component, revision, assessment, or bytes mismatch
  leaves state unchanged and falls back; no deserialisation occurs during verification.
- **Evidence:** time-of-check/time-of-use substitution tests and atomic no-mutation assertions.
- **Dependencies:** S21D3-057.

### S21D3-059 — Authorise final access at one pre-final checkpoint

- **Deliverable:** a pre-final checkpoint joining candidate selection, artifact bytes, SHADOW
  revision, invariance, matrix, calibration/OOD, final manifests, prediction-seal procedure,
  stop rules, and two canonical runtime configurations: exact canary and bounded steady state.
- **Acceptance:** authorises final access only when S21D3-039 selected one candidate and all
  S21D3-048 and S21D3-050 through S21D3-057 implementation/readiness preconditions pass; records
  zero final outcomes inspected at the authorization clock. Before access, it seals both config
  bytes/hashes and the exact successful-canary-plus-rollback condition permitting the canary-to-
  steady switch; neither configuration may change after final evidence is read. On null, every
  E06/E07 task receives the same first stop hash.
- **Evidence:** checkpoint and two config hashes, transition predicate, dependency graph, access
  capability, and not-opened map.
- **Dependencies:** S21D3-039, S21D3-048, S21D3-050 through S21D3-057.

## EPIC S21D3-E06 — Final evaluation and promotion evidence

### S21D3-060 — Seal final features and predictions before execution

- **Deliverable:** v2 feature records, rankings, confidences, abstentions, baseline choices, and
  prediction seals for every candidate/group in final A and B before the first final container
  starts, plus the exact promotion-case selection and transformed prediction seals.
- **Acceptance:** uses only the exact S21D3-059 artifact/configuration and reusable/replacement
  manifests; 60 clean group predictions and 240 clean candidate feature records. After protected
  body resolution, the fixed manifest-order rule selects the first 20 groups satisfying the
  six-case eligibility contract, or stops if fewer than 20 exist; it seals 120 transformed group
  predictions and 480 transformed candidate feature records before their verifier runs. No
  outcome is visible. Seals bind final role, group/candidate/case members, artifact, feature
  contract, threshold, code, baseline, and clock.
- **Evidence:** final prediction root, per-batch/member hashes, chronology proof, and
  `final_outcomes_inspected_before_seal: 0`.
- **Dependencies:** S21D3-059 `authorised`.

### S21D3-061 — Execute final batch A without replacement

- **Deliverable:** 120 new verifier-backed `REAL_GOVERNED_RUN` candidate outcomes over the exact
  30 final-A groups.
- **Acceptance:** every presealed candidate executes in evaluation-only mode; no member,
  prediction, order, threshold, or feature changes; all failures/timeouts remain in denominator;
  zero outcome enters fitting/calibration; predictions link only after independent verifier
  evidence exists.
- **Evidence:** campaign and receipt hashes, 120 outcome IDs, 30 group decisions, provenance and
  cost counts, prediction/outcome lineage, and no-replacement assertion.
- **Dependencies:** S21D3-060.

### S21D3-062 — Execute final batch B as independent confirmation

- **Deliverable:** 120 new verifier-backed `REAL_GOVERNED_RUN` outcomes over the exact 30
  final-B groups.
- **Acceptance:** same frozen artifact/configuration as batch A; batch-A results cannot alter
  execution, metrics, or membership; all outcomes retained; no refit or threshold change occurs
  between batches.
- **Evidence:** separate campaign/receipt/member hashes, 120 outcome IDs, 30 group decisions,
  timestamped no-change proof, and exact denominators.
- **Dependencies:** S21D3-061 complete without protocol violation.

### S21D3-063 — Compute paired material benefit

- **Deliverable:** learned-versus-strongest-baseline final assessment over A, B, and aggregate.
- **Acceptance:** at least 20 changed group decisions; first-accepted outcome and attempts to
  first accept computed per group; at least 5 points absolute gain or 20% relative error
  reduction; learned-minus-baseline positive in each batch; paired bootstrap uses seed 21041,
  2,000 group resamples, and 95% lower bound above zero.
- **Evidence:** per-group paired table, exact denominators, effect sizes, interval, bootstrap
  reproducibility hash, and pass/fail trace.
- **Dependencies:** S21D3-061, S21D3-062.

### S21D3-064 — Run safety and cross-domain anti-forgetting replay

- **Deliverable:** safety/governance and retained-domain comparison against the frozen
  deterministic path.
- **Acceptance:** zero accepted-to-rejected safety, permission, governance, secret-handling, or
  destructive-action cases; no retained domain loses more than 2 points; aggregate loss at most
  1 point; every small-suite regression receives item-level review; deterministic fallback is
  counted, not treated as learned success.
- **Evidence:** case hashes, old/new outputs, per-domain and aggregate tables, reviewer records,
  and failure stop hash if applicable.
- **Dependencies:** S21D3-063 meets benefit thresholds.

### S21D3-065 — Execute promotion-scale metamorphic/OOD evaluation

- **Deliverable:** 120 nominal pre-registered cases over twenty manifest-ordered eligible final
  groups, leaving at least 100 valid group-level decisions with four independently verified
  candidate outcomes per valid case.
- **Acceptance:** resolves only S21D3-015 recipes and S21D3-032/S21D3-060 exact promotion-case
  identities after candidate freeze; separates each of the six equivalence recipes; reports
  action preservation, coverage, abstention,
  confident errors/all, confident errors/answered, labels, and applicability; report ceiling is
  at most 1%, promotion requires exactly zero confident errors and all equivalence rules. Every
  transformed feature/prediction seal precedes the corresponding transformed verifier run.
  Operational malformed/corrupt/missing/oversized/permission cases are reported by their runtime
  or integrity tasks and do not enter this ranking-decision denominator.
- **Evidence:** case/submanifest/resolved-set hashes, 100+ decisions, 400+ verifier results,
  metric table, and exact error traces.
- **Dependencies:** S21D3-060, S21D3-063.

### S21D3-066 — Run true shadow mode against final evidence

- **Deliverable:** shadow predictions linked to final outcomes without changing executed order.
- **Acceptance:** execution follows the declared baseline; the SHADOW component's exact artifact
  is loaded only through S21D3-052's direct evaluation boundary, never through the ACTIVE-only
  production resolver; artifact/configuration equals S21D3-060; every link resolves through the
  independent verifier; zero runtime action differs because of shadow; missing/corrupt/inactive
  states report fallback reasons.
- **Evidence:** shadow result IDs, zero-action-change count, lineage hashes, and restart replay.
- **Dependencies:** S21D3-061, S21D3-062, S21D3-056.

### S21D3-067 — Build the strengthened promotion assessment

- **Deliverable:** one S21D3-048-versioned payload stored under the existing
  `PROMOTION_ASSESSMENT` authority for the exact D3 artifact, or a negative assessment bound to
  the first failed condition.
- **Acceptance:** populates and evaluates every S21D3-048 field, including exact canary and
  steady-state config hashes and their transition condition; joins calibration, matrix, benefit,
  batch direction, bootstrap, safety, retention, promotion OOD, shadow, artifact, fallback,
  resource, and retrieval evidence by identity/hash; checks all applicable Gate L2 conditions;
  payload artifact metadata and bytes resolve at assessment time; no condition is inferred from
  D2's status.
- **Evidence:** assessment ID/hash, dependency graph, evaluator identity, eligibility verdict,
  payload-artifact ID/hash/size, and exact failed conditions.
- **Dependencies:** S21D3-048, S21D3-046, S21D3-063 through S21D3-066.

### S21D3-068 — Assess the three open Gate D1 conditions

- **Deliverable:** versioned D3 mapping for D1 conditions 6, 7, and 15.
- **Acceptance:** condition 6 closes only with at least 200 unique eligible verifier-backed
  primary-surface outcomes; condition 7 closes only with at least 20 primary-surface examples
  whose advisory action changes under the frozen useful selection; neither requires activation.
  Condition 15 follows only S21D3-046's new holdout result; historical D1/D2 assessments remain
  unchanged; valid partial closure survives a later retrieval/canary failure and is not promoted
  to an overall Gate D1 pass unless every D1 condition passes.
- **Evidence:** condition-level evidence links and status hashes.
- **Dependencies:** S21D3-046, S21D3-067.

### S21D3-069 — Advance through evidence-bound verification

- **Deliverable:** `SHADOW -> VERIFIED` through S21D3-057 for the exact eligible assessment, or
  a bound not-opened record.
- **Acceptance:** transition occurs only if every fixed promotion condition and D1 remediation
  dependency needed by Gate L2 passes; exact artifact bytes are reverified; assessment hash is
  stored on the revision; failed verification mutates no lifecycle state.
- **Evidence:** verification event/ledger IDs, before/after state, assessment/artifact hashes,
  byte receipt, replay/restart proof, or stop hash.
- **Dependencies:** S21D3-057, S21D3-067 eligible, S21D3-068.

## EPIC S21D3-E07 — Approval, canary, activation, and rollback

### S21D3-070 — Prepare the exact activation bundle

- **Deliverable:** a deterministic activation-preparation record that separates (a) the exact
  existing `LearnedActivationApproval` fields from (b) separately hash-recorded canary and
  bounded steady-state runtime configurations sealed by S21D3-059 and referenced by the
  S21D3-067 assessment.
- **Acceptance:** the direct approval payload contains only component/revision/surface,
  `approval_id`, promotion-assessment hash, artifact-lineage ID, `approved`, approver identity/
  kind, reason, and approval time, matching every existing contract field and no more. The
  preparation record resolves descriptor, assessment payload bytes, artifact
  metadata/hash/size, dataset/split/feature, exact 5-group/20-slot canary config, exact bounded
  steady config, successful-canary/rollback transition condition, verifier, kill switch,
  fallback, and receipt-chain rollback rule. No unresolved pointer, mutable alias,
  model/provider actor, caller-selected rollback target, or final-data capability exists.
- **Evidence:** actual approval-payload template, preparation/config hashes, transitive dependency
  graph, capability inventory, and dry-run refusal tests.
- **Dependencies:** S21D3-069 VERIFIED.

### S21D3-071 — Record explicit human approval

- **Deliverable:** one operator `LearnedActivationApproval` using exactly the existing contract
  fields prepared by S21D3-070.
- **Acceptance:** approver is an eligible human identity distinct from model/provider/campaign
  actors; approval directly binds the assessment hash, component revision/surface, and artifact
  lineage ID, and records `approved=true`. Artifact bytes and the two configuration hashes are
  bound transitively through the
  stored assessment payload and lineage; they are not falsely claimed as approval fields. Any
  change to the bound assessment, lineage, component revision, or surface invalidates approval;
  a configuration change requires a new assessment and therefore a new approval. No repository
  review is fabricated to satisfy the one-collaborator limitation.
- **Evidence:** approval record/event/hash and wrong/stale/self-approval rejection tests.
- **Dependencies:** S21D3-070.

### S21D3-072 — Activate canary-only routing atomically

- **Deliverable:** VERIFIED-to-ACTIVE activation restricted to the exact canary manifest.
- **Acceptance:** S21D3-058 revalidates bytes immediately before transition; approval and bundle
  preparation match the exact stored assessment and lineage; the resolver accepts only the
  assessment-bound canary configuration hash; active projection exposes only the approved
  component; default activation actors remain empty; non-canary and mandatory paths continue
  deterministic behavior; failure leaves state unchanged.
- **Evidence:** activation/ledger IDs, before/after state, byte-verification receipt, routing
  proof, and restart projection.
- **Dependencies:** S21D3-058, S21D3-071.

### S21D3-073 — Execute the governed canary with stop-first semantics

- **Deliverable:** at least five group decisions over all 20 presealed canary candidate slots.
- **Acceptance:** receipt-aware effective remainder only; learned-first attempts always pass the
  verifier; first acceptance stops further attempts; zero safety regression, integrity error,
  OOD confident error, budget violation, or unstructured fallback; any first failure invokes
  kill switch, disables exactly once with the typed cause and `rollback_permitted=false`, and
  blocks steady state. A failed canary never becomes rollback-permitted later.
- **Evidence:** canary runs/receipts/outcomes, decisions and candidate-attempt denominators,
  latency/call/cost table, and stop trace.
- **Dependencies:** S21D3-072.

### S21D3-074 — Exercise kill switch, disable, and fallback after restart

- **Deliverable:** operational proof that active learned routing can be disabled immediately and
  remains disabled through process/database restart.
- **Acceptance:** after a successful canary, the explicit rehearsal disable records its typed
  cause and `rollback_permitted=true`. After a failed canary, this task reuses S21D3-073's
  existing `rollback_permitted=false` receipt and issues no second disable. Exactly one applicable
  disable receipt exists. Kill switch returns the next decision to deterministic order without
  loading the artifact; disable state replays; health reports disabled/fallback honestly; canary
  receipt remains immutable.
- **Evidence:** reused or newly written disable receipt, receipt-chain audit, before/after hashes,
  timing, restart events, no-artifact-load counter, and fallback output comparison.
- **Dependencies:** S21D3-072; execute after a successful canary or as the first canary-failure
  response.

### S21D3-075 — Prove receipt-selected rollback restoration and refusal

- **Deliverable:** `roll_back()` restoration of the exact prior approved ACTIVE activation chosen
  by the durable receipt chain, plus the failed-canary refusal path.
- **Acceptance:** on a successful real canary, S21D3-074's `rollback_permitted=true` disable is
  followed by `roll_back()`, which accepts no caller-selected target and restores only the exact
  prior D3 canary activation after assessment/approval/lineage revalidation; restart preserves
  that ACTIVE projection. On a failed real canary, a direct service call structurally refuses the
  latest `rollback_permitted=false` receipt and the real component remains disabled; permitted
  restoration is demonstrated only on an isolated scratch component. If the design path never
  opened, use the minimal existing lifecycle fixture. This task is mandatory and is never
  replaced by `not_opened`; the fixture branch exists precisely when no real activation exists.
  No task claims rollback to a nonexistent deterministic/no-component revision, and no evidence
  is deleted.
- **Evidence:** real or scratch rollback receipt, receipt-chain audit, active/disabled projection,
  lineage hashes, restart replay, caller-target refusal, and direct failed-canary refusal.
- **Dependencies:** S21D3-057 implementation on every path; S21D3-074 only when a real activation
  occurred, and the successful-real branch additionally requires S21D3-073 pass.

### S21D3-076 — Promote from canary routing to bounded steady state

- **Deliverable:** switch from the assessment-bound canary config to the already
  assessment-bound bounded steady-state config after successful canary and rollback restoration.
- **Acceptance:** S21D3-075 has already restored the exact approved D3 canary activation; this
  task revalidates its bytes and the S21D3-067 transition condition, then selects only the exact
  prebound steady config hash. It introduces no new configuration, universal coding-agent, or
  other-surface routing. The artifact/assessment/verifier/fallback and approval remain unchanged;
  any byte or config-hash difference requires a second assessment and approval rather than this
  transition. Rollout bound is declared, safety/cost health is monitored, and kill switch remains
  immediate.
- **Evidence:** configuration and activation hashes, scope diff, canary/rollback dependencies,
  and non-target path invariance.
- **Dependencies:** successful S21D3-073 and successful-real S21D3-075 restoration.

### S21D3-077 — Prove final active state and replacement readiness

- **Deliverable:** final lifecycle integrity record for active D3 or negative/not-opened state.
- **Acceptance:** exactly one active revision on the surface; artifact loads after restart;
  assessment/approval/activation/rollback lineage resolves; default-off remains default;
  a staged replacement cannot mutate active state without a new full assessment and approval.
- **Evidence:** lifecycle projection, active pointer/artifact rehash, restart result, replacement
  refusal test, and health output.
- **Dependencies:** S21D3-076.

## EPIC S21D3-E08 — Operations, recovery, CI, and complete validation

### S21D3-080 — Extend existing CLIs narrowly for D3 evidence

- **Deliverable:** read-only commands for revision-3 feature/dataset/campaign/selection,
  corrected OOD counts, retrieval benchmark, lifecycle, integrity, and health; mutating commands
  retain explicit operator intent.
- **Acceptance:** JSON output is canonical and hashable; human output names decision and outcome
  denominators; secrets and credential values never render; wrong/missing D3 environment fails
  before touching development/predecessor stores.
- **Evidence:** CLI golden tests, `--help`, JSON schema checks, and environment-boundary tests.
- **Dependencies:** relevant E02-E07 contracts.

### S21D3-081 — Extend unified integrity and health reporting

- **Deliverable:** D3 integrity report covering explicit member selection, duplicate executions/
  seals, chronology, feature schema, matrix embedding scans, OOD units, holdout access, retrieval
  one-read, artifact bytes, lifecycle, and isolation.
- **Acceptance:** predecessor D2 warnings remain visible; current D3 state distinguishes clean,
  warning, failed, and not-opened; a stored state claiming pass without its evidence fails
  closed; health never claims active when runtime falls back.
- **Evidence:** seeded violation per integrity class and canonical aggregate report.
- **Dependencies:** S21D3-023 through S21D3-077 as applicable.

### S21D3-082 — Verify evidence-database provisioning without broadening authority

- **Deliverable:** documented/tested D3 provisioning route using the existing evidence script.
- **Acceptance:** migration `0015`, role ownership/privileges, extension and schema access pass;
  inherited `postgres_bootstrap_roles.sh` NOSUPERUSER issue is not silently edited; no migration
  `0016`; all operations examples name `COGOS_POSTGRES_ENV_FILE`.
- **Evidence:** provisioning/migration logs and negative wrong-environment test.
- **Dependencies:** S21D3-002.

### S21D3-083 — Prove replay, restart, backup, and isolated restore

- **Deliverable:** full D3 backup/restart/restore evidence for the actual positive or negative
  state.
- **Acceptance:** exact database counts and hashed-row roll-up reproduce; every D3 artifact blob
  rehashes; campaign receipts/resume inputs, explicit datasets, feature/matrix/selection,
  retrieval roots, promotion/lifecycle state, and not-opened records match; predecessor pairs
  remain byte-identical.
- **Evidence:** backup manifest/archive hashes, source/restore comparison, artifact counts and
  hashes, restart projections, and restore command log.
- **Dependencies:** outcome-specific E03-E07 state, S21D3-082.

### S21D3-084 — Exercise corruption, substitution, and isolation failures

- **Deliverable:** a destructive matrix over disposable D3 copies.
- **Acceptance:** covers missing/corrupt/oversized/schema-wrong artifact; metadata/byte
  substitution; feature-seal/campaign-receipt/dataset-member mismatch; OOD unit forgery;
  holdout overlap/access; stale assessment/approval; wrong active revision; retrieval policy or
  judgement substitution; every case fails at the intended or stronger boundary with zero
  predecessor mutation.
- **Evidence:** case table, expected/actual reason, exit status, state-mutation count, and
  before/after fingerprints.
- **Dependencies:** S21D3-081, S21D3-083.

### S21D3-085 — Add focused credential-free CI

- **Deliverable:** CI coverage for v2 normalization/matrix/dataset/OOD, receipt resume, RRF/
  benchmark, artifact verification, lifecycle, and D3 evidence schemas using synthetic/local
  fixtures.
- **Acceptance:** no live provider, network, API key, subscription, GPU, or predecessor store;
  deterministic CPU bounds; no duplicate required context; repository language/security/schema
  checks include new files.
- **Evidence:** workflow diff, local invocation, expected duration/resource estimate, and CI
  fixture provenance.
- **Dependencies:** implemented E02-E08 surfaces.

### S21D3-086 — Run the complete release matrix on scratch authorities

- **Deliverable:** `evidence/sprint-21d3-verification-matrix.json` with every row expected before
  release.
- **Acceptance:** includes formatting/lint, unit/full suites, schema export, language, secrets,
  dependency audit, packaging/editable install, focused correction/retrieval/lifecycle slices,
  PostgreSQL integration/migration, benchmark replay, corruption/isolation, backup/restore,
  restart, and outcome-specific gate checks. Negative rows must fail for their expected reason;
  none are silently skipped.
- **Evidence:** command, environment, duration, expected/actual exit, log hash, and pass/fail/skip
  totals for every row.
- **Dependencies:** S21D3-083 through S21D3-085.

## EPIC S21D3-E09 — Documentation, gate, protected release, and handoff

### S21D3-090 — Update architecture and operator documentation

- **Deliverable:** correction-ranking and Experience Graph operations/architecture updates.
- **Acceptance:** documents v2 feature semantics, removed channels, matrix scans, explicit dataset
  identity, corrected OOD units, fresh campaign/resume, retrieval RRF/policy, final access,
  artifact verification, lifecycle commands, environment file, stop/negative paths, and exact
  store isolation. No future capability is described as implemented.
- **Evidence:** repository links, command examples tested against D3 scratch state, language
  check.
- **Dependencies:** implemented outcome-specific behavior.

### S21D3-091 — Prepare a versioned pre-release D3 Gate L2 assessment

- **Deliverable:** `gate-l2-d3-assessment.md` or another explicit versioned successor that does
  not overwrite the D2 historical assessment.
- **Acceptance:** all 29 conditions and D1 6/7/15 mapped to exact D3 evidence; carried/retested/
  failed/not-opened distinguished; denominator correction visible; current state is provisional
  until protected merge, post-merge CI, and tag verification.
- **Evidence:** condition table with hashes and no unsupported pass.
- **Dependencies:** S21D3-046, outcome-specific S21D3-063 through S21D3-086.

### S21D3-092 — Complete the Sprint 21D3 report

- **Deliverable:** `sprint-21d3-report.md` describing goal, intervention, data, results,
  incidents, deviations, limitations, gate verdict, stores, operations, and release route.
- **Acceptance:** exact denominators and hashes; D2 reconciliation retained; negative results
  and non-applicable cases not hidden; calibration never described as final benefit; no
  universal-model claim; release handles deferred to external release evidence where necessary.
- **Evidence:** links to every canonical D3 artifact and local matrix.
- **Dependencies:** S21D3-086, S21D3-091 draft.

### S21D3-093 — Prepare the outcome-specific handoff

- **Deliverable:** a provisional outcome-specific handoff: on pass, Sprint 22A; on failure, a
  bounded D4/remediation handoff. S21D3-095 adds the final remote release handles.
- **Acceptance:** positive handoff names exact Gate L2 and D1 closure plus active component;
  negative handoff names first stop, what remains valid, spent/unopened evidence, exact next
  experiment, and why Sprint 22A remains blocked. Neither path pre-authorises new dependencies.
- **Evidence:** handoff link and outcome-condition hash.
- **Dependencies:** S21D3-091, S21D3-092.

### S21D3-094 — Complete the protected implementation release

- **Deliverable:** final branch commits, non-draft PR, all required PR checks, squash merge
  without protection bypass, successful exact-head post-merge `main` CI, and the one permitted
  annotated outcome tag created only after that CI.
- **Acceptance:** clean diff; no unrelated/user changes overwritten; 27 required contexts and
  `enforce_admins` unchanged; one-collaborator limitation recorded; failures are diagnosed from
  logs and an unchanged-head infrastructure failure is rerun before code changes. The success
  tag is permitted only when conditions 1–28 and every pre-release part of condition 29 pass
  with bounded active state; every other valid release uses only the D3 negative tag.
- **Evidence:** PR/head/merge SHA, check list, merge method/time, post-merge run and 30/30 (or
  then-current complete required set) result, protection re-read, tag annotation/object/peeled
  SHA and first remote verification.
- **Dependencies:** S21D3-086, S21D3-090 through S21D3-093.

### S21D3-095 — Complete gate-close release evidence and remote verification

- **Deliverable:** remote-derived final D3 assessment/release JSON in a protected gate-close
  documentation PR, followed by its exact-head post-merge `main` CI and final remote re-read.
- **Acceptance:** S21D3-094 used `sprint-21-learning-baseline` only if every Gate L2 condition
  from 1 through 28 passed, every pre-release part of condition 29 passed, and bounded active
  state existed; otherwise it used `sprint-21d3-evidence-baseline`. S21D3-095 itself closes the
  remaining remote-verification and gate-close parts of condition 29.
  The gate-close PR records real PR/CI/tag handles without moving the tag; local/remote tag
  objects match and peel to the implementation-release commit; current `origin/main` contains
  the later gate-close commit; success-tag absence is asserted on the negative path; protection
  remains unchanged; the provisional S21D3-093 handoff is finalised with these remote handles.
- **Evidence:** final release manifest, gate-close PR/head/merge and CI, immutable tag
  annotation/object/peeled SHA, `ls-remote`, current `origin/main`, protection/gate re-read, and
  final handoff link.
- **Dependencies:** S21D3-094.

---

## 6. Execution waves and dependencies

| Wave | Tasks | Exit |
|---|---|---|
| W0 — authority and design | 000–018 | current baseline, reconciled D2 facts, isolated roots, revision 3 committed before measurement |
| W1 — invariant spine | 020–028 | v2 encoder, full-matrix scans, dataset identity, corrected OOD units, receipt safety, diagnostic decision |
| W2 — fresh correction evidence | 030–032, 033, 034–039 | authored/replacement roles sealed first, then vertical slice, 200/50 fitting, 80/20 calibration, 100+ fresh cases, one candidate or null |
| W3 — independent retrieval | 040–047 | fixed RRF, corrected benchmark, 50+ unseen queries, D1 condition-15 decision |
| W4 — artifact and runtime | 048, 050–055, 057, 056, 058–059 | promotion contract, offline loader, verification implementation before real SHADOW registration, then one pre-final access decision or bound not-opened chain |
| W5 — final evidence | 060–069 | final A/B, benefit, retention, promotion OOD, shadow, assessment, VERIFIED or negative stop |
| W6 — governed activation | 070–077 | exact approval, canary, kill switch, restart, rollback, bounded active state; otherwise not opened |
| W7 — operations | 080–086 | CLI/health, isolated recovery and corruption proofs, complete local matrix |
| W8 — release | 090–095 | outcome report/assessment/handoff, protected implementation release, tag, gate-close release record |

The two experiment branches are deliberately independent after W0:

```text
revision 3
  +-> invariant correction feature -> fresh self-play -> candidate -> final -> lifecycle
  |
  +-> fixed retrieval RRF -> distinct unseen holdout -> D1 condition 15

both branch verdicts + operations -> Gate L2 outcome -> protected release
```

A correction stop does not cancel the already pre-registered retrieval branch; closing D1
condition 15 remains useful evidence. A retrieval failure does not authorise correction
activation, but the frozen correction final experiment may finish so its result is not lost.
No branch may tune itself from the other branch's holdout.

### 6.1 First vertical slice

Before bulk campaigns, S21D3-033 must prove:

1. one rights-clean four-candidate task package;
2. canonical candidate-source v2 bytes and named scalar/embedding channels;
3. pre-outcome feature seal and exact receipt-bound self-play execution;
4. independent hidden-verifier labels and role-bound observation projection;
5. feature- and selection-sensitive explicit dataset identity;
6. full fitted-matrix scanning, including embedding dimensions;
7. one k-NN ranking, abstention, baseline fallback, and canonical v2 artifact reload;
8. receipt-aware stop-on-first-accept and exact missing-outcome resume;
9. wrong/corrupt artifact fallback, restart/replay, backup/restore;
10. final/retrieval capabilities refusing access.

This slice uses a dedicated synthetic fixture group outside every D3 campaign role. It spends
no fresh calibration case, correction final member, canary member, or retrieval judgement.

### 6.2 Pull-request and release strategy

Use one coherent implementation PR by default. A small pre-registration-only PR is allowed only
if campaign execution must begin from protected authority; it must merge before any number it
governs is measured. Do not split final evidence into an ungoverned artifact PR.

The release sequence has two protected documentation states:

1. implementation/evidence/report/provisional-assessment PR merges;
2. exact-head `main` CI passes;
3. create and push the one permitted annotated outcome tag at that release commit;
4. from current `main`, add remote-derived release JSON and final assessment handles in a
   gate-close documentation PR;
5. merge the gate-close PR under unchanged protection and wait for its post-merge `main` CI;
6. re-read `origin/main`, the immutable tag object/peeled commit, both CI runs, and protection.

The gate-close commit is expected to be newer than the tag, as in D2. It must not move or
recreate the annotated tag. The next sprint branches from the verified current `origin/main`
while treating the tag as immutable release evidence.

---

## 7. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| release baseline | D2 tag object/peel, current main, two PR/CI chains, protection, migration, collaborator | wrong or unprotected parent |
| D2 reconciliation | decision/outcome units and computed retrieval replay | D3 is built on false denominators |
| store isolation | development/C3/D1/D2 fingerprints unchanged | predecessor evidence contaminated |
| revision chronology | revision 3 predates diagnostic, code measurement, campaigns and retrieval score | intervention chosen after results |
| diagnostic isolation | D2 cases are development-only and cannot enter selection | failed probe became tuning target |
| feature invariance | canonical source/vector/ranking equality under declared equivalent transforms | encoder still learns spelling/context noise |
| semantic sensitivity | operator/condition mutation changes canonical representation | normalizer erased task meaning |
| complete matrix scan | scalar and all embedding dimensions pass validity/leakage scans | hidden fitted channel escaped audit |
| dataset identity | feature, partition, campaign, role and explicit member digest bound | stale D2/v1 dataset silently reused |
| data roles | exact fitting/calibration/final/canary/retrieval manifests and transitive groups | fitting/evaluation overlap |
| chronology | v2 features and final predictions predate corresponding outcomes | post-outcome leakage |
| campaign resume | manifest/mode/order/bundle/seal bound; only exact missing work repeats | restart fabricates or duplicates evidence |
| sample | 200/50 fit, 80/20 calibration, 120/30 each final, 5/20 canary | underpowered or role-ineligible result |
| OOD units | decisions equal answered plus abstained; outcomes separate | candidate slots inflate safety sample |
| calibration non-silence | clean/equivalence coverage and action-preservation floors | abstention passes by avoiding the test |
| final access | one setting/artifact frozen before any final body/outcome access | holdout selected the model |
| baseline/learner ladder | strongest honest deterministic rung and all 24 k-NN settings | straw baseline or hidden tuning |
| artifact | canonical inert JSON and exact v2 lineage | model cannot be reproduced safely |
| runtime resolver | durable/config/artifact/model agreement with named fallback | active claim differs from actual runtime |
| verifier boundary | learned order only; every attempted candidate independently verified | learner gained acceptance authority |
| final benefit | 20 changes, fixed effect threshold, two batches, positive paired lower bound | usefulness claim unsupported |
| safety/retention | zero critical regression and fixed domain/aggregate bounds | catastrophic forgetting or unsafe ordering |
| promotion OOD | 100+ actual decisions, exact units, zero promotion confident errors | invariant/safe action unsupported |
| shadow | zero executed changes and verifier-only outcome links | shadow mutated behavior |
| retrieval policy | explicit revision-2 hash and full resource/quality metrics | benchmark measured another policy |
| retrieval usefulness | 50+ disjoint unseen queries and one arm at both floors | D1 condition 15 remains open |
| lifecycle verification | focused assessment-bound VERIFIED transition and activation-time byte rehash | generic advance or stale artifact bypass |
| approval | exact eligible human approval, no self-approval | component/provider authorised itself |
| canary | exact subset, receipt-safe stop-first, verifier, first-failure stop | activation unbounded or decorative |
| kill switch/rollback | exactly one cause-bound disable, restart fallback, receipt-selected restoration, and failed-canary direct-call refusal | learned behavior cannot be stopped/recovered safely |
| recovery | database/artifact/receipt/dataset/lifecycle exact restore | evidence is ephemeral or split-brain |
| release | complete local matrix, protected PRs, exact-head CIs, immutable remote tag | result is not release-grade |

### 7.1 Required local command classes

Use the repository's locked environment and record exact commands, duration, exit status, and
log hash. At minimum the final matrix includes equivalents of:

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run ruff check --config ruff.cognitive-os.toml src tests scripts infra
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run ruff format --check --config ruff.cognitive-os.toml src tests scripts infra
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run pytest -q
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run python -m cognitive_os.schemas.export --check
./scripts/check_repository_language.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/run_postgres_integration_tests.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/verify_distribution.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/verify_editable_install.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run pip-audit
git ls-files -z | xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline
```

The D3 verification matrix must add focused correction-ranking, OOD-unit, retrieval,
lifecycle, recovery, and negative-boundary rows. Live providers and credentials are not a
release dependency.

---

## 8. Quantitative acceptance thresholds

### 8.1 Dataset and separation

- fitting: exactly the selected 50 groups and 200 new `SELF_PLAY` outcomes;
- calibration: 20 fresh groups and 80 new `SELF_PLAY` outcomes;
- final A and B: exact reused 30 groups/120 outcomes each, or a fully replaced role at no less
  than the same target; never below 25/100;
- canary: exact 5 groups and 20 sealed candidate slots;
- retrieval: overproduce at least 60 groups until at least 50 qualifying unseen queries remain;
- zero `REAL_GOVERNED_RUN` observation in fitting or calibration;
- zero task/repository/template/source/near-duplicate group crossing any role;
- zero final/canary outcome or prediction access before S21D3-059;
- 100% source-rights, manifest-member, artifact, feature, and verifier resolution;
- exact explicit members only; surface totals and latest seals are never dataset selectors.

### 8.2 Feature and calibration invariance

- 100% byte/hash equality for canonical candidate source and fitted vector under coherent
  identifier rename;
- 100% feature equality under issue-only, test-only, and baseline-only reorder cases because
  those inputs are excluded from v2;
- 100% detection of seeded unstable/label-perfect embedding dimensions;
- at least 100 fresh calibration metamorphic ranking decisions and 400 candidate outcomes;
- clean coverage at least 0.80;
- equivalence coverage at least 0.80 and no more than 0.05 below clean coverage;
- 100% first-action preservation for covered clean/transformed pairs;
- exactly zero confident equivalence/OOD errors for selection;
- at least one changed clean action and clean first-choice rate strictly above the strongest
  deterministic baseline;
- all 24 settings reported, including filtered and abstaining settings.

### 8.3 Learned material benefit

- at least 20 final group decisions differ from the strongest deterministic baseline;
- at least +5 percentage points absolute first-choice verified success or at least 20% relative
  error reduction;
- paired group bootstrap seed 21041, 2,000 resamples, 95% lower bound above zero;
- learned-minus-baseline direction strictly positive in final A and final B;
- all abstentions execute baseline order and remain in every relevant denominator;
- malformed, timeout, verifier-failed, and no-accepted-candidate tasks stay visible;
- latency, verifier/provider call counts, failures, and zero/actual costs use exact denominators.

### 8.4 Retention, OOD, and authority

- zero accepted-to-rejected safety, governance, permission, secret, or destructive-action case;
- no retained domain loses more than 2 absolute points;
- aggregate verified success loses no more than 1 absolute point;
- at least 100 final metamorphic/OOD ranking decisions over at least ten groups;
- 120 nominal cases over twenty manifest-ordered eligible final groups provide the reserve;
- report false-confident rate at most 1%; promotion exactly zero confident errors;
- errors reported both over all decisions and over answered decisions;
- shadow changes zero executed decisions;
- every learned-first correction still passes the independent verifier;
- missing/corrupt/oversized/wrong/inactive/disabled/unapproved cases fall back immediately;
- zero model/provider approvals and zero online updates to active exemplars or thresholds.

### 8.5 Retrieval

- at least 50 new unseen-task queries, wholly disjoint from correction roles and D1/D2 queries;
- at least one bounded arm reaches Recall@5 `>= 0.70` and MRR@10 `>= 0.50`;
- nDCG@10, coverage, candidates, p50/p95/max, timeouts, and cutoffs also reported;
- repeated-ranking agreement 100%; at most 10 returned results;
- graph limits: 64 nodes, 128 edges, depth 32, shortlist 20, per-GED comparison 90 ms under
  revision 2, total query budget/p95 at most 2 seconds;
- no silent timeout, cutoff, query drop, judgement read, or rerun after metrics are known;
- RRF constant 60 and equal lexical/vector weights never tuned.
- lexical and MiniLM ranks are computed over the full eligible pool, zero-score lexical documents
  are absent, and output is truncated once after fusion.

### 8.6 Release and persistence

- migration remains `0015` unless a separately approved measured gap justifies `0016`;
- 100% stored metadata/hash/size and recomputed artifact-byte agreement;
- exact backup/restore database counts, hashed-row roll-up, all D3 artifact hashes, campaign
  receipts, explicit datasets, retrieval roots, and outcome-appropriate lifecycle state;
- zero writes to development/C3/D1/D2 pairs;
- every verification-matrix row reaches its predeclared expected status; no hidden skip;
- every required PR check and both post-merge `main` CI runs succeed;
- exactly one outcome tag: success `sprint-21-learning-baseline`, otherwise
  `sprint-21d3-evidence-baseline`; local and remote annotated objects match.

---

## 9. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| intervention chosen after diagnosis | revision 3 clock follows any per-channel number | invalidate measurement, publish negative chronology failure, restart only in successor revision |
| D2 probe reused for selection | any D2 OOD case affects D3 candidate/threshold | invalidate selection and final access; create a successor fresh calibration set |
| decision inflation | candidate slots reported as ranking decisions | fail contract validation; recompute without changing outcomes |
| safety by silence | zero/near-zero equivalence coverage survives | filter setting under fixed Section 2.3 rules |
| superficial rename fix | only a production-generated probe or one fixture is canonical | compare the production authority against the independent generator and hard-coded pairs; fail exact production-vector property |
| meaning erased | semantic operator/condition mutation canonicalises identically | stop with `feature_boundary_wrong`; do not fit |
| hidden embedding leakage | matrix audits only scalar names or a seeded embedding oracle passes | stop before campaign selection and repair matrix validation |
| stale dataset reuse | v1 dataset returned for v2 members or role | refuse identity mismatch; no migration, create v3 explicit identity |
| post-outcome re-encoding | v2 feature seal follows any selected outcome | projector refuses; rerun new self-play only after a valid seal |
| duplicate surface selection | query selects all observations/latest seal | reject builder call; require canonical explicit list |
| final reuse compromised | S21D3-004 catalogue/root/access audit fails | mark the whole role for replacement; author after S21D3-018 and seal by S21D3-032 before measurement |
| protected final fails after seal | body/feature mismatch or insufficient eligible promotion cases after S21D3-032 | stop the final branch; do not substitute members after access |
| correction/retrieval overlap | shared group, clone, task signature, source or judgement | rebuild manifests before either holdout opens |
| retrieval tuning | alternate weight/constant/arm/width after development or final score | invalidate retrieval result; defer alternative to successor |
| wrong graph policy | benchmark uses revision-1 defaults or unverified hash | fail run before query resolution |
| resume re-executes work | receipt hash/mode/order mismatch or ordinary remainder schedules left-alone IDs | refuse resume and repair receipt boundary before campaign |
| stale artifact at activation | bytes/metadata differ after assessment/approval | activation atomically refuses and remains deterministic |
| generic VERIFIED bypass | generic state advance reaches VERIFIED/ACTIVE | block transition in service and require focused verification |
| verifier authority drift | learned prediction accepts or skips hidden verification | fail gate immediately; disable active path if reached |
| reviewer fiction | model/provider or fabricated second collaborator approves | reject record; keep repository approval requirement unset and document reality |
| predecessor contamination | any D3 write changes development/C3/D1/D2 fingerprint | stop destructive work, preserve evidence, diagnose from isolated copy |
| speculative complexity | new migration/dependency/model/database without measured ADR | remove/defer; use existing authority or record successor need |
| incomplete negative path | downstream task absent without stop-bound record | sprint not done; materialise typed not-opened chain |
| premature tag | tag created before exact-head implementation CI | do not move it; publish a new correctly named release only under explicit recovery plan |

---

## 10. Stop, rollback, and failure decisions

### 10.1 Before fresh campaigns

- Baseline, reconciliation, isolation, pre-registration chronology, final-reuse, grouping, or
  feature-boundary failure stops correction execution.
- A diagnostic outside the pre-registered response produces `fail_and_stop`; no second feature
  revision opens inside D3.
- Independent retrieval may continue if its own revision, groups, authority, and stores remain
  valid.

### 10.2 Before correction final access

- Any matrix, dataset, feature chronology, calibration, coverage, action-preservation, OOD,
  artifact, loader, resolver, invariance, SHADOW, or checkpoint failure records one null and
  leaves final A/B/canary unopened.
- No parametric rung or threshold revision opens. A capacity residual becomes D4 input.
- Retrieval continues independently; its result does not authorise correction final access.

### 10.3 After correction final or retrieval holdout access

- Any change to selected candidate, artifact, feature, threshold, baseline, metrics, resource
  policy, manifest, judgement, or member invalidates the affected experiment.
- Final B runs after A only under the frozen protocol, never to choose a repair.
- Any aggregate, per-batch, bootstrap, safety, retention, OOD, shadow, retrieval, or evidence
  failure keeps Gate L2 closed and forbids approval/activation.
- The outcomes remain immutable evaluation evidence. A successor requires a new revision and
  new untouched holdout; D3 final data never becomes fitting data.

### 10.4 After activation

- First canary safety, integrity, budget, OOD, artifact, verifier, or receipt failure triggers
  immediate disable and deterministic fallback.
- A failed canary cannot be restored through rollback; only a previously approval-bound valid
  state is eligible.
- Missing/corrupt/stale bytes or configuration mismatch fall back without an operator round
  trip.
- Rollback deletes no evidence and must survive restart/restore.

---

## 11. Definition of Done

### 11.1 Required for every outcome

Sprint 21D3 is complete only when:

- S21D3-000 through S21D3-018 establish current authority and revision 3 before any D3
  candidate/development/holdout measurement; immutable predecessor reconciliation is retained as
  the declared baseline exception;
- D2 denominator/retrieval discrepancies are reconciled without rewriting protected history;
- every predecessor store is unchanged and D3 recovery uses isolated authorities;
- every opened experimental role uses exact members, feature/schema/partition-aware identity,
  transitive group separation, pre-outcome seals, and complete scalar/embedding scans;
- both independent branches reach a hash-bound result or a valid first-failure result;
- every dependent conditional task has completed evidence or a transitive typed `not_opened`
  record; baseline, S21D3-075 lifecycle fixture, operations, report, gate, and release tasks are
  never not opened;
- all applicable unit, integration, PostgreSQL, recovery, corruption, packaging, schema,
  security, language, and deterministic CI checks pass;
- one outcome-specific report, versioned D3 assessment, and exact handoff exist;
- the protected implementation and gate-close PRs merge without weakened controls;
- exact-head post-merge `main` CI succeeds after both merges;
- exactly one permitted annotated tag is verified locally and remotely against its immutable
  implementation release commit.

### 11.2 Additional positive-path requirements

Gate L2 passes only when:

- diagnostic applicability, v2 exact invariance, full matrix scans, 200/50 fitting and 80/20
  fresh calibration all pass;
- one k-NN setting clears clean, non-silence, metamorphic, and OOD rules and one reproducible v2
  artifact is selected before final access;
- final A/B each contain 120 new real-run outcomes over 30 groups, at least 20 decisions change,
  material benefit and paired interval pass, and direction is positive in both batches;
- safety, retention, 100+ decision promotion OOD, shadow, artifact/fallback, and all fixed
  authority conditions pass;
- at least one frozen retrieval arm passes both floors on 50+ distinct new queries;
- the component follows REGISTERED -> SHADOW -> VERIFIED through evidence-bound verification;
- an eligible human approves the exact existing contract fields, binding artifact/config bytes
  transitively through assessment and lineage, and activation revalidates those bytes;
- canary, kill switch, restart, disable, valid restoration, rollback rehearsal, bounded steady
  state, and final active projection pass;
- Gate D1 conditions 6, 7, and 15 close and `sprint-21-learning-baseline` is the verified tag;
- only after the gate-close PR and CI does the handoff unblock Sprint 22A.

### 11.3 Valid negative-path completion

A negative D3 is complete when:

- the first failed pre-registered condition and every opened result are immutable;
- no forbidden downstream correction or retrieval data was opened after its stop;
- all dependent tasks carry typed `not_opened` evidence bound to that stop hash;
- the independent branch was completed when still valid, so useful D1 evidence is not discarded;
- applicable fixture/local/operations/recovery/security/CI checks pass;
- no failed component remains active; any approval and activation history created before a
  canary/restart/post-activation failure is preserved, the failed path is disabled, and a failed
  canary is structurally non-restorable; the success tag does not exist;
- `sprint-21d3-evidence-baseline` is annotated once after successful implementation CI and
  verified remotely;
- the final D3 assessment says Gate L2 does not pass, preserves unresolved D1 conditions, keeps
  Sprint 22A blocked, and hands off the smallest evidence-backed successor experiment.

A green PR without either the complete positive release or this complete negative release is a
checkpoint, not Sprint 21D3 completion.

---

## 12. Expected deliverables

At minimum:

- this backlog plus aligned D3 handoff, development plan, and execution allocation;
- D3 baseline, D2 reconciliation, predecessor inventory, store-isolation, and final-reuse
  eligibility records;
- revision-3 ranking/OOD, feature, dataset/group, power, transformation, retrieval, gate, and
  stop manifests;
- production identifier normalization with an independent perturbation oracle,
  `correction-ranking-v2`, named full-matrix audits,
  feature-sensitive explicit dataset identity, unit-correct OOD contracts, and receipt-safe
  resume;
- D2 per-channel diagnostic and applicability/stop record;
- on the opened correction path, 200/50 fitting and 80/20 fresh calibration outcomes, 100+
  fresh calibration metamorphic decisions, full ladder/grid, and one selection or null;
- one fixed lexical+MiniLM RRF arm, corrected benchmark tooling, a distinct 50+ query holdout,
  and a D1 condition-15 result on every valid path;
- on the candidate path, canonical v2 artifact, verified loader/resolver/sequencer, invariance,
  REGISTERED/SHADOW state, focused verification, and pre-final checkpoint;
- on the final path, 120/30 final A and 120/30 final B outcomes, paired benefit, retention,
  100+ promotion OOD decisions, shadow, promotion assessment, D1 mapping, and VERIFIED state;
- on the positive path, exact activation bundle, human approval, canary, kill switch, restart,
  restoration, rollback, bounded steady state, and final active projection;
- on every path, canonical not-opened records for every inapplicable conditional deliverable;
- updated correction-ranking and Experience Graph operations/architecture, CLI, integrity,
  health, provisioning, backup/restore, corruption/isolation, focused CI, and complete local
  verification matrix;
- outcome-specific D3 report, versioned Gate L2 assessment, handoff, protected implementation
  and gate-close release evidence, and one remotely verified annotated tag.
