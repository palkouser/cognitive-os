# Dependency classification

## Direct runtime and optional dependencies

| Dependency | Category | Default | Owning module or use | Decision |
| --- | --- | ---: | --- | --- |
| HTTPX | core runtime | Yes | `LightAgent.core` | Keep in core |
| OpenAI | optional provider required by baseline runtime | Yes | `LightAgent.core` | Keep in core to preserve the pinned import and default provider |
| PyYAML | core runtime | Yes | `LightAgent.skills` | Keep in core |
| Pydantic | core runtime | Yes | Cognitive OS domain and event contracts | Validation, serialization, and JSON Schema generation |
| jsonschema | core runtime | Yes | MiniMax and Tool Plane schema validation | Bounded local validation of request-owned schemas; MIT licensed |
| MCP | MCP | No | Cognitive OS local STDIO client and legacy manager | Retain stable `mcp>=1.23,<2` optional extra |
| boto3 | cloud integration | No | `LightAgent.builtin_tools.nos` | Move to `cloud-aws` extra and lazy import |
| Langfuse | observability | No | optional trace client in `LightAgent.core` | Move to `observability-langfuse` extra |
| mem0ai | deferred legacy memory | No | upstream examples only | Keep extra empty; 0.1.70 has unresolved advisories and Memory Plane is out of scope |
| LiteLLM | deferred provider router | No | upstream optional module | Keep extra empty; fixed versions require incompatible OpenAI 2.x |
| browser-use | browser integration | No | documentation/examples only | Leave the `browser` extra empty until a supported adapter exists |
| Requests | removable | No | upstream example tool only | Remove from project dependencies |
| Loguru | removable | No | upstream examples only | Remove from project dependencies |
| Colorama | removable | No | No runtime import found | Remove from project dependencies |
| httpx-sse | removable | No | No direct runtime import; supplied transitively by MCP when needed | Remove direct declaration |
| pydantic-settings | removable | No | No runtime import found | Remove from project dependencies |
| SymPy | domain verification | No | Safe typed mathematics adapter | `verification-math` optional extra |
| z3-solver | domain verification | No | Typed logic adapter | `verification-logic` optional extra |
| Pint | domain verification | No | Sealed units and dimensions adapter | `verification-physics` optional extra |
| Inspect AI | evaluation adapter | No | Explicit benchmark-format export only | Keep `benchmark-inspect` empty until upstream accepts a security-fixed Click |
| pgvector | memory persistence | No | PostgreSQL exact-vector type and operators | `memory-postgres`; 0.8.2 server image, Apache-2.0, no ANN indexes |
| Sentence Transformers | local embeddings | No | Optional preconfigured local CPU model | `local-embeddings`; no download or GPU requirement in core |
| NetworkX | semantic graph analysis | No | Bounded exact claim-revision projection | `semantic-graph`; PostgreSQL and stdlib traversal remain authoritative |

`inspect-ai==0.3.246` constrains Click below the security-fixed release. Cognitive OS therefore
ships a dependency-free deterministic exporter and does not install the incompatible runtime.
The runtime dependency may be restored after Inspect AI accepts a fixed Click version.

## Dependency groups

| Group | Category | Packages | Purpose |
| --- | --- | --- | --- |
| `dev` | development | pre-commit, Ruff, mypy, types-PyYAML, types-jsonschema | Local quality workflow |
| `test` | testing | pytest, pytest-asyncio, pytest-cov, Hypothesis | Offline verification |
| `security` | development security | Bandit, detect-secrets, pip-audit | Security gates |
| `docs` | documentation | MkDocs, Material for MkDocs | Documentation build tooling |
| `postgres` | optional runtime | SQLAlchemy, asyncpg, Alembic | Durable event and artifact metadata |
| `observability-otel` | optional runtime | OpenTelemetry API, SDK, OTLP gRPC | Trace correlation |
| `memory-postgres` | optional runtime | SQLAlchemy, asyncpg, Alembic, pgvector | Governed memory persistence and exact vectors |
| `local-embeddings` | optional runtime | sentence-transformers and isolated transitive ML stack | Preconfigured local embedding models only |
| `memory-benchmarks` | optional benchmark | none | Credential-free deterministic memory fixtures |
| `semantic-graph` | optional runtime | NetworkX | Non-authoritative bounded graph analysis |

Every prior direct dependency has a final category and decision; none remains unknown.
