# Sprint 21 technical plan — Learning Substrate and Extension Seam

**Document status:** Planning draft, revision 4 — D1, D4, D5 and the revised D3 applied
**Baseline tag:** `sprint-20-baseline` = `837405c90eeb4835de24e394fc9a14e1a94dbc8a`
**Migration head at baseline:** `0012`
**Audit date:** 2026-07-25
**Stage gate:** Gate L — revised (see section 16)

## 0. Scope and decisions

The Sprint Group 4 specification describes Sprint 21 as an *optional* Learned Components Laboratory
whose valid outcome is a documented no-go. The owner has reclassified it as the **critical** sprint,
with five requirements the original scope does not cover:

1. no catastrophic forgetting — learning must accumulate, and new knowledge must be able to revise
   old knowledge without destroying it;
2. robust *and* plastic enough to accept, integrate, and return knowledge from heterogeneous domains
   (logic, mathematics, coding, engineering, …) through one uniform path;
3. eventually able to operate without a large LLM connection, including its own language capability;
4. runtime-scalable — the required capacity is not knowable in advance, so scalability is a
   selection criterion for the learning method, not a later optimisation;
5. multiple candidate methods planned, with a **priority and trial order ranked by expected
   success**.

### 0.1. Owner clarification on requirement 3

Requirement 3 is **not an exit condition**. What must be delivered is the functional foundation in
code that lets language capability — and any other future learned capability — be added later as a
complement to the agent's base functions, without modifying the core.

The work therefore shifts from *building a learner* to *building the socket a learner plugs into*,
and proving the socket with one real, minimal learner. `torch`, CUDA, LoRA, and distillation leave
the sprint entirely.

### 0.2. Decisions applied

| | Decision | Effect on this plan |
|---|---|---|
| **D1** | Core = **the deterministic mandatory execution path only**. Contracts and ports may be edited when a capability is added | Section 3.1 rewritten; the sprint's headline guarantee narrows and is stated honestly in 3.1.2 and Gate L condition 2. Speculative contract fields removed |
| **D3** *(revised)* | **Both corpora:** deterministic self-play as the training corpus, plus continuously harvested real governed runs as an **evaluation-only** reference | Section 7.1; self-play enables the ablation labelling in 3.7, which is what makes D5 tractable, and the real-run corpus turns self-play distribution bias from an unmeasured limitation into a measured one (7.1.2). Two guardrails keep it a pure win: the 21.1 gate stays self-play-only, and real-run data is evaluation-only in 21A |
| **D4** | **Build the teacher-output retention hook in 21A**, request and response | Section 7.2 stays in 21A |
| **D5** | First learned surface: **context candidate reranking** | Sections 3.4–3.7 and phase 21.5 are now concrete: no new core call site is required at all |

D2 (sprint granularity) is taken as settled by the owner's acceptance of a split: **21A and 21B in
scope, generative capability a later sprint.**

Everything in section 1 was verified against the repository and the live development database on the
audit date, not taken from prior closure reports.

## 1. Readiness audit

### 1.1. What is ready, and load-bearing

