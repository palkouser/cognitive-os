# Sprint 21C2 Technical Backlog

## Governed Teacher and Provider Boundary

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution
- **Revision:** 1
- **Prepared:** 2026-07-27
- **Required parent baseline:** `sprint-21c1-evidence-baseline`
- **Required parent commit:** `aed2c1b0af280d3f0924a37eeddc191cd320e936`
- **Required parent tag object:** `fc7bd5cf384890d036cd70149b4408de650c8ec8`
- **Required parent migration head:** `0014`
- **Implementation branch:** `feature/sprint-21c2-governed-providers`
- **Target migration:** `0015_create_provider_output_governance.py`
- **Target baseline tag:** `sprint-21c2-provider-baseline`
- **Stage gate:** Gate C2 — Governed Provider Boundary
- **Successor gate:** Gate L2 remains closed until a later sprint demonstrates useful
  learned behaviour on real governed outcomes.
- **Runtime baseline:** Python 3.12.13, PostgreSQL 18, existing OpenAI Python client,
  operator-installed Claude Code and Codex CLIs
- **Execution profile:** local, CPU-first, single-maintainer, credential-free normal CI,
  operator-approved bounded live smoke
- **Repository language:** English only

---

## 0. Authority and execution contract

This backlog is the execution authority for Sprint 21C2. It refines:

- `docs/sprints/sprint-21/sprint-21c1-report.md`;
- `docs/sprints/sprint-21/sprint-21c2-handoff.md`;
- the final `sprint-21c1-evidence-baseline` tag annotation;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`.

If an implementation detail conflicts with a confirmed repository invariant, the
implementer must:

1. preserve the invariant;
2. record the conflict and decision in the Sprint 21C2 report;
3. update the provider-boundary ADR before changing a persistence, authority, trust,
   retention, process, or activation boundary;
4. avoid silently broadening the sprint.

Repository content, source, schemas, comments, fixtures, operational evidence, issue
text, commit messages, and release notes must remain English-only.

### 0.1 Release-grade meaning of done

Sprint 21C2 is not complete when adapter unit tests pass. Completion requires:

1. verification of the parent tag object, peeled commit, remote `main`, final parent CI,
   and migration head;
2. implementation of all P0 work and any accepted P1 work required by Gate C2;
3. credential-free offline provider, process, persistence, migration, and integration
   evidence;
4. one operator-approved, bounded, sanitized live smoke for OpenRouter, Claude Code,
   and Codex;
5. a pull request with all required checks green;
6. merge to `main` without weakening protection;
7. successful post-merge `main` CI on the exact merged head;
8. a final evidence update that does not create a self-referential release loop;
9. one annotated target tag created on the final evidence commit;
10. local and remote tag-object and peeled-commit verification;
11. a complete Sprint 21C2 report, Gate C2 assessment, and Sprint 21C3 handoff.

The target tag must not be moved or recreated. Final merge, CI, and tag handles that
cannot exist before release belong in the immutable tag annotation or external release
evidence, not in a tracked document that would require another release commit.

### 0.2 Provider authority rule

OpenRouter, Claude Code, and Codex are advisory teachers. They may propose structured
content, explanations, tests, or candidate actions. They may not:

- write active memory;
- activate, approve, promote, or roll back a learned component;
- review their own quarantined output;
- classify their output as a real governed run without a real governed run;
- mutate the working repository during advisory execution;
- bypass usage-rights, sensitivity, retention, verifier, or human authority checks;
- become the only evidence of a decision.

### 0.3 Simplicity rule

Sprint 21C2 must reuse the existing provider port, registry, normalized request and
response contracts, OpenAI Python client, retry logic, Event Store, Artifact Store,
learned intake, repository patterns, benchmark runner, migration tooling, and release
workflow.

The sprint may add:

- one OpenRouter adapter;
- one Codex CLI adapter;
- one shared bounded subprocess runner used by both CLI adapters;
- one small provider-construction boundary;
- one provider-output governance contract and persistence table.

It must not add a second provider platform, a second event or artifact store, a generic
plugin framework, LiteLLM, an OpenRouter-specific SDK, a new process supervisor, or a
new workflow engine.

---

## 1. Starting evidence and constraints

### 1.1 Verified Sprint 21C1 release state

At backlog preparation:

- remote `main` resolves to
  `aed2c1b0af280d3f0924a37eeddc191cd320e936`;
- remote tag object `sprint-21c1-evidence-baseline` resolves to
  `fc7bd5cf384890d036cd70149b4408de650c8ec8`;
- the tag peels to the same commit as remote `main`;
- the final parent `main` CI run is `30285564507`, with conclusion `success`;
- migration `0014` is the parent Alembic head;
- Gate C1 passed all thirteen release conditions in the final tag annotation;
- Gate L2 is closed.

Implementation must start from the peeled tag commit, not from an unverified symbolic
branch.

### 1.2 Sprint 21C1 lessons that change Sprint 21C2

The following are mandatory controls:

1. **Execute every controlled migration function in W1.** Migration `0014` applied
   successfully even though its first generic record functions produced PostgreSQL
   `text` values for UUID, integer, boolean, and timestamp columns. Migration application
   and trigger inspection alone are insufficient.
2. **Test against the real repository contract early.** The `0014` defects became visible
   only when the repository actually invoked the functions. Migration, repository, and
   shared contract work must overlap in the first pull-request checkpoint.
3. **Write artifact bytes through `ArtifactService`.** A C1 health fixture created metadata
   without bytes and restore verification caught the drift. Provider fixtures must never
   fabricate Artifact Store metadata.
4. **Open the draft pull request in W1.** CI-only dependency, migration, packaging, or
   restore defects must be found before adapter completion.
5. **Keep release evidence isolated.** The inconsistent development Artifact Store pair
   must not be used for C2 release evidence.
6. **Keep final handles out of a self-referential tracked report.** Use the final tag
   annotation for immutable release handles.

### 1.3 Accepted limitation: no second eligible reviewer

There is one collaborator. Required approving reviews remain disabled. This is an
accepted operational limitation, not permission to reduce protection:

- all 27 required checks remain required;
- `enforce_admins` remains enabled;
- no approval may be fabricated;
- no branch-protection control may be weakened to compensate.

At sprint start, query current protection and collaborator eligibility. If a second
eligible reviewer has been added, enabling one required approval is a separately
recorded protection change. Otherwise, retain and report the limitation.

### 1.4 Accepted limitation: inconsistent development Artifact Store pair

The development metadata/filesystem pair remains inconsistent. It was diagnosed
read-only, left untouched, and has a non-destructive remediation proposal awaiting
operator approval.

Sprint 21C2 must:

- leave the pair unchanged;
- use a fresh, consistent database and artifact root for all release evidence;
- use the C1 inventory only as read-only diagnostic evidence;
- stop and request operator authority before any remediation;
- never make a verifier green by deleting orphan files or metadata.

### 1.5 Provider baseline

The repository already contains:

- `ModelProviderPort`, provider registry, selection, retry, replay, mock, typed provider
  errors, and normalized request/response contracts;
- `ModelExecutionService`;
- `ProviderEventService` and `ProviderArtifactService`;
- an OpenAI-compatible MiniMax adapter that is the donor for request/response mapping;
- an advisory Claude Code adapter;
- learned evidence persistence and `LearnedObservationIntake`.

The existing Claude Code adapter has security gaps that C2 must close:

- the prompt is present in process arguments;
- `git status` equality can miss mutation of an already dirty file;
- stdout and stderr do not have hard byte limits;
- cancellation and every output-limit path do not prove process-tree cleanup;
- session, MCP, tool, and permission boundaries are not fixed strongly enough for this
  gate.

No Codex CLI or OpenRouter adapter exists at the parent baseline.

---

## 2. Sprint goal and Gate C2 decision

### 2.1 Goal

Create a governed, replayable provider boundary through which an operator can use
OpenRouter, Claude Code, and Codex as bounded advisory teachers while preserving the
authority, provenance, retention, and quarantine guarantees established in Sprint 21C1.

The sprint must:

- use the existing OpenAI client for OpenRouter;
- harden Claude Code behind a shared bounded read-only CLI process boundary;
- add Codex through the same process boundary;
- record requested and resolved provider/model identity;
- produce typed health and failure outcomes;
- default provider output bytes to transient;
- persist output only under an explicit rights and retention decision;
- map governed output into `GovernedOutcomeReference`;
- quarantine unverified provider output;
- prove that advisory execution cannot mutate the fixture repository, expose secrets,
  approve itself, or write active memory;
- keep normal CI completely offline and credential-free.

### 2.2 Gate C2 pass conditions

Gate C2 passes only when all of the following are true:

1. the exact C1 parent tag, remote commit, final parent CI, and migration head are
   verified;
2. provider configuration selects every adapter unambiguously and rejects unsafe or
   unknown settings;
3. OpenRouter discovery, request mapping, resolved-model capture, health, replay, and
   typed failures pass offline;
4. Claude Code execution structurally enforces non-interactive, read-only, no-session,
   no-MCP, bounded advisory operation;
5. Codex execution structurally enforces ephemeral, read-only, no-approval, explicit
   working-directory, bounded advisory operation;
6. the shared process boundary proves stdin prompt delivery, environment allowlisting,
   stdout/stderr caps, timeout/cancellation cleanup, and content-based mutation
   detection;
7. provider-output governance records rights, sensitivity, intended use, retention,
   expiry semantics, verifier evidence, revision, and content hashes;
8. provider output reaches learned intake only through a governed source record;
   unverified output quarantines and no provider kind is added to
   `REAL_GOVERNED_SOURCE_KINDS`;
9. no provider can approve activation, review its own quarantine, activate a learned
   component, or write active memory;
10. no key, token, authorization header, raw credential, login identity, prompt, or
    unredacted provider error is retained in logs, events, artifacts, fixtures, or Git;
11. migration `0015`, repository parity, grants, health, backup, restore, restart, and
    downgrade/upgrade evidence pass;
12. normal CI covers all contracts and failure classes without network, provider
    credentials, installed external CLIs, or GPU;
13. one operator-approved live smoke succeeds for each provider with a public synthetic
    fixture, strict bounds, sanitized evidence, and an unchanged content snapshot;
14. the protected merge, exact-head post-merge CI, annotated tag, remote verification,
    report, and handoff sequence completes.

Any failed condition is a Gate C2 no-go. A typed provider failure is correct behaviour
for an individual request, but it does not substitute for the three required successful
operator live smokes.

### 2.3 Gate L2 status

Gate C2 does not open Gate L2. The Sprint 21C2 report must state:

> Governed provider evidence is available, but useful learned behaviour has not yet
> been demonstrated.

Provider connectivity is not training, useful improvement, anti-forgetting evidence,
safe shadow performance, or activation authorization.

---

## 3. Scope boundaries

### 3.1 In scope

- versioned provider configuration and construction;
- OpenRouter through the existing OpenAI Python client;
- Claude Code advisory hardening;
- Codex CLI read-only advisory integration;
- shared bounded subprocess execution for CLI adapters;
- structured output schemas and normalized responses;
- health, runtime discovery, requested/resolved identity, usage, finish reason, latency,
  and safe routing metadata;
- timeout, cancellation, process-tree cleanup, output caps, mutation detection, and
  redaction;
- provider-output governance contracts, persistence, revisions, and source resolution;
- explicit rights, intended-use, sensitivity, retention, expiry, and verifier decisions;
- connection to C1 learned observation intake and quarantine;
- credential-free replays, fakes, property tests, PostgreSQL integration, and opt-in
  live smoke;
- migration `0015`, health, backup, restore, schema export, CI, operator documentation,
  Gate C2, report, release, and C3 handoff.

### 3.2 Explicitly out of scope

- training, promoting, or activating a useful learned component;
- opening Gate L2;
- the Sprint 21C3 corpus target of at least 200 governed outcomes, 50 corrected
  trajectories, or executable coding tasks;
- local embeddings, EMG, learned routing, or model distillation;
- unrestricted provider tools, repository writes, shell execution, browser access,
  network tools, MCP servers, plugins, apps, multi-agent execution, or persistent
  provider sessions;
- copying, exporting, refreshing, or managing Claude Code or Codex subscription
  credentials;
- unattended service authentication for subscription CLIs;
- paid OpenRouter execution or a non-zero automatic spend limit;
- hard-coding a currently free model slug as permanently available;
- retaining raw provider request or response payloads;
- physical deletion or Artifact Store garbage collection;
- promising deletion of bytes from an immutable store;
- repairing the inconsistent development Artifact Store pair;
- enabling required reviews without a confirmed second eligible reviewer;
- a new provider SDK, provider framework, dependency, Event Store, Artifact Store,
  active-memory path, or workflow engine;
- autonomous code modification, commit, pull request, deployment, or release.

### 3.3 Deferral ownership

| Deferred capability | Owning sprint or decision |
|---|---|
| real outcome volume and executable coding corpus | Sprint 21C3 |
| local embedding model and semantic input retrieval | Sprint 21C3 |
| first reproducible trained candidate | Sprint 21D1 |
| useful shadow assessment and activation decision | Sprint 21D2 |
| graph-backed experience integration | Sprint 21D1/Sprint 22 |
| unattended Claude Code or Codex authentication | separate security and terms decision |
| provider-output physical deletion and Artifact Store GC | separate storage lifecycle sprint |
| development Artifact Store remediation | operator-approved maintenance |
| adaptive or paid provider routing | later provider-policy sprint |

---

## 4. Minimal architecture

### 4.1 Reuse before addition

Sprint 21C2 must reuse:

- `cognitive_os.application.ports.model_provider.ModelProviderPort`;
- `cognitive_os.domain.model_requests`;
- `cognitive_os.domain.provider`;
- `cognitive_os.providers.registry`, `retry`, `replay`, and `errors`;
- the MiniMax OpenAI-compatible mapping and client patterns without copying the entire
  adapter;
- `ModelExecutionService`;
- `ProviderEventService` and `ProviderArtifactService`;
- the existing Event Store and content-addressed Artifact Store;
- `LearnedObservationIntake`, `LearnedEvidenceRepositoryPort`, and
  `LearnedQuarantineReview`;
- schema export, migration, health, backup, restore, benchmark, packaging, and release
  infrastructure.

### 4.2 Expected package boundary

The expected additions are:

```text
src/cognitive_os/
  application/
    ports/
      provider_output.py
    services/
      governed_teacher.py
  domain/
    provider_output.py
  infrastructure/
    learned/
      memory_provider_output.py
      postgres/
        provider_output_tables.py
        provider_output_repository.py
        provider_output_health.py
  providers/
    cli_process.py
    factory.py
    openrouter/
      client.py
      config.py
      discovery.py
      health.py
      mapping.py
    claude_code/
      ... focused hardening ...
    codex_cli/
      advisory.py
      config.py
      mapping.py
