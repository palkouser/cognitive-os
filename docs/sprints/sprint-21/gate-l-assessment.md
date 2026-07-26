# Sprint 21 — Gate L assessment

**Stage gate:** Gate L — Governed Learning Substrate
**Scope assessed:** Sprint 21A (phases 21.0–21.5), Sprint 21B (phases 21.6–21.7),
the governed-selection follow-up, and the coding domain
**Assessed at:** branch `feature/sprint-21a-learning-substrate`, release candidate
described in the [Sprint 21 substrate report](report.md)
**Revision:** 2 — re-assessed at the real branch head during Sprint 21R
([backlog](sprint-21r-technical-backlog.md), item S21R-003)
**Date:** 2026-07-26

Revision 1 assessed three domains at `fcea853`. This revision re-runs every condition
against the four-domain head. Every number below was produced by a command in this
repository and is reproducible from the artifacts named in the report; nothing is
projected.

## Status: Gate L closes with a reproducible no-go on condition 8

Nine conditions assessed. Eight are met — condition 3 is now met rather than partially
met, because the fourth domain exists. Condition 8 closes as a **recorded no-go**, which
the revised gate defines as a valid closure: *"A no-go on condition 8 is a valid closure.
A failure on 1, 2, 4, 5, 6, 7, or 9 is not."* No condition in that non-negotiable list
failed.

**Gate L2 — the learning-completion gate — remains open.** Gate L is about the
substrate being safe, measured and governed. It is not a claim that the system learns
anything useful. Section *What this assessment does not claim* states the boundary.

## The conditions

| # | Condition | Verdict | Evidence |
|---|---|---|---|
| 1 | Rights-cleared, deduplicated, provenance-complete, causally labelled experience accumulates reproducibly from the system's own verified runs | **Met** | 969 `CounterfactualLabel` records from 1020 governed runs; balance useful=0, neutral=426, harmful=543; non-degenerate at 56.0 % majority; all label ids unique; `provenance_class=self_play` on every record; a real governed run is *structurally* unlabellable (`only_reproducible_provenance`) |
| 2 | A learned component provably cannot alter the deterministic mandatory path — identical decisions absent, disabled, and abstaining | **Met** (defining condition) | `MandatoryPathInvariance` with three identical decision digests, driven through the real registry lifecycle rather than a mock, proven against two differently shaped reference components plus `ExperienceKnn` |
| 3 | One uniform situation encoding serves at least four domains | **Met** — was partially met in revision 1 | One `SituationVector` encoding, identical feature shape across **4** domains: mathematics (18 cases, 9 problem types), physics (17, 8), logic (16, 8), coding (17, 3). 68 fixture cases and 28 registered problem types total. `test_the_encoding_is_identical_across_every_domain` asserts one shape and `>= 4` distinct domains |
| 4 | A forgetting benchmark exists, is a hard promotion gate, and demonstrably rejects a component that forgets | **Met** | Per-case retention; a deliberately forgetting component is `REGRESSED` and refused eligibility despite a 0.60 → 0.90 target improvement; a silently dropped case counts as regression |
| 5 | Retrieval scales to a measured capacity envelope with an ANN index and incremental insert, exact-search path preserved | **Met** | 10⁵ vectors / 768 dims: clustered 321 ms → **15 ms at 0.992 recall@20** (21×); uniform-noise floor 0.496; index scan confirmed from the plan. Exact search is exhaustive *by SQL shape*, asserted against a live planner ([ADR 0082](../../adr/0082-approximate-vector-retrieval-and-capacity-envelope.md)). Re-verified in Sprint 21R: `test_approximate_retrieval_reaches_the_index_and_exact_retrieval_cannot` passes against PostgreSQL 18 / pgvector 0.8.2 |
| 6 | Deterministic baselines remain first-class; every learned component abstains and falls back | **Met** | `BaselineLadder` refuses to validate without a deterministic rung; registry refuses to activate a component that cannot abstain; `active_for()` returns `None` normally |
| 7 | The training corpus's distribution divergence from real governed traffic is measured, not merely disclosed; the two corpora are provably role-separated | **Met** | `DistributionComparison` produced: training n=969, evaluation n=**0**, threshold 100, verdict **`not_established`**. Role separation is enforced by contract *and* stated as a limitation. Condition 7 asks for measurement and disclosure, not low divergence |
| 8 | At most one bounded, reversible, operator-approved activation — **or a reproducible no-go** | **No-go (valid closure)** | `LearnedPromotionAssessment` decision `abstention_unsupported`. Re-measured on the four-domain corpus; see below |
| 9 | No learned component is mandatory, hides state, updates weights online, or holds authority | **Met** | Absence is a first-class registry state; no online update path exists; `ExperienceKnn.remember()` returns a new component and never mutates; weights are derived and discardable |

