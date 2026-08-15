# Sprint 22C Technical Backlog

## Continual Learning, Knowledge Acquisition, and `sprint-22c-acquisition-baseline`

- Predecessor: Sprint 22B, tag `sprint-22b-scale-baseline`, object
  `084d561ddc3def7a359863222451041e9cc23f5e`, peeling to
  `dc4006116ff2cfac3f7e581253dd5f549ba3ce52`; PR `#233`; exact-head post-merge `main` CI run
  `31802950787`, 30 of 30. **Five of five exit criteria met** — governed ingest 139.35
  items/s, recall@10 0.9636, warm filtered ANN p95 156.7 ms, bounded graph-assisted p95
  234.4 ms, restore reproduces all four §2.2e items — with **one release finding, W4-F1**,
  left unfixed on purpose and handed here with its reproduction.
- Objective and exit, from the
  [execution sprint allocation](execution-sprint-allocation.md): run repeated governed
  learning cycles and transform rights-cleared technical literature into usable Cognitive
  OS knowledge. Exit, frozen there and moved by nobody since: **every cycle replays all
  retained domains**; **a planted harmful update is quarantined**; **a valid new revision
  supersedes the active view without deleting history**; **source citations and hashes
  survive every derivative**; **at least one retained artifact improves a held-out verified
  task**.
- Migration head: `0015`. **`0016` stays a refusal by default.** The campaign pipeline is
  composition over released storage — memory provenance bundles, semantic claims, corpus
  lineage, content-addressed artifacts — and a wave that finds itself needing a migration
  has found a finding. The one candidate exception is named in §1.4 and is a gate-owner
  decision taken in W0 or not at all.
- Outcome tag: `sprint-22c-acquisition-baseline`. Negative outcome tag:
  `sprint-22c-evidence-baseline`, the D-series discipline carried.

**This is the programme's first usefulness claim for acquired knowledge, and the plan says
so.** 22A made domains data; 22B measured the store they live in; 22C must show that bytes
from a real, rights-cleared source can travel register → extract → normalize → cross-check
→ quarantine → compile → evaluate → promote and come out the other end *improving a task
nobody trained on*. Four of the five exits are pipeline-integrity claims that diligent
engineering can meet. The fifth is not, and the sprint is scheduled around that asymmetry
the way D4–D7 were scheduled around Gate L2's rank-quality conditions: the pipeline exits
are necessary plumbing, the improvement exit is the sprint.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](../sprint-21/sprint-21d4-technical-backlog.md) are 22C's
execution contract unchanged, incorporated by reference. Six findings from 22B and its
predecessors graduate into standing rules here, each already paid for once:

- **22B W4-A1** — *when two things changed between two measurements, measure the middle*:
  any before/after claim spanning more than one change measures the intermediate state
  rather than arguing about attribution;
- **22B W1-F6** — *a driver that mutates a corpus must not be pointed at the corpus an
  exit reads*: nothing in any curriculum, extraction retry, or provider call may touch the
  frozen holdout, and the holdout store is separate by construction, not by promise;
- **22B W3-F4** — *a summary may bind only what cannot move underneath it*: sealed records
  bind sources and frozen contracts, never files that later waves legitimately rewrite;
- **22A W4-F1** — *count what a coverage word covers*: "all retained domains" and "every
  derivative" are enumerations named in the record, with a test asserting the enumeration;
- **22A W4-F3** — *run a release command twice before trusting it*: every sealer and
  `--check` runs twice in its own wave, and the second run is the one that counts;
- **D7 W3-F1** — *a digest proves bytes, not usability*: replay executes retained
  evaluation cases, a citation check loads the cited source bytes, and a quarantine claim
  shows the quarantined item refused at the door it would actually enter through.

---

## 1. Verified starting state

### 1.1 What 22B released, and the two repairs it hands over by name

