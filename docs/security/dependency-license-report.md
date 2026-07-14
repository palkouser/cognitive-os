# Dependency license report

Reviewed on 2026-07-14 from locked package metadata and upstream package metadata.

| Package | Locked or constrained version | Group or extra | License | Approved | Notes |
| --- | --- | --- | --- | ---: | --- |
| HTTPX | 0.28.1 | core | BSD-3-Clause | Yes | Core HTTP client |
| OpenAI | 1.109.1 | core | Apache-2.0 | Yes | Baseline provider compatibility |
| PyYAML | 6.0.3 | core | MIT | Yes | Skill metadata parsing |
| Pydantic | 2.13.4 | core | MIT | Yes | Contract validation and schema generation |
| mypy | 1.20.2 | dev | MIT | Yes | Static analysis |
| pre-commit | 4.6.0 | dev | MIT | Yes | Local hooks |
| Ruff | 0.15.21 | dev | MIT | Yes | Lint and format gate |
| pytest | 8.4.2 | test | MIT | Yes | Test runner |
| pytest-asyncio | 1.4.0 | test | Apache-2.0 | Yes | Async tests |
| pytest-cov | 6.3.0 | test | MIT | Yes | Coverage integration |
| Hypothesis | 6.156.6 | test | MPL-2.0 | Yes | Property tests |
| Bandit | 1.9.4 | security | Apache-2.0 | Yes | Source security scan |
| detect-secrets | 1.5.0 | security | Apache-2.0 | Yes | Secret scan |
| pip-audit | 2.10.1 | security | Apache-2.0 | Yes | Dependency audit |
| MkDocs | 1.6.1 | docs | BSD-2-Clause | Yes | Documentation build |
| Material for MkDocs | 9.7.6 | docs | MIT | Yes | Documentation theme |
| boto3 | 1.43.47 | `cloud-aws` | Apache-2.0 | Yes | Optional AWS integration |
| MCP | 1.28.1 | `mcp` | MIT | Yes | Optional stable-v1 local STDIO Tool Plane integration |
| Langfuse | 3.15.0 | `observability-langfuse` | MIT | Yes | Optional observability |
| SQLAlchemy | 2.0.51 | `postgres` | MIT | Yes | Async Core database access |
| asyncpg | 0.31.0 | `postgres` | Apache-2.0 | Yes | PostgreSQL async driver |
| Alembic | 1.18.5 | `postgres` | MIT | Yes | Database migrations |
| OpenTelemetry SDK/exporter | 1.43.0 | `observability-otel` | Apache-2.0 | Yes | Optional traces |
| SymPy | 1.14.0 | `verification-math` | BSD-3-Clause | Yes | Optional typed symbolic verification |
| z3-solver | 4.16.0.0 | `verification-logic` | MIT | Yes | Optional typed logic verification |
| Pint | 0.25.3 | `verification-physics` | BSD-3-Clause | Yes | Optional units and dimensions |

The empty `browser` extra has no accepted direct dependency.

The 2026 Click advisory was remediated by resolving Click 8.4.2. Inspect AI 0.3.246 has a
stale upper bound that conflicts with the fixed version, so its runtime dependency is deferred.
The dependency-free exporter remains available and the locked environment reports no known
vulnerabilities with `pip-audit`.

The vulnerable mem0ai 0.1.70 and LiteLLM 1.80.0 runtimes were removed from the universal
lock. Their extra names remain reserved but empty. Memory and adaptive provider routing are
outside Sprint 7 scope and can return only after compatible, advisory-free releases exist.
