# Telemetry correlation

Identifiers serve different purposes:

- `correlation_id` groups an application workflow;
- `trace_id` identifies an OpenTelemetry trace;
- `span_id` identifies one operation within that trace;
- `event_id` permanently identifies an event;
- `global_position` orders all stored events.

Trace and span IDs are stored beside, not inside, the event envelope. The default no-op
adapter generates nothing. The optional adapter uses a strict attribute allowlist and never
records payloads, prompts, model output, tool arguments, artifact bytes, credentials, or full
database URLs.
