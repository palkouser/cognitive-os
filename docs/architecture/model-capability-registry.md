# Model Capability Registry

The registry separates host provider configuration from capability evidence. The provider layer
owns adapters, endpoints, credentials, enablement, health, transport, retries, and execution. The
registry stores only exact provider/model references, declared evidence, measured observations,
cohort statistics, uncertainty, and append-only profile revisions.

```text
Problem Representation -> TaskSignature -> RoutingRequest
  -> provider health and hard capability filters -> static decision
  -> optional non-executing shadow decision -> Context Bundle -> provider request
  -> verifier and acceptance -> outcome -> governed observation -> rebuildable statistics
```

Declared evidence comes from operator configuration, local provider documentation, or replay
contracts. Provider self-description is advisory. Measured evidence requires a deterministic
benchmark, replay contract, opt-in live benchmark, or verified task outcome with complete lineage.
Unknown latency and cost remain unknown; they are never converted to zero.

PostgreSQL migration `0008` owns current profile and policy projections plus append-only revisions,
observations, decisions, outcomes, statistics, experiments, and accesses. The event store owns
lifecycle evidence. Large traces and experiment artifacts remain in the Artifact Store. Restores
must preserve payload hashes, rebuild statistics, and replay decisions without touching provider
configuration.

Gate H remains partial after Sprint 16. Sprint 17 may consume exact routing evidence to diagnose
recurring weaknesses, but it cannot replace the registry or router.
