# Python Coding Agent operations

## Inspect without executing repository code

Use an exact commit already present in the local Git object store:

```bash
uv run python scripts/coding_inspect.py \
  --repository /absolute/path/to/repository \
  --base-commit 0123456789abcdef0123456789abcdef01234567 \
  --rootless-docker
```

Exit code `0` means the Python 3.12, pytest, Ruff, MyPy, Git, and rootless-Docker profile is
supported. Exit code `2` is a typed profile mismatch. Inspection performs no checkout,
dependency installation, import, or repository code execution.

## Review an outcome

```bash
uv run python scripts/coding_report.py outcome.json --output outcome.md
```

Treat an `accepted` result as a reviewable patch, not as deployment authorization. Inspect the
archived unified diff and verifier evidence, then commit or merge manually under normal
repository policy. Never copy provider credentials into a repository or artifact directory.

## Recovery and cleanup

Only one Coding Agent worktree may be active. On interruption, classify the workspace before
resuming: clean or changed prepared worktrees can be reviewed; unexpected HEAD changes,
corrupt Git state, or ownership mismatch require manual review. Normal completion archives the
diff and removes the registered worktree. Cleanup failures are recorded separately and do not
rewrite the task's acceptance result.

The agent never runs `git commit`, `git push`, `git merge`, package installers, nested Docker,
or network clients. If those are required, stop the run and perform a separately authorized
operator workflow.
