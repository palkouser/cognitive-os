# Cross-domain pilot architecture

Sprint 20 runs representative mathematics, physics, and logic tasks through the same governed
boundaries the coding path already uses. It adds an orchestration and evidence layer; it does not
add a second controller, verifier authority, memory store, or release path.

## Governed path

This is the path Gate K condition 2 requires. Everything except the solver and the checker belongs
to a service that already existed.

```text
DomainBenchmarkCase
-> DomainProblemEngine (ProblemRepresentationPort)  -> ProblemRepresentation
-> Cognitive Controller state machine + budgets
-> DomainPlanner (PlanningPort)                     -> ControllerExecutionPlan, one TOOL action
-> DomainActionExecutor (ControllerActionExecutor)
-> Tool Plane: domains.solve, R0, deterministic     -> requested/authorized/started/completed
-> ControllerVerificationService -> VerifierRegistry -> domains.checker
-> Acceptance Service                                -> acceptance decision
-> SkillExecutionService when run as a verified skill revision
-> TaskSignature recorded for routing observation
```

The domain package contributes a solver and a checker. It borrows planning, execution, budgets,
state transitions, verification, acceptance, skill lifecycle, and context assembly.

### Direct path

`DomainPilotService` composes the same solver and checker without the Controller. It is not the
governed path and is not used for case execution; it remains as the verification composer behind the
transfer experiments, where nine full Controller arms per experiment would add ceremony without
changing what is measured.

## Learning-plane path

This is the part of Gate K condition 8 the compilation stage delivers: experience compilation,
memory, semantic extraction, and corpus declaration.

```text
run_case_controlled -> MemoryEventStore (the recorded event trail)
-> build_compilation                        -> ExperienceCompilationRequest
-> ExperienceCompiler (unmodified)          -> candidates, decision, manifest
-> project_run                              -> TaskSummaryMemoryContent, VerificationSummaryMemoryContent
-> MemoryService (governed gateway)         -> two memory revisions, DOMAIN/TASK scope
-> SemanticExtractionService (unmodified)   -> grounded observations and claims
-> corpus_request per corpus-bound candidate -> CorpusFactory (unmodified)         -> corpus items
```

`src/cognitive_os/domains/learning.py` contributes the translation from recorded events to compiler
and memory inputs; it owns no compilation logic, no memory policy decision, no grounding logic, and
no corpus routing decision. Every `TimelineEntry` traces back to one recorded `EventEnvelope`: its
identity is the event's own `event_id`, and its evidence is the event's own `payload_hash`. An event
type outside the declared source-type table raises, so an unrecognised event cannot be silently
dropped or misfiled.

A rejected run is not laundered into a success story: its terminal state stays `"rejected"`, it
produces `FAILURE_PATTERN` and `NEGATIVE_EXAMPLE` candidates instead of `MEMORY` and `SKILL`
candidates, and the projected memory's `review_status` reads `"rejected"`. See ADR 0077.

## Weakness, proposal, and controlled-change path

This is the rest of Gate K condition 8: a real capability gap, mined by the unmodified Weakness
Mining Service, proposed by the unmodified Harness Proposal Engine, and run as an isolated experiment
by the unmodified Controlled Change Service.

```text
probe_case ("polynomial-equation" with irrational roots — a real, legitimate input)
-> run_case_controlled                       -> a genuine tool failure and rejection
-> DomainWeaknessSourceResolver + DomainCapabilityGapExtractor
-> WeaknessMiningService (unmodified)         -> one grouped, scored WeaknessRevision
-> confirm_domain_weakness (explicit operator transition) -> CONFIRMED
-> HarnessProposalService.create_from_weakness (unmodified) -> a TOOL_DEFINITION_CHANGE proposal
-> ControlledChangeService (unmodified)       -> isolated experiment, evaluation matrix, assessment
-> PromotionAssessment: REQUIRES_MANUAL_REVIEW (tier 3, no runtime promotion authority)
```