```

Equivalent focused names are acceptable. A new generic abstraction is not acceptable
unless both CLI adapters or both OpenAI-compatible adapters use it in this sprint.

### 4.3 Authority model

| Information | Authority |
|---|---|
| provider request lifecycle | existing Event Store |
| normalized retained bytes | existing Artifact Store |
| provider-output rights, retention, sensitivity, verifier, and revision | provider-output governance ledger |
| learned observation classification | C1 learned observation ledger |
| quarantine review | C1 human-only quarantine review |
| provider configuration | validated runtime configuration |
| current provider health | read-only health service, never persistence authority |
| active learned state | C1 learned evidence service, unchanged |
| provider login and credential | external CLI/provider credential store, never Cognitive OS |

Events are audit evidence, artifacts own bytes, and the new ledger owns the decision
that determines whether provider output may be retained or offered to learned intake.
No projection may silently become a second authority.

### 4.4 Provider execution flow

```text
operator request
  -> validated provider configuration and retention directive
  -> ModelExecutionService / bounded CLI process
  -> normalized response and model-call event
  -> rights, sensitivity, secret-scan, intended-use, and verifier decision
  -> provider-output governance record
  -> optional normalized Artifact Store content when policy permits
  -> GovernedOutcomeReference
  -> LearnedObservationIntake
  -> accepted, quarantined, or rejected observation