The million-item envelope is measured and sealed, and every campaign budget in this plan is
priced against its numbers: governed ingest **139.35 items/s**, incremental insert into a
built HNSW index **26.1 rows/s** (the 67× penalty — governed ingest produces items 5.3×
faster than the index absorbs them), cold first-touch of a 3.81 GiB index **4.2 s**, and a
restore that costs the index builds over again. Campaign-scale writes (one chapter, three
cycles) are thousands of items, not millions, so none of these numbers threatens a wave —
but each one is a sealed budget line, and a campaign that grows past fixture scale reads
them rather than rediscovering them.

**Two defects are 22C's to fix, both with exact reproductions left behind:**

- **22B W3-F1** — `MemoryService.create` commits the record and appends the
  `memory.item_created` event in **two transactions**; a crash between them leaves a
  governed item permanently outside its own event stream, because the idempotency key
  turns the resume into a lookup that never reaches the event append. One write in 506 at
  one crash; the released health check calls it a warning. The fix is a released-code
  change — record and event in one transaction, or a repair path the resume actually takes
  — and 22B was forbidden to make it mid-measurement. **22C is an acquisition sprint whose
  exits depend on the event stream being the truth**; this is repaired first.
- **22B W4-F1** — `pg_restore` **rebuilds** HNSW indexes rather than copying them, and the
  rebuilt graph dropped clustered recall from 0.9636 to **0.9410, below the 0.95 floor**,
  with no released signal that anything degraded. 22C owns the fix — a post-restore
  `REINDEX` with raised `hnsw.ef_construction`, or `maintenance_work_mem` during restore —
  and owns proving it with the measurement 22B left behind: restore the clustered corpus,
  apply the procedure, measure recall@10 against exact-scan ground truth, and beat the
  floor. 22B deliberately did not tune it, so the number 22C improves is a measured one.

**Carried, still unresolved, on purpose:** W2-A1 and W3-A1 (see §1.4), and 22B W2-F2 — at
10^6 with a 10 % pre-filter the planner answers "filtered ANN" with a sequential scan;
a finding for a future index strategy, not for a campaign whose stores are four orders of
magnitude smaller. Gate L2 and Gate D1 are untouched: 29 of 29 holds, and Gate D1's
usefulness floor is exactly what this sprint's fifth exit begins to address.

### 1.2 What exists, and what must be built

**Exists and is released — the pipeline is mostly composition.** The semantic memory
subsystem carries claims with typed revisions, deterministic claim keys, three
contradiction detectors (functional, registered, evidence), supersession chains, a
promotion gate that runs required verifier capabilities before any claim activates, and a
provider extraction service that treats provider output as a **proposal revalidated on the
host, with no semantic write authority**. The Corpus Factory carries the source
vocabulary the allocation asks for: license status, usage rights, sensitivity, quarantine
reasons, duplicate types, lineage relationships, destination routing. The governed teacher
records a rights decision and a content-addressed receipt for every provider call. Memory
provenance is a validated bundle — unique, canonically ordered, acyclic `MemorySourceRef`s
each carrying a `source_hash` — which is the mechanism the citations exit rides on. 22A's
descriptor spine gives campaign manifests a domain identity to bind: `registry.domain_ids()`
is the enumeration surface, and two worked pilots (`engineering.mechanics`,
`science.chemistry`) have kernels, checkers and committed packages. 22B's restore
machinery, host-record discipline, and driver re-binding pattern carry over unchanged.

**Must be built, all composition unless a gap proves otherwise:** the campaign manifest
contract (`CampaignManifestV1`: source, domain, goals, budget, providers, curriculum,
holdouts, stop conditions — one sealed object per campaign, frozen before the campaign's
first cycle); the campaign cycle runner that drives the nine §9.1 stages in order and
refuses to skip one; the rolling per-cycle replay harness (every retained domain's
retained evaluation cases, executed each cycle, with per-domain rates so drift and
forgetting are visible as numbers); the citation-walk verifier (from any promoted artifact
back to registered source bytes, loading them); and the planted-update fixture (§2.2b).
Any of these that turns out to need more than composition over released primitives is a
finding to surface, not to absorb.

### 1.3 The source, and the rights gate in front of everything

