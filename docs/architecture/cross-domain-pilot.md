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
| `benchmarks/domain_adapter.py` | Executes cases and 16 governance invariants |
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
