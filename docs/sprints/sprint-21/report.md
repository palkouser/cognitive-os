# Sprint 21 — Learning Substrate Release Report

**Sprint:** 21R — Learning Substrate Reconciliation and Protected Release
**Stage gate:** R0 — Protected Learning Substrate Baseline
**Backlog:** [Sprint 21R technical backlog](sprint-21r-technical-backlog.md)
**Gate assessment:** [Sprint 21 Gate L assessment](gate-l-assessment.md), revision 2
**Forward plan:** [Sprint 22 development plan](../sprint-22/development-plan.md),
[execution sprint allocation](../sprint-22/execution-sprint-allocation.md)
**Report date:** 2026-07-26
**Document status:** release evidence — pending fields are marked `PENDING` and are
filled by S21R-014 after the implementation merge

Every number in this report was produced by a command in this repository on the release
candidate. Commands and artifact paths are named so each claim can be re-run. Where a
required scenario could not run, it says so instead of appearing green.

---

## 1. Release state

| Item | Value |
|---|---|
| Repository | `palkouser/cognitive-os` |
| Active branch | `feature/sprint-21a-learning-substrate` |
| Parent `main` / `origin/main` at assessment | `c8557389f8bd1e763098125176f1321b2fc765a8` |
| Merge base | `c8557389f8bd1e763098125176f1321b2fc765a8` |
| Divergence at assessment | 0 behind, 4 ahead |
| Last implementation tag | `sprint-20-baseline`, tag object `c588a950c61da8bacebb7eaf2ed6f8e2d6f8e779`, peeled `837405c90eeb4835de24e394fc9a14e1a94dbc8a` (local and remote agree) |
| Migration head | `0013_create_approximate_vector_indexes` — unchanged by Sprint 21R |
| Latest `main` CI before release | run `30142384838`, conclusion `success` |
| Branch CI runs before release | none — `ci.yml` triggers on push to `main` and on `pull_request` only, so a feature-branch push produces no run by design |
| Release candidate head | `PENDING` (S21R-011) |
| Implementation PR | `PENDING` (S21R-012) |
| Implementation merge SHA | `PENDING` (S21R-013) |
| First post-merge `main` CI | `PENDING` (S21R-014) |
| Release-evidence PR | `PENDING` (S21R-014) |
| Final post-merge `main` CI | `PENDING` (S21R-014) |
| Annotated tag `sprint-21-substrate-baseline` | `PENDING` (S21R-015) |

Freeze artifact: `artifacts/sprint-21/preflight/state-freeze.json`.

### 1.1 Implementation commits inherited by this release

```text
d8c489c feat(learning): Sprint 21A learning substrate — self-play labelling,
        invariance gate, forgetting gate, measured ANN capacity
fcea853 feat(learning): Sprint 21B — baseline ladder, promotion gate, Gate L no-go
cec0dc0 feat(domains,skills): bind governed selection to the domain path,
        feed statistics, settle the useful label
fe26644 feat(domains): coding as the fourth domain, with the headroom evidence pinned
```

All four remain ancestors of the release candidate. No history was rewritten and no
force push was used.

### 1.2 Change inventory

132 files against `main`: 13,767 insertions, 971 deletions; 71 added, 61 modified.
Every file is categorised, with zero unclassified:

| Category | Files |
|---|---:|
| schema / event contracts | 43 |
| test | 18 |
| learning algorithm | 16 |
| domain contract | 14 |
| documentation | 14 |
| memory | 7 |
| PostgreSQL infrastructure | 7 |
| benchmark | 3 |
| CI / security | 3 |
| configuration | 2 |
| migration | 2 |
| operations | 2 |
| repository instructions | 1 |

Artifacts: `artifacts/sprint-21/preflight/change-inventory.json`,
`artifacts/sprint-21/preflight/sensitive-file-review.json`.

### 1.3 Sensitive-file review

Nine sensitive surfaces reviewed individually; all pass, with zero blocking findings.

