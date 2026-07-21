# ADR 0051: Corpus Factory authority

Status: Accepted

## Decision

The Corpus-to-Memory Factory is a deterministic, host-controlled transformation service. It may
inspect and normalize bounded local sources, retain provenance, assess policy, stage corpus items,
and emit versioned destination packages. It cannot mutate destination systems, promote candidates,
execute source material, upload data, or start model training.

PostgreSQL is authoritative for corpus metadata and access records, the artifact store owns large
content, and the event store owns lifecycle evidence. Destination owners retain all validation and
promotion authority.

## Rationale

Keeping transformation separate from acceptance prevents untrusted source or provider content
from acquiring authority merely by entering a corpus pipeline. Deterministic profiles and exact
revision references make decisions reproducible and auditable.

## Consequences

Unknown licensing, absent usage rights, secrets, ambiguous sensitivity, low quality, and unsafe
archives fail closed. Integrations require an explicit destination adapter and independent policy
decision. DVC, DataTrove, and Distilabel are not dependencies because the standard library and
existing project boundaries cover the Sprint 15 requirements with a smaller attack surface.
