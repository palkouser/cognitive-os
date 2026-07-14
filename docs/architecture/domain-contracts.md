# Domain contracts

Cognitive OS exchanges typed Pydantic v2 contracts instead of arbitrary dictionaries.
Mutable application records derive from `ContractModel`; persisted snapshots and value
objects derive from `ImmutableContractModel`. Unknown fields are rejected in both categories.

Identifiers are UUID values generated as UUID4. Persisted timestamps must be timezone-aware;
aware non-UTC input is normalized to UTC. Persisted enums use stable lowercase string values.
Frozen contracts prefer tuples, while dynamic JSON mappings are copied during validation and
serialized immediately at event boundaries.

`ArtifactRef` stores identity, media type, SHA-256 digest, logical storage key, size, and UTC
creation time. It never embeds bytes or absolute host paths. `ErrorInfo` is the single common
error record.

Task, task-run, plan, execution-step, model-call, tool-call, and verifier contracts are public.
Memory items, claims, skills, strategies, episodes, weaknesses, and harness proposals remain
deferred to their owning sprints.
