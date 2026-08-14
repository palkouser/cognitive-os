# Sprint 22B Technical Backlog

## The Million-Item Envelope, Recovery, and `sprint-22b-scale-baseline`

- Predecessor: Sprint 22A, tag `sprint-22a-domain-baseline`, object
  `58b1a0fa3b4f83de6ff9a3fd5d4023cc747b5276`, peeling to
  `291482448114ffed95a975c2b6a0d2be47a6a092`; PR `#231` and `#232`; exact-head post-merge
  `main` CI run `31573794611`, 30 of 30. **4 of 4 exit criteria met, zero release findings.**
- Objective and exit, from the
  [execution sprint allocation](execution-sprint-allocation.md): learned memory, temporal
  revision and graph-assisted retrieval **operable at 10^6 items**. Exit, frozen there and
  moved by nobody since: recall@10 ≥ **0.95**; warm filtered ANN p95 ≤ **300 ms**; bounded
  graph-assisted p95 ≤ **500 ms**; ingest ≥ **100 items/s** on the declared reference host;
  restore reproduces exact counts, hashes, active views and learned artifact pointers.
- Migration head: `0015`. **`0016` stays a refusal by default** — every scoped mutation
  (supersession, tombstone, bloat, reindex) lives in the released schema, and a wave that
  finds itself needing a migration has found a finding, not a plan item.
- Outcome tag: `sprint-22b-scale-baseline`. Negative outcome tag:
  `sprint-22b-evidence-baseline`, the D-series discipline carried.

**This backlog is a measurement plan wearing a sprint's clothes, and it says so.** Nothing
here fits a learner, authors a corpus, registers a domain or moves a threshold. 22B builds
two deterministic datasets, drives seven retrieval shapes and five mutation behaviours over
them at a million items, breaks the store and restores it, and seals what the numbers are.
The one thing it must resist is the one thing scale sprints always do: quietly redefining a
hard number as a property of a friendlier setup. Every reading that could bend is frozen in
W0 with `measured_values: 0`.

---

## 0. Authority and execution contract

Sections 0.1 through 0.4 of the
[Sprint 21D4 Technical Backlog](../sprint-21/sprint-21d4-technical-backlog.md) are 22B's
execution contract unchanged, incorporated by reference. Six findings from 22A and D7
graduate into standing rules here, each already paid for once:

- **22A W4-F1** — *count what a coverage word covers*: every "per-mode" or "per-dataset"
  claim names the modes and datasets in the record, and a test asserts the enumeration;
- **22A W4-F2** — *a claim about what did not change must be able to notice a change*:
  no `unchanged: true` literal; every such field is a recomputation;
- **22A W4-F3** — *run a release command twice before trusting it*: every sealer and
  `--check` runs twice in its own wave, and the second run is the one that counts;
- **22A W2-F3** — *a released assertion can assume the world cannot grow*: after W1 loads
  a million rows, the **whole** suite runs against that store once, not the slice;
- **D7 W3-F1** — *a digest proves bytes, not usability*: restore is verified by querying
  the restored store and loading the restored artifact, never by comparing hashes alone;
- **D7 lifecycle** — *separate processes or it proved nothing*: warm/cold and
  restart claims are measured across real process and database restarts.

---

## 1. Verified starting state

### 1.1 What 22A released, and the two stops it hands over by name

The domain registry reads its domains as data: string ids, a fail-closed 64 KiB package
boundary, content-addressed storage with a cold rebuild, two pilots registered with zero
new enum references (coupling flat at 52). `registry.domain_ids()` and
`problem_types_for()` enumerate the surface — and the 22A handoff instructs 22B to measure
**against that enumeration surface, not against the pilots**.

**W2-A1 and W3-A1 are carried, unresolved, on purpose.** `domain_pilot_runs` has a CHECK
constraint that never learned about `coding`, so descriptor domains have no persisted-run
path — widening it is a migration, and 22B allocates none; nothing in this plan persists a
pilot run. A released domain still cannot refuse a view. Both stay named in the handoff
chain until a sprint whose objective touches them; pretending 22B resolved them by walking
past them is exactly what the reuse-audit discipline exists to prevent.

