# Strategy Engine configuration

`config/strategies.example.yaml` contains the complete fail-closed Sprint 13 configuration. Limits
cover revisions, phases, branches, exact bindings, graph traversal, selection traces, Controller
plans, fallback depth, execution time, repairs, and statistics sample thresholds. Ranking weights
are fixed host configuration and use deterministic decimal arithmetic.

Deferred authority flags must remain `false`. Validation rejects provider-controlled selection,
automatic strategy creation or promotion, learned ranking, dynamic capability registration, and
external graph databases. Credentials, provider tokens, executable applicability rules, raw host
paths, and automatic permission expansion are invalid strategy content.

Production persistence uses the existing PostgreSQL, event-store, and artifact-store settings.
Strategy definitions under `strategies/` contain orchestration metadata and exact skill names only;
they must not repeat procedural skill instructions.
