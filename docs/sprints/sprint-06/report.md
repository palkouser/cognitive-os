# Sprint 6 report

Status: Complete

## Sprint goal

Sprint 6 implements the first typed, bounded, sequential, replayable Cognitive OS task loop.
Raw input becomes a validated Problem Representation; the controller clarifies, plans,
executes provider and Tool Plane actions, performs deterministic structural acceptance,
repairs within host limits, checkpoints durable state, and terminates through an explicit
event-sourced state machine.

## Problem Representation Engine

Deterministic normalization produces stable hashes, artifact and registry summaries, domain
hints, and non-removable security constraints. Structured provider generation and revision
use the existing Model Execution Service and exported JSON Schema. Unknown fields, malformed
output, identity changes, low-confidence ambiguity, dangling references, and policy removal
fail safely.

## Problem contracts

The public contracts cover generic, coding, mathematics, physics, and logic domains; typed
goals, constraints, assumptions, inputs, outputs, acceptance criteria, and clarification
questions; revision identity; risk; confidence; and source-request integrity. Computed
executability and required-evidence helpers are deterministic and immutable.

## Controller states and transitions

All 13 Sprint 6 states are explicit. The transition table is infrastructure-free and is
tested exhaustively across every source-target pair. Terminal states have no outgoing edges.
Every runtime transition carries a reason, decision ID, and expected task-run stream version.

## Controller budget

Immutable host budgets cover provider calls, tool calls, plan steps, repairs, clarifications,
elapsed time, input and output tokens, optional cost, and a hard 256-iteration ceiling.
Remaining usage saturates at zero and provider output cannot alter configuration.

## Clarification and continuation

Required questions pause durably. Answers are question-scoped and JSON-Schema validated.
Continuation values are opaque, expire, are checkpoint/task/version scoped, and are single-use.
Only SHA-256 token hashes persist; plaintext appears only in the newly issued result.
Successful continuation consumes the token before an append-only representation revision.

## Plan generation and validation

The Sprint 2 `ExecutionPlan` remains the structural DAG. Controller actions map one-to-one to
steps and validate mutually exclusive provider, tool, verification, and manual fields. The
provider-backed planning service rejects unknown registries, oversized plans, invalid action
mappings, hidden tool calls, and repair plans that broaden tool permissions.

## Sequential scheduler

The scheduler chooses one ready incomplete step by sequence and UUID tie-break. Decisions and
step-start events are persisted before execution. Completed steps are never rescheduled, and
failed dependencies or no-progress plans terminate safely.

## Provider execution integration

Provider actions use `ModelExecutionService`; direct SDK access is absent. Structured results,
tool-call proposals, timeouts, persistence, token usage, and child model-call events remain
inside the Sprint 4 boundary. Unexpected tool calls are not executed.

## Tool Plane integration

Tool actions use `ToolExecutionService`, preserving registry lookup, argument schema,
policy, approval, R3 denial, sandbox, artifact, timeout, and child tool-call event boundaries.
Denied, failed, timed-out, and cancelled tool results cannot satisfy completion evidence.

## Minimal acceptance

Deterministic checks cover JSON Schema, artifact presence/integrity evidence, completed steps,
successful tools, and plan consistency. Every required criterion must pass. Required manual
or domain-verifier criteria remain explicitly unverifiable and block completion. Provider
confidence or a model completion claim is never sufficient.

## Repair decisions

Post-verification decision precedence is deterministic. Repair planning increments versions,
preserves accepted step IDs, cannot broaden tool permissions, records every retry lifecycle,
and stops on repair, call, plan-step, elapsed, or hard iteration limits.

## Controller event persistence

Twelve new controller/problem payloads are registered in the event catalog. The task-run
stream owns controller lifecycle; model-call and tool-call child streams remain separate.
All controller appends require expected versions and carry correlation/causation identifiers.

## Checkpoints and recovery

Checkpoints use canonical JSON and SHA-256 integrity, and are task/run/version scoped artifacts.
Full replay reconstructs the current state without a checkpoint. Active child calls classify
as not started, safe to reevaluate, uncertain, or terminal. Uncertain side effects are never
blindly repeated, and corrupt or future checkpoints are rejected.

## Operational commands

Run, resume, inspect, replay, cancel, and smoke commands are present. The run command composes
a credential-free replay-provider path through PostgreSQL and the existing Model Execution
Service. Inspect, replay, and cancellation operate on the authoritative task-run stream.
Commands use safe JSON output and never echo consumed continuation values.

## Test results

- Problem/controller/contract target: 193 passed before final integration expansion.
- Full credential-free repository regression: 566 passed, 16 opt-in tests skipped.
- PostgreSQL and controller integration: 11 passed.
- Controller happy path, clarification/single-use resume, bounded repair, exhaustive state
  transitions, checkpoint integrity, adversarial budgets, recovery classification, and schema
  drift all pass.
- Ruff, Ruff format, mypy, Bandit, repository-language, shell syntax, shellcheck, and
  `git diff --check` pass.
- Python 3.12.13 and `uv pip check` pass.
- Offline sdist and wheel build pass.

## Security status

No credential, plaintext continuation token, unrestricted shell, remote MCP, parallel
controller, second event store, mutable controller-state table, or new orchestration runtime
was introduced. Provider output cannot grant permission, increase budgets, remove machine
policy, execute a tool, or authoritatively complete a task.

## Known issues

The final external PyPI vulnerability query and fresh-environment distribution install could
not complete because sandbox DNS was unavailable. `pip-audit` reached no result; the offline
wheel and sdist build succeeded. The final PostgreSQL replay CLI invocation was not repeated
after the execution environment exhausted its automatic approval allowance; the same
PostgreSQL controller path passed its 11 integration tests. CI remains credential-free and
runs these checks in its normal networked environment.

## Sprint 7 carry-over

- Implement the general Verifier Registry and capability matching.
- Implement coding, SymPy mathematics, Z3 logic, and Pint dimensional verifiers.
- Implement the Acceptance Policy service.
- Implement benchmark cases, runners, metrics, and reports.
- Add Inspect AI and SWE-bench dataset adapters.

## Restore point

Branch: `feature/sprint-6-cognitive-controller`

Planned tag: `sprint-6-baseline`

The restore point contains the typed Problem Representation Engine, bounded controller,
durable clarification and recovery contracts, operational commands, schemas, CI coverage,
tests, ADRs, architecture, and operations documentation.
