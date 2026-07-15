# ADR 0034: Coding Agent authority and workspace boundary

Status: Accepted

## Context

Sprint 8 introduces repository mutation. Provider output and repository content are
untrusted, while the main working tree and Git administrative data must remain protected.

## Decision

The Coding Agent is a domain orchestration facade over the existing Cognitive Controller;
it is not a second general state machine. It uses the existing Model Execution Service,
Tool Plane, Verification Service, Acceptance Service, event store, artifact store, budgets,
checkpoints, and recovery mechanisms.

A trusted host repository service owns a narrow allowlist of shell-free Git operations and
creates detached worktrees. Providers cannot invoke Git, a shell, subprocesses, Docker, or
filesystem adapters directly. Providers produce only typed patch plans and patch proposals.
The Patch Service is the only component allowed to initiate writes, exclusively inside the
active detached worktree and through registered Tool Plane operations.

The worktree `.git` entry and the central repository `.git/worktrees` data are never
provider-visible or provider-writable. Only the trusted host service manages worktree
administrative state. Verification and acceptance remain provider-independent and
authoritative. Claude Code review is optional and advisory-only.

No Coding Agent workflow performs package installation, network access, commit, push,
merge, or pull-request creation.

## Alternatives rejected

- A second controller would duplicate budgets, recovery, and lifecycle authority.
- Direct provider filesystem or Git access would bypass Tool Plane policy and audit.
- Applying provider text as a shell patch would permit option, path, and command injection.
- Mutating the main checkout would make isolation and reliable recovery impossible.
- Letting a model judge accept a patch would weaken deterministic verification.

## Consequences

Repository preparation and cleanup are trusted host operations. Patch proposals require
strict parsing, path and dependency policy, cumulative budgets, atomic application, and
integrity evidence. A failed or uncertain write is never blindly repeated.
