# Artifact verification

`./scripts/verify_artifact_store.sh` walks finalized blobs below the configured artifact root
and verifies that each file name equals its SHA-256 digest. Temporary files are excluded.
Application reads additionally compare expected size and hash from PostgreSQL metadata.

Orphan detection compares finalized filesystem keys with `artifact_blobs`. An orphan is safe
to retain for investigation; the Sprint 3 implementation does not delete it automatically.
