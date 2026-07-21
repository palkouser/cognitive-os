# Optional features

| Extra | Packages | Purpose | Default | Security status | Test command |
| --- | --- | --- | ---: | --- | --- |
| `browser` | none | Reserved for a supported browser adapter | Off | No dependency accepted | `uv sync --extra browser` |
| `cloud-aws` | boto3 | S3-compatible OSS upload tool | Off | Audited separately from core | `uv sync --extra cloud-aws` |
| `lightagent-legacy-memory` | none | Reserved legacy memory boundary | Off | Runtime removed because no stable advisory-free compatible release exists | `uv sync --extra lightagent-legacy-memory` |
| `mcp` | mcp | Explicit local STDIO MCP v1 client | Off | Stable v1 only; no automatic server installation | `uv sync --extra mcp` |
| `observability-langfuse` | langfuse | Optional tracing client | Off | Audited separately from core | `uv sync --extra observability-langfuse` |
| `provider-litellm` | none | Reserved provider-routing boundary | Off | Runtime deferred; fixed releases require OpenAI 2.x | `uv sync --extra provider-litellm` |
| `verification-math` | sympy | Typed symbolic mathematics verification | Off | Closed AST and bounded worker | `uv sync --extra verification-math` |
| `verification-logic` | z3-solver | Typed Boolean and arithmetic verification | Off | No raw SMT-LIB | `uv sync --extra verification-logic` |
| `verification-physics` | pint | Units and dimensional verification | Off | Sealed packaged registry | `uv sync --extra verification-physics` |
| `benchmark-inspect` | none | Explicit Inspect-compatible file export | Off | Runtime deferred because Inspect AI pins vulnerable Click | `uv sync --extra benchmark-inspect` |
| `semantic-graph` | NetworkX | Bounded exact revision graph analysis | Off | No execution of graph payloads; PostgreSQL remains authoritative | `uv sync --extra semantic-graph` |
| `corpus-dvc` | none | Evaluated content-versioning integration | Off | Rejected for Sprint 15; manifests and the artifact store already provide exact revisions without remote execution | N/A |
| `corpus-datatrove` | none | Evaluated large-scale corpus transformation | Off | Deferred; bounded deterministic standard-library transforms meet the current scale gate | N/A |
| `corpus-distilabel` | none | Evaluated provider-assisted dataset proposals | Off | Deferred; provider-authored labels cannot be authoritative and are unnecessary for the deterministic core | N/A |

Optional imports must fail with an actionable extra name. None of these packages is installed
by the default `uv sync --locked` workflow.
