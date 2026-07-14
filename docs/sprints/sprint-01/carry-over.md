# Sprint 1 carry-over

## Restore editable installation

The upstream LightAgent packaging configuration fails editable installation because
setuptools detects multiple top-level packages in a flat-layout repository. Both
`uv pip install -e .` and its `--no-deps` variant fail before installation.

### Current workaround

- Install the pinned upstream requirements into `.venv`.
- Run the checkout from the repository root.
- Use `pytest.ini` to make the checkout importable during tests.
- Use `requirements-baseline.lock.txt` as the Sprint 0 environment record.

### Sprint 1 objectives

- Separate upstream and Cognitive OS package boundaries.
- Introduce explicit package discovery configuration.
- Establish a PEP 621 and uv-compatible project layout.
- Restore `uv sync` and editable installation.
- Preserve upstream contract-test compatibility.
- Review and reduce mandatory upstream dependencies, especially `mem0ai`, Langfuse, and boto3.
- Resolve or isolate the remaining `mem0ai` security advisories.
