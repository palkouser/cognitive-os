# Sprint 21D4 Technical Backlog

## Selective Correction Ranking, Searchable-Surface Retrieval, and Gate L2 Closure

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution once the D3 release exists
- **Revision:** 1
- **Prepared:** 2026-08-05
- **Required predecessor release:** `sprint-21d3-evidence-baseline`, a negative release
- **Required predecessor tag object:** not yet created — see Section 1.0
- **Required predecessor implementation PR:** `#221`, draft at planning time
- **Required predecessor PR-head CI:** `31030347888`, success, 30 of 30 jobs on `a663bbc5bdba`
- **Planning head at preparation:** `origin/main` at
  `9fe03cea3975e81bbae57b870e7bc50d8cc29f49`, still the D2 gate-close commit
- **Required parent migration head:** `0015`
- **Implementation branch:** `feature/sprint-21d4-selective-correction-ranking`
- **Planned migration:** none
- **Next available migration:** `0016`, unallocated unless a measured durable-authority gap
  cannot be represented by the existing learned ledgers, Event Store, and Artifact Store
- **Success-path baseline tag:** `sprint-21-learning-baseline`
- **Negative-path evidence tag:** `sprint-21d4-evidence-baseline`
- **Stage gates:** Gate D1 conditions 6, 7, and 15; Gate L2
- **Execution profile:** local, CPU-first, single maintainer, credential-free normal CI,
  no live-provider, network, credential, or GPU dependency
- **Repository language:** English only
- **Planned new dependencies:** none
- **Planned new models, services, databases, or authorities:** none

---

## 0. Authority and execution contract

This backlog is the implementation authority for Sprint 21D4. It refines:

- [Sprint 21D3 report](sprint-21d3-report.md);
- [Sprint 21D4 handoff](sprint-21d4-handoff.md);
- [Gate L2 assessment (D3)](gate-l2-d3-assessment.md), which remains the immutable D3
  assessment rather than the D4 result;
- [Sprint 21D3 execution log](sprint-21d3-execution.md);
- the annotated `sprint-21d3-evidence-baseline` release, once it exists;
- [Sprint 22 development plan](../sprint-22/development-plan.md);
- [execution sprint allocation](../sprint-22/execution-sprint-allocation.md).

D4 is the closing remediation sprint for Gate L2. It changes no encoder, adds no learner
family, adds no dependency, and adds no migration. It changes three things: **what a decision
is counted as**, **how many independent decisions exist**, and **what a retrieval arm is
allowed to read**. Every other surface D4 needs was built and proven in D3 against a contract
fixture and is now exercised against a real candidate for the first time.

If implementation evidence contradicts this backlog, preserve evaluation separation,
independent-verifier authority, deterministic fallback, exact artifact lineage, and reversible
activation. Record the conflict and the smallest resolution before any affected holdout is
opened. Do not silently reinterpret a denominator, replace a sealed member, or tune against a
failed holdout.

### 0.1 Release-grade meaning of done

D4 is not complete when the calibration set is larger, a threshold is derived, retrieval
improves on a development set, or a PR turns green. Section 11 defines two valid outcomes.
Every outcome requires:

1. revalidation of the D3 tag, current `origin/main`, both D3 PR chains, branch protection,
   migration head, collaborator state, and all five predecessor Artifact Store pairs;
2. a non-destructive D3 evidence-reconciliation record that fixes no historical bytes but
   establishes the authoritative decision-independence denominators;
3. pre-registration revision 4 published before any new calibration measurement, any
   threshold derivation, any fresh campaign, and any retrieval score;
4. a fresh, group-disjoint calibration set large enough that **at least 100 decisions are
   independent** rather than replicated, and a fresh retrieval holdout D3 never scored;
5. exactly one selected candidate — a frozen k-NN setting plus one calibration-derived
   selective operating point — or a hash-bound null, fixed before any final outcome is
   accessible;
6. one widened searchable surface, frozen before the retrieval holdout is resolved, and every
   arm evaluated once;
7. either every fixed Gate L2 condition passing followed by the existing governed lifecycle,
   or the first failed pre-registered stop condition followed by complete `not_opened`
   evidence for dependent work;
8. isolated PostgreSQL and Artifact Store recovery evidence, complete local validation,
   protected PR merge, successful exact-head post-merge `main` CI, and one annotated remotely
   verified outcome-specific tag;
9. a D4 report, a versioned D4 Gate L2 assessment, and an outcome-specific handoff that
   either unblocks Sprint 22A or states precisely what still blocks it.

Final PR, merge, CI, and tag identities belong in the annotated tag or external release
evidence rather than as self-referential claims inside the implementation commit.

### 0.2 Efficiency-first implementation rule

D3 built and proved an entire promotion, artifact, runtime, verification, activation and
operations surface and then refused to use it, because no candidate existed. **D4's default
is to exercise that surface, not to extend it.** Use, in order:

1. the released D3 contracts: `correction-ranking-v2` and its alpha-normaliser, the fitted
   matrix scans, explicit dataset identity, receipt-aware resume, the versioned promotion
   payload and evaluator, `CorrectionArtifactPayloadV2`, the direct evaluation boundary, the
   hardened runtime resolver, `verify_component()`, activation-time byte revalidation, the
   eleven-class integrity report, the corruption matrix, and the release matrix;
2. the Python standard library and already locked dependencies;
3. one arithmetic selective-threshold rule over the existing k-NN confidence score,
   derived from the calibration split by quantile — not a second learner;
4. one additive, hash-neutral field on the existing `ActionDecisionGraph`;
5. a successor sprint only if the D4 residual proves a need for a different hypothesis class.

D4 must not add by default:

- migration `0016`, a new database engine/service/authority, graph database, vector database,
  event authority, or model server. A new isolated logical database in the existing PostgreSQL
  authority remains required for D4 evidence;
- a new feature contract, encoder revision, normaliser revision, or embedding model.
  `correction-ranking-v2` and hash `492c90a5df420de9…` are **unchanged in D4**;
- logistic regression, SGD, a tree, a GNN, an FGW implementation, a GPU path, or a live
  provider;
- a second activation state machine, a generic threshold service, or a calibration framework;
- a pickle, joblib, arbitrary-object, or executable-artifact loader;
- automatic acceptance of a correction based on a learned score;
- deletion or reinterpretation of D3's immutable stops.

### 0.3 Evidence-role boundary

| Evidence | Permitted D4 use | Prohibited use |
|---|---|---|
| D3 fitting task packages (50 groups) | re-execution under revision 4 as part of the enlarged fitting pool | calibration, threshold choice, final claim |
| D3 calibration task packages (20 groups) | **re-executed as fitting exemplars only**, declared in revision 4 before any D4 number | any D4 selection, threshold, or coverage decision |
| D3 calibration metamorphic set | frozen replay for the independence erratum and invariance regression | D4 candidate selection, threshold choice |
| D3 retrieval holdout and query set | read-only diagnosis of the searchable-surface cause | any D4 retrieval score or floor decision |
| D2 and D1 development evidence | historical comparison only | any D4 decision |
| D4 `SELF_PLAY` fitting campaign | fitting after rights, chronology, and leakage checks | final benefit claim |
| fresh D4 calibration set (100 groups / 400 outcomes) | k, threshold, and operating-point selection before final access | fitting exemplars, refit after selection or final access |
| correction final A `REAL_GOVERNED_RUN` | first independent final comparison | training, calibration, feature or threshold revision |
| correction final B `REAL_GOVERNED_RUN` | independent confirmation | training, calibration, feature or threshold revision |
| new unseen-task retrieval holdout | one final comparison of frozen retrieval arms | correction selection, retrieval tuning, weight selection |
| canary `REAL_GOVERNED_RUN` | bounded post-approval runtime proof | fitting or replacement of final evidence |

Every row above names a task package, not a stored observation. D4-W0-F1 established that the
D3 learned store holds no observations and no datasets, so nothing is inherited in place and
every exemplar is produced by a campaign D4 runs itself under new run identities after fresh
feature seals.

Promoting D3's and D2's spent calibration groups to D4 fitting exemplars is permitted **only**
because they are declared as fitting in revision 4 before any D4 measurement, and because D4's
own selection reads a calibration set those groups are transitively disjoint from. A D4 snapshot
must name every included observation and feature record. Queries such as "all observations on
this surface" or "latest seal for this partition" remain invalid evidence selection.

### 0.4 Negative-result and no-retuning rule

Publish a negative D4 result and keep Gate L2 closed when the first applicable condition below
occurs:

- the enlarged calibration set does not yield at least 100 independent ranking decisions;
- no frozen k-NN setting at any pre-registered selective operating point clears the fresh
  calibration, non-silence, and metamorphic rules;
- the selected operating point's coverage cannot support at least 20 changed final decisions;
- no retrieval arm clears both fixed usefulness floors on the new retrieval holdout;
- final benefit, paired interval, independent-batch direction, safety, retention, promotion
  OOD, shadow, budget, artifact, approval, canary, restart, disable, or rollback evidence fails;
- an authority, chronology, leakage, overlap, body-access, hash, or recovery invariant fails.

After the fresh calibration set is resolved, D4 may not change the feature contract, the grid,
the operating-point rule, the eligibility rule, the baseline, or calibration membership. After
candidate selection, no fit, refit, threshold change, artifact replacement, or final-manifest
change is allowed. Final B confirms final A; it is not a repair set. The retrieval holdout is
read once after every arm, surface field, and resource limit is hash-bound.

A negative release uses `sprint-21d4-evidence-baseline`; it creates no success tag and does not
unblock Sprint 22A. Dependent items must have a typed `not_opened` record bound to the first
failed decision, not merely a sentence in the report.

---

## 1. Verified starting state and reconciliations

### 1.0 D4 is blocked until D3 is released

At preparation, `origin/main` is `9fe03cea3975e81bbae57b870e7bc50d8cc29f49` — the **D2**
gate-close commit. `sprint-21d3-evidence-baseline` does not exist, PR `#221` is a draft, and
the D3 branch is 19 commits ahead of `main` at `4e4fa76d4649f9621e1d667ad6f53ea8be5eb3f9`.
S21D3-094 and S21D3-095 are held for an explicit release decision.

**S21D4-000 cannot pass until they complete.** D4 W0 is blocked on:

1. S21D3-094 — protected merge of `#221` into `main` and its exact-head post-merge CI;
2. S21D3-095 — the annotated `sprint-21d3-evidence-baseline` tag, pushed and remotely verified,
   plus the D3 gate-close documentation PR and its post-merge CI.

D4 must not branch from the unmerged D3 feature branch. Branching from an untagged branch would
make D4's parent unverifiable and would break the chain every predecessor sprint established.
If the release decision is instead to abandon the D3 branch, this backlog is void and a new
baseline must be established first.

### 1.1 Exact release state expected at D4 W0

| Item | Required value |
|---|---|
| Planning head | `origin/main` at the D3 gate-close commit, freshly fetched |
| Planning-head CI | 30 of 30 successful on the exact head |
| D3 tag | annotated `sprint-21d3-evidence-baseline`, object and peeled commit recorded |
| D3 implementation | PR `#221`, post-merge CI successful on the exact head |
| Migration | `0015` head; `0016` unallocated |
| Protection | 27 strict required contexts, `enforce_admins`, conversation resolution, no force-push or branch deletion |
| Reviewer state | one collaborator; approving-review requirement unset without fabricating a reviewer |
| Learned component state | 0 components, 0 approvals, 0 activations for `experience.correction_ranking` |
| Gate state | Gate D1 conditions 6, 7, and 15 open; Gate L2 does not pass; Sprint 22A blocked |

### 1.2 Immutable predecessor Artifact Store pairs

| Pair | Files | Fingerprint | D4 access |
|---|---:|---|---|
| development `artifacts` | 5 | `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf` | read-only diagnostic only |
| C3 `artifacts-s21c3` | 8,503 | `7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593` | read-only |
| D1 `artifacts-s21d1` | 83 | `f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f` | read-only |
| D2 `artifacts-s21d2` | 1,511 | `39417f1a03f6824cfe6f9c4b7e6bd5a3cd34da8329fb95cff0a35595899438aa` | read-only |
| D3 `artifacts-s21d3` | 1,952 blob rows resolved at W7 | re-read at S21D4-000 | read-only predecessor evidence |

D4 writes only to a new database and a new Artifact Store root. Every destructive operations
case uses disposable copies.

### 1.3 D3 result

- The correction branch stopped at S21D3-039 with a null selection, hash
  `68ea06843d2136e390bf8a4ea0698414932987f5447887187907c45c0dcea876`.
- All 24 frozen k-NN settings were measured on 20 calibration groups.
- Action preservation was **1.00 for every setting** across all six transformation cases;
  equivalence coverage never fell below clean coverage.
- The strongest setting reached 0.65 clean first-choice against a 0.5 deterministic baseline.
- Every setting that answered produced 12 to 36 confident errors of 120 metamorphic decisions.
- The retrieval branch stopped at S21D3-045, hash `f0b53912055223667c2cca93…`; no arm cleared
  either floor and every arm sat at or below the chance baseline on recall.
