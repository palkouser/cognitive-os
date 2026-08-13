# Sprint 22B execution log

- Branch: `sprint-22b-groundwork`
- Backlog: [Sprint 22B Technical Backlog](sprint-22b-technical-backlog.md)
- **W0 closed.** S22B-000 through S22B-004 and S22B-010 through S22B-016 are done. The
  authority is read from the sources that own it, 22B's store pair exists at head `0015`, the
  reference host is sealed, every §1.3 driver is built and has been run end to end at fixture
  scale, and revision 1 is published with `measured_values: 0`. **No threshold moved, no
  migration was allocated, and no released module changed** — the whole wave is new scripts,
  new tests and new evidence.
- **W1 closed.** Both 10^6 datasets exist on the declared host, the storage report is sealed,
  and the **governed-ingest exit criterion is met — 139.35 items/s over 50 000 items**, flat
  across all ten deciles against a floor of 100. The restore round trip passes all four §2.2e
  checks at a million rows, including the artifact leg that W0 could only show failing. The
  whole suite runs green against the million-row store. **Six findings and two decisions**, all
  handled inside the wave; the sharpest is that the host W0 declared could not build the index
  the sprint's exits are defined over. **W0 detail follows first.**
- **W2 closed.** The retrieval envelope is measured on both million-row corpora — seven shapes,
  warm and cold, **7 000 measured probes across fourteen cells** — and **all three exit criteria
  W2 decides are met**: recall@10 **0.9636** against 0.95, warm filtered ANN p95 **156.7 ms**
  against 300, and the bounded graph-assisted p95 **234.4 ms** against 500, the number §3.2
  called the sprint's hardest. **Four of the five exits are now decided and met.** Three
  findings, all in the measurement machinery, all fixed inside the wave; the sharpest is that
  the filtered-ANN exit is met by a query the planner answers without the index.
- W2 wave commit `a1a251b`; CI run **`31673420297`** on that exact head, **30 of 30 jobs
  successful**.
- W1 wave commit `f29aafb`; CI run **`31614344537`** on that exact head, **30 of 30 jobs
  successful**.
- W0 wave commit `613b546`, pull request **#233** against protected `main`; CI run
  **`31581697125`** on that exact head, **30 of 30 jobs successful**. The merge is the gate
  owner's, not the wave's — W0 leaves the branch reviewable rather than merged.
- Pre-registration: revision 1, SHA-256
  `1e0022094ac62dc29e1372fdd93ca060cf558773cddfb9e391373148d9d0dd73`
- Predecessor: `sprint-22a-domain-baseline`, verified live — annotated tag object
  `58b1a0fa3b4f83de…`, peeling to `291482448114ffed95a975c2b6a0d2be47a6a092`; post-merge
  exact-head CI run `31573794611` re-read from the API, **30 of 30 successful**. 22A's four
  exit criteria are met and its release recorded zero findings. 22B's dependency is discharged.
- Migration head: `0015`, unchanged, counted from the fifteen files rather than restated.
  `0016` remains unallocated and is a **refusal**, not a plan item.
