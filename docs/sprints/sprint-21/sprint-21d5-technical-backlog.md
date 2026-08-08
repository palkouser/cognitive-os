# Sprint 21D5 Technical Backlog

## Pairwise Selective Correction Ranking, Complete Searchable Surface, and Gate L2 Closure

- Predecessor: Sprint 21D4, tag `sprint-21d4-evidence-baseline`, object
  `0f1e4c897c72cedc530bb599c4d7af8e647b2774`, peeling to
  `18564a55e65f7b331bc73fc334ee1ab085cf0836`; PR `#223`; exact-head post-merge `main` CI run
  `31245482819`, 30 of 30 success.
- Groundwork already merged: PR `#225` — the hypothesis class, the completed surface, and the
  diagnostic that justifies both.
- Gate contract: **unchanged**, `9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7`,
  29 conditions, 0 thresholds changed. D5 changes no floor.
- Migration head: `0015`. D5 allocates **no** migration; `0016` stays unallocated.
- Outcome tags: success `sprint-21-learning-baseline` (does not exist yet, checked by D4);
  negative `sprint-21d5-evidence-baseline`.

**This backlog is deliberately a third the size of D4's, and that is its main design decision.**
Sprints 21D1 through 21D4 built the substrate: the independence counting rule, the operating-point
derivation, the artifact, loader, resolver, sequencer, promotion, shadow, canary, activation and
rollback surfaces, the twelve-class integrity report, the truncation fence, the release matrix and
the release process. All of it is released and none of it is rebuilt here. D5 writes four new
things and *runs* the rest.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](sprint-21d4-technical-backlog.md) are the execution contract for
D5 unchanged, and are incorporated by reference rather than restated: release-grade meaning of
done, the efficiency-first implementation rule, the evidence-role boundary, and the
negative-result and no-retuning rule. Three of them carry a D5-specific reading.

**Evidence-role boundary (§0.3).** D4's spent evidence changes role in D5 and the change is
one-directional:

| D4 evidence | D5 role | Forbidden in D5 |
|---|---|---|
| 80 fitting groups / 320 outcomes | fitting | any selection or coverage decision |
| 100 calibration groups / 400 outcomes | **fitting** | any selection, threshold or coverage decision |
| 60 retrieval groups and their 60 queries | nothing — fully spent | every use |
| final A (30 groups / 120 slots) | final A, unopened and carried | opening before S21D5-059 |
| final B (30 groups / 120 slots) | final B, unopened and carried | opening before S21D5-059 |
| canary (5 groups / 20 slots) | canary, unopened and carried | opening before S21D5-071 |

The second row is the one a reader must not misread. The D4 calibration set has been read by two
selection rules — the k-NN grid's, and this session's diagnostic. It is spent *for selection*
forever, and the D5 handoff authority that permits it as fitting evidence
([Sprint 21D5 handoff](sprint-21d5-handoff.md) §2) permits nothing else. Every D5 number that
decides anything divides by decisions taken on the **freshly authored** calibration set.

**No-retuning rule (§0.4).** The class, its regulariser, its confidence definition and every floor
are frozen in revision 5 before the D5 calibration corpus is resolved. λ = 1 was chosen on
fitting-pool-internal leave-group-out evidence and is recorded in
[`sprint-21d5-hypothesis-class-diagnostic.json`](evidence/sprint-21d5-hypothesis-class-diagnostic.json),
integrity hash `d9027c71dc5f6fc5de58f7120ab885f9a54a707ad88ac19c3aa0fc92eaeafbd9`. It is not
re-chosen in D5. A D5 that misses a floor stops; it does not search for a λ that would not have.

**Efficiency-first rule (§0.2), stated as the D5 ladder.** Before any item writes code, in order:
does the released code already do it; does the released code do it with one new argument; does one
new function beside it do it. A new module is the fourth answer, not the first, and this backlog
reaches it exactly once (`CorrectionArtifactPayloadV3`).

---

## 1. Verified starting state

### 1.1 What D4 released and D5 inherits

Verified at S21D5-000 against the remote, never assumed:

- `origin/main` at or after `fe8a9cf`, the D4 gate-close commit;
- the annotated tag `sprint-21d4-evidence-baseline` peeling to `18564a55`;
- the success tag `sprint-21-learning-baseline` **absent**;
- branch protection unchanged: administrators enforced, 27 required checks, strict, no force
  pushes, no deletions;
- migration head `0015`;
- five predecessor stores fingerprinted and unchanged.

### 1.2 What PR #225 added, and what it is not

| Landed | What it is | What it is **not** |
|---|---|---|
| `learning/pairwise_contrastive.py` | the hypothesis class: one linear direction on within-group accepted-minus-rejected differences, confidence = top-2 projection margin | a selection, a threshold, or a fitted artifact |
| `graph_projection.search_terms_from_source(structure_fallback=…)` | off-by-default AST node-type fallback for sources with no identifier terms | a re-decision of S21D4-046 |
| `scripts/hypothesis_class_diagnostic_d5.py` + sealed record | a diagnostic on spent evidence, authorised by the handoff | evidence for any Gate L2 condition |
| `sprint-21d5-hypothesis-class-proposal.md` | the §3.4 recommendation the D4 continuation rule permits | a pre-registration |

