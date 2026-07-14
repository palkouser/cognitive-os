# Development environment

Use Python 3.12 and the committed uv lockfile:

```bash
uv sync --locked --all-groups
uv run python -c "import cognitive_os"
uv pip check
```

Install only the extras required by the task. The full upstream MCP regression suite uses:

```bash
uv sync --locked --all-groups --extra mcp
```

`requirements.txt` is no longer a supported project installation path.
