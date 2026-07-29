# Sprint 21C3 Technical Backlog

## Reality-Grade Learning Inputs

- **Document type:** implementation-ready technical backlog
- **Status:** ready for execution
- **Revision:** 1
- **Prepared:** 2026-07-29
- **Required parent baseline:** `sprint-21c2-provider-baseline`
- **Required parent tag object:** `23b3304890f4a90112514c633c7e2b768f7eeeff`
- **Required parent commit:** `94abe263c8f26f36c8f8c3bc7b86859c14c1f291`
- **Required parent post-merge CI:** `30434494612`, success, 28 of 28 checks
- **Required parent migration head:** `0015`
- **Implementation branch:** `feature/sprint-21c3-reality-inputs`
- **Planned migration:** none
- **Next available migration:** `0016`, evidence-gated only
- **Target baseline tag:** `sprint-21c3-reality-baseline`
- **Stage gate:** Gate C3 — Reality-Grade Learning Inputs
- **Successor gate:** Gate L2 remains closed until a useful learned component passes the
  later training, anti-forgetting, OOD, shadow, promotion, and activation gates.
- **Execution profile:** local, CPU-first, single maintainer, offline normal CI,
  bounded provider-assisted campaign
- **Repository language:** English only

---

## 0. Authority and execution contract

This backlog is the execution authority for Sprint 21C3. It refines:

- `docs/sprints/sprint-21/sprint-21c2-report.md`;
- `docs/sprints/sprint-21/gate-c2-assessment.md`;
- `docs/sprints/sprint-21/sprint-21c3-handoff.md`;
- the final `sprint-21c2-provider-baseline` tag annotation;
- `docs/sprints/sprint-22/development-plan.md`;
- `docs/sprints/sprint-22/execution-sprint-allocation.md`;
- the project owner's 2026-07-29 open-development data-policy decision.

If an implementation detail conflicts with a confirmed repository invariant, the
implementer must:

1. preserve evidence integrity, credential isolation, source rights, and release
   reproducibility;
2. record the conflict and decision in the C3 report;
3. update the relevant ADR before changing authority, corpus-role, verifier, retention,
   or activation semantics;
4. prefer the shortest existing repository path that produces honest evidence;
5. avoid silently broadening C3 into training or activation.

### 0.1 Release-grade meaning of done

Sprint 21C3 is not complete when 30 fixture directories exist. Completion requires:

1. exact verification of the C2 tag object, peeled commit, remote `main`, post-merge CI,
   and migration head;
2. implementation and validation of all P0 work;
3. at least 30 rights-clean executable coding tasks;
4. at least 200 unique verifier-backed executed outcomes;
5. at least 50 distinct failed-to-corrected trajectories;
6. group-aware leakage and hidden-verifier evidence;
7. one real local CPU embedding model with immutable identity and retrieval evidence;
8. a measured full-precision versus half-precision storage decision;
9. deterministic offline CI and isolated PostgreSQL, Artifact Store, sandbox, and
   provider-campaign evidence;
10. a pull request with all required checks green;
11. merge to `main` without weakening protection;
12. successful post-merge `main` CI on the exact merged head;
13. one annotated baseline tag created once and verified remotely;
14. a complete C3 report, Gate C3 assessment, and D1 handoff.

Final PR, merge, CI, and tag handles belong in the tag annotation or external release
evidence, not in a tracked self-referential report.

### 0.2 Efficiency-first implementation rule

The implementation order is:

1. reuse an existing contract, service, repository, tool, or script;
2. use the standard library;
3. use an already installed dependency;
4. add the smallest focused code needed for C3.

Specifically:

- do not add a new corpus database;
- do not add a new trajectory database;
- do not add a new vector database;
- do not add a provider router or learned routing policy;
- do not add a second sandbox or worktree implementation;
- do not add a second Artifact Store or Event Store;
- do not add a model-serving process;
- do not create migration `0016` merely because the number is available.

### 0.3 Open-development data policy

The project is an open, non-enterprise development project. Effective for C3 and later
sprints:

- project-owned source, generated fixtures, task descriptions, public benchmark data,
  provider prompts derived from them, provider answers, and execution evidence are
  treated as `public` open-development data unless a source explicitly says otherwise;
- OpenRouter zero-data-retention is not required for open-development data;
- provider-side data collection may be enabled for open-development data;
- ZDR relaxation is a configuration decision, not a per-request operator exception;
- storing and sharing open-development data is permitted;
- the tracked OpenRouter example configuration must use the relaxed project default;
- zero-spend and free-model selection remain independent cost controls;
- provider correctness still requires an independent verifier.

This decision does not make credentials public. API keys, tokens, authorization headers,
subscription login material, and third-party data with explicit restrictions remain
excluded from prompts, logs, artifacts, fixtures, and Git. Source licence and usage-rights
metadata remain required because redistribution rights are not a confidentiality question.

### 0.4 Provider-efficiency rule

The measured C2 provider order for C3 is:

1. deterministic curated candidates for guaranteed campaign coverage;
2. Codex CLI and Claude Code for bounded provider diversity;
3. `openrouter/free` as a one-attempt, verifier-gated diversity source.

OpenRouter produced 5 correct results in 22 C2 attempts. C3 must not retry until it gets a
correct answer and must not depend on it for corpus completeness. A wrong or malformed
OpenRouter result is a valid verified failure outcome.

---

## 1. Starting evidence and inherited limitations

### 1.1 Verified Sprint 21C2 release

At backlog preparation:

- remote `main` resolves to
  `94abe263c8f26f36c8f8c3bc7b86859c14c1f291`;
- remote tag object `sprint-21c2-provider-baseline` resolves to
  `23b3304890f4a90112514c633c7e2b768f7eeeff`;
- the tag peels to the same commit as remote `main`;
- post-merge `main` CI run `30434494612` succeeded with 28 of 28 required checks;
- migration `0015` is the parent Alembic head;
- the final tag annotation closes Gate C2 condition 14;
- Gate C2 is passed for release purposes;
- Gate L2 is closed.

The implementation branch must start from the peeled tag commit, not from an unverified
branch name.

### 1.2 C2 evidence relevant to C3

- Full release suite: 2028 passed, 12 skipped.
- Offline provider benchmark: 35 CI plus 77 seed cases, 100% policy match.
- Local matrix: 37 commands at expected status.
- Claude Code and Codex answered the public advisory task correctly on every recorded
  attempt.
- OpenRouter free answered correctly 5 times in 22 attempts.
- Live provider calls exposed eight defects that offline fake transports did not find.
- The C2 controlled write function initially had the same migrate-clean/runtime-fail
  shape as the C1 migration defect.
- C2 restore testing again caught artifact metadata and filesystem bytes written to
  different roots.

### 1.3 C3 controls derived from those lessons

1. Open the draft PR in W1.
2. Invoke every new authority-bearing path end to end, not only its schema or constructor.
3. Run one bounded real-provider preflight before the provider campaign.
4. Use installed-client signature checks for OpenRouter extension parameters.
5. Pass network providers inlined, hash-pinned task content; never ask them to read a
   filesystem they cannot access.
6. Write every outcome and task artifact through `ArtifactService`.
7. Use one isolated database and artifact root for release evidence.
8. Count failed provider results honestly and never retry to manufacture an accuracy
   denominator.

### 1.4 Inconsistent development Artifact Store pair

The development pair remains outside C3 scope:

- path-and-size fingerprint begins `7e85d9a6`;
- five filesystem files;
- four declared blobs without content and five orphan files in the C1 inventory;
- zero C2 writes;
- remediation remains a proposal requiring separate operator authority.

C3 must produce zero writes to this pair. It must use a new isolated database and artifact
root. It must not delete or rewrite either side to make a verifier pass.

### 1.5 Reviewer limitation

There is one collaborator and no second eligible reviewer. Required approving reviews
remain disabled. This is the accepted single-maintainer release mode:

- retain all 27 required contexts;
- retain strict checks and `enforce_admins`;
- retain force-push and deletion protection;
- do not fabricate an approval;
- do not spend a sprint task repeatedly searching for a reviewer;
- re-evaluate only if collaborator state actually changes.

The missing reviewer is recorded but does not block implementation or release.

---

## 2. Sprint goal and Gate C3

### 2.1 Goal

Produce an honest, executable, reproducible input corpus on which Sprint 21D1 can
pre-register a real learning surface:

- at least 30 rights-clean coding repair tasks;
- baseline failures and hidden verifier outcomes;
- multiple genuinely different candidate strategies;
- at least 200 unique executed and verified outcomes;
- at least 50 failed-to-corrected trajectories;
- provider-assisted outcomes whose correctness is independently measured;
- strict separation between self-play corpus candidates and real-run evaluation evidence;
- a local English technical-text embedding model;
- measured retrieval quality, latency, memory, and vector-storage trade-offs.

### 2.2 Gate C3 pass conditions

Gate C3 passes only when all of the following are true:

1. the exact C2 parent tag object, peeled commit, remote `main`, final CI, and migration
   head are verified;
2. the open-development data-policy amendment is implemented, documented, and tested
   without weakening credential handling or source-rights tracking;
3. at least 30 task packages across at least six task families pass structural, licence,
   baseline-failure, and reproducibility checks;
4. hidden tests and solution-control material are unreachable from provider context,
   candidate features, embeddings, and selection inputs before scoring;
5. every candidate is executed in the existing rootless sandbox against the same hidden
   verifier and produces an immutable outcome artifact and Event Store reference;
6. at least 200 unique task or benchmark outcomes have verifier evidence and no duplicate
   event or outcome identity is counted twice;
7. at least 50 distinct failed-to-corrected trajectory manifests cover at least 20 unique
   tasks and at least two candidate-strategy families;
8. group-aware split, exact duplicate detection, normalized-code similarity checks, and a
   universal-patch adversary find no evaluation leakage or corpus shortcut;
9. OpenRouter is non-critical, single-attempt, ZDR-relaxed for open-development data, and
   reported with exact success/failure denominators;
10. real governed runs enter learned intake as evaluation-only evidence and zero enter a
    training snapshot;
11. self-play task/correction corpus candidates pass Corpus Factory rights, lineage,
    classification, and split checks without initiating training;
12. a pinned, locally stored `sentence-transformers/all-MiniLM-L6-v2` artifact produces
    normalized 384-dimensional embeddings on CPU with full model, revision, licence, and
    digest evidence;
13. a frozen retrieval benchmark passes the declared recall and ranking thresholds, and
    deterministic/hash embeddings remain test-only;
14. full-precision and half-precision storage are compared on identical vectors, queries,
    and splits, and the decision is recorded without an unjustified migration;
15. health, restart, backup/restore, artifact verification, campaign resume,
    deterministic replay, normal CI, and the full local matrix pass;
16. the protected merge, exact-head post-merge CI, one annotated tag, remote verification,
    report, gate assessment, and D1 handoff complete.

### 2.3 Gate L2 status

Gate C3 does not train or activate a learned component. The C3 report must state:

> Reality-grade inputs and local semantic retrieval are available, but useful learned
> behaviour has not yet been demonstrated.

Corpus volume and embedding retrieval are prerequisites. They are not material downstream
uplift, anti-forgetting evidence, shadow safety, or activation authorization.

---

## 3. Scope boundaries

### 3.1 In scope

- open-development data-policy amendment;
- 30 generated, rights-clean Python repair tasks;
- visible tests, hidden tests, control candidates, and candidate provenance;
- task-family and repository-group isolation;
- exact and normalized-code duplicate detection;
- hidden-test execution in the existing rootless Docker sandbox;
- baseline, curated, Codex, Claude Code, and OpenRouter candidate runs;
- immutable full coding-outcome artifacts and exact event linkage;
- coding task-run source resolution into learned intake;
- Experience Compiler trajectories;
- Corpus Factory task, correction, and evaluation manifests;
- at least 200 verified outcomes and 50 failed-to-corrected trajectories;
- provider reliability and corpus statistics;
- one local CPU Sentence Transformers model;
- exact semantic retrieval at 384 dimensions;
- full-precision versus half-precision measurement;
- offline replay, health, restart, backup/restore, CI, report, and release.

### 3.2 Explicitly out of scope

- fitting, training, promoting, or activating a learned component;
- opening Gate L2;
- EMG, graph alignment, FGW, or graph database work;
- learned provider routing;
- paid OpenRouter execution or automatic spend;
- retry-until-correct provider campaigns;
- a model server, ONNX conversion, quantized model runtime, GPU, CUDA, or LoRA;
- approximate index creation for the 200-item C3 corpus;
- a new vector database;
- a new coding agent, sandbox, worktree service, corpus factory, experience compiler,
  Event Store, Artifact Store, or learned evidence store;
- broad support for arbitrary languages or repositories;
- unrestricted dependency installation in task sandboxes;
- provider access to hidden tests or golden solutions;
- using real governed runs for training;
- repairing the inconsistent development Artifact Store pair;
- enabling impossible required reviews;
- committing model files, task databases, runtime traces, or credentials;
- migration `0016` without measured and accepted need.

### 3.3 Deferral ownership

| Deferred capability | Owner |
|---|---|
| pre-registration of the primary learned surface | Sprint 21D1 |
| EMG and simple correction-path graph retrieval | Sprint 21D1 |
| k-NN calibration or another trained selector | Sprint 21D2 |
| anti-forgetting, OOD, shadow, canary, activation | Sprint 21D2 |
| 384-dimensional approximate index | Sprint 22 scale work, unless C3 measurement proves an immediate need |
| local small-language-model inference | Sprint 22D |
| Artifact Store mismatch remediation | separately authorized maintenance |
| additional repository languages | later corpus expansion |

---

## 4. Minimal architecture

### 4.1 Reuse map

| Need | Existing authority to reuse |
|---|---|
| task and candidate execution | `CodingAgentFacade` |
| isolated repository | `WorkspaceManager` and `GitRepositoryService` |
| restricted execution | `DockerSandbox` and Tool Plane |
| visible verification | `CodingVerifierBundleFactory` |
| lifecycle evidence | `CodingEventService` and Event Store |
| bytes and manifests | existing `ArtifactService` |
| normalized trajectories | `ExperienceCompiler` and existing repositories |
| source rights, quality, splits | `CorpusFactory` |
| learned outcome classification | `LearnedObservationIntake` |
| immutable evaluation dataset | `LearnedDatasetBuilder` |
| embeddings | `EmbeddingProviderPort` and `LocalSentenceTransformerProvider` |
| vector persistence/retrieval | governed Memory Plane and pgvector |
| provider execution | C2 `ModelProviderPort` adapters and factory |
| deterministic benchmark | existing benchmark runner |

### 4.2 No-migration default

C3 does not need a new authoritative table:

- task-package and candidate bytes live in the Artifact Store;
- task-run lifecycle and outcome identity live in the Event Store;
- normalized trajectories use existing Experience Compiler tables;
- task and correction corpus items use existing Corpus Factory tables;
- observations and evaluation datasets use existing learned evidence tables;
- embeddings use existing `memory_embeddings`;
- provider output uses the C2 `provider_output_records` table.

Migration head remains `0015` unless the half-precision benchmark proves a concrete schema
change is necessary and an ADR accepts it. An event or exported schema addition does not
consume an Alembic revision.

### 4.3 Expected focused code boundary

Expected additions or changes:

```text
src/cognitive_os/
  coding/
    reality_tasks.py
    hidden_verification.py
    outcome_recording.py
  application/services/
    reality_outcome_harvester.py
    reality_campaign.py
  benchmarks/
    reality_adapter.py
  infrastructure/embeddings/
    sentence_transformers.py
scripts/
  reality_inputs.py
  local_embedding_model.py
benchmarks/manifests/
  sprint21c3-reality-ci.yaml
  sprint21c3-reality-seed.yaml
tests/fixtures/reality/
  task-manifest.yaml
  provider-visible/
  control/
docs/sprints/sprint-21/
  gate-c3-assessment.md
  sprint-21c3-report.md
  sprint-21d1-handoff.md
```

Names may be tightened. A package must not be created solely to mirror this tree.

### 4.4 Data flow

```text
rights-clean task template
  -> generated isolated Git repository
  -> baseline hidden verification
  -> curated or provider candidate
  -> existing patch/worktree/tool path
  -> visible plus hidden sandbox verification
  -> CodingOutcome artifact + Event Store identity
  -> Experience Compiler trajectory
  -> real-run learned observation (evaluation only)
  -> corpus and statistics manifests

task/correction text
  -> rights-clean Corpus Factory item
  -> pinned local CPU embedding
  -> existing Memory Plane vector record
  -> frozen exact retrieval benchmark
```

### 4.5 Task package

`RealityTaskManifest` must contain:

- stable task ID and schema version;
- domain, task family, repository group, and difficulty;
- generator profile ID and version;
- public issue description and expected behaviour;
- base-repository manifest hash;
- visible test command;
- hidden verifier bundle artifact ID and hash;
- allowed and forbidden paths;
- source identity, licence, usage-rights decision, and attribution;
- provider-visible content manifest;
- control-material manifest hash;
- deterministic generation seed;
- expected baseline status;
- required verifier IDs;
- created time and content hash.

The provider-visible projection must omit hidden test paths, hidden test names, golden
patches, solution hashes, expected candidate IDs, and control rationale.

### 4.6 Candidate strategy

Each task has four offline candidate strategies:

1. `incomplete_a` — plausible, applies, but fails at least one hidden case;
2. `correct_narrow` — minimal correction that passes all required checks;
3. `incomplete_b` — a different plausible failure mode;
4. `correct_robust` — a distinct accepted correction.

Candidate manifests bind task ID, strategy family, patch artifact/hash, source kind,
provider/model identity where applicable, and generation profile. They do not contain the
hidden expected result.

The control generator may know the solution. The provider, selector, feature builder, and
embedding input may not.

### 4.7 Outcome identity and persistence

The existing `CodingResultPackaged` event contains only an outcome hash. C3 must add a new,
backwards-compatible `coding.outcome_recorded` event rather than changing historical event
hashes.

The new event must bind:

- task-run ID;
- task ID and candidate strategy ID;
- `CodingOutcome` canonical hash;
- outcome artifact ID and content hash;
- hidden-verifier evidence artifact ID and hash;
- final status;
- provider-output ID when applicable;
- task manifest hash;
- occurred time.

`CodingOutcomeRecorder` must write canonical outcome bytes through `ArtifactService` before
appending the event. Metadata-only fabrication is prohibited.

### 4.8 Hidden verifier boundary

The hidden verifier must:

- use the existing rootless Docker image and process limits;
- mount the task workspace at `/workspace`;
- mount exactly one trusted control bundle read-only at `/verification`;
- expose no control mount to provider-visible tools;
- run a fixed host-selected pytest command;
- return normalized criterion status and artifact hashes;
- delete no workspace or control input;
- preserve network-off, read-only root, dropped capabilities, and no-new-privileges;
- record the sandbox image digest;
- fail closed when the control bundle hash changes.

The existing visible pytest, Ruff, MyPy, import, file, diff, dependency, and workspace
integrity requirements remain. Hidden pytest is an additional C3 requirement.

### 4.9 Campaign composition

The planned minimum outcome set is:

| Source | Minimum unique outcomes |
|---|---:|
| 30 task baselines | 30 |
| four offline candidates per task | 120 |
| one provider candidate per task: 10 Codex, 10 Claude Code, 10 OpenRouter | 30 |
| existing multi-domain governed benchmark replay | 51 |
| **Planned total** | **231** |

Every row is a real execution with an exact event ID and verifier evidence. A failed
candidate counts as a verified outcome; a duplicate event ID, duplicate task-run ID, or
idempotent replay does not count twice.

OpenRouter receives one attempt on ten predeclared tasks. Its result never gates the 200
outcome threshold because the offline and multi-domain paths already produce 201 outcomes.

### 4.10 Correction trajectories

For each of the 30 tasks:

- trajectory A is baseline failure -> `incomplete_a` failure -> `correct_narrow` pass;
- trajectory B is baseline failure -> `incomplete_b` failure -> `correct_robust` pass.

This yields 60 planned trajectory manifests. At least 50 must compile successfully through
the existing Experience Compiler. A trajectory is distinct by task ID, incorrect strategy,
correct strategy, and ordered outcome event IDs. Shared or duplicated identifiers are not
double-counted.

### 4.11 Corpus-role separation

- Task descriptions, public source, and curated correction examples are self-play corpus
  candidates and may be routed by Corpus Factory to a training-corpus destination.
- Corpus export still cannot initiate training.
- Actual sandboxed task-run outcomes use `REAL_GOVERNED_RUN` provenance.
- Real-run observations are evaluation-only and cannot enter training snapshots.
- Provider advisory outputs remain `OPERATOR_SUPPLIED`; the executed coding result, not the
  provider prose, becomes the real governed run.
- Provider identity and attribution are retained for later weak-label analysis.

### 4.12 Split and leakage policy

Splits are assigned by repository group and task family, never individual outcome ID.

Required checks:

- all outcomes for one task stay in one split;
- all parameter variants from one generator template stay in one split;
- no provider-visible field contains control hashes, paths, test names, or golden patch
  tokens;
- exact issue/source/patch duplicates stay in one group;
- normalized Python AST and token hashes flag near-clones;
- a universal patch assembled from all declared candidate edits cannot pass the corpus;
- evaluation families are not used to tune retrieval thresholds;
- embeddings are built only from provider-visible text.

### 4.13 Provider campaign policy

- OpenRouter defaults to `require_zero_data_retention: false`.
- OpenRouter defaults to `allow_data_collection: true` for this open project.
- Free-only routing and `maximum_spend_usd: 0.0` remain.
- Each OpenRouter task has one attempt.
- Codex and Claude campaigns use their existing bounded adapters.
- One explicit `--live` campaign flag is sufficient after configuration is enabled; no
  separate ZDR waiver or interactive prompt is required.
- Campaign resume skips already recorded task/candidate identities.
- Every provider output is schema-validated, then judged by the sandbox verifier.
- Provider success rates are reported with numerator, denominator, resolved model, and
  failure class.

### 4.14 Local embedding decision

The first C3 model is `sentence-transformers/all-MiniLM-L6-v2` because:

- the existing `sentence-transformers` optional extra already supports it;
- it is Apache-2.0;
- it produces 384-dimensional vectors;
- it is CPU-viable and substantially faster than `all-mpnet-base-v2`;
- 200–1,000 C3 records do not need an approximate index.

W0 must resolve and freeze an exact model revision. Runtime use of `main`, `latest`, or a
network download is prohibited. The model is prefetched by an explicit operator command to
an absolute local directory, hashed, and not committed.

### 4.15 Retrieval benchmark

Use at least 60 frozen query/relevant-item pairs across the six task families. Compare:

- lexical retrieval;
- deterministic test embedding, labelled non-production;
- local MiniLM float32 exact cosine;
- local MiniLM half-precision exact cosine.

Primary thresholds:

- local MiniLM recall@5 at least 0.80;
- local MiniLM MRR@10 at least 0.65;
- at least 0.15 absolute recall@5 improvement over deterministic test embeddings;
- zero cross-group relevant-item leakage;
- repeated runs have identical rankings for equal inputs.

If a threshold fails, Gate C3 remains open or the benchmark/task representation is
corrected without tuning on the evaluation groups.

### 4.16 Full versus half precision

Benchmark the same 384-dimensional normalized vectors in temporary PostgreSQL tables:

- storage bytes including indexes;
- ingest time;
- exact query p50 and p95;
- recall@5, recall@10, MRR@10, and nDCG@10;
- top-k agreement against float32 exact search;
- migration rehearsal time.

Choose half precision only if:

- storage reduction is at least 35%;
- recall@10 and MRR@10 each fall by no more than 0.01 absolute;
- p95 latency is no worse by more than 10%;
- the operational change is simpler than retaining float32.

C3 records the decision. At C3 corpus size, a passing half-precision benchmark does not by
itself justify migration `0016`; D1 can continue exact float32 until scale requires more.

---

## 5. Detailed work items

## EPIC S21C3-E00 — Baseline, policy, and release control

### S21C3-000 — Verify and freeze the C2 baseline

- **Priority:** P0
- **Depends on:** none
- **Output:** exact baseline evidence block

**Tasks**

1. Confirm a clean worktree.
2. Fetch `origin` and tags.
3. verify local and remote `main`, tag object, and peeled tag;
4. verify post-merge CI run `30434494612`;
5. verify Alembic head `0015`;
6. verify repository language and focused C2 import/replay smoke;
7. create the C3 branch from the peeled commit.

**Acceptance**

- every source handle matches the declared parent;
- the branch carries no unrelated changes;
- any mismatch blocks implementation.

### S21C3-001 — Close historical C2 status in the handoff

- **Priority:** P0
- **Depends on:** S21C3-000
- **Output:** C3 handoff updated from conditional to final C2 release state

**Tasks**

1. Record tag object, peeled commit, final `main` CI, and migration head.
2. state that Gate C2 condition 14 closed in the tag annotation;
3. retain the 5/22 OpenRouter denominator;
4. retain the Artifact Store and reviewer limitations;
5. link this C3 backlog.

**Acceptance**