The diagnostic measured, over the 100 spent independent calibration decisions:

| estimate | fitted pool | first-choice rate | zero-error coverage |
|---|---|---:|---:|
| frozen k-NN, best of 144 cells (S21D4-039) | 80 groups | 0.735 over admitted | **0.0000** |
| pairwise class, disjoint pool | 80 fitting groups | 0.79 | **0.22** |
| pairwise class, combined-pool leave-group-out | 179 spent groups | 0.84 | **0.32** |

**0.32 is below the unchanged 0.40 floor, and D5 is the sprint that finds out whether a fresh
corpus and a larger fitting pool close the gap.** Nothing in this backlog treats 0.32 as a
prediction. §3.3 pre-registers what happens at every outcome.

### 1.3 The two immutable D4 stops

Neither is re-decided. D5 measures something else, on something else.

- Correction: `5caa48970898d180ce1f339771399f42af74555a91af2f87e97d1f36c6086c8e`,
  kind `hypothesis_class_bound`. D5's answer to it is a different class, not a different corpus
  for the same class.
- Retrieval: `bf929d85f1544b6d4c3508107dd3610134bcc399f728893b5f510e673ccbc818`, MRR@10 0.4911
  against 0.50. D5's answer to it is a fresh holdout under a complete surface.

### 1.4 The carried holdout roles

`sprint-21d4-holdout-reuse-audit.json` records final A, final B and canary as never opened:
0 protected bodies resolved, 0 accesses, 0 outcomes, 0 predictions, 0 receipts, all three roles
pairwise group-disjoint, 65 protected task identities intact. **D5 authors no final and no canary
bodies.** S21D5-004 re-runs that audit rather than inheriting its verdict, because an audit result
is about the moment it was taken.

---

## 2. Sprint goal and the fixed gate contract

### 2.1 Goal

Close Gate L2 by measuring, on freshly authored evidence and against unchanged thresholds, whether
the pairwise contrastive ranker is *selectively* useful — and if it is, carry exactly one learned
correction component through the full governed lifecycle to a bounded active state, so that
Sprint 22A unblocks on evidence rather than on optimism.

D5 has two questions, and the second does not depend on the first.

**Can the pairwise class certify a zero-error region wide enough to be useful?** Zero confident
errors over at least 100 independent fresh calibration decisions, at coverage at least 0.40,
projecting at least 20 changed final decisions.

**Does a complete searchable surface reach both retrieval floors?** Recall@5 ≥ 0.70 and
MRR@10 ≥ 0.50 on at least 50 new unseen-task queries, inside the fixed budgets.

### 2.2 The 29 conditions, and what D5 must do to each

The gate contract is frozen and unchanged. D4 left 13 met, 1 met as a rejection, 15 not opened.
**D5 inherits no pass.** Every condition is re-evidenced against D5's own authorities, exactly as
§2.2 of the D4 backlog required of D4.

| Conditions | D4 state | D5 obligation |
|---|---|---|
| 1–9, 12, 17 | met on D4 evidence | re-evidence against D5 authorities and corpora |
| 10, 11, 13–16, 18, 19, 21 | not opened | measure on final A/B — the wave that never ran |
| 20 | not opened | certify zero errors on ≥100 independent **fresh** calibration decisions, then measure ≥100 nominal promotion metamorphic/OOD decisions with exactly zero confident errors |
| 22, 23 | not opened | measure against the **real** artifact, not a contract fixture — the distinction D4 refused to blur |
| 24 | met as a rejection | measure once on the fresh holdout under the complete surface |
| 25–27 | not opened | canary manifest, approval, kill switch on the real activation |
| 28 | met | re-run the complete release matrix on D5 authorities |
| 29 | met | protected release, exact-head CI, tag, remote verification |

Gate D1 conditions 6, 7 and 15 close on D5's own evidence: 6 on the 240 unique eligible
verifier-backed final outcomes, 7 on condition 13's changed-decision evidence read against the D1
contract, 15 on S21D5-046.

### 2.3 Selection rule — unchanged from D4 §2.3, one substitution

Every threshold is D4's, verbatim. The only change is which quantity plays the role of confidence.

Selection requires all of:

- at least **100 independent** clean ranking decisions in the fresh calibration set;
- exactly **zero confident errors** among admitted independent calibration decisions;
- clean coverage at least **0.40**, and high enough that the selected operating point projects at
  least **20 changed decisions** over the 60 final groups;
- clean first-choice rate over admitted decisions strictly above the strongest deterministic
  baseline measured on the same decisions;
- at least one changed clean decision;
- **100% first-action preservation** on the invariance-regression sample;
- every grid point reported, including filtered and fully abstaining points;
- maximum inference within the **250 ms** budget.

The substitution: D4's admission signal was the k-NN's absolute neighbourhood acceptance mass.
D5's is the **projection margin between the top two candidates**. `derive_zero_error_point` treats
a confidence as an opaque ordered score and needs no change to accept it — which is why the entire
certification spine, the independence census, the Clopper-Pearson bound and the single-derivation
rule are inherited without a line of new code.

---

## 3. Scope and stop rules

### 3.1 In scope

- revision-5 pre-registration naming the class, λ, the margin, the fitting composition and the
  corpus submanifests, frozen before any D5 measurement;
