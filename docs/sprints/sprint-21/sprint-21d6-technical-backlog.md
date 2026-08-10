# Sprint 21D6 Technical Backlog

## Split-Conformal Admission, the §2.3 Admission Amendment, and Gate L2 Closure

- Predecessor: Sprint 21D5, tag `sprint-21d5-evidence-baseline`, object
  `799190c06497f22edd6ec6c1eb690c511ce23bb7`, peeling to
  `53cd7579096537cd1cef0e060335ad1c98088285`; PR `#225` and `#226`; exact-head post-merge `main`
  CI run `31328614887`, 30 of 30 success.
- Groundwork written and verified, **not yet merged**: `conformal_operating_point.py` and its
  41-assertion test module — see §1.2.
- Gate contract: `9e47bc618fc1eca8b66146eacdf1bd244fced79bb1c91f46f2c6ff4484bfd8a7`, 29 conditions.
  **D6 changes exactly one sentence of it**, and that change is the sprint's first gate — see §2.
- Migration head: `0015`. D6 allocates none; `0016` stays unallocated unless W3's activation path
  turns out to need a store, which would be a defect finding, not a plan item.
- Outcome tags: success `sprint-21-learning-baseline`; negative `sprint-21d6-evidence-baseline`.

**This backlog is half the size of D5's, and the reason is that D6 authors one corpus and runs
code that already exists.** The encoder, the class, the two fitted directions, the census, the
bound, the artifact, the loader, the resolver, the sequencer, promotion, shadow, canary,
activation and rollback are all released. D6 adds one module — already written — and is otherwise
a measurement sprint with a governance decision in front of it.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](sprint-21d4-technical-backlog.md) are D6's execution contract
unchanged, incorporated by reference: the release-grade meaning of "done", the wave discipline,
the evidence-record shape, and the rule that a wave's defects are fixed inside the wave.

---

## 1. Verified starting state

### 1.1 What D5 released

Gate L2 at **14 met, 15 not opened, 0 failed**. The fifteen closed behind one typed stop,
`selective_margin_bound`, hash
`7b59897d8d83a51be3d8fb5c65e4208ddb07d813884eb99ccdb36b73236fec59`. Nothing was registered,
approved or activated: `component_state` is zero across the board, and no final or canary outcome
was ever inspected.

### 1.2 The groundwork, and what verifying it found

`src/cognitive_os/learning/conformal_operating_point.py` implements the successor admission rule
the D5 handoff named: `ConformalOperatingPointV5`, `derive_conformal_point`, `conformal_rank` and
`admitted_error_upper_bound`. It keeps the four refusals of the rule it replaces — calibration
only, one derivation, disjoint halves, independent decisions only — and adds two the prefix rule
never needed: no errors in the conformal half is *no quantile* rather than admit-everything, and a
finite-sample rank that exceeds its sample is recorded rather than silently clamped.

Reviewing it before planning on it found two defects, both now fixed:

1. **The module never said what α bounds.** The quantile is taken over the margins of *errors*, so
   the guarantee is P(admitted | wrong) ≤ α — a leak rate, the share of the ranker's mistakes that
   reach the caller. That is *not* the share of admitted decisions that are wrong, which is
   smaller by roughly the error rate over the coverage and is the quantity §2.3 reads. A reader
   who conflated them would have written the amendment in §2 against the wrong number. Both
   readings are now stated in the module docstring and in `derivation_reading`, which means they
   land in the stored bytes, together with the exchangeability assumption the guarantee rests on.
2. **`admitted_error_upper_bound` took a significance parameter no caller sets**, while the
   contract field it feeds is named `error_upper_bound_95`. A caller passing `alpha=0.10` would
   have stored a 90% bound under a name claiming 95. The parameter is deleted; 95% is now a
   property of the function, as the field name always claimed. The same pass dropped a redundant
   `errors == admitted` branch (the bisection already returns exactly 1.0 there, verified) and cut
   the iteration count from 200 to 60, which agrees bit for bit over every k < n ≤ 120.

`admitted_error_upper_bound(0, n)` reproduces the sealed `zero_error_upper_bound(n)` exactly, so
the two admission rules state their claims on one scale — the property §2 leans on.

