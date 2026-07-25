# Sprint 20 closure report — cross-domain pilot

**Branch:** `feature/sprint-20-cross-domain-pilot`
**Parent:** `sprint-19-baseline` = `46460ad6778ddcf28d5066b95792eab6e3a2bf75` (= `main` = `origin/main`)
**Migration head:** `0012`
**Date:** 2026-07-24
**Stage gate:** Gate K — General Cognitive Transfer

## Status: Gate K is NOT closed

A substantial vertical slice is delivered, tested, and verified, and the execution path, the
learning-plane path, and the weakness-mining, proposal, and controlled-change cycle are all now
governed end to end. Gate K condition 8 is fully met, and the operations gap now has a CLI and
backup/restore coverage. One backlog area remains — release — and it is not a Gate K condition and
is deliberately operator-owned. This report states what was measured and what was not built. Nothing
below is projected — every number was produced by a command in this repository.

**Update after the fourth follow-up round:** gap 1 (operations — CLI extension and backup/restore
coverage) is closed. See "Operations: CLI and backup/restore" below. Release (gap 2, now the only
remaining gap) stays operator-owned by design.

**Update after the third follow-up round:** the prior gap 1 (weakness mining, proposal generation,
and the controlled-change cycle) is closed. Gate K condition 8 is now fully met. See "Weakness,
proposal, and controlled change" below.

**Update after the second follow-up round:** the prior gap 1 (learning-plane integration — Experience
Compiler, Memory Plane, semantic extraction, Corpus Factory) is closed. See "Learning-plane
integration" below.

**Update after the first follow-up round:** the original gap 1 (Controller, Context, Tool Plane, and
routing integration) is closed. Gate K condition 2 is met. See "Governed execution" below.

## Verified evidence

| Gate | Result |
|---|---|
| Test suite (extras absent) | 1170 passed, 48 skipped |
| Test suite (extras present) | 1174 passed, 44 skipped |
| PostgreSQL + controller integration | 40 passed against PostgreSQL 18 / pgvector 0.8.2 |
| Ruff check (`src/cognitive_os`, `tests/cognitive_os`, `tests/contract`, `scripts`) | clean |
| Ruff format | clean |
| MyPy (`src/cognitive_os`) | clean, 507 source files |
| Bandit (pilot, learning-plane, weakness-mining, operations) | 0 issues |
| Repository language | passed |
| CI manifest | 24/24 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Seed manifest | 120/120 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Offline smoke | exit 0, no credentials, no network, no GPU, no extras, 28/28 governance invariants |
| Migration round trip | `0011 -> 0012 -> 0011 -> 0012` executed successfully (unchanged this round) |
| Backup / restore round trip | domain evidence backed up, restored, and verified against an isolated database; a tampered manifest field was rejected (exit 1) |

Baseline for comparison: the sprint started at 807 passed / 40 skipped; the previous round closed at
1170 passed / 47 skipped (extras absent). The one additional skip in both configurations this round
is the new PostgreSQL domain-health integration test collected without `COGOS_DATABASE_URL` set.

While verifying the previous round, `scripts/benchmark_run.py --mode domain-pilot` was found to have
never been registered in the CLI's own `argparse` choices — a bug from the first round that made the
manifest commands documented in `docs/operations/domain-pilots.md` fail outright. Fixed there; both
manifests continue to run and pass through the actual CLI.

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
| 8 | Experience, memory, weakness, proposal, change flow | **Met** — see "Learning-plane integration" and "Weakness, proposal, and controlled change" |
| 9 | Migration, events, CLI, health, backup, restore, packaging | **Partial** — migration, events, CLI, health, backup, and restore met; see "Operations" and gap 1 (packaging) |
| 10 | ≥24 CI and ≥120 seed cases | **Met** — 24 and 120, all at expected disposition, verified through the benchmark CLI |
| 11 | Committed, merged, post-merge validated, tagged | **Not met** — see gap 2 (release) |

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

`domains/learning.py` translates a governed run's recorded event trail into the inputs the existing
services already accept — it contributes no compilation logic, no memory policy decision, no
grounding logic, and no corpus routing decision.

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

Three governance invariants — `learning_recorded_events_only`, `learning_failure_preserved`,
`learning_corpus_rights` — run in the seed benchmark manifest and as parametrised tests.

**One honest note.** Learning-plane output is written to the same in-memory repositories the domain
execution path already uses: the mandatory path stays offline and credential-free. The Memory Plane,
semantic memory, and Corpus Factory PostgreSQL adapters already exist from earlier sprints and are
exercised by their own integration suites; wiring domain learning output into them was out of scope.
See `docs/adr/0077-cross-domain-learning-plane-integration.md`.

