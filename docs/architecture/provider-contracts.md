# Provider contracts

Provider-neutral contracts live in `cognitive_os.domain.provider` and
`cognitive_os.domain.model_requests`. They are strict, immutable Pydantic records that reject
unknown fields and serialize to JSON.

A request carries stable call, task-run, step, and correlation identifiers; the requested
model; text messages and system instructions; optional tool definitions; response format;
generation limits; timeout; and secret-key-safe metadata. Sprint 4 defines tools but never
executes them. Structured requests require a schema and responses are locally validated.

A normalized response records requested and resolved models, content, structured data,
tool calls, finish reason, token usage, measured latency, provider request ID, and warnings.
SDK objects and raw provider responses are prohibited. Capabilities state only verified
behavior; unknown numeric limits remain unset.
