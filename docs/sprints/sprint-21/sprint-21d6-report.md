# Sprint 21D6 report — the prefix rule was broken, and fixing it was not enough

- Branch: `sprint-21d6-groundwork`
- Pre-registration: revision 6, SHA-256
  `00935965301db64bb3da4b65b37d09baf56f8b06e9eb0346767ceaa58380e80d`, published with
  `measured_values: 0`
- Gate contract: `9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7`, 29 conditions,
  **one clause amended** by the gate owner in W0 before any measurement existed
- Gate assessment: [`gate-l2-d6-assessment.md`](gate-l2-d6-assessment.md)
- Execution log: [`sprint-21d6-execution.md`](sprint-21d6-execution.md)
- Handoff: [`sprint-21d7-handoff.md`](sprint-21d7-handoff.md)
- Outcome: **Gate L2 does not pass. Sprint 22A remains blocked.** Thirteen conditions of
  twenty-nine met, fifteen never opened, zero failed, and condition 29 `pending` until the
  protected release closes it.

---

## 1. What the sprint set out to do

Sprint 21D5 stopped on a typed stop, `selective_margin_bound`, and that stop licensed exactly one
successor experiment: **a different confidence construction over the same ranker.** Not a
different ranker — the direction reached 0.91 and 0.88 first choice against a 0.42 baseline. Not a
third hypothesis class. Not a larger corpus — coverage moved one point across a 2.25× volume span.

The failing quantity was named precisely. D5's zero-error prefix rule walks the margin ordering
down to the first wrong decision and stops, so one badly-placed error truncates everything below
it. D5's own sealed sweep prices that exactly: at 720 fitting rows the rule stopped at 27 admitted
because the 28th decision in the margin ordering was wrong, while tolerating that one error would
have admitted 58 — with a Clopper–Pearson bound of 0.079, *lower* than the zero-error point's own
0.105, because 58 decisions is more evidence than 27. A rule whose coverage is decided by the
position of one error is a rule with variance, not a bound.

D6 pre-registered the smallest change that addresses that diagnosis and nothing else.

## 2. The one clause that changed, and who changed it

§2.3 required *both* "exactly zero confident errors among admitted decisions" *and* "clean
coverage at least 0.40". D5's sealed sweep priced that pair exactly, and it is infeasible: at zero
errors the best coverage available is 0.27 at 720 rows and 0.26 at 320, against a floor of 0.40,
at volumes 2.25× apart.

The argument put to the gate owner was that **"exactly zero confident errors" never bought a zero
error rate.** At D5's coverage it bought a Clopper–Pearson 95% upper bound of 0.105. A rule
admitting one error in 58 bounds the same quantity at 0.079 with 2.2× the coverage. The zero was a
property of a small sample, not a safety property.

The gate owner granted amendment 2, and it changes one clause:

> **Struck:** exactly **zero confident errors** among admitted independent calibration decisions.
>
> **Replaced by:** admission is a **split-conformal bar at the pre-registered α**, and the
> Clopper–Pearson one-sided 95% upper bound on the error rate among admitted independent
> calibration decisions is at most the pre-registered ceiling **C**.

α = 0.20 and C = 0.15 were both pre-registered with `measured_values: 0`, and α's floor is
arithmetic rather than taste: with m = 12 wrong decisions in the conformal half, any α below
2/13 = 0.1538 reproduces the exact rule the sprint exists to replace. Everything else in §2.3 is
verbatim, and no other Gate L2 threshold moved.

**α bounds the leak, not the precision.** The quantile is taken over the margins of *errors*, so
what it guarantees is P(admitted | wrong) ≤ α. The share of admitted decisions that are wrong is a
different, smaller number, and it is the one §2.3 reads. Conflating them would have written the
amendment against the wrong quantity; both readings are in the module docstring and in the stored
bytes of every derivation.

## 3. What D6 did not change

No encoder, no normaliser, no channel, no fitted representation: the same 390 v2 channels hashing
to the same `492c90a5df42…`. No hypothesis class, no λ, no margin definition, no abstention floor.
**And no fit.** Both directions were resolved out of D5's content-addressed artifact store,
read-only, by the content hash D5 published, byte-length exact; `fitted_here: false` is checked
rather than asserted. The numeric clip-and-scale envelope was loaded from D5's released training
seal so both halves share one envelope.

