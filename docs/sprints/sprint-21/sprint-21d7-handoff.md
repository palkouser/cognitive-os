# Sprint 21D7 handoff — what a leak budget exceeded requires next

Sprint 21D3 asked whether Sprint 21D2's invariance defect was representational or a capacity
residual and answered capacity. Sprint 21D4 asked whether a frozen k-NN could be made
**selective** and answered no, with zero-error coverage of exactly zero in all 144 cells. Sprint
21D5 asked whether a confidence built out of **within-group contrast** separates the errors, and
answered half of it: the direction ranks — 0.88 first choice against a 0.42 baseline — and the
zero-error prefix rule certified 0.27 of it against a 0.40 floor.

Sprint 21D6 asked the question that stop licensed, and only that one: **is the prefix rule the
thing that was broken?** It varied the admission rule and nothing else — same encoder, same
alpha-normaliser, same 390 channels, same `pairwise-contrastive-linear-v1` class, same two sealed
directions, same margin floor, same corpus contract — and replaced the prefix with a
split-conformal bar at a pre-registered α = 0.20 under a gate-owner amendment that traded "exactly
zero confident errors" for a Clopper–Pearson ceiling of C = 0.15.

**The prefix rule was broken, and fixing it was not enough.**

---

## 1. What was measured, on evidence nobody had read

One hundred freshly authored certification groups, 400 outcomes, executed in an isolated store.
The bar was derived once from D5's hundred spent calibration decisions — rebuilt read-only from
D5's released bytes, reproducing its published matrix hash exactly — and reproduced across a
process restart.

| | D5, prefix rule, its own corpus | D6, conformal bar, a fresh corpus |
|---|---|---|
| admitted of 100 | 27 | **40** |
| errors admitted | 0 | 6 |
| CP-95 upper bound | 0.105 | **0.2747** |
| first choice over all answered | 0.88 | **0.76** |
| strongest deterministic baseline | 0.42 | **0.62** |

Eight of the nine amended §2.3 conditions hold. The ninth — the ceiling the amendment introduced —
misses by a factor of 1.8. Typed ending: **`leak_budget_exceeded`**, §3.4 step 2, stop hash
`981bb130d03a45ba…`.

**The rule itself worked.** On this same corpus the zero-error prefix admits **6 of 100**. Split
conformal admitted 40. The successor construction D5's stop asked for did exactly what it was
supposed to do, and the gate still does not close.

---

## 2. The finding that decides what comes next

§3.4 step 2 was written in W0, before any measurement, and it sizes the successor as a volume
problem: *"a tighter alpha needs more than 12 wrong decisions in the conformal half, which is a
volume question and the first measured reason this programme would have to author more."*

**The published sweep contradicts its premise.** Over the 100 reported thresholds on the
selectable cell — and the 100 on the reported one — the amended pair is satisfied at
**zero points**:

- no threshold at any coverage brings the Clopper–Pearson bound to 0.15 or below;
- the best bound available anywhere at or above the 0.40 coverage floor is **0.241298**;
- the deepest error-free prefix by margin is **6 decisions**, so even a bar admitting nothing but
  correct answers carries a bound near 0.39 on this corpus.

A tighter α moves the bar along that same curve. Every point on it misses. **This is §2.1's
infeasibility argument again, one level down: the amended pair is not merely unmet on this
evidence, it is unreachable — and "infeasible" and "unmet" size two different successors.**

The binding constraint is not where the bar sits. It is the ranker's error rate on a corpus it
was not fitted against.

---

## 3. Exchangeability, named in advance and then measured

§6 said the conformal guarantee needs D5's calibration groups and D6's certification groups to be
exchangeable, that a shared authoring contract makes this plausible rather than proven, and that
**a coverage far from the design's 0.58 is the symptom that would falsify it.**

Four readings agree, and none of them was available before W2:

1. coverage came out **0.40** against a design expectation of 0.58;
2. the realised leak — the share of the certification half's wrong answered decisions that cleared
   the bar, which is the quantity α bounds — is **0.25 against a 0.20 budget**;
3. the direction scores **0.76** first choice here against **0.88** on D5's own calibration set;
4. the strongest deterministic rung is **`lexical_similarity` at 0.62** here, where D5's corpus put
   `fixed_input_order` on top at 0.42.

