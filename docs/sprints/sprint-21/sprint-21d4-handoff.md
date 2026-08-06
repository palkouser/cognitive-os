# Sprint 21D4 handoff — what a capacity residual requires next

Sprint 21D3 asked whether Sprint 21D2's invariance defect was representational or a capacity
residual, and answered it. The alpha-normalised v2 encoding is **exactly invariant**: the same
contract spelled differently reaches the same first action every time, and action preservation
is 1.00 for all twenty-four frozen settings across all six transformation cases. The defect did
not move. What remains is absolute ranking accuracy — 0.65 clean first-choice against a 0.5
baseline — and 0.65 cannot produce a metamorphic set with zero confident errors.

**Gate L2 does not pass. Sprint 22A remains blocked.** This handoff targets a bounded successor
experiment, not Sprint 22A, and nothing here may be read as unblocking it.

Outcome condition hash: `5f5a8b639c640ce9f306664fb8bb37ff0eb8619f528db1dd5274263dd81fcea5`

D3 is released. Tag `sprint-21d3-evidence-baseline`, object
`bcf2976dd0f063b1eb4ea16b388eea590e6172dd`, peels to `ef4388b1bf9cb842b25a06aa2255abd1042702c2`;
PR `#221`; exact-head post-merge `main` CI run `31072527026`, 30 of 30 success. Gate L2 condition
29 is met and the gate still does not pass. A successor branches from the verified current
`origin/main` and treats the tag as immutable release evidence.

Authority for what D3 did: [Sprint 21D3 Technical Backlog](sprint-21d3-technical-backlog.md).
Gate status: [Gate L2 assessment (D3)](gate-l2-d3-assessment.md). Results:
[Sprint 21D3 report](sprint-21d3-report.md). Execution: [execution log](sprint-21d3-execution.md).

## 1. The first stop, and the second

D3 stopped twice, on two independent branches.

**Correction, at S21D3-039** — hash `68ea06843d2136e390bf8a4e…`. No frozen k-NN
setting cleared both the released selection rule and the revision-3 non-silence rules. Every
setting that answered was confidently wrong on some semantics-preserving case; every setting
that avoided that answered no probe at all.

**Retrieval, at S21D3-045** — hash `f0b53912055223667c2cca93…`. Sixty unseen queries,
no arm clearing either floor, every arm at or below chance on recall.

Both are immutable. Neither may be re-decided by a successor; a successor measures something
else.

## 2. What remains valid, and can be reused unchanged

- **The v2 feature contract and its normaliser.** `correction-ranking-v2`, hash
  `492c90a5df420de9…`, and the production alpha-normaliser. Its exact invariants held on every
  case D3 measured. A successor that changes the encoder is answering a question D3 already
  answered.
- **The authored D3 corpus**: 50 fitting groups, 20 calibration groups, the 120-case metamorphic
  set with its hard-coded oracle, and the 60-group retrieval pool. Transitively separated, with
  a published defect ledger.
- **Final A, final B and canary catalogues.** Sealed, never opened, zero outcomes and zero
  body-access receipts. **A successor may reuse all three whole roles**, exactly as D3 reused
  D2's — the reuse audit and the replacement procedure are already written.
- **The W4 implementation surface**: the versioned promotion payload and its evaluator, the v2
  artifact and its direct evaluation boundary, the hardened runtime resolver, receipt-aware
  sequencing, `verify_component()`, and activation-time byte revalidation. All built, all tested,
  none exercised against a real candidate.
- **The W7 operations surface**: the eleven-class evidence report, the corruption matrix, and the
  release matrix.

## 3. What is spent and may not be reused

- **The D3 calibration and metamorphic evidence is spent.** It selected nothing, but it was read
  by a selection rule, and §10.3 forbids re-deciding on it.
- **The D3 retrieval holdout is spent.** It was read once, which is all the protocol allows. A
  successor needs a **new** untouched holdout.
- **The D1 development query set remains development-only.** It has now been replayed by two
  sprints and closes no condition.

## 4. The exact next experiment

The residual is capacity, so the next experiment must change capacity or change the question —
not the encoding.

**The smallest experiment that could resolve it:** measure whether the confident-error rate is a
property of the *learner* or of the *evidence volume*. D3 fitted 200 rows over 50 groups. Before
proposing a different learner, a successor should establish the yield curve: fit the same frozen
k-NN on 400, 800 and 1600 rows over proportionally more groups, and measure confident errors on
a fresh metamorphic set at each point. If confident errors fall monotonically with volume, the
answer is a corpus sprint. If they plateau above zero, the answer is a different hypothesis
class, and *that* is when a new learner is worth pre-registering.

This ordering matters: D2 and D3 both spent a sprint on a learner change. Neither established
whether the learner was the binding constraint.

**What must not be done:** no parametric rung opened on D3's evidence, no threshold revision, no
refit on the spent calibration set, and no encoder revision. §10.2 closes all four.

## 5. Retrieval: a different constraint

Gate D1 condition 15 **remains open**, and the reason is now precise rather than suspected.
`ActionDecisionGraph.search_text()` is domain, task signature, node labels and edge kinds. It
carries no repaired source, no issue text and no provenance hash — so two structurally identical
trajectories are one document to every arm.
`distinct_after_removing_domain_and_signature: 1` over sixty candidates.

Improving the *arm* cannot fix this, and D3 demonstrated that: the fixed RRF arm reached
0.7750/0.4478 on a development set with real complementarity and 0.5000/0.3004 on the holdout.
**A successor must widen the searchable surface before it measures another arm**, and doing so
is a contract change to the Experience Memory Graph, not a retrieval tuning exercise.

One further constraint the successor inherits: the bounded-GED arm is **not reproducible** under
a wall-clock timeout, so its D1 and D2 numbers cannot be replayed by anyone. Either the
comparator gets a deterministic budget or the arm leaves the frozen set.

## 6. Not opened, and why

20 dependent tasks carry typed not-opened records bound to one stop hash,
`68ea06843d2136e390bf8a4e…`: S21D3-051, -054, -056, the ten E06 items and the seven
E07 items. S21D3-075 is the declared exception and ran unconditionally against the isolated
lifecycle fixture.

## 7. What this handoff does not authorise

- It does not unblock Sprint 22A.
- It pre-authorises **no new dependency**, no new provider, and no new store.
- It does not authorise reuse of any spent D3 evidence for a new decision.
- It does not describe any W4 or W7 capability as exercised against a real candidate. Every one
  of them was proven against a contract fixture, and the evidence says so in its first field.
