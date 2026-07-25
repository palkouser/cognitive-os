# ADR 0073: Domain libraries are tools, never authorities

## Status

Accepted for Sprint 20.

## Decision

SymPy, Pint, Z3, and Hypothesis are optional tools and test adapters. They do not own task
representation, planning, skills, strategies, benchmark truth, final acceptance, memory, proposal
approval, promotion, repository mutation, or release authority. Sprint 7 already registered them
behind `VerifierRegistry` with explicit unavailability records; Sprint 20 keeps that boundary and
adds nothing that bypasses it.

The mandatory Gate K path is dependency-free. `cognitive_os.domains.kernels` implements exact
rational arithmetic, a project-owned unit registry with base-dimension exponent vectors, and
bounded truth-table enumeration using only the standard library. No module under
`src/cognitive_os/domains/` may name `sympy`, `pint`, or `z3`; a structural test enforces this, so
the core cannot come to require an extra by accident. The optional libraries remain available as
escalation for instances outside the dependency-free scope.

Solving and checking are separate code paths. For every registered task class the registry binds
one solver and one independent checker that recomputes the result by a different route: digit-wise
partial products rather than multiplication, substitution rather than the quadratic formula,
round-trip conversion rather than a single conversion, row-by-row re-evaluation rather than a
stored table. `DomainPilotService` records the checker's disposition verbatim and composes
acceptance with `compose_disposition`, so no component in the path can accept itself.

## Alternatives and consequences

Making SymPy the mandatory arithmetic engine was rejected: it would put an optional heuristic
library on the acceptance path and make the CI gate depend on a wheel download. Reusing Pint for
the mandatory unit path was rejected for the same reason, and because a project-owned registry
gives a stable hash that can be recorded with every result.

The consequence is a deliberately narrow mandatory scope. Irrational results, non-rational roots,
and formulas outside the allowlisted AST raise `InexactError` or `UNSUPPORTED_PROBLEM_TYPE` rather
than being approximated. That is the intended trade: a smaller verified surface over a larger
unverified one.

## Verification

`tests/cognitive_os/domains/test_cross_domain_pilot.py` covers exact arithmetic, inexactness
refusal, budget ceilings, unit incompatibility, offset units, registry hash stability, truth-table
ceilings, and the structural extras check. All 51 fixture cases are accepted with correct answers
and all 51 are rejected with deliberately wrong ones.
