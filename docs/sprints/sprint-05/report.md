# Sprint 5 report

Status: Complete

## Sprint goal

Implement the typed Tool Plane, policy and approval enforcement, rootless sandbox, provider bridge,
and explicit local MCP STDIO client.

## MiniMax live validation

Health, model discovery, bounded completion, normalized `math.add` tool call, and JSON-Schema output
passed against `MiniMax-M3` using the external mode-0600 secret file.

## Tool contracts

Strict descriptors, invocations, results, policy, approval, and sandbox contracts are exported as
versioned schemas.

## Tool Registry

Explicit registration, duplicate rejection, deterministic snapshots, provider filtering, and
freezing are implemented.

## Policy engine

R0/R1/R2/R3 defaults, deny-first evaluation, version checks, enabled-tool checks, and resolved path
containment are implemented.

## Approval model

Deny-all and deterministic preconfigured providers are available. Task-scoped typed decisions are
part of the controlled execution path.

## Tool Execution Service

Input validation, policy, approval, timeout, cancellation, output validation, and lifecycle events
are owned by one service.

## Tool event persistence

Existing Sprint 2 tool-call events are appended to contiguous Sprint 3 event-store streams.

## Tool artifacts

Normalized artifact references and bounded output contracts are retained; secret sanitization uses
the established artifact boundary.

## Read-only host tools

Bounded filesystem list/read/stat and non-sensitive system information are implemented without a
shell and with resolved-root enforcement.

## Rootless Docker sandbox

The Python 3.12 image is digest-pinned, uses UID/GID 10001, and is invoked with read-only root,
disabled network, dropped capabilities, no-new-privileges, and resource limits.

## Sandbox tools

Python, pytest, Ruff, and MyPy have an executable allowlist and reject package installation,
arbitrary `-c`, absolute paths, and traversal.

## Provider-to-tool bridge

Only provider-visible descriptors are exported, provider IDs are preserved in result messages, and
calls execute sequentially through the Tool Execution Service.

## MCP client

The stable optional MCP v1 SDK is used for explicit local STDIO sessions with absolute commands and
environment allowlists.

## MCP tool discovery

MCP names are collision-safe and namespaced; schemas are bounded and descriptions remain untrusted.

## MCP tool execution

MCP descriptors default to R2 and therefore require the normal policy and approval path.

## Security tests

Path escape, invalid and remote schemas, automatic installer commands, R3 denial, restricted Git
arguments, non-root identity, read-only root, disabled networking, dropped capabilities,
no-new-privileges, device absence, and resource limits are covered. A tracked local MCP server
verifies STDIO discovery, namespacing, calls, and shutdown without package installation or network.

## Test results

- Core and credential-free regression: 372 passed, 15 skipped.
- Full PostgreSQL, MCP STDIO, and rootless Docker regression: 385 passed, 2 skipped.
- MiniMax live health, model discovery, completion, tool call, and structured output: passed.
- Rootless sandbox build, smoke, inspection, and cleanup diagnostics: passed.
- Ruff, Ruff format, MyPy (112 source files), Bandit, ShellCheck, schema drift, repository language,
  dependency compatibility, dependency audit, source build, wheel installation, and editable
  installation: passed.

## Security status

No provider credential is tracked or printed. The external provider file and ignored local
configuration both have mode `0600`. Ordinary CI is credential-free. The sandbox image is pinned to
the OCI digest resolved on 2026-07-14. MCP commands are absolute, shell-free, environment-allowlisted,
and cannot invoke automatic package installers.

## Known issues

- Remote MCP transports, OAuth, resources, prompts, and sampling are intentionally deferred.
- Sprint 5 executes provider-proposed tools sequentially and does not implement an autonomous
  provider/tool loop.
- Generated-file collection is bounded by the artifact contract but richer workspace-diff packaging
  is deferred to the coding-task controller.
- The existing setuptools license metadata deprecation remains due before 2027-02-18.

## Sprint 6 carry-over

- Implement the Problem Representation Engine.
- Implement the Cognitive Controller state machine.
- Connect provider execution and tool execution into a bounded task loop.
- Implement acceptance criteria and verifier selection.
- Implement task interruption, continuation, and user clarification.
- Add coding, mathematics, physics, and logic problem extensions.

## Restore point

- Baseline: `sprint-4-baseline` at merge commit `4e54fd9`.
- Sprint branch: `feature/sprint-5-tool-plane`.
- Closure commit message: `feat: implement typed Tool Plane and sandbox execution`.
- GitHub tracking: milestone `Sprint 5 – Tool Plane and Sandbox`, issues S5-00 through S5-27.