### 1.2 The measured 10^5 envelope — the numbers this sprint extends

`scripts/memory_ann_baseline.py` sealed two envelopes at 100 000 vectors, 768 dimensions,
50 probes, on 2026-07-25:

| | uniform gaussian | clustered |
|---|---:|---:|
| exact scan p95 | 328.8 ms | 329.3 ms |
| HNSW p95 (ef_search 1000) | 88.0 ms | **16.5 ms** |
| HNSW recall@20 | **0.496** | **0.992** |
| index build / size | 437.9 s / 410 MB | — |

Three facts to plan around rather than rediscover. **The uniform dataset is adversarial by
construction**: independent gaussians in 768 dimensions have no cluster structure and ANN
recall collapses on them — 0.496 is a property of that geometry, not of the index. **The
clustered dataset clears the recall exit with headroom at 10^5** — whether it still does at
10× the size is precisely the sprint's question. **Index build was 438 seconds at 10^5**;
naive scaling puts a 10^6 build at over an hour, which makes build time, reindex time and
concurrent-read behaviour during both first-class measurements, not footnotes.

Both envelopes carry the same sealed limitation: synthetic rows loaded outside the governed
write path measure the retrieval *engine*, not governed ingestion. That split survives into
this plan as its own pre-registered reading (§2.2c).

### 1.3 What exists, and what must be built

Exists and is released: the four `MemoryRetrievalMode`s (metadata, text, vector, ANN as a
distinct auditable mode), metadata filters combinable with vector search in one query, the
revision model with supersession states, the D-series backup/restore machinery, the EMG
bounded-graph retrieval arm, the live learned component whose artifact pointer a restore
must reproduce, and the ANN baseline harness with its scratch-table discipline.

Must be built in-wave, all measurement-plumbing rather than capability: the two 10^6
deterministic dataset generators as pre-registered recipes; the governed-ingest throughput
runner; the **hybrid** (text + vector), **temporal** (active view as of a moment) and
**stale-item** query recipes composed over released primitives; the **bounded
graph-assisted** configuration (§2.2d); the bloat/reindex/concurrency drivers; and the
restore verifier that queries rather than hashes. None of these changes a released
behaviour; each is a driver over what is already there, and any gap that turns out to need
more than composition is a finding to surface, not to absorb silently.

### 1.4 The reference host, declared once

Every latency and throughput exit is a claim about the declared reference host — the
CPU-first, GPU-free developer machine the D1 gate already declared. W0 seals its exact
CPU model, core count, RAM, storage device and PostgreSQL version into the
pre-registration; every envelope record binds that host record's hash. A number measured
anywhere else is reported with its own host record and closes nothing.

---

## 2. The readings W0 freezes, before any row exists

### 2.1 What 22B asks nobody for

No threshold change — the five exit numbers are the allocation's, verbatim. No migration.
No registry change, no new domain, no learner, no corpus. The pre-registration is
`measured_values: 0` and there is no gate-owner amendment path in this plan at all.

### 2.2 The five readings that could bend, fixed in advance

**(a) Which dataset the recall floor reads.** recall@10 ≥ 0.95 is met or missed on the
**clustered** dataset — the geometry real embeddings have. The uniform dataset is measured
and reported in full as the adversarial bound, exactly as the D-sprints reported
non-selectable cells, and no exit criterion reads it. Frozen now, because after the numbers
exist this choice would be a result, not a reading.

**(b) What "warm" means.** A warm measurement is: index built, PostgreSQL restarted, then
a pre-registered warmup of 100 discarded probes, then the measured probes. Cold numbers
(first query after restart) are recorded beside every warm one. **500 measured probes per
mode per dataset** — ten times the 10^5 envelope's 50, because a p95 over 50 probes is
decided by its three worst.

