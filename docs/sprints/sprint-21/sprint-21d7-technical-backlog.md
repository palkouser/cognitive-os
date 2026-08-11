# Sprint 21D7 Technical Backlog

## The Containment Contrastive Class, the Transfer-Gap Record, and Gate L2 Closure

- Predecessor: Sprint 21D6, tag `sprint-21d6-evidence-baseline`, object
  `29debe41f8dbe16137c0ae528f0ad4390de8d451`, peeling to
  `cfd22ab6d3e32367ed5c920a3f3844e590acf8b6`; PR `#227` and `#228`; exact-head post-merge `main`
  CI run `31382974994`, 30 of 30 success.
- Groundwork written and verified against released bytes, **not yet merged and not yet tested**:
  `repair_containment.py`, `containment_contrastive.py`, `transfer_gap.py`,
  `scripts/transfer_gap_d7.py`, the sealed diagnostic record
  [`sprint-21d7-transfer-gap.json`](evidence/sprint-21d7-transfer-gap.json) and the
  [class proposal](sprint-21d7-class-proposal.md) — see §1.2. Writing their test modules is W0
  work in this plan, not a done item.
- Gate contract: `9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7`, 29
  conditions, **unchanged — D7 asks to move no threshold**. The amended §2.3 (α = 0.20,
  C = 0.15, coverage ≥ 0.40) is measured as D6 left it. Three governance decisions stand in
  front of the sprint instead, none of which relaxes anything — see §2.2.
- Migration head: `0015`. D7 allocates none; `0016` stays unallocated unless W3's activation
  path turns out to need a store, which would be a defect finding, not a plan item.
- Outcome tags: success `sprint-21-learning-baseline`; negative `sprint-21d7-evidence-baseline`.
- **Status after execution began:** W0 and W1 are closed — see the
  [execution log](sprint-21d7-execution.md). All three §2.2 rulings were granted (the
  containment rung is **seated**), revision 7 is published, the corpus is complete at 100
  groups and the measured campaign has run. **W2 must open on the sealed pre-flight record
  §5.3 describes** ([`sprint-21d7-w2-preflight.json`](evidence/sprint-21d7-w2-preflight.json)):
  it discloses two facts the W1 bytes decide — a frozen disjointness sentence the v3
  representation falsifies by aliasing, and a measured design estimate of **zero** changed
  decisions among top-margin decisions under the seated pairing — both of which need a
  gate-owner reading fixed before any fresh decision is scored.

**This backlog is shaped like D6's with one inversion: D6 varied the admission rule over a
sealed direction, D7 varies the class under a sealed admission rule.** The bar machinery, the
census, the bound, the artifact payload, the loader, the resolver, promotion, shadow, canary,
activation and rollback are all released. D7 adds three small modules — already written — fits
one seven-channel direction once, authors one corpus, and is otherwise a measurement sprint
whose thresholds were all frozen by its predecessors.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](sprint-21d4-technical-backlog.md) are D7's execution contract
unchanged, incorporated by reference: the release-grade meaning of "done", the wave discipline,
the evidence-record shape, and the rule that a wave's defects are fixed inside the wave.

---

## 1. Verified starting state

### 1.1 What D6 released

Gate L2 at **14 met, 15 not opened, 0 failed**. The fifteen closed behind one typed stop,
`leak_budget_exceeded`, hash
`981bb130d03a45ba512ee3a758abb48db0d45c4b53a35a99bca79238c76e3fcd`. Split conformal at
α = 0.20 admitted 40 of 100 fresh decisions with 6 errors, CP-95 0.2747 against the 0.15
ceiling — and the published sweep shows the amended pair unreachable at every threshold on
either cell. Nothing was registered, approved or activated. Sprint 22A remains blocked.

### 1.2 The groundwork, and what it measured

Four files, all read-only against the released stores, all reproducing published hashes
before reading a single rate:

**`src/cognitive_os/learning/transfer_gap.py` + `scripts/transfer_gap_d7.py`** ran the §4
measurement the D6 handoff pre-registered. The learned-minus-strongest difference collapses
from **+0.46 to +0.14** (`difference_shift` −0.32) while `fixed_input_order` holds at 0.42 on
both corpora; the 320-row direction collapses harder (0.91 → 0.70). Per §4's own decision
rule: **the direction does not transfer, no admission rule over its margin ever will, and the
class question is licensed.** A scalar-only refit reproduces 0.76 on the fresh corpus, so the
non-transferring part is the 384 embedding channels — the class was ranking what an accepted
patch looks like in one authoring run.