- **100 newly authored calibration groups / 400 outcomes**, group-, clone- and source-disjoint
  from every spent and carried role;
- **60 newly authored retrieval groups** yielding at least 50 qualifying queries;
- a fitting pool of the **180 spent groups / 720 outcomes**, re-executed as a new campaign under
  new run identities;
- a volume probe at **320 and 720 rows**, which repairs D4's own stated limitation about its
  narrow 200→320 span at no authoring cost;
- `CorrectionArtifactPayloadV3` carrying a fitted direction instead of an exemplar set;
- the first real exercise of the D3-built artifact, runtime, verification, promotion, activation,
  canary and rollback surfaces;
- reuse of the carried final A, final B and canary roles after a repeated untouched audit;
- a complete typed negative path at every conditional boundary.

### 3.2 Explicitly out of scope

- any change to `correction-ranking-v2`, the alpha-normaliser, the embedding model, the
  390-channel representation or the feature contract hash `492c90a5df420de9…`;
- changing any Gate L2 or D1 threshold, the bootstrap seed 21041, the resource-policy bounds or
  reviewer controls;
- re-choosing λ, the confidence definition, the pairing rule or the solver;
- a third hypothesis class, a GNN, an FGW implementation, a GPU path, fine-tuning, or a live
  provider;
- re-deciding either D4 stop, or reusing any spent D4 calibration or retrieval evidence for a
  decision;
- authoring new final, batch-B or canary bodies unless the reuse audit fails a whole role;
- a new dependency, a new store, a new index, or a migration;
- `REAL_GOVERNED_RUN` fitting, online learning, autonomous weight updates, or verifier bypass;
- Sprint 22A domain expansion, or any claim that Gate L2 is passed before S21D5-095.

### 3.3 Revision-5 decision tree

Published before any D5 calibration number is read. Four endings, each decided by a measurement
rather than by a reader.

1. Fit the direction at **320** and at **720** exemplar rows and measure the risk–coverage curve
   on the fresh calibration set. Record coverage-at-zero-error at both volumes.
2. **Step 3 — select.** Some volume reaches zero confident errors on at least 100 independent
   decisions at coverage at least 0.40, projecting at least 20 changed final decisions, above the
   baseline. Proceed to W4.
3. **Step 4 — `volume_bound`.** Zero-error coverage is above zero and below 0.40 at 720 rows *and*
   materially higher at 720 than at 320. The residual is evidence volume; the yield curve across a
   2.25× span is the deliverable, and the successor is a corpus sprint with a target volume derived
   from it.
4. **Step 5 — `selective_margin_bound`.** Coverage is above zero, below 0.40, and flat across the
   two volumes, while first-choice rate stays above the baseline. The direction ranks and the
   margin cannot certify enough of what it ranks. The successor pre-registers a different
   *confidence construction* over the same ranker — split-conformal over the margin is the obvious
   candidate — not a different ranker and not a larger corpus.
5. **Step 6 — `hypothesis_class_bound`.** Coverage is at or near zero at both volumes. This
   contradicts the spent-evidence diagnostic, and the record must say so in those words: the
   estimate did not transfer to a fresh corpus, and the next question is why the authored
   distributions differ, not which class comes third.

Outcomes 3, 4, 5 and 6 are four different successor sprints and D5 must not guess between them in
advance.

### 3.4 Holdout and retuning stop line

- Revision 5 is hash-bound before the fresh calibration corpus is resolved.
- The selected setting, operating point, fitted direction bytes, dataset hash, split hash, feature
  hash, code revision and final prediction-seal procedure are fixed before final access.
- The retrieval surface contract, the comparator budget, the arm set and the holdout submanifest
  are frozen before the holdout is resolved. The holdout is read **once**.
- Neither branch may tune itself from the other branch's holdout.

---

## 4. Minimal D5 architecture

Four things are new. Everything else in this section is a pointer to something released.

### 4.1 The class — already merged

`pairwise-contrastive-linear-v1`, `src/cognitive_os/learning/pairwise_contrastive.py`. Fitting
needs numpy from the `semantic-graph` extra; inference is one dot product per candidate in pure
Python. Ties break on the baseline order; below the margin floor the ranker abstains and the
caller runs the deterministic order. The model seals to a `content_hash` and consumers compare
hashes rather than refitting, because bit-identity across BLAS builds is not assumed — the same
discipline W2-D9 forced on the MiniLM vectors.

### 4.2 The artifact — the one new module

`CorrectionArtifactPayloadV2` is k-NN-shaped by construction: `exemplars` with `min_length=1`,
`k`, `embedding_weight`, and three proportion floors. A direction has none of those. Making them
optional would let a v2 artifact with no exemplars load, which is exactly the
*check-that-passes-without-touching-its-question* defect the D4 report catalogued twelve times.

So: **`CorrectionArtifactPayloadV3`**, schema name `correction-ranking-artifact-v3`, dispatched on
`schema_name` beside v1 and v2, which stay byte-identical and exactly as strict.

- Identical to v2: every lineage, encoder, channel, dataset, split, manifest, embedding-model and
  numeric-bound field, plus the operating point, its derivation rule and the certificate hash that
  S21D4-050 specified.
