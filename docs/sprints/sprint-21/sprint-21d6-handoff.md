# Sprint 21D6 handoff — what a selective margin bound requires next

Sprint 21D3 asked whether Sprint 21D2's invariance defect was representational or a capacity
residual and answered capacity. Sprint 21D4 asked whether the frozen k-NN could be made
**selective** and answered no, with zero-error coverage of exactly zero in all 144 cells. Sprint
21D5 asked the next question down: the k-NN's confidence was absolute neighbourhood acceptance
mass, which barely moves among four near-clones — so does a confidence built out of **within-group
contrast** separate the errors?

It does. And it does not separate enough of them.

Over 100 freshly authored independent calibration decisions, at two fitting volumes 2.25× apart,
the pairwise contrastive direction ranks at **0.91 and 0.88 first-choice** against a 0.42
deterministic baseline and certifies **0.26 and 0.27** zero-error coverage against a floor of
0.40, with **exactly zero confident errors** in what it admits. Both cells fail one of §2.3's
eight conditions and satisfy the other seven.

**Gate L2 does not pass. Sprint 22A remains blocked.** This handoff targets one bounded successor
and refuses three tempting others.

---

## 1. The stop is typed, and the type is the instruction

The §3.3 decision tree published four endings before any D5 number existed. D5 landed on **step
5, `selective_margin_bound`**, and the two neighbours were ruled out by measurement:

- **Not step 6, `hypothesis_class_bound`.** That is where D4 landed, and it means the confidence
  cannot separate errors at all. D5's coverage is above zero at both volumes. The class is not
  the problem.
- **Not step 4, `volume_bound`.** Coverage moved by one point across a 2.25× span. A corpus
  sprint would buy a slope that is not there.

What step 5 names is narrower than either: the direction ranks, and the **specific reduction of a
ranking to one scalar margin, admitted by a zero-error prefix rule, certifies too little of it.**

The sealed record says it in one sentence, and this handoff does not get to improve on it:

> a sprint that pre-registers a different confidence construction over this same ranker —
> split-conformal over the margin is the obvious candidate — and not a different ranker, not a
> third hypothesis class and not a larger corpus. The direction ranks; the margin is what cannot
> certify enough of what it ranks.

— `sprint-21d5-continuation.json`, stop hash
`7b59897d8d83a51be3d8fb5c65e4208ddb07d813884eb99ccdb36b73236fec59`.

## 2. The successor experiment, stated as a pre-registration

**Keep, unchanged and unrefitted:** the v2 encoder, its 390 channels, the alpha-normaliser, the
`pairwise-contrastive-linear-v1` class, λ = 1, the tie-break on the baseline order, and the two
directions D5 already fitted and sealed — `5b15f4af06a2b08d` at 320 rows and `9fd297fb40701537`
at 720. Refitting the direction would confound the one thing the sprint is changing.

**Change exactly one thing:** the map from a ranked group to an admit/abstain decision.

The zero-error prefix rule D4 and D5 both used takes the margin ordering, walks down it, and stops
at the first wrong decision — so one badly-placed error truncates everything below it. At 720 rows
the ordering would admit 50 of 100 decisions at the cost of a single error; the rule stops at 27
because the 28th is wrong. **A rule whose coverage is decided by the position of one error is a
rule with variance, not a bound.**

Split conformal replaces it with a quantile: hold out a calibration split, take the margin
distribution of the wrong decisions on it, and admit above the (1−α) quantile. What that buys is
a coverage that degrades smoothly with α rather than being hostage to one point, and a stated
error rate rather than a claimed zero. What it costs is that zero is no longer on the menu — and
that is the pre-registration's central question:

> **Is §2.3's "exactly zero confident errors" the right admission rule, or is a stated
> distribution-free bound at a pre-registered α the right one?**

That question has to be answered in the contract, before the measurement, and it is a contract
change rather than a threshold relaxation. Do not run split-conformal and then argue that its
α is what zero always meant.

**The measurement is already affordable.** The corpus exists, the campaigns are executed and
sealed, the matrices are scanned, and the directions are stored and rehash to their sealed hashes
out of a restored copy. A successor sprint's W1 is not an authoring wave; it is a re-derivation
over evidence D5 already produced.

## 3. Three things the stop does not license

