# ADR 0085: Coding as the fourth cross-domain domain, and the sandbox-authority boundary

- Status: Accepted
- Date: 2026-07-25
- Sprint: 21C.1
- Relates to: [ADR 0073](0073-cross-domain-tool-authority.md) (cross-domain tool authority), [ADR 0076](0076-cross-domain-governed-execution.md) (governed execution), [ADR 0084](0084-governed-skill-selection-on-the-domain-path.md) (skill selection)

## Context

Gate L v2 condition 3 — see the Sprint 22 development plan — asks for one uniform situation encoding serving four domains instead of three. The first three (mathematics, physics, logic) are headless computations: a typed input, a typed answer, no workspace. Learning substrate work so far shows they cannot produce a useful counterfactual: the deterministic rule covers them all, and there is no surface where a baseline can fail.

The fourth domain is coding, and only coding, whose baseline can fail — multi-edit pytest repair is a real task where the single-edit strategy deterministically disagrees with the golden. That measurable disagreement is the headroom signal Gate L v2 condition 8b needs. The change also closes the residual of the Gate L condition 3 (3 → 4 domains) and gives the learning substrate a second surface beyond skill selection.

This ADR records two things the plan names and that need an explicit, separate decision:

1. **The fourth domain's authority and solver boundary** — what the domain contributes and what it borrows.
2. **The sandbox boundary** — how the coding domain stays inside ADR 0073 (cross-domain tool authority) and the existing CodingSandboxMountDescriptor boundary, without weakening them.

## Decision

### The coding domain registers as the fourth `DomainKind`

`DomainKind.CODING` joins `MATHEMATICS`, `PHYSICS`, `LOGIC`. It carries no fundamental difference: it uses the same `domains.solve` tool, the same `domains.checker` verifier, the same `BoundedCognitiveController` and Tool Plane path. What it adds is the only thing that can differ between domains: the registered problem types, their solvers, and their checkers.

Three problem types:

| problem_type       | solver                   | checker                  | permitted skills |
|--------------------|--------------------------|--------------------------|------------------|
| `pytest-repair`    | `solve_pytest_repair`    | `check_pytest_repair`    | `verification-driven-python-repair`, `focused-test-execution` |
| `assertion-repair` | `solve_assertion_repair` | `check_assertion_repair` | (same) |
| `test-selection`   | `solve_test_selection`   | `check_test_selection`   | (same) |

Two permitted skills, not one, because a permitted set of size one makes selection decorative — the invariant `test_every_problem_type_offers_a_real_choice` already enforces this for every domain.

**Measured, and worth stating plainly: this does not produce a statistics tie-break.** On all 17 coding cases exactly one candidate survives preconditions (`focused-test-execution` declares the `coding.pytest` tool capability, `verification-driven-python-repair` matches on problem domain and input shape), so the selection reason is `EXACT_SIGNATURE` every time and accumulated statistics never decide. The coding domain therefore contributes **no** cold-start ties, and 21D.1's tie-break activation surface gains nothing from it. Physics remains the domain that produces genuine ties. This is a limitation of the fourth domain, not a feature of it, and 21D.1 should size its activation surface accordingly.

The two registered strategies are `python-bug-fix` and `verification-driven-repair`. Both exist in `strategies/` and both already declare exactly these two skills. The first revision of this change invented two strategy names that were not registered anywhere; they reached every coding case plan's `strategy_revisions` as provenance for strategies that did not exist, and nothing caught it because only skill names were checked. `test_each_permitted_strategy_is_a_registered_strategy` now closes that hole for all four domains.

### The registered solver is intentionally fallible, in a measurable way

`solve_pytest_repair` and `solve_assertion_repair` apply **only the first** `find/replace` patch from the case's patch list. A task that requires two coordinated edits therefore produces a candidate whose `repaired_source` disagrees with `golden_source` on string equality.

`solve_test_selection` picks tests whose identifier mentions the target function. That heuristic fails in both directions, and both are fixtures: it misses a test that exercises the target only through a helper (`test_helper_normalises_input`), and it over-selects a test that names the target without exercising it (`test_emergency_merge_bypass`).

