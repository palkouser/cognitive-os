# Sprint 21D5 handoff — what a hypothesis-class bound requires next

Sprint 21D3 asked whether its invariance defect was representational or a capacity residual and
answered capacity. Sprint 21D4 asked the next question down: whether the frozen k-NN can be made
**selective** — given a per-decision confidence threshold above which it is never confidently
wrong, does anything useful remain above it?

It cannot. Over 100 independent calibration decisions, at two fitting volumes, across all 144
frozen cells, zero-error coverage is **exactly zero**. Not small. Zero. Every cell beats the
strongest deterministic baseline and not one of them can separate its own errors.

**Gate L2 does not pass. Sprint 22A remains blocked.** This handoff targets one bounded successor
experiment, not Sprint 22A, and nothing here may be read as unblocking it.

Authority for what D4 did: [Sprint 21D4 Technical Backlog](sprint-21d4-technical-backlog.md).
Gate status: [Gate L2 assessment (D4)](gate-l2-d4-assessment.md). Results:
[Sprint 21D4 report](sprint-21d4-report.md). Execution:
[execution log](sprint-21d4-execution.md).

## 1. The two stops, and which one is which

**Correction, at S21D4-039** — hash `5caa48970898d180ce1f3397…`, stop kind
**`hypothesis_class_bound`**. The stop kind is the whole content of this handoff, and it was
chosen by a measurement rather than by judgement. §3.3 distinguishes two failures:

- `volume_bound` — zero-error coverage is above zero but below 0.40, *and* materially higher at
  320 rows than at 200. The residual is evidence volume; the successor is a corpus sprint with a
  target volume derived from the measured yield curve.
- `hypothesis_class_bound` — zero-error coverage is at or near zero at both volumes and does not
  improve with volume. The frozen k-NN cannot separate its own errors, and *that* is when a
  different hypothesis class is worth pre-registering.

D4 measured 0 and 0. **More data is not the answer, and D4 has the curve that says so.** A
successor that authors another hundred groups and refits the same class is buying the same
number at a higher price.

**Retrieval, at S21D4-046** — the independent branch reached its own hash-bound result and it is
a near miss, not a stop of the same kind. Reciprocal rank fusion cleared Recall@5 at 0.7500
against a floor of 0.70 and missed MRR@10 at 0.4911 against 0.50. **0.0089.** Gate D1 condition
15 remains open on that evidence rather than on the correction branch's stop.

Both records are immutable. Neither may be re-decided by a successor; a successor measures
something else.

## 2. What remains valid, and can be reused unchanged

- **The revision-4 counting rule.** Nominal, independent, replicated; every rate over the
  independent denominator, named in the stored bytes, refused by the published schema if absent.
  This is the sprint's most portable output and it is not specific to correction ranking.
- **The 100 authored calibration groups and 400 outcomes**, sealed before execution,
  verifier-labelled, with a published defect ledger. They are **spent for selection** — a
  selection rule has read them — but they remain valid *fitting* and *diagnostic* evidence.
- **The 60-group retrieval pool and its 60 queries.** Read once. Spent.
- **The v2 feature contract**, `492c90a5df420de9…`, 390 channels, unchanged and re-verified.
- **The widened `search_terms` surface**, with its unchanged-hash proof and its leak guard.
- **The bounded-GED budget.** The arm is reproducible now; anything measured with it before D4 is
  not, and no back-fill was attempted.
- **The twelve-class integrity report** and the one truncation fence, both of which are
  substrate rather than experiment.

## 3. The smallest next experiment

The stop kind names it: **pre-register one hypothesis class that can separate its own errors on
these features, and test only that.**

What D4 leaves as its input:

1. **The residual is calibration, not ranking.** The grid ranks better than the deterministic
   baseline everywhere — 0.56 to 0.73 against 0.52. What it cannot do is know when it is wrong.
   A successor should not chase first-choice rate; it should chase a usable confidence.
2. **The evidence to fit that on already exists.** 100 independent calibration decisions with
   their scores, their labels and their fitted vectors, all sealed and hash-bound. No new corpus
   is needed to test whether a different class has a zero-error region.
3. **The floor to beat is published and unchanged**: zero confident errors over at least 100
   independent decisions, at coverage at least 0.40, with at least 20 projected changed final
   decisions. Do not relax it. D4's whole value is that it measured against the same floor D3
   did.
4. **The one thing to pre-register before looking**: which class, and why *this* residual implies
   it. D4 may not choose it retrospectively from its own numbers, which is why this handoff names
   the requirement rather than the class.

For the retrieval branch, the successor's question is narrower and cheaper: **0.0089 on MRR@10,
on a surface that reaches 41 of 60 candidates rather than 60.** Ten candidates carry no search
terms at all, because they are repairs in pure arithmetic over their own parameters. Whether
closing that gap closes the floor is a measurement nobody has made, and it is a smaller
measurement than a new hypothesis class.

## 4. What a successor must not assume

- **That more calibration data helps.** Measured at two volumes; it does not.
- **That D3's or D4's retrieval numbers are comparable.** Pool, comparator and surface changed
  together. No ablation was run, because the holdout is read once.
- **That any D4 surface below the selection was exercised.** D4 fitted no artifact. The loader,
  resolver, sequencer, verification and activation paths were not re-proved, and three Gate L2
  conditions D3 met against a contract fixture are recorded as not opened here rather than
  inherited.
- **That a `warning` integrity class is a pass**, or that a `not_opened` condition is a soft one.
- **That the `_test` suffix consents to anything.** Eleven paths in this repository truncate; all
  eleven now require `COGOS_TRUNCATABLE_DATABASE` to name the connected database, and W7-F1 is
  what that rule cost to learn twice.

## 5. Not opened, and why

Twenty-six dependent tasks carry typed not-opened records bound to one stop hash,
`5caa48970898d180ce1f3397…`: S21D4-050 through -058, the ten E06 items -060 through -069, and the
seven E07 items -070 through -074, -076 and -077. **S21D4-075 is the declared exception** and ran
unconditionally against the isolated lifecycle fixture.

## 6. What this handoff does not authorise

- It does not unblock Sprint 22A.
- It pre-authorises **no new dependency**, no new provider, and no new store.
- It does not authorise reuse of any spent D4 evidence for a new decision — the calibration set
  for selection, or the retrieval holdout at all.
- It does not authorise a refit, a threshold revision or an encoder revision on D4's evidence.
- It does not describe any capability below the selection as exercised against a real candidate.
