# Cognitive OS — Sprint 21R Technical Backlog

## Learning Substrate Reconciliation and Protected Release

Document status: implementation backlog

Repository: `palkouser/cognitive-os`

Required implementation parent: `main` at the revalidated merge base

Last completed implementation release: `sprint-20-baseline`

Reported active branch: `feature/sprint-21a-learning-substrate`

Assessed active branch head: `fe26644376a35d9f034f738edd67335a8e4b8114`

Assessed `main` and `origin/main`: `c8557389f8bd1e763098125176f1321b2fc765a8`

Required migration head: `0013`

Target migration head: `0013` — no new migration in Sprint 21R

Target release tag: `sprint-21-substrate-baseline`

Runtime baseline: Python 3.12, PostgreSQL 18, pgvector 0.8.2, rootless Docker

Repository language: English only

Primary operating mode: local, single-user, credential-free release validation

Sprint stage gate: R0 — Protected Learning Substrate Baseline

Prepared from:

- [Sprint 22 development plan](../sprint-22/development-plan.md);
- [execution sprint allocation](../sprint-22/execution-sprint-allocation.md);
- [Sprint 21 technical plan](technical-plan.md);
- [Gate L assessment](gate-l-assessment.md);
- [Sprint 20 report](../sprint-20/report.md);
- [Sprint 21 substrate report](report.md), created by S21R-004;
- the active branch implementation and ADRs;
- the Sprint 19 technical backlog structure;
- local and GitHub state reviewed on 2026-07-26.

This backlog defines a future execution workflow. Its presence does not itself
authorize push, PR creation, merge, or tag publication. Those external repository
actions occur only when the user explicitly starts execution of Sprint 21R or grants
equivalent release authority.

---

# 1. Executive implementation brief

Sprint 21R must convert the existing Sprint 21 learning substrate from a locally
validated, unreleased four-commit branch into a protected and reproducible repository
baseline.

The required end-to-end path is:

```text
revalidate local and remote repository state
-> freeze exact main, tag, branch, migration and schema baselines
-> inventory all 132 changed files and four commits
-> review authority, dependency, migration, CI and security-sensitive deltas
-> refresh Gate L assessment at the actual branch head
-> create Sprint 21 substrate closure evidence
-> run targeted learning/domain tests and benchmarks
-> run complete local quality, test, schema and package gates
-> run PostgreSQL migration, integration, permissions, backup and restore gates
-> run security, dependency, secret and language gates
-> verify branch CI coverage and required job names
-> create one coherent release commit for approved planning/report updates
-> push the exact branch head
-> open protected implementation PR
-> wait for every required PR check and review
-> merge with exact head matching and no bypass
-> verify post-merge main CI
-> complete final release evidence through a protected documentation PR
-> verify second post-merge main CI
-> create and push annotated sprint-21-substrate-baseline
-> verify local tag, remote tag and origin/main
-> hand off exact baseline to Sprint 21C1
```

Sprint 21R does not claim useful machine learning. It releases the contracts,
baselines, domain integration, ANN capacity evidence, and governed selection seam
needed to implement useful learning safely.

Two concepts must remain separate:

1. **Learning substrate release**
   - proves that the current implementation is reviewed, tested, migrated, restored,
     and protected;
   - may report the honest Gate L no-go and current headroom;
   - must not activate a learned component merely to obtain a green release.

2. **Gate L2 learning completion**
   - requires persistent real evidence and a materially beneficial learned runtime
     path;
   - belongs to later Sprint 21C and Sprint 21D work;
   - remains open after Sprint 21R.

---

# 2. Authoritative starting state and mandatory reconciliation

## 2.1. Assessed local state

The state observed before writing this backlog was:

| Item | Assessed state |
|---|---|
| Active branch | `feature/sprint-21a-learning-substrate` |
| Active head | `fe26644376a35d9f034f738edd67335a8e4b8114` |
| `main` | `c8557389f8bd1e763098125176f1321b2fc765a8` |
| `origin/main` | `c8557389f8bd1e763098125176f1321b2fc765a8` |
| Merge base | `c8557389f8bd1e763098125176f1321b2fc765a8` |
| Divergence | zero commits behind, four commits ahead |
| Files changed against `main` | 132 |
| Diff size | 13,767 insertions and 971 deletions |
| Active-branch PR | none |
| Active-branch Actions runs | none |
| Current migration head | `0013_create_approximate_vector_indexes.py` |
| Last implementation tag | `sprint-20-baseline` at `837405c90eeb4835de24e394fc9a14e1a94dbc8a` |
| Latest assessed `main` CI | run `30142384838`, successful |

The four active-branch commits are:

```text
d8c489c feat(learning): Sprint 21A learning substrate — self-play labelling,
        invariance gate, forgetting gate, measured ANN capacity
fcea853 feat(learning): Sprint 21B — baseline ladder, promotion gate,
        Gate L no-go
cec0dc0 feat(domains,skills): bind governed selection to the domain path,
        feed statistics, settle the useful label
fe26644 feat(domains): coding as the fourth domain,
        with the headroom evidence pinned
```

Planning documents are intentionally uncommitted at backlog-preparation time. Their
final reviewed state must be included in the release inventory without accidentally
staging unrelated user files.

## 2.2. Assessed local evidence

The planning assessment recorded:

| Check | Result |
|---|---:|
| Core tests | `1236 passed, 5 skipped` |
| Core plus contract tests | `1301 passed, 5 skipped` |
| Integration tests without provisioned PostgreSQL | `16 passed, 45 skipped` |
| Ruff lint | passed |
| Ruff format | `807 files already formatted` |
| Mypy | no issues in 522 source files |
| Contract schema drift | passed |
| Diff check | passed before planning edits |
| Coding CI benchmark | all expected outcomes matched |
| Coding seed benchmark | all expected outcomes matched |

