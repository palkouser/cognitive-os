# Sprint 21 — Gate L assessment

**Stage gate:** Gate L — Governed Learning Substrate
**Scope assessed:** Sprint 21A (phases 21.0–21.5) and Sprint 21B (phases 21.6–21.7)
**Date:** 2026-07-25

## Status: Gate L closes with a reproducible no-go on condition 8

Eight of the nine conditions are met. Condition 8 closes as a **recorded no-go**, which the
revised gate defines as a valid closure: *"A no-go on condition 8 is a valid closure. A
failure on 1, 2, 4, 5, 6, 7, or 9 is not."* No condition in that non-negotiable list failed.

Every number below was produced by a command in this repository. Nothing is projected.

## The conditions

| # | Condition | Verdict | Evidence |
|---|---|---|---|
| 1 | Rights-cleared, deduplicated, provenance-complete, causally labelled experience accumulates reproducibly from the system's own verified runs | **Met** | 969 `CounterfactualLabel` records from 1020 governed runs in 27.1 s; balance useful=0, neutral=426, harmful=543; non-degenerate at 56.0 % majority; all label ids unique; `provenance_class=self_play` on every record; a real governed run is *structurally* unlabellable (`only_reproducible_provenance`) |
| 2 | A learned component provably cannot alter the deterministic mandatory path — identical decisions absent, disabled, and abstaining | **Met** (defining condition) | `MandatoryPathInvariance` with three identical decision digests, driven through the **real** registry lifecycle rather than a mock, proven against two differently shaped reference components plus `ExperienceKnn` |
| 3 | One uniform situation encoding serves at least four domains | **Partially met — see below** | One `SituationVector` encoding, identical feature shape across **3** domains (mathematics, physics, logic). The encoding is domain-agnostic; only three domains exist to serve |
| 4 | A forgetting benchmark exists, is a hard promotion gate, and demonstrably rejects a component that forgets | **Met** | Per-case retention; a deliberately forgetting component is `REGRESSED` and refused eligibility despite a 0.60 → 0.90 target improvement; a silently dropped case counts as regression |
| 5 | Retrieval scales to a measured capacity envelope with an ANN index and incremental insert, exact-search path preserved | **Met** | 10⁵ vectors / 768 dims: clustered 321 ms → **15 ms at 0.992 recall@20** (21×); uniform-noise floor 0.496; index scan confirmed from the plan. Exact search is exhaustive *by SQL shape*, asserted against a live planner ([ADR 0082](../../adr/0082-approximate-vector-retrieval-and-capacity-envelope.md)) |
| 6 | Deterministic baselines remain first-class; every learned component abstains and falls back | **Met** | `BaselineLadder` refuses to validate without a deterministic rung; registry refuses to activate a component that cannot abstain; `active_for()` returns `None` normally |
| 7 | The training corpus's distribution divergence from real governed traffic is measured, not merely disclosed; the two corpora are provably role-separated | **Met** | `DistributionComparison` produced: training n=969, evaluation n=**0**, threshold 100, verdict **`not_established`**. Role separation is enforced by contract *and* stated as a limitation. Condition 7 asks for measurement and disclosure, not low divergence |
| 8 | At most one bounded, reversible, operator-approved activation — **or a reproducible no-go** | **No-go (valid closure)** | `LearnedPromotionAssessment` decision `abstention_unsupported`; baseline 1.0000, candidate 1.0000. See below |
| 9 | No learned component is mandatory, hides state, updates weights online, or holds authority | **Met** | Absence is a first-class registry state; no online update path exists; `ExperienceKnn.remember()` returns a new component and never mutates; weights are derived and discardable |

## Condition 8: why the no-go

Two independent measurements, either of which alone is disqualifying.

**It ties the deterministic baseline.** On a group-aware split by case the learned kNN
scores 1.0000; the deterministic `requirements_available` rule also scores 1.0000. Required
improvement 0.05, actual improvement 0.0000.

**It does not know when it does not know.** Holding out each domain in turn: 969 evaluated,
**0 abstentions, 120 confident errors**. A component that answers confidently about a
capability vocabulary it has never seen cannot reach an operator.

Both safety gates *passed* on this run — retention `retained`, invariance `identical`. The
no-go is therefore about the component having no value, not about the substrate failing.
That distinction matters: a gate stack that has only ever passed things is untested, and
this one has now rejected something for a stated, reproducible reason.

Full analysis, including the straw-man trap this nearly walked into, is in
[ADR 0083](../../adr/0083-baseline-ladder-and-the-skill-selection-null-result.md).

## Condition 3: the honest reading

The condition asks for four domains. Three exist: mathematics, physics, logic. The encoding
is verified identical across all three, carries no domain-specific feature, and its feature
schema is a single `FeatureSchema` shared by every surface — so nothing in the encoding
would need to change to admit a fourth domain.

**But "would not need to change" is not the same as "was shown to work".** Sprint 20's
cross-domain pilot delivered three domains; the fourth is not in this repository, so the
condition is recorded as *partially met* rather than met. Marking it met would claim
evidence that does not exist. It is not on the non-negotiable list, and the shortfall is
a missing domain rather than a defect in the encoding.

## What Sprint 21 did not deliver

Stated so that no later reader infers more than was built.

- **No language capability, and no generative component.** Explicit non-goal. The
  functional foundation is the extension seam plus the port family; nothing in this sprint
  understands English.
- **No parametric learned component.** The ladder stopped at the deterministic rung, so
  `scikit-learn`, `xgboost`, `scipy`, and `joblib` were never installed and no
  `learned-baseline` extra exists.
- **No `torch`, no CUDA, no LoRA, no adapters, no distillation.**
- **No real-run harvesting.** Condition 7 is satisfied by measuring and disclosing a
  divergence that is `not_established` on zero real samples. Volume accrues into Sprint 22.
- **No Tier D research.** Permitted to end in a no-go and nothing depends on it; it was not
  attempted, which is recorded here rather than in a contract that would only ever hold
  "not attempted".
- **No 10⁶ capacity point.** 10⁵ is measured; the 10⁶ index build is a multi-hour run, not a
  design question.
- **Migration 0013's learning-substrate tables are not created.** The ANN half of 0013 is
  delivered; the `learned_*` tables the plan sketches in section 10 are not, because no
  component was promoted and nothing needs to persist an assessment yet.

## Follow-up recorded, not silently dropped

1. **The domain path performs no skill selection.** `run_case_as_skill` resolves the skill
   by static lookup and never calls `SkillSelectionService`. That is why the surface had no
   decision to learn. Wiring the selector in is a change to governed execution behaviour
   and needs its own controlled change.
2. **`SkillSelectionCandidate.statistics_score` is still inert at 0**, so ties break on
   `str(skill_id)`. The fix is a deterministic aggregation over accumulated outcomes, not a
   learned component.
3. **The `useful` label class is unreachable** while every fixture baseline is accepted,
   making a three-valued label binary in practice. Held as a tripwire test.
