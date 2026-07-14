# ADR 0024: Problem Representation Engine

Status: Accepted

Raw user text is not an execution contract. Cognitive OS first performs deterministic
normalization, then asks the configured provider for a `ProblemRepresentation` matching
the exported JSON Schema. Provider output is untrusted and strictly validated. Machine,
project, user, environment, and inferred constraints are merged in that precedence order;
a provider may add lower-priority information but cannot remove machine policy.

Goals, constraints, assumptions, inputs, outputs, acceptance criteria, and missing
information remain explicit. Missing critical information pauses for clarification.
Revisions are append-only and preserve the original representation in the task-run stream.
No provider-specific type enters the domain contract.