- **`.github/workflows/ci.yml`** — 27 jobs on `main`, 27 on the candidate. Zero jobs
  removed, zero added. The only step delta is two *added* steps in
  `cross-domain-pilot-core` for the coding manifests. The Ruff steps widen scope from
  `src/cognitive_os tests/cognitive_os tests/contract scripts` to
  `src tests scripts infra`, a strict superset. No Sprint 20 regression job suppressed.
- **`.pre-commit-config.yaml`** — the same widening, keeping the hook and CI in step.
  The `detect-secrets` hook is unchanged.
- **`.secrets.baseline`** — content-level delta, ignoring line numbers: 46 fingerprints
  added, 11 removed, **every one of type `Hex High Entropy String`**. Zero
  `Secret Keyword` and zero `Basic Auth Credentials` fingerprints added. Two files added
  to the baseline (`envelope_1e5.json`, `envelope_1e5_clustered.json`), zero removed. The
  42 additions and 11 removals under `schemas/manifest.json` are schema content digests
  the exporter produced; the 4 under the envelopes are `content_hash` sha256 fields,
  inspected directly. No fingerprint suppresses a live credential.
- **`AGENTS.md`** — only the required-checks lint command list plus a paragraph on the
  first-party scope and the donor-code exclusion. English only.
- **Migration `0013`** — `revision='0013'`, `down_revision='0012'`, follows the exact
  prior head. Creates no table and no role, so no new grant is required.
- **Migration `0008`** — whitespace-only reflow inside a trigger-function SQL literal,
  verified identical ignoring all whitespace.
- **`src/cognitive_os/learning/`, `infrastructure/learned/`, `domain/learned.py`** — no
  `pickle`, untrusted `joblib.load`, `torch.load`, `eval`, `exec`, `marshal` or
  `__import__`. `LearnedArtifactFormat` admits only `safetensors`, `joblib`, `none`. No
  provider identifier, API key, token or password.
- **`infrastructure/memory/postgres/repository.py`** — an approximate query is refused
  rather than quietly served exactly, and an exact query never inherits an approximate
  setting.
- **`schemas/`** — 43 files; `python -m cognitive_os.schemas.export --check` reports no
  drift.

No donor, cache, credential, benchmark-output or environment-specific path is tracked.

---

## 2. Defect found and fixed during release validation

Sprint 21R's failure policy permits a functional change only when a reproducible release
gate exposes a defect. One did.

### 2.1 Migration `0013` broke the CI drift gate

**Symptom.** Reproducing the CI `migration` job locally against a *freshly created*
PostgreSQL 18 / pgvector 0.8.2 database:

```text
alembic upgrade head      rc=0
alembic downgrade base    rc=0
alembic upgrade head      rc=0
alembic check             rc=255   FAILED
  New upgrade operations detected:
    remove_index ix_memory_embeddings_hnsw_64
    remove_index ix_memory_embeddings_hnsw_768
```

**Root cause.** `0013` creates both approximate-retrieval indexes as partial expression
indexes through raw SQL
(`USING hnsw ((embedding::vector(N)) vector_cosine_ops) WHERE dimension = N`). A
SQLAlchemy `Table` cannot express that shape, so autogenerate reflected them, found no
metadata counterpart, and proposed dropping them — on every database upgraded to `0013`,
even though the schema is exactly what the migration intends.

**Why nothing caught it.** `ci.yml` triggers on push to `main` and on `pull_request`
only. The branch had four commits and no PR, so it had never had a CI run. Opening the
implementation PR without this fix would have produced a red required job.

**Fix.** An `include_object` hook in `infra/postgres/alembic/env.py` that excludes
exactly the approximate index names from autogenerate comparison. The exclusion is
derived from `APPROXIMATE_INDEX_NAMES`, the same constant the migration builds its names
from and the memory-plane health check verifies against, so it cannot drift. Migration
execution is untouched; only comparison is affected.

**Verification that it hides nothing.** After the round trip both indexes exist with the
intended definitions, and the widened check constraint is present:

