# Sprint 21D2 — Useful Learned Correction Ranking

- Gate D2 / Gate L2: **does not pass** — a valid negative completion under `§0.4` and `§11.3`
- Gate D1 conditions 6, 7, 15: **remain open**, and the null forfeits all three
- Release: `sprint-21d2-evidence-baseline`
- Parent baseline: `sprint-21d1-emg-baseline` → `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9`
- Migration head: `0015`, unchanged. `0016` never allocated.
- Assessment: [gate-l2-assessment.md](gate-l2-assessment.md)

## 1. What the sprint set out to do, and what it found

Sprint 21D1 ended with no learnable surface on frozen Sprint 21C3 evidence. D2's premise was
that the missing ingredient was *the evidence*, not the idea: build a corpus the system can
generate outcomes for by itself, fit a bounded ranker on its own verified self-play, and see
whether ordering the candidate repairs for a failing task is something a learned component can
usefully do.

The corpus worked. 125 disjoint repository groups, 95 of them written for this sprint, 500
candidate slots, every baseline and every variant *executed* rather than declared. 240
verifier-decided self-play outcomes at exactly the pre-registered floor.

The ranker found the signal. Against a deterministic baseline that ranks an accepted candidate
first in **3 of 10** calibration groups, the bounded k-NN reaches **9 of 10**.

Then it fell over on a rename. The same tasks, with every identifier in the visible module
renamed and the issue text reworded so that no contract changed, produced confident and wrong
answers. Twenty of the twenty-four pre-registered settings made at least one such error. The
other four made none because they answered nothing — they abstained on all ten probes.

A component that changes its answer because a variable was renamed has learned the corpus, not
the task. No candidate was selected, no artifact was written, the final holdout was never
opened, and Gate L2 does not pass.

## 2. Denominators

Nothing below is a rate without the numbers under it.

| Quantity | Exact | Floor |
|---|---|---|
| Repository groups sealed | 125 | 125 |
| Groups authored for D2 | 95 | 95 |
| Groups inherited from C3 | 30 | — |
| Candidate slots sealed | 500 | — |
| Training observations, `SELF_PLAY` | 200 over 50 groups | 200 / 50 |
| Calibration observations, `SELF_PLAY` | 40 over 10 groups | 40 / 10 |
| `REAL_GOVERNED_RUN` observations fitted on | **0** | 0 |
| Fitted matrix | 240 rows, 11 columns, 60 groups | — |
| Calibration first-choice denominator | 10 groups | — |
| OOD probe | 10 groups, 40 decisions | — |
| Grid settings swept | 24, all recorded | — |
| Eligible settings after the rule | **0** | — |
| Final batch A / B outcomes | **not opened** | 100 each |
| Canary decisions | **not opened** | 5 |

Acceptance was 0.5000 in both partitions — 100 hidden-passed and 100 hidden-failed in
training, 20 and 20 in calibration. That balance is a property of the corpus design, not a
result: each task carries two correct and two incomplete variants.

## 3. The corpus, and the oracle that had to be removed first

C3's four candidate recipes were named `correct_narrow`, `correct_robust`, `incomplete_a`,
`incomplete_b`, with per-recipe repair rates of 1.0 / 1.0 / 0.0 / 0.0. The recipe *was* the
label. A ranker given that field would have scored perfectly and learned nothing, and D1's 120
deferred correction-ranking examples are exactly the shape that oracle produces — 120 of 120
predictable from the recipe name alone.

D2 replaced the recipe family with four neutral names bound per task by a permutation derived
from the template id. Measured repair rates: **0.57 / 0.53 / 0.52 / 0.39**. The oracle is
gone, and it is the per-task *binding* rather than the neutral naming that removed it — a
neutral name with a fixed binding would have been the same oracle wearing a disguise.

Distinctness was checked by execution and by a near-clone detector over normalised ASTs and
canonicalised token streams: **0** colliding variant pairs inside the corpus, **0** D2
candidates colliding with any C3 candidate, **0** template-id collisions. Three of the ten
authoring defects were a D2 task restating a C3 one — `last_n` = `take_last`, `parse_ipv4` =
`parse_version`, `apply_defaults` = `merge_settings` — and all three are invisible to a
baseline-against-baseline comparison. Widening the check to every D2 variant against every C3
*candidate* is what found them.