The allocation requires **one rights-cleared technical chapter or paper, processed into
two domains**, and §3.5 makes rights evidence mandatory — provenance and legal constraint,
not confidentiality theater. The allocation's §7 permitted source-rights review to begin
during the scale sprint; whatever its state, **W0 blocks on it**: no extraction touches a
source whose license evidence is not sealed, and the sprint has no source until the rights
record exists. The natural candidates are openly licensed technical material matching the
two pilots — a mechanics text and a chemistry text, or one source both can consume — and
the choice is the gate owner's, recorded in the campaign manifest with the source's
content hash, edition, author, location, license, and permitted uses.

Provider calls during extraction run under the open-development data rule as configured:
no per-call ZDR waiver, `--live` opt-in for any live campaign, spend capped by the
manifest's budget, and every call leaving a governed teacher receipt.

### 1.4 The holdout evaluation path, and the one migration question

The fifth exit needs a **held-out verified task** whose outcome improves when a retained
artifact is active. 22A left a stop in the way: `domain_pilot_runs` has a CHECK constraint
that never learned about descriptor domains (W2-A1), so a pilot-domain evaluation run has
no persisted-run path, and widening it is a migration.

**The default this plan freezes: the holdout evaluation runs end to end through
`domains.solve` and `domains.checker`** — the path both pilots already exercise, resolving
by problem type — **and its outcomes are sealed as 22C evidence records rather than
`domain_pilot_runs` rows.** That measures against the enumeration surface (the 22A
handoff's instruction) without a migration, and W2-A1 stays carried by name. If the gate
owner instead decides the campaign's evaluation runs must persist in released storage,
that is `0016`, decided in W0 before any cycle runs — never mid-campaign, because a
persistence path that appears between cycle 1 and cycle 3 makes the cycles measurements of
different systems. W3-A1 (a released domain cannot refuse a view) is not touched by any
work here and stays carried.

---

## 2. The readings W0 freezes, before any cycle runs

### 2.1 What 22C asks nobody for

No threshold change — the five exit sentences are the allocation's, verbatim. No new
domain registration beyond what campaign content lands in the two existing pilots. No
learner refit, no touch on the canary routing or the live containment component. The
pre-registration is `measured_values: 0`, published before the first cycle, after the
fixture slice.

### 2.2 The five readings that could bend, fixed in advance

**(a) What a cycle is, and what "replays all retained domains" reads.** A campaign cycle
is one full pass of the nine pipeline stages under one sealed manifest. "All retained
domains" is enumerated from `registry.domain_ids()` — released and pilot alike — and
replay **executes** each domain's retained evaluation cases through its checker, per
D7 W3-F1; a hash comparison replays nothing. Per-domain rates are recorded every cycle,
so forgetting is a measured delta, not an alert that fired or did not. **At least three
cycles**, and the count is of completed nine-stage passes — a cycle that skipped a stage
is not a cycle.

**(b) What the planted harmful update is, and what "quarantined" means.** The plant is
authored and sealed in W0 — content-addressed, before any cycle runs, the D-series
hidden-edge-case discipline — and injected through the **same intake path as genuine
content** in a pre-registered cycle. A plant fed to a special door proves the special door.
Quarantined means: the item reaches a quarantine state with a named reason through the
released vocabulary, never reaches an active state, appears in the cycle's quarantine
report, and **stays quarantined through every later cycle's replay**. Detection of
un-planted errors is reported when it happens; the exit reads the plant.

**(c) What "improves a held-out verified task" reads.** The holdout — task set, verifier,
seeds, and success definition — is frozen in W0 with `measured_values: 0`, before any
source byte is extracted. Improvement is the pre-registered comparison: verified success
on the holdout **with the retained artifact active versus without it**, same tasks, same
seeds, same checker, both arms measured in 22C. The holdout is never used as curriculum,
never seen by extraction, and lives outside the campaign store (22B W1-F6 as a standing
rule); a source-leakage check runs before the comparison is read. If the artifact does not
improve the holdout, the sprint reports the measured gap as a typed negative — it does not
go looking for a friendlier task after the fact.

**(d) What "citations survive every derivative" means.** Every derived artifact — claim,
concept, example, problem, procedure, skill, test — carries a provenance chain that
resolves, hop by hop through `MemorySourceRef` and corpus lineage, to the registered
source's content hash. Verified by **walking the chain backward from every promoted
artifact and loading the cited source bytes**, not by asserting the field is non-empty.
The enumeration of derivatives is counted from the store, per 22A W4-F1, and the walk
covers all of them: a citation check that samples has verified the sample.

**(e) What "supersedes without deleting history" reads.** The supersession demonstration
runs through the released lifecycle — candidate → verified → superseded, the guarded
promotion 22B's W3 already satisfied by composition — and is verified two ways that must
agree (22B's own discipline): the active view queried, and the supersession chain walked.
History surviving means the superseded revision is still **loadable with its citations
intact**, and the event stream contains the full transition sequence. Row deletion
anywhere in the path is a finding.

### 2.3 Explicitly out of scope

- any learner refit, conformal machinery, corpus authoring for Gate L2, or touch on the
  canary routing — the retained artifact of exit five is *acquired knowledge*, not a new
  learned component;
- promotion of either pilot domain past `lifecycle: pilot` — 22A refused to invent a
  promotion path for domains, and a knowledge campaign inside a pilot domain does not
  change the domain's lifecycle;
- domains whose honest verification floor cannot be met by deterministic kernels — the
  22A handoff names this question, and this sprint keeps it a question; both campaign
  domains have deterministic checkers, and that boundary is stated in the record;
- local English capability, model selection, adapter work — 22D's, entirely;
- self-improvement proposals — 22E's, entirely;
- resolving W3-A1, or any schema change beyond the single §1.4 decision if taken;
- tuning any pre-registered configuration after its first measured number exists.

---

## 3. Execution waves

| Wave | Work | Exit criterion served |
|---|---|---|
| **W0** | Verify the 22B release from live handles; fingerprint predecessor stores; provision 22C's store pair at head `0015` (or `0016` if the §1.4 decision allocates it — decided here or never). Seal the rights record for the chosen source; refuse to proceed without it. Freeze the campaign manifest contract, the holdout (`measured_values: 0`), the planted update, the §2.2 readings, and the cycle/stage enumeration. Build the cycle runner, replay harness, citation walker, and quarantine fixture; run every stage against a fixture-scale source end to end, including one refused plant and one citation walk | every claim's authority |
| **W1** | **The two inherited repairs, before any campaign number exists**: fix 22B W3-F1 (record and event atomically, or a resume that repairs; re-run 22B's crash reproduction and show zero items outside their event stream) and 22B W4-F1 (pre-registered post-restore reindex procedure; re-run 22B's restore measurement and show clustered recall back over the floor). Both are released-behaviour changes and land **before** cycle 1 so every cycle runs on the repaired system. Then the full-pipeline vertical slice: the real source registered, one extraction segment through all nine stages into one domain, sealed | pipeline integrity; the repairs |
| **W2** | **Campaign cycle 1**, domain 1, full manifest: extract (provider-assisted, receipts sealed), normalize into claims/concepts/examples/problems/tests, cross-check, quarantine pass, compile candidates, evaluate (including the first full-replay of all retained domains), promote through the semantic promotion gate. First supersession demonstration with the two-way verification. Citation walk over everything promoted | replay; supersession; citations |
| **W3** | **Cycles 2 and 3**, extending into domain 2. The pre-registered plant cycle injects the harmful update through the genuine intake path and the record shows it quarantined and staying quarantined. Contradiction demonstration on real extracted content. Per-cycle replay of all retained domains with per-domain rates — three cycles of them, so drift and forgetting are three measured points, not a sentence. **The holdout comparison, both arms**, read once against the frozen definition | quarantine; replay; **improvement** |
| **W4** | The five exits read once from sealed records, `--check` rebuilding the document from sources; full verification matrix; whole suite against the campaign store; report and handoff naming what 22D inherits (the acquired-knowledge store is Layer 1 of the local English roadmap — the handoff prices that inheritance honestly); protected release, exact-head CI, annotated tag `sprint-22c-acquisition-baseline`, remote verification, sealers twice | release |

### 3.1 The first vertical slice

W0 runs the entire nine-stage chain against a fixture-scale source before the real source
is touched, and W1 runs the real source's first segment through everything before cycle 1
commits to the full chapter. Every sprint since D4 found its cheapest defect in the slice.
This sprint's likeliest slice finding is a stage that exists as vocabulary but not as an
executable path — the Corpus Factory's quarantine states, the semantic promotion gate and
the memory lifecycle have never been driven **by one runner in one sequence**, and the
seams between them (corpus item → semantic claim → memory record, each with its own
provenance dialect) are exactly where a citation chain would silently drop a hop. W0 wants
that hop found at fixture scale, not in cycle 2.

### 3.2 The three schedule risks, named

**The improvement exit is the sprint's hardest sentence.** Nothing in the programme has
yet shown acquired knowledge changing a verified outcome — Gate D1's usefulness floor is
open, and the D-series needed four sprints to turn retrieval into rank quality. The
pipeline can work perfectly and the artifact still not move the holdout. Schedule the
holdout comparison as early as cycle-count allows (W3, after cycle 2 if the retained
artifact exists by then), because if it misses, the honest partial — four pipeline exits
met, the improvement gap measured with both arms sealed — is a typed negative worth
releasing, and the earlier it is known, the better the negative's diagnostics.

**Rights clearance is on the critical path and outside the repository.** No sealed rights
record, no source; no source, no sprint. The allocation authorized early review; if it has
not concluded, W0's first act is to surface that as a blocking dependency with a named
owner rather than to substitute a "temporary" source — a campaign run on an unclear source
is evidence that cannot be released and work that cannot be kept.

**Provider extraction is nondeterministic, and the cycles must not be.** A cycle that can
only be reproduced by re-calling a provider is not replayable evidence. Every extraction
lands as a sealed proposal (receipt, request hash, normalized response hash) and the
host-side revalidation is the deterministic half the record binds; replay re-executes from
sealed proposals, never from fresh provider calls. If a cycle cannot be reconstructed
without the network, that cycle's evidence is incomplete and the wave stops on it.

---

## 4. Risks the evidence cannot retire

**One source is one source.** One chapter across two pilot domains demonstrates the
factory, not the library. Generality over sources, licenses, formats and domains is
accumulated by later campaigns; the record claims exactly one traversal.

**Both campaign domains verify deterministically.** The pilots carry unit-checking
kernels, so every cross-check and every holdout verdict rests on a deterministic floor.
Domains without that floor — where honest verification needs proof tools, independent
review, or graded judgment — remain the open question 22A named, and no result here
transfers to them.

**Improvement on one holdout is not a learning rate.** The fifth exit is an existence
proof: at least one retained artifact, at least one held-out task, measured improvement.
It licenses no claim about how fast the system learns, how much a chapter is worth, or
whether cycle 4 would help — those are questions for the campaigns this sprint makes
possible, priced by the numbers it seals.

---

## 5. Definition of done

**On a pass:** all five exit criteria met on sealed evidence under the frozen readings —
three completed nine-stage cycles each replaying every retained domain with per-domain
rates; the sealed plant quarantined through the genuine intake path and staying
quarantined; a supersession verified two ways with loadable history; every promoted
artifact's citation chain walked back to loaded source bytes; and the frozen holdout
improved with both arms measured — plus the two inherited repairs proven against 22B's own
reproductions (zero items outside their event stream after the crash re-run; post-restore
clustered recall back over 0.95), W2-A1 honoured or resolved per the §1.4 decision, W3-A1
carried by name, and the annotated tag **`sprint-22c-acquisition-baseline`** created after
exact-head CI and never moved. The handoff names what 22D inherits: a governed
acquired-knowledge store with provenance-complete English technical content — Layer 1 of
the local-English roadmap — and the measured cost of filling it.

**On a stop:** a typed negative under `sprint-22c-evidence-baseline` naming which exit
failed, at which cycle, with which measured values — the D-series discipline unchanged.
The stop this plan considers most likely is the improvement exit, and the plan's response
is designed in: both arms sealed, the gap measured, the negative released. The stop it
refuses to reach by construction is a campaign whose evidence cannot be replayed without
the provider, or a number met by quietly changing what the number reads.