```

There is no edge from a provider adapter to active memory, activation, approval,
quarantine review, repository mutation, or training.

### 4.5 Governed execution receipt

Preserve the existing `ModelExecutionService.execute()` contract. Add one explicit
governed path, such as `execute_with_receipt()`, sharing the same internal provider call.
It must not make a second provider request.

The receipt must expose only:

- normalized response;
- provider ID, requested model, and resolved model;
- request and normalized response hashes;
- model-call ID and completed Event Store envelope ID;
- optional retained request/response artifact references;
- applied retention directive;
- provider-output governance record reference when one was created.

`ProviderEventService` may return the appended envelope ID from `requested()` and
`completed()` rather than discarding it. Existing callers must remain compatible.

### 4.6 Provider-output retention model

The C1 `LearnedObservationRecord` must not be extended. Adding optional fields would
change canonical hashes for existing `0014` rows. Retention is represented by a separate,
versioned `ProviderOutputRecord`.

Required retention modes:

- `none`: no provider-output record and no provider request/response artifact;
- `hash_only`: persist governed metadata and hashes, but no provider content bytes;
- `normalized_content`: persist only the validated normalized response, never raw
  provider payload.

`none` is the default. `normalized_content` is allowed only when:

- usage rights and provider terms are verified for the intended use;
- secret scanning passes;
- the sensitivity policy permits storage;
- no physical-deletion obligation applies;
- expiry does not promise removal from the immutable Artifact Store;
- the retained artifact hash matches the governance record.

If a finite retention obligation requires physical deletion, C2 must use `hash_only` or
`none`. `expires_at` controls eligibility for future use; it must not falsely claim that
immutable bytes were deleted.

### 4.7 OpenRouter boundary

OpenRouter must use the installed OpenAI Python client with:

- exact HTTPS base URL `https://openrouter.ai/api/v1`;
- API key from `OPENROUTER_API_KEY` only;
- runtime model discovery;
- `openrouter/free` as the default live-smoke router;
- optional runtime-validated pinned free model;
- requested and resolved model recording;
- allowlisted routing metadata only;
- default provider policy requesting zero-data-retention and denying data collection
  where compatible endpoints exist;
- no internal or restricted content when that strict policy cannot be satisfied.

Free model availability is dynamic. A missing previously observed Gemma model is
`MODEL_UNAVAILABLE`, not a code defect and not a reason to weaken offline tests. A public
synthetic smoke may use an explicitly operator-approved free endpoint policy; that
exception may not be reused for internal or restricted content.

### 4.8 CLI process boundary

Both CLI adapters must use one shared runner that enforces:

- prompt through stdin, never process arguments;
- executable and fixed safety arguments from validated configuration;
- minimal environment allowlist with secret-like variables excluded by default;
- new process group/session;
- timeout, cancellation, stdout-cap, and stderr-cap termination;
- graceful termination followed by bounded forced process-tree kill;
- bounded captured output and sanitized diagnostic excerpts;
- content-and-mode snapshot before and after execution;
- a dedicated synthetic fixture directory, not the Cognitive OS worktree, for live
  smoke;
- no shell interpolation;
- no persistent session, resume, or history;
- no raw login identity in health output.

Default process limits are 120 seconds, 256 KiB stdout, and 64 KiB stderr. Configuration
may lower them. Hard maxima are 600 seconds, 1 MiB stdout, and 256 KiB stderr. Increasing
a hard maximum requires an ADR update and new resource-exhaustion evidence.

### 4.9 Claude Code boundary

At sprint start, validate the installed CLI version and flags. The expected structural
profile is:

- non-interactive print mode;
- structured JSON with a checked output schema;
- `plan` permission mode;
- safe mode where supported;
- explicit read-only tools limited to `Read`, `Glob`, and `Grep`;
- no `Bash`, `Edit`, `Write`, web, MCP, or delegated agents;
- strict empty MCP configuration;
- no session persistence;
- one bounded turn for smoke and a configured small maximum for other advisory calls;
- shared-runner timeout, output, environment, and mutation controls.

Health may report installed/not installed, logged in/not logged in, version, and a coarse
authentication method. It must discard email, organization, account, subscription, and
credential values.

### 4.10 Codex boundary

At sprint start, validate the installed CLI version and flags. The expected structural
profile is:

- `codex exec`;
- prompt from stdin (`-`);
- `--ephemeral`;
- `--ignore-user-config`;
- `--json`;
- `--output-schema` pointing to a generated temporary schema file;
- `--sandbox read-only`;
- `--ask-for-approval never`;
- explicit `--cd` to the isolated fixture;
- empty or explicitly disabled MCP, app, and delegated-agent configuration after
  version-specific verification;
- no resume, persistent session, bypass, `danger-full-access`, `--yolo`,
  `--dangerously-bypass-approvals-and-sandbox`, or instruction-ignore flags.

Health may report installed/not installed, logged in/not logged in, version, and a coarse
authentication method. Cognitive OS must not copy or manage ChatGPT or API credentials.

### 4.11 Typed failure taxonomy

Reuse and minimally extend the existing provider errors so all three adapters normalize:

- credential missing;
- authentication failed;
- authorization or data-policy refusal;
- model unavailable;
- provider unavailable;
- quota or credits exhausted;
- rate limited;
- network failure;
- timeout;
- cancellation;
- output limit exceeded;
- malformed or schema-invalid output;
- process execution failure;
- attempted mutation;
- unsupported capability.

Provider HTTP bodies, stderr, request IDs, and routing metadata must be allowlisted and
redacted before they enter `details`, events, artifacts, reports, or fixtures.

---

## 5. Required contracts and persistence

### 5.1 `ProviderOutputRecord`

The immutable, canonically hashed domain record must include:

- `provider_output_id`;
- `revision` and optional `previous_revision_id`;
- `schema_version`;
- `model_call_id`;
- provider ID and adapter kind;
- requested and resolved model;
- request hash and normalized response hash;
- completed model-call event ID;
- optional response artifact reference;
- prompt/template identifier and version, but not prompt content;
- canonical parameter hash;
- input source IDs and hashes;
- intended use;
- rights/terms decision and decision-evidence hash;
- sensitivity;
- secret-scan status and evidence hash;
- retention mode and optional `expires_at`;
- physical-deletion-required flag;
- verifier status, verifier identity, and verifier-evidence hash;
- optional human reviewer reference;
- recorded-by actor and recorded time;
- content hash and idempotency key;
- optional supersession reason.

Unknown rights, failed secret scan, missing verifier evidence, unrecognized sensitivity,
expired evidence, or a physical-deletion obligation must fail closed for corpus or
training eligibility.

### 5.2 Required enums and decisions

At minimum:

- intended use: transient advice, evaluation evidence, corpus candidate, skill
  candidate, training candidate;
- rights decision: unknown, prohibited, verified;
- secret-scan status: not run, passed, failed;
- retention mode: none, hash only, normalized content;
- verifier status: not run, passed, failed, inconclusive;
- sensitivity: reuse public, internal, restricted.

Do not create a new sensitivity vocabulary when the repository already has one that
fits the contract.

### 5.3 `provider_output_records` table

Migration `0015` should add one append-only governance table rather than a general
provider platform. Required database controls:

- primary key on the immutable revision ID;
- uniqueness of `(provider_output_id, revision)`;
- uniqueness of idempotency key with same-content replay and conflicting-content refusal
  through a controlled function;
- foreign-key or exact resolver relationship to the model-call event and retained
  artifact where the existing stores permit it;
- content-hash check through the controlled write path;
- revision continuity and previous-revision validation;
- no update or delete for the application role;
- explicit owner, application, backup, and restore grants;
- indexes for model call, provider, intended use, expiry, verifier status, and latest
  revision lookup;
- no raw prompt, raw response, authorization value, or credential column.

Do not add a materialized current-state table in C2. The latest revision is the maximum
valid revision for one stable output ID and can be queried through a bounded index.

### 5.4 Controlled write function

The controlled function must:

1. parse the complete typed payload;
2. use explicit casts or `jsonb_populate_record` semantics that preserve UUID, integer,
   boolean, and timestamp types;
3. validate idempotency and revision continuity;
4. validate retention and rights constraints;
5. insert one immutable row;
6. return the inserted or idempotently existing record.

W1 tests must invoke the function with every non-text PostgreSQL type before the
repository is considered ready. Applying the migration without executing the function
is not acceptance evidence.

### 5.5 Provider source kinds and learned intake

Add:

- `openrouter_advisory`;
- `claude_code_advisory`;
- `codex_cli_advisory`.

These belong to `VERIFIER_BACKED_SOURCE_KINDS`. They must never be added to
`REAL_GOVERNED_SOURCE_KINDS`.

Mapping to `GovernedOutcomeReference` must use:

- source payload hash from the governed normalized response hash;
- source event ID from the actual completed model-call event;
- provider-output ID as a resolvable source record;
- `OPERATOR_SUPPLIED` provenance unless a real governed run actually produced the
  result;
- rights and sensitivity from the latest non-expired governance revision;
- verifier status and exact evidence hash from independent verification.

Schema validation proves shape, not correctness. A provider cannot be its own verifier.

### 5.6 Revision and expiry behaviour

- Reusing an idempotency key with identical content returns the same record.
- Reusing it with different content fails closed.
- A rights revocation, sensitivity correction, verifier correction, or expiry update is
  a new revision.
- Previous rows remain immutable and auditable.
- Superseded, expired, prohibited, or failed-scan records cannot be newly selected for
  corpus or training use.
- A revision must not retroactively rewrite an already recorded learned observation;
  instead, it creates audit evidence and future selection excludes the item.