- the handoff no longer tells C3 to wait for a tag that exists;
- historical C2 report text remains unchanged;
- final release handles agree with origin.

### S21C3-002 — Amend the project data-policy ADR

- **Priority:** P0
- **Depends on:** S21C3-000
- **Output:** ADR amendment implementing Section 0.3

**Tasks**

1. Record open-development data as public by default.
2. remove mandatory ZDR for that data;
3. permit provider-side data collection for that data;
4. remove per-request ZDR waiver requirements;
5. retain credential isolation and source-rights metadata;
6. separate data policy from provider correctness and cost policy;
7. update future-facing project documentation.

**Acceptance**

- the policy is one project default, not a C3-only exception;
- no text claims credentials are safe to publish;
- no source licence is inferred from openness alone;
- the policy has executable configuration consequences.

### S21C3-003 — Isolate C3 storage and verify the development-pair fingerprint

- **Priority:** P0
- **Depends on:** S21C3-000
- **Output:** healthy isolated database/artifact root and read-only mismatch evidence

**Tasks**

1. Read the C1 mismatch inventory.
2. verify the development pair fingerprint and file count read-only;
3. create a new C3 database and artifact root;
4. run artifact health before campaign data;
5. record non-secret handles;
6. prohibit any C3 command from targeting the development pair.

**Acceptance**

- the development pair receives zero C3 writes;
- its fingerprint remains unchanged;
- the isolated pair begins healthy;
- no remediation is attempted.

### S21C3-004 — Record single-maintainer release mode

- **Priority:** P0
- **Depends on:** S21C3-000
- **Output:** current branch-protection evidence and no-review release rule

**Tasks**

1. Verify 27 required contexts, strict mode, `enforce_admins`, force-push, and deletion
   protection.
2. record one collaborator and no second eligible reviewer;
3. keep required approving reviews disabled;
4. avoid repeated reviewer polling unless collaborator state changes;
5. target `palkouser/cognitive-os` explicitly in remote commands.

**Acceptance**

- no protection is weakened;
- no approval is fabricated;
- the known reviewer limitation does not block the sprint;
- current protection evidence is retained.

## EPIC S21C3-E01 — Reality contracts and authoritative outcome recording

### S21C3-010 — Add minimal reality-input contracts

- **Priority:** P0
- **Depends on:** S21C3-002
- **Output:** task, candidate, trajectory, campaign, and statistics contracts

**Tasks**

1. Add `RealityTaskManifest`.
2. add `RealityCandidateManifest`;
3. add `RealityOutcomeReference`;
4. add `CorrectionTrajectoryManifest`;
5. add `RealityCampaignManifest` and `RealityCorpusStatistics`;
6. reuse existing IDs, hashes, rights, sensitivity, provider, artifact, verifier, and
   time contracts;
7. reject unknown strategy, source, split, or verifier values.

**Acceptance**

- contracts contain references and hashes rather than duplicate bodies;
- canonical hash mutation tests pass;
- control fields cannot enter provider-visible projections;
- no duplicate replacement for a Corpus Factory or learned contract is added.

### S21C3-011 — Export schemas and safe fixtures

- **Priority:** P0
- **Depends on:** S21C3-010
- **Output:** tracked schemas and public test fixtures

**Tasks**

1. Register new public contracts.
2. regenerate schemas;
3. add valid, invalid, mutation, and compatibility fixtures;
4. add schema drift to the reality-input CI lane;
5. ensure control material is absent from exported provider fixtures.

**Acceptance**

- schema export check passes;
- C2 schemas remain compatible;
- fixtures contain no credential or private external data.

### S21C3-012 — Persist full coding outcomes through the Artifact Store

- **Priority:** P0
- **Depends on:** S21C3-010
- **Output:** `CodingOutcomeRecorder` and `coding.outcome_recorded` event

**Tasks**

1. Canonically serialize the complete `CodingOutcome`.
2. write bytes through `ArtifactService`;
3. verify the returned hash;
4. append the new event with task, candidate, verifier, and artifact references;
5. preserve the existing `CodingResultPackaged` event unchanged;
6. make campaign completion depend on successful artifact and event recording.

**Acceptance**

- every counted outcome resolves to bytes and an event;
- a missing or hash-mismatched artifact fails closed;
- an event cannot claim bytes that were not written;
- idempotent replay returns one authoritative identity.

### S21C3-013 — Add real-run source resolution and harvesting

- **Priority:** P0
- **Depends on:** S21C3-012
- **Output:** coding and benchmark outcome harvester

**Tasks**

1. Resolve `coding.outcome_recorded` by event ID and exact artifact hash.
2. verify task manifest, verifier evidence, and terminal status;
3. construct `GovernedOutcomeReference` with `governed_task_run` or
   `governed_benchmark_case`;
4. use `REAL_GOVERNED_RUN` provenance and direct attribution only when independently
   supported;
5. offer the reference to `LearnedObservationIntake`;
6. record rejected or quarantined sources without changing them.

**Acceptance**

- accepted outcomes are evaluation eligible;
- zero real-run observations are training eligible;
- changed or missing source bytes fail closed;
- provider prose is not used as the real-run source.

### S21C3-014 — Add campaign resume and exact counting

- **Priority:** P0
- **Depends on:** S21C3-010, S21C3-012
- **Output:** resumable campaign manifest and count rules

**Tasks**

1. Derive run identity from task, candidate, generator, verifier, and campaign version.
2. skip exact completed identities on resume;
3. refuse identity reuse with changed content;
4. count unique event IDs and outcome hashes;
5. report duplicate, skipped, failed, accepted, quarantined, and missing outcomes;
6. make partial campaign state recoverable after interruption.

**Acceptance**

- restart cannot duplicate the denominator;
- resume performs no repeated provider call for completed work;
- changed inputs require a new campaign revision;
- counts reproduce from authoritative evidence.

## EPIC S21C3-E02 — Task corpus and hidden execution

### S21C3-020 — Implement six task-family generators

- **Priority:** P0
- **Depends on:** S21C3-010
- **Output:** at least 30 deterministic task packages

**Tasks**

1. Create at least five tasks in each of six families:
   boundary/collections, parsing/validation, state/idempotency, numeric logic,
   error handling, and data transformation.
2. generate tiny Python repositories with no network or dependency changes;
3. include visible tests that demonstrate the public contract without revealing all edge
   cases;
4. generate hidden control bundles separately;
5. assign stable task, group, family, licence, and seed identities;
6. commit manifests and generators, not generated Git repositories.

**Acceptance**

- at least 30 unique packages reproduce byte-identically;
- every task has Apache-2.0 or equivalent verified project-owned rights;
- task generation is CPU-only and network-free;
- each family has distinct behavior and failure shapes.

### S21C3-021 — Add the read-only hidden-test mount

- **Priority:** P0
- **Depends on:** S21C3-020
- **Output:** one verifier-only control mount in the existing sandbox

**Tasks**

1. Extend the existing sandbox request with one typed read-only verification input.
2. constrain its container destination to `/verification`;
3. verify source path and content hash before launch;
4. keep it absent from provider-visible tool descriptors;
5. retain all existing sandbox restrictions;
6. clean the container on success, failure, timeout, and cancellation.

**Acceptance**

- the control bundle is read-only;
- providers cannot enumerate or read it;
- changing its bytes fails before pytest;
- no second sandbox implementation appears.

### S21C3-022 — Add hidden pytest to the coding verifier bundle

- **Priority:** P0
- **Depends on:** S21C3-021
- **Output:** required `coding.hidden_pytest` criterion for C3 runs

**Tasks**

1. Add a host-selected fixed command against `/verification`.
2. prohibit provider-supplied hidden-test arguments;
3. normalize result and evidence hash;
4. include it in the acceptance decision;
5. preserve the existing visible verifier profile for non-C3 callers;
6. add failure, timeout, missing, tampered, and success tests.

**Acceptance**

- a visible-test-only patch cannot be accepted;
- a missing hidden bundle is unverifiable, not pass;
- hidden output is bounded and stored through Artifact Service;
- all candidates face the same verifier version.

### S21C3-023 — Record baseline verification before candidate execution

- **Priority:** P0
- **Depends on:** S21C3-022
- **Output:** authoritative baseline-failure outcome per task

**Tasks**

1. Add a C3 execution mode that verifies the untouched base worktree.
2. require hidden pytest to fail for the declared task reason;
3. require repository integrity and non-target quality checks to remain valid;
4. record the baseline as a full outcome artifact and event;
5. refuse a task whose baseline unexpectedly passes or fails for an infrastructure
   reason.

