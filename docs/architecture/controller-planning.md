# Controller planning

The Sprint 2 `ExecutionPlan` remains the structural DAG. `ControllerExecutionPlan` adds one
typed action per step and declares sequential execution. Provider, tool, verification, and
manual actions have mutually exclusive validated fields. The scheduler selects the lowest
sequence ready step, breaking ties by canonical UUID, and never reschedules completed steps.
Unknown providers, tools, tool versions, verifiers, parallel actions, cycles, and oversized
plans are rejected before execution.