- Replacing the exemplar set: `weights` (390 floats, in `FITTED_FEATURE_V2_ALLOWLIST` order),
  `regularization`, `fitted_group_count`, `fitted_pair_count`, `margin_floor`, and
  `hypothesis_class`.
- Refused at validation: a weight vector that is not 390 long or not finite; a channel list that
  is not the v2 allowlist in fitted order; a non-positive ridge; a negative margin floor; a
  `hypothesis_class` the loader does not implement.

One side effect worth measuring rather than promising: a direction is 390 floats, where an
exemplar-set artifact carries one 390-channel vector per fitting row — 720 of them at D5's pool
size, against a `MAXIMUM_EXEMPLARS` cap of 5,000. So the stored artifact is expected to be orders
of magnitude smaller, and inference becomes one dot product per candidate instead of a scan over
the whole exemplar set. S21D5-052 records the measured size and per-candidate time; neither is
asserted in advance, and neither is a Gate L2 condition.

### 4.3 The corpora — the wave that costs the sprint

| Role | D5 target | Provenance | Authoring cost |
|---|---:|---|---|
| fitting | 180 groups / 720 outcomes | 80 D4 fitting + 100 D4 calibration, re-executed as a new campaign | **none** |
| calibration | 100 groups / 400 outcomes | authored for D5 | the sprint's main deliverable |
| invariance regression | 20-group sample, 2 cases, 40 decisions | generated from the D5 fitting pool | 160 executed candidates |
| final A | 30 groups / 120 outcomes | carried, sealed, unopened | **none** |
| final B | 30 groups / 120 outcomes | carried, sealed, unopened | **none** |
| promotion metamorphic/OOD | 60 groups × 2 cases = 120 nominal, 60 independent | evaluation only | **none** |
| canary | 5 groups / 20 slots | carried, sealed, unopened | **none** |
| retrieval | 60 new disjoint groups until ≥50 queries qualify | authored for D5 | as D4 |

Two authored corpora, six inherited rows. The 60 retrieval groups are authored against a floor of
50 deliberately: the D4 corpus contract records that near-clone collisions force whole-group
withdrawal, and authoring exactly the floor turns one withdrawal into a sprint-arithmetic failure.

The authoring contract is D4's, which is recorded and proven: baseline passes visible / fails
hidden; variants one and two pass both; variant three repairs edge case 1 only; variant four
repairs edge case 2 only. Its three known failure modes are re-stated in S21D5-020 because all
three are invisible without execution — two hidden tests probing one defect wearing two
descriptions; a baseline broken so badly it fails its own visible suite; and a near-clone
collision at the level of the task rather than the code.

### 4.4 The complete searchable surface — already merged

`structure_fallback` closes the gap D4 measured and named: 26 of 120 D4 graph sides carried no
terms and are now non-empty, and the ten previously term-less repaired-side documents are pairwise
distinct. D5 turns the flag **on** for its own corpus, measures the reached fraction on that
corpus rather than on D4's, and reports it beside the arm results. Whether a complete surface
closes 0.0089 is the measurement; it is not the assumption.

### 4.5 Lifecycle — inherited whole

Sections 4.6 and 4.7 of the D4 backlog — the bounded-GED comparator budget and the lifecycle
sequence — apply unchanged and are not restated. The comparator runs under the fixed iteration
budget of one that S21D4-041 decided; anything measured with it before D4 stays unreplayable and
no back-fill is attempted.

---

## 5. Work items

Numbering mirrors D4's epics so a reader who knows D4 can navigate D5 by difference. Items marked
**[D4]** are that D4 item run unchanged against D5 authorities; their acceptance criteria are the
D4 backlog's and are not restated.

### EPIC S21D5-E00 — Baseline, reuse, and isolation

- **S21D5-000 — Revalidate the exact D5 starting point.** §1.1's six facts read from the remote;
  local and remote handles agree; `sprint-21-learning-baseline` absent. *Deps:* none.
- **S21D5-001 — Provision isolated D5 authorities.** A `cognitive_os_s21d5_test` database and a
  `s21d5` artifact root at migration `0015`; `COGOS_TRUNCATABLE_DATABASE` names the D5 database
  and nothing else. *Deps:* 000.
- **S21D5-002 — Freeze predecessor evidence and seal the inventory.** Six predecessor stores
  fingerprinted before and after; unchanged at both ends. *Deps:* 001.
- **S21D5-003 — Re-audit the spent-evidence role transition.** Records, per D4 role, its D5 role
  and the rule that permits it; refuses if any spent calibration group appears in the D5
  calibration corpus. *Deps:* 002.
- **S21D5-004 — Re-audit final and canary reuse eligibility.** The S21D4-004 audit re-run: 65
  protected identities, three roles pairwise disjoint, 0 bodies resolved, 0 accesses, 0 outcomes.
  Whole-role replacement if any role fails. *Deps:* 002.
- **S21D5-005 — Open the draft implementation PR.** *Deps:* 000.

### EPIC S21D5-E01 — Revision-5 experimental contract

- **S21D5-010 — Freeze the hypothesis class.** `pairwise-contrastive-linear-v1` by name, its
  `FIT_RULE`, λ = 1, the margin as confidence, and the diagnostic hash that justifies each. The
  record states that λ was chosen on fitting-pool-internal evidence and may not be re-chosen.
  *Deps:* 005.