While implementing this, a real bug was found and fixed in `domains/runner.py`: `store = store or
MemoryEventStore()` discarded any caller-supplied *empty* store, because `MemoryEventStore.__len__`
makes an empty store falsy, and `or` silently substituted a private store the caller could never read
from. Without this fix the learning bridge would have compiled zero events from every governed run.
Fixed to check `is None`.

## Weakness, proposal, and controlled change

Gate K condition 8 is now fully met. `domains/weakness.py` and `domains/improvement.py` compose the
unmodified Weakness Mining Service, Harness Proposal Engine, and Controlled Change Service over a
real cross-domain capability gap — they contribute probes and evidence adapters, nothing else.

**The weakness is real, not staged.** `polynomial-equation` is a registered task class that accepts
any real quadratic; the solver is exact-rational only (a declared scope limit, not a defect), so a
quadratic with irrational roots — `x^2 - 2 = 0`, `x^2 - 3 = 0`, `x^2 - 5 = 0` — is admitted at
planning time and genuinely fails at solve time. Each probe runs through the identical governed
Controller and Tool Plane path every fixture case uses and fails there for real, producing a recorded
`tool_call.failed` and a rejected acceptance decision.

| Stage | Owner | Result |
|---|---|---|
| Mining | `WeaknessMiningService` (unmodified) | 3 recorded failures group into 1 weakness signature, `MISSING_SKILL` |
| Confirmation | explicit operator transition | `CANDIDATE -> CONFIRMED`, `reproducible` |
| Proposal | `HarnessProposalService` (unmodified) | `TOOL_DEFINITION_CHANGE`, reaches `approved_for_experiment`, no provider consulted |
| Isolated experiment | `ControlledChangeService` (unmodified) | `declarative_copy` isolation, network disabled, 1 file in scope, 15 evaluation gates, 0 hard failures |
| Assessment | Change Surface Registry (tier 3) | `requires_manual_review` — no runtime promotion authority |

The full cycle is deterministic: two independent runs of mining, and of the proposal-through-experiment
chain, produce identical manifests and byte-identical experiment, isolation, and assessment content
hashes. This required a deliberate identity choice — `ProbeObservation.observation_hash` excludes each
run's real event-payload hashes, because those carry a fresh acceptance `decision_id` and timestamp on
every execution, and a weakness is a property of the harness, not of one run. Every mined signal still
cites its own real `task_run_id`.

Three governance invariants — `weakness_from_recorded_failure`, `proposal_traces_to_weakness`,
`change_cannot_self_promote` — run in the seed benchmark manifest and as parametrised tests, bringing
the pilot's total to **28**, all passing. See
`docs/adr/0078-cross-domain-weakness-proposal-change.md`.

**Two shared-component bugs, found because these probes are the pilot's first genuine tool-layer
failures.** Every prior fixture either fully succeeded or was rejected only at verification; nothing
before this made the Tool Plane itself fail.

1. `DomainActionExecutor.execute` let a `ToolPlaneError` from a failing tool call propagate past the
   Controller instead of returning a failed `ActionOutcome`. The Tool Plane had already recorded
   `tool_call.failed` and re-raised by contract; the domain executor's job is to report that as an
   outcome, not let it crash the run. Before the fix, a genuinely failing tool aborted the entire
   governed run with an unhandled traceback — no execution-step failure, no verifier result, no
   acceptance decision, and no audit trail for what happened. Fixed by catching `ToolPlaneError` and
   returning `ActionOutcome(succeeded=False, ...)`.
2. The shared `ControllerVerificationService._subject` — used by every Controller-driven acceptance
   check, not domain-specific — built an invalid `VerificationSubject` when the step under
   verification produced no output: `inline_value=None` with no other subject source, which the
   contract's own validator rejects. This aborted the run one layer later, after the first fix. Fixed
   by stating absence explicitly (`{"subject_absent": true}`); `domains.checker` now classifies that
   as `UNVERIFIABLE` rather than `FAILED`, because a verifier that never saw a candidate answer has
   not refuted one.

Both fixes are in shared Controller and Tool Plane code, not worked around inside the domain package,
and both are covered by a regression test
(`test_a_failing_tool_still_records_a_full_audit_trail`).

## Operations: CLI and backup/restore

