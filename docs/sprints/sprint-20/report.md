# Sprint 20 closure report — cross-domain pilot

**Branch:** `feature/sprint-20-cross-domain-pilot`
**Parent:** `sprint-19-baseline` = `46460ad6778ddcf28d5066b95792eab6e3a2bf75` (= `main` = `origin/main`)
**Migration head:** `0012`
**Date:** 2026-07-24
**Finalized:** 2026-07-25
**Stage gate:** Gate K — General Cognitive Transfer

## Status: Gate K is closed

All 11 Gate K conditions are met. The execution path, the learning-plane path, the weakness-mining,
proposal, and controlled-change cycle, packaging, and release are all delivered, tested, and
verified. This report states what was measured and what was not built. Nothing below is projected —
every number was produced by a command in this repository or by a remote CI run linked below.

**Update after the fifth follow-up round:** gap 1 (packaging) and gap 2 (release) are both closed.
See "Packaging" and "Remote release validation" below. Gate K condition 9 and condition 11 are now
both **Met**; all 11 conditions are met and Gate K is closed.

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
| `cognitive_os` and contract tests, no optional extras | 1081 passed, 9 skipped |
| Full test suite, `mcp` + `memory-postgres` + verification extras | 1176 passed, 43 skipped |
| PostgreSQL + controller integration (`scripts/run_postgres_integration_tests.sh`) | 40 passed against PostgreSQL 18 / pgvector 0.8.2 |
| Ruff check (`src/cognitive_os`, `tests/cognitive_os`, `tests/contract`, `scripts`) | clean |
| Ruff format | clean |
| MyPy (`src/cognitive_os`) | clean, 506 source files |
| Bandit (`src/cognitive_os`, full tree) | 0 issues |
| Repository language | passed |
| CI manifest | 24/24 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Seed manifest | 120/120 cases at expected disposition (`case_pass_rate` 1.0, verified via the CLI) |
| Offline smoke | exit 0, no credentials, no network, no GPU, no extras, 28/28 governance invariants |
| Migration round trip | `0011 -> 0012 -> 0011 -> 0012` executed successfully (unchanged this round) |
| Backup / restore round trip | domain evidence backed up, restored, and verified against an isolated database; a tampered manifest field was rejected (exit 1) |
| Wheel and sdist build | built, verified (`verify_distribution.sh`, `verify_editable_install.sh`); 51/51 fixture cases accepted from the installed wheel with no optional extra present |
| Remote CI (PR #208 and post-merge on `main`) | 27/27 jobs passed on both runs, including the new `cross-domain-pilot-core` job |

`cognitive_os` and contract tests were run without any optional extra, matching what every non-`test`
CI job actually verifies. The full-repository figure was run with the `mcp` extra installed, matching
CI's `test` job exactly: this repository ships a top-level `mcp/` configuration directory
(`mcp/lightagent_mcp_settings.json`, pre-dating Sprint 0) that `pytest.ini`'s `pythonpath = .` places
ahead of the installed package on `sys.path`, so `tests/test_mcp_client_manager.py` cannot collect
when the `mcp` PyPI package is absent — a pre-existing repository characteristic, not a Sprint 20
regression, and not a combination any CI job exercises.

Baseline for comparison: the sprint started at 807 passed / 40 skipped; the previous round reported
1170 passed / 47 skipped under its own "extras absent" accounting. This round's two rows are not a
like-for-like diff against that figure — see the note above on what each row actually syncs — but
neither test-command change nor an install/uninstall difference regressed either configuration.

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
| 9 | Migration, events, CLI, health, backup, restore, packaging | **Met** — see "Operations" and "Packaging" |
| 10 | ≥24 CI and ≥120 seed cases | **Met** — 24 and 120, all at expected disposition, verified through the benchmark CLI |
| 11 | Committed, merged, post-merge validated, tagged | **Met** — see "Remote release validation" |

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

## Packaging

`uv build` produces `cognitive_os-0.1.0.dev1-py3-none-any.whl` and the matching source
distribution; `scripts/verify_distribution.sh` and `scripts/verify_editable_install.sh` both pass.
All 23 Sprint 20 modules are present in both artifacts (16 under `cognitive_os/domains/`, plus
`domain/domains.py`, `tools/domains.py`, `verification/domains.py`, `events/domain_events.py`,
`events/memory_store.py`, `benchmarks/domain_adapter.py`, and
`infrastructure/domains/postgres/health.py`), and `MANIFEST.in`'s existing `prune infra` (unchanged
this round, in place since `sprint-19-baseline`) correctly excludes the Alembic migration itself from
the wheel — a repository concern, not a runtime one.

Beyond the file-list check, the governed path was run **from the installed wheel** in a clean
virtual environment with no optional extra present: all 51 fixture cases were accepted through
`run_case_controlled`, and all 28 governance invariants in `benchmarks/domain_adapter._GOVERNANCE`
were true, matching the offline smoke gate's own result. The one thing this does **not** exercise
from the wheel is the skill and strategy transfer path, because `procedural_skills/` and
`strategies/` are repository-relative seed data (`Path("procedural_skills")`,
`Path("strategies")`), not part of the distribution — a Sprint 12/13 characteristic, unaffected by
this round, and correctly out of scope for what a wheel installs.

