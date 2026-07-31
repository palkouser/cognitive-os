# ADR 0090: No Fused Gromov-Wasserstein, and the shortlist as the binding constraint

- Status: Accepted
- Date: 2026-08-01
- Sprint: 21D1
- Stage gate: Gate D1 — Experience Memory Graph, pre-registered learning surface
- Decision owners: project owner
- Relates to: [ADR 0089](0089-frozen-local-embedding-model-and-vector-storage-precision.md)
  (frozen local embedding model), [ADR 0009](0009-apache-20-license.md) (Apache-2.0 licence),
  [ADR 0083](0083-baseline-ladder-and-the-skill-selection-null-result.md) (baseline ladder and
  a null result reported as a result), [ADR 0088](0088-open-development-data-policy.md)
  (open-development data policy)
- Amends: nothing. It records a decision `§4.11` of the D1 backlog reserved for this point.

## Context

D1 asked whether bounded Experience Memory Graph retrieval contributes useful structure. It
does not fit anything, activate anything, or open Gate L2, and this ADR does not change that.

The measured comparison, replayed for this decision from the committed pair artifacts and the
frozen eighty-query manifest with no database access, is in
`docs/sprints/sprint-21/evidence/sprint-21d1-residuals.json`. Two arms matter:

| arm | top-5 recall | MRR@10 | p50 | p95 | budget cutoffs |
|---|---|---|---|---|---|
| `minilm_vector` — strongest arm needing no structure | 0.5375 | 0.4392 | 15.3 ms | 27.5 ms | 0 |
| `minilm_shortlist_plus_bounded_ged` | 0.6750 | 0.4481 | 24.7 ms | 1788.9 ms | 60 |

The graph arm wins fourteen queries, loses three, and leaves twenty-six unanswered. `§4.11`
sets five conditions for approving an FGW experiment in D2. Three findings decide them.

**The residual is mostly not a reranking problem.** Of the twenty-six residual queries,
nineteen are *shortlist-ceiling* misses: no relevant pair reached the ten-candidate shortlist,
so the reranker never saw one. Seven are *rerank-ordering* misses, the only class a better
structural comparator could address. A reranker can only reorder what the shortlist admits,
so the perfect ordering of the current shortlist bounds every reranker, present or future, at
0.7625 top-5 recall. That is the whole ceiling FGW would be competing for.

**The shortlist width, not the comparator, is what caps the system.** Ranking the whole
eligible pool with the vector arm puts the first relevant pair within rank thirty of a
seventy-eight candidate pool for every one of the eighty queries. The reranker ceiling by
shortlist width is 0.7625 at ten, 0.9000 at fifteen, 0.9750 at twenty and 1.0000 at thirty.
Widening the shortlist is a change to one declared bound and costs no dependency at all.

**The existing graph score is nearly degenerate, and that is also why it regresses.** Bounded
graph edit distance produces exactly two distinct scores per query and six across the entire
corpus. For the twenty fresh logic and mathematics queries every comparison that completed
returned the identical `0.525424`. Sixty-one of eighty queries had the rank of their relevant
pair decided by the pair-id tiebreak rather than by the arm. All three regressions are that
effect: the relevant pair sits in the arm's *highest* score block and still lands seventh,
because the block holds more than five candidates. For the two truth-table queries the vector
arm had ranked the relevant pair first.

The arm's advantage over the vector arm is therefore real but coarse — roughly one informative
bit per query — and its cost is already at the declared ceiling: sixty budget cutoffs across
twenty queries, three per query, on a corpus of eighty pairs.

## Decision

### No Fused Gromov-Wasserstein in D1, and no D2 experiment approved

`§4.11` permits approving a D2 experiment only when all five of its conditions hold. They do
not.

| `§4.11` condition | verdict |
|---|---|
| the simple graph arm leaves a named structural error class | **met** — `rerank_ordering`, seven queries, named with their ids, plus the score degeneracy that decides sixty-one |
| projected improvement ≥ 0.05 absolute top-5 recall or MRR over the strongest simpler arm | **met on the ceiling** — a perfect rerank of the same shortlist is +0.2250 recall and +0.3233 MRR over `minilm_vector` |
| the two-second budget and bounded memory remain credible | **not met** — the *existing* arm already spends sixty cutoff events and 1788.9 ms at p95 on eighty pairs, with 827.2 MB peak. Nothing in D1 shows a heavier comparator inside that envelope |
| a maintained dependency with acceptable transitive dependencies and licence | **not evaluated** — no dependency is proposed, so there is nothing to evidence |
| clean-room implementation, no incompatible source copied | **satisfiable** — see below; it is not a discriminator |

