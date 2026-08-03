# Gate L2 assessment — Useful Learned Activation

- Sprint: 21D2
- Assessed: 2026-08-02
- Branch: `feature/sprint-21d2-useful-learned-activation`
- Parent baseline: `sprint-21d1-emg-baseline`, tag object `a59977dbcf23df60a700385a6fc15b012bf6d142`,
  peeled to `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`
- Planning head: `1cadbabb5cdabb32bbd502f281d734fb25a229ff`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
- Revision: 2 — post-release. Condition 29 is closed on the handles in
  [`sprint-21d2-release.json`](evidence/sprint-21d2-release.json).

## Verdict

**Gate L2 does not pass.**

Twenty-nine conditions. **Fifteen are met**, one is met as a rejection, and thirteen are **not
opened**. No condition failed on a number that could have been argued about, because the
sprint stopped before the conditions that measure a model were reachable.

The gate does not pass on met conditions. It passes only when *every applicable* condition is
met, and thirteen were never authorised to be measured — which is the outcome `§0.4` and
`§11.3` define as a valid negative completion, not a shortfall in the release.

The stop is condition 12's, at S21D2-049. The bounded k-NN ranked an accepted candidate first
in **nine of ten** calibration groups against a **0.3** deterministic baseline — the signal is
real and larger than any threshold in this document — and every setting in the pre-registered
grid that found it also answered **confidently and wrongly** on a semantics-preserving
perturbation. The four settings that produced no confident out-of-distribution error produced
no out-of-distribution *answer* either: they abstained on all ten probes. Zero errors out of
zero answers is not a pass; it is a skipped check, and the selection rule was corrected to say
so before it selected anything.

So no candidate was selected, no artifact was written, the final holdout was never opened, and
nothing was registered, approved or activated. Under `§0.4` and `§11.3` that is a **valid
negative completion**, not a failure to complete: the stop condition is immutable, no
forbidden downstream data was opened, every dependent task has a not-opened record, and the
evidence is released under `sprint-21d2-evidence-baseline`.

**Gate D1 conditions 6, 7 and 15 remain open.** D2 was their remediation route and the null
forfeits all three — 6 and 7 because they close only from final D2 surface evidence that was
never opened, and 15 because `§2.3` closes it only on a new D2 unseen-task retrieval holdout,
which S21D2-033–035 would have produced in W7c.

## Condition by condition

Thirteen conditions are marked **not opened** rather than failed or skipped. The distinction
is load-bearing: a failed condition is a measurement that came out badly, and a not-opened one
is a measurement that was never authorised. Each names the record that closed it. The
selection record hash is `274a7a932ce110d12892f3dab102f10308ad556c563483d414979cbc69950536`
and the continuation record hash is
`4e5a690f16b64c22239d9e95f841a1350eeb1ad914694dd496488214a289f321`.

