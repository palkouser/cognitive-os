# ADR 0050: Experience candidate governance

## Status

Accepted for Sprint 14.

## Decision

The compiler can propose memory, semantic-observation, skill, strategy, failure-pattern,
routing-observation, benchmark-case, negative-example, and corpus-item candidates. Every candidate
starts as `proposed`, binds exact source and evidence references, propagates scope and sensitivity,
names a target schema, states limitations, and has a deterministic hash.

`validated` means only that compiler schema, provenance, authority, sensitivity, and verifier
checks passed. `routed` means a checksummed export was handed to a staging boundary. Neither status
means destination verification or promotion. Rejection, routing, and supersession append a new
candidate revision; history is never updated or deleted.

Exports contain candidate metadata, body, sources, evidence, generalizability, limitations,
verification, and a checksum manifest. Large bodies remain artifact-backed. Sprint 15 must validate
the destination schema, license, quality, duplication, and route policy before staging.

## Rejected alternatives

Direct memory writes, supported semantic claims, verified skills, active strategies, routing-policy
changes, benchmark-gate activation, and implicit status promotion were rejected as destination
authority violations.