These results are useful but not sufficient for release. The 45 skipped integration
tests require provisioned PostgreSQL or remote CI evidence. The branch itself has no
remote run.

## 2.3. State that must not be overstated

- The coding domain uses deterministic in-process expected-output checking. It does
  not execute submitted repairs in a real sandbox.
- The coding cases expose prediction headroom but do not provide a genuine learned
  choice on the current skill tie-break.
- The approximately `0.9396` deterministic rule accuracy is evidence of imperfect
  prediction, not evidence of improved agent success.
- Learned artifacts and evaluation state are not yet durably persisted.
- The measured capacity envelope is `10^5`, not `10^6`.
- Gate L2 is open.

## 2.4. Required reconciliation commands

Run from the shared checkout only after Sprint 21R execution is authorized:

```bash
cd /home/palkouser/projekt/cognitive-os

git status --short --branch
git branch --show-current
git remote -v
git fetch origin --prune --tags

git rev-parse HEAD
git rev-parse main
git rev-parse origin/main
git merge-base main HEAD
git rev-list --left-right --count main...HEAD

git log --oneline --decorate main..HEAD
git diff --shortstat main...HEAD
git diff --name-status main...HEAD

git rev-parse sprint-20-baseline^{}
git ls-remote --tags origin refs/tags/sprint-20-baseline
git ls-remote --tags origin refs/tags/sprint-20-baseline^{}

gh pr list \
  --repo palkouser/cognitive-os \
  --head feature/sprint-21a-learning-substrate \
  --state all

gh run list \
  --repo palkouser/cognitive-os \
  --branch feature/sprint-21a-learning-substrate \
  --limit 10
```

If `origin/main`, the merge base, active branch, migration head, tag, PR, or remote
run differs from the assessed state, update the report and this backlog's execution
assumptions before continuing. Do not reset, force-push, or discard planning changes.

---

# 3. Sprint goal, completion criteria and non-goals

## 3.1. Sprint goal

> Release the exact Sprint 21 learning-substrate branch through complete local and
> PostgreSQL evidence, protected review, two post-merge-verified evidence steps, and
> an annotated baseline tag, while preserving the honest Gate L no-go and creating a
> stable parent for persistent machine-learning work.

## 3.2. R0 completion criteria

Sprint 21R is complete only when:

1. current local, remote, PR, CI, tag, branch, and merge-base state is reconciled;
2. every branch commit and all 132 changed files are mapped to Sprint 21 scope or
   explicitly removed through a safe review change;
3. migration head `0013` upgrades, downgrades, re-upgrades, and passes drift checks;
4. PostgreSQL integration, permissions, vector-index, backup, and restore evidence is
   green;
5. complete local quality, typing, schema, unit, contract, integration, packaging,
   security, dependency, secret, and language gates are green;
6. Sprint 20 and earlier regression suites remain green;
7. coding and cross-domain benchmark artifacts are reproducible from tracked
   manifests;
8. the Gate L assessment reflects the fourth domain and current head;
9. the assessment clearly separates internal prediction headroom from downstream
   learned benefit;
10. the Sprint 21 report maps every release claim to a command, artifact, commit, PR,
    or CI handle;
11. approved planning documents are committed without unrelated working-tree files;
12. the active branch is pushed without force;
13. the implementation PR passes every required check and review;
14. the implementation PR is merged without administrative bypass and with exact
    head matching;
15. post-merge `main` CI passes for the implementation merge;
16. final release handles are added through a protected documentation PR;
17. post-merge `main` CI passes for the final evidence commit;
18. `sprint-21-substrate-baseline` is an annotated tag on the final verified evidence
    commit;
19. the peeled remote tag and final `origin/main` SHA agree;
20. the report states that Gate L2 remains open and names the Sprint 21C1 hand-off.

## 3.3. Explicit non-goals

Sprint 21R does not include:

- migration `0014`;
- PostgreSQL persistence for learned artifacts or evaluations;
- OpenRouter or Codex provider implementation;
- new Claude Code authority;
- live provider calls as a required CI gate;
- new training data or corpus expansion;
- executable reality-grade coding tasks;
- local embedding activation;
- EMG graph derivation or FGW;
- a new classifier, neural model, GNN, or local language model;
- activation of k-NN or another learned component solely for release;
- a claim that the coding fixtures prove coding-agent repair ability;
- a `10^6` capacity claim;
- unrestricted self-modification;
- direct push to `main`;
- branch-protection bypass, force push, `--admin`, or stale-head merge.

Functional code changes are allowed only when a reproducible release gate exposes a
defect in the existing branch. Such fixes must be targeted, tested, documented, and
re-run through every affected gate.

---

# 4. Authority and release model

## 4.1. Authority matrix

| Concern | Authority | Sprint 21R rule |
|---|---|---|
| Existing branch commits | Git history | Review and preserve exact lineage |
| Planning documents | User-approved repository changes | Review before staging |
| Gate L result | Evidence and verifier outputs | Never rewritten to obtain a release |
| Migration state | Alembic chain and repository migration checks | Remains at `0013` |
| Learned activation | Existing governed promotion contracts | No new activation in Sprint 21R |
| Local validation | Repository-owned scripts and tests | Must run from exact release head |
| Remote validation | Protected GitHub Actions | All required checks must complete |
| Implementation merge | User-authorized operator workflow | Exact-head protected merge only |
| Release evidence merge | User-authorized operator workflow | Documentation-only protected PR |
| Tag publication | User-authorized operator workflow | Only after final `main` CI |
| Secrets and credentials | Operator environment | Never persisted or printed |

## 4.2. Two-PR release sequence

Sprint 21R uses two protected PRs so that final release handles can be retained in the
repository before the baseline tag is created:

