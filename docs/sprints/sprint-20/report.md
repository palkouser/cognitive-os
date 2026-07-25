# Sprint 20 closure report — cross-domain pilot

**Branch:** `feature/sprint-20-cross-domain-pilot`
**Parent:** `sprint-19-baseline` = `46460ad6778ddcf28d5066b95792eab6e3a2bf75` (= `main` = `origin/main`)
**Migration head:** `0012`
**Date:** 2026-07-24
**Stage gate:** Gate K — General Cognitive Transfer

## Status: Gate K is NOT closed

A substantial vertical slice is delivered, tested, and verified, and both the execution path and the
learning-plane path are now governed end to end. Two backlog areas remain **not** implemented, and one
of them is a Gate K condition. This report states what was measured and what was not built. Nothing
below is projected — every number was produced by a command in this repository.

**Update after the second follow-up round:** gap 1 (learning-plane integration — Experience Compiler,
Memory Plane, semantic extraction, Corpus Factory) is closed. Gate K condition 8 is now partially met.
See "Learning-plane integration" below.

**Update after the first follow-up round:** the prior gap 1 (Controller, Context, Tool Plane, and
routing integration) is closed. Gate K condition 2 is met. See "Governed execution" below.

## Verified evidence

| Gate | Result |
|---|---|
| Test suite (extras absent) | 1150 passed, 47 skipped |
| Test suite (extras present) | 1154 passed, 43 skipped |
| PostgreSQL + controller integration | 39 passed against PostgreSQL 18 / pgvector 0.8.2 |
| Ruff check (`src/cognitive_os`, `tests/cognitive_os`, `tests/contract`, `scripts`) | clean |
| Ruff format | clean |
| MyPy (`src/cognitive_os`) | clean, 503 source files |
| Bandit (pilot + learning-plane bridge) | 0 issues |
| Repository language | passed |
| CI manifest | 24/24 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Seed manifest | 120/120 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Offline smoke | exit 0, no credentials, no network, no GPU, no extras, 25/25 governance invariants |
| Migration round trip | `0011 -> 0012 -> 0011 -> 0012` executed successfully (unchanged this round) |

Baseline for comparison: the sprint started at 807 passed / 40 skipped; the previous round closed at
1130 passed / 47 skipped (extras absent).

While verifying this round, `scripts/benchmark_run.py --mode domain-pilot` was found to have never
been registered in the CLI's own `argparse` choices — a bug from the first round that made the
manifest commands documented in `docs/operations/domain-pilots.md` fail outright. The `elif` branch
that executes it existed; only the choice list was missing. Fixed alongside this round's changes; both
manifests now run and pass through the actual CLI, not only through the adapter test that had been
silently carrying the "24/24" and "120/120" claims.

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
| 2 | Controller-owned plans, Tool Plane-mediated tools | **Met** — see "Governed execution" |
| 3 | No raw evaluation or unbounded solver path | **Met** — Sprint 7 parser reused, no `eval`/`exec`, budgets enforced |
| 4 | Deterministic verifier coverage | **Met** for the registered scope |
| 5 | Skills and strategies via existing registries | **Met** — 11 skills, 6 strategies reach `VERIFIED` |
| 6 | Positive skill and strategy transfer | **Met** — measured above |
| 7 | Source-retention and negative-transfer gates | **Met** — enforced in contract and in the database |
| 8 | Experience, memory, weakness, proposal, change flow | **Partial** — experience, memory, semantic, and corpus stages met; see "Learning-plane integration" and gap 1 |
| 9 | Migration, events, CLI, health, backup, restore, packaging | **Partial** — see gap 2 |
| 10 | ≥24 CI and ≥120 seed cases | **Met** — 24 and 120, all at expected disposition, verified through the benchmark CLI |
| 11 | Committed, merged, post-merge validated, tagged | **Not met** — see gap 3 |

## Governed execution

Gate K condition 2 is met. The execution path now belongs to the services that already own it; the
domain package contributes a solver and a checker and borrows every authority.

| Concern | Owner | Domain contribution |
|---|---|---|
| Problem representation | Cognitive Controller | a `ProblemRepresentationPort` |
| Planning, budgets, state machine | Cognitive Controller | a `PlanningPort` emitting one TOOL action |
| Tool authorisation, audit, timeout | Tool Plane | registers `domains.solve` (R0, deterministic) |
| Verification | Verifier Registry | registers `domains.checker` |
| Acceptance | Acceptance Service | none |
| Skill lifecycle | Skill Engine | a runner and a context request factory |
| Context assembly | Context Builder | required-evidence candidates |
| Routing | Model Capability Registry | a canonical `TaskSignature` |

Measured over all 51 fixture cases:

| Path | Correct answers accepted | Wrong answers rejected |
|---|---|---|
| Cognitive Controller + Tool Plane | 51/51 | 51/51 |
| Skill Engine (exact `VERIFIED` revision) | 51/51 | 51/51 |

Each run produces the full audit trail — `problem.representation_created`, `plan.created`,
`tool_call.requested/authorized/started/completed`, two `verifier.completed`, and
`controller.acceptance_decision_recorded` — with the acceptance decision strictly after the tool
result. A wrong answer travels the identical plan, tool call, and acceptance path, which is what
makes it detectable rather than trusted.

