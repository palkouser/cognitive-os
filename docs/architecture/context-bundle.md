# Context Bundle contract

A `ContextBundleRevision` is a temporary, immutable, non-authoritative projection. It binds the
exact Context Request, provider profile, ranking profile, token estimator, source snapshot, selected
sections, warnings, exclusions, trace artifact, rendered artifact, revision chain, and content hash.

Sections follow a fixed order: current task, hard constraints, verified evidence, code context,
recent trajectory, user corrections, supported semantic knowledge, disputed/unverified data, and
source warnings. A section has exactly one trust class. Retrieved content is JSON-escaped inside
visible data boundaries with exact candidate and source identifiers.

The artifact set is:

- `context-request.json`;
- `retrieval-trace.json`, containing scores and decisions but no source bodies;
- `context-bundle.json`;
- `rendered-context.txt`.

The model request carries a typed `ContextBundleReference` with bundle ID, revision, bundle artifact
ID, rendered artifact ID, bundle hash, and source-snapshot hash. Untyped metadata is not a substitute.
Bundle artifacts are append-only, replayable, sensitivity-retained, and included in normal artifact
backup. They are never ingested into memory automatically.

See [ADR 0040](../adr/0040-context-bundle-persistence.md).
