# Controlled-change security boundary

All proposals, provider output, candidate files, artifacts, and evaluation logs are untrusted.

- Intake requires an exact approved revision, exact predecessor review, passing verifier bundle,
  frozen source snapshot, and verified artifacts.
- Worktrees are detached, external, locked, path-scoped, and sandboxed. The active checkout is
  status-checked before and after candidate capture.
- Active database identities, connection URLs, credentials, and artifact namespaces are denied.
- Network is disabled by default; provider context contains opaque references, not host paths.
- Only typed operations and fixed host commands execute. Candidate text never becomes shell input.
- Evaluation definitions and manifests come from the baseline, not the candidate.
- Security, policy, migration, dependency, compatibility, recovery, or rollback failures are hard.
- Promotion approval cannot be supplied by the proposal reviewer used for isolation, a provider,
  model, candidate, or experiment.
- No runtime API or CLI operation merges, tags, publishes, or releases repository content.

Tier 3 includes authorization, grants, sandbox, verifier, migration, backup, credentials, and
release workflow changes. It has no declarative promotion adapter.
