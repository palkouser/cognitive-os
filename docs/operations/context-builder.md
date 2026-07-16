# Context Builder operations

Run the credential-free end-to-end path:

```bash
uv run python scripts/context_smoke_test.py
uv run python scripts/context.py health
```

Create inspectable fixture artifacts and verify them without a provider call:

```bash
uv run python scripts/context.py build --output .tmp-benchmark-reports/context
uv run python scripts/context.py get --bundle .tmp-benchmark-reports/context/context-bundle.json
uv run python scripts/context.py trace --bundle .tmp-benchmark-reports/context/context-bundle.json \
  --trace .tmp-benchmark-reports/context/retrieval-trace.json
uv run python scripts/context.py sources --bundle .tmp-benchmark-reports/context/context-bundle.json
uv run python scripts/context.py exclusions --bundle .tmp-benchmark-reports/context/context-bundle.json \
  --trace .tmp-benchmark-reports/context/retrieval-trace.json
uv run python scripts/context.py warnings --bundle .tmp-benchmark-reports/context/context-bundle.json
uv run python scripts/context.py verify --directory .tmp-benchmark-reports/context
uv run python scripts/context.py regenerate --expected-hash <sha256>
```

Inspection omits source bodies except the separately retained rendered artifact. Health is read-only
and reports prohibited features. Regeneration performs no provider call. A stale mutable source,
missing artifact, hash mismatch, required verifier failure, or budget mismatch is an operator-visible
failure; the command never repairs or overwrites history.

Back up and restore Context artifacts through the existing content-addressed artifact backup and
event-store procedures. After restore, run `verify`, then `regenerate`; workspace snapshots may be
reported stale and must produce a new bundle revision.