The golden reference is withheld from the solver. `ProblemTypeEntry.checker_only_inputs` names the keys the checker alone may read (`golden_source`, `selected_tests`); `registry.solver_inputs` filters them out before the solver, before the fixture builder's ground-truth run, before the case's `knowns`, and before the Skill Engine's `failure_evidence` binding. Without that, every case would hand its own answer to whatever tried to solve it and the headroom measurement below would be worthless.

The fallibility is **measured, not assumed**, and it is measured against a declaration rather than merely observed. `FALLIBLE_CODING_CASES` names the six cases whose baseline is expected to fail; `build_all_cases` turns that into each case's `expected_disposition`; and three independent surfaces compare the declaration to the measurement — the `domain_kind_coding_registered` governance check, `test_the_coding_baseline_outcome_table_is_pinned`, and the `scenario: baseline` rows of both `sprint22-coding-*` manifests. The table, measured through `DomainPilotService`:

| problem_type | cases | accepted | rejected | rejected share |
|--------------|-------|----------|----------|----------------|
| pytest-repair | 7 | 5 | 2 | 0.29 |
| test-selection | 5 | 3 | 2 | 0.40 |
| assertion-repair | 5 | 3 | 2 | 0.40 |
| **total** | **17** | **11** | **6** | 0.35 |

Six rejected against the four the plan names as a minimum, so one fixture drifting does not put the condition on the boundary. The margin is not decoration: the first revision of this change shipped exactly four, and two of the fixtures it *documented* as fallible were not. `assertion-multi-value-and-message` carried a second patch that replaced a string with itself, so the first patch alone reached the golden; `test-selection-indirect-coverage` named its "indirect" test `test_helper_calls_validate`, which a substring match on `validate` finds. Both passed while being counted as headroom, and every gate stayed green, because nothing compared the per-case claim to the per-case measurement. That is the specific failure `FALLIBLE_CODING_CASES` exists to prevent.

The corpus-level consequence is measured too: the deterministic `requirements_available` rule falls from a perfect 1.0000 with zero confident errors to **0.9396 with 78 confident errors over 1292 evaluated examples**. That is the Gate L v2 condition 8b headroom, pinned exactly in `test_the_deterministic_rule_is_imperfect_on_this_corpus` for 21D.3 to re-run the ladder against.

### The sandbox boundary is what it already is

The actual sandbox execution — DockerSandbox.run through the CodingSandboxMountDescriptor boundary — is unchanged. ADR 0073's authority model and `CodingSandboxMountDescriptor.enforce_security_boundary` (read-only root, no network, drop all capabilities, single writable `/workspace` mount) stand.

**What this ADR does NOT add is a new sandbox path — and, stated precisely, this domain does not execute any code at all.** The 21C.1 solver is R0 and in-process; so is the checker, which compares `candidate.structured["repaired_source"]` against the case's golden reference. No pytest runs, no subprocess starts, no workspace is mounted.

That has a naming consequence the first revision of this change got wrong. The checkers originally emitted their verdicts under the capability `coding.pytest`, which everywhere else in the system (`verification/coding/commands.py`, mapped to `sandbox.pytest`) means *sandboxed pytest actually ran*. A string comparison must not report under that name; the checks are now `coding.golden_equality` and `coding.required_checks`. `coding.pytest` survives only where it is true — as a declared **tool** requirement on the case, which is what a real repair of these tasks needs and what `focused-test-execution` matches its tool precondition against. Sandboxed pytest itself remains exercised only by `tests/integration/coding/`, against the Coding Agent, not against this domain.

This is a deliberate limitation. Adding a sandbox-aware domain runner that invokes pytest against a workspace on the host would have meant:

1. extending the Tool Plane contract to take a workspace-scoped pytest handle, when the existing `CodingVerifierBundleFactory` already does it;
2. teaching the deterministic `domains.solve` tool that a coding case needs a per-run `tmp_path`, when the case is already content-addressed by its `buggy_source` and `golden_source` strings;
3. introducing a flaky (timing-dependent) probe into a gate that must close reproducibly.