**`src/cognitive_os/learning/repair_containment.py`** computes the signal the fitted channels
never read: a candidate's mean coverage of the other candidates' baseline-added lines. It is
the structural shadow of the hidden verifier's actual question under the frozen corpus
anatomy (variants one and two repair both edge cases, three and four one each). As a bare
deterministic ordering it scores **0.92 / 0.84** across the two corpora — above both sealed
directions on both — and the six frozen invariance cases cannot move it, by construction
(one rename map covers every source in a group) and by measurement (600 case evaluations,
0 ordering changes).

**`src/cognitive_os/learning/containment_contrastive.py`** is
**`containment-contrastive-linear-v1`**: D5's exact fit rule, solver, tie-break and abstention
over seven relational channels — the six sealed v2 scalars plus the containment share — with
the embedding dropped entirely. Fitted on the released 720-row pool it scores 0.94 / 0.84,
and the D6 admission protocol simulated exactly (bar from the conformal half at α = 0.20)
admits **46 with 0 errors: coverage 0.46 ≥ 0.40, CP-95 0.063 ≤ 0.15**, first choice over
admitted 1.00 > 0.62, 36 changed decisions projecting 47 ≥ 20. All nine amended §2.3
conditions clear on the corpus where the released class satisfied them at zero sweep points.

State: ruff clean, imports verified, the record sealed and reproducible. **No test module
exists yet, nothing is merged, and the simulated bar is discarded** — the class has seen only
spent evidence, and §6 prices what that is worth.

### 1.3 The immutable D6 stop, and what it licenses

`leak_budget_exceeded`, read with the sealed sweep, closed the confidence axis: a third bar
over the released margin is a sprint whose result is already on the record, and more corpus
to tighten α moves along a curve that misses everywhere. The D7 handoff's §4 licensed exactly
one experiment — the transfer measurement — and its decision rule opens the class question on
a collapse. The collapse is now measured. D7 varies the hypothesis class and nothing else:
same admission rule, same α, same ceiling, same floors, same corpus contract.

### 1.4 The carried and spent roles

`final_a` (30), `final_b` (30) and `canary` (5) are carried **unopened for the fifth sprint
running**: zero bodies resolved, digests recomputed unchanged in D6's W0. D7 spends them in
W3 if and only if selection passes. Spent: the 180-group fitting pool (its licensed role is
fitting — the new class fits there), D5's 100 calibration decisions (spent twice: as D5's
calibration, then as D6's bar-setting half), and **D6's 100 certification decisions, spent by
publication and demotable to exactly one further role: D7's bar-setting half** (§2.2a). The
retrieval pool is inherited, untouched.

---

## 2. The blocking fact, and the three decisions in front of this sprint

### 2.1 What is proven infeasible, and what is licensed instead

D6 proved the amended pair unreachable **for the released class**: over 200 published sweep
points, no threshold reaches C at the floor, and the deepest error-free prefix is 6. The
groundwork proves the same pair reachable **for the containment class** on the same spent
evidence, with 4.3× slack under the ceiling and the error-free prefix at 46. The gate was
never the obstacle; the margin was. D7 therefore asks for **no relaxation, no second
amendment, no new α** — it swaps the class under the frozen rule, which is the one move the
programme's own refusals leave open, and the one §4's measured collapse licenses.

### 2.2 The three W0 governance decisions, none of which moves a threshold

**(a) The conformal-half demotion ruling.** The bar-setting half and the certified half must
share no fitted vector, and §2.3 requires 100 independent decisions in the measured set, so
D7 must author its certification corpus and take its bar-setting half from spent evidence —
the same one-step demotion D6 applied to D5's calibration half. The natural candidate is
**D6's 100 certification decisions, re-scored under the sealed v3 direction, never
re-executed**. D5's calibration half is the alternative, but it is twice-spent and, under the
new class, carries only ~6 wrong decisions — too few for a meaningful quantile (§3.2). The
ruling names the half, binds it by matrix hash, and states that a demoted half may set a
threshold and may never certify.

