# ADR 0082: Approximate vector retrieval and the measured capacity envelope

- Status: Accepted
- Date: 2026-07-25
- Amends: [ADR 0035](0035-governed-memory-plane-authority.md) (Governed Memory Plane authority)
- Sprint: 21, phase 21.3

## Context

Requirement 4 of Sprint 21 makes runtime scalability a *selection criterion* for the learning
method rather than a target to reach afterwards. A Tier A non-parametric method stores
experience and retrieves neighbours; if retrieval cannot scale, that whole tier is
disqualified before any model is written. So the capacity of vector retrieval has to be a
measured number, and it has to be measured now.

The audit that opened Sprint 21 recorded this as blocker B4: `pg_indexes` filtered for
`hnsw`/`ivfflat` returned zero rows, and retrieval was an unindexed `embedding <=> query`.

That was not an omission. ADR 0035 states it as a decision: *"Exact vector search is the only
vector mode in Sprint 9; approximate indexes and hybrid retrieval are prohibited."* The
prohibition was enforced in five places — a sealed configuration flag in
`MemoryConfiguration`, a sealed flag in `ContextConfiguration`, an `ERROR`-severity finding in
the Memory Plane health check, a `prohibited_indexes` count in the semantic health check, and
an integration test asserting zero. Adding an index without touching those would have made the
system report itself unhealthy.

Two measured facts constrained the design before it was chosen:

1. **`memory_embeddings.embedding` is an undimensioned `vector`**, deliberately, so that one
   table can hold several embedding models (`dimension <= 4096`, unique per provider and
   model). pgvector cannot build an HNSW index on such a column at all — `CREATE INDEX …
   USING hnsw (embedding …)` fails with `column does not have dimensions`, even on an empty
   table.
2. **pgvector refuses HNSW above 2 000 dimensions.** The configuration permits embeddings up
   to 4 096, so a range of legal dimensions can never be indexed.

## Decision

**Approximation becomes available per dimension, to a caller that names it, and the exact path
stays exact by construction rather than by configuration.**

### The retrieval mode carries the distinction

`MemoryRetrievalMode.VECTOR_APPROXIMATE` is a mode, not a flag on the vector query, because
`MemoryAccessRecord.retrieval_mode` and `MemoryRetrievalTrace.retrieval_mode` are both
populated from `MemoryQuery.mode`. Whether a stored result came from an exhaustive scan or
from an index that may miss a true neighbour therefore stays answerable from the audit trail
for as long as the row exists. A boolean on the query would have been invisible there.

Nothing selects the mode on a caller's behalf. `MemoryConfiguration` and
`PostgresMemoryRepository` both default to declaring no approximate dimension at all, so an
unchanged Sprint 9 call site keeps Sprint 9 behaviour and an approximate request against it is
refused rather than quietly served exactly.

### One partial expression index per dimension

```sql
CREATE INDEX ix_memory_embeddings_hnsw_768 ON cognitive_os.memory_embeddings
USING hnsw ((embedding::vector(768)) vector_cosine_ops) WHERE dimension = 768;
```

This preserves the multi-model capability the schema was built for. It also produces the
property that makes the amendment safe: **the exact query compares the undimensioned column
directly, and no index on a cast expression can serve it.** Exactness is not a flag that could
be flipped, a default that could drift, or a review item — it is the shape of the SQL, and the
two shapes are asserted to differ in unit tests and asserted against a live query planner in
`tests/integration/postgres/test_memory_plane.py`.

Adding a dimension is a migration, never a runtime decision. Migration 0013 creates the
indexes for 64 (what the deterministic provider emits, hence the only dimension exercisable
end to end today) and 768 (what a local sentence-transformer model would emit, hence the
dimension the envelope is measured at), and widens `ck_memory_access_mode` to accept the new
mode.

### The prohibition is narrowed, not dropped

The health checks no longer require zero approximate indexes. They require **exactly the
declared set, and require it to be usable**:

- an approximate index outside `APPROXIMATE_INDEX_NAMES` is still an `ERROR`;
- a declared index that is absent is an `ERROR` too, because an approximate query would then
  silently degrade to an exhaustive scan;
- validity is checked through `pg_index.indisvalid AND indisready`, not through presence in
  `pg_indexes`. A failed HNSW build leaves an *invalid* index in the catalogue — this was
  observed, not anticipated — which a presence check reports as healthy while the planner
  ignores it entirely.

`MemoryConfiguration.allow_approximate_vector_indexes` is replaced by
`approximate_vector_index_dimensions: frozenset[int]`. A blanket boolean would have permitted
queries no index can serve, since an index exists per dimension. The validator refuses a
dimension pgvector cannot index and a dimension no configured embedding provider produces.

The other three Sprint 9 seals — provider direct write, automatic promotion, network model
download — are untouched and still sealed.

### The Context Builder's seal is untouched

`ContextConfiguration.allow_approximate_vector_search` remains sealed to `False`. The
deterministic context build stays exhaustive. This is the narrowest amendment that delivers
the capacity envelope, and the context plane can be revisited on its own evidence.

