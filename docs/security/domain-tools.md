# Domain tool and solver security

## Untrusted text never reaches a solver directly

Expressions enter through `verification/mathematics/parsing.py`, which walks a Python AST and
accepts only numeric literals, allowlisted symbols, five binary operators, unary sign, and seven
named functions. Everything else raises `UnsafeExpressionError`. Logic enters as a validated
`LogicExpression`, a closed model with a fixed operator vocabulary; raw SMT-LIB has no entry point.
Units are parsed by `kernels.parse_unit`, which accepts only registry symbols, `*`, `/`, and integer
exponents.

There is no `eval`, no `exec`, no dynamic import, and no pickle anywhere on the path. Rejected in
tests: `__import__('os').system('id')`, `open('/etc/passwd').read()`,
`(1).__class__.__bases__`, `eval('2+2')`, `lambda: 1`, list comprehensions, conditional
expressions, and `globals()`.

## No process, socket, or release path

No module under `src/cognitive_os/domains/` imports `subprocess`, `os`, `socket`, `urllib`, `http`,
`requests`, `httpx`, `shutil`, `pty`, or `multiprocessing`. This is enforced by walking the import
graph with `ast`, not by grepping source text — a denylist that merely names a forbidden module does
not trip the check, while a real import does. The runtime therefore has no merge, tag, push, or
publish capability; release actions are external and operator-owned.

## Bounded resources

`ResourceBudget` is validated before execution and enforced during it: timeout, node count, depth,
symbol count, integer digits, output bytes, and retries. Concretely:

- Exact arithmetic guards every intermediate value against the integer-digit ceiling, so an
  expression bomb such as `99 ** 500` raises `BudgetExceededError` rather than allocating.
- Fractional exponents raise `InexactError` instead of entering a float path.
- Truth-table enumeration checks `2 ** variables` against the row ceiling *before* enumerating.
- Unit exponents are limited to ±12.
- Retries default to zero; there is no unbounded repair loop.

## Failing closed

Nothing short of a full pass becomes a pass. `compose_disposition` returns the worst disposition
over `FAIL`, `RESOURCE_EXHAUSTED`, `UNSUPPORTED`, `INCONCLUSIVE`, `PARTIAL`, `PASS`, and an empty
check set is a `FAIL`, not a vacuous pass. Consequences:

- Solver `unknown` and timeout are `INCONCLUSIVE` and can never become `unsatisfiable`.
- A required verifier that did not run is `UNSUPPORTED` and blocks acceptance.
- An assumption-sensitive equivalence result is inconclusive, not equivalence.
- A sequence answer asserting a unique rule while fitting rules disagree is rejected.

## Provider and unit integrity

A provider-proposed answer travels the identical verification path as a solver-produced one, which
is what makes a fabricated answer detectable. All 51 fixture cases are rejected when given a
deliberately wrong answer. Unit metadata cannot disappear: a quantity answer without units fails
contract validation, and a conversion that reports the wrong unit fails the dimension check.

Runtime unit-definition injection is refused. The registry is project-owned, pinned in source, and
hashed; the hash is recorded with every physics result. Offset temperature units are converted
affinely through explicit handling — scale-only conversion would be a defect, not a shortcut.

## Contract-level refusals

- NaN and infinity are rejected on every numeric field.
- An exact answer carrying an approximation is rejected, so the two can never be conflated.
- `TransferResult` refuses to omit a control arm.
- `TransferResult` refuses to hold `positive_transfer` with a non-empty `hard_gate_failures`, and
  migration `0012` repeats that as a check constraint so no writer can record the combination.

## Gates

Bandit reports zero issues across the pilot package. The 16 governance invariants in
`benchmarks/domain_adapter.py` run as part of both benchmark manifests and as parametrised tests, so
an authority or safety regression fails CI rather than being reported as a metric.