**(b) The ladder ruling.** The containment ordering is deterministic, so it is a legitimate
candidate sixth rung for the frozen five-rung ladder. The trade is priced openly rather than
left implicit: *without* the rung, the strongest baseline on D6-shaped corpora is
`lexical_similarity` ≈ 0.62 and the diagnostic clears every comparison with room; *with* the
rung, the baseline the class must beat over admitted decisions rises to the containment
rate itself (0.84 on D6's corpus — the diagnostic still clears it at 1.00 over admitted), and
**the changed-decisions conditions re-pair against the containment-first order, a count the
groundwork did not measure**. W2 measures it either way and reports both pairings; the ruling
decides which one §2.3 reads. Refusing the rung is legitimate; deciding it after seeing W2's
numbers is not, which is why it is a W0 item.

**(c) `CorrectionFeatureContractV3` and revision 7.** The seven-channel allowlist, the class
name, λ = 1, α = 0.20 and the single cell are frozen in the pre-registration with
`measured_values: 0`, before the corpus exists — deliberately not frozen next to the
diagnostic that motivated them. The contract states the two channel rules the class inherits:
within-group source-to-source relations are admissible, source-to-requirement relations are
banned (the v2 cosine lesson), and the containment share carries no clip-and-scale envelope
because it is in [0, 1] by construction.

**Also in the same W0 session: the condition-24 inheritance ruling**, renewed on D6's exact
form — D7 authors no retrieval group, opens no arm and changes neither surface nor
comparator, so the three voiding identities are recomputed at gate close and D5's sealed
measurement is inherited rather than re-purchased for 60 authored groups.

**If any ruling is refused, the sprint stops before W1** with the typed ending §3.4 gives it;
a refused ruling is a legitimate outcome, not a blocker to argue with.

### 2.3 The selection rule, verbatim from D6

Selection requires all of (thresholds unchanged, only the class under them is new):

- at least **100 independent** clean ranking decisions in the fresh certification set;
- admission by the **split-conformal bar at α = 0.20**, and **CP-95 upper bound ≤ 0.15** on
  the error rate among admitted independent decisions;
- clean coverage at least **0.40**, projecting at least **20 changed decisions** over the 60
  final groups under the pairing §2.2b's ruling fixes;
- clean first-choice rate over admitted decisions strictly above the strongest deterministic
  baseline on the same decisions, on the ladder the ruling fixes;
- at least one changed clean decision;
- **100% first-action preservation** on the invariance-regression sample;
- every cell and sweep point reported, filtered and abstaining ones included;
- maximum inference within the **250 ms** budget (the class needs 7 multiplications; the
  budget is inherited, not renegotiated).

### 2.4 The 29 conditions

| Conditions | D6 state | What D7 does |
|---|---|---|
| 1–3 | met | re-evidence against D7's authorities: D6 release verified live, predecessor stores fingerprinted unchanged, carried roles audited unopened |
| 4 | met | publish **revision 7** with `measured_values: 0`, carrying the three §2.2 rulings and `CorrectionFeatureContractV3` |
| 5–9 | met | re-evidence on the fresh certification corpus: verifier labels, seven-channel surface scans, nine-role disjointness, volumes, zero `REAL_GOVERNED_RUN` |
| 10, 11, 13 | not opened | final A and B on the carried roles, 120 outcomes each over 30 groups — opened only by a pass through §2.3 |
| 12, 17 | met | the ladder (five or six rungs per §2.2b) and the one cell with every sweep point; every rate over the independent denominator |
| 14, 16 | not opened | the selected candidate's final-evidence gain and per-batch direction |
| 15, 18–23 | not opened | bootstrap, safety, retention, promotion metamorphic, shadow, v3 artifact bound to the *new* conformal point, resolver reason codes |
| 24 | met | inherited under the renewed ruling; three voiding identities recomputed at gate close |
| 25–27 | not opened | canary manifest, human approval, kill switch on the real activation |
| 28, 29 | met | full release matrix, protected release, exact-head CI, tag, remote verification |

---

## 3. Revision-7 pre-registration

### 3.1 The single candidate

One cell: **`containment-contrastive-linear-v1`, fitted once on the released 720-row /
180-group pool, λ = 1, margin floor 0**. Unlike D6, the direction does not pre-exist — W2
fits it once, seals it by content hash, and reproduces the fit across a process restart
before anything reads it (deterministic Newton on a strictly convex objective, sorted group
order; the groundwork's fit is the reference: AST scalar ≈ 5.75, containment ≈ 4.70,
everything else near zero, and W2 must reproduce the groundwork's sealed model hash or stop
on a determinism defect). No volume ladder — D5 answered volume and nothing since has reopened
it. The released 390-channel directions are not re-scored: they are a different class, their
sweep is published, and re-reporting them would be motion without information.

### 3.2 α = 0.20 under the demoted half, and why the value carries over

α is the leak budget, unchanged from the amendment that introduced it. What changes is the
half it is derived from: under the sealed v3 direction the demoted D6 half carries
**m ≈ 16** wrong decisions (the groundwork's measured 0.84; the in-wave m is whatever the
sealed re-scoring finds). The finite-sample rank `ceil((1−α)(m+1))` at m = 16:

| α | rank | wrong margins above the bar | meaning |
|---|---|---|---|
| 0.05 | 17 | — | no quantile; 16 errors cannot support a 95% bar |
| 0.10 | 16 | 0 | the bar *is* the largest wrong margin — the prefix rule again |
| 0.15 | 15 | 1 | |
| **0.20** | **14** | **2** | the same α, now a genuine quantile two errors deep |
| 0.25 | 13 | 3 | |

Any α below 2/17 ≈ 0.118 reproduces the zero-error prefix rule. 0.20 needs no re-derivation
and no argument beyond the one that chose it: it is carried, not re-chosen, and
`alpha_may_be_rechosen: false` stays in force. Note the degeneracy the demotion ruling
avoids: under the new class D5's calibration half has ~6 wrong decisions, where α = 0.20
collapses back onto the prefix rule (rank 6 of 6) — a bar with no conformal content.

### 3.3 C = 0.15, and what the design expects against it

Unchanged. At the diagnostic's 46 admitted, the ceiling accommodates **two** errors
(CP-95: 0 → 0.063, 1 → 0.099, 2 → 0.131, 3 → 0.160) against a groundwork observation of
zero. The design expects to clear it and can genuinely fail it — three admitted errors on
fresh evidence breach the ceiling. That is the right amount of exposure for a class whose
diagnostic was, unavoidably, read off spent corpora.

### 3.4 Decision tree, evaluated once, on the fresh certification set only

0. **A §2.2 ruling is refused** → stop `successor_contract_refused`. The class question
   cannot be posed under the frozen gate; the record states which ruling and why.
1. **All nine §2.3 conditions hold** → select, bind the v3 artifact to the new conformal
   point, run W3's lifecycle to the end, close the gate, unblock 22A.
2. **Coverage ≥ 0.40, CP-95 > 0.15** → stop `leak_budget_exceeded`. Now read against the
   sealed transfer record: the class transferred on two spent corpora and failed on unread
   evidence, which is the exchangeability symptom §6 names — the successor question is
   authoring-run drift, not another class, and the sealed per-family rates say where.
3. **Coverage < 0.40 at α = 0.20** → stop `margin_coverage_bound`. The class ranks but its
   margin does not concentrate errors on unread evidence; the containment *rung* result
   decides whether the signal or the fit is what failed.
4. **First choice over admitted not above the ruling's baseline** → stop
   `baseline_not_beaten`. Only reachable if §2.2b seats the containment rung and the fitted
   class cannot outrank its own strongest channel on fresh evidence — which would itself be
   the finding that the other six channels add nothing.
5. **Any invariance-regression flip** → stop `invariance_violated`, and the flip names its
   channel: the containment share cannot move under the six cases by construction, so a flip
   indicts the scalar half or the assembly, not the signal.

A stop at 2–5 leaves the gate at 14–15 met and 22A blocked, and D7 releases negative under
`sprint-21d7-evidence-baseline`, exactly as D4, D5 and D6 did.

### 3.5 Explicitly out of scope

- any Gate L2 or D1 threshold: α, C, the coverage floor, the changed-decisions floor, the
  inference budget and every §2.3 sentence stay as D6 left them; **a second amendment is
  refused in advance**;
- any change to the released `correction-ranking-v2` encoder, the alpha-normaliser, the 390
  channels, either sealed direction, or the released `pairwise-contrastive-linear-v1` class;
- any source-to-requirement channel, under any name — the rename cases move that relation
  and the ban is structural, not stylistic;
- a second fitted class, a volume ladder, a second λ, a second α, a second derivation of the
  bar, or any re-pairing of the halves after W0;
- opening `final_a`, `final_b` or `canary` before a §2.3 pass; opening the promotion
  submanifest's decisions before condition 20's own precondition is met;
- authoring beyond the 100 certification groups (plus the W1 withdrawal allowance §4.1
  prices) — no retrieval groups under the renewed ruling.

---

## 4. Corpora — the one wave that costs money

### 4.1 What must be authored, and what must not

**Certification set: 100 freshly authored groups / 400 outcomes**, under the unchanged D4
authoring contract — the only authoring D7 needs. The reason is D6's arithmetic verbatim:
the halves must share no fitted vector and §2.3 counts 100 independent decisions in the
measured set, so spent evidence cannot certify. Budget the known corpus risks *inside* the
wave: the saturation heuristic's withdrawal rate rises monotonically with the 626+ released
groups now occupying the space (D6 recorded four withdrawals; plan for the pre-check plus
5–10 spare authorings), and the two defect patterns only execution reveals — a hidden test
probing one defect under two descriptions, and a baseline failing its own visible suite —
get the same in-wave fix discipline as every prior corpus wave.

**Bar-setting half: D6's 100 certification decisions, re-scored under the sealed v3
direction, never re-executed** — per §2.2a's ruling, rebuilt from the released matrix bytes
and proved against the published hash `747eb9664bbcfd3b…` before a single margin is read.

**Invariance sample: 20 groups / 40 transformed decisions** from the fresh corpus, under the
released six-case generator, seeds allocated in D7's own range. **Promotion submanifest: 120
nominal / 60 independent decisions** over the carried final roles, sealed unopened as always.

**Not** a v3 re-encoding of any spent corpus beyond the containment shares the demoted half
needs (the six scalars are already sealed per candidate; the shares are derived from released
sources at re-scoring time and bound into the record).

### 4.2 Feature seals for the fresh corpus

The fresh candidates are encoded once, pre-outcome, exactly as D6's were — the released v2
encoder under D5's inherited clip-and-scale bounds — and the v3 relational vector is
assembled per group beside them: six sealed scalars unchanged, one derived share, sealed
under `CorrectionFeatureContractV3` with the campaign manifest hash and the chronology proof.
The MiniLM embedding is still computed and sealed for the v2 record's completeness (the scans
and the census read it), but **no v3 channel reads it** — the seal must make both facts
checkable.

