# Strategy Engine operations

Run credential-free registry inspection and the complete replay smoke path:

```bash
uv run python scripts/strategy.py registry
uv run python scripts/strategy.py select --strategy python-bug-fix --approve
uv run python scripts/strategy.py graph --strategy python-bug-fix --depth 3
uv run python scripts/strategy.py compare --strategy python-bug-fix --right-strategy type-correction
uv run python scripts/strategy.py export-graph --strategy python-bug-fix --format dot
uv run python scripts/strategy.py plan --strategy python-bug-fix --approve
uv run python scripts/strategy_smoke_test.py
```

The inspection CLI emits canonical JSON and never invokes a provider or tool. `--approve` supplies
the explicit cold-start approval for the credential-free seed. Graph export also supports
`--format dot` and `--format mermaid`.

Persistent lifecycle operations require the configured PostgreSQL and artifact stores. Every
transition requires an exact current revision, operator identity, and reason; verification emits
the mandatory verifier snapshot and promotion decision. For example:

```bash
uv run python scripts/strategy.py create strategies/python-bug-fix/strategy.yaml \
  --actor-id operator --reason "Initial governed import"
uv run python scripts/strategy.py stage STRATEGY_ID \
  --expected-revision 1 --actor-id operator --reason "Regression fixtures passed"
uv run python scripts/strategy.py verify STRATEGY_ID \
  --expected-revision 2 --actor-id operator --reason "Mandatory verifier bundle passed"
uv run python scripts/strategy.py history STRATEGY_ID
```

`revise`, `deprecate`, `supersede`, and `retract` use the same guarded append-only path. Statistics,
access, usage-report, and explicit rebuild-statistics commands require an exact strategy revision.
Execution, resume, and cancellation remain application commands because only the running Controller
adapter may invoke tools or providers. There is no history deletion command.

Apply migration `0005` and run PostgreSQL diagnostics through the existing isolated test database:

```bash
./scripts/postgres_migrate.sh
uv run python scripts/strategy.py health
./scripts/run_postgres_integration_tests.sh
```

Backup and isolated restore remain `backup_event_store.sh` and `restore_event_store.sh
--test-restore`. Their manifest includes strategy identity, revision, edge, selection, outcome, and
access counts plus a canonical strategy-history digest. Restore validates current projections,
outcome-to-selection lineage, hashes, and exact counts before succeeding.

Run the ten-case CI benchmark, forty-case seed suite, and CPU-only local baseline with:

```bash
uv run python scripts/benchmark_run.py --manifest benchmarks/manifests/sprint13-strategies-ci.yaml --mode strategy-replay --report-directory .tmp/sprint13-ci
uv run python scripts/benchmark_run.py --manifest benchmarks/manifests/sprint13-strategies-seed.yaml --mode strategy-replay --report-directory .tmp/sprint13-seed
uv run python scripts/strategy_scale_baseline.py --iterations 100
```