State: 41 assertions pass, mypy clean, ruff clean, the full learning suite (1078 tests) unaffected.
**No number has been derived from D5's margins with it, deliberately** — α belongs in a
pre-registration, not in a measurement that has already seen what it needs to beat.

### 1.3 The immutable D5 stop, and what it licenses

`selective_margin_bound` licenses exactly one successor experiment: a different confidence
construction over the same ranker. Not a different ranker (0.91 first-choice), not a third
hypothesis class, not a larger corpus (0.26 → 0.27 across 2.25× volume). D6 varies the admission
rule and nothing else.

### 1.4 The carried roles

`final_a` (30), `final_b` (30) and `canary` (5) are carried from D4's seal **unopened**: zero
bodies resolved, decision `reuse`, digests recomputed unchanged in D5's W1. D6 spends them in W3.
The 180-group fitting pool and D5's 100 calibration groups are spent; the seven-role separation
proof covers 465 groups with all 21 role pairs disjoint.

---

## 2. The blocking fact, and the one contract decision in front of this sprint

### 2.1 Zero confident errors and coverage ≥ 0.40 are not jointly satisfiable, and D5 proved it

§2.3 requires *both* "exactly zero confident errors among admitted decisions" *and* "clean
coverage at least 0.40". D5's sealed risk-coverage sweep — 100 points per cell, in
`sprint-21d5-learner-selection.json` — prices that pair exactly. Reading the best coverage
available at each error count:

| Admitted errors | 720-row direction `9fd297fb…` | 320-row direction `5b15f4af…` |
|---|---|---|
| 0 | 27 admitted, coverage **0.27**, CP-95 ≤ 0.105 | 26 admitted, coverage **0.26**, CP-95 ≤ 0.109 |
| 1 | 58 admitted, coverage **0.58**, CP-95 ≤ 0.079 | 32 admitted, coverage 0.32, CP-95 ≤ 0.140 |
| 2 | 67 admitted, coverage 0.67, CP-95 ≤ 0.091 | 45 admitted, coverage **0.45**, CP-95 ≤ 0.133 |
| 3 | 73 admitted, coverage 0.73, CP-95 ≤ 0.103 | 62 admitted, coverage 0.62, CP-95 ≤ 0.120 |

Two facts fall out, and they are the whole sprint:

**The floor is unreachable at zero errors.** Not by a little: 0.27 against 0.40, on both cells, at
volumes 2.25× apart. No admission rule fixes this, because the constraint is on the ranker's error
placement, not on how the bar is chosen. A rule that admits no error admits at most 27 of 100.

**One tolerated error buys 31 coverage points.** At 720 the first two errors are 30 correct
decisions apart in the margin ordering, so a bar that tolerates one error admits 58 rather than
27 — and the Clopper–Pearson upper bound on its true error rate is **0.079, lower than the
0.105 the zero-error point itself carries**, because 58 decisions is more evidence than 27.

That last line is the argument for the amendment, and it is worth stating without hedging:
**§2.3's "exactly zero confident errors" never bought a zero error rate.** At D5's coverage it
bought an upper bound of 10.5%. A rule admitting one error in 58 bounds the same quantity at 7.9%
with 2.2× the coverage. The zero is a property of a small sample, not a safety property.

### 2.2 The amendment, and why it is a governance decision and not a sprint's own edit