**(c) Which path each throughput claim measures.** The **ingest ≥ 100 items/s exit reads
the governed write path** — real memory records with provenance, events and revisions,
sustained over at least 50 000 items with the rate reported per decile so a fading rate is
visible. The bulk engine load that builds the million-row corpus is measured and reported
too, as engine capacity, and no exit criterion reads it. The 10^5 envelope's limitation
sentence becomes two sealed numbers instead of one caveat.

**(d) What "bounded graph-assisted" is.** The D1 gate measured the graph arm at p95
1 788.9 ms against a 2 s floor; this exit is 500 ms — **3.6× tighter than the only number
ever measured, at 10× the scale**. The bounded configuration is therefore pre-registered,
not searched: ANN shortlist of width 20, graph expansion budgeted per query with the same
per-pair 250 ms discipline D1 enforced, walk depth capped, and the whole recipe named in W0
with its parameters frozen. If that configuration misses 500 ms, the sprint reports the
miss and the measured slope — it does not tune the recipe against the exit and call the
tuning a configuration.

**(e) What restore must reproduce, as a checklist.** Exact row counts per table; content
hashes of the artifact store; the active view after supersessions and tombstones (queried,
not counted); and the **live learned component's artifact pointer** — the restored store
must resolve `learned.containment.correction_ranking`'s artifact to the same
`afbdb7c0…` bytes and load it, the D7 W3-F1 lesson applied to the one artifact that is
actually live.

### 2.3 Explicitly out of scope

- any learner, corpus authoring, conformal machinery, or touch on the canary routing;
- resolving W2-A1/W3-A1, allocating `0016`, or any schema change;
- registry content changes (22A W2-F3's condition is triggered by store growth, not
  registry growth — the whole-suite run in W1 covers it);
- distributed deployment, sharding, GPU acceleration, alternative index types beyond the
  released HNSW — a measured miss on the released substrate is a finding for 23's plan,
  not a licence to swap substrates mid-measurement;
- tuning any pre-registered configuration after its first measured number exists.

---

## 3. Execution waves

| Wave | Work | Exit criterion served |
|---|---|---|
| **W0** | Verify the 22A release from live handles; fingerprint predecessor stores; provision 22B's own store pair at head `0015`. Seal the reference-host record. Publish the pre-registration with `measured_values: 0`: the five exit numbers verbatim, the five §2.2 readings, both dataset recipes (generator, seeds, dimensions, cluster parameters), probe counts, warmup protocol, the bounded graph configuration. Build and test the drivers (§1.3) against fixture-scale data | every claim's authority |
| **W1** | Generate both 10^6 datasets deterministically; bulk engine load with build time, index size, disk and RAM sealed; **governed-ingest measurement** on the reference host (50 000+ items, per-decile rates); incremental insert into the built index; run the **whole suite** against the million-row store once (22A W2-F3). **Vertical slice first**: every W2 query shape and the restore verifier, executed at 10^4 before 10^6 exists | ingest ≥ 100/s; storage reports |
| **W2** | The retrieval envelope, warm and cold, 500 probes per mode per dataset: exact (also the recall ground truth), ANN (recall@10 against exit), **filtered ANN** (metadata predicate + ANN, the 300 ms exit), hybrid, temporal, stale-item, and **bounded graph-assisted** under the frozen §2.2d recipe (the 500 ms exit). Per-mode records name every mode and dataset covered (22A W4-F1) | recall ≥ 0.95; filtered p95 ≤ 300 ms; graph p95 ≤ 500 ms |
| **W3** | Mutation and recovery at scale: supersession and tombstone waves with the active view queried after each; bloat measured and reindexed with **concurrent readers running and measured throughout**; backup of the mutated store; **restore into a separate pair** and the §2.2e checklist verified by query and artifact load; kill and restart mid-ingest, once, on purpose | restore reproduces everything |
| **W4** | Re-measure the three latency exits on the *restored* store (a restore that changes the envelope is a finding); the exit-criteria record reading all five against sealed measurements; full verification matrix; report, handoff naming what 22C inherits; protected release, exact-head CI, annotated tag `sprint-22b-scale-baseline`, remote verification, release sealers run twice (22A W4-F3) | release |