## CI gate for the cross-domain pilot

`benchmarks/manifests/sprint20-domain-ci.yaml` and `-seed.yaml` and `scripts/domain_smoke_test.py`
have existed since the pilot's first round, but no commit on this branch had ever added a
`cross-domain-pilot-core` job to `.github/workflows/ci.yml` — every sibling subsystem (weakness,
proposal, controlled-change, ...) shipped its own CI job in the same round it shipped its benchmark
manifests; the cross-domain pilot had not, until this round. Added a `cross-domain-pilot-core` job in
the same shape (contract and lifecycle tests, schema-drift gate, smoke gate, offline governance gate,
24-case CI gate, 120-case seed gate), plus the domain health check and smoke test as two more steps
in the existing `postgres-integration` job, matching how every other subsystem's health check and
smoke test already appear there.

Because this branch had never actually been exercised by CI before, wiring the job in surfaced two
real, pre-existing regressions that no prior round had caught:

- `scripts/skill_smoke_test.py` and `benchmarks/strategy_adapter.py` still compared the seed set to
  the literal Sprint 12/13 counts (8 skills, 7 strategies) instead of the count Sprint 20 itself grew
  it to (19 and 13). Both files already had the single-source-of-truth helper this round's own
  "Incidental repairs" (below) needed — `seed_package_paths()` and `seed_strategy_paths()` — the
  earlier magic-number cleanup simply missed these two call sites. Fixed to call the same helpers
  `skill_adapter.py`'s equivalent check already used.
- `domain/domains.py`'s `VerificationDisposition.PASS = "pass"` trips Bandit's B105 heuristic the
  same way `domain/context.py`'s `TOKEN_BUDGET` and `domain/corpus.py`'s `SECRET_DETECTED` already
  do; suppressed with the same `# nosec B105` style already used at those two call sites.

Neither regression originated in this round's own commits; both had shipped in earlier Sprint 20
rounds and were invisible until CI actually ran against this branch. Verified after the fix: the
skill smoke gate and the Sprint 13 strategy CI benchmark both exit `0`, `bandit -r src/cognitive_os`
reports zero issues, and the PR's remote CI run went from 4 failing jobs to 27/27 passing.

## Remote release validation

- Pull request [#208](https://github.com/palkouser/cognitive-os/pull/208) merged the Sprint 20
  implementation into `main` as `837405c90eeb4835de24e394fc9a14e1a94dbc8a`.
- The implementation commits are `a34ac38`, `fbdc209`, `9b12d68`, `fc51ae5`, `cda9909` (the four
  prior rounds), `ccda47c` (this round: the CI gate above), and `44d0527` (this round: the two
  regression fixes the CI gate surfaced).
- Pull-request CI run
  [30141871053](https://github.com/palkouser/cognitive-os/actions/runs/30141871053) passed all 27
  jobs against `44d0527`, including the new `cross-domain-pilot-core` job and the extended
  `postgres-integration` job. An earlier run against `ccda47c`
  ([30141686906](https://github.com/palkouser/cognitive-os/actions/runs/30141686906)) failed 4 of 27
  jobs on the two pre-existing regressions above; it is linked here rather than hidden because it is
  the evidence that the CI gate addition does what it claims — it caught a real defect on its first
  run, before merge, not after.
- Post-merge `main` CI run
  [30141958464](https://github.com/palkouser/cognitive-os/actions/runs/30141958464) passed all 27
  jobs against the merge commit. This is the authoritative remote release gate for the
  implementation.
- Tag `sprint-20-baseline` points at the merge commit `837405c90eeb4835de24e394fc9a14e1a94dbc8a` and
  is pushed to `origin`.
- `main` carries no branch-protection rule in this repository; the merge and tag were still made only
  after the pull-request CI run above was fully green, matching the gate every prior sprint's release
  applied under branch protection.

## Gaps — none remain

Both gaps this report tracked across its five rounds are closed: packaging (see "Packaging" above)
and release (see "Remote release validation" above). No further work is outstanding against Gate K
for this sprint.

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
(`EXPECTED_MIGRATION_REVISION`, previously a literal `"0011"` in ten health adapters). This cleanup
missed two more call sites still using the old literal skill and strategy counts; see "CI gate for
the cross-domain pilot" for what caught them and how they were fixed.

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

## Gate K and Sprint 21 hand-off

All 11 Gate K conditions are met and Sprint 20 is closed: `sprint-20-baseline` is published at the
merge commit, and the pull request, both remote CI runs, and the tag are linked under "Remote release
validation" above. Nothing in this sprint's scope remains open.

What Sprint 20 deliberately left for a later sprint, not because it was missed but because it was
out of scope by design (see "Scope honesty" above and the individual round sections): learning-plane
and weakness-mining evidence is not written to PostgreSQL, only the domain execution tables migration
`0012` created; the weakness-mining path has probed one capability gap, not every registered task
class; and the isolated experiment from "Weakness, proposal, and controlled change" stops at
`REQUIRES_MANUAL_REVIEW` with no self-promotion path, by the same operator-owned design as every
other controlled-change cycle in this repository.
