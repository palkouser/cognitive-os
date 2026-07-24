# Sprint 20 closure report — cross-domain pilot

**Branch:** `feature/sprint-20-cross-domain-pilot`
**Parent:** `sprint-19-baseline` = `46460ad6778ddcf28d5066b95792eab6e3a2bf75` (= `main` = `origin/main`)
**Migration head:** `0012`
**Date:** 2026-07-24
**Stage gate:** Gate K — General Cognitive Transfer

## Status: Gate K is NOT closed

A substantial vertical slice is delivered, tested, and verified. Five backlog areas are **not**
implemented, and three of them are Gate K conditions. This report states what was measured and what
was not built. Nothing below is projected — every number was produced by a command in this
repository.

## Verified evidence

| Gate | Result |
|---|---|
| Test suite (extras absent) | 997 passed, 47 skipped |
| Test suite (extras present) | 1001 passed, 43 skipped |
| PostgreSQL integration | 38 passed against PostgreSQL 18 / pgvector 0.8.2 |
| Ruff check | 1 pre-existing error, unchanged from baseline |
| Ruff format | clean |
| MyPy | clean, 494 source files |
| Bandit (pilot package) | 0 issues |
| Repository language | passed |
| CI manifest | 24/24 cases at expected disposition |
| Seed manifest | 120/120 cases at expected disposition |
| Offline smoke | exit 0, no credentials, no network, no GPU, no extras |
| Migration round trip | `0011 -> 0012 -> 0011 -> 0012` executed successfully |

Baseline for comparison: the sprint started at 807 passed / 40 skipped.

## Measured pilot results

51 deterministic fixture cases across 25 registered problem types (9 mathematics, 8 physics,
8 logic):

| Domain | Cases | Correct answers accepted | Wrong answers rejected |
|---|---|---|---|
| Mathematics | 18 | 18 | 18 |
| Physics | 17 | 17 | 17 |
| Logic | 16 | 16 | 16 |

Verification is discriminating in both directions, which is the point: the same path that accepts a
correct answer rejects a deliberately wrong one.

## Measured transfer results

| Arm | Mathematics → physics (skill) | Mathematics → logic (strategy) |
|---|---|---|
| Target baseline | 0.647 | 0.625 |
| No-skill control | 0.647 | 0.625 |
| Unchanged source revision | 1.000 | 1.000 |
| Minimally adapted | 1.000 | 1.000 |
| Domain-specific | 1.000 | 1.000 |
| Source retention | 1.000 | 1.000 |
| Unrelated domain | 1.000 | 1.000 |
| **Target delta** | **+0.353** | **+0.375** |
| Hard gates breached | none | none |
| Disposition | `positive_transfer` | `positive_transfer` |

The narrow-optimisation fixture is rejected as `negative_transfer` on the cost-ratio gates.

**What the transfer claim does and does not mean.** The transferred component is
verification-driven repair — a real, measurable procedure, not a label. Its declared limitations
are recorded in every `TransferResult`: it is not a general skill; faults are injected
deterministically rather than drawn from live traffic; and a single seeded run carries no
confidence interval. Cost is modelled from tool calls rather than timed, because a hard gate that
reads a wall clock is not reproducible — this was found in practice when a busy machine flipped a
disposition, and it was fixed rather than papered over.

## Gate K conditions

| # | Condition | Status |
|---|---|---|
| 1 | Immutable typed contracts | **Met** — 15 contracts, JSON Schemas exported and drift-gated |
| 2 | Controller-owned plans, Tool Plane-mediated tools | **Not met** — see gap 1 |
| 3 | No raw evaluation or unbounded solver path | **Met** — Sprint 7 parser reused, no `eval`/`exec`, budgets enforced |
| 4 | Deterministic verifier coverage | **Met** for the registered scope |
| 5 | Skills and strategies via existing registries | **Met** — 11 skills, 6 strategies reach `VERIFIED` |
| 6 | Positive skill and strategy transfer | **Met** — measured above |
| 7 | Source-retention and negative-transfer gates | **Met** — enforced in contract and in the database |
| 8 | Experience, memory, weakness, proposal, change flow | **Not met** — see gaps 2 and 3 |
| 9 | Migration, events, CLI, health, backup, restore, packaging | **Partial** — see gap 4 |
| 10 | ≥24 CI and ≥120 seed cases | **Met** — 24 and 120, all at expected disposition |
| 11 | Committed, merged, post-merge validated, tagged | **Not met** — see gap 5 |

## Gaps — what was not built

**1. Controller, Context, Tool Plane, and routing integration (S20-040 to S20-044).**
`DomainPilotService` is its own orchestrator. It does not map `DomainProblem` onto
`ProblemRepresentation`, does not drive the Cognitive Controller state machine, does not build
Context Bundles, does not register the domain kernels as Tool Plane tools, and does not use the
Skill Engine to *execute* the skills it registers. The skills and strategies are registered and
verified through the real engines, but the pilot invokes solvers directly. Gate K condition 2 is
therefore not satisfied, and this is the largest remaining item.

**2. Learning-plane integration (S20-045, S20-046).**
Domain trajectories are not compiled by the Experience Compiler and no domain evidence is written
to the Memory Plane, semantic memory, or the Corpus Factory. Evidence currently terminates in the
`domains` repository and migration `0012` tables.

**3. Weakness, proposal, and controlled-change cycle (S20-052, S20-053, S20-054).**
No domain weakness fixtures were mined, no `HarnessProposal` was generated from a domain weakness,
and no approved isolated change experiment was run. This is a Gate K condition and a complete
epic.

**4. Operations (S20-059 partial, S20-060, S20-064 partial).**
An offline smoke script exists and is machine-readable, but the main CLI was not extended with
domain subcommands. Backup, isolated restore, and recovery were not extended to cover Sprint 20
artefacts. Extras were verified to install and uninstall independently and the core was confirmed
to work without them, but no wheel or sdist was built.

**5. Release (S20-066).**
Nothing has been committed, pushed, reviewed, merged, or tagged. `sprint-20-baseline` does not
exist. The runtime holds no release authority by design — the pilot package imports no process or
network module, verified structurally — so this step is operator-owned and deliberately outside
what was executed here.

## Scope honesty

The delivered scope is narrow on purpose:

- Exact rational arithmetic only; irrational results raise rather than being approximated.
- Quadratics over the rationals; irrational roots are out of scope and reported as such.
- Algebraic equivalence is evidenced by exact evaluation at sampled points — evidence, not a proof
  of identity, and the check says so in its own detail text.
- Sequence induction searches a small transparent rule space; absence there is not absence in
  general, and underdetermination is reported whenever fitting rules disagree.
- Propositional logic only.
- SymPy, Pint, and Z3 remain optional escalation paths; the mandatory path uses none of them.

## Incidental repairs

Three magic numbers were duplicated across the repository and would have needed editing every
sprint. Each was replaced with a single source of truth: the seed skill count (`seed_package_paths`),
the seed strategy count (`seed_strategy_paths`), and the expected Alembic head
(`EXPECTED_MIGRATION_REVISION`, previously a literal `"0011"` in ten health adapters).

The benchmark matrix expander now forwards adapter-specific keys through `problem_request`. No
existing manifest uses a non-reserved key, so sprints 7 to 19 expand byte-identically.

## Recommended next step

Close gap 1 first. Controller and Tool Plane integration is a Gate K condition, and gaps 2 and 3
depend on domain trajectories flowing through the real execution path before the Experience
Compiler and Weakness Mining have anything authentic to consume.
