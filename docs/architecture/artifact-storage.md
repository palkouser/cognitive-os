# Artifact storage

Artifact bytes use `sha256/<prefix>/<digest>` beneath a configured root. Logical keys are
relative and never expose host paths. Writes stream into a same-filesystem temporary file,
enforce a configurable size limit, flush, optionally fsync, and atomically rename. Existing
content is reused only after size verification; reads recalculate size and SHA-256.

PostgreSQL stores blob and artifact metadata. Multiple artifact IDs may reference one blob.
Bytes are written before metadata because the filesystem and PostgreSQL cannot share a
transaction. Metadata failure can therefore leave a safe orphan blob. Orphans are reported,
never automatically deleted after an uncertain failure.