- **S21D5-011 — Freeze the fitting composition and the volume points.** The 180-group pool
  enumerated by group name; volume points 320 and 720; whole groups only. *Deps:* 010.
- **S21D5-012 — Freeze the corpus submanifests.** Exact calibration, retrieval, invariance,
  final A, final B, canary and promotion membership. *Deps:* 004, 010.
- **S21D5-013 — Freeze the artifact v3 contract.** Fields, refusals, and the schema-name dispatch.
  *Deps:* 010.
- **S21D5-014 — Freeze the retrieval contract.** Surface with `structure_fallback` on, comparator
  budget, arm set, query qualification rule, floors. *Deps:* 010.
- **S21D5-015 — Complete power and yield analysis.** What 100 independent decisions can and cannot
  certify; the Clopper-Pearson bound at n = 100 stated beside the floor. *Deps:* 011.
- **S21D5-016 — Publish pre-registration revision 5.** `scripts/pre_registration_d5.py --check
  --check-chronology`; `measured_values: 0`; the §3.3 tree published in full. *Deps:* 010–015.

### EPIC S21D5-E02 — Fresh corpora

- **S21D5-020 — Author 100 calibration groups.** `coding/reality_task_specs_d5.py`. The D4
  four-candidate shape; families balanced; the three known failure modes checked by execution, not
  by reading. Near-clone detectors (`normalized_structure_hash`, `token_stream_hash`) run
  **every batch** and scoped to cross-group pairs against every released corpus. *Deps:* 016.
- **S21D5-021 — Author 60 retrieval groups and their queries.** `reality_retrieval_specs_d5.py`;
  at least 50 must qualify. *Deps:* 016.
- **S21D5-022 — Prove rights, lineage, group and near-clone separation.** Seven roles, all
  pairwise disjoint; `cross_group_collisions_touching_21d5: []`. *Deps:* 020, 021.
- **S21D5-023 — Seal every D5 campaign and holdout manifest.** *Deps:* 022.
- **S21D5-024 — Prove one complete vertical slice.** §6.1's nine steps on a dedicated fixture group
  outside every role, under the v3 artifact. *Deps:* 023, 050.
- **S21D5-025 — Seal every fitting and calibration feature before execution.** Chronology refusal
  proved by a seeded post-outcome seal. *Deps:* 023.
- **S21D5-026 — Execute and ingest both campaigns.** 720 fitting and 400 calibration outcomes under
  new run identities; zero `REAL_GOVERNED_RUN` observations in either. *Deps:* 025.

### EPIC S21D5-E03 — The correction branch

- **S21D5-030 — Materialise and validate explicit snapshots.** 390 channels on the v2 allowlist;
  every leakage and chronology scan passed. *Deps:* 026.
- **S21D5-031 — Resolve the invariance-regression sample.** 20 groups, 2 cases; any label change,
  feature drift or first-action change is a stop with `invariance_regression`. *Deps:* 030.
- **S21D5-032 — Fit the direction at both volumes.** Whole groups; both models sealed by
  `content_hash` before any calibration decision is scored. *Deps:* 030.
- **S21D5-033 — Measure the strongest deterministic baseline on the same decisions.** Every rung
  recorded, including ineligible ones. *Deps:* 030.
- **S21D5-034 — Derive the zero-error operating point.** `derive_zero_error_point` on the fresh
  calibration split only, once, with the single-derivation rule enforced across restart. *Deps:*
  032.
- **S21D5-035 — Measure the risk–coverage curve and select at most one candidate.**
  `scripts/learner_selection_d5.py`. Every cell reported; §2.3 decides eligibility; §3.3 decides
  the ending. The script must have no path that asserts a pass. *Deps:* 031, 033, 034.
- **S21D5-036 — Record the typed continuation decision.** On a stop, the stop kind, its reading,
  and a complete not-opened map over every dependent item. *Deps:* 035.
- **S21D5-037 — Extend the promotion payload for the v3 class.** The condition-20 row carries
  nominal and independent counts, the certificate hash, and the hypothesis class; v1, v2 and D3/D4
  payloads stay readable through the schema-name dispatch. *Deps:* 016.

### EPIC S21D5-E04 — The retrieval branch

Independent of E03 after S21D5-016. A correction stop does not cancel it; a retrieval failure does
not authorise correction activation.

- **S21D5-040 — Project the D5 retrieval pairs under the complete surface.** `structure_fallback`
  on; structural hashes unchanged; the leak guard fails closed. *Deps:* 021, 023.
- **S21D5-041 — Measure and report surface completion on the D5 corpus.** Reached fraction, empty
  fraction, distinctness — on D5's corpus, not D4's. *Deps:* 040.
- **S21D5-042 — Replay the development benchmarks under the complete surface.** Development pool
  only; the holdout stays sealed. *Deps:* 040.
- **S21D5-043 — Resolve and seal the distinct retrieval holdout.** ≥50 qualifying queries. *Deps:*
  022, 042.
- **S21D5-044 — Verify the new retrieval graph pairs.** Edit-path round trip; every source hash
  resolved. *Deps:* 043.
- **S21D5-045 — Evaluate all frozen arms exactly once.** Inside the fixed budgets; the chance
  baseline reported beside every arm. *Deps:* 043, 044.
