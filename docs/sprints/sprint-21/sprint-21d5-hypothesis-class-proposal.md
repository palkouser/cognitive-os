# Sprint 21D5 proposal — the hypothesis class, named on the residual

- Status: groundwork for the successor experiment the [D5 handoff](sprint-21d5-handoff.md)
  bounds. **Nothing here unblocks Sprint 22A**, re-decides a D4 stop, or reads any spent
  evidence for a new decision.
- Evidence: [`sprint-21d5-hypothesis-class-diagnostic.json`](evidence/sprint-21d5-hypothesis-class-diagnostic.json),
  produced by `scripts/hypothesis_class_diagnostic_d5.py` from the sealed D4 feature seals
  and campaign labels.
- Authorisation: handoff §2 — the spent calibration set "remain[s] valid *fitting* and
  *diagnostic* evidence"; handoff §3 — "no new corpus is needed to test whether a different
  class has a zero-error region". Both sentences are exercised here and neither is exceeded:
  no selection was made, no threshold was derived for reuse, no final, batch-B or canary
  body was opened, and the retrieval holdout result was not read.

## 1. The class

**`pairwise-contrastive-linear-v1`** — `src/cognitive_os/learning/pairwise_contrastive.py`.
One linear direction, fitted by ridge-regularised logistic regression on every within-group
accepted-minus-rejected difference of sealed v2 feature vectors. Candidates rank by their
projection; the decision's confidence is the **margin** between the top two projections;
ties keep the frozen baseline order; below a margin floor the ranker abstains. No new
encoder, channel, embedding or dependency; fitting uses numpy from the `semantic-graph`
extra, inference is pure Python.

The handoff requires the class to be implied by the residual rather than picked from a
menu, so the implication is stated once: D4 measured that the frozen k-NN ranks above the
strongest deterministic baseline everywhere and separates its own errors nowhere — zero-error
coverage exactly zero at both volumes. Its confidence is the top candidate's absolute
neighbourhood acceptance mass, and among four deliberate near-clones that mass barely moves
between a right ordering and a wrong one. The failing quantity is within-group contrast, so
the class fits within-group contrast and confides only in it.

## 2. What the diagnostic measured

All numbers are in the sealed evidence record, over the 100 independent spent calibration
decisions, against the unchanged §2.3 floors (zero confident errors, coverage ≥ 0.40,
≥ 20 projected changed final decisions, first choice above the 0.52 baseline).

| estimate | fitted pool | first-choice rate | zero-error coverage |
|---|---|---:|---:|
| frozen k-NN, best of 144 cells (S21D4-039) | 80 groups | 0.735 over admitted | **0.0000** |
| this class, disjoint pool | 80 fitting groups | 0.79 over all | **0.22** |
| this class, combined-pool leave-group-out | 179 spent groups | 0.84 over all | **0.32** |

Three readings, in decreasing order of certainty:

1. **The class answers the residual.** The k-NN's zero-error region is empty; this class
   has a non-empty one on every estimate, with the margin ordering error-free through its
   top 30 decisions on the hardest estimate. The `hypothesis_class_bound` stop named the
   right bound.
2. **Volume helps this class where it measurably did not help the k-NN**: 0.22 at an
   80-group pool against 0.32 at 179-group pools, on the same authored distribution.
3. **0.32 is below 0.40.** The floor is not met on the spent estimate and the gap is one
   deep error. Whether a fresh certification clears 0.40 is exactly what D5's read-once
   measurement decides; this record makes the bet quantified rather than hopeful.

## 3. The retrieval half

The D4 surface reached 41 of 60 candidates; ten repairs in pure arithmetic produce no
identifier terms under the released extraction, and an empty document cannot be found by
any arm. `search_terms_from_source(..., structure_fallback=True)` — off by default, so
every released call site keeps its recorded bytes — gives a source whose identifier terms
come up empty its lowercased AST node-type terms from the same canonical dump, minus the
bookkeeping nodes every dump carries. Measured on the released corpus definitions: 26 of
120 graph sides are empty under the released extraction, 0 remain empty under the
fallback, and the ten previously term-less repaired-side documents are pairwise distinct.
Whether a complete surface closes the 0.0089 MRR@10 gap is a fresh-holdout measurement and
is left open.

## 4. What a D5 must still do, in order

1. **Pre-register** revision 5: this class by name, λ = 1 (chosen on fitting-pool-internal
   leave-group-out evidence, recorded before any fresh number), the margin as the
   confidence, the unchanged §2.3 floors and §3.3-style decision tree, the combined spent
   pool (80 + 100 groups) as fitting evidence, and the widened-surface flag for the
   retrieval branch.
2. **Author** a fresh 100-group calibration corpus and a fresh 60-group retrieval holdout
   under the D4 corpus contract, group-, clone- and source-disjoint from every spent role.
3. **Measure once**: derive the zero-error operating point on the fresh calibration set,
   select or stop by the tree; resolve the fresh holdout under the completed surface.
4. On a selection, **open what D4 never opened** — final A/B, the bootstrap at seed 21041,
   promotion, shadow, canary, activation — and close Gate L2 on its own evidence.

## 5. What this proposal does not do

- It does not unblock Sprint 22A, and it does not claim the 0.40 floor is met anywhere.
- It does not re-decide S21D4-039 or S21D4-046; both stops stay immutable.
- It does not spend anything: the calibration set was read for diagnostics the handoff
  authorises, the holdout result was not read at all, and every number above divides by
  the independent denominator revision 4 froze.
