# Optional features

| Extra | Packages | Purpose | Default | Security status | Test command |
| --- | --- | --- | ---: | --- | --- |
| `browser` | none | Reserved for a supported browser adapter | Off | No dependency accepted | `uv sync --extra browser` |
| `cloud-aws` | boto3 | S3-compatible OSS upload tool | Off | Audited separately from core | `uv sync --extra cloud-aws` |
| `lightagent-legacy-memory` | mem0ai | Legacy external memory examples | Off | Experimental; known upstream advisories remain | `uv sync --extra lightagent-legacy-memory` |
| `mcp` | mcp | Explicit local STDIO MCP v1 client | Off | Stable v1 only; no automatic server installation | `uv sync --extra mcp` |
| `observability-langfuse` | langfuse | Optional tracing client | Off | Audited separately from core | `uv sync --extra observability-langfuse` |
| `provider-litellm` | litellm | Optional provider routing | Off | Version range constrained for compatibility | `uv sync --extra provider-litellm` |

Optional imports must fail with an actionable extra name. None of these packages is installed
by the default `uv sync --locked` workflow.