- **S21D5-046 — Decide D1 condition 15 and Gate L2 condition 24.** First-failure precedence; a near
  miss is not a pass; nothing is reopened to close it. *Deps:* 045.
- **S21D5-047 — Preserve the advisory Experience Graph boundary.** [D4] Runs on every outcome. Six
  mandatory bundle sections byte-identical with and without retrieval; no advisory candidate
  pinned, required, evidence or executable; an empty set degrades; all four store-breakage paths
  end at `UNVERIFIED`. *Deps:* 045.

### EPIC S21D5-E05 — Artifact, runtime, and lifecycle readiness

The wave D4 planned and never ran with an artifact. Items 050–059 are the D4 items with `V2`
replaced by `V3` and the exemplar set replaced by the direction; their acceptance criteria are
otherwise D4's and are not restated.

- **S21D5-050 — Implement `CorrectionArtifactPayloadV3` and its dispatch.** §4.2. The one new
  module in this backlog. *Deps:* 013.
- **S21D5-051 — Bind the derived threshold into the artifact.** [D4 S21D4-050] *Deps:* 035 selects.
- **S21D5-052 — Fit and store the selected artifact.** [D4 S21D4-051] Plus: the stored size and the
  measured per-candidate inference time are recorded, not asserted. *Deps:* 051.
- **S21D5-053 — Prove the loader and resolver against the real artifact.** [D4 S21D4-052] The
  21-configuration matrix reaches all 18 reason codes; `unreached_reason_codes: []`. *Deps:* 052.
- **S21D5-054 — Route sequencing through the receipt-aware remainder.** [D4 S21D4-053] *Deps:* 052.
- **S21D5-055 — Prove the selected-artifact vertical slice.** [D4 S21D4-054] *Deps:* 053, 054.
- **S21D5-056 — Re-prove mandatory-path and configuration invariance.** [D4 S21D4-055] Hashed by
  execution; no constant asserted. *Deps:* 053.
- **S21D5-057 — Register the exact artifact and enter SHADOW.** [D4 S21D4-056] *Deps:* 055, 056.
- **S21D5-058 — Exercise evidence-bound verification and revalidate bytes.** [D4 S21D4-057 and
  S21D4-058, merged: both call the one shared `_revalidate_bytes`, so proving them apart proves
  the same path twice.] *Deps:* 057.
- **S21D5-059 — Authorise final access at one pre-final checkpoint.** [D4 S21D4-059] Preconditions
  in backlog order, stopping at the first failure; `authorised: false` carries one stop hash and a
  complete not-opened map. *Deps:* 046, 058.

### EPIC S21D5-E06 — Final evaluation and promotion evidence

D4 items 060–069, run unchanged on the carried final roles. Acceptance criteria are the D4
backlog's.

- **S21D5-060** — seal final features and predictions before execution. *Deps:* 059 authorises.
- **S21D5-061** — execute final batch A: 120 `REAL_GOVERNED_RUN` outcomes over the exact 30 sealed
  groups, no substitution. *Deps:* 060.
- **S21D5-062** — execute final batch B as independent confirmation, not a repair set for A.
  *Deps:* 061.
- **S21D5-063** — paired material benefit: ≥20 changed group decisions; ≥5 absolute points or 20%
  relative error reduction; bootstrap seed 21041, 2,000 resamples, 95% lower bound above zero;
  direction positive in both batches. *Deps:* 062.
- **S21D5-064** — safety and cross-domain anti-forgetting replay. *Deps:* 062.
- **S21D5-065** — promotion-scale metamorphic/OOD evaluation: ≥100 nominal over 60 final groups,
  independent count beside it, **exactly zero confident errors**. *Deps:* 062.
- **S21D5-066** — true shadow mode: zero executed decisions change. *Deps:* 062.
- **S21D5-067** — the strengthened promotion assessment: twenty gates, each with an outcome, its
  evidence hash and a detail string. *Deps:* 063–066.
- **S21D5-068** — assess Gate D1 conditions 6, 7 and 15. *Deps:* 067, 046.
- **S21D5-069** — advance `SHADOW → VERIFIED` through `verify_component()` only. *Deps:* 067.

### EPIC S21D5-E07 — Approval, canary, activation, and rollback

D4 items 070–077, run unchanged. S21D5-075 is **unconditional** and runs against the isolated
lifecycle fixture whether or not D5 activates, exactly as S21D4-075 did.

- **S21D5-070** — prepare the exact activation bundle; sealing happens here, not earlier. *Deps:*
  069.
- **S21D5-071** — record explicit human approval: exactly the existing fields, no invented field,
  no self-approval, no model or provider approver. The repository's single-collaborator reality is
  documented rather than worked around. *Deps:* 070.
- **S21D5-072** — activate canary-only routing atomically: one routed group, 20 tasks, the exact
  canary configuration hash, bytes revalidated. *Deps:* 071.
- **S21D5-073** — execute the governed canary with stop-first semantics. *Deps:* 072.
- **S21D5-074** — kill switch, cause-bound disable, fallback surviving restart. *Deps:* 073.
- **S21D5-075** — receipt-selected rollback restoration and refusal. **Unconditional.** *Deps:* 001.
- **S21D5-076** — promote to bounded steady state: three groups, 200 tasks, the exact steady-state
  hash, on canary evidence. *Deps:* 074, 075.
