# Governed procedural Skill Engine

Sprint 12 adds deterministic, revisioned procedural guidance above the Sprint 11 Context Builder.
A skill is a non-authoritative package plus host-owned metadata, requirements, preconditions,
budgets, lifecycle state, and verifier evidence. It becomes executable only at an exact verified
revision.

PostgreSQL is authoritative for skill state, the artifact store for package bytes, and the event
store for lifecycle evidence. A frozen registry exposes exact revisions. Host-registered typed
preconditions and stable sorting select applicable skills; provider suggestions are advisory and do
not affect authorization. Statistics influence ranking only after the configured sample threshold.

The Context Builder exposes verified skills as `procedural_skill` retrieved data. Metadata,
summary, full instructions, and explicitly referenced resources hydrate progressively. Instructions
remain escaped retrieved data in a separate trust section; they never become system instructions.
Retrieval, hydration, selection, export, and execution append access records.

Execution validates the package hash, registry snapshots, input schema, sensitivity, permissions,
requirements, and budget, then delegates to the existing Controller adapter. Registered provider,
tool, verifier, approval, and acceptance boundaries remain authoritative.
