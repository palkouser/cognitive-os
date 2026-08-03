# Sprint 21D2 — execution wave plan

Working plan for executing [the D2 technical backlog](sprint-21d2-technical-backlog.md).
It does not replace the backlog's `§6` wave table; it refines it against measured
repository facts: two probes inserted, four epics resequenced, three waves split along
real dependencies. Task numbering is unchanged (S21D2-000 … -095, 81 tasks in ten epics).

Status: **Sprint complete. W0–W6, W9 and W10 executed; W7 and W8 closed by the null. Released
as `sprint-21d2-evidence-baseline`, Gate L2 does not pass. Door D3 closed on an immutable
null:** the bounded k-NN
ranks an accepted candidate first in nine of ten calibration groups against a 0.3 deterministic
baseline, and reverses at full confidence under a semantics-preserving perturbation, so no
candidate was selected and final access stays closed. W0 evidence:
[`sprint-21d2-baseline.json`](evidence/sprint-21d2-baseline.json),
[`sprint-21d2-d1-erratum.json`](evidence/sprint-21d2-d1-erratum.json),
[`sprint-21d2-inherited-inventory.json`](evidence/sprint-21d2-inherited-inventory.json).
W1 evidence: draft PR `#219`,
[`sprint-21d2-surface-audit.json`](evidence/sprint-21d2-surface-audit.json),
[`sprint-21d2-p-ged-probe.json`](evidence/sprint-21d2-p-ged-probe.json),
[`sprint-21d2-power-analysis.json`](evidence/sprint-21d2-power-analysis.json),
[`sprint-21d2-pre-registration.json`](evidence/sprint-21d2-pre-registration.json).
**Door D1 is closed:** revision 2 selects `experience.correction_ranking` as primary.

**W2 is complete.** All fourteen items landed: S21D2-021 (opaque candidate identity, neutral
recipes, validation before the append), -020 (explicit paged group-aware selection with the
split digest in dataset identity), -040/-043 (encoder and bounded k-NN), -050/-052 (canonical
JSON artifact and narrow loader), -029 (role-bound projector), -053/-055/-056 (runtime
resolver, health reasons, default-off routing), -054 (two-mode sequencer and the
compare-and-set campaign receipt), -080/085a (CLI command and focused CI coverage).

**One further W2 item was not delivered in W2, and this line is a correction.** The paragraph
above previously read `-080/-081/085a`. S21D2-081 — the unified integrity and health report
over role crossing, chronology, manifest membership, artifact lineage, active state, receipt
chain, model identity and store isolation — was in the W2 plan and is not in the W2 commit
(`c3ceb23`, which names -029, -050, -052, -053, -054, -055, -056, -080, 085a). It landed in
W9 instead, where S21D2-083 depends on it. The claim is corrected here rather than quietly
dropped: a wave summary that lists an item nobody wrote is the kind of error that survives
into a gate assessment.

**One W2 deliverable is deferred with its reason.** S21D2-054 also asks
`RealityCampaignLedger.plan_resume()` to consume the receipt stream and return a typed
receipt-repair action. The receipt contract, the event, the CAS append and both sequencing
modes are done and tested; the ledger integration is not, because `plan_resume()` is C3
resume machinery with its own callers and changing it without a campaign to resume would be
untested by construction. It belongs with W3c's vertical slice (S21D2-058), which is the first
thing that actually resumes a D2 campaign. Recorded here rather than in a commit message so it
cannot be lost.

**W3a is complete: the corpus is 95 of 95.** `P-CLONE`
([`sprint-21d2-p-clone-probe.json`](evidence/sprint-21d2-p-clone-probe.json)) authored the
first ten templates and found a defect in **four of them**, none visible by inspection; the
finished corpus is recorded in
[`sprint-21d2-corpus.json`](evidence/sprint-21d2-corpus.json). 95 templates, 380 candidates,
95 distinct repository groups, six families at 16/16/16/16/16/15. Executed rather than
declared: 95/95 baselines pass their visible tests and fail their hidden ones, 380/380
candidates match their declaration, and near-clone collisions are zero both within the corpus
and against every C3 candidate. Binding recipe to variant *per task* is what stops
`recipe_alpha` from being the C3 oracle under a new spelling — repair rates land at
0.57/0.53/0.52/0.39 where C3 measured 1.0 and 0.0.

**This document's own cost projection was wrong by roughly a factor of six.** It extrapolated
`P-CLONE`'s 40% first-pass defect rate to "~34 further defect-and-repair cycles" across the
remaining 85. The measured figure was **6 in 85**. The probe measured authoring *before* the
rules were known, and the four defects it found were what taught them; a first-attempt rate
does not survive past the point where its own lesson lands. The probe earned its place by
buying the rules, not by forecasting the cost.