- Twenty dependent tasks carry typed `not_opened` records bound to the selection stop.
- Final A, final B and canary remain sealed, unopened, with zero outcomes and zero
  body-access receipts.

### 1.3.1 The D3 learned store is empty, and why that is settled

D4-W0-F1, established at S21D4-003 and recorded in
[`sprint-21d4-finding-w0-f1.json`](evidence/sprint-21d4-finding-w0-f1.json).

`cognitive_os_s21d3_test` holds **no learned observations and no explicit datasets**, while
holding the 3,306 artifacts, 1,971 artifact blobs and 1,731 events that prove the campaign ran
against that exact database. Sprint 21D2's store, read as a control, holds its documented 480
observations and 2 datasets.

The data was **persisted and committed, then removed by TRUNCATE**. Three independent signals
agree, and each rules out a different alternative: the append-only Event Store holds 340
committed `learned.observation_recorded` events, so a rollback is excluded; `n_tup_del` is zero
on `learned_observations`, so a `DELETE` is excluded; and all nine `learned_*` tables carry
`relfilenode != oid` in one contiguous block while every other table in the database does not,
which is what a rewrite by `TRUNCATE` looks like and also why the delete counter shows nothing.

The mechanism was `run_learned_smoke`, which truncates exactly those nine tables and was fenced
only by the database name ending in `_test` -- a suffix every sprint's evidence database also
carries. It fired at `17:04:08` on 2026-08-05, 114 seconds before the W7 backup manifest, which
is why that restore proof compared matching counts of nothing. Nothing is recoverable, because
every backup postdates the erasure.

This sprint closed the path: the smoke now requires `COGOS_TRUNCATABLE_DATABASE` to nominate the
connected database, which is the rule the PostgreSQL integration fixture has enforced since
W6-F2, and additionally refuses any store still holding an observation, a dataset, or a
component other than the inert reference one.

**The D3 result is undisturbed.** Its selection is committed evidence and S21D4-001 recomputes
the full 24-setting grid from that file without reading the store. What changes for D4 is only
that no predecessor row can be inherited, which Section 4.3 already required.

### 1.4 Mandatory D3 decision-independence correction

**This is the finding that decides D4's shape, and it is not in the D3 report.**

D3 reported 120 metamorphic ranking decisions per setting: 20 calibration groups times six
semantics-preserving transformation cases. Because `correction-ranking-v2` is *exactly*
invariant — the sprint's own principal result — all six transformed cases of a group produce
byte-identical fitted vectors and therefore the identical ranking decision. The recorded grid
proves it arithmetically, in all 24 settings without exception:

| Setting (k, sim, agr, conf) | clean answered | clean correct | clean errors | metamorphic answered | confident errors |
|---|---:|---:|---:|---:|---:|
| 3, 0.30, 0.60, 0.55 | 19 | 13 | 6 | 114 = 6x19 | 36 = 6x6 |
| 5, 0.30, 0.60, 0.55 | 18 | 13 | 5 | 108 = 6x18 | 30 = 6x5 |
| 5, 0.30, 0.80, 0.70 | 16 | 11 | 5 | 96 = 6x16 | 30 = 6x5 |
| 7, 0.30, 0.60, 0.55 | 15 | 11 | 4 | 90 = 6x15 | 24 = 6x4 |
| 3, 0.30, 0.60, 0.70 | 13 | 9 | 4 | 78 = 6x13 | 24 = 6x4 |
| 7, 0.30, 0.80, 0.55 | 10 | 8 | 2 | 60 = 6x10 | 12 = 6x2 |

For all 24 settings, `ood_answered == 6 * clean_answered` and
`confident_ood_errors == 6 * (clean_answered - clean_correct)`. Zero violations.

Three consequences follow, and they are the sprint:

1. **D3's metamorphic set carried no information about ranking accuracy.** It was 20 decisions
   replicated six times. It was a perfect invariance regression test and a null accuracy test.
2. **"Zero confident metamorphic errors" was, in D3, mathematically identical to "zero errors
   among answered clean decisions"** — a demand for 100% selective precision, certified on a
   sample of 20. A sample of 20 cannot distinguish 0% error from 5% error, so even a passing
   D3 would not have supported the claim.
3. **The residual is therefore not "capacity" in the sense the D3 handoff proposed.** More
   fitting rows raise first-choice accuracy; they do not make a 20-decision sample able to
   certify a zero-error rate. The binding constraint is the *calibration sample*, and the
   missing mechanism is *selective prediction* — choosing an operating point at which the
   ranker is silent whenever it would be wrong, and proving that on enough independent
   decisions to mean something.

D4 therefore freezes these terms before any experiment, extending S21D3-010 rather than
replacing it:

- **independent ranking decision:** one ranking decision whose fitted feature vector is
  distinct from every other counted decision in the same set;
- **replicated decision:** a counted decision whose fitted vector equals another's. Replicated
  decisions are reported, and they are valid invariance evidence, but they never contribute to
  an accuracy, error-rate, or coverage denominator;
- **selective operating point:** the pre-registered rule that decides, per decision, whether
  the learned order is used or the deterministic baseline runs;
- **coverage:** answered independent decisions over all independent decisions.

This does not rehabilitate D3; it makes its shortfall precise and it makes D4's target
measurable. Gate L2 condition 20's fixed threshold is unchanged. D4 satisfies it and
additionally reports the independent count everywhere, so the same collapse cannot recur
undetected.

### 1.5 Mandatory D3 retrieval and recovery reconciliation

D3's retrieval finding is reproduced, not re-litigated:
`distinct_after_removing_domain_and_signature: 1` over sixty candidates.
`ActionDecisionGraph.search_text()` is domain, task signature, node labels and edge kinds, and
its node attributes are exactly four enum values — `correctness`, `necessity`, `segment`,
`status`. Sixty structurally identical repair paths are therefore one document to every arm,
and the lexical arm's ranking is the pair-id tie-break for all sixty queries.

The D3 conclusion stands: improving an arm cannot widen a surface. D4 accepts it and does the
contract change D3 named and deliberately did not make.

D4 also inherits W3-F1: `minilm_shortlist_plus_bounded_ged` is not reproducible under a
wall-clock timeout, so its D1, D2 and D3 numbers cannot be replayed by anyone. Revision 4
resolves this rather than carrying it a fourth time (Section 4.6).

**A second D3 narrative discrepancy was found while executing the D3 release, and it is the
same class D3 catalogued in D2.** The W7 recovery paragraph of the D3 execution log disagrees
with `sprint-21d3-operations.json` on every value it states:

| Value | Execution-log narrative | Committed evidence |
|---|---|---|
| database dump SHA-256 | `c51b828106306b92…` | `f68fea62bbb0dbbb…` |
| artifact archive SHA-256 | `8bb54058d02e1f69…` | `ea6449ebefce79ee…` |
| artifact archive bytes | 1,679,871 | 1,683,401 |
| events backed up | 1,281 | 1,731 |
| artifacts backed up | 2,754 | 3,306 |
| blobs rehashed on restore | 2,077 | 2,096 |

The D3 report states 2,096, so the report and the machine-readable evidence agree and only the
execution log dissents. The shape — every value from one paragraph wrong, consistently low —
reads as a paragraph written from a rehearsal run and not refreshed from the final one. The
W7-A5 blob-row count, "1,952 of 1,952", likewise appears nowhere in the evidence, which records
1,971 blob rows.

The structural claims of that same wave all reproduce: 18 damage cases present and all failing
closed, 27 of 27 verification-matrix rows passed, `fingerprints_before == fingerprints_after`,
and `final_outcomes_inspected: false`. Nothing about the D3 result changes; what is wrong is a
narrative restatement of counts.

D4 does not rewrite the D3 execution log. Section 10.3 of the D3 backlog makes released
evidence immutable, and the programme's own convention — established when D3 reconciled D2's
retrieval narrative rather than editing it — is to correct in the successor. S21D4-001 carries
this reconciliation alongside the decision-independence one, and the D3 release tag states the
evidence values rather than the narrative ones.

### 1.6 Untouched correction-holdout inventory

| Role | Groups | Candidate slots | Outcome state |
|---|---:|---:|---|
| final A | 30 | 120 | unexecuted, sealed, zero body-access receipts |
| final B | 30 | 120 | unexecuted, sealed, zero body-access receipts |
| canary | 5 | 20 | unexecuted, sealed, zero body-access receipts |

All 65 groups are pairwise disjoint and were audited `reuse` at S21D3-004. D4 re-runs that
audit unchanged — a second reuse is not a weaker claim, but it is a second claim and must be
proved again against current bytes. If any member fails, replace the whole affected role
before fitting; never cherry-pick passing members or reduce final A/B from 30 groups to the
25-group gate floor.

### 1.7 Reusable released authority

D4 reuses without reimplementation, and this list is longer than any predecessor's because D3
built its entire second half against a contract fixture:

- `correction-ranking-v2`, the production alpha-normaliser, and the windowed mean-pooled
  canonical-source embedding;
- fitted-matrix allowlist/denylist scans over all 390 dimensions, and seeded leakage
  violations;
- explicit revision-3 dataset identity, pre-outcome feature sealing, campaign bundle
  persistence, receipt-aware resume, and chronology refusal;
- the deterministic baseline ladder with encoder-version dispatch, and bounded pure-Python
  k-NN;
- the versioned D3 promotion payload, its twenty-gate evaluator, and `not_measured` as a
  distinct outcome;
- `CorrectionArtifactPayloadV2`, `DirectEvaluationCapability`, and the narrow loader with all
  eleven refusal cases;
- the runtime resolver with 18 reason codes, `ArtifactAvailability`, and the 21-configuration
  invariance matrix;
- receipt-aware candidate sequencing, `verify_component()`, and activation-time
  `_revalidate_bytes`;
- the eleven-class evidence integrity report, its four states, the CLI environment boundary,
  the 18-case corruption matrix, and the 27-row release matrix;
- Experience Graph projection, lexical/vector/bounded-GED/RRF retrieval, resource limits,
  `reality_leakage.judgement_leaks`, and the advisory Context Builder boundary;
- D3 backup, restart, restore, corruption, isolation, and verification-matrix scripts.

The expected code change is a focused revision — a counting rule, a threshold rule, one graph
field, and one comparator budget — not a second learning subsystem.

---

## 2. Sprint goal and fixed gate contract

### 2.1 Goal

Determine whether the frozen `correction-ranking-v2` k-NN, at a calibration-derived selective
operating point and certified on at least 100 independent ranking decisions, is materially and
safely useful on untouched final evidence; and independently, whether widening the Experience
Memory Graph's searchable surface lets a frozen retrieval arm clear both usefulness floors on
a new unseen-task holdout. On a complete pass, promote exactly one correction-ranking artifact
through the released governed lifecycle, close Gate L2 and Gate D1 conditions 6, 7 and 15, and
unblock Sprint 22A. On any stop, publish a complete negative release that makes the next
engineering decision from new evidence.

### 2.2 Fixed Gate L2 conditions D4 must evidence

The 29 conditions and every threshold are unchanged. D4 inherits no pass from D3; the fifteen
D3 met as infrastructure claims must be re-evidenced against D4's own authorities.

| Condition | Required D4 evidence |
|---:|---|
| 1-3 | current baseline, immutable predecessors, and the D3 decision-independence reconciliation |
| 4 | revision-4 pre-registration before any D4 calibration, threshold, campaign or retrieval measurement |
| 5 | verifier remains label and acceptance authority; prediction only orders attempts |
| 6 | revision-4 fitted matrix contains no forbidden, identity, outcome, or answer field |
| 7 | transitive task/repository/template/clone/source groups do not cross any D4 role |
| 8 | at least 200 fitting observations/50 groups and 40 calibration observations/10 groups; D4 targets 320/80 and 400/100 |
| 9 | zero `REAL_GOVERNED_RUN` observations in fitting and calibration |
| 10 | final A and B each contain 120 new verifier-backed outcomes over 30 groups |
| 11 | final manifests inaccessible to fitting and one artifact selected before final access |
| 12 | strongest deterministic baseline and every attempted rung recorded; frozen k-NN grid first |
| 13 | at least 20 final group decisions differ from the strongest baseline |
| 14 | at least 5 percentage points absolute gain or at least 20% relative error reduction |
| 15 | paired group bootstrap, seed 21041, 2,000 resamples, 95% lower bound above zero |
| 16 | learned-minus-baseline direction positive in both final A and final B |
| 17 | exact denominators for coverage, abstention, confidence, attempts, latency, calls, failures, and cost, each naming its independent count |
| 18 | zero safety/governance/permission/secret/destructive accepted-to-rejected regressions |
| 19 | no retained domain loss above 2 points and aggregate loss at most 1 point |
| 20 | at least 100 actual pre-registered metamorphic/OOD ranking decisions over at least 10 groups, false-confident rate at most 1%, promotion exactly zero confident errors; the independent count is reported beside the nominal count and the zero-error claim is certified on at least 100 **independent** calibration decisions before final access |
| 21 | shadow changes zero executed decisions and outcome linkage uses only verifier evidence |
| 22 | selected artifact is canonical inert JSON with complete lineage and unsafe formats remain unloadable |
| 23 | every artifact/configuration/lifecycle failure immediately uses the deterministic fallback with a structured reason |
| 24 | at least one bounded arm reaches Recall@5 at least 0.70 and MRR@10 at least 0.50 on at least 50 new unseen-task queries within the fixed resource budget |
| 25 | canary manifest hash-bound, verifier mandatory, kill switch immediate |
| 26 | activation, loading, disable, restoration, and rollback survive restart |
| 27 | human approval uses exactly the existing fields, no invented approval field, no self-approval |
| 28 | isolated replay, backup/restore, corruption, artifact, packaging, schema, security, language, focused CI, and complete local matrix |
| 29 | protected merge, post-merge exact-head CI, outcome-specific report/assessment/handoff, annotated tag, and remote verification |