- C2 does not physically delete Artifact Store bytes.

---

## 6. Detailed work items

## EPIC S21C2-E00 — Baseline, remote control, and accepted limitations

### S21C2-000 — Verify and freeze the C1 parent baseline

- **Priority:** P0
- **Depends on:** none
- **Output:** exact parent verification block in the C2 report

**Tasks**

1. Confirm a clean worktree before implementation.
2. Fetch `origin` and tags.
3. Verify local `main`, remote `main`, tag object, and peeled C1 tag.
4. Verify final parent CI run `30285564507`.
5. Verify Alembic head `0014`.
6. Verify repository language and a focused provider/learned import smoke.
7. Create the C2 branch from the peeled tag commit.

**Acceptance**

- all source handles resolve to the declared parent;
- any deviation stops implementation;
- the branch contains no unrelated carried changes.

### S21C2-001 — Revalidate remote protection and reviewer eligibility

- **Priority:** P0
- **Depends on:** S21C2-000
- **Output:** current protection evidence without credential disclosure

**Tasks**

1. Reauthenticate GitHub CLI if authenticated reads fail.
2. target `palkouser/cognitive-os` explicitly;
3. query required checks, `enforce_admins`, merge settings, and open PRs;
4. determine whether a second eligible reviewer exists;
5. retain the 27 checks and `enforce_admins`;
6. do not enable an impossible approval or weaken another control.

**Acceptance**

- authenticated remote reads succeed before the first mutation;
- current protection is recorded;
- no token or identity secret enters evidence;
- no protection is weakened.

### S21C2-002 — Isolate the Artifact Store mismatch

- **Priority:** P0
- **Depends on:** S21C2-000
- **Output:** isolated, consistent C2 database and artifact root

**Tasks**

1. Reference the C1 read-only mismatch inventory.
2. Confirm that the inconsistent pair has not been mutated by C2 setup.
3. Create a fresh database and Artifact Store root.
4. run existing artifact health before migration;
5. record non-secret isolation handles.

**Acceptance**

- the release environment begins healthy;
- the original pair remains untouched and recoverable;
- all C2 artifact evidence is written through `ArtifactService`.

### S21C2-003 — Record provider-boundary ADR

- **Priority:** P0
- **Depends on:** S21C2-000
- **Output:** one ADR covering authority, process safety, and retention

**Tasks**

1. Record the authority table and data flow in Section 4.
2. Record why one shared CLI runner is justified by two adapters.
3. Record why OpenRouter reuses the existing OpenAI client.
4. Record why one separate governance ledger is required and why C1 observation hashes
   remain unchanged.
5. Record retention, expiry, immutable-byte, redaction, and verifier semantics.
6. Record provider non-authority and Gate C2 versus Gate L2.

**Acceptance**

- the ADR introduces no parallel platform;
- every trust and failure boundary has a testable consequence;
- implementation deviations update the ADR before merge.

### S21C2-004 — Freeze provider versions and supported flags

- **Priority:** P0
- **Depends on:** S21C2-000
- **Output:** sanitized provider compatibility manifest

**Tasks**

1. Record installed Claude Code and Codex version strings.
2. Capture help output only through an allowlist of required flag names.
3. Revalidate required CLI flags against current official documentation.
4. Record the installed OpenAI Python client version.
5. define supported minimum/maximum versions or fail-closed capability probing;
6. discard account, email, organization, subscription, and login identifiers.

**Acceptance**

- the manifest contains versions and supported flags only;
- an incompatible or missing flag is typed unhealthy before execution;
- no raw authentication-status payload is retained.

## EPIC S21C2-E01 — Contracts and configuration

### S21C2-010 — Version provider configuration

- **Priority:** P0
- **Depends on:** S21C2-003
- **Output:** unambiguous configuration schema for all adapters

**Tasks**

1. Add an explicit adapter discriminator rather than overloading provider kind.
2. Preserve compatibility for existing MiniMax and Claude configuration through a
   versioned migration path.
3. Add OpenRouter and Codex schemas.
4. validate HTTPS base URL, model policy, timeouts, output caps, environment allowlist,
   retry maximum, spend maximum, retention default, and live-smoke opt-in;
5. reject unknown keys and safety-weakening values;
6. update example configuration without credentials.

**Acceptance**

- every adapter parses unambiguously;
- defaults are offline, transient, read-only, zero-spend, and live-smoke disabled;
- unsafe URLs, caps, retries, tools, sandboxes, or environment variables fail at load.

### S21C2-011 — Add provider-output governance contracts

- **Priority:** P0
- **Depends on:** S21C2-003
- **Output:** immutable contracts and enums from Section 5

**Tasks**

1. Implement `ProviderOutputRecord` and retention directive.
2. reuse canonical time, actor, hash, artifact, and sensitivity contracts;
3. validate revision, rights, scan, verifier, expiry, and retention combinations;
4. prohibit raw payload fields;
5. add schema version and canonical content hash;
6. add valid, invalid, mutation, and round-trip tests.

**Acceptance**

- identical records hash identically;
- one-field mutation changes the hash;
- prohibited retention combinations fail at construction;
- C1 learned observation fixtures and hashes remain unchanged.

### S21C2-012 — Export schemas and compatibility fixtures

- **Priority:** P0
- **Depends on:** S21C2-010, S21C2-011
- **Output:** tracked schemas and safe fixtures

**Tasks**

1. Register new configuration, output, receipt, health, and advisory schemas.
2. regenerate tracked schemas;
3. add representative valid and invalid fixtures;
4. add schema drift to the focused provider lane;
5. scan fixtures for credential-like material.

**Acceptance**

- schema export check passes;
- old provider fixtures remain compatible or have an explicit version migration;
- fixtures contain only synthetic public content.

### S21C2-013 — Define governed execution and persistence ports

- **Priority:** P0
- **Depends on:** S21C2-011
- **Output:** narrow receipt and provider-output repository ports

**Tasks**

1. Define `execute_with_receipt` without changing ordinary execution semantics.
2. define record, get revision, get latest, list eligible, and health operations;
3. define exact source resolution for learned intake;
4. define idempotency and revision conflict errors;
5. avoid generic query or arbitrary SQL escape hatches.

**Acceptance**

- the port supports only C2 use cases;
- retention is explicit per governed execution;
- no method writes learned state or active memory directly.

## EPIC S21C2-E02 — Shared provider safety infrastructure

### S21C2-020 — Implement the bounded CLI process runner

- **Priority:** P0
- **Depends on:** S21C2-010
- **Output:** one shared safe runner used by Claude Code and Codex

**Tasks**

1. Spawn without a shell and deliver prompts by stdin.
2. enforce executable, argument, working-directory, and environment policies;
3. create a separate process group;
4. stream into bounded stdout/stderr buffers;
5. terminate the entire process tree on timeout, cancellation, output overflow, or
   parser refusal;
6. return a typed result with only sanitized excerpts;
7. close file descriptors and temporary schema/config files on every path.

**Acceptance**

- prompts and credentials never appear in argv;
- child and grandchild fixture processes are gone after every failure path;
- output never exceeds the configured retained cap;
- cancellation cannot leave a process running.

### S21C2-021 — Replace status-only mutation checking

- **Priority:** P0
- **Depends on:** S21C2-020
- **Output:** deterministic content snapshot and mutation guard

**Tasks**

1. Hash relative path, type, executable mode, and bytes for every fixture file.
2. exclude only generated runner-owned temporary paths;
3. compare before and after snapshots;
4. detect changes to already dirty files, new files, deletion, rename, symlink, and mode
   changes;
5. retain only paths and hashes in diagnostics, not file content;
6. fail the provider call with `MUTATION_DETECTED`.

**Acceptance**

- every mutation fixture is detected;
- an unchanged dirty fixture passes;
- no test depends only on `git status`;
- the Cognitive OS worktree is not used for live-smoke mutation proof.

### S21C2-022 — Harden redaction and secret scanning

- **Priority:** P0
- **Depends on:** S21C2-011
- **Output:** shared redaction and provider-output scan policy

**Tasks**

1. Retain existing secret-name and environment-value redaction.
2. add authorization-header, bearer-token, URL credential, common API-key, and login
   identity patterns;
3. redact before logging, error normalization, event creation, and artifact creation;
4. distinguish scan not run, pass, and fail;
5. store scan evidence hash and rule-set version, not matched secret text;
6. add adversarial nested, split-field, stderr, and provider-error fixtures.

**Acceptance**

- zero seeded secret values survive in any persisted surface;
- a scan failure prevents normalized-content retention;
- redaction does not silently make a failed scan pass;
- health output contains no personal account identifiers.

