# Sprint 22E Technical Backlog

## Governed Self-Improvement, Gate M, and `sprint-22-baseline`

- Predecessor: Sprint 22D, released as a **typed negative** — tag
  `sprint-22d-evidence-baseline`, peeling to `cb4d4ad` on `main`; PR `#235`, post-merge
  exact-head CI 30 of 30. **Two of five exit criteria met** (no external LLM during the
  local run; all 18 prior-gate conditions re-read and holding), three unmet with their
  diagnoses attached: local 66 % against a 70 % floor, accounted cost **+5.9 %** against a
  −25 % target, and 26 of 30 factual outputs ungrounded on both measured workloads.
- Objective and exit, from the
  [execution sprint allocation](execution-sprint-allocation.md): close the evidence loop
  from weakness to protected improvement without granting providers autonomous repository
  authority. Exit, frozen there and moved by nobody since: **rejected proposals cause zero
  active-state mutation**; **one approved change reaches protected `main` through PR and
  post-merge CI**; **failed and successful experience is retained and retrievable**;
  **all Gate M conditions pass**; **`sprint-22-baseline` peels to the verified protected
  commit**.
- Migration head: `0015`. **`0016` stays a refusal by default.** One named candidate
  repair (22D W2-F1, the `LOCAL_API` configuration class) sits behind a database
  `CheckConstraint` and therefore behind a migration; if the gate owner selects it, that
  selection *is* the `0016` decision, taken in W0 or not at all — never discovered
  mid-wave.
- Outcome tag: **`sprint-22-baseline`** — the programme-level Sprint 22 tag, not a
  sprint-local one. Negative outcome tag: `sprint-22e-evidence-baseline`, the D-series
  discipline carried.

**This sprint feeds the programme its own findings ledger, and the plan is built on that
being the honest version of "weakness evidence".** Every prior sprint sealed defects with
measured values and exact reproductions; 22E's loop must mine precisely that ledger, turn
one entry into a provider-assisted candidate, carry it through isolation, evaluation and
human approval to protected `main`, and retain the experience either way. And it must do
so knowing what the ledger also says: **Gate M, read against today's sealed records,
does not pass** — conditions 6 and 7 read 22D's negative, condition 5 reads 22C's. What
can legitimately change a condition's verdict is a released repair landing through the
governed path and a re-measurement on a frozen instrument. What cannot is rereading a
sealed number. The sprint is scheduled so the one approved change is spent where the
measured leverage is, and Gate M is read last, against the freshest evidence that
honestly exists.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](../sprint-21/sprint-21d4-technical-backlog.md) are 22E's
execution contract unchanged, incorporated by reference. Six findings from 22B–22D
graduate into standing rules here, each already paid for once:

- **22A W4-F2** — *a claim about what did not change must be able to notice a change*:
  every zero-mutation claim is a recomputed fingerprint comparison over an enumerated
  surface, never an `unchanged: true` literal;
- **22A W4-F3** — *run a release command twice before trusting it*: every sealer and
  `--check` runs twice in its own wave, and the second run is the one that counts;
- **D7 W3-F1** — *a digest proves bytes, not usability*: "experience is retrievable"
  is demonstrated by querying it back out and reading it; "rollback evidence" is a
  rollback executed in isolation, not a manifest that exists;
- **22B W4-A1** — *when two things changed between two measurements, measure the middle*:
  any before/after claim about the approved change isolates the change — same instrument,
  same host, the repair the only delta;
- **22C release lesson** — *a squash merge leaves the wave branch a non-ancestor*: the
  programme tag is annotated **after** the squash merge on the merged `main` head, never
  on the wave branch, and `sprint-22-baseline` peeling to the verified commit is itself
  an exit criterion here;
- **22D W4-F1 / GC-F4 / W2-F5** — *the axis nobody keeps checking is the one that keeps
  failing*: nothing in this sprint may be green under only one command line, one
  interpreter, or one machine; every gate the loop runs is exercised in the CI lane's
  configuration as well as locally.

---

## 1. Verified starting state

### 1.1 What 22D released, and what it hands over

The typed negative is the inheritance, and it is a good one: **a frozen hundred-task
instrument that re-runs from one command per workload**, a registered-verifier floor with
no model judging a model, a cleared hash-pinned local model served through the released
mapping, an escalation policy as a decision function, and a grounding walk that starts
from a generated sentence. Every number Gate M condition 6 and 7 read was produced by
this instrument, which means every re-measurement this sprint may earn is cheap and
exactly comparable.

22D also hands over **four named repairs, none of them made there** — and they are not a
to-do list here either. They are the top of the weakness ledger §1.4 mines.

### 1.2 Gate M, read against today's ledger — the honest starting score