`src/cognitive_os/domains/weakness.py` and `improvement.py` contribute the probes, the source and
extractor adapters, and nothing else. The weakness is real: `polynomial-equation` is a registered
task class that accepts any real quadratic, but the solver is exact-rational only (see "Scope and
limitations"), so an irrational-root input is admitted at planning time and fails at solve time. The
probe is not rigged — it is a legitimate input the harness genuinely cannot answer, run through the
identical governed path every fixture case uses.

Mining identity deliberately excludes each run's per-execution event-payload hashes: a weakness is a
property of the harness, not of one run, so mining the same gap twice must yield the same weakness.
See ADR 0078 for the determinism argument and the two shared-component bugs the probes' genuine
failures surfaced: `DomainActionExecutor` letting a tool failure crash the Controller run instead of
reporting it, and `ControllerVerificationService` building an invalid verification subject when a
step produced no output. Both are fixed in the Controller and Tool Plane layers, not worked around in
the domain package.

## Authority map

| Concern | Owner | Domain contribution |
|---|---|---|
| Problem representation | Cognitive Controller | supplies a `ProblemRepresentationPort` |
| Planning | Cognitive Controller | supplies a `PlanningPort` emitting one TOOL action |
| Budgets, state machine | Cognitive Controller | none |
| Tool authorisation, audit, timeout | Tool Plane | registers `domains.solve` |
| Verification | Verifier Registry | registers `domains.checker` |
| Acceptance | Acceptance Service | none |
| Skill lifecycle | Skill Engine | supplies a runner and a context factory |
| Context assembly | Context Builder | supplies required-evidence candidates |
| Routing | Model Capability Registry | emits a `TaskSignature` |
| Merge, tag, release | Operator | none, structurally |

### Provider accounting

The Controller charges one nominal provider call for problem representation, because that step is
normally a model call. `DomainProblemEngine` is deterministic and contacts no provider. That entry
is the Controller's accounting and is not overridden; the domain budget allows for it, and no
provider is configured, so a real model call cannot occur.

### Required evidence

Assumptions, required units, constraints, and provenance are `required` and `pinned` Context
candidates. The Context Builder fails closed on a required candidate it cannot fit or hydrate;
`assert_required_context` additionally catches an item a retriever never offered, which no retrieval
system can detect on its own.

## What Sprint 7 already provided

The typed ASTs, their strict parsers, and the domain verifier bundles were delivered in Sprint 7
and are reused unchanged:

- `verification/mathematics/expression_ast.py` and `parsing.py` — closed expression AST and an
  allowlisting parser over a small Python subset.
- `verification/logic/ast.py` — closed Boolean and arithmetic AST with node, depth, and variable
  ceilings.
- `verification/physics/` — quantity contract with a safe-unit pattern and Pint-backed verifiers.
- `verification/factory.py` — registers the optional SymPy, Pint, and Z3 verifiers and records
  explicit unavailability when an extra is absent.

Sprint 20 adds no parser and no second AST. Raw text still reaches a solver only through the
Sprint 7 parser.

## What Sprint 20 adds

| Module | Responsibility |
|---|---|
| `domain/domains.py` | Immutable contracts, enums, and `compose_disposition` |
| `domains/kernels.py` | Dependency-free exact arithmetic, unit registry, truth tables |
| `domains/solvers.py` | One solver and one independent checker per task class |
| `domains/registry.py` | Total, deterministic problem-type resolution |
| `domains/service.py` | Governed orchestration and acceptance composition |
| `domains/transfer.py` | Control arms, measurement, and hard gates |
| `domains/repository.py` | Append-only in-memory evidence store |
| `domains/fixtures.py` | 51 credential-free deterministic cases |
| `domains/controller.py` | Problem engine, planner, Tool Plane action executor |
| `domains/runner.py` | Composition of the governed Controller stack |
| `domains/context.py` | Required-evidence Context profile and coverage check |
| `domains/skill_execution.py` | Skill runner, context factory, `TaskSignature` |
| `domains/skill_runner.py` | Skill Engine composition |
| `tools/domains.py` | `domains.solve` Tool Plane tool |
| `verification/domains.py` | `domains.checker` registered verifier |
| `events/memory_store.py` | Shared in-process `EventStorePort` for offline runs |
| `events/domain_events.py` | Seven lifecycle events |
| `domains/learning.py` | Translates a run's recorded events into compiler, memory, and corpus inputs |
| `domains/weakness.py` | Legitimate-input probes, source resolver, and signal extractor for mining |
| `domains/improvement.py` | Proposal generation and isolated-experiment composition |
| `benchmarks/domain_adapter.py` | Executes cases and 28 governance invariants |
| `infrastructure/domains/postgres/` | Migration `0012` metadata |

## Registered task classes

25 problem types: 9 mathematics, 8 physics, 8 logic. Resolution is total — an unregistered type
raises `UnsupportedProblemType` before anything executes, so an unknown task cannot fall through to
an unbounded path.

- **Mathematics** — long multiplication and division, fraction and rational arithmetic, algebraic
  simplification, linear and quadratic equations, symbolic equivalence, exact versus approximate.
- **Physics** — unit conversion, dimensional analysis, quantity calculation, model selection,
  conservation, limiting cases, order of magnitude, significant figures.
- **Logic** — truth tables, validity, satisfiability, constraint satisfaction, consistency,
  counterexample search, sequence induction, competing hypotheses.

## Why acceptance cannot self-certify

Each task class has two independent code paths. The checker never reads the solver's output as
truth; it recomputes and compares. Examples:

| Task | Solver route | Checker route |
|---|---|---|
| Long multiplication | `left * right` | sum of digit-wise partial products |
| Long division | `divmod` | reconstruct `divisor * quotient + remainder` |
| Linear equation | isolate and divide | substitute the root, require zero residual |
| Quadratic | discriminant formula | substitute each root; discriminant check when none |
| Unit conversion | forward conversion | convert back, require the original magnitude |
| Truth table | enumerate | re-evaluate every row independently |
| Satisfiability | first satisfying row | re-evaluate the claimed model against the constraints |

A plan may require a capability the checker never exercised. That is recorded as `UNSUPPORTED`, and
`compose_disposition` takes the worst disposition, so a missing verifier blocks acceptance instead
of being silently ignored.

## Skills and strategies

Eleven domain skills and six domain strategies are registered through the existing Skill Engine and
Strategy Evolution Graph as ordinary packages under `procedural_skills/` and `strategies/`. They
reach `VERIFIED` through the Sprint 12 and Sprint 13 lifecycles with no new promotion path. The seed
set grew from 8 skills and 7 strategies to 19 and 13; its size is now derived from
`seed_package_paths()` and `seed_strategy_paths()` rather than duplicated as literals.

## Scope and limitations

- Exact rational arithmetic only. Irrational results raise rather than being approximated.
- Quadratics are solved over the rationals; irrational roots are out of scope and reported as such.
- Algebraic equivalence is evidenced by exact evaluation at sampled points, which is evidence and
  not a proof of identity. The bundle says so in its own check detail.
- Sequence induction searches a small, transparent rule space. Absence of a fitting rule there is
  not absence in general, and underdetermination is reported whenever fitting rules disagree.
- Propositional logic only; quantifiers and general theorem proving are out of scope.
- No general physics simulation. Model selection audits declared assumptions against declared
  conditions.
- Learning-plane and weakness-mining output stays in the same offline, in-memory repositories the
  domain execution path uses; it is not written to PostgreSQL in this sprint. The Memory Plane,
  semantic memory, Corpus Factory, weakness, proposal, and change PostgreSQL adapters already exist
  and are exercised by their own integration suites.
- The weakness-mining path probes one capability gap (irrational roots on `polynomial-equation`).
  Finding that gap does not imply every registered task class has been probed for its own edge cases;
  it demonstrates that the mining, proposal, and controlled-change services accept real domain
  evidence end to end.
- The isolated experiment proves the change in isolation and stops at `REQUIRES_MANUAL_REVIEW`.
  Nothing in this repository promotes it; that step is operator-owned, matching the release stance in
  ADR 0076.