| # | condition | status | handle |
|---|---|---|---|
| 1 | D1 tag object, peeled commit, `origin/main`, both exact-head CI runs, protection, migration head, collaborator count and store fingerprints revalidated | **met** | `sprint-21d2-baseline.json`: tag object `a59977db…` equals the remote, peels to `b46c2fcd…`; CI `30657167717` and `30658256397` both 30 of 30 success at their exact heads; 27 required contexts, `enforce_admins: true`, 1 collaborator; head `0015`; three inherited pairs fingerprinted |
| 2 | D2 starts from the current planning head and preserves the D1 release as immutable predecessor evidence | **met** | branched from `1cadbabb…`; no D1 tag, evidence file or artifact pair was modified — `artifacts-s21d1` is `f7b14ac7…` over 83 files before and after every wave |
| 3 | the D1 erratum is recorded without modifying the protected D1 tag or falsifying its chronology | **met** | `sprint-21d2-d1-erratum.json`: discrepancies recorded against the D1 release as published; `protected_objects_unchanged` true |
| 4 | pre-registration revision 2 names `experience.correction_ranking` primary and `experience.correction_context` secondary before any final holdout outcome is inspected | **met** | `sprint-21d2-pre-registration.json` revision 2, published in W1; `final_outcomes_inspected: 0` in every evidence file from W1 to W9 |
| 5 | the label is the independent verifier's accepted/rejected outcome, the primary unit is a task-group ranking, and the executed correction is never accepted by prediction | **met** | the hidden pytest suite decides every label; `CorrectionRankingObservationProjector` refuses a label-predicting recipe; the runtime influences ordering only and every learned-first attempt still runs the verifier |
| 6 | zero hidden-verifier, solution/control, outcome, post-outcome timing, provider-answer, candidate-strategy, identity, raw-hash or answer-revealing fields in the fitted feature set | **met** | `sprint-21d2-learner-selection.json` `fitted_matrix_validation`: 11 columns, all on the `correction-ranking-v1` allowlist; `no_forbidden_field_reaches_the_matrix` and `no_column_derives_the_label` clean on both splits; a seeded oracle and a seeded identity column are refused by test |
| 7 | task, repository, template lineage, near-duplicate cluster and source lineage do not cross training, calibration, final A, final B or canary roles | **met on the roles that exist** | 125 disjoint groups sealed in W3b, all ten partition pairs disjoint; 50 fit and 10 calibration groups share none; maximum cross-split similarity 0.978 against a 0.999 near-duplicate floor. The final and canary roles were never populated, so the guarantee is proven over the partitions that exist and is untested against ones that do not |
| 8 | at least 200 verifier-backed `SELF_PLAY` observations for fitting and at least 40 separate ones for calibration | **met** | 200 fit and 40 calibration, exactly at the floor; acceptance 0.5000 in both partitions; `sprint-21d2-self-play-campaign.json` |
| 9 | zero `REAL_GOVERNED_RUN` observation IDs in the training and calibration snapshots, including the 120 D1 deferred examples | **met** | `provenance_counts: {self_play: 240}`, `real_governed_runs_in_training: 0`; the projector binds the role from the sealed partition and cannot be passed one |
| 10 | final batches A and B each ≥100 new verifier-backed `REAL_GOVERNED_RUN` outcomes over ≥25 task groups | **not opened** | S21D2-060 was never authorised. `authorises_final_access: false` on the selection record `274a7a93…` |
| 11 | both final manifests hash-bound and inaccessible to fitting code; one candidate, artifact and threshold selected before either final outcome is opened | **partially met, then not opened** | the manifests were sealed in W3b and no fitting code can reach them; the selection that would have named a candidate produced a null, so there is nothing to have selected before opening anything |
| 12 | the strongest deterministic baseline and every attempted learner rung recorded; k-NN first, later rungs only on their stop rules | **met — and this is where the sprint stopped** | ladder `8c6b28db…`: `fixed_input_order` 0.3, `deterministic_static_ordering` 0.1, `lexical_similarity` 0.3, `frozen_minilm_cosine` 0.3, `width_20_bounded_graph` ineligible **with its reason** rather than scored zero. Baseline derived by contract, not supplied. All 24 grid settings recorded with their filter reason; 0 eligible. S21D2-046/047 not opened, and the record says why: the failure kind is `ood_deficient`, which does not authorise a parametric rung |
| 13 | at least 20 final task decisions differ from the strongest deterministic baseline | **not opened** | no final decisions exist. Closed by `274a7a93…` |
| 14 | ≥5 percentage points aggregate gain, or ≥20% relative error reduction, over that baseline | **not opened** | closed by `274a7a93…`. On *calibration* the candidate reached 0.9 against 0.3 — recorded, and not evidence for this condition, which is about final data |
| 15 | task-paired bootstrap, seed 21041, 2 000 resamples, lower bound above zero | **not opened** | closed by `274a7a93…` |
| 16 | the learned-minus-baseline direction positive in each independent final batch | **not opened** | closed by `274a7a93…` |
| 17 | coverage, abstention, confidence, attempts-to-first-accept, latency, provider calls, verifier calls, failures and costs reported with exact denominators | **met for what was measured** | all 24 settings carry first-choice rate, coverage, changed decisions, confident OOD errors, OOD answered and maximum inference milliseconds over stated denominators. The final-run costs the condition also names do not exist |
| 18 | no safety, governance, permission, secret-handling or destructive-action case moves from accepted to rejected | **not opened** | no learned component ever decided anything. Closed by `274a7a93…` |
| 19 | no retained domain loses more than 2 points, aggregate loses no more than 1, every small-suite regression reviewed | **not opened** | closed by `274a7a93…` |
| 20 | ≥100 pre-registered OOD/adversarial decisions over ≥10 groups, ≤1% false-confident action rate, promotion requiring exactly zero | **failed at calibration scale, before the final scale was authorised** | 10 groups, 40 decisions, submanifest `48d3b766…`. 20 of 24 settings produced at least one confident error; the other 4 answered no probe. The probe was verified rather than trusted: `d2_parsing.parse_csv_row` is correct at confidence 1.0 unperturbed and wrong at confidence 1.0 perturbed, and `ood_accepted_variants: 20 of 40` confirms the perturbations preserve semantics. **This is the finding the sprint stopped on** |
| 21 | shadow mode changes zero executed decisions and links outcomes only through independent verifier evidence | **not opened** | closed by `274a7a93…` |
| 22 | the selected artifact is canonical JSON with exact dataset, split, feature, embedding, code, configuration and member hashes; unsafe formats unloadable | **half met, half not opened** | the *format* is met and tested: canonical JSON, no format dispatch, no class name, no import path; `JOBLIB` stays in `UNSAFE_TO_DESERIALISE` with no runtime load path and a test asserts the loader has no `load`/`open`/`deserialise`. No artifact was written, because writing one for a candidate nobody selected would be a model nobody chose |
| 23 | missing, corrupt, oversized, schema-invalid, wrong-model, inactive, disabled, unapproved or mismatched artifacts immediately fall back with a structured health reason | **met** | twelve named fallback reasons, each with a test; two active revisions on one surface fail closed rather than picking one; health never claims active when the runtime uses the baseline. Exercised on real bytes by `sprint-21d2-operations.json`: a poisoned seal is refused at deserialisation, a substituted valid seal by the recorded hash, a deleted blob by the read path |
| 24 | at least one bounded retrieval arm on **new D2 unseen-task evidence** reaches Recall@5 ≥ 0.70 and MRR@10 ≥ 0.50 inside the resource budget | **not opened** | S21D2-033–035 sit in W7c, which the null closed. The W5 measurement is the frozen **D1** 80-query set and is labelled development-only: under resource policy revision 2 the graph arm reaches 0.5875 recall and 0.3628 MRR — *worse* than revision 1's 0.675/0.4481, because 60 budget cutoffs became 0 and the old number was flattered by its own incompleteness. `§2.3` states that rerunning the D1 queries is diagnostic, never closure |
| 25 | fail-closed runtime hash-binds the canary subset, every learned-first correction runs the verifier, kill switch returns immediately to deterministic ordering | **not opened** | no canary subset exists. Closed by `274a7a93…` |
| 26 | activation, active projection, artifact loading, disable, fallback, restoration and rollback evidence survive process restart | **not opened for the lifecycle; met for what exists** | no activation exists to survive anything. What does exist survived: PostgreSQL was restarted between two captures and the store shape is identical, `sprint-21d2-operations.json` |
| 27 | a human operator approves the exact promotion assessment, component revision and artifact lineage; no model or provider identity approves or reviews itself | **not opened** | nothing was submitted for approval. No approval was fabricated, and none is claimed |
| 28 | PostgreSQL replay, backup/restore, corruption, artifact verification, packaging, schema, security, language, focused CI and the complete local matrix pass in isolated stores | **met** | `sprint-21d2-verification-matrix.json`: **29 of 29** rows on their expected exit status in 812 s, none failed, none skipped; all four artifact pairs byte-identical before and after every destructive row. `sprint-21d2-operations.json`: counts, hashed-row roll-up, all 1511 blobs re-hashed and every store-side resume input identical between source and restore; ten damage cases all fail closed |
| 29 | protected merge, exact-head post-merge `main` CI, Gate L2 assessment, D2 report, handoff, annotated tag and remote verification | **met** | PR **#219** squash-merged with no administrator bypass to `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` at 05:46:52Z; exact-head `main` CI run **30788129259** 30 of 30 success at that commit, complete 06:00:49Z; annotated tag `sprint-21d2-evidence-baseline` created **once, after** that CI — object `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`, identical on the remote, peeling to the same commit; `origin/main` re-read at `ecb5ea12…`; protection unchanged at 27 required contexts with `enforce_admins`; `sprint-21-learning-baseline` **not created**. [`sprint-21d2-release.json`](evidence/sprint-21d2-release.json) |