1. **Implementation PR**
   - contains the existing learning substrate and reviewed planning/report content;
   - passes the complete product CI matrix;
   - merges and passes post-merge `main` CI.

2. **Release-evidence PR**
   - changes only the Sprint 21 report and strictly required evidence references;
   - records implementation PR, merge SHA, PR CI, and first post-merge CI;
   - passes protected documentation/repository CI;
   - merges and passes final post-merge `main` CI.

The annotated baseline tag is created on the final release-evidence merge SHA. That
commit contains the implementation, plans, and complete closure report.

If repository policy supports a different auditable mechanism that retains all final
handles in the tagged commit, it may be used after an explicit report update. The
release must not create an unreported tag or leave `main` ahead of the intended
baseline during hand-off.

## 4.3. Failure policy

- A product or test failure requires root-cause evidence and a targeted fix.
- An unchanged-head setup or dependency-fetch failure must be inspected and may be
  rerun before source changes.
- Repeated infrastructure failure is reported separately from product status.
- A skipped mandatory PostgreSQL scenario is not a pass.
- A red required check blocks merge.
- A changed PR head invalidates earlier exact-head evidence and must be revalidated.
- Missing credentials or authorization create a release-blocked outcome; they do not
  authorize bypass.

---

# 5. Required deliverables and file boundaries

## 5.1. Required tracked deliverables

