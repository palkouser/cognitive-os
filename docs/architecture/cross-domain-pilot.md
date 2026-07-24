# Cross-domain pilot architecture

Sprint 20 runs representative mathematics, physics, and logic tasks through the same governed
boundaries the coding path already uses. It adds an orchestration and evidence layer; it does not
add a second controller, verifier authority, memory store, or release path.

## Path

```text
DomainBenchmarkCase
-> immutable DomainProblem + frozen DomainVerificationPlan
-> registry resolution (exactly one solver and one independent checker)
-> solver produces DomainDerivation + candidate answer
-> checker recomputes by a different route and judges the candidate
-> compose_disposition -> DomainVerificationOutcome
-> DomainPilotRun + lifecycle events + append-only evidence
-> TransferExperiment over every control arm
-> hard negative-transfer gates -> TransferResult
```

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
