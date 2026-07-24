# ADR 0076: Cross-domain tasks execute under existing authorities

## Status

Accepted for Sprint 20.

## Decision

The cross-domain pilot contributes exactly two components to the execution path —
the `domains.solve` tool and the `domains.checker` verifier — and borrows every authority from the
services that already own it. There is no second controller, no second tool authority, and no
domain-owned acceptance.

- **Planning.** `DomainProblemEngine` implements `ProblemRepresentationPort` and `DomainPlanner`
  implements `PlanningPort`. The Cognitive Controller drives its own state machine, applies its own
  budgets, and creates the plan. A domain plan contains exactly one bounded `TOOL` action; a
  `PROVIDER` action is never emitted.
- **Execution.** `DomainActionExecutor` implements `ControllerActionExecutor` and runs that action
  through `ToolExecutionService`. Every solve therefore produces the full
  `requested → authorized → started → completed` audit trail, and the Tool Plane owns the timeout
  and the policy decision. `domains.solve` is `R0`, `HOST_READ_ONLY`, deterministic, declares no
  side effects, and is the only tool enabled for a domain run.
- **Acceptance.** The problem representation carries `DOMAIN_VERIFIER` acceptance criteria naming
  `domains.checker`. `ControllerVerificationService` resolves them through the `VerifierRegistry`
  and hands the results to the Acceptance Service, which owns the decision. A second
  `STEP_COMPLETED` criterion ensures a missing tool result cannot be read as an absent-but-
  acceptable answer.
- **Skills.** `run_case_as_skill` executes a case as an exact `VERIFIED` skill revision through
  `SkillExecutionService`, which enforces the package hash, the registry snapshot, the package
  artifact integrity, and the presence of a valid Context Bundle before the first step.
- **Routing.** `domain_task_signature` emits a canonical `TaskSignature` carrying declared tool
  capabilities, exact skill and strategy revisions, and the verifier profile — and no prompt or
  instruction text. The mandatory path is tool-only, so no provider is required for acceptance.

The Controller charges one *nominal* provider call for problem representation because that step is
normally a model call. `DomainProblemEngine` is deterministic and contacts no provider. That ledger
entry is the Controller's accounting and is deliberately not overridden; the domain budget allows
for it instead, and no provider is configured, so a real model call cannot occur.

## Required context

The mandatory path calls no provider, so there is no prompt to fit. The Context Bundle is used for
its other job: proving the evidence an answer depends on was present. Assumptions, required units,
constraints, and provenance are each a `required` and `pinned` candidate.

The Context Builder fails closed on a required candidate it cannot fit or hydrate, but it cannot
notice an item a retriever never offered — no retrieval system can. `assert_required_context` closes
that gap where the requirement is declared, comparing the identities the case says it needs against
the identities the bundle carries. Omitting a required unit, assumption, or provenance record raises
rather than yielding a thinner bundle.

## Alternatives and consequences

Keeping `DomainPilotService` as the execution path was rejected: it was a parallel orchestrator, and
Gate K requires Controller-owned plans. It is retained only as the direct verification composer used
by the transfer experiments, where running nine full Controller arms per experiment would add
governance ceremony without changing what is measured.

Skipping the Context Bundle entirely was considered, since a provider-free path has no prompt to
build. It was rejected because required-evidence coverage is a real Gate K obligation and needed an
enforcement point.

The consequence is more moving parts per case — a Controller run, a Tool Plane call, two verifier
executions, and an acceptance decision instead of a direct function call — in exchange for every
domain result being auditable through the same events as a coding result.

## Verification

All 51 fixture cases complete under the Controller and are accepted; all 51 are rejected when a
wrong answer is injected, through the identical plan, tool call, and acceptance path. Six governance
invariants — `controller_owns_plan`, `tool_plane_audits_solve`, `controlled_path_rejects_wrong`,
`required_context_enforced`, `skill_engine_verified_only`, `routing_signature_tool_only` — run in
both benchmark manifests and as parametrised tests.
