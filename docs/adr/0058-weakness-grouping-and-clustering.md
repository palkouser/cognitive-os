# ADR 0058: Weakness grouping and advisory clustering

## Status

Accepted for Sprint 17.

## Decision

Exact signature equality is the baseline and authoritative grouping rule. Rebuild sorts inputs and
produces stable content hashes. The default clusterer is a no-op projection with one exact group per
cluster. Comparison reports additions, removals, and stable membership without changing groups.

NetworkX may support bounded in-process neighbourhood analysis. scikit-learn and HDBSCAN may be
evaluated only behind an optional clustering extra after benchmark and dependency review. Embedding
inputs must be pinned, local, bounded, and advisory. Removing any optional library falls back to
the no-op implementation without schema or authority changes. No external graph store is used.

## Rejected alternatives

Approximate grouping as identity, automatic cluster merges, network model downloads, mandatory
embeddings, and external graph databases are rejected.