- **Eight findings and one decision, every one of them a defect in the groundwork this wave
  was written to test, and all fixed inside the wave.** Three of the eight are gaps in what the
  released system can compose, surfaced rather than absorbed (§1.3). See
  [W0 findings](#w0-findings).
- W0 measures nothing that decides anything. It establishes the authority every later wave is
  bound to, and freezes every reading that could bend once numbers exist. Gate L2 and Gate D1
  are untouched: 22B opens no condition and closes none. W2-A1 and W3-A1 are carried forward by
  name, unresolved on purpose.

---

## W2 outcome — the retrieval envelope, and the sprint's hardest number

Seven shapes, two datasets, **fourteen measured cells at five hundred probes each — 7 000
measured probes**, every one of them after a real database restart and its own hundred
discarded warmups. **All three exit criteria W2 decides are met.** With W1's governed-ingest
number, **four of the five exits are now decided and met**; only W3's restore checklist at
scale remains.

### The three exits W2 decides

| Exit | Threshold | Measured | Decided by | Verdict |
|---|---|---|---|---|
| recall@10, clustered 10^6 | ≥ 0.95 | **0.9636** | clustered, 500 probes | **met** |
| warm filtered ANN p95 | ≤ 300 ms | **156.7 ms** | clustered (worse of two) | **met** |
| bounded graph-assisted p95 | ≤ 500 ms | **234.4 ms** | uniform (worse of two) | **met** |

**The two latency exits are read on the worse of the two datasets, and that is a reading this
wave had to make.** §2.2a froze a dataset for the recall floor and only for the recall floor —
the allocation states the two latency numbers without naming a dataset, and W0 did not add one.
That left a choice still open after the numbers existed, which is exactly the situation §2.2
exists to prevent. The record takes the worse reading, reports both, and says why: an exit met
by picking the friendlier dataset afterwards would be met by choosing what it reads.

### The envelope, warm and cold

Warm is the pre-registered protocol: index built, PostgreSQL restarted, 100 discarded probes,
then 500 measured. Cold is the first probe after the restart, never averaged into the warm
distribution.

| clustered 10^6 | warm p50 | warm p95 | warm max | cold |
|---|---:|---:|---:|---:|
| exact_vector | 1201.8 ms | 1243.5 ms | 1345.8 ms | 1230.2 ms |
| ann | 40.7 ms | 44.2 ms | 56.7 ms | 55.3 ms |
| filtered_ann | 151.3 ms | **156.7 ms** | 165.0 ms | 157.0 ms |
| hybrid | 87.5 ms | 92.1 ms | 290.4 ms | 103.3 ms |
| temporal | 22.5 ms | 25.5 ms | 30.7 ms | 23.3 ms |
| stale_item | 1.4 ms | 1.5 ms | 1.6 ms | 2.9 ms |
| bounded_graph_assisted | 74.7 ms | **158.4 ms** | 259.2 ms | 479.1 ms |

| uniform 10^6 | warm p50 | warm p95 | warm max | cold |
|---|---:|---:|---:|---:|
| exact_vector | 1202.3 ms | 1220.9 ms | 1258.4 ms | 2612.6 ms |
| ann | 155.6 ms | 186.5 ms | 195.4 ms | 232.9 ms |
| filtered_ann | 149.8 ms | 153.8 ms | 159.9 ms | 663.5 ms |
| hybrid | 88.5 ms | 92.7 ms | 295.8 ms | 107.4 ms |
| temporal | 23.3 ms | 28.0 ms | 31.4 ms | 26.7 ms |
| stale_item | 1.4 ms | 1.5 ms | 1.8 ms | 2.8 ms |
| bounded_graph_assisted | 149.7 ms | 234.4 ms | 406.4 ms | **4201.5 ms** |

**The largest number in this wave is a cold one, and no exit reads it.** The uniform graph
shape's first probe after a restart took 4.2 seconds, of which **3 761.9 ms was the ANN
shortlist leg** — the first touch of a 3.81 GiB index whose pages are in neither the buffer
pool nor the page cache. §2.2b defines the exits on the warm protocol, so this closes nothing
and misses nothing. It is still the number an operator restarting under load would meet first,
and it belongs in 22C's budget rather than in a footnote.

**Three shapes do not vary with the dataset and say so on their own records.** `hybrid`,
`temporal` and `stale_item` answer over the governed memory store, which both datasets share;
the corpus tables the million rows live in are not what they read. They were still measured
once per dataset, because the protocol is per dataset and a shape measured under only one
restart would be the one shape whose warm state nobody re-established.

### The graph-assisted number, against the only prior measurement

§3.2 called this the sprint's hardest number: 500 ms against a lineage whose only measured
value was **1 788.9 ms**, at a fraction of the scale. It came in at **158.4 ms clustered and
234.4 ms uniform — 7.6× to 11.3× faster than D1, at ten times the corpus**, with **zero budget
cutoffs and zero per-pair timeouts on either dataset**.

That zero is the number that makes the p95 mean something. `BOUNDED_GRAPH_READING`'s
`the_cutoff_trap` names the failure in advance: a budget cutoff returns a shorter list faster,
so a recipe that cuts off more looks quicker while answering less, and D1 reached 1 788.9 ms
with sixty queries cut off. 22B cut off none, returned a full ten results on every probe, and
the two legs are reported separately — shortlist p95 57.9 ms clustered / 117.0 ms uniform,
expansion p95 120.1 ms / 123.3 ms.

**The speedup is inherited, not achieved.** Two released changes did it, and neither was made
by this sprint: S21D4-041 replaced the per-pair wall clock with `GED_ITERATION_BUDGET`, whose
first distance arrives in ~4.5 ms, and S21D3 made the candidate embedding cache the caller's,
having measured pool re-embedding as roughly 936 ms of the arm's 940 ms median. 22B measured
the arm as it now exists and tuned nothing: the sealed `limits_hash` on both measured records
is the pre-registration's, byte for byte.

**What this number is and is not.** It is a latency measurement of the released arm at the
frozen configuration. The graph half expands the released 80-pair D1 set, joined to the corpus
by `row_id % 80` — §2.3 forbids 22B authoring a corpus, so the 10^6 scale enters through the
shortlist leg and the expansion leg's cost is a property of the released set. **It measures no
quality at all**, and Gate D1's usefulness floor is untouched and still open.

### Recall at a million, and what the 10^5 record does not say

**0.9636 against a 0.95 floor, on 500 probes with an exact-scan ground truth per probe.** Met,
with 1.4 points of headroom — the thinnest margin of the four exits decided so far.

The 10^5 envelope recorded 0.992 on the same generator, and the temptation is to read a decay
from 0.992 to 0.9636 caused by ten times the rows. **That comparison confounds two changes**:
the corpus grew tenfold *and* the metric tightened from recall@20 to recall@10. A smaller `k`
is strictly harder — the ground-truth set is half the size and each miss costs ten points
instead of five. The honest statement is that recall@10 at 10^6 is 0.9636 and clears the floor;
how much of the distance from 0.992 belongs to the corpus and how much to `k` is not decided by
this evidence, and 22B does not pretend otherwise.

The uniform dataset came in at **0.0854**, against 0.496 at 10^5. It is adversarial by
construction, it reads no exit, and it is reported in full — the same discipline the D-series
applied to non-selectable cells. Independent gaussians in 768 dimensions have no neighbourhood
structure for an ANN graph to find, and at ten times the corpus there is ten times as much
nothing to search.

### How the envelope scaled

| | 10^5 (sealed 2026-07-25) | 10^6 (this wave) | factor |
|---|---:|---:|---:|
| exact scan p95, clustered | 329.3 ms | 1243.5 ms | 3.78× |
| exact scan p95, uniform | 328.8 ms | 1220.9 ms | 3.71× |
| ANN p95, clustered | 16.5 ms | 44.2 ms | 2.68× |
| ANN p95, uniform | 88.0 ms | 186.5 ms | 2.12× |

**Ten times the rows cost under four times the exact scan and under three times the ANN.** The
exact scan is sublinear because it parallelises across workers; the ANN is sublinear because
HNSW's search cost grows with the logarithm of the corpus, which is the property the index is
chosen for and the first time this programme has measured it holding at 10^6.

### The host constraint every number carries

Every latency above is a property of the declared reference host, and the part of that host
which decides an ANN latency is not its disk — it is how much of a 3.81 GiB index the server
can hold. **The reference host runs the released compose file's PostgreSQL defaults:
`shared_buffers` is 128 MB, so the index is 30.5× the buffer pool.** It does fit in the host's
46 GiB of RAM, which is why the warm numbers are what they are: they are served by the Linux
page cache, not by PostgreSQL's. Every W2 envelope record seals that arithmetic beside the
numbers it explains.

**22B does not raise it, and the reason is not timidity.** W0 sealed the PostgreSQL memory
settings into the host *invariants* precisely so this could not be quietly adjusted: the sealed
10^5 envelope this sprint extends was measured under these settings, so raising them would buy
better numbers at the cost of the only comparison the sprint has. §2.3 forbids tuning a
pre-registered configuration after its first measured number exists, and the host record makes
a settings change a **supersession**, not an adjustment. The constraint is recorded as a
measured reading, the full contract was executed under it, and every exit was met anyway. What
this host cannot tell anyone is what the envelope looks like on a machine sized for the index —
that is 23's portability question, and §4's "one host is one host" already says so.

---

## W2 findings — three defects, every one in the measurement machinery

Not one of them was in the released system. All three were in the apparatus this wave built or
inherited, which is what the vertical-slice discipline predicts and what a measurement sprint
should expect to find.

### W2-F1 — the settings block reported 128 MB as "163848kB"

The server-memory reading rendered `setting + unit` with no separator, and PostgreSQL's unit
for `shared_buffers` is itself `8kB`. Sixteen thousand three hundred and eighty-four blocks of
eight kilobytes came out as the string `163848kB`: a number that reads as 160 MB, is actually
128 MB, and is wrong either way. A block whose entire job is to state a constraint has to state
it in units a reader can check, so the separator is explicit and the byte count is computed
from `pg_settings` rather than parsed back out of the string. Caught in the first smoke run,
before any measured number existed.

### W2-F2 — the planner declines the HNSW index for the frozen filtered predicate

**The filtered-ANN exit is met at 156.7 ms, and the query that met it never touched the ANN
index.** `probe_corpus` reads the plan back rather than trusting it — W0 built it that way —
and `index_scan_confirmed` came back **false on both datasets** while `ann` came back true.
PostgreSQL answers the frozen predicate with a parallel sequential scan.

The planner is not obviously wrong and it is not obviously right. Forced onto the index with
`enable_seqscan = off`, the same statement runs warm at **38.7 ms clustered and 108.9 ms
uniform** — 4.0× and 1.4× faster than the plan it chose. The cost model's excuse is structural:
pgvector's HNSW scan applies the filter *after* ordering, so the planner prices a filtered
top-k as a long ordered walk and declines it, and on the uniform geometry — where the ANN has
to work hardest — its choice is nearly as good as the index path anyway.

The response is the one §2.3 leaves available and no other. The exit reads the pre-registered
query exactly as frozen, planner's choice included, because a number that had to be forced onto
a plan is a claim about a plan nobody's query will get. **A second pass runs beside it, labelled
a diagnostic, reading no exit**, so the gap between what the planner chose and what the
substrate can do is a measured number instead of an opinion. And the limitation travels on the
record: at 10^6 with a 10 % pre-filter, "filtered ANN" on this substrate is a filtered scan.
That is a finding for 22C's index strategy, not a reason to re-freeze the predicate.

### W2-F3 — the host check called a four-kilobyte reboot a different machine

`host_record_22b.py --check` refused: `the host has drifted … memory`. The machine had rebooted
at 06:41, and `MemTotal` came back **48 199 292 kB against the 48 199 296 kB both host records
sealed — four kilobytes**, on a 46 GiB bare-metal host. `MemTotal` is physical RAM minus
whatever the kernel reserved on that boot; it is not bit-stable across one.

An exact-equality check on that quantity cannot tell a reboot from a hardware change, and the
two demand opposite responses. Left alone, it would have forced a **third host record** whose
change log said "memory" and meant nothing — falsely asserting that W1 and W2 ran on different
machines, and devaluing the one supersession that was real. Superseding was the wrong answer
here for exactly the reason it was the right answer in W1-F5: **W1-F5 changed the machine's
behaviour; a reboot did not.**

So the *comparator* was fixed and the *record* was not touched. Both host files remain
byte-identical, `invariants_hash` still reproduces over the sealed values, and the check now
allows **one mebibyte** on the memory group — 256× the observed drift, three orders of
magnitude below a removed DIMM or a resized machine. A tolerated difference is **printed with
both values on every run**, so the allowance is auditable rather than a check that quietly
stopped checking, and two tests hold the line: one asserts a four-kilobyte drift passes, the
other that a four-gibibyte drift still fails.

---

## W2 evidence index

| Record | SHA-256 |
|---|---|
| `sprint-22b-w2-envelope.json` | `ac2cb734317cccaf…` |
| `sprint-22b-w2-envelope-clustered.json` | `ae81e6288305cd1d…` |
| `sprint-22b-w2-envelope-uniform.json` | `469f395346d09f54…` |
| `sprint-22b-w2-recall-clustered.json` | `fe178fe5be4e1080…` |
| `sprint-22b-w2-recall-uniform.json` | `664167c85c97c013…` |

`sprint-22b-w2-envelope.json` is assembled, never measured: `scripts/envelope_22b.py` reads the
four measurement records, counts the coverage matrix against the pre-registered shape list,
derives each exit reading from one named field of one named record, and carries every
limitation its sources sealed rather than paraphrasing them. Its `--check` rebuilds the whole
document from those sources and refuses any difference, and a test feeds it a tampered copy to
prove the refusal is real. Sealed content hash
`73313c4ddf148ae38fc025a1c4332a730922ef09b1c6ce13cba476af9c1e5ec7`.

The driver re-binding for W2 is `sprint-22b-driver-rebind.json`, from `c295892ec5bd6d62…` to
`a1d03d081bc1accd…`: the W2 drivers are new measurement code, and the executed proof shows
3 200 drawn rows identical across both implementations, `recipes_hash` unchanged at
`c99ef5e5…`, and the seven shapes unchanged. **The recipes hash has not moved since W0.**

## W2 validation

`ruff check` and `ruff format --check` with `ruff.cognitive-os.toml` over `src tests scripts
infra`: clean. `mypy src/cognitive_os`: no issues in 637 source files. `bandit -r
src/cognitive_os`: no new findings. `python -m cognitive_os.schemas.export --check` and
`check_repository_language.sh`: passed. `pre_registration_22b.py --check`,
`host_record_22b.py --check` and `envelope_22b.py --check`: **each run twice, identical output
both times** (22A W4-F3). `pre_registration_22b.py --check-chronology` accepts the W2 envelope
and the re-binding: both carry the publication's SHA-256 and both postdate it. Full suite
against the million-row store: **4 340 passed, 206 skipped** — 25 more tests than W1, none of
them a released assertion that had to change.

## What W3 inherits

A measured envelope for all seven shapes on both million-row corpora, with the cold numbers
recorded beside the warm ones — which is what makes W4's post-restore re-measurement a
regression test rather than a fresh measurement. **Four of five exit criteria decided and met.**
Two corpora untouched by this wave: W2 only read them, so W3 begins on exactly the store W1
sealed and W2 measured. And three open questions it does not have to answer but should carry:
the filtered shape's plan choice, the 4.2-second cold ANN, and a recall margin of 1.4 points.

---

## W1 outcome — two million-item corpora, and the first exit criterion decided

### The storage report, and what the 10^5 envelope predicted

| | clustered 10^6 | uniform 10^6 | clustered 10^5 | uniform 10^5 |
|---|---:|---:|---:|---:|
| bulk load | 574.5 s (1740.8/s) | 558.4 s (1790.8/s) | 57.8 s | 56.5 s |
| index build | **2081.4 s** | **3656.2 s** | 209.7 s | 437.9 s |
| index size | 3.81 GiB | 3.81 GiB | 0.38 GiB | 0.38 GiB |
| database | 7.86 GiB | 15.63 GiB (both) | — | — |

**The build scaled linearly, and §1.2's arithmetic was pessimistic.** Ten times the rows cost
9.93× the clustered build and 8.35× the uniform one; index size is exactly 10×. The backlog
warned that "naive scaling puts a 10^6 build at over an hour" and budgeted the waves around it
— clustered came in at 35 minutes, uniform at 61. Uniform stays roughly twice as expensive as
clustered at both scales, which is the same adversarial geometry that collapses its recall
showing up in construction cost.

Disk: 22 GB used of 916, 848 GB free. Nothing here reads an exit criterion (§2.2c).

### The governed-ingest exit — met, and flat

**139.35 items/s sustained over 50 000 items**, against a floor of 100. Slowest decile
**135.88/s**, fastest 140.54/s.

| decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| items/s | 135.9 | 139.3 | 140.3 | 139.6 | 139.9 | 140.3 | 140.5 | 139.6 | 140.2 | 138.1 |

§3.2 named this the wave's blind number: "Governed ingest has never been measured… If the first
decile comes in far under, the honest moves are already ordered." They were not needed. The
rate is not merely above the floor, it is **flat** — the first decile is the slowest and the
tenth is within 2% of it, so the path does not fade as the store grows past fifty thousand
governed records. This is the real path: a memory record, its provenance, its event and its
revision, per item — not the bulk load, which reads no exit.

**One of the five exit criteria is decided. It is met.**

### Incremental insert — the number that should worry 22C

Inserting into the corpus **after** its index exists costs **26.1 rows/s**, against 1740.8/s
for the same rows loaded before the index was built. That is a **67× penalty** for keeping a
million-item HNSW index current on the declared host, where the 3.81 GiB index cannot sit in
128 MB of shared buffers and every insert pays random I/O into it.

Set beside the governed-ingest number, it is the more interesting result: **governed ingest
produces items 5.3× faster than the ANN index absorbs them** (139.4/s against 26.1/s). Nothing
in 22B's exits reads this, and it is not a miss — but a deployment that ingests continuously
and expects its ANN index to stay current cannot have both on this host. 22C's acquisition
campaign is where that becomes a budget line rather than an observation.

---

## W1 findings — six defects and two decisions, before the first envelope

W1's first act was the vertical slice §3.1 demands, and it earned its place immediately: the
slice **did not finish twice in ten minutes** at 10^4, which is how the wave learned that two
of its drivers were unusable at scale. Neither would have been visible by reading them.

### W1-F1 — the batched corpus loader was quadratic

`corpus_rows(dataset, count, offset=…)` re-seeded and re-drew every prior row on each call, and
`create_corpus` called it once per batch. Measured at **0.33 ms per drawn row**, a 10^6 load in
batches of 1000 would have drawn 5.0×10⁸ rows — **about 46 hours per dataset**, against roughly
six minutes streamed.

The fix makes `corpus_stream` the single definition of the draw order and has `corpus_rows`
address into it, so a batch loader and a test cannot disagree about what row `i` is. **The rows
are unchanged**: a single `random.Random` consumed sequentially yields exactly the sequence the
discard loop reproduced, proved by executing both implementations (below).

### W1-F2 — revision 1 pinned the implementation, not the experiment

The pre-registration pinned `scale_22b.py`'s **bytes**, which made every driver defect fix a
contract violation — and W1's first act was a fix the sprint could not proceed without. What
must not move is the corpus and the readings, not the code that produces them.

The pin is **not loosened and the pre-registration is not edited**. A driver change is admitted
only through `sprint-22b-driver-rebind.json`, which re-derives the pinned implementation from
git history and *executes both* to prove they draw the same rows. A change that alters a drawn
row, the recipes hash or the seven shapes cannot be re-bound at all — it is a finding and the
sprint stops on it. The proof is re-executed on every `--check`, so a re-binding cannot outlive
the identity it asserts.

### W1-F3 — one corpus table meant the second dataset destroyed the first

`create_corpus` dropped and recreated a single shared table, so building the uniform 10^6 would
have deleted the clustered one. W2 measures 500 probes per mode **per dataset**; both must
exist at once, and rebuilding the other between waves would cost a second multi-hour build and
make the two envelopes measurements of different machine states. Each dataset now gets its own
table, named from the same frozen prefix so the recipes hash does not move.

### W1-F4 — the concurrency driver deadlocked against its own readers

`reindex_with_readers` is the driver that proves concurrent reads survive a reindex. It hung
forever. A SQLAlchemy connection begins a transaction on its first statement and holds it until
the block exits, so three readers looping inside `engine.connect()` held an `AccessShareLock`
for their whole lifetime; `REINDEX INDEX CONCURRENTLY` waits for exactly those transactions,
and they ended only after the reindex returned. Observed directly in `pg_stat_activity`: the
reindex backend in `Lock/virtualxid`, all three readers `active`.

**It passed at W0's 200 rows** because the reindex finished before the readers opened their
first transaction — a race the driver won once and would have lost for hours at 10^6. Readers
now run in `AUTOCOMMIT`, which is also the more honest measurement: a real concurrent reader is
a stream of short queries, not one transaction held open across a maintenance operation. After
the fix, 2.09 s and 8073 reader queries at p95 0.945 ms.

### W1-F5 — the declared reference host could not build a 10^6 index

With the loaders fixed, the 10^6 clustered corpus **loaded successfully — 1,000,000 rows** —
and the HNSW build then died:

```
asyncpg.exceptions.DiskFullError: could not resize shared memory segment
"/PostgreSQL.524334300" to 63999488 bytes: No space left on device
```

on a host with **860 GB of free disk**. The message names a disk that is not the problem.
PostgreSQL allocates parallel workers' dynamic shared memory in the container's `/dev/shm`,
which was Docker's default **64 MB**. No corpus below roughly 10^5 rows reaches that ceiling,
which is why every sprint until this one ran under a limit nobody had measured — including the
sealed 10^5 envelope.

This is the sharpest kind of finding a scale sprint can produce: **the declared host, as W0
sealed it, cannot take the sprint's central measurement.**

### W1-F6 — the incremental-insert driver mutated the corpus the recall exit reads

The incremental measurement appends rows, and it was run against **`clustered`** — the one
dataset an exit criterion reads. It left the recall corpus at 1 010 000 rows, and a recall
number measured over that is a number about a corpus nobody pre-registered.

Deleting the appended rows would not have been enough: the HNSW graph would still carry their
traces, so the index W2 measures would not be the index whose build was sealed. The repair is
therefore delete, `VACUUM ANALYZE`, and a full `REINDEX`, and its cost is recorded rather than
absorbed. The driver's `rows_before`/`rows_after` fields exist so this is visible in the record
instead of inferable from a row count nobody printed.

The lesson generalises past this sprint: **a driver that mutates a corpus must not be pointed
at the corpus an exit reads**, and the ones that do should say so in their own name.

### W1-D1 — the §2.2e artifact leg was unreachable in 22B's own store

§2.2e requires the restored store to resolve `learned.containment.correction_ranking`'s
artifact and load its bytes. That artifact is registered in `cognitive_os_s21d7_measured` and
nowhere else, so against 22B's fresh store the leg passed vacuously — W0's slice already
reported `resolved: false` and flagged it.

**Decision, taken with the gate owner:** register the *same bytes* in 22B's store through the
released `ArtifactService.put_file`, the content-addressed path — the store computes the hash
itself, so this is a genuine registration and not a hand-written ledger row, and re-registering
identical bytes in a second store is what content addressing is for. D7's learned **lineage** —
component revisions, activation history, evidence records — is deliberately **not** copied:
§2.3 puts learners out of scope and a lineage cannot move without a real activation run or
fabricated provenance. The checklist therefore verifies that a restore reproduces the
artifact's pointer and its loadable bytes, which is what D7 W3-F1 asked for, and says plainly
that it does not verify the learned component's governance chain.

### W1-D2 — the host was superseded, not edited

**Decision, taken with the gate owner:** raise the container's `/dev/shm` to 2 GB in
`infra/compose/postgres.yml` and re-seal the reference host under a **new host id**, exactly as
`host_record_22b.py` already prescribed — "re-seal under a new host id and say so, never edit
this record".

`sprint-22b-reference-host.json` stays byte-identical as host 1.
`sprint-22b-reference-host-2.json` is the successor, and `sprint-22b-host-change.json` seals
the delta. The only invariant group that differs is `container`; **CPU, memory, storage and
every sealed PostgreSQL setting are unchanged**, and the pre-registration's host check refuses
a successor whose PostgreSQL settings moved — a host change is not a licence to tune.

The record states what the delta can and cannot affect. It **cannot** affect recall: recall@10
is a property of the index and the probes, and no quantity of shared memory changes which
neighbours the graph finds. It **can** affect latency, because it lifts a 64 MB ceiling that
parallel query workers shared — which is precisely why this is a host change and not a
footnote. The sealed 10^5 envelope was measured on host 1; every 10^6 number is measured on
host 2, and the comparison between them carries this record.

### The restore round trip, at a million rows

All four §2.2e items are met against the restored store, and the artifact leg is no longer
vacuous:

| Check | Source | Restored | Verdict |
|---|---:|---:|---|
| row counts (events / items / revisions / artifacts) | 50 040 / 50 040 / 50 040 / 1 | identical | met |
| active view, **queried** | 50 040 | 50 040 | met |
| learned artifact pointer resolved | — | `sha256/af/afbdb7c0…` | met |
| artifact bytes **loaded from the restored archive** | — | 4354 bytes, hash matches | met |

The bytes are loaded out of the restored `*-artifacts.tar.zst`, not out of the live artifact
root — a restore that quietly reads the source's bytes has verified nothing (D7 W3-F1).

**Restore is dominated by index construction, and W3 must budget for it.** `pg_restore`
rebuilds both HNSW indexes, so the round trip cost roughly two hours of machine time against a
4.4 GB dump: the backup itself was minutes, and the restore was the clustered build plus the
uniform build over again. §3.2's instruction to budget the waves by machine-hours is right, and
this is the number it applies to.

### The whole suite against the million-row store

**4315 passed, 206 skipped, 0 failed** with both 10^6 corpora and 50 040 governed records in
place — 22A W2-F3's rule discharged.

The first run had **three failures, and all three were 22B's own W0 tests**, not released
assertions: two encoded a host record that W1 legitimately superseded, and one asserted the
driver hash literally rather than through the re-binding chain that W1-F2 introduced. No
released assertion failed at a million rows. That is the honest reading of W2-F3 here — 22A's
lesson was that released code can assume the world cannot grow, and this time it did not.

The three tests were repaired rather than deleted, and are stronger for it: the host tests now
verify **both** declared hosts and assert that they differ only where the change record says,
and the driver test now fails a change that arrives *without* a re-binding, which the literal
comparison could not distinguish from a change that arrives with one.

---

## W1 evidence index

| Record | SHA-256 |
|---|---|
| `sprint-22b-w1-slice-1e4.json` | `1b3cd99ddc46c210…` |
| `sprint-22b-w1-corpus-clustered.json` | `91208b10960bd70f…` |
| `sprint-22b-w1-corpus-uniform.json` | `b46d94238eb42476…` |
| `sprint-22b-w1-corpus-repair.json` | `879ead9af4671bc8…` |
| `sprint-22b-w1-governed-ingest.json` | `8db868ffd1964253…` |
| `sprint-22b-w1-incremental.json` | `a48c08f8a9b85585…` |
| `sprint-22b-w1-learned-artifact.json` | `f842044ba5a57f33…` |
| `sprint-22b-w1-restore-checklist.json` | `cb5ecaba5f7454aa…` |
| `sprint-22b-reference-host-2.json` | `dd958540290a4a1e…` |
| `sprint-22b-host-change.json` | `f17e7bda4ebf02d7…` |
| `sprint-22b-driver-rebind.json` | `14ce26fb6bf1250f…` |

## W1 validation

`ruff check` and `ruff format --check` over `src tests scripts infra`: clean.
`mypy src/cognitive_os`: no issues in 637 files. `export_contract_schemas.sh --check` and
`check_repository_language.sh`: passed. `pre_registration_22b.py --check` and
`host_record_22b.py --check`: **each run twice, identical output both times** (22A W4-F3), with
the driver pin satisfied *through a re-binding whose proof is re-executed on every run* and the
host bound *through a sealed change record*. Full suite against the million-row store: **4315
passed, 206 skipped**.

## What W2 inherits

Two 10^6 corpora on one host, each exactly a million rows with a cleanly built 3.81 GiB index,
in separate tables so neither wave destroys the other. A declared host — **host 2** — that can
actually build them, with the change from host 1 sealed and every 22B number binding the
successor. Drivers that have each run at scale rather than at fixture size. And one of the five
exit criteria already decided in the affirmative, with the two hardest still ahead: recall@10
on the clustered million, and the graph-assisted 500 ms that §3.2 calls the sprint's hardest
number and schedules first.

---

## W0 outcome — the authority, the host, the drivers, and six readings frozen

Four scripts, five sealed records, two test modules with **32 tests**, **eight findings** and
one decision that the plan did not anticipate needing.

Unlike 22A's W0, this wave had a threshold in front of it — five of them — and asked the gate
owner for nothing at all. What it had instead was a harder problem than any amendment: a
measurement sprint's five exit numbers are each a single scalar, and a single scalar is the
easiest thing in the world to meet by quietly changing what it reads. §2.2 named five readings
that could bend. Building the drivers turned up a sixth, and W0 froze that one under the same
rule rather than leaving it for whichever wave first needed it.

### S22B-000 and S22B-001 — the starting point, read from the authority that owns it

[`sprint-22b-baseline.json`](evidence/sprint-22b-baseline.json), integrity
`12b8166a51387a6a…`, file `ba5cc63236e8e2bf…`.

| Fact | Result |
|---|---|
| `sprint-22a-domain-baseline` resolves remotely as an annotated tag | yes, object `58b1a0fa3b4f83de…` peeling to `291482448114ffed…` |
| local and remote tag handles agree | yes |
| branch descends from current `origin/main` | yes, two commits ahead — the backlog rides with the wave that executes it |
| both 22B outcome tags | **absent**, checked rather than assumed |
| 22A exact-head CI run `31573794611` | re-read from the API, **30 of 30 successful** |
| branch protection | administrators enforced, 27 required checks, strict, no force pushes, no deletions |
| migration head | `0015`, counted from `infra/postgres/alembic/versions` |
| **twelve** predecessor artifact roots | fingerprinted through the released `reality_integrity.fingerprint`; the eleven with a released expectation match it, drift **zero** |
| 22A's own root | a **first observation** — see W0-A1 |
| stores written to before this record | **none** |

The record also binds, **by hash rather than by retyped number**, the three pieces of prior art
the exits are compared against: both sealed 10^5 envelopes and `sprint-21d1-w5a-retrieval.json`.
That matters most for the graph exit. 500 ms is 3.6× tighter than the only graph-arm latency
ever measured, and that measurement — 1788.9 ms — was itself reached with **60 queries cut off
at D1's 2 s budget**. A baseline that restated "1789 ms" as a constant would have let the
comparison drift; binding the file keeps the cutoff count attached to the number, which is why
§2.2d's frozen recipe now reports cutoffs beside every p95.

**S22B-001**: `cognitive_os_s22b_test`, `cognitive_os_s22b_restore_test` and
`cognitive_os_s22b_integration_test` were created through `postgres_provision_evidence.sh`
under the `cognitive_os_s22b` prefix — no new provisioning script, because the released one
already refuses anything outside the configured prefix. Migrated to head `0015`, fifteen
migrations, and the app role has **no DELETE** on `cognitive_os.events`, inherited from the
released grants rather than applied by hand. Roots `artifacts-s22b` and `backups-s22b` created
empty. The baseline was taken *before* any of this, so its `before` is genuinely before.

### S22B-002 — the reference host, declared once

[`sprint-22b-reference-host.json`](evidence/sprint-22b-reference-host.json), invariants hash
`811cbbb88af57677…`.

AMD Ryzen 7 5700X, 8 cores / 16 threads, 46 GiB RAM, PostgreSQL **18.4** with pgvector
**0.8.2**, data on `/dev/nvme1n1p1` (ext4, non-rotational, WD SN550-class NVMe), GPU-free by
declaration rather than by omission.

The record splits deliberately into **invariants**, which `--check` recomputes and fails on,
and **observations** — free disk, load, container id — which are recorded and compared by
nothing, because a same-host check that failed when a byte was written would prove nothing
(W2-F1/F2). The container *image digest* is an invariant while the container *id* is an
observation, because §2.2b requires real database restarts and a restart changes the id.

**The sharpest decision in the file is that the PostgreSQL memory settings are invariants.**
They are near the packaged defaults — `shared_buffers` 128 MB, `maintenance_work_mem` 64 MB,
`work_mem` 4 MB — against 46 GiB of RAM, and they will cost real wall-clock on a 10^6 HNSW
build. They stay exactly as they are. The 10^5 envelope this sprint extends was measured under
these settings, so raising `maintenance_work_mem` would buy a faster build at the price of the
only comparison the sprint has. A build that is slow here is a measured property of the
declared host and gets reported as one; §2.3's last bullet becomes a fence rather than a
sentence.

### S22B-003 — the drivers, executed rather than described

[`scripts/scale_22b.py`](../../../scripts/scale_22b.py), and its fixture-scale run in
[`sprint-22b-w0-slice.json`](evidence/sprint-22b-w0-slice.json).

Everything §1.3 lists is there, in one module, because seven scripts sharing a corpus, a probe
protocol and a host record are one script wearing seven hats. What is **reused** rather than
rebuilt is the load-bearing part:

| Driver | Composed from |
|---|---|
| both dataset recipes | `memory_ann_baseline.py`'s own `_vector_literal` / `_clustered_literal`, imported |
| bulk load, HNSW build, exact/ANN envelope | the same released harness's shapes |
| hybrid fusion | the released Context Plane's `ranking_profile` → `context-rrf-v1`, `rrf_k` 60 |
| bounded graph configuration | a released `GraphResourceLimits` instance; 22B adds no knob |
| governed ingest | `MemoryService.create` — record, provenance, event, revision |
| restore round trip | `restore_event_store.sh` and `artifact_restore_verify.py` |

Importing the released generators is not tidiness. **A 10^6 recall number is comparable to the
sealed 10^5 one only if the same function drew both corpora**, so re-implementing the geometry
would have quietly destroyed the sprint's only baseline.

The slice ran every driver end to end at 200 corpus rows and 40 governed items: bulk load,
index build, three vector shapes warm and cold, recall@10 against an exact-scan ground truth,
governed ingest per decile, embedding, three governed query shapes, hybrid, temporal, bloat
before and after a delete, `REINDEX CONCURRENTLY` with three measured concurrent readers, and
the §2.2e restore checklist. The record states in its own body that it **decides no exit
criterion** — every 22B exit is a claim at 10^6 items, so publishing the pre-registration after
this run is not publishing it after the numbers.

Two slice results are worth naming because they are the drivers refusing to flatter themselves.
`index_scan_confirmed: false` at 200 rows is **correct**: the planner declines HNSW on a tiny
corpus and the driver reports a limitation rather than a clean-looking recall of 1.0. And the
restore checklist reports `learned_artifact_pointer_resolved: false` against a store that never
held that artifact — the checklist can fail, which is the only reason its passing will mean
anything in W3.

### S22B-004 — the tests

| Module | Tests | What it holds |
|---|---:|---|
| `tests/cognitive_os/scale/test_scale_22b_drivers.py` | 13 | corpus and probe determinism, batch-boundary stability, the frozen selectivity, the seven-shape enumeration, §2.2d's parameters |
| `tests/cognitive_os/scale/test_sprint_22b_w0_evidence.py` | 19 | the five seals, the live release verification, the prior-art hash binding, `measured_values: 0`, and both validators' ability to fail |

Two properties in that table are fences rather than tests. The **batch-boundary test** asserts
that row `i` is the same row whether it arrived in one batch or three — without it, a million-row
corpus would depend on the loader's chunk size and the recipe would not be a recipe. And the
**host-drift probe** hands the check a host with one more logical CPU and requires it to refuse,
so "the host did not change" is a claim that can notice a change (22A W4-F2). It drives the
comparison directly rather than through a subprocess, so it runs in CI, which has no 22B store
to measure against.

### S22B-010 through S22B-016 — revision 1, frozen before a corpus row exists

[`sprint-22b-contracts.json`](evidence/sprint-22b-contracts.json) and
[`sprint-22b-pre-registration.json`](evidence/sprint-22b-pre-registration.json).

Eight sealed contracts: the five exit numbers verbatim, both dataset recipes, the probe
protocol, the throughput reading, the bounded graph configuration, the filter selectivity, the
restore checklist, and the reference host. `measured_values: 0`, a chronology of eight zeros,
`thresholds_changed: 0` and `amendments_made_by_22b: 0` — structurally zero, because 22B's plan
contains no gate-owner amendment path at all.

The recipes are **imported from the driver module and hashed from it**, never retyped, so
`--check` recomputes `recipes_hash` and fails if a dataset, a probe count, a selectivity or the
graph configuration drifts after publication. It also pins `scale_22b.py`'s bytes and the
reference host's invariants hash. Both `--check` validators were run twice and printed
identical output on the second run (22A W4-F3).

---

## W0 findings

Eight findings and one decision. Six are defects in this wave's own groundwork; three of those
six were found only by *running* the drivers rather than reading them, and two more by running
them **twice**.

### W0-F1 — the host record sealed `pgvector: null`

`host_record_22b.py` read its facts from `COGOS_DATABASE_BOOTSTRAP_URL`, which points at the
`postgres` database, where the `vector` extension is not installed. The first sealed record
therefore carried `null` for the version of the extension **every ANN number in the sprint
depends on**. Fixed by reading 22B's own store through `COGOS_DATABASE_ADMIN_URL`; the record
now seals pgvector `0.8.2` and a test asserts the field is populated.

### W0-F2 — `include_historical` is a released field that no released code reads

The temporal shape — "the active view as of a moment" — cannot be expressed as a released
`MemoryQuery`. `MemoryMetadataFilter` has no as-of predicate, and its `include_historical`
field appears exactly once in `src/`: at its own definition. `current_memory_statement` joins
strictly on `revision = current_revision` and never consults it.

This is the finding §3.1 predicted, arriving in W0 rather than after a million rows made every
retry expensive. It is **surfaced, not absorbed**: widening the released filter would change
released behaviour, which W0 is forbidden to do, so the temporal recipe is raw SQL over the
released `memory_revisions.created_at` — no migration, no released change — and **every temporal
record carries the sealed limitation that it bypasses the governed retrieval path and records
no access audit**. The stale-item shape is unaffected: `statuses=(superseded, retracted,
expired)` is read by the released statement and works.

### W0-F3 — hybrid is two queries by construction, not by choice

`MemoryQuery.exactly_one_mode_payload` refuses a query carrying both a text and a vector
payload. The hybrid shape is therefore two released executions fused afterwards, and the fusion
is the released Context Plane's `context-rrf-v1` profile rather than a second reciprocal-rank
implementation. Named here so no later wave reads "hybrid" as a single released capability.

### W0-F4 — a deterministic query id made the audit trail collide on the second run

The governed query drivers derived their `query_id` from the shape name alone.
`MemoryRetrievalService` derives each access record's primary key from the query id, memory id,
revision and rank, so the **second** run of any shape hit a duplicate key and the service
failed closed on its own audit. At 500 probes per shape it would have collided within a single
run. Fixed with a per-invocation token; the probe *vectors* stay deterministic, because an
audit record is a fact about one execution while a probe is a fact about the recipe. Found by
running the driver twice — 22A W4-F3, applied to a driver rather than a sealer.

### W0-F5 — the bloat driver could not notice bloat

`table_bloat` read `pg_stat_user_tables`, whose counters the statistics collector updates
asynchronously. Deleting a fifth of the corpus and measuring immediately reported **zero dead
tuples and unchanged live tuples** — a bloat measurement incapable of measuring bloat, which is
22A W4-F2 in its purest form. Replaced with `pgstattuple`, an exact synchronous heap scan: the
same delete now reports 200 → 160 live and 40 dead at 13.1%. It costs a full scan, which W3
must budget for at 10^6 rows, and that is the honest price of an answer that is a fact about
the table rather than about how long the collector had been given.

### W0-F6 — the hybrid vector leg returned nothing, and the obvious fix was forbidden

Governed ingest writes a record, its provenance, its event and its revision — and no embedding,
so the hybrid recipe's vector leg matched zero rows. The obvious fix, embedding inside the
ingest loop, would have **changed what the frozen §2.2c ingest reading measures** after the
reading was frozen. Embedding is now its own measured step, reported beside the ingest rate and
read by no exit criterion; the pre-registration states that embedding writes are not inside the
ingest loop, and a test asserts it.

### W0-F7 — the restore verifier read a column that has never existed

The §2.2e artifact check selected `storage_key` from `cognitive_os.artifacts`, which has no
such column — the storage key lives on `artifact_blobs`. The artifact leg of the checklist
could only ever have raised. Fixed by using the same join `backup_event_store.sh` and
`restore_event_store.sh` already use, rather than a third spelling of it.

### W0-F8 — "seven retrieval shapes" was eight, and the missing one was the hardest

The shape enumeration listed eight entries: it counted `metadata` and `text` as envelope rows
and **left out `bounded_graph_assisted` entirely** — the shape the sprint's hardest exit reads.
The pre-registration's own enumeration check caught it, which is exactly 22A W4-F1 arriving one
sprint later in a new costume. The seven are now the seven W2's row names; `metadata` and
`text` are enumerated separately as supporting modes with the shapes that use them, so nothing
is hidden rather than merely uncounted. A test asserts the seven against a list written from
the plan, not derived from the module.

### W0-D1 — a sixth reading, frozen under the same rule as the five

§2.2 froze the five readings that could bend. Building the filtered-ANN driver showed the
300 ms exit rests on a sixth: **a metadata predicate has a selectivity**, and the latency is a
function of how much the filter removes. Left unfrozen, a later wave could meet the exit by
filtering to a friendlier slice and call it a configuration.

W0 freezes it: ten scopes in the corpus, one selected, statuses `(candidate, verified)`, type
`episode`, applied as a pre-filter in the same statement as the ANN order-by — a tenth of the
corpus, fixed before any probe runs. This moves no threshold and asks for no amendment; it
decides a parameter §2.3's last bullet already forbids tuning, at the only moment when deciding
it is honest.

### W0-A1 — 22A's artifact root is a first observation

`sprint-22a-baseline.json` lists the eleven roots 22A must not write to, and 22A's own root was
not among them; no post-release fingerprint of `artifacts-s22a` was ever sealed. This is the
same class of stale expectation 22A named as its own W0-F1, one sprint on. 22B freezes the
current state as a first observation and **does not edit 22A's sealed record** — an authorised
change re-binds a record, it does not edit one. The other eleven roots match their released
expectations exactly; unexplained drift is zero.

---

## W0 evidence index

| Record | SHA-256 |
|---|---|
| `sprint-22b-baseline.json` | `ba5cc63236e8e2bfc2f53b1f83dff08c4a8f1f306f6e150ba7da64f371cd32c4` |
| `sprint-22b-reference-host.json` | `0f05d2ce6ebf3aaa84e2c57ce6cee5751b4bbd67d4f7c552b319c06611e13fac` |
| `sprint-22b-w0-slice.json` | `b26ba5b6ede595f01934945658f07778677d9ddfc873d3b25266c642f3dc2c9e` |
| `sprint-22b-contracts.json` | `ece220ad0f0dbba497797c2089d08a2e5a9ae75d0ec0b2f088bfea94d904fcaa` |
| `sprint-22b-pre-registration.json` | `1e0022094ac62dc29e1372fdd93ca060cf558773cddfb9e391373148d9d0dd73` |

Scripts: `baseline_22b.py` `f539f7e2b45a4a72…`, `host_record_22b.py` `0346c39ecdbfc1e6…`,
`scale_22b.py` `c295892ec5bd6d62…`, `pre_registration_22b.py` `418be8f44cda13a4…`.

## W0 validation

`ruff check` and `ruff format --check` with `ruff.cognitive-os.toml` over `src tests scripts
infra`: clean, 1210 files. `mypy src/cognitive_os`: no issues in 637 source files. `bandit -r
src/cognitive_os`: no new findings. `export_contract_schemas.sh --check`: passed.
`check_repository_language.sh`: passed. `detect-secrets-hook` over every tracked file with the
regenerated `.secrets.baseline`: clean — the 22B evidence adds 66 hex-entropy entries, as
hash-dense evidence always does. `pre_registration_22b.py --check` and `host_record_22b.py
--check`: **each run twice, identical output both times**. Full suite: **4297 passed, 217
skipped**.

No released module changed, so the benchmark-manifest and learned-replay CI lanes have nothing
to regress: `git status` at the wave's close showed only new scripts, new tests and new
evidence.

## What W1 inherits

Two reproducible dataset recipes bound to the generators that drew the sealed 10^5 envelope; a
store pair at head `0015` with a declared, sealed, re-checkable host; a driver for every shape
W2 must measure, each already run once end to end; and eight readings frozen so that no number
W1 produces can be met by changing what it reads. **The vertical slice at 10^4 comes before the
million rows**, and its likeliest finding is now known to be somewhere other than the query
recipes — W0 spent that finding already.
