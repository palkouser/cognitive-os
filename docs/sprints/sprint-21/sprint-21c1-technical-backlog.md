# Sprint 21C1 Technical Backlog

## Persistent Learned Evidence and Governed Outcome Intake

**Document type:** implementation-ready technical backlog  
**Status:** ready for execution  
**Revision:** 1  
**Prepared:** 2026-07-26  
**Required parent baseline:** `sprint-21-substrate-baseline`  
**Required parent commit:** `e9001a9338c9507a60ca43f4e3e4bee7e28ef79b`  
**Required parent migration head:** `0013`  
**Implementation branch:** `feature/sprint-21c1-learned-evidence`  
**Target migration:** `0014_create_learned_evidence_store.py`  
**Target baseline tag:** `sprint-21c1-evidence-baseline`  
**Stage gate:** Gate C1 — Durable Learned Evidence  
**Successor gate:** Gate L2 remains closed until a later sprint demonstrates useful learned behaviour on real governed outcomes.
**Runtime baseline:** Python 3.12.13, PostgreSQL 18, pgvector 0.8.2, rootless Docker 29.6.2  
**Execution profile:** local, CPU-first, single-maintainer, credential-free normal CI  
**Repository language:** English only

---

## 0. Authority and execution contract

This backlog is the execution authority for Sprint 21C1. It refines:

- `docs/sprints/sprint-21/report.md`;
- `docs/sprints/sprint-21/gate-l-assessment.md`;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`;
- the Sprint 21R execution observations recorded after release.

If an implementation detail conflicts with a confirmed repository invariant, the implementer must:

1. preserve the invariant;
2. record the conflict and decision in the Sprint 21C1 report;
3. use an ADR before changing a persistence, authority, trust, or activation boundary;
4. avoid silently broadening the sprint.

Repository content, code, schemas, comments, logs committed as fixtures, and operational documentation must remain English-only.

### 0.1 Release-grade meaning of done

Sprint 21C1 is not complete when local tests pass. Completion requires:

1. verified parent tag and migration baseline;
2. implementation and migration;
3. local deterministic, PostgreSQL, migration, integrity, and backup/restore evidence;
4. a pull request with all required checks green;
5. merge to `main`;
6. successful post-merge `main` CI on the exact merged head;
7. a final evidence update that does not require a self-referential tag or commit;
8. one annotated target tag created on the final evidence commit;
9. local and remote tag-object and peeled-commit verification;
10. a complete Sprint 21C1 report and explicit Sprint 21C2 handoff.

The target tag must not be moved or recreated to add evidence that could have been kept in its annotation or linked externally.

---

## 1. Starting evidence

### 1.1 Verified Sprint 21R release state

Sprint 21R completed the deterministic learning substrate and Gate R0:

- `main`, `origin/main`, and the peeled `sprint-21-substrate-baseline` tag resolve to
  `e9001a9338c9507a60ca43f4e3e4bee7e28ef79b`;
- the final `main` CI run is `30209256649`, with conclusion `success`;
- Alembic head is `0013`;
- the final full local suite reported `1385 passed, 50 skipped`;
- the focused PostgreSQL suite reported `42 passed`;
- deterministic domain, seed, and coding benchmark cases all passed;
- no provider call, external network call, credential use, active model mutation, or GPU execution was required;
- Gate L remained a no-go because there was no active ML component, no durable learned artifact, no real learned sample, and no demonstrated material improvement.

### 1.2 Sprint 21R lessons that change Sprint 21C1 execution

The following are mandatory controls rather than optional process improvements:

1. **Open the implementation pull request early.** Sprint 21R accumulated four commits before pull-request CI ran. Two CI-only integration defects were consequently found late.
2. **Do not skip import failures.** If a CI lane exercises a PostgreSQL-backed learned module, that lane must install the declared PostgreSQL extra.
3. **Keep Alembic drift explicit.** Any raw-SQL index or function that Alembic cannot reflect exactly requires a narrow, named comparison rule and focused regressions. A broad object-class exclusion is prohibited.
4. **Use an isolated database and artifact root for release evidence.** The existing development database contains artifact metadata that does not match its current filesystem artifact root. The mismatch must be diagnosed, but it must not contaminate Sprint 21C1 release evidence.
5. **Do not assume required-review protection is available.** One approving review may be enabled only after a second eligible reviewer is confirmed. All other verified branch-protection controls remain mandatory.
6. **Do not create a self-referential release loop.** The tracked report must not require its own future merge SHA, final CI run, or final tag object. Those immutable handles belong in the tag annotation and external release evidence.
7. **Do not infer accelerator need from availability.** An NVIDIA RTX 5070 Ti was visible at closeout, but Sprint 21C1 is intentionally CPU-only and must not introduce a GPU dependency.

### 1.3 Operational prerequisite discovered after Sprint 21R

At backlog preparation time, public Git and workflow reads still resolved the release handles, but the active GitHub CLI credential returned HTTP 401 for authenticated API calls. This does not change the source baseline. It is a release-blocking operational prerequisite for:

- opening and updating the pull request;
- reading current branch protection;
- inspecting private/authenticated check detail;
- merging;
- publishing and verifying the release tag.

Credential reauthentication must occur before the first remote mutation. No token or credential value may be committed, printed into the report, or stored in a fixture.

---

## 2. Sprint goal and Gate C1 decision

### 2.1 Goal

Build the durable evidence layer that the existing learned contracts lack:

- persist learned component descriptors and lifecycle revisions;
- persist immutable dataset, artifact-lineage, evaluation, promotion, observation, activation, rollback, and access evidence;
- link large model or dataset bytes to the existing content-addressed Artifact Store;
- reconstruct current learned state after restart from authoritative history;
- accept governed outcome references through a deterministic harvester and quarantine unsuitable inputs;
- preserve real governed outcomes as evaluation-only data;
- provide integrity, health, migration, backup, restore, CLI, and CI evidence;
- keep runtime learned activation disabled by default.

### 2.2 Gate C1 pass condition

Gate C1 passes only when all of the following are true:

- migration `0014` is the single Alembic head;
- learned evidence survives process and database restart;
- replay of authoritative learned history reproduces the persisted current projection;
- duplicate writes are idempotent and conflicting reuse of an idempotency key fails closed;
- artifact lineage resolves through the existing Artifact Store and hash mismatch or missing content is visible as unhealthy;
- an accepted, quarantined, and rejected outcome can each be distinguished and audited;
- a real-governed-run record cannot enter a training snapshot;
- a fixture component can exercise register, shadow, verify, activate, disable, and rollback persistence without enabling a useful runtime model;
- activation is impossible without exact persisted promotion and human approval evidence;
- concurrent activation cannot create two active components for one surface;
- learned tables, grants, health checks, backup, restore, and migration downgrade/upgrade checks pass;
- credential-free CI remains deterministic;
- the release sequence in Section 0.1 is complete.

### 2.3 Gate L2 status

Gate C1 does not open Gate L2. The Sprint 21C1 report must state:

> Durable learned evidence is available, but useful learned behaviour has not yet been demonstrated.

The following remain future evidence:

- enough real governed outcomes for meaningful evaluation;
- a trained candidate with reproducible artifacts;
- material uplift over the deterministic ladder;
- zero unacceptable confident out-of-distribution errors;
- no catastrophic forgetting;
- production-safe shadow performance;
- explicit activation authorization for an actually useful component.

---

## 3. Scope boundaries

### 3.1 In scope

- additions to existing learned domain contracts where durable evidence requires them;
- learned persistence ports and application services;
- an in-memory repository for contract parity and fast tests;
- PostgreSQL table metadata, repository, health, and migration `0014`;
- lifecycle compare-and-swap and idempotency controls;
- immutable evidence and activation history;
- integration with the existing Event Store for correlated audit events;
- integration with the existing Artifact Store for bytes and content hashes;
- deterministic governed-outcome intake and quarantine;
- state replay, restart, corruption, and concurrency tests;
- migration, grants, schema export, backup, restore, CLI, CI, and operational documentation;
- a deterministic inert component fixture used only to prove lifecycle persistence.

### 3.2 Explicitly out of scope

- claiming that machine learning is optional to the Cognitive OS;
- training or activating a useful learned component;
- provider-backed data collection or live provider routing;
- OpenRouter, Claude Code, Codex, or other remote-model integration;
- automatic source-code modification or autonomous deployment;
- executable coding-corpus generation or sandboxed code scoring;
- learned tie-break routing;
- graph-memory or EMG implementation;
- embedding generation or semantic approximate-nearest-neighbour changes;
- GPU execution, CUDA dependencies, or accelerator benchmarking;
- processing a 200-outcome real corpus;
- a production shadow traffic decision;
- unsafe deserialization, including `joblib.load`, pickle loading, or execution of an artifact supplied as data;
- a second Event Store, Artifact Store, benchmark framework, promotion framework, or learned-state authority;
- destructive repair of the existing development artifact mismatch;
- enabling required approving reviews without a confirmed eligible second reviewer.

### 3.3 Deferral ownership

| Deferred capability | Owning sprint |
|---|---|
| governed OpenRouter, Claude Code, and Codex provider boundary | Sprint 21C2 |
| executable corpus, at least 200 governed outcomes including at least 50 coding outcomes, and local embeddings | Sprint 21C3 |
| first reproducible trained candidate and pre-registered learning surface | Sprint 21D1 |
| real shadow assessment and first useful activation decision | Sprint 21D2 |
| graph-backed experience integration | Sprint 22 |
| broader corpus and external provider integrations | later dedicated integration sprints |

---

## 4. Minimal architecture

### 4.1 Reuse before addition

Sprint 21C1 must reuse:

- `cognitive_os.domain.learned` for situation, dataset, component, prediction, invariance, forgetting, OOD, capacity, baseline-ladder, and promotion contracts;
- `cognitive_os.application.ports.learned` as the home of learned component, dataset, trainer, and artifact-facing ports;
- `LearnedComponentRegistry` transition rules as domain policy, while replacing its in-memory-only authority with a persistent application service;
- the existing PostgreSQL engine and repository conventions;
- the existing content-addressed `ArtifactService` and `artifacts` table for bytes;
- the existing Event Store and learned event family for correlated audit, extending
  that family only where an observation or lineage action has no valid existing
  event contract;
- the existing schema-export mechanism;
- the existing benchmark runner where a small adapter is sufficient;
- the existing PostgreSQL migration, drift, health, backup, and restore scripts;
- the existing controlled-change and domain-pilot patterns for immutable receipts, compare-and-swap, grants, and health reporting.

### 4.2 Authority model

There must be one authority for each concern:

| Concern | Authority |
|---|---|
| artifact bytes and base artifact metadata | existing Artifact Store |
| learned lifecycle history | append-only learned history tables |
| current learned component projection | learned component projection rebuilt from lifecycle history |
| learned domain invariants | learned domain contracts and registry policy |
| cross-subsystem audit stream | existing Event Store |
| benchmark results | existing benchmark result and artifact mechanisms |
| runtime activation lookup | persistent learned projection loaded through the learned service |

The Event Store is not a second learned-state authority. A missing correlated Event Store event is an integrity warning, while missing learned lifecycle history for a projection row is an integrity failure.

### 4.3 Transaction rule

Every learned state mutation must atomically:

1. validate the expected current revision;
2. append one immutable history row;
3. update the current projection;
4. return a hash-bound receipt.

The correlated Event Store event is emitted through the existing event service after the learned transaction. Health reporting must detect a missing or mismatched correlation. Sprint 21C1 must not introduce a distributed transaction or a second generic outbox framework.

### 4.4 Artifact rule

Learned persistence stores references and lineage, not large bytes:

```text
learned artifact lineage
        |
        v
