# Controller state machine

Every state and transition is defined in `controller/transitions.py`; exhaustive tests reject
all other source-target pairs. Terminal states have no outgoing edges.

```mermaid
stateDiagram-v2
  received --> representing_problem
  representing_problem --> waiting_for_clarification
  representing_problem --> ready
  ready --> planning
  planning --> executing
  executing --> verifying
  executing --> paused
  verifying --> completed
  verifying --> repairing
  repairing --> executing
  paused --> executing
  paused --> verifying
  waiting_for_clarification --> representing_problem
  received --> cancelled
  representing_problem --> failed
  planning --> failed
  executing --> failed
  verifying --> failed
  repairing --> failed
```

Active states also have the explicit cancellation and budget-exhaustion transitions declared
by the transition table. Every transition carries a decision ID, reason, and expected version.