D6 authored one corpus and ran one partition. That is the whole of what it added.

## 4. The corpus, and what authoring it cost

One hundred certification groups, freshly authored, 400 outcomes. Eighty-nine were written and
**eighty-five kept**; four were withdrawn, and all four for one reason: the body carrying the
defect reduced to a textbook one-liner and collided with a released group. That is what a
saturated subject looks like from the inside. The `--search` pre-check screens the *words* a
contract uses and killed one group before a line was written; it cannot see saturation, and that
was the price of the other four.

Executed in an isolated store: **400 runs, 200 hidden-passing, 0 of 100 baselines through the
hidden suite, 0 containers on the replay.** The 200 is the contract's shape exactly — two full
repairs per group — and no baseline passing its hidden suite is the other half of it.

Eleven of eleven snapshot scans passed over the pair the gate owner ruled on: D5's conformal half
against D6's certification half. The conformal matrix, rebuilt read-only from D5's released bytes,
comes back as its published `106061126df8…` — every vector and every label intact. Highest
cross-split similarity 0.993313 against a 0.999 floor; 100 groups against 100 sharing none.

## 5. The measurement

The bar was derived **once**, at α = 0.20, from the conformal half only, and reproduced across a
process restart by passing the sealed derivation back. The rebuilt conformal half yields exactly
12 wrong answered decisions at 720 rows and 9 at 320 — D5's published counts — and the stage
refuses rather than proceeding if it does not, because §3.2's α floor was computed from that
number.

Rank 11 of 12, threshold `0.448554`. On the pre-registered 720 cell:

| the amended §2.3 | required | measured | |
|---|---|---|---|
| independent clean decisions | ≥ 100 | 100 | met |
| clean coverage | ≥ 0.40 | **0.40** | met, exactly at the floor |
| projected changed final decisions | ≥ 20 | 39.0 | met |
| first choice over admitted vs. baseline | strictly above | 0.85 vs 0.62 | met |
| changed clean decisions | ≥ 1 | 26 | met |
| first-action preservation | 100% | 100% | met |
| every cell and sweep point reported | — | 2 cells, 200 points | met |
| maximum inference | ≤ 250 ms | 0.023 ms | met |
| **CP-95 upper bound among admitted** | **≤ 0.15** | **0.274745** | **failed** |

Forty admitted, six wrong. Eight conditions hold; the ninth — the one the amendment introduced —
misses by a factor of 1.8. Typed ending **`leak_budget_exceeded`**, §3.4 step 2. The null selection
is immutable and its stop hash is `981bb130d03a45ba…`.

**The rule worked.** On this same corpus, the zero-error prefix rule D6 replaced admits **6 of
100**. Split conformal admitted 40. The successor construction did exactly what D5's stop asked
of it.

## 6. The finding that sizes the successor

§3.4's step 2 was written in W0 and points the successor at conformal-half volume: a tighter α
needs more than 12 wrong decisions to draw the quantile from. **The published sweep contradicts
its premise.**

Across the 100 reported thresholds on the selectable cell and the 100 on the reported one, the
amended pair — coverage ≥ 0.40 and CP-95 ≤ 0.15 — is satisfied at **zero points**. No threshold at
any coverage reaches the ceiling; the best bound available anywhere at or above the coverage floor
is 0.241298; the deepest error-free prefix by margin is 6 decisions.

A tighter α moves the bar along that curve, and every point on it misses. **This is §2.1's
infeasibility argument one level down: the amended pair is not merely unmet on this evidence, it
is unreachable.** What binds is the ranker's error rate on a corpus it was not fitted against, and
that is a hypothesis-class question rather than a volume one. The distinction is recorded in the
selection record, in the continuation record beside the sealed sentence it qualifies, and in the
handoff — never in place of the typed ending, which stays exactly as it was written.

## 7. Exchangeability, named in advance and then measured

