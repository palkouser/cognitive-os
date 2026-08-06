# Gate L2 assessment — Invariant Correction Ranking (Sprint 21D3)

- Sprint: 21D3
- Assessed: 2026-08-05
- Branch: `feature/sprint-21d3-invariant-correction-ranking`
- Parent baseline: `sprint-21d2-evidence-baseline`, tag object
  `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`, peeled to
  `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5`
- Migration head: `0015`, unchanged. `0016` remains unallocated.
- Revision: 3 — **final**. Condition 29 closed on the protected merge of `#221`, its exact-head
  post-merge `main` CI run `31072527026` (30 of 30 success on
  `ef4388b1bf9cb842b25a06aa2255abd1042702c2`), and remote verification of the annotated tag
  `sprint-21d3-evidence-baseline`, object `bcf2976dd0f063b1eb4ea16b388eea590e6172dd`.
- Machine-readable form: [`sprint-21d3-gate-l2.json`](evidence/sprint-21d3-gate-l2.json),
  integrity `e16c07d3b8ecbdd9…`
- Release record: [`sprint-21d3-release.json`](evidence/sprint-21d3-release.json)

This document does **not** replace [`gate-l2-assessment.md`](gate-l2-assessment.md), which is
Sprint 21D2's historical assessment and stays exactly as it was written.

## Verdict

**Gate L2 does not pass.**

Twenty-nine conditions. **Sixteen are met**, one is met as a rejection, twelve are **not
opened**, and **none failed**.

The gate does not pass on met conditions. It passes only when *every applicable* condition is
met, and twelve were never authorised to be measured — the outcome §0.4 and §11.3 define as a
valid negative completion rather than a shortfall.

D3 stopped twice, on two independent branches, and both stops are recorded with their own hash.

**The correction branch stopped at S21D3-039** with a null candidate selection, hash
`68ea06843d2136e3…`. All twenty-four frozen k-NN settings were
measured. The intervention worked on the question it was designed for and failed on a different
one: action preservation is **1.00 for every setting** across all six transformation cases,
equivalence coverage never falls below clean coverage, and the strongest setting reaches **0.65**
clean first-choice against a **0.5** deterministic baseline. But every setting that answers is
confidently wrong on some semantics-preserving case — 12 to 36 confident errors of 120 decisions
— and the contract allows exactly zero. The residual is one of **capacity, not invariance**: the
alpha-normalised source encoding is exactly invariant, and what remains is absolute ranking
accuracy that 0.65 cannot turn into a zero-confident-error metamorphic set.

**The retrieval branch stopped at S21D3-045** with a negative result, hash
`f0b5391205522366…`. Sixty unseen queries, floor fifty. No arm cleared
either floor:

| Arm | Recall@5 | MRR@10 |
|---|---|---|
| `no_memory` | 0.0000 | 0.0000 |
| `exact_signature` | 0.0000 | 0.0000 |
| `lexical` | 0.4833 | 0.3042 |
| `minilm_vector` | 0.5333 | 0.3414 |
| `minilm_shortlist_plus_bounded_ged` | 0.5000 | 0.3073 |
| `reciprocal_rank_fusion` | 0.5000 | 0.3004 |
| *chance baseline* | *0.5768* | *0.3317* |
| **floor** | **0.7000** | **0.5000** |

The cause is recorded rather than guessed: all sixty candidates share one searchable body once
domain and task signature are removed, so the lexical arm's ranking is the pair-id tie-break for
all sixty queries. D1 hit the same ceiling.

So no candidate was selected, no artifact was fitted, no final or canary body was opened, and
nothing was registered, approved or activated. Every dependent E05, E06 and E07 task carries a
typed not-opened record bound to the selection stop.

**Gate D1 conditions 6, 7 and 15 remain open.** D3 was condition 15's remediation route and the
holdout closed no floor; conditions 6 and 7 need final and canary outcomes that were never
authorised.

## The twenty-nine conditions

Every row names the file and the rule that decided it. No condition is asserted — the table is
generated from the frozen manifest and the produced evidence by
[`scripts/gate_assessment_d3.py`](../../../scripts/gate_assessment_d3.py), and a condition with
no bearing evidence is `not opened` bound to its stop hash, never `met`.

