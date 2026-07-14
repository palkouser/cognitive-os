# ADR 0032: Benchmark artifacts and reproducibility

Status: Accepted

Benchmark cases and manifests are immutable and content-hashed. Runs record the manifest, configuration, Git revision, provider, Tool Registry, Verifier Registry, sandbox image, seed, timestamps, resources, and outcomes. Reports are content-addressed artifacts and lifecycle events remain in the existing event store; Sprint 7 adds no benchmark-specific database table. Large external datasets are optional, manual, licensed, and stored outside Git.