**Acceptance**

- every task has one verified subject failure before correction;
- environment errors are not mislabeled as task failures;
- baseline execution uses the same image and verifier profile as candidates.

### S21C3-024 — Prove control-material isolation and shortcut resistance

- **Priority:** P0
- **Depends on:** S21C3-020, S21C3-022
- **Output:** leakage and universal-patch adversarial suite

**Tasks**

1. Scan provider requests, context bundles, feature rows, embedding text, and exported
   manifests for control tokens.
2. hash normalized AST and token streams for group detection;
3. attempt a universal patch assembled from all declared candidate edits;
4. attempt task-ID and family lookup shortcuts;
5. verify evaluation groups remain unseen during threshold selection;
6. fail corpus publication on any leak.

**Acceptance**

- zero hidden path, test name, solution hash, or golden token leaks;
- the universal patch cannot solve the corpus;
- near-clones are grouped rather than split;
- test assertions use only provider-visible inputs until scoring.

## EPIC S21C3-E03 — Candidate campaign, outcomes, and trajectories

### S21C3-030 — Generate four offline candidate strategies per task

- **Priority:** P0
- **Depends on:** S21C3-020
- **Output:** 120 deterministic candidate manifests

**Tasks**

1. Generate `incomplete_a`, `correct_narrow`, `incomplete_b`, and `correct_robust`.
2. ensure the two incorrect candidates apply cleanly but fail different hidden cases;
3. ensure the two correct candidates differ materially in strategy or implementation;
4. route proposals through the existing patch and tool plane;
5. store patch bytes and manifests through Artifact Service;
6. verify candidate generation is deterministic.

**Acceptance**

- 120 unique candidate identities exist;
- incomplete candidates never pass hidden verification;
- correct candidates pass every required criterion;
- correct candidates are not exposed as labels to selectors or providers.

### S21C3-031 — Execute the 150-outcome offline coding campaign

- **Priority:** P0
- **Depends on:** S21C3-014, S21C3-023, S21C3-030
- **Output:** 30 baseline plus 120 candidate outcome records

**Tasks**

1. Execute all baselines.
2. execute every offline candidate in a fresh worktree;
3. verify main checkout integrity after each run;
4. record outcome, hidden evidence, timing, resources, diff, and cleanup;
5. resume safely after interruption;
6. publish exact outcome counts.

**Acceptance**

- 150 unique outcomes resolve end to end;
- all statuses match the candidate contract;
- zero main-worktree mutations occur;
- zero duplicate outcomes inflate counts.

### S21C3-032 — Run the 30-outcome provider diversity campaign

- **Priority:** P0
- **Depends on:** S21C3-002, S21C3-014, S21C3-024
- **Output:** ten Codex, ten Claude Code, and ten OpenRouter task outcomes

**Tasks**

1. Freeze provider/task assignment before execution.
2. use one provider campaign run per selected task;
3. inline hash-pinned content for OpenRouter;
4. use one attempt for OpenRouter and no retry-until-correct loop;
5. execute every returned patch through the hidden verifier;
6. record malformed, refused, incorrect, and correct outcomes;
7. retain normalized public project output under the campaign retention policy.

**Acceptance**

- 30 unique provider-attributed outcomes are attempted and recorded;
- OpenRouter correctness is not a gate;
- exact provider/model denominators are present;
- no provider sees hidden control material;
- provider failure cannot block the offline 200-outcome path.

### S21C3-033 — Replay 51 existing multi-domain governed cases

- **Priority:** P0
- **Depends on:** S21C3-013
- **Output:** at least 51 fresh verifier-backed domain outcomes

**Tasks**

1. Select the existing deterministic cases from the protected benchmark manifests.
2. freeze case IDs, versions, domains, and verifier profiles;
3. execute rather than copy prior result labels;
4. record as governed benchmark outcomes;
5. offer accepted references to learned intake;
6. report domain counts separately from coding tasks.

**Acceptance**

- at least 51 unique fresh executions exist;
- prior fixture metrics are not relabeled as new runs;
- each outcome has verifier and source evidence;
- no case enters training because it is a real governed run.

### S21C3-034 — Compile at least 50 failed-to-corrected trajectories

- **Priority:** P0
- **Depends on:** S21C3-031
- **Output:** 60 planned Experience Compiler manifests

**Tasks**

1. Build two ordered correction paths per task as defined in Section 4.10.
2. resolve every source event and artifact by exact hash;
3. compile through the existing Experience Compiler;
4. persist using the existing experience repository;
5. retain gaps, conflicts, and failed compilations;
6. count only distinct ordered source identities.

**Acceptance**

- at least 50 trajectories compile;
- at least 20 unique tasks are represented;
- at least two incorrect and two correct strategy families are represented overall;
- source or ordering mismatch fails closed;
- no new trajectory repository is added.

### S21C3-035 — Route self-play task and correction items through Corpus Factory

- **Priority:** P0
- **Depends on:** S21C3-024, S21C3-030, S21C3-034
- **Output:** rights-checked corpus manifests and group-aware split

**Tasks**

1. Ingest task descriptions, provider-visible source, and curated correction examples.
2. retain exact task, candidate, and trajectory lineage;
3. classify rights, sensitivity, quality, and destination;
4. assign splits by repository group and family;
5. keep control material outside normalized items;
6. keep corpus export upload/training actions at zero.

**Acceptance**

- all routed items have verified rights and lineage;
- exact duplicates do not enter twice;
- one task family never crosses splits;
- exported corpus cannot start training;
- real-run outcomes are absent from the self-play training-candidate manifest.

### S21C3-036 — Build evaluation-only learned evidence

- **Priority:** P0
- **Depends on:** S21C3-013, S21C3-031, S21C3-032, S21C3-033
- **Output:** accepted/quarantined/rejected observations and evaluation dataset

**Tasks**

1. Offer all real task and benchmark outcomes to learned intake.
2. preserve provider attribution and verifier evidence;
3. quarantine incomplete attribution or evidence;
4. build an evaluation-role snapshot only;
5. attempt and reject a training snapshot containing a real run;
6. verify manifests through Artifact Service.

**Acceptance**

- observation counts reconcile with campaign evidence;
- zero real-run observations enter training;
- provider advisory records remain distinct from executed outcomes;
- the evaluation snapshot is immutable and reproducible.

### S21C3-037 — Publish corpus and provider statistics

- **Priority:** P0
- **Depends on:** S21C3-034, S21C3-035, S21C3-036
- **Output:** machine-readable statistics and human summary

**Tasks**

1. Report counts by domain, family, group, split, source, provider, resolved model,
   strategy, verifier, status, attribution, and rights.
2. report exact unique and duplicate counts;
3. report provider accuracy and schema/refusal/failure classes;
4. report correction depth and time;
5. report quarantine/rejection reasons;
6. retain numerator and denominator for every percentage.

**Acceptance**

- statistics reproduce from persisted evidence;
- C2 OpenRouter 5/22 remains historical and C3 results are separate;
- failures are visible rather than excluded;
- no usefulness or training claim is inferred.

## EPIC S21C3-E04 — C2 policy and provider-efficiency corrections

### S21C3-040 — Relax the tracked OpenRouter data policy

- **Priority:** P0
- **Depends on:** S21C3-002
- **Output:** future-facing configuration and tests matching the owner decision

**Tasks**

1. Change `OpenRouterProviderConfig.require_zero_data_retention` default to `false`.
2. change `allow_data_collection` default to `true`;
3. update `config/providers.example.yaml`;
4. remove obsolete comments requiring ZDR for data classified under the
   open-development policy;
5. retain HTTPS, key-source, free-only, zero-spend, and one-attempt defaults;
6. update tests and operator documentation.

**Acceptance**

- the example no longer needs a live-only ZDR override;
- no per-call ZDR approval is required;
- credentials remain excluded;
- paid routing remains refused at zero spend.

### S21C3-041 — Simplify live campaign authorization

- **Priority:** P0
- **Depends on:** S21C3-002, S21C3-040
- **Output:** one non-interactive explicit campaign opt-in

**Tasks**

1. Keep live execution disabled by default.
2. allow an enabled configuration plus explicit `--live` without an interactive prompt;
3. remove a separate ZDR-waiver prompt;
4. support campaign resume without repeating completed calls;
5. record config hash and command intent.

**Acceptance**

- unattended local campaign execution is possible after deliberate configuration;
- ordinary CI cannot call a provider;
- one command can resume the campaign;
- no safety dialogue blocks each public-data call.

