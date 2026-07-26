# Cognitive OS — Development Plan: Sprint 21 completion and Sprint 22

**Document status:** Draft for owner review — revision 1
**Date:** 2026-07-25
**Baseline:** branch `feature/sprint-21a-learning-substrate` at `cec0dc0`
**Stage gates:** Gate L v2 (Sprint 21 completion), Gate M (Sprint 22)

## 1. Owner decisions this plan is built on

Four decisions were taken before this plan was written, and each shapes it:

| # | Decision | Consequence |
|---|---|---|
| **D-A** | The new exit condition ("own ML method created **and wired in**") is satisfied by **both** paths together: an immediate bounded activation on the cold-start tie-break surface, **and** headroom creation (fallible coding domain + real-run corpus) where material improvement is measurable. | Phase 21D has two exit conditions, not one. A silent no-go is no longer a valid closure: if no surface shows headroom after the corpora exist, that is escalated to the owner with the measurements, not recorded quietly. |
| **D-B** | The fourth domain is **coding**. | The only candidate whose baseline can genuinely fail (pytest repair), so it delivers Gate L condition 3 evidence **and** creates the learnable signal in one move. |
| **D-C** | Tier C enters as an **on-ramp only**: local embedding model activation + the teacher-output retention hook. No `torch`, no LoRA yet. | Language-capability data acquisition starts now; adapter training remains a later sprint with a corpus that will by then exist. |
| **D-D** | **Self-hosting counts as real traffic**: the agent's governed work on its own repository (weakness→proposal→controlled-change cycles, operator CLI runs) is harvested as the real-run corpus. | B1 closes with continuously accruing data; this is also the project's stated purpose (the agent improving its own code). |

## 2. Current state, measured

What stands (all verified green at `cec0dc0`):

- Learning substrate: 17 sealed contracts, ports, events, registry, mandatory-path
  invariance gate, forgetting gate, baseline ladder, OOD gate, promotion assessment.
- Governed skill selection is live on the domain path (`permitted_canonical_names`,
  `NOT_PERMITTED` exclusions, honest selection reasons); accumulated statistics break
  ties (12/17 physics selections by `verified_statistics`).
- Two counterfactual corpora: 969 monotone labels (`SELECTION_FORCED`) and 51 two-sided
  labels (`SELECTION_REPLACED`, useful=0/neutral=17/harmful=34).
- ANN capacity measured at 10⁵ × 768d: 15 ms at 0.992 recall@20 (21×) on a clustered
  corpus; exact path exhaustive by SQL shape (ADR 0082).
- Gate L closed 8/9 with a reproducible no-go on condition 8 (ADR 0083); the three
  follow-up items are closed (ADR 0084).
- 1230 unit/contract tests, 42 integration tests, all benchmark/governance gates green.

The five weaknesses this plan must eliminate:

| ID | Weakness | Closed by |
|---|---|---|
| W1 (B1) | No real-world experience accumulates; distribution divergence `not_established` (0 real samples vs threshold 100) | 21C.4 harvester + D-D self-hosting; conclusive comparison in 21D.5 |
| W2 (B4 residual) | HNSW impossible above 2 000 dims while configuration permits 4 096; no quantisation | 21C.2 halfvec quantised indexes + measured recall |
| W3 | Gate L condition 3 partial: 3 domains, not 4 | 21C.1 coding domain |
| W4 | Learning proven on one surface only (skill selection), and that surface has no headroom | 21C.1 (fallible baselines) + 21D.3/21D.4 (second surface) |
| W5 | Language capability: seam ready, no component, no data acquisition | 21C.5 teacher retention + 21C.6 local embeddings (D-C on-ramp); adapters deferred with a stated on-ramp exit |

## 3. Gate L v2 — the revised exit conditions

Conditions 1, 2, 4, 5, 6, 7, 9 are unchanged from the revised Gate L and remain met
(re-verified at closure). Two conditions change:

**Condition 3 (v2):** one uniform situation encoding serves **four** domains —
mathematics, physics, logic, **coding** — with the identical-shape test extended and the
cross-domain pilot executing coding cases end to end through the same governed path.

**Condition 8 (v2), per D-A — both required:**

- **8a. Bounded activation at parity:** one own-built component (Tier A kNN) is ACTIVE on
  the cold-start tie-break surface — deciding only where every merit key ties and
  statistics are below the sample threshold — operator-approved, reversible, with proven
  mandatory-path invariance and a persisted lifecycle state. Parity is sufficient here
  because the bounded scope provably cannot degrade an outcome.
