# ADR 0040: Context Bundle persistence

## Status

Accepted for Sprint 11.

## Decision

Each build persists four content-addressed artifacts:

| Artifact | Media type | Reference |
| --- | --- | --- |
| Context Request | `application/vnd.cognitive-os.context-request+json` | request artifact ID and digest |
| Retrieval trace | `application/vnd.cognitive-os.context-trace+json` | bundle trace reference |
| Context Bundle | `application/vnd.cognitive-os.context-bundle+json` | typed model-request reference |
| Rendered context | `text/vnd.cognitive-os.context` | typed model-request reference |

`context.build_requested`, `context.bundle_created`, `context.build_failed`, and
`context.bundle_attached` events own lifecycle history and carry IDs and hashes, never full source
content. Bundle revision one has no predecessor; later revisions name the immediately preceding
revision. A revision never overwrites an earlier artifact.

Replay validates the request, registry, ranking, estimator, trace, source-snapshot, bundle, and
rendered hashes. Immutable sources can regenerate the same bundle. A changed workspace, plan, or
task stream requires a new revision. Missing or stale required evidence fails closed.

Sensitive bundles follow the source retention ceiling and may be omitted by deployment retention
policy; traces contain metadata only. No bundle is ingested into memory automatically. Existing
artifact backup and event restore preserve audit evidence. Database migration `0004` remains
unnecessary until captured query plans demonstrate a missing index; it must never add context
content tables.
