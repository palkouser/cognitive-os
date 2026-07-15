# Python Coding Agent architecture

Sprint 8 adds a bounded Python 3.12 coding facade on top of the existing model execution,
Tool Plane, verifier, acceptance, event-store, and artifact boundaries. It does not introduce
a second general-purpose controller and provider output never decides acceptance.

## Authority boundary

The trusted host validates an exact local 40-character commit and prepares a detached Git
worktree. The main checkout is snapshotted before execution and must retain the same HEAD and
status. Repository inspection parses files and Python ASTs without importing or executing
repository code. Only structured patch plans and patch proposals cross the provider boundary;
host paths and credentials do not.

All mutation goes through task-bound workspace tools. Canonical path checks reject absolute
paths, traversal, `.git`, forbidden paths, symlink escapes, hard links, dependency changes,
binary patches, mode changes, and submodule changes. Writes are atomic and patch attempts,
changed files, and diff lines have aggregate limits. Commit, push, merge, package installation,
and network access are outside the agent's authority.

## Sandbox and acceptance

The rootless Docker image has a read-only root, no network, no Linux capabilities, no-new-
privileges, a non-root user, and at most 4 CPUs and 8192 MB memory. Its only writable host mount
is the detached worktree at `/workspace`; the main repository is never mounted.

Pytest, Ruff, MyPy, controlled import, file policy, diff policy, dependency policy, and
workspace integrity form the required verifier bundle. The existing acceptance service is
authoritative. Repair is allowed only while both the three-attempt patch budget and the
three-cycle repair budget remain. Repeated proposals fail closed.

## Lifecycle and audit

Typed events record profile detection/rejection, workspace preparation, indexing, planning,
patch attempts, patch rejection/application, archive, and result packaging on the task-run
stream with expected-version concurrency. Outcomes record policy denials, risks, verifier
evidence, acceptance, changed files, usage, and cleanup disposition. Reports never claim that
a commit, push, or merge occurred.

Claude Code may provide an explicitly enabled, read-only advisory review. Its output is
untrusted context and cannot mutate the worktree, approve a patch, or override verifiers.
Inspect runtime execution remains deferred until its upstream dependency set is compatible
with the repository's security policy; deterministic export remains supported.