- updated `docs/sprints/sprint-21/gate-l-assessment.md`;
- new `docs/sprints/sprint-21/report.md`;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`;
- this backlog;
- any targeted code, test, schema, manifest, CI, secret-baseline, or documentation
  correction proven necessary by validation.

## 5.2. Required report content

The Sprint 21 report must include:

- parent `main` and `sprint-20-baseline` SHAs;
- active branch and four implementation commits;
- migration head;
- change inventory and sensitive-file review;
- local environment and hardware constraints;
- exact test, benchmark, schema, migration, backup, restore, security, packaging, and
  language results;
- current learned-surface limitation;
- current domain and ANN capacity evidence;
- known limitations;
- implementation PR and CI handles;
- implementation merge and first post-merge CI;
- release-evidence PR and final post-merge CI;
- annotated tag and remote peeled SHA;
- Sprint 21C1 hand-off.

## 5.3. Artifact rules

- Large benchmark and test output remains in declared artifact locations or CI
  artifacts, not copied wholesale into Markdown.
- Reports store exact hashes, commands, counts, paths, and URLs.
- Temporary directories are explicit and outside tracked source.
- Credentials, authorization headers, host secrets, and raw provider payloads are
  prohibited.
- Generated schema changes must come only from the repository exporter.
- `.secrets.baseline` changes require exact finding review; never regenerate blindly.

---

# 6. Baseline inventory and review policy

The branch touches security- and release-sensitive surfaces, including:

- `.github/workflows/ci.yml`;
- `.pre-commit-config.yaml`;
- `.secrets.baseline`;
- `AGENTS.md`;
- migration `0013`;
- PostgreSQL health, table, and repository code;
- configuration and generated schemas;
- event catalog and learned event schemas;
- benchmark manifests;
- domain selection and execution;
- memory retrieval;
- learning and k-NN implementations.

Each sensitive change must be reviewed against its owning subsystem. A broad diff is
not accepted merely because tests pass.

The review must confirm:

- CI scope expansion is intentional and does not suppress existing jobs;
- pre-commit and secret-baseline changes do not hide findings;
- repository instructions remain accurate and English-only;
- migration `0013` follows the exact prior head and grant conventions;
- approximate retrieval falls back safely;
- domain selection retains deterministic authority and OOD behavior;
- learned schemas are deterministic and exported;
- no unsafe artifact loading or provider credential path was introduced;
- default and optional installation boundaries remain valid.

---

# 7. Detailed backlog

Priority definitions:

- **P0:** blocks the protected substrate baseline or preserves a critical authority,
  migration, security, or evidence invariant;
- **P1:** required for a complete and maintainable release;
- **P2:** useful improvement that may be deferred only when R0 remains fully
  satisfied.

Complexity uses **S / M / L / XL** as relative execution size.

## Epic A — State reconciliation, scope and reporting

### S21R-000 — Freeze the exact local and remote starting state

**Priority:** P0

**Complexity:** M

**Dependencies:** none

**Objective**

Replace every planning-time assumption with an authenticated, current repository
fact before modifying release evidence.

**Implementation tasks**

1. Capture branch, HEAD, `main`, `origin/main`, merge base, divergence, worktree, and
   remote URLs.
2. Fetch remote branches and tags without modifying the active branch.
3. Resolve and peel `sprint-20-baseline`.
4. Query all existing PRs and runs for the active branch.
5. Query the latest successful `main` run and exact head.
6. Resolve current Alembic head and schema manifest state.
7. Record current uncommitted planning files without staging them.
8. Stop and update the execution record if the branch has diverged or a PR appeared.

**Acceptance criteria**

- every SHA is full length and command-derived;
- local `main`, `origin/main`, merge base, and tag relationships are explicit;
- no fetch result is mistaken for a working-tree change;
- no destructive Git operation is used;
- the report contains an assessment timestamp and exact commands.

---

### S21R-001 — Audit the four commits and complete changed-file inventory

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-000

**Objective**

Prove that every committed change belongs to the learning substrate and that
authority-sensitive deltas have a specific review owner.

**Implementation tasks**

1. Review each commit independently and as the combined `main...HEAD` diff.
2. Classify every changed file as domain contract, learning algorithm, memory,
   PostgreSQL, schema/event, benchmark, CI/security, operations, test, or
   documentation.
3. Review `.github/workflows/ci.yml`, `.pre-commit-config.yaml`,
   `.secrets.baseline`, `AGENTS.md`, and migration `0013` separately.
4. Confirm generated schemas match source contracts.
5. Confirm no donor, local download, cache, credential, benchmark output, or
   environment-specific path is tracked.
6. Record any out-of-scope or unexplained file as a blocking finding.

**Acceptance criteria**

- all changed files have a scope category;
- every sensitive file has a review conclusion;
- unexplained changes block release;
- removal or correction uses a normal targeted commit, never history rewriting;
- the final diff has no unrelated user file.

---

### S21R-002 — Finalize the approved planning document set

**Priority:** P0

**Complexity:** M

**Dependencies:** S21R-001

**Objective**

Make the development plan, sprint allocation, and Sprint 21R backlog internally
consistent and ready to live in the tagged baseline.

**Implementation tasks**

1. Verify the development plan's current SHAs, test evidence, migration head, and
   immediate action.
2. Verify this backlog against actual repository commands and file paths.
3. Verify the execution allocation maps every development-plan task exactly once.
4. Add reciprocal links between plan, allocation, backlog, Gate L assessment, and
   Sprint 21 report.
5. Run Markdown diff and repository language checks.
6. Confirm that planning text does not imply that provider, merge, or tag actions
   already occurred.

**Acceptance criteria**

- all planning documents are English-only;
- no contradictory sprint, tag, migration, or gate name remains;
- every later sprint has a predecessor and exit artifact;
- this sprint remains release-only;
- planning files pass `git diff --check` and repository language policy.

---

### S21R-003 — Refresh the Gate L assessment at the actual branch head

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-001, S21R-002

**Objective**

Replace the stale three-domain assessment with an evidence-backed four-domain
assessment without converting current headroom into a false ML-success claim.

**Implementation tasks**

1. Update branch head, migration, corpus, domain, benchmark, and test evidence.
2. Add coding-domain accepted and rejected case statistics.
3. Record the deterministic `requirements_available` result and confident errors.
4. Explain that coding exposes one applicable skill and no learned tie-break.
5. Explain that coding verification compares expected output and executes no repair.
6. Re-run Gate L conditions against current artifacts.
7. Preserve no-go conditions that remain valid.
8. Add explicit hand-off requirements for persistent evidence and real executable
   outcomes.

**Acceptance criteria**

- the assessment covers logic, mathematics, physics, and coding;
- all numbers cite a manifest, artifact, test, or command;
- `0.9396` is described as prediction headroom only;
- the assessment does not claim active or materially useful ML;
- Gate L2 remains open with explicit missing evidence.

---

### S21R-004 — Create the Sprint 21 substrate report and evidence matrix

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-003

**Objective**

Create one authoritative closure document that separates implemented substrate,
validated evidence, release state, remaining gaps, and Sprint 21C1 hand-off.

**Implementation tasks**

1. Create `docs/sprints/sprint-21/report.md`.
2. Map every R0 completion criterion to evidence or a pending release step.
3. Record commit and changed-file inventory.
4. Record tests, benchmarks, migration, PostgreSQL, backup/restore, security,
   packaging, and language results.
5. Record current hardware limits, including unavailable NVIDIA driver.
6. Record known limitations and Gate L2-open status.
7. Create placeholders only for final PR, merge, CI, and tag handles.
8. Define the exact Sprint 21C1 parent tag and migration hand-off.

**Acceptance criteria**

- every claim is reproducible;
- pending release fields are visibly pending before merge;
- skipped mandatory checks cannot appear green;
- limitations include non-executable coding fixtures and non-persistent learning;
- report language does not imply Sprint 21C or Gate L2 completion.

---

## Epic B — Local, PostgreSQL and release-gate validation

### S21R-005 — Reproduce focused learning, domain and benchmark evidence

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-001

**Objective**

Verify the branch's new behavior independently before running the complete repository
matrix.

**Required commands**

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run pytest tests/cognitive_os/learning -q

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run pytest \
  tests/cognitive_os/domains \
  tests/cognitive_os/benchmarks/test_domain_adapter.py \
  tests/cognitive_os/memory/test_approximate_retrieval.py \
  -q

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-ci.yaml \
  --mode domain-pilot \
  --report-directory /tmp/sprint21r-domain-ci

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-seed.yaml \
  --mode domain-pilot \
  --report-directory /tmp/sprint21r-domain-seed

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint22-coding-ci.yaml \
  --mode domain-pilot \
  --report-directory /tmp/sprint21r-coding-ci

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint22-coding-seed.yaml \
  --mode domain-pilot \
  --report-directory /tmp/sprint21r-coding-seed
```

**Acceptance criteria**

- targeted tests pass without credentials or network;
- manifests and report hashes are recorded;
- expected outcomes match with zero active-state mutation;
- ANN envelope artifacts reproduce within declared tolerance;
- failures retain raw case-level evidence.

---

### S21R-006 — Run complete local quality, test, schema and package gates

**Priority:** P0

**Complexity:** XL

**Dependencies:** S21R-002, S21R-005

**Required validation**

```bash
UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv sync --locked --all-groups \
  --extra mcp \
  --extra memory-postgres \
  --extra semantic-graph

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run ruff check --config ruff.cognitive-os.toml src tests scripts infra

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run ruff format --check --config ruff.cognitive-os.toml src tests scripts infra

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run mypy src/cognitive_os

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run python -m cognitive_os.schemas.export --check

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run pytest tests/cognitive_os tests/contract -q

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
uv run pytest -q

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
./scripts/verify_distribution.sh

UV_CACHE_DIR=/home/palkouser/projekt/cognitive-os/.cache/uv \
./scripts/verify_editable_install.sh

git diff --check
./scripts/check_repository_language.sh
```

**Acceptance criteria**