**Not a different ranker.** The direction reaches 0.91 first-choice. A sprint that swaps it out
would be answering a question nobody asked and would lose the one comparison D5 makes cleanly.

**Not a third hypothesis class.** D4 tried k-NN, D5 tried a linear contrastive direction, and the
second fixed the defect the first was diagnosed with. A third class before the confidence
construction has been varied would be searching over the wrong axis.

**Not a larger corpus.** 0.26 → 0.27 across 2.25× volume. Author more groups only if a successor
measures a *slope* that D5's two points did not show.

## 4. What Sprint 21D6 inherits, and what it must not assume

**Inherits, usable without re-deriving:**

- the revision-5 counting rule and the operating-point spine —
  `DecisionCensusV4.from_feature_hashes`, `derive_zero_error_point` with its single-derivation
  `previous=` rule, and the Clopper–Pearson bound. None of it is specific to correction ranking;
- the 180-group fitting pool (720 outcomes) and D5's 100 calibration groups / 400 outcomes,
  authored, executed, sealed and role-disjoint;
- the two sealed directions and their fitted matrices, with the fit/calibration split proved
  group-disjoint;
- the **complete** searchable surface, and the retrieval result that closes Gate D1 condition 15;
- `CorrectionArtifactPayloadV3`, its loader and the v1/v2/v3 dispatch — released and exercised,
  never bound to a candidate;
- the operations, integrity and release substrate: twelve integrity classes over a D5 prefix, of
  which nine are shared implementations a successor extends by supplying a prefix rather than by
  copying twelve checks.

**Must not assume:**

- **that any Gate L2 condition is inherited.** §2.2 has held for three sprints: each re-evidences
  all of them against its own authorities. Fourteen met here are fourteen met *here*;
- **that condition 24 stays closed for free.** It is met on D5's holdout. A successor that changes
  the surface, the arms or the comparator has changed the thing that was measured;
- **that the 0.91 means the ranker is good.** The baseline it beats is near chance;
- **that zero confident errors means a zero error rate.** Zero in 26 admitted decisions bounds the
  true rate at 10.9%;
- **that the lifecycle below the selection works.** Nothing has ever run it with a fitted model.
  D3 built artifact, loader, resolver, sequencer, promotion, shadow, canary, activation and
  rollback; D4 and D5 both stopped before driving them. That code is *unexercised*, not proven,
  and the first sprint that reaches it should budget for defects there the way D4 budgeted for
  them in corpus authoring;
- **that a predecessor root marked `intact` still resolves.** S21D5-W3-F1: D4's retrieval graph
  set declares sixty pairs and none of their blobs exists. Check the bytes, not the claim.

## 5. Sprint 22A is still blocked, and by what

Sprint 22A's own objective — the data-driven domain registry and its two pilot domains — was never
in D5's scope and is not what blocks it. What blocks it is §8.1: all twenty-nine Gate L2
conditions met. The tally is **one of twenty-nine newly closed in this sprint** — condition 24,
where D4 had a rejection — with fifteen closed behind a typed stop and the other thirteen met and
re-evidenced against D5's own authorities.

The unblocking path is not a documentation change. It runs through a selected candidate, a v3
artifact bound to a derived operating point, final A/B evidence, promotion, shadow, canary and a
bounded activation — the fifteen conditions the stop closed. A successor that answers §2's
question in the affirmative reopens all fifteen at once.

---

## Evidence handles

| Record | SHA-256 of the file | Seal (`integrity_content_hash`) |
|---|---|---|
| `sprint-21d5-pre-registration.json` | `ed983599bfcdb75993856419de531777d9f4f6cdcce127ead03dcdcddee34b1a` | see the record |
| `sprint-21d5-learner-selection.json` | see the W2 index | `4d45fc00188c00ca…` |
| `sprint-21d5-continuation.json` | see the W2 index | stop `7b59897d8d83…` |
| `sprint-21d5-retrieval-decision.json` | see the W3 index | `ccc666c70833d27c…` |
| `sprint-21d5-gate-l2.json` | regenerated at gate close | 14 met, 15 not opened, 0 failed |
| `sprint-21d5-release.json` | the remote-derived release handles | tag `799190c06497f22e…` |

The per-wave evidence indexes in [`sprint-21d5-execution.md`](sprint-21d5-execution.md) carry both
hashes for every record; this table names only the four a successor's pre-registration has to
bind.
