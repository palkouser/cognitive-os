# ADR 0016: OpenTelemetry event correlation

Status: Accepted

OpenTelemetry is optional and an always-available no-op adapter is the default. Application
correlation IDs remain distinct from telemetry trace and span IDs. Trace and span IDs are
stored as database metadata rather than changing `EventEnvelope`.

Telemetry attributes use an explicit safe allowlist. Event payloads, prompts, model outputs,
tool arguments, artifact contents, credentials, and complete database URLs must never be
recorded. Telemetry failures must not affect persistence correctness.