- all commands pass from the exact candidate head;
- test counts and skips are recorded by suite;
- required scenarios are not omitted from the command set;
- wheel, sdist, wheel install, and editable install remain valid;
- schema exporter produces no uncommitted drift;
- final diff is clean of whitespace errors.

---

### S21R-007 — Validate migration `0013`, PostgreSQL integration and permissions

**Priority:** P0

**Complexity:** XL

**Dependencies:** S21R-005

**Objective**

Prove the approximate-vector migration and every affected repository against a
provisioned PostgreSQL 18 / pgvector 0.8.2 environment.

**Implementation tasks**

1. Start the repository-owned PostgreSQL development environment.
2. Bootstrap isolated roles.
3. Run the full migration chain to `0013`.
4. Run downgrade and re-upgrade checks.
5. Run Alembic head and schema drift checks.
6. Run `scripts/run_postgres_integration_tests.sh`.
7. Run vector index creation, query, fallback, and permission tests.
8. Confirm earlier sprint tables, functions, grants, data, and hashes remain intact.
9. Stop or preserve the environment according to repository operations policy.

**Acceptance criteria**

- the migration chain reaches exactly `0013`;
- `0012 -> 0013 -> 0012 -> 0013` passes;
- all PostgreSQL integration tests execute rather than skip;
- owner, runtime, migrator, and backup roles retain least privilege;
- vector extension absence and index failure have typed safe behavior;
- no pre-existing data or grant regresses.

---

### S21R-008 — Validate backup, isolated restore and replay at migration `0013`

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-007

**Objective**

Prove that Sprint 21 schema, memory indexes, events, domain evidence, and artifacts
survive the repository's recovery path.

**Implementation tasks**

1. Create a backup with the repository-owned backup script.
2. Verify manifest, checksums, schema version, item counts, event counts, and artifact
   references.
3. Restore only into an isolated test target.
4. Run restore verification and deterministic replay.
5. Compare active views and hashes with the source database.
6. Verify that the active database is never a restore target by default.
7. Record backup and restore durations and storage.

**Acceptance criteria**

- backup and isolated restore complete successfully;
- migration head is `0013` before and after restore;
- event replay and current projections agree;
- ANN indexes are present or deterministically rebuildable according to policy;
- artifacts and hashes resolve;
- no active-state mutation occurs during test restore.

---

### S21R-009 — Run security, dependency, secret and optional-boundary review

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-001, S21R-006

**Required coverage**

- Bandit over first-party Python;
- dependency audit for the locked environment;
- tracked-file secret scan against the reviewed baseline;
- manual `.secrets.baseline` delta review;
- pre-commit configuration delta review;
- repository language check;
- clean default wheel without optional ML/PostgreSQL extras;
- optional-boundary import and packaging checks;
- unsafe pickle or opaque executable artifact search;
- credential and local-path leakage search.

**Acceptance criteria**

- no new unresolved high-severity finding exists;
- `.secrets.baseline` contains only reviewed fingerprints;
- no secret or raw credential appears in Git history or working changes;
- core install remains provider- and PostgreSQL-credential-free;
- optional dependency absence produces explicit capability behavior;
- repository language policy passes.

---

### S21R-010 — Verify CI coverage and release-job mapping

**Priority:** P0

**Complexity:** M

**Dependencies:** S21R-006, S21R-007, S21R-008, S21R-009

**Objective**

Ensure the branch's modified workflow will execute every mandatory release check on
the protected PR and on `main`.

**Implementation tasks**

1. Inventory all job IDs in `.github/workflows/ci.yml`.
2. Compare required branch-protection checks with current job names.
3. Confirm the expanded Ruff scope covers first-party `src`, `tests`, `scripts`, and
   `infra`.
4. Confirm the cross-domain job runs both coding manifests.
5. Confirm PostgreSQL integration and migration jobs run with pgvector.
6. Confirm security, build, full test, optional-boundary, sandbox, memory, semantic,
   strategy, experience, corpus, and controlled-change jobs remain enabled.
7. Confirm no required job depends on live provider credentials.
8. Add or change workflow code only if a demonstrated coverage gap exists.

**Acceptance criteria**

- every R0 evidence class maps to at least one required local or remote gate;
- job names are unique and compatible with branch protection;
- coding-domain additions do not replace Sprint 20 regression coverage;
- live providers remain outside mandatory CI;
- workflow changes, if any, pass syntax and local relevant tests.

---

## Epic C — Protected implementation release

### S21R-011 — Create the coherent release commit and push exact branch head

**Priority:** P0

**Complexity:** M

**Dependencies:** S21R-003, S21R-004, S21R-010

**Objective**

Commit only the approved planning, assessment, report, and evidence corrections on
top of the four reviewed implementation commits, then publish the exact head.

**Pre-commit requirements**

- all mandatory local gates are green;
- report pre-release fields are current;
- generated schemas are clean;
- no secret or local-only path exists;
- `git status` contains only reviewed Sprint 21R files;
- no unrelated user change is staged.

**Required workflow**

```bash
git switch feature/sprint-21a-learning-substrate
git status --short --branch
git diff --check

git add docs/sprints/sprint-21
git add docs/sprints/sprint-22

# Add any targeted release-gate fix paths explicitly after review.

git diff --cached --name-status
git diff --cached --check

git commit -m "docs(sprint-21): reconcile learning substrate release"
git rev-parse HEAD

git push --set-upstream origin feature/sprint-21a-learning-substrate
```

Do not use `git add -A` unless the complete working tree has been re-audited and every
path is in scope.

**Acceptance criteria**

- the commit contains only reviewed Sprint 21R changes;
- the four original implementation commits remain ancestors;
- no history rewrite or force push occurs;
- remote branch head equals the exact local candidate head;
- the report records the pushed head.

---

