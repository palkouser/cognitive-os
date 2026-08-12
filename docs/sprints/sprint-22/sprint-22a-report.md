# Sprint 22A report — The Data-Driven Domain Registry

- Branch: `sprint-22a-groundwork`, pull request **#231** against protected `main`. The merge is
  the gate owner's decision, not a wave's; see §6
- Predecessor: Sprint 21D7, tag `sprint-21-learning-baseline`, object `3025082526cef6d9…`,
  peeling to `3f5d7379caf85290da45885e22138506211bee2e`; branch point `c5119cc`
- Pre-registration: **revision 1**, published in W0 with `measured_values: 0`, SHA-256
  `dc40727db85be1ce…`. **Revisions after W0: none**
- Outcome tag on a pass: **`sprint-22a-domain-baseline`**. Negative tag
  `sprint-22a-evidence-baseline` — not created
- Migration head: `0015`, unchanged. `0016` remains unallocated, and the exit criterion makes
  it a refusal
- Exit criteria: **4 of 4 met**, decided in
  [`sprint-22a-exit-criteria.json`](evidence/sprint-22a-exit-criteria.json)
- Thresholds moved by this sprint: **0**, in every wave

---

## 1. The question, and the answer

The allocation asked whether the system can grow past its four released subjects **without
creating domain silos or core branching**. In the released design a domain is an enum member:
`DomainKind` had 57 references across 9 modules, and every one of them was a place where a
fifth domain would have to be taught about, one branch at a time.

22A's answer is that domain identity moves into **data** — a versioned descriptor package,
validated through a fail-closed boundary, stored as a content-addressed artifact, and rebuilt
into the registry at startup from an event stream. Two pilots arrived that way:
`engineering.mechanics` and `science.chemistry`, five problem types between them, both solving
through the released Tool Plane tool and judged by the released verifier.

**They added zero `DomainKind` branches, because a descriptor-registered domain has no enum
member to branch on.** The count is 57 → 52 (W1 removed five by deriving metadata through an
adapter) and then flat through W2, W3 and W4 with both pilots registered. That is §3.5's silo
regression, closed as a measurement rather than promised as a policy.

**And the enum survives the sprint on purpose.** §2.3's reading leaves `DomainKind` as the
closed vocabulary of the released four. The day a fifth domain needs what only enum members
get — a persisted pilot run, the Cognitive Controller's state machine — the fence is the
finding, and it belongs to a successor's contract. Both of those days are already named: W2-A1
and the boundary in §5 below.

## 2. What the sprint produced

| Wave | Outcome |
|---|---|
| **W0** | groundwork tested and merged-ready, the two §2.2 decisions taken, revision 1 published with `measured_values: 0`; three findings and one advisory |
| **W1** | the registry seam, storage without a schema, and a vertical slice run in four processes; three findings, two of them found by running the slice rather than reviewing it |
| **W2** | the mechanics pilot, registered from a committed package and solving end to end; three findings and one named stop |
| **W3** | the chemistry pilot, the rejection suite, the silo regression sealed; one finding and two advisories |
| **W4** | the verification matrix, the four exit criteria decided, the report and the handoff; three findings |

**Thirteen findings and four advisories across five waves**, every finding fixed inside its own
wave.

## 3. The numbers

| | |
|---|---:|
| Pilots registered, from committed package files | **2** |
| Problem types they added | 5 |
| Registry entries, released + pilot | 28 + 5 = **33** |
| `released_snapshot_hash()`, with both pilots registered | `00187f2b…` — **unchanged** |
| Released descriptor content hashes unchanged | **4 of 4** |
| `DomainKind` references: W0 → W1 → W2 → W3 → W4 | 57 → 52 → 52 → 52 → **52** |
| References added by two pilots | **0** |
| Controller modules byte-identical to the branch point | **11 of 11** |
| Migration files byte-identical to the branch point | **15 of 15** |
| Migrations, tables, columns and enum members allocated | **0** |
| Concepts the pilots own / share / keep private | 6 / **4** / 2 |
| Owners sharing into `physics`, which owns none of them | **2** |
| Hostile packages refused, across four layers | **10** |
| Benchmark manifests replayed / cases / pass rate | 6 / **248** / 1.0 |
| Verification-matrix rows passed / skipped / structural findings | **39 / 0 / 0** |
| Test suite | **4117 passed**, 107 skipped |

## 4. The four exit criteria

Each is decided in [`sprint-22a-exit-criteria.json`](evidence/sprint-22a-exit-criteria.json),
and the record says for every claim whether it was **measured** in that process or **recorded**
from a sealed wave record whose bytes it binds.

**1. Both new domains register without changing the core controller or the storage schema —
met, measured.** The eleven modules under `src/cognitive_os` whose names say they are
controllers, and the fifteen migration files, are compared byte for byte against `c5119cc`, the
commit the branch left. The *set* is sealed as well as the contents, so a twelfth controller
module or a sixteenth migration is a refusal rather than an invisible widening. One thing did
change and the record says so rather than leaving a reader to find it: a new **event contract**,
`domain.descriptor_registered`. An event type is a contract over a stream the released store
already has; it allocates no table, no column and no enum member.