### S21C3-042 — Add one real-provider compatibility preflight

- **Priority:** P0
- **Depends on:** S21C3-040, S21C3-041
- **Output:** bounded pre-campaign compatibility receipt

**Tasks**

1. Validate installed OpenAI client signature for OpenRouter extension arguments.
2. validate catalog variable-price normalization;
3. validate inline task-content assembly;
4. run one tiny public task per provider;
5. verify schema and response mapping;
6. stop the campaign on a structural boundary defect, not on an incorrect model answer.

**Acceptance**

- the C2 fake-transport blind spots have direct regressions;
- structural incompatibility is found before 30 campaign tasks;
- model incorrectness remains a measured outcome;
- preflight data is not counted toward the 200 outcome corpus.

### S21C3-043 — Keep OpenRouter off the critical path

- **Priority:** P0
- **Depends on:** S21C3-032
- **Output:** fixed provider assignment and no-retry reliability report

**Tasks**

1. Preselect exactly ten OpenRouter tasks.
2. run one attempt each;
3. classify model, schema, quota, rate, and boundary outcomes separately;
4. compare with Codex and Claude denominators;
5. prohibit fallback-result relabeling as OpenRouter success;
6. document when a paid or pinned provider would be justified later.

**Acceptance**

- OpenRouter cannot delay corpus completion;
- no retry selection bias enters accuracy;
- every result is retained as a verified success or failure;
- provider recommendation is evidence-based.

## EPIC S21C3-E05 — Local embeddings and storage calibration

### S21C3-050 — Freeze the local embedding model

- **Priority:** P0
- **Depends on:** S21C3-000
- **Output:** accepted model manifest

**Tasks**

1. Select `sentence-transformers/all-MiniLM-L6-v2`.
2. resolve an exact upstream revision;
3. record model ID, revision, 384 dimensions, normalization, sequence limit, licence,
   source URL, file list, and whole-tree digest;
4. document the rejected `all-mpnet-base-v2` alternative and CPU-speed reason;
5. prohibit floating revisions.

**Acceptance**

- the model is Apache-2.0 with evidence;
- identity is immutable;
- the model is not committed;
- the decision introduces no new dependency beyond `local-embeddings`.

### S21C3-051 — Add explicit operator prefetch and health

- **Priority:** P0
- **Depends on:** S21C3-050
- **Output:** one model-prefetch command and local-only health check

**Tasks**

1. Add an opt-in network prefetch command using the already installed Hugging Face
   dependency.
2. require model ID, revision, absolute destination, and `--allow-network`;
3. verify downloaded file hashes and licence;
4. write a manifest beside the local model;
5. keep runtime `local_files_only=True`;
6. report missing, digest mismatch, dependency missing, dimension mismatch, and healthy.

**Acceptance**

- runtime performs zero downloads;
- prefetch is resumable and idempotent;
- wrong bytes are unhealthy;
- no model or cache enters Git.

### S21C3-052 — Activate 384-dimensional CPU embedding

- **Priority:** P0
- **Depends on:** S21C3-051
- **Output:** production local embedding configuration and integration

**Tasks**

1. Configure `LocalSentenceTransformerProvider` with exact identity.
2. embed normalized provider-visible technical text only;
3. batch within existing limits;
4. store through the existing Memory Plane;
5. query exact cosine distance;
6. refuse silent fallback to deterministic embeddings.

**Acceptance**

- output is finite, normalized, and exactly 384-dimensional;
- repeat input produces stable vectors within declared tolerance;
- missing local model returns a typed unavailable capability;
- production evidence names the local model, never the deterministic provider.

### S21C3-053 — Build the frozen retrieval benchmark

- **Priority:** P0
- **Depends on:** S21C3-024, S21C3-035, S21C3-052
- **Output:** at least 60 query/relevant-item cases

**Tasks**

1. Select cases across all six task families.
2. group queries with their task family and repository source;
3. freeze relevant-item judgments before result inspection;
4. include terminology, symptom, failure, correction, and analogous-task queries;
5. keep evaluation groups out of threshold design;
6. record manifest hash.

**Acceptance**

- at least 60 cases exist;
- relevance is independently reproducible;
- no hidden-test or solution token appears in query text;
- the benchmark is immutable for C3 decisions.

### S21C3-054 — Measure local retrieval quality and efficiency

- **Priority:** P0
- **Depends on:** S21C3-053
- **Output:** lexical, deterministic, and MiniLM comparison

**Tasks**

1. Run lexical retrieval.
2. run deterministic test embeddings with an explicit non-production label;
3. run MiniLM float32 exact cosine;
4. measure recall@5/10, MRR@10, nDCG@10, p50/p95 latency, ingest time, and peak RSS;
5. report per-family and aggregate results;
6. repeat to verify stable ranking.

**Acceptance**

- MiniLM clears Section 4.15 thresholds;
- fake/hash embeddings are excluded from production evidence;
- no result is tuned on evaluation groups;
- model and corpus hashes accompany every metric.

### S21C3-055 — Benchmark full and half precision

- **Priority:** P0
- **Depends on:** S21C3-054
- **Output:** temporary-table storage and retrieval comparison

**Tasks**

1. Load identical vectors into temporary `vector(384)` and `halfvec(384)` tables.
2. run identical exact queries;
3. measure database and index bytes, load time, latency, and ranking metrics;
4. rehearse conversion without changing production tables;
5. evaluate Section 4.16 thresholds;
6. clean temporary tables.

**Acceptance**

- comparison uses identical inputs and queries;
- measurement is repeatable;
- temporary objects are removed;
- no migration is created before the decision.

### S21C3-056 — Record the storage decision

- **Priority:** P0
- **Depends on:** S21C3-055
- **Output:** explicit float32/halfvec decision and migration verdict

**Tasks**

1. Compare results with the threshold table.
2. choose float32 or half precision;
3. state whether C3 needs migration `0016`;
4. default to no migration when the C3-scale benefit is operationally irrelevant;
5. record the scale trigger that would reopen the decision.

**Acceptance**

- the chosen mode follows measured evidence;
- a no-migration decision is valid and explicit;
- an `0016` proposal, if any, includes clean/incremental/downgrade/restore work;
- no unused schema or index remains.

## EPIC S21C3-E06 — Operations, CI, and evidence

### S21C3-060 — Add one `reality_inputs` operator CLI

- **Priority:** P0
- **Depends on:** S21C3-014, S21C3-031, S21C3-036, S21C3-054
- **Output:** generate, validate, run, resume, harvest, stats, embed, and verify commands

**Tasks**

1. Reuse one script entry point.
2. default to offline validation;
3. require explicit `--live` for provider tasks;
4. support task/provider subsets and resume;
5. print sanitized machine-readable receipts;
6. document exit codes and isolation handles.

**Acceptance**

- one command resumes a campaign;
- normal use does not need interactive ZDR approval;
- output contains no credentials;
- every subcommand has deterministic tests.

### S21C3-061 — Add end-to-end health and integrity checks

- **Priority:** P0
- **Depends on:** S21C3-012, S21C3-034, S21C3-036, S21C3-052
- **Output:** unified C3 integrity report

**Tasks**

1. Verify task, candidate, outcome, hidden evidence, trajectory, corpus, observation,
   dataset, model, and embedding hashes.
2. distinguish provider/model availability warnings from evidence corruption;
3. detect missing artifacts and broken event links;
4. verify group split and count reconciliation;
5. verify zero writes to the development Artifact Store pair.

**Acceptance**

- any broken authority link is unhealthy;
- OpenRouter wrong answers do not make storage unhealthy;
- unavailable local model is a capability failure, not silent fallback;
- all counts reconcile.

### S21C3-062 — Extend backup, restore, restart, and campaign resume

- **Priority:** P0
- **Depends on:** S21C3-061
- **Output:** recoverable C3 evidence

**Tasks**

1. Use existing table manifests; add no table unless migration `0016` is approved.
2. back up Event, Artifact, Experience, Corpus, Memory, learned, and provider-output
   evidence;
3. restore into a fresh database and artifact root;
4. restart services and re-resolve every counted outcome;
5. resume an interrupted campaign without duplicate calls;
6. rerun corpus statistics and retrieval.

**Acceptance**

- counts, hashes, splits, trajectories, and rankings reproduce;
- missing bytes fail restore verification;
- campaign resume produces no duplicate denominator;
- the development pair remains untouched.

### S21C3-063 — Add credential-free CI and deterministic seed cases

