# Provider health checks

Run normalized health diagnostics without printing credentials:

```bash
uv run python scripts/provider_health.py --config config/providers.example.yaml
```

Output contains provider ID, kind, status, latency, configured model, resolved model, and a
safe message. Missing MiniMax credentials produce `misconfigured`; a disabled Claude Code
entry produces `unavailable` with a disabled message. Health checks never print API keys or
complete provider requests and responses.

Offline replay verification requires no provider or network:

```bash
uv run python scripts/provider_replay_test.py
```
