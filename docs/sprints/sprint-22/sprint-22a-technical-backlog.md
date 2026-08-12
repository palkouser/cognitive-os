# Sprint 22A Technical Backlog

## The Data-Driven Domain Registry, Two Pilot Domains, and `sprint-22a-domain-baseline`

- Predecessor: Sprint 21D7, tag `sprint-21-learning-baseline`, object
  `3025082526cef6d9…`, peeling to `3f5d7379caf85290da45885e22138506211bee2e`; PR `#229` and
  `#230`; exact-head post-merge `main` CI run `31476479587`, 30 of 30 success. **Gate L2
  passes at 29 of 29 and Gate D1's three conditions are closed** — 22A's dependency is
  discharged for the first time since the sprint was allocated.
- Objective and exit, from the
  [execution sprint allocation](execution-sprint-allocation.md): expand beyond the four
  released subjects **without creating domain silos or core branching**. Exit: both new
  domains register without changing the core controller or storage schema; cross-domain
  items are stored once and exposed through multiple governed views; global and per-domain
  replay remain green; invalid domain packages fail closed.
- Groundwork written and verified, **not yet merged and not yet tested**:
  `src/cognitive_os/domain/descriptors.py` (the versioned descriptor contract, the
  fail-closed package boundary, the released-domain adapter) and
  `scripts/domain_survey_22a.py` with its sealed record
  [`sprint-22a-domain-survey.json`](evidence/sprint-22a-domain-survey.json) — see §1.2.
  Writing their test modules is W0 work in this plan, not a done item.
- Migration head: `0015`. **The exit criterion makes `0016` a refusal**: "without changing
  the … storage schema" means a wave that finds itself allocating a migration has left the
  sprint's own contract, and that is a stop to surface, not a plan item.
- Outcome tag: `sprint-22a-domain-baseline`. Negative outcome tag:
  `sprint-22a-evidence-baseline`, the D-series discipline carried over.

**This backlog inverts Sprint 21's shape.** The D-series varied learners under a frozen
gate; 22A varies *nothing that learns* — it moves domain identity from an enum into data,
proves the four released domains unchanged under the move, and registers two pilots through
the same door a hostile package would knock on. The learning surface is explicitly out of
scope: the live component keeps routing its five canary groups untouched, and the one
question the D7 handoff raised about it is decided in W0 rather than drifted into (§2.2a).

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](../sprint-21/sprint-21d4-technical-backlog.md) are 22A's
execution contract unchanged, incorporated by reference: the release-grade meaning of
"done", the wave discipline, the evidence-record shape, and the rule that a wave's defects
are fixed inside the wave. Five D7 findings graduate into standing rules here:

- **W3-F1**: a digest recomputed unchanged proves the bytes did not move, not that anything
  can use them — every carried input a wave plans around is *executed* in a slice first;
- **W1-F2**: a duplicate registry key that silently replaces its predecessor is the failure
  mode of every registry — the descriptor registry refuses re-registration of an existing
  (`domain_id`, `revision`) rather than replacing it;
- **W4-F1**: a validator can outlive the claim it enforces — every compat assertion names
  the sealed record it reads, and an authorised change re-binds rather than edits;
- **W2-F1/F2**: a reproduction check that fails on the passage of time proves nothing — no
  `--check` re-globs a directory, no live stopwatch enters sealed bytes.

---

## 1. Verified starting state

### 1.1 What D7 released, and what of it 22A touches

Gate L2 **passes**: 29 met, 0 failed, 0 not opened. `learned.containment.correction_ranking`
is active on `experience.correction_ranking`, bounded to five canary groups; the bounded
steady-state configuration is sealed and was never entered. The handoff's load-bearing
sentence — **the deterministic containment rung is most of the value, and the fitted
direction adds five admitted decisions to it** — is a fact about the coding domain's
correction surface, and 22A touches none of that surface except to keep replaying it green.
The four §6 risks D7 carried forward travel with the correction component, not with this
sprint.

