# ADR 0029: Verifier Registry and execution

Status: Accepted

Cognitive OS owns an explicit, freezeable Verifier Registry. Descriptors are immutable and separate from implementations; duplicate identities, invalid descriptor hashes, invalid configuration schemas, and post-freeze mutation are rejected. Capability matching and execution order are deterministic. Sprint 2 `VerifierResult` remains the terminal evidence contract.

Every execution persists `verifier.started` before running and exactly one terminal event. A missing terminal write is an uncertain outcome and is never retried automatically. Command-based verifiers use the Tool Plane and rootless sandbox. Parallel verifier execution is deferred.