```text
CREATE INDEX ix_memory_embeddings_hnsw_64  ON cognitive_os.memory_embeddings
  USING hnsw (((embedding)::vector(64)) vector_cosine_ops)  WHERE (dimension = 64)
CREATE INDEX ix_memory_embeddings_hnsw_768 ON cognitive_os.memory_embeddings
  USING hnsw (((embedding)::vector(768)) vector_cosine_ops) WHERE (dimension = 768)
CHECK (retrieval_mode = ANY (ARRAY['metadata','text','vector','vector_approximate']))
```

Three regression tests in
`tests/cognitive_os/memory/test_approximate_retrieval.py::TestAutogenerateSeesTheApproximateIndexesAsIntended`
pin that every approximate index name is excluded, that nothing else is (a broad
exclusion would hide real drift), and that the exclusion tracks the declared dimensions.

### 2.2 `memory-plane-core` could not collect its own new test module

**Symptom.** The first CI run of this branch — PR #210, which *is* its first run — failed
`memory-plane-core`:

```text
ImportError while importing test module tests/cognitive_os/memory/test_approximate_retrieval.py
E   ModuleNotFoundError: No module named 'sqlalchemy'
Interrupted: 1 error during collection
```

**Root cause.** `test_approximate_retrieval.py` was added by `d8c489c` and imports
`sqlalchemy.dialects.postgresql` at module level, because its whole purpose is to assert
the *generated SQL shape* that keeps exact retrieval exact. `memory-plane-core` synced
`--locked --all-groups` with no extra, and `sqlalchemy` lives behind the
`memory-postgres` extra: verified by `uv run --isolated --no-dev --all-groups`, where
`find_spec("sqlalchemy")` is `None`. The module therefore could not be collected at all.

**Why nothing caught it.** The same reason as §2.1 — the branch had never had a CI run.
Locally it passes, because a development environment synced with
`--extra memory-postgres` has SQLAlchemy; the gap only appears in the job's narrower
environment.

**Fix.** `memory-plane-core` now syncs `--all-groups --extra memory-postgres`, following
the existing precedent of `semantic-memory-core`, which adds `--extra semantic-graph` for
the same reason. The whole-repository `test` job gained the extra too, since
`pytest tests/cognitive_os -q` collects the same module. Making the module skip instead
was rejected: the ANN SQL-shape guarantee is exactly what must not go untested, and a
skipped mandatory scenario is not a pass. The default-wheel boundary is unaffected and
still guarded by the separate `optional-boundary` job.

### 2.3 A pre-existing local drift, correctly not fixed

`alembic check` against the *development* database also reported
`experience_step_assessments.confidence` as `TEXT` where the model declares
`Numeric(5,4)`. This does **not** appear on a freshly migrated database and is absent
from the CI path, which rebuilds from `base`. It is local development-database state, not
a product defect, and no source change was made for it.

---

## 3. Evidence matrix — R0 completion criteria