### 1.2 The groundwork, and the measured starting state

`descriptors.py` defines `DomainDescriptorV1` — stable string ids under an explicit grammar,
revisioned identity, parent/related links, concepts with multi-domain sharing, capability
requirements (verifiers, tools, skills, strategies, units), corpus references by hash,
transfer links as pre-registered claims, mandatory provenance — plus the fail-closed
`validate_domain_package` boundary (bytes in, contract or diagnosed refusal out) and
`released_domain_descriptors()`, which derives the four released domains from the released
problem-type registry rather than transcribing them.

The sealed survey ([`sprint-22a-domain-survey.json`](evidence/sprint-22a-domain-survey.json))
measured the ground the exit criterion is about:

| | |
|---|---|
| modules referencing `DomainKind` | **9** |
| references, counted from the AST | **57** |
| released domains derived as descriptors | 4, each with a content hash |
| registry snapshot hash bound into the record | yes |
| package boundary refusal cases | **6 of 6 refused**, diagnostics stored |

The four derived content hashes are the **backward-compatibility contract**: a wave that
changes any of them has changed released behaviour, and the diff names which domain and
which field. The 9/57 coupling numbers are the quantity W1 must show reaching the adapter
boundary and stopping.

### 1.3 What the D7 handoff refuses, restated as 22A boundaries

- **No third hypothesis class, no new corpus authoring** — 22A fits nothing and authors no
  correction-ranking groups; the containment signal's anatomy dependence is exactly why the
  learned component is *not* extended to new domains here (a domain expansion that varies
  candidate count dissolves the signal by design, and the handoff says so);
- **No steady-state promotion by default** — the sealed canary→steady transition condition
  stays unexercised unless the gate owner takes it as a separate governed decision (§2.2b);
- **Coverage does not transfer on faith** — nothing in 22A moves the conformal bar, the
  admitted set or the routed groups.

---

## 2. The two decisions in front of W0, and the one reading to freeze

### 2.1 What 22A asks nobody for

No Gate L2 or D1 threshold, no amendment, no migration, no new learner. The sprint's own
exit criteria are its gate, and they were frozen in the allocation years of sprints ago.

### 2.2 Two governance decisions, taken in W0 with `measured_values: 0`

**(a) The rung-as-product question, decided rather than drifted into.** The D7 handoff
raised it explicitly: *"if 22A wants the cheap win, the rung is the product."* The
containment ordering is deterministic, label-free and scores 0.84–0.92 where the released
deterministic fallback (`lexical_similarity`) scores 0.61–0.62 — but the released runtime's
seventeen fallback codes are gate evidence (condition 23) that names the lexical ordering.
Making the rung the deterministic advisory is therefore a governed change to a released
surface with its own small evidence trail, or it is not done at all. W0 puts the either/or
to the gate owner with both branches priced; **neither branch blocks any other item in this
plan**, and taking it later under its own record is a legitimate answer.

**(b) The steady-state transition stays closed.** Recorded as a decision, not a default:
22A does not enter the bounded steady state, and the sealed transition condition — canary
tasks, safety regressions, verifier disagreements — remains the named key to that door.

### 2.3 The one reading W0 freezes: what happens to `DomainKind`

The exit forbids changing the core controller and storage schema, and 57 references make
"delete the enum" a different, bigger sprint. The frozen reading: **the enum survives as
the adapter's closed vocabulary for the four released domains, and everything general moves
behind the descriptor boundary.** New domains exist only as descriptors; no new enum member
is ever added; the adapter maps the four released members to their derived descriptors
(ids are the enum values verbatim, so stored records resolve without migration). The
W0 pre-registration freezes the descriptor schema v1, this reading, the two pilot ids —
**`engineering.mechanics`** and **`science.chemistry`** — and the four compat hashes from
the sealed survey.

---

## 3. The work, itemised

### 3.1 The registry seam (W1)

