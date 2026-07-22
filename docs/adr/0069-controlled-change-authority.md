# ADR 0069: Controlled-change authority and approval separation

## Status

Accepted for Sprint 19.

## Decision

The Controlled Change service may consume one exact `approved_for_experiment` proposal revision,
create isolated evidence, and coordinate host-owned adapters. Proposal approval, isolation
approval, and promotion approval are distinct immutable records. Provider, model, candidate, and
experiment actors cannot approve promotion.

Change surfaces are classified as Tier 0 metadata, Tier 1 governed declarative state, Tier 2
repository content, or Tier 3 critical state. The Controller owns execution, the Tool Plane owns
side effects, destination registries own declarative revisions, and operators own repository
merge, tag, publish, and release actions. The operator-authorized Sprint 19 commit and protected
release workflow is external to Cognitive OS runtime authority.

## Alternatives and consequences

Reusing proposal approval for promotion and granting the runtime GitHub authority were rejected.
The additional approval step is deliberate; it prevents measured evidence from becoming authority.

## Verification

Lifecycle, actor, stale-hash, Tier 3, and runtime-capability tests fail closed.
