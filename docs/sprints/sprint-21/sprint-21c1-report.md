# Sprint 21C1 report — Durable Learned Evidence

- Sprint: 21C1
- Stage gate: C1 — Durable Learned Evidence
- Gate C1 decision: **conditional pass** — see
  [gate-c1-assessment.md](gate-c1-assessment.md)
- Gate L2: **closed**

> Durable learned evidence is available, but useful learned behaviour has not yet been
> demonstrated.

## 1. Source state

| | |
|---|---|
| Required parent commit | `e9001a9338c9507a60ca43f4e3e4bee7e28ef79b` |
| Parent tag | `sprint-21-substrate-baseline` |
| Parent migration head | `0013` |
| Branch | `feature/sprint-21c1-learned-evidence` |
| Implementation pull request | [#213](https://github.com/palkouser/cognitive-os/pull/213) |
| Final implementation commit | `e5f68cd` |
| Final migration head | `0014` |
| Diff against parent | 74 files, +16012 / −841 |

The parent baseline was verified before any work started: `main`, `origin/main`, and the
local and remote peeled tag all resolved to `e9001a93…`, CI run `30209256649` succeeded on
that same commit, and the migration head was `0013`. The branch was cut from the explicit
SHA rather than from a branch name.

## 2. Delivered work

| Backlog ID | Delivered |
|---|---|
| S21C1-000..003 | Control checks, verified baseline, isolated evidence environment, read-only artifact mismatch diagnosis |
| S21C1-010..012 | `domain/learned_evidence.py` contracts, exported schemas, narrow persistence ports |
| S21C1-013 | `LearnedEvidenceService` — the one way durable learned state changes |
| S21C1-014 | `LearnedEventService` — correlation with the existing Event Store, five new payloads |
| S21C1-020..021 | In-memory reference store, shared contract suite, inert lifecycle fixture |
| S21C1-030..031 | Nine SQLAlchemy tables, migration `0014` with triggers, controlled functions and grants |
| S21C1-032..034 | PostgreSQL repository, activation concurrency and rollback, read-only health |
| S21C1-040..043 | Artifact lineage adapter, governed outcome intake, dataset manifests, quarantine review |
| S21C1-050..052 | `scripts/learned.py`, backup and restore coverage, migration and restart smoke |
| S21C1-060..064 | Contract, PostgreSQL and adversarial tests; benchmark family; early PR lane; local matrix |
| S21C1-070..072 | Configuration, operator documentation, Gate C1 assessment, this report |

### Changed surfaces

**Migration.** `0014_create_learned_evidence_store.py`: 9 tables, 8 append-only triggers,
10 controlled `SECURITY DEFINER` functions, least-privilege grants.

**Contracts.** `domain/learned_evidence.py` — 13 public contracts and 7 enums, all exported
to `schemas/v1/learned/`. Event catalogue 207 → 212.

**Services.** `application/services/learned_evidence.py`, `learned_intake.py`,
`learned_datasets.py`, `learned_quarantine.py`; `events/learned_event_service.py`.

**Infrastructure.** `infrastructure/learned/memory_repository.py`,
`learned/postgres/{tables,repository,health}.py`, `learned/artifacts.py`.

**Operations.** `scripts/learned.py`, `scripts/learned_restart_smoke.sh`,
`src/cognitive_os/learned_smoke.py`, `config/learned.example.yaml`,
`config/learned_config.py`, `docs/operations/learned-evidence.md`.

**CI.** `learned-evidence-core` gains two benchmark gates; `postgres-integration` gains the
learned smoke, health, replay and artifact verification, placed before the backup step so
the manifest has learned rows to compare.

## 3. Evidence

### 3.1 Local verification matrix

25 commands, 278 seconds, every exit status as expected. Full record in
[`evidence/sprint-21c1-local-matrix.json`](evidence/sprint-21c1-local-matrix.json).

| Command | Result |
|---|---|
| `pytest -q` (database present) | 1634 passed, 11 skipped, 113s |
| `pytest -q` (credential-free) | 1535 passed, 110 skipped, 101s |
| `pytest tests/cognitive_os/learned_evidence -q` | 201 passed |
| PostgreSQL lane (`-m postgres`) | 243 passed |
| `pytest tests/contract -q` | 65 passed |
| ruff check / format / mypy (538 files) / bandit | all clean |
| `check_repository_language.sh` | passed |
| schema drift (`--check`) | passed |
| alembic base→head, 0014→0013→0014, heads, check | all exit 0, single head, no drift |
| benchmark `sprint21c1-learned-ci` | 16 cases, 100% |
| benchmark `sprint21c1-learned-seed` | 48 cases, 100% |
| `learned.py` health / replay-verify / artifact-verify | exit 0 |
| `learned.py component-show` on a missing component | exit 3, as designed |
| `learned_restart_smoke.sh` | passed |

Skips are enumerated, not counted. The 110 credential-free skips are the PostgreSQL
suites — including the 29 learned repository and 16 learned health cases — all of which run
in the database-present row. The 11 remaining are opt-in live-provider and MCP integration
cases, none of them learned evidence.

Environment: local workstation, Python 3.12.13, PostgreSQL 18 with pgvector 0.8.2 in a
rootless container, isolated database `cognitive_os_s21c1_test`, no accelerator, zero
network or provider calls.

### 3.2 PostgreSQL health, drift, backup and restore

Health on a populated store: healthy, revision `0014`, 9 tables, 8 append-only triggers, 10
controlled functions, 1 component, 1 active, 6 revisions, replay matching, no integrity
failures. Each of the twelve checks has a test that injects one defect and asserts the
report names it.

`alembic check` is clean after a full base→head cycle and after `0014 → 0013 → 0014`.

Backup and restore carry learned counts, a content-hash roll-up and four structural checks.
The negative case was exercised: emptying the artifact archive and regenerating its
checksum makes the restore refuse with `artifact metadata references a missing regular
file`. The archive was restored and re-verified byte-for-byte afterwards.

### 3.3 Continuous integration

| Head | Wave | Result | Run |
|---|---|---|---|
| `472d1e2` | W1 | 28/28 | — |
| `39fe023` | W2 | 28/28 | 30217373849 |
| `e90d3d3` | W3 | 27/28 | 30218303435 |
| `f20d78f` | W4a | 28/28 | 30280334990 |
| `b1e2e38` | W4 | 28/28 | 30281720018 |
| `5a84bea` | W5 | 28/28 | 30282967260 |
| `e5f68cd` | W6 | 28/28 | 30284173946 |

The single non-green run is explained in §5.

## 4. Artifact mismatch handling

The development Artifact Store pair is inconsistent: all 4 declared blobs are missing from
disk and 5 files on disk have no metadata — two disjoint sets, so neither side is obviously
the recoverable one.

It was diagnosed **read-only** and left untouched, as the backlog requires. The inventory
and a non-destructive remediation proposal await operator approval:
[`evidence/sprint-21c1-artifact-mismatch-inventory.json`](evidence/sprint-21c1-artifact-mismatch-inventory.json).
All Sprint 21C1 evidence was produced on a separate, consistent, isolated pair.

One incident is worth recording because it is the same failure class. A health test seeded
artifact metadata with a fabricated hash and no bytes behind it; CI's restore verifier
caught it several steps later. The fix was S21C1-040 proper — the fixture now stores real
bytes through the real `ArtifactService`, so metadata and disk cannot diverge by
construction — rather than a test patch. The check that exists to catch this drift caught
it in the one case where we created it.

## 5. Defects found and fixed

**Three in migration `0014`, all found by writing the repository against it in wave 3.**

1. The generic `record_learned_*` functions built `($1->>'key')` expressions, which yield
   `text`. PostgreSQL refuses to assign `text` to a `uuid`, `integer` or `timestamptz`
   column, so **every ledger append would have failed at runtime** while the migration
   itself applied cleanly. Wave 1 exercised the append-only triggers but never the
   functions they protect. Replaced with `jsonb_populate_record`.
2. Four columns were `Integer` where the contract field is `bool`.
3. `register_learned_component` stored `descriptor_version` inside the revision's
   `payload_json`, so reading back the authoritative ledger failed contract validation.

`0014` was corrected in place rather than superseded: it is unmerged, exists on no deployed
database, and one correct migration is easier to reason about than a released one plus a
fix.

**One CI break, ours.** `postgres-integration` on `e90d3d3` failed at
`artifact_restore_verify.py` — the orphaned metadata described in §4. All 188 database tests
had passed; the failure was several steps later.

**One infrastructure failure, correctly not treated as a code problem.**
`postgres-integration` on `f20d78f` failed at `Initialize containers` — the pgvector service
never started, so there was no checkout and no test run. It was inspected, identified as
infrastructure, and superseded by the next push rather than worked around.

**Two environment defects, outside the repository.** The isolated environment file carried a
stale container ID and an in-container port of 55432 rather than 5432, so `pg_dump` fell
back to a socket connection as `root`. While fixing them a local test-database password
reached the terminal; both cluster roles were rotated and `.env.postgres.local` was updated
to match, since the dev and isolated environments share those roles. Neither file is
committed; both are gitignored.

## 6. Branch protection and reviewer status

`main` is protected: 27 required status checks, strict up-to-date required,
`enforce_admins` enabled, required approving reviews **not** enabled.

**The repository has one collaborator, `palkouser`, so no second eligible reviewer
exists.** The Sprint 21C1 backlog puts enabling required approving reviews out of scope
without a confirmed second reviewer. The limitation is recorded rather than worked around,
and no protection was weakened to compensate. It is carried as a residual risk in the Gate
C1 assessment.

## 7. Gate C1 and Gate L2

Gate C1: **conditional pass**. Twelve of thirteen conditions pass with linked evidence. The
thirteenth is the release sequence itself — merge, post-merge `main` CI, final evidence
update and annotated tag — which this report precedes and cannot self-referentially record.
Those handles belong in the tag annotation.

Gate L2: **closed**, and untouched by this sprint. Nothing was trained. No component is
active in any shipped configuration. The only component that reaches `ACTIVE` anywhere does
so inside an isolated test or an isolated `_test` database, and it abstains
unconditionally. `config/learned.example.yaml` declares persistence enabled, activation
disabled, no authorised actor and no active component, and the loader refuses configurations
that would quietly widen that.

## 8. Deviations

1. **Nine tables rather than the backlog's eight.** `learned_activation_approvals` is
   separate, so a refused approval stays queryable and `ck_learned_approval_human_only`
   sits on exactly the rows it governs. Pre-approved and recorded in ADR 0086.
2. **Migration `0014` corrected in place** rather than superseded by an `0015` (§5).
3. **The benchmark uses the existing runner.** The backlog permitted retaining focused
   tests if adapting the runner would require a second runner or a broad rewrite; it
   required neither.
4. **Entering `SHADOW` and `VERIFIED` produces no correlated audit event.** No existing
   event type matches exactly, and inventing one was outside the four the backlog
   authorised. The silence is declared in `STATE_EVENT_TYPES`, which health reads, so it is
   a known silence rather than an unexplained gap.

## 9. Residual risks

Carried in full in the [Gate C1 assessment §5](gate-c1-assessment.md). In short: no second
eligible reviewer; the development artifact mismatch still awaiting operator approval; the
transition policy existing in two languages (compared exhaustively); the two uncorrelated
lifecycle states; the bounded payload re-validation in health; and the risk that a
correlation warning is mistaken for corruption.

## 10. Sprint 21C2 handoff

See [sprint-21c2-handoff.md](sprint-21c2-handoff.md).
