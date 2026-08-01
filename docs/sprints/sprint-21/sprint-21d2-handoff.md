# Sprint 21D2 handoff — the bounded learned comparison

D1 pre-registered the decision problem, established the strongest deterministic baselines, and
tested whether bounded Experience Memory Graph retrieval contributes useful structure. It fitted
nothing and activated nothing.

**Gate L2 does not pass at handoff.** Whether a learned component actually helps is still
unanswered, and nothing in C1, C2, C3 or D1 may be mistaken for an answer.

D2 performs the learned comparison. It preserves every D1 measurement, but it must create a new
primary-surface pre-registration revision because D1 selected no primary. It must not look at the
wrong split or reinterpret D1's negative gate result as a pass.

Implementation authority: [Sprint 21D1 Technical Backlog](sprint-21d1-technical-backlog.md).
Gate status: [Gate D1 assessment](gate-d1-assessment.md). Results:
[Sprint 21D1 report](sprint-21d1-report.md). D2 implementation authority:
[Sprint 21D2 Technical Backlog](sprint-21d2-technical-backlog.md).

## 1. Starting point

| | |
| --- | --- |
| Parent tag | `sprint-21d1-emg-baseline`, annotated |
| Parent release commit | `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`, peeled D1 implementation baseline |
| Parent pull request | `#217`, squash-merged under unchanged branch protection; main CI run `30657167717`, 30 of 30 success |
| Current planning head | `1cadbabb5cdabb32bbd502f281d734fb25a229ff`, after gate-close PR `#218` |
| Planning-head CI | `30658256397`, 30 of 30 success on the exact planning head |
| D2 branch point | revalidated current `origin/main`, not the older peeled tag commit |
| Alembic head | `0015`; `0016` unallocated |
| Gate D1 | **does not pass** — conditions 6, 7 and 15 open |
| Gate L2 | **does not pass** |

## 2. The first thing D2 must not do

Do not fit a learner on `governed.outcome_triage`. D1 audited it and rejected it, and the
rejection is a property of the evidence rather than of the method:

- `candidate_strategy` predicts the verifier label with **no error** on all 150 enumerated coding
  outcomes. It is a perfect oracle and must never be a feature.
- With both construction oracles removed the coding half is exactly 60/60 with no rung above
  0.5000, and group frequency scores **0.0000** — anti-informative, not merely weak.
- The benchmark half is single-class: 64 of 64 passed.

Sampling more of the same evidence does not repair a surface whose label is a function of a
forbidden field. D1's shortfall campaign therefore generated zero outcomes on purpose.

`experience.correction_ranking` is the only balanced candidate — 60/60 — and is **deferred**, not
rejected. It has 120 eligible development examples and 30 changeable task rankings. All are
`REAL_GOVERNED_RUN` evidence, so none may enter training or calibration. D2 must revisit the
surface with a new rights-cleared `SELF_PLAY` fitting corpus and separately sealed,
group-disjoint `REAL_GOVERNED_RUN` final batches.

## 3. Exact APIs

| purpose | handle |
| --- | --- |
| graph contracts | `cognitive_os.domain.experience_graph` — 10 contracts, exported under `v1/experience-graph/` |
| projection and edit paths | `cognitive_os.experience.graph_projection` — `project`, `project_correction`, `project_persisted_side`, `derive_edit_path`, `apply_edit_path`, `round_trips` |
| bounded retrieval | `cognitive_os.experience.graph_retrieval` — `candidates_from`, `eligible_pool`, `no_memory`, `lexical`, `exact_signature`, `minilm_vector`, `bounded_ged`, `recall_at`, `reciprocal_rank`, `ndcg_at` |
| persisted evidence | `cognitive_os.experience.graph_store` — `load_evidence`, `blob_path`, `GraphEvidence` |
| advisory context | `cognitive_os.experience.graph_context.ExperienceGraphContextRetriever`, retriever id `context.experience_graph` |
| surface contracts | `cognitive_os.domain.learned` — `SurfaceSampleAudit`, `SurfaceSelectionDecision`, `SurfaceActionCostMatrix`, `SurfaceDisposition`, `FeatureTiming`, `LabelSource` |
| leakage validation | `cognitive_os.learning.leakage` — `FIELD_TIMING`, `validate_query_projection`, `duplicate_identities` |
| baselines | `cognitive_os.learning.triage_evidence` — the four-rung ladder, `oracle_free_population`, `residual_headroom`, `paired_bootstrap` |
| bounded k-NN pattern | `cognitive_os.infrastructure.learned.knn.ExperienceKnn` — reuse the pattern without changing the existing `skill.selection` identity |
| dataset authority | `cognitive_os.application.services.learned_datasets.LearnedDatasetBuilder` — extend with explicit D2 member/group manifests |
| current campaign execution | `cognitive_os.application.services.reality_campaign_runner.RealityCampaignRunner` — currently executes every explicit candidate; D2 adds bounded two-mode sequencing here |
| current C3 outcome intake | `cognitive_os.application.services.reality_outcome_harvester.RealityOutcomeHarvester` — fixed `coding.repair`/`REAL_GOVERNED_RUN`; retain defaults and add a separate role-bound D2 projector |
| durable lifecycle | `cognitive_os.application.services.learned_evidence.LearnedEvidenceService` — lineage, approval, activation, disable and rollback |
| learned configuration | `cognitive_os.config.learned_config` — default-off activation, explicit actors, no real-run training |
| integrity | `cognitive_os.coding.reality_integrity.experience_graph_checks` |
| operator commands | `scripts/experience.py graph-build|graph-verify|graph-query|graph-benchmark|graph-health` |