| # | Criterion | Status | Evidence |
|---:|---|---|---|
| 1 | Local, remote, PR, CI, tag, branch and merge-base state reconciled | **Met** | §1; `artifacts/sprint-21/preflight/state-freeze.json` |
| 2 | Every commit and all 132 files mapped to scope or removed | **Met** | §1.2, §1.3; zero unclassified, zero blocking findings |
| 3 | Migration head `0013` upgrades, downgrades, re-upgrades, passes drift | **Met after the §2.1 fix** | §4.4 |
| 4 | PostgreSQL integration, permissions, vector-index, backup, restore green | **Met** | §4.5, §4.6 |
| 5 | Complete local quality, typing, schema, unit, contract, integration, packaging, security, dependency, secret and language gates green | **Met** | §4.1–§4.3, §4.7 |
| 6 | Sprint 20 and earlier regression suites remain green | **Met** | §4.2, §4.3 |
| 7 | Coding and cross-domain benchmark artifacts reproducible from tracked manifests | **Met** | §4.3 |
| 8 | Gate L assessment reflects the fourth domain and current head | **Met** | [gate-l-assessment.md](gate-l-assessment.md) revision 2 |
| 9 | Assessment separates internal prediction headroom from downstream learned benefit | **Met** | Gate L assessment, *Condition 8* and *What this assessment does not claim* |
| 10 | Every release claim maps to a command, artifact, commit, PR or CI handle | **Met** | this report |
| 11 | Approved planning documents committed without unrelated working-tree files | **Met** | §6 |
| 12 | Active branch pushed without force | `PENDING` | S21R-011 |
| 13 | Implementation PR passes every required check and review | **Blocked — see §7**; PR #210 CI evidence in §4.11 | S21R-012 |
| 14 | Implementation PR merged without administrative bypass, exact head matching | **Blocked — see §7** | S21R-013 |
| 15 | Post-merge `main` CI passes for the implementation merge | `PENDING` | S21R-014 |
| 16 | Final release handles added through a documentation-only PR | `PENDING` | S21R-014 |
| 17 | Post-merge `main` CI passes for the final evidence commit | `PENDING` | S21R-014 |
| 18 | `sprint-21-substrate-baseline` annotated on the final verified evidence commit | `PENDING` | S21R-015 |
| 19 | Peeled remote tag and final `origin/main` agree | `PENDING` | S21R-015 |
| 20 | Report states Gate L2 remains open and names the Sprint 21C1 hand-off | **Met** | §5, §8 |

---

## 4. Measured evidence

### 4.1 Quality, typing, schema, language

| Gate | Command | Result |
|---|---|---|
| Ruff lint | `ruff check --config ruff.cognitive-os.toml src tests scripts infra` | `All checks passed!` |
| Ruff format | `ruff format --check … src tests scripts infra` | `807 files already formatted` |
| Mypy | `mypy src/cognitive_os` | `no issues found in 522 source files` |
| Schema drift | `python -m cognitive_os.schemas.export --check` | `Contract schema check passed.` |
| Whitespace | `git diff --check` | clean |
| Language policy | `./scripts/check_repository_language.sh` | `Repository language check passed.` |

Artifact: `artifacts/sprint-21/evidence/s21r-006-local-gates.txt`.

### 4.2 Test suites

| Suite | Result |
|---|---|
| `pytest tests/cognitive_os/learning` | 80 passed |
| `pytest tests/cognitive_os/domains tests/cognitive_os/benchmarks/test_domain_adapter.py tests/cognitive_os/memory/test_approximate_retrieval.py` | 463 passed |
| `pytest tests/cognitive_os` | **1238 passed, 5 skipped** |
| `pytest tests/cognitive_os tests/contract` | **1303 passed, 5 skipped** |
| `pytest` (whole repository) | **1385 passed, 50 skipped** |
| `run_postgres_integration_tests.sh` | **42 passed** — executed, not skipped |

The 50 skips in the whole-repository run are the PostgreSQL-marked cases, which are
covered separately and green in §4.5; they are not counted as passes anywhere.

The Sprint 22 development plan records `1236` and `1301` for the first two suites,
measured before Sprint 21R. The current figures are `1238` and `1303`: the three
regression tests from §2.1, minus one test that the plan's environment collected and this
one does not. Artifacts:
`artifacts/sprint-21/evidence/s21r-005-focused-tests.txt`,
`artifacts/sprint-21/evidence/s21r-006-final-counts.txt`.

### 4.3 Benchmarks — all four manifests, credential-free

| Benchmark | Cases | Pass rate | Expected matched | Manifest hash |
|---|---:|---:|---:|---|
| `sprint20-domain-ci` | 24 | 1.0 | 24 | `2523f85c805043539911db063f4ea34eba565d55a016ffb9c31401ddec08a832` |
| `sprint20-domain-seed` | 120 | 1.0 | 120 | `9994ad6632467dce2f6d5e130ded5df0b6583128422a61fcf6f0df942fafdde6` |
| `sprint22-coding-ci` | 15 | 1.0 | 15 | `295b20f4f88e5c74308d1ad5d53564194124ce41094f44cff138818ae2c04f2d` |
| `sprint22-coding-seed` | 25 | 1.0 | 25 | `16034ae90aceeffb08498f87aa7fca286b821c374cb37ad63a08c9960dbcfc72` |