---

## 5. Execution waves

| Wave | Work | Conditions |
|---|---|---|
| **W0** | Test and merge the groundwork: unit tests for the three new modules (fit determinism against the groundwork's sealed model hash, the 600-case invariance golden, CP-bound reproduction, transfer-record round-trip), mypy/ruff/CI, protected-main PR. Verify the D6 release from live handles; fingerprint every predecessor store; audit the carried roles unopened. Obtain the three §2.2 rulings and the condition-24 renewal; publish revision 7 with `measured_values: 0` | 1, 2, 3, 4 |
| **W1** | Vertical slice first (§5.1). Then author and execute the 100-group / 400-outcome certification corpus in D7's own isolated store pair under new run identities; hidden-verifier labels; v2 seals plus v3 relational assembly (§4.2); surface scans; nine-role separation proof | 5, 6, 7, 8, 9 |
| **W2** ✅ **closed — `1_select`** | **Step 0, before any fresh decision is scored:** act on the sealed pre-flight (§5.3) — obtain the disjointness-reading clarification, the baseline-reading clarification, and the gate owner's knowing decision on the seated pairing's measured zero-changed estimate. Then: fit the v3 direction once on the released 720-row pool, seal it, reproduce it across a process restart (it must reproduce `d80160c4aa795fad…`); seal the §4 transfer-gap record as W-stage evidence; run the v3 relational separation scan (`relational_scans.py`) beside the released v2 scans and seal both; measure the seated six-rung ladder on the fresh corpus, both changed-decision pairings reported; re-score the demoted half, derive the conformal bar **once**, reproduce it across restart; score the certification cell; report every sweep point; run the invariance regression; evaluate the amended §2.3; select or stop. **Done, with one deviation the record states: the ladder measured is the *five released rungs*, because S21D7-027 superseded S21D7-011 and unseated the containment rung before any decision was scored; the containment ordering is reported beside them as an unseated measurement.** Ending `1_select`, no condition failed, no threshold moved | 12, 17 |
| **W3** | Only on a pass: v3 artifact bound to the new conformal point; loader, resolver, sequencer against the real artifact; **open the carried roles** — final A and B, 120 outcomes each over 30 groups; paired bootstrap; safety and retention; promotion metamorphic inside the admission budget; shadow; canary manifest, human approval, kill switch; activation, restart survival, deliberate rollback | 10, 11, 13–16, 18–23, 25–27 |
| **W4** | Full release matrix; protected release, exact-head CI, annotated tag, remote verification; gate assessment (`scripts/gate_assessment_d7.py`, counts-derived verdict, stop-hash-bound rows on a stop); Gate D1 6, 7 from final surface evidence and 15 by the renewed inheritance; report and handoff | 28, 29 |

### 5.1 The first vertical slice

Before W1 authors 100 groups, run **one** fixture group end to end: v3 assembly →
seven-channel fit on fixture pairs → bar derivation from a fixture half → artifact binding →
loader round-trip. D4 found its typed-null defect in a slice, D5 its canonical-hash defect,
D6 its store-guard duplication; the slice is where this sprint's version of that defect is
cheapest. The one new seam to probe hard: `relational_numbers` refusing drifted scalar names,
and the assembly's behaviour on a pure-deletion group (every share zero, tie-break to the
frozen order).

