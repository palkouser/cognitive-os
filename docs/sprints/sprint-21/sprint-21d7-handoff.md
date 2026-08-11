# Sprint 21D7 handoff — a passing gate, and what most of the value turned out to be

Sprint 21D3 asked whether D2's invariance defect was representational or a capacity residual and
answered capacity. D4 asked whether the frozen k-NN could be made **selective** and answered no,
with zero-error coverage of exactly zero in all 144 cells. D5 asked whether a **within-group
contrastive margin** separates the errors and answered yes, but certified only 0.26–0.27 against a
floor of 0.40. D6 asked whether **split conformal** over that same margin certifies enough of it,
and the answer was a typed stop: the bound came out at 0.2747 against a ceiling of 0.15, and the
sealed transfer record said why — the 384 embedding channels carried the *authoring run*, not the
task.

D7 asked the question that record licensed: **drop them.** Seven relational channels, six sealed
v2 scalars and the repair-containment share, the same fit rule, the same α, the same ceiling, the
same coverage floor.

It passes. **Gate L2 passes at 29 of 29, and Sprint 22A is unblocked.** The release is on the
remote: `#229` squash-merged into protected `main` as `3f5d7379…`, exact-head CI 30 of 30, and
the annotated tag `sprint-21-learning-baseline` created after it and never moved.

And the most useful sentence in this handoff is not that one. It is this:

> **The deterministic containment rung is most of the value, and the fitted direction is the
> remainder.** Under the seated ladder, only 5 of 59 admitted decisions differ from the ordering
> the containment channel produces on its own — 5.085 projected changed final decisions against a
> floor of 20. The sprint passes because S21D7-027 unseated that rung at W2 step 0, before
> anything was scored, on the gate owner's explicit decision with both branches priced.

A successor that reads the +0.383 and skips that paragraph will inherit the wrong model of what
was built.

---

## 1. The ending is typed, and the type is the instruction

§3.4 published six endings in W0 with `measured_values: 0`. D7 landed on **ending 1,
`1_select`**, and the sealed sentence is what it means:

> all nine conditions hold; bind the v3 artifact to the new conformal point, run the lifecycle,
> close the gate, unblock Sprint 22A

— `sprint-21d7-contracts.json`, `contracts.decision_tree.endings`.

All four of those were done, in W3, and `sprint-21d7-continuation.json` names the fifteen
deliverables with the record that closed each. The same record prints the fifteen Gate L2
conditions a stop would have closed **as an empty set**, deliberately: D3 through D6 each bound
between fifteen and nineteen conditions to a stop hash, and an omitted map is not the same claim
as an empty one.

## 2. What was measured, in the order it matters

| | |
|---|---|
| final first choice, 60 groups opened once | **52 / 60 = 0.8667** |
| strongest rung on the same groups (`fixed_input_order`) | 29 / 60 = 0.4833 |
| absolute gain / relative error reduction | **+0.3833** / **0.7419** |
| changed decisions | **45** (floor 20) |
| paired group bootstrap, 10 000 resamples | **[0.233, 0.533]**, excludes zero |
| per-batch direction | final A **+0.300**, final B **+0.467** |
| certification cell: coverage / CP bound | 0.59 / **0.126207** against C = 0.15 |
| safety movement / retention loss | **0** / **0** |
| promotion metamorphic | 120 nominal, 60 independent, 80 admitted, **0 errors**, bound 0.0368 |
| canary: learned vs rung attempts to an accepted candidate | **5** vs **9** |

**No threshold moved in any wave.** α = 0.20, C = 0.15 and the 0.40 coverage floor are D6's,
carried unchanged; D7 made zero amendments across W0, W1, W2, W3 and W4.

## 3. The three findings a successor should read before its own W1

**W3-F1 — a digest recomputed unchanged proves the bytes did not move, not that anything can use
them.** The two final roles had been carried "intact" for five sprints. They were intact. They
were also unencodable: four D2-authored bodies predate the source canonicaliser's reflection ban,
and nobody had ever run a final body through the canonicaliser, because opening the roles is what
W3 does. The repair was audit-first — `sprint-21d7-final-role-audit.json` sealed with
`bodies_authored_by_this_record: 0` — and the test that catches the next one is written over the
**roles**, not over the replacements.