Every run recorded `provider_calls=0`, `network_calls=0`, `credential_reads=0`,
`gpu_calls=0` and `active_state_mutations=0`. Reports:
`artifacts/sprint-21/benchmarks/{domain-ci,domain-seed,coding-ci,coding-seed}/`, summary
in `artifacts/sprint-21/evidence/s21r-005-benchmarks.json`.

The coding seed run reports `accepted=11` and `baseline_rejected=6` across 17 cases —
the per-case baseline outcome table, matching the declaration in
`FALLIBLE_CODING_CASES` exactly.

Deterministic smoke gate: `scripts/domain_smoke_test.py` exits 0 with
`matched_declared_disposition == cases` for all four domains and
`fallible_baselines=6` for coding. Governance sweep: `scripts/domain.py health` reports
all 28 checks true, `healthy: true`.

### 4.4 Migration `0013`

Reproduced on a fresh isolated database, PostgreSQL 18 / pgvector 0.8.2:

| Sequence | Result |
|---|---|
| `upgrade head` → `downgrade base` → `upgrade head` → `check` | all rc=0 (after the §2.1 fix; `check` was rc=255 before) |
| `downgrade 0012` → `upgrade 0013` → `downgrade 0012` → `upgrade 0013` | all rc=0 |
| `alembic check` after the round trip | rc=0, `No new upgrade operations detected.` |
| `alembic current` | `0013 (head)` |

Both HNSW indexes and the widened `ck_memory_access_mode` constraint verified present
after the round trip (§2.1). Artifact:
`artifacts/sprint-21/evidence/s21r-007-migration-roundtrip.txt`.

### 4.5 PostgreSQL integration and permissions

42 tests executed and passed against a provisioned PostgreSQL 18 / pgvector 0.8.2. Named
evidence for the release-critical cases:

```text
PASSED test_memory_plane.py::test_postgres_memory_exact_retrieval_and_access_audit
PASSED test_memory_plane.py::test_runtime_role_cannot_rewrite_or_delete_memory_history
PASSED test_memory_plane.py::test_approximate_retrieval_reaches_the_index_and_exact_retrieval_cannot
PASSED test_memory_plane.py::test_approximate_search_effort_applies_and_does_not_leak
PASSED test_permissions.py::test_runtime_role_cannot_mutate_event_history_or_schema
PASSED test_health.py::test_health_reports_database_and_migration_without_url
```

The third is the plan-readback proof that the approximate query actually reaches the
index while the exact query cannot. Artifact:
`artifacts/sprint-21/evidence/s21r-007-postgres-integration.txt`.

### 4.6 Backup, isolated restore, replay

Run against a consistent isolated database and artifact root at migration head `0013`,
mirroring the CI job.

| Step | Result |
|---|---|
| `backup_event_store.sh` | manifest written; `Verified 3 artifact files.`; 2.1 s |
| Dump and archive checksums on restore | both `OK` |
| `restore_event_store.sh --test-restore` | `Verified 3 artifact files.`, `Verified 2 restored Wiki revision hashes.`, `Isolated restore verification passed.`; 3.2 s |
| Migration head before backup / after restore | `0013` / `0013` |
| Storage | dump 458 KB, artifact archive 341 B, backup root 952 KB |

Source-versus-restored comparison, all MATCH: events 40, artifacts 3, artifact blobs 3,
memory items 4, semantic claims 3. Both ANN indexes present in the restored database. The
test restore targeted only `s21r_backup_restore_test`; the active development database was
not a target and was not mutated.

**Disclosed limitation.** The first backup attempt ran against the development database
and failed: `artifact metadata references a missing regular file`. Its `artifact_blobs`
rows reference four content hashes whose files are absent, while the artifact root holds
five different files — the two drifted apart in local development on 2026-07-15. The
verification script refused correctly; that guard working is the intended behaviour. No
source change was made, and the release evidence above therefore comes from a freshly
built consistent pair, which is what CI does. The development database's artifact state
remains inconsistent and is an operations item, not a release blocker.

