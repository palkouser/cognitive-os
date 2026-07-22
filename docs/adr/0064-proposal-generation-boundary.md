# ADR 0064: Deterministic and provider-assisted generation

## Status

Accepted for Sprint 18.

## Decision

Deterministic templates are the credential-free baseline. Provider assistance is disabled by
default and may only draft bounded prose from host-selected sources. Host code validates type,
scope, citations, typed operations, risks, validation, rollback, and verifier results.

## Alternatives

Provider-authored patches, provider-selected sources, automatic provider fallback authority, and
an external optimizer as a second controller were rejected.

## Consequences

Availability failures fall back to deterministic generation. Authority or scope violations are
rejected and never silently accepted.

## Rollback and migration impact

Disabling provider assistance restores the full deterministic path without schema changes. No
generated output can execute commands or write a destination.
