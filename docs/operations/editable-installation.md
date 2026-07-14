# Editable installation

Synchronize the development environment and verify that the import resolves through the
`src` layout:

```bash
uv sync --locked --all-groups
uv run python -c "import cognitive_os"
./scripts/verify_editable_install.sh
```

The verification script creates an isolated temporary environment, installs the repository
in editable mode, and rejects an import outside `src/cognitive_os`.