**The cost projection was wrong, and the correction matters more than the number.** The
`P-CLONE` probe measured a 40% first-pass defect rate on ten templates, and the wave plan
extrapolated about 34 further defect-and-repair cycles across the remaining 85. The measured
figure was **6 in 85 — 7%**, roughly a sixth of the projection. The probe measured authoring
*without the rules*, and the four defects it found were what taught them. Extrapolating a
first-attempt rate past the point where its lesson lands overstates the remaining work. The
probe was still worth running; it bought knowledge, not a forecast.

## 4. Pre-outcome features, and why chronology is a wall-clock fact

Every feature is encoded and hash-bound into one sealed artifact **before the first container
starts**. `CorrectionRankingObservationProjector` refuses an outcome that predates its own
seal, so "the features are pre-outcome" is not a claim about discipline — a violation cannot
be recorded.

The eleven columns are diff shape, statement-graph structure, AST size, a frozen-MiniLM cosine
between the requirement text and the candidate delta, a missing-value indicator and the
declared verifier capabilities. Eight scans over the fitted matrix, all clean: no forbidden
field, every feature record preceding its outcome, every row resolving to one pre-outcome
source chain, no group crossing the split, no identical row carrying two labels, no near
duplicate crossing the split (maximum cross-split similarity 0.978 against a 0.999 floor), and
no column deriving the label on either split. A seeded oracle column and a seeded identity
column are both refused, by test.

## 5. The ladder, and a rung that was recorded ineligible rather than scored zero

| Rung | Kind | First-choice rate |
|---|---|---|
| `fixed_input_order` | deterministic | **0.3** |
| `deterministic_static_ordering` | deterministic | 0.1 |
| `lexical_similarity` | deterministic | 0.3 |
| `frozen_minilm_cosine` | deterministic | 0.3 |
| `width_20_bounded_graph` | deterministic | **ineligible, with its reason** |
| bounded cosine k-NN | learned | 0.9 at 0.9 coverage, k=3 |

The baseline is *derived* by the contract — `strongest_non_learned_rung_on_the_calibration_ladder`
— and the record refuses to name a weaker rung or understate its rate. A learned rung is
excluded by `kind`, not by name, so renaming one changes nothing.

`width_20_bounded_graph` is ineligible because a correction task presents exactly four
candidates: a twenty-wide shortlist is the entire pool, and the rung reduces to its own
tie-break. Recording it as 0.0 would have been a straw man that made every other rung look
better.

## 6. Calibration, and the check that was nearly skipped rather than passed

The grid was declared before any number existed: k ∈ {3,5,7}, similarity floor ∈ {0.30, 0.50},
agreement floor ∈ {0.60, 0.80}, confidence floor ∈ {0.55, 0.70}, embedding weight frozen at
0.7. Twenty-four settings, grid identity `c0abae23…`.

Every one is in the record with the reason it was filtered:

| Reason | Settings |
|---|---|
| 1 confident OOD error against a contract allowing 0 | 16 |
| 2 confident OOD errors | 4 |
| answered no OOD probe at all | 4 |
| **eligible** | **0** |

**W6-F1 — the hole in the safety filter, found by running the rule.** As first written, the
rule filtered a setting only for *producing* a confident OOD error. The four settings that
abstained on all ten probes recorded zero errors, still changed decisions on calibration, and
survived every other filter. The rule selected one of them — scoring exactly the baseline 0.3
— and `_failure_kind` classified the resulting failure from column separation alone (0.8213)
as `signal_is_linear`, **which authorises the parametric rung**. A hole in a safety filter was
one step from adding a dependency to this repository.

The fix was an `ood_answered == 0` filter, a `FailureKind.authorises_parametric_continuation`
property, and binding the continuation outcome to the failure kind. The verdict did not
change. The reason and the branch did.

**The probe was verified before the null was trusted.** `d2_parsing.parse_csv_row` is answered
correctly at confidence 1.0 unperturbed and wrongly at confidence 1.0 perturbed;
`ood_accepted_variants: 20 of 40` confirms the perturbed packages still execute and still
carry the same labels. The deficiency is in the ranker, not in the probe.

## 7. Why no later rung was opened

`§3.3` opens S21D2-046 only on residual evidence that authorises parametric continuation. The
recorded failure kind is `ood_deficient`, an invariance problem rather than a capacity one: a
logistic model or a bounded tree fitted on **the same features** faces the same perturbation.
Only `SIGNAL_IS_LINEAR` and `SIGNAL_IS_NON_LINEAR` open it.