existing artifacts.artifact_id
        |
        v
content-addressed Artifact Store bytes
```

Before registration, activation, or rollback:

- the artifact reference must exist;
- its observed content hash must equal the declared hash;
- its declared format and media type must be allowed;
- the service must treat the payload as inert data;
- no artifact loader may execute or deserialize untrusted object graphs.

`ArtifactFormat.JOBLIB` may remain a descriptive legacy enum value, but Sprint 21C1 must not load it.

### 4.5 Runtime rule

The default configuration contains no active learned component. Persistence support for activation does not authorize activation of an effective runtime model.

An inert deterministic fixture may enter `ACTIVE` only inside isolated tests that prove persistence and rollback. It must not be packaged as a default runtime component.

### 4.6 Expected package boundary

Use this package layout unless an existing adjacent module makes one file redundant:

```text
src/cognitive_os/
  domain/
    learned.py                         # existing learner and evaluation contracts
    learned_evidence.py                # new durable evidence-only contracts
  application/
    ports/
      learned.py                       # existing runtime learner ports
      learned_evidence.py              # new narrow persistence ports
    services/
      learned_evidence.py              # lifecycle, intake and activation policy
  events/
    learned_events.py                  # existing family plus narrow new payloads
    learned_event_service.py           # correlation with the existing Event Store
  infrastructure/
    learned/
      memory_repository.py             # deterministic contract reference
      postgres/
        __init__.py
        tables.py
        repository.py
        health.py
scripts/
  learned_evidence.py                  # safe operational CLI
infra/postgres/alembic/versions/
  0014_create_learned_evidence_store.py
config/
  learned.example.yaml
