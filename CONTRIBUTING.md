# Contributing to Cognitive OS

Thanks for helping improve LightAgent. The project values small, focused changes
that preserve the lightweight core and keep existing APIs compatible.

## Development Setup

```bash
uv sync --locked --all-groups --extra mcp
```

## Before Opening a Pull Request

Run the focused regression suite:

```bash
uv run pytest -q
uv run pytest tests/contract -q
./scripts/verify_distribution.sh
./scripts/verify_editable_install.sh
```

## Contribution Guidelines

- Keep default `agent.run()` behavior backward compatible unless a breaking
  change is explicitly approved and documented.
- Prefer focused modules and tests over adding more logic to `LightAgent/core.py`.
- Do not include credentials, local logs, generated build artifacts, or private
  tool implementations.
- For memory, MCP, tool loading, or code execution changes, include a short
  security note in the PR.
- Update README or `docs/` when behavior, configuration, or public APIs change.

## Reporting Issues

Please use the bug or feature templates when possible. Security issues should be
reported privately through GitHub Security Advisories.
