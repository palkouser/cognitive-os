# ADR 0017: Provider-neutral model execution

Status: Accepted

Date: 2026-07-14

Providers are stateless external executors behind an asynchronous Cognitive OS port.
Normalized requests, responses, capabilities, health records, stream events, and typed
errors are authoritative; SDK, HTTP, and subprocess objects cannot cross the adapter
boundary. Cognitive OS owns task state, durable history, retry state, and persistence.

Sprint 4 selection is explicit and static. The registry performs no discovery, scoring,
adaptive routing, fallback, voting, or orchestration. Provider request and response bodies
may be retained only as policy-controlled artifacts, while lifecycle events contain compact
identifiers, usage, latency, status, artifact references, and sanitized errors.

This preserves offline mock and replay execution and allows MiniMax and CLI-agent adapters
to share one application contract. Adaptive routing and provider-generated tool execution
are deferred.
