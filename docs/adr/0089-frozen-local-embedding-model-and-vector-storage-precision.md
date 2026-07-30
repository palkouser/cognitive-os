# ADR 0089: The frozen local embedding model, and float32 as the vector storage precision

- Status: Accepted
- Date: 2026-07-30
- Sprint: 21C3
- Stage gate: Gate C3 — Reality-Grade Learning Inputs
- Decision owners: project owner
- Relates to: [ADR 0035](0035-governed-memory-plane-authority.md) (governed Memory Plane
  authority), [ADR 0082](0082-approximate-vector-retrieval-and-capacity-envelope.md)
  (approximate vector retrieval and capacity envelope), [ADR 0009](0009-apache-20-license.md)
  (Apache-2.0 licence), [ADR 0088](0088-open-development-data-policy.md) (open-development
  data policy)
- Amends: nothing. ADR 0082's capacity envelope and its conclusion that C3-scale retrieval
  needs no approximate index are unchanged and are what this decision rests on.

## Context

Until this sprint the Memory Plane's only working embedding provider was
`DeterministicEmbeddingProvider` — a hashing vector, 64 dimensions, no semantic content
whatever. It exists so that the plane's write, index and audit paths can be exercised without
a model, and it does that job. It is not retrieval. A record found by it is a record whose
tokens hashed into the same buckets.

Two questions had to be answered before C3 could claim a working learned-evidence input path,
and they are answered together here because the second is meaningless without the first.

1. **Which model, exactly.** §4.14 selects `all-MiniLM-L6-v2`. A model identified by name is
   not identified: `main` moves, `latest` moves, and a retrieval measurement taken against a
   moving pointer cannot be reproduced or defended. It also has to be obtained without the
   runtime ever reaching the network.
2. **Which storage precision.** pgvector 0.8 offers `halfvec`, which halves the bytes per
   component. §4.16 sets the conditions under which taking it is worth a schema migration.

## Decision

### The model is pinned to a commit, fetched by an operator, and never downloaded at runtime

`sentence-transformers/all-MiniLM-L6-v2` at revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions, L2-normalized output, 256-token
sequence limit, Apache-2.0 as declared by the model card at that revision. Eleven files are
enumerated in `cognitive_os.infrastructure.embeddings.minilm`; the whole-tree digest is
`98eb3ae4df320d0b721902aabef795cafb36c3a516f036e92e2b046f55ef4229`.

`scripts/embedding_model.py prefetch --destination <absolute path> --allow-network` is the
only code path in this repository that downloads a model, and it refuses a revision other than
the frozen one, refuses a relative destination, and refuses to finish if the model card at
that revision stops declaring Apache-2.0. It writes `cognitive-os-model.json` beside the
weights. The model is never committed; the ~88 MB tree lives outside the working tree
entirely.

`health` re-hashes every file against that manifest and reports one of `missing`,
`dependency_missing`, `digest_mismatch`, `dimension_mismatch` or `healthy`. It measures the
dimension by encoding a probe string rather than reading it out of `config.json`, because the
config is the model's claim and this check exists for the case where the claim is wrong.

**`all-mpnet-base-v2` was rejected**, and not narrowly. It is the stronger model on general
sentence benchmarks. It is also 768-dimensional and roughly five times the CPU cost per
record, for a corpus ADR 0082 already sized at a few hundred short technical records — where
§4.16's measurements below show the *entire* retrieval question resolving in well under a
millisecond either way. Paying five times the latency for accuracy this corpus is too small to
demonstrate is not a trade.

### There is no fallback to the deterministic provider

`build_embedding_provider` raises `EmbeddingUnavailableError` when the configured local model
is missing, mismatched or unloadable. It never returns the hashing provider instead.

This is the part worth stating as a decision rather than leaving as an implementation detail.
A fallback here would not degrade retrieval, it would replace it, and the evidence file would
carry `sentence-transformers-local` over numbers a hash produced. The measurements below are
exactly how large that lie would be: recall@5 0.917 against 0.458.

### Storage stays float32. Migration `0016` is not created

Measured on the isolated C3 PostgreSQL (pgvector 0.8.2), same 60 vectors, same 60 queries,
temporary tables, HNSW index on both:

| | `vector(384)` | `halfvec(384)` |
| --- | --- | --- |
| total bytes incl. index | 278 528 | 188 416 |
| table bytes | 98 304 | 57 344 |
| recall@5 / recall@10 | 0.9167 / 0.9667 | 0.9167 / 0.9667 |
| MRR@10 / nDCG@10 | 0.7105 / 0.7704 | 0.7105 / 0.7704 |
| p50 / p95 | 0.300 ms / 0.558 ms | 0.306 ms / 0.460 ms |
| top-10 agreement vs float32 exact | — | 1.000 |

Half precision loses nothing measurable: identical rankings on all sixty queries, and slightly
*better* p95. It fails §4.16's first condition anyway. Total storage falls 32.4%, short of the
35% required. The table alone falls 41.7%; the HNSW index does not shrink with the column, so
the saving is diluted exactly where §4.16 asks the question — total bytes including indexes.

So the answer is float32, and it is the answer §4.16 anticipated for a different reason:
migration `0016` is not created. The rehearsed conversion — drop the HNSW index, `ALTER
COLUMN`, rebuild — took 6.8 ms at this scale, which is the real argument. A change this cheap
to perform later is a change with no reason to perform now, and an unused `halfvec` column
would be schema nobody reads.

**The scale trigger that reopens this.** Revisit when the embedded corpus passes **100 000
records**, or when vector storage including indexes passes **1 GiB**, whichever comes first. At
that size the fixed per-table overhead that diluted the 41.7% down to 32.4% stops dominating,
and the 35% threshold is likely to be met by the same measurement that failed it here. Rerun
`scripts/retrieval_benchmark.py` against the corpus of the day; do not carry these numbers
forward.

## Consequences

- C3 has a real embedding provider, and evidence that names it truthfully.
- The retrieval numbers in `sprint-21c3-w5-retrieval.json` are reproducible: model revision,
  tree digest and benchmark manifest hash are all in the file.
- An operator must run one command before first use. A host that skips it gets a typed
  unavailable capability, not silently worse retrieval.
- The `local-embeddings` extra (`sentence-transformers`, and through it PyTorch) is required
  for the production provider. It stays an extra: nothing in the default install path imports
  it, and `health` reports `dependency_missing` rather than raising an `ImportError` out of a
  request.
- Alembic head stays `0015` for the whole of C3.

## Verification

- `scripts/embedding_model.py health` on a tampered file reports `digest_mismatch`
  (`tests/cognitive_os/infrastructure/test_local_embedding_model.py`).
- `build_embedding_provider` raises rather than substituting the hashing provider, asserted
  for the missing-model, wrong-digest and wrong-dimension cases.
- §4.15 thresholds are checked by `scripts/retrieval_benchmark.py` itself and recorded in the
  evidence file: recall@5 0.9167 ≥ 0.80, MRR@10 0.7105 ≥ 0.65, margin over the deterministic
  provider 0.4584 ≥ 0.15, zero cross-group leakage, rankings identical across repeated runs.
- The temporary comparison tables are dropped by the same run that creates them, and the run
  records `temporary_objects_remaining: 0`.

## References

- `docs/sprints/sprint-21/evidence/sprint-21c3-w5-retrieval.json`
- `docs/sprints/sprint-21/sprint-21c3-technical-backlog.md` §4.14, §4.15, §4.16
- `docs/operations/local-embedding-model.md`
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/1110a243fdf4706b3f48f1d95db1a4f5529b4d41