**W4-F1 — a validator can outlive the claim it enforces.** The W1 seal asserts that all three
carried roles are byte-identical to D6's. W3's authorised repair made that false for two of them,
and the release matrix is where it surfaced, because that is the only place the sprint's own
validators run. Fixed by rebinding rather than by editing: `sprint-21d7-protected-role-rebinding
.json` names the moved roles, proves each new hash is the one its W3 campaign actually executed
against, and leaves the W1 seal's bytes alone — the same discipline S21D7-027 used when it
superseded S21D7-011.

**W2-F1 and W2-F2 — reproduction checks that fail on the passage of time prove nothing.** A
`--check` that re-globs a directory to rebuild a chronology block expires the moment the wave
writes its next record; a live stopwatch inside a record makes byte-for-byte restart reproduction
impossible. Both were fixed by making the check compare what is claimed rather than what the
clock said.

## 4. What Sprint 22A inherits, and what it must not assume

**Inherits, usable without re-deriving:**

- a **live selection surface**: `experience.correction_ranking`, component
  `learned.containment.correction_ranking`, active on five canary groups, with a ledger that
  replays, a hash chain that verifies and a kill switch that has been exercised;
- an **admission rule with a stated error budget**: split-conformal at α = 0.20 with a
  Clopper–Pearson 95% upper bound at or below C = 0.15, measured at 0.126207 with coverage 0.59;
- the **transfer record** that says why this class and not the last, and the per-family rates
  underneath it;
- the seven-channel v3 contract, its encoder, the artifact format, the loader, the resolver with
  all eighteen reason codes exercised, and a promotion payload whose twenty gates are each bound
  by hash to the record that measured them;
- the retrieval condition, inherited under a ruling re-checked at gate close.

**Must not assume:**

- **that the learned component is where the value is.** See the paragraph at the top. The
  containment ordering is a deterministic, label-free, pre-sandbox computation, and on the
  admitted subset the fitted direction adds five decisions to it. If 22A wants the cheap win, the
  rung is the product;
- **that the coverage transfers.** The bar was placed on D6's demoted certification groups.
  Exchangeability is now load-bearing in production: a corpus with a different family profile
  moves coverage without moving a threshold;
- **that the anatomy is free.** The containment signal reads the two-complete-two-partial
  structure the authoring contract froze. A domain expansion that varies candidate count or
  repair completeness dissolves the signal by design;
- **that "active" means shipped.** It routes five groups. The bounded steady-state configuration
  is sealed and was never entered, and the canary→steady transition was not taken;
- **that a carried role is usable because its digest is unchanged.** W3-F1. Run the thing you
  intend to run, on the bytes you intend to run it on, before you plan around them;
- **that any Gate L2 condition is inherited.** §2.2 has held for four sprints: each re-evidences
  all of them against its own authorities.

## 5. What this handoff refuses

**Not a third hypothesis class.** The class question resolved. Reopening it before the corpus
question is answered would be searching the axis that just stopped moving.

**Not a larger corpus, yet.** The aliasing counts bound reachable coverage from above on any
seven-channel corpus of this size. Author more groups only against a measured slope.

**Not a steady-state promotion by default.** Entering the bounded steady state is a decision with
its own evidence — canary tasks, safety regressions, verifier disagreements — and the transition
condition that names all three is sealed and unexercised.

---

## Evidence handles

| Record | Seal (`integrity_content_hash`) |
|---|---|
| `sprint-21d7-pre-registration.json` | revision 7, `measured_values: 0` |
| `sprint-21d7-learner-selection.json` | `63fd43dab720c57e…`, ending `1_select` |
| `sprint-21d7-artifact.json` | `b38e3f60a13c4c8f…` |
| `sprint-21d7-final-evidence.json` | `a8aa099a5d32f9a0…` |
| `sprint-21d7-promotion.json` | `fde811401cb85dab…` |
| `sprint-21d7-lifecycle.json` | `155fc87f4bcef558…` |
| `sprint-21d7-continuation.json` | ending `1_select`, 15 delivered, 0 not opened |
| `sprint-21d7-gate-l2.json` | `5b83cd4bcfa1cce9…`, 29 met, verdict `gate_l2_passes` |
| `sprint-21d7-release.json` | `582aa77732308731…`, zero findings, tag `3025082526cef6d9…` |

The per-wave evidence indexes in [`sprint-21d7-execution.md`](sprint-21d7-execution.md) carry both
hashes for every record; this table names only the ones a successor's pre-registration has to
bind.
