# ADR 0060: Weakness lifecycle and resolution

## Status

Accepted for Sprint 17.

## Decision

Automatic confirmation is disabled. Provider or model actors cannot authorize lifecycle changes.
Normal confirmation requires configured signal count, distinct tasks, evidence coverage, and a
verifier bundle. A rare critical-safety case may use the explicit exception only with an operator
approval reference.

| Current | Allowed next state |
| --- | --- |
| candidate | candidate, confirmed, superseded, retracted |
| confirmed | confirmed, monitoring, resolved, superseded, retracted |
| monitoring | monitoring, confirmed, resolved, superseded, retracted |
| resolved | monitoring, superseded, retracted |
| superseded | retracted |
| retracted | none |

Resolution requires bounded monitoring evidence and appends a revision; it never deletes history.
Recurrence returns a resolved item to monitoring. Supersession requires a distinct successor, and
retraction preserves all prior evidence.

## Rejected alternatives

Automatic provider confirmation, destructive resolution, status overwrite, and causal inference
from correlation are rejected.