Every sprint since D3 has declared "changing any Gate L2 threshold" out of scope, and D6 does not
get to exempt itself. §2.3's admission clause is a gate threshold. Changing it is a **revision of
the gate contract, taken by the gate owner, before any D6 measurement exists** — which is exactly
the form the D5 handoff demanded ("a contract change rather than a threshold relaxation… Do not
run split-conformal and then argue that its α is what zero always meant").

The proposed change is one clause. Everything else in §2.3 stays verbatim.

> **Struck:** exactly **zero confident errors** among admitted independent calibration decisions.
>
> **Replaced by:** admission is a **split-conformal bar at the pre-registered α**, and the
> Clopper–Pearson one-sided 95% upper bound on the error rate among admitted independent
> calibration decisions is at most the pre-registered ceiling **C**.

The amendment record follows the shape D4's amendment 1 already established
(`sprint-21d4-contracts-amendment-1.json`): bound to the unchanged hash of the sealed original,
carrying the digest of the operative sentence, and carrying a chronology proving zero D6
measurements existed when it was signed. What it must additionally carry, because this one
relaxes rather than clarifies: the §2.1 table as its justification, and the explicit statement
that the pre-amendment pair was infeasible rather than merely unmet.

**If the gate owner refuses the amendment, D6 does not run.** That is a legitimate outcome and
§3.4 types it.

### 2.3 The amended selection rule

Selection requires all of:

- at least **100 independent** clean ranking decisions in the fresh certification set;
- admission by the **split-conformal bar at α = 0.20**, and **CP-95 upper bound ≤ 0.15** on the
  error rate among admitted independent decisions *(the amended clause)*;
- clean coverage at least **0.40**, high enough to project at least **20 changed decisions** over
  the 60 final groups;
- clean first-choice rate over admitted decisions strictly above the strongest deterministic
  baseline on the same decisions;
- at least one changed clean decision;
- **100% first-action preservation** on the invariance-regression sample;
- every cell and sweep point reported, including filtered and fully abstaining ones;
- maximum inference within the **250 ms** budget.

### 2.4 The 29 conditions

| Conditions | D5 state | What D6 does |
|---|---|---|
| 1–3 | met | re-evidence against D6's authorities: D5 release verified live, predecessor stores unchanged, carried roles audited unopened |
| 4 | met | publish **revision 6** and the §2.3 amendment with `measured_values: 0` |
| 5–9 | met | re-evidence on the fresh certification corpus: verifier labels, surface scans, eight-role disjointness, volumes, zero `REAL_GOVERNED_RUN` |
| 10, 11, 13 | not opened | final A and B on the carried roles, 120 outcomes each over 30 groups |
| 12, 17 | met | both cells and all sweep points reported; every rate over the independent denominator |
| 14, 16 | not opened | the selected candidate and the v3 artifact bound to the conformal point |
| 15, 18–23 | not opened | loader, resolver, sequencer, promotion, shadow, real-artifact measurement |
| 24 | met | see §4.1 — the one condition whose re-evidencing D6 should ask to be excused from |
| 25–27 | not opened | canary manifest, approval, kill switch on the real activation |
| 28, 29 | met | full release matrix, protected release, exact-head CI, tag, remote verification |

---

## 3. Revision-6 pre-registration

### 3.1 The single candidate

One cell, pre-registered before the corpus exists: the **720-row direction
`9fd297fb407015374485e8f7ef8fbb557e6f89f7ac3286e2572769fdab937d74`**, unrefitted, out of D5's
sealed matrices, rehashed on load. The 320-row direction is re-scored and **reported** — §2.3
requires every point reported — but is **not selectable**. One class, one λ, one direction, one α:
there is nothing to search over, which is the property that makes a single derivation meaningful.

Chosen a priori as the larger fit, on a question D5 answered: coverage moved one point across a
2.25× span, so there is no volume slope to exploit and no reason to prefer the smaller fit. It is
also, visibly in §2.1's table, the cell that can clear the floor — which is a reason to state the
choice openly rather than to launder it, and a reason the pass/fail decision happens on evidence
neither this document nor D5 has read.

### 3.2 α = 0.20, and why no smaller value is even meaningful

α is a **leak budget**: at most one in five of the ranker's errors may clear its own bar. With the
720 cell's **m = 12** wrong answered decisions, the finite-sample rank `ceil((1−α)(m+1))` maps α
onto integers, and the map is coarse and fully determined by the sealed m:

| α | rank | wrong margins above the bar | meaning |
|---|---|---|---|
| 0.05 | 13 | — | no quantile exists; 12 errors cannot support a 95% bar (needs m ≥ 19) |
| 0.10, 0.15 | 12 | 0 | the bar *is* the largest wrong margin — the prefix rule D5 stopped on, coverage 0.27 |
| **0.20** | **11** | **1** | the first α whose bar is not the failed rule |
| 0.25, 0.30 | 10 | 2 | |
| 0.40 | 8 | 4 | |

Any α below **2/13 = 0.1538** reproduces the rule the sprint exists to replace. 0.20 is the
smallest round value above that floor. This is a power argument computed from D5's *published*
aggregate, and it is design input, not a result.

### 3.3 C = 0.15, and what it is measured against

The ceiling is the Clopper–Pearson 95% upper bound on the error rate among admitted decisions.
At the ~58 admitted the design expects, the bound reads: 1 error → 0.079, 2 → 0.105, 3 → 0.128,
**4 → 0.151**. So C = 0.15 accommodates up to three admitted errors at that coverage, against an
expectation of ~2.4 (α × 12 errors per 100 decisions), leaving roughly one error of slack. It is a
ceiling the design expects to clear and can genuinely fail — which is the point of pre-registering
it. Compare what it replaces: 10.5% at coverage 0.27.

### 3.4 Decision tree, evaluated once, on the fresh certification set only

0. **The amendment is refused** → stop `admission_contract_refused`. Gate L2 is unclosable with
   this ranker at these volumes and §2.1 is the proof; the successor question moves off the
   confidence axis entirely.
1. **All eight §2.3 conditions hold** → select, bind the artifact, run the lifecycle, close the
   gate, unblock 22A.
2. **Coverage ≥ 0.40, CP-95 > 0.15** → stop `leak_budget_exceeded`. The bar held its leak
   guarantee and the admitted precision still missed. A tighter α needs more wrong decisions in
   the conformal half than 12, which is a corpus-volume question — the first time this programme
   would have a measured reason to author more.
3. **Coverage < 0.40 at the pre-registered α** → stop `margin_coverage_bound`. The margin does not
   concentrate the ranker's errors at low margins on unread evidence. The confidence construction
   has then been varied twice and failed twice, and the next axis is §3.3 step 6,
   `hypothesis_class_bound` — where D4 landed, now with a much narrower question.
4. **The quantile does not exist** → unreachable by construction (m = 12 is sealed and 12 ≥ 11),
   and if it happens the derivation is wrong, not the evidence.

A stop at 2 or 3 leaves the gate at 14–15 met and 22A blocked, and D6 releases negative under
`sprint-21d6-evidence-baseline`, exactly as D4 and D5 did.

### 3.5 Explicitly out of scope

- any change to `correction-ranking-v2`, the alpha-normaliser, the encoder, the 390 channels or
  the feature contract hash;
- refitting either direction, changing λ, the pairing rule, the margin definition or the
  abstention floor of 0;
- a third hypothesis class, a new ranker, a larger fitting pool;
- any Gate L2 or D1 threshold other than the single §2.3 admission clause §2.2 names;
- a second α, a second split, or a second derivation of the bar.

---

## 4. Corpora — the one wave that costs money

### 4.1 What must be authored, and what must not

**Certification set: 100 freshly authored groups / 400 outcomes.** This is the only authoring the
correction branch needs, and the D5 handoff's expectation that "W1 is not an authoring wave" holds
for the bar and fails for the measurement. The reason is arithmetic: the bar-setting half and the
certified half must share no fitted vector, §2.3 requires **100 independent decisions in the
measured set**, and D5 produced exactly 100. One hundred decisions cannot be both halves.

**Bar-setting (conformal) half: D5's 100 spent calibration decisions, re-scored, not re-executed.**
This is the corpus lifecycle already in force — D4's calibration became D5's fitting pool — applied
one step further: a spent calibration role is demoted to threshold-setting, which is a fitting-like
use and never a certifying one. The wrong-margin list comes out of the sealed calibration matrix
`106061126df83261…` and the sealed direction, both of which rehash to their released digests.

**Not** the reverse assignment. Certifying on D5's set would put the gate's headline numbers on
evidence whose full sweep is published in this very document.

**Not** a 50/50 split of D5's set: 50 certified decisions fails §2.3's 100-decision condition, and
a second threshold relaxation is a worse trade than one authoring wave.

### 4.2 The retrieval condition, and the lazier alternative worth asking for

Condition 24 is met on D5's freshly authored retrieval holdout, and §2.2's standing rule — each
sprint re-evidences every condition against its own authorities — would cost D6 **60 more authored
groups yielding ≥50 queries**, for a surface D6 does not touch, does not fit and does not change.

**Recommendation: ask the gate owner, in the same W0 decision as the amendment, to rule condition
24 inherited from D5's sealed measurement for any sprint that changes neither the surface, the
arms nor the comparator** — with the D5 handoff's own caveat as the test of that condition. One
line of governance against 60 authored groups. If the ruling is refused, W1 authors them and the
sprint is one wave longer; nothing else in this plan moves.

---

## 5. Execution waves

| Wave | Work | Conditions |
|---|---|---|
| **W0** | Verify the D5 release from live handles; fingerprint every predecessor store; audit the carried roles unopened; obtain the §2.3 amendment and the condition-24 ruling; publish revision 6 with `measured_values: 0`; merge the conformal module | 1, 2, 3, 4 |
| **W1** | Author and execute the 100-group / 400-outcome certification corpus under new run identities; hidden-verifier labels; surface scans; eight-role separation; (retrieval corpus only if §4.2 is refused) | 5, 6, 7, 8, 9, (24) |
| **W2** | Re-derive the 12 wrong margins from the sealed matrices; derive the conformal bar **once**, reproduce it across a process restart; score both cells; report every sweep point; measure the amended §2.3; select or stop | 12, 14, 17 |
| **W3** | v3 artifact bound to the conformal point; loader, resolver, sequencer; final A and B on the carried roles; promotion, shadow; canary manifest, approval, kill switch; activation and rollback | 10, 11, 13, 15, 16, 18–23, 25–27 |
| **W4** | Full release matrix; protected release, exact-head CI, tag, remote verification; gate assessment; Gate D1 6, 7, 15; report and handoff | 28, 29 |

### 5.1 The first vertical slice

Before W1 authors 100 groups, run **one** group end to end through W2's derivation and W3's
artifact binding on fixture data. D4 found its typed-null defect this way and D5 found its
canonical-hash defect this way; both were cheap in a slice and expensive in a wave.

### 5.2 The two schedule risks, named

**W3 is the sprint.** Roughly 3,100 lines of artifact, runtime, sequencer, promotion and
lifecycle code have unit tests and goldens but have **never been driven by a fitted model**. D3
built them, D4 and D5 both stopped before reaching them. Budget W3 like D4 budgeted corpus
authoring — as a wave that will find defects, not as a wave that will confirm they are absent.

**W1's known defect patterns.** The 100-group shape has two failure modes that only execution
reveals; they are in the D4 corpus contract and D5 hit both. Budget for them inside the wave.

---

## 6. Risks the evidence cannot retire

**Exchangeability between the halves.** The conformal guarantee needs D5's calibration groups and
D6's fresh certification groups to be exchangeable. They come from the same authoring contract and
the same generator, which makes it plausible, not proven. It is stated in the record rather than
assumed silently, and a coverage far from the design's 0.58 is the symptom that would falsify it.

**α was chosen knowing what it buys on the bar-setting half.** §3.2 states the rationale in leak
terms and §3.1 states the cell choice openly. The control is that neither number is certified
until it is measured on 400 outcomes nobody has read.

**The CP bound reads the admitted set as a fixed-size sample.** The admitted set is selected by
margin, so this is the established convention of D4 and D5 rather than an exact conditional
statement. D6 changes nothing here; changing it would move every historical number.

---

## 7. Definition of done

**On a pass:** 29 of 29 conditions met, a real fitted component promoted, shadowed, canaried,
activated and rolled back once on purpose, the success tag `sprint-21-learning-baseline` created,
and §8.1's blocker on Sprint 22A discharged — 22A inherits a live selection surface and an
admission rule with a stated, bounded error budget, and its own objective (the data-driven domain
registry and its two pilot domains) becomes the only thing left in its way.

**On a stop:** the typed stop from §3.4, the fifteen conditions closed against its hash, a
negative release under `sprint-21d6-evidence-baseline`, and a handoff that names one successor
experiment and refuses the rest — the discipline D3, D4 and D5 each kept.
