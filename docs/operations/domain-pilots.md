# Operating the cross-domain pilot

Everything below runs offline, on CPU, with no credentials and no optional extras.

## Offline smoke test

```bash
uv run python scripts/domain_smoke_test.py --output artifacts/sprint-20/evidence/domain-smoke.json
```

Exits `0` only when all three domains accept every correct answer, reject every wrong answer, all 28
governance invariants hold, both transfer experiments are positive, and the negative-transfer
fixture is rejected. The JSON report carries the registry snapshot, the unit-registry hash, per-domain
counts, per-arm transfer deltas, and which optional extras are present.

## Benchmarks

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-ci.yaml \
  --mode domain-pilot --report-directory artifacts/sprint-20/benchmarks/ci

uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-seed.yaml \
  --mode domain-pilot --report-directory artifacts/sprint-20/benchmarks/seed
```

- CI manifest: 24 cases — 6 mathematics, 6 physics, 6 logic, 6 transfer and governance.
- Seed manifest: 120 cases — 30 per domain plus 30 transfer, adversarial, and governance.

The adapter really executes each case and compares the observed disposition with the manifest
expectation, so a regression in a solver, checker, or gate fails the benchmark rather than passing a
declarative table.

## Tests

```bash
uv run pytest tests/cognitive_os/domains tests/cognitive_os/benchmarks/test_domain_adapter.py -q
```

## Running one case through the governed stack

```python
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.domains.runner import run_case_controlled   # Controller + Tool Plane
from cognitive_os.domains.skill_runner import run_case_as_skill  # + Skill Engine

case = build_all_cases()[0]
run = await run_case_controlled(case)      # run.state, run.accepted, run.event_types
skill = await run_case_as_skill(case)      # exact VERIFIED revision, Context Bundle enforced
```

`run.event_types` carries the full audit trail, including the Tool Plane
`requested/authorized/started/completed` sequence and the acceptance decision. The smoke report
prints the same evidence per domain under its `governed` key.

## Feeding a run into the learning plane

```python
from cognitive_os.domains.fixtures import build_all_cases
from cognitive_os.domains.learning import run_case_with_learning

case = build_all_cases()[0]
run, result = await run_case_with_learning(case)
# result.compilation.decision.decision   -> "completed"
# result.memory_ids                      -> 2 typed memory revisions written
# result.observation_count, .claim_count -> grounded semantic extraction
# result.corpus_item_count               -> corpus items declared to the Factory
```

This runs the case under the Controller and Tool Plane (as above), then compiles the recorded event
trail through the unmodified Experience Compiler, projects it into the Memory Plane through the
governed `MemoryService` gateway, extracts semantic observations and claims, and declares any
corpus-bound candidates to the Corpus Factory with rights taken from the case's own
`ProvenanceRef`. A wrong-answer run (pass `candidate_override=wrong_answer_for(case)`) compiles as
failure evidence — `FAILURE_PATTERN` and `NEGATIVE_EXAMPLE` candidates, `review_status="rejected"` —
never as a laundered success. See `docs/adr/0077-cross-domain-learning-plane-integration.md`.

To compile a run recorded elsewhere without re-executing it:

```python
from cognitive_os.domains.learning import compile_run

result = await compile_run(case, store)  # store: the MemoryEventStore the run wrote to
```

## Mining a real weakness, proposing a fix, and running the isolated experiment

```python
from cognitive_os.domains.weakness import mine_domain_weaknesses, confirm_domain_weakness
from cognitive_os.domains.improvement import propose_from_domain_weakness, run_isolated_experiment

mining = await mine_domain_weaknesses()      # runs the real probes, mines the real signals
# mining.signal_count, mining.weakness_count -> 3, 1

weakness = await confirm_domain_weakness()   # explicit CANDIDATE -> CONFIRMED transition
proposal = await propose_from_domain_weakness(weakness)
# proposal.proposal.status -> "approved_for_experiment"