Six governance invariants run in both benchmark manifests and as parametrised tests:
`controller_owns_plan`, `tool_plane_audits_solve`, `controlled_path_rejects_wrong`,
`required_context_enforced`, `skill_engine_verified_only`, `routing_signature_tool_only`.

**Two honest notes.** The Controller charges one *nominal* provider call for problem representation
because that step is normally a model call; `DomainProblemEngine` is deterministic and contacts no
provider. That entry is the Controller's accounting and was not overridden — the domain budget
allows for it, and no provider is configured, so a real model call cannot occur. Separately, the
Context Builder cannot detect an item a retriever never offered, which no retrieval system can;
`assert_required_context` closes that gap where the requirement is declared, and omitting a required
unit, assumption, or provenance record raises.

`DomainPilotService` remains as the direct verification composer behind the transfer experiments,
where running nine full Controller arms per experiment would add ceremony without changing what is
measured. It is no longer the case-execution path.

## Learning-plane integration

Gate K condition 8 is now partially met: the experience, memory, semantic, and corpus stages are
delivered; weakness mining and the controlled-change cycle are not (gap 1, below). `domains/learning.py`
translates a governed run's recorded event trail into the inputs the existing services already accept
— it contributes no compilation logic, no memory policy decision, no grounding logic, and no corpus
routing decision.

| Concern | Owner | Domain contribution |
|---|---|---|
| Trajectory compilation | `ExperienceCompiler` (unmodified) | `build_compilation` groups recorded events into trajectory sources |
| Memory write | `MemoryService` (governed gateway) | `project_run` projects 2 typed contents; `domain_memory_policy()` grants only those types and `DOMAIN`/`TASK` scope |
| Semantic extraction | `SemanticExtractionService` (unmodified) | reuses the existing typed-memory extractors, no domain-specific extractor added |
| Corpus declaration | `CorpusFactory` (unmodified) | `corpus_request` derives usage rights from the case's own `ProvenanceRef` |

Measured over all 51 fixture cases, both directions:

| Path | Compilation decision | Terminal state | Memories | Observations / claims | Corpus items |
|---|---|---|---|---|---|
| Accepted run | `completed`, 51/51 | `accepted` | 2/run | 4 / 4 | ≥1 |
| Wrong-answer run | `completed`, 51/51 | `rejected` | 2/run | 4 / 4 | ≥2 (adds a negative example) |

Every `TimelineEntry` the compiler consumes carries the originating event's own `event_id` as its
identity and the event's own `payload_hash` as its evidence — nothing is synthesised, and an event
type outside the declared source-type table raises instead of being filed as `unknown`. A rejected
run is not laundered into success: its terminal state stays `"rejected"`, it produces
`FAILURE_PATTERN` and `NEGATIVE_EXAMPLE` candidates instead of `MEMORY` and `SKILL` candidates, and
the projected memory's `review_status` reads `"rejected"`.

Three new governance invariants — `learning_recorded_events_only`, `learning_failure_preserved`,
`learning_corpus_rights` — run in the seed benchmark manifest and as parametrised tests, bringing the
pilot's total to **25**, all passing.

**One honest note.** Learning-plane output is written to the same in-memory repositories the domain
execution path already uses, matching gap 1's precedent from the first round: the mandatory path
stays offline and credential-free. The Memory Plane, semantic memory, and Corpus Factory PostgreSQL
adapters already exist from earlier sprints and are exercised by their own integration suites; wiring
domain learning output into them was out of scope for this round. See `docs/adr/0077-cross-domain-learning-plane-integration.md`.

While implementing this, a real bug was found and fixed in `domains/runner.py`: `store = store or
MemoryEventStore()` discarded any caller-supplied *empty* store, because `MemoryEventStore.__len__`
makes an empty store falsy, and `or` silently substituted a private store the caller could never read
from. Without this fix the learning bridge would have compiled zero events from every governed run.
Fixed to check `is None`.

## Gaps — what was not built

**1. Weakness, proposal, and controlled-change cycle (S20-052, S20-053, S20-054).**
No domain weakness fixtures were mined, no `HarnessProposal` was generated from a domain weakness,
and no approved isolated change experiment was run. This is the remainder of Gate K condition 8 and
a complete epic. Domain trajectories now flow through the real Controller, Tool Plane, and Experience
Compiler, so weakness mining finally has authentic compiled material to consume — which was the
blocker that made this the right order.

**2. Operations (S20-059 partial, S20-060, S20-064 partial).**
An offline smoke script exists and is machine-readable, but the main CLI was not extended with
domain subcommands. Backup, isolated restore, and recovery were not extended to cover Sprint 20
artefacts. Extras were verified to install and uninstall independently and the core was confirmed
to work without them, but no wheel or sdist was built.

**3. Release (S20-066).**
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

This round: `scripts/benchmark_run.py --mode domain-pilot` is now a registered CLI choice (see
"Verified evidence"), and `MemoryEventStore` gained a `stored_events()` accessor so a caller can
replay a run's full envelopes rather than only its event-type names.

## Recommended next step

Close the weakness-mining and controlled-change gap next (gap 1). Domain trajectories now compile
through the real Experience Compiler with real candidates, so Weakness Mining and the
`HarnessProposal` flow finally have authentic compiled material to consume — which was the blocker
that made this the right order.