Artifact: `artifacts/sprint-21/evidence/s21r-008-backup-restore.txt`.

### 4.7 Security, dependency, secrets, packaging

| Gate | Result |
|---|---|
| `bandit -r src/cognitive_os` | exit 0, no failed test; only informational `nosec` notices on the sandbox lifecycle temp paths |
| `pip-audit` over the locked environment | `No known vulnerabilities found` (`cognitive-os` itself skipped: not on PyPI) |
| `detect-secrets-hook --baseline .secrets.baseline` over every tracked file | rc=0 |
| `.secrets.baseline` delta review | §1.3 — hex digests only |
| `./scripts/verify_distribution.sh` | wheel, sdist, wheel install and semantic extra all OK |
| `./scripts/verify_editable_install.sh` | `Editable import OK` |
| Default-wheel optional boundary | covered by the `optional-boundary` CI job |

Artifact: `artifacts/sprint-21/evidence/s21r-009-security.txt`.

### 4.8 CI coverage mapping

27 jobs, unique ids, none removed relative to `main`. Every required evidence class maps
to at least one job: quality, mypy, bandit, schema drift, unit and contract tests,
PostgreSQL integration, migration round trip, drift check, backup/restore, both Sprint 20
manifests, both Sprint 22 coding manifests, domain smoke, domain governance, packaging,
optional boundary, language policy, sandbox, memory, semantic, strategy, experience,
corpus and controlled change. No job requires live provider credentials. Artifact:
`artifacts/sprint-21/evidence/s21r-010-ci-mapping.txt`.

### 4.9 Retrieval capacity, as measured

| Corpus | Dimension | Exact p50 | Approximate p50 | Speed-up |
|---|---:|---:|---:|---:|
| Clustered, 10⁵ | 768 | 321.2 ms | **15.3 ms** | 21× |
| Uniform noise, 10⁵ | 768 | 319.4 ms | 82.0 ms | 3.9× |

Recall 0.992@20 on the clustered corpus; the uniform-noise floor is 0.496 and is
disclosed rather than hidden. Committed envelopes:
`docs/sprints/sprint-21/envelope_1e5.json`,
`docs/sprints/sprint-21/envelope_1e5_clustered.json`. Both state that vectors were loaded
outside the governed write path, so they measure the retrieval engine, not governed
ingestion. **10⁶ is not measured** — that is Sprint 22B.

### 4.10 Environment and hardware

| Item | Value |
|---|---|
| Python | 3.12.13 |
| PostgreSQL | `pgvector/pgvector:0.8.2-pg18-bookworm`, healthy |
| Docker | 29.6.2, rootless |
| GPU | NVIDIA GeForce RTX 5070 Ti, driver 595.84 — **present and responding** |

The backlog's S21R-004 task 5 anticipated recording an unavailable NVIDIA driver. The
measured fact is the opposite, so the measured fact is recorded. This changes no
non-goal: no CUDA, `torch` or GPU dependency is introduced, no gate uses the GPU, and
every benchmark run reported `gpu_calls=0`.

---

## 5. What this release does not claim

- **No useful machine learning.** No learned component is active, promoted or enabled.
  None was activated to obtain a green release.
- **`0.9396` is prediction headroom only** — the deterministic `requirements_available`
  rule's accuracy over 1292 examples, with 78 confident errors. It is not evidence of
  improved agent success and not a Gate L2 result. See the Gate L assessment.
- **The coding domain executes no code.** Its checker compares against a golden
  reference and reports under `coding.golden_equality`, deliberately not `coding.pytest`.
  No coding fixture proves coding-agent repair ability.
- **The coding domain provides no learned tie-break.** All 17 cases have one applicable
  candidate and select by `EXACT_SIGNATURE`.
- **Learned artifacts and evaluation state are not durably persisted.** Migration head is
  `0013`; the learned evidence store is Sprint 21C1.
