# Benchmark framework

```text
Manifest -> Sequential Case Runner -> Controller or Verifier -> Metrics -> Report Artifact
```

Manifests and cases are immutable, licensed, provenance-bearing, and content-hashed. Runs are sequential, seeded, bounded, and continue after isolated case errors by default. Reports include correctness, verification error, latency, resource, and safety metrics. The tracked seed suite contains 56 credential-free cases across generic, coding, mathematics, logic, physics, and controller domains.