## Gate D1 remediation — a separate mapping

D2 was the remediation route for the three conditions D1 left open. It closes none of them,
and the reason differs by condition.

| D1 condition | D2 outcome | why |
|---|---|---|
| 6 — a learnable surface with enough eligible held-out outcomes | **not closed** | `§2.3`: closes only from new, final D2 surface evidence. The final holdout was never opened, so there is no such evidence. D1's 120 deferred records remain development evidence and were never relabelled as D2 training |
| 7 — enough changeable advisory decisions on that surface | **not closed** | same route, same reason. On *calibration* the candidate changed decisions in every eligible setting, which is encouraging and is not what condition 7 asks for |
| 15 — retrieval usefulness floor, Recall@5 ≥ 0.70 and MRR@10 ≥ 0.50 | **not closed, and forfeited by the null** | `§2.3` closes it only on a new D2 unseen-task holdout, which W7c would have built. The W5 diagnostic on the frozen D1 queries measured *worse* under the wider shortlist, which is a real finding about D1's numbers and closes nothing |

The wider shortlist result deserves stating plainly, because it corrects a D1 conclusion. D1
reported 0.675 recall and 0.4481 MRR for the bounded graph arm with 60 of its comparisons cut
off by the budget and scored 0.0. Widening the shortlist to 20 removed every cutoff and the
scores *fell*, to 0.5875 and 0.3628. The cutoffs had been keeping weak candidates out of the
top ten. D1's number was not wrong, but it was flattered by its own incompleteness, and the
lever D1 named for D2 does not work the way D1 expected.