```

Do not move existing algorithms merely to match this tree. Dependency direction must remain:

```text
domain <- application ports/services <- infrastructure and scripts
```

Core import lanes must not import SQLAlchemy or a PostgreSQL driver unless the
PostgreSQL implementation is explicitly selected.

### 4.7 Configuration baseline

`config/learned.example.yaml` must be non-secret and safe by default. It must express:

- schema version;
- persistence enabled state;
- indirect use of existing `COGOS_DATABASE_URL` and `COGOS_ARTIFACT_ROOT`;
- an empty active-component declaration;
- activation mutation disabled for ordinary CLI use;
- accepted harvester source types;
- quarantine as the default for ambiguous or unverified intake;
- real-governed-run training disabled;
- bounded list, batch, and replay page sizes;
- event-correlation health policy;
- artifact allowed-format and media-type policy without enabling deserialization.

Do not introduce a second database URL, artifact root, provider credential, or GPU
configuration surface for Sprint 21C1.

---

## 5. Required persistence model

Migration `0014_create_learned_evidence_store.py` must create the following bounded model. A schema change requires an ADR and backlog/report update before implementation.

### 5.1 `learned_components`

Mutable current projection, updated only through controlled repository functions.

Required semantics:

- stable `component_id` primary key;
- `surface`, descriptor version, current revision, and current state;
- current artifact-lineage reference where applicable;
- current descriptor and content hashes;
- created and updated timestamps;
- one active component at most per surface;
- no direct `cogos_app` insert, update, or delete.

### 5.2 `learned_component_revisions`

Append-only authoritative lifecycle history.

Each row must contain:

- component and monotonic revision;
- previous revision or initial marker;
- state before and state after;
- descriptor and artifact-lineage references;
- optional promotion-assessment and activation-approval hashes;
- optional rollback target;
- actor, authority, reason, timestamp;
- canonical payload and content hash;
- idempotency key.

### 5.3 `learned_datasets`

Append-only dataset-snapshot metadata.

Required fields and invariants:

- dataset snapshot ID and surface;
- `CorpusRole`;
- feature-schema hash;
- split-manifest artifact reference and hash;
- example-manifest artifact reference and hash;
- provenance class counts;
- sensitivity and usage-rights metadata;
- canonical payload and content hash;
- `REAL_GOVERNED_RUN` provenance is forbidden when `corpus_role = TRAINING`;
- example bodies remain in the Artifact Store rather than JSONB rows.

### 5.4 `learned_artifacts`

Append-only learned lineage that references the existing Artifact Store.

Required semantics:

- lineage ID;
- existing `artifact_id`;
- owning component or dataset;
- declared `ArtifactFormat` and media type;
- declared and observed content hash;
- producing manifest or source evidence hash;
- lineage role such as dataset, split, model, report, or metric bundle;
- verified timestamp and verifier;
- no duplicated artifact bytes.

### 5.5 `learned_evidence_records`

One append-only typed evidence table rather than one table per domain contract.

The allowlisted `evidence_kind` values must cover:

- learned prediction;
- shadow result;
- mandatory-path invariance;
- forgetting assessment;
- distribution comparison;
- retrieval capacity;
- deterministic baseline ladder;
- OOD assessment;
- promotion assessment.

Each record must carry the relevant component, dataset, surface, source-run, schema, payload, and content hashes. Unknown evidence kinds fail validation.

### 5.6 `learned_observations`

Append-only governed-outcome intake and quarantine ledger.

Required semantics:

- stable observation ID;
- source task, run, event, and outcome references where available;
- source payload hash;
- provenance class;
- attribution: `direct`, `contributing`, or `unknown`;
- status: `accepted`, `quarantined`, or `rejected`;
- verifier status and verifier evidence hash;
- usage rights and sensitivity;
- quarantine or rejection reason;
- evaluation eligibility;
- canonical payload and content hash;
- idempotency key derived from source identity and observed content.

An accepted observation is not automatically a dataset example. A dataset snapshot requires a separate, immutable selection manifest.

### 5.7 `learned_activation_history`

Append-only activation authority and receipt ledger.

Allowlisted record kinds:

- approval;
- activation;
- disable;
- rollback.

Required semantics:

- exact component, surface, revision, and artifact-lineage identity;
- exact eligible promotion-assessment hash for activation;
- exact human approval hash for activation;
- previous activation reference;
- rollback target;
- actor, authority, reason, timestamp;
- canonical payload and content hash;
- a model or provider identity cannot be its own approver;
- a negative or mismatched approval cannot authorize activation.

### 5.8 `learned_accesses`

Append-only read and export audit for sensitive learned datasets and artifacts.

Required semantics:

- actor and authority;
- target type and target ID;
- purpose and decision;
- timestamp;
- canonical payload and content hash;
- no secret, raw credential, or sensitive example body in the audit payload.

### 5.9 Database controls

Migration `0014` must include:

- primary, foreign-key, check, and uniqueness constraints;
- partial uniqueness for one active component per surface;
- idempotency-key uniqueness at the correct scope;
- append-only update/delete rejection triggers for all immutable tables;
- controlled functions for component registration, lifecycle advance, evidence recording, observation recording, activation approval, activation/disable/rollback, and access audit;
- compare-and-swap on component revision and activation state;
- `cogos_owner` ownership and maintenance privileges;
- `cogos_app` read access plus execute access only to required controlled functions;
- no direct application mutation grant on the projection or immutable ledgers;
- downgrade support;
- no broad Alembic reflection exclusion.

---

## 6. Domain and service invariants

### 6.1 Required contract additions

Add only contracts that are absent from `cognitive_os.domain.learned`:

- `LearnedEvidenceKind`;
- `ObservationAttribution`;
- `ObservationStatus`;
- `LearnedObservationRecord`;
- `LearnedArtifactLineage`;
- `LearnedActivationAction`;
- `LearnedActivationApproval`;
- `LearnedActivationReceipt`;
- `LearnedAccessRecord`;
- repository result and conflict types where the common repository contracts are insufficient.

All new evidence-bearing contracts must be immutable, versioned, canonical-hashable, timezone-aware, and reject unknown enum values.

### 6.2 Existing contract invariants that must remain true

- a training snapshot cannot include `REAL_GOVERNED_RUN`;
- use rights are mandatory before dataset inclusion;
- ordinary component state transitions remain restricted by
  `LearnedComponentRegistry`;
- restoring a previously active component is a distinct rollback operation, never
  an unrestricted `DISABLED -> ACTIVE` transition;
- promotion eligibility requires invariance, acceptable forgetting, acceptable OOD behaviour, and material improvement;
- active lookup yields at most one component per surface;
- component and dataset hashes bind the full canonical payload;
- structured values remain finite and schema-bound.

### 6.3 Outcome harvester policy

The harvester may read references from existing governed tasks, decisions, tool outcomes, domain outcomes, and evaluation results. It must:

1. verify source identity and content hash;
2. classify provenance and attribution;
3. reject missing usage-rights information;
4. quarantine ambiguous, contradictory, sensitive, unverified, or incomplete records;
5. preserve accepted real-run records as evaluation-only;
6. record why each non-accepted record was quarantined or rejected;
7. be deterministic for the same source snapshot;
8. perform no provider call and no source-system mutation.

Synthetic fixtures must be labelled `SELF_PLAY` or `OPERATOR_SUPPLIED`; they must never be counted as real governed outcomes.

### 6.4 Activation policy

Activation must fail unless all of these exact identities match:

- component ID;
- component revision;
- surface;
- artifact-lineage ID and hash;
- eligible promotion-assessment ID and hash;
- positive human approval ID and hash.

Activation must also fail when:

- current revision changed after assessment;
- artifact verification is stale or mismatched;
- another component is already active for the surface and no atomic replacement was requested;
- the component is retracted;
- the actor lacks authority;
- approval comes from a provider or component identity;
- an idempotency key is reused with different content.

Rollback must use a separate domain operation. It may restore only the exact prior
activation referenced by the current activation chain, after re-verifying that
activation's artifact, promotion, and approval hashes. The generic registry
`transition` method must continue to reject `DISABLED -> ACTIVE`.

### 6.5 Replay policy

Replay starts from append-only learned history, not from mutable in-memory state. It must:

- process records in stable component/revision order;
- validate the hash chain and legal transitions;
- reproduce the current projection exactly;
- fail closed on a missing revision, broken predecessor, illegal transition, or hash mismatch;
- remain deterministic across repeated runs;
- be usable as a health check without mutating production state.

---

## 7. Detailed work items

## EPIC S21C1-E00 — Remote and baseline readiness

### S21C1-000 — Restore authenticated release control

**Priority:** P0  
**Depends on:** none  
**Output:** authenticated GitHub CLI session and recorded remote-read evidence

**Tasks**

1. Reauthenticate the GitHub CLI without exposing the credential.
2. Verify the active account and repository target.
3. Query `main` branch protection with `gh --repo palkouser/cognitive-os`.
4. Confirm the current open pull-request state.
5. Confirm whether a second eligible reviewer exists.
6. If a second reviewer exists, plan a separate protection change to require one approval.
7. If no second reviewer exists, record the limitation; do not weaken any existing protection.

**Acceptance**

- authenticated API reads succeed;
- no credential appears in terminal evidence, fixtures, commits, or report;
- branch-protection evidence is current rather than inherited from Sprint 21R;
- remote mutation remains blocked until this item passes.

### S21C1-001 — Verify and freeze the parent baseline

**Priority:** P0  
**Depends on:** S21C1-000 for remote API evidence; Git verification may proceed independently  
**Output:** baseline verification block in the Sprint 21C1 report

**Tasks**

1. Confirm a clean worktree before implementation.
2. Fetch `origin` and tags.
3. Verify local `main`, `origin/main`, and peeled `sprint-21-substrate-baseline`.
4. Verify annotated tag object and signature metadata available to the repository.
5. Verify migration head `0013`.
6. Re-run the repository language check and a minimal learned import/contract smoke.
7. Create `feature/sprint-21c1-learned-evidence` from the verified parent.

**Required command family**

```bash
git fetch origin --prune --tags
git status --short --branch
git remote -v
git rev-parse main
git rev-parse origin/main
git rev-parse 'sprint-21-substrate-baseline^{}'
git ls-remote origin main refs/tags/sprint-21-substrate-baseline \
  'refs/tags/sprint-21-substrate-baseline^{}'