The last one is the sharpest, because it is measured with no model at all. **D6's corpus is a
different distribution from D5's, and it is a harder one for this ranker and an easier one for a
lexical baseline.** Both corpora came out of the same authoring contract, the same generator and
the same six families; four withdrawn groups and a saturation heuristic are the only authoring
differences on record.

That is not a defect in the corpus. It is the finding: **the programme has been measuring transfer
without knowing it.** D4 fitted and certified inside one corpus. D5 fitted on D4's spent evidence
and certified on its own fresh corpus. D6 placed a bar on D5's evidence and certified on its own.
Each step read a number that was partly a property of the ranker and partly a property of the gap
between two authoring runs, and until now nothing separated the two.

---

## 4. The one successor experiment

**Measure the transfer gap directly, before varying anything else.**

Score D6's 100 certification decisions and D5's 100 calibration decisions with the *same* sealed
720 direction — which D6 has already done, and the two numbers are 0.76 and 0.88 — and then ask
the question neither sprint asked: **how much of that 12-point drop is the direction, and how much
is the corpus?** The deterministic ladder answers it with no model in it at all. `lexical_similarity`
at 0.62 against 0.42 says the two corpora differ by 20 points on a rung that never saw a fitted
weight, which is more than the whole learned-minus-baseline margin D5 reported.

A concrete, minimal shape:

- **one measurement, no fitting**: the released ladder over both corpora, every rung, both
  directions, reported per family;
- **the pre-registered quantity**: per-rung first-choice rate on each corpus, and the
  learned-minus-baseline difference on each. If the difference is stable across corpora and only
  the absolute rates move, the transfer gap is corpus difficulty and the confidence axis is
  genuinely exhausted. If the difference itself collapses, the direction does not transfer, and no
  admission rule over it ever will;
- **the decision it feeds**: whether Gate L2's §2.3 can be closed by *any* construction over
  `pairwise-contrastive-linear-v1`, which is the question three sprints have now approached from
  three sides without asking directly.

It costs no authoring, no fitting and no new contract. Every input is released and sealed.

## 5. What this handoff refuses

**A third confidence construction.** The axis has been varied twice — zero-error prefix, then
split conformal — and the sweep says the second one's failure is not about where the bar sits. A
third bar over the same margin is a sprint whose result is already on the record.

**A larger corpus, on the strength of step 2's sentence.** The sentence was written before the
sweep existed and its premise does not hold: more wrong decisions in the conformal half buy a
tighter α, and every α lands on a curve that misses. Authoring 100 more groups to move a bar along
it would be the most expensive way to reproduce this result.

**A third hypothesis class, yet.** D4 landed on `hypothesis_class_bound` and D5's diagnostic
narrowed it; picking a third class now, before the transfer gap is measured, risks attributing a
corpus difference to a model family. §4's measurement is what tells the difference — and if it
says the direction does not transfer, *then* the class question is the right one and it will be
much better posed.

**Any relaxation of §2.3.** The gate owner has amended it once, on an infeasibility argument
supported by a published table. §2.1's table priced the pre-amendment pair; §2 of this document
prices the amended one. **Neither is an argument for a second amendment** — two relaxations in two
sprints is a gate that follows the measurement rather than binding it. If the amended pair is
also infeasible against this ranker, the honest reading is that this ranker does not clear this
gate, not that the gate is too high.

---

## 6. State handed over

- Released on `main` at `cfd22ab6d3e32367ed5c920a3f3844e590acf8b6` (PR `#227`, squash-merged
  into protected main, exact-head CI 30 of 30); tag `sprint-21d6-evidence-baseline`, object
  `29debe41f8dbe16137c0ae528f0ad4390de8d451`.
- **Gate L2: 14 met, 15 not opened, 0 failed, 0 carried.** Exactly where D5 left it, on a
  different stop.
- **Gate D1: 6 and 7 closed by the stop; 15 closed** by inheritance from D5's sealed retrieval
  measurement, with all three voiding identities recomputed at gate close and unmoved.
- **Sprint 22A remains blocked.**
- Spent: D5's 100 calibration groups (now also spent as a bar-setting half) and D6's 100
  certification groups. Both are published in full, including every sweep point, so neither can
  serve as a holdout again.
- **Unopened, for the fourth sprint running:** `final_a` (30), `final_b` (30), `canary` (5). Zero
  bodies resolved, digests recomputed unchanged. They are still the only unread evidence this
  programme has, and §4's measurement does not touch them.