This mattered practically. `sklearn` already imports transitively through
`sentence-transformers`, so the rung could have been built without anyone noticing a dependency
had been added. It was not, and no code path imports it. `git diff origin/main...HEAD --
uv.lock pyproject.toml` is empty.

S21D2-047 is unreachable because 046 never opened. S21D2-048 — the single pre-final
pre-registration revision `§3.4` permits inside D2 — **was not spent**. The residual that would
motivate one is a finding about the encoder's invariance, and revising features to survive a
perturbation after seeing the perturbation is the retuning the rule exists to prevent.

## 8. Retrieval — a D1 number corrected, and a condition not closed

S21D2-030 widened the graph shortlist from 10 to 20 and S21D2-031 froze resource policy
revision 2 (`d0e8520e…`). Re-measuring D1's frozen 80-query set under it:

| Arm | Recall@5 | MRR@10 | nDCG@10 | Timeouts |
|---|---|---|---|---|
| bounded graph, width 10 (D1's number) | 0.6750 | 0.4481 | 0.3438 | **60** |
| bounded graph, width 20 | **0.5875** | **0.3628** | **0.2327** | **0** |
| `minilm_vector` | 0.6750 | 0.4392 | 0.3740 | 0 |
| lexical | 0.5250 | 0.4145 | 0.3327 | 0 |

**The wider shortlist measured worse, and the explanation is the timeouts.** Revision 1 could
not fit ten pairs at 250 ms into a 2 s budget, cut 60 comparisons and scored them 0.0 — which
accidentally kept weak candidates out of the top ten. D1's number was flattered by its own
incompleteness. The lever D1 named for D2 does not work the way D1 expected.

This is development-only evidence and closes nothing: `§2.3` closes D1 condition 15 only on a
**new D2 unseen-task holdout**, which W7c would have built and the null closed. The D1
evidence file was not modified; this is a second measurement that supersedes nothing.

## 9. Operations

| Proof | Result |
|---|---|
| Backup, container restart, restore into an isolated database | counts, a digest over every hashed row, all **1511** artifact blobs re-hashed out of the archive, and every store-side input to `plan_resume_with_receipts` identical between source and restore |
| Negative-release state after restore | 0 components, 0 revisions, 0 evidence records, 0 approvals, 0 activations — asserted, not assumed |
| Corruption and isolation matrix | **10 of 10** cases fail closed |
| Release verification matrix | **29 of 29** rows on expected exit status, 812 s, none failed, none skipped |
| Artifact pairs across every destructive row | development, C3, D1 and D2 all byte-identical before and after |
| Integrity report | eight classes; six measured clean, two `not_opened` and bound to the selection hash |

Two damage cases moved under measurement and are recorded as what happened rather than as what
was aimed at. A poisoned feature record never reaches the seal check at all — the contract
re-seals on load and refuses the bytes, which is a stronger refusal than the one the case was
written to demonstrate. That left the seal-hash check unexercised, so a second case covers the
attack poisoning cannot mount: a *valid* seal from another execution served under the declared
artifact identity, which only the independently recorded hash catches.

## 10. Findings

| ID | Finding |
|---|---|
| W4-F1 | `RealityCampaignSequenceRecorded` was declared *below* `CODING_EVENT_MODELS`, so the default catalog never registered it and a real Event Store refused the campaign receipt. W2 and W3c had only exercised the sequencer against an in-memory double. |
| W4-F2 | The first resume re-executed all 300 containers while reporting a resume: `prepare_task` minted a fresh control bundle, the manifest names its bundle by artifact id, and the run identity hashes the manifest. Bundle ids are now recorded per partition and passed back. |
| W4-F3 | With F2 fixed, the resume re-sealed features with a fresh clock, so every replayed outcome preceded its own feature record and the projector correctly refused every projection. The recorded seal time is now carried across the resume and the re-encoded set must reproduce the recorded hash. |
| W5-F1 | The wider shortlist measured worse. See §8. |
| W6-F1 | The selection rule could be satisfied by silence. See §6. |
| W9-F1 | D2 had no operations document, so nothing stated that the shell scripts need `COGOS_POSTGRES_ENV_FILE`. The first backup dumped the *development* database; the matrix's `postgres_migration_check.sh` reported a true failure about the wrong store. First attributed to a defect in `postgres_common.sh` — wrong: the override is deliberate and documented, and C3 and D1 both document the correct form. What D2 lacked was the document. S21D2-090 supplies it. |

## 11. Deviations

**W4-D1 — 480 observations for 240 pieces of work.** A consequence of W4-F2: the same 240
candidates were executed twice under two sets of run identities. Both executions are real —
every row resolves to bytes and to an event — and **neither was deleted**. The training
snapshot selects an explicit 240-member list rather than whatever the store holds, so the
dataset is exactly 240 regardless. Erasing rows to make a total look round is what turns
evidence into a claim.

The S21D2-081 integrity report now surfaces this as a warning rather than leaving it in a
deviation note: two campaign manifests carry three seals each, so a dataset built from "every
row on this surface" would silently span more than one execution.

**S21D2-081 landed in W9, not W2.** The wave plan recorded it as delivered with `-080` and
`085a`; it is not in the W2 commit `c3ceb23`, and S21D2-083 depends on it. The plan is
corrected rather than the claim dropped.

## 12. Limitations

- The primary calibration metric moves in steps of 0.1 on ten groups. 0.9 versus 0.3 is a
  large gap at a coarse resolution, and no final data exists to refine it.
- Fitted only on self-play. No real governed run entered any snapshot, by construction.
- The OOD probe is 40 decisions over 10 groups — calibration scale. Condition 20's 100
  decisions over 10 groups were never authorised.
- Group disjointness is proven over the partitions that exist. Final and canary were never
  populated, so the guarantee is untested against roles that do not exist.
- 214 inherited C3 and D1 outcomes, including the 120 deferred examples, stay evaluation-only
  for the life of the programme.
- Required approving reviews remain disabled: a second eligible reviewer does not exist. No
  approval was fabricated.
- `postgres_bootstrap_roles.sh`'s `ALTER ROLE … NOSUPERUSER` abort is unchanged since C1 and
  belongs to its owner; S21D2-082 routes around it.
- Correction ranking is one surface with four candidates per task. It is not a universal
  domain model, and `CodingAgentFacade` is not claimed as covered.

## 13. Inherited stores, unchanged

| Pair | Fingerprint | Files |
|---|---|---|
| development `artifacts` | `7e85d9a69d1db2f07c3772fcba26d50c5bb31ca558f81930da07a5feb1982dcf` | 5 |
| C3 `artifacts-s21c3` | `7d19e3c8e45455296520eb8b6edf524d2454d6f5e07a432b751939eb23dfe593` | 8503 |
| D1 `artifacts-s21d1` | `f7b14ac7a66508c5ad41f8f310a02544d1dc8e1d513dcc5bbdab82106cfbf30f` | 83 |

Identical at W0 provisioning and after the W9 destructive matrix. Zero writes to any of them.
The D1 erratum records discrepancies against the D1 release **as published**, without touching
the protected tag or its chronology.

## 14. Release

`sprint-21d2-evidence-baseline`. The success tag `sprint-21-learning-baseline` is forbidden on
this path and was not created. Sprint 22A remains blocked; the handoff targets a remediation
sprint.

Exact merge, CI and tag handles are recorded in
[gate-l2-assessment.md](gate-l2-assessment.md) condition 29 and in
[`sprint-21d2-release.json`](evidence/sprint-21d2-release.json), and are deliberately not
restated here: this report is inside the release it would be citing, so a claim about that
release made in this file would be self-referential. Read them from the assessment, which was
updated after the push from the remote rather than from the repository that created it.

## 15. What this sprint is worth

A negative result that took the full corpus, the full campaign and the full selection
machinery to produce is more expensive than a positive one and more useful than a guess. Three
things outlive it:

**The corpus.** 125 disjoint groups with an oracle-free recipe family, executed rather than
declared, reusable by any successor.

**The chronology guarantee.** Pre-outcome sealing makes "the features came first" a fact about
a clock rather than a promise about process, and it caught W4-F3 by refusing every projection
rather than by anyone noticing.

**The measurement that says no.** A rule that can be satisfied by silence would have selected
a component that reverses under a rename, and classified the failure as one that authorises
adding a dependency. It was found by running the rule against real numbers, not by reading it.
That is the sprint's most valuable output, and it is the reason the gate is closed rather than
the reason it is disappointing.