Gate D1 condition 6 closes when at least 200 unique, eligible, verifier-backed primary-surface
outcomes exist — final A and B together produce 240. Condition 7 closes when at least 20
primary-surface examples can change the advisory action under the frozen learned policy, which
is condition 13's evidence read against the D1 contract. Condition 15 closes independently only
if the new retrieval holdout reaches both floors.

### 2.3 Revised D4 non-silence and independence rules

These replace S21D3-023's added rules. They are stricter in the dimension that failed and
honest in the dimension D3 over-constrained.

Selection requires all of:

- **at least 100 independent clean ranking decisions** in the calibration set;
- exactly **zero confident errors among answered independent calibration decisions**;
- clean coverage at least **0.40**, and at least high enough that the selected operating point
  projects at least 20 changed decisions over the 60 final groups;
- clean first-choice rate over answered decisions strictly above the strongest deterministic
  baseline measured on the same decisions;
- at least one changed clean decision, so identity with the fallback is not called useful;
- 100% first-action preservation on the invariance-regression sample;
- every grid point reported, including filtered and fully abstaining points.

**The 0.80 clean-coverage floor is deliberately lowered to 0.40, and the change is a
tightening, not a relaxation.** D3's 0.80 floor was a self-imposed rule, not a Gate L2
threshold. Combined with a zero-error requirement certified on 20 decisions it was
unsatisfiable by construction: the grid offered coverage 0.95 with 6 clean errors or coverage
0.50 with 2, and nothing between. A selective ranker's whole mechanism is buying precision with
coverage, and a floor that forbids buying it forbids the mechanism. What replaces it is
stricter: the coverage that survives must be *earned* — zero errors on 100+ independent
decisions, and enough answered final decisions to satisfy condition 13 on its own terms. A
ranker that abstains everywhere still fails, now on condition 13 rather than on a floor.

Condition 20 remains a safety ceiling. Malformed inputs, corrupt artifacts, missing
configuration, oversized payloads and permission violations remain mandatory runtime and
corruption tests; they are not ranking decisions and cannot inflate any denominator.

---

## 3. Scope, experimental revisions, and stop rules

### 3.1 In scope

- exact baseline, store, seal, and decision-independence reconciliation;
- revision-4 pre-registration with the counting rule, the selective operating-point rule, the
  corpus reallocation, and the widened retrieval surface all frozen before measurement;
- a fitting pool enlarged to 80 groups / 320 outcomes **from rights-cleared existing task
  packages**, re-executed as a new campaign under new run identities;
- 100 newly authored calibration groups / 400 outcomes, group-, clone- and source-disjoint
  from every other role;
- a fitting-volume probe at 200 and 320 rows, reported as the yield curve the D3 handoff asked
  for, produced as a by-product of the reallocation at zero additional authoring cost;
- a 20-group invariance-regression sample with two transformation cases, replacing D3's
  six-case set on all groups;
- correction final A/B and canary reuse after a repeated untouched-holdout audit;
- one additive, hash-neutral `search_terms` field on `ActionDecisionGraph` and its projection;
- a deterministic budget for the bounded-GED comparator, or its retirement from the frozen set;
- a distinct, newly sealed retrieval holdout with at least 50 qualifying queries;
- first real exercise of the D3-built artifact, runtime, verification, promotion, activation,
  canary, rollback and operations surfaces;
- a complete typed negative path at every conditional boundary.

### 3.2 Explicitly out of scope

- any change to `correction-ranking-v2`, the alpha-normaliser, the embedding model, or the
  390-channel fitted representation;
- changing Gate L2 or D1 thresholds, the bootstrap seed, the resource-policy node/edge/depth
  bounds, or reviewer controls;
- a parametric learner, a second hypothesis class, fine-tuning, a GNN, an FGW implementation,
  a GPU path, or a live provider;
- tuning to D3's spent calibration or retrieval evidence, or re-deciding either D3 stop;
- authoring new final, batch-B or canary bodies unless the reuse audit fails a whole role;
- a universal correction model, cross-surface learner, or `CodingAgentFacade` coverage claim;
- `REAL_GOVERNED_RUN` fitting, online learning, autonomous weight updates, or verifier bypass;
- repair of the inconsistent five-file development Artifact Store pair;
- repair of `postgres_bootstrap_roles.sh` beyond the existing provisioning route;
- Sprint 22A domain expansion or any claim that Gate L2 is passed before the final release gate.

### 3.3 Revision-4 decision tree

Revision 4 must publish this response before reading any D4 calibration number:

1. Replay D3's grid under the corrected independence denominators. If the replay cannot
   reproduce D3's recorded values from D3's own evidence, stop with
   `reconciliation_not_reproducible` — the erratum in Section 1.4 is then unproven and nothing
   downstream may rely on it.
2. Fit at 200 and at 320 rows and measure the risk–coverage curve of the frozen grid on the
   fresh calibration set. Record coverage-at-zero-error at both volumes.
3. If some grid point and operating point reach zero errors on at least 100 independent
   decisions at coverage at least 0.40, proceed to selection.
4. If zero-error coverage is above zero but below 0.40 at 320 rows *and* materially higher at
   320 than at 200, stop with `volume_bound`: the residual is evidence volume, the yield curve
   is the deliverable, and the successor sprint is a corpus sprint with a named target volume.
5. If zero-error coverage is at or near zero at both volumes and does not improve with volume,
   stop with `hypothesis_class_bound`: the frozen k-NN cannot separate its own errors, and
   *that* is when a different hypothesis class is worth pre-registering.

Outcomes 4 and 5 are different sprints and D4 must not guess between them in advance. This is
the tree D3's handoff asked for, made affordable by measuring it on the corpus D4 needs anyway.

### 3.4 Learner continuation rule

D4 evaluates the frozen 24-setting k-NN grid crossed with the pre-registered selective
operating points. No parametric rung opens inside D4. A fresh residual may recommend a specific
D5 hypothesis class only when:

- the independence reconciliation reproduces;
- the enlarged calibration set yields at least 100 independent decisions;
- the fitted matrix passes every leakage and chronology check;
- zero-error coverage is measured at both volumes and classified by Section 3.3;
- the recommendation is recorded without opening either correction final batch.

### 3.5 Holdout and retuning stop line

- The D3 replay may run only after revision 4 is hash-bound.
- Fresh calibration data may be resolved only after the counting rule, grid, operating-point
  rule, coverage rules, transformation recipes, and exact member submanifests are frozen.
- The selected setting, operating point, fitted artifact bytes, dataset hash, split hash,
  feature hash, code revision, and final prediction-seal procedure must be fixed before final
  access.
- The widened surface contract, the graph field, its leak guard, the comparator budget,
  retrieval arms, fusion constant, ties, resources, queries, judgements, and metric code must
  be fixed before the retrieval holdout is resolved.
- Any final or retrieval failure closes the associated branch. No new revision, arm, surface
  field, or member replacement is permitted in D4.

---

## 4. Minimal D4 architecture

### 4.1 Decision independence as a first-class reported quantity

One rule, applied everywhere a decision is counted: a decision set reports
`nominal_decisions`, `independent_decisions`, and `replicated_decisions`, where independence
is equality of the fitted feature vector. Every rate names which denominator it used, and
accuracy, error and coverage rates use the independent denominator.

This is a counting change, not a mechanism change. It lands in the released
`knn_calibration.py` and `calibration_ood.py` contracts so no evidence file can report a rate
without it, and a schema validation refuses a decision set whose rates use the nominal
denominator. The D3 metamorphic set replayed under this rule reports 120 nominal, 20
independent, 100 replicated — which is the erratum, computed rather than asserted.

### 4.2 The selective operating point

The frozen k-NN already produces a confidence score per ranking decision, and the released
setting grid already contains a `confidence_floor` with two values. D4 changes only where the
floor comes from:

1. compute the score for every independent clean calibration decision;
2. sort the answered decisions by score descending;
3. the **zero-error operating point** is the highest score threshold at which every answered
   decision above it is correct, reported with its coverage and with the binomial 95% upper
   bound on the true error rate at that coverage;
4. the pre-registered grid of operating points is the zero-error point plus the two released
   fixed floors `0.55` and `0.70`, so D3's settings remain in the comparison as declared
   comparators and the change is attributable;
5. selection precedence is fixed before measurement: a released fixed floor is preferred if it
   satisfies Section 2.3; only if none does may the derived point be selected.

That is a quantile of a sorted list. It is arithmetic over the existing score, it introduces
no model, no fit, no dependency, and no new artifact channel beyond the threshold value and
its provenance. The derived threshold is part of the selected candidate's identity and is
sealed into the artifact before final access, exactly as `confidence_floor` already is.

The honest statement of what this buys: it converts "is the ranker accurate enough?" into "is
there an operating point at which the ranker is never confidently wrong, and does enough work
remain at that point to be useful?" — which is the question Gate L2 conditions 13, 14 and 20
jointly ask, and which D3's two-point floor grid could not resolve.

### 4.3 Corpus reallocation

D3 spent its authoring budget on 20 calibration groups and 480 executed transformed candidates
that, being exactly invariant, could not change any conclusion. D4 spends the same budget on
distinct groups.

| Role | D4 target | Provenance | Authoring cost |
|---|---:|---|---|
| fitting | 80 groups / 320 outcomes | 50 D2 training + 10 D2 calibration + 20 D3 calibration, all re-executed as a new campaign | none |
| calibration | 100 groups / 400 outcomes | authored for D4 | the wave's main deliverable |
| invariance regression | 20-group sample, 2 cases, 40 transformed decisions | generated | 160 executed candidates, down from D3's 480 |
| final A | 30 groups / 120 outcomes | carried, sealed, unopened | none |
| final B | 30 groups / 120 outcomes | carried, sealed, unopened | none |
| promotion metamorphic/OOD | 60 groups x 2 cases = 120 nominal, 60 independent | verifier-backed evaluation only | none |
| canary | 5 groups / 20 slots | carried, sealed, unopened | none |
| retrieval | at least 60 new disjoint groups until at least 50 queries qualify | authored for D4 | as D3 |

**Sprint 21C3's corpus is deliberately excluded.** It would have carried the pool to roughly
110 groups and 440 outcomes, but only if around thirty of its groups cleared a rights and
role-disjointness audit that has not been run. The release owner chose the certain pool over
the larger one, so the probe measures 200 and 320 rather than 200 and 440. The smaller upper
point weakens the volume arm of Section 3.3 and the record says so: a flat curve between 200
and 320 is weaker evidence for `hypothesis_class_bound` than a flat curve to 440 would have
been, and S21D4-039 must report that limitation rather than let the reader infer a stronger
conclusion than the spacing supports. C3 remains available to a successor if the volume arm is
the one that fires.

The exact fitting composition is still an audit result, not an assumption: S21D4-012 enumerates
every rights-cleared, role-disjoint group actually available and records the achieved count. If
fewer than 80 are eligible, the fitting pool is what is eligible and the volume probe reports
the volumes it actually measured. A planned number that survives contact with an audit is
evidence; one that does not is a target, and the evidence records the difference.

**No row of it is inherited.** D4-W0-F1 established that the D3 learned store holds no
observations and no datasets, so every group named above is a task *package to re-execute*,
never a row to read. That was already the contract -- new run identities after fresh feature
seals -- but it is now the only possibility rather than the disciplined choice.

Promotion decisions over the 60 final groups are 60 independent and 120 nominal. Condition 20's
fixed threshold is met on the nominal count exactly as it is written, the independent count is
reported beside it, and the zero-error claim that matters is certified before final access on
at least 100 independent *calibration* decisions. D4 does not author replacement final groups
to inflate the independent promotion count — that would open a sealed role for a reporting
convenience.

### 4.4 Invariance regression, not an invariance experiment

The six-case transformation set proved its property exactly and is now a regression test. Two
cases — one identifier rename, one issue rewrite — over a declared 20-group sample, with the
released independent perturbation generator and hard-coded golden pairs as a second oracle.
Any label change, any feature drift, any first-action change is a stop with
`invariance_regression`. Seeded semantic operator and branch-condition mutations remain
mandatory and must change the canonical representation.

### 4.5 The widened searchable surface

`ActionDecisionGraph.search_text()` gains exactly one input:

```python
search_terms: tuple[str, ...] = ()   # additive, default empty
```

The field is **excluded from `structural_hash` and from `ExperienceGraphNode.label`**, so
labelled graph-edit distance, edit-path round-tripping, and every stored D1/D2/D3 structural
hash are byte-unchanged. It is included in `content_hash` — a new graph is new bytes — and old
stored graphs deserialise unchanged under the default. That is the whole contract change: one
optional field and two lines in `search_text()`.

The projection fills it from evidence that already exists behind each node's `source_hash`:

- resolve the node's source blob through the released graph store;
- run the released `correction_source.canonical_source_bytes` alpha-normaliser over it, so the
  terms are the same canonical form the correction encoder already trusts, with local bindings
  replaced by placeholders and imports, attributes, builtins and magic names preserved;
- emit a bounded, deterministic term list under the existing 1024-character attribute bound and
  the existing `FORBIDDEN_ATTRIBUTE_MARKERS` guard;
- refuse the whole projection, fail-closed, if `reality_leakage.judgement_leaks` reports that
  any term names the relevance label the graph will be scored against.

This is the minimum that makes sixty repair trajectories sixty documents. The query side
becomes the failed trajectory's canonical terms and the document side the repaired
trajectory's — which is the retrieval question the surface is supposed to answer: *find a
repair for a bug shaped like mine*. Alpha-normalisation is what keeps that from becoming
lookup: two tasks in a family share structure and preserved names, not spelling.

Nothing is added that is not already resolvable at projection time. No issue text, no
provenance hash, no unnormalised body, no new store, no new index.

### 4.6 The bounded-GED comparator

`nx.graph_edit_distance(..., timeout=...)` is an anytime search under a wall clock, so the
score depends on the host and the moment. D3 measured it, named it, and left it frozen. A
fourth sprint reporting an irreproducible arm is a defect the programme keeps rather than has.

Revision 4 declares one of two outcomes before the holdout is resolved, and S21D4-041 decides
between them on measurement, not preference:

- **deterministic budget:** replace the wall-clock `timeout` with a fixed iteration budget from
  `networkx.optimize_graph_edit_distance`, which yields successively better distances and is
  host-independent. Repeated-ranking agreement must then be 100% across two passes;
- **retirement:** if a fixed budget cannot reproduce a stable ranking, the arm leaves the frozen
  set and is reported as retired with its reason.

Either way the D1, D2 and D3 numbers for this arm stay marked irreproducible. Nothing is
back-filled.

The rest of the resource policy is unchanged: 64 nodes, 128 edges, path depth 32, 20-vector
shortlist, two seconds per query, ten returned results. The comparators remain no-memory, exact
signature, lexical, MiniLM vector, bounded GED, and the D3 equal-weight RRF arm with constant
60 and untuned weights.

### 4.7 Lifecycle sequence

The positive path reuses the released sequence without shortcuts:

