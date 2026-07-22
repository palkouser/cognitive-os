# ADR 0070: Controlled-change isolation and evaluation order

## Status

Accepted for Sprint 19.

## Decision

Repository candidates extend the Sprint 8 detached `WorkspaceManager`; no second Git runtime is
introduced. Worktrees are outside the active checkout, detached at an exact commit, locked per
experiment, path-scoped, sandboxed, and archived only after immutable diff capture. Configuration,
database clones, and Artifact Store namespaces use distinct opaque identities. Network is disabled
by default. Tools, providers, resources, retries, and side effects are allowlisted.

Evaluation order is baseline-owned: integrity, reproducible build, focused tests, target benchmark,
historical and unrelated-domain regression, security and policy, migration and schema, dependency
and packaging, performance and resources, then backup, restore, and rollback. Any hard failure
removes promotion eligibility without deleting evidence.

## Alternatives and consequences

Active-checkout mutation, candidate-owned gates, unrestricted network, and natural-language shell
execution were rejected. Isolation costs disk and setup time but keeps active state recoverable.

## Verification

Worktree lock/remove/repair, scope escape, configuration, database identity, artifact symlink,
matrix completeness, and hard-failure tests cover the boundary.
