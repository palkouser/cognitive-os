# Sprint 22C Execution Log

Continual learning, knowledge acquisition, and the campaign pipeline. Executed against the
[Sprint 22C Technical Backlog](sprint-22c-technical-backlog.md), whose §0 incorporates the
[Sprint 21D4](../sprint-21/sprint-21d4-technical-backlog.md) execution contract unchanged.

Waves are recorded newest first.

---

## W3 outcome — three cycles, the plant refused, and the improvement exit measured as a negative

Cycles 2 and 3 ran into `science.chemistry` on the same campaign store, the pre-registered
plant travelled the genuine intake path and was refused, every cycle replayed every retained
domain, and the frozen holdout was read once with both arms. Four of the five exits are met on
sealed evidence. **The fifth is not, and the wave's value is that it says exactly why.**

| Item | What it owed | Outcome |
|---|---|---|
| **S22C-050** — the second source | every worked example the cleared chemistry chapters carry | **41 located** (25 + 16) by the book's *own* layout, which is not the physics book's |
| **S22C-051** — cycle 2 | nine stages into domain 2, replaying what cycle 1 retained | **ran.** 25 passages, 1 formalised, **0 acquired** |
| **S22C-052** — cycle 3 and the plant | the sealed plant through the genuine intake, quarantined and staying quarantined | **met.** All four §2.2b conditions, refused by the cross-check's second leg |
| replay | three cycles, per-domain rates, forgetting as a delta | **met.** 3 points, mechanics 1.0 / 1.0 / 1.0 — nothing forgotten |
| **S22C-053** — the holdout | both arms, once, against the frozen definition | **read.** Arm A **0 of 4**, arm B **0 of 4**. A measured negative |

### S22C-050 — a second book is a second layout

*Chemistry 2e* opens a worked example with `EXAMPLE 3.1`, not `WORKED EXAMPLE`, and closes one
with a `Check Your Learning` whose `Answer:` is printed in the text layer — the only place in
either book where a stated result reliably survives extraction. So the passage is cut *after*
that answer, and the reader now carries a **source profile** rather than one book's habits.

The physics side is untouched: the same eighteen passage identities, the same bytes, the same
sealed records rebuilding byte-for-byte. Where the two books needed different identities the
**new** source took the prefix, because a wave does not rewrite an identity that sealed
evidence already names — eighteen provider seals and two records name those.

### S22C-051 — cycle 2, and the same finding from the other side

Twenty-five passages from *Composition of Substances and Solutions*. The provider formalised
**one** — *Deriving Moles from Grams for an Element*, the only passage in the chapter that
prints the atomic mass it relies on (`the atomic mass of K is 39.10 amu`). Twenty-three were
refused as `no_registered_problem_type`: the chapter is mostly molarity, dilution, percent
composition and empirical formulas, and `chemistry.molar-conversion` is one direction of one
of those.

Then the one that was formalised failed the cross-check:

> the source asserts `exact_value='0.12'`; the kernel computed `'47/391'`

**That is W3-F2, and it is not a defect.** 4.7 g of potassium at 39.10 g/mol is `47/391` mol,
which the textbook prints — correctly, at two significant figures — as `0.12`. W1-F3 fixed the
comparison to read *numbers* rather than notations and refused to widen it into a
significant-figures tolerance, because that is tuning the check until the source passes. The
consequence, now measured: **a textbook that rounds its answers cannot be verified by exact
equality**, and almost every textbook rounds. Cycle 2 acquired nothing.

### S22C-052 — the plant, refused on the path everything else took

Cycle 3 registered chapter 4's sixteen passages **and** the plant W0 sealed before any cycle
existed, in one intake, through the same nine functions. The plant is not malformed and
nothing about its shape distinguishes it: it asserts that `2 H2 + O2 → 3 H2O` conserves mass.

All four frozen conditions hold. The released checker **passed** the derivation — asked whether
that equation balances, the kernel correctly answers no, and the checker correctly accepts that
answer — and what refused the plant is the second cross-check leg comparing the *source's
assertion* to the kernel's computation. That is W0-F4 restated on real content, and it is why
the second leg exists.

The fourth condition, "stays quarantined through every later cycle's replay", has no later
cycle to observe. The record reads it as a **mechanism** instead: replay executes retained
cases, the plant is in no retained-case record, so there is no path by which it returns. A
record that observed the plant staying out would be reporting a coincidence.

### Replay — three measured points

| Cycle | Domains enumerated | With retained cases | `engineering.mechanics` rate |
|---|---|---|---|
| 1 | 6 | 1 | 1.0 |
| 2 | 6 | 1 | 1.0 |
| 3 | 6 | 1 | 1.0 |

Cycle 1's artifact is **executed** again in cycles 2 and 3, not referenced — the retained set is
read out of the sealed retained-case records and run through the released path each time. Four
of six domains retain nothing and report `cases: 0` rather than being omitted (W0-A1). Nothing
was forgotten; the delta across three points is zero. What this does *not* show is resilience,
because a retained set of one is a weak test of forgetting, and the record says so.

### S22C-053 — the holdout, and the exit this sprint was scheduled around

Read once, no leakage, `measured_values` 0 at freeze.

| Case | Withheld | Arm A | Arm B |
|---|---|---|---|
| molar conversion, water | `atomic_masses` | refused | **no retained artifact supplies it** |
| molar conversion, methane | `atomic_masses` | refused | **no retained artifact supplies it** |
| mass balance, ammonia | `atomic_masses` | refused | **no retained artifact supplies it** |
| uniform motion, 3 000 m | `speed` | refused | ran, and was wrong: 480 m against 3 000 m |

**Arm A 0 of 4, arm B 0 of 4.** Arm A failed exactly as the frozen definition predicted — the
kernels refuse a case that does not declare what it relies on, which is the baseline the
holdout was built on.

Arm B is the finding. Three cases had nothing to restore *from*: the campaign retained no
chemistry artifact at all, so no acquired fact carries `atomic_masses`. The arm reports that
rather than running — an arm B that filled its own gap from the case it was measuring would
measure nothing, and that distinction is the whole integrity of the exit. The fourth case did
run, with a genuinely retained artifact (Layla's 2.4 m/s, cycle 1, citation resolving to source
bytes), and computed 480 m against an expected 3 000 m. **That is not a pipeline failure**: the
artifact is sound and describes a different body. The holdout's fourth case was authored
expecting the campaign to retain a fact — *15 m/s* — that exists in the physics source only in
running prose, never in a worked example.

### W3 findings

#### W3-F1 — the pipeline can only retain what a kernel recomputes, and a holdout needs facts

This is the sprint's central result and it subsumes W2-F1.

A governed acquisition pipeline whose verification floor is deterministic kernels can promote
exactly one kind of artifact: **a worked example whose asserted result a registered problem
type can recompute exactly.** The four holdout cases need something else — an atomic mass, a
stated speed. Those are *declarative facts*, and no registered problem type can verify a
declarative fact, so the pipeline cannot acquire one however plainly the source states it. The
atomic mass of potassium is printed in chapter 3 in words; the jet car's 15 m/s is printed in
chapter 2 in words; neither can become a retained artifact.

That is Gate D1's usefulness floor, stated with numbers rather than as a worry: **59 worked
examples across two rights-cleared textbooks, 1 acquired, 0 of 4 held-out tasks improved.**
Three independent walls produced it, and they compound:

| Wall | Passages | Share |
|---|---|---|
| the domain registers few problem types, and directionally | 53 | 90 % |
| a kernel demands an input its answer does not use (W3-D1) | 2 | 3 % |
| the arithmetic is an image with no text layer | 1 | 2 % |
| the givens themselves are not stated | 1 | 2 % |
| **formalised, then refused because the textbook rounded** (W3-F2) | **1** | 2 % |
| **acquired** | **1** | **2 %** |

Fifty-nine, and the wall everybody expects — *the maths is a picture*, the one W1 found on its
single passage and which looked like the whole problem — is **one passage in fifty-nine**.

**What would move it** is a question for the gate owner, not an absorption for a wave: widening
a domain's problem types, adding a verification path for declarative facts that is not a
kernel, or accepting that acquisition serves domains whose content matches their kernels. This
record measures the gap; it does not close it.

#### W3-F2 — exact equality and a rounding textbook cannot both be right

Recorded above. The rule stands unchanged, because the alternative is a tolerance chosen after
seeing which one lets the source through, and W1-F3 already refused that. But the cost is now
priced: this pipeline can verify a textbook's *reasoning* and cannot verify its *printed
answers*, and those are different capabilities.

#### W3-D1 — a refusal with a name, rather than a value invented for a kernel

`chemistry.mass-balance` requires `atomic_masses` on every case and its verdict does not depend
on their values — only on their presence. A passage that balances an equation never states
them. The provider could have supplied standard values from its own knowledge; that is
inventing data to satisfy a kernel, and rule 1 exists to refuse it. So the wave added a refusal
reason, `kernel_requires_unstated_input`, and the two passages that hit it — including
chapter 4's *only* balancing example — are refusals on the record rather than a fudge. The
decision is recorded because it decides what the wave measures.

#### W3-A1 — the contradiction demonstration on real content could not be run

§3 asks for one. It did not happen, and the reason is W3-F1: the campaign promoted no chemistry
content, so there were never two claims about one subject for the released detectors to
compare. The machinery is not unexercised — cycle 1's supersession turns on the functional
detector's rule, which is why its temporal boundary exists — but a contradiction between two
*acquired* claims needs two acquired claims. Carried by name rather than substituted for.