- **S21D5-077** — prove final active state and replacement readiness; zero online updates. *Deps:*
  076.

### EPIC S21D5-E08 — Operations, recovery, CI, and validation

D4 items 080–086. All of this is released and was proven in D4 W7; D5 re-runs it against D5
authorities. The truncation fence and its eleven paths are already in place and
`COGOS_TRUNCATABLE_DATABASE` already governs them.

- **S21D5-080** — extend the evidence CLI narrowly: `scripts/learned.py d5-integrity`, read-only,
  offline by default, one line of canonical sorted JSON, refusing any database name lacking
  `s21d5`. *Deps:* 026.
- **S21D5-081** — unified integrity and health: the twelve classes clean with both authorities.
  *Deps:* 080.
- **S21D5-082** — verify provisioning at migration `0015` with no `0016`. *Deps:* 001.
- **S21D5-083** — replay, restart, backup and isolated restore reproducing counts, hashed rows,
  both resume inputs and every blob rehash. **The backup runs before the damage, not after** —
  W0-F1 and W7-F1 are what that sentence cost. *Deps:* 081.
- **S21D5-084** — corruption, substitution and isolation failures: every damage case fails closed.
  *Deps:* 083.
- **S21D5-085** — focused credential-free CI. Any new environment check must be collectable
  **without** a SQLAlchemy import — W7-F2 is what that sentence cost. *Deps:* 080.
- **S21D5-086** — the complete release matrix on scratch authorities, before the release PR.
  *Deps:* 084, 085.

### EPIC S21D5-E09 — Documentation, gate, protected release, and handoff

- **S21D5-090 — Update architecture and operator documentation.** Extends the released documents;
  every command shown was run. *Deps:* 086.
- **S21D5-091 — Prepare `gate-l2-d5-assessment.md`.** A versioned successor touching none of the
  D2, D3 or D4 assessments. Generated by `scripts/gate_assessment_d5.py` from the frozen contract
  and the produced evidence. **The script must have no path that asserts a pass — it can only read
  one.** *Deps:* 090.
- **S21D5-092 — Complete the Sprint 21D5 report.** Outcome, both branch results, every finding with
  an ID, and the limitations — including that a passing D5 measures one surface, on authored tasks,
  under a frozen encoder. *Deps:* 091.
- **S21D5-093 — Prepare the outcome-specific handoff.** On a pass: exactly what Sprint 22A inherits
  and what it must not assume. On a stop: the smallest next experiment named by the §3.3 stop kind.
  *Deps:* 092.
- **S21D5-094 — Complete the protected implementation release.** Merge under unchanged protection;
  exact-head post-merge `main` CI green; create and push **one** annotated outcome tag —
  `sprint-21-learning-baseline` on a pass, `sprint-21d5-evidence-baseline` on a stop. *Deps:* 093.
- **S21D5-095 — Complete gate-close release evidence and remote verification.** A gate-close
  documentation PR from current `main` adds the remote-derived release JSON and final assessment
  handles; it merges under unchanged protection; its post-merge `main` CI succeeds; `origin/main`,
  the immutable tag object and peeled commit, both CI runs and the protection state are re-read.
  **On a pass, and only after this item, the handoff unblocks Sprint 22A.** The tag is never moved
  or recreated. *Deps:* 094.

---

## 6. Execution waves

| Wave | Items | Exit |
|---|---|---|
| W0 — authority and contract | 000–016 | D4 release verified, isolated D5 roots, role transition and reuse audited, revision 5 committed before any measurement |
| W1 — corpora | 020–026 | 100 calibration and 60 retrieval groups authored, separated, sealed; both campaigns executed under new run identities |
| W2 — correction branch | 030–037 | risk–coverage curve at 320 and 720 rows, one candidate or a typed stop under §3.3 |
| W3 — retrieval branch | 040–047 | complete surface measured on D5's corpus, ≥50 unseen queries, condition-24 decision |
| W4 — artifact and runtime | 050–059 | the v3 artifact fitted, stored, loaded, resolved, sequenced, in SHADOW; one pre-final access decision |
| W5 — final evidence | 060–069 | final A/B, benefit, retention, promotion OOD, shadow, assessment, `VERIFIED` or a typed stop |
| W6 — governed activation | 070–077 | approval, canary, kill switch, restart, rollback, bounded steady state; otherwise not opened |
| W7 — operations | 080–086 | CLI/health, isolated recovery, corruption proofs, complete local matrix |
| W8 — release | 090–095 | report, assessment, handoff, protected release, tag, gate-close record |

The two branches stay independent after W0:

```text
revision 5
  +-> 180-group fitting pool -> fresh calibration -> margin operating point -> candidate
  |     -> v3 artifact -> SHADOW -> final A/B -> VERIFIED -> canary -> bounded active
  |
  +-> complete searchable surface -> fresh unseen holdout -> D1 condition 15 / L2 condition 24

both branch verdicts + operations -> Gate L2 outcome -> protected release -> Sprint 22A
```

### 6.1 First vertical slice

