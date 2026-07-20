# Experience candidates

The compiler supports nine proposed candidate types: memory, semantic observation, skill, strategy,
failure pattern, routing observation, benchmark case, negative example, and corpus item. Generation
is evidence-dependent: for example, a routing observation requires provider evidence and a skill
candidate requires a repaired accepted path.

Each candidate includes exact snapshot provenance, source and evidence references, propagated scope
and sensitivity, limitations, a target subsystem and schema version, the generator profile, and a
canonical hash. Forbidden authority fields and secret-like summaries fail validation.

Candidate status is append-only. `validated` is compiler validation only; `routed` is export or
staging hand-off only. The deterministic export package contains candidate metadata, body, sources,
evidence, generalizability, limitations, verification, and a checksummed manifest. Sprint 15 owns all
destination classification, licensing, deduplication, quality, staging, and promotion decisions.
