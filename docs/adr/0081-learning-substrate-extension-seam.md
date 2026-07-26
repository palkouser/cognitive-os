# ADR 0081: The learning substrate is an extension seam, not a learner

## Status

Accepted for Sprint 21A.

## Context

Sprint 21 was reclassified from the optional Learned Components Laboratory of the Sprint Group 4
specification into the project's critical sprint, with five owner requirements: no catastrophic
forgetting, uniform cross-domain integration, eventual operation without a large LLM, runtime
scalability, and a candidate-method order ranked by expected success.

The owner then clarified requirement 3: **the agent's own language capability is not an exit
condition.** What must be delivered is the functional foundation in code that lets language
capability — and any other future learned capability — be added later as a complement to the agent's
base functions, without modifying the core.

## Decision

Sprint 21A delivers the seam, not the learner.

### The port family and the descriptor

`application/ports/learned.py` defines `LearnedComponentPort` (inference, mandatory),
`LearnedTrainerPort`, `LearnedDatasetPort`, and `LearnedArtifactStorePort`. Only the inference
protocol is mandatory, because this repository already ships two inference-only learned adapters —
`LocalSentenceTransformerProvider` and `LocalCrossEncoderReranker` — and a component that never
trains must not be forced to implement a trainer. The seam is therefore a generalisation of a
pattern already proven in the codebase rather than a new architecture.

`LearnedComponentDescriptor` is what makes a future capability additive: one configuration-declared
record stating surface, tier, capability class, resource class, required optional-dependency extra,
artifact format, abstention support, explanation kind, deterministic baseline, and limitations.

### The core boundary (owner decision D1)

Core means **the deterministic mandatory execution path**. Contracts under `domain/**` and protocols
under `application/ports/**` are not frozen and may be extended when a capability genuinely needs
it.

The consequence is stated rather than hidden: "a future capability needs no core change" **cannot be
a CI gate** under this boundary. What is a CI gate is the more useful half:

> **Mandatory-path invariance.** With a learned component absent, present but disabled, or present
but > abstaining, the deterministic path produces identical decision digests over the recorded case
set.

`MandatoryPathInvariance` records it and exposes `identical`; `LearnedPromotionAssessment` refuses
eligibility when it is false. Contract and port drift is recorded instead of forbidden, and requires
its own ADR.

Because contracts may evolve later, this sprint does **not** guess a future generative adapter's
contract shape. Speculative descriptor fields (`generative`, `gpu_required`, `base_model_identity`,
`adapter_of`) are deliberately absent; the sprint that builds that capability adds them. The one
field kept ahead of need is `LearnedPrediction.payload_artifact`, because retrofitting artifact
indirection later would rewrite every stored prediction.

### Method order (requirement 5)

Ranked by the two requirements that eliminate candidates before accuracy is considered — forgetting
and scalability:

| Tier | Method | Why here |
|---|---|---|
| A | Non-parametric retrieval (kNN over pgvector) | Forgetting is impossible by construction: learning is an `INSERT`. Scaling is an index property. Roughly 80 % already built. The k neighbours are the explanation |
| B | Incremental parametric heads (SGD, trees, boosting) | Deterministic under a seed, retrainable from the immutable corpus in minutes, interpretable |
| C | Adapter-based learning over frozen base weights | The right eventual design for language capability — parameter isolation is the strongest structural forgetting defence — but out of scope; `torch` does not enter the repository in Sprint 21 |
| D | KAN, graph-neural | Research only, permitted to end in a no-go |

Rejected: online gradient updates on live tasks; one monolithic model owning all domains; learned
weights as authoritative state.

### Structural invariants, enforced in contracts

Three properties are enforced by model validators rather than by review, because review does not run
in CI:

1. `LearnedShadowResult.shadow_actual_outcome` is typed `None` — copying the Sprint 16
   `ShadowRoutingResult` precedent — so the outcome of a decision that was never executed cannot be
   recorded even deliberately. `executed_decision` must equal the deterministic baseline.
2. A `LearnedDatasetSnapshot` with `corpus_role="training"` cannot contain `REAL_GOVERNED_RUN`
   provenance, keeping the evaluation corpus uncontaminated (owner decision D3, revised).
3. `LearnedPromotionAssessment` cannot become eligible while forgetting regressed, while invariance
   is unproven, while the component cannot abstain, or without a material improvement.

Additionally `AblationLabel` refuses `REAL_GOVERNED_RUN` provenance outright, because such a run's
counterfactual is unobtainable (see "Consequences").

## Alternatives considered

**A stricter core boundary** — extensions loaded as external plugins from outside `src/cognitive_os`
— was considered and rejected by the owner. It would give a stronger guarantee at the cost of a
plugin discovery and trust boundary (signature and digest verification, import sandboxing) that this
project has not needed.

**Freezing contracts and ports** was rejected for the same decision. It would have forced this
sprint to predict a generative adapter's contract needs, which is speculative generality.

**Deriving the event-count assertions** from the catalog was considered and rejected when the two
count tripwires (193 → 204) failed: those literals exist precisely so that adding an event is a
deliberate act. Unlike the seed-count literals that broke CI in Sprint 20, they do not duplicate a
value that has a single source of truth.

## Consequences

### A measured finding that blocks the planned first surface

The plan selected context candidate reranking as the first learned surface (owner decision D5) and
leave-one-out ablation as the labelling strategy, with a gate requiring the label balance to be
measured **before** the harness is built. That measurement was taken and it fails:

- domain fixture cases declare **4–6 context candidates each** (34 cases with 4, 10 with 5, 7 with
  6; 228 candidates over 51 cases);
- **every candidate is `required=True` and `pinned=True`** in `domains/context.py`;
- a built bundle includes **4 of 4** with **0 exclusions** against a budget of 64 items, so there is
  no budget pressure and **reordering cannot change any outcome**;
- ablating any candidate raises — `ContextRetrieverError` for task and plan items,
  `RequiredContextMissingError` for assumptions and provenance — so **4 of 4 ablations are hard
  failures** and every label is `useful`.

`LabelBalance.degenerate` reports exactly this state. The consequence is that the reranking surface
has no learnable task on the self-play corpus as it stands, and the ablation labelling produces no
signal there. The gate did its job at the cheap moment: before the harness existed.

Resolving it is an owner decision, not an implementation detail, and is deliberately left open by
this ADR. The options are recorded in the Sprint 21 technical plan.

### What this ADR does not deliver

No self-play harness, no dataset materialisation, no ANN index, no registry wiring, and no learned
component. Those phases follow the surface decision above.

## Verification

- `domain/learned.py`: 13 public contracts, schemas exported, drift gate passing.
- `events/learned_events.py`: 11 event payloads registered; both count tripwires updated
  deliberately from 193 to 204.
- 32 contract tests covering every structural invariant above, including the negative case for each.
- Ruff, Ruff format, MyPy (508 source files), and Bandit clean.
- The ablation measurement in "Consequences" was produced by running the existing
  `build_domain_context` with its `omit` parameter against every required item of a fixture case.