- **8b. Material improvement where headroom exists:** on the coding-inclusive corpus
  and/or the real-run corpus, the baseline ladder is re-run; at least one surface must
  show a learned component materially beating the strongest non-learned rung, pass every
  gate (forgetting, invariance, OOD abstention, ladder pin), and reach
  operator-approved bounded activation. If **no** surface shows headroom, the sprint
  does not close silently: the measurements are escalated to the owner as a decision
  point (revise surfaces, revise corpus, or accept a recorded no-go **explicitly**).

## 4. Phase 21C — Foundations and headroom

### 21C.1 Coding as the fourth cross-domain domain

The decisive property: coding cases must include tasks whose **baseline can fail**.
Everything else in this plan's learning story depends on that.

Tasks:

1. `DomainKind.CODING`; problem types registered in the problem-type registry, each with
   two permitted skills (the existing `python-repair` and `focused-tests` families):
   - `pytest-repair` — a failing test plus a defective function; solver applies a
     deterministic repair strategy; checker runs sandboxed pytest (`coding.pytest`).
   - `test-selection` — pick the minimal test subset that exercises a changed function;
     checker verifies the selected set fails before/passes after.
   - `assertion-repair` — a broken assertion to correct against a specification.
2. Deterministic solver/checker pair per type, reusing the sandbox
   (`tools/sandbox/lifecycle.py`) and the existing `coding.pytest` verifier capability.
   Sandboxed execution must stay inside the existing tool authority (ADR 0073).
3. ≥ 16 seed cases. **At least 4 must have a fallible baseline** — repair tasks whose
   primary skill's deterministic strategy does not always succeed (e.g. multi-edit
   repairs where the single-edit strategy fails). Baseline failure is measured, not
   assumed: the exit evidence includes the per-case baseline outcome table.
4. Extend fixtures, benchmark manifests (`sprint20-domain-ci`/`seed` gain coding cases or
   a `sprint22-coding-ci` manifest is added), smoke tests, and the encoding-shape test to
   4 domains.

Exit evidence:
- All coding cases execute through `run_case_as_skill` with recorded selection; permitted
  sets enforced; governance and benchmark gates green.
- Measured baseline outcome table showing ≥ 4 cases with `accepted=False` baselines.
- `test_the_encoding_is_identical_across_every_domain` passes with 4 domains.
- ADR: coding domain authority and sandbox boundary.

### 21C.2 Quantised ANN for high dimensions (closes W2/B4 residual)

pgvector's `halfvec` (16-bit) supports HNSW up to 4 096 dimensions. The same partial
expression-index pattern from ADR 0082 applies: `USING hnsw ((embedding::halfvec(3072))
halfvec_cosine_ops) WHERE dimension = 3072`.

Tasks:

1. Migration 0014: partial halfvec HNSW indexes for declared high dimensions; the
   declared set moves to one place (`APPROXIMATE_INDEX_DIMENSIONS` split into full/half
   precision tiers); health checks extended to the halfvec index names.
2. Repository: the approximate distance expression casts to `halfvec(N)` for dimensions
   above 2 000; exact path untouched (same SQL-shape guarantee, same plan-readback
   integration test extended).
3. `RetrievalCapacityEnvelope` gains a `quantisation` field (`none` | `halfvec`); an
   envelope for a quantised index must state it, and its recall is measured against the
   full-precision exhaustive result — quantisation error is then *inside* the recall
   number, disclosed rather than hidden.
4. Measured envelope at 10⁵ × 3072d (clustered + uniform floor), same script extended.

Exit evidence: migration up/down verified; plan readback shows the halfvec index used;
envelope with `quantisation=halfvec` and measured recall committed; ADR amendment to 0082.

### 21C.3 Learned-plane persistence (migration 0015)

Activation (21D.1) requires durable state; everything is currently in-memory.

Tables (append-only history + current projection, matching the Sprint 9–20 conventions):
`learned_component_states` (+history), `learned_promotion_assessments`,
`learned_baseline_ladders`, `learned_ood_assessments`, `learned_dataset_snapshots`,
`learned_counterfactual_labels`, `learned_capacity_envelopes`,
`learned_distribution_comparisons`. Weights/corpora stay in the Artifact Store;
PostgreSQL holds identity, lineage, metrics, verdicts.

Database-level guardrail (from the 21 plan, section 10): the training-snapshot
provenance restriction is a CHECK constraint as well as a contract validator.

