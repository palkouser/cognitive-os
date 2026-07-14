# Coding verifiers

```text
Coding Verifier -> Tool Execution Service -> Rootless Sandbox -> Normalized Result
```

Pytest, Ruff, MyPy, and import verification use allowlisted sandbox tools and bounded arguments. File, diff, and dependency policies evaluate normalized manifests without network access. Source workspaces are mounted read-only; package installation, plugin loading, shell syntax, path traversal, `.git` writes, symlink escapes, and unbounded output are rejected.
