# Provider artifact policy

Provider bodies remain outside event rows. `ProviderArtifactPolicy` supports `none`,
`normalized_only`, and `normalized_and_raw_sanitized`; the default is `normalized_only`.
Normalized requests and responses are canonical JSON artifacts stored through the Sprint 3
content-addressed artifact port and referenced by lifecycle events.

Request models reject secret-like metadata keys. Authorization headers, credentials, HTTP
client state, raw SDK objects, and secret environment variables are never artifacts. Raw
provider response storage remains disabled by default. Artifact persistence failures are
explicit and abort the execution lifecycle rather than silently dropping evidence.