`domains/registry.py` keeps its deterministic, total, fail-closed resolution — that shape
is right and predates this sprint. What changes: the per-domain metadata tables
(`_DOMAIN_METADATA`, `_REQUIRED_TOOLS`) become *derived from descriptors* through the
adapter, and a descriptor-registered domain's problem types resolve through the same
`ProblemTypeEntry` path with `domain` carried as the string id. The proof obligation is
behavioural identity: `registry.snapshot_hash()` unchanged for the four released domains,
the derived descriptor hashes unchanged against the sealed survey, and the full replay
green — the released domains must not be able to tell the seam exists.

### 3.2 Storage without a schema (W1)

Descriptors are `HashedExperienceContract`s: they persist as content-addressed artifacts
and evidence records through the released artifact service, exactly as every Sprint 21
sealed object did. No table, no migration, no `0016`. The registry's loaded state is
rebuilt from artifact bytes at startup and refuses a descriptor whose stored hash does not
match its content — the same discipline every D-sprint store read kept.

### 3.3 The mechanics pilot (W2)

`engineering.mechanics`, revision 1, `lifecycle: pilot`. Two or three problem types with
honestly deterministic kernels over the *existing* physics capabilities — statics
equilibrium and uniform-motion/force-balance checks are unit-carrying computations
`physics.dimension` and `physics.quantity` already verify. Shared concepts declared into
`physics` (multi-domain membership stored once, exposed through both governed views). The
pilot registers through `validate_domain_package` — the same door a hostile package uses —
and the registration record stores the package bytes' hash beside the acceptance.

### 3.4 The chemistry pilot (W3)

`science.chemistry`, revision 1, `lifecycle: pilot`. The honesty constraint bites here:
a chemistry domain whose verifier cannot actually verify is a silo wearing a lifecycle
field. The pilot's problem types are bounded to what deterministic kernels can judge —
stoichiometric mass balance and molar-quantity conversion, which are exact arithmetic over
declared atomic masses with unit dimensions — verified by the existing quantity/dimension
verifiers plus one new *capability name* whose verifier is a deterministic kernel, not a
model. If a candidate problem type cannot be deterministically verified, it is out of the
pilot, recorded as such.

### 3.5 Rejection, quarantine and the silo regression (W3)

The six sealed refusal cases become the seed of a rejection suite that also covers: a
package impersonating a released domain id at a new revision (refused: revision supersession
is a governance path, not a package upload), a package whose capabilities name no registered
verifier (refused at resolution with `MISSING_REQUIRED_VERIFIER`), and a package sharing a
concept into a domain that never declared it back. The silo regression is a test, not a
sentence: registering both pilots adds **zero** new branches on `DomainKind` (the AST count
from the survey is recomputed and must not grow).

### 3.6 Replay (every wave, gated in W4)

Global and per-domain replay green after every wave: the four released domains' benchmark
and verification replays, the correction-ranking surface's own checks (the live component
untouched), and the two pilots' new cases. A replay that goes red inside a wave is fixed
inside the wave.

---

## 4. Execution waves

| Wave | Work | Exit criterion served |
|---|---|---|
| **W0** | Test and merge the groundwork: unit tests for `descriptors.py` (grammar, closed-world validation, adapter derivation against the sealed survey hashes, all six refusals) and the survey script; mypy/ruff/CI; protected-main PR. Verify the D7 release from live handles; fingerprint predecessor stores. Take the two §2.2 decisions; publish the 22A pre-registration with `measured_values: 0`: schema v1 frozen, the §2.3 reading, the two pilot ids, the four compat hashes | fail-closed boundary |
| **W1** | The registry seam and artifact-backed storage (§3.1, §3.2): metadata derived through the adapter, descriptors persisted as content-addressed artifacts, startup rebuild with hash refusal. Prove behavioural identity: snapshot hash, compat hashes, full replay. **Vertical slice first**: one fixture descriptor through package → artifact → startup rebuild → resolution → refusal-on-tamper | no core/storage change |
| **W2** | The mechanics pilot (§3.3): package authored, validated through the boundary, registered, two-to-three problem types solving and verifying end to end; shared concepts exposed through both views; replay green | first new domain registers |
| **W3** | The chemistry pilot (§3.4) and the rejection suite (§3.5): second domain end to end, quarantine and diagnostics demonstrated on the hostile cases, the silo regression (AST count not grown) sealed | second domain; fail-closed; views |
| **W4** | Full verification matrix; global and per-domain replay as the gated claim; the sprint report against the four exit criteria; protected release, exact-head CI, annotated tag `sprint-22a-domain-baseline`, remote verification; handoff naming what 22B inherits | replay green; release |

