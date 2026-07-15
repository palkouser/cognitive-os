# Sprint 8 report

Status: Complete

## Sprint goal

Sprint 8 delivers a bounded Python 3.12 Coding Agent MVP on the existing Cognitive OS model,
Tool Plane, verifier, acceptance, event-store, artifact, and sandbox boundaries. The agent
turns a structured coding problem into a reviewable detached-worktree patch and evidence
package. It never commits, pushes, merges, installs dependencies, or grants itself network
access.

## Implemented components

- Immutable coding problem, repository profile, workspace, index, patch, command, outcome, and
  verified trajectory contracts with deterministic hashes and exported JSON Schemas.
- Fail-closed Sprint 8 configuration for repository roots, commands, paths, cleanup, artifacts,
  repair budgets, 20-file/1000-line patch limits, and 4 CPU/8192 MB sandbox limits.
- Shell-free trusted Git adapter for exact local commit validation, status, diff, detached
  worktree preparation/removal, and bounded output/timeout handling.
- Cross-process workspace lock and filesystem-level one-active-worktree enforcement. A mount
  descriptor proves that only the detached worktree is exposed as writable `/workspace`.
- Execution-free repository profiling, bounded file inventory, Python AST symbol/import index,
  deterministic search, and context packaging. Symlinks, binary files, oversized files,
  malformed Python, and detached-worktree `.git` metadata are handled without following or
  executing them.
- Canonical path, symlink, hard-link, dependency, secret, unified-diff, revision, repeated-patch,
  changed-file, and cumulative-line enforcement. Patch and file writes are atomic; overwrites
  require an expected content hash.
- Task-bound workspace tools for patch, file write, generated-file deletion, diff read, and
  changed-file listing. Structured planning and proposal requests exclude host paths and reject
  provider tool calls, permission expansion, stale revisions, and scope expansion.
- A Coding Agent facade that runs profile, preflight, worktree, index, plan, patch, verifier,
  bounded repair, full acceptance, main-tree integrity, cleanup, and packaging stages without a
  second general controller state machine.
- Required pytest, Ruff, MyPy, controlled-import, file, diff, dependency, and workspace-integrity
  verifier bundle. Existing acceptance decisions remain authoritative.
- Ten typed coding lifecycle events persisted with expected-version concurrency.
- Secret-safe canonical JSON and Markdown outcome reports, repository inspection and report
  commands, and a credential-free Sprint 8 smoke path.
- Four-case CI and fourteen-case seed coding manifests, deterministic fixture factory, Coding
  Benchmark Adapter, safety/correctness metrics, and a dedicated CI job.
- SPDX package metadata, architecture/operations documentation, Claude Code advisory boundary,
  ADR 0034, and updated project policy.

## Package structure

The implementation is centered in `src/cognitive_os/coding`, with public contracts in
`domain/coding.py`, application ports for repository/workspace/index/patch operations, trusted
Git infrastructure in `infrastructure/repository`, workspace tools in `tools/workspace.py`,
coding event services, verifier registration, benchmark adapter/manifests, operational scripts,
and unit/integration/adversarial tests.

## Validation results

- Full credential-free regression: **630 passed, 18 opt-in tests skipped**.
- Sprint 8 coding target: **24 passed, 1 Docker opt-in test skipped** in the normal run.
- Real rootless Docker checks: image build passed; non-root smoke passed; existing sandbox
  inspection tests **2/2 passed**; Coding Agent worktree-only mount test **1/1 passed**.
- End-to-end credential-free facade trajectory passed with an exact detached commit, structured
  plan/proposal, Tool Plane patch, accepted verifier decision, archived diff, and unchanged main
  checkout.
- Ruff and Ruff format passed; strict MyPy passed for **232 source files**; Bandit passed; JSON
  Schema drift, repository language, and `git diff --check` passed.
- Wheel, source distribution, isolated wheel installation, and editable installation passed on
  Python 3.12.13. SPDX license metadata includes `LICENSE` and `NOTICE` without the deprecated
  classifier/table warning.
- Dependency audit: no known vulnerabilities; the local `cognitive-os` development package is
  not a PyPI audit target. The complete new-file scan found no candidate secrets.
- Credential-free coding replay: **4/4 CI cases** and **14/14 seed cases** matched expected
  outcomes. The set includes a repair trajectory, two policy rejections, a bounded no-progress
  outcome, zero sandbox failures, and main-tree integrity for every case.

## Security status

The rootless container runs as the invoking non-root host UID for safe bind-mount ownership,
with a read-only image root, network mode `none`, all capabilities dropped, no-new-privileges,
bounded PIDs/output/time/memory/CPU, and one read-write worktree mount. The main checkout is not
mounted. Real Docker validation caught and corrected Docker v29 mount syntax and rootless UID
mapping issues before closure.

Repository content cannot select commands, inject shell syntax, access `.git`, traverse an
absolute/parent path, follow a symlink, modify a hard-linked file, add a secret, change dependency
metadata without permission, exceed patch budgets, or make model confidence satisfy acceptance.
Cleanup errors are recorded separately rather than rewriting the verification outcome.

## Known limitations

- Inspect AI runtime execution remains deferred because its upstream Click constraint conflicts
  with the security-fixed dependency set. Deterministic Inspect export remains available.
- Claude Code live advisory and MiniMax live coding runs require explicit operator opt-in and
  credentials; neither is part of credential-free CI and neither has acceptance authority.
- Prepared SWE-bench repositories remain an explicit external input. Cognitive OS does not
  download datasets, clone benchmark repositories, or execute network preparation implicitly.
- PostgreSQL lifecycle coverage is present as an opt-in integration test and runs in the CI
  PostgreSQL service; local closure used the credential-free event and facade paths.

## Sprint 9 carry-over

- Expand verified coding trajectories from deterministic local cases to larger prepared
  repositories while preserving the same authority boundary.
- Add richer semantic context ranking and focused-test selection without executing imports
  during inspection.
- Add operator UI/queue ergonomics for stale-worktree review and long-running resume workflows.
- Reassess Inspect runtime only after upstream dependency compatibility is security-safe.

## Verified trajectory hand-off

`CodingTrajectoryPackage` carries the problem, repository profile, context hash, patch plan,
patch attempts, verifier failures, repair decisions, final diff artifact, acceptance decision,
command reports, usage metrics, risks, and provenance. It is canonical, hashable, secret-safe,
and keeps provider claims separate from authoritative verifier evidence.

## Restore point

Branch: `feature/sprint-8-python-coding-agent`

Planned tag: `sprint-8-baseline`

Parent baseline: `sprint-7-baseline` at
`a9dffb235d7a043711b86a209a9a1195a63a370a`.

Restore after publication with `git switch --detach sprint-8-baseline`; return to development
with `git switch feature/sprint-8-python-coding-agent`. The baseline tag is created only after
the committed branch passes GitHub CI.
