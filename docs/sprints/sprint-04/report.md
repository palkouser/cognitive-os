# Sprint 4 report

Status: Complete

## Sprint goal

Implement provider-neutral model execution with deterministic offline providers, MiniMax M3
support, durable call history, and bounded Claude Code advisory mode.

## Provider contracts

Strict Pydantic contracts now define provider identity, capabilities, health, messages, tool
definitions, requests, responses, tool calls, and streaming events. The asynchronous
`ModelProvider` port is independent of provider SDK types. A typed, sanitized error taxonomy
covers configuration, authentication, rate limiting, timeouts, transport, malformed responses,
unsupported capabilities, cancellation, policy violations, and persistence failures.

## Provider registry

The static registry supports explicit registration, duplicate rejection, deterministic provider
selection, capability checks, disabled-provider rejection, and isolated health reporting. Sprint 4
does not perform adaptive routing.

## Mock provider

The asynchronous mock adapter supports deterministic responses, streams, health states, delays,
and typed failures without network or credentials.

## Replay provider

The replay adapter validates versioned JSON fixtures and replays deterministic complete and
streaming results. `scripts/provider_replay_test.py` provides a credential-free operational check.

## Retry and timeout policy

Retries are limited to explicitly retryable errors, bounded exponential backoff, configured
attempt limits, and jitter. Authentication, validation, policy, capability, malformed-response,
and persistence errors fail immediately. Complete calls and streams share a total deadline;
streaming retries stop after the first payload. Cancellation is propagated and recorded.

## Provider execution service

`ModelExecutionService` owns static selection, capability enforcement, retry, timeout,
cancellation, lifecycle persistence, artifact persistence, and globally ordered streaming events.
Provider adapters remain transport and mapping boundaries.

## Provider event persistence

Sprint 2 model-call lifecycle events are reused and persisted through the Sprint 3 event store.
Started, attempt, retry, success, failure, timeout, and cancellation paths are covered. PostgreSQL
integration tests verify ordered, contiguous lifecycle history and terminal-event uniqueness.

## Provider artifacts

Normalized request and response artifacts are stored through the artifact service. Recursive
sanitization removes secret-like keys and configured secret values before persistence. Raw provider
payload storage remains disabled by default.

## MiniMax integration

The MiniMax adapter uses the existing OpenAI-compatible SDK boundary, lazy client construction,
normalized request and response mapping, streaming text and tool deltas, typed SDK error mapping,
and no SDK-level retries. Import and ordinary CI execution require no API key and make no network
calls.

## MiniMax health and model discovery

Health uses the model-list endpoint and reports typed healthy, unavailable, or misconfigured
states. `scripts/provider_health.py` provides safe diagnostics. The local environment had no
MiniMax secret, so the live health and completion smoke tests were not run.

## MiniMax tool calls and structured output

Tool calls and structured output are normalized, locally JSON-Schema validated, and guarded by
explicit capability flags. These flags default to false until an enabled account and selected
model are verified live; unsupported requests fail before network submission.

## Claude Code advisory mode

The adapter is read-only and subprocess based. It uses an argument vector without a shell, an
explicit working directory and environment allowlist, bounded turns and timeout, process-group
termination, structured output parsing, and Git status comparison before and after execution.
Repository modification produces a typed policy violation. The local host did not contain the
`claude` executable, so the opt-in live advisory smoke test was not run.

## Test results

- Focused provider, contract, execution, configuration, and persistence tests: 53 passed.
- Full credential-free suite: 360 passed, 12 skipped.
- Full suite with isolated PostgreSQL: 370 passed, 2 skipped (the two opt-in live provider tests).
- Ruff, MyPy (82 source files), Bandit, ShellCheck, repository-language, schema-drift, and
  whitespace checks passed.
- Dependency compatibility, source distribution, wheel, editable-install, and distribution-install
  verification passed.
- Provider replay and safe health diagnostic commands passed.

The rootless PostgreSQL wrappers were also corrected: startup no longer changes a container-owned
data directory, and test reset now uses the administrative URL with a `psql`-compatible scheme.

## Security status

Secrets are loaded only by environment-variable reference. Local provider configuration is ignored,
diagnostic output is sanitized, subprocess execution is shell-free, raw provider responses are off
by default, and ordinary CI is offline and credential-free. Bandit and the repository secret hook
pass on the tracked change set.

## Known issues

- Live MiniMax completion, model discovery, tool-call, and structured-output behavior remains to be
  verified with a user-supplied account secret and enabled model.
- Live Claude Code authentication and advisory behavior remains to be verified on a host with an
  authenticated `claude` CLI.
- Exact tokenizer-based context counting is deferred; Sprint 4 uses a conservative configured
  context budget.
- Raw response persistence is intentionally disabled pending a provider-specific sanitization
  review.
- Setuptools reports that the existing license-table and license-classifier metadata must migrate
  to an SPDX expression before 2027-02-18.

## Sprint 5 carry-over

- Implement the typed Tool Registry.
- Implement tool risk and permission contracts.
- Implement safe local tool execution.
- Implement rootless Docker sandbox lifecycle.
- Implement MCP client integration.
- Persist tool-call lifecycle events through the event store.
- Add approval and policy enforcement.

## Restore point

- Baseline: Sprint 3 remediation commit `a4a1675` on `main`.
- Sprint branch: `feature/sprint-4-provider-layer`.
- Closure commit: the commit containing this report, with message
  `feat: implement provider-neutral model execution`.
- GitHub tracking: milestone `Sprint 4 – Provider Layer`, issues #77 through #100.
