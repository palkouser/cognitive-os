# Controlled-change operations

## Credential-free checks

```bash
uv run python scripts/change_smoke_test.py
uv run python scripts/change_benchmark.py --manifest benchmarks/manifests/sprint19-change-ci.yaml
uv run python scripts/change.py health
```

Database health requires an isolated `_test` database configuration:

```bash
uv run python scripts/change.py health --database
```

Repository experiments use
`<configured-change-root>/<experiment-id>/worktree`. An interrupted worktree is inspected with
`git worktree list --porcelain` and repaired through the host-owned `repair` adapter. Cleanup unlocks
the worktree, captures artifacts, and then removes or archives it. Never manually delete a linked
worktree before recording repair metadata.

Database clones require a distinct test database, owner, runtime role, and URL. Teardown refuses an
active database identity. Artifact namespaces reject traversal and symlink roots.

Backup manifests contain Sprint 19 counts and a deterministic protected-history hash. Restore uses
the existing `--test-restore` path, refuses the active database, checks projection integrity, and
compares restored counts and hashes. Migration validation is `0010 -> 0011 -> 0010 -> 0011`.

Tier 1 promotion uses the destination service. Tier 0/2 bundles require the operator to revalidate
the exact hashes and use the protected repository workflow. Tier 3 reports manual review only.
