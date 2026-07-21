# Routing configuration

Copy `config/routing.example.yaml` and retain the fail-closed defaults. Static routing is enabled by
persisted policy; shadow evaluation is allowed but shadow execution is always disabled. Learned
routing, exploration, automatic provider enablement, credential storage, automatic promotion,
external routing runtimes, and unbounded multi-model patterns are rejected by schema validation.

Limits cap models, candidates, fallbacks, TaskSignature dimensions, observation batches,
experiments, roles, calls, routing time, and promotion sample thresholds. Adaptive execution cannot
be enabled in configuration: it requires an approved, scoped, persisted policy revision.