### S21C2-023 — Add provider factory and normalized health

- **Priority:** P0
- **Depends on:** S21C2-010
- **Output:** small configuration-to-provider construction boundary

**Tasks**

1. Build MiniMax, replay, Claude Code, OpenRouter, and Codex adapters from validated
   schemas.
2. register through the existing registry;
3. normalize installed, configured, authenticated, reachable, model-ready, and policy
   status;
4. keep health read-only and inference-free;
5. avoid dynamic plugin loading or import-string configuration.

**Acceptance**

- all adapters construct through one explicit match;
- unknown adapters fail closed;
- health performs no completion and retains no secret;
- existing registry tests remain green.

### S21C2-024 — Build process and network replay fixtures

- **Priority:** P0
- **Depends on:** S21C2-020, S21C2-023
- **Output:** deterministic fake process and HTTP transports

**Tasks**

1. Cover success, malformed output, timeout, cancellation, cap overflow, non-zero exit,
   missing binary, login failure, and mutation.
2. cover OpenRouter catalog, completion, routing metadata, HTTP error, and malformed
   response paths;
3. assert exact request safety fields without real network;
4. run fixtures on all normal CI platforms;
5. ensure fake artifact records are created through real in-memory Artifact Service
   behavior.

**Acceptance**

- normal CI requires no provider binary, key, login, network, or GPU;
- replay results are deterministic;
- fixtures cannot be mistaken for live or real governed outcomes.

## EPIC S21C2-E03 — OpenRouter

### S21C2-030 — Implement the OpenRouter adapter

- **Priority:** P0
- **Depends on:** S21C2-010, S21C2-023, S21C2-024
- **Output:** `ModelProviderPort` implementation using the existing OpenAI client

**Tasks**

1. Reuse the installed `AsyncOpenAI` client and existing normalized mappings.
2. keep OpenRouter headers, discovery, routing, and errors provider-specific;
3. send only normalized messages and allowlisted parameters;
4. record requested and resolved model, usage, finish reason, latency, and safe request
   ID;
5. enforce output and context caps;
6. prohibit raw response persistence.

**Acceptance**

- the adapter passes the shared provider contract;
- no new provider dependency is added;
- normalized replay matches the declared schema;
- request authorization is absent from every recorded surface.

### S21C2-031 — Add discovery and free-model policy

- **Priority:** P0
- **Depends on:** S21C2-030
- **Output:** runtime catalog and model-selection receipt

**Tasks**

1. Query the model catalog through a bounded health/discovery client.
2. support `openrouter/free`;
3. support an optional pinned free model only after runtime validation;
4. record requested route and actual resolved model;
5. cache catalog metadata with a short bounded lifetime and explicit timestamp;
6. reject paid-only routing when the configured maximum spend is zero.

**Acceptance**

- disappearance of a free model is typed `MODEL_UNAVAILABLE`;
- no current Gemma slug is treated as permanent;
- resolved-model identity is present in successful receipts;
- catalog failure does not weaken offline CI.

### S21C2-032 — Enforce OpenRouter data policy and typed failures

- **Priority:** P0
- **Depends on:** S21C2-030
- **Output:** privacy/routing policy and complete error mapping

**Tasks**

1. Add allowlisted zero-data-retention and data-collection preferences.
2. block internal/restricted content unless strict provider policy is satisfied;
3. map authentication, policy, credits, timeout, rate, invalid response, upstream, and
   no-endpoint failures;
4. allow retries only where the existing retry policy proves safety;
5. use one attempt for live smoke;
6. redact response bodies and metadata before error construction.

**Acceptance**

- every documented failure class has an offline fixture;
- a relaxed public-smoke policy requires explicit operator consent;
- no policy downgrade occurs automatically;
- retry cannot duplicate learned ingestion.

### S21C2-033 — Add OpenRouter health and live smoke

- **Priority:** P0
- **Depends on:** S21C2-031, S21C2-032
- **Output:** read-only health and opt-in smoke command

**Tasks**

1. Report configured, credential-present, catalog-reachable, and free-route-ready.
2. avoid completion during health;
3. require an explicit live flag and operator confirmation for smoke;
4. use a fixed public synthetic prompt, maximum 128 output tokens, one attempt, and zero
   configured paid spend;
5. emit a sanitized receipt with resolved model, hashes, policy, latency, usage, and
   status;
6. never print the key or raw response.

**Acceptance**

- health works without a key and reports typed not-ready;
- offline smoke replay passes in CI;
- one real operator-approved smoke succeeds for Gate C2;
- live evidence is clearly labeled and contains no content or secret.

## EPIC S21C2-E04 — Claude Code advisory hardening

### S21C2-040 — Move Claude Code to the shared runner

- **Priority:** P0
- **Depends on:** S21C2-020, S21C2-021
- **Output:** hardened Claude Code advisory adapter

**Tasks**

1. Remove prompt content from argv.
2. use structured print mode and checked JSON schema;
3. enforce plan/safe mode, strict empty MCP, no session persistence, and read-only
   tools;
4. set bounded turns and process limits;
5. normalize successful content through existing response contracts;
6. reject any adapter configuration that enables mutation tools.

**Acceptance**

- actual argv contains only approved flags and paths;
- `Bash`, `Edit`, `Write`, MCP, web, and delegation are structurally absent;
- existing Claude mapping behavior remains compatible;
- the adapter passes the shared provider contract.

### S21C2-041 — Harden Claude health and output mapping

- **Priority:** P0
- **Depends on:** S21C2-040
- **Output:** sanitized health and typed structured results

**Tasks**

1. Probe binary version and coarse login state.
2. discard identity-bearing auth fields;
3. map schema-valid result, usage, finish, and warnings;
4. normalize missing login, unsupported flag, malformed JSON, process failure, timeout,
   cap, cancellation, and mutation;
5. retain no raw stderr.

**Acceptance**

- health cannot disclose an account identity;
- every failure has a deterministic fixture;
- schema-valid but verifier-unchecked output remains unverified.

### S21C2-042 — Prove Claude process and mutation safety

- **Priority:** P0
- **Depends on:** S21C2-040, S21C2-041
- **Output:** adversarial Claude adapter test suite

**Tasks**

1. Assert exact safety arguments from a fake executable.
2. attempt writes, deletion, rename, mode change, child-process escape, and large output;
3. test timeout and cancellation cleanup;
4. test an already dirty fixture;
5. test secret-like stderr and auth payloads.

**Acceptance**

- all mutations fail closed;
- no child process remains;
- no seeded secret or identity survives;
- live smoke uses the same runner and policy as replay.

### S21C2-043 — Add Claude Code live smoke

- **Priority:** P0
- **Depends on:** S21C2-042
- **Output:** opt-in operator smoke and sanitized receipt

**Tasks**

1. Copy the committed public synthetic advisory fixture to a temporary directory.
2. capture the pre-execution content snapshot;
3. run one structured, one-turn read-only advisory;
4. validate schema and a deterministic expected finding;
5. compare the post-execution snapshot;
6. emit only hashes, version, coarse auth method, timing, and status.

**Acceptance**

- one operator-approved smoke succeeds;
- the expected finding is independently verified;
- the fixture is byte-for-byte and mode-for-mode unchanged;
- no Cognitive OS repository content is sent.

## EPIC S21C2-E05 — Codex CLI advisory adapter

### S21C2-050 — Implement the Codex CLI adapter

- **Priority:** P0
- **Depends on:** S21C2-020, S21C2-021, S21C2-023
- **Output:** new read-only Codex `ModelProviderPort`

**Tasks**

1. Build the exact safe `codex exec` argument profile from Section 4.10.
2. deliver prompt by stdin;
3. generate the output schema and empty tool/MCP configuration in runner-owned
   temporary files;
4. enforce explicit isolated working directory;
5. map the final structured output to normalized response contracts;
6. reject any bypass, writable sandbox, approval, resume, or user-config inheritance.

**Acceptance**

- adapter construction cannot select unsafe flags;
- actual argv and stdin are separately asserted;
- the adapter passes the shared provider contract;
- no custom repository configuration can widen authority.

### S21C2-051 — Normalize Codex JSONL, schema, and health

- **Priority:** P0
- **Depends on:** S21C2-050
- **Output:** bounded parser and sanitized health

**Tasks**

1. Parse JSONL incrementally within the stdout cap.
2. allowlist required event types and ignore only documented non-authoritative events;
3. require the final output schema;
4. probe version and coarse login state;
5. discard login identity and raw event content not required by the normalized result;
6. type missing binary, login, unsupported flag, malformed JSONL, missing final output,
   timeout, cap, cancellation, and mutation.

