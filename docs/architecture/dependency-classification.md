# Dependency classification

## Direct runtime and optional dependencies

| Dependency | Category | Default | Owning module or use | Decision |
| --- | --- | ---: | --- | --- |
| HTTPX | core runtime | Yes | `LightAgent.core` | Keep in core |
| OpenAI | optional provider required by baseline runtime | Yes | `LightAgent.core` | Keep in core to preserve the pinned import and default provider |
| PyYAML | core runtime | Yes | `LightAgent.skills` | Keep in core |
| Pydantic | core runtime | Yes | Cognitive OS domain and event contracts | Validation, serialization, and JSON Schema generation |
| jsonschema | core runtime | Yes | MiniMax normalized structured output | Local validation of provider output against request-owned schemas; MIT licensed |
| MCP | MCP | No | `LightAgent.mcp_client_manager` | Move to `mcp` extra |
| boto3 | cloud integration | No | `LightAgent.builtin_tools.nos` | Move to `cloud-aws` extra and lazy import |
| Langfuse | observability | No | optional trace client in `LightAgent.core` | Move to `observability-langfuse` extra |
| mem0ai | memory legacy | No | upstream examples and user-supplied memory adapter | Move to `lightagent-legacy-memory` extra |
| LiteLLM | optional provider | No | `LightAgent.litellm_client` | Move to `provider-litellm` extra |
| browser-use | browser integration | No | documentation/examples only | Leave the `browser` extra empty until a supported adapter exists |
| Requests | removable | No | upstream example tool only | Remove from project dependencies |
| Loguru | removable | No | upstream examples only | Remove from project dependencies |
| Colorama | removable | No | No runtime import found | Remove from project dependencies |
| httpx-sse | removable | No | No direct runtime import; supplied transitively by MCP when needed | Remove direct declaration |
| pydantic-settings | removable | No | No runtime import found | Remove from project dependencies |

## Dependency groups

| Group | Category | Packages | Purpose |
| --- | --- | --- | --- |
| `dev` | development | pre-commit, Ruff, mypy, types-PyYAML, types-jsonschema | Local quality workflow |
| `test` | testing | pytest, pytest-asyncio, pytest-cov, Hypothesis | Offline verification |
| `security` | development security | Bandit, detect-secrets, pip-audit | Security gates |
| `docs` | documentation | MkDocs, Material for MkDocs | Documentation build tooling |
| `postgres` | optional runtime | SQLAlchemy, asyncpg, Alembic | Durable event and artifact metadata |
| `observability-otel` | optional runtime | OpenTelemetry API, SDK, OTLP gRPC | Trace correlation |

Every prior direct dependency has a final category and decision; none remains unknown.