### 5.2 The three schedule risks, named

**W3 is still the sprint.** Roughly 3,100 lines of artifact, runtime, sequencer, promotion
and lifecycle code have unit tests and goldens and have **never been driven by a fitted
model** — D4, D5 and D6 all stopped before reaching them. If §2.3 passes, W3 inherits four
sprints of deferred integration risk at once. Budget it as the wave that will find defects.

**W1's authoring saturation.** Retention was 8–10 per authored 10 with the pre-check at D6's
occupancy; D7 authors into a strictly fuller space, and the pre-check cannot see saturated
primitives (the D6 W1 lesson). Expect withdrawals; the allowance is priced in §4.1.

**W2's determinism seam.** The direction is fitted in-wave for the first time since D5.
The groundwork's sealed model hash is the cross-check; a W2 fit that does not reproduce it
bit-for-bit on the same pool is a stop-worthy defect in the environment, not a number to
shrug at (BLAS variance was the W2-D9 lesson — hashes are compared, fits are not repeated).
The pre-flight has already reproduced it once on this environment.

### 5.3 The W2 pre-flight — two facts the W1 bytes decide, disclosed before the bar

Between W1 and W2, the sealed bytes were read for two questions the plan had left to W2 to
answer implicitly, and both answers arrived early enough to matter. The record is
[`sprint-21d7-w2-preflight.json`](evidence/sprint-21d7-w2-preflight.json), produced by
`scripts/w2_preflight_d7.py` in the demotion ruling's own discipline — recomputation from
sealed bytes, `d7_certification_decisions_scored: 0`, the D7 campaign record never opened,
no bar derived, nothing on the fresh corpus scored or ladder-measured.