A "no-go" is an explicitly valid D1 output and this is one. It is not a judgement that
structural comparison is worthless: the graph arm beat every simpler arm on recall. It is the
judgement that a more expensive comparator is aimed at seven of twenty-six residual queries
while nineteen sit behind a shortlist the comparator never touches, and that the lever which
does reach them costs nothing.

### The first D2 lever is the shortlist, and it is re-measured before FGW is reconsidered

D2 should widen `vector_shortlist` and re-measure before any optimal-transport dependency is
discussed again. A shortlist of twenty raises the reranker ceiling from 0.7625 to 0.9750,
which is the only change measured in D1 that could carry the arm past the 0.70 recall and 0.50
MRR usefulness floor Gate D1 missed. It also multiplies the graph arm's cost, which is exactly
why the re-measurement has to happen against the declared budget rather than in principle.

The FGW question reopens only on a residual report taken *after* that lever, showing a
`rerank_ordering` class that is still the dominant residual.

### Zero packages, and NetworkX stays where it is

The lockfile and the manifest on this branch are byte-identical to `origin/main`. D1 added
four modules, a context source and ten schemas without adding a package.

`networkx` 3.6.1 remains the optional `semantic-graph` extra, BSD-3-Clause, compatible with
this repository's Apache-2.0 licence, with an empty runtime dependency closure — every one of
its requirements is extra-gated — and a pinned wheel hash in `uv.lock`. D1 made it a third
consumer alongside `semantic_memory/graph.py` and `strategies/`, and only inside the graph
edit distance reranker. The action-decision graph contract deliberately validates its own DAG
invariant with Kahn's algorithm instead, because a contract that stops enforcing its invariant
wherever an optional extra is absent is not a contract.

Candidate FGW libraries were not installed, imported or resolved, so this ADR records no
licence, maintenance or transitive-dependency claim about any of them. Should D2 propose one,
`§S21D1-061`'s evidence — source, licence, maintenance and necessity — is gathered at that
point, against a residual report that justifies the proposal.

### The clean-room boundary

The referenced EMG preprint is CC BY-NC-SA 4.0, which is incompatible with this repository's
Apache-2.0 licence. Its concepts informed the design; no paper code, asset, dataset or figure
is copied, vendored or derived file-by-file. The D1 graph modules — 337, 411, 293 and 224
lines — are written against this repository's own contracts, carry no external provenance
marker, and their vocabulary (action-decision graph, failed/successful pair, edit path) names
what the Experience Compiler already produced. The boundary is a licence boundary, not a
naming one: reading a paper and implementing its idea is permitted, copying its expression is
not, and nothing here copies expression.

## Consequences

**Positive.** No unused package, no speculative abstraction and no optimal-transport surface
enters the repository for a gain that the measurement bounds at +0.0875 recall over the arm we
already have. D2 inherits a named first lever with a measured ceiling attached to it, rather
than a dependency to evaluate. The residual report links every class to raw query ids, so the
next measurement can be compared to this one query by query rather than headline to headline.

**Negative.** The structural signal stays coarse. Sixty-one of eighty rankings remain decided
by a tiebreak, and this ADR does not fix that — it declines to fix it with a dependency. If
the shortlist lever raises the ceiling without the comparator improving, the tie degeneracy
becomes the dominant residual and FGW returns as a serious question, which is precisely the
condition written into the reopening rule above.

**Neutral.** Gate L2 stays closed. The graph arm remains measured evidence and an advisory
context source with no execution or acceptance authority, exactly as W5b left it.

## Verification

- `docs/sprints/sprint-21/evidence/sprint-21d1-residuals.json` replays the frozen benchmark
  from committed artifacts alone and reproduces `sprint-21d1-retrieval-benchmark.json` exactly
  — 0.5375/0.4392 and 0.6750/0.4481 with sixty cutoffs — before any classification is applied.
  Every rebuilt query's content hash was compared with the frozen manifest, and every pair
  artifact with its hash in `sprint-21d1-emg-root.json`.
- `git diff origin/main...HEAD -- uv.lock pyproject.toml` is empty. That is the lockfile check
  `§S21D1-062` requires, and it is the mechanical form of "no unused package".
- `docs/sprints/sprint-21/evidence/sprint-21d1-w6a-decision.json` records the dependency scan
  and the condition-by-condition verdict in machine-readable form.

## References

- Sprint 21D1 technical backlog, `§4.11` (FGW decision), `§S21D1-060`, `§S21D1-061`,
  `§S21D1-062`
- `src/cognitive_os/experience/graph_retrieval.py` — the bounded reranker and its budget
- `src/cognitive_os/domain/experience_graph.py` — the resource policy this decision leaves
  unchanged
