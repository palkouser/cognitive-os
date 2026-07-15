# Memory data model

`memory_items` contains stable identity and the exact current projection. `memory_revisions`
contains immutable typed content and governance metadata. `memory_sources` records ordered typed
provenance, `memory_embeddings` stores revision/model/content-specific vectors, and
`memory_accesses` records each returned result without copying content.

Revision one has no predecessor. Every later revision references the immediately preceding
revision. Database constraints enforce positive revisions, bounded confidence and salience,
source identity shape, vector dimension, hashes, and current status. Deferred provenance checks
reject revision transactions with no source. Triggers reject update or delete on history tables;
the runtime advances current projection only through an expected-revision function.

The supported types are episode, observation, decision, correction, task summary, code context,
verification summary, failure pattern, and user instruction. There is deliberately no `fact`
type. Repository scope uses a stable digest rather than an absolute host path. Large trajectories,
diffs, reports, and command output stay in the artifact store.