**Fact one — the frozen disjointness sentence is false at the level the class lives, and
clean at the level it leaks.** `corpus_roles` froze "no fitted vector may appear in both
halves" — a sentence written for the 390-channel representation, where distinct sources
never collide. The v3 representation is seven numbers, and seven numbers alias: **eleven
relational vectors appear in both the certification half and the demoted bar-setting half**
(13 certification groups touched; 23 more alias against the fitting pool). The two
properties the sentence exists for both hold across every half pair — **zero shared
decision signatures, zero shared canonical sources** — and the independent-decision count
is exactly 100 per half. `relational_scans.py` is the scan that separates the two readings
permanently; W2 runs it beside the v2 scans and seals it. What W2 needs from the gate owner
first: a clarification binding the sentence to the leakage properties, with aliasing
reported — a reading of a frozen sentence, not a threshold change, and it must predate the
first scored decision or the wave's own record would carry a claim its bytes falsify.

**Fact two — under the seated pairing, the measured design estimate of changed decisions is
zero.** On both spent corpora the fitted class agrees with the containment rung on **every
decision in its top-margin range** (top-40/46/50 alike; disagreements — 14 and 11 of 100 —
all sit at low margins). The §2.3 conditions that read the changed count against the seated
ladder's strongest rung are therefore on course to fail regardless of the admission numbers,
and the baseline condition splits into two readings exactly here: admitted-rate against the
rung's *whole-corpus* rate can pass on numbers where admitted-rate against the rung's rate
*on the admitted subset* cannot, because agreement makes the latter two identical. D6's cell
never had to distinguish them; this cell will. The pre-flight asks the gate owner for two
decisions before W2 scores anything: **fix the baseline condition's reading**, and **decide
the seated pairing's consequence knowingly** — proceed to a probable
`baseline_not_beaten` negative that would close the class question with a sealed record, or
supersede the ladder ruling while the chronology still proves no fresh decision has been
read. Both are legitimate; the pre-flight record deliberately argues for neither.