change = await run_isolated_experiment(proposal)
# change.promotion_mode        -> PromotionMode.MANUAL_REVIEW_ONLY
# change.assessment.decision   -> PromotionDecision.REQUIRES_MANUAL_REVIEW
```

Each stage composes the unmodified Weakness Mining Service, Harness Proposal Engine, and Controlled
Change Service. The probes (`domains.weakness.IRRATIONAL_ROOT_PROBES`) are legitimate
`polynomial-equation` inputs the harness genuinely cannot solve — not fixtures rigged to fail — so
mining reads back a real recorded `tool_call.failed` and a real rejected acceptance decision. If the
underlying gap is ever fixed, `observe_probes` raises `DomainWeaknessError` rather than reporting a
stale weakness. The cycle stops at `REQUIRES_MANUAL_REVIEW`: nothing in this repository promotes a
candidate. See `docs/adr/0078-cross-domain-weakness-proposal-change.md`.

## PostgreSQL

Migration `0012` is required; the expected Alembic head is `0012`. Learning-plane and
weakness-mining output (compilations, memories, semantic observations and claims, corpus
declarations, mined signals, proposals, change experiments) stays in the same in-memory repositories
the domain execution path uses in this sprint; none of it is written to PostgreSQL. The Memory Plane,
semantic memory, Corpus Factory, weakness, proposal, and change PostgreSQL adapters already exist
from earlier sprints and are exercised by their own integration suites.

```bash
cd infra/postgres
COGOS_DATABASE_ADMIN_URL=... uv run python -m alembic upgrade head
COGOS_DATABASE_ADMIN_URL=... uv run python -m alembic current   # 0012 (head)
```

Round trip, exercised in this sprint:

```bash
uv run python -m alembic downgrade 0011
uv run python -m alembic upgrade 0012
```

Opt-in integration tests:

```bash
COGOS_DATABASE_URL=... COGOS_DATABASE_ADMIN_URL=... \
  uv run pytest tests/integration/postgres/test_domain_postgres.py -q
```

The integration database name must end in `_test`; the fixture refuses to run otherwise.

## Optional extras

The mandatory path never needs these. Install them only to exercise the optional escalation
verifiers:

```bash
uv pip install 'sympy>=1.14,<2'          # verification-math
uv pip install 'pint>=0.25.3,<0.26'      # verification-physics
uv pip install 'z3-solver>=4.16,<5'      # verification-logic
```

With all three absent the suite reports 1170 passed and 47 skipped; with all three present, 1174
passed and 43 skipped. The difference is exactly the optional escalation verifiers, which skip
cleanly rather than failing.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `UnsupportedProblemType` | task class is not registered | register it, or reject the case; do not widen a solver silently |
| `InexactError: square root is irrational` | task is outside exact rational scope | expected; the mandatory path never approximates |
| `BudgetExceededError` | a declared ceiling was crossed | raise the budget deliberately or reduce the input |
| `UnitError: incompatible units` | dimensional mismatch | fix the case; this is the check working |
| Disposition `unsupported` | a required verifier did not run | the plan requires a capability the checker never exercised |
| `RequiredContextMissingError` | declared evidence is absent from the bundle | supply the unit, assumption, or provenance record; do not relax the requirement |
| Controller state `budget_exhausted` | a declared ceiling was crossed | check `domain_budget()`; representation costs one nominal provider call |
| `SkillPolicyError` | package hash or registry snapshot mismatch | the skill revision is not the exact verified one |
| `record_domain_pilot_run` raises "different content" | immutable evidence would change | investigate; do not force the write |
| Health reports a revision mismatch | database is not at `0012` | run the migration |
| `DomainLearningError: a governed run must record events before it can be compiled` | the store passed to `compile_run` never ran a case | run the case with that same store first, or pass none and let it create one |
| `DomainLearningError: no trajectory source is declared for event ...` | the Controller emitted an event type the learning bridge does not map | a real gap — extend the source-type table in `domains/learning.py`, do not skip the event |
| `DomainWeaknessError: a probe solved an input the harness is documented not to support` | the irrational-root gap was fixed since this miner was written | the weakness is closed; update or remove the probe, do not force a stale weakness |
| `DomainWeaknessError: a proposable weakness needs at least two distinct task runs` | fewer than two probes produced a capability-gap observation | add another legitimate probe input, do not lower the threshold |
| `ProposalConflictError: maximum active proposals for weakness reached` | a second proposal was requested for the same weakness while one is still active | resolve or supersede the existing proposal first |
| Assessment `decision` is not `requires_manual_review` for a tier-3 proposal | the change-surface registry classification changed | expected only if the proposal type's tier changed; investigate before treating this as routine |