Exit evidence: migration 0013→0015 up/down verified; health checks; postgres adapters
with the same port surface as the in-memory ones; integration tests; least-privilege
grants; backup manifest coverage.

### 21C.4 Real-run harvester (closes W1/B1, per D-D)

Tasks:

1. `learning/harvest.py`: after any governed run completes (controller runs, domain
   pilot runs, weakness→proposal→controlled-change cycles, operator CLI), a
   `RealRunObservation` is recorded — situation encoding, selection decision, outcome,
   provenance `REAL_GOVERNED_RUN` — into the evaluation corpus **only**. The 7.1.3
   guardrails stand: contract + DB constraint keep real runs out of training snapshots;
   no counterfactual labels from real runs (structurally impossible already).
2. Wire-in points: `run_case_as_skill` / controller completion hook / change-cycle
   completion; each emits `learned.real_run_harvested`.
3. `scripts/learning.py harvest-status`: corpus size, per-domain distribution, days to
   the 100-sample threshold at current rate.
4. First conclusive `DistributionComparison` when ≥ 100 samples exist. A verdict of
   `HIGH` divergence is an acceptable, disclosed outcome; `not_established` stops being
   the only reachable verdict.

Exit evidence: harvested corpus grows across ordinary development sessions without
per-run operator action; comparison produced and persisted; sample count and per-domain
distribution in the closure report.

### 21C.5 Teacher-output retention hook (D4 debt; Tier C on-ramp, part 1)

Tasks:

1. Provider-plane hook: every LLM request/response pair on governed paths is retained —
   hashed, rights-recorded, stored in the Artifact Store with a `TeacherExchangeRecord`
   contract (`ProvenanceClass.TEACHER_OUTPUT` added; allowed in **training** snapshots,
   which is the point of a teacher corpus, and the B3 narrow amendment path from the
   Sprint 21 plan section 7.3 governs any actual training use).
2. Retention is fail-open for the run and fail-visible for the corpus: a failed
   retention never blocks the governed run, but is counted and surfaced in health.
3. `scripts/learning.py teacher-status`: exchange count, token volume, per-model split.

Exit evidence: exchanges from real provider traffic accumulate; contract + schema +
events; a retention-failure health finding; zero impact on run outcomes (invariance
sweep unchanged).

### 21C.6 Local embedding model activation (Tier C on-ramp, part 2)

The `sentence_transformers` optional extra, digested local model path, and the
`EmbeddingProviderConfiguration` seam already exist; the 768d HNSW index from 0013 is
waiting for exactly this.

Tasks: operator provisioning runbook (model choice, digest pinning); provider enabled in
memory + semantic planes; measured retrieval-quality comparison against the
deterministic embedding on a fixed English query set (recall@k over seeded semantic
pairs); capacity envelope at 768d with the real model's vectors replacing synthetic
gaussians.

Exit evidence: local model active without network access; measured quality delta;
envelope re-measured on real embedding distribution; documentation.

## 5. Phase 21D — The own ML method, wired in (Gate L v2 closure)

### 21D.1 Bounded activation: cold-start tie-break (exit condition 8a)

The surface: when every merit key ties (specificity, scope) **and** statistics are below
the sample threshold, selection currently falls to `str(skill_id)` — an arbitrary key
carrying no information. The Tier A kNN, voting over accumulated counterfactual and
real-run experience, replaces exactly that key and nothing else.

Tasks:

1. `SkillSelectionService` integration: an optional `LearnedComponentRegistry` consult
   at the tie-break position only; abstention → canonical tie-break, unchanged. New
   selection reason `LEARNED_TIE_BREAK` so the decision record names it honestly.
2. Full gate run: invariance (absent/disabled/abstaining identical — note the component
   only acts where outcomes tie at parity, so invariance must still hold on the whole
   corpus), forgetting, OOD abstention, ladder with the canonical tie-break as the
   deterministic rung, promotion assessment.
3. Operator approval step; ACTIVE state persisted (21C.3); kill-switch documented and
   tested (DISABLED transition mid-sweep).
4. Post-activation monitoring: per-selection events; a weekly (campaign-scheduled in 22)
   re-run of the invariance and forgetting gates.

Exit evidence: one own-built component ACTIVE on a governed surface, bounded, reversible,
every gate green, decision records showing `LEARNED_TIE_BREAK` selections in real sweeps.

### 21D.2 Corpora over four domains

Re-run both harnesses (`selfplay`, `replacement`) over the coding-inclusive case set.