| # | Condition | Reads | Today |
|---|---|---|---|
| 1 | Gate L2 passes | D7's sealed close, re-read at 22D W4 | **holds**, 29 of 29 |
| 2 | Registry v2 adds two domains without core branching | 22A's four exits | **holds** |
| 3 | the 10^6 envelope passes | 22B's five exits | **holds** |
| 4 | three cycles pass cross-domain anti-forgetting | 22C's replay exit | **holds** |
| 5 | a source acquired, verified, learned, **applied** end to end | 22C exit 5 / 22D W1 | **ambiguous** — 22C measured 0/4 improvement; 22D's layer answers 4 holdout tasks grounded |
| 6 | bounded local English passes without a large LLM | 22D exit (b) | **fails as sealed** — 66 % against 70 |
| 7 | large-LLM dependence falls by the declared threshold | 22D exit (c) | **fails as sealed** — calls −4 %, cost +5.9 % |
| 8 | one governed self-improvement reaches protected `main` | this sprint | **22E's to earn** |
| 9 | security, provider, migration, distribution, language gates | CI lanes at head | **holds**, re-read not quoted |
| 10 | post-merge CI and the annotated `sprint-22-baseline` | this sprint's release | **22E's to earn** |

Three of ten do not hold or are ambiguous, and the plan refuses to discover that in W4.
**W0 freezes, with the gate owner, the reading of conditions 5, 6 and 7**: which sealed
record each one reads, and the rule that a 22E re-measurement on the frozen 22D
instrument replaces it **only if** a released repair affecting that measurement has
landed through the governed path first. Condition 5's reading — whether "applied end to
end" is 22C's improvement arithmetic or 22D's grounded holdout answers — is the gate
owner's sentence to write, in W0, before anything is re-measured, because deciding it
afterwards would be choosing a verdict.

### 1.3 The substrate exists end to end — and has never touched the real repository

Released and fixture-proven: the **weakness service** (signal extractors, failure-code
registry, impact scoring, evidence packages), the **proposals service** (change
specification, minimality analysis, risk assessment, validation plan, rollback plan,
provider draft merge with host verification, typed revision transitions, a priority
queue), the **controlled-change service** (worktree isolation with an approver,
database-clone validation, artifact namespace, evaluation matrix, active-state
protection snapshots, typed promotion steps, rollback manifests), and the **experience
compiler with the EMG** behind it. `changes/demo.py` drives the whole chain end to end —
credential-free, deterministic, in memory.

The gap between that demo and this sprint's exit is the sprint: **no proposal has ever
been mined from real weakness evidence, no candidate has ever been generated by a real
provider against the real tree, no evaluation matrix has ever run the real suite, and no
governed change has ever reached the real protected `main`.** Every seam between the
fixture demo and the real repository — worktree against branch protection, sandbox
against a 4.5-minute suite, clone against a store with released grants — is unmeasured,
and §3.1 puts the slice there.

### 1.4 The weakness ledger — the mined field, with measured values attached

The loop's input is the programme's own sealed findings, each carrying a reproduction
and a priced expected benefit — which is precisely what `build_expected_benefit` wants
and what invented weaknesses never have:

- **22D W2-F2** — the registered physics verifiers error on `m/s²` and `Ω`, the units a
  model actually writes. Measured worth: **roughly a dozen tasks per model arm** on a
  local score of 66 against a floor of 70 — the highest-leverage candidate on the board,
  and the one whose landing licenses re-reading Gate M condition 6;
- **22D W3-F1** — the escalation policy is blind to output kind and escalates seventy
  arithmetic tasks for lacking a citation the grounding exit never wanted. One line, and
  22D names it the reason exit (c) could not pass at any local success rate — the
  candidate that touches condition 7;
- **22D's abstention observation** — no model arm has abstained once in four hundred
  answers, though exit (d) has "explicitly uncertain" as a second way to pass. A bounded
  answer-policy change, not an exit rewrite;
- **22B W3-F1** — the `MemoryService.create` two-transaction crash window, confirmed
  still unrepaired in released code, with 22B's exact crash reproduction sealed and
  bound. The cleanest **low-risk** candidate: small, released, and provable to
  `items_missing_an_event == 0` by re-running a measurement that already exists;
- **22D W2-F1** — `ProviderKind.LOCAL_API` released with no configuration class; behind
  a `CheckConstraint`, therefore behind `0016` (§ header). Eligible only by explicit W0
  decision.

W0 seals this ledger as a ranked candidate list with expected benefit, risk class and
reproduction handle per entry. **The plan pre-selects nothing**: the three dry runs and
the one approved change are drawn from it by the gate owner, because the approval
authority is the exit's whole point.

---

## 2. The readings W0 freezes, before any proposal exists

### 2.1 What 22E asks the gate owner for