| # | Condition | State | Decided by |
|---|---|---|---|
| 1 | current baseline and exact predecessor release | **met** | the branch descends from the frozen baseline and the D2 release is re-read (sprint-21d3-baseline.json) |
| 2 | immutable predecessor stores and negative D2 release | **met** | all four predecessor store fingerprints reproduce (sprint-21d3-baseline.json) |
| 3 | unit and retrieval reconciliation | **met** | the D2 denominator and retrieval reconciliation is published and immutable (sprint-21d3-d2-reconciliation.json) |
| 4 | revision-3 pre-registration chronology | **met** | zero D3 measurements precede publication (sprint-21d3-pre-registration.json) |
| 5 | verifier remains label and acceptance authority | **met** | the mandatory decision is identical under every fallback configuration, and only a bounded campaign configuration reorders (sprint-21d3-runtime-invariance.json) |
| 6 | v2 fitted matrix contains no forbidden field | **met** | the fitted matrix scans all 390 v2 columns and carries no forbidden field (sprint-21d3-vertical-slice.json) |
| 7 | transitive groups never cross roles | **met** | zero groups cross a role and no near clone survives (sprint-21d3-separation.json) |
| 8 | minimum fit and calibration counts | **met** | 200 fitting outcomes over 50 groups and 80 calibration over 20 (sprint-21d3-self-play-campaign.json) |
| 9 | zero real governed runs in fit or calibration | **met** | zero real governed runs entered fitting or calibration (sprint-21d3-self-play-campaign.json) |
| 10 | two exact independent final batches | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 11 | holdout inaccessible and candidate selected before access | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 12 | strongest deterministic baseline and revised k-NN first | **met** | every attempted rung is retained on the ladder and every frozen setting measured (sprint-21d3-learner-selection.json) |
| 13 | at least twenty changed final group decisions | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 14 | absolute or relative benefit floor | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 15 | paired group bootstrap lower bound above zero | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 16 | positive direction in final A and final B | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 17 | unit-correct operational denominators | **met** | ranking decisions and candidate outcomes are counted apart (sprint-21d3-calibration-metamorphic.json) |
| 18 | zero accepted safety or governance regressions | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 19 | retention floors by domain and aggregate | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 20 | one hundred promotion metamorphic decisions with safety ceiling | **met** | at least 100 ranking decisions over at least 10 groups (sprint-21d3-calibration-metamorphic.json) |
| 21 | shadow executes no changed decision | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 22 | canonical inert JSON artifact with complete lineage | **met** | the artifact is canonical JSON and every unsafe or wrong-schema load refuses (sprint-21d3-runtime-invariance.json) |
| 23 | structured deterministic fallback on every failure | **met** | every runtime reason code is reachable and each falls back deterministically (sprint-21d3-runtime-invariance.json) |
| 24 | new retrieval holdout clears recall and MRR floors | **met as rejection** | the floors were measured on 60 unseen queries and no arm cleared them; the first failed floor is recall_at_5 (sprint-21d3-retrieval-holdout-result.json) |
| 25 | hash-bound canary with verifier and kill switch | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 26 | restart-safe lifecycle, disable, restore and rollback | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 27 | exact human approval authority and no self-approval | **not opened** | closed by the selection stop before it could be measured (S21D3-039 null candidate selection) |
| 28 | isolated recovery and complete validation matrix | **met** | every required isolated and repository check ran and passed, none skipped (sprint-21d3-verification-matrix.json) |
| 29 | protected release, exact-head CI, documents and verified tag | **met** | the protected merge, its exact-head post-merge main CI and the remote tag agree (sprint-21d3-release.json) |

## Gate D1's three open conditions

| # | Closure rule | State | Why |
|---|---|---|---|
| 6 | at least 200 unique eligible verifier-backed primary-surface outcomes | **not opened** | closed by the selection stop: the outcomes that would close it are final and canary outcomes, which were never authorised |
| 7 | at least 20 primary-surface examples change advisory action | **not opened** | closed by the selection stop: the outcomes that would close it are final and canary outcomes, which were never authorised |
| 15 | new unseen-task retrieval holdout independently clears both floors | **not opened** | D3 was condition 15's remediation route. The holdout was executed once on 60 unseen queries and no arm cleared either floor, so the condition remains_open |

## The release, and what closed condition 29

Condition 29 was the only condition still moving when this assessment was first written. It is
now closed on evidence rather than on assertion. PR `#221` merged into protected `main` by
squash at `2026-08-06T04:53:46Z` with no administrator bypass and no protection change; the
exact-head post-merge `main` CI run `31072527026` completed `success`, 30 of 30 jobs, on
`ef4388b1bf9cb842b25a06aa2255abd1042702c2` at `05:08:59Z`; and the annotated tag was created
once, afterwards, at `05:27:44Z`, and verified against the remote. Branch protection is
byte-identical to the W0 reading — 27 strict contexts, `enforce_admins`, conversation
resolution, no force-push, no deletion, no approving-review requirement. All four predecessor
Artifact Store pairs reproduce their W0 fingerprints after the release.

`scripts/gate_assessment_d3.py` gained no ability to assert this. It gained one bearing that
reads [`sprint-21d3-release.json`](evidence/sprint-21d3-release.json) and compares the merge
commit, the peeled commit, remote `main` and the CI head to each other, the CI conclusion to
`success`, and the local tag object to the remote one. The bearing exists only when that record
exists, so a pre-release run still reports condition 29 as `not opened` rather than as failed.

Because conditions 1 through 28 do not all pass, the permitted tag is
`sprint-21d3-evidence-baseline`. The success tag `sprint-21-learning-baseline` is **not**
created by this sprint, and its absence is itself part of what S21D3-095 asserts.

## What this sprint does not claim

- No universal model claim. The k-NN was measured on one surface, on authored tasks, with a
  frozen encoder, and it was not selected.
- No benefit claim. The 0.65 clean first-choice figure is a **calibration** measurement. It is
  not a final-batch benefit and is never described as one; the final batches were never opened.
- No retrieval capability claim. Every arm sits at or below chance on the holdout, including
  the fixed RRF arm that reached 0.7750/0.4478 on the development set.
- No statement that Sprint 22A is unblocked. It is not.