**W1 changed two planned numbers.** `P-GED` measured the per-pair GED timeout at **90 ms**
rather than the inherited 250 ms (F1 below, superseded by the probe's own finding), and
S21D2-014 raised the final batches to **30+30 groups**, which raises the corpus to **125
groups and 95 new** rather than 115 and 85 (F3's authoring load grows by about ten
templates).

---

## 1. Findings

Every row below was measured in this checkout at `1cadbabb5cdabb32bbd502f281d734fb25a229ff`,
not inferred from the backlog.

| # | Where | Finding | Status |
|---|---|---|---|
| **F1** ⚠️ | `§4.10`, `§8.4` | *Direction confirmed, mechanism wrong — see `sprint-21d2-p-ged-probe.json`. The probe measured per-pair GED cost at p50 0.93 ms for coding and 1501 ms for logic and mathematics, not a uniform ~176 ms, and the convergence fraction is 0.7625 at every timeout from 50 ms to 1000 ms. So the lever is cancelled by a non-converging quarter of pairs rather than by uniform cost, and 90 ms per pair leaves zero cuts at width 20 with a 236 ms margin. Original reasoning below.* **Width 20 is cancelled by the unchanged 2-second budget.** `bounded_ged` reserves the per-pair timeout before starting a comparison (`graph_retrieval.py:225-229`), so it stops at `elapsed > budget − per_pair`. D1 measured p95 **1788.9 ms** for ~10 completed pairs (~176 ms/pair after the 27.5 ms embed). At width 20 with `per_pair=250 ms` and `budget=2 s`, roughly the first 9–10 pairs complete and the rest are cut to score `0.0` — and cut pairs sink under the `-score` sort in `_result`. The cut band is exactly shortlist ranks 11–20, which is where D1's **19 shortlist-ceiling misses** live. Width 20 would then reproduce the width-10 result. | **Fixed in the plan** — probe `P-GED` in W1; the per-pair timeout is chosen from it and pre-registered in 017/031. `§8.4`'s 250 ms and 2 s are *maxima*, so lowering per-pair (~90 ms fits 20 pairs) is compliant; raising the budget after a bad final result is not. |
| **F2** | `§1.4`, S21D2-030 | The shortlist defect is real and one line. `bounded_ged` takes candidates from `minilm_vector`'s public result (`graph_retrieval.py:210`), which `_result` already truncated to `returned_results` (`:88`); the `[: limits.vector_shortlist]` slice on `:211` then re-slices ten entries. `GraphResourceLimits` allows `vector_shortlist` up to 100, so no contract change is needed — only an internal untruncated scoring path. | Confirmed; W1 |
| **F3** | S21D2-022, `§4.1` | **Corpus scale is the critical path.** `TASK_SPECS` holds exactly **30** specs in 3,121 lines (~104 lines each: baseline + 4 candidate variants + visible and hidden test modules + issue/expected/edge-case prose). D2 needs ≥115 groups, ≥85 new ⇒ **~8,800 lines of hand-authored task code**. `reality_task_specs.py:18-20` states the corpus is deliberately unparameterised because variants of one template "share an AST shape, land in one near-clone group" — so `near_clone_pairs` will actively reject mass production. | **Probe first** — `P-CLONE` at the head of W3a measures the rejection rate on 10 before committing to 85. **Settled:** 95 templates authored, 8,523 lines; near-clone collisions within the corpus and against every C3 candidate both zero |
| **F4** | `§4.1` | **Container volume.** C3's W2 ran "30 tasks, 120 candidates, **420 container runs**" (C3 report `§1`). D2's five partitions are 115 groups of the same shape ⇒ **≈1,600 container runs** across W3c–W8, ~3.8× C3, before canary and any post-stop audit campaign. | Drives the W4 ‖ W5 overlap |
| **F5** | S21D2-021, `§9` | **Opaque candidates are a cross-layer change, not a rename.** `RealityCandidateStrategy` is exactly the forbidden family (`incomplete_a`, `incomplete_b`, `correct_narrow`, `correct_robust`, `provider_proposed`); `candidate_id_for(task_id, strategy)` derives candidate identity *from it*; `TaskRuns.candidates` is a **dict keyed by the strategy enum** (`reality_campaign_runner.py:101-115`); and `CodingOutcomeRecorded.candidate_strategy` / `RealityOutcomeReference.strategy` persist it. The `§9` risk "runner reorders by strategy" is live in today's code. | Sequenced first in W2 |
| **F6** | S21D2-021 | `_reference()` is built **after** `self._events.append(...)` (`outcome_recording.py:125-126`). A `RealityOutcomeReference` validator failure therefore leaves the authoritative event durably appended. The validate-before-append refactor the backlog asks for is small and belongs in the same change as F5. | Confirmed; W2 |
| **F7** | S21D2-069 | `advance_component()` refuses `ACTIVE` (`learned_evidence.py:201-205`) but **not** `VERIFIED`, and `verify_component()` does not exist. The backlog's gap description is exact. | Confirmed; W6/W8 |
| **F8** | S21D2-050 | `LearnedArtifactFormat` = `SAFETENSORS`, `JOBLIB`, `NONE` (`learned.py:53-58`); no `JSON`. `UNSAFE_TO_DESERIALISE = {JOBLIB}` (`artifacts.py:33`). | Confirmed; W2 |
| **F9** | S21D2-057 | `MandatoryPathInvariance` carries exactly three decision hashes and `identical` compares those three (`learned.py:420-441`). The optional fourth artifact-unavailable hash is a genuine backward-compatible extension. | Confirmed; W6 |
| **F10** | S21D2-054 | `CodingEventService.append` hardcodes `StreamType.TASK_RUN` (`coding_event_service.py:29`). `StreamType.SYSTEM` already exists (`enums.py:105`). The campaign-sequence receipt needs a narrow stream-type parameter, not a second service or a second store. | Confirmed; W2 |
| **F11** | S21D2-020 | `maximum_page_size` is `Field(default=500, ge=1, le=500)` — the cap **cannot be raised by configuration** — and `LearnedDatasetBuilder.build` calls `list_observations(..., limit=500)` with no offset loop (`learned_datasets.py:147`). `_split` assigns by `observation_id.int % DEFAULT_HOLDOUT_FRACTION` into `("holdout", "train")` (`:71-83`), and `dataset_id_for` hashes `split_policy` *as a string* plus members — so two different assignments over the same members do collide, exactly as `§4.2` says. Splits must also be renamed to `fit`/`calibration`. | Confirmed; W2 |
| **F12** | `§3.3`, `§9` | **`sklearn` already imports** in `.venv`, transitively via `sentence-transformers`/`torch`. The "transitive sklearn import" risk is not hypothetical: a P1 rung can be built on it and nothing will fail. The guard has to be an executable test, not a review note. | Recorded for W6 |
| **F13** | S21D2-033, -068 | **A null learner at 049 also forfeits D1 condition 15.** 033 is `final-conditional` and depends on 049 + 061 + 062, so the retrieval holdout is unreachable on a learner-null path even though E03's work (030–032, 036) is complete and independent of the learner. This is intentional — the queries need executed final outcomes, and self-play groups are already seen — but it means E03 returns diagnostics only on the null path. | **Recorded**, not fixed; changes the expected value of E03 |
| **F14** | S21D2-002, -082 | **PostgreSQL is not a host service.** `pg_lsclusters` is empty and `sudo` is non-interactive here; the database is the rootless container `compose-postgres-1` (`pgvector/pgvector:0.8.2-pg18`) on `127.0.0.1:55432`, healthy. Every D2 database must be created inside it, following `.env.s21d1.local`, which also carries `COGOS_POSTGRES_TOOL_CONTAINER` and `COGOS_CONTAINER_*` URLs for in-container tooling. | W0 entry condition |
| **F15** | `§1.6` | Inherited store fingerprint inputs verified: development pair **5** files, C3 source **8,503**, D1 evidence **83** — all matching `§1.6`. MiniLM present at `cognitive-os-data/models/all-MiniLM-L6-v2`; `networkx`, `sympy`, `z3`, `torch`, `sentence-transformers` all import in `.venv` (Python 3.12.13). `ci.yml` defines exactly **30** jobs. No blocking environment gap for W0. | Verified, no action |
| **F16** | S21D2-002, -084 | **The evidence store has been erased before.** C3's W6-F2: the release matrix truncated the C3 evidence store *twice*, because the integration fixture guarded only on a name ending in `_test` — which the evidence database also ends in. D1's answer was a separate `cognitive_os_s21d1_integration_test`. D2 must inherit that split in W0, before any matrix row runs, not discover it in W9. | **Fixed in the plan** — W0 exit gate |

Verified and correct, no action: `HEAD` = local `main` = `origin/main` = `1cadbabb…`; tag
`sprint-21d1-emg-baseline` → object `a59977db…` → peel `b46c2fcd…`; alembic head `0015`
with `0016` unallocated; `CorpusRole` is two-valued (`TRAINING`, `EVALUATION`);
`ExperienceKnn` exists at `infrastructure/learned/knn.py`; `learned_intake.py` and
`learned_quarantine.py` exist for S21D2-077; every API the backlog names is present.

---

## 2. Wave map

| Wave | Tasks | Character | Parallel | Exit gate |
|---|---|---|---|---|
| **W0** | 000–003, **082** | evidence + operator, no code | — | exact parent revalidated; D2 pair **plus a separate integration database** (F16); three inherited stores fingerprinted; provisioning closed or runbooked |
| **W1** | 004, **030**, **`P-GED`**, 010–016, **036**, 017 | strictly sequential after the probe | 036 ‖ 010–016 | **one-way door**: 017 freezes surface, features, groups, metrics, baseline rule, power *and* resource policy |
| **W2** | **021**, 020, 029, 040, 043, 050, 052, 053, 054, 055, 056, **080**, **081**, **085a** | code only, no evidence | ‖ W3a | every new authority exists and is unit-green before any bulk evidence |
| **W3a** ✅ | **`P-CLONE`**, 022-author | authoring; critical path (F3) | ‖ W2 | ≥85 genuinely new templates; near-clone and source-rights green — **met at 95** |
| **W3b** ✅ | 022-seal, 026, 027, 028 | manifests, zero outcomes | after W3a | 115 disjoint groups; both OOD submanifests; capability isolation proven — **met at 125, all ten pairs disjoint** |
| **W3c** ✅ | 058, **075-scratch** | one group end to end | after W2 + W3b | 10 slice steps green; failed-canary rollback refusal proven on scratch |
| **W4** ✅ | 023, 024, 025 | container-bound (F4) | ‖ W5 | ≥200 fit + ≥40 calibration `SELF_PLAY`; zero `REAL_GOVERNED_RUN` — **met at 200 + 40, acceptance 0.5000 in both** |
| **W5** ✅ | 031, 032 | measurement | ‖ W4 | canonical resource policy rev 2; width-20 diagnostic on the frozen 80 queries — **met; the wider shortlist measured worse (W5-F1)** |
| **W6** ✅ | 041, 042, 044, 045, *046, 047, 048*, 049, 051, 057, 059 | **one-way door** | none | exactly one candidate **or** an immutable null; `REGISTERED → SHADOW`; final access still closed — **an immutable null: the k-NN reached 0.9 against a 0.3 baseline and reversed confidently under a semantics-preserving perturbation** |
| **W7a** | 060, 061, 062 | holdout opens | none | ≥25 groups / ≥100 outcomes per batch; no setting changed after A |
| **W7b** | 063, 064, 065, 066 | measurement | ‖ W7c | benefit, forgetting, OOD, shadow |
| **W7c** | 033, 034, 035 | retrieval closure | ‖ W7b | ≥50 new queries; one bounded arm ≥0.70 / ≥0.50, or negative |
| **W7d** | **068 → 067** | assessment | after W7b + W7c | D1 remediation record; eligible **or** explicitly ineligible promotion assessment |
| **W8** | 069–074, 075-real, 076, 077 | pass-conditional | none | VERIFIED, approval, canary, kill switch, restart, rollback, steady state |
| **W9** ✅ | **081**, 083, 084, **085b**, 086 | mandatory on every path | none | recovery, corruption matrix, CI, full isolated matrix — **met: 29/29 matrix rows, ten damage cases all failing closed, and the backup script stopped from backing up the wrong database (W9-F1)** |
| **W10** | 090–095 | mandatory on every path | none | Gate L2 result, report, handoff, outcome-appropriate tag, gate-result PR |

*Italic* tasks are P1 and open only on their stated continuation condition. **Bold** entries
are moved, split or new relative to backlog `§6`.

### Deltas from backlog `§6`

1. **030 and the new `P-GED` probe move from W5 to W1, ahead of 017.** The resource policy
   cannot be pre-registered honestly without measuring width-20 GED cost (F1), and it cannot
   be measured truthfully before the shortlist fix (F2). Backlog `§6` places both after
   pre-registration, which would freeze a policy that F1 says defeats its own lever.
2. **036 moves from W5 to W1** — it depends only on 030.
3. **082 moves from W9 to W0** — it depends only on 002, and a provisioning gap found in W9
   is a gap found after all evidence exists.
4. **080 and 081 move from W9 to W2** — their dependencies (020, 029, 030, 050, 052, 055) are
   all code.
5. **085 splits.** `085a` (fixture and access-guard lane, after 054) runs in W2; `085b`
   (final-evidence coverage, after 067) stays in W9. The backlog's single 085 depends on
   067, which is final-conditional — so an undivided 085 would leave the branch without CI
   for most of the sprint.
6. **022 splits** into authoring (W3a) and sealing (W3b), with `P-CLONE` in front (F3).
7. **075's scratch leg moves from W8 to W3c.** `§6` already calls it mandatory on every
   outcome; running it before the path is known means a negative release already has it.
8. **021 is sequenced ahead of 020 and 029** — both consume candidate identity, and F5 makes
   that a cross-layer change.
9. **W7 splits four ways.** The backlog's flat `060–068, 033–035` hides that 068 depends on
   034/035 and 067 depends on 068 — so the assessment ordering is `068 → 067`, not the
   numeric order.
10. **Two probes are new**: `P-GED` (W1) and `P-CLONE` (W3a).

---

## 3. Wave notes

### W0 — authority and isolation (000–003, 082)
Branch `feature/sprint-21d2-useful-learned-activation` from revalidated `origin/main`, not
from the D1 tag commit. Create the D2 pair inside `compose-postgres-1` (F14) —
`cognitive_os_s21d2_test`, `artifacts-s21d2`, `backups-s21d2`, `cognitive_os_s21d2_restore_test`
— **and** `cognitive_os_s21d2_integration_test` in the same step (F16). 082 lands here: the
inherited `ALTER ROLE … NOSUPERUSER` abort must fail visibly rather than leave a partial
bootstrap, and `sudo` is non-interactive in this environment.

### W1 — draft PR, retrieval truth, design freeze (004, 030, `P-GED`, 010–016, 036, 017)
Order is fixed: `004 → 030 → P-GED → 010 → 011 → 012 → 013 → 014 → 015 → 016 →
017`, with 036 free to interleave.

**`P-GED` (new, read-only).** With the F2 fix in place, run the frozen D1 80-query set at
`vector_shortlist=20` and record the per-pair GED wall time distribution, the completed-pair
count per query, and the cutoff count — as a *measurement*, with no policy claim and no
metric published. It answers one question: what per-pair timeout lets 20 pairs finish inside
2 seconds, and how many pairs genuinely need more than that? Without it, 031 freezes a policy
that F1 predicts will reproduce the width-10 result.

**014 is a single combined sizing gate.** It must produce both the paired-power group count
*and* the `§4.10` yield estimate for ≥50 qualifying failed-state retrieval queries, because
both feed the same one-way seal in W3b. Counts may rise before sealing and never after.

**017 is the sprint's first one-way door.** After it, only the single `§3.4` pre-final
revision is available, and it may not touch thresholds, final manifests or group partitions.

### W2 — implementation spine (021, 020, 029, 040, 043, 050, 052–056, 080, 081, 085a)
Code only. 021 first (F5, F6): opaque candidate identity, the outcome-neutral D2 recipe set,
`candidate_id_for` off the strategy enum, ordered-manifest preservation through
`TaskRuns`, and the shared validate-before-append validator. 020 next (F11): explicit paged
selection, `fit`/`calibration` split names, and the canonical split digest bound into
`dataset_id_for`. 054 needs only a stream-type parameter on `CodingEventService` (F10).
085a gives the branch a working CI lane from here on.

### W3a — corpus authoring (`P-CLONE`, 022-author) ‖ W2 — **complete**
**`P-CLONE` (new).** Author 10 new templates, run `near_clone_pairs` and the source-rights
check, and record the rejection rate. Extrapolate to 85 (F3). If the rate implies the
authoring cost exceeds the sprint, that is a scope decision to take here — with 10 templates
spent — not after 60.

**Outcome.** 95 templates in `reality_task_specs_d2.py`, 380 candidates, 95 distinct
repository groups, 16/16/16/16/16/15 across the six families. Evidence:
[`sprint-21d2-corpus.json`](evidence/sprint-21d2-corpus.json). Executed, not declared:
95/95 baselines pass their visible tests and fail their hidden ones, and 380/380 candidates
match their declaration. Per-recipe repair rates land at 0.57 / 0.53 / 0.52 / 0.39 against
C3's 1.0 / 1.0 / 0.0 / 0.0 — the oracle is gone, and it is the per-task *binding* rather than
the neutral naming that removed it.

**The probe's cost projection was wrong, and the correction matters more than the number.**
`P-CLONE` measured a 40% first-pass defect rate on ten and this document extrapolated
"~34 further defect-and-repair cycles" across the remaining 85. The measured figure was
**6 defects in 85 — 7%**, roughly a sixth of the projection. The reason is that the probe
measured authoring *without* the rules, and the four defects it found were what taught them;
extrapolating a first-attempt rate past the point where its lesson lands overstates the
remaining work. The probe was still worth running — it just bought knowledge, not a forecast.

**One check was missing and was added mid-wave.** The probe compared D2 baselines against C3
baselines only. Widening it to every D2 variant against every C3 *candidate* immediately found
that `d2_transform.apply_defaults`'s minimal repair was byte-identical to C3
`state_idempotency.merge_settings.incomplete_a` — a task already solved in the inherited
corpus, which is exactly the donor-to-recipient transfer `reality_leakage` exists to refuse.
Reshaping the variant would not have helped, because the same three lines genuinely solve both
contracts, so the task was replaced outright with `d2_transform.rank_records`. Three of the ten
total defects were this kind: a D2 task restating a C3 one (`last_n` = `take_last`,
`parse_ipv4` = `parse_version`, `apply_defaults` = `merge_settings`). All three are invisible
to reading and visible only to the detector.

The 489 corpus tests execute every candidate against both suites through a session-scoped
thread pool — 570 pytest invocations in ~49s rather than minutes — so the check survives as a
gate on every later edit instead of being too slow to keep.

### W3b — sealing (022-seal, 026–028) — **complete**
Sealing is the second one-way door: counts may rise before it, never after. Evidence:
[`sprint-21d2-sealed-catalogues.json`](evidence/sprint-21d2-sealed-catalogues.json). Five
catalogues at 50/10/30/30/5 groups and 500 outcome-free candidate slots, all ten partition
pairs disjoint, seal hash `521e620f…`, reproducible from the corpus and the recorded seeds.
Batch B carries its own seed and its own generator path, and is family-identical to batch A
without being drawn from the same shuffle — it is a confirmation set, so it should look like A.

**The placement of the inherited groups was the real decision.** Five partitions need 125
groups and D2 authored 95, so C3's thirty must be used. Final A, final B and canary must be new
relative to D1, and `S21D2-024` refuses an inherited group in calibration — so training is the
only partition that can hold them, and that is also the only placement keeping a task D1 has
already published out of every number D2 reports. All thirty go to training, none anywhere else.

**They do not bring their identity with them.** A C3 candidate id is `uuid5(task_id, strategy)`,
a reversible encoding of the recipe: reusing one would restore the D1 oracle through the
identifier rather than through a feature — the same leak `F5` found, arriving by a different
road. Inherited tasks enter under D2 opaque positional identity and the neutral binding
instead, and zero of the 120 C3-derived candidate ids appear in the seal. The 214 inherited
`REAL_GOVERNED_RUN` observations stay unread and training-ineligible; only the *tasks* are
reused, re-executed as self-play.

**The check that earns its runtime is the replay.** Every one of the 500 slots executes the
variant it points at against that task's hidden verifier: 500 of 500 match their declaration.
Nothing else catches a wrong recipe-to-position composition, which would mislabel the entire
campaign while every hash stayed stable. Acceptance sits at exactly 0.5000 in all five
partitions, and — measured on the sealed slots rather than on the corpus — no recipe and no
*position* predicts the verdict (positions run 0.448/0.456/0.536/0.560). Position mattered as
much as recipe here: opaque candidate identity is worth nothing if slot zero is always the
answer.

**The frozen feature contract was left alone, deliberately.** `variant_index` is label-adjacent
and belongs in the catalogue, which is control material like the hidden verifier bundle. Adding
it to `FITTED_FEATURE_DENYLIST` would change the pre-registered contract's hash and spend the
single pre-final revision `§3.4` permits — to buy a guarantee the allowlist already gives, since
it rejects by absence. A test asserts no catalogue field name appears in the allowlist instead.

**Deferred with its reason.** No adapter from `SealedPartitionCatalogue` to the projector's
`SealedCampaignManifest` was written. That shape needs `campaign_id`, `campaign_version` and
`feature_sealed_at`, none of which exist until a campaign does, so building it now would be
untested by construction. It belongs with W3c's vertical slice (S21D2-058), the first thing
that runs one.

### W3c — the vertical slice (058, 075-scratch) — **complete**
`§6.1`'s ten steps run as ten test classes, so a failure names the step it broke. Evidence:
[`sprint-21d2-vertical-slice.json`](evidence/sprint-21d2-vertical-slice.json). One training
group and one synthetic sealed-evaluation group go through rights-clean packaging, pre-outcome
feature sealing, role-bound projection, the group-aware split, one k-NN fit, canonical JSON,
the narrow loader, both sequencing modes, fallback, restart determinism, and the closed
holdout — with **zero containers spent and zero final bodies opened**. CI runs it on committed
deterministic vectors; the pinned MiniLM identity check stays a separate local release step and
is not claimed here.

**Both deferred items are closed.** The catalogue-to-campaign adapter could finally be written
because a campaign now supplies the three values it needs. `plan_resume_with_receipts()` gives
the typed answer W2 asked for — five actions over the receipt chain, of which
`refuse_contradicted_receipt` is the one that matters: an outcome for a candidate the receipt
calls intentionally unattempted means the two durable records disagree, and that is a new
revision, not a resume.

**Writing it found a defect in itself.** The first implementation read candidate outcomes
through `completed_by_identity`, which silently drops any run recorded without a run identity
key. Candidate runs need not carry one, so an interrupted sequence looked like a task nobody
had touched and would have been planned as fresh work — the precise failure the receipt exists
to prevent, reintroduced by the code meant to prevent it. Caught by the `rerun_unsealed_task`
test; fixed by reading the outcome streams directly.

**075's scratch leg exposed a missing authority, not a missing test.** The backlog asks
`roll_back()` to refuse a disable receipt carrying `rollback_permitted=false`, and no such field
existed anywhere in the codebase — the refusal was unwritable. It is now a hash-bound field on
`LearnedActivationReceipt`, required on a disable and forbidden on every other action, and
`disable()` takes it with **no default**: a disable after a failed canary and a disable that
parks a healthy component are indistinguishable from inside the service, so a default would
guess, and the permissive guess is exactly how a failed component gets restored. The refusal is
structural — the chain is read before the caller, the approval or the lineage, so better
evidence cannot step around it.

**That change had a compatibility question, and it was measured rather than assumed.** A new
field on a hashed contract changes the canonical hash of every receipt, so any receipt persisted
earlier would fail to load. The inherited inventory records `learned_components = 0` in the D1
store: **zero receipts at risk**. What the wave plan wrote as a sequencing preference —
"before any real activation exists" — is really a hard compatibility requirement, and the
window was still open. Anyone running D2 against a store that already holds activation receipts
needs a migration first.

The contract schema drift gate caught the receipt change before the commit, which is what it is
for; `learned-activation-receipt.schema.json` was regenerated.

### W4 ‖ W5 — self-play evidence and retrieval freeze (023–025 ‖ 031, 032) — **complete**
W4 is container-bound (F4); W5 is CPU measurement on already-frozen data. They share no
input, so W5 filled W4's container time.

**W4 met every floor and spent 300 containers to do it.**
[`sprint-21d2-self-play-campaign.json`](evidence/sprint-21d2-self-play-campaign.json):
50 training groups → **200** `SELF_PLAY` outcomes, 10 calibration groups → **40**, plus 60
baselines, none of which passed its hidden suite. Acceptance is exactly **0.5000** in both
partitions, which is the 2-of-4 authored balance arriving intact through the sandbox. Zero
`REAL_GOVERNED_RUN` observations were written, no final, batch-B or canary body was opened,
and the D2 pair is the only store touched.

The order inside the command is the deliverable, not a detail. Every candidate's pre-outcome
features are encoded and sealed into one hash-bound artifact *before the first container
starts*, so `every_feature_record_precedes_its_outcome` is a statement about the wall clock —
and `CorrectionRankingObservationProjector` refuses an outcome that predates its own seal, so
a campaign run in the wrong order cannot produce an observation at all. Features come from the
frozen local MiniLM, the task text and the stored diff; nothing else.

**025's snapshot is exact rather than ambient.** One `CorpusRole.TRAINING` dataset of 240
observations with `fit` (200) and `calibration` (40) as explicit splits sharing no repository
group, selected by an explicit member list instead of whatever the store happens to hold —
which is what made the snapshot survive the duplication below. Rebuilt from the same inputs it
returns the same identity, which is the restart/replay identity test.

**024's OOD perturbations are resolved and executed, not declared.** All four presealed
perturbations were applied to the ten calibration groups; the reorder had nothing to swap in
eight of them and says so rather than being given one. All ten perturbed packages still pass
their published suites, because a probe that cannot run measures whether the ranker notices
broken Python.

**Three findings, and the second one cost 300 containers.**

*W4-F1.* `RealityCampaignSequenceRecorded` was declared *below* `CODING_EVENT_MODELS` in the
same module, so the default catalog never registered it and the real Event Store refused it as
an unsupported contract. The campaign receipt — the durable authority for what a stop-first
campaign deliberately did not do — could not be appended at all. W2 and W3c exercised the
sequencer against an in-memory recording double, which is exactly why it looked finished.

*W4-F2.* The first resume re-executed all 300 containers while reporting a resume.
`prepare_task` minted a fresh control-bundle artifact, the task manifest names its bundle by
artifact ID, and the run identity hashes the manifest — so every run got a new identity and
matched nothing. C3 had already learned this and passed its bundles back; this command did
not. Bundle IDs are now recorded per partition and a runner test pins the identity.

*W4-F3.* With F2 fixed, the resume replayed every run and then refused to project any of
them: the replayed outcomes carry their original times and the feature set had been re-sealed
with the current clock, so every outcome preceded its own feature record. The projector was
right. A resume that re-seals features has not resumed the campaign — it has produced
post-outcome features for it. The recorded seal time is now carried across a resume and the
re-encoded set must reproduce the recorded hash.

**One deviation, recorded rather than tidied.** W4-F2 means the same 240 candidates were
executed twice under two sets of run identities, so the store holds 480 accepted observations
for 240 distinct pieces of work. Both executions are real and every row resolves to bytes and
to an event. Nothing was deleted: `store_before_campaign` records what this run inherited, and
because the snapshot selects an explicit member list the dataset is exactly 240 regardless.
The final resume replayed 300 identities, started zero containers and added zero rows.

**W5 froze the policy and then found that the wider shortlist is worse.** 031's revision 2 is
now a named object, `GRAPH_RESOURCE_POLICY_REVISION_2`, whose hash matches the one
pre-registration froze before any D2 measurement existed; the class defaults deliberately did
not move, because every Sprint 21D1 result was produced under them. Contract tests pin the
three acceptance clauses: a comparison never starts unless its timeout is reserved, a cut-off
pair keeps its shortlist place and is counted, and every result carries the policy it was
produced under.

032 re-measured the frozen 80 queries under it
([`sprint-21d2-d1-retrieval-diagnostic.json`](evidence/sprint-21d2-d1-retrieval-diagnostic.json),
development-only, D1's own evidence read and never written). **W5-F1: the bounded graph arm
got worse** — top-5 recall 0.5875 against 0.675, MRR 0.3628 against 0.4481, nDCG 0.2327
against 0.3438 — while the other four arms are unchanged to four decimal places, which is what
says the difference is the shortlist rather than the run. Timeouts went from 60 to 0, and that
is the explanation rather than a second result: ten pairs at 250 ms overruns the two-second
budget, so revision 1 cut off 60 comparisons and scored each of them 0.0, which happened to
keep weak candidates out of the top ten. Twenty pairs at 90 ms fits, every comparison
completes, and the extra ten are ranked on their real distance. **The revision 1 number was
flattered by its own incompleteness.** Nothing in D2 is decided by this: the primary surface
is `experience.correction_ranking` and the retrieval floors belong to 033/034 on a holdout
that does not exist yet.

### W6 — learner selection (041–049, 051, 057, 059) — **complete, and it is a null**
The ladder is a stop-first ladder: a passing k-NN at 045 ends learner work. F12 means the
046 gate needs an executable test that a transitive `sklearn` import cannot satisfy the
dependency contract. 049 is the third one-way door — and by F13 a null there closes final
access *and* forfeits D1 condition 15, so the null branch runs straight to W9/W10.

**Door D3 closed on an immutable null**
([`sprint-21d2-learner-selection.json`](evidence/sprint-21d2-learner-selection.json)). The
short version: **the learner works and is not yet trustworthy.**

**041: the matrices are clean, and the scans can fail.** Eight scans over the serialized fit
and calibration matrices — forbidden fields, chronology, one source chain per row, group
split, contradictory duplicates, cross-split near-duplicates, and perfect label separation per
column on both splits. All pass on the real corpus: 240 rows, 11 columns, 60 groups sharing
none, highest cross-split similarity **0.978** against a 0.999 floor, and every row reproducing
the feature hash its seal recorded before execution. The scans are exercised against seeded
failures rather than described: an injected oracle column and an injected `candidate_id` column
each fail the scan named for them.

**042: the baseline is derived, and one rung is honestly ineligible.** Four rungs run —
0.3 / 0.1 / 0.3 / 0.3 for fixed order, static ordering, lexical overlap and MiniLM cosine — and
`width_20_bounded_graph` is recorded **ineligible with its reason**: a correction task presents
exactly four candidates, so a twenty-wide shortlist is the entire pool and the rung reduces to
its own tie-break. `fixed_input_order` at **0.3** is the strongest non-learned rung; the
contract recomputes that from the ladder and refuses a record that names a weaker one.

**044: the k-NN finds the signal.** At `k=3` with the loosest floors it ranks an accepted
candidate first in **nine of ten** calibration groups at 0.9 coverage — against a 0.3 baseline,
on a corpus where every group has exactly two accepted candidates of four. All 24 grid settings
stay in the record.

**And it is not invariant, which is what ended the wave.** On `d2_parsing.parse_csv_row` the
same setting is correct at confidence **1.0** unperturbed and wrong at confidence **1.0** once
identifiers are renamed and the issue text restated — a semantics-preserving perturbation whose
executed labels are unchanged (20 accepted of 40, exactly as before; the probe's labels come
from executing the perturbed hidden suites, not from assuming they carried over). Twenty of 24
settings produce at least one confident OOD error; the other four produce none by abstaining on
every probe.

**045: fail, `ood_deficient`, and the ladder stops rather than continues.** The frozen contract
allows zero confident OOD errors and §3.3 requires the OOD checks to pass before a rung may be
selected, so the null follows from the pre-registration rather than from a judgement made
today. **046 and 047 are not opened, and the reason is not "we ran out of time":** an
invariance failure is not a capacity failure, and a parametric model fitted on the same features
would meet the same perturbation. `FailureKind` now says in itself which kinds open a later
rung. No dependency was added and no code path imports `sklearn` — which F12 makes worth
stating, because it imports transitively already and a rung could have been built on it
unnoticed. **048 is unused; one §3.4 revision remains.**

**049: null.** No artifact was written and no lifecycle revision allocated, because 051 and 059
are candidate-conditional and there is no candidate. The record names the failed continuation
rule and states in a field that it authorises no final access.

**057 ran anyway, on the null path, and it is the one guarantee that still holds.** The
invariance record now carries Sprint 21D2's fourth configuration — present, enabled, artifact
unloadable — alongside absent, disabled and abstaining. That is the state nobody chooses and
the one a corrupt blob actually produces, and the digest was taken with the loader genuinely
refusing (`CorrectionArtifactError`) rather than with a simulated failure. All four digests
agree over 68 cases. The field is optional so every pre-D2 record still loads, and
`assess_promotion` gained an explicit D2 requirement so an older three-hash record cannot carry
a D2 component to eligible — tested in both directions. As in W3c, the compatibility window was
measured rather than assumed: **zero stored evidence records and zero activation rows** in the
D2 pair.

**W6-F1: a hole in my own selection rule, found by running it.** As first written the rule
filtered a setting only for *producing* a confident OOD error. Four settings recorded zero by
abstaining on all ten probes — passing a safety check by never taking it — and since they still
changed decisions on calibration they survived every other filter. The rule then selected one
of them, a setting scoring exactly the baseline, and the continuation record classified the
failure from column separation alone as `signal_is_linear`, **which authorises the parametric
rung**. A hole in a safety filter was one step from adding a dependency to the repository. The
evaluator manifest already states the principle for calibration coverage; applying it to the
probe as well is what closed it. The verdict was unchanged — the rung fails either way — but
the reason and the branch were not.

### W7 — final evidence (060–068, 033–035)
060's access authorization is the fourth one-way door. Predictions come through the narrow
direct loader from the selected SHADOW artifact, never the ACTIVE-only resolver. W7b and W7c
are independent measurement lanes over the same executed batches; W7d is ordered `068 → 067`.

### W8 — governed activation (069–077)
Pass-conditional. 071/072 are the fifth one-way door. A failed canary at 073 disables once
with `rollback_permitted=false`, 074 reuses that receipt rather than issuing a second
disable, and 075's real leg does not run — the scratch proof from W3c already stands.

### W9 — operations (081, 083–086) — **complete**
Mandatory on every outcome, including the earliest null. Evidence:
[`sprint-21d2-operations.json`](evidence/sprint-21d2-operations.json) and
[`sprint-21d2-verification-matrix.json`](evidence/sprint-21d2-verification-matrix.json).

**081 arrives here rather than in W2, and its third state is what the null needed.** The
report carries eight classes. Six could be measured. Two — activation state and model
identity — have nothing behind them, because no component was ever registered, and a report
that answered "0 wrongly-active components" would have been true and misleading at once. They
are recorded as `not_opened`, each bound to the hash of the selection record that closed them.
The state is not a way to skip a check: a component found on the stopped surface turns the
not-opened claim straight into a failure, and S21D2-084's tampering row proves it does.

**Running the chronology check for the first time reported half the store as out of order,
and the check was wrong, not the store.** W4-F2 made the campaign execute the same 240
candidates twice, and each execution sealed its own feature set. Measured against the one seal
the campaign evidence names, the 240 rows from the earlier execution looked like outcomes that
preceded their own features. They were nothing of the kind — each was pre-outcome under the
seal it actually ran under, and that seal is still in the store. The check now discovers every
seal a campaign manifest carries and measures each row against the earliest, and a separate
warning states plainly that two manifests were sealed three times each, so a dataset over this
store must select an explicit member list rather than every row. That warning is W4-D1 finally
saying itself, in the report, instead of only in a deviation note.

**W9-F1: D2 had no operations document, so nothing stated the shell scripts' prerequisite.**
An operator who follows this sprint's own convention — `set -a && . ./.env.s21d2.local && set
+a`, which every D2 command and evidence file records — and then runs
`scripts/backup_event_store.sh` gets a dump of `cognitive_os_dev`. The first run of
`scripts/operations_d2.py` did exactly that and wrote a partial dump into the development
backup root before aborting. The matrix hit it from the other side:
`postgres_migration_check.sh` reported "Database is not on all head revisions", true about the
development database and alarming about the wrong one.

**The first attribution was wrong and is corrected here.** This was recorded as a defect in
`postgres_common.sh`, on the reasoning that `load_postgres_environment()` re-sources
`$COGOS_POSTGRES_ENV_FILE` inside `set -a` and overwrites exported handles. The mechanism is
right; the attribution was not. That override is deliberate and documented —
`docs/operations/learned-evidence.md` says in as many words that exporting the variables is
not enough and that this is what stops a mis-scoped command reaching a real database — and
both C3 and D1 document the correct form, `COGOS_POSTGRES_ENV_FILE=$PWD/.env.<sprint>.local
./scripts/backup_event_store.sh`, in their own operations guides. What D2 lacked was the
operations document that would have said so, which is exactly what S21D2-090 was for. Guarded
in addition by refusing any backup manifest that does not name the D2 database, so a
mis-scoped run is a refusal rather than a quiet substitution. No repository script changed.

**What 083 proves on a null path is an absence.** On the success path the assertion would be
that the runtime resolves the same active model. There is none, so what has to survive the
restore exactly is the inactive state — zero components, revisions, evidence records,
approvals and activations — which is the easiest thing for a restore to get wrong in the
safe-looking direction. Counts, the roll-up over every hashed row, all 1511 artifact blobs
re-hashed, and every store-side input to `plan_resume_with_receipts` match between source and
restore; the container was restarted between the two captures.

**084's ten damage cases all fail closed, and two of them moved.** The poisoned feature record
never reaches the seal check at all: the contract re-seals on load and refuses the bytes, which
is a stronger refusal than the one the case was written to demonstrate, so it is recorded as
what happened. That left the seal-hash check unexercised, so a second case was added for the
attack poisoning cannot mount — a *valid* seal from another execution served under the declared
artifact identity. Only the independently recorded hash catches that one.

**085b covers a null instead of final evidence.** The plan reserved it for coverage after
S21D2-067; there is no final evidence, so the lane owns the opposite guarantee — the eight
integrity classes and a guard over the published evidence files, so that a record which now
says "not opened" cannot quietly start saying "zero". The recorded CI steps are extracted from
the workflow rather than transcribed, and a test fails if a step named in the evidence is no
longer in the lane.

**086 lists the rows a stop closed rather than omitting them.** Five conditional rows — the
holdout, the benefit and forgetting measurements, the promotion assessment, approval and
canary, and 075's real leg — carry the selection record's hash instead of an exit code, and
the matrix refuses to record them that way at all if the selection record ever names a
candidate. **29 of 29 rows passed, none failed, none skipped**, in 812 seconds: lint, format,
typing, security, schema drift, language, the unit / contract / full suites, the Docker coding
slice, the isolated PostgreSQL lane, packaging, migration head and check, benchmarks, the C3
and D2 operator commands, and all four artifact pairs — development, C3, D1 and D2 — measured
before and after and byte-identical across every destructive row.

**Two matrix rows failed first and both were the matrix's fault, not the repository's.**
`migration_check` reported "Database is not on all head revisions" — W9-F1 from the other
side, a true statement about `cognitive_os_dev` made while verifying the D2 release. A defect
that produces a *plausible failure about the wrong store* is worse than one that crashes,
because the natural next move is to go and migrate something. `artifact_recovery` invoked
`scripts/artifact_restore_verify.py` bare; it is a helper that `restore_event_store.sh` pipes
metadata into, so the row only ever proved that it prints its usage. The row was removed
rather than repaired, because recovery is proven where it happens.

### W10 — release (090–095) — **complete**
Evidence: [`sprint-21d2-release.json`](evidence/sprint-21d2-release.json),
[`gate-l2-assessment.md`](gate-l2-assessment.md),
[`sprint-21d2-report.md`](sprint-21d2-report.md),
[`sprint-21d3-handoff.md`](sprint-21d3-handoff.md),
[`correction-ranking.md`](../../operations/correction-ranking.md).

PR `#219` squash-merged with no administrator bypass to `ecb5ea12…`, exact-head `main` CI run
`30788129259` 30 of 30 success, and the annotated tag `sprint-21d2-evidence-baseline` created
**once, after** that CI — object `3f3c00e2…`, identical on the remote, peeling to the same
commit. `sprint-21-learning-baseline` is forbidden on this path and was not created.
Protection unchanged at 27 required contexts with `enforce_admins`.

**Gate L2 does not pass: fifteen conditions met, one met as a rejection, thirteen not opened.**
The thirteen are marked not opened rather than failed or skipped, each naming the record that
closed it, because a failed condition is a measurement that came out badly and a not-opened one
is a measurement that was never authorised. Gate D1 conditions 6, 7 and 15 remain open and the
null forfeits all three. Sprint 22A stays blocked; the handoff targets Sprint 21D3.

**090 turned out to be W9-F1's real fix, and the finding's attribution was corrected.** W9-F1
was recorded as a defect in `postgres_common.sh`. The mechanism was right and the attribution
was not: the environment-file override is deliberate and documented — `learned-evidence.md`
states that exporting the variables is not enough and that this is what stops a mis-scoped
command reaching a real database — and both C3 and D1 document the correct invocation in their
own operations guides. What D2 lacked was the operations document. No repository script was
changed.

---

## 4. One-way doors and valid stops

| Door | Task | After it |
|---|---|---|
| D1 | **017** | surface, features, groups, metrics, baseline rule, power and resource policy are frozen; only the single `§3.4` revision remains |
| D2 | **022-seal** | member manifests and group partitions are fixed; counts may never fall |
| D3 | **049** | exactly one candidate, or a null that closes final access **and** forfeits condition 15 (F13) |
| D4 | **060** | final batch A opens; no feature, label, grouping, baseline, threshold or metric may change |
| D5 | **071/072** | the component is approved and active in the canary subset |

Valid negative stops, each producing a complete negative release rather than a retry:
010 rejects the surface · 017 records a null primary · `P-CLONE` shows the 85-group corpus is
unreachable · 045/046/047 all fail calibration → 049 null · 034 misses both retrieval floors ·
063 fails benefit, direction or interval · 064/065 fail safety, retention or OOD · 073 fails
canary. In every case E08 and E09 still run in full.