### S21R-012 — Open the protected implementation PR and obtain complete CI

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-011

**Objective**

Submit the exact release candidate to protected review and obtain complete remote
evidence.

**Required workflow**

```bash
gh pr create \
  --repo palkouser/cognitive-os \
  --base main \
  --head feature/sprint-21a-learning-substrate \
  --title "Sprint 21: Learning substrate and four-domain evidence" \
  --body-file /tmp/sprint21r-implementation-pr.md

gh pr view \
  --repo palkouser/cognitive-os \
  feature/sprint-21a-learning-substrate \
  --json number,url,headRefOid,baseRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup

gh pr checks \
  --repo palkouser/cognitive-os \
  feature/sprint-21a-learning-substrate \
  --watch
```

**Acceptance criteria**

- PR head equals the recorded candidate SHA;
- every required job executes;
- PostgreSQL-dependent cases do not appear as local skips;
- required reviews and branch protection are satisfied;
- PR description states Gate L2 remains open;
- no check is waived or bypassed.

---

### S21R-013 — Triage failures, close review findings and merge exact head

**Priority:** P0

**Complexity:** L

**Dependencies:** S21R-012

**Failure workflow**

1. Open the exact failed job and step log.
2. Classify product, test, environment, dependency-fetch, quota, or infrastructure
   cause.
3. For an unchanged-head infrastructure failure, rerun the failed job before editing
   source.
4. For a reproducible product failure, apply the smallest root-cause fix.
5. Re-run local affected gates and all remote required checks.
6. Update the report and head SHA.
7. Resolve review comments without broad refactoring.

**Merge workflow**

```bash
gh pr view \
  --repo palkouser/cognitive-os \
  feature/sprint-21a-learning-substrate \
  --json headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup

git rev-parse HEAD

gh pr merge \
  --repo palkouser/cognitive-os \
  feature/sprint-21a-learning-substrate \
  --merge \
  --match-head-commit REPLACE_WITH_VALIDATED_HEAD_SHA \
  --delete-branch
```

Forbidden:

```text
--admin
force push
direct push to main
merge with pending or failed required checks
merge after head change without revalidation
editing code to hide an infrastructure-only failure
```

**Acceptance criteria**

- all review findings are resolved;
- final PR head is fully revalidated;
- merge uses exact head matching;
- no required check or review is bypassed;
- implementation merge SHA and PR handles are recorded.

---

### S21R-014 — Verify implementation `main` and merge final release evidence

**Priority:** P0

**Complexity:** M

**Dependencies:** S21R-013

**Objective**

Verify the implementation on protected `main`, then replace pending report fields
through a documentation-only protected PR.

**Implementation-main workflow**

```bash
git fetch origin --prune --tags
git switch main
git pull --ff-only origin main
git rev-parse HEAD

gh run list \
  --repo palkouser/cognitive-os \
  --branch main \
  --limit 10

gh run watch \
  --repo palkouser/cognitive-os \
  REPLACE_WITH_IMPLEMENTATION_MAIN_RUN_ID \
  --exit-status
```

**Release-evidence tasks**

1. Create a documentation branch from the verified implementation merge.
2. Fill the report's implementation PR, head, merge, PR CI, and post-merge CI fields.
3. Re-run diff, language, schema, and relevant documentation checks.
4. Open a documentation-only protected PR.
5. Confirm the diff contains only the report and strictly required evidence links.
6. Wait for all required checks and review.
7. Merge without bypass.
8. Verify the second post-merge `main` CI.
9. Record the final evidence merge SHA and CI run.

**Acceptance criteria**

- implementation post-merge `main` CI is successful;
- report contains exact implementation release handles;
- evidence PR is documentation-only;
- evidence PR and final `main` CI pass;
- final `origin/main` contains implementation and complete closure report;
- no functional change is smuggled into the evidence PR.

---

### S21R-015 — Tag, verify and hand off the protected substrate

**Priority:** P0

**Complexity:** M

**Dependencies:** S21R-014

**Objective**

Publish the annotated substrate tag only after final `main` evidence is complete, then
provide an exact Sprint 21C1 starting contract.

**Required workflow**

```bash
git fetch origin --prune --tags
git switch main
git pull --ff-only origin main

git rev-parse HEAD
git rev-parse origin/main

git tag -a sprint-21-substrate-baseline \
  REPLACE_WITH_FINAL_VERIFIED_MAIN_SHA \
  -m "Sprint 21 protected learning substrate baseline"

git push origin sprint-21-substrate-baseline

git rev-parse sprint-21-substrate-baseline^{}
git ls-remote --tags origin refs/tags/sprint-21-substrate-baseline
git ls-remote --tags origin refs/tags/sprint-21-substrate-baseline^{}
```

**Hand-off requirements**

- exact tag object and peeled commit;
- exact final `main` and `origin/main`;
- final `main` CI run and conclusion;
- migration head `0013`;
- complete Gate L2-open list;
- Sprint 21C1 branch name;
- expected next migration `0014_create_learned_evidence_store.py`;
- known PostgreSQL, provider, corpus, GPU, and coding limitations.

**Acceptance criteria**

- tag is annotated;
- local peeled tag, remote peeled tag, `main`, and `origin/main` agree;
- final CI belongs to the tagged commit and is successful;
- report has no pending release field;
- Gate L2 is still explicitly open;
- Sprint 21C1 can branch from the tag with a clean checkout.

If tag push, protected merge, review, credentials, or GitHub policy blocks the
workflow, Sprint 21R ends as **release-blocked**, not complete. No bypass is allowed.

---

# 8. Implementation sequence

## Wave 0 — State and scope

```text
S21R-000 -> S21R-001 -> S21R-002
```

No evidence document may be finalized before current remote state and the combined
diff are known.

## Wave 1 — Assessment and report