Two contract rules D2 inherits and must not weaken:

- `SurfaceSelectionDecision` accepts an absent primary surface only with a recorded reason. A
  selection cannot be silently empty.
- `SurfaceActionCostMatrix` refuses any cost assignment under which abstaining or requesting
  repair costs less than verifying a candidate the verifier would reject. That is the rule that
  stops a predictor becoming an acceptance authority.

## 4. Manifests

| manifest | file |
| --- | --- |
| surface audits, four surfaces, hash-bound | `evidence/sprint-21d1-surface-audit.json` |
| pre-registration, revision 1, decision hash `4ceeb74e…` | `evidence/sprint-21d1-pre-registration.json` |
| canonical outcome view, 214 records | `evidence/sprint-21d1-outcome-view.json` |
| frozen primary baseline and ladder | `evidence/sprint-21d1-primary-baseline.json` |
| the 80-pair set, frozen | `evidence/sprint-21d1-pair-set.json` |
| EMG root, 80 children + similarity links | `evidence/sprint-21d1-emg-root.json` |
| 80 frozen queries with declared relevance | `evidence/sprint-21d1-graph-queries.json` |
| retrieval metrics, five arms | `evidence/sprint-21d1-retrieval-benchmark.json` |
| residual taxonomy with per-query records | `evidence/sprint-21d1-residuals.json` |
| verification matrix, 22 rows | `evidence/sprint-21d1-verification-matrix.json` |

All paths are relative to `docs/sprints/sprint-21/`.

**Splits.** Groups are the unit of separation and group identity is one-to-one with task identity
in this corpus. Every query excludes its own group, so the D1 benchmark is unseen-task by
construction. D2 must keep group-level separation; sampling at the example level would leak.

**Frozen holdouts.** There is no D2 holdout yet. Everything D1 published is over the frozen D1
benchmark, and D1 read no future holdout. D2 must construct its holdout from group-disjoint
evidence before fitting anything, and must not evaluate final D2 benefit on the 80 pairs used to
compare arms. The minimum final design is two independent batches of 25 task groups and four
candidates per group: 100 outcomes in A and 100 in B. A power analysis may increase, never lower,
those counts. Across training, calibration, final A, final B, and canary, D2 needs at least 115
distinct groups. D1 contains only 30, so at least 85 genuinely new groups are required even if
every old group is reused exclusively for self-play training.

## 5. The strongest retrieval arm

`minilm_shortlist_plus_bounded_ged`: 0.6750 top-5 recall, 0.4481 MRR@10, 0.3438 nDCG@10,
p50 24.7 ms, p95 1788.9 ms, 60 budget cutoffs.

The strongest arm needing **no** structure is `minilm_vector`: 0.5375, 0.4392, **0.3740**, p95
27.5 ms, zero cutoffs. It wins nDCG and costs two orders of magnitude less at the tail.

Neither clears the usefulness floor of 0.70 recall and 0.50 MRR. Condition 15 is open.

**Carry both forward.** The graph arm is the recall leader and the vector arm is the ordering and
latency leader, and D1 does not have the evidence to collapse that into one choice.

## 6. The first lever, with its ceiling attached

The binding constraint is shortlist width, not the structural comparator.

| shortlist width | ceiling for any reranker (top-5 recall) |
| --- | --- |
| 10 (current) | 0.7625 |
| 15 | 0.9000 |
| 20 | **0.9750** |
| 30 | 1.0000 |