### 4.1 The first vertical slice

Before W1 builds the seam, one fixture descriptor runs the whole chain — package bytes →
boundary → artifact store → process restart → registry rebuild → problem-type resolution →
a tampered-byte refusal. D4 through D7 each found their cheapest defect in the slice; the
seam this sprint's version will live in is the startup rebuild, because it is the one place
"storage without a schema" can silently become "state in memory" (the D7 lifecycle lesson:
separate processes or it proved nothing).

### 4.2 The three schedule risks, named

**Chemistry's verifier honesty.** The temptation is a pilot that "registers" with verifier
names nothing enforces. The §3.4 constraint is the control, and the W3 record must show a
chemistry candidate *failing* verification for a real reason, not only passing.

**Seam scope creep.** 57 references invite a refactor crusade. The exit needs the four
released domains *unchanged* and the pilots *possible* — every reference beyond the
metadata tables and the adapter boundary is out of scope, and the survey recount in W3 is
the fence.

**The replay bill.** Per-domain replay across four released domains plus two pilots is the
sprint's longest wall-clock item and it runs in every wave. Budget it like D-series corpus
waves: as the thing that finds defects, scheduled early in each wave rather than at its
end.

---

## 5. Risks the evidence cannot retire

**Two pilots prove extensibility, not generality.** Both pilots lean on unit-carrying
deterministic verification, the substrate the released physics domain built. A domain whose
verification is not reducible to deterministic kernels — the 22C acquisition question — is
deliberately not attempted here, and the handoff must say so rather than let two pilots
imply a universal registry.

**Backward compatibility is proven against behaviour, not against use.** The compat hashes
and snapshot hash prove the four released domains resolve identically; they cannot prove no
caller depended on `DomainKind` in a way the adapter reading breaks. The W1 replay over the
whole released surface is the strongest available evidence, and W3-F1's lesson says to run
it, not to reason about it.

**The enum outlives the sprint by design.** §2.3's reading leaves `DomainKind` as the
closed vocabulary of the released four. That is a fence, not a dissolution — the day a
fifth domain needs what only the enum's members get, the fence is the finding, and it
belongs to a successor sprint's contract, not to a quiet exception.

---

## 6. Definition of done

**On a pass:** both pilots registered through the fail-closed boundary with zero core
controller and zero storage-schema changes; cross-domain items stored once and exposed
through multiple governed views; global and per-domain replay green; the hostile-package
suite refused with diagnostics; the four released domains byte-identical in behaviour
(snapshot hash, compat hashes, replay); the two §2.2 decisions on the record; the
annotated tag **`sprint-22a-domain-baseline`** created after exact-head CI and never moved;
a handoff naming what Sprint 22B inherits — the registry a million-item scale test can
enumerate domains from, and the descriptor spine 22C's campaign manifests will bind to.

**On a stop:** a typed negative under `sprint-22a-evidence-baseline` naming which exit
criterion failed on what evidence, the D-series discipline unchanged — including the stop
this plan considers most likely if one comes: a pilot whose honest verification floor
cannot be met by deterministic kernels, which is a finding about the boundary between 22A
and 22C, not a reason to lower the floor.
