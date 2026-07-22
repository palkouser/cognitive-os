# Sprint 18 closure report

## Outcome and authority

Sprint 18 implementation is complete on `feature/sprint-18-harness-proposal-engine`. Cognitive OS
now has a governed Harness Proposal Engine that converts exact eligible weakness revisions into
immutable, verifier-gated proposals and a deterministic review queue. It cannot implement or apply
a proposal, mutate a source or destination subsystem, execute patches or shell commands, approve
promotion, merge, deploy, release, or train a model.

The protected PR, final `main` CI, release verification, and `sprint-18-baseline` tag remain
operator-controlled release steps and are intentionally not performed by the engine.

## Baseline and inventory

- Parent tag: `sprint-17-baseline`
- Parent commit: `e8ca551dc9697886a935687265073bd402efe06c`
- Implementation commit: the commit containing this closure report
- Parent Alembic head: `0009`
- Sprint 18 Alembic head: `0010`
- Preflight artifact: `artifacts/sprint-18/preflight/repository-inventory.json`
- Preflight SHA-256: `b33d5fe5db7b20ac5df51536821e3295a58b40393559d9879fd056eb341744bc`
- Final merge and tag SHA: pending protected review and final `main` CI

The baseline tag, prior closure report, migration head, ancestry, clean starting worktree, core
tests, and an isolated Sprint 17 backup/restore were reconciled before implementation.

## Delivered surfaces

- 15 registered proposal types, typed artifact/configuration/repository operations, immutable
  identity and revisions, exact source snapshots, benefits, minimality, risks, alternatives,
  validation, rollback, review, queue, access, statistics, verifier, and replay contracts.
- Deterministic credential-free generation, optional bounded provider prose with safe fallback,
  exact-revision lifecycle/review operations, deterministic duplicate signatures and queue order.
- 22 mandatory verifier capabilities and 10 bounded lifecycle event types.
- PostgreSQL and in-memory repositories, content-addressed Artifact Store references, event
  service, health report, exact replay, CLI, smoke path, benchmark adapter, and JSON Schemas.
- Ten `harness_proposal*` tables, nine append-only history triggers, seven controlled runtime
  functions, least-privilege grants, constraints, indexes, and compare-and-set revisions.
- Fail-closed nested configuration, a 16-case CI manifest, a 64-case seed manifest, CI jobs,
  backup/restore extensions, eight ADRs, and architecture/security/operations/benchmark guides.

## Gate I evidence

| Gate | Result |
| --- | --- |
| Required Ruff check and format | passed; 674 files formatted |
| Mypy | passed; 462 source files |
| Required core tests | 651 passed, 5 skipped |
| Full repository tests with isolated PostgreSQL | 821 passed, 11 skipped |
| Proposal-focused unit/schema/event tests | 12 passed |
| Proposal PostgreSQL persistence and health | 3 passed |
| Deterministic smoke | 15 proposal types validated; 0 destination writes |
| CI benchmark | 16/16 passed; pass rate 1.0; 0 destination writes |
| Seed benchmark | 64/64 passed; pass rate 1.0; 0 destination writes |
| Migration round trip | `0010 -> 0009 -> 0010` passed |
| Alembic schema drift | no new upgrade operations detected |
| Backup and isolated restore | passed with proposal counts, history hash, and integrity checks |
| JSON Schema drift | passed |
| Bandit | passed; no Sprint 18 finding |
| Secret scan | passed with reviewed baseline |
| Repository language | passed |
| Dependency audit | no known vulnerabilities |
| Wheel, sdist, wheel install, editable install | passed |
| Dependency lock | unchanged; no new runtime dependency |

The isolated development database discrepancy observed before implementation was not mutated: its
pre-existing experience-column drift and missing local artifact belong to that environment. A
fresh isolated database at `0009` was used for Sprint 18 migration and recovery evidence.

## External resources

EvoAgentX, GEPA, and DSPy remain conceptual pattern donors only. No donor source, runtime,
optimizer, database, credential, model, or dataset was added. Existing Pydantic, SQLAlchemy,
Alembic, asyncpg, pytest, and Hypothesis dependencies were reused; `uv.lock` is unchanged.

## Known limitations and Sprint 19 hand-off

Expected benefit remains a hypothesis. Static proposal verification does not prove that a future
candidate improves the harness, and provider assistance is not exercised by credential-free CI.
Sprint 19 may consume only an explicitly approved exact proposal revision, frozen source snapshot,
artifact hashes, passing verifier bundle, validation plan, and rollback plan in an isolated
experiment. Implementation, merge, deployment, and promotion require separate authority and must
not be inferred from `approved_for_experiment`.

No proposal was implemented, applied, or promoted during Sprint 18.