```text
S21R-001/S21R-002 -> S21R-003 -> S21R-004
```

## Wave 2 — Local and PostgreSQL evidence

```text
S21R-001 -> S21R-005
S21R-002/S21R-005 -> S21R-006
S21R-005 -> S21R-007 -> S21R-008
S21R-001/S21R-006 -> S21R-009
S21R-006/S21R-007/S21R-008/S21R-009 -> S21R-010
```

PostgreSQL, backup/restore, security, and packaging work may run in parallel after
their dependencies, but all must converge before the release commit.

## Wave 3 — Protected implementation release

```text
S21R-003/S21R-004/S21R-010
  -> S21R-011
  -> S21R-012
  -> S21R-013
```

## Wave 4 — Final evidence, tag and hand-off

```text
S21R-013 -> S21R-014 -> S21R-015
```

---

# 9. Definition of Ready

A Sprint 21R item is ready only when:

- every listed dependency is complete;
- exact relevant SHAs and file paths are known;
- the allowed side effects are explicit;
- required commands, tests, and evidence outputs are identified;
- no unresolved migration, credential, worktree, PR, tag, or branch-protection
  ambiguity exists;
- the item does not assume Gate L2 success;
- the item can complete without adding Sprint 21C behavior;
- unrelated user changes can be preserved.

---

# 10. Definition of Done for each backlog item

Each item is done only when:

1. its stated tasks are complete;
2. command output or review evidence is retained;
3. acceptance criteria are mapped to exact evidence;
4. affected tests and checks pass;
5. security, authority, and secret boundaries remain intact;
6. generated schemas and manifests are deterministic;
7. documentation is English and current;
8. no unrelated file or destructive Git operation is involved;
9. failures and skips are reported honestly;
10. the Sprint 21 report is updated when the item changes a release fact.

---

# 11. Test and release acceptance matrix

| Area | Mandatory Sprint 21R evidence |
|---|---|
| Repository state | branch, head, main, origin/main, merge base, divergence, tag |
| Commit scope | four commits and every changed file reviewed |
| Learning contracts | schemas, events, registry, invariance, forgetting, replacement |
| Governed selection | deterministic authority, statistics, fallback, OOD behavior |
| Domains | logic, mathematics, physics, coding |
| Coding limitation | no false executable-repair claim |
| ANN | migration `0013`, recall/latency artifacts, exact fallback |
| Quality | Ruff check and format, Mypy, diff check |
| Tests | focused, core, contract, full repository |
| Schemas | export check and manifest consistency |
| PostgreSQL | integration, permissions, vector indexes, health |
| Migration | chain, `0012 -> 0013 -> 0012 -> 0013`, drift |
| Recovery | backup, isolated restore, replay, hashes |
| Security | Bandit, dependency audit, secret scan, baseline review |
| Packaging | wheel, sdist, wheel install, editable install, optional boundary |
| Language | repository English policy |
| Benchmarks | Sprint 20 domain and Sprint 22 coding CI/seed manifests |
| PR | exact head, all required checks, reviews, no bypass |
| Main | implementation and final-evidence post-merge CI |
| Release | annotated tag, remote peeled SHA, complete report |
| Hand-off | clean `0013` baseline and Gate L2-open list |

---

# 12. Risks and mitigations

| Risk | Consequence | Required mitigation |
|---|---|---|
| Branch state changed after planning | invalid baseline | blocking S21R-000 revalidation |
| Planning files mixed with unrelated changes | accidental user-data commit | explicit path staging and cached diff review |
| Broad 132-file diff hides unsafe change | authority or security regression | categorized inventory and sensitive-file audit |
| Local green hides PostgreSQL skips | false release confidence | provisioned integration and remote CI |
| CI workflow drops an older gate | regression escapes | job mapping and Sprint 20 benchmark retention |
| `0.9396` treated as ML success | false Gate L closure | explicit assessment limitation |
| Coding fixture treated as executable repair | invalid learning evidence | report and benchmark-scope warning |
| `.secrets.baseline` masks a secret | credential exposure | exact delta and tracked-file scan |
| Migration `0013` loses prior grants/data | restore or runtime failure | round trip, permissions, backup/restore |
| Infrastructure fetch failure triggers code churn | unnecessary regression | log inspection and unchanged-head rerun |
| PR head changes after validation | stale evidence | exact head matching and full revalidation |
| Final report lacks post-merge handles | incomplete tagged evidence | second protected evidence PR |
| Tag created before final CI | unprotected baseline | S21R-015 dependency on final `main` run |
| Merge or tag credentials unavailable | incomplete release | release-blocked result, no bypass |

---

# 13. Internal resources to reuse

Use the existing repository implementation and scripts before adding anything:

- `src/cognitive_os/learning/`;
- `src/cognitive_os/domain/learned.py`;
- `src/cognitive_os/infrastructure/learned/`;
- `src/cognitive_os/domains/`;
- `src/cognitive_os/memory/`;
- `src/cognitive_os/events/learned_events.py`;
- `src/cognitive_os/schemas/`;
- `tests/cognitive_os/learning/`;
- `tests/cognitive_os/domains/`;
- `tests/integration/postgres/`;
- `benchmarks/manifests/sprint20-domain-*.yaml`;
- `benchmarks/manifests/sprint22-coding-*.yaml`;
- `scripts/benchmark_run.py`;
- `scripts/postgres_migration_check.sh`;
- `scripts/run_postgres_integration_tests.sh`;
- `scripts/backup_event_store.sh`;
- `scripts/restore_event_store.sh`;
- `scripts/verify_distribution.sh`;
- `scripts/verify_editable_install.sh`;
- `scripts/check_repository_language.sh`;
- `.github/workflows/ci.yml`.

Useful discovery commands:

```bash
rg --files src/cognitive_os/learning tests/cognitive_os/learning
rg --files src/cognitive_os/domains tests/cognitive_os/domains
rg -n "Learned|learned" src/cognitive_os tests schemas
rg -n "HNSW|ivfflat|vector|approximate" src infra tests docs
rg -n "sprint22-coding" .github benchmarks tests docs
rg -n "backup|restore|migration" scripts tests .github docs
rg -n "secret|detect-secrets|language" .github scripts docs
```

The exact released implementation is authoritative when a planning path or command
name differs.

---

# 14. External operational references

- Git worktree and branch state:
  <https://git-scm.com/docs/git-status>
- Git tag objects:
  <https://git-scm.com/docs/git-tag>
- GitHub CLI PR creation:
  <https://cli.github.com/manual/gh_pr_create>
- GitHub CLI PR checks:
  <https://cli.github.com/manual/gh_pr_checks>
- GitHub CLI protected merge:
  <https://cli.github.com/manual/gh_pr_merge>
- GitHub Actions run inspection:
  <https://cli.github.com/manual/gh_run_view>
- GitHub protected branches:
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>

---

# 15. Sprint 21C1 hand-off contract

Sprint 21C1 may begin only after `sprint-21-substrate-baseline` exists and R0 evidence
is complete.

The hand-off must guarantee:

- exact tagged parent and clean checkout;
- migration head `0013`;
- stable learned contracts and schema exports;
- governed deterministic selection and fallback;
- four-domain regression evidence;
- retained honest no-go and headroom evidence;
- reproducible `10^5` capacity artifacts;
- complete PostgreSQL grants, backup, restore, and health;
- known limitations for coding fixtures, real-run evidence, providers, embeddings,
  GPU, and learned activation;
- no uncommitted release document;
- next branch name `feature/sprint-21c1-learned-evidence`;
- next expected migration `0014_create_learned_evidence_store.py`.

Sprint 21C1 must reuse these contracts. It must not create a parallel learning event
store, artifact system, benchmark runner, or promotion framework.

---

# 16. Final R0 checklist

- [ ] Local and remote repository state is revalidated.
- [ ] `main`, `origin/main`, merge base, branch head, and divergence are recorded.
- [ ] `sprint-20-baseline` local and remote peeled SHAs are verified.
- [ ] Existing branch PRs and runs are reconciled.
- [ ] All four implementation commits are reviewed.
- [ ] All changed files are categorized.
- [ ] CI, pre-commit, secret baseline, instructions, and migration deltas are reviewed.
- [ ] Planning documents are mutually consistent and English-only.
- [ ] Gate L assessment reflects the current head and four domains.
- [ ] Gate L assessment does not claim downstream ML benefit.
- [ ] Sprint 21 report exists with an evidence matrix.
- [ ] Focused learning and domain tests pass.
- [ ] Sprint 20 domain CI and seed benchmarks pass.
- [ ] Sprint 22 coding CI and seed benchmarks pass.
- [ ] Complete core plus contract tests pass.
- [ ] Complete repository tests pass.
- [ ] Ruff, formatting, Mypy, schemas, and diff checks pass.
- [ ] Distribution and editable-install checks pass.
- [ ] Migration chain reaches exactly `0013`.
- [ ] `0012 -> 0013 -> 0012 -> 0013` passes.
- [ ] All PostgreSQL integration tests execute and pass.
- [ ] Permissions and pgvector index behavior pass.
- [ ] Backup, isolated restore, replay, and hashes pass.
- [ ] Security and dependency audits pass.
- [ ] Secret scan and baseline review pass.
- [ ] Repository language policy passes.
- [ ] Required CI job mapping is complete.
- [ ] Coherent release commit contains no unrelated file.
- [ ] Feature branch is pushed without force.
- [ ] Protected implementation PR is created.
- [ ] Exact-head required PR checks and reviews pass.
- [ ] Implementation PR merges without bypass.
- [ ] Implementation post-merge `main` CI passes.
- [ ] Final report handles are committed through a protected evidence PR.
- [ ] Final evidence PR checks and review pass.
- [ ] Final evidence post-merge `main` CI passes.
- [ ] Report has no pending release field.
- [ ] Annotated `sprint-21-substrate-baseline` is created and pushed.
- [ ] Local tag, remote peeled tag, `main`, and `origin/main` agree.
- [ ] Gate L2 remains explicitly open.
- [ ] Sprint 21C1 hand-off is exact and clean.

---

# 17. Recommended issue hierarchy

```text
Sprint 21R — Learning Substrate Reconciliation and Protected Release
|-- Epic A: State reconciliation, scope and reporting
|   |-- S21R-000 Freeze local and remote state
|   |-- S21R-001 Audit commits and changed files
|   |-- S21R-002 Finalize planning documents
|   |-- S21R-003 Refresh Gate L assessment
|   `-- S21R-004 Create Sprint 21 report
|-- Epic B: Local, PostgreSQL and release-gate validation
|   |-- S21R-005 Focused learning/domain evidence
|   |-- S21R-006 Complete local validation
|   |-- S21R-007 PostgreSQL and migration validation
|   |-- S21R-008 Backup and restore validation
|   |-- S21R-009 Security and optional-boundary review
|   `-- S21R-010 CI coverage mapping
`-- Epic C: Protected implementation release
    |-- S21R-011 Coherent commit and push
    |-- S21R-012 Protected implementation PR
    |-- S21R-013 Triage, review and merge
    |-- S21R-014 Final release-evidence PR
    `-- S21R-015 Tag and hand-off
```

Recommended labels:

```text
sprint-21r
learning-substrate
gate-r0
priority-p0
priority-p1
release
evidence
learning
domains
coding
ann
postgres
migration
backup-restore
security
benchmark
ci
documentation
```
