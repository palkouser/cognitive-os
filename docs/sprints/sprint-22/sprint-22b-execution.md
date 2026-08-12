# Sprint 22B execution log

- Branch: `sprint-22b-groundwork`
- Backlog: [Sprint 22B Technical Backlog](sprint-22b-technical-backlog.md)
- **W0 closed.** S22B-000 through S22B-004 and S22B-010 through S22B-016 are done. The
  authority is read from the sources that own it, 22B's store pair exists at head `0015`, the
  reference host is sealed, every §1.3 driver is built and has been run end to end at fixture
  scale, and revision 1 is published with `measured_values: 0`. **No threshold moved, no
  migration was allocated, and no released module changed** — the whole wave is new scripts,
  new tests and new evidence.
- Wave commit `613b546`, pull request **#233** against protected `main`; CI run
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