gh auth status
gh --repo palkouser/cognitive-os pr list --state all
gh --repo palkouser/cognitive-os run view 30209256649
```

Use the repository migration tooling to confirm the single head. Do not create the
feature branch from a symbolic or unverified tag.

**Acceptance**

- every source handle resolves to the declared parent commit;
- any deviation stops implementation and is explained;
- the branch has no unrelated carried changes.

### S21C1-002 — Isolate the development Artifact Store mismatch

**Priority:** P0  
**Depends on:** S21C1-001  
**Output:** diagnostic inventory and isolated Sprint 21C1 database/artifact environment

**Tasks**

1. Run read-only artifact verification against the existing development pair.
2. Inventory missing content, orphan files, and metadata/hash disagreement.
3. Do not delete, rewrite, or silently repair either side.
4. Define a recoverable remediation proposal for later operator approval.
5. Create a fresh, consistent PostgreSQL database and Artifact Store root for Sprint 21C1 evidence.
6. Record exact non-secret environment handles in the report.

**Acceptance**

- release evidence never uses the inconsistent pair;
- the original mismatch remains recoverable;
- the isolated pair passes existing artifact health before migration `0014`.

### S21C1-003 — Record the learned-evidence authority ADR

**Priority:** P0  
**Depends on:** S21C1-001  
**Output:** one ADR covering persistence and authority boundaries

**Tasks**

1. Record the authority table from Section 4.2.
2. Record why one generic typed evidence table is used.
3. Record why artifact bytes remain in the existing Artifact Store.
4. Record lifecycle transaction, replay, event-correlation, and failure semantics.
5. Record activation approval and rollback authority.
6. Record the prohibition on unsafe deserialization.
7. Record Gate C1 versus Gate L2.

**Acceptance**

- the ADR introduces no parallel platform;
- authority and failure behaviour are testable;
- any implementation deviation updates the ADR before code merge.

## EPIC S21C1-E01 — Contracts, ports, and package boundary

### S21C1-010 — Add minimal durable-evidence contracts

**Priority:** P0  
**Depends on:** S21C1-003  
**Output:** immutable contracts in `src/cognitive_os/domain/learned.py` or a focused adjacent learned module

**Tasks**

1. Add the contract set from Section 6.1.
2. Reuse existing timestamp, canonicalization, validation, and hash helpers.
3. Bind IDs, hashes, schema versions, authority, and reasons.
4. Reject non-finite numeric values and naive timestamps.
5. Reject unknown evidence, attribution, status, and activation action values.
6. Keep real-run evaluation-only validation in the domain layer.
7. Clarify in learned-domain documentation that machine learning is a mandatory
   Cognitive OS product capability while each particular model and its activation
   remain replaceable and governed.
8. Add a narrow rollback policy function or method that accepts only an exact
   previous activation receipt without broadening ordinary registry transitions.

**Acceptance**

- valid round trips preserve canonical hashes;
- one-field mutation changes the hash;
- invalid rights, timestamps, hashes, or enum values fail at construction;
- no duplicate replacement for an existing learned contract is added.
- no documentation can be read as making the learning plane optional or authorizing
  an unproven component.

### S21C1-011 — Export schema and compatibility fixtures

**Priority:** P0  
**Depends on:** S21C1-010  
**Output:** generated schemas and backwards-compatibility fixtures

**Tasks**

1. Register new contracts with the repository schema exporter.
2. Regenerate tracked schemas.
3. Add representative valid and invalid payload fixtures.
4. Add a schema drift check to the focused learned test lane.

**Acceptance**

- `python -m cognitive_os.schemas.export --check` passes;
- previously exported learned schemas remain compatible unless the ADR declares a versioned break;
- fixtures contain no secret or sensitive real payload.

### S21C1-012 — Define learned evidence repository ports

**Priority:** P0  
**Depends on:** S21C1-010  
**Output:** narrow persistence and replay ports

**Tasks**

1. Define operations for component registration and compare-and-swap transition.
2. Define immutable dataset, artifact-lineage, evidence, observation, activation, and access writes.
3. Define exact retrieval and listing operations required by the application service.
4. Define replay and integrity inspection.
5. Define idempotent success, stale revision, conflict, not-found, and integrity errors.
6. Avoid a generic CRUD repository.

**Acceptance**

- every method maps to a required Sprint 21C1 use case;
- the in-memory and PostgreSQL implementations can share one contract suite;
- no port exposes arbitrary SQL, untyped payload writes, or direct state replacement.

### S21C1-013 — Add the learned evidence application service

**Priority:** P0  
**Depends on:** S21C1-012  
**Output:** one service enforcing lifecycle, artifact, and activation policy

**Tasks**

1. Compose existing registry policy with the persistence port.
2. Validate Artifact Store references before lineage registration.
3. Enforce real-run evaluation-only policy.
4. Enforce exact promotion and approval linkage.
5. Emit existing learned Event Store events with correlation IDs.
6. Return immutable receipts.
7. Keep runtime activation disabled unless explicitly invoked by an authorized caller.

**Acceptance**

- callers cannot bypass domain transitions through the service;
- every mutation returns a stable receipt;
- event correlation failures are observable;
- the service performs no provider, network, or artifact execution.

### S21C1-014 — Implement learned event correlation

**Priority:** P1  
**Depends on:** S21C1-013  
**Output:** learned event service using existing event contracts and Event Store

**Tasks**

1. Add a focused event service instead of embedding append logic in every caller.
2. Map persisted actions to existing learned event types where their semantics
   match exactly.
3. Add narrow, backwards-compatible payload classes and event types for observation
   recording, artifact-lineage linking, activation approval, and rollback; do not
   make a placeholder component ID mandatory for an observation.
4. Include the relevant component or observation identity, surface, content hash,
   actor, authority, reason, and correlation ID.
5. Make retry idempotent under existing Event Store rules.
6. Register new event payloads in the existing schema and event-model exports.
7. Add integrity queries for missing or mismatched correlated events.

**Acceptance**

- no second event store exists;
- event replay order is stable;
- a learned lifecycle record remains authoritative even when event correlation is unhealthy;
- health output distinguishes warning from projection/history corruption.

## EPIC S21C1-E02 — In-memory reference implementation

### S21C1-020 — Implement the in-memory repository

**Priority:** P0  
**Depends on:** S21C1-012  
**Output:** deterministic in-memory learned-evidence repository

**Tasks**

1. Implement every port method.
2. Preserve append-only history.
3. Enforce revision compare-and-swap.
4. Enforce idempotency and conflicting-reuse rejection.
5. Rebuild current state from history rather than copying the projection.
6. Provide deterministic snapshots for tests.

**Acceptance**

- shared repository contract tests pass;
- replay and direct state agree;
- stale concurrent transition fails;
- duplicate identical request returns the original receipt;
- duplicate key with different content fails.

### S21C1-021 — Prove lifecycle and activation policy with an inert fixture

**Priority:** P0  
**Depends on:** S21C1-013, S21C1-020  
**Output:** credential-free lifecycle integration fixture

**Tasks**

1. Register an inert reference component.
2. Record shadow, invariance, forgetting, OOD, and promotion evidence.
3. Demonstrate rejection with missing or mismatched approval.
4. Add an exact positive test approval.
5. Activate, disable, and roll back the fixture in isolated state.
6. Restart the service and reconstruct the same state.

**Acceptance**

- the fixture never becomes a shipped default active component;
- activation without exact evidence fails;
- rollback restores the expected prior state;
- the test does not claim accuracy uplift or Gate L2 success.

## EPIC S21C1-E03 — PostgreSQL learned evidence store

### S21C1-030 — Define SQLAlchemy Core table metadata

**Priority:** P0  
**Depends on:** S21C1-003, S21C1-010  
**Output:** learned table metadata under `src/cognitive_os/infrastructure/learned/postgres/`

**Tasks**

1. Define the eight tables in Section 5.
2. Reuse repository naming, JSONB, timestamp, hash, and index conventions.
3. Keep the projection separate from append-only ledgers.
4. Add narrow constraints for evidence and activation kinds.
5. Add table exports required by health and migration checks.

**Acceptance**

- metadata imports without a live PostgreSQL dependency in core-only lanes;
- all required keys and constraints have stable names;
- no table stores large artifact bytes;
- no speculative table is added.

### S21C1-031 — Create migration `0014`

**Priority:** P0  
**Depends on:** S21C1-030  
**Output:** `infra/postgres/alembic/versions/0014_create_learned_evidence_store.py`

**Tasks**

1. Create all learned tables, indexes, constraints, triggers, and controlled functions.
2. Set revision parent to `0013`.
3. Add grants for `cogos_owner` and `cogos_app`.
4. Add downgrade in reverse dependency order.
5. Update the shared expected migration revision from `0013` to `0014`.
6. If reflection needs an exclusion, list exact object names and add a regression for each.

**Acceptance**

- upgrade from `0013` to `0014` succeeds;
- clean upgrade from base succeeds;
- downgrade to `0013` and re-upgrade succeeds;
- Alembic reports one head;
- `alembic check` reports no unintended operations;
- grants and controlled functions work under the application role.

### S21C1-032 — Implement the PostgreSQL repository

**Priority:** P0  
**Depends on:** S21C1-031  
**Output:** PostgreSQL implementation of the learned persistence ports

**Tasks**

1. Map all contracts without lossy conversion.
2. Call controlled functions for mutations.
3. Translate database conflicts into domain repository errors.
4. Preserve canonical payload and content hashes.
5. Implement stable reads and pagination where required.
6. Support replay and integrity inspection.

**Acceptance**

- shared repository contract tests pass unchanged;
- application-role tests cannot directly mutate protected tables;
- transaction rollback leaves neither partial history nor projection;
- retrieval ordering is deterministic.

### S21C1-033 — Enforce activation concurrency and rollback

**Priority:** P0  
**Depends on:** S21C1-032  
**Output:** concurrency-safe persistent activation path

**Tasks**

1. Add compare-and-swap to activation and replacement.
2. Enforce one active component per surface with a database constraint.
3. Bind activation to exact persisted promotion and approval evidence.
4. Store the previous activation reference.
5. Verify the previous activation's artifact, promotion, and approval lineage before
   rollback.
6. Perform rollback through the explicit rollback operation, not the generic
   component transition API.
7. Add two-session race tests.

**Acceptance**

- exactly one of two conflicting activations succeeds;
- no transient committed state contains two active components for a surface;
- a stale rollback target fails;
- generic `DISABLED -> ACTIVE` still fails;
- successful rollback creates a new receipt and does not rewrite history.

### S21C1-034 — Add learned persistence health

**Priority:** P0  
**Depends on:** S21C1-032, S21C1-014  
**Output:** learned section in the shared PostgreSQL health report

**Required checks**

- migration revision equals `0014`;
- required tables, triggers, functions, grants, and indexes exist;
- no projection row lacks lifecycle history;
- projection equals deterministic replay;
- revision sequences have no gap;
- immutable payload hashes verify;
- artifact references exist and hashes agree;
- at most one active component exists per surface;
- active records have exact promotion and approval evidence;
- real governed outcomes do not appear in training datasets;
- correlated Event Store gaps are counted separately;
- quarantined and rejected observations remain auditable.

**Acceptance**

- healthy fresh state reports zero integrity failures;
- each injected defect changes the expected health field;
- health is read-only;
- existing subsystem health remains compatible after revision bump.

## EPIC S21C1-E04 — Artifact lineage and governed outcome intake

### S21C1-040 — Integrate learned lineage with the existing Artifact Store

**Priority:** P0  
**Depends on:** S21C1-013, S21C1-032  
**Output:** verified artifact-lineage adapter

**Tasks**

1. Store bytes through the existing `ArtifactService`.
2. Record learned lineage only after observed hash verification.
3. Verify media type and declared format.
4. Reject missing, corrupted, or mismatched content.
5. Expose read-only verification for health and CLI.
6. Ensure no code path calls unsafe object deserialization.

**Acceptance**

- identical bytes deduplicate through the existing store;
- learned lineage never duplicates bytes;
- bit corruption is detected;
- a `JOBLIB` or pickle-like payload remains inert and is never loaded;
- missing artifact content prevents activation and rollback.

### S21C1-041 — Implement governed outcome intake

**Priority:** P0  
**Depends on:** S21C1-013, S21C1-032  
**Output:** deterministic observation harvester

**Tasks**

1. Accept source references from existing governed result surfaces.
2. Resolve source hashes without modifying source records.
3. Classify provenance and attribution.
4. Validate usage rights, sensitivity, verifier evidence, and completeness.
5. Accept, quarantine, or reject with a stable reason code.
6. Persist idempotently and emit a correlated learned event.

**Acceptance**

- repeated intake of the same source yields the same observation receipt;
- changed content under the same source identity fails closed;
- ambiguous attribution is quarantined;
- missing rights are rejected;
- no fixture is misclassified as a real governed run.

### S21C1-042 — Build immutable dataset selection manifests

**Priority:** P0  
**Depends on:** S21C1-040, S21C1-041  
**Output:** deterministic evaluation dataset snapshot builder

**Tasks**

1. Select only eligible observation IDs.
2. Sort selection deterministically.
3. Store example and split manifests in the Artifact Store.
4. Bind feature-schema and split hashes into the dataset snapshot.
5. Record provenance counts and rights evidence.
6. Reject real-run training snapshots at both domain and database layers.

**Acceptance**

- the same inputs produce the same manifest and dataset hash;
- different membership or split changes the hash;
- real-run observations can form an evaluation snapshot;
- real-run observations cannot form a training snapshot;
- raw examples are not duplicated into dataset-table JSONB.

### S21C1-043 — Add quarantine review and access audit

**Priority:** P1  
**Depends on:** S21C1-041  
**Output:** controlled review and read-audit path

**Tasks**

1. List quarantined observations by reason without exposing sensitive bodies.
2. Require an authorized, reasoned decision to produce a replacement accepted or rejected record.
3. Preserve the original quarantine record.
4. Audit sensitive dataset, manifest, and artifact reads.
5. Prevent a component or provider identity from reviewing its own evidence.

**Acceptance**

- review appends evidence and never rewrites quarantine history;
- unauthorized review fails;
- sensitive reads produce access records;
- list output is bounded and redacted.

## EPIC S21C1-E05 — Operations, backup, and restore

### S21C1-050 — Add a safe learned-evidence CLI

**Priority:** P1  
**Depends on:** S21C1-034, S21C1-040, S21C1-041  
**Output:** credential-free operational CLI and smoke script

**Required commands**

- `health`;
- `component show`;
- `component history`;
- `evidence verify`;
- `artifact verify`;
- `observation list`;
- `observation quarantine`;
- `replay verify`;
- `smoke`.

Activation, approval, and rollback mutation commands are not required in Sprint 21C1. Tests may call the application service directly.

**Acceptance**

- commands are read-only except for an explicitly isolated `smoke` fixture;
- JSON output is stable and machine-readable;
- output contains no secret or raw sensitive example body;
- non-zero exit status distinguishes unhealthy, not-found, and invalid usage.

### S21C1-051 — Extend backup and restore

**Priority:** P0  
**Depends on:** S21C1-031, S21C1-034  
**Output:** learned evidence included in the shared event-store backup contract

**Tasks**

1. Add learned table counts and content-hash summaries to the backup manifest.
2. Include learned tables in backup and restore verification.
3. Include referenced artifact integrity in the manifest without duplicating artifact bytes.
4. Restore into a fresh isolated database and artifact root.
5. Compare pre-backup and post-restore replay and health.
6. Add a missing-artifact negative restore test.

**Acceptance**

- consistent backup/restore reproduces counts, hashes, projection, and replay;
- missing artifact content is reported rather than ignored;
- the existing development mismatch is not used;
- existing backup/restore evidence remains green.

### S21C1-052 — Add migration and restart smoke

**Priority:** P0  
**Depends on:** S21C1-032, S21C1-051  
**Output:** repeatable lifecycle smoke across database restart

**Tasks**

1. Start from a fresh database at `0013`.
2. Upgrade to `0014`.
3. Ingest the deterministic fixture.
4. restart database and application process;
5. verify projection, history, Artifact Store references, and event correlations;
6. backup and restore;
7. verify replay again.

**Acceptance**

- all receipts and hashes remain stable;
- no in-memory-only state is required;
- health is green before and after restart and restore.

## EPIC S21C1-E06 — Verification and CI

### S21C1-060 — Add contract and property tests

**Priority:** P0  
**Depends on:** S21C1-010 through S21C1-021  
**Output:** deterministic core test family

**Coverage**

- contract validation and canonical hashing;
- state-machine legal and illegal transitions;
- dataset role and provenance policy;
- idempotency and conflict;
- replay determinism;
- exact promotion/approval binding;
- rollback history;
- observation classification;
- schema export;
- no default active component.

**Acceptance**

- tests are credential-free and network-free;
- generated/property cases use a fixed seed in CI;
- failures report the violated invariant.

### S21C1-061 — Add PostgreSQL and adversarial tests

**Priority:** P0  
**Depends on:** S21C1-032 through S21C1-043  
**Output:** focused PostgreSQL integration suite

**Coverage**

- grants and controlled-function permissions;
- append-only trigger rejection;
- revision compare-and-swap race;
- activation race;
- idempotency conflict;
- illegal transition;
- mismatched promotion and approval;
- hash and artifact corruption;
- missing artifact;
- real-run training insertion rejection;
- replay gap and broken predecessor;
- quarantine review authorization;
- restart and rollback.

**Acceptance**

- tests run under owner and application roles where appropriate;
- no test converts a dependency import failure into a skip;
- every defect class has a named assertion.

### S21C1-062 — Add deterministic evidence benchmark cases

**Priority:** P1  
**Depends on:** S21C1-021, S21C1-042  
**Output:** small benchmark-runner adapter plus CI and seed manifests

**Required case families**

- lifecycle persistence;
- observation accept/quarantine/reject;
- dataset selection determinism;
- artifact verification;
- replay;
- activation rejection;
- rollback.

**Minimum evidence**

- at least 12 CI cases;
- at least 48 fixed-seed cases;
- 100% expected-policy match;
- zero provider, credential, network, or GPU use.

If adapting the existing benchmark runner would require a second runner or a broad rewrite, retain the cases as focused deterministic tests and record that bounded decision in the ADR. A new benchmark framework is prohibited.

### S21C1-063 — Add the early pull-request CI lane

**Priority:** P0  
**Depends on:** S21C1-010, S21C1-030, initial S21C1-031 skeleton  
**Output:** early draft PR and `learned-evidence-core` CI coverage

**Tasks**

1. Push the first coherent contracts/table/migration skeleton.
2. Open a draft pull request immediately.
3. Add a focused learned-evidence core job.
4. Install the PostgreSQL extra in every job importing PostgreSQL learned modules.
5. Keep provider, credential, network, and GPU access disabled.
6. Run schema and migration drift checks in the appropriate lane.
7. Update the same PR throughout implementation unless a reviewed scope split is required.

**Acceptance**

- pull-request CI runs before multiple untested integration commits accumulate;
- missing optional extras fail setup or tests instead of being skipped;
- required checks are not removed to make the PR green;
- unchanged-head infrastructure failures are inspected and rerun before code changes.

### S21C1-064 — Run the full local verification matrix

**Priority:** P0  
**Depends on:** all implementation items  
**Output:** timestamped local evidence in the Sprint 21C1 report

**Required commands or equivalent repository-standard commands**

```bash
scripts/check_repository_language.sh
python -m cognitive_os.schemas.export --check
uv run pytest tests/unit/learned -q
uv run pytest tests/contract -q
uv run pytest tests/integration/test_learned_evidence.py -q
uv run pytest tests/integration/test_postgres_learned_evidence.py -q
uv run pytest -q
scripts/postgres_migrate.sh
scripts/run_postgres_integration_tests.sh
```

Also run:

- the evidence smoke and deterministic cases;
- Alembic upgrade, downgrade, re-upgrade, head, and drift checks;
- learned health under healthy and injected-failure states;
- backup and test restore against the isolated consistent pair.

**Acceptance**

- exact commands, counts, duration, environment class, and exit status are recorded;
- any skip is enumerated with its reason;
- no pre-existing failure is hidden;
- the final focused and full suites run on the exact candidate head.

## EPIC S21C1-E07 — Documentation, gate, and release

### S21C1-070 — Update configuration and operator documentation

**Priority:** P1  
**Depends on:** S21C1-050 through S21C1-052  
**Output:** accurate operations and configuration documentation

**Required content**

- learned persistence architecture and authority;
- database and Artifact Store configuration;
- no-default-active-component behaviour;
- observation statuses and quarantine workflow;
- artifact verification and safe format handling;
- health, replay, backup, and restore;
- credential and redaction rules;
- recovery steps for event-correlation warnings;
- isolated-environment requirement;
- explicit Gate L2 non-claim.

**Acceptance**

- all documented commands are exercised;
- defaults are safe;
- no credential example resembles a live token;
- no document claims that Sprint 21C1 trained or activated useful ML.

### S21C1-071 — Produce the Gate C1 assessment

**Priority:** P0  
**Depends on:** S21C1-064  
**Output:** `docs/sprints/sprint-21/gate-c1-assessment.md`

**Tasks**

1. Evaluate every Gate C1 condition in Section 2.2.
2. Link exact test, migration, backup, restore, CI, and integrity evidence.
3. Distinguish pass, fail, and not-applicable.
4. State that Gate L2 remains closed.
5. List residual risks and owners.

**Acceptance**

- every conclusion has evidence;
- deterministic fixtures are not described as real outcomes;
- persistence capability is not described as useful learned behaviour.

### S21C1-072 — Complete the Sprint 21C1 report

**Priority:** P0  
**Depends on:** S21C1-071  
**Output:** release-grade Sprint 21C1 report

**Required content**

- starting and final source state;
- delivered work by backlog ID;
- changed migrations, contracts, tables, services, scripts, and CI;
- exact test and benchmark evidence;
- PostgreSQL health, drift, backup, and restore evidence;
- artifact mismatch handling;
- branch-protection and reviewer status;
- pull-request and CI handles known before the report commit;
- Gate C1 outcome and Gate L2 status;
- deviations, residual risks, and Sprint 21C2 handoff.

**Self-reference rule**

The tracked report may contain:

- implementation PR and merge handles already known;
- prior completed CI handles;
- the expected target tag name.

It must not require:

- its own future merge SHA;
- the future final `main` CI run;
- the future annotated tag object.

Those final handles belong in the immutable tag annotation and external release record.

### S21C1-073 — Merge, verify final `main`, and create one baseline tag

**Priority:** P0  
**Depends on:** S21C1-000, S21C1-063, S21C1-072  
**Output:** protected release and verified annotated tag

**Tasks**

1. Confirm every required PR check is green on the exact candidate head.
2. Resolve all required conversations.
3. Obtain the required review if branch protection and reviewer availability permit it.
4. Merge through the protected repository path.
5. wait for post-merge `main` CI and verify the exact head and successful conclusion;
6. if a separate report/evidence PR is required, merge it before tagging and wait for its final `main` CI;
7. create `sprint-21c1-evidence-baseline` once on the final evidence commit;
8. include final `main` CI, Gate C1 decision, migration head, and handoff in the tag annotation;
9. push the tag;
10. verify local tag object, remote tag object, peeled commit, `origin/main`, and final CI head.

**Acceptance**

- peeled target tag equals the intended final evidence commit;
- `origin/main` equals that commit at tag creation;
- final `main` CI succeeds on that exact commit;
- the tag is annotated and remote-verifiable;
- no tag move, deletion, or recreation is needed.

### S21C1-074 — Prepare the Sprint 21C2 handoff

**Priority:** P1  
**Depends on:** S21C1-073  
**Output:** executable handoff for the governed teacher and provider boundary

**Required handoff**

- parent tag: `sprint-21c1-evidence-baseline`;
- parent migration: `0014`;
- next available migration: `0015`, to be used only if Sprint 21C2 needs a schema change;
- recommended branch: `feature/sprint-21c2-governed-providers`;
- exact learned repository, dataset, artifact, evidence, and health APIs;
- exact provider-output retention, rights, sensitivity, and expiry fields that map
  into learned evidence;
- accepted Gate C1 limitations;
- unresolved Artifact Store remediation item;
- Gate L2 remains closed;
- no provider may write active memory, approve itself, or activate a learned
  component merely because persistence exists.

---

## 8. Execution waves and pull-request strategy

### 8.1 Dependency order

| Wave | Work items | Exit |
|---|---|---|
| W0 — control | 000–003 | authenticated control, verified parent, isolated storage, ADR |
| W1 — contract skeleton | 010–014, 030, initial 031, 063 | schemas and table skeleton green in an early draft PR |
| W2 — reference behaviour | 020–021 | lifecycle and replay pass in memory |
| W3 — durable core | 031–034 | migration, repository, concurrency, and health pass |
| W4 — evidence intake | 040–043 | artifact lineage, observation intake, datasets, quarantine pass |
| W5 — operations | 050–052 | CLI, restart, backup, and restore pass |
| W6 — verification | 060–064 | focused and full local evidence green |
| W7 — closeout | 070–074 | Gate C1, report, protected merge, final CI, one tag, handoff |

No wave may claim completion while a P0 dependency remains red.

### 8.2 Early PR rule

The first pull request must be opened during W1, after a coherent contracts/table/migration skeleton exists, rather than after feature completion. It may begin as draft.

Recommended first remote checkpoint:

- domain contracts compile;
- table metadata imports;
- migration chain recognizes `0014`;
- schema export is updated;
- focused unit tests pass;
- learned CI job installs the correct extras.

### 8.3 Scope-split rule

Use one implementation PR by default. Split only when:

- the first PR is a strictly preparatory migration/contract change that can be independently released; or
- a reviewed risk boundary requires separate authorization.

Do not split merely to bypass required checks or review.

---

## 9. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| source | exact parent and final SHA | wrong baseline or untracked work |
| contracts | schema and hash tests | evidence cannot be trusted |
| in-memory parity | shared repository suite | port semantics are ambiguous |
| PostgreSQL | owner/app role integration | persistence or authority failure |
| migration | clean, incremental, downgrade, drift | release is not deployable |
| lifecycle | legal/illegal transitions and CAS | unsafe component state |
| activation | exact assessment/approval and race | unauthorized or double activation |
| observation | accept/quarantine/reject | contaminated learning evidence |
| dataset | deterministic selection and role rules | leakage or irreproducibility |
| artifact | existence, hash, inert handling | corrupt or executable artifact risk |
| replay | projection equality after restart | hidden in-memory authority |
| events | correlation and gap health | incomplete cross-subsystem audit |
| backup/restore | counts, hashes, replay, artifact integrity | non-recoverable learned state |
| benchmark/smoke | deterministic policy match | regression in bounded workflow |
| full suite | repository-wide tests | cross-sprint regression |
| PR CI | all required checks | remote integration unresolved |
| post-merge CI | exact final `main` head | release not validated |
| tag | local/remote object and peeled SHA | baseline not reproducible |

---

## 10. Quantitative acceptance thresholds

### 10.1 Correctness

- 100% of required contract, repository, lifecycle, observation, artifact, replay, and activation tests pass.
- 0 illegal transitions succeed.
- 0 conflicting idempotency-key reuses succeed.
- 0 real-governed-run observations enter a training snapshot.
- 0 unauthorized activation, approval, rollback, or quarantine-review operations succeed.
- 0 committed states contain two active components for one surface.
- 0 corrupted or missing artifacts are reported healthy.

### 10.2 Determinism

- repeated canonicalization produces identical hashes;
- repeated fixture intake produces identical receipts;
- repeated selection produces identical dataset and manifest hashes;
- repeated replay produces an identical projection;
- fixed-seed evidence cases have 100% expected-policy match.

### 10.3 Durability

- state remains identical after application restart;
- state remains identical after PostgreSQL restart;
- backup/restore preserves learned table counts, hashes, and replay;
- all immutable ledgers reject update and delete under the application role.

### 10.4 Operational safety

- 0 provider calls;
- 0 external network calls in tests and benchmarks;
- 0 credential reads by learned tests;
- 0 GPU requirements;
- 0 unsafe artifact deserializations;
- 0 destructive repairs to the original inconsistent development pair.

### 10.5 Performance guardrail

Sprint 21C1 is not a throughput sprint. Still, the deterministic 48-case seed run and a replay of at least 1,000 synthetic metadata records must:

- complete within the existing CI job timeout;
- show no unbounded query pattern;
- use bounded pagination for list operations;
- record elapsed time and peak resident memory for trend comparison.

This is a regression guardrail, not a claim of production-scale capacity.

---

## 11. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| GitHub credential unavailable | authenticated API remains 401 | local work may continue; PR, merge, and release stay blocked |
| no eligible second reviewer | self-approval is impossible | keep existing protection; record review limitation; do not fabricate approval |
| development artifact mismatch | metadata and filesystem disagree | isolate release environment; produce non-destructive remediation proposal |
| migration reflection drift | `alembic check` proposes false removal | add exact-name handling and focused regression only |
| optional dependency absent in CI | PostgreSQL module import fails | install declared extra; do not skip |
| dual authority emerges | projection and event stream both treated as primary | return to ADR authority model; replay from learned history |
| artifact execution path appears | loader imports pickle/joblib execution | remove the path; keep artifact inert |
| synthetic data counted as real | fixture provenance mislabeled | fail Gate C1 evidence and correct counts |
| persistence presented as learning success | report implies uplift or Gate L2 | correct the claim; Gate L2 remains closed |
| concurrent activation race | two successful activations for one surface | block release and fix database constraint/CAS |
| self-referential release evidence | report needs future tag or own merge SHA | move final handles to tag annotation/external record |
| scope expands to training/providers/EMG | new dependency not required for durability | defer to owning sprint |

---

## 12. Definition of Done

Sprint 21C1 is complete only when:

- all P0 items are complete;
- every P1 deferral is explicitly justified and does not weaken Gate C1;
- the eight-table persistence model or its pre-approved ADR replacement is deployed by migration `0014`;
- current learned state is reproducible from immutable history;
- Artifact Store lineage verifies without duplicated bytes or unsafe loading;
- observation intake and quarantine are deterministic and auditable;
- real-run evaluation-only policy is enforced in domain and database layers;
- activation and rollback are persistent, exact-evidence-bound, and concurrency-safe;
- no useful component is active by default;
- health, migration, grants, backup, restore, restart, and corruption tests pass;
- focused and full local suites pass on the candidate head;
- all required PR checks pass;
- post-merge `main` CI passes on the final evidence commit;
- the annotated `sprint-21c1-evidence-baseline` tag is created once and verified;
- the report clearly states that Gate L2 remains closed;
- Sprint 21C2 has an exact parent, next migration, API handoff, and residual-risk list.

---

## 13. Expected deliverables

At minimum, Sprint 21C1 should produce:

- this backlog and an authority ADR;
- new learned evidence contracts and exported schemas;
- learned persistence ports and application service;
- in-memory and PostgreSQL repository implementations;
- `src/cognitive_os/infrastructure/learned/postgres/` table, repository, and health modules;
- `infra/postgres/alembic/versions/0014_create_learned_evidence_store.py`;
- learned event correlation service;
- Artifact Store lineage adapter;
- governed outcome harvester and quarantine workflow;
- deterministic dataset selection manifests;
- safe operational CLI and smoke;
- updated health, backup, restore, and migration scripts;
- learned core, contract, PostgreSQL, adversarial, concurrency, restart, and corruption tests;
- an early draft pull request with learned CI coverage;
- `docs/sprints/sprint-21/gate-c1-assessment.md`;
- a Sprint 21C1 report;
- annotated `sprint-21c1-evidence-baseline`;
- Sprint 21C2 handoff.

The final delivered system must provide durable, governed evidence for future machine learning without pretending that persistence alone is machine learning.
