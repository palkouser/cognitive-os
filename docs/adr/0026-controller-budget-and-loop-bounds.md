# ADR 0026: Controller budget and loop bounds

Status: Accepted

The host owns immutable limits for provider calls, tool calls, plan steps, repair cycles,
clarification cycles, elapsed time, tokens, and optional cost units. Checks run before and
after actions, and actual usage comes from normalized persisted results. Provider output
cannot modify budgets. A defensive ceiling of 256 controller iterations applies in addition
to semantic limits. Exhaustion is an explicit durable controller outcome; no clarification,
repair, or execution loop relies on model compliance for termination.