**2. Cross-domain items are stored once and exposed through multiple governed views — met,
recorded.** The two pilots own six concepts and share four into `physics`. The same content
hash appears in the owner's `OWNED` view and the target's `SHARED` view because it is the same
object, and `physics` owns none of them. The two concepts the pilots did not declare are absent
from the target's view — which is what makes the exposure *governed* rather than automatic.

**3. Global and per-domain replay remain green — met, measured.** Six manifests, 248 cases,
pass rate 1.0, executed by the check itself rather than carried as numbers. All four released
domains are covered; see W4-F1 for why that sentence is not free.

**4. Invalid domain packages fail closed — met, recorded.** Ten hostile cases across four
layers — package boundary 6, registry door 1, catalogue 2, resolution 1 — every one refused
with diagnostics, registry entries unchanged after every one, nothing registered halfway. The
layer is part of the claim: a case that slid to a later layer would be a regression even if it
still ended in a refusal.

## 5. The findings worth carrying past this sprint

**W1-F2 — a registry that replaces is a registry that lies.** The first write order registered
problem types before checking for a collision, so a package colliding on its third type would
have left two entries behind. Every refusal is now decided before a single entry is written.

**W2-F1 — the question W2 inherited named the wrong registry.** W1's handoff said the domain
registry's `snapshot_hash()` was bound into released semantic-memory records. It is not; that
hash belongs to `PredicateRegistry`, and the domain registry's had **no production caller at
all**, counted from the AST with the receiver kept. The decision (S22A-030) split it:
`snapshot_hash()` covers the whole registry and changes when it grows, `released_snapshot_hash()`
covers the released four and reproduces `00187f2b…` forever. The sealed compat value re-binds to
the second rather than being edited.

**W2-F3 — two released assertions assumed the registry could never grow.** A pilot registered
in-process made a floor of "at least two skills for every problem type" fail for a domain that
legitimately declares none. Found by the whole suite, not by the wave's own tests.

**W3-F1 — the runner could not express the requirement the released checker enforces.** §3.5
asked for a package whose capabilities name a verifier that never runs, refused at resolution
with `MISSING_REQUIRED_VERIFIER`. The descriptor runner built its request from the registry
entry alone, so that path had no caller and could only have been *described*. Mirroring the
released `required_capabilities` parameter gave it one.

**W4-F1 — "per-domain replay" covered three of the four released domains for three waves.**
The four manifests every wave ran are `sprint20-domain-{ci,seed}`, which carry logic,
mathematics and physics, and the two learned manifests, which carry the correction surface. The
**coding** domain's cases live in `sprint22-coding-{ci,seed}`, and no 22A wave ran them —
including the wave that sealed the coding domain's own governance check
`domain_kind_coding_registered`, which is precisely the reading §2.3 froze. W4 replays six
manifests, and the test that asserts all four released domains are covered is what keeps a
successor from quietly shrinking the set again.

**W4-F2 — the sprint's first exit criterion was a constant in both waves that claimed it.**
`core_controller_changed: false` and `storage_schema_changed: false` were written as literals in
W2's and W3's sealers. They were true, and they were not checks: nothing would have changed had
someone edited the controller. W4 measures them instead, against the branch point, over a sealed
file set. The general form is D7's W4-F1 — *a validator can outlive the claim it enforces* — and
its cheapest instance is a validator that never enforced anything.

**W4-F3 — the release command's self-check was not idempotent, and running it twice is what
said so.** The matrix globs the evidence directory for records carrying the pre-registration's
hash and fails if one of them is not chronology-checked. Its own record carries that hash and is
written *after* the row that would check it, so the first run was clean and the second failed on
a file the first had created. D5 hit the same shape by putting these checks in a test module and
D7 moved them into the command; it arrived here by a different door. A release command that is
not idempotent is a defect in the command, and the fix is one exclusion with the reason attached.

## 6. The release, and what remains

The wave is complete and the branch is reviewable. What W4 did **not** do is merge it: `main` is
protected, PR #231 is `MERGEABLE` and `BLOCKED` pending the gate owner, and the annotated tag
**`sprint-22a-domain-baseline`** is created once, on the commit exact-head post-merge CI passes
on, after that CI, and never moved. `scripts/release_22a.py --pull-request 231` reads every one
of those handles back from GitHub and from the local repository — the merge commit and its
timestamp, both CI runs with their conclusions and job counts, the tag object and the commit it
peels to, and the branch protection state — and creates nothing. A record that could produce the
state it describes would be a record of itself.

Two stops travel to Sprint 22B by name rather than being closed by a green record:

- **W2-A1**: `domain_pilot_runs` carries `CHECK (domain IN ('mathematics','physics','logic'))`
  and `record_domain_pilot_run` refuses anything else — it never learned about `coding` either.
  Widening it is a migration, and `0016` is this sprint's refusal, so descriptor domains have no
  persisted-run path.
- **W3-A1**: a released domain cannot refuse a view. Released descriptors are derived by the
  adapter and carry no `related_domain_ids`, so reciprocity is required of pilot targets only.
  That asymmetry is load-bearing, not an oversight to patch.

And the risk §5 of the backlog says the evidence cannot retire: **two pilots prove
extensibility, not generality.** Both lean on unit-carrying deterministic verification, the
substrate the released physics domain built. A domain whose verification is not reducible to
deterministic kernels is 22C's question, and this sprint deliberately did not attempt it.
