# Operating the cross-domain pilot

Everything below runs offline, on CPU, with no credentials and no optional extras.

## Offline smoke test

```bash
uv run python scripts/domain_smoke_test.py --output artifacts/sprint-20/evidence/domain-smoke.json
```

Exits `0` only when all three domains accept every correct answer, reject every wrong answer, all 16
governance invariants hold, both transfer experiments are positive, and the negative-transfer
fixture is rejected. The JSON report carries the registry snapshot, the unit-registry hash, per-domain
counts, per-arm transfer deltas, and which optional extras are present.

## Benchmarks

```bash
uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-ci.yaml \
  --mode domain-pilot --output artifacts/sprint-20/benchmarks/ci.json

uv run python scripts/benchmark_run.py \
  --manifest benchmarks/manifests/sprint20-domain-seed.yaml \
  --mode domain-pilot --output artifacts/sprint-20/benchmarks/seed.json
```

- CI manifest: 24 cases — 6 mathematics, 6 physics, 6 logic, 6 transfer and governance.
- Seed manifest: 120 cases — 30 per domain plus 30 transfer, adversarial, and governance.

The adapter really executes each case and compares the observed disposition with the manifest
expectation, so a regression in a solver, checker, or gate fails the benchmark rather than passing a
declarative table.

## Tests

```bash
uv run pytest tests/cognitive_os/domains tests/cognitive_os/benchmarks/test_domain_adapter.py -q
```

## PostgreSQL

Migration `0012` is required; the expected Alembic head is `0012`.

```bash
cd infra/postgres
COGOS_DATABASE_ADMIN_URL=... uv run python -m alembic upgrade head
COGOS_DATABASE_ADMIN_URL=... uv run python -m alembic current   # 0012 (head)
```

Round trip, exercised in this sprint:

```bash
uv run python -m alembic downgrade 0011
uv run python -m alembic upgrade 0012
```

Opt-in integration tests:

```bash
COGOS_DATABASE_URL=... COGOS_DATABASE_ADMIN_URL=... \
  uv run pytest tests/integration/postgres/test_domain_postgres.py -q
```

The integration database name must end in `_test`; the fixture refuses to run otherwise.

## Optional extras

The mandatory path never needs these. Install them only to exercise the optional escalation
verifiers:

```bash
uv pip install 'sympy>=1.14,<2'          # verification-math
uv pip install 'pint>=0.25.3,<0.26'      # verification-physics
uv pip install 'z3-solver>=4.16,<5'      # verification-logic
```

With all three absent the suite reports 985 passed and 47 skipped; with all three present, 989
passed and 43 skipped. The difference is exactly the optional escalation verifiers, which skip
cleanly rather than failing.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| `UnsupportedProblemType` | task class is not registered | register it, or reject the case; do not widen a solver silently |
| `InexactError: square root is irrational` | task is outside exact rational scope | expected; the mandatory path never approximates |
| `BudgetExceededError` | a declared ceiling was crossed | raise the budget deliberately or reduce the input |
| `UnitError: incompatible units` | dimensional mismatch | fix the case; this is the check working |
| Disposition `unsupported` | a required verifier did not run | the plan requires a capability the checker never exercised |
| `record_domain_pilot_run` raises "different content" | immutable evidence would change | investigate; do not force the write |
| Health reports a revision mismatch | database is not at `0012` | run the migration |
