# Sprint 21D7 report — The Containment Contrastive Class

- Branch: `sprint-21d7-groundwork`, squash-merged as **#229** into protected `main` at
  `2026-08-11T09:09:57Z`, commit `3f5d7379caf85290da45885e22138506211bee2e`
- Release tag: **`sprint-21-learning-baseline`**, object `3025082526cef6d9…`, created after
  the exact-head post-merge CI run `31476479587` (30 of 30 success) and never moved
- Predecessor: Sprint 21D6, tag `sprint-21d6-evidence-baseline`, object
  `29debe41f8dbe16137c0ae528f0ad4390de8d451`
- Pre-registration: **revision 7**, published in W0 with `measured_values: 0`
- Migration head: `0015`, unchanged. `0016` remains unallocated
- Gate L2: **29 met, 0 pending, 0 failed, 0 not opened — the gate passes**
- Gate D1: conditions **6, 7 and 15 all closed**
- Thresholds moved by this sprint: **0**, in every wave

---

## 1. The question, and the answer

D6 asked whether split-conformal admission over the pairwise contrastive margin certifies enough
of what it ranks. It answered no: the Clopper–Pearson bound came out at 0.2747 against a ceiling
of 0.15, and the sealed transfer record said why — the direction was carrying the **authoring
run** rather than the task, in the 384 MiniLM embedding channels.

D7 asked the question that record licensed. **Drop them.** Seven relational channels — six sealed
v2 scalars plus the repair-containment share — the same fit rule, the same α, the same ceiling,
the same coverage floor, nothing amended.

It transfers. The bound comes out at **0.126207** against the same 0.15, coverage **0.59** against
a floor of 0.40, and on 60 final groups opened once after five sprints of being carried, the
promoted artifact scores **0.8667** first choice against the strongest baseline's **0.4833**.

**And the deterministic containment rung is most of that.** Under the seated ladder, 5 of 59
admitted decisions differ from the ordering that one channel produces on its own. The sprint
passes because S21D7-027 unseated the rung at W2 step 0, before anything was scored, on the gate
owner's explicit decision with both branches priced. Every number above is real; this sentence is
what they mean.

## 2. What the sprint produced

| Wave | Outcome |
|---|---|
| **W0** | three §2.2 rulings and the condition-24 renewal, revision 7 with `measured_values: 0`, three findings |
| **W1** | 100-group / 400-outcome certification corpus authored and executed in its own store pair; four findings |
| **W2** | three step-0 rulings before the first score, one fit, one bar, ending **`1_select`**; two findings |
| **W3** | the artifact, the runtime, the two final roles, promotion, the canary, and a governed activation; one finding |
| **W4** | the release matrix, the gate assessment, the continuation; one finding |

**Eleven findings across five waves**, every one fixed inside its own wave.

## 3. The numbers

**The certification cell** — 100 independent decisions, read once:

| | |
|---|---|
| coverage at α = 0.20 | 0.59 (floor 0.40) |
| Clopper–Pearson 95% upper bound | **0.126207** (ceiling 0.15) |
| first choice over admitted | **0.9492** (baseline 0.61) |
| changed decisions / projected | 46 / 46.78 (floor 20) |
| first-action preservation | 100% |
| sweep points reported / selectable | 90 / 0 |

**The final evidence** — 60 groups opened once:

| | |
|---|---|
| learned first choice | **52 / 60 = 0.8667** |
| strongest rung on the same groups | 29 / 60 = 0.4833 |
| absolute gain / relative error reduction | **+0.3833** / **0.7419** |
| changed decisions | **45** |
| paired group bootstrap, 10 000 resamples | **[0.233, 0.533]**, excludes zero |
| per-batch direction | final A +0.300, final B +0.467 |
| shadow: would change / did change | 45 / **0** |

**Promotion and activation:**

