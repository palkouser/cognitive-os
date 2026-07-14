# Sprint 1 report

Status: Implementation complete - remote CI and release pending

## Sprint goal

Normalize Cognitive OS packaging, restore editable installation, minimize the default
runtime dependency set, and protect the pinned LightAgent boundary without implementing new
runtime capabilities.

## Package architecture

Cognitive OS-owned code now lives under `src/cognitive_os`. Setuptools discovery includes
only `cognitive_os*`; the pinned `LightAgent` donor source remains repository-local and is
excluded from the Cognitive OS wheel and source distribution. ADR 0012 records the boundary.

## Editable installation

The Sprint 0 flat-layout failure was reproduced and captured. `uv pip install -e .` and the
isolated `scripts/verify_editable_install.sh` workflow now succeed, with imports resolving to
`src/cognitive_os`.

## Dependency isolation

The default environment contains HTTPX, OpenAI, and PyYAML as direct runtime dependencies.
Development, testing, security, and documentation tools use uv dependency groups. MCP,
boto3, Langfuse, LiteLLM, browser integration, and legacy memory use explicit extras and are
off by default.

## mem0ai remediation

`mem0ai` is absent from the default synchronized environment, and the default dependency
audit reports no known vulnerabilities. The opt-in `lightagent-legacy-memory` extra retains
Mem0 0.1.70 for compatibility and separately records its four known advisories. The feature
is disabled by default and remains experimental.

## Optional features

Each optional feature has an owner, package mapping, default state, security disposition,
and test command in `docs/architecture/optional-features.md`. Narrow lazy imports prevent
MCP and boto3 from being required by a default `LightAgent` import. Missing integrations
produce actionable extra names.

## Contract tests

Fifteen offline contract tests cover Cognitive OS dependency boundaries and the pinned
LightAgent import, LightFlow, tool registration and validation, runtime hooks, trace export,
checkpoint, retry, and resume contracts. No API key, internet, GPU, Docker, or external
database is used.

## Build results

`uv build` creates `cognitive_os-0.1.0.dev1-py3-none-any.whl` and
`cognitive_os-0.1.0.dev1.tar.gz`. The wheel installs into an isolated environment. Explicit
manifest and package discovery rules exclude LightAgent, tests, documentation, runtime data,
environment files, traces, and unrelated top-level directories.

## Test results

- Cognitive OS tests: 3 passed.
- LightAgent and dependency contract tests: 15 passed.
- Full repository regression: 84 passed.
- Ruff check and format check: passed.
- mypy: passed for 13 Cognitive OS source files.
- Bandit: no findings.
- ShellCheck and Bash syntax validation: passed.
- Repository language policy: passed.

## Security status

The default `pip-audit` reports no known third-party vulnerabilities. The secret baseline was
reviewed and updated for moved lines; no real credential was found. Direct dependency
licenses and approval status are documented. The legacy Mem0 audit remains explicitly
non-zero and isolated from core.

## Known issues

- LightAgent is intentionally repository-local rather than bundled in the Cognitive OS wheel.
- The legacy-memory extra retains four upstream Mem0 advisories and must not be enabled by
  default.
- Imported LightAgent donor files retain original-language content as a documented provenance
  exception; all new or changed Cognitive OS-owned content is English.

## Sprint 2 carry-over

- Define the installed adapter strategy if Cognitive OS must consume LightAgent outside a
  repository checkout.
- Replace or remove the vulnerable legacy-memory extra before production use.
- Revisit packaging license metadata when the project moves beyond the backlog-mandated
  pre-alpha metadata shape.

## Restore point

The donor runtime remains LightAgent v0.9.1 at
`8ea4db3c9d8791e0977eea2a4481824441b4ba82`. After green remote CI and review, the merged
Sprint 1 closure is marked by the `sprint-1-baseline` tag and GitHub release.
