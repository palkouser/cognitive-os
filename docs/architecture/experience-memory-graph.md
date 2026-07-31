# Experience Memory Graph

Sprint 21D1 projects compiled trajectories into canonical action-decision graphs, pairs each
failed run with the successful run that repaired it, and measures whether bounded retrieval
over those pairs contributes structure a simpler retriever does not already have.

**It fits nothing and activates nothing.** No component is trained, no model is selected, no
threshold is applied to a live decision, and Gate L2 remains closed. Everything below is
evidence and an advisory context source.

## Contracts

`src/cognitive_os/domain/experience_graph.py` holds ten contracts, exported under
`v1/experience-graph/` by the existing schema registry.

An **`ActionDecisionGraph`** is one compiled trajectory: nodes in canonical order (observation,
reasoning, tool action, tool result, verifier, correction, accepted outcome), edges over seven
kinds, and a declared acceptance state. It is a DAG, validated with Kahn's algorithm over the
declared node and edge bounds — deliberately not with `networkx`, because that is the optional
`semantic-graph` extra and an invariant that stops holding wherever an optional dependency is
absent is not an invariant.

Two hashes, and the difference matters:

* `content_hash` covers everything including each node's `source_hash`, the evidence the step
  was projected from. It identifies *this* graph from *this* run.
* `structural_hash` covers labelled structure only, with provenance deliberately excluded. Two
  runs of the same task produce different evidence bytes at every step, so an edit path between
  the two sides of a pair has to be structural or it can never round trip.

A **`FailedSuccessGraphPair`** is causal by construction: the failed side cannot be accepted,
the successful side must be, both sides share a task signature and a group, and the edit path
must start at the failed graph's structure and end at the successful one's.

A **`GraphEditPath`** is the ordered labelled difference between the two. Applying it to the
failed graph must reproduce the successful graph's structure; a pair whose path does not round
trip is rejected rather than stored with whatever came out.

## Authority

The Experience Memory Graph has none. Precisely:

* it never executes a retrieved edit, and a retrieved candidate carries no patch body;
* it never marks an outcome accepted, and never overrides a verifier;
* its candidates reach the Context Builder as `ContextSourceType.EXPERIENCE_GRAPH`, whose
  default trust class is `UNVERIFIED`. A candidate earns `VERIFIED` per retrieval by resolving
  its hashes, never by belonging to a source type;
* those candidates are never `pinned`, never `required` and never `evidence`, so they compete
  under the existing ranking and token budget and lose when something better is present;
* a request whose purpose is not repair or advisory receives nothing at all;
* a verifier that raises degrades a candidate to `UNVERIFIED` rather than propagating, so a
  corrupt store stays visible instead of looking like an empty corpus.

An empty graph set reports **degraded**, not unavailable, because the deterministic path keeps
working without graph memory.

## Resource policy

`GraphResourceLimits` is pre-registered and changing it invalidates affected measurements:

| bound | value |
|---|---|
| nodes per graph | 64 |
| edges per graph | 128 |
| path depth | 32 |
| vector shortlist | 10 |
| returned results | 10 |
| per-pair graph-edit timeout | 250 ms |
| query budget | 2 s |
| cross-task similarity neighbours | 3 |

Ten shortlisted comparisons at 250 ms each already exceed a two-second budget, so the budget is
enforced inside the arm with the per-pair timeout *reserved*: a comparison that could not finish
inside what remains keeps its shortlist position at the fallback score and is counted as a
cutoff. Checking only elapsed time would let a comparison start at the last moment and overrun
the budget by its whole timeout, which is not a budget.

Graph edit distance is NP-hard. That is why the graph arm is a reranker over a MiniLM shortlist
and never a full-corpus scan.

## Retrieval arms

Five arms answer the same frozen queries over the same pool with the same group exclusions, so
a difference between two arms is a difference in ranking and nothing else: `no_memory`,
`lexical`, `exact_signature`, `minilm_vector`, and `minilm_shortlist_plus_bounded_ged`.

Group exclusion happens once, before any arm sees the pool. A repair request cannot retrieve
its own answer.

## What D1 measured

The graph arm reaches 0.6750 top-5 recall against 0.5375 for the strongest arm needing no
structure, and 0.4481 MRR@10 against 0.4392. It loses on nDCG@10, 0.3438 against 0.3740. It
spends 60 budget cutoffs and 1788.9 ms at p95 to do it.

Both numbers sit below the pre-registered usefulness floor of 0.70 recall and 0.50 MRR, so
**Gate D1's condition 15 is not met** and is reported rather than tuned.

The residual analysis found the reason, and it is not the comparator:
`docs/sprints/sprint-21/evidence/sprint-21d1-residuals.json`. Nineteen of twenty-six residual
queries never had a relevant pair on the shortlist at all. The bounded edit distance produces
two distinct scores per query and six across the whole corpus, so sixty-one of eighty rankings
were decided by the pair-id tiebreak. [ADR 0090](../adr/0090-no-fused-gromov-wasserstein-and-the-shortlist-constraint.md)
records the resulting no-go on Fused Gromov-Wasserstein and names the shortlist width as the
binding constraint.

## Limitations

* Sixty of the eighty pairs are historical coding corrections whose original runs cannot be
  recompiled byte for byte. They carry `legacy_recompilation_unavailable`, and the integrity
  report treats that as a warning, never as unresolved evidence.
* Fourteen of the twenty fresh queries have only a same-domain relevance judgement, reported as
  a separate tier and never blended into one number.
* No held-out D2 set exists yet. Every number here is over the frozen D1 benchmark.
* The graph payload lives in the Artifact Store and the root manifest in the repository. No
  migration was added; head remains `0015`.

## Where the code is

| area | module |
|---|---|
| contracts | `src/cognitive_os/domain/experience_graph.py` |
| projection and edit paths | `src/cognitive_os/experience/graph_projection.py` |
| bounded retrieval | `src/cognitive_os/experience/graph_retrieval.py` |
| persisted evidence reader | `src/cognitive_os/experience/graph_store.py` |
| advisory context source | `src/cognitive_os/experience/graph_context.py` |
| integrity checks | `src/cognitive_os/coding/reality_integrity.py` |
| operator commands | `scripts/experience.py` |