## Condition 3: what the fourth domain does and does not add

The fourth domain is coding, with three problem types (`pytest-repair`,
`assertion-repair`, `test-selection`) and 17 seed cases. It closes condition 3 on
evidence rather than on the argument that the encoding *would* generalise: the encoding
is now verified identical across four domains, not three, and the feature schema is
still a single `FeatureSchema`.

Two limits must be read with it, both measured:

**It executes no code.** Solver and checker are in-process and R0. The checker compares
the candidate against the case's golden reference; its capability is
`coding.golden_equality`, deliberately not `coding.pytest`, because nothing runs pytest.
No sandbox is entered, no repair is executed, and no evidence from this domain may be
read as a test-execution result. [ADR 0085](../../adr/0085-coding-domain-as-fourth-cross-domain-domain.md)
records what a later sprint would have to build to change that.

**It produces no learned tie-break.** All 17 coding cases have exactly one applicable
skill candidate and select by `EXACT_SIGNATURE`; accumulated statistics never decide.
The cold-start tie-break surface — the one a bounded Tier A activation would occupy —
gains nothing from the fourth domain. Physics remains the only domain producing genuine
ties.

## Condition 8: why the no-go, re-measured

Revision 1 recorded the no-go on a three-domain corpus where the deterministic rung was
*perfect*: `requirements_available` scored 1.0000 with 0 confident errors, so there was
no headroom for any learned component to occupy.

That is no longer true, and the change is the substantive result of the coding domain:

| Rung | Evaluated | Score | Confident errors |
|---|---:|---:|---:|
| Majority (straw man) | 437 | 0.5034 | 217 |
| Deterministic `requirements_available` | 1292 | **0.9396** | **78** |

Six of the 17 coding cases have a baseline that measurably fails (pytest-repair 2 of 7,
test-selection 2 of 5, assertion-repair 2 of 5), because a coding outcome depends on
whether a repair strategy actually succeeds rather than on which capabilities were
declared. The deterministic rule can no longer explain the corpus.

**`0.9396` is prediction headroom, and nothing more.** Specifically it is *not*:

- evidence that any learned component beats the deterministic rung — none was trained
  against this corpus;
- evidence of improved agent success — the metric predicts whether a governed selection
  would be accepted, not whether the agent solved anything better;
- a Gate L2 result. Gate L2 needs a persistent, safe, materially useful learned
  component on a real surface. This is the *precondition* for looking for one.

The no-go therefore stands, with its reason changed: revision 1 recorded "no headroom
exists"; revision 2 records "headroom now exists and has not yet been contested." The
component that tied in 21B has not been re-run against the enlarged corpus, which is
Sprint 21D1/21D2 work, not Sprint 21R's.

Both safety gates passed on the 21B run — retention `retained`, invariance `identical`.
Full 21B analysis, including the straw-man trap it nearly walked into, is in
[ADR 0083](../../adr/0083-baseline-ladder-and-the-skill-selection-null-result.md).

## What this assessment does not claim

Stated so that no later reader infers more than was built.

- **No active learned component.** Nothing is promoted, nothing is enabled, and no
  activation was performed to obtain a green release.
- **No persistent learned state.** Corpora, ladders, assessments and envelopes live in
  memory and in committed artifacts. Migration `0014` and the learned evidence store are
  Sprint 21C1 work; the current migration head is `0013`.
- **No real-run experience.** Condition 7 is satisfied by measuring and disclosing a
  divergence that is `not_established` on **zero** real samples.
- **No executable coding corpus.** See condition 3 above.
- **No parametric learned component.** The ladder stopped at the deterministic rung, so
  `scikit-learn`, `xgboost`, `scipy` and `joblib` were never installed and no
  `learned-baseline` extra exists.
