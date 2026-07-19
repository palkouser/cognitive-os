# ADR 0041: Skill Engine authority

## Status

Accepted for Sprint 12.

## Decision

PostgreSQL migration `0004` owns skill identities, immutable revisions, requirements, exact package
references, execution outcomes, statistics revisions, and access audits. The event store owns
lifecycle evidence. The artifact store owns package bodies, exports, verifier bundles, and large
regression reports. Filesystem packages are staging and interchange input only.

Only operator- or host-authorized services can stage, verify, deprecate, supersede, or retract a
skill. Imported and provider-authored content starts as draft. Promotion requires a complete
deterministic verification snapshot and an explicit promotion decision. Providers cannot select,
modify, promote, or execute a skill and cannot expand scope, sensitivity, permissions, or budgets.

The inherited root `skills/` tree remains non-authoritative donor content. Governed repository seed
packages live under `procedural_skills/` and enter authority only through the same import and
promotion path as external packages.

## Consequences and verification

History tables reject updates and deletes; `advance_skill` is the only optimistic current-pointer
transition. Health checks compare projections, packages, and migration head. Backup and restore
manifests include skill counts and a canonical revision-history digest.
