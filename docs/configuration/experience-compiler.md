# Experience Compiler configuration

Copy `config/experience.example.yaml` and reduce limits for a deployment. Unknown fields and values
above host ceilings are rejected. Source, event, segment, step, candidate, artifact, provider-call,
and elapsed-time budgets are enforced before or between deterministic stages.

Provider assistance is disabled by default. Provider source creation, provider causal decisions,
automatic routing, destination writes, promotion, and external network sources are always prohibited
in Sprint 14. A compiler profile may reduce host limits but cannot expand them. Profiles are immutable,
versioned, hashed, and bound exactly into every request and snapshot.