| | |
|---|---|
| safety movement into a named construct | **0** of 45 changed decisions |
| retention: worst domain / aggregate loss | **0** / **0** |
| promotion metamorphic | 120 nominal, 60 independent, 80 admitted, 0 errors, bound 0.0368 |
| runtime reason codes reached | **18 of 18**; all 17 fallbacks equal the released rung on all 100 groups |
| canary: learned vs rung attempts to an accepted candidate | **5** vs **9** |
| lifecycle | 4 processes, 2 database restarts, 6 ledger revisions, replay and hash chain verified |

## 4. The findings worth carrying past this sprint

**W3-F1 — a digest recomputed unchanged proves the bytes did not move, not that anything can use
them.** Four D2-authored final bodies predate the source canonicaliser's reflection ban. Five
sprints recomputed their catalogue digests, found them unchanged, and recorded the roles as
carried intact. They were intact. They were also unencodable, and nobody had ever run a final body
through the canonicaliser, because opening the roles is what W3 does. Repaired audit-first, with
the frozen 30/120 counts kept and the test written over the **roles** rather than the
replacements.

**W4-F1 — a validator can outlive the claim it enforces.** The W1 seal asserts that all three
carried roles are byte-identical to D6's; W3's authorised repair made that false for two of them.
The release matrix is where it surfaced, because that is the only place the sprint's own
validators all run. Fixed by rebinding rather than by editing — the repaired hashes are proved to
be the ones the W3 campaigns actually executed against, and the W1 seal's bytes are untouched.

**W2-F1 and W2-F2 — a reproduction check that fails on the passage of time proves nothing.** A
`--check` that re-globs the evidence directory to rebuild a chronology block expires the moment
the wave writes its next record; a live stopwatch inside a record makes byte-for-byte restart
reproduction impossible.

**W1-F2 — a task-level clone is invisible to both detectors** when the bodies were written
independently and the two contracts use different vocabulary.

**W0-F1 — D6 ran its measured campaign in a second store pair that no released D6 record
fingerprints.** An audit reading only `cognitive_os_s21d6_test` reads the store where D6 did the
least work.

## 5. What is live, and what it is bounded to

`learned.containment.correction_ranking` is **active** on `experience.correction_ranking`, routing
the five canary groups and nothing else. Its artifact is 4354 bytes of canonical inert JSON,
`afbdb7c0…`, model hash `d80160c4…`, bound to a lineage naming D5's fitting pool and D6's demoted
certification half. Its approval names the exact assessment hash, component revision and lineage
id, and three refusals — a model identity approving, a human approval naming another assessment,
an unauthorised actor activating — were executed rather than described.

What it is **not**: the bounded steady-state configuration is sealed and was never entered, the
canary→steady transition was not taken, and no surface outside the five routed groups consults the
component.

## 6. The release, and what remains

**Condition 29 closed on the remote, not on prose.** `#229` squash-merged into protected `main`
by the gate owner at `2026-08-11T09:09:57Z` with no administrator bypass; exact-head post-merge
`main` CI run `31476479587`, 30 of 30 jobs successful, completed `09:25:34Z`; the annotated tag
`sprint-21-learning-baseline` created at `09:26:38Z` — **after** that CI, once, never moved —
object `3025082526cef6d9…` peeling to the release commit. `scripts/release_d7.py` read every one
of those handles back from GitHub and recorded **zero findings**.

One thing that ordering forced, and both records say so: condition 29 *is* the release, so the
gate cannot read a pass until the release record exists, and the release record refuses to be
written for a gate that is not on course to pass. The check that survives that is the honest
form — every condition the release does not itself create must be met, and 29 must be the only
row outstanding.

**Nothing remains.** Gate L2 passes at 29 of 29, Gate D1's three are closed, and **Sprint 22A is
unblocked**.

---

| Document | |
|---|---|
| Execution log | [`sprint-21d7-execution.md`](sprint-21d7-execution.md) |
| Gate assessment | [`gate-l2-d7-assessment.md`](gate-l2-d7-assessment.md) |
| Handoff | [`sprint-21d7-handoff.md`](sprint-21d7-handoff.md) |
| Backlog | [`sprint-21d7-technical-backlog.md`](sprint-21d7-technical-backlog.md) |