```text
pre-registration revision 4
  -> independence reconciliation and D3 grid replay
  -> enlarged fitting campaign and fresh 100-group calibration campaign
  -> explicit snapshots and matrix validation
  -> risk-coverage curve at two volumes -> one operating point
  -> one candidate selection and canonical v2 artifact
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
`not_opened` record bound to the first stop hash. Every arrow from `REGISTERED` onward is
released D3 code being executed for the first time against a real candidate.

### 4.8 Expected focused code boundary

| Module | Change |
|---|---|
| `src/cognitive_os/learning/knn_calibration.py` | independent/nominal/replicated denominators; the zero-error operating point as a sorted-quantile rule |
| `src/cognitive_os/learning/calibration_ood.py` | independence classification of a transformed case; two-case regression set |
| `src/cognitive_os/learning/correction_artifact.py` | the derived threshold and its calibration provenance as artifact identity |
| `src/cognitive_os/learning/promotion.py` | independent counts in the promotion payload's condition-20 gate |
| `src/cognitive_os/domain/experience_graph.py` | one additive `search_terms` field, excluded from `structural_hash` and `label` |
| `src/cognitive_os/experience/graph_projection.py` | fill `search_terms` from resolved sources through the released normaliser, leak-guarded |
| `src/cognitive_os/experience/graph_retrieval.py` | the deterministic GED budget or the arm's retirement |
| `src/cognitive_os/coding/reality_task_specs_d4.py` | 100 authored calibration groups |
| `src/cognitive_os/coding/reality_retrieval_specs_d4.py` | the new retrieval pool |
| `scripts/*_d4.py` | narrow campaign, selection, retrieval, artifact, operations and matrix scripts, adapted from their D3 originals |
| `tests/cognitive_os/{learning,experience,coding}` | focused tests beside the released ones they extend |

No database migration is expected. No new module is expected outside the corpus and script
files. Nothing in `learned_evidence.py`, the runtime resolver, the loader, the sequencer or the
integrity report is expected to change — if one of them does, it is a defect D3 shipped and the
change is recorded as a finding, not as planned work.

---

## 5. Detailed work items

Every item below is independently reviewable. "Evidence" means a committed, canonical,
machine-readable artifact unless the item explicitly names a test or document. Conditional
items produce a typed `not_opened` result when their dependency closes. S21D4-075 is the
explicit exception: receipt-chain rollback/refusal is an unconditional substrate gate and uses
the minimal isolated lifecycle fixture when no real D4 activation exists.

## EPIC S21D4-E00 — Baseline, reconciliation, and isolation

### S21D4-000 — Revalidate the exact D4 starting point

- **Deliverable:** `evidence/sprint-21d4-baseline.json` generated from fresh local and remote
  reads before implementation.
- **Acceptance:** records local/remote branch heads; the D3 tag object and peeled commit; PR
  `#221` and the D3 gate-close PR; all PR-head and post-merge CI runs; 27 required contexts;
  `enforce_admins`; collaborator and review state; migration head; component/approval/activation
  counts; and all five predecessor store fingerprints. The implementation branch is proved to
  descend from current `origin/main`. **The item fails, and D4 does not start, if
  `sprint-21d3-evidence-baseline` does not resolve remotely.**
- **Evidence:** commands, timestamps, resolved SHAs, remote URLs, CI conclusions, protection
  JSON hash, and zero-write fingerprint receipts.
- **Dependencies:** S21D3-094 and S21D3-095.

### S21D4-001 — Publish the immutable D3 decision-independence reconciliation

- **Deliverable:** `evidence/sprint-21d4-d3-reconciliation.json` plus a short referenced
  erratum in the D4 report and handoff.
- **Acceptance:** recomputes, from D3's own committed evidence, that for all 24 settings
  `ood_answered == 6 * clean_answered` and
  `confident_ood_errors == 6 * (clean_answered - clean_correct)`; classifies D3's 120
  metamorphic decisions as 20 independent and 100 replicated; states that D3's zero-error
  requirement was equivalent to 100% selective precision on a sample of 20; and modifies no D1,
  D2 or D3 byte. It records the binomial 95% upper bound on a zero-error claim at n=20 so the
  insufficiency is a number rather than an adjective. It additionally reconciles the six W7
  recovery values and the W7-A5 blob-row count of Section 1.5, naming the evidence value, the
  narrative value and the JSON pointer for each, and confirming that the structural claims of
  that wave reproduce.
- **Evidence:** per-setting recomputation table, exact JSON pointers, replay command, result
  hash, and `protected_objects_unchanged: true`.
- **Dependencies:** S21D4-000.

### S21D4-002 — Provision isolated D4 authorities

- **Deliverable:** a D4 PostgreSQL database, Artifact Store root, evidence output root, backup
  root, restore database, and scratch roots, all outside the five predecessor pairs.
- **Acceptance:** provisioning uses `scripts/postgres_provision_evidence.sh` with the explicit
  `COGOS_POSTGRES_ENV_FILE`; the guard rejects any non-`s21d4` database name and each
  predecessor root by absolute path; permissions pass; migration reaches `0015`; the run is
  idempotent; `postgres_bootstrap_roles.sh` is hashed and not invoked.
- **Evidence:** redacted environment manifest, role/privilege check, migration output,
  absolute-root inventory, before/after predecessor fingerprints.
- **Dependencies:** S21D4-000.

### S21D4-003 — Freeze the predecessor evidence and seal inventory

- **Deliverable:** `evidence/sprint-21d4-predecessor-inventory.json`.
- **Acceptance:** enumerates the D3 explicit datasets and their exact members, all D3
  observations and seals with their chronology, campaign bundle identities, feature/member
  hashes, both D3 stop hashes, the twenty typed not-opened records, and zero final/canary
  outcomes. Store-wide and latest-seal selection is explicitly rejected.
- **Evidence:** exact observation, feature, group, campaign, partition, manifest and seal
  counts; integrity content hash.
- **Dependencies:** S21D4-002.

### S21D4-004 — Re-audit correction final and canary reuse eligibility

- **Deliverable:** one eligibility record per final A, final B, and canary manifest.
- **Acceptance:** repeats S21D3-004 against current bytes using only sealed catalogue, root and
  access identities: exact 30/120, 30/120, 5/20 membership; unchanged catalogue, source-file and
  manifest hashes; pairwise group/clone/source disjointness; zero outcomes, predictions and
  body-access receipts; capability isolation from fitting; no D3 selection authority. Records
  exactly `reuse` or `replacement_required` per whole role without resolving protected bodies.
  Revision 4 pre-registers the complete replacement procedure; no partial role reuse.
- **Evidence:** role decision, catalogue/root/access hashes, zero-access proof, conditional
  replacement contract.
- **Dependencies:** S21D4-003.

### S21D4-005 — Open the draft implementation PR in wave 1

- **Deliverable:** a draft PR from `feature/sprint-21d4-selective-correction-ranking` to
  protected `main`.
- **Acceptance:** the description states the negative predecessor, current gate state, no
  migration by default, positive and negative release routes, the exact holdout stop lines, and
  the single-reviewer limitation. No administrator bypass or protection change is requested.
- **Evidence:** PR number, initial head SHA, required-check inventory in the execution log.
- **Dependencies:** S21D4-000 through S21D4-004 and the S21D4-018 document scaffold.

## EPIC S21D4-E01 — Revision-4 experimental contract

### S21D4-010 — Freeze decision independence

- **Deliverable:** revision-4 contract models and a pre-registration section defining
  independent decision, replicated decision, coverage over independent decisions, and the rule
  that no rate may mix denominators.
- **Acceptance:** `nominal == independent + replicated`; independence is equality of the fitted
  feature vector; schema validation refuses a decision set that reports an accuracy, error or
  coverage rate over the nominal denominator; the D3 metamorphic set replayed under the contract
  reports 120/20/100.
- **Evidence:** canonical contract hash; unit tests including one group whose six transformed
  cases collapse to one independent decision.
- **Dependencies:** S21D4-001.

### S21D4-011 — Freeze the selective operating-point rule

- **Deliverable:** the pre-registered risk–coverage protocol and the operating-point grid.
- **Acceptance:** specifies the score, the sort, the zero-error threshold definition, the
  binomial upper-bound reporting, the operating-point grid (`0.55`, `0.70`, derived), the fixed
  selection precedence in Section 4.2, and that the derived threshold becomes part of the
  candidate identity. Explicitly forbids deriving a threshold from anything but the calibration
  split, and forbids more than one derivation.
- **Evidence:** contract hash, worked example on synthetic scores, seeded refusal of a
  threshold derived from final or metamorphic data.
- **Dependencies:** S21D4-010.

### S21D4-012 — Freeze the corpus reallocation and audit the fitting pool

- **Deliverable:** `evidence/sprint-21d4-fitting-pool.json` and the revision-4 role table.
- **Acceptance:** enumerates every rights-cleared task group available for fitting with its
  provenance sprint, its rights record, and its disjointness from calibration, final A, final B,
  canary and retrieval; records the achieved fitting group and outcome count; declares D3's and
  D2's spent calibration groups as fitting exemplars **before** any D4 measurement; declares the
  two volume points as 200 and 320; and records that Sprint 21C3's corpus is excluded by
  decision rather than by failed audit. Every group is recorded as a package to re-execute, with
  the D4-W0-F1 reference, because no predecessor row survives. If fewer than 80 groups are
  eligible, the record states the achieved number and the volume points are set from it.
- **Evidence:** per-group provenance and rights table, achieved counts, transitive disjointness
  proof, contract hash.
- **Dependencies:** S21D4-003, S21D4-010.

### S21D4-013 — Freeze the widened searchable-surface contract

- **Deliverable:** the revision-4 retrieval surface specification.
- **Acceptance:** specifies the `search_terms` field, its exclusion from `structural_hash` and
  from `ExperienceGraphNode.label`, its inclusion in `content_hash`, the derivation from
  resolved source blobs through the released alpha-normaliser, the bound, the forbidden-marker
  guard, the mandatory `judgement_leaks` check, and fail-closed refusal. Declares that no
  unnormalised body, issue text or provenance hash enters the surface.
- **Evidence:** contract hash; a diff listing every field added and every hash proved unchanged.
- **Dependencies:** S21D4-010.

### S21D4-014 — Complete power and yield analysis

- **Deliverable:** `evidence/sprint-21d4-power-and-yield.json` produced without outcome access.
- **Acceptance:** justifies 80/320 fitting, 100/400 calibration, the 100-independent-decision
  floor, the 0.40 coverage floor and its link to condition 13's 20 changed decisions over 60
  final groups, the 20-group invariance sample, and retrieval overproduction sufficient for 50
  qualifying queries. Reports the binomial upper bound on a zero-error rate at n = 20, 60 and
  100 so the sample-size argument is arithmetic.
- **Evidence:** assumptions, formulas, sensitivity table, contract hash.
- **Dependencies:** S21D4-011, S21D4-012.

### S21D4-015 — Freeze calibration and promotion submanifests

- **Deliverable:** the exact case submanifests for the calibration invariance sample and the
  promotion metamorphic set.
- **Acceptance:** binds the 20-group regression sample, its two transformation cases, seeds,
  generator identity, hard-coded oracle, eligibility and applicability rules, case-ID
  derivation, label authority, decision semantics, and counting code. Binds the promotion set to
  all 60 final groups with two cases each and records its independent count as 60 before any
  final access.
- **Evidence:** submanifest hashes, generator code hash, oracle hash.
- **Dependencies:** S21D4-014.

### S21D4-016 — Freeze the retrieval candidate, comparator and benchmark contract

- **Deliverable:** the revision-4 retrieval protocol.
- **Acceptance:** freezes the arms, the RRF constant 60 and equal weights, the tie-break, the
  single truncation point, the resource policy, the query and judgement construction, the
  metric code, and the bounded-GED decision procedure of Section 4.6 including the
  repeated-agreement criterion that decides between a deterministic budget and retirement.
  Publishes the frozen ordering test vector the fusion must reproduce.
- **Evidence:** contract hash, policy hash, test-vector hash.
- **Dependencies:** S21D4-013.

### S21D4-017 — Freeze metrics, fixed gates, and stop records

- **Deliverable:** the revision-4 metric, gate and stop manifest.
- **Acceptance:** restates the 29 fixed conditions and thresholds unchanged; binds Section 2.3's
  revised non-silence rules with an explicit note that the coverage floor moved from 0.80 to
  0.40 and why; enumerates every typed stop kind including `reconciliation_not_reproducible`,
  `volume_bound`, `hypothesis_class_bound` and `invariance_regression`; and defines the
  not-opened record shape.
- **Evidence:** gate manifest hash; a diff against the D3 gate manifest showing zero threshold
  changes.
- **Dependencies:** S21D4-011 through S21D4-016.

### S21D4-018 — Publish pre-registration revision 4

- **Deliverable:** `evidence/sprint-21d4-pre-registration.json`, committed before any D4
  measurement.
- **Acceptance:** contains every frozen contract hash from E01, the decision tree of Section
  3.3, the evidence-role boundary, and zero measured values. `scripts/pre_registration_d4.py
  --check` reproduces its SHA-256; every later evidence file carries that SHA and passes
  `--check-chronology`. Records `d4_measurements_before_pre_registration: 0`.
- **Evidence:** file SHA-256, first commit containing the exact bytes, chronology check output.
- **Dependencies:** S21D4-017.

## EPIC S21D4-E02 — Independence, threshold, and the volume probe

### S21D4-020 — Implement independent decision counting

- **Deliverable:** the counting rule in the released calibration and OOD contracts.
- **Acceptance:** every decision set reports nominal, independent and replicated counts; every
  accuracy, error and coverage rate uses the independent denominator and names it; schema
  export refuses a payload without the triple; the existing D3 evidence remains readable.
- **Evidence:** contract schema diff, focused tests including the six-into-one collapse.
- **Dependencies:** S21D4-018.

### S21D4-021 — Implement the zero-error operating point

- **Deliverable:** the sorted-quantile threshold rule and its provenance record.
- **Acceptance:** given scored decisions it returns the highest threshold with zero errors above
  it, its coverage, and the binomial 95% upper bound; refuses to derive from any set other than
  the declared calibration split; refuses a second derivation; is deterministic across process
  restart; adds no dependency.
- **Evidence:** focused tests on hand-computed vectors including all-correct, all-wrong,
  ties, and empty-answered cases.
- **Dependencies:** S21D4-020.

### S21D4-022 — Replay the D3 grid under corrected denominators

- **Deliverable:** `evidence/sprint-21d4-d3-grid-replay.json`.
- **Acceptance:** reproduces every D3 recorded value from D3 evidence, then reports each setting
  under the independent denominator. Development-only: derives no threshold, records zero D4
  calibration/final/canary access, zero writes to any predecessor store. A failure to reproduce
  stops with `reconciliation_not_reproducible`.
- **Evidence:** per-setting old and new denominators, reproduction diff, integrity hash.
- **Dependencies:** S21D4-021.

### S21D4-023 — Prove v2 sealing and resume for the D4 campaign shape

- **Deliverable:** a seeded vertical fixture proving pre-outcome feature sealing, receipt-bound
  execution, post-outcome seal refusal, and empty effective remainder on restart, for a campaign
  with two partitions at D4's sizes.
- **Acceptance:** reproduces the feature seal and dataset record after restart, preserves the
  stored seal time, resolves identical receipt and dataset members, verifies every artifact byte
  and lineage. Uses a fixture group outside every D4 role.
- **Evidence:** `evidence/sprint-21d4-seal-resume.json`.
- **Dependencies:** S21D4-020.

### S21D4-024 — Record the typed continuation decision

- **Deliverable:** `evidence/sprint-21d4-continuation.json`.
- **Acceptance:** records `proceed` only when the replay reproduces, the counting rule is in
  force, and the fitting pool audit resolved; otherwise records the typed stop and closes the
  correction branch while leaving retrieval open.
- **Evidence:** decision kind, bound hashes, dependent task list.
- **Dependencies:** S21D4-022, S21D4-023, S21D4-012.

## EPIC S21D4-E03 — Fresh evidence at honest scale

### S21D4-030 — Author 100 new calibration groups and the retrieval pool

- **Deliverable:** `reality_task_specs_d4.py` with 100 four-candidate calibration groups and
  `reality_retrieval_specs_d4.py` with at least 60 failed/repair retrieval groups.
- **Acceptance:** every body is **executed rather than declared** — each baseline passes its
  visible suite and fails its hidden one, each declared repair passes both, each partial fix
  passes visible and fails hidden, each retrieval failed state is rejected and each repair
  accepted by the verifier. Every declaration mismatch is fixed and recorded in a defect ledger.
  At least 15 distinct template families, so 100 groups are not 6 families with 94 seeds.
- **Evidence:** `evidence/sprint-21d4-corpus.json` with per-group execution verdicts, family
  distribution, and the defect ledger.
- **Dependencies:** S21D4-024.

### S21D4-031 — Prove rights, lineage, group and near-clone separation

- **Deliverable:** `evidence/sprint-21d4-separation.json`.
- **Acceptance:** zero cross-group near-clone collisions on either detector over all C3, D2, D3
  and D4 bodies; zero groups crossing any role; zero task signatures or query ids reused from
  D1, D2 or D3; a seeded restatement is still caught; the intra-pair structural matches of a
  retrieval group's own two states are named as such.
- **Dependencies:** S21D4-030.

### S21D4-032 — Seal all D4 campaign and holdout manifests

- **Deliverable:** `evidence/sprint-21d4-sealed-manifests.json`.
- **Acceptance:** seals fitting, calibration, final A, final B, canary and retrieval manifests
  before any outcome; carries the reused D2/D3 catalogue objects so final A/B and canary hashes
  are *identical to* the ones S21D3-004 bound, not merely equal; revokes the corpus-authoring
  capability; records the D4 seal hash.
- **Dependencies:** S21D4-031.

### S21D4-033 — Prove one complete vertical slice

- **Deliverable:** `evidence/sprint-21d4-vertical-slice.json`.
- **Acceptance:** one fixture group outside every role runs from package through v2 feature
  seal, sandboxed self-play, hidden-verifier labels, receipt, role-bound observation, explicit
  dataset identity, fitted matrix, k-NN ranking at a derived operating point, artifact reload,
  restart replay, and refusal of final and retrieval capabilities. Spends no calibration case,
  final member, canary member or retrieval judgement.
- **Dependencies:** S21D4-032.

### S21D4-034 — Seal every fitting and calibration feature before execution

- **Acceptance:** all 840 v2 feature records are sealed before the first container of their
  partition starts; a post-outcome seal is refused; seal chronology is recorded per partition.
- **Dependencies:** S21D4-033.

### S21D4-035 — Execute and ingest the fitting campaign

- **Acceptance:** the achieved fitting groups produce their `SELF_PLAY` outcomes under
  `label_all`, zero `REAL_GOVERNED_RUN` rows, zero baselines passing hidden verification, and a
  receipt-aware resume that replays every recorded run identity without a new container and
  leaves an empty effective remainder.
- **Evidence:** `evidence/sprint-21d4-self-play-campaign.json`.
- **Dependencies:** S21D4-034.

### S21D4-036 — Execute and ingest the fresh calibration campaign

- **Acceptance:** 100 groups produce 400 `SELF_PLAY` outcomes under the same contract, sealed
  before execution, with the same resume proof.
- **Dependencies:** S21D4-035.

### S21D4-037 — Materialise and validate explicit snapshots

- **Acceptance:** two immutable explicit datasets rebuild to identical identities; the fitted
  matrix is built from the fitting snapshot alone; all eleven scans pass over 390 fitted
  dimensions including allowlist, finite/range on every scalar and all 384 embedding
  dimensions, chronology, source chain, group split, contradictions, near-duplicates and
  perfect separation on both splits.
- **Dependencies:** S21D4-036.

### S21D4-038 — Resolve the invariance-regression sample

- **Deliverable:** `evidence/sprint-21d4-invariance-regression.json`.
- **Acceptance:** 40 transformed cases over the declared 20-group sample resolve with **zero
  verifier label changes and zero first-action changes**; every transformed feature record is
  sealed before its transformed candidate runs; the independent count of the transformed set is
  reported as zero, which is the property being regression-tested. Seeded semantic mutations
  change the canonical representation.
- **Dependencies:** S21D4-037.

### S21D4-039 — Measure the risk–coverage curve and select at most one candidate

- **Deliverable:** `evidence/sprint-21d4-learner-selection.json`.
- **Acceptance:** measures the strongest deterministic baseline on the same decisions; measures
  all 24 frozen settings crossed with the three operating points at both volume points;
  reports for each the independent decision count, coverage, first-choice rate, confident
  errors, changed decisions, the binomial upper bound, and maximum inference latency against the
  250 ms budget; applies the fixed selection precedence; and records **either** one candidate —
  setting, operating point, threshold value, dataset, split, feature and code identities — **or**
  an immutable null with its typed stop kind from Section 3.3 and the complete
  `dependent_not_opened` list.
- **Evidence:** the full grid, the curve at both volumes, the selection or null, its content
  hash, `final_or_canary_outcomes_inspected: 0`.
- **Dependencies:** S21D4-038.

## EPIC S21D4-E04 — Retrieval surface closure

### S21D4-040 — Widen the searchable surface

- **Deliverable:** the additive `search_terms` field and its projection.
- **Acceptance:** `structural_hash` and `ExperienceGraphNode.label` are byte-unchanged for every
  D1, D2 and D3 stored graph — proved by recomputation, not by inspection; old graphs
  deserialise under the default; the projection resolves sources, normalises through the
  released authority, bounds the output, applies the forbidden-marker guard, and fails closed on
  a `judgement_leaks` hit; edit paths still round-trip.
- **Evidence:** `evidence/sprint-21d4-surface.json` with the unchanged-hash proof over the D3
  graph root and the distinct-document count before and after.
- **Dependencies:** S21D4-018.

### S21D4-041 — Decide the bounded-GED comparator

- **Deliverable:** either the deterministic iteration budget or a typed retirement record.
- **Acceptance:** two identical passes agree byte for byte on every arm including this one, or
  the arm is retired with its measured instability as the reason. The D1/D2/D3 numbers stay
  marked irreproducible either way; nothing is back-filled.
- **Dependencies:** S21D4-016.

### S21D4-042 — Replay the development benchmarks under the widened surface

- **Deliverable:** `evidence/sprint-21d4-retrieval-development.json`.
- **Acceptance:** replays the frozen D1 80-query set and D3's spent holdout under the widened
  surface with an explicit `--policy-hash`, emits the complete pre-registered metric set with
  `timeouts` and `budget_cutoffs` separate, and reports per-arm repeated-order agreement.
  Development-only: it validates the implementation and selects nothing. Zero writes reach the
  D1, D2 or D3 stores.
- **Dependencies:** S21D4-040, S21D4-041.

### S21D4-043 — Resolve and seal the distinct retrieval holdout

- **Acceptance:** at least 60 new groups executed rather than declared through the released
  campaign runner and the same hidden verifier profile; queries and relevance judgements frozen
  and written to disk before the benchmark subprocess exists; every query excludes its own
  group; at least 50 qualify; zero reuse of any D1, D2 or D3 task signature or query id; the
  leak guard runs over the widened text and passes.
- **Evidence:** `evidence/sprint-21d4-retrieval-queries.json`.
- **Dependencies:** S21D4-042.

### S21D4-044 — Project and verify the new retrieval graph pairs

- **Acceptance:** projection succeeds on every group; sources resolve; edit paths round-trip;
  no bound moves; the integrity report catches a seeded missing blob, a broken authority link
  and tampered bytes, read-only, against the real root; the reported
  `distinct_after_removing_domain_and_signature` count is greater than one.
- **Evidence:** `evidence/sprint-21d4-retrieval-emg-root.json`.
- **Dependencies:** S21D4-043.

### S21D4-045 — Evaluate all frozen arms exactly once

- **Deliverable:** `evidence/sprint-21d4-retrieval-holdout-result.json`.
- **Acceptance:** every arm runs once; Recall@5, MRR@10, nDCG@10, p50/p95/max latency, coverage,
  candidate counts, timeouts, budget cutoffs, query/model/policy/root hashes, per-query rankings
  and per-arm repeated-order agreement are all reported; the uniformly-random chance baseline is
  reported beside them; no rerun after metrics are known.
- **Dependencies:** S21D4-044.

### S21D4-046 — Decide D1 condition 15 and Gate L2 condition 24

- **Acceptance:** records the first failed floor or the passing arm, hash-bound and immutable.
  No alternative fusion, width, weight, metric or holdout member is opened either way.
- **Dependencies:** S21D4-045.

### S21D4-047 — Preserve the advisory Experience Graph boundary

- **Acceptance:** proved, not asserted, under the widened surface: mandatory bundle sections are
  byte-identical whether or not retrieval contributed; an advisory candidate is never pinned,
  required or evidence and carries no executable body; an empty set degrades rather than fails;
  a corrupt store can only lower trust to `UNVERIFIED`.
- **Dependencies:** S21D4-045.

## EPIC S21D4-E05 — Artifact, runtime, and lifecycle readiness

### S21D4-048 — Extend the promotion payload for independent counts

- **Acceptance:** the condition-20 gate row carries nominal and independent decision counts and
  the calibration certificate hash; `not_measured` remains distinct from `failed`; precedence is
  still fixed by the gate tuple; v1 and D3 payloads stay readable through the schema-name
  dispatch.
- **Dependencies:** S21D4-018.

### S21D4-050 — Bind the derived threshold into the artifact

- **Acceptance:** `CorrectionArtifactPayloadV2` carries the operating point, its derivation
  rule, the calibration dataset and split identities it was derived from, and the certificate
  hash. The 390-channel order, the feature contract hash `492c90a5df420de9…`, the normaliser and
  the grammar are **unchanged**. Version confusion still fails before anything is built.
- **Dependencies:** S21D4-039 selects a candidate.

### S21D4-051 — Fit and store the selected artifact

- **Acceptance:** fitted from the fitting snapshot alone at the selected setting and operating
  point; stored as canonical inert JSON with complete lineage; the stored bytes rehash to the
  recorded address; the direct evaluation boundary's eleven refusal cases still refuse.
- **Dependencies:** S21D4-050.

### S21D4-052 — Prove the loader and resolver against the real artifact

- **Acceptance:** the 21-configuration matrix resolves against the real artifact and reaches
  every one of the 18 reason codes; `unreached_reason_codes: []`; the resolver still holds no
  direct-evaluation capability and imports no module that could reach a provider, the network,
  a GPU or a credential.
- **Dependencies:** S21D4-051.

### S21D4-053 — Route sequencing through the receipt-aware remainder

- **Acceptance:** the reconciled plan is the only authority on what may be attempted; a
  contradicted receipt makes the task unrunnable rather than partially runnable; the learned
  order decides what is tried first among what is left and never widens it; a resume restates
  deliberate skips.
- **Dependencies:** S21D4-051.

### S21D4-054 — Prove the selected-artifact vertical slice

- **Acceptance:** one fixture task runs end to end under the real artifact: resolution, ranking
  at the derived threshold, abstention to the deterministic order, hidden verification of every
  attempted candidate, receipt, restart replay, and wrong/corrupt/oversized artifact fallback.
- **Dependencies:** S21D4-052, S21D4-053.

### S21D4-055 — Re-prove mandatory-path and configuration invariance

- **Acceptance:** each of the 21 resolutions drives the sequencer and the attempted order is
  hashed by execution; every fallback configuration produces the identical decision hash and
  only the bounded campaign configurations differ. No constant is asserted.
- **Dependencies:** S21D4-052.

### S21D4-056 — Register the exact artifact and enter SHADOW

- **Acceptance:** registration binds the exact artifact hash, size, media type and lineage;
  `SHADOW` is entered through the released transition; zero executed decisions change.
- **Dependencies:** S21D4-054, S21D4-055.

### S21D4-057 — Exercise evidence-bound verification

- **Acceptance:** `verify_component()` re-reads the recorded assessment, the evidence row's
  payload artifact, the re-serialised payload hash, the model artifact's media type, hash and
  size, and rehashes both artifacts before the evaluator runs. `advance_component` still refuses
  a generic transition to `VERIFIED` and to `ACTIVE`. The assessment names the revision sitting
  in `SHADOW`, not the one it reaches after.
- **Dependencies:** S21D4-056.

### S21D4-058 — Revalidate artifact bytes immediately before activation

- **Acceptance:** both verification and activation call the one shared `_revalidate_bytes`;
  bytes replaced after verification leave the component in `VERIFIED` with the surface unheld;
  a substituted metadata row is caught; nothing is deserialised.
- **Dependencies:** S21D4-057.

### S21D4-059 — Authorise final access at one pre-final checkpoint

- **Deliverable:** `evidence/sprint-21d4-pre-final-checkpoint.json`.
- **Acceptance:** evaluates preconditions in backlog order and stops at the first failure —
  S21D4-039 selected one candidate; the continuation permits correction work; the artifact is
  stored; the vertical slice passed; the component is registered and in SHADOW; the independent
  retrieval branch reached a result. Records `authorised` with the exact canary and bounded
  steady-state configuration hashes and their transition condition, or `authorised: false` with
  one stop hash and a complete not-opened map over every dependent task.
- **Dependencies:** S21D4-046, S21D4-058.

## EPIC S21D4-E06 — Final evaluation and promotion evidence

### S21D4-060 — Seal final features and predictions before execution

- **Acceptance:** every final A and B feature record and every learned prediction is sealed
  before the corresponding outcome exists; chronology refusal is proved by a seeded
  post-outcome seal.
- **Dependencies:** S21D4-059 authorises access.

### S21D4-061 — Execute final batch A without replacement

- **Acceptance:** 120 new `REAL_GOVERNED_RUN` outcomes over the exact 30 sealed groups; no
  member substituted; every attempted candidate independently verified.
- **Dependencies:** S21D4-060.

### S21D4-062 — Execute final batch B as independent confirmation

- **Acceptance:** 120 new outcomes over the exact 30 sealed groups under the frozen protocol;
  B is not a repair set for A.
- **Dependencies:** S21D4-061.

### S21D4-063 — Compute paired material benefit

- **Acceptance:** at least 20 changed group decisions; at least 5 absolute points or 20%
  relative error reduction; paired group bootstrap seed 21041, 2,000 resamples, 95% lower bound
  above zero; direction positive in both batches; every abstention executes the baseline order
  and stays in the denominator.
- **Dependencies:** S21D4-062.

### S21D4-064 — Run safety and cross-domain anti-forgetting replay

- **Acceptance:** zero accepted-to-rejected safety, governance, permission, secret or
  destructive regressions; no retained domain loses more than 2 absolute points; aggregate loss
  at most 1 point.
- **Dependencies:** S21D4-062.

### S21D4-065 — Execute promotion-scale metamorphic/OOD evaluation

- **Acceptance:** at least 100 nominal decisions over the 60 final groups with the independent
  count reported beside them; false-confident rate at most 1%; **exactly zero confident errors**;
  errors reported over all decisions and over answered decisions; verifier failures reported
  separately from ranker errors.
- **Dependencies:** S21D4-062.

### S21D4-066 — Run true shadow mode against final evidence

- **Acceptance:** zero executed decisions change; outcome linkage uses only verifier evidence.
- **Dependencies:** S21D4-062.

### S21D4-067 — Build the strengthened promotion assessment

- **Acceptance:** all twenty gates carry an outcome, the evidence hash it came from and a
  detail string; identity is checked before measurement; the payload is inert bytes in the
  Artifact Store and the assessment names its artifact id and byte hash.
- **Dependencies:** S21D4-063 through S21D4-066.

### S21D4-068 — Assess the three open Gate D1 conditions

- **Acceptance:** condition 6 against the 240 unique eligible verifier-backed outcomes;
  condition 7 against the changed-decision evidence; condition 15 against S21D4-046. Each
  closes or stays open on its own evidence.
- **Dependencies:** S21D4-067, S21D4-046.

### S21D4-069 — Advance through evidence-bound verification

- **Acceptance:** `SHADOW -> VERIFIED` only through `verify_component()` with the real payload;
  the transition records the assessment hash atomically.
- **Dependencies:** S21D4-067.

## EPIC S21D4-E07 — Approval, canary, activation, and rollback

### S21D4-070 — Prepare the exact activation bundle

- **Acceptance:** the bundle binds component, revision, surface, artifact lineage, assessment
  hash, and the two sealed configuration documents with their transition condition. Sealing
  happens here, at authorised access, not earlier.
- **Dependencies:** S21D4-069.

### S21D4-071 — Record explicit human approval

- **Acceptance:** exactly the existing fields; no invented field; no self-approval; no model or
  provider approver; the repository's single-collaborator reality is documented rather than
  worked around.
- **Dependencies:** S21D4-070.

### S21D4-072 — Activate canary-only routing atomically

- **Acceptance:** one routed group, 20 tasks, the exact canary configuration hash; activation
  revalidates bytes; a mismatch refuses atomically and stays deterministic.
- **Dependencies:** S21D4-071.

### S21D4-073 — Execute the governed canary with stop-first semantics

- **Acceptance:** verifier mandatory on every attempt; first failure stops; receipt-safe.
- **Dependencies:** S21D4-072.

### S21D4-074 — Exercise kill switch, disable, and fallback after restart

- **Acceptance:** exactly one cause-bound disable; immediate deterministic fallback; the
  fallback survives restart.
- **Dependencies:** S21D4-073.

### S21D4-075 — Prove receipt-selected rollback restoration and refusal

- **Acceptance:** a previously approval-bound valid state restores; a failed canary is
  structurally non-restorable; rollback deletes no evidence and survives restart.
  **Unconditional** — runs against the isolated lifecycle fixture whether or not D4 activates.
- **Dependencies:** none beyond S21D4-002.

### S21D4-076 — Promote from canary routing to bounded steady state

- **Acceptance:** the transition condition is met on canary evidence; three groups, 200 tasks,
  the exact steady-state configuration hash.
- **Dependencies:** S21D4-074, S21D4-075.

### S21D4-077 — Prove final active state and replacement readiness

- **Acceptance:** the active projection matches the ledger; a replacement candidate would follow
  the same governed path; zero online updates to active exemplars or thresholds.
- **Dependencies:** S21D4-076.

## EPIC S21D4-E08 — Operations, recovery, CI, and complete validation

### S21D4-080 — Extend the D4 evidence CLI narrowly

- **Acceptance:** `scripts/learned.py d4-integrity` is read-only, offline by default, prints one
  line of canonical sorted JSON, and refuses any database name lacking `s21d4` and each of the
  five predecessor roots by absolute path, on values, before anything is opened.
- **Dependencies:** S21D4-002.

### S21D4-081 — Extend unified integrity and health reporting

- **Acceptance:** the eleven released classes plus one new class, `decision_independence`, which
  fails when any evidence file reports a rate over a nominal denominator. Four states retained;
  a class nobody checked warns rather than passes; a stored pass without its evidence fails
  closed. Every class has a seeded violation.
- **Dependencies:** S21D4-080.

### S21D4-082 — Verify provisioning without broadening authority

- **Acceptance:** read-only: migration head `0015`, no `0016` on disk in
  `infra/postgres/alembic/versions`, schema ownership, extensions, and
  `postgres_bootstrap_roles.sh` hashed and not invoked.
- **Dependencies:** S21D4-002.

### S21D4-083 — Prove replay, restart, backup, and isolated restore

- **Acceptance:** backup with the repository's own script, container restart, restore into the
  D4 restore database; counts, hashed-row roll-up, both resume inputs and every blob rehash
  reproduce; the integrity report over the restored copy is clean; the lifecycle state restores
  as whatever it actually is.
- **Dependencies:** S21D4-082.

### S21D4-084 — Exercise corruption, substitution, and isolation failures

- **Acceptance:** the released 18-case matrix plus two D4 cases — a forged independent-decision
  count and a threshold derived from a set other than the calibration split — all failing
  closed against extracted copies, with every predecessor fingerprint identical before and after.
- **Dependencies:** S21D4-083.

### S21D4-085 — Add focused credential-free CI

- **Acceptance:** the `learned-evidence-core` lane runs the independence tests with their seeded
  violations and the released `d4-integrity` command over the committed evidence, both
  credential-free by construction.
- **Dependencies:** S21D4-081.

### S21D4-086 — Run the complete release matrix on scratch authorities

- **Acceptance:** every row is the released command, not an invented equivalent; negative rows
  refuse for their declared reason; each recorded row names its duration and output hash; no
  hidden skip.
- **Evidence:** `evidence/sprint-21d4-verification-matrix.json`.
- **Dependencies:** S21D4-084, S21D4-085.

## EPIC S21D4-E09 — Documentation, gate, protected release, and handoff

### S21D4-090 — Update architecture and operator documentation

- **Acceptance:** extends the released operations documents rather than adding a third; every
  command shown was run; the three things easiest to misread are stated — that a `warning` class
  is not a pass, that a replicated decision is not a decision, and that a widened surface is a
  leak until the guard proves otherwise. No future capability is described as implemented.
- **Dependencies:** S21D4-086.

### S21D4-091 — Prepare a versioned D4 Gate L2 assessment

- **Deliverable:** `gate-l2-d4-assessment.md`, a versioned successor that touches neither the
  D2 nor the D3 assessment.
- **Acceptance:** the condition table is generated by `scripts/gate_assessment_d4.py` from the
  frozen gate manifest and the produced evidence; a condition with no bearing evidence is
  `not_opened` bound to its stop hash, never `met`; the script cannot assert a pass.
- **Dependencies:** S21D4-090.

### S21D4-092 — Complete the Sprint 21D4 report

- **Acceptance:** states the outcome, the independence erratum, the risk–coverage result at both
  volumes, the retrieval result under the widened surface, every finding with an ID, and the
  limitations — including that a passing D4 measures one surface with authored tasks and a
  frozen encoder.
- **Dependencies:** S21D4-091.

### S21D4-093 — Prepare the outcome-specific handoff

- **Acceptance:** on a pass, states exactly what Sprint 22A inherits and what it must not
  assume. On a stop, names the smallest next experiment from the typed stop kind: `volume_bound`
  hands over a corpus sprint with a target volume derived from the measured curve;
  `hypothesis_class_bound` hands over the first hypothesis class worth pre-registering and the
  evidence that justifies it.
- **Dependencies:** S21D4-092.

### S21D4-094 — Complete the protected implementation release

- **Acceptance:** the implementation, evidence, report and provisional assessment PR merges
  under unchanged protection; exact-head post-merge `main` CI succeeds; the one permitted
  annotated tag is created at that release commit and pushed.
- **Dependencies:** S21D4-093.

### S21D4-095 — Complete gate-close release evidence and remote verification

- **Acceptance:** a gate-close documentation PR from current `main` adds the remote-derived
  release JSON and final assessment handles; it merges under unchanged protection; its
  post-merge `main` CI succeeds; `origin/main`, the immutable tag object and peeled commit, both
  CI runs and the protection state are re-read. On a pass, and only after this item, the handoff
  unblocks Sprint 22A. The tag is never moved or recreated.
- **Dependencies:** S21D4-094.

---

## 6. Execution waves and dependencies

| Wave | Tasks | Exit |
|---|---|---|
| W0 — authority and design | 000–018 | D3 release verified, independence erratum published, isolated roots, revision 4 committed before measurement |
| W1 — independence and threshold spine | 020–024 | counting rule, operating-point rule, D3 grid replayed under corrected denominators, typed continuation |
| W2 — fresh evidence at scale | 030–039 | 100 authored calibration groups sealed first, 320-row fitting, risk–coverage curve at two volumes, one candidate or a typed null |
| W3 — retrieval surface | 040–047 | widened surface with unchanged structural hashes, comparator decided, 50+ new queries, D1 condition-15 decision |
| W4 — artifact and runtime | 048, 050–055, 057, 056, 058–059 | the D3-built surface exercised against a real artifact, then one pre-final access decision |
| W5 — final evidence | 060–069 | final A/B, benefit, retention, promotion OOD, shadow, assessment, VERIFIED or negative stop |
| W6 — governed activation | 070–077 | approval, canary, kill switch, restart, rollback, bounded steady state; otherwise not opened |
| W7 — operations | 080–086 | CLI/health, isolated recovery and corruption proofs, complete local matrix |
| W8 — release | 090–095 | outcome report/assessment/handoff, protected release, tag, gate-close record |

The two experiment branches stay independent after W0:

```text
revision 4
  +-> independence + selective threshold -> fresh calibration -> candidate -> final -> lifecycle
  |
  +-> widened searchable surface -> distinct unseen holdout -> D1 condition 15

both branch verdicts + operations -> Gate L2 outcome -> protected release
```

A correction stop does not cancel the retrieval branch and a retrieval failure does not
authorise correction activation. No branch may tune itself from the other branch's holdout.

**W2 is the schedule risk.** Authoring 100 executed four-candidate groups is the largest single
deliverable in the sprint and it gates everything downstream on the correction branch. If W2
cannot reach 100 groups, the honest response is to author fewer, record the achieved
independent-decision count, and let Section 2.3's floor decide the outcome — not to reduce the
floor or to reinstate replicated decisions to reach it.

### 6.1 First vertical slice

Before bulk campaigns, S21D4-033 must prove, on a dedicated fixture group outside every role:

1. one rights-clean four-candidate task package;
2. canonical v2 bytes and named scalar and embedding channels, unchanged from D3;
3. pre-outcome feature seal and receipt-bound self-play execution;
4. independent hidden-verifier labels and role-bound observation projection;
5. explicit dataset identity and full fitted-matrix scanning;
6. one ranking at a derived operating point, its abstention, and the baseline fallback;
7. canonical artifact reload, receipt-aware stop-on-first-accept and exact missing-outcome
   resume;
8. wrong, corrupt and oversized artifact fallback, restart, replay, backup and restore;
9. final and retrieval capabilities refusing access.

### 6.2 Pull-request and release strategy

One coherent implementation PR by default. A small pre-registration-only PR is allowed only if
campaign execution must begin from protected authority, and it must merge before any number it
governs is measured. Do not split final evidence into an ungoverned artifact PR.

The release sequence has two protected documentation states, unchanged from D3:

1. implementation, evidence, report and provisional-assessment PR merges;
2. exact-head `main` CI passes;
3. create and push the one permitted annotated outcome tag at that release commit;
4. from current `main`, add remote-derived release JSON and final assessment handles in a
   gate-close documentation PR;
5. merge the gate-close PR under unchanged protection and wait for its post-merge `main` CI;
6. re-read `origin/main`, the immutable tag object and peeled commit, both CI runs, and
   protection.

The gate-close commit is expected to be newer than the tag. It must not move or recreate the
annotated tag.

---

## 7. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| release baseline | D3 tag object/peel, current main, both PR/CI chains, protection, migration, collaborator | wrong or unprotected parent |
| D3 reconciliation | the 6x replica identity recomputed from D3 evidence for all 24 settings | D4 is built on an unproven erratum |
| store isolation | five predecessor fingerprints unchanged | predecessor evidence contaminated |
| revision chronology | revision 4 predates every D4 calibration, threshold, campaign and retrieval number | intervention chosen after results |
| decision independence | nominal, independent and replicated counts everywhere; no rate over a nominal denominator | a replicated set inflates a safety sample again |
| feature invariance | canonical source, vector and ranking equality under the two regression transforms | encoder regressed |
| semantic sensitivity | seeded operator/condition mutation changes the canonical representation | normaliser erased task meaning |
| complete matrix scan | scalar and all 384 embedding dimensions pass validity and leakage scans | hidden fitted channel escaped audit |
| dataset identity | feature, partition, campaign, role and explicit member digest bound | stale D3 dataset silently reused |
| data roles | exact fitting/calibration/final/canary/retrieval manifests and transitive groups | fitting and evaluation overlap |
| chronology | features and final predictions predate their outcomes | post-outcome leakage |
| campaign resume | manifest, mode, order, bundle and seal bound; only exact missing work repeats | restart fabricates or duplicates evidence |
| sample | 80/320 fitting, 100/400 calibration, 120/30 each final, 5/20 canary | underpowered or role-ineligible result |
| operating point | derived once, from the calibration split only, sealed into the candidate | threshold chosen after seeing an outcome |
| calibration certificate | zero confident errors over at least 100 independent decisions, with its binomial bound | zero-error claim is unsupported by its sample |
| non-silence | coverage floor and projected changed-decision count | abstention passes by avoiding the test |
| final access | one setting, operating point and artifact frozen before any final body or outcome | holdout selected the model |
| baseline/learner ladder | strongest honest deterministic rung and all 24 settings at all three operating points | straw baseline or hidden tuning |
| artifact | canonical inert JSON, exact v2 lineage, threshold provenance | model cannot be reproduced safely |
| runtime resolver | durable, config, artifact and model agreement with named fallback | active claim differs from actual runtime |
| verifier boundary | learned order only; every attempted candidate independently verified | learner gained acceptance authority |
| final benefit | 20 changes, fixed effect threshold, two batches, positive paired lower bound | usefulness claim unsupported |
| safety/retention | zero critical regression and fixed domain and aggregate bounds | catastrophic forgetting or unsafe ordering |
| promotion OOD | 100+ nominal decisions with the independent count beside them, zero confident errors | invariant and safe action unsupported |
| shadow | zero executed changes and verifier-only outcome links | shadow mutated behaviour |
| retrieval surface | D1/D2/D3 structural hashes byte-unchanged; distinct-document count above one; leak guard clean | the fix changed frozen evidence or leaked its own label |
| retrieval reproducibility | two identical passes agree on every arm, or the unstable arm is retired | an irreproducible number is reported a fourth time |
| retrieval usefulness | 50+ disjoint unseen queries and one arm at both floors | D1 condition 15 remains open |
| lifecycle verification | assessment-bound VERIFIED transition and activation-time byte rehash | generic advance or stale artifact bypass |
| approval | exact eligible human approval, no self-approval | component or provider authorised itself |
| canary | exact subset, receipt-safe stop-first, verifier, first-failure stop | activation unbounded or decorative |
| kill switch/rollback | one cause-bound disable, restart fallback, receipt-selected restoration, failed-canary refusal | learned behaviour cannot be stopped or recovered safely |
| recovery | database, artifact, receipt, dataset and lifecycle exact restore | evidence is ephemeral or split-brain |
| release | complete local matrix, protected PRs, exact-head CIs, immutable remote tag | result is not release-grade |

### 7.1 Required local command classes

Use the repository's locked environment and record exact commands, duration, exit status and log
hash. At minimum the final matrix includes equivalents of:

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run ruff check --config ruff.cognitive-os.toml src tests scripts infra
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run ruff format --check --config ruff.cognitive-os.toml src tests scripts infra
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run pytest -q
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run mypy src/cognitive_os
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run bandit -q -r src
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run python -m cognitive_os.schemas.export --check
./scripts/check_repository_language.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/run_postgres_integration_tests.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/verify_distribution.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv ./scripts/verify_editable_install.sh
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv uv run pip-audit
git ls-files -z | xargs -0 uv run detect-secrets-hook --baseline .secrets.baseline
```

The D4 matrix adds focused independence, operating-point, retrieval-surface, lifecycle,
recovery and negative-boundary rows. Live providers and credentials are not a release
dependency.

---

## 8. Quantitative acceptance thresholds

### 8.1 Dataset and separation

- fitting: the audited eligible group set, 80 groups and 320 new `SELF_PLAY` outcomes;
- calibration: 100 fresh groups and 400 new `SELF_PLAY` outcomes, at least 15 template families;
- final A and B: exact reused 30 groups / 120 outcomes each, or a fully replaced role at no
  less than the same target; never below 25/100;
- canary: exact 5 groups and 20 sealed candidate slots;
- retrieval: at least 60 new groups until at least 50 qualifying unseen queries remain;
- zero `REAL_GOVERNED_RUN` observation in fitting or calibration;
- zero task, repository, template, source or near-duplicate group crossing any role;
- zero final or canary outcome or prediction access before S21D4-059;
- exact explicit members only; surface totals and latest seals are never dataset selectors.

### 8.2 Independence, invariance and calibration

- at least **100 independent** clean calibration ranking decisions;
- every reported rate names its denominator and uses the independent one;
- 100% byte and hash equality for canonical source and fitted vector under the two regression
  transforms, and zero verifier label changes across the 40 transformed cases;
- 100% detection of seeded unstable or label-perfect embedding dimensions;
- **exactly zero confident errors among answered independent calibration decisions** at the
  selected operating point, with its binomial 95% upper bound reported;
- clean coverage at least 0.40 and enough to project at least 20 changed final decisions;
- clean first-choice rate over answered decisions strictly above the strongest deterministic
  baseline on the same decisions;
- at least one changed clean decision;
- all 24 settings at all three operating points reported, including filtered and fully
  abstaining ones;
- the risk–coverage curve reported at both volume points, with coverage-at-zero-error at each.

### 8.3 Learned material benefit

- at least 20 final group decisions differ from the strongest deterministic baseline;
- at least +5 absolute percentage points first-choice verified success or at least 20% relative
  error reduction;
- paired group bootstrap seed 21041, 2,000 resamples, 95% lower bound above zero;
- learned-minus-baseline direction strictly positive in final A and final B;
- all abstentions execute baseline order and remain in every relevant denominator;
- malformed, timeout, verifier-failed and no-accepted-candidate tasks stay visible;
- latency, verifier and provider call counts, failures, and zero or actual costs use exact
  denominators;
- maximum measured inference at or below the 250 ms budget.

### 8.4 Retention, OOD, and authority

- zero accepted-to-rejected safety, governance, permission, secret or destructive case;
- no retained domain loses more than 2 absolute points; aggregate loss at most 1 point;
- at least 100 nominal promotion ranking decisions over at least 10 groups, with the
  independent count reported beside them;
- false-confident rate at most 1%; promotion exactly zero confident errors;
- errors reported both over all decisions and over answered decisions;
- shadow changes zero executed decisions;
- every learned-first correction still passes the independent verifier;
- missing, corrupt, oversized, wrong, inactive, disabled and unapproved cases fall back
  immediately with a structured reason;
- zero model or provider approvals and zero online updates to active exemplars or thresholds.

### 8.5 Retrieval

- `structural_hash` and node `label` byte-unchanged for every D1, D2 and D3 stored graph;
- `distinct_after_removing_domain_and_signature` strictly greater than one, and reported;
- zero `judgement_leaks` hits over the widened searchable text;
- at least 50 new unseen-task queries, wholly disjoint from every correction role and from D1,
  D2 and D3 queries;
- at least one bounded arm reaches Recall@5 `>= 0.70` and MRR@10 `>= 0.50`;
- nDCG@10, coverage, candidates, p50/p95/max, timeouts and budget cutoffs reported separately;
- repeated-ranking agreement 100% on every arm still in the frozen set; at most 10 returned
  results;
- graph limits unchanged: 64 nodes, 128 edges, depth 32, shortlist 20, query budget 2 seconds;
- the uniformly-random chance baseline reported beside every arm;
- RRF constant 60 and equal weights never tuned; no silent timeout, cutoff, query drop,
  judgement read, or rerun after metrics are known.

### 8.6 Release and persistence

- migration remains `0015` unless a separately approved measured gap justifies `0016`;
- 100% stored metadata, hash, size and recomputed artifact-byte agreement;
- exact backup and restore database counts, hashed-row roll-up, all D4 artifact hashes,
  campaign receipts, explicit datasets, retrieval roots, and outcome-appropriate lifecycle
  state;
- zero writes to the development, C3, D1, D2 and D3 pairs;
- every verification-matrix row reaches its predeclared expected status; no hidden skip;
- every required PR check and both post-merge `main` CI runs succeed;
- exactly one outcome tag: success `sprint-21-learning-baseline`, otherwise
  `sprint-21d4-evidence-baseline`; local and remote annotated objects match.

---

## 9. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| D3 never released | S21D4-000 cannot resolve the D3 tag | do not start D4; complete S21D3-094 and -095 or establish a new baseline |
| erratum unproven | the D3 grid replay does not reproduce | stop with `reconciliation_not_reproducible`; nothing downstream may assume the collapse |
| replicated decisions return | any rate reported over a nominal denominator | fail contract validation; recompute without changing outcomes |
| corpus under-delivers | fewer than 100 calibration groups authored | record the achieved independent count and let the floor decide; never reinstate replicas to reach it |
| corpus is one family with 100 seeds | fewer than 15 template families or a near-clone hit | the separation detector fails closed; author diversity rather than tune the detector |
| threshold shopping | more than one derivation, or a derivation from any set but calibration | invalidate selection; the derived point is single-shot by contract |
| coverage floor gamed | the selected point projects fewer than 20 changed final decisions | reject the setting at selection; do not discover it after final access |
| surface change breaks frozen evidence | any D1/D2/D3 `structural_hash` moves | revert the field placement; it must be excluded from every existing hash |
| widened surface leaks | `judgement_leaks` hits, or a perfect holdout score | treat a perfect score as a leak until proved otherwise, exactly as W3-F2 did; re-resolve from scratch |
| irreproducible arm again | repeated-order agreement below 100% after the budget change | retire the arm rather than report a fourth irreproducible number |
| D3-built surface has latent defects | the loader, resolver, sequencer or verification path needs changes | record each as a finding with an ID; it is a D3 defect found by first real use, not planned work |
| CI lane boundaries | a new import drags SQLAlchemy or a store into a unit lane | keep production functions in released modules, not in scripts; the W3-A2 and W1 boundaries are precedent |
| stale artifact at activation | bytes or metadata differ after assessment or approval | activation atomically refuses and remains deterministic |
| verifier authority drift | learned prediction accepts or skips hidden verification | fail the gate immediately; disable the active path if reached |
| reviewer fiction | a model, provider or fabricated collaborator approves | reject the record; keep the approval requirement unset and document reality |
| predecessor contamination | any D4 write changes a predecessor fingerprint | stop destructive work, preserve evidence, diagnose from an isolated copy |
| speculative complexity | new migration, dependency, model or database without a measured ADR | remove or defer; use existing authority or record a successor need |
| checks that measure nothing | a check passes against a path, glob or constant that does not exist | four such defects recurred across D3's waves; read every new evidence file against the question it claims to answer before it is committed |
| incomplete negative path | a downstream task absent without a stop-bound record | sprint not done; materialise the typed not-opened chain |
| premature tag | tag created before exact-head implementation CI | do not move it; publish a correctly named release only under an explicit recovery plan |

---

## 10. Stop, rollback, and failure decisions

### 10.1 Before fresh campaigns

- Baseline, reconciliation, isolation, pre-registration chronology, final-reuse, grouping or
  independence-counting failure stops correction execution.
- A grid replay that cannot reproduce D3's recorded values produces `fail_and_stop`; no second
  counting rule opens inside D4.
- Independent retrieval may continue if its own revision, groups, authority and stores remain
  valid.

### 10.2 Before correction final access

- Any matrix, dataset, chronology, calibration, independence, coverage, invariance-regression,
  artifact, loader, resolver, SHADOW or checkpoint failure records one null and leaves final
  A/B and canary unopened.
- `volume_bound` and `hypothesis_class_bound` are both null selections. Neither authorises a
  parametric rung, a threshold revision or a refit inside D4; each names a different successor.
- Retrieval continues independently; its result does not authorise correction final access.

### 10.3 After correction final or retrieval holdout access

- Any change to the selected candidate, artifact, feature, threshold, baseline, metrics,
  resource policy, surface field, manifest, judgement or member invalidates the affected
  experiment.
- Final B runs after A only under the frozen protocol, never to choose a repair.
- Any aggregate, per-batch, bootstrap, safety, retention, OOD, shadow, retrieval or evidence
  failure keeps Gate L2 closed and forbids approval and activation.
- The outcomes remain immutable evaluation evidence. A successor requires a new revision and a
  new untouched holdout; D4 final data never becomes fitting data.

### 10.4 After activation

- The first canary safety, integrity, budget, OOD, artifact, verifier or receipt failure
  triggers immediate disable and deterministic fallback.
- A failed canary cannot be restored through rollback; only a previously approval-bound valid
  state is eligible.
- Missing, corrupt or stale bytes and configuration mismatches fall back without an operator
  round trip.
- Rollback deletes no evidence and must survive restart and restore.

---

## 11. Definition of Done

### 11.1 Required for every outcome

Sprint 21D4 is complete only when:

- the D3 release exists and S21D4-000 through S21D4-018 establish current authority and revision
  4 before any D4 measurement;
- the D3 decision-independence erratum is published without rewriting protected history;
- every predecessor store is unchanged and D4 recovery uses isolated authorities;
- every opened role uses exact members, feature-, schema- and partition-aware identity,
  transitive group separation, pre-outcome seals, and complete scalar and embedding scans;
- every reported rate names its denominator and uses the independent one;
- both independent branches reach a hash-bound result or a valid first-failure result;
- every dependent conditional task has completed evidence or a transitive typed `not_opened`
  record; baseline, S21D4-075, operations, report, gate and release tasks are never not opened;
- all applicable unit, integration, PostgreSQL, recovery, corruption, packaging, schema,
  security, language and deterministic CI checks pass;
- one outcome-specific report, a versioned D4 assessment and an exact handoff exist;
- the protected implementation and gate-close PRs merge without weakened controls;
- exact-head post-merge `main` CI succeeds after both merges;
- exactly one permitted annotated tag is verified locally and remotely against its immutable
  implementation release commit.

### 11.2 Additional positive-path requirements

Gate L2 passes, and Sprint 22A unblocks, only when:

- the independence reconciliation reproduces and the counting rule is in force everywhere;
- the fresh calibration set yields at least 100 independent decisions and the fitted matrix
  passes every scan;
- one frozen k-NN setting at one pre-registered operating point produces zero confident errors
  over those decisions at coverage at least 0.40 with at least 20 projected changed final
  decisions, and one reproducible v2 artifact is selected before final access;
- final A and B each contain 120 new real-run outcomes over 30 groups, at least 20 decisions
  change, material benefit and the paired interval pass, and the direction is positive in both
  batches;
- safety, retention, promotion OOD with zero confident errors, shadow, artifact and fallback,
  and all fixed authority conditions pass;
- at least one frozen retrieval arm passes both floors on at least 50 distinct new queries under
  the widened surface, with every remaining arm reproducible;
- the component follows REGISTERED -> SHADOW -> VERIFIED through evidence-bound verification;
- an eligible human approves the exact existing contract fields, binding artifact and
  configuration bytes transitively through assessment and lineage, and activation revalidates
  those bytes;
- canary, kill switch, restart, disable, valid restoration, rollback rehearsal, bounded steady
  state and the final active projection pass;
- Gate D1 conditions 6, 7 and 15 close and `sprint-21-learning-baseline` is the verified tag;
- only after the gate-close PR and its CI does the handoff unblock Sprint 22A.

### 11.3 Valid negative-path completion

A negative D4 is complete when:

- the first failed pre-registered condition and every opened result are immutable;
- no forbidden downstream correction or retrieval data was opened after its stop;
- all dependent tasks carry typed `not_opened` evidence bound to that stop hash;
- the independent branch was completed while still valid, so useful evidence is not discarded;
- the typed stop kind is one of the pre-registered ones and the handoff names the single
  successor experiment it implies;
- applicable fixture, local, operations, recovery, security and CI checks pass;
- no failed component remains active; any approval and activation history created before a
  canary, restart or post-activation failure is preserved, the failed path is disabled, a failed
  canary is structurally non-restorable, and the success tag does not exist;
- `sprint-21d4-evidence-baseline` is annotated once after successful implementation CI and
  verified remotely;
- the final D4 assessment says Gate L2 does not pass, preserves the unresolved D1 conditions,
  keeps Sprint 22A blocked, and hands off the smallest evidence-backed successor experiment.

A green PR without either the complete positive release or this complete negative release is a
checkpoint, not Sprint 21D4 completion.

---

## 12. Expected deliverables

At minimum:

- this backlog plus an aligned D4 handoff and updated execution allocation;
- D4 baseline, D3 decision-independence reconciliation, predecessor inventory, store-isolation
  and final-reuse eligibility records;
- revision-4 independence, operating-point, corpus-reallocation, surface, power, transformation,
  retrieval, gate and stop manifests;
- the independent-decision counting rule, the zero-error operating-point rule, and the D3 grid
  replayed under corrected denominators;
- 100 authored calibration groups and at least 60 authored retrieval groups, all executed rather
  than declared, with a published defect ledger;
- an enlarged fitting campaign, a fresh calibration campaign, explicit snapshots, full matrix
  validation, the invariance-regression result, and the risk–coverage curve at two volumes;
- one candidate selection with its sealed operating point, or a typed null naming its successor;
- one additive searchable-surface field with its unchanged-hash proof, a decided bounded-GED
  comparator, a distinct 50+ query holdout, and a D1 condition-15 result on every valid path;
- on the candidate path, the canonical v2 artifact and the first real exercise of the loader,
  resolver, sequencer, verification, invariance and pre-final checkpoint surfaces D3 built;
- on the final path, 120/30 final A and 120/30 final B outcomes, paired benefit, retention,
  promotion OOD, shadow, the promotion assessment, the D1 mapping and the VERIFIED state;
- on the positive path, the activation bundle, human approval, canary, kill switch, restart,
  restoration, rollback, bounded steady state and final active projection;
- on every path, canonical not-opened records for every inapplicable conditional deliverable;
- updated correction-ranking and Experience Graph operations and architecture documents, CLI,
  integrity, health, provisioning, backup and restore, corruption and isolation proofs, focused
  CI, and the complete local verification matrix;
- an outcome-specific D4 report, a versioned Gate L2 assessment, a handoff, protected
  implementation and gate-close release evidence, and one remotely verified annotated tag.