**Acceptance**

- malformed or truncated JSONL fails closed;
- unknown authority-bearing event types fail closed;
- health contains no account identity;
- parser memory is bounded by the output cap.

### S21C2-052 — Prove Codex process and mutation safety

- **Priority:** P0
- **Depends on:** S21C2-050, S21C2-051
- **Output:** adversarial Codex adapter test suite

**Tasks**

1. Assert exact safe flags through a fake executable.
2. attempt file writes, deletion, rename, mode change, child escape, oversized JSONL,
   and stderr leakage;
3. test timeout and cancellation;
4. test already dirty fixture mutation;
5. assert temporary config and schema cleanup.

**Acceptance**

- every attempted mutation or authority widening fails;
- no process or temporary secret-bearing file remains;
- no bypass flag is accepted by configuration or construction.

### S21C2-053 — Add Codex live smoke

- **Priority:** P0
- **Depends on:** S21C2-052
- **Output:** opt-in operator smoke and sanitized receipt

**Tasks**

1. Copy the same public synthetic advisory fixture to a new temporary directory.
2. run one ephemeral, structured, read-only advisory;
3. validate the output schema and deterministic expected finding;
4. compare the complete content snapshot;
5. emit only version, coarse auth method, hashes, timing, and status;
6. remove runner-owned temporary files.

**Acceptance**

- one operator-approved smoke succeeds;
- the independent fixture verifier passes;
- the fixture remains unchanged;
- no Cognitive OS repository content or credential is sent or retained.

## EPIC S21C2-E06 — Provider-output governance and learned intake

### S21C2-060 — Create migration `0015`

- **Priority:** P0
- **Depends on:** S21C2-011, S21C2-013
- **Output:** one append-only provider-output governance table

**Tasks**

1. Add table metadata and migration from `0014`.
2. add append-only trigger, controlled record function, constraints, indexes, and grants;
3. update the expected Alembic head;
4. add narrow drift handling only if reflection proves it necessary;
5. implement clean upgrade/downgrade and incremental upgrade;
6. invoke the controlled function with UUID, integer, boolean, timestamp, enum, JSON,
   nullable, and artifact fields in W1.

**Acceptance**

- `0015` is the single head;
- direct function invocation writes and returns correctly typed values;
- update/delete fail under the app role;
- idempotent replay succeeds and conflicting reuse fails;
- migration, drift, grants, and downgrade/upgrade tests pass.

### S21C2-061 — Implement memory and PostgreSQL repositories

- **Priority:** P0
- **Depends on:** S21C2-013, S21C2-060
- **Output:** two repository implementations passing one shared suite

**Tasks**

1. Implement record, revision, latest, source resolution, and eligibility listing.
2. use one unchanged shared contract suite;
3. enforce bounded pagination and deterministic ordering;
4. validate persisted payload hash on read;
5. fail closed on missing event or artifact linkage;
6. add concurrency tests for revision and idempotency races.

**Acceptance**

- both stores pass the same suite unchanged;
- restart preserves records and eligibility;
- corruption, broken lineage, and expired latest revision are visible;
- no hidden in-memory current-state authority exists.

### S21C2-062 — Add governed teacher orchestration

- **Priority:** P0
- **Depends on:** S21C2-013, S21C2-022, S21C2-061
- **Output:** one service from provider execution to governed receipt

**Tasks**

1. Require an explicit retention and intended-use directive.
2. execute the provider exactly once;
3. collect event ID, hashes, safe metadata, rights, sensitivity, scan, and verifier
   evidence;
4. store normalized bytes only when policy permits;
5. record one governance revision;
6. create the source reference and call learned intake;
7. return provider, governance, and intake receipts.

**Acceptance**

- retries cannot duplicate provider-output or learned records;
- default execution retains no request/response bytes;
- a persistence failure cannot be reported as learned success;
- no service call reaches active memory or activation.

### S21C2-063 — Integrate provider source kinds with learned intake

- **Priority:** P0
- **Depends on:** S21C2-061, S21C2-062
- **Output:** exact source resolver and provider-specific classification

**Tasks**

1. Add the three provider source kinds to the verifier-backed allowlist only.
2. resolve the latest valid governance revision and response hash;
3. map provenance, attribution, rights, sensitivity, verifier status, and evidence hash;
4. quarantine missing or inconclusive verification;
5. reject prohibited rights, failed scan, invalid source, or inconsistent hash;
6. keep provider output non-real unless an actual governed run produced it.

**Acceptance**

- verified eligible fixture input follows the expected intake policy;
- unverified provider output quarantines;
- prohibited or corrupt output rejects;
- zero provider source kinds appear in `REAL_GOVERNED_SOURCE_KINDS`.

### S21C2-064 — Enforce retention revision and expiry

- **Priority:** P0
- **Depends on:** S21C2-061, S21C2-062
- **Output:** deterministic eligibility and supersession policy

**Tasks**

1. Implement rights revocation, verifier correction, sensitivity correction, and expiry
   as revisions.
2. exclude superseded, expired, prohibited, and failed-scan records from new use;
3. prohibit normalized content with physical deletion obligations;
4. verify retained artifact hash and existence;
5. preserve historical observation and access audit;
6. add boundary-time tests with an injected clock.

**Acceptance**

- eligibility changes only through a new immutable revision;
- exact expiry is deterministic;
- missing or corrupt retained content is unhealthy;
- no test claims that immutable bytes were physically deleted.

### S21C2-065 — Add provider-output health, backup, and restore

- **Priority:** P0
- **Depends on:** S21C2-060, S21C2-061, S21C2-064
- **Output:** operational integrity coverage

**Tasks**

1. Check table, function, trigger, grants, revision continuity, hash validity, event
   linkage, artifact linkage, and expiry consistency.
2. distinguish integrity failures from provider reachability warnings;
3. extend backup and restore table manifests;
4. restore into a fresh database and artifact root;
5. replay source resolution and learned intake after restart;
6. verify artifacts through existing Artifact Service tooling.

**Acceptance**

- integrity failure makes governance health unhealthy;
- provider offline status does not imply ledger corruption;
- backup/restore preserves counts, hashes, revisions, and links;
- release evidence uses only the isolated consistent pair.

## EPIC S21C2-E07 — Verification, operations, and release

### S21C2-070 — Add a unified provider health and smoke CLI

- **Priority:** P0
- **Depends on:** S21C2-033, S21C2-041, S21C2-051, S21C2-065
- **Output:** safe operator commands

**Tasks**

1. Add provider list, health, replay smoke, live smoke, and governance verify commands.
2. require provider selection and an explicit live opt-in;
3. display typed status and sanitized receipts;
4. default to no network and no output retention;
5. refuse live operation outside an isolated fixture root;
6. document exit codes.

**Acceptance**

- health and replay work without credentials;
- live execution cannot occur accidentally;
- CLI output contains no prompt, response, secret, identity, or raw stderr;
- every command has deterministic tests.

### S21C2-071 — Commit one synthetic advisory fixture and verifier

- **Priority:** P0
- **Depends on:** S21C2-012
- **Output:** public, rights-clean, deterministic cross-provider fixture

**Tasks**

1. Create a tiny text or code fixture with one known, read-only diagnosable defect.
2. include provenance, rights, expected structured finding, and content manifest;
3. implement an independent deterministic verifier;
4. prevent schema-only success from counting as correct;
5. prohibit repository-specific or sensitive content.

**Acceptance**

- all providers can receive the same task;
- the verifier accepts only the expected finding;
- fixture hashes are stable;
- fixture provenance cannot be mistaken for a real user outcome.

### S21C2-072 — Add offline contract and failure benchmark

- **Priority:** P0
- **Depends on:** S21C2-024, S21C2-063, S21C2-071
- **Output:** deterministic provider boundary benchmark

**Tasks**

1. Add at least 24 fixed CI cases across the three providers and governance path.
2. add at least 72 fixed-seed policy/failure cases;
3. cover success, typed failures, retry/idempotency, retention, rights, scan, verifier,
   expiry, mutation, and cleanup;
4. report expected-policy match and resource measurements;
5. prohibit network, credentials, real CLI binaries, and GPU.

**Acceptance**

- expected-policy match is 100%;
- zero test fixture is labeled as a live or real governed run;
- repeated seeds produce identical receipts and hashes;
- execution remains within the existing CI timeout.

### S21C2-073 — Open the draft PR in W1

- **Priority:** P0
- **Depends on:** S21C2-010 through S21C2-013, initial S21C2-020, initial S21C2-060
- **Output:** early remote integration feedback

**Tasks**

1. Open a draft PR after schemas, configuration, runner skeleton, table, and controlled
   function smoke compile.