### W3 evidence index

| Record | Item | Integrity |
|---|---|---|
| [`sprint-22c-w3-chapter.json`](evidence/sprint-22c-w3-chapter.json) | S22C-050 — 41 chemistry worked examples | `9ca302354749722c…` |
| [`sprint-22c-w3-proposals/`](evidence/sprint-22c-w3-proposals) | 41 sealed `ReplayFixture`s | hashed per receipt in the cycle records |
| [`sprint-22c-w3-cycle2.json`](evidence/sprint-22c-w3-cycle2.json) | S22C-051 — cycle 2 | `719dd161abbfcfb0…` |
| [`sprint-22c-w3-cycle3.json`](evidence/sprint-22c-w3-cycle3.json) | S22C-052 — cycle 3, carrying the plant | `b88fa112a8abd2bf…` |
| [`sprint-22c-w3-plant.json`](evidence/sprint-22c-w3-plant.json) | S22C-052 — the four frozen conditions, read from the cycle | `28b6d22c22c9a73a…` |
| [`sprint-22c-w3-improvement.json`](evidence/sprint-22c-w3-improvement.json) | S22C-053 — both arms, read once | `87a1bd5bce4f143d…` |
| [`sprint-22c-w3-retained-cases.json`](evidence/sprint-22c-w3-retained-cases.json) | what a fourth cycle would replay | `84d7e76284d485e7…` |

Drivers: [`scripts/improvement_22c.py`](../../../scripts/improvement_22c.py) and
[`scripts/plant_22c.py`](../../../scripts/plant_22c.py), both of which **re-run nothing** and
read sealed records; `chapter_22c.py`, `provider_22c.py` and `cycle_22c.py` gained source and
cycle profiles. No released code changed in this wave.

### W3 validation

All static gates clean. Cycle 1's record, the W1 slices and the W0 fixture slice **all still
rebuild byte-for-byte** after the profile refactor, which is the evidence that cycles 2 and 3
ran the code cycle 1 was measured on. 20 new tests read the W3 records with no database and no
provider.

### What W4 inherits

**Met on sealed evidence:** every cycle replays all retained domains; the planted update is
quarantined and cannot return; a valid new revision supersedes the active view without
deleting history (W2); source citations and hashes survive every derivative.

**Not met, measured:** at least one retained artifact improves a held-out verified task — arm A
0 of 4, arm B 0 of 4, both arms sealed. Under §5 that is a **stop**, and the release is the
typed negative `sprint-22c-evidence-baseline` unless the gate owner takes W3-F1's decision and
a further wave changes the input.

**Carried by name:** W3-A1 (contradiction on real content), W2-A1, 22B W2-F2, W0-A1, and the
crash window W1's resume repairs but does not close.

---

## W2 outcome — cycle 1 acquired one worked example in eighteen, and the domain is the reason

Three drivers, one released-code repair, three sealed records and eighteen sealed provider
proposals. Cycle 1 ran all nine stages against a provisioned PostgreSQL campaign store, the
supersession was verified two ways on that store, and every promoted artifact's citation
resolved to loaded source bytes.

The number the wave exists to produce is the **acquisition yield**, and it is a negative:

| Item | What it owed | Outcome |
|---|---|---|
| **S22C-040** — the chapters | every worked example the cleared chapters carry, by one rule | **18 located** across chapters 2, 4 and 6; six cross a page break |
| **S22C-041a** — extraction | provider-assisted, receipts sealed, replayable without the network | **18 governed calls**, each sealed as a released `ReplayFixture` and re-executed through the released provider path |
| **S22C-041** — cycle 1 | nine stages, full manifest, replay of every retained domain | **ran on the campaign store.** 1 of 18 promoted; the other 17 quarantined with named reasons |
| **S22C-042** — supersession | the released lifecycle, verified two ways, history loadable | **met.** proposed → supported → superseded, both ways agree, three revisions still loadable with citations resolving |

### S22C-040 — the chapters, located by the book's own layout

The rights record names Physics chapters 2, 4 and 6 for `engineering.mechanics`, one per
registered problem type. All three are taken, because a cycle that read only the kinematics
chapter would measure one problem type's coverage and publish it as the source's yield.

A passage runs from the `WORKED EXAMPLE` marker to the next structural marker of the book's
own layout — never to a character offset typed into a driver, because offsets move with every
`pdftotext` version and the anchors are the document's own words. The body pages are named and
the running heads on them are recorded, so the range can be checked rather than believed; the
Chapter Review and Test Prep pages are excluded because they are exercises with no worked
solutions, and counting them would have inflated the denominator of the number below.

Eighteen worked examples: **nine in chapter 2, three in chapter 4, six in chapter 6**. Six of
them cross a page boundary, so folio numbers, form feeds and running heads sit inside the
registered bytes. They stay there — W1's rule, at chapter scale: *a campaign that cleans its
sources cannot afterwards prove what it read.*

### S22C-041a — what a provider was actually asked, and what it refused

A worked example is prose; a kernel needs `{"speed": {"magnitude": "2.4", "unit": "m/s"}, …}`.
Turning the first into the second is the job §1.2 gives a provider — *a proposal revalidated
on the host, with no semantic write authority*. The provider is never asked whether the
physics is right. It is asked what the passage says; whether the passage is right is the
kernel's answer, two stages later.

Every call went through the released `GovernedTeacherService` under a
`corpus_candidate` directive with the gate owner's clearance as its rights decision, and every
call left a receipt carrying the request hash, the normalized response hash and the completed
model-call envelope. Beside each receipt the driver sealed a released `ReplayFixture`.
**Ordinary runs then load those fixtures into the released `ReplayProvider` and execute the
same governed path again**, so the seal is verified by re-execution rather than by trust: an
edited response would not reproduce its sealed normalized hash and the cycle would refuse to
run. `--live` is §1.3's opt-in and is the only way a network call happens; the sealed cycle
made **zero**.

The provider formalised **one** passage and refused seventeen — sixteen for
`no_registered_problem_type` and one for `no_readable_result` — and its refusals are the most
useful output of the wave. It was explicitly forbidden to bend a passage into the nearest
type, and it did not:

> Bending the given 650 N friction plus an unknown thrust into a statics-equilibrium force
> list would mean inventing the very quantity the passage solves for.

### S22C-041 — cycle 1, on the campaign store

Nine stages in order, on `cognitive_os_s22c_campaign` at migration head `0015`, provisioned
for this cycle so the store W1's crash reproduction wrote to was not touched. Two operational
facts belong in the record rather than in a shell history. The **first** attempt at this cycle
ran against the sprint's `_test` store and aborted at the supersession on W2-F2, leaving
eighteen corpus items and two claims behind there; that is why the campaign has a database of
its own, and the `_test` store's ten thousand memory rows — W1's crash evidence — were left
untouched rather than truncated. The **second** is that `--cycle` is not idempotent: the Corpus
Factory refuses a re-ingest of identical content by design, so re-running the authoritative
cycle means dropping and re-migrating the campaign database, and the record names the database
so a reader can tell which run they are looking at. The manifest is
`s22c-physics` revision 2 (`16a16c2a3e5e2c35…`), and it names the **real** frozen holdout
rather than W1's placeholder, so the leakage check compares this curriculum against the cases
the improvement exit will actually read: eighteen curriculum segments, zero overlap,
`measured_values` still 0.

Replay enumerated all six domains from `registry.domain_ids()` and executed what each retains;
four of six retain nothing and are reported with `cases: 0` rather than omitted (W0-A1,
unchanged). The citation walk covered the single promoted artifact — one hundred per cent of
them, and the record says `sampled: false` — over four hops to loaded, rehashed source bytes.

### S22C-042 — the supersession, and why the boundary is temporal

The claim cycle 1 promoted carries the statement a *provider* read out of the passage. The
cross-check then computed the same quantity with the domain's own kernel, in exact rationals —
`552/5` where the textbook writes `110.4`. A claim carrying the value a deterministic kernel
computed is better grounded than one carrying a value a model read, and replacing the second
with the first is the ordinary business of an acquisition campaign. **The source did not
change; what changed is that the campaign now holds a number it verified rather than a number
it was told.** Both revisions cite the same registered bytes, and the walk proves it.

Verified two ways that agree: the active view queried returns exactly the successor, and the
supersession chain walked from the predecessor reaches exactly that claim. History survives —
revisions 1, 2 and 3 all load, revision 2's evidence still resolves to loaded bytes, no row was
deleted — and the predecessor's stream carries the full sequence
`claim_created → belief_changed → belief_changed`.

