# Temporal semantic data model

Sprint 10 adds twelve PostgreSQL tables without replacing Sprint 9 memory rows. A semantic
observation is an immutable, bounded unit grounded to an exact event, artifact, or Memory Plane
revision. It is not the same object as a governed `MemoryRecord` observation.

`semantic_claims` owns stable scope, subject, predicate, sensitivity, and current-projection
identity. `semantic_claim_revisions` owns object, statement, belief, confidence, half-open valid
interval, system recording time, evidence snapshot, and content hash. Revisions are append-only;
the runtime advances current projections only with an exact expected revision. Evidence,
relations, contradiction history, Wiki history, lineage, and access audit are also append-only.

Valid time answers when a claim applies in the represented domain. System time answers what was
recorded by a given time. `valid_at`, `known_at`, and combined bitemporal reads select the highest
visible revision without exposing a later system-time revision. Overlaps remain visible and are
handled as contradictions rather than destructive corrections.

The frozen predicate registry defines allowed value types, cardinality, temporal behavior, and
deterministic contradiction rules. Values are typed; labels never replace stable identity.
PostgreSQL relations reference exact claim revisions. No graph database or approximate index is
part of this model.

The initial registry covers project language and tooling, repository base/profile, task outcome,
acceptance and changed files, verification results, user instructions, and explicit memory
corrections. Repository base/profile and project Python-version predicates are functional; the
remaining predicates preserve multiple grounded values. Deterministic extractors currently map
code-context, accepted episode, task-summary, verification-summary, correction, and user-instruction
memory fields to these host-owned predicates. Each emitted claim uses its own exact field span.

Initial claim revision and evidence rows commit in one PostgreSQL transaction. Later claim revisions
and their evidence use the same atomic boundary. Lifecycle events remain a separate append-only
audit write; health diagnostics expose any projection/event divergence without destructive repair.