2. ensure the provider lane installs only declared extras;
3. run direct `0015` function invocation in PostgreSQL CI;
4. run schema drift, language, security, and packaging checks;
5. keep live smokes excluded from normal CI.

**Acceptance**

- CI exercises the controlled function, not just migration application;
- no missing dependency is converted into a skip;
- remote defects are addressed before adapter closeout.

### S21C2-074 — Run the complete local verification matrix

- **Priority:** P0
- **Depends on:** S21C2-065, S21C2-072
- **Output:** command-by-command local evidence

**Tasks**

1. Run provider, learned intake, event, artifact, config, schema, and contract suites.
2. run PostgreSQL owner/app integration;
3. run migration clean/incremental/downgrade/upgrade/drift;
4. run backup/restore/restart;
5. run security, secret scan, mutation, process cleanup, language, packaging, lint, and
   format checks;
6. run the full repository test suite;
7. record command, head, start/end, duration, exit, and non-secret result.

**Acceptance**

- every required command has the expected exit status;
- no unexplained skip or warning hides provider behavior;
- no release evidence touches the inconsistent development pair;
- full-suite regressions are zero.

### S21C2-075 — Execute three operator-approved live smokes

- **Priority:** P0
- **Depends on:** S21C2-033, S21C2-043, S21C2-053, S21C2-071, S21C2-074
- **Output:** sanitized OpenRouter, Claude Code, and Codex live evidence

**Tasks**

1. Obtain explicit operator approval for the bounded live run.
2. verify the public synthetic fixture and isolation root;
3. execute one call per provider with the declared caps;
4. independently verify each structured result;
5. verify content snapshots after both CLI calls;
6. retain only sanitized hashes, versions, provider/model identity, policy, usage,
   timing, and status;
7. destroy runner-owned temporary files without deleting evidence stores.

**Acceptance**

- all three calls succeed;
- OpenRouter records the resolved free model;
- both CLI fixture trees remain unchanged;
- zero content, credential, identity, or raw provider payload is retained;
- failure causes Gate C2 to remain open rather than weakening policy.

### S21C2-076 — Update operator and security documentation

- **Priority:** P0
- **Depends on:** S21C2-070
- **Output:** configuration, authentication, retention, and incident runbooks

**Tasks**

1. Document local subscription use versus unattended authentication.
2. document OpenRouter key handling, zero-spend defaults, and data-policy decisions;
3. document CLI read-only flags, version compatibility, and isolation;
4. document retention modes, rights review, sensitivity, expiry, and immutable-byte
   limitation;
5. document typed failures and safe rerun rules;
6. document that Artifact Store remediation and provider credential recovery need
   separate operator authority.

**Acceptance**

- examples contain placeholders only;
- no instruction copies subscription credentials;
- operator procedures do not bypass safety flags;
- deferred risks have explicit owners.

### S21C2-077 — Produce Gate C2 assessment and sprint report

- **Priority:** P0
- **Depends on:** S21C2-074, S21C2-075, S21C2-076
- **Output:** Gate C2 evidence matrix and C2 report

**Tasks**

1. Evaluate all fourteen Gate C2 conditions.
2. link local, PostgreSQL, replay, live, PR, and migration evidence;
3. report exact test counts and all skips;
4. report both inherited limitations without hiding them;
5. separate provider availability from learned usefulness;
6. state Gate L2 closed using the required wording;
7. leave future release handles to tag annotation.

**Acceptance**

- every gate condition has pass/fail and evidence;
- no conditional item is reported as pass;
- no live fixture is counted as a real governed outcome;
- limitations and residual risks are explicit.

### S21C2-078 — Complete protected release and baseline tag

- **Priority:** P0
- **Depends on:** S21C2-077
- **Output:** merged, CI-verified, remotely tagged provider baseline

**Tasks**

1. Convert the draft PR to ready only after local evidence is green.
2. wait for all required checks;
3. merge without weakening or bypassing protection;
4. verify remote `main` at the exact merge/evidence commit;
5. wait for successful post-merge `main` CI;
6. create one annotated `sprint-21c2-provider-baseline` tag;
7. include final PR, merge, CI, migration, Gate C2, Gate L2, live-smoke, reviewer, and
   Artifact Store limitation evidence in the annotation;
8. push once and verify remote tag object and peeled commit.

**Acceptance**

- all required checks and exact-head post-merge CI succeed;
- one tag object exists and peels to final `main`;
- the tag is not moved;
- required reviews remain unchanged unless a second eligible reviewer was confirmed;
- Gate C2 passes and Gate L2 remains closed.

### S21C2-079 — Prepare Sprint 21C3 handoff

- **Priority:** P0
- **Depends on:** S21C2-077
- **Output:** exact C3 starting contract

**Tasks**

1. Record parent tag and peeled commit.
2. record migration head `0015` and next available revision;
3. inventory provider, governance, intake, replay, health, and live-smoke APIs;
4. record data-policy, retention, verifier, and source-kind invariants;
5. list known failures and accepted limitations;
6. recommend branch `feature/sprint-21c3-reality-inputs`;
7. keep the 200-outcome and executable corpus work in C3.

**Acceptance**

- C3 can start without inferring provider authority or storage semantics;
- unresolved limitations have an owner;
- no useful-learning or Gate L2 claim is carried forward prematurely.

---

## 7. Execution waves and pull-request strategy

### 7.1 Dependency order

| Wave | Work items | Exit |
|---|---|---|
| W0 — control | 000–004 | verified parent, current protection, isolated stores, ADR, version manifest |
| W1 — contract skeleton | 010–013, initial 020, initial 060, 073 | schemas, runner skeleton, table, and actual controlled-function call green in draft PR |
| W2 — shared safety | 020–024 | process, mutation, redaction, factory, replay boundaries green |
| W3 — provider adapters | 030–033, 040–043, 050–053 | all three provider contracts and offline failure paths green |
| W4 — governance | 060–065 | durable retention, revisions, source resolution, intake, health, backup/restore green |
| W5 — verification | 070–076 | synthetic verifier, offline benchmark, full local matrix, three live smokes green |
| W6 — closeout | 077–079 | Gate C2, report, protected release, tag, and C3 handoff complete |

No wave may claim completion while a P0 dependency is red.

### 7.2 Early pull-request rule

The draft PR opens in W1. Its first coherent checkpoint must include:

- versioned provider configuration;
- provider-output contracts and schemas;
- bounded runner interface;
- `0015` table and controlled write function;
- a PostgreSQL test that invokes the function with all non-text types;
- schema drift and repository-language checks;
- credential-free CI configuration.

### 7.3 Implementation split rule

Use one implementation PR by default. Split only if:

- the contract/migration change is independently releasable and reviewed before adapter
  work; or
- a security review requires the process boundary to merge separately.

Do not split to bypass checks, hide a red gate, or merge an authority-bearing provider
path before its governance record exists.

### 7.4 Live evidence rule

Live smoke is:

- opt-in and operator-approved;
- outside normal CI;
- executed only after offline and local security evidence passes;
- limited to one public synthetic task per provider;
- zero-spend by configuration for OpenRouter;
- non-mutating and read-only for CLI providers;
- recorded as sanitized evidence, not raw content;
- required for Gate C2 but never a reusable credential or unattended job.

---

## 8. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| source | exact parent and final SHA/tag objects | wrong baseline or unreproducible release |
| configuration | adapter discrimination and unsafe-value rejection | ambiguous or widened authority |
| contracts | schema, hash, revision, rights, expiry tests | governance evidence cannot be trusted |
| subprocess | stdin, caps, environment, cleanup | prompt/secret leak or orphan execution |
| mutation | content-and-mode before/after equality | advisory provider changed the fixture |
| redaction | adversarial secret/identity fixtures | sensitive data can persist |
| OpenRouter | discovery, mapping, policy, typed errors | network teacher is uncontrolled |
| Claude Code | exact flags, schema, health, faults | subscription CLI has excessive authority |
| Codex | exact flags, JSONL/schema, health, faults | subscription CLI has excessive authority |
| persistence parity | unchanged shared repository suite | port semantics are ambiguous |
| PostgreSQL | controlled function and app-role tests | runtime ledger writes can fail or bypass policy |
| learned intake | accept/quarantine/reject and source resolution | provider output contaminates evidence |
| artifacts/events | exact hashes and envelope IDs | lineage is incomplete or corrupt |
| health | integrity versus availability split | outage is mistaken for corruption or vice versa |
| migration | clean, incremental, downgrade, drift | release is not deployable |
| backup/restore | counts, hashes, revisions, events, artifacts | provider evidence is not recoverable |
| offline benchmark | 24 CI and 72 seeded cases at 100% | bounded policies regress |
| live smoke | three successful sanitized receipts | provider path has not been demonstrated |
| full suite | repository-wide tests | cross-sprint regression |
| PR CI | all required checks | remote integration unresolved |
| post-merge CI | exact final `main` head | release not validated |
| tag | local/remote object and peeled SHA | baseline not reproducible |

