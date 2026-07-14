# Bounded Cognitive Controller

The controller is a Cognitive OS application service over the existing provider, Tool Plane,
event, artifact, approval, registry, telemetry, and replay boundaries. It selects exactly one
ready plan step, records the decision and step start, invokes the existing execution service,
records the terminal result, checkpoints, and verifies. Provider output proposes data only;
it cannot change state, budget, policy, approval, or completion.

```mermaid
sequenceDiagram
  Controller->>Provider Execution: typed provider action
  Provider Execution->>Event Store: child model-call events
  Controller->>Tool Execution: typed tool action
  Tool Execution->>Event Store: child tool-call events
  Controller->>Minimal Acceptance: persisted structural evidence
```
