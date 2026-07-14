# Running verifiers

List and inspect health:

```bash
uv run python scripts/verifier_list.py --include-unavailable
uv run python scripts/verifier_health.py
```

Run a pure verifier with a typed request:

```bash
uv run python scripts/verifier_run.py --verifier generic.exact --request-file request.json
```

Coding commands additionally require the approved rootless sandbox and Tool Plane configuration.
