# ADR 0015: Content-addressed artifact storage

Status: Accepted

Artifact bytes use SHA-256 content-addressed local filesystem storage. PostgreSQL stores blob
and artifact metadata, and multiple artifact records may reference one blob. Writes stream
through a temporary file on the same filesystem and finish with an atomic rename. Reads
verify both size and content hash.

Filesystem and PostgreSQL transactions cannot commit atomically. Bytes are written first;
metadata failure may leave a safe, detectable orphan blob. Automatic deletion after an
uncertain failure is prohibited. Cloud and object-store adapters are deferred.