**Falsifiable predictions, recorded before the run:** on the replacement corpus, coding
cases with fallible baselines make `useful` empirically non-zero for the first time; and
the deterministic `requirements_available` rule stops being perfect, because coding
outcomes depend on runtime repair success, not on declared capabilities alone. If either
prediction fails, the headroom assumption is wrong and 8b escalates early — that is the
point of recording them.

Exit evidence: class balances for both corpora; the existing tripwire
(`test_the_deterministic_rule_is_perfect_on_this_corpus`) **expected to flip** and be
updated with the measured number; corpus snapshots persisted (21C.3).

### 21D.3 Ladder v2 and the Tier B decision (exit condition 8b)

1. Ladder re-run on the 4-domain corpus, group-aware and held-out-domain splits, with
   the deterministic rung now measured (not assumed) — plus the real-run corpus as an
   evaluation-only reference.
2. If Tier A materially beats the strongest non-learned rung → promotion path directly.
3. If Tier A ties or loses while headroom exists (deterministic rung < 1.0), install the
   `learned-baseline` extra (scikit-learn) and climb the trial order: logistic/SGD →
   decision tree → random forest → gradient boosting, **stopping at the first rung that
   materially beats**, per the straw-man rule already enforced by `BaselineLadder`.
4. Winner through every gate → operator-approved bounded activation on the
   skill-selection surface (beyond the tie-break scope of 8a — e.g. advisory reranking
   with abstention, scope defined in the promotion assessment).
5. If nothing beats the deterministic rung anywhere: **escalation packet** to the owner —
   the measured ladders, the corpus balances, and the surface options — for an explicit
   decision. Not a silent no-go (D-A).

Exit evidence: persisted ladder + promotion assessment; either an ACTIVE component with
material improvement or the escalation decision recorded.

### 21D.4 Second surface, chosen by measurement

After 21C.4 data exists, measure headroom on the two candidate surfaces and take the
better one through the same gates in shadow first:

- **Model-capability routing** (Sprint 16 shadow structures exist): predict
  success/cost per provider from accumulated real-run outcomes; deterministic baseline =
  current routing policy.
- **Memory-retrieval reranking**: predict `used_in_context` from retrieval features
  against the access-audit ground truth the Memory Plane already records.

Exit evidence: one surface measured end to end (ladder, OOD, forgetting) with shadow
evidence persisted; activation only if 8b-grade improvement, otherwise the shadow record
and the reason.

### 21D.5 Gate L v2 assessment and Sprint 21 closure report

All nine conditions re-assessed with evidence links; conditions 3 and 8 in their v2
forms; the closure report states measured numbers only. Sprint 21 is then **complete**.

## 6. Phase 22 — Scale and autonomy (Gate M)

### 22.1 Capacity at 10⁶

The 10⁵ envelope exists; 10⁶ is an execution task, not a design question (build time
scaled ~linearly: ≈ 35–40 min expected for 768d full precision, measured rather than
assumed). Run for 768d full precision and 3072d halfvec; operations runbook updated
(maintenance_work_mem, lock window, `CONCURRENTLY` guidance for live tables).

Exit evidence: committed envelopes at 10⁶ with recall and build cost; incremental-insert
measurement (insert throughput with the index in place), since Tier A's "learning is an
INSERT" claim depends on it.

### 22.2 Long-horizon campaign framework

The loop that makes accumulation autonomous rather than session-bound:

1. `learning/campaign.py`: a campaign = a bounded, resumable sequence of governed runs
   (domain cases, self-play sweeps, harvest cycles) with a manifest, budget, and
   checkpointing; every run flows through the 21C.4 harvester.
2. Scheduled maintenance: corpus snapshot revisions; Tier B retrain-from-immutable-corpus
   with the forgetting benchmark as a hard gate on every retrain; scheduled invariance
   re-verification for ACTIVE components.
3. Operator surface: `scripts/learning.py campaign start|status|stop`; events; health.

Exit evidence: a campaign runs across process restarts without per-run operator action;
corpus growth curve recorded; ≥ 1 scheduled retrain executed with the forgetting gate
demonstrably enforced (including one deliberate red run in tests).

### 22.3 Self-improvement loop closure

The weakness-mining → proposal → controlled-change cycle (Sprints 18–19) starts
consuming learned-plane evidence: confident-error clusters, selector statistics
anomalies, forgetting near-misses, and divergence findings become mining sources.

Exit evidence: ≥ 1 controlled change merged whose originating weakness signal came from
the learned plane, with the full evidence chain (signal → proposal → change → verified).

### 22.4 Language-capability foundation metrics (requirement 3, honest form)