---

## 6. Risks the evidence cannot retire

**The class was found after reading D6's published evidence.** The diagnostic is selection on
spent corpora, however principled the signal's derivation from the frozen anatomy is. The
controls: the construction is licensed by the corpus contract rather than by the corpus, its
transfer is measured across two independent authoring runs, every threshold it must clear was
frozen before it existed — and the fresh certification is read once. The 46-with-zero-errors
diagnostic is an upper bound on hope, exactly as D5's 0.32-below-the-floor was a lower one.

**Exchangeability, one pairing over.** The conformal guarantee now needs D6's certification
groups and D7's fresh groups exchangeable. Same contract, same generator, same families — and
one more authoring run of drift than the pairing D6's §6 flagged and then measured as the
0.41 → 0.62 lexical shift. The sealed per-family transfer record is the instrument: a
coverage far from the design's ~0.46, or a family profile unlike either spent corpus, is the
symptom, and step 2 of §3.4 is typed for it.

**The anatomy is load-bearing.** The containment signal reads the two-complete-two-partial
structure the authoring contract froze. A future corpus contract that varies candidate count
or repair completeness dissolves the signal by design — acceptable inside Sprint 21's frozen
contract, and stated here so 22A's domain expansion prices it rather than inheriting it as an
assumption.

**The class and its baseline are the same signal at admissible margins.** §5.3's fact two,
stated as the risk it is: the fitted direction is dominated by the AST scalar and the
containment share, so where its margin is large it reproduces the containment-first order
exactly. Under the seated ladder the learned component's admissible value-add over its own
strongest channel is measured at zero on both spent corpora. If that holds on the fresh
corpus, the honest finding is that the class question resolved into a *deterministic*
discovery — the rung, not the direction, is the product — and Gate L2's "useful learned
activation" does not close over it. The pre-flight puts that choice in front of the gate
owner while it is still a design decision rather than a post-hoc reading.

**Representational aliasing is a property of every seven-channel corpus.** The v3 code will
alias within and across any two corpora of this size; the pre-flight counts it (11 across
the operative halves, 14 groups with a within-group alias whose worst case is a permanent
zero margin). The leakage-level properties are what the scans must keep proving; the
aliasing counts bound reachable coverage from above and belong in every W2+ record rather
than in a reviewer's post-hoc discovery.

---

## 7. Definition of done

**On a pass:** 29 of 29 conditions met, a real seven-channel component fitted, selected,
bound, promoted, shadowed, canaried, approved by a human, activated and rolled back once on
purpose; the success tag `sprint-21-learning-baseline` created after exact-head CI; Gate D1
conditions 6 and 7 closed from final surface evidence and 15 by the renewed inheritance;
**Sprint 22A unblocked**, inheriting a live selection surface, an admission rule with a
stated bounded error budget, and a transfer record that says why this class and not the last.

**On a stop:** the typed stop from §3.4, the not-opened conditions closed against its hash,
a negative release under `sprint-21d7-evidence-baseline`, and a handoff that names one
successor experiment and refuses the rest — the discipline D3 through D6 each kept, with one
asset none of them had: a sealed measurement separating what the ranker is from what the
corpus gap is.
