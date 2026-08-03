# Sprint 21D3 handoff — the remediation Sprint 21D2's null requires

Sprint 21D2 built the corpus, ran the campaign, fitted the ranker, and stopped. The bounded
k-NN ranked an accepted candidate first in nine of ten calibration groups against a 0.3
deterministic baseline, then answered confidently and wrongly when identifiers were renamed
and issue text reworded without changing any contract.

**Gate L2 does not pass. Sprint 22A remains blocked.** This handoff targets a remediation
sprint, not Sprint 22A, and nothing here may be read as unblocking it.

Implementation authority for what D2 did:
[Sprint 21D2 Technical Backlog](sprint-21d2-technical-backlog.md). Gate status:
[Gate L2 assessment](gate-l2-assessment.md). Results:
[Sprint 21D2 report](sprint-21d2-report.md). Operating the evidence:
[correction-ranking operations](../../operations/correction-ranking.md).

## 1. Starting point

| | |
| --- | --- |
| Parent tag | `sprint-21d2-evidence-baseline`, annotated — a **negative** release. Tag object `3f3c00e216879b4d1443ca20ac3e5f14c1bc0e29`, identical on the remote |
| Parent release commit | `ecb5ea128c26d49af0661c5e2c3fe5a125f1cec5`, the peeled D2 evidence baseline |
| Parent pull request | `#219`, squash-merged with no administrator bypass under unchanged protection |
| Parent exact-head CI | run `30788129259`, 30 of 30 success on `ecb5ea12…` |
| Grandparent tag | `sprint-21d1-emg-baseline`, tag object `a59977dbcf23df60a700385a6fc15b012bf6d142`, peeled to `b46c2fcd77d568148ce2046f3ec7c4369bd4a8b9` |
| Migration head | `0015`. `0016` still unallocated |
| Component state | 0 components, 0 approvals, 0 activations on `experience.correction_ranking` |
| Gate D1 | conditions 6, 7, 15 **open** — D2 was their remediation route and the null forfeits all three |
| Gate D2 / Gate L2 | **does not pass**, valid negative completion |
| Sprint 22A | **blocked** |

Remote state can change. Reverify the tag object, peeled commit, current `origin/main`, both
exact-head CI runs, branch protection and migration head on day one, and branch from the
verified `origin/main` rather than from the peeled tag, so the gate-close documentation stays
in history.

## 2. The failed condition, stated exactly

Gate L2 condition **20**, at calibration scale, is what stopped the sprint:

> on at least 100 pre-registered OOD/adversarial decisions across at least ten groups, the
> reported false-confident action rate is at most 1%, and promotion satisfies the existing
> stricter contract of exactly zero confident errors

Measured on 10 groups and 40 decisions, submanifest `48d3b766c4dc0104dfe4653e7b808c5c1af6570d9ee9c3cfbf2b8b53082c1381`:

| Grid settings | Outcome |
|---|---|
| 16 | one confident OOD error |
| 4 | two confident OOD errors |
| 4 | **no OOD answer at all** — abstained on all ten probes |
| **0** | eligible |

The continuation record `4e5a690f16b64c22239d9e95f841a1350eeb1ad914694dd496488214a289f321`
records `fail_and_stop` with failure kind `ood_deficient`. The selection record
`274a7a932ce110d12892f3dab102f10308ad556c563483d414979cbc69950536` is a null with
`authorises_final_access: false`.

The probe was verified before the null was accepted: `d2_parsing.parse_csv_row` is answered
correctly at confidence 1.0 unperturbed and wrongly at confidence 1.0 perturbed, and 20 of 40
perturbed variants still execute with unchanged labels. The deficiency is in the ranker.

## 3. What D3 must not do

These are consequences of `§0.4` and `§3.4`, not preferences.

- **Do not reuse D2's calibration OOD set as a selection target.** It has been seen. Tuning an
  encoder against the perturbation that exposed it is the retuning the rule forbids, and it
  would produce a component that passes exactly one probe.
- **Do not relax condition 20.** It is a fixed minimum. So are 8, 10, 13–16, 18, 19 and 24.
- **Do not treat 0.9-against-0.3 as a benefit result.** It is calibration, on ten groups, in
  steps of 0.1, and it is precisely the number that turned out not to survive a rename.
- **Do not open S21D2-046 or -047 on D2's residuals.** `ood_deficient` does not authorise a
  parametric rung: a logistic model or bounded tree on the same features faces the same
  perturbation. Changing the features changes the pre-registration, and that is D3's job, not
  a rung inside D2.
- **Do not train on any `REAL_GOVERNED_RUN` observation.** All 214 inherited C3 and D1
  outcomes, including the 120 deferred correction-ranking examples, are evaluation-eligible and
  training-ineligible for the life of the programme.
- **Do not reinterpret correction ranking as a universal domain model**, and do not claim
  `CodingAgentFacade` coverage. It is one surface, four candidates per task.

## 4. What D3 requires

### A new pre-registration revision

Revision 2 is frozen and D2 did **not** spend the single pre-final revision `§3.4` permits.
That is deliberate: the residual is a finding about the encoder's invariance, and revising
features after seeing the perturbation that broke them is retuning. D3 opens with revision 3,
written before any new measurement, and it must name what changed in the feature contract and
why.

### A new, untouched holdout

`§0.4` requires it after a failed comparison, and `§2.3` requires it independently for D1
condition 15. Two distinct holdouts are needed and must not be the same set:

| Holdout | For | Minimum |
|---|---|---|
| correction-ranking final A and B | Gate L2 conditions 10–16 | ≥100 verifier-backed `REAL_GOVERNED_RUN` outcomes over ≥25 groups, each batch |
| retrieval unseen-task | D1 condition 15 | ≥50 new queries, per `§2.3` |