19 of 26 residual queries never had a relevant pair on the shortlist, so no reranker can reach
them. Widening `vector_shortlist` changes one pre-registered bound, adds no dependency, and is
the only measured change that could carry an arm past the floor.

It also multiplies the graph arm's cost, which already spends 60 cutoffs and 1788.9 ms at p95 on
80 pairs. Re-measure against the declared budget, not in principle.

There is one implementation prerequisite. `bounded_ged()` currently obtains its shortlist from
the already truncated public `minilm_vector()` result. With ten returned results, setting the
shortlist to twenty still gives GED only ten candidates. D2 must first separate internal vector
scores from public result truncation and prove that twenty candidates are considered while no
more than ten are returned.

## 7. The FGW decision, and when it reopens

[ADR 0090](../../adr/0090-no-fused-gromov-wasserstein-and-the-shortlist-constraint.md): **no-go**,
and no D2 experiment is approved. The whole D1 branch added zero packages —
`git diff …-- uv.lock pyproject.toml` is empty.

The question reopens on **one** condition: a residual report taken *after* the shortlist lever,
which still shows `rerank_ordering` as the dominant residual class. Until then, an
optimal-transport dependency would be aimed at 7 of 26 residual queries while 19 sit behind a
shortlist it never touches.

If the post-width-20 final residual justifies a later experiment, that successor must gather
`S21D1-061`'s source, licence, maintenance and necessity evidence and use a new holdout. D2 may
record the hypothesis but may not install FGW or retune on its final queries.

The clean-room boundary stands: the EMG preprint is CC BY-NC-SA 4.0, incompatible with this
repository's Apache-2.0. Concepts may inform design; expression must not be copied.

## 8. The material-benefit rule for D2

A learned component earns Gate L2 passage and steady-state routing only when all of the
following hold:

1. it changes at least 20 task-level decisions over at least 200 held-out verifier-backed
   outcomes in two independently generated, group-disjoint batches constructed after D1;
2. it beats the **strongest deterministic baseline** by at least 5 percentage points absolute
   verified success or 20% relative error reduction; provider/LLM cost is zero/zero in this
   offline sprint and is not an alternative passing gate;
3. the learned-minus-baseline direction is positive in each independent batch;
4. the improvement survives the paired bootstrap already in `triage_evidence` — seed 21041, 2000
   resamples, stdlib, no new dependency;
5. it never lowers the cost of skipping verification: the `SurfaceActionCostMatrix` invariant is a
   contract, not a guideline;
6. its inputs pass the leakage validator with no oracle field, verified on the fitted feature set
   rather than on the intended one;
7. zero safety accepted-to-rejected transition occurs, no retained domain loses more than two
   absolute points, aggregate verified success loses no more than one point, OOD reporting is
   at most 1%, and the existing promotion contract sees exactly zero confident OOD errors;
8. its retrieval and inference stay inside a declared resource budget, measured with the per-pair
   timeout reserved rather than by elapsed time alone;
9. shadow changes no executed decision, canary stays bounded, every candidate still meets the
   independent verifier, and fallback, kill switch, restart and rollback are proven;
10. the negative result, if that is what the measurement gives, is published with the same weight
   as a positive one.

Initial bounded activation is earlier: it requires items 1–8, the shadow portion of item 9, an
eligible pre-activation promotion assessment, fresh model lineage, and exact human approval.
Canary, kill switch, restart, and rollback are post-activation operational confirmation and cannot
be circular inputs to that initial approval.

## 9. Executable D2 boundaries

The D2 backlog uses the current contracts rather than inventing persistence that does not exist:

- durable `CorpusRole` remains `TRAINING` or `EVALUATION`; immutable campaign manifests carry
  `fit`, `calibration`, `final_a`, `final_b`, and `canary` partitions; the canonical exact
  split-assignment digest participates in explicit-mode dataset identity;
- a focused role-bound projector maps only training/calibration to `SELF_PLAY` and only
  final/canary to `REAL_GOVERNED_RUN`, always on `experience.correction_ranking`; the existing
  C3 `RealityOutcomeHarvester` remains `coding.repair`/real-run compatible;
- explicit dataset selection pages beyond the current 500-row listing limit and rejects any
  unresolved, extra, wrong-role, wrong-hash, or cross-group member;
- every task uses four outcome-neutral, prebuilt and sealed recipes with opaque candidate IDs;
  label-named `correct_*`/`incomplete_*` recipes are not reused, and all references validate before
  append-only outcome recording;