`scripts/domain.py` is a new operator CLI, matching every sibling subsystem's own script
(`scripts/weakness.py`, `scripts/experience.py`, `scripts/proposal.py`, `scripts/change.py`, and the
rest) — there is no single top-level CLI in this repository to extend; each subsystem already ships
its own. Seven actions, each a thin call into an existing composition function and each printing one
JSON object: `run`, `run-skill`, `learn`, `mine`, `propose`, `experiment`, `health` (offline by
default, `--database` for a read-only PostgreSQL check).

`src/cognitive_os/infrastructure/domains/postgres/health.py` adds `PostgresDomainHealthService`,
matching `PostgresWeaknessHealthService`'s shape: table, trigger, and controlled-function counts,
plus three read-only checks (evidence rows without a parent run, transfer results without an
experiment, and any row violating the hard-gate-versus-positive-transfer constraint). Verified
against the live database: `healthy: true`, 7 tables, 6 append-only triggers, 3 controlled functions,
zero violations.

`scripts/backup_event_store.sh` and `scripts/restore_event_store.sh` gain `domain_counts` and
`domain_history_sha256`, following the exact pattern the weakness, proposal, and controlled-change
additions from earlier sprints already established in these two scripts; restore additionally
computes `domain_integrity` and folds it into the script's final gate. Verified against an isolated
database rather than the shared development database (whose artifact store has a pre-existing,
unrelated metadata-versus-filesystem inconsistency that predates this session): a full backup and
restore round trip with one recorded `domain_pilot_runs` row reproduced the row exactly and matched
both new manifest fields, and a backup manifest with a deliberately corrupted `domain_counts` value
was rejected by the restore script with exit `1`. See
`docs/adr/0079-cross-domain-operations-cli-and-backup.md`.

**One honest note.** Wheel/sdist packaging (S20-064) was not part of this round — it was not
requested and remains open. Learning-plane and weakness-mining evidence still is not written to
PostgreSQL; this round adds coverage only for the domain execution tables migration `0012` already
created, and creates no new tables.

**One caught-before-it-shipped mistake.** A first attempt at inserting the new backup-script query
between two existing lines accidentally dropped a union clause from the unrelated
`change_history_sha256` query, silently narrowing what it covered. Caught by diffing the edited line
against the untouched copy of the identical query in `restore_event_store.sh` before running either
script, and corrected before any backup ran against real data.

## Gaps — what was not built

**1. Packaging (S20-064 partial).**
Extras were verified to install and uninstall independently and the core was confirmed to work
without them, but no wheel or sdist was built. Not part of this round's scope.

**2. Release (S20-066).**
Nothing has been committed, pushed, reviewed, merged, or tagged. `sprint-20-baseline` does not
exist. The runtime holds no release authority by design — the pilot package imports no process or
network module, verified structurally, and the controlled-change cycle stops at manual review with no
self-promotion path — so this step is operator-owned and deliberately outside what was executed here.

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
- The weakness-mining path probes one capability gap. Finding it demonstrates that mining, proposal
  generation, and the controlled-change cycle accept real domain evidence end to end; it does not
  imply every registered task class has been probed for its own edge cases.

## Incidental repairs

Three magic numbers were duplicated across the repository and would have needed editing every
sprint. Each was replaced with a single source of truth: the seed skill count (`seed_package_paths`),
the seed strategy count (`seed_strategy_paths`), and the expected Alembic head
(`EXPECTED_MIGRATION_REVISION`, previously a literal `"0011"` in ten health adapters).

The benchmark matrix expander now forwards adapter-specific keys through `problem_request`. No
existing manifest uses a non-reserved key, so sprints 7 to 19 expand byte-identically.

Previous round: `scripts/benchmark_run.py --mode domain-pilot` became a registered CLI choice, and
`MemoryEventStore` gained a `stored_events()` accessor so a caller can replay a run's full envelopes
rather than only its event-type names.

Previous round: two shared Controller and Tool Plane defects were fixed rather than worked around —
see "Weakness, proposal, and controlled change" for `DomainActionExecutor.execute` and
`ControllerVerificationService._subject`. Both are shared code, used by every Controller-driven run
in the repository, not domain-specific.

This round: none of the pre-existing backup/restore query text for weakness, proposal, or
controlled-change evidence was altered — a mistake that briefly did alter one was caught by diffing
before either script ran; see "Operations: CLI and backup/restore".

## Recommended next step

Gate K condition 8 is fully met and operations now has a CLI and backup/restore coverage; the
remaining gaps are packaging (gap 1) and release (gap 2), neither a Gate K condition. Packaging is a
short, self-contained step (`uv build` and a smoke-test of the built wheel). Release remains
operator-owned by design regardless of ordering — the runtime holds no merge, tag, or push authority
structurally, and the controlled-change cycle stops at manual review with no self-promotion path.
