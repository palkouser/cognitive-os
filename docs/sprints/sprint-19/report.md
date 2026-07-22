# Sprint 19 closure report

## Outcome and authority

Sprint 19 implementation is complete on
`feature/sprint-19-controlled-change-management`. Cognitive OS now accepts only an exact,
approved Sprint 18 proposal revision, prepares an isolated experiment, captures an immutable
candidate, evaluates it against ordered regression gates, and produces either a governed
declarative promotion receipt or an operator-owned repository promotion bundle.

The runtime cannot merge, tag, publish, deploy, bypass branch protection, reuse proposal approval
as promotion approval, or promote a Tier 3 change. The protected Sprint implementation release is
an external operator-authorized repository action and is not authority granted to the controlled
change subsystem.

## Baseline and inventory

- Parent tag: `sprint-18-baseline`
- Parent and branch-point commit: `a5ea70ee434bcdedf26ea6e80a0fc1e661eddf2c`
- Implementation branch: `feature/sprint-19-controlled-change-management`
- Implementation commit: the commit containing this closure report
- Parent Alembic head: `0010`
- Sprint 19 Alembic head: `0011`
- Preflight artifact: `artifacts/sprint-19/preflight/repository-inventory.json`
- Preflight SHA-256: `bf48c294063b193c7d3414f84a4688714a9d819c5777bd65916d6b80cff2e3ff`
- Final merge, post-merge CI, and tag SHA: pending protected release workflow

Sprint 18 PR 206, its merge, post-merge CI run 29943619550, the exact baseline tag, migration
head, branch ancestry, and clean starting checkout were verified before implementation.

## Delivered surfaces

- 27 immutable public controlled-change contracts and schemas, 15 registered proposal surfaces,
  four tiers, four implementation channels, deterministic signatures, and compare-and-set
  lifecycle revisions.
- Exact read-only approved-proposal intake, active-state snapshots, detached and locked Git
  worktrees, configuration copies, database-clone identity checks, content-addressed artifact
  namespaces, and 11 mandatory isolation verifier capabilities.
- Typed implementation plans, exact deterministic transformations, reuse of the existing Coding
  Agent worktree boundary, credential-free provider scope fixtures, disabled external
  evolution authority, and immutable candidate evidence.
- An ordered 15-gate evaluation matrix, hard-failure decisions, raw regression comparisons,
  measured-benefit assessments, separate exact promotion reviews, Tier 1 destination receipts,
  Tier 0/2 repository bundles, Tier 3 manual-only enforcement, and rollback receipts.
- Fourteen versioned lifecycle events with replay, in-memory and PostgreSQL repositories, health
  diagnostics, machine-readable CLI output, smoke and benchmark paths, and backup/restore checks.
- Eleven PostgreSQL tables, ten append-only history triggers, five controlled runtime functions,
  one append-only rejection function, least-privilege grants, and migration `0011`.
- An 18-case CI manifest and a 72-case seed manifest with successful, rejected, rollback-ready,
  approval, hard-failure, and manual-review scenarios.

## Gate J evidence

| Gate | Result |
| --- | --- |
| Required Ruff check and format | passed; 697 files formatted |
| Strict MyPy | passed; 479 source files |
| Required core tests | 661 passed, 5 skipped optional scenarios |
| Full repository tests | 807 passed, 40 skipped optional/environment scenarios |
| Sprint 19 focused unit and worktree integration | 13 passed |
| PostgreSQL integration | 31 passed |
| Deterministic smoke | 15 evaluation gates; eligible; 0 active mutations; 0 release operations |
| CI benchmark | 18/18 passed; pass rate 1.0; 0 active mutations |
| Seed benchmark | 72/72 passed; 52 hard failures rejected; 4 manual reviews; 0 active mutations |
| Migration round trip | `0010 -> 0011 -> 0010 -> 0011` passed |
| Alembic schema drift | no new upgrade operations detected |
| Backup and isolated restore | passed with Sprint 19 counts and history integrity checks |
| JSON Schema drift | passed; 27 controlled-change and 14 new event schemas |
| Bandit | passed; no Sprint 19 finding |
| Secret scan | passed with reviewed hash-only schema and inventory baseline entries |
| Repository language | passed |
| Dependency audit | no known vulnerabilities |
| Wheel, sdist, wheel install, and editable install | passed |
| Dependency lock | unchanged; no new runtime dependency |

The skipped core and repository scenarios are optional external-service or environment-dependent
tests; their required PostgreSQL equivalents ran separately without skips. Live provider use is
not required for credential-free CI.

## Authority and regression evidence

- The detached-worktree integration test proves the active checkout remains unchanged and that a
  forbidden path fails before candidate capture.
- Configuration secret keys, active database identity reuse, artifact-root symlinks, dependency
  expansion, external evolution activation, stale revisions, illegal transitions, reused
  approvals, and mismatched rollback references fail closed.
- The Tier 1 fixture appends a verified declarative revision under separate approval and restores
  its exact predecessor with an immutable receipt.
- The Tier 2 fixture produces only an immutable repository bundle whose merge and release steps
  remain manual and outside runtime authority.
- The Tier 3 fixture and benchmark produce `requires_manual_review`; no automatic adapter exists.
- Security, policy, migration, performance, recovery, rollback, dependency, scope, and active-state
  failure codes cannot be overridden by a quality improvement.

## Dependencies, donors, and limitations

Existing Pydantic, SQLAlchemy, Alembic, asyncpg, pytest, and Hypothesis capabilities were reused.
OpenEvolve, GEPA, and EvoAgentX remain documented pattern donors only; no donor code, runtime,
credential path, database access, or dependency was added, and `uv.lock` is unchanged.

Local deterministic measurements are not universal capacity claims. The Claude Code role is
credential-free replay in mandatory CI; a live-provider run is optional. Repository promotion is
deliberately a bundle for an external protected workflow, not a runtime action. Database clone
creation remains host-operated around the validated identity and migration boundary.

## Sprint 20 hand-off

Sprint 20 may consume only exact immutable experiment, candidate, evaluation, comparison,
assessment, approval, promotion, rollback, event, artifact, and health evidence. It must preserve
active-state isolation, separate approvals, hard regression gates, append-only histories, Tier 3
manual authority, and the prohibition on unattended runtime merge or release.