So this domain compares strings deterministically and proves the baseline outcome table, under a capability name that says so. The comparison is **inside** the CheckerFn — same authority boundary as every other domain — and `tests/integration/coding/` stays authoritative for the sandbox boundary itself. What a later sprint would have to build to run real pytest here is exactly the three items above; until then, no evidence produced by this domain should be read as a test-execution result.

### The fourth domain adds nothing to governed selection or skill authority

ADR 0084's selection path treats the four domains identically: `permitted_canonical_names` is set from `entry.skills`, and that field is `(verification-driven-python-repair, focused-test-execution)` for coding cases. No new selection reason, no new exclusion reason, no new `SkillSelectionReason` value. The selector still cannot decide a coding case without going through the same registry the other three domains use.

This means Sprint 21C.1 leaves:

- the `statistics_score` plumbing untouched;
- the `CounterfactualVariation` set untouched;
- the `BaselineLadder` and out-of-distribution gates untouched.

The only thing it changes is a count (`>= 3` → `>= 4`) in `test_the_encoding_is_identical_across_every_domain`. The encoding shape stays identical; the feature schema stays one schema; the prohibited-feature list grows by nothing.

## Consequences

- Gate L v2 condition 3 closes: one uniform situation encoding serves four domains with identical shape, and a measurable baseline rejects exactly the coding cases the headroom assumption needs.
- The coding-domain manifest pair (`sprint22-coding-ci`, `sprint22-coding-seed`) becomes the entry point for downstream phases that build on it: the replacement corpora in 21D.2 and the ladder in 21D.3 read from `build_all_cases()` and pick up the 17 coding cases automatically. Both manifests run in CI alongside the sprint20 pair.
- A `scenario: baseline` case type joins `accept`/`reject` in the domain benchmark adapter. The distinction matters and the first revision of this change conflated them: `reject` injects a corrupted answer and proves acceptance refuses it, which passes for *any* case and says nothing about the baseline. `baseline` injects nothing and pins whether the registered solver succeeds. Only the second is condition 8b evidence.
- `CodingSandboxMountDescriptor` and `tools/sandbox/lifecycle.py` remain the only sandbox authority. This ADR does not introduce a second path; it reuses what's there.
- A new governance invariant (`domain_kind_coding_registered`) is registered. It runs on every sweep, compares every coding case's measured outcome to its declared `expected_disposition`, and would catch a regression that removed the fourth domain, dropped a problem type, or un-fallibled a baseline.
- `ProblemTypeEntry.checker_only_inputs` is a general mechanism, not a coding special case: any future domain whose cases carry their own ground truth can withhold it from the solver the same way.
- Fixing the `expected` key in the domain adapter had a side effect outside this domain. `expected` is a reserved matrix key routed to `expected_outputs`, and the transfer scenario was reading it from `problem_request`, where it never arrives — so `domain-ci-transfer-02`, which declares `expected: negative_transfer`, had been running the *positive* transfer experiment since Sprint 20. It now runs the negative one, and passes.

## Alternatives considered

- **Make the registered solver multi-edit and add an outer "single-edit baseline" gauge alongside it.** Rejected: it leaves two runnable solvers on one problem type and invites drift between them. A deliberately-fallible registered solver with a measured outcome table is the same fact as data, not as code.
- **Run the actual sandboxed pytest in the unit-test path.** Rejected: pytest is timing-dependent, requires Docker for the Coding Agent sandbox, and would gate a Sprint 21 closure on infrastructure that the integration suites already cover. The golden-equality checker is honest only because it does not pretend to be the real verifier — which is why it no longer borrows the real verifier's capability name.
- **Keep exactly the four fallible fixtures the plan's minimum requires.** Rejected after measuring: four is the floor, and shipping at the floor meant a single fixture defect took the evidence below it. Two did, undetected. Six with a declared table is the same claim with a margin and a tripwire.
- **Register coding as a sub-domain of one of the three existing values.** Rejected: it inverts the plan. The plan names a fourth domain so that the encoding-shape test and the situation-encoding feature schema both widen; folding coding into one of the existing three would keep both at three and the closure claim would be a lie.