- **Priority:** P0
- **Depends on:** S21C3-024, S21C3-031, S21C3-054
- **Output:** focused C3 CI lane and benchmark manifests

**Tasks**

1. Run a small representative task from each family.
2. use replay providers only;
3. use deterministic embeddings only for contract mechanics, labelled test-only;
4. run hidden verifier, leakage, artifact, event, trajectory, corpus, and learned-intake
   checks;
5. prohibit network, provider credentials, local model requirement, and GPU;
6. run the full 30-task/real-model campaign outside normal CI.

**Acceptance**

- CI is deterministic and credential-free;
- missing optional local model does not skip non-model C3 contracts;
- no provider behavior is faked into a live-quality claim;
- the focused lane completes within existing timeout.

### S21C3-064 — Open the draft PR in W1

- **Priority:** P0
- **Depends on:** S21C3-010 through S21C3-014, initial S21C3-021
- **Output:** early remote integration feedback

**Tasks**

1. Open a draft PR after contracts, outcome recording, hidden-mount skeleton, schemas,
   and one end-to-end fixture exist.
2. run Artifact Service bytes-before-event regression;
3. run schema, packaging, language, and optional-extra checks;
4. keep live providers and local model outside normal CI;
5. correct remote failures before bulk task creation.

**Acceptance**

- remote CI exercises the real outcome record path;
- missing dependencies are not converted into skips;
- bulk corpus work does not accumulate before boundary validation.

### S21C3-065 — Run the complete local verification matrix

- **Priority:** P0
- **Depends on:** S21C3-037, S21C3-043, S21C3-056, S21C3-062, S21C3-063
- **Output:** command-by-command release evidence

**Tasks**

1. Run contract, task, sandbox, verifier, campaign, provider, artifact, event,
   experience, corpus, learned, memory, and embedding tests.
2. run PostgreSQL integration and health;
3. run migration head, drift, backup/restore, and restart;
4. run leakage, universal-patch, secret, language, security, packaging, lint, format,
   and schema checks;
5. run the full repository suite;
6. record command, head, duration, exit, counts, and non-secret result.

**Acceptance**

- every required command has expected status;
- unexplained skips are zero;
- full-suite regressions are zero;
- all release evidence uses the isolated C3 pair.

## EPIC S21C3-E07 — Gate, documentation, and release

### S21C3-070 — Update project and operator documentation

- **Priority:** P0
- **Depends on:** S21C3-002, S21C3-040, S21C3-060
- **Output:** current data, campaign, corpus, and embedding runbooks

**Tasks**

1. Document the open-development data policy.
2. document relaxed ZDR/data collection and retained credential boundary;
3. document provider assignment and no-retry accuracy reporting;
4. document task generation, hidden verification, campaign resume, and corpus roles;
5. document local-model prefetch, health, and no-network runtime;
6. document storage decision and migration verdict;
7. retain Artifact Store and reviewer limitations.

**Acceptance**

- the example workflow is non-interactive after explicit setup;
- documentation does not retain the obsolete per-fixture ZDR waiver;
- no credential value or model file is committed;
- deferred work has an owner.

### S21C3-071 — Produce the Gate C3 assessment

- **Priority:** P0
- **Depends on:** S21C3-065, S21C3-070
- **Output:** evidence matrix for all 16 Gate C3 conditions

**Tasks**

1. Mark each condition pass or fail.
2. link task, outcome, trajectory, corpus, provider, embedding, storage, PostgreSQL, and
   CI evidence;
3. report exact denominators and duplicate exclusions;
4. state Gate L2 closed;
5. leave final release handles to the tag annotation.

**Acceptance**

- every pass has evidence;
- no conditional item is called pass;
- no corpus or embedding metric is called useful learned behavior;
- limitations remain explicit.

### S21C3-072 — Complete the Sprint 21C3 report

- **Priority:** P0
- **Depends on:** S21C3-071
- **Output:** factual sprint report and D1 readiness decision

**Tasks**

1. Record delivered tasks and deviations by backlog ID.
2. report task, outcome, correction, provider, split, rights, verifier, and embedding
   statistics;
3. report OpenRouter correctness with exact denominator;
4. report the ZDR policy amendment;
5. report Artifact Store fingerprint and zero C3 writes;
6. report reviewer limitation and unchanged protection;
7. report storage decision and migration head;
8. state whether D1 has sufficient honest data.

**Acceptance**

- all counts reconcile with machine-readable evidence;
- failures and null results remain visible;
- the report contains no future tag self-reference;
- Gate L2 remains closed.

### S21C3-073 — Complete protected release and baseline tag

- **Priority:** P0
- **Depends on:** S21C3-072
- **Output:** merged, exact-head CI-verified, remotely tagged C3 baseline

**Tasks**

1. Mark the PR ready only after local evidence is green.
2. wait for all required checks;
3. merge without weakening or bypassing protection;
4. verify remote `main` at the exact final commit;
5. wait for successful post-merge `main` CI;
6. create one annotated `sprint-21c3-reality-baseline` tag;
7. include final PR, merge, CI, migration, gate, corpus, provider, embedding, reviewer,
   and Artifact Store evidence in the annotation;
8. push once and verify remote tag object and peeled commit.

**Acceptance**

- all required checks and post-merge CI succeed;
- one tag exists and peels to final `main`;
- no review is fabricated;
- protection remains intact;
- Gate C3 passes and Gate L2 remains closed.

### S21C3-074 — Prepare the Sprint 21D1 handoff

- **Priority:** P0
- **Depends on:** S21C3-072
- **Output:** exact learning-surface and EMG starting contract

**Tasks**

1. Record parent tag, peeled commit, migration head, and next revision.
2. inventory task, outcome, trajectory, corpus, learned observation, embedding, and
   retrieval APIs;
3. freeze group-aware splits and evidence manifests;
4. list candidate learning surfaces without selecting from held-out results;
5. carry provider reliability, data policy, reviewer, and Artifact Store limitations;
6. recommend branch `feature/sprint-21d1-learning-surface-emg`.

**Acceptance**

- D1 can pre-register a surface without reconstructing C3 authority;
- evaluation groups remain frozen;
- no training or activation is smuggled into the handoff;
- unresolved risks have owners.

---

## 6. Execution waves

| Wave | Work items | Exit |
|---|---|---|
| W0 — release and policy | 000–004 | verified parent, final C2 status, data-policy ADR, isolated storage, release mode |
| W1 — first vertical slice | 010–014, initial 021–023, 064 | one generated task travels through hidden verifier, Artifact Store, Event Store, intake, and draft PR |
| W2 — task corpus | 020–024, 030 | 30 valid tasks, 120 offline candidates, leakage checks green |
| W3 — executed reality | 031–037 | at least 200 outcomes, 50 correction trajectories, corpus roles and statistics green |
| W4 — provider correction | 040–043, 032 | relaxed ZDR policy, simplified campaign, real preflight, 30 provider outcomes |
| W5 — local retrieval | 050–056 | pinned model, frozen retrieval benchmark, storage decision |
| W6 — recovery and CI | 060–065 | CLI, health, restore, resume, offline CI, full local matrix green |
| W7 — release | 070–074 | documentation, Gate C3, report, protected release, tag, D1 handoff |

No wave may claim completion while a P0 dependency is red.

### 6.1 First vertical slice

Before generating all 30 tasks, W1 must prove one task end to end:

1. deterministic task generation;
2. baseline hidden failure;
3. one incomplete candidate failure;
4. one correct candidate pass;
5. full outcome artifact;
6. `coding.outcome_recorded` event;
7. learned intake reference;
8. Experience Compiler trajectory;
9. Corpus Factory item;
10. restart and exact replay.

This is the shortest test of the actual C3 architecture.

### 6.2 Pull-request strategy

Use one implementation PR by default. Split only if:

- the data-policy ADR/config change needs independent release before provider campaign;
  or
- the hidden verifier boundary requires focused security review.

Do not split to hide a red gate or merge bulk generated corpus before the first vertical
slice is green.

---

## 7. Verification matrix