**The temporal boundary is the mechanism, not a workaround.** The campaign predicate is
functional and the released contradiction detector compares current revisions while ignoring
belief status (W0-F3's rule, one layer on), so a superseded predecessor whose validity stayed
open would go on contradicting its own successor and the successor could never activate.
Closing the predecessor at the supersession instant is what supersession *means* for a
bitemporal functional claim: it was true until the revision, and the successor is true from it.
Half-open intervals make the two abut without overlapping.

### W2 findings

#### W2-F1 — the acquisition yield is bounded by the domain, not by the source

**One worked example in eighteen. 5.6 %.** Sixteen of the seventeen refusals are
`no_registered_problem_type`, and the diagnosis is sharper than the count:

| Chapter | Chosen for | Worked examples | Acquired |
|---|---|---|---|
| 2 — Motion in One Dimension | `mechanics.uniform-motion` | 9 | **1** |
| 4 — Forces and Newton's Laws | `mechanics.statics-equilibrium` | 3 | **0** |
| 6 — Circular and Rotational Motion | `mechanics.moment-balance` | 6 | **0** |

Three things this exposes, none of which the plan anticipated:

- **The registered problem types are directional.** `mechanics.uniform-motion` takes a speed
  and a duration and returns a displacement. Chapter 2 mostly asks the *inverse* — an average
  speed from a distance and a time, a duration from a displacement and a velocity — and no
  registered type runs that way. The kernel could compute those quotients; the problem type
  cannot express them.
- **The chapter-to-problem-type mapping in S22C-020 was never verified against the chapters'
  contents.** The rights record confirmed the chapters were *present*. Chapter 4's worked
  examples are Newton's second law on accelerating bodies, not statics; chapter 6's are
  angular speeds, centripetal acceleration and rotational kinematics. Exactly one is a moment
  about a pivot — *Calculating the Torque on a Merry-Go-Round* — and **that one states no
  readable result**, because its Solution carries only the equation number `6.13` and its
  Discussion has its substantive clauses sheared out where symbols were images.
- **The image problem is real but secondary.** W1 found it on one passage and it looked like
  the binding constraint. At chapter scale it accounts for **one** refusal in seventeen.

This is a measurement, not a defect, and it is the most useful thing the wave produced: the
cost of filling a governed knowledge store is set by how much of a source a *domain* can be
held to, and this domain can be held to one worked example per rights-cleared textbook chapter
set. The candidate resolutions are the gate owner's (§1.3, §2.1), and they are not equal:

| Resolution | Consequence |
|---|---|
| Register more problem types in `engineering.mechanics` — the inverse kinematic relations, Newton's second law, angular speed | The direct fix, and it is a **domain revision**: 22A made domains data precisely so this is possible. §2.1 says "no new domain registration beyond what campaign content lands in the two existing pilots", which this arguably is not, so it is a decision and not an absorption |
| Accept a one-artifact physics campaign and lean on chemistry for cycles 2 and 3 | Honest, cheap, and leaves the improvement exit resting entirely on the chemistry campaign — which is where the frozen holdout's cases live anyway |
| Choose different chapters | Does not help. The refusals are about what the *domain* registers, and no chapter of an introductory physics text is mostly displacement-from-speed-and-time |

**W3 is not blocked by this.** Cycles 2 and 3 extend into chemistry, whose two problem types
are molar conversion and mass balance and whose chapters are full of both.

#### W2-F2 — the PostgreSQL active view kept superseded claims, and only the campaign store had the defect

`PostgresSemanticMemoryRepository.query_claims` filtered on belief status inside the same
`SELECT` that picked the current revision with `DISTINCT ON (claim_id) … ORDER BY revision
DESC`. The two composed the wrong way round: the database discarded the superseded revision and
returned the newest one that *survived the filter* — the last revision the claim held before it
was retired. **A superseded claim stayed in the active view wearing its old belief, and so did
a retracted one.**

The in-memory repository has always taken the newest revision first and then asked whether it
is believed, which is the correct order: a claim's belief is whatever its latest revision says,
not whatever its latest agreeable revision said.

Two stores disagreeing is worse than either being wrong alone. **Every test in the suite runs
in memory**, so the store the campaign actually writes to was the only place this behaviour
existed, and nothing could see it. Cycle 1 found it the only way it could be found: the
successor was refused promotion with `semantic.critical_contradiction`, because the predecessor
it had just replaced went on contradicting it from an interval the store still thought was
current. The same run had passed in memory minutes earlier.

The repair moves the belief filter into an outer query over the current-revision subquery;
`valid_at` and `known_at` stay inside, because they choose *which* revision is current, which
is what the in-memory implementation does with them. Eight integration tests pin it: the
create → support → retire scenario is run against each repository on its own and then against
both with a **parity assertion**, for `superseded` and `retracted` alike, plus one test that
the retired claim's three revisions are still loadable and one that a claim which *is* believed
is still returned. The parity assertion is the part that would have caught this — either
implementation alone looks reasonable. Against the pre-repair code four of the eight fail; the
two in-memory ones are among the four that pass, which is the shape of the whole problem.

#### W2-F3 — the Tool Plane's evidence cannot reach a governed store

`domains.descriptor_runner.run_descriptor_case` takes a `MemoryEventStore` **by type** and calls
`event_types()` on it, a method only the in-memory store has. So the solve and verify events of
every cross-check and every replay in a campaign cycle are written to an in-memory store and
discarded. Nothing before 22C needed them durable, so nothing noticed. The record names the two
stores apart rather than letting an in-memory Tool Plane read as a choice this driver made; the
consequence is that cycle 1's *domain evaluation* left no durable trace, while its corpus,
semantic, memory and artifact writes all did.

#### W2-F4 — the quarantine vocabulary cannot say "no registered domain can check this"

`CorpusQuarantineReason` offers ten reasons, all about the source: unclear licence, conflicting
provenance, malformed archive, unverifiable provider data. It has no reason for *the platform
has no registered domain that could check this*, which turned out to be sixteen of seventeen
refusals — the commonest outcome of a real acquisition campaign by a wide margin. Both provider
refusals therefore map onto `unverifiable_provider_data`, the nearest honest released value, and
the campaign keeps the distinction in its own record. A campaign may be stricter than the
released vocabulary and may never invent a value for it.

### W2-D1 — the gate owner authorised the live provider call

§1.3 makes any live campaign an explicit opt-in, so the decision was put and not assumed. The
gate owner chose *one live call per passage, then sealed replay*. The adapter named in the
question was MiniMax; its configured key is empty on this host, so the call ran through the
released **Claude Code advisory adapter** instead — read-only, `plan` permission mode, an empty
MCP configuration, no settings sources, and a bounded runner. That is a different adapter than
the question named, and the record says so: what the authorisation covered is a live provider
call, and the receipts name which provider answered.

### W2 evidence index

| Record | Item | Integrity |
|---|---|---|
| [`sprint-22c-w2-chapter.json`](evidence/sprint-22c-w2-chapter.json) | S22C-040 — 18 worked examples, one location rule | `3157e5013a98ae8d…` |
| [`sprint-22c-w2-proposals/`](evidence/sprint-22c-w2-proposals) | S22C-041a — 18 sealed `ReplayFixture`s, one per passage | hashed per receipt in the cycle record |
| [`sprint-22c-w2-cycle1.json`](evidence/sprint-22c-w2-cycle1.json) | S22C-041, S22C-042 — cycle 1 and the supersession | `a5383c8bba85b753…` |
| [`sprint-22c-w2-retained-cases.json`](evidence/sprint-22c-w2-retained-cases.json) | what cycles 2 and 3 replay | `f22358e4a293661b…` |

Drivers: [`scripts/chapter_22c.py`](../../../scripts/chapter_22c.py),
[`scripts/provider_22c.py`](../../../scripts/provider_22c.py) and
[`scripts/cycle_22c.py`](../../../scripts/cycle_22c.py). Released change:
`PostgresSemanticMemoryRepository.query_claims`. `campaign_22c.py`'s nine stage functions gained
an injected composition and a sealed-proposal path and are otherwise unchanged — W0's and W1's
records **rebuild byte-for-byte** after both, which is the evidence that cycle 1 runs the code
the slices proved.

### W2 validation

`ruff check` and `ruff format --check` over `src tests scripts infra`, `mypy src/cognitive_os`
(638 files), `bandit -r src/cognitive_os` (0 issues at every confidence), the contract schema
export `--check`, and the repository language policy — all clean. Whole suite over the full
tree: **4 504 passed, 223 skipped**, 4 726 collected — the PostgreSQL integration directory is
collected and skips unless a database is nominated for truncation, which is why the skip count
is large and why W2-F2's tests were also run directly against the sprint's integration store.
Two new test modules: 22 tests reading the cycle records with no database and no provider, and
8 integration tests pinning W2-F2 in both stores. `cycle_22c.py --check` rebuilds the cycle's
**invariants** in
memory and compares them — the manifest, the sealed receipts, the yield, every cross-check
verdict, the quarantine decisions, the replay and the citation chains — while the campaign
store's own rows are left as observations, because a validator that recomputed an observation
would only prove the record agrees with itself (W1-F1).

### What W3 inherits

**Ready:** the campaign store with cycle 1 in it, the sealed proposals every later cycle
replays from, the retained-case record, and a supersession the released lifecycle now supports
on PostgreSQL as well as in memory.

**Owed:** W2-F1's decision — whether `engineering.mechanics` gains problem types, or the
physics campaign stands at one artifact. Cycles 2 and 3 extend into chemistry either way, and
the improvement exit's holdout cases are chemistry's.

**Carried by name, unchanged:** W2-A1 (the topic-versus-instance claim subject, changed by this
wave and *not* exercised by it — one formalised segment cannot collide, and the record refuses
to claim a defect it did not observe), W3-A1, 22B W2-F2, W0-A1, and the crash window W1's
resume repairs but does not close.

---

## W1-D2 — the gate owner's ruling: a program may advise on a licence, and may not decide it

W1-F6 was surfaced as a blocking dependency with two candidate resolutions. The gate owner
took neither, and named the reason both were wrong:

> The licence review is the result of a design error. Automatic examination, adjudication and
> acceptance of a licence cannot be the basis of actual use. The program may check the
> licence, if there is one at all, and may propose a classification and a use — but the
> material's actual classification and use must be provided by the user (permission), because
> the legal responsibility is theirs.

That is a sharper diagnosis than the finding. The defect was never the length of
`APPROVED_LICENSES`. It was that a list of identifiers **was** the determination, while the
`LicenseDeclaration` it produced carried a `declared_by` naming an operator who had decided
nothing. The field said a human had declared it; the list had. Lengthening the list would
have preserved exactly that, and would have taken a legal judgement — is CC BY-NC-SA
restricted? — inside the program, which is what made the "obvious" fix end the chemistry
campaign.

**What changed in released code.** `OperatorLicenseClearance` is a new contract in
`domain/corpus.py`: an identifier, the operator's determination, what they permit it to be
used for, who they are by name, when they decided, the licence evidence they decided on, and
the content hash of the bytes it covers. `CorpusFactoryRequest` carries them. The factory's
lists are renamed `RECOGNISED_PERMISSIVE_LICENSES` / `RECOGNISED_INTERNAL_LICENSES` and
demoted to advice, published as `LicenseClassification.advisory_status` beside the decision,
so a reader can always see both — including when they disagree, which for CC BY 4.0 they do.

**The asymmetry is the whole design, and it is pinned by tests.** *The program may refuse on
its own; it may never permit on its own.* Without a clearance an unrecognised licence still
quarantines exactly as before — the ruling removed an authority, not a safeguard. Two
refusals guard the contract: a clearance may not carry `unknown` or `conflicting`, because
those are the absence of a decision and would let an operator decline to decide while looking
like one who had; and it names a `source_content_hash`, so a decision cannot drift onto
another edition. The authority runs both ways: an operator may also mark `restricted`
something the platform would have recognised.

**W1-F6's second half, also closed.** `CorpusConfiguration` advertised
`unknown_license_action` and five siblings; `_route` hard-coded the same outcomes and read
none of them. They are read now, validated at load rather than as a `KeyError` mid-ingest,
and `allow` is deliberately not a legal value — configuration may choose *how strictly to
refuse* and may not choose to permit. Fixing that surfaced one more: each check **assigned**
`status`, so a later one could soften an earlier one, and material an operator had marked
`restricted` came out merely `quarantined` when a usage right was also missing. Refusals are
monotone now; every reason is still recorded.

**The current sources are accepted on the gate owner's authorisation.** S22C-020 already was
the review — a named authority, the licence page hashed, exact bytes — and had no way to be
heard. It is now carried into the factory as the clearance it always was.

| Record | Then | Now |
|---|---|---|
| [`sprint-22c-w1-slice.json`](evidence/sprint-22c-w1-slice.json) | passage quarantined, `license-review-required` | kept, sealed, true about the design it ran under |
| [`sprint-22c-w1-slice-cleared.json`](evidence/sprint-22c-w1-slice-cleared.json) | — | same bytes, same nine stages, **promoted**, citation chain resolving to loaded source bytes |
| [`sprint-22c-w0-slice.json`](evidence/sprint-22c-w0-slice.json) | fixture licence read `approved` | kept, sealed, not rebuilt |
| [`sprint-22c-w1-fixture-slice.json`](evidence/sprint-22c-w1-fixture-slice.json) | — | identical in every substantive field; licence reads **`internal`** |

That last row is the ruling's own audit. The fixture chapter's clearance permits internal
use, derivative work and benchmark use — **not** public release. The allowlist had been
overwriting that with `approved` because Apache-2.0 is on it. Now the clearance decides, and
the record says what the operator actually determined. Five promoted, plant quarantined, nine
stages, citations resolving: unchanged.

**No record is edited.** Each supersedes its predecessor by name and both keep their seals —
the same discipline as W1-F1 and W1-F4. `sprint-22c-w1-slice.json` is not wrong; it is what
this pipeline did when a list was allowed to decide.

**W2 is unblocked.**

---

## W1 outcome — both inherited repairs proven, and a licence policy that refuses the sprint's own sources

Two drivers, one released-code repair, seven sealed records, two new test modules. The two
repairs 22B handed over by name are **both proven against 22B's own reproductions**, and the
real source's first segment travelled all nine stages — where it was **refused by the
released Corpus Factory**, which does not recognise CC BY 4.0. That refusal is W1's headline
and W2's blocking dependency.

| Item | What it owed | Outcome |
|---|---|---|
| **S22C-031** — 22B W3-F1 | zero governed items outside their event stream after the same crash | **met.** 1 orphan after recovery, **0 after the resume** |
| **S22C-032** — 22B W4-F1 | clustered recall back over the 0.95 floor after a restore | **met.** 0.9410 → **0.9676** |
| **S22C-033** — the vertical slice | the real source's first segment through all nine stages | **ran, and was refused.** Nine stages in order; the platform quarantined the passage on its licence |

### S22C-031 — the resume now repairs, and the window is still open

**22B W3-F1.** `MemoryService.create` wrote the record in one transaction and appended
`memory.item_created` in another, and decided whether to append by asking whether the memory
existed *before* the write. Both halves are wrong. The window is real — 22B killed the
database mid-ingest and one write in 502 came back with a row and no event — and the
pre-check made the orphan **permanent**, because the resume that re-runs a crashed range
finds the row through its idempotency key, concludes the item is not new, and never reaches
the append. The recovery procedure was what made the damage last.

The repair asks the stream instead of the record. `MemoryEventService.ensure_item_created`
looks for the record's creation event and appends it if it is absent, whether this call
created the record or found it, so the resume repairs. Round-trip count is unchanged: the
`get_current` probe that existed only to decide the append is replaced by a
`get_stream_version` probe that asks the question actually in doubt.

Proven twice, because the crash alone is not a proof. The crash is a race, and a re-run that
misses the window reports zero orphans and means nothing — so the driver records
`window_opened` and **refuses to read a run where it is false**. Attempt 1 missed; attempt 2
landed, with 504 writes before the SIGKILL, 4.56 s of crash recovery, **1 item outside its
event stream after recovery and 0 after the resume**, and the same range resumed without
duplicating anything. Beside it, a deterministic proof: an orphan written directly through
the repository — exactly the state a crash leaves — repaired by one resume and not
duplicated by a second.

**What is not fixed, said twice in the record.** The window is not closed. An item whose
range is never re-run keeps its orphan, and a repaired event is stamped when the repair ran,
not when the record was written. Closing it needs the record and the event in one
transaction, which needs a transactional boundary `MemoryRepositoryPort` and `EventStorePort`
do not share, and §1.4 froze `0016` as a refusal. It is named as owed, not counted as done.

### S22C-032 — the restored index, back over the floor

**22B W4-F1.** `pg_restore` rebuilds HNSW indexes rather than copying them, and the rebuilt
graph read **0.9410** against a 0.95 floor with no released signal that anything had
degraded. The procedure was pre-registered before the first REINDEX, with the mechanism as a
hypothesis and its falsifier named — a procedure chosen after seeing which knob moved the
number is a knob, not a procedure.

**The precondition first, and sealed on its own.** Before anything was rebuilt, 22B's
restored store was re-measured unchanged: 500 probes, exact-scan ground truth per probe,
**0.9410 — identical to the sealed value**, in 685 s. The reading is deterministic given the
same index and probe seed, so any other value would have meant the store moved since 22B
sealed it and the comparison this repair rests on was void. It held, and the record exists
independently of what happened next (W1-F4).

**The hypothesis.** The server's default `maintenance_work_mem` is **64 MB** against an index
of **3 906 MB**, so `pg_restore`'s rebuild took pgvector's two-phase on-disk path: the second
phase inserts the remaining tuples one at a time into a graph it can no longer see whole, and
the result is a worse graph with no error and no warning at the SQL level. The source index
was built by the same code under the same setting, so the two-phase path alone is not the
whole story — the phases split at a different point, because `pg_restore` loads rows in the
archive's order rather than the original insert order, and which tuples land in the in-memory
phase decides the graph both phases inherit.

**The result.** A serial rebuild at 12 GB took **658.8 s** and the same 500 probes then read
**0.9676** — over the floor, **+0.0266** on the restored index, and **+0.004** even against
22B's own source index. The hypothesis held and the pre-registered fallback
(`hnsw.ef_construction = 200`) was **not** used.

What this does not claim: that the repaired index is the one 22B built at the source. It is
not — it is a third graph, built under a budget neither earlier build had. The claim is only
that a restored store can be returned above the floor by a procedure fixed in advance. And
the rebuild is not free: an operator restoring a governed store pays eleven minutes per index
before that store's recall is trustworthy.

### S22C-033 — the real source, refused on its licence

`Physics_-_WEB.pdf`, CC BY 4.0, content hash re-verified against S22C-020 before the file was
opened. One worked example from §2.2 Speed and Velocity — *"Layla jogs with an average
velocity of 2.4 m/s east. What is her displacement after 46 seconds?"* — pages 79–80, located
by the passage's own opening and closing words rather than by typed offsets, into
`engineering.mechanics`. Chemistry is a separate campaign and no artifact here touches it.

`run_cycle` is the only entry point and the fixture chapter is now its *default argument*
rather than a separate path, so the real source travelled the same nine functions W0's
fixture did. **What one real passage found, that six authored ones could not:**

- **The passage crosses a page boundary.** `pdftotext` puts the folio numbers `67` and `68`,
  a form feed and the running head `2 • Motion in One Dimension` in the **middle** of the
  worked example, at offsets 178, 183 and 187. They are kept in the registered bytes: a
  campaign that cleans its sources cannot afterwards prove what it read.
- **The arithmetic is an image.** Under `Solution` the text layer carries `2.2` — an equation
  number — and nothing else. This class of source states results and hides derivations, so
  the cross-check's second leg is the only thing between the campaign and a number nobody
  checked.
- **The passage asserts its answer at two precisions**, "about 110 m east" and "a calculator
  shows the answer as 110.4 m". Which one an extraction takes decides accept or quarantine,
  so the rule is fixed for the campaign: the exact value when the passage states one.

The kernel verified the physics and the checker accepted the derivation. Then the platform
refused the content — see W1-F5 and W1-F6. Both verdicts are kept in the record, because
"the evidence accepted it" and "the platform refused it" are different facts and W2 needs
both.

### W1 findings

#### W1-F3 — the cross-check compared a number with a notation

The mechanics kernel answers in exact rationals and renders them with `str(Fraction)`, so
2.4 m/s for 46 s comes back as `552/5`. The textbook writes `110.4 m`. `assertion_agrees`
compared them as **strings** and would have quarantined a correct passage for spelling its
answer differently. Every asserted value in the fixture chapter happened to be an integer,
which is exactly why the fixture could not find this.

The comparison now reads numbers where both sides are numbers. It is deliberately **not** a
tolerance: `Fraction('110.4') == Fraction('552/5')` is exact equality, so the passage's own
rounded "about 110 m" still disagrees with the kernel and is still refused. Widening this
into a significant-figures tolerance would be tuning the check until the source passed.

A guard was needed twice. Excluding booleans from the numeric path is not enough, because
Python's `True == 1` is true on the fallback path — so a plant asserting `balanced: True`
against a kernel that computed the number `1` would have agreed. A boolean is a verdict, and
a verdict is not a magnitude. The W0 slice record is **byte-identical** after the fix, which
is the evidence that the plant is still caught and the five genuine segments still pass.

#### W1-F4 — the pre-registered procedure could not be executed, and was amended in public

Revision 1 of the reindex procedure raised `maintenance_work_mem` to 12 GB **and** kept
`max_parallel_maintenance_workers = 4`. A parallel HNSW build puts its shared graph in
dynamic shared memory, which PostgreSQL allocates from `/dev/shm` — capped at 2 GB by the
container, a limit 22B itself raised from Docker's 64 MB default in its own W1-F5, sized for
the build 22B ran. So the procedure asked a 2 GB filesystem for 12 GB and died with
`DiskFullError … No space left on device` on a host with 821 GB free. The two settings are
safe apart and incompatible together, and neither one's documentation says so. It failed
**after** the precondition measurement and **before** any index was touched, so 22B's
restored index was left exactly as sealed.

Revision 2's record calls that measurement "40-minute", which was the estimate held when it
was sealed; revision 2's own precondition then measured **685 s**. The estimate is left
standing rather than corrected, for the same reason revision 1 is: the record says what was
believed when it was written, and the measurement that refined it is in the record beside it.

Revision 1 is **not edited**. It stays sealed in `sprint-22c-repair-plan.json` as published,
because a pre-registration that is rewritten after it fails is not a pre-registration.
Revision 2 is a record of its own, names revision 1 by hash, quotes the error, and sets
`max_parallel_maintenance_workers = 0` — a serial build takes its memory from the backend's
own heap, so the raised budget is honoured without touching `/dev/shm` and the procedure runs
on a default container instead of requiring an infrastructure change. Revision 1's claim that
parallel workers were "rebuild wall-clock only" was too confident and is **withdrawn** in
revision 2: an HNSW build is order-dependent and a serial build is a different graph. What is
unchanged is the hypothesis under test, which is about the memory budget, and the reading.

The operational half: the precondition costs eleven minutes and the rebuild that follows it
can fail. It is now **sealed into its own record the moment it is read**, before anything is
put at risk — revision 1's failure threw away a measurement that had already succeeded and
told nobody.

#### W1-F5 — the campaign promoted an item the Corpus Factory had refused

`stage_quarantine` consulted the cross-check and nothing else, so an item the released
`CorpusFactory` had already routed to **quarantine at stage 1** sailed through it, compiled,
and was promoted. The fixture chapter is Apache-2.0, which the factory approves, so at
fixture scale the two decisions always agreed and the seam was invisible — the exact seam
§3.1 predicted, found by the first real passage.

A campaign may be stricter than the Corpus Factory. It may never be more permissive: the
factory owns licence, sensitivity and routing, and an acquisition pipeline that overrides it
has taken an authority §1.2 does not give it. The stage now refuses on either ground and the
record keeps them apart. W0's slice record is byte-identical after the fix, which is the
evidence that the fixture never depended on the bug.

#### W1-F6 — the released licence policy has no vocabulary for open content, and this blocks W2

`corpus.factory.APPROVED_LICENSES` is `{Apache-2.0, MIT, BSD-3-Clause, CC0-1.0}` — a
**software**-licence allowlist. No Creative Commons content licence except CC0 is in it, so
`CC-BY-4.0` classifies as `UNKNOWN`, routes to `QUARANTINED` with `license-review-required`,
and stays there. That is the entire class §1.3 names as this sprint's natural candidates.
There is no released path to present a **completed** licence review — and one exists, sealed,
with a named authority and the licence page hashed (S22C-020). The factory has no way to be
told.

Its second half: `CorpusConfiguration` offers `unknown_license_action` and five siblings, and
`CorpusFactory._route` **hard-codes the same outcomes instead of reading them**. Six settings
that describe behaviour nothing consults. Today they happen to agree, so nothing is wrong and
nothing is honest either: an operator setting `unknown_license_action = "reject"` gets a
quarantine and no warning.

**This blocked cycle 1 for both campaigns**, and the wave surfaced it rather than absorbing
it — §1.2 is explicit that a primitive needing more than composition is a finding to surface.
**Resolved by W1-D2 above**, which took neither candidate and named the design error behind
both.
Widening a platform-wide licence allowlist so this wave's slice turns green is the move this
programme refuses. The decision is the gate owner's (§1.3), and **the obvious fix has a
consequence the plan did not anticipate**:

| Resolution | Consequence |
|---|---|
| Add the CC BY family to `APPROVED_LICENSES` | **This would deny the chemistry campaign, not merely quarantine it.** A `RESTRICTED` licence routes to `CorpusRouteStatus.DENIED`, and CC BY-NC-SA is restricted by any honest reading of NonCommercial. Approving CC BY while classifying CC BY-NC-SA restricted ends the two-campaign plan chosen in W1-D1 |
| Give the factory a path to accept a completed licence review | A released feature rather than a policy edit, and the one that matches what actually happened: the review exists and is sealed; the factory cannot hear it |

### W1 evidence index

| Record | Item | Integrity |
|---|---|---|
| [`sprint-22c-repair-plan.json`](evidence/sprint-22c-repair-plan.json) | S22C-030 rev 1 — the procedure that could not run, kept | `8488e6c929ae4e67…` |
| [`sprint-22c-repair-plan-r2.json`](evidence/sprint-22c-repair-plan-r2.json) | S22C-030 rev 2 — supersedes rev 1 by hash | `20ad115d49a091e2…` |
| [`sprint-22c-w1-event-repair.json`](evidence/sprint-22c-w1-event-repair.json) | S22C-031 — the planted orphan, repaired by one resume | `07c79a3d6a4a0a31…` |
| [`sprint-22c-w1-crash.json`](evidence/sprint-22c-w1-crash.json) | S22C-031 — 22B's crash re-run: 1 → 0 | `e102f38f0fa68251…` |
| [`sprint-22c-w1-restore-precondition.json`](evidence/sprint-22c-w1-restore-precondition.json) | S22C-032 — 22B's 0.9410, independently re-read | `d03bac866ccf674b…` |
| [`sprint-22c-w1-restore-reindex.json`](evidence/sprint-22c-w1-restore-reindex.json) | S22C-032 — the procedure applied, the floor re-read | `67c832f93060b6c5…` |
| [`sprint-22c-w1-slice.json`](evidence/sprint-22c-w1-slice.json) | S22C-033 — the real source through nine stages | `850c56b33c5709f1…` |

Drivers: [`scripts/repairs_22c.py`](../../../scripts/repairs_22c.py) and
[`scripts/slice_22c.py`](../../../scripts/slice_22c.py). Released change:
`MemoryEventService.ensure_item_created` and `MemoryService.create`, bound into the
pre-registration by `repair_source_hash` so a drift in either fails `--check`.

### W1 validation

`ruff check` and `ruff format --check` over `src tests scripts infra`, `mypy src/cognitive_os`
(638 files), `bandit -r src/cognitive_os` (0 issues at every confidence), contract schema
export `--check`, and the repository language policy — all clean. Whole suite:
**4 333 passed, 107 skipped**. Three new test modules — 8 tests pinning the write-path repair
over the ports with no database, 33 reading the W1 records, and 13 pinning W1-D2's licence
authority in released code. The four contract schemas the ruling changed are re-exported and
`--check` passes; `LicenseDeclaration`'s is untouched, which is why `SourceManifest` hashes
are unaffected by the new fields.

### What W2 inherits

**Unblocked:** the repaired governed write path, in released code, under every campaign write
from here on. The restore procedure, pre-registered, executed and read.

**Unblocked by W1-D2:** cycle 1. The released Corpus Factory now advises on a licence and an
operator decides it, both cleared sources are carried as `OperatorLicenseClearance`, and the
real passage travels all nine stages to a promotion whose citation chain resolves to loaded
source bytes.

**Carried by name, unchanged:** W2-A1, W3-A1, 22B W2-F2, W0-A1 (four of six enumerated
domains retain no evaluation cases). **Newly owed:** the crash window itself, which the
resume repairs but does not close.

---

## W1 groundwork — the gate opened, and the licence that was not what it said

**S22C-020.** [`sprint-22c-source-rights.json`](evidence/sprint-22c-source-rights.json),
integrity `0069209ccadca52b…`. Driver:
[`scripts/source_rights_22c.py`](../../../scripts/source_rights_22c.py).

W0 closed with one thing outstanding and refused to invent its way past it. The gate owner
has now nominated two sources, and the review is **concluded**:

| Source | Licence | Domain |
|---|---|---|
| `Physics_-_WEB.pdf` — OpenStax High School Physics, ©2020 Texas Education Agency | **CC BY 4.0** | `engineering.mechanics` |
| `chemistry-2e_-_WEB.pdf` — OpenStax Chemistry 2e, ©2026 Rice University | **CC BY-NC-SA 4.0** | `science.chemistry` |

### W1-D1 — the nomination said CC BY; one of the two is not

Both files were nominated as "CC BY, OpenStax-class". The driver does not write a nomination
down as a fact: it locates the licence statement by searching each PDF's front matter, reads
that page, and hashes **those bytes** as the clearance's evidence. The physics book is CC BY
4.0, as nominated. The chemistry book says, in its own words, *"licensed under a Creative
Commons Attribution **Non-Commercial ShareAlike** 4.0 International License … for
noncommercial purposes only. Any adaptations must be shared under the same type of licence."*

That is not a paperwork detail. **NonCommercial** bars commercial use of everything derived
from the chemistry book, and **ShareAlike** propagates to every adaptation — which reaches
forward into 22D, whose Layer 1 is precisely this acquired-knowledge store. A record that had
transcribed "CC BY" would have been the most expensive kind of wrong thing available to this
sprint: a clearance that looks valid, on bytes it does not describe. W0's second gate probe —
*a clearance issued against different bytes* — was written for exactly this shape, and here
the shape arrived in real content rather than in a probe.

**The gate owner's decisions, recorded rather than inferred.** Two campaigns, one per source,
so no artifact ever merges a CC BY lineage with an NC-SA one: the permissive lineage stays
unencumbered and the ShareAlike lineage stays labelled at every derivative. And the campaign
is research and internal use, not commercial — so the chemistry source is cleared for
`internal_use`, `derivative_work` and `benchmark_use` only, with `commercial_use` barred by
the licence and `public_release` excluded by decision. The physics source is cleared for the
full vocabulary, because CC BY permits it and needlessly narrowing a permissive licence would
be a fiction in the other direction.

Both clearances are built **through the released `CampaignSourceRights` contract**, so they
are validated by the same code the campaign validates them with, and each is then put through
the gate both ways: it admits the real content hash and refuses a neighbouring one. A
clearance nobody put through the door is a clearance nobody tested.

### W1-F1 — a `--check` that re-derives a world observation cannot survive the world changing

Sealing the clearance immediately broke `rights_22c.py --check`. That validator rebuilt the
whole W0 record and compared it, and part of the W0 record is an *observation of the world* —
whether a rights-review file existed. The moment one did, the check reported W0's record as
unreproducible, which is false: the record is intact, and it is true, because it states what
was so at W0.

The W0 record is **not edited**. Editing history so a validator passes is the failure this
sprint exists to avoid. Instead the validator now splits its fields the way 22B's reference
host did (S22B-002): *invariants* — the five gate probes and the fixture clearance — are
recomputed and compared, so a gate that stopped refusing would still fail the check;
*observations* — `source_rights_review` and `blocking_dependency` — are recorded and compared
by nothing. The stored seal is verified separately over the full body, observations included,
so the fields the check no longer recomputes are still protected from being edited. The check
now also reports `world_has_moved_since_w0: true`, which is the honest thing for it to say.

This is the same family as 22B's W3-F4: *a summary may bind only what cannot move underneath
it*.

### What this unblocks, and what W1 still owes

The three prerequisites were verified present rather than assumed: 22B's backup dumps
(6.1 GB full dump under `backups-s22b`), the 22B source store still at 16 GB with its
clustered corpus, and 821 GB free. `cognitive_os_s22c_restore_test` is provisioned at head
`0015` and empty.

W1's remaining work is unchanged and now unobstructed: the two inherited repairs
(22B W3-F1's atomic record-and-event, 22B W4-F1's post-restore reindex), each proven against
the reproduction bound by hash in the baseline, and then the real source's first segment
through all nine stages into one domain.

`sprint-22c-source-rights.json` is what `rights_22c.py` reads to decide the review has
concluded, so the W0 blocking dependency is discharged by a file rather than by an assertion.

---

## W0 outcome — the authority, the gate that blocks, the drivers, and the freezes

Five scripts, one new contract module, six sealed records, two test modules with **54
tests**, **six findings**, one decision and one carried observation.

22B's W0 had five thresholds in front of it and asked the gate owner for nothing. 22C's has
five *sentences* in front of it — four pipeline-integrity claims and one usefulness claim
nothing in the programme has ever made — and it does have to ask the gate owner for
something, because §1.3 puts a rights gate in front of the whole sprint and the review has
not concluded. So this wave splits cleanly in two: **everything that does not need the real
source is finished**, and **the one thing that does is surfaced as a blocking dependency
with the gate built, executed, and currently refusing.**

Three of the six findings were found only by *running* the pipeline rather than reading it,
and the sharpest of them — W0-F3 — is the exact failure §3.1 predicted at the corpus →
semantic → memory seam, at fixture scale, in W0, for the price of one afternoon rather than
of cycle 2.

### S22C-000 and S22C-001 — the starting point, read from the authority that owns it

[`sprint-22c-baseline.json`](evidence/sprint-22c-baseline.json), integrity
`6ddd1e8950d7a923…`, file `578a36f2ae88c035…`.

| Fact | Result |
|---|---|
| `sprint-22b-scale-baseline` resolves remotely as an annotated tag | yes, object `084d561ddc3def7a…` peeling to `dc4006116ff2cfac…` |
| local and remote tag handles agree | yes |
| **the tag peels to the current `origin/main`** | yes — checked rather than assumed, because 22B had to re-cut this tag after a squash merge stranded it |
| both 22C outcome tags | **absent**, checked rather than assumed |
| 22B exact-head post-merge CI run `31804585618` | re-read from the API, **30 of 30 successful** |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015`, counted from `infra/postgres/alembic/versions` |
| **fourteen** predecessor artifact roots | fingerprinted through the released `reality_integrity.fingerprint`; the twelve with a released expectation match it, drift **zero** |
| 22B's own two roots | **first observations**, for exactly the reason 22A's own root was one in 22B |
| stores written to before this record | **none** |

The record also binds, **by hash rather than by retyped number**, the two reproductions W1
is required to beat. That is the whole point of the file for this sprint. W1 owes
`items_missing_an_event == 0` after re-running 22B's crash, and clustered recall back over
`0.95` from the sealed `0.9410`; a baseline that restated those as constants would let the
comparison drift the moment either record moved. The three sealed throughput numbers 22B
measured are bound the same way, as campaign budget lines a later wave reads rather than
rediscovers.

**S22C-001**: four databases were created through the released
`postgres_provision_evidence.sh` under the `cognitive_os_s22c` prefix — the campaign store,
a **holdout store**, an integration store, and a restore target for W1's W4-F1 repair. All
four migrated to head `0015`, fifteen migrations, 114 tables, and the app role has **no
DELETE** on `cognitive_os.events`, inherited from the released grants rather than applied by
hand. Roots `artifacts-s22c`, `backups-s22c` and `artifacts-s22c-holdout` created empty.
The baseline was taken *before* any of this, so its `before` is genuinely before.

The holdout store exists because §2.2c requires the holdout to live outside the campaign
store and 22B's W1-F6 is a standing rule here: separate **by construction, not by promise**.
Its name is not derivable from the campaign's own connection string, so a driver handed only
`COGOS_DATABASE_URL` cannot reach it by any code path.

### S22C-002 — the rights gate, and the one thing this wave asks for

[`sprint-22c-rights-gate.json`](evidence/sprint-22c-rights-gate.json), integrity
`85e0b74a865b0da5…`.

The allocation's §7 permitted the source-rights review to begin during the scale sprint.
Read from the repository rather than from the plan's expectation: **it has not concluded.**
22B's execution record names no rights work, and no rights evidence file exists. §3.2 says
exactly what W0 does with that, and this wave did it — surfaced the blocking dependency with
a named owner and the exact list of fields a concluded review must produce, and **registered
no substitute source and picked no chapter**, because §1.3 reserves that choice to the gate
owner and a campaign run on an unclear source is evidence that cannot be released.

What the wave refused to do is more interesting than what it recorded, so the gate is
**executed** rather than described. Five probes, four of which must refuse:

| Probe | Result |
|---|---|
| no rights record at all | refused |
| **a clearance issued against different bytes** | refused — the dangerous one, because it looks cleared |
| a record carrying an unconcluded review | refused by the contract itself: `CampaignSourceRights` cannot hold `status=not_cleared` |
| a campaign use the clearance does not permit | refused by `CampaignManifestV1` |
| a matching clearance for the fixture chapter | **admitted, as it must be** |

The fifth probe is the one that makes the other four mean something. A gate that refuses
everything has not been tested either, and 22A W4-F2's lesson is that a check which cannot
notice a change proves nothing when it passes.

**This blocks W1, not W0.** §3.1 has W0 running the whole chain against a fixture-scale
source *before* the real source is touched, so every driver, freeze and test below is
complete and none of them read an uncleared byte.

### S22C-003 — the drivers, executed rather than described

[`scripts/campaign_22c.py`](../../../scripts/campaign_22c.py), and its fixture-scale run in
[`sprint-22c-w0-slice.json`](evidence/sprint-22c-w0-slice.json), integrity `dfee2af1c59faeb1…`.

Everything §1.2 lists is in one module — the cycle runner, the rolling replay harness, the
citation walker, the planted-update fixture and the fixture source — because five scripts
sharing a manifest, a store composition and a stage enumeration are one script wearing five
hats. What is **composed** rather than rebuilt is the load-bearing part:

| Stage | Composed from |
|---|---|
| register source | `CorpusFactory.ingest` — rights, licence, sensitivity, lineage, routing |
| extract | sealed proposals, revalidated by the released provider-revalidation legs |
| normalize | the released `SemanticExtractionProposal`, grounded in artifact bytes |
| cross-check | the pilots' own deterministic kernels through `run_descriptor_case` |
| quarantine | the released `CorpusQuarantineReason` vocabulary |
| compile | `SemanticExtractionService.commit` and `MemoryService.create` |
| evaluate | `run_descriptor_case` again, over every domain `registry.domain_ids()` names |
| promote | `SemanticPromotionGate.decide` then `SemanticMemoryService.transition_claim` |
| observe | the event store the other eight stages already wrote to |

The one thing the module adds is **sequence**, and the refusal that goes with it: `enter` is
the only way into a stage and it compares against `CAMPAIGN_STAGES` rather than a list
retyped at the call site, so "three completed cycles" is a countable claim rather than a
description. A pass that skipped a stage raises, and the record says which stage was due.

The slice ran all nine stages end to end at six segments across the two pilot domains:
source registered through the factory, six sealed proposals revalidated on the host with
**zero provider calls**, six claim structures grounded in loaded artifact bytes, six
deterministic cross-checks, one quarantine, five compiled memory records, a replay over
**all six** enumerated domains, five promotions through the released gate, and a citation
walk over **every** promoted artifact — not a sample — each of which resolved back to loaded
source bytes.

The record states in its own body that it **decides no exit criterion**: every 22C exit is a
claim about the real rights-cleared source across three cycles, so publishing the
pre-registration after this run is not publishing it after the numbers.

Two slice results are worth naming because they are the drivers refusing to flatter
themselves. Four of the six enumerated domains report `cases: 0` — reported rather than
omitted, which is W0-A1 below. And the plant's record says plainly that the released
`domains.checker` **accepted** its derivation, which is W0-F4.

### S22C-010 through S22C-018 — revision 1, frozen before the first cycle

[`sprint-22c-contracts.json`](evidence/sprint-22c-contracts.json) and
[`sprint-22c-pre-registration.json`](evidence/sprint-22c-pre-registration.json).

Nine sealed contracts: the five exit sentences verbatim, §2.2's five readings, the campaign
manifest contract, the §1.4 decision, and the fixture source with its recipes hash.
`measured_values: 0`, `thresholds_changed: 0`, `amendments_made_by_22c: 0` — structurally
zero, because 22C's plan contains no gate-owner amendment path at all — and a chronology of
five zeros.

The recipes are **imported from the modules that implement them and hashed from there**,
never retyped, so a driver that drifts drifts this record too and `--check` catches it. The
pin is on the readings and the source, not on the driver's bytes: 22B's W1-F2 cost a wave
when revision 1 pinned an implementation and W1's first act was a defect fix.

**The one thing 22B did not have to freeze.** §3.2 schedules this sprint around the risk
that the pipeline works perfectly and the artifact still does not move the holdout. A
holdout frozen as prose would let W3 discover, after three cycles, that its two arms were
never mechanically different — so the pre-registration runs the **arm mechanism** on a probe
case *deliberately outside the holdout set*. Arm A refused, arm B accepted by the released
checker with the expected answer, holdout still at `measured_values: 0`. The improvement
exit is now a comparison that can distinguish something, and that was established before a
single cycle was paid for.

[`sprint-22c-holdout.json`](evidence/sprint-22c-holdout.json) freezes the holdout itself:
four cases across both pilot domains, `domains.checker`, seeds, success definition, and the
two arms. Each case is a released pilot problem whose formal inputs deliberately omit
exactly one declared fact the source chapter supplies. Without it the kernel refuses the
case by design; with it the kernel solves and the *released* checker verifies the answer
independently, so a wrong value from a wrong artifact still fails. That is the existence
proof §4 describes and nothing more — the record says so in its own limitations.

### S22C-004 — the tests

| Module | Tests | What it holds |
|---|---:|---|
| `tests/cognitive_os/campaign/test_campaign_22c_drivers.py` | 23 | stage-order refusal, the four rights refusals, holdout separation, the two cross-check legs, the refusal-as-data guard, replay enumeration |
| `tests/cognitive_os/campaign/test_sprint_22c_w0_evidence.py` | 31 | the six seals, the live release verification, both bound repairs, `measured_values: 0`, the plant's record, the citation walk |

Four properties in that table are fences rather than tests. The **import fence** asserts that
`campaign_22c.py` contains no reference to `holdout_22c` at all, so a wave that reaches for a
holdout case as curriculum breaks the suite instead of the exit (22B W1-F6 made structural).
The **assertion-leg test** asserts that the released checker *accepts* the plant's
derivation, so a future wave that deleted the second cross-check leg would fail here rather
than quietly stop catching plants. The **stage-skip test** enters `normalize` after
`register_source` and requires a refusal. And the **citation test** requires every walked hop
to have loaded bytes whose recomputed hash equals the declared one, so a walk that degraded
into a field-presence check would fail.

Everything runs in memory against the two committed pilot packages, so it all runs in CI,
where no 22C store exists.

---

## W0 findings

Six findings, one decision, one carried observation. Three of the six were found only by
running the pipeline, and one of those three is a defect class that would have cost a cycle.

### W0-F1 — a wave command with 22C's environment loaded migrated the development database

`postgres_migrate.sh` calls `load_postgres_environment`, which sources
`.env.postgres.local` **with `set -a` after** the caller's own exports. Every variable that
file also defines therefore wins, `COGOS_DATABASE_ADMIN_URL` included. Running the migration
with 22C's environment sourced in the shell targeted `cognitive_os_dev`, not the store the
command was meant for. Nothing was damaged — the development database was already at head
`0015`, so `alembic upgrade head` printed no upgrade lines and was a no-op — but had it been
behind, a 22C wave command would have migrated the development store while reporting
success.

The variable that survives is the one `.env.postgres.local` does *not* define, which is why
the prefix guard still held and no database outside `cognitive_os_s22c` could have been
created. Fixed by invocation rather than by editing a released script: every 22C store
command runs with `COGOS_POSTGRES_ENV_FILE=.env.s22c.local`, and the four stores were
re-migrated that way and verified at head `0015` with 114 tables each. This is the mirror
image of 22B's `scale_22b.py` trap — there a driver *did not* source the env file; here a
script sources a *different* one over yours.

### W0-F2 — the released predicate registry has no vocabulary for acquired knowledge

`build_default_predicate_registry()` registers thirteen predicates — `project.*`,
`repository.*`, `task.*`, `verification.*`, `user.*`, `memory.*` — and then calls
`freeze()`. There is nothing under which a technical passage's worked result can be said,
and the registry cannot be extended after construction. A knowledge-acquisition campaign
stops at stage 3.

This is the seam §3.1 predicted, found by running the driver. It is **not** a released-code
change to fix: `PredicateRegistry` is publicly constructible and `register` is public before
`freeze`, which is exactly how `benchmarks/semantic_adapter.py` already builds a registry of
its own. The campaign registry is therefore *the released descriptors plus one*, so acquired
claims and released claims live under one vocabulary rather than two, and the consequence is
recorded rather than hidden: a campaign extraction's `registry_snapshot_hash` is not the
released snapshot hash and cannot be. That is 22A's S22A-030 decision — a registry that
gained something is allowed to say so — one layer down.

The predicate is `domain.worked_example`, functional and bitemporal, which also gives the
released functional-contradiction detector something real to say about two different results
for one topic.

### W0-F3 — the pipeline wrote semantic claims two stages before the check that judges them

**The wave's sharpest finding, and it cost one run to find.**

The first version of the driver committed each claim at **normalize**, stage 3. §9.1 does
not: it creates "semantic revisions" at **compile**, stage 6, two stages after the
cross-check. With the commit at stage 3 the planted passage's claim sat in the semantic store
as a proposed revision, and the released promotion gate's `semantic.critical_contradiction`
verifier then refused the **genuine** claim it contradicts. The run failed with
`chemistry-mass-balance: promotion rejected ['semantic.critical_contradiction']` — the true
claim blocked, the plant the cause.

The consequence generalises past this fixture and is worth stating plainly: **one planted
update would deny promotion to the very knowledge it falsifies.** A content attack becomes a
denial of acquisition, and no exit criterion as written would have noticed, because the plant
*was* quarantined and *did not* reach an active state. The four pipeline exits would have
read green while the pipeline was unusable.

Two repairs were tried before the right one. Retracting the quarantined claim through the
released lifecycle (`PROPOSED → RETRACTED`, legal, history-preserving) did not help: the
released functional detector compares current revisions and does not consult belief status,
so a retracted claim still contradicts. Closing its validity interval would have meant
choosing overlap semantics to suit the fixture. The actual fix was to stop writing at stage
3, which is what the development plan said in the first place — unverified content never
reaches the knowledge store at all, and stage 6 commits only what registration, extraction,
structuring, deterministic recomputation and quarantine have all cleared.

### W0-F4 — `domains.checker` accepts the plant, and it is right to

The obvious cross-check is to run the derived case through the released `domains.solve` tool
and `domains.checker` verifier and quarantine whatever the checker refuses. Running the
slice showed that check **passing the plant**, with `verifier_status: passed`.

It is not a defect in the checker. The checker judges whether the *derivation* is sound, and
the plant's derivation is impeccable: asked whether `2 H2 + O2 -> 3 H2O` balances, the kernel
correctly answers "no", the checker correctly accepts that answer, and the passage's
assertion that it *does* balance is never examined by anyone. A checker that accepts a case
has verified an arithmetic; nothing had verified the literature.

So the cross-check has two legs, and the record keeps them apart. The second compares the
conclusion the **source asserts** against the conclusion the kernel **computes**, and it is
what refuses the plant: `the source asserts structured.balanced=True; the kernel computed
False`. The slice record names the refusing leg precisely rather than crediting the checker,
and a test asserts the checker still accepts the derivation — so deleting the second leg
fails the suite instead of quietly ending plant detection.

### W0-F5 — a refused case raised out of the runner instead of being measured

`run_descriptor_case` has a branch for a solve that did not complete, and for the commonest
refusal of all — a kernel declining a case — that branch is unreachable. The released Tool
Plane records a `failed` event and then **re-raises** `ToolPlaneError`, so the exception
escapes. `UnsupportedProblemType` escapes even earlier, from the registry, and is a
`LookupError` rather than a `ToolPlaneError`.

Any harness that must *measure* refusals rather than merely avoid them would abort on the
first one: a replay over a domain with one malformed case, and — fatally for this sprint —
the holdout's arm A, whose entire point is that the case fails without acquired knowledge.
The improvement exit was unmeasurable until this was fixed.

Fixed once, in the one helper every 22C caller routes through, rather than in each of them:
cross-check, replay and both holdout arms need identical semantics and three copies of a
`try`/`except` is how two of them drift.

### W0-F6 — the pre-registration bound a hash that moved every run

`--check` failed deterministically on both runs. The pre-registration bound the contracts
record's `integrity_content_hash`, and that seal covers the whole body including
`recorded_at` — so the bound value changed every time either record was written, and the
binding asserted nothing.

This is 22B's W2-F1/F2 in a new place: never bind a value that moves with the clock. Fixed
by giving the contracts record a **substance hash** over its body excluding `recorded_at`,
which is what the pre-registration now binds; the full seal stays as the "this file is
intact" check. Both `--check` validators were then run twice and printed identical output on
the second run (22A W4-F3).

### W0-D1 — the §1.4 decision, taken in W0 as the plan requires

The plan's frozen default is taken: **the holdout evaluation runs end to end through
`domains.solve` and `domains.checker`**, resolving by problem type, and its outcomes are
sealed as 22C evidence records rather than `domain_pilot_runs` rows. **`0016` remains a
refusal**; no migration is allocated. 22A's W2-A1 stays carried by name, and W3-A1 is
untouched by any campaign work and stays carried.

This was decidable in W0 because nothing about it needed the source. §1.4 permits the gate
owner to decide otherwise, but only here — a persistence path appearing between cycle 1 and
cycle 3 would make the cycles measurements of different systems.

### W0-A1 — four of six enumerated domains retain no evaluation cases

`registry.domain_ids()` names six domains with both pilots registered, and the slice's
replay executed cases for two of them. The other four — `mathematics`, `physics`, `logic`,
`coding` — report `cases: 0`, reported rather than omitted, because "all retained domains"
is an enumeration the record must be able to be wrong about (22A W4-F1).

That is honest but thin: for four of six domains, "every cycle replays all retained domains"
currently replays nothing. The wave that reads the replay exit must either author retained
cases for the released four or state in the record that four of six retain none. Carried by
name rather than resolved here, because choosing which cases the released domains retain is
campaign-content work and this wave has no source.

---

## W0 evidence index

| Record | File SHA-256 | Integrity hash |
|---|---|---|
| [`sprint-22c-baseline.json`](evidence/sprint-22c-baseline.json) | `578a36f2ae88c035…` | `6ddd1e8950d7a923…` |
| [`sprint-22c-rights-gate.json`](evidence/sprint-22c-rights-gate.json) | `ea269719ded94cd5…` | `85e0b74a865b0da5…` |
| [`sprint-22c-holdout.json`](evidence/sprint-22c-holdout.json) | `690108b25c3ed412…` | `e9dd8fbf8961c9cc…` |
| [`sprint-22c-w0-slice.json`](evidence/sprint-22c-w0-slice.json) | `1287b09371af1d5f…` | `dfee2af1c59faeb1…` |
| [`sprint-22c-contracts.json`](evidence/sprint-22c-contracts.json) | `b343c0db131441a8…` | `d8c78d01e37c4502…` |
| [`sprint-22c-pre-registration.json`](evidence/sprint-22c-pre-registration.json) | `705f5d216843921a…` | `26b4199442cb211d…` |

Drivers: [`scripts/baseline_22c.py`](../../../scripts/baseline_22c.py),
[`scripts/rights_22c.py`](../../../scripts/rights_22c.py),
[`scripts/holdout_22c.py`](../../../scripts/holdout_22c.py),
[`scripts/campaign_22c.py`](../../../scripts/campaign_22c.py),
[`scripts/pre_registration_22c.py`](../../../scripts/pre_registration_22c.py). Contract:
[`src/cognitive_os/domain/campaigns.py`](../../../src/cognitive_os/domain/campaigns.py).

---

## W0 validation

`ruff check` and `ruff format --check` with `--config ruff.cognitive-os.toml` over `src
tests scripts infra`: clean. `mypy src/cognitive_os`: **no issues in 638 source files**.
`bandit -r src/cognitive_os`: no findings. `scripts/export_contract_schemas.sh --check`:
contract schema check passed. `scripts/check_repository_language.sh`: passed. Whole suite:
**4416 passed, 217 skipped**.

Both benchmark lanes no unit test covers were run locally before pushing, per the standing
rule that pytest green is not CI green: `sprint21c1-learned-ci` **16 cases, pass rate 1.0**
and `sprint21c1-learned-seed` **48 cases, pass rate 1.0**, both `learned-replay`. The
learned smoke ran `--confirm-isolated` against the 22C **integration** store with a scratch
artifact root — never the campaign store, whose fingerprint this sprint pins — and returned
healthy with `replay_matches: true` and no correlation or health failures.

Every sealer and `--check` was run **twice** and the second run is the one recorded (22A
W4-F3): `campaign_22c.py --check`, `rights_22c.py --check`, `holdout_22c.py --check` and
`pre_registration_22c.py --check` all reproduced on both runs, the last only after W0-F6 was
fixed.

**Exact-head CI: run [`31824921436`](https://github.com/palkouser/cognitive-os/actions/runs/31824921436),
head `e09857ab02b39fd35de2c572f1adb78dc5bfbfad`, 30 of 30 successful**, on
[PR #234](https://github.com/palkouser/cognitive-os/pull/234). The pull request exists
because the workflow triggers only on pushes to `main` and on pull requests, so a wave branch
receives no CI at all until one is open — which is why every sprint since 22A carries a PR
number, and why a wave that only pushed would have reported "green" against nothing.

Recording that handle moved the wave head, so the head this wave closes on has its own run:
[`31825973602`](https://github.com/palkouser/cognitive-os/actions/runs/31825973602), head
`04c4e8b180d5299cd22dcda609e67a8d026e5763`, **30 of 30 successful**, clean working tree.

---

## What W1 inherits

**Blocked, by name and with an owner:** the source-rights clearance. No sealed rights
record, no source; no source, no cycle 1. The record lists every field a concluded review
must produce, and the gate that will consume it is built and currently refusing. Nothing
else in this wave waits on it.

**Owed before any campaign number exists**, both with their reproductions bound by hash in
the baseline: 22B's **W3-F1** — `MemoryService.create` still commits the record and appends
`memory.item_created` in two transactions, confirmed unchanged in released code at
`application/services/memory_service.py`, and the fix must be proven by re-running 22B's own
crash to `items_missing_an_event == 0` — and 22B's **W4-F1**, a pre-registered post-restore
reindex procedure proven by re-running 22B's restore measurement to clustered recall back
over `0.95` from the sealed `0.9410`. A restore target, `cognitive_os_s22c_restore_test`, is
provisioned and waiting at head `0015`.

**Ready and frozen:** the nine-stage runner with its refusal, the replay harness over
`registry.domain_ids()`, the citation walker that loads bytes, the sealed plant, the campaign
manifest contract, and a holdout whose two arms are already known to be mechanically
different.

**Carried by name:** 22A W2-A1, 22A W3-A1, 22B W2-F2, and W0-A1 above.