- **No real-run experience.** The distribution comparison is `not_established` on zero
  real samples.
- **The measured capacity envelope is 10⁵, not 10⁶.**
- **Gate L2 is open.**

---

## 6. Release commit scope

The release commit adds only reviewed Sprint 21R content on top of the four
implementation commits:

- `docs/sprints/sprint-21/gate-l-assessment.md` — revision 2, four domains
- `docs/sprints/sprint-21/report.md` — this report
- `docs/sprints/sprint-21/sprint-21r-technical-backlog.md`
- `docs/sprints/sprint-22/development-plan.md` — revision 2
- `docs/sprints/sprint-22/execution-sprint-allocation.md`
- `infra/postgres/alembic/env.py` — the §2.1 fix
- `tests/cognitive_os/memory/test_approximate_retrieval.py` — its regression tests

Paths were staged explicitly. No unrelated working-tree file is included.

**Artifacts are deliberately not committed.** `.gitignore` excludes `/artifacts/`, and
the Sprint 20 evidence is untracked for the same reason, so the 20 files under
`artifacts/sprint-21/` referenced throughout §4 are local reproducible evidence rather
than tracked release content. They are reproduced by re-running the commands this report
names; the durable tracked record is this report and the Gate L assessment. The same rule
is why raw benchmark output is summarised here rather than pasted.

---

## 7. Release status: blocked pending owner decision

Two premises of the backlog's release model do not hold as written. Both are recorded
here rather than worked around, because §4.3 of the backlog makes bypass forbidden and
§7 S21R-015 defines **release-blocked** as a legitimate outcome.

**1. `main` is not a protected branch.** `gh api repos/palkouser/cognitive-os/branches/main/protection`
returns `404 Branch not protected`. There are therefore no required status checks and no
required reviews enforced by GitHub. The backlog requires a "protected implementation
PR", that "required reviews and branch protection are satisfied", and that the merge
happen "without administrative bypass". With no protection configured, those conditions
cannot be satisfied as stated — and claiming them would be exactly the kind of false
release claim this sprint forbids. What *can* be done, and has been prepared, is the same
workflow by discipline: open the PR, wait for every CI job to complete green, merge only
then, with exact head matching, no force push and no `--admin`.

**2. There is no second party to review.** The backlog requires review findings to be
resolved before merge. A self-merge satisfies no review requirement.

**Consequently S21R-013, S21R-014 and S21R-015 are not executed.** The implementation
merge, the release-evidence PR and the annotated `sprint-21-substrate-baseline` tag all
wait on an explicit owner decision to either configure branch protection and review the
PR, or to record a waiver of the review requirement in this report before merging.

Nothing else blocks the release: every local, PostgreSQL, benchmark, security and
packaging gate is green, and the one defect the gates exposed is fixed and tested.

---

## 8. Sprint 21C1 hand-off contract

Sprint 21C1 may begin only once `sprint-21-substrate-baseline` exists and §3 is complete.

| Item | Value |
|---|---|
| Parent tag | `sprint-21-substrate-baseline` — `PENDING` |
| Migration head | `0013` |
| Next branch | `feature/sprint-21c1-learned-evidence` |
| Next migration | `0014_create_learned_evidence_store.py`, from verified head `0013` |
| Reproducible capacity artifacts | `envelope_1e5.json`, `envelope_1e5_clustered.json` at 10⁵ |
| Four-domain regression evidence | §4.3 |

Gate L2 remains open. The missing evidence and its owning sprints are tabulated in the
Gate L assessment's *Gate L2* section: durable learned evidence (21C1), real governed
traffic (21C1), executed coding outcomes (21C3), a materially beneficial learned
component (21D1, 21D2), and a tie-break surface with real ties (21D1).

Known limitations carried forward: non-executable coding fixtures, no real-run corpus, no
provider adapters, no local embeddings, no GPU-dependent path, no active learned
component, and the development database's inconsistent artifact state (§4.6).

Sprint 21C1 must reuse these contracts. It must not create a parallel learning event
store, artifact system, benchmark runner or promotion framework.
