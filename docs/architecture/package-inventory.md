# Package inventory

## Top-level directories

| Path | Type | Importable package | Runtime role | Target action |
| --- | --- | ---: | --- | --- |
| `.codex/` | Tool configuration | No | Local agent policy | Retain outside distributions |
| `.github/` | Repository automation | No | CI and contribution workflow | Retain outside distributions |
| `.vscode/` | Editor configuration | No | Developer workflow | Retain outside distributions |
| `LightAgent/` | Upstream Python package | Yes | Pinned donor runtime | Keep repository-local and exclude from the Cognitive OS wheel |
| `cognitive_os/` | Cognitive OS Python package | Yes | Sprint 0 package marker | Move to `src/cognitive_os/` |
| `docs/` | Documentation | No | Architecture and operations evidence | Retain outside distributions |
| `example/` | Upstream examples | Namespace-like | Demonstration only | Retain outside distributions |
| `infra/` | Infrastructure placeholder | No | Future operations assets | Retain outside distributions |
| `logs/` | Runtime directory marker | No | Ignored runtime output | Exclude from distributions |
| `mcp/` | Upstream MCP examples | Namespace-like | Optional integration examples | Retain outside distributions |
| `scripts/` | Executable tooling | No | Development verification | Retain outside distributions |
| `skills/` | Donor skill assets | Namespace-like | Optional runtime data | Retain outside distributions |
| `tests/` | Test suite | Namespace-like | Verification | Exclude from distributions |

## Current import roots

Before Sprint 1, both the repository root and `cognitive_os/` were import roots. The
repository root also exposed `LightAgent/` and several namespace-like directories to
automatic setuptools discovery. The target installation exposes only `src/cognitive_os`;
the checkout continues to expose the pinned `LightAgent` compatibility runtime.

## Current build backend

The Sprint 0 file mixed Poetry metadata with a setuptools build backend and did not provide
setuptools package discovery configuration. Sprint 1 standardizes on setuptools with an
explicit `src` package root.

## Editable-install failure

Setuptools rejected the flat layout because it discovered `mcp`, `logs`, `infra`, `skills`,
`LightAgent`, and `cognitive_os` as possible top-level packages. The captured failure is in
`docs/baseline/sprint-1-editable-install-before.txt`.

## Default dependencies

The old requirements path installed HTTP/provider libraries plus MCP, Langfuse, Mem0, and
boto3 unconditionally. The normalized core contains only the libraries required for the
repository-local LightAgent import and basic OpenAI-compatible runtime: HTTPX, OpenAI, and
PyYAML.

## Optional or legacy dependencies

MCP, AWS SDK support, Langfuse, LiteLLM, browser integration, and Mem0 legacy memory are
explicit optional features. Development, testing, documentation, and security tools are uv
dependency groups.

## Dependency vulnerabilities

The four Sprint 0 Mem0 advisories are removed from the default environment. The legacy
memory extra remains opt-in and experimental until its upstream advisories are resolved.

## Recommended target structure

```text
src/cognitive_os/       Cognitive OS distribution
LightAgent/             repository-local pinned donor runtime
tests/cognitive_os/     Cognitive OS package tests
tests/contract/         offline compatibility contracts
docs/                   architecture and operations records
scripts/                reproducible verification commands
```