§6 of the backlog said the conformal guarantee needs the two halves to be exchangeable, that a
shared authoring contract makes this plausible rather than proven, and that a coverage far from
the design's 0.58 is the symptom that would falsify it. Four readings agree:

- coverage **0.40** against a design expectation of 0.58;
- realised leak **0.25** against a 0.20 budget — 6 of the certification half's 24 wrong answered
  decisions cleared the bar;
- the direction scores **0.76** first choice here against **0.88** on D5's own calibration set;
- the strongest deterministic rung is **`lexical_similarity` at 0.62**, where D5's corpus put
  `fixed_input_order` on top at 0.42.

The last is the sharpest, because it is measured with no model in it at all. D6's corpus is a
different distribution from D5's — harder for this ranker, easier for a lexical baseline — and both
came out of the same authoring contract and the same generator.

## 8. Findings

**The typed ending asserted a guarantee nobody measured.** §3.4 step 2's wording — "the bar held
its leak guarantee" — was carried into the classifier as a constant. The realised leak, the one
quantity α actually bounds, was absent from the record. Fixed inside the wave: every cell now
measures it, and on the selectable cell it exceeded the budget, which is exactly what the constant
would have concealed.

**§2.3's invariance condition had no item in any wave's condition list.** W1's list ran 5–9 and
W2's ran 12/14/17; first-action preservation belongs to neither and would have been evaluated
against a predecessor's sample. S21D6-031 measures it on D6's own bodies: 160 vectors compared,
zero changed, zero label changes, zero first-action changes.

**The store guard was copied from D5 and its forbidden list stopped at `s21d4`** — in three
places — while D6 reads its envelope, both directions and its whole conformal half *out of D5's
store*. Three copies became one `_isolated_pair()`, and the release matrix executes the refusal
rather than describing it.

**Two authoring failure modes, both from the D4 contract, both hit again.** A "more careful"
repair that silently fixed a second edge case; a visible test asserting the one reading of the
contract the baseline fails. Three lessons written down: the visible case must be one both
readings of the contract agree on; an accidental repair looks exactly like a careful one; escape
only where the escape must survive into the generated module.

## 9. Limitations

**Two spent corpora, and no holdout gained.** D5's 100 calibration groups are now spent twice —
once as calibration, once as a bar-setting half — and D6's 100 certification groups are published
in full, sweep included. Neither can serve as a holdout again.

**The CP bound reads the admitted set as a fixed-size sample.** The admitted set is selected by
margin, so this is D4's and D5's established convention rather than an exact conditional
statement. Changing it would move every historical number, and D6 changed nothing here.

**The chronology of the conformal half is inherited, not recomputed.** D5's per-row outcome times
live in D5's database, which D6 does not open, so both timestamps are D5's seal time and the
chronology scan's verdict over that half is not independent evidence. The claim it would test was
certified in the bound D5 record.

**One condition's evidence is a predecessor's measurement.** Gate L2 condition 24 and Gate D1
condition 15 are inherited from D5's sealed retrieval result under a W0 ruling. The inheritance is
re-checked at gate close by recomputing the three identities that void it — the searchable
surface, the arms, the comparator — and all three are unmoved; but the measurement itself is
D5's, and the record says so rather than presenting it as D6's.

**The release matrix is a smaller claim than D5's.** D6 allocates no operations wave, so three
rows D5 recorded from backup, restore and corruption evidence have no evidence to read, and there
is no `d6-integrity` report command to run. Both absences are named in the record.

## 10. Outcome

**Gate L2 does not pass.** Thirteen conditions met, fifteen never opened behind one typed stop,
zero failed, zero carried from D5, and condition 29 `pending` until the protected release closes
it — which makes the released total the same fourteen-fifteen split D5 ended on, reached by a
different route and with a materially sharper reason.

Sprint 22A remains blocked. The successor experiment the handoff names is not a third bar and not
a larger corpus: it is to **measure the transfer gap directly** — the released deterministic
ladder over both corpora, every rung, both directions, no fitting — because three sprints have now
read numbers that are partly a property of the ranker and partly a property of the gap between two
authoring runs, and nothing has yet separated the two.

`final_a`, `final_b` and `canary` stay unopened for the fourth sprint running.
