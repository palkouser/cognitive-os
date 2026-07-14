# Schema versioning

Every event payload declares a positive integer schema version. Event type names are
permanent. Compatible additions still require schema review and a regenerated snapshot.
Removed, renamed, or semantically changed fields require a new version and an explicit
migration path.

Migrations are registered by event type, source version, and target version. They operate on
copied JSON mappings and never mutate original event data. No event is upgraded or rewritten
without a registered path.

Tracked schemas under `schemas/v1` and representative fixtures under
`tests/fixtures/contracts/v1` are public compatibility artifacts.