## What keeps the gate closed, precisely

**One finding, and it is about invariance rather than capacity.** The bounded k-NN reaches
0.9 first-choice against a 0.3 baseline, then reverses at full confidence when identifiers are
renamed and the issue text is reworded without changing any contract. A component that changes
its answer because a variable was renamed has learned the corpus, not the task.

That distinction decides what happens next, and the continuation record says so rather than
leaving it to judgement. `FailureKind.OOD_DEFICIENT` does not authorise a parametric rung,
because a logistic model or a bounded tree fitted on the *same features* faces the same
perturbation. Only `SIGNAL_IS_LINEAR` and `SIGNAL_IS_NON_LINEAR` — findings about capacity —
open S21D2-046. The remedy is an encoder whose features do not move under a rename, and that
is a new pre-registration in a successor sprint, not a rung in this one.

**The sprint nearly missed it.** As first written, the selection rule filtered a setting only
for *producing* a confident OOD error. Four settings recorded zero by abstaining on all ten
probes, still changed decisions on calibration, and survived every other filter. The rule
selected one, and `_failure_kind` classified the resulting failure from column separation
alone as `signal_is_linear` — **which authorises the parametric rung**. A hole in a safety
filter was one step from adding a dependency to this repository. Adding an `ood_answered == 0`
filter and binding the outcome to the failure kind closed it. The verdict was unchanged; the
reason and the branch were not. Recorded as W6-F1.

## What this assessment does not claim

- Not that a learned correction ranker cannot work. It claims that *this* encoder does not
  survive a rename, measured on ten sealed groups.
- Not that the calibration result is a benefit measurement. The primary metric moves in steps
  of 0.1 on ten groups, and no final data was opened.
- Not that retrieval is closed either way. Condition 24's holdout does not exist.
- Not that the correction-ranking surface generalises to any other decision. It is one
  surface, four candidates per task, and `CodingAgentFacade` is explicitly not covered.

## Release state, re-read after the push

Every handle below was read from the remote *after* the tag was pushed, not from the local
repository that created it.

| | |
|---|---|
| `origin/main` | `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` |
| Tag object, local and remote | `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29` |
| Peeled commit | `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5` |
| Implementation PR | `#219`, squash, no bypass |
| PR-head CI | run `30787401395` at `139a149c…`, 30 of 30 success |
| Exact-head `main` CI | run `30788129259` at `ecb5ea12…`, 30 of 30 success |
| Migration head | `0015`; `0016` unallocated |
| Components / approvals / activations | 0 / 0 / 0 |
| development `artifacts` | `7e85d9a6…`, 5 files — unchanged since W0 |
| C3 `artifacts-s21c3` | `7d19e3c8…`, 8503 files — unchanged since W0 |
| D1 `artifacts-s21d1` | `f7b14ac7…`, 83 files — unchanged since W0 |

**Gate L2 remains `does not pass` after the release.** Condition 29 closing does not change
the verdict, and it was never able to: a release condition records that the negative result was
published correctly, not that the result was positive. Sprint 22A stays blocked, and the
handoff at [`sprint-21d3-handoff.md`](sprint-21d3-handoff.md) targets a remediation sprint.

## Limitations carried forward

- Required approving reviews stay disabled because a second eligible reviewer does not exist.
  Carried unchanged from C3 and D1; not worked around, and no approval is fabricated.
- The D2 evidence store holds 480 correction-ranking observations for 240 distinct pieces of
  work, because W4-F2 executed the campaign twice under two sets of run identities. Both
  executions are real and neither was deleted; the dataset selects an explicit 240-member list,
  and the integrity report now warns that two manifests were sealed three times each.
- 214 inherited C3 and D1 outcomes, including the 120 deferred correction-ranking examples,
  remain evaluation-eligible and training-ineligible for the life of the programme.
- `postgres_bootstrap_roles.sh`'s `ALTER ROLE … NOSUPERUSER` abort is unchanged from C1, C2,
  C3 and D1 and belongs to the bootstrap script's owner. S21D2-082 routes around it rather
  than repairing it.
- Migration head stays at `0015`. `0016` was never allocated, because no measured authority
  gap justified one.