- **No `torch`, no CUDA, no LoRA, no adapters, no distillation, and no language
  capability.** An NVIDIA RTX 5070 Ti with driver 595.84 is present on the development
  host, and no gate, dependency or code path uses it.
- **No 10⁶ capacity point.** 10⁵ is measured; 10⁶ is Sprint 22B.

## Gate L2: what remains open, and what would close it

| Missing evidence | Required before Gate L2 | Owning sprint |
|---|---|---|
| Durable learned evidence and artifacts, replayable and rollback-capable | Migration `0014_create_learned_evidence_store.py` from head `0013`, with grants, health, backup and restore | 21C1 |
| Real governed traffic in the evaluation corpus | ≥ 100 harvested real-run observations, making `DistributionComparison` conclusive rather than `not_established` | 21C1 |
| Coding outcomes that depend on executed code | Sandboxed execution of candidate repairs, so a coding label reflects a real result | 21C3 |
| A learned component that materially beats the strongest non-learned rung | Pre-registered surface, ladder re-run against `0.9396`, every gate green, bounded operator-approved activation | 21D1, 21D2 |
| A learned tie-break surface with real ties | Measured headroom on a surface that actually ties; coding provides none | 21D1 |

## Follow-up items from revision 1: all three closed

Recorded as resolved rather than deleted, so the record shows what was found. Full
analysis: [ADR 0084](../../adr/0084-governed-skill-selection-on-the-domain-path.md).

1. **The domain path performed no skill selection — closed.** `run_case_as_skill` took
   `entry.skills[0]`, discarding a real choice: every problem type offers two candidates.
   The Skill Engine now selects, with `verifier_capabilities` set to the case's own
   `required_verifiers`, and the decision is recorded on `DomainSkillRun.selection`.
   Wiring it in immediately exposed that preconditions do *not* scope selection to a
   problem type's permitted set — selection reached `deterministic-arithmetic`, a
   legitimate mathematics skill outside the permitted list — so
   `SkillSelectionRequest.permitted_canonical_names` was added and non-permitted skills
   are recorded as `NOT_PERMITTED` exclusions rather than filtered out of sight.
2. **`statistics_score` inert — closed, and the diagnosis was wrong.** The deterministic
   aggregation already existed and was already written after every execution; the gap was
   that a fresh registry per case meant every selection read an empty log. Sharing the
   registry is the whole fix. Measured over 17 physics cases: 5 honest
   `canonical_tie_break` below the sample threshold, then **12 selections decided by
   `verified_statistics`**. A second defect surfaced: `SkillSelectionDecision.reason` read
   the winner's own attributes and claimed `exact_signature` while statistics were
   deciding; it now names the key that actually discriminated.
3. **`useful` unreachable — closed, and it was stronger than "unreachable".** The
   variation *adds* a required capability, a monotone restriction, so a rejected baseline
   could never be repaired and no corpus could ever have produced `useful`. The tripwire
   was watching for the impossible. `CounterfactualVariation` now marks monotone
   variations and the contract refuses `USEFUL` for one; `SELECTION_REPLACED` provides the
   genuinely two-sided variation. Measured: 51 labels, useful=0, neutral=17, harmful=34 —
   `useful` is now **reachable by construction and absent because the selector never picks
   a loser**, which is a property of the system working, and a different fact from the one
   previously recorded.

## Defect found while re-assessing

Sprint 21R's own gates exposed one release-blocking defect that no earlier gate had run.
It is recorded here because it changes the release head, and in full in the report.

Migration `0013` creates its two approximate-retrieval indexes as partial expression
indexes through raw SQL, a shape `Table` metadata cannot express. Autogenerate therefore
reflected them, found no counterpart, and proposed dropping them, so
`alembic -c infra/postgres/alembic.ini check` — the CI `migration` job's last step —
failed on every database upgraded to `0013`. The branch had never had a CI run, because
`ci.yml` triggers on push to `main` and on `pull_request` only. Fixed with a narrow
`include_object` hook derived from the same `APPROXIMATE_INDEX_NAMES` constant the
migration and the memory-plane health check use, plus three regression tests.