Two decisions, both in W0, both sealed before any candidate is generated: the
**condition-reading freeze** for Gate M 5/6/7 (§1.2), and the **candidate eligibility
rule** — whether any `0016`-shaped repair may enter the ranked list. Beyond these, no
threshold moves, no amendment path exists, and the pre-registration publishes with
`measured_values: 0`.

### 2.2 The five readings that could bend, fixed in advance

**(a) What "zero active-state mutation" reads.** The active surface is **enumerated** in
W0 — working tree and protected `main`, the governed stores, the active learned pointer,
the artifact roots, the registry snapshot — and fingerprinted through the released
`reality_integrity.fingerprint` before and after every rejected proposal, with the
comparison recomputed (22A W4-F2). At least one rejection is **deliberate and real**: a
genuine provider-generated candidate refused at a genuine gate, not a fixture refusing a
fixture.

**(b) What "one approved change" is.** A repair drawn from the sealed ledger, carried
through the full chain — mined weakness → proposal with rollback plan → provider-assisted
candidate in an isolated worktree → sandbox evaluation matrix → regression, security,
migration, packaging and rollback gates → **approval by the named user** → PR to
protected `main` → merge by the gate owner → post-merge exact-head CI. No provider
merges, tags or deploys anything, and a test asserts the provider's authority ends at
the proposal.

