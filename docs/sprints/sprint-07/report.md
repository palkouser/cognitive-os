# Sprint 7 report

Status: Complete

## Sprint goal

Sprint 7 replaces the temporary Sprint 6 acceptance boundary with an authoritative,
typed verifier registry, deterministic acceptance policy, controller integration, and a
reproducible benchmark foundation. Verification results, rather than provider confidence,
now decide whether required acceptance criteria are satisfied.

## Verifier contracts and registry

Immutable contracts describe verifier capabilities, descriptors, requirements, subjects,
requests, executions, bundles, health, and resource usage. The registry rejects duplicate
identities, freezes explicitly, reports unavailable optional verifiers, and produces a
canonical snapshot hash. Capability matching and tie-breaking are deterministic and reject
ambiguous or unsupported requests safely.

## Verification execution and persistence

`VerificationService` enforces verifier-call and elapsed-time budgets, normalizes verifier
errors separately from subject failures, and aggregates immutable executions into bundles.
Verifier lifecycle events use the existing event store with expected-version concurrency,
correlation, and causation metadata. Recovery tests cover completed, failed, and interrupted
execution histories.

## Generic and Sprint 6 compatibility verifiers

Registered generic verifiers cover exact values, JSON Schema, artifact integrity, completed
plan steps, successful tool calls, and structural plan consistency. The Sprint 6 minimal
checks are therefore represented by normal registry entries instead of a privileged
completion path. Unknown configuration and missing evidence fail closed.

## Coding verifiers

Pytest, Ruff, MyPy, and controlled-import verification invoke commands only through the
existing `ToolExecutionService`; they do not call a shell or subprocess directly. Static
policy verifiers enforce allowed and forbidden paths, changed-file sets, diff limits, and
dependency-file changes. Source-workspace mutation and package installation are outside the
verifier authority boundary.

## Mathematics verifiers

A bounded AST parser accepts a sealed arithmetic grammar and rejects attributes, indexing,
comprehensions, imports, lambdas, and unknown calls. Numeric comparison supports explicit
tolerances. Symbolic equivalence and equation-solution checks run SymPy in a bounded worker
process, returning timeout, unsupported, configuration, and verification-error outcomes
without evaluating arbitrary Python.

## Logic verifiers

Typed logical expressions map explicitly to Z3 constructors. Satisfiability, contradiction,
implication, and equivalence checks enforce node, variable, and timeout limits. Raw SMT-LIB,
dynamic evaluation, and unrestricted solver input are not accepted.

## Physics verifiers

Pint-backed dimension, quantity, and unit-conversion checks use a sealed unit registry and
bounded numeric tolerances. Custom unit definitions, offset-unit ambiguity, and unknown units
fail safely. The verifiers distinguish dimensional incompatibility from runtime failure.

## Acceptance policy and controller integration

Typed policies map criteria to required verifier capabilities and define explicit handling
for pass, fail, unavailable, timeout, unsupported, and verifier-error outcomes. The
acceptance service emits an immutable `AcceptanceDecision`; model confidence never satisfies
a criterion. The bounded controller accounts for verifier calls and elapsed verification
time, persists `controller.acceptance_decision_recorded`, repairs only within its existing
limits, and cannot complete while a required criterion is unresolved.

## Benchmark framework

Typed manifests and cases, deterministic dataset expansion, registry snapshots, canonical
hashing, resource budgets, runners, lifecycle events, aggregate metrics, JSON reports, and
run comparison are implemented. Reports record manifest and case hashes, Git commit,
configuration, provider, verifier versions, Tool Registry snapshot, sandbox digest,
environment metadata, seed, timestamps, correctness, latency, resource, and safety fields.

The tracked Sprint 7 seed manifest expands deterministically to 56 credential-free cases
across generic, coding, mathematics, logic, and physics domains. The four-case CI manifest
and the 56-case seed manifest both completed with a 1.0 pass rate and no verification errors.

## External evaluation adapters

The Inspect adapter exports deterministic, Inspect-compatible Python task material while
keeping Cognitive OS reports and events authoritative. Inspect AI itself is not installed:
version 0.3.246 constrains Click below the security-fixed release, so `benchmark-inspect`
remains a reserved empty extra until upstream compatibility is available. The exporter and
its CI contract remain fully credential-free.

The SWE-bench adapter imports local metadata-only manifests. It performs no download,
repository clone, patch application, test execution, or network request; repository
preparation remains an explicit external operation.

## Operational commands

Commands are provided to list, health-check, and run verifiers; evaluate acceptance; list,
run, compare, and report benchmarks; export Inspect tasks; import SWE-bench metadata; and run
the Sprint 7 smoke path. Example verifier and benchmark configuration is fail-closed and
contains no credentials.

## Test results

- Full credential-free repository regression: 606 passed, 16 opt-in tests skipped.
- Sprint 7 verification, contract, benchmark, and persistence target: 39 passed.
- Sprint 7 smoke: generic, coding, mathematics, logic, physics, acceptance, and benchmark
  paths passed.
- CI benchmark manifest: 4/4 expected outcomes matched; seed manifest: 56/56.
- PostgreSQL verifier/controller integration: 11 passed during the Sprint 7 validation run.
- Ruff, Ruff format, mypy (204 source files), Bandit, schema drift, repository language,
  secret scan, and `git diff --check` pass.
- Locked all-extras environment: 133 packages compatible; `pip-audit` reports no known
  vulnerability.
- Source distribution, wheel installation, and editable installation pass on Python 3.12.13.

## Security status

No verifier can grant itself authority, bypass Tool Plane policy, install dependencies,
access provider secrets, make network requests by default, mutate the authoritative source
workspace, or complete a task from provider claims alone. SymPy, Z3, and Pint are isolated
behind explicit optional extras and sealed input mappings.

The vulnerable `mem0ai` 0.1.70 and LiteLLM 1.80.0 runtimes were removed from the universal
lock. Their legacy optional feature names remain empty and documented: mem0 has unresolved
advisories, while fixed LiteLLM releases require an incompatible OpenAI 2.x dependency.

## Known issues

The build emits setuptools deprecation warnings for the legacy license table and license
classifier. Builds remain successful, but the metadata must move to an SPDX license string
before the announced 2027-02-18 removal date. Inspect AI runtime execution remains deferred
for the Click security constraint described above; deterministic export is available now.

## Sprint 8 carry-over

- Implement the Python Coding Agent on top of the verifier, Tool Plane, and controller
  boundaries without weakening them.
- Add repository preparation and patch workflows as explicit, policy-controlled operations.
- Restore Inspect runtime testing only after a security-compatible upstream dependency set
  exists.
- Migrate package license metadata to the current SPDX format.

## Restore point

Branch: `feature/sprint-7-verifier-benchmarks`

Planned tag: `sprint-7-baseline`

The restore point contains the typed verifier and acceptance architecture, safe domain
verifiers, controller integration, reproducible benchmarks, external-format adapters,
schemas, CI coverage, tests, ADRs, architecture documentation, and operations runbooks.
