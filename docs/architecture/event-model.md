# Event model

An `EventPayload` is a typed immutable description of one domain state change. Its stable
event type and positive schema version are class metadata and are not duplicated inside the
payload JSON.

An `EventEnvelope` is the persistence boundary for Sprint 3. It adds event identity, UTC
occurred and recorded times, stream identity and type, positive stream version, correlation
and optional causation IDs, actor, source component, privacy class, and a SHA-256 payload
digest. Stream version is independent of payload schema version.

Payload hashes cover the payload only. Canonical project JSON uses sorted keys, UTF-8, no
insignificant whitespace, and rejects NaN and Infinity. It is deterministic project JSON,
not a claim of RFC 8785 compliance.

Sprint 3 may store and retrieve envelopes and enforce optimistic stream concurrency. It must
not replace domain contracts with ORM types, silently rewrite events, or change payload
integrity semantics. OpenTelemetry correlation is a future adapter concern.