**(c) What a dry run is, and what three of them cover.** A dry run is a complete
lifecycle that stops short of merge — every stage entered in order through the released
transitions, stage-skipping refused (22C's discipline), experience compiled at the end.
The three cover **distinct weakness classes and distinct outcomes**: at least one
candidate must fail its own evaluation honestly and be rejected on the evidence, because
a loop that has only ever succeeded has not been tested (22A W4-F2, applied to a
process).

**(d) What "all Gate M conditions pass" reads.** Read once, in W4, at the release head —
each of the ten bound to the record and dotted field path it is read from, an
unresolvable path **raising** rather than rendering false, `--check` rebuilding the
document from sources (22D's exit-criteria discipline, inherited as a working driver).
Each condition reads the freshest sealed record its W0-frozen reading names; a 22E
re-measurement is admissible only under §1.2's rule, and the record states per condition
whether it read a predecessor's seal or a re-measurement, and why.

**(e) What "retained and retrievable" means.** Both kinds of experience — the failed
candidates' and the approved change's — are compiled through the released Experience
Compiler into the EMG, and then **queried back out**: the record shows a retrieval, from
the store, whose content answers what was tried, what failed, and why, for one failure
and one success (D7 W3-F1). Retention without a demonstrated read is a hope.

### 2.3 Explicitly out of scope

- any autonomous provider authority — merge, tag, deploy, active-memory write — anywhere,
  including "just for the demo";
- rewriting any 22D exit sentence or 22C exit arithmetic — Gate M reads the allocation's
  conditions under W0-frozen readings, and amending a predecessor's exit is nobody's
  option here;
- Layer-1 scale-up, new acquisition campaigns, adapter training, any learner refit —
  the successor campaigns' work, priced by 22C/22D and untouched by this sprint;
- more than one approved change. The exit says one; a second "while we are here" is how
  a governed loop becomes an ungoverned habit. Further repairs are further sprints';
- resolving 22C W3-A1 or 22C W2-A1; any schema change beyond an explicitly selected
  `0016` candidate under §2.1;
- tuning any pre-registered configuration after its first measured number exists.

---

## 3. Execution waves

| Wave | Work | Exit criterion served |
|---|---|---|
| **W0** | Verify the 22D release from live handles; fingerprint predecessor roots; provision 22E's stores at head `0015`. Seal the ranked weakness ledger (§1.4) with expected benefit and reproduction handle per entry. Take the two gate-owner decisions (§2.1) and freeze the five §2.2 readings; publish the pre-registration, `measured_values: 0`. Enumerate and fingerprint the active surface. Slice: the released controlled-change demo, then one fixture proposal driven through every stage to a **rejection**, with the zero-mutation comparison recomputed | every claim's authority |
| **W1** | The isolation substrate against the **real repository**: worktree under branch protection, sandbox running the real suite, database clone validated, artifact namespace. **Dry run 1** — a real provider-assisted candidate on a ledger entry, carried to a deliberate gate rejection; zero-mutation proven by recomputed fingerprints; experience compiled and **queried back** | rejected ⇒ zero mutation |
| **W2** | **Dry runs 2 and 3** on distinct weakness classes, provider-assisted under governed receipts; at least one fails its own evaluation matrix honestly; rollback executed once in isolation rather than attached as prose; experience of both kinds compiled and retrieved | experience retained and retrievable |
| **W3** | **The approved change**: the gate owner selects from the sealed ledger; full chain through worktree, evaluation, gates, named-user approval, PR, gate-owner merge, post-merge exact-head CI. Then the **licensed re-measurement**, if the landed repair touches a Gate M condition: the frozen 22D instrument re-run per workload (condition 6/7 candidates) or 22B's crash reproduction re-run (the crash-window candidate), sealed with the repair as the only delta (22B W4-A1) | one change reaches protected `main` |
| **W4** | Gate M's ten conditions read once against their W0-frozen readings; the five 22E exits read once; full verification matrix and whole suite; report and handoff pricing what 23A inherits; protected release; on pass, the annotated **`sprint-22-baseline`** created on the merged `main` head after the squash merge and exact-head CI, then verified to peel; on a partial, the typed negative under `sprint-22e-evidence-baseline` naming each failing condition with its measured value | Gate M; the tag |

### 3.1 The first vertical slice

W0 ends by driving the released demo and then a fixture proposal through the entire
chain to a rejection; W1 begins by doing the same against the real repository before any
provider is paid. Every sprint since D4 found its cheapest defect in the slice, and this
sprint's likeliest slice finding is a seam the fixture demo cannot see: the evaluation
matrix meeting the real suite's runtime, the worktree meeting branch protection's
required checks, the clone meeting released grants, or a stage transition that only ever
ran in memory meeting a persisted store. W1 wants each of those found on a fixture
candidate, not on the one change the sprint gets to land.

### 3.2 The three schedule risks, named

**Gate M cannot pass as sealed today, and one change flips at most what it touches.**
Three of ten conditions read negatives or ambiguity. The highest-leverage candidate
(22D W2-F2) plausibly moves condition 6 across its floor; condition 7 additionally needs
the escalation repair; condition 5 turns on a W0 reading, not on code. The plan spends
its one approved change where the gate owner directs, re-measures what that licenses,
and prices the rest honestly: **a Gate M partial is this sprint's most likely outcome,
and §5 designs the typed negative for it.** The refused move is reading a sealed
negative as anything but what it says.

**The loop has never met the real repository.** Every seam in §1.3's last sentence is
unmeasured, and the evaluation matrix's cost arithmetic — the real suite is ~4.5 minutes
per run, times the matrix's cells, times four proposals — is wall-clock the waves must
budget, not discover. A matrix cell "economised away" to fit a schedule is the kind of
quiet reading-change this programme exists to refuse.

**Two humans are on the critical path, by design.** The approval is the named user's and
the merge is the gate owner's — the same shape as 22C's rights gate, and handled the same
way: W3 surfaces the decision with the sealed ledger in front of it and blocks until a
human moves. Automating past either is not a schedule fix; it is the exact failure
Gate M's first sentence forbids, and the sprint would rather stop than demonstrate it.

---

## 4. Risks the evidence cannot retire

**One approved change is one change.** The loop demonstrated once is an existence proof
of governed self-improvement, not a claim of autonomy, throughput, or that the next
change is safe because this one was. Gate M condition 8 asks for exactly the existence
proof, and the record claims no more.

**Part of Gate M is inherited, whatever this sprint does.** Conditions 5 through 7
measure 22C's and 22D's systems. A perfectly executed loop still reads their negatives
unless a landed repair legitimately moves a re-measurement; a failed Gate M with a clean
loop is a coherent, releasable outcome, and the plan says so in advance rather than
discovering it in W4.

**Retained experience is retained, not yet proven useful.** Exit three demonstrates
compilation and retrieval. Whether the EMG's memory of this sprint's failures improves
the next proposal is the successor programme's measurement — the same discipline that
kept 22B from calling an enumerable registry a scale claim.

---

## 5. Definition of done

**On a pass:** all five exit criteria met on sealed evidence under the frozen readings —
every rejected proposal's zero-mutation comparison recomputed over the enumerated
surface; the approved change merged by the gate owner and green on post-merge
exact-head CI; both kinds of experience compiled and queried back; all ten Gate M
conditions holding under their W0-frozen readings, re-measurements admitted only behind
landed repairs; and the annotated **`sprint-22-baseline`** created after the squash
merge, verified to peel to the protected commit — the programme-level tag that opens
Sprint 23A. The handoff prices what the alpha inherits: a self-improvement loop with one
real traversal, a weakness ledger with its top entries repaired or still priced, and the
frozen instruments every future re-measurement reads.

**On a stop:** a typed negative under `sprint-22e-evidence-baseline` naming each Gate M
condition that failed, which record it read, and the measured value — with the loop's
own five exits reported separately, because a clean loop under a failed gate is a
result the successor needs, not a failure to hide. The stop this plan considers most
likely is a Gate M partial on conditions 5–7; the stop it refuses to reach by
construction is a provider with authority it was never granted, or a condition met by
rereading what a sealed record already said.