| Evidence class | Required proof | Failure meaning |
|---|---|---|
| baseline | exact parent tag, commit, CI, migration | wrong C3 starting point |
| data policy | config, ADR, and tests agree | obsolete ZDR exception still controls work |
| task package | identity, rights, reproducibility, baseline fail | task is not honest or repeatable |
| hidden boundary | mount isolation and tamper tests | provider can see or change the answer |
| candidate | distinct strategy and patch hash | corpus has duplicate or fake diversity |
| execution | sandbox event and artifact | outcome is a label, not a run |
| verifier | visible plus hidden evidence | success is not independently established |
| outcome count | unique event/task-run/hash reconciliation | denominator is inflated |
| trajectory | ordered failed-to-corrected source chain | correction evidence is synthetic |
| leakage | group split, AST/token duplicate, universal patch | evaluation can be gamed |
| provider | exact numerator/denominator/model/failure | provider reliability is hidden |
| learned intake | real-run evaluation-only rejection from training | corpus contamination |
| Corpus Factory | rights, lineage, quality, split | self-play input is ungoverned |
| model | exact revision, licence, files, digest | embedding source is mutable |
| retrieval | frozen query/relevant manifest and metrics | local semantic value is unmeasured |
| precision | identical float32/halfvec inputs and queries | storage decision is anecdotal |
| artifacts/events | bytes, hashes, exact source links | evidence cannot be resolved |
| PostgreSQL | health, restart, backup/restore | evidence is not durable |
| CI | offline deterministic focused lane | remote integration unresolved |
| release | exact-head main CI and remote tag | C3 baseline is not reproducible |

---

## 8. Quantitative acceptance thresholds

### 8.1 Task corpus

- at least 30 tasks;
- at least six task families;
- at least five tasks per family;
- 100% verified usage rights;
- 100% deterministic regeneration;
- 100% declared baseline failures;
- zero hidden/control material in provider-visible inputs;
- zero universal-patch corpus solutions.

### 8.2 Executed outcomes

- at least 200 unique verifier-backed outcomes;
- planned evidence target: 231;
- at least 150 offline coding outcomes;
- at least 30 provider-attributed coding outcomes;
- at least 51 multi-domain governed benchmark outcomes;
- zero duplicate event IDs or task-run IDs counted twice;
- zero copied historical labels counted as new executions.

### 8.3 Corrections

- at least 50 distinct failed-to-corrected trajectories;
- planned target: 60;
- at least 20 unique tasks;
- at least two incorrect strategy families;
- at least two accepted correction strategy families;
- every transition resolves to immutable outcome events and artifacts.

### 8.4 Provider efficiency

- OpenRouter: exactly ten planned C3 task attempts, one attempt per task;
- Codex: ten planned task runs;
- Claude Code: ten planned task runs;
- zero retry-until-correct loops;
- zero paid OpenRouter spend;
- zero ZDR policy refusals for open-development data;
- exact success and failure denominators.

### 8.5 Retrieval

- at least 60 frozen query/relevant pairs;
- MiniLM recall@5 at least 0.80;
- MiniLM MRR@10 at least 0.65;
- MiniLM recall@5 at least 0.15 above deterministic test embedding;
- repeated-ranking agreement 100% for equal inputs;
- zero deterministic embeddings in production evidence.

### 8.6 Storage

- half precision saves at least 35% before selection;
- recall@10 drop at most 0.01 absolute;
- MRR@10 drop at most 0.01 absolute;
- p95 query latency no worse by more than 10%;
- temporary benchmark objects removed;
- migration count is zero unless evidence explicitly accepts `0016`.

### 8.7 Safety and durability retained for efficiency

- zero credentials or authorization values persisted;
- zero C3 writes to the inconsistent development Artifact Store pair;
- zero main-worktree mutations;
- zero provider access to hidden controls;
- zero real governed runs in training snapshots;
- backup/restore and restart preserve all counted evidence.

---

## 9. Risks and required responses

| Risk | Trigger | Required response |
|---|---|---|
| OpenRouter remains unreliable | wrong/schema-invalid result | record one verified failure; do not retry; continue offline campaign |
| obsolete ZDR default blocks free endpoints | policy refusal on open project data | apply project-wide relaxed default; retain zero spend |
| data-policy relaxation leaks credentials | token or auth material reaches payload | block release; fix credential boundary; data openness does not include credentials |
| hidden test leaks | control token appears before scoring | invalidate affected task/group and regenerate |
| universal candidate solves tasks | one aggregate patch passes broadly | reject corpus design and diversify task families |
| visible tests pass but hidden fail | candidate overfits public contract | record failed outcome; keep it as negative evidence |
| baseline passes | task is already solved | reject or revise task before campaign |
| sandbox infrastructure fails | timeout/image/mount error | classify infrastructure failure; do not count as task outcome |
| outcome event has no bytes | metadata written without artifact content | fail campaign and repair recorder |
| duplicate resume inflates counts | same identity runs twice | use authoritative identity; count once; investigate call duplication |
| provider output labeled real run | advisory source used directly | reject; only executed sandbox outcome is real |
| real outcome enters training | dataset builder accepts it | block release; preserve evaluation-only checks |
| 30 tasks are near-clones | normalized AST/token collision across splits | group or replace tasks |
| local model downloads at runtime | missing cache triggers network | fail capability; use explicit prefetch |
| model revision floats | `main` or no revision configured | reject configuration |
| MiniLM misses retrieval threshold | frozen benchmark fails | inspect representation, not holdout labels; Gate remains open |
| halfvec saves space but hurts ranking | metric drop exceeds threshold | keep float32; no migration |
| migration proposed without need | `0016` appears before decision | remove it |
| Artifact Store mismatch | development pair targeted | stop; use isolated C3 pair; no repair |
| reviewer unavailable | one collaborator remains | use accepted single-maintainer mode; retain checks and `enforce_admins` |
| corpus volume presented as learning | report claims Gate L2 | correct report; Gate L2 remains closed |

---

## 10. External source basis

The initial local-model and vector-storage decision is based on:

- Sentence Transformers pretrained model guidance:
  <https://sbert.net/docs/sentence_transformer/pretrained_models.html>
- `all-MiniLM-L6-v2` model card:
  <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2>
- `all-MiniLM-L6-v2` Apache-2.0 licence:
  <https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/blob/826711e54e001c83835913827a843d8dd0a1def9/LICENSE>
- pgvector half-precision and exact-search documentation:
  <https://github.com/pgvector/pgvector>

W0 must freeze exact revisions. Current documentation is an input to the decision, not a
floating runtime dependency.

---

## 11. Definition of Done

Sprint 21C3 is complete only when:

- all P0 work is complete;
- the exact C2 release is the parent;
- the open-development data policy is active;
- credentials and source rights remain governed;
- at least 30 tasks pass structural and baseline checks;
- hidden tests remain outside provider and feature inputs;
- at least 200 unique executed outcomes resolve through Event and Artifact Stores;
- at least 50 failed-to-corrected trajectories compile;
- group-aware leakage and universal-patch checks pass;
- provider failures remain in exact denominators;
- OpenRouter is not a corpus-completeness dependency;
- self-play task/correction items and real-run evaluation evidence remain separate;
- zero real governed runs enter training snapshots;
- one pinned local CPU embedding model passes health and retrieval thresholds;
- deterministic embeddings remain test-only;
- the full/half precision decision is measured;
- migration head remains `0015` unless `0016` is explicitly justified and fully tested;
- health, restart, backup/restore, campaign resume, local matrix, and full suite pass;
- all required PR checks pass;
- exact-head post-merge `main` CI passes;
- one annotated `sprint-21c3-reality-baseline` tag is remotely verified;
- Gate C3 passes;
- Gate L2 remains closed;
- D1 receives frozen inputs, splits, metrics, APIs, and residual risks.

---

## 12. Expected deliverables

At minimum:

- this backlog;
- project data-policy ADR amendment;
- updated OpenRouter defaults and example configuration;
- reality task, candidate, outcome, trajectory, campaign, and statistics contracts;
- at least 30 deterministic task manifests;
- four offline candidate strategies per task;
- hidden-test control bundles and verifier-only sandbox mount;
- `coding.outcome_recorded` event and full outcome Artifact Store recording;
- resumable campaign runner and operator CLI;
- at least 200 authoritative outcome records;
- at least 50 Experience Compiler correction trajectories;
- Corpus Factory self-play manifests;
- learned evaluation observations and dataset manifest;
- provider reliability report with exact denominators;
- pinned local MiniLM model manifest and prefetch command;
- local CPU embedding and retrieval benchmark;
- float32 versus halfvec measurement and migration decision;
- isolated C3 health, backup, restore, restart, and resume evidence;
- focused offline C3 CI lane;
- an early draft PR;
- `docs/sprints/sprint-21/gate-c3-assessment.md`;
- `docs/sprints/sprint-21/sprint-21c3-report.md`;
- annotated `sprint-21c3-reality-baseline`;
- `docs/sprints/sprint-21/sprint-21d1-handoff.md`.