---

## 9. Quantitative acceptance thresholds

### 9.1 Correctness

- 100% of provider, process, governance, repository, migration, and intake tests pass.
- 100% expected-policy match across at least 24 fixed CI cases and 72 fixed-seed cases.
- 0 provider source kinds enter `REAL_GOVERNED_SOURCE_KINDS`.
- 0 unverified provider outputs enter an eligible corpus/training selection.
- 0 providers approve, activate, review their own quarantine, or write active memory.
- 0 idempotency conflicts succeed.
- 0 missing or corrupt retained artifacts report healthy.

### 9.2 Process safety

- 0 prompts in process arguments.
- 0 shell-based provider launches.
- 0 processes remain after timeout, cap, cancellation, parser, or mutation failure.
- 0 unauthorized file, mode, symlink, creation, deletion, or rename changes pass.
- retained stdout and stderr never exceed configured caps.
- runtime never accepts a limit above the hard maxima without an ADR change.

### 9.3 Data and credential safety

- 0 credentials, authorization headers, secret values, login identities, raw provider
  bodies, or raw stderr enter logs, artifacts, events, reports, fixtures, or Git.
- 0 normalized-content artifacts exist without verified rights, passed scan, permitted
  sensitivity, and compatible retention.
- 0 internal or restricted OpenRouter prompts use an endpoint policy that permits
  disallowed collection.
- 0 provider calls or credential reads occur in normal CI.

### 9.4 Durability

- all governance records survive application and PostgreSQL restart;
- backup/restore preserves record counts, hashes, revisions, event IDs, and artifact
  links;
- app-role update/delete against the ledger always fails;
- the controlled function succeeds for every declared PostgreSQL type;
- the original inconsistent development Artifact Store pair receives 0 C2 writes.

### 9.5 Live evidence

- exactly one gate smoke per provider unless a failed attempt must be retried after a
  recorded typed failure;
- each successful result passes the independent fixture verifier;
- OpenRouter records requested route and resolved model;
- both CLI fixture snapshots are unchanged;
- live evidence retains hashes and normalized metadata only.

### 9.6 Performance guardrail

C2 is not a provider-throughput sprint. Still:

- the 72-case seeded run must complete inside the existing CI timeout;
- subprocess memory is bounded by output caps;
- provider-output lists use bounded pagination;
- catalog discovery and health have bounded timeouts;
- health performs no completion;
- elapsed time and peak resident memory are recorded for trend comparison.

---

## 10. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| no second reviewer | one collaborator remains | retain checks and `enforce_admins`; report limitation; do not fabricate approval |
| development Artifact Store drift | missing/orphan pair remains | isolate C2; no mutation; await separate operator approval |
| migration function type defect | migration applies but function fails | block W1; invoke every typed field directly; fix before repository wave |
| artifact metadata without bytes | fixture writes metadata directly | replace with real `ArtifactService` write; fail restore evidence |
| CLI flag drift | required safety flag absent or renamed | mark adapter unhealthy; update compatibility manifest and tests; do not substitute a weaker flag |
| prompt appears in argv | adapter passes prompt positionally | block release; use stdin through shared runner |
| dirty-tree mutation is missed | `git status` is unchanged | use content-and-mode snapshot; block adapter |
| child process survives | timeout/cancel/cap returns first | block release; fix process-group cleanup |
| provider output self-verifies | same provider identity supplies verdict | quarantine; require independent deterministic or human verifier |
| free OpenRouter route changes | pinned slug disappears or quota changes | runtime discovery and typed unavailable/quota result; keep offline CI green |
| strict data policy has no free endpoint | no compatible route | do not send internal/restricted data; use explicitly approved public synthetic smoke or keep live gate open |
| immutable artifact conflicts with expiry | policy requires physical deletion | retain hash only or none; do not promise deletion |
| provider output becomes real evidence | source kind added to real allowlist | block release and remove it |
| raw provider payload retained | raw policy or body reaches artifact/event | block release; normalized content only under explicit governance |
| subscription credential automation appears | code copies CLI login state | remove path; keep authentication external and operator-initiated |
| provider connectivity presented as learning | report implies Gate L2 | correct report; Gate L2 remains closed |
| live smoke leaks repository content | workdir is Cognitive OS checkout | stop call; use copied public synthetic fixture |
| new general framework appears | plugin/workflow/provider platform added | remove or defer; use existing registry and one small factory |

---

## 11. External source basis

Implementation must revalidate current provider behavior at sprint start. The backlog
was prepared against these official sources:

- OpenRouter quick start and OpenAI SDK compatibility:
  <https://openrouter.ai/docs/quickstart>
- OpenRouter free router:
  <https://openrouter.ai/openrouter/free/api>
- OpenRouter model discovery:
  <https://openrouter.ai/docs/guides/overview/models>
- OpenRouter free variants:
  <https://openrouter.ai/docs/guides/routing/model-variants/free>
- OpenRouter errors:
  <https://openrouter.ai/docs/api/reference/errors-and-debugging>
- OpenRouter zero-data-retention policy:
  <https://openrouter.ai/docs/guides/features/zdr>
- OpenRouter data-collection policy:
  <https://openrouter.ai/docs/guides/privacy/data-collection>
- OpenRouter provider selection:
  <https://openrouter.ai/docs/guides/routing/provider-selection>
- Codex command reference:
  <https://learn.chatgpt.com/docs/developer-commands#codex-exec>
- Codex sandbox configuration:
  <https://learn.chatgpt.com/docs/sandboxing#configure-defaults>
- Claude Code CLI reference:
  <https://code.claude.com/docs/en/cli-usage>
- Claude Code permission modes:
  <https://code.claude.com/docs/en/permission-modes>

Official documentation does not replace runtime capability probing. Only flags verified
for the installed CLI version may be emitted.

---

## 12. Definition of Done

Sprint 21C2 is complete only when:

- all P0 items are complete;
- any P1 deferral is explicit and cannot weaken Gate C2;
- C1 parent handles and migration are exact;
- remote protection remains intact;
- the inconsistent development Artifact Store pair remains untouched;
- OpenRouter, Claude Code, and Codex pass one shared normalized provider contract;
- CLI execution is read-only, bounded, prompt-safe, environment-safe, and process-clean;
- provider configuration cannot widen authority;
- provider output defaults to transient;
- retained output has explicit rights, intended use, sensitivity, scan, verifier,
  retention, and expiry evidence;
- migration `0015`, repositories, health, backup, restore, and restart pass;
- provider output reaches learned intake only through the governed source resolver;
- unverified output quarantines and no provider is a real-run source by default;
- normal CI is offline, credential-free, CLI-independent, and deterministic;
- all three operator-approved live smokes succeed with sanitized evidence;
- focused and full local suites pass;
- all required PR checks pass;
- post-merge `main` CI passes on the exact final head;
- one annotated `sprint-21c2-provider-baseline` tag is created and remotely verified;
- the report states Gate C2 pass and Gate L2 closed;
- the C3 handoff freezes APIs, migration, residual risks, and exact parent.

---

## 13. Expected deliverables

At minimum, Sprint 21C2 should produce:

- this backlog and one provider-boundary ADR;
- versioned provider configuration and construction;
- shared bounded CLI process runner and content mutation guard;
- hardened Claude Code advisory adapter;
- OpenRouter adapter using the existing OpenAI Python client;
- new Codex CLI advisory adapter;
- provider-output governance contracts and schemas;
- migration `0015_create_provider_output_governance.py`;
- in-memory and PostgreSQL provider-output repositories;
- governed teacher orchestration and learned-intake source resolver;
- normalized provider health and safe operator CLI;
- credential-free HTTP/process replay fixtures;
- one public synthetic cross-provider fixture and independent verifier;
- at least 24 fixed CI and 72 fixed-seed provider/governance cases;
- migration, repository, redaction, mutation, cleanup, backup, restore, restart, and
  corruption tests;
- one sanitized operator-approved live-smoke receipt per provider;
- an early draft PR with actual controlled-function PostgreSQL coverage;
- updated configuration, security, retention, and operator documentation;
- `docs/sprints/sprint-21/gate-c2-assessment.md`;
- a Sprint 21C2 report;
- annotated `sprint-21c2-provider-baseline`;
- Sprint 21C3 handoff.
