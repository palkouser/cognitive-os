# ADR 0025: Event-sourced Cognitive Controller

Status: Accepted

The task-run event stream is authoritative. Runtime state is a projection reconstructed
from typed events; checkpoints are verified optimization artifacts, not an alternate source
of truth. Sprint 6 adds no mutable controller-state table and no second workflow runtime.

Execution is sequential. Controller lifecycle events stay in the task-run stream. Provider
and tool calls retain their child streams and are linked through correlation, causation, and
step identifiers. A decision and step-start event are committed before an external action.
Expected stream versions reject concurrent writers. Recovery never blindly repeats an
uncertain provider call or side-effecting tool call.