D2's 125 sealed groups are **spent for training and calibration** — 60 of them carry outcomes.
The remaining 65 are sealed and unexecuted; whether they are enough for a final holdout is a
count D3 must do, not assume.

### An encoder whose features do not move under a rename

This is the actual technical problem. The eleven columns are diff shape, statement-graph
structure, AST size, a frozen-MiniLM cosine over requirement and delta text, a missing-value
indicator and declared capabilities. The cosine channel is the obvious suspect — MiniLM
embeddings of renamed identifiers are not the same embeddings — but it is a suspect, not a
diagnosis, and D3 should measure per-channel invariance before changing anything.

A useful first probe, cheap and decisive: hold the ranker fixed, perturb one channel at a
time, and record which channels move. If the structural channels are stable and only the
lexical one moves, the fix is a normalisation D3 can pre-register. If the structural channels
move too, the feature set is the wrong shape and the pre-registration has more to say.

## 5. What D2 leaves that works

Reusable without re-litigation. Every item below is tested and released.

| Component | What it gives D3 |
|---|---|
| `reality_task_specs_d2` — 95 templates, 380 candidates | 95 new disjoint groups, executed and near-clone-checked. Six families, oracle-free recipes at 0.57/0.53/0.52/0.39 |
| `correction_catalogue` | 125 sealed groups, 500 slots, ten pairwise-disjoint partitions, `outcomes_present: false` at seal |
| `correction_features` + `seal_feature_records` | pre-outcome sealing. The projector refuses an outcome that predates its own seal, so chronology is a wall-clock fact rather than a promise |
| `CorrectionRankingObservationProjector` | role bound by the sealed partition; refuses to take a surface, provenance class or source kind as an argument |
| `correction_matrix` | eight leakage scans, each with a seeded-violation test, including a seeded oracle and a seeded identity column |
| `correction_ladder` | derived baseline that refuses a record naming a weaker rung; learned rungs excluded by `kind`, not by name |
| `knn_calibration` | the declared grid, the selection rule **with W6-F1's fix**, and `FailureKind.authorises_parametric_continuation` |
| `calibration_ood` | semantics-preserving perturbations with labels obtained by *executing* the perturbed hidden suites |
| `correction_integrity` | eight integrity classes with the `not_opened` state, bound to a stop hash and refusing an unbound claim |
| `scripts/operations_d2.py` | backup, restart, restore, ten-case damage matrix |
| `scripts/verification_matrix.py --sprint 21D2` | 29-row release matrix with not-opened rows carrying their stop hash |

### The selection rule's fix is the part to read first

As first written the rule filtered a setting only for *producing* a confident OOD error, so a
setting that answered nothing passed by silence. It selected one, and the failure was then
classified from column separation alone as `signal_is_linear` — which authorises a parametric
rung and a new dependency. `ood_answered == 0` now disqualifies, and the continuation outcome
is bound to the failure kind. If D3 adds a filter, it should ask the same question of it:
*can this be satisfied by refusing to answer?*

## 6. Known state D3 inherits

- **480 observations for 240 pieces of work.** W4-F2 executed the campaign twice under two
  sets of run identities. Both are real, neither was deleted, and the dataset selects an
  explicit 240-member list. The integrity report warns that two manifests carry three seals
  each. A D3 dataset built from "every row on this surface" would silently span executions.
- **Three seals per partition** in the D2 store, at 05:26, 05:32 and 05:49 on 2026-08-02. Only
  the middle one is named by the campaign evidence; all three are real and the chronology check
  needs all of them.
- **Migration head `0015`.** `0016` unallocated. D2 measured no authority gap that justified
  one; D3 should not allocate it without measuring one either.
- **Required approving reviews disabled** — a second eligible reviewer does not exist. Carried
  from C3, D1 and D2 unchanged, never worked around, and no approval fabricated.
- **`postgres_bootstrap_roles.sh`'s `ALTER ROLE … NOSUPERUSER` abort** is unchanged since C1
  and belongs to its owner. `scripts/postgres_provision_evidence.sh` routes around it.
- **Shell scripts need `COGOS_POSTGRES_ENV_FILE`.** Exporting the sprint environment is not
  enough; W9-F1 cost a wasted backup and a false migration failure before this was written
  down. See [correction-ranking operations](../../operations/correction-ranking.md).

## 7. Retrieval, and a D1 number that changed

D1 reported 0.675 Recall@5 and 0.4481 MRR@10 for the bounded graph arm, with **60** of its
comparisons cut off by the budget and scored 0.0. Under resource policy revision 2 the
shortlist widens to 20, the cutoffs go to **0**, and the scores *fall* to 0.5875 and 0.3628.
The cutoffs had been keeping weak candidates out of the top ten.

D1 named the shortlist width as D2's first lever. It is not the lever D1 thought it was. D3
should treat retrieval as an open question with a corrected starting point, not as a nearly
solved one, and D1 condition 15 still closes only on a new unseen-task holdout.

## 8. Exit criteria for D3

D3 completes — positively or negatively — when:

- pre-registration revision 3 is published before any new measurement, naming the feature
  change and its justification;
- per-channel invariance under semantics-preserving perturbation is measured and recorded,
  whatever it shows;
- a new untouched holdout exists and is hash-bound before any candidate is selected;
- either every Gate L2 condition is met and a bounded, reversible, operator-approved
  activation follows, or a complete negative release records the first failed pre-registered
  stop condition, immutably, with a not-opened record for every dependent task.

A green implementation PR without one of those two releases is a checkpoint, not a completed
sprint.
