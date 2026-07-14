# Event naming

Published event names use:

```text
<aggregate-or-component>.<past-tense-action>
```

Examples include `task.created`, `task_run.started`, `tool_call.denied`, and
`verifier.completed`. Names are lowercase dotted identifiers. Permission denial is distinct
from execution failure, verifier completion may carry any completed verification outcome,
and user correction records provenance rather than declaring truth.

An event type is permanent after publication. A semantic replacement receives a new event
type instead of renaming an existing one.
