# Sprint 2 report

Status: Implementation complete - remote CI and release pending

## Sprint goal

Establish a stable, provider-neutral, persistence-neutral, and versioned internal contract
layer for tasks, execution, model calls, tool calls, verification, and lifecycle events. This
sprint deliberately implements contracts only: no persistence, providers, tool execution,
controller behavior, memory, skills, or self-improvement logic is included.

## Domain model

Pydantic 2 is now a direct core dependency. Shared strict and immutable base models reject
unknown fields, validate defaults, normalize strings, and revalidate nested records. Public
contracts cover tasks, task runs, execution plans and steps, model-call and tool-call audit
records, verifier results, actors, errors, artifacts, and token usage. Provider SDK objects
and LightAgent internals are excluded from the contract surface.

## Identifier and timestamp policy

Domain identifiers are explicit UUID type aliases and are generated as UUID4 values.
Persisted timestamps must be timezone-aware and are normalized to UTC. Naive datetimes are
rejected. String enums use stable lowercase values, and persisted records use tuples where
ordered immutable collections are required.

## Task and execution contracts

`Task` and `TaskRun` enforce lifecycle-dependent timestamps, outcome, error, and waiting
state invariants. `ExecutionPlan` validates unique step identifiers, existing dependencies,
and an acyclic dependency graph. `ExecutionStep` validates lifecycle-specific start,
completion, retry, output, and error combinations. Transition helpers explicitly define
allowed task-run and execution-step state changes.

## Model and tool audit contracts

Provider-neutral model-call request and result records capture model selection, artifact
references, token usage, latency, retries, and structured failures without retaining SDK
responses. Tool-call request and result records capture authorization decisions, arguments,
outputs, timing, and execution errors without implementing authorization or execution.

## Verification contract

`VerifierResult` records the verifier identity, outcome, summary, optional score, evidence
artifacts, and a structured failure. Its validation rules keep success, failure, evidence,
and score combinations internally consistent.

## Event payloads

Thirty-nine explicit v1 payload models cover task and task-run changes, plans and execution
steps, checkpoints and resume, model calls, tool calls, verification, user approvals, and
user corrections. Event names follow the documented permanent
`<aggregate-or-component>.<past-tense-action>` convention. Payloads are immutable typed
models rather than arbitrary dictionaries.

## Event envelope

`EventEnvelope` records event identity, stream identity and version, event type and payload
schema version, UTC occurrence time, correlation and causation, actor, source component,
privacy classification, payload, and payload hash. Envelope construction resolves typed
payload metadata and computes integrity data. Validation rejects inconsistent event types,
invalid stream versions, and payload hash tampering.

## Serialization and hashing

Canonical JSON uses UTF-8, sorted keys, compact separators, normalized model output, and
rejects non-finite numbers. SHA-256 payload digests are computed from those canonical bytes,
making serialization and integrity checks deterministic across runs.

## Event catalog and migrations

The default catalog explicitly registers every supported `(event_type, schema_version)`
pair and distinguishes unknown event types from unsupported versions. Encoding and decoding
resolve concrete payload classes through this catalog. The migration registry is explicit,
stepwise, deep-copying, and fails when any requested version path is unavailable; it does
not silently rewrite event records.

## JSON Schema export

The schema registry exports ten public domain/envelope schemas and thirty-nine concrete
event payload schemas. Together with `schemas/manifest.json`, this produces 50 deterministic
tracked files. The manifest records the schema-set version, generator identity, model and
event mappings, file paths, and SHA-256 hashes. Export and `--check` modes are available
through the Python module and shell wrapper, and CI rejects schema drift.

## Compatibility fixtures

Nine human-readable v1 fixtures cover representative domain records and event envelopes.
Compatibility tests validate canonical round trips, strict unknown and missing-field
handling, enum casing, catalog resolution, schema versions, hash tampering, schema snapshots,
and digest changes after valid mutations. Bounded Hypothesis strategies exercise UUIDs, UTC
timestamps, tuples, artifacts, token usage, lifecycle combinations, execution graphs,
serialization, and hashing.

## Test results

- Domain tests: 160 passed.
- Event tests: 14 passed.
- Schema tests: 2 passed.
- Domain compatibility tests: 20 passed.
- LightAgent contract tests: 8 passed.
- Full repository regression: 280 passed.
- Ruff check and format check: passed for the owned source, tests, contracts, and scripts.
- mypy: passed for 37 Cognitive OS source files.
- Bandit: no findings.
- ShellCheck and Bash syntax validation: passed.
- Repository language policy and schema drift check: passed.
- Distribution build, isolated wheel installation, and editable installation: passed.
- GitHub PR CI: pending.

## Security status

The core dependency audit reports no known third-party vulnerabilities; the local
pre-release package is skipped because it is not published on PyPI. Pydantic 2.13.4 is an
approved MIT-licensed direct core dependency. The secret baseline records reviewed schema
and fixture digests as deterministic false positives; no credential was found.

## Known issues

- These contracts are not yet persisted; concurrency and replay semantics remain Sprint 3
  work.
- Dynamic JSON mappings at the event boundary are copied, validated, and serialized
  immediately, but Python mappings are not intrinsically deeply immutable.
- LightAgent remains a pinned repository-local donor and is not coupled to the contract
  implementation.

## Sprint 3 carry-over

- Implement the PostgreSQL-backed append-only event store.
- Implement optimistic stream concurrency.
- Persist and retrieve `EventEnvelope` records.
- Implement artifact storage references.
- Add event replay and stream reconstruction.
- Add OpenTelemetry correlation.

## Restore point

The donor runtime remains LightAgent v0.9.1 at
`8ea4db3c9d8791e0977eea2a4481824441b4ba82`. After green remote CI and review, the merged
Sprint 2 closure will be marked by the `sprint-2-baseline` tag and GitHub release.