### A capacity measurement must disclose what it measured

`RetrievalCapacityEnvelope` is a sealed contract, and most of its validators exist because the
corresponding mistake was made while building the measurement:

- an approximate envelope **must** report recall against exhaustive ground truth. Latency
  alone is the one number an approximate index can always win, because it is fast precisely
  when it skips the answer;
- an exact envelope must **not** report measured recall — it is 1 by construction, and stating
  it would imply it had been measured;
- an approximate envelope must state **whether the query plan actually used the index**. A
  cost-based planner declines an approximate index on a small corpus and scans exhaustively
  instead; recall then comes out at 1 for a reason that says nothing about the index. The
  first run of the baseline script reported exactly that, and read as a clean result until
  the plan was read back;
- an unused index reporting recall below 1 is refused as incoherent: an exhaustive scan cannot
  miss a neighbour.

`hnsw.ef_search` is raised to at least the query's candidate limit and applied with `SET
LOCAL`, so a pooled connection carries no approximate setting back to the next caller. pgvector
returns at most `ef_search` rows from an HNSW scan, so an `ef_search` below the `LIMIT`
truncates silently — which presents as poor recall, sending an investigation in the wrong
direction.

## Measured result

At 10^5 vectors, 768 dimensions, 50 probes, result limit 20, candidate limit 1 000,
`ef_search = 1 000`, index scan confirmed from the plan in both approximate rows:

| Corpus distribution | Exact p50 | Approx p50 | Speed-up | Recall@20 | Index build |
|---|---|---|---|---|---|
| 64 gaussian clusters (spread 0.35) | 321.2 ms | **15.3 ms** | **21×** | **0.992** | 209.7 s |
| Independent gaussian noise | 319.4 ms | 82.0 ms | 3.9× | 0.496 | 437.9 s |

Index size was 409.6 MB in both cases.

**The distribution dominates the result, and the first run was misread because of it.** Run
against independent Gaussian noise the index loses half the true top-20, which reads as a
poor showing for HNSW. It is not: in 768 dimensions independent noise is nearly
equidistant, so there is no neighbourhood structure for a proximity graph to exploit — the
adversarial floor, not a deployment estimate. Real embeddings are strongly clustered, and
on a clustered corpus the same index returns 99.2% of the exhaustive top-20 twenty-one
times faster.

Both numbers are kept. The uniform run is the floor and the clustered run is the realistic
case; `RetrievalCapacityEnvelope.limitations` names which distribution produced each, so
neither can be quoted as the other. `scripts/memory_ann_baseline.py --clusters 0` reproduces
the floor.

**This is what Requirement 4 needed.** Retrieval at 10^5 is not a barrier to a Tier A
non-parametric method: 15 ms at 99% recall leaves room for the reranking surface. The
exhaustive path costs 321 ms at the same size, which would have been.

## Consequences

- Retrieval capacity is a measured, content-addressed record instead of an assumption, which
  is what Requirement 4 needs in order to rank Tier A against the other tiers.
- Recall is now a documented, disclosed property of one retrieval mode. This is a real
  behaviour change from Sprint 9 and is stated as such, never silent.
- Callers gain a mode they must ask for. Existing callers are unaffected: every default is the
  Sprint 9 behaviour.
- The in-memory repository double **refuses** approximate retrieval rather than serving it
  exactly. Serving it would look like perfect recall and make any measurement taken against
  the double meaningless.
- Dimensions above 2 000 remain exhaustive-only, permanently, at pgvector's limit. They are
  still searchable — just not quickly — and `MemoryQuery` refuses an approximate request for
  them rather than accepting one that no index can satisfy.
- An HNSW build over a large table exceeds the application's 30-second command timeout by a
  wide margin. Deployments must allow for that when applying migration 0013 to a populated
  table; the measured build time is recorded in the sprint report.

## Alternatives considered

- **Redefine `embedding` as `vector(768)`.** Rejected: it destroys the multi-model capability
  the schema deliberately supports, and requires rewriting existing rows.
- **A separate embeddings table per dimension.** Rejected: it duplicates the provenance
  foreign keys and the audit path to buy a slightly simpler index definition.
- **Keep the prohibition and accept exhaustive scan at scale.** Rejected, but only after
  measurement: this is the option that disqualifies Tier A, and Requirement 4 makes that a
  decision to take on evidence rather than by default.
- **Two-stage retrieval that restores exact top-k.** The repository already over-fetches
  candidates and re-scores them exactly, so the returned *scores* are exact and ranking among
  returned rows is exact. It does not restore exact *recall*: a true neighbour the index never
  returned stays missing. The envelope therefore reports recall rather than claiming
  exactness.
- **A boolean flag on `MemoryVectorQuery`.** Rejected: the access record and the trace both
  derive their mode from `MemoryQuery.mode`, so a flag would leave the audit trail unable to
  distinguish an exhaustive result from an approximate one.