No generative claim. What Sprint 22 delivers and measures:

- teacher corpus volume (exchanges, tokens, per-model split) with growth targets set
  from 21C.5's measured accrual rate;
- semantic claims extracted from teacher outputs through the existing semantic plane
  (count, verification rate);
- English retrieval quality: recall@k on a fixed English query/pair set against the
  local embedding provider, tracked across corpus growth;
- a written distillation-readiness assessment: what corpus size and quality the first
  adapter-training sprint (full Tier C) would need, so that sprint starts from a
  measured threshold instead of a guess.

### 22.5 Gate M

1. Retrieval capacity measured at 10⁶ with incremental insert, quantisation disclosed.
2. Experience accumulates autonomously (campaign framework) from self-hosted real
   traffic; distribution comparison conclusive and periodically refreshed.
3. ≥ 1 own-built learned component ACTIVE with measured benefit over ≥ N real
   selections (N declared before measurement), and ≥ 1 additional surface measured
   through the full gate stack.
4. Scheduled retraining exists and the forgetting benchmark has demonstrably rejected at
   least one deliberate regression (the gate is exercised, not decorative).
5. Self-improvement loop closed: learned-plane evidence produced ≥ 1 merged controlled
   change.
6. Language-capability foundation: teacher corpus + embedding quality metrics tracked,
   distillation-readiness assessment written.
7. Every Sprint 21 guarantee intact: mandatory-path invariance, abstention/fallback,
   no online weight updates, no learned authority, weights derived and discardable.

A failure on 1, 2, 4, or 7 blocks Gate M. Condition 3's improvement half follows the
D-A escalation rule rather than silent-no-go.

## 7. Sequencing and dependencies

```text
21C.1 coding domain ──────────────┬─→ 21D.2 corpora ─→ 21D.3 ladder v2 ─→ 8b activation/escalation
21C.2 halfvec ANN ────────────────┼─→ 22.1 10⁶ envelopes
21C.3 persistence (0015) ─────────┼─→ 21D.1 activation (8a) ─→ 21D.5 Gate L v2
21C.4 harvester (real runs) ──────┼─→ 21D.4 second surface ──→ 22.2 campaigns ─→ 22.3 loop ─→ Gate M
21C.5 teacher retention ──────────┴─→ 22.4 language metrics
21C.6 local embeddings ──────────────→ 22.4
```

21C tasks are parallelisable except 21C.3 → 21D.1. The critical path to Gate L v2 is
21C.1 → 21D.2 → 21D.3; the critical path to Gate M runs through 21C.4 → 22.2.

## 8. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Coding fallible-baseline cases are hard to make deterministic (flaky sandbox) | Medium | High | Sandbox already pinned and offline; repair tasks chosen so failure is a deterministic property of the strategy, not of timing; per-case reproducibility test mandatory |
| The 21D.2 predictions fail — coding adds cases but no headroom | Medium | High | Predictions recorded before the run; early escalation per D-A instead of building 21D.3 on a false premise |
| Self-hosted "real traffic" is too homogeneous to be a meaningful reference | Medium | Medium | Disclosed on every comparison (the corpus states its source); campaign tasks (22.2) diversify it; divergence verdict HIGH is an acceptable outcome |
| halfvec quantisation loses recall at high dims | Medium | Medium | Recall measured against full-precision exhaustive truth and disclosed in the envelope; exact path always available |
| Tie-break activation surface is too small to demonstrate value | Low | Medium | 8a's claim is bounded harmlessness + wiring, not value; value is 8b's job |
| Teacher retention captures sensitive content | Medium | High | Rights/sensitivity recorded per exchange; sensitivity ceiling enforced at write; retention excluded for restricted-sensitivity runs |
| scikit-learn enters and the trial order still finds nothing | Medium | Low | The extra is installed only after measured headroom exists (21D.3 step 3); a null result then still escalates with data |
| Scope: 21C+21D+22 is three sprints of work | High | Medium | Phases are gate-separated; Gate L v2 can close on 21C+21D alone; 22 has its own gate |

## 9. Explicit non-goals

- No generative language component and no `torch`/LoRA/CUDA in this cycle (D-C); the
  on-ramp (teacher corpus + local embeddings) is the deliverable, adapters are the next
  cycle's, started from a measured distillation-readiness threshold.
- No online weight updates, no learned authority, no mandatory learned component —
  the Sprint 21 invariants are permanent.
- No claim that self-hosted traffic represents external-user traffic; every comparison
  states its source.