| Foundation | Evidence | Why it matters now |
|---|---|---|
| The chosen attach point already exists as a port | `ContextRerankerPort` + `LocalCrossEncoderReranker` — optional, absence-tested, digest-pinned, `local_files_only=True` | **D5 needs no new core call site.** A learned reranker replaces an optional adapter behind an existing protocol |
| A deterministic baseline to beat, already implemented | [ranking.py](../../../src/cognitive_os/context/ranking.py) — weighted reciprocal-rank fusion over seven weighted signals plus modifiers and bounded selection | The baseline is real, tuned, and non-trivial; beating it is a meaningful result rather than beating a straw man |
| Port-and-adapter pattern with two learned components in production shape | `EmbeddingProviderPort`, `ContextRerankerPort` | The seam is a generalisation of a proven pattern, not a new architecture |
| Frozen registries with configuration-driven selection | Verifier, tool, retriever, skill, strategy registries | Four precedents for the learned-component registry, including absence handling and health reporting |
| Append-only event store with replay | Migration `0001`+, replay tested every sprint | **The rehearsal buffer.** Continual learning without a replay corpus is unmeasurable; the project records one by construction |
| Corpus Factory with a training destination and rights model | `CorpusDestinationType.TRAINING_CORPUS`, `CorpusUsageRight.MODEL_TRAINING`, `training_suitability` | The rights-checked, deduplicated, provenance-tracked pipeline exists as a contract; it must be connected, not designed |
| `TaskSignature` — canonical, low-cardinality, domain-agnostic | [routing.py:273](../../../src/cognitive_os/domain/routing.py#L273), 17 categorical or bounded fields, computed for coding *and* the Sprint 20 pilot | A ready-made feature vector for requirement 2 |
| A shadow contract that structurally cannot lie | `ShadowRoutingResult.shadow_actual_outcome: None = None` at [routing.py:607](../../../src/cognitive_os/domain/routing.py#L607) — the field's *type* is `None` | Copy verbatim into the learned-component contracts |
| Governed runs are fast and deterministic | **Measured: 24.4 ms per governed domain run, 51 runs in 1.24 s** | This is what makes causal ablation labelling affordable (section 3.7) — the single most important measurement in this audit |
| Controlled-change machinery with Tier-3 manual review | Sprint 19, `PromotionMode.MANUAL_REVIEW_ONLY` | The one safety amendment this sprint needs (7.3) has an existing governed path |

### 1.2. Findings that block the stated requirements

**B1 — There is no accumulated experience to learn from. (Top blocker.)** The live development
database holds **13 events, 1 memory item, 1 memory embedding, 2 memory accesses, 2 semantic claims
with 4 revisions, 5 artifacts.** Every subsystem from Sprint 9 to Sprint 20 is exercised by fixtures
and integration tests that truncate their tables on each run. The system has the machinery to
accumulate experience and has accumulated approximately none.

Resolved in phase 21.1 by the self-play training corpus, whose exit gate is quantitative, alongside
real-run harvesting whose volume is deliberately ungated (7.1.3).

**B4 — Vector search is exact brute force. (Second blocker.)** `SELECT indexname FROM pg_indexes
WHERE indexdef ILIKE '%hnsw%' OR '%ivfflat%'` returns **zero rows**. Retrieval uses unindexed
`embedding <=> query`; in-process vector math is pure Python
([deterministic.py:62](../../../src/cognitive_os/infrastructure/embeddings/deterministic.py#L62));
`numpy` is not a core dependency (core is httpx, jsonschema, openai, pydantic, PyYAML).

Requirement 4 therefore fails today far below the Sprint 22 targets of 10^6 memory revisions and
10^6 routing observations. It decides which learning method is viable at all, so the ANN index, the
quantisation decision, and the capacity envelope move **into** Sprint 21.

**B4 was understated.** The absence of an index is not an omission but a *decision*, recorded in
ADR 0035 and enforced in five places: a sealed `MemoryConfiguration` flag, a sealed
`ContextConfiguration` flag, an `ERROR`-severity Memory Plane health finding, a
`prohibited_indexes` count in the semantic health check, and an integration test asserting zero.
Resolving B4 therefore requires amending a Sprint 9 guarantee, not adding a migration — see
[ADR 0082](../../adr/0082-approximate-vector-retrieval-and-capacity-envelope.md) for the narrowed
form and its measured constraints (an undimensioned `vector` column cannot carry an HNSW index at
all; pgvector refuses HNSW above 2 000 dimensions, while the configuration permits 4 096).

**B3 — The corpus contract structurally forbids training. (Required, narrow.)**
`CorpusExportRequest.prohibit_upload_and_training` raises when `train=True`, and
`CorpusExportResult.training_actions` is `Field(default=0, ge=0, le=0)` — a field that can only ever
hold zero ([corpus.py:709](../../../src/cognitive_os/domain/corpus.py#L709),
[corpus.py:730](../../../src/cognitive_os/domain/corpus.py#L730)).

Not a bug: Sprints 0–20 were deliberately built so that nothing can train a model. Any learning,
including Tier B's small CPU models, collides with it. Resolved explicitly through the Sprint 19
Tier-3 path in 7.3 — never by quietly relaxing a validator.

**B2 — Raw provider output is never persisted.** `ModelCallRecord.raw_response_artifact` is declared
at [model_calls.py:42](../../../src/cognitive_os/domain/model_calls.py#L42) and written by **no code
path in the repository**. There is no request-body field at all. Per D4 this is fixed in 21A as a
governed, default-off hook (7.2) — sized for correctness, not volume, because no distillation
happens this sprint.

**B5 — No training infrastructure.** Both existing learned adapters are inference-only. Under
revision 3 what is needed is a dataset/feature/artifact lifecycle and a CPU trainer port — not a
deep-learning stack. `torch` stays out.

### 1.3. Verdict on synchronisation with the project goals

Against `target.md` — a harness that owns memory, identity, and learning, with the LLM as a
replaceable tool — the project is **in sync on ownership, out of sync on learning.** Governance,
provider independence, verification, and auditability are delivered and strong; accumulated
experience and learning from it have not started. Sprints 9–20 built the organs; nothing has yet
been eaten. With requirement 3 reframed as a seam and D1 settled, the fix fits two sprints.

## 2. Sprint objective

Deliver a governed learning substrate and an extension seam: the system accumulates knowledge from
its own verified experience, integrates it across domains through one uniform representation,
measurably resists catastrophic forgetting, scales incrementally at runtime, improves context
candidate reranking over its deterministic baseline, and **accepts future learned capabilities as
configuration-declared adapters that cannot alter the deterministic mandatory path.**

## 3. The extension seam

### 3.1. The core boundary, per D1

**Core = the deterministic mandatory execution path.** Contracts under `domain/**` and protocols
under `application/ports/**` are *not* frozen; they may be extended when a capability genuinely
needs it.

#### 3.1.1. What this still guarantees, as a hard CI gate

The valuable half of the guarantee survives intact and is testable:

> **Mandatory-path invariance.** With every learned component absent, disabled, or abstaining, the >
deterministic mandatory path produces byte-identical decisions to the baseline on every recorded >
case. A learned component can never degrade or alter the deterministic core.

This is enforced by replaying the full recorded case set in three configurations — component absent,
component present but disabled, component present and abstaining — and requiring identical decision
hashes in all three. It is a stronger, more useful test than a file-diff check, because it
constrains *behaviour* rather than *file layout*, and it is exactly what protects the eleven sprints
of deterministic guarantees already delivered.

#### 3.1.2. What this no longer guarantees, stated plainly

Under the looser boundary, "a future capability needs no core change" **cannot be a CI gate**,
because the paths a future capability would touch are no longer frozen. It is therefore recorded as
a **design convention with measured drift**, not a pass/fail condition:

- `ExtensionConformanceRecord` still records which paths adding a component touched, so a reviewer
  sees contract churn accumulating instead of discovering it later;
- an ADR is required when a new capability edits a contract or a port, so the change is deliberate;
- **Gate L condition 2 is worded accordingly** (section 16) — the plan does not claim a guarantee
  the chosen boundary cannot support.

There is a real upside, and it is worth taking: because contracts may evolve later, this sprint does
**not** need to guess a future generative adapter's contract shape. Speculative descriptor fields
are therefore removed (3.3). Only the one field whose retrofit would be genuinely expensive is kept
ahead of need: prediction payloads are artifact-referenced from day one, because changing that later
rewrites every stored prediction.

### 3.2. Port family

Four protocols in the existing `application/ports` style — structural typing, no base classes:

```text
LearnedComponentPort      descriptor; health_check(); predict(situation) -> LearnedPrediction
LearnedTrainerPort        train(dataset_snapshot) -> LearnedModelArtifact   (optional per component)
LearnedArtifactStorePort  put/get model artifacts by digest  (thin adapter over the Artifact Store)
LearnedDatasetPort        materialise a hash-identified snapshot from governed sources
```

A component may implement only `LearnedComponentPort`; both existing adapters are exactly that
shape, which is the evidence the seam fits reality rather than only fitting new code.

### 3.3. Descriptor

```text
component_id, version, use_case
capability_class        discriminative | ranking | embedding | anomaly   (extensible)
resource_class          cpu | cpu_preferred
required_extra          optional dependency group name
artifact_format         safetensors | joblib | none
supports_abstention     must be true to be promotable
explanation_kind        neighbours | feature_attribution | none
declared_limitations
content_hash
```

Trimmed per 3.1.2: `generative`, `gpu_required`, `base_model_identity`, and `adapter_of` are **not**
added now. They are the fields a later sprint adds when it actually builds that capability, and D1
permits that. The enums are extensible so the addition is additive.

### 3.4. Attach point, per D5

The learned reranker attaches **behind the existing `ContextRerankerPort`**. Consequences:

- **no new core call site**, and no change to the Context Builder's control flow;
- the deterministic weighted-RRF ranking in
  [ranking.py](../../../src/cognitive_os/context/ranking.py) remains the baseline and the fallback;
- the port is already optional and absence-tested, so "component absent" is a pre-existing passing
  path rather than new work;
- reranking is advisory by construction in this codebase — it reorders candidates that the safety,
  trust, sensitivity, and required-evidence gates have already admitted — so the blast radius is the
  smallest of the three candidate surfaces.

### 3.5. Lifecycle

Reuse the Sprint 12 skill lifecycle shape: `registered -> shadow -> verified -> active (bounded
scope) -> disabled -> retracted`, with Sprint 19 promotion assessment and rollback,
`MANUAL_REVIEW_ONLY` above the lowest risk class, and immediate disable on drift, digest mismatch,
missing artifact, feature-schema mismatch, or verifier failure.

### 3.6. The label problem, and why it is real

Context reranking has no label in the system today. Verified by inspection: `ContextRetrievalTrace`
records `exclusions`, `ContextBundleRevision` records `excluded_candidates`, and `ContextCandidate`
carries `access_audit_ids` — but **nothing records whether an included candidate actually
contributed to the outcome.** There is no "this candidate was useful" signal anywhere in the
contracts.

Three ways to get one:

| Approach | Label quality | Cost | Verdict |
|---|---|---|---|
| Outcome attribution — bundle used, run accepted or rejected | Bundle-level only; classic credit-assignment ambiguity across 8–20 candidates | Free | Too weak to train on alone |
| Required-evidence coverage — was the required candidate present | Nearly tautological; `assert_required_context` already enforces it | Free | Useful as a sanity feature, not a label |
| **Leave-one-out ablation** — remove one candidate, re-run, observe whether the outcome changes | **Causal and per-candidate** | See 3.7 | **Chosen** |

### 3.7. Ablation labelling — affordable because of the self-play corpus

Ablation is normally too expensive to consider. Here it is not, and the reason is the self-play
training corpus (7.1.1): governed runs are deterministic, CPU-only, credential-free, and **measured
at 24.4 ms each (51 runs in 1.24 s)**.

| Sweep | Runs | Measured or projected cost |
|---|---|---|
| One full pass over the 51 fixture cases | 51 | **1.24 s, measured** |
| Leave-one-out ablation, 8 candidates per case | ~408 | **~10 s, projected from the measurement** |
| 10× self-play volume with full ablation | ~4 080 | **~1.7 min** |

So per-candidate causal labels are obtainable in seconds, for the whole corpus, repeatedly. That is
the pivotal finding of this plan: the self-play corpus and the reranking surface (D5) combine into a
labelling strategy that neither would support alone — self-play makes ablation cheap, and reranking
is the surface where per-candidate causal labels are exactly what is needed.

Labelling contract: a candidate is *useful* when its removal changes the run's acceptance decision
or degrades its verifier disposition; *neutral* when removal changes nothing; *harmful* when removal
improves the outcome. Neutral is the majority class and must be handled as such — a reranker that
learns only to predict "neutral" is a null result, and the promotion gate must reject it on the
baseline comparison.

#### 3.7.1. Which runs can be ablated, and which physically cannot

Ablation requires a counterfactual re-run whose only difference is the removed candidate. That holds
for exactly one class of run, and the boundary is a property of the code, not a policy choice:

| Run class | Ablatable | Why |
|---|---|---|
| Provider-free deterministic path — the Sprint 20 domain pilot, deterministic tools and verifiers | **Yes** | The model step is computation, not a call. This is the self-play corpus |
| Replay-backed run | **No** | `request_fingerprint` hashes the request's semantic content, so an ablated request misses and the provider raises `replay_fixture_not_found` ([replay.py:105](../../../src/cognitive_os/providers/replay.py#L105)) |
| Live-provider run | **No** | The counterfactual is confounded: the response differs for reasons unrelated to the ablation, and each attempt costs a call |

This is why the revised D3 (section 7.1) cannot dilute the labelling pipeline: real-run data is
*incapable* of producing an ablation label, so it never enters that path. The two corpora cannot
compete for the same role.

The replay provider's fail-closed behaviour also hands the plan a verification for free: pointing
the ablation harness at replay fixtures raises loudly instead of emitting fabricated "neutral"
labels. Section 13 makes that a test.

## 4. Priority and trial order for learning methods

Requirement 5. The order is driven by the two requirements that eliminate most candidates before
accuracy is considered: no catastrophic forgetting, and runtime scalability.

### Tier A — Non-parametric retrieval learning *(first, and the backbone)*

Embed the situation, store the outcome, decide by weighted k-nearest-neighbour vote over stored
experience, calibrated on measured success rates.

- **Catastrophic forgetting is impossible by construction** — learning is an `INSERT`; nothing is
  overwritten, so nothing can be destroyed. Revision is a new, later-dated record with higher
  weight, which is exactly the Sprint 10 bitemporal claim semantics.
- **Scalability is an index property, not a retraining property.** HNSW supports incremental insert;
  capacity grows with disk.
- **Roughly 80 % built** — pgvector storage, embedding ports, retrieval fusion, provenance, and
  access audit all exist.
- The k neighbours *are* the explanation, satisfying interpretability for free.
- Degrades gracefully: no neighbour above threshold ⇒ abstain ⇒ deterministic path unchanged.

Prerequisites: the ANN index (B4) and a real corpus (B1) — prerequisites of the sprint anyway.

### Tier B — Incremental parametric heads *(second)*

Small calibrated models — SGD / logistic regression with `partial_fit`, decision trees, gradient
boosting — over `TaskSignature` features plus Tier-A retrieval statistics and the ablation labels.
Cheap, deterministic under a fixed seed, retrainable from the replay corpus in minutes,
interpretable. Forgetting is handled by **retraining from the immutable corpus**, sound only because
the corpus is append-only.

Trial order: constant/majority → kNN (Tier A as a feature) → decision tree → random forest →
gradient boosting. A complex model is never promoted for beating a weak straw man.

### Tier C — Adapter-based parametric learning *(out of scope)*

A small open-weight local model with frozen base weights and per-domain LoRA adapters remains the
right eventual design for language capability, because parameter isolation is the strongest
structural defence against forgetting: the base is never modified, so a bad adapter is deleted
rather than recovered from. Removed from this sprint by 0.1; `torch`, CUDA, and `peft` do not enter
the repository in Sprint 21. Under D1 the contracts it will need may be added in the sprint that
builds it.

### Tier D — Research only

KAN and graph-neural experiments as Group 4 scopes them: permitted to end in a no-go, nothing
depends on them.

### What the ordering rejects

- **Online gradient updates on live tasks** — fastest route to catastrophic forgetting and
  unauditable state. Prohibited.
- **A single monolithic model owning all domains** — contradicts requirements 1 and 2; every new
  domain's gradients would fight the previous domains'.
- **Learned weights as authoritative state** — weights stay derived and discardable; PostgreSQL and
  the event store remain the source of truth. This is the invariant that makes forgetting
  recoverable.

## 5. Catastrophic forgetting: defence stack and gate

| Layer | Mechanism | Provided by |
|---|---|---|
| Authoritative store | Append-only revisions; knowledge is superseded, never overwritten | Sprints 9, 10, 15 |
| Rehearsal corpus | Every trained component uses an immutable snapshot that always includes older-domain samples | New in 21.2 |
| Non-parametric core | kNN decisions later learning cannot overwrite | Tier A |
| Revision semantics | Bitemporal validity and confidence, so correction ≠ destruction | Sprint 10 |
| Measurement | Retention suite re-runs every previously passing case, all domains, after each learning step | New in 21.2 — the gate |
| Rollback | Disable any component, delete any artifact, restore the prior measured state | Sprint 19 + new disable path |

**The forgetting gate.** After any learning event, all previously passing benchmark cases across
*all* domains re-run. A component is ineligible for promotion if any previously passing case
regresses beyond its declared tolerance, regardless of target-metric improvement — the Sprint 19
"hard failure ends eligibility" rule applied to learning. Recorded as `ForgettingAssessment`.

**The gate's own negative test is mandatory.** A deliberately catastrophic component — trained only
on the newest domain — must be *rejected* by the gate in CI. A gate that has never rejected anything
proves nothing.

Regularisation (EWC, synaptic intelligence) is deliberately absent: it mitigates forgetting within
one shared parameter set, which Tiers A and B do not have.

## 6. Uniform cross-domain representation

### 6.1. In — the situation encoding

`SituationVector` combines the canonical `TaskSignature` (17 categorical or bounded fields, already
computed for coding *and* the Sprint 20 pilot); bounded numeric context features (candidate counts,
budget utilisation, retry depth, verifier coverage); and, for the reranking surface, the candidate's
own `score_breakdown`, `trust_class`, `sensitivity`, `retrieval_routes`, and token estimate — all
already present on `ContextCandidate`.

Prohibited as features, matching Group 4: credentials, secrets, raw prompt bodies, unrestricted
text. Embeddings are dimension-checked derived vectors, not text bodies.

### 6.2. Out — the decision envelope

Every learned component returns `(decision, confidence, abstain, explanation)`. Abstention is
first-class: below the confidence floor the deterministic path runs and the component records that
it abstained. `supports_abstention=False` ⇒ not promotable. Payloads are artifact-referenced
(3.1.2).

### 6.3. Domain integration test

Verified adversarially: a component trained on coding + mathematics must, on held-out logic and
physics cases, either generalise or abstain. **Confident wrongness on an unseen domain is a hard
promotion failure.**

## 7. Data acquisition (phase 21.1)

### 7.1. Sources, per the revised D3

Two corpora with **strictly separated roles**. The separation is not a convention to be remembered —
it is enforced (7.1.3) and it is what makes running both a pure gain rather than a complication.

#### 7.1.1. Training corpus — deterministic self-play

The 51 Sprint 20 domain cases, coding fixtures, and benchmark manifests replayed at volume:
credential-free, CPU-only, network-free, with verified labels from the existing independent checkers
plus the per-candidate ablation labels of 3.7. No rights negotiation, no provider, no security
amendment. This is the **only** source that can produce ablation labels (3.7.1), and therefore the
only source the reranker trains on in 21A.

#### 7.1.2. Evaluation-only reference corpus — real governed runs

Verified trajectories from actual governed runs, harvested continuously through the existing
Experience Compiler → Corpus Factory path. It cannot be ablated (3.7.1) and is never trained on. It
buys three measurements, none of which needs an ablation label:

| Measurement | What it needs | What it tells us |
|---|---|---|
| **Distribution comparison** — marginal distributions of `SituationVector` features, self-play versus real | Features only, **no labels at all** | The direct measurement of self-play bias: how far real traffic sits from what the component trained on |
| **Weak-label validation** — the self-play-trained reranker scored against real runs' bundle-level acceptance outcomes | Bundle-level outcome, which already exists | Whether the learned ordering correlates with real acceptance. A weak label is unacceptable for training and acceptable for evaluation, because the question is correlation, not instruction |
| **Abstention divergence** — abstention rate on real traffic versus self-play | The component's own abstention flag | The honest out-of-distribution signal. Because abstention is *safe* behaviour, a higher rate on real traffic converts an unknown risk into a measured safety property rather than a quality regression |

Recorded as `DistributionComparisonRecord` (section 9) so the result is evidence, not a remark in a
report.

**Volume caveat, stated plainly.** The live database holds 13 events; real runs accrue only as the
system is actually used. The 21A real-run corpus will therefore be **small** — a few hundred runs
support a coarse marginal-distribution comparison on the high-cardinality `TaskSignature` fields
(`problem_domain`, `problem_class`) and nothing finer. Statistically weak, incomparably better than
zero, and the pipeline accrues volume by itself through Sprint 22. Every comparison must report its
sample count and decline to conclude below a declared minimum.

#### 7.1.3. The two guardrails that keep this a pure gain

1. **The 21.1 exit gate is defined on the self-play corpus alone** (7.4). Real-run volume can never
   block a phase, so the schedule is insulated from how much the system happens to be used.
2. **Real-run data is evaluation-only in 21A, enforced structurally.** A dataset snapshot used for
   training must reject any item whose provenance is a real governed run. This costs nothing extra
   in governance: per the 7.3 amendment only *training* requires an explicit `MODEL_TRAINING` right,
   so an evaluation-only corpus adds **no new rights burden** — the rights architecture already
   draws the line this decision needs.

The one genuinely new discipline is split hygiene: with two corpora, time-aware and group-aware
splits stop being theoretical Group 4 requirements and start mattering, because leaking the
evaluation corpus into training would silently destroy the only bias measurement the plan has.

#### 7.1.4. Remaining sources

3. Recorded teacher output, once the 7.2 hook exists — for a later sprint's distillation, not for
   this one.
4. Operator-supplied local corpora with declared rights.

### 7.2. The B2 hook, per D4

Built in 21A, sized for correctness rather than volume:

- persist request **and** response bodies as Artifact Store blobs, referenced by
  `ModelCallRecord.raw_response_artifact` and a new request counterpart — never as PostgreSQL
  columns, preserving the existing rule;
- run existing secret detection and sensitivity classification **before** writing; quarantine on any
  hit;
- record declared usage rights per provider channel, because a provider's terms — not the project's
  preference — decide whether its output may ever train a model;
- **opt-in per channel, off by default**, with a documented purge path;
- payloads never enter a feature vector directly; they enter the Corpus Factory, where rights,
  deduplication, and classification already live.

### 7.3. The B3 amendment — narrowest form

- `CorpusExportRequest.train` **stays prohibited**; corpus *export* still cannot initiate training.
- A separate contract governs training intent, so "export a corpus" and "train on a corpus" remain
  distinct operations with distinct approvals.
- Training may consume only a hash-identified `LearnedDatasetSnapshot` whose every item carries an
  explicit `MODEL_TRAINING` right.
- `CorpusExportResult.training_actions` keeps `le=0`; training is recorded on the new learning
  contracts, so the corpus subsystem's guarantee stays literally true.

**Tier 3** change surface: ADR, manual review, manual promotion, bundled with nothing else.

### 7.4. Phase exit condition

A reproducible command produces a rights-cleared, deduplicated, hash-identified **self-play** corpus
of at least 10 000 labelled reranking decisions spanning at least four domains, with per-candidate
ablation labels, zero secret-scan hits, and complete provenance.

**The gate depends on the self-play corpus only** (guardrail 7.1.3). Real-run harvesting must be
switched on and proven to record correctly, but its volume is explicitly **not** gated — a phase
cannot be blocked by how much the system happened to be used.

## 8. Phase plan

### Sprint 21A — Learning substrate and extension seam

| Phase | Deliverable | Exit gate |
|---|---|---|
| 21.0 | ADRs: seam design, D1 boundary and its stated limits, method ordering, Tier-3 amendment, ablation labelling, two-corpus separation | ADRs accepted; no code |
| 21.1 | Self-play harness, ablation labelling, corpus assembly, B2 retention hook, **real-run harvesting switched on** | Section 7.4 self-play corpus exists; harvesting proven to record correctly, its volume ungated |
| 21.2 | Feature schema, dataset snapshot, **evaluation-only provenance enforcement**, time-aware and group-aware split policy, rehearsal manifest, **retention suite and forgetting gate** | Gate provably rejects a deliberately forgetting component; a real-run item provably cannot enter a training snapshot |
| 21.3 | ANN index, quantisation decision, incremental insert, capacity envelope (resolves B4; shared with Sprint 22) | Measured recall and p50/p95 at 10^5 and 10^6 vectors; exact-search path preserved for query classes that need it |

**21.3 measured at 10^5** (768 dimensions, index scan confirmed from the plan): on a clustered
corpus, 321 ms exhaustive → **15 ms approximate at 0.992 recall@20**, a 21× speed-up; on
independent gaussian noise, the adversarial floor, 0.496 recall. Retrieval is therefore not a
barrier to Tier A at this size. The exact path stays exhaustive by construction, not by
configuration — see [ADR 0082](../../adr/0082-approximate-vector-retrieval-and-capacity-envelope.md).
The 10^6 point remains to be measured; index build time scaled to 210 s at 10^5, so it is a
multi-hour run rather than a design question.
| 21.4 | Port family, descriptor, registry, lifecycle, **mandatory-path invariance gate** (3.1.1) | Identical decision hashes with the component absent, disabled, and abstaining; two differently shaped components attach |
| 21.5 | Tier A non-parametric reranker behind `ContextRerankerPort`, in shadow, against weighted RRF; **first distribution comparison** (7.1.2) | Shadow evidence recorded; no executed decision changed; `DistributionComparisonRecord` produced, or declining to conclude on a stated sample count |

Gate 21A: the system accumulates rights-cleared, causally labelled experience; **measures its own
distribution bias instead of merely disclosing it**; measures forgetting; scales retrieval to a
documented envelope; and accepts learned components that provably cannot alter the deterministic
path — while changing no behaviour.

### Sprint 21B — First governed learned decision surface

| Phase | Deliverable | Exit gate |
|---|---|---|
| 21.6 | Tier B incremental heads on the reranking surface; baseline hierarchy; calibration; promotion assessment; **weak-label validation and abstention divergence against the real-run corpus** (7.1.2) | Materially beats weighted RRF with no forgetting regression, or a recorded null result; divergence measured and disclosed |
| 21.7 | Bounded promotion of the reranking surface; Tier D research records; Gate L assessment | Operator-approved bounded activation **or** a reproducible no-go |

A no-go at 21.7 is a valid completion. Even then, 21A leaves accumulated experience, a forgetting
benchmark, a scaled retrieval path, and a proven mandatory-path invariance gate.

### Deferred to a later sprint

Generative and language adapters (Tier C), `torch`/CUDA extras, distillation, adapter composition,
and the contract fields they require.

## 9. Contracts

New immutable contracts in the existing `HashedExperienceContract` style. Fields indicative; ADR
review may adjust.

```text
SituationVector              encoding_version, task_signature, numeric_features, candidate_features,
                             embedding_ref, prohibited_feature_check, content_hash

FeatureSchema                feature_schema_id, version, use_case, features, types, normalization,
                             missing_value_policy, prohibited_features, sensitivity, content_hash

AblationLabel                label_id, case_id, candidate_ref, removed_candidate_hash,
                             baseline_outcome, ablated_outcome, label (useful|neutral|harmful),
                             determinism_proof, content_hash

LearnedDatasetSnapshot       dataset_id, revision, corpus_role (training|evaluation),
                             source_manifests, item_provenance_classes, observation_refs,
                             feature_schema, label_definition, split_manifest, sampling_policy,
                             sensitivity, usage_rights, domain_distribution,
                             distribution_limitations, content_hash

DistributionComparisonRecord comparison_id, training_snapshot, evaluation_snapshot,
                             compared_features, per_feature_divergence, sample_counts,
                             minimum_sample_threshold, abstention_rate_training,
                             abstention_rate_evaluation, weak_label_correlation,
                             conclusive, verdict, limitations, content_hash

LearnedComponentDescriptor   see section 3.3

LearnedExperiment            experiment_id, use_case, component_type, tier, baseline_component,
                             feature_schema, dataset_snapshot, training_profile,
                             evaluation_profile, resource_budget, random_seed, content_hash

LearnedModelArtifact         model_artifact_id, experiment_id, framework, framework_version,
                             model_type, hyperparameters, feature_schema, training_dataset,
                             weights_artifact, serialization_format, checksums, resource_usage,
                             content_hash

LearnedPrediction            prediction_id, model_artifact, situation_ref, features_hash,
                             prediction, payload_artifact, confidence, abstained, explanation,
                             content_hash

LearnedShadowResult          prediction_ref, deterministic_baseline_decision,
                             learned_shadow_decision, executed_decision, actual_outcome,
                             agreement, metric_delta, shadow_actual_outcome: None

ContinualLearningSession     session_id, predecessor_session, dataset_snapshot,
                             rehearsal_manifest, updated_components, content_hash

ForgettingAssessment         assessment_id, session_id, baseline_benchmark_manifest,
                             per_domain_before, per_domain_after, regressed_cases,
                             retained_cases, forgetting_score, tolerance, verdict, content_hash

MandatoryPathInvariance      record_id, component_descriptor, case_set_hash,
                             decision_hash_absent, decision_hash_disabled,
                             decision_hash_abstaining, identical, content_hash

ExtensionConformanceRecord   record_id, component_descriptor, paths_touched, contracts_edited,
                             ports_edited, adr_reference, configuration_only, absence_path_passed,
                             content_hash

CapacityEnvelope             vector_count, index_type, quantization, build_time,
                             insert_throughput, recall_at_k, p50_latency, p95_latency,
                             memory_peak, storage_size, content_hash

LearnedPromotionAssessment   experiment_id, model_artifact, quality_comparison,
                             forgetting_assessment, mandatory_path_invariance,
                             safety_comparison, latency_comparison, resource_comparison,
                             interpretability_assessment, reproducibility_assessment,
                             distribution_comparison, drift_plan, fallback_plan,
                             operator_approval_requirement, decision, content_hash
```

Structural, not documented, invariants:

- `LearnedShadowResult.shadow_actual_outcome: None` — an unexecuted counterfactual can never be
  claimed as a success;
- `LearnedPromotionAssessment` cannot reach an eligible decision while `ForgettingAssessment`
  reports a regression or `MandatoryPathInvariance.identical` is false;
- a descriptor with `supports_abstention=False` cannot reach `active`;
- **a `LearnedDatasetSnapshot` with `corpus_role="training"` cannot contain an item whose provenance
  class is a real governed run** — the evaluation-only guardrail (7.1.3) enforced by a model
  validator rather than by review discipline;
- **a `DistributionComparisonRecord` with `conclusive=False` cannot be cited as evidence of low
  divergence** — below the declared sample threshold the only permitted verdict is "not
  established".

`MandatoryPathInvariance` is the machine-readable form of the surviving hard guarantee (3.1.1);
`ExtensionConformanceRecord` is the measured-drift record for the guarantee D1 gave up (3.1.2);
`DistributionComparisonRecord` is the measurement the revised D3 buys (7.1.2).

## 10. Persistence

```text
0013 - Learning substrate, ablation labels, shadow evidence, forgetting, invariance,
       and distribution-comparison records
```

Tables: `learned_feature_schemas`, `learned_ablation_labels`, `learned_dataset_snapshots`,
`learned_component_descriptors`, `learned_experiments`, `learned_model_artifacts`,
`learned_predictions`, `learned_shadow_results`, `learned_continual_sessions`,
`learned_forgetting_assessments`, `learned_distribution_comparisons`,
`learned_mandatory_path_invariance`, `learned_extension_conformance`, `learned_capacity_envelopes`,
`learned_promotion_assessments`, `learned_component_revisions`, `learned_accesses`.

`learned_dataset_snapshots.corpus_role` carries a database-level check constraint, and the
training-snapshot provenance restriction (7.1.3) is enforced as a constraint as well as in the
contract — the guardrail should not depend on application code being correct.

Standard requirements: append-only history, compare-and-set revision advancement, least-privilege
grants, UTC, deterministic identifiers, database constraints for critical invariants, backup and
restore manifest coverage, health checks, tested downgrade. Weights and datasets live in the
Artifact Store; PostgreSQL holds identity, lineage, metrics, and verdicts only.

The 21.3 ANN work alters `memory_embeddings` and the semantic-memory vector tables; it touches
existing indexed data and belongs in its own revision, with the measured index build time in the
closure report.

## 11. Events

```text
learned.dataset_created             learned.session_started
learned.ablation_labelled           learned.session_completed
learned.component_registered        learned.forgetting_assessed
learned.experiment_created          learned.invariance_verified
learned.training_started            learned.distribution_compared
learned.training_completed          learned.capacity_measured
learned.training_failed             learned.component_enabled
learned.shadow_prediction_recorded  learned.component_disabled
learned.evaluation_completed        learned.component_retracted
learned.promotion_assessed
```

## 12. Verification capabilities

Beyond the Group 4 list (dataset lineage and rights, feature-schema integrity, prohibited-feature
absence, split-leakage prevention, training reproducibility, artifact integrity, baseline
completeness, metric reproducibility, uncertainty integrity, shadow non-interference, deterministic
fallback, drift plan, no online learning, no hidden state authority):

- **mandatory-path invariance** — identical decisions with the component absent, disabled,
  abstaining;
- **ablation determinism** — the same ablation yields the same label on re-run;
- **forgetting non-regression** across all previously passing domains;
- **abstention correctness** — confident answers on unseen domains fail;
- **rehearsal completeness** — a training set silently dropping an older domain is rejected;
- **capacity-envelope integrity** — recall and latency measured, never projected;
- **training-rights enforcement** — no item lacking `MODEL_TRAINING` reaches a training set;
- **payload-retention safety** — no secret or credential reaches an artifact or a feature;
- **corpus-role separation** — a training snapshot cannot contain a real-run item (7.1.3), enforced
  in the contract and in the database;
- **evaluation-corpus leakage prevention** — time-aware and group-aware splits keep the evaluation
  corpus out of every training set, because leaking it destroys the only bias measurement available;
- **distribution-comparison integrity** — divergence and sample counts measured, never projected,
  and an inconclusive comparison cannot be reported as low divergence.

## 13. Tests

All Group 4 Sprint 21 tests remain required. Additions:

- **the invariance gate:** decision hashes identical across absent / disabled / abstaining, over the
  full recorded case set;
- a second, differently shaped component attaches and the gate still holds;
- **the forgetting gate's negative test:** a deliberately catastrophic component is rejected;
- ablation labelling is deterministic and reproducible from the recorded corpus;
- **the ablation harness pointed at replay fixtures raises `replay_fixture_not_found` rather than
  emitting fabricated "neutral" labels** — the free verification the replay provider's fail-closed
  fingerprinting gives us (3.7.1);
- **a real-run item cannot enter a `corpus_role="training"` snapshot**, rejected by the contract and
  by the database constraint independently;
- **an inconclusive distribution comparison cannot be recorded as low divergence**;
- a reranker that predicts only the majority class is rejected on the baseline comparison;
- a rehearsal corpus omitting a domain is rejected;
- unseen-domain input produces abstention, not a confident answer;
- ANN recall floor at 10^5 and 10^6 vectors; incremental insert does not degrade it;
- exact-search path still available and correct where required;
- a planted secret is quarantined by payload retention;
- an item without training rights cannot enter a dataset snapshot;
- corpus export still refuses `train=True` after the 7.3 amendment;
- disable path restores the exact deterministic decision on every recorded case;
- every optional extra absent — core installs, imports, and passes.

## 14. Benchmarks

Group 4 layering — 16 CI cases and 64 seed cases per evaluated use case — plus:

- a **retention suite**: every previously passing domain case, re-run after each learning session;
- a **scaling suite** at 10^4, 10^5, 10^6 vectors, CPU-only path mandatory;
- an **invariance suite**: the 3.1.1 gate, as a gate rather than a unit test;
- a **reranking quality suite**: learned reranker versus weighted RRF on held-out cases, reporting
  nDCG-style ordering quality *and* the downstream acceptance-rate delta, because reordering that
  improves ranking metrics without improving outcomes is a null result;
- a **distribution and out-of-distribution suite**: marginal feature divergence between the training
  and evaluation corpora, weak-label correlation, and abstention-rate divergence, each reported with
  its sample count and its conclusive-or-not verdict (7.1.2).

CI stays CPU-only, credential-free, network-free. Large-corpus runs remain opt-in.

## 15. Dependency strategy

```text
learned-baseline    scikit-learn         Tiers A/B, CPU only
learned-boosting    xgboost              Tier B, must materially beat scikit-learn
```

`torch`, `peft`, `transformers`, `pykan`, and `torch-geometric` **do not enter the repository in
Sprint 21.**

Rules: no learned dependency in the core wheel or mandatory path; `numpy` may become a `learned-*`
dependency but not a core one; serialised models use `safetensors` or `joblib` — **loading untrusted
pickle is prohibited**; no automatic model download, ever — local paths with recorded digests only;
every extra's absence is a tested path.

## 16. Gate L, revised

1. rights-cleared, deduplicated, provenance-complete, causally labelled experience accumulates
   reproducibly from the system's own verified runs;
2. **a learned component provably cannot alter the deterministic mandatory path** — identical
   decisions absent, disabled, and abstaining, recorded as `MandatoryPathInvariance`; and every
   contract or port edit made while adding a component is recorded and ADR-justified
   (`ExtensionConformanceRecord`). *Per D1 this is a behavioural guarantee plus measured drift, not
   a no-core-change guarantee;*
3. one uniform situation encoding serves at least four domains;
4. a forgetting benchmark exists, is a hard promotion gate, and demonstrably rejects a component
   that forgets;
5. retrieval scales to a measured capacity envelope with an ANN index and incremental insert, with
   the exact-search path preserved where required;
6. deterministic baselines remain first-class; every learned component abstains and falls back;
7. **the training corpus's distribution divergence from real governed traffic is measured, not
   merely disclosed** — recorded as `DistributionComparisonRecord`, with its sample count, and
   reported as "not established" rather than "low" whenever the sample is below the declared
   threshold; the two corpora are provably role-separated (7.1.3);
8. at most one bounded, reversible, operator-approved activation — or a reproducible no-go;
9. no learned component is mandatory, hides state, updates weights online, or holds authority.

A no-go on condition 8 is a valid closure. A failure on 1, 2, 4, 5, 6, 7, or 9 is not. **Condition 2
is the defining condition**, in the narrowed form D1 permits.

Condition 7 is satisfied by *measuring and disclosing*, not by achieving low divergence. A large
measured divergence is an acceptable Gate L outcome, provided it is measured, disclosed, and
reflected in the activation scope. Silently not knowing is what the condition forbids.

## 17. Explicit non-goals

- **No language capability and no generative component.** Only the substrate is in scope. No closure
  report may claim otherwise.
- **No `torch`, no CUDA, no LoRA, no distillation** in Sprint 21.
- **No pre-training and no full fine-tuning**, ever, on this hardware: measured 16 303 MiB VRAM
  makes 7B+ full fine-tuning and from-scratch language pre-training infeasible by orders of
  magnitude.
- **No guarantee that a future capability needs zero contract changes** — D1 traded that for
  flexibility; see 3.1.2.
- **No *statistically strong* measurement of self-play distribution bias.** The revised D3 measures
  it, but the real-run corpus in 21A will be small (13 events at baseline; volume accrues only with
  actual use), so the comparison supports coarse marginal divergence on high-cardinality
  `TaskSignature` fields and nothing finer. Below the declared sample threshold the verdict must be
  "not established".
- **No training on real governed runs in 21A.** The real-run corpus is evaluation-only, by guardrail
  7.1.3 — so the reranker's *training* distribution remains self-play, and no result may be
  generalised to real traffic beyond what the comparison actually establishes.
- **No online learning from live user tasks.** Learning happens in governed sessions over immutable
  snapshots.
- **No autonomous model acquisition.** No downloads; operator-provided local artifacts with digests.
- **Weights are never authoritative.** PostgreSQL and the event store remain the source of truth.
- **No self-promotion.** Every activation is operator-approved.
- **The forgetting gate measures only what the benchmarks cover.**
- **Sprint 22 coupling is partial.** 21.3 delivers the retrieval capacity envelope, not the
  long-horizon campaign framework.

## 18. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Ablation labels are overwhelmingly "neutral", leaving little signal | **High** | High | Measure the class balance in 21.1 *before* building 21.5; if signal is thin, the reranking surface is reconsidered at the 21.1 gate rather than after the work |
| Self-play bias produces a reranker that only works on fixtures | High | **Reduced to Medium** | Now **measured** via the evaluation-only real-run corpus (7.1.2): feature divergence, weak-label correlation, abstention divergence — plus held-out domains, abstention testing, and the confident-wrongness hard failure |
| The bias measurement is too under-powered to conclude, because real-run volume stays low | **High** | Medium | Sample count recorded on every comparison; "not established" is the mandatory verdict below threshold, so a weak measurement cannot masquerade as a clean bill of health. Volume accrues into Sprint 22 automatically |
| Evaluation corpus leaks into training, destroying the bias measurement | Low | **High** | `corpus_role` contract validator *and* a database constraint (section 10); time-aware and group-aware splits; a dedicated test asserting rejection from both layers |
| Contract churn accumulates unnoticed under the looser D1 boundary | Medium | Medium | `ExtensionConformanceRecord` + mandatory ADR per contract edit; reviewed at each phase gate |
| ANN index weakens the exact-search guarantee documented today | Medium | Medium | Keep exact search per query class; record recall explicitly; documented behaviour change, never silent |
| The Tier-3 amendment weakens a real safety property | Certain, by design | High | Narrowest form (7.3); separate contract; ADR; manual review; `training_actions` invariant preserved |
| Beating weighted RRF turns out to be hard | Medium | Low | A recorded null result is a valid 21.6 outcome; the substrate's value does not depend on it |
| Scope overrun | Medium | Medium | 21A/21B split; Tier C fully excluded; 21A independently valuable |

## 19. Status

Decisions D1, D4, D5 and the **revised D3 (both corpora, with the two guardrails)** are applied. D2
is taken as settled (21A + 21B in scope). No open decision blocks phase 21.0.

Three items should be revisited at the 21.1 gate rather than now, because they depend on data that
does not yet exist:

1. **the ablation class balance** — if "useful" labels are too rare, the first learned surface
   should be reconsidered before 21.5, not after;
2. **the self-play volume multiplier** — the 10 000-record target in 7.4 is derived from the case
   count and candidate fan-out, not from a learning-curve measurement; the measurement replaces the
   estimate once the harness exists;
3. **the minimum sample threshold for a conclusive distribution comparison** — it must be declared
   before the first comparison runs, so the threshold cannot be chosen after seeing a result that
   would look better on the other side of it.

**Closing update.** Sprint 21 executed and Gate L was assessed. The surface actually measured was
**skill selection**, not context reranking as this section anticipated — the reranking surface was
measured degenerate at the 21.1 gate (every candidate `required=True, pinned=True`), exactly the
contingency risk 1 above names, and skill selection was substituted per an explicit owner decision.
The 21.6 measurement then found skill selection itself unlearnable for an unrelated, sharper
reason: the label is a closed-form function of data already declared before the run, the
deterministic rule already implements it, and the domain path performs no selection decision at
all. Full results: [Gate L assessment](gate-l-assessment.md),
[ADR 0083](../../adr/0083-baseline-ladder-and-the-skill-selection-null-result.md). Gate L closes
8/9, with condition 8 (promotion) as a reproducible no-go — a valid closure under this section's own
terms, and one that exercised every non-negotiable gate (2, 4, 5, 6, 7, 9) rather than merely
declaring them satisfied.