### 3.1 The first vertical slice

Before W1 generates a million rows, the entire measurement chain runs at 10^4: both
generators, the governed-ingest runner, all seven query shapes, the mutation drivers, one
backup-restore round trip with the full §2.2e checklist, and both sealers twice. Every
sprint since D4 found its cheapest defect in the slice; this sprint's likeliest slice
finding is a query recipe (hybrid, temporal, stale) that turns out to need more than
composition over released primitives — which W0 wants to know **before** the row count
makes every retry expensive.

### 3.2 The three schedule risks, named

**The graph-assisted exit is the sprint's hardest number.** 500 ms against a lineage whose
only measurement is 1 789 ms at a fraction of the scale. The frozen §2.2d recipe is
designed to keep the graph walk off the critical path (ANN shortlist first, budgeted
expansion second), but no one has measured it. Schedule it first inside W2, because if it
misses, the remaining waves proceed unchanged toward an honest partial — four of five exits
met is a typed negative with a measured slope, not a failure to have tried.

**Wall-clock arithmetic owns W1 and W3.** 438 s of index build at 10^5 suggests hours at
10^6; reindex after bloat repeats it; restore verification queries a million-row store.
Budget the waves by machine-hours, run mutations while humans sleep, and never let a
timeout be "fixed" by shrinking the dataset — the dataset size is the sprint.

**Governed ingest has never been measured.** The 100 items/s exit reads a path whose
throughput nobody knows: provenance, events and revision writes per item. If the first
decile comes in far under, the honest moves are already ordered in §2.2c — report the
governed number, report the engine number, and let the gap be the finding. Relabelling the
bulk path as ingest is the one move this plan forbids by name.

---

## 4. Risks the evidence cannot retire

**One host is one host.** Every number is a property of the declared reference host, and
the record says so. Portability of the envelope is 23's question; pretending otherwise
would repeat the mistake the 10^5 record avoided by sealing its limitation.

**Synthetic clusters are not production embeddings.** The clustered generator is a stand-in
with the right geometry class, pre-registered because it is reproducible — but a corpus of
real MiniLM embeddings over real items would have its own structure. 22C's acquisition
pipeline is where real-content scale data first exists; the handoff must say the envelope
is conditional on the geometry, with the uniform dataset bounding the pathological end.

**Recall ground truth costs an exact scan per probe.** At 10^6 × 768 dimensions × 1 000
probes across datasets and modes, ground-truth computation is itself hours of machine time
and is the one measurement nobody can shortcut — a sampled ground truth would make the
recall exit unfalsifiable in exactly the way this programme refuses.

---

## 5. Definition of done

**On a pass:** all five exit criteria met on sealed evidence under the frozen readings —
recall@10 ≥ 0.95 on the clustered million at 768 dimensions; warm filtered ANN p95 ≤
300 ms; the frozen bounded graph recipe p95 ≤ 500 ms; governed ingest ≥ 100 items/s
sustained on the sealed reference host; a restored store that answers queries, serves the
active view and loads the live learned artifact identically — plus the re-measured
post-restore envelope, the whole-suite run against the million-row store, W2-A1 and W3-A1
carried forward by name, and the annotated tag **`sprint-22b-scale-baseline`** created
after exact-head CI and never moved. The handoff names what 22C inherits: two reproducible
million-item datasets, a measured envelope to regress against, and a governed-ingest
number its campaign budgets can finally be priced in.

**On a stop:** a typed negative under `sprint-22b-evidence-baseline` naming which exit
criterion failed, on which dataset, at which measured value and slope — the D-series
discipline unchanged. The stop this plan considers most likely is the graph-assisted
500 ms; the stop it refuses to reach by construction is any number met by quietly changing
what the number reads.
