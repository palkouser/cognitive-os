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

## A failing tool cannot crash past the Controller

`DomainActionExecutor.execute` catches `ToolPlaneError` and returns a failed `ActionOutcome` instead
of letting the exception propagate. Before this fix, a genuinely failing tool call — the Tool Plane
had already recorded `tool_call.failed` and re-raised — aborted the entire governed run with an
unhandled traceback: no execution-step failure, no verifier result, no acceptance decision, and no
audit trail for what happened. A harness that cannot answer a legitimate input must produce a
rejection with evidence, not lose the evidence to a crash.

Separately, the shared `ControllerVerificationService._subject` (owned outside the domain package,
used by every Controller-driven acceptance check) built an invalid `VerificationSubject` when the step
under verification produced no output — passing `inline_value=None` with no other subject source,
which the contract's own validator rejects. This is now stated explicitly as `{"subject_absent":
true}`, and `domains.checker` classifies that as `UNVERIFIABLE`, not `FAILED`: a verifier that never
saw a candidate answer has not refuted one.

## No self-promotion authority

The weakness-mining, proposal, and controlled-change cycle mines a real capability gap, generates a
proposal, and runs an isolated experiment — and stops. `TOOL_DEFINITION_CHANGE` is classified tier 3
by the existing `ChangeSurfaceRegistry`, which fixes its promotion mode to `MANUAL_REVIEW_ONLY`; the
domain package supplies no override and holds no promotion authority. The isolation manifest proves
the active checkout, database, and artifact namespace are untouched — network policy `disabled`,
exactly one file in scope, and the baseline commit pinned to the protection snapshot's own recorded
commit. Every stage of the cycle is deterministic and reproducible offline, with no credentials and no
network access.

## Gates

Bandit reports zero issues across the pilot, learning-plane, and weakness-mining packages. The 28
governance invariants in `benchmarks/domain_adapter.py` — including three for the learning-plane
bridge and three for weakness mining, proposal traceability, and self-promotion refusal — run as part
of both benchmark manifests and as parametrised tests, so an authority or safety regression fails CI
rather than being reported as a metric.
