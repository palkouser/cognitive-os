# Event store schema

The `cognitive_os` schema contains `event_streams`, `events`, `artifact_blobs`, and
`artifacts`. `event_streams` records immutable stream type and current version. `events`
stores queryable envelope fields plus database metadata, with unique event IDs and unique
`(stream_id, stream_version)` pairs.

`artifact_blobs` identifies one filesystem blob by SHA-256, size, and logical storage key.
`artifacts` gives a blob one or more domain identifiers and may link it to a source event.
Foreign keys use restrictive deletion behavior. JSONB stores actor and payload structures,
but integrity always uses canonical Sprint 2 JSON rather than JSONB key ordering.
