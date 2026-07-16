# ADR 0038: Context Builder authority

## Status

Accepted for Sprint 11.

## Decision

The Context Builder is a host-controlled, deterministic projection service. Source systems remain
authoritative; a Context Request, retrieval trace, Context Bundle revision, and rendered context are
immutable artifacts. The existing event stream records lifecycle references. No Context Builder
state database is introduced.

```text
Controller -> Context Request -> source retrievers -> Context Bundle -> context verifiers
                     |                  |                    |
                     v                  v                    v
                artifact store   authoritative sources   provider request
                                      |                       |
                         event / memory / semantic /           v
                         artifact / repository / workspace   provider
```

Provider output cannot select retrievers, widen scope or sensitivity, change ranking weights,
grant permissions, alter budgets, write memory, or bypass verification. Retrieved prose is data,
never policy. Wiki text remains a derived rendering whose exact claim lineage is authoritative.

Context validation and immediate source-snapshot revalidation gate provider execution. Required
source failure, unsafe content, a stale mutable source, an invalid digest, or an unavailable required
verifier blocks the provider call. Optional retriever failure may produce a warning and a new bundle
revision. Recovery replays artifact and event references, validates immutable sources, and rebuilds
when mutable snapshots changed.

## Security test map

| Invariant | Test boundary |
| --- | --- |
| Retrieved text has no policy authority | instruction/data separation and adversarial rendering |
| Scope and sensitivity never widen | request/config validation and pre-hydration filtering |
| Secrets never reach bundle or trace | secret-safe hydration and trace-integrity verification |
| Every item has exact provenance | candidate validation and provenance verifier |
| Stale required sources block calls | source-snapshot revalidation and Controller integration |
| Invalid bundles block calls | required Context verifier bundle and model execution gate |

## Rejected alternatives

- A Context Builder database would duplicate authoritative state and complicate recovery.
- Provider-selected retrieval would turn untrusted output into policy.
- Automatic bundle-to-memory ingestion would create circular, ungrounded authority.
- Treating Wiki pages as evidence would break claim-revision lineage.