Before bulk campaigns, S21D5-024 proves on a dedicated fixture group outside every role: one
rights-clean four-candidate package; canonical v2 bytes and named channels unchanged; pre-outcome
feature seal and receipt-bound execution; independent hidden-verifier labels; explicit dataset
identity and full matrix scanning; one ranking at a derived margin threshold, its abstention and
the baseline fallback; canonical **v3** artifact reload, receipt-aware stop-on-first-accept and
exact missing-outcome resume; wrong, corrupt and oversized artifact fallback, restart, replay,
backup and restore; and final and retrieval capabilities refusing access.

### 6.2 The two schedule risks, named

**W1 is the authoring risk**, exactly as D4's W2 was. If W1 cannot reach 100 calibration groups,
the honest response is to author fewer, record the achieved independent-decision count, and let
§2.3's floor decide the outcome — never to reduce the floor, and never to reinstate replicated
decisions to reach it.

**W4 through W6 are the unexercised-code risk, and this is new.** D3 built the artifact, loader,
resolver, sequencer, promotion, shadow, canary, activation and rollback surfaces. D4 planned to
drive them with a real artifact and stopped before it could. **Nobody has ever run this path with
a fitted model.** Budget for defects there the way D4 budgeted for them in corpus authoring: the
D4 report's twelve smaller defects all shared one shape — a check that passes without touching its
question — and an unexercised lifecycle is where that shape hides best. Every W4–W6 item is
proved by running the thing and reading the output against the question it claims to answer.

### 6.3 Pull-request and release strategy

Unchanged from D4 §6.2. One coherent implementation PR by default; a pre-registration-only PR is
allowed only if campaign execution must begin from protected authority, and it must merge before
any number it governs is measured. Two protected documentation states: the implementation release,
then the gate-close record. The gate-close commit is newer than the tag and must not move it.

---

## 7. Verification matrix

Every row is proved by running something and reading its output. No row is satisfied by an
assertion about a constant.

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| role transition | no spent calibration group in the D5 calibration corpus; every D5 rate over the independent denominator | a spent group decided something |
| pre-registration | revision 5 hash-bound with `measured_values: 0` before the corpus resolves | the contract followed the data |
| corpus separation | seven roles pairwise disjoint; `cross_group_collisions_touching_21d5: []` | the calibration set is not unseen |
| feature seal | every fitting and calibration feature sealed before its outcome; seeded post-outcome seal refused | chronology is decorative |
| independence | nominal, independent and replicated reported; every rate over the independent count | D3's erratum recurring |
| operating point | derived once, from calibration only; a second derivation reproduces the hash | the threshold was searched |
| selection | every cell reported including filtered and fully abstaining; §3.3 ending named | a weaker candidate was promoted to a candidate |
| invariance | 100% first-action preservation on the 20-group sample | the representation drifted |
| artifact | stored bytes rehash to the recorded address; v1, v2 and v3 dispatch correctly; unsafe formats unloadable | the artifact is not the model |
| resolver | all 18 reason codes reached against the real artifact; `unreached_reason_codes: []` | a fixture was proved instead of a candidate |
| final evidence | 240 outcomes over the exact sealed groups, no substitution, every attempt independently verified | the benefit is not measured |
| promotion OOD | ≥100 nominal, independent count beside it, exactly zero confident errors | condition 20 is unmet |
| activation | canary hash-bound, verifier mandatory, kill switch immediate, fallback surviving restart | the lifecycle is untested |
| retrieval | ≥50 unseen queries, arms evaluated once, chance baseline reported | the floor was approached, not met |
| operations | twelve integrity classes clean with both authorities; every damage case fails closed; backup **before** damage | recovery is theoretical |
| release | protected merge, exact-head CI, one annotated tag, remote re-read | the head is not reproducible |

---

## 8. Definition of done

### 8.1 On a pass

- all 29 Gate L2 conditions `met`, with no relaxed threshold and no condition met against a
  fixture;
- Gate D1 conditions 6, 7 and 15 closed on D5's own evidence;
- exactly one learned correction component bounded and **active**, with zero online updates;
- `sprint-21-learning-baseline` created once, protected, and verified from the remote;
- the handoff states what Sprint 22A inherits and what it must not assume;
- **Sprint 22A unblocks**, and only after S21D5-095.

### 8.2 On a stop

- the first pre-registered failure and every dependent not-opened record are immutable and bound
  to one stop hash;
- the independent retrieval result is retained when it is valid, whichever way the correction
  branch went;
- `sprint-21d5-evidence-baseline` is protected and verified from the remote;
- the §3.3 stop kind names the successor experiment — a corpus sprint with a target volume, a
  conformal-confidence sprint over the same ranker, or a question about why the authored
  distributions differ;
- Gate L2 does not pass and Sprint 22A stays blocked. A negative release is a complete release,
  not an abandoned one.

### 8.3 What Sprint 22A inherits on a pass

Named here so the handoff cannot invent it later: the active bounded correction component and its
governed replacement path; the revision-5 counting rule and operating-point spine, neither of
which is specific to correction ranking; the 180-group fitting pool and the D5 corpora; the
complete searchable surface; and the operations, integrity and release substrate. Sprint 22A's own
objective — data-driven domain registry, its two pilot domains and its `sprint-22a-domain-baseline`
tag — is out of scope for every item in this backlog.