- `RealityCampaignRunner` gains a bounded candidate sequencer and a versioned sequence receipt
  appended with compare-and-set to the existing Event Store campaign stream. The existing
  `RealityCampaignLedger.plan_resume()` consumes it;
  Training/calibration have no learned order and execute all four candidates in frozen deterministic
  order; final/shadow use a direct verified SHADOW artifact snapshot, record learned order, but still
  execute the baseline order. Only canary/active execution uses the ACTIVE resolver, tries learned
  order, and stops after independent verifier acceptance. Resume preserves actual attempts and
  intentionally unattempted IDs;
- final A/B and canary bodies use separate holdout roots/processes. Fitting receives no root or
  artifact capability; a final evaluation worker receives one only after the hash-bound access
  decision;
- this activation covers only the controlled four-candidate campaign path. `CodingAgentFacade`
  remains a single-proposal repair loop and is not claimed as learned-active in D2;
- the component is registered and enters SHADOW before final/shadow evidence. A focused
  `verify_component()` reaches VERIFIED only after reloading the eligible D2 assessment payload;
  generic state advancement refuses VERIFIED and ACTIVE. Exact human approval follows;
- approval and receipt use their real fields. Canary membership is a separately hash-recorded,
  fail-closed configuration subset of the already approved bounded surface;
- `activate()` re-verifies exact promotion artifact media/schema/hash/size inside the state-changing
  operation. A failed canary writes one `rollback_permitted=false` disable receipt and is never
  rolled back into service; rollback proof uses scratch lifecycle state unless the real canary
  succeeds. Valid runtime observations enter evaluation-only intake, while only invalid or
  unresolved inputs are quarantined. Under the current contract, accepted
  `REAL_GOVERNED_RUN` rows remain permanently training-ineligible.

A valid calibration or final negative result completes the protected D2 evidence release but does
not pass Gate L2. Conditional tasks receive immutable not-opened records, the tag is
`sprint-21d2-evidence-baseline`, Sprint 22A stays blocked, and a remediation handoff is produced.
Only the positive path may publish `sprint-21-learning-baseline` and an S22A handoff.

## 10. Risks

| risk | why it matters | what D1 leaves for it |
| --- | --- | --- |
| a second leaked oracle | D1 found one perfect predictor by looking; a fitted model will find one without announcing it | `FIELD_TIMING` and `validate_query_projection`, to be run on the fitted feature set |
| real-run contamination | the 120 deferred records look like convenient training data but are evaluation-only | the dataset contracts and configuration structurally prohibit `REAL_GOVERNED_RUN` training |
| example-level sampling | group identity is task identity here, so example-level splits leak completely | group-disjoint splits and the `excluded_groups` contract |
| tuning to the floor | conditions 6, 7 and 15 are open and each is closable by moving a threshold | the thresholds are pre-registered and hash-bound; moving one invalidates affected results |
| the legacy half | 60 of 80 pairs cannot be recompiled byte for byte | `legacy_recompilation_unavailable` on the pair, reported as a warning and never as damage |
| tie degeneracy | 61 of 80 graph rankings were decided by a tiebreak | recorded per query in the residual report, so a new comparator is compared query by query |
| store erasure | the truncating integration suite erased a campaign once | `COGOS_TRUNCATABLE_DATABASE` consent, scratch artifact roots, and fingerprint-before-and-after |

## 11. Release handles

| | |
| --- | --- |
| implementation PR | `#217` |
| annotated tag | `sprint-21d1-emg-baseline` |
| gate-close PR/current head | `#218`, `1cadbabb5cdabb32bbd502f281d734fb25a229ff` |
| current exact-head CI | `30658256397`, 30 of 30 success |
| D2 implementation branch | `feature/sprint-21d2-useful-learned-activation` |
| D2 success tag | `sprint-21-learning-baseline` |
| D2 negative-evidence tag | `sprint-21d2-evidence-baseline` |
| CI lane for graph work | `experience-graph-core`, credential-free, three extras |
| local equivalent | `uv run pytest tests/cognitive_os/experience tests/cognitive_os/learning -q` |
| verification matrix | `evidence/sprint-21d1-verification-matrix.json`, 22 rows, 306 s |
| architecture | [Experience Memory Graph](../../architecture/experience-memory-graph.md) |
| operations | [Experience Memory Graph operations](../../operations/experience-memory-graph.md) |

Branch protection was not changed and none is proposed. Required approving reviews stay disabled
because a second eligible reviewer does not exist; the limitation is carried forward, not worked
around.
