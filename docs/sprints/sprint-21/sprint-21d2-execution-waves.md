# Sprint 21D2 — execution wave plan

Working plan for executing [the D2 technical backlog](sprint-21d2-technical-backlog.md).
It does not replace the backlog's `§6` wave table; it refines it against measured
repository facts: two probes inserted, four epics resequenced, three waves split along
real dependencies. Task numbering is unchanged (S21D2-000 … -095, 81 tasks in ten epics).

Status: **W0, W1 and W2 complete; W3a probe complete, W3a authoring 10 of 95.** W0 evidence:
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
compare-and-set campaign receipt), -080/-081/085a (CLI command, health output, focused CI
coverage).

**One W2 deliverable is deferred with its reason.** S21D2-054 also asks
`RealityCampaignLedger.plan_resume()` to consume the receipt stream and return a typed
receipt-repair action. The receipt contract, the event, the CAS append and both sequencing
modes are done and tested; the ledger integration is not, because `plan_resume()` is C3
resume machinery with its own callers and changing it without a campaign to resume would be
untested by construction. It belongs with W3c's vertical slice (S21D2-058), which is the first
thing that actually resumes a D2 campaign. Recorded here rather than in a commit message so it
cannot be lost.

**W3a's probe is complete; its authoring is not.** `P-CLONE`
([`sprint-21d2-p-clone-probe.json`](evidence/sprint-21d2-p-clone-probe.json)) authored the
first ten D2 templates and measured what the plan needed to know before committing to
ninety-five. It found a defect in **four of the ten**, none of them visible by inspection, and
the corrected cohort is clean on every axis. It also removed a leak the enum rename alone would
not have: binding recipe to variant *per task* is what stops `recipe_alpha` from being the C3
oracle under a new spelling — measured repair rates are 0.4/0.5/0.5/0.6 where C3 measured 1.0
and 0.0. **85 templates remain**, at a measured ~80 lines each and an expected ~34 further
defect-and-repair cycles.

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
| **F3** | S21D2-022, `§4.1` | **Corpus scale is the critical path.** `TASK_SPECS` holds exactly **30** specs in 3,121 lines (~104 lines each: baseline + 4 candidate variants + visible and hidden test modules + issue/expected/edge-case prose). D2 needs ≥115 groups, ≥85 new ⇒ **~8,800 lines of hand-authored task code**. `reality_task_specs.py:18-20` states the corpus is deliberately unparameterised because variants of one template "share an AST shape, land in one near-clone group" — so `near_clone_pairs` will actively reject mass production. | **Probe first** — `P-CLONE` at the head of W3a measures the rejection rate on 10 before committing to 85 |
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
| **W3a** | **`P-CLONE`**, 022-author | authoring; critical path (F3) | ‖ W2 | ≥85 genuinely new templates; near-clone and source-rights green |
| **W3b** | 022-seal, 026, 027, 028 | manifests, zero outcomes | after W3a | 115 disjoint groups; both OOD submanifests; capability isolation proven |
| **W3c** | 058, **075-scratch** | one group end to end | after W2 + W3b | 10 slice steps green; failed-canary rollback refusal proven on scratch |
| **W4** | 023, 024, 025 | container-bound (F4) | ‖ W5 | ≥200 fit + ≥40 calibration `SELF_PLAY`; zero `REAL_GOVERNED_RUN` |
| **W5** | 031, 032 | measurement | ‖ W4 | canonical resource policy rev 2; width-20 diagnostic on the frozen 80 queries |
| **W6** | 041, 042, 044, 045, *046, 047, 048*, 049, 051, 057, 059 | **one-way door** | none | exactly one candidate **or** an immutable null; `REGISTERED → SHADOW`; final access still closed |
| **W7a** | 060, 061, 062 | holdout opens | none | ≥25 groups / ≥100 outcomes per batch; no setting changed after A |
| **W7b** | 063, 064, 065, 066 | measurement | ‖ W7c | benefit, forgetting, OOD, shadow |
| **W7c** | 033, 034, 035 | retrieval closure | ‖ W7b | ≥50 new queries; one bounded arm ≥0.70 / ≥0.50, or negative |
| **W7d** | **068 → 067** | assessment | after W7b + W7c | D1 remediation record; eligible **or** explicitly ineligible promotion assessment |
| **W8** | 069–074, 075-real, 076, 077 | pass-conditional | none | VERIFIED, approval, canary, kill switch, restart, rollback, steady state |
| **W9** | 083, 084, **085b**, 086 | mandatory on every path | none | recovery, corruption matrix, CI, full isolated matrix |
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

### W3a — corpus authoring (`P-CLONE`, 022-author) ‖ W2
**`P-CLONE` (new).** Author 10 new templates, run `near_clone_pairs` and the source-rights
check, and record the rejection rate. Extrapolate to 85 (F3). If the rate implies the
authoring cost exceeds the sprint, that is a scope decision to take here — with 10 templates
spent — not after 60.

### W3b/W3c — sealing and the vertical slice (022-seal, 026–028, 058, 075-scratch)
Sealing is the second one-way door: counts may rise before it, never after. 058 is `§6.1`'s
ten-step slice; `stop_on_first_accepted` is exercised only through an isolated scratch
component with a fixture ACTIVE receipt. 075's scratch leg runs immediately after, so the
`rollback_permitted=false` refusal is proven before any real activation exists.

### W4 ‖ W5 — self-play evidence and retrieval freeze (023–025 ‖ 031, 032)
W4 is container-bound (F4); W5 is CPU measurement on already-frozen data. They share no
input, so W5 fills W4's container time. 031 freezes the policy chosen from `P-GED`; 032 is
the formal diagnostic artifact and is labelled development-only.

### W6 — learner selection (041–049, 051, 057, 059)
The ladder is a stop-first ladder: a passing k-NN at 045 ends learner work. F12 means the
046 gate needs an executable test that a transitive `sklearn` import cannot satisfy the
dependency contract. 049 is the third one-way door — and by F13 a null there closes final
access *and* forfeits D1 condition 15, so the null branch runs straight to W9/W10.

### W7 — final evidence (060–068, 033–035)
060's access authorization is the fourth one-way door. Predictions come through the narrow
direct loader from the selected SHADOW artifact, never the ACTIVE-only resolver. W7b and W7c
are independent measurement lanes over the same executed batches; W7d is ordered `068 → 067`.

### W8 — governed activation (069–077)
Pass-conditional. 071/072 are the fifth one-way door. A failed canary at 073 disables once
with `rollback_permitted=false`, 074 reuses that receipt rather than issuing a second
disable, and 075's real leg does not run — the scratch proof from W3c already stands.

### W9/W10 — operations and release (083–086, 090–095)
Mandatory on every outcome, including the earliest null. On a stopped path they validate the
fixture/null/negative artifacts and common authorities, and the release is
`sprint-21d2-evidence-baseline` with Gate L2 `does not pass`.

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
